import math
import random

from panda3d.core import Vec3
from worlds.simulation.actions import ActionRejected, distance, REACH
from worlds.simulation.contracts import EntityState, MATERIALS, ResourceAreaState, ResourceState, SimulationEvent
from worlds.simulation.rules import HAND_COUNT, MASS_EPSILON
from worlds.simulation.terrain import surface_height

ROOT_MASS = 0.05
MAX_SEED_MASS = 1
SEED_MATURITY = 0.5
GROVE_RADIUS = 35
GROWTH_SECONDS = {'wood': 21600, 'food': 3600, 'fiber': 7200}
PLANT_NAMES = {'wood': 'Tree', 'food': 'Berry bush', 'fiber': 'Fiber plant'}
SEED_DIMENSIONS = {'wood': (0.8, 0.8, 6), 'food': (1, 1, 1), 'fiber': (0.7, 0.7, 1)}


def resource_profile(entity, supply=None):
	planted = entity.material in GROWTH_SECONDS

	return ResourceState(
		supply=supply or ('renewable' if planted else 'finite'),
		capacity=entity.mass,
		mature_dimensions=entity.dimensions,
		root_mass=min(ROOT_MASS, entity.mass / 10) if planted else 0,
		growth_seconds=GROWTH_SECONDS.get(entity.material),
	)


def resize_resource(entity, capacity, dimensions):
	base = entity.position[2] - entity.dimensions[2] / 2
	scale = (entity.mass / capacity) ** (1 / 3)
	entity.dimensions = tuple(max(0.01, length * scale) for length in dimensions)

	if entity.fixed:
		entity.position = (*entity.position[:2], base + entity.dimensions[2] / 2)


def enable_ecology(state):
	for entity in state.entities:
		if entity.kind == 'resource' and entity.fixed and entity.resource is None:
			entity.resource = resource_profile(entity)

	if state.resource_areas:
		return

	for material, name in (('wood', 'Evergreen grove'), ('food', 'Wild berry patch'), ('fiber', 'Wild fiber bed')):
		plants = sorted(
			(
				entity
				for entity in state.entities
				if entity.kind == 'resource' and entity.material == material and entity.fixed
			),
			key=lambda entity: entity.position[:2],
		)
		covered = set()
		grove_index = 0

		for plant in plants:
			if plant.id in covered:
				continue

			members = [
				entity
				for entity in plants
				if entity.id not in covered and distance(entity.position[:2], plant.position[:2]) <= GROVE_RADIUS
			]
			covered.update(entity.id for entity in members)
			grove_index += 1

			if grove_index % 3 != 1:
				continue

			area = ResourceAreaState(
				name=f'{name} {grove_index}',
				material=material,
				position=plant.position,
				radius=35,
				target_count=len(members),
				renewal_seconds=GROWTH_SECONDS[material],
				next_spawn_tick=state.tick + GROWTH_SECONDS[material] * state.config.physics_hz,
			)

			for member in members:
				member.resource.area_id = area.id

			state.resource_areas.append(area)

	rocks = sorted(
		(entity for entity in state.entities if entity.kind == 'resource' and entity.material == 'stone'),
		key=lambda entity: entity.position[:2],
	)

	for index, rock in enumerate(rocks):
		if index % 5 == 0:
			rock.resource.supply = 'infinite'


class Ecology:
	def __init__(self, state, physics, manipulation):
		self.state = state
		self.physics = physics
		self.manipulation = manipulation

	def plant_profile(self, target):
		if target.kind != 'resource' or not target.fixed or target.material not in GROWTH_SECONDS:
			raise ActionRejected('Choose a rooted tree, berry bush, or fiber plant.')

		return target.resource or resource_profile(target)

	def take_seed(self, actor, target, amount):
		profile = self.plant_profile(target)

		if (
			amount > MAX_SEED_MASS
			or target.mass / profile.capacity < SEED_MATURITY
			or target.mass - amount < profile.root_mass
		):
			raise ActionRejected(
				'Take at most 1 kg of seeds or cuttings from a mature plant, leaving its roots intact.'
			)

		part = self.manipulation.gather(actor, target, amount)
		part.kind = 'seed'
		part.name = f'{PLANT_NAMES[target.material]} seeds or cutting'
		part.resource = profile.model_copy(update={'supply': 'renewable', 'area_id': None, 'felled_tick': None})

		return part

	def plant(self, actor, seed, destination):
		if seed.kind != 'seed' or seed.resource is None or seed.id not in actor.held_ids:
			raise ActionRejected('Hold seeds or a living cutting before planting.')

		x, y = destination[:2]
		ground = surface_height(x, y, self.state.config)

		if ground <= self.state.config.water_level + 0.5:
			raise ActionRejected('Plant on dry land above the water.')

		if abs(destination[2] - ground) > 1 or distance(self.state.entity(actor.id).position, (x, y, ground)) > REACH:
			raise ActionRejected('Plant in soil within reach.')

		if any(
			entity.id not in (seed.id, actor.id)
			and distance((x, y), entity.position[:2]) < max(entity.dimensions[:2]) / 2 + 0.3
			for entity in self.state.entities
		):
			raise ActionRejected('That planting location is occupied.')

		self.manipulation.release(actor, seed)
		seed.kind = 'resource'
		seed.name = f'Planted {PLANT_NAMES[seed.material].lower()}'
		seed.fixed = True
		seed.rotation = (1, 0, 0, 0)
		seed.velocity = seed.angular_velocity = (0, 0, 0)
		seed.resource.last_growth_tick = self.state.tick
		seed.position = (x, y, ground + seed.dimensions[2] / 2)
		resize_resource(seed, seed.resource.capacity, seed.resource.mature_dimensions)
		self.physics.replace_entity(seed)

		return seed

	def fell(self, actor, target):
		profile = self.plant_profile(target)

		if target.material != 'wood' or target.mass / profile.capacity < SEED_MATURITY:
			raise ActionRejected('Choose a mature standing tree to fell.')

		root_mass = profile.root_mass if profile.supply != 'finite' else 0
		width = max(target.dimensions[:2])
		log = EntityState(
			name='Felled log',
			kind='part',
			material='wood',
			shape='cylinder',
			dimensions=(width, width, target.dimensions[2]),
			mass=target.mass - root_mass,
			position=target.position,
			creator_id=actor.id,
		)
		log.resource = ResourceState(supply='finite', capacity=log.mass, mature_dimensions=log.dimensions)

		if root_mass:
			target.resource = profile
			target.mass = root_mass
			profile.last_growth_tick = profile.felled_tick = self.state.tick
			resize_resource(target, profile.capacity, profile.mature_dimensions)
			self.physics.replace_entity(target)
		else:
			self.manipulation.remove_entity(target)

		self.state.entities.append(log)
		self.physics.add_entity(log)
		direction = Vec3(*log.position) - Vec3(*self.state.entity(actor.id).position)
		direction.z = 0

		if direction.length() == 0:
			direction = Vec3(1, 0, 0)

		direction.normalize()
		self.physics.nodes[log.id].node().applyTorqueImpulse(Vec3(-direction.y, direction.x, 0) * log.mass * 0.5)

		return log

	def uproot(self, actor, target):
		profile = self.plant_profile(target)
		limit = 25 * actor.body.strength_trait * max(0.1, actor.body.growth)

		if (
			len(actor.held_ids) >= HAND_COUNT
			or sum(self.state.entity(identity).mass for identity in actor.held_ids) + target.mass > limit
		):
			raise ActionRejected('A free hand and enough carrying ability are needed. Fell a large tree first.')

		target.kind = 'seed'
		target.fixed = False
		target.resource = profile.model_copy(update={'supply': 'renewable', 'area_id': None, 'felled_tick': None})
		target.name = f'Uprooted {PLANT_NAMES[target.material].lower()}'
		self.physics.replace_entity(target)
		self.manipulation.grasp(actor, target)

		return target

	def grow(self):
		added = {}

		for entity in self.state.entities:
			profile = entity.resource

			if (
				entity.kind != 'resource'
				or not entity.fixed
				or profile is None
				or profile.supply == 'finite'
				or profile.growth_seconds is None
				or entity.mass >= profile.capacity
			):
				continue

			elapsed = (self.state.tick - profile.last_growth_tick) / self.state.config.physics_hz
			amount = min(profile.capacity - entity.mass, profile.capacity * elapsed / profile.growth_seconds)
			profile.last_growth_tick = self.state.tick

			if amount <= MASS_EPSILON:
				continue

			entity.mass += amount
			resize_resource(entity, profile.capacity, profile.mature_dimensions)
			self.physics.replace_entity(entity)
			added[entity.id] = amount

		return added

	def reseed(self):
		events = []

		for area in self.state.resource_areas:
			if self.state.tick < area.next_spawn_tick:
				continue

			area.next_spawn_tick = self.state.tick + round(area.renewal_seconds * self.state.config.physics_hz)
			count = sum(
				entity.kind == 'resource'
				and entity.fixed
				and entity.resource is not None
				and entity.resource.area_id == area.id
				for entity in self.state.entities
			)

			if count >= area.target_count:
				continue

			rng = random.Random(f'{self.state.config.seed}:{area.id}:{self.state.tick}')

			for _ in range(12):
				angle, radius = rng.random() * math.tau, math.sqrt(rng.random()) * area.radius
				x, y = area.position[0] + math.cos(angle) * radius, area.position[1] + math.sin(angle) * radius
				ground = surface_height(x, y, self.state.config)

				if (
					max(abs(x), abs(y)) > self.state.config.size / 2 - 2
					or ground <= self.state.config.water_level + 0.5
					or any(
						distance((x, y), entity.position[:2]) < max(entity.dimensions[:2]) / 2 + 1
						for entity in self.state.entities
					)
				):
					continue

				seed = EntityState(
					name=f'Wild {PLANT_NAMES[area.material].lower()} sapling',
					kind='resource',
					material=area.material,
					dimensions=SEED_DIMENSIONS[area.material],
					fixed=True,
					position=(x, y, ground + SEED_DIMENSIONS[area.material][2] / 2),
				)
				seed.mass = seed.volume * MATERIALS[seed.material].density
				seed.resource = resource_profile(seed)
				seed.resource.area_id = area.id
				seed.resource.last_growth_tick = self.state.tick
				seed.mass = seed.resource.root_mass
				resize_resource(seed, seed.resource.capacity, seed.resource.mature_dimensions)
				self.state.entities.append(seed)
				self.physics.add_entity(seed)
				events.append(
					SimulationEvent(
						kind='resource.reseeded',
						tick=self.state.tick,
						subject_id=seed.id,
						data={'area_id': area.id, 'mass_added': seed.mass, 'source': 'natural_reseeding'},
					)
				)
				break

		return events

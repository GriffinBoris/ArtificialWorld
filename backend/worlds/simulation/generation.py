import math
import random

from worlds.simulation.contracts import BodyState, EntityState, InhabitantState, MATERIALS, WorldState
from worlds.simulation.ecology import enable_ecology
from worlds.simulation.terrain import surface_height

FOREST_GROVES = 14
TREES_PER_GROVE = 36
ROCK_PATCHES = 9
ROCKS_PER_PATCH = 12
MEADOW_PLANTS = 180
STARTER_DEPOSITS = 100
CLEARING_RADIUS = 9
DEPOSIT_SPACING = 1.4
LEGACY_DEPOSITS = 100


def add_deposit(state, rng, material, x, y):
	half = state.config.size / 2 - 3

	if abs(x) > half or abs(y) > half or math.hypot(x, y) < CLEARING_RADIUS:
		return

	ground = surface_height(x, y, state.config)

	if ground < state.config.water_level + 0.7:
		return

	if any(math.hypot(x - entity.position[0], y - entity.position[1]) < DEPOSIT_SPACING for entity in state.entities):
		return

	height = (
		rng.uniform(4.5, 7.5)
		if material == 'wood'
		else rng.uniform(0.65, 2)
		if material == 'stone'
		else rng.uniform(0.7, 1.3)
	)
	width = rng.uniform(0.65, 1.1) if material == 'wood' else height * rng.uniform(0.9, 1.5)
	dimensions = (width, width, height)
	noun = {'wood': 'Tree', 'stone': 'Rock outcrop', 'food': 'Berry bush', 'fiber': 'Fiber patch'}[material]
	entity = EntityState(
		name=f'{noun} {len(state.entities)}',
		kind='resource',
		material=material,
		dimensions=dimensions,
		fixed=True,
		position=(x, y, ground + height / 2),
	)
	entity.mass = entity.volume * MATERIALS[material].density
	state.entities.append(entity)


def populate_resources(state, rng):
	half = state.config.size / 2 - 8

	for index in range(STARTER_DEPOSITS):
		angle, radius = rng.uniform(0, math.tau), rng.uniform(12, min(57, half))
		material = ('wood', 'wood', 'stone', 'fiber', 'food')[index % 5]
		add_deposit(state, rng, material, math.cos(angle) * radius, math.sin(angle) * radius)

	for index in range(FOREST_GROVES + ROCK_PATCHES):
		spread = min(135, half) if index % 2 == 0 else half
		center_x, center_y = rng.uniform(-spread, spread), rng.uniform(-spread, spread)
		material = 'wood' if index < FOREST_GROVES else 'stone'
		count = TREES_PER_GROVE if material == 'wood' else ROCKS_PER_PATCH

		for _ in range(count):
			angle, radius = rng.uniform(0, math.tau), math.sqrt(rng.random()) * (30 if material == 'wood' else 14)
			add_deposit(state, rng, material, center_x + math.cos(angle) * radius, center_y + math.sin(angle) * radius)

	for index in range(MEADOW_PLANTS):
		spread = min(120, half) if index % 2 == 0 else half
		add_deposit(
			state,
			rng,
			'food' if index % 3 == 0 else 'fiber',
			rng.uniform(-spread, spread),
			rng.uniform(-spread, spread),
		)


def populate_legacy_resources(state, rng):
	for index in range(LEGACY_DEPOSITS):
		x, y = rng.uniform(-190, 190), rng.uniform(-190, 190)
		ground = surface_height(x, y, state.config)

		if ground < state.config.water_level + 0.5:
			continue

		material = ('wood', 'wood', 'stone', 'fiber', 'food')[index % 5]
		dimensions = {
			'wood': (0.65, 0.65, 3.5),
			'stone': (1, 0.8, 0.5),
			'fiber': (0.6, 0.6, 0.7),
			'food': (0.7, 0.7, 0.8),
		}[material]
		entity = EntityState(
			name=f'{material.title()} deposit {index + 1}',
			kind='resource',
			material=material,
			dimensions=dimensions,
			fixed=True,
			position=(x, y, ground + dimensions[2] / 2),
		)
		entity.mass = entity.volume * MATERIALS[material].density
		state.entities.append(entity)


def populate(state: WorldState, population=6):
	rng = random.Random(state.config.seed)

	for index in range(population):
		x, y = (index % 3) * 5 - 5, (index // 3) * 5 - 5
		entity = EntityState(
			name=f'Inhabitant {index + 1}',
			kind='inhabitant',
			material='body',
			shape='capsule',
			dimensions=(0.5, 0.5, 1.7),
			mass=70,
			position=(x, y, surface_height(x, y, state.config) + 0.9),
		)
		body = BodyState(
			repair_trait=rng.uniform(0.85, 1.15),
			metabolism_trait=rng.uniform(0.9, 1.1),
			strength_trait=rng.uniform(0.85, 1.15),
		)
		state.entities.append(entity)
		state.inhabitants.append(InhabitantState(id=entity.id, name=entity.name, body=body))

	if state.config.rules_version == 1:
		populate_legacy_resources(state, rng)
	else:
		populate_resources(state, rng)

	for index in range(24):
		x, y = rng.uniform(-18, 18), rng.uniform(-15, 18)
		ground = surface_height(x, y, state.config)

		if ground < state.config.water_level + 0.5:
			continue

		entity = EntityState(
			name=f'Fallen branch {index + 1}',
			dimensions=(0.08, 0.08, 1),
			position=(x, y, ground + 0.1),
			rotation=(math.sqrt(0.5), math.sqrt(0.5), 0, 0),
		)
		entity.mass = entity.volume * MATERIALS['wood'].density
		state.entities.append(entity)

	enable_ecology(state)

	return state

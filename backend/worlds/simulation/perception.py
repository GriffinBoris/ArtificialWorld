import math

from worlds.simulation.actions import distance
from worlds.simulation.terrain import surface_height

SIGHT_RANGE = 60
VISIBLE_OBJECT_LIMIT = 30


def visible(state, observer_id, target):
	origin = state.entity(observer_id).position

	if distance(origin, target.position) > SIGHT_RANGE:
		return False

	start = (origin[0], origin[1], origin[2] + 0.6)
	end = target.position
	minimum = [min(a, b) for a, b in zip(start, end, strict=True)]
	maximum = [max(a, b) for a, b in zip(start, end, strict=True)]
	obstacles = [
		obstacle
		for obstacle in state.entities
		if obstacle.id not in (observer_id, target.id)
		and all(
			low < center + size / 2 and high > center - size / 2
			for low, high, center, size in zip(minimum, maximum, obstacle.position, obstacle.dimensions, strict=True)
		)
	]

	for index in range(1, 20):
		t = index / 20
		x, y, z = [a + (b - a) * t for a, b in zip(start, end, strict=True)]

		if surface_height(x, y, state.config) > z + 0.2:
			return False

		for obstacle in obstacles:
			if all(
				abs(point - center) < size / 2
				for point, center, size in zip((x, y, z), obstacle.position, obstacle.dimensions, strict=True)
			):
				return False

	return True


def observe(state, observer_id):
	agent = state.inhabitant(observer_id)
	body = state.entity(observer_id)
	candidates = sorted(
		(
			entity
			for entity in state.entities
			if entity.id != observer_id and distance(body.position, entity.position) <= SIGHT_RANGE
		),
		key=lambda entity: distance(body.position, entity.position),
	)
	objects = []

	for entity in candidates:
		if visible(state, observer_id, entity):
			objects.append(entity)

			if len(objects) == VISIBLE_OBJECT_LIMIT:
				break

	visible_ids = {entity.id for entity in objects} | {observer_id}

	return {
		'inhabitant_id': observer_id,
		'name': agent.name,
		'self_named': agent.self_named,
		'parent_named': agent.parent_named,
		'parents': agent.parents,
		'children': [
			{'id': child.id, 'name': child.name, 'parent_named': child.parent_named, 'self_named': child.self_named}
			for child in state.inhabitants
			if agent.id in child.parents and child.id in visible_ids
		],
		'tick': state.tick,
		'simulated_seconds': state.seconds,
		'alive': agent.alive,
		'body': agent.body.model_dump(),
		'position': body.position,
		'held_ids': agent.held_ids,
		'activity': agent.activity.model_dump() if agent.activity else None,
		'last_action_result': agent.last_action_result,
		'visible_objects': [
			{
				'id': entity.id,
				'name': entity.name,
				'kind': entity.kind,
				'material': entity.material,
				'dimensions': entity.dimensions,
				'position': entity.position,
				'velocity': entity.velocity,
			}
			for entity in objects
		],
		'landscape': [
			{
				'position': (body.position[0] + math.cos(angle) * radius, body.position[1] + math.sin(angle) * radius),
				'height': surface_height(
					body.position[0] + math.cos(angle) * radius,
					body.position[1] + math.sin(angle) * radius,
					state.config,
				),
			}
			for radius in (5, 20)
			for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2)
		],
		'wind': state.config.wind,
		'water_level': state.config.water_level,
		'resource_areas': [
			area.model_dump(mode='json')
			for area in state.resource_areas
			if distance(body.position[:2], area.position[:2]) <= area.radius + SIGHT_RANGE
		],
		'connections': [
			{'id': joint.id, 'entity_a': joint.entity_a, 'entity_b': joint.entity_b, 'kind': joint.kind}
			for joint in state.joints
			if joint.entity_a in visible_ids and joint.entity_b in visible_ids
		],
	}

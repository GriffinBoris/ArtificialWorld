import math
from itertools import pairwise

import pytest
from worlds.simulation.actions import Action, begin_action
from worlds.simulation.contracts import EntityState, WorldState
from worlds.simulation.engine import Simulation
from worlds.simulation.pathfinding import PathNotFound, RoutePlanner
from worlds.simulation.perception import observe
from worlds.simulation.terrain import surface_height


def test_route_goes_around_a_wall_and_respects_body_clearance(resource_simulation):
	state, actor, _, _ = resource_simulation
	wall = EntityState(
		name='Wall', fixed=True, dimensions=(1, 4, 3), position=(4, 0, surface_height(4, 0, state.config) + 1.5)
	)
	state.entities.append(wall)
	planner = RoutePlanner(state, actor.id)
	path = planner.route((8, 0, 0))
	assert path[-1][:2] == (8, 0)
	assert any(abs(point[1]) > 2.5 for point in path)
	previous = state.entity(actor.id).position[:2]
	for waypoint in path:
		assert planner.clear_segment(previous, waypoint[:2])
		previous = waypoint[:2]


def test_blocked_destination_and_deep_water_cannot_be_reported_as_a_route(resource_simulation):
	state, actor, tree, _ = resource_simulation
	with pytest.raises(PathNotFound, match='destination is blocked'):
		RoutePlanner(state, actor.id).route(tree.position)
	state.config.water_level = 100
	with pytest.raises(PathNotFound, match='deep water'):
		RoutePlanner(state, actor.id).route((8, 0, 0))


def test_one_walk_action_follows_a_route_and_reports_arrival(resource_simulation):
	state, actor, _, _ = resource_simulation
	wall = EntityState(
		name='Wall', fixed=True, dimensions=(1, 4, 3), position=(4, 0, surface_height(4, 0, state.config) + 1.5)
	)
	state.entities.append(wall)
	activity = begin_action(state, actor.id, Action(kind='walk', destination=(8, 0, 0)))
	simulation = Simulation(state)
	try:
		frames = simulation.advance(30)
		result = actor.last_action_result
		assert result['status'] == 'arrived'
		assert result['activity_id'] == activity.id
		assert math.dist(state.entity(actor.id).position[:2], (8, 0)) < 0.6
		assert any(abs(frame['state']['entities'][0]['position'][1]) > 2.4 for frame in frames)
		assert (
			len(
				[
					event
					for event in simulation.events
					if event.kind == 'activity.completed' and event.subject_id == activity.id
				]
			)
			== 1
		)
		assert observe(state, actor.id)['last_action_result']['status'] == 'arrived'
		assert actor.activity is None
	finally:
		simulation.close()


def test_a_walk_persists_between_steps_and_returns_a_result_only_when_finished(resource_simulation):
	state, actor, _, _ = resource_simulation
	actor.driver = 'pydantic'
	activity = begin_action(state, actor.id, Action(kind='walk', destination=(8, 0, 0)))
	simulation = Simulation(state)
	try:
		frames = simulation.advance(2)
		assert actor.activity is activity
		assert actor.last_action_result is None
		assert activity.navigation is not None
		positions = [
			next(entity['position'] for entity in frame['state']['entities'] if entity['id'] == actor.id)
			for frame in frames
		]
		assert max(math.dist(a[:2], b[:2]) for a, b in pairwise(positions)) < 0.3
		restored = WorldState.model_validate(state.model_dump(mode='json'))
	finally:
		simulation.close()
	resumed = Simulation(restored)
	try:
		resumed.advance(30)
		result = restored.inhabitant(actor.id).last_action_result
		assert result['activity_id'] == activity.id
		assert result['status'] == 'arrived'
		assert restored.inhabitant(actor.id).activity is None
		assert restored.tick < 32 * restored.config.physics_hz
	finally:
		resumed.close()


def test_unreachable_walk_returns_failure_without_advancing_through_the_obstacle(resource_simulation):
	state, actor, tree, _ = resource_simulation
	activity = begin_action(state, actor.id, Action(kind='walk', destination=tree.position))
	simulation = Simulation(state)
	try:
		simulation.advance(0.1)
		assert actor.last_action_result['status'] == 'failed'
		assert 'blocked' in actor.last_action_result['reason']
		assert not any(
			event.kind == 'activity.completed' and event.subject_id == activity.id for event in simulation.events
		)
		assert actor.activity is None
	finally:
		simulation.close()


def test_walking_replans_when_a_new_obstacle_blocks_the_journey(resource_simulation):
	state, actor, tree, _ = resource_simulation
	state.entities.remove(tree)
	activity = begin_action(state, actor.id, Action(kind='walk', destination=(10, 0, 0)))
	simulation = Simulation(state)
	try:
		simulation.advance(2)
		assert actor.activity is activity
		wall = EntityState(
			name='New wall', fixed=True, dimensions=(1, 4, 3), position=(4, 0, surface_height(4, 0, state.config) + 1.5)
		)
		state.entities.append(wall)
		simulation.physics.add_entity(wall)
		simulation.advance(40)
		assert actor.last_action_result['status'] == 'arrived'
		assert activity.navigation.replans > 0
	finally:
		simulation.close()


def test_a_barrier_across_the_world_has_no_route(resource_simulation):
	state, actor, _, _ = resource_simulation
	state.entities.extend(
		EntityState(name='Barrier', fixed=True, dimensions=(1, 30, 30), position=(4, y, 15))
		for y in (-60, -30, 0, 30, 60)
	)
	with pytest.raises(PathNotFound, match='No walkable route'):
		RoutePlanner(state, actor.id).route((8, 0, 0))

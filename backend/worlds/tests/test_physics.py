import math

import pytest
from panda3d.core import Quat, Vec3
from pydantic import ValidationError
from worlds.simulation.contracts import EntityState, InhabitantState, JointState, WorldConfig, WorldState
from worlds.simulation.manipulation import Manipulation
from worlds.simulation.physics import PhysicsWorld
from worlds.simulation.terrain import surface_height, terrain_height


def test_falling_object_settles_on_ground():
	config = WorldConfig(wind=(0, 0, 0))
	ground = terrain_height(0, 0, config.seed)
	part = EntityState(name='Stone', mass=10, dimensions=(0.4, 0.4, 0.4), position=(0, 0, ground + 3))
	state = WorldState(config=config, entities=[part])
	physics = PhysicsWorld(state)
	try:
		for _ in range(180):
			physics.step()
		physics.synchronize()
		assert ground - 0.2 < part.position[2] < ground + 0.5
		assert abs(part.velocity[2]) < 0.2
	finally:
		physics.close()


@pytest.mark.parametrize(('rules_version', 'x', 'y'), [(1, 110, 80), (2, 65, 48)])
def test_buoyancy_distinguishes_same_size_light_and_dense_parts(rules_version, x, y):
	config = WorldConfig(wind=(0, 0, 0), rules_version=rules_version)
	assert surface_height(x, y, config) < config.water_level - 2
	wood = EntityState(name='Wood', mass=600, dimensions=(1, 1, 1), position=(x, y, -0.4))
	stone = EntityState(name='Stone', mass=2600, dimensions=(1, 1, 1), position=(x + 2, y, -0.4))
	state = WorldState(config=config, entities=[wood, stone])
	physics = PhysicsWorld(state)
	try:
		for _ in range(180):
			physics.step()
		physics.synchronize()
		assert wood.position[2] > stone.position[2] + 1
		assert wood.position[2] > -0.5
	finally:
		physics.close()


@pytest.mark.parametrize('clearance', [0.85, 0.9, 0.95, 1])
def test_small_tablet_cannot_fall_through_the_detailed_terrain(clearance):
	config = WorldConfig(seed=17, wind=(0, 0, 0))
	ground = surface_height(-4.2, -5, config)
	part = EntityState(
		name='Tablet',
		mass=3,
		dimensions=(0.2, 0.2, 0.125),
		position=(-4.2, -5, surface_height(-5, -5, config) + clearance),
	)
	physics = PhysicsWorld(WorldState(config=config, entities=[part]))
	try:
		for _ in range(90):
			physics.step()
		physics.synchronize()
		assert ground < part.position[2] < ground + 0.2
	finally:
		physics.close()


def test_tilted_surface_has_vertical_aerodynamic_force():
	angle = math.pi / 8
	wing = EntityState(
		name='Plate',
		dimensions=(2, 2, 0.05),
		mass=2,
		position=(0, 0, 40),
		rotation=(math.cos(angle), 0, math.sin(angle), 0),
	)
	physics = PhysicsWorld(WorldState(config=WorldConfig(wind=(10, 0, 0)), entities=[wing]))
	try:
		assert abs(physics.environmental_force(wing).z) > 10
	finally:
		physics.close()


def test_fixed_joint_preserves_connection_under_gravity():
	a = EntityState(name='Anchor', fixed=True, dimensions=(0.2, 0.2, 0.2), position=(0, 0, 20))
	b = EntityState(name='Hanging part', dimensions=(0.2, 0.2, 0.2), position=(0, 0, 19))
	joint = JointState(entity_a=a.id, entity_b=b.id, anchor_a=(0, 0, -0.5), anchor_b=(0, 0, 0.5), strength=10000)
	state = WorldState(config=WorldConfig(wind=(0, 0, 0)), entities=[a, b], joints=[joint])
	physics = PhysicsWorld(state)
	try:
		for _ in range(60):
			physics.step()
		physics.synchronize()
		assert b.position[2] == pytest.approx(19, abs=0.1)
		assert len(state.joints) == 1
	finally:
		physics.close()


def test_geometry_rejects_nonfinite_or_mismatched_shapes():
	with pytest.raises(ValidationError):
		EntityState(name='Invalid', position=(float('nan'), 0, 0))
	with pytest.raises(ValidationError):
		EntityState(name='Invalid sphere', shape='sphere', dimensions=(1, 2, 3))


def test_off_center_push_turns_a_hinged_bar_around_its_pivot():
	anchor = EntityState(name='Pivot', fixed=True, position=(0, 0, 20))
	bar = EntityState(name='Lever', mass=4, dimensions=(4, 0.1, 0.1), position=(0, 0, 20))
	body = EntityState(name='Experimenter', kind='inhabitant', fixed=True, position=(1.5, 0.7, 20))
	actor = InhabitantState(id=body.id, name=body.name)
	joint = JointState(entity_a=anchor.id, entity_b=bar.id, kind='hinge', strength=100000)
	state = WorldState(
		config=WorldConfig(wind=(0, 0, 0)), entities=[anchor, bar, body], inhabitants=[actor], joints=[joint]
	)
	physics = PhysicsWorld(state)
	try:
		Manipulation(state, physics).push(actor, bar, (0, 0, -1), contact_point=(1.8, 0, 20))
		for _ in range(12):
			physics.step()
		physics.synchronize()
		tip = Quat(*bar.rotation).xform(Vec3(2, 0, 0))
		assert tip.z < -0.5
		assert bar.position == pytest.approx(anchor.position, abs=0.1)
		assert len(state.joints) == 1
	finally:
		physics.close()

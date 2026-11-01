import pytest
from core.test_fixtures import TestFixtures
from pydantic_ai import models
from worlds.services.worlds import create_world
from worlds.simulation.contracts import EntityState, InhabitantState, WorldConfig, WorldState
from worlds.simulation.ecology import resource_profile
from worlds.simulation.physics import PhysicsWorld
from worlds.simulation.terrain import surface_height


@pytest.fixture(autouse=True)
def forbid_live_inference(monkeypatch):

	monkeypatch.setattr(models, 'ALLOW_MODEL_REQUESTS', False)


@pytest.fixture
def owner(db):
	return TestFixtures.create_user()


@pytest.fixture
def world(owner):
	return create_world(owner, 'Test island', {'seed': 17, 'wind': [0, 0, 0]}, 2)


@pytest.fixture
def resource_simulation():
	config = WorldConfig(size=128, wind=(0, 0, 0))
	ground = surface_height(0, 0, config)
	body = EntityState(
		name='Planter',
		kind='inhabitant',
		material='body',
		shape='capsule',
		dimensions=(0.5, 0.5, 1.7),
		mass=70,
		position=(0, 0, ground + 0.85),
	)
	actor = InhabitantState(id=body.id, name=body.name, wake_tick=1000000)
	tree = EntityState(
		name='Tree',
		kind='resource',
		material='wood',
		fixed=True,
		mass=10,
		dimensions=(0.4, 0.4, 2),
		position=(1.5, 0, surface_height(1.5, 0, config) + 1),
	)
	tree.resource = resource_profile(tree)
	tree.resource.growth_seconds = 10
	state = WorldState(config=config, entities=[body, tree], inhabitants=[actor])
	physics = PhysicsWorld(state)
	try:
		yield state, actor, tree, physics
	finally:
		physics.close()

import math
from collections import Counter

import pytest
from worlds.simulation.contracts import MATERIALS, WorldConfig, WorldState
from worlds.simulation.generation import populate
from worlds.simulation.terrain import surface_height, terrain_grid, terrain_height


def test_new_generation_has_dense_habitats_finite_material_and_nearby_water():
	state = populate(WorldState(config=WorldConfig(seed=42)))
	resources = [entity for entity in state.entities if entity.kind == 'resource']
	counts = Counter(entity.material for entity in resources)
	assert counts['wood'] >= 400
	assert counts['stone'] >= 100
	assert counts['food'] >= 60
	assert counts['fiber'] >= 100
	assert surface_height(29, 0, state.config) < state.config.water_level
	for entity in resources:
		assert entity.fixed
		assert entity.mass == pytest.approx(entity.volume * MATERIALS[entity.material].density)
		assert entity.position[2] - entity.dimensions[2] / 2 == pytest.approx(
			surface_height(*entity.position[:2], state.config)
		)
		assert math.hypot(*entity.position[:2]) >= 9
	assert all(
		surface_height(*state.entity(agent.id).position[:2], state.config) > state.config.water_level
		for agent in state.inhabitants
	)


@pytest.mark.parametrize('size', [128, 1024, 4096])
def test_generation_stays_inside_bounds_and_repeats_the_same_seed(size):
	config = WorldConfig(seed=17, size=size)
	first, second = [populate(WorldState(config=config), population=2) for _ in range(2)]
	assert [(entity.material, entity.dimensions, entity.position, entity.mass) for entity in first.entities] == [
		(entity.material, entity.dimensions, entity.position, entity.mass) for entity in second.entities
	]
	assert all(
		abs(entity.position[axis]) + entity.dimensions[axis] / 2 < size / 2
		for entity in first.entities
		for axis in (0, 1)
	)


def test_surface_interpolates_the_actual_collision_mesh_and_legacy_terrain_is_versioned():
	config = WorldConfig(seed=42, size=128)
	grid = terrain_grid(config)
	spacing = config.size / (len(grid) - 1)
	x, y = -config.size / 2 + 40.2 * spacing, -config.size / 2 + 50.3 * spacing
	expected = grid[50][40] + (grid[50][41] - grid[50][40]) * 0.2 + (grid[51][40] - grid[50][40]) * 0.3
	assert surface_height(x, y, config) == pytest.approx(expected)
	assert len(grid) == 129
	legacy = WorldConfig(seed=42, rules_version=1)
	assert len(terrain_grid(legacy)) == 65
	assert terrain_height(29, 0, legacy.seed, legacy.rules_version) > legacy.water_level
	assert terrain_height(29, 0, config.seed, config.rules_version) < config.water_level

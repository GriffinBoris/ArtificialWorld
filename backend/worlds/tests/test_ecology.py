import pytest
from worlds.services.editor import edit_world, WorldEdit
from worlds.services.recordings import decode_recording, replay_state, save_checkpoint
from worlds.services.state import append_events, load_state, persist_state
from worlds.services.worlds import advance_world
from worlds.simulation.actions import Action, ActionRejected, begin_action
from worlds.simulation.contracts import EntityState, ResourceAreaState, SimulationEvent, WorldState
from worlds.simulation.ecology import Ecology, enable_ecology, resource_profile
from worlds.simulation.interactions import complete_activity
from worlds.simulation.manipulation import Manipulation
from worlds.simulation.terrain import surface_height


def test_felling_removes_the_standing_tree_and_preserves_its_mass_as_log_and_roots(resource_simulation):
	state, actor, tree, physics = resource_simulation
	log = Ecology(state, physics, Manipulation(state, physics)).fell(actor, tree)
	assert log.kind == 'part' and not log.fixed
	assert log.mass == pytest.approx(9.95)
	assert tree.mass == pytest.approx(0.05)
	assert tree.dimensions[2] < 0.5
	assert tree.resource.felled_tick == state.tick
	assert sum(entity.mass for entity in state.entities if entity.material == 'wood') == pytest.approx(10)
	assert Manipulation(state, physics).gather(actor, log, 1).mass == 1
	assert log.mass == pytest.approx(8.95)


def test_seed_collection_and_planting_transfer_real_material_without_cloning(resource_simulation):
	state, actor, tree, physics = resource_simulation
	ecology = Ecology(state, physics, Manipulation(state, physics))
	seed = ecology.take_seed(actor, tree, 0.25)
	assert seed.kind == 'seed' and seed.id in actor.held_ids
	assert tree.mass == pytest.approx(9.75)
	seed = ecology.plant(actor, seed, (-0.7, 0, surface_height(-0.7, 0, state.config)))
	assert seed.fixed and seed.kind == 'resource'
	assert seed.id not in actor.held_ids
	assert seed.resource.supply == 'renewable'
	assert seed.resource.area_id is None
	assert sum(entity.mass for entity in state.entities if entity.material == 'wood') == pytest.approx(10)


def test_uprooting_a_stump_clears_its_location_and_keeps_a_transplant(resource_simulation):
	state, actor, tree, physics = resource_simulation
	ecology = Ecology(state, physics, Manipulation(state, physics))
	ecology.fell(actor, tree)
	ecology.uproot(actor, tree)
	assert tree.kind == 'seed' and not tree.fixed
	assert tree.id in actor.held_ids
	assert not any(entity.kind == 'resource' and entity.fixed for entity in state.entities)


def test_plant_material_can_be_reused_as_an_ordinary_manufactured_part(resource_simulation):
	state, actor, tree, physics = resource_simulation
	manipulation = Manipulation(state, physics)
	seed = Ecology(state, physics, manipulation).take_seed(actor, tree, 0.25)
	part = manipulation.shape(actor, seed, Action(kind='shape', target_id=seed.id, dimensions=(0.05, 0.05, 0.05)))
	assert part.kind == 'part' and part.resource is None
	assert seed.kind == 'part' and seed.resource is None
	assert part.id in actor.held_ids
	assert sum(entity.mass for entity in state.entities if entity.material == 'wood') == pytest.approx(10)


def test_regrowth_uses_simulated_time_and_records_its_material_input(resource_simulation):
	state, actor, tree, physics = resource_simulation
	ecology = Ecology(state, physics, Manipulation(state, physics))
	ecology.fell(actor, tree)
	assert ecology.grow() == {}
	state.tick = 60
	assert ecology.grow() == {tree.id: pytest.approx(1)}
	assert tree.mass == pytest.approx(1.05)
	assert ecology.grow() == {}
	state.tick = 6000
	ecology.grow()
	assert tree.mass == 10
	assert tree.dimensions == pytest.approx((0.4, 0.4, 2))


def test_gathering_cannot_consume_a_living_plants_roots(resource_simulation):
	state, actor, tree, physics = resource_simulation
	before = state.model_dump()
	with pytest.raises(ActionRejected, match='quantity'):
		Manipulation(state, physics).gather(actor, tree, 10)
	assert state.model_dump() == before


@pytest.mark.parametrize('amount', [2, 11])
def test_seed_collection_rejects_large_quantities_without_changing_the_plant(resource_simulation, amount):
	state, actor, tree, physics = resource_simulation
	before = state.model_dump()
	with pytest.raises(ActionRejected, match='at most 1 kg'):
		Ecology(state, physics, Manipulation(state, physics)).take_seed(actor, tree, amount)
	assert state.model_dump() == before


def test_planting_in_water_is_rejected_without_losing_the_held_seed(resource_simulation):
	state, actor, tree, physics = resource_simulation
	ecology = Ecology(state, physics, Manipulation(state, physics))
	seed = ecology.take_seed(actor, tree, 0.25)
	before = state.model_dump()
	with pytest.raises(ActionRejected, match='dry land'):
		ecology.plant(actor, seed, (29, 0, 0))
	assert state.model_dump() == before


def test_infinite_quarry_supplies_material_repeatedly_and_logs_the_input(resource_simulation):
	state, actor, tree, physics = resource_simulation
	manipulation = Manipulation(state, physics)
	manipulation.remove_entity(tree)
	rock = EntityState(
		name='Quarry face',
		kind='resource',
		material='stone',
		fixed=True,
		mass=2,
		dimensions=(0.4, 0.4, 0.4),
		position=tree.position,
	)
	rock.resource = resource_profile(rock, 'infinite')
	state.entities.append(rock)
	physics.add_entity(rock)
	for _ in range(2):
		begin_action(state, actor.id, Action(kind='gather', target_id=rock.id, amount=1))
		events = complete_activity(state, physics, actor)
		actor.activity = None
		assert events[0].data['source_mass_added'] == 1
	assert rock.mass == 2
	assert sum(entity.mass for entity in state.entities if entity.material == 'stone') == 4
	with pytest.raises(ActionRejected, match='free hand'):
		manipulation.gather(actor, rock, 1)
	assert rock.mass == 2


def test_resource_area_reseeds_after_clearing_without_instant_or_unbounded_spawning(resource_simulation):
	state, _, _, physics = resource_simulation
	area = ResourceAreaState(
		name='Evergreen grove',
		material='wood',
		position=(10, 10, 0),
		radius=3,
		target_count=1,
		renewal_seconds=1,
		next_spawn_tick=60,
	)
	state.resource_areas = [area]
	ecology = Ecology(state, physics, Manipulation(state, physics))
	assert ecology.reseed() == []
	state.tick = 60
	event = ecology.reseed()[0]
	seed = state.entity(event.subject_id)
	assert event.data['mass_added'] == seed.mass
	assert seed.resource.area_id == area.id
	assert seed.mass < seed.resource.capacity
	assert ecology.reseed() == []
	state.tick = 120
	assert ecology.reseed() == []
	Manipulation(state, physics).remove_entity(seed)
	state.tick = 180
	assert ecology.reseed()[0].subject_id != seed.id


@pytest.mark.django_db
def test_existing_world_can_enable_ecology_without_replacing_entities_or_terrain(world):
	state = load_state(world)
	state.resource_areas = []
	for entity in state.entities:
		entity.resource = None
	persist_state(world, state)
	identities = {entity.id for entity in state.entities}
	configuration = world.configuration
	edit_world(world.id, WorldEdit(kind='ecology'))
	world.refresh_from_db()
	updated = load_state(world)
	assert {entity.id for entity in updated.entities} == identities
	assert world.configuration == configuration
	assert world.resource_areas.exists()
	assert any(entity.resource and entity.resource.supply == 'infinite' for entity in updated.entities)
	assert world.events.filter(kind='editor.ecology_enabled').count() == 1
	areas = {area.id for area in updated.resource_areas}
	enable_ecology(updated)
	assert {area.id for area in updated.resource_areas} == areas


@pytest.mark.django_db
def test_growth_and_resource_areas_survive_persistence_and_replay_without_regrowing(world, monkeypatch):
	state = load_state(world)
	tree = next(entity for entity in state.entities if entity.material == 'wood' and entity.kind == 'resource')
	tree.mass = tree.resource.root_mass
	tree.resource.growth_seconds = 10
	tree.resource.last_growth_tick = 0

	append_events(world, [SimulationEvent(kind='editor.intervened', tick=0, subject_id=tree.id)])
	persist_state(world, state)
	save_checkpoint(world, state)
	advance_world(world.id, 2, owner_step=True)
	world.refresh_from_db()
	live = load_state(world)
	assert live.entity(tree.id).mass > tree.mass
	assert world.events.filter(kind='resource.grown', subject_id=tree.id).exists()
	assert live.resource_areas
	monkeypatch.setattr(Ecology, 'grow', lambda self: pytest.fail('Replay must not run ecology.'))
	past = replay_state(world, 0)
	assert past.entity(tree.id).mass == tree.mass
	assert past.resource_areas == state.resource_areas
	assert decode_recording(world.checkpoints.order_by('-tick').first())['resource_areas']


def test_legacy_recordings_load_with_no_ecology_until_explicitly_enabled():
	state = WorldState.model_validate(
		{'config': {'rules_version': 1}, 'entities': [{'name': 'Old tree', 'kind': 'resource'}]}
	)
	assert state.resource_areas == []
	assert state.entities[0].resource is None

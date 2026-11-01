import pytest
from rest_framework.exceptions import ValidationError
from worlds.services.inhabitants import observation, read_document, submit_action, write_memory
from worlds.services.inspection import inspect_records
from worlds.services.recordings import replay_state, save_checkpoint
from worlds.services.state import load_state, persist_state
from worlds.services.worlds import advance_world
from worlds.simulation.actions import Action, ActionRejected
from worlds.simulation.contracts import Activity, EntityState
from worlds.simulation.engine import Simulation
from worlds.simulation.interactions import complete_activity
from worlds.simulation.lifecycle import progress_pregnancy
from worlds.simulation.manipulation import Manipulation
from worlds.simulation.physics import PhysicsWorld


def arrange(world):
	state = load_state(world)
	for actor in state.inhabitants:
		actor.wake_tick = 1000000
		actor.activity = None
	actor = state.inhabitants[0]
	part = EntityState(
		name='Wood tablet',
		mass=3,
		dimensions=(0.2, 0.2, 0.125),
		position=(state.entity(actor.id).position[0] + 0.8, *state.entity(actor.id).position[1:]),
		creator_id=actor.id,
	)
	state.entities.append(part)
	persist_state(world, state)
	save_checkpoint(world, state)
	return state, actor, part


@pytest.mark.django_db
def test_writings_have_persistent_versions_and_reachable_read_access(world):
	state, actor, part = arrange(world)
	submit_action(
		world.id,
		actor.id,
		Action(kind='write', target_id=part.id, title='A shared unit', text='We can exchange these marked stones.'),
	)
	advance_world(world.id, 1, owner_step=True)
	world.refresh_from_db()
	assert world.artifacts.exists(), (
		load_state(world).entity(actor.id).position,
		load_state(world).entity(part.id).position,
		list(world.events.values('kind', 'data')),
	)
	artifact = world.artifacts.get()
	assert artifact.versions.get().content == 'We can exchange these marked stones.'
	assert read_document(world.id, actor.id, artifact.id)['version'] == 1
	state = load_state(world)
	state.entity(actor.id).position = (450, 450, 20)
	persist_state(world, state)
	with pytest.raises(ValidationError, match='distance'):
		read_document(world.id, actor.id, artifact.id)


@pytest.mark.django_db
def test_replay_inspector_hides_later_document_versions_and_memories(world):
	_, actor, part = arrange(world)
	submit_action(
		world.id, actor.id, Action(kind='write', target_id=part.id, title='Experiment', text='First observation.')
	)
	advance_world(world.id, 1, owner_step=True)
	world.refresh_from_db()
	artifact = world.artifacts.get()
	write_memory(world.id, actor.id, 'First memory.')
	submit_action(
		world.id,
		actor.id,
		Action(
			kind='write',
			target_id=part.id,
			artifact_id=str(artifact.id),
			title='Experiment',
			text='A later observation.',
		),
	)
	advance_world(world.id, 1, owner_step=True)
	world.refresh_from_db()
	write_memory(world.id, actor.id, 'Later memory.')
	historical = inspect_records(world, part.id, tick=60)
	assert [version['content'] for version in historical['artifacts'][0]['versions']] == ['First observation.']
	assert len(inspect_records(world, part.id)['artifacts'][0]['versions']) == 2
	assert inspect_records(world, actor.id, tick=60)['memories'] == ['First memory.']
	assert inspect_records(world, actor.id)['memories'] == ['First memory.', 'Later memory.']


@pytest.mark.django_db
def test_memories_are_private_to_their_inhabitant(world):
	state = load_state(world)
	first, second = state.inhabitants
	write_memory(world.id, first.id, 'I suspect these plates can lift.', 0.4)
	world.refresh_from_db()
	assert observation(world, first.id)['memories'][0]['text'] == 'I suspect these plates can lift.'
	assert observation(world, second.id)['memories'] == []
	assert world.events.filter(kind='memory.written').get().data['private'] is True


@pytest.mark.django_db
def test_speech_only_reaches_nearby_inhabitants(world):
	state, actor, _ = arrange(world)
	other = state.inhabitants[1]
	state.entity(other.id).position = (450, 450, 20)
	persist_state(world, state)
	submit_action(world.id, actor.id, Action(kind='speak', text='Can anyone hear this?'))
	advance_world(world.id, 1, owner_step=True)
	world.refresh_from_db()
	message = world.events.get(kind='message.spoken')
	assert other.id not in message.data['recipient_ids']
	assert observation(world, other.id)['messages'] == []


@pytest.mark.django_db
def test_replay_includes_new_parts_created_inside_a_step(world):
	state, actor, _ = arrange(world)
	deposit = EntityState(
		name='Fiber deposit',
		kind='resource',
		material='fiber',
		fixed=True,
		mass=10,
		position=(state.entity(actor.id).position[0] + 1, *state.entity(actor.id).position[1:]),
	)
	state.entities.append(deposit)
	persist_state(world, state)
	save_checkpoint(world, state)
	submit_action(world.id, actor.id, Action(kind='gather', target_id=deposit.id, amount=0.1))
	advance_world(world.id, 2, owner_step=True)
	world.refresh_from_db()
	created = world.events.get(kind='resource.gathered').subject_id
	replay = replay_state(world, 90)
	assert replay.entity(created).mass == pytest.approx(0.1)
	assert replay.entity(deposit.id).mass == pytest.approx(9.9)


@pytest.mark.django_db
def test_shaping_preserves_mass_and_rejects_creating_material(world):
	state, actor, part = arrange(world)
	physics = PhysicsWorld(state)
	try:
		manipulation = Manipulation(state, physics)
		manipulation.grasp(actor, part)
		before = sum(entity.mass for entity in state.entities)
		with pytest.raises(ActionRejected, match='enough material'):
			manipulation.shape(actor, part, Action(kind='shape', target_id=part.id, dimensions=(2, 2, 2)))
		assert part.id in actor.held_ids
		manipulation.shape(actor, part, Action(kind='shape', target_id=part.id, dimensions=(0.1, 0.1, 0.1)))
		assert sum(entity.mass for entity in state.entities) == pytest.approx(before)
	finally:
		physics.close()


@pytest.mark.django_db
def test_birth_creates_distinct_offspring_and_no_private_memories(world):
	state = load_state(world)
	parent, partner = state.inhabitants
	parent.pregnancy_partner = partner.id
	parent.pregnancy_progress = 1
	physics = PhysicsWorld(state)
	try:
		events = progress_pregnancy(state, parent, 1, physics)
		child = state.inhabitants[-1]
		assert child.id not in (parent.id, partner.id)
		assert child.parents == [parent.id, partner.id]
		assert child.body.growth < 1
		assert child.body.age_seconds == 0
		assert events[0].kind == 'inhabitant.born'
	finally:
		physics.close()


@pytest.mark.django_db
def test_persistent_program_executes_with_only_virtual_records_and_local_messages(world):
	state, actor, part = arrange(world)
	physics = PhysicsWorld(state)
	try:
		Manipulation(state, physics).grasp(actor, part)
	finally:
		physics.close()
	persist_state(world, state)
	submit_action(
		world.id,
		actor.id,
		Action(
			kind='program',
			target_id=part.id,
			title='Counter',
			text='[{"put":"count","value":{"op":"add","args":[{"record":"count"},1]}},{"send":"hello nearby"}]',
		),
	)
	advance_world(world.id, 1, owner_step=True)
	world.refresh_from_db()
	assert world.programs.count() == 1
	assert world.artifacts.get(kind='program').title == 'Counter'
	advance_world(world.id, 1, owner_step=True)
	world.refresh_from_db()
	assert world.programs.get().state['records'] == {'count': 1}
	assert world.events.filter(kind='message.spoken', actor_id=part.id).get().data['text'] == 'hello nearby'
	assert load_state(world).entity(part.id).kind == 'device'
	advance_world(world.id, 5, owner_step=True)
	assert world.programs.get().state['records'] == {'count': 6}


@pytest.mark.django_db
def test_reproduction_needs_both_consents_and_can_be_revoked(world):
	state = load_state(world)
	first, second = state.inhabitants
	position = state.entity(first.id).position
	state.entity(second.id).position = (position[0] + 1, position[1], position[2])
	physics = PhysicsWorld(state)
	try:

		def consent(actor, partner, willing=True):
			actor.activity = Activity(
				kind='consent',
				started_tick=0,
				ends_tick=1,
				parameters=Action(kind='consent', target_id=partner.id, willing=willing).model_dump(mode='json'),
			)
			return complete_activity(state, physics, actor)

		consent(first, second)
		assert first.pregnancy_partner is None and second.pregnancy_partner is None
		consent(first, second, willing=False)
		assert first.reproduction_consent is None
		consent(second, first)
		assert first.pregnancy_partner is None and second.pregnancy_partner is None
		consent(first, second)
		assert first.pregnancy_partner == second.id
		assert second.pregnancy_partner is None
	finally:
		physics.close()


@pytest.mark.django_db
def test_population_growth_has_no_founder_count_cap(world):
	state = load_state(world)
	parent, partner = state.inhabitants
	physics = PhysicsWorld(state)
	try:
		for _ in range(12):
			parent.pregnancy_partner = partner.id
			parent.pregnancy_progress = 1
			assert progress_pregnancy(state, parent, 0, physics)[0].kind == 'inhabitant.born'
		assert len(state.inhabitants) == 14
		assert len({child.id for child in state.inhabitants}) == 14
	finally:
		physics.close()


@pytest.mark.django_db
def test_walking_moves_an_embodied_inhabitant_across_terrain(world):
	state, actor, _ = arrange(world)
	start = state.entity(actor.id).position
	action = Action(kind='walk', destination=(start[0] + 10, start[1], start[2]))
	actor.activity = Activity(kind='walk', started_tick=0, ends_tick=1800, parameters=action.model_dump(mode='json'))
	simulation = Simulation(state)
	try:
		simulation.advance(5)
		assert state.entity(actor.id).position[0] > start[0] + 1
		assert actor.body.energy < 100
	finally:
		simulation.close()

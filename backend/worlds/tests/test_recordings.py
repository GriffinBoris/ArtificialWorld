import pytest
from worlds.services.recordings import decode_recording, motion_deltas, replay_state
from worlds.services.state import load_state
from worlds.services.worlds import advance_world
from worlds.simulation.contracts import EntityState, WorldState


@pytest.mark.django_db
def test_step_persists_state_events_and_ten_hz_motion(world):
	before = load_state(world)
	advance_world(world.id, 2, owner_step=True)
	world.refresh_from_db()
	after = load_state(world)
	assert world.tick == 120
	assert world.checkpoints.count() == 2
	assert world.events.filter(kind='activity.started', tick=0).count() == 2
	assert world.events.filter(kind='message.spoken').count() == 2
	assert world.events.filter(kind='world.advanced').count() == 1
	frames = decode_recording(world.motion_blocks.get())
	assert len(frames) == 20
	assert frames[0]['tick'] == 6
	assert frames[-1]['tick'] == 120
	assert before.entities != after.entities
	sequences = list(world.events.order_by('sequence').values_list('sequence', flat=True))
	assert sequences == list(range(1, len(sequences) + 1))


@pytest.mark.django_db
def test_replay_uses_recordings_without_advancing_live_state(world, monkeypatch):
	advance_world(world.id, 2, owner_step=True)
	world.refresh_from_db()
	before = load_state(world).model_dump()
	frame = next(frame for frame in decode_recording(world.motion_blocks.get()) if frame['tick'] == 60)
	replay = replay_state(world, 60)
	for item in frame['state']['entities']:
		assert replay.entity(item['id']).position == tuple(item['position'])
	assert replay.tick == 60
	assert load_state(world).model_dump() == before


@pytest.mark.django_db
def test_corrupted_recording_is_rejected(world):
	checkpoint = world.checkpoints.get()
	checkpoint.payload = b'corrupted'
	with pytest.raises(ValueError, match='checksum'):
		decode_recording(checkpoint)


def test_motion_transfer_preserves_fixed_resource_changes_new_entities_and_removals():
	tree = EntityState(name='Tree', kind='resource', fixed=True, mass=100)
	part = EntityState(name='A part')
	state = WorldState(entities=[tree, part])
	frames = [{'tick': 0, 'state': state.model_dump(mode='json')}]
	tree.mass = 95
	state.entities.remove(part)
	new_part = EntityState(name='Gathered wood', mass=5)
	state.entities.append(new_part)
	state.tick = 6
	frames.append({'tick': 6, 'state': state.model_dump(mode='json')})
	state.tick = 12
	frames.append({'tick': 12, 'state': state.model_dump(mode='json')})
	deltas = motion_deltas(frames)
	assert deltas[1]['removed_entity_ids'] == [part.id]
	assert {entity['id'] for entity in deltas[1]['changed_entities']} == {tree.id, new_part.id}
	assert deltas[2]['changed_entities'] == []
	entities = {}
	for original, delta in zip(frames, deltas, strict=True):
		for identity in delta['removed_entity_ids']:
			del entities[identity]
		entities.update({entity['id']: entity for entity in delta['changed_entities']})
		assert {**delta['state'], 'entities': list(entities.values())} == original['state']

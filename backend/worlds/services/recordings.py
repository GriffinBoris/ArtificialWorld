import hashlib
import json
import zlib

from worlds.models import Checkpoint, MotionBlock
from worlds.simulation.contracts import WorldState


def encode_recording(data):
	payload = zlib.compress(json.dumps(data, separators=(',', ':'), allow_nan=False).encode(), level=6)

	return payload, hashlib.sha256(payload).hexdigest()


def decode_recording(record):
	payload = bytes(record.payload)

	if hashlib.sha256(payload).hexdigest() != record.checksum:
		raise ValueError('Recording checksum mismatch.')

	return json.loads(zlib.decompress(payload))


def save_checkpoint(world, state):
	payload, checksum = encode_recording(state.model_dump(mode='json'))
	Checkpoint.objects.get_or_create(
		world=world,
		tick=state.tick,
		event_sequence=world.event_sequence,
		defaults={'payload': payload, 'checksum': checksum},
	)


def save_motion(world, start_tick, state, frames):
	if not frames:
		return

	payload, checksum = encode_recording(frames)
	MotionBlock.objects.create(
		world=world, start_tick=start_tick, end_tick=state.tick, payload=payload, checksum=checksum
	)


def motion_deltas(frames):

	previous = {}
	encoded = []

	for frame in frames:
		state = frame['state']
		entities = {entity['id']: entity for entity in state['entities']}
		encoded.append(
			{
				'tick': frame['tick'],
				'state': {key: value for key, value in state.items() if key != 'entities'},
				'changed_entities': [
					entity for identity, entity in entities.items() if previous.get(identity) != entity
				],
				'removed_entity_ids': [identity for identity in previous if identity not in entities],
			}
		)
		previous = entities

	return encoded


def replay_state(world, tick):
	checkpoint = world.checkpoints.filter(tick__lte=tick).order_by('-tick', '-event_sequence').first()

	if checkpoint is None:
		raise ValueError('No checkpoint exists at this time.')

	state = WorldState.model_validate(decode_recording(checkpoint))

	for block in world.motion_blocks.filter(end_tick__gt=checkpoint.tick, start_tick__lte=tick).order_by(
		'start_tick', 'id'
	):
		for frame in decode_recording(block):
			if checkpoint.tick < frame['tick'] <= tick:
				state = WorldState.model_validate(frame['state'])

	return state

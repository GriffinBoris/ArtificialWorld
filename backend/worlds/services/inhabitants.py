from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from worlds.models import Artifact, Inhabitant, Memory, World
from worlds.services.artifacts import artifact_position, read_artifact
from worlds.services.recordings import save_checkpoint
from worlds.services.state import append_events, load_state, persist_state, world_lock
from worlds.simulation.actions import ActionRejected, begin_action, distance
from worlds.simulation.contracts import SimulationEvent
from worlds.simulation.perception import observe
from worlds.simulation.rules import SPEECH_RANGE

MESSAGE_BATCH_SIZE = 20


def observation(world, actor_id, state=None):
	if state is None:
		state = load_state(world)
	agent = state.inhabitant(str(actor_id))
	result = observe(state, agent.id)
	result['memories'] = list(
		Memory.objects.filter(inhabitant_id=actor_id).order_by('-id').values('id', 'text', 'tick', 'confidence')[:8]
	)
	result['messages'] = [
		{'sequence': event.sequence, 'tick': event.tick, 'speaker_id': event.actor_id, 'text': event.data['text']}
		for event in world.events.filter(kind='message.spoken', sequence__gt=agent.last_observation_sequence).order_by(
			'sequence'
		)
		if agent.id in event.data['recipient_ids']
	]
	result['observed_sequence'] = (
		result['messages'][MESSAGE_BATCH_SIZE]['sequence'] - 1
		if len(result['messages']) > MESSAGE_BATCH_SIZE
		else world.event_sequence
	)
	result['messages'] = result['messages'][:MESSAGE_BATCH_SIZE]
	thinking_ids = {
		str(value) for value in world.decisions.filter(status='thinking').values_list('inhabitant_id', flat=True)
	}
	visible_ids = {item['id'] for item in result['visible_objects']}
	result['nearby_inhabitants'] = [
		{
			'id': other.id,
			'name': other.name,
			'position': state.entity(other.id).position,
			'status': 'dead'
			if not other.alive
			else 'thinking'
			if other.id in thinking_ids
			else 'acting'
			if other.activity
			else 'idle',
			'activity': other.activity.kind if other.activity else None,
		}
		for other in state.inhabitants
		if other.id != agent.id and other.id in visible_ids
	]
	result['artifacts'] = [
		{'id': str(artifact.id), 'title': artifact.title, 'position': artifact_position(artifact, state)}
		for artifact in world.artifacts.filter(location__isnull=False)
		if distance(state.entity(agent.id).position, artifact_position(artifact, state)) <= SPEECH_RANGE
	]
	result['personal_events'] = list(
		world.events.filter(
			Q(actor_id=agent.id) | Q(subject_id=agent.id),
			sequence__gt=agent.last_observation_sequence,
			kind__in=(
				'activity.completed',
				'activity.failed',
				'collision.damage',
				'inhabitant.born',
				'inhabitant.died',
				'inhabitant.named',
				'connection.broken',
			),
		)
		.order_by('-sequence')
		.values('sequence', 'tick', 'kind', 'subject_id', 'data')[:20]
	)

	return result


def submit_action(world_id, actor_id, action):
	with world_lock(world_id), transaction.atomic():
		world = World.objects.select_for_update().get(id=world_id)
		state = load_state(world)

		if (
			action.kind == 'write'
			and action.artifact_id
			and not Artifact.objects.filter(id=action.artifact_id, world=world, location_id=action.target_id).exists()
		):
			raise ValidationError('This artifact does not exist on that writing surface.')

		try:
			activity = begin_action(state, str(actor_id), action)
		except ActionRejected as error:
			raise ValidationError(str(error)) from error

		append_events(
			world,
			[
				SimulationEvent(
					kind='activity.started',
					tick=state.tick,
					actor_id=str(actor_id),
					subject_id=activity.id,
					data=activity.model_dump(mode='json'),
				)
			],
		)
		persist_state(world, state)
		save_checkpoint(world, state)

		return activity


def write_memory(world_id, actor_id, text, confidence=0.5):
	with world_lock(world_id), transaction.atomic():
		world = World.objects.select_for_update().get(id=world_id)
		agent = Inhabitant.objects.get(world=world, entity_id=actor_id)

		if not agent.alive:
			raise ValidationError('A dead inhabitant cannot write memories.')

		memory = Memory.objects.create(inhabitant=agent, text=text, tick=world.tick, confidence=confidence)
		append_events(
			world,
			[
				SimulationEvent(
					kind='memory.written',
					tick=world.tick,
					actor_id=str(actor_id),
					subject_id=str(memory.id),
					data={'text': text, 'confidence': confidence, 'private': True},
				)
			],
		)
		world.save(update_fields=('event_sequence', 'updated_ts'))

		return memory


def search_memories(actor_id, query=''):
	return list(
		Memory.objects.filter(inhabitant_id=actor_id)
		.filter(Q(text__icontains=query))
		.order_by('-id')
		.values('id', 'text', 'tick', 'confidence')[:30]
	)


def read_document(world_id, actor_id, artifact_id):
	with world_lock(world_id), transaction.atomic():
		world = World.objects.select_for_update().get(id=world_id)
		state = load_state(world)
		result = read_artifact(world, state, str(actor_id), artifact_id)
		append_events(
			world,
			[
				SimulationEvent(
					kind='artifact.read',
					tick=world.tick,
					actor_id=str(actor_id),
					subject_id=str(artifact_id),
					data={'version': result['version']},
				)
			],
		)
		world.save(update_fields=('event_sequence', 'updated_ts'))

		return result

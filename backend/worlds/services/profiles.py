from django.db.models import Q
from rest_framework.exceptions import NotFound
from worlds.models import Memory
from worlds.services.recordings import replay_state
from worlds.services.state import load_state

PROFILE_LIMIT = 100
MESSAGE_SCAN_LIMIT = 1000


def world_messages(world, actor_id=None, tick=None):
	query = world.events.filter(kind='message.spoken')

	if tick is not None:
		query = query.filter(tick__lte=tick)

	names = {str(entity.id): entity.name for entity in world.entities.all()}
	rows = []

	for event in query.order_by('-sequence')[:MESSAGE_SCAN_LIMIT]:
		recipients = event.data['recipient_ids']

		if actor_id is not None and event.actor_id != str(actor_id) and str(actor_id) not in recipients:
			continue

		rows.append(
			{
				'id': event.id,
				'sequence': event.sequence,
				'tick': event.tick,
				'speaker_id': event.actor_id,
				'speaker_name': event.data.get('speaker_name', names.get(event.actor_id, 'Former inhabitant')),
				'text': event.data['text'],
				'recipient_ids': recipients,
				'position': event.data['position'],
			}
		)

		if len(rows) == PROFILE_LIMIT:
			break

	return list(reversed(rows))


def inhabitant_profile(world, actor_id, tick=None):
	state = load_state(world) if tick is None else replay_state(world, tick)
	identity = str(actor_id)
	agent = next((agent for agent in state.inhabitants if agent.id == identity), None)

	if agent is None:
		raise NotFound('This inhabitant does not exist at the selected time.')

	memories = Memory.objects.filter(inhabitant_id=actor_id)
	events = world.events.filter(Q(actor_id=identity) | Q(subject_id=identity)).exclude(
		kind__in=('decision.observed', 'decision.completed', 'activity.started', 'memory.written', 'message.spoken')
	)
	decisions = world.decisions.filter(inhabitant_id=actor_id)

	if tick is not None:
		memories = memories.filter(tick__lte=tick)
		events = events.filter(tick__lte=tick)
		decisions = decisions.filter(tick__lte=tick)

	decision_rows = list(
		decisions.order_by('-created_ts').values('id', 'tick', 'status', 'observation', 'result', 'trace', 'error')[:20]
	)

	if tick is not None:
		for decision in decision_rows:
			for entry in decision['trace']:
				if entry.get('completed_tick', -1) > tick:
					entry['status'] = 'running'
					entry.pop('result')
					entry.pop('completed_tick')
					entry.pop('error', None)

	return {
		'inhabitant': agent.model_dump(mode='json'),
		'position': state.entity(identity).position,
		'memories': list(memories.order_by('-tick', '-id').values('id', 'text', 'confidence', 'tick')[:PROFILE_LIMIT]),
		'messages': world_messages(world, actor_id, tick),
		'history': list(
			events.order_by('-sequence').values('id', 'sequence', 'tick', 'kind', 'actor_id', 'subject_id', 'data')[
				:PROFILE_LIMIT
			]
		),
		'decisions': decision_rows,
		'recorded_tick': state.tick,
	}

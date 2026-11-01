import asyncio

from django.conf import settings
from django.db import close_old_connections, transaction
from rest_framework.exceptions import ValidationError
from worlds.agents.contracts import DecisionContext, DecisionOutcome
from worlds.agents.conversation import bootstrap_conversation, MAX_RECENT_TURNS, retain_conversation
from worlds.agents.providers import provider_available
from worlds.agents.pydantic_driver import PydanticDriver
from worlds.agents.rounds import collect_decisions
from worlds.models import Artifact, Decision, Inhabitant, Memory, World
from worlds.services.artifacts import artifact_position, read_artifact
from worlds.services.inhabitants import observation
from worlds.services.recordings import save_checkpoint
from worlds.services.state import append_events, load_state, persist_state, world_lock, WorldBusy
from worlds.simulation.actions import Action, ActionRejected, begin_action, distance, REACH
from worlds.simulation.contracts import SimulationEvent
from worlds.simulation.rules import WRITING_RANGE


def due_inhabitants(state):
	return [
		agent
		for agent in state.inhabitants
		if agent.alive and agent.driver != 'scripted' and agent.activity is None and agent.wake_tick <= state.tick
	]


def prepare_round(world_id, owner_step=False, live=False, independent=False, limit=None):
	with world_lock(world_id), transaction.atomic():
		world = World.objects.select_for_update().get(id=world_id)

		if not owner_step and world.status != 'running':
			return world.revision, [], 0

		thinking_ids = {
			str(value) for value in world.decisions.filter(status='thinking').values_list('inhabitant_id', flat=True)
		}

		if thinking_ids and not independent:
			raise WorldBusy('An agent decision round is already running.')

		state = load_state(world)
		agents = [agent for agent in due_inhabitants(state) if agent.id not in thinking_ids]
		agents.sort(key=lambda agent: (agent.last_decision_tick, agent.id))
		if limit is not None:
			agents = agents[:limit]
		if not agents:
			return world.revision, [], settings.WORLD_THINKING_SLOTS

		if live:
			validate_live_configuration(state, agents)

		contexts = []
		events = []

		for agent in agents:
			observed = observation(world, agent.id, state)
			conversation = Inhabitant.objects.get(world=world, pk=agent.id).agent_context

			if not conversation:
				conversation = bootstrap_conversation(
					list(
						world.decisions.filter(inhabitant_id=agent.id, status__in=('completed', 'rejected')).order_by(
							'-created_ts'
						)[:MAX_RECENT_TURNS]
					)
				)

			pending_id = conversation.get('pending_decision_id')
			previous = (
				world.decisions.get(id=pending_id, inhabitant_id=agent.id)
				if pending_id
				else world.decisions.filter(inhabitant_id=agent.id, status__in=('completed', 'rejected'))
				.order_by('-created_ts')
				.first()
			)
			observed['continuity'] = {
				'session_id': agent.id,
				'earlier_experiences': conversation.get('summary', []),
				'last_shared_plan': conversation.get('last_shared_plan', ''),
			}
			decision = Decision.objects.create(
				world=world,
				inhabitant_id=agent.id,
				tick=state.tick,
				observation=observed,
				model_name=agent.model_name,
				status='thinking',
			)
			documents = {
				str(artifact.id): read_artifact(world, state, agent.id, artifact.id)
				for artifact in world.artifacts.filter(location__isnull=False)
				if distance(state.entity(agent.id).position, artifact_position(artifact, state)) <= WRITING_RANGE
			}
			memories = list(
				Memory.objects.filter(inhabitant_id=agent.id).order_by('-id').values('id', 'text', 'confidence', 'tick')
			)
			contexts.append(
				DecisionContext(
					str(decision.id), agent.id, agent.driver, agent.model_name, observed, memories, documents
				)
			)
			contexts[-1].event_sequence = world.event_sequence
			contexts[-1].world_id = str(world.id)
			contexts[-1].conversation = conversation
			if previous:
				contexts[-1].previous_tool = next(
					(entry for entry in previous.trace if 'tool_call_id' in entry and 'result' in entry),
					None,
				)

			contexts[-1].measurements = {
				entity.id: {
					'id': entity.id,
					'mass': entity.mass,
					'condition': entity.condition,
					'shape': entity.shape,
					'dimensions': entity.dimensions,
					'rotation': entity.rotation,
					'resource': entity.resource.model_dump(mode='json') if entity.resource else None,
				}
				for entity in state.entities
				if entity.id in {item['id'] for item in observed['visible_objects']}
				and distance(state.entity(agent.id).position, entity.position) <= REACH + max(entity.dimensions) / 2
			}
			events.append(
				SimulationEvent(
					kind='decision.observed',
					tick=state.tick,
					actor_id=agent.id,
					subject_id=str(decision.id),
					data={'observation': observed},
				)
			)

		append_events(world, events)
		world.save(update_fields=('event_sequence', 'updated_ts'))

		return world.revision, contexts, settings.WORLD_THINKING_SLOTS


def apply_round(world_id, revision, outcomes, independent=False):
	with world_lock(world_id), transaction.atomic():
		world = World.objects.select_for_update().get(id=world_id)
		state = load_state(world)
		events = []
		stale = revision != world.revision
		failed = any(outcome.error for outcome in outcomes)
		accepted = True
		offset = state.action_rotation % max(1, len(outcomes))

		for outcome in outcomes[offset:] + outcomes[:offset]:
			context = outcome.context
			stale = revision != world.revision
			if independent:
				agent = state.inhabitant(context.actor_id)
				stale = (
					world.status != 'running'
					or not agent.alive
					or agent.activity is not None
					or agent.driver != context.driver
					or agent.model_name != context.model_name
					or world.events.filter(kind='world.paused', sequence__gt=context.event_sequence).exists()
				)
				failed = bool(outcome.error)
			decision = Decision.objects.get(id=context.decision_id, world=world, status='thinking')
			decision.status = 'stale' if stale else 'failed' if failed else 'completed'
			decision.error = outcome.error
			if outcome.trace:
				decision.trace = outcome.trace
			accepted = accepted and not stale and not failed

			if outcome.reply:
				decision.result = outcome.reply.draft.model_dump(mode='json')
				decision.trace = outcome.reply.trace
				decision.messages = outcome.reply.messages

			action_tool = next((entry for entry in decision.trace if 'tool_call_id' in entry), None)

			if action_tool and (stale or failed):
				action_tool.update(
					status='cancelled',
					result={
						'status': 'failed',
						'reason': 'The world changed or the decision round failed before acting.',
					},
				)

			if not stale and not failed:
				draft = outcome.reply.draft
				state.inhabitant(context.actor_id).last_observation_sequence = context.observation['observed_sequence']

				try:
					if (
						draft.action.kind == 'write'
						and draft.action.artifact_id
						and not Artifact.objects.filter(
							id=draft.action.artifact_id, world=world, location_id=draft.action.target_id
						).exists()
					):
						raise ActionRejected('This artifact does not exist on that writing surface.')

					activity = begin_action(state, context.actor_id, draft.action)
					decision.result['activity_id'] = activity.id

					if action_tool:
						action_tool.update(status='running', activity_id=activity.id)

					events.append(
						SimulationEvent(
							kind='activity.started',
							tick=state.tick,
							actor_id=context.actor_id,
							subject_id=activity.id,
							data=activity.model_dump(mode='json'),
						)
					)
				except ActionRejected as error:
					decision.status = 'rejected'
					decision.error = str(error)

					if action_tool:
						action_tool.update(
							status='failed',
							error=str(error),
							result={'status': 'failed', 'reason': str(error)},
						)

					events.append(
						SimulationEvent(
							kind='activity.failed',
							tick=state.tick,
							actor_id=context.actor_id,
							subject_id=str(decision.id),
							data={'kind': draft.action.kind, 'reason': str(error)},
						)
					)
					activity = begin_action(state, context.actor_id, Action(kind='wait', seconds=1))
					events.append(
						SimulationEvent(
							kind='activity.started',
							tick=state.tick,
							actor_id=context.actor_id,
							subject_id=activity.id,
							data=activity.model_dump(mode='json'),
						)
					)

				for memory in draft.memories:
					row = Memory.objects.create(inhabitant_id=context.actor_id, tick=state.tick, **memory.model_dump())
					events.append(
						SimulationEvent(
							kind='memory.written',
							tick=state.tick,
							actor_id=context.actor_id,
							subject_id=str(row.id),
							data={**memory.model_dump(), 'private': True},
						)
					)

				for trace in decision.trace:
					if trace['tool'] == 'read_document' and 'result' in trace:
						events.append(
							SimulationEvent(
								kind='artifact.read',
								tick=state.tick,
								actor_id=context.actor_id,
								subject_id=trace['arguments']['artifact_id'],
								data={'version': trace['result']['version']},
							)
						)

			if not stale and not failed and decision.messages:
				conversation = retain_conversation(context.conversation, decision.messages, decision.trace, decision.id)
				Inhabitant.objects.filter(world=world, pk=context.actor_id).update(agent_context=conversation)

			decision.save(update_fields=('status', 'result', 'trace', 'messages', 'error', 'updated_ts'))
			if independent and failed and not stale:
				state.inhabitant(context.actor_id).wake_tick = state.tick + 10 * state.config.physics_hz
			events.append(
				SimulationEvent(
					kind=f'decision.{decision.status}',
					tick=state.tick,
					actor_id=context.actor_id,
					subject_id=str(decision.id),
					data={'result': decision.result, 'trace': decision.trace, 'error': decision.error},
				)
			)

		if failed and not stale and not independent:
			world.status = 'paused'
			world.error = next(outcome.error for outcome in outcomes if outcome.error)

		if outcomes:
			state.action_rotation += 1

		append_events(world, events)
		persist_state(world, state)
		save_checkpoint(world, state)

		return accepted


def complete_action_tools(world, events):
	for event in events:
		if event.kind not in ('activity.completed', 'activity.failed'):
			continue

		decision = world.decisions.filter(result__activity_id=event.subject_id).first()

		if decision is None:
			continue

		for entry in decision.trace:
			if entry.get('activity_id') == event.subject_id:
				entry['status'] = 'completed' if event.kind == 'activity.completed' else 'failed'
				entry['result'] = event.data
				entry['completed_tick'] = event.tick

				if event.kind == 'activity.failed':
					entry['error'] = event.data['reason']

		decision.save(update_fields=('trace', 'updated_ts'))


def decide_world(world_id, owner_step=False, driver=None):

	world = World.objects.get(id=world_id)

	if not owner_step and world.status != 'running':
		return True

	state = load_state(world)

	if not due_inhabitants(state):
		return True

	if driver is None:
		validate_live_configuration(state, due_inhabitants(state))

		if not asyncio.run(provider_available()):
			raise ValidationError('Authorize the selected model provider before enabling live decisions.')

	return execute_round(world_id, owner_step, driver)


def validate_live_configuration(state, agents):
	if not settings.WORLD_ALLOW_LIVE_AI or not state.config.allow_live_models:
		raise ValidationError('Live models are disabled. Enable the local server gate and this world explicitly.')

	if any(agent.driver != 'pydantic' or not agent.model_name for agent in agents):
		raise ValidationError('Each thinking inhabitant needs a supported driver and an explicit model name.')


def execute_round(world_id, owner_step, driver):
	revision, contexts, slots = prepare_round(world_id, owner_step, live=driver is None)

	if not contexts:
		return True

	async def collect():
		active_driver = None

		try:
			try:
				active_driver = driver if driver is not None else PydanticDriver(progress=record_progress)

				return await collect_decisions(contexts, active_driver, slots)
			finally:
				if isinstance(active_driver, PydanticDriver):
					await asyncio.wait_for(active_driver.provider.client.close(), timeout=5)
		except Exception as error:
			return [
				DecisionOutcome(context=context, error=f'Agent round failed ({type(error).__name__}).')
				for context in contexts
			]

	outcomes = asyncio.run(collect())

	return apply_round(world_id, revision, outcomes)


def record_progress(context, trace):

	close_old_connections()

	try:
		with world_lock(context.world_id, blocking=True):
			Decision.objects.filter(id=context.decision_id, world_id=context.world_id, status='thinking').update(
				trace=trace
			)
	finally:
		close_old_connections()

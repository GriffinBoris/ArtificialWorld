import asyncio
import json

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel
from worlds.agents import pydantic_driver
from worlds.agents.contracts import DecisionDraft, DriverReply
from worlds.agents.rounds import collect_decisions
from worlds.models import Decision
from worlds.services import runner as runner_module
from worlds.services.decisions import apply_round, prepare_round
from worlds.services.inhabitants import observation
from worlds.services.runner import database_call, WorldRunner
from worlds.services.state import append_events, load_state, persist_state
from worlds.services.worlds import set_world_status
from worlds.simulation.actions import Action
from worlds.simulation.contracts import SimulationEvent
from worlds.tests.test_decisions import configure_agents, FakeDriver


@pytest.mark.django_db(transaction=True)
def test_independent_sdk_turns_keep_tool_results_and_private_sessions(world, settings, monkeypatch):
	settings.WORLD_AI_PROVIDER = 'chatgpt'
	settings.WORLD_ALLOW_LIVE_AI = True
	state = configure_agents(world)
	state.config.allow_live_models = True
	persist_state(world, state)
	set_world_status(world.id, 'running')
	resumed = set()

	async def fake_model(messages, info):
		observed = [
			json.loads(part.content)
			for message in messages
			for part in message.parts
			if isinstance(part, UserPromptPart)
		]
		actor_id = observed[-1]['inhabitant_id']
		assert all(item['inhabitant_id'] == actor_id for item in observed)
		if any(
			isinstance(part, ToolReturnPart) and part.tool_name == 'wait'
			for message in messages
			for part in message.parts
		):
			resumed.add(actor_id)
			return ModelResponse(parts=[ToolCallPart('rest', {'seconds': 30}, tool_call_id=f'rest-{actor_id}')])
		return ModelResponse(parts=[ToolCallPart('wait', {'seconds': 0.1}, tool_call_id=f'wait-{actor_id}')])

	monkeypatch.setattr(pydantic_driver, 'OpenAIResponsesModel', lambda *args, **kwargs: FunctionModel(fake_model))

	async def run():
		runner = WorldRunner()
		try:
			await runner.step(world.id, advance=False)
			await asyncio.gather(*runner.tasks)
			await runner.step(world.id)
			await asyncio.gather(*runner.tasks)
			await runner.step(world.id, advance=False)
			assert not runner.tasks
		finally:
			await runner.close()

	asyncio.run(run())
	assert not world.decisions.exclude(status='completed').exists(), list(
		world.decisions.values('status', 'error', 'trace')
	)
	assert resumed == {agent.id for agent in state.inhabitants}
	assert world.decisions.filter(status='completed').count() == 4
	assert all(len(row.agent_context['turns']) == 2 for row in world.inhabitants.all())


@pytest.mark.django_db
def test_independent_claims_respect_capacity_and_never_duplicate_an_inhabitant(world):
	configure_agents(world)
	set_world_status(world.id, 'running')
	_, first, _ = prepare_round(world.id, independent=True, limit=1)
	_, second, _ = prepare_round(world.id, independent=True, limit=1)
	_, third, _ = prepare_round(world.id, independent=True, limit=1)
	assert len(first) == len(second) == 1
	assert first[0].actor_id != second[0].actor_id
	assert not third
	assert world.decisions.filter(status='thinking').count() == 2


@pytest.mark.django_db(transaction=True)
def test_slow_thinker_does_not_stop_physics_or_another_inhabitant(world):
	state = configure_agents(world)
	fast, slow = state.inhabitants
	set_world_status(world.id, 'running')

	async def run():
		release = asyncio.Event()
		started = asyncio.Event()

		class Driver:
			async def decide(self, context):
				if context.actor_id == slow.id:
					started.set()
					await release.wait()
				return DriverReply(DecisionDraft(action=Action(kind='rest', seconds=30)))

		runner = WorldRunner(Driver())
		try:
			await runner.step(world.id, advance=False)
			await asyncio.wait_for(started.wait(), timeout=2)
			for task, (_, _, context) in runner.tasks.items():
				if context.actor_id == fast.id:
					await task
			await runner.step(world.id)
			await runner.step(world.id)
			current = await asyncio.to_thread(database_call, lambda: load_state(type(world).objects.get(pk=world.pk)))
			assert current.tick == 120
			assert current.inhabitant(fast.id).activity.kind == 'rest'
			assert current.inhabitant(slow.id).activity is None
			assert len(runner.tasks) == 1
			release.set()
			await asyncio.gather(*runner.tasks)
			await runner.step(world.id, advance=False)
			current = await asyncio.to_thread(database_call, lambda: load_state(type(world).objects.get(pk=world.pk)))
			assert current.inhabitant(slow.id).activity.started_tick == 120
			assert not runner.tasks
		finally:
			await runner.close()

	asyncio.run(run())
	world.refresh_from_db()
	assert world.status == 'running'
	assert world.decisions.filter(status='completed').count() == 2


@pytest.mark.django_db(transaction=True)
def test_pause_cancels_thinking_and_releases_slots_without_losing_context(world):
	configure_agents(world)
	world.inhabitants.update(agent_context={'summary': ['Continue my life.']})
	set_world_status(world.id, 'running')

	async def run():
		class Driver:
			async def decide(self, context):
				await asyncio.Event().wait()

		runner = WorldRunner(Driver())
		try:
			await runner.step(world.id, advance=False)
			assert len(runner.tasks) == 2
			await asyncio.to_thread(database_call, set_world_status, world.id, 'paused')
			await runner.step(world.id, advance=False)
			assert not runner.tasks
		finally:
			await runner.close()

	asyncio.run(run())
	assert world.decisions.filter(status='stale').count() == 2
	assert all(row.agent_context == {'summary': ['Continue my life.']} for row in world.inhabitants.all())


@pytest.mark.django_db
def test_independent_failure_does_not_discard_other_decisions_or_pause_world(world):
	configure_agents(world)
	set_world_status(world.id, 'running')
	revision, contexts, slots = prepare_round(world.id, independent=True)
	outcomes = asyncio.run(collect_decisions(contexts, FakeDriver(), slots))
	outcomes[0].error = 'Model request failed.'
	assert not apply_round(world.id, revision, outcomes[:1], independent=True)
	assert apply_round(world.id, revision, outcomes[1:], independent=True)
	world.refresh_from_db()
	assert world.status == 'running'
	state = load_state(world)
	assert state.inhabitant(contexts[0].actor_id).wake_tick == 600
	assert state.inhabitant(contexts[1].actor_id).activity is not None


@pytest.mark.django_db
def test_pause_then_resume_still_invalidates_old_independent_results(world):
	configure_agents(world)
	set_world_status(world.id, 'running')
	revision, contexts, slots = prepare_round(world.id, independent=True)
	outcomes = asyncio.run(collect_decisions(contexts, FakeDriver(), slots))
	set_world_status(world.id, 'paused')
	set_world_status(world.id, 'running')
	assert not apply_round(world.id, revision, outcomes[:1], independent=True)
	assert world.decisions.filter(status='stale').count() == 1


@pytest.mark.django_db
def test_pending_messages_survive_thinking_and_more_than_one_observation_batch(world):
	state = configure_agents(world)
	speaker, listener = state.inhabitants
	set_world_status(world.id, 'running')
	revision, contexts, slots = prepare_round(world.id, independent=True)
	listener_context = next(context for context in contexts if context.actor_id == listener.id)
	world.refresh_from_db()
	append_events(
		world,
		[
			SimulationEvent(
				kind='message.spoken',
				tick=0,
				actor_id=speaker.id,
				data={'text': f'Message {index}', 'recipient_ids': [listener.id]},
			)
			for index in range(25)
		],
	)
	world.save(update_fields=('event_sequence',))
	(outcome,) = asyncio.run(collect_decisions([listener_context], FakeDriver(), slots))
	assert apply_round(world.id, revision, [outcome], independent=True)
	world.refresh_from_db()
	first = observation(world, listener.id)
	assert [message['text'] for message in first['messages']] == [f'Message {index}' for index in range(20)]
	state = load_state(world)
	state.inhabitant(listener.id).last_observation_sequence = first['observed_sequence']
	persist_state(world, state)
	second = observation(world, listener.id)
	assert [message['text'] for message in second['messages']] == [f'Message {index}' for index in range(20, 25)]
	assert not observation(world, speaker.id)['messages']


@pytest.mark.django_db
def test_nearby_status_shows_thinking_without_revealing_private_plans(world):
	state = load_state(world)
	first, second = state.inhabitants
	state.entity(second.id).position = state.entity(first.id).position
	persist_state(world, state)
	Decision.objects.create(
		world=world,
		inhabitant_id=second.id,
		tick=0,
		status='thinking',
		observation={},
		trace=[{'tool': 'share_plan', 'arguments': {'text': 'private-plan'}}],
	)
	seen = observation(world, first.id)
	assert seen['nearby_inhabitants'][0]['status'] == 'thinking'
	assert 'private-plan' not in str(seen)


@pytest.mark.django_db(transaction=True)
def test_provider_startup_failure_releases_claims_without_freezing_the_world(world, settings, monkeypatch):
	settings.WORLD_ALLOW_LIVE_AI = True
	state = configure_agents(world)
	state.config.allow_live_models = True
	persist_state(world, state)
	set_world_status(world.id, 'running')

	class BrokenProvider:
		def __init__(self, progress):
			raise RuntimeError('secret-provider-details')

	monkeypatch.setattr(runner_module, 'PydanticDriver', BrokenProvider)

	async def run():
		runner = WorldRunner()
		try:
			await runner.step(world.id, advance=False)
			await runner.step(world.id)
			assert not runner.tasks
		finally:
			await runner.close()

	asyncio.run(run())
	world.refresh_from_db()
	assert world.tick == 60
	assert world.status == 'running'
	assert world.decisions.filter(status='failed').count() == 2
	assert 'secret-provider-details' not in str(list(world.decisions.values()))

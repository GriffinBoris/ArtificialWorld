import asyncio
import json
from typing import get_args

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel
from worlds.agents import pydantic_driver
from worlds.agents.contracts import DecisionContext
from worlds.models import Decision, Inhabitant, Memory
from worlds.services.decisions import decide_world, record_progress
from worlds.services.editor import configure_agents
from worlds.services.profiles import inhabitant_profile
from worlds.services.recordings import save_checkpoint
from worlds.services.state import load_state, persist_state
from worlds.services.worlds import advance_world, create_world
from worlds.simulation.actions import Action


@pytest.mark.django_db(transaction=True)
def test_four_agents_think_concurrently_and_save_separate_contexts(monkeypatch, settings, owner):
	settings.WORLD_AI_PROVIDER = 'chatgpt'
	settings.WORLD_THINKING_SLOTS = 4
	world = create_world(owner, 'Concurrent lives', {'wind': [0, 0, 0]}, 4)
	state = load_state(world)

	for agent in state.inhabitants:
		agent.driver = 'pydantic'
		agent.model_name = 'test-only'

	persist_state(world, state)
	active = 0
	peak = 0

	async def fake_model(messages, info):
		nonlocal active, peak
		active += 1
		peak = max(peak, active)
		await asyncio.sleep(0.02)
		active -= 1
		observation = next(
			json.loads(part.content)
			for message in messages
			for part in message.parts
			if isinstance(part, UserPromptPart)
		)

		if any(isinstance(part, ToolReturnPart) for message in messages for part in message.parts):
			return ModelResponse(
				parts=[ToolCallPart('wait', {'seconds': 1}, tool_call_id=f'wait-{observation["name"]}')]
			)

		return ModelResponse(
			parts=[
				ToolCallPart('share_plan', {'text': f'I will explore as {observation["name"]}.'}, tool_call_id='plan')
			]
		)

	monkeypatch.setattr(pydantic_driver, 'OpenAIResponsesModel', lambda *args, **kwargs: FunctionModel(fake_model))
	driver = pydantic_driver.PydanticDriver(progress=record_progress)

	try:
		assert decide_world(world.id, owner_step=True, driver=driver)
		assert peak == 4
		world.refresh_from_db()
		assert world.tick == 0
		assert all(agent.activity.started_tick == 0 for agent in load_state(world).inhabitants)

		for row in world.inhabitants.all():
			assert row.agent_context['last_shared_plan'] == f'I will explore as {row.name}.'
			assert len(row.agent_context['turns']) == 1
	finally:
		asyncio.run(driver.provider.client.close())


def test_actual_pydantic_loop_uses_only_world_tools_and_validates_action(monkeypatch, settings):
	settings.WORLD_AI_PROVIDER = 'chatgpt'
	calls = []

	def fake_model(messages, info):
		calls.append(messages)
		assert not info.output_tools
		names = {tool.name for tool in info.function_tools}
		assert set(get_args(Action.model_fields['kind'].annotation)) <= names
		assert {'inspect', 'recall', 'remember', 'read_document', 'scratch', 'share_plan'} <= names
		if len(calls) == 1:
			return ModelResponse(
				parts=[ToolCallPart('inspect', {'object_id': 'nearby-object'}, tool_call_id='measurement')]
			)

		return ModelResponse(
			parts=[
				ToolCallPart('remember', {'text': 'The measured object has mass 2 kg.'}, tool_call_id='memory'),
				ToolCallPart('rest', {'seconds': 30}, tool_call_id='resting'),
			]
		)

	monkeypatch.setattr(pydantic_driver, 'OpenAIResponsesModel', lambda *args, **kwargs: FunctionModel(fake_model))
	context = DecisionContext(
		'round',
		'actor',
		'pydantic',
		'test-only',
		{'tick': 0, 'name': 'A'},
		[],
		{},
		measurements={'nearby-object': {'mass': 2}},
	)

	async def decide():
		driver = pydantic_driver.PydanticDriver()
		try:
			return await driver.decide(context)
		finally:
			await driver.provider.client.close()

	result = asyncio.run(decide())
	assert result.draft.action.kind == 'rest'
	assert result.draft.action.seconds == 30
	assert result.draft.memories[0].text == 'The measured object has mass 2 kg.'
	assert result.trace[0] == {'tool': 'inspect', 'arguments': {'object_id': 'nearby-object'}, 'result': {'mass': 2}}
	assert result.trace[-1] == {
		'tool': 'rest',
		'arguments': {'seconds': 30},
		'tool_call_id': 'resting',
		'status': 'pending',
	}
	assert len(calls) == 2


def test_shared_plan_is_published_before_the_model_returns_an_action(monkeypatch, settings):
	settings.WORLD_AI_PROVIDER = 'chatgpt'
	progress = []

	def fake_model(messages, info):
		if not progress:
			return ModelResponse(
				parts=[ToolCallPart('share_plan', {'text': 'I will search for food.'}, tool_call_id='visible-plan')]
			)
		assert progress[0][0] == 'round'
		assert progress[0][1][0]['arguments']['text'] == 'I will search for food.'
		return ModelResponse(parts=[ToolCallPart('wait', {'seconds': 1}, tool_call_id='waiting')])

	monkeypatch.setattr(pydantic_driver, 'OpenAIResponsesModel', lambda *args, **kwargs: FunctionModel(fake_model))
	context = DecisionContext('round', 'actor', 'pydantic', 'test-only', {'tick': 0, 'name': 'A'}, [], {})

	async def decide():
		driver = pydantic_driver.PydanticDriver(
			progress=lambda context, trace: progress.append((context.decision_id, trace))
		)
		try:
			return await driver.decide(context)
		finally:
			await driver.provider.client.close()

	result = asyncio.run(decide())
	assert result.draft.action.kind == 'wait'
	assert result.trace[-1]['tool'] == 'wait'
	assert result.trace[0] == progress[0][1][0]
	assert progress[-1][1][-1]['tool'] == 'wait'


@pytest.mark.parametrize('invalid_response', ['plain_text', 'invalid_id'])
def test_agent_retries_text_or_invalid_arguments_instead_of_acting(monkeypatch, settings, invalid_response):
	settings.WORLD_AI_PROVIDER = 'chatgpt'
	requests = []

	def fake_model(messages, info):
		requests.append(messages)

		if len(requests) == 1:
			if invalid_response == 'plain_text':
				return ModelResponse(parts=[TextPart('I am walking now.')])

			return ModelResponse(parts=[ToolCallPart('grasp', {'target_id': 'made-up-id'}, tool_call_id='invalid')])

		return ModelResponse(parts=[ToolCallPart('wait', {'seconds': 1}, tool_call_id='waiting')])

	monkeypatch.setattr(pydantic_driver, 'OpenAIResponsesModel', lambda *args, **kwargs: FunctionModel(fake_model))
	context = DecisionContext('round', 'actor', 'pydantic', 'test-only', {'tick': 0, 'name': 'A'}, [], {})

	async def decide():
		driver = pydantic_driver.PydanticDriver()
		try:
			return await driver.decide(context)
		finally:
			await driver.provider.client.close()

	reply = asyncio.run(decide())
	assert reply.draft.action.kind == 'wait'
	assert reply.trace[-1]['tool'] == 'wait'

	if invalid_response == 'invalid_id':
		assert reply.trace[0]['tool'] == 'grasp'
		assert 'error' in reply.trace[0]
	assert len(requests) == 2


def test_one_body_does_not_start_two_actions_from_one_model_response(monkeypatch, settings):
	settings.WORLD_AI_PROVIDER = 'chatgpt'

	def fake_model(messages, info):
		return ModelResponse(
			parts=[
				ToolCallPart('rest', {'seconds': 1}, tool_call_id='first'),
				ToolCallPart('rest', {'seconds': 2}, tool_call_id='second'),
			]
		)

	monkeypatch.setattr(pydantic_driver, 'OpenAIResponsesModel', lambda *args, **kwargs: FunctionModel(fake_model))
	context = DecisionContext('round', 'actor', 'pydantic', 'test-only', {'tick': 0, 'name': 'A'}, [], {})

	async def decide():
		driver = pydantic_driver.PydanticDriver()
		try:
			return await driver.decide(context)
		finally:
			await driver.provider.client.close()

	reply = asyncio.run(decide())
	assert reply.draft.action.kind == 'rest'
	assert len(reply.trace) == 2
	assert 'already starting' in reply.trace[0]['error']
	assert reply.trace[-1]['tool_call_id'] in ('first', 'second')


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('blocked', [False, True])
def test_walk_and_speech_tools_resume_with_persisted_outcomes(
	monkeypatch,
	settings,
	world,
	resource_simulation,
	blocked,
):
	settings.WORLD_AI_PROVIDER = 'chatgpt'
	state, actor, tree, _ = resource_simulation
	actor.driver = 'pydantic'
	actor.model_name = 'test-only'
	actor.wake_tick = 0
	persist_state(world, state)
	save_checkpoint(world, state)
	tool_results = []
	destination = list(tree.position) if blocked else [8, 0, 0]

	def fake_model(messages, info):
		results = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]

		if not results:
			return ModelResponse(
				parts=[
					ToolCallPart(
						'share_plan', {'text': 'Explore the tree, then talk about the river.'}, tool_call_id='plan'
					)
				]
			)

		result = results[-1]

		if result.tool_name == 'share_plan':
			return ModelResponse(parts=[ToolCallPart('walk', {'destination': destination}, tool_call_id='journey')])

		assert any(
			isinstance(part, ToolCallPart) and part.tool_name == 'share_plan' and 'river' in part.args_as_dict()['text']
			for message in messages
			for part in message.parts
		)
		tool_results.append(result)

		if result.tool_name == 'walk':
			assert result.tool_call_id == 'journey'
			assert result.content['status'] == ('failed' if blocked else 'arrived')

			if blocked:
				assert 'blocked' in result.content['reason']
			else:
				assert abs(result.content['position'][0] - 8) < 0.6
			return ModelResponse(
				parts=[
					ToolCallPart('remember', {'text': 'I tried exploring.'}, tool_call_id='memory'),
					ToolCallPart('speak', {'text': 'I finished exploring!'}, tool_call_id='greeting'),
				]
			)

		assert result.tool_name == 'speak'
		assert result.tool_call_id == 'greeting'
		assert result.content['status'] == 'completed'
		return ModelResponse(parts=[ToolCallPart('wait', {'seconds': 1}, tool_call_id='waiting')])

	monkeypatch.setattr(pydantic_driver, 'OpenAIResponsesModel', lambda *args, **kwargs: FunctionModel(fake_model))
	driver = pydantic_driver.PydanticDriver(progress=record_progress)

	try:
		assert decide_world(world.id, owner_step=True, driver=driver)
		decision = world.decisions.get(inhabitant_id=actor.id)
		assert decision.trace[-1]['status'] == 'running'
		assert 'result' not in decision.trace[-1]

		advance_world(world.id, seconds=2, owner_step=True)
		decision.refresh_from_db()

		if not blocked:
			assert decision.trace[-1]['status'] == 'running'
			assert 'result' not in decision.trace[-1]
			advance_world(world.id, seconds=30, owner_step=True)

		world.refresh_from_db()
		decision.refresh_from_db()
		assert decision.trace[-1]['result']['status'] == ('failed' if blocked else 'arrived')
		assert decision.trace[-1]['status'] == ('failed' if blocked else 'completed')
		assert load_state(world).inhabitant(actor.id).activity is None

		past = inhabitant_profile(world, actor.id, tick=0)['decisions'][0]['trace'][-1]
		assert past['status'] == 'running'
		assert 'result' not in past
		assert 'completed_tick' not in past

		Decision.objects.create(
			world=world, inhabitant_id=actor.id, tick=world.tick, observation={}, status='interrupted'
		)
		assert decide_world(world.id, owner_step=True, driver=driver)
		assert Memory.objects.get(inhabitant_id=actor.id).text == 'I tried exploring.'
		advance_world(world.id, seconds=2, owner_step=True)
		assert world.events.get(kind='message.spoken', actor_id=actor.id).data['text'] == 'I finished exploring!'

		assert decide_world(world.id, owner_step=True, driver=driver)
		assert [result.tool_name for result in tool_results] == ['walk', 'speak']
		assert len(Inhabitant.objects.get(pk=actor.id).agent_context['turns']) == 3
		configure_agents(world.id, [actor.id], 'pydantic', 'test-only', allow_live_models=False)
		pending = world.decisions.filter(result__action__kind='wait').get()
		assert pending.trace[-1]['result']['status'] == 'failed'
		assert 'settings changed' in pending.trace[-1]['result']['reason']
	finally:
		asyncio.run(driver.provider.client.close())

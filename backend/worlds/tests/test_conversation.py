import json

import pytest
from pydantic_ai.messages import (
	ModelRequest,
	ModelResponse,
	TextPart,
	ThinkingPart,
	ToolCallPart,
	ToolReturnPart,
	UserPromptPart,
)
from worlds.agents.conversation import (
	conversation_history,
	MAX_HISTORY_CHARACTERS,
	MAX_RECENT_TURNS,
	MAX_SUMMARY_CHARACTERS,
	public_messages,
	retain_conversation,
)
from worlds.models import Decision, Inhabitant
from worlds.serializers import WorldDetailSerializer
from worlds.services.decisions import prepare_round
from worlds.services.state import load_state, persist_state


def turn(index, text='Hello from a neighbor.'):
	parts = [
		UserPromptPart(
			json.dumps(
				{
					'tick': index,
					'messages': [
						{'tick': index, 'speaker_id': 'neighbor', 'text': text},
					],
				}
			)
		)
	]

	if index:
		parts.insert(0, ToolReturnPart('wait', {'status': 'completed'}, tool_call_id=f'call-{index - 1}'))

	return public_messages(
		[
			ModelRequest(parts=parts),
			ModelResponse(parts=[ToolCallPart('wait', {'seconds': 1}, tool_call_id=f'call-{index}')]),
		]
	)


def test_public_conversation_does_not_store_model_reasoning_or_provider_metadata():
	messages = public_messages(
		[
			ModelResponse(
				parts=[
					ThinkingPart('private-hidden-reasoning'),
					TextPart('unrequested-model-monologue'),
					ToolCallPart('speak', {'text': 'Hello!'}, tool_call_id='greeting'),
				],
				provider_name='provider-private-metadata',
			)
		]
	)
	encoded = json.dumps(messages)
	assert 'Hello!' in encoded
	assert 'private-hidden-reasoning' not in encoded
	assert 'unrequested-model-monologue' not in encoded
	assert 'provider-private-metadata' not in encoded


def test_invalid_arguments_from_an_earlier_retry_do_not_break_history():
	invalid = '{"destination": ['
	messages = public_messages([ModelResponse(parts=[ToolCallPart('walk', invalid, tool_call_id='invalid')])])
	assert conversation_history({'turns': [messages]})[0].parts[0].args == invalid


def test_compaction_keeps_recent_exchanges_and_a_bounded_factual_journal():
	conversation = {}

	for index in range(40):
		trace = [{'tool': 'wait', 'arguments': {'seconds': 1}, 'tool_call_id': f'call-{index}'}]

		if not index:
			trace.insert(0, {'tool': 'share_plan', 'arguments': {'text': 'I want to find berries and visit River.'}})

		conversation = retain_conversation(conversation, turn(index), trace, f'decision-{index}')

	assert len(conversation['turns']) == MAX_RECENT_TURNS
	assert len(json.dumps(conversation['turns'])) <= MAX_HISTORY_CHARACTERS
	assert sum(map(len, conversation['summary'])) <= MAX_SUMMARY_CHARACTERS
	assert any('Hello from a neighbor' in entry for entry in conversation['summary'])
	assert conversation['last_shared_plan'] == 'I want to find berries and visit River.'
	assert conversation['pending_decision_id'] == 'decision-39'
	known_calls = set()

	for message in conversation_history(conversation):
		for part in message.parts:
			if isinstance(part, ToolCallPart):
				known_calls.add(part.tool_call_id)
			elif isinstance(part, ToolReturnPart):
				assert part.tool_call_id in known_calls

	assert 'call-39' in known_calls
	assert 'call-0' not in known_calls


def test_one_oversized_turn_keeps_its_pending_call_and_compacts_the_old_observation():
	messages = turn(0, 'x' * (MAX_HISTORY_CHARACTERS + 1000))
	conversation = retain_conversation(
		{},
		messages,
		[
			{'tool': 'wait', 'arguments': {'seconds': 1}, 'tool_call_id': 'call-0'},
		],
		'decision-0',
	)
	assert len(json.dumps(conversation['turns'])) < MAX_HISTORY_CHARACTERS
	assert len(json.dumps(messages)) > MAX_HISTORY_CHARACTERS
	assert conversation_history(conversation)[-1].parts[0].tool_call_id == 'call-0'
	assert conversation['summary']


@pytest.mark.django_db
def test_existing_lives_bootstrap_context_without_sharing_private_plans(world):
	state = load_state(world)
	first, second = state.inhabitants

	for agent in state.inhabitants:
		agent.driver = 'pydantic'
		agent.model_name = 'test'

	persist_state(world, state)
	Decision.objects.create(
		world=world,
		inhabitant_id=first.id,
		tick=0,
		status='completed',
		observation={},
		trace=[
			{'tool': 'share_plan', 'arguments': {'text': 'My private berry plan.'}},
			{'tool': 'speak', 'arguments': {'text': 'I spoke about the river.'}, 'result': {'status': 'completed'}},
		],
	)
	Inhabitant.objects.filter(pk=second.id).update(agent_context={'summary': ['Another private life.'], 'turns': []})
	_, contexts, slots = prepare_round(world.id, owner_step=True)
	by_actor = {context.actor_id: context for context in contexts}
	assert slots == 4
	assert by_actor[first.id].observation['continuity']['last_shared_plan'] == 'My private berry plan.'
	assert 'Another private life' not in json.dumps(by_actor[first.id].conversation)
	assert 'My private berry plan' not in json.dumps(by_actor[second.id].conversation)
	assert 'Another private life' not in json.dumps(WorldDetailSerializer(world).data)

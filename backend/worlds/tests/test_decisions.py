import asyncio
import uuid

import pytest
from django.core.management import call_command
from pydantic_ai import ModelRetry
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, UserPromptPart
from rest_framework.exceptions import ValidationError
from worlds.agents.contracts import DecisionContext, DecisionDraft, DecisionFailed, DriverReply, PersonalMemory
from worlds.agents.conversation import public_messages
from worlds.agents.rounds import collect_decisions
from worlds.agents.tools import LocalTools
from worlds.models import Decision, Inhabitant, Memory
from worlds.services.decisions import apply_round, decide_world, prepare_round
from worlds.services.state import load_state, persist_state, WorldBusy
from worlds.services.worlds import advance_world, set_world_status
from worlds.simulation.actions import Action


class FakeDriver:
	def __init__(self, action=None, failure=False):
		self.action = action or Action(kind='rest', seconds=0.1)
		self.failure = failure
		self.active = 0
		self.peak_active = 0
		self.observed_ticks = []

	async def decide(self, context):
		self.active += 1
		self.peak_active = max(self.peak_active, self.active)
		self.observed_ticks.append(context.observation['tick'])
		await asyncio.sleep(0.01)
		self.active -= 1
		if self.failure:
			raise RuntimeError('secret-token-must-not-be-logged')
		return DriverReply(
			DecisionDraft(action=self.action, memories=[PersonalMemory(text='I chose to rest.')]),
			trace=[
				{
					'tool': self.action.kind,
					'arguments': self.action.model_dump(mode='json', exclude={'kind'}, exclude_unset=True),
					'tool_call_id': f'{context.decision_id}-action',
					'status': 'pending',
				}
			],
		)


def configure_agents(world):
	state = load_state(world)
	for agent in state.inhabitants:
		agent.driver = 'pydantic'
		agent.model_name = 'explicit-test-model'
	persist_state(world, state)
	return state


@pytest.mark.parametrize('slots', [2, 4])
def test_thinking_slots_collect_a_whole_round_before_returning(slots):
	contexts = [DecisionContext(str(index), str(index), 'pydantic', 'test', {'tick': 42}, [], {}) for index in range(6)]
	driver = FakeDriver()
	outcomes = asyncio.run(collect_decisions(contexts, driver, slots=slots))
	assert driver.peak_active == slots
	assert driver.active == 0
	assert [result.context.actor_id for result in outcomes] == [str(index) for index in range(6)]
	assert all(not result.error for result in outcomes)


@pytest.mark.django_db
@pytest.mark.parametrize('interruption', ['pause', 'provider_failure'])
def test_interrupted_round_does_not_advance_private_conversations(world, interruption):
	state = configure_agents(world)
	original = {'turns': [], 'summary': ['Keep exploring the river.']}
	world.inhabitants.update(agent_context=original)
	revision, contexts, slots = prepare_round(world.id, owner_step=True)
	outcomes = asyncio.run(collect_decisions(contexts, FakeDriver(), slots))

	for outcome in outcomes:
		call = outcome.reply.trace[-1]
		outcome.reply.messages = public_messages(
			[
				ModelRequest(parts=[UserPromptPart('{"tick":0}')]),
				ModelResponse(parts=[ToolCallPart(call['tool'], call['arguments'], tool_call_id=call['tool_call_id'])]),
			]
		)

	if interruption == 'pause':
		set_world_status(world.id, 'paused')
	else:
		outcomes[-1].error = 'Provider request failed.'

	assert not apply_round(world.id, revision, outcomes)
	assert all(Inhabitant.objects.get(pk=agent.id).agent_context == original for agent in state.inhabitants)
	assert not Memory.objects.exists()


def test_authentication_failure_explains_credential_checks_without_exposing_provider_details():
	class RejectedDriver:
		async def decide(self, context):
			raise DecisionFailed('ModelAuthenticationError', []) from RuntimeError('private-provider-token')

	context = DecisionContext('round', 'actor', 'pydantic', 'test', {'tick': 0}, [], {})
	(outcome,) = asyncio.run(collect_decisions([context], RejectedDriver(), slots=1))
	assert 'API key expiry' in outcome.error
	assert 'access to this model' in outcome.error
	assert 'private-provider-token' not in outcome.error


@pytest.mark.django_db
def test_decisions_do_not_age_the_world_and_actions_start_together(world):
	configure_agents(world)
	driver = FakeDriver()
	assert decide_world(world.id, owner_step=True, driver=driver)
	world.refresh_from_db()
	state = load_state(world)
	assert world.tick == 0
	assert driver.observed_ticks == [0, 0]
	assert [agent.activity.started_tick for agent in state.inhabitants] == [0, 0]
	assert world.decisions.filter(status='completed').count() == 2
	assert Memory.objects.count() == 2
	assert world.events.filter(kind='decision.observed').count() == 2
	advance_world(world.id, seconds=1, owner_step=True)
	world.refresh_from_db()
	assert world.tick == 6
	assert all(agent.activity is None for agent in load_state(world).inhabitants)


@pytest.mark.django_db
def test_provider_failure_pauses_without_aging_or_partial_actions(world):
	configure_agents(world)
	assert not decide_world(world.id, owner_step=True, driver=FakeDriver(failure=True))
	world.refresh_from_db()
	assert world.tick == 0
	assert world.status == 'paused'
	assert all(agent.activity is None for agent in load_state(world).inhabitants)
	assert not Memory.objects.exists()
	assert world.decisions.filter(status='failed').count() == 2
	assert 'secret-token' not in str(list(Decision.objects.values()))
	assert 'secret-token' not in str(list(world.events.values()))


@pytest.mark.django_db
def test_owner_pause_invalidates_in_flight_decisions(world):
	configure_agents(world)
	revision, contexts, slots = prepare_round(world.id, owner_step=True)
	with pytest.raises(WorldBusy):
		prepare_round(world.id, owner_step=True)
	with pytest.raises(ValidationError, match='waiting'):
		advance_world(world.id, owner_step=True)
	outcomes = asyncio.run(collect_decisions(contexts, FakeDriver(), slots))
	set_world_status(world.id, 'paused')
	assert not apply_round(world.id, revision, outcomes)
	world.refresh_from_db()
	assert all(agent.activity is None for agent in load_state(world).inhabitants)
	assert world.decisions.filter(status='stale').count() == 2
	assert not Memory.objects.exists()


@pytest.mark.django_db
def test_invalid_physical_action_records_rejection_and_short_wait(world):
	configure_agents(world)
	assert decide_world(world.id, owner_step=True, driver=FakeDriver(Action(kind='grasp', target_id=str(uuid.uuid4()))))
	world.refresh_from_db()
	assert world.decisions.filter(status='rejected').count() == 2
	assert all(agent.activity.kind == 'wait' for agent in load_state(world).inhabitants)
	assert all(decision.trace[-1]['status'] == 'failed' for decision in world.decisions.all())
	advance_world(world.id, seconds=1, owner_step=True)
	_, contexts, _ = prepare_round(world.id, owner_step=True)
	assert all(context.previous_tool['result']['status'] == 'failed' for context in contexts)
	assert all('not present' in context.previous_tool['result']['reason'] for context in contexts)


@pytest.mark.django_db
def test_live_inference_requires_both_explicit_gates(world, settings):
	configure_agents(world)
	settings.WORLD_ALLOW_LIVE_AI = False
	with pytest.raises(ValidationError, match='disabled'):
		decide_world(world.id, owner_step=True)
	settings.WORLD_ALLOW_LIVE_AI = True
	with pytest.raises(ValidationError, match='disabled'):
		decide_world(world.id, owner_step=True)
	assert not Decision.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_runner_restart_recovers_interrupted_round_without_advancing_time(world, settings, tmp_path):
	settings.TEMP_DIR = tmp_path
	configure_agents(world)
	prepare_round(world.id, owner_step=True)
	world.status = 'running'
	world.save(update_fields=('status',))
	call_command('run_worlds', once=True)
	world.refresh_from_db()
	assert world.status == 'paused'
	assert world.tick == 0
	assert world.decisions.filter(status='interrupted').count() == 2
	assert decide_world(world.id, owner_step=True, driver=FakeDriver())


def test_agent_tools_cannot_read_ungranted_documents_or_other_memories():
	context = DecisionContext(
		'decision', 'actor', 'pydantic', 'test', {'tick': 0, 'name': 'A'}, [{'text': 'my memory'}], {}
	)
	tools = LocalTools(context)
	assert tools.recall('other') == []
	with pytest.raises(ModelRetry, match='reading distance'):
		tools.read_document(str(uuid.uuid4()))
	assert tools.scratch('[{"put":"sum","value":{"op":"add","args":[2,3]}}]')['records'] == {'sum': 5}
	with pytest.raises(ModelRetry):
		tools.scratch('[{"exec":"read server files"}]')

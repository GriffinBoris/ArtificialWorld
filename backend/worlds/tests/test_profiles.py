import asyncio
from functools import partial

import pytest
from core.test_fixtures import TestFixtures
from django.urls import reverse
from pydantic_ai import ModelRetry
from worlds.agents.contracts import DecisionContext
from worlds.agents.tools import LocalTools
from worlds.models import Decision, Memory
from worlds.services.decisions import record_progress
from worlds.services.state import append_events, load_state
from worlds.services.worlds import advance_world
from worlds.simulation.contracts import SimulationEvent


@pytest.mark.django_db
def test_profile_contains_only_personal_memories_and_heard_conversation(client, world, owner):
	first, second = load_state(world).inhabitants
	Memory.objects.create(inhabitant_id=first.id, text='I found a berry bush.', tick=0)
	Memory.objects.create(inhabitant_id=second.id, text='A private second memory.', tick=0)
	append_events(
		world,
		[
			SimulationEvent(
				kind='message.spoken',
				tick=0,
				actor_id=first.id,
				data={
					'speaker_name': first.name,
					'text': 'Hello there!',
					'recipient_ids': [second.id],
					'position': [0, 0, 0],
				},
			),
			SimulationEvent(
				kind='message.spoken',
				tick=0,
				actor_id=second.id,
				data={
					'speaker_name': second.name,
					'text': 'I can hear you.',
					'recipient_ids': [first.id],
					'position': [0, 0, 0],
				},
			),
			SimulationEvent(
				kind='message.spoken',
				tick=0,
				actor_id=second.id,
				data={
					'speaker_name': second.name,
					'text': 'Too far away.',
					'recipient_ids': [],
					'position': [100, 100, 0],
				},
			),
		],
	)
	world.save(update_fields=('event_sequence',))
	client.force_login(owner)
	response = client.get(reverse('worlds:inhabitant-profile', kwargs={'world_id': world.id, 'actor_id': first.id}))
	assert response.status_code == 200
	profile = response.json()
	assert profile['inhabitant']['name'] == first.name
	assert [memory['text'] for memory in profile['memories']] == ['I found a berry bush.']
	assert [message['text'] for message in profile['messages']] == ['Hello there!', 'I can hear you.']
	assert profile['inhabitant']['body']['health'] > 0
	assert len(client.get(reverse('worlds:world-messages', kwargs={'world_id': world.id})).json()) == 3


@pytest.mark.django_db
def test_replay_profile_does_not_show_future_messages_memories_or_decisions(client, world, owner):
	actor = load_state(world).inhabitants[0]
	advance_world(world.id, 2, owner_step=True)
	world.refresh_from_db()
	Memory.objects.create(inhabitant_id=actor.id, text='I remember saying hello.', tick=world.tick)
	Decision.objects.create(
		world=world, inhabitant_id=actor.id, tick=world.tick, status='completed', observation={'tick': world.tick}
	)
	client.force_login(owner)
	url = reverse('worlds:inhabitant-profile', kwargs={'world_id': world.id, 'actor_id': actor.id})
	live = client.get(url).json()
	assert live['messages'] and live['memories'] and live['decisions']
	past = client.get(url, {'tick': 0}).json()
	assert past['recorded_tick'] == 0
	assert past['messages'] == past['memories'] == past['decisions'] == []
	assert client.get(url, {'tick': world.tick + 1}).status_code == 400


@pytest.mark.django_db
def test_profile_is_scoped_to_world_and_owner(client, world, owner):
	actor = load_state(world).inhabitants[0]
	url = reverse('worlds:inhabitant-profile', kwargs={'world_id': world.id, 'actor_id': actor.id})
	assert client.get(url).status_code == 403
	client.force_login(TestFixtures.create_user())
	assert client.get(url).status_code == 404
	client.force_login(owner)
	assert (
		client.get(
			reverse('worlds:inhabitant-profile', kwargs={'world_id': world.id, 'actor_id': world.id})
		).status_code
		== 404
	)


@pytest.mark.django_db(transaction=True)
def test_shared_plans_persist_while_decision_is_still_thinking(world, client, owner):
	actor = load_state(world).inhabitants[0]
	decision = Decision.objects.create(
		world=world, inhabitant_id=actor.id, tick=0, status='thinking', observation={'tick': 0}
	)
	context = DecisionContext(str(decision.id), actor.id, 'pydantic', 'test', {'tick': 0, 'name': actor.name}, [], {})
	context.world_id = str(world.id)
	tools = LocalTools(context, progress=partial(record_progress, context))
	asyncio.run(asyncio.to_thread(tools.share_plan, 'I will look for food near the clearing.'))
	client.force_login(owner)
	response = client.get(reverse('worlds:inhabitant-profile', kwargs={'world_id': world.id, 'actor_id': actor.id}))
	visible = response.json()['decisions'][0]
	assert visible['status'] == 'thinking'
	assert visible['trace'][0]['arguments']['text'] == 'I will look for food near the clearing.'
	assert visible['result'] is None
	decision.status = 'completed'
	decision.save(update_fields=('status',))
	asyncio.run(asyncio.to_thread(tools.share_plan, 'A late update must not change a completed decision.'))
	decision.refresh_from_db()
	assert len(decision.trace) == 1


@pytest.mark.parametrize('text', ['', ' ', 'x' * 1201])
def test_shared_plan_requires_a_short_visible_statement(text):
	context = DecisionContext('decision', 'actor', 'pydantic', 'test', {'tick': 0, 'name': 'A'}, [], {})
	tools = LocalTools(context)
	with pytest.raises(ModelRetry, match='short plan'):
		tools.share_plan(text)
	assert tools.trace == []

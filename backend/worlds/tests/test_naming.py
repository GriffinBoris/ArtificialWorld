import uuid

import pytest
from django.urls import reverse
from pydantic import ValidationError
from worlds.models import Inhabitant
from worlds.services.inhabitants import submit_action
from worlds.services.recordings import replay_state
from worlds.services.state import load_state
from worlds.services.worlds import advance_world
from worlds.simulation.actions import Action, ActionRejected
from worlds.simulation.contracts import InhabitantState
from worlds.simulation.naming import choose_name
from worlds.simulation.perception import observe


def test_repeated_parent_and_self_naming_preserves_identity(resource_simulation):
	state, parent, _, _ = resource_simulation
	child_entity = state.entity(parent.id).model_copy(deep=True)
	child_entity.id = str(uuid.uuid4())
	child_entity.name = 'Child 2'
	child = InhabitantState(id=child_entity.id, name=child_entity.name, parents=[parent.id])
	state.entities.append(child_entity)
	state.inhabitants.append(child)
	event = choose_name(state, parent, Action(kind='name_child', target_id=child.id, text='Juniper'))
	assert child.name == child_entity.name == 'Juniper'
	assert child.parent_named and not child.self_named
	assert event.data == {'previous_name': 'Child 2', 'name': 'Juniper', 'self_chosen': False}
	assert event.subject_id == child.id
	choose_name(state, parent, Action(kind='name_child', target_id=child.id, text='Willow'))
	assert child.name == child_entity.name == 'Willow'
	choose_name(state, child, Action(kind='name_self', text='  River  '))
	assert child.name == child_entity.name == 'River'
	assert child.self_named
	choose_name(state, parent, Action(kind='name_child', target_id=child.id, text='Another name'))
	choose_name(state, child, Action(kind='name_self', text='Sky'))
	assert child.name == child_entity.name == 'Sky'
	assert child.id == child_entity.id == event.subject_id
	assert observe(state, parent.id)['children'][0]['self_named'] is True
	assert observe(state, child.id)['parents'] == [parent.id]


def test_naming_an_unrelated_inhabitant_is_rejected(resource_simulation):
	state, actor, _, _ = resource_simulation
	other = actor.model_copy(deep=True, update={'id': str(uuid.uuid4())})
	state.inhabitants.append(other)
	with pytest.raises(ActionRejected, match='own child'):
		choose_name(state, actor, Action(kind='name_child', target_id=other.id, text='Unwanted'))
	assert other.name == actor.name
	assert not other.parent_named


def test_names_can_be_shared_and_do_not_require_a_parental_choice(resource_simulation):
	state, actor, _, _ = resource_simulation
	entity = state.entity(actor.id).model_copy(deep=True, update={'id': str(uuid.uuid4())})
	child = InhabitantState(id=entity.id, name='Child', parents=[actor.id])
	state.entities.append(entity)
	state.inhabitants.append(child)
	choose_name(state, actor, Action(kind='name_self', text='River'))
	choose_name(state, child, Action(kind='name_self', text='River'))
	assert actor.name == child.name == 'River'
	assert not child.parent_named
	choose_name(state, actor, Action(kind='name_child', target_id=child.id, text='Parent choice'))
	assert child.name == 'Parent choice'
	assert child.parent_named and child.self_named


@pytest.mark.parametrize('name', ['', '   ', 'x' * 121])
def test_naming_requires_a_nonempty_bounded_name(name):
	with pytest.raises(ValidationError, match='1 to 120'):
		Action(kind='name_self', text=name)


@pytest.mark.django_db
def test_name_action_persists_and_replay_keeps_the_old_name(client, world, owner):
	actor = load_state(world).inhabitants[0]
	context = {'turns': [], 'summary': ['Keep exploring the river.']}
	Inhabitant.objects.filter(pk=actor.id).update(agent_context=context)
	original = actor.name
	submit_action(world.id, actor.id, Action(kind='name_self', text='Moss'))
	advance_world(world.id, 1, owner_step=True)
	world.refresh_from_db()
	row = Inhabitant.objects.get(pk=actor.id)
	assert row.name == row.entity.name == 'Moss'
	assert row.state['self_named'] is True
	event = world.events.get(kind='inhabitant.named')
	assert event.data['previous_name'] == original
	assert event.actor_id == event.subject_id == actor.id
	assert replay_state(world, 0).inhabitant(actor.id).name == original
	assert replay_state(world, world.tick).inhabitant(actor.id).name == 'Moss'
	client.force_login(owner)
	profile = client.get(
		reverse('worlds:inhabitant-profile', kwargs={'world_id': world.id, 'actor_id': actor.id})
	).json()
	assert profile['inhabitant']['name'] == 'Moss'
	assert any(item['kind'] == 'inhabitant.named' for item in profile['history'])

	first_tick = world.tick
	submit_action(world.id, actor.id, Action(kind='name_self', text='River'))
	advance_world(world.id, 1, owner_step=True)
	world.refresh_from_db()
	row.refresh_from_db()
	assert row.name == row.entity.name == 'River'
	assert row.agent_context == context
	assert replay_state(world, first_tick).inhabitant(actor.id).name == 'Moss'
	assert replay_state(world, world.tick).inhabitant(actor.id).name == 'River'
	assert list(
		world.events.filter(kind='inhabitant.named').order_by('sequence').values_list('data__name', flat=True)
	) == ['Moss', 'River']

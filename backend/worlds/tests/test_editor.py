import asyncio
import stat

import pytest
from core.test_fixtures import TestFixtures
from django.urls import reverse
from pydantic_ai.providers.openai_chatgpt import OpenAIChatGPTCredentials
from worlds.agents.credentials import SubscriptionCredentials
from worlds.services.recordings import replay_state
from worlds.services.state import load_state


@pytest.mark.django_db
def test_editor_records_placed_part_and_checkpoint(client, world, owner):
	client.force_login(owner)
	response = client.post(
		reverse('worlds:world-edit', kwargs={'world_id': world.id}),
		{'edit': {'kind': 'create', 'part': {'name': 'Editor block', 'position': [0, 0, 15]}}},
		content_type='application/json',
	)
	assert response.status_code == 200
	world.refresh_from_db()
	part = world.entities.get(name='Editor block')
	assert part.state['mass'] == 75
	assert world.events.get(kind='editor.intervened').subject_id == str(part.id)
	assert replay_state(world, 0).entity(str(part.id)).name == 'Editor block'


@pytest.mark.django_db
def test_editor_rejects_invalid_geometry_before_persistence(client, world, owner):
	client.force_login(owner)
	response = client.post(
		reverse('worlds:world-edit', kwargs={'world_id': world.id}),
		{'edit': {'kind': 'create', 'part': {'dimensions': [-1, 1, 1]}}},
		content_type='application/json',
	)
	assert response.status_code == 400
	assert not world.events.filter(kind='editor.intervened').exists()


@pytest.mark.django_db
def test_editor_requires_paused_world(client, world, owner):
	client.force_login(owner)
	world.status = 'running'
	world.save()
	response = client.post(
		reverse('worlds:world-edit', kwargs={'world_id': world.id}),
		{'edit': {'kind': 'create', 'part': {}}},
		content_type='application/json',
	)
	assert response.status_code == 400
	assert not world.events.filter(kind='editor.intervened').exists()


@pytest.mark.django_db
def test_agent_configuration_is_explicit_and_does_not_make_model_calls(client, world, owner):
	client.force_login(owner)
	actors = [str(actor.pk) for actor in world.inhabitants.all()]
	response = client.post(
		reverse('worlds:world-agent-settings', kwargs={'world_id': world.id}),
		{'actor_ids': actors, 'driver': 'pydantic', 'model_name': 'chosen-model', 'allow_live_models': False},
		content_type='application/json',
	)
	assert response.status_code == 200
	world.refresh_from_db()
	assert all(
		actor.driver == 'pydantic' and actor.model_name == 'chosen-model' for actor in load_state(world).inhabitants
	)
	assert world.decisions.count() == 0
	assert world.configuration['allow_live_models'] is False


@pytest.mark.django_db
@pytest.mark.parametrize('route', ['world-agent-settings', 'world-edit'])
def test_other_owner_cannot_configure_or_edit(client, world, route):
	client.force_login(TestFixtures.create_user())
	assert (
		client.post(
			reverse(f'worlds:{route}', kwargs={'world_id': world.id}), {}, content_type='application/json'
		).status_code
		== 404
	)


@pytest.mark.django_db
def test_other_owner_cannot_inspect_private_world_records(client, world):
	client.force_login(TestFixtures.create_user())
	assert (
		client.get(
			reverse('worlds:world-inspect', kwargs={'world_id': world.id, 'entity_id': world.inhabitants.first().pk})
		).status_code
		== 404
	)


def test_subscription_credentials_are_private_and_refreshed_atomically(settings, tmp_path):
	settings.TEMP_DIR = tmp_path
	source = SubscriptionCredentials()
	credentials = OpenAIChatGPTCredentials(
		client_id='test-client',
		access_token='fake-access',
		refresh_token='fake-refresh',
		scope='chatgpt.tokens.use.direct',
	)
	asyncio.run(source.save(credentials))
	assert stat.S_IMODE(source.directory.stat().st_mode) == 0o700
	assert stat.S_IMODE(source.path.stat().st_mode) == 0o600
	assert asyncio.run(source.load()).access_token == 'fake-access'
	credentials.access_token = 'fake-refreshed-access'
	asyncio.run(source.save(credentials))
	assert asyncio.run(source.load()).access_token == 'fake-refreshed-access'
	assert [path.name for path in source.directory.iterdir()] == ['chatgpt.json']

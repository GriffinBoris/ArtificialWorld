import asyncio
import json
import subprocess

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from worlds.agents import providers, pydantic_driver
from worlds.agents.contracts import DecisionContext
from worlds.agents.providers import create_provider, OPENCODE_GO_BASE_URL, opencode_key, provider_available


@pytest.fixture(autouse=True)
def no_local_credential_export(monkeypatch):
	monkeypatch.setattr(providers.shutil, 'which', lambda name: None)


def test_opencode_v2_reads_only_the_active_go_credential(settings, monkeypatch):
	settings.OPENCODE_GO_API_KEY = ''
	monkeypatch.setattr(providers.shutil, 'which', lambda name: '/cli/opencode')

	def export(command, **options):
		assert command == ['/cli/opencode', 'auth', 'export', 'opencode-go']
		assert options == {'capture_output': True, 'check': False, 'text': True, 'timeout': 10}
		return subprocess.CompletedProcess(
			command,
			0,
			stdout=json.dumps(
				[
					{'integrationID': 'opencode-go', 'active': False, 'value': {'type': 'key', 'key': 'old-key'}},
					{'integrationID': 'opencode-go', 'active': True, 'value': {'type': 'key', 'key': 'current-key'}},
				]
			),
		)

	monkeypatch.setattr(providers.subprocess, 'run', export)
	assert opencode_key() == 'current-key'
	settings.OPENCODE_GO_API_KEY = 'override'
	assert opencode_key() == 'override'


def test_failed_credential_export_does_not_expose_secret_output(settings, monkeypatch):
	settings.OPENCODE_GO_API_KEY = ''
	monkeypatch.setattr(providers.shutil, 'which', lambda name: '/cli/opencode')
	monkeypatch.setattr(
		providers.subprocess,
		'run',
		lambda *args, **kwargs: subprocess.CompletedProcess(
			args[0],
			1,
			stdout='private-key',
			stderr='private-key',
		),
	)
	with pytest.raises(ImproperlyConfigured, match='could not export') as failure:
		opencode_key()
	assert 'private-key' not in str(failure.value)


def test_opencode_go_uses_only_its_local_api_key_and_env_override(settings, tmp_path, monkeypatch):
	settings.WORLD_AI_PROVIDER = 'opencode-go'
	settings.OPENCODE_GO_API_KEY = ''
	monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
	directory = tmp_path / 'opencode'
	directory.mkdir()
	path = directory / 'auth.json'
	path.write_text(json.dumps({'unrelated': {'type': 'api', 'key': 'do-not-use'}}))
	assert opencode_key() is None
	assert asyncio.run(provider_available()) is False
	with pytest.raises(ImproperlyConfigured, match='OPENCODE_GO_API_KEY'):
		create_provider()
	path.write_text(json.dumps({'opencode': {'type': 'api', 'key': 'console-test-key'}}))
	assert opencode_key() == 'console-test-key'
	path.write_text(
		json.dumps(
			{
				'opencode': {'type': 'api', 'key': 'console-test-key'},
				'opencode-go': {'type': 'api', 'key': 'go-test-key'},
			}
		)
	)
	assert opencode_key() == 'go-test-key'
	settings.OPENCODE_GO_API_KEY = 'env-test-key'
	assert opencode_key() == 'env-test-key'
	assert asyncio.run(provider_available()) is True
	provider = create_provider()
	assert str(provider.client.base_url) == f'{OPENCODE_GO_BASE_URL}/'
	asyncio.run(provider.client.close())
	assert provider.client.is_closed()


def test_opencode_driver_supplies_honest_client_identity_and_stable_session(settings, monkeypatch):
	settings.WORLD_AI_PROVIDER = 'opencode-go'
	settings.OPENCODE_GO_API_KEY = 'fake-test-key'
	settings_seen = []

	def fake_model(messages, info):
		settings_seen.append(info.model_settings)
		return ModelResponse(parts=[ToolCallPart('name_self', {'text': 'Moss'}, tool_call_id='choice')])

	monkeypatch.setattr(pydantic_driver, 'OpenAIChatModel', lambda *args, **kwargs: FunctionModel(fake_model))
	context = DecisionContext(
		'first-round', 'stable-inhabitant-id', 'pydantic', 'test-model', {'tick': 0, 'name': 'Inhabitant 1'}, [], {}
	)

	async def decide():
		driver = pydantic_driver.PydanticDriver()
		try:
			first = await driver.decide(context)
			context.decision_id = 'second-round'
			await driver.decide(context)
			return first
		finally:
			await driver.provider.client.close()

	assert asyncio.run(decide()).draft.action.text == 'Moss'
	assert len(settings_seen) == 2
	for entry in settings_seen:
		assert entry['extra_headers'] == {
			'User-Agent': 'ArtificialWorld/0.1',
			'x-opencode-session': 'stable-inhabitant-id',
		}


@pytest.mark.django_db
def test_provider_availability_never_returns_credentials(client, world, owner, settings):
	settings.WORLD_AI_PROVIDER = 'opencode-go'
	settings.OPENCODE_GO_API_KEY = 'private-test-key'
	client.force_login(owner)
	response = client.get(reverse('worlds:world-agent-settings', kwargs={'world_id': world.id}))
	assert response.status_code == 200
	assert response.json()['provider'] == 'opencode-go'
	assert response.json()['subscription_authorized'] is True
	assert 'private-test-key' not in response.content.decode()
	assert response.json()['thinking_slots'] == settings.WORLD_THINKING_SLOTS
	assert set(response.json()) == {
		'provider',
		'subscription_authorized',
		'server_enabled',
		'supported_drivers',
		'thinking_slots',
	}

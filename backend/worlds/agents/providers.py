import json
import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openai_chatgpt import OpenAIChatGPTProvider
from worlds.agents.credentials import SubscriptionCredentials

OPENCODE_GO_BASE_URL = 'https://opencode.ai/inference/go/openai/v1'


def opencode_key():
	if settings.OPENCODE_GO_API_KEY:
		return settings.OPENCODE_GO_API_KEY

	if executable := shutil.which('opencode'):
		try:
			result = subprocess.run(
				[executable, 'auth', 'export', 'opencode-go'],
				capture_output=True,
				check=False,
				text=True,
				timeout=10,
			)
		except (OSError, subprocess.TimeoutExpired):
			raise ImproperlyConfigured(
				'Could not read the OpenCode Go credential from the local OpenCode app.'
			) from None

		if result.returncode:
			raise ImproperlyConfigured('OpenCode could not export its Go credential. Check your OpenCode connection.')

		credentials = [
			entry['value']
			for entry in json.loads(result.stdout)
			if entry['integrationID'] == 'opencode-go' and entry['active']
		]

		if not credentials:
			return None

		if len(credentials) != 1:
			raise ImproperlyConfigured(
				'OpenCode returned multiple active Go credentials. Select one account in OpenCode.'
			)

		(credential,) = credentials
		return credential['key'] if credential['type'] == 'key' else None

	path = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'opencode' / 'auth.json'

	if not path.exists():
		return None

	auth = json.loads(path.read_text())

	credential = auth.get('opencode-go') or auth.get('opencode')

	if credential is None or credential['type'] != 'api':
		return None

	return credential['key']


async def provider_available():
	if settings.WORLD_AI_PROVIDER == 'opencode-go':
		return bool(opencode_key())

	if settings.WORLD_AI_PROVIDER == 'chatgpt':
		credentials = await SubscriptionCredentials().load()

		return credentials is not None and credentials.plan_usage_granted

	raise ImproperlyConfigured('WORLD_AI_PROVIDER must be opencode-go or chatgpt.')


def create_provider():
	if settings.WORLD_AI_PROVIDER == 'opencode-go':
		key = opencode_key()

		if not key:
			raise ImproperlyConfigured('Connect OpenCode Go locally or set OPENCODE_GO_API_KEY before enabling models.')

		return OpenAIProvider(base_url=OPENCODE_GO_BASE_URL, api_key=key)

	if settings.WORLD_AI_PROVIDER == 'chatgpt':
		return OpenAIChatGPTProvider(credential_source=SubscriptionCredentials())

	raise ImproperlyConfigured('WORLD_AI_PROVIDER must be opencode-go or chatgpt.')

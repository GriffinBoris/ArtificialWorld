import json
import os
import tempfile
from dataclasses import asdict

from django.conf import settings
from pydantic_ai.providers.openai_chatgpt import OpenAIChatGPTCredentials, OpenAIChatGPTCredentialSource


class SubscriptionCredentials(OpenAIChatGPTCredentialSource):
	def __init__(self):
		self.directory = settings.TEMP_DIR / 'agent-credentials'
		self.path = self.directory / 'chatgpt.json'

	async def load(self):
		if not self.path.exists():
			return None

		return OpenAIChatGPTCredentials(**json.loads(self.path.read_text()))

	async def save(self, credentials: OpenAIChatGPTCredentials):
		self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
		self.directory.chmod(0o700)

		with tempfile.NamedTemporaryFile(mode='w', dir=self.directory, delete=False) as temporary:
			try:
				os.chmod(temporary.name, 0o600)
				json.dump(asdict(credentials), temporary)
				temporary.flush()
				os.fsync(temporary.fileno())
				os.replace(temporary.name, self.path)
			finally:
				if os.path.exists(temporary.name):
					os.unlink(temporary.name)

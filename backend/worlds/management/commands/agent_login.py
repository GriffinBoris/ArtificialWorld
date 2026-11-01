import asyncio
import uuid
import webbrowser

from django.core.management.base import BaseCommand, CommandError
from pydantic_ai.providers.openai_chatgpt import OpenAIChatGPTOAuthFlow
from worlds.agents.credentials import SubscriptionCredentials


class Command(BaseCommand):
	help = 'Sign this local application in to ChatGPT. This command does not run inference.'

	def handle(self, *args, **options):
		try:
			asyncio.run(self.login())
		except CommandError:
			raise
		except Exception as error:
			message = (
				f'Sign-in failed ({type(error).__name__}). '
				'Check your browser and local callback port 1455, then try again.'
			)
			raise CommandError(message) from None

	async def login(self):
		source = SubscriptionCredentials()
		previous = await source.load()
		flow = OpenAIChatGPTOAuthFlow(
			app_name='Artificial World',
			host_id=f'urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, str(source.directory))}',
			client_id=previous.client_id if previous else None,
			id_token_hint=previous.id_token if previous else None,
		)
		self.stdout.write(
			'Opening ChatGPT authorization in your browser. Tokens stay in the ignored local credential store.'
		)

		if not webbrowser.open(flow.authorization_url()):
			raise CommandError('The browser could not open. Configure a default browser and run agent_login again.')

		credentials = await asyncio.wait_for(flow.exchange_code_from_callback(), timeout=300)

		if not credentials.plan_usage_granted:
			raise CommandError('Plan usage was not granted. No inference is enabled.')

		await source.save(credentials)
		self.stdout.write(
			self.style.SUCCESS(
				'Subscription authorization saved. Live model calls remain off until explicitly enabled for a world.'
			)
		)

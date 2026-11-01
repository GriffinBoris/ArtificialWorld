import asyncio
import fcntl
import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError
from worlds.models import World
from worlds.services.runner import database_call, WorldRunner
from worlds.services.state import WorldBusy

logger = logging.getLogger(__name__)


class Command(BaseCommand):
	help = 'Advance running local worlds. Scripted inhabitants do not make model calls.'

	def add_arguments(self, parser):
		parser.add_argument('--once', action='store_true')

	def handle(self, *args, **options):
		settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)

		with (settings.TEMP_DIR / 'world-runner.lock').open('a') as lock:
			try:
				fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
			except BlockingIOError as error:
				raise CommandError('A world runner is already active.') from error

			try:
				World.objects.filter(status='running').update(
					status='paused', error='Runner restarted; resume the world when ready.'
				)
				World.objects.filter(decisions__status='thinking').update(
					status='paused', error='Runner interrupted an agent round. Resume to start a new round.'
				)

				for world in World.objects.filter(decisions__status='thinking').distinct():
					world.decisions.filter(status='thinking').update(
						status='interrupted', error='Runner restarted before this decision completed.'
					)

				asyncio.run(self.run(options['once']))

			except KeyboardInterrupt:
				self.stdout.write('World runner stopped. Completed steps are saved.')

	async def run(self, once):
		runner = WorldRunner()
		next_step = time.monotonic()

		try:
			while True:
				started = time.monotonic()
				advance = started >= next_step
				world_ids = await asyncio.to_thread(database_call, self.world_ids)

				for world_id in world_ids:
					try:
						await runner.step(world_id, advance=advance)
					except WorldBusy:
						continue
					except ValidationError as error:
						await asyncio.to_thread(database_call, self.pause, world_id, str(error.detail)[:1000])
					except Exception as error:
						logger.exception(
							'World runner paused a failed step (%s)',
							type(error).__name__,
							extra={'world_id': str(world_id)},
						)
						await asyncio.to_thread(
							database_call,
							self.pause,
							world_id,
							f'Step failed ({type(error).__name__}). Check the local agent and world configuration.',
						)

				if once:
					return
				if advance:
					next_step = max(time.monotonic(), started + 1)
				await asyncio.sleep(0.1)
		finally:
			await runner.close()

	def world_ids(self):
		return list(World.objects.filter(status='running').values_list('id', flat=True)) + list(
			World.objects.exclude(status='running')
			.filter(decisions__status='thinking')
			.distinct()
			.values_list('id', flat=True)
		)

	def pause(self, world_id, error):
		World.objects.filter(id=world_id).update(status='paused', error=error)

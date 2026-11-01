import asyncio

from django.conf import settings
from django.db import close_old_connections
from worlds.agents.contracts import DecisionOutcome
from worlds.agents.pydantic_driver import PydanticDriver
from worlds.agents.rounds import collect_decisions
from worlds.models import World
from worlds.services.decisions import apply_round, prepare_round, record_progress
from worlds.services.state import WorldBusy
from worlds.services.worlds import advance_world, set_world_status

SHUTDOWN_ATTEMPTS = 50


def database_call(function, *args, **kwargs):
	close_old_connections()
	try:
		return function(*args, **kwargs)
	finally:
		close_old_connections()


class WorldRunner:
	def __init__(self, driver=None):
		self.driver = driver
		self.tasks = {}

	async def step(self, world_id, advance=True):
		running = await asyncio.to_thread(database_call, World.objects.filter(id=world_id, status='running').exists)

		for task, (active_world, revision, context) in list(self.tasks.items()):
			if active_world != world_id:
				continue
			if task.cancelled():
				outcome = DecisionOutcome(context=context, error='World paused before this decision completed.')
			elif task.done():
				(outcome,) = task.result()
			elif not running:
				task.cancel()
				await asyncio.gather(task, return_exceptions=True)
				outcome = DecisionOutcome(context=context, error='World paused before this decision completed.')
			else:
				continue

			await asyncio.to_thread(database_call, apply_round, world_id, revision, [outcome], independent=True)
			del self.tasks[task]

		if not running:
			return

		if advance:
			await asyncio.to_thread(database_call, advance_world, world_id, independent=True)

		capacity = settings.WORLD_THINKING_SLOTS - len(self.tasks)
		if capacity <= 0:
			return

		revision, contexts, _ = await asyncio.to_thread(
			database_call,
			prepare_round,
			world_id,
			live=self.driver is None or isinstance(self.driver, PydanticDriver),
			independent=True,
			limit=capacity,
		)
		if contexts and self.driver is None:
			try:
				self.driver = PydanticDriver(progress=record_progress)
			except Exception as error:
				for context in contexts:
					outcome = DecisionOutcome(context=context, error=f'Agent provider failed ({type(error).__name__}).')
					task = asyncio.get_running_loop().create_future()
					task.set_result([outcome])
					self.tasks[task] = (world_id, revision, context)
				return

		for context in contexts:
			task = asyncio.create_task(collect_decisions([context], self.driver, slots=1))
			self.tasks[task] = (world_id, revision, context)

	async def close(self):
		try:
			for world_id in {world_id for world_id, _, _ in self.tasks.values()}:
				for attempt in range(SHUTDOWN_ATTEMPTS):
					try:
						await asyncio.to_thread(database_call, set_world_status, world_id, 'paused')
						await self.step(world_id, advance=False)
						break
					except WorldBusy:
						if attempt == SHUTDOWN_ATTEMPTS - 1:
							raise
						await asyncio.sleep(0.1)
		finally:
			for task in self.tasks:
				task.cancel()
			await asyncio.gather(*self.tasks, return_exceptions=True)
			if isinstance(self.driver, PydanticDriver):
				await asyncio.wait_for(self.driver.provider.client.close(), timeout=5)

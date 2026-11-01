import copy
from threading import Lock
from typing import Literal, Optional

from pydantic import ValidationError
from pydantic_ai import CallDeferred, ModelRetry
from worlds.agents.contracts import MAX_PERSONAL_MEMORIES, PersonalMemory
from worlds.simulation.actions import Action
from worlds.simulation.programs import ProgramError, SimulationProgramVM, validate_program

MAX_QUERY_LENGTH = 200
MAX_SHARED_PLAN_LENGTH = 1200


class LocalTools:
	def __init__(self, context, progress=None):
		self.context = context
		self.trace = []
		self.progress = progress
		self.trace_lock = Lock()
		self.action = None
		self.memories = []

	def perform(self, kind, **arguments):
		try:
			action = Action(kind=kind, **arguments)
		except ValidationError as error:
			self.record({'tool': kind, 'arguments': arguments, 'error': str(error)})
			raise ModelRetry(str(error)) from error

		with self.trace_lock:
			available = self.action is None

			if available:
				self.action = action

		if not available:
			message = 'An action is already starting. Wait for its outcome before taking another.'
			self.record({'tool': kind, 'arguments': arguments, 'error': message})
			raise ModelRetry(message)

		raise CallDeferred(metadata={'action': action.model_dump(mode='json')})

	def walk(self, destination: tuple[float, float, float]) -> dict:
		"""Walk to [x,y,z] around obstacles. Elevation follows terrain. Return arrival or failure."""
		return self.perform('walk', destination=destination)

	def speak(self, text: str) -> dict:
		"""Speak to everyone within hearing range. Messages persist for recipients, including those still thinking."""
		return self.perform('speak', text=text)

	def wait(self, seconds: float = 1) -> dict:
		"""Let simulated time pass without another activity."""
		return self.perform('wait', seconds=seconds)

	def rest(self, seconds: float = 30) -> dict:
		"""Rest for the specified simulated seconds to recover energy."""
		return self.perform('rest', seconds=seconds)

	def grasp(self, target_id: str) -> dict:
		"""Pick up a reachable object, subject to strength and mass."""
		return self.perform('grasp', target_id=target_id)

	def release(self, target_id: str) -> dict:
		"""Let go of an object you hold."""
		return self.perform('release', target_id=target_id)

	def place(self, target_id: str, destination: tuple[float, float, float]) -> dict:
		"""Move a held object toward [x,y,z]. Collisions and gravity still apply."""
		return self.perform('place', target_id=target_id, destination=destination)

	def push(
		self,
		target_id: str,
		direction: tuple[float, float, float],
		contact_point: Optional[tuple[float, float, float]] = None,
	) -> dict:
		"""Push a reachable object in a direction. An optional world-space contact point can produce rotation."""
		return self.perform('push', target_id=target_id, direction=direction, contact_point=contact_point)

	def strike(
		self,
		target_id: str,
		direction: tuple[float, float, float],
		contact_point: Optional[tuple[float, float, float]] = None,
	) -> dict:
		"""Strike a reachable object, optionally away from its center. Impact and material determine the effect."""
		return self.perform('strike', target_id=target_id, direction=direction, contact_point=contact_point)

	def shape(
		self,
		target_id: str,
		dimensions: tuple[float, float, float],
		shape: Literal['box', 'sphere', 'cylinder'] = 'box',
	) -> dict:
		"""Reshape a held part into the chosen dimensions without adding mass. Shaped seeds cease to be plantable."""
		return self.perform('shape', target_id=target_id, dimensions=dimensions, shape=shape)

	def connect(
		self,
		target_id: str,
		other_id: str,
		connection: Literal['fixed', 'hinge'] = 'fixed',
	) -> dict:
		"""Join two touching manufactured parts using held fiber. Choose a fixed bond or a hinge."""
		return self.perform('connect', target_id=target_id, other_id=other_id, connection=connection)

	def detach(self, target_id: str) -> dict:
		"""Detach a reachable connection using its connection ID."""
		return self.perform('detach', target_id=target_id)

	def gather(self, target_id: str, amount: float = 0.25) -> dict:
		"""Gather kilograms of material from a reachable resource or log. Finite sources lose that mass."""
		return self.perform('gather', target_id=target_id, amount=amount)

	def fell(self, target_id: str) -> dict:
		"""Cut a mature tree into a loose log. Roots remain and may regrow."""
		return self.perform('fell', target_id=target_id)

	def take_seed(self, target_id: str, amount: float = 0.25) -> dict:
		"""Take up to 1 kg of seeds or cuttings from a mature tree, bush, or fiber plant."""
		return self.perform('take_seed', target_id=target_id, amount=amount)

	def plant(self, target_id: str, destination: tuple[float, float, float]) -> dict:
		"""Plant a held seed, cutting, or transplant in nearby dry soil at [x,y,ground_z]. Growth takes time."""
		return self.perform('plant', target_id=target_id, destination=destination)

	def uproot(self, target_id: str) -> dict:
		"""Remove a small plant or stump and hold it as a transplant, clearing its location."""
		return self.perform('uproot', target_id=target_id)

	def eat(self, target_id: str, amount: float = 0.25) -> dict:
		"""Eat kilograms of edible material you hold."""
		return self.perform('eat', target_id=target_id, amount=amount)

	def drink(self, amount: float = 0.25) -> dict:
		"""Drink kilograms of water when water is within reach."""
		return self.perform('drink', amount=amount)

	def care(self, target_id: str, amount: float = 0.25) -> dict:
		"""Give kilograms of held food to another reachable living inhabitant."""
		return self.perform('care', target_id=target_id, amount=amount)

	def write(self, target_id: str, text: str, title: str = '', artifact_id: Optional[str] = None) -> dict:
		"""Write on a nearby manufactured wood or stone surface. Supply artifact_id to update an existing document."""
		return self.perform('write', target_id=target_id, text=text, title=title, artifact_id=artifact_id)

	def program(self, target_id: str, source: str, title: str = '') -> dict:
		"""Program a held manufactured part using scratch's bounded JSON language. Devices have finite energy."""
		return self.perform('program', target_id=target_id, text=source, title=title)

	def consent(self, target_id: Optional[str] = None, willing: bool = True) -> dict:
		"""Offer reproductive consent to a reachable mature partner, or revoke consent with willing=false."""
		return self.perform('consent', target_id=target_id, willing=willing)

	def name_self(self, text: str) -> dict:
		"""Choose or change your own name, using 1 to 120 characters."""
		return self.perform('name_self', text=text)

	def name_child(self, target_id: str, text: str) -> dict:
		"""Choose or change the name of your own child. The child may also change their own name."""
		return self.perform('name_child', target_id=target_id, text=text)

	def remember(self, text: str, confidence: float = 0.5) -> str:
		"""Keep a personal memory with confidence from 0 to 1. Up to four memories can be noted per decision."""
		try:
			memory = PersonalMemory(text=text, confidence=confidence)
		except ValidationError as error:
			raise ModelRetry(str(error)) from error

		with self.trace_lock:
			if len(self.memories) == MAX_PERSONAL_MEMORIES:
				raise ModelRetry('At most four memories can be noted before taking an action.')

			self.memories.append(memory)

		self.record({'tool': 'remember', 'arguments': memory.model_dump(), 'result': 'Memory noted.'})
		return 'Memory noted.'

	def record(self, entry):
		with self.trace_lock:
			self.trace.append(entry)

			if self.progress is not None:
				self.progress(copy.deepcopy(self.trace))

	def share_plan(self, text: str) -> str:
		"""Share a short, visible plan or observation with the spectator.

		Do not include private reasoning. This does not speak to other inhabitants.
		"""

		if not text.strip() or len(text) > MAX_SHARED_PLAN_LENGTH:
			raise ModelRetry('Share a short plan of 1 to 1200 characters.')

		self.record({'tool': 'share_plan', 'arguments': {'text': text}, 'result': 'Plan recorded for the spectator.'})

		return 'Plan recorded for the spectator.'

	def inspect(self, object_id: str) -> dict:
		"""Examine and measure a visible object within reach, including its mass, shape, and condition."""
		result = self.context.measurements.get(object_id)

		if result is None:
			self.record(
				{
					'tool': 'inspect',
					'arguments': {'object_id': object_id},
					'error': 'That object cannot be examined from here.',
				}
			)
			raise ModelRetry('That object cannot be examined from here.')

		self.record({'tool': 'inspect', 'arguments': {'object_id': object_id}, 'result': copy.deepcopy(result)})

		return copy.deepcopy(result)

	def recall(self, query: str = '') -> list[dict]:
		"""Search your own stored memories. Other inhabitants' memories are private."""

		if len(query) > MAX_QUERY_LENGTH:
			self.record(
				{
					'tool': 'recall',
					'arguments': {'query': query[:MAX_QUERY_LENGTH], 'truncated': True},
					'error': 'Query exceeded 200 characters.',
				}
			)
			raise ModelRetry('Use a search query of at most 200 characters.')

		result = [memory for memory in self.context.memories if query.casefold() in memory['text'].casefold()][:30]
		self.record({'tool': 'recall', 'arguments': {'query': query}, 'result': copy.deepcopy(result)})

		return result

	def read_document(self, artifact_id: str) -> dict:
		"""Read a document within reach at the start of this decision round."""
		result = self.context.documents.get(artifact_id)

		if result is None:
			self.record(
				{
					'tool': 'read_document',
					'arguments': {'artifact_id': artifact_id},
					'error': 'That document is not within reading distance.',
				}
			)
			raise ModelRetry('That document is not within reading distance.')

		self.record(
			{'tool': 'read_document', 'arguments': {'artifact_id': artifact_id}, 'result': copy.deepcopy(result)}
		)

		return copy.deepcopy(result)

	def scratch(self, source: str) -> dict:
		"""Run a JSON instruction list in private scratch space.

		Example: [{"put":"sum","value":{"op":"add","args":[2,3]}}].
		Instructions: put/value, send, repeat/do, if/then/else.
		Expressions: record, sensor, op/args. Sensors: tick, name, inbox.
		No host access or world changes.
		"""

		try:
			result = SimulationProgramVM(
				{}, {'tick': self.context.observation['tick'], 'name': self.context.observation['name'], 'inbox': []}
			).run(validate_program(source))
		except (ProgramError, TypeError, KeyError, RecursionError) as error:
			self.record({'tool': 'scratch', 'arguments': {'source': source[:16000]}, 'error': str(error)})
			raise ModelRetry(str(error)) from error

		self.record({'tool': 'scratch', 'arguments': {'source': source}, 'result': copy.deepcopy(result)})

		return result

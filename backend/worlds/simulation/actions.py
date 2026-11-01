import math
import uuid
from typing import Literal, Optional

from pydantic import Field, field_validator, model_validator
from worlds.simulation.contracts import Activity, Contract
from worlds.simulation.rules import MIN_WORLD_ELEVATION

REACH = 2.0
MAX_ACTION_SECONDS = 600
MAX_NAME_LENGTH = 120


class Action(Contract):
	kind: Literal[
		'walk',
		'wait',
		'rest',
		'grasp',
		'release',
		'place',
		'push',
		'strike',
		'shape',
		'connect',
		'detach',
		'gather',
		'fell',
		'take_seed',
		'plant',
		'uproot',
		'eat',
		'drink',
		'care',
		'speak',
		'write',
		'program',
		'consent',
		'name_self',
		'name_child',
	]
	target_id: Optional[str] = None
	other_id: Optional[str] = None
	destination: Optional[tuple[float, float, float]] = None
	direction: Optional[tuple[float, float, float]] = None
	contact_point: Optional[tuple[float, float, float]] = None
	dimensions: Optional[tuple[float, float, float]] = None
	shape: Literal['box', 'sphere', 'cylinder'] = 'box'
	connection: Literal['fixed', 'hinge'] = 'fixed'
	amount: float = Field(default=0.25, gt=0, le=25)
	seconds: float = Field(default=1, ge=0.1, le=MAX_ACTION_SECONDS)
	text: str = Field(default='', max_length=8000)
	title: str = Field(default='', max_length=120)
	artifact_id: Optional[str] = None
	willing: bool = True

	@field_validator('target_id', 'other_id', 'artifact_id')
	@classmethod
	def valid_identity(cls, value):
		return str(uuid.UUID(value)) if value is not None else None

	@model_validator(mode='after')
	def required_arguments(self):
		if self.kind == 'name_child' and not self.target_id:
			raise ValueError('Naming a child requires their target_id.')

		if self.kind in ('name_self', 'name_child') and not 1 <= len(self.text.strip()) <= MAX_NAME_LENGTH:
			raise ValueError('A name must contain 1 to 120 characters.')

		if (
			self.kind
			in (
				'grasp',
				'release',
				'place',
				'push',
				'strike',
				'shape',
				'connect',
				'detach',
				'gather',
				'fell',
				'take_seed',
				'plant',
				'uproot',
				'eat',
				'care',
				'write',
				'program',
			)
			or (self.kind == 'consent' and self.willing)
		) and not self.target_id:
			raise ValueError('This action requires a target_id.')

		if self.kind in ('walk', 'place', 'plant') and self.destination is None:
			raise ValueError('This action requires a destination.')

		if self.kind in ('push', 'strike') and self.direction is None:
			raise ValueError('This action requires a direction.')

		if self.kind == 'shape' and self.dimensions is None:
			raise ValueError('Shaping requires dimensions.')

		if self.kind == 'connect' and not self.other_id:
			raise ValueError('Connecting requires two different target parts.')

		if self.kind in ('speak', 'write', 'program') and not self.text.strip():
			raise ValueError('Speech and writing require text.')

		return self


class ActionRejected(ValueError):
	pass


def distance(a, b):
	return math.dist(a, b)


def reachable(state, actor, target_id):
	target = next((entity for entity in state.entities if entity.id == target_id), None)

	if target is None:
		raise ActionRejected('That object is not present in this world.')

	origin = state.entity(actor.id)

	if distance(origin.position, target.position) > REACH + max(target.dimensions) / 2:
		raise ActionRejected('That object is out of reach.')

	return target


def begin_action(state, actor_id, action):
	actor = state.inhabitant(actor_id)

	if not actor.alive:
		raise ActionRejected('This inhabitant is dead.')

	if actor.activity:
		raise ActionRejected('An activity is already in progress.')

	if action.destination:
		half = state.config.size / 2

		if (
			abs(action.destination[0]) > half
			or abs(action.destination[1]) > half
			or not MIN_WORLD_ELEVATION <= action.destination[2] <= state.config.ceiling
		):
			raise ActionRejected('The destination lies outside the world.')

	if action.target_id and action.kind not in ('detach', 'name_child'):
		reachable(state, actor, action.target_id)

	duration = action.seconds

	if action.kind == 'walk':
		duration = min(
			MAX_ACTION_SECONDS,
			max(1, distance(state.entity(actor_id).position[:2], action.destination[:2]) / 1.4 * 2 + 5),
		)
	elif action.kind in ('shape', 'connect', 'gather'):
		duration = max(duration, 5 * action.amount)
	elif action.kind == 'fell':
		target = state.entity(action.target_id)
		duration = min(
			MAX_ACTION_SECONDS,
			max(duration, 10, target.mass / (30 * actor.body.strength_trait * max(0.1, actor.body.growth))),
		)
	elif action.kind in ('take_seed', 'plant', 'uproot'):
		duration = max(duration, 3)

	actor.activity = Activity(
		kind=action.kind,
		started_tick=state.tick,
		ends_tick=state.tick + max(1, round(duration * state.config.physics_hz)),
		parameters=action.model_dump(mode='json'),
	)
	actor.last_decision_tick = state.tick

	return actor.activity

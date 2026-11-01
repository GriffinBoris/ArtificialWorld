from dataclasses import dataclass, field
from typing import Optional

from pydantic import Field
from worlds.simulation.actions import Action
from worlds.simulation.contracts import Contract

MAX_PERSONAL_MEMORIES = 4


class PersonalMemory(Contract):
	text: str = Field(min_length=1, max_length=8000)
	confidence: float = Field(default=0.5, ge=0, le=1)


class DecisionDraft(Contract):
	action: Action
	memories: list[PersonalMemory] = Field(default_factory=list, max_length=MAX_PERSONAL_MEMORIES)
	message: str = Field(
		default='',
		max_length=2000,
		description='Optional visible description of your decision. Do not include private reasoning.',
	)


@dataclass
class DecisionContext:
	decision_id: str
	actor_id: str
	driver: str
	model_name: str
	observation: dict
	memories: list[dict]
	documents: dict[str, dict]
	measurements: dict[str, dict] = field(default_factory=dict)
	event_sequence: int = 0
	previous_tool: Optional[dict] = None
	conversation: dict = field(default_factory=dict)
	world_id: str = ''


@dataclass
class DriverReply:
	draft: DecisionDraft
	trace: list[dict] = field(default_factory=list)
	messages: list[dict] = field(default_factory=list)


@dataclass
class DecisionOutcome:
	context: DecisionContext
	reply: Optional[DriverReply] = None
	error: str = ''
	trace: list[dict] = field(default_factory=list)


class DecisionFailed(Exception):
	def __init__(self, error_type, trace):
		super().__init__('The agent request failed.')
		self.error_type = error_type
		self.trace = trace

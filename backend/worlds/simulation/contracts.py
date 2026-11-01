import math
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

MIN_PART_SIZE = 0.01
MAX_PART_SIZE = 30
QUATERNION_TOLERANCE = 0.01
CURRENT_RULES_VERSION = 2


def new_id():
	return str(uuid4())


class Contract(BaseModel):
	model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class WorldConfig(Contract):
	rules_version: int = Field(default=CURRENT_RULES_VERSION, ge=1, le=CURRENT_RULES_VERSION)
	seed: int = Field(default=42, ge=0, le=2**31 - 1)
	size: float = Field(default=1024, ge=128, le=4096)
	ceiling: float = Field(default=256, ge=32, le=1024)
	gravity: float = Field(default=9.81, gt=0, le=30)
	wind: tuple[float, float, float] = (5, 1, 0)
	water_level: float = 0
	physics_hz: Literal[60] = 60
	recording_hz: Literal[10] = 10
	thinking_slots: Literal[2] = Field(default=2, exclude=True)
	food_hours: float = Field(default=24, gt=0)
	water_hours: float = Field(default=8, gt=0)
	energy_hours: float = Field(default=16, gt=0)
	gestation_hours: float = Field(default=6, gt=0, le=10000)
	maturation_hours: float = Field(default=24, gt=0, le=100000)
	allow_live_models: bool = False


class Material(Contract):
	density: float
	friction: float
	color: str
	strength: float


MATERIALS = {
	'wood': Material(density=600, friction=0.6, color='#a87849', strength=1600),
	'stone': Material(density=2600, friction=0.8, color='#8c9597', strength=6000),
	'fiber': Material(density=300, friction=0.8, color='#c9b578', strength=800),
	'food': Material(density=800, friction=0.4, color='#91b65c', strength=100),
	'body': Material(density=1000, friction=0.7, color='#e4aa76', strength=1800),
}


class ResourceState(Contract):
	supply: Literal['finite', 'renewable', 'infinite'] = 'finite'
	capacity: float = Field(gt=0, le=1e7)
	mature_dimensions: tuple[float, float, float]
	root_mass: float = Field(default=0, ge=0)
	growth_seconds: Optional[float] = Field(default=None, gt=0)
	last_growth_tick: int = 0
	felled_tick: Optional[int] = None
	area_id: Optional[str] = None


class ResourceAreaState(Contract):
	id: str = Field(default_factory=new_id)
	name: str
	material: Literal['wood', 'food', 'fiber']
	position: tuple[float, float, float]
	radius: float = Field(default=30, gt=0)
	target_count: int = Field(default=20, ge=1)
	renewal_seconds: float = Field(default=21600, gt=0)
	next_spawn_tick: int = 0


class EntityState(Contract):
	id: str = Field(default_factory=new_id)
	name: str = Field(max_length=120)
	kind: Literal['part', 'resource', 'seed', 'inhabitant', 'corpse', 'device'] = 'part'
	material: Literal['wood', 'stone', 'fiber', 'food', 'body'] = 'wood'
	shape: Literal['box', 'sphere', 'cylinder', 'capsule'] = 'box'
	dimensions: tuple[float, float, float] = (0.2, 0.2, 1)
	position: tuple[float, float, float] = (0, 0, 2)
	rotation: tuple[float, float, float, float] = (1, 0, 0, 0)
	velocity: tuple[float, float, float] = (0, 0, 0)
	angular_velocity: tuple[float, float, float] = (0, 0, 0)
	mass: float = Field(default=1, gt=0, le=1e7)
	fixed: bool = False
	condition: float = Field(default=100, ge=0, le=100)
	creator_id: Optional[str] = None
	resource: Optional[ResourceState] = None

	@model_validator(mode='after')
	def validate_geometry(self):
		if any(value < MIN_PART_SIZE or value > MAX_PART_SIZE for value in self.dimensions):
			raise ValueError('Part dimensions must be between 0.01 and 30 metres.')

		if self.shape == 'sphere' and len(set(self.dimensions)) != 1:
			raise ValueError('Sphere dimensions must be equal.')

		if self.shape in ('capsule', 'cylinder') and self.dimensions[0] != self.dimensions[1]:
			raise ValueError('Round parts must have equal width and depth.')

		if self.shape == 'capsule' and self.dimensions[2] < self.dimensions[0]:
			raise ValueError('Capsule height must include its caps.')

		length = math.sqrt(sum(value * value for value in self.rotation))

		if abs(length - 1) > QUATERNION_TOLERANCE:
			raise ValueError('Rotation must be a unit quaternion.')

		return self

	@property
	def volume(self):
		x, y, z = self.dimensions

		if self.shape == 'sphere':
			return 4 * math.pi * (x / 2) ** 3 / 3

		if self.shape == 'cylinder':
			return math.pi * (x / 2) ** 2 * z

		if self.shape == 'capsule':
			radius = x / 2

			return math.pi * radius**2 * max(0, z - x) + 4 * math.pi * radius**3 / 3

		return x * y * z


class WalkNavigation(Contract):
	waypoints: list[tuple[float, float, float]]
	waypoint_index: int = 0
	progress_position: tuple[float, float, float]
	progress_tick: int
	replans: int = 0


class Activity(Contract):
	id: str = Field(default_factory=new_id)
	kind: str
	started_tick: int
	ends_tick: int
	parameters: dict = Field(default_factory=dict)
	navigation: Optional[WalkNavigation] = None


class BodyState(Contract):
	health: float = 100
	food: float = 100
	water: float = 100
	energy: float = 100
	wear: float = 0
	injury: float = 0
	stress: float = 0
	growth: float = Field(default=1, ge=0, le=1)
	age_seconds: float = 0
	air: float = 120
	repair_trait: float = 1
	metabolism_trait: float = 1
	strength_trait: float = 1


class InhabitantState(Contract):
	id: str
	name: str
	self_named: bool = False
	parent_named: bool = False
	alive: bool = True
	body: BodyState = Field(default_factory=BodyState)
	driver: Literal['scripted', 'pydantic'] = 'scripted'
	model_name: str = ''
	parents: list[str] = Field(default_factory=list)
	held_ids: list[str] = Field(default_factory=list)
	activity: Optional[Activity] = None
	wake_tick: int = 0
	last_decision_tick: int = -1
	last_observation_sequence: int = 0
	last_action_result: Optional[dict] = None
	reproduction_consent: Optional[str] = None
	pregnancy_partner: Optional[str] = None
	pregnancy_progress: float = 0
	last_birth_age: float = -1e9


class JointState(Contract):
	id: str = Field(default_factory=new_id)
	entity_a: str
	entity_b: str
	kind: Literal['fixed', 'hinge'] = 'fixed'
	anchor_a: tuple[float, float, float] = (0, 0, 0)
	anchor_b: tuple[float, float, float] = (0, 0, 0)
	rotation_a: tuple[float, float, float, float] = (1, 0, 0, 0)
	rotation_b: tuple[float, float, float, float] = (1, 0, 0, 0)
	axis: tuple[float, float, float] = (0, 1, 0)
	axis_b: tuple[float, float, float] = (0, 1, 0)
	strength: float = Field(default=800, gt=0, le=100000)
	creator_id: Optional[str] = None


class SimulationEvent(Contract):
	kind: str
	tick: int
	actor_id: Optional[str] = None
	subject_id: Optional[str] = None
	data: dict = Field(default_factory=dict)


class WorldState(Contract):
	config: WorldConfig = Field(default_factory=WorldConfig)
	tick: int = 0
	action_rotation: int = 0
	entities: list[EntityState] = Field(default_factory=list)
	inhabitants: list[InhabitantState] = Field(default_factory=list)
	joints: list[JointState] = Field(default_factory=list)
	resource_areas: list[ResourceAreaState] = Field(default_factory=list)

	@property
	def seconds(self):
		return self.tick / self.config.physics_hz

	def entity(self, entity_id):
		return next(entity for entity in self.entities if entity.id == entity_id)

	def inhabitant(self, inhabitant_id):
		return next(inhabitant for inhabitant in self.inhabitants if inhabitant.id == inhabitant_id)

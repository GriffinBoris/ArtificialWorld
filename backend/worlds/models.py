import uuid

from core.base_models import ProjectBaseModel
from django.conf import settings
from django.db import models


class World(ProjectBaseModel):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	name = models.TextField()
	configuration = models.JSONField()
	tick = models.PositiveBigIntegerField(default=0)
	action_rotation = models.PositiveBigIntegerField(default=0)
	revision = models.PositiveBigIntegerField(default=0)
	event_sequence = models.PositiveBigIntegerField(default=0)
	status = models.TextField(default='paused')
	error = models.TextField(blank=True)


class ResourceArea(ProjectBaseModel):
	id = models.UUIDField(primary_key=True, editable=False)
	world = models.ForeignKey('worlds.World', related_name='resource_areas', on_delete=models.CASCADE)
	name = models.TextField()
	state = models.JSONField()


class Entity(ProjectBaseModel):
	id = models.UUIDField(primary_key=True, editable=False)
	world = models.ForeignKey('worlds.World', related_name='entities', on_delete=models.CASCADE)
	name = models.TextField()
	kind = models.TextField()
	material = models.TextField()
	state = models.JSONField()


class Inhabitant(ProjectBaseModel):
	entity = models.OneToOneField('worlds.Entity', primary_key=True, on_delete=models.CASCADE)
	world = models.ForeignKey('worlds.World', related_name='inhabitants', on_delete=models.CASCADE)
	name = models.TextField()
	alive = models.BooleanField(default=True)
	driver = models.TextField(default='scripted')
	state = models.JSONField()
	agent_context = models.JSONField(default=dict)


class Connection(ProjectBaseModel):
	id = models.UUIDField(primary_key=True, editable=False)
	world = models.ForeignKey('worlds.World', related_name='connections', on_delete=models.CASCADE)
	entity_a = models.ForeignKey('worlds.Entity', related_name='connections_a', on_delete=models.CASCADE)
	entity_b = models.ForeignKey('worlds.Entity', related_name='connections_b', on_delete=models.CASCADE)
	state = models.JSONField()


class Artifact(ProjectBaseModel):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	world = models.ForeignKey('worlds.World', related_name='artifacts', on_delete=models.CASCADE)
	author = models.ForeignKey('worlds.Inhabitant', null=True, on_delete=models.SET_NULL)
	location = models.ForeignKey('worlds.Entity', null=True, on_delete=models.SET_NULL)
	title = models.TextField()
	kind = models.TextField(default='document')
	position = models.JSONField()
	created_tick = models.PositiveBigIntegerField()


class ArtifactVersion(ProjectBaseModel):
	class Meta:
		constraints = (models.UniqueConstraint(fields=('artifact', 'version'), name='artifact_version_unique'),)

	artifact = models.ForeignKey('worlds.Artifact', related_name='versions', on_delete=models.CASCADE)
	version = models.PositiveIntegerField()
	author = models.ForeignKey('worlds.Inhabitant', null=True, on_delete=models.SET_NULL)
	content = models.TextField()
	tick = models.PositiveBigIntegerField()


class Memory(ProjectBaseModel):
	inhabitant = models.ForeignKey('worlds.Inhabitant', related_name='memories', on_delete=models.CASCADE)
	text = models.TextField()
	tick = models.PositiveBigIntegerField()
	confidence = models.FloatField(default=0.5)


class WorldEvent(ProjectBaseModel):
	class Meta:
		constraints = (models.UniqueConstraint(fields=('world', 'sequence'), name='world_event_sequence_unique'),)
		indexes = (models.Index(fields=('world', 'tick')),)

	world = models.ForeignKey('worlds.World', related_name='events', on_delete=models.CASCADE)
	sequence = models.PositiveBigIntegerField()
	tick = models.PositiveBigIntegerField()
	kind = models.TextField()
	actor_id = models.TextField(null=True)
	subject_id = models.TextField(null=True)
	data = models.JSONField()


class Checkpoint(ProjectBaseModel):
	class Meta:
		constraints = (
			models.UniqueConstraint(fields=('world', 'tick', 'event_sequence'), name='world_checkpoint_tick_unique'),
		)

	world = models.ForeignKey('worlds.World', related_name='checkpoints', on_delete=models.CASCADE)
	tick = models.PositiveBigIntegerField()
	event_sequence = models.PositiveBigIntegerField()
	payload = models.BinaryField()
	checksum = models.TextField()


class MotionBlock(ProjectBaseModel):
	class Meta:
		indexes = (models.Index(fields=('world', 'start_tick')),)

	world = models.ForeignKey('worlds.World', related_name='motion_blocks', on_delete=models.CASCADE)
	start_tick = models.PositiveBigIntegerField()
	end_tick = models.PositiveBigIntegerField()
	payload = models.BinaryField()
	checksum = models.TextField()


class Decision(ProjectBaseModel):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	world = models.ForeignKey('worlds.World', related_name='decisions', on_delete=models.CASCADE)
	inhabitant = models.ForeignKey('worlds.Inhabitant', related_name='decisions', on_delete=models.CASCADE)
	tick = models.PositiveBigIntegerField()
	status = models.TextField(default='queued')
	observation = models.JSONField()
	result = models.JSONField(null=True)
	trace = models.JSONField(default=list)
	messages = models.JSONField(default=list)
	error = models.TextField(blank=True)
	model_name = models.TextField(blank=True)


class SimulationProgram(ProjectBaseModel):
	artifact_version = models.OneToOneField('worlds.ArtifactVersion', primary_key=True, on_delete=models.CASCADE)
	world = models.ForeignKey('worlds.World', related_name='programs', on_delete=models.CASCADE)
	owner = models.ForeignKey('worlds.Inhabitant', on_delete=models.CASCADE)
	host = models.ForeignKey('worlds.Entity', on_delete=models.CASCADE)
	state = models.JSONField(default=dict)
	enabled = models.BooleanField(default=False)
	next_tick = models.PositiveBigIntegerField(default=0)

import fcntl
from contextlib import contextmanager

from django.conf import settings
from rest_framework.exceptions import APIException
from worlds.models import Connection, Entity, Inhabitant, ResourceArea, WorldEvent
from worlds.simulation.contracts import (
	EntityState,
	InhabitantState,
	JointState,
	ResourceAreaState,
	WorldConfig,
	WorldState,
)


class WorldBusy(APIException):
	status_code = 409
	default_detail = 'The world is completing another step. Try again shortly.'


@contextmanager
def world_lock(world_id, blocking=False):
	directory = settings.TEMP_DIR / 'world-locks'
	directory.mkdir(parents=True, exist_ok=True)

	with (directory / f'{world_id}.lock').open('a') as lock:
		try:
			fcntl.flock(lock.fileno(), fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
		except BlockingIOError as error:
			raise WorldBusy from error

		try:
			yield
		finally:
			fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def load_state(world):
	return WorldState(
		config=WorldConfig.model_validate(world.configuration),
		tick=world.tick,
		action_rotation=world.action_rotation,
		entities=[EntityState.model_validate(entity.state) for entity in world.entities.order_by('id')],
		inhabitants=[
			InhabitantState.model_validate(inhabitant.state) for inhabitant in world.inhabitants.order_by('entity_id')
		],
		joints=[JointState.model_validate(connection.state) for connection in world.connections.order_by('id')],
		resource_areas=[ResourceAreaState.model_validate(area.state) for area in world.resource_areas.order_by('id')],
	)


def persist_state(world, state):
	ResourceArea.objects.bulk_create(
		[
			ResourceArea(id=area.id, world=world, name=area.name, state=area.model_dump(mode='json'))
			for area in state.resource_areas
		],
		update_conflicts=True,
		unique_fields=('id',),
		update_fields=('name', 'state'),
	)
	world.resource_areas.exclude(id__in=[area.id for area in state.resource_areas]).delete()
	Entity.objects.bulk_create(
		[
			Entity(
				id=entity.id,
				world=world,
				name=entity.name,
				kind=entity.kind,
				material=entity.material,
				state=entity.model_dump(mode='json'),
			)
			for entity in state.entities
		],
		update_conflicts=True,
		unique_fields=('id',),
		update_fields=('name', 'kind', 'material', 'state'),
	)
	Inhabitant.objects.bulk_create(
		[
			Inhabitant(
				entity_id=inhabitant.id,
				world=world,
				name=inhabitant.name,
				alive=inhabitant.alive,
				driver=inhabitant.driver,
				state=inhabitant.model_dump(mode='json'),
			)
			for inhabitant in state.inhabitants
		],
		update_conflicts=True,
		unique_fields=('entity',),
		update_fields=('name', 'alive', 'driver', 'state'),
	)
	Connection.objects.bulk_create(
		[
			Connection(
				id=joint.id,
				world=world,
				entity_a_id=joint.entity_a,
				entity_b_id=joint.entity_b,
				state=joint.model_dump(mode='json'),
			)
			for joint in state.joints
		],
		update_conflicts=True,
		unique_fields=('id',),
		update_fields=('state',),
	)
	world.connections.exclude(id__in=[joint.id for joint in state.joints]).delete()
	world.entities.exclude(id__in=[entity.id for entity in state.entities]).delete()
	world.tick = state.tick
	world.action_rotation = state.action_rotation
	world.revision += 1
	world.configuration = state.config.model_dump(mode='json')
	world.save(
		update_fields=(
			'tick',
			'action_rotation',
			'revision',
			'configuration',
			'event_sequence',
			'status',
			'error',
			'updated_ts',
		)
	)


def append_events(world, events):
	rows = []

	for event in events:
		world.event_sequence += 1
		rows.append(
			WorldEvent(
				world=world,
				sequence=world.event_sequence,
				tick=event.tick,
				kind=event.kind,
				actor_id=event.actor_id,
				subject_id=event.subject_id,
				data=event.data,
			)
		)

	WorldEvent.objects.bulk_create(rows)

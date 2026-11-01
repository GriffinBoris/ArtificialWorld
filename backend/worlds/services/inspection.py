from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from worlds.services.recordings import replay_state
from worlds.simulation.rules import INITIAL_DEVICE_POWER


def inspect_records(world, entity_id, tick=None):
	identity = str(entity_id)

	if tick is None:
		get_object_or_404(world.entities, id=entity_id)
		artifacts = world.artifacts.filter(location_id=entity_id)
		programs = list(
			world.programs.filter(host_id=entity_id).values('artifact_version_id', 'enabled', 'next_tick', 'state')
		)
	else:
		state = replay_state(world, tick)

		if not any(entity.id == identity for entity in state.entities):
			raise NotFound('That object is not present at this recorded time.')

		written = world.events.filter(kind='artifact.written', data__location_id=identity, tick__lte=tick).values_list(
			'subject_id', flat=True
		)
		deployed = world.events.filter(kind='program.deployed', data__host_id=identity, tick__lte=tick)
		artifact_ids = set(written) | {event.data['artifact_id'] for event in deployed}
		artifacts = world.artifacts.filter(id__in=artifact_ids)
		programs = historical_programs(world, deployed, tick)

	versions = []

	for artifact in artifacts:
		rows = artifact.versions.order_by('version')

		if tick is not None:
			rows = rows.filter(tick__lte=tick)

		versions.append(
			{
				'id': str(artifact.id),
				'title': artifact.title,
				'kind': artifact.kind,
				'versions': list(rows.values('version', 'content', 'tick', 'author_id')),
			}
		)

	memories = world.inhabitants.filter(entity_id=entity_id).exclude(memories__isnull=True)
	decisions = world.decisions.filter(inhabitant_id=entity_id)

	if tick is not None:
		memories = memories.filter(memories__tick__lte=tick)
		decisions = decisions.filter(tick__lte=tick)

	return {
		'artifacts': versions,
		'memories': list(memories.values_list('memories__text', flat=True)),
		'decisions': list(
			decisions.order_by('-created_ts').values('id', 'tick', 'status', 'observation', 'result', 'trace', 'error')[
				:8
			]
		),
		'programs': programs,
	}


def historical_programs(world, deployments, tick):
	programs = []

	for deployment in deployments:
		last = (
			world.events.filter(
				subject_id=deployment.subject_id,
				tick__lte=tick,
				kind__in=('program.executed', 'program.failed', 'program.unpowered'),
			)
			.order_by('-sequence')
			.first()
		)
		executed = (
			world.events.filter(subject_id=deployment.subject_id, tick__lte=tick, kind='program.executed')
			.order_by('-sequence')
			.first()
		)
		programs.append(
			{
				'artifact_version_id': int(deployment.subject_id),
				'enabled': last is None or last.kind == 'program.executed',
				'next_tick': executed.tick + world.configuration['physics_hz'] if executed else deployment.tick,
				'state': {'records': executed.data['records'], 'power': executed.data['power']}
				if executed
				else {'records': {}, 'power': INITIAL_DEVICE_POWER},
			}
		)

	return programs

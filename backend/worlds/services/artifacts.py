import uuid

from rest_framework.exceptions import ValidationError
from worlds.models import Artifact, ArtifactVersion, Inhabitant
from worlds.simulation.actions import distance
from worlds.simulation.rules import WRITING_RANGE


def persist_artifact_events(world, events):
	for event in events:
		if event.kind != 'artifact.written':
			continue

		data = event.data
		author = Inhabitant.objects.get(world=world, entity_id=event.actor_id)

		if event.subject_id:
			artifact = Artifact.objects.select_for_update().get(
				id=event.subject_id, world=world, location_id=data['location_id']
			)
			version = artifact.versions.count() + 1
		else:
			artifact = Artifact.objects.create(
				id=uuid.uuid4(),
				world=world,
				author=author,
				location_id=data['location_id'],
				title=data['title'],
				position=data['position'],
				created_tick=event.tick,
			)
			version = 1

		ArtifactVersion.objects.create(
			artifact=artifact, version=version, author=author, content=data['text'], tick=event.tick
		)
		event.subject_id = str(artifact.id)
		event.data['version'] = version


def artifact_position(artifact, state):
	if artifact.location_id:
		return state.entity(str(artifact.location_id)).position

	return artifact.position


def read_artifact(world, state, actor_id, artifact_id):
	artifact = world.artifacts.filter(id=artifact_id).first()

	if (
		artifact is None
		or artifact.location_id is None
		or distance(state.entity(actor_id).position, artifact_position(artifact, state)) > WRITING_RANGE
	):
		raise ValidationError('The artifact is not within reading distance.')

	version = artifact.versions.order_by('-version').first()

	return {
		'id': str(artifact.id),
		'title': artifact.title,
		'kind': artifact.kind,
		'version': version.version,
		'text': version.content,
		'author_id': str(version.author_id),
		'tick': version.tick,
	}

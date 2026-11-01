import pytest
from core.test_fixtures import TestFixtures
from django.test import Client
from django.urls import reverse
from worlds.models import Artifact, ArtifactVersion, Decision, Memory, SimulationProgram, World
from worlds.serializers import MemoryInputSerializer, StepInputSerializer
from worlds.services.state import load_state
from worlds.services.worlds import advance_world


@pytest.mark.django_db
def test_world_deletion_removes_content_and_recordings_without_deleting_other_worlds(client, world, owner):
	advance_world(world.id, seconds=1, owner_step=True)
	world.refresh_from_db()
	actor = load_state(world).inhabitants[0]
	Memory.objects.create(inhabitant_id=actor.id, tick=0, text='A memory')
	Decision.objects.create(world=world, inhabitant_id=actor.id, tick=0, status='completed', observation={})
	artifact = Artifact.objects.create(
		world=world, author_id=actor.id, title='A document', position=[0, 0, 0], created_tick=0
	)
	version = ArtifactVersion.objects.create(artifact=artifact, version=1, content='An idea', tick=0)
	SimulationProgram.objects.create(world=world, artifact_version=version, owner_id=actor.id, host_id=actor.id)
	other = World.objects.create(owner=owner, name='Keep this world', configuration={})
	assert world.motion_blocks.exists() and world.checkpoints.exists() and world.events.exists()
	client.force_login(owner)
	response = client.delete(reverse('worlds:world-detail', kwargs={'world_id': world.id}))
	assert response.status_code == 204
	assert World.objects.filter(id=other.id).exists()
	assert not World.objects.filter(id=world.id).exists()
	assert not Memory.objects.filter(inhabitant_id=actor.id).exists()
	assert not ArtifactVersion.objects.filter(artifact_id=artifact.id).exists()
	for relation in (
		'entities',
		'inhabitants',
		'resource_areas',
		'connections',
		'artifacts',
		'events',
		'checkpoints',
		'motion_blocks',
		'decisions',
		'programs',
	):
		assert not getattr(world, relation).exists()


@pytest.mark.django_db
def test_world_deletion_requires_owner_and_no_active_decisions(client, world, owner):
	url = reverse('worlds:world-detail', kwargs={'world_id': world.id})
	assert client.delete(url).status_code == 403
	client.force_login(TestFixtures.create_user())
	assert client.delete(url).status_code == 404
	client.force_login(owner)
	world.status = 'running'
	world.save(update_fields=('status',))
	assert client.delete(url).status_code == 409
	world.status = 'paused'
	world.save(update_fields=('status',))
	actor = load_state(world).inhabitants[0]
	Decision.objects.create(world=world, inhabitant_id=actor.id, tick=0, status='thinking', observation={})
	assert client.delete(url).status_code == 409
	assert World.objects.filter(id=world.id).exists()


@pytest.mark.django_db
def test_local_world_deletion_requires_csrf(world, settings):
	settings.WORLD_REQUIRE_LOGIN = False
	client = Client(enforce_csrf_checks=True)
	url = reverse('worlds:world-detail', kwargs={'world_id': world.id})
	assert client.delete(url).status_code == 403
	token = client.get(reverse('user_bootstrap')).json()['csrf_token']
	assert client.delete(url, HTTP_X_CSRFTOKEN=token).status_code == 204


@pytest.mark.django_db
def test_anonymous_user_cannot_list_worlds(client):
	assert client.get(reverse('worlds:world-list')).status_code == 403


@pytest.mark.django_db
def test_owner_can_create_step_and_replay_world(client, owner):
	client.force_login(owner)
	created = client.post(
		reverse('worlds:world-list'), {'name': 'Owned world', 'population': 1}, content_type='application/json'
	)
	assert created.status_code == 201
	world_id = created.json()['id']
	stepped = client.post(
		reverse('worlds:world-step', kwargs={'world_id': world_id}), {'seconds': 0.5}, content_type='application/json'
	)
	assert stepped.status_code == 200
	assert stepped.json()['tick'] == 30
	replay = client.get(reverse('worlds:world-replay', kwargs={'world_id': world_id}), {'tick': 0})
	assert replay.status_code == 200
	assert replay.json()['recorded_tick'] == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
	'route', ['world-detail', 'world-terrain', 'world-events', 'world-replay', 'world-motion', 'world-messages']
)
def test_other_owner_cannot_read_world(client, world, route):
	other = TestFixtures.create_user()
	client.force_login(other)
	assert client.get(reverse(f'worlds:{route}', kwargs={'world_id': world.id})).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize('route', ['world-step', 'world-status'])
def test_other_owner_cannot_change_world(client, world, route):
	other = TestFixtures.create_user()
	client.force_login(other)
	assert (
		client.post(
			reverse(f'worlds:{route}', kwargs={'world_id': world.id}), {}, content_type='application/json'
		).status_code
		== 404
	)


@pytest.mark.django_db
def test_invalid_step_does_not_change_world(client, world, owner):
	client.force_login(owner)
	response = client.post(
		reverse('worlds:world-step', kwargs={'world_id': world.id}), {'seconds': -1}, content_type='application/json'
	)
	assert response.status_code == 400
	world.refresh_from_db()
	assert world.tick == 0


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity'])
def test_numeric_api_fields_reject_nonfinite_input(value):
	assert not StepInputSerializer(data={'seconds': value}).is_valid()
	assert not MemoryInputSerializer(data={'text': 'A note', 'confidence': value}).is_valid()

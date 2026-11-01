import pytest
from django.test import Client
from django.urls import reverse
from worlds.access import LOCAL_WORLD_USERNAME
from worlds.models import World


@pytest.mark.django_db
def test_local_access_opens_existing_worlds_without_changing_owners(client, world, settings):
	settings.WORLD_REQUIRE_LOGIN = False
	response = client.get(reverse('worlds:world-list'))
	assert response.status_code == 200
	assert [item['id'] for item in response.json()] == [str(world.id)]
	assert client.get(reverse('worlds:world-detail', kwargs={'world_id': world.id})).status_code == 200
	previous_owner = world.owner_id
	world.refresh_from_db()
	assert world.owner_id == previous_owner
	assert client.get(reverse('user_auth_status')).status_code == 403
	settings.WORLD_REQUIRE_LOGIN = True
	assert client.get(reverse('worlds:world-list')).status_code == 403


@pytest.mark.django_db
def test_local_creation_and_step_use_csrf_and_a_non_login_identity(settings):
	settings.WORLD_REQUIRE_LOGIN = False
	client = Client(enforce_csrf_checks=True)
	bootstrap = client.get(reverse('user_bootstrap')).json()
	assert bootstrap['local_world_access'] is True
	assert bootstrap['is_authenticated'] is False
	response = client.post(
		reverse('worlds:world-list'),
		{'name': 'Local world', 'population': 1},
		content_type='application/json',
		headers={'X-CSRFToken': bootstrap['csrf_token']},
	)
	assert response.status_code == 201
	world = World.objects.get(id=response.json()['id'])
	assert world.owner.username == LOCAL_WORLD_USERNAME
	assert not world.owner.has_usable_password()
	assert not world.owner.is_staff
	response = client.post(
		reverse('worlds:world-step', kwargs={'world_id': world.id}),
		{'seconds': 0.1},
		content_type='application/json',
		headers={'X-CSRFToken': bootstrap['csrf_token']},
	)
	assert response.status_code == 200
	assert response.json()['tick'] == 6


@pytest.mark.django_db
def test_local_access_still_rejects_mutations_without_csrf(settings):
	settings.WORLD_REQUIRE_LOGIN = False
	client = Client(enforce_csrf_checks=True)
	response = client.post(reverse('worlds:world-list'), {'name': 'Rejected world'}, content_type='application/json')
	assert response.status_code == 403
	assert not World.objects.exists()


@pytest.mark.django_db
def test_local_access_rejects_untrusted_origin_even_with_csrf(settings):
	settings.WORLD_REQUIRE_LOGIN = False
	client = Client(enforce_csrf_checks=True)
	token = client.get(reverse('user_bootstrap')).json()['csrf_token']
	response = client.post(
		reverse('worlds:world-list'),
		{'name': 'Rejected origin'},
		content_type='application/json',
		headers={'X-CSRFToken': token, 'Origin': 'https://untrusted.invalid'},
	)
	assert response.status_code == 403
	assert not World.objects.exists()

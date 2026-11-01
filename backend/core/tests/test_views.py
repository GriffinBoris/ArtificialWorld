import pytest
from core.test_fixtures import TestFixtures
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestLogout:
	@pytest.fixture(autouse=True)
	def setup(self, client):
		self.user = TestFixtures.create_user()
		client.force_login(self.user)

	def test_logout_post(self, client):
		response = client.post(reverse('user_logout'), content_type='application/json')
		assert response.status_code == status.HTTP_200_OK
		assert response.wsgi_request.session.session_key is None

	def test_logout_get_is_not_allowed(self, client):
		response = client.get(reverse('user_logout'), content_type='application/json')
		assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
		assert response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
class TestRegisterView:
	@pytest.fixture(autouse=True)
	def setup(self):
		self.data = {
			'email': 'test@mail.com',
			'first_name': 'First',
			'last_name': 'Last',
			'password_one': 'passwordpassword',
			'password_two': 'passwordpassword',
			'company_name': 'test',
			'address_one': 'test',
			'address_two': 'test',
			'city': 'test',
			'state': 'test',
			'zip_code': 'test',
			'phone': 'test',
		}

	def test_post(self, client):
		assert not User.objects.filter(email='test@mail.com').exists()

		response = client.post(reverse('user_register'), self.data, content_type='application/json')
		assert response.status_code == status.HTTP_200_OK

		user = User.objects.get(email='test@mail.com')
		assert user is not None
		assert response.wsgi_request.session.session_key is not None
		assert user.first_name == 'First'
		assert user.last_name == 'Last'

	def test_email_already_in_use(self, client):
		User.objects.create_user(
			username='test', email='test@mail.com', password='password', first_name='First', last_name='Last'
		)
		assert User.objects.filter(email='test@mail.com').exists()

		response = client.post(reverse('user_register'), self.data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert response.json() == {
			'type': 'validation_error',
			'errors': [{'code': 'invalid', 'detail': 'Email already in use.', 'attr': 'email'}],
		}

	def test_non_matching_passwords(self, client):
		assert not User.objects.filter(email='test@mail.com').exists()

		data = self.data.copy()
		data['password_two'] = 'password_different'

		response = client.post(reverse('user_register'), data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST

		assert response.json() == {
			'type': 'validation_error',
			'errors': [
				{'code': 'invalid', 'detail': 'Passwords must match.', 'attr': 'password_one'},
				{'code': 'invalid', 'detail': 'Passwords must match.', 'attr': 'password_two'},
			],
		}

	@pytest.mark.parametrize(
		'missing_field, expected_error',
		[
			('email', 'email'),
			('first_name', 'first_name'),
			('last_name', 'last_name'),
			('password_one', 'password_one'),
			('password_two', 'password_two'),
		],
	)
	def test_missing_required_fields(self, client, missing_field, expected_error):
		assert not User.objects.filter(email='test@mail.com').exists()

		data = self.data.copy()
		del data[missing_field]

		response = client.post(reverse('user_register'), data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST

		assert response.json() == {
			'errors': [{'attr': expected_error, 'code': 'required', 'detail': 'This field is required.'}],
			'type': 'validation_error',
		}
		assert not User.objects.filter(email='test@mail.com').exists()
		assert response.wsgi_request.session.session_key is None


@pytest.mark.django_db
class TestValidateUserView:
	@pytest.fixture(autouse=True)
	def setup(self, client):
		self.user = TestFixtures.create_user()
		client.force_login(self.user)

		self.data = {
			'email': 'newuser@mail.com',
			'first_name': 'John',
			'last_name': 'Doe',
			'password_one': 'passwordpassword',
			'password_two': 'passwordpassword',
		}

		self.existing_user = TestFixtures.create_user()

	def test_post_valid_user(self, client):
		response = client.post(reverse('user_register_validate_user'), self.data, content_type='application/json')
		assert response.status_code == status.HTTP_200_OK
		assert response.json() == {}

	def test_email_already_in_use(self, client):
		data = self.data.copy()
		data['email'] = self.existing_user.email
		response = client.post(reverse('user_register_validate_user'), data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert response.json() == {
			'errors': [{'attr': 'email', 'code': 'invalid', 'detail': 'Email already in use.'}],
			'type': 'validation_error',
		}

	@pytest.mark.parametrize(
		'missing_field, expected_error',
		[
			('email', 'email'),
			('first_name', 'first_name'),
			('last_name', 'last_name'),
			('password_one', 'password_one'),
			('password_two', 'password_two'),
		],
	)
	def test_missing_required_fields(self, client, missing_field, expected_error):
		data = self.data.copy()
		del data[missing_field]

		response = client.post(reverse('user_register_validate_user'), data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert response.json() == {
			'errors': [{'attr': expected_error, 'code': 'required', 'detail': 'This field is required.'}],
			'type': 'validation_error',
		}

	def test_unauthenticated_access(self, client):
		client.logout()
		response = client.post(reverse('user_register_validate_user'), self.data, content_type='application/json')
		assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestLoginView:
	@pytest.fixture(autouse=True)
	def setup(self, client):
		self.data = {'username': 'test', 'email': 'test@mail.com', 'password': 'password'}
		self.user = User.objects.create_user(**self.data)

	def test_post(self, client):
		response = client.post(reverse('user_login'), self.data, content_type='application/json')
		assert response.status_code == status.HTTP_200_OK
		assert response.wsgi_request.session.session_key is not None

	@pytest.mark.parametrize('missing_field, expected_error', [('email', 'email'), ('password', 'password')])
	def test_missing_required_fields(self, client, missing_field, expected_error):
		data = self.data.copy()
		del data[missing_field]

		response = client.post(reverse('user_login'), data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert response.json() == {
			'type': 'validation_error',
			'errors': [{'code': 'required', 'detail': 'This field is required.', 'attr': expected_error}],
		}
		assert response.wsgi_request.session.session_key is None

	def test_incorrect_password(self, client):
		data = self.data.copy()
		data['password'] = 'wrongpassword'

		response = client.post(reverse('user_login'), data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert response.json() == {
			'type': 'validation_error',
			'errors': [
				{'code': 'invalid_credentials', 'detail': 'Incorrect email or password.', 'attr': 'email'},
				{'code': 'invalid_credentials', 'detail': 'Incorrect email or password.', 'attr': 'password'},
			],
		}
		assert response.wsgi_request.session.session_key is None


@pytest.mark.django_db
class TestPasswordChangeView:
	@pytest.fixture(autouse=True)
	def setup(self, client):
		self.data = {
			'current_password': 'password',
			'new_password_one': 'Passwordpassword1!',
			'new_password_two': 'Passwordpassword1!',
		}
		self.user = User.objects.create_user(
			username='test', email='test@mail.com', password=self.data['current_password']
		)
		client.force_login(self.user)

	def test_post(self, client):
		assert self.user.check_password('password')

		response = client.post(reverse('user_change_password'), self.data, content_type='application/json')
		assert response.status_code == status.HTTP_200_OK
		self.user.refresh_from_db()
		assert self.user.check_password(self.data['new_password_one'])

	@pytest.mark.parametrize(
		'missing_field, expected_error',
		[
			('current_password', 'current_password'),
			('new_password_one', 'new_password_one'),
			('new_password_two', 'new_password_two'),
		],
	)
	def test_missing_required_fields(self, client, missing_field, expected_error):
		assert self.user.check_password('password')

		data = self.data.copy()
		del data[missing_field]

		response = client.post(reverse('user_change_password'), data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert response.json() == {
			'type': 'validation_error',
			'errors': [{'code': 'required', 'detail': 'This field is required.', 'attr': expected_error}],
		}
		self.user.refresh_from_db()
		assert self.user.check_password('password')

	def test_incorrect_current_password(self, client):
		assert self.user.check_password('password')
		data = self.data.copy()
		data['current_password'] = 'Wrongpassword'

		response = client.post(reverse('user_change_password'), data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert response.json() == {
			'type': 'validation_error',
			'errors': [{'code': 'invalid_credentials', 'detail': 'Incorrect password.', 'attr': 'current_password'}],
		}
		assert self.user.check_password('password')

	def test_non_matching_passwords(self, client):
		data = self.data.copy()
		data['new_password_two'] = 'password_different'

		response = client.post(reverse('user_change_password'), data, content_type='application/json')
		assert response.status_code == status.HTTP_400_BAD_REQUEST
		assert response.json() == {
			'type': 'validation_error',
			'errors': [
				{'code': 'invalid', 'detail': 'Passwords must match.', 'attr': 'new_password_one'},
				{'code': 'invalid', 'detail': 'Passwords must match.', 'attr': 'new_password_two'},
			],
		}


@pytest.mark.django_db
class TestAuthStatusView:
	@pytest.fixture(autouse=True)
	def setup(self, client):
		self.user = User.objects.create_user(username='test', email='test@mail.com', password='password')

	def test_authenticated_user(self, client):
		client.force_login(self.user)
		response = client.get(reverse('user_auth_status'))
		assert response.status_code == status.HTTP_200_OK

	def test_unauthenticated_user(self, client):
		client.logout()
		response = client.get(reverse('user_auth_status'))
		assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAppBootstrapView:
	def test_anonymous_bootstrap_returns_csrf_and_auth_state(self, client):
		response = client.get(reverse('user_bootstrap'), headers={'X-Request-ID': 'bootstrap-test'})

		assert response.status_code == status.HTTP_200_OK
		assert response.json()['is_authenticated'] is False
		assert response.json()['local_world_access'] is False
		assert response.json()['csrf_token']
		assert response.json()['auth_methods']['password_login'] is True
		assert response['X-Request-ID'] == 'bootstrap-test'

	def test_authenticated_bootstrap_returns_session_state(self, client):
		client.force_login(TestFixtures.create_user())
		response = client.get(reverse('user_bootstrap'))

		assert response.status_code == status.HTTP_200_OK
		assert response.json()['is_authenticated'] is True

	def test_bootstrap_token_authorizes_csrf_protected_login(self):
		User.objects.create_user(username='csrf', email='csrf@example.com', password='Passwordpassword1!')
		csrf_client = Client(enforce_csrf_checks=True)
		bootstrap = csrf_client.get(reverse('user_bootstrap'))

		response = csrf_client.post(
			reverse('user_login'),
			{'email': 'csrf@example.com', 'password': 'Passwordpassword1!'},
			content_type='application/json',
			headers={'X-CSRFToken': bootstrap.json()['csrf_token']},
		)

		assert response.status_code == status.HTTP_200_OK
		refreshed_bootstrap = csrf_client.get(reverse('user_bootstrap'))
		assert refreshed_bootstrap.json()['is_authenticated'] is True

		logout_response = csrf_client.post(
			reverse('user_logout'),
			content_type='application/json',
			headers={'X-CSRFToken': refreshed_bootstrap.json()['csrf_token']},
		)
		assert logout_response.status_code == status.HTTP_200_OK

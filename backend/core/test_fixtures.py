from uuid import uuid4

from django.contrib.auth.models import User


class TestFixtures:
	@staticmethod
	def create_user():
		identity = uuid4().hex

		return User.objects.create_user(
			username=identity,
			first_name='Test',
			last_name='User',
			email=f'{identity}@notreal.fake',
			password='password',
		)

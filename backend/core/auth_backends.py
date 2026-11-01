from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
	def authenticate(self, request, email=None, password=None, **kwargs):
		user_model = get_user_model()
		username = kwargs.get('username')

		if not email and not username:
			return None

		try:
			user = user_model.objects.get(email=email) if email else user_model.objects.get(username=username)
		except user_model.DoesNotExist:
			return None

		if user.check_password(password) and self.user_can_authenticate(user):
			return user

		return None

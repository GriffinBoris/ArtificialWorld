from core.base_views import ProjectBaseAPIView
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from rest_framework.authentication import SessionAuthentication
from worlds.models import World

LOCAL_WORLD_USERNAME = 'artificial-world-local'


class WorldAuthentication(SessionAuthentication):
	def authenticate(self, request):
		if settings.WORLD_REQUIRE_LOGIN:
			return super().authenticate(request)

		self.enforce_csrf(request)
		user, _ = get_user_model().objects.get_or_create(
			username=LOCAL_WORLD_USERNAME, defaults={'password': make_password(None), 'is_active': False}
		)

		return user, None


class WorldBaseAPIView(ProjectBaseAPIView):
	authentication_classes = (WorldAuthentication,)

	def world_queryset(self, request):
		if not settings.WORLD_REQUIRE_LOGIN:
			return World.objects.all()

		return World.objects.filter(owner=request.user)

	def get_world(self, request, world_id):
		return get_object_or_404(self.world_queryset(request), id=world_id)

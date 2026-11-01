from core.base_views import ProjectBaseAPIView, ProjectBasePublicAPIView
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated


def test_project_base_api_view_is_authenticated_by_default():
	assert ProjectBaseAPIView.authentication_classes == (SessionAuthentication,)
	assert ProjectBaseAPIView.permission_classes == (IsAuthenticated,)


def test_public_api_view_requires_explicit_inheritance():
	assert ProjectBasePublicAPIView.authentication_classes == ()
	assert ProjectBasePublicAPIView.permission_classes == ()

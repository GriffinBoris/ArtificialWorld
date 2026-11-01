from core.base_views import ProjectBaseAPIView, ProjectBasePublicAPIView
from core.serializers import ChangePasswordSerializer, LoginSerializer, RegistrationSerializer
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.response import Response

AUTH_METHODS = {'google_sso': False, 'microsoft_sso': False, 'password_login': True}


class LogoutView(ProjectBaseAPIView):
	def post(self, request):
		logout(request)

		return Response(data={}, status=status.HTTP_200_OK)


class RegisterView(ProjectBasePublicAPIView):
	def post(self, request):
		user_serializer = RegistrationSerializer(data=request.data)
		user_serializer.is_valid(raise_exception=True)

		user = user_serializer.save()

		login(request, user)

		return Response(data={}, status=status.HTTP_200_OK)


class ValidateUserView(ProjectBasePublicAPIView):
	def post(self, request):
		serializer = RegistrationSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		return Response(data={}, status=status.HTTP_200_OK)


class AuthMethodsView(ProjectBasePublicAPIView):
	def get(self, request):
		return Response(data=AUTH_METHODS, status=status.HTTP_200_OK)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AppBootstrapView(ProjectBasePublicAPIView):
	authentication_classes = (SessionAuthentication,)

	def get(self, request):
		return Response(
			data={
				'auth_methods': AUTH_METHODS,
				'csrf_token': get_token(request),
				'is_authenticated': request.user.is_authenticated,
				'local_world_access': not settings.WORLD_REQUIRE_LOGIN,
			},
			status=status.HTTP_200_OK,
		)


class LoginView(ProjectBasePublicAPIView):
	def post(self, request):
		serializer = LoginSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		user = authenticate(request, email=serializer.data['email'], password=serializer.data['password'])

		if not user:
			errors = {
				'email': [ErrorDetail('Incorrect email or password.', code='invalid_credentials')],
				'password': [ErrorDetail('Incorrect email or password.', code='invalid_credentials')],
			}
			raise ValidationError(errors)

		login(request, user)

		return Response(data={}, status=status.HTTP_200_OK)


class PasswordChangeView(ProjectBaseAPIView):
	def post(self, request):
		serializer = ChangePasswordSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		if not request.user.check_password(serializer.data['current_password']):
			errors = {
				'current_password': [ErrorDetail('Incorrect password.', code='invalid_credentials')],
			}
			raise ValidationError(errors)

		request.user.set_password(serializer.data['new_password_one'])
		request.user.save()
		update_session_auth_hash(request, request.user)

		return Response(data={}, status=status.HTTP_200_OK)


class AuthStatusView(ProjectBaseAPIView):
	def get(self, request):
		return Response(data={}, status=status.HTTP_200_OK)

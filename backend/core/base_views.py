from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class ProjectBaseAPIView(APIView):
	authentication_classes = (SessionAuthentication,)
	permission_classes = (IsAuthenticated,)


class ProjectBasePublicAPIView(APIView):
	authentication_classes = ()
	permission_classes = ()

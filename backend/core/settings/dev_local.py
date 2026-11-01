import os

from core.settings.base import *  # noqa: F403

SECRET_KEY = 'django-insecure-qqx6=8frisj$dq3(ee5=epdzy1n^e-1y8(#!6al!c*ot=_$lz+'

DEBUG = True

BACKEND_DOMAIN = 'http://localhost:8000'
FRONTEND_DOMAIN = 'http://localhost:5173'

ALLOWED_HOSTS = ('localhost', '127.0.0.1', '[::1]')

CORS_ALLOWED_ORIGINS = [
	BACKEND_DOMAIN,
	FRONTEND_DOMAIN,
	'http://127.0.0.1:8000',
	'http://127.0.0.1:5173',
]

CSRF_TRUSTED_ORIGINS = [
	BACKEND_DOMAIN,
	FRONTEND_DOMAIN,
	'http://127.0.0.1:8000',
	'http://127.0.0.1:5173',
]

CORS_ALLOW_CREDENTIALS = True
CSRF_USE_SESSIONS = False
WORLD_REQUIRE_LOGIN = os.environ.get('WORLD_REQUIRE_LOGIN', '0') == '1'

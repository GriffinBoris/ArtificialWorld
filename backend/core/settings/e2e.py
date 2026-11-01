import os

from core.settings.base import TEMP_DIR
from core.settings.dev_pytest import *  # noqa: F403

BACKEND_DOMAIN = os.environ['BACKEND_DOMAIN']
FRONTEND_DOMAIN = os.environ['FRONTEND_DOMAIN']
WORLD_REQUIRE_LOGIN = os.environ.get('WORLD_REQUIRE_LOGIN', '0') == '1'

ALLOWED_HOSTS = ('localhost', '127.0.0.1')
CORS_ALLOWED_ORIGINS = (BACKEND_DOMAIN, FRONTEND_DOMAIN)
CSRF_TRUSTED_ORIGINS = (BACKEND_DOMAIN, FRONTEND_DOMAIN)

e2e_database_path = TEMP_DIR / 'db.e2e.sqlite3'
DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': e2e_database_path,
		'TEST': {'NAME': e2e_database_path},
	}
}

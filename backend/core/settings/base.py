import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR.parent / 'temp'
WORLD_ALLOW_LIVE_AI = os.environ.get('WORLD_ALLOW_LIVE_AI', '0') == '1'
WORLD_AI_PROVIDER = os.environ.get('WORLD_AI_PROVIDER', 'opencode-go')
WORLD_THINKING_SLOTS = int(os.environ.get('WORLD_THINKING_SLOTS', '4'))
MAX_THINKING_SLOTS = 16

if not 1 <= WORLD_THINKING_SLOTS <= MAX_THINKING_SLOTS:
	raise ValueError('WORLD_THINKING_SLOTS must be between 1 and 16.')

OPENCODE_GO_API_KEY = os.environ.get('OPENCODE_GO_API_KEY', '')
WORLD_REQUIRE_LOGIN = True

os.makedirs(TEMP_DIR, exist_ok=True)

SECRET_KEY = 'django-insecure-c2oxf1u+np!$_5^v23aht-1u!vik=#(#3qz=gg*8#u#mrz$4x-'

DEBUG = True

ALLOWED_HOSTS = ()

BASE_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
	'corsheaders',
	'rest_framework',
	'drf_standardized_errors',
	'drf_spectacular',
]

CUSTOM_APPS = [
	'worlds.apps.WorldsConfig',
	'core',
]

INSTALLED_APPS = BASE_APPS + THIRD_PARTY_APPS + CUSTOM_APPS

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'core.request_logging.RequestLoggingMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'corsheaders.middleware.CorsMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
		},
	},
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': BASE_DIR / 'db.sqlite3',
	}
}

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]

AUTHENTICATION_BACKENDS = ['core.auth_backends.EmailBackend']

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR.parent / 'static'

FRONTEND_DIST_DIR = BASE_DIR.parent.parent / 'frontend' / 'dist'
STATICFILES_DIRS = [FRONTEND_DIST_DIR] if FRONTEND_DIST_DIR.exists() else []

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATICFILES_FINDERS = [
	'django.contrib.staticfiles.finders.FileSystemFinder',
	'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'formatters': {
		'json': {
			'()': 'core.request_logging.JsonFormatter',
		},
	},
	'handlers': {
		'console': {
			'level': LOG_LEVEL,
			'class': 'logging.StreamHandler',
			'formatter': 'json',
			'filters': ['request_context'],
		},
		'django.server': {
			'level': LOG_LEVEL,
			'class': 'logging.StreamHandler',
			'formatter': 'json',
			'filters': ['request_context'],
		},
		'mail_admins': {
			'level': 'ERROR',
			'class': 'django.utils.log.AdminEmailHandler',
			'include_html': True,
			'filters': ['require_debug_false'],
		},
	},
	'filters': {
		'require_debug_false': {
			'()': 'django.utils.log.RequireDebugFalse',
		},
		'request_context': {
			'()': 'core.request_logging.RequestContextFilter',
		},
	},
	'loggers': {
		'django.request': {
			'handlers': ['console'],
			'level': LOG_LEVEL,
			'propagate': False,
		},
		'django.server': {
			'handlers': ['django.server'],
			'level': LOG_LEVEL,
			'propagate': False,
		},
	},
	'root': {
		'handlers': ['console', 'mail_admins'],
		'level': LOG_LEVEL,
	},
}

REST_FRAMEWORK = {
	'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
	'DEFAULT_PARSER_CLASSES': ('rest_framework.parsers.JSONParser',),
	'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
	'EXCEPTION_HANDLER': 'drf_standardized_errors.handler.exception_handler',
}

SPECTACULAR_SETTINGS = {
	'TITLE': 'Artificial World',
	'DESCRIPTION': '',
	'VERSION': '1.0.0',
	'SERVE_INCLUDE_SCHEMA': False,
	'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAdminUser'],
}

MINIMUM_PASSWORD_LENGTH = 15
MAXIMUM_PASSWORD_LENGTH = 64


STORAGES = {
	'default': {
		'BACKEND': 'django.core.files.storage.FileSystemStorage',
		'OPTIONS': {
			'location': TEMP_DIR / 'storage',
		},
	},
	'staticfiles': {
		'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
	},
}


CACHES = {
	'default': {
		'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
		'LOCATION': 'unique-snowflake',
	}
}

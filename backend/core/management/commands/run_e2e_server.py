from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
	help = 'Rebuild deterministic e2e data and run the Django development server.'

	def add_arguments(self, parser):
		parser.add_argument('--addrport', default='127.0.0.1:8000')

	def handle(self, *args, **options):
		connections.close_all()
		database_path = Path(settings.DATABASES['default']['NAME'])

		if database_path.exists():
			database_path.unlink()

		call_command('migrate', interactive=False, verbosity=0)
		get_user_model().objects.create_user(
			username='e2e@example.com',
			email='e2e@example.com',
			password='Passwordpassword1!',
		)
		call_command('runserver', options['addrport'], use_reloader=False)

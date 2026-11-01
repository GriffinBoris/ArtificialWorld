from enum import Enum

from django.conf import settings
from django.utils.translation import gettext_lazy


class Messages(Enum):
	EMAIL_ALREADY_IN_USE = gettext_lazy('Email already in use.')
	PASSWORDS_MUST_MATCH = gettext_lazy('Passwords must match.')
	PASSWORD_TOO_SHORT = gettext_lazy('Passwords must be at least %(min_password_length)s characters long.') % {
		'min_password_length': settings.MINIMUM_PASSWORD_LENGTH
	}
	PASSWORD_TOO_LONG = gettext_lazy('Passwords must be at most %(max_password_length)s characters long.') % {
		'max_password_length': settings.MAXIMUM_PASSWORD_LENGTH
	}
	PASSWORD_NO_UPPERCASE = gettext_lazy('Passwords must contain at least 1 upper case letter.')
	PASSWORD_NO_LOWERCASE = gettext_lazy('Passwords must contain at least 1 lower case letter.')
	PASSWORD_NO_NUMBER = gettext_lazy('Passwords must contain at least 1 number.')
	PASSWORD_NO_SYMBOL = gettext_lazy('Passwords must contain at least 1 symbol.')

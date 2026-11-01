import string

from core.messages import Messages
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
	email = serializers.EmailField(allow_null=False, allow_blank=False)
	password = serializers.CharField(allow_null=False, allow_blank=False)


class RegistrationSerializer(serializers.Serializer):
	email = serializers.EmailField(allow_null=False, allow_blank=False)
	first_name = serializers.CharField(allow_null=False, allow_blank=False)
	last_name = serializers.CharField(allow_null=False, allow_blank=False)
	password_one = serializers.CharField(allow_null=False, allow_blank=False)
	password_two = serializers.CharField(allow_null=False, allow_blank=False)

	def validate_email(self, value):
		if User.objects.filter(email=value).exists():
			raise serializers.ValidationError(Messages.EMAIL_ALREADY_IN_USE.value)

		return value

	def validate_password_one(self, value):
		if len(value) < settings.MINIMUM_PASSWORD_LENGTH:
			raise serializers.ValidationError(Messages.PASSWORD_TOO_SHORT.value)

		if len(value) > settings.MAXIMUM_PASSWORD_LENGTH:
			raise serializers.ValidationError(Messages.PASSWORD_TOO_LONG.value)

		return value

	def validate(self, attrs):
		password_one = attrs['password_one']
		password_two = attrs['password_two']

		if password_one != password_two:
			raise serializers.ValidationError(
				{
					'password_one': Messages.PASSWORDS_MUST_MATCH.value,
					'password_two': Messages.PASSWORDS_MUST_MATCH.value,
				}
			)

		return attrs

	def create(self, validated_data):
		email = validated_data['email']
		password_one = validated_data['password_one']
		first_name = validated_data['first_name']
		last_name = validated_data['last_name']

		return User.objects.create_user(
			username=email,
			email=email,
			password=password_one,
			first_name=first_name,
			last_name=last_name,
		)


class ChangePasswordSerializer(serializers.Serializer):
	current_password = serializers.CharField(allow_null=False, allow_blank=False)
	new_password_one = serializers.CharField(allow_null=False, allow_blank=False)
	new_password_two = serializers.CharField(allow_null=False, allow_blank=False)

	def validate(self, attrs):
		new_password_one = attrs['new_password_one']
		new_password_two = attrs['new_password_two']

		if new_password_one != new_password_two:
			raise serializers.ValidationError(
				{
					'new_password_one': Messages.PASSWORDS_MUST_MATCH.value,
					'new_password_two': Messages.PASSWORDS_MUST_MATCH.value,
				}
			)

		if len(new_password_one) < settings.MINIMUM_PASSWORD_LENGTH:
			raise serializers.ValidationError({'new_password_two': Messages.PASSWORD_TOO_SHORT.value})

		upper_case_letters = [i for i in new_password_two if i in string.ascii_uppercase]

		if not upper_case_letters:
			raise serializers.ValidationError({'new_password_two': Messages.PASSWORD_NO_UPPERCASE.value})

		lower_case_letters = [i for i in new_password_two if i in string.ascii_lowercase]

		if not lower_case_letters:
			raise serializers.ValidationError({'new_password_two': Messages.PASSWORD_NO_LOWERCASE.value})

		digits = [i for i in new_password_two if i in string.digits]

		if not digits:
			raise serializers.ValidationError({'new_password_two': Messages.PASSWORD_NO_NUMBER.value})

		symbols = [i for i in new_password_two if i in string.punctuation]

		if not symbols:
			raise serializers.ValidationError({'new_password_two': Messages.PASSWORD_NO_SYMBOL.value})

		return attrs

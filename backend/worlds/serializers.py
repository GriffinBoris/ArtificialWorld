import math

from pydantic import ValidationError as ContractValidationError
from rest_framework import serializers
from worlds.models import World, WorldEvent
from worlds.services.editor import WorldEdit
from worlds.services.state import load_state
from worlds.simulation.actions import Action
from worlds.simulation.contracts import WorldConfig


class WorldInputSerializer(serializers.Serializer):
	name = serializers.CharField(max_length=120, default='First light')
	configuration = serializers.JSONField(default=dict)
	population = serializers.IntegerField(default=6, min_value=1, max_value=10)

	def validate_configuration(self, value):
		try:
			return WorldConfig.model_validate(value).model_dump(mode='json')
		except ContractValidationError as error:
			raise serializers.ValidationError(str(error)) from error


class WorldOutputSerializer(serializers.ModelSerializer):
	class Meta:
		model = World
		fields = ('id', 'name', 'configuration', 'tick', 'revision', 'status', 'error', 'event_sequence', 'created_ts')
		read_only_fields = fields


class WorldDetailSerializer(WorldOutputSerializer):
	class Meta(WorldOutputSerializer.Meta):
		fields = (*WorldOutputSerializer.Meta.fields, 'state')
		read_only_fields = fields

	state = serializers.SerializerMethodField()

	def get_state(self, instance):
		return load_state(instance).model_dump(mode='json')


class WorldEventSerializer(serializers.ModelSerializer):
	class Meta:
		model = WorldEvent
		fields = ('id', 'sequence', 'tick', 'kind', 'actor_id', 'subject_id', 'data')
		read_only_fields = fields


class FiniteFloatField(serializers.FloatField):
	def to_internal_value(self, data):
		value = super().to_internal_value(data)

		if not math.isfinite(value):
			raise serializers.ValidationError('Enter a finite number.')

		return value


class StepInputSerializer(serializers.Serializer):
	seconds = FiniteFloatField(default=1, min_value=0.1, max_value=10)


class StatusInputSerializer(serializers.Serializer):
	status = serializers.ChoiceField(choices=('paused', 'running'))


class ActionInputSerializer(serializers.Serializer):
	action = serializers.JSONField()

	def validate_action(self, value):
		try:
			return Action.model_validate(value)
		except ContractValidationError as error:
			raise serializers.ValidationError(str(error)) from error


class MemoryInputSerializer(serializers.Serializer):
	text = serializers.CharField(max_length=8000)
	confidence = FiniteFloatField(default=0.5, min_value=0, max_value=1)


class AgentSettingsInputSerializer(serializers.Serializer):
	actor_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
	driver = serializers.ChoiceField(choices=('scripted', 'pydantic'))
	model_name = serializers.CharField(max_length=120, allow_blank=True, default='')
	allow_live_models = serializers.BooleanField(default=False)


class WorldEditInputSerializer(serializers.Serializer):
	edit = serializers.JSONField()

	def validate_edit(self, value):
		try:
			return WorldEdit.model_validate(value)
		except ContractValidationError as error:
			raise serializers.ValidationError(str(error)) from error

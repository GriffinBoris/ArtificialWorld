import asyncio

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from worlds.access import WorldBaseAPIView
from worlds.agents.providers import provider_available
from worlds.models import Inhabitant
from worlds.serializers import (
	ActionInputSerializer,
	AgentSettingsInputSerializer,
	MemoryInputSerializer,
	StatusInputSerializer,
	StepInputSerializer,
	WorldDetailSerializer,
	WorldEditInputSerializer,
	WorldEventSerializer,
	WorldInputSerializer,
	WorldOutputSerializer,
)
from worlds.services.editor import configure_agents, edit_world
from worlds.services.inhabitants import observation, read_document, search_memories, submit_action, write_memory
from worlds.services.inspection import inspect_records
from worlds.services.profiles import inhabitant_profile, world_messages
from worlds.services.recordings import decode_recording, motion_deltas, replay_state
from worlds.services.state import world_lock, WorldBusy
from worlds.services.worlds import advance_world, create_world, set_world_status
from worlds.simulation.contracts import WorldConfig
from worlds.simulation.terrain import terrain_grid


class WorldListView(WorldBaseAPIView):
	def get(self, request):
		return Response(WorldOutputSerializer(self.world_queryset(request).order_by('-created_ts'), many=True).data)

	def post(self, request):
		serializer = WorldInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		world = create_world(request.user, **serializer.validated_data)

		return Response(WorldDetailSerializer(world).data, status=201)


class WorldDetailView(WorldBaseAPIView):
	def delete(self, request, world_id):
		with world_lock(world_id), transaction.atomic():
			world = self.get_world(request, world_id)

			if world.status == 'running' or world.decisions.filter(status='thinking').exists():
				raise WorldBusy('Pause this world and wait for its current decisions to finish before deleting it.')

			world.delete()

		return Response(status=204)

	@transaction.atomic
	def get(self, request, world_id):
		world = self.get_world(request, world_id)

		return Response(WorldDetailSerializer(world).data)


class WorldTerrainView(WorldBaseAPIView):
	def get(self, request, world_id):
		world = self.get_world(request, world_id)
		config = WorldConfig.model_validate(world.configuration)

		return Response({'size': config.size, 'water_level': config.water_level, 'heights': terrain_grid(config)})


class WorldStepView(WorldBaseAPIView):
	def post(self, request, world_id):
		self.get_world(request, world_id)
		serializer = StepInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		world = advance_world(world_id, serializer.validated_data['seconds'], owner_step=True)

		return Response(WorldDetailSerializer(world).data)


class WorldStatusView(WorldBaseAPIView):
	def post(self, request, world_id):
		self.get_world(request, world_id)
		serializer = StatusInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		return Response(WorldOutputSerializer(set_world_status(world_id, serializer.validated_data['status'])).data)


class WorldEventsView(WorldBaseAPIView):
	def get(self, request, world_id):
		world = self.get_world(request, world_id)
		after = serializers.IntegerField(min_value=0).run_validation(request.query_params.get('after', 0))

		return Response(
			WorldEventSerializer(world.events.filter(sequence__gt=after).order_by('sequence')[:200], many=True).data
		)


class WorldReplayView(WorldBaseAPIView):
	def get(self, request, world_id):
		world = self.get_world(request, world_id)
		tick = serializers.IntegerField(min_value=0, max_value=world.tick).run_validation(
			request.query_params.get('tick', world.tick)
		)
		state = replay_state(world, tick)

		return Response({'state': state.model_dump(mode='json'), 'requested_tick': tick, 'recorded_tick': state.tick})


class WorldMotionView(WorldBaseAPIView):
	def get(self, request, world_id):
		world = self.get_world(request, world_id)
		after = serializers.IntegerField(min_value=0, max_value=world.tick).run_validation(
			request.query_params.get('after', 0)
		)
		until = min(world.tick, after + 600)
		frames = [
			frame
			for block in world.motion_blocks.filter(end_tick__gt=after, start_tick__lt=until).order_by(
				'start_tick', 'id'
			)
			for frame in decode_recording(block)
			if after < frame['tick'] <= until
		]

		return Response({'frames': motion_deltas(frames), 'until_tick': until})


class InhabitantObservationView(WorldBaseAPIView):
	@transaction.atomic
	def get(self, request, world_id, actor_id):
		world = self.get_world(request, world_id)
		get_object_or_404(Inhabitant, world=world, entity_id=actor_id)

		return Response(observation(world, actor_id))


class InhabitantActionView(WorldBaseAPIView):
	def post(self, request, world_id, actor_id):
		world = self.get_world(request, world_id)
		get_object_or_404(Inhabitant, world=world, entity_id=actor_id)
		serializer = ActionInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		activity = submit_action(world_id, actor_id, serializer.validated_data['action'])

		return Response(activity.model_dump(mode='json'), status=202)


class InhabitantMemoryView(WorldBaseAPIView):
	def get(self, request, world_id, actor_id):
		world = self.get_world(request, world_id)
		get_object_or_404(Inhabitant, world=world, entity_id=actor_id)
		query = serializers.CharField(max_length=200, allow_blank=True).run_validation(
			request.query_params.get('q', '')
		)

		return Response(search_memories(actor_id, query))

	def post(self, request, world_id, actor_id):
		world = self.get_world(request, world_id)
		get_object_or_404(Inhabitant, world=world, entity_id=actor_id)
		serializer = MemoryInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		memory = write_memory(world_id, actor_id, **serializer.validated_data)

		return Response(
			{'id': memory.id, 'text': memory.text, 'confidence': memory.confidence, 'tick': memory.tick}, status=201
		)


class InhabitantDocumentView(WorldBaseAPIView):
	def get(self, request, world_id, actor_id, artifact_id):
		world = self.get_world(request, world_id)
		get_object_or_404(Inhabitant, world=world, entity_id=actor_id)

		return Response(read_document(world_id, actor_id, artifact_id))


class WorldAgentSettingsView(WorldBaseAPIView):
	def get(self, request, world_id):
		self.get_world(request, world_id)

		return Response(
			{
				'server_enabled': settings.WORLD_ALLOW_LIVE_AI,
				'subscription_authorized': asyncio.run(provider_available()),
				'provider': settings.WORLD_AI_PROVIDER,
				'supported_drivers': ['scripted', 'pydantic'],
				'thinking_slots': settings.WORLD_THINKING_SLOTS,
			}
		)

	def post(self, request, world_id):
		self.get_world(request, world_id)
		serializer = AgentSettingsInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		return Response(WorldDetailSerializer(configure_agents(world_id, **serializer.validated_data)).data)


class WorldEditView(WorldBaseAPIView):
	def post(self, request, world_id):
		self.get_world(request, world_id)
		serializer = WorldEditInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		return Response(WorldDetailSerializer(edit_world(world_id, serializer.validated_data['edit'])).data)


class WorldInspectView(WorldBaseAPIView):
	def get(self, request, world_id, entity_id):
		world = self.get_world(request, world_id)
		tick = (
			serializers.IntegerField(min_value=0, max_value=world.tick).run_validation(request.query_params['tick'])
			if 'tick' in request.query_params
			else None
		)

		return Response(inspect_records(world, entity_id, tick))


class WorldMessagesView(WorldBaseAPIView):
	def get(self, request, world_id):
		world = self.get_world(request, world_id)
		tick = (
			serializers.IntegerField(min_value=0, max_value=world.tick).run_validation(request.query_params['tick'])
			if 'tick' in request.query_params
			else None
		)

		return Response(world_messages(world, tick=tick))


class InhabitantProfileView(WorldBaseAPIView):
	@transaction.atomic
	def get(self, request, world_id, actor_id):
		world = self.get_world(request, world_id)
		get_object_or_404(Inhabitant, world=world, entity_id=actor_id)
		tick = (
			serializers.IntegerField(min_value=0, max_value=world.tick).run_validation(request.query_params['tick'])
			if 'tick' in request.query_params
			else None
		)

		return Response(inhabitant_profile(world, actor_id, tick))

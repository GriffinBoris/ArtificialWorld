from typing import Literal, Optional
from uuid import UUID

from django.db import transaction
from pydantic import Field, model_validator
from rest_framework.exceptions import ValidationError
from worlds.models import World
from worlds.services.decisions import complete_action_tools
from worlds.services.recordings import save_checkpoint
from worlds.services.state import append_events, load_state, persist_state, world_lock, WorldBusy
from worlds.simulation.contracts import Contract, EntityState, MATERIALS, SimulationEvent
from worlds.simulation.ecology import enable_ecology, resource_profile
from worlds.simulation.rules import MIN_WORLD_ELEVATION


class NewPart(Contract):
	name: str = Field(default='Placed part', min_length=1, max_length=120)
	material: Literal['wood', 'stone', 'fiber', 'food'] = 'wood'
	shape: Literal['box', 'sphere', 'cylinder'] = 'box'
	dimensions: tuple[float, float, float] = (0.5, 0.5, 0.5)
	position: tuple[float, float, float] = (0, 0, 4)
	fixed: bool = False
	kind: Literal['part', 'resource'] = 'part'

	@model_validator(mode='after')
	def valid_part(self):
		entity = EntityState(**self.model_dump())
		EntityState(**{**self.model_dump(), 'mass': entity.volume * MATERIALS[self.material].density})

		return self


class WorldEdit(Contract):
	kind: Literal['create', 'move', 'remove', 'body', 'ecology']
	target_id: Optional[UUID] = None
	part: Optional[NewPart] = None
	position: Optional[tuple[float, float, float]] = None
	metric: Literal['health', 'food', 'water', 'energy', 'wear', 'injury', 'stress'] = 'food'
	value: float = Field(default=100, ge=0, le=100)

	@model_validator(mode='after')
	def required_arguments(self):
		if self.kind == 'create' and self.part is None:
			raise ValueError('Creating a part requires part properties.')

		if self.kind not in ('create', 'ecology') and self.target_id is None:
			raise ValueError('This edit requires a target_id.')

		if self.kind == 'move' and self.position is None:
			raise ValueError('Moving an object requires a position.')

		return self


def editable_state(world):
	if world.status != 'paused':
		raise ValidationError('Pause the world before editing it.')

	if world.decisions.filter(status='thinking').exists():
		raise WorldBusy('Wait for the current decision round to finish before editing.')

	return load_state(world)


def edit_world(world_id, edit):
	with world_lock(world_id), transaction.atomic():
		world = World.objects.select_for_update().get(id=world_id)
		state = editable_state(world)

		if edit.kind == 'ecology':
			enable_ecology(state)
			append_events(
				world,
				[
					SimulationEvent(
						kind='editor.ecology_enabled',
						tick=state.tick,
						data={'area_ids': [area.id for area in state.resource_areas]},
					)
				],
			)
			persist_state(world, state)
			save_checkpoint(world, state)

			return world

		if edit.kind == 'create':
			entity = EntityState(**edit.part.model_dump())
			entity.mass = entity.volume * MATERIALS[entity.material].density

			if entity.kind == 'resource' and entity.fixed:
				entity.resource = resource_profile(entity)
		else:
			entity = next((entity for entity in state.entities if entity.id == str(edit.target_id)), None)

			if entity is None:
				raise ValidationError('That object is not in this world.')

		position = edit.position if edit.kind == 'move' else entity.position

		if (
			any(abs(value) > state.config.size / 2 for value in position[:2])
			or not MIN_WORLD_ELEVATION <= position[2] <= state.config.ceiling
		):
			raise ValidationError('The position lies outside the world.')

		if edit.kind == 'create':
			state.entities.append(entity)
		elif edit.kind in ('move', 'remove'):
			if edit.kind == 'remove' and entity.kind in ('inhabitant', 'corpse'):
				raise ValidationError('Inhabitant histories are retained. Adjust health instead of deleting a body.')

			state.joints = [joint for joint in state.joints if entity.id not in (joint.entity_a, joint.entity_b)]

			for agent in state.inhabitants:
				if agent.id == entity.id:
					agent.held_ids.clear()

				if entity.id in agent.held_ids:
					agent.held_ids.remove(entity.id)

			if edit.kind == 'remove':
				state.entities.remove(entity)
			else:
				entity.position = edit.position
				entity.velocity = (0, 0, 0)
				entity.angular_velocity = (0, 0, 0)
		elif edit.kind == 'body':
			agent = next((agent for agent in state.inhabitants if agent.id == entity.id and agent.alive), None)

			if agent is None:
				raise ValidationError('Select a living inhabitant to adjust its condition.')

			agent.body = agent.body.model_copy(update={edit.metric: edit.value})

		append_events(
			world,
			[
				SimulationEvent(
					kind='editor.intervened',
					tick=state.tick,
					subject_id=entity.id,
					data={'edit': edit.model_dump(mode='json'), 'entity': entity.model_dump(mode='json')},
				)
			],
		)
		persist_state(world, state)
		save_checkpoint(world, state)

		return world


def configure_agents(world_id, actor_ids, driver, model_name, allow_live_models):
	with world_lock(world_id), transaction.atomic():
		world = World.objects.select_for_update().get(id=world_id)
		state = editable_state(world)
		identities = {str(value) for value in actor_ids}

		if not identities.issubset({agent.id for agent in state.inhabitants if agent.alive}):
			raise ValidationError('Choose living inhabitants from this world.')

		if driver != 'scripted' and not model_name:
			raise ValidationError('An explicit subscription model name is required.')

		cancelled = []

		for agent in state.inhabitants:
			if agent.id in identities:
				if agent.activity:
					result = {
						'kind': agent.activity.kind,
						'status': 'failed',
						'reason': 'Agent settings changed before this activity finished.',
						'position': state.entity(agent.id).position,
					}
					cancelled.append(
						SimulationEvent(
							kind='activity.failed',
							tick=state.tick,
							actor_id=agent.id,
							subject_id=agent.activity.id,
							data=result,
						)
					)
					agent.last_action_result = {'activity_id': agent.activity.id, 'tick': state.tick, **result}

				agent.driver = driver
				agent.model_name = model_name if driver != 'scripted' else ''
				agent.activity = None
				agent.wake_tick = state.tick

		state.config.allow_live_models = allow_live_models
		complete_action_tools(world, cancelled)
		append_events(world, cancelled)
		append_events(
			world,
			[
				SimulationEvent(
					kind='editor.agents_configured',
					tick=state.tick,
					data={
						'actor_ids': sorted(identities),
						'driver': driver,
						'model_name': model_name,
						'allow_live_models': allow_live_models,
					},
				)
			],
		)
		persist_state(world, state)
		save_checkpoint(world, state)

		return world

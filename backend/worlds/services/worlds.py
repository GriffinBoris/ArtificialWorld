import math
import random

from django.db import transaction
from rest_framework.exceptions import ValidationError
from worlds.models import World
from worlds.services.artifacts import persist_artifact_events
from worlds.services.decisions import complete_action_tools
from worlds.services.programs import persist_program_events, run_programs
from worlds.services.recordings import save_checkpoint, save_motion
from worlds.services.state import append_events, load_state, persist_state, world_lock
from worlds.simulation.actions import Action, begin_action
from worlds.simulation.contracts import SimulationEvent, WorldConfig, WorldState
from worlds.simulation.engine import Simulation
from worlds.simulation.generation import populate

SCRIPTED_GREETINGS = (
	'Hello! I think I will have a little look around.',
	'This looks like a lovely place to start.',
	'I wonder what is over that hill.',
	'Good to see some friendly faces here!',
	'There is a whole world out there. Shall we explore?',
	'I might find us a nice spot by the trees.',
)


@transaction.atomic
def create_world(owner, name, configuration, population):
	config = WorldConfig.model_validate(configuration)
	world = World.objects.create(owner=owner, name=name, configuration=config.model_dump(mode='json'))
	state = populate(WorldState(config=config), population)
	append_events(
		world,
		[
			SimulationEvent(
				kind='world.created',
				tick=0,
				data={'seed': config.seed, 'population': population, 'rules_version': config.rules_version},
			)
		],
	)
	persist_state(world, state)
	save_checkpoint(world, state)

	return world


def scripted_decisions(state):
	events = []

	for inhabitant in state.inhabitants:
		if (
			inhabitant.driver != 'scripted'
			or not inhabitant.alive
			or inhabitant.activity is not None
			or inhabitant.wake_tick > state.tick
		):
			continue

		entity = state.entity(inhabitant.id)
		rng = random.Random(f'{state.config.seed}:{inhabitant.id}:{state.tick}')
		angle = rng.uniform(0, math.tau)
		length = rng.uniform(8, 25)
		half = state.config.size / 2 - 2
		destination = [
			max(-half, min(half, entity.position[0] + math.cos(angle) * length)),
			max(-half, min(half, entity.position[1] + math.sin(angle) * length)),
		]
		voice = int(inhabitant.id.replace('-', '')[-4:], 16) % len(SCRIPTED_GREETINGS)

		if inhabitant.last_decision_tick < 0 or (state.tick > 30 * state.config.physics_hz and rng.randrange(5) == 0):
			action = Action(kind='speak', seconds=1 + voice * 0.2, text=SCRIPTED_GREETINGS[voice])
		else:
			action = Action(kind='walk', destination=(*destination, entity.position[2]))

		begin_action(state, inhabitant.id, action)
		events.append(
			SimulationEvent(
				kind='activity.started',
				tick=state.tick,
				actor_id=inhabitant.id,
				subject_id=inhabitant.activity.id,
				data=inhabitant.activity.model_dump(mode='json'),
			)
		)

	return events


def advance_world(world_id, seconds=1, owner_step=False, independent=False):
	with world_lock(world_id), transaction.atomic():
		world = World.objects.select_for_update().get(id=world_id)

		if not owner_step and world.status != 'running':
			return world

		state = load_state(world)

		if not independent and world.decisions.filter(status='thinking').exists():
			raise ValidationError('The world is waiting for an agent decision round.')

		if not independent and any(
			inhabitant.alive
			and inhabitant.driver != 'scripted'
			and inhabitant.activity is None
			and inhabitant.wake_tick <= state.tick
			for inhabitant in state.inhabitants
		):
			raise ValidationError(
				'An inhabitant needs a model decision. Run its configured agent scheduler before advancing.'
			)

		start_tick = state.tick
		end_tick = start_tick + round(seconds * state.config.physics_hz)
		frames = []
		simulation = Simulation(state)

		try:
			while state.tick < end_tick:
				events = run_programs(world, state)
				events.extend(scripted_decisions(state))
				append_events(world, events)
				next_program_tick = (
					world.programs.filter(enabled=True, next_tick__gt=state.tick)
					.order_by('next_tick')
					.values_list('next_tick', flat=True)
					.first()
				)
				chunk_end = min(end_tick, state.tick + state.config.physics_hz, next_program_tick or end_tick)
				frames.extend(
					simulation.advance(
						(chunk_end - state.tick) / state.config.physics_hz, stop_at_decision=not independent
					)
				)
				persist_artifact_events(world, simulation.events)
				persist_program_events(world, simulation.events)
				complete_action_tools(world, simulation.events)
				append_events(world, simulation.events)
				simulation.events.clear()

				if not independent and any(
					agent.alive
					and agent.driver != 'scripted'
					and agent.activity is None
					and agent.wake_tick <= state.tick
					for agent in state.inhabitants
				):
					break
		finally:
			simulation.close()

		append_events(
			world,
			[
				SimulationEvent(
					kind='world.advanced', tick=state.tick, data={'from_tick': start_tick, 'to_tick': state.tick}
				)
			],
		)
		persist_state(world, state)
		save_motion(world, start_tick, state, frames)
		save_checkpoint(world, state)

		return world


def set_world_status(world_id, status):
	with world_lock(world_id), transaction.atomic():
		world = World.objects.select_for_update().get(id=world_id)
		world.status = status
		world.error = ''
		world.revision += 1
		append_events(world, [SimulationEvent(kind=f'world.{status}', tick=world.tick)])
		world.save(update_fields=('status', 'error', 'revision', 'event_sequence', 'updated_ts'))

		return world

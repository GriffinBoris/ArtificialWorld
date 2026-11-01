import json

from worlds.models import Artifact, ArtifactVersion, Inhabitant, SimulationProgram
from worlds.simulation.actions import distance
from worlds.simulation.contracts import SimulationEvent
from worlds.simulation.programs import ProgramError, SimulationProgramVM, validate_program
from worlds.simulation.rules import INITIAL_DEVICE_POWER, SPEECH_RANGE

POWER_COST_PER_INSTRUCTION = 0.001


def persist_program_events(world, events):
	for event in events:
		if event.kind != 'program.deployed':
			continue

		data = event.data
		agent = Inhabitant.objects.get(world=world, entity_id=event.actor_id)
		artifact = Artifact.objects.create(
			world=world,
			author=agent,
			location_id=data['host_id'],
			position=data['position'],
			title=data['title'],
			kind='program',
			created_tick=event.tick,
		)
		version = ArtifactVersion.objects.create(
			artifact=artifact, author=agent, version=1, content=data['source'], tick=event.tick
		)
		program = SimulationProgram.objects.create(
			artifact_version=version,
			world=world,
			owner=agent,
			host_id=data['host_id'],
			enabled=True,
			next_tick=event.tick,
			state={'records': {}, 'power': INITIAL_DEVICE_POWER, 'inbox_after': world.event_sequence},
		)
		event.subject_id = str(program.pk)
		event.data['artifact_id'] = str(artifact.id)


def run_programs(world, state):
	events = []

	for program in world.programs.filter(enabled=True, next_tick__lte=state.tick).select_related(
		'artifact_version', 'host'
	):
		host = state.entity(str(program.host_id))

		if program.state['power'] <= 0:
			program.enabled = False
			program.save(update_fields=('enabled',))
			events.append(SimulationEvent(kind='program.unpowered', tick=state.tick, subject_id=str(program.pk)))
			continue

		inbox = [
			{'speaker': message.actor_id, 'text': message.data['text']}
			for message in world.events.filter(
				sequence__gt=program.state['inbox_after'], kind='message.spoken'
			).order_by('sequence')
			if host.id in message.data.get('recipient_ids', [])
		][-20:]

		try:
			instructions = validate_program(program.artifact_version.content)
			vm = SimulationProgramVM(
				program.state['records'],
				{'tick': state.tick, 'inbox': inbox, 'name': program.artifact_version.artifact.title},
			)
			result = vm.run(instructions)
			cost = result['instructions_used'] * POWER_COST_PER_INSTRUCTION

			if cost > program.state['power']:
				raise ProgramError('Device ran out of power.')

			program.state = {
				'records': result['records'],
				'power': program.state['power'] - cost,
				'inbox_after': world.event_sequence,
			}
			program.next_tick = state.tick + state.config.physics_hz
			program.save(update_fields=('state', 'next_tick', 'updated_ts'))
			events.append(
				SimulationEvent(
					kind='program.executed',
					tick=state.tick,
					subject_id=str(program.pk),
					data={
						'instructions': result['instructions_used'],
						'records': result['records'],
						'power': program.state['power'],
					},
				)
			)
			recipients = [
				agent.id
				for agent in state.inhabitants
				if agent.alive and distance(state.entity(agent.id).position, host.position) <= SPEECH_RANGE
			]
			recipients.extend(
				str(other.host_id)
				for other in world.programs.filter(enabled=True).exclude(pk=program.pk)
				if distance(state.entity(str(other.host_id)).position, host.position) <= SPEECH_RANGE
			)

			for text in result['messages']:
				events.append(
					SimulationEvent(
						kind='message.spoken',
						tick=state.tick,
						actor_id=host.id,
						data={
							'text': text,
							'speaker_name': host.name,
							'position': host.position,
							'recipient_ids': recipients,
							'program_id': str(program.pk),
						},
					)
				)
		except (ProgramError, TypeError, KeyError, RecursionError, json.JSONDecodeError) as error:
			program.enabled = False
			program.save(update_fields=('enabled',))
			events.append(
				SimulationEvent(
					kind='program.failed', tick=state.tick, subject_id=str(program.pk), data={'reason': str(error)}
				)
			)

	return events

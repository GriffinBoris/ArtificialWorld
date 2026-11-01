import math

from worlds.simulation.actions import Action, ActionRejected, distance, reachable
from worlds.simulation.contracts import SimulationEvent
from worlds.simulation.ecology import Ecology
from worlds.simulation.manipulation import Manipulation
from worlds.simulation.naming import choose_name
from worlds.simulation.programs import SimulationProgramVM, validate_program
from worlds.simulation.rules import INITIAL_DEVICE_POWER, MASS_EPSILON, REPRODUCTION_CONDITION, SPEECH_RANGE
from worlds.simulation.terrain import surface_height


def complete_activity(state, physics, actor):
	activity = actor.activity
	action = Action.model_validate(activity.parameters)
	events = []
	manipulation = Manipulation(state, physics)
	ecology = Ecology(state, physics, manipulation)
	target = (
		reachable(state, actor, action.target_id)
		if action.target_id and action.kind not in ('detach', 'consent', 'name_child')
		else None
	)

	if action.kind in ('name_self', 'name_child'):
		events.append(choose_name(state, actor, action))
	elif action.kind == 'grasp':
		manipulation.grasp(actor, target)
	elif action.kind == 'release':
		manipulation.release(actor, target)
	elif action.kind == 'place':
		manipulation.place(actor, target, action.destination)
	elif action.kind in ('push', 'strike'):
		manipulation.push(
			actor, target, action.direction, strike=action.kind == 'strike', contact_point=action.contact_point
		)
	elif action.kind == 'shape':
		part = manipulation.shape(actor, target, action)
		events.append(
			SimulationEvent(
				kind='part.shaped',
				tick=state.tick,
				actor_id=actor.id,
				subject_id=part.id,
				data={'source_id': action.target_id, 'part': part.model_dump(mode='json')},
			)
		)
	elif action.kind == 'gather':
		infinite = target.resource is not None and target.resource.supply == 'infinite' and target.material == 'stone'
		part = manipulation.gather(actor, target, action.amount)
		events.append(
			SimulationEvent(
				kind='resource.gathered',
				tick=state.tick,
				actor_id=actor.id,
				subject_id=part.id,
				data={
					'source_id': action.target_id,
					'mass': part.mass,
					'source_mass_added': part.mass if infinite else 0,
				},
			)
		)
	elif action.kind in ('take_seed', 'plant', 'fell', 'uproot'):
		if action.kind == 'take_seed':
			result = ecology.take_seed(actor, target, action.amount)
		elif action.kind == 'plant':
			result = ecology.plant(actor, target, action.destination)
		elif action.kind == 'fell':
			result = ecology.fell(actor, target)
		else:
			result = ecology.uproot(actor, target)

		kind = {
			'take_seed': 'plant.seed_taken',
			'plant': 'plant.planted',
			'fell': 'tree.felled',
			'uproot': 'plant.uprooted',
		}[action.kind]
		events.append(
			SimulationEvent(
				kind=kind,
				tick=state.tick,
				actor_id=actor.id,
				subject_id=result.id,
				data={'source_id': target.id, 'entity': result.model_dump(mode='json')},
			)
		)
	elif action.kind == 'connect':
		joint = manipulation.connect(actor, target, action)
		events.append(
			SimulationEvent(
				kind='connection.created',
				tick=state.tick,
				actor_id=actor.id,
				subject_id=joint.id,
				data=joint.model_dump(mode='json'),
			)
		)
	elif action.kind == 'detach':
		joint = next((item for item in state.joints if item.id == action.target_id), None)

		if joint is None:
			raise ActionRejected('The connection is not present.')

		reachable(state, actor, joint.entity_a)
		reachable(state, actor, joint.entity_b)
		manipulation.remove_joint(joint)
		events.append(
			SimulationEvent(kind='connection.detached', tick=state.tick, actor_id=actor.id, subject_id=joint.id)
		)
	elif action.kind == 'eat':
		if target.material != 'food' or target.id not in actor.held_ids:
			raise ActionRejected('Hold edible material before eating it.')

		amount = min(action.amount, target.mass)
		target.mass -= amount
		actor.body.food = min(100, actor.body.food + amount * 120)

		if target.mass <= MASS_EPSILON:
			manipulation.release(actor, target)
			manipulation.remove_entity(target)
		else:
			physics.nodes[target.id].node().setMass(target.mass)
	elif action.kind == 'drink':
		entity = state.entity(actor.id)
		ground = surface_height(*entity.position[:2], state.config)

		if ground > state.config.water_level + 1 or entity.position[2] > state.config.water_level + 2:
			raise ActionRejected('Water is not within reach.')

		actor.body.water = min(100, actor.body.water + action.amount * 100)
	elif action.kind == 'care':
		patient = next((other for other in state.inhabitants if other.id == target.id and other.alive), None)

		if patient is None or patient.id == actor.id:
			raise ActionRejected('Choose another living inhabitant.')

		food = next((state.entity(item) for item in actor.held_ids if state.entity(item).material == 'food'), None)

		if food is None:
			raise ActionRejected('Hold food to provide care.')

		amount = min(action.amount, food.mass)
		food.mass -= amount
		patient.body.food = min(100, patient.body.food + amount * 120)
		patient.body.stress = max(0, patient.body.stress - amount * 10)

		if food.mass <= MASS_EPSILON:
			manipulation.release(actor, food)
			manipulation.remove_entity(food)
		else:
			physics.nodes[food.id].node().setMass(food.mass)
	elif action.kind == 'speak':
		position = state.entity(actor.id).position
		recipients = [
			other.id
			for other in state.inhabitants
			if other.alive
			and other.id != actor.id
			and distance(position, state.entity(other.id).position) <= SPEECH_RANGE
		]
		recipients.extend(
			entity.id
			for entity in state.entities
			if entity.kind == 'device' and distance(position, entity.position) <= SPEECH_RANGE
		)
		events.append(
			SimulationEvent(
				kind='message.spoken',
				tick=state.tick,
				actor_id=actor.id,
				data={
					'text': action.text,
					'speaker_name': actor.name,
					'position': position,
					'recipient_ids': recipients,
				},
			)
		)
	elif action.kind == 'write':
		if target.kind != 'part' or target.material not in ('wood', 'stone'):
			raise ActionRejected('Writing requires a manufactured wood or stone surface.')

		events.append(
			SimulationEvent(
				kind='artifact.written',
				tick=state.tick,
				actor_id=actor.id,
				subject_id=action.artifact_id,
				data={
					'title': action.title or 'Untitled',
					'text': action.text,
					'location_id': target.id,
					'position': target.position,
				},
			)
		)
	elif action.kind == 'program':
		if target.kind != 'part' or target.id not in actor.held_ids:
			raise ActionRejected('Hold an unprogrammed manufactured part to use as the device.')

		if actor.body.energy < INITIAL_DEVICE_POWER:
			raise ActionRejected('Insufficient energy to power this device.')

		try:
			SimulationProgramVM({}, {'tick': state.tick, 'inbox': [], 'name': action.title}).run(
				validate_program(action.text)
			)
		except (TypeError, KeyError, RecursionError) as error:
			raise ActionRejected('The program contains an invalid instruction.') from error

		actor.body.energy -= INITIAL_DEVICE_POWER
		target.kind = 'device'
		events.append(
			SimulationEvent(
				kind='program.deployed',
				tick=state.tick,
				actor_id=actor.id,
				subject_id=target.id,
				data={
					'host_id': target.id,
					'title': action.title or 'Device',
					'source': action.text,
					'position': target.position,
				},
			)
		)
	elif action.kind == 'consent':
		if not action.willing:
			actor.reproduction_consent = None

			return [SimulationEvent(kind='inhabitant.consent_revoked', tick=state.tick, actor_id=actor.id)]

		partner = next(
			(
				other
				for other in state.inhabitants
				if other.id == action.target_id and other.alive and other.id != actor.id
			),
			None,
		)

		if partner is None or actor.body.growth < 1 or partner.body.growth < 1:
			raise ActionRejected('Reproduction requires two living mature inhabitants.')

		if min(actor.body.food, actor.body.water, actor.body.energy) < REPRODUCTION_CONDITION:
			raise ActionRejected('This inhabitant is not in sufficient condition to reproduce.')

		reachable(state, actor, partner.id)

		if (
			partner.reproduction_consent == actor.id
			and partner.pregnancy_partner is None
			and actor.pregnancy_partner is None
		):
			if min(partner.body.food, partner.body.water, partner.body.energy) < REPRODUCTION_CONDITION:
				raise ActionRejected('The partner is not in sufficient condition to reproduce.')

			actor.pregnancy_partner = partner.id
			actor.pregnancy_progress = 0
			actor.reproduction_consent = None
			partner.reproduction_consent = None
			actor.body.energy -= 20
			partner.body.energy -= 20
			events.append(
				SimulationEvent(kind='inhabitant.conceived', tick=state.tick, actor_id=actor.id, subject_id=partner.id)
			)
		else:
			actor.reproduction_consent = partner.id
			events.append(
				SimulationEvent(
					kind='inhabitant.consent_given', tick=state.tick, actor_id=actor.id, subject_id=partner.id
				)
			)

	if action.kind not in ('rest', 'wait', 'walk'):
		actor.body.energy = max(0, actor.body.energy - 0.1 * math.sqrt(action.amount))

	return events

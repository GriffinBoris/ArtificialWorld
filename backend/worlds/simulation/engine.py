from panda3d.core import Vec3
from worlds.simulation.actions import ActionRejected
from worlds.simulation.biology import update_body
from worlds.simulation.contracts import SimulationEvent
from worlds.simulation.ecology import Ecology
from worlds.simulation.interactions import complete_activity
from worlds.simulation.lifecycle import progress_pregnancy
from worlds.simulation.locomotion import Locomotion
from worlds.simulation.manipulation import Manipulation
from worlds.simulation.physics import PhysicsWorld


class Simulation:
	def __init__(self, state):
		self.state = state
		self.physics = PhysicsWorld(state)
		self.events = []
		self.ecology = Ecology(state, self.physics, Manipulation(state, self.physics))
		self.locomotion = Locomotion(state, self.physics)

	def advance(self, seconds, stop_at_decision=True):
		frames = []
		steps = round(seconds * self.state.config.physics_hz)
		dt = 1 / self.state.config.physics_hz
		grown = {}

		for _ in range(steps):
			self.state.tick += 1
			self._activities()

			if self.state.tick % self.state.config.physics_hz == 0:
				for identity, amount in self.ecology.grow().items():
					grown[identity] = grown.get(identity, 0) + amount

				self.events.extend(self.ecology.reseed())

			self.events.extend(self.physics.step())
			self.physics.synchronize()

			for inhabitant in list(self.state.inhabitants):
				entity = self.state.entity(inhabitant.id)
				previous_growth = inhabitant.body.growth
				self.events.extend(update_body(inhabitant, entity, self.state.config, dt, self.state.tick))
				self.events.extend(progress_pregnancy(self.state, inhabitant, dt, self.physics))

				if int(inhabitant.body.growth * 100) > int(previous_growth * 100):
					growth = inhabitant.body.growth
					entity.dimensions = (0.25 + 0.25 * growth, 0.25 + 0.25 * growth, 0.6 + 1.1 * growth)
					entity.mass = 4 + 66 * growth

					for joint in list(self.state.joints):
						if inhabitant.id in (joint.entity_a, joint.entity_b):
							Manipulation(self.state, self.physics).remove_joint(joint)

					inhabitant.held_ids.clear()
					self.physics.replace_entity(entity)

				if not inhabitant.alive:
					for joint in list(self.state.joints):
						if inhabitant.id in (joint.entity_a, joint.entity_b):
							Manipulation(self.state, self.physics).remove_joint(joint)

					self.physics.nodes[entity.id].node().setAngularFactor(Vec3(1))

			if self.state.tick % (self.state.config.physics_hz // self.state.config.recording_hz) == 0:
				frames.append({'tick': self.state.tick, 'state': self.state.model_dump(mode='json')})

			if stop_at_decision and any(
				agent.alive
				and agent.driver != 'scripted'
				and agent.activity is None
				and agent.wake_tick <= self.state.tick
				for agent in self.state.inhabitants
			):
				if not frames or frames[-1]['tick'] != self.state.tick:
					frames.append({'tick': self.state.tick, 'state': self.state.model_dump(mode='json')})

				break

		self.events.extend(
			SimulationEvent(
				kind='resource.grown',
				tick=self.state.tick,
				subject_id=identity,
				data={'mass_added': amount, 'source': 'sunlight_water_soil'},
			)
			for identity, amount in grown.items()
		)

		return frames

	def _activities(self):
		inhabitants = self.state.inhabitants
		offset = self.state.action_rotation % max(1, len(inhabitants))
		completed = False

		for inhabitant in inhabitants[offset:] + inhabitants[:offset]:
			activity = inhabitant.activity

			if not inhabitant.alive or activity is None:
				continue

			try:
				if activity.kind == 'walk':
					if not self.locomotion.step(inhabitant):
						continue
				elif self.state.tick < activity.ends_tick:
					continue

				if activity.kind not in ('walk', 'wait', 'rest'):
					self.events.extend(complete_activity(self.state, self.physics, inhabitant))

				result = {
					'kind': activity.kind,
					'status': 'arrived' if activity.kind == 'walk' else 'completed',
					'position': self.state.entity(inhabitant.id).position,
					'elapsed_seconds': (self.state.tick - activity.started_tick) / self.state.config.physics_hz,
				}

				if activity.kind == 'walk':
					result['destination'] = activity.parameters['destination']

				self.events.append(
					SimulationEvent(
						kind='activity.completed',
						tick=self.state.tick,
						actor_id=inhabitant.id,
						subject_id=activity.id,
						data=result,
					)
				)
			except (ActionRejected, ValueError) as error:
				result = {
					'kind': activity.kind,
					'status': 'failed',
					'reason': str(error),
					'position': self.state.entity(inhabitant.id).position,
				}
				self.events.append(
					SimulationEvent(
						kind='activity.failed',
						tick=self.state.tick,
						actor_id=inhabitant.id,
						subject_id=activity.id,
						data=result,
					)
				)

			inhabitant.last_action_result = {'activity_id': activity.id, 'tick': self.state.tick, **result}
			inhabitant.activity = None
			inhabitant.wake_tick = self.state.tick
			completed = True

		if completed:
			self.state.action_rotation += 1

	def close(self):
		self.physics.close()

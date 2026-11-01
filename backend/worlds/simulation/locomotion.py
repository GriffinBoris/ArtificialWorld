import math

from panda3d.core import Vec3
from worlds.simulation.actions import ActionRejected
from worlds.simulation.contracts import WalkNavigation
from worlds.simulation.pathfinding import PathNotFound, RoutePlanner
from worlds.simulation.terrain import surface_height

ARRIVAL_DISTANCE = 0.5
WAYPOINT_DISTANCE = 0.2
PROGRESS_DISTANCE = 0.2
STUCK_SECONDS = 4
MAX_REPLANS = 3


class Locomotion:
	def __init__(self, state, physics):
		self.state = state
		self.physics = physics

	def plan(self, actor):
		activity = actor.activity

		try:
			waypoints = RoutePlanner(self.state, actor.id).route(activity.parameters['destination'])
		except PathNotFound as error:
			raise ActionRejected(str(error)) from error

		position = self.state.entity(actor.id).position
		replans = activity.navigation.replans + 1 if activity.navigation else 0
		activity.navigation = WalkNavigation(
			waypoints=waypoints, progress_position=position, progress_tick=self.state.tick, replans=replans
		)
		length = sum(math.dist(a[:2], b[:2]) for a, b in zip([position, *waypoints[:-1]], waypoints, strict=True))
		speed = 1.4 * max(0.2, min(1, actor.body.energy / 30)) * max(0.2, actor.body.growth)
		activity.ends_tick = self.state.tick + math.ceil((length / speed * 2 + 10) * self.state.config.physics_hz)

	def step(self, actor):
		activity = actor.activity
		entity = self.state.entity(actor.id)
		node = self.physics.nodes[actor.id]

		if activity.navigation is None:
			self.plan(actor)

		navigation = activity.navigation

		if math.dist(entity.position[:2], navigation.waypoints[-1][:2]) < ARRIVAL_DISTANCE:
			velocity = node.node().getLinearVelocity()
			node.node().setLinearVelocity(Vec3(0, 0, velocity.z))

			return True

		if self.state.tick >= activity.ends_tick:
			raise ActionRejected('The journey timed out before reaching the destination.')

		if math.dist(entity.position[:2], navigation.progress_position[:2]) >= PROGRESS_DISTANCE:
			navigation.progress_position = entity.position
			navigation.progress_tick = self.state.tick
		elif self.state.tick - navigation.progress_tick >= STUCK_SECONDS * self.state.config.physics_hz:
			if navigation.replans >= MAX_REPLANS:
				raise ActionRejected('Movement remained blocked after replanning the route.')

			self.plan(actor)
			navigation = activity.navigation

		while (
			navigation.waypoint_index < len(navigation.waypoints) - 1
			and math.dist(entity.position[:2], navigation.waypoints[navigation.waypoint_index][:2]) < WAYPOINT_DISTANCE
		):
			navigation.waypoint_index += 1

		x, y = navigation.waypoints[navigation.waypoint_index][:2]
		delta = Vec3(x - node.getX(), y - node.getY(), 0)
		delta.normalize()
		stamina = max(0.2, min(1, actor.body.energy / 30))
		speed = 1.4 * stamina * max(0.2, actor.body.growth)
		velocity = node.node().getLinearVelocity()
		force = (delta * speed - Vec3(velocity.x, velocity.y, 0)) * entity.mass * 6
		limit = 350 * actor.body.strength_trait * max(0.1, actor.body.growth)

		if force.length() > limit:
			force.normalize()
			force *= limit

		ground = surface_height(node.getX(), node.getY(), self.state.config)

		if node.getZ() - entity.dimensions[2] / 2 < ground + 0.4:
			node.node().setActive(True)
			node.node().applyCentralForce(force)

		return False

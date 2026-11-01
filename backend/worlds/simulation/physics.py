import math

from panda3d.bullet import (
	BulletBoxShape,
	BulletCapsuleShape,
	BulletCylinderShape,
	BulletGenericConstraint,
	BulletHingeConstraint,
	BulletPlaneShape,
	BulletRigidBodyNode,
	BulletSphereShape,
	BulletTriangleMesh,
	BulletTriangleMeshShape,
	BulletWorld,
	ZUp,
)
from panda3d.core import NodePath, PandaNode, Point3, Quat, TransformState, Vec3
from worlds.simulation.contracts import MATERIALS, SimulationEvent
from worlds.simulation.terrain import terrain_grid

REFERENCE_FRAME_A = True
DISABLE_LINKED_COLLISIONS = True
MAX_ENVIRONMENTAL_FORCE = 100000


class PhysicsWorld:
	def __init__(self, state):
		self.state = state
		self.world = BulletWorld()
		self.world.setGravity(Vec3(0, 0, -state.config.gravity))
		self.root = NodePath(PandaNode('world'))
		self.nodes = {}
		self.constraints = {}
		self._add_terrain()

		for entity in state.entities:
			self.add_entity(entity)

		for joint in state.joints:
			self.add_joint(joint)

	def _add_terrain(self):
		config = self.state.config
		grid = terrain_grid(config)
		resolution = len(grid) - 1
		spacing = config.size / resolution
		mesh = BulletTriangleMesh()

		for y in range(resolution):
			for x in range(resolution):
				points = [
					Point3(-config.size / 2 + xx * spacing, -config.size / 2 + yy * spacing, grid[yy][xx])
					for xx, yy in [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
				]
				mesh.addTriangle(points[0], points[1], points[2])
				mesh.addTriangle(points[1], points[3], points[2])

		ground = BulletRigidBodyNode('terrain')
		ground.addShape(BulletTriangleMeshShape(mesh, dynamic=False))
		self.root.attachNewNode(ground)
		self.world.attachRigidBody(ground)
		half = config.size / 2

		for normal, constant in [
			(Vec3(1, 0, 0), -half),
			(Vec3(-1, 0, 0), -half),
			(Vec3(0, 1, 0), -half),
			(Vec3(0, -1, 0), -half),
			(Vec3(0, 0, -1), -config.ceiling),
		]:
			wall = BulletRigidBodyNode('boundary')
			wall.addShape(BulletPlaneShape(normal, constant))
			self.root.attachNewNode(wall)
			self.world.attachRigidBody(wall)

	def add_entity(self, entity):
		x, y, z = entity.dimensions

		if entity.shape == 'sphere':
			shape = BulletSphereShape(x / 2)
		elif entity.shape == 'cylinder':
			shape = BulletCylinderShape(x / 2, z, ZUp)
		elif entity.shape == 'capsule':
			shape = BulletCapsuleShape(x / 2, max(0.01, z - x), ZUp)
		else:
			shape = BulletBoxShape(Vec3(x / 2, y / 2, z / 2))

		body = BulletRigidBodyNode(entity.id)
		body.addShape(shape)
		body.setMass(0 if entity.fixed else entity.mass)
		body.setFriction(MATERIALS[entity.material].friction)
		body.setRestitution(0.05)

		if not entity.fixed:
			body.setCcdMotionThreshold(min(entity.dimensions) / 4)
			body.setCcdSweptSphereRadius(min(entity.dimensions) * 0.4)

		if entity.kind == 'inhabitant':
			body.setAngularFactor(Vec3(0))

		node = self.root.attachNewNode(body)
		node.setPos(*entity.position)
		node.setQuat(Quat(*entity.rotation))
		body.setLinearVelocity(Vec3(*entity.velocity))
		body.setAngularVelocity(Vec3(*entity.angular_velocity))
		self.world.attachRigidBody(body)
		self.nodes[entity.id] = node

	def add_joint(self, joint):
		a, b = self.nodes[joint.entity_a], self.nodes[joint.entity_b]

		if joint.kind == 'hinge':
			constraint = BulletHingeConstraint(
				a.node(),
				b.node(),
				Point3(*joint.anchor_a),
				Point3(*joint.anchor_b),
				Vec3(*joint.axis),
				Vec3(*joint.axis_b),
				REFERENCE_FRAME_A,
			)
		else:
			constraint = BulletGenericConstraint(
				a.node(),
				b.node(),
				TransformState.makePosQuatScale(Point3(*joint.anchor_a), Quat(*joint.rotation_a), Vec3(1)),
				TransformState.makePosQuatScale(Point3(*joint.anchor_b), Quat(*joint.rotation_b), Vec3(1)),
				REFERENCE_FRAME_A,
			)

			for axis in range(3):
				constraint.setLinearLimit(axis, 0, 0)
				constraint.setAngularLimit(axis, 0, 0)

		constraint.setBreakingThreshold(joint.strength / self.state.config.physics_hz)
		self.world.attachConstraint(constraint, DISABLE_LINKED_COLLISIONS)
		self.constraints[joint.id] = constraint

	def replace_entity(self, entity):
		old = self.nodes.pop(entity.id)
		self.world.removeRigidBody(old.node())
		old.removeNode()
		self.add_entity(entity)

	def environmental_force(self, entity):
		node = self.nodes[entity.id]
		velocity = node.node().getLinearVelocity()
		relative = Vec3(*self.state.config.wind) - velocity
		speed = relative.length()
		x, y, z = entity.dimensions
		area = max(x * y, x * z, y * z)
		force = relative * (0.03 * speed * area)

		if entity.kind in ('part', 'device') and z < min(x, y) * 0.2 and speed > 0:
			normal = node.getQuat().xform(Vec3(0, 0, 1))
			incidence = normal.dot(relative / speed)
			force += normal * (1.225 * speed**2 * x * y * incidence * abs(incidence))

		bottom = node.getZ() - z / 2
		submerged = max(0, min(1, (self.state.config.water_level - bottom) / z))

		if submerged:
			force += Vec3(0, 0, 1000 * entity.volume * self.state.config.gravity * submerged)
			force -= velocity * (20 * area * submerged)

		if force.length() > MAX_ENVIRONMENTAL_FORCE:
			force.normalize()
			force *= MAX_ENVIRONMENTAL_FORCE

		return force

	def step(self):
		for entity in self.state.entities:
			if not entity.fixed:
				self.nodes[entity.id].node().applyCentralForce(self.environmental_force(entity))

		self.world.doPhysics(1 / self.state.config.physics_hz, 1, 1 / self.state.config.physics_hz)
		events = self._collision_damage()

		for joint in list(self.state.joints):
			constraint = self.constraints[joint.id]

			if not constraint.isEnabled():
				self.world.removeConstraint(constraint)
				self.state.joints.remove(joint)

				for inhabitant in self.state.inhabitants:
					if joint.entity_a == inhabitant.id and joint.entity_b in inhabitant.held_ids:
						inhabitant.held_ids.remove(joint.entity_b)

				del self.constraints[joint.id]
				events.append(
					SimulationEvent(
						kind='connection.broken', tick=self.state.tick, actor_id=joint.creator_id, subject_id=joint.id
					)
				)

		return events

	def _collision_damage(self):
		events = []
		entities = {entity.id: entity for entity in self.state.entities}

		for manifold in self.world.getManifolds():
			a, b = manifold.getNode0().getName(), manifold.getNode1().getName()
			impulse = sum(max(0, point.getAppliedImpulse()) for point in manifold.getManifoldPoints())

			for entity_id, other in ((a, b), (b, a)):
				entity = entities.get(entity_id)

				if entity is None or entity.fixed:
					continue

				energy = impulse**2 / (2 * entity.mass)
				threshold = 100 if entity.material == 'body' else MATERIALS[entity.material].strength / 4
				damage = max(0, energy - threshold) / 30

				if damage <= 0:
					continue

				entity.condition = max(0, entity.condition - damage)

				if entity.kind == 'inhabitant':
					actor = self.state.inhabitant(entity.id)
					actor.body.health -= damage
					actor.body.injury = min(100, actor.body.injury + damage)

				events.append(
					SimulationEvent(
						kind='collision.damage',
						tick=self.state.tick,
						subject_id=entity.id,
						data={'other_id': other, 'impulse': impulse, 'damage': damage},
					)
				)

		return events

	def synchronize(self):
		for entity in self.state.entities:
			node = self.nodes[entity.id]
			entity.position = tuple(node.getPos())
			quat = node.getQuat()
			entity.rotation = (quat.getR(), quat.getI(), quat.getJ(), quat.getK())
			entity.velocity = tuple(node.node().getLinearVelocity())
			entity.angular_velocity = tuple(node.node().getAngularVelocity())

			if not all(math.isfinite(value) for value in (*entity.position, *entity.velocity)):
				raise ValueError('Physics produced a non-finite state; the step was not committed.')

	def close(self):
		for constraint in self.constraints.values():
			self.world.removeConstraint(constraint)

		for node in self.nodes.values():
			self.world.removeRigidBody(node.node())

		self.root.removeNode()

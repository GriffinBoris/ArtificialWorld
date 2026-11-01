from panda3d.core import Point3, Vec3
from worlds.simulation.actions import ActionRejected, distance, REACH, reachable
from worlds.simulation.contracts import EntityState, JointState, MATERIALS
from worlds.simulation.ecology import resize_resource
from worlds.simulation.rules import FIBER_PER_CONNECTION, HAND_COUNT, MASS_EPSILON


class Manipulation:
	def __init__(self, state, physics):
		self.state = state
		self.physics = physics

	def remove_entity(self, entity):
		for joint in list(self.state.joints):
			if entity.id in (joint.entity_a, joint.entity_b):
				self.remove_joint(joint)

		node = self.physics.nodes.pop(entity.id)
		self.physics.world.removeRigidBody(node.node())
		node.removeNode()
		self.state.entities.remove(entity)

		for actor in self.state.inhabitants:
			if entity.id in actor.held_ids:
				actor.held_ids.remove(entity.id)

	def remove_joint(self, joint):
		constraint = self.physics.constraints.pop(joint.id)
		self.physics.world.removeConstraint(constraint)
		self.state.joints.remove(joint)

	def grasp(self, actor, target):
		if target.fixed or target.kind in ('inhabitant', 'corpse'):
			raise ActionRejected('This object cannot be grasped.')

		if target.id in actor.held_ids or any(target.id in other.held_ids for other in self.state.inhabitants):
			raise ActionRejected('This object is already held.')

		if len(actor.held_ids) >= HAND_COUNT:
			raise ActionRejected('Both hands are occupied.')

		limit = 25 * actor.body.strength_trait * max(0.1, actor.body.growth)

		if sum(self.state.entity(item).mass for item in actor.held_ids) + target.mass > limit:
			raise ActionRejected('The object is too heavy to carry.')

		body_node, part_node = self.physics.nodes[actor.id], self.physics.nodes[target.id]
		point = Point3(part_node.getPos())
		joint = JointState(
			entity_a=actor.id,
			entity_b=target.id,
			anchor_a=tuple(body_node.getRelativePoint(self.physics.root, point)),
			anchor_b=(0, 0, 0),
			strength=limit * self.state.config.gravity * 2,
			creator_id=actor.id,
		)
		joint.rotation_a = tuple(body_node.getQuat().conjugate())
		joint.rotation_b = tuple(part_node.getQuat().conjugate())
		self.state.joints.append(joint)
		self.physics.add_joint(joint)
		actor.held_ids.append(target.id)

	def release(self, actor, target):
		if target.id not in actor.held_ids:
			raise ActionRejected('This object is not held.')

		for joint in list(self.state.joints):
			if joint.entity_a == actor.id and joint.entity_b == target.id:
				self.remove_joint(joint)

		actor.held_ids.remove(target.id)

	def place(self, actor, target, destination):
		if target.id not in actor.held_ids:
			raise ActionRejected('Grasp the object before placing it.')

		if distance(self.state.entity(actor.id).position, destination) > REACH:
			raise ActionRejected('The placement location is out of reach.')

		direction = Vec3(*destination) - self.physics.nodes[target.id].getPos()

		if direction.length() > 1:
			direction.normalize()

		self.release(actor, target)
		self.physics.nodes[target.id].node().applyCentralImpulse(direction * target.mass)

	def gather(self, actor, target, amount):
		if (
			target.kind != 'resource' and not (target.kind == 'part' and target.resource is not None)
		) or target.material == 'body':
			raise ActionRejected('This is not a material deposit.')

		if any(target.id in (joint.entity_a, joint.entity_b) for joint in self.state.joints):
			raise ActionRejected('Put the source down and detach it before gathering.')

		infinite = target.material == 'stone' and target.resource is not None and target.resource.supply == 'infinite'
		reserved = (
			target.resource.root_mass
			if target.resource and target.resource.growth_seconds and target.resource.supply != 'finite'
			else 0
		)

		if not infinite and target.mass - reserved < amount - MASS_EPSILON:
			raise ActionRejected('The deposit does not contain that quantity.')

		if len(actor.held_ids) >= HAND_COUNT:
			raise ActionRejected('A free hand is needed.')

		if amount > 25 * actor.body.strength_trait * max(0.1, actor.body.growth):
			raise ActionRejected('That quantity is too heavy.')

		length = (amount / MATERIALS[target.material].density) ** (1 / 3)
		position = self.state.entity(actor.id).position
		part = EntityState(
			name=f'{target.material.title()} piece',
			material=target.material,
			dimensions=(length, length, length),
			mass=amount,
			position=(position[0] + 0.6, position[1], position[2] + 0.1),
			creator_id=actor.id,
		)
		self.state.entities.append(part)
		self.physics.add_entity(part)

		try:
			self.grasp(actor, part)
		except ActionRejected:
			self.remove_entity(part)
			raise

		if not infinite:
			capacity, dimensions = (
				(target.resource.capacity, target.resource.mature_dimensions)
				if target.resource
				else (target.mass, target.dimensions)
			)
			target.mass -= amount

			if target.mass <= MASS_EPSILON:
				self.remove_entity(target)
			else:
				if target.resource:
					target.resource.last_growth_tick = self.state.tick

				resize_resource(target, capacity, dimensions)
				self.physics.replace_entity(target)

		return part

	def shape(self, actor, target, action):
		if target.id not in actor.held_ids or target.kind not in ('part', 'seed'):
			raise ActionRejected('Hold a loose material part before shaping it.')

		if any(
			target.id in (joint.entity_a, joint.entity_b) and actor.id not in (joint.entity_a, joint.entity_b)
			for joint in self.state.joints
		):
			raise ActionRejected('Detach the part from its assembly before shaping it.')

		part = EntityState(
			name=f'Shaped {target.material}',
			material=target.material,
			dimensions=action.dimensions,
			shape=action.shape,
			position=target.position,
			creator_id=actor.id,
		)
		part.mass = part.volume * MATERIALS[part.material].density

		if part.mass > target.mass + 1e-8:
			raise ActionRejected('There is not enough material for these dimensions.')

		carried = sum(self.state.entity(item).mass for item in actor.held_ids if item != target.id)

		if carried + part.mass > 25 * actor.body.strength_trait * max(0.1, actor.body.growth):
			raise ActionRejected('The shaped object would exceed current carrying ability.')

		remaining = target.mass - part.mass
		self.release(actor, target)

		if remaining > MASS_EPSILON:
			length = (remaining / MATERIALS[target.material].density) ** (1 / 3)

			target.mass = remaining
			target.kind = 'part'
			target.resource = None
			target.dimensions = (max(0.01, length),) * 3
			self.physics.replace_entity(target)
		else:
			self.remove_entity(target)

		self.state.entities.append(part)
		self.physics.add_entity(part)
		self.grasp(actor, part)

		return part

	def connect(self, actor, a, action):
		b = reachable(self.state, actor, action.other_id)

		if (
			a.id == b.id
			or a.kind in ('inhabitant', 'corpse', 'resource')
			or b.kind in ('inhabitant', 'corpse', 'resource')
		):
			raise ActionRejected('Choose two separate manufactured parts.')

		if distance(a.position, b.position) > (max(a.dimensions) + max(b.dimensions)) / 2 + 0.2:
			raise ActionRejected('Bring the parts together before connecting them.')

		binding = next(
			(
				self.state.entity(item)
				for item in actor.held_ids
				if self.state.entity(item).material == 'fiber' and self.state.entity(item).mass >= FIBER_PER_CONNECTION
			),
			None,
		)

		if binding is None:
			raise ActionRejected('Hold at least 0.01 kg of fiber to make a connection.')

		point = Point3(*[(first + second) / 2 for first, second in zip(a.position, b.position, strict=True)])
		joint = JointState(
			entity_a=a.id,
			entity_b=b.id,
			kind=action.connection,
			anchor_a=tuple(self.physics.nodes[a.id].getRelativePoint(self.physics.root, point)),
			anchor_b=tuple(self.physics.nodes[b.id].getRelativePoint(self.physics.root, point)),
			creator_id=actor.id,
		)
		joint.rotation_a = tuple(self.physics.nodes[a.id].getQuat().conjugate())
		joint.rotation_b = tuple(self.physics.nodes[b.id].getQuat().conjugate())
		joint.axis = tuple(self.physics.nodes[a.id].getRelativeVector(self.physics.root, Vec3(0, 1, 0)))
		joint.axis_b = tuple(self.physics.nodes[b.id].getRelativeVector(self.physics.root, Vec3(0, 1, 0)))
		self.state.joints.append(joint)
		self.physics.add_joint(joint)

		binding.mass -= FIBER_PER_CONNECTION
		a.mass += FIBER_PER_CONNECTION
		self.physics.nodes[a.id].node().setMass(a.mass)

		if binding.mass <= MASS_EPSILON:
			self.release(actor, binding)
			self.remove_entity(binding)
		else:
			self.physics.nodes[binding.id].node().setMass(binding.mass)

		return joint

	def push(self, actor, target, direction, strike=False, contact_point=None):
		if target.fixed:
			raise ActionRejected('This object is anchored.')

		vector = Vec3(*direction)

		if vector.length() <= 0:
			raise ActionRejected('Choose a nonzero direction.')

		vector.normalize()
		impulse = min(80, 15 * actor.body.strength_trait * max(0.1, actor.body.growth))
		node = self.physics.nodes[target.id]

		if contact_point is not None:
			if distance(self.state.entity(actor.id).position, contact_point) > REACH:
				raise ActionRejected('The contact point is out of reach.')

			local = node.getRelativePoint(self.physics.root, Point3(*contact_point))

			if any(abs(value) > size / 2 + 0.1 for value, size in zip(local, target.dimensions, strict=True)):
				raise ActionRejected('The contact point must lie on the object.')

			node.node().applyImpulse(vector * impulse, Point3(*contact_point) - node.getPos())
		else:
			node.node().applyCentralImpulse(vector * impulse)

		if strike:
			damage = max(0, impulse**2 / (2 * target.mass) - 10) / 50
			target.condition = max(0, target.condition - damage)
			victim = next((inhabitant for inhabitant in self.state.inhabitants if inhabitant.id == target.id), None)

			if victim:
				victim.body.health -= damage
				victim.body.injury = min(100, victim.body.injury + damage)

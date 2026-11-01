from worlds.simulation.actions import ActionRejected
from worlds.simulation.contracts import SimulationEvent


def choose_name(state, actor, action):
	if action.kind == 'name_self':
		target = actor
	else:
		target = next((child for child in state.inhabitants if child.id == action.target_id), None)

		if target is None or actor.id not in target.parents:
			raise ActionRejected('You can give a parent-chosen name only to your own child.')

	if not target.alive:
		raise ActionRejected('This inhabitant is no longer alive.')

	previous = target.name
	target.name = state.entity(target.id).name = action.text.strip()

	if target.id == actor.id:
		target.self_named = True
	else:
		target.parent_named = True

	return SimulationEvent(
		kind='inhabitant.named',
		tick=state.tick,
		actor_id=actor.id,
		subject_id=target.id,
		data={'previous_name': previous, 'name': target.name, 'self_chosen': target.id == actor.id},
	)

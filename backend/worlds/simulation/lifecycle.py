import random

from worlds.simulation.contracts import BodyState, EntityState, InhabitantState, SimulationEvent


def progress_pregnancy(state, actor, dt, physics):
	if not actor.alive or actor.pregnancy_partner is None:
		return []

	adequacy = min(actor.body.food, actor.body.water, actor.body.energy) / 100
	actor.pregnancy_progress += dt * adequacy * actor.body.repair_trait / (state.config.gestation_hours * 3600)

	if actor.pregnancy_progress < 1:
		return []

	partner = state.inhabitant(actor.pregnancy_partner)
	rng = random.Random(f'{state.config.seed}:{actor.id}:{partner.id}:{state.tick}')
	origin = state.entity(actor.id)
	entity = EntityState(
		name=f'Child {len(state.inhabitants) + 1}',
		kind='inhabitant',
		material='body',
		shape='capsule',
		dimensions=(0.25, 0.25, 0.6),
		mass=4,
		position=(origin.position[0] + 0.5, origin.position[1], origin.position[2]),
		creator_id=actor.id,
	)
	body = BodyState(
		growth=0.05,
		repair_trait=max(
			0.5, min(2, (actor.body.repair_trait + partner.body.repair_trait) / 2 * rng.uniform(0.95, 1.05))
		),
		metabolism_trait=max(
			0.5, min(2, (actor.body.metabolism_trait + partner.body.metabolism_trait) / 2 * rng.uniform(0.95, 1.05))
		),
		strength_trait=max(
			0.5, min(2, (actor.body.strength_trait + partner.body.strength_trait) / 2 * rng.uniform(0.95, 1.05))
		),
	)
	child = InhabitantState(
		id=entity.id,
		name=entity.name,
		body=body,
		parents=[actor.id, partner.id],
		driver=actor.driver,
		model_name=actor.model_name,
	)
	state.entities.append(entity)
	state.inhabitants.append(child)
	physics.add_entity(entity)
	actor.pregnancy_partner = None
	actor.pregnancy_progress = 0
	actor.last_birth_age = actor.body.age_seconds

	return [
		SimulationEvent(
			kind='inhabitant.born',
			tick=state.tick,
			actor_id=actor.id,
			subject_id=child.id,
			data={
				'parents': child.parents,
				'entity': entity.model_dump(mode='json'),
				'inhabitant': child.model_dump(mode='json'),
			},
		)
	]

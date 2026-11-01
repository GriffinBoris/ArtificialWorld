import math

from worlds.simulation.contracts import SimulationEvent

HEALING_ADEQUACY_THRESHOLD = 0.2


def update_body(inhabitant, entity, config, dt, tick):
	if not inhabitant.alive:
		return []

	body = inhabitant.body
	body.age_seconds += dt
	metabolism = body.metabolism_trait
	active = inhabitant.activity is not None and inhabitant.activity.kind not in ('rest', 'wait')
	body.food = max(0, body.food - 100 * metabolism * dt / (config.food_hours * 3600))
	body.water = max(0, body.water - 100 * metabolism * dt / (config.water_hours * 3600))

	if inhabitant.activity and inhabitant.activity.kind == 'rest':
		body.energy = min(100, body.energy + 100 * dt / (8 * 3600))
	else:
		body.energy = max(0, body.energy - (1.5 if active else 1) * 100 * dt / (config.energy_hours * 3600))

	adequacy = min(body.food, body.water, body.energy) / 100
	body.stress = max(0, min(100, body.stress + dt * ((1 - adequacy) * 0.002 - adequacy * 0.001)))

	strain = (1 + body.stress / 50 + body.injury / 25) * dt / (365 * 24 * 3600)
	repair = adequacy * body.repair_trait * dt / (300 * 24 * 3600)
	body.wear = max(0, body.wear + strain - repair)
	body.injury = max(0, body.injury - adequacy * body.repair_trait * dt / 3600)

	if body.food == 0:
		body.health -= dt / 600

	if body.water == 0:
		body.health -= dt / 60

	body.health -= max(0, body.wear - 100) * dt / 3600

	if entity.position[2] + entity.dimensions[2] * 0.35 < config.water_level:
		body.air = max(0, body.air - dt)

		if body.air == 0:
			body.health -= 20 * dt
	else:
		body.air = min(120, body.air + 10 * dt)

	if adequacy > HEALING_ADEQUACY_THRESHOLD:
		body.health = min(100, body.health + adequacy * body.repair_trait * dt / 3600)

	if body.growth < 1:
		body.growth = min(1, body.growth + adequacy * dt / (config.maturation_hours * 3600))

	if not math.isfinite(body.health):
		raise ValueError('Invalid biological state.')

	if body.health > 0:
		return []

	body.health = 0
	inhabitant.alive = False
	inhabitant.activity = None
	inhabitant.held_ids.clear()
	entity.kind = 'corpse'

	return [
		SimulationEvent(
			kind='inhabitant.died',
			tick=tick,
			actor_id=inhabitant.id,
			data={'age_seconds': body.age_seconds, 'body': body.model_dump()},
		)
	]

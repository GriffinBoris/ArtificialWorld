from worlds.simulation.biology import update_body
from worlds.simulation.contracts import BodyState, EntityState, InhabitantState, WorldConfig


def test_age_does_not_schedule_death():
	entity = EntityState(name='Old inhabitant', kind='inhabitant', position=(0, 0, 10))
	inhabitant = InhabitantState(id=entity.id, name=entity.name, body=BodyState(age_seconds=1000 * 365 * 86400))
	update_body(inhabitant, entity, WorldConfig(), 1, 60)
	assert inhabitant.alive
	assert inhabitant.body.health > 99


def test_nourishment_and_repair_trait_can_reduce_wear():
	entity = EntityState(name='Healthy inhabitant', position=(0, 0, 10))
	inhabitant = InhabitantState(id=entity.id, name=entity.name, body=BodyState(wear=1, repair_trait=1.5))
	update_body(inhabitant, entity, WorldConfig(), 60, 3600)
	assert inhabitant.body.wear < 1


def test_death_releases_activity_and_possessions():
	entity = EntityState(name='Inhabitant', position=(110, 80, -5))
	inhabitant = InhabitantState(id=entity.id, name=entity.name, body=BodyState(health=1, air=0), held_ids=['a-part'])
	events = update_body(inhabitant, entity, WorldConfig(), 1, 60)
	assert not inhabitant.alive
	assert inhabitant.body.health == 0
	assert inhabitant.held_ids == []
	assert entity.kind == 'corpse'
	assert events[0].kind == 'inhabitant.died'

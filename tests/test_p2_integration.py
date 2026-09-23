from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application.p2 import (
    CHARNECA,
    CHARNECA_CONNECTION,
    CHARNECA_LOCATION_ID,
    MARCAS_CODEX,
    P2_CONTENT_ID,
    P2_REWARD_SOURCE,
    REFUGE,
    P2Service,
)
from asterion.domain.combat import allowed_actions
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Brazier,
    Character,
    CodexEntry,
    CombatRecord,
    Encounter,
    GameActivity,
    HuntContext,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_road_integration import _seed_road


async def _seed_p2(database, actor: int, level: int = 3):
    await _seed_road(database, actor)
    sessions = database[1]
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.level = level
        character.xp = 0
        session.add_all(
            [
                LocationDiscovery(
                    character_id=character.id,
                    location_id="tdo.location.estrada_das_cinzas",
                ),
                LocationDiscovery(
                    character_id=character.id,
                    location_id="tdo.location.refugio_do_ocaso",
                ),
            ]
        )
        await session.commit()
    return P2Service(sessions, "ocaso")


async def _force_combat_hp(database, activity_id, *, player_hp=None, enemy_hp=None):
    async with database[1]() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.id == activity_id)
        )
        encounter, record = (
            await session.execute(
                select(Encounter, CombatRecord)
                .join(CombatRecord)
                .where(Encounter.game_activity_id == activity_id)
            )
        ).one()
        combat = decode(
            record.snapshot,
            record.id,
            activity.ruleset_version,
            activity.state_version,
        )
        if player_hp is not None:
            combat.fighters["player"].hp = Decimal(player_hp)
            character = await session.scalar(
                select(Character).where(Character.id == activity.character_id)
            )
            character.hp = Decimal(player_hp)
        if enemy_hp is not None:
            combat.fighters["enemy"].hp = Decimal(enemy_hp)
        record.snapshot = encode(combat)
        await session.commit()
        return encounter.id


@pytest.mark.asyncio
async def test_p2_is_not_autoaccepted_and_requires_level_three(database):
    actor = 775001
    service = await _seed_p2(database, actor, level=2)

    alda = await service.alda(actor)
    assert alda is not None
    assert alda.status == "unaccepted"
    assert alda.available is False
    assert await service.offer(actor) is None

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.level = 3
        await session.commit()

    alda = await service.alda(actor)
    assert alda.available is True
    offer = await service.offer(actor)
    assert offer.kind == "offer"
    async with database[1]() as session:
        assert await session.scalar(
            select(Quest).where(Quest.quest_id == "P2")
        ) is None


@pytest.mark.asyncio
async def test_p2_accept_unlocks_connection_not_charneca_or_brazier(database):
    actor = 775002
    service = await _seed_p2(database, actor)

    accepted = await service.accept(actor)
    assert accepted.status == "active"
    assert accepted.step == 1
    assert CHARNECA_LOCATION_ID not in accepted.known_locations

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == CHARNECA_CONNECTION,
            )
        )
        assert await session.scalar(
            select(LocationDiscovery).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == CHARNECA_LOCATION_ID,
            )
        ) is None
        assert await session.scalar(
            select(Brazier).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == "tdo.brazier.vento_morto",
            )
        ) is None


@pytest.mark.asyncio
async def test_first_normal_arrival_discovers_charneca_and_advances_step_one(database):
    actor = 775003
    service = await _seed_p2(database, actor)
    await service.accept(actor)

    arrived = await service.travel_normal(actor, CHARNECA)
    assert arrived.kind == "arrival"
    assert arrived.location == CHARNECA
    assert arrived.step == 2
    assert CHARNECA_LOCATION_ID in arrived.known_locations

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await session.scalar(
            select(Brazier).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == "tdo.brazier.vento_morto",
            )
        ) is None

    returned = await service.travel_normal(actor, REFUGE)
    assert returned.location == REFUGE
    again = await service.travel_normal(actor, CHARNECA)
    assert again.kind == "objective"
    assert again.step == 2


@pytest.mark.asyncio
async def test_p2_third_point_materializes_deterministic_arachnid_without_variant(database):
    actor = 775004
    service = await _seed_p2(database, actor)
    await service.accept(actor)
    view = await service.travel_normal(actor, CHARNECA)

    for point in (3, 1, 2):
        view = await service.investigate_point(actor, point, view.state_version)

    assert view.step == 3
    assert view.combat is not None
    assert view.combat.fighters["enemy"].name == "Aranha de Cinza"
    assert view.combat.variant is None

    async with database[1]() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == view.activity_id)
        )
        assert context.creature_id == "aranha_cinza"
        assert context.variant is None
        assert context.local_id == CHARNECA
        assert context.loot_profile == "mission_scripted_p2"
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character.id,
                BestiaryEntry.creature_id == "aranha_cinza",
            )
        )


@pytest.mark.asyncio
async def test_p2_defeat_recovers_at_refuge_and_retry_keeps_species_new_encounter(database):
    actor = 775005
    service = await _seed_p2(database, actor)
    await service.accept(actor)
    view = await service.travel_normal(actor, CHARNECA)
    for point in (1, 2, 3):
        view = await service.investigate_point(actor, point, view.state_version)

    first_encounter = view.encounter_id
    await _force_combat_hp(database, view.activity_id, player_hp="1")
    action = "attack" if "attack" in allowed_actions(view.combat) else allowed_actions(view.combat)[0]
    defeated = await service.action(
        actor,
        view.activity_id,
        view.combat.version,
        action,
    )
    assert defeated.step == 3
    assert defeated.progress["defeat"] is True
    assert defeated.location == REFUGE

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character.hp == character.max_hp
        assert await session.scalar(
            select(Brazier).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == "tdo.brazier.vento_morto",
            )
        ) is None

    retried = await service.travel_normal(actor, CHARNECA)
    assert retried.combat is not None
    assert retried.encounter_id != first_encounter
    assert retried.combat.fighters["enemy"].name == "Aranha de Cinza"
    assert retried.combat.variant is None

    resumed = await service.resume(actor)
    assert resumed.encounter_id == retried.encounter_id


@pytest.mark.asyncio
async def test_p2_victory_pays_enemy_xp_only_then_final_reward_is_exact(database):
    actor = 775006
    service = await _seed_p2(database, actor)
    await service.accept(actor)
    view = await service.travel_normal(actor, CHARNECA)
    for point in (1, 2, 3):
        view = await service.investigate_point(actor, point, view.state_version)

    encounter_id = view.encounter_id
    await _force_combat_hp(database, view.activity_id, enemy_hp="1")
    won = await service.action(
        actor,
        view.activity_id,
        view.combat.version,
        "attack",
    )
    assert won.step == 4

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character.vigor == 100
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == f"p2:encounter:{encounter_id}",
            )
        )
        rows = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == event.id
                )
            )
        ).all()
        kinds = {row.kind for row in rows}
        assert "xp" in kinds
        assert not kinds.intersection({"crowns", "material", "equipment", "rune"})
        assert await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "hunt_round.charneca_da_fuligem",
            )
        ) is None

    stone = await service.examine_stone(actor, won.state_version)
    assert stone.step == 5
    assert await service.travel_normal(actor, REFUGE)
    oren = await service.oren(actor)
    delivered = await service.deliver_record(actor, oren.state_version)
    assert delivered.step == 6
    completed = await service.complete_with_alda(actor, delivered.state_version)
    assert completed.status == "completed"

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        final_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P2_REWARD_SOURCE,
            )
        )
        rows = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == final_event.id
                )
            )
        ).all()
        assert sorted((row.kind, row.item_id, row.quantity) for row in rows) == sorted(
            [
                ("xp", None, 3300),
                ("crowns", None, 140),
                ("material", "material.tdo.ferro_de_fuligem", 1),
                ("material", "material.tdo.erva_cinzenta", 2),
                ("material", "material.tdo.residuo_ocaso", 1),
            ]
        )
        assert await session.scalar(
            select(CodexEntry).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == MARCAS_CODEX,
            )
        )
        assert await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "hunt_manual.charneca_da_fuligem",
            )
        )
        assert await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "explore.charneca_da_fuligem",
            )
        )
        stacks = (
            await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character.id)
            )
        ).all()
        material_totals = {
            stack.material_id: stack.quantity
            for stack in stacks
            if stack.bound
        }
        assert material_totals == {
            "material.tdo.ferro_de_fuligem": 1,
            "material.tdo.erva_cinzenta": 2,
            "material.tdo.residuo_ocaso": 1,
        }

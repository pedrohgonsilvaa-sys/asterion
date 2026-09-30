from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.active_arts import ActiveArtService
from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.application.equipment import EquipmentService
from asterion.application.progression import level_xp
from asterion.application.road import ROAD
from asterion.application.round import (
    HEAL_CONSUMABLE,
    PURIFY_CONSUMABLE,
    RoundService,
)
from asterion.domain.arts import FIRST_CLASS_ART_IDS
from asterion.domain.combat import DotState
from asterion.domain.combat_math import Stats, resolve_combat_stats
from asterion.domain.equipment_stats import equipment_configuration_from_data
from asterion.domain.road import CREATURES, ROUND_FAMILIARITY
from asterion.infrastructure.db.models import (
    Character,
    CombatRecord,
    ConsumableStack,
    EquipmentItem,
    GameActivity,
    HuntRound,
    HuntRoundEncounter,
    RewardEvent,
    Unlock,
)
from tests.test_road_integration import _seed_road


async def _seed_round(database, actor: int, *, vigor: int = 100):
    await _seed_road(database, actor, vigor=vigor)
    sessions = database[1]
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(Unlock(character_id=character.id, unlock_id=ROUND_FAMILIARITY))
        await session.commit()
    service = RoundService(sessions, "ocaso")
    await service.travel(actor, ROAD)
    return actor, service


def _force_safe_common(monkeypatch, round_module):
    """Keep scheduler/economy tests independent from combat-survival variance."""
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level, **kwargs: CREATURES[0])
    original = round_module.create_road_combat

    def safe_combat(*args, **kwargs):
        state = original(*args, **kwargs)
        enemy = state.fighters["enemy"]
        enemy.stats = Stats(
            enemy.stats.hp,
            enemy.stats.attack * 0 + 1,
            enemy.stats.defense,
            enemy.stats.agility,
        )
        return state

    monkeypatch.setattr(round_module, "create_road_combat", safe_combat)


@pytest.mark.asyncio
async def test_round_preparation_consumables_and_reconnect_are_persistent(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772001)
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level, **kwargs: CREATURES[0])

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add_all(
            [
                ConsumableStack(
                    character_id=character.id,
                    consumable_id=HEAL_CONSUMABLE,
                    quantity=4,
                ),
                ConsumableStack(
                    character_id=character.id,
                    consumable_id=PURIFY_CONSUMABLE,
                    quantity=2,
                ),
            ]
        )
        await session.commit()

    prepared = await service.prepare_round(actor, 5)
    assert prepared.kind == "round_prepare"
    consumables = await service.round_consumables(
        actor, prepared.round_id, prepared.state_version
    )
    assert (consumables.heal_quantity, consumables.purify_quantity) == (4, 2)

    toggled = await service.toggle_round_consumable(
        actor,
        prepared.round_id,
        consumables.state_version,
        HEAL_CONSUMABLE,
    )
    assert toggled.prepared_heal is True
    started = await service.start_round(actor, toggled.round_id, toggled.state_version)
    assert started.kind == "round_active"
    assert started.prepared_heal is True
    assert started.completed_encounters == 0
    assert started.next_resolution_at is not None

    resumed = await service.resume(actor)
    assert resumed.kind == "round_active"
    assert resumed.round_id == started.round_id
    assert resumed.encounter_id == started.encounter_id

    stale = await service.start_round(actor, toggled.round_id, toggled.state_version)
    assert stale.kind == "round_active"
    stale_prepare = await service.round_prepare_view(
        actor, toggled.round_id, toggled.state_version
    )
    assert stale_prepare.kind == "round_active"
    async with database[1]() as session:
        assert (
            await session.scalar(select(func.count(HuntRound.id)))
        ) == 1
        assert (
            await session.scalar(select(func.count(HuntRoundEncounter.id)))
        ) == 1


@pytest.mark.asyncio
async def test_round_resolves_due_encounter_once_and_charges_two_vigor(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772002)
    _force_safe_common(monkeypatch, round_module)
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    assert await service.advance_due_rounds() == 1
    resumed = await service.resume(actor)
    assert resumed.kind == "round_active"
    assert resumed.completed_encounters == 1
    assert resumed.vigor == 98

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        encounters = (
            await session.scalars(
                select(HuntRoundEncounter)
                .where(HuntRoundEncounter.round_id == state.id)
                .order_by(HuntRoundEncounter.ordinal)
            )
        ).all()
        assert [row.ordinal for row in encounters] == [1, 2]
        assert encounters[0].status == "completed"
        assert encounters[1].status == "materialized"
        first_activity = encounters[0].activity_id
        assert first_activity is not None
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.source_id == f"activity:{first_activity}"
            )
        ) == 1


@pytest.mark.asyncio
async def test_round_freezes_equipment_across_encounters_and_keeps_new_level(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772021)
    _force_safe_common(monkeypatch, round_module)
    item_id = uuid4()
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character.id,
                source_key="round:frozen-equipment",
                item_name="Frozen torso",
                rarity="Comum",
                slot="Torso",
                item_level=1,
                bound=False,
                payload={
                    "slot": "Torso",
                    "core": {"HP": 10},
                    "secondaries": [],
                    "enhancement": 0,
                    "rune": None,
                    "enchantment": None,
                },
            )
        )
    equipped = await EquipmentService(database[1], "ocaso").equip_item(actor, item_id)
    assert equipped is not None and equipped.combat_configuration_version == 1
    prepared = await service.prepare_round(actor, 5)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.xp = level_xp(1) - 1
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind == "round_active"

    async with database[1].begin() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        assert state.config_snapshot["local_id"] == "tdo.location.estrada_das_cinzas"
        first = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == state.id,
                HuntRoundEncounter.ordinal == 1,
            )
        )
        frozen = equipment_configuration_from_data(
            state.config_snapshot["combat_configuration"]
        )
        assert frozen.combat_configuration_version == 1
        assert [item.item_instance_id for item in frozen.items] == [str(item_id)]
        assert first.combat_snapshot["configuration_snapshot"] == (
            state.config_snapshot["combat_configuration"]
        )
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        character = await session.scalar(
            select(Character).where(Character.id == state.character_id)
        )
        character.xp = level_xp(1) - 1
        item = await session.scalar(select(EquipmentItem).where(EquipmentItem.id == item_id))
        item.payload = item.payload | {"core": {"HP": 999}}

    async def unexpected_live_configuration_load(*args, **kwargs):
        raise AssertionError("Ronda must use its frozen equipment configuration")

    monkeypatch.setattr(
        round_module, "load_equipment_configuration", unexpected_live_configuration_load
    )

    assert await service.advance_due_rounds() == 1
    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        encounters = (
            await session.scalars(
                select(HuntRoundEncounter)
                .where(HuntRoundEncounter.round_id == state.id)
                .order_by(HuntRoundEncounter.ordinal)
            )
        ).all()
        assert [encounter.ordinal for encounter in encounters] == [1, 2]
        second = encounters[1]
        assert second.combat_snapshot["configuration_snapshot"] == (
            state.config_snapshot["combat_configuration"]
        )
        player = second.combat_snapshot["fighters"]["player"]
        assert player["level"] == 2
        expected_stats = resolve_combat_stats(
            "sentinela", 2, "remanescente", frozen.contribution()
        )
        assert Decimal(player["stats"]["hp"]) == expected_stats.hp
        assert Decimal(player["stats"]["attack"]) == expected_stats.attack
        character = await session.scalar(
            select(Character).where(Character.id == state.character_id)
        )
        assert character.level == 2
        assert character.max_hp == expected_stats.hp

    reconnected = await service.resume(actor)
    assert reconnected.kind == "round_active"
    assert reconnected.encounter_id == second.id

    async with database[1].begin() as session:
        character_row = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        blocked = EquipmentItem(
            character_id=character_row.id,
            source_key="round:blocked-mutation",
            item_name="Blocked head",
            rarity="Comum",
            slot="Cabeça",
            item_level=1,
            bound=False,
            payload={
                "slot": "Cabeça",
                "core": {"HP": 10},
                "secondaries": [],
                "enhancement": 0,
                "rune": None,
                "enchantment": None,
            },
        )
        session.add(blocked)
        blocked_id = blocked.id
    with pytest.raises(CombatConfigurationLocked):
        await EquipmentService(database[1], "ocaso").equip_item(actor, blocked_id)


@pytest.mark.asyncio
async def test_round_freezes_authoritative_active_arts_and_blocks_mutation(database):
    actor, service = await _seed_round(database, 772022)
    art_id = FIRST_CLASS_ART_IDS["sentinela"]
    art_service = ActiveArtService(database[1], "ocaso")
    equipped = await art_service.equip_art(actor, 1, art_id)
    assert equipped is not None and equipped.combat_configuration_version == 1

    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind in {"round_active", "round_interrupted"}

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        frozen = state.config_snapshot["combat_configuration"]
        assert frozen["combat_configuration_version"] == 1
        assert frozen["active_arts"] == [{"slot": 1, "art_id": art_id}]
        encounter = await session.scalar(
            select(HuntRoundEncounter)
            .where(HuntRoundEncounter.round_id == state.id)
            .order_by(HuntRoundEncounter.ordinal)
        )
        assert encounter.combat_snapshot["configuration_snapshot"] == frozen
        assert "art" in encounter.combat_snapshot["player_actions"]

    with pytest.raises(CombatConfigurationLocked):
        await art_service.unequip_slot(actor, 1, expected_configuration_version=1)

    resumed = await service.resume(actor)
    assert resumed.round_id == started.round_id
    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        assert state.config_snapshot["combat_configuration"]["active_arts"] == [
            {"slot": 1, "art_id": art_id}
        ]



@pytest.mark.asyncio
async def test_cancel_during_materialized_encounter_waits_for_boundary(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772003)
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level, **kwargs: CREATURES[0])
    prepared = await service.prepare_round(actor, 10)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)

    cancellation = await service.cancel_round(
        actor, started.round_id, started.state_version
    )
    assert cancellation.kind == "round_active"
    assert cancellation.cancel_requested is True

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    await service.advance_due_rounds()
    result = await service.resume(actor)
    assert result.kind == "round_cancelled"
    assert result.completed_encounters == 1
    assert result.reward_lines
    async with database[1]() as session:
        encounters = (
            await session.scalars(
                select(HuntRoundEncounter).where(
                    HuntRoundEncounter.round_id == started.round_id
                )
            )
        ).all()
        assert len(encounters) == 1


@pytest.mark.asyncio
async def test_vigor_ending_happens_before_next_encounter_is_created(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772004, vigor=2)
    _force_safe_common(monkeypatch, round_module)
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    await service.advance_due_rounds()
    result = await service.resume(actor)
    assert result.kind == "round_ended"
    assert result.end_reason == "vigor"
    assert result.completed_encounters == 1
    assert result.vigor == 0
    async with database[1]() as session:
        count = await session.scalar(
            select(func.count(HuntRoundEncounter.id)).where(
                HuntRoundEncounter.round_id == started.round_id
            )
        )
        assert count == 1


@pytest.mark.asyncio
async def test_elite_interrupts_before_auto_combat_and_reuses_encounter_id(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772005)
    item_id = uuid4()
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character.id,
                source_key="round:elite-frozen-equipment",
                item_name="Frozen torso",
                rarity="Comum",
                slot="Torso",
                item_level=1,
                bound=False,
                payload={
                    "slot": "Torso",
                    "core": {"HP": 10},
                    "secondaries": [],
                    "enhancement": 0,
                    "rune": None,
                    "enchantment": None,
                },
            )
        )
    equipped = await EquipmentService(database[1], "ocaso").equip_item(actor, item_id)
    assert equipped is not None and equipped.combat_configuration_version == 1
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level, **kwargs: CREATURES[3])
    prepared = await service.prepare_round(actor, 5)
    interrupted = await service.start_round(actor, prepared.round_id, prepared.state_version)

    assert interrupted.kind == "round_interrupted"
    assert interrupted.completed_encounters == 0
    assert interrupted.creature == "Alfa Cinéreo"
    persisted_encounter_id = interrupted.encounter_id

    async with database[1].begin() as session:
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == interrupted.round_id)
        )
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(HuntRoundEncounter.id == persisted_encounter_id)
        )
        frozen_data = state.config_snapshot["combat_configuration"]
        assert frozen_data["equipment"][0]["item_instance_id"] == str(item_id)
        assert encounter.combat_snapshot["configuration_snapshot"] == frozen_data
        item = await session.scalar(select(EquipmentItem).where(EquipmentItem.id == item_id))
        item.payload = item.payload | {"core": {"HP": 999}}

    async def unexpected_live_configuration_load(*args, **kwargs):
        raise AssertionError("Elite resume must use its materialized combat snapshot")

    monkeypatch.setattr(
        round_module, "load_equipment_configuration", unexpected_live_configuration_load
    )

    reopened = await service.resume(actor)
    assert reopened.kind == "round_interrupted"
    assert reopened.encounter_id == persisted_encounter_id

    combat = await service.engage_round_elite(
        actor, interrupted.round_id, interrupted.state_version
    )
    assert combat.kind == "combat"
    assert combat.encounter_id == persisted_encounter_id
    frozen_configuration = equipment_configuration_from_data(frozen_data)
    expected_stats = resolve_combat_stats(
        "sentinela", 1, "remanescente", frozen_configuration.contribution()
    )
    player = combat.combat.fighters["player"]
    assert player.stats == expected_stats
    assert combat.combat.configuration_snapshot == frozen_data
    assert player.stats.hp < resolve_combat_stats(
        "sentinela",
        1,
        "remanescente",
        equipment_configuration_from_data(
            frozen_data
            | {
                "equipment": [
                    frozen_data["equipment"][0]
                    | {"core": {"HP": "999"}}
                ]
            }
        ).contribution(),
    ).hp

    stale = await service.engage_round_elite(
        actor, interrupted.round_id, interrupted.state_version
    )
    assert stale.kind == "combat"
    assert stale.encounter_id == persisted_encounter_id

    async with database[1]() as session:
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == interrupted.round_id)
        )
        assert state.status == "ended"
        assert state.end_reason == "elite_engaged"
        assert state.result_acknowledged is True
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id == interrupted.character_id,
                GameActivity.status == "active",
            )
        ) == 1


@pytest.mark.asyncio
async def test_common_round_encounter_commits_at_most_one_consumable(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772007)
    _force_safe_common(monkeypatch, round_module)
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.hp = 300
        session.add(
            ConsumableStack(
                character_id=character.id,
                consumable_id=HEAL_CONSUMABLE,
                quantity=3,
            )
        )
        await session.commit()

    prepared = await service.prepare_round(actor, 5)
    toggled = await service.toggle_round_consumable(
        actor, prepared.round_id, prepared.state_version, HEAL_CONSUMABLE
    )
    started = await service.start_round(actor, toggled.round_id, toggled.state_version)
    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    await service.advance_due_rounds()
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        quantity = await session.scalar(
            select(ConsumableStack.quantity).where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == HEAL_CONSUMABLE,
            )
        )
        assert quantity == 2


@pytest.mark.asyncio
async def test_common_round_automatically_consumes_legacy_purification_stock(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772008)
    _force_safe_common(monkeypatch, round_module)
    original = round_module.create_road_combat

    def poisoned_combat(*args, **kwargs):
        combat = original(*args, **kwargs)
        combat.fighters["player"].hp = Decimal("1")
        combat.dot_states["player"] = [
            DotState(
                "poison",
                2,
                3,
                Decimal("10000"),
                "enemy",
                [Decimal("10000"), Decimal("10000")],
            )
        ]
        return combat

    monkeypatch.setattr(round_module, "create_road_combat", poisoned_combat)
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            ConsumableStack(
                character_id=character.id,
                consumable_id=PURIFY_CONSUMABLE,
                quantity=2,
            )
        )
        await session.commit()

    prepared = await service.prepare_round(actor, 5)
    toggled = await service.toggle_round_consumable(
        actor, prepared.round_id, prepared.state_version, PURIFY_CONSUMABLE
    )
    started = await service.start_round(actor, toggled.round_id, toggled.state_version)
    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    await service.advance_due_rounds()
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        quantity = await session.scalar(
            select(ConsumableStack.quantity).where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == PURIFY_CONSUMABLE,
            )
        )
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(HuntRoundEncounter.round_id == started.round_id)
        )
        record = await session.scalar(
            select(CombatRecord).where(CombatRecord.encounter_id == encounter.id)
        )
        assert quantity == 1
        assert record is not None
        assert "consumable:purify" in [event["action"] for event in record.snapshot["events"]]


@pytest.mark.asyncio
async def test_terminal_round_result_acknowledges_without_restarting_batch(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772006, vigor=0)
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level, **kwargs: CREATURES[0])
    prepared = await service.prepare_round(actor, 5)
    result = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert result.kind == "round_ended"
    assert result.end_reason == "vigor"

    back = await service.round_back(actor, result.round_id)
    assert back.kind == "hunt_prepare"
    resumed = await service.resume(actor)
    assert resumed.kind == "road"

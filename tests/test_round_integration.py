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
from asterion.application.talents import TalentService
from asterion.application.vigor import REGEN_INTERVAL_SECONDS
from asterion.domain.arts import (
    BASTIAO_ART_IDS,
    DEVASTADOR_ART_IDS,
    FIRST_CLASS_ART_IDS,
)
from asterion.domain.combat import DotState
from asterion.domain.combat_math import Stats, resolve_combat_stats
from asterion.domain.equipment_stats import equipment_configuration_from_data
from asterion.domain.road import CREATURES, ROUND_FAMILIARITY
from asterion.domain.talents import TALENTS_BY_CLASS
from asterion.infrastructure.db.models import (
    Character,
    CombatRecord,
    ConsumableStack,
    EquipmentItem,
    GameActivity,
    HuntRound,
    HuntRoundEncounter,
    RewardComponent,
    RewardEvent,
    Unlock,
)
from tests.helpers.weapon_metadata import add_compatible_weapon_for_arts
from tests.test_road_integration import _seed_road


async def _seed_round(
    database, actor: int, *, vigor: int = 100, pvpve: bool = False
):
    await _seed_road(database, actor, vigor=vigor)
    sessions = database[1]
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(Unlock(character_id=character.id, unlock_id=ROUND_FAMILIARITY))
        await session.commit()
    service = RoundService(sessions, "ocaso")
    if not pvpve:
        async def no_round_match(*_args, **_kwargs):
            return False

        service.pvpve.queue_round_hunt = no_round_match
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
async def test_round_snapshot_uses_a_legally_acquired_nv25_talent(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772020)
    _force_safe_common(monkeypatch, round_module)
    sessions = database[1]
    talent = next(
        item for item in TALENTS_BY_CLASS["sentinela"] if item.level == 25
    )
    expected_stats = resolve_combat_stats("sentinela", 25, "remanescente")
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = 25
        character.xp = level_xp(25)
        character.hp = expected_stats.hp
        character.max_hp = expected_stats.hp

    talents = TalentService(sessions, "ocaso")
    view = await talents.view(actor)
    assert view is not None and view.available_points == 5
    acquired = await talents.acquire(
        actor, talent.talent_id, view.combat_configuration_version
    )
    assert acquired is not None and acquired.changed

    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind == "round_active"
    async with sessions() as session:
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == started.round_id)
        )
        encounter = await session.scalar(
            select(HuntRoundEncounter)
            .where(HuntRoundEncounter.round_id == started.round_id)
            .order_by(HuntRoundEncounter.ordinal)
        )
        assert state is not None and encounter is not None
        frozen = equipment_configuration_from_data(
            state.config_snapshot["combat_configuration"]
        )
        expected_choice = {"point_slot": 1, "talent_id": talent.talent_id}
        assert frozen.talent_choices == ((1, talent.talent_id),)
        assert state.config_snapshot["combat_configuration"]["talents"] == [
            expected_choice
        ]
        assert encounter.combat_snapshot["configuration_snapshot"]["talents"] == [
            expected_choice
        ]
        assert encounter.combat_snapshot["fighters"]["player"]["talent_ids"] == [
            talent.talent_id
        ]


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
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        await add_compatible_weapon_for_arts(session, character.id, (art_id,))
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
        assert FIRST_CLASS_ART_IDS["sentinela"] in encounter.combat_snapshot["player_actions"]
        assert "art" not in encounter.combat_snapshot["player_actions"]

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
async def test_round_snapshots_equipped_devastador_ariete(database):
    actor, service = await _seed_round(database, 772024)
    art_id = DEVASTADOR_ART_IDS["ariete"]
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = 20
        character.selected_path = "devastador"
        session.add(Unlock(character_id=character.id, unlock_id="class_trial_completed"))
        await add_compatible_weapon_for_arts(session, character.id, (art_id,))

    art_service = ActiveArtService(database[1], "ocaso")
    equipped = await art_service.equip_art(actor, 2, art_id)
    assert equipped is not None and equipped.changed
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind in {"round_active", "round_interrupted"}

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        frozen = state.config_snapshot["combat_configuration"]
        assert frozen["active_arts"] == [{"slot": 2, "art_id": art_id}]
        assert frozen["selected_path"] == "devastador"
        encounter = await session.scalar(
            select(HuntRoundEncounter)
            .where(HuntRoundEncounter.round_id == state.id)
            .order_by(HuntRoundEncounter.ordinal)
        )
        assert art_id in encounter.combat_snapshot["player_actions"]

    resumed = await service.resume(actor)
    assert resumed.round_id == started.round_id
    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        encounter = await session.scalar(
            select(HuntRoundEncounter)
            .where(HuntRoundEncounter.round_id == state.id)
            .order_by(HuntRoundEncounter.ordinal)
        )
        assert state.config_snapshot["combat_configuration"] == frozen
        assert art_id in encounter.combat_snapshot["player_actions"]


@pytest.mark.asyncio
async def test_round_snapshots_equipped_bastiao_path_art(database):
    actor, service = await _seed_round(database, 772025)
    art_id = BASTIAO_ART_IDS["escudo_de_cinzas"]
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = 12
        character.selected_path = "bastiao"
        session.add(Unlock(character_id=character.id, unlock_id="class_trial_completed"))

    art_service = ActiveArtService(database[1], "ocaso")
    equipped = await art_service.equip_art(actor, 1, art_id)
    assert equipped is not None and equipped.changed

    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind in {"round_active", "round_interrupted"}

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        frozen = state.config_snapshot["combat_configuration"]
        assert frozen["selected_path"] == "bastiao"
        assert frozen["active_arts"] == [{"slot": 1, "art_id": art_id}]
        encounter = await session.scalar(
            select(HuntRoundEncounter)
            .where(HuntRoundEncounter.round_id == state.id)
            .order_by(HuntRoundEncounter.ordinal)
        )
        assert art_id in encounter.combat_snapshot["player_actions"]

    resumed = await service.resume(actor)
    assert resumed.round_id == started.round_id
    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        encounter = await session.scalar(
            select(HuntRoundEncounter)
            .where(HuntRoundEncounter.round_id == state.id)
            .order_by(HuntRoundEncounter.ordinal)
        )
        assert state.config_snapshot["combat_configuration"]["selected_path"] == "bastiao"
        assert art_id in encounter.combat_snapshot["player_actions"]



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
async def test_round_observes_natural_vigor_regeneration_between_encounters(
    database, monkeypatch
):
    import asterion.application.round as round_module
    import asterion.application.vigor as vigor_module

    actor, service = await _seed_round(database, 772120, vigor=2)
    _force_safe_common(monkeypatch, round_module)
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind == "round_active"

    anchor = datetime.now(UTC)
    target = anchor + timedelta(seconds=864)

    class JourneyClock(datetime):
        instant = target

        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return cls.instant.replace(tzinfo=None)
            return cls.instant.astimezone(tz)

    monkeypatch.setattr(round_module, "datetime", JourneyClock)
    monkeypatch.setattr(vigor_module, "utcnow", lambda: target)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor).with_for_update()
        )
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == started.round_id).with_for_update()
        )
        character.vigor = 1
        character.vigor_regen_at = anchor
        state.next_resolution_at = target

    assert await service.advance_due_rounds() == 1
    result = await service.resume(actor)
    assert result.kind == "round_ended"
    assert result.completed_encounters == 1
    assert result.vigor == 0

    async with database[1]() as session:
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == started.round_id,
                HuntRoundEncounter.ordinal == 1,
            )
        )
        assert encounter is not None and encounter.activity_id is not None
        crowns = await session.scalar(
            select(func.count(RewardComponent.id))
            .join(RewardEvent, RewardEvent.id == RewardComponent.reward_event_id)
            .where(
                RewardEvent.source_id == f"activity:{encounter.activity_id}",
                RewardComponent.kind == "crowns",
            )
        )
        assert crowns == 1


def _install_round_clock(monkeypatch, instant):
    import asterion.application.round as round_module
    import asterion.application.vigor as vigor_module

    class ControlledDateTime(datetime):
        current = instant

        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return cls.current.replace(tzinfo=None)
            return cls.current.astimezone(tz)

    monkeypatch.setattr(round_module, "datetime", ControlledDateTime)
    monkeypatch.setattr(vigor_module, "utcnow", lambda: ControlledDateTime.current)
    return ControlledDateTime


async def _advance_round_cadence(clock, service, actor, count):
    result = None
    for _ in range(count):
        clock.current += timedelta(minutes=3)
        await service.advance_due_rounds()
        result = await service.resume(actor)
        if result.kind != "round_active":
            break
    return result


@pytest.mark.asyncio
async def test_delayed_round_catchup_cannot_finance_future_encounters_with_vigor(
    database, monkeypatch
):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772121, vigor=2)
    _force_safe_common(monkeypatch, round_module)
    start = datetime.now(UTC)
    clock = _install_round_clock(monkeypatch, start)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor).with_for_update()
        )
        character.vigor_regen_at = start

    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind == "round_active"

    clock.current = start + timedelta(hours=12)
    assert await service.advance_due_rounds() == 1

    async with database[1]() as session:
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == started.round_id)
        )
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        encounters = (
            await session.scalars(
                select(HuntRoundEncounter)
                .where(HuntRoundEncounter.round_id == started.round_id)
                .order_by(HuntRoundEncounter.ordinal)
            )
        ).all()
        assert state.status == "ended" and state.end_reason == "vigor"
        assert state.completed_encounters == 1
        assert character.vigor == 0
        assert [(row.ordinal, row.status) for row in encounters] == [(1, "completed")]

    # Reconnect at worker wall-clock time may naturally refill Vigor, but must
    # leave the terminal batch closed and never materialize another encounter.
    resumed = await service.resume(actor)
    assert resumed.kind == "round_ended"
    assert await service.advance_due_rounds() == 0
    async with database[1]() as session:
        assert await session.scalar(
            select(func.count(HuntRoundEncounter.id)).where(
                HuntRoundEncounter.round_id == started.round_id
            )
        ) == 1


@pytest.mark.asyncio
async def test_round_five_encounters_pointwise_and_delayed_catchup_are_economically_equal(
    database, monkeypatch
):
    import asterion.application.road as road_module
    import asterion.application.round as round_module

    actor_on_time, on_time_service = await _seed_round(database, 772122, vigor=10)
    actor_delayed, delayed_service = await _seed_round(database, 772123, vigor=10)
    _force_safe_common(monkeypatch, round_module)
    monkeypatch.setattr(road_module, "_draw_int", lambda seed, label, upper: upper - 1)
    start = datetime.now(UTC)
    clock = _install_round_clock(monkeypatch, start)
    async with database[1].begin() as session:
        for actor in (actor_on_time, actor_delayed):
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor).with_for_update()
            )
            character.vigor_regen_at = start

    on_time_prepare = await on_time_service.prepare_round(actor_on_time, 5)
    on_time_start = await on_time_service.start_round(
        actor_on_time, on_time_prepare.round_id, on_time_prepare.state_version
    )
    assert on_time_start.kind == "round_active"
    assert (await on_time_service.resume(actor_on_time)).round_id == on_time_start.round_id
    on_time_result = await _advance_round_cadence(
        clock, on_time_service, actor_on_time, 5
    )
    assert on_time_result.kind == "round_completed"
    assert on_time_result.completed_encounters == 5
    on_time_seed = on_time_start.round_id

    delayed_start_time = clock.current
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor_delayed)
            .with_for_update()
        )
        character.vigor_regen_at = delayed_start_time
    delayed_prepare = await delayed_service.prepare_round(actor_delayed, 5)
    delayed_start = await delayed_service.start_round(
        actor_delayed, delayed_prepare.round_id, delayed_prepare.state_version
    )
    assert delayed_start.kind == "round_active"
    assert (await delayed_service.resume(actor_delayed)).round_id == delayed_start.round_id
    clock.current = delayed_start_time + timedelta(hours=12)
    assert await delayed_service.advance_due_rounds() == 1

    async with database[1]() as session:
        on_time_state = await session.scalar(
            select(HuntRound).where(HuntRound.id == on_time_start.round_id)
        )
        delayed_state = await session.scalar(
            select(HuntRound).where(HuntRound.id == delayed_start.round_id)
        )
        on_time_character = await session.scalar(
            select(Character).where(Character.telegram_id == actor_on_time)
        )
        delayed_character = await session.scalar(
            select(Character).where(Character.telegram_id == actor_delayed)
        )
        assert on_time_state.config_snapshot == delayed_state.config_snapshot
        assert on_time_state.completed_encounters == delayed_state.completed_encounters == 5
        assert on_time_state.status == delayed_state.status == "completed"
        assert on_time_character.vigor == delayed_character.vigor == 1
        assert on_time_character.xp == delayed_character.xp
        assert on_time_character.crowns == delayed_character.crowns
        for round_id in (on_time_seed, delayed_start.round_id):
            encounters = (
                await session.scalars(
                    select(HuntRoundEncounter)
                    .where(HuntRoundEncounter.round_id == round_id)
                    .order_by(HuntRoundEncounter.ordinal)
                )
            ).all()
            assert [row.status for row in encounters] == ["completed"] * 5
            assert len({row.ordinal for row in encounters}) == 5
            activity_ids = [row.activity_id for row in encounters]
            assert all(activity_ids)
            reward_count = await session.scalar(
                select(func.count(RewardEvent.id)).where(
                    RewardEvent.source_id.in_([f"activity:{item}" for item in activity_ids])
                )
            )
            assert reward_count == 5

    # Reconnect later may regenerate Vigor naturally, but it must not reopen
    # the completed batch or alter any of its already-settled rewards.
    delayed_result = await delayed_service.resume(actor_delayed)
    assert delayed_result.kind == "round_completed"
    assert delayed_result.completed_encounters == 5


@pytest.mark.asyncio
async def test_round_regeneration_is_first_available_at_next_due_boundary(
    database, monkeypatch
):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772124, vigor=10)
    _force_safe_common(monkeypatch, round_module)
    start = datetime.now(UTC)
    clock = _install_round_clock(monkeypatch, start)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor).with_for_update()
        )
        character.vigor_regen_at = start
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind == "round_active"

    clock.current = start + timedelta(minutes=12)
    await service.advance_due_rounds()
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character.vigor == 2

    clock.current = start + timedelta(seconds=REGEN_INTERVAL_SECONDS)
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character.vigor == 2

    clock.current = start + timedelta(minutes=15)
    await service.advance_due_rounds()
    result = await service.resume(actor)
    assert result.kind == "round_completed"
    assert result.completed_encounters == 5
    assert result.vigor == 1
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
    assert back.kind == "road"
    resumed = await service.resume(actor)
    assert resumed.kind == "road"


@pytest.mark.asyncio
async def test_leaving_round_preparation_returns_to_local_without_cost(database):
    actor, service = await _seed_round(database, 772099, vigor=73)
    prepared = await service.prepare_round(actor, 10)
    assert prepared.kind == "round_prepare"

    selection = await service.round_back(actor, prepared.round_id)
    assert selection.kind == "round_select"
    assert selection.location == prepared.location
    resumed = await service.resume(actor)
    assert resumed.kind == "road"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        state = await session.scalar(select(HuntRound).where(HuntRound.id == prepared.round_id))
        assert character.vigor == 73
        assert state.status == "cancelled"
        assert state.result_acknowledged is True


@pytest.mark.asyncio
async def test_round_preparation_back_callback_returns_to_round_selection(database):
    from unittest.mock import AsyncMock

    from aiogram import Bot, Dispatcher

    from asterion.application.world import WorldService
    from asterion.bot.world_handlers import world_router
    from tests.test_creation_ui import callback_update

    actor, service = await _seed_round(database, 772101, vigor=73)
    prepared = await service.prepare_round(actor, 10)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(WorldService(database[1], "ocaso"), {}, road=service)
    )
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            f"road:round:back:{prepared.round_id.hex}",
            update_id=772102,
            actor=actor,
        ),
    )
    response = bot.session.make_request.call_args.args[1]
    callbacks = [
        button.callback_data
        for row in response.reply_markup.inline_keyboard
        for button in row
    ]
    assert "Escolha o tamanho do lote." in response.text
    assert callbacks[:3] == [
        "road:round:new:5",
        "road:round:new:10",
        "road:round:new:20",
    ]
    assert callbacks[-1] == "world:local"
    await dispatcher.feed_raw_update(
        bot,
        callback_update("road:round:new:5", update_id=772103, actor=actor),
    )
    next_preparation = bot.session.make_request.call_args.args[1]
    assert "🎯 Ronda · 5 Encontros" in next_preparation.text
    new_round_id = await service.resume(actor)
    assert new_round_id.kind == "round_prepare"
    assert new_round_id.round_id != prepared.round_id
    async with database[1]() as session:
        states = (
            await session.scalars(
                select(HuntRound).where(HuntRound.character_id == new_round_id.character_id)
            )
        ).all()
        assert sum(state.status == "preparing" for state in states) == 1

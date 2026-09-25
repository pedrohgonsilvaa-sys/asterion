import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

import asterion.application.equipment as equipment_module
from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.application.equipment import (
    EquipmentMutationCode,
    EquipmentMutationRejected,
    EquipmentMutationStatus,
    EquipmentService,
)
from asterion.application.inventory import InventoryService
from asterion.application.progression import consolidate_character_level, level_xp
from asterion.application.road import ROAD
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.equipment import EquipmentSlot
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.road import materialize_equipment
from asterion.infrastructure.db.models import (
    Account,
    BlockedDelivery,
    Character,
    CharacterEquipmentSlot,
    EquipmentItem,
    GameActivity,
    HuntRound,
    PendingItem,
)
from tests.test_road_integration import _seed_road


async def _seed_actor(database, actor: int):
    await _seed_road(database, actor=actor)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor))
        character.name = f"H{suffix}"
    async with database[1]() as session:
        character_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == actor)
        )
    return character_id


async def _seed_foreign_character(database, actor: int):
    character_id = uuid4()
    async with database[1].begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Foreign",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.6-baseline-1.0",
                level=1,
                xp=0,
                hp=702,
                max_hp=702,
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
    return character_id


async def _add_item(
    database,
    character_id,
    source_key: str,
    slot: str,
    *,
    rarity: str = "Comum",
    item_level: int = 1,
    payload: dict | None = None,
):
    item_id = uuid4()
    core_attribute = {
        "Principal": "ATQ",
        "2H": "ATQ",
        "Arma Principal": "ATQ",
        "Secundária": "ATQ",
        "Cabeça": "HP",
        "Torso": "HP",
        "Mãos": "ATQ",
        "Pés": "HP",
        "Acessório": "HP",
        "Artefato": "HP",
    }[slot]
    async with database[1].begin() as session:
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character_id,
                source_key=source_key,
                item_name=f"{source_key} item",
                rarity=rarity,
                slot=slot,
                item_level=item_level,
                bound=False,
                payload=payload or {
                    "slot": slot,
                    "core": {core_attribute: 10},
                    "secondaries": [],
                    "enhancement": 0,
                    "rune": None,
                    "enchantment": None,
                },
            )
        )
    return item_id


async def _equipment_state(database, actor: int):
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        rows = (
            await session.scalars(
                select(CharacterEquipmentSlot).where(
                    CharacterEquipmentSlot.character_id == character.id
                )
            )
        ).all()
        return character.combat_configuration_version, {
            row.slot: row.equipment_item_id for row in rows
        }


async def _wait_for_postgres_lock(database, query_fragment: str) -> None:
    _, sessions = database
    deadline = asyncio.get_running_loop().time() + 5
    statement = text(
        """
        SELECT EXISTS (
            SELECT 1 FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid <> pg_backend_pid()
              AND wait_event_type = 'Lock'
              AND query ILIKE :query_pattern
        )
        """
    )
    while asyncio.get_running_loop().time() < deadline:
        async with sessions() as observer:
            waiting = await observer.scalar(
                statement, {"query_pattern": f"%{query_fragment}%"}
            )
        if waiting:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"No PostgreSQL lock wait observed for {query_fragment}")


@pytest.mark.asyncio
async def test_equip_replace_noops_unequip_and_configuration_version(database):
    actor = 907101
    character_id = await _seed_actor(database, actor)
    first = await _add_item(database, character_id, "equip:first", "Principal")
    replacement = await _add_item(database, character_id, "equip:replacement", "Principal")
    service = EquipmentService(database[1], "ocaso")

    equipped = await service.equip_item(actor, first, expected_configuration_version=0)
    assert equipped is not None
    assert (equipped.status, equipped.combat_configuration_version) == (
        EquipmentMutationStatus.CHANGED,
        1,
    )
    repeat = await service.equip_item(actor, first, expected_configuration_version=1)
    assert repeat is not None and repeat.status == EquipmentMutationStatus.ALREADY_EQUIPPED
    assert repeat.combat_configuration_version == 1

    swapped = await service.equip_item(actor, replacement, expected_configuration_version=1)
    assert swapped is not None and swapped.changed and swapped.combat_configuration_version == 2
    version, slots = await _equipment_state(database, actor)
    assert version == 2
    assert slots == {EquipmentSlot.PRINCIPAL.value: replacement}
    async with database[1]() as session:
        assert await session.scalar(select(EquipmentItem.id).where(EquipmentItem.id == first))
        assert await session.scalar(select(EquipmentItem.id).where(EquipmentItem.id == replacement))

    empty = await service.unequip_slot(
        actor, EquipmentSlot.SECUNDARIA, expected_configuration_version=2
    )
    assert empty is not None and empty.status == EquipmentMutationStatus.ALREADY_EMPTY
    assert empty.combat_configuration_version == 2
    removed = await service.unequip_slot(
        actor, EquipmentSlot.PRINCIPAL, expected_configuration_version=2
    )
    assert removed is not None and removed.changed and removed.combat_configuration_version == 3
    version, slots = await _equipment_state(database, actor)
    assert version == 3 and slots == {}


@pytest.mark.asyncio
async def test_equipment_hp_changes_preserve_percentage_and_never_revive(database):
    actor = 907120
    character_id = await _seed_actor(database, actor)
    base_hp = resolve_combat_stats("sentinela", 1, "remanescente").hp
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.max_hp = base_hp
        character.hp = base_hp / Decimal(2)
    item_id = await _add_item(
        database,
        character_id,
        "equip:hp-preserve",
        "Torso",
        payload={
            "slot": "Torso",
            "core": {"HP": 100},
            "secondaries": [],
            "enhancement": 0,
            "rune": None,
            "enchantment": None,
        },
    )
    service = EquipmentService(database[1], "ocaso")
    result = await service.equip_item(actor, item_id)
    assert result is not None and result.changed
    equipped_max = resolve_combat_stats(
        "sentinela",
        1,
        "remanescente",
        EquipmentStatContribution(hp=Decimal(100)),
    ).hp
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character.max_hp == equipped_max
        assert character.hp == Decimal(407)
    unchanged = await service.equip_item(actor, item_id, expected_configuration_version=1)
    assert unchanged is not None and unchanged.status == EquipmentMutationStatus.ALREADY_EQUIPPED
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert (character.hp, character.max_hp, character.combat_configuration_version) == (
            Decimal(407), equipped_max, 1
        )

    removed = await service.unequip_slot(
        actor, "Torso", expected_configuration_version=1
    )
    assert removed is not None and removed.changed
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character.max_hp == base_hp
        assert character.hp == Decimal(356)

    dead_actor = 907121
    dead_character_id = await _seed_actor(database, dead_actor)
    dead_item = await _add_item(
        database,
        dead_character_id,
        "equip:hp-dead",
        "Torso",
        payload={
            "slot": "Torso",
            "core": {"HP": 100},
            "secondaries": [],
            "enhancement": 0,
            "rune": None,
            "enchantment": None,
        },
    )
    async with database[1].begin() as session:
        dead = await session.scalar(
            select(Character).where(Character.telegram_id == dead_actor)
        )
        dead.max_hp = base_hp
        dead.hp = 0
    await EquipmentService(database[1], "ocaso").equip_item(dead_actor, dead_item)
    async with database[1]() as session:
        dead = await session.scalar(
            select(Character).where(Character.telegram_id == dead_actor)
        )
        assert dead.hp == 0 and dead.max_hp == equipped_max

    legacy_actor = 907124
    legacy_character_id = await _seed_actor(database, legacy_actor)
    legacy_head = await _add_item(
        database, legacy_character_id, "equip:legacy-hp", "Cabeça"
    )
    new_weapon = await _add_item(
        database, legacy_character_id, "equip:legacy-hp-mutation", "Principal"
    )
    async with database[1].begin() as session:
        legacy = await session.scalar(
            select(Character).where(Character.telegram_id == legacy_actor)
        )
        legacy.max_hp = base_hp
        legacy.hp = base_hp / Decimal(2)
        legacy.combat_configuration_version = 1
        session.add(
            CharacterEquipmentSlot(
                character_id=legacy_character_id,
                slot=EquipmentSlot.CABECA.value,
                equipment_item_id=legacy_head,
            )
        )
    legacy_result = await EquipmentService(database[1], "ocaso").equip_item(
        legacy_actor, new_weapon, expected_configuration_version=1
    )
    assert legacy_result is not None and legacy_result.changed
    expected_legacy_stats = resolve_combat_stats(
        "sentinela", 1, "remanescente", EquipmentStatContribution(hp=Decimal(10))
    )
    async with database[1]() as session:
        legacy = await session.scalar(
            select(Character).where(Character.telegram_id == legacy_actor)
        )
        assert legacy.max_hp == expected_legacy_stats.hp
        assert legacy.hp == Decimal(361)


@pytest.mark.asyncio
async def test_full_hp_equipping_and_non_hp_mutation_preserve_current_health(
    database, monkeypatch
):
    actor = 907125
    character_id = await _seed_actor(database, actor)
    base_stats = resolve_combat_stats("sentinela", 1, "remanescente")
    item_id = await _add_item(
        database,
        character_id,
        "equip:hp-full",
        "Torso",
        payload={
            "slot": "Torso",
            "core": {"HP": 100},
            "secondaries": [],
            "enhancement": 0,
            "rune": None,
            "enchantment": None,
        },
    )
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.max_hp = base_stats.hp
        character.hp = base_stats.hp
    result = await EquipmentService(database[1], "ocaso").equip_item(actor, item_id)
    expected = resolve_combat_stats(
        "sentinela", 1, "remanescente", EquipmentStatContribution(hp=Decimal(100))
    )
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert result is not None and result.changed
        assert character.hp == Decimal(814)
        assert character.max_hp == expected.hp

    no_hp_actor = 907126
    no_hp_character_id = await _seed_actor(database, no_hp_actor)
    weapon_id = await _add_item(
        database, no_hp_character_id, "equip:no-hp", "Principal"
    )
    torso_id = await _add_item(
        database,
        no_hp_character_id,
        "equip:hp-rollback",
        "Torso",
        payload={
            "slot": "Torso",
            "core": {"HP": 100},
            "secondaries": [],
            "enhancement": 0,
            "rune": None,
            "enchantment": None,
        },
    )
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == no_hp_actor)
        )
        character.max_hp = base_stats.hp
        character.hp = Decimal(333)
    service = EquipmentService(database[1], "ocaso")
    await service.equip_item(no_hp_actor, weapon_id)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == no_hp_actor)
        )
        assert (character.hp, character.max_hp) == (Decimal(333), base_stats.hp)
        state_before_failure = (
            character.hp,
            character.max_hp,
            character.combat_configuration_version,
        )

    async def fail_after_hp_reconciliation(*args, **kwargs):
        raise RuntimeError("injected equipment slot write failure")

    monkeypatch.setattr(
        EquipmentService,
        "_write_equipped",
        staticmethod(fail_after_hp_reconciliation),
    )
    with pytest.raises(RuntimeError, match="injected equipment slot write failure"):
        await service.equip_item(no_hp_actor, torso_id)
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == no_hp_actor)
        )
        slots = (
            await session.scalars(
                select(CharacterEquipmentSlot).where(
                    CharacterEquipmentSlot.character_id == character.id
                )
            )
        ).all()
        assert (
            character.hp,
            character.max_hp,
            character.combat_configuration_version,
        ) == state_before_failure
        assert len(slots) == 1 and slots[0].equipment_item_id == weapon_id


@pytest.mark.asyncio
async def test_level_consolidation_uses_current_equipped_contribution(database):
    actor = 907127
    character_id = await _seed_actor(database, actor)
    item_id = await _add_item(
        database,
        character_id,
        "equip:progression-hp",
        "Cabeça",
        payload={
            "slot": "Cabeça",
            "core": {"HP": 10},
            "secondaries": [],
            "enhancement": 0,
            "rune": None,
            "enchantment": None,
        },
    )
    await EquipmentService(database[1], "ocaso").equip_item(actor, item_id)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor).with_for_update()
        )
        character.xp = level_xp(1)
        character.hp = Decimal(500)
        assert await consolidate_character_level(session, character) == 1
        assert character.level == 2
        expected = resolve_combat_stats(
            character.character_class,
            character.level,
            character.race,
            EquipmentStatContribution(hp=Decimal(10)),
        )
        assert character.max_hp == expected.hp
        assert character.hp == Decimal(500)


@pytest.mark.asyncio
async def test_equip_revalidates_owner_item_level_and_expected_version(database):
    actor = 907102
    other_actor = 907103
    character_id = await _seed_actor(database, actor)
    other_character_id = await _seed_foreign_character(database, other_actor)
    too_high = await _add_item(database, character_id, "equip:too-high", "Cabeça", item_level=2)
    foreign = await _add_item(database, other_character_id, "equip:foreign", "Cabeça")
    service = EquipmentService(database[1], "ocaso")

    with pytest.raises(EquipmentMutationRejected) as level_error:
        await service.equip_item(actor, too_high)
    assert level_error.value.code == EquipmentMutationCode.ITEM_LEVEL_REQUIRED
    with pytest.raises(EquipmentMutationRejected) as owner_error:
        await service.equip_item(actor, foreign)
    assert owner_error.value.code == EquipmentMutationCode.ITEM_UNAVAILABLE
    with pytest.raises(EquipmentMutationRejected) as stale_error:
        await service.equip_item(actor, too_high, expected_configuration_version=1)
    assert stale_error.value.code == EquipmentMutationCode.STALE_CONFIGURATION
    with pytest.raises(EquipmentMutationRejected) as missing_error:
        await service.equip_item(actor, uuid4())
    assert missing_error.value.code == EquipmentMutationCode.ITEM_UNAVAILABLE
    version, slots = await _equipment_state(database, actor)
    assert version == 0 and slots == {}


@pytest.mark.asyncio
async def test_two_handed_equipment_clears_secondary_and_inventory_reports_block(database):
    actor = 907104
    character_id = await _seed_actor(database, actor)
    secondary = await _add_item(database, character_id, "equip:secondary", "Secundária")
    two_handed = await _add_item(database, character_id, "equip:2h", "2H")
    service = EquipmentService(database[1], "ocaso")
    await service.equip_item(actor, secondary)
    result = await service.equip_item(actor, two_handed, expected_configuration_version=1)
    assert result is not None and result.changed and result.combat_configuration_version == 2
    version, slots = await _equipment_state(database, actor)
    assert version == 2
    assert slots == {EquipmentSlot.PRINCIPAL.value: two_handed}

    inventory = await InventoryService(database[1], "ocaso").category(actor, "equipment")
    assert inventory is not None and inventory.secondary_blocked_by_two_handed
    by_id = {entry.key: entry for entry in inventory.entries}
    assert by_id[str(two_handed)].equipped_slot == EquipmentSlot.PRINCIPAL.value
    assert by_id[str(secondary)].equipped_slot is None

    with pytest.raises(EquipmentMutationRejected) as raised:
        await service.equip_item(actor, secondary, expected_configuration_version=2)
    assert raised.value.code == EquipmentMutationCode.SECONDARY_BLOCKED_BY_TWO_HANDED
    blocked = await service.unequip_slot(
        actor, EquipmentSlot.SECUNDARIA, expected_configuration_version=2
    )
    assert blocked is not None
    assert blocked.status == EquipmentMutationStatus.BLOCKED_BY_TWO_HANDED
    assert blocked.combat_configuration_version == 2

    await service.unequip_slot(actor, EquipmentSlot.PRINCIPAL, expected_configuration_version=2)
    inventory = await InventoryService(database[1], "ocaso").category(actor, "equipment")
    assert inventory is not None and not inventory.secondary_blocked_by_two_handed


@pytest.mark.asyncio
async def test_one_handed_principal_replaces_two_handed_and_unblocks_secondary(database):
    actor = 907105
    character_id = await _seed_actor(database, actor)
    two_handed = await _add_item(database, character_id, "equip:2h-replace", "2H")
    one_handed = await _add_item(database, character_id, "equip:1h-replace", "Principal")
    service = EquipmentService(database[1], "ocaso")
    await service.equip_item(actor, two_handed)
    result = await service.equip_item(actor, one_handed, expected_configuration_version=1)
    assert result is not None and result.combat_configuration_version == 2
    view = await InventoryService(database[1], "ocaso").category(actor, "equipment")
    assert view is not None and not view.secondary_blocked_by_two_handed
    version, slots = await _equipment_state(database, actor)
    assert version == 2 and slots == {EquipmentSlot.PRINCIPAL.value: one_handed}


@pytest.mark.asyncio
async def test_final_state_enforces_one_mythic_but_allows_same_slot_replacement(database):
    actor = 907106
    character_id = await _seed_actor(database, actor)
    mythic_head = await _add_item(
        database, character_id, "equip:mythic-head", "Cabeça", rarity="Mítico"
    )
    replacement_head = await _add_item(
        database, character_id, "equip:mythic-head-replacement", "Cabeça", rarity="Mítico"
    )
    mythic_main = await _add_item(
        database, character_id, "equip:mythic-main", "Principal", rarity="Mítico"
    )
    service = EquipmentService(database[1], "ocaso")

    await service.equip_item(actor, mythic_head)
    with pytest.raises(EquipmentMutationRejected) as raised:
        await service.equip_item(actor, mythic_main, expected_configuration_version=1)
    assert raised.value.code == EquipmentMutationCode.MYTHIC_LIMIT
    replaced = await service.equip_item(
        actor, replacement_head, expected_configuration_version=1
    )
    assert replaced is not None and replaced.changed
    assert replaced.combat_configuration_version == 2
    version, slots = await _equipment_state(database, actor)
    assert version == 2 and slots == {EquipmentSlot.CABECA.value: replacement_head}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("round_status", "blocked"),
    [
        ("preparing", False),
        ("active", True),
        ("interrupted", True),
        ("completed", False),
        ("cancelled", False),
        ("defeated", False),
        ("ended", False),
    ],
)
async def test_equipment_service_reuses_ronda_configuration_guard(
    database, round_status, blocked
):
    actor = 907107
    character_id = await _seed_actor(database, actor)
    item_id = await _add_item(database, character_id, f"equip:round:{round_status}", "Torso")
    async with database[1].begin() as session:
        session.add(
            HuntRound(
                character_id=character_id,
                status=round_status,
                batch_size=5,
                seed=f"seed-{round_status}",
            )
        )
    service = EquipmentService(database[1], "ocaso")
    if blocked:
        with pytest.raises(CombatConfigurationLocked) as raised:
            await service.equip_item(actor, item_id)
        assert raised.value.blocker.kind == "hunt_round"
        assert raised.value.blocker.status == round_status
    else:
        result = await service.equip_item(actor, item_id)
        assert result is not None and result.changed


@pytest.mark.asyncio
async def test_active_foreground_activity_blocks_equipment_mutation(database):
    actor = 907108
    character_id = await _seed_actor(database, actor)
    item_id = await _add_item(database, character_id, "equip:active-activity", "Torso")
    async with database[1].begin() as session:
        session.add(
            GameActivity(
                character_id=character_id,
                content_id="test.combat",
                status="active",
                state_version=0,
                ruleset_version="test-ruleset",
            )
        )
    with pytest.raises(CombatConfigurationLocked) as raised:
        await EquipmentService(database[1], "ocaso").equip_item(actor, item_id)
    assert raised.value.blocker.kind == "foreground_activity"
    assert (await _equipment_state(database, actor)) == (0, {})


@pytest.mark.asyncio
async def test_road_freezes_equipment_reconciles_legacy_hp_and_reconnects_from_snapshot(database):
    actor = 907122
    _, road = await _seed_road(database, actor=actor)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character_id = character.id
        character_class = character.character_class
        race = character.race
        level = character.level
        base_stats = resolve_combat_stats(
            character.character_class, character.level, character.race
        )
        character.max_hp = base_stats.hp
        character.hp = base_stats.hp / Decimal(2)
        item = EquipmentItem(
            character_id=character_id,
            source_key="equip:legacy-hp-before-stats",
            item_name="Legacy HP item",
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
        session.add(item)
        await session.flush()
        character.combat_configuration_version = 1
        session.add(
            CharacterEquipmentSlot(
                character_id=character_id,
                slot=EquipmentSlot.TORSO.value,
                equipment_item_id=item.id,
            )
        )
        item_id = item.id

    await road.travel(actor, ROAD)
    combat_view = await road.start_hunt(actor)
    assert combat_view is not None and combat_view.kind == "combat"
    combat = combat_view.combat
    assert combat.configuration_snapshot["combat_configuration_version"] == 1
    assert combat.configuration_snapshot["equipment"][0]["item_instance_id"] == str(item_id)
    expected_stats = resolve_combat_stats(
        character_class,
        level,
        race,
        EquipmentStatContribution(hp=Decimal(10)),
    )
    assert combat.fighters["player"].stats == expected_stats

    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character.max_hp == expected_stats.hp
        assert character.hp == Decimal(361)
        item = await session.scalar(select(EquipmentItem).where(EquipmentItem.id == item_id))
        item.payload = item.payload | {"core": {"HP": 999}}

    resumed = await road.resume(actor)
    assert resumed is not None and resumed.kind == "combat"
    assert resumed.combat.configuration_snapshot == combat.configuration_snapshot
    assert resumed.combat.fighters["player"].stats == combat.fighters["player"].stats


@pytest.mark.asyncio
async def test_pending_equipment_keeps_primary_key_identity_when_materialized(database):
    actor = 907109
    actor, road = await _seed_road(database, actor=actor)
    payload = materialize_equipment("pending-stable-equipment", "Raro", 1)
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        for index in range(60):
            session.add(
                EquipmentItem(
                    character_id=character.id,
                    source_key=f"stable-fill:{index}",
                    item_name=f"Fill {index}",
                    rarity="Comum",
                    slot="Principal",
                    item_level=1,
                    bound=False,
                    payload={},
                )
            )
        for index in range(20):
            session.add(
                PendingItem(
                    character_id=character.id,
                    source_key=f"stable-fill-pending:{index}",
                    kind="material",
                    payload={"material_id": f"material.stable-fill.{index}"},
                    quantity=1,
                )
            )
        await session.flush()
        await road._pending(
            session, character.id, "stable.pending.equipment", "equipment", payload
        )
        await session.commit()

    async with database[1]() as session:
        assert await session.scalar(
            select(EquipmentItem.id).where(EquipmentItem.source_key == "stable.pending.equipment")
        ) is None
        delivery = await session.scalar(
            select(BlockedDelivery).where(
                BlockedDelivery.source_key == "stable.pending.equipment"
            )
        )
        assert delivery is not None
        stable_id = UUID(delivery.payload["item_instance_id"])
        first_item = await session.scalar(
            select(EquipmentItem).where(EquipmentItem.source_key == "stable-fill:0")
        )
        assert first_item is not None
        await session.delete(first_item)
        await session.commit()

    assert await road.retry_blocked_deliveries(actor)
    async with database[1]() as session:
        instance = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.source_key == "stable.pending.equipment"
            )
        )
        assert instance is not None
        assert instance.id == stable_id
        assert instance.payload["item_instance_id"] == str(stable_id)


@pytest.mark.asyncio
async def test_postgres_concurrent_same_slot_mutations_serialize(database):
    actor = 907110
    character_id = await _seed_actor(database, actor)
    items = [
        await _add_item(database, character_id, f"equip:race-slot:{index}", "Torso")
        for index in range(2)
    ]
    service = EquipmentService(database[1], "ocaso")
    gate = asyncio.Event()

    async def equip(item_id):
        await gate.wait()
        return await service.equip_item(actor, item_id)

    tasks = [asyncio.create_task(equip(item_id)) for item_id in items]
    gate.set()
    results = await asyncio.gather(*tasks)
    assert all(result is not None and result.changed for result in results)
    assert {result.combat_configuration_version for result in results} == {1, 2}
    version, slots = await _equipment_state(database, actor)
    assert version == 2
    assert slots == {EquipmentSlot.TORSO.value: next(iter(slots.values()))}
    assert next(iter(slots.values())) in items


@pytest.mark.asyncio
async def test_postgres_concurrent_mythics_cannot_exceed_global_limit(database):
    actor = 907111
    character_id = await _seed_actor(database, actor)
    items = [
        await _add_item(
            database,
            character_id,
            f"equip:race-mythic:{index}",
            slot,
            rarity="Mítico",
        )
        for index, slot in enumerate(("Cabeça", "Principal"))
    ]
    service = EquipmentService(database[1], "ocaso")
    gate = asyncio.Event()

    async def equip(item_id):
        await gate.wait()
        try:
            return await service.equip_item(actor, item_id)
        except EquipmentMutationRejected as exc:
            return exc

    tasks = [asyncio.create_task(equip(item_id)) for item_id in items]
    gate.set()
    results = await asyncio.gather(*tasks)
    assert sum(not isinstance(result, EquipmentMutationRejected) for result in results) == 1
    rejected = next(
        result for result in results if isinstance(result, EquipmentMutationRejected)
    )
    assert rejected.code == EquipmentMutationCode.MYTHIC_LIMIT
    version, slots = await _equipment_state(database, actor)
    assert version == 1 and len(slots) == 1


@pytest.mark.asyncio
async def test_postgres_concurrent_two_handed_and_secondary_leave_valid_state(database):
    actor = 907112
    character_id = await _seed_actor(database, actor)
    secondary = await _add_item(database, character_id, "equip:race-secondary", "Secundária")
    two_handed = await _add_item(database, character_id, "equip:race-2h", "2H")
    service = EquipmentService(database[1], "ocaso")
    gate = asyncio.Event()

    async def equip(item_id):
        await gate.wait()
        try:
            return await service.equip_item(actor, item_id)
        except EquipmentMutationRejected as exc:
            return exc

    tasks = [asyncio.create_task(equip(item_id)) for item_id in (secondary, two_handed)]
    gate.set()
    results = await asyncio.gather(*tasks)
    assert any(not isinstance(result, EquipmentMutationRejected) for result in results)
    version, slots = await _equipment_state(database, actor)
    assert version in {1, 2}
    assert slots == {EquipmentSlot.PRINCIPAL.value: two_handed}


@pytest.mark.asyncio
async def test_postgres_activity_first_blocks_equipment_mutation(database):
    actor = 907113
    _, road = await _seed_road(database, actor=actor)
    async with database[1]() as session:
        character_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == actor)
        )
    item_id = await _add_item(database, character_id, "equip:activity-first", "Torso")
    await road.travel(actor, ROAD)
    await road.start_hunt(actor)
    with pytest.raises(CombatConfigurationLocked):
        await EquipmentService(database[1], "ocaso").equip_item(actor, item_id)
    assert (await _equipment_state(database, actor)) == (0, {})


@pytest.mark.asyncio
async def test_postgres_equipment_lock_first_serializes_road_activity_start(
    database, monkeypatch
):
    actor = 907114
    _, road = await _seed_road(database, actor=actor)
    async with database[1]() as session:
        character_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == actor)
        )
    item_id = await _add_item(database, character_id, "equip:mutation-first", "Torso")
    await road.travel(actor, ROAD)
    service = EquipmentService(database[1], "ocaso")
    acquired = asyncio.Event()
    release = asyncio.Event()
    original_guard = equipment_module.lock_for_combat_configuration_mutation

    async def pause_after_guard(session, locked_character_id):
        character = await original_guard(session, locked_character_id)
        acquired.set()
        await release.wait()
        return character

    monkeypatch.setattr(
        equipment_module,
        "lock_for_combat_configuration_mutation",
        pause_after_guard,
    )
    equipment_task = asyncio.create_task(service.equip_item(actor, item_id))
    activity_task = None
    try:
        await asyncio.wait_for(acquired.wait(), timeout=5)
        activity_task = asyncio.create_task(road.start_hunt(actor))
        await _wait_for_postgres_lock(database, "characters")
        release.set()
        result = await asyncio.wait_for(equipment_task, timeout=5)
        activity = await asyncio.wait_for(activity_task, timeout=5)
        assert result is not None and result.changed
        assert activity is not None and activity.kind == "combat"
        snapshot = activity.combat.configuration_snapshot
        assert snapshot["combat_configuration_version"] == 1
        assert snapshot["equipment"][0]["item_instance_id"] == str(item_id)
        assert activity.combat.fighters["player"].stats.hp == activity.max_hp
        version, slots = await _equipment_state(database, actor)
        assert version == 1 and slots == {EquipmentSlot.TORSO.value: item_id}
        with pytest.raises(CombatConfigurationLocked):
            await service.equip_item(actor, item_id)
    finally:
        release.set()
        for task in (equipment_task, activity_task):
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.dungeons import DungeonService
from asterion.application.road import CHARNECA, REGION
from asterion.domain.combat import CombatEvent, act
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    DungeonPityState,
    DungeonRun,
    DungeonRunEncounter,
    DungeonRunMember,
    GameActivity,
    Unlock,
    WorldState,
)


async def _seed(database, *, actor: int, level: int = 4, vigor: int = 100):
    _engine, sessions = database
    character_id = uuid4()
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Heroa",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=level,
                xp=0,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
                vigor=vigor,
                max_vigor=100,
                crowns=0,
            )
        )
        session.add(WorldState(character_id=character_id, region=REGION, location=CHARNECA))
        session.add(Unlock(character_id=character_id, unlock_id="dungeon.tdo.cripta_ocaso"))
    return character_id, sessions


@pytest.mark.asyncio
async def test_solo_run_reserves_vigor_snapshots_and_reconnects_to_same_encounter(database):
    actor = 774401
    _character_id, sessions = await _seed(database, actor=actor)
    service = DungeonService(sessions, "ocaso")

    view = await service.start_solo(actor, "stable")
    assert view is not None and view.kind == "ready"
    assert view.run_id is not None
    assert view.vigor == 75
    run_id = view.run_id

    async with sessions() as session:
        run = await session.get(DungeonRun, run_id)
        member = await session.scalar(
            select(DungeonRunMember).where(DungeonRunMember.run_id == run_id)
        )
        assert run.initial_group_size == 1
        assert member.position == 1
        assert member.vigor_reserved == 25
        assert "combat_configuration_version" in member.combat_configuration
        lobby_count = await session.scalar(
            select(__import__("sqlalchemy").func.count(GameActivity.id)).where(
                GameActivity.character_id == view.character_id,
                GameActivity.status == "active",
            )
        )
        assert lobby_count == 1

    first = await service.begin_encounter(actor, run_id, view.state_version)
    assert first is not None and first.kind == "combat"
    assert first.environment == "Vestíbulo Raspado"
    assert tuple(key for key in first.combat.fighters if key != "player") == ("enemy",)
    resumed = await service.resume(actor)
    assert resumed is not None and resumed.kind == "combat"
    assert resumed.run_id == first.run_id
    assert resumed.activity_id == first.activity_id
    assert resumed.combat.id == first.combat.id
    assert resumed.combat.fighters["enemy"].name == "Profanador Calcinado"


@pytest.mark.asyncio
async def test_entry_rejects_low_vigor_without_creating_run(database):
    actor = 774402
    character_id, sessions = await _seed(database, actor=actor, vigor=24)
    service = DungeonService(sessions, "ocaso")
    view = await service.start_solo(actor, "stable")
    assert view is not None and view.reason == "vigor"
    async with sessions() as session:
        assert await session.scalar(select(DungeonRun.id)) is None
        character = await session.get(Character, character_id)
        assert character.vigor == 24


@pytest.mark.asyncio
async def test_rupture_requires_level_60_and_fractured_first_clear(database):
    actor = 774407
    _character_id, sessions = await _seed(database, actor=actor, level=60)
    service = DungeonService(sessions, "ocaso")

    locked = await service.start_solo(actor, "rupture")
    assert locked is not None and locked.kind == "detail" and locked.reason == "gate"

    async with sessions.begin() as session:
        character_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == actor)
        )
        session.add_all(
            Unlock(character_id=character_id, unlock_id=unlock_id)
            for unlock_id in (
                "dungeon.tdo.cripta_ocaso.first_clear.stable",
                "dungeon.tdo.cripta_ocaso.first_clear.fractured",
            )
        )

    available = await service.start_solo(actor, "rupture")
    assert available is not None and available.kind == "ready"
    assert available.difficulty == "rupture"
    assert available.vigor == 50


@pytest.mark.asyncio
async def test_sem_nome_mastery_refreshes_after_stable_clear_when_late_evidence_arrives(
    database,
):
    actor = 774408
    character_id, sessions = await _seed(database, actor=actor, level=7)
    service = DungeonService(sessions, "ocaso")
    async with sessions.begin() as session:
        session.add(
            BestiaryEntry(
                character_id=character_id,
                creature_id="sem_nome",
                bkp=20,
                stage="studied",
            )
        )
        session.add_all(
            BestiaryEvidence(
                character_id=character_id,
                creature_id="sem_nome",
                evidence_id=evidence_id,
                category="behavior",
            )
            for evidence_id in (
                "first_victory",
                "phase:nobody_rest",
                "action:peso_sepulcro",
            )
        )

    combat = SimpleNamespace(
        fighters={"enemy": SimpleNamespace(id="enemy", stats=SimpleNamespace(hp=Decimal(1000)))},
        events=[
            CombatEvent(
                sequence=1,
                round=3,
                actor="enemy",
                action="maos_esquecidos",
            )
        ],
    )
    encounter = SimpleNamespace(encounter_ordinal=5, progress={})
    run = SimpleNamespace(difficulty="stable")
    character = SimpleNamespace(id=character_id)

    async with sessions.begin() as session:
        await service._record_combat_events(
            session, character, run, encounter, None, combat
        )
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "sem_nome",
            )
        )
        assert entry.stage == "studied"

    async with sessions.begin() as session:
        session.add(
            Unlock(
                character_id=character_id,
                unlock_id="dungeon.tdo.cripta_ocaso.first_clear.stable",
            )
        )
    async with sessions.begin() as session:
        await service._record_combat_events(
            session, character, run, encounter, None, combat
        )
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "sem_nome",
            )
        )
        assert entry.stage == "dominated"


@pytest.mark.asyncio
async def test_migration_schema_supports_four_members_and_persisted_pity(database):
    _engine, sessions = database
    run_id = uuid4()
    actors = (774403, 774404, 774405, 774406)
    character_ids = (uuid4(), uuid4(), uuid4(), uuid4())
    async with sessions.begin() as session:
        for position, (actor, character_id) in enumerate(
            zip(actors, character_ids, strict=True), start=1
        ):
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    id=character_id,
                    telegram_id=actor,
                    server_id="ocaso",
                    name=f"Hero{chr(96 + position)}",
                    race="remanescente",
                    character_class="sentinela",
                    stage="menu:ready",
                    ruleset_version="gdd-1.4.7-baseline-1.0",
                    level=4,
                    xp=0,
                    hp=Decimal("702"),
                    max_hp=Decimal("702"),
                    vigor=100,
                    max_vigor=100,
                    crowns=0,
                )
            )
        session.add(
            DungeonRun(
                id=run_id,
                dungeon_family_id="dungeon.tdo.cripta_ocaso",
                difficulty="stable",
                status="active",
                ruleset_version="dungeon-1.0",
                content_version="tdo-1.0.11",
                reference_level=6,
                initial_group_size=4,
                current_encounter_ordinal=6,
                state_version=0,
                seed="seed",
                has_brazier=False,
                brazier_activated=False,
                active_checkpoint_encounter=6,
                progress={},
                vigor_refunded=False,
            )
        )
        session.add(
            DungeonRunEncounter(
                run_id=run_id,
                encounter_ordinal=6,
                definition_id="tdo.future.gallery.encounter_6",
                status="pending",
                activity_id=None,
                attempt_count=0,
                progress={},
                reward_settled=False,
            )
        )
        for position, character_id in enumerate(character_ids, start=1):
            session.add(
                DungeonRunMember(
                    run_id=run_id,
                    character_id=character_id,
                    position=position,
                    status="active",
                    vigor_reserved=25,
                    consumable_uses=0,
                    combat_configuration={},
                    hp=702,
                    max_hp=702,
                    run_state={},
                    contribution={},
                )
            )
        session.add(
            DungeonPityState(
                character_id=character_ids[0], legendary_plus_points=23, mythic_points=199
            )
        )
    async with sessions() as session:
        members = (
            await session.scalars(select(DungeonRunMember).where(DungeonRunMember.run_id == run_id))
        ).all()
        pity = await session.get(DungeonPityState, character_ids[0])
        assert len(members) == 4
        assert pity.legendary_plus_points == 23
        assert pity.mythic_points == 199
        run = await session.get(DungeonRun, run_id)
        assert run.current_encounter_ordinal == 6
        assert run.active_checkpoint_encounter == 6


def test_tombstone_defense_aura_tracks_living_sources_and_snapshot_roundtrips():
    from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
    from asterion.domain.tdo_crypt import create_crypt_combat
    from asterion.infrastructure.db.combat_codec import decode, encode

    combat_id = uuid4()
    base = create_crypt_combat(
        combat_id,
        name="Heroa",
        character_class="sentinela",
        race="remanescente",
        hp=Decimal("3000"),
        level=6,
        difficulty="stable",
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=4,
        run_seed="crypt-aura-test",
    )
    assert len(base.stat_auras) == 1

    damage_by_active_sources = []
    for active_sources in (3, 2, 1, 0):
        state = decode(encode(base), base.id, base.ruleset, base.version)
        for index in range(active_sources + 1, 4):
            state.fighters[f"tomb_{index}"].hp = Decimal(0)
        updated = act(state, "attack", target_id="enemy_1")
        attack_event = next(
            event
            for event in updated.events
            if event.actor == "player" and event.action == "attack"
        )
        damage_by_active_sources.append(attack_event.effective_damage)

    assert damage_by_active_sources == sorted(damage_by_active_sources)
    assert len(set(damage_by_active_sources)) == 4

    legacy = encode(base)
    legacy.pop("stat_auras")
    decoded_legacy = decode(legacy, base.id, base.ruleset, base.version)
    assert decoded_legacy.stat_auras == ()

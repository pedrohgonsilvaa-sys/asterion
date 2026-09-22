import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from asterion.application.prologue import PrologueService
from asterion.domain.creation import PROLOGUE
from asterion.domain.prologue import (
    CONTENT_ID,
    LEVEL_TWO_XP,
    POST_COMBAT_STAGE,
    PROFILE,
    REWARD_XP,
    RULESET,
)
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CombatRecord,
    Encounter,
    GameActivity,
    RewardGrant,
)


@pytest.fixture
def prologue(database):
    return PrologueService(database[1], "ocaso", PROFILE)


async def character(database, actor=1, cls="sentinela", race="remanescente"):
    from asterion.domain.combat_math import class_stats, racial_stats

    stats = racial_stats(class_stats(cls, 1), race)
    async with database[1].begin() as session:
        session.add(Account(telegram_id=actor))
        row = Character(
            telegram_id=actor,
            server_id="ocaso",
            name=f"Hero{actor}" if actor > 9 else f"Heroaa{actor}",
            race=race,
            character_class=cls,
            stage=PROLOGUE,
            ruleset_version=RULESET,
            level=1,
            xp=0,
            hp=stats.hp,
            max_hp=stats.hp,
        )
        # Names are ASCII letters only at DB level.
        row.name = "Hero" + chr(96 + actor)
        session.add(row)
    return row


async def win(service, view):
    for action in ("attack", "defend", "art"):
        view = await service.action(
            1,
            view.activity_id,
            view.combat.version,
            action,
        )
    for _ in range(30):
        if view.combat.result:
            break
        action = (
            "art"
            if "art"
            in __import__("asterion.domain.combat", fromlist=["allowed_actions"]).allowed_actions(
                view.combat
            )
            else "attack"
        )
        view = await service.action(1, view.activity_id, view.combat.version, action)
    assert view.combat.result == "victory"
    return view


async def test_enter_creates_stable_activity_encounter_and_combat(prologue, database):
    await character(database)
    view = await prologue.enter(1)
    assert view.stage == "cinzas_na_estrada:first_combat"
    assert view.combat.ruleset == RULESET
    assert view.combat.fighters["enemy"].stats.values() == (244, 50, 45, 56)
    assert view.combat.fighters["enemy"].hp == 244
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(GameActivity)) == 1
        assert await session.scalar(select(func.count()).select_from(Encounter)) == 1
        assert await session.scalar(select(func.count()).select_from(CombatRecord)) == 1
        activity = await session.scalar(select(GameActivity))
        assert activity.content_id == CONTENT_ID and activity.status == "active"


async def test_new_tutorial_records_dog_knowledge_without_observation_xp(prologue, database):
    await character(database)
    await prologue.enter(1)
    async with database[1]() as session:
        entry = await session.scalar(
            select(BestiaryEntry).where(BestiaryEntry.creature_id == "dog_cinereo")
        )
        evidence = (
            await session.scalars(
                select(BestiaryEvidence).where(BestiaryEvidence.creature_id == "dog_cinereo")
            )
        ).all()
        stored = await session.scalar(select(Character))
        assert entry is not None and (entry.bkp, entry.stage) == (7, "observed")
        assert {row.evidence_id for row in evidence} == {"first_observation", "first_combat"}
        assert stored.xp == 0


async def test_repeated_and_concurrent_enter_are_idempotent(prologue, database):
    await character(database)
    devices = [PrologueService(database[1], "ocaso", PROFILE) for _ in range(8)]
    views = await asyncio.gather(*(service.enter(1) for service in devices))
    assert len({view.activity_id for view in views}) == 1
    assert len({view.encounter_id for view in views}) == 1
    assert len({view.combat.id for view in views}) == 1
    assert await prologue.enter(1) == views[0]
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(GameActivity)) == 1


async def test_two_actions_same_version_have_one_winner(prologue, database):
    await character(database)
    initial = await prologue.enter(1)
    devices = [PrologueService(database[1], "ocaso", PROFILE) for _ in range(2)]
    results = await asyncio.gather(
        *(
            service.action(1, initial.activity_id, initial.combat.version, "attack")
            for service in devices
        )
    )
    current = await prologue.resume(1)
    assert results == [current, current]
    assert current.combat.version == initial.combat.version + 1
    assert [event.action for event in current.combat.events] == ["attack", "bite"]


async def test_duplicate_old_forged_and_other_actor_callbacks_are_safe(prologue, database):
    await character(database, 1)
    await character(database, 2)
    initial = await prologue.enter(1)
    changed = await prologue.action(1, initial.activity_id, initial.combat.version, "defend")
    assert (
        await prologue.action(1, initial.activity_id, initial.combat.version, "defend") == changed
    )
    assert (
        await prologue.action(1, changed.activity_id, changed.combat.version, "reward") == changed
    )
    other_before = await prologue.enter(2)
    assert (
        await prologue.action(2, changed.activity_id, changed.combat.version, "attack")
        == other_before
    )
    assert await prologue.resume(1) == changed


async def test_restart_at_every_tutorial_stage_restores_exact_snapshot(prologue, database):
    await character(database)
    state = await prologue.enter(1)
    for action, stage in (("attack", "defend"), ("defend", "art"), ("art", "normal")):
        restarted = PrologueService(database[1], "ocaso", PROFILE)
        assert await restarted.resume(1) == state
        state = await restarted.action(1, state.activity_id, state.combat.version, action)
        assert state.combat.tutorial_stage == stage
    assert await PrologueService(database[1], "ocaso", PROFILE).resume(1) == state


async def test_victory_grants_exactly_once_and_persists_hp(prologue, database):
    await character(database)
    won = await win(prologue, await prologue.enter(1))
    remaining_hp = won.combat.fighters["player"].hp
    assert won.stage == POST_COMBAT_STAGE and won.xp == REWARD_XP
    attempts = await asyncio.gather(
        *(
            PrologueService(database[1], "ocaso", PROFILE).action(
                1,
                won.activity_id,
                won.combat.version - 1,
                "attack",
            )
            for _ in range(8)
        )
    )
    assert all(view == won for view in attempts)
    assert await prologue.enter(1) == won
    async with database[1]() as session:
        stored = await session.scalar(select(Character))
        activity = await session.scalar(select(GameActivity))
        grant = await session.scalar(select(RewardGrant))
        assert stored.xp == 320 < LEVEL_TWO_XP and stored.level == 1
        assert stored.hp == remaining_hp and stored.max_hp > stored.hp
        assert stored.stage == POST_COMBAT_STAGE
        assert activity.status == "completed"
        assert grant.xp == 320 and grant.character_id == stored.id
        assert await session.scalar(select(func.count()).select_from(RewardGrant)) == 1
        # Schema contains no loot, currency, material, vigor or bestiary bonus grant.
        assert set(RewardGrant.__table__.columns.keys()) == {
            "game_activity_id",
            "character_id",
            "xp",
            "ruleset_version",
            "created_at",
        }


async def test_concurrent_reward_attempt_has_single_grant(prologue, database):
    await character(database)
    view = await prologue.enter(1)
    # Put a legal normal-turn snapshot one hit from victory, then persist it.
    for action in ("attack", "defend", "art"):
        view = await prologue.action(1, view.activity_id, view.combat.version, action)
    async with database[1].begin() as session:
        activity = await session.get(GameActivity, view.activity_id)
        encounter = await session.scalar(
            select(Encounter).where(
                Encounter.game_activity_id == view.activity_id,
            )
        )
        record = await session.scalar(
            select(CombatRecord).where(
                CombatRecord.encounter_id == encounter.id,
            )
        )
        from asterion.infrastructure.db.combat_codec import decode, encode

        state = decode(record.snapshot, record.id, activity.ruleset_version, activity.state_version)
        state.fighters["enemy"].hp = Decimal(1)
        record.snapshot = encode(state)
    services = [PrologueService(database[1], "ocaso", PROFILE) for _ in range(8)]
    results = await asyncio.gather(
        *(
            service.action(1, view.activity_id, view.combat.version, "attack")
            for service in services
        )
    )
    assert all(result.xp == 320 and result.stage == POST_COMBAT_STAGE for result in results)
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(RewardGrant)) == 1
        assert (await session.scalar(select(Character))).xp == 320


async def test_incompatible_foreground_blocks_first_combat(prologue, database):
    row = await character(database)
    async with database[1].begin() as session:
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=row.id,
                content_id="different_foreground",
                status="active",
                state_version=0,
                ruleset_version=RULESET,
            )
        )
    assert await prologue.enter(1) is None


async def test_wrong_stage_or_ruleset_cannot_instantiate(prologue, database):
    row = await character(database)
    async with database[1].begin() as session:
        stored = await session.get(Character, row.id)
        stored.stage = POST_COMBAT_STAGE
    assert await prologue.enter(1) is None
    async with database[1].begin() as session:
        stored = await session.get(Character, row.id)
        stored.stage = PROLOGUE
        stored.ruleset_version = "gdd-1.4.1-baseline-1.0"
    with pytest.raises(ValueError, match="migrated"):
        await prologue.enter(1)


async def test_database_rejects_two_active_foregrounds(database):
    row = await character(database)
    with pytest.raises(IntegrityError):
        async with database[1].begin() as session:
            session.add_all(
                [
                    GameActivity(
                        id=uuid4(),
                        character_id=row.id,
                        content_id="first",
                        status="active",
                        state_version=0,
                        ruleset_version=RULESET,
                    ),
                    GameActivity(
                        id=uuid4(),
                        character_id=row.id,
                        content_id="second",
                        status="active",
                        state_version=0,
                        ruleset_version=RULESET,
                    ),
                ]
            )


async def test_same_prologue_occurrence_cannot_be_created_twice_after_completion(database):
    row = await character(database)
    with pytest.raises(IntegrityError):
        async with database[1].begin() as session:
            session.add_all(
                [
                    GameActivity(
                        id=uuid4(),
                        character_id=row.id,
                        content_id=CONTENT_ID,
                        status="completed",
                        state_version=1,
                        ruleset_version=RULESET,
                    ),
                    GameActivity(
                        id=uuid4(),
                        character_id=row.id,
                        content_id=CONTENT_ID,
                        status="completed",
                        state_version=1,
                        ruleset_version=RULESET,
                    ),
                ]
            )


def test_telegram_ids_remain_bigint_and_foreign_keys_are_explicit():
    from sqlalchemy import BigInteger

    assert isinstance(Account.__table__.c.telegram_id.type, BigInteger)
    assert isinstance(Character.__table__.c.telegram_id.type, BigInteger)
    assert Character.__table__.c.telegram_id.foreign_keys
    assert GameActivity.__table__.c.character_id.foreign_keys
    assert Encounter.__table__.c.game_activity_id.foreign_keys
    assert CombatRecord.__table__.c.encounter_id.foreign_keys

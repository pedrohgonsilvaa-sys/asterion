# ruff: noqa: E501,I001,F401
from copy import deepcopy
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.p7 import (
    COURO_MUSGOSO,
    FERRO_ENREDADO,
    GARGANTA_BRAZIER,
    GARGANTA,
    GARGANTA_EXPLORE_UNLOCK,
    GARGANTA_HUNT_UNLOCK,
    GARGANTA_LOCATION_ID,
    P7_FEAT,
    P7_ID,
    P7_REWARD_SOURCE,
    P7_ROUTES_CODEX,
    P7Service,
    REGION,
    VIGILIA,
    VIGILIA_BRAZIER,
    VIGILIA_LOCATION_ID,
)
from asterion.bot.p6_ui import render_p6
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    Brazier,
    Character,
    CodexEntry,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_s6_p6_integration import _seed_final_campaign


def _terminal(result: str):
    def finish(combat, action, **kwargs):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = result
        if result == "defeat":
            player = next(
                fighter
                for fighter in updated.fighters.values()
                if (fighter.side or ("player" if fighter.id == "player" else "enemy")) == "player"
            )
            player.hp = Decimal(0)
        return updated

    return finish


async def _seed_p7_ready(database, actor: int, *, level: int = 11):
    character_id, sessions = await _seed_final_campaign(database, actor, level=level)
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id="P6",
                title="A Âncora do Poente",
                status="completed",
                step=10,
                content_version="tdo-1.0.15",
                progress={"completed": True},
            )
        )
    return character_id, sessions


@pytest.mark.asyncio
async def test_p7_requires_p6_and_level_11(database):
    actor = 999701
    _, sessions = await _seed_final_campaign(database, actor, level=11)
    service = P7Service(sessions, "ocaso")
    view = await service.enter_vales(actor)
    assert view is not None
    assert view.kind == "unavailable"

    actor += 1
    _, sessions = await _seed_p7_ready(database, actor, level=10)
    service = P7Service(sessions, "ocaso")
    view = await service.enter_vales(actor)
    assert view is not None
    assert view.kind == "unavailable"


@pytest.mark.asyncio
async def test_p7_full_solo_flow_reward_and_unlocks_are_idempotent(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 999703
    character_id, sessions = await _seed_p7_ready(database, actor)
    service = P7Service(sessions, "ocaso")

    entered = await service.enter_vales(actor)
    assert entered is not None
    assert entered.status == "active"
    assert entered.step == 2
    assert entered.kind == "road_points"
    assert entered.location == GARGANTA

    async with sessions() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        assert (world.region, world.location) == (REGION, GARGANTA)
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == GARGANTA_LOCATION_ID,
            )
        ) is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == GARGANTA_BRAZIER,
            )
        ) is not None

    resumed_entry = await service.enter_vales(actor)
    assert resumed_entry is not None and resumed_entry.status == "active"
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(Brazier.id)).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == GARGANTA_BRAZIER,
            )
        ) == 1

    first = await service.examine_road_point(actor, entered.state_version, "a")
    assert first is not None and first.step == 2
    stale = await service.examine_road_point(actor, entered.state_version, "a")
    assert stale is not None and stale.step == 2
    second = await service.examine_road_point(actor, first.state_version, "b")
    assert second is not None and second.step == 3

    passage = await service.inspect_recent_passage(actor, second.state_version)
    assert passage is not None and passage.step == 4 and passage.kind == "start_fauna"

    combat = await service.start_solo_combat(actor, passage.state_version)
    assert combat is not None and combat.kind == "combat" and combat.combat is not None
    assert combat.activity_id is not None
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(BestiaryEntry.id)).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "p7_fauna_regional",
            )
        ) == 0
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(RewardEvent.character_id == character_id)
        ) == 0

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    won = await service.action_combat(
        actor,
        combat.activity_id,
        combat.combat.version,
        "attack",
    )
    assert won is not None and won.step == 5 and won.kind == "worked_stone"

    stone = await service.inspect_worked_stone(actor, won.state_version)
    assert stone is not None and stone.step == 6 and stone.kind == "proceed_vigilia"
    assert stone.progress["worked_stone"] is True

    vigilia = await service.proceed_to_vigilia(actor, stone.state_version)
    assert vigilia is not None and vigilia.step == 7 and vigilia.location == VIGILIA
    assert vigilia.kind == "activate_brazier"

    brazier = await service.activate_brazier(actor, vigilia.state_version)
    assert brazier is not None and brazier.kind == "report_dara"

    async with sessions() as session:
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VIGILIA_BRAZIER,
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == VIGILIA_LOCATION_ID,
            )
        ) is not None

    before = None
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        before = (character.xp, character.crowns)

    completed = await service.report_dara(actor, brazier.state_version)
    assert completed is not None and completed.status == "completed" and completed.kind == "completed"

    repeated = await service.report_dara(actor, completed.state_version)
    assert repeated is not None and repeated.status == "completed"

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert before is not None
        assert character.xp >= before[0] + 8750
        assert character.crowns == before[1] + 270
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P7_REWARD_SOURCE,
            )
        ) == 1
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).join(RewardEvent).where(
                        RewardEvent.character_id == character_id,
                        RewardEvent.source_id == P7_REWARD_SOURCE,
                    )
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} >= {
            ("xp", None, 8750),
            ("crowns", None, 270),
            ("material", FERRO_ENREDADO, 1),
            ("material", COURO_MUSGOSO, 1),
        }
        for unlock_id in (GARGANTA_HUNT_UNLOCK, GARGANTA_EXPLORE_UNLOCK):
            assert await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == unlock_id,
                )
            ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == P7_FEAT,
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == P7_ROUTES_CODEX,
            )
        ) is not None
        assert await session.scalar(
            select(func.count(BestiaryEntry.id)).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "p7_fauna_regional",
            )
        ) == 0


@pytest.mark.asyncio
async def test_p7_defeat_keeps_checkpoint_and_retry(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 999704
    _, sessions = await _seed_p7_ready(database, actor)
    service = P7Service(sessions, "ocaso")
    view = await service.enter_vales(actor)
    view = await service.examine_road_point(actor, view.state_version, "a")
    view = await service.examine_road_point(actor, view.state_version, "b")
    view = await service.inspect_recent_passage(actor, view.state_version)
    combat = await service.start_solo_combat(actor, view.state_version)
    assert combat is not None and combat.combat is not None and combat.activity_id is not None

    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await service.action_combat(
        actor,
        combat.activity_id,
        combat.combat.version,
        "attack",
    )
    assert defeated is not None
    assert defeated.step == 4
    assert defeated.kind == "retry"
    assert defeated.progress["awaiting_retry"] is True

    retried = await service.retry(actor, defeated.state_version)
    assert retried is not None and retried.kind == "combat"
    assert retried.activity_id != combat.activity_id


def test_p6_completion_exposes_vales_entry_only_at_level_11():
    from uuid import uuid4
    from asterion.application.p6 import P6View

    base = dict(
        character_id=uuid4(),
        kind="completed",
        status="completed",
        step=10,
        state_version=3,
        progress={"reward_choice": "arma"},
        location="Refúgio do Ocaso",
        available=True,
        xp=0,
    )
    low = render_p6(P6View(level=10, **base))
    high = render_p6(P6View(level=11, **base))
    low_callbacks = [button.callback_data for row in low.keyboard.inline_keyboard for button in row]
    high_callbacks = [button.callback_data for row in high.keyboard.inline_keyboard for button in row]
    assert "p7:enter" not in low_callbacks
    assert "p7:enter" in high_callbacks

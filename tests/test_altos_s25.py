from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.road import ALTOS_ESCARPA_LABEL
from asterion.application.s25 import (
    S25_CODEX_ENTRY,
    S25_CODEX_FRAGMENT,
    S25_REWARD_SOURCE,
    S25Service,
)
from asterion.bot.s25_ui import render_s25
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CodexFragment,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_road_integration import _seed_road

ALTOS_REGION = "Altos Cinéreos"
S25_ACTIONS = (
    "inspect_bridge",
    "locate_seal",
    "compare_orders",
    "verify_structure",
    "return_to_doren",
    "record_codex",
)


async def _seed_s25(
    database,
    actor: int,
    *,
    level=42,
    p25_status="completed",
    location=ALTOS_ESCARPA_LABEL,
):
    actor, _road = await _seed_road(database, actor=actor)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = ALTOS_REGION
        world.location = location
        if p25_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id="P25",
                    title="O Peso Antigo",
                    status=p25_status,
                    step=9,
                    content_version="altos-1.0.1",
                    progress={"completed": p25_status == "completed"},
                )
            )
    return actor, sessions, S25Service(sessions, "ocaso")


async def _complete_s25(service, actor, view):
    for action in S25_ACTIONS:
        objective = await service.objective(actor)
        assert objective is not None and objective.step == view.step
        view = await service.advance(actor, objective.state_version, action)
        assert view is not None
    return view


@pytest.mark.asyncio
async def test_s25_gate_requires_p25_level_42_and_escarpa(database):
    actor, _sessions, service = await _seed_s25(
        database, 778250, level=42, p25_status="active"
    )
    locked = await service.offer(actor)
    assert locked is not None and not locked.available

    actor, _sessions, service = await _seed_s25(
        database, 778251, level=41, p25_status="completed"
    )
    locked = await service.offer(actor)
    assert locked is not None and not locked.available

    actor, _sessions, service = await _seed_s25(
        database,
        778252,
        level=42,
        p25_status="completed",
        location="Abrigo do Peso",
    )
    assert await service.offer(actor) is None

    actor, _sessions, service = await _seed_s25(database, 778253)
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    assert offer.status == "unaccepted"


@pytest.mark.asyncio
async def test_s25_six_steps_codex_reward_and_bridge_gates_are_idempotent(database):
    actor, sessions, service = await _seed_s25(database, 778254)
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1

    before_version = accepted.state_version
    first = await service.advance(actor, before_version, S25_ACTIONS[0])
    assert first is not None and first.step == 2
    duplicate = await service.advance(actor, before_version, S25_ACTIONS[0])
    assert duplicate is not None and duplicate.state_version == first.state_version
    assert duplicate.progress == first.progress

    view = first
    for action in S25_ACTIONS[1:]:
        view = await service.advance(actor, view.state_version, action)
        assert view is not None
    assert view.status == "completed"
    assert view.progress["completed"] is True
    assert view.progress["codex_recorded"] is True

    stale_callback = await service.advance(actor, before_version, S25_ACTIONS[0])
    assert stale_callback is not None and stale_callback.status == "completed"
    assert stale_callback.state_version == view.state_version

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(CodexEntry).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == S25_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment).where(
                CodexFragment.character_id == character.id,
                CodexFragment.fragment_id == S25_CODEX_FRAGMENT,
            )
        ) is not None
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S25_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )
        ).all()
        assert {(item.kind, item.quantity) for item in components} == {
            ("xp", 22_280),
            ("crowns", 370),
        }
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id.in_(
                    (
                        "unlock.location.altos.pontes_fuligem",
                        "unlock.hunt.altos.pontes",
                        "unlock.explore.altos.pontes",
                        "unlock.round.altos.pontes",
                    )
                ),
            )
        ) is None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == "location.altos.pontes_fuligem",
            )
        ) is None


@pytest.mark.asyncio
async def test_s25_abandon_requires_no_foreground_and_reaccept_preserves_codex(database):
    actor, sessions, service = await _seed_s25(database, 778255)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        session.add_all(
            (
                CodexEntry(character_id=character.id, entry_id=S25_CODEX_ENTRY),
                CodexFragment(
                    character_id=character.id,
                    entry_id=S25_CODEX_ENTRY,
                    fragment_id=S25_CODEX_ENTRY,
                ),
            )
        )

    accepted = await service.accept(actor)
    assert accepted is not None and accepted.status == "active"
    view = await service.advance(actor, accepted.state_version, S25_ACTIONS[0])
    assert view is not None and view.step == 2
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=character.id,
                content_id="s25.foreground_test",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    blocked = await service.abandon(actor, view.state_version)
    assert blocked is not None and blocked.status == "active" and blocked.step == 2

    async with sessions.begin() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.content_id == "s25.foreground_test")
        )
        assert activity is not None
        activity.status = "completed"
    abandoned = await service.abandon(actor, view.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    assert abandoned.step == 1 and abandoned.progress == {}

    offer = await service.offer(actor)
    assert offer is not None and offer.reacceptable
    restarted = await service.accept(actor, offer.state_version, reaccept=True)
    assert restarted is not None and restarted.status == "active"
    assert restarted.step == 1 and restarted.progress == {}

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(CodexEntry).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == S25_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment).where(
                CodexFragment.character_id == character.id,
                CodexFragment.fragment_id == S25_CODEX_ENTRY,
            )
        ) is not None


@pytest.mark.asyncio
async def test_s25_objective_ui_exposes_only_current_step_and_no_bridge_unlock(database):
    actor, _sessions, service = await _seed_s25(database, 778256)
    accepted = await service.accept(actor)
    assert accepted is not None
    objective = await service.objective(actor)
    assert objective is not None and objective.kind == "objective"
    screen = render_s25(objective)
    callbacks = {
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    }
    assert f"s25:action:{objective.state_version}:inspect_bridge" in callbacks
    assert all("pontes" not in callback for callback in callbacks)

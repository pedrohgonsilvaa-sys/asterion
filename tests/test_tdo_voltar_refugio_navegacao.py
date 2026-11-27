"""Voltar ao Refúgio nas Terras do Ocaso é só navegação de UI (sem teleporte).

Regra: docs/SOURCE_AUTHORITY.md (2026-11-19, item 3). O botão mostra a tela do
Refúgio e não altera Local, região, exploração, Missão, recompensas nem desbloqueios.
"""

from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage
from sqlalchemy import select

from asterion.application.p1 import P1Service
from asterion.application.road import CHARNECA, REFUGE, ROAD
from asterion.application.world import WorldService
from asterion.bot.world_handlers import world_router
from asterion.infrastructure.db.models import (
    Achievement,
    Character,
    GameActivity,
    LocationDiscovery,
    Quest,
    Unlock,
    WorldState,
)
from tests.test_character_surfaces_telegram import _last_screen
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road

TDO_REGION = "Terras do Ocaso"
RETURN_CALLBACKS = ["menu:back", "world:adventure"]


async def _snapshot(sessions, actor):
    """Estado que o retorno não pode alterar: posição, progresso, descobertas e desbloqueios."""
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        quests = (
            await session.scalars(
                select(Quest).where(Quest.character_id == character.id).order_by(Quest.quest_id)
            )
        ).all()
        discoveries = (
            await session.scalars(
                select(LocationDiscovery.location_id).where(
                    LocationDiscovery.character_id == character.id
                )
            )
        ).all()
        unlocks = (
            await session.scalars(
                select(Unlock.unlock_id).where(Unlock.character_id == character.id)
            )
        ).all()
        activities = (
            await session.scalars(
                select(GameActivity.content_id).where(
                    GameActivity.character_id == character.id,
                    GameActivity.status == "active",
                )
            )
        ).all()
        return {
            "region": world.region,
            "location": world.location,
            "quests": [
                (q.quest_id, q.status, q.step, dict(q.progress or {}), q.state_version)
                for q in quests
            ],
            "discoveries": sorted(discoveries),
            "unlocks": sorted(unlocks),
            "activities": sorted(activities),
        }


def _dispatcher(sessions, road):
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"),
            {},
            p1=P1Service(sessions, "ocaso"),
            road=road,
        )
    )
    return dispatcher


async def _press(sessions, road, actor, callback_data):
    dispatcher = _dispatcher(sessions, road)
    bot = Bot("123456:local-test-token")

    async def telegram_response(_bot, method, **_kwargs):
        if isinstance(method, EditMessageText):
            return TelegramMessage(
                message_id=method.message_id,
                date=1,
                chat=Chat(id=actor, type="private"),
                from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                text=method.text,
            )
        return True

    bot.session.make_request = AsyncMock(side_effect=telegram_response)
    await dispatcher.feed_raw_update(bot, callback_update(callback_data, actor=actor))
    await bot.session.close()
    return _last_screen(bot)


async def _set_location(sessions, actor, location):
    """Personagem nas Terras do Ocaso com P1 concluído (estado normal após o Prólogo)."""
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        p1 = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "P1")
        )
        p1.status = "completed"
        if (
            await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character.id,
                    Achievement.achievement_id == "feat.tdo.cinzas_na_estrada",
                )
            )
            is None
        ):
            session.add(
                Achievement(
                    character_id=character.id, achievement_id="feat.tdo.cinzas_na_estrada"
                )
            )
        world.region = TDO_REGION
        world.location = location


@pytest.mark.asyncio
@pytest.mark.parametrize("callback_data", RETURN_CALLBACKS)
async def test_return_from_discovered_local_shows_refuge_without_moving(database, callback_data):
    actor, road = await _seed_road(database, actor=893201)
    sessions = database[1]
    await _set_location(sessions, actor, CHARNECA)
    before = await _snapshot(sessions, actor)
    assert before["location"] == CHARNECA

    screen = await _press(sessions, road, actor, callback_data)

    assert "Terras do Ocaso" in screen.text
    assert await _snapshot(sessions, actor) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("callback_data", RETURN_CALLBACKS)
async def test_return_during_active_p1_on_road_shows_refuge_without_moving(
    database, callback_data
):
    actor, road = await _seed_road(database, actor=893202)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        quest = await session.scalar(select(Quest).where(Quest.character_id == character.id))
        quest.status = "active"
        quest.step = 1
        session.add(
            Achievement(character_id=character.id, achievement_id="feat.tdo.cinzas_na_estrada")
        )
    await _set_location(sessions, actor, ROAD)
    before = await _snapshot(sessions, actor)

    screen = await _press(sessions, road, actor, callback_data)

    assert "Terras do Ocaso" in screen.text
    after = await _snapshot(sessions, actor)
    assert after == before
    assert after["location"] == ROAD


@pytest.mark.asyncio
async def test_return_from_local_with_foreground_activity_does_not_move_character(database):
    # Atividade em primeiro plano: o retorno não move o personagem nem altera estado.
    # (O fallback de menu pode renderizar a tela, mas não altera Local.)
    actor, road = await _seed_road(database, actor=893203)
    sessions = database[1]
    await _set_location(sessions, actor, CHARNECA)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add(
            GameActivity(
                character_id=character.id,
                content_id="test_voltar_refugio_foreground",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    before = await _snapshot(sessions, actor)

    await _press(sessions, road, actor, "menu:back")

    after = await _snapshot(sessions, actor)
    assert after == before
    assert after["location"] == CHARNECA


@pytest.mark.asyncio
async def test_refuge_return_when_already_at_refuge_keeps_state(database):
    actor, road = await _seed_road(database, actor=893204)
    sessions = database[1]
    await _set_location(sessions, actor, REFUGE)
    before = await _snapshot(sessions, actor)

    screen = await _press(sessions, road, actor, "menu:back")

    assert "Terras do Ocaso" in screen.text
    assert await _snapshot(sessions, actor) == before

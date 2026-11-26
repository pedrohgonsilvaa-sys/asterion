"""Terras do Ocaso: o Refúgio do Ocaso substitui o Menu Principal.

Regra: Visual/UI v1.6.2, seção 66.1 item 1 (docs/SOURCE_AUTHORITY.md, 2026-11-16).
Dentro da Região, a tela que antes abria o Menu Principal é o Refúgio. Fora dela, o Menu
Principal permanece. A apresentação é só navegação de UI: não teleporta, não altera Local,
exploração, progresso, descobertas ou desbloqueios.
"""

from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage
from sqlalchemy import select

from asterion.application.p1 import P1Service
from asterion.application.road import CHARNECA, REFUGE
from asterion.application.world import WorldService
from asterion.bot.world_handlers import world_router
from asterion.infrastructure.db.models import (
    Achievement,
    Character,
    GameActivity,
    Quest,
    WorldState,
)
from tests.test_character_surfaces_telegram import _last_screen
from tests.test_creation_ui import message_update
from tests.test_road_integration import _seed_road
from tests.test_tdo_voltar_refugio_navegacao import _snapshot

TDO_REGION = "Terras do Ocaso"
OUTSIDE_REGION = "Vales dos Enforcados"
# Marcadores de tela: o Refúgio tem o botão de Explorar do hub; o Menu Principal não tem.
REFUGE_MARKER = "adv:hub"  # ⚔️ Aventura só existe no Menu do Refúgio (2026-11-26)
MAIN_MENU_MARKER = "road:explore:start"


async def _set_state(sessions, actor, *, region, location):
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        p1 = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "P1")
        )
        p1.status = "completed"
        session.add(
            Achievement(character_id=character.id, achievement_id="feat.tdo.cinzas_na_estrada")
        )
        world.region = region
        world.location = location


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


async def _feed(sessions, road, actor, update):
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
    await dispatcher.feed_raw_update(bot, update)
    await bot.session.close()
    return _last_screen(bot)


def _callbacks(screen):
    return [
        button.callback_data
        for row in screen.reply_markup.inline_keyboard
        for button in row
        if button.callback_data
    ]


async def _menu(sessions, road, actor):
    return await _feed(sessions, road, actor, message_update("/menu", actor=actor))


@pytest.mark.asyncio
async def test_menu_inside_tdo_at_refuge_shows_refuge(database):
    actor, road = await _seed_road(database, actor=893301)
    sessions = database[1]
    await _set_state(sessions, actor, region=TDO_REGION, location=REFUGE)
    before = await _snapshot(sessions, actor)

    screen = await _menu(sessions, road, actor)

    assert REFUGE_MARKER in _callbacks(screen)
    assert MAIN_MENU_MARKER not in _callbacks(screen)
    assert await _snapshot(sessions, actor) == before


@pytest.mark.asyncio
async def test_menu_inside_tdo_without_road_view_shows_refuge_without_moving(database):
    # Sem visão de Local (caminho em que o /menu cai no Menu Principal), em TDO fora do
    # Refúgio: a tela é o Refúgio e o personagem não se move.
    actor, _road = await _seed_road(database, actor=893304)
    sessions = database[1]
    await _set_state(sessions, actor, region=TDO_REGION, location=CHARNECA)
    before = await _snapshot(sessions, actor)

    screen = await _menu(sessions, None, actor)

    assert REFUGE_MARKER in _callbacks(screen)
    assert MAIN_MENU_MARKER not in _callbacks(screen)
    assert await _snapshot(sessions, actor) == before


@pytest.mark.asyncio
async def test_menu_outside_tdo_keeps_main_menu(database):
    actor, road = await _seed_road(database, actor=893302)
    sessions = database[1]
    await _set_state(sessions, actor, region=OUTSIDE_REGION, location=CHARNECA)
    before = await _snapshot(sessions, actor)

    screen = await _menu(sessions, road, actor)

    assert REFUGE_MARKER not in _callbacks(screen)
    assert await _snapshot(sessions, actor) == before


@pytest.mark.asyncio
async def test_menu_inside_tdo_with_foreground_activity_keeps_existing_rule(database):
    # Atividade em primeiro plano: a regra existente vale; o Refúgio não substitui a atividade
    # e o personagem não se move.
    actor, road = await _seed_road(database, actor=893303)
    sessions = database[1]
    await _set_state(sessions, actor, region=TDO_REGION, location=CHARNECA)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add(
            GameActivity(
                character_id=character.id,
                content_id="test_menu_refuge_foreground",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    before = await _snapshot(sessions, actor)

    await _menu(sessions, road, actor)

    assert await _snapshot(sessions, actor) == before

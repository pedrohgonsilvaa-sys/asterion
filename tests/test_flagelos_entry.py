"""Acesso do jogador ao hub de O Despertar dos Flagelos pelo Dispatcher real do aiogram.

Cobre a entrada player-facing (Aventura → Eventos Mundiais → hub, deep link
``/start flagelo``) com os roteadores na mesma ordem do ``runtime``: o roteador do Flagelo
fica antes do ``creation_router``, cujo ``/start`` genérico abre o Menu Principal.
Abrir o hub só lê o estado: não grava contribuição, não cria participante nem rodada.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage
from sqlalchemy import func, select

from asterion.application.creation import CreationService
from asterion.application.flagelos import FlageloService
from asterion.application.world_event_veu import VeuEventService
from asterion.application.world_event_veu_views import VeuEventViews
from asterion.bot.creation_handlers import creation_router
from asterion.bot.flagelo_handlers import flagelo_router
from asterion.bot.flagelo_ui import FACE, TITLE
from asterion.bot.world_event_veu_handlers import veu_event_router
from asterion.bot.world_event_veu_ui import FLAGELO_ENTRY
from asterion.bot.world_ui import render_adventure
from asterion.domain import flagelos as fl
from asterion.domain.creation import NamePolicy
from asterion.infrastructure.db.models import (
    FlageloContribution,
    FlageloEvent,
    FlageloParticipant,
    FlageloRegionProgress,
    FlageloRound,
)
from tests.test_character_surfaces_telegram import _message_update
from tests.test_creation_ui import callback_update
from tests.test_flagelos_service import (
    SERVER,
    T0,
    FakeSimulator,
    _active,
    _characters,
    _fill,
)


class _Client:
    """Mesma ordem do ``runtime``: Véu, Flagelo e, por último, o ``/start`` da criação."""

    def __init__(self, database):
        sessions = database[1]
        self.flagelos = FlageloService(sessions, SERVER, FakeSimulator())
        veu = VeuEventService(sessions, SERVER)
        self.dispatcher = Dispatcher(disable_fsm=True)
        self.dispatcher.include_router(veu_event_router(veu, VeuEventViews(veu), {}))
        self.dispatcher.include_router(flagelo_router(self.flagelos, {}))
        self.dispatcher.include_router(
            creation_router(CreationService(sessions, SERVER, NamePolicy(())), {})
        )
        self.bot = Bot("123456:local-test-token")
        self.update_id = 0

        async def respond(_bot, method, **_kwargs):
            if isinstance(method, (SendMessage, EditMessageText)):
                return TelegramMessage(
                    message_id=getattr(method, "message_id", None) or 900,
                    date=1,
                    chat=Chat(id=method.chat_id or 1, type="private"),
                    from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                    text=method.text,
                )
            return True

        self.bot.session.make_request = AsyncMock(side_effect=respond)

    def _screen(self):
        for call in reversed(self.bot.session.make_request.call_args_list):
            method = call.args[1]
            if isinstance(method, (SendMessage, EditMessageText)):
                return method
        raise AssertionError("Telegram did not receive a screen")

    async def click(self, actor, data):
        self.update_id += 1
        await self.dispatcher.feed_raw_update(
            self.bot, callback_update(data, update_id=self.update_id, actor=actor)
        )
        return self._screen()

    async def say(self, actor, text):
        self.update_id += 1
        await self.dispatcher.feed_raw_update(
            self.bot, _message_update(text, actor=actor, update_id=self.update_id)
        )
        return self._screen()


def _callbacks(screen) -> list[str]:
    return [b.callback_data for row in screen.reply_markup.inline_keyboard for b in row]


def _labels(screen) -> list[str]:
    return [b.text for row in screen.reply_markup.inline_keyboard for b in row]


async def _snapshot(database):
    """Tudo que uma contribuição, um spawn ou uma entrada em combate alteraria."""
    async with database[1]() as session:
        bars = (
            await session.execute(
                select(
                    FlageloRegionProgress.region_id,
                    FlageloRegionProgress.current_points,
                    FlageloRegionProgress.active_flagelo_id,
                ).order_by(FlageloRegionProgress.region_id)
            )
        ).all()
        counts = []
        for model in (FlageloContribution, FlageloEvent, FlageloParticipant, FlageloRound):
            counts.append(await session.scalar(select(func.count()).select_from(model)))
        return tuple(bars), tuple(counts)


def _assert_six_bars(text: str, points: dict[str, int]) -> None:
    for region in fl.REGIONS:
        value = points.get(region.region_id, 0)
        assert f"{region.short_label} <code>{value}/{fl.THRESHOLD}</code>" in text


def test_adventure_events_button_opens_the_world_events_screen():
    keyboard = render_adventure().keyboard.inline_keyboard
    assert "wev:hub" in [b.callback_data for row in keyboard for b in row]


@pytest.mark.asyncio
async def test_world_events_lists_the_flagelo_and_opens_the_hub_without_one_active(database):
    ((actor, _),) = await _characters(database, 1)
    client = _Client(database)
    await _fill(database, client.flagelos, "varzeas", 412)
    await client.flagelos.apply_contributions(now=T0)

    events = await client.click(actor, "wev:hub")
    assert FLAGELO_ENTRY[0] in _labels(events)
    assert FLAGELO_ENTRY[1] == "flg:hub"

    before = await _snapshot(database)
    hub = await client.click(actor, "flg:hub")
    assert TITLE in hub.text
    _assert_six_bars(hub.text, {"varzeas": 412})
    assert "Nenhum Flagelo desperto" in hub.text
    assert "flg:enter" not in _callbacks(hub)
    assert f"[ {FACE} ]" not in _labels(hub)
    assert "wev:hub" in _callbacks(hub)
    assert await _snapshot(database) == before


@pytest.mark.asyncio
async def test_hub_with_an_active_flagelo_shows_its_region_and_the_face_button(database):
    ((actor, _),) = await _characters(database, 1)
    client = _Client(database)
    await _fill(database, client.flagelos, "vde", fl.THRESHOLD)
    _, spawned = await client.flagelos.apply_contributions(now=T0)
    assert len(spawned) == 1
    event = await _active(database)
    region = fl.region(event.region_id)

    before = await _snapshot(database)
    await client.click(actor, "wev:hub")
    hub = await client.click(actor, "flg:hub")
    assert f"{region.short_label} <code>{fl.THRESHOLD}/{fl.THRESHOLD}</code>" in hub.text
    assert "⚔️ desperto" in hub.text
    assert region.flagelo.name in hub.text
    assert region.region in hub.text
    assert f"[ {FACE} ]" in _labels(hub)
    assert "flg:enter" in _callbacks(hub)
    # Abrir o hub (e a tela de Eventos) não cria combate nem mexe nas barras.
    assert await _snapshot(database) == before

    # O botão leva ao fluxo real de entrada: só aqui o jogador vira participante.
    await client.click(actor, "flg:enter")
    async with database[1]() as session:
        participants = await session.scalar(select(func.count()).select_from(FlageloParticipant))
    assert participants == 1


@pytest.mark.asyncio
async def test_start_flagelo_deep_link_opens_the_hub_not_the_main_menu(database):
    ((actor, _),) = await _characters(database, 1)
    client = _Client(database)
    await _fill(database, client.flagelos, "nareth", 120)
    await client.flagelos.apply_contributions(now=T0)

    before = await _snapshot(database)
    hub = await client.say(actor, "/start flagelo")
    assert TITLE in hub.text
    _assert_six_bars(hub.text, {"nareth": 120})
    assert "flg:enter" not in _callbacks(hub)
    # O deep link só mostra o hub: não inicia Flagelo, não contribui, não entra em combate.
    assert await _snapshot(database) == before
    assert await _active(database) is None

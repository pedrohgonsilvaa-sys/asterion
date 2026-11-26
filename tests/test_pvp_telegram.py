"""Telegram flows for Duelo and Arena da Vigilia (GDD v1.6.0 14, 39.4; UI 48)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage

from asterion.application.pvp import (
    ConfirmationView,
    DuelInviteView,
    PvpHubView,
    PvpMessageView,
    PvpResultView,
    PvpService,
    QueueView,
    RankingRow,
    RankingView,
)
from asterion.bot.guilds_ui import pack
from asterion.bot.pvp_handlers import deliver_notices, pvp_router
from asterion.bot.pvp_ui import error_text, render_pvp, render_ranking
from tests.test_guilds_telegram import _button, _message_update, callback_update
from tests.test_pvp import A, B, _seed

MATCH = UUID(int=7)


class _Client:
    def __init__(self, database):
        self.service = PvpService(database[1], "ocaso")
        self.dispatcher = Dispatcher(disable_fsm=True)
        self.dispatcher.include_router(pvp_router(self.service, {}))
        self.bot = Bot("123456:local-test-token")
        self.update_id = 0
        self.ids = iter(range(7000, 8000))

        async def respond(_bot, method, **_kwargs):
            if isinstance(method, (SendMessage, EditMessageText)):
                return TelegramMessage(
                    message_id=getattr(method, "message_id", None) or next(self.ids),
                    date=1,
                    chat=Chat(id=getattr(method, "chat_id", None) or 1, type="private"),
                    from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                    text=method.text,
                )
            return True

        self.bot.session.make_request = AsyncMock(side_effect=respond)

    async def click(self, actor, data):
        self.update_id += 1
        await self.dispatcher.feed_raw_update(
            self.bot, callback_update(data, actor=actor, update_id=self.update_id)
        )
        return self.screen_of(actor)

    async def say(self, actor, text, reply_prompt=None):
        self.update_id += 1
        reply = None
        if reply_prompt is not None:
            reply = {
                "message_id": 700,
                "date": 1,
                "chat": {"id": actor, "type": "private"},
                "from": {"id": 123456, "is_bot": True, "first_name": "Asterion"},
                "text": reply_prompt,
            }
        await self.dispatcher.feed_raw_update(
            self.bot,
            _message_update(text, actor=actor, update_id=self.update_id, reply_to=reply),
        )
        return self.screen_of(actor)

    def screen_of(self, actor):
        for call in reversed(self.bot.session.make_request.call_args_list):
            method = call.args[1]
            if isinstance(method, (SendMessage, EditMessageText)) and method.chat_id == actor:
                return method
        return None


def _labels(screen):
    return [button.text for row in screen.keyboard.inline_keyboard for button in row]


def _result(**overrides):
    values = {
        "kind": "arena",
        "outcome": "win",
        "reason": "combat",
        "name": "Alfa",
        "opponent": "Beta",
        "renome_before": 1190,
        "renome_after": 1210,
        "placed_before": True,
        "placed_after": True,
        "placement_played": 5,
    }
    return PvpResultView(**(values | overrides))


def test_arena_result_follows_ui_48_and_hides_mmr():
    screen = render_pvp(_result())
    assert screen.text.splitlines()[:2] == ["🏆 Arena da Vigília · Vitória", "Alfa vs Beta"]
    assert "🏅 Renome · 1190 → 1210 (+20)" in screen.text
    assert "🔥 Elo · Chama I → Forjado III" in screen.text
    assert "MMR" not in screen.text and "Recompensas" not in screen.text
    assert _labels(screen) == ["↩️ Retornar"]


def test_same_elo_shows_only_the_elo():
    screen = render_pvp(_result(renome_before=1000, renome_after=1020))
    assert "🔥 Elo · Chama I\n" in f"{screen.text}\n" and "→ Chama" not in screen.text


@pytest.mark.parametrize(
    ("outcome", "title"),
    [("loss", "💀 Arena da Vigília · Derrota"), ("draw", "⚖️ Arena da Vigília · Empate")],
)
def test_result_titles(outcome, title):
    assert render_pvp(_result(outcome=outcome)).text.startswith(title)


def test_placement_lines():
    during = render_pvp(_result(placed_before=False, placed_after=False, placement_played=3))
    assert "🏅 Colocação · 3/5" in during.text
    done = render_pvp(
        _result(placed_before=False, placed_after=True, renome_before=0, renome_after=800)
    )
    assert "🏅 Renome · 800\n🔥 Elo · Chama II" in done.text


def test_duel_result_has_no_rating_block():
    screen = render_pvp(_result(kind="duel", renome_before=None, renome_after=None))
    assert screen.text.startswith("🏆 Duelo · Vitória")
    assert "Renome" not in screen.text and "Elo" not in screen.text


def test_afk_and_surrender_are_explained():
    assert "AFK" in render_pvp(_result(reason="afk")).text
    assert "Rendição" in render_pvp(_result(reason="surrender")).text


def test_confirmation_never_names_the_opponent():
    screen = render_pvp(ConfirmationView(MATCH, False, 45))
    assert _labels(screen) == ["Aceitar", "Recusar"]
    assert "revelado" in screen.text


def test_invite_screens():
    incoming = DuelInviteView(MATCH, True, "Beta", 41, "tecelao", 45)
    assert "Nv. 41 · Tecelão" in render_pvp(incoming).text
    assert "Aceitar" in _labels(render_pvp(incoming))
    outgoing = DuelInviteView(MATCH, False, "B", 11, "vigia", 9)
    assert "Cancelar Duelo" in _labels(render_pvp(outgoing))


def test_hub_states():
    from asterion.bot.pvp_ui import render_arena, render_vigil

    arena = render_arena()
    assert [[b.text for b in r] for r in arena.keyboard.inline_keyboard] == [
        ["🏆 Arena da Vigília", "⚔️ Duelo"],
        ["↩️ Retornar"],
    ]
    noon = datetime(2026, 11, 26, 15, 30, tzinfo=UTC)  # 12:30 em São Paulo
    hub = PvpHubView("Alfa", 30, 0, None, 2, 1, 1, 0, False, None, None)
    screen = render_vigil(hub, now=noon)
    assert "🏅 <b>Colocação</b> · <code>2/5</code>" in screen.text
    assert "🕕 <b>12:00 à 13:00</b> · <code>🟢 Aberto</code>" in screen.text
    assert "🕐 <b>19:00 à 20:00</b> · <code>🔴 Fechado</code>" in screen.text
    assert _labels(screen) == ["🏆 Classificação", "⚔️ Entrar na Arena", "↩️ Retornar"]
    placed = PvpHubView("Alfa", 30, 1842, "Forjado II", 5, 9, 1, 0, True, None, None)
    text = render_vigil(placed, position=128, now=noon).text
    assert "🏅 <b>Posição Atual</b> · <code>#128</code>" in text
    assert "⚒️ <code>Forjado II · 1.842 Renome</code>" in text
    night = datetime(2026, 11, 26, 3, 0, tzinfo=UTC)
    assert render_vigil(hub, now=night).text.count("🔴 Fechado") == 2


def test_messages_and_errors_have_text():
    until = datetime(2026, 11, 9, 15, 35, tzinfo=UTC)
    assert "12:35" in render_pvp(PvpMessageView("dodged", until)).text
    assert render_pvp(QueueView(12)).text.count("12s") == 1
    assert error_text("window_closed") != error_text("anything-else")


def test_ranking_screen():
    row = RankingRow(1, "Alfa", "Regente", 3100)
    screen = render_ranking(RankingView((row,), row, 5))
    assert "<b>#1 👑 Alfa</b>\n👑 <code>Regente · 3.100 Renome</code>" in screen.text
    assert "🥇" not in screen.text and "▶️ Próxima" not in _labels(screen)
    more = render_ranking(RankingView((row,), row, 5, page=0, has_more=True))
    assert _labels(more) == ["▶️ Próxima", "↩️ Retornar"]


@pytest.mark.asyncio
async def test_delivery_survives_a_blocked_player():
    from aiogram.exceptions import TelegramForbiddenError

    from asterion.application.pvp import PvpNotice

    bot = AsyncMock()
    bot.send_message.side_effect = [
        TelegramForbiddenError(method=SendMessage(chat_id=1, text="x"), message="blocked"),
        None,
    ]
    view = PvpMessageView("duel_expired")
    await deliver_notices(bot, [PvpNotice(1, view), PvpNotice(2, view)])
    assert bot.send_message.await_count == 2


@pytest.mark.asyncio
async def test_duel_through_buttons_and_resume_with_menu(database):
    await _seed(database)
    client = _Client(database)
    hub = await client.click(A, "pvp:hub")
    assert hub.text.startswith("⚔️ <b>Arena</b>")
    await client.click(A, "pvp:duel")
    assert "Digite o nome do personagem que deseja desafiar." in client.screen_of(A).text
    preview = await client.say(A, "Beta")
    assert "Nv. 30 · Sentinela" in preview.text
    sent = await client.click(A, _button(preview, "Enviar Desafio"))
    assert "Duelo enviado" in sent.text
    incoming = client.screen_of(B)
    assert "Desafio de Duelo" in incoming.text and "Alfa" in incoming.text

    started = await client.click(B, _button(incoming, "Aceitar"))
    assert "⚔️ Duelo" in started.text
    notified = client.screen_of(A)
    assert "⚔️ Duelo" in notified.text

    resumed = await client.say(A, "/menu")
    assert "⚔️ Duelo" in resumed.text
    resumed = await client.say(B, "/start")
    assert "⚔️ Duelo" in resumed.text

    turn_holder, waiting = (A, B) if "Seu turno" in client.screen_of(A).text else (B, A)
    screen = client.screen_of(turn_holder)
    attack = next(
        button.callback_data
        for row in screen.reply_markup.inline_keyboard
        for button in row
        if button.callback_data.startswith("pv:")
    )
    before = screen.text
    after = await client.click(turn_holder, attack)
    assert after.text != before and "Turno do oponente" in after.text
    assert "Seu turno" in client.screen_of(waiting).text
    waiting_labels = [b.text for r in after.reply_markup.inline_keyboard for b in r]
    assert not any(
        b.callback_data.startswith("pv:") for r in after.reply_markup.inline_keyboard for b in r
    )
    assert "Atualizar" in waiting_labels


@pytest.mark.asyncio
async def test_menu_passes_through_without_a_pvp_activity(database):
    await _seed(database)
    client = _Client(database)
    assert await client.say(A, "/menu") is None


@pytest.mark.asyncio
async def test_bad_tokens_do_not_crash(database):
    await _seed(database)
    client = _Client(database)
    await client.click(A, "pvp:ok:notatoken")
    await client.click(A, f"pvp:ok:{pack(MATCH)}")
    answers = [
        call.args[1]
        for call in client.bot.session.make_request.call_args_list
        if type(call.args[1]).__name__ == "AnswerCallbackQuery"
    ]
    assert len(answers) == 2 and all(item.show_alert for item in answers)

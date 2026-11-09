"""Telegram screens for the Batalha de Guildas (GDD v1.6.0 §15, §49.14; UI §48.3)."""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage
from sqlalchemy import select

from asterion.application import guild_battle as guild_battle_module
from asterion.application.guild_battle import (
    GuildBattleFightView,
    GuildBattleMessageView,
    GuildBattleNotice,
    GuildBattleResultView,
    GuildBattleService,
    MemberOption,
    StandingRow,
    notice_category,
)
from asterion.bot.guild_battle_handlers import (
    deliver_guild_battle_notices,
    guild_battle_router,
)
from asterion.bot.guild_battle_ui import (
    STANDINGS_TOP,
    Draft,
    error_text,
    fingerprint,
    render_guild_battle,
    render_standings,
)
from asterion.bot.guilds_ui import render_guild_menu
from asterion.infrastructure.db.models import (
    Character,
    CharacterNotificationPreference,
    GuildBattleRegistration,
)
from tests.test_guild_battle import (
    CLOSED,
    CONFIRM,
    PAIR,
    REGISTER,
    START,
    _actor,
    _confirm,
    _ids,
    _register,
    _seed,
)
from tests.test_guilds_telegram import _message_update, callback_update

BATTLE = UUID(int=9)


class _Client:
    def __init__(self, database, now):
        self.now = now
        self.service = GuildBattleService(database[1], "ocaso")
        self.dispatcher = Dispatcher(disable_fsm=True)
        self.dispatcher.include_router(
            guild_battle_router(self.service, {}, clock=lambda: self.now)
        )
        self.bot = Bot("123456:local-test-token")
        self.update_id = 0
        self.ids = iter(range(7000, 8000))
        self.alerts: list[str] = []

        async def respond(_bot, method, **_kwargs):
            if isinstance(method, AnswerCallbackQuery) and method.text:
                self.alerts.append(method.text)
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

    async def say(self, actor, text):
        self.update_id += 1
        await self.dispatcher.feed_raw_update(
            self.bot, _message_update(text, actor=actor, update_id=self.update_id)
        )
        return self.screen_of(actor)

    def screen_of(self, actor):
        for call in reversed(self.bot.session.make_request.call_args_list):
            method = call.args[1]
            if isinstance(method, (SendMessage, EditMessageText)) and method.chat_id == actor:
                return method
        return None


def _labels(screen):
    markup = getattr(screen, "reply_markup", None) or screen.keyboard
    return [button.text for row in markup.inline_keyboard for button in row]


def _data(screen, label):
    for row in screen.reply_markup.inline_keyboard:
        for button in row:
            if button.text.startswith(label):
                return button.callback_data
    raise AssertionError(f"{label!r} not in {_labels(screen)}")


def _result(outcome, points, opponent_points):
    return GuildBattleResultView(
        BATTLE, outcome, "Aurora", "Brasas", Decimal(points), Decimal(opponent_points), 1500, 1524
    )


# ------------------------------------------------------------ pure screens


def test_direct_victory_follows_ui_48_3_and_hides_the_rating():
    text = render_guild_battle(_result("win", 2, 0)).text
    assert text.splitlines()[:4] == [
        "🏆 Batalha de Guildas · Vitória",
        "Aurora vs Brasas",
        "",
        "⚔️ Frentes · 2–0",
    ]
    assert "👑" not in text and "📈 Classificação · +3" in text
    assert "1500" not in text and "1524" not in text


def test_champion_is_shown_apart_from_the_fronts():
    win = render_guild_battle(_result("win", 1, 1)).text
    assert "⚔️ Frentes · 1–1\n👑 Campeão · Vitória" in win
    draw = render_guild_battle(_result("draw", "1.5", "1.5")).text
    assert draw.startswith("⚖️ Batalha de Guildas · Empate")
    assert "⚔️ Frentes · 1,5–1,5\n👑 Campeão · Empate" in draw and "+1" in draw
    loss = render_guild_battle(_result("loss", "0.5", "1.5")).text
    assert loss.startswith("💀") and "0,5–1,5" in loss and "+0" in loss
    assert _labels(render_guild_battle(_result("loss", 0, 2))) == ["← Guilda"]


def test_notices_have_text_and_follow_the_author_categories():
    for code in ("paired", "bye"):
        assert "Batalha de Guildas" in render_guild_battle(GuildBattleMessageView(code)).text
    over = render_guild_battle(GuildBattleMessageView("fight_over", "front_2")).text
    assert "Frente II · 3v3" in over
    assert notice_category(GuildBattleMessageView("paired")) == "essentials"
    assert notice_category(GuildBattleMessageView("bye")) == "competitive"
    assert notice_category(GuildBattleMessageView("fight_over", "front_1")) == "competitive"
    assert notice_category(_result("win", 2, 0)) == "competitive"


def test_every_guild_battle_error_code_has_its_own_text():
    source = Path(guild_battle_module.__file__).read_text(encoding="utf-8")
    codes = set(re.findall(r'GuildBattleError\("([a-z_]+)"\)', source))
    assert len(codes) >= 14
    fallback = error_text("__unknown__")
    for code in codes:
        assert error_text(code) != fallback, code


def test_draft_round_trip_and_rejects_bad_payloads():
    draft = Draft().pick(0).pick(1).pick(2).pick(3).pick(4)
    assert draft.step == "champion"
    draft = draft.crown(3).pick(5).pick(6).pick(7)
    assert draft.reserves == (5, 6)
    assert Draft.unpack(draft.pack(), 8) == draft
    for bad in ("AB.CDE.Z.FG", "AA.CDE.C.", "A.CDE..", "AB.CDE.F.G", "AB.CDE..F", "x"):
        with pytest.raises(ValueError):
            Draft.unpack(bad, 8)


def test_standings_show_top_ten_and_the_own_guild_without_rating():
    rows = tuple(
        StandingRow(i, UUID(int=i), f"G{i:02}", 40 - i, 1500 + i, i, 1, 1, 1, 0, i >= 10)
        for i in range(1, 15)
    )
    text = render_standings(rows, own_guild="G13", individual_eligible=False).text
    assert "#10 G10" in text and "#11 G11" not in text
    assert "👉 #13 G13" in text
    assert "1513" not in text
    assert "Batalhas reais · 9/10" in text and "🎁 Elegível" in text
    assert STANDINGS_TOP == 10
    empty = render_standings((), own_guild=None, individual_eligible=None).text
    assert "Nenhuma Guilda" in empty


def test_guild_menu_has_the_entry_point():
    from asterion.domain.guilds import GuildRole
    from tests.test_guilds_telegram import _view

    screen = render_guild_menu(_view(GuildRole.MEMBER))
    assert "🛡️ Batalha de Guildas" in _labels(screen)


async def test_delivery_skips_what_the_player_switched_off():
    service = AsyncMock()
    notices = [GuildBattleNotice(1, GuildBattleMessageView("bye"))]
    service.deliverable.return_value = []
    bot = AsyncMock()
    await deliver_guild_battle_notices(service, bot, notices)
    bot.send_message.assert_not_awaited()


# ---------------------------------------------------------------- database


@pytest.mark.asyncio
async def test_leader_drafts_registers_and_members_see_the_roster(database):
    await _seed(database, guilds=("Aurora",))
    client = _Client(database, REGISTER)
    leader, member = _actor("Aurora", 1), _actor("Aurora", 2)

    hub = await client.click(leader, "gb:hub")
    assert "🟢 Inscrição aberta" in hub.text
    screen = await client.click(leader, _data(hub, "Montar Inscrição"))
    for name in ("Aura", "Aurb", "Aurc", "Aurd", "Aure"):
        screen = await client.click(leader, _data(screen, name))
    assert "Escolha o Campeão" in screen.text
    assert all(label.startswith("👑") for label in _labels(screen)[:5])
    screen = await client.click(leader, _data(screen, "👑 Aurc"))
    screen = await client.click(leader, _data(screen, "Aurf"))
    screen = await client.click(leader, _data(screen, "Aurg"))
    assert not any(label.startswith("Aur") for label in _labels(screen))
    review = await client.click(leader, _data(screen, "Revisar Inscrição"))
    assert "⚔️ Frente I · Aura, Aurb" in review.text
    assert "⚔️ Frente II · 👑 Aurc, Aurd, Aure" in review.text
    assert "🪑 Reservas · Aurf, Aurg" in review.text
    hub = await client.click(leader, _data(review, "Inscrever Guilda"))
    assert "📝 Inscrita" in hub.text and "👑 Campeão" in hub.text
    assert "Cancelar Inscrição" in _labels(hub)

    seen = await client.click(member, "gb:hub")
    assert "Aurc 👑 Campeão" in seen.text
    assert not {"Montar Inscrição", "Cancelar Inscrição", "Refazer Inscrição"} & set(
        _labels(seen)
    )
    await client.click(member, "gb:d:AAAA:...")
    assert client.alerts[-1] == error_text("no_permission")

    await client.click(leader, "gb:cx")
    hub = await client.click(leader, "gb:cxok")
    assert "📝 Inscrita" not in hub.text and "Montar Inscrição" in _labels(hub)


@pytest.mark.asyncio
async def test_stale_draft_restarts_when_the_member_list_changes(database):
    await _seed(database, guilds=("Aurora",))
    client = _Client(database, REGISTER)
    leader = _actor("Aurora", 1)
    hub = await client.click(leader, "gb:hub")
    first = await client.click(leader, _data(hub, "Montar Inscrição"))
    pick = _data(first, "Aura")
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == _actor("Aurora", 7))
        )
        character.level = 29
    screen = await client.click(leader, pick)
    assert client.alerts[-1] == error_text("roster_changed")
    assert "Frente I · —" in screen.text and "Aurg" not in str(_labels(screen))


@pytest.mark.asyncio
async def test_confirmation_substitution_and_combat_screens(database):
    await _seed(database)
    service = GuildBattleService(database[1], "ocaso")
    await _register(database, service, "Aurora", champion=2)
    await _register(database, service, "Brasas")
    notices = await service.run_maintenance(now=PAIR)
    assert {notice.view.code for notice in notices} == {"paired"}

    client = _Client(database, CONFIRM)
    leader = _actor("Aurora", 1)
    member = _actor("Aurora", 3)
    hub = await client.click(member, "gb:hub")
    assert "⚔️ Pareada" in hub.text and "🆚 Brasas" in hub.text
    assert "⏳ aguardando" in hub.text
    hub = await client.click(member, _data(hub, "✅ Confirmar Entrada"))
    assert "Aurc 👑 Campeão · ✅ confirmado" in hub.text
    assert "✅ Confirmar Entrada" not in _labels(hub)

    reserve = await client.click(_actor("Aurora", 6), "gb:hub")
    assert "✅ Confirmar Entrada" not in _labels(reserve)

    hub = await client.click(leader, "gb:hub")
    sub = await client.click(leader, _data(hub, "Substituir por reserva"))
    assert "Aurc" not in str(_labels(sub))
    sub = await client.click(leader, _data(sub, "Aura"))
    hub = await client.click(leader, _data(sub, "Aurf"))
    assert "Aura · substituído" in hub.text
    assert re.search(r"⚔️ Frente I · 2v2\n· Aurb · ⏳ aguardando\n· Aurf · ⏳ aguardando", hub.text)

    await _confirm(service, "Aurora", (2, 4, 5, 6), now=CONFIRM)
    await _confirm(service, "Brasas", (1, 2, 3, 4, 5), now=CONFIRM)
    client.now = CLOSED
    await client.click(leader, "gb:hub")
    hub = await client.click(_actor("Aurora", 7), "gb:hub")
    assert "Substituir por reserva" not in _labels(hub)

    started = await service.run_maintenance(now=START)
    fights = [n for n in started if isinstance(n.view, GuildBattleFightView)]
    assert {n.view.kind for n in fights} == {"front_1", "front_2"}
    client.now = START
    view = next(n.view for n in fights if n.telegram_id == _actor("Aurora", 2))
    screen = render_guild_battle(view)
    assert screen.text.startswith("🛡️ Batalha de Guildas")
    assert "Frente I · 2v2" in screen.text

    turn = next(n for n in fights if n.view.my_turn)
    resumed = await client.say(turn.telegram_id, "/menu")
    assert "🛡️ Batalha de Guildas" in resumed.text and "Seu turno" in resumed.text
    action = next(
        button.callback_data
        for row in resumed.reply_markup.inline_keyboard
        for button in row
        if button.callback_data.startswith("gbf:")
    )
    after = await client.click(turn.telegram_id, action)
    assert after.text != resumed.text and "Aguardando" in after.text
    assert not any(
        button.callback_data.startswith("gbf:")
        for row in after.reply_markup.inline_keyboard
        for button in row
    )
    waiting = [n for n in fights if not n.view.my_turn and n.view.kind == turn.view.kind]
    teammate_screen = render_guild_battle(waiting[0].view)
    assert not any(
        button.callback_data.startswith("gbf:")
        for row in teammate_screen.keyboard.inline_keyboard
        for button in row
    )

    await client.click(turn.telegram_id, action)
    assert client.screen_of(turn.telegram_id) is not None


@pytest.mark.asyncio
async def test_notice_filter_respects_essentials_and_competitive(database):
    await _seed(database, guilds=("Aurora",))
    service = GuildBattleService(database[1], "ocaso")
    ids = await _ids(database, "Aurora")
    actor = _actor("Aurora", 1)
    async with database[1].begin() as session:
        session.add(
            CharacterNotificationPreference(
                character_id=ids[0], category="competitive", enabled=False
            )
        )
    notices = [
        GuildBattleNotice(actor, GuildBattleMessageView("paired")),
        GuildBattleNotice(actor, GuildBattleMessageView("bye")),
        GuildBattleNotice(_actor("Aurora", 2), GuildBattleMessageView("bye")),
    ]
    kept = await service.deliverable(notices)
    assert kept == [notices[0], notices[2]]
    async with database[1].begin() as session:
        session.add(
            CharacterNotificationPreference(
                character_id=ids[0], category="essentials", enabled=False
            )
        )
    assert await service.deliverable(notices) == [notices[2]]


@pytest.mark.asyncio
async def test_hub_errors_and_bad_tokens(database):
    await _seed(database, guilds=("Aurora",))
    client = _Client(database, REGISTER)
    await client.click(424242, "gb:hub")
    assert client.alerts[-1] == error_text("no_character")
    leader = _actor("Aurora", 1)
    await client.click(leader, "gb:sb:notatoken")
    assert client.alerts[-1] == error_text("not_paired")
    await client.click(leader, "gb:sbok:x:y")
    assert client.alerts[-1] == error_text("invalid_substitution")
    hub = await client.click(leader, "gb:hub")
    fp = _data(hub, "Montar Inscrição").split(":")[2]
    await client.click(leader, f"gb:reg:{fp}:AB.CDE..")
    assert client.alerts[-1] == error_text("invalid_roster")
    await client.click(leader, f"gb:d:{fp}:zz.zzz..")
    assert client.alerts[-1] == error_text("invalid_roster")
    calls = client.bot.session.make_request.await_count
    await client.say(leader, "/menu")
    assert client.bot.session.make_request.await_count == calls
    client.now = PAIR
    hub = await client.click(leader, "gb:hub")
    assert "🔴 Inscrição fechada" in hub.text
    async with database[1]() as session:
        assert (await session.scalars(select(GuildBattleRegistration))).first() is None


def test_fingerprint_changes_with_the_candidates():
    a = (MemberOption(UUID(int=1), "A", 30), MemberOption(UUID(int=2), "B", 30))
    assert fingerprint(a) != fingerprint(a[:1]) and len(fingerprint(a)) == 4

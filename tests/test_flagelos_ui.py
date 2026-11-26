"""O Despertar dos Flagelos: telas do Telegram e envio do aviso à comunidade."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from asterion.application.flagelos import (
    NOTICE_TOPIC,
    ActiveFlagelo,
    CombatScreen,
    HubView,
    RankingLine,
    RegionBar,
    SelfState,
)
from asterion.application.outbox import OUTBOX_HANDLERS
from asterion.bot.flagelo_handlers import register_flagelo_notices
from asterion.bot.flagelo_ui import render_combat, render_hub, render_notice
from asterion.domain import flagelos as fl


def _callbacks(screen) -> list[str]:
    return [b.callback_data for row in screen.keyboard.inline_keyboard for b in row]


def _bars(points=(420, 310, 271, 412, 198, 337), active=None):
    return tuple(
        RegionBar(
            region.region_id,
            region.emoji,
            region.short_label,
            value,
            fl.THRESHOLD,
            fl.percent(value),
            region.region_id == active,
        )
        for region, value in zip(fl.REGIONS, points, strict=True)
    )


def test_hub_shows_the_six_bars_absolute_and_percent():
    screen = render_hub(HubView(_bars(), None, None))
    for line in (
        "🌑 Ocaso <code>420/500</code> (84%)",
        "🪢 Vales <code>310/500</code> (62%)",
        "🌾 Nareth <code>271/500</code> (54%)",
        "🥀 Várzeas <code>412/500</code> (82%)",
        "⛰️ Altos <code>198/500</code> (39%)",
        "🌫️ Confins <code>337/500</code> (67%)",
    ):
        assert line in screen.text
    assert _callbacks(screen) == ["wev:hub"]


def test_active_flagelo_shows_hp_lifetime_and_face_button():
    active = ActiveFlagelo(
        uuid4(),
        "tdo",
        "Terras do Ocaso",
        "Varkhenn, o Flagelo das Cinzas",
        31_840,
        35_060,
        18 * 60 + 5,
        3,
        200,
        0,
        True,
    )
    screen = render_hub(HubView(_bars(active="tdo"), active, None))
    assert "⚔️ <b>Varkhenn, o Flagelo das Cinzas</b>" in screen.text
    assert "❤️ <code>31.840/35.060</code>" in screen.text
    assert "⏱️ Ativo há 18m" in screen.text
    assert _callbacks(screen) == ["flg:enter", "wev:hub"]
    assert screen.keyboard.inline_keyboard[0][0].text == "[ Enfrentar o Flagelo ]"
    waiting = render_hub(HubView(_bars(), active, SelfState(True, False, 75, 2, False)))
    assert "⏳ Reentrada em <code>75 s</code>" in waiting.text
    assert _callbacks(waiting) == ["flg:hub", "wev:hub"]


def test_last_rankings_are_listed_by_category():
    lines = (
        RankingLine("offensive", 1, "Ana", 9_000),
        RankingLine("support", 1, "Bia", 300),
    )
    screen = render_hub(HubView(_bars(), None, None, lines, "Varkhenn"))
    assert "🗡️ Ofensivo\n1º Ana · <code>9.000</code>" in screen.text
    assert "✨ Suporte\n1º Bia · <code>300</code>" in screen.text


def test_combat_screen_actions_and_telegraph():
    view = CombatScreen(
        uuid4(),
        "Varkhenn, o Flagelo das Cinzas",
        7,
        8,
        30_000,
        35_060,
        "Ana",
        400,
        500,
        (1, 2),
        False,
        False,
        "Última Fagulha",
        ({"kind": "enemy_damaged", "amount": 120},),
        1,
    )
    screen = render_combat(view)
    assert "⚠️ <i>O Flagelo prepara Última Fagulha.</i>" in screen.text
    assert "O Flagelo sofreu <b>120 de dano</b>" in screen.text
    assert _callbacks(screen) == [
        "flg:a:atk:7",
        "flg:a:def:7",
        "flg:a:art1:7",
        "flg:a:art2:7",
        "flg:fight",
        "flg:leave",
    ]
    acted = render_combat(
        CombatScreen(uuid4(), "x", 7, 8, 1, 2, "Ana", 1, 2, (), True, False, None, (), 0)
    )
    assert _callbacks(acted) == ["flg:fight", "flg:leave"]


def test_notice_texts_follow_the_specification():
    assert render_notice(
        "spawn", "Varkhenn, o Flagelo das Cinzas", "Varkhenn", "Terras do Ocaso"
    ) == (
        "⚠️ O Despertar começou.\n\nVarkhenn, o Flagelo das Cinzas, despertou nas Terras do Ocaso."
    )
    assert render_notice(
        "spawn", "Korvann, o Flagelo do Contrapeso", "Korvann", "Altos Cinéreos"
    ).endswith("despertou nos Altos Cinéreos.")
    assert render_notice("defeat", "x", "Varkhenn", "Terras do Ocaso") == (
        "🏆 O Flagelo foi derrotado.\n\nVarkhenn caiu. O ciclo do Despertar recomeçou."
    )


class _Bot:
    def __init__(self):
        self.sent = []

    async def get_me(self):
        return SimpleNamespace(username="asterion_bot")

    async def send_message(self, **kwargs):
        self.sent.append(kwargs)


class _Service:
    async def notice_payload(self, event_id):
        return "Varkhenn, o Flagelo das Cinzas", "Varkhenn", "Terras do Ocaso"


async def test_outbox_handler_posts_to_the_community_topic_with_a_hub_link():
    deliver = register_flagelo_notices(_Service(), -100123, 77)
    assert OUTBOX_HANDLERS[NOTICE_TOPIC] is deliver
    bot = _Bot()
    await deliver({"kind": "spawn", "event_id": str(uuid4()), "region_id": "tdo"}, bot=bot)
    (sent,) = bot.sent
    assert (sent["chat_id"], sent["message_thread_id"]) == (-100123, 77)
    assert sent["text"].startswith("⚠️ O Despertar começou.")
    button = sent["reply_markup"].inline_keyboard[0][0]
    assert button.url == "https://t.me/asterion_bot?start=flagelo"


async def test_outbox_handler_without_community_chat_sends_nothing():
    deliver = register_flagelo_notices(_Service(), None, None)
    bot = _Bot()
    await deliver({"kind": "defeat", "event_id": str(uuid4())}, bot=bot)
    assert bot.sent == []

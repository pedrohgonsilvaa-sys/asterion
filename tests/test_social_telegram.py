"""Telegram flows for Vínculos, Benefícios and Comunidade (GDD v1.6.0 §31, §32)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, GetMe, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage

from asterion.application.engagement import DailyGiftService
from asterion.application.promo_codes import PromoCodeAdmin, PromoCodeService
from asterion.application.recruitment import RecruitmentService
from asterion.application.social import PlayerCard, RequestsView, RequestView, SocialService
from asterion.bot.benefits_handlers import benefits_router
from asterion.bot.benefits_ui import CODE_PROMPT, render_community
from asterion.bot.social_handlers import social_router
from asterion.bot.social_ui import SEARCH_PROMPT, relato_message, render_requests
from tests.test_guilds_telegram import _message_update, callback_update
from tests.test_social import ANA, BEA, SERVER, _seed, _set_history

_CHAT = -100555
_TOPIC = 77


class _Client:
    def __init__(self, database, *, chat_id=_CHAT, topic_id=_TOPIC, fail_post=False):
        self.social = SocialService(database[1], SERVER)
        self.recruitment = RecruitmentService(database[1], SERVER)
        self.dispatcher = Dispatcher()
        self.dispatcher.include_router(
            social_router(self.social, {}, community_chat_id=chat_id, relatos_topic_id=topic_id)
        )
        self.dispatcher.include_router(
            benefits_router(
                DailyGiftService(database[1], SERVER),
                self.recruitment,
                PromoCodeService(database[1], SERVER),
                {},
                community_url="https://t.me/+comunidade",
            )
        )
        self.bot = Bot("123456:local-test-token")
        self.update_id = 0
        self.ids = iter(range(5000, 6000))
        self.posts = []

        async def respond(_bot, method, **_kwargs):
            if isinstance(method, GetMe):
                return User(id=123456, is_bot=True, first_name="Asterion", username="asterion_bot")
            if isinstance(method, (SendMessage, EditMessageText)):
                chat = method.chat_id
                if chat == _CHAT:
                    if fail_post:
                        from aiogram.exceptions import TelegramBadRequest

                        raise TelegramBadRequest(method=method, message="chat not found")
                    self.posts.append(method)
                return TelegramMessage(
                    message_id=getattr(method, "message_id", None) or next(self.ids),
                    date=datetime(2026, 11, 8),
                    chat=Chat(id=chat or 1, type="private"),
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
        return self.last(actor)

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
            self.bot, _message_update(text, actor=actor, update_id=self.update_id, reply_to=reply)
        )
        return self.last(actor)

    def last(self, actor):
        for call in reversed(self.bot.session.make_request.call_args_list):
            method = call.args[1]
            if isinstance(method, (SendMessage, EditMessageText)) and method.chat_id == actor:
                return method
        return None

    def alerts(self):
        return [
            call.args[1].text
            for call in self.bot.session.make_request.call_args_list
            if type(call.args[1]).__name__ == "AnswerCallbackQuery" and call.args[1].text
        ]


def _labels(screen):
    return {button.text for row in screen.reply_markup.inline_keyboard for button in row}


@pytest.mark.asyncio
async def test_search_reply_opens_public_profile_and_request(database):
    ids = await _seed(database)
    client = _Client(database)
    screen = await client.say(ANA, "be", reply_prompt=SEARCH_PROMPT)
    assert any("Bea" in label for label in _labels(screen))

    profile = await client.click(ANA, f"so:p:{ids[BEA].hex}")
    assert "Bea" in profile.text and str(BEA) not in profile.text
    assert {"Adicionar Amigo", "Bloquear"} <= _labels(profile)

    after = await client.click(ANA, f"so:add:{ids[BEA].hex}")
    assert "Pedido enviado" in after.text and "Cancelar Pedido" in _labels(after)


@pytest.mark.asyncio
async def test_block_needs_confirmation(database):
    ids = await _seed(database)
    client = _Client(database)
    confirm = await client.click(ANA, f"so:blk:{ids[BEA].hex}")
    assert "Confirmar Bloqueio" in _labels(confirm)
    assert (await client.social.blocked(ANA)).total == 0
    done = await client.click(ANA, f"so:bly:{ids[BEA].hex}")
    assert "Desbloquear" in _labels(done)
    assert (await client.social.blocked(ANA)).total == 1


@pytest.mark.asyncio
async def test_malformed_callback_is_answered_without_crashing(database):
    await _seed(database)
    client = _Client(database)
    await client.click(ANA, "so:p:nao-e-uuid")
    await client.click(ANA, "so:p")
    assert len(client.alerts()) == 2


@pytest.mark.asyncio
async def test_share_posts_to_relatos_topic_without_parse_mode(database):
    ids = await _seed(database)
    await _set_history(database, ids[ANA], "Um <b>texto</b> livre")
    client = _Client(database)
    await client.click(ANA, "so:share")
    assert len(client.posts) == 1
    post = client.posts[0]
    assert post.message_thread_id == _TOPIC and post.parse_mode is None
    assert "Um <b>texto</b> livre" in post.text and "Não é lore oficial" in post.text
    assert post.reply_markup.inline_keyboard[0][0].url.startswith(
        "https://t.me/asterion_bot?start=relato_"
    )
    await client.click(ANA, "so:share")
    assert len(client.posts) == 1 and "disponível em" in client.alerts()[-1]


@pytest.mark.asyncio
async def test_share_failure_keeps_the_recharge(database):
    ids = await _seed(database)
    await _set_history(database, ids[ANA], "Texto")
    failing = _Client(database, fail_post=True)
    await failing.click(ANA, "so:share")
    assert "Recarga não foi usada" in failing.alerts()[-1]
    working = _Client(database)
    await working.click(ANA, "so:share")
    assert len(working.posts) == 1


@pytest.mark.asyncio
async def test_share_without_topic_is_refused_and_keeps_recharge(database):
    ids = await _seed(database)
    await _set_history(database, ids[ANA], "Texto")
    client = _Client(database, topic_id=None)
    await client.click(ANA, "so:share")
    assert "não foi configurado" in client.alerts()[-1]


@pytest.mark.asyncio
async def test_profile_deep_link_and_invalid_link(database):
    ids = await _seed(database)
    client = _Client(database)
    screen = await client.say(ANA, f"/start perfil_{ids[BEA].hex}")
    assert "Bea" in screen.text
    bad = await client.say(ANA, "/start perfil_xxx")
    assert "não está disponível" in bad.text


@pytest.mark.asyncio
async def test_relato_message_identifies_the_author(database):
    ids = await _seed(database)
    await _set_history(database, ids[ANA], "Texto")
    client = _Client(database)
    relato = await client.social.share_story(ANA)
    assert "Relato de Ana" in relato_message(relato)
    screen = await client.say(BEA, f"/start relato_{relato.relato_id.hex}")
    assert {"Abrir Perfil", "Denunciar Relato"} <= _labels(screen)


@pytest.mark.asyncio
async def test_benefits_menu_lists_only_what_exists_before_monetization(database):
    await _seed(database)
    client = _Client(database)
    screen = await client.click(ANA, "bn:root")
    assert _labels(screen) == {
        "Dádiva Diária",
        "Chamado de Asterion",
        "Códigos de Asterion",
        "← Menu",
    }


@pytest.mark.asyncio
async def test_daily_gift_screen_claims_and_hides_the_button(database):
    await _seed(database)
    client = _Client(database)
    screen = await client.click(ANA, "bn:gift")
    assert "Resgatar" in _labels(screen) and "Dia 7" in screen.text
    claimed = await client.click(ANA, "bn:gift:claim")
    assert "Dia 1 resgatado" in claimed.text and "Resgatar" not in _labels(claimed)


@pytest.mark.asyncio
async def test_call_screen_shows_personal_link(database):
    await _seed(database)
    client = _Client(database)
    screen = await client.click(ANA, "bn:call")
    assert "https://t.me/asterion_bot?start=chamado_" in screen.text


@pytest.mark.asyncio
async def test_code_reply_redeems(database):
    await _seed(database)
    await PromoCodeAdmin(database[1], SERVER).create(
        code="TESTE-1", reward_table=[{"c_multiplier": "0.10", "basics": 0, "fragments": 0}]
    )
    client = _Client(database)
    screen = await client.say(ANA, "teste-1", reply_prompt=CODE_PROMPT)
    assert "TESTE-1 resgatado" in screen.text and "Coroas" in screen.text
    again = await client.say(ANA, "teste-1", reply_prompt=CODE_PROMPT)
    assert "já resgatou" in again.text


@pytest.mark.asyncio
async def test_community_entry_uses_the_configured_link(database):
    await _seed(database)
    client = _Client(database)
    screen = await client.click(ANA, "community:open")
    assert screen.reply_markup.inline_keyboard[0][0].url == "https://t.me/+comunidade"


def test_requests_screen_stays_under_the_telegram_button_limit():
    card = PlayerCard(uuid4(), "Nome", 1, "sentinela")
    view = RequestsView(
        tuple(RequestView(uuid4(), card) for _ in range(30)),
        tuple(RequestView(uuid4(), card) for _ in range(20)),
    )
    screen = render_requests(view)
    assert sum(len(row) for row in screen.keyboard.inline_keyboard) <= 100
    assert "30 recebidos" in screen.text


def test_community_without_link_says_so():
    assert "não foi configurado" in render_community(None).text

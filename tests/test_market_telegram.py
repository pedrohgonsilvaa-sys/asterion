"""Telegram flows for Mercado, Loja Pessoal and Troca Direta (GDD v1.6.0 §28, §29)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, GetMe, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage

from asterion.application.market import MarketService
from asterion.application.trades import TradeService
from asterion.bot.guilds_ui import pack
from asterion.bot.market_handlers import SEARCH_PROMPT, market_router
from asterion.bot.market_ui import (
    ERROR_FALLBACK,
    ERROR_MESSAGES,
    error_text,
    listing_prompt,
    parse_ref,
    parse_whole,
    with_ref,
)
from tests.test_guilds_telegram import _button, _message_update, callback_update
from tests.test_market import BUYER, SELLER, _give_equipment, _give_material, _material_total, _seed


class _Client:
    def __init__(self, database, chat_id=None, topic_id=None, fail_community=False):
        self.market = MarketService(database[1], "ocaso")
        self.trades = TradeService(database[1], "ocaso")
        self.dispatcher = Dispatcher(disable_fsm=True)
        self.dispatcher.include_router(
            market_router(
                self.market,
                self.trades,
                {},
                community_chat_id=chat_id,
                community_topic_id=topic_id,
            )
        )
        self.bot = Bot("123456:local-test-token")
        self.update_id = 0
        self.ids = iter(range(5000, 6000))
        self.sent = []

        async def respond(_bot, method, **_kwargs):
            if isinstance(method, GetMe):
                return User(id=123456, is_bot=True, first_name="Asterion", username="asterion_bot")
            if isinstance(method, (SendMessage, EditMessageText)):
                chat = getattr(method, "chat_id", None)
                if isinstance(method, SendMessage):
                    if fail_community and chat == chat_id:
                        from aiogram.exceptions import TelegramBadRequest

                        raise TelegramBadRequest(method=method, message="chat not found")
                    self.sent.append(method)
                return TelegramMessage(
                    message_id=getattr(method, "message_id", None) or next(self.ids),
                    date=1,
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
        return self._screen_of(actor)

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
        return self._screen_of(actor)

    def _screen_of(self, actor):
        """The last screen shown to this player, skipping notices sent to the other one."""
        for call in reversed(self.bot.session.make_request.call_args_list):
            method = call.args[1]
            if isinstance(method, (SendMessage, EditMessageText)) and method.chat_id == actor:
                return method
        return None


def test_every_reference_round_trips():
    assert parse_ref(with_ref("Texto", "mkt:price:AbC-_d")) == ("mkt", "price", "AbC-_d")
    assert parse_ref("Mensagem qualquer") is None
    assert parse_ref(None) is None


def test_parse_whole_accepts_only_whole_numbers():
    assert parse_whole("1.000") == 1000
    assert parse_whole(" 15 ") == 15
    assert parse_whole("-3") is None
    assert parse_whole("1,5") is None
    assert parse_whole("9" * 20) is None


def test_every_known_error_has_a_message():
    assert error_text("not_a_code") == ERROR_FALLBACK
    assert all(message for message in ERROR_MESSAGES.values())


@pytest.mark.asyncio
async def test_sell_search_and_buy_flow(database):
    await _seed(database)
    client = _Client(database)
    stack = await _give_material(database, SELLER, 10)

    screen = await client.click(SELLER, "mkt:mine")
    assert "Loja de Vendedor" in screen.text and "Ofertas ativas · 0/6" in screen.text

    prompt = listing_prompt("material", stack, "Ferro", 10)
    screen = await client.say(SELLER, "4 100", reply_prompt=prompt)
    assert "Oferta criada" in screen.text
    assert await _material_total(database, SELLER) == 6

    code = (await client.market.my_shop(SELLER)).code
    screen = await client.say(BUYER, code, reply_prompt=SEARCH_PROMPT)
    assert "Ofertas disponíveis" in screen.text
    listing = (await client.market.find_shop(BUYER, code)).listings[0]

    reference = with_ref("Quantas?", f"mkt:buy:{pack(listing.listing_id)}")
    screen = await client.say(BUYER, "2", reply_prompt=reference)
    assert "Total · 200 Coroas" in screen.text

    screen = await client.click(BUYER, _button(screen, "Confirmar compra"))
    assert "Compra concluída" in screen.text
    assert await _material_total(database, BUYER) == 2
    sale = [item for item in client.sent if item.chat_id == SELLER]
    assert sale and "190 Coroas" in sale[-1].text and "taxa 10 Coroas" in sale[-1].text


@pytest.mark.asyncio
async def test_price_change_shows_the_current_offer(database):
    await _seed(database)
    client = _Client(database)
    stack = await _give_material(database, SELLER, 5)
    listing = await client.market.create_listing(SELLER, "material", stack, 5, 10)
    preview = await client.market.prepare_purchase(BUYER, listing.listing_id, 1)
    await client.market.edit_price(SELLER, listing.listing_id, 25)
    screen = await client.click(BUYER, f"mkt:cp:{pack(preview.purchase_id)}")
    assert "A oferta mudou" in screen.text and "25 Coroas" in screen.text
    assert await _material_total(database, BUYER) == 0


@pytest.mark.asyncio
async def test_mythic_purchase_passes_through_the_extra_screen(database):
    await _seed(database)
    client = _Client(database)
    item = await _give_equipment(database, SELLER, rarity="Mítico")
    screen = await client.say(
        SELLER, "500", reply_prompt=listing_prompt("equipment", item, "Lâmina", 1)
    )
    assert "Item Mítico" in screen.text
    screen = await client.click(SELLER, _button(screen, "Confirmar anúncio"))
    assert "Oferta criada" in screen.text
    listing = (await client.market.my_shop(SELLER)).listings[0]
    screen = await client.click(BUYER, f"mkt:buy:{pack(listing.listing_id)}:1")
    screen = await client.click(BUYER, _button(screen, "Confirmar compra"))
    assert "confirmação final" in screen.text
    screen = await client.click(BUYER, _button(screen, "Comprar item Mítico"))
    assert "Compra concluída" in screen.text


@pytest.mark.asyncio
async def test_invalid_shop_text_is_refused_in_portuguese(database):
    await _seed(database)
    client = _Client(database)
    screen = await client.say(SELLER, "visite t.me/golpe", reply_prompt=with_ref("x", "mkt:desc"))
    assert screen.text == ERROR_MESSAGES["text_links_forbidden"]


@pytest.mark.asyncio
async def test_promotion_without_community_shows_copy_text(database):
    await _seed(database)
    client = _Client(database)
    screen = await client.click(SELLER, "mkt:promote")
    assert "Copie o texto" in screen.text
    assert "https://t.me/asterion_bot?start=shop_" in screen.text


@pytest.mark.asyncio
async def test_promotion_posts_to_the_mercado_topic(database):
    await _seed(database)
    client = _Client(database, chat_id=-1001, topic_id=77)
    screen = await client.click(SELLER, "mkt:promote")
    assert "divulgada" in screen.text
    post = next(item for item in client.sent if item.chat_id == -1001)
    assert post.message_thread_id == 77
    assert "Código ·" in post.text


@pytest.mark.asyncio
async def test_refused_post_does_not_spend_the_cooldown(database):
    await _seed(database)
    client = _Client(database, chat_id=-1001, topic_id=77, fail_community=True)
    await client.click(SELLER, "mkt:promote")
    shop = await client.market.my_shop(SELLER)
    assert shop.promotion_available_at is None


@pytest.mark.asyncio
async def test_deep_link_resolves_the_code_on_the_server(database):
    await _seed(database)
    client = _Client(database)
    code = (await client.market.my_shop(SELLER)).code
    screen = await client.say(BUYER, f"/start shop_{code}")
    assert "Loja de Vendedor" in screen.text
    await client.say(BUYER, "/start shop_INVALIDO")
    assert (
        client.bot.session.make_request.call_args[0][1].text == (ERROR_MESSAGES["shop_unavailable"])
    )


@pytest.mark.asyncio
async def test_trade_flow_with_two_confirmations(database):
    await _seed(database)
    client = _Client(database)
    stack = await _give_material(database, SELLER, 3)

    screen = await client.click(SELLER, "trd:root")
    assert "Convidar jogador" in str(screen.reply_markup)
    screen = await client.say(SELLER, "comprador", reply_prompt=with_ref("x", "trd:invite"))
    assert "Aguardando Comprador" in screen.text
    assert any(item.chat_id == BUYER and "convite" in item.text for item in client.sent)

    screen = await client.click(BUYER, "trd:root")
    screen = await client.click(BUYER, _button(screen, "Aceitar"))
    assert "Troca com Vendedor" in screen.text

    prompt = with_ref("Quantas?", f"trd:qty:m:{pack(stack)}:3")
    screen = await client.say(SELLER, "2", reply_prompt=prompt)
    assert "× 2" in screen.text

    for actor, label in (
        (SELLER, "Confirmar (1/2)"),
        (BUYER, "Confirmar (1/2)"),
        (SELLER, "Confirmar (2/2)"),
    ):
        screen = await client.click(actor, "trd:root")
        await client.click(actor, _button(screen, label))
    screen = await client.click(BUYER, "trd:root")
    screen = await client.click(BUYER, _button(screen, "Confirmar (2/2)"))
    assert "Troca concluída" in screen.text
    assert await _material_total(database, BUYER) == 2


@pytest.mark.asyncio
async def test_forged_trade_id_is_rejected_by_the_server(database):
    await _seed(database)
    client = _Client(database)
    view = await client.trades.invite(SELLER, "comprador")
    await client.click(SELLER + 2, f"trd:x:{pack(view.trade_id)}")
    assert (await client.trades.current(SELLER)).status == "invited"

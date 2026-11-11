"""Telegram adapters for Mercado, Loja Pessoal and Troca Direta (GDD v1.6.0 §28, §29)."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from asterion.application.market import MarketError, MarketService, ShopView
from asterion.application.trades import TradeError, TradeService, TradeView
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import unpack
from asterion.bot.market_ui import (
    KIND_BY_CODE,
    error_text,
    listing_prompt,
    parse_ref,
    parse_whole,
    promotion_keyboard,
    promotion_text,
    render_confirm_mythic_listing,
    render_confirm_mythic_purchase,
    render_confirm_remove,
    render_edit_shop,
    render_kinds,
    render_listing,
    render_my_shop,
    render_own_listing,
    render_promotion_copy,
    render_public_shop,
    render_purchase_done,
    render_purchase_preview,
    render_root,
    render_sources,
    render_trade,
    render_trade_closed,
    render_trade_start,
    render_trade_withdraw,
    sale_notice,
    trade_quantity_prompt,
    with_ref,
)
from asterion.domain.market import SHOP_DESCRIPTION_MAX, SHOP_NAME_MAX

_Failure = (MarketError, TradeError)
DEEP_LINK_PREFIX = "shop_"

SEARCH_PROMPT = with_ref("Envie o Código da Loja.", "mkt:search")
NAME_PROMPT = with_ref(f"Envie o Nome da Loja (até {SHOP_NAME_MAX} caracteres).", "mkt:name")
DESCRIPTION_PROMPT = with_ref(
    f"Envie a Descrição da Loja (até {SHOP_DESCRIPTION_MAX} caracteres, sem links).", "mkt:desc"
)
INVITE_PROMPT = with_ref("Envie o nome do personagem para convidar à Troca.", "trd:invite")


def market_router(
    market: MarketService,
    trades: TradeService,
    images: dict[str, str],
    *,
    community_chat_id: int | None = None,
    community_topic_id: int | None = None,
) -> Router:
    router = Router(name="market")

    async def show(query: CallbackQuery, screen: Screen) -> None:
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def ask(query: CallbackQuery, text: str) -> None:
        if isinstance(query.message, Message):
            await query.message.answer(text, reply_markup=ForceReply(selective=True))

    async def shop_screen(shop: ShopView, notice: str | None = None) -> Screen:
        return render_my_shop(shop, notice) if shop.is_owner else render_public_shop(shop, notice)

    async def notify(
        bot: Bot,
        telegram_id: int | None,
        text: str,
        markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        if telegram_id is None:
            return
        try:
            await bot.send_message(telegram_id, text, reply_markup=markup)
        except TelegramAPIError:
            return  # The state is durable; the player sees it on the next screen.

    async def notify_trade(bot: Bot, view: TradeView, text: str) -> None:
        keyboard = render_trade_closed("").keyboard
        if view.status in {"invited", "open"}:
            keyboard = _open_trade_keyboard()
        await notify(bot, view.counterpart_telegram_id, text, keyboard)

    async def deep_link(bot: Bot) -> Callable[[str], str] | None:
        try:
            me = await bot.me()
        except TelegramAPIError:
            return None
        if not me.username:
            return None
        return lambda code: f"https://t.me/{me.username}?start={DEEP_LINK_PREFIX}{code}"

    async def promote(query: CallbackQuery, actor: int) -> None:
        promotion = await market.promote(actor)
        bot = query.bot
        builder = await deep_link(bot)
        link = builder(promotion.code) if builder else None
        if community_chat_id is None:
            await show(query, render_promotion_copy(promotion, link))
            return
        try:
            await bot.send_message(
                community_chat_id,
                promotion_text(promotion),
                message_thread_id=community_topic_id,
                reply_markup=promotion_keyboard(link),
            )
        except TelegramAPIError:
            await market.revert_promotion(actor, promotion.previous_promoted_at)
            raise MarketError("promotion_failed") from None
        shop = await market.my_shop(actor)
        await show(query, render_my_shop(shop, "📣 Loja divulgada no tópico Mercado."))

    async def open_trade(query: CallbackQuery, actor: int, notice: str | None = None) -> None:
        view = await trades.current(actor)
        await show(query, render_trade_start() if view is None else render_trade(view, notice))

    async def refresh_listing(query: CallbackQuery, actor: int, listing_id: UUID, notice: str):
        try:
            row = await market.listing(actor, listing_id)
        except MarketError:
            await show(query, render_trade_closed(notice))
            return
        await show(query, render_listing(row, notice))

    async def handle_market(query: CallbackQuery, actor: int, parts: list[str]) -> None:
        action = parts[1]
        if action == "root":
            await show(query, render_root(await trades.current(actor)))
        elif action == "search":
            await ask(query, SEARCH_PROMPT)
        elif action == "mine":
            await show(query, render_my_shop(await market.my_shop(actor)))
        elif action == "add":
            await show(query, render_kinds("mkt", "📦 Nova oferta", "mkt:mine"))
        elif action == "src":
            kind = KIND_BY_CODE[parts[2]]
            entries = await market.sources(actor, kind)
            await show(query, render_sources("mkt", kind, entries, int(parts[3]), "mkt:add"))
        elif action == "pick":
            kind = KIND_BY_CODE[parts[2]]
            source_id = unpack(parts[3])
            entries = await market.sources(actor, kind)
            entry = next((item for item in entries if item.id == source_id), None)
            if entry is None or not entry.eligible:
                raise MarketError("item_unavailable")
            await ask(query, listing_prompt(kind, source_id, entry.title, entry.quantity))
        elif action == "lm":
            kind = KIND_BY_CODE[parts[2]]
            await market.create_listing(
                actor, kind, unpack(parts[3]), int(parts[4]), int(parts[5]), mythic_confirmed=True
            )
            await show(query, render_my_shop(await market.my_shop(actor), "✅ Oferta criada."))
        elif action == "own":
            await show(query, render_own_listing(await market.listing(actor, unpack(parts[2]))))
        elif action == "eprice":
            await ask(
                query,
                with_ref("Envie o novo preço em Coroas.", f"mkt:price:{parts[2]}"),
            )
        elif action == "rm":
            await show(query, render_confirm_remove(await market.listing(actor, unpack(parts[2]))))
        elif action == "rmok":
            destination = await market.remove_listing(actor, unpack(parts[2]))
            notice = {
                "inventory": "Oferta removida. O item voltou ao Inventário.",
                "pending": "Oferta removida. O item foi para Entregas Pendentes.",
                "blocked": "Oferta removida. Libere espaço para receber o item.",
            }[destination]
            await show(query, render_my_shop(await market.my_shop(actor), notice))
        elif action == "l":
            await show(query, render_listing(await market.listing(actor, unpack(parts[2]))))
        elif action == "buy":
            listing_id = unpack(parts[2])
            if int(parts[3]) > 1:
                await ask(
                    query,
                    with_ref(
                        f"Quantas unidades comprar? Disponível: {parts[3]}.",
                        f"mkt:buy:{parts[2]}",
                    ),
                )
                return
            preview = await market.prepare_purchase(actor, listing_id, 1)
            await show(query, render_purchase_preview(preview))
        elif action == "cm":
            await show(query, render_confirm_mythic_purchase(unpack(parts[2])))
        elif action in {"cp", "cp2"}:
            await confirm_purchase(query, actor, unpack(parts[2]), mythic=action == "cp2")
        elif action == "edit":
            await show(query, render_edit_shop(await market.my_shop(actor)))
        elif action == "ename":
            await ask(query, NAME_PROMPT)
        elif action == "edesc":
            await ask(query, DESCRIPTION_PROMPT)
        elif action == "cname":
            await show(query, render_edit_shop(await market.edit_shop(actor, clear_name=True)))
        elif action == "cdesc":
            shop = await market.edit_shop(actor, clear_description=True)
            await show(query, render_edit_shop(shop))
        elif action == "promote":
            await promote(query, actor)
        else:
            raise ValueError(action)

    async def confirm_purchase(
        query: CallbackQuery, actor: int, purchase_id: UUID, *, mythic: bool
    ) -> None:
        try:
            result = await market.confirm_purchase(actor, purchase_id, mythic_confirmed=mythic)
        except MarketError as exc:
            if exc.code != "offer_updated":
                raise
            listing_id = await market.purchase_listing(actor, purchase_id)
            await refresh_listing(query, actor, listing_id, error_text(exc.code))
            return
        await show(query, render_purchase_done(result))
        if result.notify_seller and not result.already_committed:
            await notify(query.bot, result.seller_telegram_id, sale_notice(result))

    async def handle_trade(query: CallbackQuery, actor: int, parts: list[str]) -> None:
        action = parts[1]
        if action == "root":
            await open_trade(query, actor)
        elif action == "invite":
            await ask(query, INVITE_PROMPT)
        elif action in {"yes", "no"}:
            view = await trades.respond(actor, unpack(parts[2]), accept=action == "yes")
            if action == "yes":
                await show(query, render_trade(view))
                await notify_trade(query.bot, view, "🤝 Convite de Troca aceito.")
            else:
                await show(query, render_trade_closed("Convite recusado."))
                await notify_trade(query.bot, view, "🤝 Convite de Troca recusado.")
        elif action == "add":
            await show(query, render_kinds("trd", "📦 Adicionar à Troca", "trd:root"))
        elif action == "src":
            kind = KIND_BY_CODE[parts[2]]
            entries = await trades.sources(actor, kind)
            await show(query, render_sources("trd", kind, entries, int(parts[3]), "trd:add"))
        elif action == "pick":
            kind = KIND_BY_CODE[parts[2]]
            source_id = unpack(parts[3])
            available = int(parts[4])
            if available > 1:
                await ask(query, trade_quantity_prompt(kind, source_id, available))
                return
            view = await _require_live(actor)
            updated = await trades.add_item(actor, view.trade_id, kind, source_id, 1)
            await show(query, render_trade(updated))
            await notify_trade(query.bot, updated, "🤝 A Troca mudou. Confira os itens.")
        elif action == "out":
            await show(query, render_trade_withdraw(await _require_live(actor)))
        elif action == "rm":
            updated = await trades.remove_item(actor, unpack(parts[2]), unpack(parts[3]))
            await show(query, render_trade(updated))
            await notify_trade(query.bot, updated, "🤝 A Troca mudou. Confira os itens.")
        elif action == "c":
            outcome = await trades.confirm(actor, unpack(parts[2]), int(parts[3]))
            if outcome.status == "committed":
                await show(query, render_trade_closed("✅ Troca concluída."))
                await notify_trade(query.bot, outcome.view, "✅ Troca concluída.")
            elif outcome.status == "no_space":
                notice = "Um dos Inventários não tem espaço. Confirme de novo depois de liberar."
                await show(query, render_trade(outcome.view, notice))
                await notify_trade(query.bot, outcome.view, f"🤝 {notice}")
            else:
                await show(query, render_trade(outcome.view))
                await notify_trade(query.bot, outcome.view, "🤝 O outro jogador confirmou.")
        elif action == "x":
            view = await trades.cancel(actor, unpack(parts[2]))
            await show(query, render_trade_closed("Troca cancelada. Os itens voltaram."))
            await notify_trade(query.bot, view, "🤝 A Troca foi cancelada. Os itens voltaram.")
        else:
            raise ValueError(action)

    async def _require_live(actor: int) -> TradeView:
        view = await trades.current(actor)
        if view is None:
            raise TradeError("trade_unavailable")
        return view

    @router.callback_query(F.data.startswith("mkt:"))
    async def market_action(query: CallbackQuery) -> None:
        await run_callback(query, handle_market)

    @router.callback_query(F.data.startswith("trd:"))
    async def trade_action(query: CallbackQuery) -> None:
        await run_callback(query, handle_trade)

    async def run_callback(query: CallbackQuery, handler) -> None:
        try:
            await handler(query, query.from_user.id, (query.data or "").split(":"))
        except _Failure as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            return
        except (IndexError, KeyError, ValueError):
            await query.answer(error_text("unknown"), show_alert=True)
            return
        await query.answer()

    @router.message(
        CommandStart(deep_link=True, magic=F.args.startswith(DEEP_LINK_PREFIX)),
    )
    async def open_shop_link(message: Message, command: CommandObject) -> None:
        """§28.9: a link only navigates; the Code is resolved server-side."""
        if message.from_user is None or command.args is None:
            return
        code = command.args.removeprefix(DEEP_LINK_PREFIX)
        try:
            shop = await market.find_shop(message.from_user.id, code)
        except MarketError as exc:
            await message.answer(error_text(exc.code))
            return
        await present(message, await shop_screen(shop), images)

    @router.message(
        F.text,
        F.reply_to_message.text.func(lambda text: parse_ref(text) is not None),
        F.reply_to_message.from_user.is_bot,
    )
    async def text_reply(message: Message) -> None:
        reference = parse_ref(message.reply_to_message.text if message.reply_to_message else None)
        if message.from_user is None or reference is None:
            return
        try:
            await handle_reply(message, message.from_user.id, reference, message.text or "")
        except _Failure as exc:
            await message.answer(error_text(exc.code))
        except (IndexError, KeyError, ValueError):
            await message.answer(error_text("unknown"))

    async def handle_reply(
        message: Message, actor: int, reference: tuple[str, ...], text: str
    ) -> None:
        scope, action = reference[0], reference[1]
        if scope == "trd":
            await handle_trade_reply(message, actor, action, reference, text)
            return
        if action == "search":
            await present(message, await shop_screen(await market.find_shop(actor, text)), images)
        elif action == "name":
            await present(
                message, render_edit_shop(await market.edit_shop(actor, name=text)), images
            )
        elif action == "desc":
            shop = await market.edit_shop(actor, description=text)
            await present(message, render_edit_shop(shop), images)
        elif action == "price":
            price = parse_whole(text)
            if price is None:
                raise MarketError("invalid_price")
            await market.edit_price(actor, unpack(reference[2]), price)
            await present(
                message, render_my_shop(await market.my_shop(actor), "Preço atualizado."), images
            )
        elif action == "buy":
            quantity = parse_whole(text)
            if quantity is None:
                raise MarketError("invalid_quantity")
            preview = await market.prepare_purchase(actor, unpack(reference[2]), quantity)
            await present(message, render_purchase_preview(preview), images)
        elif action == "list":
            await create_listing_from_reply(message, actor, reference, text)
        else:
            raise ValueError(action)

    async def create_listing_from_reply(
        message: Message, actor: int, reference: tuple[str, ...], text: str
    ) -> None:
        kind = KIND_BY_CODE[reference[2]]
        source_id = unpack(reference[3])
        fields = text.split()
        if int(reference[4]) > 1:
            if len(fields) != 2:
                raise MarketError("invalid_quantity")
            quantity, price = parse_whole(fields[0]), parse_whole(fields[1])
        else:
            quantity, price = 1, parse_whole(fields[0]) if len(fields) == 1 else None
        if quantity is None:
            raise MarketError("invalid_quantity")
        if price is None:
            raise MarketError("invalid_price")
        try:
            await market.create_listing(actor, kind, source_id, quantity, price)
        except MarketError as exc:
            if exc.code != "mythic_confirmation_required":
                raise
            await present(
                message, render_confirm_mythic_listing(kind, source_id, quantity, price), images
            )
            return
        await present(
            message, render_my_shop(await market.my_shop(actor), "✅ Oferta criada."), images
        )

    async def handle_trade_reply(
        message: Message, actor: int, action: str, reference: tuple[str, ...], text: str
    ) -> None:
        if action == "invite":
            view = await trades.invite(actor, text)
            await present(message, render_trade(view), images)
            await notify_trade(message.bot, view, "🤝 Você recebeu um convite de Troca Direta.")
        elif action == "qty":
            quantity = parse_whole(text)
            if quantity is None:
                raise TradeError("invalid_quantity")
            view = await _require_live(actor)
            updated = await trades.add_item(
                actor, view.trade_id, KIND_BY_CODE[reference[2]], unpack(reference[3]), quantity
            )
            await present(message, render_trade(updated), images)
            await notify_trade(message.bot, updated, "🤝 A Troca mudou. Confira os itens.")
        else:
            raise ValueError(action)

    return router


def _open_trade_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Abrir Troca", callback_data="trd:root")]]
    )

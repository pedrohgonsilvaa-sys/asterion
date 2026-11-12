"""Telegram adapters for public Crafting Services (GDD v1.6.0 §27.3)."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, ForceReply, Message

from asterion.application.craft_services import CraftServiceError, CraftServiceService
from asterion.bot.craft_service_ui import (
    edit_price_prompt,
    error_text,
    parse_ref,
    price_prompt,
    render_confirm_cancel,
    render_my_services,
    render_offer,
    render_offerable,
    render_order_done,
    render_order_preview,
    render_own_offer,
    render_pick_profession,
    render_shop_services,
    service_notice,
)
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import unpack
from asterion.bot.market_ui import parse_whole
from asterion.domain.professions import PROFESSION_IDS, RECIPE_DEFINITIONS


def craft_service_router(services: CraftServiceService, images: dict[str, str]) -> Router:
    router = Router(name="craft_services")

    async def show(query: CallbackQuery, screen: Screen) -> None:
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def ask(query: CallbackQuery, text: str) -> None:
        if isinstance(query.message, Message):
            await query.message.answer(text, reply_markup=ForceReply(selective=True))

    async def notify(bot: Bot, telegram_id: int | None, text: str) -> None:
        if telegram_id is None:
            return
        try:
            await bot.send_message(telegram_id, text)
        except TelegramAPIError:
            return  # The state is durable; the artisan sees it on the next screen.

    async def handle(query: CallbackQuery, actor: int, parts: list[str]) -> None:
        action = parts[1]
        if action == "mine":
            await show(query, render_my_services(await services.my_services(actor)))
        elif action == "new":
            await show(query, render_pick_profession(await services.my_services(actor)))
        elif action == "prof":
            profession_id = PROFESSION_IDS[int(parts[2])]
            recipes = await services.offerable_recipes(actor, profession_id)
            await show(query, render_offerable(profession_id, recipes))
        elif action == "rec":
            index = int(parts[2])
            if not 0 <= index < len(RECIPE_DEFINITIONS):
                raise ValueError(index)
            await ask(query, price_prompt(index))
        elif action == "own":
            await show(query, render_own_offer(await services.offer(actor, unpack(parts[2]))))
        elif action == "eprice":
            await ask(query, edit_price_prompt(await services.offer(actor, unpack(parts[2]))))
        elif action == "x":
            await show(query, render_confirm_cancel(await services.offer(actor, unpack(parts[2]))))
        elif action == "xok":
            await services.cancel_offer(actor, unpack(parts[2]))
            view = await services.my_services(actor)
            await show(query, render_my_services(view, "Serviço cancelado."))
        elif action == "rep":
            await services.republish(actor, unpack(parts[2]))
            view = await services.my_services(actor)
            await show(query, render_my_services(view, "✅ Serviço republicado por 7 dias."))
        elif action == "shop":
            await show(
                query, render_shop_services(await services.shop_services(actor, unpack(parts[2])))
            )
        elif action == "o":
            await show(query, render_offer(await services.offer(actor, unpack(parts[2]))))
        elif action == "ord":
            await show(
                query, render_order_preview(await services.prepare_order(actor, unpack(parts[2])))
            )
        elif action == "cf":
            await confirm(query, actor, parts[2])
        else:
            raise ValueError(action)

    async def confirm(query: CallbackQuery, actor: int, token: str) -> None:
        order_id = unpack(token)
        try:
            result = await services.confirm_order(actor, order_id)
        except CraftServiceError as exc:
            if exc.code not in {"offer_updated", "order_stale", "preview_expired"}:
                raise
            offer_id = await services.order_offer(actor, order_id)
            await show(
                query, render_offer(await services.offer(actor, offer_id), error_text(exc.code))
            )
            return
        await show(query, render_order_done(result))
        if result.notify_artisan and not result.already_committed:
            await notify(query.bot, result.artisan_telegram_id, service_notice(result))

    @router.callback_query(F.data.startswith("svc:"))
    async def service_action(query: CallbackQuery) -> None:
        try:
            await handle(query, query.from_user.id, (query.data or "").split(":"))
        except CraftServiceError as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            return
        except (IndexError, KeyError, ValueError):
            await query.answer(error_text("unknown"), show_alert=True)
            return
        await query.answer()

    @router.message(
        F.text,
        F.reply_to_message.text.func(lambda text: parse_ref(text) is not None),
        F.reply_to_message.from_user.is_bot,
    )
    async def text_reply(message: Message) -> None:
        reference = parse_ref(message.reply_to_message.text if message.reply_to_message else None)
        if message.from_user is None or reference is None:
            return
        actor = message.from_user.id
        try:
            price = parse_whole(message.text or "")
            if price is None:
                raise CraftServiceError("invalid_price")
            if reference[1] == "create":
                recipe = RECIPE_DEFINITIONS[int(reference[2])]
                await services.create_offer(actor, recipe.recipe_id, price)
                notice = "✅ Serviço publicado por 7 dias."
            elif reference[1] == "price":
                await services.edit_price(actor, unpack(reference[2]), price)
                notice = "Preço atualizado."
            else:
                raise ValueError(reference[1])
        except CraftServiceError as exc:
            await message.answer(error_text(exc.code))
            return
        except (IndexError, KeyError, ValueError):
            await message.answer(error_text("unknown"))
            return
        await present(
            message, render_my_services(await services.my_services(actor), notice), images
        )

    return router

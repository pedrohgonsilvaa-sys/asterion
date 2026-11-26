"""Telegram adapters for Benefícios and Comunidade (GDD v1.6.0 §32)."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.engagement import DailyGiftService, EngagementError
from asterion.application.promo_codes import PromoCodeService
from asterion.application.recruitment import RecruitmentService
from asterion.bot.benefits_ui import (
    error_text,
    parse_ref,
    render_benefits,
    render_call,
    render_code_prompt,
    render_community,
    render_gift,
    render_promo_invalid,
    render_promo_result,
    render_recruit_prompt,
)
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.text_prompt import (
    PROMPTS,
    HasPrompt,
    PendingPrompt,
    consume_reply,
    show_on_prompt,
)

RECRUIT_LINK_PREFIX = "chamado_"


def benefits_router(
    gifts: DailyGiftService,
    recruitment: RecruitmentService,
    codes: PromoCodeService,
    images: dict[str, str],
    *,
    community_url: str | None = None,
    shop_open: bool = False,
) -> Router:
    router = Router(name="benefits")

    async def show(query: CallbackQuery, screen: Screen) -> None:
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def prompt_on_screen(query: CallbackQuery, kind: str, screen: Screen) -> None:
        """Prompt temporário (decisão do autor 2026-11-26 §32.4): a tela vira o pedido."""
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)
            PROMPTS.open(query.from_user.id, kind, query.message)

    async def recruit_link(bot: Bot, code: str) -> str | None:
        try:
            me = await bot.me()
        except TelegramAPIError:
            return None
        return (
            f"https://t.me/{me.username}?start={RECRUIT_LINK_PREFIX}{code}" if me.username else None
        )

    async def call_screen(bot: Bot, actor: int, notice: str | None = None) -> Screen:
        view = await recruitment.view(actor)
        return render_call(view, await recruit_link(bot, view.code), notice)

    async def dispatch(query: CallbackQuery, actor: int) -> None:
        data = query.data or ""
        if data == "bn:root":
            await show(query, render_benefits(shop_open=shop_open))
        elif data == "bn:gift":
            await show(query, render_gift(await gifts.view(actor)))
        elif data == "bn:gift:claim":
            result = await gifts.claim(actor)
            await show(query, render_gift(await gifts.view(actor), result))
        elif data == "bn:call":
            await show(query, await call_screen(query.bot, actor))
        elif data == "bn:call:claim":
            payout = await recruitment.claim(actor)
            notice = f"🪙 {payout.crowns} Coroas resgatadas."
            await show(query, await call_screen(query.bot, actor, notice))
        elif data == "bn:call:enter":
            await prompt_on_screen(query, "bn:recruit", render_recruit_prompt())
        elif data == "bn:code":
            await prompt_on_screen(query, "bn:code", render_code_prompt())
        else:
            raise EngagementError("unknown")

    @router.callback_query(F.data == "community:open")
    async def community(query: CallbackQuery) -> None:
        await show(query, render_community(community_url))
        await query.answer()

    @router.callback_query(F.data.startswith("bn:"))
    async def callback(query: CallbackQuery) -> None:
        try:
            await dispatch(query, query.from_user.id)
        except EngagementError as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            return
        await query.answer()

    _PROMO_INVALID = {"promo_invalid", "promo_expired", "promo_exhausted", "promo_already_redeemed"}

    @router.message(F.text, HasPrompt("bn:"))
    async def prompt_reply(message: Message, prompt: PendingPrompt) -> None:
        actor = message.from_user.id
        text = message.text or ""
        await consume_reply(message)
        PROMPTS.close(actor)
        try:
            if prompt.kind == "bn:code":
                result = await codes.redeem(actor, text)
                screen = render_promo_result(result.code, result.granted)
            else:
                await recruitment.link(actor, text)
                screen = await call_screen(message.bot, actor, "📣 Recrutador vinculado.")
        except EngagementError as exc:
            if prompt.kind == "bn:code" and exc.code in _PROMO_INVALID:
                screen = render_promo_invalid()
            elif prompt.kind == "bn:code":
                await show_on_prompt(
                    message, prompt, render_code_prompt(error_text(exc.code)), images
                )
                PROMPTS.follow(actor, prompt)
                return
            else:
                await show_on_prompt(
                    message, prompt, render_recruit_prompt(error_text(exc.code)), images
                )
                PROMPTS.follow(actor, prompt)
                return
        await show_on_prompt(message, prompt, screen, images)

    @router.message(
        F.text,
        F.reply_to_message.text.func(lambda text: parse_ref(text) is not None),
        F.reply_to_message.from_user.is_bot,
    )
    async def text_reply(message: Message) -> None:
        if message.from_user is None or message.reply_to_message is None:
            return
        reference = parse_ref(message.reply_to_message.text)
        actor = message.from_user.id
        try:
            if reference == "bn:code":
                result = await codes.redeem(actor, message.text or "")
                await present(message, render_promo_result(result.code, result.granted), images)
            elif reference == "bn:recruit":
                await recruitment.link(actor, message.text or "")
                screen = await call_screen(message.bot, actor, "📯 Recrutador vinculado.")
                await present(message, screen, images)
        except EngagementError as exc:
            await message.answer(error_text(exc.code))

    @router.message(CommandStart(deep_link=True, magic=F.args.startswith(RECRUIT_LINK_PREFIX)))
    async def open_recruit_link(message: Message, command: CommandObject) -> None:
        """§32.2: a newcomer's link is kept, and the normal /start creates the character."""
        if message.from_user is None or command.args is None:
            return
        code = command.args.removeprefix(RECRUIT_LINK_PREFIX)
        try:
            linked = await recruitment.open_invite(message.from_user.id, code)
        except EngagementError as exc:
            await message.answer(error_text(exc.code))
            return
        if not linked:
            raise SkipHandler
        await message.answer("📯 Recrutador vinculado.")

    return router

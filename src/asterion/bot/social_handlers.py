"""Telegram adapters for Vínculos and Relatos (GDD v1.6.0 §31, §31.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, ForceReply, Message

from asterion.application.social import SocialError, SocialService
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.social_ui import (
    SEARCH_PROMPT,
    error_text,
    parse_ref,
    relato_keyboard,
    relato_message,
    render_blocked,
    render_confirm_block,
    render_friends,
    render_public_profile,
    render_recents,
    render_relato,
    render_requests,
    render_search_results,
)

PROFILE_LINK_PREFIX = "perfil_"
RELATO_LINK_PREFIX = "relato_"


def social_router(
    social: SocialService,
    images: dict[str, str],
    *,
    community_chat_id: int | None = None,
    relatos_topic_id: int | None = None,
) -> Router:
    router = Router(name="social")

    async def show(query: CallbackQuery, screen: Screen) -> None:
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def profile(query: CallbackQuery, actor: int, key: str, notice: str | None = None):
        view = await social.public_profile(actor, UUID(hex=key))
        await show(query, render_public_profile(view, notice))

    async def share(query: CallbackQuery, actor: int) -> None:
        if community_chat_id is None or relatos_topic_id is None:
            raise SocialError("community_unavailable")
        relato = await social.share_story(actor)
        bot = query.bot
        link = None
        try:
            me = await bot.me()
            if me.username:
                link = (
                    f"https://t.me/{me.username}?start={RELATO_LINK_PREFIX}{relato.relato_id.hex}"
                )
            sent = await bot.send_message(
                community_chat_id,
                relato_message(relato),
                message_thread_id=relatos_topic_id,
                reply_markup=relato_keyboard(link),
                parse_mode=None,
            )
        except TelegramAPIError:
            await social.revert_relato(relato.relato_id)
            raise SocialError("post_failed") from None
        await social.attach_relato(relato.relato_id, community_chat_id, sent.message_id)
        await query.answer("📖 Relato publicado.", show_alert=True)

    async def dispatch(query: CallbackQuery, actor: int, parts: list[str]) -> bool:
        """Run one action. Returns True when it already answered the callback."""
        action = parts[1]
        if action == "friends":
            await show(query, render_friends(await social.friends(actor, _page(parts))))
        elif action == "recents":
            await show(query, render_recents(await social.recents(actor, _page(parts))))
        elif action == "blocked":
            await show(query, render_blocked(await social.blocked(actor, _page(parts))))
        elif action == "requests":
            await show(query, render_requests(await social.requests(actor)))
        elif action == "search":
            if isinstance(query.message, Message):
                await query.message.answer(SEARCH_PROMPT, reply_markup=ForceReply(selective=True))
        elif action == "share":
            await share(query, actor)
            return True
        elif action == "p":
            await profile(query, actor, parts[2])
        elif action == "add":
            await social.send_request(actor, UUID(hex=parts[2]))
            await profile(query, actor, parts[2], "📩 Pedido enviado.")
        elif action == "rm":
            await social.remove_friend(actor, UUID(hex=parts[2]))
            await profile(query, actor, parts[2], "Amizade removida.")
        elif action == "blk":
            view = await social.public_profile(actor, UUID(hex=parts[2]))
            await show(query, render_confirm_block(view))
        elif action == "bly":
            await social.block(actor, UUID(hex=parts[2]))
            await profile(query, actor, parts[2], "🚫 Personagem bloqueado.")
        elif action == "unb":
            await social.unblock(actor, UUID(hex=parts[2]))
            await profile(query, actor, parts[2], "Bloqueio removido.")
        elif action in {"acc", "dec"}:
            await social.respond_request(actor, UUID(hex=parts[2]), accept=action == "acc")
            await show(query, render_requests(await social.requests(actor)))
        elif action == "can":
            await social.cancel_request(actor, UUID(hex=parts[2]))
            await show(query, render_requests(await social.requests(actor)))
        elif action == "rep":
            await social.report_history(actor, UUID(hex=parts[2]))
            await query.answer("Denúncia registrada para análise.", show_alert=True)
            return True
        elif action == "repr":
            await social.report_relato(actor, UUID(hex=parts[2]))
            await query.answer("Denúncia registrada para análise.", show_alert=True)
            return True
        else:
            raise SocialError("unknown")
        return False

    @router.callback_query(F.data.startswith("so:"))
    async def callback(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            answered = await dispatch(query, query.from_user.id, parts)
        except SocialError as exc:
            await query.answer(
                error_text(exc.code, exc.available_at, datetime.now(UTC)), show_alert=True
            )
            return
        except (IndexError, ValueError):
            await query.answer(error_text("unknown"), show_alert=True)
            return
        if not answered:
            await query.answer()

    @router.message(
        F.text,
        F.reply_to_message.text.func(lambda text: parse_ref(text) is not None),
        F.reply_to_message.from_user.is_bot,
    )
    async def search_reply(message: Message) -> None:
        if message.from_user is None:
            return
        try:
            cards = await social.search(message.from_user.id, message.text or "")
        except SocialError as exc:
            await message.answer(error_text(exc.code))
            return
        await present(message, render_search_results(cards), images)

    @router.message(CommandStart(deep_link=True, magic=F.args.startswith(PROFILE_LINK_PREFIX)))
    async def open_profile_link(message: Message, command: CommandObject) -> None:
        if message.from_user is None or command.args is None:
            return
        try:
            target = UUID(hex=command.args.removeprefix(PROFILE_LINK_PREFIX))
            view = await social.public_profile(message.from_user.id, target)
        except SocialError as exc:
            await message.answer(error_text(exc.code))
            return
        except ValueError:
            await message.answer(error_text("not_found"))
            return
        await present(message, render_public_profile(view), images)

    @router.message(CommandStart(deep_link=True, magic=F.args.startswith(RELATO_LINK_PREFIX)))
    async def open_relato_link(message: Message, command: CommandObject) -> None:
        if command.args is None:
            return
        try:
            view = await social.relato(UUID(hex=command.args.removeprefix(RELATO_LINK_PREFIX)))
        except (SocialError, ValueError):
            await message.answer(error_text("not_found"))
            return
        await present(message, render_relato(view), images)

    return router


def _page(parts: list[str]) -> int:
    return int(parts[2]) if len(parts) > 2 else 0

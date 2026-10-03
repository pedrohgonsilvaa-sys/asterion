"""Telegram routes for Settings, Help, Account, rename, and deletion recovery."""

from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, ForceReply, Message

from asterion.application.account import AccountRejected, AccountService
from asterion.application.character_surfaces import CharacterSurfacesService
from asterion.bot.account_ui import (
    render_account,
    render_delete_confirmation,
    render_deletion_pending,
    render_expired_action,
    render_help_root,
    render_help_topic,
    render_notifications,
    render_rename_preview,
    render_rename_start,
    render_settings,
)
from asterion.bot.character_surfaces_ui import render_profile
from asterion.bot.creation_handlers import present

RENAME_PROMPT = "Responda a esta mensagem com o novo nome do personagem."


def _parse_base36(value: str) -> int:
    if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
        raise ValueError("invalid revision")
    return int(value, 36)


def _private_router(name: str) -> Router:
    router = Router(name=name)
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")
    return router


def settings_router(
    service: AccountService,
    character_surfaces: CharacterSurfacesService,
    images: dict[str, str],
) -> Router:
    router = _private_router("settings_account_help")

    async def show_account(target: Message | CallbackQuery) -> None:
        actor = target.from_user.id
        view = await service.account(actor)
        if view is None:
            if isinstance(target, Message):
                await target.answer("Personagem indisponível.")
            else:
                await target.answer("Personagem indisponível.", show_alert=True)
            return
        screen = render_account(view)
        message = target if isinstance(target, Message) else target.message
        if isinstance(message, Message):
            await present(message, screen, images, edit=isinstance(target, CallbackQuery))

    async def show_pending_if_any(message: Message) -> bool:
        view = await service.pending_deletion(message.from_user.id)
        if view is None or not view.deletion_pending:
            return False
        await present(message, render_deletion_pending(view), images)
        return True

    @router.message(CommandStart())
    async def account_aware_start(message: Message) -> None:
        if message.from_user and await show_pending_if_any(message):
            return
        raise SkipHandler()

    @router.message(Command("menu"))
    async def account_aware_menu(message: Message) -> None:
        if message.from_user is None:
            return
        if await show_pending_if_any(message):
            return
        if await service.account(message.from_user.id) is None:
            await message.answer("Você não possui um personagem ativo. Use /start para começar.")
            return
        raise SkipHandler()

    @router.message(Command("perfil"))
    async def profile_command(message: Message) -> None:
        if message.from_user is None:
            return
        view = await character_surfaces.profile(message.from_user.id)
        if view is None:
            await message.answer("Personagem indisponível.")
            return
        await present(message, render_profile(view), images)

    @router.message(Command("ajuda"))
    async def help_command(message: Message) -> None:
        await present(message, render_help_root(), images)

    @router.message(Command("cancelar"))
    async def cancel_command(message: Message) -> None:
        if message.from_user is None:
            return
        changed = await service.cancel_transient_inputs(message.from_user.id)
        await message.answer(
            "Entrada cancelada. Sua atividade e seu progresso continuam intactos."
            if changed
            else "Não há entrada cancelável no momento."
        )

    @router.callback_query(F.data == "settings:root")
    async def settings_root(query: CallbackQuery) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_settings(), images, edit=True)

    @router.callback_query(F.data == "settings:notifications")
    async def notifications(query: CallbackQuery) -> None:
        view = await service.notification(query.from_user.id, "essentials")
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_notifications(view), images, edit=True)

    @router.callback_query(F.data.startswith("settings:n:"))
    async def toggle_notification(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        if len(parts) != 5 or parts[2] != "essentials" or parts[4] not in {"0", "1"}:
            await query.answer("Ação expirada.", show_alert=True)
            if isinstance(query.message, Message):
                await present(query.message, render_expired_action(), images, edit=True)
            return
        try:
            revision = _parse_base36(parts[3])
        except ValueError:
            revision = -1
        view = await service.set_notification(
            query.from_user.id,
            "essentials",
            expected_revision=revision,
            expected_enabled=parts[4] == "1",
            enabled=parts[4] == "0",
        )
        stale = view is None or view.revision != revision + 1
        await query.answer("A tela foi atualizada." if stale else None)
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_notifications(view), images, edit=True)

    @router.callback_query(F.data == "help:root")
    async def help_root(query: CallbackQuery) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_help_root(), images, edit=True)

    @router.callback_query(F.data.startswith("help:"))
    async def help_topic(query: CallbackQuery) -> None:
        key = (query.data or "").removeprefix("help:")
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_help_topic(key), images, edit=True)

    @router.callback_query(F.data == "account:root")
    async def account_root(query: CallbackQuery) -> None:
        await query.answer()
        await show_account(query)

    @router.callback_query(F.data == "account:rename")
    async def rename_start(query: CallbackQuery) -> None:
        view = await service.account(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_rename_start(view), images, edit=True)

    @router.callback_query(F.data == "account:rename:input")
    async def rename_input(query: CallbackQuery) -> None:
        if not isinstance(query.message, Message):
            await query.answer()
            return
        prompt = await query.message.answer(
            RENAME_PROMPT,
            reply_markup=ForceReply(selective=True, input_field_placeholder="Novo nome"),
            parse_mode=None,
        )
        try:
            await service.begin_rename(query.from_user.id, prompt.message_id)
        except AccountRejected as exc:
            await prompt.edit_text(_account_error(exc.code))
            await query.answer("Não foi possível iniciar o Renome.", show_alert=True)
            return
        await query.answer("Responda à mensagem com o novo nome.")

    @router.callback_query(F.data.startswith("account:r:confirm:"))
    async def rename_confirm(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            revision = _parse_base36(parts[3]) if len(parts) == 4 else -1
            new_name = await service.confirm_rename(query.from_user.id, revision)
        except (ValueError, AccountRejected) as exc:
            await query.answer(_account_error(getattr(exc, "code", "expired")), show_alert=True)
            if isinstance(query.message, Message):
                await present(query.message, render_expired_action(), images, edit=True)
            return
        await query.answer("Nome alterado.")
        if isinstance(query.message, Message):
            await show_account(query)
            await query.message.answer(f"✅ Nome Alterado · {new_name}")

    @router.callback_query(F.data == "account:delete")
    async def delete_preview(query: CallbackQuery) -> None:
        try:
            view = await service.start_deletion_confirmation(query.from_user.id)
        except AccountRejected as exc:
            await query.answer(_account_error(exc.code), show_alert=True)
            if isinstance(query.message, Message):
                await show_account(query)
            return
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_delete_confirmation(view), images, edit=True)

    @router.callback_query(F.data.startswith("account:d:confirm:"))
    async def delete_confirm(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            preview_id = UUID(hex=parts[3]) if len(parts) == 4 else None
        except ValueError:
            preview_id = None
        if preview_id is None:
            await query.answer("Esta ação expirou.", show_alert=True)
            if isinstance(query.message, Message):
                await present(query.message, render_expired_action(), images, edit=True)
            return
        view = await service.account(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        try:
            await service.request_deletion(query.from_user.id, view.name, preview_id)
        except AccountRejected as exc:
            await query.answer(_account_error(exc.code), show_alert=True)
            if isinstance(query.message, Message):
                await show_account(query)
            return
        current = await service.account(query.from_user.id)
        await query.answer("Exclusão pendente.")
        if current is not None and isinstance(query.message, Message):
            await present(query.message, render_deletion_pending(current), images, edit=True)

    @router.callback_query(F.data.startswith("account:d:cancel:"))
    async def delete_cancel(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            revision = _parse_base36(parts[3]) if len(parts) == 4 else -1
            await service.cancel_deletion(query.from_user.id, revision)
        except (ValueError, AccountRejected) as exc:
            await query.answer(_account_error(getattr(exc, "code", "expired")), show_alert=True)
            if isinstance(query.message, Message):
                view = await service.account(query.from_user.id)
                if view is not None:
                    await present(query.message, render_deletion_pending(view), images, edit=True)
            return
        await query.answer("Exclusão cancelada.")
        await show_account(query)

    @router.callback_query(F.data.startswith("account:"))
    async def stale_account_callback(query: CallbackQuery) -> None:
        await query.answer("Esta ação expirou.", show_alert=True)
        if isinstance(query.message, Message):
            await present(query.message, render_expired_action(), images, edit=True)

    @router.message(F.text, F.reply_to_message)
    async def rename_reply(message: Message, event_update) -> None:
        if message.from_user is None or not message.text:
            raise SkipHandler()
        prompt = message.reply_to_message
        if (
            message.text.startswith("/")
            or prompt is None
            or prompt.from_user is None
            or not prompt.from_user.is_bot
            or not (prompt.text or "").startswith(RENAME_PROMPT)
        ):
            raise SkipHandler()
        try:
            view = await service.preview_rename(
                message.from_user.id,
                prompt.message_id,
                event_update.update_id,
                message.text,
            )
        except AccountRejected as exc:
            await message.answer(_account_error(exc.code))
            return
        await present(message, render_rename_preview(view), images)

    @router.message()
    async def pending_deletion_message_guard(message: Message) -> None:
        if message.from_user is None:
            raise SkipHandler()
        if not await show_pending_if_any(message):
            raise SkipHandler()

    @router.callback_query()
    async def pending_deletion_callback_guard(query: CallbackQuery) -> None:
        if not isinstance(query.message, Message):
            await query.answer()
            return
        view = await service.pending_deletion(query.from_user.id)
        if view is None or not view.deletion_pending:
            raise SkipHandler()
        await query.answer("Exclusão pendente.")
        await present(query.message, render_deletion_pending(view), images, edit=True)

    return router


def _account_error(code: str) -> str:
    return {
        "foreground": "Conclua a atividade atual antes de alterar a Conta.",
        "input_pending": "Conclua ou cancele a entrada pendente primeiro.",
        "cooldown": "O prazo de recarga do Renome ainda não terminou.",
        "insufficient_crowns": "Coroas insuficientes.",
        "name_unavailable": "Este nome está em uso ou reservado.",
        "deletion_pending": "Há uma Exclusão Pendente para este personagem.",
        "deletion_due": "O prazo terminou; a exclusão está sendo finalizada.",
        "stale_preview": "Esta prévia expirou. Abra Conta para atualizar.",
        "stale_confirmation": "Esta confirmação expirou. Abra Conta para atualizar.",
        "stale_deletion": "A tela de Exclusão foi atualizada.",
        "stale_input": "Esta solicitação expirou. Abra Conta para tentar novamente.",
        "invalid_name": "O nome não segue as regras de criação.",
        "expired": "Esta ação expirou. Atualize a tela.",
    }.get(code, "Não foi possível processar esta ação. Atualize a tela e tente novamente.")

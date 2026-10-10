"""Telegram adapters for Vínculos → Grupo and persistent invitations."""

from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.groups import GroupError, GroupService
from asterion.bot.creation_handlers import present
from asterion.bot.groups_ui import (
    render_expired_group_action,
    render_group,
    render_invites,
    render_links,
    revision36,
)


def _parse_revision(value: str) -> int:
    if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
        raise ValueError("invalid revision")
    return int(value, 36)


def groups_router(
    service: GroupService,
    images: dict[str, str],
    p1=None,
    p2=None,
    p3=None,
    p4=None,
    p5=None,
    p6=None,
    s6=None,
) -> Router:
    router = Router(name="groups")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show_links(target: Message | CallbackQuery) -> None:
        actor = target.from_user.id
        group = await service.group(actor)
        invites = await service.incoming_invites(actor)
        message = target if isinstance(target, Message) else target.message
        if isinstance(message, Message):
            await present(
                message,
                render_links(group, len(invites)),
                images,
                edit=isinstance(target, CallbackQuery),
            )

    async def show_group(target: Message | CallbackQuery) -> None:
        group = await service.group(target.from_user.id)
        proposals = await service.activity_proposals(target.from_user.id)
        message = target if isinstance(target, Message) else target.message
        if isinstance(message, Message):
            await present(
                message,
                render_group(group, proposals),
                images,
                edit=isinstance(target, CallbackQuery),
            )

    async def show_inbox(target: Message | CallbackQuery) -> None:
        invites = await service.incoming_invites(target.from_user.id)
        message = target if isinstance(target, Message) else target.message
        if isinstance(message, Message):
            await present(
                message,
                render_invites(invites),
                images,
                edit=isinstance(target, CallbackQuery),
            )

    async def stale(query: CallbackQuery) -> None:
        await query.answer("Ação expirada. Atualizei a tela.", show_alert=True)
        if isinstance(query.message, Message):
            await present(query.message, render_expired_group_action(), images, edit=True)

    @router.message(Command("grupo"))
    async def group_command(message: Message) -> None:
        if message.from_user is None:
            return
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 2 or parts[1].casefold() != "convidar":
            await show_group(message)
            return
        if len(parts) != 3:
            await message.answer("Use /grupo convidar Nome do personagem.")
            return
        group = await service.group(message.from_user.id)
        if group is None:
            await message.answer("Crie um Grupo antes de convidar alguém.")
            return
        try:
            invite = await service.invite(
                message.from_user.id,
                parts[2],
                expected_group_revision=group.revision,
            )
        except GroupError as exc:
            await message.answer(_error_text(exc.code))
            return
        await message.answer(f"Convite enviado a {invite.invitee_name}. Ele expira em 10 minutos.")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Aceitar",
                        callback_data=(
                            f"group:invite:a:{invite.invite_id.hex}:"
                            f"{revision36(invite.revision)}"
                        ),
                    ),
                    InlineKeyboardButton(
                        text="Recusar",
                        callback_data=(
                            f"group:invite:d:{invite.invite_id.hex}:"
                            f"{revision36(invite.revision)}"
                        ),
                    ),
                ]
            ]
        )
        try:
            await message.bot.send_message(
                invite.invitee_telegram_id,
                f"{invite.inviter_name} convidou você para um Grupo de Asterion. "
                "O convite expira em 10 minutos.",
                reply_markup=keyboard,
            )
        except TelegramAPIError:
            # The invitation remains durable and can be accepted from Vínculos → Convites.
            return

    @router.callback_query(F.data == "links:root")
    async def links_root(query: CallbackQuery) -> None:
        await query.answer()
        await show_links(query)

    @router.callback_query(F.data == "group:root")
    async def group_root(query: CallbackQuery) -> None:
        await query.answer()
        await show_group(query)

    @router.callback_query(F.data == "group:create")
    async def group_create(query: CallbackQuery) -> None:
        try:
            await service.create_group(query.from_user.id)
        except GroupError as exc:
            if exc.code != "already_in_group":
                await query.answer(_error_text(exc.code), show_alert=True)
                return
        await query.answer()
        await show_group(query)

    @router.callback_query(F.data == "group:inbox")
    async def group_inbox(query: CallbackQuery) -> None:
        await query.answer()
        await show_inbox(query)

    @router.callback_query(F.data.startswith("group:invite:"))
    async def group_invite_response(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            if len(parts) != 5 or parts[2] not in {"a", "d"}:
                raise ValueError("invalid callback")
            invite_id = UUID(hex=parts[3])
            expected_revision = _parse_revision(parts[4])
            group = await service.respond_invite(
                query.from_user.id,
                invite_id,
                expected_revision=expected_revision,
                accept=parts[2] == "a",
            )
        except (ValueError, GroupError) as exc:
            if isinstance(exc, GroupError) and exc.code not in {"stale", "invite_expired"}:
                await query.answer(_error_text(exc.code), show_alert=True)
                return
            await stale(query)
            return
        await query.answer("Convite aceito." if parts[2] == "a" else "Convite recusado.")
        if parts[2] == "a" and group is not None:
            await show_group(query)
        else:
            await show_inbox(query)

    @router.callback_query(F.data.startswith("group:leave:"))
    async def group_leave(query: CallbackQuery) -> None:
        try:
            parts = (query.data or "").split(":")
            if len(parts) != 3:
                raise ValueError("invalid callback")
            group = await service.leave(
                query.from_user.id,
                expected_group_revision=_parse_revision(parts[2]),
            )
        except (ValueError, GroupError) as exc:
            if isinstance(exc, GroupError) and exc.code not in {"stale", "not_in_group"}:
                await query.answer(_error_text(exc.code), show_alert=True)
                return
            await stale(query)
            return
        await query.answer("Você saiu do Grupo.")
        if group is None:
            await show_links(query)
        else:
            await show_group(query)

    @router.callback_query(F.data.startswith("group:kick:"))
    async def group_kick(query: CallbackQuery) -> None:
        try:
            parts = (query.data or "").split(":")
            if len(parts) != 4:
                raise ValueError("invalid callback")
            await service.kick(
                query.from_user.id,
                UUID(hex=parts[2]),
                expected_group_revision=_parse_revision(parts[3]),
            )
        except (ValueError, GroupError) as exc:
            if isinstance(exc, GroupError) and exc.code not in {"stale", "not_group_member"}:
                await query.answer(_error_text(exc.code), show_alert=True)
                return
            await stale(query)
            return
        await query.answer("Integrante removido.")
        if isinstance(query.message, Message):
            await show_group(query)

    @router.callback_query(F.data.startswith("group:lead:"))
    async def group_transfer(query: CallbackQuery) -> None:
        try:
            parts = (query.data or "").split(":")
            if len(parts) != 4:
                raise ValueError("invalid callback")
            await service.transfer_leadership(
                query.from_user.id,
                UUID(hex=parts[2]),
                expected_group_revision=_parse_revision(parts[3]),
            )
        except (ValueError, GroupError) as exc:
            if isinstance(exc, GroupError) and exc.code not in {"stale", "not_group_member"}:
                await query.answer(_error_text(exc.code), show_alert=True)
                return
            await stale(query)
            return
        await query.answer("Liderança transferida.")
        if isinstance(query.message, Message):
            await show_group(query)

    @router.callback_query(F.data.startswith("group:proposal:"))
    async def activity_proposal_action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            if len(parts) != 5 or parts[2] not in {"yes", "no", "start"}:
                raise ValueError("invalid activity proposal callback")
            proposal_id = UUID(hex=parts[3])
            revision = _parse_revision(parts[4])
            if parts[2] in {"yes", "no"}:
                await service.respond_activity(
                    query.from_user.id,
                    proposal_id,
                    expected_revision=revision,
                    accept=parts[2] == "yes",
                )
                await query.answer(
                    "Atividade confirmada." if parts[2] == "yes" else "Atividade recusada."
                )
                await show_group(query)
                return
            proposal = await service.activity_proposal(query.from_user.id, proposal_id)
            service_by_type = {
                "campaign_p1": p1,
                "campaign_p2": p2,
                "campaign_p3": p3,
                "campaign_p4": p4,
                "campaign_p5": p5,
                "campaign_p6": p6,
                "campaign_s6": s6,
            }
            campaign_service = service_by_type.get(proposal.activity_type)
            if campaign_service is None:
                await query.answer(
                    "Esta atividade não pode ser iniciada por esta tela.", show_alert=True
                )
                return
            await campaign_service.start_group_combat(
                query.from_user.id, proposal_id, expected_revision=revision
            )
            await query.answer("Confronto da Jornada iniciado.")
            if isinstance(query.message, Message):
                view = await campaign_service.resume(query.from_user.id)
                if proposal.activity_type == "campaign_p1":
                    from asterion.bot.p1_ui import render_p1

                    screen = render_p1(view)
                elif proposal.activity_type == "campaign_p2":
                    from asterion.bot.p2_ui import render_p2

                    screen = render_p2(view)
                elif proposal.activity_type == "campaign_p3":
                    from asterion.bot.p3_ui import render_p3

                    screen = render_p3(view)
                elif proposal.activity_type == "campaign_p4":
                    from asterion.bot.p4_ui import render_p4

                    screen = render_p4(view)
                elif proposal.activity_type == "campaign_p5":
                    from asterion.bot.p5_ui import render_p5

                    screen = render_p5(view)
                elif proposal.activity_type == "campaign_p6":
                    from asterion.bot.p6_ui import render_p6

                    screen = render_p6(view)
                else:
                    from asterion.bot.s6_ui import render_s6

                    screen = render_s6(view)
                await present(query.message, screen, images, edit=True)
        except (ValueError, GroupError) as exc:
            if isinstance(exc, GroupError) and exc.code not in {"stale", "proposal_expired"}:
                await query.answer(_error_text(exc.code), show_alert=True)
                return
            await stale(query)

    return router


def _error_text(code: str) -> str:
    messages = {
        "character_missing": "Personagem indisponível.",
        "not_in_group": "Você não está em um Grupo.",
        "already_in_group": "Este personagem já está em um Grupo.",
        "group_full": "O Grupo já tem quatro integrantes.",
        "leader_only": "Somente o Líder pode fazer isso.",
        "character_not_found": "Não encontrei esse personagem neste servidor.",
        "cannot_invite_self": "Você não pode convidar o próprio personagem.",
        "invite_pending": "Já existe um convite pendente para esse personagem.",
        "invite_expired": "Esse convite expirou ou já foi respondido.",
        "wrong_server": "Esse convite pertence a outro servidor.",
        "activity_in_progress": (
            "A ação está bloqueada enquanto você participa de uma atividade compartilhada."
        ),
        "not_group_member": "Esse personagem não está no seu Grupo.",
        "cannot_kick_self": "Use Sair do Grupo para remover a si mesmo.",
        "participant_busy": "Um dos integrantes já está preparando outra atividade.",
        "proposer_ineligible": "Você não está elegível para propor essa atividade.",
        "roster_not_group_subset": "O roster precisa conter integrantes deste Grupo.",
        "roster_size_invalid": "O roster precisa ter de um a quatro personagens.",
        "journey_reference_not_member": "A referência da Jornada precisa pertencer ao Grupo.",
        "participant_ineligible": "Você não está elegível para confirmar essa atividade.",
    }
    return messages.get(code, "Não foi possível concluir essa ação.")

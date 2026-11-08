"""Telegram adapters for Guilds (GDD v1.6.0 §30, §44.1).

Buttons carry ids only. Each click re-reads the viewer's Guild and compares it
with the id in the button; the service then re-checks permissions in its own
transaction, so a stale or forged callback can never act on another Guild.
"""

from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from asterion.application.guilds import GuildError, GuildService, GuildView
from asterion.bot.creation_handlers import present
from asterion.bot.guilds_ui import (
    DEPOSIT_PROMPT,
    FOUND_PROMPT,
    INVITE_PROMPT,
    RENAME_PROMPT,
    SEARCH_PROMPT,
    contribute_prompt,
    error_text,
    kind_from_contribute_prompt,
    pack,
    parse_crowns,
    render_browse,
    render_confirm,
    render_expired,
    render_guild_menu,
    render_inbox,
    render_manage_members,
    render_my_applications,
    render_new_project,
    render_public_page,
    render_received_applications,
    render_search_results,
    render_works,
    unpack,
)
from asterion.domain.guilds import GuildRole, ProjectKind, Recruitment

# Errors that mean "your screen is out of date" rather than "you did something invalid".
_STALE_CODES = {"not_in_guild", "guild_missing", "target_not_member"}


def guilds_router(service: GuildService, images: dict[str, str]) -> Router:
    router = Router(name="guilds")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    def _target(target: Message | CallbackQuery) -> Message | None:
        message = target if isinstance(target, Message) else target.message
        return message if isinstance(message, Message) else None

    async def show_menu(target: Message | CallbackQuery) -> None:
        message = _target(target)
        if message is None:
            return
        actor = target.from_user.id
        guild = await service.my_guild(actor)
        invites = 0
        applications = 0
        if guild is None:
            invites = len(await service.incoming_invites(actor))
        elif guild.viewer_role in (GuildRole.LEADER, GuildRole.OFFICER):
            applications = len(await service.received_applications(actor))
        await present(
            message,
            render_guild_menu(guild, invites=invites, applications=applications),
            images,
            edit=isinstance(target, CallbackQuery),
        )

    async def stale(query: CallbackQuery) -> None:
        await query.answer("Ação expirada. Atualizei a tela.", show_alert=True)
        message = _target(query)
        if message is not None:
            await present(message, render_expired(), images, edit=True)

    async def fail(query: CallbackQuery, exc: GuildError) -> None:
        if exc.code in _STALE_CODES:
            await stale(query)
        else:
            await query.answer(error_text(exc.code), show_alert=True)

    async def current_guild(query: CallbackQuery, token: str) -> GuildView | None:
        """The viewer's Guild, only if it is the one the button was drawn for."""
        try:
            guild_id = unpack(token)
        except ValueError:
            return None
        guild = await service.my_guild(query.from_user.id)
        if guild is None or guild.guild_id != guild_id:
            return None
        return guild

    async def ask(query: CallbackQuery, prompt: str, placeholder: str) -> None:
        message = _target(query)
        if message is None:
            await query.answer()
            return
        await message.answer(
            prompt,
            reply_markup=ForceReply(selective=True, input_field_placeholder=placeholder),
            parse_mode=None,
        )
        await query.answer("Envie a resposta à solicitação.")

    @router.message(Command("guilda"))
    async def guild_command(message: Message) -> None:
        if message.from_user is not None:
            await show_menu(message)

    @router.callback_query(F.data == "guild:root")
    async def guild_root(query: CallbackQuery) -> None:
        await query.answer()
        await show_menu(query)

    # ----------------------------------------------------- without a Guild

    @router.callback_query(F.data == "guild:found")
    async def guild_found(query: CallbackQuery) -> None:
        if await service.my_guild(query.from_user.id) is not None:
            await query.answer(error_text("already_in_guild"), show_alert=True)
            return
        await ask(query, FOUND_PROMPT, "Nome TAG")

    @router.callback_query(F.data == "guild:search")
    async def guild_search(query: CallbackQuery) -> None:
        await ask(query, SEARCH_PROMPT, "Nome ou TAG")

    @router.callback_query(F.data.startswith("guild:browse:"))
    async def guild_browse(query: CallbackQuery) -> None:
        token = (query.data or "").split(":")[-1]
        try:
            after = None if token == "0" else unpack(token)
        except ValueError:
            await stale(query)
            return
        page = await service.recruiting(after=after)
        message = _target(query)
        await query.answer()
        if message is not None:
            await present(message, render_browse(page, first=after is None), images, edit=True)

    @router.callback_query(F.data.startswith("guild:page:"))
    async def guild_page(query: CallbackQuery) -> None:
        try:
            guild_id = unpack((query.data or "").split(":")[2])
        except (ValueError, IndexError):
            await stale(query)
            return
        page = await service.public_page(guild_id)
        mine = await service.my_guild(query.from_user.id)
        message = _target(query)
        await query.answer()
        if message is not None:
            await present(
                message, render_public_page(page, can_apply=mine is None), images, edit=True
            )

    @router.callback_query(F.data.startswith("guild:apply:"))
    async def guild_apply(query: CallbackQuery) -> None:
        try:
            guild_id = unpack((query.data or "").split(":")[2])
            await service.apply(query.from_user.id, guild_id)
        except (ValueError, IndexError):
            await stale(query)
            return
        except GuildError as exc:
            await fail(query, exc)
            return
        await query.answer("Inscrição enviada.")
        message = _target(query)
        if message is not None:
            await present(
                message,
                render_my_applications(await service.my_applications(query.from_user.id)),
                images,
                edit=True,
            )

    @router.callback_query(F.data == "guild:myapps")
    async def guild_my_applications(query: CallbackQuery) -> None:
        await query.answer()
        message = _target(query)
        if message is not None:
            applications = await service.my_applications(query.from_user.id)
            await present(message, render_my_applications(applications), images, edit=True)

    @router.callback_query(F.data.startswith("guild:cancelapp:"))
    async def guild_cancel_application(query: CallbackQuery) -> None:
        try:
            application_id = unpack((query.data or "").split(":")[2])
            await service.cancel_application(query.from_user.id, application_id)
        except (ValueError, IndexError):
            await stale(query)
            return
        except GuildError as exc:
            await fail(query, exc)
            return
        await query.answer("Inscrição cancelada.")
        message = _target(query)
        if message is not None:
            applications = await service.my_applications(query.from_user.id)
            await present(message, render_my_applications(applications), images, edit=True)

    @router.callback_query(F.data == "guild:inbox")
    async def guild_inbox(query: CallbackQuery) -> None:
        await query.answer()
        message = _target(query)
        if message is not None:
            invites = await service.incoming_invites(query.from_user.id)
            await present(message, render_inbox(invites), images, edit=True)

    @router.callback_query(F.data.startswith("guild:inv:"))
    async def guild_invite_response(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            if len(parts) != 4 or parts[2] not in {"a", "d"}:
                raise ValueError("invalid callback")
            await service.respond_invite(
                query.from_user.id, unpack(parts[3]), accept=parts[2] == "a"
            )
        except ValueError as exc:
            if isinstance(exc, GuildError):
                await query.answer(error_text(exc.code), show_alert=True)
                message = _target(query)
                if message is not None:
                    invites = await service.incoming_invites(query.from_user.id)
                    await present(message, render_inbox(invites), images, edit=True)
                return
            await stale(query)
            return
        await query.answer("Convite aceito." if parts[2] == "a" else "Convite recusado.")
        if parts[2] == "a":
            await show_menu(query)
        else:
            message = _target(query)
            if message is not None:
                invites = await service.incoming_invites(query.from_user.id)
                await present(message, render_inbox(invites), images, edit=True)

    # ------------------------------------------------- Leader and Officer

    @router.callback_query(F.data.startswith("guild:invite:"))
    async def guild_invite_prompt(query: CallbackQuery) -> None:
        guild = await current_guild(query, (query.data or "").split(":")[-1])
        if guild is None:
            await stale(query)
            return
        if guild.viewer_role is GuildRole.MEMBER:
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        await ask(query, INVITE_PROMPT, "Nome do personagem")

    @router.callback_query(F.data.startswith("guild:recv:"))
    async def guild_received(query: CallbackQuery) -> None:
        guild = await current_guild(query, (query.data or "").split(":")[-1])
        if guild is None:
            await stale(query)
            return
        try:
            applications = await service.received_applications(query.from_user.id)
        except GuildError as exc:
            await fail(query, exc)
            return
        await query.answer()
        message = _target(query)
        if message is not None:
            await present(
                message,
                render_received_applications(guild.guild_id, applications),
                images,
                edit=True,
            )

    @router.callback_query(F.data.startswith("guild:app:"))
    async def guild_review_application(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            if len(parts) != 5 or parts[2] not in {"a", "r"}:
                raise ValueError("invalid callback")
            guild = await current_guild(query, parts[3])
            if guild is None:
                raise ValueError("stale guild")
            application_id = unpack(parts[4])
            pending = {
                item.application_id: item
                for item in await service.received_applications(query.from_user.id)
            }
            if parts[2] == "a":
                await service.approve_application(query.from_user.id, application_id)
            else:
                await service.reject_application(query.from_user.id, application_id)
        except GuildError as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            await _refresh_received(query)
            return
        except ValueError:
            await stale(query)
            return
        await query.answer("Inscrição aprovada." if parts[2] == "a" else "Inscrição recusada.")
        applicant = pending.get(application_id)
        if applicant is not None and applicant.character_telegram_id is not None:
            result = (
                "foi aprovada. Você agora faz parte da Guilda."
                if parts[2] == "a"
                else "foi recusada."
            )
            try:
                await query.bot.send_message(
                    applicant.character_telegram_id,
                    f"Sua Inscrição na Guilda {guild.name} [{guild.tag}] {result}",
                )
            except TelegramAPIError:
                # The result is durable and shows under Guilda → Minhas Inscrições.
                pass
        await _refresh_received(query)

    async def _refresh_received(query: CallbackQuery) -> None:
        message = _target(query)
        guild = await service.my_guild(query.from_user.id)
        if message is None or guild is None:
            return
        try:
            applications = await service.received_applications(query.from_user.id)
        except GuildError:
            return
        await present(
            message,
            render_received_applications(guild.guild_id, applications),
            images,
            edit=True,
        )

    @router.callback_query(F.data.startswith("guild:recr:"))
    async def guild_recruitment(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            if len(parts) != 4 or parts[2] not in {"o", "c"}:
                raise ValueError("invalid callback")
            if await current_guild(query, parts[3]) is None:
                raise ValueError("stale guild")
            await service.set_recruitment(
                query.from_user.id,
                Recruitment.OPEN if parts[2] == "o" else Recruitment.CLOSED,
            )
        except GuildError as exc:
            await fail(query, exc)
            return
        except ValueError:
            await stale(query)
            return
        await query.answer(
            "Recrutamento aberto." if parts[2] == "o" else "Recrutamento fechado."
        )
        await show_menu(query)

    @router.callback_query(F.data.startswith("guild:mem:"))
    async def guild_members(query: CallbackQuery) -> None:
        guild = await current_guild(query, (query.data or "").split(":")[-1])
        if guild is None:
            await stale(query)
            return
        if guild.viewer_role is GuildRole.MEMBER:
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        await query.answer()
        message = _target(query)
        if message is not None:
            await present(message, render_manage_members(guild), images, edit=True)

    # ------------------------------------------------ member actions (ids)

    async def member_action(query: CallbackQuery, parts: list[str], expected_len: int):
        """Parse `guild:<verb>:<guild>:<character>` and return (guild, character_id)."""
        if len(parts) != expected_len:
            return None
        guild = await current_guild(query, parts[2])
        if guild is None:
            return None
        try:
            character_id = unpack(parts[3])
        except ValueError:
            return None
        return guild, character_id

    def _name(guild: GuildView, character_id: UUID) -> str:
        for member in guild.members:
            if member.character_id == character_id:
                return member.name
        return "esse membro"

    async def refresh_members(query: CallbackQuery) -> None:
        guild = await service.my_guild(query.from_user.id)
        message = _target(query)
        if guild is None or message is None:
            await show_menu(query)
            return
        if len(guild.members) < 2 or guild.viewer_role is GuildRole.MEMBER:
            await show_menu(query)
            return
        await present(message, render_manage_members(guild), images, edit=True)

    @router.callback_query(F.data.regexp(r"^guild:(pro|dem):"))
    async def guild_change_role(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        parsed = await member_action(query, parts, 4)
        if parsed is None:
            await stale(query)
            return
        _guild, character_id = parsed
        try:
            if parts[1] == "pro":
                await service.promote(query.from_user.id, character_id)
            else:
                await service.demote(query.from_user.id, character_id)
        except GuildError as exc:
            await fail(query, exc)
            return
        await query.answer("Cargo alterado.")
        await refresh_members(query)

    @router.callback_query(F.data.regexp(r"^guild:(kick|lead):"))
    async def guild_confirm_member_action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        parsed = await member_action(query, parts, 4)
        message = _target(query)
        if parsed is None or message is None:
            await stale(query)
            return
        guild, character_id = parsed
        name = _name(guild, character_id)
        if parts[1] == "kick":
            text = f"Expulsar {name} da Guilda? Ele só poderá entrar em outra após 12 horas."
        else:
            text = (
                f"Transferir a liderança para {name}? Você passará a ser Oficial."
            )
        await query.answer()
        await present(
            message,
            render_confirm(text, f"guild:{parts[1]}ok:{parts[2]}:{parts[3]}"),
            images,
            edit=True,
        )

    @router.callback_query(F.data.regexp(r"^guild:(kick|lead)ok:"))
    async def guild_member_action_confirmed(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        parsed = await member_action(query, parts, 4)
        if parsed is None:
            await stale(query)
            return
        _guild, character_id = parsed
        try:
            if parts[1] == "kickok":
                await service.remove_member(query.from_user.id, character_id)
            else:
                await service.transfer_leadership(query.from_user.id, character_id)
        except GuildError as exc:
            await fail(query, exc)
            return
        done = "Integrante removido." if parts[1] == "kickok" else "Liderança transferida."
        await query.answer(done)
        await show_menu(query)

    # ----------------------------------------------------------- everyone

    @router.callback_query(F.data.startswith("guild:leave:"))
    async def guild_leave_confirm(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        guild = await current_guild(query, parts[-1])
        message = _target(query)
        if guild is None or message is None:
            await stale(query)
            return
        if guild.viewer_role is GuildRole.LEADER:
            await query.answer(error_text("leader_must_transfer"), show_alert=True)
            return
        await query.answer()
        await present(
            message,
            render_confirm(
                f"Sair da Guilda {guild.name}? Você só poderá entrar em outra após 12 horas.",
                f"guild:leaveok:{parts[-1]}",
            ),
            images,
            edit=True,
        )

    @router.callback_query(F.data.startswith("guild:leaveok:"))
    async def guild_leave(query: CallbackQuery) -> None:
        if await current_guild(query, (query.data or "").split(":")[-1]) is None:
            await stale(query)
            return
        try:
            await service.leave(query.from_user.id)
        except GuildError as exc:
            await fail(query, exc)
            return
        await query.answer("Você saiu da Guilda.")
        await show_menu(query)

    # --------------------------------------------- Treasury, Obras, Rename

    async def show_works(target: Message | CallbackQuery) -> None:
        message = _target(target)
        guild = await service.my_guild(target.from_user.id)
        if message is None or guild is None:
            await show_menu(target)
            return
        await present(message, render_works(guild), images, edit=isinstance(target, CallbackQuery))

    @router.callback_query(F.data.startswith("guild:works:"))
    async def guild_works(query: CallbackQuery) -> None:
        if await current_guild(query, (query.data or "").split(":")[-1]) is None:
            await stale(query)
            return
        await query.answer()
        await show_works(query)

    @router.callback_query(F.data.startswith("guild:dep:"))
    async def guild_deposit_prompt(query: CallbackQuery) -> None:
        if await current_guild(query, (query.data or "").split(":")[-1]) is None:
            await stale(query)
            return
        await ask(query, DEPOSIT_PROMPT, "Quantidade de Coroas")

    @router.callback_query(F.data.startswith("guild:newp:"))
    async def guild_new_project(query: CallbackQuery) -> None:
        guild = await current_guild(query, (query.data or "").split(":")[-1])
        message = _target(query)
        if guild is None or message is None:
            await stale(query)
            return
        if guild.viewer_role is not GuildRole.LEADER:
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        await query.answer()
        await present(message, render_new_project(guild), images, edit=True)

    @router.callback_query(F.data.startswith("guild:np:"))
    async def guild_start_project(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            if len(parts) != 4 or await current_guild(query, parts[2]) is None:
                raise ValueError("stale guild")
            kind = ProjectKind(parts[3])
            await service.start_project(query.from_user.id, kind)
        except GuildError as exc:
            await fail(query, exc)
            return
        except ValueError:
            await stale(query)
            return
        await query.answer("Obra aberta para Financiamento.")
        await show_works(query)

    @router.callback_query(F.data.startswith("guild:con:"))
    async def guild_contribute_prompt(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        guild = None
        if len(parts) == 5 and parts[2] in {"w", "t"}:
            guild = await current_guild(query, parts[3])
        try:
            project_id = unpack(parts[4]) if guild is not None else None
        except ValueError:
            project_id = None
        project = next(
            (
                p
                for p in (guild.active_projects if guild else ())
                if p.project_id == project_id and p.status == "funding"
            ),
            None,
        )
        if guild is None or project is None:
            await stale(query)
            return
        from_treasury = parts[2] == "t"
        if from_treasury and guild.viewer_role is not GuildRole.LEADER:
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        await ask(
            query,
            contribute_prompt(project.kind, from_treasury=from_treasury),
            "Quantidade de Coroas",
        )

    @router.callback_query(F.data.startswith("guild:ren:"))
    async def guild_rename_prompt(query: CallbackQuery) -> None:
        guild = await current_guild(query, (query.data or "").split(":")[-1])
        if guild is None:
            await stale(query)
            return
        if guild.viewer_role is not GuildRole.LEADER:
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        await ask(query, RENAME_PROMPT, "Nome TAG")

    # ---------------------------------------------------------- dissolution

    @router.callback_query(F.data.startswith("guild:diss:"))
    async def guild_dissolve_confirm(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        guild = await current_guild(query, parts[-1])
        message = _target(query)
        if guild is None or message is None:
            await stale(query)
            return
        if guild.viewer_role is not GuildRole.LEADER:
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        await query.answer()
        await present(
            message,
            render_confirm(
                f"Dissolver a Guilda {guild.name}? Você terá 72 horas para cancelar. "
                "Nesse período a Tesouraria e as Obras ficam congeladas. No fim, o saldo da "
                "Tesouraria e as Coroas das Obras em Financiamento são perdidos, e todos os "
                "membros só poderão entrar em outra Guilda após 12 horas.",
                f"guild:dissok:{parts[-1]}",
            ),
            images,
            edit=True,
        )

    @router.callback_query(F.data.regexp(r"^guild:diss(ok|no):"))
    async def guild_dissolution(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        if len(parts) != 3 or await current_guild(query, parts[2]) is None:
            await stale(query)
            return
        try:
            if parts[1] == "dissok":
                await service.request_dissolution(query.from_user.id)
            else:
                await service.cancel_dissolution(query.from_user.id)
        except GuildError as exc:
            await fail(query, exc)
            return
        await query.answer(
            "Dissolução marcada para daqui a 72 horas."
            if parts[1] == "dissok"
            else "Dissolução cancelada."
        )
        await show_menu(query)

    @router.message(
        F.text,
        F.reply_to_message.text.func(lambda text: kind_from_contribute_prompt(text) is not None),
        F.reply_to_message.from_user.is_bot,
    )
    async def guild_contribute_reply(message: Message) -> None:
        prompt = message.reply_to_message
        parsed = kind_from_contribute_prompt(prompt.text or "") if prompt else None
        if message.from_user is None or parsed is None:
            return
        kind, from_treasury = parsed
        amount = parse_crowns(message.text or "")
        if amount is None:
            await message.answer(error_text("invalid_amount"))
            return
        guild = await service.my_guild(message.from_user.id)
        project = next(
            (p for p in (guild.active_projects if guild else ()) if p.kind is kind),
            None,
        )
        if project is None:
            await message.answer(error_text("project_not_funding"))
            return
        try:
            result = await service.contribute(
                message.from_user.id, project.project_id, amount, from_treasury=from_treasury
            )
        except GuildError as exc:
            await message.answer(error_text(exc.code))
            return
        await message.answer(f"Contribuição registrada: {result.applied} Coroas.")
        await present(message, render_works(result.guild), images)

    # ------------------------------------------------------- text replies

    # The prompt text is part of the filter so replies to other features' prompts
    # keep propagating to their own routers.
    @router.message(
        F.text,
        F.reply_to_message.text.in_(
            {FOUND_PROMPT, SEARCH_PROMPT, INVITE_PROMPT, DEPOSIT_PROMPT, RENAME_PROMPT}
        ),
        F.reply_to_message.from_user.is_bot,
    )
    async def guild_reply(message: Message) -> None:
        prompt = message.reply_to_message
        if message.from_user is None or prompt is None:
            return
        actor = message.from_user.id
        text = (message.text or "").strip()
        if prompt.text == FOUND_PROMPT:
            parts = text.split()
            if len(parts) != 2:
                await message.answer(
                    "Envie o Nome e a TAG separados por um espaço. Ex.: Aurora AUR"
                )
                return
            try:
                await service.create_guild(actor, parts[0], parts[1])
            except GuildError as exc:
                await message.answer(error_text(exc.code))
                return
            await show_menu(message)
        elif prompt.text == DEPOSIT_PROMPT:
            amount = parse_crowns(text)
            if amount is None:
                await message.answer(error_text("invalid_amount"))
                return
            try:
                guild = await service.deposit(actor, amount)
            except GuildError as exc:
                await message.answer(error_text(exc.code))
                return
            await message.answer(f"Depósito registrado: {amount} Coroas.")
            await present(message, render_works(guild), images)
        elif prompt.text == RENAME_PROMPT:
            parts = text.split()
            if len(parts) != 2 or parts == ["-", "-"]:
                await message.answer("Envie o Nome e a TAG separados por espaço. Ex.: Aurora -")
                return
            try:
                await service.rename(
                    actor,
                    name=None if parts[0] == "-" else parts[0],
                    tag=None if parts[1] == "-" else parts[1],
                )
            except GuildError as exc:
                await message.answer(error_text(exc.code))
                return
            await message.answer("Guilda renomeada.")
            await show_menu(message)
        elif prompt.text == SEARCH_PROMPT:
            results = await service.search(text)
            await present(message, render_search_results(text[:32], results), images)
        elif prompt.text == INVITE_PROMPT:
            try:
                invite = await service.invite(actor, text)
            except GuildError as exc:
                await message.answer(error_text(exc.code))
                return
            await message.answer(f"Convite enviado a {invite.invitee_name}.")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Aceitar", callback_data=f"guild:inv:a:{pack(invite.invite_id)}"
                        ),
                        InlineKeyboardButton(
                            text="Recusar", callback_data=f"guild:inv:d:{pack(invite.invite_id)}"
                        ),
                    ]
                ]
            )
            try:
                await message.bot.send_message(
                    invite.invitee_telegram_id,
                    f"{invite.inviter_name} convidou você para a Guilda "
                    f"{invite.guild_name} [{invite.guild_tag}].",
                    reply_markup=keyboard,
                )
            except TelegramAPIError:
                # The invite is durable and still appears under Guilda → Convites recebidos.
                return

    return router

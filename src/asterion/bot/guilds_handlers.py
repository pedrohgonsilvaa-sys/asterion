"""Telegram adapters for Guilds (GDD v1.7.1 §30; decisões do autor 2026-11-26 §9–§16).

Buttons carry ids only. Each click re-reads the viewer's Guild and compares it
with the id in the button; the service then re-checks permissions in its own
transaction, so a stale or forged callback can never act on another Guild.

Entradas de texto usam o prompt temporário (``text_prompt``): a tela atual vira o
pedido, a resposta do jogador é apagada e a mesma tela mostra o resultado.
"""

from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.guilds import (
    CharacterCandidateView,
    GuildError,
    GuildService,
    GuildView,
)
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import (
    error_text,
    finances_from_treasury,
    pack,
    parse_crowns,
    render_application,
    render_browse,
    render_confirm,
    render_deposit,
    render_deposit_prompt,
    render_dissolve,
    render_expired,
    render_finance_prompt,
    render_found_confirm,
    render_found_name,
    render_found_tag,
    render_guild_menu,
    render_inbox,
    render_invite,
    render_invite_candidates,
    render_invite_prompt,
    render_manage,
    render_members,
    render_my_applications,
    render_obra,
    render_obras,
    render_public_page,
    render_received_applications,
    render_recruit,
    render_rename_confirm,
    render_rename_name,
    render_rename_tag,
    render_search_prompt,
    render_search_results,
    render_symbol_picker,
    render_treasury,
    render_treasury_history,
    unpack,
)
from asterion.bot.text_prompt import (
    PROMPTS,
    HasPrompt,
    PendingPrompt,
    consume_reply,
    show_on_prompt,
)
from asterion.domain.guilds import (
    GUILD_SYMBOLS,
    GuildNameError,
    GuildRole,
    ProjectKind,
    Recruitment,
    normalize_guild_name,
    normalize_guild_tag,
)

PAGE_SIZE = 5

# Errors that mean "your screen is out of date" rather than "you did something invalid".
_STALE_CODES = {"not_in_guild", "guild_missing", "target_not_member"}


def guilds_router(service: GuildService, images: dict[str, str]) -> Router:
    router = Router(name="guilds")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    # Rascunhos de interface (fundação, renome e candidatos de convite) por jogador.
    found_drafts: dict[int, dict[str, str]] = {}
    rename_drafts: dict[int, dict[str, str]] = {}
    candidates: dict[int, tuple[CharacterCandidateView, ...]] = {}

    def _target(target: Message | CallbackQuery) -> Message | None:
        message = target if isinstance(target, Message) else target.message
        return message if isinstance(message, Message) else None

    async def show(query: CallbackQuery, screen: Screen) -> Message | None:
        message = _target(query)
        if message is not None:
            await present(message, screen, images, edit=True)
        return message

    async def ask(
        query: CallbackQuery, prompt_kind: str, screen: Screen, **data: str
    ) -> None:
        """Edita a tela atual para o pedido de texto e abre o prompt temporário."""
        await query.answer()
        message = await show(query, screen)
        if message is not None:
            PROMPTS.open(query.from_user.id, prompt_kind, message, data)

    async def reopen(message: Message, prompt: PendingPrompt, screen: Screen) -> None:
        """Mostra o erro no próprio pedido e mantém o prompt aberto."""
        message_id = await show_on_prompt(message, prompt, screen, images)
        PROMPTS.follow(message.from_user.id, prompt, message_id=message_id)

    async def show_menu(target: Message | CallbackQuery) -> None:
        message = _target(target)
        if message is None:
            return
        guild = await service.my_guild(target.from_user.id)
        await present(
            message, render_guild_menu(guild), images, edit=isinstance(target, CallbackQuery)
        )

    async def stale(query: CallbackQuery) -> None:
        await query.answer("Ação expirada. Atualizei a tela.", show_alert=True)
        await show(query, render_expired())

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

    def _parts(query: CallbackQuery) -> list[str]:
        return (query.data or "").split(":")

    def _manager(guild: GuildView) -> bool:
        return guild.viewer_role in (GuildRole.LEADER, GuildRole.OFFICER)

    @router.message(Command("guilda"))
    async def guild_command(message: Message) -> None:
        if message.from_user is not None:
            await show_menu(message)

    @router.callback_query(F.data == "guild:root")
    async def guild_root(query: CallbackQuery) -> None:
        await query.answer()
        await show_menu(query)

    # ------------------------------------------------- fundação (§15, §16)

    @router.callback_query(F.data == "guild:found")
    async def guild_found(query: CallbackQuery) -> None:
        if await service.my_guild(query.from_user.id) is not None:
            await query.answer(error_text("already_in_guild"), show_alert=True)
            return
        found_drafts[query.from_user.id] = {}
        await ask(query, "guild:found:name", render_found_name())

    @router.callback_query(F.data.startswith("guild:sym:"))
    async def guild_symbol(query: CallbackQuery) -> None:
        draft = found_drafts.get(query.from_user.id) or {}
        try:
            symbol = GUILD_SYMBOLS[int(_parts(query)[2])]
        except (IndexError, ValueError):
            symbol = None
        if symbol is None or "name" not in draft or "tag" not in draft:
            await stale(query)
            return
        draft["symbol"] = symbol
        await query.answer()
        await show(query, render_found_confirm(draft["name"], draft["tag"], symbol))

    @router.callback_query(F.data == "guild:foundok")
    async def guild_found_confirm(query: CallbackQuery) -> None:
        draft = found_drafts.get(query.from_user.id) or {}
        if not {"name", "tag", "symbol"} <= draft.keys():
            await stale(query)
            return
        try:
            await service.create_guild(
                query.from_user.id, draft["name"], draft["tag"], symbol=draft["symbol"]
            )
        except GuildError as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            return
        found_drafts.pop(query.from_user.id, None)
        await query.answer("Guilda fundada.")
        await show_menu(query)

    @router.message(F.text, HasPrompt("guild:found:"))
    async def guild_found_text(message: Message, prompt: PendingPrompt) -> None:
        actor = message.from_user.id
        text = (message.text or "").strip()
        await consume_reply(message)
        draft = found_drafts.setdefault(actor, {})
        PROMPTS.close(actor)
        try:
            if prompt.kind == "guild:found:name":
                draft["name"] = normalize_guild_name(text)
                message_id = await show_on_prompt(
                    message, prompt, render_found_tag(draft["name"]), images
                )
                PROMPTS.follow(actor, prompt, kind="guild:found:tag", message_id=message_id)
                return
            draft["tag"] = normalize_guild_tag(text)
        except GuildNameError as exc:
            screen = (
                render_found_name(error=error_text(exc.code))
                if prompt.kind == "guild:found:name"
                else render_found_tag(draft.get("name", ""), error=error_text(exc.code))
            )
            await reopen(message, prompt, screen)
            return
        await show_on_prompt(message, prompt, render_symbol_picker(), images)

    # ------------------------------------------------------- procurar (§12)

    @router.callback_query(F.data == "guild:search")
    async def guild_search(query: CallbackQuery) -> None:
        await ask(query, "guild:search", render_search_prompt())

    @router.message(F.text, HasPrompt("guild:search"))
    async def guild_search_text(message: Message, prompt: PendingPrompt) -> None:
        text = (message.text or "").strip()
        await consume_reply(message)
        PROMPTS.close(message.from_user.id)
        results = await service.search(text)
        screen = render_search_results(text[:32], results)
        if not results:
            await reopen(message, prompt, screen)
            return
        await show_on_prompt(message, prompt, screen, images)

    # ------------------------------------------------- Guildas (§10, §11)

    @router.callback_query(F.data.startswith("guild:browse:"))
    async def guild_browse(query: CallbackQuery) -> None:
        try:
            index = max(0, int(_parts(query)[-1]))
        except ValueError:
            await stale(query)
            return
        page = await service.recruiting(offset=index * PAGE_SIZE, limit=PAGE_SIZE)
        await query.answer()
        await show(query, render_browse(page, first=index == 0, page_index=index))

    async def pending_application_for(actor: int, guild_id: UUID) -> UUID | None:
        for item in await service.my_applications(actor):
            if item.guild_id == guild_id and item.status == "pending":
                return item.application_id
        return None

    async def show_public(query: CallbackQuery, guild_id: UUID, back: str) -> None:
        page = await service.public_page(guild_id)
        mine = await service.my_guild(query.from_user.id)
        pending = await pending_application_for(query.from_user.id, guild_id)
        await query.answer()
        await show(
            query,
            render_public_page(
                page, can_apply=mine is None, pending_application=pending, back=back
            ),
        )

    @router.callback_query(F.data.startswith("guild:page:"))
    async def guild_page(query: CallbackQuery) -> None:
        try:
            guild_id = unpack(_parts(query)[2])
        except (ValueError, IndexError):
            await stale(query)
            return
        await show_public(query, guild_id, "guild:root")

    @router.callback_query(F.data.startswith("guild:apply:"))
    async def guild_apply(query: CallbackQuery) -> None:
        try:
            guild_id = unpack(_parts(query)[2])
            await service.apply(query.from_user.id, guild_id)
        except GuildError as exc:
            await fail(query, exc)
            return
        except (ValueError, IndexError):
            await stale(query)
            return
        await query.answer("Inscrição enviada.")
        await show(query, render_my_applications(await service.my_applications(query.from_user.id)))

    # --------------------------------------------- inscrições próprias (§14)

    @router.callback_query(F.data.regexp(r"^guild:myapps(:\d+)?$"))
    async def guild_my_applications(query: CallbackQuery) -> None:
        parts = _parts(query)
        index = int(parts[2]) if len(parts) == 3 else 0
        await query.answer()
        applications = await service.my_applications(query.from_user.id)
        await show(query, render_my_applications(applications, page_index=index))

    @router.callback_query(F.data.startswith("guild:mapp:"))
    async def guild_my_application(query: CallbackQuery) -> None:
        try:
            application_id = unpack(_parts(query)[2])
        except (ValueError, IndexError):
            await stale(query)
            return
        item = next(
            (
                a
                for a in await service.my_applications(query.from_user.id)
                if a.application_id == application_id and a.status == "pending"
            ),
            None,
        )
        if item is None:
            await stale(query)
            return
        await show_public(query, item.guild_id, "guild:myapps")

    @router.callback_query(F.data.startswith("guild:cancelapp:"))
    async def guild_cancel_application(query: CallbackQuery) -> None:
        try:
            application_id = unpack(_parts(query)[2])
            await service.cancel_application(query.from_user.id, application_id)
        except GuildError as exc:
            await fail(query, exc)
            return
        except (ValueError, IndexError):
            await stale(query)
            return
        await query.answer("Inscrição cancelada.")
        applications = await service.my_applications(query.from_user.id)
        await show(query, render_my_applications(applications))

    # ------------------------------------------------------- convites (§13)

    @router.callback_query(F.data == "guild:inbox")
    async def guild_inbox(query: CallbackQuery) -> None:
        await query.answer()
        await show(query, render_inbox(await service.incoming_invites(query.from_user.id)))

    @router.callback_query(F.data.startswith("guild:invv:"))
    async def guild_invite_view(query: CallbackQuery) -> None:
        try:
            invite_id = unpack(_parts(query)[2])
        except (ValueError, IndexError):
            await stale(query)
            return
        invite = next(
            (i for i in await service.incoming_invites(query.from_user.id) if i.invite_id == invite_id),  # noqa: E501
            None,
        )
        if invite is None:
            await stale(query)
            return
        await query.answer()
        await show(query, render_invite(invite))

    @router.callback_query(F.data.startswith("guild:inv:"))
    async def guild_invite_response(query: CallbackQuery) -> None:
        parts = _parts(query)
        try:
            if len(parts) != 4 or parts[2] not in {"a", "d"}:
                raise ValueError("invalid callback")
            await service.respond_invite(
                query.from_user.id, unpack(parts[3]), accept=parts[2] == "a"
            )
        except GuildError as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            await show(query, render_inbox(await service.incoming_invites(query.from_user.id)))
            return
        except ValueError:
            await stale(query)
            return
        await query.answer("Convite aceito." if parts[2] == "a" else "Convite recusado.")
        if parts[2] == "a":
            await show_menu(query)
        else:
            await show(query, render_inbox(await service.incoming_invites(query.from_user.id)))

    # -------------------------------------------------- Gerenciar (§9.3)

    @router.callback_query(F.data.startswith("guild:mgmt:"))
    async def guild_manage(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        rename_drafts.pop(query.from_user.id, None)
        await query.answer()
        await show(query, render_manage(guild))

    @router.callback_query(F.data.startswith("guild:mem:"))
    async def guild_members(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        await query.answer()
        await show(query, render_members(guild))

    # --------------------------------------------------- Convidar (§9.4)

    @router.callback_query(F.data.startswith("guild:invite:"))
    async def guild_invite_prompt(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        if not _manager(guild):
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        await ask(query, "guild:invite", render_invite_prompt(guild))

    @router.message(F.text, HasPrompt("guild:invite"))
    async def guild_invite_text(message: Message, prompt: PendingPrompt) -> None:
        actor = message.from_user.id
        text = (message.text or "").strip()
        await consume_reply(message)
        PROMPTS.close(actor)
        guild = await service.my_guild(actor)
        if guild is None:
            await show_on_prompt(message, prompt, render_guild_menu(None), images)
            return
        found = await service.find_characters(text)
        if not found:
            screen = render_invite_prompt(guild, error=error_text("character_not_found"))
            await reopen(message, prompt, screen)
            return
        candidates[actor] = found
        await show_on_prompt(message, prompt, render_invite_candidates(guild, found), images)

    @router.callback_query(F.data.startswith("guild:invp:"))
    async def guild_invite_pick(query: CallbackQuery) -> None:
        parts = _parts(query)
        guild = await current_guild(query, parts[2]) if len(parts) == 4 else None
        try:
            character_id = unpack(parts[3]) if guild is not None else None
        except ValueError:
            character_id = None
        chosen = next(
            (c for c in candidates.get(query.from_user.id, ()) if c.character_id == character_id),
            None,
        )
        if guild is None or chosen is None:
            await stale(query)
            return
        await query.answer()
        await show(query, render_invite_candidates(guild, (chosen,)))

    @router.callback_query(F.data.startswith("guild:invc:"))
    async def guild_invite_send(query: CallbackQuery) -> None:
        parts = _parts(query)
        guild = await current_guild(query, parts[2]) if len(parts) == 4 else None
        if guild is None:
            await stale(query)
            return
        try:
            invite = await service.invite(
                query.from_user.id, "", target_character_id=unpack(parts[3])
            )
        except GuildError as exc:
            await fail(query, exc)
            return
        except ValueError:
            await stale(query)
            return
        candidates.pop(query.from_user.id, None)
        await query.answer(f"Convite enviado a {invite.invitee_name}.")
        await show(query, render_manage(guild))
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✉️ Convite", callback_data=f"guild:invv:{pack(invite.invite_id)}"
                    )
                ]
            ]
        )
        try:
            await query.bot.send_message(
                invite.invitee_telegram_id,
                f"✉️ {invite.inviter_name} convidou você para a Guilda "
                f"[{invite.guild_tag}] {invite.guild_name}.",
                reply_markup=keyboard,
            )
        except TelegramAPIError:
            # The invite is durable and still appears under Guilda → Convites.
            pass

    # ---------------------------------------------------- Recrutar (§9.5)

    @router.callback_query(F.data.startswith("guild:recruit:"))
    async def guild_recruit(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        await query.answer()
        await show(query, render_recruit(guild))

    @router.callback_query(F.data.startswith("guild:recr:"))
    async def guild_recruitment(query: CallbackQuery) -> None:
        parts = _parts(query)
        try:
            if len(parts) != 4 or parts[2] not in {"o", "c"}:
                raise ValueError("invalid callback")
            if await current_guild(query, parts[3]) is None:
                raise ValueError("stale guild")
            guild = await service.set_recruitment(
                query.from_user.id,
                Recruitment.OPEN if parts[2] == "o" else Recruitment.CLOSED,
            )
        except GuildError as exc:
            await fail(query, exc)
            return
        except ValueError:
            await stale(query)
            return
        await query.answer("Recrutamento aberto." if parts[2] == "o" else "Recrutamento fechado.")
        await show(query, render_recruit(guild))

    # ----------------------------------------- Inscrições recebidas (§9.6)

    async def show_received(query: CallbackQuery) -> None:
        guild = await service.my_guild(query.from_user.id)
        if guild is None:
            await show_menu(query)
            return
        try:
            applications = await service.received_applications(query.from_user.id)
        except GuildError:
            await show(query, render_manage(guild))
            return
        await show(query, render_received_applications(guild.guild_id, applications))

    @router.callback_query(F.data.startswith("guild:recv:"))
    async def guild_received(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        if not _manager(guild):
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        await query.answer()
        await show_received(query)

    @router.callback_query(F.data.startswith("guild:appv:"))
    async def guild_application_view(query: CallbackQuery) -> None:
        parts = _parts(query)
        guild = await current_guild(query, parts[2]) if len(parts) == 4 else None
        try:
            application_id = unpack(parts[3]) if guild is not None else None
            pending = await service.received_applications(query.from_user.id)
        except (GuildError, ValueError):
            await stale(query)
            return
        item = next((a for a in pending if a.application_id == application_id), None)
        if guild is None or item is None:
            await stale(query)
            return
        await query.answer()
        await show(query, render_application(guild.guild_id, item))

    @router.callback_query(F.data.startswith("guild:app:"))
    async def guild_review_application(query: CallbackQuery) -> None:
        parts = _parts(query)
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
            await show_received(query)
            return
        except ValueError:
            await stale(query)
            return
        await query.answer("Inscrição aceita." if parts[2] == "a" else "Inscrição recusada.")
        applicant = pending.get(application_id)
        if applicant is not None and applicant.character_telegram_id is not None:
            result = (
                "foi aceita. Você agora faz parte da Guilda."
                if parts[2] == "a"
                else "foi recusada."
            )
            try:
                await query.bot.send_message(
                    applicant.character_telegram_id,
                    f"📝 Sua Inscrição na Guilda [{guild.tag}] {guild.name} {result}",
                )
            except TelegramAPIError:
                pass
        await show_received(query)

    # ------------------------------------------------ cargos e membros

    async def member_action(query: CallbackQuery, parts: list[str]):
        """Parse `guild:<verb>:<guild>:<character>` and return (guild, character_id)."""
        if len(parts) != 4:
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
        if guild is None:
            await show_menu(query)
            return
        await show(query, render_members(guild))

    @router.callback_query(F.data.regexp(r"^guild:(pro|dem):"))
    async def guild_change_role(query: CallbackQuery) -> None:
        parts = _parts(query)
        parsed = await member_action(query, parts)
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
        parts = _parts(query)
        parsed = await member_action(query, parts)
        if parsed is None:
            await stale(query)
            return
        guild, character_id = parsed
        name = _name(guild, character_id)
        if parts[1] == "kick":
            text = f"Remover {name} da Guilda? Ele só poderá entrar em outra após 12 horas."
        else:
            text = f"Transferir a liderança para {name}? Você passará a ser Oficial."
        await query.answer()
        await show(
            query,
            render_confirm(
                text, f"guild:{parts[1]}ok:{parts[2]}:{parts[3]}", f"guild:mem:{parts[2]}"
            ),
        )

    @router.callback_query(F.data.regexp(r"^guild:(kick|lead)ok:"))
    async def guild_member_action_confirmed(query: CallbackQuery) -> None:
        parts = _parts(query)
        parsed = await member_action(query, parts)
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
        await query.answer(
            "Integrante removido." if parts[1] == "kickok" else "Liderança transferida."
        )
        await refresh_members(query)

    @router.callback_query(F.data.startswith("guild:leave:"))
    async def guild_leave_confirm(query: CallbackQuery) -> None:
        parts = _parts(query)
        guild = await current_guild(query, parts[-1])
        if guild is None:
            await stale(query)
            return
        if guild.viewer_role is GuildRole.LEADER:
            await query.answer(error_text("leader_must_transfer"), show_alert=True)
            return
        await query.answer()
        await show(
            query,
            render_confirm(
                f"Sair da Guilda {guild.name}? Você só poderá entrar em outra após 12 horas.",
                f"guild:leaveok:{parts[-1]}",
                f"guild:mem:{parts[-1]}",
            ),
        )

    @router.callback_query(F.data.startswith("guild:leaveok:"))
    async def guild_leave(query: CallbackQuery) -> None:
        if await current_guild(query, _parts(query)[-1]) is None:
            await stale(query)
            return
        try:
            await service.leave(query.from_user.id)
        except GuildError as exc:
            await fail(query, exc)
            return
        await query.answer("Você saiu da Guilda.")
        await show_menu(query)

    # -------------------------------------------------- Tesouraria (§9.7)

    @router.callback_query(F.data.startswith("guild:works:"))
    async def guild_treasury(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        await query.answer()
        await show(query, render_treasury(guild))

    @router.callback_query(F.data.startswith("guild:hist:"))
    async def guild_history(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        try:
            entries = await service.treasury_history(query.from_user.id)
        except GuildError as exc:
            await fail(query, exc)
            return
        await query.answer()
        await show(query, render_treasury_history(guild, entries))

    @router.callback_query(F.data.startswith("guild:dep:"))
    async def guild_deposit_screen(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        await query.answer()
        await show(query, render_deposit(guild))

    @router.callback_query(F.data.startswith("guild:depv:"))
    async def guild_deposit_preset(query: CallbackQuery) -> None:
        parts = _parts(query)
        if len(parts) != 4 or await current_guild(query, parts[2]) is None:
            await stale(query)
            return
        try:
            guild = await service.deposit(query.from_user.id, int(parts[3]))
        except GuildError as exc:
            await fail(query, exc)
            return
        except ValueError:
            await stale(query)
            return
        await query.answer(f"Depósito registrado: {parts[3]} Coroas.")
        await show(query, render_treasury(guild))

    @router.callback_query(F.data.startswith("guild:depq:"))
    async def guild_deposit_prompt(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        await ask(query, "guild:deposit", render_deposit_prompt(guild))

    @router.message(F.text, HasPrompt("guild:deposit"))
    async def guild_deposit_text(message: Message, prompt: PendingPrompt) -> None:
        actor = message.from_user.id
        amount = parse_crowns(message.text or "")
        await consume_reply(message)
        PROMPTS.close(actor)
        guild = await service.my_guild(actor)
        if guild is None:
            await show_on_prompt(message, prompt, render_guild_menu(None), images)
            return
        try:
            if amount is None:
                raise GuildError("invalid_amount")
            guild = await service.deposit(actor, amount)
        except GuildError as exc:
            await reopen(message, prompt, render_deposit_prompt(guild, error=error_text(exc.code)))
            return
        await show_on_prompt(message, prompt, render_treasury(guild), images)

    # ------------------------------------------------------- Obras (§9.8)

    @router.callback_query(F.data.startswith("guild:obras:"))
    async def guild_obras(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        await query.answer()
        await show(query, render_obras(guild))

    def _kind(value: str) -> ProjectKind | None:
        try:
            return ProjectKind(value)
        except ValueError:
            return None

    @router.callback_query(F.data.startswith("guild:obra:"))
    async def guild_obra(query: CallbackQuery) -> None:
        parts = _parts(query)
        guild = await current_guild(query, parts[2]) if len(parts) == 4 else None
        kind = _kind(parts[3]) if guild is not None else None
        if guild is None or kind is None:
            await stale(query)
            return
        await query.answer()
        await show(query, render_obra(guild, kind))

    @router.callback_query(F.data.startswith("guild:fin:"))
    async def guild_finance(query: CallbackQuery) -> None:
        """Financiar: abre a Obra em Financiamento (Líder) e pede a contribuição."""
        parts = _parts(query)
        guild = await current_guild(query, parts[2]) if len(parts) == 4 else None
        kind = _kind(parts[3]) if guild is not None else None
        if guild is None or kind is None:
            await stale(query)
            return
        project = next((p for p in guild.active_projects if p.kind is kind), None)
        if project is None:
            try:
                guild = await service.start_project(query.from_user.id, kind)
            except GuildError as exc:
                await fail(query, exc)
                return
            project = next((p for p in guild.active_projects if p.kind is kind), None)
        if project is None or project.status != "funding":
            await query.answer(error_text("project_not_funding"), show_alert=True)
            return
        await ask(query, "guild:fin", render_finance_prompt(guild, kind), kind=kind.value)

    @router.message(F.text, HasPrompt("guild:fin"))
    async def guild_finance_text(message: Message, prompt: PendingPrompt) -> None:
        actor = message.from_user.id
        amount = parse_crowns(message.text or "")
        await consume_reply(message)
        PROMPTS.close(actor)
        guild = await service.my_guild(actor)
        kind = _kind(prompt.data.get("kind", ""))
        if guild is None or kind is None:
            await show_on_prompt(message, prompt, render_guild_menu(guild), images)
            return
        project = next((p for p in guild.active_projects if p.kind is kind), None)
        try:
            if amount is None:
                raise GuildError("invalid_amount")
            if project is None:
                raise GuildError("project_not_funding")
            result = await service.contribute(
                actor, project.project_id, amount, from_treasury=finances_from_treasury(guild)
            )
        except GuildError as exc:
            await reopen(
                message, prompt, render_finance_prompt(guild, kind, error=error_text(exc.code))
            )
            return
        await show_on_prompt(message, prompt, render_obra(result.guild, kind), images)

    # --------------------------------------------------- Renomear (§9.11)

    @router.callback_query(F.data.startswith("guild:ren:"))
    async def guild_rename_prompt(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        if guild.viewer_role is not GuildRole.LEADER:
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        rename_drafts[query.from_user.id] = {}
        await ask(query, "guild:ren:name", render_rename_name(guild))

    @router.message(F.text, HasPrompt("guild:ren:"))
    async def guild_rename_text(message: Message, prompt: PendingPrompt) -> None:
        actor = message.from_user.id
        text = (message.text or "").strip()
        await consume_reply(message)
        PROMPTS.close(actor)
        guild = await service.my_guild(actor)
        if guild is None:
            await show_on_prompt(message, prompt, render_guild_menu(None), images)
            return
        draft = rename_drafts.setdefault(actor, {})
        try:
            if prompt.kind == "guild:ren:name":
                draft["name"] = normalize_guild_name(text)
                message_id = await show_on_prompt(
                    message, prompt, render_rename_tag(guild, draft["name"]), images
                )
                PROMPTS.follow(actor, prompt, kind="guild:ren:tag", message_id=message_id)
                return
            draft["tag"] = normalize_guild_tag(text)
        except GuildNameError as exc:
            screen = (
                render_rename_name(guild, error=error_text(exc.code))
                if prompt.kind == "guild:ren:name"
                else render_rename_tag(guild, draft.get("name", ""), error=error_text(exc.code))
            )
            await reopen(message, prompt, screen)
            return
        await show_on_prompt(
            message, prompt, render_rename_confirm(guild, draft["name"], draft["tag"]), images
        )

    @router.callback_query(F.data.startswith("guild:renok:"))
    async def guild_rename_confirm(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        draft = rename_drafts.get(query.from_user.id) or {}
        if guild is None or not {"name", "tag"} <= draft.keys():
            await stale(query)
            return
        try:
            await service.rename(
                query.from_user.id,
                name=None if draft["name"].casefold() == guild.name.casefold() else draft["name"],
                tag=None if draft["tag"] == guild.tag else draft["tag"],
            )
        except GuildError as exc:
            await fail(query, exc)
            return
        rename_drafts.pop(query.from_user.id, None)
        await query.answer("Guilda renomeada.")
        await show_menu(query)

    # -------------------------------------------------- Dissolver (§9.12)

    @router.callback_query(F.data.startswith("guild:diss:"))
    async def guild_dissolve_screen(query: CallbackQuery) -> None:
        guild = await current_guild(query, _parts(query)[-1])
        if guild is None:
            await stale(query)
            return
        if guild.viewer_role is not GuildRole.LEADER:
            await query.answer(error_text("no_permission"), show_alert=True)
            return
        await query.answer()
        await show(query, render_dissolve(guild))

    @router.callback_query(F.data.startswith("guild:dissok:"))
    async def guild_dissolve(query: CallbackQuery) -> None:
        if await current_guild(query, _parts(query)[-1]) is None:
            await stale(query)
            return
        try:
            await service.dissolve(query.from_user.id)
        except GuildError as exc:
            await fail(query, exc)
            return
        await query.answer("Guilda dissolvida.")
        await show_menu(query)

    return router

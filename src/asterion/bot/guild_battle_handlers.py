"""Telegram adapters for the Batalha de Guildas (GDD v1.6.0 §15, §39.4, §49.14)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.guild_battle import (
    GuildBattleError,
    GuildBattleFightView,
    GuildBattleHubView,
    GuildBattleNotice,
    GuildBattleOutcome,
    GuildBattleService,
)
from asterion.bot.combat_ui import GuildBattleCombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.guild_battle_ui import (
    Draft,
    error_text,
    fingerprint,
    render_cancel_confirm,
    render_draft,
    render_guild_battle,
    render_hub,
    render_review,
    render_standings,
    render_substitution,
)
from asterion.bot.guilds_ui import unpack
from asterion.bot.telegram_outbox import TelegramOutbox, enqueue_notices


async def deliver_guild_battle_notices(
    service: GuildBattleService, outbox: TelegramOutbox, notices: Iterable[GuildBattleNotice]
) -> None:
    """Best effort, after the notification categories: every screen can be reopened."""
    allowed = await service.deliverable(list(notices))
    await enqueue_notices(outbox, "guild_battle", allowed, render_guild_battle)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def guild_battle_router(
    service: GuildBattleService,
    images: dict[str, str],
    *,
    clock: Callable[[], datetime] = _utcnow,
) -> Router:
    router = Router(name="guild_battle")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, screen) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def fail(query: CallbackQuery, code: str) -> None:
        await query.answer(error_text(code), show_alert=True)

    async def show_hub(query: CallbackQuery) -> None:
        try:
            now = clock()
            hub = await service.hub(query.from_user.id, now=now)
        except GuildBattleError as error:
            await fail(query, error.code)
            return
        await show(query, render_hub(hub, now=now))

    async def finish(query: CallbackQuery, outcome: GuildBattleOutcome) -> None:
        await show(query, render_guild_battle(outcome.view))
        await deliver_guild_battle_notices(
            service, TelegramOutbox(service.sessions), outcome.notices
        )

    @router.message(CommandStart())
    @router.message(Command("menu"))
    async def resume_foreground(message: Message) -> None:
        if message.from_user is None:
            raise SkipHandler
        view = await service.foreground(message.from_user.id, now=clock())
        if view is None:
            raise SkipHandler
        await present(message, render_guild_battle(view), images)

    @router.callback_query(F.data == "gb:hub")
    async def hub(query: CallbackQuery) -> None:
        await show_hub(query)

    @router.callback_query(F.data == "gb:ref")
    async def refresh(query: CallbackQuery) -> None:
        view = await service.foreground(query.from_user.id, now=clock())
        if view is None:
            await show_hub(query)
            return
        await show(query, render_guild_battle(view))

    @router.callback_query(F.data == "gb:std")
    async def standings(query: CallbackQuery) -> None:
        try:
            hub = await service.hub(query.from_user.id, now=clock())
        except GuildBattleError:
            hub = None
        rows = await service.standings()
        eligible = await service.individual_reward_eligible(query.from_user.id)
        await show(
            query,
            render_standings(
                rows,
                own_guild=None if hub is None else hub.guild_name,
                individual_eligible=None if hub is None else eligible,
            ),
        )

    async def draft_of(query: CallbackQuery) -> tuple[GuildBattleHubView, Draft] | None:
        """Revalidate the Leader and the draft carried in the callback data."""
        try:
            hub = await service.hub(query.from_user.id, now=clock())
        except GuildBattleError as error:
            await fail(query, error.code)
            return None
        if not hub.is_leader:
            await fail(query, "no_permission")
            return None
        try:
            _, _, fp, packed = (query.data or "").split(":", 3)
            if fp != fingerprint(hub.candidates):
                raise LookupError
            draft = Draft.unpack(packed, len(hub.candidates))
        except LookupError:
            await query.answer(error_text("roster_changed"), show_alert=True)
            if isinstance(query.message, Message):
                await present(query.message, render_draft(hub, Draft()), images, edit=True)
            return None
        except ValueError:
            await fail(query, "invalid_roster")
            return None
        return hub, draft

    @router.callback_query(F.data.startswith("gb:d:"))
    async def draft(query: CallbackQuery) -> None:
        state = await draft_of(query)
        if state is not None:
            await show(query, render_draft(*state))

    @router.callback_query(F.data.startswith("gb:rv:"))
    async def review(query: CallbackQuery) -> None:
        state = await draft_of(query)
        if state is None:
            return
        hub, chosen = state
        if chosen.step != "reserve":
            await fail(query, "invalid_roster")
            return
        await show(query, render_review(hub, chosen))

    @router.callback_query(F.data.startswith("gb:reg:"))
    async def register(query: CallbackQuery) -> None:
        state = await draft_of(query)
        if state is None:
            return
        hub, chosen = state
        if chosen.champion is None:
            await fail(query, "invalid_roster")
            return
        ids = [item.character_id for item in hub.candidates]
        try:
            await service.register(
                query.from_user.id,
                front_1=tuple(ids[i] for i in chosen.front_1),
                front_2=tuple(ids[i] for i in chosen.front_2),
                champion=ids[chosen.champion],
                reserves=tuple(ids[i] for i in chosen.reserves),
                now=clock(),
            )
        except GuildBattleError as error:
            await fail(query, error.code)
            return
        await show_hub(query)

    @router.callback_query(F.data == "gb:cx")
    async def cancel_confirm(query: CallbackQuery) -> None:
        await show(query, render_cancel_confirm())

    @router.callback_query(F.data == "gb:cxok")
    async def cancel(query: CallbackQuery) -> None:
        try:
            await service.cancel_registration(query.from_user.id, now=clock())
        except GuildBattleError as error:
            await fail(query, error.code)
            return
        await show_hub(query)

    @router.callback_query(F.data == "gb:ok")
    async def confirm(query: CallbackQuery) -> None:
        try:
            await service.confirm(query.from_user.id, now=clock())
        except GuildBattleError as error:
            await fail(query, error.code)
            return
        await show_hub(query)

    async def leader_registration(query: CallbackQuery):
        try:
            hub = await service.hub(query.from_user.id, now=clock())
        except GuildBattleError as error:
            await fail(query, error.code)
            return None
        if not hub.is_leader:
            await fail(query, "no_permission")
            return None
        if hub.registration is None or hub.registration.status != "paired":
            await fail(query, "not_paired")
            return None
        return hub.registration

    @router.callback_query(F.data == "gb:sub")
    async def substitution(query: CallbackQuery) -> None:
        registration = await leader_registration(query)
        if registration is not None:
            await show(query, render_substitution(registration, None))

    @router.callback_query(F.data.startswith("gb:sb:"))
    async def substitution_reserve(query: CallbackQuery) -> None:
        registration = await leader_registration(query)
        if registration is None:
            return
        try:
            character_id = unpack((query.data or "").rsplit(":", 1)[1])
        except (IndexError, ValueError):
            await fail(query, "invalid_substitution")
            return
        replaced = next(
            (row for row in registration.roster if row.character_id == character_id), None
        )
        if replaced is None or replaced.slot == "reserve" or replaced.confirmed:
            await fail(query, "invalid_substitution")
            return
        await show(query, render_substitution(registration, replaced))

    @router.callback_query(F.data.startswith("gb:sbok:"))
    async def substitute(query: CallbackQuery) -> None:
        try:
            _, _, out, reserve = (query.data or "").split(":")
            replaced_id, reserve_id = unpack(out), unpack(reserve)
        except ValueError:
            await fail(query, "invalid_substitution")
            return
        try:
            await service.substitute(query.from_user.id, replaced_id, reserve_id, now=clock())
        except GuildBattleError as error:
            await fail(query, error.code)
            return
        await show_hub(query)

    @router.callback_query(GuildBattleCombatCallback.filter())
    async def fight(query: CallbackQuery, callback_data: GuildBattleCombatCallback) -> None:
        now = clock()
        view = await service.foreground(query.from_user.id, now=now)
        if (
            not isinstance(view, GuildBattleFightView)
            or view.battle.activity_id.hex != callback_data.activity
        ):
            if view is None:
                await fail(query, "not_found")
            else:
                await show(query, render_guild_battle(view))
            return
        try:
            outcome = await service.action(
                query.from_user.id,
                view.fight_id,
                callback_data.combat_version,
                callback_data.action_index,
                callback_data.target,
                now=now,
            )
        except GuildBattleError as error:
            await fail(query, error.code)
            return
        await finish(query, outcome)

    return router

"""Telegram callbacks for persistent Cripta dungeon runs."""

from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.dungeons import DungeonService
from asterion.bot.combat_ui import DungeonCombatCallback, class_trial_action_ids
from asterion.bot.creation_handlers import present
from asterion.bot.dungeon_ui import render_dungeon_targets, render_dungeons
from asterion.domain.combat import action_target_ids


def dungeon_router(service: DungeonService, images: dict[str, str]) -> Router:
    router = Router(name="dungeons")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view):
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_dungeons(view), images, edit=True)

    @router.callback_query(F.data == "dungeon:known")
    async def known(query: CallbackQuery):
        await show(query, await service.known(query.from_user.id))

    @router.callback_query(F.data == "dungeon:crypt")
    async def detail(query: CallbackQuery):
        await show(query, await service.detail(query.from_user.id))

    @router.callback_query(F.data.startswith("dungeon:start:"))
    async def start(query: CallbackQuery):
        suffix = (query.data or "").rsplit(":", 1)[-1]
        if suffix not in {"s", "f"}:
            await show(query, await service.detail(query.from_user.id))
            return
        difficulty = "stable" if suffix == "s" else "fractured"
        await show(query, await service.start_solo(query.from_user.id, difficulty))

    @router.callback_query(F.data.startswith("dungeon:e:"))
    async def enter(query: CallbackQuery):
        try:
            _, _, run_id, version = (query.data or "").split(":")
            view = await service.begin_encounter(query.from_user.id, UUID(hex=run_id), int(version))
        except (ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:b:"))
    async def brazier(query: CallbackQuery):
        try:
            _, _, run_id, version = (query.data or "").split(":")
            view = await service.activate_brazier(
                query.from_user.id, UUID(hex=run_id), int(version)
            )
        except (ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:r:"))
    async def retry(query: CallbackQuery):
        try:
            _, _, run_id, version = (query.data or "").split(":")
            view = await service.retry(query.from_user.id, UUID(hex=run_id), int(version))
        except (ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:confirm:"))
    async def confirm_abandon(query: CallbackQuery):
        try:
            view = await service.resume(query.from_user.id)
            if view is not None and view.run_id is not None:
                from dataclasses import replace

                run_id = (query.data or "").split(":")[2]
                version = int((query.data or "").split(":")[3])
                if view.run_id.hex == run_id and view.state_version == version:
                    view = replace(view, kind="confirm_abandon")
        except (ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:a:"))
    async def abandon(query: CallbackQuery):
        try:
            _, _, run_id, version = (query.data or "").split(":")
            view = await service.abandon(query.from_user.id, UUID(hex=run_id), int(version))
        except (ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:back:"))
    async def back(query: CallbackQuery):
        await show(query, await service.resume(query.from_user.id))

    @router.callback_query(F.data == "dungeon:noop")
    async def unavailable(query: CallbackQuery):
        await query.answer("Esta dificuldade ainda não está disponível.")

    @router.callback_query(F.data.startswith("df:"))
    async def fight(query: CallbackQuery):
        try:
            data = DungeonCombatCallback.unpack(query.data or "")
            view = await service.resume(query.from_user.id)
            if (
                view is None
                or view.kind != "combat"
                or view.run_id is None
                or view.activity_id is None
                or view.run_id.hex[:16] != data.run
                or view.activity_id != data.activity_id
                or view.combat.version != data.combat_version
            ):
                pass
            elif data.target == "b":
                pass
            else:
                actions = class_trial_action_ids(view.combat)
                if not 0 <= data.action_index < len(actions):
                    view = await service.resume(query.from_user.id)
                else:
                    action_id = actions[data.action_index]
                    definition = view.combat.player_actions.get(action_id)
                    targets = (
                        ()
                        if definition is None
                        or definition.target_mode in {"self", "all_opponents", "all_allies"}
                        else action_target_ids(view.combat, action_id)
                    )
                    if data.target == "s":
                        if len(targets) > 1 and isinstance(query.message, Message):
                            await query.answer()
                            await present(
                                query.message,
                                render_dungeon_targets(view, data.action_index),
                                images,
                                edit=True,
                            )
                            return
                        view = await service.resume(query.from_user.id)
                    elif data.target == "x":
                        view = (
                            await service.action(
                                query.from_user.id,
                                view.run_id,
                                view.activity_id,
                                data.combat_version,
                                action_id,
                            )
                            if not targets
                            else await service.resume(query.from_user.id)
                        )
                    elif data.target.startswith("d"):
                        target_index = data.target_index
                        if target_index is None or not 0 <= target_index < len(targets):
                            view = await service.resume(query.from_user.id)
                        else:
                            view = await service.action(
                                query.from_user.id,
                                view.run_id,
                                view.activity_id,
                                data.combat_version,
                                action_id,
                                targets[target_index],
                            )
                    else:
                        view = await service.resume(query.from_user.id)
        except (KeyError, ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_dungeons(view), images, edit=True)

    return router

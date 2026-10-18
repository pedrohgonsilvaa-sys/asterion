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
    router.message.filter(F.chat.type == "private")

    async def show(query: CallbackQuery, view):
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_dungeons(view), images, edit=True)

    @router.callback_query(F.data == "dungeon:known")
    async def known(query: CallbackQuery):
        await show(query, await service.known(query.from_user.id))

    @router.callback_query(F.data == "dungeon:crypt")
    async def detail(query: CallbackQuery):
        await show(query, await service.detail(query.from_user.id, "dungeon.tdo.cripta_ocaso"))

    @router.callback_query(F.data == "dungeon:galleries")
    async def galleries(query: CallbackQuery):
        await show(
            query,
            await service.detail(query.from_user.id, "dungeon.tdo.galerias_vigia"),
        )

    @router.callback_query(F.data == "dungeon:fosso")
    async def fosso(query: CallbackQuery):
        await show(query, await service.detail(query.from_user.id, "dungeon.vde.fosso_raizes"))

    @router.callback_query(F.data == "dungeon:sanctuary")
    async def sanctuary(query: CallbackQuery):
        await show(
            query,
            await service.detail(query.from_user.id, "dungeon.vde.santuario_no_antigo"),
        )

    @router.callback_query(F.data == "dungeon:nareth-galleries")
    async def nareth_galleries(query: CallbackQuery):
        await show(
            query,
            await service.detail(query.from_user.id, "dungeon.nareth.galerias_meridiano"),
        )

    @router.callback_query(F.data == "dungeon:nareth-observatory")
    async def nareth_observatory(query: CallbackQuery):
        await show(
            query,
            await service.detail(query.from_user.id, "dungeon.nareth.observatorio_afundado"),
        )

    @router.callback_query(F.data == "dungeon:varzeas-infirmary")
    async def varzeas_infirmary(query: CallbackQuery):
        await show(
            query,
            await service.detail(query.from_user.id, "dungeon.varzeas.enfermaria_afundada"),
        )

    @router.callback_query(F.data == "dungeon:varzeas-cistern")
    async def varzeas_cistern(query: CallbackQuery):
        await show(
            query,
            await service.detail(query.from_user.id, "dungeon.varzeas.cisterna_transferencia"),
        )

    @router.callback_query(F.data == "dungeon:altos-pedreira")
    async def altos_pedreira(query: CallbackQuery):
        await show(
            query,
            await service.detail(
                query.from_user.id, "dungeon.altos.pedreira_contrapeso"
            ),
        )

    @router.callback_query(F.data.startswith("dungeon:group:"))
    async def prepare_group(query: CallbackQuery):
        try:
            _, _, family_key, difficulty_key = (query.data or "").split(":")
            family = {
                "c": "dungeon.tdo.cripta_ocaso",
                "g": "dungeon.tdo.galerias_vigia",
                "f": "dungeon.vde.fosso_raizes",
                "s": "dungeon.vde.santuario_no_antigo",
                "n": "dungeon.nareth.galerias_meridiano",
                "o": "dungeon.nareth.observatorio_afundado",
                "i": "dungeon.varzeas.enfermaria_afundada",
                "t": "dungeon.varzeas.cisterna_transferencia",
                "p": "dungeon.altos.pedreira_contrapeso",
            }[family_key]
            difficulty = {"s": "stable", "f": "fractured", "r": "rupture"}[
                difficulty_key
            ]
            view = await service.prepare_group(query.from_user.id, family, difficulty)
        except (KeyError, ValueError, TypeError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:queue:"))
    async def queue(query: CallbackQuery):
        try:
            _, _, family_key, difficulty_key = (query.data or "").split(":")
            family = {
                "c": "dungeon.tdo.cripta_ocaso",
                "g": "dungeon.tdo.galerias_vigia",
                "f": "dungeon.vde.fosso_raizes",
                "s": "dungeon.vde.santuario_no_antigo",
                "n": "dungeon.nareth.galerias_meridiano",
                "o": "dungeon.nareth.observatorio_afundado",
                "i": "dungeon.varzeas.enfermaria_afundada",
                "t": "dungeon.varzeas.cisterna_transferencia",
                "p": "dungeon.altos.pedreira_contrapeso",
            }[family_key]
            difficulty = {"s": "stable", "f": "fractured", "r": "rupture"}[
                difficulty_key
            ]
            view = await service.join_matchmaking(
                query.from_user.id, family, difficulty
            )
        except (KeyError, ValueError, TypeError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:ready:"))
    async def ready_check(query: CallbackQuery):
        try:
            _, _, lobby_id, version = (query.data or "").split(":")
            view = await service.open_entry_confirmation(
                query.from_user.id, UUID(hex=lobby_id), int(version)
            )
        except (ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:conf:"))
    async def confirm_entry(query: CallbackQuery):
        try:
            _, _, lobby_id, version, answer = (query.data or "").split(":")
            view = await service.confirm_entry(
                query.from_user.id,
                UUID(hex=lobby_id),
                int(version),
                confirm=answer == "y",
            )
        except (ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:inv:"))
    async def respond_invite(query: CallbackQuery):
        try:
            _, _, invite_id, answer = (query.data or "").split(":")
            view = await service.respond_invite(
                query.from_user.id, UUID(hex=invite_id), accept=answer == "y"
            )
        except (ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.callback_query(F.data.startswith("dungeon:cancel:"))
    async def cancel_lobby(query: CallbackQuery):
        try:
            _, _, lobby_id, version = (query.data or "").split(":")
            view = await service.cancel_queue_or_lobby(
                query.from_user.id, UUID(hex=lobby_id), int(version)
            )
        except (ValueError, TypeError, IndexError):
            view = await service.resume(query.from_user.id)
        await show(query, view)

    @router.message(F.text.startswith("/dungeon_invite"))
    async def invite_by_character_name(message: Message):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) != 2 or not parts[1].strip():
            await message.answer("Use: /dungeon_invite Nome exato do personagem")
            return
        view = await service.invite_active_lobby_by_name(
            message.from_user.id, parts[1].strip()
        )
        await present(message, render_dungeons(view), images)

    @router.callback_query(F.data.startswith("dungeon:start:"))
    async def start(query: CallbackQuery):
        pieces = (query.data or "").split(":")
        if len(pieces) == 3 and pieces[2] in {"s", "f", "r"}:
            # Legacy callback shape belongs to the original Crypt dungeon.
            family = "dungeon.tdo.cripta_ocaso"
            suffix = pieces[2]
        elif len(pieces) == 4:
            family = {
                "c": "dungeon.tdo.cripta_ocaso",
                "g": "dungeon.tdo.galerias_vigia",
                "f": "dungeon.vde.fosso_raizes",
                "s": "dungeon.vde.santuario_no_antigo",
                "n": "dungeon.nareth.galerias_meridiano",
                "o": "dungeon.nareth.observatorio_afundado",
                "i": "dungeon.varzeas.enfermaria_afundada",
                "t": "dungeon.varzeas.cisterna_transferencia",
                "p": "dungeon.altos.pedreira_contrapeso",
            }.get(pieces[2])
            suffix = pieces[3]
        else:
            await show(query, await service.resume(query.from_user.id))
            return
        if family is None or suffix not in {"s", "f", "r"}:
            await show(query, await service.resume(query.from_user.id))
            return
        difficulty = {"s": "stable", "f": "fractured", "r": "rupture"}[suffix]
        await show(
            query,
            await service.start_solo(query.from_user.id, difficulty, family),
        )

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
                actor_key = view.combat_actor_key
                actions = class_trial_action_ids(view.combat, actor_key=actor_key)
                if not 0 <= data.action_index < len(actions):
                    view = await service.resume(query.from_user.id)
                else:
                    action_id = actions[data.action_index]
                    from asterion.domain.combat import player_actions_for

                    definition = player_actions_for(view.combat, actor_key).get(action_id)
                    targets = (
                        ()
                        if definition is None
                        or definition.target_mode in {"self", "all_opponents", "all_allies"}
                        else action_target_ids(
                            view.combat, action_id, actor_key=actor_key or "player"
                        )
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

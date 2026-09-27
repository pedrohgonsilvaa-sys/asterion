"""Intent-only aiogram adapter for authoritative Foreground combat."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.p2 import P2Service
from asterion.application.prologue import PrologueService
from asterion.application.road import RoadService
from asterion.application.world import WorldService
from asterion.bot.combat_ui import (
    CombatCallback,
    CombatConsumableCallback,
    CombatConsumableFlowCallback,
    P2CombatCallback,
    render_combat,
)
from asterion.bot.creation_handlers import present
from asterion.bot.p2_ui import render_p2
from asterion.bot.road_ui import render_road
from asterion.bot.world_ui import render_world


def combat_router(
    service: PrologueService,
    images: dict[str, str],
    world: WorldService | None = None,
    road: RoadService | None = None,
    p2: P2Service | None = None,
) -> Router:
    router = Router(name="foreground_combat")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data == "prologue:continue")
    async def enter(query: CallbackQuery):
        view = await service.enter(query.from_user.id)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            if road and hasattr(view, "kind"):
                await present(query.message, render_road(view), images, edit=True)
                return
            world_view = await world.resume(query.from_user.id) if world else None
            screen = (
                render_world(world_view)
                if world_view
                else render_road(view)
                if road and hasattr(view, "kind")
                else render_combat(view)
            )
            await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data.startswith("fight:"))
    async def action(query: CallbackQuery):
        try:
            data = CombatCallback.unpack(query.data or "")
            activity_id = data.activity_id
        except (KeyError, ValueError, TypeError):
            await query.answer()
            return
        view = (
            await road.action(query.from_user.id, activity_id, data.version, data.action)
            if road
            else None
        )
        if view is None:
            view = await service.action(query.from_user.id, activity_id, data.version, data.action)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            if road is not None and hasattr(view, "kind"):
                await present(query.message, render_road(view), images, edit=True)
                return
            world_view = await world.resume(query.from_user.id) if world else None
            await present(
                query.message,
                render_world(world_view) if world_view else render_combat(view),
                images,
                edit=True,
            )

    @router.callback_query(F.data.startswith("p2fight:"))
    async def p2_action(query: CallbackQuery):
        if p2 is None:
            await query.answer()
            return
        try:
            data = P2CombatCallback.unpack(query.data or "")
        except (KeyError, ValueError, TypeError):
            await query.answer()
            return
        view = await p2.action(
            query.from_user.id,
            data.activity_id,
            data.version,
            data.action,
        )
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p2(view), images, edit=True)

    @router.callback_query(F.data.startswith("cu:"))
    async def consumable(query: CallbackQuery):
        try:
            data = CombatConsumableCallback.unpack(query.data or "")
            activity_id = data.activity_id
            item_id = data.item_id
            target_id = data.target_id
            effect_id = data.effect_id
        except (KeyError, ValueError, TypeError):
            await query.answer()
            return
        view = (
            await road.action(
                query.from_user.id,
                activity_id,
                data.state_version,
                consumable_id=item_id,
                target_id=target_id,
                effect_id=effect_id,
            )
            if road
            else None
        )
        if view is None and p2 is not None:
            view = await p2.action(
                query.from_user.id,
                activity_id,
                data.state_version,
                consumable_id=item_id,
                target_id=target_id,
                effect_id=effect_id,
            )
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            if getattr(view, "context", None) == "p2":
                await present(query.message, render_p2(view), images, edit=True)
                return
            if hasattr(view, "kind"):
                await present(query.message, render_road(view), images, edit=True)
                return
            await present(query.message, render_combat(view), images, edit=True)

    @router.callback_query(F.data.startswith("cf:"))
    async def consumable_flow(query: CallbackQuery):
        if (road is None and p2 is None) or not isinstance(query.message, Message):
            await query.answer()
            return
        try:
            data = CombatConsumableFlowCallback.unpack(query.data or "")
            activity_id = data.activity_id
            item_id = data.item_id
            target_id = data.target_id
            effect_id = data.effect_id
        except (KeyError, ValueError, TypeError):
            await query.answer()
            return

        view = None
        if data.step == "o":
            if road is not None:
                view = await road.consumable_selection(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    screen="items",
                )
            if view is None and p2 is not None:
                view = await p2.consumable_selection(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    screen="items",
                )
        elif data.step == "i" and item_id is not None:
            if road is not None:
                view = await road.consumable_selection(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    screen="choose_item",
                    item_id=item_id,
                )
            if view is None and p2 is not None:
                view = await p2.consumable_selection(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    screen="choose_item",
                    item_id=item_id,
                )
            option = getattr(view, "ready_consumable_option", None)
            if option is not None:
                if getattr(view, "context", None) == "p2" and p2 is not None:
                    view = await p2.action(
                        query.from_user.id,
                        activity_id,
                        data.state_version,
                        consumable_id=option.item_id,
                        target_id=option.target_id,
                        effect_id=option.effect_id,
                    )
                elif road is not None:
                    view = await road.action(
                        query.from_user.id,
                        activity_id,
                        data.state_version,
                        consumable_id=option.item_id,
                        target_id=option.target_id,
                        effect_id=option.effect_id,
                    )
        elif data.step == "t" and item_id is not None and target_id is not None:
            if road is not None:
                view = await road.consumable_selection(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    screen="choose_target",
                    item_id=item_id,
                    target_id=target_id,
                )
            if view is None and p2 is not None:
                view = await p2.consumable_selection(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    screen="choose_target",
                    item_id=item_id,
                    target_id=target_id,
                )
            option = getattr(view, "ready_consumable_option", None)
            if option is not None:
                if getattr(view, "context", None) == "p2" and p2 is not None:
                    view = await p2.action(
                        query.from_user.id,
                        activity_id,
                        data.state_version,
                        consumable_id=option.item_id,
                        target_id=option.target_id,
                        effect_id=option.effect_id,
                    )
                elif road is not None:
                    view = await road.action(
                        query.from_user.id,
                        activity_id,
                        data.state_version,
                        consumable_id=option.item_id,
                        target_id=option.target_id,
                        effect_id=option.effect_id,
                    )
        elif data.step == "e" and item_id is not None and target_id is not None and effect_id:
            if road is not None:
                view = await road.action(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    consumable_id=item_id,
                    target_id=target_id,
                    effect_id=effect_id,
                )
            if view is None and p2 is not None:
                view = await p2.action(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    consumable_id=item_id,
                    target_id=target_id,
                    effect_id=effect_id,
                )
        elif data.step == "b":
            screen = data.parent_screen or "combat"
            if road is not None:
                view = await road.consumable_selection(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    screen=screen,
                    item_id=item_id,
                    target_id=target_id,
                )
            if view is None and p2 is not None:
                view = await p2.consumable_selection(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    screen=screen,
                    item_id=item_id,
                    target_id=target_id,
                )

        await query.answer()
        if view is not None:
            screen = (
                render_p2(view)
                if getattr(view, "context", None) == "p2"
                else render_road(view)
                if hasattr(view, "kind")
                else render_combat(view)
            )
            await present(query.message, screen, images, edit=True)

    return router

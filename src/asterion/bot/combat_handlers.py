"""Intent-only aiogram adapter for authoritative Foreground combat."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.p2 import P2Service
from asterion.application.p3 import P3Service
from asterion.application.p4 import P4Service
from asterion.application.prologue import PrologueService
from asterion.application.road import RoadService
from asterion.application.s2 import S2Service
from asterion.application.s3 import S3Service
from asterion.application.s4 import S4Service
from asterion.application.s5 import S5Service
from asterion.application.world import WorldService
from asterion.bot.combat_ui import (
    CombatCallback,
    CombatConsumableCallback,
    CombatConsumableFlowCallback,
    P2CombatCallback,
    P3CombatCallback,
    P4CombatCallback,
    S2CombatCallback,
    S3CombatCallback,
    render_combat,
)
from asterion.bot.creation_handlers import present
from asterion.bot.p2_ui import render_p2
from asterion.bot.p3_ui import render_p3
from asterion.bot.p4_ui import render_p4
from asterion.bot.road_ui import render_road
from asterion.bot.s2_ui import render_s2
from asterion.bot.s3_ui import render_s3
from asterion.bot.s4_ui import render_s4
from asterion.bot.s5_ui import render_s5
from asterion.bot.world_ui import render_world


def combat_router(
    service: PrologueService,
    images: dict[str, str],
    world: WorldService | None = None,
    road: RoadService | None = None,
    p2: P2Service | None = None,
    s2: S2Service | None = None,
    p3: P3Service | None = None,
    s3: S3Service | None = None,
    p4: P4Service | None = None,
    s4: S4Service | None = None,
    s5: S5Service | None = None,
) -> Router:
    router = Router(name="foreground_combat")
    router.callback_query.filter(F.message.chat.type == "private")

    async def consumable_action(actor, activity_id, version, *, item_id, target_id, effect_id):
        view = (
            await road.action(
                actor,
                activity_id,
                version,
                consumable_id=item_id,
                target_id=target_id,
                effect_id=effect_id,
            )
            if road is not None
            else None
        )
        if view is None and s2 is not None:
            view = await s2.action(
                actor,
                activity_id,
                version,
                consumable_id=item_id,
                target_id=target_id,
                effect_id=effect_id,
            )
        if view is None and p2 is not None:
            view = await p2.action(
                actor,
                activity_id,
                version,
                consumable_id=item_id,
                target_id=target_id,
                effect_id=effect_id,
            )
        if view is None and p3 is not None:
            view = await p3.action(
                actor,
                activity_id,
                version,
                consumable_id=item_id,
                target_id=target_id,
                effect_id=effect_id,
            )
        if view is None and s3 is not None:
            view = await s3.action(
                actor, activity_id, version, consumable_id=item_id,
                target_id=target_id, effect_id=effect_id,
            )
        if view is None and p4 is not None:
            view = await p4.action_combat(
                actor, activity_id, version, consumable_id=item_id,
                target_id=target_id, effect_id=effect_id,
            )
        if view is None and s4 is not None:
            view = await s4.action_combat(
                actor, activity_id, version, consumable_id=item_id,
                target_id=target_id, effect_id=effect_id,
            )
        if view is None and s5 is not None:
            view = await s5.action_combat(
                actor, activity_id, version, consumable_id=item_id,
                target_id=target_id, effect_id=effect_id,
            )
        return view

    async def consumable_selection(actor, activity_id, version, **kwargs):
        view = (
            await road.consumable_selection(actor, activity_id, version, **kwargs)
            if road is not None
            else None
        )
        if view is None and s2 is not None:
            view = await s2.consumable_selection(
                actor, activity_id, version, **kwargs
            )
        if view is None and p2 is not None:
            view = await p2.consumable_selection(
                actor, activity_id, version, **kwargs
            )
        if view is None and p3 is not None:
            view = await p3.consumable_selection(
                actor, activity_id, version, **kwargs
            )
        if view is None and s3 is not None:
            view = await s3.consumable_selection(actor, activity_id, version, **kwargs)
        if view is None and p4 is not None:
            view = await p4.consumable_selection(actor, activity_id, version, **kwargs)
        if view is None and s4 is not None:
            view = await s4.consumable_selection(actor, activity_id, version, **kwargs)
        if view is None and s5 is not None:
            view = await s5.consumable_selection(actor, activity_id, version, **kwargs)
        return view

    def render_service_view(view):
        if getattr(view, "context", None) == "s2":
            return render_s2(view)
        if getattr(view, "context", None) == "p2":
            return render_p2(view)
        if getattr(view, "context", None) == "p3":
            return render_p3(view)
        if getattr(view, "context", None) == "s3":
            return render_s3(view)
        if getattr(view, "context", None) == "p4":
            return render_p4(view)
        if getattr(view, "context", None) == "s4":
            return render_s4(view)
        if getattr(view, "context", None) == "s5":
            return render_s5(view)
        if hasattr(view, "kind"):
            return render_road(view)
        return render_combat(view)

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
            activity_id = data.activity_id
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await p2.action(
            query.from_user.id,
            activity_id,
            data.version,
            data.action,
        )
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p2(view), images, edit=True)

    @router.callback_query(F.data.startswith("s2fight:"))
    async def s2_action(query: CallbackQuery):
        if s2 is None:
            await query.answer()
            return
        try:
            data = S2CombatCallback.unpack(query.data or "")
            activity_id = data.activity_id
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await s2.action(
            query.from_user.id,
            activity_id,
            data.version,
            data.action,
        )
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s2(view), images, edit=True)

    @router.callback_query(F.data.startswith("p3fight:"))
    async def p3_action(query: CallbackQuery):
        if p3 is None:
            await query.answer()
            return
        try:
            data = P3CombatCallback.unpack(query.data or "")
            activity_id = data.activity_id
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await p3.action(
            query.from_user.id,
            activity_id,
            data.version,
            data.action,
        )
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p3(view), images, edit=True)

    @router.callback_query(F.data.startswith("s3fight:"))
    async def s3_action(query: CallbackQuery):
        if s3 is None:
            await query.answer()
            return
        try:
            data = S3CombatCallback.unpack(query.data or "")
            activity_id = data.activity_id
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await s3.action(query.from_user.id, activity_id, data.version, data.action)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s3(view), images, edit=True)

    @router.callback_query(F.data.startswith("p4fight:"))
    async def p4_action(query: CallbackQuery):
        if p4 is None:
            await query.answer()
            return
        try:
            data = P4CombatCallback.unpack(query.data or "")
            activity_id = data.activity_id
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await p4.action_combat(query.from_user.id, activity_id, data.version, data.action)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p4(view), images, edit=True)

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
        view = await consumable_action(
            query.from_user.id,
            activity_id,
            data.state_version,
            item_id=item_id,
            target_id=target_id,
            effect_id=effect_id,
        )
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_service_view(view), images, edit=True)

    @router.callback_query(F.data.startswith("cf:"))
    async def consumable_flow(query: CallbackQuery):
        if (
            (
                road is None
                and p2 is None
                and s2 is None
                and p3 is None
                and s3 is None
                and p4 is None
                and s4 is None
                and s5 is None
            )
            or not isinstance(query.message, Message)
        ):
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
            view = await consumable_selection(
                query.from_user.id,
                activity_id,
                data.state_version,
                screen="items",
            )
        elif data.step == "i" and item_id is not None:
            view = await consumable_selection(
                query.from_user.id,
                activity_id,
                data.state_version,
                screen="choose_item",
                item_id=item_id,
            )
            option = getattr(view, "ready_consumable_option", None)
            if option is not None:
                view = await consumable_action(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    item_id=option.item_id,
                    target_id=option.target_id,
                    effect_id=option.effect_id,
                )
        elif data.step == "t" and item_id is not None and target_id is not None:
            view = await consumable_selection(
                query.from_user.id,
                activity_id,
                data.state_version,
                screen="choose_target",
                item_id=item_id,
                target_id=target_id,
            )
            option = getattr(view, "ready_consumable_option", None)
            if option is not None:
                view = await consumable_action(
                    query.from_user.id,
                    activity_id,
                    data.state_version,
                    item_id=option.item_id,
                    target_id=option.target_id,
                    effect_id=option.effect_id,
                )
        elif data.step == "e" and item_id is not None and target_id is not None and effect_id:
            view = await consumable_action(
                query.from_user.id,
                activity_id,
                data.state_version,
                item_id=item_id,
                target_id=target_id,
                effect_id=effect_id,
            )
        elif data.step == "b":
            screen = data.parent_screen or "combat"
            view = await consumable_selection(
                query.from_user.id,
                activity_id,
                data.state_version,
                screen=screen,
                item_id=item_id,
                target_id=target_id,
            )

        await query.answer()
        if view is not None:
            await present(query.message, render_service_view(view), images, edit=True)

    return router

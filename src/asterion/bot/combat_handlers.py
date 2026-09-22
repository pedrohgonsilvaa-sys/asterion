"""Intent-only aiogram adapter for authoritative Foreground combat."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.prologue import PrologueService
from asterion.application.road import RoadService
from asterion.application.world import WorldService
from asterion.bot.combat_ui import CombatCallback, render_combat
from asterion.bot.creation_handlers import present
from asterion.bot.road_ui import render_road
from asterion.bot.world_ui import render_world


def combat_router(
    service: PrologueService,
    images: dict[str, str],
    world: WorldService | None = None,
    road: RoadService | None = None,
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

    return router

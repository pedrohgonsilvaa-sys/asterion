# ruff: noqa: E501
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.consumables import ConsumableService
from asterion.application.inventory import InventoryService
from asterion.application.p1 import P1Service
from asterion.application.p2 import CHARNECA, P2Service
from asterion.application.p3 import P3Service
from asterion.application.p4 import P4Service
from asterion.application.prologue import PrologueService
from asterion.application.road import BOSQUE, REFUGE, ROAD, RUINS, RoadService
from asterion.application.s1 import S1Service
from asterion.application.s2 import S2Service
from asterion.application.s3 import S3Service
from asterion.application.world import WorldService
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.inventory_ui import render_inventory
from asterion.bot.p1_ui import render_p1
from asterion.bot.p2_ui import render_p2, render_p2_mission_detail
from asterion.bot.p3_ui import render_p3, render_p3_detail
from asterion.bot.p4_ui import render_p4, render_p4_detail
from asterion.bot.road_ui import render_road
from asterion.bot.s2_ui import render_s2
from asterion.bot.s3_ui import render_s3
from asterion.bot.world_ui import render_world


def world_router(
    service: WorldService,
    images: dict[str, str],
    p1: P1Service | None = None,
    road: RoadService | None = None,
    inventory: InventoryService | None = None,
    s1: S1Service | None = None,
    consumables: ConsumableService | None = None,
    prologue: PrologueService | None = None,
    p2: P2Service | None = None,
    s2: S2Service | None = None,
    p3: P3Service | None = None,
    s3: S3Service | None = None,
    p4: P4Service | None = None,
) -> Router:
    router = Router(name="world")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def resume_world_or_prologue(actor: int) -> Screen | None:
        view = await service.resume(actor)
        if view is not None:
            return render_world(view)
        if prologue is None:
            return None
        combat_view = await prologue.resume(actor)
        view = await service.resume(actor)
        if view is not None:
            return render_world(view)
        return render_combat(combat_view) if combat_view is not None else None

    async def show(message: Message):
        p2_view = await p2.resume(message.from_user.id) if p2 and message.from_user else None
        if (
            p2_view is not None
            and p2_view.status == "active"
            and p2_view.kind == "combat"
        ):
            await present(message, render_p2(p2_view), images)
            return
        p4_view = await p4.resume(message.from_user.id) if p4 and message.from_user else None
        if p4_view is not None and p4_view.status == "active" and p4_view.kind == "combat":
            await present(message, render_p4(p4_view), images)
            return
        s3_view = await s3.resume(message.from_user.id) if s3 and message.from_user else None
        if s3_view is not None and s3_view.status == "active" and s3_view.kind == "combat":
            await present(message, render_s3(s3_view), images)
            return
        s2_view = await s2.resume(message.from_user.id) if s2 and message.from_user else None
        if s2_view is not None and s2_view.status == "active" and s2_view.kind == "combat":
            await present(message, render_s2(s2_view), images)
            return
        p3_view = await p3.resume(message.from_user.id) if p3 and message.from_user else None
        if p3_view is not None and p3_view.status == "active" and p3_view.kind == "combat":
            await present(message, render_p3(p3_view), images)
            return
        road_view = await road.resume(message.from_user.id) if road and message.from_user else None
        if road_view is not None:
            await present(message, render_road(road_view), images)
            return
        p1_view = await p1.resume(message.from_user.id) if p1 and message.from_user else None
        if p1_view is not None and p1_view.combat is not None:
            await present(message, render_p1(p1_view), images)
            return
        if (
            p2_view is not None
            and p2_view.status == "active"
            and p2_view.location == CHARNECA
        ):
            await present(message, render_p2(p2_view), images)
            return
        screen = (
            await resume_world_or_prologue(message.from_user.id)
            if message.from_user
            else None
        )
        if screen:
            await present(message, screen, images)

    async def show_menu(query: CallbackQuery):
        p2_view = await p2.resume(query.from_user.id) if p2 else None
        if (
            p2_view is not None
            and p2_view.status == "active"
            and p2_view.kind == "combat"
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_p2(p2_view), images, edit=True)
            return
        p4_view = await p4.resume(query.from_user.id) if p4 else None
        if (
            p4_view is not None and p4_view.status == "active"
            and p4_view.kind == "combat" and isinstance(query.message, Message)
        ):
            await present(query.message, render_p4(p4_view), images, edit=True)
            return
        s3_view = await s3.resume(query.from_user.id) if s3 else None
        if (
            s3_view is not None and s3_view.status == "active"
            and s3_view.kind == "combat" and isinstance(query.message, Message)
        ):
            await present(query.message, render_s3(s3_view), images, edit=True)
            return
        s2_view = await s2.resume(query.from_user.id) if s2 else None
        if (
            s2_view is not None
            and s2_view.status == "active"
            and s2_view.kind == "combat"
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_s2(s2_view), images, edit=True)
            return
        p3_view = await p3.resume(query.from_user.id) if p3 else None
        if (
            p3_view is not None
            and p3_view.status == "active"
            and p3_view.kind == "combat"
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_p3(p3_view), images, edit=True)
            return
        road_view = await road.resume(query.from_user.id) if road else None
        if (
            road_view is not None
            and isinstance(query.message, Message)
            and (road_view.kind in {"combat", "exploration"} or road_view.kind.startswith("round_"))
        ):
            await present(query.message, render_road(road_view), images, edit=True)
            return
        p1_view = await p1.resume(query.from_user.id) if p1 else None
        if (
            p1_view is not None
            and p1_view.combat is not None
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_p1(p1_view), images, edit=True)
            return
        if (
            p2_view is not None
            and p2_view.status == "active"
            and p2_view.location == CHARNECA
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_p2(p2_view), images, edit=True)
            return
        screen = await resume_world_or_prologue(query.from_user.id)
        if screen is not None and isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def s2_combat_foreground(query: CallbackQuery) -> bool:
        p2_view = await p2.resume(query.from_user.id) if p2 is not None else None
        if (
            p2_view is not None
            and p2_view.status == "active"
            and p2_view.kind == "combat"
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_p2(p2_view), images, edit=True)
            return True
        view = await s2.resume(query.from_user.id) if s2 is not None else None
        if (
            view is not None
            and view.status == "active"
            and view.kind == "combat"
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_s2(view), images, edit=True)
            return True
        p3_view = await p3.resume(query.from_user.id) if p3 is not None else None
        if (
            p3_view is not None
            and p3_view.status == "active"
            and p3_view.kind == "combat"
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_p3(p3_view), images, edit=True)
            return True
        p4_view = await p4.resume(query.from_user.id) if p4 is not None else None
        if p4_view is not None and p4_view.status == "active" and p4_view.kind == "combat" and isinstance(query.message, Message):
            await present(query.message, render_p4(p4_view), images, edit=True)
            return True
        s3_view = await s3.resume(query.from_user.id) if s3 is not None else None
        if s3_view is not None and s3_view.status == "active" and s3_view.kind == "combat" and isinstance(query.message, Message):
            await present(query.message, render_s3(s3_view), images, edit=True)
            return True
        return False

    def exploration_callback_attempt_id(query: CallbackQuery) -> UUID | None:
        data = query.data or ""
        parts = data.split(":")
        if len(parts) == 3 and tuple(parts[:2]) in {
            ("road", "local"),
            ("road", "explore"),
        }:
            raw_id = parts[2]
        elif len(parts) == 4 and parts[:2] == ["road", "route"]:
            raw_id = parts[3]
        else:
            return None
        try:
            return UUID(raw_id)
        except (TypeError, ValueError):
            return None

    def exploration_route_matches(view, query: CallbackQuery) -> bool:
        data = query.data or ""
        if data.startswith("road:local:") or data.startswith("road:explore:"):
            return True
        destination = data.rsplit(":", 2)[1] if data.count(":") == 3 else ""
        return bool(
            view.route_available
            and (
                (view.location == CHARNECA
                 and view.recovery_location == REFUGE
                 and destination == "charneca")
                or (view.location == BOSQUE
                    and view.recovery_location == CHARNECA
                    and destination == "bosque")
                or (view.location == RUINS
                    and destination == {
                        BOSQUE: "ruinas",
                        CHARNECA: "bosque",
                        REFUGE: "charneca",
                    }.get(view.recovery_location))
            )
        )

    async def foreground(query: CallbackQuery) -> bool:
        p2_view = await p2.resume(query.from_user.id) if p2 else None
        if (
            p2_view is not None
            and p2_view.status == "active"
            and p2_view.kind == "combat"
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_p2(p2_view), images, edit=True)
            return True
        s2_view = await s2.resume(query.from_user.id) if s2 else None
        if (
            s2_view is not None
            and s2_view.status == "active"
            and s2_view.kind == "combat"
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_s2(s2_view), images, edit=True)
            return True
        p3_view = await p3.resume(query.from_user.id) if p3 else None
        if (
            p3_view is not None
            and p3_view.status == "active"
            and p3_view.kind == "combat"
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_p3(p3_view), images, edit=True)
            return True
        p4_view = await p4.resume(query.from_user.id) if p4 else None
        if p4_view is not None and p4_view.status == "active" and p4_view.kind == "combat" and isinstance(query.message, Message):
            await present(query.message, render_p4(p4_view), images, edit=True)
            return True
        s3_view = await s3.resume(query.from_user.id) if s3 else None
        if s3_view is not None and s3_view.status == "active" and s3_view.kind == "combat" and isinstance(query.message, Message):
            await present(query.message, render_s3(s3_view), images, edit=True)
            return True
        road_view = await road.resume(query.from_user.id) if road else None
        if road_view is not None and road_view.kind == "exploration":
            callback_attempt_id = exploration_callback_attempt_id(query)
            if (
                callback_attempt_id == road_view.attempt_id
                and exploration_route_matches(road_view, query)
                and isinstance(query.message, Message)
            ):
                return False
            if isinstance(query.message, Message):
                await present(query.message, render_road(road_view), images, edit=True)
                return True
        if (
            road_view is not None
            and (road_view.kind == "combat" or road_view.kind.startswith("round_"))
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_road(road_view), images, edit=True)
            return True
        view = await p1.resume(query.from_user.id) if p1 else None
        if view is not None and view.combat is not None and isinstance(query.message, Message):
            await present(query.message, render_p1(view), images, edit=True)
            return True
        return False

    async def restore_context(query: CallbackQuery):
        if not isinstance(query.message, Message):
            return
        p2_view = await p2.resume(query.from_user.id) if p2 is not None else None
        if p2_view is not None and p2_view.status == "active":
            await present(query.message, render_p2(p2_view), images, edit=True)
            return
        s2_view = await s2.resume(query.from_user.id) if s2 is not None else None
        if s2_view is not None and s2_view.status == "active":
            await present(query.message, render_s2(s2_view), images, edit=True)
            return
        p3_view = await p3.resume(query.from_user.id) if p3 is not None else None
        if p3_view is not None and p3_view.status == "active" and p3_view.kind == "combat":
            await present(query.message, render_p3(p3_view), images, edit=True)
            return
        p4_view = await p4.resume(query.from_user.id) if p4 is not None else None
        if p4_view is not None and p4_view.status == "active" and p4_view.kind == "combat":
            await present(query.message, render_p4(p4_view), images, edit=True)
            return
        s3_view = await s3.resume(query.from_user.id) if s3 is not None else None
        if s3_view is not None and s3_view.status == "active" and s3_view.kind == "combat":
            await present(query.message, render_s3(s3_view), images, edit=True)
            return
        road_view = await road.resume(query.from_user.id) if road is not None else None
        if road_view is not None and (
            road_view.kind in {"combat", "exploration", "hunt_victory", "hunt_defeat"}
            or road_view.kind.startswith("round_")
        ):
            await present(query.message, render_road(road_view), images, edit=True)
            return
        if p4 is not None:
            p4_view = await p4.resume(query.from_user.id)
            if p4_view is not None and p4_view.status == "active":
                await present(query.message, render_p4(p4_view), images, edit=True)
                return
        if s3 is not None:
            s3_view = await s3.resume(query.from_user.id)
            if s3_view is not None and s3_view.status == "active":
                await present(query.message, render_s3(s3_view), images, edit=True)
                return
        if p3_view is not None and p3_view.status == "active":
            await present(query.message, render_p3(p3_view), images, edit=True)
            return
        if road_view is not None:
            await present(query.message, render_road(road_view), images, edit=True)
            return
        screen = await resume_world_or_prologue(query.from_user.id)
        if screen is not None:
            await present(query.message, screen, images, edit=True)

    @router.message(Command("menu"))
    async def menu(message: Message):
        await show(message)

    @router.callback_query(F.data == "world:rest")
    async def rest(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        view = await service.rest(query.from_user.id)
        await query.answer()
        if view and isinstance(query.message, Message):
            await present(query.message, render_world(view), images, edit=True)

    @router.callback_query(F.data == "road:hunt")
    async def hunt(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            view = await road.start_hunt(query.from_user.id)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data == "road:prepare")
    async def hunt_prepare(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            current = await road.resume(query.from_user.id)
            if current is not None:
                if current.kind == "hunt_victory":
                    await road.acknowledge_result(query.from_user.id)
                elif current.kind == "hunt_defeat":
                    await road.acknowledge_defeat(query.from_user.id)
            view = await road.prepare_hunt(query.from_user.id)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data == "road:local")
    async def road_local(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            view = await road.resume(query.from_user.id)
            if view is not None and view.kind == "hunt_defeat":
                view = await road.acknowledge_defeat(query.from_user.id)
            elif view is not None and view.kind == "hunt_victory":
                view = await road.acknowledge_result(query.from_user.id)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.regexp(r"^road:local:[0-9a-fA-F]{32}$"))
    async def road_local_after_exploration(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        attempt_id = exploration_callback_attempt_id(query)
        current = await road.resume(query.from_user.id)
        if (
            attempt_id is None
            or current is None
            or current.kind != "exploration"
            or current.attempt_id != attempt_id
        ):
            await restore_context(query)
            return
        view = await road.acknowledge_result(query.from_user.id, attempt_id)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data == "road:explore")
    async def explore_prepare(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            view = await road.prepare_explore(query.from_user.id)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.regexp(r"^road:explore:[0-9a-fA-F]{32}$"))
    async def explore_retry(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        attempt_id = exploration_callback_attempt_id(query)
        current = await road.resume(query.from_user.id)
        if (
            attempt_id is not None
            and current is not None
            and current.kind == "exploration"
            and current.attempt_id == attempt_id
        ):
            await road.acknowledge_result(query.from_user.id, attempt_id)
        view = await road.prepare_explore(query.from_user.id)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data == "road:explore:start")
    async def explore(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            view = await road.explore(query.from_user.id)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:round:new:"))
    async def round_prepare(query: CallbackQuery):
        if await s2_combat_foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        try:
            batch_size = int((query.data or "").rsplit(":", 1)[1])
        except (TypeError, ValueError):
            return
        view = await road.prepare_round(query.from_user.id, batch_size)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:round:prepare:view:"))
    async def round_prepare_view(query: CallbackQuery):
        if await s2_combat_foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        try:
            _, _, _, _, token, raw_version = (query.data or "").split(":")
            round_id, version = UUID(hex=token), int(raw_version)
        except (TypeError, ValueError):
            return
        view = await road.round_prepare_view(query.from_user.id, round_id, version)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:round:cons:"))
    async def round_consumables(query: CallbackQuery):
        if await s2_combat_foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        try:
            _, _, _, token, raw_version = (query.data or "").split(":")
            round_id, version = UUID(hex=token), int(raw_version)
        except (TypeError, ValueError):
            return
        view = await road.round_consumables(query.from_user.id, round_id, version)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:round:toggle:"))
    async def round_toggle_consumable(query: CallbackQuery):
        if await s2_combat_foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        try:
            _, _, _, raw_kind, token, raw_version = (query.data or "").split(":")
            round_id, version = UUID(hex=token), int(raw_version)
            consumable = (
                "consumable.heal" if raw_kind == "h"
                else "consumable.purification" if raw_kind == "p"
                else ""
            )
        except (TypeError, ValueError):
            return
        if not consumable:
            return
        view = await road.toggle_round_consumable(
            query.from_user.id, round_id, version, consumable
        )
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:round:start:"))
    async def round_start(query: CallbackQuery):
        if await s2_combat_foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        try:
            _, _, _, token, raw_version = (query.data or "").split(":")
            round_id, version = UUID(hex=token), int(raw_version)
        except (TypeError, ValueError):
            return
        view = await road.start_round(query.from_user.id, round_id, version)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:round:cancel:"))
    async def round_cancel(query: CallbackQuery):
        if await s2_combat_foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        try:
            _, _, _, token, raw_version = (query.data or "").split(":")
            round_id, version = UUID(hex=token), int(raw_version)
        except (TypeError, ValueError):
            return
        view = await road.cancel_round(query.from_user.id, round_id, version)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:round:elite:"))
    async def round_elite(query: CallbackQuery):
        if await s2_combat_foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        try:
            _, _, _, token, raw_version = (query.data or "").split(":")
            round_id, version = UUID(hex=token), int(raw_version)
        except (TypeError, ValueError):
            return
        view = await road.engage_round_elite(query.from_user.id, round_id, version)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:round:back:"))
    async def round_back(query: CallbackQuery):
        if await s2_combat_foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        try:
            token = (query.data or "").rsplit(":", 1)[1]
            round_id = UUID(hex=token)
        except (TypeError, ValueError):
            return
        view = await road.round_back(query.from_user.id, round_id)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data == "inventory:root")
    async def inventory_root(query: CallbackQuery):
        await query.answer()
        if inventory is None or not isinstance(query.message, Message):
            return
        view = await inventory.root(query.from_user.id)
        if view is not None:
            await present(query.message, render_inventory(view), images, edit=True)

    @router.callback_query(F.data.startswith("inventory:category:"))
    async def inventory_category(query: CallbackQuery):
        await query.answer()
        if inventory is None or not isinstance(query.message, Message):
            return
        category = (query.data or "").rsplit(":", 1)[-1]
        view = await inventory.category(query.from_user.id, category)
        if view is not None:
            await present(query.message, render_inventory(view), images, edit=True)

    @router.callback_query(F.data.startswith("inventory:consumable:"))
    async def inventory_consumable(query: CallbackQuery):
        await query.answer()
        if inventory is None or not isinstance(query.message, Message):
            return
        item_id = (query.data or "").removeprefix("inventory:consumable:")
        view = await inventory.consumable_detail(query.from_user.id, item_id)
        if view is not None:
            await present(query.message, render_inventory(view), images, edit=True)

    @router.callback_query(F.data.startswith("consumable:vigor:"))
    async def use_vigor(query: CallbackQuery):
        if (
            consumables is None
            or inventory is None
            or not isinstance(query.message, Message)
        ):
            await query.answer()
            return
        item_id = (query.data or "").split(":", maxsplit=2)[-1]
        value = await consumables.use_vigor_potion(query.from_user.id, item_id)
        view = await inventory.consumable_detail(query.from_user.id, item_id)
        if value is None:
            current = (
                f" Vigor · {view.vigor}/{view.max_vigor}."
                if view is not None and view.vigor is not None
                else ""
            )
            await query.answer(
                f"Poção de Vigor indisponível.{current}", show_alert=True
            )
        else:
            await query.answer(f"Vigor recuperado · {value}/100.")
        if view is not None:
            await present(query.message, render_inventory(view), images, edit=True)

    @router.callback_query(F.data == "pending:root")
    async def pending_root(query: CallbackQuery):
        await query.answer()
        if inventory is None or not isinstance(query.message, Message):
            return
        view = await inventory.pending(query.from_user.id)
        if view is not None:
            await present(query.message, render_inventory(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:route:"))
    async def overland_route(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        route_parts = (query.data or "").split(":")
        route_key = ":".join(route_parts[:3])
        destination = {
            "road:route:charneca": CHARNECA,
            "road:route:refuge": REFUGE,
            "road:route:bosque": BOSQUE,
            "road:route:ruinas": RUINS,
        }.get(route_key)
        route_attempt_id = exploration_callback_attempt_id(query)
        route_has_attempt_id = len(route_parts) == 4
        if len(route_parts) not in {3, 4}:
            await restore_context(query)
            return
        if route_has_attempt_id and route_attempt_id is None:
            await restore_context(query)
            return
        if destination is None:
            await restore_context(query)
            return
        current = await road.resume(query.from_user.id)
        if route_has_attempt_id and (
            current is None
            or current.kind != "exploration"
            or current.attempt_id != route_attempt_id
        ):
            await restore_context(query)
            return
        if current is not None:
            if (
                current.kind == "hunt_defeat"
                and current.location == CHARNECA
                and current.recovery_location == REFUGE
                and destination == CHARNECA
            ):
                await road.acknowledge_defeat(query.from_user.id)
            elif (
                current.kind == "exploration"
                and current.location == CHARNECA
                and current.recovery_location == REFUGE
                and destination == CHARNECA
                and current.attempt_id == route_attempt_id
            ):
                await road.acknowledge_result(query.from_user.id, route_attempt_id)
            elif (
                current.kind == "round_defeated"
                and current.location == CHARNECA
                and current.recovery_location == REFUGE
                and destination == CHARNECA
                and current.round_id is not None
            ):
                await road.round_back(query.from_user.id, current.round_id)
            elif (
                current.kind == "hunt_defeat"
                and current.location == BOSQUE
                and current.recovery_location == CHARNECA
                and destination == BOSQUE
            ):
                await road.acknowledge_defeat(query.from_user.id)
            elif (
                current.kind == "exploration"
                and current.location == BOSQUE
                and current.recovery_location == CHARNECA
                and destination == BOSQUE
                and current.attempt_id == route_attempt_id
            ):
                await road.acknowledge_result(query.from_user.id, route_attempt_id)
            elif (
                current.kind == "round_defeated"
                and current.location == BOSQUE
                and current.recovery_location == CHARNECA
                and destination == BOSQUE
                and current.round_id is not None
            ):
                await road.round_back(query.from_user.id, current.round_id)
            elif (
                current.kind == "hunt_defeat"
                and current.location == RUINS
                and destination == {
                    BOSQUE: RUINS,
                    CHARNECA: BOSQUE,
                    REFUGE: CHARNECA,
                }.get(current.recovery_location)
            ):
                await road.acknowledge_defeat(query.from_user.id)
            elif (
                current.kind == "exploration"
                and current.location == RUINS
                and current.attempt_id == route_attempt_id
                and destination == {
                    BOSQUE: RUINS,
                    CHARNECA: BOSQUE,
                    REFUGE: CHARNECA,
                }.get(current.recovery_location)
            ):
                await road.acknowledge_result(query.from_user.id, route_attempt_id)
            elif (
                current.kind == "round_defeated"
                and current.location == RUINS
                and destination == {
                    BOSQUE: RUINS,
                    CHARNECA: BOSQUE,
                    REFUGE: CHARNECA,
                }.get(current.recovery_location)
                and current.round_id is not None
            ):
                await road.round_back(query.from_user.id, current.round_id)
        view = await road.travel_route(query.from_user.id, destination)
        if view is not None:
            s2_view = await s2.resume(query.from_user.id) if s2 is not None else None
            if s2_view is not None and s2_view.status == "active":
                await present(query.message, render_s2(s2_view), images, edit=True)
                return
            p4_view = await p4.resume(query.from_user.id) if p4 is not None else None
            if p4_view is not None and p4_view.status == "active":
                await present(query.message, render_p4(p4_view), images, edit=True)
                return
            s3_view = await s3.resume(query.from_user.id) if s3 is not None else None
            if s3_view is not None and s3_view.status == "active":
                await present(query.message, render_s3(s3_view), images, edit=True)
                return
            await present(query.message, render_road(view), images, edit=True)
        else:
            await restore_context(query)

    @router.callback_query(F.data.startswith("road:travel:"))
    async def travel(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if road is None or not isinstance(query.message, Message):
            return
        token = (query.data or "").removeprefix("road:travel:")
        if token.startswith("brazier:"):
            token = token.removeprefix("brazier:")
        destinations = {
            "estrada": "tdo.brazier.estrada",
            "refugio_do_ocaso": "tdo.brazier.refugio_do_ocaso",
            "vento_morto": "tdo.brazier.vento_morto",
            "galhos_mortos": "tdo.brazier.galhos_mortos",
            # Existing callbacks continue to mean a permanent-Brazier destination.
            "road": "tdo.brazier.estrada",
            "refuge": "tdo.brazier.refugio_do_ocaso",
        }
        brazier_id = destinations.get(token)
        if brazier_id is None:
            await restore_context(query)
            return
        view = await road.travel_brazier(query.from_user.id, brazier_id)
        if view is not None:
            await present(query.message, render_road(view), images, edit=True)
        else:
            await restore_context(query)

    @router.callback_query(F.data.startswith("road:unavailable:"))
    async def road_unavailable(query: CallbackQuery):
        await query.answer("Indisponível nesta etapa.")

    @router.callback_query(F.data == "world:adventure")
    async def adventure(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if isinstance(query.message, Message):
            text = (
                "🗺️ Aventura\n\nEstradas, ruínas e caminhos esquecidos se estendem por Asterion. "
                "Escolha como deseja seguir sua jornada.\n\n🗺️ Mapa · Mundo\n📜 Missões · Objetivos\n"
                "🦌 Caçadas · Combate\n⛓️ Masmorras · Desafios\n🧭 Desbravar · Exploração\n"
                "🌍 Eventos Mundiais · Ocorrências\n⚔️ PvP · Competição"
            )
            keyboard = [
                [
                    InlineKeyboardButton(text="Mapa", callback_data="world:map"),
                    InlineKeyboardButton(text="Missões", callback_data="world:missions"),
                ],
                [
                    InlineKeyboardButton(text="Caçadas", callback_data="menu:noop"),
                    InlineKeyboardButton(text="Masmorras", callback_data="menu:noop"),
                ],
                [
                    InlineKeyboardButton(text="Desbravar", callback_data="menu:noop"),
                    InlineKeyboardButton(text="Eventos", callback_data="menu:noop"),
                ],
                [InlineKeyboardButton(text="PvP", callback_data="menu:noop")],
                [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
            ]
            await present(
                query.message,
                Screen(text, "adventure", InlineKeyboardMarkup(inline_keyboard=keyboard)),
                images,
                edit=True,
            )

    @router.callback_query(F.data == "world:missions")
    async def missions(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        p1_view = await p1.resume(query.from_user.id) if p1 else None
        p2_view = await p2.resume(query.from_user.id) if p2 else None
        p3_view = await p3.resume(query.from_user.id) if p3 else None
        s3_view = await s3.resume(query.from_user.id) if s3 else None
        p4_view = await p4.resume(query.from_user.id) if p4 else None
        if s3_view is None and s3 is not None:
            s3_view = await s3.offer(query.from_user.id)
        if p4_view is None and p4 is not None:
            p4_view = await p4.offer(query.from_user.id)
        s1_view = await s1.resume(query.from_user.id) if s1 else None
        s2_view = await s2.resume(query.from_user.id) if s2 else None
        if s2_view is None and s2 is not None:
            s2_view = await s2.offer(query.from_user.id)
        text = "📜 Missões\n\nObjetivos, promessas e caminhos ainda inacabados acompanham sua jornada por Asterion."
        keyboard = []
        if p1_view is not None and p1_view.status == "active":
            text += (
                "\n\n🔥 Missão Principal\n\n"
                "📜 Vozes na Estrada · Em Andamento\nTerras do Ocaso · Nv. 1–10"
            )
            keyboard.append(
                [InlineKeyboardButton(text="Principal", callback_data="world:principal")]
            )
        elif p2_view is not None and p2_view.status == "active":
            text += (
                "\n\n🔥 Missão Principal\n\n"
                "📜 Fuligem sem Fogo · Em Andamento\nTerras do Ocaso · Nv. 3+"
            )
            keyboard.append(
                [InlineKeyboardButton(text="Principal", callback_data="world:principal")]
            )
        elif p4_view is not None and p4_view.status == "active":
            text += (
                "\n\n🔥 Missão Principal\n\n"
                "📜 Pedras que Ainda Vigiam · Em Andamento\nTerras do Ocaso · Nv. 7+"
            )
            keyboard.append([InlineKeyboardButton(text="Principal", callback_data="world:principal")])
        elif p3_view is not None and p3_view.status == "active":
            text += (
                "\n\n🔥 Missão Principal\n\n"
                "🌿 Sob Galhos Calcinados · Em Andamento\nTerras do Ocaso · Nv. 5+"
            )
            keyboard.append(
                [InlineKeyboardButton(text="Principal", callback_data="world:principal")]
            )
        elif p4_view is not None and p4_view.available:
            text += (
                "\n\n🔥 Missão Principal\n\n"
                "📜 Pedras que Ainda Vigiam · Disponível\nTerras do Ocaso · Nv. 7+"
            )
            keyboard.append([InlineKeyboardButton(text="Principal", callback_data="p4:offer")])
        secondary_lines = []
        secondary_buttons = []
        if s1_view is not None and s1_view.status == "active":
            secondary_lines.append("🕯️ Luzes sob as Cinzas · Em Andamento")
            secondary_buttons.append([InlineKeyboardButton(text="Luzes sob as Cinzas", callback_data="s1:detail")])
        if s2_view is not None:
            if s2_view.status == "active":
                secondary_lines.append("📖 Os Nomes Esquecidos · Em Andamento")
                secondary_buttons.append([InlineKeyboardButton(text="Os Nomes Esquecidos", callback_data="s2:detail")])
            elif s2_view.status == "completed":
                secondary_lines.append("✅ Os Nomes Esquecidos · Concluída")
                secondary_buttons.append([InlineKeyboardButton(text="Os Nomes Esquecidos", callback_data="s2:detail")])
            elif s2_view.reacceptable:
                secondary_lines.append("📖 Os Nomes Esquecidos · Disponível para reaceite")
                secondary_buttons.append([InlineKeyboardButton(text="Os Nomes Esquecidos", callback_data="s2:offer")])
            elif s2_view.available:
                secondary_lines.append("📖 Os Nomes Esquecidos · Disponível")
                secondary_buttons.append([InlineKeyboardButton(text="Os Nomes Esquecidos", callback_data="s2:offer")])
        if s3_view is not None:
            if s3_view.status == "active":
                secondary_lines.append("📜 Rastros sob os Galhos · Em Andamento")
                secondary_buttons.append([InlineKeyboardButton(text="Rastros sob os Galhos", callback_data="s3:detail")])
            elif s3_view.status == "completed":
                secondary_lines.append("✅ Rastros sob os Galhos · Concluída")
                secondary_buttons.append([InlineKeyboardButton(text="Rastros sob os Galhos", callback_data="s3:detail")])
            elif s3_view.reacceptable:
                secondary_lines.append("📜 Rastros sob os Galhos · Disponível para reaceite")
                secondary_buttons.append([InlineKeyboardButton(text="Rastros sob os Galhos", callback_data="s3:offer")])
            elif s3_view.available:
                secondary_lines.append("📜 Rastros sob os Galhos · Disponível")
                secondary_buttons.append([InlineKeyboardButton(text="Rastros sob os Galhos", callback_data="s3:offer")])
        if secondary_lines:
            text += "\n\n📖 Missões Secundárias\n\n" + "\n".join(
                f"{index} {line}" for index, line in enumerate(secondary_lines, start=1)
            )
            keyboard.extend(secondary_buttons)
        if p4_view is not None and p4_view.status == "completed":
            text += "\n\n✅ Pedras que Ainda Vigiam · Concluída"
        keyboard.append(
            [InlineKeyboardButton(text="← Aventura", callback_data="world:adventure")]
        )
        await present(
            query.message,
            Screen(text, "missions", InlineKeyboardMarkup(inline_keyboard=keyboard)),
            images,
            edit=True,
        )

    @router.callback_query(F.data == "world:oren")
    async def oren_npc(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        p2_view = await p2.resume(query.from_user.id) if p2 else None
        if (
            p2_view is not None
            and p2_view.status == "active"
            and p2_view.step == 5
        ):
            view = await p2.oren(query.from_user.id, p2_view.state_version)
            if view is not None:
                await present(query.message, render_p2(view), images, edit=True)
            return
        p4_view = await p4.resume(query.from_user.id) if p4 else None
        if p4_view is not None and p4_view.status == "active":
            if p4_view.step == 6:
                p4_view = await p4.action(
                    query.from_user.id, p4_view.state_version, "report_oren"
                )
            if p4_view is not None:
                await present(query.message, render_p4(p4_view), images, edit=True)
            return
        s2_view = await s2.oren(query.from_user.id) if s2 else None
        view = await s1.oren(query.from_user.id) if s1 else None
        p3_view = await p3.oren(query.from_user.id) if p3 else None
        if view is not None:
            from asterion.bot.s1_ui import render_s1

            screen = render_s1(view)
        elif s2_view is not None:
            screen = render_s2(s2_view)
        elif p3_view is not None:
            screen = render_p3(p3_view)
        else:
            screen = Screen(
                "✒️ Oren Cal\nRefúgio do Ocaso · Terras do Ocaso",
                "oren_cal",
                InlineKeyboardMarkup(inline_keyboard=[]),
            )
        if s2_view is not None and view is not None:
            rows = list(screen.keyboard.inline_keyboard) if screen.keyboard else []
            if s2_view.status == "active":
                if s2_view.step == 6:
                    s2_action = f"s2:{s2_view.state_version}:complete"
                    s2_label = "Entregar o fragmento a Oren"
                else:
                    s2_action = "s2:objective"
                    s2_label = "Ver Os Nomes Esquecidos"
                rows.append([InlineKeyboardButton(text=s2_label, callback_data=s2_action)])
            elif s2_view.status == "completed":
                rows.append([InlineKeyboardButton(text="Os Nomes Esquecidos · Concluída", callback_data="s2:detail")])
            elif s2_view.reacceptable or s2_view.available:
                rows.append([InlineKeyboardButton(text="Os Nomes Esquecidos", callback_data="s2:offer")])
            text = screen.text + "\n\n📖 Os Nomes Esquecidos · " + (
                "Em Andamento" if s2_view.status == "active" else
                "Concluída" if s2_view.status == "completed" else
                "Disponível para reaceite" if s2_view.reacceptable else
                "Disponível" if s2_view.available else
                "Indisponível no momento"
            )
            screen = Screen(text, screen.image_key, InlineKeyboardMarkup(inline_keyboard=rows), parse_mode=screen.parse_mode)
        if p3_view is not None and (view is not None or s2_view is not None):
            rows = list(screen.keyboard.inline_keyboard) if screen.keyboard else []
            if p3_view.status == "active":
                p3_label = (
                    "Falar com Oren Cal · Sob Galhos Calcinados"
                    if p3_view.step == 5
                    else "Sob Galhos Calcinados · Em Andamento"
                )
                rows.append([InlineKeyboardButton(text=p3_label, callback_data="p3:oren")])
            elif p3_view.status == "completed":
                rows.append([InlineKeyboardButton(text="Sob Galhos Calcinados · Concluída", callback_data="p3:oren")])
            elif p3_view.available:
                rows.append([InlineKeyboardButton(text="Sob Galhos Calcinados", callback_data="p3:offer")])
            text = screen.text + "\n\n🌿 Sob Galhos Calcinados · " + (
                "Em Andamento" if p3_view.status == "active" else
                "Concluída" if p3_view.status == "completed" else
                "Disponível" if p3_view.available else
                "Indisponível no momento"
            )
            screen = Screen(text, screen.image_key, InlineKeyboardMarkup(inline_keyboard=rows), parse_mode=screen.parse_mode)
        elif p3_view is not None and view is None and s2_view is None:
            screen = render_p3(p3_view)
        await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data == "world:principal")
    async def principal(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        p1_view = await p1.resume(query.from_user.id) if p1 else None
        if p1_view is not None and p1_view.status == "active":
            await _present_p1_principal(query, p1_view)
            return
        p2_view = await p2.resume(query.from_user.id) if p2 else None
        if p2_view is not None and p2_view.status == "active":
            await present(
                query.message,
                render_p2_mission_detail(p2_view),
                images,
                edit=True,
            )
            return
        p4_view = await p4.resume(query.from_user.id) if p4 else None
        if p4_view is not None and p4_view.status == "active":
            await present(query.message, render_p4_detail(p4_view), images, edit=True)
            return
        p3_view = await p3.resume(query.from_user.id) if p3 else None
        if p3_view is not None and p3_view.status == "active":
            await present(
                query.message,
                render_p3_detail(p3_view),
                images,
                edit=True,
            )
            return
        if p1_view is None or p1_view.status != "active":
            await present(
                query.message,
                Screen(
                    "📜 Missões\n\nObjetivos, promessas e caminhos ainda inacabados acompanham sua jornada por Asterion.",
                    "missions",
                    InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="← Aventura", callback_data="world:adventure"
                                )
                            ]
                        ]
                    ),
                ),
                images,
                edit=True,
            )
            return
    async def _present_p1_principal(query: CallbackQuery, p1_view) -> None:
        if not isinstance(query.message, Message):
            return
        progress = p1_view.progress or {}
        if p1_view.step == 1:
            objective, local = "Seguir pela Estrada das Cinzas", "Estrada das Cinzas"
        elif p1_view.step == 2:
            objective, local = (
                f"Examinar Sinais · {'1/2' if progress.get('pegadas') else '0/2'}",
                "Estrada das Cinzas",
            )
        elif p1_view.step == 3:
            objective, local = "Sobreviver ao encontro na Estrada", "Estrada das Cinzas"
            context = "Os sulcos desaparecem onde a estrada se estreita entre pedras partidas. Antes que você possa seguir as marcas, um rosnado baixo rompe o silêncio. Um Cão Cinéreo emerge da fuligem e fecha a passagem."
        elif p1_view.step == 4:
            objective, local = "Alcançar o Refúgio do Ocaso", "Refúgio do Ocaso"
            context = "Mais adiante, a estrada deixa de ser apenas ruína. Pedras empilhadas, madeira reaproveitada e pontos de luz surgem através da fuligem."
        elif p1_view.step == 5:
            objective, local = "Falar com Alda Veyr", "Refúgio do Ocaso"
            context = "Uma mulher observa a estrada antes mesmo de olhar para você. Sua atenção passa primeiro pelas marcas da fuligem, depois por suas armas e só então pelo seu rosto."
        elif p1_view.step == 6:
            objective, local = "Conhecer Oren Cal", "Refúgio do Ocaso"
            context = "Alda indica um homem cercado por folhas, tábuas riscadas e fragmentos trazidos das estradas. Ele organiza cada peça como se perder uma palavra fosse tão grave quanto perder uma pessoa."
        else:
            objective, local = "Ativar o Braseiro do Refúgio", "Refúgio do Ocaso"
            context = "No centro do Refúgio, uma chama resiste entre pedras marcadas pelo uso. Pessoas passam por ela sem cerimônia, mas nenhuma ignora completamente sua presença."
        if p1_view.step == 1:
            context = "A chama deixada para trás desaparece pouco a pouco entre a fuligem. A Estrada das Cinzas segue adiante, irregular e silenciosa, mas desta vez há marcas recentes onde antes havia apenas abandono."
        elif p1_view.step == 2 and not progress.get("pegadas"):
            context = "Marcas de botas cortam a fuligem em uma única direção. As bordas ainda estão nítidas demais para terem permanecido ali por muito tempo."
        elif p1_view.step == 2:
            context = "Duas marcas estreitas atravessam a cinza ao lado das pegadas. A fuligem ainda não voltou a cobrir completamente os sulcos deixados pelas rodas."
        elif p1_view.step == 3 and progress.get("defeat"):
            context = "Recuperado no Braseiro da Estrada, você precisará retornar ao encontro e vencê-lo antes de seguir viagem."
        text = (
            f"📜 Vozes na Estrada · Em Andamento\nMissão Principal · Terras do Ocaso\n\n<i>{context}</i>\n\n🎯 Objetivo · {objective}\n\n"
            f"Local · {local}\n\n🎁 Recompensas\n\n✨ XP · 2.400\n🪙 Coroas · 120\n📦 Ferro de Fuligem · 1 · Vinculado\n📦 Couro Escoriado · 1 · Vinculado"
        )
        buttons = [[InlineKeyboardButton(text="Ver Objetivo", callback_data="world:objective")]]
        road_known = "tdo.location.estrada_das_cinzas" in p1_view.known_locations
        refuge_known = "tdo.location.refugio_do_ocaso" in p1_view.known_locations
        if (local == "Estrada das Cinzas" and road_known) or (
            local == "Refúgio do Ocaso" and refuge_known
        ):
            buttons.append([InlineKeyboardButton(text="Ver no Mapa", callback_data="world:map")])
        buttons.append([InlineKeyboardButton(text="← Missões", callback_data="world:missions")])
        await present(
            query.message,
            Screen(
                text, "mission_p1", InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML"
            ),
            images,
            edit=True,
        )

    @router.callback_query(F.data == "world:objective")
    async def objective(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if isinstance(query.message, Message) and p2 is not None:
            p2_view = await p2.resume(query.from_user.id)
            if p2_view is not None and p2_view.status == "active":
                await present(query.message, render_p2(p2_view), images, edit=True)
                return
        if isinstance(query.message, Message) and p3 is not None:
            p3_view = await p3.objective(query.from_user.id)
            if p3_view is not None and p3_view.status == "active":
                await present(query.message, render_p3(p3_view), images, edit=True)
                return
        if isinstance(query.message, Message) and p1 is not None:
            view = await p1.resume(query.from_user.id)
            if view is not None:
                await present(query.message, render_p1(view), images, edit=True)

    async def map_state(actor: int):
        known: set[str] = set()
        if p1 is not None:
            p1_view = await p1.resume(actor)
            if p1_view is not None:
                ids = set(p1_view.known_locations)
                if "tdo.location.estrada_das_cinzas" in ids:
                    known.add("Estrada das Cinzas")
                if "tdo.location.refugio_do_ocaso" in ids:
                    known.add("Refúgio do Ocaso")
                if "tdo.location.charneca_da_fuligem" in ids:
                    known.add(CHARNECA)
        p2_view = await p2.resume(actor) if p2 is not None else None
        if p2_view is not None and p2_view.status == "active" and p2_view.location == CHARNECA:
            known.add(CHARNECA)
        p3_view = await p3.resume(actor) if p3 is not None else None
        if p3_view is not None and (
            p3_view.status == "completed"
            or (p3_view.status == "active" and (p3_view.progress or {}).get("bosque_entered"))
        ):
            known.add(BOSQUE)
        p4_view = await p4.resume(actor) if p4 is not None else None
        if p4_view is not None and (
            p4_view.status == "completed"
            or (p4_view.status == "active" and (p4_view.progress or {}).get("ruins_discovered"))
        ):
            known.add(RUINS)
        current = None
        road_view = None
        if road is not None:
            road_view = await road.resume(actor)
            if road_view is not None:
                current = getattr(road_view, "recovery_location", None) or road_view.location
        if current is None and p2_view is not None and p2_view.status == "active":
            current = p2_view.location
        if current is None and p3_view is not None and p3_view.status == "active":
            current = p3_view.location
        if current is None and p4_view is not None and p4_view.status == "active":
            current = p4_view.location
        if current is None:
            world_view = await service.resume(actor)
            if world_view is not None:
                current = world_view.location
        return known, current, road_view, p2_view, p3_view, p4_view

    @router.callback_query(F.data == "world:map")
    async def map_screen(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        known, current, _, _, _, _ = await map_state(query.from_user.id)
        if not known:
            text = "🗺️ Mapa\n\nNenhuma Região conhecida."
            keyboard = [[InlineKeyboardButton(text="← Aventura", callback_data="world:adventure")]]
        else:
            current_icon = (
                "🌑" if current == CHARNECA else "🌲" if current == BOSQUE else "🪨" if current == RUINS else "🔥"
            )
            current_line = f"{current_icon} {current} · Local Atual" if current else ""
            text = (
                "🗺️ Mapa\n\n"
                "🌑 Terras do Ocaso · Nv. 1–10\n"
                f"{current_line}\n\n"
                "🗺️ Regiões Conhecidas\n\n"
                "1 🌑 Terras do Ocaso · Nv. 1–10"
            )
            keyboard = [
                [InlineKeyboardButton(text="1", callback_data="world:map:region:tdo")],
                [InlineKeyboardButton(text="← Aventura", callback_data="world:adventure")],
            ]
        await present(
            query.message,
            Screen(text, "map", InlineKeyboardMarkup(inline_keyboard=keyboard)),
            images,
            edit=True,
        )

    @router.callback_query(F.data == "world:map:region:tdo")
    async def map_region_tdo(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        known, current, _, _, _, _ = await map_state(query.from_user.id)
        ordered = [
            ("Estrada das Cinzas", "road"),
            ("Refúgio do Ocaso", "refuge"),
            (CHARNECA, "charneca"),
            (BOSQUE, "bosque"),
            (RUINS, "ruinas"),
        ]
        visible = [(name, key) for name, key in ordered if name in known]
        lines = ["🌑 Terras do Ocaso · Nv. 1–10", ""]
        buttons = []
        for index, (name, key) in enumerate(visible, start=1):
            state = "Local Atual" if name == current else "Acessível"
            icon = (
                "🌑" if key == "charneca" else
                "🌲" if key == "bosque" else
                "🪨" if key == "ruinas" else
                "🔥" if name == current else
                "🏚️" if key == "refuge" else "📍"
            )
            lines.append(f"{index} {icon} {name} · {state}")
            buttons.append(
                InlineKeyboardButton(
                    text=str(index),
                    callback_data=f"world:map:local:{key}",
                )
            )
        keyboard = []
        if buttons:
            keyboard.append(buttons)
        keyboard.append([InlineKeyboardButton(text="← Mapa", callback_data="world:map")])
        await present(
            query.message,
            Screen(
                "\n".join(lines),
                "map",
                InlineKeyboardMarkup(inline_keyboard=keyboard),
            ),
            images,
            edit=True,
        )

    @router.callback_query(F.data.startswith("world:map:local:"))
    async def map_local(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        key = (query.data or "").rsplit(":", 1)[-1]
        names = {"road": ROAD, "refuge": REFUGE, "charneca": CHARNECA, "bosque": BOSQUE, "ruinas": RUINS}
        name = names.get(key)
        if name is None:
            return
        known, current, road_view, p2_view, p3_view, p4_view = await map_state(query.from_user.id)
        if name not in known:
            return
        if key == "charneca" and p2_view is not None and p2_view.status == "active":
            await present(query.message, render_p2(p2_view), images, edit=True)
            return
        if key == "bosque" and p3_view is not None and p3_view.status == "active":
            screen = render_p3(p3_view)
            rows = list(screen.keyboard.inline_keyboard) if screen.keyboard else []
            rows.append([InlineKeyboardButton(text="← Terras do Ocaso", callback_data="world:map:region:tdo")])
            await present(
                query.message,
                Screen(screen.text, screen.image_key, InlineKeyboardMarkup(inline_keyboard=rows), parse_mode=screen.parse_mode),
                images,
                edit=True,
            )
            return
        if key in {"bosque", "ruinas"} and p4_view is not None and p4_view.status == "active":
            screen = render_p4(p4_view)
            rows = list(screen.keyboard.inline_keyboard) if screen.keyboard else []
            rows.append([InlineKeyboardButton(text="← Terras do Ocaso", callback_data="world:map:region:tdo")])
            await present(
                query.message,
                Screen(screen.text, screen.image_key, InlineKeyboardMarkup(inline_keyboard=rows), parse_mode=screen.parse_mode),
                images,
                edit=True,
            )
            return
        brazier_travel_available = bool(
            road_view is not None
            and road_view.location == current
            and road_view.brazier_id
            and road_view.brazier_destinations
            and not (p2_view is not None and p2_view.status == "active")
            and not (p3_view is not None and p3_view.status == "active")
        )
        local_kinds = {"road", "refuge", "charneca", "bosque", "ruinas"}
        is_current = name == current
        if is_current:
            if road_view is not None and road_view.kind not in local_kinds:
                screen = render_road(road_view)
                rows = list(screen.keyboard.inline_keyboard) if screen.keyboard else []
                rows.append(
                    [
                        InlineKeyboardButton(
                            text="← Terras do Ocaso",
                            callback_data="world:map:region:tdo",
                        )
                    ]
                )
                await present(
                    query.message,
                    Screen(
                        screen.text,
                        screen.image_key,
                        InlineKeyboardMarkup(inline_keyboard=rows),
                        parse_mode=screen.parse_mode,
                    ),
                    images,
                    edit=True,
                )
                return
        if key in {"charneca", "bosque", "ruinas"} and current == name and road_view is not None and road_view.kind in {"charneca", "bosque", "ruinas"}:
            screen = render_road(road_view)
            rows = list(screen.keyboard.inline_keyboard) if screen.keyboard else []
            if rows and rows[-1] and rows[-1][-1].callback_data == "menu:back":
                rows[-1] = [InlineKeyboardButton(text="← Terras do Ocaso", callback_data="world:map:region:tdo")]
            else:
                rows.append([InlineKeyboardButton(text="← Terras do Ocaso", callback_data="world:map:region:tdo")])
            await present(
                query.message,
                Screen(screen.text, screen.image_key, InlineKeyboardMarkup(inline_keyboard=rows), parse_mode=screen.parse_mode),
                images,
                edit=True,
            )
            return
        icon = "🌑" if key == "charneca" else "🌲" if key == "bosque" else "🪨" if key == "ruinas" else "🔥" if is_current else ("🏚️" if key == "refuge" else "📍")
        title = f"{icon} {name}" + (" · Local Atual" if is_current else "")
        level_band = "Nv. 3–5" if key == "charneca" else "Nv. 5–8" if key == "bosque" else "Nv. 8–10" if key == "ruinas" else "Nv. 1–10"
        local_brazier = road_view.brazier_label if is_current and road_view is not None else None
        if key in {"charneca", "bosque", "ruinas"} and local_brazier is None and road_view is not None:
            local_brazier = next(
                (
                    label
                    for _, label, destination_location in road_view.brazier_destinations
                    if destination_location == name
                ),
                None,
            )
        brazier_line = (
            f"🔥 {local_brazier} · Descoberto"
            if local_brazier
            else "🔥 Braseiro · Não descoberto"
            if key in {"charneca", "bosque", "ruinas"}
            else "🔥 Braseiro · Descoberto"
        )
        lines = [title, f"Terras do Ocaso · {level_band}", "", brazier_line]
        keyboard = []
        if key == "road":
            lines.extend(["🧭 Desbravar · Disponível", "🦌 Caçadas · Disponível"])
            if is_current:
                keyboard.append(
                    [
                        InlineKeyboardButton(text="Desbravar", callback_data="road:explore"),
                        InlineKeyboardButton(text="Caçadas", callback_data="road:prepare"),
                    ]
                )
        elif key == "refuge":
            lines.extend(["🚫 Desbravar · Indisponível", "🚫 Caçadas · Indisponível"])
            if is_current:
                keyboard.append(
                    [InlineKeyboardButton(text="Oren Cal", callback_data="world:oren")]
                )
                keyboard.append(
                    [InlineKeyboardButton(text="Alda Veyr", callback_data="p2:alda")]
                )
                if road_view is not None and road_view.route_available:
                    keyboard.append([InlineKeyboardButton(text="Seguir para a Charneca", callback_data="road:route:charneca")])
        elif key in {"charneca", "bosque"}:
            if is_current and road_view is not None and road_view.kind == "charneca":
                lines.extend([
                    "🧭 Desbravar · Disponível conforme gates",
                    "🦌 Caçadas · Disponível conforme nível e pool",
                    "🔒 Ronda de Caça · Vença uma Caçada neste Local"
                    if not road_view.familiar
                    else "🏕️ Ronda de Caça · Disponível",
                ])
                keyboard.append([InlineKeyboardButton(text="Desbravar", callback_data="road:explore"), InlineKeyboardButton(text="Caçadas", callback_data="road:prepare")])
                if road_view.route_available:
                    keyboard.append([InlineKeyboardButton(text="Retornar ao Refúgio", callback_data="road:route:refuge")])
                if BOSQUE in road_view.route_destinations:
                    keyboard.append([InlineKeyboardButton(text="Seguir para o Bosque", callback_data="road:route:bosque")])
            elif is_current and road_view is not None and road_view.kind == "bosque":
                lines.extend(["🧭 Desbravar · Disponível conforme gates", "🦌 Caçadas · Disponível conforme nível e pool"])
                if road_view.familiar:
                    lines.append("🏕️ Ronda de Caça · Disponível")
                else:
                    lines.append("🔒 Ronda de Caça · Vença uma Caçada neste Local")
                keyboard.append([InlineKeyboardButton(text="Desbravar", callback_data="road:explore"), InlineKeyboardButton(text="Caçadas", callback_data="road:prepare")])
                if road_view.route_available:
                    keyboard.append([InlineKeyboardButton(text="Retornar à Charneca", callback_data="road:route:charneca")])
            elif current == REFUGE and road_view is not None and CHARNECA in road_view.route_destinations:
                lines.extend(["🧭 Desbravar · Disponível conforme gates", "🦌 Caçadas · Disponível conforme nível e pool"])
                keyboard.append([InlineKeyboardButton(text="Seguir para a Charneca", callback_data="road:route:charneca")])
            elif current == CHARNECA and road_view is not None and BOSQUE in road_view.route_destinations:
                lines.extend(["🧭 Desbravar · Disponível conforme gates", "🦌 Caçadas · Disponível conforme nível e pool"])
                keyboard.append([InlineKeyboardButton(text="Seguir para o Bosque", callback_data="road:route:bosque")])
        elif key == "ruinas":
            normal_open = bool(
                road_view is not None and current == RUINS and road_view.kind == "ruinas"
            )
            if normal_open:
                lines.extend(["🧭 Desbravar · Disponível", "🦌 Caçadas · Disponível conforme nível e pool"])
                lines.append(
                    "🏕️ Ronda de Caça · Disponível"
                    if road_view.familiar
                    else "🔒 Ronda de Caça · Vença uma Caçada neste Local"
                )
                keyboard.append([
                    InlineKeyboardButton(text="Desbravar", callback_data="road:explore"),
                    InlineKeyboardButton(text="Caçadas", callback_data="road:prepare"),
                ])
                if road_view.route_available:
                    keyboard.append([
                        InlineKeyboardButton(text="Retornar ao Bosque", callback_data="road:route:bosque")
                    ])
            elif current == RUINS:
                lines.extend(["🔒 Acesso ao Local · Nv. 8", "Conteúdo normal indisponível no momento."])
            elif current == BOSQUE and road_view is not None and RUINS in road_view.route_destinations:
                lines.append("🧭 Rota terrestre · Disponível")
                keyboard.append([
                    InlineKeyboardButton(text="Seguir para as Ruínas", callback_data="road:route:ruinas")
                ])
            elif current == BOSQUE:
                lines.append("🔒 Acesso normal · P4 concluída e Nv. 8+")
        if brazier_travel_available:
            keyboard.append([InlineKeyboardButton(text="Travessia dos Braseiros", callback_data="world:travel")])
        keyboard.append(
            [InlineKeyboardButton(text="← Terras do Ocaso", callback_data="world:map:region:tdo")]
        )
        await present(
            query.message,
            Screen(
                "\n".join(lines),
                "map",
                InlineKeyboardMarkup(inline_keyboard=keyboard),
            ),
            images,
            edit=True,
        )

    @router.callback_query(F.data == "world:travel")
    async def world_travel(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        p4_view = await p4.resume(query.from_user.id) if p4 is not None else None
        if p4_view is not None and p4_view.status == "active":
            await present(query.message, render_p4(p4_view), images, edit=True)
            return
        p3_view = await p3.resume(query.from_user.id) if p3 is not None else None
        if p3_view is not None and p3_view.status == "active":
            await present(query.message, render_p3(p3_view), images, edit=True)
            return
        _, current, road_view, _, _, _ = await map_state(query.from_user.id)
        if road_view is None or road_view.location != current or not road_view.brazier_id:
            return
        lines = [
            "🔥 Travessia dos Braseiros",
            "",
            f"🔥 Atual · {road_view.brazier_label}",
        ]
        keyboard = []
        if road_view.brazier_destinations:
            lines.extend(["", "🗺️ Destinos"])
            for index, (brazier_id, label, location) in enumerate(road_view.brazier_destinations, start=1):
                lines.extend(["", f"{index} 🔥 {label} · {location}"])
                brazier_key = brazier_id.removeprefix("tdo.brazier.")
                keyboard.append([InlineKeyboardButton(text=str(index), callback_data=f"road:travel:brazier:{brazier_key}")])
        current_key = {ROAD: "road", REFUGE: "refuge", CHARNECA: "charneca", BOSQUE: "bosque", RUINS: "ruinas"}.get(current)
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"← {current}",
                    callback_data=f"world:map:local:{current_key}" if current_key else "world:map:region:tdo",
                )
            ]
        )
        await present(
            query.message,
            Screen(
                "\n".join(lines),
                "map",
                InlineKeyboardMarkup(inline_keyboard=keyboard),
            ),
            images,
            edit=True,
        )

    @router.callback_query(F.data == "menu:back")
    async def back(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        await show_menu(query)

    @router.callback_query(F.data == "menu:noop")
    async def noop(query: CallbackQuery):
        await query.answer()

    return router

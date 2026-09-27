# ruff: noqa: E501
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.consumables import ConsumableService
from asterion.application.inventory import InventoryService
from asterion.application.p1 import P1Service
from asterion.application.p2 import CHARNECA, P2Service
from asterion.application.prologue import PrologueService
from asterion.application.road import RoadService
from asterion.application.s1 import S1Service
from asterion.application.world import WorldService
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.inventory_ui import render_inventory
from asterion.bot.p1_ui import render_p1
from asterion.bot.p2_ui import render_p2, render_p2_mission_detail
from asterion.bot.road_ui import render_road
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
        road_view = await road.resume(query.from_user.id) if road else None
        if (
            road_view is not None
            and (road_view.kind in {"combat", "exploration"} or road_view.kind.startswith("round_"))
            and isinstance(query.message, Message)
        ):
            await present(query.message, render_road(road_view), images, edit=True)
            return True
        view = await p1.resume(query.from_user.id) if p1 else None
        if view is not None and view.combat is not None and isinstance(query.message, Message):
            await present(query.message, render_p1(view), images, edit=True)
            return True
        return False

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
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            view = await road.start_hunt(query.from_user.id)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data == "road:prepare")
    async def hunt_prepare(query: CallbackQuery):
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
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            view = await road.resume(query.from_user.id)
            if view is not None and view.kind == "hunt_defeat":
                view = await road.acknowledge_defeat(query.from_user.id)
            elif view is not None and view.kind == "hunt_victory":
                view = await road.acknowledge_result(query.from_user.id)
            elif view is not None and view.kind == "exploration":
                view = await road.acknowledge_result(query.from_user.id)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data == "road:explore")
    async def explore_prepare(query: CallbackQuery):
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            current = await road.resume(query.from_user.id)
            if current is not None and current.kind == "exploration" and current.retry_available:
                await road.acknowledge_result(query.from_user.id)
            view = await road.prepare_explore(query.from_user.id)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data == "road:explore:start")
    async def explore(query: CallbackQuery):
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            view = await road.explore(query.from_user.id)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data.startswith("road:round:new:"))
    async def round_prepare(query: CallbackQuery):
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

    @router.callback_query(F.data.startswith("road:travel:"))
    async def travel(query: CallbackQuery):
        await query.answer()
        if road is not None and isinstance(query.message, Message):
            destination = (
                "Estrada das Cinzas" if query.data.endswith("road") else "Refúgio do Ocaso"
            )
            view = await road.travel(query.from_user.id, destination)
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

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
        s1_view = await s1.resume(query.from_user.id) if s1 else None
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
        if s1_view is not None and s1_view.status == "active":
            text += (
                "\n\n📖 Missões Secundárias\n\n"
                "1 🕯️ Luzes sob as Cinzas · Em Andamento"
            )
            keyboard.append([InlineKeyboardButton(text="1", callback_data="s1:detail")])
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
        view = await s1.oren(query.from_user.id) if s1 else None
        if view is not None:
            from asterion.bot.s1_ui import render_s1

            await present(query.message, render_s1(view), images, edit=True)

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
        if isinstance(query.message, Message) and p1 is not None:
            view = await p1.resume(query.from_user.id)
            if view is not None:
                await present(query.message, render_p1(view), images, edit=True)

    async def map_state(actor: int) -> tuple[set[str], str | None]:
        known: set[str] = set()
        if p1 is not None:
            p1_view = await p1.resume(actor)
            if p1_view is not None:
                ids = set(p1_view.known_locations)
                if "tdo.location.estrada_das_cinzas" in ids:
                    known.add("Estrada das Cinzas")
                if "tdo.location.refugio_do_ocaso" in ids:
                    known.add("Refúgio do Ocaso")
        current = None
        if road is not None:
            road_view = await road.resume(actor)
            if road_view is not None:
                current = road_view.location
        if current is None:
            world_view = await service.resume(actor)
            if world_view is not None:
                current = world_view.location
        if current == CHARNECA:
            # The regional map screen is intentionally withheld in this PR.
            current = None
        return known, current

    @router.callback_query(F.data == "world:map")
    async def map_screen(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        known, current = await map_state(query.from_user.id)
        if not known:
            text = "🗺️ Mapa\n\nNenhuma Região conhecida."
            keyboard = [[InlineKeyboardButton(text="← Aventura", callback_data="world:adventure")]]
        else:
            current_line = f"🔥 {current} · Local Atual" if current else ""
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
        known, current = await map_state(query.from_user.id)
        ordered = [
            ("Estrada das Cinzas", "road"),
            ("Refúgio do Ocaso", "refuge"),
        ]
        visible = [(name, key) for name, key in ordered if name in known]
        lines = ["🌑 Terras do Ocaso · Nv. 1–10", ""]
        buttons = []
        for index, (name, key) in enumerate(visible, start=1):
            state = "Local Atual" if name == current else "Acessível"
            icon = "🔥" if name == current else ("🏚️" if key == "refuge" else "📍")
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
        name = "Estrada das Cinzas" if key == "road" else "Refúgio do Ocaso"
        known, current = await map_state(query.from_user.id)
        if key not in {"road", "refuge"} or name not in known:
            return
        is_current = current == name
        icon = "🔥" if is_current else ("🏚️" if key == "refuge" else "📍")
        title = f"{icon} {name}" + (" · Local Atual" if is_current else "")
        lines = [title, "Terras do Ocaso · Nv. 1–10", "", "🔥 Braseiro · Descoberto"]
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
        else:
            lines.extend(["🚫 Desbravar · Indisponível", "🚫 Caçadas · Indisponível"])
            if is_current:
                keyboard.append(
                    [InlineKeyboardButton(text="Oren Cal", callback_data="world:oren")]
                )
                keyboard.append(
                    [InlineKeyboardButton(text="Alda Veyr", callback_data="p2:alda")]
                )
        keyboard.append(
            [InlineKeyboardButton(text="Travessia dos Braseiros", callback_data="world:travel")]
        )
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
        known, current = await map_state(query.from_user.id)
        if current not in {"Estrada das Cinzas", "Refúgio do Ocaso"}:
            return
        current_brazier = (
            "Braseiro da Estrada"
            if current == "Estrada das Cinzas"
            else "Braseiro do Refúgio"
        )
        target_name = (
            "Refúgio do Ocaso"
            if current == "Estrada das Cinzas"
            else "Estrada das Cinzas"
        )
        target_key = "refuge" if target_name == "Refúgio do Ocaso" else "road"
        lines = [
            "🔥 Travessia dos Braseiros",
            "",
            f"🔥 Atual · {current_brazier}",
        ]
        keyboard = []
        if target_name in known:
            target_brazier = (
                "Braseiro do Refúgio"
                if target_key == "refuge"
                else "Braseiro da Estrada"
            )
            lines.extend(["", "🗺️ Destinos", "", f"1 🔥 {target_brazier} · {target_name}"])
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text="1",
                        callback_data=f"road:travel:{target_key}",
                    )
                ]
            )
        current_key = "road" if current == "Estrada das Cinzas" else "refuge"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"← {current}",
                    callback_data=f"world:map:local:{current_key}",
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

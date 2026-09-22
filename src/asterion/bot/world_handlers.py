# ruff: noqa: E501
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.p1 import P1Service
from asterion.application.road import RoadService
from asterion.application.world import WorldService
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.p1_ui import render_p1
from asterion.bot.road_ui import render_road
from asterion.bot.world_ui import render_world


def world_router(
    service: WorldService,
    images: dict[str, str],
    p1: P1Service | None = None,
    road: RoadService | None = None,
) -> Router:
    router = Router(name="world")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(message: Message):
        road_view = await road.resume(message.from_user.id) if road and message.from_user else None
        if road_view is not None:
            await present(message, render_road(road_view), images)
            return
        p1_view = await p1.resume(message.from_user.id) if p1 and message.from_user else None
        if p1_view is not None and p1_view.combat is not None:
            await present(message, render_p1(p1_view), images)
            return
        view = await service.resume(message.from_user.id) if message.from_user else None
        if view:
            await present(message, render_world(view), images)

    async def show_menu(query: CallbackQuery):
        road_view = await road.resume(query.from_user.id) if road else None
        if (
            road_view is not None
            and isinstance(query.message, Message)
            and road_view.kind in {"combat", "exploration"}
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
        view = await service.resume(query.from_user.id)
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_world(view), images, edit=True)

    async def foreground(query: CallbackQuery) -> bool:
        road_view = await road.resume(query.from_user.id) if road else None
        if (
            road_view is not None
            and road_view.kind in {"combat", "exploration"}
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
            if view is not None:
                await present(query.message, render_road(view), images, edit=True)

    @router.callback_query(F.data == "road:explore")
    async def explore_prepare(query: CallbackQuery):
        await query.answer()
        if road is not None and isinstance(query.message, Message):
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
        if p1_view is not None and p1_view.status == "active":
            text = (
                "📜 Missões\n\nObjetivos, promessas e caminhos ainda inacabados acompanham sua jornada por Asterion.\n\n"
                "🔥 Missão Principal\n\n📜 Vozes na Estrada · Em Andamento\nTerras do Ocaso · Nv. 1–10"
            )
            keyboard = [
                [InlineKeyboardButton(text="Principal", callback_data="world:principal")],
                [InlineKeyboardButton(text="← Aventura", callback_data="world:adventure")],
            ]
        else:
            text = "📜 Missões\n\nObjetivos, promessas e caminhos ainda inacabados acompanham sua jornada por Asterion."
            keyboard = [[InlineKeyboardButton(text="← Aventura", callback_data="world:adventure")]]
        await present(
            query.message,
            Screen(text, "missions", InlineKeyboardMarkup(inline_keyboard=keyboard)),
            images,
            edit=True,
        )

    @router.callback_query(F.data == "world:principal")
    async def principal(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        p1_view = await p1.resume(query.from_user.id) if p1 else None
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
        if isinstance(query.message, Message) and p1 is not None:
            view = await p1.resume(query.from_user.id)
            if view is not None:
                await present(query.message, render_p1(view), images, edit=True)

    @router.callback_query(F.data == "world:map")
    async def map_screen(query: CallbackQuery):
        if await foreground(query):
            await query.answer()
            return
        await query.answer()
        if not isinstance(query.message, Message):
            return
        known: set[str] = set()
        if p1 is not None:
            view = await p1.resume(query.from_user.id)
            if view is not None:
                ids = set(view.known_locations)
                if "tdo.location.estrada_das_cinzas" in ids:
                    known.add("Estrada das Cinzas")
                if "tdo.location.refugio_do_ocaso" in ids:
                    known.add("Refúgio do Ocaso")
        text = "🗺️ Mapa · Mundo\n\n" + "\n".join(f"📍 {name}" for name in sorted(known))
        await present(
            query.message,
            Screen(
                text,
                "map",
                InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="← Aventura", callback_data="world:adventure")]
                    ]
                ),
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

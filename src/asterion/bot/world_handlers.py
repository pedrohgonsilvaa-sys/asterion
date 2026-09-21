# ruff: noqa: E501
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.p1 import P1Service
from asterion.application.world import WorldService
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.p1_ui import render_p1
from asterion.bot.world_ui import render_world


def world_router(
    service: WorldService, images: dict[str, str], p1: P1Service | None = None
) -> Router:
    router = Router(name="world")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(message: Message):
        p1_view = await p1.resume(message.from_user.id) if p1 and message.from_user else None
        if p1_view is not None and p1_view.combat is not None:
            await present(message, render_p1(p1_view), images)
            return
        view = await service.resume(message.from_user.id) if message.from_user else None
        if view:
            await present(message, render_world(view), images)

    async def show_menu(query: CallbackQuery):
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

    @router.message(Command("menu"))
    async def menu(message: Message):
        await show(message)

    @router.callback_query(F.data == "world:rest")
    async def rest(query: CallbackQuery):
        view = await service.rest(query.from_user.id)
        await query.answer()
        if view and isinstance(query.message, Message):
            await present(query.message, render_world(view), images, edit=True)

    @router.callback_query(F.data == "world:adventure")
    async def adventure(query: CallbackQuery):
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
        elif p1_view.step == 4:
            objective, local = "Alcançar o Refúgio do Ocaso", "Estrada das Cinzas"
        elif p1_view.step == 5:
            objective, local = "Falar com Alda Veyr", "Refúgio do Ocaso"
        elif p1_view.step == 6:
            objective, local = "Conhecer Oren Cal", "Refúgio do Ocaso"
        else:
            objective, local = "Ativar o Braseiro do Refúgio", "Refúgio do Ocaso"
        text = (
            f"📜 Vozes na Estrada · Em Andamento\nMissão Principal · Terras do Ocaso\n\n🎯 Objetivo · {objective}\n\n"
            f"Local · {local}\n\n🎁 Recompensas\n\n✨ XP · 2.400\n🪙 Coroas · 120\n📦 Ferro de Fuligem · 1 · Vinculado\n📦 Couro Escoriado · 1 · Vinculado"
        )
        buttons = [[InlineKeyboardButton(text="Ver Objetivo", callback_data="world:objective")]]
        if (
            local == "Estrada das Cinzas"
            or "tdo.location.refugio_do_ocaso" in p1_view.known_locations
        ):
            buttons.append([InlineKeyboardButton(text="Ver no Mapa", callback_data="world:map")])
        buttons.append([InlineKeyboardButton(text="← Missões", callback_data="world:missions")])
        await present(
            query.message,
            Screen(text, "mission_p1", InlineKeyboardMarkup(inline_keyboard=buttons)),
            images,
            edit=True,
        )

    @router.callback_query(F.data == "world:objective")
    async def objective(query: CallbackQuery):
        await query.answer()
        if isinstance(query.message, Message) and p1 is not None:
            view = await p1.resume(query.from_user.id)
            if view is not None:
                await present(query.message, render_p1(view), images, edit=True)

    @router.callback_query(F.data == "world:map")
    async def map_screen(query: CallbackQuery):
        await query.answer()
        if not isinstance(query.message, Message):
            return
        known = {"Estrada das Cinzas"}
        if p1 is not None:
            view = await p1.resume(query.from_user.id)
            if view is not None and "tdo.location.refugio_do_ocaso" in view.known_locations:
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
        await query.answer()
        await show_menu(query)

    @router.callback_query(F.data == "menu:noop")
    async def noop(query: CallbackQuery):
        await query.answer()

    return router

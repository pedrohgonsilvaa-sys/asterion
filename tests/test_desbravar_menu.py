"""Menu Principal com ⛰️ Desbravar, menu Desbravar e evento ao tocar num Local.

Decisões fechadas do autor: Desbravar é o novo nome de Explorar; todos os Locais
nascem descobertos e clicáveis; tocar num Local leva o personagem até ele pelo hub e
gera o evento do Local (Desbravar canônico). A Câmara do Poente ainda não tem evento.
"""

import pytest
from sqlalchemy import func, select

from asterion.application.road import BOSQUE, CAMARA, CHARNECA, REFUGE, ROAD, RUINS
from asterion.application.tdo_explore import CAMARA_CODEX_ENTRY, discover_all_locations
from asterion.bot.market_ui import render_root
from asterion.bot.world_ui import (
    DESBRAVAR_LOCAL_BY_KEY,
    refuge_menu_keyboard,
    render_desbravar,
)
from asterion.domain.tdo_explore import EXPLORE_TARGETS
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    ExplorationAttempt,
    LocationDiscovery,
    WorldState,
)
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road
from tests.test_tdo_refuge_menu_principal import _callbacks, _feed, _set_state


def _labels(markup):
    return [[button.text for button in row] for row in markup.inline_keyboard]


def test_main_menu_has_desbravar_and_no_removed_entries():
    rows = _labels(refuge_menu_keyboard(gift_available=True))
    assert rows == [
        ["✨ Resgatar Dádiva Diária"],
        ["⛰️ Desbravar", "🗺️ Mapa"],
        ["👤 Personagem", "🏪 Mercado"],
        ["🏟️ Arena", "🏰 Guilda"],
        ["🌌 Eventos", "📖 Códice"],
        ["🏆 Classificação", "🎁 Benefícios"],
        ["🌐 Comunidade", "⚙️ Configurações"],
    ]
    everything = " ".join(label for row in rows for label in row)
    for gone in ("Explorar", "Refúgio", "Caçadas", "Masmorras", "Forja"):
        assert gone not in everything
    callbacks = {
        b.text: b.callback_data
        for row in refuge_menu_keyboard(gift_available=False).inline_keyboard
        for b in row
    }
    assert callbacks["⛰️ Desbravar"] == "tdo:explore"
    assert callbacks["🗺️ Mapa"] == "world:map"


def test_forge_lives_inside_the_market():
    callbacks = {
        b.text: b.callback_data for row in render_root(None).keyboard.inline_keyboard for b in row
    }
    assert callbacks["🔨 Forja"] == "craft:root"


def test_desbravar_menu_layout_and_text():
    screen = render_desbravar()
    assert screen.text.startswith("<b>🧭 Desbravar</b>\n\n<i>As Terras do Ocaso se estendem")
    assert screen.text.endswith("uma ameaça à espreita.</i>")
    assert _labels(screen.keyboard) == [
        ["🗝️ Masmorras", "🌘 Refúgio do Ocaso"],
        ["🔥 Estrada das Cinzas", "🌑 Charneca da Fuligem"],
        ["🌲 Bosque Calcinado", "🏚️ Ruínas do Vigia"],
        ["🌒 Câmara do Poente"],
        ["↩️ Voltar"],
    ]
    data = [b.callback_data for row in screen.keyboard.inline_keyboard for b in row]
    assert data[:2] == ["dungeon:known", "refuge:local"]
    assert data[-1] == "menu:back"
    assert "Caçada" not in screen.text + " ".join(
        b.text for row in screen.keyboard.inline_keyboard for b in row
    )
    assert DESBRAVAR_LOCAL_BY_KEY == {
        "road": ROAD, "charneca": CHARNECA, "bosque": BOSQUE, "ruinas": RUINS, "camara": CAMARA
    }


async def _location(sessions, actor) -> str:
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        return (await session.get(WorldState, character.id)).location


async def _ready(database, actor):
    actor, road = await _seed_road(database, actor=actor)
    sessions = database[1]
    await _set_state(sessions, actor, region="Terras do Ocaso", location=REFUGE)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await discover_all_locations(session, character.id)
    return actor, road, sessions


@pytest.mark.asyncio
async def test_discover_all_locations_is_idempotent_and_records_the_camara(database):
    actor, _road, sessions = await _ready(database, 894501)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await discover_all_locations(session, character.id)
    async with sessions() as session:
        found = set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character.id
                    )
                )
            ).all()
        )
        codex = await session.scalar(
            select(func.count(CodexEntry.id)).where(
                CodexEntry.character_id == character.id, CodexEntry.entry_id == CAMARA_CODEX_ENTRY
            )
        )
    assert {target.location_id for target in EXPLORE_TARGETS} <= found
    assert codex == 1


@pytest.mark.asyncio
async def test_desbravar_entry_opens_the_menu_without_moving(database):
    actor, road, sessions = await _ready(database, 894502)
    screen = await _feed(sessions, road, actor, callback_update("tdo:explore", actor=actor))
    assert "🧭 Desbravar" in screen.text
    assert "tdo:desb:charneca" in _callbacks(screen)
    assert await _location(sessions, actor) == REFUGE


@pytest.mark.asyncio
async def test_touching_a_local_travels_there_and_generates_its_event(database):
    actor, road, sessions = await _ready(database, 894503)
    await _feed(sessions, road, actor, callback_update("tdo:desb:charneca", actor=actor))
    assert await _location(sessions, actor) == CHARNECA
    async with sessions() as session:
        attempts = await session.scalar(select(func.count(ExplorationAttempt.id)))
    assert attempts == 1


@pytest.mark.asyncio
async def test_from_another_local_the_trip_goes_through_the_hub(database):
    actor, road, sessions = await _ready(database, 894504)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        (await session.get(WorldState, character.id)).location = CHARNECA
    await _feed(sessions, road, actor, callback_update("tdo:desb:bosque", actor=actor))
    assert await _location(sessions, actor) == BOSQUE


@pytest.mark.asyncio
async def test_camara_is_clickable_and_opens_its_entry(database):
    actor, road, sessions = await _ready(database, 894505)
    screen = await _feed(sessions, road, actor, callback_update("tdo:desb:camara", actor=actor))
    assert await _location(sessions, actor) == CAMARA
    assert "Câmara do Poente" in screen.text
    async with sessions() as session:
        assert await session.scalar(select(func.count(ExplorationAttempt.id))) == 0

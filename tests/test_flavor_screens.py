"""Flavor Text no fim das telas de Sistema e de Região (GDD v1.6.0 §37.4)."""

from datetime import UTC, datetime
from html import escape
from types import SimpleNamespace
from uuid import uuid4

import pytest
from aiogram import Dispatcher

from asterion.application.active_arts import ActiveArtCharacterView
from asterion.application.inventory import InventoryView
from asterion.application.legacy import LegacyView
from asterion.application.professions import ProfessionHomeView
from asterion.application.road import ALTOS_ESCARPA_LABEL, CONFINS_MARCHA_LABEL
from asterion.application.talents import TalentView
from asterion.bot import flavor_ui
from asterion.bot.character_progression_ui import render_art_root, render_talent_root
from asterion.bot.character_ui import render_character
from asterion.bot.chronicle_ui import render_calendar
from asterion.bot.creation_ui import Screen
from asterion.bot.equipment_ui import render_equipment_root
from asterion.bot.flavor_ui import CAPTION_LIMIT, with_flavor
from asterion.bot.guilds_ui import render_guild_menu
from asterion.bot.inventory_ui import render_inventory
from asterion.bot.market_ui import render_root
from asterion.bot.professions_ui import render_profession_home
from asterion.bot.world_handlers import world_router
from asterion.bot.world_ui import render_legacy
from asterion.domain.chronicle import Phase
from asterion.domain.flavor import FlavorContext, FlavorKind, select_flavor
from asterion.domain.flavor_catalog import FLAVOR_CATALOG
from asterion.domain.guilds import GuildRole
from tests.test_calendar_screen import _view as _chronicle_view
from tests.test_charneca_player_facing import _last_method, _telegram
from tests.test_creation_ui import callback_update
from tests.test_equipment_telegram_ui import _root as _equipment_root
from tests.test_guilds_telegram import _view as _guild_view

NOW_EPOCH = 1_794_500_000
CALENDAR_NOW = datetime(2026, 11, 11, 15, 0, tzinfo=UTC)


def _talent_view() -> TalentView:
    return TalentView(uuid4(), "Hero", "sentinela", 10, None, 3, 2, 1, (), 0, None, False)


def _art_view() -> ActiveArtCharacterView:
    return ActiveArtCharacterView(uuid4(), "Hero", "sentinela", 10, None, 3, (), (), False)


def _profession_view() -> ProfessionHomeView:
    return ProfessionHomeView(uuid4(), "Hero", 10, 0, None, False, None, None, (), False)


def _legacy_view() -> LegacyView:
    return LegacyView("Hero", 10, 0, 0, "1", 3, None, False, False, ())


def _inventory_view() -> InventoryView:
    return InventoryView(
        "inventory_root",
        uuid4(),
        used_slots=1,
        equipment_slots=1,
        consumable_slots=0,
        material_slots=0,
        rune_slots=0,
    )


GUILD = _guild_view(GuildRole.LEADER)  # uma vez só: o id da Guilda entra nos botões

SYSTEM_SCREENS = {
    "personagem": render_character,
    "inventario": lambda: render_inventory(_inventory_view()),
    "mercado": lambda: render_root(None),
    "equipamentos": lambda: render_equipment_root(_equipment_root()),
    "artes": lambda: render_art_root(_art_view()),
    "talentos": lambda: render_talent_root(_talent_view()),
    "oficios": lambda: render_profession_home(_profession_view()),
    "legado": lambda: render_legacy(_legacy_view()),
    "guilda": lambda: render_guild_menu(GUILD),
    "guilda_sem_guilda": lambda: render_guild_menu(None),
    "calendario": lambda: render_calendar(_chronicle_view(Phase.UNSCHEDULED, None), CALENDAR_NOW),
}


def _expected(key: str, kind=FlavorKind.SYSTEM, scope="system", now_epoch=NOW_EPOCH) -> str:
    entry = select_flavor(
        FLAVOR_CATALOG, FlavorContext(kind=kind, scope=scope, key=key, now_epoch=now_epoch)
    )
    assert entry is not None
    return f"\n\n<i>{escape(entry.text, quote=False)}</i>"


def _body(plain: Screen) -> str:
    return plain.text if plain.parse_mode == "HTML" else escape(plain.text, quote=False)


@pytest.fixture
def fixed_clock(monkeypatch):
    monkeypatch.setattr(flavor_ui, "time", SimpleNamespace(time=lambda: NOW_EPOCH + 0.7))


@pytest.mark.parametrize("name", SYSTEM_SCREENS)
def test_system_screen_ends_with_one_italic_flavor_line(name, fixed_clock, monkeypatch):
    key = name.removesuffix("_sem_guilda")
    now_epoch = int(CALENDAR_NOW.timestamp()) if key == "calendario" else NOW_EPOCH
    screen = SYSTEM_SCREENS[name]()
    monkeypatch.setattr(flavor_ui, "FLAVOR_CATALOG", ())
    plain = SYSTEM_SCREENS[name]()

    assert screen.parse_mode == "HTML"
    assert screen.text == _body(plain) + _expected(key, now_epoch=now_epoch)
    assert screen.text.count("<i>") == 1
    assert (screen.image_key, screen.keyboard) == (plain.image_key, plain.keyboard)


@pytest.mark.parametrize("name", SYSTEM_SCREENS)
def test_system_screen_without_flavor_is_unchanged(name, monkeypatch):
    monkeypatch.setattr(flavor_ui, "FLAVOR_CATALOG", ())
    screen = SYSTEM_SCREENS[name]()
    assert "<i>" not in screen.text
    assert screen.parse_mode in (None, "HTML")


def test_flavor_is_stable_inside_the_window_and_changes_screen_only_by_text():
    screen = Screen("Linha <1> & fim", "x", None)
    first = with_flavor(screen, "personagem", now_epoch=NOW_EPOCH)
    again = with_flavor(screen, "personagem", now_epoch=NOW_EPOCH + 60)
    assert first == again
    assert first.text.startswith("Linha &lt;1&gt; &amp; fim\n\n<i>")
    assert first.parse_mode == "HTML"


def test_unknown_key_and_markdown_screen_stay_unchanged():
    screen = Screen("texto", "x", None)
    assert with_flavor(screen, "sem_frase", now_epoch=NOW_EPOCH) is screen
    markdown = Screen("*texto*", "x", None, parse_mode="MarkdownV2")
    assert with_flavor(markdown, "personagem", now_epoch=NOW_EPOCH) is markdown


def test_flavor_is_skipped_when_it_would_pass_the_caption_limit():
    screen = Screen("a" * (CAPTION_LIMIT - 10), "x", None)
    assert with_flavor(screen, "personagem", now_epoch=NOW_EPOCH) is screen


class _Missions:
    def __init__(self, known=()):
        self._known = set(known)

    async def region_access(self, actor):
        return True

    async def resume(self, actor, *args):
        return None

    async def known_locations(self, actor):
        return set(self._known)


class _World:
    async def resume(self, actor):
        return None


def _region_dispatcher() -> Dispatcher:
    missions = _Missions()
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            _World(),
            {},
            vde_missions=missions,
            nareth_missions=missions,
            varzeas_missions=missions,
            altos_missions=_Missions({ALTOS_ESCARPA_LABEL, CONFINS_MARCHA_LABEL}),
        )
    )
    return dispatcher


REGIONS = ("tdo", "vde", "nareth", "varzeas", "altos", "confins")


@pytest.mark.parametrize("region", REGIONS)
async def test_region_screen_ends_with_one_italic_flavor_line(region, fixed_clock, monkeypatch):
    bot = _telegram()
    dispatcher = _region_dispatcher()
    await dispatcher.feed_raw_update(
        bot, callback_update(f"world:map:region:{region}", update_id=990001, actor=990001)
    )
    method = _last_method(bot)

    monkeypatch.setattr(flavor_ui, "FLAVOR_CATALOG", ())
    await dispatcher.feed_raw_update(
        bot, callback_update(f"world:map:region:{region}", update_id=990002, actor=990001)
    )
    plain = _last_method(bot)

    assert plain.parse_mode is None
    assert "<i>" not in plain.text
    assert method.parse_mode == "HTML"
    expected = _expected(region, kind=FlavorKind.NARRATIVE, scope="region")
    assert method.text == escape(plain.text, quote=False) + expected

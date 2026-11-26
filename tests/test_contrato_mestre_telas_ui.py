"""Contrato Mestre de Implementação das Telas UI v1.0.0: telas puras."""

from __future__ import annotations

from asterion.application.character_surfaces import KnowledgeView
from asterion.bot import map_ui, missions_ui
from asterion.bot.character_surfaces_ui import render_codex_category, render_codex_root
from asterion.bot.ui_format import identity
from asterion.domain.tdo_hub import TEXTO_CAMARA_POS_P6, TEXTO_CAMARA_PRE_P6


def _labels(screen) -> list[list[str]]:
    return [[button.text for button in row] for row in screen.keyboard.inline_keyboard]


def _callbacks(screen) -> list[str]:
    return [button.callback_data for row in screen.keyboard.inline_keyboard for button in row]


# ---- §4 Identidade -------------------------------------------------------------------


def test_identity_variants():
    full = identity(emoji="🏹", name="Oppan", level=1, legacy_level=1, guild_tag="CIN")
    assert full == (
        "🏹 <b>[CIN] Oppan</b> · <code>Nv. 1 · Legado I</code>\n"
        "🎖️ <code>Caminhante das Cinzas</code>"
    )
    assert identity(emoji="🏹", name="Oppan", level=12).startswith(
        "🏹 <b>Oppan</b> · <code>Nv. 12</code>\n"
    )
    assert "Legado V" in identity(emoji="🏹", name="Oppan", level=1, legacy_level=5)
    assert identity(emoji="🏹", name="<x>", level=1, title="Aliado").endswith("<code>Aliado</code>")
    assert "&lt;x&gt;" in identity(emoji="🏹", name="<x>", level=1)


# ---- §15 Mapa ------------------------------------------------------------------------


def test_map_root_lists_known_regions_and_returns_to_menu():
    screen = map_ui.render_map([("Terras do Ocaso", "tdo", "🌘")], back_callback="menu:back")
    assert screen.text.startswith("🗺️ <b>Mapa</b>\n\n<i>O conhecimento das terras")
    assert _labels(screen) == [["🌘 Terras do Ocaso"], ["↩️ Voltar"]]
    assert _callbacks(screen) == ["world:map:region:tdo", "menu:back"]


def test_tdo_region_lists_only_known_locals_without_level_or_brazier():
    known = {"Refúgio do Ocaso", "Charneca da Fuligem", "Câmara do Poente", "Estrada das Cinzas"}
    screen = map_ui.render_tdo_region(known)
    assert screen.text.startswith("🌘 <b>Terras do Ocaso</b>\n\n<i>Uma região marcada")
    assert _labels(screen) == [
        ["🛖 Refúgio do Ocaso"],
        ["🌫️ Charneca da Fuligem"],
        ["🏛️ Câmara do Poente"],
        ["↩️ Voltar"],
    ]
    assert "Nv." not in screen.text and "Braseiro" not in screen.text
    assert _callbacks(screen)[-1] == "world:map"
    everything = {"Refúgio do Ocaso", "Charneca da Fuligem", "Bosque Calcinado",
                  "Ruínas do Vigia", "Câmara do Poente"}
    assert [row[0] for row in _labels(map_ui.render_tdo_region(everything))][:-1] == [
        "🛖 Refúgio do Ocaso",
        "🌫️ Charneca da Fuligem",
        "🌲 Bosque Calcinado",
        "🏚️ Ruínas do Vigia",
        "🏛️ Câmara do Poente",
    ]


def test_tdo_local_is_title_description_and_back_only():
    charneca = map_ui.render_tdo_local("charneca")
    assert charneca.text == (
        "🌫️ <b>Charneca da Fuligem</b>\n\n<i>" + map_ui.CHARNECA_TEXT + "</i>"
    )
    assert _labels(charneca) == [["↩️ Voltar"]]
    assert _callbacks(charneca) == ["world:map:region:tdo"]
    assert "Ir para o Local" not in str(_labels(charneca))
    assert TEXTO_CAMARA_PRE_P6 in map_ui.render_tdo_local("camara").text
    assert TEXTO_CAMARA_POS_P6 in map_ui.render_tdo_local("camara", p6_completed=True).text
    # Sem texto canônico, nenhuma descrição é inventada.
    assert map_ui.render_tdo_local("bosque").text == "🌲 <b>Bosque Calcinado</b>"


# ---- §19 Missões ---------------------------------------------------------------------


def test_missions_entry_returns_to_the_refuge_mural():
    for any_mission in (True, False):
        assert _callbacks(missions_ui.render_entry(any_mission=any_mission))[-1] == (
            "refuge:local"
        )


# ---- §20 Códice ----------------------------------------------------------------------


def _knowledge() -> KnowledgeView:
    return KnowledgeView("vigia", (), (), (), frozenset())


def test_codex_root_has_seven_categories_and_no_counter():
    screen = render_codex_root(_knowledge())
    assert screen.text.startswith("<b>📖 Códice de Asterion</b>\n\n<i>O conhecimento")
    assert _labels(screen) == [
        ["🌌 Mundo", "🗺️ Locais"],
        ["👥 Povos", "👤 Figuras"],
        ["📜 História", "🌀 Mistérios"],
        ["📖 Crônicas"],
        ["🐾 Bestiário"],
        ["↩️ Voltar"],
    ]
    assert _callbacks(screen)[-2:] == ["kb:b", "menu:back"]
    for forbidden in ("???", "%", "0/", "Nenhuma"):
        assert forbidden not in screen.text


def test_empty_codex_category_shows_only_description_and_back():
    screen = render_codex_category(_knowledge(), "mysteries")
    assert screen.text == (
        "<b>🌀 Mistérios e Fenômenos</b>\n\n<i>Registros sobre fenômenos, mistérios e "
        "verdades ocultas que foram legitimamente descobertos pelo personagem.</i>"
    )
    assert _labels(screen) == [["↩️ Voltar"]]
    assert _callbacks(screen) == ["kb:cd"]


# ---- Ajustes pós-validação: Armazém preserva a origem ---------------------------------


def test_warehouse_back_follows_its_origin():
    from uuid import uuid4

    from asterion.application.warehouse import WarehouseView
    from asterion.bot.refuge_ui import CB_WAREHOUSE
    from asterion.bot.warehouse_ui import render_warehouse

    assert CB_WAREHOUSE == "warehouse:root:refuge"
    for accessible in (True, False):
        view = WarehouseView("warehouse_root", uuid4(), accessible, "Refúgio do Ocaso", 60, 100)
        from_refuge = render_warehouse(view, back_to_refuge=True)
        assert _labels(from_refuge)[-1] == ["↩️ Voltar"]
        assert _callbacks(from_refuge)[-1] == "refuge:local"
        from_inventory = render_warehouse(view)
        assert _labels(from_inventory)[-1] == ["← Inventário"]
        assert _callbacks(from_inventory)[-1] == "inventory:root"

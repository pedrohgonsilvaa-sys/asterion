"""Telas locais do Refúgio do Ocaso (Bloco UI 1 v1.1.0 §2).

Refúgio-local, Braseiro do Refúgio e os NPCs do abrigo. O HUD principal fica em
``world_ui.refuge_hud_text``. Regras (descanso, Proficiências, Missões) seguem nos
serviços existentes; aqui só há apresentação.
"""

from __future__ import annotations

from decimal import Decimal
from html import escape

from asterion.bot.asset_catalog import location_key, npc_key
from asterion.bot.creation_ui import Screen
from asterion.bot.ui_format import (
    HP_FILL,
    back,
    bar,
    blocks,
    button,
    column,
    keyboard,
    mono,
    narrative,
    number,
)
from asterion.domain.tdo_hub import REFUGE_LABEL

REFUGE_BRAZIER_ID = "tdo.brazier.refugio_do_ocaso"
# Bloco UI 1 §8 item 1: o Refúgio usa a arte do Refúgio, nunca a do Braseiro.
REFUGE_IMAGE_KEY = location_key(REFUGE_LABEL)

CB_LOCAL = "refuge:local"
CB_BRAZIER = "refuge:brazier"
CB_REST = "refuge:rest"
CB_DARIAN = "refuge:darian"
CB_ALDA = "refuge:alda"
CB_OREN = "refuge:oren"
CB_HUD = "menu:back"

REFUGE_TEXT = (
    "Entre as cinzas do Ocaso, este abrigo permanece como um dos poucos lugares seguros "
    "da região. Aqui estão reunidos os serviços e pessoas que mantêm o Refúgio "
    "funcionando antes que a estrada seja novamente percorrida."
)
BRAZIER_TEXT = (
    "O fogo permanece aceso entre as pedras antigas, lançando calor sobre o abrigo e "
    "mantendo este lugar seguro."
)
BRAZIER_RECOVERED_TEXT = (
    "Depois de passar algum tempo ao lado do braseiro, o calor devolve suas forças. A "
    "vitalidade se recupera e o cansaço diminui, deixando o personagem pronto para "
    "seguir novamente."
)
DARIAN_TEXT = (
    "Um homem de poucas palavras, acostumado ao peso das armas e das armaduras e ao "
    "trabalho constante de mantê-las prontas. Seu olhar atento acompanha cada movimento, "
    "como quem prefere corrigir um erro antes que ele se torne uma falha."
)
DARIAN_SERVICE_TEXT = (
    "Treinamento de armas, armaduras e escudos, com foco em técnica, preparo e "
    "aperfeiçoamento para os perigos da estrada."
)
ALDA_TEXT = (
    "Uma mulher acostumada a manter o Refúgio funcionando enquanto a estrada continua "
    "trazendo novos perigos. Alda coordena as necessidades práticas do abrigo e "
    "acompanha o que acontece além de suas fronteiras."
)
OREN_TEXT = (
    "Um homem dedicado a registrar os acontecimentos do Refúgio e preservar a memória "
    "daqueles que passam por suas portas. Oren mantém seus registros organizados e "
    "acompanha as histórias que chegam da estrada."
)
# As etapas de Missão com Alda e Oren seguem no fluxo de Missão existente (``p2:alda``,
# ``world:oren``, alcançados pelas telas de Missão via ``road:local``); as telas do
# Refúgio mostram só a descrição e ``↩️ Voltar``.


def render_refuge_local() -> Screen:
    """Refúgio-local: serviços e pessoas do abrigo. Sem Dádiva Diária."""
    text = blocks("🌘 <b>Refúgio do Ocaso</b>", narrative(REFUGE_TEXT))
    rows = column(
        button("🔥 Braseiro do Refúgio", CB_BRAZIER),
        button("⚔️ Darian Veyr", CB_DARIAN),
        button("🧭 Alda Veyr", CB_ALDA),
        button("📜 Oren Cal", CB_OREN),
    )
    return Screen(text, REFUGE_IMAGE_KEY, keyboard(*rows, back(CB_HUD)), "HTML")


def brazier_status(
    name: str, hp: Decimal | int, max_hp: Decimal | int, *, emoji: str, guild_tag: str | None
) -> str:
    """Bloco de status do Braseiro: só identidade, HP e barra (sem Vigor)."""
    tag = f"[{escape(guild_tag)}] " if guild_tag else ""
    return "\n".join(
        (
            f"<b>{emoji} {tag}{escape(name)}</b>",
            f"❤️ <b>HP</b> · {mono(f'{number(int(hp))} / {number(int(max_hp))}')}",
            bar(hp, max_hp, HP_FILL),
        )
    )


def render_refuge_brazier(
    name: str,
    hp: Decimal | int,
    max_hp: Decimal | int,
    *,
    emoji: str,
    guild_tag: str | None = None,
    recovered: bool = False,
) -> Screen:
    """Braseiro do Refúgio; ``Recuperar-se`` só aparece com HP abaixo do máximo."""
    text = blocks(
        "🔥 <b>Braseiro do Refúgio</b>",
        narrative(BRAZIER_RECOVERED_TEXT if recovered else BRAZIER_TEXT),
        brazier_status(name, hp, max_hp, emoji=emoji, guild_tag=guild_tag),
    )
    rows = [] if hp >= max_hp else column(button("🔥 Recuperar-se", CB_REST))
    return Screen(text, REFUGE_BRAZIER_ID, keyboard(*rows, back(CB_LOCAL)), "HTML")


def render_darian(*, shields: bool) -> Screen:
    """Darian Veyr: treinamento de armas, armaduras e escudos."""
    text = blocks(
        "⚔️ <b>Darian Veyr</b>", narrative(DARIAN_TEXT), narrative(DARIAN_SERVICE_TEXT)
    )
    options = [button("⚔️ Armas", "wpt:root"), button("🥋 Armaduras", "apt:root")]
    if shields:
        options.append(button("🛡️ Escudos", "wpt:shield"))
    return Screen(
        text, REFUGE_IMAGE_KEY, keyboard(*column(*options), back(CB_LOCAL)), "HTML"
    )


def _npc(title: str, text: str, image: str) -> Screen:
    return Screen(blocks(title, narrative(text)), image, keyboard(back(CB_LOCAL)), "HTML")


def render_alda() -> Screen:
    return _npc("🧭 <b>Alda Veyr</b>", ALDA_TEXT, npc_key("alda veyr"))


def render_oren() -> Screen:
    return _npc("📜 <b>Oren Cal</b>", OREN_TEXT, npc_key("oren cal"))

"""Linha de Flavor Text no fim das telas (GDD v1.6.0 §37.4).

Um único ponto para todas as telas: escolhe a frase com ``select_flavor`` e a
acrescenta em itálico no fim do texto. Sem frase elegível, a tela volta igual.
"""

from __future__ import annotations

import time
from dataclasses import replace
from html import escape

from asterion.bot.creation_ui import Screen
from asterion.domain.flavor import FlavorContext, FlavorKind, select_flavor
from asterion.domain.flavor_catalog import FLAVOR_CATALOG

# Legenda de foto no Telegram aceita no máximo 1024 caracteres. Se a frase
# fizer a tela passar disso, a tela fica sem frase em vez de quebrar o envio.
CAPTION_LIMIT = 1024


def with_flavor(
    screen: Screen,
    key: str,
    *,
    kind: FlavorKind = FlavorKind.SYSTEM,
    scope: str = "system",
    now_epoch: int | None = None,
) -> Screen:
    """Devolve ``screen`` com uma frase de Flavor em itálico no fim, se houver."""
    entry = select_flavor(
        FLAVOR_CATALOG,
        FlavorContext(
            kind=kind,
            scope=scope,
            key=key,
            flags=frozenset(),
            now_epoch=int(time.time()) if now_epoch is None else now_epoch,
        ),
    )
    if entry is None:
        return screen
    if screen.parse_mode is None:
        # Texto puro vira HTML: escapar mantém a aparência idêntica.
        body = escape(screen.text, quote=False)
    elif screen.parse_mode.upper() == "HTML":
        body = screen.text
    else:
        return screen  # Markdown não é usado nestas telas; não arrisca quebrar.
    if len(screen.text) + 2 + len(entry.text) > CAPTION_LIMIT:
        return screen
    text = f"{body}\n\n<i>{escape(entry.text, quote=False)}</i>"
    return replace(screen, text=text, parse_mode="HTML")


def with_region_flavor(screen: Screen, region_key: str, *, now_epoch: int | None = None) -> Screen:
    return with_flavor(
        screen,
        region_key,
        kind=FlavorKind.NARRATIVE,
        scope="region",
        now_epoch=now_epoch,
    )

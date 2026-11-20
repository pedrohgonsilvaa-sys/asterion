"""QA-002: telas de Missão (P2 a P6, S2 a S6) nunca oferecem Local → Local nas Terras do Ocaso.

Fonte: GDD §18.3 (hub), TdO v1.0.18 §33.1 e critério §33.16 item 18, UI v1.6.2 §66.1
(SOURCE_AUTHORITY.md, sincronizações 2026-11-14 e 2026-11-16): o Refúgio do Ocaso é o hub,
não há ligação Local–Local, e de um Local só se volta ao Refúgio.

Os testes renderizam as telas a partir de views montadas à mão (sem banco) e olham só os
botões. Regiões em que Local → Local é legítimo (Nareth, Várzeas, Altos, Confins, Vales)
ficam fora de propósito.
"""

import re
from importlib import import_module
from uuid import uuid4

import pytest

from asterion.application.road import BOSQUE, CAMARA, CHARNECA, REFUGE, ROAD, RUINS

_COMMON = ("offer", "unavailable", "completed", "combat_pending", "recovery")
# módulo -> (classe da view, função de render, tipos de tela que carregam navegação)
_SCREENS = {
    "p2": ("P2View", "render_p2", ("travel", "ash_points", "stone", "oren", "alda", *_COMMON)),
    "p3": (
        "P3View",
        "render_p3",
        ("travel", "fragments", "carved", "return", "choice", "oren", *_COMMON),
    ),
    "p4": (
        "P4View",
        "render_p4",
        ("enter_ruins", "path", "structures", "safe_route", "return", "reports", "alda", *_COMMON),
    ),
    "p5": (
        "P5View",
        "render_p5",
        (
            "travel", "follow_structures", "find_door", "elements", "record_symbol",
            "return", "reports", "alda", "oren", *_COMMON,
        ),
    ),
    "p6": (
        "P6View",
        "render_p6",
        (
            "travel_ruins", "cross_door", "enter_chamber", "travel_chamber", "inspect_before",
            "start_boss", "retry", "retry_chamber", "retry_travel", "inspect_after",
            "record_anchor", "return_refuge", "reports", "choose_reward", *_COMMON,
        ),
    ),
    "s2": (
        "S2View",
        "render_s2",
        ("oren", "fragment", "return", "abandoned", "abandon_confirm", *_COMMON),
    ),
    "s3": (
        "S3View",
        "render_s3",
        ("route", "tracks", "cargo", "report", "alda", "abandon_confirm", "detail", *_COMMON),
    ),
    "s4": (
        "S4View",
        "render_s4",
        (
            "travel", "watch_points", "orientation", "turn_point", "examine", "return",
            "report", "oren", "abandon_confirm", "detail", *_COMMON,
        ),
    ),
    "s5": (
        "S5View",
        "render_s5",
        (
            "travel", "investigate", "light_points", "record", "return", "report",
            "abandon_confirm", "detail", *_COMMON,
        ),
    ),
    "s6": (
        "S6View",
        "render_s6",
        (
            "travel_ruins", "return_refuge", "travel_refuge", "review", "marks", "shelter",
            "last_record", "report", "oren", "abandoned", *_COMMON,
        ),
    ),
}

# Locais do hub da Região, fora o Refúgio.
_HUB_LOCALS = (ROAD, CHARNECA, BOSQUE, RUINS, CAMARA)
_HUB_ROUTE_KEYS = {"road", "charneca", "bosque", "ruinas", "camara"}
_TO_LOCAL_LABEL = re.compile(
    r"^(Seguir|Retornar|Ir|Viajar)\s+(para|a|à|ao|às|aos)?\s*(a |o |as |os )?"
    r"(Estrada|Charneca|Bosque|Ruínas|Câmara do Poente)",
    re.IGNORECASE,
)


def _view(module: str, kind: str, location: str, step: int, **extra):
    cls = getattr(import_module(f"asterion.application.{module}"), _SCREENS[module][0])
    return cls(
        character_id=uuid4(),
        kind=kind,
        status="active",
        step=step,
        state_version=7,
        progress={},
        location=location,
        level=5,
        **extra,
    )


def _buttons(screen):
    keyboard = screen.keyboard
    if keyboard is None:
        return []
    return [button for row in keyboard.inline_keyboard for button in row]


def _local_to_local_buttons(buttons):
    """Botões que levam a outro Local do hub (callback de rota ou rótulo de viagem)."""
    bad = []
    for button in buttons:
        data = button.callback_data or ""
        match = re.search(r"route:(?:\d+:)?(\w+)$", data) or re.search(r"^road:route:(\w+)", data)
        target = match.group(1) if match else None
        if target in _HUB_ROUTE_KEYS or _TO_LOCAL_LABEL.match(button.text):
            bad.append((button.text, data))
    return bad


def _render_all(module: str, location: str):
    render = getattr(import_module(f"asterion.bot.{module}_ui"), _SCREENS[module][1])
    rendered = 0
    for kind in _SCREENS[module][2]:
        for step in range(1, 9):
            for awaiting in (False, True):
                extra = {"awaiting_exploration": awaiting} if module.startswith("p") else {}
                try:
                    view = _view(module, kind, location, step, **extra)
                except TypeError:
                    view = _view(module, kind, location, step)
                try:
                    screen = render(view)
                except Exception:  # noqa: BLE001 - combinação kind/step que a tela não aceita
                    continue
                rendered += 1
                yield kind, step, awaiting, screen
    assert rendered, f"{module}: nenhuma tela renderizada em {location}"


@pytest.mark.parametrize("module", sorted(_SCREENS))
@pytest.mark.parametrize("location", _HUB_LOCALS)
def test_mission_screens_from_a_local_never_offer_another_local(module, location):
    for kind, step, awaiting, screen in _render_all(module, location):
        if (module, kind) == ("p2", "travel"):
            # Estado inalcançável fora do Refúgio: accept exige REFUGE e _travel é bloqueado com
            # P2 ativa. Em REFUGE é coberto por test_p2_travel_screen_from_refuge_*.
            continue
        if (module, kind) == ("p2", "recovery"):
            continue  # tela fixa no Refúgio (texto e botão); a derrota sempre recupera lá
        bad = _local_to_local_buttons(_buttons(screen))
        assert not bad, f"{module} kind={kind} step={step} awaiting={awaiting} em {location}: {bad}"


def test_guard_detects_local_to_local_button():
    from aiogram.types import InlineKeyboardButton

    ok = InlineKeyboardButton(text="Voltar ao Refúgio", callback_data="road:route:refuge")
    assert _local_to_local_buttons([ok]) == []
    for text, data in (
        ("Seguir para o Bosque", "road:route:bosque"),
        ("Seguir para as Ruínas", "p4:7:enter"),
        ("Voltar", "p3:s3route:7:ruinas"),
    ):
        assert _local_to_local_buttons([InlineKeyboardButton(text=text, callback_data=data)])


def test_p2_travel_screen_from_refuge_offers_the_hub_edge():
    """P2 etapa 1 só nasce no Refúgio (accept exige REFUGE): existe a aresta para a Charneca."""
    render = import_module("asterion.bot.p2_ui").render_p2
    view = _view("p2", "travel", REFUGE, 1)
    buttons = _buttons(render(view))
    assert ("Seguir para a Charneca", "p2:7:travel") in [(b.text, b.callback_data) for b in buttons]

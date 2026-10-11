from uuid import uuid4

from asterion.application.road import VDE_BAIXIOS, VDE_BERCO, VDE_CLAUSTRO, RoadView
from asterion.application.vde_missions import (
    P10_ID,
    P11_ID,
    S10_ID,
    S11_ID,
    VDEMissionView,
)
from asterion.bot.road_ui import render_current_local
from asterion.bot.vde_missions_ui import render_vde_mission


def _callbacks(screen):
    return [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]


def test_p10_and_s10_mission_controls_are_specific_and_stale_safe():
    p10 = VDEMissionView(
        uuid4(), P10_ID, "Pedra sob as Raízes", "sanctuary", "active", 6, 13,
        {}, VDE_CLAUSTRO, 18,
    )
    screen = render_vde_mission(p10)
    assert "não exige explorar a masmorra" in screen.text
    assert f"vde:{P10_ID}:13:sanctuary" in _callbacks(screen)

    s10 = VDEMissionView(
        uuid4(), S10_ID, "Água sem Reflexo", "survivor", "active", 6, 22,
        {"second_explorer_status": "missing"}, VDE_BAIXIOS, 18,
    )
    screen = render_vde_mission(s10)
    assert "um dos exploradores" in screen.text
    assert "destino do segundo permanece desconhecido" in screen.text
    assert f"vde:{S10_ID}:22:survivor" in _callbacks(screen)
    assert all(len(callback.encode("utf-8")) < 64 for callback in _callbacks(screen))


def test_claustro_local_navigation_uses_existing_route_callback():
    view = RoadView(
        "vde_claustro",
        uuid4(),
        location=VDE_CLAUSTRO,
        route_destinations=(VDE_BAIXIOS,),
    )
    screen = render_current_local(view)
    assert "Claustro das Raízes" in screen.text
    assert "Seguir para os Baixios" not in screen.text
    assert "road:route:vde_baixios" in _callbacks(screen)
    assert all(len(callback.encode("utf-8")) < 64 for callback in _callbacks(screen))


def test_s11_and_p11_objective_buttons_are_compact_and_narratively_scoped():
    cases = (
        (S11_ID, "patrols", {"patrols": []}, ("pontos de patrulha",)),
        (S11_ID, "fragments", {"marking_fragments": ["1"]}, ("fragmento",)),
        (P11_ID, "pressure_points", {"pressure_points": ["a"]}, ("pontos de pressão",)),
        (P11_ID, "clear_roots", {}, ("superar as raízes",)),
        (P11_ID, "chamber", {}, ("examinar a câmara",)),
        (P11_ID, "traces", {}, ("registrar os vestígios",)),
        (P11_ID, "convergence", {}, ("seguir a convergência",)),
        (P11_ID, "open_berco", {}, ("abrir acesso ao Berço", "A Matriarca não construiu")),
    )
    for quest, kind, progress, expected in cases:
        screen = render_vde_mission(
            VDEMissionView(
                uuid4(), quest, "Missão", kind, "active", 7, 4,
                progress, VDE_CLAUSTRO, 19,
            )
        )
        assert all(text.casefold() in screen.text.casefold() for text in expected), (
            quest,
            kind,
            screen.text,
        )
        assert all(len(callback.encode("utf-8")) < 64 for callback in _callbacks(screen))
        assert all(callback != "menu:noop" for callback in _callbacks(screen))
    p11_combat = render_vde_mission(
        VDEMissionView(
            uuid4(), P11_ID, "Onde Tudo se Enreda", "combat_start", "active", 3, 5,
            {}, VDE_CLAUSTRO, 19,
        )
    )
    assert "espécie não é identificada" in p11_combat.text
    assert "Carrasco de Casca" not in p11_combat.text


def test_berco_local_only_offers_return_route():
    view = RoadView(
        "vde_berco",
        uuid4(),
        location=VDE_BERCO,
        route_destinations=(VDE_CLAUSTRO,),
        brazier_destinations=(("ignored", "Ignorado", VDE_CLAUSTRO),),
    )
    screen = render_current_local(view)
    callbacks = _callbacks(screen)
    assert "Local de clímax" in screen.text
    assert "road:route:vde_claustro" in callbacks
    assert not any(
        label in screen.text for label in ("Caçada", "Ronda", "Desbravar", "Braseiro")
    )
    assert not any("brazier" in callback for callback in callbacks)

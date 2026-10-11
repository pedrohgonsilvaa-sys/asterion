from uuid import uuid4

from asterion.application.road import VDE_BAIXIOS, VDE_CLAUSTRO, RoadView
from asterion.application.vde_missions import (
    P10_ID,
    S10_ID,
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

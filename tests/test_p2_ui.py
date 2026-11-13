from uuid import uuid4

import pytest

from asterion.application.p2 import ASH_POINT_IDS, P2View
from asterion.application.road import RoadView
from asterion.bot.p2_ui import render_p2, render_p2_mission_detail
from asterion.bot.road_ui import render_road


def _view(
    kind,
    *,
    step=1,
    version=0,
    progress=None,
    status="active",
    location="Refúgio do Ocaso",
    level=3,
    available=False,
    **kwargs,
):
    return P2View(
        character_id=uuid4(),
        kind=kind,
        status=status,
        step=step,
        state_version=version,
        progress=progress or {},
        location=location,
        level=level,
        available=available,
        **kwargs,
    )


def _buttons(screen):
    return [
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]


def test_offer_renders_canonical_mission_and_explicit_accept():
    screen = render_p2(_view("offer", status=None, step=None, available=True))

    assert "Fuligem sem Fogo" in screen.text
    assert "Missão Principal · Terras do Ocaso" in screen.text
    assert "Alda Veyr" in screen.text
    assert "Fuligem sem fogo significa" in screen.text
    assert "Investigar a fuligem sem queima recente na Charneca da Fuligem" in screen.text
    assert "XP · 3.300" in screen.text and "Coroas · 140" in screen.text
    assert "Ferro de Fuligem · 1 · Vinculado" in screen.text
    assert "Erva Cinzenta · 2 · Vinculado" in screen.text
    assert "Resíduo do Ocaso · 1 · Vinculado" in screen.text
    buttons = _buttons(screen)
    assert buttons[0].text == "Aceitar Missão"
    assert buttons[0].callback_data == "p2:0:accept"
    assert buttons[-1].text == "← Refúgio do Ocaso"


def test_offer_shows_identity_line_option_and_reply_after_the_canonical_line():
    screen = render_p2(
        _view(
            "offer",
            status=None,
            step=None,
            available=True,
            identity_lines=("— Linha de identidade.",),
            identity_options=(("rotas", "Perguntar pelas rotas antigas"),),
            identity_reply="— Resposta da Alda.",
        )
    )

    canonical = screen.text.index("Fuligem sem fogo significa")
    assert canonical < screen.text.index("Linha de identidade") < screen.text.index(
        "Resposta da Alda"
    ) < screen.text.index("🎯 Objetivo")
    buttons = _buttons(screen)
    assert buttons[0].callback_data == "p2:0:accept"
    assert buttons[1].text == "Perguntar pelas rotas antigas"
    assert buttons[1].callback_data == "p2:0:ask:rotas"
    assert buttons[-1].callback_data == "road:local"


def test_unavailable_is_neutral_and_has_no_accept_button():
    screen = render_p2(_view("unavailable", status=None, step=None, blocked_by_foreground=True))

    assert "Fuligem sem Fogo · Indisponível no momento" in screen.text
    assert "Há uma atividade em andamento." in screen.text
    assert "Nv." not in screen.text and "P1" not in screen.text and "S1" not in screen.text
    assert all(button.text != "Aceitar Missão" for button in _buttons(screen))
    assert _buttons(screen)[0].callback_data == "road:local"


def test_travel_callback_carries_authoritative_state_version():
    screen = render_p2(_view("travel", version=9))
    button = _buttons(screen)[0]

    assert "Viajar até a Charneca da Fuligem" in screen.text
    assert button.text == "Seguir para a Charneca"
    assert button.callback_data == "p2:9:travel"


def test_spider_checkpoint_offers_solo_or_confirmed_group_and_reconnect_target():
    solo_or_group = render_p2(
        _view("combat_pending", step=3, version=31, location="Charneca da Fuligem", group_size=3)
    )
    callbacks = {button.text: button.callback_data for button in _buttons(solo_or_group)}
    assert callbacks["Enfrentar Solo"] == "p2:31:solo"
    assert callbacks["Formar Grupo"] == "p2:31:group"

    pending = render_p2(
        _view(
            "combat_pending",
            step=3,
            version=32,
            location="Charneca da Fuligem",
            group_size=3,
            proposal_id=uuid4(),
            proposal_status="pending",
        )
    )
    assert "Aguardando confirmações" in pending.text
    assert _buttons(pending)[0].callback_data == "group:root"


def test_refuge_keeps_oren_and_adds_local_alda_interaction():
    screen = render_road(RoadView("refuge", uuid4(), "Refúgio do Ocaso"))
    callbacks = {button.text: button.callback_data for button in _buttons(screen)}

    assert callbacks["Alda Veyr"] == "p2:alda"
    assert callbacks["Oren Cal"] == "world:oren"


@pytest.mark.parametrize(
    ("progress", "expected_count"),
    [
        ({}, "0/3"),
        ({"ash_points": [ASH_POINT_IDS[2]]}, "1/3"),
        ({"ash_points": list(ASH_POINT_IDS[:2])}, "2/3"),
    ],
)
def test_ash_points_show_progress_and_only_unexamined_callbacks(progress, expected_count):
    screen = render_p2(_view("ash_points", step=2, version=14, progress=progress))

    assert expected_count in screen.text
    buttons = _buttons(screen)
    point_buttons = [button for button in buttons if button.callback_data.startswith('p2:14:ash:')]
    examined = progress.get("ash_points", [])
    expected_ids = [point_id for point_id in ASH_POINT_IDS if point_id not in examined]
    assert [button.callback_data for button in point_buttons] == [
        f"p2:14:ash:{point_id}" for point_id in expected_ids
    ]
    names = ("Montículo de Cinza", "Terra Revirada", "Marca na Fuligem")
    for name, point_id in zip(names, ASH_POINT_IDS, strict=True):
        if point_id in progress.get("ash_points", []):
            assert f"✅ {name}" in screen.text
        else:
            assert f"⚪ {name}" in screen.text
            assert any(button.text == name for button in point_buttons)


def test_recovery_is_contextual_and_does_not_offer_road_brazier_rest():
    screen = render_p2(_view("recovery", step=3, version=5, location="Refúgio do Ocaso"))

    assert "💀 Derrota" in screen.text and "❤️ HP · Restaurado" in screen.text
    assert "Retornar à Charneca e enfrentar a Aranha de Cinza" in screen.text
    assert "Braseiro da Estrada" not in screen.text and "Descansar" not in screen.text
    assert _buttons(screen)[0].callback_data == "p2:5:retry"


def test_stone_oren_alda_and_completion_use_versioned_actions():
    stone = render_p2(_view("stone", step=4, version=21))
    examined = render_p2(
        _view("stone", step=4, version=22, progress={"stone_examined": True})
    )
    oren = render_p2(_view("oren", step=5, version=23))
    alda = render_p2(_view("alda", step=6, version=24))
    completed = render_p2(
        _view("completed", status="completed", step=6, version=25, rewarded=True)
    )

    assert _buttons(stone)[0].callback_data == "p2:21:stone"
    assert "Examinar a Pedra Marcada" in stone.text
    assert _buttons(examined)[0].callback_data == "p2:22:refuge"
    assert "Levar o registro a Oren Cal" in examined.text
    assert _buttons(oren)[0].callback_data == "p2:23:oren"
    assert "Entregar o registro da Pedra Marcada" in oren.text
    assert _buttons(alda)[0].callback_data == "p2:24:report"
    assert "Também não vou chamá-la de escrita até termos prova." in alda.text
    assert "Concluída" in completed.text and "XP · 3.300" in completed.text
    assert _buttons(completed)[0].callback_data == "road:local"


@pytest.mark.parametrize(
    ("step", "progress", "expected"),
    [
        (1, {}, "Viajar até a Charneca da Fuligem"),
        (
            2,
            {"ash_points": [ASH_POINT_IDS[0], ASH_POINT_IDS[1]]},
            "Examinar Pontos de Fuligem · 2/3",
        ),
        (3, {}, "Derrotar a Aranha de Cinza"),
        (3, {"awaiting_retry": True}, "Retornar à Charneca"),
        (4, {}, "Examinar a Pedra Marcada"),
        (4, {"stone_examined": True}, "Levar o registro a Oren Cal"),
        (5, {}, "Falar com Oren Cal"),
        (6, {}, "Reportar a situação a Alda Veyr"),
    ],
)
def test_mission_detail_objective_is_derived_from_current_progress(step, progress, expected):
    screen = render_p2_mission_detail(
        _view("travel", step=step, progress=progress, location="Charneca da Fuligem")
    )

    assert expected in screen.text
    assert _buttons(screen)[0].callback_data == "p2:resume"
    assert _buttons(screen)[-1].callback_data == "world:missions"

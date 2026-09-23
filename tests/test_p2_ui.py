from uuid import uuid4

from asterion.application.p2 import P2View
from asterion.bot.p2_ui import render_p2


def view(
    kind="detail",
    *,
    status="active",
    step=1,
    version=5,
    progress=None,
    location="Refúgio do Ocaso",
    level=3,
    available=False,
    known=(),
):
    return P2View(
        kind=kind,
        character_id=uuid4(),
        status=status,
        step=step,
        state_version=version,
        progress=progress or {},
        location=location,
        level=level,
        available=available,
        known_locations=known,
    )


def labels(screen):
    return [button.text for row in screen.keyboard.inline_keyboard for button in row]


def test_alda_below_level_three_shows_requirement_without_mission_button():
    screen = render_p2(view(kind="alda", status="unaccepted", level=2))
    assert "📜 Fuligem sem Fogo · Indisponível" in screen.text
    assert "🔒 Requer · Nv. 3" in screen.text
    assert labels(screen) == ["← Refúgio do Ocaso"]


def test_alda_available_and_offer_require_explicit_acceptance():
    alda = render_p2(
        view(kind="alda", status="unaccepted", available=True)
    )
    assert "📜 Fuligem sem Fogo · Disponível" in alda.text
    assert labels(alda) == ["Fuligem sem Fogo", "← Refúgio do Ocaso"]

    offer = render_p2(view(kind="offer", status="unaccepted"))
    assert "✨ XP · 3.300" in offer.text
    assert "🪙 Coroas · 140" in offer.text
    assert "⛏️ Ferro de Fuligem · 1" in offer.text
    assert "🌿 Erva Cinzenta · 2" in offer.text
    assert "💧 Resíduo do Ocaso · 1" in offer.text
    assert labels(offer) == ["Aceitar Missão", "← Alda Veyr"]
    assert "Continuar" not in labels(offer)


def test_step_one_uses_normal_movement_not_map_before_discovery():
    screen = render_p2(view(step=1))
    assert "🎯 Objetivo · Viajar até a Charneca da Fuligem" in screen.text
    assert "Ir para Charneca da Fuligem" in labels(screen)
    assert "Ver no Mapa" not in labels(screen)
    assert "Travessia dos Braseiros" not in labels(screen)


def test_first_arrival_announces_discovery_once_and_uses_numeric_points():
    screen = render_p2(
        view(
            kind="arrival",
            step=2,
            progress={"points": []},
            location="Charneca da Fuligem",
            known=("tdo.location.charneca_da_fuligem",),
        )
    )
    assert "🗺️ Local · Descoberto" in screen.text
    assert "🎯 Pontos de Fuligem · 0/3" in screen.text
    assert labels(screen) == ["1", "2", "3", "← Missões"]

    reconstructed = render_p2(
        view(
            kind="objective",
            step=2,
            progress={"points": [1]},
            location="Charneca da Fuligem",
            known=("tdo.location.charneca_da_fuligem",),
        )
    )
    assert "🗺️ Local · Descoberto" not in reconstructed.text
    assert "1 ✅ Ponto de Fuligem · Examinado" in reconstructed.text
    assert labels(reconstructed) == ["2", "3", "← Missões"]


def test_step_four_five_six_use_specific_actions_only():
    stone = render_p2(
        view(kind="objective", step=4, location="Charneca da Fuligem")
    )
    assert labels(stone) == ["Examinar Pedra Marcada", "← Missões"]

    step_five = render_p2(
        view(kind="objective", step=5, location="Refúgio do Ocaso")
    )
    assert labels(step_five) == ["Oren Cal", "Ver no Mapa", "← Missões"]

    oren = render_p2(
        view(kind="oren", step=5, location="Refúgio do Ocaso")
    )
    assert labels(oren) == ["Entregar Registro", "← Refúgio do Ocaso"]

    reported = render_p2(
        view(kind="oren_reported", step=6, location="Refúgio do Ocaso")
    )
    assert "Esta marca não é decoração." in reported.text
    assert labels(reported) == ["Alda Veyr", "← Refúgio do Ocaso"]

    alda = render_p2(
        view(kind="alda", step=6, location="Refúgio do Ocaso")
    )
    assert labels(alda) == ["Reportar a Alda", "← Refúgio do Ocaso"]


def test_p2_completion_receipt_matches_approved_shell():
    screen = render_p2(
        view(
            kind="completed",
            status="completed",
            step=6,
            location="Refúgio do Ocaso",
        )
    )
    assert "✅ Fuligem sem Fogo · Concluída" in screen.text
    assert "📖 Códice · Marcas na Fuligem" in screen.text
    assert labels(screen) == ["← Refúgio do Ocaso"]
    assert "OK" not in labels(screen)
    assert "Continuar" not in labels(screen)


def test_p2_defeat_points_to_refuge_without_revealing_charneca_brazier():
    screen = render_p2(
        view(
            kind="objective",
            step=3,
            progress={"defeat": True, "recovery": True},
            location="Refúgio do Ocaso",
        )
    )
    assert "💀 Derrota" in screen.text
    assert "🔥 Braseiro do Refúgio" in screen.text
    assert "Braseiro do Vento Morto" not in screen.text

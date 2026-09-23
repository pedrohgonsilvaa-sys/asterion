from uuid import uuid4

from asterion.application.s1 import S1View
from asterion.bot.s1_ui import render_s1


def view(
    kind="detail",
    *,
    status="active",
    step=1,
    version=4,
    progress=None,
    tracked=False,
    location="Estrada das Cinzas",
    level=2,
    available=False,
    reacceptable=False,
    fragment_owned=False,
    fragment_new=False,
):
    return S1View(
        kind=kind,
        character_id=uuid4(),
        status=status,
        step=step,
        state_version=version,
        progress=progress or {},
        tracked=tracked,
        location=location,
        level=level,
        available=available,
        reacceptable=reacceptable,
        fragment_owned=fragment_owned,
        fragment_new_this_attempt=fragment_new,
    )


def labels(screen):
    return [button.text for row in screen.keyboard.inline_keyboard for button in row]


def callbacks(screen):
    return [button.callback_data for row in screen.keyboard.inline_keyboard for button in row]


def test_s1_offer_requires_explicit_official_accept_button():
    screen = render_s1(
        view(kind="offer", status="unaccepted", available=True, location="Refúgio do Ocaso")
    )
    assert "— Luz é uma coisa simples quando há fogo." in screen.text
    assert "✨ XP · 1.140" in screen.text
    assert labels(screen) == ["Aceitar Missão", "← Oren Cal"]
    assert "Continuar" not in labels(screen)


def test_s1_initial_detail_and_tracking_labels_are_official():
    screen = render_s1(view(progress={"points": []}))
    assert "🕯️ Luzes sob as Cinzas · Em Andamento" in screen.text
    assert "🎯 Pontos Marcados · 0/3" in screen.text
    assert labels(screen) == [
        "Acompanhar",
        "Ver Objetivo",
        "Ver no Mapa",
        "Abandonar Missão",
        "← Missões",
    ]
    tracked = render_s1(view(progress={"points": [1]}, tracked=True))
    assert "🎯 Pontos Marcados · 1/3" in tracked.text
    assert "Deixar de Acompanhar" in labels(tracked)


def test_s1_point_shell_uses_numeric_buttons_only_for_pending_points():
    screen = render_s1(
        view(
            kind="objective",
            step=1,
            progress={"points": [1]},
            location="Estrada das Cinzas",
        )
    )
    assert "1 ✅ Ponto Marcado · Investigado" in screen.text
    assert "2 📍 Ponto Marcado · Pendente" in screen.text
    assert "3 📍 Ponto Marcado · Pendente" in screen.text
    assert labels(screen) == ["2", "3", "← Luzes sob as Cinzas"]
    assert "Continuar" not in labels(screen)


def test_s1_point_shell_outside_road_has_no_progress_callback():
    screen = render_s1(
        view(
            kind="objective",
            step=1,
            progress={"points": [1]},
            location="Refúgio do Ocaso",
        )
    )
    assert labels(screen) == ["Ver no Mapa", "← Luzes sob as Cinzas"]
    assert not any(":point:" in callback for callback in callbacks(screen))


def test_s1_steps_two_three_and_four_use_specific_actions():
    ashes = render_s1(view(kind="objective", step=2))
    assert labels(ashes) == ["Examinar Cinzas", "← Luzes sob as Cinzas"]
    light = render_s1(view(kind="objective", step=3))
    assert labels(light) == ["Observar Luz", "← Luzes sob as Cinzas"]
    away = render_s1(
        view(kind="objective", step=4, location="Estrada das Cinzas")
    )
    assert labels(away) == ["Ver no Mapa", "← Luzes sob as Cinzas"]


def test_s1_oren_states_available_active_return_reacceptable_completed():
    available = render_s1(
        view(
            kind="oren",
            status="unaccepted",
            location="Refúgio do Ocaso",
            available=True,
        )
    )
    assert "Luzes sob as Cinzas · Disponível" in available.text
    assert labels(available) == ["Luzes sob as Cinzas", "← Refúgio do Ocaso"]

    active = render_s1(
        view(kind="oren", step=2, location="Refúgio do Ocaso")
    )
    assert "Luzes sob as Cinzas · Em Andamento" in active.text
    assert labels(active) == ["← Refúgio do Ocaso"]

    returning = render_s1(
        view(kind="oren", step=4, location="Refúgio do Ocaso")
    )
    assert "🎯 Objetivo · Retornar a Oren Cal" in returning.text
    assert labels(returning) == ["Falar com Oren", "← Refúgio do Ocaso"]

    reacceptable = render_s1(
        view(
            kind="oren",
            status="abandoned",
            location="Refúgio do Ocaso",
            reacceptable=True,
        )
    )
    assert "Luzes sob as Cinzas · Reaceitável" in reacceptable.text
    assert labels(reacceptable) == ["Luzes sob as Cinzas", "← Refúgio do Ocaso"]

    completed = render_s1(
        view(kind="oren", status="completed", location="Refúgio do Ocaso")
    )
    assert "✅ Luzes sob as Cinzas · Concluída" in completed.text
    assert labels(completed) == ["← Refúgio do Ocaso"]


def test_s1_abandon_confirmation_uses_reiniciado_wording():
    screen = render_s1(view(kind="abandon_confirm", step=3))
    assert "Progresso · Reiniciado" in screen.text
    assert "Reaceitação · Disponível com Oren Cal" in screen.text
    assert "Perdido" not in screen.text
    assert labels(screen) == ["Confirmar Abandono", "← Luzes sob as Cinzas"]


def test_s1_completion_only_announces_new_fragment_when_new_in_attempt():
    new = render_s1(
        view(
            kind="completed",
            status="completed",
            step=4,
            location="Refúgio do Ocaso",
            fragment_owned=True,
            fragment_new=True,
        )
    )
    assert "📖 Códice · Estrada das Cinzas atualizada" in new.text
    assert "📖 Trecho · Luzes na Estrada" in new.text
    assert labels(new) == ["← Refúgio do Ocaso"]

    existing = render_s1(
        view(
            kind="completed",
            status="completed",
            step=4,
            location="Refúgio do Ocaso",
            fragment_owned=True,
            fragment_new=False,
        )
    )
    assert "📖 Trecho · Luzes na Estrada" not in existing.text

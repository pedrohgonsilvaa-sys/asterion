from decimal import Decimal
from uuid import uuid4

from asterion.application.road import CHARNECA, REFUGE, ROAD, RoadView
from asterion.application.round import RoundView
from asterion.bot.road_ui import render_road, render_round_selection


def _callbacks(screen):
    if screen.keyboard is None:
        return []
    return [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]


def test_hunt_is_manual_and_round_is_opened_from_local():
    prepare = render_road(
        RoadView(
            "hunt_prepare",
            uuid4(),
            ROAD,
            name="Heroa",
            hp=Decimal("702"),
            max_hp=Decimal("702"),
            vigor=100,
            max_vigor=100,
        )
    )
    road = render_road(RoadView("road", uuid4(), ROAD, familiar=True))
    callbacks = [
        button.callback_data
        for screen in (prepare, road)
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]
    assert "road:unavailable:group" not in callbacks
    assert "world:round" in callbacks
    assert all(not callback.startswith("road:round:new:") for callback in callbacks)
    assert all(callback != "menu:noop" for callback in callbacks)



def test_round_batch_selection_uses_numbered_list_and_numeric_buttons():
    screen = render_round_selection(RoadView("road", uuid4(), ROAD, familiar=True))
    assert "1 · 5 Encontros" in screen.text
    assert "2 · 10 Encontros" in screen.text
    assert "3 · 20 Encontros" in screen.text
    buttons = [
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if (button.callback_data or "").startswith("road:round:new:")
    ]
    assert [button.text for button in buttons] == ["1", "2", "3"]



def test_refuge_keeps_oren_accessible_after_p1():
    screen = render_road(RoadView("refuge", uuid4(), "Refúgio do Ocaso"))
    labels = [
        button.text
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]
    callbacks = [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]
    assert "Oren Cal" in labels
    assert "world:oren" in callbacks


def test_charneca_local_exposes_only_unlocked_round_and_regional_route():
    locked = render_road(
        RoadView(
            "charneca",
            uuid4(),
            CHARNECA,
            familiar=False,
            route_available=True,
        )
    )
    assert "📍 Local Atual\n🌑 Charneca da Fuligem" in locked.text
    assert "Terras do Ocaso · Nv. 3–5" in locked.text
    assert "Ronda de Caça · Vença uma Caçada neste Local" in locked.text
    assert "world:map:fromlocal" in _callbacks(locked)
    assert "road:route:refuge" not in _callbacks(locked)
    assert not any(value.startswith("road:round:new:") for value in _callbacks(locked))
    assert not any("Cripta" in value for value in _callbacks(locked))

    familiar = render_road(
        RoadView(
            "charneca",
            uuid4(),
            CHARNECA,
            familiar=True,
            route_available=True,
            brazier_id="tdo.brazier.vento_morto",
            brazier_label="Braseiro do Vento Morto",
            brazier_destinations=(
                ("tdo.brazier.refugio_do_ocaso", "Braseiro do Refúgio", REFUGE),
            ),
        )
    )
    assert "Ronda de Caça · Disponível" in familiar.text
    assert "Braseiro do Vento Morto · Descoberto" in familiar.text
    assert "world:round" in _callbacks(familiar)
    assert "road:round:new:5" not in _callbacks(familiar)
    assert "world:map:fromlocal" in _callbacks(familiar)


def test_charneca_hunt_and_explore_recovery_never_offer_retry():
    hunt = render_road(
        RoadView(
            "hunt_defeat",
            uuid4(),
            CHARNECA,
            recovery_brazier="Braseiro do Refúgio",
            recovery_location=REFUGE,
            route_available=True,
        )
    )
    assert "💀 Caçada · Derrota" in hunt.text
    assert "🔥 Braseiro do Refúgio" in hunt.text
    assert "Refúgio do Ocaso · Terras do Ocaso" in hunt.text
    assert "road:route:charneca" in _callbacks(hunt)
    assert "road:prepare" not in _callbacks(hunt)

    explore = render_road(
        RoadView(
            "exploration",
            uuid4(),
            CHARNECA,
            result_text="A tentativa terminou em derrota.",
            recovery_brazier="Braseiro do Vento Morto",
            recovery_location=CHARNECA,
        )
    )
    assert "💀 Desbravar · Derrota" in explore.text
    assert "🔥 Braseiro do Vento Morto" in explore.text
    assert "road:explore" not in _callbacks(explore)
    assert "road:route:charneca" not in _callbacks(explore)

    estrada_defeat = render_road(
        RoadView("hunt_defeat", uuid4(), ROAD, recovery_brazier=None)
    )
    assert "road:prepare" not in _callbacks(estrada_defeat)
    assert _callbacks(estrada_defeat) == ["road:local"]


def test_charneca_round_screens_use_frozen_local_and_regional_recovery():
    prepare = render_road(
        RoundView(
            kind="round_prepare",
            character_id=uuid4(),
            location=CHARNECA,
            round_id=uuid4(),
            state_version=4,
            batch_size=10,
            vigor=70,
            max_vigor=100,
            hp=Decimal("500"),
            max_hp=Decimal("702"),
        )
    )
    assert "Charneca da Fuligem" in prepare.text
    assert "Terras do Ocaso · Nv. 3–5" in prepare.text

    refuge_defeat = render_road(
        RoundView(
            kind="round_defeated",
            character_id=uuid4(),
            location=CHARNECA,
            round_id=uuid4(),
            recovery_brazier="Braseiro do Refúgio",
            recovery_location=REFUGE,
            route_available=True,
            batch_size=5,
        )
    )
    assert "🔥 Braseiro do Refúgio" in refuge_defeat.text
    assert "road:route:charneca" in _callbacks(refuge_defeat)
    assert "p2" != refuge_defeat.image_key

    charneca_defeat = render_road(
        RoundView(
            kind="round_defeated",
            character_id=uuid4(),
            location=CHARNECA,
            round_id=uuid4(),
            recovery_brazier="Braseiro do Vento Morto",
            recovery_location=CHARNECA,
            batch_size=5,
        )
    )
    assert "🔥 Braseiro do Vento Morto" in charneca_defeat.text
    assert "road:route:charneca" not in _callbacks(charneca_defeat)
    assert "road:round:back:" in _callbacks(charneca_defeat)[0]

from decimal import Decimal
from uuid import uuid4

from asterion.application.road import ROAD, RoadView
from asterion.bot.road_ui import render_road


def test_group_stays_unavailable_but_round_callbacks_are_live():
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
    assert "road:unavailable:group" in callbacks
    assert "road:round:new:5" in callbacks
    assert "road:round:new:10" in callbacks
    assert "road:round:new:20" in callbacks
    assert all("road:unavailable:round" not in callback for callback in callbacks)
    assert all(callback != "menu:noop" for callback in callbacks)



def test_round_batch_selection_uses_numbered_list_and_numeric_buttons():
    screen = render_road(RoadView("road", uuid4(), ROAD, familiar=True))
    assert "1 🏕️ Ronda · 5 Encontros" in screen.text
    assert "2 🏕️ Ronda · 10 Encontros" in screen.text
    assert "3 🏕️ Ronda · 20 Encontros" in screen.text
    buttons = [
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if (button.callback_data or "").startswith("road:round:new:")
    ]
    assert [button.text for button in buttons] == ["1", "2", "3"]

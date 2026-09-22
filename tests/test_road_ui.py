from decimal import Decimal
from uuid import uuid4

from asterion.application.road import ROAD, RoadView
from asterion.bot.road_ui import render_road


def test_temporary_group_and_round_callbacks_are_explicitly_unavailable():
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
    assert "road:unavailable:round:5" in callbacks
    assert "road:unavailable:round:10" in callbacks
    assert "road:unavailable:round:20" in callbacks
    assert all(callback != "menu:noop" for callback in callbacks)

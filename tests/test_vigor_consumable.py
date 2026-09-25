from datetime import UTC, date, datetime

from asterion.application.consumables import daily_consumable_cycle


def test_vigor_cycle_rolls_at_six_am_sao_paulo():
    before_boundary = datetime(2026, 9, 24, 8, 59, 59, tzinfo=UTC)
    at_boundary = datetime(2026, 9, 24, 9, 0, tzinfo=UTC)

    assert daily_consumable_cycle(before_boundary) == date(2026, 9, 23)
    assert daily_consumable_cycle(at_boundary) == date(2026, 9, 24)

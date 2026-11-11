"""Menu → Calendário: cycle times (GDD §34) and the screen (GDD §37.2)."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from asterion.application.chronicle import ChronicleView
from asterion.bot.chronicle_ui import render_calendar
from asterion.domain.calendar_cycles import next_daily_reset, next_new_vigil
from asterion.domain.chronicle import Phase, calendar_for

SP = ZoneInfo("America/Sao_Paulo")


def sp(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=SP)


def test_daily_reset_is_next_six_am():
    assert next_daily_reset(sp(2026, 11, 11, 5, 59)) == sp(2026, 11, 11, 6)
    assert next_daily_reset(sp(2026, 11, 11, 6, 1)) == sp(2026, 11, 12, 6)
    assert next_daily_reset(sp(2026, 11, 11, 23, 59)) == sp(2026, 11, 12, 6)


def test_daily_reset_exactly_at_six_goes_to_next_day():
    assert next_daily_reset(sp(2026, 11, 11, 6)) == sp(2026, 11, 12, 6)


def test_new_vigil_is_next_monday_six_am():
    # 2026-11-11 is a wednesday; the next monday is 2026-11-16.
    assert sp(2026, 11, 11).weekday() == 2
    assert next_new_vigil(sp(2026, 11, 11, 12)) == sp(2026, 11, 16, 6)
    # Sunday night.
    assert next_new_vigil(sp(2026, 11, 15, 23, 59)) == sp(2026, 11, 16, 6)


def test_new_vigil_on_monday_before_and_at_reset():
    assert next_new_vigil(sp(2026, 11, 16, 5, 59)) == sp(2026, 11, 16, 6)
    assert next_new_vigil(sp(2026, 11, 16, 6)) == sp(2026, 11, 23, 6)
    assert next_new_vigil(sp(2026, 11, 16, 12)) == sp(2026, 11, 23, 6)


def test_times_follow_sao_paulo_zone_not_the_input_zone():
    # 08:59 UTC is 05:59 in Sao Paulo (UTC-3), still before the 06:00 reset.
    now = datetime(2026, 11, 11, 8, 59, tzinfo=UTC)
    assert next_daily_reset(now) == sp(2026, 11, 11, 6)
    assert next_daily_reset(now + timedelta(minutes=1)) == sp(2026, 11, 12, 6)


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError):
        next_daily_reset(datetime(2026, 11, 11, 12))


def _view(phase, calendar):
    return ChronicleView(
        phase=phase,
        calendar=calendar,
        chapters_open=0,
        gate_ok=False,
        chapters=(),
        points=0,
        milestones=0,
        claimable=0,
        vote=None,
        outcome=None,
        layers=frozenset(),
    )


NOW = datetime(2026, 11, 11, 15, 0, tzinfo=UTC)  # 12:00 in Sao Paulo, a wednesday


def test_calendar_screen_without_day_one_still_shows_cycles():
    screen = render_calendar(_view(Phase.UNSCHEDULED, None), NOW)
    assert "Reset diário · 12/11 às 06:00" in screen.text
    assert "Nova Vigília · 16/11 às 06:00" in screen.text
    assert "Sem data ainda" in screen.text


def test_calendar_screen_by_phase():
    calendar = calendar_for(date(2026, 11, 14))
    assert "Começa em" in render_calendar(_view(Phase.SCHEDULED, calendar), NOW).text
    assert "Em andamento · termina em" in render_calendar(_view(Phase.ACTIVE, calendar), NOW).text
    assert "resgate da Trilha até" in render_calendar(_view(Phase.RESCUE, calendar), NOW).text
    assert "Arquivada" in render_calendar(_view(Phase.ARCHIVED, calendar), NOW).text


def test_calendar_screen_buttons_lead_to_chronicle_and_menu():
    screen = render_calendar(_view(Phase.UNSCHEDULED, None), NOW)
    callbacks = [b.callback_data for row in screen.keyboard.inline_keyboard for b in row]
    assert callbacks == ["cr:root", "menu:back"]

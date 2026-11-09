"""Telegram screens of the Crônica, Trilha, vote and Salão da Vigília."""

from __future__ import annotations

from datetime import date, timedelta

from asterion.application.chronicle import (
    ChapterView,
    ChronicleView,
    ClaimResult,
    HallRow,
    HallView,
    ObjectiveView,
    TrackView,
    VoteView,
)
from asterion.application.engagement import Granted, GrantedItem
from asterion.bot.benefits_ui import render_benefits
from asterion.bot.chronicle_ui import (
    error_text,
    render_chapter,
    render_chronicle,
    render_hall,
    render_trail,
    render_vote,
)
from asterion.domain.chronicle import (
    CHAPTERS,
    VOTE_OPTIONS,
    VOTE_TEXTS,
    Layer,
    Outcome,
    Phase,
    calendar_for,
    objectives_of,
)

CAL = calendar_for(date(2026, 12, 1))


def _buttons(screen) -> list[str]:
    return [b.callback_data for row in screen.keyboard.inline_keyboard for b in row]


def _chapter(number: int, done: set[str], *, level: int = 10) -> ChapterView:
    chapter = CHAPTERS[number - 1]
    objectives = tuple(
        ObjectiveView(item, item.objective_id in done, level < item.min_level)
        for item in objectives_of(number)
    )
    concluded = chapter.conclusion_id in done
    return ChapterView(
        number,
        chapter.title,
        chapter.summary,
        chapter.conclusion,
        objectives,
        concluded,
        not concluded and all(o.done for o in objectives if o.objective.required),
    )


def _view(phase=Phase.ACTIVE, chapters=(), vote=None, outcome=None, layers=frozenset()):
    return ChronicleView(
        phase, CAL, len(chapters), True, tuple(chapters), 500, 5, 2, vote, outcome, layers
    )


def test_unscheduled_and_scheduled_screens():
    unscheduled = ChronicleView(
        Phase.UNSCHEDULED, None, 0, False, (), 0, 0, 0, None, None, frozenset()
    )
    assert "ainda não tem data" in render_chronicle(unscheduled).text
    assert "Começa em 01/12 às 06:00" in render_chronicle(_view(Phase.SCHEDULED)).text


def test_chronicle_lists_open_chapters_and_trilha():
    screen = render_chronicle(_view(chapters=[_chapter(1, {"cap_01_conclusao"})]))
    assert "CONVERGÊNCIA" in screen.text
    assert "🎁 2 recompensa(s)" in screen.text
    assert {"cr:ch:1", "cr:trail", "bn:root"} <= set(_buttons(screen))


def test_chapter_offers_conclusion_only_when_mandatory_objectives_are_done():
    required = {item.objective_id for item in objectives_of(1)}
    assert "cr:conclude:1" in _buttons(render_chapter(_view(), _chapter(1, required)))
    assert "cr:conclude:1" not in _buttons(render_chapter(_view(), _chapter(1, set())))
    locked = render_chapter(_view(), _chapter(4, set(), level=4))
    assert "⏳ Requer Nv. 5" in locked.text


def test_vote_screen_shows_cost_footer_and_c3_only_with_the_layer():
    vote = VoteView("main", True, 4, 1, Outcome.SELAR, VOTE_OPTIONS, CAL.vote_closes_at, False)
    base = render_vote(_view(vote=vote))
    assert "Nenhuma resposta cura o mundo" in base.text
    assert "seu voto" in base.text
    assert VOTE_TEXTS[Outcome.SELAR].c3 not in base.text
    assert len([b for b in _buttons(base) if b.startswith("cr:vote:")]) == 4
    deep = render_vote(_view(vote=vote, layers=frozenset({Layer.C3})))
    assert VOTE_TEXTS[Outcome.SELAR].c3 in deep.text
    ineligible = VoteView("main", False, 2, 0, None, VOTE_OPTIONS, CAL.vote_closes_at, False)
    screen = render_vote(_view(vote=ineligible))
    assert "(2/4)" in screen.text and not any(b.startswith("cr:vote:") for b in _buttons(screen))


def test_outcome_epilogue_after_t():
    screen = render_chronicle(_view(Phase.CLOSING, outcome=Outcome.EM_ESPERA))
    assert "A pergunta continua aberta" in screen.text


def test_trail_screen_and_claim_result():
    view = TrackView(
        Phase.ACTIVE, 400, 4, False, frozenset(), (("free", 2), ("free", 4)), 50, 150, True
    )
    screen = render_trail(view)
    assert "Pontos · 400/4000 · Marco 4/40" in screen.text
    assert "Título Ouvinte dos Ecos" in screen.text
    assert "cr:trail:claim" in _buttons(screen)
    result = ClaimResult(
        (("free", 2),), Granted(250, (GrantedItem("Ferro", 3),)), ("Contador de Pulsos",)
    )
    claimed = render_trail(view, result)
    assert "🪙 250 Coroas" in claimed.text and "🎖️ Contador de Pulsos" in claimed.text


def test_hall_screen():
    assert "Nenhuma Crônica" in render_hall(HallView(None, (), (), None)).text
    row = HallRow(1, "Ana", 2600, "Arauto II", 25, 0, True, "Arauto II")
    guild = HallRow(1, "Cinzas", 1620, None, 11, 22, True, None)
    screen = render_hall(HallView("cr01", (row,), (guild,), row))
    assert "1. Ana · Arauto II · 2600 Renome · 🎁 Arauto II" in screen.text
    assert "1. Cinzas · 22 pts · 11 batalhas · 🎁 Elegível" in screen.text


def test_benefits_links_the_trilha_and_errors_are_translated():
    assert "cr:trail" in _buttons(render_benefits())
    assert "P1" in error_text("chronicle_gate")
    assert error_text("whatever") == "Esta ação não está mais disponível."
    assert CAL.end_at - CAL.starts_at < timedelta(days=56)

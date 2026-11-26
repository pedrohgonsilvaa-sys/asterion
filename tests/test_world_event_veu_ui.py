"""Telas de A Ruptura do Véu: texto e botões da especificação v1.3.0 (sem banco)."""

from __future__ import annotations

from datetime import UTC, datetime

from asterion.application.world_event_veu_views import (
    EnemyBar,
    HistoryLine,
    NucleusLine,
    NucleusScreen,
    PanelView,
    ParticipantRow,
    ParticipantsPage,
)
from asterion.bot import world_event_veu_ui as ui


def _callbacks(screen) -> list[str]:
    return [b.callback_data for row in screen.keyboard.inline_keyboard for b in row]


def _screen(**over) -> NucleusScreen:
    base = dict(
        key="A", name="O Primeiro Rasgo", state="ATIVA", round_number=12, seconds_left=8,
        enemies=(EnemyBar("VEU-01", "Mandíbula de Vigília", 6840, 9000, False),),
        self_name="Ardan", self_hp=842, self_max_hp=1180, art_slots=(1, 2),
        acted=False, waiting=False, removed=False, telegraphs=(), history=(),
    )
    base.update(over)
    return NucleusScreen(**base)


def test_panel_lists_active_nuclei_without_recommending_any():
    view = PanelView(
        "active", datetime(2026, 11, 24, 15, tzinfo=UTC), None, "EM_ANDAMENTO", 2, 1122, True,
        None,
        (
            NucleusLine("D", "A Coluna", "derrubar uma manifestação vertical", 7, "ATIVA"),
            NucleusLine("E", "O Interior", "romper a casca de uma manifestação", 3, "ATIVA"),
        ),
    )
    screen = ui.render_panel(view)
    assert "⚔️ Fase atual · <code>2/3</code>" in screen.text
    assert "⏳ Tempo restante · <code>18:42</code>" in screen.text
    assert "Escolha um Núcleo para participar." in screen.text
    assert "👥 7 participantes" in screen.text and "<code>7" not in screen.text
    assert _callbacks(screen) == ["veu:n:D", "veu:n:E", "wev:hub"]
    assert "recomend" not in screen.text.lower()


def test_scheduled_panel_matches_the_list_layout():
    view = PanelView("scheduled", datetime(2026, 11, 24, 23, tzinfo=UTC))
    screen = ui.render_panel(view)
    assert screen.text.startswith("🕳️ <b>Ruptura do Véu</b>")
    assert "🕐 <b>Próxima Ruptura</b> · <code>20:00</code>" in screen.text
    assert _callbacks(screen) == ["wev:hub"]


def test_nucleus_screen_follows_the_closed_combat_pattern():
    screen = ui.render_nucleus(
        _screen(
            history=(
                HistoryLine("enemy_damaged", "Mandíbula de Vigília", 312),
                HistoryLine("barrier_absorbed", "", 72),
            )
        )
    )
    text = screen.text
    assert "<code>Turno 12</code> · ⏱️ <code>00:08</code>" in text
    assert "❤️ <code>6.840/9.000</code>" in text
    assert "🟥🟥🟥🟥🟥🟥🟥⬜⬜⬜" in text
    assert "❤️ <code>842/1.180</code>" in text  # HP próprio sempre visível
    assert "📜 <b>Histórico:</b>" in text
    assert "⚔️ Mandíbula de Vigília sofreu <b>312 de dano</b>." in text
    assert "🛡️ A barreira absorveu <b>72 de dano</b>." in text
    assert "🤝" not in text  # sem suporte: seção omitida
    assert "Sua Ação" not in text and "Alterar" not in text
    assert _callbacks(screen) == [
        "veu:a:atk:A:12", "veu:a:def:A:12", "veu:a:art1:A:12", "veu:a:art2:A:12",
        "veu:p:A:0", "veu:back",
    ]


def test_inactive_nucleus_only_offers_the_way_back():
    screen = ui.render_nucleus(_screen(state="RESOLVIDA"))
    assert _callbacks(screen) == ["veu:back"]


def test_targets_are_listed_only_for_living_enemies():
    view = _screen(
        enemies=(
            EnemyBar("VEU-01", "Mandíbula de Vigília", 10, 9000, False),
            EnemyBar("VEU-02", "Oito-Pulsos", 0, 9000, True),
            EnemyBar("VEU-03", "Costela Andante", 50, 9000, False),
        )
    )
    screen = ui.render_targets(view, "atk")
    assert "🎯 <b>Escolha o alvo</b>" in screen.text
    assert _callbacks(screen) == ["veu:t:atk:A:12:VEU-01", "veu:t:atk:A:12:VEU-03", "veu:n:A"]


def test_participants_page_has_hp_bar_and_pagination_without_effects():
    rows = tuple(ParticipantRow(f"Nome{i}", "tecelao", 390, 980) for i in range(5))
    first = ui.render_participants(ParticipantsPage("A", 0, 2, rows))
    assert first.text.count("❤️") == 5 and "🟥🟥🟥⬜⬜⬜⬜⬜⬜⬜" in first.text
    assert _callbacks(first) == ["veu:p:A:1", "veu:n:A"]
    last = ui.render_participants(ParticipantsPage("A", 1, 2, rows[:2]))
    assert _callbacks(last) == ["veu:p:A:0", "veu:n:A"]
    assert "debuff" not in first.text.lower()
    assert "· Tecelão" in first.text  # nome canônico da Classe, com acento


def test_pre_event_notices_use_the_closed_texts():
    ten = ui.render_notice(10)
    assert "Algo desconhecido está atravessando para este lado." in ten.text
    assert "⏰ O evento começa em <code>10 minutos</code>." in ten.text
    assert _callbacks(ten) == ["veu:hub"]
    assert ten.keyboard.inline_keyboard[0][0].text == "🌫️ Ver Evento"
    five = ui.render_notice(5)
    assert "O Véu está cedendo. A manifestação se aproxima." in five.text
    assert five.keyboard.inline_keyboard[0][0].text == "🌫️ Entrar no Evento"


def test_final_screens_use_victory_and_failure_texts():
    won = ui.render_panel(
        PanelView("final", None, None, "ENCERRADO", 3, 0, True, victory=True,
                  reward={"crowns": 1200, "xp": 300, "items": []}, eligible=True)
    )
    assert "O Véu permanece. Por enquanto." in won.text and "1.200" in won.text
    lost = ui.render_panel(PanelView("final", None, None, "ENCERRADO", 2, 0, True, victory=False))
    assert "A ruptura não foi contida a tempo." in lost.text
    assert "Coroas" not in lost.text


def test_router_registers_every_callback_family_used_by_the_screens():
    from asterion.bot.world_event_veu_handlers import veu_event_router

    router = veu_event_router(object(), object(), {})
    assert len(router.callback_query.handlers) == 8  # wev:hub, hub, back, n, a, ta, t, p

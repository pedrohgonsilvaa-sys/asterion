from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from asterion.application.road import ROAD
from asterion.application.round import RoundView
from asterion.bot.road_ui import render_road


def _view(kind: str, **changes):
    values = dict(
        kind=kind,
        character_id=uuid4(),
        location=ROAD,
        round_id=uuid4(),
        state_version=3,
        batch_size=10,
        completed_encounters=3,
        vigor=72,
        max_vigor=100,
        name="Heroa",
        hp=Decimal("420"),
        max_hp=Decimal("702"),
    )
    values.update(changes)
    return RoundView(**values)


def _callbacks(screen):
    if screen.keyboard is None:
        return []
    return [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]


def test_round_prepare_uses_approved_summary_and_actions():
    screen = render_road(
        _view(
            "round_prepare",
            prepared_heal=True,
            prepared_purify=True,
        )
    )
    assert "🏕️ Ronda de Caça" in screen.text
    assert "🎯 Ronda · 10 Encontros" in screen.text
    assert "⏱️ Cadência · 3 min por Encontro" in screen.text
    assert "🧪 Consumíveis · Cura + Purificação" in screen.text
    callbacks = _callbacks(screen)
    assert any(value.startswith("road:round:cons:") for value in callbacks)
    assert any(value.startswith("road:round:start:") for value in callbacks)


def test_round_consumables_use_numeric_toggles_and_no_external_shortcuts():
    screen = render_road(
        _view(
            "round_consumables",
            heal_quantity=4,
            purify_quantity=2,
            prepared_heal=True,
        )
    )
    assert "1 🧪 Poção de Cura · 4" in screen.text
    assert "2 🧪 Preparado de Purificação · 2" in screen.text
    assert "🟢 Uso Automático · Ativo" in screen.text
    assert "⚪ Uso Automático · Inativo" in screen.text
    callbacks = _callbacks(screen)
    assert any("road:round:toggle:h:" in value for value in callbacks)
    assert any("road:round:toggle:p:" in value for value in callbacks)
    assert not any("market" in value or "craft" in value for value in callbacks)


def test_empty_round_consumables_do_not_block_return():
    screen = render_road(_view("round_consumables"))
    assert "Nenhum Consumível elegível" in screen.text
    assert len(_callbacks(screen)) == 1
    assert _callbacks(screen)[0].startswith("road:round:prepare:view:")


def test_round_active_cancel_request_removes_cancel_button():
    active = render_road(
        _view(
            "round_active",
            next_resolution_at=datetime.now(UTC) + timedelta(minutes=2),
        )
    )
    assert "🏕️ Ronda de Caça · Andamento" in active.text
    assert "⚔️ Encontros · 3/10" in active.text
    assert any(value.startswith("road:round:cancel:") for value in _callbacks(active))

    pending = render_road(
        _view(
            "round_active",
            cancel_requested=True,
            next_resolution_at=datetime.now(UTC) + timedelta(minutes=2),
        )
    )
    assert "⏳ Cancelamento · Após o Encontro Atual" in pending.text
    assert pending.keyboard is None


def test_round_elite_interruption_counts_only_completed_encounters():
    screen = render_road(
        _view(
            "round_interrupted",
            creature="Alfa Cinéreo",
            enemy_level=3,
            result_text="A Estrada guarda ameaças entre as cinzas.",
        )
    )
    assert "🏕️ Ronda de Caça · Interrompida" in screen.text
    assert "⚔️ Encontros · 3/10" in screen.text
    assert "⚠️ Motivo · Elite Encontrado" in screen.text
    assert "🐺 Alfa Cinéreo · Nv. 3" in screen.text
    assert any(value.startswith("road:round:elite:") for value in _callbacks(screen))


def test_round_terminal_shells_follow_approved_semantics():
    completed = render_road(
        _view("round_completed", completed_encounters=10, reward_lines=("✨ XP · 1000",))
    )
    assert "🏆 Ronda de Caça · Concluída" in completed.text
    assert "🎁 Recompensas" in completed.text

    cancelled = render_road(_view("round_cancelled"))
    assert "🏕️ Ronda de Caça · Cancelada" in cancelled.text
    assert "✅ A Ronda foi encerrada." in cancelled.text

    defeated = render_road(_view("round_defeated"))
    assert "💀 Ronda de Caça · Derrota" in defeated.text
    assert "🔥 Braseiro da Estrada" in defeated.text
    assert "❤️ HP · Restaurado" in defeated.text

    vigor = render_road(_view("round_ended", end_reason="vigor"))
    assert "🏕️ Ronda de Caça · Encerrada" in vigor.text
    assert "⚡ Vigor · Insuficiente" in vigor.text
    assert "2 Vigor" not in vigor.text


def test_inventory_pending_ending_exposes_both_direct_actions():
    screen = render_road(
        _view(
            "round_ended",
            end_reason="inventory_pending",
            inventory_blocked=True,
            pending_blocked=True,
        )
    )
    assert "🎒 Inventário · Espaço Insuficiente" in screen.text
    assert "📦 Entregas Pendentes · Limite Atingido" in screen.text
    callbacks = _callbacks(screen)
    assert "inventory:root" in callbacks
    assert "pending:root" in callbacks

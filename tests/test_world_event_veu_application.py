"""Camada Application de A Ruptura do Véu (Etapa 4): orquestração sobre PostgreSQL real."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select, update

from asterion.application.world_event_veu import (
    VeuEventError,
    VeuEventService,
)
from asterion.domain import world_event_veu as ev
from asterion.infrastructure.db.models import (
    Account,
    Character,
    VeuEventAction,
    VeuEventEnemyDecision,
    VeuEventNucleus,
    VeuEventOccurrence,
    VeuEventParticipant,
)

SLOT = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)  # terça 12:00 em São Paulo
SERVER = "ocaso"


@pytest.fixture
def svc(database) -> VeuEventService:
    return VeuEventService(database[1], SERVER)


async def _characters(database, count: int, base: int = 770000) -> list[UUID]:
    async with database[1].begin() as session:
        for index in range(count):
            session.add(Account(telegram_id=base + index))
            session.add(
                Character(
                    telegram_id=base + index,
                    server_id=SERVER,
                    name="Veu" + "abcdefghij"[index],
                    race="remanescente",
                    character_class="sentinela",
                    stage="menu",
                    ruleset_version="tdo-1.0.15",
                    level=30,
                    hp=Decimal("50"),
                    max_hp=Decimal("500"),
                    vigor=100,
                    max_vigor=100,
                )
            )
    async with database[1]() as session:
        rows = (
            await session.scalars(
                select(Character)
                .where(Character.telegram_id >= base)
                .order_by(Character.telegram_id)
            )
        ).all()
        return [row.id for row in rows]


async def _running(svc, database, players: int = 2):
    """Ocorrência EM_ANDAMENTO com ``players`` participantes."""
    characters = await _characters(database, players)
    occurrence = await svc.get_or_create_occurrence(SLOT)
    await svc.open_occurrence(occurrence.id, now=SLOT)
    for character in characters:
        await svc.join(occurrence.id, character, now=SLOT)
    await svc.start_occurrence(occurrence.id, now=SLOT + timedelta(minutes=1))
    return occurrence.id, characters


async def _set_nuclei(database, occurrence_id: UUID, keys: str, state: ev.NucleusState):
    async with database[1].begin() as session:
        await session.execute(
            update(VeuEventNucleus)
            .where(
                VeuEventNucleus.occurrence_id == occurrence_id,
                VeuEventNucleus.nucleus_key.in_(list(keys)),
            )
            .values(state=state.value)
        )


# ----------------------------------------------------------------- ocorrência


@pytest.mark.asyncio
async def test_occurrence_is_get_or_create_once_per_slot(svc, database):
    first = await svc.get_or_create_occurrence(SLOT)
    second = await svc.get_or_create_occurrence(SLOT)
    assert first.id == second.id
    assert first.state == "AGENDADO" and first.phase == 1
    assert first.nuclei == {} and first.snapshots == {}
    async with database[1]() as session:
        row = await session.scalar(select(VeuEventOccurrence))
    assert row.event_id == ev.EVENT_ID and row.ruleset_version == ev.RULESET
    assert row.deadline_at - row.scheduled_at == ev.DEADLINE


@pytest.mark.asyncio
async def test_occurrence_creation_is_safe_under_concurrency(svc, database):
    views = await asyncio.gather(*(svc.get_or_create_occurrence(SLOT) for _ in range(5)))
    assert len({view.id for view in views}) == 1


@pytest.mark.asyncio
async def test_slot_outside_the_schedule_is_rejected(svc):
    with pytest.raises(VeuEventError) as error:
        await svc.get_or_create_occurrence(SLOT + timedelta(hours=1))
    assert error.value.code == "not_a_scheduled_slot"
    with pytest.raises(ValueError):
        await svc.get_or_create_occurrence(datetime(2026, 11, 24, 12, 0))


@pytest.mark.asyncio
async def test_open_waits_for_the_slot_and_is_idempotent(svc):
    occurrence = await svc.get_or_create_occurrence(SLOT)
    with pytest.raises(VeuEventError) as error:
        await svc.open_occurrence(occurrence.id, now=SLOT - timedelta(seconds=1))
    assert error.value.code == "before_scheduled_time"
    opened = await svc.open_occurrence(occurrence.id, now=SLOT)
    again = await svc.open_occurrence(occurrence.id, now=SLOT + timedelta(minutes=1))
    assert opened.state == again.state == "ABERTO"
    assert opened.state_version == again.state_version == 1


@pytest.mark.asyncio
async def test_start_requires_open_and_creates_phase_one(svc, database):
    occurrence = await svc.get_or_create_occurrence(SLOT)
    with pytest.raises(VeuEventError) as error:
        await svc.start_occurrence(occurrence.id, now=SLOT)
    assert error.value.code == "invalid_transition"
    occurrence_id, characters = await _running(svc, database, players=3)
    view = await svc.get_occurrence(occurrence_id)
    assert view.state == "EM_ANDAMENTO" and view.phase == 1
    assert view.nuclei == {"A": "ATIVA", "B": "ATIVA", "C": "ATIVA"}
    assert view.snapshots == {1: 3}
    again = await svc.start_occurrence(occurrence_id, now=SLOT + timedelta(minutes=2))
    assert again.state_version == view.state_version and again.snapshots == {1: 3}


@pytest.mark.asyncio
async def test_other_server_cannot_touch_the_occurrence(svc, database):
    occurrence = await svc.get_or_create_occurrence(SLOT)
    other = VeuEventService(database[1], "outro")
    with pytest.raises(VeuEventError) as error:
        await other.open_occurrence(occurrence.id, now=SLOT)
    assert error.value.code == "occurrence_not_found"


# ---------------------------------------------------------------- participantes


@pytest.mark.asyncio
async def test_join_is_idempotent_and_records_the_phase(svc, database):
    (character,) = await _characters(database, 1)
    occurrence = await svc.get_or_create_occurrence(SLOT)
    with pytest.raises(VeuEventError) as error:
        await svc.join(occurrence.id, character, now=SLOT)
    assert error.value.code == "event_not_open"
    await svc.open_occurrence(occurrence.id, now=SLOT)
    first = await svc.join(occurrence.id, character, now=SLOT)
    second = await svc.join(occurrence.id, character, now=SLOT + timedelta(minutes=1))
    assert first == second and first.phases == (1,) and first.current_nucleus is None
    assert len(await svc.list_participants(occurrence.id)) == 1


@pytest.mark.asyncio
async def test_join_respects_the_entry_window_and_the_character(svc, database):
    (character,) = await _characters(database, 1)
    occurrence = await svc.get_or_create_occurrence(SLOT)
    await svc.open_occurrence(occurrence.id, now=SLOT)
    with pytest.raises(VeuEventError) as error:
        await svc.join(occurrence.id, character, now=SLOT + ev.ENTRY_WINDOW + timedelta(seconds=1))
    assert error.value.code == "entry_window_closed"
    with pytest.raises(VeuEventError) as error:
        await svc.join(occurrence.id, UUID(int=1), now=SLOT)
    assert error.value.code == "character_not_found"


@pytest.mark.asyncio
async def test_voluntary_exit_blocks_rejoin_and_leaves_the_nucleus(svc, database):
    occurrence_id, (alfa, _beta) = await _running(svc, database)
    await svc.enter_nucleus(occurrence_id, alfa, "A", now=SLOT)
    left = await svc.leave_event(occurrence_id, alfa, now=SLOT)
    assert left.voluntary_exit and left.current_nucleus is None
    with pytest.raises(VeuEventError) as error:
        await svc.join(occurrence_id, alfa, now=SLOT)
    assert error.value.code == "participant_left"
    with pytest.raises(VeuEventError):
        await svc.enter_nucleus(occurrence_id, alfa, "B", now=SLOT)


@pytest.mark.asyncio
async def test_enter_nucleus_and_switch_follow_the_closed_rules(svc, database):
    occurrence_id, (alfa, beta) = await _running(svc, database)
    entered = await svc.enter_nucleus(occurrence_id, alfa, "A", now=SLOT)
    assert entered.current_nucleus == "A"
    assert (await svc.enter_nucleus(occurrence_id, alfa, "A", now=SLOT)).current_nucleus == "A"
    switched = await svc.enter_nucleus(occurrence_id, alfa, "B", now=SLOT)
    assert switched.current_nucleus == "B"
    async with database[1]() as session:
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
    assert row.acts_from_round == 2  # trocar: 1 rodada sem agir no destino
    with pytest.raises(VeuEventError) as error:
        await svc.enter_nucleus(occurrence_id, beta, "D", now=SLOT)
    assert error.value.code == "nucleus_not_available"
    await _set_nuclei(database, occurrence_id, "B", ev.NucleusState.RESOLVIDA)
    with pytest.raises(VeuEventError) as error:
        await svc.enter_nucleus(occurrence_id, beta, "B", now=SLOT)
    assert error.value.code == "nucleus_not_active"


# ---------------------------------------------------------------------- rodadas


@pytest.mark.asyncio
async def test_open_round_uses_the_ten_second_window_and_one_unresolved_round(svc, database):
    occurrence_id, _ = await _running(svc, database)
    opened_at = SLOT + timedelta(minutes=2)
    first = await svc.open_round(occurrence_id, "A", now=opened_at)
    again = await svc.open_round(occurrence_id, "A", now=opened_at + timedelta(seconds=3))
    assert first.id == again.id and first.round_number == 1 and first.state == "OPEN"
    assert first.decision_deadline - first.opened_at == timedelta(seconds=10)
    other = await svc.open_round(occurrence_id, "B", now=opened_at)
    assert other.id != first.id and other.round_number == 1
    await svc.resolve_round(first.id, now=first.decision_deadline)
    second = await svc.open_round(occurrence_id, "A", now=first.decision_deadline)
    assert second.round_number == 2
    await _set_nuclei(database, occurrence_id, "C", ev.NucleusState.RESOLVIDA)
    with pytest.raises(VeuEventError) as error:
        await svc.open_round(occurrence_id, "C", now=opened_at)
    assert error.value.code == "nucleus_not_active"


@pytest.mark.asyncio
async def test_action_is_deterministic_idempotent_and_validated(svc, database):
    occurrence_id, (alfa, beta) = await _running(svc, database)
    await svc.enter_nucleus(occurrence_id, alfa, "A", now=SLOT)
    round_ = await svc.open_round(occurrence_id, "A", now=SLOT)
    first = await svc.register_action(round_.id, alfa, "attack", now=SLOT)
    again = await svc.register_action(round_.id, alfa, "attack", now=SLOT + timedelta(seconds=2))
    key = ev.occurrence_key(SLOT)
    assert first.id == again.id == ev.action_id(key, "A", 1, alfa)
    assert first.created and not again.created
    with pytest.raises(VeuEventError) as error:
        await svc.register_action(round_.id, alfa, "defend", now=SLOT)
    assert error.value.code == "action_already_registered"
    with pytest.raises(VeuEventError) as error:
        await svc.register_action(round_.id, beta, "attack", now=SLOT)
    assert error.value.code == "not_in_nucleus"
    async with database[1]() as session:
        count = len((await session.scalars(select(VeuEventAction))).all())
    assert count == 1


@pytest.mark.asyncio
async def test_action_input_and_window_are_rejected(svc, database):
    occurrence_id, (alfa, _beta) = await _running(svc, database)
    await svc.enter_nucleus(occurrence_id, alfa, "A", now=SLOT)
    round_ = await svc.open_round(occurrence_id, "A", now=SLOT)
    for kwargs in (
        {"action_type": "stabilize"},
        {"action_type": "art"},
        {"action_type": "art", "art_slot": 4},
        {"action_type": "attack", "art_slot": 1},
    ):
        with pytest.raises(VeuEventError):
            await svc.register_action(round_.id, alfa, now=SLOT, **kwargs)
    art = await svc.register_action(round_.id, alfa, "art", art_slot=2, now=SLOT)
    assert art.art_slot == 2
    late = SLOT + timedelta(seconds=11)
    other = await svc.open_round(occurrence_id, "B", now=SLOT)
    with pytest.raises(VeuEventError) as error:
        await svc.register_action(other.id, alfa, "attack", now=late)
    assert error.value.code in {"decision_window_closed", "not_in_nucleus"}
    with pytest.raises(VeuEventError) as error:
        await svc.register_action(round_.id, alfa, "attack", now=late)
    assert error.value.code == "decision_window_closed"


@pytest.mark.asyncio
async def test_enemy_decision_is_seeded_idempotent_and_validated(svc, database):
    occurrence_id, (alfa, beta) = await _running(svc, database)
    await svc.enter_nucleus(occurrence_id, alfa, "A", now=SLOT)
    round_ = await svc.open_round(occurrence_id, "A", now=SLOT)
    first = await svc.register_enemy_decision(
        round_.id, "VEU-02", "pulsacao_irregular", target_ids=[alfa], now=SLOT
    )
    again = await svc.register_enemy_decision(
        round_.id, "VEU-02", "pulsacao_irregular", target_ids=[alfa], now=SLOT
    )
    assert first.seed == ev.enemy_seed(ev.occurrence_key(SLOT), "A", 1)
    assert first.created and not again.created and first.target_ids == (str(alfa),)
    with pytest.raises(VeuEventError) as error:
        await svc.register_enemy_decision(round_.id, "VEU-02", "pulso_de_carne", now=SLOT)
    assert error.value.code == "decision_already_committed"
    for enemy, action, code, targets in (
        ("VEU-18", "golpe_da_margem", "enemy_not_in_nucleus", ()),
        ("VEU-01", "inexistente", "enemy_action_unknown", ()),
        ("VEU-01", "mordida_vertical", "target_not_in_nucleus", (beta,)),
        ("VEU-02", "pulsacao_irregular", "too_many_targets", (alfa, alfa, alfa)),
    ):
        with pytest.raises(VeuEventError) as error:
            await svc.register_enemy_decision(
                round_.id, enemy, action, target_ids=targets, now=SLOT
            )
        assert error.value.code == code
    barrier = await svc.register_enemy_decision(
        round_.id, "VEU-03", "fechamento_toracico", now=SLOT
    )
    assert barrier.created and barrier.action_key == "fechamento_toracico"
    async with database[1]() as session:
        rows = (await session.scalars(select(VeuEventEnemyDecision))).all()
    assert sorted(row.enemy_key for row in rows) == ["VEU-02", "VEU-03"]


@pytest.mark.asyncio
async def test_resolve_waits_for_the_window_and_runs_exactly_once(svc, database):
    occurrence_id, (alfa, beta) = await _running(svc, database)
    for character in (alfa, beta):
        await svc.enter_nucleus(occurrence_id, character, "A", now=SLOT)
    round_ = await svc.open_round(occurrence_id, "A", now=SLOT)
    await svc.register_action(round_.id, alfa, "attack", now=SLOT)
    with pytest.raises(VeuEventError) as error:
        await svc.resolve_round(round_.id, now=SLOT + timedelta(seconds=9))
    assert error.value.code == "decision_window_open"
    due = round_.decision_deadline
    results = await asyncio.gather(*(svc.resolve_round(round_.id, now=due) for _ in range(4)))
    assert sum(1 for result in results if result.resolved_now) == 1
    winner = next(result for result in results if result.resolved_now)
    assert winner.afk_streaks == {alfa: 0, beta: 1} and winner.removed == ()
    view = await svc.get_round(round_.id)
    assert view.state == "RESOLVED" and view.resolved_at == due
    async with database[1]() as session:
        action = await session.scalar(select(VeuEventAction))
        beta_row = await session.get(VeuEventParticipant, (occurrence_id, beta))
    assert action.valid is True and action.validated_at == due
    assert beta_row.afk_streak == 1


@pytest.mark.asyncio
async def test_three_idle_rounds_remove_from_nucleus_but_not_from_the_event(svc, database):
    occurrence_id, (alfa, beta) = await _running(svc, database)
    for character in (alfa, beta):
        await svc.enter_nucleus(occurrence_id, character, "A", now=SLOT)
    now = SLOT
    expected = [(0, 1), (0, 2), (0, 3)]
    for index, (alfa_streak, beta_streak) in enumerate(expected):
        round_ = await svc.open_round(occurrence_id, "A", now=now)
        await svc.register_action(round_.id, alfa, "defend", now=now)
        result = await svc.resolve_round(round_.id, now=round_.decision_deadline)
        now = round_.decision_deadline
        assert result.afk_streaks[beta] == beta_streak, index
        assert result.afk_streaks.get(alfa) == alfa_streak
    assert result.removed == (beta,)
    participants = {p.character_id: p for p in await svc.list_participants(occurrence_id)}
    assert participants[beta].current_nucleus is None
    assert participants[beta].nucleus_removed and not participants[beta].voluntary_exit
    assert participants[beta].afk_label == "AFK 3/3"
    assert participants[alfa].current_nucleus == "A" and participants[alfa].afk_label is None
    back = await svc.enter_nucleus(occurrence_id, beta, "A", now=now)
    assert back.current_nucleus == "A" and not back.nucleus_removed and back.afk_streak == 0


@pytest.mark.asyncio
async def test_action_resets_the_afk_counter(svc, database):
    occurrence_id, (alfa, _beta) = await _running(svc, database)
    await svc.enter_nucleus(occurrence_id, alfa, "A", now=SLOT)
    now = SLOT
    streaks = []
    for acted in (False, False, True):
        round_ = await svc.open_round(occurrence_id, "A", now=now)
        if acted:
            await svc.register_action(round_.id, alfa, "attack", now=now)
        result = await svc.resolve_round(round_.id, now=round_.decision_deadline)
        now = round_.decision_deadline
        streaks.append(result.afk_streaks[alfa])
    assert streaks == [1, 2, 0]


# ---------------------------------------------------------------------- fases


@pytest.mark.asyncio
async def test_phase_advances_with_two_of_three_resolved_and_freezes_a_new_n(svc, database):
    occurrence_id, (alfa, beta) = await _running(svc, database)
    await svc.enter_nucleus(occurrence_id, alfa, "A", now=SLOT)
    await svc.enter_nucleus(occurrence_id, beta, "C", now=SLOT)
    await _set_nuclei(database, occurrence_id, "A", ev.NucleusState.RESOLVIDA)
    one = await svc.reevaluate_progress(occurrence_id, now=SLOT)
    assert one.phase == 1 and set(one.nuclei) == {"A", "B", "C"}
    # Núcleo resolvido solta o participante, sem punição.
    participants = {p.character_id: p for p in await svc.list_participants(occurrence_id)}
    assert participants[alfa].current_nucleus is None and not participants[alfa].nucleus_removed
    await svc.leave_event(occurrence_id, beta, now=SLOT)
    await _set_nuclei(database, occurrence_id, "B", ev.NucleusState.RESOLVIDA)
    later = SLOT + timedelta(minutes=10)
    two = await svc.reevaluate_progress(occurrence_id, now=later)
    assert two.phase == 2 and two.snapshots == {1: 2, 2: 1}  # N da Fase II sem quem saiu
    assert two.nuclei["D"] == two.nuclei["E"] == two.nuclei["F"] == "ATIVA"
    assert two.nuclei["C"] == "ATIVA"  # destino do remanescente não é decidido aqui
    again = await svc.reevaluate_progress(occurrence_id, now=later)
    assert again.phase == 2 and again.state_version == two.state_version


@pytest.mark.asyncio
async def test_concurrent_reevaluation_advances_the_phase_once(svc, database):
    occurrence_id, _ = await _running(svc, database)
    await _set_nuclei(database, occurrence_id, "AB", ev.NucleusState.RESOLVIDA)
    views = await asyncio.gather(
        *(svc.reevaluate_progress(occurrence_id, now=SLOT) for _ in range(4))
    )
    assert {view.phase for view in views} == {2}
    final = await svc.get_occurrence(occurrence_id)
    assert final.phase == 2 and final.snapshots.keys() == {1, 2}
    assert set(final.nuclei) == set("ABCDEF") and final.state_version == 3


@pytest.mark.asyncio
async def test_final_nucleus_completes_the_event_without_the_other_eight(svc, database):
    occurrence_id, _ = await _running(svc, database)
    await _set_nuclei(database, occurrence_id, "AB", ev.NucleusState.RESOLVIDA)
    await svc.reevaluate_progress(occurrence_id, now=SLOT)
    await _set_nuclei(database, occurrence_id, "DE", ev.NucleusState.RESOLVIDA)
    third = await svc.reevaluate_progress(occurrence_id, now=SLOT)
    assert third.phase == 3 and set(third.nuclei) == set("ABCDEFGHI")
    assert third.snapshots.keys() == {1, 2, 3}
    await _set_nuclei(database, occurrence_id, "GH", ev.NucleusState.RESOLVIDA)
    still = await svc.reevaluate_progress(occurrence_id, now=SLOT)
    assert still.state == "EM_ANDAMENTO" and still.phase == 3
    await _set_nuclei(database, occurrence_id, "I", ev.NucleusState.RESOLVIDA)
    done = await svc.reevaluate_progress(occurrence_id, now=SLOT)
    assert done.state == "CONCLUIDO"
    with pytest.raises(VeuEventError) as error:
        await svc.open_round(occurrence_id, "I", now=SLOT)
    assert error.value.code == "event_not_running"
    final = await svc.reevaluate_progress(occurrence_id, now=SLOT)
    assert final.state == "CONCLUIDO" and final.state_version == done.state_version


@pytest.mark.asyncio
async def test_boss_prepared_action_needs_telegraph_and_is_not_consecutive(svc, database):
    occurrence_id, (alfa, _beta) = await _running(svc, database)
    for keys in ("AB", "DE"):
        await _set_nuclei(database, occurrence_id, keys, ev.NucleusState.RESOLVIDA)
        await svc.reevaluate_progress(occurrence_id, now=SLOT)
    await svc.enter_nucleus(occurrence_id, alfa, "I", now=SLOT)
    first = await svc.open_round(occurrence_id, "I", now=SLOT)
    with pytest.raises(VeuEventError) as error:
        await svc.register_enemy_decision(first.id, "VEU-18", "preparar_a_ruptura", now=SLOT)
    assert error.value.code == "telegraph_required"
    await svc.register_enemy_decision(
        first.id, "VEU-18", "preparar_a_ruptura", telegraph_key="veu18.ruptura", now=SLOT
    )
    await svc.resolve_round(first.id, now=first.decision_deadline)
    second = await svc.open_round(occurrence_id, "I", now=first.decision_deadline)
    with pytest.raises(VeuEventError) as error:
        await svc.register_enemy_decision(
            second.id, "VEU-18", "preparar_a_ruptura", telegraph_key="t", now=SLOT
        )
    assert error.value.code == "action_not_consecutive"
    ok = await svc.register_enemy_decision(second.id, "VEU-18", "golpe_da_margem", now=SLOT)
    assert ok.seed == ev.enemy_seed(ev.occurrence_key(SLOT), "I", 2)

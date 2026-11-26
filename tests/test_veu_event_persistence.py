"""PostgreSQL persistence of A Ruptura do Véu (Etapa 3): schema, constraints, migration."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from asterion.domain import world_event_veu as ev
from asterion.infrastructure.db.models import (
    Account,
    Character,
    VeuEventAction,
    VeuEventEnemyDecision,
    VeuEventNucleus,
    VeuEventOccurrence,
    VeuEventParticipant,
    VeuEventPhaseSnapshot,
    VeuEventRound,
)

SLOT = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)  # terça 12:00 em São Paulo
OTHER_SLOT = datetime(2026, 11, 24, 23, 0, tzinfo=UTC)  # terça 20:00
KEY = ev.occurrence_key(SLOT)
A, B = 880001, 880002
VEU_TABLES = {
    "veu_event_occurrences",
    "veu_event_phase_snapshots",
    "veu_event_nuclei",
    "veu_event_participants",
    "veu_event_rounds",
    "veu_event_actions",
    "veu_event_enemy_decisions",
}


def _occurrence(slot=SLOT, **override) -> VeuEventOccurrence:
    values = {
        "server_id": "ocaso",
        "event_id": ev.EVENT_ID,
        "occurrence_key": ev.occurrence_key(slot),
        "state": ev.EventState.AGENDADO.value,
        "phase": 1,
        "scheduled_at": slot,
        "entry_closes_at": slot + ev.ENTRY_WINDOW,
        "deadline_at": slot + ev.DEADLINE,
        "state_version": 0,
        "ruleset_version": ev.RULESET,
    }
    values.update(override)
    return VeuEventOccurrence(**values)


def _nuclei(occurrence_id: UUID) -> list[VeuEventNucleus]:
    return [
        VeuEventNucleus(
            occurrence_id=occurrence_id,
            nucleus_key=n.key,
            phase=n.phase,
            state=ev.NucleusState.ATIVA.value,
            state_version=0,
        )
        for n in ev.NUCLEI
    ]


def _round(nucleus: VeuEventNucleus, number=1, opened_at=SLOT, **override) -> VeuEventRound:
    values = {
        "occurrence_id": nucleus.occurrence_id,
        "nucleus_id": nucleus.id,
        "round_number": number,
        "state": ev.RoundState.OPEN.value,
        "opened_at": opened_at,
        "decision_deadline": ev.decision_deadline(opened_at),
    }
    values.update(override)
    return VeuEventRound(**values)


def _participant(occurrence_id: UUID, character_id: UUID, **override) -> VeuEventParticipant:
    values = {
        "occurrence_id": occurrence_id,
        "character_id": character_id,
        "joined_at": SLOT,
        "voluntary_exit": False,
        "afk_streak": 0,
        "significant_actions": 0,
        "major_contributions": 0,
        "phases": [],
    }
    values.update(override)
    return VeuEventParticipant(**values)


def _action(round_: VeuEventRound, character_id: UUID, **override) -> VeuEventAction:
    values = {
        "id": ev.action_id(KEY, "A", round_.round_number, character_id),
        "occurrence_id": round_.occurrence_id,
        "round_id": round_.id,
        "character_id": character_id,
        "action_type": "attack",
        "registered_at": SLOT,
    }
    values.update(override)
    return VeuEventAction(**values)


async def _characters(database) -> tuple[UUID, UUID]:
    async with database[1].begin() as session:
        for actor, name in ((A, "Alfa"), (B, "Beta")):
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    telegram_id=actor,
                    server_id="ocaso",
                    name=name,
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
            await session.scalars(select(Character).order_by(Character.telegram_id))
        ).all()
        return rows[0].id, rows[1].id


async def _setup(database):
    """Occurrence with Núcleos A–I, two characters and both as participants."""
    alfa, beta = await _characters(database)
    async with database[1].begin() as session:
        occurrence = _occurrence()
        session.add(occurrence)
        await session.flush()
        nuclei = _nuclei(occurrence.id)
        session.add_all(nuclei)
        session.add_all([_participant(occurrence.id, alfa), _participant(occurrence.id, beta)])
        await session.flush()
        by_key = {n.nucleus_key: n for n in nuclei}
        return occurrence.id, by_key, alfa, beta


async def _rejected(database, *rows) -> None:
    with pytest.raises(IntegrityError):
        async with database[1].begin() as session:
            session.add_all(rows)


# ------------------------------------------------------------------ ocorrência


@pytest.mark.asyncio
async def test_occurrence_is_created_with_the_domain_state_and_window(database):
    async with database[1].begin() as session:
        session.add(_occurrence())
    async with database[1]() as session:
        row = await session.scalar(select(VeuEventOccurrence))
    assert row.state == "AGENDADO" and row.phase == 1 and row.state_version == 0
    assert row.occurrence_key == KEY
    assert row.entry_closes_at - row.scheduled_at == timedelta(minutes=15)
    assert row.deadline_at - row.scheduled_at == timedelta(minutes=60)
    assert row.opened_at is None and row.closed_at is None


@pytest.mark.asyncio
async def test_occurrence_is_unique_per_server_and_slot_key(database):
    async with database[1].begin() as session:
        session.add(_occurrence())
    await _rejected(database, _occurrence())
    # outro horário e outro servidor são ocorrências independentes
    async with database[1].begin() as session:
        session.add(_occurrence(OTHER_SLOT))
        session.add(_occurrence(server_id="outro"))
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(VeuEventOccurrence)) == 3


@pytest.mark.asyncio
async def test_occurrence_insert_is_idempotent_with_on_conflict(database):
    from sqlalchemy.dialects.postgresql import insert

    values = {
        "id": uuid4(), "server_id": "ocaso", "event_id": ev.EVENT_ID, "occurrence_key": KEY,
        "state": "AGENDADO", "phase": 1, "scheduled_at": SLOT,
        "entry_closes_at": SLOT + ev.ENTRY_WINDOW, "deadline_at": SLOT + ev.DEADLINE,
        "state_version": 0, "ruleset_version": ev.RULESET,
    }
    for _ in range(2):
        async with database[1].begin() as session:
            await session.execute(
                insert(VeuEventOccurrence).values(**{**values, "id": uuid4()})
                .on_conflict_do_nothing(constraint="uq_veu_occurrence")
            )
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(VeuEventOccurrence)) == 1


@pytest.mark.asyncio
async def test_occurrence_state_phase_and_dates_are_constrained(database):
    await _rejected(database, _occurrence(state="gathering"))
    await _rejected(database, _occurrence(phase=0))
    await _rejected(database, _occurrence(phase=4))
    await _rejected(database, _occurrence(deadline_at=SLOT))
    await _rejected(database, _occurrence(entry_closes_at=SLOT))
    await _rejected(database, _occurrence(state_version=-1))


@pytest.mark.asyncio
async def test_all_six_global_states_are_accepted(database):
    async with database[1].begin() as session:
        for index, state in enumerate(ev.EventState):
            slot = SLOT + timedelta(days=7 * index)
            session.add(_occurrence(slot, state=state.value))
    async with database[1]() as session:
        states = set(await session.scalars(select(VeuEventOccurrence.state)))
    assert states == {s.value for s in ev.EventState}


# ------------------------------------------------------------ N global por fase


@pytest.mark.asyncio
async def test_one_global_n_snapshot_per_phase(database):
    occurrence_id, *_ = await _setup(database)
    async with database[1].begin() as session:
        for phase, n in ((1, 12), (2, 9), (3, 200)):
            session.add(VeuEventPhaseSnapshot(
                occurrence_id=occurrence_id, phase=phase, n=n, frozen_at=SLOT))
    async with database[1]() as session:
        rows = (await session.scalars(
            select(VeuEventPhaseSnapshot).order_by(VeuEventPhaseSnapshot.phase))).all()
    assert [(r.phase, r.n) for r in rows] == [(1, 12), (2, 9), (3, 200)]
    await _rejected(database, VeuEventPhaseSnapshot(
        occurrence_id=occurrence_id, phase=1, n=13, frozen_at=SLOT))  # um N por fase


@pytest.mark.asyncio
async def test_snapshot_n_and_phase_are_bounded(database):
    occurrence_id, *_ = await _setup(database)
    for phase, n in ((0, 5), (4, 5), (1, -1), (1, 201)):
        await _rejected(database, VeuEventPhaseSnapshot(
            occurrence_id=occurrence_id, phase=phase, n=n, frozen_at=SLOT))


# ------------------------------------------------------------------- Núcleos


@pytest.mark.asyncio
async def test_occurrence_has_nuclei_a_to_i_with_the_domain_phases(database):
    occurrence_id, by_key, *_ = await _setup(database)
    async with database[1]() as session:
        rows = (await session.scalars(
            select(VeuEventNucleus).where(VeuEventNucleus.occurrence_id == occurrence_id)
            .order_by(VeuEventNucleus.nucleus_key))).all()
    assert [r.nucleus_key for r in rows] == list("ABCDEFGHI")
    assert {r.nucleus_key: r.phase for r in rows} == {n.key: n.phase for n in ev.NUCLEI}
    assert all(r.state == "ATIVA" and r.enemy_state == {} for r in rows)
    assert len(by_key) == 9


@pytest.mark.asyncio
async def test_nucleus_is_unique_per_occurrence_and_bound_to_its_phase(database):
    occurrence_id, *_ = await _setup(database)
    dup = VeuEventNucleus(occurrence_id=occurrence_id, nucleus_key="A", phase=1,
                          state="ATIVA", state_version=0)
    await _rejected(database, dup)
    async with database[1].begin() as session:
        other = _occurrence(OTHER_SLOT)
        session.add(other)
        await session.flush()
        session.add_all(_nuclei(other.id))  # outra ocorrência repete A–I sem conflito
    wrong_phase = VeuEventNucleus(occurrence_id=occurrence_id, nucleus_key="D", phase=1,
                                  state="ATIVA", state_version=0)
    unknown_key = VeuEventNucleus(occurrence_id=occurrence_id, nucleus_key="J", phase=3,
                                  state="ATIVA", state_version=0)
    for row in (wrong_phase, unknown_key):
        await _rejected(database, row)


@pytest.mark.asyncio
async def test_nucleus_states_follow_the_domain_enum(database):
    occurrence_id, *_ = await _setup(database)
    async with database[1].begin() as session:
        session.add(_occurrence(OTHER_SLOT))
    async with database[1].begin() as session:
        other = await session.scalar(
            select(VeuEventOccurrence).where(VeuEventOccurrence.occurrence_key
                                             == ev.occurrence_key(OTHER_SLOT)))
        for index, state in enumerate(ev.NucleusState):
            session.add(VeuEventNucleus(
                occurrence_id=other.id, nucleus_key="ABCDE"[index],
                phase=1 if index < 3 else 2, state=state.value, state_version=0))
    await _rejected(database, VeuEventNucleus(
        occurrence_id=occurrence_id, nucleus_key="J", phase=3, state="ATIVO", state_version=0))


@pytest.mark.asyncio
async def test_deleting_the_occurrence_cascades_to_everything(database):
    occurrence_id, by_key, alfa, _ = await _setup(database)
    async with database[1].begin() as session:
        round_ = _round(by_key["A"])
        session.add(round_)
        await session.flush()
        session.add(_action(round_, alfa))
        session.add(VeuEventEnemyDecision(
            round_id=round_.id, enemy_key="VEU-01", action_key="mordida_vertical",
            target_ids=[], seed=ev.enemy_seed(KEY, "A", 1), committed_at=SLOT))
        session.add(VeuEventPhaseSnapshot(
            occurrence_id=occurrence_id, phase=1, n=2, frozen_at=SLOT))
    async with database[1].begin() as session:
        await session.execute(text("DELETE FROM veu_event_occurrences"))
    async with database[1]() as session:
        for table in VEU_TABLES:
            assert await session.scalar(text(f"SELECT count(*) FROM {table}")) == 0


# --------------------------------------------------------------------- rodadas


@pytest.mark.asyncio
async def test_round_is_created_with_the_ten_second_window(database):
    _, by_key, *_ = await _setup(database)
    async with database[1].begin() as session:
        session.add(_round(by_key["A"], opened_at=SLOT))
    async with database[1]() as session:
        row = await session.scalar(select(VeuEventRound))
    assert row.state == "OPEN"
    assert row.decision_deadline - row.opened_at == ev.DECISION_WINDOW
    assert row.resolution_started_at is None and row.resolved_at is None


@pytest.mark.asyncio
async def test_round_window_must_be_exactly_ten_seconds(database):
    _, by_key, *_ = await _setup(database)
    for seconds in (8, 9, 11, 20, 180):
        await _rejected(database, _round(
            by_key["A"], decision_deadline=SLOT + timedelta(seconds=seconds)))


@pytest.mark.asyncio
async def test_round_number_is_unique_per_nucleus_and_independent_across_nuclei(database):
    _, by_key, *_ = await _setup(database)
    async with database[1].begin() as session:
        first = _round(by_key["A"], 1)
        session.add(first)
        session.add(_round(by_key["B"], 1))  # outro Núcleo, mesma numeração
    async with database[1].begin() as session:
        await session.execute(text(
            "UPDATE veu_event_rounds SET state='RESOLVING', resolution_started_at=:t, "
            "resolved_at=NULL WHERE nucleus_id=:n"), {"t": SLOT, "n": by_key["A"].id})
    await _rejected(database, _round(by_key["A"], 1))
    await _rejected(database, _round(by_key["A"], 0))


@pytest.mark.asyncio
async def test_round_has_one_resolution_path_and_one_open_round_per_nucleus(database):
    _, by_key, *_ = await _setup(database)
    async with database[1].begin() as session:
        session.add(_round(by_key["A"], 1))
    await _rejected(database, _round(by_key["A"], 2))  # outra rodada ainda aberta
    # estados incoerentes com os carimbos
    await _rejected(database, _round(by_key["B"], 1, state="RESOLVING"))
    await _rejected(database, _round(by_key["B"], 1, state="RESOLVED",
                                     resolution_started_at=SLOT))
    await _rejected(database, _round(by_key["B"], 1, state="OPEN", resolved_at=SLOT))
    await _rejected(database, _round(by_key["B"], 1, state="DONE"))
    async with database[1].begin() as session:  # resolvida libera a próxima
        session.add(_round(by_key["B"], 1, state="RESOLVED",
                           resolution_started_at=SLOT, resolved_at=SLOT))
        session.add(_round(by_key["B"], 2))


@pytest.mark.asyncio
async def test_round_must_belong_to_a_nucleus_of_the_same_occurrence(database):
    _, by_key, *_ = await _setup(database)
    stranger = _round(by_key["A"], 1, occurrence_id=uuid4())
    await _rejected(database, stranger)


# ----------------------------------------------------------------------- ações


@pytest.mark.asyncio
async def test_action_uses_the_deterministic_action_id_and_is_unique_per_character_round(
    database,
):
    _, by_key, alfa, beta = await _setup(database)
    async with database[1].begin() as session:
        round_ = _round(by_key["A"], 1)
        session.add(round_)
        await session.flush()
        session.add(_action(round_, alfa))
        session.add(_action(round_, beta, action_type="art", art_slot=2, target_ref="x"))
    async with database[1]() as session:
        row = await session.get(VeuEventAction, ev.action_id(KEY, "A", 1, alfa))
    assert row is not None and row.valid is None and row.significant is False
    async with database[1]() as session:
        round_ = await session.scalar(select(VeuEventRound))
    # mesmo action_id (reenvio) e outro id para o mesmo personagem na mesma rodada
    await _rejected(database, _action(round_, alfa))
    await _rejected(database, _action(round_, alfa, id=uuid4()))


@pytest.mark.asyncio
async def test_action_type_is_limited_to_the_universal_actions_and_three_art_slots(database):
    _, by_key, alfa, beta = await _setup(database)
    async with database[1].begin() as session:
        round_ = _round(by_key["A"], 1)
        session.add(round_)
        await session.flush()
        session.add(_action(round_, alfa, action_type="defend"))
    async with database[1]() as session:
        round_ = await session.scalar(select(VeuEventRound))
    for bad in (
        {"action_type": "stabilize"},  # contextual: continua bloqueada
        {"action_type": "art"},
        {"action_type": "art", "art_slot": 0},
        {"action_type": "art", "art_slot": 4},
        {"action_type": "attack", "art_slot": 1},
    ):
        await _rejected(database, _action(round_, beta, id=uuid4(), **bad))


@pytest.mark.asyncio
async def test_action_needs_a_participant_of_the_same_occurrence(database):
    _, by_key, alfa, _ = await _setup(database)
    async with database[1].begin() as session:
        round_ = _round(by_key["A"], 1)
        session.add(round_)
        await session.flush()
    async with database[1]() as session:
        round_ = await session.scalar(select(VeuEventRound))
    await _rejected(database, _action(round_, uuid4(), id=uuid4()))


# ------------------------------------------------------------------- decisões


@pytest.mark.asyncio
async def test_enemy_decision_stores_the_unsigned_64_bit_seed_exactly(database):
    _, by_key, *_ = await _setup(database)
    seed = ev.enemy_seed(KEY, "A", 1)
    async with database[1].begin() as session:
        round_ = _round(by_key["A"], 1)
        session.add(round_)
        await session.flush()
        session.add(VeuEventEnemyDecision(
            round_id=round_.id, enemy_key="VEU-01", action_key="mordida_vertical",
            target_ids=["a", "b"], telegraph_key=None, seed=seed, committed_at=SLOT))
        session.add(VeuEventEnemyDecision(
            round_id=round_.id, enemy_key="VEU-02", action_key="pulso_de_carne",
            seed=2**64 - 1, committed_at=SLOT))
    async with database[1]() as session:
        rows = {r.enemy_key: r for r in await session.scalars(select(VeuEventEnemyDecision))}
        round_ = await session.scalar(select(VeuEventRound))
    assert int(rows["VEU-01"].seed) == seed and rows["VEU-01"].target_ids == ["a", "b"]
    assert int(rows["VEU-02"].seed) == 2**64 - 1 and rows["VEU-02"].target_ids == []
    await _rejected(database, VeuEventEnemyDecision(
        round_id=round_.id, enemy_key="VEU-01", action_key="x", seed=1, committed_at=SLOT))
    await _rejected(database, VeuEventEnemyDecision(
        round_id=round_.id, enemy_key="VEU-03", action_key="x", seed=-1, committed_at=SLOT))


# ---------------------------------------------------------------- participação


@pytest.mark.asyncio
async def test_participant_defaults_and_afk_counter_follow_the_domain(database):
    occurrence_id, by_key, alfa, _ = await _setup(database)
    streak = 0
    for _ in range(3):
        state = ev.afk_after_round(streak, acted=False)
        streak = state.streak
        async with database[1].begin() as session:
            row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
            row.afk_streak = state.streak
    assert streak == ev.AFK_LIMIT
    async with database[1]() as session:
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
    assert row.afk_streak == 3 and row.voluntary_exit is False and row.phases == []
    for bad in (-1, 4):
        with pytest.raises(IntegrityError):
            async with database[1].begin() as session:
                row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
                row.afk_streak = bad


@pytest.mark.asyncio
async def test_afk_removal_from_the_nucleus_does_not_remove_from_the_event(database):
    occurrence_id, by_key, alfa, beta = await _setup(database)
    async with database[1].begin() as session:
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
        row.current_nucleus_id = by_key["A"].id
        row.nucleus_entered_at = SLOT
        row.afk_streak = 2
    async with database[1].begin() as session:  # 3ª rodada sem ação: sai do Núcleo
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
        state = ev.afk_after_round(row.afk_streak, acted=False)
        assert state.removed
        row.afk_streak = state.streak
        row.current_nucleus_id = None
        row.nucleus_removed_at = SLOT + timedelta(minutes=1)
    async with database[1]() as session:
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
        records = [
            ev.ParticipantRecord(r.character_id, r.voluntary_exit, r.reentry_available_at)
            for r in await session.scalars(select(VeuEventParticipant))
        ]
    assert row.current_nucleus_id is None and row.nucleus_removed_at is not None
    assert row.voluntary_exit is False and row.left_at is None
    # continua contando no N global; ele pode entrar de novo em outro Núcleo
    assert ev.valid_participant_count(records, SLOT + timedelta(minutes=2)) == 2
    async with database[1].begin() as session:
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
        row.current_nucleus_id = by_key["B"].id
        row.nucleus_removed_at = None
        row.afk_streak = 0


@pytest.mark.asyncio
async def test_nucleus_switch_moves_the_participant_and_keeps_the_event_state(database):
    occurrence_id, by_key, alfa, _ = await _setup(database)
    async with database[1].begin() as session:
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
        row.current_nucleus_id = by_key["A"].id
        row.nucleus_entered_at = SLOT
        row.significant_actions = 3
    async with database[1].begin() as session:
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
        row.current_nucleus_id = by_key["B"].id
        row.nucleus_entered_at = SLOT + timedelta(seconds=30)
    async with database[1]() as session:
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
    assert row.current_nucleus_id == by_key["B"].id
    assert row.significant_actions == 3 and row.voluntary_exit is False


@pytest.mark.asyncio
async def test_participant_cannot_be_in_and_removed_from_a_nucleus_at_once(database):
    occurrence_id, by_key, alfa, _ = await _setup(database)
    with pytest.raises(IntegrityError):
        async with database[1].begin() as session:
            row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
            row.current_nucleus_id = by_key["A"].id
            row.nucleus_removed_at = SLOT


@pytest.mark.asyncio
async def test_participant_nucleus_must_belong_to_the_same_occurrence(database):
    occurrence_id, _, alfa, _ = await _setup(database)
    async with database[1].begin() as session:
        other = _occurrence(OTHER_SLOT)
        session.add(other)
        await session.flush()
        foreign = _nuclei(other.id)
        session.add_all(foreign)
        await session.flush()
        foreign_id = foreign[0].id
    with pytest.raises(IntegrityError):
        async with database[1].begin() as session:
            row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
            row.current_nucleus_id = foreign_id


@pytest.mark.asyncio
async def test_voluntary_exit_is_event_level_and_consistent(database):
    occurrence_id, _, alfa, _ = await _setup(database)
    with pytest.raises(IntegrityError):
        async with database[1].begin() as session:
            row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
            row.voluntary_exit = True  # sem left_at
    async with database[1].begin() as session:
        row = await session.get(VeuEventParticipant, (occurrence_id, alfa))
        row.voluntary_exit = True
        row.left_at = SLOT + timedelta(minutes=5)
    async with database[1]() as session:
        records = [
            ev.ParticipantRecord(r.character_id, r.voluntary_exit, r.reentry_available_at)
            for r in await session.scalars(select(VeuEventParticipant))
        ]
    assert ev.valid_participant_count(records, SLOT + timedelta(minutes=6)) == 1


@pytest.mark.asyncio
async def test_participant_is_one_row_per_occurrence_and_character(database):
    occurrence_id, _, alfa, _ = await _setup(database)
    await _rejected(database, _participant(occurrence_id, alfa))
    # o mesmo personagem entra em outra ocorrência (horário) sem conflito
    async with database[1].begin() as session:
        other = _occurrence(OTHER_SLOT)
        session.add(other)
        await session.flush()
        session.add(_participant(other.id, alfa))


@pytest.mark.asyncio
async def test_deleting_a_character_removes_its_participation_and_actions(database):
    occurrence_id, by_key, alfa, beta = await _setup(database)
    async with database[1].begin() as session:
        round_ = _round(by_key["A"], 1)
        session.add(round_)
        await session.flush()
        session.add(_action(round_, alfa))
    async with database[1].begin() as session:
        await session.execute(text("DELETE FROM characters WHERE id = :id"), {"id": alfa})
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(VeuEventAction)) == 0
        assert await session.scalar(
            select(func.count()).select_from(VeuEventParticipant)) == 1


# ------------------------------------------------------------------- migration


def _config(connection=None) -> Config:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def test_alembic_has_a_single_head_and_it_chains_the_veu_migrations():
    script = ScriptDirectory.from_config(_config())
    # O Despertar dos Flagelos (0060) e o Título persistido (0061) entraram depois do Véu:
    # a cabeça única continua encadeando as migrations do Véu.
    assert script.get_heads() == ["20261126_0063"]
    assert script.get_revision("20261126_0063").down_revision == "20261126_0062"
    assert script.get_revision("20261126_0062").down_revision == "20261126_0061"
    assert script.get_revision("20261126_0061").down_revision == "20261125_0060"
    assert script.get_revision("20261125_0060").down_revision == "20261123_0059"
    assert script.get_revision("20261123_0059").down_revision == "20261123_0058"
    assert script.get_revision("20261123_0058").down_revision == "20261123_0057"
    assert script.get_revision("20261122_0056").down_revision == "20261120_0055"


@pytest_asyncio.fixture
async def raw_schema():
    url = os.environ.get("ASTERION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ASTERION_TEST_DATABASE_URL to run real PostgreSQL migration tests")
    schema = "test_veu_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        yield engine, async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


async def _veu_tables(connection) -> set[str]:
    rows = await connection.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = current_schema() AND table_name LIKE 'veu\\_%'"))
    return {row[0] for row in rows}


@pytest.mark.asyncio
async def test_migration_upgrades_downgrades_and_upgrades_again(raw_schema):
    engine, _ = raw_schema
    async with engine.begin() as connection:
        await connection.run_sync(lambda c: command.upgrade(_config(c), "20261120_0055"))
        assert await _veu_tables(connection) == set()
        await connection.run_sync(lambda c: command.upgrade(_config(c), "head"))
        assert await _veu_tables(connection) == VEU_TABLES
        regional = await connection.scalar(text(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = "
            "current_schema() AND table_name IN ('world_event_occurrences',"
            "'world_event_participations')"))
        assert regional == 2  # o modelo regional antigo segue intacto
        await connection.run_sync(lambda c: command.downgrade(_config(c), "20261120_0055"))
        assert await _veu_tables(connection) == set()
        await connection.run_sync(lambda c: command.upgrade(_config(c), "head"))
        assert await _veu_tables(connection) == VEU_TABLES


@pytest.mark.asyncio
async def test_models_and_migration_agree(raw_schema):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from asterion.infrastructure.db.base import Base

    engine, _ = raw_schema
    async with engine.begin() as connection:
        await connection.run_sync(lambda c: command.upgrade(_config(c), "head"))

        def diff(sync_connection):
            context = MigrationContext.configure(sync_connection, opts={"compare_type": True})
            return [
                d for d in compare_metadata(context, Base.metadata)
                if "veu_event" in repr(d)
            ]

        assert await connection.run_sync(diff) == []

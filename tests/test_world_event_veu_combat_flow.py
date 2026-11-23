"""Fluxo de combate, fases, acerto e encerramento de A Ruptura do Véu (PostgreSQL real)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application.world_event_veu import (
    RoundInputs,
    VeuEventError,
    VeuEventService,
    VeuEventUpkeep,
)
from asterion.domain import veu_combat as vc
from asterion.domain import world_event_veu as ev
from asterion.infrastructure.db.models import (
    Character,
    VeuEventNucleus,
    VeuEventOccurrence,
    VeuEventParticipant,
)
from tests.test_world_event_veu_application import SERVER, SLOT, _characters


class FakeSimulator:
    """Dano fixo por ação; o motor de verdade é testado à parte."""

    def __init__(self, damage: int = 10**9, player_hp: int = 10**6):
        self.damage = damage
        self.player_hp = player_hp

    async def prepare(self, session, participants, actions, enemies, combat_key):
        players = {
            p.character_id: vc.PlayerUnit(
                p.character_id,
                Decimal(p.hp if p.hp is not None else self.player_hp),
                Decimal(self.player_hp),
                Decimal(10),
            )
            for p in participants
        }
        alive = sorted(code for code, unit in enemies.items() if not unit.defeated)
        intents = [
            vc.PlayerIntent(
                a.character_id,
                a.action_type,
                alive[0] if alive else None,
                0 if a.action_type == "defend" else self.damage,
            )
            for a in actions
        ]
        return RoundInputs(intents, players)


@pytest.fixture
def svc(database) -> VeuEventService:
    return VeuEventService(database[1], SERVER, FakeSimulator())


async def _start(svc, database, players=1, base=780000):
    characters = await _characters(database, players, base=base)
    upkeep = VeuEventUpkeep(svc)
    await upkeep.tick(SLOT)
    occurrence = (await svc.get_or_create_occurrence(SLOT)).id
    for character in characters:
        await svc.join(occurrence, character, now=SLOT)
    await upkeep.tick(SLOT + timedelta(seconds=1))
    return occurrence, characters


async def _play_nucleus(svc, occurrence, character, key, now):
    """Joga rodadas no Núcleo até resolvê-lo; devolve o instante seguinte."""
    await svc.enter_nucleus(occurrence, character, key, now=now)
    for _ in range(8):
        round_ = await svc.open_round(occurrence, key, now=now)
        await svc.commit_enemy_decisions(round_.id, now=now)
        try:
            await svc.register_action(round_.id, character, "attack", now=now)
        except VeuEventError:
            pass  # ainda observando (entrada/troca)
        now = round_.decision_deadline
        await svc.resolve_round(round_.id, now=now)
        view = await svc.reevaluate_progress(occurrence, now=now)
        if view.nuclei.get(key) == "RESOLVIDA":
            return now
        participants = await svc.list_participants(occurrence)
        if participants[0].current_nucleus != key:
            await svc.enter_nucleus(occurrence, character, key, now=now)
    raise AssertionError(f"Núcleo {key} não resolveu")


@pytest.mark.asyncio
async def test_start_is_automatic_at_the_slot_and_creates_phase_one(svc, database):
    occurrence, _ = await _start(svc, database)
    view = await svc.get_occurrence(occurrence)
    assert view.state == "EM_ANDAMENTO" and view.phase == 1
    assert sorted(view.nuclei) == ["A", "B", "C"]
    # Ninguém entrou num Núcleo ainda: o N da Fase I não foi congelado (não é 0).
    assert view.snapshots == {}
    await svc.enter_nucleus(occurrence, _[0], "A", now=SLOT + timedelta(seconds=2))
    assert (await svc.get_occurrence(occurrence)).snapshots == {1: 1}
    async with database[1]() as session:
        nucleus = await session.scalar(
            select(VeuEventNucleus).where(VeuEventNucleus.nucleus_key == "A")
        )
    assert set(nucleus.enemy_state) == {"VEU-01", "VEU-02", "VEU-03"}
    assert Decimal(nucleus.enemy_state["VEU-01"]["hp"]) > 0


@pytest.mark.asyncio
async def test_nucleus_resolves_when_every_creature_falls_and_players_are_removed(svc, database):
    occurrence, (hero,) = await _start(svc, database)
    now = await _play_nucleus(svc, occurrence, hero, "A", SLOT + timedelta(seconds=2))
    view = await svc.get_occurrence(occurrence)
    assert view.nuclei["A"] == "RESOLVIDA" and view.phase == 1
    (participant,) = await svc.list_participants(occurrence)
    assert participant.current_nucleus is None and not participant.nucleus_removed
    assert participant.afk_streak == 0
    with pytest.raises(VeuEventError) as error:
        await svc.enter_nucleus(occurrence, hero, "A", now=now)
    assert error.value.code == "nucleus_not_active"


@pytest.mark.asyncio
async def test_two_of_three_advance_the_phase_with_a_new_snapshot(svc, database):
    occurrence, (hero,) = await _start(svc, database)
    now = await _play_nucleus(svc, occurrence, hero, "A", SLOT + timedelta(seconds=2))
    await _play_nucleus(svc, occurrence, hero, "B", now)
    view = await svc.get_occurrence(occurrence)
    assert view.phase == 2
    assert sorted(view.nuclei) == ["A", "B", "C", "D", "E", "F"]
    assert view.snapshots == {1: 1, 2: 1}
    assert view.nuclei["C"] == "ATIVA"  # sem destino definido pela fonte: fica como está


@pytest.mark.asyncio
async def test_full_victory_settles_rewards_once_and_closes(svc, database):
    occurrence, (hero,) = await _start(svc, database)
    now = SLOT + timedelta(seconds=2)
    for key in ("A", "B", "D", "E", "I"):
        now = await _play_nucleus(svc, occurrence, hero, key, now)
    assert (await svc.get_occurrence(occurrence)).state == "CONCLUIDO"
    async with database[1]() as session:
        before = await session.scalar(select(Character).where(Character.id == hero))
        crowns, xp, level = before.crowns, before.xp, before.level
    first = await svc.settle_occurrence(occurrence, now=now)
    again = await svc.settle_occurrence(occurrence, now=now)
    assert first.state == "ENCERRADO" and first.rewarded == 1 and again.participants == 0
    async with database[1]() as session:
        after = await session.scalar(select(Character).where(Character.id == hero))
        participant = await session.get(VeuEventParticipant, (occurrence, hero))
        row = await session.get(VeuEventOccurrence, occurrence)
    assert participant.eligible and participant.reward["vigor"] == 10
    assert after.crowns - crowns == participant.reward["crowns"] > 0
    assert after.xp != xp or after.level > level
    assert row.state == "ENCERRADO" and row.closed_at is not None


@pytest.mark.asyncio
async def test_failure_pays_no_completion_reward(svc, database):
    occurrence, (hero,) = await _start(svc, database)
    await _play_nucleus(svc, occurrence, hero, "A", SLOT + timedelta(seconds=2))
    report = await VeuEventUpkeep(svc).tick(SLOT + ev.DEADLINE)
    assert len(report.failed) == 1
    async with database[1]() as session:
        row = await session.get(VeuEventOccurrence, occurrence)
        participant = await session.get(VeuEventParticipant, (occurrence, hero))
    assert row.state == "ENCERRADO"  # o mesmo tick acerta e encerra
    assert participant.eligible is False and participant.reward == {}


@pytest.mark.asyncio
async def test_switch_makes_the_player_wait_one_round(svc, database):
    occurrence, (hero,) = await _start(svc, database)
    now = SLOT + timedelta(seconds=2)
    await svc.enter_nucleus(occurrence, hero, "A", now=now)
    await svc.enter_nucleus(occurrence, hero, "B", now=now)
    first = await svc.open_round(occurrence, "B", now=now)
    with pytest.raises(VeuEventError) as error:
        await svc.register_action(first.id, hero, "attack", now=now)
    assert error.value.code == "waiting_next_round"
    await svc.resolve_round(first.id, now=first.decision_deadline)
    # Quem espera não ganha AFK nem punição (§14.2).
    (participant,) = await svc.list_participants(occurrence)
    assert participant.afk_streak == 0
    second = await svc.open_round(occurrence, "B", now=first.decision_deadline)
    action = await svc.register_action(second.id, hero, "attack", now=first.decision_deadline)
    assert action.created


@pytest.mark.asyncio
async def test_defeat_removes_from_nucleus_and_allows_reentry_after_two_minutes(database):
    svc = VeuEventService(database[1], SERVER, FakeSimulator(damage=1, player_hp=1))
    occurrence, (hero,) = await _start(svc, database, base=781000)
    now = SLOT + timedelta(seconds=2)
    await svc.enter_nucleus(occurrence, hero, "A", now=now)
    round_ = await svc.open_round(occurrence, "A", now=now)
    await svc.commit_enemy_decisions(round_.id, now=now)
    await svc.register_action(round_.id, hero, "attack", now=now)
    done = round_.decision_deadline
    await svc.resolve_round(round_.id, now=done)
    (participant,) = await svc.list_participants(occurrence)
    assert participant.current_nucleus is None and not participant.voluntary_exit
    with pytest.raises(VeuEventError) as error:
        await svc.enter_nucleus(occurrence, hero, "A", now=done + timedelta(seconds=119))
    assert error.value.code == "reentry_pending"
    again = await svc.enter_nucleus(occurrence, hero, "A", now=done + ev.REENTRY_DELAY)
    assert again.current_nucleus == "A"
    # Mesma participação: o personagem não vira outra linha.
    assert len(await svc.list_participants(occurrence)) == 1


@pytest.mark.asyncio
async def test_engine_simulator_uses_the_real_combat_engine_for_attack_and_defend(database):
    from asterion.application.world_event_veu_combat import EngineRoundSimulator

    svc = VeuEventService(database[1], SERVER, EngineRoundSimulator())
    occurrence, (attacker, defender) = await _start(svc, database, players=2, base=782000)
    now = SLOT + timedelta(seconds=2)
    for character in (attacker, defender):
        await svc.enter_nucleus(occurrence, character, "C", now=now)
    round_ = await svc.open_round(occurrence, "C", now=now)
    await svc.commit_enemy_decisions(round_.id, now=now)
    await svc.register_action(round_.id, attacker, "attack", target_ref="VEU-07", now=now)
    await svc.register_action(round_.id, defender, "defend", now=now)
    before = Decimal(
        (await svc.nucleus_enemy_state(occurrence, "C"))["VEU-07"]["hp"]
    )
    await svc.resolve_round(round_.id, now=round_.decision_deadline)
    state = await svc.nucleus_enemy_state(occurrence, "C")
    assert Decimal(state["VEU-07"]["hp"]) < before  # o motor causou dano real
    assert Decimal(state["VEU-08"]["hp"]) == Decimal(state["VEU-08"]["max_hp"])
    async with database[1]() as session:
        rows = (
            await session.scalars(
                select(VeuEventParticipant).where(VeuEventParticipant.occurrence_id == occurrence)
            )
        ).all()
    by_id = {row.character_id: row for row in rows}
    assert by_id[attacker].significant_actions == 1  # dano efetivo
    assert by_id[defender].significant_actions == 0  # Defender sem impacto não conta


@pytest.mark.asyncio
async def test_phase_one_snapshot_counts_earlier_joiners_and_ignores_later_ones(svc, database):
    from asterion.domain.veu_bestiary import creature, creature_stats

    occurrence, heroes = await _start(svc, database, players=3, base=783000)
    assert (await svc.get_occurrence(occurrence)).snapshots == {}
    now = SLOT + timedelta(seconds=2)
    # Dois entram antes do snapshot; o terceiro só entra depois dele.
    await svc.leave_event(occurrence, heroes[2], now=now)
    await svc.enter_nucleus(occurrence, heroes[0], "A", now=now)
    view = await svc.get_occurrence(occurrence)
    assert view.snapshots == {1: 2}
    stats = await svc.enemy_stats(occurrence, "A")
    assert stats["VEU-01"].hp == creature_stats(creature("VEU-01"), 2).hp
    assert stats["VEU-01"].hp > creature_stats(creature("VEU-01"), 1).hp
    # Quem entra ou sai depois não altera nada já congelado (§8.4).
    late = (await _characters(database, 1, base=783500))[0]
    await svc.join(occurrence, late, now=now + timedelta(seconds=5))
    await svc.enter_nucleus(occurrence, late, "B", now=now + timedelta(seconds=5))
    await svc.enter_nucleus(occurrence, heroes[1], "A", now=now + timedelta(seconds=5))
    assert (await svc.get_occurrence(occurrence)).snapshots == {1: 2}
    state = await svc.nucleus_enemy_state(occurrence, "B")
    expected = creature_stats(creature("VEU-04"), 2).hp.to_integral_value()
    assert Decimal(state["VEU-04"]["max_hp"]) == expected


@pytest.mark.asyncio
async def test_valid_participation_records_the_nucleus_creatures_once(svc, database):
    from asterion.infrastructure.db.models import BestiaryEntry, BestiaryEvidence

    occurrence, (hero,) = await _start(svc, database, base=784000)
    now = SLOT + timedelta(seconds=2)
    await svc.enter_nucleus(occurrence, hero, "A", now=now)
    round_ = await svc.open_round(occurrence, "A", now=now)
    # Sem ação válida a criatura não "participou" do encontro.
    await svc.resolve_round(round_.id, now=round_.decision_deadline)
    async with database[1]() as session:
        assert (await session.scalars(select(BestiaryEntry))).all() == []
    for _ in range(2):
        round_ = await svc.open_round(occurrence, "A", now=now)
        await svc.register_action(round_.id, hero, "defend", now=now)
        await svc.resolve_round(round_.id, now=round_.decision_deadline)
        now = round_.decision_deadline
    async with database[1]() as session:
        entries = (await session.scalars(select(BestiaryEntry))).all()
        evidence = (await session.scalars(select(BestiaryEvidence))).all()
    assert sorted(e.creature_id for e in entries) == [
        "bestiary.veu.01_mandibula_vigilia",
        "bestiary.veu.02_oito_pulsos",
        "bestiary.veu.03_costela_andante",
    ]
    # Registrado uma vez só, mesmo após duas rodadas válidas.
    first = [e for e in evidence if e.evidence_id == "first_observation"]
    assert len(first) == 3

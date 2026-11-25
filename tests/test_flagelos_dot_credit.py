"""O Despertar dos Flagelos — o dano de DoT continua creditado a quem o aplicou, mesmo depois
que o aplicador saiu ou foi derrotado (``in_combat`` falso no instante do tick)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application.flagelo_combat import BossDot, BossEffects
from asterion.application.flagelos import FlageloService
from asterion.domain import flagelos as fl
from asterion.domain.combat import DOT_TICK_COEFFICIENTS, DotState
from asterion.domain.combat_math import dot_damage
from asterion.infrastructure.db.models import FlageloEvent, FlageloParticipant, FlageloRound
from tests.test_flagelos_service import (
    SERVER,
    T0,
    FakeSimulator,
    _active,
    _characters,
    _spawn,
)

D = Decimal

def _expected_tick(boss_defense: int, source_level: int, snapshot: Decimal) -> int:
    return dot_damage([snapshot], DOT_TICK_COEFFICIENTS["burn"], D(boss_defense), source_level)


async def _setup(database, *, applier_state: str):
    """A aplica um DoT no Flagelo e depois sai (ou é derrotado); B segue em combate."""
    service = FlageloService(database[1], SERVER, FakeSimulator(damage=1))
    (a, a_id), (b, b_id) = await _characters(database, 2, base=885_000)
    event = await _spawn(database, service)
    await service.enter(a, now=T0)
    await service.enter(b, now=T0)
    boss = fl.REGIONS[0].flagelo
    snapshot = D(200)
    dot = BossDot(
        DotState("burn", 1, 3, snapshot, "player", [snapshot]), str(a_id), source_level=10
    )
    async with database[1].begin() as session:
        row = await session.get(FlageloEvent, event.id)
        effects = BossEffects([], [dot]).to_data()
        row.enemy_state = {**(row.enemy_state or {}), "player_effects": effects}
    if applier_state == "left":
        await service.leave(a, now=T0)
    else:  # derrotado: fora do combate, vida zerada
        async with database[1].begin() as session:
            participant = await session.get(FlageloParticipant, (event.id, a_id))
            participant.in_combat = False
            participant.hp = D(0)
            participant.defeated_at = T0
    return service, event, (a, a_id), (b, b_id), _expected_tick(boss.defense, 10, snapshot)


async def _participant(database, event_id, character_id) -> FlageloParticipant:
    async with database[1]() as session:
        return await session.get(FlageloParticipant, (event_id, character_id))


@pytest.mark.parametrize("applier_state", ["left", "defeated"])
async def test_dot_tick_is_credited_to_the_applier_after_leaving(database, applier_state):
    service, event, (a, a_id), (b, b_id), tick = await _setup(database, applier_state=applier_state)
    assert tick > 0
    before = await _active(database)
    round_ = await service.open_round(now=T0)
    await service.register_action(b, round_.round_number, "attack", now=T0)
    assert await service.resolve_round(round_.id, now=T0 + fl.DECISION_WINDOW)
    after = await _active(database)
    # Dano do ataque do B (1) + um tick do DoT do A: o Flagelo perdeu os dois.
    assert before.hp_current - after.hp_current == 1 + tick
    applier = await _participant(database, event.id, a_id)
    assert applier.effective_damage == tick
    assert applier.participation_points == 1  # dano efetivo > 0
    assert "offensive" in (applier.first_metric_timestamps or {})
    stayed = await _participant(database, event.id, b_id)
    assert stayed.effective_damage == 1  # o dano do tick não vaza para quem ficou


async def test_dot_credit_does_not_duplicate_and_reaches_the_offensive_ranking(database):
    service, event, (a, a_id), (b, b_id), tick = await _setup(database, applier_state="left")
    round_ = await service.open_round(now=T0)
    await service.register_action(b, round_.round_number, "attack", now=T0)
    deadline = T0 + fl.DECISION_WINDOW
    assert await service.resolve_round(round_.id, now=deadline)
    assert not await service.resolve_round(round_.id, now=deadline)  # rodada já resolvida
    await service.tick(now=deadline)  # o job não repete o crédito
    assert (await _participant(database, event.id, a_id)).effective_damage == tick
    # Mata o Flagelo na rodada seguinte: o ranking ofensivo traz o aplicador com o valor do DoT.
    async with database[1].begin() as session:
        row = await session.get(FlageloEvent, event.id)
        row.hp_current = 5
    service.simulator.damage = 50
    async with database[1]() as session:  # o próprio ``tick`` já abriu a rodada seguinte
        nxt = await session.scalar(
            select(FlageloRound).where(
                FlageloRound.flagelo_id == event.id, FlageloRound.state == "OPEN"
            )
        )
    await service.register_action(b, nxt.round_number, "attack", now=deadline)
    await service.resolve_round(nxt.id, now=deadline + fl.DECISION_WINDOW)
    async with database[1]() as session:
        dead = await session.get(FlageloEvent, event.id)
    ranking = {item["character_id"]: item for item in dead.rankings["offensive"]}
    credited = (await _participant(database, event.id, a_id)).effective_damage
    assert ranking[str(a_id)]["value"] == credited
    assert ranking[str(a_id)]["value"] >= tick
    # A posição segue a métrica: quem causou mais dano efetivo (incluindo o DoT) fica na frente.
    first = max(ranking.values(), key=lambda item: item["value"])
    assert first["position"] == 1 and first["character_id"] == str(a_id)

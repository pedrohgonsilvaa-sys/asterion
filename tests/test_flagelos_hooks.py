"""Ganchos reais de contribuição do Despertar dos Flagelos (Caçada, Desbravar, Contrato)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from asterion.application import contracts as contracts_module
from asterion.domain.combat import allowed_actions
from asterion.infrastructure.db.models import Character, FlageloContribution
from tests.test_contracts import NOW, A, _complete_coleta, _seed, _service
from tests.test_road_integration import ROAD, _seed_road


@pytest.fixture(autouse=True)
def _contracts_on():
    contracts_module.set_enabled(True)
    yield
    contracts_module.set_enabled(False)


async def _contributions(database, telegram_id: int, kind: str):
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id)
        )
        rows = await session.scalars(
            select(FlageloContribution).where(
                FlageloContribution.character_id == character.id, FlageloContribution.kind == kind
            )
        )
        return [(row.kind, row.region_id, row.points) for row in rows.all()]


async def test_manual_hunt_victory_contributes_one_in_the_current_region(database):
    actor, service = await _seed_road(database, 771301)
    await service.travel(actor, ROAD)
    view = await service.start_hunt(actor)
    for _ in range(100):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    assert view.kind == "hunt_victory"
    await service.resume(actor)  # reconexão não conta de novo
    assert await _contributions(database, actor, "hunt") == [("hunt", "tdo", 1)]


async def test_desbravar_contributes_once_per_attempt(database):
    actor, service = await _seed_road(database, 771302)
    await service.travel(actor, ROAD)
    view = await service.explore(actor)
    for _ in range(100):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    assert await _contributions(database, actor, "desbravar") == [("desbravar", "tdo", 1)]
    # O cenário já traz a Missão P1 concluída: o ouvinte de Missão gravou +4 nas Terras do Ocaso.
    assert await _contributions(database, actor, "mission") == [("mission", "tdo", 4)]


async def test_contract_claim_contributes_two_in_the_contract_region(database):
    await _seed(database, A)
    service = _service(database)
    view = await _complete_coleta(database, service)
    done = await service.get(A, view.instance_id, now=NOW)
    await service.claim(A, view.instance_id, done.version, now=NOW)
    assert await _contributions(database, A, "contract") == [("contract", "tdo", 2)]

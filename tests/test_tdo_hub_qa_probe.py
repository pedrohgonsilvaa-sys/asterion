"""Sondas de QA do bloco A: Local descoberto so por Explorar deve ter Cacada (crit. 12)."""

import pytest

from asterion.application.road import BOSQUE, CHARNECA, RUINS
from tests.test_tdo_hub_integration import ALL_IDS, _road, _seed


@pytest.mark.asyncio
@pytest.mark.parametrize("label", [CHARNECA, BOSQUE, RUINS])
async def test_local_discovered_only_by_explore_has_hunt(database, label):
    actor = 930100 + len(label)
    await _seed(database, actor, discovered=ALL_IDS)
    road = _road(database)
    view = await road.travel_route(actor, label)
    assert view is not None and view.location == label
    started = await road.start_hunt(actor)
    assert started is not None, f"{label}: start_hunt None apos Explorar"

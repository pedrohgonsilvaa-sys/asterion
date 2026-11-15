"""QA da fatia 2 de Explorar (TdO v1.0.18): concorrência, Grupo real, Charneca 193."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.tdo_explore import TdoExploreService
from asterion.domain.tdo_explore import CHARNECA_LOCATION_ID, EXPLORE_TARGETS
from asterion.infrastructure.db.models import (
    LocationDiscovery,
    RewardEvent,
    SocialGroup,
    SocialGroupMember,
)
from tests.test_tdo_explore_integration import Clock, _character, _discovered, _seed


@pytest.mark.asyncio
async def test_double_click_same_instant_only_one_discovers(database):
    actor = 920001
    cid = await _seed(database, actor)
    clock = Clock()
    svc = TdoExploreService(database[1], "ocaso", clock=clock)
    results = await asyncio.gather(*(svc.explore(actor) for _ in range(8)))
    statuses = sorted(r.status for r in results)
    assert statuses == ["cooldown"] * 7 + ["discovered"], statuses
    assert len(await _discovered(database, cid)) == 1
    assert (await _character(database, cid)).xp == 120
    async with database[1]() as s:
        n = await s.scalar(
            select(func.count()).select_from(RewardEvent).where(RewardEvent.character_id == cid)
        )
    assert n == 1


@pytest.mark.asyncio
async def test_double_click_with_independent_services_and_clock_past_cooldown(database):
    actor = 920002
    cid = await _seed(database, actor)
    clock = Clock()
    svcs = [TdoExploreService(database[1], "ocaso", clock=clock) for _ in range(4)]
    results = await asyncio.gather(*(s.explore(actor) for s in svcs))
    assert sum(r.status == "discovered" for r in results) == 1
    assert len(await _discovered(database, cid)) == 1


@pytest.mark.asyncio
async def test_real_group_is_individual_and_concurrent_members_do_not_deadlock(database):
    a, b = 920003, 920004
    ca = await _seed(database, a)
    cb = await _seed(database, b)
    gid = uuid4()
    async with database[1].begin() as s:
        s.add(SocialGroup(id=gid, server_id="ocaso", leader_character_id=ca))
        await s.flush()
        s.add(SocialGroupMember(character_id=ca, group_id=gid))
        s.add(SocialGroupMember(character_id=cb, group_id=gid))
    clock = Clock()
    svc = TdoExploreService(database[1], "ocaso", clock=clock)
    ra, rb = await asyncio.wait_for(asyncio.gather(svc.explore(a), svc.explore(b)), 20)
    assert ra.status == rb.status == "discovered"
    assert len(await _discovered(database, ca)) == 1
    assert len(await _discovered(database, cb)) == 1
    assert (await _character(database, ca)).xp == 120
    assert (await _character(database, cb)).xp == 120
    # grupo não compartilha descobertas
    clock.advance(3)
    await svc.explore(a)
    assert len(await _discovered(database, ca)) == 2
    assert len(await _discovered(database, cb)) == 1


@pytest.mark.asyncio
async def test_charneca_half_up_193_at_cap(database):
    others = tuple(t.location_id for t in EXPLORE_TARGETS if t.location_id != CHARNECA_LOCATION_ID)
    cid = await _seed(database, 920005, level=10, xp=0, discovered=others)
    r = await TdoExploreService(database[1], "ocaso", clock=Clock()).explore(920005)
    assert r.location_id == CHARNECA_LOCATION_ID and r.xp == 193
    async with database[1]() as s:
        assert await s.scalar(
            select(func.count()).select_from(LocationDiscovery).where(
                LocationDiscovery.character_id == cid
            )
        ) == 4


@pytest.mark.asyncio
async def test_uniform_draw_distribution_over_seeds():
    from collections import Counter

    from asterion.domain.tdo_explore import pick_explore_target

    c = Counter(pick_explore_target(f"x{i}", ()).location_id for i in range(4000))
    assert len(c) == 4 and min(c.values()) > 850

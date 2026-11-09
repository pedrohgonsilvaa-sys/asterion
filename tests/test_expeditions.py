"""PostgreSQL integration tests for the Expedição (GDD v1.6.0 §22.2, §49.15)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.combat_configuration_guard import find_combat_configuration_blocker
from asterion.application.expeditions import (
    ExpeditionError,
    ExpeditionHubView,
    ExpeditionResultView,
    ExpeditionService,
    ExpeditionStageNotice,
)
from asterion.application.guild_upkeep import _has_cooperative_commitment
from asterion.bot.expedition_ui import render_expedition
from asterion.domain.expeditions import (
    ExpeditionOption,
    ExpeditionResult,
    ExpeditionRoute,
    ExpeditionStage,
    OptionQuality,
    reward_bundle,
)
from asterion.infrastructure.db.models import (
    Account,
    AccountLink,
    AccountRiskFlag,
    Character,
    Expedition,
    ExpeditionChoice,
    GameActivity,
    Guild,
    GuildMember,
    GuildTreasuryEntry,
)

D = Decimal
# Monday 2026-11-16, 18:00 in Sao Paulo.
START = datetime(2026, 11, 16, 21, 0, tzinfo=UTC)
BEFORE = START - timedelta(days=1)
STAGE_2 = START + timedelta(hours=24)
STAGE_3 = START + timedelta(hours=48)
END = START + timedelta(hours=72)
ACTORS = (890001, 890002, 890003, 890004, 890005, 890006, 890007)
LEADER, OFFICER, MEMBER_A, MEMBER_B, MEMBER_C, MEMBER_D, MEMBER_E = ACTORS
NAMES = ("Alfa", "Beta", "Gama", "Delta", "Epsilon", "Zeta", "Eta")
FAVORABLE, NEUTRAL, POOR = 0, 1, 2

STAGE = ExpeditionStage(
    "Um rastro no barro.",
    (
        ExpeditionOption("seguir", "Seguir o rastro", OptionQuality.FAVORABLE),
        ExpeditionOption("esperar", "Esperar", OptionQuality.NEUTRAL),
        ExpeditionOption("correr", "Correr", OptionQuality.POOR),
    ),
)
ROUTE = ExpeditionRoute("rota_teste", "Rota de Teste", (STAGE, STAGE, STAGE), "Vocês voltam.")


async def _seed(database, level: int = 30) -> None:
    async with database[1].begin() as session:
        guild = Guild(server_id="ocaso", name="Aurora", tag="AUR")
        session.add(guild)
        await session.flush()
        for index, (actor, name) in enumerate(zip(ACTORS, NAMES, strict=True)):
            session.add(Account(telegram_id=actor))
            character = Character(
                telegram_id=actor,
                server_id="ocaso",
                name=name,
                race="remanescente",
                character_class="sentinela",
                stage="menu",
                ruleset_version="tdo-1.0.15",
                level=level,
                hp=D("50"),
                max_hp=D("500"),
                vigor=100,
                max_vigor=100,
            )
            session.add(character)
            await session.flush()
            role = "leader" if index == 0 else "officer" if index == 1 else "member"
            when = START - timedelta(days=30)
            session.add(
                GuildMember(
                    character_id=character.id,
                    guild_id=guild.id,
                    role=role,
                    joined_at=when,
                    role_since=when,
                )
            )


def _service(database, catalog=(ROUTE,)) -> ExpeditionService:
    return ExpeditionService(database[1], "ocaso", catalog)


async def _code(awaitable) -> str:
    with pytest.raises(ExpeditionError) as error:
        await awaitable
    return error.value.code


async def _character_id(database, actor: int):
    async with database[1]() as session:
        return await session.scalar(select(Character.id).where(Character.telegram_id == actor))


async def _pick(database, service, *actors, by=LEADER, now=BEFORE):
    view = None
    for actor in actors:
        view = await service.toggle_roster(by, await _character_id(database, actor), now=now)
    return view


async def _launch(database, service, roster=(LEADER, MEMBER_A, MEMBER_B)) -> Expedition:
    await _pick(database, service, *roster)
    await service.run_maintenance(now=START)
    async with database[1]() as session:
        return await session.scalar(select(Expedition))


async def _status(database):
    async with database[1]() as session:
        return await session.scalar(select(Expedition))


async def test_empty_catalog_offers_nothing(database):
    await _seed(database)
    service = _service(database, catalog=())
    assert (await service.hub(LEADER, now=BEFORE)).catalog_empty
    character = await _character_id(database, MEMBER_A)
    assert await _code(service.toggle_roster(LEADER, character, now=BEFORE)) == "catalog_empty"


async def test_only_leader_or_officer_manages_the_roster(database):
    await _seed(database)
    service = _service(database)
    target = await _character_id(database, MEMBER_A)
    assert await _code(service.toggle_roster(MEMBER_B, target, now=BEFORE)) == "not_manager"
    view = await service.toggle_roster(OFFICER, target, now=BEFORE)
    assert view.roster_count == 1 and view.can_manage


async def test_toggle_removes_and_roster_stops_at_six(database):
    await _seed(database)
    service = _service(database)
    await _pick(database, service, *ACTORS[:6])
    last = await _character_id(database, MEMBER_E)
    assert await _code(service.toggle_roster(LEADER, last, now=BEFORE)) == "roster_full"
    first = await _character_id(database, MEMBER_A)
    view = await service.toggle_roster(LEADER, first, now=BEFORE)
    assert view.roster_count == 5


async def test_roster_below_minimum_is_cancelled_at_the_start(database):
    await _seed(database)
    service = _service(database)
    await _pick(database, service, LEADER, MEMBER_A)
    await service.run_maintenance(now=START)
    assert (await _status(database)).status == "cancelled"


async def test_member_who_left_before_the_start_is_dropped(database):
    await _seed(database)
    service = _service(database)
    await _pick(database, service, LEADER, MEMBER_A, MEMBER_B)
    gone = await _character_id(database, MEMBER_B)
    async with database[1].begin() as session:
        await session.delete(await session.get(GuildMember, gone))
    await service.run_maintenance(now=START)
    assert (await _status(database)).status == "cancelled"


async def test_start_freezes_roster_and_never_locks_the_configuration(database):
    await _seed(database)
    service = _service(database)
    expedition = await _launch(database, service)
    assert expedition.status == "active"
    target = await _character_id(database, MEMBER_C)
    assert await _code(service.toggle_roster(LEADER, target, now=START)) == "already_active"
    character = await _character_id(database, MEMBER_A)
    async with database[1]() as session:
        assert await find_combat_configuration_blocker(session, character) is None
        assert await session.scalar(select(func.count()).select_from(GameActivity)) == 0


async def test_start_notifies_the_roster(database):
    await _seed(database)
    service = _service(database)
    await _pick(database, service, LEADER, MEMBER_A, MEMBER_B)
    notices = await service.run_maintenance(now=START)
    assert {notice.telegram_id for notice in notices} == {LEADER, MEMBER_A, MEMBER_B}
    assert notices[0].view == ExpeditionStageNotice(ROUTE.name, 1)


async def test_one_choice_per_stage_and_only_in_its_window(database):
    await _seed(database)
    service = _service(database)
    expedition = await _launch(database, service)
    view = await service.choose(LEADER, expedition.id, 1, NEUTRAL, now=START)
    assert isinstance(view, ExpeditionHubView) and view.answered
    code = await _code(service.choose(LEADER, expedition.id, 1, FAVORABLE, now=START))
    assert code == "already_chosen"
    assert (
        await _code(service.choose(MEMBER_A, expedition.id, 2, FAVORABLE, now=START))
        == "stage_closed"
    )
    assert (
        await _code(service.choose(MEMBER_A, expedition.id, 1, FAVORABLE, now=STAGE_2))
        == "stage_closed"
    )
    assert (
        await _code(service.choose(MEMBER_C, expedition.id, 1, FAVORABLE, now=START))
        == "not_in_roster"
    )


async def test_missing_answers_take_the_default_without_waiting(database):
    await _seed(database)
    service = _service(database)
    expedition = await _launch(database, service)
    await service.choose(LEADER, expedition.id, 1, FAVORABLE, now=START)
    await service.run_maintenance(now=STAGE_2)
    async with database[1]() as session:
        rows = (await session.scalars(select(ExpeditionChoice))).all()
    assert sorted((row.is_default, row.points) for row in rows) == [
        (False, 100),
        (True, 20),
        (True, 20),
    ]


async def _answer(service, expedition, actors, option, now, stage):
    for actor in actors:
        await service.choose(actor, expedition.id, stage, option, now=now)


async def _full_run(service, expedition, roster, option) -> None:
    moments = ((1, START), (2, STAGE_2), (3, STAGE_3))
    for stage, moment in moments:
        await service.run_maintenance(now=moment)
        await _answer(service, expedition, roster, option, moment, stage)
    await service.run_maintenance(now=END)


async def test_silent_guild_fails_and_earns_nothing(database):
    await _seed(database)
    service = _service(database)
    expedition = await _launch(database, service)
    notices = await service.run_maintenance(now=END)
    finished = await _status(database)
    assert (finished.score, finished.result) == (60, "failed")
    assert finished.treasury_crowns == 0
    results = [notice.view for notice in notices if isinstance(notice.view, ExpeditionResultView)]
    assert len(results) == 3 and not any(view.eligible for view in results)
    assert finished.id == expedition.id
    async with database[1]() as session:
        guild = await session.scalar(select(Guild))
        assert guild.treasury_crowns == 0


async def test_best_answers_are_exceptional_and_pay_once(database):
    await _seed(database)
    service = _service(database)
    roster = (LEADER, MEMBER_A, MEMBER_B)
    expedition = await _launch(database, service, roster)
    await _full_run(service, expedition, roster, FAVORABLE)
    await service.run_maintenance(now=END + timedelta(minutes=1))
    finished = await _status(database)
    assert (finished.score, finished.result) == (300, "exceptional")
    assert finished.settled_at is not None
    expected = reward_bundle(30, ExpeditionResult.EXCEPTIONAL)
    async with database[1]() as session:
        for actor in roster:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character.crowns == expected.crowns
        guild = await session.scalar(select(Guild))
        assert guild.treasury_crowns == 5_000
        assert await session.scalar(select(func.count()).select_from(GuildTreasuryEntry)) == 1
    view = await service.last_result(LEADER)
    screen = render_expedition(view)
    assert "Excepcional" in screen.text and "300/300" in screen.text
    assert "Tesouraria" in screen.text and "Recompensas" in screen.text


@pytest.mark.parametrize(
    ("option", "score", "result"),
    [(NEUTRAL, 150, "completed"), (POOR, 75, "failed")],
)
async def test_score_follows_option_quality(database, option, score, result):
    await _seed(database)
    service = _service(database)
    roster = (LEADER, MEMBER_A, MEMBER_B)
    expedition = await _launch(database, service, roster)
    await _full_run(service, expedition, roster, option)
    finished = await _status(database)
    assert (finished.score, finished.result) == (score, result)


async def test_individual_reward_needs_two_active_stages(database):
    await _seed(database)
    service = _service(database)
    roster = (LEADER, MEMBER_A, MEMBER_B)
    expedition = await _launch(database, service, roster)
    for stage, moment in ((1, START), (2, STAGE_2), (3, STAGE_3)):
        await service.run_maintenance(now=moment)
        await _answer(service, expedition, roster[:2], FAVORABLE, moment, stage)
    # Only one active stage for the last member.
    await service.run_maintenance(now=END - timedelta(seconds=1))
    await service.choose(MEMBER_B, expedition.id, 3, FAVORABLE, now=END - timedelta(seconds=1))
    await service.run_maintenance(now=END)
    assert (await service.last_result(LEADER)).eligible
    outsider = await service.last_result(MEMBER_B)
    assert not outsider.eligible and outsider.crowns == 0
    assert "Recompensas" not in render_expedition(outsider).text
    assert "Tesouraria" in render_expedition(outsider).text


async def test_leaving_the_guild_keeps_the_frozen_seat_and_the_reward(database):
    await _seed(database)
    service = _service(database)
    roster = (LEADER, MEMBER_A, MEMBER_B)
    expedition = await _launch(database, service, roster)
    gone = await _character_id(database, MEMBER_B)
    async with database[1].begin() as session:
        await session.delete(await session.get(GuildMember, gone))
    await _full_run(service, expedition, roster, FAVORABLE)
    result = await service.last_result(MEMBER_B)
    assert isinstance(result, ExpeditionResultView) and result.eligible


async def test_active_expedition_blocks_final_dissolution(database):
    await _seed(database)
    service = _service(database)
    expedition = await _launch(database, service)
    async with database[1]() as session:
        assert await _has_cooperative_commitment(session, expedition.guild_id)
    await service.run_maintenance(now=END)
    async with database[1]() as session:
        assert not await _has_cooperative_commitment(session, expedition.guild_id)


async def test_linked_accounts_in_the_roster_are_only_flagged(database):
    await _seed(database)
    async with database[1].begin() as session:
        session.add(
            AccountLink(
                account_a=min(LEADER, MEMBER_A),
                account_b=max(LEADER, MEMBER_A),
            )
        )
    service = _service(database)
    expedition = await _launch(database, service)
    assert expedition.status == "active"
    async with database[1]() as session:
        flags = await session.scalar(
            select(func.count())
            .select_from(AccountRiskFlag)
            .where(AccountRiskFlag.activity_kind == "expedition")
        )
        assert flags == 1

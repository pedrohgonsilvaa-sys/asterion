"""Vínculos, blocks, Recentes, Histórias and Relatos (GDD v1.6.0 §31, §49.18)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.character_surfaces import (
    MAX_HISTORY_CHARACTERS,
    CharacterSurfacesService,
    HistoryInputResult,
)
from asterion.application.groups import GroupError, GroupService
from asterion.application.guilds import GuildError, GuildService
from asterion.application.pvp import PvpError, PvpService
from asterion.application.social import ContentModerationAdmin, SocialError, SocialService
from asterion.application.social_graph import blocked_between, record_recent_contacts
from asterion.application.trades import TradeError, TradeService
from asterion.domain.social import MAX_FRIENDS, STORY_SHARE_COOLDOWN
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterProfile,
    ContentReport,
    FriendRequest,
    Friendship,
    GuildInvite,
    Relato,
)

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
ANA, BEA, CAI = 870001, 870002, 870003
SERVER = "ocaso"


def _name(prefix: str, index: int) -> str:
    return prefix + chr(97 + index // 26) + chr(97 + index % 26)


async def _seed(database, extra: int = 0) -> dict[int, object]:
    actors = [(ANA, "Ana"), (BEA, "Bea"), (CAI, "Cai")]
    actors += [(880000 + index, _name("Extra", index)) for index in range(extra)]
    ids = {}
    async with database[1].begin() as session:
        for actor, name in actors:
            session.add(Account(telegram_id=actor))
            character = Character(
                telegram_id=actor,
                server_id=SERVER,
                name=name,
                race="remanescente",
                character_class="sentinela",
                stage="menu",
                ruleset_version="tdo-1.0.15",
                level=30,
                hp=Decimal("100"),
                max_hp=Decimal("100"),
                vigor=100,
                max_vigor=100,
            )
            session.add(character)
            await session.flush()
            ids[actor] = character.id
    return ids


def _service(database) -> SocialService:
    return SocialService(database[1], SERVER)


async def _code(awaitable) -> str:
    with pytest.raises((SocialError, GroupError, GuildError, TradeError, PvpError)) as error:
        await awaitable
    return error.value.code


async def _set_history(database, character_id, text: str) -> None:
    async with database[1].begin() as session:
        session.add(CharacterProfile(character_id=character_id, revision=1, history=text))


@pytest.mark.asyncio
async def test_friend_request_flow_and_guards(database):
    ids = await _seed(database)
    service = _service(database)
    await service.send_request(ANA, ids[BEA], now=NOW)
    await service.send_request(ANA, ids[BEA], now=NOW)  # idempotent
    assert await _code(service.send_request(BEA, ids[ANA], now=NOW)) == "incoming_pending"
    assert await _code(service.send_request(ANA, ids[ANA], now=NOW)) == "self"

    requests = await service.requests(BEA)
    assert [item.card.name for item in requests.incoming] == ["Ana"]
    await service.respond_request(BEA, requests.incoming[0].request_id, accept=True, now=NOW)

    assert [card.name for card in (await service.friends(ANA)).cards] == ["Bea"]
    assert [card.name for card in (await service.friends(BEA)).cards] == ["Ana"]
    assert await _code(service.send_request(ANA, ids[BEA], now=NOW)) == "already_friends"
    await service.remove_friend(ANA, ids[BEA])
    assert (await service.friends(BEA)).total == 0


@pytest.mark.asyncio
async def test_only_the_recipient_answers_and_only_the_sender_cancels(database):
    ids = await _seed(database)
    service = _service(database)
    await service.send_request(ANA, ids[BEA], now=NOW)
    request_id = (await service.requests(ANA)).outgoing[0].request_id
    assert await _code(service.respond_request(ANA, request_id, accept=True)) == "request_gone"
    assert await _code(service.cancel_request(BEA, request_id)) == "request_gone"
    await service.cancel_request(ANA, request_id)
    assert await _code(service.cancel_request(ANA, request_id)) == "request_gone"


@pytest.mark.asyncio
async def test_request_limits_come_from_section_49(database):
    ids = await _seed(database, extra=31)
    service = _service(database)
    for index in range(20):
        await service.send_request(ANA, ids[880000 + index], now=NOW)
    assert await _code(service.send_request(ANA, ids[880020], now=NOW)) == "sent_full"
    async with database[1].begin() as session:
        await session.execute(FriendRequest.__table__.delete())
    for index in range(30):
        await service.send_request(880000 + index, ids[BEA], now=NOW)
    assert await _code(service.send_request(880030, ids[BEA], now=NOW)) == "target_full"


@pytest.mark.asyncio
async def test_friend_limit_is_enforced_for_both_sides(database):
    ids = await _seed(database)
    filler = await _seed_many(database, MAX_FRIENDS)
    async with database[1].begin() as session:
        for other in filler:
            first, second = sorted((ids[ANA], other))
            session.add(Friendship(character_a=first, character_b=second, created_at=NOW))
    service = _service(database)
    assert await _code(service.send_request(ANA, ids[BEA], now=NOW)) == "friends_full"
    assert await _code(service.send_request(BEA, ids[ANA], now=NOW)) == "target_full"


async def _seed_many(database, count: int) -> list:
    ids = []
    async with database[1].begin() as session:
        for index in range(count):
            actor = 890000 + index
            session.add(Account(telegram_id=actor))
            character = Character(
                telegram_id=actor,
                server_id=SERVER,
                name=_name("Filler", index),
                race="remanescente",
                character_class="sentinela",
                stage="menu",
                ruleset_version="tdo-1.0.15",
                hp=Decimal("100"),
                max_hp=Decimal("100"),
            )
            session.add(character)
            await session.flush()
            ids.append(character.id)
    return ids


@pytest.mark.asyncio
async def test_concurrent_requests_cannot_exceed_the_limit(database):
    ids = await _seed(database, extra=25)
    service = _service(database)
    results = await asyncio.gather(
        *(service.send_request(ANA, ids[880000 + index], now=NOW) for index in range(25)),
        return_exceptions=True,
    )
    refused = [item for item in results if isinstance(item, SocialError)]
    assert len(refused) == 5 and {item.code for item in refused} == {"sent_full"}
    assert len((await service.requests(ANA)).outgoing) == 20


@pytest.mark.asyncio
async def test_block_clears_links_and_stops_every_direct_invite(database):
    ids = await _seed(database)
    service = _service(database)
    await service.send_request(ANA, ids[BEA], now=NOW)
    request_id = (await service.requests(BEA)).incoming[0].request_id
    await service.respond_request(BEA, request_id, accept=True, now=NOW)
    await service.send_request(ANA, ids[CAI], now=NOW)

    groups = GroupService(database[1], SERVER)
    await groups.create_group(ANA)
    guilds = GuildService(database[1], SERVER)
    await guilds.create_guild(ANA, "Vigilia", "VGL", now=NOW)
    invite = await guilds.invite(ANA, "Cai", now=NOW)

    await service.block(CAI, ids[ANA], now=NOW)
    await service.block(BEA, ids[ANA], now=NOW)
    await service.block(BEA, ids[ANA], now=NOW)  # idempotent

    assert (await service.friends(ANA)).total == 0
    assert (await service.requests(ANA)).outgoing == ()
    async with database[1]() as session:
        assert (await session.get(GuildInvite, invite.invite_id)).status == "cancelled"
        assert await blocked_between(session, ids[ANA], ids[BEA])
        assert await blocked_between(session, ids[BEA], ids[ANA])

    # §31 lists friendship, Group, Trade and Guild; the Duel is the author's decision.
    assert await _code(service.send_request(ANA, ids[BEA], now=NOW)) == "unavailable"
    assert await _code(groups.invite(ANA, "Bea")) == "invite_refused"
    assert await _code(guilds.invite(ANA, "Bea", now=NOW)) == "invite_refused"
    trades = TradeService(database[1], SERVER)
    assert await _code(trades.invite(ANA, "Bea", now=NOW)) == "partner_unavailable"
    pvp = PvpService(database[1], SERVER)
    assert await _code(pvp.challenge(ANA, ids[BEA], now=NOW)) == "opponent_busy"

    await service.unblock(BEA, ids[ANA])
    await service.send_request(ANA, ids[BEA], now=NOW)


@pytest.mark.asyncio
async def test_block_after_invite_stops_acceptance(database):
    ids = await _seed(database)
    service = _service(database)
    trades = TradeService(database[1], SERVER)
    trade = await trades.invite(ANA, "Bea", now=NOW)
    pvp = PvpService(database[1], SERVER)
    duel = await pvp.challenge(ANA, ids[CAI], now=NOW)

    await service.block(ANA, ids[BEA], now=NOW)
    await service.block(ANA, ids[CAI], now=NOW)

    assert await _code(trades.respond(BEA, trade.trade_id, accept=True, now=NOW)) == (
        "trade_unavailable"
    )
    assert await _code(pvp.accept(CAI, duel.view.match_id, now=NOW)) == "expired"


@pytest.mark.asyncio
async def test_recents_keep_the_last_14_days_only(database):
    ids = await _seed(database)
    service = _service(database)
    async with database[1].begin() as session:
        await record_recent_contacts(session, [ids[ANA], ids[BEA]], NOW - timedelta(days=13))
    async with database[1].begin() as session:
        await record_recent_contacts(session, [ids[ANA], ids[CAI]], NOW)

    names = [card.name for card in (await service.recents(ANA, now=NOW)).cards]
    assert names == ["Cai", "Bea"]
    later = NOW + timedelta(days=2)
    assert [c.name for c in (await service.recents(ANA, now=later)).cards] == ["Cai"]


@pytest.mark.asyncio
async def test_search_is_prefix_based_rate_limited_and_escapes_wildcards(database):
    await _seed(database)
    service = _service(database)
    assert [card.name for card in await service.search(ANA, "be", now=NOW)] == ["Bea"]
    assert await service.search(ANA, "%%", now=NOW) == ()
    assert await _code(service.search(ANA, "a", now=NOW)) == "query_invalid"
    for _ in range(18):
        await service.search(ANA, "ca", now=NOW)
    assert await _code(service.search(ANA, "ca", now=NOW)) == "search_rate_limited"
    assert await service.search(ANA, "ca", now=NOW + timedelta(seconds=61))


@pytest.mark.asyncio
async def test_public_profile_hides_identity_and_empty_story(database):
    ids = await _seed(database)
    service = _service(database)
    view = await service.public_profile(ANA, ids[BEA])
    assert view.history is None and view.name == "Bea"
    assert not hasattr(view, "telegram_id")
    await _set_history(database, ids[BEA], "Veio do leste.")
    assert (await service.public_profile(ANA, ids[BEA])).history == "Veio do leste."


@pytest.mark.asyncio
async def test_history_limit_links_and_removal(database):
    ids = await _seed(database)
    assert MAX_HISTORY_CHARACTERS == 600
    surfaces = CharacterSurfacesService(database[1], SERVER)
    assert await surfaces.begin_history_input(ANA, 0, 7001)
    for bad in ("veja https://exemplo.com", "fale com @fulano_x", "acesse t.me/grupo"):
        assert await surfaces.save_history(ANA, 7001, bad) == HistoryInputResult.FORBIDDEN
    assert await surfaces.save_history(ANA, 7001, "x" * 601) == HistoryInputResult.TOO_LONG
    assert await surfaces.save_history(ANA, 7001, "x" * 600) == HistoryInputResult.SAVED
    assert not await surfaces.remove_history(ANA, 0)
    assert await surfaces.remove_history(ANA, 1)
    assert (await surfaces.profile(ANA)).history is None
    assert ids


@pytest.mark.asyncio
async def test_share_uses_a_snapshot_and_a_six_hour_recharge(database):
    ids = await _seed(database)
    service = _service(database)
    assert await _code(service.share_story(ANA, now=NOW)) == "no_story"
    await _set_history(database, ids[ANA], "Primeira versão")
    relato = await service.share_story(ANA, now=NOW)
    assert relato.body == "Primeira versão" and relato.author_name == "Ana"

    with pytest.raises(SocialError) as error:
        await service.share_story(ANA, now=NOW + STORY_SHARE_COOLDOWN - timedelta(seconds=1))
    assert error.value.code == "share_cooldown"
    assert error.value.available_at == NOW + STORY_SHARE_COOLDOWN

    async with database[1].begin() as session:
        profile = await session.scalar(
            select(CharacterProfile).where(CharacterProfile.character_id == ids[ANA])
        )
        profile.history = "Versão nova"
    assert (await service.relato(relato.relato_id)).body == "Primeira versão"
    later = await service.share_story(ANA, now=NOW + STORY_SHARE_COOLDOWN)
    assert later.body == "Versão nova"


@pytest.mark.asyncio
async def test_failed_post_does_not_spend_the_recharge(database):
    ids = await _seed(database)
    service = _service(database)
    await _set_history(database, ids[ANA], "Texto")
    relato = await service.share_story(ANA, now=NOW)
    await service.revert_relato(relato.relato_id)
    await service.share_story(ANA, now=NOW)


@pytest.mark.asyncio
async def test_saved_link_cannot_be_shared(database):
    ids = await _seed(database)
    await _set_history(database, ids[ANA], "Velha história com https://exemplo.com")
    assert await _code(_service(database).share_story(ANA, now=NOW)) == "story_forbidden"


@pytest.mark.asyncio
async def test_reports_are_deduplicated_and_upheld_removal_keeps_the_rest(database):
    ids = await _seed(database)
    service = _service(database)
    admin = ContentModerationAdmin(database[1])
    await _set_history(database, ids[BEA], "Texto denunciado")
    assert await _code(service.report_history(BEA, ids[BEA], now=NOW)) == "self"
    await service.report_history(ANA, ids[BEA], now=NOW)
    await service.report_history(ANA, ids[BEA], now=NOW)
    await service.report_history(CAI, ids[BEA], now=NOW)
    reports = await admin.list_reports("open")
    assert len(reports) == 2

    async with database[1]() as session:
        crowns = await session.scalar(select(Character.crowns).where(Character.id == ids[BEA]))

    result = await admin.resolve(reports[0].report_id, uphold=True, note="ok", now=NOW)
    assert result.removed
    assert await admin.list_reports("open") == ()
    assert (await service.public_profile(ANA, ids[BEA])).history is None
    async with database[1]() as session:
        assert (
            await session.scalar(select(Character.crowns).where(Character.id == ids[BEA]))
        ) == crowns
        statuses = (await session.scalars(select(ContentReport.status))).all()
    assert set(statuses) == {"upheld"}


@pytest.mark.asyncio
async def test_upheld_report_does_not_remove_a_text_edited_since(database):
    ids = await _seed(database)
    service = _service(database)
    admin = ContentModerationAdmin(database[1])
    await _set_history(database, ids[BEA], "Antes")
    await service.report_history(ANA, ids[BEA], now=NOW)
    async with database[1].begin() as session:
        profile = await session.scalar(
            select(CharacterProfile).where(CharacterProfile.character_id == ids[BEA])
        )
        profile.history = "Depois"
    report = (await admin.list_reports("open"))[0]
    assert not (await admin.resolve(report.report_id, uphold=True, note=None, now=NOW)).removed
    assert (await service.public_profile(ANA, ids[BEA])).history == "Depois"


@pytest.mark.asyncio
async def test_removed_relato_returns_message_location(database):
    ids = await _seed(database)
    service = _service(database)
    admin = ContentModerationAdmin(database[1])
    await _set_history(database, ids[BEA], "Relato ruim")
    relato = await service.share_story(BEA, now=NOW)
    await service.attach_relato(relato.relato_id, -100123, 55)
    await service.report_relato(ANA, relato.relato_id, now=NOW)
    report = (await admin.list_reports("open"))[0]
    result = await admin.resolve(report.report_id, uphold=True, note=None, now=NOW)
    assert (result.removed, result.chat_id, result.message_id) == (True, -100123, 55)
    assert await _code(service.relato(relato.relato_id)) == "not_found"
    async with database[1]() as session:
        assert await session.scalar(select(func.count(Relato.id))) == 1

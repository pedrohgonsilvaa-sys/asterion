"""Perfil público, Histórias, Relatos e denúncias (GDD v1.6.0 §31.1, §49.18).

Vínculos (Amigos, Pedidos, Bloqueados, Recentes e Busca) saiu do produto.
"""

from __future__ import annotations

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
from asterion.application.trades import TradeError, TradeService
from asterion.domain.social import STORY_SHARE_COOLDOWN
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterBlock,
    CharacterProfile,
    ContentReport,
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
async def test_old_blocks_no_longer_stop_direct_invites_or_acceptance(database):
    """Vínculos saiu do produto: bloqueios gravados antes não afetam Grupo, Guilda,
    Troca nem Duelo (decisão do autor)."""
    ids = await _seed(database)
    async with database[1].begin() as session:
        for blocker, blocked in ((BEA, ANA), (ANA, CAI), (CAI, ANA)):
            session.add(
                CharacterBlock(
                    blocker_character_id=ids[blocker],
                    blocked_character_id=ids[blocked],
                    created_at=NOW,
                )
            )

    groups = GroupService(database[1], SERVER)
    await groups.create_group(ANA)
    await groups.invite(ANA, "Bea")
    guilds = GuildService(database[1], SERVER)
    await guilds.create_guild(ANA, "Vigilia", "VGL", now=NOW)
    await guilds.invite(ANA, "Bea", now=NOW)
    trades = TradeService(database[1], SERVER)
    trade = await trades.invite(ANA, "Bea", now=NOW)
    await trades.respond(BEA, trade.trade_id, accept=True, now=NOW)
    pvp = PvpService(database[1], SERVER)
    duel = await pvp.challenge(ANA, ids[CAI], now=NOW)
    await pvp.accept(CAI, duel.view.match_id, now=NOW)


def test_vinculos_service_api_is_gone():
    service_methods = set(dir(SocialService))
    for gone in (
        "search", "send_request", "respond_request", "cancel_request", "remove_friend",
        "block", "unblock", "friends", "blocked", "recents", "requests",
    ):
        assert gone not in service_methods


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

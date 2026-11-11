"""Effects of the six Obras beyond Alojamentos (§30.2, author delegation 2026-11-11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application.guild_works import character_work_levels
from asterion.application.guilds import GuildService
from asterion.domain.guild_battle import (
    REWARD_COSMETICS,
    TITLE_VETERAN,
    guild_reward_tier,
)
from asterion.domain.guild_works import (
    NO_WORKS,
    WorkLevels,
    discounted,
    effect_text,
    with_bonus,
)
from asterion.domain.guilds import ProjectKind
from asterion.domain.market import cumulative_fee, split_sale
from asterion.infrastructure.db.models import Account, Character, GuildProject

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
LEADER, MEMBER = 870001, 870002


def test_levels_map_to_the_provisional_tables():
    works = WorkLevels.from_levels(
        {
            "forge": 5,
            "veil_altar": 1,
            "treasury": 2,
            "veil_archive": 3,
            "hunters_post": 4,
            "war_hall": 9,  # Clamped to V.
            "lodging": 5,  # Not a WorkLevels effect.
        }
    )
    assert works.enhancement_discount == 10
    assert works.respec_discount == 10
    assert works.market_fee_bps == 400
    assert works.recipe_discount == 12
    assert works.hunt_crown_bonus == 8
    assert works.battle_crowns == 275
    assert (NO_WORKS.market_fee_bps, NO_WORKS.battle_crowns, NO_WORKS.hunt_crown_bonus) == (
        500,
        0,
        0,
    )


def test_discount_and_bonus_round_down():
    assert discounted(1_000, 10) == 900
    assert discounted(155, 10) == 140  # 15,5 off rounds down to 15.
    assert discounted(500, 0) == 500
    assert discounted(0, 50) == 0
    assert with_bonus(30, 10) == 33
    assert with_bonus(9, 10) == 9  # 0,9 rounds down to 0.
    assert with_bonus(0, 10) == 0


def test_fee_in_basis_points_keeps_the_default_five_percent():
    assert cumulative_fee(190) == 9
    assert cumulative_fee(190, 400) == 7
    assert cumulative_fee(1_000, 250) == 25
    assert split_sale(0, 0, 1_000, 300).fee == 30


def test_effect_texts():
    assert effect_text(ProjectKind.FORGE, 2) == "−4% Coroas no Aprimoramento"
    assert effect_text(ProjectKind.TREASURY, 1) == "Taxa do Mercado 4,5% nos anúncios criados"
    assert effect_text(ProjectKind.TREASURY, 4) == "Taxa do Mercado 3% nos anúncios criados"
    assert effect_text(ProjectKind.WAR_HALL, 5) == (
        "+275 Coroas por combatente em cada Batalha de Guildas"
    )
    assert effect_text(ProjectKind.LODGING, 3) is None


def test_reward_tiers_by_eligible_rank():
    assert [guild_reward_tier(rank) for rank in (1, 2, 3, 4, 10, 11)] == [
        "champion",
        "podium",
        "podium",
        "top10",
        "top10",
        "veteran",
    ]
    assert all(TITLE_VETERAN in items for items in REWARD_COSMETICS.values())
    with pytest.raises(ValueError):
        guild_reward_tier(0)


async def _seed(database) -> None:
    async with database[1].begin() as session:
        for actor, name in ((LEADER, "Lider"), (MEMBER, "Membro")):
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    telegram_id=actor,
                    server_id="ocaso",
                    name=name,
                    race="remanescente",
                    character_class="sentinela",
                    stage="road_active",
                    ruleset_version="tdo-1.0.15",
                    hp=Decimal("100"),
                    max_hp=Decimal("100"),
                    vigor=100,
                    max_vigor=100,
                    crowns=1_000,
                )
            )


@pytest.mark.asyncio
async def test_only_completed_levels_of_the_current_guild_apply(database):
    await _seed(database)
    service = GuildService(database[1], "ocaso")
    guild = await service.create_guild(LEADER, "Vigilia", "VGL", now=NOW)
    invite = await service.invite(LEADER, "Membro", now=NOW)
    member = await service.respond_invite(MEMBER, invite.invite_id, accept=True, now=NOW)
    async with database[1].begin() as session:
        for kind, level, status in (
            ("forge", 1, "completed"),
            ("forge", 2, "completed"),
            ("forge", 3, "building"),  # Not finished: no effect yet.
            ("hunters_post", 1, "cancelled"),
        ):
            session.add(
                GuildProject(
                    guild_id=guild.guild_id,
                    kind=kind,
                    level=level,
                    status=status,
                    cost=10,
                    funded=0 if status == "cancelled" else 10,
                    started_at=NOW,
                    completes_at=NOW + timedelta(days=1) if status == "building" else None,
                )
            )
    async with database[1]() as session:
        works = await character_work_levels(session, member.viewer_character_id)
    assert (works.forge, works.hunters_post) == (2, 0)
    assert works.enhancement_discount == 4

    # §30.3: leaving removes the benefits at once.
    await service.leave(MEMBER, now=NOW)
    async with database[1]() as session:
        assert await character_work_levels(session, member.viewer_character_id) == NO_WORKS
        leader_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == LEADER)
        )
        assert (await character_work_levels(session, leader_id)).forge == 2

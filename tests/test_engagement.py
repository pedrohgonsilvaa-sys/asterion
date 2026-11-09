"""Dádiva Diária, Chamado and Códigos de Asterion (GDD v1.6.0 §32, §49.10, §49.19)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update

from asterion.application.account_risk import AccountRiskAdmin
from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.cosmetic_catalog import COSMETICS_BY_ID
from asterion.application.engagement import DailyGiftService, EngagementError
from asterion.application.promo_codes import PromoCodeAdmin, PromoCodeService
from asterion.application.recruitment import RecruitmentService, link_pending_invite
from asterion.domain.engagement import (
    DAILY_GIFT,
    RECRUIT_PRESTIGE,
    REGION_SUPPLY,
    Bundle,
    PromoRewardError,
    bundle_materials,
    normalize_promo_code,
    promo_crowns,
    validate_promo_entry,
)
from asterion.domain.professions import IRON, MATERIAL_NAMES, VDE_FRAGMENT_II
from asterion.infrastructure.db.models import (
    Account,
    AccountRiskFlag,
    Character,
    CharacterCosmetic,
    MaterialStack,
    PromoRedemption,
    RecruitmentInvite,
    RecruitmentLink,
    WorldState,
)

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
ANA, BEA = 910001, 910002
SERVER = "ocaso"


async def _make(database, actor, name, *, level=1, created=NOW, region=None):
    async with database[1].begin() as session:
        session.add(Account(telegram_id=actor))
        character = Character(
            telegram_id=actor,
            server_id=SERVER,
            name=name,
            race="remanescente",
            character_class="sentinela",
            stage="menu",
            ruleset_version="tdo-1.0.15",
            level=level,
            hp=Decimal("100"),
            max_hp=Decimal("100"),
            created_at=created,
        )
        session.add(character)
        await session.flush()
        if created is None:
            await session.execute(
                update(Character).where(Character.id == character.id).values(created_at=None)
            )
        if region:
            session.add(WorldState(character_id=character.id, region=region, location="X"))
        return character.id


async def _crowns(database, actor) -> int:
    async with database[1]() as session:
        return await session.scalar(select(Character.crowns).where(Character.telegram_id == actor))


async def _materials(database, actor) -> dict[str, int]:
    async with database[1]() as session:
        rows = (
            await session.execute(
                select(MaterialStack.material_id, MaterialStack.bound, MaterialStack.quantity)
                .join(Character, Character.id == MaterialStack.character_id)
                .where(Character.telegram_id == actor)
            )
        ).all()
    assert all(bound for _, bound, _ in rows)
    totals: dict[str, int] = {}
    for material_id, _, quantity in rows:
        totals[material_id] = totals.get(material_id, 0) + quantity
    return totals


async def _code(awaitable) -> str:
    with pytest.raises(EngagementError) as error:
        await awaitable
    return error.value.code


async def _set_level(database, actor, level) -> None:
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = level


def test_daily_table_matches_section_49():
    assert sum(item.crowns for item in DAILY_GIFT) == 500
    assert sum(item.basics for item in DAILY_GIFT) == 6
    assert sum(item.fragments for item in DAILY_GIFT) == 5
    assert len(DAILY_GIFT) == 7


def test_every_region_material_exists_in_the_catalog():
    for supply in REGION_SUPPLY.values():
        for material_id in (*supply.basics, supply.fragment):
            assert material_id in MATERIAL_NAMES


def test_basics_rotate_and_grade_follows_region():
    assert bundle_materials(Bundle(basics=2), "Terras do Ocaso") == {
        IRON: 1,
        "material.tdo.couro_escoriado": 1,
    }
    four = bundle_materials(Bundle(basics=4), "Planícies de Nareth")
    assert len(four) == 4 and set(four.values()) == {1}
    assert bundle_materials(Bundle(fragments=2), "Vales dos Enforcados") == {VDE_FRAGMENT_II: 2}
    assert bundle_materials(Bundle(basics=1), None) == {IRON: 1}


def test_recruit_prestige_exists_in_cosmetic_catalog():
    names = [COSMETICS_BY_ID[item.cosmetic_id].name for item in RECRUIT_PRESTIGE]
    assert names == [
        "Guia da Estrada",
        "Voz que Reúne",
        "Laço das Cinzas",
        "Círculo dos Caminhantes",
        "Arauto de Asterion",
    ]


def test_promo_code_format_and_caps():
    assert normalize_promo_code(" abc-123 ") == "ABC-123"
    assert normalize_promo_code("abc") is None
    assert normalize_promo_code("com espaço") is None
    validate_promo_entry(
        {"c_multiplier": "0.50", "basics": 4, "fragments": 2}, allow_above_normal=False
    )
    for above in (
        {"c_multiplier": "0.51"},
        {"basics": 5},
        {"fragments": 3},
    ):
        with pytest.raises(PromoRewardError, match="reward_above_normal"):
            validate_promo_entry(above, allow_above_normal=False)
        validate_promo_entry(above, allow_above_normal=True)
    for over in ({"c_multiplier": "1.01"}, {"basics": 9}, {"fragments": 4}):
        with pytest.raises(PromoRewardError, match="reward_above_hard_cap"):
            validate_promo_entry(over, allow_above_normal=True)
    with pytest.raises(PromoRewardError, match="reward_empty"):
        validate_promo_entry({}, allow_above_normal=False)
    with pytest.raises(PromoRewardError, match="reward_malformed"):
        validate_promo_entry({"basics": -1}, allow_above_normal=False)


def test_promo_crowns_use_character_level():
    assert promo_crowns("0.50", 1) == 60  # C(1)=120
    assert promo_crowns("1.00", 60) == 1000
    # 0.327 x 200 = 65.4: rounding to 65 first would give 60 instead of 70.
    assert promo_crowns("0.327", 7) == 70


@pytest.mark.asyncio
async def test_daily_claim_is_idempotent_per_cycle_and_resets_at_six(database):
    await _make(database, ANA, "Ana")
    service = DailyGiftService(database[1], SERVER)
    first = await service.claim(ANA, now=NOW)
    assert (first.day, first.already_claimed, first.granted.crowns) == (1, False, 100)
    again = await service.claim(ANA, now=NOW + timedelta(hours=1))
    assert (again.day, again.already_claimed, again.granted) == (1, True, None)
    assert await _crowns(database, ANA) == 100
    # 06:00 São Paulo is 09:00 UTC.
    before = datetime(2026, 11, 9, 8, 59, tzinfo=UTC)
    assert (await service.claim(ANA, now=before)).already_claimed
    after = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)
    assert (await service.claim(ANA, now=after)).day == 2


@pytest.mark.asyncio
async def test_concurrent_daily_claims_pay_once(database):
    await _make(database, ANA, "Ana")
    service = DailyGiftService(database[1], SERVER)
    results = await asyncio.gather(*(service.claim(ANA, now=NOW) for _ in range(5)))
    assert sum(not item.already_claimed for item in results) == 1
    assert await _crowns(database, ANA) == 100


@pytest.mark.asyncio
async def test_full_cycle_totals_and_a_missed_day_only_waits(database):
    await _make(database, ANA, "Ana", region="Terras do Ocaso")
    service = DailyGiftService(database[1], SERVER)
    days = []
    moment = NOW
    for index in range(8):
        # Skipping cycles between claims must not reset the sequence.
        moment += timedelta(days=1 + index % 3)
        days.append((await service.claim(ANA, now=moment)).day)
    assert days == [1, 2, 3, 4, 5, 6, 7, 1]
    assert await _crowns(database, ANA) == 600
    materials = await _materials(database, ANA)
    assert materials.pop("material.tdo.fragmento_aprimoramento_i") == 5
    assert sum(materials.values()) == 6


@pytest.mark.asyncio
async def test_daily_progress_survives_character_deletion(database):
    character_id = await _make(database, ANA, "Ana")
    service = DailyGiftService(database[1], SERVER)
    await service.claim(ANA, now=NOW)
    async with database[1].begin() as session:
        await delete_character_owned_data(session, character_id)
    async with database[1].begin() as session:
        session.add(
            Character(
                telegram_id=ANA,
                server_id=SERVER,
                name="Nova",
                race="remanescente",
                character_class="sentinela",
                stage="menu",
                ruleset_version="tdo-1.0.15",
                hp=Decimal("100"),
                max_hp=Decimal("100"),
            )
        )
    assert (await service.claim(ANA, now=NOW)).already_claimed


async def _recruit_setup(database, recruit_level=1, recruit_created=NOW):
    await _make(database, ANA, "Ana", level=10)
    await _make(database, BEA, "Bea", level=recruit_level, created=recruit_created)
    service = RecruitmentService(database[1], SERVER)
    view = await service.view(ANA, now=NOW)
    return service, view.code


@pytest.mark.asyncio
async def test_link_gives_nothing_and_milestones_pay_each_side_once(database):
    service, code = await _recruit_setup(database)
    await service.link(BEA, code, now=NOW)
    assert await _crowns(database, ANA) == 0 and await _crowns(database, BEA) == 0
    assert await _code(service.claim(BEA, now=NOW)) == "nothing_to_claim"

    await _set_level(database, BEA, 30)
    assert (await service.view(BEA, now=NOW)).claimable_crowns == 300
    assert (await service.claim(BEA, now=NOW)).crowns == 300
    assert (await service.claim(ANA, now=NOW)).crowns == 300
    assert await _code(service.claim(BEA, now=NOW)) == "nothing_to_claim"
    await _set_level(database, BEA, 60)
    assert (await service.claim(BEA, now=NOW)).crowns == 300
    assert (await service.claim(ANA, now=NOW)).crowns == 300
    assert await _crowns(database, ANA) == 600 and await _crowns(database, BEA) == 600


@pytest.mark.asyncio
async def test_link_rules(database):
    service, code = await _recruit_setup(database)
    assert await _code(service.link(BEA, "AAAAAAAA", now=NOW)) == "recruit_code_invalid"
    assert await _code(service.link(ANA, code, now=NOW)) == "recruit_self"
    late = NOW + timedelta(hours=72, seconds=1)
    assert await _code(service.link(BEA, code, now=late)) == "recruit_window_closed"
    await service.link(BEA, code, now=NOW + timedelta(hours=72))
    assert await _code(service.link(BEA, code, now=NOW)) == "recruit_already_linked"


@pytest.mark.asyncio
async def test_old_characters_and_level_ten_cannot_be_recruited(database):
    await _make(database, ANA, "Ana", level=10)
    await _make(database, BEA, "Bea", created=None)
    await _make(database, 910003, "Cai", level=10)
    service = RecruitmentService(database[1], SERVER)
    code = (await service.view(ANA, now=NOW)).code
    assert await _code(service.link(BEA, code, now=NOW)) == "recruit_window_closed"
    assert await _code(service.link(910003, code, now=NOW)) == "recruit_window_closed"
    assert not (await service.view(BEA, now=NOW)).can_link


@pytest.mark.asyncio
async def test_recruiter_below_level_ten_is_refused(database):
    await _make(database, ANA, "Ana", level=9)
    await _make(database, BEA, "Bea")
    service = RecruitmentService(database[1], SERVER)
    code = (await service.view(ANA, now=NOW)).code
    assert await _code(service.link(BEA, code, now=NOW)) == "recruiter_ineligible"


@pytest.mark.asyncio
async def test_linked_accounts_are_flagged_and_still_paid(database):
    service, code = await _recruit_setup(database)
    await AccountRiskAdmin(database[1]).link(ANA, BEA, note="mesmo dono")
    await service.link(BEA, code, now=NOW)
    async with database[1]() as session:
        flags = (await session.scalars(select(AccountRiskFlag))).all()
    assert [flag.activity_kind for flag in flags] == ["recruitment"]
    await _set_level(database, BEA, 10)
    assert (await service.claim(BEA, now=NOW)).crowns == 100


@pytest.mark.asyncio
async def test_only_ten_recruits_pay_the_recruiter_but_all_count_for_prestige(database):
    await _make(database, ANA, "Ana", level=10)
    service = RecruitmentService(database[1], SERVER)
    code = (await service.view(ANA, now=NOW)).code
    for index in range(12):
        actor = 920000 + index
        await _make(database, actor, "Recruta" + chr(97 + index))
        await service.link(actor, code, now=NOW + timedelta(seconds=index))
        await _set_level(database, actor, 60)
    assert (await service.claim(ANA, now=NOW)).crowns == 6000
    assert await _code(service.claim(ANA, now=NOW)) == "nothing_to_claim"
    # Each recruit still receives their own side.
    assert (await service.claim(920011, now=NOW)).crowns == 600
    view = await service.view(ANA, now=NOW)
    assert view.recruits == 12 and view.prestige == (
        "Guia da Estrada",
        "Voz que Reúne",
        "Laço das Cinzas",
        "Círculo dos Caminhantes",
    )
    async with database[1]() as session:
        count = await session.scalar(select(func.count()).select_from(CharacterCosmetic))
    assert count == 4


@pytest.mark.asyncio
async def test_concurrent_recruiter_claims_pay_once(database):
    service, code = await _recruit_setup(database)
    await service.link(BEA, code, now=NOW)
    await _set_level(database, BEA, 10)
    results = await asyncio.gather(
        *(service.claim(ANA, now=NOW) for _ in range(4)), return_exceptions=True
    )
    assert sum(not isinstance(item, Exception) for item in results) == 1
    assert await _crowns(database, ANA) == 100


@pytest.mark.asyncio
async def test_deep_link_before_creation_is_consumed_by_creation(database):
    await _make(database, ANA, "Ana", level=10)
    service = RecruitmentService(database[1], SERVER)
    code = (await service.view(ANA, now=NOW)).code
    assert await service.open_invite(BEA, code, now=NOW) is False
    async with database[1].begin() as session:
        character = Character(
            telegram_id=BEA,
            server_id=SERVER,
            name="Bea",
            race="remanescente",
            character_class="sentinela",
            stage="prologo",
            ruleset_version="tdo-1.0.15",
            hp=Decimal("100"),
            max_hp=Decimal("100"),
            created_at=NOW,
        )
        session.add(character)
        await session.flush()
        await link_pending_invite(session, BEA, SERVER, character.id, NOW)
    async with database[1]() as session:
        assert await session.get(RecruitmentInvite, (BEA, SERVER)) is None
        link = await session.get(RecruitmentLink, (BEA, SERVER))
    assert link.recruiter_telegram_id == ANA


@pytest.mark.asyncio
async def test_invalid_invite_never_stops_creation(database):
    await _make(database, ANA, "Ana", level=2)
    service = RecruitmentService(database[1], SERVER)
    code = (await service.view(ANA, now=NOW)).code
    assert await service.open_invite(BEA, code, now=NOW) is False
    character_id = await _make_existing_account(database, BEA, "Bea")
    async with database[1].begin() as session:
        await link_pending_invite(session, BEA, SERVER, character_id, NOW)
    async with database[1]() as session:
        assert await session.get(RecruitmentLink, (BEA, SERVER)) is None
        assert await session.get(RecruitmentInvite, (BEA, SERVER)) is None


async def _make_existing_account(database, actor, name):
    async with database[1].begin() as session:
        character = Character(
            telegram_id=actor,
            server_id=SERVER,
            name=name,
            race="remanescente",
            character_class="sentinela",
            stage="prologo",
            ruleset_version="tdo-1.0.15",
            hp=Decimal("100"),
            max_hp=Decimal("100"),
            created_at=NOW,
        )
        session.add(character)
        await session.flush()
        return character.id


async def _promo(database, **kwargs):
    defaults = {
        "code": "CINZAS-2026",
        "reward_table": [{"c_multiplier": "0.50", "basics": 2, "fragments": 1}],
        "now": NOW,
    }
    return await PromoCodeAdmin(database[1], SERVER).create(**{**defaults, **kwargs})


@pytest.mark.asyncio
async def test_code_redeems_once_and_is_case_insensitive(database):
    await _make(database, ANA, "Ana", level=60, region="Vales dos Enforcados")
    await _promo(database)
    service = PromoCodeService(database[1], SERVER)
    result = await service.redeem(ANA, "cinzas-2026", now=NOW)
    assert result.granted.crowns == 500
    materials = await _materials(database, ANA)
    assert materials[VDE_FRAGMENT_II] == 1 and sum(materials.values()) == 3
    assert await _code(service.redeem(ANA, "CINZAS-2026", now=NOW)) == "promo_already_redeemed"


@pytest.mark.asyncio
async def test_code_window_states(database):
    await _make(database, ANA, "Ana")
    row = await _promo(database)
    service = PromoCodeService(database[1], SERVER)
    assert row.expires_at == NOW + timedelta(days=30)
    assert await _code(service.redeem(ANA, "NAO-EXISTE", now=NOW)) == "promo_invalid"
    assert await _code(service.redeem(ANA, "abc", now=NOW)) == "promo_invalid"
    assert (
        await _code(service.redeem(ANA, "CINZAS-2026", now=NOW + timedelta(days=30, seconds=1)))
        == "promo_expired"
    )
    await PromoCodeAdmin(database[1], SERVER).set_active("CINZAS-2026", False)
    assert await _code(service.redeem(ANA, "CINZAS-2026", now=NOW + timedelta(minutes=9))) == (
        "promo_invalid"
    )


@pytest.mark.asyncio
async def test_global_limit_under_concurrency(database):
    for index in range(4):
        await _make(database, 930000 + index, "Pessoa" + chr(97 + index))
    await _promo(database, global_limit=2)
    service = PromoCodeService(database[1], SERVER)
    results = await asyncio.gather(
        *(service.redeem(930000 + index, "CINZAS-2026", now=NOW) for index in range(4)),
        return_exceptions=True,
    )
    assert sum(not isinstance(item, Exception) for item in results) == 2
    assert {item.code for item in results if isinstance(item, EngagementError)} == {
        "promo_exhausted"
    }


@pytest.mark.asyncio
async def test_character_deletion_does_not_grant_a_new_redemption(database):
    character_id = await _make(database, ANA, "Ana")
    await _promo(database)
    service = PromoCodeService(database[1], SERVER)
    await service.redeem(ANA, "CINZAS-2026", now=NOW)
    async with database[1].begin() as session:
        await delete_character_owned_data(session, character_id)
    await _make_existing_account(database, ANA, "Nova")
    assert await _code(service.redeem(ANA, "CINZAS-2026", now=NOW)) == "promo_already_redeemed"


@pytest.mark.asyncio
async def test_character_scope_allows_a_new_character(database):
    character_id = await _make(database, ANA, "Ana")
    await _promo(database, scope="character")
    service = PromoCodeService(database[1], SERVER)
    await service.redeem(ANA, "CINZAS-2026", now=NOW)
    async with database[1].begin() as session:
        await delete_character_owned_data(session, character_id)
    await _make_existing_account(database, ANA, "Nova")
    await service.redeem(ANA, "CINZAS-2026", now=NOW)


@pytest.mark.asyncio
async def test_random_prize_is_stored_and_follows_the_redemption_id(database):
    await _make(database, ANA, "Ana", level=10)
    table = [
        {"weight": 1, "c_multiplier": "0.10", "basics": 0, "fragments": 0},
        {"weight": 1, "c_multiplier": "0", "basics": 1, "fragments": 0},
    ]
    await _promo(database, reward_table=table)
    await PromoCodeService(database[1], SERVER).redeem(ANA, "CINZAS-2026", now=NOW)
    async with database[1]() as session:
        row = await session.scalar(select(PromoRedemption))
    from asterion.application.promo_codes import _draw

    assert row.entry_index == _draw(table, row.id)
    assert _draw(table, row.id) == _draw(table, row.id)


@pytest.mark.asyncio
async def test_attempts_are_limited_per_minute_and_per_hour(database):
    await _make(database, ANA, "Ana")
    service = PromoCodeService(database[1], SERVER)
    for _ in range(5):
        assert await _code(service.redeem(ANA, "NAO-EXISTE", now=NOW)) == "promo_invalid"
    assert await _code(service.redeem(ANA, "NAO-EXISTE", now=NOW)) == "promo_rate_limited"
    moment = NOW
    for _ in range(3):
        moment += timedelta(minutes=2)
        for _ in range(5):
            assert await _code(service.redeem(ANA, "NAO-EXISTE", now=moment)) == "promo_invalid"
    moment += timedelta(minutes=2)
    assert await _code(service.redeem(ANA, "NAO-EXISTE", now=moment)) == "promo_rate_limited"
    moment = NOW + timedelta(minutes=61)
    assert await _code(service.redeem(ANA, "NAO-EXISTE", now=moment)) == "promo_invalid"

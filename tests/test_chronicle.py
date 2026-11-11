"""Crônica I, Trilha, vote and the competitive cycle on PostgreSQL (GDD §5, §49.16)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.chronicle import (
    ChronicleAdmin,
    ChronicleError,
    ChronicleService,
    record_objective,
    record_repeatable,
)
from asterion.application.competitive_cycle import entry_closed
from asterion.domain.chronicle import (
    CHAPTERS_BY_NUMBER,
    Outcome,
    Phase,
    calendar_for,
    required_objectives,
)
from asterion.infrastructure.db.models import (
    Account,
    Achievement,
    ArenaProfile,
    Character,
    CharacterCosmetic,
    ChronicleClaim,
    ChronicleCycleLog,
    ChronicleElector,
    Guild,
    GuildBattle,
    GuildBattleFight,
    GuildBattleFightMember,
    GuildBattleProfile,
    GuildBattleRegistration,
    Quest,
    VigilHallEntry,
)

SERVER = "ocaso"
DAY1 = date(2026, 12, 1)
CAL = calendar_for(DAY1)
BEFORE = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
WEEK1 = CAL.starts_at + timedelta(hours=1)
ANA, BEA, CAIO = 930001, 930002, 930003


async def _make(database, actor, name, *, p1=True, level=10):
    async with database[1].begin() as session:
        await session.merge(Account(telegram_id=actor))
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
            created_at=BEFORE,
        )
        session.add(character)
        await session.flush()
        if p1:
            session.add(
                Quest(character_id=character.id, quest_id="P1", title="P1", status="completed")
            )
        return character.id


async def _schedule(database):
    await ChronicleAdmin(database[1], SERVER).set_day1(DAY1, "teste", now=BEFORE)


async def _record(database, actor, objective_id, now):
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor).with_for_update()
        )
        return await record_objective(session, SERVER, character, objective_id, now=now)


async def _repeat(database, actor, source, key, now, started_at=None):
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor).with_for_update()
        )
        return await record_repeatable(
            session, SERVER, character, source, key, now=now, started_at=started_at
        )


async def _conclude_all(database, actor, chapters, now):
    service = ChronicleService(database[1], SERVER)
    for number in chapters:
        for objective_id in sorted(required_objectives(number)):
            await _record(database, actor, objective_id, now)
        await service.conclude_chapter(actor, number, now=now)


async def test_nothing_opens_without_day1(database):
    await _make(database, ANA, "Ana")
    assert not await _record(database, ANA, "cap_01_obj_01", WEEK1)
    view = await ChronicleService(database[1], SERVER).view(ANA, now=WEEK1)
    assert view.phase is Phase.UNSCHEDULED and view.points == 0


async def test_day1_changes_until_start_then_only_extension(database):
    admin = ChronicleAdmin(database[1], SERVER)
    await admin.set_day1(date(2026, 12, 8), "primeira data", now=BEFORE)
    await admin.set_day1(DAY1, "data final", now=BEFORE)
    with pytest.raises(ChronicleError) as error:
        await admin.set_day1(date(2026, 12, 15), "tarde demais", now=WEEK1)
    assert error.value.code == "chronicle_started"
    new_end = CAL.end_at + timedelta(days=2)
    extended = await admin.extend(new_end, "falha do servidor", now=WEEK1)
    assert extended.vote_closes_at == new_end - timedelta(hours=48)
    with pytest.raises(ChronicleError) as error:
        await admin.extend(new_end + timedelta(days=1), "sem prazo", now=extended.vote_closes_at)
    assert error.value.code == "chronicle_closing_started"
    async with database[1]() as session:
        actions = (await session.scalars(select(ChronicleCycleLog.action))).all()
    assert sorted(actions) == ["extend", "set_day1", "set_day1"]


async def test_points_are_unique_per_account_and_need_p1(database):
    await _schedule(database)
    await _make(database, ANA, "Ana")
    await _make(database, BEA, "Bea", p1=False)
    service = ChronicleService(database[1], SERVER)
    assert not await _record(database, ANA, "cap_02_obj_01", WEEK1)  # chapter 2 not open
    assert await _record(database, ANA, "cap_01_obj_01", WEEK1)
    assert not await _record(database, ANA, "cap_01_obj_01", WEEK1)
    assert not await _record(database, BEA, "cap_01_obj_01", WEEK1)
    assert (await service.view(ANA, now=WEEK1)).points == 50
    assert (await service.view(BEA, now=WEEK1)).gate_ok is False
    # A recreated character replays the story but never pays the account again.
    async with database[1].begin() as session:
        old = await session.scalar(select(Character.id).where(Character.telegram_id == ANA))
        await delete_character_owned_data(session, old)
    await _make(database, ANA, "Anova")
    assert await _record(database, ANA, "cap_01_obj_01", WEEK1)
    view = await service.view(ANA, now=WEEK1)
    assert view.points == 50
    assert view.chapters[0].objectives[0].done


async def test_level_gates_elite_and_boss_objectives(database):
    await _schedule(database)
    await _make(database, ANA, "Ana", level=4)
    week4 = CAL.chapter_opens_at(4) + timedelta(hours=1)
    assert not await _record(database, ANA, "cap_04_obj_04", week4)
    view = await ChronicleService(database[1], SERVER).view(ANA, now=week4)
    boss = next(item for item in view.chapters[3].objectives if item.objective.min_level == 5)
    assert boss.level_locked


async def test_repeatable_caps_and_idempotence(database):
    await _schedule(database)
    await _make(database, ANA, "Ana")
    assert await _repeat(database, ANA, "rep_cr01_desbravar", "a1", WEEK1) == 25
    assert await _repeat(database, ANA, "rep_cr01_desbravar", "a1", WEEK1) == 0
    assert await _repeat(database, ANA, "rep_cr01_desbravar", "a2", WEEK1) == 25
    assert await _repeat(database, ANA, "rep_cr01_desbravar", "a3", WEEK1) == 0  # 2/day
    granted = [
        await _repeat(database, ANA, "rep_cr01_masmorra", f"run{i}", WEEK1) for i in range(6)
    ]
    assert granted == [25, 25, 25, 25, 0, 0]  # 150 x 1 released week
    week2 = CAL.chapter_opens_at(2) + timedelta(hours=1)
    assert await _repeat(database, ANA, "rep_cr01_masmorra", "run9", week2) == 25
    track = await ChronicleService(database[1], SERVER).track(ANA, now=week2)
    assert track.repeatable_points == 175 and track.repeatable_cap == 300
    # After T only an activity started before it may settle, until T+2h.
    late = CAL.end_at + timedelta(minutes=30)
    assert await _repeat(database, ANA, "rep_cr01_masmorra", "late", late) == 0
    started = CAL.end_at - timedelta(minutes=10)
    assert await _repeat(database, ANA, "rep_cr01_masmorra", "grace", late, started) == 25


async def test_chapter_conclusion_and_trilha_claims(database):
    await _schedule(database)
    await _make(database, ANA, "Ana")
    service = ChronicleService(database[1], SERVER)
    with pytest.raises(ChronicleError) as error:
        await service.conclude_chapter(ANA, 1, now=WEEK1)
    assert error.value.code == "chronicle_objectives_missing"
    await _conclude_all(database, ANA, [1], WEEK1)
    view = await service.view(ANA, now=WEEK1)
    assert view.chapters[0].concluded and view.points == 500
    with pytest.raises(ChronicleError):
        await service.conclude_chapter(ANA, 1, now=WEEK1)
    result = await service.claim(ANA, now=WEEK1)
    assert result.milestones == (("free", 2), ("free", 4))
    assert result.granted.crowns == 250
    assert sum(item.quantity for item in result.granted.items) == 3
    with pytest.raises(ChronicleError) as error:
        await service.claim(ANA, now=WEEK1)
    assert error.value.code == "nothing_to_claim"
    # The Passe unlocks Premium retroactively from the same points.
    await ChronicleAdmin(database[1], SERVER).grant_pass(ANA, "teste", now=WEEK1)
    result = await service.claim(ANA, now=WEEK1)
    assert result.milestones == (("premium", 4),)
    assert result.granted.crowns == 0 and result.cosmetics == ("Contador de Pulsos",)
    with pytest.raises(ChronicleError) as error:
        await ChronicleAdmin(database[1], SERVER).grant_pass(BEA, "tarde", now=CAL.end_at)
    assert error.value.code == "chronicle_pass_closed"


async def test_cosmetics_follow_the_account(database):
    await _schedule(database)
    await _make(database, ANA, "Ana")
    service = ChronicleService(database[1], SERVER)
    await ChronicleAdmin(database[1], SERVER).grant_pass(ANA, "teste", now=WEEK1)
    await _conclude_all(database, ANA, [1], WEEK1)
    await service.claim(ANA, now=WEEK1)
    async with database[1].begin() as session:
        old = await session.scalar(select(Character.id).where(Character.telegram_id == ANA))
        await delete_character_owned_data(session, old)
    new_id = await _make(database, ANA, "Anova")
    await service.track(ANA, now=WEEK1)
    async with database[1]() as session:
        owned = (
            await session.scalars(
                select(CharacterCosmetic.cosmetic_id).where(
                    CharacterCosmetic.character_id == new_id
                )
            )
        ).all()
    assert owned == ["cos_cr01_titulo_contador_de_pulsos"]


async def _answer_feats(database) -> list[int]:
    async with database[1]() as session:
        return sorted(
            (
                await session.scalars(
                    select(Character.telegram_id)
                    .join(Achievement, Achievement.character_id == Character.id)
                    .where(Achievement.achievement_id == "feito_cr01_respondeu_ao_eco")
                )
            ).all()
        )


async def test_vote_snapshot_runoff_and_neutral_outcome(database):
    await _schedule(database)
    for actor, name in ((ANA, "Ana"), (BEA, "Bea"), (CAIO, "Caio")):
        await _make(database, actor, name)
    service = ChronicleService(database[1], SERVER)
    d50 = CAL.vote_opens_at + timedelta(hours=1)
    with pytest.raises(ChronicleError) as error:
        await service.vote(ANA, "selar", now=WEEK1)
    assert error.value.code == "chronicle_vote_closed"
    for actor in (ANA, BEA):
        await _conclude_all(database, actor, [1, 2, 3, 4], d50)
        await _record(database, actor, "cap_08_obj_01", d50)
    await _conclude_all(database, CAIO, [1, 2, 3], d50)
    await _record(database, CAIO, "cap_08_obj_01", d50)
    with pytest.raises(ChronicleError) as error:
        await service.vote(CAIO, "selar", now=d50)
    assert error.value.code == "chronicle_vote_ineligible"
    await service.vote(ANA, "estabilizar", now=d50)
    await service.vote(ANA, "selar", now=d50)  # replaces the previous choice
    view = await service.vote(BEA, "destruir", now=d50)
    assert view.vote.choice is Outcome.DESTRUIR
    # CAIO concludes a 4th chapter after the close: not in the frozen electorate.
    await _conclude_all(database, CAIO, [4], CAL.vote_closes_at + timedelta(minutes=1))
    await service.run_maintenance(now=CAL.vote_closes_at + timedelta(minutes=1))
    await service.run_maintenance(now=CAL.vote_closes_at + timedelta(minutes=2))
    async with database[1]() as session:
        electorate = (await session.scalars(select(ChronicleElector.account_id))).all()
        status = await ChronicleAdmin(database[1], SERVER).status(now=CAL.vote_closes_at)
    assert sorted(electorate) == [ANA, BEA]
    assert status.runoff_options == ("selar", "destruir")
    assert await _answer_feats(database) == [ANA, BEA]  # pr_cr01_feito_resposta
    runoff = CAL.vote_closes_at + timedelta(hours=1)
    with pytest.raises(ChronicleError):
        await service.vote(CAIO, "selar", now=runoff)
    with pytest.raises(ChronicleError):
        await service.vote(ANA, "herdeiros", now=runoff)
    await service.vote(ANA, "selar", now=runoff)
    await service.vote(BEA, "destruir", now=runoff)
    await service.run_maintenance(now=CAL.runoff_closes_at)
    status = await ChronicleAdmin(database[1], SERVER).status(now=CAL.runoff_closes_at)
    assert status.outcome == "em_espera"
    assert await _answer_feats(database) == [ANA, BEA]  # once, whatever the option
    # The epilogue is published only at T.
    assert (await service.view(ANA, now=CAL.runoff_closes_at)).outcome is None
    assert (await service.view(ANA, now=CAL.end_at)).outcome is Outcome.EM_ESPERA


async def test_main_vote_winner_without_runoff(database):
    await _schedule(database)
    await _make(database, ANA, "Ana")
    service = ChronicleService(database[1], SERVER)
    d50 = CAL.vote_opens_at + timedelta(hours=1)
    await _conclude_all(database, ANA, [1, 2, 3, 4], d50)
    await _record(database, ANA, "cap_08_obj_02", d50)
    await service.vote(ANA, "herdeiros", now=d50)
    await service.run_maintenance(now=CAL.vote_closes_at)
    status = await ChronicleAdmin(database[1], SERVER).status(now=CAL.vote_closes_at)
    assert status.outcome == "herdeiros" and status.runoff_options == ()


async def test_finalization_archives_and_soft_resets(database):
    await _schedule(database)
    ana = await _make(database, ANA, "Ana", level=30)
    bea = await _make(database, BEA, "Bea", level=30)
    async with database[1].begin() as session:
        for character_id, renome, matches, placed in ((ana, 2600, 25, 5), (bea, 0, 2, 2)):
            session.add(
                ArenaProfile(
                    character_id=character_id,
                    server_id=SERVER,
                    renome=renome,
                    mmr=1800,
                    placement_played=placed,
                    placement_wins=0,
                    matches_played=matches + 40,
                    cycle_matches=matches,
                    wins=0,
                    losses=0,
                    draws=0,
                )
            )
        guild = Guild(server_id=SERVER, name="Cinzas", tag="CNZ", created_at=BEFORE)
        session.add(guild)
        await session.flush()
        session.add(
            GuildBattleProfile(
                guild_id=guild.id,
                server_id=SERVER,
                rating=1620,
                career_real_battles=14,
                real_battles=11,
                wins=7,
                draws=1,
                losses=3,
                byes=1,
                points=22,
            )
        )
    service = ChronicleService(database[1], SERVER)
    async with database[1]() as session:
        assert not await entry_closed(session, SERVER, CAL.end_at - timedelta(seconds=1))
        assert await entry_closed(session, SERVER, CAL.end_at)
    await service.run_maintenance(now=CAL.finalization_at)
    await service.run_maintenance(now=CAL.finalization_at + timedelta(minutes=1))
    async with database[1]() as session:
        assert not await entry_closed(session, SERVER, CAL.finalization_at)
        ana_profile = await session.get(ArenaProfile, ana)
        bea_profile = await session.get(ArenaProfile, bea)
        guild_profile = await session.get(GuildBattleProfile, guild.id)
        hall = (await session.scalars(select(VigilHallEntry).order_by(VigilHallEntry.kind))).all()
    assert (ana_profile.renome, ana_profile.mmr, ana_profile.cycle_matches) == (1800, 1800, 0)
    assert (bea_profile.renome, bea_profile.cycle_matches) == (0, 0)
    assert (guild_profile.rating, guild_profile.career_real_battles) == (1620, 14)
    assert (guild_profile.points, guild_profile.real_battles, guild_profile.byes) == (0, 0, 0)
    assert [(row.kind, row.name, row.reward_tier, row.reward_eligible) for row in hall] == [
        ("arena", "Ana", "Arauto II", True),
        ("guild_battle", "Cinzas", "champion", True),
    ]
    view = await service.hall(ANA)
    assert view.own_arena.elo == "Arauto II" and view.guilds[0].points == 22
    history = await service.history(ANA)
    assert history[0].arena_elo == "Arauto II"


async def test_liquidation_delivers_pending_rights_once(database):
    await _schedule(database)
    await _make(database, ANA, "Ana")
    service = ChronicleService(database[1], SERVER)
    await _conclude_all(database, ANA, [1], WEEK1)
    rescue = CAL.finalization_at + timedelta(days=1)
    track = await service.track(ANA, now=rescue)
    assert track.can_claim and len(track.claimable) == 2
    await service.run_maintenance(now=CAL.rescue_ends_at)
    await service.run_maintenance(now=CAL.rescue_ends_at + timedelta(hours=1))
    async with database[1]() as session:
        claims = (await session.scalars(select(ChronicleClaim.via))).all()
        crowns = await session.scalar(select(Character.crowns).where(Character.telegram_id == ANA))
        count = await session.scalar(select(func.count()).select_from(ChronicleClaim))
    assert claims == ["liquidation", "liquidation"] and count == 2
    assert crowns == 250
    with pytest.raises(ChronicleError) as error:
        await service.claim(ANA, now=CAL.rescue_ends_at)
    assert error.value.code == "chronicle_claim_closed"
    assert CHAPTERS_BY_NUMBER[1].conclusion_id == "cap_01_conclusao"


async def test_vote_eligibility_survives_character_deletion(database):
    await _schedule(database)
    await _make(database, ANA, "Ana")
    d50 = CAL.vote_opens_at + timedelta(hours=1)
    await _conclude_all(database, ANA, [1, 2, 3, 4], d50)
    await _record(database, ANA, "cap_08_obj_01", d50)
    async with database[1].begin() as session:
        old = await session.scalar(select(Character.id).where(Character.telegram_id == ANA))
        await delete_character_owned_data(session, old)
    await _make(database, ANA, "Anova")
    view = await ChronicleService(database[1], SERVER).vote(ANA, "destruir", now=d50)
    assert view.vote.eligible and view.vote.choice is Outcome.DESTRUIR
    assert view.chapters[0].concluded is False  # the story is replayed, not the vote


async def _guild(session, name, tag, real_battles, points):
    guild = Guild(server_id=SERVER, name=name, tag=tag, created_at=BEFORE)
    session.add(guild)
    await session.flush()
    session.add(
        GuildBattleProfile(
            guild_id=guild.id,
            server_id=SERVER,
            rating=1500,
            career_real_battles=real_battles,
            real_battles=real_battles,
            wins=0,
            draws=0,
            losses=0,
            byes=0,
            points=points,
        )
    )
    return guild.id


async def test_finalization_grants_guild_battle_cosmetics_by_tier(database):
    await _schedule(database)
    ana = await _make(database, ANA, "Ana", level=30)
    bea = await _make(database, BEA, "Bea", level=30)
    caio = await _make(database, CAIO, "Caio", level=30)
    async with database[1].begin() as session:
        # Lodo leads on points but has 9 real battles: it ranks nothing, so
        # Cinzas is the champion and Brasas the podium among eligible Guildas.
        await _guild(session, "Lodo", "LOD", 9, 27)
        cinzas = await _guild(session, "Cinzas", "CNZ", 11, 22)
        brasas = await _guild(session, "Brasas", "BRS", 10, 12)
        for index in range(4):
            at = BEFORE + timedelta(days=index)
            regs = []
            for guild_id in (cinzas, brasas):
                reg = GuildBattleRegistration(
                    server_id=SERVER,
                    guild_id=guild_id,
                    starts_at=at,
                    status="finished",
                    created_at=at,
                    updated_at=at,
                )
                session.add(reg)
                regs.append(reg)
            await session.flush()
            battle = GuildBattle(
                server_id=SERVER,
                starts_at=at,
                registration_a_id=regs[0].id,
                registration_b_id=regs[1].id,
                guild_a_id=cinzas,
                guild_b_id=brasas,
                status="finished",
                created_at=at,
                finished_at=at,
            )
            session.add(battle)
            await session.flush()
            fight = GuildBattleFight(battle_id=battle.id, kind="front_1", status="finished")
            session.add(fight)
            await session.flush()
            fighters = [(ana, ANA, "a"), (caio, CAIO, "b")]
            if index < 3:
                fighters.append((bea, BEA, "a"))
            for key, (character_id, account, side) in enumerate(fighters):
                session.add(
                    GuildBattleFightMember(
                        fight_id=fight.id,
                        character_id=character_id,
                        account_id=account,
                        side=side,
                        actor_key=f"{side}{key}",
                    )
                )
    service = ChronicleService(database[1], SERVER)
    await service.run_maintenance(now=CAL.finalization_at)
    await service.run_maintenance(now=CAL.finalization_at + timedelta(minutes=1))
    async with database[1]() as session:
        owned = {
            (row.character_id, row.cosmetic_id)
            for row in (
                await session.scalars(
                    select(CharacterCosmetic).where(
                        CharacterCosmetic.source_achievement_id.like("guild_battle:%")
                    )
                )
            ).all()
        }
        tiers = {
            row.name: row.reward_tier
            for row in (
                await session.scalars(
                    select(VigilHallEntry).where(VigilHallEntry.kind == "guild_battle")
                )
            ).all()
        }
    assert tiers == {"Lodo": None, "Cinzas": "champion", "Brasas": "podium"}
    assert owned == {
        (ana, "cosmetic.title.gvg.campeao_da_vigilia"),
        (ana, "cosmetic.frame.gvg.estandarte_invicto"),
        (ana, "cosmetic.title.gvg.veterano_das_frentes"),
        (caio, "cosmetic.title.gvg.linha_que_nao_cedeu"),
        (caio, "cosmetic.title.gvg.veterano_das_frentes"),
    }

"""PostgreSQL integration tests for the Batalha de Guildas (GDD v1.6.0 §15, §36, §49.14)."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application.combat_configuration_guard import find_combat_configuration_blocker
from asterion.application.guild_battle import (
    GuildBattleError,
    GuildBattleFightView,
    GuildBattleResultView,
    GuildBattleService,
    individual_participations,
)
from asterion.application.guild_battle_locks import character_roster_locked
from asterion.application.guild_upkeep import _has_cooperative_commitment
from asterion.application.guilds import GuildError, GuildService
from asterion.domain.combat import withdraw_fighter
from asterion.domain.guild_battle import TURN_TTL
from asterion.infrastructure.db.models import (
    Account,
    AccountLink,
    AccountRiskFlag,
    Character,
    GameActivity,
    Guild,
    GuildBattle,
    GuildBattleFight,
    GuildBattleFightMember,
    GuildBattleProfile,
    GuildBattleRegistration,
    GuildMember,
)

D = Decimal
# Wednesday 2026-11-11, 21:00 in Sao Paulo.
START = datetime(2026, 11, 12, 0, 0, tzinfo=UTC)
REGISTER = START - timedelta(hours=2)
PAIR = START - timedelta(minutes=30)
CONFIRM = START - timedelta(minutes=20)
CLOSED = START - timedelta(minutes=10)

# Seven members per Guild: actor ids n01..n07, the first one is the Leader.
GUILDS = {"Aurora": ("AUR", 910000), "Brasas": ("BRA", 920000), "Cinzas": ("CIN", 930000)}


def _actor(guild: str, index: int) -> int:
    return GUILDS[guild][1] + index


async def _seed(database, guilds=("Aurora", "Brasas"), level: int = 30) -> None:
    async with database[1].begin() as session:
        for name in guilds:
            tag, _base = GUILDS[name]
            guild = Guild(server_id="ocaso", name=name, tag=tag)
            session.add(guild)
            await session.flush()
            for index in range(1, 8):
                actor = _actor(name, index)
                session.add(Account(telegram_id=actor))
                character = Character(
                    telegram_id=actor,
                    server_id="ocaso",
                    name=f"{tag.title()}{chr(96 + index)}",
                    race="remanescente",
                    character_class="sentinela",
                    stage="menu",
                    ruleset_version="tdo-1.0.15",
                    level=level,
                    hp=D("7"),
                    max_hp=D("100"),
                    vigor=100,
                    max_vigor=100,
                )
                session.add(character)
                await session.flush()
                when = START - timedelta(days=30)
                session.add(
                    GuildMember(
                        character_id=character.id,
                        guild_id=guild.id,
                        role="leader" if index == 1 else "member",
                        joined_at=when,
                        role_since=when,
                    )
                )


def _service(database) -> GuildBattleService:
    return GuildBattleService(database[1], "ocaso")


async def _code(awaitable) -> str:
    with pytest.raises((GuildBattleError, GuildError)) as error:
        await awaitable
    return error.value.code


async def _ids(database, guild: str) -> list:
    async with database[1]() as session:
        rows = []
        for index in range(1, 8):
            rows.append(
                await session.scalar(
                    select(Character.id).where(Character.telegram_id == _actor(guild, index))
                )
            )
        return rows


async def _register(database, service, guild: str, *, champion: int = 0):
    """Front I: members 1-2, Front II: members 3-5, reserves 6-7."""
    ids = await _ids(database, guild)
    return await service.register(
        _actor(guild, 1),
        front_1=tuple(ids[0:2]),
        front_2=tuple(ids[2:5]),
        champion=ids[champion],
        reserves=tuple(ids[5:7]),
        now=REGISTER,
    )


async def _confirm(service, guild: str, indexes, now=CONFIRM) -> None:
    for index in indexes:
        await service.confirm(_actor(guild, index), now=now)


async def _fights(database) -> dict[str, GuildBattleFight]:
    async with database[1]() as session:
        return {row.kind: row for row in (await session.scalars(select(GuildBattleFight))).all()}


async def _finish(database, service, kind: str, losing_side: str | None, now) -> list:
    """Drive one active fight to a result through the service's own settlement."""
    async with database[1].begin() as session:
        fight = await session.scalar(
            select(GuildBattleFight).where(GuildBattleFight.kind == kind).with_for_update()
        )
        members = await service._fight_members(session, fight.id)
        combat = service._decode(fight)
        if losing_side is None:
            combat = deepcopy(combat)
            for fighter in combat.fighters.values():
                fighter.hp = D(0)
            combat.result = "defeat"
            combat.version += 1
        else:
            for member in members:
                if member.side == losing_side:
                    combat = withdraw_fighter(combat, member.actor_key)
        assert combat.result
        return await service._advance(session, fight, members, combat, now)


async def _active_activities(database) -> set[int]:
    async with database[1]() as session:
        rows = (
            await session.execute(
                select(Character.telegram_id)
                .join(GameActivity, GameActivity.character_id == Character.id)
                .where(GameActivity.status == "active")
            )
        ).all()
        return {row[0] for row in rows}


@pytest.mark.asyncio
async def test_registration_rules(database):
    await _seed(database)
    service = _service(database)
    ids = await _ids(database, "Aurora")
    assert await _code(
        service.register(
            _actor("Aurora", 2), front_1=tuple(ids[0:2]), front_2=tuple(ids[2:5]),
            champion=ids[0], now=REGISTER,
        )
    ) == "no_permission"  # fmt: skip
    assert await _code(
        service.register(
            _actor("Aurora", 1), front_1=tuple(ids[0:3]), front_2=tuple(ids[3:5]),
            champion=ids[0], now=REGISTER,
        )
    ) == "invalid_roster"  # fmt: skip
    assert await _code(
        service.register(
            _actor("Aurora", 1), front_1=tuple(ids[0:2]), front_2=tuple(ids[2:5]),
            champion=ids[5], reserves=(ids[5],), now=REGISTER,
        )
    ) == "invalid_roster"  # fmt: skip
    brasas = await _ids(database, "Brasas")
    assert await _code(
        service.register(
            _actor("Aurora", 1), front_1=(ids[0], brasas[0]), front_2=tuple(ids[2:5]),
            champion=ids[0], now=REGISTER,
        )
    ) == "member_ineligible"  # fmt: skip
    async with database[1].begin() as session:
        low = await session.get(Character, ids[4])
        low.level = 29
    assert await _code(_register(database, service, "Aurora")) == "member_ineligible"
    async with database[1].begin() as session:
        (await session.get(Character, ids[4])).level = 30
    assert await _code(
        service.register(
            _actor("Aurora", 1), front_1=tuple(ids[0:2]), front_2=tuple(ids[2:5]),
            champion=ids[0], now=PAIR,
        )
    ) == "registration_closed"  # fmt: skip

    view = await _register(database, service, "Aurora")
    assert view.status == "registered" and len(view.roster) == 7
    assert [row.is_champion for row in view.roster].count(True) == 1
    # Replacing the roster keeps one registration; cancel frees the Guild.
    view = await _register(database, service, "Aurora", champion=3)
    assert next(row for row in view.roster if row.is_champion).character_id == ids[3]
    async with database[1]() as session:
        guild_id = (await session.get(GuildMember, ids[0])).guild_id
        assert await _has_cooperative_commitment(session, guild_id)
    await service.cancel_registration(_actor("Aurora", 1), now=REGISTER)
    assert await service.registration(_actor("Aurora", 1)) is None
    async with database[1]() as session:
        assert not await _has_cooperative_commitment(session, guild_id)


@pytest.mark.asyncio
async def test_tie_goes_to_champion_and_settles_ratings(database):
    await _seed(database)
    service = _service(database)
    guilds = GuildService(database[1], "ocaso")
    await _register(database, service, "Aurora", champion=2)  # Champion in Front II.
    await _register(database, service, "Brasas", champion=0)  # Champion in Front I.
    # Before pairing the roster may still change Guild.
    assert await service.run_maintenance(now=PAIR - timedelta(seconds=1)) == []
    notices = await service.run_maintenance(now=PAIR)
    assert len(notices) == 14
    view = await service.registration(_actor("Aurora", 1))
    assert view.status == "paired" and view.opponent_name == "Brasas"

    aurora = await _ids(database, "Aurora")
    async with database[1]() as session:
        assert await character_roster_locked(session, aurora[1])
        assert await character_roster_locked(session, aurora[5])  # Reserves too.
    assert await _code(guilds.leave(_actor("Aurora", 2), now=CONFIRM)) == (
        "guild_battle_roster_locked"
    )
    assert await _code(guilds.remove_member(_actor("Aurora", 1), aurora[3], now=CONFIRM)) == (
        "guild_battle_roster_locked"
    )
    async with database[1].begin() as session:
        session.add(
            AccountLink(
                account_a=min(_actor("Aurora", 3), _actor("Brasas", 1)),
                account_b=max(_actor("Aurora", 3), _actor("Brasas", 1)),
            )
        )

    # Aurora misses one Front I combatant, Brasas one Front II combatant: 1-1.
    await _confirm(service, "Aurora", (1, 3, 4, 5))
    await _confirm(service, "Brasas", (1, 2, 3, 4))
    assert await _code(service.confirm(_actor("Aurora", 2), now=CLOSED)) == "confirmation_closed"
    assert await _code(service.confirm(_actor("Aurora", 6), now=CONFIRM)) == "not_in_roster"
    async with database[1]() as session:
        blocker = await find_combat_configuration_blocker(session, aurora[0])
        assert blocker is not None and blocker.content_id == "guild_battle"

    notices = await service.run_maintenance(now=START)
    async with database[1]() as session:
        battle = await session.scalar(select(GuildBattle))
        aurora_guild = (await session.get(GuildMember, aurora[0])).guild_id
    aurora_side = "a" if battle.guild_a_id == aurora_guild else "b"
    brasas_side = "b" if aurora_side == "a" else "a"
    fights = await _fights(database)
    assert fights["front_1"].end_reason == "no_show"
    assert fights["front_1"].winner_side == brasas_side
    assert fights["front_2"].end_reason == "no_show"
    assert fights["front_2"].winner_side == aurora_side
    champion = fights["champion"]
    assert champion.status == "active"
    assert any(isinstance(item.view, GuildBattleFightView) for item in notices)
    # Only the two Champions keep the configuration lock now.
    assert await _active_activities(database) == {_actor("Aurora", 3), _actor("Brasas", 1)}
    async with database[1]() as session:
        flags = (await session.scalars(select(AccountRiskFlag))).all()
        assert [flag.activity_kind for flag in flags] == ["guild_battle"]
        assert flags[0].activity_reference == f"guild_battle:{champion.id.hex}"
        battle = await session.scalar(select(GuildBattle))
        assert battle.status == "champion" and battle.points_a == battle.points_b == 1

    async with database[1]() as session:
        champion_side = await session.scalar(
            select(GuildBattleFightMember.side).where(
                GuildBattleFightMember.character_id == aurora[2]
            )
        )
    losing = "b" if champion_side == "a" else "a"
    notices = await _finish(database, service, "champion", losing, START + timedelta(minutes=5))
    results = [item.view for item in notices if isinstance(item.view, GuildBattleResultView)]
    aurora_view = next(v for v in results if v.guild_name == "Aurora")
    assert aurora_view.outcome == "win" and aurora_view.opponent_name == "Brasas"
    assert (aurora_view.rating_before, aurora_view.rating_after) == (1500, 1524)
    assert await _active_activities(database) == set()
    async with database[1]() as session:
        profiles = {
            row.guild_id: row for row in (await session.scalars(select(GuildBattleProfile))).all()
        }
        battle = await session.scalar(select(GuildBattle))
        assert battle.status == "finished"
        winner = profiles[battle.guild_a_id if champion_side == "a" else battle.guild_b_id]
        loser = profiles[battle.guild_b_id if champion_side == "a" else battle.guild_a_id]
        assert (winner.points, winner.wins, winner.rating, winner.real_battles) == (3, 1, 1524, 1)
        assert (loser.points, loser.losses, loser.rating) == (0, 1, 1476)
        statuses = set((await session.scalars(select(GuildBattleRegistration.status))).all())
        assert statuses == {"finished"}
        assert not await character_roster_locked(session, aurora[1])
        assert await individual_participations(session, aurora[2]) == 1
        assert await individual_participations(session, aurora[1]) == 0
    standings = await service.standings()
    assert [row.guild_name for row in standings] == ["Aurora", "Brasas"]
    assert not standings[0].reward_eligible
    # The roster is free again.
    await guilds.leave(_actor("Aurora", 2), now=START + timedelta(minutes=6))


@pytest.mark.asyncio
async def test_real_fronts_with_afk_withdrawal_and_draw(database):
    await _seed(database)
    service = _service(database)
    await _register(database, service, "Aurora", champion=0)
    await _register(database, service, "Brasas", champion=0)
    await service.run_maintenance(now=PAIR)
    await _confirm(service, "Aurora", range(1, 6))
    await _confirm(service, "Brasas", range(1, 6))
    await service.run_maintenance(now=START)
    fights = await _fights(database)
    assert fights["front_1"].status == fights["front_2"].status == "active"
    assert "champion" not in fights
    async with database[1]() as session:
        sizes = {
            kind: len(
                (
                    await session.scalars(
                        select(GuildBattleFightMember).where(
                            GuildBattleFightMember.fight_id == fight.id
                        )
                    )
                ).all()
            )
            for kind, fight in fights.items()
        }
    assert sizes == {"front_1": 4, "front_2": 6}

    # One more timeout for a player who already had one: withdrawn, team fights on.
    front = fights["front_2"]
    async with database[1].begin() as session:
        combat = service._decode(front)
        from asterion.domain.combat import active_player_key

        key = active_player_key(combat)
        member = await session.scalar(
            select(GuildBattleFightMember).where(
                GuildBattleFightMember.fight_id == front.id,
                GuildBattleFightMember.actor_key == key,
            )
        )
        member.consecutive_timeouts = 1
        member.total_timeouts = 1
    await service.run_maintenance(now=front.deadline_at)
    async with database[1]() as session:
        member = await session.scalar(
            select(GuildBattleFightMember).where(
                GuildBattleFightMember.fight_id == front.id,
                GuildBattleFightMember.actor_key == key,
            )
        )
        front = await session.get(GuildBattleFight, front.id)
        assert member.withdrawn_at is not None
        assert front.status == "active"
        assert service._decode(front).fighters[key].hp == 0
        assert front.deadline_at == member.withdrawn_at + TURN_TTL

    later = START + timedelta(minutes=3)
    await _finish(database, service, "front_1", "b", later)
    active = await _active_activities(database)
    # Front I ended: its non-Champion members are free, both Champions stay locked.
    assert _actor("Aurora", 2) not in active and _actor("Brasas", 2) not in active
    assert {_actor("Aurora", 1), _actor("Brasas", 1)} <= active
    notices = await _finish(database, service, "front_2", None, later)
    async with database[1]() as session:
        battle = await session.scalar(select(GuildBattle))
        assert battle.status == "finished"
        assert (battle.points_a, battle.points_b) == (D("1.5"), D("0.5"))
        assert battle.winner_side == "a"
    assert "champion" not in await _fights(database)
    assert any(isinstance(item.view, GuildBattleResultView) for item in notices)
    assert await _active_activities(database) == set()


@pytest.mark.asyncio
async def test_reserve_substitution_and_champion_draw(database):
    await _seed(database)
    service = _service(database)
    await _register(database, service, "Aurora", champion=0)
    await _register(database, service, "Brasas", champion=0)
    await service.run_maintenance(now=PAIR)
    aurora = await _ids(database, "Aurora")
    await _confirm(service, "Aurora", (2, 3, 4, 5))
    # The unconfirmed Champion is replaced by a reserve, who takes the Champion role.
    view = await service.substitute(_actor("Aurora", 1), aurora[0], aurora[5], now=CONFIRM)
    champion = next(row for row in view.roster if row.is_champion)
    assert champion.character_id == aurora[5] and champion.slot == "front_1"
    assert (
        await _code(service.substitute(_actor("Aurora", 1), aurora[1], aurora[6], now=CONFIRM))
        == "invalid_substitution"
    )  # Already confirmed.
    assert (
        await _code(service.substitute(_actor("Aurora", 1), aurora[2], aurora[6], now=CLOSED))
        == "confirmation_closed"
    )
    assert await _code(service.confirm(_actor("Aurora", 1), now=CONFIRM)) == "not_in_roster"
    await _confirm(service, "Aurora", (6,))
    await _confirm(service, "Brasas", range(1, 6))
    await service.run_maintenance(now=START)
    later = START + timedelta(minutes=2)
    await _finish(database, service, "front_1", "b", later)
    await _finish(database, service, "front_2", "a", later)
    assert (await _fights(database))["champion"].status == "active"
    # Simultaneous death of the Champions: the whole battle is a draw.
    await _finish(database, service, "champion", None, later)
    async with database[1]() as session:
        battle = await session.scalar(select(GuildBattle))
        assert battle.status == "finished" and battle.winner_side is None
        profiles = (await session.scalars(select(GuildBattleProfile))).all()
        assert {(p.points, p.draws, p.rating) for p in profiles} == {(1, 1, 1500)}
        assert await individual_participations(session, aurora[5]) == 1


@pytest.mark.asyncio
async def test_odd_count_bye_and_dissolution_waits_for_battle(database):
    await _seed(database, guilds=("Aurora", "Brasas", "Cinzas"))
    service = _service(database)
    for name in ("Aurora", "Brasas", "Cinzas"):
        await _register(database, service, name)
    async with database[1].begin() as session:
        guild = await session.scalar(select(Guild).where(Guild.name == "Aurora"))
        guild.dissolution_requested_at = REGISTER
        guild.dissolution_due_at = REGISTER
        guild_id = guild.id
        # The highest rating is never the bye, so Aurora is always paired.
        session.add(GuildBattleProfile(guild_id=guild_id, server_id="ocaso", rating=1600))
    await service.run_maintenance(now=PAIR)
    async with database[1]() as session:
        registrations = (await session.scalars(select(GuildBattleRegistration))).all()
        assert sorted(row.status for row in registrations) == ["bye", "paired", "paired"]
        bye = next(row for row in registrations if row.status == "bye")
        profile = await session.get(GuildBattleProfile, bye.guild_id)
        assert (profile.byes, profile.real_battles, profile.points, profile.rating) == (
            1, 0, 0, 1500,
        )  # fmt: skip
        paired = {row.guild_id for row in registrations if row.status == "paired"}
    # A Guild in a Batalha cannot finish its dissolution (§30.3).
    assert guild_id in paired
    async with database[1]() as session:
        assert await _has_cooperative_commitment(session, guild_id)
    await GuildService(database[1], "ocaso").run_maintenance(now=PAIR + timedelta(minutes=1))
    async with database[1]() as session:
        assert (await session.get(Guild, guild_id)).status == "active"
    # Nobody confirms: both Fronts are 0/0, the Champions are absent, the battle is a draw.
    await service.run_maintenance(now=START)
    async with database[1]() as session:
        battle = await session.scalar(select(GuildBattle))
        assert battle.status == "finished" and battle.winner_side is None
        fights = (await session.scalars(select(GuildBattleFight))).all()
        assert sorted(row.kind for row in fights) == ["champion", "front_1", "front_2"]
        assert all(row.absent_a and row.absent_b for row in fights)
        assert not await _has_cooperative_commitment(session, guild_id)


@pytest.mark.asyncio
async def test_player_actions_follow_turn_and_version(database):
    from asterion.domain.combat import active_player_key

    await _seed(database)
    service = _service(database)
    await _register(database, service, "Aurora")
    await _register(database, service, "Brasas")
    await service.run_maintenance(now=PAIR)
    await _confirm(service, "Aurora", range(1, 6))
    await _confirm(service, "Brasas", range(1, 6))
    await service.run_maintenance(now=START)
    front = (await _fights(database))["front_1"]
    async with database[1]() as session:
        members = {
            row.actor_key: row.account_id
            for row in (
                await session.scalars(
                    select(GuildBattleFightMember).where(
                        GuildBattleFightMember.fight_id == front.id
                    )
                )
            ).all()
        }
    key = active_player_key(service._decode(front))
    current = members[key]
    other = next(account for k, account in members.items() if k != key)
    view = await service.foreground(current, now=START)
    assert isinstance(view, GuildBattleFightView) and view.my_turn and view.kind == "front_1"
    assert not (await service.foreground(other, now=START)).my_turn
    version = view.battle.combat.version
    await service.action(other, front.id, version, 0, "d0", now=START)
    await service.action(current, front.id, version + 9, 0, "d0", now=START)
    assert (await _fights(database))["front_1"].state_version == version
    outcome = await service.action(current, front.id, version, 0, "d0", now=START)
    after = (await _fights(database))["front_1"]
    assert after.state_version > version
    assert active_player_key(service._decode(after)) != key
    assert any(item.telegram_id != current for item in outcome.notices)
    assert (
        await _code(service.action(_actor("Aurora", 6), front.id, version, 0, "d0", now=START))
        == "not_found"
    )

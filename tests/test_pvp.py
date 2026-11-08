"""PostgreSQL integration tests for Duelo and Arena da Vigilia (GDD v1.6.0 14, 39, 49.14)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.application.pvp import (
    ConfirmationView,
    DuelInviteView,
    PvpCombatView,
    PvpError,
    PvpHubView,
    PvpMessageView,
    PvpResultView,
    PvpService,
    QueueView,
)
from asterion.domain.arena import TURN_TTL
from asterion.domain.combat import active_player_key
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    AccountLink,
    AccountRiskFlag,
    ArenaProfile,
    ArenaQueueEntry,
    Character,
    GameActivity,
    PvpMatch,
    PvpMatchMember,
)

# Monday 2026-11-09, 12:30 in Sao Paulo: the first Arena window is open.
NOW = datetime(2026, 11, 9, 15, 30, tzinfo=UTC)
CLOSED = datetime(2026, 11, 9, 16, 0, tzinfo=UTC)
A, B, C, D = 860001, 860002, 860003, 860004
LOW = 860005


async def _seed(database) -> None:
    async with database[1].begin() as session:
        for actor, name, level in (
            (A, "Alfa", 30),
            (B, "Beta", 30),
            (C, "Gama", 31),
            (D, "Delta", 60),
            (LOW, "Novato", 9),
        ):
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    telegram_id=actor,
                    server_id="ocaso",
                    name=name,
                    race="remanescente",
                    character_class="sentinela",
                    stage="menu",
                    ruleset_version="tdo-1.0.15",
                    level=level,
                    hp=Decimal("7"),
                    max_hp=Decimal("100"),
                    vigor=100,
                    max_vigor=100,
                )
            )


def _service(database) -> PvpService:
    return PvpService(database[1], "ocaso")


async def _code(awaitable) -> str:
    with pytest.raises(PvpError) as error:
        await awaitable
    return error.value.code


async def _char(session, actor: int) -> Character:
    return await session.scalar(select(Character).where(Character.telegram_id == actor))


async def _paired(service, first=A, second=B, now=NOW) -> ConfirmationView:
    await service.enter_queue(first, now=now)
    return (await service.enter_queue(second, now=now)).view


async def _started(service, first=A, second=B, now=NOW):
    confirmation = await _paired(service, first, second, now)
    await service.accept(first, confirmation.match_id, now=now)
    return confirmation.match_id, await service.accept(second, confirmation.match_id, now=now)


async def _duel(service, first=A, second=B, now=NOW):
    preview = await service.duel_preview(first, "Beta" if second == B else "Gama")
    invite = await service.challenge(first, preview.character_id, now=now)
    return invite.view.match_id, await service.accept(second, invite.view.match_id, now=now)


async def _set_round(database, match_id, round_number: int) -> None:
    async with database[1].begin() as session:
        match = await session.get(PvpMatch, match_id)
        combat = decode(
            match.combat_snapshot, match.combat_id, match.ruleset_version, match.state_version
        )
        combat.round = round_number
        match.combat_snapshot = encode(combat)


async def _current_actor(database, match_id) -> str | None:
    async with database[1]() as session:
        match = await session.get(PvpMatch, match_id)
        return active_player_key(
            decode(
                match.combat_snapshot, match.combat_id, match.ruleset_version, match.state_version
            )
        )


async def _accounts(database, match_id, actor_key: str) -> tuple[int, int]:
    """(account holding the turn, the other account)."""
    async with database[1]() as session:
        rows = (
            await session.scalars(select(PvpMatchMember).where(PvpMatchMember.match_id == match_id))
        ).all()
    current = next(row.account_id for row in rows if row.actor_key == actor_key)
    return current, next(row.account_id for row in rows if row.account_id != current)


async def _profile(database, actor) -> ArenaProfile:
    async with database[1]() as session:
        character = await _char(session, actor)
        return await session.get(ArenaProfile, character.id)


async def _deadline(database, match_id) -> datetime:
    async with database[1]() as session:
        return (await session.get(PvpMatch, match_id)).deadline_at


@pytest.mark.asyncio
async def test_arena_requires_level_and_an_open_window(database):
    await _seed(database)
    service = _service(database)
    assert await _code(service.enter_queue(LOW, now=NOW)) == "arena_level"
    assert await _code(service.enter_queue(A, now=CLOSED)) == "window_closed"


@pytest.mark.asyncio
async def test_queue_locks_configuration_until_it_is_left(database):
    await _seed(database)
    service = _service(database)
    view = (await service.enter_queue(A, now=NOW)).view
    assert isinstance(view, QueueView)
    async with database[1].begin() as session:
        character = await _char(session, A)
        with pytest.raises(CombatConfigurationLocked):
            await lock_for_combat_configuration_mutation(session, character.id)
    assert isinstance(await service.foreground(A, now=NOW), QueueView)
    assert isinstance((await service.leave_queue(A, now=NOW)).view, PvpHubView)
    assert await service.foreground(A, now=NOW) is None
    async with database[1].begin() as session:
        character = await _char(session, A)
        assert await lock_for_combat_configuration_mutation(session, character.id) is not None


@pytest.mark.asyncio
async def test_confirmation_hides_the_opponent_and_match_starts_clean(database):
    await _seed(database)
    service = _service(database)
    confirmation = await _paired(service)
    assert isinstance(confirmation, ConfirmationView)
    assert not hasattr(confirmation, "opponent_name")
    first = await service.accept(A, confirmation.match_id, now=NOW)
    assert first.view.accepted is True
    assert first.notices == ()
    started = await service.accept(B, confirmation.match_id, now=NOW)
    assert isinstance(started.view, PvpCombatView)
    assert [notice.telegram_id for notice in started.notices] == [A]
    combat = started.view.battle.combat
    assert all(fighter.hp == fighter.stats.hp for fighter in combat.fighters.values())
    assert combat.pvp_mode is True and combat.external_consumables_allowed is False
    async with database[1]() as session:
        assert (await _char(session, A)).hp == Decimal("7")
    assert isinstance(await service.foreground(A, now=NOW), PvpCombatView)
    assert isinstance(await service.foreground(B, now=NOW), PvpCombatView)


@pytest.mark.asyncio
async def test_refusal_is_a_dodge_and_the_other_player_returns_to_the_queue(database):
    await _seed(database)
    service = _service(database)
    confirmation = await _paired(service)
    outcome = await service.decline(A, confirmation.match_id, now=NOW)
    assert isinstance(outcome.view, PvpMessageView)
    assert outcome.view.until is None
    assert await service.foreground(A, now=NOW) is None
    assert isinstance(await service.foreground(B, now=NOW), QueueView)
    assert [notice.view.code for notice in outcome.notices] == ["requeued"]

    await service.enter_queue(A, now=NOW)
    second = await service.foreground(A, now=NOW)
    assert isinstance(second, ConfirmationView)
    blocked = await service.decline(A, second.match_id, now=NOW)
    assert blocked.view.until == NOW + timedelta(minutes=5)
    assert await _code(service.enter_queue(A, now=NOW)) == "queue_blocked"
    await service.enter_queue(A, now=NOW + timedelta(minutes=5))


@pytest.mark.asyncio
async def test_no_show_is_charged_only_to_who_did_not_accept(database):
    await _seed(database)
    service = _service(database)
    confirmation = await _paired(service)
    await service.accept(A, confirmation.match_id, now=NOW)
    notices = await service.run_maintenance(now=NOW + timedelta(seconds=45))
    codes = {notice.telegram_id: notice.view.code for notice in notices}
    assert codes == {A: "requeued", B: "dodged"}
    assert isinstance(await service.foreground(A, now=NOW), QueueView)
    assert await service.foreground(B, now=NOW) is None


@pytest.mark.asyncio
async def test_window_close_releases_the_queue_but_not_formed_matches(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    await service.enter_queue(C, now=NOW)
    notices = await service.run_maintenance(now=CLOSED)
    assert [(item.telegram_id, item.view.code) for item in notices] == [(C, "queue_released")]
    assert await service.foreground(C, now=CLOSED) is None
    assert (await _profile(database, C)).queue_blocked_until is None
    assert isinstance(await service.foreground(A, now=CLOSED), PvpCombatView)
    assert match_id is not None


@pytest.mark.asyncio
async def test_two_consecutive_timeouts_are_afk_and_settle_placement(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    actor = await _current_actor(database, match_id)
    afk, other = await _accounts(database, match_id, actor)
    deadline = await _deadline(database, match_id)

    await service.run_maintenance(now=deadline)
    assert await _current_actor(database, match_id) != actor
    view = await service.foreground(other, now=deadline)
    await service.action(other, match_id, view.battle.combat.version, 0, "d0", now=deadline)
    assert await _current_actor(database, match_id) == actor

    deadline = await _deadline(database, match_id)
    notices = await service.run_maintenance(now=deadline)
    results = {item.telegram_id: item.view for item in notices}
    assert isinstance(results[other], PvpResultView)
    assert results[other].outcome == "win" and results[other].reason == "afk"
    assert results[afk].outcome == "loss"
    assert results[other].placement_played == 1
    assert (await _profile(database, other)).placement_wins == 1
    assert await service.foreground(afk, now=deadline) is None
    assert await service.foreground(other, now=deadline) is None


@pytest.mark.asyncio
async def test_valid_action_resets_consecutive_timeouts_but_third_total_is_afk(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    actor = await _current_actor(database, match_id)
    afk, other = await _accounts(database, match_id, actor)
    now = NOW

    async def act_for(character):
        view = await service.foreground(character, now=now)
        await service.action(character, match_id, view.battle.combat.version, 0, "d0", now=now)

    for index in range(3):
        now = await _deadline(database, match_id)
        notices = await service.run_maintenance(now=now)
        if index == 2:
            assert notices[0].view.reason == "afk"
            break
        await act_for(other)
        await act_for(afk)
        await act_for(other)


@pytest.mark.asyncio
async def test_recognized_downtime_never_charges_a_timeout(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    actor = await _current_actor(database, match_id)
    deadline = await _deadline(database, match_id)
    late = deadline + timedelta(minutes=10)
    assert await service.run_maintenance(now=late) == []
    assert await _current_actor(database, match_id) == actor
    assert await _deadline(database, match_id) == late + TURN_TTL


@pytest.mark.asyncio
async def test_surrender_only_from_round_five(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    assert await _code(service.surrender(A, match_id, now=NOW)) == "surrender_round"
    await _set_round(database, match_id, 5)
    outcome = await service.surrender(A, match_id, now=NOW)
    assert outcome.view.outcome == "loss" and outcome.view.reason == "surrender"
    assert outcome.notices[0].view.outcome == "win"


@pytest.mark.asyncio
async def test_placement_finishes_with_the_table_value(database):
    await _seed(database)
    service = _service(database)
    async with database[1].begin() as session:
        for actor in (A, B):
            character = await _char(session, actor)
            session.add(
                ArenaProfile(
                    character_id=character.id,
                    server_id="ocaso",
                    renome=0,
                    mmr=1500,
                    placement_played=4,
                    placement_wins=2,
                    matches_played=4,
                    wins=2,
                    losses=2,
                    draws=0,
                )
            )
    match_id, _ = await _started(service)
    await _set_round(database, match_id, 5)
    await service.surrender(B, match_id, now=NOW)
    winner = await _profile(database, A)
    loser = await _profile(database, B)
    assert (winner.renome, loser.renome) == (1000, 800)
    assert (winner.mmr, loser.mmr) == (1524, 1476)


@pytest.mark.asyncio
async def test_placed_player_uses_the_table_value_of_a_placement_opponent(database):
    await _seed(database)
    service = _service(database)
    async with database[1].begin() as session:
        character = await _char(session, A)
        session.add(
            ArenaProfile(
                character_id=character.id,
                server_id="ocaso",
                renome=400,
                mmr=1500,
                placement_played=5,
                placement_wins=0,
                matches_played=25,
                wins=0,
                losses=25,
                draws=0,
            )
        )
    match_id, _ = await _started(service)
    await _set_round(database, match_id, 5)
    outcome = await service.surrender(B, match_id, now=NOW)
    # Beta has 0 wins in Placement, so it counts as 400: an even match.
    assert (await _profile(database, A)).renome == 420
    assert outcome.notices[0].telegram_id == A
    assert outcome.notices[0].view.renome_after == 420
    assert (await _profile(database, B)).renome == 0


@pytest.mark.asyncio
async def test_recent_rematch_only_repeats_without_another_option(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    await _set_round(database, match_id, 5)
    await service.surrender(A, match_id, now=NOW)
    later = NOW + timedelta(minutes=1)
    await service.enter_queue(A, now=later)
    await service.enter_queue(C, now=later)
    assert isinstance(await service.foreground(A, now=later), ConfirmationView)
    await service.decline(C, (await service.foreground(C, now=later)).match_id, now=later)
    view = (await service.enter_queue(B, now=later)).view
    assert isinstance(view, ConfirmationView)


@pytest.mark.asyncio
async def test_level_gap_above_fifteen_never_pairs(database):
    await _seed(database)
    service = _service(database)
    await service.enter_queue(A, now=NOW)
    view = (await service.enter_queue(D, now=NOW)).view
    assert isinstance(view, QueueView)
    await service.run_maintenance(now=NOW + timedelta(seconds=300))
    assert isinstance(await service.foreground(D, now=NOW), QueueView)


@pytest.mark.asyncio
async def test_decay_applies_once_per_monday(database):
    await _seed(database)
    service = _service(database)
    boundary = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)
    async with database[1].begin() as session:
        for actor, renome, last in (
            (A, 2600, boundary - timedelta(days=7)),
            (B, 2600, boundary - timedelta(days=6)),
            (C, 2399, boundary - timedelta(days=30)),
        ):
            character = await _char(session, actor)
            session.add(
                ArenaProfile(
                    character_id=character.id,
                    server_id="ocaso",
                    renome=renome,
                    mmr=1500,
                    placement_played=5,
                    placement_wins=5,
                    matches_played=30,
                    wins=30,
                    losses=0,
                    draws=0,
                    last_match_at=last,
                )
            )
    await service.run_maintenance(now=boundary)
    await service.run_maintenance(now=boundary + timedelta(minutes=1))
    assert (await _profile(database, A)).renome == 2550
    assert (await _profile(database, B)).renome == 2600
    assert (await _profile(database, C)).renome == 2399
    await service.run_maintenance(now=boundary + timedelta(days=7))
    assert (await _profile(database, A)).renome == 2500


@pytest.mark.asyncio
async def test_ranking_lists_only_placed_characters(database):
    await _seed(database)
    service = _service(database)
    async with database[1].begin() as session:
        for actor, renome, played in ((A, 1500, 5), (B, 3100, 5), (C, 900, 3)):
            character = await _char(session, actor)
            session.add(
                ArenaProfile(
                    character_id=character.id,
                    server_id="ocaso",
                    renome=renome,
                    mmr=1500,
                    placement_played=played,
                    placement_wins=0,
                    matches_played=played,
                    wins=0,
                    losses=played,
                    draws=0,
                )
            )
    view = await service.ranking(A)
    assert [(row.position, row.name, row.elo) for row in view.highlights] == [
        (1, "Beta", "Regente"),
        (2, "Alfa", "Forjado II"),
    ]
    assert view.own.position == 2
    assert (await service.ranking(C)).own is None


@pytest.mark.asyncio
async def test_duel_shows_level_and_locks_only_after_both_accept(database):
    await _seed(database)
    service = _service(database)
    preview = await service.duel_preview(A, "beta")
    assert (preview.name, preview.level, preview.character_class) == ("Beta", 30, "sentinela")
    invite = await service.challenge(A, preview.character_id, now=NOW)
    assert isinstance(invite.view, DuelInviteView)
    assert invite.notices[0].telegram_id == B and invite.notices[0].view.incoming is True
    async with database[1].begin() as session:
        character = await _char(session, A)
        assert await lock_for_combat_configuration_mutation(session, character.id) is not None
    assert await service.foreground(A, now=NOW) is None
    assert await _code(service.accept(A, invite.view.match_id, now=NOW)) == "expired"
    started = await service.accept(B, invite.view.match_id, now=NOW)
    assert isinstance(started.view, PvpCombatView) and started.view.kind == "duel"
    async with database[1].begin() as session:
        character = await _char(session, A)
        with pytest.raises(CombatConfigurationLocked):
            await lock_for_combat_configuration_mutation(session, character.id)


@pytest.mark.asyncio
async def test_duel_gates(database):
    await _seed(database)
    service = _service(database)
    assert await _code(service.duel_preview(LOW, "Beta")) == "duel_level"
    assert await _code(service.duel_preview(A, "Novato")) == "opponent_level"
    assert await _code(service.duel_preview(A, "Alfa")) == "duel_self"
    assert await _code(service.duel_preview(A, "Ninguem")) == "target_not_found"


@pytest.mark.asyncio
async def test_duel_allows_extreme_level_gap_and_gives_no_rating(database):
    await _seed(database)
    service = _service(database)
    preview = await service.duel_preview(A, "Delta")
    invite = await service.challenge(A, preview.character_id, now=NOW)
    match_id = invite.view.match_id
    await service.accept(D, match_id, now=NOW)
    await _set_round(database, match_id, 5)
    outcome = await service.surrender(A, match_id, now=NOW)
    assert outcome.view.kind == "duel" and outcome.view.renome_after is None
    assert await _profile(database, A) is None


@pytest.mark.asyncio
async def test_duel_invite_expires_and_can_be_refused(database):
    await _seed(database)
    service = _service(database)
    preview = await service.duel_preview(A, "Beta")
    invite = await service.challenge(A, preview.character_id, now=NOW)
    assert await _code(service.challenge(A, preview.character_id, now=NOW)) == "invite_open"
    notices = await service.run_maintenance(now=NOW + timedelta(seconds=45))
    assert {item.view.code for item in notices} == {"duel_expired"}
    assert await _code(service.accept(B, invite.view.match_id, now=NOW)) == "expired"

    second = await service.challenge(A, preview.character_id, now=NOW)
    refused = await service.decline(B, second.view.match_id, now=NOW)
    assert refused.notices[0].telegram_id == A
    assert refused.notices[0].view.code == "duel_declined"


@pytest.mark.asyncio
async def test_busy_player_cannot_duel(database):
    await _seed(database)
    service = _service(database)
    await service.enter_queue(B, now=NOW)
    preview = await service.duel_preview(A, "Beta")
    assert await _code(service.challenge(A, preview.character_id, now=NOW)) == "opponent_busy"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["arena", "duel"])
async def test_linked_accounts_are_flagged_and_never_blocked(database, mode):
    await _seed(database)
    service = _service(database)
    async with database[1].begin() as session:
        session.add(AccountLink(account_a=A, account_b=B))
    match_id, started = await (_started(service) if mode == "arena" else _duel(service))
    assert isinstance(started.view, PvpCombatView)
    async with database[1]() as session:
        flags = (await session.scalars(select(AccountRiskFlag))).all()
    assert [flag.activity_kind for flag in flags] == ["arena_match" if mode == "arena" else "duel"]
    assert flags[0].activity_reference == f"pvp:{match_id.hex}"


@pytest.mark.asyncio
async def test_stale_action_changes_nothing(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    actor = await _current_actor(database, match_id)
    current, other = await _accounts(database, match_id, actor)
    view = await service.foreground(current, now=NOW)
    version = view.battle.combat.version
    await service.action(other, match_id, version, 0, "d0", now=NOW)
    assert await _current_actor(database, match_id) == actor
    await service.action(current, match_id, version + 9, 0, "d0", now=NOW)
    assert await _current_actor(database, match_id) == actor


@pytest.mark.asyncio
async def test_duplicate_callback_resolves_only_one_action(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    actor = await _current_actor(database, match_id)
    current, _other = await _accounts(database, match_id, actor)
    view = await service.foreground(current, now=NOW)
    version = view.battle.combat.version
    await asyncio.gather(
        *(service.action(current, match_id, version, 0, "d0", now=NOW) for _ in range(4))
    )
    async with database[1]() as session:
        match = await session.get(PvpMatch, match_id)
    assert match.state_version == version + 1


@pytest.mark.asyncio
async def test_action_and_timeout_compete_atomically(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    actor = await _current_actor(database, match_id)
    current, _other = await _accounts(database, match_id, actor)
    view = await service.foreground(current, now=NOW)
    version = view.battle.combat.version
    deadline = await _deadline(database, match_id)
    await asyncio.gather(
        service.action(current, match_id, version, 0, "d0", now=deadline),
        service.run_maintenance(now=deadline),
    )
    async with database[1]() as session:
        match = await session.get(PvpMatch, match_id)
    assert match.state_version == version + 1


@pytest.mark.asyncio
async def test_simultaneous_entries_form_a_single_match(database):
    await _seed(database)
    service = _service(database)
    await asyncio.gather(
        *(service.enter_queue(actor, now=NOW) for actor in (A, B, C)),
    )
    async with database[1]() as session:
        matches = await session.scalar(select(func.count()).select_from(PvpMatch))
        waiting = await session.scalar(
            select(func.count())
            .select_from(ArenaQueueEntry)
            .where(ArenaQueueEntry.status == "waiting")
        )
    assert (matches, waiting) == (1, 1)


@pytest.mark.asyncio
async def test_double_accept_and_finished_match_release_locks(database):
    await _seed(database)
    service = _service(database)
    confirmation = await _paired(service)
    await asyncio.gather(
        service.accept(A, confirmation.match_id, now=NOW),
        service.accept(B, confirmation.match_id, now=NOW),
    )
    await _set_round(database, confirmation.match_id, 5)
    await service.surrender(A, confirmation.match_id, now=NOW)
    async with database[1]() as session:
        active = await session.scalar(
            select(func.count()).select_from(GameActivity).where(GameActivity.status == "active")
        )
    assert active == 0
    later = NOW + timedelta(minutes=1)
    assert isinstance((await service.enter_queue(A, now=later)).view, QueueView)


@pytest.mark.asyncio
async def test_deleting_a_character_after_matches_keeps_the_rest(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    await _set_round(database, match_id, 5)
    await service.surrender(A, match_id, now=NOW)
    async with database[1].begin() as session:
        character = await _char(session, A)
        await delete_character_owned_data(session, character.id)
    assert await _profile(database, B) is not None


@pytest.mark.asyncio
async def test_a_real_knockout_settles_the_match_for_the_survivor(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    actor = await _current_actor(database, match_id)
    current, other = await _accounts(database, match_id, actor)
    async with database[1].begin() as session:
        match = await session.get(PvpMatch, match_id)
        combat = decode(
            match.combat_snapshot, match.combat_id, match.ruleset_version, match.state_version
        )
        rival_key = "b1" if actor == "a1" else "a1"
        combat.fighters[rival_key].hp = Decimal(1)
        match.combat_snapshot = encode(combat)
    view = await service.foreground(current, now=NOW)
    outcome = await service.action(current, match_id, view.battle.combat.version, 0, "d0", now=NOW)
    assert isinstance(outcome.view, PvpResultView)
    assert outcome.view.outcome == "win" and outcome.view.reason == "combat"
    assert outcome.notices[0].telegram_id == other
    assert outcome.notices[0].view.outcome == "loss"
    assert await service.foreground(current, now=NOW) is None
    async with database[1]() as session:
        # The world HP was never touched by the match (14.3).
        assert (await _char(session, current)).hp == Decimal("7")
        assert (await _char(session, other)).hp == Decimal("7")


@pytest.mark.asyncio
async def test_simultaneous_death_is_a_draw_and_processes_mmr(database):
    await _seed(database)
    service = _service(database)
    match_id, _ = await _started(service)
    async with database[1].begin() as session:
        match = await session.get(PvpMatch, match_id)
        members = (
            await session.scalars(select(PvpMatchMember).where(PvpMatchMember.match_id == match_id))
        ).all()
        by_id = {
            row.id: row
            for row in (
                await session.scalars(select(Character).where(Character.telegram_id.in_((A, B))))
            ).all()
        }
        outcome = await service._settle(session, match, members, by_id, None, "combat", NOW)
    assert outcome.view.outcome == "draw"
    first, second = await _profile(database, A), await _profile(database, B)
    assert (first.draws, second.draws) == (1, 1)
    assert (first.mmr, second.mmr) == (1500, 1500)
    assert (first.placement_played, first.placement_wins) == (1, 0)

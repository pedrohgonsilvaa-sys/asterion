"""PostgreSQL integration tests for the Juramento (GDD v1.6.0 §22.1, §49.15)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update

from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.application.groups import GroupService
from asterion.application.guild_upkeep import _has_cooperative_commitment
from asterion.application.oaths import (
    OATH_ACTIVITY_TYPE,
    OathAttemptResultView,
    OathCycleResultView,
    OathError,
    OathHubView,
    OathService,
    OathTurnNotice,
)
from asterion.application.prologue import CombatView
from asterion.bot.combat_ui import class_trial_action_ids
from asterion.bot.oath_ui import render_oath
from asterion.domain.combat import active_player_key
from asterion.domain.oaths import OathEncounter, OathTrialDefinition, encounter_stats, reward_bundle
from asterion.domain.road import Creature
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    Character,
    GameActivity,
    Guild,
    GuildMember,
    GuildTreasuryEntry,
    OathAttempt,
    OathAttemptMember,
    OathCycle,
    OathGuildProgress,
    OathMember,
    OathMilestone,
)

D = Decimal
# Friday 2026-11-13, 18:00 in Sao Paulo.
OPENING = datetime(2026, 11, 13, 21, 0, tzinfo=UTC)
PLAYING = OPENING + timedelta(hours=1)
DEADLINE = OPENING + timedelta(hours=48)
GRACE_END = DEADLINE + timedelta(minutes=30)
A, B, C = 880001, 880002, 880003


def _creature(category: str) -> Creature:
    return Creature(
        f"teste_{category}",
        f"Teste {category}",
        category,
        "balanced",
        1,
        60,
        0,
        ("golpe",),
        (("golpe", "Golpe Pesado", D("1.00"), 0, D(0), 0),),
    )


TRIAL = OathTrialDefinition(
    "provacao_teste",
    "Provação de Teste",
    (
        OathEncounter(_creature("elite"), "Primeiro."),
        OathEncounter(_creature("elite"), "Segundo."),
        OathEncounter(_creature("boss"), "Terceiro."),
    ),
    "O Juramento se cumpre.",
)


async def _seed(database, level: int = 30) -> None:
    async with database[1].begin() as session:
        rows = {}
        for actor, name in ((A, "Alfa"), (B, "Beta"), (C, "Gama")):
            session.add(Account(telegram_id=actor))
            rows[actor] = Character(
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
            session.add(rows[actor])
        first = Guild(server_id="ocaso", name="Aurora", tag="AUR")
        second = Guild(server_id="ocaso", name="Brasa", tag="BRA")
        session.add_all((first, second))
        await session.flush()
        when = OPENING - timedelta(days=30)
        for actor, guild, role in (
            (A, first, "leader"),
            (B, first, "member"),
            (C, second, "leader"),
        ):
            session.add(
                GuildMember(
                    character_id=rows[actor].id,
                    guild_id=guild.id,
                    role=role,
                    joined_at=when,
                    role_since=when,
                )
            )


def _service(database, notifier=None, catalog=(TRIAL,)) -> OathService:
    return OathService(database[1], "ocaso", catalog, notifier)


async def _code(awaitable) -> str:
    with pytest.raises(OathError) as error:
        await awaitable
    return error.value.code


async def _char(session, actor: int) -> Character:
    return await session.scalar(select(Character).where(Character.telegram_id == actor))


async def _attempt(database) -> OathAttempt:
    async with database[1]() as session:
        return await session.scalar(select(OathAttempt).order_by(OathAttempt.started_at.desc()))


async def _binding(database, actor: int) -> OathMember | None:
    async with database[1]() as session:
        character = await _char(session, actor)
        return await session.scalar(
            select(OathMember).where(OathMember.character_id == character.id)
        )


async def _weaken(database) -> None:
    """Leaves the current enemy one hit from falling."""
    async with database[1].begin() as session:
        attempt = await session.scalar(select(OathAttempt).where(OathAttempt.status == "active"))
        combat = decode(
            attempt.combat_snapshot,
            attempt.combat_id,
            attempt.ruleset_version,
            attempt.state_version,
        )
        combat.fighters["enemy"].hp = D(1)
        attempt.combat_snapshot = encode(combat)


async def _endanger(database) -> None:
    """Leaves the roster one hit from falling and the enemy hard to kill."""
    async with database[1].begin() as session:
        attempt = await session.scalar(select(OathAttempt).where(OathAttempt.status == "active"))
        combat = decode(
            attempt.combat_snapshot,
            attempt.combat_id,
            attempt.ruleset_version,
            attempt.state_version,
        )
        for key, fighter in combat.fighters.items():
            fighter.hp = D(1) if key != "enemy" else D(999_999)
        attempt.combat_snapshot = encode(combat)


async def _press(service, view: CombatView, action: str, *, now=PLAYING, actor=A):
    index = list(class_trial_action_ids(view.combat, actor_key=view.combat_actor_key)).index(action)
    return await service.action(actor, view.activity_id, view.combat.version, index, "x", now=now)


async def _win_stage(service, database, *, now=PLAYING):
    await _weaken(database)
    view = await service.foreground(A)
    return await _press(service, view, "attack", now=now)


async def _start(service, now=PLAYING) -> CombatView:
    await service.hub(A, now=OPENING)
    return await service.start_solo(A, now=now)


async def test_empty_catalog_creates_no_cycle(database):
    await _seed(database)
    service = _service(database, catalog=())
    view = await service.hub(A, now=PLAYING)
    assert view.catalog_empty
    await service.run_maintenance(now=PLAYING)
    assert await _code(service.start_solo(A, now=PLAYING)) == "closed"
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(OathCycle)) == 0


async def test_cycle_row_is_unique_per_opening(database):
    await _seed(database)
    service = _service(database)
    await service.run_maintenance(now=OPENING)
    await service.run_maintenance(now=PLAYING)
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(OathCycle)) == 1


async def test_character_without_guild_cannot_start(database):
    await _seed(database)
    async with database[1].begin() as session:
        character = await _char(session, A)
        await session.delete(await session.get(GuildMember, character.id))
    service = _service(database)
    await service.hub(A, now=PLAYING)
    assert await _code(service.start_solo(A, now=PLAYING)) == "no_guild"


async def test_start_is_clean_consumes_one_provacao_and_never_touches_character_hp(database):
    await _seed(database)
    service = _service(database)
    view = await _start(service)
    assert isinstance(view, CombatView) and view.context == "oath_trial"
    assert view.combat.fighters["player"].hp == view.combat.fighters["player"].stats.hp
    assert (await _binding(database, A)).provacoes_used == 1
    async with database[1]() as session:
        assert (await _char(session, A)).hp == D("50")
    assert view.combat.fighters["enemy"].stats == encounter_stats(
        TRIAL.encounter(1).creature, 30, 1
    )


async def test_configuration_is_locked_through_the_whole_provacao(database):
    await _seed(database)
    service = _service(database)
    await _start(service)
    await _win_stage(service, database)
    async with database[1].begin() as session:
        character = await _char(session, A)
        with pytest.raises(CombatConfigurationLocked):
            await lock_for_combat_configuration_mutation(session, character.id)


async def test_resume_returns_the_same_provacao(database):
    await _seed(database)
    service = _service(database)
    view = await _start(service)
    again = await service.foreground(A)
    assert again.activity_id == view.activity_id
    assert await _code(service.start_solo(A, now=PLAYING)) == "busy"
    assert (await _binding(database, A)).provacoes_used == 1


async def test_full_provacao_scores_sixty_and_keeps_counting_up(database):
    await _seed(database)
    service = _service(database)
    await _start(service)
    first = await _win_stage(service, database)
    assert isinstance(first, CombatView) and "Combate 2/3" in first.stage
    assert (await _binding(database, A)).contribution == 10
    second = await _win_stage(service, database)
    assert isinstance(second, CombatView) and "Combate 3/3" in second.stage
    assert (await _binding(database, A)).contribution == 25
    result = await _win_stage(service, database)
    assert isinstance(result, OathAttemptResultView)
    assert result.outcome == "completed"
    assert (result.points, result.cycle_total) == (60, 60)
    attempt = await _attempt(database)
    async with database[1]() as session:
        progress = await session.get(OathGuildProgress, (attempt.cycle_id, attempt.guild_id))
        assert progress.contribution == 60
        milestones = await session.scalar(select(func.count()).select_from(OathMilestone))
        assert milestones == 4
        activity = await session.scalar(select(GameActivity))
        assert activity.status == "completed"


async def test_next_combat_keeps_hp_and_a_growing_version(database):
    await _seed(database)
    service = _service(database)
    await _start(service)
    await _weaken(database)
    before = await service.foreground(A)
    hurt = before.combat.fighters["player"].stats.hp - D(40)
    async with database[1].begin() as session:
        attempt = await session.scalar(select(OathAttempt))
        combat = decode(
            attempt.combat_snapshot,
            attempt.combat_id,
            attempt.ruleset_version,
            attempt.state_version,
        )
        combat.fighters["player"].hp = hurt
        attempt.combat_snapshot = encode(combat)
    before = await service.foreground(A)
    after = await _press(service, before, "attack")
    assert after.combat.fighters["player"].hp == hurt
    assert after.combat.version > before.combat.version
    assert after.combat.fighters["enemy"].stats == encounter_stats(
        TRIAL.encounter(2).creature, 30, 1
    )
    # A button from the previous combat cannot act on the new one.
    index = list(class_trial_action_ids(before.combat, actor_key="player")).index("attack")
    stale = await service.action(
        A, before.activity_id, before.combat.version, index, "x", now=PLAYING
    )
    assert stale.combat.version == after.combat.version


async def test_defeat_keeps_earned_contribution_and_consumes_the_provacao(database):
    await _seed(database)
    service = _service(database)
    await _start(service)
    await _win_stage(service, database)
    await _endanger(database)
    view = await service.foreground(A)
    result = await _press(service, view, "defend")
    if isinstance(result, CombatView):
        result = await _press(service, result, "defend")
    assert isinstance(result, OathAttemptResultView)
    assert result.outcome == "failed" and result.points == 10
    binding = await _binding(database, A)
    assert binding.contribution == 10 and binding.provacoes_used == 1


async def test_three_provacoes_per_cycle(database):
    await _seed(database)
    service = _service(database)
    await _start(service)
    for number in range(1, 4):
        assert (await _binding(database, A)).provacoes_used == number
        await service.abandon(A, now=PLAYING)
        if number < 3:
            await service.start_solo(A, now=PLAYING)
    assert await _code(service.start_solo(A, now=PLAYING)) == "no_provacoes"
    hub = await service.hub(A, now=PLAYING)
    assert hub.provacoes_left == 0 and not hub.can_start


async def test_abandon_keeps_contribution_and_frees_the_character(database):
    await _seed(database)
    service = _service(database)
    await _start(service)
    await _win_stage(service, database)
    result = await service.abandon(A, now=PLAYING)
    assert isinstance(result, OathAttemptResultView) and result.outcome == "abandoned"
    assert (await _binding(database, A)).contribution == 10
    assert await service.foreground(A) is None
    assert await _code(service.abandon(A, now=PLAYING)) == "no_active"


async def test_guild_hopping_is_blocked_within_the_cycle(database):
    await _seed(database)
    service = _service(database)
    await _start(service)
    await _win_stage(service, database)
    await service.abandon(A, now=PLAYING)
    async with database[1].begin() as session:
        character = await _char(session, A)
        other = await session.scalar(select(Guild).where(Guild.name == "Brasa"))
        membership = await session.get(GuildMember, character.id)
        membership.guild_id = other.id
        membership.role = "member"
    hub = await service.hub(A, now=PLAYING)
    assert hub.bound_elsewhere and not hub.can_start
    assert await _code(service.start_solo(A, now=PLAYING)) == "bound_elsewhere"
    attempt = await _attempt(database)
    async with database[1]() as session:
        # The contribution stays with the Guild it was earned for.
        assert (
            await session.get(OathGuildProgress, (attempt.cycle_id, attempt.guild_id))
        ).contribution == 10


async def test_no_new_provacao_after_the_deadline(database):
    await _seed(database)
    service = _service(database)
    await service.hub(A, now=OPENING)
    assert await _code(service.start_solo(A, now=DEADLINE)) == "closed"
    hub = await service.hub(A, now=DEADLINE)
    assert hub.window == "grace" and not hub.can_start


async def test_open_provacao_ends_at_the_grace_period_keeping_only_what_was_committed(database):
    await _seed(database)
    service = _service(database)
    await _start(service, now=DEADLINE - timedelta(minutes=1))
    await _win_stage(service, database, now=DEADLINE - timedelta(seconds=30))
    async with database[1].begin() as session:
        await session.execute(update(OathAttempt).values(last_action_at=GRACE_END))
    await service.run_maintenance(now=GRACE_END)
    attempt = await _attempt(database)
    assert attempt.status == "expired" and attempt.points == 10


async def test_action_after_the_grace_period_earns_nothing(database):
    await _seed(database)
    service = _service(database)
    view = await _start(service, now=DEADLINE - timedelta(minutes=1))
    await _weaken(database)
    index = list(class_trial_action_ids(view.combat, actor_key="player")).index("attack")
    result = await service.action(
        A, view.activity_id, view.combat.version, index, "x", now=GRACE_END
    )
    assert isinstance(result, OathAttemptResultView) and result.outcome == "expired"
    assert (await _binding(database, A)).contribution == 0


async def test_idle_provacao_is_closed_by_maintenance(database):
    await _seed(database)
    service = _service(database)
    await _start(service)
    await service.run_maintenance(now=PLAYING + timedelta(minutes=29))
    assert (await _attempt(database)).status == "active"
    await service.run_maintenance(now=PLAYING + timedelta(minutes=31))
    assert (await _attempt(database)).status == "abandoned"
    assert await service.foreground(A) is None


async def _set_scores(database, collective: int, individual: dict[int, int]) -> None:
    async with database[1].begin() as session:
        await session.execute(update(OathGuildProgress).values(contribution=collective))
        for actor, value in individual.items():
            character = await _char(session, actor)
            await session.execute(
                update(OathMember)
                .where(OathMember.character_id == character.id)
                .values(contribution=value, provacoes_used=1)
            )


async def _bind(service, database, actor) -> None:
    await service.hub(actor, now=OPENING)
    await service.start_solo(actor, now=PLAYING)
    await service.abandon(actor, now=PLAYING)


async def test_finalization_pays_once_and_separates_collective_from_individual(database):
    await _seed(database)
    service = _service(database)
    await _bind(service, database, A)
    await _bind(service, database, B)
    await _set_scores(database, 300, {A: 60, B: 59})
    notices = await service.run_maintenance(now=GRACE_END)
    await service.run_maintenance(now=GRACE_END + timedelta(minutes=1))
    assert {notice.telegram_id for notice in notices} == {A, B}
    expected = reward_bundle(30, 2)
    async with database[1]() as session:
        first = await _char(session, A)
        second = await _char(session, B)
        assert first.crowns == expected.crowns
        assert second.crowns == 0
        guild = await session.scalar(select(Guild).where(Guild.name == "Aurora"))
        assert guild.treasury_crowns == 4_000
        assert await session.scalar(select(func.count()).select_from(GuildTreasuryEntry)) == 1
        cycle = await session.scalar(select(OathCycle))
        assert cycle.status == "closed"
    result = await service.last_result(A)
    assert isinstance(result, OathCycleResultView)
    assert result.tier == 2 and result.eligible and result.treasury == 4_000
    assert any("Fragmento" in item.name for item in result.items)
    other = await service.last_result(B)
    assert other.participated and not other.eligible and other.crowns == 0


async def test_no_tier_means_no_reward(database):
    await _seed(database)
    service = _service(database)
    await _bind(service, database, A)
    await _set_scores(database, 119, {A: 119})
    await service.run_maintenance(now=GRACE_END)
    async with database[1]() as session:
        assert (await _char(session, A)).crowns == 0
    result = await service.last_result(A)
    assert result.tier == 0 and not result.eligible


async def test_member_who_did_not_play_only_sees_the_collective_result(database):
    await _seed(database)
    service = _service(database)
    await _bind(service, database, A)
    await _set_scores(database, 120, {A: 60})
    await service.run_maintenance(now=GRACE_END)
    result = await service.last_result(B)
    assert isinstance(result, OathCycleResultView)
    assert result.tier == 1 and not result.participated and not result.eligible
    assert "🎁" not in render_oath(result).text


async def test_reward_survives_leaving_the_guild_after_the_snapshot(database):
    await _seed(database)
    service = _service(database)
    await _bind(service, database, A)
    await _set_scores(database, 120, {A: 60})
    async with database[1].begin() as session:
        character = await _char(session, A)
        await session.delete(await session.get(GuildMember, character.id))
    await service.run_maintenance(now=GRACE_END)
    async with database[1]() as session:
        assert (await _char(session, A)).crowns == reward_bundle(30, 1).crowns


async def test_finalization_blocks_guild_dissolution_until_done(database):
    await _seed(database)
    service = _service(database)
    await _bind(service, database, A)
    attempt = await _attempt(database)
    async with database[1]() as session:
        assert await _has_cooperative_commitment(session, attempt.guild_id)
    await service.run_maintenance(now=GRACE_END)
    async with database[1]() as session:
        assert not await _has_cooperative_commitment(session, attempt.guild_id)


async def _open_cycle_now(database, service) -> None:
    """Group confirmation uses the real clock, so the cycle must be open today."""
    now = datetime.now(UTC)
    async with database[1].begin() as session:
        session.add(
            OathCycle(
                server_id="ocaso",
                cycle_key="teste",
                trial_id=TRIAL.trial_id,
                status="open",
                opens_at=now - timedelta(minutes=1),
                deadline_at=now + timedelta(hours=1),
                grace_ends_at=now + timedelta(hours=2),
                ruleset_version="oath_v1",
            )
        )


async def _start_group(database, service) -> str:
    groups = GroupService(database[1], "ocaso")
    group = await groups.create_group(A)
    invite = await groups.invite(A, "Beta", expected_group_revision=group.revision)
    joined = await groups.respond_invite(
        B, invite.invite_id, expected_revision=invite.revision, accept=True
    )
    payload = await service.group_proposal(A)
    proposal = await groups.propose_activity(
        A,
        activity_type=OATH_ACTIVITY_TYPE,
        participant_character_ids=tuple(member.character_id for member in joined.members),
        eligibility_resolver=service.eligibility,
        context_payload=payload,
    )
    ready = await groups.respond_activity(
        B, proposal.proposal_id, expected_revision=proposal.revision, accept=True
    )
    result = await groups.start_activity(
        A,
        proposal.proposal_id,
        expected_revision=ready.revision,
        eligibility_resolver=service.eligibility,
        create_activity=service.create_activity,
    )
    assert result.started
    return result.activity_reference


async def _active_actor(service) -> tuple[int, CombatView]:
    for actor in (A, B):
        view = await service.foreground(actor)
        if view is not None and active_player_key(view.combat) == view.combat_actor_key:
            return actor, view
    raise AssertionError("nobody can act")


async def test_group_provacao_scales_and_counts_collective_once(database):
    await _seed(database)
    sent = []

    async def record(notices):
        sent.extend(notices)

    service = _service(database, record)
    await _open_cycle_now(database, service)
    reference = await _start_group(database, service)
    await service.announce_start(reference, A)
    assert [notice.telegram_id for notice in sent] == [B]
    assert sent[0].view == OathTurnNotice(TRIAL.name, started=True)
    sent.clear()
    actor, view = await _active_actor(service)
    assert view.combat.party_mode
    assert view.combat.fighters["enemy"].stats == encounter_stats(
        TRIAL.encounter(1).creature, 30, 2
    )
    assert any(
        (button.callback_data or "").startswith("oa:")
        for row in render_oath(view).keyboard.inline_keyboard
        for button in row
    )
    other = B if actor == A else A
    waiting = await service.foreground(other)
    assert any(
        button.callback_data == "oath:go"
        for row in render_oath(waiting).keyboard.inline_keyboard
        for button in row
    )
    now = datetime.now(UTC)
    await _weaken(database)
    result = await _press(service, await service.foreground(actor), "attack", now=now, actor=actor)
    assert isinstance(result, CombatView) and "Combate 2/3" in result.stage
    attempt = await _attempt(database)
    async with database[1]() as session:
        assert (
            await session.get(OathGuildProgress, (attempt.cycle_id, attempt.guild_id))
        ).contribution == 10
    # §22.1: presence alone earns no individual contribution.
    assert (await _binding(database, actor)).contribution == 10
    assert (await _binding(database, other)).contribution == 0


async def test_group_turn_passes_with_a_notice(database):
    await _seed(database)
    sent = []

    async def record(notices):
        sent.extend(notices)

    service = _service(database, record)
    await _open_cycle_now(database, service)
    await _start_group(database, service)
    actor, view = await _active_actor(service)
    other = B if actor == A else A
    now = datetime.now(UTC)
    await _press(service, view, "defend", now=now, actor=actor)
    assert [notice.telegram_id for notice in sent] == [other]
    assert isinstance(sent[0].view, OathTurnNotice) and not sent[0].view.started


async def test_only_the_opener_abandons_and_it_ends_for_the_whole_roster(database):
    await _seed(database)
    service = _service(database)
    await _open_cycle_now(database, service)
    await _start_group(database, service)
    assert await _code(service.abandon(B)) == "not_opener"
    result = await service.abandon(A)
    assert isinstance(result, OathAttemptResultView)
    assert await service.foreground(B) is None
    async with database[1]() as session:
        count = await session.scalar(
            select(func.count()).select_from(GameActivity).where(GameActivity.status == "active")
        )
        assert count == 0
        members = await session.scalar(select(func.count()).select_from(OathAttemptMember))
        assert members == 2


async def _edit_combat(database, change) -> None:
    async with database[1].begin() as session:
        attempt = await session.scalar(select(OathAttempt).where(OathAttempt.status == "active"))
        combat = decode(
            attempt.combat_snapshot,
            attempt.combat_id,
            attempt.ruleset_version,
            attempt.state_version,
        )
        change(combat)
        attempt.combat_snapshot = encode(combat)


async def test_fallen_member_stays_down_and_defeat_needs_the_whole_roster(database):
    await _seed(database)
    service = _service(database)
    await _open_cycle_now(database, service)
    await _start_group(database, service)
    actor, view = await _active_actor(service)
    other = B if actor == A else A
    other_key = (await service.foreground(other)).combat_actor_key

    def fell(combat):
        combat.fighters[other_key].hp = D(0)
        combat.fighters["enemy"].hp = D(1)

    await _edit_combat(database, fell)
    now = datetime.now(UTC)
    following = await _press(
        service, await service.foreground(actor), "attack", now=now, actor=actor
    )
    assert isinstance(following, CombatView) and "Combate 2/3" in following.stage
    fallen = following.combat.fighters[other_key]
    assert fallen.hp == 0 and not fallen.takes_turn
    assert active_player_key(following.combat) == following.combat_actor_key

    def last_stand(combat):
        combat.fighters[following.combat_actor_key].hp = D(1)
        combat.fighters["enemy"].hp = D(999_999)

    await _edit_combat(database, last_stand)
    result = await _press(service, await service.foreground(actor), "defend", now=now, actor=actor)
    if isinstance(result, CombatView):
        result = await _press(service, result, "defend", now=now, actor=actor)
    assert isinstance(result, OathAttemptResultView) and result.outcome == "failed"
    assert (await _binding(database, actor)).contribution == 10


async def test_hub_outside_a_cycle_shows_the_next_opening(database):
    await _seed(database)
    service = _service(database)
    view = await service.hub(A, now=OPENING - timedelta(days=1))
    assert isinstance(view, OathHubView)
    assert view.deadline is None and view.next_opening == OPENING


async def test_consumable_budget_is_three_per_provacao_across_its_combats(database):
    await _seed(database)
    service = _service(database)
    view = await _start(service)
    assert view.consumable_budget_limit == 3
    await _win_stage(service, database)
    async with database[1].begin() as session:
        await session.execute(update(OathAttemptMember).values(consumable_uses=3))
    resumed = await service.foreground(A)
    assert resumed.consumable_budget_limit == 0
    assert resumed.consumable_options == ()
    unchanged = await service.consume_for_activity(
        A,
        resumed.activity_id,
        resumed.combat.version,
        item_id="qualquer",
        target_id="player",
        effect_id=None,
        now=PLAYING,
    )
    assert unchanged.combat.version == resumed.combat.version

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

import asterion.application.pvpve as pvpve_module
from asterion.bot.road_ui import render_road
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    GameActivity,
    HuntContext,
    HuntRound,
    HuntRoundEncounter,
    PvpveCollision,
    PvpveCollisionMember,
    PvpveDomainGrant,
    PvpveQueue,
    RewardComponent,
    RewardEvent,
    WorldState,
)
from tests.test_road_integration import _seed_road
from tests.test_round_integration import _force_safe_common, _seed_round


@pytest.mark.asyncio
async def test_round_frontier_uses_seventy_five_minute_pvpve_queue_and_reconnects(database):
    actor, service = await _seed_round(database, 992701, pvpve=True)
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)

    assert started.kind == "hunt_queue"
    assert started.pvpve_round_queue is True
    queue_screen = render_road(started)
    queue_button = queue_screen.keyboard.inline_keyboard[1][0]
    assert queue_button.text == "Continuar sem Rival"
    assert len(queue_button.callback_data.encode()) < 64
    async with database[1]() as session:
        queue = await session.scalar(
            select(PvpveQueue).where(PvpveQueue.roster_snapshot.contains([started.character_id.hex]))
        )
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == prepared.round_id)
        )
        activity = await session.get(GameActivity, started.activity_id)
        assert queue is not None and queue.source_type == "round"
        assert queue.expires_at - queue.created_at == timedelta(minutes=75)
        assert state is not None and state.next_resolution_at == queue.expires_at
        assert activity is not None and activity.content_id == "road_pvpve_queue"
        assert await session.scalar(select(HuntRoundEncounter.id)) is None

    resumed = await service.resume(actor)
    assert resumed is not None and resumed.kind == "hunt_queue"
    assert resumed.activity_id == started.activity_id


@pytest.mark.asyncio
async def test_expired_round_queue_continues_as_normal_pve_without_new_round(database, monkeypatch):
    actor, service = await _seed_round(database, 992702, pvpve=True)
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind == "hunt_queue"

    async with database[1]() as session:
        queue = await session.scalar(
            select(PvpveQueue).where(PvpveQueue.status == "waiting")
        )
        assert queue is not None
        expiry = queue.expires_at

    monkeypatch.setattr(pvpve_module, "_utcnow", lambda: expiry)
    assert await service.pvpve.refresh_queue(actor, started.activity_id)

    resumed = await service.resume(actor)
    assert resumed is not None and resumed.kind == "round_active"
    assert resumed.round_id == prepared.round_id
    assert resumed.encounter_id is not None
    async with database[1]() as session:
        queue = await session.scalar(
            select(PvpveQueue).where(PvpveQueue.status == "expired")
        )
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == prepared.round_id)
        )
        assert queue is not None and state is not None
        assert state.status == "active" and state.completed_encounters == 0
        assert await session.scalar(select(HuntRoundEncounter.id)) is not None


@pytest.mark.asyncio
async def test_round_scheduler_resolves_expired_pvpve_queue(database):
    actor, service = await _seed_round(database, 992703, pvpve=True)
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind == "hunt_queue"
    boundary = datetime.now(UTC) - timedelta(seconds=1)
    async with database[1]() as session:
        queue = await session.scalar(
            select(PvpveQueue).where(PvpveQueue.status == "waiting")
        )
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == prepared.round_id)
        )
        assert queue is not None and state is not None
        queue.expires_at = boundary
        state.next_resolution_at = boundary
        await session.commit()

    assert await service.advance_due_rounds() == 1
    async with database[1]() as session:
        queue = await session.scalar(
            select(PvpveQueue).where(PvpveQueue.status == "expired")
        )
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == prepared.round_id)
        )
        activity = await session.get(GameActivity, started.activity_id)
        encounter = await session.scalar(select(HuntRoundEncounter))
        assert queue is not None and state is not None and activity is not None
        assert activity.content_id == "road_hunt_round"
        assert state.status == "active" and state.completed_encounters == 0
        assert encounter is not None and encounter.status == "materialized"


@pytest.mark.asyncio
async def test_round_queue_cancel_continues_the_same_batch(database):
    actor, service = await _seed_round(database, 992706, pvpve=True)
    prepared = await service.prepare_round(actor, 5)
    queued = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert queued.kind == "hunt_queue"

    view = await service.pvpve.cancel_queue(actor, queued.activity_id)
    assert view is not None and view.kind == "round_active"
    async with database[1]() as session:
        queue = await session.scalar(select(PvpveQueue))
        state = await session.get(HuntRound, prepared.round_id)
        activity = await session.get(GameActivity, queued.activity_id)
        encounter = await session.scalar(select(HuntRoundEncounter))
        assert queue is not None and queue.status == "cancelled"
        assert state is not None and state.status == "active"
        assert activity is not None and activity.content_id == "road_hunt_round"
        assert encounter is not None and encounter.status == "materialized"


@pytest.mark.asyncio
async def test_round_queue_context_change_ends_batch_instead_of_stranding_it(database):
    actor, service = await _seed_round(database, 992710, pvpve=True)
    prepared = await service.prepare_round(actor, 5)
    queued = await service.start_round(actor, prepared.round_id, prepared.state_version)
    boundary = datetime.now(UTC) - timedelta(seconds=1)
    async with database[1].begin() as session:
        queue = await session.scalar(select(PvpveQueue))
        state = await session.get(HuntRound, prepared.round_id)
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.get(WorldState, character.id)
        assert queue is not None and state is not None and world is not None
        queue.expires_at = boundary
        state.next_resolution_at = boundary
        world.location = "Refúgio do Ocaso"

    assert await service.pvpve.refresh_queue(actor, queued.activity_id)
    view = await service.resume(actor)
    assert view is not None and view.kind == "round_ended"
    async with database[1]() as session:
        queue = await session.scalar(select(PvpveQueue))
        state = await session.get(HuntRound, prepared.round_id)
        activity = await session.get(GameActivity, queued.activity_id)
        assert queue is not None and queue.status == "cancelled"
        assert state is not None and state.status == "ended"
        assert state.end_reason == "pvpve_context_changed"
        assert activity is not None and activity.status == "completed"
        assert await session.scalar(select(HuntRoundEncounter.id)) is None


@pytest.mark.asyncio
async def test_round_ai_acts_without_waiting_and_takeover_is_idempotent(database):
    round_actor, manual_actor, service, _prepared, round_member, collision = (
        await _start_round_manual_collision(database, 992707, 995103)
    )
    async with database[1].begin() as session:
        persisted = await session.get(PvpveCollision, collision.id)
        combat = decode(
            persisted.combat_snapshot,
            persisted.combat_id,
            persisted.ruleset_version,
            persisted.state_version,
        )
        order = (round_member.actor_key,) + tuple(
            key for key in combat.order if key != round_member.actor_key
        )
        combat = replace(combat, order=order, turn_index=0)
        persisted.combat_snapshot = encode(combat)
        persisted.state_version = combat.version
        round_version = combat.version

    handled, view = await service.pvpve.handle_action(
        round_actor,
        round_member.game_activity_id,
        round_version,
        action="defend",
    )
    assert handled and view is not None and view.pvpve_round_ai
    async with database[1]() as session:
        persisted = await session.get(PvpveCollision, collision.id)
        member = await session.get(
            PvpveCollisionMember, (collision.id, round_member.character_id)
        )
        assert persisted is not None and persisted.state_version > round_version
        assert member is not None and member.contributed is True
        auto_version = persisted.state_version

    takeover = await service.pvpve.assume_round_control(
        round_actor, round_member.game_activity_id
    )
    repeated = await service.pvpve.assume_round_control(
        round_actor, round_member.game_activity_id
    )
    assert takeover is not None and takeover.pvpve_round_ai is False
    assert takeover.pvpve_round_takeover is True
    assert repeated is not None and repeated.pvpve_round_ai is False
    assert "você agirá na próxima oportunidade" in render_road(takeover).text
    screen = render_road(view)
    callback = screen.keyboard.inline_keyboard[0][0].callback_data
    assert callback == f"road:pvpve:takeover:{round_member.game_activity_id.hex}"
    assert len(callback.encode()) < 64
    async with database[1]() as session:
        persisted = await session.get(PvpveCollision, collision.id)
        member = await session.get(
            PvpveCollisionMember, (collision.id, round_member.character_id)
        )
        assert persisted is not None and persisted.state_version == auto_version
        assert member is not None and member.round_takeover is True


@pytest.mark.asyncio
async def test_round_can_match_another_round_and_reconnects_both_owners(database):
    actor_a, service_a = await _seed_round(database, 992708, pvpve=True)
    actor_b, service_b = await _seed_round(database, 992709, pvpve=True)
    first = await service_a.prepare_round(actor_a, 5)
    first_view = await service_a.start_round(actor_a, first.round_id, first.state_version)
    assert first_view.kind == "hunt_queue"
    second = await service_b.prepare_round(actor_b, 5)
    second_view = await service_b.start_round(actor_b, second.round_id, second.state_version)

    async with database[1]() as session:
        queues = list((await session.scalars(select(PvpveQueue))).all())
        collision = await session.scalar(select(PvpveCollision))
        members = list((await session.scalars(select(PvpveCollisionMember))).all())
        assert len(queues) == 2 and all(row.source_type == "round" for row in queues)
        assert all(row.status == "matched" for row in queues)
        assert collision is not None
        assert collision.status != "active"
        assert len(members) == 2

    assert second_view is not None
    assert await service_a.resume(actor_a) is not None
    assert await service_b.resume(actor_b) is not None


@pytest.mark.asyncio
async def test_manual_queue_can_be_matched_by_a_later_round_queue(database):
    manual_actor, manual_service = await _seed_road(database, 992711)
    del manual_service.pvpve.queue_manual_hunt
    await manual_service.travel(manual_actor, "Estrada das Cinzas")
    manual_view = await manual_service.start_hunt(manual_actor)
    assert manual_view is not None and manual_view.kind == "hunt_queue"

    round_actor, round_service = await _seed_round(database, 992712, pvpve=True)
    prepared = await round_service.prepare_round(round_actor, 5)
    round_view = await round_service.start_round(
        round_actor, prepared.round_id, prepared.state_version
    )
    assert round_view is not None

    async with database[1]() as session:
        queues = list((await session.scalars(select(PvpveQueue))).all())
        collision = await session.scalar(select(PvpveCollision))
        assert {queue.source_type for queue in queues} == {"manual", "round"}
        assert all(queue.status == "matched" for queue in queues)
        assert collision is not None
        assert collision.roster_size == 1
    assert await manual_service.resume(manual_actor) is not None
    assert await round_service.resume(round_actor) is not None


async def _start_round_manual_collision(database, round_actor, manual_actor):
    await _seed_road(database, manual_actor)
    round_actor, service = await _seed_round(database, round_actor, pvpve=True)
    prepared = await service.prepare_round(round_actor, 5)
    round_view = await service.start_round(
        round_actor, prepared.round_id, prepared.state_version
    )
    assert round_view.kind == "hunt_queue"
    await service.travel(manual_actor, "Estrada das Cinzas")
    manual_view = await service.start_hunt(manual_actor)
    assert manual_view is not None and manual_view.combat_context == "pvpve"
    async with database[1]() as session:
        round_character = await session.scalar(
            select(Character).where(Character.telegram_id == round_actor)
        )
        member = await session.scalar(
            select(PvpveCollisionMember).where(
                PvpveCollisionMember.character_id == round_character.id
            )
        )
        collision = await session.get(PvpveCollision, member.collision_id)
        return round_actor, manual_actor, service, prepared, member, collision


@pytest.mark.asyncio
async def test_round_pvp_victory_returns_to_frozen_round_pve(database, monkeypatch):
    import asterion.application.round as round_module

    _force_safe_common(monkeypatch, round_module)
    round_actor, manual_actor, service, prepared, round_member, collision = (
        await _start_round_manual_collision(database, 992704, 995101)
    )
    takeover = await service.pvpve.assume_round_control(
        round_actor, round_member.game_activity_id
    )
    assert takeover is not None and takeover.pvpve_round_ai is False
    async with database[1].begin() as session:
        persisted = await session.get(PvpveCollision, collision.id)
        combat = decode(
            persisted.combat_snapshot,
            persisted.combat_id,
            persisted.ruleset_version,
            persisted.state_version,
        )
        opponent_key = next(
            key for key in combat.fighters if key != round_member.actor_key
        )
        fighters = {
            key: replace(fighter, hp=Decimal("1"))
            if key == opponent_key
            else replace(fighter, stats=replace(fighter.stats, attack=Decimal("10000")))
            if key == round_member.actor_key
            else fighter
            for key, fighter in combat.fighters.items()
        }
        order = (round_member.actor_key,) + tuple(
            key for key in combat.order if key != round_member.actor_key
        )
        combat = replace(combat, fighters=fighters, order=order, turn_index=0)
        persisted.combat_snapshot = encode(combat)
        persisted.state_version = combat.version
        activity_id = round_member.game_activity_id
        target_id = combat.fighters[opponent_key].id

    await service.action(
        round_actor,
        activity_id,
        combat.version,
        "attack",
        target_id=target_id,
    )

    async with database[1]() as session:
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == prepared.round_id)
        )
        activity = await session.get(GameActivity, activity_id)
        persisted = await session.get(PvpveCollision, collision.id)
        member = await session.get(
            PvpveCollisionMember, (collision.id, round_member.character_id)
        )
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == prepared.round_id
            )
        )
        assert state is not None and state.status == "active"
        assert activity is not None and activity.content_id == "road_hunt_round"
        assert persisted is not None and persisted.status == "prey"
        assert member is not None and member.status == "prey"
        assert encounter is not None and encounter.status == "materialized"

    async with database[1].begin() as session:
        state = await session.get(HuntRound, prepared.round_id)
        assert state is not None
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
    assert await service.advance_due_rounds() == 1

    async with database[1]() as session:
        state = await session.get(HuntRound, prepared.round_id)
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == prepared.round_id
            )
        )
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == encounter.activity_id)
        )
        grant = await session.get(
            PvpveDomainGrant, (collision.id, round_member.character_id)
        )
        persisted_collision = await session.get(PvpveCollision, collision.id)
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == round_member.character_id,
                RewardEvent.source_id == f"activity:{encounter.activity_id}",
            )
        )
        assert state is not None and state.completed_encounters == 1
        assert encounter is not None and encounter.status == "completed"
        assert context is not None and context.pvpve_collision_id == collision.id
        assert context.pvpve_domain_eligible is True
        assert reward is not None
        assert grant is not None and grant.status == "granted" and grant.crowns > 0
        assert persisted_collision is not None and persisted_collision.status == "completed"

    assert await service.advance_due_rounds() == 0
    async with database[1]() as session:
        assert await session.scalar(
            select(PvpveDomainGrant.character_id).where(
                PvpveDomainGrant.collision_id == collision.id
            )
        ) == round_member.character_id


@pytest.mark.asyncio
async def test_round_pvp_victory_without_vigor_closes_collision_without_orphaned_prey(
    database,
):
    round_actor, _manual_actor, service, prepared, round_member, collision = (
        await _start_round_manual_collision(database, 992713, 995104)
    )
    takeover = await service.pvpve.assume_round_control(
        round_actor, round_member.game_activity_id
    )
    assert takeover is not None
    async with database[1].begin() as session:
        persisted = await session.get(PvpveCollision, collision.id)
        character = await session.get(Character, round_member.character_id)
        assert persisted is not None and character is not None
        combat = decode(
            persisted.combat_snapshot,
            persisted.combat_id,
            persisted.ruleset_version,
            persisted.state_version,
        )
        opponent_key = next(
            key for key in combat.fighters if key != round_member.actor_key
        )
        fighters = {
            key: replace(fighter, hp=Decimal("1"))
            if key == opponent_key
            else replace(fighter, stats=replace(fighter.stats, attack=Decimal("10000")))
            if key == round_member.actor_key
            else fighter
            for key, fighter in combat.fighters.items()
        }
        order = (round_member.actor_key,) + tuple(
            key for key in combat.order if key != round_member.actor_key
        )
        combat = replace(combat, fighters=fighters, order=order, turn_index=0)
        persisted.combat_snapshot = encode(combat)
        persisted.state_version = combat.version
        character.vigor = 1
        activity_id = round_member.game_activity_id
        target_id = combat.fighters[opponent_key].id

    await service.action(
        round_actor,
        activity_id,
        combat.version,
        "attack",
        target_id=target_id,
    )

    async with database[1]() as session:
        state = await session.get(HuntRound, prepared.round_id)
        activity = await session.get(GameActivity, activity_id)
        persisted = await session.get(PvpveCollision, collision.id)
        member = await session.get(
            PvpveCollisionMember, (collision.id, round_member.character_id)
        )
        assert state is not None and state.status == "ended"
        assert state.end_reason == "vigor"
        assert activity is not None and activity.status == "completed"
        assert activity.content_id == "road_hunt_round"
        assert persisted is not None and persisted.status == "completed"
        assert member is not None and member.status == "settled"
        assert member.result_acknowledged is True
        assert member.domain_eligible is False
        assert await session.scalar(
            select(HuntRoundEncounter.id).where(
                HuntRoundEncounter.round_id == prepared.round_id
            )
        ) is None
        assert await session.get(
            PvpveDomainGrant, (collision.id, round_member.character_id)
        ) is None


@pytest.mark.asyncio
async def test_round_pvp_defeat_ends_batch_and_preserves_round_result(database):
    round_actor, manual_actor, service, prepared, round_member, collision = (
        await _start_round_manual_collision(database, 992705, 995102)
    )
    takeover = await service.pvpve.assume_round_control(
        round_actor, round_member.game_activity_id
    )
    assert takeover is not None and takeover.pvpve_round_takeover
    async with database[1].begin() as session:
        state = await session.get(HuntRound, prepared.round_id)
        assert state is not None
        prior_activity = GameActivity(
            id=uuid4(),
            character_id=round_member.character_id,
            content_id="road_round_encounter",
            status="completed",
            state_version=0,
            ruleset_version="gdd-1.4.9",
            last_valid_action_at=datetime.now(UTC),
        )
        session.add(prior_activity)
        await session.flush()
        session.add(
            HuntRoundEncounter(
                id=uuid4(),
                round_id=prepared.round_id,
                ordinal=1,
                activity_id=prior_activity.id,
                combat_id=uuid4(),
                seed="previous-settlement",
                creature_id="dog_cinereo",
                category="common",
                enemy_level=1,
                status="completed",
                state_version=0,
                combat_snapshot={},
            )
        )
        state.completed_encounters = 1
        previous_reward = RewardEvent(
            character_id=round_member.character_id,
            source_id=f"activity:{prior_activity.id}",
        )
        session.add(previous_reward)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=previous_reward.id,
                kind="xp",
                quantity=123,
                payload={},
            )
        )

        persisted = await session.get(PvpveCollision, collision.id)
        combat = decode(
            persisted.combat_snapshot,
            persisted.combat_id,
            persisted.ruleset_version,
            persisted.state_version,
        )
        round_key = round_member.actor_key
        manual_key = next(key for key in combat.fighters if key != round_key)
        fighters = {
            key: replace(
                fighter,
                hp=Decimal("1"),
                barrier=Decimal(0),
                barrier_remaining=0,
                ward_charges=0,
                ward_remaining=0,
                protection_layers=0,
                defending=False,
            )
            if key == round_key
            else replace(fighter, stats=replace(fighter.stats, attack=Decimal("10000")))
            if key == manual_key
            else fighter
            for key, fighter in combat.fighters.items()
        }
        order = (manual_key,) + tuple(key for key in combat.order if key != manual_key)
        combat = replace(combat, fighters=fighters, order=order, turn_index=0)
        persisted.combat_snapshot = encode(combat)
        persisted.state_version = combat.version
        manual_member = await session.scalar(
            select(PvpveCollisionMember).where(
                PvpveCollisionMember.collision_id == collision.id,
                PvpveCollisionMember.character_id != round_member.character_id,
            )
        )
        target_id = combat.fighters[round_key].id

    await service.action(
        manual_actor,
        manual_member.game_activity_id,
        combat.version,
        "attack",
        target_id=target_id,
    )

    async with database[1]() as session:
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == prepared.round_id)
        )
        activity = await session.get(GameActivity, round_member.game_activity_id)
        member = await session.get(
            PvpveCollisionMember, (collision.id, round_member.character_id)
        )
        assert state is not None and state.status == "defeated"
        assert state.end_reason == "pvpve_defeat"
        assert activity is not None and activity.status == "failed"
        assert member is not None and member.status == "defeated"
        assert member.result_acknowledged is True
        previous = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == prepared.round_id,
                HuntRoundEncounter.ordinal == 1,
            )
        )
        future = await session.scalar(
            select(HuntRoundEncounter.id).where(
                HuntRoundEncounter.round_id == prepared.round_id,
                HuntRoundEncounter.ordinal > 1,
            )
        )
        assert previous is not None and previous.status == "completed"
        assert future is None

    result = await service.resume(round_actor)
    assert result is not None and result.kind == "round_defeated"
    assert any("123" in line for line in result.reward_lines)

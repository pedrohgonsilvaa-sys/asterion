from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import func, select

from asterion.application.dungeons import DungeonService
from asterion.application.road import REGION, RUINS
from asterion.bot.combat_ui import DungeonCombatCallback
from asterion.bot.dungeon_handlers import dungeon_router
from asterion.bot.dungeon_ui import render_dungeons
from asterion.domain.combat import active_player_key
from asterion.domain.dungeons import rarity_with_pity
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import PlayerCombatantSpec
from asterion.domain.tdo_crypt import create_crypt_combat
from asterion.domain.tdo_galleries import (
    GALLERIES_FAMILY_ID,
    create_galleries_combat,
    gallery_encounter_specs,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CombatRecord,
    DungeonInvite,
    DungeonLobbyMember,
    DungeonMatchQueue,
    DungeonPityState,
    DungeonRun,
    DungeonRunMember,
    GameActivity,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_creation_ui import callback_update

D = Decimal


async def _seed_party(database, actors, *, family_id="dungeon.tdo.cripta_ocaso"):
    _engine, sessions = database
    location = RUINS if family_id == GALLERIES_FAMILY_ID else "Charneca da Fuligem"
    character_ids = [uuid4() for _ in actors]
    async with sessions.begin() as session:
        for index, (actor, character_id) in enumerate(
            zip(actors, character_ids, strict=True), start=1
        ):
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    id=character_id,
                    telegram_id=actor,
                    server_id="ocaso",
                    name=f"Hero{chr(96 + index)}",
                    race="remanescente",
                    character_class="sentinela",
                    stage="menu:ready",
                    ruleset_version="gdd-1.4.7-baseline-1.0",
                    level=8 if family_id == GALLERIES_FAMILY_ID else 4,
                    xp=0,
                    hp=D(702),
                    max_hp=D(702),
                    vigor=100,
                    max_vigor=100,
                    crowns=0,
                )
            )
            session.add(
                WorldState(character_id=character_id, region=REGION, location=location)
            )
            session.add(Unlock(character_id=character_id, unlock_id=family_id))
    return sessions, character_ids


async def _form_matchmade_party(service, actors, family_id):
    views = []
    for actor in actors:
        views.append(await service.join_matchmaking(actor, family_id, "stable"))
    latest = views[-1]
    assert latest is not None
    if latest.kind == "queue":
        latest = await service.open_entry_confirmation(
            actors[0], latest.lobby_id, latest.lobby_version
        )
    assert latest is not None and latest.kind == "confirming"
    version = latest.lobby_version
    lobby_id = latest.lobby_id
    for actor in actors:
        latest = await service.confirm_entry(actor, lobby_id, version, confirm=True)
    assert latest is not None and latest.run_id is not None
    return latest


@pytest.mark.asyncio
@pytest.mark.parametrize("group_size", (2, 3, 4))
async def test_matchmaking_forms_one_shared_run_and_one_shared_combat(
    database, group_size
):
    actors = tuple(781000 + index for index in range(group_size))
    sessions, character_ids = await _seed_party(database, actors)
    service = DungeonService(sessions, "ocaso")
    ready = await _form_matchmade_party(service, actors, "dungeon.tdo.cripta_ocaso")

    async with sessions() as session:
        run = await session.get(DungeonRun, ready.run_id)
        members = (
            await session.scalars(
                select(DungeonRunMember)
                .where(DungeonRunMember.run_id == ready.run_id)
                .order_by(DungeonRunMember.position)
            )
        ).all()
        active_shells = await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id.in_(character_ids),
                GameActivity.status == "active",
            )
        )
        assert run.initial_group_size == group_size
        assert len(members) == group_size
        assert active_shells == group_size
        assert all(member.vigor_reserved == 25 for member in members)

    first = await service.begin_encounter(actors[0], ready.run_id, ready.state_version)
    assert first is not None and first.kind == "combat"
    assert len([key for key in first.combat.fighters if key.startswith("member_")]) == group_size
    resumed = [await service.resume(actor) for actor in actors]
    assert all(view is not None and view.kind == "combat" for view in resumed)
    assert {view.combat.id for view in resumed} == {first.combat.id}
    assert {view.encounter_id for view in resumed} == {first.encounter_id}

    active_key = active_player_key(first.combat)
    assert active_key is not None and active_key.startswith("member_")
    active_position = int(active_key.removeprefix("member_"))
    actor_by_position = {position: actor for position, actor in enumerate(actors, start=1)}
    active_actor = actor_by_position[active_position]
    other_actor = next(actor for actor in actors if actor != active_actor)
    wrong_view = resumed[actors.index(other_actor)]
    rejected = await service.action(
        other_actor,
        first.run_id,
        wrong_view.activity_id,
        first.combat.version,
        "attack",
        "enemy",
    )
    assert rejected is not None and rejected.combat.version == first.combat.version

    active_view = resumed[active_position - 1]
    advanced = await service.action(
        active_actor,
        first.run_id,
        active_view.activity_id,
        first.combat.version,
        "attack",
        "enemy",
    )
    assert advanced is not None and advanced.combat.version == first.combat.version + 1


@pytest.mark.asyncio
async def test_group_lobby_invitation_acceptance_and_ready_check_reserve_vigor_last(database):
    actors = (781010, 781011)
    sessions, character_ids = await _seed_party(database, actors)
    service = DungeonService(sessions, "ocaso")
    lobby = await service.prepare_group(actors[0], "dungeon.tdo.cripta_ocaso", "stable")
    invite = await service.invite_by_name(
        actors[0], lobby.lobby_id, lobby.lobby_version, "Herob"
    )
    assert invite.reason == "invited:Herob"
    pending = await service.pending_invite(actors[1])
    accepted = await service.respond_invite(actors[1], pending.invite_id, accept=True)
    assert accepted.kind == "lobby"
    confirmation = await service.open_entry_confirmation(
        actors[0], lobby.lobby_id, accepted.lobby_version
    )
    assert confirmation.kind == "confirming"
    waiting = await service.confirm_entry(
        actors[0], confirmation.lobby_id, confirmation.lobby_version, confirm=True
    )
    assert waiting.kind == "confirming"
    async with sessions() as session:
        characters = (
            await session.scalars(select(Character).where(Character.id.in_(character_ids)))
        ).all()
        assert sorted(character.vigor for character in characters) == [100, 100]
    entered = await service.confirm_entry(
        actors[1], confirmation.lobby_id, confirmation.lobby_version, confirm=True
    )
    assert entered.run_id is not None and entered.kind == "ready"
    async with sessions() as session:
        characters = (
            await session.scalars(select(Character).where(Character.id.in_(character_ids)))
        ).all()
        assert sorted(character.vigor for character in characters) == [75, 75]


@pytest.mark.asyncio
async def test_invitation_rechecks_eligibility_before_acceptance(database):
    actors = (781012, 781013)
    sessions, character_ids = await _seed_party(database, actors)
    service = DungeonService(sessions, "ocaso")
    lobby = await service.prepare_group(actors[0], "dungeon.tdo.cripta_ocaso", "stable")
    invited = await service.invite_by_name(
        actors[0], lobby.lobby_id, lobby.lobby_version, "Herob"
    )
    assert invited.reason == "invited:Herob"
    pending = await service.pending_invite(actors[1])

    async with sessions.begin() as session:
        unlock = await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character_ids[1],
                Unlock.unlock_id == "dungeon.tdo.cripta_ocaso",
            )
        )
        await session.delete(unlock)

    response = await service.respond_invite(actors[1], pending.invite_id, accept=True)
    assert response.kind == "invite" and response.reason == "discovery"
    async with sessions() as session:
        invitation = await session.get(DungeonInvite, pending.invite_id)
        member = await session.scalar(
            select(DungeonLobbyMember).where(
                DungeonLobbyMember.lobby_id == lobby.lobby_id,
                DungeonLobbyMember.character_id == character_ids[1],
            )
        )
        characters = (
            await session.scalars(
                select(Character).where(Character.id.in_(character_ids))
            )
        ).all()
        assert invitation.status == "expired"
        assert member is None
        assert all(character.vigor == 100 for character in characters)


@pytest.mark.asyncio
async def test_matchmaking_keeps_difficulty_queues_separate_and_cancellable(database):
    actors = (781014, 781015)
    sessions, character_ids = await _seed_party(database, actors)
    service = DungeonService(sessions, "ocaso")
    async with sessions.begin() as session:
        for character_id in character_ids:
            session.add(
                Unlock(
                    character_id=character_id,
                    unlock_id="dungeon.tdo.cripta_ocaso.first_clear.stable",
                )
            )
    stable = await service.join_matchmaking(
        actors[0], "dungeon.tdo.cripta_ocaso", "stable"
    )
    fractured = await service.join_matchmaking(
        actors[1], "dungeon.tdo.cripta_ocaso", "fractured"
    )
    assert stable.lobby_id != fractured.lobby_id
    assert fractured.difficulty == "fractured"
    left = await service.cancel_queue_or_lobby(
        actors[0], stable.lobby_id, stable.lobby_version
    )
    assert left.kind == "cancelled"
    still_waiting = await service.resume(actors[1])
    assert still_waiting.kind == "queue"
    async with sessions() as session:
        first_row = await session.get(DungeonMatchQueue, character_ids[0])
        second_row = await session.get(DungeonMatchQueue, character_ids[1])
        assert first_row.status == "cancelled"
        assert second_row.status == "queued"


def test_gallery_has_five_canonical_encounters_and_group_scaled_boss():
    assert len(gallery_encounter_specs(1, "stable", 1, 9)) == 1
    assert len(gallery_encounter_specs(2, "stable", 1, 9)) == 2
    assert len(gallery_encounter_specs(3, "stable", 1, 9)) == 1
    conductors = gallery_encounter_specs(4, "stable", 1, 9)
    assert [spec.creature.creature_id for spec in conductors] == [
        "preceptor_rachado",
        "condutor_guarda",
        "condutor_guarda",
    ]
    assert all(
        not spec.variant
        for ordinal in range(1, 6)
        for spec in gallery_encounter_specs(ordinal, "stable", 1, 9)
    )

    solo = create_galleries_combat(
        uuid4(),
        name="Solo",
        character_class="sentinela",
        race="remanescente",
        hp=D(702),
        level=8,
        difficulty="stable",
        reference_level=9,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=5,
        run_seed="gallery-group-scaling",
        initial_group_size=1,
    )
    four = create_galleries_combat(
        uuid4(),
        name="Party",
        character_class="sentinela",
        race="remanescente",
        hp=D(702),
        level=8,
        difficulty="stable",
        reference_level=9,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=5,
        run_seed="gallery-group-scaling",
        initial_group_size=4,
    )
    solo_boss = solo.fighters["enemy"]
    group_boss = four.fighters["enemy"]
    assert float(group_boss.stats.hp / solo_boss.stats.hp) == pytest.approx(3.34)
    assert float(group_boss.stats.attack / solo_boss.stats.attack) == pytest.approx(1.21)


@pytest.mark.parametrize("ordinal", range(1, 6))
def test_crypt_encounters_use_one_shared_multiplayer_combat(ordinal):
    equipment = EquipmentConfigurationSnapshot(0)
    party = tuple(
        PlayerCombatantSpec(
            f"member_{position}",
            f"character-{position}",
            f"Hero{chr(96 + position)}",
            "sentinela",
            "remanescente",
            8,
            D(702),
            equipment,
            (),
        )
        for position in range(1, 5)
    )
    combat = create_crypt_combat(
        uuid4(),
        name="Heroa",
        character_class="sentinela",
        race="remanescente",
        hp=D(702),
        level=8,
        difficulty="stable",
        equipment=equipment,
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"crypt-party-{ordinal}",
        initial_group_size=4,
        party=party,
    )
    assert combat.party_mode
    assert all(f"member_{position}" in combat.fighters for position in range(1, 5))
    assert combat.configuration_snapshot["dungeon"]["initial_group_size"] == 4
    assert combat.variant is None
    if ordinal == 4:
        assert all(
            not combat.fighters[f"tomb_{index}"].takes_turn for index in range(1, 4)
        )
        assert len(combat.stat_auras) == 1
    if ordinal == 5:
        assert combat.pressure_start_opportunity == 12
        assert combat.pressure_cap == 5


@pytest.mark.asyncio
async def test_brazier_revives_every_member_and_group_abandon_refunds_each_member(database):
    actors = (781020, 781021)
    sessions, character_ids = await _seed_party(database, actors)
    service = DungeonService(sessions, "ocaso")
    ready = await _form_matchmade_party(service, actors, "dungeon.tdo.cripta_ocaso")

    async with sessions.begin() as session:
        run = await session.get(DungeonRun, ready.run_id)
        run.has_brazier = True
        run.current_encounter_ordinal = 4
        run.progress = {**run.progress, "awaiting_brazier": True}
        members = (
            await session.scalars(
                select(DungeonRunMember)
                .where(DungeonRunMember.run_id == ready.run_id)
                .order_by(DungeonRunMember.position)
            )
        ).all()
        member = members[-1]
        member.status = "defeated"
        member.hp = D(0)
        character = await session.get(Character, member.character_id)
        character.hp = D(0)
    brazier = await service.activate_brazier(actors[0], ready.run_id, ready.state_version)
    assert brazier.kind == "ready"
    async with sessions() as session:
        members = (
            await session.scalars(
                select(DungeonRunMember).where(DungeonRunMember.run_id == ready.run_id)
            )
        ).all()
        characters = (
            await session.scalars(select(Character).where(Character.id.in_(character_ids)))
        ).all()
        assert all(member.status == "active" and member.hp == member.max_hp for member in members)
        assert all(character.hp == character.max_hp for character in characters)

    votes = await service.abandon(actors[0], ready.run_id, brazier.state_version)
    assert votes.kind == "abandon_pending"
    failed = await service.abandon(actors[1], ready.run_id, votes.state_version)
    assert failed.kind == "failed"
    async with sessions() as session:
        run = await session.get(DungeonRun, ready.run_id)
        members = (
            await session.scalars(
                select(DungeonRunMember).where(DungeonRunMember.run_id == ready.run_id)
            )
        ).all()
        characters = (
            await session.scalars(select(Character).where(Character.id.in_(character_ids)))
        ).all()
        assert run.status == "failed"
        assert all(member.vigor_reserved == 0 and member.vigor_refunded for member in members)
        assert all(character.vigor == 100 for character in characters)


async def _force_party_wipe(sessions, run_id, fight):
    async with sessions.begin() as session:
        record = await session.get(CombatRecord, fight.encounter_id)
        state = decode(record.snapshot, record.id, fight.combat.ruleset, fight.combat.version)
        enemy = state.fighters["enemy"]
        enemy.stats = replace(enemy.stats, hp=D(100000), attack=D(100000))
        enemy.hp = enemy.stats.hp
        for key in ("member_1", "member_2"):
            state.fighters[key].hp = D(1)
        record.snapshot = encode(state)


@pytest.mark.asyncio
async def test_individually_defeated_member_spectates_while_other_member_continues(database):
    actors = (781030, 781031)
    sessions, character_ids = await _seed_party(database, actors)
    service = DungeonService(sessions, "ocaso")
    ready = await _form_matchmade_party(service, actors, "dungeon.tdo.cripta_ocaso")
    fight = await service.begin_encounter(actors[0], ready.run_id, ready.state_version)
    await _force_party_wipe(sessions, ready.run_id, fight)

    views = [await service.resume(actor) for actor in actors]
    for _ in range(4):
        combat = next(view.combat for view in views if view is not None)
        active_key = active_player_key(combat)
        assert active_key is not None
        active_position = int(active_key.removeprefix("member_"))
        active_actor = actors[active_position - 1]
        active_view = views[active_position - 1]
        next_view = await service.action(
            active_actor,
            ready.run_id,
            active_view.activity_id,
            combat.version,
            "attack",
            "enemy",
        )
        views = [await service.resume(actor) for actor in actors]
        if any(view.member_status == "defeated" for view in views if view is not None):
            break
        assert next_view is not None

    defeated_position = next(
        index for index, view in enumerate(views) if view.member_status == "defeated"
    )
    defeated_actor = actors[defeated_position]
    defeated_view = views[defeated_position]
    assert defeated_view.kind == "combat"
    assert defeated_view.combat_actor_key is None
    rejected = await service.action(
        defeated_actor,
        ready.run_id,
        defeated_view.activity_id,
        defeated_view.combat.version,
        "attack",
        "enemy",
    )
    assert rejected is not None and rejected.kind == "stale"
    active_view = views[1 - defeated_position]
    assert active_view.combat.version == defeated_view.combat.version
    async with sessions() as session:
        members = (
            await session.scalars(
                select(DungeonRunMember)
                .where(DungeonRunMember.run_id == ready.run_id)
                .order_by(DungeonRunMember.position)
            )
        ).all()
        assert members[defeated_position].status == "defeated"
        assert members[1 - defeated_position].status == "active"


@pytest.mark.asyncio
@pytest.mark.parametrize("brazier_active", (False, True))
async def test_party_wipe_refunds_or_retries_as_a_unit(database, brazier_active):
    actors = (781040, 781041)
    sessions, character_ids = await _seed_party(database, actors)
    service = DungeonService(sessions, "ocaso")
    ready = await _form_matchmade_party(service, actors, "dungeon.tdo.cripta_ocaso")
    async with sessions.begin() as session:
        run = await session.get(DungeonRun, ready.run_id)
        run.has_brazier = brazier_active
        run.brazier_activated = brazier_active
        run.active_checkpoint_encounter = 1 if brazier_active else None
    fight = await service.begin_encounter(actors[0], ready.run_id, ready.state_version)
    await _force_party_wipe(sessions, ready.run_id, fight)

    views = [await service.resume(actor) for actor in actors]
    result = None
    for _ in range(8):
        combat = next(view.combat for view in views if view is not None)
        active_key = active_player_key(combat)
        assert active_key is not None
        active_position = int(active_key.removeprefix("member_"))
        active_actor = actors[active_position - 1]
        active_view = views[active_position - 1]
        result = await service.action(
            active_actor,
            ready.run_id,
            active_view.activity_id,
            combat.version,
            "attack",
            "enemy",
        )
        if result.kind in {"failed", "ready", "retry"}:
            break
        views = [await service.resume(actor) for actor in actors]

    assert result is not None
    async with sessions() as session:
        run = await session.get(DungeonRun, ready.run_id)
        members = (
            await session.scalars(
                select(DungeonRunMember)
                .where(DungeonRunMember.run_id == ready.run_id)
                .order_by(DungeonRunMember.position)
            )
        ).all()
        characters = (
            await session.scalars(select(Character).where(Character.id.in_(character_ids)))
        ).all()
        if brazier_active:
            assert run.status == "active"
            assert result.kind == "retry"
            assert run.progress["retry_available"] is True
            assert all(
                member.status == "active" and member.hp == member.max_hp
                for member in members
            )
            assert all(
                member.vigor_reserved == 25 and not member.vigor_refunded
                for member in members
            )
        else:
            assert run.status == "failed"
            assert result.kind == "failed"
            assert all(member.status == "left" and member.vigor_refunded for member in members)
            assert all(character.vigor == 100 for character in characters)
    if brazier_active:
        retried = await service.retry(actors[0], ready.run_id, result.state_version)
        assert retried.kind == "ready"
        assert retried.run_id == ready.run_id


@pytest.mark.asyncio
async def test_group_galleries_attack_callback_routes_to_shared_combat(database):
    actors = (781050, 781051)
    sessions, _character_ids = await _seed_party(
        database, actors, family_id=GALLERIES_FAMILY_ID
    )
    service = DungeonService(sessions, "ocaso")
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(dungeon_router(service, {}))

    async def click(actor, callback, update_id):
        await dispatcher.feed_raw_update(
            bot,
            callback_update(callback, update_id=update_id, actor=actor),
        )

    await click(actors[0], "dungeon:queue:g:s", 781052)
    await click(actors[1], "dungeon:queue:g:s", 781053)
    queue = await service.resume(actors[0])
    confirm_group = next(
        button
        for row in render_dungeons(queue).keyboard.inline_keyboard
        for button in row
        if button.text == "Confirmar Grupo"
    )
    await click(actors[0], confirm_group.callback_data, 781054)
    confirming = await service.resume(actors[0])
    assert confirming.kind == "confirming"
    ready_button = next(
        button
        for row in render_dungeons(confirming).keyboard.inline_keyboard
        for button in row
        if button.text == "Confirmar Entrada"
    )
    await click(actors[0], ready_button.callback_data, 781055)
    confirming_other = await service.resume(actors[1])
    await click(
        actors[1],
        next(
            button.callback_data
            for row in render_dungeons(confirming_other).keyboard.inline_keyboard
            for button in row
            if button.text == "Confirmar Entrada"
        ),
        781056,
    )
    ready = await service.resume(actors[0])
    assert ready.kind == "ready" and ready.run_id is not None
    assert ready.vigor == 75
    enter = next(
        button
        for row in render_dungeons(ready).keyboard.inline_keyboard
        for button in row
        if button.text == "⚔️ Entrar no Encontro"
    )
    await click(actors[0], enter.callback_data, 781057)
    fight = await service.resume(actors[0])
    assert fight.kind == "combat"
    actor_key = active_player_key(fight.combat)
    active_position = int(actor_key.removeprefix("member_"))
    active_actor = actors[active_position - 1]
    active_view = await service.resume(active_actor)
    attack = next(
        button
        for row in render_dungeons(active_view).keyboard.inline_keyboard
        for button in row
        if button.text == "Atacar"
    )
    assert len(attack.callback_data.encode("utf-8")) <= 64
    callback = DungeonCombatCallback.unpack(attack.callback_data)
    assert callback.run == ready.run_id.hex[:16]
    assert callback.activity_id == active_view.activity_id

    await click(active_actor, attack.callback_data, 781058)

    resumed = await service.resume(active_actor)
    other = await service.resume(actors[1 - (active_position - 1)])
    assert resumed.kind == "combat" and other.kind == "combat"
    assert resumed.combat.id == other.combat.id == fight.combat.id
    assert resumed.combat.version == other.combat.version == fight.combat.version + 1


@pytest.mark.asyncio
async def test_group_settlement_has_individual_contribution_first_clear_and_pity(database):
    actors = (781060, 781061)
    sessions, character_ids = await _seed_party(database, actors)
    service = DungeonService(sessions, "ocaso")
    ready = await _form_matchmade_party(service, actors, "dungeon.tdo.cripta_ocaso")
    async with sessions.begin() as session:
        run = await session.get(DungeonRun, ready.run_id)
        members = (
            await session.scalars(
                select(DungeonRunMember)
                .where(DungeonRunMember.run_id == ready.run_id)
                .order_by(DungeonRunMember.position)
            )
        ).all()
        characters = (
            await session.scalars(
                select(Character)
                .where(Character.id.in_(character_ids))
                .order_by(Character.id)
            )
        ).all()
        members[0].contribution = {"points": "100", "actions": 4}
        members[1].contribution = {"points": "50", "actions": 2}
        run.progress = {
            **run.progress,
            "internal_rewards": [[4, "common"], [5, "uncommon"]],
        }
        first_clear = "dungeon.tdo.cripta_ocaso.first_clear.stable"
        session.add(Unlock(character_id=characters[0].id, unlock_id=first_clear))
        by_id = {character.id: character for character in characters}
        await service._settle_run(session, characters[0], run, members, by_id)
        saved_reward_lines = dict(run.progress["reward_lines_by_character"])
        await service._settle_run(session, characters[0], run, members, by_id)
        assert run.progress["reward_lines_by_character"] == saved_reward_lines

    async with sessions() as session:
        events = (
            await session.scalars(
                select(RewardEvent).where(RewardEvent.character_id.in_(character_ids))
            )
        ).all()
        assert len(events) == 2
        assert len({event.source_id for event in events}) == 2
        components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id.in_([event.id for event in events]),
                    RewardComponent.kind == "xp",
                )
            )
        ).all()
        assert sorted(component.payload["participation_factor"] for component in components) == [
            "0.70",
            "1",
        ]
        pity = (
            await session.scalars(
                select(DungeonPityState).where(
                    DungeonPityState.character_id.in_(character_ids)
                )
            )
        ).all()
        assert len(pity) == 2
        expected_pity = {
            member.character_id: rarity_with_pity(
                f"{run.seed}:member:{member.character_id.hex}",
                run.difficulty,
                0,
                0,
            )[1:]
            for member in members
        }
        assert {
            state.character_id: (state.legendary_plus_points, state.mythic_points)
            for state in pity
        } == expected_pity
        clear_unlocks = (
            await session.scalars(
                select(Unlock).where(
                    Unlock.character_id.in_(character_ids),
                    Unlock.unlock_id == "dungeon.tdo.cripta_ocaso.first_clear.stable",
                )
            )
        ).all()
        assert len(clear_unlocks) == 2

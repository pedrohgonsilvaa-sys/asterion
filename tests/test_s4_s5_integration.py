from copy import deepcopy
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.groups import GroupService
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, RUINS, RoadService
from asterion.application.s4 import S4_ID, S4_REWARD_SOURCE, S4Service
from asterion.application.s5 import (
    S5_CODEX_ENTRY,
    S5_CREATURES,
    S5_ID,
    S5_REWARD_SOURCE,
    S5Service,
    choose_s5_creature,
)
from asterion.domain.arts import FIRST_CLASS_ART_IDS
from asterion.domain.road import RUINS_ROUTE_UNLOCK
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Character,
    CharacterActiveArtSlot,
    CharacterTalentChoice,
    CodexEntry,
    Encounter,
    GameActivity,
    HuntContext,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.weapon_metadata import add_compatible_weapon_for_arts
from tests.test_s3_p4_integration import _seed_campaign


def _terminal(result: str):
    def finish(combat, action, *, effect_id: str | None = None):
        assert effect_id is None
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = result
        if result == "defeat":
            updated.fighters["player"].hp = Decimal(0)
        return updated

    return finish


async def _seed_p4(database, actor: int, *, level: int = 8):
    character_id, sessions = await _seed_campaign(database, actor, level=level)
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id="P4",
                title="Pedras que Ainda Vigiam",
                status="completed",
                step=6,
                content_version="tdo-1.0.11",
                progress={"completed": True},
            )
        )
    return character_id, sessions


async def _set_location(sessions, character_id, location: str):
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = "Terras do Ocaso"
        world.location = location


async def _start_s4(actor: int, service: S4Service, sessions, character_id):
    accepted = await service.accept(actor)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    await _set_location(sessions, character_id, RUINS)
    view = accepted
    for point in ("s4.watch_point.3", "s4.watch_point.1", "s4.watch_point.2"):
        view = await service.action(actor, view.state_version, "watch", point)
    assert view is not None and view.step == 2
    view = await service.action(actor, view.state_version, "orientation")
    assert view is not None and view.step == 3 and view.kind == "combat"
    return view


async def _start_s5(actor: int, service: S5Service, sessions, character_id):
    accepted = await service.accept(actor)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    await _set_location(sessions, character_id, RUINS)
    view = await service.action(actor, accepted.state_version, "investigate")
    assert view is not None and view.step == 2
    view = await service.action(actor, view.state_version, "light_point", "s5.light_point.1")
    duplicate = await service.action(actor, view.state_version, "light_point", "s5.light_point.1")
    assert duplicate is not None and duplicate.step == 2
    view = await service.action(actor, duplicate.state_version, "light_point", "s5.light_point.2")
    assert view is not None and view.step == 3 and view.kind == "combat"
    return view


@pytest.mark.asyncio
async def test_s4_s5_eligibility_is_independent_and_offers_do_not_create_quests(database):
    actor = 998601
    _, sessions = await _seed_campaign(database, actor, level=7)
    s4 = S4Service(sessions, "ocaso")
    s5 = S5Service(sessions, "ocaso")
    assert not (await s4.offer(actor)).available
    assert not (await s5.offer(actor)).available

    actor += 1
    _, sessions = await _seed_p4(database, actor, level=6)
    s4 = S4Service(sessions, "ocaso")
    s5 = S5Service(sessions, "ocaso")
    assert not (await s4.offer(actor)).available
    assert not (await s5.offer(actor)).available

    actor += 1
    character_id, sessions = await _seed_p4(database, actor, level=7)
    s4 = S4Service(sessions, "ocaso")
    s5 = S5Service(sessions, "ocaso")
    offer4 = await s4.offer(actor)
    offer5 = await s5.offer(actor)
    assert offer4.available and offer5 is not None and not offer5.available
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == S4_ID)
        ) is None
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == S5_ID)
        ) is None


@pytest.mark.asyncio
async def test_level_7_s4_uses_existing_ruins_route_without_unlocking_normal_gameplay(database):
    actor = 998609
    character_id, sessions = await _seed_p4(database, actor, level=7)
    async with sessions.begin() as session:
        session.add(LocationDiscovery(
            character_id=character_id, location_id="tdo.location.ruinas_do_vigia"
        ))
        session.add(Unlock(character_id=character_id, unlock_id=RUINS_ROUTE_UNLOCK))

    s4 = S4Service(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")
    assert await road.travel_route(actor, CHARNECA) is not None
    assert await road.travel_route(actor, BOSQUE) is not None
    assert await road.travel_route(actor, RUINS) is None
    assert await road.travel_route(actor, CHARNECA) is not None
    assert await road.travel_route(actor, REFUGE) is not None

    offer = await s4.offer(actor)
    accepted = await s4.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active"
    assert await road.travel_route(actor, CHARNECA) is not None
    bosque = await road.travel_route(actor, BOSQUE)
    assert bosque is not None and RUINS in bosque.route_destinations
    ruins = await road.travel_route(actor, RUINS)
    assert ruins is not None and ruins.location == RUINS
    assert await road.start_hunt(actor) is None


@pytest.mark.asyncio
async def test_s4_watch_points_combat_checkpoint_reward_and_reconnect(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998604
    character_id, sessions = await _seed_p4(database, actor)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.selected_path = "bastiao"
        await add_compatible_weapon_for_arts(
            session,
            character_id,
            (FIRST_CLASS_ART_IDS["sentinela"],),
        )
        session.add(CharacterActiveArtSlot(
            character_id=character_id, slot=1, art_id=FIRST_CLASS_ART_IDS["sentinela"]
        ))
        session.add(CharacterTalentChoice(
            character_id=character_id, point_slot=1, talent_id="talent.sentinela.aco_desperto"
        ))
    service = S4Service(sessions, "ocaso")
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.step == 1
    await _set_location(sessions, character_id, RUINS)

    first = await service.action(actor, accepted.state_version, "watch", "s4.watch_point.2")
    assert first is not None and first.step == 1
    duplicate = await service.action(actor, first.state_version, "watch", "s4.watch_point.2")
    assert duplicate is not None and duplicate.step == 1
    second = await service.action(actor, duplicate.state_version, "watch", "s4.watch_point.1")
    combat = await service.action(actor, second.state_version, "watch", "s4.watch_point.3")
    assert combat is not None and combat.step == 2
    combat = await service.action(actor, combat.state_version, "orientation")
    assert combat is not None and combat.kind == "combat" and combat.combat is not None
    assert combat.combat.fighters["enemy"].name == "Vigia Rachado"
    assert combat.combat.fighters["enemy"].level == 7
    assert combat.combat.variant is None

    async with sessions() as session:
        activity = await session.get(GameActivity, combat.activity_id)
        assert activity is not None
        encounter = await session.scalar(
            select(Encounter).where(Encounter.game_activity_id == activity.id)
        )
        from asterion.infrastructure.db.combat_codec import decode
        from asterion.infrastructure.db.models import CombatRecord

        record = await session.scalar(
            select(CombatRecord).where(CombatRecord.encounter_id == encounter.id)
        )
        assert record is not None
        snapshot = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        assert snapshot.configuration_snapshot["selected_path"] == "bastiao"
        assert snapshot.configuration_snapshot["talents"] == [
            {"point_slot": 1, "talent_id": "talent.sentinela.aco_desperto"}
        ]
        assert (
            snapshot.configuration_snapshot["active_arts"][0]["art_id"]
            == FIRST_CLASS_ART_IDS["sentinela"]
        )
        assert await session.scalar(
            select(HuntContext.id).where(HuntContext.game_activity_id == activity.id)
        ) is None
        assert (await session.get(Character, character_id)).vigor == 61
    resumed = await service.resume(actor)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id, combat.encounter_id, combat.combat_id
    )

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await service.action_combat(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert victory is not None and victory.step == 4
    await service.action(actor, victory.state_version, "turn_point")
    step5 = await service.resume(actor)
    assert step5 is not None and step5.step == 5
    step6 = await service.action(actor, step5.state_version, "examine")
    assert step6 is not None and step6.step == 6
    await _set_location(sessions, character_id, REFUGE)
    report = await service.resume(actor)
    assert report is not None and report.kind == "report"
    complete = await service.action(actor, report.state_version, "report")
    assert complete is not None and complete.status == "completed"
    await service.action(actor, report.state_version, "report")

    async with sessions() as session:
        events = (
            await session.scalars(select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S4_REWARD_SOURCE,
            ))
        ).all()
        assert len(events) == 1
        components = (
            await session.scalars(select(RewardComponent).where(
                RewardComponent.reward_event_id == events[0].id
            ))
        ).all()
        assert {(row.kind, row.quantity, row.item_id) for row in components} == {
            ("xp", 3990, None),
            ("crowns", 150, None),
            ("material", 2, "material.tdo.ferro_de_fuligem"),
            ("material", 1, "material.tdo.couro_escoriado"),
            ("material", 1, "material.tdo.residuo_ocaso"),
        }
        assert await session.scalar(select(RewardEvent.id).where(
            RewardEvent.character_id == character_id,
            RewardEvent.source_id == f"{S4_REWARD_SOURCE}:enemy-xp:{combat.activity_id}",
        )) is not None
        assert await session.scalar(select(func.count()).select_from(BestiaryEntry).where(
            BestiaryEntry.character_id == character_id,
            BestiaryEntry.creature_id == "vigia_rachado",
        )) == 1
        assert await session.scalar(select(CodexEntry.id).where(
            CodexEntry.character_id == character_id
        )) is None


@pytest.mark.asyncio
async def test_s4_defeat_retries_same_vigia_without_advancing_or_rerolling(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998605
    character_id, sessions = await _seed_p4(database, actor)
    service = S4Service(sessions, "ocaso")
    view = await _start_s4(actor, service, sessions, character_id)
    first_activity = view.activity_id
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeat = await service.action_combat(
        actor, view.activity_id, view.activity_state_version, "attack"
    )
    assert defeat is not None and defeat.step == 3 and defeat.kind == "recovery"
    assert defeat.progress["awaiting_retry"] is True
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and character.hp == character.max_hp
        assert character.vigor == 61
        failed = await session.get(GameActivity, first_activity)
        assert failed is not None and failed.status == "failed"
    await _set_location(sessions, character_id, RUINS)
    retry = await service.retry(actor, defeat.state_version)
    assert retry is not None and retry.kind == "combat" and retry.step == 3
    assert retry.activity_id != first_activity
    assert retry.combat.fighters["enemy"].name == "Vigia Rachado"
    assert retry.combat.fighters["enemy"].level == 7
    assert retry.combat.variant is None


@pytest.mark.asyncio
async def test_s4_abandon_and_reaccept_resets_only_transient_progress(database):
    actor = 998606
    character_id, sessions = await _seed_p4(database, actor)
    service = S4Service(sessions, "ocaso")
    accepted = await service.accept(actor)
    await _set_location(sessions, character_id, RUINS)
    progress = await service.action(actor, accepted.state_version, "watch", "s4.watch_point.1")
    abandoned = await service.abandon(actor, progress.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    await _set_location(sessions, character_id, REFUGE)
    offer = await service.offer(actor)
    assert offer is not None and offer.reacceptable
    reaccepted = await service.accept(actor, offer.state_version, reaccept=True)
    assert reaccepted is not None and reaccepted.status == "active" and reaccepted.step == 1
    assert reaccepted.progress == {"watch_points": []}
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Quest).where(
            Quest.character_id == character_id, Quest.quest_id == S4_ID
        )) == 1


@pytest.mark.asyncio
async def test_s5_deterministic_encounter_defeat_retry_reward_and_codex(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998607
    character_id, sessions = await _seed_p4(database, actor, level=8)
    service = S5Service(sessions, "ocaso")
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    combat = await _start_s5(actor, service, sessions, character_id)
    creature_id = choose_s5_creature(character_id)
    assert combat.progress["encounter_creature_id"] == creature_id
    assert combat.combat.fighters["enemy"].name == S5_CREATURES[creature_id].name
    assert combat.combat.fighters["enemy"].level == 8
    assert combat.combat.variant is None
    resumed = await service.resume(actor)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id, combat.encounter_id, combat.combat_id
    )
    async with sessions() as session:
        assert await session.scalar(select(HuntContext.id).where(
            HuntContext.game_activity_id == combat.activity_id
        )) is None
        assert (await session.get(Character, character_id)).vigor == 61

    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeat = await service.action_combat(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert defeat is not None and defeat.kind == "recovery" and defeat.step == 3
    await _set_location(sessions, character_id, RUINS)
    retry = await service.retry(actor, defeat.state_version)
    assert retry is not None and retry.kind == "combat"
    assert retry.progress["encounter_creature_id"] == creature_id
    assert retry.activity_id != combat.activity_id
    assert retry.combat.fighters["enemy"].name == S5_CREATURES[creature_id].name

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await service.action_combat(
        actor, retry.activity_id, retry.activity_state_version, "attack"
    )
    assert victory is not None and victory.step == 4
    record = await service.action(actor, victory.state_version, "record")
    assert record is not None and record.step == 5
    assert record.progress["direction_observed"] and record.progress["duration_observed"]
    await _set_location(sessions, character_id, REFUGE)
    report = await service.resume(actor)
    complete = await service.action(actor, report.state_version, "report")
    assert complete is not None and complete.status == "completed"
    await service.action(actor, report.state_version, "report")

    async with sessions() as session:
        events = (
            await session.scalars(select(RewardEvent).where(
                RewardEvent.character_id == character_id, RewardEvent.source_id == S5_REWARD_SOURCE
            ))
        ).all()
        assert len(events) == 1
        components = (
            await session.scalars(select(RewardComponent).where(
                RewardComponent.reward_event_id == events[0].id
            ))
        ).all()
        assert {(row.kind, row.quantity, row.item_id) for row in components} == {
            ("xp", 4480, None),
            ("crowns", 160, None),
            ("material", 1, "material.tdo.ferro_de_fuligem"),
            ("material", 1, "material.tdo.erva_cinzenta"),
            ("material", 2, "material.tdo.residuo_ocaso"),
        }
        assert await session.scalar(select(RewardEvent.id).where(
            RewardEvent.character_id == character_id,
            RewardEvent.source_id == f"{S5_REWARD_SOURCE}:enemy-xp:{retry.activity_id}",
        )) is not None
        assert await session.scalar(select(CodexEntry.id).where(
            CodexEntry.character_id == character_id, CodexEntry.entry_id == S5_CODEX_ENTRY
        )) is not None
        assert await session.scalar(select(func.count()).select_from(CodexEntry).where(
            CodexEntry.character_id == character_id
        )) == 1


@pytest.mark.asyncio
async def test_s5_offer_does_not_require_s4_and_reaccept_preserves_single_quest(database):
    actor = 998608
    character_id, sessions = await _seed_p4(database, actor, level=8)
    service = S5Service(sessions, "ocaso")
    offer = await service.offer(actor)
    accepted = await service.accept(actor, offer.state_version)
    await service.abandon(actor, accepted.state_version)
    again = await service.offer(actor)
    assert again is not None and again.reacceptable
    restarted = await service.accept(actor, again.state_version, reaccept=True)
    assert restarted is not None and restarted.status == "active" and restarted.step == 1
    assert restarted.progress == {"light_points": []}
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Quest).where(
            Quest.character_id == character_id, Quest.quest_id == S5_ID
        )) == 1


@pytest.mark.asyncio
async def test_s5_shares_lights_and_uses_confirmed_group_encounter(database, monkeypatch):
    import asterion.application.campaign_coop as campaign_coop
    from asterion.domain.combat import active_player_key

    actors = (998630, 998631)
    seeded = [await _seed_p4(database, actor, level=8) for actor in actors]
    character_ids = [row[0] for row in seeded]
    sessions = database[1]
    groups = GroupService(sessions, "ocaso")
    service = S5Service(sessions, "ocaso", groups=groups)
    accepted = [await service.accept(actor) for actor in actors]
    assert all(view is not None and view.status == "active" for view in accepted)

    group = await groups.create_group(actors[0])
    async with sessions() as session:
        invitee = await session.scalar(
            select(Character).where(Character.id == character_ids[1])
        )
        assert invitee is not None
        invitee_name = invitee.name
    invite = await groups.invite(
        actors[0], invitee_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )
    for character_id in character_ids:
        await _set_location(sessions, character_id, RUINS)

    view = await service.resume(actors[0])
    view = await service.action(actors[0], view.state_version, "investigate")
    companion = await service.resume(actors[1])
    assert view.step == companion.step == 2
    for light_point in ("s5.light_point.2", "s5.light_point.1"):
        view = await service.action(actors[0], view.state_version, "light_point", light_point)
    companion = await service.resume(actors[1])
    assert view.kind == "combat_pending" and view.group_size == 2
    assert companion.step == 3
    assert view.progress["encounter_creature_id"] == companion.progress["encounter_creature_id"]

    proposal = await service.propose_group_combat(actors[0], view.state_version)
    pending_view = await service.detail(actors[0])
    assert pending_view.kind == "combat_pending"
    assert pending_view.proposal_id == proposal.proposal_id
    invitee_proposals = await groups.activity_proposals(actors[1])
    pending = next(row for row in invitee_proposals if row.proposal_id == proposal.proposal_id)
    ready = await groups.respond_activity(
        actors[1], pending.proposal_id, expected_revision=pending.revision, accept=True
    )
    started = await service.start_group_combat(
        actors[0], ready.proposal_id, expected_revision=ready.revision
    )
    views = {actor: await service.resume(actor) for actor in actors}
    assert started.kind == "combat"
    assert len({views[actor].encounter_id for actor in actors}) == 1
    assert len({views[actor].activity_id for actor in actors}) == 2
    assert all(views[actor].combat == views[actors[0]].combat for actor in actors)

    def terminal_victory(combat, action, *, actor_key=None, target_id=None):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = "victory"
        return updated

    monkeypatch.setattr(campaign_coop, "act", terminal_victory)
    active_key = active_player_key(views[actors[0]].combat)
    current_actor = next(
        actor for actor in actors if views[actor].combat_actor_key == active_key
    )
    current = views[current_actor]
    resolved = await service.action_combat(
        current_actor,
        current.activity_id,
        current.activity_state_version,
        "attack",
    )
    assert resolved.step == 4 and resolved.progress["combat_result"] == "victory"
    for actor in actors:
        member_view = await service.resume(actor)
        assert member_view.step == 4

    async with sessions() as session:
        quests = (
            await session.scalars(
                select(Quest).where(
                    Quest.character_id.in_(character_ids), Quest.quest_id == S5_ID
                )
            )
        ).all()
        assert {row.progress["combat_result"] for row in quests} == {"victory"}
        rewards = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id.in_(character_ids),
                    RewardEvent.source_id.like(f"{S5_REWARD_SOURCE}:enemy-xp:%"),
                )
            )
        ).all()
        assert len(rewards) == 2


@pytest.mark.asyncio
async def test_s4_shares_watches_and_uses_confirmed_group_vigia_combat(database, monkeypatch):
    import asterion.application.campaign_coop as campaign_coop
    from asterion.domain.combat import active_player_key

    actors = (998620, 998621)
    seeded = [await _seed_p4(database, actor, level=7) for actor in actors]
    character_ids = [row[0] for row in seeded]
    sessions = database[1]
    groups = GroupService(sessions, "ocaso")
    service = S4Service(sessions, "ocaso", groups=groups)
    accepted = [await service.accept(actor) for actor in actors]
    assert all(view is not None and view.status == "active" for view in accepted)

    group = await groups.create_group(actors[0])
    async with sessions() as session:
        invitee = await session.scalar(
            select(Character).where(Character.id == character_ids[1])
        )
        assert invitee is not None
        invitee_name = invitee.name
    invite = await groups.invite(
        actors[0], invitee_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )
    for character_id in character_ids:
        await _set_location(sessions, character_id, RUINS)

    view = await service.resume(actors[0])
    for point in ("s4.watch_point.2", "s4.watch_point.3", "s4.watch_point.1"):
        view = await service.action(actors[0], view.state_version, "watch", point)
    companion = await service.resume(actors[1])
    assert view.step == companion.step == 2
    assert len(view.progress["watch_points"]) == 3
    assert len(companion.progress["watch_points"]) == 3
    view = await service.action(actors[0], view.state_version, "orientation")
    companion = await service.resume(actors[1])
    assert view.kind == "combat_pending" and view.group_size == 2
    assert companion.step == 3 and companion.progress["patrol_orientation_recorded"]

    proposal = await service.propose_group_combat(actors[0], view.state_version)
    pending_view = await service.detail(actors[0])
    assert pending_view.kind == "combat_pending"
    assert pending_view.proposal_id == proposal.proposal_id
    invitee_proposals = await groups.activity_proposals(actors[1])
    pending = next(row for row in invitee_proposals if row.proposal_id == proposal.proposal_id)
    ready = await groups.respond_activity(
        actors[1], pending.proposal_id, expected_revision=pending.revision, accept=True
    )
    started = await service.start_group_combat(
        actors[0], ready.proposal_id, expected_revision=ready.revision
    )
    views = {actor: await service.resume(actor) for actor in actors}
    assert started.kind == "combat"
    assert len({views[actor].encounter_id for actor in actors}) == 1
    assert len({views[actor].activity_id for actor in actors}) == 2
    assert all(views[actor].combat == views[actors[0]].combat for actor in actors)

    def terminal_victory(combat, action, *, actor_key=None, target_id=None):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = "victory"
        return updated

    monkeypatch.setattr(campaign_coop, "act", terminal_victory)
    active_key = active_player_key(views[actors[0]].combat)
    current_actor = next(
        actor for actor in actors if views[actor].combat_actor_key == active_key
    )
    current = views[current_actor]
    resolved = await service.action_combat(
        current_actor,
        current.activity_id,
        current.activity_state_version,
        "attack",
    )
    assert resolved.step == 4 and resolved.progress["combat_result"] == "victory"
    for actor in actors:
        member_view = await service.resume(actor)
        assert member_view.step == 4

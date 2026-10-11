import pytest
from sqlalchemy import func, select

from asterion.application.groups import GroupService
from asterion.application.p7 import REGION
from asterion.application.road import (
    VDE_BERCO,
    VDE_CLAUSTRO,
    RoadService,
)
from asterion.application.vde_missions import (
    BERCO_LOCATION_ID,
    BERCO_ROUTE_UNLOCK,
    CLAUSTRO,
    CLAUSTRO_LOCATION_ID,
    P11_ID,
    P11_REWARD_SOURCE,
    S11_ID,
    S11_REWARD_SOURCE,
    VDEMissionService,
)
from asterion.domain.combat import active_player_key
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    CampaignSharedEncounter,
    Character,
    CodexEntry,
    CodexFragment,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_p7_integration import _terminal
from tests.test_vde_p10_s10_claustro_integration import _seed_late_region


async def _seed_claustro(
    database,
    actor: int,
    *,
    level: int,
    completed_p10: bool = True,
    discovered: bool = True,
):
    character_id, sessions = await _seed_late_region(
        database, actor, level=max(level, 18), p10=completed_p10
    )
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = REGION
        world.location = CLAUSTRO
        session.add(
            Unlock(
                character_id=character_id,
                unlock_id="route.vde.baixios_claustro",
            )
        )
        if discovered:
            session.add(
                LocationDiscovery(
                    character_id=character_id,
                    location_id=CLAUSTRO_LOCATION_ID,
                )
            )
    return character_id, sessions


def _reward_components(rows):
    return {(row.kind, row.quantity, row.item_id) for row in rows}


@pytest.mark.asyncio
async def test_s11_gate_sequence_bestiary_and_one_time_reward(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998801
    character_id, sessions = await _seed_claustro(database, actor, level=17)
    missions = VDEMissionService(sessions, "ocaso")

    undiscovered_actor = 998806
    _, undiscovered_sessions = await _seed_claustro(
        database, undiscovered_actor, level=18, discovered=False
    )
    undiscovered = await VDEMissionService(undiscovered_sessions, "ocaso").start(
        undiscovered_actor, S11_ID
    )
    assert undiscovered is not None and undiscovered.kind == "unavailable"

    blocked = await missions.start(actor, S11_ID)
    assert blocked is not None and blocked.kind == "unavailable"
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 18
    s11 = await missions.start(actor, S11_ID)
    assert s11 is not None and s11.status == "active" and s11.kind == "patrols"

    for point in ("a", "b"):
        s11 = await missions.examine(actor, S11_ID, s11.state_version, point)
    assert s11 is not None and s11.kind == "combat_start" and s11.step == 2
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    fight = await missions.start_solo_combat(actor, S11_ID, s11.state_version)
    assert fight is not None and fight.activity_id is not None and fight.combat is not None
    s11 = await missions.action_combat(
        actor, fight.activity_id, fight.combat.version, "attack"
    )
    assert s11 is not None and s11.kind == "return_place" and s11.step == 3
    async with sessions() as session:
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "vigia_enraizado",
            )
        ) is not None
        activity = await session.get(GameActivity, fight.activity_id)
        assert activity is not None and activity.content_id == "vde_s11_vigia_enraizado"

    s11 = await missions.advance(actor, S11_ID, s11.state_version, "return_place")
    assert s11 is not None and s11.kind == "fragments" and s11.step == 4
    for _ in range(3):
        s11 = await missions.advance(actor, S11_ID, s11.state_version, "fragment")
    assert s11 is not None and s11.kind == "report" and s11.step == 5
    old_version = s11.state_version
    s11 = await missions.advance(actor, S11_ID, old_version, "report")
    assert s11 is not None and s11.status == "completed"
    await missions.advance(actor, S11_ID, old_version, "report")

    async with sessions() as session:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S11_ID)
        )
        assert quest is not None and quest.status == "completed"
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S11_REWARD_SOURCE,
            )
        )
        assert event is not None
        rows = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
                )
            ).all()
        )
        assert _reward_components(rows) == {
            ("xp", 10990, None),
            ("crowns", 280, None),
            ("material", 1, "material.vde.ferro_enredado"),
            ("material", 1, "material.vde.erva_de_turfa"),
            ("material", 2, "material.vde.resina_enredada"),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S11_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "codex.fragment.vigia.rotinas_que_permanecem",
            )
        ) is not None


@pytest.mark.asyncio
async def test_p11_opens_berco_navigably_without_climax_activities(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998802
    character_id, sessions = await _seed_claustro(database, actor, level=18)
    missions = VDEMissionService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")

    no_p10_actor = 998807
    _, no_p10_sessions = await _seed_claustro(
        database, no_p10_actor, level=19, completed_p10=False
    )
    no_p10 = await VDEMissionService(no_p10_sessions, "ocaso").start(no_p10_actor, P11_ID)
    assert no_p10 is not None and no_p10.kind == "unavailable"

    initial_local = await road.resume(actor)
    assert initial_local is not None and VDE_BERCO not in initial_local.route_destinations
    blocked = await missions.start(actor, P11_ID)
    assert blocked is not None and blocked.kind == "unavailable"
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 19
    p11 = await missions.start(actor, P11_ID)
    assert p11 is not None and p11.status == "active" and p11.kind == "pressure_points"
    for point in ("a", "b", "c"):
        p11 = await missions.examine(actor, P11_ID, p11.state_version, point)
    assert p11 is not None and p11.kind == "clear_roots" and p11.step == 2
    p11 = await missions.advance(actor, P11_ID, p11.state_version, "roots")
    assert p11 is not None and p11.kind == "combat_start" and p11.step == 3
    assert "espécie não é identificada" in __import__(
        "asterion.bot.vde_missions_ui", fromlist=["render_vde_mission"]
    ).render_vde_mission(p11).text

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    fight = await missions.start_solo_combat(actor, P11_ID, p11.state_version)
    assert fight is not None and fight.activity_id is not None and fight.combat is not None
    p11 = await missions.action_combat(
        actor, fight.activity_id, fight.combat.version, "attack"
    )
    assert p11 is not None and p11.kind == "chamber" and p11.step == 4
    p11 = await missions.advance(actor, P11_ID, p11.state_version, "chamber")
    p11 = await missions.advance(actor, P11_ID, p11.state_version, "traces")
    p11 = await missions.advance(actor, P11_ID, p11.state_version, "convergence")
    assert p11 is not None and p11.kind == "open_berco" and p11.step == 7
    open_screen = __import__(
        "asterion.bot.vde_missions_ui", fromlist=["render_vde_mission"]
    ).render_vde_mission(p11)
    assert "A Matriarca não construiu" in open_screen.text
    assert "função" not in open_screen.text

    old_version = p11.state_version
    p11 = await missions.advance(actor, P11_ID, old_version, "open_berco")
    assert p11 is not None and p11.status == "completed"
    await missions.advance(actor, P11_ID, old_version, "open_berco")
    resumed = await VDEMissionService(sessions, "ocaso").resume(actor, P11_ID)
    assert resumed is not None and resumed.status == "completed"

    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P11_REWARD_SOURCE,
            )
        )
        assert event is not None
        rows = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
                )
            ).all()
        )
        assert _reward_components(rows) == {
            ("xp", 16900, None),
            ("crowns", 490, None),
            ("material", 3, "material.vde.ferro_enredado"),
            ("material", 1, "material.vde.resina_enredada"),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P11_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == BERCO_LOCATION_ID,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == BERCO_ROUTE_UNLOCK,
            )
        ) is not None
        for entry_id in (
            "codex.location.berco_da_matriarca",
            "codex.mystery.a_rede_sob_os_vales",
        ):
            assert await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character_id,
                    CodexEntry.entry_id == entry_id,
                )
            ) is not None

    local = await road.resume(actor)
    assert local is not None and VDE_BERCO in local.route_destinations
    assert await road.travel_route(actor, VDE_BERCO) is not None
    berco = await road.resume(actor)
    assert berco is not None and berco.kind == "vde_berco"
    assert not berco.hunt_enabled and not berco.explore_enabled
    assert not berco.familiar and berco.brazier_id is None and not berco.brazier_destinations
    assert berco.route_destinations == (VDE_CLAUSTRO,)
    from asterion.bot.road_ui import render_current_local

    screen = render_current_local(berco)
    assert "Local de clímax" in screen.text
    assert not any(
        label in screen.text for label in ("Caçada", "Ronda de Caça", "Desbravar", "Braseiro")
    )
    assert "road:route:vde_claustro" in {
        button.callback_data for row in screen.keyboard.inline_keyboard for button in row
    }
    assert await road.travel_route(actor, VDE_CLAUSTRO) is not None


@pytest.mark.asyncio
async def test_p11_shared_pressure_points_and_helper_reward_safety(database, monkeypatch):
    import asterion.application.campaign_coop as campaign_coop

    leader, eligible, helper = 998803, 998804, 998805
    leader_id, sessions = await _seed_claustro(database, leader, level=19)
    eligible_id, _ = await _seed_claustro(database, eligible, level=19)
    helper_id, _ = await _seed_claustro(database, helper, level=19)
    async with sessions() as session:
        eligible_row = await session.get(Character, eligible_id)
        helper_row = await session.get(Character, helper_id)
        assert eligible_row is not None and helper_row is not None
        eligible_name, helper_name = eligible_row.name, helper_row.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invite = await groups.invite(leader, eligible_name, expected_group_revision=group.revision)
    await groups.respond_invite(
        eligible, invite.invite_id, expected_revision=invite.revision, accept=True
    )
    group = await groups.group(leader)
    invite = await groups.invite(leader, helper_name, expected_group_revision=group.revision)
    await groups.respond_invite(
        helper, invite.invite_id, expected_revision=invite.revision, accept=True
    )

    missions = VDEMissionService(sessions, "ocaso", groups)
    for actor in (leader, eligible):
        view = await missions.start(actor, P11_ID)
        assert view is not None and view.status == "active"
    view = await missions.resume(leader, P11_ID)
    for point in ("a", "b", "c"):
        view = await missions.examine(leader, P11_ID, view.state_version, point)
    assert view is not None and view.kind == "clear_roots"
    view = await missions.advance(leader, P11_ID, view.state_version, "roots")
    async with sessions() as session:
        for character_id in (leader_id, eligible_id):
            quest = await session.scalar(
                select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P11_ID)
            )
            assert quest is not None and quest.step == 3
            assert len(quest.progress["pressure_points"]) == 3

    proposal_view = await missions.propose_group_combat(leader, P11_ID, view.state_version)
    assert proposal_view is not None and proposal_view.proposal_id is not None
    proposal = await groups.activity_proposal(leader, proposal_view.proposal_id)
    for actor in (eligible, helper):
        await groups.respond_activity(
            actor,
            proposal.proposal_id,
            expected_revision=proposal.revision,
            accept=True,
        )
        proposal = await groups.activity_proposal(leader, proposal_view.proposal_id)
    started = await missions.start_group_combat(
        leader, proposal.proposal_id, expected_revision=proposal.revision
    )
    assert started is not None and started.kind == "combat" and started.group_size == 3
    async with sessions() as session:
        encounter = await session.get(CampaignSharedEncounter, started.encounter_id)
        assert encounter is not None and encounter.roster_size == 3

    resumed = await missions.resume_active(eligible)
    helper_view = await missions.resume_active(helper)
    assert resumed is not None and resumed.encounter_id == started.encounter_id
    assert helper_view is not None and helper_view.encounter_id == started.encounter_id
    monkeypatch.setattr(campaign_coop, "act", _terminal("victory"))
    active_key = active_player_key(started.combat)
    assert active_key is not None
    views_by_actor = {leader: started, eligible: resumed, helper: helper_view}
    turn_owner = next(
        actor
        for actor, participant_view in views_by_actor.items()
        if participant_view.combat_actor_key == active_key
    )
    active_view = views_by_actor[turn_owner]
    result = await missions.action_combat(
        turn_owner, active_view.activity_id, active_view.combat.version, "attack"
    )
    assert result is not None and result.kind == "chamber"
    async with sessions() as session:
        for character_id in (leader_id, eligible_id):
            quest = await session.scalar(
                select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P11_ID)
            )
            assert quest is not None and quest.step == 4
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == helper_id, Quest.quest_id == P11_ID)
        ) is None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == helper_id,
                RewardEvent.source_id == P11_REWARD_SOURCE,
            )
        ) is None

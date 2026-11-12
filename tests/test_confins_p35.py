from collections import Counter

import pytest
from sqlalchemy import select

from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P34_CONTENT_VERSION,
    P34_ID,
    P35_ACHIEVEMENT,
    P35_CODEX_RECONSTRUCTION,
    P35_CODEX_RUPTURE,
    P35_CONTENT_VERSION,
    P35_ID,
    P35_REWARD_SOURCE,
    P35_TITLE,
    AltosMissionService,
)
from asterion.application.groups import GroupError, GroupService
from asterion.application.knowledge_catalog import (
    ACHIEVEMENT_BY_ID,
    CODEX_BY_ID,
    CODEX_FRAGMENTS,
)
from asterion.application.road import (
    CONFINS_CAMARA_REGENCIA_LABEL,
    CONFINS_NO_CENTRAL_LABEL,
    CONFINS_REGION_LABEL,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Character,
    CharacterCosmetic,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_confins_p34 import _seed_p34_actor
from tests.test_s4_s5_integration import _terminal


async def _complete_p34(mission, road, actor, monkeypatch):
    view = await mission.start_p34(actor)
    assert view is not None and view.status == "active"
    assert await road.travel_route(actor, CONFINS_NO_CENTRAL_LABEL) is not None
    await mission.on_location(actor)
    view = await mission.resume(actor, P34_ID)
    assert view is not None and view.step == 2
    for action in (
        "inspect_reference_conduction",
        "inspect_route_alignment",
        "inspect_failure_communication",
    ):
        view = await mission.advance(actor, view.state_version, action)
        assert view is not None
    battle = await mission.start_solo_combat(actor, view.state_version, P34_ID)
    assert battle is not None and battle.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    view = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert view is not None and view.step == 4
    for action in (
        "observe_regional_anchor_evidence",
        "compare_eris_with_roven",
        "record_anchor_codex_and_conclude",
    ):
        view = await mission.advance(actor, view.state_version, action)
        assert view is not None
    assert view.status == "completed"
    return view


async def _seed_completed_p34(database, actor: int, *, level: int = 59):
    actor, road, sessions = await _seed_p34_actor(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_NO_CENTRAL_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P34_ID,
                title="A Âncora Central",
                status="completed",
                step=6,
                content_version=P34_CONTENT_VERSION,
                state_version=6,
                progress={"completed": True},
            )
        )
        session.add(
            Unlock(
                character_id=character.id,
                unlock_id="unlock.location.confins.no_central",
            )
        )
        session.add(
            LocationDiscovery(
                character_id=character.id,
                location_id="location.confins.no_central",
            )
        )
    return actor, road, sessions


@pytest.mark.parametrize("level", (58,))
@pytest.mark.asyncio
async def test_p35_gate_requires_p34_and_suspends_below_level_59(database, level):
    actor, _road, sessions = await _seed_p34_actor(database, 793500 + level, level=level)
    mission = AltosMissionService(sessions, "ocaso")
    assert await mission.start_p35(actor) is None

    actor, _road, sessions = await _seed_completed_p34(
        database, 793520 + level, level=level
    )
    view = await AltosMissionService(sessions, "ocaso").start_p35(actor)
    assert view is not None and view.quest_id == P35_ID
    assert view.status == "suspended"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P35_ID
            )
        ) is None


@pytest.mark.asyncio
async def test_p34_to_p35_progress_chamber_at_59_scripted_combat_and_rewards(
    database, monkeypatch
):
    actor, road, sessions = await _seed_p34_actor(database, 793540, level=59)
    mission = AltosMissionService(sessions, "ocaso")
    await _complete_p34(mission, road, actor, monkeypatch)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character_id = character.id
        before_xp, before_crowns = character.xp, character.crowns

    view = await mission.start_p35(actor)
    assert view is not None and view.status == "active" and view.step == 1
    assert view.title == P35_TITLE
    assert view.progress["s35_contextual_knowledge_available"] is False

    for chain in (
        "custodia_ancoras",
        "regencia_continuidade",
        "oposicao_desvelados",
    ):
        view = await mission.advance(
            actor, view.state_version, f"record_chain_{chain}"
        )
        assert view is not None
    assert view.step == 2
    assert len(view.progress["documentary_chain_evidence_ids"]) == 3

    for evidence in (
        "pre_civil_deterioration",
        "anchors_stabilized",
        "growing_dependency_inequality",
        "coupled_convergence",
    ):
        view = await mission.advance(
            actor, view.state_version, f"verify_sequence_{evidence}"
        )
        assert view is not None
    assert view.step == 3
    assert len(view.progress["technical_sequence_evidence_ids"]) == 4

    assert await road.travel_route(actor, CONFINS_CAMARA_REGENCIA_LABEL) is None
    battle = await mission.start_solo_combat(actor, view.state_version, P35_ID)
    assert battle is not None and battle.kind == "combat" and battle.combat is not None
    enemies = [fighter for fighter in battle.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1
    assert enemies[0].level == 59
    assert battle.combat.variant is None
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P35_REWARD_SOURCE,
            )
        ) is None

    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert defeated is not None and defeated.step == 3
    assert defeated.progress["awaiting_retry"] is True
    retry = await mission.retry_combat(actor, defeated.state_version, P35_ID)
    assert retry is not None and retry.kind == "combat" and retry.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    view = await mission.action(
        actor, retry.activity_id, retry.combat.version, "attack"
    )
    assert view is not None and view.step == 4
    assert view.progress["scripted_vigia_victory"] is True
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.xp, character.crowns) == (before_xp, before_crowns)
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P35_REWARD_SOURCE,
            )
        ) is None

    view = await mission.advance(
        actor, view.state_version, "reconstruct_desvelados_sabotage"
    )
    assert view is not None and view.step == 5
    assert view.progress["desvelados_facts"]["no_collective_blame"] is True
    view = await mission.advance(
        actor, view.state_version, "record_cael_rhen_decision_context"
    )
    assert view is not None and view.step == 6
    assert view.progress["cael_decision_facts"]["documentary_uncertainty_preserved"]
    view = await mission.advance(
        actor, view.state_version, "record_convergence_codices"
    )
    assert view is not None and view.step == 7
    view = await mission.advance(actor, view.state_version, "open_chamber_route")
    assert view is not None and view.step == 8
    assert view.progress["chamber_route_opened"] is True

    local = await road.resume(actor)
    assert local is not None and CONFINS_CAMARA_REGENCIA_LABEL in local.route_destinations
    assert await road.travel_route(actor, CONFINS_CAMARA_REGENCIA_LABEL) is not None
    await mission.on_location(actor)
    local = await road.resume(actor)
    assert local is not None and local.location == CONFINS_CAMARA_REGENCIA_LABEL
    assert not local.hunt_enabled and not local.explore_enabled
    assert local.familiar is False
    assert local.brazier_id is None
    assert local.route_destinations == (CONFINS_NO_CENTRAL_LABEL,)
    assert await road.prepare_hunt(actor) is None
    assert await road.prepare_explore(actor) is None
    async with sessions() as session:
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "location.confins.camara_regencia",
            )
        ) is not None

    assert await road.travel_route(actor, CONFINS_NO_CENTRAL_LABEL) is not None
    await mission.on_location(actor)
    view = await mission.resume(actor, P35_ID)
    assert view is not None and view.step == 8
    view = await mission.advance(actor, view.state_version, "conclude_with_sera")
    assert view is not None and view.status == "completed"
    duplicate = await mission.advance(
        actor, view.state_version - 1, "conclude_with_sera"
    )
    assert duplicate is not None and duplicate.status == "completed"

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.xp - before_xp, character.crowns - before_crowns) == (
            98_950,
            1_220,
        )
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P35_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        assert Counter((row.kind, row.item_id, row.quantity) for row in components) == Counter(
            {
                ("xp", None, 98_950): 1,
                ("crowns", None, 1_220): 1,
                ("material", "material.confins.ferro_baliza", 2): 1,
                ("material", "material.confins.musgo_limiar", 1): 1,
                ("material", "material.confins.po_referencia", 1): 1,
            }
        )
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "unlock.location.confins.camara_regencia",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "unlock.campaign.first_journey_complete",
            )
        ) is None
        for entry_id in (P35_CODEX_RECONSTRUCTION, P35_CODEX_RUPTURE):
            assert entry_id in CODEX_BY_ID
            assert entry_id in CODEX_FRAGMENTS
            assert await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character_id,
                    CodexEntry.entry_id == entry_id,
                )
            ) is not None
            assert await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.entry_id == entry_id,
                    CodexFragment.fragment_id == entry_id,
                )
            ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == P35_ACHIEVEMENT,
            )
        ) is not None
        cosmetic = await session.scalar(
            select(CharacterCosmetic).where(
                CharacterCosmetic.character_id == character_id,
                CharacterCosmetic.cosmetic_id == "cosmetic.frame.confins.arquivo_duplo",
            )
        )
        assert cosmetic is not None and cosmetic.cosmetic_type == "frame"
        assert ACHIEVEMENT_BY_ID[P35_ACHIEVEMENT].name == "A Noite Reconstruída"
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id == P35_ID,
                Quest.content_version == P35_CONTENT_VERSION,
                Quest.status == "completed",
            )
        ) is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id, Quest.quest_id == "P36"
            )
        ) is None


@pytest.mark.asyncio
async def test_p35_documentary_steps_are_solo_and_helper_keeps_own_progress(
    database, monkeypatch
):
    actors = (793560, 793561)
    _lead, _road, sessions = await _seed_completed_p34(database, actors[0])
    _helper, _road, _sessions = await _seed_completed_p34(database, actors[1])
    groups = GroupService(sessions, "ocaso")
    async with sessions() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper_name = helper.name
    group = await groups.create_group(actors[0])
    invite = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    for actor in actors:
        view = await mission.start_p35(actor)
        assert view is not None and view.status == "active"

    # Objectives are Solo (Ação × Consequência §5): only the leader records.
    for chain in (
        "custodia_ancoras",
        "regencia_continuidade",
        "oposicao_desvelados",
    ):
        view = await mission.resume(actors[0], P35_ID)
        assert view is not None and view.step == 1
        await mission.advance(actors[0], view.state_version, f"record_chain_{chain}")
    view = await mission.resume(actors[0], P35_ID)
    assert view is not None and view.step == 2
    assert len(view.progress["documentary_chain_evidence_ids"]) == 3
    helper = await mission.resume(actors[1], P35_ID)
    assert helper is not None and helper.step == 1
    assert not helper.progress.get("documentary_chain_evidence_ids")

    for evidence in (
        "pre_civil_deterioration",
        "anchors_stabilized",
        "growing_dependency_inequality",
        "coupled_convergence",
    ):
        view = await mission.resume(actors[0], P35_ID)
        assert view is not None and view.step == 2
        await mission.advance(
            actors[0], view.state_version, f"verify_sequence_{evidence}"
        )
    view = await mission.resume(actors[0], P35_ID)
    assert view is not None and view.step == 3
    assert len(view.progress["technical_sequence_evidence_ids"]) == 4
    helper = await mission.resume(actors[1], P35_ID)
    assert helper is not None and helper.step == 1

    # P35 is not a Boss: the Group proposal is refused, the fight is Solo.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await mission.propose_group_combat(actors[0], view.state_version, P35_ID)
    assert not await groups.activity_proposals(actors[0])
    battle = await mission.start_solo_combat(
        actors[0], view.state_version, P35_ID
    )
    assert battle is not None and battle.combat is not None
    assert battle.group_size == 1 and not battle.combat.party_mode
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    leader = await mission.action(
        actors[0], battle.activity_id, battle.combat.version, "attack"
    )
    assert leader is not None and leader.step == 4
    helper = await mission.resume(actors[1], P35_ID)
    assert helper is not None and helper.step == 1

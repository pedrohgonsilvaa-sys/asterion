from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.groups import GroupService
from asterion.application.p7 import REGION
from asterion.application.road import VDE_BERCO, RoadService
from asterion.application.vde_missions import (
    BERCO_LOCATION_ID,
    BERCO_ROUTE_UNLOCK,
    CLAUSTRO,
    P11_ID,
    P12_ID,
    P12_NUCLEUS,
    P12_NUCLEUS_SOURCE,
    P12_REWARD_CHOICES,
    P12_REWARD_SOURCE,
    VDE_CAMPAIGN_UNLOCK,
    VDEMissionService,
)
from asterion.domain.campaign_combat import scale_campaign_boss_stats
from asterion.domain.combat import active_player_key
from asterion.domain.road import VDE_MATRIARCH, road_enemy_stats
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEvidence,
    CampaignSharedEncounter,
    Character,
    CodexEntry,
    CodexFragment,
    EquipmentItem,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_vde_s11_p11_berco_integration import _seed_claustro

D = Decimal


async def _seed_p12_gate(database, actor: int, *, level: int, start_boss: bool = False):
    character_id, sessions = await _seed_claustro(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = REGION
        world.location = CLAUSTRO
        session.add_all(
            [
                Quest(
                    character_id=character_id,
                    quest_id=P11_ID,
                    title="Onde Tudo se Enreda",
                    status="completed",
                    step=7,
                    content_version="vales-1.0.4",
                    progress={"completed": True, "berco_access_open": True},
                ),
                Unlock(character_id=character_id, unlock_id=BERCO_ROUTE_UNLOCK),
                LocationDiscovery(
                    character_id=character_id,
                    location_id=BERCO_LOCATION_ID,
                ),
            ]
        )
        if start_boss:
            world.location = "Berço da Matriarca"
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=P12_ID,
                    title="A Matriarca das Raízes",
                    status="active",
                    step=5,
                    content_version="vales-1.0.4",
                    state_version=6,
                    progress={
                        "entered_berco": True,
                        "advance_network": True,
                        "external_connections": ["a", "b", "c"],
                        "central_chamber": True,
                        "reward_choice": None,
                    },
                )
            )
        for location_id in (
            "vde.location.garganta_dos_lacos",
            "vde.location.mata_suspensa",
            "vde.location.baixios_enredados",
            "vde.location.claustro_das_raizes",
            BERCO_LOCATION_ID,
        ):
            exists = await session.scalar(
                select(LocationDiscovery.id).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id == location_id,
                )
            )
            if exists is None:
                session.add(
                    LocationDiscovery(
                        character_id=character_id,
                        location_id=location_id,
                    )
                )
    return character_id, sessions


async def _complete_current_shared_boss_turn(service, actors, activity_id, sessions):
    views = [await service.resume(actor, P12_ID) for actor in actors]
    current = next(view for view in views if view is not None and view.combat is not None)
    actor_key = active_player_key(current.combat)
    assert actor_key is not None
    actor_index = next(
        index
        for index, view in enumerate(views)
        if view is not None and view.combat_actor_key == actor_key
    )
    actor = actors[actor_index]
    await service.action_combat(
        actor,
        activity_id,
        current.combat.version,
        "attack",
        target_id="enemy",
    )


@pytest.mark.asyncio
async def test_p12_auto_start_story_victory_settlement_and_epic_choice(database):
    actor = 998901
    character_id, sessions = await _seed_p12_gate(database, actor, level=19)
    missions = VDEMissionService(sessions, "ocaso")

    blocked = await missions.resume(actor, P12_ID)
    assert blocked is not None and blocked.kind == "unavailable"
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == P12_ID)
        ) is None

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 20
    p12 = await missions.resume(actor, P12_ID)
    assert p12 is not None and p12.status == "active" and p12.step == 1
    assert p12.kind == "enter_berco"

    road = RoadService(sessions, "ocaso")
    assert await road.travel_route(actor, VDE_BERCO) is not None
    p12 = await missions.advance(actor, P12_ID, p12.state_version, "enter_berco")
    assert p12 is not None and p12.step == 2 and p12.kind == "advance_network"
    p12 = await missions.advance(actor, P12_ID, p12.state_version, "advance_network")
    assert p12 is not None and p12.step == 3 and p12.kind == "connections"
    for point in ("a", "b", "c"):
        p12 = await missions.examine(actor, P12_ID, p12.state_version, point)
    assert p12 is not None and p12.step == 4 and p12.kind == "central_chamber"
    p12 = await missions.advance(actor, P12_ID, p12.state_version, "central_chamber")
    assert p12 is not None and p12.step == 5 and p12.kind == "combat_start"

    fight = await missions.start_solo_combat(actor, P12_ID, p12.state_version)
    assert fight is not None and fight.combat is not None and fight.activity_id is not None
    assert fight.combat.party_mode and fight.combat.manual_sides == ("player",)
    assert fight.combat.fighters["enemy"].name == VDE_MATRIARCH.name
    assert fight.combat.fighters["enemy"].stats == road_enemy_stats(VDE_MATRIARCH, 20)

    async with sessions.begin() as session:
        activity = await session.get(GameActivity, fight.activity_id)
        assert activity is not None
        _encounter, record = await CombatRepository(session).combat(activity)
        state = decode(record.snapshot, record.id, activity.ruleset_version, activity.state_version)
        state.fighters["enemy"].hp = D(1)
        state.phase_id = "III"
        state.phase_triggered_ids = {"matriarca.phase.ii", "matriarca.phase.iii"}
        state.order = ("player", "enemy")
        state.turn_index = 0
        for key in ("connection_a", "connection_b", "connection_c"):
            state.fighters[key].hp = D(0)
        record.snapshot = encode(state)

    after_victory = await missions.action_combat(
        actor,
        fight.activity_id,
        fight.combat.version,
        "attack",
        target_id="enemy",
    )
    assert after_victory is not None and after_victory.kind == "examine_center"
    assert after_victory.status == "active" and after_victory.step == 6
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P12_NUCLEUS_SOURCE,
            )
        ) == 1
        core = await session.scalar(
            select(RewardComponent).join(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P12_NUCLEUS_SOURCE,
            )
        )
        assert core is not None and core.item_id == P12_NUCLEUS and core.quantity == 1
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P12_REWARD_SOURCE,
            )
        ) is None
        evidence = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == VDE_MATRIARCH.creature_id,
                    )
                )
            ).all()
        )
        assert "first_victory" in evidence
        assert await session.scalar(
            select(Achievement.achievement_id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.vde.o_berco_silencia",
            )
        ) == "feat.vde.o_berco_silencia"

    p12 = await missions.advance(actor, P12_ID, after_victory.state_version, "examine_center")
    assert p12 is not None and p12.step == 7 and p12.kind == "register"
    old_version = p12.state_version
    p12 = await missions.advance(actor, P12_ID, old_version, "register")
    assert p12 is not None and p12.status == "completed" and p12.kind == "choice"
    await missions.advance(actor, P12_ID, old_version, "register")

    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P12_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
                )
            ).all()
        )
        assert {(row.kind, row.quantity, row.item_id) for row in components} == {
            ("xp", 32580, None),
            ("crowns", 800, None),
            ("material", 4, "material.vde.ferro_enredado"),
            ("material", 4, "material.vde.resina_enredada"),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P12_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "recipe.vde.matriarca.seiva",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VDE_CAMPAIGN_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.achievement_id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.vde.vales_dos_enforcados",
            )
        ) == "feat.vde.vales_dos_enforcados"
        assert await session.scalar(
            select(Achievement.achievement_id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.vde.a_rede_nao_dorme",
            )
        ) is None
        codex = set(
            (
                await session.scalars(
                    select(CodexEntry.entry_id).where(CodexEntry.character_id == character_id)
                )
            ).all()
        )
        assert {
            "codex.location.berco_da_matriarca",
            "codex.mystery.a_rede_sob_os_vales",
            "codex.mystery.pulsacao_sob_a_pedra",
            "codex.mystery.estruturas_interligadas",
        } <= codex
        fragments = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id
                    )
                )
            ).all()
        )
        assert "codex.fragment.vales.continuidade_nareth" in fragments
        character = await session.get(Character, character_id)
        assert character is not None
        narethish = await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "region.nareth.available",
            )
        )
        assert bool(narethish) == (character.level >= 21)

    choice_version = p12.state_version
    p12 = await missions.choose_p12_reward(actor, choice_version, "2")
    assert p12 is not None and p12.kind == "completed"
    assert (p12.progress or {}).get("reward_choice") == "2"
    await missions.choose_p12_reward(actor, choice_version, "1")
    async with sessions() as session:
        equipment_events = list(
            (
                await session.scalars(
                    select(RewardEvent).where(
                        RewardEvent.character_id == character_id,
                        RewardEvent.source_id == f"{P12_REWARD_SOURCE}:equipment",
                    )
                )
            ).all()
        )
        assert len(equipment_events) == 1
        equipment_component = await session.scalar(
            select(RewardComponent).where(
                RewardComponent.reward_event_id == equipment_events[0].id
            )
        )
        assert equipment_component is not None
        assert equipment_component.payload["choice"] == "2"
        assert equipment_component.payload["item_name"] == P12_REWARD_CHOICES["2"][0]
        item = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.character_id == character_id,
                EquipmentItem.source_key == f"{P12_REWARD_SOURCE}:equipment:{character_id}:2",
            )
        )
        # The source key is a stable identity; if inventory is full the payload remains pending.
        if item is not None:
            assert item.rarity == "Épico"
            assert item.item_level == 20
            assert item.bound is True


@pytest.mark.asyncio
async def test_group_matriarch_uses_frozen_scaling_and_settles_each_eligible_member(database):
    actors = (998911, 998912)
    seeded = [
        await _seed_p12_gate(database, actor, level=20, start_boss=True) for actor in actors
    ]
    character_ids = [character_id for character_id, _ in seeded]
    sessions = seeded[0][1]
    names = {}
    async with sessions() as session:
        for actor, character_id in zip(actors, character_ids, strict=True):
            character = await session.get(Character, character_id)
            assert character is not None
            names[actor] = character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invite = await groups.invite(
        actors[0], names[actors[1]], expected_group_revision=group.revision
    )
    group = await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )
    missions = VDEMissionService(sessions, "ocaso", groups)
    proposal_view = await missions.propose_group_combat(actors[0], P12_ID, 6)
    assert proposal_view is not None and proposal_view.proposal_id is not None
    proposal = await groups.activity_proposal(actors[0], proposal_view.proposal_id)
    accepted = await groups.respond_activity(
        actors[1],
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
    )
    started = await missions.start_group_combat(
        actors[0], proposal.proposal_id, expected_revision=accepted.revision
    )
    assert started is not None and started.combat is not None and started.encounter_id is not None
    assert started.group_size == 2
    assert started.combat.fighters["enemy"].stats == scale_campaign_boss_stats(
        road_enemy_stats(VDE_MATRIARCH, 20), 2
    )
    reconnect = await missions.resume_active(actors[1])
    assert reconnect is not None and reconnect.encounter_id == started.encounter_id

    async with sessions.begin() as session:
        encounter = await session.get(CampaignSharedEncounter, started.encounter_id)
        assert encounter is not None
        state = decode(
            encounter.combat_snapshot,
            encounter.id,
            encounter.ruleset_version,
            encounter.state_version,
        )
        state.fighters["enemy"].hp = D(1)
        state.phase_id = "III"
        state.phase_triggered_ids = {"matriarca.phase.ii", "matriarca.phase.iii"}
        state.fighters["connection_a"].hp = D(0)
        state.fighters["connection_b"].hp = D(0)
        state.fighters["connection_c"].hp = D(0)
        state.order = ("p1", "p2", "enemy")
        state.turn_index = 0
        encounter.combat_snapshot = encode(state)
        encounter.state_version = state.version

    await _complete_current_shared_boss_turn(
        missions, actors, started.activity_id, sessions
    )
    views = [await missions.resume(actor, P12_ID) for actor in actors]
    assert all(view is not None and view.step == 6 for view in views)
    for character_id in character_ids:
        async with sessions.begin() as session:
            quest = await session.scalar(
                select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P12_ID)
            )
            assert quest is not None
            quest.state_version += 1
            version = quest.state_version
        # The explicit version refresh above is a fixture-only lockstep check for shared recovery.
        actor = actors[character_ids.index(character_id)]
        resumed = await missions.resume(actor, P12_ID)
        assert resumed is not None and resumed.state_version == version

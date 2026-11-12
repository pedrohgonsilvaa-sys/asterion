import asyncio
from copy import deepcopy
from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application import campaign_coop, scripted_combat
from asterion.application.altos_missions import (
    P36_CONTENT_VERSION,
    P36_ID,
    S36_ID,
    AltosMissionService,
)
from asterion.application.groups import GroupService
from asterion.application.road import (
    CONFINS_ESTRADAS_AUSENTES_LABEL,
    CONFINS_FRATURAS_LIMIAR_LABEL,
    CONFINS_NO_CENTRAL_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
)
from asterion.application.s36 import (
    S36_ACHIEVEMENT,
    S36_BOSS_ID,
    S36_CODEX_ENTRY,
    S36_COMPLETION_UNLOCK,
    S36_REWARD_SOURCE,
    S36_TITLE_COSMETIC,
    S36Service,
)
from asterion.domain.combat import active_player_key
from asterion.domain.combat_math import enemy_stats
from asterion.domain.road import ARCHETYPE, CATEGORY, creature_for
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    CampaignObjectiveCredit,
    CampaignSharedEncounter,
    CampaignSharedEncounterMember,
    Character,
    CharacterCosmetic,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_confins_p35 import _seed_completed_p34
from tests.test_s4_s5_integration import _terminal

D = Decimal


def _campaign_terminal(result: str):
    def finish(combat, action, **_kwargs):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = result
        if result == "defeat":
            updated.fighters["player"].hp = D(0)
        return updated

    return finish


async def _seed_p36_complete(database, actor: int, *, level: int = 60):
    actor, road, sessions = await _seed_completed_p34(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        character.xp = 0
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_ULTIMO_REFUGIO_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P36_ID,
                title="O Regente Fraturado",
                status="completed",
                step=8,
                content_version=P36_CONTENT_VERSION,
                state_version=8,
                progress={"completed": True},
            )
        )
        session.add(
            Unlock(
                character_id=character.id,
                unlock_id="unlock.campaign.first_journey_complete",
            )
        )
        refuge_unlock = await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "unlock.location.confins.ultimo_refugio",
            )
        )
        if refuge_unlock is None:
            session.add(
                Unlock(
                    character_id=character.id,
                    unlock_id="unlock.location.confins.ultimo_refugio",
                )
            )
        refuge_discovery = await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == "location.confins.ultimo_refugio",
            )
        )
        if refuge_discovery is None:
            session.add(
                LocationDiscovery(
                    character_id=character.id,
                    location_id="location.confins.ultimo_refugio",
                )
            )
    return actor, road, sessions


async def _begin_s36(database, actor: int, *, groups=None):
    actor, road, sessions = await _seed_p36_complete(database, actor)
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    service = S36Service(sessions, "ocaso", mission)
    view = await service.offer(actor)
    assert view is not None and view.available and view.status == "unaccepted"
    accepted = await service.accept(actor)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    view = await service.advance(actor, accepted.state_version, "examine_civil_routines")
    assert view is not None and view.step == 2
    await _travel_to_node(road, actor)
    return actor, road, sessions, mission, service, view


async def _travel_to_node(road, actor):
    for destination in (
        CONFINS_ESTRADAS_AUSENTES_LABEL,
        CONFINS_FRATURAS_LIMIAR_LABEL,
        CONFINS_NO_CENTRAL_LABEL,
    ):
        assert await road.travel_route(actor, destination) is not None


async def _travel_to_refuge(road, actor):
    for destination in (
        CONFINS_FRATURAS_LIMIAR_LABEL,
        CONFINS_ESTRADAS_AUSENTES_LABEL,
        CONFINS_ULTIMO_REFUGIO_LABEL,
    ):
        assert await road.travel_route(actor, destination) is not None


async def _complete_field_evidence(service, actor, view):
    for action in (
        "inspect_control_safety",
        "inspect_control_obsolete_order",
        "inspect_control_verification",
    ):
        view = await service.advance(actor, view.state_version, action)
        assert view is not None
    assert view.step == 3
    for action in ("collect_return_proof_a", "collect_return_proof_b"):
        view = await service.advance(actor, view.state_version, action)
        assert view is not None
    assert view.step == 4
    return view


@pytest.mark.asyncio
async def test_s36_requires_p36_current_level_60_and_explicit_acceptance(database):
    actor, road, sessions = await _seed_completed_p34(database, 796360, level=60)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_ULTIMO_REFUGIO_LABEL

    mission = AltosMissionService(sessions, "ocaso")
    service = S36Service(sessions, "ocaso", mission)
    unavailable = await service.offer(actor)
    assert unavailable is not None and not unavailable.available
    denied = await service.accept(actor)
    assert denied is not None and denied.status == "unaccepted"
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == denied.character_id,
                Quest.quest_id == S36_ID,
            )
        ) is None

    actor, road, sessions = await _seed_p36_complete(database, 796361, level=59)
    mission = AltosMissionService(sessions, "ocaso")
    service = S36Service(sessions, "ocaso", mission)
    unavailable = await service.giver(actor)
    assert unavailable is not None and not unavailable.available
    denied = await service.accept(actor)
    assert denied is not None and denied.status == "unaccepted"
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == denied.character_id,
                Quest.quest_id == S36_ID,
            )
        ) is None

    actor, _road, sessions = await _seed_p36_complete(database, 796362, level=60)
    service = S36Service(sessions, "ocaso", AltosMissionService(sessions, "ocaso"))
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor)
    assert accepted is not None and accepted.status == "active"


@pytest.mark.asyncio
async def test_s36_current_level_after_legacy_gates_progress_without_erasing_evidence(database):
    actor, _road, sessions, _mission, service, view = await _begin_s36(
        database, 796363
    )
    view = await service.advance(actor, view.state_version, "inspect_control_safety")
    assert view is not None and view.step == 2
    assert "evidence.confins.s36.controle_seguranca" in view.evidence

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = 1

    blocked = await service.advance(
        actor, view.state_version, "inspect_control_obsolete_order"
    )
    assert blocked is not None and blocked.step == 2
    assert blocked.evidence == view.evidence

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = 60

    resumed = await service.advance(
        actor, blocked.state_version, "inspect_control_obsolete_order"
    )
    assert resumed is not None and resumed.step == 2
    assert set(resumed.evidence) == {
        "evidence.confins.s36.controle_seguranca",
        "evidence.confins.s36.ordem_sem_funcao",
    }


@pytest.mark.asyncio
async def test_s36_solo_full_progress_retry_reaccept_and_exact_one_time_reward(
    database, monkeypatch
):
    actor, road, sessions, mission, service, view = await _begin_s36(
        database, 796370
    )
    character_id = view.character_id
    view = await _complete_field_evidence(service, actor, view)
    assert len(view.evidence) == 5

    battle = await service.start_solo_combat(actor, view.state_version)
    assert battle is not None and battle.combat is not None
    boss = battle.combat.fighters["enemy"]
    definition = creature_for(S36_BOSS_ID)
    assert boss.name == "Verificador sem Testemunhas" and boss.level == 60
    assert definition.category == "boss" and definition.archetype == "controller"
    assert boss.stats == enemy_stats(60, CATEGORY["boss"], ARCHETYPE["controller"])
    assert set(battle.combat.enemy_actions) == {
        "golpe_comprovacao",
        "desvio_registro",
        "selagem_retorno",
        "conferencia_final",
    }
    actions = battle.combat.enemy_actions
    assert actions["golpe_comprovacao"].coefficient == D("1.00")
    assert actions["desvio_registro"].coefficient == D("0.90")
    assert actions["desvio_registro"].cooldown == 3
    assert actions["desvio_registro"].effect_stat == "agility"
    assert actions["desvio_registro"].duration == 2
    assert actions["selagem_retorno"].self_barrier_coefficient == D("0.90")
    assert actions["selagem_retorno"].cooldown == 4
    assert actions["selagem_retorno"].max_uses_per_combat == 2
    assert actions["conferencia_final"].prepared
    assert actions["conferencia_final"].coefficient == D("1.75")
    assert actions["conferencia_final"].cooldown == 5
    assert len(
        [fighter for fighter in battle.combat.fighters.values() if fighter.side == "enemy"]
    ) == 1

    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert defeated is not None and defeated.quest_id == S36_ID and defeated.step == 4
    assert defeated.progress["awaiting_retry"]
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S36_REWARD_SOURCE,
            )
        ) is None
        world = await session.get(WorldState, character_id)
        assert world is not None and world.location == CONFINS_ULTIMO_REFUGIO_LABEL

    await _travel_to_node(road, actor)
    retry = await service.retry_combat(actor, defeated.state_version)
    assert retry is not None and retry.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor, retry.activity_id, retry.combat.version, "attack"
    )
    assert victory is not None and victory.step == 5
    assert victory.progress["verifier_victory"]
    async with sessions() as session:
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == S36_BOSS_ID,
            )
        )
        assert entry is not None and entry.stage != "dominated"
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == S36_BOSS_ID,
                BestiaryEvidence.evidence_id == "first_victory",
            )
        ) is not None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S36_REWARD_SOURCE,
            )
        ) is None

    view = await service.resume(actor)
    assert view is not None and view.step == 5
    abandoned = await service.abandon(actor, view.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    await _travel_to_refuge(road, actor)
    resumed = await service.accept(actor, abandoned.state_version, reaccept=True)
    assert resumed is not None and resumed.status == "active" and resumed.step == 5
    assert resumed.verifier_victory
    await _travel_to_node(road, actor)
    view = await service.advance(actor, resumed.state_version, "record_bestiary")
    assert view is not None and view.step == 6
    view = await service.advance(actor, view.state_version, "narrate_civil_continuity")
    assert view is not None and view.step == 7
    completed, duplicate = await asyncio.gather(
        service.advance(actor, view.state_version, "conclude_with_haro_sera"),
        service.advance(actor, view.state_version, "conclude_with_haro_sera"),
    )
    assert completed is not None and completed.status == "completed"
    assert duplicate is not None and duplicate.status == "completed"

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and character.level == 60 and character.xp == 0
        assert character.crowns == 1_250
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S36_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == event.id
                    )
                )
            ).all()
        )
        assert len(components) == 10
        assert sum(row.quantity for row in components if row.kind == "xp") == 101_900
        assert sum(row.quantity for row in components if row.kind == "crowns") == 1_250
        material_counts = {}
        for row in components:
            if row.kind == "material":
                assert row.payload["bound"] is True
                material_counts[row.item_id] = material_counts.get(row.item_id, 0) + row.quantity
        assert material_counts == {
            "material.confins.ferro_baliza": 2,
            "material.confins.couro_marcha": 2,
            "material.confins.musgo_limiar": 2,
            "material.confins.po_referencia": 2,
        }
        stacks = list(
            (
                await session.scalars(
                    select(MaterialStack).where(MaterialStack.character_id == character_id)
                )
            ).all()
        )
        assert len(stacks) == 4
        assert all(stack.quantity == 2 and stack.bound for stack in stacks)
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == S36_COMPLETION_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == S36_ACHIEVEMENT,
            )
        ) is not None
        assert await session.scalar(
            select(CharacterCosmetic.cosmetic_id).where(
                CharacterCosmetic.character_id == character_id,
                CharacterCosmetic.cosmetic_id == S36_TITLE_COSMETIC,
                CharacterCosmetic.cosmetic_type == "title",
            )
        ) == S36_TITLE_COSMETIC
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == S36_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == S36_CODEX_ENTRY,
            )
        ) is not None
        p36 = await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P36_ID)
        )
        assert p36 is not None and p36.status == "completed"
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "unlock.campaign.first_journey_complete",
            )
        ) is not None
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == S36_ID,
                CampaignObjectiveCredit.objective_id == "s36.completed",
            )
        ) is not None


@pytest.mark.asyncio
async def test_s36_members_do_earlier_steps_alone_and_fight_the_boss_together(
    database, monkeypatch
):
    actors = (796380, 796381, 796382)
    _lead, road, sessions = await _seed_p36_complete(database, actors[0])
    _helper, _road, _sessions = await _seed_p36_complete(database, actors[1])
    _late, _road, _sessions = await _seed_p36_complete(
        database, actors[2], level=59
    )
    groups = GroupService(sessions, "ocaso")
    names = {}
    async with sessions() as session:
        for actor in actors:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            names[actor] = character.name
    group = await groups.create_group(actors[0])
    revision = group.revision
    for actor in actors[1:]:
        invitation = await groups.invite(
            actors[0], names[actor], expected_group_revision=revision
        )
        accepted_invite = await groups.respond_invite(
            actor,
            invitation.invite_id,
            expected_revision=invitation.revision,
            accept=True,
        )
        revision = accepted_invite.revision

    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    service = S36Service(sessions, "ocaso", mission)
    views = {}
    for actor in actors[:2]:
        accepted = await service.accept(actor)
        assert accepted is not None and accepted.status == "active"
        views[actor] = await service.advance(
            actor, accepted.state_version, "examine_civil_routines"
        )
        assert views[actor] is not None and views[actor].step == 2
        await _travel_to_node(road, actor)

    # Steps before the Boss are Solo (Ação × Consequência §5): each member
    # collects the evidence alone and the other one stays on the same step.
    steps = (
        "inspect_control_safety",
        "inspect_control_obsolete_order",
        "inspect_control_verification",
        "collect_return_proof_a",
        "collect_return_proof_b",
    )
    actor = actors[0]
    view = views[actor]
    assert view is not None
    view = await service.advance(actor, view.state_version, steps[0])
    assert view is not None and view.step == 2
    other_view = await service.resume(actors[1])
    assert other_view is not None and other_view.step == 2
    async with sessions() as session:
        credit_by_actor = {}
        for eligible_actor in actors[:2]:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == eligible_actor)
            )
            assert character is not None
            credit_by_actor[eligible_actor] = await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character.id,
                    CampaignObjectiveCredit.quest_id == S36_ID,
                    CampaignObjectiveCredit.source_key == "evidence.confins.s36.controle_seguranca",
                )
            )
        assert credit_by_actor[actors[0]] is not None
        assert credit_by_actor[actors[1]] is None
        late_character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[2])
        )
        assert late_character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == late_character.id,
                Quest.quest_id == S36_ID,
            )
        ) is None

    for action in steps[1:]:
        view = await service.advance(actor, view.state_version, action)
        assert view is not None
    assert view.step == 4
    other_view = await service.resume(actors[1])
    assert other_view is not None and other_view.step == 2
    # The other member does the same steps on their own.
    for action in steps:
        other_view = await service.advance(actors[1], other_view.state_version, action)
        assert other_view is not None
    assert other_view.step == 4
    async with sessions() as session:
        for eligible_actor in actors[:2]:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == eligible_actor)
            )
            assert character is not None
            assert await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character.id,
                    CampaignObjectiveCredit.quest_id == S36_ID,
                    CampaignObjectiveCredit.source_key == "evidence.confins.s36.controle_seguranca",
                )
            ) is not None

    # Boss: both members fight together in one shared encounter.
    pending = await service.propose_group_combat(actor, view.state_version)
    assert pending is not None and pending.proposal_id is not None
    proposal = await groups.activity_proposal(actor, pending.proposal_id)
    accepted = await groups.respond_activity(
        actors[1], proposal.proposal_id, expected_revision=proposal.revision, accept=True
    )
    started = await mission.start_group_combat(
        actor, proposal.proposal_id, expected_revision=accepted.revision
    )
    assert started is not None and started.combat is not None and started.group_size == 2
    async with sessions() as session:
        encounter = await session.scalar(
            select(CampaignSharedEncounter).where(
                CampaignSharedEncounter.id == started.encounter_id
            )
        )
        assert encounter is not None
        assert encounter.scaling_snapshot["roster_size"] == 2
    monkeypatch.setattr(campaign_coop, "act", _campaign_terminal("victory"))
    active_key = active_player_key(started.combat)
    async with sessions() as session:
        active_member = await session.scalar(
            select(CampaignSharedEncounterMember).where(
                CampaignSharedEncounterMember.shared_encounter_id == started.encounter_id,
                CampaignSharedEncounterMember.actor_key == active_key,
            )
        )
        assert active_member is not None
        active_character = await session.get(Character, active_member.character_id)
        assert active_character is not None
        active_actor = active_character.telegram_id
        activity_id = active_member.game_activity_id
    result = await mission.action(
        active_actor, activity_id, started.combat.version, "attack"
    )
    assert result is not None and result.step == 5
    async with sessions() as session:
        for eligible_actor in actors[:2]:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == eligible_actor)
            )
            assert character is not None
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == S36_ID,
                )
            )
            assert quest is not None and quest.step == 5
        late_character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[2])
        )
        assert late_character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == late_character.id,
                Quest.quest_id == S36_ID,
            )
        ) is None

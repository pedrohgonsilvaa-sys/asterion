import asyncio
from collections import Counter
from copy import deepcopy
from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application import campaign_coop, scripted_combat
from asterion.application.altos_missions import (
    P35_CONTENT_VERSION,
    P35_ID,
    P36_CAMPAIGN_UNLOCK,
    P36_CODEX_NATURE,
    P36_CODEX_PROTOCOL,
    P36_CONTENT_VERSION,
    P36_CORE_ID,
    P36_CORE_SOURCE,
    P36_FIRST_VICTORY_ACHIEVEMENT,
    P36_FIRST_VICTORY_FRAME,
    P36_ID,
    P36_NARRATIVE_UNLOCK,
    P36_RECIPE_UNLOCK,
    P36_REGION_ACHIEVEMENT,
    P36_REGION_APPEARANCE,
    P36_REWARD_OPTIONS,
    P36_REWARD_SOURCE,
    AltosMissionService,
)
from asterion.application.groups import GroupService
from asterion.application.knowledge_catalog import ACHIEVEMENT_BY_ID
from asterion.application.road import (
    CONFINS_CAMARA_REGENCIA_LABEL,
    CONFINS_ESTRADAS_AUSENTES_LABEL,
    CONFINS_FRATURAS_LIMIAR_LABEL,
    CONFINS_NO_CENTRAL_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
)
from asterion.domain.combat import (
    _damage_aura_reduction,
    _resolve_phase_triggers,
    active_player_key,
)
from asterion.domain.combat_math import enemy_stats
from asterion.domain.confins_regent import ANCHOR_IDS, ANCHOR_KEYS
from asterion.domain.professions import recipes_for
from asterion.domain.road import ARCHETYPE, CATEGORY, CONFINS_REGENTE_FRATURADO, creature_for
from asterion.domain.road import CONFINS_LOCATION_CATALOG as CONFINS_LOCATION_ENTRIES
from asterion.domain.weapon_metadata import weapon_definition
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    CampaignSharedEncounter,
    CampaignSharedEncounterMember,
    Character,
    CharacterCosmetic,
    CodexEntry,
    CodexFragment,
    EquipmentItem,
    LocationDiscovery,
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
            updated.fighters["player"].hp = Decimal(0)
        return updated

    return finish


async def _complete_p35(mission, road, actor, monkeypatch):
    view = await mission.start_p35(actor)
    assert view is not None and view.status == "active" and view.step == 1
    for evidence in (
        "custodia_ancoras",
        "regencia_continuidade",
        "oposicao_desvelados",
    ):
        view = await mission.advance(actor, view.state_version, f"record_chain_{evidence}")
        assert view is not None
    for evidence in (
        "pre_civil_deterioration",
        "anchors_stabilized",
        "growing_dependency_inequality",
        "coupled_convergence",
    ):
        view = await mission.advance(actor, view.state_version, f"verify_sequence_{evidence}")
        assert view is not None
    battle = await mission.start_solo_combat(actor, view.state_version, P35_ID)
    assert battle is not None and battle.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    view = await mission.action(actor, battle.activity_id, battle.combat.version, "attack")
    assert view is not None and view.step == 4
    for action in (
        "reconstruct_desvelados_sabotage",
        "record_cael_rhen_decision_context",
        "record_convergence_codices",
        "open_chamber_route",
    ):
        view = await mission.advance(actor, view.state_version, action)
        assert view is not None
    assert view.step == 8
    view = await mission.advance(actor, view.state_version, "conclude_with_sera")
    assert view is not None and view.status == "completed"
    assert await road.travel_route(actor, CONFINS_CAMARA_REGENCIA_LABEL) is not None
    await mission.on_location(actor)
    return await mission.resume_active(actor)


async def _seed_p36_boss_ready(database, actor: int):
    actor, road, sessions = await _seed_completed_p34(database, actor, level=60)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = 60
        character.xp = 0
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_CAMARA_REGENCIA_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P35_ID,
                title="A Noite da Convergência",
                status="completed",
                step=8,
                content_version=P35_CONTENT_VERSION,
                state_version=8,
                progress={"completed": True},
            )
        )
        session.add(
            Unlock(
                character_id=character.id,
                unlock_id="unlock.location.confins.camara_regencia",
            )
        )
        session.add(
            LocationDiscovery(
                character_id=character.id,
                location_id="location.confins.camara_regencia",
            )
        )
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P36_ID,
                title="O Regente Fraturado",
                status="active",
                step=3,
                content_version=P36_CONTENT_VERSION,
                state_version=3,
                progress={
                    "completed_steps": [1, 2],
                    "chamber_entered": True,
                    "chamber_evidence_ids": [
                        "institutional_record",
                        "local_matter",
                        "incompatible_states",
                    ],
                    "final_evidence_ids": [
                        "final_evidence_a",
                        "final_evidence_b",
                        "final_evidence_c",
                    ],
                    "knowledge_gaps_recorded": True,
                },
            )
        )
    return actor, road, sessions


@pytest.mark.asyncio
async def test_p35_to_p36_solo_boss_choice_rewards_and_campaign_completion(
    database, monkeypatch
):
    actor, road, sessions = await _seed_completed_p34(database, 793610, level=60)
    mission = AltosMissionService(sessions, "ocaso")
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character_id = character.id
        for location_id, _label in CONFINS_LOCATION_ENTRIES:
            if location_id == "location.confins.camara_regencia":
                continue
            existing = await session.scalar(
                select(LocationDiscovery.id).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id == location_id,
                )
            )
            if existing is None:
                session.add(
                    LocationDiscovery(character_id=character_id, location_id=location_id)
                )

    p36 = await _complete_p35(mission, road, actor, monkeypatch)
    assert p36 is not None and p36.quest_id == P36_ID and p36.status == "active"
    assert p36.step == 1 and p36.progress["chamber_entered"] is True

    for evidence in ("institutional_record", "local_matter", "incompatible_states"):
        p36 = await mission.advance(
            actor, p36.state_version, f"record_chamber_{evidence}"
        )
        assert p36 is not None
    assert p36.step == 2
    for evidence in ("final_evidence_a", "final_evidence_b", "final_evidence_c"):
        p36 = await mission.advance(
            actor, p36.state_version, f"record_final_evidence_{evidence}"
        )
        assert p36 is not None
    assert p36.step == 3
    assert p36.progress["knowledge_gaps_recorded"] is True

    battle = await mission.start_solo_combat(actor, p36.state_version, P36_ID)
    assert battle is not None and battle.kind == "combat" and battle.combat is not None
    boss = battle.combat.fighters["enemy"]
    assert boss.level == 60
    assert boss.stats == enemy_stats(60, CATEGORY["boss"], ARCHETYPE["balanced"])
    actions = battle.combat.enemy_actions
    assert set(actions) >= {
        "ordem_sobreposta",
        "selo_continuidade",
        "marca_divergencia",
        "leitura_duas_ordens",
        "ancoragem_conflito",
        "desfecho_ultima_ordem",
    }
    assert actions["selo_continuidade"].max_uses_per_combat == 2
    assert actions["selo_continuidade"].cooldown == 4
    assert actions["selo_continuidade"].self_barrier_hp_fraction == D("0.08")
    assert actions["leitura_duas_ordens"].target_mode == "all_opponents"
    assert actions["desfecho_ultima_ordem"].prepared is True
    assert actions["desfecho_ultima_ordem"].phase_ids == ("III",)
    assert battle.combat.phase_id == "I"
    assert all(battle.combat.fighters[key].encounter_hidden for key in ANCHOR_KEYS)

    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert defeated is not None and defeated.step == 3
    assert defeated.progress["awaiting_retry"] is True
    async with sessions() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P36_CORE_SOURCE,
            )
        ) is None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P36_REWARD_SOURCE,
            )
        ) is None
    for destination in (
        CONFINS_ESTRADAS_AUSENTES_LABEL,
        CONFINS_FRATURAS_LIMIAR_LABEL,
        CONFINS_NO_CENTRAL_LABEL,
        CONFINS_CAMARA_REGENCIA_LABEL,
    ):
        assert await road.travel_route(actor, destination) is not None
    retry = await mission.retry_combat(actor, defeated.state_version, P36_ID)
    assert retry is not None and retry.combat is not None

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    result = await mission.action(
        actor, retry.activity_id, retry.combat.version, "attack"
    )
    assert result is not None and result.step == 6
    assert result.progress["first_core_claimed"] is True
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and character.level == 60 and character.xp == 0
        bestiary_milestone = await session.scalar(
            select(RewardComponent).where(
                RewardComponent.kind == "bestiary_first_victory_xp",
                RewardComponent.item_id == CONFINS_REGENTE_FRATURADO,
                RewardComponent.quantity == 6114,
            )
        )
        assert bestiary_milestone is not None
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == CONFINS_REGENTE_FRATURADO,
            )
        )
        assert entry is not None and entry.stage != "dominated"
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == CONFINS_REGENTE_FRATURADO,
                BestiaryEvidence.evidence_id == "first_victory",
            )
        ) is not None
    result = await mission.advance(actor, result.state_version, "record_regent_nature")
    assert result is not None and result.step == 7
    result = await mission.advance(
        actor, result.state_version, "record_regent_codices_and_recipe"
    )
    assert result is not None and result.step == 8

    option = "selo_referencia_presente"
    choice_a, choice_b = await asyncio.gather(
        mission.choose_p36_reward(actor, result.state_version, option),
        mission.choose_p36_reward(
            actor, result.state_version, "relicario_ordem_findada"
        ),
    )
    assert choice_a is not None and choice_b is not None
    selected = choice_a.progress["reward_choice"]
    assert selected in {option, "relicario_ordem_findada"}
    assert choice_b.progress["reward_choice"] == selected
    reconnected = await mission.resume(actor, P36_ID)
    assert reconnected is not None and reconnected.progress["reward_choice"] == selected
    result = await mission.advance(
        actor, reconnected.state_version, "conclude_with_sera"
    )
    assert result is not None and result.status == "completed"
    duplicate = await mission.advance(actor, result.state_version - 1, "conclude_with_sera")
    assert duplicate is not None and duplicate.status == "completed"

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and character.level == 60 and character.xp == 0
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P36_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )
        ).all()
        assert Counter((row.kind, row.item_id, row.quantity) for row in components) == Counter(
            {
                ("xp", None, 183_420): 1,
                ("crowns", None, 2_000): 1,
                ("equipment", "equipment.confins.campaign.p36.selo_referencia_presente", 1): 1,
                ("material", "material.confins.ferro_baliza", 3): 1,
                ("material", "material.confins.couro_marcha", 1): 1,
                ("material", "material.confins.musgo_limiar", 1): 1,
                ("material", "material.confins.po_referencia", 3): 1,
            }
        )
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P36_CORE_SOURCE,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == P36_CAMPAIGN_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == P36_NARRATIVE_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == P36_RECIPE_UNLOCK,
            )
        ) is not None
        for entry_id in (P36_CODEX_NATURE, P36_CODEX_PROTOCOL):
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
                Achievement.achievement_id == P36_FIRST_VICTORY_ACHIEVEMENT,
            )
        ) is not None
        assert await session.scalar(
                select(CharacterCosmetic.cosmetic_id).where(
                CharacterCosmetic.character_id == character_id,
                CharacterCosmetic.cosmetic_id == P36_FIRST_VICTORY_FRAME,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == P36_REGION_ACHIEVEMENT,
            )
        ) is not None
        assert await session.scalar(
                select(CharacterCosmetic.cosmetic_id).where(
                CharacterCosmetic.character_id == character_id,
                CharacterCosmetic.cosmetic_id == P36_REGION_APPEARANCE,
            )
        ) is not None
        equipment = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.character_id == character_id,
                EquipmentItem.source_key == f"{P36_REWARD_SOURCE}:equipment",
            )
        )
        assert equipment is not None and equipment.item_name == "Selo da Referência Presente"
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == P36_ID,
            )
        )
        assert quest is not None and quest.status == "completed"


@pytest.mark.asyncio
async def test_p36_group_first_victory_and_core_are_individual(database, monkeypatch):
    actors = (793620, 793621)
    _lead, _road, sessions = await _seed_p36_boss_ready(database, actors[0])
    _helper, _road, _sessions = await _seed_p36_boss_ready(database, actors[1])
    groups = GroupService(sessions, "ocaso")
    async with sessions() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper_name = helper.name
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    view = await mission.resume(actors[0], P36_ID)
    assert view is not None and view.step == 3
    pending = await mission.propose_group_combat(actors[0], view.state_version, P36_ID)
    assert pending is not None and pending.proposal_id is not None
    proposal = await groups.activity_proposal(actors[0], pending.proposal_id)
    accepted = await groups.respond_activity(
        actors[1], proposal.proposal_id, expected_revision=proposal.revision, accept=True
    )
    started = await mission.start_group_combat(
        actors[0], proposal.proposal_id, expected_revision=accepted.revision
    )
    assert started is not None and started.combat is not None and started.group_size == 2
    async with sessions() as session:
        encounter = await session.scalar(
            select(CampaignSharedEncounter).where(
                CampaignSharedEncounter.quest_id == P36_ID
            )
        )
        assert encounter is not None
        assert encounter.scaling_snapshot is not None
        assert encounter.scaling_snapshot["roster_size"] == 2
        hp_factor, attack_factor = campaign_coop.campaign_boss_scaling(2)
        assert D(encounter.scaling_snapshot["hp_factor"]) == hp_factor
        assert D(encounter.scaling_snapshot["attack_factor"]) == attack_factor
    assert set(started.combat.enemy_actions) >= {
        "ordem_sobreposta",
        "selo_continuidade",
        "marca_divergencia",
        "leitura_duas_ordens",
        "ancoragem_conflito",
        "desfecho_ultima_ordem",
    }
    monkeypatch.setattr(campaign_coop, "act", _campaign_terminal("victory"))
    active_key = active_player_key(started.combat)
    assert active_key in {"p1", "p2"}
    async with sessions() as session:
        member = await session.scalar(
            select(CampaignSharedEncounterMember).where(
                CampaignSharedEncounterMember.shared_encounter_id
                == started.encounter_id,
                CampaignSharedEncounterMember.actor_key == active_key,
            )
        )
        assert member is not None
        active_character = await session.get(Character, member.character_id)
        assert active_character is not None
        active_actor = active_character.telegram_id
        active_activity_id = member.game_activity_id
    result = await mission.action(
        active_actor, active_activity_id, started.combat.version, "attack"
    )
    assert result is not None and result.step == 6
    async with sessions() as session:
        character_ids = tuple(
            (
                await session.scalars(
                    select(Character.id).where(Character.telegram_id.in_(actors))
                )
            ).all()
        )
        assert len(character_ids) == 2
        for character_id in character_ids:
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P36_ID,
                )
            )
            assert quest is not None and quest.step == 6
            assert quest.progress["first_core_claimed"] is True
            assert await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == P36_CORE_SOURCE,
                )
            ) is not None
            assert await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character_id,
                    Achievement.achievement_id == P36_FIRST_VICTORY_ACHIEVEMENT,
                )
            ) is not None


@pytest.mark.asyncio
async def test_regent_phase_objects_and_barrier_are_one_shot(database):
    actor, _road, sessions = await _seed_p36_boss_ready(database, 793630)
    mission = AltosMissionService(sessions, "ocaso")
    view = await mission.resume(actor, P36_ID)
    assert view is not None
    battle = await mission.start_solo_combat(actor, view.state_version, P36_ID)
    assert battle is not None and battle.combat is not None
    combat = deepcopy(battle.combat)
    boss = combat.fighters["enemy"]
    reference = enemy_stats(60, CATEGORY["common"], ARCHETYPE["balanced"])
    assert combat.phase_id == "I"
    assert set(ANCHOR_IDS) == {combat.fighters[key].id for key in ANCHOR_KEYS}
    assert all(combat.fighters[key].stats.hp == reference.hp * D("0.25") for key in ANCHOR_KEYS)
    assert all(combat.fighters[key].stats.defense == reference.defense for key in ANCHOR_KEYS)

    boss.hp = boss.stats.hp * D("0.70")
    _resolve_phase_triggers(combat)
    assert combat.phase_id == "II"
    assert all(combat.fighters[key].hp == combat.fighters[key].stats.hp for key in ANCHOR_KEYS)
    assert all(not combat.fighters[key].encounter_hidden for key in ANCHOR_KEYS)
    assert _damage_aura_reduction(combat, "enemy") == D("0.10")

    two_remaining = deepcopy(combat)
    two_remaining_boss = two_remaining.fighters["enemy"]
    two_remaining_boss.hp = two_remaining_boss.stats.hp * D("0.35")
    _resolve_phase_triggers(two_remaining)
    assert two_remaining.phase_id == "III"
    assert two_remaining_boss.barrier == (
        two_remaining_boss.stats.hp * D("0.10")
    ).to_integral_value(rounding="ROUND_FLOOR")
    assert _damage_aura_reduction(two_remaining, "enemy") == D(0)

    combat.fighters[ANCHOR_KEYS[0]].hp = D(0)
    assert _damage_aura_reduction(combat, "enemy") == D("0.05")
    boss.hp = boss.stats.hp * D("0.35")
    _resolve_phase_triggers(combat)
    assert combat.phase_id == "III"
    assert all(combat.fighters[key].hp == 0 for key in ANCHOR_KEYS)
    assert combat.fighters[ANCHOR_KEYS[1]].encounter_hidden
    assert _damage_aura_reduction(combat, "enemy") == D(0)
    assert boss.barrier == (boss.stats.hp * D("0.05")).to_integral_value(rounding="ROUND_FLOOR")
    assert boss.barrier_remaining == -1
    before = (boss.barrier, set(combat.phase_triggered_ids), combat.phase_id)
    _resolve_phase_triggers(combat)
    assert (boss.barrier, set(combat.phase_triggered_ids), combat.phase_id) == before


def test_p36_global_metadata_and_recipe_are_registered():
    regent = creature_for(CONFINS_REGENTE_FRATURADO)
    assert regent is not None
    assert regent.creature_id == CONFINS_REGENTE_FRATURADO
    assert regent.category == "boss" and regent.archetype == "balanced"
    assert regent.unlock_level == 60 and regent.max_level == 60
    weapon_id = "equipment.confins.campaign.p36.guarda_ultimo_protocolo"
    weapon = weapon_definition(weapon_id)
    assert weapon is not None
    assert weapon.weapon_form == "weapon.form.mace"
    assert weapon.handedness == "weapon.hands.one"
    assert weapon.slot_eligibility == "weapon.slot.secondary_only"
    assert weapon.compatibility_tags == frozenset({"weapon.compat.melee"})
    recipe = next(
        row
        for row in recipes_for("artificer")
        if row.recipe_id == P36_RECIPE_UNLOCK
    )
    assert recipe.output_id == "enchant.confins.eco_encerramento"
    assert recipe.grade == 6 and recipe.required_level == 15
    assert recipe.fixed_crown_cost == 400
    assert Counter((item.material_id, item.quantity) for item in recipe.fixed_materials) == Counter(
        {
            ("material.confins.po_referencia", 5): 1,
            ("material.confins.ferro_baliza", 2): 1,
            ("material.tdo.catalisador_elite_vi", 1): 1,
            (P36_CORE_ID, 1): 1,
        }
    )
    assert ACHIEVEMENT_BY_ID[P36_FIRST_VICTORY_ACHIEVEMENT].name == "Encerrar sem Curar"
    assert set(P36_REWARD_OPTIONS) == {
        "guarda_ultimo_protocolo",
        "selo_referencia_presente",
        "relicario_ordem_findada",
    }

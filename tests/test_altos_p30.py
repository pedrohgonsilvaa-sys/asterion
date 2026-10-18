from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.altos_missions import (
    ALTOS_PRIMARY_LOCATIONS,
    ALTOS_REGION_ACHIEVEMENT,
    P29_CONTENT_VERSION,
    P29_ID,
    P30_ACHIEVEMENT,
    P30_CODEX_ENTRY,
    P30_CONTENT_VERSION,
    P30_CORE_ID,
    P30_CORE_REWARD_SOURCE,
    P30_ID,
    P30_MISSION_ID,
    P30_NARRATIVE_UNLOCK,
    P30_RECIPE_UNLOCK,
    P30_TITLE,
    AltosMissionService,
)
from asterion.application.groups import GroupService
from asterion.application.knowledge_catalog import ACHIEVEMENT_BY_ID, CODEX_FRAGMENTS
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_CORACAO_LABEL,
    ALTOS_REGION_LABEL,
)
from asterion.domain.altos_colossus import (
    ESCORA_IDS,
    ESCORA_KEYS,
    configure_colossus_encounter,
)
from asterion.domain.combat import (
    Action,
    Combat,
    Fighter,
    _damage_aura_reduction,
    _resolve_phase_triggers,
)
from asterion.domain.combat_math import CombatStats, enemy_stats
from asterion.domain.road import (
    ALTOS_COLOSSO_CINEREO,
    ARCHETYPE,
    CATEGORY,
    creature_for,
)
from asterion.infrastructure.db.models import (
    Achievement,
    CampaignSharedEncounter,
    Character,
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
from tests.test_altos_p28 import _seed_p28_character
from tests.test_s4_s5_integration import _terminal

D = Decimal


async def _seed_p30_character(database, actor: int, *, level: int = 50):
    actor, road, sessions = await _seed_p28_character(
        database, actor, level=level, p28_status="completed"
    )
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = ALTOS_REGION_LABEL
        world.location = ALTOS_CORACAO_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P29_ID,
                title="Antes da Convergência",
                status="completed",
                step=7,
                content_version=P29_CONTENT_VERSION,
                state_version=7,
                progress={"completed": True},
            )
        )
        session.add(
            Unlock(
                character_id=character.id,
                unlock_id="unlock.location.altos.coracao_colosso",
            )
        )
        existing_locations = set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character.id,
                        LocationDiscovery.location_id.in_(ALTOS_PRIMARY_LOCATIONS),
                    )
                )
            ).all()
        )
        session.add_all(
            LocationDiscovery(character_id=character.id, location_id=location_id)
            for location_id in ALTOS_PRIMARY_LOCATIONS
            if location_id not in existing_locations
        )
    return actor, road, sessions


async def _reach_p30_combat(mission: AltosMissionService, actor: int):
    view = await mission.resume_active(actor)
    assert view is not None and view.quest_id == P30_ID and view.step == 2
    for path in ("contraforte", "cabo", "escora"):
        view = await mission.advance(
            actor, view.state_version, f"inspect_load_path_{path}"
        )
        assert view is not None
    assert view.step == 3
    view = await mission.advance(
        actor, view.state_version, "recover_exceptional_coupling_record"
    )
    assert view is not None and view.step == 4
    return view


def _combat_fixture() -> Combat:
    stats = CombatStats(
        hp=D(1000),
        attack=D(100),
        defense=D(100),
        agility=D(50),
    )
    enemy_actions = {
        key: Action(key, key, D(1))
        for key in (
            "golpe_contraforte",
            "marca_carga",
            "placa_sustentacao",
            "varredura_contrapeso",
            "carga_distribuida",
        )
    }
    return Combat(
        id=uuid4(),
        ruleset="test-combat-ruleset",
        fighters={
            "enemy": Fighter(
                ALTOS_COLOSSO_CINEREO,
                "Colosso Cinéreo",
                50,
                stats,
                stats.hp,
                side="enemy",
            ),
            "player": Fighter(
                "character.test",
                "Aventureiro",
                50,
                stats,
                stats.hp,
                side="player",
            ),
        },
        player_actions={},
        enemy_actions=enemy_actions,
        ai_cycle=tuple(enemy_actions),
    )


def test_p30_colossus_phase_machine_matches_final_escora_contract():
    boss_profile = creature_for(ALTOS_COLOSSO_CINEREO)
    assert (
        boss_profile.name,
        boss_profile.category,
        boss_profile.archetype,
        boss_profile.unlock_level,
        boss_profile.max_level,
        boss_profile.weight,
    ) == ("Colosso Cinéreo", "boss", "armored", 50, 50, 0)
    assert tuple(action[0] for action in boss_profile.actions) == (
        "golpe_contraforte",
        "marca_carga",
        "placa_sustentacao",
        "varredura_contrapeso",
        "carga_distribuida",
    )
    assert boss_profile.ai == (
        "golpe_contraforte",
        "marca_carga",
        "placa_sustentacao",
        "varredura_contrapeso",
        "carga_distribuida",
    )
    assert boss_profile.ai_priority == ()
    action_rows = {action[0]: action for action in boss_profile.actions}
    assert action_rows["carga_distribuida"][2] == D("1.80")
    assert action_rows["carga_distribuida"][8] is True
    assert action_rows["carga_distribuida"][9] == 5

    combat = configure_colossus_encounter(_combat_fixture())
    boss = combat.fighters["enemy"]
    reference = enemy_stats(50, CATEGORY["common"], ARCHETYPE["balanced"])
    for key, element_id in zip(ESCORA_KEYS, ESCORA_IDS, strict=True):
        escora = combat.fighters[key]
        assert escora.id == element_id
        assert escora.stats.hp == reference.hp * D("0.25")
        assert escora.stats.defense == reference.defense * D("0.80")
        assert escora.hp == 0 and escora.encounter_hidden
        assert not escora.takes_turn and escora.required_for_victory is False

    assert _damage_aura_reduction(combat, "enemy") == 0
    boss.hp = boss.stats.hp * D("0.70")
    _resolve_phase_triggers(combat)
    assert combat.phase_id == "phase_ii"
    assert all(combat.fighters[key].hp > 0 for key in ESCORA_KEYS)
    assert all(not combat.fighters[key].encounter_hidden for key in ESCORA_KEYS)
    assert _damage_aura_reduction(combat, "enemy") == D("0.12")

    combat.fighters[ESCORA_KEYS[0]].hp = 0
    boss.hp = boss.stats.hp * D("0.35")
    _resolve_phase_triggers(combat)
    expected_barrier = (boss.stats.hp * D("0.06")).to_integral_value(
        rounding="ROUND_FLOOR"
    )
    assert combat.phase_id == "phase_iii"
    assert boss.barrier == expected_barrier
    assert boss.barrier_remaining == -1
    assert all(combat.fighters[key].hp == 0 for key in ESCORA_KEYS)
    assert combat.fighters[ESCORA_KEYS[0]].hp == 0
    _resolve_phase_triggers(combat)
    assert boss.barrier == expected_barrier

    actions = combat.enemy_actions
    assert actions["placa_sustentacao"].max_uses_per_combat == 2
    assert actions["placa_sustentacao"].self_barrier_hp_fraction == D("0.08")
    assert "phase_iii" not in actions["placa_sustentacao"].phase_ids
    assert actions["carga_distribuida"].skip_if_actor_last_action == (
        "carga_distribuida",
    )


@pytest.mark.asyncio
async def test_p30_level_gate_suspends_at_49_and_starts_at_50(database):
    actor, _road, sessions = await _seed_p30_character(database, 783001, level=49)
    mission = AltosMissionService(sessions, "ocaso")

    suspended = await mission.resume_active(actor)
    assert suspended is not None
    assert (suspended.quest_id, suspended.status) == (P30_ID, "suspended")
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "unlock.location.altos.coracao_colosso",
            )
        ) is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P30_ID
            )
        ) is None

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = 50

    active = await mission.resume_active(actor)
    assert active is not None
    assert (active.quest_id, active.status, active.step) == (P30_ID, "active", 2)
    assert active.progress["entered_coracao"] is True


@pytest.mark.asyncio
async def test_p30_solo_victory_claims_core_and_personal_rewards_once(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actor, _road, sessions = await _seed_p30_character(database, 783002)
    mission = AltosMissionService(sessions, "ocaso")
    view = await _reach_p30_combat(mission, actor)

    combat_view = await mission.start_solo_combat(
        actor, view.state_version, P30_ID
    )
    assert combat_view is not None and combat_view.combat is not None
    assert combat_view.combat.fighters["enemy"].name == "Colosso Cinéreo"
    assert combat_view.combat.fighters["enemy"].level == 50
    assert combat_view.combat.variant is None
    assert set(ESCORA_KEYS).issubset(combat_view.combat.fighters)
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor,
        combat_view.activity_id,
        combat_view.combat.version,
        "attack",
    )
    assert victory is not None and victory.step == 7
    assert victory.progress["completed_steps"] == [1, 2, 3, 4, 5, 6]

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        core_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P30_CORE_REWARD_SOURCE,
            )
        )
        assert core_event is not None
        assert await session.scalar(
            select(RewardComponent.id).where(
                RewardComponent.reward_event_id == core_event.id,
                RewardComponent.item_id == P30_CORE_ID,
                RewardComponent.quantity == 1,
            )
        ) is not None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P30_MISSION_ID,
            )
        ) is None

    view = await mission.advance(
        actor, victory.state_version, "inspect_postcombat_sabotage_record"
    )
    assert view is not None and view.step == 8
    assert view.progress["collective_attribution"] is False
    codex = await mission.advance(actor, view.state_version, "record_sabotage_codex")
    assert codex is not None and codex.step == 9
    recipe_step = await mission.advance(
        actor, codex.state_version, "reveal_colossus_recipe"
    )
    assert recipe_step is not None and recipe_step.step == 10
    assert recipe_step.progress["recipe_revealed"] is True
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == P30_RECIPE_UNLOCK,
            )
        ) is None

    completed = await mission.choose_p30_reward(
        actor, recipe_step.state_version, "relicario_ordem_interrompida"
    )
    assert completed is not None and completed.status == "completed"
    assert completed.progress["reward_choice"] == "relicario_ordem_interrompida"
    replay = await mission.choose_p30_reward(
        actor, recipe_step.state_version, "selo_rede_sustentada"
    )
    assert replay is not None and replay.status == "completed"
    assert replay.progress["reward_choice"] == "relicario_ordem_interrompida"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        reward_events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P30_MISSION_ID,
                )
            )
        ).all()
        assert len(reward_events) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == reward_events[0].id
                )
            )
        ).all()
        assert {
            (component.kind, component.item_id, component.quantity)
            for component in components
        } == {
            ("xp", None, 134_100),
            ("crowns", None, 1_700),
            (
                "equipment",
                "equipment.altos.campaign.p30.relicario_ordem_interrompida",
                1,
            ),
            ("material", "material.altos.ferro_contrapeso", 5),
            ("material", "material.altos.cinza_basalto", 3),
        }
        equipment = (
            await session.scalars(
                select(EquipmentItem).where(
                    EquipmentItem.character_id == character.id,
                    EquipmentItem.source_key == f"{P30_MISSION_ID}:equipment",
                )
            )
        ).all()
        assert len(equipment) == 1
        assert (equipment[0].rarity, equipment[0].item_level, equipment[0].bound) == (
            "Épico",
            50,
            True,
        )
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == P30_RECIPE_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == P30_NARRATIVE_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == P30_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.fragment_id == P30_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == P30_ACHIEVEMENT,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == ALTOS_REGION_ACHIEVEMENT,
            )
        ) is not None


@pytest.mark.asyncio
async def test_p30_defeat_keeps_encounter_retryable_without_rewards(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actor, _road, sessions = await _seed_p30_character(database, 783003)
    mission = AltosMissionService(sessions, "ocaso")
    view = await _reach_p30_combat(mission, actor)
    started = await mission.start_solo_combat(actor, view.state_version, P30_ID)
    assert started is not None and started.combat is not None
    encounter_id = started.activity_id
    initial_escora_hp = started.combat.fighters[ESCORA_KEYS[0]].stats.hp
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await mission.action(
        actor, started.activity_id, started.combat.version, "defend"
    )
    assert defeated is not None and defeated.step == 4
    assert defeated.progress["awaiting_retry"] is True
    assert defeated.location == ALTOS_ABRIGO_LABEL

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id.in_((P30_CORE_REWARD_SOURCE, P30_MISSION_ID)),
            )
        ) is None
        world = await session.get(WorldState, character.id)
        assert world is not None and world.location == ALTOS_ABRIGO_LABEL
        world.location = ALTOS_CORACAO_LABEL

    current = await mission.resume(actor, P30_ID)
    assert current is not None and current.progress["awaiting_retry"] is True
    retried = await mission.retry_combat(actor, current.state_version, P30_ID)
    assert retried is not None and retried.combat is not None
    assert retried.activity_id == encounter_id
    assert retried.combat.fighters[ESCORA_KEYS[0]].stats.hp == initial_escora_hp
    assert retried.combat.fighters[ESCORA_KEYS[0]].encounter_hidden


@pytest.mark.asyncio
async def test_p30_group_shares_encounter_and_freezes_boss_scaling(database):
    actors = (783004, 783005)
    seeded = [await _seed_p30_character(database, actor) for actor in actors]
    sessions = seeded[0][2]
    async with sessions() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper_name = helper.name
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    views = {actor: await mission.resume_active(actor) for actor in actors}
    assert all(view is not None and view.step == 2 for view in views.values())
    view = views[actors[0]]
    for path in ("contraforte", "cabo", "escora"):
        view = await mission.advance(
            actors[0], view.state_version, f"inspect_load_path_{path}"
        )
        assert view is not None
    view = await mission.advance(
        actors[0], view.state_version, "recover_exceptional_coupling_record"
    )
    assert view is not None and view.step == 4
    helper_view = await mission.resume(actors[1], P30_ID)
    assert helper_view is not None and helper_view.step == 4
    assert helper_view.progress["coupling_record_recovered"] is True

    pending = await mission.propose_group_combat(actors[0], view.state_version, P30_ID)
    assert pending is not None and pending.proposal_id is not None
    proposal = await groups.activity_proposal(actors[0], pending.proposal_id)
    accepted = await groups.respond_activity(
        actors[1], proposal.proposal_id, expected_revision=proposal.revision, accept=True
    )
    started = await mission.start_group_combat(
        actors[0], proposal.proposal_id, expected_revision=accepted.revision
    )
    assert started is not None and started.combat is not None
    assert started.group_size == 2
    assert {fighter.side for fighter in started.combat.fighters.values()} >= {
        "player",
        "enemy",
    }
    frozen_boss_hp = started.combat.fighters["enemy"].stats.hp
    async with sessions.begin() as session:
        encounter = await session.get(CampaignSharedEncounter, started.encounter_id)
        assert encounter is not None and encounter.roster_size == 2
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[0])
        )
        assert character is not None
        character.level = 51
    resumed = await mission.resume(actors[0], P30_ID)
    assert resumed is not None and resumed.combat is not None
    assert resumed.combat.fighters["enemy"].stats.hp == frozen_boss_hp


def test_p30_codex_achievement_and_coração_content_are_registered():
    assert P30_TITLE == "O Colosso Cinéreo"
    assert P30_CONTENT_VERSION == "altos-1.0.1"
    assert ACHIEVEMENT_BY_ID[P30_ACHIEVEMENT].name == "O Peso Pode Cessar"
    assert ACHIEVEMENT_BY_ID[ALTOS_REGION_ACHIEVEMENT].name == "Altos Cinéreos"
    fragment = CODEX_FRAGMENTS[P30_CODEX_ENTRY].text
    assert "ala radicalizada" in fragment
    assert "minutos finais" not in fragment
    assert "P31" not in fragment

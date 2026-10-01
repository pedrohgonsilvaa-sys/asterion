from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.active_arts import ActiveArtService
from asterion.application.class_trials import ClassTrialService
from asterion.domain.arts import ERRANTE_ART_IDS
from asterion.domain.class_trials import (
    ERRANTE_CONDITION_IDS,
    ERRANTE_ENTITY_IDS,
    ERRANTE_EXPOSE_ACTION_ID,
    ERRANTE_EXPOSED_EFFECT_ID,
    ERRANTE_PREPARED_ACTION_ID,
    ERRANTE_SHORT_CUT_ACTION_ID,
    ERRANTE_STAGE_3_CUT_A_ACTION_ID,
    ERRANTE_STAGE_3_CUT_B_ACTION_ID,
    ERRANTE_TRAINING_CUT_ACTION_ID,
    TrialCombatEvent,
    create_errante_trial_combat,
    errante_conditions_for_event,
    errante_enemy_actions,
    errante_stage_definition,
)
from asterion.domain.combat import Effect, Fighter, start_combat
from asterion.domain.combat_math import CombatStats, resolve_combat_stats
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    Character,
    ClassTrialState,
    CombatRecord,
    Encounter,
    MaterialStack,
    RewardEvent,
    Unlock,
    WorldState,
)

REFUGE = "Refúgio do Ocaso"
REGION = "Terras do Ocaso"


async def _seed_errante(database, actor: int):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats("errante", 10, "remanescente")
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Errante",
                race="remanescente",
                character_class="errante",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=10,
                xp=0,
                hp=Decimal("1"),
                max_hp=stats.hp,
                vigor=37,
                max_vigor=100,
                crowns=23,
            )
        )
        session.add(WorldState(character_id=character_id, region=REGION, location=REFUGE))
    return character_id, sessions, ClassTrialService(sessions, "ocaso")


async def _start_errante(service, actor: int, arts: tuple[str, ...], *, stage: int = 1):
    art_service = ActiveArtService(service.sessions, service.server_id)
    for slot, art_id in enumerate(arts, start=1):
        await art_service.equip_art(actor, slot, art_id)
    view = await service.resume(actor)
    if view.kind == "available":
        view = await service.begin(actor, view.state_version)
    if stage > 1:
        async with service.sessions.begin() as session:
            state = await session.get(ClassTrialState, view.character_id)
            state.current_stage = stage
            state.completed_stages = list(range(1, stage))
            state.state_version += 1
        view = await service.resume(actor)
    if view.context == "refuge":
        view = await service.return_to_circle(actor, view.state_version)
    return await service.start_attempt(actor, view.state_version)


def _player(stats: CombatStats | None = None) -> Fighter:
    stats = stats or CombatStats(Decimal("702"), Decimal("100"), Decimal("85"), Decimal("90"))
    return Fighter(
        id="player",
        name="Errante",
        level=10,
        stats=stats,
        hp=stats.hp,
        race="remanescente",
        character_class="errante",
    )


def test_errante_templates_and_cycles_match_tdo_v1_0_12():
    expected = {
        1: ("trial_entity.errante.primeiro_corte", "580", "95", "85", "90"),
        2: ("trial_entity.errante.passo", "620", "105", "85", "90"),
        3: ("trial_entity.errante.brecha", "620", "100", "90", "95"),
    }
    for stage, (entity_id, hp, attack, defense, agility) in expected.items():
        definition = errante_stage_definition(stage)
        entity = definition.entities[0]
        assert entity.entity_id == entity_id
        assert entity.max_hp == Decimal(hp)
        assert entity.stats == {
            "attack": Decimal(attack),
            "defense": Decimal(defense),
            "agility": Decimal(agility),
        }
        assert entity.variant is None
        assert definition.required_conditions == (ERRANTE_CONDITION_IDS[stage],)

    assert errante_stage_definition(1).entities[0].action_ids == (
        ERRANTE_TRAINING_CUT_ACTION_ID,
    )
    assert errante_stage_definition(2).entities[0].action_ids == (
        ERRANTE_SHORT_CUT_ACTION_ID,
        ERRANTE_PREPARED_ACTION_ID,
    )
    assert errante_stage_definition(3).entities[0].action_ids == (
        ERRANTE_STAGE_3_CUT_A_ACTION_ID,
        ERRANTE_STAGE_3_CUT_B_ACTION_ID,
        ERRANTE_EXPOSE_ACTION_ID,
    )
    assert errante_enemy_actions(2)[ERRANTE_SHORT_CUT_ACTION_ID].coefficient == Decimal("0.95")
    assert errante_enemy_actions(2)[ERRANTE_PREPARED_ACTION_ID].coefficient == Decimal("1.65")
    assert errante_enemy_actions(2)[ERRANTE_PREPARED_ACTION_ID].prepared is True
    assert errante_enemy_actions(3)[ERRANTE_EXPOSE_ACTION_ID].self_effect_duration == 1
    assert errante_enemy_actions(3)[ERRANTE_EXPOSE_ACTION_ID].self_effect_magnitude == 0


def test_errante_stage_one_needs_a_correlated_real_bleed_tick():
    echo = ERRANTE_ENTITY_IDS[1]
    apply_id = "attempt-a:bleed-application"
    blocked_application = TrialCombatEvent(
        event_id="action-blocked",
        event_type="combat_action",
        actor_id="player",
        target_ids=(echo,),
        action_id=ERRANTE_ART_IDS["ferida_profunda"],
        dot_kind="bleed",
        effect_applied=False,
    )
    conditions, context = errante_conditions_for_event(1, blocked_application)
    assert not conditions
    assert context.get("bleed_application_event_ids", []) == []

    application = TrialCombatEvent(
        event_id="action-1",
        event_type="combat_action",
        actor_id="player",
        target_ids=(echo,),
        action_id=ERRANTE_ART_IDS["ferida_profunda"],
        dot_kind="bleed",
        dot_application_event_id=apply_id,
    )
    conditions, context = errante_conditions_for_event(1, application, context)
    assert not conditions
    assert context["bleed_application_event_ids"] == [apply_id]

    unrelated_tick = TrialCombatEvent(
        event_id="tick-unrelated",
        event_type="dot_tick",
        actor_id="player",
        target_ids=(echo,),
        dot_kind="bleed",
        dot_application_event_id="other-application",
        dot_source_id="player",
        effective_damage=Decimal("10"),
    )
    assert errante_conditions_for_event(1, unrelated_tick, context)[0] == ()

    legitimate_tick = TrialCombatEvent(
        event_id="tick-1",
        event_type="dot_tick",
        actor_id="player",
        target_ids=(echo,),
        dot_kind="bleed",
        dot_application_event_id=apply_id,
        dot_source_id="player",
        effective_damage=Decimal("10"),
    )
    assert errante_conditions_for_event(1, legitimate_tick, context)[0] == (
        ERRANTE_CONDITION_IDS[1],
    )
    assert errante_conditions_for_event(1, legitimate_tick, context)[0] == (
        ERRANTE_CONDITION_IDS[1],
    )


def test_errante_stage_two_requires_matching_prepared_response_then_window_damage():
    echo = ERRANTE_ENTITY_IDS[2]
    prepared_id = "combat:prepared:17"
    _, context = errante_conditions_for_event(
        2,
        TrialCombatEvent(
            event_id="prepare-1",
            event_type="prepared_action",
            actor_id=echo,
            action_id=ERRANTE_PREPARED_ACTION_ID,
            prepared_action_instance_id=prepared_id,
        ),
    )
    invalid_passo = TrialCombatEvent(
        event_id="passo-outside",
        event_type="combat_action",
        actor_id="player",
        target_ids=("player",),
        action_id=ERRANTE_ART_IDS["passo_velado"],
        action_instance_id="passo-1",
        actor_effect_id="errante.passo_velado.evasao",
    )
    assert errante_conditions_for_event(2, invalid_passo, context)[0] == ()

    valid_passo = TrialCombatEvent(
        event_id="passo-valid",
        event_type="combat_action",
        actor_id="player",
        target_ids=("player",),
        action_id=ERRANTE_ART_IDS["passo_velado"],
        action_instance_id="passo-2",
        actor_effect_id="errante.passo_velado.evasao",
        response_to_prepared_action_instance_id=prepared_id,
    )
    _, context = errante_conditions_for_event(2, valid_passo, context)
    no_damage = TrialCombatEvent(
        event_id="attack-no-damage",
        event_type="combat_action",
        actor_id="player",
        target_ids=(echo,),
        action_id="attack",
        action_instance_id="attack-1",
        actor_effect_ids=("errante.passo_velado.janela_ofensiva",),
        effective_damage=Decimal(0),
    )
    assert errante_conditions_for_event(2, no_damage, context)[0] == ()
    hit = TrialCombatEvent(
        event_id="attack-hit",
        event_type="combat_action",
        actor_id="player",
        target_ids=(echo,),
        action_id="attack",
        action_instance_id="attack-2",
        actor_effect_ids=("errante.passo_velado.janela_ofensiva",),
        effective_damage=Decimal("12"),
    )
    assert errante_conditions_for_event(2, hit, context)[0] == (ERRANTE_CONDITION_IDS[2],)


def test_errante_stage_three_requires_opportunity_art_during_active_exposed_effect():
    echo = ERRANTE_ENTITY_IDS[3]
    outside = TrialCombatEvent(
        event_id="opportunity-outside",
        event_type="combat_action",
        actor_id="player",
        target_ids=(echo,),
        action_id=ERRANTE_ART_IDS["golpe_oportuno"],
        target_effect_ids=(),
    )
    assert errante_conditions_for_event(3, outside)[0] == ()
    during = TrialCombatEvent(
        event_id="opportunity-exposed",
        event_type="combat_action",
        actor_id="player",
        target_ids=(echo,),
        action_id=ERRANTE_ART_IDS["golpe_oportuno"],
        target_effect_ids=(ERRANTE_EXPOSED_EFFECT_ID,),
        effective_damage=Decimal(0),
    )
    assert errante_conditions_for_event(3, during)[0] == (ERRANTE_CONDITION_IDS[3],)


def test_errante_combat_codec_round_trip_and_legacy_defaults():
    definition = errante_stage_definition(2, allowed_art_ids=(
        ERRANTE_ART_IDS["passo_velado"],
    ))
    combat = start_combat(create_errante_trial_combat(_player(), definition))
    combat.prepared_action = ERRANTE_PREPARED_ACTION_ID
    combat.prepared_source = "enemy"
    combat.prepared_target = "player"
    combat.prepared_action_instance_id = "prepared:trial:2"
    combat.fighters["player"].next_direct_crit_bonus = Decimal("10")
    combat.fighters["player"].next_direct_crit_expires_opportunity = 3
    combat.fighters["player"].next_direct_crit_effect_id = "window"
    combat.fighters["player"].effects.append(
        Effect(
            "evasion-window",
            "evasion",
            Decimal("15"),
            1,
            combat.fighters["player"].opportunity,
            kind="buff",
            stat_modifier_mode="percentage_points",
        )
    )
    assert combat.prepared_action == ERRANTE_PREPARED_ACTION_ID
    assert combat.prepared_action_instance_id
    snapshot = encode(combat)
    restored = decode(snapshot, combat.id, combat.ruleset, combat.version)
    assert restored.prepared_action_instance_id == combat.prepared_action_instance_id
    assert restored.player_actions[ERRANTE_ART_IDS["passo_velado"]].next_direct_crit_bonus == 10
    assert restored.fighters["player"].next_direct_crit_bonus == Decimal("10")
    assert restored.fighters["player"].next_direct_crit_expires_opportunity == 3
    assert restored.fighters["player"].next_direct_crit_effect_id == "window"
    assert restored.fighters["player"].effects[0].stat_modifier_mode == "percentage_points"

    legacy = encode(combat)
    legacy.pop("prepared_action_instance_id", None)
    for actions in (legacy["player_actions"], legacy["enemy_actions"]):
        for action in actions.values():
            action.pop("next_direct_crit_bonus", None)
            action.pop("next_direct_crit_duration", None)
            action.pop("next_direct_crit_effect_id", None)
            action.pop("crit_bonus_if_target_debuffed", None)
            action.pop("self_effect_modifier_mode", None)
    for fighter in legacy["fighters"].values():
        fighter.pop("next_direct_crit_bonus", None)
        fighter.pop("next_direct_crit_expires_opportunity", None)
        fighter.pop("next_direct_crit_effect_id", None)
        for effect in fighter["effects"]:
            effect.pop("stat_modifier_mode", None)
    for event in legacy["events"] + legacy["mechanic_events"]:
        event.pop("actor_effect_ids", None)
        event.pop("prepared_action_instance_id", None)
        event.pop("response_to_prepared_action_instance_id", None)
        event.pop("dot_kind", None)
        event.pop("dot_application_event_id", None)
        event.pop("dot_source_id", None)
    old = decode(legacy, combat.id, combat.ruleset, combat.version)
    assert old.prepared_action_instance_id is None
    assert old.fighters["player"].next_direct_crit_bonus == 0
    assert old.fighters["player"].next_direct_crit_expires_opportunity is None
    assert old.player_actions[ERRANTE_ART_IDS["passo_velado"]].self_effect_modifier_mode == (
        "multiplicative"
    )
    assert old.fighters["player"].effects[0].stat_modifier_mode == "multiplicative"


@pytest.mark.asyncio
async def test_errante_attempt_uses_persisted_active_arts_and_reconnects(database):
    actor = 998801
    character_id, sessions, service = await _seed_errante(database, actor)
    arts = (
        ERRANTE_ART_IDS["corte_veloz"],
        ERRANTE_ART_IDS["ferida_profunda"],
        ERRANTE_ART_IDS["passo_velado"],
    )
    active = await _start_errante(service, actor, arts)
    assert active.kind == "active"
    assert active.trial_id == "trial.errante.brecha"
    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None
    assert {fighter.id for key, fighter in combat.fighters.items() if key != "player"} == {
        ERRANTE_ENTITY_IDS[1]
    }
    assert combat.variant is None
    assert combat.external_consumables_allowed is False
    assert combat.consumable_uses == 0
    assert set(combat.player_actions) == {"attack", *arts}
    assert combat.fighters["player"].hp == combat.fighters["player"].stats.hp

    prepared = await service.action(
        actor, active.attempt_id, combat.version, ERRANTE_ART_IDS["ferida_profunda"]
    )
    assert prepared is not None
    assert prepared.attempt_state["pedagogic_context"].get("bleed_application_event_ids")
    assert prepared.attempt_state["pedagogic_conditions"] == [ERRANTE_CONDITION_IDS[1]]
    resumed = await service.resume(actor)
    restored = await service.combat(actor, active.attempt_id)
    assert resumed.attempt_id == active.attempt_id
    assert restored.id == combat.id
    assert resumed.attempt_state["pedagogic_conditions"] == [ERRANTE_CONDITION_IDS[1]]

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.vigor == 37
        assert await session.scalar(select(RewardEvent.id).where(
            RewardEvent.character_id == character_id
        )) is None
        assert await session.scalar(select(BestiaryEntry.id).where(
            BestiaryEntry.character_id == character_id
        )) is None
        assert await session.scalar(select(MaterialStack.character_id).where(
            MaterialStack.character_id == character_id
        )) is None


@pytest.mark.asyncio
async def test_errante_defeat_discards_attempt_state_and_retry_keeps_stage(database):
    actor = 998802
    _, sessions, service = await _seed_errante(database, actor)
    arts = (ERRANTE_ART_IDS["passo_velado"], ERRANTE_ART_IDS["corte_veloz"])
    active = await _start_errante(service, actor, arts, stage=2)
    definition = active.stage_definition
    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None and combat.variant is None
    assert ERRANTE_PREPARED_ACTION_ID in combat.enemy_actions
    assert combat.player_actions[ERRANTE_ART_IDS["passo_velado"]].next_direct_crit_bonus == 10
    failed = await service.fail_attempt(actor, active.attempt_id, active.state_version)
    assert failed.status == "ready"
    assert failed.current_stage == 2
    assert failed.completed_stages == (1,)
    assert failed.attempt_state is None
    retry = await service.start_attempt(actor, failed.state_version)
    assert retry.status == "active"
    assert retry.current_stage == 2
    assert retry.attempt_id != active.attempt_id
    retry_entity = retry.stage_definition["entities"][0]["entity_id"]
    original_entity = definition["entities"][0]["entity_id"]
    assert retry_entity == original_entity
    assert retry.attempt_state["pedagogic_conditions"] == []
    assert retry.attempt_state["pedagogic_context"] == {}
    assert retry.attempt_state["external_consumables_used"] == 0
    combat_retry = await service.combat(actor, retry.attempt_id)
    assert combat_retry is not None and combat_retry.variant is None
    async with sessions() as session:
        character = await session.scalar(select(Character).where(
            Character.telegram_id == actor
        ))
        assert character.vigor == 37
        assert await session.scalar(select(RewardEvent.id).where(
            RewardEvent.character_id == character.id
        )) is None


@pytest.mark.asyncio
async def test_errante_stage_two_uses_prepared_response_and_rng_independent_window(database):
    actor = 998803
    _, _, service = await _seed_errante(database, actor)
    arts = (ERRANTE_ART_IDS["passo_velado"], ERRANTE_ART_IDS["corte_veloz"])
    active = await _start_errante(service, actor, arts, stage=2)
    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None

    for _ in range(3):
        if combat.prepared_action == ERRANTE_PREPARED_ACTION_ID:
            break
        active = await service.action(actor, active.attempt_id, combat.version, "attack")
        combat = await service.combat(actor, active.attempt_id)
        assert combat is not None
    assert combat.prepared_action == ERRANTE_PREPARED_ACTION_ID
    prepared_id = combat.prepared_action_instance_id
    assert prepared_id

    active = await service.action(
        actor,
        active.attempt_id,
        combat.version,
        ERRANTE_ART_IDS["passo_velado"],
    )
    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None
    passo_event = next(
        event
        for event in reversed(combat.events)
        if event.action == ERRANTE_ART_IDS["passo_velado"]
    )
    assert passo_event.response_to_prepared_action_instance_id == prepared_id
    assert passo_event.actor_effect_id == "errante.passo_velado.evasao"
    assert combat.fighters["player"].stat("evasion") == (
        combat.fighters["player"].stats.evasion + Decimal("15")
    )

    active = await service.action(actor, active.attempt_id, combat.version, "attack")
    assert ERRANTE_CONDITION_IDS[2] in active.attempt_state["pedagogic_conditions"]
    hit = next(
        event
        for event in reversed((await service.combat(actor, active.attempt_id)).events)
        if event.action == "attack"
    )
    assert hit.effective_damage > 0
    assert "errante.passo_velado.janela_ofensiva" in hit.actor_effect_ids
    assert not hit.dodged


@pytest.mark.asyncio
async def test_errante_stage_three_applies_exposed_marker_without_extra_damage_gate(database):
    actor = 998804
    _, _, service = await _seed_errante(database, actor)
    arts = (ERRANTE_ART_IDS["golpe_oportuno"], ERRANTE_ART_IDS["corte_veloz"])
    active = await _start_errante(service, actor, arts, stage=3)
    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None

    for _ in range(4):
        echo = combat.fighters["enemy"]
        if any(effect.id == ERRANTE_EXPOSED_EFFECT_ID for effect in echo.effects):
            break
        active = await service.action(actor, active.attempt_id, combat.version, "attack")
        combat = await service.combat(actor, active.attempt_id)
        assert combat is not None
    echo = combat.fighters["enemy"]
    assert any(effect.id == ERRANTE_EXPOSED_EFFECT_ID for effect in echo.effects)
    assert next(
        effect for effect in echo.effects if effect.id == ERRANTE_EXPOSED_EFFECT_ID
    ).magnitude == 0

    active = await service.action(
        actor,
        active.attempt_id,
        combat.version,
        ERRANTE_ART_IDS["golpe_oportuno"],
    )
    assert ERRANTE_CONDITION_IDS[3] in active.attempt_state["pedagogic_conditions"]
    opportunity = next(
        event
        for event in reversed((await service.combat(actor, active.attempt_id)).events)
        if event.action == ERRANTE_ART_IDS["golpe_oportuno"]
    )
    assert ERRANTE_EXPOSED_EFFECT_ID in opportunity.target_effect_ids


@pytest.mark.asyncio
async def test_errante_stage_three_completion_unlocks_paths_once(database):
    actor = 998805
    character_id, sessions, service = await _seed_errante(database, actor)
    arts = (ERRANTE_ART_IDS["golpe_oportuno"], ERRANTE_ART_IDS["corte_veloz"])
    active = await _start_errante(service, actor, arts, stage=3)
    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None

    for _ in range(4):
        exposed = any(
            effect.id == ERRANTE_EXPOSED_EFFECT_ID
            for effect in combat.fighters["enemy"].effects
        )
        if exposed:
            break
        active = await service.action(actor, active.attempt_id, combat.version, "attack")
        combat = await service.combat(actor, active.attempt_id)
        assert combat is not None
    active = await service.action(
        actor,
        active.attempt_id,
        combat.version,
        ERRANTE_ART_IDS["golpe_oportuno"],
    )
    assert ERRANTE_CONDITION_IDS[3] in active.attempt_state["pedagogic_conditions"]

    combat = await service.combat(actor, active.attempt_id)
    combat.fighters["enemy"].hp = Decimal(1)
    async with sessions.begin() as session:
        encounter = await session.scalar(
            select(Encounter).where(Encounter.game_activity_id == active.attempt_id)
        )
        record = await session.scalar(
            select(CombatRecord).where(CombatRecord.encounter_id == encounter.id)
        )
        record.snapshot = encode(combat)
    completed = await service.action(actor, active.attempt_id, combat.version, "attack")
    assert completed.kind == "completed"
    assert completed.completed_stages == (1, 2, 3)
    assert completed.available_paths == ("carrasco", "sabotador")
    assert completed.selected_path is None
    assert completed.path_art_unlocked is False
    assert completed.path_art_min_level == 12

    duplicate = await service.complete_stage(actor, active.attempt_id, completed.state_version)
    resumed = await service.resume(actor)
    assert duplicate.kind == "completed"
    assert resumed.kind == "completed"
    assert resumed.selected_path is None
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "class_trial_completed",
            )
        ) is not None
        character = await session.get(Character, character_id)
        assert character.xp == 0 and character.crowns == 23 and character.vigor == 37
        assert await session.scalar(
            select(RewardEvent.id).where(RewardEvent.character_id == character_id)
        ) is None

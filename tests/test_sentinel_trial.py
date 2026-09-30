from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.active_arts import ActiveArtService
from asterion.application.class_trials import ClassTrialService
from asterion.domain.class_trials import (
    SENTINEL_ART_IDS,
    SENTINEL_CONDITION_IDS,
    SENTINEL_ENTITY_IDS,
    TrialCombatEvent,
    create_sentinel_trial_combat,
    reset_trial_combat,
    sentinel_conditions_for_event,
    sentinel_stage_definition,
    trial_event_from_combat_event,
)
from asterion.domain.combat import (
    Fighter,
    act,
    allowed_actions,
    combat_consumable_options,
    start_combat,
)
from asterion.domain.combat_math import CombatStats, resolve_combat_stats
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    Character,
    ClassTrialState,
    CodexEntry,
    CombatRecord,
    Encounter,
    GameActivity,
    MaterialStack,
    RewardComponent,
    RewardEvent,
    WorldState,
)

REGION = "Terras do Ocaso"
REFUGE = "Refúgio do Ocaso"
SENTINEL = "sentinela"


async def _seed_sentinel(database, actor: int):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats(SENTINEL, 10, "remanescente")
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Sentinela{chr(ord('a') + actor % 26)}",
                race="remanescente",
                character_class=SENTINEL,
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


async def _start_sentinel(service, actor: int, arts=(), *, stage: int = 1):
    art_service = ActiveArtService(service.sessions, service.server_id)
    for slot, art_id in enumerate(tuple(arts), start=1):
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


async def _take(service, actor, view, action):
    assert view.combat_version is not None
    return await service.action(actor, view.attempt_id, view.combat_version, action)


@pytest.mark.asyncio
async def test_each_sentinel_stage_materializes_only_its_documented_echo(database):
    arts = tuple(SENTINEL_ART_IDS.values())[:3]
    for offset, stage in enumerate((1, 2, 3)):
        actor = 998101 + offset
        _, _, service = await _seed_sentinel(database, actor)
        active = await _start_sentinel(service, actor, arts, stage=stage)
        assert active.kind == "active" and active.current_stage == stage
        assert active.stage_definition["stage"] == stage
        combat = await service.combat(actor, active.attempt_id)
        expected_echo = SENTINEL_ENTITY_IDS[stage]
        assert {fighter.id for key, fighter in combat.fighters.items() if key != "player"} == {
            expected_echo
        }
        assert combat.variant is None
        assert combat.external_consumables_allowed is False
        assert combat.configuration_snapshot["equipped_class_art_ids"] == list(arts)
        assert combat.configuration_snapshot["active_arts"] == [
            {"slot": slot, "art_id": art_id}
            for slot, art_id in enumerate(arts, start=1)
        ]
        assert combat.fighters["player"].hp == combat.fighters["player"].stats.hp
        assert combat.fighters["player"].effects == []
        assert combat.fighters["player"].barrier == 0
        assert combat.fighters["player"].cooldowns == {}
        assert set(combat.ai_cycle) == set(active.stage_definition["entities"][0]["action_ids"])
        assert set(combat.enemy_actions) == set(combat.ai_cycle)
        # The definition builder itself exposes the distinct documented identities.
        definition = sentinel_stage_definition(stage)
        assert [entity.entity_id for entity in definition.entities] == [
            SENTINEL_ENTITY_IDS[stage]
        ]


@pytest.mark.asyncio
async def test_stage_one_prepared_impact_records_valid_defender_mitigation_and_reconnect(database):
    actor = 998104
    character_id, sessions, service = await _seed_sentinel(database, actor)
    active = await _start_sentinel(service, actor)
    attempt_id = active.attempt_id
    combat = await service.combat(actor, attempt_id)

    for _ in range(6):
        if combat.prepared_action is not None:
            break
        active = await _take(service, actor, active, "attack")
        combat = await service.combat(actor, attempt_id)
    assert combat.prepared_action == "trial.sentinela.impacto_anunciado"
    assert combat.response_window_seen is True

    resumed = await service.resume(actor)
    restored = await service.combat(actor, attempt_id)
    assert resumed.attempt_id == attempt_id
    assert resumed.encounter_id == active.encounter_id
    assert resumed.combat_id == active.combat_id
    assert restored.prepared_action == combat.prepared_action
    assert restored.prepared_target == combat.prepared_target
    assert restored.response_window_seen is True

    before = resumed.combat_version
    after_defend = await service.action(actor, attempt_id, before, "defend")
    resolved = await service.combat(actor, attempt_id)
    assert after_defend.attempt_state["pedagogic_conditions"] == [
        SENTINEL_CONDITION_IDS[1]
    ]
    resolution = next(
        event
        for event in resolved.events
        if event.action == "trial.sentinela.impacto_anunciado"
        and event.prepared_resolution
    )
    assert resolution.actor_entity_id == SENTINEL_ENTITY_IDS[1]
    assert resolution.target == "player"
    assert resolution.defender_mitigation_applied is True
    assert resolution.dodged is False

    stale = await service.action(actor, attempt_id, before, "attack")
    assert stale.combat_version == after_defend.combat_version
    condition_events = [
        row
        for row in after_defend.attempt_state["events"]
        if SENTINEL_CONDITION_IDS[1] in row["conditions"]
    ]
    assert len(condition_events) == 1
    assert len(set(after_defend.attempt_state["processed_event_ids"])) == len(
        after_defend.attempt_state["processed_event_ids"]
    )
    assert stale.attempt_state["pedagogic_conditions"] == [SENTINEL_CONDITION_IDS[1]]
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.vigor == 37
        assert character.crowns == 23 and character.xp == 0


@pytest.mark.asyncio
async def test_stage_one_muralha_requires_absorbed_damage_and_defender_path_is_distinct(database):
    actor = 998105
    _, _, service = await _seed_sentinel(database, actor)
    active = await _start_sentinel(
        service, actor, (SENTINEL_ART_IDS["muralha_breve"],)
    )
    attempt_id = active.attempt_id
    combat = await service.combat(actor, attempt_id)
    for _ in range(6):
        if combat.prepared_action is not None:
            break
        active = await _take(service, actor, active, "attack")
        combat = await service.combat(actor, attempt_id)
    active = await _take(service, actor, active, SENTINEL_ART_IDS["muralha_breve"])
    combat = await service.combat(actor, attempt_id)
    resolution = next(
        event
        for event in combat.events
        if event.action == "trial.sentinela.impacto_anunciado"
        and event.prepared_resolution
    )
    assert resolution.target_barrier_source == f"player:{SENTINEL_ART_IDS['muralha_breve']}"
    assert resolution.barrier_absorbed >= 1
    assert active.attempt_state["pedagogic_conditions"] == [SENTINEL_CONDITION_IDS[1]]


def test_sentinel_condition_interpreters_ignore_rng_and_require_resolution_facts():
    echo = SENTINEL_ENTITY_IDS[1]
    miss = TrialCombatEvent(
        "miss",
        "combat_action",
        echo,
        target_ids=("player",),
        action_id="trial.sentinela.impacto_anunciado",
        prepared_resolution=True,
        dodged=True,
    )
    assert sentinel_conditions_for_event(1, miss) == ()

    unrelated = TrialCombatEvent(
        "unrelated",
        "combat_action",
        echo,
        target_ids=("player",),
        action_id="trial.sentinela.golpe_contido",
        prepared_resolution=True,
        defender_mitigation_applied=True,
    )
    assert sentinel_conditions_for_event(1, unrelated) == ()

    outside_window = TrialCombatEvent(
        "outside",
        "combat_action",
        "player",
        target_ids=(SENTINEL_ENTITY_IDS[2],),
        action_id="attack",
        effective_damage=Decimal(10),
    )
    no_damage = TrialCombatEvent(
        "no-damage",
        "combat_action",
        "player",
        target_ids=(SENTINEL_ENTITY_IDS[2],),
        action_id="attack",
        target_effect_ids=("sentinel.quebra_postura",),
        effective_damage=Decimal(0),
    )
    hit_during_window = TrialCombatEvent(
        "window-hit",
        "combat_action",
        "player",
        target_ids=(SENTINEL_ENTITY_IDS[2],),
        action_id="attack",
        target_effect_ids=("sentinel.quebra_postura",),
        effective_damage=Decimal(1),
    )
    assert sentinel_conditions_for_event(2, outside_window) == ()
    assert sentinel_conditions_for_event(2, no_damage) == ()
    assert sentinel_conditions_for_event(2, hit_during_window) == (
        SENTINEL_CONDITION_IDS[2],
    )
    assert sentinel_conditions_for_event(2, hit_during_window) == (
        SENTINEL_CONDITION_IDS[2],
    )  # the domain condition is a stable id; persistence de-duplicates it.

    without_retaliation = TrialCombatEvent(
        "no-retaliation",
        "combat_action",
        "player",
        target_ids=(SENTINEL_ENTITY_IDS[3],),
        action_id=SENTINEL_ART_IDS["impacto_resoluto"],
    )
    with_retaliation = TrialCombatEvent(
        "retaliation",
        "combat_action",
        "player",
        target_ids=(SENTINEL_ENTITY_IDS[3],),
        action_id=SENTINEL_ART_IDS["impacto_resoluto"],
        retaliation_valid=True,
        retaliation_used=True,
        retaliation_activation_id="ret-1",
        retaliation_source_type="defender",
        retaliation_source_actor_id=SENTINEL_ENTITY_IDS[3],
        dodged=True,
    )
    other_action = TrialCombatEvent(
        "other-action",
        "combat_action",
        "player",
        target_ids=(SENTINEL_ENTITY_IDS[3],),
        action_id="attack",
        retaliation_valid=True,
        retaliation_used=True,
        retaliation_activation_id="ret-2",
        retaliation_source_type="defender",
        retaliation_source_actor_id=SENTINEL_ENTITY_IDS[3],
    )
    assert sentinel_conditions_for_event(3, without_retaliation) == ()
    assert sentinel_conditions_for_event(3, other_action) == ()
    assert sentinel_conditions_for_event(3, with_retaliation) == (
        SENTINEL_CONDITION_IDS[3],
    )


@pytest.mark.asyncio
async def test_stage_two_window_is_snapshotted_at_hit_and_survives_expiry_and_reconnect(database):
    actor = 998106
    _, _, service = await _seed_sentinel(database, actor)
    active = await _start_sentinel(
        service, actor, (SENTINEL_ART_IDS["quebra_postura"],), stage=2
    )
    attempt_id = active.attempt_id
    active = await _take(service, actor, active, SENTINEL_ART_IDS["quebra_postura"])
    combat = await service.combat(actor, attempt_id)
    echo = combat.fighters["enemy"]
    assert any(effect.id == "sentinel.quebra_postura" for effect in echo.effects)
    resumed = await service.resume(actor)
    assert resumed.attempt_id == attempt_id
    assert any(
        effect.id == "sentinel.quebra_postura"
        for effect in (await service.combat(actor, attempt_id)).fighters["enemy"].effects
    )

    active = await _take(service, actor, active, "attack")
    combat = await service.combat(actor, attempt_id)
    hit = next(
        event
        for event in combat.events
        if event.actor == "player" and event.action == "attack"
    )
    assert "sentinel.quebra_postura" in hit.target_effect_ids
    assert hit.effective_damage > 0
    assert active.attempt_state["pedagogic_conditions"] == [SENTINEL_CONDITION_IDS[2]]
    assert not any(
        effect.id == "sentinel.quebra_postura"
        for effect in combat.fighters["enemy"].effects
    )
    assert (await service.resume(actor)).attempt_state["pedagogic_conditions"] == [
        SENTINEL_CONDITION_IDS[2]
    ]


@pytest.mark.asyncio
async def test_stage_three_uses_real_defender_retaliation_and_impacto_resoluto(database):
    actor = 998108
    _, _, service = await _seed_sentinel(database, actor)
    active = await _start_sentinel(
        service, actor, (SENTINEL_ART_IDS["impacto_resoluto"],), stage=3
    )
    attempt_id = active.attempt_id
    combat = await service.combat(actor, attempt_id)

    for _ in range(6):
        if combat.prepared_action == "trial.sentinela.martelo_anunciado":
            break
        active = await _take(service, actor, active, "attack")
        combat = await service.combat(actor, attempt_id)
    assert combat.prepared_action == "trial.sentinela.martelo_anunciado"
    assert combat.response_window_seen is True

    active = await _take(service, actor, active, "defend")
    combat = await service.combat(actor, attempt_id)
    player = combat.fighters["player"]
    assert player.retaliation_charges == 1
    assert player.retaliation_remaining == 1
    assert player.retaliation_source_type == "defender"
    assert player.retaliation_source_actor_id == SENTINEL_ENTITY_IDS[3]
    activation_id = player.retaliation_activation_id
    assert activation_id
    martelo = next(
        event
        for event in combat.events
        if event.action == "trial.sentinela.martelo_anunciado"
        and event.prepared_resolution
    )
    assert martelo.defender_prevented_damage > 0

    resumed = await service.resume(actor)
    restored = await service.combat(actor, attempt_id)
    assert resumed.attempt_id == attempt_id
    assert restored.fighters["player"].retaliation_activation_id == activation_id
    assert restored.fighters["player"].retaliation_charges == 1

    active = await _take(service, actor, resumed, SENTINEL_ART_IDS["impacto_resoluto"])
    combat = await service.combat(actor, attempt_id)
    impacto = next(
        event
        for event in combat.events
        if event.actor == "player"
        and event.action == SENTINEL_ART_IDS["impacto_resoluto"]
    )
    assert impacto.retaliation_used is True
    assert impacto.retaliation_valid is True
    assert impacto.retaliation_activation_id == activation_id
    assert impacto.retaliation_source_type == "defender"
    assert impacto.retaliation_source_actor_id == SENTINEL_ENTITY_IDS[3]
    assert SENTINEL_CONDITION_IDS[3] in active.attempt_state["pedagogic_conditions"]
    assert combat.fighters["player"].retaliation_charges == 0



@pytest.mark.asyncio
async def test_trial_attempt_has_no_external_consumables_or_economic_side_effects(database):
    actor = 998107
    character_id, sessions, service = await _seed_sentinel(database, actor)
    active = await _start_sentinel(service, actor, tuple(SENTINEL_ART_IDS.values())[:3])
    combat = await service.combat(actor, active.attempt_id)
    assert combat_consumable_options(
        combat, ("consumable.herb_gray",), budget_limit=99
    ) == ()
    assert combat.external_consumables_allowed is False
    assert combat.consumable_uses == 0
    assert active.attempt_state["external_consumables_used"] == 0
    stale_consumable = await service.action(
        actor,
        active.attempt_id,
        active.combat_version,
        "consumable:consumable.heal",
    )
    assert stale_consumable.combat_version == active.combat_version
    assert stale_consumable.attempt_state["external_consumables_used"] == 0

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.vigor == 37
        for model in (
            RewardEvent,
            BestiaryEntry,
            CodexEntry,
            MaterialStack,
        ):
            assert await session.scalar(
                select(func.count()).select_from(model).where(
                    model.character_id == character_id
                )
            ) == 0
        assert await session.scalar(
            select(func.count())
            .select_from(RewardComponent)
            .join(RewardEvent)
            .where(RewardEvent.character_id == character_id)
        ) == 0


@pytest.mark.asyncio
async def test_sentinel_stage_checkpoint_then_stage_two_defeat_and_retry(database):
    actor = 998109
    character_id, sessions, service = await _seed_sentinel(database, actor)
    active = await _start_sentinel(service, actor)
    first_plan = active.stage_definition
    for _ in range(24):
        combat = await service.combat(actor, active.attempt_id)
        action = "defend" if combat.prepared_action else "attack"
        active = await _take(service, actor, active, action)
        if active.kind != "active":
            break
    assert active.kind == "ready"
    assert active.current_stage == 2
    assert active.completed_stages == (1,)

    art_service = ActiveArtService(service.sessions, service.server_id)
    await art_service.equip_art(actor, 1, SENTINEL_ART_IDS["quebra_postura"])
    stage_two = await service.start_attempt(actor, active.state_version)
    stage_two_plan = stage_two.stage_definition
    stage_two = await _take(
        service, actor, stage_two, SENTINEL_ART_IDS["quebra_postura"]
    )
    stage_two = await _take(service, actor, stage_two, "attack")
    assert stage_two.attempt_state["pedagogic_conditions"] == [
        SENTINEL_CONDITION_IDS[2]
    ]
    async with sessions.begin() as session:
        activity = await session.get(GameActivity, stage_two.attempt_id)
        encounter, record = (
            await session.execute(
                select(Encounter, CombatRecord)
                .join(CombatRecord, CombatRecord.encounter_id == Encounter.id)
                .where(Encounter.game_activity_id == activity.id)
            )
        ).one()
        combat = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        combat.fighters["player"].hp = Decimal(1)
        combat.evasion_streaks["player"] = 2
        record.snapshot = encode(combat)
        (await session.get(Character, character_id)).hp = Decimal(1)

    failed = await _take(service, actor, stage_two, "attack")
    assert failed.kind == "ready"
    assert failed.current_stage == 2
    assert failed.completed_stages == (1,)
    assert failed.stage_definition == stage_two_plan
    assert failed.attempt_state is None

    retried = await service.start_attempt(actor, failed.state_version)
    assert retried.attempt_id != stage_two.attempt_id
    assert retried.stage_definition == stage_two_plan
    assert retried.completed_stages == (1,)
    assert retried.attempt_state["pedagogic_conditions"] == []
    assert first_plan["stage"] == 1
    assert retried.encounter_id != stage_two.encounter_id
    retried_combat = await service.combat(actor, retried.attempt_id)
    assert retried_combat.fighters["player"].hp == retried_combat.fighters["player"].stats.hp
    assert retried_combat.fighters["player"].effects == []
    assert retried_combat.fighters["player"].barrier == 0
    assert retried_combat.fighters["player"].cooldowns == {}
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert (character.xp, character.crowns, character.vigor) == (0, 23, 37)
        for model in (RewardEvent, BestiaryEntry, CodexEntry, MaterialStack):
            assert await session.scalar(
                select(func.count()).select_from(model).where(
                    model.character_id == character_id
                )
            ) == 0


@pytest.mark.asyncio
async def test_victory_without_pedagogy_ends_attempt_without_checkpoint(database):
    actor = 998110
    _, sessions, service = await _seed_sentinel(database, actor)
    active = await _start_sentinel(service, actor)
    attempt_id = active.attempt_id
    async with sessions.begin() as session:
        activity = await session.get(GameActivity, attempt_id)
        encounter, record = (
            await session.execute(
                select(Encounter, CombatRecord)
                .join(CombatRecord, CombatRecord.encounter_id == Encounter.id)
                .where(Encounter.game_activity_id == activity.id)
            )
        ).one()
        combat = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        combat.fighters["enemy"].hp = Decimal(1)
        record.snapshot = encode(combat)

    ended = await _take(service, actor, active, "attack")
    assert ended.kind == "ready"
    assert ended.current_stage == 1
    assert ended.completed_stages == ()
    assert ended.attempt_state is None
    async with sessions() as session:
        activity = await session.get(GameActivity, attempt_id)
        state = await session.get(ClassTrialState, active.character_id)
        assert activity.status == "failed"
        assert state.status == "ready"
        assert state.current_stage == 1
        assert state.completed_stages == []


def test_trial_combat_codec_roundtrip_and_legacy_defaults():
    definition = sentinel_stage_definition(
        3, allowed_art_ids=(SENTINEL_ART_IDS["impacto_resoluto"],)
    )
    player = Fighter(
        "player",
        "Sentinela",
        10,
        CombatStats(Decimal(1000), Decimal(10), Decimal(1000), Decimal(1)),
        Decimal(1000),
        race="remanescente",
        character_class=SENTINEL,
    )
    combat = start_combat(
        reset_trial_combat(
            create_sentinel_trial_combat(player, definition), definition, Decimal(1000)
        )
    )
    restored = decode(encode(combat), combat.id, combat.ruleset, combat.version)
    assert restored.external_consumables_allowed is False
    assert restored.enemy_actions["trial.sentinela.martelo_anunciado"].self_effect_id == (
        "sentinel.guarda_aberta"
    )
    assert restored.events == combat.events

    legacy_payload = deepcopy(encode(combat))
    legacy_payload.pop("external_consumables_allowed")
    legacy_payload.pop("mechanic_events", None)
    for actions in (legacy_payload["player_actions"], legacy_payload["enemy_actions"]):
        for action in actions.values():
            action.pop("effect_id", None)
            action.pop("self_effect_stat", None)
            action.pop("self_effect_magnitude", None)
            action.pop("self_effect_duration", None)
            action.pop("self_effect_id", None)
    for event in legacy_payload["events"]:
        for key in (
            "actor_entity_id",
            "actor_effect_id",
            "calculated_damage",
            "effective_damage",
            "target_defending",
            "defender_mitigation_applied",
            "target_barrier_source",
            "prepared_resolution",
            "target_effect_ids",
            "defender_prevented_damage",
            "retaliation_valid",
            "retaliation_used",
            "retaliation_event",
            "retaliation_activation_id",
            "retaliation_source_type",
            "retaliation_source_event_id",
            "retaliation_source_actor_id",
            "retaliation_remaining",
            "internal",
        ):
            event.pop(key, None)
    legacy = decode(legacy_payload, combat.id, combat.ruleset, combat.version)
    assert legacy.external_consumables_allowed is True
    assert legacy.enemy_actions["trial.sentinela.martelo_anunciado"].self_effect_id is None
    assert legacy.events[0].actor_entity_id == ""
    assert legacy.events[0].target_effect_ids == ()


def test_stage_three_shared_engine_retaliation_pipeline_is_rng_independent():
    definition = sentinel_stage_definition(
        3, allowed_art_ids=(SENTINEL_ART_IDS["impacto_resoluto"],)
    )
    player = Fighter(
        "player",
        "Sentinela",
        10,
        CombatStats(Decimal(1000), Decimal(120), Decimal(100), Decimal(100)),
        Decimal(1000),
        race="remanescente",
        character_class=SENTINEL,
    )
    combat = start_combat(
        reset_trial_combat(
            create_sentinel_trial_combat(player, definition), definition, Decimal(1000)
        )
    )

    for _ in range(6):
        if combat.prepared_action == "trial.sentinela.martelo_anunciado":
            break
        combat = act(combat, "attack")
    assert combat.prepared_action == "trial.sentinela.martelo_anunciado"

    combat = act(combat, "defend")
    player = combat.fighters["player"]
    assert player.retaliation_charges == 1
    assert player.retaliation_source_actor_id == SENTINEL_ENTITY_IDS[3]
    activation_id = player.retaliation_activation_id

    enemy = combat.fighters["enemy"]
    enemy.stats = replace(enemy.stats, evasion=Decimal(100))
    before = len(combat.events)
    combat = act(combat, SENTINEL_ART_IDS["impacto_resoluto"])
    impacto = next(
        event
        for event in combat.events[before:]
        if event.actor == "player"
        and event.action == SENTINEL_ART_IDS["impacto_resoluto"]
    )
    trial_event = trial_event_from_combat_event(combat, impacto)

    assert impacto.dodged is True
    assert impacto.retaliation_used is True
    assert impacto.retaliation_activation_id == activation_id
    assert sentinel_conditions_for_event(3, trial_event) == (SENTINEL_CONDITION_IDS[3],)



def test_stage_three_echo_applies_its_own_guard_open_effect():
    definition = sentinel_stage_definition(
        3, allowed_art_ids=(SENTINEL_ART_IDS["impacto_resoluto"],)
    )
    player = Fighter(
        "player",
        "Sentinela",
        10,
        CombatStats(Decimal(1000), Decimal(10), Decimal(1000), Decimal(1)),
        Decimal(1000),
        race="remanescente",
        character_class=SENTINEL,
    )
    combat = start_combat(
        reset_trial_combat(
            create_sentinel_trial_combat(player, definition), definition, Decimal(1000)
        )
    )
    for _ in range(6):
        if any(
            event.action == "trial.sentinela.martelo_anunciado"
            and event.prepared_resolution
            for event in combat.events
        ):
            break
        assert "attack" in allowed_actions(combat)
        combat = act(combat, "attack")
    event = next(
        event
        for event in combat.events
        if event.action == "trial.sentinela.martelo_anunciado"
        and event.prepared_resolution
    )
    assert event.actor_effect_id == "sentinel.guarda_aberta"
    assert any(effect.id == "sentinel.guarda_aberta" for effect in combat.fighters["enemy"].effects)
    from asterion.bot.combat_ui import event_line

    assert "própria DEF" in event_line(combat, event)


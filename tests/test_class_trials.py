from decimal import Decimal
from itertools import count
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.class_trials import ClassTrialService
from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.domain import class_trials as class_trials_domain
from asterion.domain.arts import (
    LUMINAR_ART_IDS,
    ORACULO_ART_IDS,
    TECELAO_ART_IDS,
    VIGIA_ART_IDS,
)
from asterion.domain.class_trials import (
    CLASS_PATHS,
    LUMINAR_ALLY_ENTITY_ID,
    LUMINAR_CONDITION_IDS,
    ORACULO_CONDITION_IDS,
    ORACULO_OFFENSIVE_WINDOW_TAG,
    ORACULO_SINAL_EFFECT_ID,
    TRIAL_COMPLETED_UNLOCK,
    TRIAL_IDS_BY_CLASS,
    TrialCombatEvent,
    TrialEntityDefinition,
)
from asterion.domain.combat import allowed_actions
from asterion.domain.combat_math import resolve_combat_stats
from asterion.infrastructure.db.combat_codec import encode
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    Character,
    CharacterActiveArtSlot,
    ClassTrialState,
    CodexEntry,
    CombatRecord,
    ConsumableStack,
    Encounter,
    GameActivity,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

REFUGE = "Refúgio do Ocaso"
REGION = "Terras do Ocaso"


async def _seed_trial(
    database,
    actor: int,
    *,
    level: int = 10,
    location: str = REFUGE,
    character_class: str = "luminar",
    active_art_ids: tuple[str, ...] = (),
):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats(character_class, level, "remanescente")
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Hero{chr(ord('a') + actor % 26)}",
                race="remanescente",
                character_class=character_class,
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=level,
                xp=0,
                hp=Decimal("1"),
                max_hp=stats.hp,
                vigor=37,
                max_vigor=100,
                crowns=23,
            )
        )
        session.add_all(
            CharacterActiveArtSlot(
                character_id=character_id,
                slot=slot,
                art_id=art_id,
            )
            for slot, art_id in enumerate(active_art_ids, start=1)
        )
        session.add(
            WorldState(character_id=character_id, region=REGION, location=location)
        )
    return character_id, sessions, ClassTrialService(sessions, "ocaso")


async def _start_stage(service: ClassTrialService, actor: int, stage: int):
    view = await service.resume(actor)
    if view.kind == "available":
        view = await service.begin(actor, view.state_version)
    if view.context == "refuge":
        view = await service.return_to_circle(actor, view.state_version)
    return await service.start_attempt(actor, view.state_version)


def _stage_condition_events(active):
    """Construct objective engine facts for a persisted Oráculo/Luminar stage."""
    stage = active.current_stage
    hostiles = tuple(
        row["entity_id"]
        for row in active.stage_definition["entities"]
        if row["team"] == "hostile"
    )
    hostile = hostiles[0]
    defeated = {entity_id: Decimal(0) for entity_id in hostiles}
    prefix = f"{active.character_class}-{stage}"

    if active.character_class == "luminar":
        if stage == 1:
            return (
                TrialCombatEvent(
                    f"{prefix}-pressure",
                    "combat_action",
                    hostile,
                    (LUMINAR_ALLY_ENTITY_ID,),
                    "trial.luminar.pressao_aliado",
                    effective_damage=Decimal(1),
                ),
                TrialCombatEvent(
                    f"{prefix}-renewal",
                    "combat_action",
                    "player",
                    (LUMINAR_ALLY_ENTITY_ID,),
                    LUMINAR_ART_IDS["renovacao"],
                    effective_healing=Decimal(1),
                    entity_hp=defeated,
                ),
            )
        if stage == 2:
            application_id = f"{prefix}-judgment-application"
            return (
                TrialCombatEvent(
                    f"{prefix}-judgment",
                    "combat_action",
                    "player",
                    (hostile,),
                    LUMINAR_ART_IDS["julgamento"],
                    effect_applied=True,
                    applied_effect_id="luminar.julgamento.cura",
                    effect_application_event_id=application_id,
                    applied_effect_stat="healing_received",
                    applied_effect_magnitude=Decimal("0.15"),
                    applied_effect_kind="debuff",
                ),
                TrialCombatEvent(
                    f"{prefix}-recovery",
                    "combat_action",
                    hostile,
                    (hostile,),
                    "trial.luminar.recuperacao_treino",
                    target_effect_ids=("luminar.julgamento.cura",),
                    target_effect_application_event_ids=(application_id,),
                    base_healing=Decimal(100),
                    calculated_healing=Decimal(85),
                    effective_healing=Decimal(85),
                    healing_received_multiplier=Decimal("0.85"),
                    entity_hp=defeated,
                ),
            )
        return (
            TrialCombatEvent(
                f"{prefix}-pressure-player",
                "combat_action",
                hostile,
                ("player",),
                "trial.luminar.pressao_jogador",
                effective_damage=Decimal(1),
            ),
            TrialCombatEvent(
                f"{prefix}-pressure-ally",
                "combat_action",
                hostile,
                (LUMINAR_ALLY_ENTITY_ID,),
                "trial.luminar.pressao_aliado_etapa3",
                effective_damage=Decimal(1),
            ),
            TrialCombatEvent(
                f"{prefix}-decision",
                "combat_action",
                "player",
                (hostile,),
                LUMINAR_ART_IDS["fulgor"],
                effective_damage=Decimal(1),
            ),
            TrialCombatEvent(
                f"{prefix}-survive-next-pressure",
                "combat_action",
                hostile,
                ("player",),
                "trial.luminar.pressao_jogador",
                entity_hp=defeated,
                fighter_hp_after={
                    "player": Decimal(1),
                    LUMINAR_ALLY_ENTITY_ID: Decimal(1),
                },
            ),
        )

    if stage == 1:
        application_id = f"{prefix}-sinal-application"
        return (
            TrialCombatEvent(
                f"{prefix}-sinal",
                "combat_action",
                "player",
                (hostile,),
                ORACULO_ART_IDS["sinal_funesto"],
                effect_applied=True,
                applied_effect_id=ORACULO_SINAL_EFFECT_ID,
                effect_application_event_id=application_id,
                applied_effect_stat="attack",
                applied_effect_magnitude=Decimal("0.08"),
                applied_effect_kind="debuff",
                applied_effect_removable=True,
            ),
            TrialCombatEvent(
                f"{prefix}-weakened-attack",
                "combat_action",
                hostile,
                ("player",),
                "trial.oraculo.ataque_sinal",
                calculated_damage=Decimal(1),
                actor_effect_facts=(
                    (ORACULO_SINAL_EFFECT_ID, "attack", Decimal("0.08"), 2, "debuff"),
                ),
                entity_hp=defeated,
            ),
        )
    if stage == 2:
        prepared_id = f"{prefix}-prepared-instance"
        return (
            TrialCombatEvent(
                f"{prefix}-prepare",
                "prepared_action",
                hostile,
                action_id="trial.oraculo.impacto_anunciado",
                prepared_action_instance_id=prepared_id,
            ),
            TrialCombatEvent(
                f"{prefix}-defend",
                "combat_action",
                "player",
                action_id="defend",
                response_to_prepared_action_instance_id=prepared_id,
            ),
            TrialCombatEvent(
                f"{prefix}-resolve",
                "combat_action",
                hostile,
                ("player",),
                "trial.oraculo.impacto_anunciado",
                prepared_resolution=True,
                prepared_action_instance_id=prepared_id,
                entity_hp=defeated,
            ),
        )
    prepared_id = f"{prefix}-prepared-instance"
    return (
        TrialCombatEvent(
            f"{prefix}-ruina",
            "combat_action",
            "player",
            (hostile,),
            ORACULO_ART_IDS["ruina_predita"],
            action_instance_id=f"{prefix}-ruina-action",
            target_state_tags=(ORACULO_OFFENSIVE_WINDOW_TAG,),
        ),
        TrialCombatEvent(
            f"{prefix}-prepare",
            "prepared_action",
            hostile,
            action_id="trial.oraculo.ruptura_predita",
            prepared_action_instance_id=prepared_id,
        ),
        TrialCombatEvent(
            f"{prefix}-defend",
            "combat_action",
            "player",
            action_id="defend",
            response_to_prepared_action_instance_id=prepared_id,
        ),
        TrialCombatEvent(
            f"{prefix}-resolve",
            "combat_action",
            hostile,
            ("player",),
            "trial.oraculo.ruptura_predita",
            prepared_resolution=True,
            prepared_action_instance_id=prepared_id,
            entity_hp=defeated,
        ),
    )


async def _complete_stage(service: ClassTrialService, actor: int, stage: int):
    active = await _start_stage(service, actor, stage)
    assert active is not None and active.kind == "active"
    return await _fight_to_checkpoint(service, actor, active)


def _next_trial_action(view, combat):
    class_name = view.character_class
    stage = view.current_stage
    conditions = set(view.attempt_state["pedagogic_conditions"])
    context = view.attempt_state["pedagogic_context"]
    hostile = next(
        row["entity_id"]
        for row in view.stage_definition["entities"]
        if row["team"] == "hostile"
    )
    if combat.prepared_action is not None:
        return "defend", None

    if class_name == "oraculo":
        sinal = ORACULO_ART_IDS["sinal_funesto"]
        ruina = ORACULO_ART_IDS["ruina_predita"]
        if stage == 1 and not context.get("sinal_application_event_id"):
            return sinal, hostile
        if stage == 3 and (
            ORACULO_OFFENSIVE_WINDOW_TAG
            in combat.fighters["enemy"].training_state_tags
            and ORACULO_CONDITION_IDS[3][0] not in conditions
        ):
            return ruina, hostile
        return "attack", hostile

    if stage == 1 and LUMINAR_CONDITION_IDS[1] not in conditions:
        if context.get("ally_damaged"):
            return LUMINAR_ART_IDS["renovacao"], LUMINAR_ALLY_ENTITY_ID
        return "attack", hostile
    if stage == 2 and not context.get("judgment_application_event_id"):
        return LUMINAR_ART_IDS["julgamento"], hostile
    if stage == 3:
        if not context.get("both_pressured"):
            return "attack", hostile
        if not context.get("priority_decision_event_id"):
            return LUMINAR_ART_IDS["renovacao"], LUMINAR_ALLY_ENTITY_ID
        if LUMINAR_CONDITION_IDS[3][1] not in conditions:
            return "defend", None
        return LUMINAR_ART_IDS["fulgor"], hostile
    return LUMINAR_ART_IDS["fulgor"], hostile


async def _fight_to_checkpoint(
    service, actor: int, active, *, include_diagnostics: bool = False
):
    stage = active.current_stage
    combat_id = active.combat_id
    expected_state = f"ready at checkpoint for stage {stage + 1}"

    def failure_details(final_result, obtained_state):
        return (
            f"Combat.id={combat_id}; stage={stage}; final_result={final_result!r}; "
            f"expected_state={expected_state}; obtained_state={obtained_state!r}"
        )

    async def current_result(view):
        if view.attempt_id is None:
            return None
        current_combat = await service.combat(actor, view.attempt_id)
        return current_combat.result if current_combat is not None else None

    for _ in range(100):
        if active.kind != "active":
            details = failure_details(await current_result(active), active.kind)
            if include_diagnostics:
                pytest.fail(f"Class Trial simulation ended before checkpoint: {details}")
            pytest.fail(f"Class Trial simulation ended before checkpoint: {active.kind}")
        combat = await service.combat(actor, active.attempt_id)
        if combat is None or combat.result is not None:
            result = combat.result if combat is not None else None
            details = failure_details(result, "combat unavailable or already finished")
            if include_diagnostics:
                pytest.fail(f"Class Trial simulation cannot continue: {details}")
            pytest.fail("Class Trial combat is unavailable or already finished")
        action, target = _next_trial_action(active, combat)
        if action not in allowed_actions(combat):
            action, target = "attack", next(
                row["entity_id"]
                for row in active.stage_definition["entities"]
                if row["team"] == "hostile"
            )
        updated = await service.action(
            actor,
            active.attempt_id,
            active.combat_version,
            action,
            target_id=target,
        )
        if updated.kind != "active":
            if updated.current_stage == stage + 1 or updated.kind == "completed":
                return updated
            final_combat = await service.combat(actor, active.attempt_id)
            result = final_combat.result if final_combat is not None else None
            details = failure_details(result, updated.kind)
            if include_diagnostics:
                pytest.fail(f"Class Trial simulation did not checkpoint: {details}")
            pytest.fail(
                f"Class Trial stage {stage} did not checkpoint: obtained {updated.kind}"
            )
        if updated.combat_version == active.combat_version:
            details = failure_details(combat.result, "active combat version did not advance")
            if include_diagnostics:
                pytest.fail(f"Class Trial simulation stopped advancing: {details}")
            pytest.fail("Class Trial combat version did not advance")
        active = updated
    result = await current_result(active)
    details = failure_details(result, active.kind)
    if include_diagnostics:
        pytest.fail(f"Class Trial simulation exceeded its action limit: {details}")
    pytest.fail(f"{active.character_class} Trial stage {stage} did not checkpoint")


@pytest.mark.asyncio
async def test_trial_gate_and_begin_are_persistent_without_creating_a_quest(database):
    low_id, _, low = await _seed_trial(database, 997301, level=9)
    eligible_id, sessions, eligible = await _seed_trial(database, 997302)
    elsewhere_id, _, elsewhere = await _seed_trial(
        database, 997303, location="Charneca da Fuligem"
    )

    assert (await low.resume(997301)).kind == "unavailable"
    assert (await low.resume(997301)).blocker == "level"
    assert (await elsewhere.resume(997303)).blocker == "location"
    offer = await eligible.resume(997302)
    assert offer.kind == "available" and offer.current_stage == 1
    begun = await eligible.begin(997302, offer.state_version)
    repeated = await eligible.begin(997302, offer.state_version)
    assert begun.kind == "ready" and begun.context == "circle"
    assert repeated.state_version == begun.state_version
    async with sessions() as session:
        assert await session.scalar(
            select(ClassTrialState.character_id).where(
                ClassTrialState.character_id == eligible_id
            )
        ) == eligible_id
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == eligible_id)
        ) is None
        assert await session.scalar(
            select(ClassTrialState.character_id).where(
                ClassTrialState.character_id == low_id
            )
        ) is None
        assert await session.scalar(
            select(ClassTrialState.character_id).where(
                ClassTrialState.character_id == elsewhere_id
            )
        ) is None


@pytest.mark.asyncio
async def test_stage_checkpoint_is_idempotent_and_reconnects_between_stages(
    database, monkeypatch
):
    actor = 997304
    generated_uuids = []
    next_uuid = count(1)

    def deterministic_uuid4():
        value = UUID(int=next(next_uuid))
        generated_uuids.append(value)
        return value

    # create_luminar_trial_combat makes a template id, then reset_trial_combat
    # assigns the live Combat.id. Keep these UUIDs unique and reproducible.
    _, _, service = await _seed_trial(
        database,
        actor,
        active_art_ids=(LUMINAR_ART_IDS["renovacao"], LUMINAR_ART_IDS["fulgor"]),
    )
    with monkeypatch.context() as deterministic_ids:
        deterministic_ids.setattr(
            class_trials_domain, "uuid4", deterministic_uuid4
        )
        active = await _start_stage(service, actor, 1)
    assert active.attempt_id is not None
    assert active.combat_id == UUID(int=2), (
        "Unexpected Luminar seed: Combat.id="
        f"{active.combat_id}; stage={active.current_stage}; final_result=None; "
        "expected_state=active stage 1 using UUID(int=2); "
        f"obtained_state={active.kind}; generated_uuids={generated_uuids}"
    )
    assert generated_uuids == [UUID(int=1), UUID(int=2)], (
        f"Unexpected deterministic UUID sequence for Combat.id={active.combat_id}; "
        f"stage={active.current_stage}; generated_uuids={generated_uuids}"
    )
    duplicate_start = await service.start_attempt(actor, active.state_version - 1)
    assert duplicate_start.attempt_id == active.attempt_id

    hostile = next(
        row["entity_id"]
        for row in active.stage_definition["entities"]
        if row["team"] == "hostile"
    )
    first = await service.action(
        actor,
        active.attempt_id,
        active.combat_version,
        "attack",
        target_id=hostile,
    )
    duplicate = await service.action(
        actor,
        active.attempt_id,
        active.combat_version,
        "attack",
        target_id=hostile,
    )
    duplicate_context = (
        f"Combat.id={active.combat_id}; stage=1; final_result=None; "
        "expected_state=duplicate action is idempotent; "
        f"obtained_state=version {duplicate.combat_version}, "
        f"first version {first.combat_version}"
    )
    assert duplicate.combat_version == first.combat_version, duplicate_context
    assert duplicate.attempt_state["events"] == first.attempt_state["events"], (
        duplicate_context
    )
    checkpoint = await _fight_to_checkpoint(
        service, actor, first, include_diagnostics=True
    )
    stale = await service.complete_stage(
        actor, active.attempt_id, active.state_version
    )
    resumed = await service.resume(actor)
    final_combat = await service.combat(actor, active.attempt_id)
    final_result = final_combat.result if final_combat is not None else None
    checkpoint_context = (
        f"Combat.id={active.combat_id}; stage=1; final_result={final_result!r}; "
        "expected_state=ready at stage 2 with completed_stages=(1,); "
        f"obtained_state=kind {checkpoint.kind}, stage {checkpoint.current_stage}, "
        f"completed_stages={checkpoint.completed_stages}"
    )
    assert checkpoint.kind == "ready", checkpoint_context
    assert (
        checkpoint.current_stage == 2 and checkpoint.completed_stages == (1,)
    ), checkpoint_context
    assert stale.current_stage == 2 and stale.completed_stages == (1,), checkpoint_context
    assert resumed.current_stage == 2 and resumed.completed_stages == (1,), checkpoint_context
    assert resumed.attempt_id is None and resumed.attempt_state is None


@pytest.mark.asyncio
async def test_defeat_clears_attempt_conditions_and_retry_reuses_stage_plan(database):
    actor = 997305
    character_id, sessions, service = await _seed_trial(
        database, actor, active_art_ids=(LUMINAR_ART_IDS["renovacao"],)
    )
    active = await _start_stage(service, actor, 1)
    hostile = next(
        row["entity_id"]
        for row in active.stage_definition["entities"]
        if row["team"] == "hostile"
    )
    pressured = await service.action(
        actor,
        active.attempt_id,
        active.combat_version,
        "attack",
        target_id=hostile,
    )
    observed = await service.action(
        actor,
        active.attempt_id,
        pressured.combat_version,
        LUMINAR_ART_IDS["renovacao"],
        target_id=LUMINAR_ALLY_ENTITY_ID,
    )
    assert observed.attempt_state["pedagogic_conditions"] == [
        LUMINAR_CONDITION_IDS[1]
    ]
    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None
    combat.fighters[LUMINAR_ALLY_ENTITY_ID].hp = Decimal(1)
    async with sessions.begin() as session:
        record = await session.get(CombatRecord, combat.id)
        record.snapshot = encode(combat)
    defeated = await service.action(
        actor,
        active.attempt_id,
        observed.combat_version,
        "attack",
        target_id=hostile,
    )
    assert defeated.kind == "ready" and defeated.current_stage == 1
    assert defeated.completed_stages == () and defeated.attempt_state is None
    assert defeated.stage_definition == active.stage_definition
    assert defeated.attempt_id is None and defeated.context == "circle"

    left = await service.leave_to_refuge(actor, defeated.state_version)
    assert left.kind == "between_attempts" and left.context == "refuge"
    returned = await service.return_to_circle(actor, left.state_version)
    assert returned.current_stage == 1 and returned.stage_definition == active.stage_definition
    retried = await service.start_attempt(actor, returned.state_version)
    assert retried.attempt_id != active.attempt_id
    assert retried.stage_definition == active.stage_definition
    assert retried.attempt_state["pedagogic_conditions"] == []
    hostile = next(
        row for row in active.stage_definition["entities"] if row["team"] == "hostile"
    )
    assert retried.attempt_state["entities"][hostile["entity_id"]]["hp"] == hostile[
        "max_hp"
    ]
    async with sessions() as session:
        previous = await session.scalar(
            select(GameActivity).where(GameActivity.id == active.attempt_id)
        )
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert previous.status == "failed"
        assert character.vigor == 37
        assert world.location == REFUGE


@pytest.mark.asyncio
async def test_attempt_resets_trial_state_and_locks_configuration_without_vigor_or_items(database):
    actor = 997306
    character_id, sessions, service = await _seed_trial(database, actor)
    active = await _start_stage(service, actor, 1)
    persisted_combat = await service.combat(actor, active.attempt_id)
    assert active.encounter_id is not None and active.combat_id is not None
    assert persisted_combat is not None
    assert persisted_combat.fighters["player"].hp == persisted_combat.fighters["player"].stats.hp
    assert persisted_combat.fighters["player"].effects == []
    assert persisted_combat.fighters["player"].barrier == 0
    assert persisted_combat.fighters["player"].cooldowns == {}
    assert set(persisted_combat.player_actions) == {"attack"}
    assert persisted_combat.consumable_uses == 0
    assert not persisted_combat.external_consumables_allowed
    assert persisted_combat.variant is None
    assert active.consumable_options == ()
    assert active.attempt_state["player"]["effects"] == []
    assert active.attempt_state["player"]["barrier"] == "0"
    assert active.attempt_state["player"]["cooldowns"] == {}
    resources = active.attempt_state["player"]["resources"]
    assert resources["ward_charges"] == 0 and resources["ward_remaining"] == 0
    assert resources["next_direct_crit"]["bonus"] == "0"
    assert resources["retaliation"]["charges"] == 0
    assert resources["retaliation"]["remaining_T"] == 0
    assert active.attempt_state["player"]["action_chains"] == {}
    assert active.attempt_state["external_consumables_used"] == 0
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.hp == character.max_hp
        assert character.vigor == 37
        assert await session.scalar(
            select(func.count()).select_from(ConsumableStack).where(
                ConsumableStack.character_id == character_id
            )
        ) == 0
        with pytest.raises(CombatConfigurationLocked):
            async with sessions.begin() as locked_session:
                await lock_for_combat_configuration_mutation(locked_session, character_id)
        for model in (RewardEvent, BestiaryEntry, CodexEntry, MaterialStack):
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
async def test_reconnect_during_attempt_restores_identity_and_conditions(database):
    actor = 997307
    _, sessions, service = await _seed_trial(
        database,
        actor,
        active_art_ids=(LUMINAR_ART_IDS["egide_solar"], LUMINAR_ART_IDS["fulgor"]),
    )
    active = await _start_stage(service, actor, 1)
    duplicate_start = await service.start_attempt(actor, active.state_version)
    assert duplicate_start.encounter_id == active.encounter_id
    assert duplicate_start.combat_id == active.combat_id
    assert await service.combat(actor, active.attempt_id) is not None
    async with sessions() as session:
        assert await session.scalar(
            select(func.count()).select_from(Encounter).join(GameActivity).where(
                GameActivity.character_id == active.character_id
            )
        ) == 1
    changed = await service.action(
        actor,
        active.attempt_id,
        active.combat_version,
        LUMINAR_ART_IDS["egide_solar"],
        target_id=LUMINAR_ALLY_ENTITY_ID,
    )
    resumed = await service.resume(actor)
    assert resumed.kind == "active"
    assert resumed.attempt_id == active.attempt_id
    assert resumed.current_stage == 1
    assert resumed.encounter_id == active.encounter_id
    assert resumed.combat_id == active.combat_id
    assert resumed.stage_definition["entities"] == active.stage_definition["entities"]
    persisted_combat = await service.combat(actor, active.attempt_id)
    assert persisted_combat.id == active.combat_id
    assert set(persisted_combat.fighters) - {"player"} == {
        row["entity_id"] for row in active.stage_definition["entities"]
    }
    assert resumed.attempt_state["pedagogic_conditions"] == [
        LUMINAR_CONDITION_IDS[1]
    ]
    assert resumed.attempt_state["pedagogic_context"]["ally_trial_barrier_source"] == (
        f"player:{LUMINAR_ART_IDS['egide_solar']}"
    )
    assert Decimal(resumed.attempt_state["entities"][LUMINAR_ALLY_ENTITY_ID]["barrier"]) > 0
    assert resumed.attempt_state["entities"][LUMINAR_ALLY_ENTITY_ID]["barrier_remaining"] > 0
    assert any(
        row["action_id"] == LUMINAR_ART_IDS["egide_solar"]
        for row in resumed.attempt_state["events"]
    )
    assert resumed.state_version == changed.state_version


@pytest.mark.asyncio
async def test_oraculo_vislumbre_answers_same_prepared_threat_after_reconnect(database):
    actor = 997362
    art_ids = (
        ORACULO_ART_IDS["sinal_funesto"],
        ORACULO_ART_IDS["vislumbre"],
        ORACULO_ART_IDS["ruina_predita"],
    )
    _, _, service = await _seed_trial(
        database,
        actor,
        character_class="oraculo",
        active_art_ids=art_ids,
    )
    await service.begin(actor)
    checkpoint = await _complete_stage(service, actor, 1)
    assert checkpoint.current_stage == 2 and checkpoint.completed_stages == (1,)
    active = await _start_stage(service, actor, 2)
    hostile_id = active.stage_definition["entities"][0]["entity_id"]

    for _ in range(3):
        combat = await service.combat(actor, active.attempt_id)
        assert combat is not None
        if combat.prepared_action is not None:
            break
        active = await service.action(
            actor,
            active.attempt_id,
            active.combat_version,
            "attack",
            target_id=hostile_id,
        )
    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None
    prepared_instance = combat.prepared_action_instance_id
    assert combat.prepared_action == "trial.oraculo.impacto_anunciado"
    assert prepared_instance

    resumed = await service.resume(actor)
    restored = await service.combat(actor, active.attempt_id)
    assert resumed.attempt_id == active.attempt_id
    assert resumed.encounter_id == active.encounter_id
    assert restored is not None
    assert restored.prepared_action_instance_id == prepared_instance

    answered = await service.action(
        actor,
        active.attempt_id,
        resumed.combat_version,
        ORACULO_ART_IDS["vislumbre"],
        target_id="player",
    )
    assert answered.kind == "active" and answered.current_stage == 2
    assert ORACULO_CONDITION_IDS[2] in answered.attempt_state["pedagogic_conditions"]
    completed = await _fight_to_checkpoint(service, actor, answered)
    assert completed.kind == "ready" and completed.current_stage == 3
    assert completed.completed_stages == (1, 2)
    persisted = await service.combat(actor, active.attempt_id)
    assert persisted is not None
    response_event = next(
        event
        for event in persisted.events
        if event.action == ORACULO_ART_IDS["vislumbre"]
    )
    assert response_event.response_to_prepared_action_instance_id == prepared_instance
    assert response_event.effect_id == "oraculo.vislumbre.agility"
    assert response_event.target == "player"


@pytest.mark.asyncio
async def test_required_ally_falling_to_zero_fails_attempt_and_discards_conditions(database):
    actor = 997308
    _, _, service = await _seed_trial(database, actor)
    active = await _start_stage(service, actor, 1)
    hostile = next(
        row["entity_id"]
        for row in active.stage_definition["entities"]
        if row["team"] == "hostile"
    )
    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None
    combat.fighters[LUMINAR_ALLY_ENTITY_ID].hp = Decimal(1)
    async with service.sessions.begin() as session:
        record = await session.get(CombatRecord, combat.id)
        record.snapshot = encode(combat)
    failed = await service.action(
        actor,
        active.attempt_id,
        active.combat_version,
        "attack",
        target_id=hostile,
    )
    assert failed.kind == "ready" and failed.status == "ready"
    assert failed.current_stage == 1 and failed.attempt_state is None
    assert failed.attempt_id is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("character_class", "expected_paths", "art_ids", "actor"),
    [
        (
            "luminar",
            ("guardiao", "inquisidor"),
            (
                LUMINAR_ART_IDS["fulgor"],
                LUMINAR_ART_IDS["renovacao"],
                LUMINAR_ART_IDS["julgamento"],
            ),
            997309,
        ),
        (
            "oraculo",
            ("agoureiro", "invocador"),
            (
                ORACULO_ART_IDS["sinal_funesto"],
                ORACULO_ART_IDS["vislumbre"],
                ORACULO_ART_IDS["ruina_predita"],
            ),
            997352,
        ),
    ],
)
async def test_final_checkpoint_unlocks_both_paths_once_without_selection_or_reward(
    database, character_class, expected_paths, art_ids, actor
):
    character_id, sessions, service = await _seed_trial(
        database,
        actor,
        character_class=character_class,
        active_art_ids=art_ids,
    )
    await service.begin(actor)
    first = await _complete_stage(service, actor, 1)
    second = await _complete_stage(service, actor, 2)
    final = await _complete_stage(service, actor, 3)
    async with sessions() as session:
        final_activity = await session.scalar(
            select(GameActivity)
            .where(GameActivity.character_id == character_id)
            .order_by(GameActivity.last_valid_action_at.desc(), GameActivity.id.desc())
            .limit(1)
        )
    duplicate = await service.complete_stage(
        actor, final_activity.id, final.state_version
    )
    resumed = await service.resume(actor)

    assert first.current_stage == 2 and first.completed_stages == (1,)
    assert second.current_stage == 3 and second.completed_stages == (1, 2)
    assert final.kind == "completed" and final.completed_stages == (1, 2, 3)
    assert duplicate.kind == "completed" and resumed.kind == "completed"
    assert final.available_paths == expected_paths
    assert final.selected_path is None and not final.path_art_unlocked
    assert final.path_art_min_level == 12
    async with sessions() as session:
        assert await session.scalar(
            select(func.count()).select_from(Unlock).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == TRIAL_COMPLETED_UNLOCK,
            )
        ) == 1
        character = await session.get(Character, character_id)
        assert character.xp == 0 and character.crowns == 23 and character.vigor == 37
        for model in (RewardEvent, BestiaryEntry, CodexEntry, MaterialStack):
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
@pytest.mark.parametrize(
    ("character_class", "art_ids", "trial_art"),
    [
        (
            "oraculo",
            (
                ORACULO_ART_IDS["sinal_funesto"],
                ORACULO_ART_IDS["vislumbre"],
                ORACULO_ART_IDS["ruina_predita"],
            ),
            ORACULO_ART_IDS["sinal_funesto"],
        ),
        (
            "luminar",
            (
                LUMINAR_ART_IDS["fulgor"],
                LUMINAR_ART_IDS["renovacao"],
                LUMINAR_ART_IDS["egide_solar"],
            ),
            LUMINAR_ART_IDS["fulgor"],
        ),
    ],
)
async def test_oraculo_and_luminar_attempts_use_equipped_arts_and_preserve_costs(
    database, character_class, art_ids, trial_art
):
    actor = 997360 if character_class == "oraculo" else 997361
    character_id, sessions, service = await _seed_trial(
        database,
        actor,
        character_class=character_class,
        active_art_ids=art_ids,
    )
    offer = await service.resume(actor)
    begun = await service.begin(actor, offer.state_version)
    active = await service.start_attempt(actor, begun.state_version)
    assert active.kind == "active" and active.attempt_id is not None
    assert active.attempt_state["equipped_art_ids"] == list(art_ids)
    assert active.consumable_options == ()

    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None
    assert combat.external_consumables_allowed is False
    assert combat.variant is None
    assert combat.consumable_uses == 0
    assert set(combat.player_actions) == {"attack", *art_ids}
    target_id = active.stage_definition["entities"][0]["entity_id"]

    changed = await service.action(
        actor,
        active.attempt_id,
        active.combat_version,
        trial_art,
        target_id=target_id,
    )
    assert changed.kind == "active" and changed.attempt_id == active.attempt_id
    resumed = await service.resume(actor)
    assert resumed.attempt_id == active.attempt_id
    assert resumed.encounter_id == active.encounter_id
    assert resumed.combat_id == active.combat_id
    assert resumed.attempt_state["events"]

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.xp == 0 and character.crowns == 23 and character.vigor == 37
        for model in (RewardEvent, BestiaryEntry, CodexEntry, MaterialStack):
            assert await session.scalar(
                select(func.count()).select_from(model).where(
                    model.character_id == character_id
                )
            ) == 0
        assert await session.scalar(
            select(func.count()).select_from(ConsumableStack).where(
                ConsumableStack.character_id == character_id
            )
        ) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("character_class", "art_ids", "first_action"),
    [
        (
            "vigia",
            (
                VIGIA_ART_IDS["disparo_preciso"],
                VIGIA_ART_IDS["marca_da_presa"],
                VIGIA_ART_IDS["saraivada"],
            ),
            VIGIA_ART_IDS["marca_da_presa"],
        ),
        (
            "tecelao",
            (
                TECELAO_ART_IDS["chama_tecida"],
                TECELAO_ART_IDS["fio_cortante"],
                TECELAO_ART_IDS["veu_entrelacado"],
            ),
            TECELAO_ART_IDS["chama_tecida"],
        ),
    ],
)
async def test_vigia_and_tecelao_attempts_use_persisted_arts_and_reconnect(
    database, character_class, art_ids, first_action
):
    actor = 997350 if character_class == "vigia" else 997351
    character_id, sessions, service = await _seed_trial(
        database,
        actor,
        character_class=character_class,
        active_art_ids=art_ids,
    )
    offer = await service.resume(actor)
    begun = await service.begin(actor, offer.state_version)
    active = await service.start_attempt(actor, begun.state_version)
    assert active.kind == "active" and active.attempt_id is not None
    assert active.attempt_state["equipped_art_ids"] == list(art_ids)
    assert active.consumable_options == ()

    combat = await service.combat(actor, active.attempt_id)
    assert combat is not None
    assert combat.external_consumables_allowed is False
    assert combat.consumable_uses == 0
    assert combat.variant is None
    assert set(combat.player_actions) == {"attack", *art_ids}
    assert len(combat.fighters) >= 2

    changed = await service.action(
        actor,
        active.attempt_id,
        active.combat_version,
        first_action,
        target_id=active.stage_definition["entities"][0]["entity_id"],
    )
    assert changed.kind == "active"
    assert changed.attempt_id == active.attempt_id
    if character_class == "vigia":
        assert changed.attempt_state["pedagogic_context"]["mark_application_event_id"]
        assert changed.attempt_state["pedagogic_conditions"] == []
    else:
        burn_event = next(
            row
            for row in changed.attempt_state["events"]
            if row["action_id"] == TECELAO_ART_IDS["chama_tecida"]
        )
        assert burn_event["dot_kind"] == "burn"
        assert burn_event["dot_application_event_id"]
        assert changed.attempt_state["pedagogic_conditions"] == [
            "tecelao.stage_1.burn_applied"
        ]
    resumed = await service.resume(actor)
    restored = await service.combat(actor, active.attempt_id)
    latest_version = changed.combat_version
    assert resumed.kind == "active"
    assert resumed.attempt_id == active.attempt_id
    assert resumed.encounter_id == active.encounter_id
    assert resumed.combat_id == active.combat_id
    assert restored is not None and restored.id == active.combat_id
    assert restored.version == changed.combat_version
    assert restored.fighters["player"].last_action == first_action
    assert restored.consumable_uses == 0
    if character_class == "tecelao":
        assert restored.fighters["player"].action_chains["trama_encadeada"][
            "prepared_by_action_id"
        ] == first_action
        assert restored.fighters["player"].action_chains["trama_encadeada"][
            "remaining"
        ] == 2
        consumed = await service.action(
            actor,
            active.attempt_id,
            changed.combat_version,
            TECELAO_ART_IDS["fio_cortante"],
            target_id=active.stage_definition["entities"][0]["entity_id"],
        )
        assert consumed.attempt_state["pedagogic_conditions"] == [
            "tecelao.stage_1.burn_applied",
        ]
        chain_record = next(
            row
            for row in reversed(consumed.attempt_state["events"])
            if row["action_id"] == TECELAO_ART_IDS["fio_cortante"]
        )
        assert chain_record["chain_empowered"] is True
        assert chain_record["power_multiplier"] == "1.10"
        assert chain_record["chain_prepared_by_action_instance_id"]
        assert chain_record["chain_consumed_by_action_instance_id"]
        latest_version = consumed.combat_version

    rejected_consumable = await service.action(
        actor,
        active.attempt_id,
        latest_version,
        "consumable:external",
    )
    assert rejected_consumable.combat_version == latest_version

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.vigor == 37
        assert await session.scalar(
            select(func.count()).select_from(Encounter).join(GameActivity).where(
                GameActivity.character_id == character_id
            )
        ) == 1
        for model in (RewardEvent, BestiaryEntry, CodexEntry, MaterialStack):
            assert await session.scalar(
                select(func.count()).select_from(model).where(
                    model.character_id == character_id
                )
            ) == 0


def test_trial_entities_require_stable_id_no_variant_and_passive_roles():
    assert set(TRIAL_IDS_BY_CLASS) == {
        "sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar"
    }
    assert all(len(paths) == 2 for paths in CLASS_PATHS.values())
    with pytest.raises(ValueError):
        TrialEntityDefinition(
            "training.echo",
            "hostile",
            "active",
            Decimal("1"),
            {},
        )
    with pytest.raises(ValueError):
        TrialEntityDefinition(
            "trial_entity.test.variant",
            "hostile",
            "active",
            Decimal("1"),
            {},
            variant="resistant",
        )
    with pytest.raises(ValueError):
        TrialEntityDefinition(
            "trial_entity.test.passive",
            "hostile",
            "passive",
            Decimal("1"),
            {},
            ("offense",),
        )

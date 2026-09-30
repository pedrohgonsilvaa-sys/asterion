from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.class_trials import ClassTrialService
from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.domain.arts import TECELAO_ART_IDS, VIGIA_ART_IDS
from asterion.domain.class_trials import (
    CLASS_PATHS,
    TRIAL_COMPLETED_UNLOCK,
    TRIAL_IDS_BY_CLASS,
    TrialCombatEvent,
    TrialEntityDefinition,
    TrialStageDefinition,
)
from asterion.domain.combat import Action, Combat, Effect, Fighter
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, resolve_combat_stats
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    Character,
    CharacterActiveArtSlot,
    ClassTrialState,
    CodexEntry,
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


def _plan(stage: int, *, conditions=("demonstration.complete",)) -> TrialStageDefinition:
    """Synthetic templates keep the integration tests independent of class balance."""
    return TrialStageDefinition(
        stage=stage,
        entities=(
            TrialEntityDefinition(
                "trial_entity.test.primary",
                "hostile",
                "active",
                Decimal("100"),
                {"attack": Decimal("1"), "defense": Decimal("1")},
                ("training.attack",),
            ),
            TrialEntityDefinition(
                "trial_entity.test.manifestation",
                "hostile",
                "passive",
                Decimal("50"),
                {"defense": Decimal("1")},
            ),
            TrialEntityDefinition(
                "trial_entity.test.ally",
                "ally",
                "passive",
                Decimal("30"),
                {"defense": Decimal("1")},
                required_to_survive=True,
            ),
        ),
        required_conditions=tuple(conditions),
        allowed_art_ids=("class_art.test_equipped",),
    )


def _combat(plan: TrialStageDefinition) -> Combat:
    stats = resolve_combat_stats("luminar", 10, "remanescente")
    fighters = {
        "player": Fighter(
            "player",
            "Hero",
            10,
            stats,
            Decimal("1"),
            race="remanescente",
            character_class="luminar",
            opportunity=4,
            defending=True,
            last_action="old-action",
            cooldowns={"old-action": 12},
            effects=[Effect("old", "attack", Decimal("0.1"), 2, 0)],
            barrier=Decimal("15"),
            barrier_remaining=2,
            barrier_source="old-source",
            ward_remaining=2,
            ward_charges=1,
        )
    }
    for entity in plan.entities:
        fighters[entity.entity_id] = Fighter(
            entity.entity_id,
            entity.entity_id,
            10,
            stats,
            Decimal("1"),
            opportunity=3,
            last_action="old-action",
            cooldowns={"old-action": 9},
            effects=[Effect("old", "defense", Decimal("0.1"), 1, 0)],
            barrier=Decimal("7"),
            barrier_remaining=1,
        )
    return Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        fighters,
        {
            "attack": Action("attack", "Attack", Decimal("1")),
            "class_art.test_equipped": Action(
                "class_art.test_equipped", "Equipped Art", Decimal("1")
            ),
            "unlisted_art": Action("unlisted_art", "Not Equipped", Decimal("1")),
        },
        {"training.attack": Action("training.attack", "Training", Decimal("1"))},
        ("training.attack",),
        rng_cursor=7,
        consumable_uses=2,
        variant=None,
    )


async def _start_stage(service: ClassTrialService, actor: int, stage: int):
    view = await service.resume(actor)
    if view.kind == "available":
        view = await service.begin(actor, view.state_version)
    if view.context == "refuge":
        view = await service.return_to_circle(actor, view.state_version)
    return await service.start_attempt(actor, view.state_version, _plan(stage))


async def _complete_stage(service: ClassTrialService, actor: int, stage: int):
    active = await _start_stage(service, actor, stage)
    assert active is not None and active.kind == "active"
    condition = active.stage_definition["required_conditions"][0]
    event = TrialCombatEvent(
        event_id=f"stage-{stage}-victory",
        event_type="targets_defeated",
        actor_id="player",
        target_ids=(
            "trial_entity.test.primary",
            "trial_entity.test.manifestation",
        ),
        satisfied_conditions=(condition,),
        entity_hp={
            "trial_entity.test.primary": Decimal(0),
            "trial_entity.test.manifestation": Decimal(0),
        },
    )
    progressed = await service.record_combat_event(
        actor, active.attempt_id, active.state_version, event
    )
    return await service.complete_stage(actor, active.attempt_id, progressed.state_version)


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
async def test_stage_checkpoint_is_idempotent_and_reconnects_between_stages(database):
    actor = 997304
    _, sessions, service = await _seed_trial(database, actor)
    active = await _start_stage(service, actor, 1)
    assert active.attempt_id is not None
    duplicate_start = await service.start_attempt(
        actor, active.state_version - 1, _plan(1)
    )
    assert duplicate_start.attempt_id == active.attempt_id

    event = TrialCombatEvent(
        event_id="target-one-down",
        event_type="direct_damage",
        actor_id="player",
        target_ids=("trial_entity.test.primary",),
        satisfied_conditions=("demonstration.complete",),
        entity_hp={"trial_entity.test.primary": Decimal(0)},
    )
    first = await service.record_combat_event(
        actor, active.attempt_id, active.state_version, event
    )
    duplicate = await service.record_combat_event(
        actor, active.attempt_id, active.state_version, event
    )
    assert duplicate.state_version == first.state_version
    assert duplicate.attempt_state["processed_event_ids"] == ["target-one-down"]
    incomplete = await service.complete_stage(actor, active.attempt_id, first.state_version)
    assert incomplete.kind == "active" and incomplete.current_stage == 1

    final_target = TrialCombatEvent(
        event_id="passive-target-down",
        event_type="area_damage",
        actor_id="player",
        target_ids=("trial_entity.test.manifestation",),
        entity_hp={"trial_entity.test.manifestation": Decimal(0)},
    )
    second = await service.record_combat_event(
        actor, active.attempt_id, incomplete.state_version, final_target
    )
    checkpoint = await service.complete_stage(actor, active.attempt_id, second.state_version)
    stale = await service.complete_stage(actor, active.attempt_id, second.state_version)
    resumed = await service.resume(actor)
    assert checkpoint.kind == "ready"
    assert checkpoint.current_stage == 2 and checkpoint.completed_stages == (1,)
    assert stale.current_stage == 2 and stale.completed_stages == (1,)
    assert resumed.current_stage == 2 and resumed.completed_stages == (1,)
    assert resumed.attempt_id is None and resumed.attempt_state is None


@pytest.mark.asyncio
async def test_defeat_clears_attempt_conditions_and_retry_reuses_stage_plan(database):
    actor = 997305
    character_id, sessions, service = await _seed_trial(database, actor)
    active = await _start_stage(service, actor, 1)
    condition_event = TrialCombatEvent(
        event_id="pedagogy-event",
        event_type="valid_response",
        actor_id="player",
        satisfied_conditions=("demonstration.complete",),
    )
    observed = await service.record_combat_event(
        actor, active.attempt_id, active.state_version, condition_event
    )
    defeated = await service.fail_attempt(actor, active.attempt_id, observed.state_version)
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
    assert retried.attempt_state["entities"]["trial_entity.test.primary"]["hp"] == "100"
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
    attached = await service.attach_combat(
        actor, active.attempt_id, active.state_version, _combat(_plan(1))
    )
    persisted_combat = await service.combat(actor, active.attempt_id)
    assert attached.encounter_id is not None and attached.combat_id is not None
    assert persisted_combat.fighters["player"].hp == persisted_combat.fighters["player"].stats.hp
    assert persisted_combat.fighters["player"].effects == []
    assert persisted_combat.fighters["player"].barrier == 0
    assert persisted_combat.fighters["player"].cooldowns == {}
    assert persisted_combat.fighters["player"].ward_charges == 0
    assert all(
        fighter.opportunity == 0
        and fighter.effects == []
        and fighter.barrier == 0
        and fighter.cooldowns == {}
        for key, fighter in persisted_combat.fighters.items()
        if key != "player"
    )
    assert "unlisted_art" not in persisted_combat.player_actions
    assert persisted_combat.rng_cursor == 0 and persisted_combat.consumable_uses == 0
    assert persisted_combat.variant is None
    assert active.consumable_options == ()
    assert active.attempt_state["player"] == {
        "hp": str(active.attempt_state["player"]["hp"]),
        "effects": [],
        "barrier": "0",
        "barrier_remaining": 0,
        "cooldowns": {},
        "resources": {},
    }
    assert active.attempt_state["external_consumables_used"] == 0
    assert active.attempt_state["events"] == []
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
    _, sessions, service = await _seed_trial(database, actor)
    active = await _start_stage(service, actor, 1)
    attached = await service.attach_combat(
        actor, active.attempt_id, active.state_version, _combat(_plan(1))
    )
    duplicate_attach = await service.attach_combat(
        actor, active.attempt_id, active.state_version, _combat(_plan(1))
    )
    assert duplicate_attach.encounter_id == attached.encounter_id
    assert duplicate_attach.combat_id == attached.combat_id
    assert await service.combat(actor, active.attempt_id) is not None
    active = attached
    async with sessions() as session:
        assert await session.scalar(
            select(func.count()).select_from(Encounter).join(GameActivity).where(
                GameActivity.character_id == active.character_id
            )
        ) == 1
    event = TrialCombatEvent(
        event_id="condition-a",
        event_type="prepared_response",
        actor_id="player",
        target_ids=("trial_entity.test.primary",),
        satisfied_conditions=("demonstration.complete",),
        entity_barriers={"trial_entity.test.ally": (Decimal("12"), 2)},
        data={"measurement": Decimal("1.25")},
    )
    changed = await service.record_combat_event(
        actor, active.attempt_id, active.state_version, event
    )
    resumed = await service.resume(actor)
    assert resumed.kind == "active"
    assert resumed.attempt_id == active.attempt_id
    assert resumed.current_stage == 1
    assert resumed.encounter_id == attached.encounter_id
    assert resumed.combat_id == attached.combat_id
    assert resumed.stage_definition["entities"] == active.stage_definition["entities"]
    persisted_combat = await service.combat(actor, active.attempt_id)
    assert persisted_combat.id == attached.combat_id
    assert set(persisted_combat.fighters) - {"player"} == {
        row["entity_id"] for row in active.stage_definition["entities"]
    }
    assert resumed.attempt_state["pedagogic_conditions"] == ["demonstration.complete"]
    assert resumed.attempt_state["entities"]["trial_entity.test.ally"]["barrier"] == "12"
    assert resumed.attempt_state["entities"]["trial_entity.test.ally"]["barrier_remaining"] == 2
    assert resumed.attempt_state["events"][0]["data"]["measurement"] == "1.25"
    assert resumed.state_version == changed.state_version


@pytest.mark.asyncio
async def test_required_ally_falling_to_zero_fails_attempt_and_discards_conditions(database):
    actor = 997308
    _, _, service = await _seed_trial(database, actor)
    active = await _start_stage(service, actor, 1)
    event = TrialCombatEvent(
        event_id="ally-defeated",
        event_type="damage_taken",
        actor_id="trial_entity.test.primary",
        target_ids=("trial_entity.test.ally",),
        satisfied_conditions=("demonstration.complete",),
        entity_hp={"trial_entity.test.ally": Decimal(0)},
    )
    failed = await service.record_combat_event(
        actor, active.attempt_id, active.state_version, event
    )
    assert failed.kind == "ready" and failed.status == "ready"
    assert failed.current_stage == 1 and failed.attempt_state is None
    assert failed.attempt_id is None


@pytest.mark.asyncio
async def test_final_checkpoint_unlocks_both_paths_once_without_selection_or_reward(database):
    actor = 997309
    character_id, sessions, service = await _seed_trial(database, actor)
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
    assert final.available_paths == ("guardiao", "inquisidor")
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

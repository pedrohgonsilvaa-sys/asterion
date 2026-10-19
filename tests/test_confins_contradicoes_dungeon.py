from copy import deepcopy
from decimal import ROUND_FLOOR, Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.bestiary import (
    CONFINS_CONTRADICOES_BOSS_MASTERY,
    _reward_source_id,
)
from asterion.application.crafting import CraftingService
from asterion.application.dungeons import (
    CONFINS_CONTRADICOES_FAMILY_ID,
    DUNGEON_FAMILIES,
    DungeonService,
    _enemy_rewards_for,
)
from asterion.domain.combat import (
    CombatEvent,
    _damage_aura_reduction,
    _resolve_phase_triggers,
    act,
    action_target_ids,
    active_player_key,
)
from asterion.domain.confins_contradictions_dungeon import (
    CONFINS_CONTRADICOES_BASIC_MATERIAL_WEIGHTS,
    CONFINS_CONTRADICOES_BOSS,
    CONFINS_CONTRADICOES_BOSS_CODEX_ENTRY,
    CONFINS_CONTRADICOES_CODEX_ENTRY,
    CONFINS_CONTRADICOES_CORE_ID,
    CONFINS_CONTRADICOES_DISCOVERY_UNLOCK,
    CONFINS_CONTRADICOES_FIRST_CLEAR_PREFIX,
    CONFINS_CONTRADICOES_PHASE_II,
    CONFINS_CONTRADICOES_PHASE_III,
    CONFINS_CONTRADICOES_PLATE_IDS,
    CONFINS_CONTRADICOES_PLATE_KEYS,
    CONFINS_CONTRADICOES_RECIPE_UNLOCK,
    CONFINS_CONTRADICOES_RECORD_CODEX_ENTRY,
    CONFINS_CONTRADICOES_REWARD_PREFIX,
    confins_contradicoes_encounter_specs,
    confins_contradicoes_enemy_rewards,
    create_confins_contradicoes_combat,
)
from asterion.domain.dungeons import (
    DIFFICULTIES,
    catalyst_material_id,
    fragment_material_id,
)
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.professions import canonical_recipe, recipe_crown_cost
from asterion.domain.road import (
    CONFINS_CONTRADICOES_CUSTODIO,
    CONFINS_CONTRADICOES_PRECEPTOR,
    CONFINS_NO_CENTRAL,
    CONFINS_VIGIA_DESFASADO,
    creature_for,
    road_enemy_stats,
)
from asterion.domain.weapon_metadata import weapon_definition, weapon_type_id_for_recipe
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CodexEntry,
    DungeonRun,
    DungeonRunEncounter,
    DungeonRunMember,
    EquipmentItem,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_confins_arquivo_dungeon import _scripted_result
from tests.test_professions_crafting_integration import (
    _add_materials,
    _seed_active_professions,
    _set_profession_level,
)
from tests.test_s6_p6_integration import _seed_final_campaign

D = Decimal


def _combat(ordinal: int, *, difficulty="stable", group_size=1):
    return create_confins_contradicoes_combat(
        uuid4(),
        name="Aventureira",
        character_class="sentinela",
        race="remanescente",
        hp=D(8_000),
        level=60,
        difficulty=difficulty,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"contradicoes:{ordinal}:{difficulty}:{group_size}",
        initial_group_size=group_size,
    )


def test_confins_contradicoes_family_roster_economy_and_recipe_are_canonical():
    family = DUNGEON_FAMILIES[CONFINS_CONTRADICOES_FAMILY_ID]
    assert family.name == "Câmara das Contradições"
    assert family.entry_location == CONFINS_NO_CENTRAL
    assert family.discovery_unlock == CONFINS_CONTRADICOES_DISCOVERY_UNLOCK
    assert family.required_quest_ids == ("P34",)
    assert (family.minimum_level, family.reference_level, family.encounter_count) == (
        58,
        60,
        5,
    )
    assert dict(family.completion_xp_by_difficulty) == {
        "stable": 15_550,
        "fractured": 19_050,
        "rupture": 24_240,
    }
    assert dict(family.first_clear_xp_by_difficulty) == {
        "stable": 24_880,
        "fractured": 30_480,
        "rupture": 38_784,
    }
    assert dict(family.crowns_by_difficulty) == {
        "stable": 800,
        "fractured": 1_200,
        "rupture": 1_800,
    }
    assert family.core_id == CONFINS_CONTRADICOES_CORE_ID
    assert family.recipe_unlock == CONFINS_CONTRADICOES_RECIPE_UNLOCK
    assert CONFINS_CONTRADICOES_BASIC_MATERIAL_WEIGHTS == (
        ("material.confins.ferro_baliza", 4_000),
        ("material.confins.couro_marcha", 1_000),
        ("material.confins.musgo_limiar", 1_500),
        ("material.confins.po_referencia", 3_500),
    )
    assert DIFFICULTIES["stable"].vigor == 25
    assert DIFFICULTIES["fractured"].vigor == 35
    assert DIFFICULTIES["rupture"].vigor == 50
    assert [DIFFICULTIES[key].consumable_limit for key in ("stable", "fractured", "rupture")] == [
        6,
        5,
        4,
    ]
    assert catalyst_material_id(60).endswith("catalisador_elite_vi")
    assert fragment_material_id(60).endswith("fragmento_aprimoramento_vi")

    expected = {
        1: [(CONFINS_VIGIA_DESFASADO, 58)],
        2: [(CONFINS_CONTRADICOES_CUSTODIO, 59)],
        3: [(CONFINS_CONTRADICOES_PRECEPTOR, 60)],
        4: [(CONFINS_CONTRADICOES_CUSTODIO, 60), (CONFINS_CONTRADICOES_PRECEPTOR, 60)],
        5: [
            (CONFINS_CONTRADICOES_BOSS, 60),
            (CONFINS_CONTRADICOES_PLATE_IDS[0], 60),
            (CONFINS_CONTRADICOES_PLATE_IDS[1], 60),
        ],
    }
    for ordinal, entries in expected.items():
        specs = confins_contradicoes_encounter_specs(ordinal, "stable", 1)
        assert [(spec.creature.creature_id, spec.level) for spec in specs] == entries
        assert [row[:2] for row in confins_contradicoes_enemy_rewards(ordinal)] == [
            row for row in entries if not row[0].startswith("encounter_element.")
        ]
        assert [row[0] for row in _enemy_rewards_for(
            type("Run", (), {
                "dungeon_family_id": CONFINS_CONTRADICOES_FAMILY_ID,
                "difficulty": "stable",
                "initial_group_size": 1,
            })(), ordinal
        )] == [row[0] for row in confins_contradicoes_enemy_rewards(ordinal)]
    assert len(expected[4]) == 2  # One multi-target encounter, not two encounters.

    recipe = canonical_recipe(CONFINS_CONTRADICOES_RECIPE_UNLOCK)
    assert recipe is not None
    assert recipe.output_id == "equipment.confins.special.guarda_duas_versoes"
    assert recipe.output_slot == "Secundária"
    assert recipe.rarity == "Épico" and recipe.grade == 6
    assert recipe.required_level == 15 and recipe.sw == 1
    assert recipe.fixed_materials == (
        type(recipe.fixed_materials[0])("material.confins.ferro_baliza", 7),
        type(recipe.fixed_materials[0])("material.confins.po_referencia", 3),
        type(recipe.fixed_materials[0])("material.tdo.catalisador_elite_vi", 2, False),
        type(recipe.fixed_materials[0])("material.tdo.fragmento_aprimoramento_vi", 6, False),
        type(recipe.fixed_materials[0])(CONFINS_CONTRADICOES_CORE_ID, 1),
    )
    assert recipe_crown_cost(recipe, 60) == 500
    assert weapon_type_id_for_recipe(CONFINS_CONTRADICOES_RECIPE_UNLOCK) == recipe.output_id
    weapon = weapon_definition(recipe.output_id)
    assert weapon is not None
    assert (
        weapon.weapon_form,
        weapon.handedness,
        weapon.slot_eligibility,
        weapon.compatibility_tags,
    ) == (
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        frozenset({"weapon.compat.melee"}),
    )


def test_confins_contradicoes_boss_actions_plates_phases_and_telegraph_persist():
    custody = creature_for(CONFINS_CONTRADICOES_CUSTODIO)
    assert custody.category == "elite" and custody.archetype == "armored"
    assert {row[0] for row in custody.actions} == {
        "impacto_coordenacao",
        "placa_no",
        "pressao_referencia",
        "travamento_passagem",
    }
    preceptor = creature_for(CONFINS_CONTRADICOES_PRECEPTOR)
    assert preceptor.category == "elite" and preceptor.archetype == "controller"
    assert {row[0] for row in preceptor.actions} == {
        "golpe_ordem",
        "ordem_a",
        "ordem_b",
        "confronto_registros",
    }

    solo = _combat(5)
    group = _combat(5, group_size=4)
    fractured = _combat(5, difficulty="fractured")
    boss = solo.fighters["testemunha"]
    actions = solo.enemy_actions
    assert creature_for(CONFINS_CONTRADICOES_BOSS).category == "boss"
    assert creature_for(CONFINS_CONTRADICOES_BOSS).archetype == "controller"
    assert set(actions) == {
        "e0_referencia_incompativel",
        "e0_revisao_contraditoria",
        "e0_placa_evidencia",
        "e0_leitura_sobreposta",
        "e0_afirmacao_final",
    }
    assert actions["e0_referencia_incompativel"].coefficient == D("1.00")
    revision = actions["e0_revisao_contraditoria"]
    assert revision.coefficient == D("0.90")
    assert revision.effect_stat == "defense" and revision.attack_debuff == D("0.12")
    assert revision.duration == 2 and revision.cooldown == 3
    barrier = actions["e0_placa_evidencia"]
    assert barrier.self_barrier_hp_fraction == D("0.08")
    assert barrier.cooldown == 4 and barrier.max_uses_per_combat == 2
    assert actions["e0_leitura_sobreposta"].target_mode == "all_opponents"
    assert actions["e0_leitura_sobreposta"].phase_ids == ("II", "III")
    prepared = actions["e0_afirmacao_final"]
    assert prepared.prepared and prepared.coefficient == D("1.85")
    assert prepared.cooldown == 5 and prepared.phase_ids == ("III",)
    assert boss.stats.hp < group.fighters["testemunha"].stats.hp
    assert fractured.fighters["testemunha"].stats.hp > boss.stats.hp
    assert solo.phase_id == "I"
    assert len(solo.phase_triggers) == 2
    assert [trigger.hp_fraction_at_most for trigger in solo.phase_triggers] == [
        D("0.70"),
        D("0.35"),
    ]
    plates = [solo.fighters[key] for key in ("placa_afirmacao_a", "placa_afirmacao_b")]
    assert all(plate.hp == 0 and plate.encounter_hidden for plate in plates)
    for fighter, spec in zip(
        plates,
        confins_contradicoes_encounter_specs(5, "stable", 1)[1:],
        strict=True,
    ):
        base = road_enemy_stats(spec.creature, 60)
        assert fighter.stats.hp == base.hp * D("0.25")
        assert fighter.stats.defense == base.defense
        assert not fighter.takes_turn and not fighter.required_for_victory

    boss.hp = boss.stats.hp * D("0.70")
    _resolve_phase_triggers(solo)
    assert solo.phase_id == "II"
    assert all(plate.hp == plate.stats.hp and not plate.encounter_hidden for plate in plates)
    assert _damage_aura_reduction(solo, "testemunha") == D("0.10")
    phase_events = set(solo.phase_triggered_ids)
    _resolve_phase_triggers(solo)
    assert solo.phase_triggered_ids == phase_events

    plates[0].hp = 0
    assert _damage_aura_reduction(solo, "testemunha") == D("0.05")
    barrier_before_phase_iii = boss.barrier
    boss.hp = boss.stats.hp * D("0.35")
    _resolve_phase_triggers(solo)
    assert solo.phase_id == "III"
    assert _damage_aura_reduction(solo, "testemunha") == 0
    assert plates[0].hp == 0 and plates[1].hp == 0
    assert boss.barrier - barrier_before_phase_iii == (
        boss.stats.hp * D("0.05")
    ).to_integral_value(rounding=ROUND_FLOOR)
    restored = decode(encode(solo), solo.id, solo.ruleset, solo.version)
    assert restored.phase_id == "III"
    assert {CONFINS_CONTRADICOES_PHASE_II, CONFINS_CONTRADICOES_PHASE_III}.issubset(
        restored.phase_triggered_ids
    )
    assert restored.fighters["placa_afirmacao_a"].hp == 0
    assert restored.enemy_actions["e0_afirmacao_final"].phase_ids == ("III",)

    no_plates = _combat(5)
    no_plates_boss = no_plates.fighters["testemunha"]
    no_plates_boss.hp = no_plates_boss.stats.hp * D("0.70")
    _resolve_phase_triggers(no_plates)
    no_plates.fighters["placa_afirmacao_a"].hp = 0
    no_plates.fighters["placa_afirmacao_b"].hp = 0
    no_plates_barrier_before_phase_iii = no_plates_boss.barrier
    no_plates_boss.hp = no_plates_boss.stats.hp * D("0.35")
    _resolve_phase_triggers(no_plates)
    assert no_plates_boss.barrier == no_plates_barrier_before_phase_iii

    both_plates = _combat(5)
    both_boss = both_plates.fighters["testemunha"]
    both_boss.hp = both_boss.stats.hp * D("0.70")
    _resolve_phase_triggers(both_plates)
    both_barrier_before_phase_iii = both_boss.barrier
    both_boss.hp = both_boss.stats.hp * D("0.35")
    _resolve_phase_triggers(both_plates)
    assert both_boss.barrier - both_barrier_before_phase_iii == (
        both_boss.stats.hp * D("0.10")
    ).to_integral_value(rounding=ROUND_FLOOR)
    assert all(
        both_plates.fighters[key].hp == 0
        and both_plates.fighters[key].encounter_hidden
        for key in CONFINS_CONTRADICOES_PLATE_KEYS
    )

    telegraph = _combat(5)
    telegraph_boss = telegraph.fighters["testemunha"]
    telegraph_boss.hp = telegraph_boss.stats.hp * D("0.35")
    _resolve_phase_triggers(telegraph)
    for key in (
        "e0_placa_evidencia",
        "e0_revisao_contraditoria",
        "e0_leitura_sobreposta",
        "e0_referencia_incompativel",
    ):
        telegraph_boss.cooldowns[key] = 999
    actor = active_player_key(telegraph)
    target = action_target_ids(telegraph, "attack", actor_key=actor)[0]
    telegraph = act(telegraph, "attack", target_id=target, actor_key=actor)
    assert telegraph.prepared_action == "e0_afirmacao_final"
    persisted_telegraph = decode(
        encode(telegraph), telegraph.id, telegraph.ruleset, telegraph.version
    )
    assert persisted_telegraph.prepared_action == "e0_afirmacao_final"

    assert CONFINS_CONTRADICOES_BOSS_MASTERY[CONFINS_CONTRADICOES_BOSS] == {
        "first_victory",
        "mechanic:affirmation_plates_observed",
        "action:revisao_contraditoria",
        "stable_first_clear",
    }


async def _seed_chamber_actor(database, actor: int, *, level=60, discovered=True):
    character_id, sessions = await _seed_final_campaign(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.vigor = 100
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = "Confins do Véu"
        world.location = CONFINS_NO_CENTRAL
        session.add(
            Quest(
                character_id=character_id,
                quest_id="P34",
                title="A Âncora Central",
                status="completed",
                step=6,
                content_version="confins-1.0.0",
                progress={"completed": True},
            )
        )
        if discovered:
            session.add(
                Unlock(
                    character_id=character_id,
                    unlock_id=CONFINS_CONTRADICOES_DISCOVERY_UNLOCK,
                )
            )
    return character_id, sessions


async def _clear_chamber_run(
    service,
    actor,
    difficulty,
    monkeypatch,
    *,
    fail_once=None,
    brazier_exists=True,
):
    brazier_rolls = []
    attempts = set()

    def roll_brazier(seed, requested_difficulty):
        brazier_rolls.append((seed, requested_difficulty))
        return brazier_exists

    def scripted_action(state, action_id, *, target_id=None, actor_key=None):
        ordinal = state.configuration_snapshot["dungeon"]["ordinal"]
        should_fail = fail_once == ordinal and ordinal not in attempts
        attempts.add(ordinal)
        if should_fail:
            return _scripted_result(
                state,
                action_id,
                target_id=target_id,
                actor_key=actor_key,
                defeat=True,
            )

        observed = deepcopy(state)
        if ordinal == 5:
            boss = observed.fighters["testemunha"]
            boss.hp = boss.stats.hp * D("0.70")
            _resolve_phase_triggers(observed)
            boss.hp = boss.stats.hp * D("0.35")
            _resolve_phase_triggers(observed)
        updated = _scripted_result(
            observed,
            action_id,
            target_id=target_id,
            actor_key=actor_key,
        )
        if ordinal == 5:
            boss = updated.fighters["testemunha"]
            updated.events.append(
                CombatEvent(
                    len(updated.events),
                    updated.round,
                    "testemunha",
                    "e0_revisao_contraditoria",
                    actor_entity_id=boss.id,
                )
            )
        return updated

    monkeypatch.setattr("asterion.application.dungeons.roll_brazier", roll_brazier)
    monkeypatch.setattr("asterion.application.dungeons.act", scripted_action)
    current = await service.start_solo(
        actor, difficulty, family_id=CONFINS_CONTRADICOES_FAMILY_ID
    )
    assert current is not None and current.run_id is not None
    run_id = current.run_id
    assert current.has_brazier is None
    for ordinal in range(1, 6):
        if current.kind == "retry":
            failed = current
            current = await service.retry(actor, run_id, failed.state_version)
            assert current is not None and current.kind == "ready"
            current = await service.resume(actor)
            assert current is not None and current.kind == "ready"
            assert current.run_id == run_id
        if current.kind == "brazier":
            current = await service.activate_brazier(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
        fight = await service.begin_encounter(actor, run_id, current.state_version)
        assert fight is not None and fight.kind == "combat" and fight.combat is not None
        assert fight.activity_id is not None
        assert fight.combat.configuration_snapshot["dungeon"]["ordinal"] == ordinal
        enemies = [fighter for fighter in fight.combat.fighters.values() if fighter.side == "enemy"]
        expected = {
            1: ["Vigia Desfasado"],
            2: ["Custódio do Nó Central"],
            3: ["Preceptor de Contradição"],
            4: ["Custódio do Nó Central", "Preceptor de Contradição"],
            5: ["Testemunha Impossível", "Placa de Afirmação A", "Placa de Afirmação B"],
        }[ordinal]
        assert sorted(fighter.name for fighter in enemies) == sorted(expected)
        if ordinal == 4:
            assert len(enemies) == 2
            async with service.sessions() as session:
                encounter = await session.get(DungeonRunEncounter, (run_id, 4))
                assert encounter is not None
                assert encounter.encounter_ordinal == 4

        target = action_target_ids(fight.combat, "attack", actor_key="player")[0]
        current = await service.action(
            actor,
            run_id,
            fight.activity_id,
            fight.combat.version,
            "attack",
            target,
        )
        assert current is not None
        if current.kind == "failed":
            return current, run_id, brazier_rolls
        if current.kind == "retry":
            assert current.kind == "retry"
            current = await service.retry(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
            current = await service.resume(actor)
            assert current is not None and current.kind == "ready"
            fight = await service.begin_encounter(actor, run_id, current.state_version)
            assert fight is not None and fight.kind == "combat" and fight.combat is not None
            target = action_target_ids(fight.combat, "attack", actor_key="player")[0]
            current = await service.action(
                actor,
                run_id,
                fight.activity_id,
                fight.combat.version,
                "attack",
                target,
            )
            assert current is not None
        if ordinal == 3 and current.kind == "brazier":
            current = await service.activate_brazier(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
    return current, run_id, brazier_rolls


@pytest.mark.asyncio
async def test_confins_contradicoes_discovery_and_level_gates_postgres(database):
    actor = 992_101
    character_id, sessions = await _seed_chamber_actor(
        database, actor, level=57, discovered=False
    )
    service = DungeonService(sessions, "ocaso")
    assert (await service.detail(actor, CONFINS_CONTRADICOES_FAMILY_ID)).kind == "hidden"
    blocked = await service.start_solo(
        actor, "stable", family_id=CONFINS_CONTRADICOES_FAMILY_ID
    )
    assert blocked is not None and blocked.reason == "gate"

    async with sessions.begin() as session:
        session.add(
            Unlock(
                character_id=character_id,
                unlock_id=CONFINS_CONTRADICOES_DISCOVERY_UNLOCK,
            )
        )
    detail = await service.detail(actor, CONFINS_CONTRADICOES_FAMILY_ID)
    assert detail is not None and detail.kind == "detail"
    assert dict(detail.difficulty_gates)["stable"] == "level"
    blocked = await service.start_solo(
        actor, "stable", family_id=CONFINS_CONTRADICOES_FAMILY_ID
    )
    assert blocked is not None and blocked.reason == "level"

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 58
    detail = await service.detail(actor, CONFINS_CONTRADICOES_FAMILY_ID)
    assert detail is not None and dict(detail.difficulty_gates)["stable"] == "available"
    created = await service.start_solo(
        actor, "stable", family_id=CONFINS_CONTRADICOES_FAMILY_ID
    )
    assert created is not None and created.run_id is not None
    async with sessions() as session:
        run = await session.get(DungeonRun, created.run_id)
        assert run is not None and run.reference_level == 60
        assert run.has_brazier in {True, False}
        assert await session.scalar(
            select(func.count(Unlock.id)).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == CONFINS_CONTRADICOES_FIRST_CLEAR_PREFIX + "stable",
            )
        ) == 0


@pytest.mark.asyncio
async def test_confins_contradicoes_group_invitation_rejects_individually_ineligible_member(
    database,
):
    leader_actor = 992_105
    target_actor = 992_106
    _leader_id, sessions = await _seed_chamber_actor(database, leader_actor, level=60)
    target_id, _target_sessions = await _seed_final_campaign(
        database, target_actor, level=60
    )
    async with sessions.begin() as session:
        target = await session.get(Character, target_id)
        assert target is not None
        target_name = target.name
        target.vigor = 100
        world = await session.get(WorldState, target_id)
        assert world is not None
        world.region = "Confins do Véu"
        world.location = CONFINS_NO_CENTRAL
        session.add(
            Unlock(
                character_id=target_id,
                unlock_id=CONFINS_CONTRADICOES_DISCOVERY_UNLOCK,
            )
        )
    service = DungeonService(sessions, "ocaso")
    lobby = await service.prepare_group(
        leader_actor, CONFINS_CONTRADICOES_FAMILY_ID, "stable"
    )
    assert lobby is not None and lobby.lobby_id is not None
    rejected = await service.invite_by_name(
        leader_actor, lobby.lobby_id, lobby.lobby_version, target_name
    )
    assert rejected is not None and rejected.reason
    async with sessions() as session:
        target = await session.get(Character, target_id)
        assert target is not None and target.vigor == 100
        assert await session.scalar(select(func.count(DungeonRun.id))) == 0


@pytest.mark.asyncio
async def test_confins_contradicoes_stable_run_retry_settlement_codex_and_bestiary_postgres(
    database, monkeypatch
):
    actor = 992_102
    character_id, sessions = await _seed_chamber_actor(database, actor, level=58)
    service = DungeonService(sessions, "ocaso")
    completed, run_id, brazier_rolls = await _clear_chamber_run(
        service, actor, "stable", monkeypatch, fail_once=4
    )
    assert completed.kind == "completed" and completed.first_clear
    assert len(brazier_rolls) == 1 and brazier_rolls[0][1] == "stable"

    async with sessions() as session:
        run = await session.get(DungeonRun, run_id)
        assert run is not None and run.status == "completed"
        assert run.has_brazier is True and run.brazier_activated is True
        encounters = (
            await session.scalars(
                select(DungeonRunEncounter)
                .where(DungeonRunEncounter.run_id == run_id)
                .order_by(DungeonRunEncounter.encounter_ordinal)
            )
        ).all()
        assert len(encounters) == 5 and all(row.status == "completed" for row in encounters)
        assert encounters[3].attempt_count == 2
        rewards = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"{CONFINS_CONTRADICOES_REWARD_PREFIX}{run_id.hex}",
                )
            )
        ).all()
        assert len(rewards) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == rewards[0].id)
            )
        ).all()
        xp = next(row for row in components if row.kind == "xp")
        crowns = next(row for row in components if row.kind == "crowns")
        assert xp.payload["completion"] == 24_880
        assert xp.payload["first_clear"] is True
        assert crowns.quantity == 800
        materials = {row.item_id: row.quantity for row in components if row.kind == "material"}
        assert sum(
            materials.get(item_id, 0)
            for item_id, _weight in CONFINS_CONTRADICOES_BASIC_MATERIAL_WEIGHTS
        ) == 8
        assert materials[CONFINS_CONTRADICOES_CORE_ID] == 1
        assert materials[catalyst_material_id(60)] == 2
        assert materials[fragment_material_id(60)] == 2
        assert sum(row.quantity for row in components if row.kind == "equipment") == 1
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id
                == _reward_source_id(
                    "first_victory", character_id, CONFINS_CONTRADICOES_BOSS
                ),
            )
        ) == 1
        milestone = await session.scalar(
            select(RewardComponent)
            .join(RewardEvent, RewardComponent.reward_event_id == RewardEvent.id)
            .where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id
                == _reward_source_id(
                    "first_victory", character_id, CONFINS_CONTRADICOES_BOSS
                ),
                RewardComponent.kind == "bestiary_first_victory_xp",
                RewardComponent.item_id == CONFINS_CONTRADICOES_BOSS,
            )
        )
        assert milestone is not None and milestone.quantity == 6_114
        codex = set(
            (
                await session.scalars(
                    select(CodexEntry.entry_id).where(
                        CodexEntry.character_id == character_id,
                        CodexEntry.entry_id.in_(
                            {
                                CONFINS_CONTRADICOES_CODEX_ENTRY,
                                CONFINS_CONTRADICOES_RECORD_CODEX_ENTRY,
                                CONFINS_CONTRADICOES_BOSS_CODEX_ENTRY,
                            }
                        ),
                    )
                )
            ).all()
        )
        assert codex == {
            CONFINS_CONTRADICOES_CODEX_ENTRY,
            CONFINS_CONTRADICOES_RECORD_CODEX_ENTRY,
            CONFINS_CONTRADICOES_BOSS_CODEX_ENTRY,
        }
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "achievement.confins.contradicoes_estavel",
            )
        ) is not None
        boss = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == CONFINS_CONTRADICOES_BOSS,
            )
        )
        assert boss is not None
        observed = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == CONFINS_CONTRADICOES_BOSS,
                    )
                )
            ).all()
        )
        assert {
            "first_victory",
            "phase:afirmacoes_incompativeis",
            "phase:afirmacao_final",
            "mechanic:placas_consumidas",
            "mechanic:affirmation_plates_observed",
            "action:revisao_contraditoria",
            "stable_first_clear",
        }.issubset(observed)


@pytest.mark.asyncio
async def test_confins_contradicoes_wipe_without_brazier_fails_run_and_refunds_vigor(
    database, monkeypatch
):
    actor = 992_103
    character_id, sessions = await _seed_chamber_actor(database, actor, level=58)
    service = DungeonService(sessions, "ocaso")
    current, run_id, brazier_rolls = await _clear_chamber_run(
        service,
        actor,
        "stable",
        monkeypatch,
        fail_once=1,
        brazier_exists=False,
    )
    assert current.kind == "failed" and not current.brazier_activated
    assert len(brazier_rolls) == 1
    async with sessions() as session:
        run = await session.get(DungeonRun, run_id)
        encounter = await session.get(DungeonRunEncounter, (run_id, 1))
        member = await session.get(DungeonRunMember, (run_id, character_id))
        character = await session.get(Character, character_id)
        assert run is not None and run.status == "failed"
        assert encounter is not None and encounter.status != "completed"
        assert member is not None and member.vigor_refunded
        assert character is not None and character.vigor == character.max_vigor
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id.startswith(CONFINS_CONTRADICOES_REWARD_PREFIX),
            )
        ) == 0
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == CONFINS_CONTRADICOES_FIRST_CLEAR_PREFIX + "stable",
            )
        ) is None


@pytest.mark.asyncio
async def test_confins_contradicoes_difficulty_progression_stable_fractured_rupture_postgres(
    database, monkeypatch
):
    actor = 992_104
    character_id, sessions = await _seed_chamber_actor(database, actor, level=60)
    service = DungeonService(sessions, "ocaso")
    references = []
    for difficulty, expected_xp, expected_crowns in (
        ("stable", 24_880, 800),
        ("fractured", 30_480, 1_200),
        ("rupture", 38_784, 1_800),
    ):
        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            assert character is not None
            character.vigor = 100
            world = await session.get(WorldState, character_id)
            assert world is not None
            world.location = CONFINS_NO_CENTRAL
        completed, run_id, _rolls = await _clear_chamber_run(
            service, actor, difficulty, monkeypatch
        )
        assert completed.kind == "completed" and completed.first_clear
        async with sessions() as session:
            run = await session.get(DungeonRun, run_id)
            event = await session.scalar(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"{CONFINS_CONTRADICOES_REWARD_PREFIX}{run_id.hex}",
                )
            )
            assert run is not None and event is not None
            references.append(run.reference_level)
            xp = await session.scalar(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == event.id,
                    RewardComponent.kind == "xp",
                )
            )
            crowns = await session.scalar(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == event.id,
                    RewardComponent.kind == "crowns",
                )
            )
            assert xp.payload["completion"] == expected_xp
            assert crowns.quantity == expected_crowns
    assert references == [60, 60, 60]
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id.startswith(CONFINS_CONTRADICOES_REWARD_PREFIX),
            )
        ) == 3
        for difficulty in ("stable", "fractured", "rupture"):
            assert await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == CONFINS_CONTRADICOES_FIRST_CLEAR_PREFIX + difficulty,
                )
            ) is not None


@pytest.mark.asyncio
async def test_confins_contradicoes_recipe_craft_uses_canonical_weapon_metadata_postgres(
    database,
):
    actor = 992_107
    character_id = await _seed_active_professions(database, actor, "blacksmith", "alchemist")
    await _set_profession_level(database, character_id, "blacksmith", 15)
    await _add_materials(
        database,
        character_id,
        {
            "material.confins.ferro_baliza": 7,
            "material.confins.po_referencia": 3,
            "material.tdo.catalisador_elite_vi": 2,
            "material.tdo.fragmento_aprimoramento_vi": 6,
            CONFINS_CONTRADICOES_CORE_ID: 1,
        },
    )
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 60
        character.crowns = 5_000
        session.add(
            Unlock(
                character_id=character_id,
                unlock_id=CONFINS_CONTRADICOES_RECIPE_UNLOCK,
            )
        )
    service = CraftingService(database[1], "ocaso")
    preview = await service.preview(actor, CONFINS_CONTRADICOES_RECIPE_UNLOCK)
    assert preview is not None
    assert preview.item_level == 60 and preview.crown_cost == 500
    assert {item.material_id: item.required for item in preview.ingredients} == {
        "material.confins.ferro_baliza": 7,
        "material.confins.po_referencia": 3,
        "material.tdo.catalisador_elite_vi": 2,
        "material.tdo.fragmento_aprimoramento_vi": 6,
        CONFINS_CONTRADICOES_CORE_ID: 1,
    }
    crafted = await service.commit(actor, preview.receipt_id)
    repeated = await service.commit(actor, preview.receipt_id)
    assert crafted is not None and repeated is not None
    equipment_item_id = crafted.output_payload["equipment_item_id"]
    assert repeated.output_payload["equipment_item_id"] == equipment_item_id
    assert (
        crafted.output_payload["equipment"]["weapon_type_id"]
        == "equipment.confins.special.guarda_duas_versoes"
    )
    assert crafted.output_payload["equipment"]["slot"] == "Secundária"
    assert crafted.output_payload["equipment"]["enhancement"] == 0

    async with database[1]() as session:
        character = await session.get(Character, character_id)
        equipment = await session.get(EquipmentItem, UUID(equipment_item_id))
        assert character is not None and character.crowns == 4_500
        assert equipment is not None
        assert equipment.rarity == "Épico"
        assert equipment.slot == "Secundária" and equipment.item_level == 60
        assert equipment.payload["weapon_type_id"] == (
            "equipment.confins.special.guarda_duas_versoes"
        )
        assert equipment.payload["slot"] == "Secundária"
        assert "weapon_family" not in equipment.payload
        assert await session.scalar(
            select(func.count(EquipmentItem.id)).where(
                EquipmentItem.character_id == character_id,
                EquipmentItem.source_key.like("craft:%:equipment"),
            )
        ) == 1
        assert await session.scalar(
            select(func.count(MaterialStack.id)).where(
                MaterialStack.character_id == character_id,
            )
        ) == 0

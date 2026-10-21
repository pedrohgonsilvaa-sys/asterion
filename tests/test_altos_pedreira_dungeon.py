from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.bestiary import ALTOS_PEDREIRA_DISTINCTIVE_BOSS_MASTERY
from asterion.application.dungeons import (
    ALTOS_PEDREIRA_FAMILY_ID,
    DUNGEON_FAMILIES,
    DungeonService,
    _encounter_specs,
    _enemy_rewards_for,
)
from asterion.domain.altos_pedreira_dungeon import (
    ALTOS_PEDREIRA_BASIC_MATERIAL_WEIGHTS,
    ALTOS_PEDREIRA_CORE_ID,
    ALTOS_PEDREIRA_DISCOVERY_UNLOCK,
    ALTOS_PEDREIRA_FIRST_CLEAR_PREFIX,
    ALTOS_PEDREIRA_RECIPE_UNLOCK,
    altos_pedreira_encounter_specs,
    create_altos_pedreira_combat,
)
from asterion.domain.combat import (
    CombatEvent,
    _fighter_stat,
    action_target_ids,
    allowed_actions,
)
from asterion.domain.dungeons import (
    DIFFICULTIES,
    difficulty_gate,
    stable_draw,
    weighted_material_for_ordinal,
)
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.professions import canonical_recipe
from asterion.domain.road import (
    ALTOS_ESCARAVELHO_BASALTO,
    ALTOS_PEDREIRA_OPERARIO,
    ALTOS_PEDREIRA_PESO_SEM_FIM,
    ALTOS_PEDREIRA_PRENSOR,
    ALTOS_PEDREIRAS,
    ALTOS_REGION,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    CodexEntry,
    DungeonRun,
    DungeonRunEncounter,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_s6_p6_integration import _seed_final_campaign

D = Decimal


def _combat(ordinal: int, *, difficulty: str = "stable", group_size: int = 1):
    return create_altos_pedreira_combat(
        uuid4(),
        name="Aventureiro",
        character_class="sentinela",
        race="remanescente",
        hp=D(5000),
        level=47,
        difficulty=difficulty,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"altos-pedreira:{ordinal}:{difficulty}:{group_size}",
        initial_group_size=group_size,
    )


def test_altos_pedreira_family_and_difficulty_gates_are_canonical():
    family = DUNGEON_FAMILIES[ALTOS_PEDREIRA_FAMILY_ID]
    assert family.family_id == "dungeon.altos.pedreira_contrapeso"
    assert family.entry_location == "Pedreiras Suspensas"
    assert family.discovery_unlock == "unlock.dungeon.altos.pedreira_contrapeso"
    assert family.required_quest_ids == ("P27",)
    assert (family.minimum_level, family.reference_level, family.encounter_count) == (
        45,
        47,
        5,
    )
    assert difficulty_gate(
        level=45,
        discovered=True,
        stable_first_clear=False,
        fractured_first_clear=False,
        minimum_level=45,
    ) == {"stable": "available", "fractured": "first_stable", "rupture": "level"}
    assert (
        difficulty_gate(
            level=47,
            discovered=True,
            stable_first_clear=True,
            fractured_first_clear=False,
            minimum_level=45,
        )["fractured"]
        == "available"
    )
    assert (
        difficulty_gate(
            level=60,
            discovered=True,
            stable_first_clear=True,
            fractured_first_clear=True,
            minimum_level=45,
        )["rupture"]
        == "available"
    )


def test_altos_pedreira_has_five_exact_encounters_and_zero_economy_for_elements():
    expected = {
        1: {ALTOS_PEDREIRA_OPERARIO},
        2: {ALTOS_PEDREIRA_OPERARIO, ALTOS_ESCARAVELHO_BASALTO},
        3: {ALTOS_PEDREIRA_PRENSOR},
        4: {ALTOS_PEDREIRA_OPERARIO, "encounter_element.altos.pedreira.trava_carga"},
        5: {ALTOS_PEDREIRA_PESO_SEM_FIM},
    }
    for ordinal, creature_ids in expected.items():
        run = SimpleNamespace(
            dungeon_family_id=ALTOS_PEDREIRA_FAMILY_ID,
            difficulty="rupture",
            initial_group_size=4,
            reference_level=60,
        )
        specs = _encounter_specs(run, ordinal)
        assert {spec.creature.creature_id for spec in specs} == creature_ids
        expected_level = 45 if ordinal < 3 else 46 if ordinal < 5 else 47
        assert {spec.level for spec in specs} == {expected_level}
        assert {
            creature_id for creature_id, _level, _category in _enemy_rewards_for(run, ordinal)
        } == {spec.creature.creature_id for spec in specs if spec.required_for_victory}
    fourth = altos_pedreira_encounter_specs(4, "stable", 1)
    travas = [spec for spec in fourth if spec.fighter_key.startswith("trava_")]
    assert len(travas) == 3
    assert all(spec.passive and not spec.required_for_victory for spec in travas)
    assert all(spec.stat_multipliers.hp == D("0.20") for spec in travas)
    assert all(spec.stat_multipliers.defense == D("0.80") for spec in travas)
    assert [row[1] for row in _enemy_rewards_for(run, 4)] == [46]


def test_altos_pedreira_travas_supply_per_active_four_percent_defense():
    combat = _combat(4)
    operator_defense = combat.fighters["operario"].stats.defense
    assert len(combat.stat_auras) == 1
    assert combat.stat_auras[0].source_fighter_keys == ("trava_1", "trava_2", "trava_3")
    assert _fighter_stat(combat, "operario", "defense") == operator_defense * D("1.12")
    combat.fighters["trava_2"].hp = D(0)
    assert _fighter_stat(combat, "operario", "defense") == operator_defense * D("1.08")


def test_altos_pedreira_creatures_use_published_actions_and_boss_phases():
    first = _combat(1)
    assert set(first.enemy_actions) == {"ferramenta_inercial", "golpe_arrasto"}
    assert first.enemy_actions["ferramenta_inercial"].coefficient == D("1.00")
    assert first.enemy_actions["golpe_arrasto"].coefficient == D("0.85")
    assert first.enemy_actions["golpe_arrasto"].effect_stat == "defense"
    assert first.enemy_actions["golpe_arrasto"].attack_debuff == D("0.10")
    assert first.enemy_actions["golpe_arrasto"].duration == 2
    assert first.enemy_actions["golpe_arrasto"].cooldown == 3

    elite = _combat(3)
    assert set(elite.enemy_actions) == {
        "impacto_prensa",
        "placa_compressao",
        "pressao_trilho",
        "curso_completo",
    }
    assert elite.enemy_actions["placa_compressao"].self_barrier_coefficient == D("0.95")
    assert elite.enemy_actions["pressao_trilho"].coefficient == D("1.30")
    assert elite.enemy_actions["curso_completo"].prepared is True
    assert elite.enemy_actions["curso_completo"].coefficient == D("1.75")

    boss = _combat(5, difficulty="rupture", group_size=4)
    assert set(boss.enemy_actions) == {
        "impacto_carro",
        "cabo_tensao",
        "contrapeso_elevado",
        "contrapeso_baixo",
        "queda_massa",
    }
    assert boss.phase_id == "I"
    assert [(trigger.hp_fraction_at_most, trigger.phase_id) for trigger in boss.phase_triggers] == [
        (D("0.65"), "II"),
        (D("0.30"), "III"),
    ]
    elevated = boss.enemy_actions["contrapeso_elevado"]
    low = boss.enemy_actions["contrapeso_baixo"]
    fall = boss.enemy_actions["queda_massa"]
    assert elevated.cooldown == low.cooldown == 5
    assert elevated.self_effects[0].magnitude == D("0.08")
    assert elevated.self_effects[1].magnitude == D("0.08")
    assert elevated.skip_if_any_self_effect_active == (
        "altos.pedreira.contrapeso_elevado.attack",
        "altos.pedreira.contrapeso_baixo.attack",
    )
    assert low.self_barrier_hp_fraction == D("0.08")
    assert low.self_barrier_duration == 2 and low.skip_if_barrier_active
    assert low.skip_if_self_effect_active == "altos.pedreira.contrapeso_elevado.attack"
    assert low.phase_ids == ("I", "II")
    assert fall.prepared is True and fall.coefficient == D("1.80") and fall.cooldown == 5
    assert fall.skip_if_actor_last_action == ("queda_massa",)
    assert boss.phase_triggers[0].ai_priority != boss.phase_triggers[1].ai_priority
    assert boss.configuration_snapshot["dungeon"]["initial_group_size"] == 4
    assert boss.fighters["peso_sem_fim"].stats.hp > _combat(5).fighters["peso_sem_fim"].stats.hp


def test_altos_pedreira_boss_constraints_survive_combat_snapshot_codec():
    combat = _combat(5)
    restored = decode(encode(combat), combat.id, combat.ruleset, combat.version)
    elevated = restored.enemy_actions["contrapeso_elevado"]
    assert elevated.skip_if_any_self_effect_active == (
        "altos.pedreira.contrapeso_elevado.attack",
        "altos.pedreira.contrapeso_baixo.attack",
    )
    assert restored.phase_triggers[0].ai_priority == combat.phase_triggers[0].ai_priority
    assert restored.enemy_actions["queda_massa"].skip_if_actor_last_action == ("queda_massa",)


def test_altos_pedreira_settlement_recipe_and_knowledge_contracts():
    family = DUNGEON_FAMILIES[ALTOS_PEDREIRA_FAMILY_ID]
    assert dict(family.completion_xp_by_difficulty) == {
        "stable": 12_590,
        "fractured": 15_430,
        "rupture": 24_240,
    }
    assert dict(family.first_clear_xp_by_difficulty) == {
        "stable": 20_144,
        "fractured": 24_688,
        "rupture": 38_784,
    }
    assert dict(family.crowns_by_difficulty) == {"stable": 650, "fractured": 970, "rupture": 1_800}
    assert family.basic_material_weights == ALTOS_PEDREIRA_BASIC_MATERIAL_WEIGHTS
    assert DIFFICULTIES["rupture"].reference_level == 60
    assert DIFFICULTIES["rupture"].cores == 4
    assert DIFFICULTIES["rupture"].catalysts == 4
    assert DIFFICULTIES["rupture"].fragments == 7
    assert ALTOS_PEDREIRA_CORE_ID == family.core_id
    assert ALTOS_PEDREIRA_FIRST_CLEAR_PREFIX == family.first_clear_prefix
    assert ALTOS_PEDREIRA_RECIPE_UNLOCK == family.recipe_unlock

    materials = {material_id for material_id, _weight in family.basic_material_weights}
    results = [
        weighted_material_for_ordinal("fixed-seed", i, family.basic_material_weights)
        for i in range(100)
    ]
    assert set(results) <= materials
    assert results == [
        weighted_material_for_ordinal("fixed-seed", i, family.basic_material_weights)
        for i in range(100)
    ]

    recipe = canonical_recipe("recipe.altos.pedreira.relicario_peso_suspenso")
    assert recipe is not None
    assert (
        recipe.output_id,
        recipe.profession_id,
        recipe.required_level,
        recipe.grade,
        recipe.rarity,
        recipe.output_slot,
        recipe.sw,
    ) == (
        "equipment.altos.special.relicario_peso_suspenso",
        "jeweler",
        12,
        5,
        "Raro",
        "Artefato",
        2,
    )
    assert [(row.material_id, row.quantity) for row in recipe.fixed_materials] == [
        ("material.altos.ferro_contrapeso", 10),
        ("material.altos.cinza_basalto", 6),
        ("material.tdo.fragmento_aprimoramento_v", 8),
        (ALTOS_PEDREIRA_CORE_ID, 1),
    ]
    assert ALTOS_PEDREIRA_DISTINCTIVE_BOSS_MASTERY[ALTOS_PEDREIRA_PESO_SEM_FIM] == {
        "first_victory",
        "action:contrapeso_elevado",
        "action:contrapeso_baixo",
        "action:queda_massa",
    }


@pytest.mark.asyncio
async def test_altos_pedreira_is_discovery_and_p27_gated_and_settles_once(database, monkeypatch):
    actor = 994_700
    character_id, sessions = await _seed_final_campaign(database, actor, level=45)
    service = DungeonService(sessions, "ocaso")
    async with sessions.begin() as session:
        character_world = await session.get(WorldState, character_id)
        assert character_world is not None
        character_world.region = ALTOS_REGION
        character_world.location = ALTOS_PEDREIRAS
        session.add(
            Quest(
                character_id=character_id,
                quest_id="P27",
                title="A Continuidade a Qualquer Custo",
                status="completed",
                step=7,
                content_version="altos-1.0.1",
                progress={"completed": True},
            )
        )

    assert (await service.detail(actor, ALTOS_PEDREIRA_FAMILY_ID)).kind == "hidden"
    blocked = await service.start_solo(actor, "stable", family_id=ALTOS_PEDREIRA_FAMILY_ID)
    assert blocked is not None and blocked.kind == "detail" and blocked.reason == "gate"
    hidden_map = await service.known(actor)
    assert hidden_map is not None and all(
        row[0] != ALTOS_PEDREIRA_FAMILY_ID for row in hidden_map.known_dungeons
    )

    async with sessions.begin() as session:
        session.add(Unlock(character_id=character_id, unlock_id=ALTOS_PEDREIRA_DISCOVERY_UNLOCK))
    detail = await service.detail(actor, ALTOS_PEDREIRA_FAMILY_ID)
    assert detail is not None and detail.kind == "detail"
    assert dict(detail.difficulty_gates)["stable"] == "available"
    known_map = await service.known(actor)
    assert known_map is not None
    assert any(row[0] == ALTOS_PEDREIRA_FAMILY_ID for row in known_map.known_dungeons)

    brazier_rolls = []
    monkeypatch.setattr(
        "asterion.application.dungeons.roll_brazier",
        lambda seed, difficulty: brazier_rolls.append((seed, difficulty)) or True,
    )

    def controlled_victory(
        state,
        action_id,
        *,
        target_id=None,
        actor_key=None,
        effect_id: str | None = None,
    ):
        assert effect_id is None
        actor_key = actor_key or "player"
        if action_id not in allowed_actions(state, actor_key):
            return state
        targets = action_target_ids(state, action_id, actor_key=actor_key)
        if target_id not in targets:
            return state
        updated = deepcopy(state)
        actor_fighter = updated.fighters[actor_key]
        updated.events.append(
            CombatEvent(
                len(updated.events),
                updated.round,
                actor_key,
                action_id,
                target=target_id,
                actor_entity_id=actor_fighter.id,
            )
        )
        for fighter in updated.fighters.values():
            if fighter.side == "enemy" and fighter.required_for_victory:
                fighter.hp = D(0)
        updated.result = "victory"
        updated.version += 1
        return updated

    monkeypatch.setattr("asterion.application.dungeons.act", controlled_victory)
    created = await service.start_solo(actor, "stable", family_id=ALTOS_PEDREIRA_FAMILY_ID)
    assert created is not None and created.run_id is not None
    run_id = created.run_id
    current = created
    assert len(brazier_rolls) == 1

    for ordinal in range(1, 6):
        if current.kind == "brazier":
            current = await service.activate_brazier(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
        fight = await service.begin_encounter(actor, run_id, current.state_version)
        assert fight is not None and fight.kind == "combat" and fight.combat is not None
        assert fight.activity_id is not None
        assert fight.combat.configuration_snapshot["dungeon"]["ordinal"] == ordinal
        if ordinal == 4:
            enemies = [
                fighter for fighter in fight.combat.fighters.values() if fighter.side == "enemy"
            ]
            assert len(enemies) == 4
            assert sum(fighter.required_for_victory for fighter in enemies) == 1
        if ordinal == 5:
            enemies = [
                fighter for fighter in fight.combat.fighters.values() if fighter.side == "enemy"
            ]
            assert len(enemies) == 1
            assert enemies[0].name == "Peso sem Fim"
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
        if ordinal == 3:
            assert current.kind == "brazier"
            assert len(brazier_rolls) == 1
    assert current.kind == "completed"
    assert len(brazier_rolls) == 1

    async with sessions() as session:
        run = await session.get(DungeonRun, run_id)
        assert run is not None and run.status == "completed"
        assert run.has_brazier is True and run.brazier_activated is True
        assert (
            await session.scalar(
                select(func.count(DungeonRunEncounter.run_id)).where(
                    DungeonRunEncounter.run_id == run_id
                )
            )
            == 5
        )
        events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id
                    == f"{DUNGEON_FAMILIES[ALTOS_PEDREIRA_FAMILY_ID].reward_prefix}{run_id.hex}",
                )
            )
        ).all()
        assert len(events) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == events[0].id)
            )
        ).all()
        xp = next(row for row in components if row.kind == "xp")
        crowns = next(row for row in components if row.kind == "crowns")
        assert xp.payload["completion"] == 20_144
        assert crowns.quantity == 650
        material_rows = [row for row in components if row.kind == "material"]
        material_counts = {row.item_id: row.quantity for row in material_rows}
        assert (
            sum(
                material_counts.get(item, 0)
                for item, _weight in ALTOS_PEDREIRA_BASIC_MATERIAL_WEIGHTS
            )
            == 8
        )
        assert material_counts["material.tdo.catalisador_elite_v"] == 2
        assert material_counts[ALTOS_PEDREIRA_CORE_ID] == 1
        assert material_counts["material.tdo.fragmento_aprimoramento_v"] == 2
        equipment = next(row for row in components if row.kind == "equipment")
        assert equipment.quantity == 1 and equipment.payload["item_level"] == 47
        assert (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == ALTOS_PEDREIRA_FIRST_CLEAR_PREFIX + "stable",
                )
            )
            is not None
        )
        assert (
            await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character_id,
                    Achievement.achievement_id == "achievement.altos.pedreira_primeira",
                )
            )
            is not None
        )
        codex = set(
            (
                await session.scalars(
                    select(CodexEntry.entry_id).where(
                        CodexEntry.character_id == character_id,
                        CodexEntry.entry_id.in_(
                            (
                                "codex.altos.dungeon.pedreira_contrapeso",
                                "codex.altos.dungeon.ciclo_contrapeso",
                                "codex.altos.dungeon.peso_sem_fim",
                            )
                        ),
                    )
                )
            ).all()
        )
        assert codex == {
            "codex.altos.dungeon.pedreira_contrapeso",
            "codex.altos.dungeon.ciclo_contrapeso",
            "codex.altos.dungeon.peso_sem_fim",
        }
        boss_entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == ALTOS_PEDREIRA_PESO_SEM_FIM,
            )
        )
        assert boss_entry is not None and boss_entry.stage != "dominated"
        boss_evidence = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == ALTOS_PEDREIRA_PESO_SEM_FIM,
                    )
                )
            ).all()
        )
        assert "first_victory" in boss_evidence
        recipe_seed = f"{run.seed}:member:{character_id.hex}"
        expected_recipe = (
            stable_draw(recipe_seed, "recipe.discovery", 10_000)
            < DIFFICULTIES["stable"].recipe_chance * 100
        )
        assert (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == ALTOS_PEDREIRA_RECIPE_UNLOCK,
                )
            )
            is not None
        ) is expected_recipe

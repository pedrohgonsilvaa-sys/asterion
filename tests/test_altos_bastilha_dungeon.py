from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.bestiary import ALTOS_BASTILHA_DISTINCTIVE_BOSS_MASTERY
from asterion.application.dungeons import (
    ALTOS_BASTILHA_FAMILY_ID,
    DUNGEON_FAMILIES,
    DungeonService,
    _encounter_specs,
    _enemy_rewards_for,
)
from asterion.domain.altos_bastilha_dungeon import (
    ALTOS_BASTILHA_BASIC_MATERIAL_WEIGHTS,
    ALTOS_BASTILHA_CORE_ID,
    ALTOS_BASTILHA_DISCOVERY_UNLOCK,
    ALTOS_BASTILHA_FIRST_CLEAR_PREFIX,
    ALTOS_BASTILHA_GUARDIAN,
    ALTOS_BASTILHA_PHASE_II,
    ALTOS_BASTILHA_PHASE_III,
    ALTOS_BASTILHA_RECIPE_UNLOCK,
    altos_bastilha_encounter_specs,
    create_altos_bastilha_combat,
)
from asterion.domain.combat import (
    CombatEvent,
    _damage_aura_reduction,
    _resolve_phase_triggers,
    action_target_ids,
    allowed_actions,
)
from asterion.domain.dungeons import DIFFICULTIES, difficulty_gate, stable_draw
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.professions import ALTOS_BASTILHA_CORE, canonical_recipe
from asterion.domain.road import (
    ALTOS_BASTILHA,
    ALTOS_BASTILHA_COORDENADOR_CARGA,
    ALTOS_BASTILHA_CUSTODIO_PONTE,
    ALTOS_QUEBRA_CABOS,
    ALTOS_REGION,
    ALTOS_VIGIA_CARGA,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
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
    return create_altos_bastilha_combat(
        uuid4(),
        name="Aventureiro",
        character_class="sentinela",
        race="remanescente",
        hp=D(5_000),
        level=50,
        difficulty=difficulty,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"altos-bastilha:{ordinal}:{difficulty}:{group_size}",
        initial_group_size=group_size,
    )


def test_altos_bastilha_family_gates_encounters_and_reward_contract_are_canonical():
    family = DUNGEON_FAMILIES[ALTOS_BASTILHA_FAMILY_ID]
    assert family.entry_location == ALTOS_BASTILHA
    assert family.discovery_unlock == ALTOS_BASTILHA_DISCOVERY_UNLOCK
    assert family.required_quest_ids == ("P28",)
    assert (family.minimum_level, family.reference_level, family.encounter_count) == (
        48,
        50,
        5,
    )
    assert difficulty_gate(
        level=48,
        discovered=True,
        stable_first_clear=False,
        fractured_first_clear=False,
        minimum_level=48,
    ) == {"stable": "available", "fractured": "first_stable", "rupture": "level"}
    assert (
        difficulty_gate(
            level=60,
            discovered=True,
            stable_first_clear=True,
            fractured_first_clear=True,
            minimum_level=48,
        )["rupture"]
        == "available"
    )

    expected = {
        1: {ALTOS_VIGIA_CARGA},
        2: {ALTOS_VIGIA_CARGA, ALTOS_QUEBRA_CABOS},
        3: {ALTOS_BASTILHA_CUSTODIO_PONTE},
        4: {ALTOS_BASTILHA_COORDENADOR_CARGA},
        5: {ALTOS_BASTILHA_GUARDIAN, "encounter_element.altos.bastilha.ponto_ancoragem"},
    }
    for ordinal, creature_ids in expected.items():
        run = SimpleNamespace(
            dungeon_family_id=ALTOS_BASTILHA_FAMILY_ID,
            difficulty="rupture",
            initial_group_size=4,
            reference_level=60,
        )
        specs = _encounter_specs(run, ordinal)
        assert {spec.creature.creature_id for spec in specs} == creature_ids
        assert {
            creature_id for creature_id, _level, _category in _enemy_rewards_for(run, ordinal)
        } == {spec.creature.creature_id for spec in specs if spec.required_for_victory}

    anchors = altos_bastilha_encounter_specs(5, "stable", 1)[1:]
    assert len(anchors) == 2
    assert all(spec.passive and spec.initially_inactive for spec in anchors)
    assert all(not spec.required_for_victory for spec in anchors)
    assert all(spec.stat_multipliers.hp == D("0.20") for spec in anchors)
    assert all(spec.stat_multipliers.defense == D("0.80") for spec in anchors)
    assert dict(family.completion_xp_by_difficulty) == {
        "stable": 13_280,
        "fractured": 16_270,
        "rupture": 24_240,
    }
    assert dict(family.first_clear_xp_by_difficulty) == {
        "stable": 21_248,
        "fractured": 26_032,
        "rupture": 38_784,
    }
    assert dict(family.crowns_by_difficulty) == {
        "stable": 680,
        "fractured": 1_020,
        "rupture": 1_800,
    }
    assert family.basic_material_weights == ALTOS_BASTILHA_BASIC_MATERIAL_WEIGHTS
    assert DIFFICULTIES["rupture"].reference_level == 60
    assert (
        DIFFICULTIES["rupture"].cores,
        DIFFICULTIES["rupture"].catalysts,
        DIFFICULTIES["rupture"].fragments,
    ) == (4, 4, 7)
    assert ALTOS_BASTILHA_CORE_ID == ALTOS_BASTILHA_CORE

    recipe = canonical_recipe(ALTOS_BASTILHA_RECIPE_UNLOCK)
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
        "equipment.altos.special.guarda_ordem_profunda",
        "blacksmith",
        12,
        5,
        "Épico",
        "Secundária",
        1,
    )
    assert [(row.material_id, row.quantity) for row in recipe.fixed_materials] == [
        ("material.altos.ferro_contrapeso", 7),
        ("material.altos.cinza_basalto", 3),
        ("material.tdo.catalisador_elite_v", 2),
        ("material.tdo.fragmento_aprimoramento_v", 6),
        (ALTOS_BASTILHA_CORE_ID, 1),
    ]
    assert ALTOS_BASTILHA_DISTINCTIVE_BOSS_MASTERY[ALTOS_BASTILHA_GUARDIAN] == {
        "first_victory",
        "phase:ancoragem_ativa",
        "mechanic:ponto_ancoragem_observado",
        "action:redistribuicao_forcada",
    }


def test_altos_bastilha_elites_and_guardian_use_canonical_actions_and_phases():
    bridge = _combat(3)
    assert set(bridge.enemy_actions) == {
        "golpe_parapeito",
        "travar_passagem",
        "reorientar_carga",
        "fecho_ponte",
    }
    assert bridge.enemy_actions["travar_passagem"].self_barrier_coefficient == D("1.00")
    assert bridge.enemy_actions["reorientar_carga"].effect_stat == "agility"
    assert bridge.enemy_actions["reorientar_carga"].attack_debuff == D("0.12")
    assert bridge.enemy_actions["fecho_ponte"].prepared is True
    assert bridge.enemy_actions["fecho_ponte"].coefficient == D("1.75")

    coordinator = _combat(4)
    assert set(coordinator.enemy_actions) == {
        "pulso_coordenacao",
        "ordem_prioridade",
        "redistribuir_placas",
        "sobrecarga_linha",
    }
    assert coordinator.enemy_actions["ordem_prioridade"].attack_debuff == D("0.10")
    assert coordinator.enemy_actions["redistribuir_placas"].self_barrier_coefficient == D("0.95")
    assert coordinator.enemy_actions["sobrecarga_linha"].coefficient == D("1.70")

    solo = _combat(5)
    group = _combat(5, difficulty="rupture", group_size=4)
    assert set(solo.enemy_actions) == {
        "e0_impacto_sustentacao",
        "e0_linha_carga",
        "e0_ancora_postura",
        "e0_varredura_ponte",
        "e0_redistribuicao_forcada",
    }
    assert solo.enemy_actions["e0_impacto_sustentacao"].coefficient == D("1.00")
    assert solo.enemy_actions["e0_linha_carga"].attack_debuff == D("0.10")
    anchor_action = solo.enemy_actions["e0_ancora_postura"]
    assert anchor_action.target_mode == "self"
    assert anchor_action.self_barrier_hp_fraction == D("0.08")
    assert anchor_action.cooldown == 4 and anchor_action.max_uses_per_combat == 2
    assert solo.enemy_actions["e0_varredura_ponte"].target_mode == "all_opponents"
    forced = solo.enemy_actions["e0_redistribuicao_forcada"]
    assert forced.prepared is True and forced.coefficient == D("1.80")
    assert forced.cooldown == 5 and forced.phase_ids == ("III",)
    assert [(trigger.hp_fraction_at_most, trigger.phase_id) for trigger in solo.phase_triggers] == [
        (D("0.70"), "II"),
        (D("0.35"), "III"),
    ]
    assert solo.phase_triggered_ids == set()
    solo_hp = solo.fighters["guardiao_contrapeso"].stats.hp
    group_hp = group.fighters["guardiao_contrapeso"].stats.hp
    assert solo_hp < group_hp

    guardian = solo.fighters["guardiao_contrapeso"]
    anchors = (solo.fighters["ponto_ancoragem_1"], solo.fighters["ponto_ancoragem_2"])
    assert all(
        anchor.hp == 0 and anchor.encounter_hidden and not anchor.takes_turn for anchor in anchors
    )
    assert _damage_aura_reduction(solo, "guardiao_contrapeso") == 0
    guardian.hp = guardian.stats.hp * D("0.70")
    _resolve_phase_triggers(solo)
    assert solo.phase_id == "II"
    assert {anchor.hp for anchor in anchors} == {anchor.stats.hp for anchor in anchors}
    assert _damage_aura_reduction(solo, "guardiao_contrapeso") == D("0.10")
    assert all(not anchor.encounter_hidden for anchor in anchors)
    anchors[0].hp = 0
    assert _damage_aura_reduction(solo, "guardiao_contrapeso") == D("0.05")
    guardian.hp = guardian.stats.hp * D("0.35")
    _resolve_phase_triggers(solo)
    assert solo.phase_id == "III"
    assert solo.enemy_actions["e0_ancora_postura"].phase_ids == ("I", "II")
    restored = decode(encode(solo), solo.id, solo.ruleset, solo.version)
    assert restored.phase_id == "III"
    assert ALTOS_BASTILHA_PHASE_II in restored.phase_triggered_ids
    assert ALTOS_BASTILHA_PHASE_III in restored.phase_triggered_ids
    assert restored.fighters["ponto_ancoragem_1"].hp == 0


@pytest.mark.asyncio
async def test_altos_bastilha_is_hidden_until_discovery_and_settles_on_shared_engine(
    database, monkeypatch
):
    actor = 994_701
    character_id, sessions = await _seed_final_campaign(database, actor, level=48)
    service = DungeonService(sessions, "ocaso")
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = ALTOS_REGION
        world.location = ALTOS_BASTILHA

    assert (await service.detail(actor, ALTOS_BASTILHA_FAMILY_ID)).kind == "hidden"
    blocked = await service.start_solo(actor, "stable", family_id=ALTOS_BASTILHA_FAMILY_ID)
    assert blocked is not None and blocked.reason == "gate"
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id="P28",
                title="Os Desvelados",
                status="completed",
                step=7,
                content_version="altos-1.0.1",
                progress={"completed": True},
            )
        )
    assert (await service.detail(actor, ALTOS_BASTILHA_FAMILY_ID)).kind == "hidden"
    blocked = await service.start_solo(actor, "stable", family_id=ALTOS_BASTILHA_FAMILY_ID)
    assert blocked is not None and blocked.reason == "gate"
    async with sessions.begin() as session:
        session.add(Unlock(character_id=character_id, unlock_id=ALTOS_BASTILHA_DISCOVERY_UNLOCK))

    detail = await service.detail(actor, ALTOS_BASTILHA_FAMILY_ID)
    assert detail is not None and detail.kind == "detail"
    assert dict(detail.difficulty_gates)["stable"] == "available"
    known = await service.known(actor)
    assert known is not None and any(
        row[0] == ALTOS_BASTILHA_FAMILY_ID for row in known.known_dungeons
    )

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
        active = updated.fighters[actor_key]
        updated.events.append(
            CombatEvent(
                len(updated.events),
                updated.round,
                actor_key,
                action_id,
                target=target_id,
                actor_entity_id=active.id,
            )
        )
        for fighter in updated.fighters.values():
            if fighter.side == "enemy" and fighter.required_for_victory:
                fighter.hp = D(0)
        updated.result = "victory"
        updated.version += 1
        return updated

    monkeypatch.setattr("asterion.application.dungeons.act", controlled_victory)
    current = await service.start_solo(actor, "stable", family_id=ALTOS_BASTILHA_FAMILY_ID)
    assert current is not None and current.run_id is not None
    run_id = current.run_id
    assert len(brazier_rolls) == 1

    for ordinal in range(1, 6):
        if current.kind == "brazier":
            current = await service.activate_brazier(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
        fight = await service.begin_encounter(actor, run_id, current.state_version)
        assert fight is not None and fight.kind == "combat" and fight.combat is not None
        assert fight.activity_id is not None
        assert fight.combat.configuration_snapshot["dungeon"]["ordinal"] == ordinal
        enemies = [fighter for fighter in fight.combat.fighters.values() if fighter.side == "enemy"]
        if ordinal == 1:
            assert [fighter.name for fighter in enemies] == ["Vigia de Carga"]
        if ordinal == 2:
            assert {fighter.name for fighter in enemies} == {"Vigia de Carga", "Quebra-Cabos"}
        if ordinal == 5:
            assert {fighter.name for fighter in enemies} == {
                "Guardião do Contrapeso",
                "Ponto de Ancoragem",
            }
            assert sum(fighter.required_for_victory for fighter in enemies) == 1
            anchors = [fighter for fighter in enemies if fighter.name == "Ponto de Ancoragem"]
            assert len(anchors) == 2
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
        assert run.has_brazier and run.brazier_activated
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
                    == f"{DUNGEON_FAMILIES[ALTOS_BASTILHA_FAMILY_ID].reward_prefix}{run_id.hex}",
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
        assert xp.payload["completion"] == 21_248
        assert next(row.quantity for row in components if row.kind == "crowns") == 680
        material_counts = {
            row.item_id: row.quantity for row in components if row.kind == "material"
        }
        basic_total = sum(
            material_counts.get(item_id, 0) for item_id, _ in ALTOS_BASTILHA_BASIC_MATERIAL_WEIGHTS
        )
        assert basic_total == 8
        assert material_counts["material.tdo.catalisador_elite_v"] == 2
        assert material_counts[ALTOS_BASTILHA_CORE_ID] == 1
        assert material_counts["material.tdo.fragmento_aprimoramento_v"] == 2
        assert any(row.kind == "equipment" and row.quantity == 1 for row in components)
        assert (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == ALTOS_BASTILHA_FIRST_CLEAR_PREFIX + "stable",
                )
            )
        ) is not None
        assert (
            await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character_id,
                    Achievement.achievement_id == "achievement.altos.bastilha_primeira",
                )
            )
        ) is not None
        codex_ids = set(
            (
                await session.scalars(
                    select(CodexEntry.entry_id).where(
                        CodexEntry.character_id == character_id,
                        CodexEntry.entry_id.in_(
                            (
                                "codex.altos.dungeon.bastilha_profunda",
                                "codex.altos.dungeon.protocolos_prioridade",
                                "codex.altos.dungeon.guardiao_contrapeso",
                            )
                        ),
                    )
                )
            ).all()
        )
        assert codex_ids == {
            "codex.altos.dungeon.bastilha_profunda",
            "codex.altos.dungeon.protocolos_prioridade",
            "codex.altos.dungeon.guardiao_contrapeso",
        }
        bestiary = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == ALTOS_BASTILHA_GUARDIAN,
            )
        )
        assert bestiary is not None and bestiary.stage != "dominated"
        member_seed = f"{run.seed}:member:{character_id.hex}"
        expected_recipe = (
            stable_draw(member_seed, "recipe.discovery", 10_000)
            < DIFFICULTIES["stable"].recipe_chance * 100
        )
        recipe_unlocked = await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == ALTOS_BASTILHA_RECIPE_UNLOCK,
            )
        )
        assert (recipe_unlocked is not None) is expected_recipe

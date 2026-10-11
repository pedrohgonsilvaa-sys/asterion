from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.bestiary import BestiaryRecorder
from asterion.application.dungeons import DUNGEON_FAMILIES, DungeonService, DungeonView
from asterion.application.knowledge_catalog import (
    CODEX_BY_ID,
    CODEX_FRAGMENTS,
    CREATURE_PRESENTATION,
)
from asterion.application.road import RoadService
from asterion.application.vde_missions import MATA_EXPLORE_UNLOCK, P8_ID
from asterion.bot.dungeon_ui import render_dungeons
from asterion.domain.combat import (
    _barrier_received_multiplier,
    _damage_aura_reduction,
    _resolve_phase_triggers,
)
from asterion.domain.dungeons import DIFFICULTIES, difficulty_gate, material_for_ordinal
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.professions import RECIPE_BY_ID
from asterion.domain.road import (
    CREATURE_CATALOG,
    HUNT_PROFILES,
    VDE_CREATURES,
    VDE_DUNGEON_CREATURES,
    VDE_HANGING_ROOT,
    VDE_PIT_HANGER,
    VDE_PIT_WEAVER,
    VDE_PULSING_NODE,
    VDE_VINE_SPIDER,
    creature_for,
    road_enemy_stats,
)
from asterion.domain.vde_fosso import (
    FOSSO_BASIC_MATERIALS,
    FOSSO_DISCOVERY_UNLOCK,
    FOSSO_FAMILY_ID,
    create_fosso_combat,
    fosso_encounter_specs,
    fosso_enemy_rewards,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CodexFragment,
    DungeonRun,
    DungeonRunMember,
    ExplorationAttempt,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_vde_s7_p8_integration import _seed_vde_ready

D = Decimal
FOSSO_UNLOCK = "dungeon.vde.fosso_raizes"
MATA = "Mata Suspensa"
VDE_REGION = "Vales dos Enforcados"
FOSSO_LOCATION_ID = "vde.location.fosso_das_raizes"


def _combat(ordinal: int, *, difficulty="stable", group_size=1):
    return create_fosso_combat(
        uuid4(),
        name="Heroa",
        character_class="sentinela",
        race="remanescente",
        hp=D(5000),
        level=17,
        difficulty=difficulty,
        reference_level=16,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"fosso-{ordinal}-{difficulty}-{group_size}",
        initial_group_size=group_size,
    )


@pytest.mark.parametrize(
    ("ordinal", "expected"),
    (
        (1, ("aranha_cipo",)),
        (2, ("aranha_cipo", "peregrino_enredado")),
        (3, ("tecela_fosso",)),
        (4, ("casca_errante", "fosso_no_pulsante", "fosso_no_pulsante", "fosso_no_pulsante")),
        (5, ("o_que_pende", "fosso_raiz_sustentacao", "fosso_raiz_sustentacao")),
    ),
)
def test_fosso_encounters_use_the_canonical_roster_without_variants(ordinal, expected):
    specs = fosso_encounter_specs(ordinal, "stable", 1, 16)
    assert tuple(spec.creature.creature_id for spec in specs) == expected
    assert all(spec.variant is None for spec in specs)


def test_fosso_creatures_are_cataloged_without_expanding_world_open_vales_pool():
    expected_open_world_ids = {
        "lobo_musgoso",
        "gralha_vale",
        "peregrino_enredado",
        "aranha_cipo",
        "cervo_no",
        "no_feroz",
        "viuva_cipos",
        "sanguessuga_turfa",
        "casca_errante",
        "mariposa_breu_verde",
        "vigia_enraizado",
        "carrasco_casca",
    }
    world_open_ids = {creature.creature_id for creature in VDE_CREATURES}
    assert len(VDE_CREATURES) == 12
    assert world_open_ids == expected_open_world_ids

    dungeon_creatures = {creature.creature_id: creature for creature in VDE_DUNGEON_CREATURES}
    assert set(dungeon_creatures) == {"tecela_fosso", "o_que_pende"}
    assert world_open_ids.isdisjoint(dungeon_creatures)
    assert all(
        creature_for(creature_id) is creature
        for creature_id, creature in dungeon_creatures.items()
    )
    assert all(creature in CREATURE_CATALOG for creature in dungeon_creatures.values())
    assert all(
        not (
            {"tecela_fosso", "o_que_pende"}
            & {creature_id for creature_id, _ in profile.creature_weights}
        )
        for profile in HUNT_PROFILES.values()
    )

    mechanical_ids = {"fosso_no_pulsante", "fosso_raiz_sustentacao"}
    assert mechanical_ids.isdisjoint(creature.creature_id for creature in CREATURE_CATALOG)


def test_fosso_codex_uses_canonical_titles_and_categories():
    cordas = CODEX_BY_ID["codex.mystery.cordas_sob_a_mata"]
    assert (cordas.title, cordas.category) == ("Cordas sob a Mata", "mysteries")
    assert "codex.history.cordas_sob_a_mata" not in CODEX_BY_ID

    aquilo = CODEX_BY_ID["codex.history.aquilo_que_pende"]
    assert aquilo.title == "Aquilo que Pende"
    assert "codex.history.o_que_pende" not in CODEX_BY_ID
    assert not any(entry.title == "O Que Pende" for entry in CODEX_BY_ID.values())
    assert creature_for("o_que_pende").name == "O Que Pende"
    assert CREATURE_PRESENTATION["o_que_pende"].habitats == ("vde.location.fosso_das_raizes",)
    assert "codex.fragment.fosso.o_que_pende" not in CODEX_FRAGMENTS
    assert (
        CODEX_FRAGMENTS["codex.fragment.fosso.aquilo_que_pende"].title
        == "Aquilo que Pende"
    )
    assert (
        CODEX_FRAGMENTS["codex.fragment.fosso.cordas_sob_a_mata"].title
        == "Cordas sob a Mata"
    )


def test_fosso_family_and_grade_ii_reward_configuration_are_canonical():
    family = DUNGEON_FAMILIES[FOSSO_FAMILY_ID]
    assert (
        family.name,
        family.region_display,
        family.entry_location,
        family.range_label,
        family.minimum_level,
        family.reference_level,
        family.encounter_count,
    ) == ("Fosso das Raízes", VDE_REGION, MATA, "Nv.14–17", 14, 16, 5)
    assert family.basic_material_pool == FOSSO_BASIC_MATERIALS
    assert family.catalyst_material == "material.vde.catalisador_elite_ii"
    assert family.fragment_material == "material.vde.fragmento_aprimoramento_ii"
    assert family.core_id == "material.vde.nucleo_fosso_raizes"
    assert family.recipe_unlock == "recipe.vde.fosso.relicario_cordas_mortas"
    assert family.recipe_name == "Relicário das Cordas Mortas"
    assert family.known_path_unlock == FOSSO_DISCOVERY_UNLOCK
    assert all("material.tdo." not in material for material in family.basic_material_pool)


def test_fosso_dungeon_rewards_reuse_global_quantities_and_recipe_costs():
    assert DIFFICULTIES["stable"].basic_materials == 8
    assert DIFFICULTIES["stable"].catalysts == 2
    assert DIFFICULTIES["stable"].cores == 1
    assert DIFFICULTIES["stable"].fragments == 2
    assert DIFFICULTIES["fractured"].basic_materials == 11
    assert DIFFICULTIES["fractured"].catalysts == 3
    assert DIFFICULTIES["fractured"].cores == 2
    assert DIFFICULTIES["fractured"].fragments == 4
    assert DIFFICULTIES["rupture"].basic_materials == 14
    assert DIFFICULTIES["rupture"].catalysts == 4
    assert DIFFICULTIES["rupture"].cores == 4
    assert DIFFICULTIES["rupture"].fragments == 7

    recipe = RECIPE_BY_ID["recipe.vde.fosso.relicario_cordas_mortas"]
    assert (recipe.profession_id, recipe.required_level, recipe.grade, recipe.rarity) == (
        "jeweler",
        5,
        2,
        "Raro",
    )
    assert (recipe.output_slot, recipe.sw, recipe.fixed_crown_cost) == ("Artefato", 2, None)
    assert tuple((row.material_id, row.quantity) for row in recipe.fixed_materials) == (
        ("material.vde.ferro_enredado", 10),
        ("material.vde.resina_enredada", 6),
        ("material.vde.fragmento_aprimoramento_ii", 8),
        ("material.vde.nucleo_fosso_raizes", 1),
    )

    draws = tuple(
        material_for_ordinal("same-run-member-seed", ordinal, FOSSO_BASIC_MATERIALS)
        for ordinal in range(DIFFICULTIES["stable"].basic_materials)
    )
    assert set(draws) <= set(FOSSO_BASIC_MATERIALS)
    assert draws == tuple(
        material_for_ordinal("same-run-member-seed", ordinal, FOSSO_BASIC_MATERIALS)
        for ordinal in range(DIFFICULTIES["stable"].basic_materials)
    )


def test_fosso_gates_and_recipe_chances_follow_global_dungeon_rules():
    family = DUNGEON_FAMILIES[FOSSO_FAMILY_ID]
    assert difficulty_gate(
        level=13,
        discovered=True,
        stable_first_clear=False,
        fractured_first_clear=False,
        minimum_level=family.minimum_level,
    ) == {"stable": "level", "fractured": "level", "rupture": "level"}
    assert difficulty_gate(
        level=14,
        discovered=True,
        stable_first_clear=False,
        fractured_first_clear=False,
        minimum_level=family.minimum_level,
    ) == {"stable": "available", "fractured": "first_stable", "rupture": "level"}
    assert difficulty_gate(
        level=60,
        discovered=True,
        stable_first_clear=True,
        fractured_first_clear=True,
        minimum_level=family.minimum_level,
    ) == {"stable": "available", "fractured": "available", "rupture": "available"}
    assert tuple(DIFFICULTIES[key].recipe_chance for key in ("stable", "fractured", "rupture")) == (
        8,
        15,
        25,
    )


def test_tecela_kit_is_exact_and_has_no_hard_cc():
    combat = _combat(3)
    assert combat.fighters["enemy"].name == VDE_PIT_WEAVER.name
    expected = {
        "picada_profunda": (D("0.85"), 2, "poison", 1),
        "fio_arrasto": (D("0.80"), 3, None, 0),
        "casulo_breve": (D(0), 4, None, 0),
        "queda_tecela": (D("1.65"), 4, None, 0),
    }
    for action_id, (coefficient, cooldown, dot, stacks) in expected.items():
        action = combat.enemy_actions[action_id]
        actual = (
            action.coefficient,
            action.cooldown,
            action.native_dot_kind,
            action.native_dot_stacks,
        )
        assert actual == (
            coefficient,
            cooldown,
            dot,
            stacks,
        )
        assert not any(
            effect.hard_cc for effect in (*action.self_effects, *action.target_effects)
        )
    assert combat.enemy_actions["fio_arrasto"].effect_stat == "agility"
    assert combat.enemy_actions["fio_arrasto"].attack_debuff == D("0.15")
    assert combat.enemy_actions["fio_arrasto"].duration == 2
    assert combat.enemy_actions["casulo_breve"].self_barrier_coefficient == D("0.75")
    assert combat.enemy_actions["queda_tecela"].prepared is True


def test_pulsating_nodes_scale_and_barrier_received_aura_tracks_alive_nodes():
    combat = _combat(4)
    bark = combat.fighters["bark"]
    nodes = tuple(combat.fighters[f"node_{index}"] for index in range(1, 4))
    reference = road_enemy_stats(VDE_PULSING_NODE, 16)
    assert tuple(node.hp for node in nodes) == (reference.hp * D("0.20"),) * 3
    assert tuple(node.stats.defense for node in nodes) == (
        reference.defense * (D("0.80") / D("0.90")),
    ) * 3
    assert all(not node.takes_turn and not node.required_for_victory for node in nodes)
    expected = (D("1.00"), D("1.10"), D("1.20"), D("1.30"))
    for alive_count, multiplier in enumerate(expected):
        state = deepcopy(combat)
        state_nodes = tuple(state.fighters[f"node_{index}"] for index in range(1, 4))
        for node in state_nodes[: 3 - alive_count]:
            node.hp = 0
        assert _barrier_received_multiplier(state, "bark") == multiplier
    assert fosso_enemy_rewards(4) == (("casca_errante", 16, "uncommon"),)
    mechanical_ids = {"fosso_no_pulsante", "fosso_raiz_sustentacao"}
    assert mechanical_ids.isdisjoint(creature.creature_id for creature in CREATURE_CATALOG)
    assert all(
        row[0] not in mechanical_ids
        for ordinal in range(1, 6)
        for row in fosso_enemy_rewards(ordinal)
    )
    assert bark.hp > 0


def test_que_pende_has_exact_actions_and_group_snapshot_scaling():
    solo = _combat(5)
    boss = solo.fighters["enemy"]
    assert boss.name == VDE_PIT_HANGER.name
    assert boss.level == 17
    actions = solo.enemy_actions
    expected = {
        "garra_suspensa": (D("1.00"), None),
        "laco_fosso": (D("0.90"), 3),
        "seiva_escura": (D("0.80"), 2),
        "varredura_cordas": (D("0.80"), 3),
        "despencar": (D("1.75"), 4),
    }
    actual = {
        key: (actions[f"e0_{key}"].coefficient, actions[f"e0_{key}"].cooldown)
        for key in expected
    }
    assert actual == expected
    assert actions["e0_laco_fosso"].effect_stat == "agility"
    assert actions["e0_laco_fosso"].attack_debuff == D("0.12")
    assert actions["e0_laco_fosso"].duration == 2
    assert actions["e0_seiva_escura"].native_dot_kind == "poison"
    assert actions["e0_seiva_escura"].native_dot_stacks == 1
    assert actions["e0_varredura_cordas"].target_mode == "all_opponents"
    assert actions["e0_despencar"].prepared is True
    assert actions["e0_despencar"].phase_ids == ("III",)

    size_multipliers = (
        (D(1), D(1)),
        (D("1.78"), D("1.07")),
        (D("2.56"), D("1.14")),
        (D("3.34"), D("1.21")),
    )
    for size, (hp_multiplier, attack_multiplier) in enumerate(size_multipliers, start=1):
        combat = _combat(5, group_size=size)
        scaled = combat.fighters["enemy"]
        base = road_enemy_stats(VDE_PIT_HANGER, 17)
        difficulty = DIFFICULTIES["stable"]
        assert scaled.stats.hp == (
            base.hp
            * (D(3) / D("2.20") * difficulty.boss_hp_multiplier * hp_multiplier)
        )
        assert scaled.stats.attack == (
            base.attack * (difficulty.boss_attack_multiplier * attack_multiplier)
        )
        assert scaled.stats.defense == base.defense
        assert scaled.stats.agility == base.agility
        assert combat.configuration_snapshot["dungeon"]["initial_group_size"] == size


def test_que_pende_roots_are_optional_and_fixed_reduction_persists_through_phase_three():
    combat = _combat(5, group_size=2)
    boss = combat.fighters["enemy"]
    roots = (combat.fighters["root_1"], combat.fighters["root_2"])
    common = road_enemy_stats(VDE_HANGING_ROOT, 17)
    assert all(root.stats.hp == common.hp * D("0.25") for root in roots)
    assert all(not root.takes_turn and not root.required_for_victory for root in roots)
    assert all(root.stats.attack == 0 for root in roots)
    assert _damage_aura_reduction(combat, "enemy") == 0

    boss.hp = boss.stats.hp * D("0.70")
    _resolve_phase_triggers(combat)
    assert combat.phase_id == "II"
    assert all(root.hp == root.stats.hp for root in roots)
    assert _damage_aura_reduction(combat, "enemy") == D("0.05")
    roots[0].hp = 0
    assert _damage_aura_reduction(combat, "enemy") == D("0.05")

    boss.hp = boss.stats.hp * D("0.35")
    surviving_hp = roots[1].hp
    _resolve_phase_triggers(combat)
    assert combat.phase_id == "III"
    assert roots[0].hp == 0 and roots[1].hp == surviving_hp
    assert combat.enemy_actions["e0_despencar"].phase_ids == ("III",)
    assert _damage_aura_reduction(combat, "enemy") == D("0.05")
    _resolve_phase_triggers(combat)
    assert roots[0].hp == 0 and roots[1].hp == surviving_hp

    roots[1].hp = 0
    assert _damage_aura_reduction(combat, "enemy") == 0
    restored = decode(encode(combat), combat.id, combat.ruleset, combat.version)
    assert restored.damage_auras == combat.damage_auras
    assert restored.phase_triggered_ids == combat.phase_triggered_ids
    assert {key: restored.fighters[key].hp for key in ("root_1", "root_2")} == {
        key: combat.fighters[key].hp for key in ("root_1", "root_2")
    }


def test_old_combat_aura_snapshot_decodes_with_neutral_defaults():
    combat = _combat(5)
    payload = encode(combat)
    payload["damage_auras"] = [
        {
            key: value
            for key, value in aura.items()
            if key not in {"reduction_mode", "barrier_received_per_source"}
        }
        for aura in payload.get("damage_auras", [])
    ]
    restored = decode(payload, combat.id, combat.ruleset, combat.version)
    assert all(aura.reduction_mode == "per_source" for aura in restored.damage_auras)
    assert all(aura.barrier_received_per_source == 0 for aura in restored.damage_auras)


def test_known_dungeon_list_displays_the_vde_fosso_and_family_callback():
    view = DungeonView(
        kind="known",
        character_id=uuid4(),
        character_name="Heroa",
        level=17,
        location=MATA,
        hp=D(1000),
        max_hp=D(1000),
        vigor=100,
        max_vigor=100,
        known_dungeons=((FOSSO_FAMILY_ID, "Fosso das Raízes", "Nv.14–17", MATA, VDE_REGION),),
    )
    screen = render_dungeons(view)
    assert "Vales dos Enforcados · Mata Suspensa" in screen.text
    assert screen.keyboard.inline_keyboard[0][0].callback_data == "dungeon:fosso"


@pytest.mark.asyncio
async def test_fosso_discovery_materializes_only_the_canonical_unlock_once(database, monkeypatch):
    import asterion.application.road as road_module

    actor = 881101
    character_id, sessions = await _seed_vde_ready(database, actor, level=14, round_ready=False)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = VDE_REGION
        world.location = MATA
        session.add_all(
            (
                Quest(
                    character_id=character_id,
                    quest_id=P8_ID,
                    title="Entre Galhos Suspensos",
                    status="completed",
                    step=7,
                    content_version="vales-1.0.4",
                    progress={"completed": True},
                ),
                LocationDiscovery(
                    character_id=character_id,
                    location_id="vde.location.mata_suspensa",
                ),
                Unlock(character_id=character_id, unlock_id=MATA_EXPLORE_UNLOCK),
            )
        )

    dungeon_service = DungeonService(sessions, "ocaso")
    hidden = await dungeon_service.known(actor)
    assert hidden is not None and hidden.kind == "empty"
    detail = await dungeon_service.detail(actor, FOSSO_FAMILY_ID)
    assert detail is not None and detail.kind == "hidden"

    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: (
            "great_discovery",
            "explore.vde.mata.entrada_fosso_raizes",
            "Entrada encontrada.",
        ),
    )
    road = RoadService(sessions, "ocaso")
    result = await road.explore(actor)
    assert result is not None and result.attempt_id is not None
    await road.acknowledge_result(actor, result.attempt_id)
    await road.acknowledge_result(actor, result.attempt_id)

    async with sessions() as session:
        unlocks = await session.scalar(
            select(func.count(Unlock.id)).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == FOSSO_UNLOCK,
            )
        )
        assert unlocks == 1
        attempt = await session.get(ExplorationAttempt, result.attempt_id)
        assert attempt is not None and attempt.result_acknowledged is True
        unique_reward = await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"explore:{result.attempt_id}",
            )
        )
        assert unique_reward == 1
        xp_components = (
            await session.scalars(
                select(RewardComponent).join(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"explore:{result.attempt_id}",
                    RewardComponent.kind == "xp",
                )
            )
        ).all()
        assert sum(component.quantity for component in xp_components) == 1832
        noncanonical = await session.scalar(
            select(func.count(Unlock.id)).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "known_path.vde.fosso_raizes",
            )
        )
        assert noncanonical == 0

    known = await dungeon_service.known(actor)
    assert known is not None and known.kind == "known"
    assert known.known_dungeons == (
        (FOSSO_FAMILY_ID, "Fosso das Raízes", "Nv.14–17", MATA, VDE_REGION),
    )
    detail = await dungeon_service.detail(actor, FOSSO_FAMILY_ID)
    assert detail is not None and dict(detail.difficulty_gates)["stable"] == "available"
    run = await dungeon_service.start_solo(actor, "stable", family_id=FOSSO_FAMILY_ID)
    assert run is not None and run.kind == "ready" and run.run_id is not None
    first = await dungeon_service.begin_encounter(actor, run.run_id, run.state_version)
    assert first is not None and first.kind == "combat"
    assert first.combat.fighters["enemy"].name == VDE_VINE_SPIDER.name
    resumed = await dungeon_service.resume(actor)
    assert resumed is not None and resumed.run_id == run.run_id
    assert resumed.combat is not None and resumed.combat.id == first.combat.id


@pytest.mark.asyncio
async def test_fosso_minimum_level_is_enforced_without_materializing_a_run(database):
    actor = 881102
    character_id, sessions = await _seed_vde_ready(database, actor, level=13, round_ready=False)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = VDE_REGION
        world.location = MATA
        session.add(Unlock(character_id=character_id, unlock_id=FOSSO_UNLOCK))
    service = DungeonService(sessions, "ocaso")
    view = await service.start_solo(actor, "stable", family_id=FOSSO_FAMILY_ID)
    assert view is not None and view.reason == "level"
    async with sessions() as session:
        assert await session.scalar(select(DungeonRun.id)) is None
        assert await session.scalar(select(DungeonRunMember.run_id)) is None


@pytest.mark.asyncio
async def test_fosso_codex_progression_persists_canonical_entries(database):
    actor = 881104
    character_id, sessions = await _seed_vde_ready(database, actor, level=17, round_ready=False)
    service = DungeonService(sessions, "ocaso")
    async with sessions.begin() as session:
        await service._ensure_codex_for_encounter(
            session, character_id, 2, family_id=FOSSO_FAMILY_ID
        )
        await service._ensure_codex_for_encounter(
            session, character_id, 5, family_id=FOSSO_FAMILY_ID
        )

    async with sessions() as session:
        entry_ids = set(
            (
                await session.scalars(
                    select(CodexEntry.entry_id).where(CodexEntry.character_id == character_id)
                )
            ).all()
        )
        fragment_ids = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id
                    )
                )
            ).all()
        )
    assert "codex.mystery.cordas_sob_a_mata" in entry_ids
    assert "codex.history.aquilo_que_pende" in entry_ids
    assert "codex.history.cordas_sob_a_mata" not in entry_ids
    assert "codex.history.o_que_pende" not in entry_ids
    assert "codex.fragment.fosso.cordas_sob_a_mata" in fragment_ids
    assert "codex.fragment.fosso.aquilo_que_pende" in fragment_ids


@pytest.mark.asyncio
async def test_que_pende_first_victory_milestone_is_876_xp_and_idempotent(database):
    actor = 881103
    character_id, sessions = await _seed_vde_ready(database, actor, level=17, round_ready=False)
    recorder = BestiaryRecorder()
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        before = character.xp
        await recorder.record(
            session,
            character_id,
            "o_que_pende",
            victory=True,
            observation_category="boss",
        )
        await recorder.record(
            session,
            character_id,
            "o_que_pende",
            victory=True,
            observation_category="boss",
        )

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and character.xp == before + 876
        events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id
                    == f"bestiary:first_victory:{character_id}:o_que_pende",
                )
            )
        ).all()
        assert len(events) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == events[0].id,
                    RewardComponent.kind == "bestiary_first_victory_xp",
                )
            )
        ).all()
        assert [row.quantity for row in components] == [876]

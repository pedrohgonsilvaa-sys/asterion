from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.bestiary import BestiaryRecorder
from asterion.application.dungeons import DUNGEON_FAMILIES, DungeonService, DungeonView
from asterion.application.knowledge_catalog import CODEX_BY_ID, CODEX_FRAGMENTS
from asterion.bot.dungeon_ui import render_dungeons
from asterion.domain.combat import (
    _damage_aura_reduction,
    _enemy_action,
    _fighter_stat,
    _resolve_phase_triggers,
    action_target_ids,
)
from asterion.domain.dungeons import DIFFICULTIES
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.professions import RECIPE_BY_ID
from asterion.domain.road import (
    CREATURE_CATALOG,
    VDE_DUNGEON_CREATURES,
    VDE_OLD_KNOT_GUARDIAN,
    VDE_RADICULAR_SEAL,
    VDE_ROOT_CONTAINMENT,
    VDE_ROOTED_PRELATE,
    VDE_ROOTED_WATCHER,
    VDE_TANGLED_CUSTODIAN,
    creature_for,
    road_enemy_stats,
)
from asterion.domain.vde_santuario import (
    SANCTUARY_BASIC_MATERIALS,
    SANCTUARY_DISCOVERY_UNLOCK,
    SANCTUARY_FAMILY_ID,
    create_sanctuary_combat,
    sanctuary_encounter_specs,
    sanctuary_enemy_rewards,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CodexEntry,
    CodexFragment,
    DungeonRun,
    DungeonRunMember,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_vde_s7_p8_integration import _seed_vde_ready

D = Decimal
CLAUSTRO = "Claustro das Raízes"
VDE_REGION = "Vales dos Enforcados"
GUARDIAN_ID = "guardiao_no_antigo"
ROOT_MECHANIC_ID = "vde_root_containment_mechanic"
SEAL_MECHANIC_ID = "vde_radicular_seal_mechanic"


def _combat(ordinal: int, *, difficulty="stable", group_size=1):
    return create_sanctuary_combat(
        uuid4(),
        name="Heroa",
        character_class="sentinela",
        race="remanescente",
        hp=D(5000),
        level=20,
        difficulty=difficulty,
        reference_level=19,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"sanctuary-{ordinal}-{difficulty}-{group_size}",
        initial_group_size=group_size,
    )


@pytest.mark.parametrize(
    ("ordinal", "expected"),
    (
        (1, ("vigia_enraizado",)),
        (2, ("vigia_enraizado", "casca_errante")),
        (3, ("custodio_enredado",)),
        (
            4,
            (
                "prelado_enraizado",
                ROOT_MECHANIC_ID,
                ROOT_MECHANIC_ID,
                ROOT_MECHANIC_ID,
                ROOT_MECHANIC_ID,
            ),
        ),
        (5, (GUARDIAN_ID, SEAL_MECHANIC_ID, SEAL_MECHANIC_ID, SEAL_MECHANIC_ID)),
    ),
)
def test_sanctuary_encounters_use_the_canonical_roster_without_variants(ordinal, expected):
    specs = sanctuary_encounter_specs(ordinal, "stable", 1, 19)
    assert tuple(spec.creature.creature_id for spec in specs) == expected
    assert all(spec.variant is None for spec in specs)


def test_sanctuary_catalog_and_reward_roster_keep_mechanics_out_of_bestiary():
    catalog_ids = {creature.creature_id for creature in CREATURE_CATALOG}
    dungeon_ids = {creature.creature_id for creature in VDE_DUNGEON_CREATURES}
    assert {
        "custodio_enredado",
        "prelado_enraizado",
        GUARDIAN_ID,
    } <= dungeon_ids
    assert {ROOT_MECHANIC_ID, SEAL_MECHANIC_ID}.isdisjoint(catalog_ids)
    assert creature_for("custodio_enredado") is VDE_TANGLED_CUSTODIAN
    assert creature_for("prelado_enraizado") is VDE_ROOTED_PRELATE
    assert creature_for(GUARDIAN_ID) is VDE_OLD_KNOT_GUARDIAN
    assert creature_for("vigia_enraizado") is VDE_ROOTED_WATCHER
    assert sanctuary_enemy_rewards(4) == (("prelado_enraizado", 19, "elite"),)
    assert sanctuary_enemy_rewards(5) == ((GUARDIAN_ID, 20, "boss"),)
    assert all(
        all(
            row[0] not in {ROOT_MECHANIC_ID, SEAL_MECHANIC_ID}
            for row in sanctuary_enemy_rewards(i)
        )
        for i in range(1, 6)
    )


def test_custodian_kit_matches_the_regional_source():
    combat = _combat(3)
    expected = {
        "impacto_guarda": (D("1.00"), None),
        "egide_tomada": (D(0), 3),
        "marca_constritiva": (D("0.90"), 3),
        "peso_no": (D("1.70"), 4),
    }
    assert combat.fighters["enemy"].name == VDE_TANGLED_CUSTODIAN.name
    assert {
        action: (combat.enemy_actions[action].coefficient, combat.enemy_actions[action].cooldown)
        for action in expected
    } == expected
    assert combat.enemy_actions["egide_tomada"].self_barrier_coefficient == D("0.90")
    assert combat.enemy_actions["egide_tomada"].self_barrier_duration == 2
    assert combat.enemy_actions["marca_constritiva"].attack_debuff == D("0.12")
    assert combat.enemy_actions["marca_constritiva"].duration == 2
    assert combat.enemy_actions["marca_constritiva"].effect_stat == "defense"
    assert combat.enemy_actions["peso_no"].prepared is True
    assert not any(
        effect.hard_cc
        for action in combat.enemy_actions.values()
        for effect in (*action.self_effects, *action.target_effects)
    )


def test_prelate_roots_restore_one_at_half_hp_and_scale_its_defense_aura():
    combat = _combat(4)
    prelate = combat.fighters["prelate"]
    roots = tuple(combat.fighters[f"root_{i}"] for i in range(1, 5))
    reference = road_enemy_stats(VDE_ROOT_CONTAINMENT, 19)
    assert all(root.hp == reference.hp * D("0.20") for root in roots)
    assert all(root.stats.attack == 0 and not root.takes_turn for root in roots)
    assert all(not root.required_for_victory for root in roots)
    target_ids = set(action_target_ids(combat, "attack", actor_key="player"))
    assert all(root.id in target_ids for root in roots)
    assert _fighter_stat(combat, "prelate", "defense") == (
        road_enemy_stats(VDE_ROOTED_PRELATE, 19).defense * D("1.20")
    )
    action = combat.enemy_actions["e0_restabelecer_raiz"]
    assert action.max_uses_per_combat == 1
    assert action.revive_fighter_keys == ("root_1", "root_2", "root_3", "root_4")
    assert action.revive_hp_fraction == D("0.50")
    assert action.requires_defeated_fighter_keys == ("root_1", "root_2", "root_3", "root_4")

    roots[0].hp = 0
    roots[1].hp = 0
    revived_key = next(
        key
        for key in sorted(
            action.revive_fighter_keys, key=lambda key: (combat.fighters[key].id, key)
        )
        if combat.fighters[key].hp <= 0
    )
    combat.fighters[revived_key].hp = (
        combat.fighters[revived_key].stats.hp * action.revive_hp_fraction
    )
    assert sum(root.hp > 0 for root in roots) == 3
    assert prelate.stats.defense == road_enemy_stats(VDE_ROOTED_PRELATE, 19).defense
    assert combat.stat_auras[0].multiplier_per_source == D("0.05")


def test_guardian_phase_targets_scaling_reduction_and_retry_state_are_persisted():
    combat = _combat(5, group_size=3)
    guardian = combat.fighters["guardian"]
    seals = tuple(combat.fighters[f"seal_{i}"] for i in range(1, 4))
    reference = road_enemy_stats(VDE_OLD_KNOT_GUARDIAN, 20)
    assert guardian.stats.hp == reference.hp * (
        D(3) / D("2.20") * DIFFICULTIES["stable"].boss_hp_multiplier * D("2.56")
    )
    assert guardian.stats.attack == reference.attack * D("1.14")
    assert guardian.stats.defense == reference.defense
    assert guardian.stats.agility == reference.agility
    common_seal = road_enemy_stats(VDE_RADICULAR_SEAL, 20)
    assert all(seal.stats.hp == common_seal.hp * D("0.25") for seal in seals)
    assert all(seal.stats.attack == 0 and seal.hp == 0 for seal in seals)
    assert all(not seal.takes_turn and not seal.required_for_victory for seal in seals)
    assert _damage_aura_reduction(combat, "guardian") == 0

    actions = combat.enemy_actions
    assert actions["e0_golpe_no"].coefficient == D("1.00")
    assert actions["e0_marca_de_constricao"].coefficient == D("0.90")
    assert actions["e0_marca_de_constricao"].attack_debuff == D("0.10")
    assert actions["e0_marca_de_constricao"].duration == 2
    assert actions["e0_egide_raizes"].self_barrier_hp_fraction == D("0.08")
    assert actions["e0_egide_raizes"].cooldown == 4
    assert actions["e0_egide_raizes"].self_barrier_duration == 2
    assert actions["e0_egide_raizes"].max_uses_per_combat == 2
    assert actions["e0_egide_raizes"].phase_ids == ()
    assert actions["e0_varredura_enredada"].coefficient == D("0.85")
    assert actions["e0_varredura_enredada"].target_mode == "all_opponents"
    assert actions["e0_varredura_enredada"].phase_ids == ()
    assert actions["e0_fechamento_no"].coefficient == D("1.80")
    assert actions["e0_fechamento_no"].prepared is True
    assert actions["e0_fechamento_no"].phase_ids == ("III",)

    combat.ai_priorities["guardian"] = ("e0_egide_raizes",)
    assert _enemy_action(combat, "guardian") == "e0_egide_raizes"
    combat.ai_priorities["guardian"] = ("e0_varredura_enredada",)
    assert _enemy_action(combat, "guardian") == "e0_varredura_enredada"

    guardian.hp = guardian.stats.hp * D("0.70")
    _resolve_phase_triggers(combat)
    assert combat.phase_id == "II"
    assert all(seal.hp == seal.stats.hp for seal in seals)
    target_ids = set(action_target_ids(combat, "attack", actor_key="player"))
    assert all(seal.id in target_ids for seal in seals)
    assert _damage_aura_reduction(combat, "guardian") == D("0.12")
    destroyed_hp = seals[0].stats.hp
    seals[0].hp = 0
    assert _damage_aura_reduction(combat, "guardian") == D("0.08")

    guardian.hp = guardian.stats.hp * D("0.35")
    surviving_hp = seals[1].hp
    _resolve_phase_triggers(combat)
    assert combat.phase_id == "III"
    assert seals[0].hp == destroyed_hp * D("0.50")
    assert seals[1].hp == surviving_hp
    assert seals[2].hp == seals[2].stats.hp
    assert _damage_aura_reduction(combat, "guardian") == D("0.12")
    assert actions["e0_egide_raizes"].phase_ids == ()
    assert actions["e0_varredura_enredada"].phase_ids == ()
    assert actions["e0_fechamento_no"].phase_ids == ("III",)

    restored = decode(encode(combat), combat.id, combat.ruleset, combat.version)
    assert restored.phase_id == "III"
    assert restored.phase_triggered_ids == combat.phase_triggered_ids
    assert {key: restored.fighters[key].hp for key in ("seal_1", "seal_2", "seal_3")} == {
        key: combat.fighters[key].hp for key in ("seal_1", "seal_2", "seal_3")
    }


@pytest.mark.parametrize(
    ("group_size", "group_hp", "group_attack"),
    (
        (1, D("1.00"), D("1.00")),
        (2, D("1.78"), D("1.07")),
        (3, D("2.56"), D("1.14")),
        (4, D("3.34"), D("1.21")),
    ),
)
def test_guardian_dungeon_scaling_is_frozen_for_each_roster_size(
    group_size, group_hp, group_attack
):
    combat = _combat(5, group_size=group_size)
    guardian = combat.fighters["guardian"]
    reference = road_enemy_stats(VDE_OLD_KNOT_GUARDIAN, 20)
    stable = DIFFICULTIES["stable"]
    expected_hp = reference.hp * (
        D(3) / D("2.20") * stable.boss_hp_multiplier * group_hp
    )
    expected_attack = reference.attack * stable.boss_attack_multiplier * group_attack
    assert abs(guardian.stats.hp - expected_hp) < D("1e-20")
    assert abs(guardian.stats.attack - expected_attack) < D("1e-20")
    assert guardian.stats.defense == reference.defense
    assert guardian.stats.agility == reference.agility


def test_sanctuary_family_codex_and_recipe_are_canonical():
    family = DUNGEON_FAMILIES[SANCTUARY_FAMILY_ID]
    assert (
        family.name,
        family.region_display,
        family.entry_location,
        family.minimum_level,
        family.reference_level,
        family.encounter_count,
    ) == ("Santuário do Nó Antigo", VDE_REGION, CLAUSTRO, 18, 19, 5)
    assert family.discovery_unlock == SANCTUARY_DISCOVERY_UNLOCK
    assert family.known_path_unlock == SANCTUARY_DISCOVERY_UNLOCK
    assert family.core_id == "material.vde.nucleo_no_antigo"
    assert family.recipe_unlock == "recipe.vde.santuario.guarda_no_antigo"
    assert family.basic_material_pool == SANCTUARY_BASIC_MATERIALS

    recipe = RECIPE_BY_ID[family.recipe_unlock]
    assert (recipe.profession_id, recipe.required_level, recipe.output_slot) == (
        "blacksmith",
        10,
        "Secundária",
    )
    assert (recipe.grade, recipe.rarity, recipe.sw, recipe.fixed_crown_cost) == (
        2,
        "Épico",
        1,
        None,
    )
    assert tuple((row.material_id, row.quantity) for row in recipe.fixed_materials) == (
        ("material.vde.ferro_enredado", 7),
        ("material.vde.resina_enredada", 3),
        ("material.vde.catalisador_elite_ii", 2),
        ("material.vde.fragmento_aprimoramento_ii", 6),
        ("material.vde.nucleo_no_antigo", 1),
    )

    assert CODEX_BY_ID["codex.history.camara_das_quatro_raizes"].title == "Câmara das Quatro Raízes"
    assert CODEX_BY_ID["codex.history.protocolos_sepultados"].title == "Protocolos Sepultados"
    assert CODEX_BY_ID["codex.history.selos_radicular"].title == "Selos Radiculares"
    assert CODEX_BY_ID["codex.history.guardiao_no_antigo"].title == "Guardião do Nó Antigo"
    assert CODEX_FRAGMENTS["codex.fragment.sanctuary.ancient_knot"].title == "O Nó Antigo"
    assert (
        CODEX_FRAGMENTS["codex.fragment.sanctuary.interlinked_structures"].title
        == "Estruturas Interligadas"
    )


def test_sanctuary_is_player_visible_with_a_live_callback():
    view = DungeonView(
        kind="known",
        character_id=uuid4(),
        character_name="Heroa",
        level=18,
        location=CLAUSTRO,
        hp=D(1000),
        max_hp=D(1000),
        vigor=100,
        max_vigor=100,
        known_dungeons=(
            (SANCTUARY_FAMILY_ID, "Santuário do Nó Antigo", "Nv.18–20", CLAUSTRO, VDE_REGION),
        ),
    )
    screen = render_dungeons(view)
    assert screen.keyboard.inline_keyboard[0][0].callback_data == "dungeon:sanctuary"

    detail = DungeonView(
        kind="detail",
        character_id=uuid4(),
        character_name="Heroa",
        level=18,
        location=CLAUSTRO,
        hp=D(1000),
        max_hp=D(1000),
        vigor=100,
        max_vigor=100,
        family_id=SANCTUARY_FAMILY_ID,
        dungeon_name="Santuário do Nó Antigo",
        range_label="Nv.18–20",
        region_display=VDE_REGION,
        entry_display=CLAUSTRO,
        minimum_level=18,
        difficulty_gates=(
            ("stable", "available"),
            ("fractured", "first_stable"),
            ("rupture", "level"),
        ),
    )
    detail_screen = render_dungeons(detail)
    callbacks = {
        button.callback_data
        for row in detail_screen.keyboard.inline_keyboard
        for button in row
    }
    assert "dungeon:start:s:s" in callbacks
    assert "dungeon:group:s:s" in callbacks
    assert "dungeon:queue:s:s" in callbacks

    unknown_screen = render_dungeons(
        replace(detail, family_id="dungeon.vde.not_a_real_family")
    )
    unknown_callbacks = {
        button.callback_data
        for row in unknown_screen.keyboard.inline_keyboard
        for button in row
    }
    assert "Masmorra indisponível" in unknown_screen.text
    assert unknown_callbacks == {"dungeon:known"}


@pytest.mark.asyncio
async def test_sanctuary_level_gate_preserves_reason_and_does_not_create_a_run(database):
    actor = 991801
    character_id, sessions = await _seed_vde_ready(database, actor, level=17, round_ready=False)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = VDE_REGION
        world.location = CLAUSTRO
        session.add(Unlock(character_id=character_id, unlock_id=SANCTUARY_DISCOVERY_UNLOCK))

    service = DungeonService(sessions, "ocaso")
    view = await service.start_solo(actor, "stable", family_id=SANCTUARY_FAMILY_ID)
    assert view is not None and view.reason == "level"
    async with sessions() as session:
        assert await session.scalar(select(DungeonRun.id)) is None
        assert await session.scalar(select(DungeonRunMember.run_id)) is None


@pytest.mark.asyncio
async def test_sanctuary_solo_start_persists_and_reconnects_the_same_encounter(database):
    actor = 991802
    character_id, sessions = await _seed_vde_ready(database, actor, level=18, round_ready=False)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = VDE_REGION
        world.location = CLAUSTRO
        session.add(Unlock(character_id=character_id, unlock_id=SANCTUARY_DISCOVERY_UNLOCK))

    service = DungeonService(sessions, "ocaso")
    known = await service.known(actor)
    assert known is not None and known.kind == "known"
    assert tuple(row[0] for row in known.known_dungeons) == (SANCTUARY_FAMILY_ID,)
    detail = await service.detail(actor, SANCTUARY_FAMILY_ID)
    assert detail is not None and dict(detail.difficulty_gates)["stable"] == "available"
    run_view = await service.start_solo(actor, "stable", family_id=SANCTUARY_FAMILY_ID)
    assert run_view is not None and run_view.kind == "ready" and run_view.run_id is not None
    first = await service.begin_encounter(actor, run_view.run_id, run_view.state_version)
    assert first is not None and first.kind == "combat"
    assert first.combat.fighters["enemy"].name == VDE_ROOTED_WATCHER.name
    assert first.activity_id is not None

    resumed = await service.resume(actor)
    assert resumed is not None and resumed.kind == "combat"
    assert resumed.run_id == run_view.run_id
    assert resumed.activity_id == first.activity_id
    assert resumed.combat.id == first.combat.id

    async with sessions() as session:
        run = await session.get(DungeonRun, run_view.run_id)
        member = await session.scalar(
            select(DungeonRunMember).where(DungeonRunMember.run_id == run_view.run_id)
        )
        assert run is not None and run.dungeon_family_id == SANCTUARY_FAMILY_ID
        assert member is not None and member.vigor_reserved == DIFFICULTIES["stable"].vigor


@pytest.mark.asyncio
async def test_sanctuary_settlement_is_idempotent_and_awards_its_core_and_codex(database):
    actor = 991803
    character_id, sessions = await _seed_vde_ready(database, actor, level=18, round_ready=False)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = VDE_REGION
        world.location = CLAUSTRO
        session.add(Unlock(character_id=character_id, unlock_id=SANCTUARY_DISCOVERY_UNLOCK))

    service = DungeonService(sessions, "ocaso")
    created = await service.start_solo(actor, "stable", family_id=SANCTUARY_FAMILY_ID)
    assert created is not None and created.run_id is not None
    async with sessions.begin() as session:
        run = await session.get(DungeonRun, created.run_id)
        member = await session.scalar(
            select(DungeonRunMember).where(DungeonRunMember.run_id == created.run_id)
        )
        character = await session.get(Character, character_id)
        assert run is not None and member is not None and character is not None
        member.contribution = {"points": "1", "actions": 1}
        run.progress = {**run.progress, "internal_rewards": []}
        await service._settle_run(session, character, run, [member], {character.id: character})
        reward_lines = dict(run.progress["reward_lines_by_character"])
        await service._settle_run(session, character, run, [member], {character.id: character})
        assert dict(run.progress["reward_lines_by_character"]) == reward_lines

    async with sessions() as session:
        events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"{SANCTUARY_FAMILY_ID}.run.{created.run_id.hex}",
                )
            )
        ).all()
        assert len(events) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == events[0].id)
            )
        ).all()
        core = [
            row
            for row in components
            if row.kind == "material" and row.item_id == "material.vde.nucleo_no_antigo"
        ]
        assert [(row.quantity, row.payload["material_id"]) for row in core] == [
            (DIFFICULTIES["stable"].cores, "material.vde.nucleo_no_antigo")
        ]
        xp = sum(row.quantity for row in components if row.kind == "xp")
        assert xp > 0
        unlock = await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == SANCTUARY_FAMILY_ID + ".first_clear.stable",
            )
        )
        assert unlock is not None
        stable_feat = await session.scalar(
            select(Achievement).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.vde.o_no_antigo",
            )
        )
        assert stable_feat is not None
        guardian = await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == GUARDIAN_ID,
            )
        )
        assert guardian is None


@pytest.mark.asyncio
async def test_sanctuary_codex_entries_are_recorded_at_the_matching_encounters(database):
    actor = 991805
    character_id, sessions = await _seed_vde_ready(database, actor, level=18, round_ready=False)
    service = DungeonService(sessions, "ocaso")
    async with sessions.begin() as session:
        for ordinal in (2, 3, 4, 5):
            await service._ensure_codex_for_encounter(
                session, character_id, ordinal, family_id=SANCTUARY_FAMILY_ID
            )
        await service._record_sanctuary_codex_completion(session, character_id)
    async with sessions() as session:
        entries = set(
            (
                await session.scalars(
                    select(CodexEntry.entry_id).where(CodexEntry.character_id == character_id)
                )
            ).all()
        )
        fragments = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id
                    )
                )
            ).all()
        )
    assert "codex.history.protocolos_sepultados" in entries
    assert "codex.history.camara_das_quatro_raizes" in entries
    assert "codex.mystery.o_no_antigo" in entries
    assert "codex.mystery.estruturas_interligadas" in entries
    assert "codex.fragment.sanctuary.protocols" in fragments
    assert "codex.fragment.sanctuary.chamber" in fragments
    assert "codex.fragment.sanctuary.ancient_knot" in fragments
    assert "codex.fragment.sanctuary.interlinked_structures" in fragments


@pytest.mark.asyncio
async def test_guardian_first_victory_milestone_is_fixed_and_idempotent(database):
    actor = 991804
    character_id, sessions = await _seed_vde_ready(database, actor, level=20, round_ready=False)
    recorder = BestiaryRecorder()
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        before = character.xp
        await recorder.record(
            session,
            character_id,
            GUARDIAN_ID,
            victory=True,
            elite=False,
            observation_category="boss",
        )
        await recorder.record(
            session,
            character_id,
            GUARDIAN_ID,
            victory=True,
            elite=False,
            observation_category="boss",
        )
        assert character.xp == before + 1086
    async with sessions() as session:
        events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id
                    == f"bestiary:first_victory:{character_id}:guardiao_no_antigo",
                )
            )
        ).all()
        assert len(events) == 1


@pytest.mark.parametrize(
    ("creature_id", "distinctive_actions"),
    (
        (
            "custodio_enredado",
            (
                "action:egide_tomada",
                "action:marca_constritiva",
                "action:peso_no",
            ),
        ),
        (
            "prelado_enraizado",
            ("action:seiva_restritiva", "action:restabelecer_raiz"),
        ),
    ),
)
@pytest.mark.asyncio
async def test_sanctuary_elite_mastery_requires_distinctive_actions(
    database, creature_id, distinctive_actions
):
    recorder = BestiaryRecorder()

    generic_actor = 991820 + (creature_id == "prelado_enraizado")
    generic_character_id, generic_sessions = await _seed_vde_ready(
        database, generic_actor, level=20, round_ready=False
    )
    generic_evidence = {
        "first_victory": "victory",
        "elite": "elite",
        "elite_victory": "elite_victory",
        "mechanic:generic": "mechanic",
    }
    async with generic_sessions.begin() as session:
        session.add(
            BestiaryEntry(
                character_id=generic_character_id,
                creature_id=creature_id,
                bkp=45,
                wins=1,
            )
        )
        session.add_all(
            BestiaryEvidence(
                character_id=generic_character_id,
                creature_id=creature_id,
                evidence_id=evidence_id,
                category=category,
            )
            for evidence_id, category in generic_evidence.items()
        )
        await session.flush()
        await recorder.record(
            session,
            generic_character_id,
            creature_id,
            elite=True,
            observation_category="elite",
        )
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == generic_character_id,
                BestiaryEntry.creature_id == creature_id,
            )
        )
        assert entry is not None and entry.stage == "studied"

    specific_actor = 991822 + (creature_id == "prelado_enraizado")
    specific_character_id, specific_sessions = await _seed_vde_ready(
        database, specific_actor, level=20, round_ready=False
    )
    async with specific_sessions.begin() as session:
        session.add(
            BestiaryEntry(
                character_id=specific_character_id,
                creature_id=creature_id,
                bkp=0,
                wins=1,
            )
        )
        session.add_all(
            BestiaryEvidence(
                character_id=specific_character_id,
                creature_id=creature_id,
                evidence_id=evidence_id,
                category="behavior" if evidence_id.startswith("action:") else "victory",
            )
            for evidence_id in ("first_victory", *distinctive_actions)
        )
        await session.flush()
        await recorder.record(
            session,
            specific_character_id,
            creature_id,
            elite=True,
            observation_category="elite",
        )
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == specific_character_id,
                BestiaryEntry.creature_id == creature_id,
            )
        )
        assert entry is not None and entry.stage == "dominated"

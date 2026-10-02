from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from asterion.application.dungeons import DungeonService
from asterion.domain.combat import _enemy_action, _fighter_stat, _perform, act
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    CUSTODIO_PRIMEIRO_SELO,
    GUARD_CONDUCTOR,
    VIGIA_INTEGRO,
    road_enemy_stats,
)
from asterion.domain.tdo_galleries import (
    create_galleries_combat,
    gallery_encounter_specs,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _combat(ordinal: int, *, difficulty: str = "stable", group_size: int = 1):
    return create_galleries_combat(
        uuid4(),
        name="Heroa",
        character_class="sentinela",
        race="remanescente",
        hp=D(5000),
        level=9,
        difficulty=difficulty,
        reference_level=9,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"gallery-{ordinal}-{difficulty}-{group_size}",
        initial_group_size=group_size,
    )


@pytest.mark.parametrize(
    ("ordinal", "creature_ids"),
    (
        (1, ("vigia_rachado",)),
        (2, ("vigia_rachado", "custodio_sem_rosto")),
        (3, ("vigia_integro",)),
        (4, ("preceptor_rachado", "condutor_guarda", "condutor_guarda")),
        (5, ("custodio_primeiro_selo", "fragmento_guarda", "fragmento_guarda")),
    ),
)
def test_gallery_encounter_catalog_is_canonical_and_has_no_variants(
    ordinal, creature_ids
):
    specs = gallery_encounter_specs(ordinal, "stable", 1, 9)
    assert tuple(spec.creature.creature_id for spec in specs) == creature_ids
    assert all(spec.variant is None for spec in specs)


def test_vigia_integro_has_official_barrier_and_prepared_action():
    combat = _combat(3)
    shield = next(
        action
        for action in combat.enemy_actions.values()
        if action.id.endswith("egide_integra")
    )
    prepared = next(
        action
        for action in combat.enemy_actions.values()
        if action.id.endswith("queda_guarda")
    )
    assert combat.fighters["enemy"].name == VIGIA_INTEGRO.name
    assert shield.self_barrier_coefficient == D("0.80")
    assert shield.cooldown == 3
    assert prepared.coefficient == D("1.60")
    assert prepared.prepared is True


def test_preceptor_aura_tracks_condutors_and_restore_is_once_per_encounter():
    combat = _combat(4)
    preceptor = combat.fighters["preceptor"]
    conduits = (combat.fighters["conductor_1"], combat.fighters["conductor_2"])
    assert tuple(row.hp for row in conduits) == tuple(
        road_enemy_stats(GUARD_CONDUCTOR, 9).hp * D("0.30") for _ in conduits
    )
    assert _fighter_stat(combat, "preceptor", "defense") == (
        preceptor.stats.defense * D("1.20")
    )
    conduits[0].hp = D(0)
    assert _fighter_stat(combat, "preceptor", "defense") == (
        preceptor.stats.defense * D("1.10")
    )
    conduits[0].hp = D(0)
    conduits[1].hp = D(0)

    restore_id, restore = next(
        (key, action)
        for key, action in combat.enemy_actions.items()
        if key.endswith("restabelecer_conduto")
    )
    assert restore.max_uses_per_combat == 1
    assert restore.revive_fighter_keys == ("conductor_1", "conductor_2")
    chosen = _enemy_action(combat, "preceptor")
    assert chosen == restore_id
    assert _perform(combat, "preceptor", chosen)
    assert conduits[0].hp == conduits[0].stats.hp * D("0.50")
    assert conduits[1].hp == 0
    assert _enemy_action(combat, "preceptor") != restore_id


def test_boss_fragment_aura_phase_activation_revival_and_codec():
    base = _combat(5)
    boss = base.fighters["enemy"]
    fragments = (base.fighters["fragment_1"], base.fighters["fragment_2"])
    assert all(fragment.hp == 0 for fragment in fragments)
    assert all(not fragment.takes_turn for fragment in fragments)

    damage_by_active = []
    for active_count in range(3):
        state = deepcopy(base)
        source_fragments = (state.fighters["fragment_1"], state.fighters["fragment_2"])
        for fragment in source_fragments[:active_count]:
            fragment.hp = fragment.stats.hp
        for fragment in source_fragments[active_count:]:
            fragment.hp = D(0)
        updated = act(state, "attack", target_id="enemy")
        event = next(
            row
            for row in updated.events
            if row.actor == "player"
            and row.target == boss.id
            and row.effective_damage > 0
        )
        damage_by_active.append(event.effective_damage)
    assert damage_by_active[0] > damage_by_active[1] > damage_by_active[2]
    assert damage_by_active[1] == int(D(damage_by_active[0]) * D("0.95"))
    assert damage_by_active[2] == int(D(damage_by_active[0]) * D("0.90"))

    base.fighters["enemy"].hp = boss.stats.hp * D("0.7001")
    first_phase = act(base, "attack", target_id="enemy")
    assert all(
        fragment.hp == fragment.stats.hp
        for fragment in first_phase.fighters.values()
        if fragment.id.startswith("dungeon:fragmento_guarda")
    )
    phase_event = next(
        event for event in first_phase.mechanic_events
        if event.action == "phase:galleries.order_of_containment"
    )
    assert phase_event.internal
    shield_event = next(
        event
        for event in first_phase.events
        if event.actor == "enemy" and event.action.endswith("egide_selo")
    )
    assert shield_event.barrier_value == int(boss.stats.hp * D("0.08"))

    living_fragment = first_phase.fighters["fragment_2"]
    living_fragment.hp = living_fragment.stats.hp * D("0.70")
    first_phase.fighters["fragment_1"].hp = D(0)
    first_phase.fighters["enemy"].hp = boss.stats.hp * D("0.3501")
    last_phase = act(first_phase, "attack", target_id="enemy")
    assert last_phase.fighters["fragment_1"].hp == (
        last_phase.fighters["fragment_1"].stats.hp * D("0.50")
    )
    assert last_phase.fighters["fragment_2"].hp == living_fragment.hp
    assert (
        sum(
            event.action == "phase:galleries.last_order"
            for event in last_phase.mechanic_events
        )
        == 1
    )

    last_phase.fighters["fragment_1"].hp = D(0)
    last_phase.fighters["enemy"].hp = boss.stats.hp * D("0.20")
    repeated = act(last_phase, "attack", target_id="enemy")
    assert repeated.fighters["fragment_1"].hp == 0
    assert (
        sum(
            event.action == "phase:galleries.last_order"
            for event in repeated.mechanic_events
        )
        == 1
    )
    restored = decode(encode(repeated), repeated.id, repeated.ruleset, repeated.version)
    assert restored.phase_triggered_ids == repeated.phase_triggered_ids
    assert restored.damage_auras == repeated.damage_auras


@pytest.mark.parametrize(
    ("difficulty", "start_opportunity"),
    (("stable", 12), ("fractured", 10), ("rupture", 8)),
)
def test_gallery_boss_pressure_precedes_priority_ai_and_persists(
    difficulty, start_opportunity
):
    state = _combat(5, difficulty=difficulty)
    enemy = state.fighters["enemy"]
    enemy.opportunity = start_opportunity
    chosen = _enemy_action(state, "enemy")
    assert chosen
    assert state.pressure_stacks == 1
    enemy.opportunity = start_opportunity + 20
    _enemy_action(state, "enemy")
    assert state.pressure_stacks == 5
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.pressure_stacks == 5
    assert restored.pressure_start_opportunity == start_opportunity


def test_gallery_damage_event_uses_pressure_bonus_despite_priority_ai():
    state = _combat(5)
    enemy = state.fighters["enemy"]
    enemy.opportunity = 11
    for action_id in ("e0_egide_selo", "e0_marca_contencao", "e0_ruptura_selo"):
        enemy.cooldowns[action_id] = 99
    updated = act(state, "attack", target_id="enemy")
    enemy_event = next(
        event for event in updated.events
        if event.actor == "enemy" and event.effective_damage > 0
    )
    assert enemy_event.pressure_stacks == 1


def test_custodio_egide_aoe_prepared_action_and_pressure_profiles():
    for difficulty, expected_start in (("stable", 12), ("fractured", 10), ("rupture", 8)):
        combat = _combat(5, difficulty=difficulty, group_size=1)
        boss = combat.fighters["enemy"]
        barrier = next(
            action
            for action in combat.enemy_actions.values()
            if action.id.endswith("egide_selo")
        )
        sweep = next(
            action
            for action in combat.enemy_actions.values()
            if action.id.endswith("varredura_selo")
        )
        prepared = next(
            action
            for action in combat.enemy_actions.values()
            if action.id.endswith("ruptura_selo")
        )
        assert boss.name == CUSTODIO_PRIMEIRO_SELO.name
        assert barrier.self_barrier_hp_fraction == D("0.08")
        assert barrier.max_uses_per_combat == 2
        assert sweep.coefficient == D("0.80") and sweep.target_mode == "all_opponents"
        assert prepared.coefficient == D("1.75") and prepared.prepared is True
        assert combat.pressure_start_opportunity == expected_start
        assert combat.pressure_cap == 5
        assert not prepared.heal_coefficient


def test_contribution_thresholds_are_deterministic_and_relative():
    scores = [
        SimpleNamespace(contribution={"points": "371"}),
        SimpleNamespace(contribution={"points": "75"}),
        SimpleNamespace(contribution={"points": "35"}),
        SimpleNamespace(contribution={"points": "10"}),
        SimpleNamespace(contribution={"points": "9"}),
    ]
    factors = [DungeonService._participation_factor(row, scores) for row in scores]
    assert factors == [D(1), D(1), D("0.70"), D("0.25"), D(0)]

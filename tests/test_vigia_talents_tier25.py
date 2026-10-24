from dataclasses import replace
from decimal import ROUND_FLOOR, Decimal
from uuid import UUID, uuid4

import pytest

from asterion.domain.combat import (
    Action,
    Combat,
    Fighter,
    _finish_combat,
    _perform,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    direct_damage,
    effective_defense,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TALENTS_BY_CLASS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    _static_talent_secondary_modifier_totals,
    static_talent_secondary_modifiers,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
PERFURACAO = "talent.vigia.perfuracao_calculada"
ANTECIPACAO = "talent.vigia.antecipacao"
AQUISICAO = "talent.vigia.aquisicao_rapida"
MIRA_ESTAVEL = "talent.vigia.mira_estavel"
VIGIA_ATTACK = "attack"
VOLEIO = "class_art.vigia.voleio"
COMBAT_ID = UUID("de0a5204-ff68-4a32-8e09-02516b0fc67f")


def _internal_stats(
    talent_ids: tuple[str, ...],
    *,
    level: int = 34,
    path: str | None = None,
    equipment: EquipmentStatContribution | None = None,
) -> CombatStats:
    definitions = tuple(TALENT_DEFINITIONS[talent_id] for talent_id in talent_ids)
    return _resolve_combat_stats_with_static_talent_modifiers(
        "vigia",
        level,
        "remanescente",
        equipment,
        path,
        _static_talent_modifier_totals(definitions),
        _static_talent_secondary_modifier_totals(definitions),
    )


def _fighter(
    key: str,
    *,
    entity_id: str | None = None,
    side: str,
    character_class: str = "",
    talent_ids: tuple[str, ...] = (),
    path: str | None = None,
    attack: str = "100",
    defense: str = "0",
    evasion: str = "0",
    hp: str = "10000",
    takes_turn: bool = False,
    name: str | None = None,
) -> Fighter:
    return Fighter(
        entity_id or key,
        name or key,
        34,
        CombatStats(
            D(hp), D(attack), D(defense), D("100"), evasion=D(evasion)
        ),
        D(hp),
        race="remanescente",
        character_class=character_class,
        selected_path=path,
        talent_ids=talent_ids,
        side=side,
        takes_turn=takes_turn,
        required_for_victory=False,
    )


def _battle(
    *,
    talents: tuple[str, ...] = (),
    path: str | None = None,
    enemy_count: int = 1,
    combat_id: UUID = COMBAT_ID,
    vigia_evasion: str = "0",
    same_enemy_name: bool = False,
    pvp: bool = False,
) -> Combat:
    vigia = _fighter(
        "vigia",
        entity_id="vigia-entity",
        name="Vigia",
        side="player",
        character_class="vigia",
        talent_ids=talents,
        path=path,
        attack="200",
        defense="0",
        evasion=vigia_evasion,
        hp="10000",
        takes_turn=True,
    )
    fighters = {"player": vigia}
    for index in range(enemy_count):
        key = f"enemy-{index}"
        fighters[key] = _fighter(
            key,
            entity_id=f"enemy-entity-{index}",
            name="Same Enemy" if same_enemy_name else key,
            side="enemy",
            attack="1000",
            defense="0",
            hp="10000",
        )
    player_actions = {
        VIGIA_ATTACK: Action(VIGIA_ATTACK, "Ataque Básico", D("0.2")),
        "multi": Action("class_art.vigia.multi", "Multi", D("0.2"), hit_count=3),
        VOLEIO: Action(
            VOLEIO, "Voleio", D("0.2"), target_mode="all_opponents"
        ),
        "attack_dot": Action(
            "class_art.vigia.attack_dot",
            "Ataque com DoT",
            D("0.2"),
            target_mode="all_opponents",
            native_dot_kind="bleed",
            native_dot_stacks=1,
            duration=2,
        ),
    }
    enemy_actions = {
        "hit": Action("enemy.hit", "Golpe", D(1)),
        "multi_hit": Action("enemy.multi", "Golpes", D(1), hit_count=3),
        "aoe": Action(
            "enemy.aoe", "Área", D(1), target_mode="all_opponents"
        ),
        "dot": Action(
            "enemy.dot", "Sangramento", D(0), native_dot_kind="bleed",
            native_dot_stacks=1, duration=2
        ),
    }
    return start_combat(
        Combat(
            combat_id,
            CURRENT_COMBAT_RULESET,
            fighters,
            player_actions,
            enemy_actions,
            ("hit",),
            pvp_mode=pvp,
        )
    )


def _aim(state: Combat, target_key: str = "enemy-0") -> dict | None:
    target = state.fighters[target_key]
    source = state.fighters["player"]
    entries = target.path_state.get("aim_from", {})
    entry = entries.get(source.id) if isinstance(entries, dict) else None
    if not isinstance(entry, dict) or int(entry.get("remaining", 0)) <= 0:
        return None
    return entry


def _events(state: Combat, action: str, *, actor: str | None = None):
    return [
        event
        for event in state.events
        if event.action == action and (actor is None or event.actor == actor)
    ]


def test_perfuracao_calculada_is_two_percentage_points_and_uses_static_composition():
    talent = TALENT_DEFINITIONS[PERFURACAO]
    assert talent.level == 25 and talent.per_points == D(2)
    equipment = EquipmentStatContribution(
        per=D("1.5"),
        defense=D("14.25"),
        rune_points=(ZERO, ZERO, ZERO, ZERO, ZERO, ZERO, ZERO, ZERO),
    )
    for path in (None, "atirador", "rastreador"):
        actual = _internal_stats((PERFURACAO,), path=path, equipment=equipment)
        baseline = _internal_stats((), path=path, equipment=equipment)
        assert actual.per == baseline.per + D(2)
        assert actual.attack == baseline.attack
        assert actual.crit == baseline.crit
        assert actual.defense == baseline.defense
        assert _internal_stats((PERFURACAO,), path=path, equipment=equipment) == actual

    # The shared combat rule applies PER as percentage points and retains its
    # global 30% cap, regardless of the source of the static points.
    assert effective_defense(D(100), D(29) + talent.per_points) == D(70)


def test_perfuracao_calculada_is_publicly_valid_at_nv25():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    assert TALENT_DEFINITIONS[PERFURACAO].level == 25
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("vigia", 24, (PERFURACAO,))
    assert validate_active_talent_ids("vigia", 25, (PERFURACAO,)) == (PERFURACAO,)
    assert static_talent_secondary_modifiers("vigia", 25, (PERFURACAO,))[0] == D(2)
    assert resolve_combat_stats("vigia", 25, "remanescente", talent_ids=(PERFURACAO,))
    assert validate_active_talent_ids("vigia", 15, ("talent.vigia.mao_firme",))
    assert validate_active_talent_ids("vigia", 15, (MIRA_ESTAVEL,))
def test_perfuracao_calculada_stacks_with_atirador_mira_per_and_respects_per_cap():
    state = _battle(talents=(PERFURACAO,), path="atirador")
    actor = state.fighters["player"]
    actor.stats = replace(_internal_stats((PERFURACAO,), path="atirador"), crit=ZERO)
    target = state.fighters["enemy-0"]
    target.stats = CombatStats(D(10000), D(10), D(100), D(1))
    target.path_state["aim_from"] = {
        actor.id: {"stacks": 2, "remaining": 2, "applied_opportunity": 0}
    }

    assert _perform(state, "player", VIGIA_ATTACK, target_id="enemy-0")
    event = _events(state, VIGIA_ATTACK, actor="player")[-1]
    assert actor.stat("per") == D(2)
    assert event.path_per_bonus == D(6)  # Mira Perfeita: 3 p.p. × 2 Mira.
    assert event.calculated_damage == direct_damage(
        actor.stat("attack"), D("0.2"), target.stats.defense, actor.level,
        penetration=D(8),
    )
    assert effective_defense(D(100), actor.stat("per") + event.path_per_bonus) == D(92)


def test_antecipacao_reduces_only_first_positive_direct_component_by_seven_percent():
    state = _battle(talents=(ANTECIPACAO,))
    initial = state.fighters["player"].hp
    assert _perform(state, "enemy-0", "hit", target_id="player")
    first = _events(state, "hit", actor="enemy-0")[-1]
    reduced = first.calculated_damage
    assert reduced > 0
    assert first.effective_damage == reduced
    assert initial - state.fighters["player"].hp == reduced
    assert state.fighters["player"].path_state["vigia_antecipacao_used"] is True

    assert _perform(state, "enemy-0", "hit", target_id="player")
    second = _events(state, "hit", actor="enemy-0")[-1]
    # Compare against a same-seed non-Talent attack to avoid depending on the
    # exact direct-damage coefficient and rounding implementation.
    baseline = _battle()
    assert _perform(baseline, "enemy-0", "hit", target_id="player")
    assert _perform(baseline, "enemy-0", "hit", target_id="player")
    unprotected = _events(baseline, "hit", actor="enemy-0")[-1]
    baseline_first_damage = D(
        _events(baseline, "hit", actor="enemy-0")[0].calculated_damage
    )
    assert reduced == int(
        (baseline_first_damage * D("0.93")).to_integral_value(rounding=ROUND_FLOOR)
    )
    assert second.calculated_damage == unprotected.calculated_damage


def test_antecipacao_does_not_spend_on_dodge_zero_or_existing_full_reduction():
    missed = _battle(talents=(ANTECIPACAO,), vigia_evasion="100")
    assert _perform(missed, "enemy-0", "hit", target_id="player")
    assert _events(missed, "hit", actor="enemy-0")[-1].dodged
    assert "vigia_antecipacao_used" not in missed.fighters["player"].path_state

    reduced_to_zero = _battle(talents=(ANTECIPACAO,))
    target = reduced_to_zero.fighters["player"]
    target.training_state_tags = ("complete_direct_mitigation",)
    target.tagged_direct_damage_reductions = {"complete_direct_mitigation": D(1)}
    assert _perform(reduced_to_zero, "enemy-0", "hit", target_id="player")
    assert _events(reduced_to_zero, "hit", actor="enemy-0")[-1].calculated_damage == 0
    assert "vigia_antecipacao_used" not in target.path_state

    target.tagged_direct_damage_reductions.clear()
    assert _perform(reduced_to_zero, "enemy-0", "hit", target_id="player")
    assert target.path_state["vigia_antecipacao_used"] is True


def test_antecipacao_counts_positive_damage_before_barrier_and_only_first_multihit_component():
    absorbed = _battle(talents=(ANTECIPACAO,))
    vigia = absorbed.fighters["player"]
    vigia.barrier = D("10000")
    vigia.barrier_remaining = 2
    assert _perform(absorbed, "enemy-0", "hit", target_id="player")
    event = _events(absorbed, "hit", actor="enemy-0")[-1]
    assert event.calculated_damage > 0 and event.effective_damage == 0
    assert vigia.path_state["vigia_antecipacao_used"] is True

    multi = _battle(talents=(ANTECIPACAO,))
    assert _perform(multi, "enemy-0", "multi_hit", target_id="player")
    events = _events(multi, "multi_hit", actor="enemy-0")
    assert len(events) == 3
    baseline = _battle()
    assert _perform(baseline, "enemy-0", "multi_hit", target_id="player")
    raw_events = _events(baseline, "multi_hit", actor="enemy-0")
    assert [event.calculated_damage for event in events] == [
        int(
            (D(raw_events[0].calculated_damage) * D("0.93")).to_integral_value(
                rounding=ROUND_FLOOR
            )
        ),
        raw_events[1].calculated_damage,
        raw_events[2].calculated_damage,
    ]


def test_antecipacao_roundtrips_reconnect_and_clears_at_combat_end():
    state = _battle(talents=(ANTECIPACAO,), path="rastreador")
    assert _perform(state, "enemy-0", "hit", target_id="player")
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].path_state["vigia_antecipacao_used"] is True
    before = restored.fighters["player"].hp
    assert _perform(restored, "enemy-0", "hit", target_id="player")
    assert restored.fighters["player"].path_state["vigia_antecipacao_used"] is True
    assert before - restored.fighters["player"].hp > 0
    _finish_combat(restored, "victory")
    assert "vigia_antecipacao_used" not in restored.fighters["player"].path_state


@pytest.mark.parametrize(
    ("path", "expected_first_target_stacks"),
    ((None, 2), ("atirador", 2), ("rastreador", 2)),
)
def test_aquisicao_rapida_adds_one_extra_from_action_start_snapshot(
    path, expected_first_target_stacks
):
    state = _battle(talents=(AQUISICAO,), path=path)
    assert _perform(state, "player", VIGIA_ATTACK, target_id="enemy-0")
    assert _aim(state)["stacks"] == expected_first_target_stacks
    assert state.fighters["player"].path_state["aim_acquisition_used"] == {
        "enemy-entity-0": True
    }

    # The same target can get the ordinary Mira later, but the one-time extra
    # is not restored by a new action.
    state.fighters["enemy-0"].path_state["aim_from"]["vigia-entity"]["remaining"] = 0
    assert _perform(state, "player", VIGIA_ATTACK, target_id="enemy-0")
    assert _aim(state)["stacks"] == 1
    assert state.fighters["player"].path_state["aim_acquisition_used"]["enemy-entity-0"]


def test_aquisicao_rapida_is_once_per_target_identity_and_combat():
    state = _battle(
        talents=(AQUISICAO,), path="rastreador", enemy_count=3, same_enemy_name=True
    )
    for target_key in ("enemy-0", "enemy-1", "enemy-2"):
        assert _perform(state, "player", VIGIA_ATTACK, target_id=target_key)
    used = state.fighters["player"].path_state["aim_acquisition_used"]
    assert used == {
        "enemy-entity-0": True,
        "enemy-entity-1": True,
        "enemy-entity-2": True,
    }
    assert all(_aim(state, key)["stacks"] == 2 for key in ("enemy-0", "enemy-1", "enemy-2"))

    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].path_state["aim_acquisition_used"] == used
    assert _perform(restored, "player", VIGIA_ATTACK, target_id="enemy-0")
    assert _aim(restored, "enemy-0")["stacks"] == 2
    assert restored.fighters["player"].path_state["aim_acquisition_used"]["enemy-entity-0"]

    _finish_combat(restored, "victory")
    assert "aim_acquisition_used" not in restored.fighters["player"].path_state
    new_fight = _battle(talents=(AQUISICAO,), path="rastreador", combat_id=uuid4())
    assert _perform(new_fight, "player", VIGIA_ATTACK, target_id="enemy-0")
    assert _aim(new_fight)["stacks"] == 2


def test_aquisicao_rapida_extra_is_not_mistaken_for_normal_rastros_generation():
    state = _battle(talents=(AQUISICAO,), path="rastreador", enemy_count=2)
    action = Action(
        "class_art.vigia.voleio",
        "Voleio",
        D("0.2"),
        target_mode="all_opponents",
        native_dot_kind="bleed",
        native_dot_stacks=1,
        duration=2,
    )
    state.player_actions[VOLEIO] = action
    assert _perform(state, "player", VOLEIO, target_id="enemy-0")
    # The explicit primary receives ordinary base Mira plus Aquisição Rápida.
    # A secondary receives no ordinary AoE Mira, but the published per-target
    # extra plus Rastros Múltiplos' independent normal status Mira.
    assert _aim(state, "enemy-0")["stacks"] == 2
    assert _aim(state, "enemy-1")["stacks"] == 2
    assert state.fighters["player"].path_state["aim_acquisition_used"] == {
        "enemy-entity-0": True,
        "enemy-entity-1": True,
    }


def test_aquisicao_rapida_applies_to_aoe_valid_targets_but_keeps_base_primary_only():
    state = _battle(talents=(AQUISICAO,), path="atirador", enemy_count=3)
    assert _perform(state, "player", VOLEIO, target_id="enemy-1")
    assert _aim(state, "enemy-1")["stacks"] == 2
    assert _aim(state, "enemy-0")["stacks"] == 1
    assert _aim(state, "enemy-2")["stacks"] == 1

    no_primary = _battle(talents=(AQUISICAO,), path="atirador", enemy_count=2)
    assert _perform(no_primary, "player", VOLEIO)
    assert all(_aim(no_primary, key)["stacks"] == 1 for key in ("enemy-0", "enemy-1"))

    miss = _battle(talents=(AQUISICAO,), path="atirador", enemy_count=2)
    miss.fighters["enemy-1"].stats = CombatStats(
        D(10000), D(10), D(0), D(1), evasion=D(100)
    )
    assert _perform(miss, "player", VOLEIO, target_id="enemy-1")
    assert _aim(miss, "enemy-1") is None
    assert "enemy-entity-1" not in miss.fighters["player"].path_state.get(
        "aim_acquisition_used", {}
    )
    assert _aim(miss, "enemy-0")["stacks"] == 1


def test_aquisicao_rapida_respects_caps_and_records_first_eligible_capped_trigger():
    rastreador = _battle(
        talents=(AQUISICAO,), path="rastreador", enemy_count=4
    )
    for target_key in ("enemy-0", "enemy-1", "enemy-2"):
        assert _perform(rastreador, "player", VIGIA_ATTACK, target_id=target_key)
        assert _aim(rastreador, target_key)["stacks"] == 2
    assert _perform(rastreador, "player", VIGIA_ATTACK, target_id="enemy-3")
    assert _aim(rastreador, "enemy-3") is None
    assert rastreador.fighters["player"].path_state["aim_acquisition_used"][
        "enemy-entity-3"
    ] is True

    # Freeing a Rastreador target slot does not replay the spent per-target
    # allowance for a target whose first eligible hit already occurred.
    rastreador.fighters["enemy-0"].path_state.pop("aim_from")
    assert _perform(rastreador, "player", VIGIA_ATTACK, target_id="enemy-3")
    assert _aim(rastreador, "enemy-3")["stacks"] == 1

    atirador = _battle(talents=(AQUISICAO,), path="atirador")
    atirador.fighters["enemy-0"].path_state["aim_from"] = {
        "vigia-entity": {
            "stacks": 3,
            "remaining": 2,
            "applied_opportunity": 0,
        }
    }
    assert _perform(atirador, "player", VIGIA_ATTACK, target_id="enemy-0")
    assert _aim(atirador)["stacks"] == 4
    assert "enemy-entity-0" not in atirador.fighters["player"].path_state.get(
        "aim_acquisition_used", {}
    )


def test_aquisicao_rapida_does_not_use_allowance_for_zero_damage_or_invalid_action():
    state = _battle(talents=(AQUISICAO,), path="atirador")
    target = state.fighters["enemy-0"]
    target.training_state_tags = ("complete_direct_mitigation",)
    target.tagged_direct_damage_reductions = {"complete_direct_mitigation": D(1)}
    assert _perform(state, "player", VIGIA_ATTACK, target_id="enemy-0")
    assert "enemy-entity-0" not in state.fighters["player"].path_state.get(
        "aim_acquisition_used", {}
    )

    target.tagged_direct_damage_reductions.clear()
    assert not _perform(state, "player", VIGIA_ATTACK, target_id="unknown")
    assert "enemy-entity-0" not in state.fighters["player"].path_state.get(
        "aim_acquisition_used", {}
    )
    assert _perform(state, "player", VIGIA_ATTACK, target_id="enemy-0")
    assert _aim(state)["stacks"] == 2

    absorbed = _battle(talents=(AQUISICAO,), path="atirador")
    absorbed.fighters["enemy-0"].barrier = D("10000")
    absorbed.fighters["enemy-0"].barrier_remaining = 2
    assert _perform(absorbed, "player", VIGIA_ATTACK, target_id="enemy-0")
    absorbed_event = _events(absorbed, VIGIA_ATTACK, actor="player")[-1]
    assert absorbed_event.calculated_damage > 0
    assert absorbed_event.effective_damage == 0
    assert _aim(absorbed)["stacks"] == 2
    assert absorbed.fighters["player"].path_state["aim_acquisition_used"][
        "enemy-entity-0"
    ] is True


def test_aquisicao_rapida_keeps_atirador_target_switch_rules_without_resetting_quota():
    state = _battle(talents=(AQUISICAO,), path="atirador", enemy_count=2)
    assert _perform(state, "player", VIGIA_ATTACK, target_id="enemy-0")
    assert _aim(state, "enemy-0")["stacks"] == 2

    assert _perform(state, "player", VIGIA_ATTACK, target_id="enemy-1")
    assert _aim(state, "enemy-0") is None
    assert _aim(state, "enemy-1")["stacks"] == 2

    assert _perform(state, "player", VIGIA_ATTACK, target_id="enemy-0")
    # Switching back gives only the normal Mira; A's extra was already used.
    assert _aim(state, "enemy-1") is None
    assert _aim(state, "enemy-0")["stacks"] == 1
    assert state.fighters["player"].path_state["aim_acquisition_used"] == {
        "enemy-entity-0": True,
        "enemy-entity-1": True,
    }


def test_aquisicao_rapida_saraivada_multi_hit_triggers_once_per_target():
    state = _battle(talents=(AQUISICAO,), path="atirador")
    state.player_actions["multi"] = Action(
        "class_art.vigia.saraivada",
        "Saraivada",
        D("0.1"),
        hit_count=3,
    )
    assert _perform(state, "player", "multi", target_id="enemy-0")
    hits = _events(state, "multi", actor="player")
    assert len(hits) == 3
    assert len({event.action_instance_id for event in hits}) == 1
    assert _aim(state)["stacks"] == 2
    assert state.fighters["player"].path_state["aim_acquisition_used"] == {
        "enemy-entity-0": True
    }


def test_aquisicao_rapida_uses_mira_estavel_duration_without_extra_stack_or_window():
    state = _battle(talents=(AQUISICAO, MIRA_ESTAVEL), path="atirador")
    assert _perform(state, "player", VIGIA_ATTACK, target_id="enemy-0")
    assert _aim(state)["stacks"] == 2
    assert _aim(state)["remaining"] == 3
    assert _aim(state)["trigger"] == "aquisicao_rapida"


def test_nv25_hooks_require_level_and_nv35_is_public():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("vigia", 24, (PERFURACAO,))
    assert validate_active_talent_ids("vigia", 25, (ANTECIPACAO,)) == (ANTECIPACAO,)
    assert resolve_combat_stats("vigia", 25, "remanescente", talent_ids=(PERFURACAO,))
    future_id = next(t.talent_id for t in TALENTS_BY_CLASS["vigia"] if t.level == 35)
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("vigia", 34, (future_id,))
    assert validate_active_talent_ids("vigia", 60, (future_id,)) == (future_id,)
    assert validate_active_talent_ids("vigia", 15, ("talent.vigia.mao_firme",))
    assert validate_active_talent_ids("vigia", 15, (MIRA_ESTAVEL,))

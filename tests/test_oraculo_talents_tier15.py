from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.domain.arts import ORACULO_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Fighter,
    _apply_barrier,
    _tick_path_resources,
    act,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    class_stats,
    finalize_primary_stats,
    racial_stats,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    _static_talent_secondary_modifier_totals,
    static_talent_modifiers,
    static_talent_secondary_modifiers,
    talent_points_at_level,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
PRESSAGIO_CORTANTE = "talent.oraculo.pressagio_cortante"
VEU_CAUTELOSO = "talent.oraculo.veu_cauteloso"
SINAL_PERSISTENTE = "talent.oraculo.sinal_persistente"
SINAL = ORACULO_ART_IDS["sinal_funesto"]
SELO = ORACULO_ART_IDS["selo_da_queda"]
AUGURIO = ORACULO_ART_IDS["augurio_favoravel"]
VEU_PREMONITORIO = ORACULO_ART_IDS["veu_premonitorio"]


def _internal_stats(
    talent_ids: tuple[str, ...],
    *,
    path: str | None = None,
    equipment: EquipmentStatContribution | None = None,
):
    definitions = tuple(TALENT_DEFINITIONS[talent_id] for talent_id in talent_ids)
    return _resolve_combat_stats_with_static_talent_modifiers(
        "oraculo",
        34,
        "remanescente",
        equipment,
        path,
        _static_talent_modifier_totals(definitions),
        _static_talent_secondary_modifier_totals(definitions),
    )


def _combat(
    *,
    path: str | None = None,
    talents: tuple[str, ...] = (),
    arts: tuple[str, ...] = (SELO,),
    per: Decimal = ZERO,
    enemy_count: int = 1,
    ally: bool = False,
):
    stats = resolve_combat_stats("oraculo", 34, "remanescente", selected_path=path)
    state = PROFILE.create(uuid4(), "Oráculo", "oraculo", "remanescente", stats.hp)
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET

    actor = state.fighters["player"]
    actor.level = 34
    actor.character_class = "oraculo"
    actor.selected_path = path
    actor.talent_ids = tuple(talents)
    actor.side = "player"
    actor.stats = replace(
        stats,
        hp=D(1000),
        attack=D(100),
        defense=D(100),
        agility=D(200),
        per=per,
        crit=ZERO,
        evasion=ZERO,
        block=ZERO,
    )
    actor.hp = actor.stats.hp

    for index in range(enemy_count):
        key = "enemy" if index == 0 else f"enemy-{index}"
        if index == 0:
            target = state.fighters["enemy"]
        else:
            target = Fighter(
                id=f"enemy-entity-{index}",
                name=f"Inimigo {index}",
                level=34,
                stats=CombatStats(D(10000), D(20), D(100), D(0)),
                hp=D(10000),
                side="enemy",
                takes_turn=False,
                required_for_victory=False,
            )
            state.fighters[key] = target
        target.stats = replace(
            target.stats,
            hp=D(10000),
            attack=D(20),
            defense=D(100),
            agility=ZERO,
            per=ZERO,
            crit=ZERO,
            evasion=ZERO,
            block=ZERO,
        )
        target.hp = target.stats.hp
        target.side = "enemy"
        target.takes_turn = False

    if ally:
        ally_stats = replace(actor.stats, hp=D(1000), agility=D(50))
        state.fighters["ally"] = Fighter(
            id="ally-entity",
            name="Aliada",
            level=34,
            stats=ally_stats,
            hp=ally_stats.hp,
            race="remanescente",
            character_class="sentinela",
            side="player",
            takes_turn=False,
            required_for_victory=False,
        )
        state.party_mode = True
        state.manual_sides = ("player",)

    state.player_actions = class_player_actions("oraculo", arts, path)
    state.enemy_actions = {
        "wait": Action("enemy.wait", "Aguardar", ZERO, target_mode="self")
    }
    state.ai_cycle = ("wait",)
    return start_combat(state)


def _mark(state, kind: str, target_key: str, *, remaining: int = 2):
    actor = state.fighters["player"]
    target = state.fighters[target_key]
    key = f"omen_{kind}"
    actor.path_state.setdefault(key, {})[target.id] = {
        "remaining": remaining,
        "applied_opportunity": actor.opportunity,
    }


def _event(state, action_id: str):
    return next(
        event
        for event in reversed(state.events)
        if event.action == action_id
        and event.actor_entity_id == state.fighters["player"].id
    )


def test_oraculo_tier15_definitions_are_publicly_authorized_at_level():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35})
    assert talent_points_at_level(15) == 3
    expected = {
        PRESSAGIO_CORTANTE: ("Presságio Cortante", D(15), D(0), D(0)),
        VEU_CAUTELOSO: ("Véu Cauteloso", D(15), D(0), D("0.02")),
        SINAL_PERSISTENTE: ("Sinal Persistente", D(15), D(0), D(0)),
    }
    for talent_id, (name, level, per, defense) in expected.items():
        definition = TALENT_DEFINITIONS[talent_id]
        assert (definition.name, definition.level, definition.per_points) == (name, level, per)
        assert definition.defense_percent == defense
        assert validate_active_talent_ids("oraculo", 15, (talent_id,)) == (talent_id,)
        assert validate_talent_choices("oraculo", 15, ((1, talent_id),)) == (
            (1, talent_id),
        )
        static_talent_modifiers("oraculo", 15, (talent_id,))
        static_talent_secondary_modifiers("oraculo", 15, (talent_id,))
        resolve_combat_stats("oraculo", 15, "remanescente", talent_ids=(talent_id,))
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("oraculo", 14, (talent_id,))
    tier25 = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "oraculo" and definition.level == 25
    )
    assert validate_active_talent_ids("oraculo", 25, (tier25,)) == (tier25,)
    tier35 = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "oraculo" and definition.level == 35
    )
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("oraculo", 34, (tier35,))
    assert validate_active_talent_ids("oraculo", 35, (tier35,)) == (tier35,)
    assert validate_active_talent_ids("oraculo", 60, (tier35,)) == (tier35,)


@pytest.mark.parametrize("path", (None, "agoureiro", "invocador"))
def test_veu_cauteloso_composes_static_defense_once_with_other_stages(path):
    equipment = EquipmentStatContribution(
        defense=D("13.25"),
        crit=D("3.5"),
        rune_percent=(ZERO, ZERO, D("0.035"), ZERO, ZERO, ZERO, ZERO, ZERO),
        rune_points=(ZERO, ZERO, D("0.4"), ZERO, ZERO, ZERO, ZERO, ZERO),
        enchantment_percent=(ZERO, ZERO, D("0.025"), ZERO, ZERO, ZERO, ZERO, ZERO),
        enchantment_points=(ZERO, ZERO, D("0.3"), ZERO, ZERO, ZERO, ZERO, ZERO),
    )
    actual = _internal_stats((VEU_CAUTELOSO,), path=path, equipment=equipment)
    baseline = _internal_stats((), path=path, equipment=equipment)

    base = class_stats("oraculo", 34)
    path_defense = PATH_DEFINITIONS[path].defense if path else ZERO
    raw = base.defense * (D(1) + path_defense) * D("1.02") + equipment.defense
    raw = raw * (D(1) + equipment.rune_percent[2]) + equipment.rune_points[2]
    raw = raw * (D(1) + equipment.enchantment_percent[2]) + equipment.enchantment_points[2]
    expected = finalize_primary_stats(
        racial_stats(replace(base, defense=raw), "remanescente")
    ).defense

    assert actual.defense == expected
    assert actual.defense > baseline.defense
    assert (
        actual.hp,
        actual.attack,
        actual.agility,
        actual.per,
        actual.crit,
        actual.evasion,
        actual.block,
    ) == (
        baseline.hp,
        baseline.attack,
        baseline.agility,
        baseline.per,
        baseline.crit,
        baseline.evasion,
        baseline.block,
    )
    assert _internal_stats((VEU_CAUTELOSO,), path=path, equipment=equipment) == actual


def test_three_oraculo_tier15_effects_coexist_in_controlled_internal_combat():
    talents = (PRESSAGIO_CORTANTE, VEU_CAUTELOSO, SINAL_PERSISTENTE)
    internal_stats = _internal_stats(talents, path="agoureiro")
    veil_only_stats = _internal_stats((VEU_CAUTELOSO,), path="agoureiro")
    assert internal_stats.defense == veil_only_stats.defense
    assert internal_stats.crit == veil_only_stats.crit

    state = _combat(path="agoureiro", talents=talents)
    actor = state.fighters["player"]
    actor.stats = replace(
        internal_stats,
        hp=D(1000),
        attack=D(100),
        agility=D(200),
        per=ZERO,
        crit=ZERO,
        evasion=ZERO,
        block=ZERO,
    )
    actor.hp = actor.stats.hp
    _mark(state, "offensive", "enemy")

    result = act(state, SELO, target_id=state.fighters["enemy"].id)
    event = _event(result, SELO)
    resolved_actor = result.fighters["player"]
    target_id = result.fighters["enemy"].id
    assert resolved_actor.stats.defense == internal_stats.defense
    assert event.path_per_bonus == D(2)
    assert event.path_power_multiplier == D("1.16")
    assert resolved_actor.path_state["omen_offensive"][target_id]["remaining"] == 3


@pytest.mark.parametrize(
    ("path", "expected_power"),
    ((None, D("1.12")), ("agoureiro", D("1.16")), ("invocador", D("1.12"))),
)
def test_pressagio_cortante_applies_only_when_offensive_mark_is_consumed(path, expected_power):
    state = _combat(path=path, talents=(PRESSAGIO_CORTANTE,))
    _mark(state, "offensive", "enemy")
    target_id = state.fighters["enemy"].id

    result = act(state, SELO, target_id=target_id)
    event = _event(result, SELO)
    actor = result.fighters["player"]

    assert event.path_per_bonus == D(2)
    assert event.path_power_multiplier == expected_power
    assert "pressagio.ofensivo_consumido" in event.path_triggers
    assert event.class_resource_changes == (("omen_offensive", target_id, 1, 0),)
    # Selo applies its own DEF Debuff and can create a fresh mark only afterward.
    assert actor.path_state["omen_offensive"][target_id]["remaining"] == 2
    assert "oraculo.pressagio_offensive_criado" in event.path_triggers


@pytest.mark.parametrize("mark_kind", ("none", "defensive", "other_target"))
def test_pressagio_cortante_does_not_trigger_without_the_selected_targets_old_offensive_mark(
    mark_kind,
):
    state = _combat(talents=(PRESSAGIO_CORTANTE,), enemy_count=2)
    actor = state.fighters["player"]
    if mark_kind == "defensive":
        _mark(state, "defensive", "player")
    elif mark_kind == "other_target":
        _mark(state, "offensive", "enemy-1")

    result = act(state, SELO, target_id=state.fighters["enemy"].id)
    event = _event(result, SELO)
    assert event.path_per_bonus == ZERO
    assert "pressagio.ofensivo_consumido" not in event.path_triggers
    assert event.path_power_multiplier == D(1)
    if mark_kind == "defensive":
        assert actor.id in result.fighters["player"].path_state["omen_defensive"]
    if mark_kind == "other_target":
        assert state.fighters["enemy-1"].id in result.fighters["player"].path_state[
            "omen_offensive"
        ]


def test_pressagio_cortante_respects_per_cap_and_does_not_change_attack_coefficient():
    empowered = _combat(talents=(PRESSAGIO_CORTANTE,), per=D(29))
    _mark(empowered, "offensive", "enemy")
    baseline = _combat(per=D(29))
    _mark(baseline, "offensive", "enemy")

    empowered_result = act(empowered, SELO, target_id=empowered.fighters["enemy"].id)
    baseline_result = act(baseline, SELO, target_id=baseline.fighters["enemy"].id)
    empowered_event = _event(empowered_result, SELO)
    baseline_event = _event(baseline_result, SELO)

    assert empowered_event.path_per_bonus == D(2)
    assert baseline_event.path_per_bonus == ZERO
    assert (
        empowered_event.path_power_multiplier
        == baseline_event.path_power_multiplier
        == D("1.12")
    )
    # At 29 p.p. the Talent reaches, but cannot exceed, the shared 30 p.p. cap.
    assert empowered_event.damage == baseline_event.damage


@pytest.mark.parametrize("outcome", ("dodge", "barrier"))
def test_consumed_omen_is_not_refunded_after_commit(outcome):
    state = _combat(talents=(PRESSAGIO_CORTANTE, SINAL_PERSISTENTE))
    target = state.fighters["enemy"]
    _mark(state, "offensive", "enemy", remaining=3)
    if outcome == "dodge":
        target.stats = replace(target.stats, evasion=D(100))
    else:
        _apply_barrier(
            target,
            applier_id="barrier-source",
            effect_definition_id="barrier.test",
            value=D(10000),
            duration=2,
            applied_opportunity=target.opportunity,
            round_number=state.round,
        )

    result = act(state, SELO, target_id=target.id)
    event = _event(result, SELO)
    actor = result.fighters["player"]
    assert event.path_per_bonus == D(2)
    assert event.class_resource_changes == (("omen_offensive", target.id, 1, 0),)
    if outcome == "dodge":
        assert event.dodged
        assert "omen_offensive" not in actor.path_state
    else:
        assert event.effective_damage == 0
        # The new mark is produced by the successful DEF Debuff, not a refund.
        assert actor.path_state["omen_offensive"][target.id]["remaining"] == 3


@pytest.mark.parametrize("talents, expected", (((), 2), ((SINAL_PERSISTENTE,), 3)))
def test_offensive_omen_duration_counts_only_oraculo_opportunities_and_survives_codec(
    talents, expected
):
    state = _combat(talents=talents, arts=(SINAL,))
    result = act(state, SINAL, target_id=state.fighters["enemy"].id)
    target_id = result.fighters["enemy"].id
    mark = result.fighters["player"].path_state["omen_offensive"][target_id]
    assert mark["remaining"] == expected

    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["player"].path_state["omen_offensive"][target_id] == mark
    _tick_path_resources(restored, "enemy")
    assert restored.fighters["player"].path_state["omen_offensive"][target_id][
        "remaining"
    ] == expected

    owner = restored.fighters["player"]
    for left in range(expected - 1, 0, -1):
        owner.opportunity += 1
        _tick_path_resources(restored, "player")
        assert owner.path_state["omen_offensive"][target_id]["remaining"] == left
    owner.opportunity += 1
    _tick_path_resources(restored, "player")
    assert target_id not in owner.path_state.get("omen_offensive", {})


@pytest.mark.parametrize("talents, expected", (((), 2), ((SINAL_PERSISTENTE,), 3)))
@pytest.mark.parametrize("art_id", (AUGURIO, VEU_PREMONITORIO))
def test_defensive_omen_duration_tracks_the_oraculo_and_survives_codec(
    art_id, talents, expected
):
    state = _combat(talents=talents, arts=(art_id,))
    actor = state.fighters["player"]
    result = act(state, art_id, target_id=actor.id)
    owner = result.fighters["player"]
    mark = owner.path_state["omen_defensive"][owner.id]

    assert mark["remaining"] == expected
    assert mark["applied_opportunity"] == actor.opportunity
    if art_id == AUGURIO:
        assert any(effect.id == "oraculo.augurio_favoravel.attack" for effect in owner.effects)
    else:
        assert owner.barrier > 0

    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["player"].path_state["omen_defensive"][owner.id] == mark

    restored_owner = restored.fighters["player"]
    for left in range(expected - 1, 0, -1):
        restored_owner.opportunity += 1
        _tick_path_resources(restored, "player")
        assert restored_owner.path_state["omen_defensive"][owner.id]["remaining"] == left
    restored_owner.opportunity += 1
    _tick_path_resources(restored, "player")
    assert owner.id not in restored_owner.path_state.get("omen_defensive", {})


def test_defensive_omen_is_targeted_and_reapplied_by_a_buff_without_being_consumed():
    state = _combat(
        talents=(SINAL_PERSISTENTE,),
        arts=(AUGURIO,),
        ally=True,
    )
    actor = state.fighters["player"]
    ally = state.fighters["ally"]
    _mark(state, "defensive", "ally", remaining=1)

    result = act(state, AUGURIO, target_id=ally.id)
    owner = result.fighters["player"]
    event = _event(result, AUGURIO)
    assert "pressagio.defensivo_consumido" not in event.path_triggers
    assert event.class_resource_changes == ()
    assert owner.path_state["omen_defensive"] == {
        ally.id: {
            "remaining": 3,
            "applied_opportunity": actor.opportunity,
        }
    }
    assert actor.id not in owner.path_state["omen_defensive"]
    assert "oraculo.pressagio_defensive_criado" in event.path_triggers


def test_offensive_and_defensive_omens_remain_independent_through_consumption_and_recreation():
    state = _combat(
        talents=(PRESSAGIO_CORTANTE, SINAL_PERSISTENTE),
        arts=(SELO, VEU_PREMONITORIO),
    )
    actor = state.fighters["player"]
    enemy_id = state.fighters["enemy"].id
    _mark(state, "offensive", "enemy", remaining=3)
    _mark(state, "defensive", "player", remaining=3)

    after_offensive = act(state, SELO, target_id=enemy_id)
    offense_event = _event(after_offensive, SELO)
    actor_after = after_offensive.fighters["player"]
    assert offense_event.path_per_bonus == D(2)
    assert actor_after.path_state["omen_offensive"][enemy_id]["remaining"] == 3
    assert actor_after.path_state["omen_defensive"][actor.id]["remaining"] == 3

    after_defensive = act(after_offensive, VEU_PREMONITORIO, target_id=actor.id)
    defense_event = _event(after_defensive, VEU_PREMONITORIO)
    actor_final = after_defensive.fighters["player"]
    assert "pressagio.defensivo_consumido" in defense_event.path_triggers
    assert actor_final.path_state["omen_defensive"][actor.id]["remaining"] == 3
    # The offensive mark remains independent, but its own duration advances on
    # the Oráculo's next opportunity while the defensive mark is consumed.
    assert actor_final.path_state["omen_offensive"][enemy_id]["remaining"] == 2


def test_resguardo_prevents_offensive_generation_but_not_commit_time_consumption():
    state = _combat(talents=(PRESSAGIO_CORTANTE, SINAL_PERSISTENTE))
    target = state.fighters["enemy"]
    target.ward_charges = 1
    target.ward_remaining = 2
    target.ward_applied_opportunity = target.opportunity
    _mark(state, "offensive", "enemy", remaining=3)

    result = act(state, SELO, target_id=target.id)
    event = _event(result, SELO)
    actor = result.fighters["player"]
    assert event.path_per_bonus == D(2)
    assert event.class_resource_changes == (("omen_offensive", target.id, 1, 0),)
    assert "omen_offensive" not in actor.path_state
    assert "oraculo.pressagio_offensive_criado" not in event.path_triggers


def test_precommit_invalid_target_preserves_offensive_omen_and_cooldown():
    state = _combat(talents=(PRESSAGIO_CORTANTE,))
    _mark(state, "offensive", "enemy")
    actor = state.fighters["player"]
    target_id = state.fighters["enemy"].id

    assert act(state, SELO, target_id="outside-encounter") is state
    assert actor.path_state["omen_offensive"][target_id]["remaining"] == 2
    assert SELO not in actor.cooldowns
    assert not any(event.action == SELO for event in state.events)

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

import asterion.domain.combat as combat_module
from asterion.domain.arts import ORACULO_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Fighter,
    _advance_barrier_sources,
    _apply_barrier,
    _deal_damage,
    act,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    _static_talent_secondary_modifier_totals,
    static_talent_secondary_modifiers,
    talent_points_at_level,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
DESTINO_EXPOSTO = "talent.oraculo.destino_exposto"
ANTEVISAO_DEFENSIVA = "talent.oraculo.antevisao_defensiva"
LEITURA_DOS_SINAIS = "talent.oraculo.leitura_dos_sinais"
LEITURA_EFFECT = "class_mechanic.oraculo.leitura_dos_sinais.agility"
PRESSAGIO_CORTANTE = "talent.oraculo.pressagio_cortante"
SINAL_PERSISTENTE = "talent.oraculo.sinal_persistente"
SINAL = ORACULO_ART_IDS["sinal_funesto"]
SELO = ORACULO_ART_IDS["selo_da_queda"]
AUGURIO = ORACULO_ART_IDS["augurio_favoravel"]


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
    enemy_count: int = 1,
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
        per=ZERO,
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

    state.player_actions = class_player_actions("oraculo", arts, path)
    state.enemy_actions = {
        "wait": Action("enemy.wait", "Aguardar", ZERO, target_mode="self")
    }
    state.ai_cycle = ("wait",)
    return start_combat(state)


def _event(state, action_id: str):
    return next(
        event
        for event in reversed(state.events)
        if event.action == action_id
        and event.actor_entity_id == state.fighters["player"].id
    )


def test_destino_exposto_adds_two_static_crit_points_for_each_oraculo_path():
    equipment = EquipmentStatContribution(crit=D("3.5"))
    for path in (None, "agoureiro", "invocador"):
        baseline = _internal_stats((), path=path, equipment=equipment)
        actual = _internal_stats((DESTINO_EXPOSTO,), path=path, equipment=equipment)

        assert actual.crit == baseline.crit + D(2)
        assert (
            actual.hp,
            actual.attack,
            actual.defense,
            actual.agility,
            actual.per,
            actual.evasion,
            actual.block,
        ) == (
            baseline.hp,
            baseline.attack,
            baseline.defense,
            baseline.agility,
            baseline.per,
            baseline.evasion,
            baseline.block,
        )
        assert _internal_stats((DESTINO_EXPOSTO,), path=path, equipment=equipment) == actual


def test_destination_exposed_secondary_composition_preserves_other_crit_sources():
    equipment = EquipmentStatContribution(crit=D("4.25"))
    baseline = _internal_stats((), path="agoureiro", equipment=equipment)
    actual = _internal_stats((DESTINO_EXPOSTO,), path="agoureiro", equipment=equipment)

    assert baseline.crit == D(5) + D("4.25")
    assert actual.crit == D("11.25")
    assert actual.crit - baseline.crit == D(2)


@pytest.mark.parametrize(("pvp", "expected"), ((False, D(47)), (True, D(40))))
def test_destino_exposto_respects_the_existing_pvp_crit_cap(monkeypatch, pvp, expected):
    observed: list[Decimal] = []

    def capture_chance(points: Decimal) -> Decimal:
        observed.append(points)
        return ZERO

    monkeypatch.setattr(combat_module, "chance_from_percentage_points", capture_chance)
    state = _combat(talents=(DESTINO_EXPOSTO,), arts=())
    state.pvp_mode = pvp
    composed = _internal_stats(
        (DESTINO_EXPOSTO,),
        equipment=EquipmentStatContribution(crit=D(40)),
    )
    state.fighters["player"].stats = replace(
        state.fighters["player"].stats,
        crit=composed.crit,
    )

    act(state, "attack", target_id=state.fighters["enemy"].id)

    assert [points for points in observed if points > ZERO] == [expected]


def test_oraculo_tier25_is_publicly_valid_at_required_level():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    assert talent_points_at_level(25) == 5
    for talent_id in (DESTINO_EXPOSTO, ANTEVISAO_DEFENSIVA, LEITURA_DOS_SINAIS):
        assert TALENT_DEFINITIONS[talent_id].level == 25
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("oraculo", 24, (talent_id,))
        assert validate_active_talent_ids("oraculo", 25, (talent_id,)) == (talent_id,)
        assert static_talent_secondary_modifiers("oraculo", 25, (talent_id,))
        assert resolve_combat_stats("oraculo", 25, "remanescente", talent_ids=(talent_id,))
    legal_tier15 = ("talent.oraculo.pressagio_cortante",)
    assert validate_active_talent_ids("oraculo", 25, legal_tier15) == legal_tier15


def test_antevisao_defensiva_tracks_any_positive_barrier_without_stacking(monkeypatch):
    state = _combat(talents=(ANTEVISAO_DEFENSIVA,), arts=())
    owner = state.fighters["player"]
    owner_defense = owner.stats.defense
    target = state.fighters["enemy"]

    assert owner.barrier == ZERO
    assert owner.stat("defense") == owner_defense

    _apply_barrier(
        target,
        applier_id="enemy-source",
        effect_definition_id="barrier.enemy",
        value=D(100),
        duration=3,
        applied_opportunity=target.opportunity,
    )
    assert owner.stat("defense") == owner_defense

    # A barrier supplied by another entity qualifies: eligibility follows the
    # recipient's active barrier layers, not the creator's class or Art ID.
    _apply_barrier(
        owner,
        applier_id="ally-source",
        effect_definition_id="barrier.ally",
        value=D(5),
        duration=3,
        applied_opportunity=owner.opportunity,
    )
    _apply_barrier(
        owner,
        applier_id="consumable-source",
        effect_definition_id="barrier.consumable",
        value=D(7),
        duration=3,
        applied_opportunity=owner.opportunity,
    )
    assert owner.barrier == D(12)
    assert owner.stat("defense") == owner_defense * D("1.05")
    assert owner.stats.defense == owner_defense

    # Depleting one source leaves the effect active while any positive layer remains.
    _deal_damage(owner, D(5))
    assert owner.barrier == D(7)
    assert owner.stat("defense") == owner_defense * D("1.05")

    # The modifier is consulted by the ordinary damage-stat lookup as well.
    seen: list[Decimal] = []
    real_direct_damage = combat_module.direct_damage

    def capture_defense(attack, coefficient, defense, attacker_level, **kwargs):
        seen.append(defense)
        return real_direct_damage(attack, coefficient, defense, attacker_level, **kwargs)

    monkeypatch.setattr(combat_module, "direct_damage", capture_defense)
    target.character_class = "oraculo"
    target.talent_ids = (ANTEVISAO_DEFENSIVA,)
    target.stats = replace(target.stats, defense=D(100))
    _apply_barrier(
        target,
        applier_id="foreign-source",
        effect_definition_id="barrier.foreign",
        value=D(10),
        duration=2,
        applied_opportunity=target.opportunity,
    )
    act(state, "attack", target_id=target.id)
    assert seen == [D(105)]

    _deal_damage(owner, D(7))
    assert owner.barrier == ZERO
    assert owner.stat("defense") == owner_defense


def test_antevisao_defensiva_uses_barrier_caps_and_does_not_survive_expiration():
    state = _combat(talents=(ANTEVISAO_DEFENSIVA,), arts=())
    owner = state.fighters["player"]
    owner.barrier_cap_fraction = D("0.35")

    granted = _apply_barrier(
        owner,
        applier_id="phase-source",
        effect_definition_id="barrier.phase",
        value=D(500),
        duration=1,
        applied_opportunity=owner.opportunity,
    )
    assert granted == D(350)
    assert owner.barrier == D(350)
    assert owner.stat("defense") == owner.stats.defense * D("1.05")

    owner.opportunity += 1
    _advance_barrier_sources(owner)
    assert owner.barrier == ZERO
    assert owner.stat("defense") == owner.stats.defense


def test_antevisao_barrier_derived_defense_survives_codec_without_reapplication():
    state = _combat(talents=(ANTEVISAO_DEFENSIVA,), arts=())
    owner = state.fighters["player"]
    base_defense = owner.stats.defense
    _apply_barrier(
        owner,
        applier_id="ally-source",
        effect_definition_id="barrier.ally",
        value=D(17),
        duration=2,
        applied_opportunity=owner.opportunity,
    )

    restored = decode(encode(state), state.id, state.ruleset, state.version)
    restored_owner = restored.fighters["player"]
    assert restored_owner.barrier == D(17)
    assert restored_owner.stat("defense") == base_defense * D("1.05")
    assert restored_owner.stats.defense == base_defense

    _deal_damage(restored_owner, D(8))
    assert restored_owner.barrier == D(9)
    assert restored_owner.stat("defense") == base_defense * D("1.05")
    _deal_damage(restored_owner, D(9))
    assert restored_owner.barrier == ZERO
    assert restored_owner.stat("defense") == base_defense


def test_antevisao_defensiva_coexists_with_veu_cauteloso_and_is_not_static():
    veu_cauteloso = "talent.oraculo.veu_cauteloso"
    composed = _internal_stats((veu_cauteloso,))
    state = _combat(talents=(veu_cauteloso, ANTEVISAO_DEFENSIVA), arts=())
    owner = state.fighters["player"]
    owner.stats = replace(
        composed,
        hp=D(1000),
        attack=D(100),
        agility=D(200),
        per=ZERO,
        crit=ZERO,
        evasion=ZERO,
        block=ZERO,
    )
    owner.hp = owner.stats.hp
    static_defense = owner.stats.defense

    assert owner.stat("defense") == static_defense
    _apply_barrier(
        owner,
        applier_id="ally-source",
        effect_definition_id="barrier.ally",
        value=D(1),
        duration=2,
        applied_opportunity=owner.opportunity,
    )
    assert owner.stat("defense") == static_defense * D("1.05")

    _deal_damage(owner, D(1))
    assert owner.barrier == ZERO
    assert owner.stat("defense") == static_defense
    assert owner.stats.defense == static_defense


def test_leitura_dos_sinais_follows_offensive_omen_application_and_survives_codec():
    state = _combat(talents=(LEITURA_DOS_SINAIS, SINAL_PERSISTENTE), arts=(SINAL,))
    actor_before = state.fighters["player"]
    baseline_agility = actor_before.stat("agility")

    resolved = act(state, SINAL, target_id=state.fighters["enemy"].id)
    actor_after = resolved.fighters["player"]
    target_id = resolved.fighters["enemy"].id
    effect = next(effect for effect in actor_after.effects if effect.id == LEITURA_EFFECT)
    event = _event(resolved, SINAL)

    assert actor_after.path_state["omen_offensive"][target_id]["remaining"] == 3
    assert (effect.magnitude, effect.remaining, effect.applied_opportunity) == (
        D("0.05"),
        1,
        actor_before.opportunity,
    )
    assert actor_after.stat("agility") == baseline_agility * D("1.05")
    assert "oraculo.pressagio_offensive_criado" in event.path_triggers
    assert "oraculo.leitura_dos_sinais" in event.path_triggers
    assert LEITURA_EFFECT not in {row[0] for row in event.actor_effect_facts}

    restored = decode(encode(resolved), resolved.id, resolved.ruleset, resolved.version)
    restored_actor = restored.fighters["player"]
    restored_effect = next(
        effect for effect in restored_actor.effects if effect.id == LEITURA_EFFECT
    )
    assert restored_effect.remaining == effect.remaining == 1
    assert restored_actor.stat("agility") == actor_after.stat("agility")
    # Retrying the action while it is on cooldown cannot reapply or stack the buff.
    assert act(restored, SINAL, target_id=target_id) is restored
    assert sum(effect.id == LEITURA_EFFECT for effect in restored_actor.effects) == 1

    followup = act(restored, "attack", target_id=target_id)
    followup_event = _event(followup, "attack")
    followup_actor = followup.fighters["player"]
    assert LEITURA_EFFECT in {row[0] for row in followup_event.actor_effect_facts}
    assert not any(effect.id == LEITURA_EFFECT for effect in followup_actor.effects)
    assert followup_actor.stat("agility") == baseline_agility


def test_leitura_dos_sinais_is_not_triggered_by_defensive_omen_or_consumption_only():
    defensive = _combat(talents=(LEITURA_DOS_SINAIS,), arts=(AUGURIO,))
    resolved_defensive = act(
        defensive,
        AUGURIO,
        target_id=defensive.fighters["player"].id,
    )
    assert "omen_defensive" in resolved_defensive.fighters["player"].path_state
    assert not any(
        effect.id == LEITURA_EFFECT
        for effect in resolved_defensive.fighters["player"].effects
    )
    assert "oraculo.leitura_dos_sinais" not in _event(resolved_defensive, AUGURIO).path_triggers

    consumed_only = _combat(talents=(LEITURA_DOS_SINAIS,), arts=(SELO,))
    owner = consumed_only.fighters["player"]
    target = consumed_only.fighters["enemy"]
    owner.path_state.setdefault("omen_offensive", {})[target.id] = {
        "remaining": 2,
        "applied_opportunity": owner.opportunity,
    }
    target.ward_charges = 1
    target.ward_remaining = 2
    target.ward_applied_opportunity = target.opportunity

    resolved_consumed_only = act(consumed_only, SELO, target_id=target.id)
    consumed_event = _event(resolved_consumed_only, SELO)
    assert "pressagio.ofensivo_consumido" in consumed_event.path_triggers
    assert "oraculo.pressagio_offensive_criado" not in consumed_event.path_triggers
    assert "oraculo.leitura_dos_sinais" not in consumed_event.path_triggers
    assert not any(
        effect.id == LEITURA_EFFECT
        for effect in resolved_consumed_only.fighters["player"].effects
    )


def test_leitura_dos_sinais_reapplication_is_one_effect_and_resguardo_blocks_generation():
    state = _combat(talents=(LEITURA_DOS_SINAIS,), arts=(SINAL,))
    first = act(state, SINAL, target_id=state.fighters["enemy"].id)
    actor = first.fighters["player"]
    enemy = first.fighters["enemy"]
    actor.cooldowns[SINAL] = actor.opportunity
    second = act(first, SINAL, target_id=enemy.id)
    second_actor = second.fighters["player"]

    effects = [effect for effect in second_actor.effects if effect.id == LEITURA_EFFECT]
    assert len(effects) == 1
    assert effects[0].magnitude == D("0.05")
    assert effects[0].remaining == 1
    assert "oraculo.leitura_dos_sinais" in _event(second, SINAL).path_triggers

    blocked = _combat(talents=(LEITURA_DOS_SINAIS,), arts=(SELO,))
    target = blocked.fighters["enemy"]
    target.ward_charges = 1
    target.ward_remaining = 2
    target.ward_applied_opportunity = target.opportunity
    result = act(blocked, SELO, target_id=target.id)
    event = _event(result, SELO)
    assert "oraculo.pressagio_offensive_criado" not in event.path_triggers
    assert "oraculo.leitura_dos_sinais" not in event.path_triggers
    assert not any(effect.id == LEITURA_EFFECT for effect in result.fighters["player"].effects)


def test_leitura_coexists_with_cutting_and_persistent_omens_on_selo():
    state = _combat(
        path="agoureiro",
        talents=(LEITURA_DOS_SINAIS, PRESSAGIO_CORTANTE, SINAL_PERSISTENTE),
        arts=(SELO,),
    )
    owner = state.fighters["player"]
    target = state.fighters["enemy"]
    owner.path_state.setdefault("omen_offensive", {})[target.id] = {
        "remaining": 3,
        "applied_opportunity": owner.opportunity,
    }

    resolved = act(state, SELO, target_id=target.id)
    resolved_owner = resolved.fighters["player"]
    event = _event(resolved, SELO)

    assert event.path_per_bonus == D(2)
    assert event.path_power_multiplier == D("1.16")
    assert event.class_resource_changes == (("omen_offensive", target.id, 1, 0),)
    assert resolved_owner.path_state["omen_offensive"][target.id]["remaining"] == 3
    assert sum(effect.id == LEITURA_EFFECT for effect in resolved_owner.effects) == 1
    assert "oraculo.pressagio_offensive_criado" in event.path_triggers
    assert "oraculo.leitura_dos_sinais" in event.path_triggers
    assert LEITURA_EFFECT not in {row[0] for row in event.actor_effect_facts}


def test_leitura_activates_when_barrier_absorbs_damage_but_debuff_applies():
    state = _combat(talents=(LEITURA_DOS_SINAIS,), arts=(SELO,))
    target = state.fighters["enemy"]
    _apply_barrier(
        target,
        applier_id="barrier-source",
        effect_definition_id="barrier.test",
        value=D(10000),
        duration=2,
        applied_opportunity=target.opportunity,
        round_number=state.round,
    )

    resolved = act(state, SELO, target_id=target.id)
    event = _event(resolved, SELO)
    owner = resolved.fighters["player"]
    effect = next(effect for effect in owner.effects if effect.id == LEITURA_EFFECT)

    assert event.effective_damage == 0
    assert "oraculo.pressagio_offensive_criado" in event.path_triggers
    assert "oraculo.leitura_dos_sinais" in event.path_triggers
    assert owner.path_state["omen_offensive"][target.id]["remaining"] == 2
    assert (effect.magnitude, effect.remaining) == (D("0.05"), 1)

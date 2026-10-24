from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

from asterion.domain.arts import (
    GUARDIAO_ART_IDS,
    LUMINAR_ART_IDS,
    ORACULO_ART_IDS,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Combat,
    DotState,
    Effect,
    Fighter,
    _apply_barrier,
    act,
    apply_effect,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, resolve_combat_stats
from asterion.domain.prologue import PROFILE

D = Decimal

FRAQUEZA_PREVISTA = "talent.oraculo.fraqueza_prevista"
MENTE_VELADA = "talent.oraculo.mente_velada"
SEQUENCIA_PROFETICA = "talent.oraculo.sequencia_profetica"
PUNICAO_DA_FRAQUEZA = "talent.luminar.punicao_da_fraqueza"
LUZ_PROTETORA = "talent.luminar.luz_protetora"
FLUXO_RESTAURADOR = "talent.luminar.fluxo_restaurador"

RUINA = ORACULO_ART_IDS["ruina_predita"]
AUGURIO = ORACULO_ART_IDS["augurio_favoravel"]
VEU_PREMONITORIO = ORACULO_ART_IDS["veu_premonitorio"]
EXPLOSAO_SOLAR = LUMINAR_ART_IDS["explosao_solar"]
AURORA_GUARDIA = GUARDIAO_ART_IDS["aurora_guardia"]


def _battle(
    character_class: str,
    *,
    path: str | None = None,
    arts: tuple[str, ...],
    talents: tuple[str, ...] = (),
    enemy_count: int = 1,
    ally_hps: tuple[D, ...] = (),
) -> Combat:
    stats = resolve_combat_stats(
        character_class, 60, "remanescente", selected_path=path
    )
    state = PROFILE.create(
        uuid4(), character_class.title(), character_class, "remanescente", stats.hp
    )
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET
    actor = state.fighters["player"]
    actor.level = 60
    actor.character_class = character_class
    actor.selected_path = path
    actor.talent_ids = talents
    actor.side = "player"
    actor.takes_turn = True
    actor.stats = replace(
        stats,
        hp=D(1000),
        attack=D(100),
        defense=D(100),
        agility=D(100),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    actor.hp = actor.stats.hp

    if enemy_count > 1:
        for index in range(1, enemy_count):
            enemy_stats = CombatStats(D(10000), D(100), D(0), D(0))
            state.fighters[f"enemy-{index}"] = Fighter(
                f"enemy-entity-{index}",
                f"Enemy {index}",
                60,
                enemy_stats,
                enemy_stats.hp,
                side="enemy",
                takes_turn=False,
                required_for_victory=False,
            )
    for fighter in state.fighters.values():
        if fighter.id == actor.id:
            continue
        if fighter.side != "enemy":
            continue
        fighter.stats = replace(
            fighter.stats,
            hp=D(10000),
            attack=D(100),
            defense=D(0),
            agility=D(0),
            per=D(0),
            crit=D(0),
            evasion=D(0),
            block=D(0),
        )
        fighter.hp = fighter.stats.hp
        fighter.takes_turn = False

    for index, hp in enumerate(ally_hps):
        ally_stats = CombatStats(D(1000), D(100), D(100), D(50))
        key = f"ally-{index}"
        state.fighters[key] = Fighter(
            key,
            f"Ally {index}",
            60,
            ally_stats,
            hp,
            character_class="sentinela",
            side="player",
            takes_turn=False,
            required_for_victory=False,
        )

    state.player_actions = class_player_actions(character_class, arts, path)
    state.enemy_actions = {
        "wait": Action("enemy.wait", "Wait", D(0), target_mode="self")
    }
    state.ai_cycle = ("wait",)
    if ally_hps:
        state.party_mode = True
        state.manual_sides = ("player",)
    return start_combat(state)


def _events(state: Combat, action_id: str):
    actor_id = state.fighters["player"].id
    return [
        event
        for event in state.events
        if event.actor_entity_id == actor_id and event.action == action_id
    ]


def test_fraqueza_prevista_uses_action_start_normal_debuff_per_target():
    state = _battle(
        "oraculo",
        arts=(RUINA,),
        talents=(FRAQUEZA_PREVISTA,),
        enemy_count=2,
    )
    marked = state.fighters["enemy"]
    marked.effects.append(
        Effect("enemy.attack.down", "attack", D("0.10"), 2, 0, kind="debuff")
    )
    dot_only = state.fighters["enemy-1"]
    state.dot_states[dot_only.id] = [
        DotState("poison", 1, 2, D(100), "enemy", stack_cap=3)
    ]

    result = act(state, RUINA, target_id=marked.id)
    event = _events(result, RUINA)[0]
    assert event.path_power_multiplier == D("1.03")
    assert "oraculo.fraqueza_prevista" in event.path_triggers

    no_debuff = _battle(
        "oraculo", arts=(RUINA,), talents=(FRAQUEZA_PREVISTA,)
    )
    no_debuff.fighters["enemy"].effects.append(
        Effect("fixed.boss.attack", "attack", D("0.10"), 2, 0,
               kind="debuff", fixed_mechanic=True)
    )
    no_debuff.dot_states[no_debuff.fighters["enemy"].id] = [
        DotState("poison", 1, 2, D(100), "enemy", stack_cap=3)
    ]
    event = _events(act(no_debuff, RUINA), RUINA)[0]
    assert event.path_power_multiplier == D(1)
    assert "oraculo.fraqueza_prevista" not in event.path_triggers


def test_mente_velada_reduces_only_removable_numeric_debuff_magnitude():
    state = _battle("oraculo", arts=(RUINA,), talents=(MENTE_VELADA,))
    target = state.fighters["player"]
    assert apply_effect(
        state,
        target,
        Effect("debuff.attack", "attack", D("0.10"), 2, 0, kind="debuff"),
    )
    applied = next(effect for effect in target.effects if effect.id == "debuff.attack")
    assert applied.magnitude == D("0.0940")
    assert applied.remaining == 2

    for effect in (
        Effect("debuff.fixed", "attack", D("0.10"), 2, 0, kind="debuff", fixed_mechanic=True),
        Effect("debuff.cc", "agility", D("0.10"), 2, 0, kind="debuff", hard_cc=True),
        Effect("debuff.immutable", "defense", D("0.10"), 2, 0, kind="debuff", unremovable=True),
        Effect("debuff.protected", "healing_received", D("0.10"), 2, 0,
               kind="debuff", protected=True),
    ):
        assert apply_effect(state, target, effect)
        applied = next(item for item in target.effects if item.id == effect.id)
        assert applied.magnitude == D("0.10")


def test_mente_velada_composes_once_with_alvorano_and_barrier_reduction():
    state = _battle("oraculo", arts=(RUINA,), talents=(MENTE_VELADA,))
    target = state.fighters["player"]
    target.race = "alvorano"
    _apply_barrier(
        target,
        applier_id="ally",
        effect_definition_id="barrier.veil",
        value=D(10),
        duration=2,
        applied_opportunity=target.opportunity,
        round_number=state.round,
        debuff_magnitude_reduction=D("0.20"),
    )
    effect = Effect("debuff.agility", "agility", D("0.10"), 2, 0, kind="debuff")
    assert apply_effect(state, target, effect)
    applied = next(item for item in target.effects if item.id == effect.id)
    assert applied.magnitude == D("0.10") * D("0.88") * D("0.80") * D("0.94")


def test_sequencia_profetica_triggers_once_on_defensive_omen_consumption():
    state = _battle(
        "oraculo",
        arts=(VEU_PREMONITORIO,),
        talents=(SEQUENCIA_PROFETICA,),
    )
    actor = state.fighters["player"]
    actor.path_state["omen_defensive"] = {
        actor.id: {"remaining": 2, "applied_opportunity": actor.opportunity}
    }

    result = act(state, VEU_PREMONITORIO, target_id=actor.id)
    actor = result.fighters["player"]
    assert actor.stat("agility") == D(103)
    assert any(
        effect.id == "class_mechanic.oraculo.sequencia_profetica.agility"
        and effect.magnitude == D("0.03")
        and effect.remaining == 1
        for effect in actor.effects
    )
    assert _events(result, VEU_PREMONITORIO)[0].class_resource_changes == (
        ("omen_defensive", actor.id, 1, 0),
    )
    assert actor.path_state["omen_defensive"].get(actor.id) is not None


def test_sequencia_profetica_also_triggers_on_offensive_omen_consumption():
    state = _battle(
        "oraculo",
        arts=(RUINA,),
        talents=(SEQUENCIA_PROFETICA,),
    )
    actor = state.fighters["player"]
    target_id = state.fighters["enemy"].id
    actor.path_state["omen_offensive"] = {
        target_id: {"remaining": 2, "applied_opportunity": actor.opportunity}
    }

    result = act(state, RUINA, target_id=target_id)
    actor = result.fighters["player"]
    assert actor.stat("agility") == D(103)
    assert any(
        effect.id == "class_mechanic.oraculo.sequencia_profetica.agility"
        and effect.remaining == 1
        for effect in actor.effects
    )
    assert _events(result, RUINA)[0].class_resource_changes == (
        ("omen_offensive", target_id, 1, 0),
    )


def test_punicao_da_fraqueza_requires_action_start_healing_reduction_per_target():
    state = _battle(
        "luminar",
        arts=(EXPLOSAO_SOLAR,),
        talents=(PUNICAO_DA_FRAQUEZA,),
        enemy_count=2,
    )
    state.fighters["enemy"].effects.append(
        Effect("enemy.healing.down", "healing_received", D("0.20"), 2, 0,
               kind="debuff")
    )
    result = act(state, EXPLOSAO_SOLAR)
    events = _events(result, EXPLOSAO_SOLAR)
    assert len(events) == 2
    assert {event.path_power_multiplier for event in events} == {D("1.03"), D(1)}
    assert sum("luminar.punicao_da_fraqueza" in event.path_triggers for event in events) == 1


def test_punicao_da_fraqueza_recognizes_burn_healing_penalty_but_not_unrelated_debuff():
    state = _battle(
        "luminar", arts=(EXPLOSAO_SOLAR,), talents=(PUNICAO_DA_FRAQUEZA,)
    )
    target = state.fighters["enemy"]
    target.effects.append(
        Effect("enemy.attack.down", "attack", D("0.20"), 2, 0, kind="debuff")
    )
    assert _events(act(state, EXPLOSAO_SOLAR), EXPLOSAO_SOLAR)[0].path_power_multiplier == D(1)

    burning = _battle(
        "luminar", arts=(EXPLOSAO_SOLAR,), talents=(PUNICAO_DA_FRAQUEZA,)
    )
    target = burning.fighters["enemy"]
    burning.dot_states[target.id] = [DotState("burn", 1, 2, D(100), "luminar")]
    event = _events(act(burning, EXPLOSAO_SOLAR), EXPLOSAO_SOLAR)[0]
    assert event.path_power_multiplier == D("1.03")


def test_punicao_da_fraqueza_ignores_expired_healing_reduction():
    state = _battle(
        "luminar", arts=(EXPLOSAO_SOLAR,), talents=(PUNICAO_DA_FRAQUEZA,)
    )
    state.fighters["enemy"].effects.append(
        Effect(
            "enemy.healing.expired",
            "healing_received",
            D("0.20"),
            0,
            0,
            kind="debuff",
        )
    )
    event = _events(act(state, EXPLOSAO_SOLAR), EXPLOSAO_SOLAR)[0]
    assert event.path_power_multiplier == D(1)
    assert "luminar.punicao_da_fraqueza" not in event.path_triggers


def test_luz_protetora_is_dynamic_and_uses_positive_active_barrier_only():
    state = _battle("luminar", arts=(EXPLOSAO_SOLAR,), talents=(LUZ_PROTETORA,))
    actor = state.fighters["player"]
    assert actor.stat("defense") == actor.stats.defense
    _apply_barrier(
        actor,
        applier_id="ally",
        effect_definition_id="barrier.ally",
        value=D(100),
        duration=2,
        applied_opportunity=actor.opportunity,
        round_number=state.round,
    )
    assert actor.stat("defense") == actor.stats.defense * D("1.05")
    actor.barrier_layers[0].value = D(0)
    assert actor.stat("defense") == actor.stats.defense


def test_fluxo_restaurador_buffs_each_effectively_healed_aurora_guardia_recipient_once():
    state = _battle(
        "luminar",
        path="guardiao",
        arts=(AURORA_GUARDIA,),
        talents=(FLUXO_RESTAURADOR,),
        ally_hps=(D(500), D(999)),
    )
    actor = state.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }

    result = act(state, AURORA_GUARDIA)
    events = _events(result, AURORA_GUARDIA)
    assert len(events) == 3
    healed = {event.target for event in events if event.effective_healing > 0}
    assert len(healed) == 2
    for fighter in result.fighters.values():
        effect_id = "class_mechanic.luminar.fluxo_restaurador.defense"
        effects = [effect for effect in fighter.effects if effect.id == effect_id]
        if fighter.id in healed:
            assert len(effects) == 1
            assert effects[0].magnitude == D("0.04")
            assert effects[0].remaining == 1
        else:
            assert not effects
    assert result.fighters["player"].path_state.get("luminar_state") is None

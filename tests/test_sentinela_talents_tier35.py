from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.domain.arts import SENTINEL_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    BarrierLayer,
    Effect,
    _apply_barrier,
    _barrier_received_multiplier,
    _end_turn,
    _grant_retaliation,
    _perform,
    act,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TALENTS_BY_CLASS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    _static_talent_secondary_modifier_totals,
    static_talent_secondary_modifiers,
    talent_points_at_level,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D("0")
HUNDRED = D("100")
OLHO = "talent.sentinela.olho_de_combate"
BARREIRA_DENSA = "talent.sentinela.barreira_densa"
CONTRAPESO = "talent.sentinela.contrapeso"
RETALIACAO_PERSISTENTE = "talent.sentinela.retaliacao_persistente"
GUARDA_PREPARADA = "talent.sentinela.guarda_preparada"
MURALHA_BREVE = SENTINEL_ART_IDS["muralha_breve"]
CONTRAPESO_EFFECT = "class_mechanic.sentinela.contrapeso.defense"


def _internal_stats(talents: tuple[str, ...], *, path: str | None = None):
    definitions = tuple(TALENT_DEFINITIONS[talent_id] for talent_id in talents)
    return _resolve_combat_stats_with_static_talent_modifiers(
        "sentinela",
        35,
        "remanescente",
        None,
        path,
        _static_talent_modifier_totals(definitions),
        _static_talent_secondary_modifier_totals(definitions),
    )


def _battle(
    *,
    talents: tuple[str, ...] = (),
    path: str | None = None,
    arts: tuple[str, ...] = (MURALHA_BREVE,),
    enemy_takes_turn: bool = False,
    enemy_evasion: Decimal = ZERO,
    defense: Decimal = HUNDRED,
):
    state = PROFILE.create(
        uuid4(), "Sentinela Nv35", "sentinela", "remanescente", D(1000)
    )
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET
    player = state.fighters["player"]
    player.level = 35
    player.character_class = "sentinela"
    player.selected_path = path
    player.talent_ids = talents
    player.stats = CombatStats(D(1000), D(100), defense, D(100), D(0), D(5))
    player.hp = D(1000)

    enemy = state.fighters["enemy"]
    enemy.character_class = "dummy"
    enemy.side = "enemy"
    enemy.takes_turn = enemy_takes_turn
    enemy.stats = CombatStats(D(10000), D(100), D(0), D(0), D(0), D(0), enemy_evasion)
    enemy.hp = D(10000)
    state.player_actions = {
        "attack": Action("attack", "Ataque Básico", D("0.01")),
        **class_player_actions("sentinela", arts, selected_path=path),
    }
    state.enemy_actions = {
        "hit": Action("enemy.test_hit", "Golpe inimigo", D("0.10"))
    }
    state.ai_cycle = ("hit",)
    state.ai_target_cycle = ("player",)
    return start_combat(state)


def _last_action(state, action_id: str, *, actor: str = "player"):
    return next(
        event
        for event in reversed(state.events)
        if event.actor == actor and event.action == action_id
    )


def _retaliation(state):
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=state.fighters["enemy"],
        source_event_id="test:defender",
    )


def _contrapeso_effect(actor):
    return next((effect for effect in actor.effects if effect.id == CONTRAPESO_EFFECT), None)


@pytest.mark.parametrize("path", (None, "bastiao", "devastador"))
def test_olho_de_combate_adds_two_static_crit_points_in_internal_composition(path):
    baseline = _internal_stats((), path=path)
    actual = _internal_stats((OLHO,), path=path)
    assert TALENT_DEFINITIONS[OLHO].crit_points == D(2)
    assert actual.crit == baseline.crit + D(2)
    assert (actual.hp, actual.attack, actual.defense, actual.agility, actual.per) == (
        baseline.hp,
        baseline.attack,
        baseline.defense,
        baseline.agility,
        baseline.per,
    )


def test_olho_de_combate_is_public_at_nv35_and_unavailable_below_it():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35})
    assert talent_points_at_level(35) == 7
    assert TALENT_DEFINITIONS[OLHO].level == 35
    for level in (34,):
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("sentinela", level, (OLHO,))
        with pytest.raises(TalentSelectionError):
            static_talent_secondary_modifiers("sentinela", level, (OLHO,))
    assert validate_active_talent_ids("sentinela", 35, (OLHO,)) == (OLHO,)
    assert validate_active_talent_ids("sentinela", 60, (OLHO,)) == (OLHO,)
    assert static_talent_secondary_modifiers("sentinela", 60, (OLHO,))
    assert len(tuple(item for item in TALENTS_BY_CLASS["sentinela"] if item.level == 35)) == 3


@pytest.mark.parametrize(("pvp", "expected_chance"), ((True, D("0.40")), (False, D("0.41"))))
def test_olho_de_combate_obeys_existing_pvp_crit_cap_without_capping_pve(
    monkeypatch, pvp, expected_chance
):
    equipment = EquipmentStatContribution(crit=D(34))
    definitions = (TALENT_DEFINITIONS[OLHO],)
    stats = _resolve_combat_stats_with_static_talent_modifiers(
        "sentinela",
        35,
        "remanescente",
        equipment,
        None,
        _static_talent_modifier_totals(definitions),
        _static_talent_secondary_modifier_totals(definitions),
    )
    assert stats.crit == D(41)
    seen = []

    def record_chance(_rng, chance, _purpose):
        seen.append(chance)
        return False

    monkeypatch.setattr("asterion.domain.combat.CombatRng.chance", record_chance)
    state = _battle()
    state.pvp_mode = pvp
    player = state.fighters["player"]
    player.stats = stats
    player.hp = stats.hp
    assert _perform(state, "player", "attack", target_id="enemy")
    assert seen == [expected_chance]


def test_barreira_densa_scales_real_self_muralha_barrier_once_and_survives_codec():
    state = _battle(talents=(BARREIRA_DENSA,))
    baseline = _battle()
    assert _barrier_received_multiplier(state, "player") == D("1.05")
    protected = act(state, MURALHA_BREVE)
    unmodified = act(baseline, MURALHA_BREVE)
    assert _last_action(protected, MURALHA_BREVE).barrier_value == D(73)
    assert _last_action(unmodified, MURALHA_BREVE).barrier_value == D(70)
    layer = protected.fighters["player"]._active_barrier_layers()[0]
    assert layer.identity == (protected.fighters["player"].id, MURALHA_BREVE)
    restored = decode(encode(protected), protected.id, protected.ruleset, protected.version)
    assert restored.fighters["player"]._active_barrier_layers()[0].value == D(73)


def test_barreira_densa_applies_to_recipient_not_to_sentinel_caster_or_other_classes():
    state = _battle(talents=(BARREIRA_DENSA,), arts=())
    sentinel = state.fighters["player"]
    ally = deepcopy(sentinel)
    ally.id = "ally"
    ally.name = "Aliado"
    ally.character_class = "dummy"
    ally.side = "player"
    ally.talent_ids = ()
    ally.barrier_layers = []
    ally.hp = ally.stats.hp
    ally.takes_turn = False
    state.fighters["ally"] = ally
    state.party_mode = True
    state.manual_sides = ("player",)
    outgoing = Action(
        "class_art.sentinela.barreira_teste",
        "Barreira de teste",
        D(0),
        target_mode="ally",
        target_barrier_coefficient=D("0.50"),
        target_barrier_duration=2,
    )
    state.player_actions[outgoing.id] = outgoing
    result = act(state, outgoing.id, target_id="ally")
    assert result.fighters["ally"].barrier == D(50)
    assert _barrier_received_multiplier(result, "ally") == D(1)
    assert _barrier_received_multiplier(result, "player") == D("1.05")

    forged = deepcopy(result)
    forged.fighters["ally"].character_class = "tecelao"
    forged.fighters["ally"].talent_ids = (BARREIRA_DENSA,)
    assert _barrier_received_multiplier(forged, "ally") == D(1)


def test_barreira_densa_respects_pvp_aggregate_cap_after_receiver_scaling():
    state = _battle(talents=(BARREIRA_DENSA,))
    sentinel = state.fighters["player"]
    sentinel.barrier_cap_fraction = D("0.35")
    _apply_barrier(
        sentinel,
        applier_id="ally",
        effect_definition_id="barrier.existing",
        value=345,
        duration=2,
        applied_opportunity=sentinel.opportunity,
        round_number=state.round,
    )
    result = act(state, MURALHA_BREVE)
    assert _last_action(result, MURALHA_BREVE).barrier_value == D(5)
    assert result.fighters["player"].barrier == D(350)


def test_barreira_densa_composes_with_guard_preparada_at_distinct_pipeline_stages():
    state = _battle(talents=(BARREIRA_DENSA, GUARDA_PREPARADA))
    sentinel = state.fighters["player"]
    sentinel.path_state["guard_prepared_barrier"] = {
        "remaining": 2,
        "applied_opportunity": sentinel.opportunity,
    }
    result = act(state, MURALHA_BREVE)
    event = _last_action(result, MURALHA_BREVE)
    assert event.barrier_power_multiplier == D("1.06")
    assert event.path_triggers.count("sentinela.guarda_preparada") == 1
    assert event.barrier_value == D(77)  # floor(70 × 1.06 × 1.05)
    assert "guard_prepared_barrier" not in result.fighters["player"].path_state


def test_barreira_densa_composes_as_recipient_stage_with_luminar_egide_densa():
    state = _battle(talents=(BARREIRA_DENSA,), arts=())
    luminar = state.fighters["player"]
    sentinel = deepcopy(luminar)
    sentinel.id = "sentinel-ally"
    sentinel.name = "Sentinela aliado"
    sentinel.character_class = "sentinela"
    sentinel.talent_ids = (BARREIRA_DENSA,)
    sentinel.side = "player"
    sentinel.barrier_layers = []
    sentinel.hp = sentinel.stats.hp
    sentinel.takes_turn = False
    state.fighters["ally"] = sentinel
    state.party_mode = True
    state.manual_sides = ("player",)
    luminar.character_class = "luminar"
    luminar.talent_ids = ("talent.luminar.egide_densa",)
    luminar_path_action = Action(
        "class_art.luminar.barreira_combinada_teste",
        "Barreira combinada",
        D(0),
        target_mode="ally",
        target_barrier_coefficient=D("3.50"),
        target_barrier_duration=2,
    )
    state.player_actions[luminar_path_action.id] = luminar_path_action
    result = act(state, luminar_path_action.id, target_id=sentinel.id)
    barrier_event = _last_action(result, luminar_path_action.id)
    assert barrier_event.barrier_value == D(382)  # floor(350 × 1.04 × 1.05)
    layer = result.fighters["ally"]._active_barrier_layers()[0]
    assert layer.identity == (luminar.id, luminar_path_action.id)


def test_contrapeso_does_not_trigger_on_retaliation_generation_or_refresh():
    state = _battle(talents=(CONTRAPESO, RETALIACAO_PERSISTENTE))
    sentinel = state.fighters["player"]
    _retaliation(state)
    assert sentinel.retaliation_charges == 1
    assert sentinel.retaliation_remaining == 2
    assert _contrapeso_effect(sentinel) is None
    _retaliation(state)
    assert sentinel.retaliation_charges == 1
    assert sentinel.retaliation_remaining == 2
    assert _contrapeso_effect(sentinel) is None
    assert [event.retaliation_event for event in state.mechanic_events] == [
        "granted",
        "refreshed",
    ]


def test_effective_defender_action_grants_retaliation_without_triggering_contrapeso():
    state = _battle(talents=(CONTRAPESO,), enemy_takes_turn=True, defense=ZERO)
    state.fighters["enemy"].stats = replace(
        state.fighters["enemy"].stats, attack=D(1000)
    )
    updated = act(state, "defend")
    sentinel = updated.fighters["player"]
    assert sentinel.retaliation_charges == 1
    assert any(event.retaliation_event == "granted" for event in updated.mechanic_events)
    assert _contrapeso_effect(sentinel) is None


def test_contrapeso_triggers_after_committed_retaliation_consumption_and_resolves_1t():
    state = _battle(
        talents=(CONTRAPESO, RETALIACAO_PERSISTENTE), defense=D(100)
    )
    _retaliation(state)
    assert _perform(state, "player", "attack", target_id="enemy")
    sentinel = state.fighters["player"]
    effect = _contrapeso_effect(sentinel)
    assert effect is not None
    assert (effect.stat, effect.magnitude, effect.remaining) == (
        "defense",
        D("0.04"),
        1,
    )
    assert sentinel.stat("defense") == D(104)
    assert sentinel.retaliation_charges == 0
    assert any(event.retaliation_event == "consumed" for event in state.mechanic_events)
    assert any(event.retaliation_event == "action_resolved" for event in state.mechanic_events)

    sentinel.opportunity += 1
    state.order = ("player",)
    state.turn_index = 0
    _end_turn(state)
    assert _contrapeso_effect(sentinel) is None
    assert sentinel.stat("defense") == D(100)


@pytest.mark.parametrize("target_result", ("dodged", "barrier"))
def test_contrapeso_follows_commit_even_when_postcommit_damage_is_avoided(target_result):
    state = _battle(talents=(CONTRAPESO,))
    target = state.fighters["enemy"]
    if target_result == "dodged":
        target.stats = replace(target.stats, evasion=D(100))
    else:
        target.barrier_layers.append(
            BarrierLayer(target.id, "test.full", D(10000), 2, target.opportunity)
        )
    _retaliation(state)
    updated = act(state, "attack", target_id="enemy")
    event = _last_action(updated, "attack")
    assert event.retaliation_used
    if target_result == "dodged":
        assert event.dodged
    else:
        assert event.effective_damage == 0
        assert event.barrier_absorbed > 0
    assert _contrapeso_effect(updated.fighters["player"]) is not None


def test_contrapeso_rejection_before_commit_preserves_retaliation_and_does_not_buff():
    state = _battle(talents=(CONTRAPESO,))
    _retaliation(state)
    rejected = act(state, "attack", target_id="missing")
    assert rejected is state
    assert rejected.fighters["player"].retaliation_charges == 1
    assert _contrapeso_effect(rejected.fighters["player"]) is None


def test_contrapeso_multihit_consumes_once_and_keeps_one_effect_after_reconnect():
    state = _battle(talents=(CONTRAPESO,))
    _retaliation(state)
    state.player_actions["multi"] = Action(
        "class_art.sentinela.test_multi", "Dois golpes", D("0.20"), hit_count=2
    )
    assert _perform(state, "player", "multi", target_id="enemy")
    actor = state.fighters["player"]
    assert actor.retaliation_charges == 0
    assert len([effect for effect in actor.effects if effect.id == CONTRAPESO_EFFECT]) == 1
    action_hits = [
        event
        for event in state.events
        if event.actor == "player" and event.action == "multi"
    ]
    assert len(action_hits) == 2
    assert sum(event.retaliation_used for event in action_hits) == 2
    assert sum(
        event.retaliation_event == "consumed" for event in state.mechanic_events
    ) == 1
    assert sum(
        event.retaliation_event == "action_resolved"
        for event in state.mechanic_events
    ) == 1
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    effect = _contrapeso_effect(restored.fighters["player"])
    assert effect is not None
    assert effect.remaining == 1
    assert effect.magnitude == D("0.04")
    assert _perform(restored, "player", "attack", target_id="enemy")
    assert len(
        [
            effect
            for effect in restored.fighters["player"].effects
            if effect.id == CONTRAPESO_EFFECT
        ]
    ) == 1


def test_second_consumption_renews_contrapeso_without_stacking():
    state = _battle(talents=(CONTRAPESO,))
    for _ in range(2):
        _retaliation(state)
        assert _perform(state, "player", "attack", target_id="enemy")
        assert state.fighters["player"].retaliation_charges == 0
        assert len(
            [
                effect
                for effect in state.fighters["player"].effects
                if effect.id == CONTRAPESO_EFFECT
            ]
        ) == 1
        effect = _contrapeso_effect(state.fighters["player"])
        assert effect is not None
        assert effect.magnitude == D("0.04")
        assert effect.remaining == 1


def test_contrapeso_composes_with_firme_sob_impacto_as_a_distinct_source():
    state = _battle(talents=(CONTRAPESO,), defense=D(100))
    actor = state.fighters["player"]
    actor.effects.append(
        Effect(
            "class_mechanic.sentinela.firme_sob_impacto.defense",
            "defense",
            D("0.05"),
            1,
            actor.opportunity,
            kind="buff",
        )
    )
    _retaliation(state)
    assert _perform(state, "player", "attack", target_id="enemy")
    assert actor.stat("defense") == D("109.2")
    assert _contrapeso_effect(actor) is not None
    assert any(
        effect.id == "class_mechanic.sentinela.firme_sob_impacto.defense"
        for effect in actor.effects
    )

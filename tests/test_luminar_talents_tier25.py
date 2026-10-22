from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4

import pytest

from asterion.domain.arts import LUMINAR_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Combat,
    Fighter,
    act,
    start_combat,
    use_combat_consumable,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    class_stats,
    effective_defense,
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
    static_talent_modifiers,
    static_talent_secondary_modifiers,
    talent_points_at_level,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

LUZ_PERFURANTE = "talent.luminar.luz_perfurante"
EGIDE_DENSA = "talent.luminar.egide_densa"
ALTERNANCIA_RADIANTE = "talent.luminar.alternancia_radiante"
JULGAMENTO_PRECISO = "talent.luminar.julgamento_preciso"
CONTRALUZ_PERSISTENTE = "talent.luminar.contraluz_persistente"
PROTECAO_TECIDA = "talent.tecelao.protecao_tecida"
FULGOR = LUMINAR_ART_IDS["fulgor"]
JULGAMENTO = LUMINAR_ART_IDS["julgamento"]
EGIDE_SOLAR = LUMINAR_ART_IDS["egide_solar"]
LUZ_RESTAURADORA = LUMINAR_ART_IDS["luz_restauradora"]
EXPLOSAO_SOLAR = LUMINAR_ART_IDS["explosao_solar"]


def _internal_stats(talent_ids, *, path=None, equipment=None):
    definitions = tuple(TALENT_DEFINITIONS[talent_id] for talent_id in talent_ids)
    return _resolve_combat_stats_with_static_talent_modifiers(
        "luminar",
        34,
        "remanescente",
        equipment,
        path,
        _static_talent_modifier_totals(definitions),
        _static_talent_secondary_modifier_totals(definitions),
    )


def _fighter(
    fighter_id,
    *,
    hp="10000",
    attack="20",
    defense="0",
    agility="0",
    side="enemy",
    character_class="",
    takes_turn=False,
):
    stats = CombatStats(D(hp), D(attack), D(defense), D(agility))
    return Fighter(
        fighter_id,
        fighter_id,
        34,
        stats,
        D(hp),
        character_class=character_class,
        side=side,
        takes_turn=takes_turn,
        required_for_victory=False,
    )


def _combat(
    *,
    arts=(EXPLOSAO_SOLAR,),
    path=None,
    talents=(),
    attack="100",
    enemy_count=2,
    enemy_evasion="0",
    pvp=False,
    ally_class=None,
    ally_talents=(),
):
    stats = resolve_combat_stats("luminar", 34, "remanescente", selected_path=path)
    player = PROFILE.create(uuid4(), "Luminar", "luminar", "remanescente", stats.hp)
    player.tutorial = None
    player.ruleset = CURRENT_COMBAT_RULESET
    actor = player.fighters["player"]
    actor.level = 34
    actor.character_class = "luminar"
    actor.selected_path = path
    actor.talent_ids = tuple(talents)
    actor.side = "player"
    actor.takes_turn = True
    actor.stats = replace(
        stats,
        hp=D("1000"),
        attack=D(attack),
        defense=D("100"),
        agility=D("100"),
        per=D(0),
        crit=D("5"),
        evasion=D(0),
        block=D(0),
    )
    actor.hp = actor.stats.hp

    fighters = {"player": actor}
    for index in range(enemy_count):
        enemy = _fighter(
            f"enemy-{index}",
            defense="0",
            agility="0",
            side="enemy",
        )
        enemy.stats = replace(enemy.stats, evasion=D(enemy_evasion))
        fighters[enemy.id] = enemy

    state = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        fighters,
        class_player_actions("luminar", arts, path),
        {"wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")},
        ("wait",),
        pvp_mode=pvp,
    )
    if ally_class is not None:
        ally = _fighter(
            "ally",
            hp="1000",
            attack="100",
            side="player",
            character_class=ally_class,
            takes_turn=False,
        )
        ally.id = "ally-entity"
        ally.talent_ids = tuple(ally_talents)
        state.fighters["ally"] = ally
        state.party_mode = True
        state.manual_sides = ("player",)
    return start_combat(state)


def _event(state, action_id):
    return next(
        event
        for event in state.events
        if event.actor_entity_id == state.fighters["player"].id
        and event.action == action_id
    )


def _luminar_state(state, kind, remaining=2):
    actor = state.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": kind,
        "remaining": remaining,
        "applied_opportunity": actor.opportunity,
    }


@pytest.mark.parametrize("path", (None, "guardiao", "inquisidor"))
def test_luz_perfurante_is_static_two_point_per_and_composes_once(path):
    equipment = EquipmentStatContribution(per=D("1.25"))
    baseline = _internal_stats((), path=path, equipment=equipment)
    actual = _internal_stats((LUZ_PERFURANTE,), path=path, equipment=equipment)

    assert TALENT_DEFINITIONS[LUZ_PERFURANTE].per_points == D(2)
    assert actual.per == baseline.per + D(2)
    assert (
        actual.hp,
        actual.attack,
        actual.defense,
        actual.agility,
        actual.crit,
        actual.evasion,
        actual.block,
    ) == (
        baseline.hp,
        baseline.attack,
        baseline.defense,
        baseline.agility,
        baseline.crit,
        baseline.evasion,
        baseline.block,
    )
    assert _internal_stats((LUZ_PERFURANTE,), path=path, equipment=equipment) == actual
    assert effective_defense(D(100), D(31)) == D(70)


def test_luz_perfurante_is_publicly_composable_at_nv25_only():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25})
    for level in (24,):
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("luminar", level, (LUZ_PERFURANTE,))
        with pytest.raises(TalentSelectionError):
            static_talent_secondary_modifiers("luminar", level, (LUZ_PERFURANTE,))
        with pytest.raises(TalentSelectionError):
            resolve_combat_stats("luminar", level, "remanescente", talent_ids=(LUZ_PERFURANTE,))
        with pytest.raises(TalentSelectionError):
            static_talent_modifiers("luminar", level, (EGIDE_DENSA,))
    assert talent_points_at_level(25) == 5
    assert validate_active_talent_ids("luminar", 25, (LUZ_PERFURANTE,)) == (LUZ_PERFURANTE,)
    assert static_talent_secondary_modifiers("luminar", 25, (LUZ_PERFURANTE,))[0] == D(2)
    assert static_talent_secondary_modifiers("luminar", 15, (JULGAMENTO_PRECISO,)) == (
        D(0), D(0), D(0), D(0)
    )


def test_egide_densa_strengthens_luminar_barrier_on_self_and_ally_only():
    own = _combat(arts=(EGIDE_SOLAR,), talents=(EGIDE_DENSA,))
    opportunity = own.fighters["player"].opportunity
    own_result = act(own, EGIDE_SOLAR)
    own_event = _event(own_result, EGIDE_SOLAR)
    own_actor = own_result.fighters["player"]
    assert own_event.barrier_value == D(93)  # floor(100 ATQ × 90% × 104%)
    assert own_event.barrier_duration == 2
    assert own_actor.cooldowns[EGIDE_SOLAR] == opportunity + 3
    assert "luminar.egide_densa" in own_event.path_triggers

    ally_state = _combat(
        arts=(LUZ_RESTAURADORA,),
        talents=(EGIDE_DENSA,),
        ally_class="tecelao",
        ally_talents=(PROTECAO_TECIDA,),
        attack="1000",
        enemy_count=1,
    )
    ally_result = act(
        ally_state,
        LUZ_RESTAURADORA,
        target_id="ally-entity",
    )
    ally_event = _event(ally_result, LUZ_RESTAURADORA)
    assert ally_event.barrier_value == D(382)  # floor(350 × 104% × 105%)
    assert ally_event.healed == 0
    assert ally_event.barrier_duration == 2
    assert ally_event.barrier_applied_source == (
        f"{ally_result.fighters['player'].id}:{LUZ_RESTAURADORA}"
    )
    assert "luminar.egide_densa" in ally_event.path_triggers


def test_egide_densa_does_not_boost_a_barrier_applied_by_another_class():
    state = _combat(
        arts=(LUZ_RESTAURADORA,),
        talents=(EGIDE_DENSA,),
        ally_class="sentinela",
        enemy_count=1,
    )
    ally = state.fighters["ally"]
    ally.takes_turn = True
    state.player_actions_by_fighter["ally"] = {
        "external_barrier": Action(
            "test.external_barrier",
            "Barreira externa",
            D(0),
            target_mode="ally",
            target_barrier_coefficient=D("0.50"),
            target_barrier_duration=2,
        )
    }
    state.order = ("ally", "player")
    state.turn_index = 0

    result = act(state, "external_barrier", actor_key="ally", target_id="player")
    event = next(event for event in result.events if event.action == "external_barrier")
    assert event.barrier_value == D(50)
    assert "luminar.egide_densa" not in event.path_triggers


def test_egide_densa_boosts_a_consumable_barrier_when_luminar_is_the_applier():
    state = _combat(talents=(EGIDE_DENSA,), enemy_count=1)
    actor = state.fighters["player"]
    actor.character_class = "luminar"
    actor.talent_ids = (EGIDE_DENSA,)
    actor.stats = replace(actor.stats, hp=D(1000))
    actor.hp = D(1000)

    result = use_combat_consumable(
        state,
        "consumable.protection.vde.ii",
        budget_limit=1,
    )
    event = next(
        event
        for event in result.events
        if event.action == "consumable:consumable.protection.vde.ii"
    )

    assert event.barrier_value == D(124)  # floor(1000 HP × 12% × 104%)
    assert event.barrier_applied_source == (
        f"{result.fighters['player'].id}:consumable.protecao"
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    ((None, D(40)), ("guardiao", D(41)), ("inquisidor", D(38))),
)
def test_egide_densa_composes_after_fulgor_path_power_and_keeps_floor(path, expected):
    state = _combat(
        arts=(LUZ_RESTAURADORA,),
        path=path,
        talents=(EGIDE_DENSA,),
        attack="100",
        enemy_count=1,
    )
    _luminar_state(state, "fulgor")
    result = act(state, LUZ_RESTAURADORA, target_id="player")
    event = _event(result, LUZ_RESTAURADORA)
    assert event.barrier_value == expected
    assert event.healed == 0  # the Talent changes Barrier, not healing
    assert event.class_resource_changes == (
        ("luminar_state", result.fighters["player"].id, 1, 0),
    )
    assert "luminar.fulgor_consumido" in event.path_triggers
    assert "luminar.julgamento_gerado" not in event.path_triggers


def test_egide_densa_respects_barrier_cap_and_codec_does_not_reapply_it():
    state = _combat(
        arts=(LUZ_RESTAURADORA,),
        talents=(EGIDE_DENSA,),
        attack="1000",
        enemy_count=1,
        pvp=True,
    )
    actor = state.fighters["player"]
    assert actor.barrier_cap_fraction == D("0.35")
    actor.barrier = D(330)
    actor.barrier_remaining = 2
    result = act(state, LUZ_RESTAURADORA, target_id=actor.id)
    updated = result.fighters["player"]
    event = _event(result, LUZ_RESTAURADORA)

    assert updated.barrier == D(350)
    assert event.barrier_value == D(20)
    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["player"].barrier == D(350)
    assert tuple(
        (layer.identity, layer.value, layer.remaining)
        for layer in restored.fighters["player"].barriers
    ) == tuple(
        (layer.identity, layer.value, layer.remaining)
        for layer in updated.barriers
    )


def test_fulgor_consumption_at_barrier_cap_still_grants_alternancia_radiante():
    state = _combat(
        arts=(LUZ_RESTAURADORA,),
        talents=(EGIDE_DENSA, ALTERNANCIA_RADIANTE),
        enemy_count=1,
        pvp=True,
    )
    actor = state.fighters["player"]
    actor.barrier = D(350)
    actor.barrier_remaining = 2
    _luminar_state(state, "fulgor")

    result = act(state, LUZ_RESTAURADORA, target_id=actor.id)
    event = _event(result, LUZ_RESTAURADORA)
    buff_id = "class_mechanic.luminar.alternancia_radiante.agility"

    assert event.barrier_value == 0
    assert "luminar.fulgor_consumido" in event.path_triggers
    assert "luminar.alternancia_radiante" in event.path_triggers
    assert "luminar_state" not in result.fighters["player"].path_state
    assert sum(effect.id == buff_id for effect in result.fighters["player"].effects) == 1


def test_alternancia_radiante_applies_after_fulgor_commit_and_is_codec_stable():
    state = _combat(
        arts=(LUZ_RESTAURADORA,),
        talents=(ALTERNANCIA_RADIANTE,),
        enemy_count=1,
    )
    _luminar_state(state, "fulgor")
    result = act(state, LUZ_RESTAURADORA, target_id="player")
    event = _event(result, LUZ_RESTAURADORA)
    buff_id = "class_mechanic.luminar.alternancia_radiante.agility"
    buffs = [effect for effect in result.fighters["player"].effects if effect.id == buff_id]

    assert "luminar.fulgor_consumido" in event.path_triggers
    assert "luminar.alternancia_radiante" in event.path_triggers
    assert len(buffs) == 1 and buffs[0].magnitude == D("0.04")
    assert buffs[0].remaining == 1
    assert buff_id not in event.actor_effect_ids
    assert "luminar_state" not in result.fighters["player"].path_state
    assert "luminar.julgamento_gerado" not in event.path_triggers

    restored = decode(encode(result), result.id, result.ruleset, result.version)
    restored_buffs = [
        effect for effect in restored.fighters["player"].effects if effect.id == buff_id
    ]
    assert len(restored_buffs) == 1 and restored_buffs[0].remaining == 1
    assert act(restored, LUZ_RESTAURADORA, target_id="player") is restored

    after_next_turn = act(result, "defend")
    assert not any(
        effect.id == buff_id for effect in after_next_turn.fighters["player"].effects
    )


def test_alternancia_radiante_generates_once_for_aoe_julgamento_and_no_replay():
    state = _combat(
        arts=(EXPLOSAO_SOLAR,),
        talents=(ALTERNANCIA_RADIANTE, JULGAMENTO_PRECISO),
        enemy_count=3,
    )
    _luminar_state(state, "julgamento")
    result = act(state, EXPLOSAO_SOLAR)
    actor = result.fighters["player"]
    events = [event for event in result.events if event.action == EXPLOSAO_SOLAR]
    buff_id = "class_mechanic.luminar.alternancia_radiante.agility"

    assert len(events) == 3
    assert sum("luminar.alternancia_radiante" in event.path_triggers for event in events) == 1
    assert all("luminar.julgamento_consumido" in event.path_triggers for event in events)
    assert all(event.path_crit_bonus == D(2) for event in events)
    assert len([effect for effect in actor.effects if effect.id == buff_id]) == 1
    assert "luminar_state" not in actor.path_state
    assert not any("luminar.fulgor_gerado" in event.path_triggers for event in events)

    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert len(
        [effect for effect in restored.fighters["player"].effects if effect.id == buff_id]
    ) == 1
    assert act(restored, EXPLOSAO_SOLAR) is restored


def test_alternancia_radiante_triggers_after_committed_evasion_but_not_on_invalid_target():
    state = _combat(
        arts=(JULGAMENTO,),
        talents=(ALTERNANCIA_RADIANTE,),
        enemy_count=1,
        enemy_evasion="100",
    )
    _luminar_state(state, "julgamento")
    invalid = act(state, JULGAMENTO, target_id="outside-encounter")
    assert invalid is state
    assert state.fighters["player"].path_state["luminar_state"]["kind"] == "julgamento"

    result = act(state, JULGAMENTO, target_id=state.fighters["enemy-0"].id)
    event = _event(result, JULGAMENTO)
    assert event.dodged
    assert "luminar.julgamento_consumido" in event.path_triggers
    assert "luminar.alternancia_radiante" in event.path_triggers
    buff_id = "class_mechanic.luminar.alternancia_radiante.agility"
    assert sum(effect.id == buff_id for effect in result.fighters["player"].effects) == 1


def test_alternancia_radiante_does_not_trigger_when_state_is_generated_or_renewed():
    generated = _combat(
        arts=(FULGOR,),
        talents=(ALTERNANCIA_RADIANTE,),
        enemy_count=1,
    )
    after_generation = act(generated, FULGOR, target_id="enemy-0")
    generated_event = _event(after_generation, FULGOR)
    assert "luminar.fulgor_gerado" in generated_event.path_triggers
    assert "luminar.alternancia_radiante" not in generated_event.path_triggers
    assert not any(
        effect.id == "class_mechanic.luminar.alternancia_radiante.agility"
        for effect in after_generation.fighters["player"].effects
    )

    renewed = _combat(
        arts=(EXPLOSAO_SOLAR,),
        talents=(ALTERNANCIA_RADIANTE, CONTRALUZ_PERSISTENTE),
        enemy_count=1,
    )
    _luminar_state(renewed, "fulgor", remaining=1)
    after_renewal = act(renewed, EXPLOSAO_SOLAR)
    renewed_event = _event(after_renewal, EXPLOSAO_SOLAR)
    assert "luminar.fulgor_gerado" in renewed_event.path_triggers
    assert "luminar.alternancia_radiante" not in renewed_event.path_triggers
    assert after_renewal.fighters["player"].path_state["luminar_state"]["remaining"] == 3


def test_all_three_tier25_effects_coexist_in_a_controlled_internal_context():
    state = _combat(
        arts=(LUZ_RESTAURADORA,),
        talents=(LUZ_PERFURANTE, EGIDE_DENSA, ALTERNANCIA_RADIANTE),
        enemy_count=1,
    )
    actor = state.fighters["player"]
    _luminar_state(state, "fulgor")
    result = act(state, LUZ_RESTAURADORA, target_id=actor.id)
    event = _event(result, LUZ_RESTAURADORA)
    updated = result.fighters["player"]

    assert event.barrier_value == D(40)  # floor(35 × 110% Fulgor × 104% Égide)
    assert "luminar.egide_densa" in event.path_triggers
    assert "luminar.alternancia_radiante" in event.path_triggers
    assert updated.path_state.get("luminar_state") is None
    assert _internal_stats((LUZ_PERFURANTE,)).per == class_stats("luminar", 34).per + D(2)

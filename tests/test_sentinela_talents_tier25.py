from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.arts import SENTINEL_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    BarrierLayer,
    Combat,
    CombatEvent,
    DotState,
    Effect,
    _apply_class_mechanic_buff,
    _end_turn,
    _finish_combat,
    _grant_retaliation,
    _perform,
    _record_devastador_charge,
    act,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, direct_damage
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENTS_BY_CLASS,
    TalentSelectionError,
    talent_points_at_level,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
D_0 = D("0")
D_100 = D("100")
D_1000 = D("1000")
D_01 = D("0.10")
PRESSAO = "talent.sentinela.pressao_de_fissuras"
FIRME = "talent.sentinela.firme_sob_impacto"
PERSISTENTE = "talent.sentinela.retaliacao_persistente"
PONTA_REVIDADA = "talent.sentinela.ponta_revidada"
GUARDA_PREPARADA = "talent.sentinela.guarda_preparada"
QUEBRA_POSTURA = SENTINEL_ART_IDS["quebra_postura"]
GOLPE_RECHACO = SENTINEL_ART_IDS["golpe_de_rechaco"]


def _battle(
    *,
    talents: tuple[str, ...] = (),
    path: str | None = None,
    enemy_attack: Decimal = D_1000,
    enemy_coefficient: Decimal = D_01,
    enemy_hits: int = 1,
    enemy_takes_turn: bool = False,
    player_hp: Decimal = D_1000,
    player_defense: Decimal = D_0,
    player_evasion: Decimal = D_0,
    player_barrier: Decimal = D_0,
    enemy_defense: Decimal = D_100,
    enemy_effects: tuple[Effect, ...] = (),
    arts: tuple[str, ...] = (),
) -> Combat:
    state = PROFILE.create(
        UUID("44444444-4444-4444-8444-444444444444"),
        "Sentinela Nv25",
        "sentinela",
        "remanescente",
        player_hp,
    )
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET
    player = state.fighters["player"]
    player.level = 25
    player.character_class = "sentinela"
    player.selected_path = path
    player.talent_ids = talents
    player.stats = CombatStats(
        player_hp,
        D(100),
        player_defense,
        D(100),
        per=D(0),
        crit=D(0),
        evasion=player_evasion,
        block=D(0),
    )
    player.hp = player_hp
    player.barrier = player_barrier
    player.barrier_remaining = 2 if player_barrier else 0
    player.barrier_source = "test:barrier" if player_barrier else ""

    enemy = state.fighters["enemy"]
    enemy.character_class = "dummy"
    enemy.side = "enemy"
    enemy.takes_turn = enemy_takes_turn
    enemy.stats = CombatStats(
        D(10000),
        enemy_attack,
        enemy_defense,
        D(0),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    enemy.hp = D(10000)
    enemy.effects = list(enemy_effects)
    state.player_actions = {
        "attack": Action("attack", "Ataque Básico", D("0.01")),
        **class_player_actions("sentinela", arts, selected_path=path),
    }
    state.enemy_actions = {
        "hit": Action(
            "enemy.test_hit",
            "Golpe inimigo",
            enemy_coefficient,
            hit_count=enemy_hits,
        )
    }
    state.ai_cycle = ("hit",)
    state.ai_target_cycle = ("player",)
    return start_combat(state)


def _last_event(state: Combat, action: str, *, actor: str = "player", target: str = "enemy"):
    return next(
        event
        for event in reversed(state.events)
        if event.actor == actor and event.action == action and event.target == target
    )


def _damage_effect(*, remaining: int = 2, fixed: bool = False, stat: str = "defense"):
    return Effect(
        "test.defense_reduction",
        stat,
        D("0.10"),
        remaining,
        0,
        kind="debuff",
        fixed_mechanic=fixed,
    )


def test_sentinel_tier25_catalog_and_public_authority():
    tier25 = tuple(t for t in TALENTS_BY_CLASS["sentinela"] if t.level == 25)
    assert tuple(t.talent_id for t in tier25) == (PRESSAO, FIRME, PERSISTENTE)
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25})
    assert talent_points_at_level(25) == 5
    assert talent_points_at_level(15) == 3
    assert validate_active_talent_ids("sentinela", 25, (PRESSAO,)) == (PRESSAO,)
    assert validate_talent_choices("sentinela", 25, ((1, FIRME),)) == ((1, FIRME),)
    assert validate_active_talent_ids("sentinela", 25, (PONTA_REVIDADA,)) == (
        PONTA_REVIDADA,
    )


def test_pressure_of_fissures_applies_direct_power_against_live_defense_debuff():
    state = _battle(
        talents=(PRESSAO,),
        enemy_effects=(_damage_effect(),),
    )
    state.player_actions["strike"] = Action(
        "test.sentinela.direct_strike", "Golpe direto", D(1)
    )
    assert _perform(state, "player", "strike", target_id="enemy")
    event = _last_event(state, "strike")
    assert event.path_power_multiplier == D("1.03")
    assert "sentinela.pressao_de_fissuras" in event.path_triggers
    expected = direct_damage(
        state.fighters["player"].stat("attack"),
        D("1.03"),
        state.fighters["enemy"].stat("defense"),
        state.fighters["player"].level,
    )
    unmodified = direct_damage(
        state.fighters["player"].stat("attack"),
        D(1),
        state.fighters["enemy"].stat("defense"),
        state.fighters["player"].level,
    )
    assert event.calculated_damage == expected > unmodified


@pytest.mark.parametrize(
    "effect, add_dot",
    (
        (_damage_effect(remaining=0), False),
        (_damage_effect(fixed=True), False),
        (_damage_effect(stat="attack"), False),
        (None, True),
        (None, False),
    ),
)
def test_pressure_does_not_trigger_without_valid_active_minus_def(effect, add_dot):
    state = _battle(talents=(PRESSAO,), enemy_effects=(effect,) if effect else ())
    if add_dot:
        state.dot_states[state.fighters["enemy"].id] = [
            DotState("bleed", 1, 2, D(100), "player")
        ]
    assert _perform(state, "player", "attack", target_id="enemy")
    assert _last_event(state, "attack").path_power_multiplier == D(1)


@pytest.mark.parametrize("preexisting", (False, True))
def test_quebra_postura_uses_only_pre_event_defense_reduction(preexisting):
    state = _battle(
        talents=(PRESSAO,),
        arts=(QUEBRA_POSTURA,),
        enemy_effects=(_damage_effect(),) if preexisting else (),
    )
    assert _perform(state, "player", QUEBRA_POSTURA, target_id="enemy")
    event = _last_event(state, QUEBRA_POSTURA)
    assert event.path_power_multiplier == (D("1.03") if preexisting else D(1))
    assert any(effect.id == "sentinel.quebra_postura" for effect in state.fighters["enemy"].effects)


def test_quebra_postura_resguardo_block_does_not_create_eligibility():
    state = _battle(talents=(PRESSAO,), arts=(QUEBRA_POSTURA,))
    enemy = state.fighters["enemy"]
    enemy.ward_charges = 1
    enemy.ward_remaining = 2
    assert _perform(state, "player", QUEBRA_POSTURA, target_id="enemy")
    assert _last_event(state, QUEBRA_POSTURA).path_power_multiplier == D(1)
    assert not any(effect.stat == "defense" for effect in enemy.effects)


def test_pressure_is_evaluated_per_target_and_per_action_for_aoe_and_multihit():
    state = _battle(talents=(PRESSAO,))
    second = replace(
        state.fighters["enemy"],
        id="enemy2",
        name="Alvo dois",
        effects=[],
        hp=D(10000),
        side="enemy",
    )
    state.fighters["enemy2"] = second
    state.fighters["enemy"].effects.append(_damage_effect())
    state.player_actions["sweep"] = Action(
        "class_art.sentinela.test_aoe",
        "Varredura",
        D("0.50"),
        target_mode="all_opponents",
    )
    assert _perform(state, "player", "sweep")
    assert _last_event(state, "sweep", target="enemy").path_power_multiplier == D("1.03")
    assert _last_event(state, "sweep", target="enemy2").path_power_multiplier == D(1)

    multi = _battle(talents=(PRESSAO,), enemy_effects=(_damage_effect(),))
    multi.player_actions["multi"] = Action(
        "class_art.sentinela.test_multi", "Dois golpes", D("0.20"), hit_count=2
    )
    assert _perform(multi, "player", "multi", target_id="enemy")
    hit_events = [
        event
        for event in multi.events
        if event.actor == "player" and event.action == "multi"
    ]
    assert len(hit_events) == 2
    assert [event.path_power_multiplier for event in hit_events] == [D("1.03"), D("1.03")]


@pytest.mark.parametrize(
    "loss, expected",
    ((79, False), (80, True), (81, True)),
)
def test_firme_sob_impacto_uses_real_hp_loss_and_exact_eight_percent(loss, expected):
    state = _battle(
        talents=(FIRME,),
        enemy_attack=D(1000),
        enemy_coefficient=D(loss) / D(1000),
        enemy_takes_turn=True,
    )
    updated = act(state, "attack", target_id="enemy")
    hit = _last_event(updated, "hit", actor="enemy", target="player")
    assert hit.effective_damage == loss
    effect = next(
        (
            effect
            for effect in updated.fighters["player"].effects
            if effect.id == "class_mechanic.sentinela.firme_sob_impacto.defense"
        ),
        None,
    )
    assert (effect is not None) is expected
    if effect is not None:
        assert effect.magnitude == D("0.05")
        assert effect.remaining == 1


def test_firme_sob_impacto_uses_max_hp_not_current_hp_and_aggregates_multihit():
    state = _battle(
        talents=(FIRME,),
        enemy_attack=D(1000),
        enemy_coefficient=D("0.04"),
        enemy_hits=2,
        enemy_takes_turn=True,
        player_hp=D(1000),
    )
    state.fighters["player"].hp = D(100)
    updated = act(state, "attack", target_id="enemy")
    hits = [event for event in updated.events if event.actor == "enemy" and event.action == "hit"]
    assert [event.effective_damage for event in hits] == [40, 40]
    assert updated.fighters["player"].hp == D(20)
    effects = [
        effect
        for effect in updated.fighters["player"].effects
        if effect.id == "class_mechanic.sentinela.firme_sob_impacto.defense"
    ]
    assert len(effects) == 1


@pytest.mark.parametrize(
    "barrier, expected_hp_loss, expected_buff",
    ((D(100), 0, False), (D(30), 70, False), (D(20), 80, True)),
)
def test_firme_sob_impacto_counts_hp_after_barrier_absorption(
    barrier, expected_hp_loss, expected_buff
):
    state = _battle(
        talents=(FIRME,),
        enemy_attack=D(1000),
        enemy_coefficient=D("0.10"),
        enemy_takes_turn=True,
        player_barrier=barrier,
    )
    updated = act(state, "attack", target_id="enemy")
    hit = _last_event(updated, "hit", actor="enemy", target="player")
    assert hit.effective_damage == expected_hp_loss
    assert any(
        effect.id == "class_mechanic.sentinela.firme_sob_impacto.defense"
        for effect in updated.fighters["player"].effects
    ) is expected_buff


def test_firme_sob_impacto_aggregates_distinct_barrier_sources_before_hp_threshold():
    state = _battle(
        talents=(FIRME,),
        enemy_attack=D(1000),
        enemy_coefficient=D("0.10"),
        enemy_takes_turn=True,
    )
    player = state.fighters["player"]
    player.barrier_layers.extend(
        (
            BarrierLayer("ally-a", "barrier-a", D(10), 2, player.opportunity),
            BarrierLayer("ally-b", "barrier-b", D(10), 2, player.opportunity),
        )
    )
    updated = act(state, "attack", target_id="enemy")
    hit = _last_event(updated, "hit", actor="enemy", target="player")
    assert hit.barrier_absorbed == 20
    assert hit.effective_damage == 80
    assert any("firme_sob_impacto" in effect.id for effect in updated.fighters["player"].effects)


def test_firme_sob_impacto_does_not_sum_loss_across_aoe_allies():
    state = _battle(
        talents=(FIRME,),
        enemy_attack=D(1000),
        enemy_coefficient=D("0.04"),
        enemy_takes_turn=True,
    )
    ally = replace(
        state.fighters["player"],
        id="ally",
        name="Aliado",
        character_class="dummy",
        talent_ids=(),
        side="player",
        hp=D(1000),
        stats=replace(state.fighters["player"].stats, hp=D(1000)),
    )
    state.fighters["ally"] = ally
    state.enemy_actions["hit"] = replace(
        state.enemy_actions["hit"], target_mode="all_opponents"
    )
    updated = act(state, "attack", target_id="enemy")
    hits = [
        event
        for event in updated.events
        if event.actor == "enemy" and event.action == "hit"
    ]
    assert {event.target: event.effective_damage for event in hits} == {
        "player": 40,
        "ally": 40,
    }
    assert not any(
        "firme_sob_impacto" in effect.id
        for effect in updated.fighters["player"].effects
    )


@pytest.mark.parametrize(
    "raw, expected_hp_loss, expected_buff",
    ((145, 79, False), (146, 80, True), (148, 81, True)),
)
def test_firme_sob_impacto_checks_real_damage_after_defender(raw, expected_hp_loss, expected_buff):
    state = _battle(
        talents=(FIRME,),
        enemy_attack=D(1000),
        enemy_coefficient=D(raw) / D(1000),
        enemy_takes_turn=True,
    )
    updated = act(state, "defend")
    hit = _last_event(updated, "hit", actor="enemy", target="player")
    assert hit.defender_prevented_damage > 0
    assert hit.effective_damage == expected_hp_loss
    assert any(
        effect.id == "class_mechanic.sentinela.firme_sob_impacto.defense"
        for effect in updated.fighters["player"].effects
    ) is expected_buff


def test_firme_sob_impacto_not_applied_after_lethal_hit_and_clears_at_combat_end():
    state = _battle(
        talents=(FIRME,),
        enemy_attack=D(1000),
        enemy_coefficient=D(1),
        enemy_takes_turn=True,
    )
    state.fighters["player"].hp = D(80)
    updated = act(state, "attack", target_id="enemy")
    assert updated.fighters["player"].hp == 0
    assert not any(
        effect.id == "class_mechanic.sentinela.firme_sob_impacto.defense"
        for effect in updated.fighters["player"].effects
    )

    survivor = _battle(talents=(FIRME,))
    _apply_class_mechanic_buff(
        survivor.fighters["player"],
        mechanic="sentinela.firme_sob_impacto",
        stat="defense",
        magnitude=D("0.05"),
        duration=1,
    )
    _finish_combat(survivor, "victory")
    assert not any(
        effect.id == "class_mechanic.sentinela.firme_sob_impacto.defense"
        for effect in survivor.fighters["player"].effects
    )


def test_firme_buff_roundtrips_in_combat_codec_and_expires_after_owner_turn():
    state = _battle(talents=(FIRME,), enemy_takes_turn=True)
    updated = act(state, "attack", target_id="enemy")
    player = updated.fighters["player"]
    effect = next(
        effect
        for effect in player.effects
        if effect.id.endswith("firme_sob_impacto.defense")
    )
    decoded = decode(encode(updated), updated.id, updated.ruleset, updated.version)
    expected_effect_id = effect.id
    restored = next(
        candidate
        for candidate in decoded.fighters["player"].effects
        if candidate.id == expected_effect_id
    )
    assert restored.remaining == effect.remaining == 1
    assert restored.applied_opportunity == effect.applied_opportunity
    # The buff is applied after the enemy's primary results and remains through
    # the Sentinel's next opportunity; its owner-turn boundary expires it.
    assert player.opportunity > restored.applied_opportunity
    player.opportunity = restored.applied_opportunity + 1
    updated.order = ("player",)
    updated.turn_index = 0
    _end_turn(updated)
    assert not any(e.id == restored.id for e in player.effects)


def test_firme_buff_is_not_applied_retroactively_to_the_triggering_hit():
    state_with_talent = _battle(
        talents=(FIRME,),
        enemy_attack=D(1000),
        enemy_coefficient=D("0.30"),
        enemy_takes_turn=True,
        player_defense=D(100),
    )
    state_without_talent = _battle(
        enemy_attack=D(1000),
        enemy_coefficient=D("0.30"),
        enemy_takes_turn=True,
        player_defense=D(100),
    )
    with_talent = act(state_with_talent, "attack", target_id="enemy")
    without_talent = act(state_without_talent, "attack", target_id="enemy")
    hit_with_talent = _last_event(with_talent, "hit", actor="enemy", target="player")
    hit_without_talent = _last_event(without_talent, "hit", actor="enemy", target="player")
    assert hit_with_talent.calculated_damage == hit_without_talent.calculated_damage
    assert with_talent.fighters["player"].stat("defense") == D(105)


def test_dot_tick_is_not_classified_as_an_enemy_action_for_firme():
    state = _battle(talents=(FIRME,))
    event_start = len(state.events)
    state.events.append(
        CombatEvent(
            len(state.events),
            state.round,
            "enemy",
            "dot:bleed:tick",
            state.fighters["player"].id,
            effective_damage=100,
            actor_entity_id=state.fighters["enemy"].id,
        )
    )
    _record_devastador_charge(state, "enemy", event_start, "dot:bleed:tick")
    assert not any("firme_sob_impacto" in e.id for e in state.fighters["player"].effects)


@pytest.mark.parametrize("path", (None, "bastiao", "devastador"))
def test_firme_coexists_with_sentinel_paths_and_devastador_charge(path):
    state = _battle(
        talents=(FIRME,),
        path=path,
        enemy_attack=D(1000),
        enemy_coefficient=D("0.10"),
        enemy_takes_turn=True,
    )
    updated = act(state, "attack", target_id="enemy")
    player = updated.fighters["player"]
    assert any("firme_sob_impacto" in effect.id for effect in player.effects)
    assert ("devastador_charge" in player.path_state) is (path == "devastador")


def test_firme_reapplication_keeps_one_five_percent_defense_effect():
    state = _battle(
        talents=(FIRME,),
        enemy_attack=D(1000),
        enemy_coefficient=D("0.10"),
        enemy_takes_turn=True,
    )
    once = act(state, "attack", target_id="enemy")
    twice = act(once, "attack", target_id="enemy")
    effects = [
        effect
        for effect in twice.fighters["player"].effects
        if effect.id == "class_mechanic.sentinela.firme_sob_impacto.defense"
    ]
    assert len(effects) == 1
    assert effects[0].magnitude == D("0.05")
    assert effects[0].remaining == 1


def test_firme_does_not_count_same_side_hp_loss():
    state = _battle(talents=(FIRME,))
    state.fighters["player"].hp -= D(100)
    state.events.append(
        CombatEvent(
            len(state.events),
            state.round,
            "player",
            "self_cost",
            state.fighters["player"].id,
            effective_damage=100,
            actor_entity_id=state.fighters["player"].id,
        )
    )
    _record_devastador_charge(state, "player", 0, "self_cost")
    assert not any("firme_sob_impacto" in effect.id for effect in state.fighters["player"].effects)


@pytest.mark.parametrize("talents, expected", (((), 1), ((PERSISTENTE,), 2)))
def test_retaliacao_persistente_sets_one_or_two_turn_window(talents, expected):
    state = _battle(talents=talents)
    sentinel = state.fighters["player"]
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=state.fighters["enemy"],
        source_event_id="test:defender",
    )
    assert sentinel.retaliation_charges == 1
    assert sentinel.retaliation_remaining == expected


def test_retaliation_refreshes_one_charge_and_expires_by_owner_opportunities():
    state = _battle(talents=(PERSISTENTE,))
    sentinel = state.fighters["player"]
    sentinel.opportunity = 4
    for event_id in ("first", "refresh"):
        _grant_retaliation(
            state,
            target_key="player",
            source_actor=state.fighters["enemy"],
            source_event_id=event_id,
        )
    assert sentinel.retaliation_charges == 1
    assert sentinel.retaliation_remaining == 2
    sentinel.opportunity = 5
    _end_turn(state)
    assert sentinel.retaliation_remaining == 1
    sentinel.opportunity = 6
    _end_turn(state)
    assert sentinel.retaliation_charges == 0
    assert sentinel.retaliation_remaining == 0


def test_non_owner_turns_do_not_consume_retaliation_duration():
    state = _battle(talents=(PERSISTENTE,))
    sentinel = state.fighters["player"]
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=state.fighters["enemy"],
        source_event_id="test:defender",
    )
    state.fighters["enemy"].opportunity += 5
    state.order = ("enemy",)
    state.turn_index = 0
    _end_turn(state)
    assert sentinel.retaliation_charges == 1
    assert sentinel.retaliation_remaining == 2


def test_defender_legitimately_grants_persistent_retaliation_and_dodge_does_not():
    state = _battle(talents=(PERSISTENTE,), enemy_takes_turn=True)
    updated = act(state, "defend")
    sentinel = updated.fighters["player"]
    assert sentinel.retaliation_charges == 1
    assert sentinel.retaliation_remaining == 2
    assert any(event.retaliation_event == "granted" for event in updated.mechanic_events)

    dodged = _battle(
        talents=(PERSISTENTE,),
        player_evasion=D(100),
        enemy_takes_turn=True,
    )
    after = act(dodged, "defend")
    assert _last_event(after, "hit", actor="enemy", target="player").dodged
    assert after.fighters["player"].retaliation_charges == 0


def test_retaliation_consumed_once_by_multihit_and_precommit_rejection_preserves_it():
    state = _battle(talents=(PERSISTENTE,))
    sentinel = state.fighters["player"]
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=state.fighters["enemy"],
        source_event_id="test:defender",
    )
    rejected = act(state, "attack", target_id="missing")
    assert rejected is state
    assert sentinel.retaliation_charges == 1
    state.player_actions["multi"] = Action(
        "class_art.sentinela.test_multi", "Três golpes", D("0.10"), hit_count=3
    )
    assert _perform(state, "player", "multi", target_id="enemy")
    hits = [event for event in state.events if event.actor == "player" and event.action == "multi"]
    consumed = [event for event in state.mechanic_events if event.retaliation_event == "consumed"]
    assert len(hits) == 3
    assert all(event.retaliation_used for event in hits)
    assert len(consumed) == 1
    assert sentinel.retaliation_charges == 0


@pytest.mark.parametrize("outcome", ("dodge", "barrier"))
def test_retaliation_is_consumed_after_commit_even_when_damage_does_not_reach_hp(outcome):
    state = _battle(talents=(PERSISTENTE,))
    target = state.fighters["enemy"]
    if outcome == "dodge":
        target.stats = replace(target.stats, evasion=D(100))
    else:
        target.barrier_layers.append(
            BarrierLayer(target.id, "test.full_barrier", D(1000), 2, target.opportunity)
        )
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=target,
        source_event_id="test:defender",
    )
    updated = act(state, "attack", target_id="enemy")
    hit = _last_event(updated, "attack")
    assert hit.retaliation_used
    if outcome == "dodge":
        assert hit.dodged
    else:
        assert hit.effective_damage == 0
        assert hit.barrier_absorbed > 0
    assert updated.fighters["player"].retaliation_charges == 0


def test_ending_combat_clears_persistent_retaliation():
    state = _battle(talents=(PERSISTENTE,))
    sentinel = state.fighters["player"]
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=state.fighters["enemy"],
        source_event_id="test:defender",
    )
    _finish_combat(state, "victory")
    assert sentinel.retaliation_charges == 0
    assert sentinel.retaliation_remaining == 0


@pytest.mark.parametrize("talent", (PERSISTENTE, PONTA_REVIDADA, GUARDA_PREPARADA))
def test_retaliation_codec_roundtrip_preserves_charge_duration_and_source(talent):
    state = _battle(talents=(talent,))
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=state.fighters["enemy"],
        source_event_id="test:defender",
    )
    restored = decode(encode(state), state.id, state.ruleset, state.version).fighters["player"]
    assert restored.retaliation_charges == 1
    assert restored.retaliation_remaining == (2 if talent == PERSISTENTE else 1)
    assert restored.retaliation_source_event_id == "test:defender"


def test_golpe_de_rechaco_retaliation_and_ponta_revidada_keep_distinct_per_bonuses():
    state = _battle(
        talents=(PONTA_REVIDADA, PERSISTENTE),
        arts=(GOLPE_RECHACO,),
        enemy_defense=D(100),
    )
    state.fighters["player"].stats = replace(
        state.fighters["player"].stats, per=D(0)
    )
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=state.fighters["enemy"],
        source_event_id="test:defender",
    )
    assert _perform(state, "player", GOLPE_RECHACO, target_id="enemy")
    event = _last_event(state, GOLPE_RECHACO)
    assert event.retaliation_used
    assert event.calculated_damage > 0
    assert event.path_per_bonus == D(10)  # Golpe de Rechaço's own +10 p.p.
    assert event.calculated_damage == direct_damage(
        state.fighters["player"].stat("attack"),
        D("1.45"),
        state.fighters["enemy"].stat("defense"),
        state.fighters["player"].level,
        penetration=D(14),
    )
    assert state.fighters["player"].retaliation_charges == 0


def test_nv25_talents_are_publicly_authorized_and_future_tiers_stay_closed():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25})
    assert talent_points_at_level(25) == 5
    assert validate_active_talent_ids("sentinela", 25, (PONTA_REVIDADA,)) == (
        PONTA_REVIDADA,
    )
    for talent_id in (PRESSAO, FIRME, PERSISTENTE):
        assert validate_active_talent_ids("sentinela", 25, (talent_id,)) == (talent_id,)
    future_id = next(t.talent_id for t in TALENTS_BY_CLASS["sentinela"] if t.level == 35)
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("sentinela", 60, (future_id,))

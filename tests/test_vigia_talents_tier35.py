from copy import deepcopy
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from asterion.domain.combat import (
    Action,
    ActionEffect,
    Combat,
    Fighter,
    _begin_turn,
    _deal_combat_damage,
    _end_turn,
    _finish_combat,
    _perform,
    _switch_aim_target,
    _tick_path_resources,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    resolve_combat_stats,
)
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TalentSelectionError,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ALVO_EXPOSTO = "talent.vigia.alvo_exposto"
RECUO_INSTINTIVO = "talent.vigia.recuo_instintivo"
VISAO_PERSISTENTE = "talent.vigia.visao_persistente"
AQUISICAO_RAPIDA = "talent.vigia.aquisicao_rapida"
MIRA_ESTAVEL = "talent.vigia.mira_estavel"
ANTECIPACAO = "talent.vigia.antecipacao"
POSTURA_VIGILANTE = "talent.vigia.postura_vigilante"
PONTO_FRACO = "talent.vigia.ponto_fraco"
COMBAT_ID = UUID("3645b722-052b-4c2a-9e0c-7fae49b73492")
RECUO_BUFF = "class_mechanic.vigia.recuo_instintivo.defense"


def _fighter(
    key: str,
    *,
    entity_id: str | None = None,
    name: str | None = None,
    side: str,
    character_class: str = "",
    talent_ids: tuple[str, ...] = (),
    path: str | None = None,
    hp: str = "10000",
    max_hp: str = "10000",
    attack: str = "200",
    defense: str = "0",
    evasion: str = "0",
    takes_turn: bool = False,
) -> Fighter:
    return Fighter(
        entity_id or key,
        name or key,
        34,
        CombatStats(
            D(max_hp),
            D(attack),
            D(defense),
            D("100"),
            evasion=D(evasion),
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
    hp: str = "10000",
    max_hp: str = "10000",
    defense: str = "100",
    enemy_attack: str = "1000",
    same_enemy_name: bool = False,
    pvp: bool = False,
) -> Combat:
    vigia = _fighter(
        "player",
        entity_id="vigia-entity",
        name="Vigia",
        side="player",
        character_class="vigia",
        talent_ids=talents,
        path=path,
        hp=hp,
        max_hp=max_hp,
        attack="200",
        defense=defense,
        takes_turn=True,
    )
    fighters = {"player": vigia}
    for index in range(enemy_count):
        key = f"enemy-{index}"
        fighters[key] = _fighter(
            key,
            entity_id=f"enemy-entity-{index}",
            name="Shared Name" if same_enemy_name else key,
            side="enemy",
            hp="10000",
            max_hp="10000",
            attack=enemy_attack,
            defense="100",
        )
    player_actions = {
        "attack": Action("attack", "Ataque Básico", D("0.2")),
        "multi": Action(
            "class_art.vigia.saraivada",
            "Saraivada",
            D("0.2"),
            hit_count=3,
        ),
        "aoe": Action(
            "class_art.vigia.voleio",
            "Voleio",
            D("0.2"),
            target_mode="all_opponents",
        ),
        "utility": Action(
            "class_art.vigia.utility",
            "Utilidade",
            D(0),
            target_mode="self",
            self_effects=(
                # This fixture is only to prove a non-direct action does not
                # receive Alvo Exposto's component-power increase.
                ActionEffect("utility.buff", "defense", D("0.05"), 1, "buff"),
            ),
        ),
    }
    enemy_actions = {
        "hit": Action("enemy.hit", "Golpe", D(1)),
        "multi_hit": Action(
            "enemy.multi_hit", "Golpes", D("0.2"), hit_count=3
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


def _event(state: Combat, action: str, *, actor: str = "player", target: str | None = None):
    return next(
        event
        for event in reversed(state.events)
        if event.action == action
        and event.actor == actor
        and (target is None or event.target == target)
    )


def _aim(state: Combat, target_key: str) -> dict | None:
    source = state.fighters["player"]
    entry = state.fighters[target_key].path_state.get("aim_from", {}).get(source.id)
    if not isinstance(entry, dict) or int(entry.get("remaining", 0)) <= 0:
        return None
    return entry


def _set_aim(
    state: Combat,
    target_key: str,
    stacks: int,
    *,
    remaining: int = 2,
    trigger: str = "direct",
) -> None:
    source = state.fighters["player"]
    state.fighters[target_key].path_state.setdefault("aim_from", {})[source.id] = {
        "stacks": stacks,
        "remaining": remaining,
        "applied_opportunity": source.opportunity,
        "trigger": trigger,
    }


def _recuo_effect(fighter: Fighter):
    return next((effect for effect in fighter.effects if effect.id == RECUO_BUFF), None)


@pytest.mark.parametrize("stacks", (2, 3, 4))
def test_alvo_exposto_is_action_start_target_mira_and_direct_power(stacks: int):
    path = "atirador" if stacks == 4 else None
    state = _battle(talents=(ALVO_EXPOSTO,), path=path)
    _set_aim(state, "enemy-0", stacks)

    assert _perform(state, "player", "attack", target_id="enemy-0")
    event = _event(state, "attack", target="enemy-entity-0")

    assert event.path_power_multiplier == D("1.03")
    assert event.path_final_damage_bonus == D(0)
    assert event.path_triggers.count("vigia.alvo_exposto") == 1


@pytest.mark.parametrize("stacks", (0, 1))
def test_alvo_exposto_does_not_qualify_below_two_valid_miras(stacks: int):
    state = _battle(talents=(ALVO_EXPOSTO,))
    if stacks:
        _set_aim(state, "enemy-0", stacks)

    assert _perform(state, "player", "attack", target_id="enemy-0")
    event = _event(state, "attack", target="enemy-entity-0")
    assert event.path_power_multiplier == D(1)
    assert "vigia.alvo_exposto" not in event.path_triggers


def test_alvo_exposto_uses_only_live_mira_owned_by_this_vigia():
    state = _battle(talents=(ALVO_EXPOSTO,))
    _set_aim(state, "enemy-0", 2, remaining=0)
    state.fighters["enemy-0"].path_state["aim_from"] = {
        "another-vigia": {
            "stacks": 3,
            "remaining": 2,
            "applied_opportunity": state.fighters["player"].opportunity,
        }
    }

    assert _perform(state, "player", "attack", target_id="enemy-0")
    event = _event(state, "attack", target="enemy-entity-0")
    assert event.path_power_multiplier == D(1)
    assert "vigia.alvo_exposto" not in event.path_triggers


def test_mira_created_by_this_action_does_not_retroactively_enable_alvo_exposto():
    state = _battle(talents=(ALVO_EXPOSTO, AQUISICAO_RAPIDA))

    assert _perform(state, "player", "attack", target_id="enemy-0")
    first = _event(state, "attack", target="enemy-entity-0")
    assert first.path_power_multiplier == D(1)
    assert _aim(state, "enemy-0")["stacks"] == 2

    assert _perform(state, "player", "attack", target_id="enemy-0")
    second = _event(state, "attack", target="enemy-entity-0")
    assert second.path_power_multiplier == D("1.03")


def test_alvo_exposto_uses_one_snapshot_for_all_saraivada_hits():
    eligible = _battle(talents=(ALVO_EXPOSTO,))
    _set_aim(eligible, "enemy-0", 2)
    assert _perform(eligible, "player", "multi", target_id="enemy-0")
    eligible_hits = [
        event
        for event in eligible.events
        if event.actor == "player" and event.action == "multi"
    ]
    assert len(eligible_hits) == 3
    assert [event.path_power_multiplier for event in eligible_hits] == [
        D("1.03"),
        D("1.03"),
        D("1.03"),
    ]

    one_mira = _battle(talents=(ALVO_EXPOSTO,))
    _set_aim(one_mira, "enemy-0", 1)
    assert _perform(one_mira, "player", "multi", target_id="enemy-0")
    hits = [
        event
        for event in one_mira.events
        if event.actor == "player" and event.action == "multi"
    ]
    assert [event.path_power_multiplier for event in hits] == [D(1)] * 3
    assert _aim(one_mira, "enemy-0")["stacks"] == 2


def test_alvo_exposto_is_evaluated_per_target_in_aoe():
    state = _battle(talents=(ALVO_EXPOSTO,), enemy_count=3)
    _set_aim(state, "enemy-0", 2)
    _set_aim(state, "enemy-1", 1)

    assert _perform(state, "player", "aoe", target_id="enemy-0")
    events = {
        event.target: event
        for event in state.events
        if event.actor == "player" and event.action == "aoe"
    }
    assert events["enemy-entity-0"].path_power_multiplier == D("1.03")
    assert events["enemy-entity-1"].path_power_multiplier == D(1)
    assert events["enemy-entity-2"].path_power_multiplier == D(1)


def test_alvo_exposto_coexists_with_mira_perfeita_without_reclassifying_its_bonuses():
    state = _battle(talents=(ALVO_EXPOSTO,), path="atirador", pvp=True)
    _set_aim(state, "enemy-0", 2)

    assert _perform(state, "player", "attack", target_id="enemy-0")
    event = _event(state, "attack", target="enemy-entity-0")
    assert event.path_power_multiplier == D("1.03")
    assert event.path_per_bonus == D(6)
    assert event.path_crit_bonus == D(0)


def test_alvo_exposto_respects_rastreador_two_miras_per_target_and_target_isolation():
    state = _battle(talents=(ALVO_EXPOSTO,), path="rastreador", enemy_count=3)
    _set_aim(state, "enemy-0", 2)
    _set_aim(state, "enemy-1", 1)

    assert _perform(state, "player", "aoe", target_id="enemy-0")
    events = {
        event.target: event
        for event in state.events
        if event.actor == "player" and event.action == "aoe"
    }
    assert events["enemy-entity-0"].path_power_multiplier == D("1.03")
    assert events["enemy-entity-1"].path_power_multiplier == D(1)
    assert events["enemy-entity-2"].path_power_multiplier == D(1)


def test_alvo_exposto_does_not_create_direct_damage_when_hit_is_fully_absorbed():
    state = _battle(talents=(ALVO_EXPOSTO,))
    _set_aim(state, "enemy-0", 2)
    target = state.fighters["enemy-0"]
    target.barrier = D(100000)
    target.barrier_remaining = 2

    assert _perform(state, "player", "attack", target_id="enemy-0")
    event = _event(state, "attack", target="enemy-entity-0")
    assert event.calculated_damage > 0
    assert event.effective_damage == 0
    assert event.path_power_multiplier == D("1.03")


def test_recuo_instintivo_is_inactive_at_41_percent_and_uses_exact_hp_ratio():
    above = _battle(talents=(RECUO_INSTINTIVO,), hp="410", max_hp="1000")
    assert _recuo_effect(above.fighters["player"]) is None
    assert "vigia_recuo_instintivo_used" not in above.fighters["player"].path_state

    non_multiple = _battle(
        talents=(RECUO_INSTINTIVO,), hp="400", max_hp="999"
    )
    assert _recuo_effect(non_multiple.fighters["player"]) is None


@pytest.mark.parametrize("hp", ("400", "399"))
def test_recuo_instintivo_triggers_at_or_below_40_percent_on_first_combat_observation(
    hp: str,
):
    state = _battle(talents=(RECUO_INSTINTIVO,), hp=hp, max_hp="1000")
    vigia = state.fighters["player"]
    marker = vigia.path_state["vigia_recuo_instintivo_used"]
    effect = _recuo_effect(vigia)

    assert marker["combat_id"] == str(state.id)
    assert marker["reason"] == "first_combat_observation"
    assert effect is not None and effect.magnitude == D("0.08")
    assert effect.remaining == 1
    assert vigia.stat("defense") == vigia.stats.defense * D("1.08")


def test_recuo_instintivo_triggers_after_real_hp_loss_and_not_on_barrier_absorption():
    state = _battle(talents=(RECUO_INSTINTIVO,), hp="500", max_hp="1000")
    vigia = state.fighters["player"]
    assert _recuo_effect(vigia) is None
    _deal_combat_damage(state, "player", D(100), source_key="enemy-0")
    assert vigia.hp == D(400)
    assert _recuo_effect(vigia) is not None

    shielded = _battle(talents=(RECUO_INSTINTIVO,), hp="500", max_hp="1000")
    protected = shielded.fighters["player"]
    protected.barrier = D(500)
    protected.barrier_remaining = 2
    _deal_combat_damage(shielded, "player", D(300), source_key="enemy-0")
    assert protected.hp == D(500)
    assert _recuo_effect(protected) is None
    assert "vigia_recuo_instintivo_used" not in protected.path_state


def test_recuo_instintivo_partial_barrier_uses_real_hp_after_absorption():
    state = _battle(talents=(RECUO_INSTINTIVO,), hp="500", max_hp="1000")
    vigia = state.fighters["player"]
    vigia.barrier = D(50)
    vigia.barrier_remaining = 2

    _deal_combat_damage(state, "player", D(100), source_key="enemy-0")
    assert vigia.hp == D(450)
    assert _recuo_effect(vigia) is None

    _deal_combat_damage(state, "player", D(50), source_key="enemy-0")
    assert vigia.hp == D(400)
    assert _recuo_effect(vigia) is not None


def test_recuo_instintivo_does_not_reduce_the_hit_that_crosses_the_threshold():
    with_talent = _battle(
        talents=(RECUO_INSTINTIVO,), hp="450", max_hp="1000", defense="100",
        enemy_attack="300",
    )
    baseline = _battle(hp="450", max_hp="1000", defense="100", enemy_attack="300")

    assert _perform(with_talent, "enemy-0", "hit", target_id="player")
    assert _perform(baseline, "enemy-0", "hit", target_id="player")
    actual = next(event for event in with_talent.events if event.action == "hit")
    unmodified = next(event for event in baseline.events if event.action == "hit")

    assert actual.calculated_damage == unmodified.calculated_damage
    assert with_talent.fighters["player"].hp <= D(400)
    assert _recuo_effect(with_talent.fighters["player"]) is not None


def test_recuo_instintivo_keeps_the_action_start_defense_snapshot_across_multihit():
    with_talent = _battle(
        talents=(RECUO_INSTINTIVO,), hp="500", max_hp="1000", defense="100",
        enemy_attack="1000",
    )
    baseline = _battle(hp="500", max_hp="1000", defense="100", enemy_attack="1000")

    assert _perform(with_talent, "enemy-0", "multi_hit", target_id="player")
    assert _perform(baseline, "enemy-0", "multi_hit", target_id="player")
    actual = [event for event in with_talent.events if event.action == "multi_hit"]
    unmodified = [event for event in baseline.events if event.action == "multi_hit"]

    assert len(actual) == len(unmodified) == 3
    assert [event.calculated_damage for event in actual] == [
        event.calculated_damage for event in unmodified
    ]
    assert with_talent.fighters["player"].hp <= D(400)
    assert _recuo_effect(with_talent.fighters["player"]) is not None


def test_recuo_instintivo_damage_buff_is_one_opportunity_and_does_not_rearm_after_healing():
    state = _battle(talents=(RECUO_INSTINTIVO,), hp="500", max_hp="1000")
    vigia = state.fighters["player"]
    _deal_combat_damage(state, "player", D(100), source_key="enemy-0")
    original_marker = deepcopy(vigia.path_state["vigia_recuo_instintivo_used"])
    assert _recuo_effect(vigia) is not None

    # Finish the Vigia's next opportunity. Its own effect expires at this
    # boundary; unrelated combatants do not consume the window.
    state.order = ("enemy-0", "player")
    state.turn_index = 0
    _end_turn(state)
    assert vigia.opportunity == 2
    assert _recuo_effect(vigia) is not None
    state.turn_index = 1
    _end_turn(state)
    assert _recuo_effect(vigia) is None
    assert vigia.path_state["vigia_recuo_instintivo_used"] == original_marker

    vigia.hp = D(700)
    _deal_combat_damage(state, "player", D(400), source_key="enemy-0")
    assert vigia.hp <= D(400)
    assert _recuo_effect(vigia) is None
    assert vigia.path_state["vigia_recuo_instintivo_used"] == original_marker


def test_recuo_instintivo_coexists_with_static_postura_and_antecipacao_independently():
    state = _battle(
        talents=(RECUO_INSTINTIVO, POSTURA_VIGILANTE, ANTECIPACAO),
        hp="600",
        max_hp="1000",
        defense="102",
        enemy_attack="100",
    )
    vigia = state.fighters["player"]

    assert _perform(state, "enemy-0", "hit", target_id="player")
    event = next(event for event in state.events if event.action == "hit")
    assert vigia.path_state["vigia_antecipacao_used"] is True
    assert event.calculated_damage > 0
    assert "vigia_recuo_instintivo_used" not in vigia.path_state
    vigia.hp = D(425)
    _deal_combat_damage(state, "player", D(25), source_key="enemy-0")
    assert vigia.hp == D(400)
    assert "vigia_recuo_instintivo_used" in vigia.path_state
    assert _recuo_effect(vigia) is not None
    assert vigia.stat("defense") == vigia.stats.defense * D("1.08")


def test_recuo_instintivo_codec_reconnect_and_new_combat_are_scoped():
    state = _battle(talents=(RECUO_INSTINTIVO,), hp="500", max_hp="1000")
    vigia = state.fighters["player"]
    _deal_combat_damage(state, "player", D(100), source_key="enemy-0")
    marker = deepcopy(vigia.path_state["vigia_recuo_instintivo_used"])
    effect = deepcopy(_recuo_effect(vigia))

    restored = decode(encode(state), state.id, state.ruleset, state.version)
    restored_vigia = restored.fighters["player"]
    assert restored_vigia.path_state["vigia_recuo_instintivo_used"] == marker
    assert _recuo_effect(restored_vigia) == effect
    _begin_turn(restored)
    assert restored_vigia.path_state["vigia_recuo_instintivo_used"] == marker
    assert _recuo_effect(restored_vigia).remaining == 1

    next_combat = deepcopy(restored)
    next_combat.id = uuid4()
    next_combat.version = 0
    next_combat.result = ""
    next_combat.events = []
    next_combat.mechanic_events = []
    next_combat.order = ()
    next_combat.turn_index = 0
    restarted = start_combat(next_combat)
    new_marker = restarted.fighters["player"].path_state[
        "vigia_recuo_instintivo_used"
    ]
    assert new_marker["combat_id"] == str(restarted.id)
    assert new_marker["combat_id"] != marker["combat_id"]
    assert _recuo_effect(restarted.fighters["player"]) is not None


def test_recuo_instintivo_does_not_save_a_defeated_vigia_retroactively():
    state = _battle(
        talents=(RECUO_INSTINTIVO,), hp="500", max_hp="1000", enemy_attack="1000"
    )
    vigia = state.fighters["player"]
    assert _perform(state, "enemy-0", "hit", target_id="player")
    assert vigia.hp == 0
    assert state.result == "defeat"
    assert _recuo_effect(vigia) is None


def test_visao_persistente_keeps_exactly_one_previous_target_mira_for_one_turn():
    state = _battle(talents=(VISAO_PERSISTENTE,), enemy_count=2)
    vigia = state.fighters["player"]
    _set_aim(state, "enemy-0", 3)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"

    assert _perform(state, "player", "attack", target_id="enemy-1")
    preserved = _aim(state, "enemy-0")
    assert preserved is not None
    assert (preserved["stacks"], preserved["remaining"]) == (1, 1)
    assert preserved["trigger"] == "visao_persistente"
    assert _aim(state, "enemy-1")["stacks"] == 1

    vigia.opportunity += 1
    _tick_path_resources(state, "player")
    assert _aim(state, "enemy-0") is None


def test_visao_persistente_without_existing_mira_does_not_create_one():
    state = _battle(talents=(VISAO_PERSISTENTE,), enemy_count=2)
    state.fighters["player"].path_state["aim_current_target_id"] = "enemy-entity-0"

    _switch_aim_target(state, "player", "enemy-entity-1")
    assert _aim(state, "enemy-0") is None
    assert state.fighters["player"].path_state["aim_current_target_id"] == "enemy-entity-1"


def test_visao_persistente_new_switch_replaces_the_previous_target_window():
    state = _battle(talents=(VISAO_PERSISTENTE,), enemy_count=3)
    vigia = state.fighters["player"]
    _set_aim(state, "enemy-0", 3)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"

    _switch_aim_target(state, "player", "enemy-entity-1")
    assert (_aim(state, "enemy-0")["stacks"], _aim(state, "enemy-0")["remaining"]) == (
        1,
        1,
    )
    _set_aim(state, "enemy-1", 2)
    _switch_aim_target(state, "player", "enemy-entity-2")

    assert _aim(state, "enemy-0") is None
    assert (_aim(state, "enemy-1")["stacks"], _aim(state, "enemy-1")["remaining"]) == (
        1,
        1,
    )
    assert _aim(state, "enemy-2") is None


def test_visao_persistente_a_to_b_to_a_keeps_one_mark_without_refreshing_it():
    state = _battle(talents=(VISAO_PERSISTENTE,), enemy_count=2)
    vigia = state.fighters["player"]
    _set_aim(state, "enemy-0", 3)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"

    _switch_aim_target(state, "player", "enemy-entity-1")
    preserved = deepcopy(_aim(state, "enemy-0"))
    assert preserved["stacks"] == 1 and preserved["remaining"] == 1

    _switch_aim_target(state, "player", "enemy-entity-0")
    assert _aim(state, "enemy-0") == preserved
    assert _aim(state, "enemy-1") is None

    _switch_aim_target(state, "player", "enemy-entity-1")
    assert _aim(state, "enemy-0")["stacks"] == 1
    assert _aim(state, "enemy-0")["remaining"] == 1


def test_visao_persistente_same_target_retry_is_idempotent_and_does_not_refresh_window():
    state = _battle(talents=(VISAO_PERSISTENTE,), enemy_count=2)
    vigia = state.fighters["player"]
    _set_aim(state, "enemy-0", 2)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"
    _switch_aim_target(state, "player", "enemy-entity-1")
    previous = deepcopy(_aim(state, "enemy-0"))

    _switch_aim_target(state, "player", "enemy-entity-1")
    assert _aim(state, "enemy-0") == previous
    assert _aim(state, "enemy-1") is None


def test_visao_persistente_does_not_override_atirador_caps_or_mira_estavel_duration():
    state = _battle(
        talents=(VISAO_PERSISTENTE, MIRA_ESTAVEL), path="atirador", enemy_count=2
    )
    vigia = state.fighters["player"]
    _set_aim(state, "enemy-0", 4, remaining=3)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"

    _switch_aim_target(state, "player", "enemy-entity-1")
    preserved = _aim(state, "enemy-0")
    assert preserved is not None
    assert (preserved["stacks"], preserved["remaining"]) == (1, 1)


def test_visao_persistente_is_id_specific_and_does_not_create_a_mark_on_same_name_target():
    state = _battle(
        talents=(VISAO_PERSISTENTE,), enemy_count=2, same_enemy_name=True
    )
    vigia = state.fighters["player"]
    _set_aim(state, "enemy-0", 2)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"

    assert _perform(state, "player", "attack", target_id="enemy-1")
    assert _aim(state, "enemy-0")["stacks"] == 1
    assert _aim(state, "enemy-1")["stacks"] == 1
    assert state.fighters["enemy-0"].name == state.fighters["enemy-1"].name
    assert state.fighters["enemy-0"].id != state.fighters["enemy-1"].id


def test_visao_persistente_reconnect_keeps_mark_identity_and_remaining_window():
    state = _battle(talents=(VISAO_PERSISTENTE,), enemy_count=2)
    vigia = state.fighters["player"]
    _set_aim(state, "enemy-0", 2)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"
    assert _perform(state, "player", "attack", target_id="enemy-1")
    before = deepcopy(_aim(state, "enemy-0"))

    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert _aim(restored, "enemy-0") == before
    _switch_aim_target(restored, "player", "enemy-entity-1")
    assert _aim(restored, "enemy-0") == before


def test_visao_persistente_does_not_change_rastreador_multitarget_behavior():
    state = _battle(talents=(VISAO_PERSISTENTE,), path="rastreador", enemy_count=4)
    vigia = state.fighters["player"]
    for key in ("enemy-0", "enemy-1", "enemy-2"):
        _set_aim(state, key, 2)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"

    _switch_aim_target(state, "player", "enemy-entity-3")
    assert all(_aim(state, key)["stacks"] == 2 for key in ("enemy-0", "enemy-1", "enemy-2"))
    assert _aim(state, "enemy-3") is None


def test_visao_persistente_does_not_restore_aquisicao_rapida_quota_after_expiry():
    state = _battle(
        talents=(VISAO_PERSISTENTE, AQUISICAO_RAPIDA), enemy_count=2
    )
    vigia = state.fighters["player"]
    _set_aim(state, "enemy-0", 2)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"
    vigia.path_state["aim_acquisition_used"] = {"enemy-entity-0": True}

    _switch_aim_target(state, "player", "enemy-entity-1")
    vigia.opportunity += 1
    _tick_path_resources(state, "player")
    assert _aim(state, "enemy-0") is None
    assert vigia.path_state["aim_acquisition_used"]["enemy-entity-0"] is True

    assert _perform(state, "player", "attack", target_id="enemy-0")
    assert _aim(state, "enemy-0")["stacks"] == 1
    assert vigia.path_state["aim_acquisition_used"]["enemy-entity-0"] is True


def test_visao_persistente_is_cleared_at_combat_end():
    state = _battle(talents=(VISAO_PERSISTENTE,), enemy_count=2)
    vigia = state.fighters["player"]
    _set_aim(state, "enemy-0", 2)
    vigia.path_state["aim_current_target_id"] = "enemy-entity-0"
    _switch_aim_target(state, "player", "enemy-entity-1")

    _finish_combat(state, "victory")
    assert _aim(state, "enemy-0") is None
    assert "aim_current_target_id" not in vigia.path_state


def test_vigia_nv35_and_nv55_are_eligible_at_their_required_levels():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    for talent_id in (ALVO_EXPOSTO, RECUO_INSTINTIVO, VISAO_PERSISTENTE):
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("vigia", 34, (talent_id,))
        assert validate_active_talent_ids("vigia", 35, (talent_id,)) == (talent_id,)
        assert validate_active_talent_ids("vigia", 60, (talent_id,)) == (talent_id,)
        assert resolve_combat_stats("vigia", 60, "remanescente", talent_ids=(talent_id,))
    nv55_id = "talent.vigia.disparo_implacavel"
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("vigia", 54, (nv55_id,))
    assert validate_active_talent_ids("vigia", 55, (nv55_id,)) == (nv55_id,)

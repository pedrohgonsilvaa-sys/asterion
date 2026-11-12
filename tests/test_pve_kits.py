from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4

import pytest

from asterion.domain import oaths, world_events
from asterion.domain.combat import (
    Effect,
    _enemy_action,
    _lowest_hp_target,
    act,
)
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.pve_kits import PREPARED, SIMPLE, KitAction, kit_creature
from asterion.domain.road import (
    ARCHETYPE,
    VARIANTS,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)
from asterion.infrastructure.db import combat_codec

EVENTS = world_events.WORLD_EVENT_CATALOG
TRIALS = oaths.OATH_TRIAL_CATALOG


def _creatures():
    for event in EVENTS:
        for phase in event.phases:
            yield "event", phase.creature
    for trial in TRIALS:
        for encounter in trial.encounters:
            yield "oath", encounter.creature


def _creature(creature_id):
    return next(creature for _, creature in _creatures() if creature.creature_id == creature_id)


def _party_combat(creature, hps):
    members = tuple(
        PlayerCombatantSpec(
            f"m{index}",
            f"character-{index}",
            f"Membro {index}",
            "sentinela",
            "remanescente",
            20,
            D(hp),
            EquipmentConfigurationSnapshot(0),
            (),
        )
        for index, hp in enumerate(hps)
    )
    state = create_creature_party_combat(
        uuid4(),
        members[0].name,
        "sentinela",
        "remanescente",
        D(hps[0]),
        (CreatureCombatantSpec(creature, 20, "enemy"),),
        player_level=20,
        party=members,
    )
    for index, hp in enumerate(hps):
        state.fighters[f"m{index}" if len(hps) > 1 else "player"].hp = D(hp)
    return state


def test_catalogs_have_six_entries_with_the_fixed_structure():
    assert len(EVENTS) == 6 and len(TRIALS) == 6
    assert [event.reference_level for event in EVENTS] == [10, 20, 30, 40, 50, 60]
    assert all(event.attuned for event in EVENTS)
    ids = [creature.creature_id for _, creature in _creatures()]
    assert len(ids) == len(set(ids)) == 36
    for event in EVENTS:
        assert all(phase.creature.category == "boss" for phase in event.phases)


def test_every_kit_is_a_priority_list_with_a_fallback_and_lowest_hp_targeting():
    for _, creature in _creatures():
        assert creature.target_policy == "lowest_hp"
        assert creature.archetype in ARCHETYPE
        fallback = creature.actions[-1]
        assert creature.ai == (fallback[0],)
        assert fallback[9] is None
        assert creature.ai_priority == tuple(action[0] for action in creature.actions[:-1])


def test_coefficients_are_the_band_midpoints():
    seen = {}
    for _, creature in _creatures():
        for action in creature.actions:
            seen.setdefault(action[2], action[1])
    assert set(seen) <= {D("1.00"), D("1.325"), D("1.70"), D("0.825"), D("0.85"), D("0.65"), D(0)}


def test_agile_variant_applies_only_to_the_stats():
    phase = EVENTS[0].phase(1)
    assert phase.variant == "agile" and phase.creature.archetype == "predator"
    plain = world_events.boss_stats(phase.creature, 10, 1)
    agile = world_events.boss_stats(phase.creature, 10, 1, "agile")
    assert agile.agility > plain.agility and agile.hp < plain.hp
    assert VARIANTS["agile"].attack == 1
    trial = TRIALS[2].encounter(1)
    assert trial.variant == "agile"
    assert oaths.encounter_stats(trial.creature, 20, 2, "agile").agility > oaths.encounter_stats(
        trial.creature, 20, 2
    ).agility


def test_event_aoe_has_no_group_condition_and_trancador_falls_back_to_arrasto():
    for kind, creature in _creatures():
        if kind == "event":
            assert all(
                "min_living_opponents" not in dict(extras) for _, extras in creature.action_extras
            )
    trancador = EVENTS[1].phase(2).creature
    assert trancador.ai == ("arrasto_cruzado",)
    assert trancador.actions[-1][4] == D("0.10") and trancador.actions[-1][10] == "defense"
    assert "arrasto_cruzado" not in dict(trancador.action_extras) or not any(
        key == "skip_if_target_effect_active"
        for key, _ in dict(trancador.action_extras)["arrasto_cruzado"]
    )


def test_single_target_hits_the_lowest_hp_without_the_effect():
    creature = _creature("oath.ultima_guarda.sentinela_portao")
    state = _party_combat(creature, (300, 120, 200))
    strike = state.enemy_actions["golpe_contencao"]
    assert strike.effect_id == strike.skip_if_target_effect_active == "pve.defense_down_10"
    assert _lowest_hp_target(state, "enemy", strike) == state.fighters["m1"].id
    state.fighters["m1"].effects.append(
        Effect("pve.defense_down_10", "defense", D("0.10"), 2, 0)
    )
    assert _lowest_hp_target(state, "enemy", strike) == state.fighters["m2"].id


def test_group_aoe_needs_two_targets_without_the_effect():
    creature = _creature("oath.ultima_guarda.guarda_relevo")
    state = _party_combat(creature, (300, 300))
    enemy = state.fighters["enemy"]
    enemy.cooldowns = {"chamado_revezamento": 99, "interdicao": 99}
    for fighter in state.fighters.values():
        fighter.effects.clear()
    state.prepared_action = None
    assert _enemy_action(state) == "linha_vigilia"
    state.fighters["m0"].effects.append(
        Effect("pve.attack_down_10", "attack", D("0.10"), 2, 0)
    )
    assert _enemy_action(state) == "marcar_chao"


def test_multi_hit_and_dot_extras_reach_the_engine():
    state = _party_combat(_creature("oath.preco.credor_fim"), (300, 300))
    multi = state.enemy_actions["cobranca_fracionada"]
    assert multi.hit_count == 2 and multi.coefficient == D("0.65")
    phase = EVENTS[0].phase(2).creature
    single = _party_combat(phase, (300,))
    burn = single.enemy_actions["golpe_incandescente"]
    assert burn.native_dot_kind == "burn" and burn.skip_if_target_dot_at_cap == "burn"


def test_kit_state_survives_the_database_codec():
    state = _party_combat(_creature("oath.preco.credor_fim"), (300, 200))
    back = combat_codec.decode(combat_codec.encode(state), state.id, state.ruleset, state.version)
    assert back.ai_target_policy == "lowest_hp"
    assert back.enemy_actions["cobranca_fracionada"].hit_count == 2
    assert back.enemy_actions["troco"].skip_if_target_effect_active == "pve.attack_down_10"


def test_kit_creature_rejects_a_fallback_with_recarga():
    with pytest.raises(ValueError):
        kit_creature(
            "x",
            "X",
            "elite",
            "balanced",
            (KitAction("a", "A", PREPARED, cooldown=4), KitAction("b", "B", SIMPLE, cooldown=2)),
        )
    assert replace(KitAction("a", "A", SIMPLE)).effect_id() is None


@pytest.mark.parametrize(
    "kind,creature",
    list(_creatures()),
    ids=[creature.creature_id for _, creature in _creatures()],
)
def test_every_kit_plays_a_whole_combat(kind, creature):
    state = _party_combat(creature, (5000,) if kind == "event" else (5000, 4000, 3000))
    used = set()
    for _ in range(600):
        if state.result:
            break
        before = len(state.events)
        state = act(state, "attack")
        used.update(
            event.action
            for event in state.events[before:]
            if getattr(event, "actor", "") == "enemy"
        )
        assert len(state.events) > before
    assert len(used & {action[0] for action in creature.actions}) >= 2

from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

import pytest

from asterion.domain.campaign_combat import scale_campaign_boss_stats
from asterion.domain.combat import _resolve_phase_triggers
from asterion.domain.nareth_bosses import (
    ARCHON_AXES,
    ARCHON_PHASE_II,
    ARCHON_PHASE_III,
    configure_nareth_campaign_boss,
    nareth_boss_phase_evidence,
)
from asterion.domain.road import (
    NARETH_ARCONTE_INVERTIDO,
    NARETH_CUSTODIO_SEM_NORTE,
    RULESET,
    Creature,
    CreatureCombatantSpec,
    create_creature_party_combat,
    road_enemy_stats,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _combat(creature, size=1):
    state = create_creature_party_combat(
        uuid4(),
        "Sentinela",
        "sentinela",
        "remanescente",
        D(1200),
        (CreatureCombatantSpec(creature, 30, "enemy", campaign_boss_group_size=size),),
        player_level=30,
        ruleset_version=RULESET,
    )
    return configure_nareth_campaign_boss(state, creature.creature_id, shared=size > 1)


@pytest.mark.parametrize("creature", (NARETH_CUSTODIO_SEM_NORTE, NARETH_ARCONTE_INVERTIDO))
def test_nareth_campaign_bosses_use_global_factors_and_scaling(creature):
    solo = road_enemy_stats(creature, 30)
    expected = ((D("1.00"), D("1.00")), (D("1.55"), D("1.04")),
                (D("2.10"), D("1.08")), (D("2.65"), D("1.12")))
    for size, (hp_factor, attack_factor) in enumerate(expected, start=1):
        state = _combat(creature, size)
        actual = state.fighters["enemy"].stats
        assert actual == scale_campaign_boss_stats(solo, size)
        assert actual.hp == (solo.hp * hp_factor).quantize(D(1), rounding=ROUND_HALF_UP)
        assert actual.attack == (solo.attack * attack_factor).quantize(D(1), rounding=ROUND_HALF_UP)
        assert actual.defense == solo.defense
        assert actual.agility == solo.agility
        assert state.fighters["enemy"].level == 30


def test_custodio_sem_norte_has_only_the_published_actions_and_prepared_queda():
    state = _combat(NARETH_CUSTODIO_SEM_NORTE)
    assert set(state.enemy_actions) == {
        "golpe_marco", "rota_negada", "correcao_cega", "queda_sem_norte"
    }
    assert state.enemy_actions["rota_negada"].duration == 2
    assert state.enemy_actions["rota_negada"].cooldown == 3
    assert state.enemy_actions["queda_sem_norte"].prepared is True
    assert state.enemy_actions["queda_sem_norte"].coefficient == D("1.70")
    assert state.phase_triggers == ()
    assert not any(key.startswith("axis_") for key in state.fighters)


def test_arconte_activates_three_persistent_axes_and_phase_three_does_not_recreate_them():
    state = _combat(NARETH_ARCONTE_INVERTIDO, 2)
    boss = state.fighters["enemy"]
    boss.hp = boss.stats.hp * D("0.70")
    _resolve_phase_triggers(state)

    assert state.phase_id == "II"
    assert ARCHON_PHASE_II in state.phase_triggered_ids
    assert len(ARCHON_AXES) == 3
    for key in ARCHON_AXES:
        axis = state.fighters[key]
        assert axis.hp == axis.stats.hp
        common = Creature("common", "Comum", "common", "balanced", 30, 30, 0, (), ())
        assert axis.stats.hp == road_enemy_stats(common, 30).hp * D("0.30")
        assert axis.takes_turn is False
        assert axis.required_for_victory is False
    assert tuple(aura.stat for aura in state.stat_auras) == ("attack", "defense", "agility")
    assert {evidence for evidence in nareth_boss_phase_evidence(state)} >= {
        "phase:corrigir_o_que_permanece",
        "mechanic:eixo_carga_observado",
        "mechanic:eixo_guarda_observado",
        "mechanic:eixo_ritmo_observado",
    }

    state.fighters[ARCHON_AXES[0]].hp = 0
    survivors = {key: state.fighters[key].hp for key in ARCHON_AXES[1:]}
    boss.hp = boss.stats.hp * D("0.35")
    _resolve_phase_triggers(state)
    assert state.phase_id == "III"
    assert ARCHON_PHASE_III in state.phase_triggered_ids
    assert state.fighters[ARCHON_AXES[0]].hp == 0
    assert {key: state.fighters[key].hp for key in ARCHON_AXES[1:]} == survivors
    assert state.enemy_actions["protocolo_continuidade"].phase_ids == ("II",)
    assert state.enemy_actions["retificacao_final"].phase_ids == ("III",)
    assert state.enemy_actions["retificacao_final"].prepared is True


def test_arconte_axes_and_phase_snapshot_survive_combat_codec_round_trip():
    state = _combat(NARETH_ARCONTE_INVERTIDO, 3)
    state.fighters["enemy"].hp = state.fighters["enemy"].stats.hp * D("0.70")
    _resolve_phase_triggers(state)
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.phase_id == "II"
    assert restored.phase_triggered_ids == {ARCHON_PHASE_II}
    assert restored.stat_auras == state.stat_auras
    assert restored.phase_triggers == state.phase_triggers
    assert {key: restored.fighters[key].hp for key in ARCHON_AXES} == {
        key: state.fighters[key].hp for key in ARCHON_AXES
    }

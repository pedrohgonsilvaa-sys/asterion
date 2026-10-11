from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from asterion.domain.campaign_combat import scale_campaign_boss_stats
from asterion.domain.combat import (
    Action,
    _damage_aura_reduction,
    _resolve_phase_triggers,
    act,
    action_target_ids,
)
from asterion.domain.road import (
    RULESET,
    VDE_MATRIARCH,
    Creature,
    CreatureCombatantSpec,
    create_creature_party_combat,
    road_enemy_stats,
)
from asterion.domain.vde_matriarch import (
    CONNECTION_KEYS,
    PHASE_II_ID,
    PHASE_III_ID,
    configure_matriarch_combat,
    matriarch_phase_evidence,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _combat(size: int = 1):
    state = create_creature_party_combat(
        uuid4(),
        "Sentinela",
        "sentinela",
        "remanescente",
        D(1000),
        (
            CreatureCombatantSpec(
                VDE_MATRIARCH,
                20,
                "enemy",
                campaign_boss_group_size=size,
            ),
        ),
        player_level=20,
        ruleset_version=RULESET,
    )
    return configure_matriarch_combat(state, shared=size > 1)


def _enter_phase_ii(state):
    boss = state.fighters["enemy"]
    boss.hp = boss.stats.hp * D("0.70")
    _resolve_phase_triggers(state)


def test_matriarch_profile_and_campaign_boss_scaling_are_exact():
    solo_stats = road_enemy_stats(VDE_MATRIARCH, 20)
    expected = (
        (D("1.00"), D("1.00")),
        (D("1.55"), D("1.04")),
        (D("2.10"), D("1.08")),
        (D("2.65"), D("1.12")),
    )
    for size, (hp_factor, attack_factor) in enumerate(expected, start=1):
        state = _combat(size)
        boss = state.fighters["enemy"]
        scaled = scale_campaign_boss_stats(solo_stats, size)
        assert boss.stats == scaled
        assert boss.stats.hp == (solo_stats.hp * hp_factor).quantize(
            D(1), rounding=ROUND_HALF_UP
        )
        assert boss.stats.attack == (solo_stats.attack * attack_factor).quantize(
            D(1), rounding=ROUND_HALF_UP
        )
        assert boss.stats.defense == solo_stats.defense
        assert boss.stats.agility == solo_stats.agility
        assert boss.level == 20
        assert state.party_mode
        assert state.fighters["player"].stats.hp > 0


def test_phase_two_activates_three_optional_persistent_connections():
    state = _combat(2)
    _enter_phase_ii(state)

    assert state.phase_id == "II"
    assert PHASE_II_ID in state.phase_triggered_ids
    assert len(CONNECTION_KEYS) == 3
    reference = road_enemy_stats(
        Creature("common_reference", "Comum", "common", "balanced", 20, 20, 0, (), ()),
        20,
    )
    for key in CONNECTION_KEYS:
        connection = state.fighters[key]
        assert connection.hp == reference.hp * D("0.30")
        assert connection.stats.defense == reference.defense * D("0.90")
        assert connection.stats.attack == 0
        assert connection.takes_turn is False
        assert connection.required_for_victory is False
        assert connection.hp > 0
    assert _damage_aura_reduction(state, "enemy") == D("0.12")
    assert set(action_target_ids(state, "attack")) == {
        "enemy",
        "connection_a",
        "connection_b",
        "connection_c",
    }

    state.fighters["connection_a"].hp = 0
    assert _damage_aura_reduction(state, "enemy") == D("0.08")

    surviving_hp = {key: state.fighters[key].hp for key in CONNECTION_KEYS}
    state.fighters["enemy"].hp = state.fighters["enemy"].stats.hp * D("0.35")
    _resolve_phase_triggers(state)
    assert state.phase_id == "III"
    assert PHASE_III_ID in state.phase_triggered_ids
    assert {key: state.fighters[key].hp for key in CONNECTION_KEYS} == surviving_hp
    _resolve_phase_triggers(state)
    assert {key: state.fighters[key].hp for key in CONNECTION_KEYS} == surviving_hp


def test_matriarch_actions_match_the_canonical_phase_and_telegraph_rules():
    state = _combat()
    actions = state.enemy_actions
    assert actions["golpe_matriarca"].coefficient == D("1.00")
    assert actions["raiz_constritiva"].coefficient == D("0.90")
    assert actions["raiz_constritiva"].effect_stat == "agility"
    assert actions["raiz_constritiva"].attack_debuff == D("0.10")
    assert actions["raiz_constritiva"].duration == 2
    assert actions["raiz_constritiva"].cooldown == 3
    assert actions["seiva_corrompida"].coefficient == D("0.80")
    assert actions["seiva_corrompida"].native_dot_kind == "poison"
    assert actions["seiva_corrompida"].native_dot_stacks == 1
    assert actions["seiva_corrompida"].cooldown == 3
    assert actions["chicote_radicular"].coefficient == D("1.30")
    assert actions["chicote_radicular"].cooldown == 3
    assert actions["varredura_raizes"].phase_ids == ("II", "III")
    assert actions["abraco_berco"].phase_ids == ("II",)
    assert actions["estrangulamento_vale"].phase_ids == ("III",)

    _enter_phase_ii(state)
    assert actions["varredura_raizes"].coefficient == D("0.80")
    assert actions["varredura_raizes"].target_mode == "all_opponents"
    assert actions["varredura_raizes"].cooldown == 3
    assert actions["varredura_raizes"].phase_ids == ("II", "III")
    assert actions["abraco_berco"].self_barrier_hp_fraction == D("0.08")
    assert actions["abraco_berco"].cooldown == 5
    assert actions["abraco_berco"].max_uses_per_combat == 2
    assert actions["abraco_berco"].skip_if_barrier_active

    state.fighters["enemy"].hp = state.fighters["enemy"].stats.hp * D("0.35")
    _resolve_phase_triggers(state)
    strangulation = actions["estrangulamento_vale"]
    assert strangulation.prepared
    assert strangulation.coefficient == D("1.80")
    assert strangulation.cooldown == 5
    assert strangulation.phase_ids == ("III",)
    assert actions["abraco_berco"].phase_ids == ("II",)
    assert matriarch_phase_evidence(state) == (
        "mechanic:conexoes_radicular_observadas",
        "phase:a_rede",
        "phase:aquilo_que_permanece",
    )


def test_phase_and_connection_state_survive_snapshot_reconnect():
    state = _combat(3)
    _enter_phase_ii(state)
    state.fighters["connection_b"].hp -= D(17)
    state.fighters["enemy"].hp = state.fighters["enemy"].stats.hp * D("0.35")
    _resolve_phase_triggers(state)

    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.phase_id == "III"
    assert restored.phase_triggered_ids == {PHASE_II_ID, PHASE_III_ID}
    assert restored.fighters["connection_b"].hp == state.fighters["connection_b"].hp
    assert restored.damage_auras == state.damage_auras
    assert restored.enemy_actions["estrangulamento_vale"].phase_ids == ("III",)


def test_matriarch_attacks_can_select_and_destroy_connections():
    state = _combat(1)
    _enter_phase_ii(state)
    state.order = ("player", "enemy")
    state.turn_index = 0
    state.player_actions = {"attack": Action("attack", "Ataque", D("1.00"))}
    state.player_actions_by_fighter = {}
    before = state.fighters["connection_a"].hp

    updated = act(state, "attack", target_id="connection_a")

    assert updated is not state
    assert updated.fighters["connection_a"].hp < before
    if updated.fighters["connection_a"].hp == 0:
        assert "connection_a" not in action_target_ids(updated, "attack")
        assert _damage_aura_reduction(updated, "enemy") == D("0.08")
    assert updated.result is None

"""Resolução em lote de A Ruptura do Véu (domínio puro)."""

from __future__ import annotations

from decimal import Decimal as D
from uuid import UUID

from asterion.domain import veu_combat as vc

A, B = UUID(int=1), UUID(int=2)


def _enemy(code="VEU-01", hp=1000, attack=100, defense=10):
    return vc.EnemyUnit(code, D(hp), D(hp), D(attack), D(defense))


def _players():
    return {
        A: vc.PlayerUnit(A, D(500), D(500), D(10)),
        B: vc.PlayerUnit(B, D(500), D(500), D(10)),
    }


def test_damage_is_summed_from_the_initial_state_and_overkill_is_not_counted():
    enemy = _enemy(hp=100)
    intents = [
        vc.PlayerIntent(A, "attack", "VEU-01", 80),
        vc.PlayerIntent(B, "attack", "VEU-01", 80),
    ]
    out = vc.resolve_batch({"VEU-01": enemy}, _players(), intents, [])
    assert enemy.hp == 0 and enemy.defeated
    assert out.damage_by_character == {A: 80, B: 20}  # overkill de B não conta
    assert out.kills_by_character == {B: ["VEU-01"]}
    assert out.defeated_enemies == ["VEU-01"]


def test_defeated_enemy_still_acts_in_its_own_round_and_defend_mitigates():
    enemy = _enemy(hp=10, attack=200)
    decision = vc.EnemyDecisionData("VEU-01", "mordida_vertical", (A, B), False)
    plain = vc.resolve_batch(
        {"VEU-01": _enemy(hp=10, attack=200)}, _players(),
        [vc.PlayerIntent(A, "attack", "VEU-01", 50)], [decision],
    )
    defended = vc.resolve_batch(
        {"VEU-01": enemy}, _players(),
        [vc.PlayerIntent(A, "defend", None, 0), vc.PlayerIntent(B, "attack", "VEU-01", 50)],
        [decision],
    )
    assert plain.damage_taken[A] > 0
    assert defended.damage_taken[A] < plain.damage_taken[A]  # Defender reduz
    assert defended.damage_taken[B] == plain.damage_taken[B]


def test_player_defeat_and_hp_never_below_zero():
    players = _players()
    players[A].hp = D(1)
    decision = vc.EnemyDecisionData("VEU-01", "mordida_vertical", (A,), False)
    out = vc.resolve_batch({"VEU-01": _enemy(attack=500)}, players, [], [decision])
    assert players[A].hp == 0 and out.defeated_players == [A]
    assert out.damage_taken[A] == 1


def test_barrier_absorbs_damage_for_two_rounds_and_counts_as_absorbed():
    enemy = _enemy("VEU-03", hp=1000, attack=100)
    decision = vc.EnemyDecisionData("VEU-03", "fechamento_toracico", (), False)
    vc.resolve_batch({"VEU-03": enemy}, _players(), [], [decision])
    assert enemy.barrier == D(60) and enemy.barrier_turns == 1  # 60% ATQ, 2 turnos (1 já passou)
    out = vc.resolve_batch(
        {"VEU-03": enemy}, _players(), [vc.PlayerIntent(A, "attack", "VEU-03", 100)], []
    )
    assert out.absorbed_by_character == {A: 60}
    assert out.damage_by_character == {A: 40}
    assert enemy.barrier == 0  # expirou no fim desta rodada


def test_cooldown_blocks_reuse_and_decision_is_deterministic():
    enemy = _enemy("VEU-01")
    first = vc.decide_enemy(enemy, [A, B], 1, 12345)
    again = vc.decide_enemy(enemy, [B, A], 1, 12345)
    assert first == again
    decision = vc.EnemyDecisionData("VEU-01", "fechamento_subito", (A,), False)
    vc.resolve_batch({"VEU-01": enemy}, _players(), [], [decision])
    assert enemy.cooldowns == {"fechamento_subito": 2}
    for seed in range(40):
        picked = vc.decide_enemy(enemy, [A], 2, seed)
        assert picked.action_key != "fechamento_subito"


def test_not_consecutive_and_max_uses_are_respected():
    boss = _enemy("VEU-18", hp=10_000)
    boss.last_action = "preparar_a_ruptura"
    boss.uses["recompor_a_margem"] = 2
    for seed in range(60):
        picked = vc.decide_enemy(boss, [A], 3, seed)
        assert picked.action_key not in {"preparar_a_ruptura", "recompor_a_margem"}


def test_prepared_actions_are_telegraphed_and_aoe_hits_everyone():
    boss = _enemy("VEU-18", hp=10_000)
    seen = {}
    for seed in range(200):
        d = vc.decide_enemy(boss, [A, B], 1, seed)
        seen[d.action_key] = d
    assert seen["preparar_a_ruptura"].telegraph is True
    assert set(seen["linha_impossivel"].target_ids) == {A, B}
    assert seen["golpe_da_margem"].telegraph is False
    assert len(seen["golpe_da_margem"].target_ids) == 1


def test_no_decision_without_players_or_when_defeated():
    assert vc.decide_enemy(_enemy(), [], 1, 1) is None
    dead = _enemy()
    dead.hp = D(0)
    assert vc.decide_enemy(dead, [A], 1, 1) is None


def test_enemy_state_roundtrip():
    enemy = _enemy()
    enemy.cooldowns = {"x": 2}
    enemy.barrier = D(5)
    assert vc.EnemyUnit.from_data("VEU-01", enemy.to_data()).to_data() == enemy.to_data()

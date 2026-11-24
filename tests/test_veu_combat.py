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


# ------------------------------------------------------------ efeitos e suporte


def _hit(code, action, targets):
    return vc.EnemyDecisionData(code, action, tuple(targets), False)


def test_kit_debuff_is_applied_lasts_its_turns_and_changes_the_engine_stat():
    from asterion.domain.combat import Fighter
    from asterion.domain.combat_math import CombatStats

    players = _players()
    out = vc.resolve_batch(
        {"VEU-01": _enemy()}, players, [], [_hit("VEU-01", "fechamento_subito", [A])]
    )
    (effect,) = players[A].effects
    assert (effect.stat, effect.magnitude, effect.remaining, effect.kind) == (
        "agility", D("0.10"), 2, "debuff",
    )
    assert players[B].effects == []
    assert out.damage_taken[A] > 0  # dano + debuff
    fighter = Fighter("p", "A", 30, CombatStats(D(500), D(100), D(50), D(100)), D(500))
    fighter.effects = [vc.engine_effect(effect)]
    assert fighter.stat("agility") == D(90)  # AGI −10% pelo motor
    # Dura 2 rodadas (a da aplicação não conta) e expira.
    vc.resolve_batch({}, players, [], [])
    assert players[A].effects[0].remaining == 1
    vc.resolve_batch({}, players, [], [])
    assert players[A].effects == []


def test_debuff_only_action_applies_without_damage_and_reapplying_refreshes():
    players = _players()
    out = vc.resolve_batch(
        {"VEU-09": _enemy("VEU-09")}, players, [], [_hit("VEU-09", "trama_ossea", [A])]
    )
    assert out.damage_taken == {} and players[A].hp == 500
    assert [e.stat for e in players[A].effects] == ["defense"]
    vc.resolve_batch({}, players, [], [])
    vc.resolve_batch(
        {"VEU-09": _enemy("VEU-09")}, players, [], [_hit("VEU-09", "trama_ossea", [A])]
    )
    assert len(players[A].effects) == 1 and players[A].effects[0].remaining == 2


def test_each_kit_debuff_stat_maps_to_an_engine_stat():
    from asterion.domain.veu_bestiary import VEU_CREATURES, ActionKind

    stats = {
        action.stat
        for creature in VEU_CREATURES
        for action in creature.actions
        if action.kind in (ActionKind.DAMAGE_DEBUFF, ActionKind.DEBUFF)
    }
    assert stats and stats <= set(vc.STAT_MAP)


def test_effective_heal_is_capped_by_missing_hp_and_credited():
    players = _players()
    players[B].hp = D(450)
    out = vc.resolve_batch(
        {}, players,
        [vc.PlayerIntent(A, "art", None, 0, (vc.SupportResult(A, B, "heal", 300),))], [],
    )
    assert players[B].hp == 500 and out.heal_by_character == {A: 50}  # só o que faltava
    wasted = vc.resolve_batch(
        {}, players,
        [vc.PlayerIntent(A, "art", None, 0, (vc.SupportResult(A, B, "heal", 300),))], [],
    )
    assert wasted.heal_by_character == {}  # cura excedente não conta


def test_heal_and_damage_in_the_same_round_are_netted_before_the_defeat_check():
    players = _players()
    players[B].hp = D(20)
    enemy = _enemy(attack=100)
    out = vc.resolve_batch(
        {"VEU-01": enemy}, players,
        [vc.PlayerIntent(A, "art", None, 0, (vc.SupportResult(A, B, "heal", 400),))],
        [_hit("VEU-01", "mordida_vertical", [B])],
    )
    assert out.defeated_players == [] and players[B].hp > 0
    dead = _players()
    dead[B].hp = D(20)
    out = vc.resolve_batch(
        {"VEU-01": _enemy(attack=100)}, dead, [], [_hit("VEU-01", "mordida_vertical", [B])]
    )
    assert out.defeated_players == [B]


def test_support_barrier_absorbs_from_the_next_round_and_credits_the_supporter():
    players = _players()
    vc.resolve_batch(
        {}, players,
        [vc.PlayerIntent(A, "art", None, 0, (vc.SupportResult(A, B, "barrier", 80, 2),))], [],
    )
    assert players[B].barrier == 80 and players[B].barrier_source == A
    out = vc.resolve_batch(
        {"VEU-01": _enemy(attack=100)}, players, [], [_hit("VEU-01", "mordida_vertical", [B])]
    )
    assert out.barrier_absorbed_for == {A: 80}  # Barreira efetivamente absorvida
    assert players[B].hp < 500
    # A Barreira expira depois dos turnos, mesmo sem uso.
    fresh = _players()
    vc.resolve_batch(
        {}, fresh,
        [vc.PlayerIntent(A, "art", None, 0, (vc.SupportResult(A, B, "barrier", 80, 2),))], [],
    )
    vc.resolve_batch({}, fresh, [], [])
    vc.resolve_batch({}, fresh, [], [])
    assert fresh[B].barrier == 0


def test_protection_effect_credits_the_supporter_only_when_it_mitigated_real_damage():
    players = _players()
    buff = vc.PlayerEffect(f"support:{A.hex}:x", "defense", D("0.2"), 2, "buff", str(A))
    vc.resolve_batch(
        {}, players,
        [
            vc.PlayerIntent(
                A, "art", None, 0, (vc.SupportResult(A, B, "protection", 0, 0, (buff,)),)
            )
        ],
        [],
    )
    assert [e.kind for e in players[B].effects] == ["buff"]
    quiet = vc.resolve_batch({}, players, [], [])
    assert quiet.protection_credit == set()
    out = vc.resolve_batch(
        {"VEU-01": _enemy(attack=100)}, players, [], [_hit("VEU-01", "mordida_vertical", [B])]
    )
    assert out.protection_credit == {A}


def test_support_kinds_reads_only_direct_ally_support():
    from asterion.domain.combat import Action, ActionEffect

    heal = Action("a", "a", D(0), target_mode="ally", heal_coefficient=D("0.5"))
    barrier = Action("b", "b", D(0), target_mode="ally", target_barrier_coefficient=D("0.9"))
    guard = Action(
        "c", "c", D(0), target_mode="all_allies",
        target_effects=(ActionEffect("e", "defense", D("0.1"), 2, "buff"),),
    )
    offensive = Action("d", "d", D("1"), target_mode="opponent", heal_coefficient=D("0.5"))
    assert vc.support_kinds(heal) == ("heal",)
    assert vc.support_kinds(barrier) == ("barrier",)
    assert vc.support_kinds(guard) == ("protection",)
    assert vc.support_kinds(offensive) == ()


def test_weaver_uses_bone_weave_with_three_or_more_participants():
    boss = _enemy("VEU-09", hp=5000)
    ids = [UUID(int=n) for n in range(1, 4)]
    for seed in range(50):
        picked = vc.decide_enemy(boss, ids, 1, seed)
        assert picked.action_key == "trama_ossea"
    boss.cooldowns["trama_ossea"] = 2  # indisponível: volta ao desempate normal
    assert all(
        vc.decide_enemy(boss, ids, 1, seed).action_key != "trama_ossea" for seed in range(30)
    )
    two = {vc.decide_enemy(_enemy("VEU-09", hp=5000), ids[:2], 1, s).action_key for s in range(60)}
    assert len(two) > 1  # com 2 participantes não há prioridade

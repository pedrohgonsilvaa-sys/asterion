"""Extensões do lote compartilhado (``veu_combat.resolve_batch``) usadas pelos Flagelos."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from asterion.application.flagelo_combat import BossDot, BossEffects, next_boss_state, tick_boss
from asterion.domain import flagelos as fl
from asterion.domain import veu_combat as vc
from asterion.domain.combat import DOT_DURATIONS, DotState, Effect
from asterion.domain.combat_math import CombatStats, direct_damage, dot_damage

D = Decimal
A, B = UUID(int=1), UUID(int=2)


def _boss(code="varkhenn", hp=35_060, attack=138):
    return vc.EnemyUnit(code, D(hp), D(35_060), D(attack), D(100), agility=D(94))


def _players(*ids, hp=1000):
    return {i: vc.PlayerUnit(i, D(hp), D(hp), D(50)) for i in ids}


def _run(code, key, players, intents=(), enemy=None, targets=None):
    enemy = enemy or _boss(code)
    targets = tuple(players) if targets is None else targets
    outcome = vc.resolve_batch(
        {code: enemy},
        players,
        list(intents),
        [vc.EnemyDecisionData(code, key, targets, False)],
        kit=fl.kit,
        level=fl.FLAGELOS_BY_ID[code].flagelo.level,
    )
    return enemy, outcome


def test_flagelo_damage_uses_its_own_level_and_kit():
    players = _players(A)
    _, outcome = _run("varkhenn", "peso_do_entulho", players)
    assert outcome.damage_taken[A] == direct_damage(D(138), D("1.30"), D(50), 10)


def test_defender_prevented_damage_is_the_real_difference():
    players = _players(A)
    intents = [vc.PlayerIntent(A, "defend", None, 0)]
    _, outcome = _run("varkhenn", "golpe_de_cinza", players, intents)
    full = direct_damage(D(138), D("1.00"), D(50), 10)
    reduced = direct_damage(D(138), D("1.00"), D(50), 10, mitigation=vc.DEFEND_MITIGATION)
    assert outcome.prevented_by_character == {A: full - reduced}
    assert outcome.damage_taken[A] == reduced


def test_aoe_burn_is_applied_then_ticks_with_the_engine_formula():
    players = _players(A, B)
    _run("varkhenn", "sopro_de_fuligem", players)
    for player in players.values():
        (dot,) = player.dots
        assert (dot.kind, dot.remaining, dot.snapshots) == ("burn", DOT_DURATIONS["burn"], [D(138)])
    hp_before = players[A].hp
    # Próxima rodada sem ataque que acerte A: só o tick da Queimadura.
    _, outcome = _run("varkhenn", "golpe_de_cinza", players, targets=(B,))
    tick = dot_damage([D(138)], D("0.15"), D(50), 10)
    assert hp_before - players[A].hp == tick
    assert players[A].dots[0].remaining == DOT_DURATIONS["burn"] - 1
    assert any(item["kind"] == "player_dot" for item in outcome.history)


def test_aoe_with_agi_debuff_applies_it_to_every_target():
    players = _players(A, B)
    _run("azharel", "meridiano_divergente", players)
    for player in players.values():
        assert [(e.stat, e.magnitude, e.remaining) for e in player.effects] == [
            ("agility", D("0.10"), 2)
        ]


def test_self_heal_is_five_percent_and_never_revives():
    enemy = _boss("hemrath", hp=30_000)
    enemy.max_hp = D(63_880)
    _, outcome = _run("hemrath", "restituicao_rubra", _players(A), enemy=enemy)
    assert enemy.hp == D(30_000 + 3_194)
    dead = _boss("hemrath", hp=10)
    dead.max_hp = D(63_880)
    _run(
        "hemrath",
        "restituicao_rubra",
        _players(A),
        [vc.PlayerIntent(A, "attack", "hemrath", 50)],
        dead,
    )
    assert dead.hp <= 0
    assert enemy.uses["restituicao_rubra"] == 1


def test_escora_inversa_raises_attack_and_lowers_defense_for_two_turns():
    enemy = _boss("korvann")
    _run("korvann", "escora_inversa", _players(A), enemy=enemy)
    assert (enemy.buff_attack, enemy.defense_mod) == (D("0.08"), -D("0.08"))
    assert enemy.defense_mod_turns == 1 and enemy.effective_defense == D(100) * D("0.92")


def test_boss_dot_ticks_credit_the_source_and_fresh_effects_wait_a_round():
    state = DotState("poison", 1, 3, D(200), "player", [D(200)])
    before = BossEffects([], [BossDot(state, str(A), 30)])
    aged, ticks = tick_boss(BossEffects.from_data(before.to_data()), D(160))
    assert ticks == [(str(A), dot_damage([D(200)], D("0.12"), D(160), 30))]
    assert aged.dots[0].state.remaining == 2
    fresh = Effect("debuff:def", "defense", D("0.10"), 2, 0)
    merged = BossEffects([fresh], list(before.dots))
    nxt, _ = next_boss_state(before, merged, D(160))
    assert [(e.id, e.remaining) for e in nxt.effects] == [("debuff:def", 2)]
    # O debuff aplicado por jogador reduz a DEF do Flagelo pelo ``Fighter.stat`` do motor.
    assert BossEffects([fresh]).stat(CombatStats(D(1), D(100), D(160), D(10)), "defense") == D(144)


def test_veu_defaults_are_untouched():
    """Sem ``kit``/``level`` o lote continua usando o Bestiário e o nível do Véu."""
    enemy = vc.EnemyUnit("VEU-01", D(1000), D(1000), D(100), D(50))
    players = _players(A)
    outcome = vc.resolve_batch(
        {"VEU-01": enemy},
        players,
        [],
        [vc.EnemyDecisionData("VEU-01", "mordida_vertical", (A,), False)],
    )
    assert outcome.damage_taken[A] == direct_damage(D(100), D("1.00"), D(50), 30)
    assert players[A].dots == [] and "dots" not in players[A].state_data()

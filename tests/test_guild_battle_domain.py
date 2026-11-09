"""Pure rules of the Batalha de Guildas (GDD v1.6.0 §15, §49.14)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from asterion.domain.combat import active_player_key, withdraw_fighter
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.guild_battle import (
    GUILD_BATTLE_TIMEZONE,
    PairingCandidate,
    StandingCandidate,
    classification_points,
    front_points,
    individual_reward_eligible,
    next_battle_start,
    no_show_winner,
    open_registration,
    order_standings,
    pair_guilds,
    rating_after_battle,
    rating_k,
    reward_eligible,
)
from asterion.domain.road import PlayerCombatantSpec, create_player_versus_player_combat

D = Decimal
# Wednesday 2026-11-11, 21:00 in Sao Paulo is 00:00 UTC on Thursday.
WEDNESDAY = datetime(2026, 11, 12, 0, 0, tzinfo=UTC)


def _guild(number: int) -> UUID:
    return UUID(int=number)


def test_battles_are_wednesday_and_sunday_at_21_sao_paulo():
    start = next_battle_start(WEDNESDAY - timedelta(hours=1))
    assert start == WEDNESDAY
    local = start.astimezone(GUILD_BATTLE_TIMEZONE)
    assert (local.weekday(), local.hour, local.minute) == (2, 21, 0)
    following = next_battle_start(start).astimezone(GUILD_BATTLE_TIMEZONE)
    assert (following.weekday(), following.hour) == (6, 21)


def test_registration_opens_24h_before_and_closes_at_2030():
    assert open_registration(WEDNESDAY - timedelta(hours=24, seconds=1)) is None
    opened = open_registration(WEDNESDAY - timedelta(hours=24))
    assert opened is not None and opened.starts_at == WEDNESDAY
    assert opened.registration_closes_at == WEDNESDAY - timedelta(minutes=30)
    assert opened.confirmation_closes_at == WEDNESDAY - timedelta(minutes=10)
    assert open_registration(WEDNESDAY - timedelta(minutes=31)) is not None
    assert open_registration(WEDNESDAY - timedelta(minutes=30)) is None


def test_pairing_sorts_by_rating_and_pairs_neighbours():
    pairing = pair_guilds(
        [
            PairingCandidate(_guild(1), 1500, 0),
            PairingCandidate(_guild(2), 1700, 0),
            PairingCandidate(_guild(3), 1400, 0),
            PairingCandidate(_guild(4), 1600, 0),
        ]
    )
    assert pairing.bye is None
    assert pairing.pairs == ((_guild(2), _guild(4)), (_guild(1), _guild(3)))


def test_odd_count_gives_rotating_bye_by_fewest_byes_then_lowest_rating():
    candidates = [
        PairingCandidate(_guild(1), 1400, 1),
        PairingCandidate(_guild(2), 1600, 0),
        PairingCandidate(_guild(3), 1500, 0),
    ]
    pairing = pair_guilds(candidates)
    assert pairing.bye == _guild(3)
    assert pairing.pairs == ((_guild(2), _guild(1)),)
    tied = pair_guilds(
        [
            PairingCandidate(_guild(9), 1500, 0),
            PairingCandidate(_guild(5), 1500, 0),
            PairingCandidate(_guild(7), 1500, 0),
        ]
    )
    assert tied.bye == _guild(5)
    assert pair_guilds([PairingCandidate(_guild(1), 1500, 0)]).bye == _guild(1)


def test_technical_rating_uses_k48_for_first_five_real_battles_then_k32():
    assert rating_k(0) == 48 and rating_k(4) == 48 and rating_k(5) == 32
    assert rating_after_battle(1500, 1500, D(1), 0) == 1524
    assert rating_after_battle(1500, 1500, D(1), 5) == 1516
    assert rating_after_battle(1500, 1500, D("0.5"), 0) == 1500
    # No floor: the technical rating only pairs similar strengths.
    assert rating_after_battle(10, 1500, D(0), 9) == 10


def test_points_standings_and_eligibility():
    assert [classification_points(D(s)) for s in ("1", "0.5", "0")] == [3, 1, 0]
    assert front_points("a", absent_a=False, absent_b=False) == (D(1), D(0))
    assert front_points(None, absent_a=False, absent_b=False) == (D("0.5"), D("0.5"))
    assert front_points(None, absent_a=True, absent_b=True) == (D(0), D(0))
    assert no_show_winner(True, False) == "b"
    assert no_show_winner(False, True) == "a"
    assert no_show_winner(True, True) is None
    ordered = order_standings(
        [
            StandingCandidate(_guild(2), 6, 1500),
            StandingCandidate(_guild(1), 6, 1500),
            StandingCandidate(_guild(3), 6, 1600),
            StandingCandidate(_guild(4), 9, 1400),
        ]
    )
    assert [row.guild_id for row in ordered] == [_guild(4), _guild(3), _guild(1), _guild(2)]
    assert not reward_eligible(9) and reward_eligible(10)
    assert not individual_reward_eligible(3) and individual_reward_eligible(4)


def _spec(key: str) -> PlayerCombatantSpec:
    return PlayerCombatantSpec(
        key, f"{key}-character", key, "sentinela", "remanescente", 30, D(100),
        EquipmentConfigurationSnapshot(0), (),
    )  # fmt: skip


def test_withdrawn_fighter_counts_as_defeated_and_the_team_fights_on():
    state = create_player_versus_player_combat(
        uuid4(), (_spec("a1"), _spec("a2")), (_spec("b1"), _spec("b2")), full_hp=True
    )
    active = active_player_key(state)
    assert active is not None
    side = active[0]
    partner = f"{side}2" if active.endswith("1") else f"{side}1"
    after = withdraw_fighter(state, active)
    assert after.version == state.version + 1
    assert after.fighters[active].hp == 0
    assert not after.result
    assert active_player_key(after) != active
    # Withdrawing again is a no-op; the last fighter of a side ends the combat.
    assert withdraw_fighter(after, active) is after
    finished = withdraw_fighter(after, partner)
    assert finished.result
    survivors = {f.side for f in finished.fighters.values() if f.hp > 0}
    assert survivors == {"enemy" if side == "a" else "player"}
    assert withdraw_fighter(finished, "b1" if side == "a" else "a1") is finished


def test_withdraw_does_not_touch_the_original_state():
    state = create_player_versus_player_combat(
        uuid4(), (_spec("a1"),), (replace(_spec("b1")),), full_hp=True
    )
    key = active_player_key(state)
    withdraw_fighter(state, key)
    assert state.fighters[key].hp > 0

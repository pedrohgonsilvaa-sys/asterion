from decimal import Decimal
from uuid import uuid4

from asterion.application.round import RoundService
from asterion.domain.combat import (
    DotState,
    Effect,
    act,
    consumable_available,
    use_heal_consumable,
    use_purification_consumable,
)
from asterion.domain.combat_math import Stats, dot_damage
from asterion.domain.road import CREATURES, create_road_combat

D = Decimal


def _combat():
    state = create_road_combat(
        uuid4(),
        "Heroa",
        "sentinela",
        "remanescente",
        D("500"),
        CREATURES[0],
        1,
        None,
    )
    state.fighters["player"].stats = Stats(D("1000"), D("100"), D("0"), D("100"))
    state.fighters["player"].hp = D("400")
    state.fighters["enemy"].stats = Stats(D("1000"), D("100"), D("0"), D("50"))
    return state


def _service():
    return RoundService(None, "ocaso")


def test_dot_damage_uses_half_effective_defense_and_no_rng():
    snapshots = [D("100"), D("120")]
    low_def = dot_damage(snapshots, D("0.12"), D("0"), 1)
    defended = dot_damage(snapshots, D("0.12"), D("100"), 1)
    assert low_def == 26
    assert 0 < defended < low_def
    assert dot_damage(snapshots, D("0.12"), D("100"), 1) == defended


def test_heal_consumable_is_22_percent_floor_and_shares_cd2():
    state = _combat()
    before_version = state.version
    healed = use_heal_consumable(state)
    assert healed.version == before_version + 1
    assert healed.fighters["player"].hp == D("620")
    assert healed.events[-2].action == "consumable:heal"
    assert consumable_available(healed) is False

    advanced = use_heal_consumable(healed)
    assert advanced is healed

    advanced = act(healed, "attack")
    assert consumable_available(advanced) is True


def test_purification_removes_only_oldest_dot_stack():
    state = _combat()
    state.dot_states["player"] = [
        DotState(
            "poison",
            3,
            3,
            D("100"),
            "enemy",
            [D("100"), D("200"), D("300")],
        )
    ]
    purified = use_purification_consumable(state, dot_index=0)
    dot = purified.dot_states["player"][0]
    assert dot.stacks == 2
    assert dot.stack_snapshots == [D("200"), D("300")]
    assert dot.snapshot_attack == D("200")


def test_purification_tiers_match_approved_thresholds():
    service = _service()
    state = _combat()

    state.dot_states["player"] = [
        DotState("poison", 2, 1, D("100"), "enemy", [D("100"), D("100")])
    ]
    assert service._purification_candidate(state, "critical") is None
    assert service._purification_candidate(state, "high") == ("purify_dot", 0)

    state.dot_states["player"] = [
        DotState("poison", 1, 3, D("500"), "enemy", [D("500")])
    ]
    assert service._purification_candidate(state, "critical") == ("purify_dot", 0)

    state.dot_states["player"] = []
    state.fighters["player"].effects = [
        Effect("antiheal", "healing_received", D("0.20"), 1, 0)
    ]
    state.fighters["player"].hp = D("400")
    assert service._purification_candidate(state, "critical") == ("purify_effect", 0)

    state.fighters["player"].hp = D("700")
    state.fighters["player"].effects = [
        Effect("slow", "agility", D("0.18"), 2, 0)
    ]
    assert service._purification_candidate(state, "critical") is None
    assert service._purification_candidate(state, "high") == ("purify_effect", 0)


def test_purification_selection_prioritizes_dot_without_rng():
    service = _service()
    state = _combat()
    state.dot_states["player"] = [
        DotState("poison", 2, 1, D("100"), "enemy", [D("100"), D("100")])
    ]
    state.fighters["player"].effects = [
        Effect("antiheal", "healing_received", D("0.40"), 3, 0)
    ]
    state.fighters["player"].hp = D("700")

    first = service._purification_candidate(state, "high")
    second = service._purification_candidate(state, "high")
    assert first == second == ("purify_dot", 0)


def test_predictable_lethal_dot_is_purified_before_other_priorities():
    service = _service()
    state = _combat()
    state.fighters["player"].hp = D("10")
    state.dot_states["player"] = [
        DotState("poison", 1, 2, D("100"), "enemy", [D("100")])
    ]
    assert service._lethal_purification_candidate(state) == ("purify_dot", 0)

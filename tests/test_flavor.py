from __future__ import annotations

from dataclasses import replace

from asterion.domain.flavor import (
    FLAVOR_CATALOG,
    LENGTH_LIMITS,
    FlavorContext,
    FlavorEntry,
    FlavorKind,
    base_bank_shortfall,
    eligible_entries,
    select_flavor,
    validate_catalog,
    validate_entry,
)


def _entry(id_: str, **kw) -> FlavorEntry:
    base = dict(
        id=id_,
        kind=FlavorKind.NARRATIVE,
        scope="local",
        key="x",
        text="Vento seco sobre a pedra.",
        draft=False,
    )
    base.update(kw)
    return FlavorEntry(**base)


def _ctx(**kw) -> FlavorContext:
    base = dict(kind=FlavorKind.NARRATIVE, scope="local", key="x", now_epoch=1000)
    base.update(kw)
    return FlavorContext(**base)


def test_catalog_is_valid_and_all_draft():
    assert validate_catalog(FLAVOR_CATALOG) == []
    assert FLAVOR_CATALOG
    assert all(entry.draft for entry in FLAVOR_CATALOG)


def test_catalog_meets_system_base_bank():
    assert base_bank_shortfall(FLAVOR_CATALOG) == {}


def test_drafts_hidden_unless_requested():
    ctx = FlavorContext(kind=FlavorKind.SYSTEM, scope="system", key="personagem")
    assert select_flavor(FLAVOR_CATALOG, ctx) is None
    assert select_flavor(FLAVOR_CATALOG, ctx, include_drafts=True) is not None


def test_validation_flags_problems():
    long_text = "a" * (LENGTH_LIMITS[FlavorKind.NARRATIVE][2] + 1)
    assert validate_entry(_entry("a", text=long_text))
    assert validate_entry(_entry("a", priority=150))
    assert validate_entry(_entry("a", weight=10))
    assert validate_entry(
        _entry("a", requires_all=frozenset({"f"}), forbidden_any=frozenset({"f"}))
    )
    assert validate_catalog([_entry("a"), _entry("a")]) == ["a: id repetido"]


def test_eligibility_by_context_and_flags():
    entries = [
        _entry("base"),
        _entry("other_key", key="y"),
        _entry("needs", requires_all=frozenset({"discovered:s"})),
        _entry("before", forbidden_any=frozenset({"discovered:s"})),
        _entry("off", active=False),
    ]
    assert {e.id for e in eligible_entries(entries, _ctx())} == {"base", "before"}
    ctx = _ctx(flags=frozenset({"discovered:s"}))
    assert {e.id for e in eligible_entries(entries, ctx)} == {"base", "needs"}


def test_spoiler_entry_never_selected_before_discovery():
    entries = [_entry("spoiler", requires_all=frozenset({"discovered:s"}), priority=300)]
    assert select_flavor(entries, _ctx()) is None


def test_highest_priority_wins():
    entries = [_entry("low"), _entry("high", priority=300), _entry("mid", priority=200)]
    for epoch in range(0, 20000, 1800):
        assert select_flavor(entries, _ctx(now_epoch=epoch)).id == "high"


def test_stable_within_window_and_rerolls_across_windows():
    entries = [_entry(f"e{i}") for i in range(8)]
    first = select_flavor(entries, _ctx(now_epoch=0))
    assert select_flavor(entries, _ctx(now_epoch=1799)) == first
    picks = {select_flavor(entries, _ctx(now_epoch=w * 1800)).id for w in range(40)}
    assert len(picks) > 1


def test_stability_token_overrides_time():
    entries = [_entry(f"e{i}") for i in range(8)]
    a = select_flavor(entries, _ctx(stability_token="run1", now_epoch=0))
    b = select_flavor(entries, _ctx(stability_token="run1", now_epoch=10**7))
    assert a == b


def test_state_change_invalidates_selection():
    entries = [
        _entry("before", forbidden_any=frozenset({"d"}), priority=200),
        _entry("after", requires_all=frozenset({"d"}), priority=200),
    ]
    assert select_flavor(entries, _ctx()).id == "before"
    assert select_flavor(entries, _ctx(flags=frozenset({"d"}))).id == "after"


def test_anti_repeat_excludes_last_two_when_three_or_more():
    entries = [_entry(f"e{i}") for i in range(3)]
    for epoch in range(0, 30 * 1800, 1800):
        pick = select_flavor(entries, _ctx(now_epoch=epoch), recent_ids=["e0", "e1"])
        assert pick.id == "e2"


def test_anti_repeat_ignored_with_fewer_than_three():
    entries = [_entry("e0"), _entry("e1")]
    pick = select_flavor(entries, _ctx(), recent_ids=["e0", "e1"])
    assert pick is not None


def test_weight_biases_selection():
    heavy = _entry("heavy", weight=200)
    light = _entry("light", weight=25)
    picks = [select_flavor([heavy, light], _ctx(now_epoch=w * 1800)).id for w in range(400)]
    assert picks.count("heavy") > picks.count("light") * 3


def test_base_bank_shortfall_reports_missing():
    entries = [replace(_entry(f"e{i}"), scope="region", key="r") for i in range(4)]
    assert base_bank_shortfall(entries) == {("region", "r"): 2}

from uuid import uuid4

import pytest

from asterion.domain.creation import Creation, NamePolicy, navigate, normalize_name


@pytest.mark.parametrize(
    "value, expected",
    [
        ("abc", "Abc"),
        ("LUIKEN", "Luiken"),
        ("lUiKeN", "Luiken"),
        ("Abcdefghijklmnop", "Abcdefghijklmnop"),
    ],
)
def test_valid_names(value, expected):
    assert normalize_name(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "Ab",
        "Abcdefghijklmnopq",
        "João",
        "Luiken1",
        "Lua Sol",
        " Luiken",
        "Luiken ",
        "Lua-Sol",
        "Luiken\n",
        "Ｌｕｉｋｅｎ",
        "Lui_ken",
        "Lui🔥ken",
    ],
)
def test_invalid_names(value):
    assert normalize_name(value) is None


def test_name_policy_has_no_invented_editorial_defaults():
    assert NamePolicy().accepts("Luiken")
    assert not NamePolicy(frozenset({"LUIKEN"})).accepts("Luiken")


@pytest.mark.parametrize("action", ["confirm", "choose", "r0", "c0", "classes", "races"])
def test_incompatible_actions_do_not_transition(action):
    assert navigate(Creation(uuid4()), action) is None

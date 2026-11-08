import pytest

from asterion.domain.guilds import (
    LODGING_CAPACITY,
    GuildNameError,
    GuildRole,
    accepts_entry,
    can_invite,
    can_manage_recruitment,
    can_remove,
    can_transfer_leadership,
    capacity_for_lodging,
    is_over_cap,
    normalize_guild_name,
    normalize_guild_tag,
)


@pytest.mark.parametrize("name", ["Abc", "Vigilia", "ABCDEFGHIJKLMNOP", "ocaso"])
def test_valid_guild_names_keep_their_display_form(name):
    assert normalize_guild_name(f"  {name} ") == name


@pytest.mark.parametrize("name", ["Ab", "A" * 17, "Os Vigias", "Vigia1", "Vigília", "Vi-gia", ""])
def test_invalid_guild_names_are_rejected(name):
    with pytest.raises(GuildNameError):
        normalize_guild_name(name)


def test_tag_is_exactly_three_letters_and_uppercased():
    assert normalize_guild_tag("ocs") == "OCS"
    for tag in ("OC", "OCSS", "OC1", "ÓCS", "O S"):
        with pytest.raises(GuildNameError):
            normalize_guild_tag(tag)


def test_lodging_capacity_progression_matches_gdd():
    assert LODGING_CAPACITY == (5, 7, 9, 10, 11, 12)
    assert capacity_for_lodging(0) == 5
    assert capacity_for_lodging(5) == 12
    with pytest.raises(ValueError):
        capacity_for_lodging(6)


def test_full_and_over_cap_guilds_accept_nobody():
    assert accepts_entry(4, 5)
    assert not accepts_entry(5, 5)
    assert not accepts_entry(6, 5)
    assert is_over_cap(6, 5)
    assert not is_over_cap(5, 5)


def test_role_permissions_follow_section_55_5():
    leader, officer, member = GuildRole.LEADER, GuildRole.OFFICER, GuildRole.MEMBER
    assert can_invite(leader) and can_invite(officer) and not can_invite(member)
    assert can_manage_recruitment(officer) and not can_manage_recruitment(member)
    assert can_transfer_leadership(leader) and not can_transfer_leadership(officer)
    assert can_remove(leader, officer) and can_remove(leader, member)
    assert can_remove(officer, member)
    assert not can_remove(officer, officer)
    assert not can_remove(officer, leader)
    assert not can_remove(member, member)
    assert not can_remove(leader, leader)

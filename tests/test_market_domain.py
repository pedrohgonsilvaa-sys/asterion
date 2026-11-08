"""Pure rules of Shops and Direct Trade (GDD v1.6.0 §28, §29, §49.10, §49.18, §55.4)."""

from __future__ import annotations

import pytest

from asterion.domain.market import (
    LISTING_SLOTS,
    MarketTextError,
    cumulative_fee,
    fallback_shop_name,
    generate_shop_code,
    market_unlocked,
    normalize_shop_code,
    promotion_summary,
    split_sale,
    trade_steps_required,
    validate_shop_description,
    validate_shop_name,
)


def test_shop_holds_six_listings():
    assert LISTING_SLOTS == 6


def test_cumulative_fee_is_floor_of_five_percent():
    assert [cumulative_fee(value) for value in (0, 19, 20, 39, 40, 1000)] == [0, 0, 1, 1, 2, 50]


def test_splitting_a_stack_never_pays_less_fee_than_one_purchase():
    gross_before = fee_before = 0
    for _ in range(100):
        split = split_sale(gross_before, fee_before, 19)
        gross_before += 19
        fee_before += split.fee
    assert fee_before == cumulative_fee(1900) == 95


def test_split_sale_conserves_every_crown():
    split = split_sale(19, 0, 21)
    assert split.fee + split.net == 21
    assert split.fee == 2


def test_generated_codes_normalize_to_themselves():
    code = generate_shop_code()
    assert len(code) == 8
    assert normalize_shop_code(code) == code
    assert not set(code) & set("01OIL")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("abcd-2345", "ABCD2345"), (" abcd 2345 ", "ABCD2345"), ("ABC", None), ("ABCD234O", None)],
)
def test_code_normalization(raw, expected):
    assert normalize_shop_code(raw) == expected


def test_fallback_follows_the_character_name():
    assert fallback_shop_name("Alda") == "Loja de Alda"


def test_name_limit_is_36_characters():
    assert validate_shop_name("x" * 36) == "x" * 36
    with pytest.raises(MarketTextError) as error:
        validate_shop_name("x" * 37)
    assert error.value.code == "name_too_long"


def test_description_limit_is_240_characters():
    assert len(validate_shop_description("y" * 240)) == 240
    with pytest.raises(MarketTextError):
        validate_shop_description("y" * 241)


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("veja https://exemplo.com", "text_links_forbidden"),
        ("t.me/canal", "text_links_forbidden"),
        ("fale com @vendedor", "text_links_forbidden"),
        ("Sistema: sua conta caiu", "text_imitates_system"),
        ("oculto​zero", "text_invalid_characters"),
        ("<b>negrito</b>", "text_invalid_characters"),
    ],
)
def test_abusive_presentation_is_rejected(text, code):
    with pytest.raises(MarketTextError) as error:
        validate_shop_description(text)
    assert error.value.code == code


def test_line_breaks_collapse_into_one_line():
    assert validate_shop_name("Forja\n  do   Norte") == "Forja do Norte"


def test_promotion_summary_is_short():
    assert promotion_summary(None) is None
    assert promotion_summary("curta") == "curta"
    assert len(promotion_summary("z" * 200)) == 80


def test_market_opens_after_the_prologue():
    assert not market_unlocked("cinzas_na_estrada:intro")
    assert not market_unlocked("cinzas_na_estrada:tutorial")
    assert market_unlocked("menu")


def test_mythic_adds_one_confirmation_step():
    assert trade_steps_required(False) == 2
    assert trade_steps_required(True) == 3

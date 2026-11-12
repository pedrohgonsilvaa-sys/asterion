"""Screens of public Crafting Services (GDD v1.6.0 §27.3); no database needed."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from asterion.application.craft_services import (
    MyServicesView,
    OfferView,
    OrderPreview,
    ShopServicesView,
)
from asterion.application.crafting import IngredientPreview
from asterion.bot.craft_service_ui import (
    parse_ref,
    price_prompt,
    render_my_services,
    render_offer,
    render_order_preview,
    render_shop_services,
)
from asterion.domain.professions import RECIPE_DEFINITIONS, canonical_recipe

WEAPON = canonical_recipe("recipe.tdo.blacksmith.walker_weapon.comum")
WHEN = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def _offer(**overrides) -> OfferView:
    values = dict(
        offer_id=uuid4(),
        shop_id=uuid4(),
        recipe_id=WEAPON.recipe_id,
        recipe=WEAPON,
        title="Lâmina",
        price=120,
        revision=1,
        status="active",
        expires_at=WHEN,
        suspended_reason=None,
        executions=0,
    )
    values.update(overrides)
    return OfferView(**values)


def _callbacks(screen) -> list[str]:
    return [button.callback_data for row in screen.keyboard.inline_keyboard for button in row]


def test_my_services_shows_slots_republish_and_suspension():
    active = _offer(suspended_reason="profession_level")
    expired = _offer(status="expired")
    view = MyServicesView(uuid4(), (active,), (expired,), ("blacksmith",))
    screen = render_my_services(view)
    assert "1/3" in screen.text and "Suspenso" in screen.text
    callbacks = _callbacks(screen)
    assert any(data.startswith("svc:rep:") for data in callbacks)
    assert "svc:new" in callbacks


def test_public_list_and_offer_never_offer_a_suspended_service():
    view = ShopServicesView(uuid4(), "Forja", False, (_offer(),))
    assert any(data.startswith("svc:o:") for data in _callbacks(render_shop_services(view)))
    suspended = render_offer(_offer(suspended_reason="profession_inactive"))
    assert not any(data.startswith("svc:ord:") for data in _callbacks(suspended))


def test_order_preview_shows_guarantees_costs_and_leftovers():
    preview = OrderPreview(
        order_id=uuid4(),
        offer_id=uuid4(),
        recipe=WEAPON,
        title="Lâmina",
        artisan_name="Artesão",
        price=120,
        recipe_cost=30,
        total=150,
        item_level=7,
        ingredients=(IngredientPreview("material.x", "Ferro", 7, 7, 7, (("abc", 7, False),)),),
        result_bound=False,
        secondaries=1,
        delivery="Inventário",
        wallet=1000,
    )
    text = render_order_preview(preview).text
    assert "Nv.7" in text and "1 atributo(s)" in text
    assert "Taxa da Receita · 30 Coroas" in text and "Total · 150 Coroas" in text
    assert "sobra" in text


def test_price_prompt_reference_round_trips():
    index = RECIPE_DEFINITIONS.index(WEAPON)
    assert parse_ref(price_prompt(index)) == ("svc", "create", str(index))

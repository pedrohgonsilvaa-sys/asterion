"""Telegram presentation for public Crafting Services (GDD v1.6.0 §27.3).

Services live inside the artisan's Personal Shop: there is no global directory
or search. Buttons carry packed ids, never authority; CraftServiceService
revalidates owner, revision, price, Ofício and materials on every click.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.craft_services import (
    MyServicesView,
    OfferableRecipe,
    OfferView,
    OrderPreview,
    OrderResult,
    ShopServicesView,
)
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import pack
from asterion.domain.craft_services import SERVICE_SLOTS
from asterion.domain.market import MARKET_FEE_PERCENT
from asterion.domain.professions import PROFESSION_BY_ID, PROFESSION_IDS, RECIPE_DEFINITIONS

IMAGE_KEY = "market"
_REF = re.compile(r"\nRef: (svc:[\w:-]+)$")

ERROR_MESSAGES = {
    "character_missing": "Crie um personagem antes de abrir o Mercado.",
    "market_locked": "O Mercado abre quando o Prólogo terminar.",
    "foreground_locked": "Termine a atividade em andamento antes de pedir um Serviço.",
    "shop_unavailable": "Loja indisponível.",
    "unknown_profession": "Ofício desconhecido.",
    "recipe_unavailable": "Esta Receita não pode ser oferecida como Serviço.",
    "recipe_not_known": "Você não conhece esta Receita.",
    "profession_inactive": "Este Ofício não está ativo.",
    "profession_level": "Seu nível de Ofício não atende esta Receita.",
    "service_slots_full": f"Sua Loja já tem {SERVICE_SLOTS} Serviços ativos.",
    "offer_unavailable": "Este Serviço não está mais disponível.",
    "not_offer_owner": "Este Serviço não é da sua Loja.",
    "own_service": "Você não pode contratar o próprio Serviço. Use a Criação normal.",
    "artisan_unavailable": "O artesão não atende mais esta Receita agora.",
    "offer_updated": "O Serviço mudou. Confira o valor atual antes de pedir.",
    "order_stale": "Seus materiais mudaram. Abra o Serviço de novo.",
    "order_unavailable": "Este pedido não está mais disponível.",
    "preview_expired": "Esta confirmação expirou. Abra o Serviço de novo.",
    "not_enough_crowns": "Você não tem Coroas suficientes.",
    "artisan_wallet_limit": "A carteira do artesão não pode receber este valor agora.",
    "client_level": "Seu nível não atende o Grau desta Receita.",
    "materials": "Você não tem os materiais desta Receita.",
    "wrong_location": "Peça Serviços num local seguro de Criação.",
    "delivery_blocked": "Resolva suas Entregas Pendentes antes.",
    "inventory_full": "Seu Inventário não tem espaço para o resultado.",
    "invalid_price": "O preço precisa ser de pelo menos 1 Coroa.",
    "price_out_of_range": "Esse valor não pode ser registrado.",
    "price_unchanged": "O Serviço já tem esse preço.",
}
ERROR_FALLBACK = "Não foi possível concluir esta ação."

_SUSPENDED = {
    "recipe_changed": "Receita alterada por atualização",
    "recipe_not_known": "Receita desconhecida",
    "profession_inactive": "Ofício inativo",
    "profession_level": "Nível de Ofício insuficiente",
    "recipe_unavailable": "Receita indisponível",
}


def error_text(code: str) -> str:
    return ERROR_MESSAGES.get(code, ERROR_FALLBACK)


def with_ref(text: str, ref: str) -> str:
    return f"{text}\n\nRef: {ref}"


def parse_ref(text: str | None) -> tuple[str, ...] | None:
    match = _REF.search(text or "")
    return None if match is None else tuple(match.group(1).split(":"))


def _button(text: str, data: str) -> InlineKeyboardButton:
    assert len(data.encode("utf-8")) <= 64, data
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(*rows: Sequence[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(row) for row in rows])


def _crowns(value: int) -> str:
    text = f"{value:,}".replace(",", ".")
    return f"{text} Coroa" if value == 1 else f"{text} Coroas"


def _when(moment: datetime) -> str:
    return moment.strftime("%d/%m %H:%M UTC")


def _offer_line(row: OfferView) -> str:
    suffix = "" if row.suspended_reason is None else " · ⏸ Suspenso"
    return f"{row.title} · {_crowns(row.price)}{suffix}"


def recipe_token(row: OfferableRecipe | OrderPreview) -> int:
    return RECIPE_DEFINITIONS.index(row.recipe)


def render_my_services(view: MyServicesView, notice: str | None = None) -> Screen:
    lines = [f"🛠️ Meus Serviços · {len(view.offers)}/{SERVICE_SLOTS}", ""]
    lines += [f"• {_offer_line(row)}" for row in view.offers]
    if not view.offers:
        lines.append("Nenhum Serviço ativo.")
    lines += [
        "",
        "O cliente traz os materiais e paga o preço mais a taxa da Receita. "
        f"Você recebe o preço menos {MARKET_FEE_PERCENT}% (menos com a Tesouraria da Guilda). "
        "Cada oferta dura 7 dias.",
    ]
    if notice:
        lines = [notice, "", *lines]
    rows = [[_button(_offer_line(row), f"svc:own:{pack(row.offer_id)}")] for row in view.offers]
    rows += [
        [_button(f"↻ Republicar {row.title}", f"svc:rep:{pack(row.offer_id)}")]
        for row in view.expired
    ]
    if len(view.offers) < SERVICE_SLOTS and view.professions:
        rows.append([_button("Oferecer Serviço", "svc:new")])
    rows.append([_button("← Minha Loja", "mkt:mine")])
    return Screen("\n".join(lines), IMAGE_KEY, _keyboard(*rows))


def render_pick_profession(view: MyServicesView) -> Screen:
    rows = [
        [
            _button(
                f"{PROFESSION_BY_ID[item].emoji} {PROFESSION_BY_ID[item].name}",
                f"svc:prof:{PROFESSION_IDS.index(item)}",
            )
        ]
        for item in view.professions
    ]
    rows.append([_button("← Meus Serviços", "svc:mine")])
    return Screen("🛠️ Oferecer Serviço\n\nEscolha o Ofício.", IMAGE_KEY, _keyboard(*rows))


def render_offerable(profession_id: str, recipes: Sequence[OfferableRecipe]) -> Screen:
    profession = PROFESSION_BY_ID[profession_id]
    lines = [f"🛠️ {profession.name} · Receitas", ""]
    rows = []
    for row in recipes:
        if row.reason is None:
            rows.append([_button(row.recipe.name, f"svc:rec:{recipe_token(row)}")])
    hidden = sum(1 for row in recipes if row.reason is not None)
    lines.append("Escolha a Receita." if rows else "Nenhuma Receita disponível no seu nível.")
    if hidden:
        lines.append(f"{hidden} Receita(s) acima do seu nível de Ofício não aparecem.")
    rows.append([_button("← Ofícios", "svc:new")])
    return Screen("\n".join(lines), IMAGE_KEY, _keyboard(*rows))


def price_prompt(recipe_index: int) -> str:
    name = RECIPE_DEFINITIONS[recipe_index].name
    return with_ref(
        f"Oferecer {name} como Serviço. Envie o preço em Coroas (sem contar a taxa da Receita, "
        "que o cliente paga à parte).",
        f"svc:create:{recipe_index}",
    )


def edit_price_prompt(row: OfferView) -> str:
    return with_ref(
        f"Envie o novo preço de {row.title} em Coroas. Pedidos abertos com o preço antigo "
        "precisarão ser refeitos.",
        f"svc:price:{pack(row.offer_id)}",
    )


def render_own_offer(row: OfferView) -> Screen:
    token = pack(row.offer_id)
    lines = [f"🛠️ {row.title}", "", f"Preço · {_crowns(row.price)}"]
    lines.append(f"Expira em {_when(row.expires_at)}")
    lines.append(f"Execuções · {row.executions}")
    if row.suspended_reason is not None:
        reason = _SUSPENDED.get(row.suspended_reason, row.suspended_reason)
        lines += ["", f"⏸ Suspenso · {reason}. Clientes não o veem até você voltar a atender."]
    return Screen(
        "\n".join(lines),
        IMAGE_KEY,
        _keyboard(
            [_button("Editar Preço", f"svc:eprice:{token}")],
            [_button("Cancelar Serviço", f"svc:x:{token}")],
            [_button("← Meus Serviços", "svc:mine")],
        ),
    )


def render_confirm_cancel(row: OfferView) -> Screen:
    token = pack(row.offer_id)
    return Screen(
        f"Cancelar o Serviço {row.title}? Para mudar a Receita, cancele e crie outro.",
        IMAGE_KEY,
        _keyboard(
            [_button("Cancelar Serviço", f"svc:xok:{token}")],
            [_button("Voltar", f"svc:own:{token}")],
        ),
    )


def render_shop_services(view: ShopServicesView, notice: str | None = None) -> Screen:
    lines = [f"🛠️ Serviços · {view.shop_name}", ""]
    if view.offers:
        lines.append("Você traz os materiais; o artesão executa a Receita para você.")
    else:
        lines.append("Esta Loja não tem Serviços disponíveis no momento.")
    if notice:
        lines = [notice, "", *lines]
    rows = [
        [_button(_offer_line(row), f"svc:o:{pack(row.offer_id)}")]
        for row in view.offers
        if not view.is_owner
    ]
    rows.append([_button("← Mercado", "mkt:root")])
    return Screen("\n".join(lines), IMAGE_KEY, _keyboard(*rows))


def render_offer(row: OfferView, notice: str | None = None) -> Screen:
    head = f"{notice}\n\n" if notice else ""
    recipe = row.recipe
    lines = [f"{head}🛠️ {row.title}"]
    if recipe is not None and recipe.rarity:
        lines.append(recipe.rarity)
    lines += [
        "",
        f"Preço do Serviço · {_crowns(row.price)}",
        "Mais a taxa da Receita, mostrada no pedido.",
        f"Expira em {_when(row.expires_at)}",
    ]
    rows = []
    if row.available:
        rows.append([_button("Pedir Serviço", f"svc:ord:{pack(row.offer_id)}")])
    rows.append([_button("← Serviços da Loja", f"svc:shop:{pack(row.shop_id)}")])
    return Screen("\n".join(lines), IMAGE_KEY, _keyboard(*rows))


def _ingredient_lines(preview: OrderPreview) -> list[str]:
    lines = []
    for item in preview.ingredients:
        lines.append(f"{item.name} · {item.required}")
        parts = []
        for stack_id, quantity, bound in item.consumed_stacks:
            place = "Armazém" if stack_id.startswith("warehouse:") else "Inventário"
            parts.append(f"{quantity} · {place}{' · Vinculado' if bound else ''}")
        if parts:
            lines.append("  Consumir · " + ", ".join(parts))
    return lines


def render_order_preview(preview: OrderPreview) -> Screen:
    """§27.3: guarantees and the parts rolled at commit, never a promised roll."""
    recipe = preview.recipe
    lines = [
        "🧾 Pedido de Serviço",
        "",
        f"{preview.title} · por {preview.artisan_name}",
    ]
    if preview.item_level is not None:
        slot = recipe.output_slot or "Equipamento"
        lines.append(f"Garantido · {recipe.rarity} · {slot} · Nv.{preview.item_level}")
    if preview.secondaries:
        lines.append(f"Sorteado ao confirmar · {preview.secondaries} atributo(s) secundário(s)")
    elif preview.secondaries == 0:
        lines.append("Sem atributos sorteados.")
    if recipe.output_kind in {"equipment", "rune"}:
        lines.append("🔗 Vinculado" if preview.result_bound else "🔓 Negociável")
    lines += ["", "🧱 Seus materiais", *_ingredient_lines(preview)]
    lines += [
        "",
        f"Preço do Serviço · {_crowns(preview.price)}",
        f"Taxa da Receita · {_crowns(preview.recipe_cost)}",
        f"Total · {_crowns(preview.total)}",
        f"Sua carteira · {_crowns(preview.wallet)}",
        f"🎒 Destino · {preview.delivery}",
        "",
        "O resultado e qualquer sobra ficam com você.",
    ]
    return Screen(
        "\n".join(lines),
        IMAGE_KEY,
        _keyboard(
            [_button("Confirmar pedido", f"svc:cf:{pack(preview.order_id)}")],
            [_button("Cancelar", f"svc:o:{pack(preview.offer_id)}")],
        ),
    )


def render_order_done(result: OrderResult) -> Screen:
    lines = ["✅ Serviço concluído", "", result.title]
    if result.item_level is not None:
        lines.append(f"Nv.{result.item_level}")
    lines += [
        f"Total pago · {_crowns(result.price + result.recipe_cost)}",
        f"🎒 Destino · {result.delivery}",
    ]
    return Screen("\n".join(lines), IMAGE_KEY, _keyboard([_button("← Mercado", "mkt:root")]))


def service_notice(result: OrderResult) -> str:
    return (
        f"🛠️ Serviço executado na sua Loja: {result.title} para {result.client_name}.\n"
        f"Recebido · {_crowns(result.net)} (taxa {_crowns(result.fee)})"
    )

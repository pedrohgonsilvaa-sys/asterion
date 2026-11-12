"""Telegram presentation for Mercado, Loja Pessoal and Troca Direta (GDD v1.6.0 §28, §29).

Buttons carry packed ids and terms, never authority: the services revalidate
owner, server, price and state in their own transaction on every click.
Free-text prompts end in a "Ref:" line so a reply finds its action again.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.item_escrow import NegotiableEntry
from asterion.application.market import (
    ListingView,
    Promotion,
    PurchasePreview,
    PurchaseResult,
    ShopView,
)
from asterion.application.trades import TradeItemView, TradeView
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import pack
from asterion.domain.market import (
    LISTING_SLOTS,
    MARKET_FEE_PERCENT,
    SHOP_DESCRIPTION_MAX,
    SHOP_NAME_MAX,
)

IMAGE_KEY = "market"
PAGE_SIZE = 8
KIND_CODES = {"equipment": "e", "material": "m", "consumable": "c", "rune": "r"}
KIND_BY_CODE = {code: kind for kind, code in KIND_CODES.items()}
KIND_LABELS = (
    ("equipment", "Equipamentos"),
    ("material", "Materiais"),
    ("consumable", "Consumíveis"),
    ("rune", "Runas"),
)

_REF = re.compile(r"\nRef: ((?:mkt|trd):[\w:-]+)$")

ERROR_MESSAGES = {
    "character_missing": "Crie um personagem antes de abrir o Mercado.",
    "market_locked": "O Mercado abre quando o Prólogo terminar.",
    "foreground_locked": "Termine a atividade em andamento antes de mexer nos itens.",
    "shop_unavailable": "Loja indisponível ou Código inválido. Confira e tente de novo.",
    "search_rate_limited": "Muitas buscas seguidas. Aguarde um pouco e tente de novo.",
    "listing_slots_full": "Sua Loja já tem 6 ofertas ativas.",
    "listing_unavailable": "Esta oferta não está mais disponível.",
    "not_listing_owner": "Esta oferta não é da sua Loja.",
    "own_listing": "Você não pode comprar a própria oferta.",
    "offer_updated": "A oferta mudou. Confira o valor atual antes de comprar.",
    "insufficient_quantity": "Não há quantidade suficiente nesta oferta.",
    "not_enough_crowns": "Você não tem Coroas suficientes.",
    "inventory_full": "Seu Inventário não tem espaço para este item.",
    "preview_expired": "Esta confirmação expirou. Abra a oferta de novo.",
    "purchase_unavailable": "Esta compra não está mais disponível.",
    "seller_wallet_limit": "A carteira do vendedor não pode receber este valor agora.",
    "mythic_confirmation_required": "Item Mítico precisa de confirmação extra.",
    "invalid_price": "O preço precisa ser de pelo menos 1 Coroa.",
    "price_out_of_range": "Esse valor não pode ser registrado.",
    "price_unchanged": "A oferta já tem esse preço.",
    "invalid_quantity": "Quantidade inválida.",
    "invalid_kind": "Tipo de item inválido.",
    "item_unavailable": "Este item não está mais disponível.",
    "item_equipped": "Desequipe o item antes de negociar.",
    "item_bound": "Item vinculado não pode ser negociado.",
    "item_locked": "Desbloqueie o item antes de negociar.",
    "item_component_bound": "Remova o componente vinculado antes de negociar.",
    "promotion_cooldown": "Você divulgou a Loja há pouco. A recarga é de 30 minutos.",
    "promotion_failed": "Não foi possível publicar agora. Tente de novo.",
    "name_empty": "O nome não pode ficar vazio.",
    "name_too_long": f"O nome pode ter até {SHOP_NAME_MAX} caracteres.",
    "description_empty": "A descrição não pode ficar vazia.",
    "description_too_long": f"A descrição pode ter até {SHOP_DESCRIPTION_MAX} caracteres.",
    "text_invalid_characters": "O texto tem caracteres não permitidos.",
    "text_links_forbidden": "Links e menções não são permitidos.",
    "text_imitates_system": "O texto não pode imitar mensagens do sistema.",
    "partner_unavailable": "Personagem não encontrado neste servidor.",
    "self_trade": "Você não pode trocar consigo mesmo.",
    "trade_busy": "Um dos personagens já está em outra Troca.",
    "trade_unavailable": "Esta Troca não está mais ativa.",
    "not_invited": "Este convite não é para você.",
    "not_a_party": "Você não participa desta Troca.",
    "trade_changed": "A Troca mudou. Confira os itens e confirme de novo.",
    "trade_empty": "Adicione ao menos um item antes de confirmar.",
    "waiting_partner": "Aguarde a confirmação do outro jogador.",
}
ERROR_FALLBACK = "Não foi possível concluir esta ação."


def error_text(code: str) -> str:
    return ERROR_MESSAGES.get(code, ERROR_FALLBACK)


def with_ref(text: str, ref: str) -> str:
    return f"{text}\n\nRef: {ref}"


def parse_ref(text: str | None) -> tuple[str, ...] | None:
    match = _REF.search(text or "")
    return None if match is None else tuple(match.group(1).split(":"))


def parse_whole(raw: str) -> int | None:
    cleaned = raw.strip().replace(".", "")
    if not cleaned.isascii() or not cleaned.isdigit() or len(cleaned) > 19:
        return None
    return int(cleaned)


def _button(text: str, data: str) -> InlineKeyboardButton:
    assert len(data.encode("utf-8")) <= 64, data
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(*rows: Sequence[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(row) for row in rows])


def number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _when(moment: datetime) -> str:
    return moment.strftime("%d/%m %H:%M UTC")


def _rarity(rarity: str | None) -> str:
    return f" · {rarity}" if rarity else ""


def _crowns(value: int) -> str:
    return f"{number(value)} Coroa" if value == 1 else f"{number(value)} Coroas"


def _offer_price(row: ListingView) -> str:
    if row.initial > 1:
        return f"{row.remaining}× · {_crowns(row.unit_price)} cada"
    return _crowns(row.unit_price)


def render_root(trade: TradeView | None) -> Screen:
    label = "Troca Direta" if trade is None else "Troca Direta · em andamento"
    return Screen(
        "🛒 Mercado\n\nEncontre uma Loja pelo Código, cuide da sua ou troque itens direto "
        "com outro jogador.",
        IMAGE_KEY,
        _keyboard(
            [_button("Buscar Loja", "mkt:search")],
            [_button("Minha Loja", "mkt:mine")],
            [_button(label, "trd:root")],
            [_button("← Menu", "menu:back")],
        ),
    )


def render_my_shop(shop: ShopView, notice: str | None = None) -> Screen:
    lines = [f"🏪 {shop.name}", f"Código · {shop.code}"]
    if shop.description:
        lines += ["", shop.description]
    lines += ["", f"Ofertas ativas · {len(shop.listings)}/{LISTING_SLOTS}"]
    lines += [f"• {row.title} · {_offer_price(row)}" for row in shop.listings]
    if notice:
        lines = [notice, "", *lines]
    rows = [
        [_button(f"{row.title} · {_offer_price(row)}", f"mkt:own:{pack(row.listing_id)}")]
        for row in shop.listings
    ]
    if len(shop.listings) < LISTING_SLOTS:
        rows.append([_button("Adicionar oferta", "mkt:add")])
    rows.append([_button("🛠️ Meus Serviços", "svc:mine")])
    rows.append([_button("Editar Loja", "mkt:edit"), _button("Divulgar Loja", "mkt:promote")])
    rows.append([_button("← Mercado", "mkt:root")])
    return Screen("\n".join(lines), IMAGE_KEY, _keyboard(*rows))


def render_public_shop(shop: ShopView, notice: str | None = None) -> Screen:
    lines = [f"🏪 {shop.name}", f"Código · {shop.code}"]
    if shop.description:
        lines += ["", shop.description]
    lines.append("")
    if shop.listings:
        lines.append("Ofertas disponíveis:")
    else:
        lines.append("Não existem ofertas disponíveis no momento.")
    if notice:
        lines = [notice, "", *lines]
    rows = [
        [_button(f"{row.title} · {_offer_price(row)}", f"mkt:l:{pack(row.listing_id)}")]
        for row in shop.listings
    ]
    # §27.3: Services are found only here, inside the artisan's Shop.
    rows.append([_button("🛠️ Serviços da Loja", f"svc:shop:{pack(shop.shop_id)}")])
    rows.append([_button("Buscar outra Loja", "mkt:search")])
    rows.append([_button("← Mercado", "mkt:root")])
    return Screen("\n".join(lines), IMAGE_KEY, _keyboard(*rows))


def render_edit_shop(shop: ShopView) -> Screen:
    rows = [[_button("Editar Nome", "mkt:ename")]]
    if shop.has_custom_name:
        rows.append([_button("Remover Nome", "mkt:cname")])
    rows.append([_button("Editar Descrição", "mkt:edesc")])
    if shop.description:
        rows.append([_button("Remover Descrição", "mkt:cdesc")])
    rows.append([_button("← Minha Loja", "mkt:mine")])
    return Screen(
        f"✏️ Editar Loja\n\nNome · {shop.name}\n\nO Código da Loja nunca muda.",
        IMAGE_KEY,
        _keyboard(*rows),
    )


def render_kinds(prefix: str, title: str, back: str) -> Screen:
    rows = [[_button(label, f"{prefix}:src:{KIND_CODES[kind]}:0")] for kind, label in KIND_LABELS]
    rows.append([_button("← Voltar", back)])
    return Screen(f"{title}\n\nEscolha o tipo de item.", IMAGE_KEY, _keyboard(*rows))


def render_sources(
    prefix: str, kind: str, entries: Sequence[NegotiableEntry], page: int, back: str
) -> Screen:
    eligible = [entry for entry in entries if entry.eligible]
    hidden = len(entries) - len(eligible)
    start = max(page, 0) * PAGE_SIZE
    code = KIND_CODES[kind]
    rows = []
    for entry in eligible[start : start + PAGE_SIZE]:
        suffix = f" ×{entry.quantity}" if entry.quantity > 1 else ""
        rows.append(
            [
                _button(
                    f"{entry.title}{_rarity(entry.rarity)}{suffix}",
                    f"{prefix}:pick:{code}:{pack(entry.id)}:{entry.quantity}",
                )
            ]
        )
    nav = []
    if page > 0:
        nav.append(_button("‹", f"{prefix}:src:{code}:{page - 1}"))
    if start + PAGE_SIZE < len(eligible):
        nav.append(_button("›", f"{prefix}:src:{code}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([_button("← Voltar", back)])
    text = "Escolha o item." if eligible else "Nenhum item Negociável deste tipo no Inventário."
    if hidden:
        text += f"\n\n{hidden} item(ns) vinculado(s), equipado(s) ou travado(s) não aparecem."
    return Screen(text, IMAGE_KEY, _keyboard(*rows))


def listing_prompt(kind: str, source_id: UUID, title: str, available: int) -> str:
    ref = f"mkt:list:{KIND_CODES[kind]}:{pack(source_id)}:{available}"
    if available > 1:
        text = (
            f"Anunciar {title} (você tem {available}). Envie a quantidade e o preço por unidade, "
            "separados por espaço. Exemplo: 5 120"
        )
    else:
        text = f"Anunciar {title}. Envie o preço de venda em Coroas."
    return with_ref(
        f"{text} A venda paga {MARKET_FEE_PERCENT}% de taxa, menos com a Tesouraria da Guilda.",
        ref,
    )


def render_confirm_mythic_listing(kind: str, source_id: UUID, quantity: int, price: int) -> Screen:
    data = f"mkt:lm:{KIND_CODES[kind]}:{pack(source_id)}:{quantity}:{price}"
    return Screen(
        f"⚠️ Item Mítico\n\nConfirme que quer colocar este item à venda por {_crowns(price)}.",
        IMAGE_KEY,
        _keyboard([_button("Confirmar anúncio", data)], [_button("Cancelar", "mkt:mine")]),
    )


def render_own_listing(row: ListingView) -> Screen:
    token = pack(row.listing_id)
    return Screen(
        f"📦 {row.title}{_rarity(row.rarity)}\n\n{_offer_price(row)}\n"
        f"Expira em {_when(row.expires_at)}",
        IMAGE_KEY,
        _keyboard(
            [_button("Editar Preço", f"mkt:eprice:{token}")],
            [_button("Remover da Loja", f"mkt:rm:{token}")],
            [_button("← Minha Loja", "mkt:mine")],
        ),
    )


def render_confirm_remove(row: ListingView) -> Screen:
    token = pack(row.listing_id)
    return Screen(
        f"Remover {row.title} da Loja? {row.remaining}× voltam para você.",
        IMAGE_KEY,
        _keyboard(
            [_button("Remover", f"mkt:rmok:{token}")],
            [_button("Voltar", f"mkt:own:{token}")],
        ),
    )


def render_listing(row: ListingView, notice: str | None = None) -> Screen:
    head = f"{notice}\n\n" if notice else ""
    return Screen(
        f"{head}📦 {row.title}{_rarity(row.rarity)}\n\n{_offer_price(row)}\n"
        f"Expira em {_when(row.expires_at)}",
        IMAGE_KEY,
        _keyboard(
            [_button("Comprar", f"mkt:buy:{pack(row.listing_id)}:{row.remaining}")],
            [_button("← Mercado", "mkt:root")],
        ),
    )


def render_purchase_preview(preview: PurchasePreview) -> Screen:
    action = "mkt:cm" if preview.mythic else "mkt:cp"
    return Screen(
        f"🧾 Confirmar compra\n\n{preview.title} × {preview.quantity}\n"
        f"Preço por unidade · {_crowns(preview.unit_price)}\n"
        f"Total · {_crowns(preview.total)}\n\nSua carteira · {_crowns(preview.wallet)}",
        IMAGE_KEY,
        _keyboard(
            [_button("Confirmar compra", f"{action}:{pack(preview.purchase_id)}")],
            [_button("Cancelar", "mkt:root")],
        ),
    )


def render_confirm_mythic_purchase(purchase_id: UUID) -> Screen:
    return Screen(
        "⚠️ Item Mítico\n\nEsta é a confirmação final da compra.",
        IMAGE_KEY,
        _keyboard(
            [_button("Comprar item Mítico", f"mkt:cp2:{pack(purchase_id)}")],
            [_button("Cancelar", "mkt:root")],
        ),
    )


def render_purchase_done(result: PurchaseResult) -> Screen:
    return Screen(
        f"✅ Compra concluída\n\n{result.title} × {result.quantity}\n"
        f"Total pago · {_crowns(result.gross)}",
        IMAGE_KEY,
        _keyboard([_button("← Mercado", "mkt:root")]),
    )


def sale_notice(result: PurchaseResult) -> str:
    return (
        f"🪙 Venda na sua Loja: {result.title} × {result.quantity}.\n"
        f"Recebido · {_crowns(result.net)} (taxa {_crowns(result.fee)})"
    )


def promotion_text(promotion: Promotion) -> str:
    lines = [
        f"🛒 {promotion.shop_name}",
        f"De {promotion.owner_name}",
        f"Código · {promotion.code}",
        f"Ofertas disponíveis · {promotion.offers}",
    ]
    if promotion.summary:
        lines += ["", promotion.summary]
    return "\n".join(lines)


def promotion_keyboard(link: str | None) -> InlineKeyboardMarkup | None:
    if link is None:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Abrir Loja", url=link)]]
    )


def render_promotion_copy(promotion: Promotion, link: str | None) -> Screen:
    body = promotion_text(promotion)
    if link:
        body += f"\n{link}"
    return Screen(
        f"Copie o texto abaixo e publique no tópico Mercado da Comunidade:\n\n{body}",
        IMAGE_KEY,
        _keyboard([_button("← Minha Loja", "mkt:mine")]),
    )


# ------------------------------------------------------------- Direct Trade


def _trade_lines(items: Sequence[TradeItemView]) -> list[str]:
    if not items:
        return ["• nada ainda"]
    return [f"• {item.title}{_rarity(item.rarity)} × {item.quantity}" for item in items]


def render_trade_start() -> Screen:
    return Screen(
        "🤝 Troca Direta\n\nTroque itens Negociáveis ou dê um presente a outro jogador. "
        "Coroas não entram na Troca.",
        IMAGE_KEY,
        _keyboard(
            [_button("Convidar jogador", "trd:invite")],
            [_button("← Mercado", "mkt:root")],
        ),
    )


def render_trade(view: TradeView, notice: str | None = None) -> Screen:
    token = pack(view.trade_id)
    head = f"{notice}\n\n" if notice else ""
    if view.status == "invited" and not view.viewer_is_initiator:
        return Screen(
            f"{head}🤝 {view.counterpart_name} convidou você para uma Troca Direta.",
            IMAGE_KEY,
            _keyboard(
                [_button("Aceitar", f"trd:yes:{token}"), _button("Recusar", f"trd:no:{token}")],
                [_button("← Mercado", "mkt:root")],
            ),
        )
    if view.status == "invited":
        return Screen(
            f"{head}🤝 Aguardando {view.counterpart_name} aceitar a Troca.",
            IMAGE_KEY,
            _keyboard(
                [_button("Cancelar convite", f"trd:x:{token}")],
                [_button("← Mercado", "mkt:root")],
            ),
        )
    lines = [
        f"{head}🤝 Troca com {view.counterpart_name}",
        "",
        "Você oferece:",
        *_trade_lines(view.my_items),
        "",
        f"{view.counterpart_name} oferece:",
        *_trade_lines(view.their_items),
        "",
        f"Sua confirmação · {view.my_steps}/{view.steps_required}",
        f"Confirmação de {view.counterpart_name} · {view.their_steps}/{view.steps_required}",
        f"Expira às {_when(view.expires_at)} se ninguém agir.",
    ]
    if view.steps_required > 2:
        lines.append("⚠️ Há item Mítico: uma confirmação extra é exigida.")
    rows = [[_button("Adicionar item", "trd:add")]]
    if view.my_items:
        rows.append([_button("Retirar item", "trd:out")])
    if view.my_steps < view.steps_required:
        label = f"Confirmar ({view.my_steps + 1}/{view.steps_required})"
        rows.append([_button(label, f"trd:c:{token}:{view.revision}")])
    rows.append([_button("Atualizar", "trd:root"), _button("Cancelar Troca", f"trd:x:{token}")])
    rows.append([_button("← Mercado", "mkt:root")])
    return Screen("\n".join(lines), IMAGE_KEY, _keyboard(*rows))


def render_trade_withdraw(view: TradeView) -> Screen:
    token = pack(view.trade_id)
    rows = [
        [
            _button(
                f"{item.title} × {item.quantity}",
                f"trd:rm:{token}:{pack(item.item_id)}",
            )
        ]
        for item in view.my_items
    ]
    rows.append([_button("← Troca", "trd:root")])
    return Screen("Qual item retirar da Troca?", IMAGE_KEY, _keyboard(*rows))


def render_trade_closed(text: str) -> Screen:
    return Screen(text, IMAGE_KEY, _keyboard([_button("← Mercado", "mkt:root")]))


def trade_quantity_prompt(kind: str, source_id: UUID, available: int) -> str:
    return with_ref(
        f"Quantas unidades oferecer? Você tem {available}.",
        f"trd:qty:{KIND_CODES[kind]}:{pack(source_id)}:{available}",
    )

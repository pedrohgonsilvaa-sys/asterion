"""Telegram screens for Apoiar Asterion: Patrono, Passe da Crônica and orders (GDD §35)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.payments import OrderView, ShopView
from asterion.bot.creation_ui import Screen
from asterion.domain.chronicle import TIMEZONE
from asterion.domain.payments import (
    CHRONICLE_PASS,
    CREATED,
    EXPIRED,
    PAID,
    PATRON,
    PATRON_DAYS,
    PATRON_PRESTIGE,
    PATRON_TEMPORARY_COSMETICS,
    PRODUCTS,
    REFUND_WINDOW,
    REFUNDED,
    REVERSED,
    TERMS_VERSION,
    format_brl,
)

_IMAGE = "menu"

_ERRORS = {
    "payments_disabled": "As compras ainda não estão disponíveis.",
    "terms_outdated": "Os termos mudaram. Abra a loja de novo e leia a versão atual.",
    "chronicle_pass_closed": "O Passe só pode ser comprado enquanto a Crônica está aberta.",
    "chronicle_pass_active": "Seu Passe da Crônica já está ativo neste servidor.",
    "provider_unavailable": "O pagamento está indisponível agora. Tente de novo em instantes.",
    "unknown_product": "Este produto não existe.",
}

_STATUS = {
    CREATED: "⏳ Aguardando pagamento",
    PAID: "✅ Pago",
    EXPIRED: "⌛ Expirado",
    REFUNDED: "↩️ Reembolsado",
    REVERSED: "↩️ Estornado",
}


def error_text(code: str) -> str:
    return _ERRORS.get(code, "Esta ação não está mais disponível.")


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _when(moment) -> str:
    return moment.astimezone(TIMEZONE).strftime("%d/%m/%Y %H:%M")


_TEMPORARY = " e ".join(
    f"{'Título' if kind == 'title' else 'Moldura'} {name}"
    for _, kind, name in PATRON_TEMPORARY_COSMETICS
)
_PRESTIGE_DAYS = "/".join(str(days) for days, _ in PATRON_PRESTIGE)


def render_shop(view: ShopView, notice: str | None = None) -> Screen:
    lines = ["🕯️ Apoiar Asterion", ""]
    if notice:
        lines.extend([notice, ""])
    lines.extend(
        [
            "O apoio mantém Asterion vivo. Só concede cosméticos e prestígio: "
            "nada de XP, Coroas, itens, combate ou progressão.",
            "",
        ]
    )
    patron_price = view.prices.get(PATRON)
    pass_price = view.prices.get(CHRONICLE_PASS)
    lines.append(
        "👑 Patrono de Asterion"
        + (f" · {format_brl(patron_price)} por {PATRON_DAYS} dias" if patron_price else "")
    )
    lines.append(f"{_TEMPORARY} enquanto ativo.")
    lines.append(f"Prestígio permanente aos {_PRESTIGE_DAYS} dias de apoio acumulado.")
    if view.patron_active and view.patron_until is not None:
        lines.append(f"Status: ativo até {_when(view.patron_until)}.")
    else:
        lines.append("Status: inativo.")
    if view.patron_paid_days:
        lines.append(f"Apoio acumulado: {view.patron_paid_days} dias.")
    if view.patron_prestige:
        lines.append("Prestígio: " + ", ".join(view.patron_prestige) + ".")
    lines.extend(
        [
            "",
            "📜 Passe da Crônica" + (f" · {format_brl(pass_price)}" if pass_price else ""),
            "Libera a camada Premium da Trilha desta Crônica, inclusive nos Marcos já alcançados.",
        ]
    )
    if view.pass_active:
        lines.append("Status: ativo.")
    elif not view.pass_open:
        lines.append("Status: fora de uma Crônica aberta.")
    else:
        lines.append("Status: disponível.")
    rows = []
    if not view.enabled:
        lines.extend(["", "As compras ainda não estão disponíveis."])
    else:
        if patron_price:
            label = "Renovar Patrono" if view.patron_active else "Ser Patrono"
            rows.append([_button(f"👑 {label}", f"pay:t:{PATRON}")])
        if pass_price and view.pass_open and not view.pass_active:
            rows.append([_button("📜 Comprar Passe da Crônica", f"pay:t:{CHRONICLE_PASS}")])
    rows.append([_button("🧾 Meus pedidos", "pay:orders")])
    rows.append([_button("← Benefícios", "bn:root")])
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def terms_text(product_id: str, price_cents: int, link_minutes: int) -> str:
    product = PRODUCTS[product_id]
    if product_id == PATRON:
        what = (
            f"• {PATRON_DAYS} dias de Patrono, somados ao tempo que você já tiver. "
            "Vale para toda a conta."
        )
    else:
        what = (
            "• Libera a camada Premium da Trilha desta Crônica neste servidor, inclusive "
            "nos Marcos já alcançados. Não pode ser comprado depois do fim da Crônica."
        )
    days = REFUND_WINDOW.days
    return "\n".join(
        [
            f"📄 Termos de compra · {product.name}",
            f"Versão {TERMS_VERSION}",
            "",
            f"Valor: {format_brl(price_cents)}.",
            what,
            "• Só concede cosméticos e prestígio. Não dá XP, Coroas, itens, combate nem "
            "progressão. Não pode ser trocado nem vendido no Mercado.",
            "• Pagamento por Pix ou cartão no checkout da InfinitePay, fora do Telegram.",
            "• O benefício é liberado sozinho depois que o pagamento é confirmado.",
            f"• O link de pagamento vale {link_minutes} minutos.",
            f"• Reembolso: até {days} dias após o pagamento, sem perguntas, pelo suporte do "
            "jogo. Depois disso, só em caso de erro nosso.",
            "• O reembolso remove apenas o que esta compra concedeu.",
            "• Pedidos de reembolso repetidos podem ser analisados.",
        ]
    )


def render_terms(product_id: str, price_cents: int, link_minutes: int) -> Screen:
    return Screen(
        terms_text(product_id, price_cents, link_minutes),
        _IMAGE,
        _keyboard(
            [
                [
                    _button(
                        "✅ Aceito os termos e quero pagar",
                        f"pay:b:{product_id}:{TERMS_VERSION}",
                    )
                ],
                [_button("← Apoiar Asterion", "pay:root")],
            ]
        ),
    )


def render_checkout(order: OrderView) -> Screen:
    lines = [
        f"🧾 Pedido criado: {order.product_name}",
        "",
        f"Valor: {format_brl(order.amount_cents)}.",
    ]
    if order.expires_at is not None:
        lines.append(f"Pague até {_when(order.expires_at)}.")
    lines.extend(
        [
            "",
            "Toque em Pagar, escolha Pix e pague no app do seu banco.",
            "O benefício é liberado sozinho quando o pagamento for confirmado. "
            "Você vai receber uma mensagem aqui.",
        ]
    )
    rows = []
    if order.checkout_url:
        rows.append([InlineKeyboardButton(text="💳 Pagar", url=order.checkout_url)])
    rows.append([_button("🧾 Meus pedidos", "pay:orders")])
    rows.append([_button("← Apoiar Asterion", "pay:root")])
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def render_orders(orders: list[OrderView], now) -> Screen:
    lines = ["🧾 Meus pedidos", ""]
    rows = []
    if not orders:
        lines.append("Nenhum pedido ainda.")
    for order in orders:
        status = _STATUS.get(order.status, order.status)
        if order.status == PAID and order.grant_error:
            status += " · liberação pendente"
        lines.append(
            f"{_when(order.created_at)} · {order.product_name} · "
            f"{format_brl(order.amount_cents)} · {status}"
        )
        if (
            order.status == CREATED
            and order.checkout_url
            and order.expires_at is not None
            and order.expires_at > now
            and len(rows) < 3
        ):
            label = f"💳 Pagar · {order.product_name}"
            rows.append([InlineKeyboardButton(text=label, url=order.checkout_url)])
    lines.extend(["", "Dúvidas ou reembolso: fale com o suporte do jogo."])
    rows.append([_button("← Apoiar Asterion", "pay:root")])
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))

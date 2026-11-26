"""Telegram screens for Apoiar Asterion: Patrono, Passe da Crônica and orders (GDD §35)."""

from __future__ import annotations

from html import escape

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


_PRODUCT_EMOJI = {PATRON: "👑", CHRONICLE_PASS: "📜"}
_ORDER_STATUS = {
    CREATED: "⏳ <b>Aguardando pagamento</b>",
    PAID: "✅ <b>Pago</b>",
    EXPIRED: "⏳ <b>Expirado</b>",
    REFUNDED: "↩️ <b>Reembolsado</b>",
    REVERSED: "↩️ <b>Estornado</b>",
}
_BACK = [_button("↩️ Retornar", "pay:root")]
SUPPORT_TEXT = (
    "O apoio mantém Asterion vivo. O Patrono concede uma skin exclusiva, o título Patrono "
    "das Cinzas, a moldura Vigília do Patrono e prestígio permanente."
)


def _html(*parts: str | None) -> str:
    return "\n\n".join(part for part in parts if part)


def _m(text: str) -> str:
    return f"<code>{escape(text)}</code>"


def _days_list() -> str:
    days = [str(value) for value, _ in PATRON_PRESTIGE]
    return ", ".join(days[:-1]) + f" e {days[-1]}" if len(days) > 1 else days[0]


def render_shop(view: ShopView, notice: str | None = None) -> Screen:
    """Apoiar Asterion (decisão do autor 2026-11-26 §31.1)."""
    patron_price = view.prices.get(PATRON)
    price = (
        f"💰 {_m(format_brl(patron_price))} · {_m(f'{PATRON_DAYS} dias')}"
        if patron_price
        else f"⏳ {_m(f'{PATRON_DAYS} dias')}"
    )
    return Screen(
        _html(
            escape(notice) if notice else None,
            "🕯️ <b>Apoiar Asterion</b>",
            f"<i>{escape(SUPPORT_TEXT)}</i>",
            f"👑 <b>Patrono de Asterion</b>\n{price}",
            "🏅 <b>Prestígio</b>\n"
            f"<i>Reconhecimentos permanentes aos {_days_list()} dias de apoio acumulado.</i>",
            "📜 <b>Passe da Crônica</b>\n<i>Libera a camada Premium da Trilha da Crônica "
            "desta Crônica, inclusive nos Marcos já alcançados.</i>",
        ),
        _IMAGE,
        _keyboard(
            [
                [_button("👑 Patrono", f"pay:t:{PATRON}"), _button("📜 Crônica", "pay:pass")],
                [_button("🧾 Pedidos", "pay:orders")],
                [_button("↩️ Retornar", "bn:root")],
            ]
        ),
        "HTML",
    )


def terms_text(product_id: str, price_cents: int, link_minutes: int) -> str:
    """Termos (§31.2). ``link_minutes`` fica na assinatura por compatibilidade."""
    product = PRODUCTS[product_id]
    if product_id == PATRON:
        title = "📄 <b>Termos do Patrono de Asterion</b>"
        duration = f"\n⏳ <b>Duração</b> · {_m(f'{PATRON_DAYS} dias')}"
        benefit = (
            "O Patrono concede uma skin, título e moldura exclusivas conforme o tempo de "
            "apoio acumulado. No entanto, não concede XP, Coroas, itens, combate ou "
            "progressão. O benefício não pode ser trocado nem vendido no Mercado."
        )
    else:
        title = f"📄 <b>Termos do {escape(product.name)}</b>"
        duration = ""
        benefit = (
            "O Passe libera a camada Premium da Trilha desta Crônica neste servidor, "
            "inclusive nos Marcos já alcançados. Não concede XP, Coroas, itens, combate ou "
            "progressão e não pode ser trocado nem vendido no Mercado."
        )
    return _html(
        title,
        f"💰 <b>Valor</b> · {_m(format_brl(price_cents))}{duration}",
        f"🎁 <b>Benefícios</b>\n\n<i>{escape(benefit)}</i>",
        "💳 <b>Pagamento</b>\n\n<i>O pagamento é realizado por Pix ou cartão no checkout "
        "externo. Após a confirmação, o benefício é liberado automaticamente.</i>",
        "🔄 <b>Reembolso</b>\n\n<i>Reembolsos seguem as condições de suporte e dos termos "
        "da compra.</i>",
    )


def render_terms(product_id: str, price_cents: int, link_minutes: int) -> Screen:
    return Screen(
        terms_text(product_id, price_cents, link_minutes),
        _IMAGE,
        _keyboard(
            [
                [_button("✅ Aceitar", f"pay:b:{product_id}:{TERMS_VERSION}")],
                _BACK,
            ]
        ),
        "HTML",
    )


def render_checkout(order: OrderView) -> Screen:
    """Pedido criado (§31.4)."""
    rows = []
    if order.checkout_url:
        rows.append([InlineKeyboardButton(text="💳 Pagar", url=order.checkout_url)])
    rows.append([_button("🧾 Pedidos", "pay:orders")])
    rows.append(_BACK)
    product = "Patrono" if order.product == PATRON else order.product_name
    return Screen(
        _html(
            f"🧾 <b>Pedido do {escape(product)}</b>",
            f"💰 <b>Valor</b> · {_m(format_brl(order.amount_cents))}\n"
            f"⏳ <b>Status</b> · {_m('Aguardando pagamento')}",
            "<i>Pague pelo checkout para concluir a compra. O benefício será liberado "
            "automaticamente quando o pagamento for confirmado.</i>",
        ),
        _IMAGE,
        _keyboard(rows),
        "HTML",
    )


def render_orders(orders: list[OrderView], now) -> Screen:
    """Meus Pedidos (§31.3)."""
    blocks = []
    pay_url = None
    for order in orders:
        status = _ORDER_STATUS.get(order.status, escape(order.status))
        if order.status == PAID and order.grant_error:
            status += " · <b>liberação pendente</b>"
        emoji = _PRODUCT_EMOJI.get(order.product, "🧾")
        local = order.created_at.astimezone(TIMEZONE)
        blocks.append(
            f"<b>{local:%d/%m/%Y, %H:%M}</b>\n"
            f"{emoji} <b>{escape(order.product_name)}</b>\n"
            f"💰 {_m(format_brl(order.amount_cents))} · {status}"
        )
        if (
            pay_url is None
            and order.status == CREATED
            and order.checkout_url
            and order.expires_at is not None
            and order.expires_at > now
        ):
            pay_url = order.checkout_url
    rows = []
    if pay_url:
        rows.append([InlineKeyboardButton(text="💳 Pagar", url=pay_url)])
    rows.append(_BACK)
    return Screen(
        _html(
            "🧾 <b>Meus Pedidos</b>",
            "\n\n".join(blocks) if blocks else "<code>❌ Vazio.</code>",
            "<i>Dúvidas ou solicitações de reembolso: fale com o suporte do jogo.</i>",
        ),
        _IMAGE,
        _keyboard(rows),
        "HTML",
    )


def render_pass(view: ShopView) -> Screen:
    """Passe da Crônica (§31.5). Sem Crônica aberta, a tela é só informativa."""
    if view.pass_active:
        current, status = "Aberta", "Ativo"
    elif view.pass_open:
        current, status = "Aberta", "Disponível"
    else:
        current, status = "Nenhuma Crônica aberta", "Indisponível"
    rows = []
    pass_price = view.prices.get(CHRONICLE_PASS)
    if view.enabled and pass_price and view.pass_open and not view.pass_active:
        rows.append([_button("📜 Comprar", f"pay:t:{CHRONICLE_PASS}")])
    rows.append(_BACK)
    return Screen(
        _html(
            "📜 <b>Passe da Crônica</b>",
            "<i>O Passe libera a camada Premium da Trilha da Crônica e permite receber os "
            "benefícios Premium dos Marcos da Crônica.</i>",
            f"📜 <b>Crônica Atual</b> · {_m(current)}",
            f"✨ <b>Status</b> · {_m(status)}",
            None
            if view.pass_open
            else "<i>Uma nova Crônica aparecerá aqui quando uma temporada estiver "
            "disponível.</i>",
        ),
        _IMAGE,
        _keyboard(rows),
        "HTML",
    )

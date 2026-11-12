"""Operator CLI for paid orders (GDD §35.2). Never exposed to players.

Usage:
    python -m asterion.payments_cli list [--status paid] [--account <telegram_id>]
    python -m asterion.payments_cli show <pedido>
    python -m asterion.payments_cli reconcile
    python -m asterion.payments_cli attach <order_nsu> <transaction_nsu> <slug> [--amount N]
    python -m asterion.payments_cli refund <pedido> --note "motivo" [--our-error]
    python -m asterion.payments_cli reverse <pedido> --note "chargeback"

<pedido> is the order id, its order_nsu or the provider's transaction_nsu.

The refund itself is made by the author in the InfinitePay app or web account
(the API has no refund). ``refund`` only records it and revokes what the order
granted. Within 7 days of payment it needs no reason; later it needs
``--our-error``. ``reverse`` records a chargeback/reversal.

``reconcile`` asks the provider again about every unpaid order that already has
a notice; after a backup restore, ``attach`` rebuilds a lost notice with the ids
shown in the InfinitePay app, then confirms it. Nothing is delivered twice.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.payments import (
    OrderView,
    PaymentError,
    PaymentService,
    build_provider,
    payment_config,
)
from asterion.config import Settings, get_settings
from asterion.domain.chronicle import TIMEZONE
from asterion.domain.payments import ORDER_STATUSES, REFUNDED, REVERSED, format_brl
from asterion.infrastructure.infinitepay import PaymentProviderError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.payments_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="listar pedidos")
    listing.add_argument("--status", choices=ORDER_STATUSES)
    listing.add_argument("--account", type=int)
    listing.add_argument("--limit", type=int, default=50)
    show = sub.add_parser("show", help="mostrar um pedido e seu histórico")
    show.add_argument("order")
    sub.add_parser("reconcile", help="consultar de novo os pedidos não pagos com aviso")
    attach = sub.add_parser("attach", help="registrar um aviso perdido e confirmar")
    attach.add_argument("order_nsu")
    attach.add_argument("transaction_nsu")
    attach.add_argument("invoice_slug")
    attach.add_argument("--amount", type=int, help="valor em centavos (pedido perdido)")
    for name, text in (("refund", "registrar reembolso"), ("reverse", "registrar estorno")):
        refund = sub.add_parser(name, help=text)
        refund.add_argument("order")
        refund.add_argument("--note", required=True)
        if name == "refund":
            refund.add_argument("--our-error", action="store_true")
    return parser


def _line(order: OrderView) -> str:
    when = order.created_at.astimezone(TIMEZONE).strftime("%Y-%m-%d %H:%M")
    extra = f" · erro: {order.grant_error}" if order.grant_error else ""
    return (
        f"{when} · {order.status:<8} · {order.product_name} · "
        f"{format_brl(order.amount_cents)} · {order.order_nsu}{extra}"
    )


async def run(
    args: argparse.Namespace, sessions: async_sessionmaker[AsyncSession], settings: Settings
) -> int:
    payments = PaymentService(
        sessions, settings.server_id, payment_config(settings), build_provider(settings)
    )
    operator = os.environ.get("USER") or os.environ.get("USERNAME") or "operator"
    if args.command == "list":
        orders = await payments.list_orders(
            status=args.status, account_id=args.account, limit=args.limit
        )
        for order in orders:
            print(_line(order))
        if not orders:
            print("Nenhum pedido.")
        return 0
    if args.command == "show":
        order = await payments.find(args.order)
        if order is None:
            print("Pedido não encontrado.", file=sys.stderr)
            return 1
        print(_line(order))
        for event in await payments.events(order.id):
            when = event.created_at.astimezone(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            note = f" · {event.note}" if event.note else ""
            print(f"  {when} · {event.kind} · {event.actor} · {event.data}{note}")
        return 0
    if args.command == "reconcile":
        results = await payments.reconcile(operator=operator)
        for order, outcome in results:
            print(f"{_line(order)} -> {outcome}")
        if not results:
            print("Nada para reconciliar.")
        return 0
    if args.command == "attach":
        queued = await payments.attach_notice(
            args.order_nsu,
            args.transaction_nsu,
            args.invoice_slug,
            amount_cents=args.amount,
            operator=operator,
        )
        print(f"Aviso: {queued}.")
        order = await payments.find(args.order_nsu)
        if order is not None and queued == "queued":
            print(f"Confirmação: {await payments.confirm(order.id, actor=f'operator:{operator}')}.")
        return 0
    result = await payments.refund(
        args.order,
        status=REFUNDED if args.command == "refund" else REVERSED,
        note=args.note,
        operator=operator,
        our_error=getattr(args, "our_error", False),
    )
    print(_line(result.order))
    print(f"Revogado: {result.revoked}")
    print(f"Reembolsos/estornos desta conta: {result.refunds_of_account}")
    if result.flagged:
        print("⚠️  Conta marcada para análise por reembolsos repetidos.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    async def execute() -> int:
        from asterion.infrastructure.db.session import SessionFactory

        return await run(args, SessionFactory, get_settings())

    try:
        return asyncio.run(execute())
    except (PaymentError, PaymentProviderError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

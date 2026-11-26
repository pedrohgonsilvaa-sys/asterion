"""Telegram screens for Benefícios and Comunidade (GDD v1.6.0 §32, §2.1)."""

from __future__ import annotations

import re
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.engagement import DailyGiftResult, DailyGiftView, Granted
from asterion.application.recruitment import RecruitmentView
from asterion.bot.creation_ui import Screen
from asterion.domain.engagement import (
    DAILY_GIFT,
    RECRUIT_MILESTONES,
    RECRUITER_MIN_LEVEL,
    Bundle,
)

_IMAGE = "menu"
_REF = re.compile(r"\nRef: (bn:[\w-]+)$")

CODE_PROMPT = "Envie o Código de Asterion.\n\nRef: bn:code"
RECRUIT_PROMPT = "Envie o código de Chamado de quem convidou você.\n\nRef: bn:recruit"

_ERRORS = {
    "no_character": "Crie um personagem para usar Benefícios.",
    "recruit_code_invalid": "Este código de Chamado não existe.",
    "recruit_self": "Você não pode usar o próprio código.",
    "recruit_already_linked": "Sua conta já tem um recrutador.",
    "recruit_window_closed": (
        "O prazo acabou: o vínculo vale até 72h após a criação e antes do Nv.10."
    ),
    "recruiter_ineligible": f"Quem convida precisa estar no Nv.{RECRUITER_MIN_LEVEL} ou acima.",
    "nothing_to_claim": "Ainda não há recompensa para resgatar.",
    "promo_invalid": "Código inválido.",
    "promo_expired": "Este Código expirou.",
    "promo_exhausted": "Este Código atingiu o limite de resgates.",
    "promo_already_redeemed": "Você já resgatou este Código.",
    "promo_rate_limited": "Muitas tentativas. Aguarde um pouco e tente de novo.",
}


def error_text(code: str) -> str:
    return _ERRORS.get(code, "Esta ação não está mais disponível.")


def parse_ref(text: str | None) -> str | None:
    match = _REF.search(text or "")
    return None if match is None else match.group(1)


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


_BACK = [_button("↩️ Retornar", "bn:root")]


def _html(*parts: str | None) -> str:
    return "\n\n".join(part for part in parts if part)


def _m(text: str) -> str:
    return f"<code>{escape(text)}</code>"


def _n(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def render_benefits(*, shop_open: bool = False) -> Screen:
    """Benefícios (decisão do autor 2026-11-26 §32.1)."""
    codes = [_button("🎟️ Códigos", "bn:code")]
    if shop_open:
        codes.append(_button("🔱 Patrono", "pay:root"))
    return Screen(
        _html(
            "🎁 <b>Benefícios</b>",
            "<i>Recompensas, recrutamento e códigos de Asterion ficam reunidos aqui.</i>",
        ),
        _IMAGE,
        _keyboard(
            [
                [_button("🎁 Dádiva", "bn:gift"), _button("📣 Chamado", "bn:call")],
                codes,
                [_button("↩️ Retornar", "menu:back")],
            ]
        ),
        "HTML",
    )


def _bundle_values(bundle: Bundle) -> list[str]:
    """Emoji da recompensa antes do valor configurado (§32.2)."""
    parts = []
    if bundle.crowns:
        parts.append(f"🪙 {_m(f'{_n(bundle.crowns)} Coroas')}")
    if bundle.basics:
        parts.append(f"🧱 {_m(f'{bundle.basics} Materiais Básicos')}")
    if bundle.fragments:
        label = "Fragmentos" if bundle.fragments > 1 else "Fragmento"
        parts.append(f"✨ {_m(f'{bundle.fragments} {label}')}")
    return parts


def granted_lines(granted: Granted) -> list[str]:
    """Texto puro (telas fora desta etapa, como a Trilha da Crônica)."""
    lines = []
    if granted.crowns:
        lines.append(f"🪙 {granted.crowns} Coroas")
    lines.extend(f"📦 {item.quantity}× {item.name} · vinculado" for item in granted.items)
    return lines


def granted_html(granted: Granted) -> list[str]:
    """Recompensas em monoespaçado, com o emoji antes do valor (§32.5)."""
    lines = []
    if granted.crowns:
        lines.append(f"🪙 {_m(f'{_n(granted.crowns)} Coroas')}")
    lines.extend(f"📦 {_m(f'{item.quantity} {item.name}')}" for item in granted.items)
    return lines


def render_gift(view: DailyGiftView, result: DailyGiftResult | None = None) -> Screen:
    """Dádiva Diária (§32.2): ✅ dia resgatado, ❌ dia ainda não resgatado."""
    lines = []
    for index, bundle in enumerate(DAILY_GIFT, start=1):
        done = index < view.next_day or (view.claimed_today and index == view.next_day)
        mark = "✅" if done else "❌"
        lines.append(f"{mark} <b>Dia {index}</b> · " + " · ".join(_bundle_values(bundle)))
    rows = []
    if not view.claimed_today:
        rows.append([_button("🎁 Resgatar", "bn:gift:claim")])
    rows.append(_BACK)
    return Screen(
        _html("🎁 <b>Dádiva Diária</b>", "\n".join(lines)), _IMAGE, _keyboard(rows), "HTML"
    )


def render_call(view: RecruitmentView, link: str | None, notice: str | None = None) -> Screen:
    """Chamado de Asterion (§32.3)."""
    identity = [f"🎟️ <b>Código</b> · {_m(view.code)}"]
    if link:
        identity.append(f"🔗 <b>Link</b> · {_m(link)}")
    milestones = "\n".join(
        f"🪙 <b>Nv. {milestone}</b> · {_m(f'{crowns} Coroas por marco')}"
        for milestone, crowns in RECRUIT_MILESTONES.items()
    )
    claim = (
        f"🪙 <b>Disponível</b> · {_m(f'{_n(view.claimable_crowns)} Coroas')}"
        if view.claimable_crowns
        else None
    )
    rows = []
    if view.claimable_crowns:
        rows.append([_button("🪙 Resgatar", "bn:call:claim")])
    if view.can_link:
        rows.append([_button("🎟️ Código", "bn:call:enter")])
    rows.append(_BACK)
    return Screen(
        _html(
            escape(notice) if notice else None,
            "📣 <b>Chamado de Asterion</b>",
            "<i>O Chamado permite convidar novos aventureiros para Asterion e acompanhar o "
            "progresso dos recrutados.</i>",
            "\n".join(identity),
            f"👥 <b>Recrutas</b> · {_m(str(view.recruits))}",
            milestones,
            claim,
        ),
        _IMAGE,
        _keyboard(rows),
        "HTML",
    )


def render_code_prompt(error: str | None = None) -> Screen:
    """Código de Asterion (§32.4): o pedido usa a própria tela."""
    return Screen(
        _html(
            "🎟️ <b>Código de Asterion</b>",
            "<i>Resgate códigos promocionais para receber recompensas especiais de "
            "Asterion.</i>",
            escape(error) if error else None,
            "✏️ <b>Digite o código para resgatar.</b>",
        ),
        _IMAGE,
        _keyboard([_BACK]),
        "HTML",
    )


def render_recruit_prompt(error: str | None = None) -> Screen:
    return Screen(
        _html(
            "📣 <b>Chamado de Asterion</b>",
            escape(error) if error else None,
            "✏️ <b>Digite o código de quem convidou você.</b>",
        ),
        _IMAGE,
        _keyboard([[_button("↩️ Retornar", "bn:call")]]),
        "HTML",
    )


def render_promo_result(code: str, granted: Granted) -> Screen:
    """Código resgatado (§32.5)."""
    lines = granted_html(granted)
    return Screen(
        _html(
            "🎟️ <b>Código de Asterion</b>",
            "<i>Código resgatado com sucesso.</i>",
            "\n".join(["🎁 <b>Recompensas:</b>", *lines]) if lines else None,
        ),
        _IMAGE,
        _keyboard([_BACK]),
        "HTML",
    )


def render_promo_invalid() -> Screen:
    """Código inválido (§32.6)."""
    return Screen(
        _html(
            "🎟️ <b>Código</b>",
            "❌ <b>Código Inválido</b>",
            "<i>O código informado não existe, expirou ou já foi utilizado.</i>",
        ),
        _IMAGE,
        _keyboard([[_button("🎟️ Tentar Novamente", "bn:code")], _BACK]),
        "HTML",
    )


def community_invite_text() -> str:
    return (
        "🌘 A Comunidade Oficial de Asterion reúne Eventos, Mercado, Guildas, Relatos "
        "e novidades. Ela fica sempre no Menu Principal."
    )


def community_keyboard(url: str | None, *, with_menu: bool = True) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if url:
        rows.append([InlineKeyboardButton(text="Abrir Comunidade", url=url)])
    if with_menu:
        rows.append([_button("← Menu", "menu:back")])
    return _keyboard(rows)


def render_community(url: str | None) -> Screen:
    text = community_invite_text() if url else "🌘 O link da Comunidade ainda não foi configurado."
    return Screen(text, _IMAGE, community_keyboard(url))

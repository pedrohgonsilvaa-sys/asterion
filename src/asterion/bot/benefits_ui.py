"""Telegram screens for Benefícios and Comunidade (GDD v1.6.0 §32, §2.1)."""

from __future__ import annotations

import re

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


_BACK = [_button("← Benefícios", "bn:root")]


def render_benefits() -> Screen:
    return Screen(
        "🎁 Benefícios\n\nRecompensas, recrutamento e códigos de Asterion.",
        _IMAGE,
        _keyboard(
            [
                [_button("Dádiva Diária", "bn:gift")],
                [_button("Trilha da Crônica", "cr:trail")],
                [_button("Chamado de Asterion", "bn:call")],
                [_button("Códigos de Asterion", "bn:code")],
                [_button("Apoiar Asterion", "pay:root")],
                [_button("← Menu", "menu:back")],
            ]
        ),
    )


def _bundle_text(bundle: Bundle) -> str:
    parts = []
    if bundle.crowns:
        parts.append(f"{bundle.crowns} Coroas")
    if bundle.basics:
        parts.append(f"{bundle.basics} Materiais Básicos")
    if bundle.fragments:
        parts.append(f"{bundle.fragments} Fragmentos" if bundle.fragments > 1 else "1 Fragmento")
    return " + ".join(parts)


def granted_lines(granted: Granted) -> list[str]:
    lines = []
    if granted.crowns:
        lines.append(f"🪙 {granted.crowns} Coroas")
    lines.extend(f"📦 {item.quantity}× {item.name} · vinculado" for item in granted.items)
    return lines


def render_gift(view: DailyGiftView, result: DailyGiftResult | None = None) -> Screen:
    lines = ["🎁 Dádiva Diária", ""]
    if result is not None and result.granted is not None:
        lines.extend([f"Dia {result.day} resgatado:", *granted_lines(result.granted), ""])
    for index, bundle in enumerate(DAILY_GIFT, start=1):
        marker = "👉" if index == view.next_day and not view.claimed_today else "▫️"
        lines.append(f"{marker} Dia {index} · {_bundle_text(bundle)}")
    lines.extend(["", "Perder um dia apenas adia o próximo resgate. Nova Dádiva às 06:00."])
    rows = []
    if not view.claimed_today:
        rows.append([_button("Resgatar", "bn:gift:claim")])
    rows.append(_BACK)
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def render_call(view: RecruitmentView, link: str | None, notice: str | None = None) -> Screen:
    lines = ["📯 Chamado de Asterion", ""]
    if notice:
        lines.extend([notice, ""])
    lines.append(f"Seu código: {view.code}")
    if link:
        lines.append(f"Seu link: {link}")
    if not view.recruiter_eligible:
        lines.append(f"Seu código passa a valer no Nv.{RECRUITER_MIN_LEVEL}.")
    lines.extend(["", f"Recrutas: {view.recruits}"])
    for milestone, crowns in RECRUIT_MILESTONES.items():
        lines.append(
            f"Nv.{milestone} · {view.recruits_at[milestone]} recruta(s) · {crowns} Coroas por marco"
        )
    if view.prestige:
        lines.extend(["", "Prestígio: " + ", ".join(view.prestige)])
    if view.claimable_crowns:
        lines.extend(["", f"Disponível para resgate: {view.claimable_crowns} Coroas"])
    rows = []
    if view.claimable_crowns:
        rows.append([_button("Resgatar", "bn:call:claim")])
    if view.can_link:
        rows.append([_button("Inserir código de quem me convidou", "bn:call:enter")])
    rows.append(_BACK)
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def render_promo_result(code: str, granted: Granted) -> Screen:
    return Screen(
        "\n".join([f"🎟️ Código {code} resgatado", "", *granted_lines(granted)]),
        _IMAGE,
        _keyboard([_BACK]),
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

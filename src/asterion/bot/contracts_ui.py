"""Telas de Telegram dos Contratos Regionais (Documento B §22 a §27).

Botoes carregam ids empacotados e a versao vista; nunca autoridade. O backend
revalida tudo (ContractService). Nenhuma tela passa de MAX_BUTTONS botoes.
"""

from __future__ import annotations

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.contracts import (
    ACCEPTED,
    COMPLETED,
    BoardView,
    ContractView,
)
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import pack
from asterion.domain.contracts_catalog import TYPE_LABEL
from asterion.domain.contracts_config import MAX_BUTTONS
from asterion.domain.professions import MATERIAL_NAMES

IMAGE_KEY = "adventure"
BACK = "world:adventure"

ERROR_MESSAGES = {
    "disabled": "Os Contratos ainda não estão disponíveis.",
    "character_missing": "Crie um personagem antes de abrir o Quadro.",
    "market_locked": "O Quadro abre quando o Prólogo terminar.",
    "not_found": "Este Contrato não existe mais.",
    "stale": "Esta tela está desatualizada. Abra o Quadro de novo.",
    "state_changed": "Este Contrato mudou de estado. Abra o Quadro de novo.",
    "expired": "Este Contrato expirou.",
    "not_eligible": "Você ainda não pode usar os Contratos desta região.",
    "limit": "Você já tem o máximo de Contratos. Resgate ou abandone um.",
    "already_held": "Você já tem este Contrato.",
    "wrong_place": "Você não está no lugar do objetivo.",
    "no_action": "Este Contrato não tem ação direta. Cumpra o objetivo na região.",
    "no_region": "Não foi possível saber sua região.",
}
ERROR_FALLBACK = "Não foi possível concluir essa ação."


def error_text(code: str) -> str:
    return ERROR_MESSAGES.get(code, ERROR_FALLBACK)


def _button(text: str, data: str) -> InlineKeyboardButton:
    assert len(data.encode("utf-8")) <= 64, data
    return InlineKeyboardButton(text=text, callback_data=data)


def _screen(text: str, rows: list[list[InlineKeyboardButton]]) -> Screen:
    if sum(len(row) for row in rows) > MAX_BUTTONS:
        raise ValueError("contract screen exceeds the button limit")
    return Screen(text, IMAGE_KEY, InlineKeyboardMarkup(inline_keyboard=rows), "HTML")


def _ref(view: ContractView) -> str:
    return f"{pack(view.instance_id)}:{view.version}"


def number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def reward_text(view: ContractView) -> str:
    material = MATERIAL_NAMES.get(view.material_id, view.material_id)
    return (
        f"{number(view.xp)} XP\n{number(view.crowns)} Coroas\n{view.materials}× {escape(material)}"
    )


def progress_text(view: ContractView) -> str:
    kind = view.definition.contract_type
    base = f"{view.progress}/{view.target}"
    if kind == "CACA":
        return f"{base} vitória(s) em Caçada na região."
    if kind == "COLETA":
        material = MATERIAL_NAMES.get(view.definition.material_id or "", "Material")
        return f"{base} · {escape(material)}"
    if kind == "ENTREGA":
        return f"{base} · Entregar em {escape(view.place or '')}."
    return f"{base} · Examinar em {escape(view.place or '')}."


def render_board(board: BoardView, notice: str | None = None) -> Screen:
    head = "📜 <b>QUADRO DE CONTRATOS</b>\n\n"
    if notice:
        head += f"{escape(notice)}\n\n"
    if not board.eligible:
        text = (
            head + f"{escape(board.region_name)}: o Quadro desta região ainda está fechado.\n"
            "Avance na Missão Principal e no nível da região."
        )
        return _screen(text, [[_button("Voltar", BACK)]])
    if board.offers:
        text = head + "Escolha um contrato disponível para ver seus detalhes."
    else:
        text = head + "Nenhum contrato disponível agora. O Quadro renova a cada 24 h."
    rows = [[_button(offer.definition.name, f"ctr:d:{_ref(offer)}")] for offer in board.offers]
    rows.append([_button("Meus Contratos", "ctr:m")])
    rows.append([_button("Voltar", BACK)])
    return _screen(text, rows)


def render_detail(view: ContractView) -> Screen:
    definition = view.definition
    text = (
        "📜 <b>CONTRATO</b>\n\n"
        f"<b>{escape(definition.name)}</b>\n\n"
        f"Tipo: {TYPE_LABEL[definition.contract_type]}\n"
        f"Região: {escape(_region_name(definition.region))}\n\n"
        f"{escape(definition.description)}\n\n"
        f"Requisitos:\n{escape(view.requirement)}\n\n"
        f"Recompensa:\n{reward_text(view)}"
    )
    return _screen(
        text, [[_button("ACEITAR", f"ctr:a:{_ref(view)}")], [_button("VOLTAR", "ctr:b")]]
    )


def render_mine(views: tuple[ContractView, ...]) -> Screen:
    if not views:
        text = "📜 <b>MEUS CONTRATOS</b>\n\nVocê não tem contratos aceitos."
    else:
        text = "📜 <b>MEUS CONTRATOS</b>\n\nEscolha um contrato para ver o andamento."
    rows = [
        [_button(("✅ " if v.state == COMPLETED else "") + v.definition.name, f"ctr:o:{_ref(v)}")]
        for v in views
    ]
    rows.append([_button("Quadro", "ctr:b")])
    return _screen(text, rows)


def render_contract(view: ContractView, notice: str | None = None) -> Screen:
    if view.state == COMPLETED:
        text = (
            "✅ <b>CONTRATO CONCLUÍDO</b>\n\n"
            f"<b>{escape(view.definition.name)}</b>\n\nO objetivo foi concluído.\n\n"
            f"Recompensa disponível:\n{reward_text(view)}"
        )
        return _screen(
            text,
            [[_button("RESGATAR", f"ctr:r:{_ref(view)}")], [_button("QUADRO", "ctr:b")]],
        )
    state = "Aceito" if view.state == ACCEPTED else "Em andamento"
    text = (
        "📜 <b>MEU CONTRATO</b>\n\n"
        f"<b>{escape(view.definition.name)}</b>\n\n"
        f"Estado: {state}\n\nProgresso:\n{progress_text(view)}"
    )
    if notice:
        text += f"\n\n{escape(notice)}"
    return _screen(
        text,
        [
            [_button("CONTINUAR", f"ctr:g:{_ref(view)}")],
            [_button("ABANDONAR", f"ctr:x:{_ref(view)}")],
            [_button("QUADRO", "ctr:b")],
        ],
    )


def render_abandon(view: ContractView) -> Screen:
    text = (
        "⚠️ <b>ABANDONAR CONTRATO?</b>\n\n"
        "O progresso deste Contrato será encerrado.\nA recompensa não será recebida."
    )
    return _screen(
        text,
        [
            [_button("CONFIRMAR ABANDONO", f"ctr:z:{_ref(view)}")],
            [_button("MANTER CONTRATO", f"ctr:o:{_ref(view)}")],
        ],
    )


def _region_name(code: str) -> str:
    from asterion.domain.contracts_config import REGION_NAMES

    return REGION_NAMES[code]

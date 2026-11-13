"""Presentation for settings, help, and player account workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.account import (
    AccountView,
    NotificationPreferenceView,
    RenameInputView,
)
from asterion.bot.creation_ui import Screen

HELP_TOPICS = (
    (
        "start",
        "Primeiros Passos",
        "Use o Menu para abrir Aventura, Personagem, Códice e Configurações. "
        "O jogo salva seu progresso no servidor.",
    ),
    (
        "combat",
        "Combate",
        "Durante um combate, escolha uma ação disponível no painel. /menu e /start "
        "retomam a atividade ativa sem encerrá-la.",
    ),
    (
        "adventure",
        "Aventura",
        "Mapa e Missões mostram caminhos e objetivos conhecidos. Caçadas, Desbravar e "
        "Masmorras seguem as regras de cada atividade.",
    ),
    (
        "character",
        "Personagem",
        "Atributos mostram os valores atuais. Perfil guarda uma História opcional. "
        "Caminhos, Talentos, Artes e Doutrinas configuram seu personagem.",
    ),
    (
        "equipment",
        "Equipamentos",
        "Inventário e Equipamentos mostram itens adquiridos. Aprimoramentos, Runas e "
        "Encantamentos alteram a configuração conforme as regras do jogo.",
    ),
    (
        "progression",
        "Artes, Talentos e Caminho",
        "Artes equipadas podem ser usadas em combate. Talentos e Caminho têm requisitos "
        "próprios e podem ser configurados em locais permitidos.",
    ),
    (
        "hunt",
        "Caçada e Ronda",
        "Caçadas são encontros manuais. Rondas resolvem um lote de encontros conforme "
        "a preparação e as regras da atividade.",
    ),
    (
        "explore",
        "Desbravar",
        "A exploração revela informações e locais conforme as escolhas disponíveis. "
        "Descobertas podem aparecer no Mapa e no Códice.",
    ),
    (
        "dungeon",
        "Masmorras e Grupo",
        "Masmorras conhecidas podem ser iniciadas nas dificuldades liberadas. A run "
        "mantém seu estado ao reconectar.",
    ),
    (
        "craft",
        "Ofícios e Criação",
        "Ofícios liberam receitas. A Criação mostra custos e resultado antes da "
        "confirmação, e valida materiais e Coroas no commit.",
    ),
    (
        "runes",
        "Runas e Encantamentos",
        "Runas e Encantamentos modificam Equipamentos. Consulte o detalhe do item "
        "para compatibilidade, custos e ações disponíveis.",
    ),
    (
        "knowledge",
        "Bestiário e Códice",
        "Essas telas guardam apenas criaturas observadas e conhecimentos adquiridos "
        "durante a jornada.",
    ),
    (
        "cosmetics",
        "Doutrinas e Cosméticos",
        "Cosméticos mudam a apresentação. Doutrinas salvam referências à configuração "
        "de combate e respeitam os bloqueios de atividade.",
    ),
    (
        "account",
        "Conta e Configurações",
        "Ajuste notificações, renomeie o personagem ou solicite a exclusão pendente, "
        "que pode ser cancelada dentro do prazo.",
    ),
)


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _base36(value: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    out = ""
    while value:
        value, digit = divmod(value, 36)
        out = chars[digit] + out
    return out


def render_settings() -> Screen:
    return Screen(
        "🎛️ Configurações\n\nEscolha uma opção.",
        "menu",
        _keyboard(
            [
                [_button("🔔 Notificações", "settings:notifications")],
                [_button("🛟 Ajuda", "help:root")],
                [_button("👤 Conta", "account:root")],
                [_button("← Menu", "menu:back")],
            ]
        ),
    )


def render_notifications(view: NotificationPreferenceView) -> Screen:
    state = "Ativas" if view.enabled else "Silenciadas"
    next_state = "Desativar" if view.enabled else "Ativar"
    return Screen(
        f"🔔 Notificações\n\nEssenciais · {state}\n\n"
        "Mensagens necessárias para as ações que você iniciou continuam sendo exibidas.",
        "menu",
        _keyboard(
            [
                [
                    _button(
                        next_state,
                        f"settings:n:essentials:{_base36(view.revision)}:{int(view.enabled)}",
                    )
                ],
                [_button("← Configurações", "settings:root")],
            ]
        ),
    )


def render_help_root() -> Screen:
    rows = []
    lines = ["🛟 Ajuda", "", "Escolha um assunto.", ""]
    for key, title, _body in HELP_TOPICS:
        lines.append(title)
        rows.append([_button(title, f"help:{key}")])
    rows.extend([[_button("← Configurações", "settings:root")]])
    return Screen("\n".join(lines), "menu", _keyboard(rows))


def render_help_topic(key: str) -> Screen:
    topic = next((item for item in HELP_TOPICS if item[0] == key), None)
    if topic is None:
        return render_help_root()
    _key, title, body = topic
    return Screen(
        f"🛟 {title}\n\n{body}",
        "menu",
        _keyboard(
            [
                [_button("← Ajuda", "help:root")],
                [_button("Configurações", "settings:root"), _button("Menu", "menu:back")],
            ]
        ),
    )


def render_account(view: AccountView) -> Screen:
    if view.deletion_pending:
        return Screen(
            f"👤 Conta\n\n{escape(view.name)} · Nv. {view.level}\n\n"
            f"⏳ Exclusão Pendente · {_remaining(view.deletion_due_at)}",
            "character",
            _keyboard(
                [
                    [_button("Acompanhar Exclusão", "account:d:pending")],
                    [_button("← Configurações", "settings:root")],
                ]
            ),
            parse_mode="HTML",
        )
    return Screen(
        f"👤 Conta\n\n{escape(view.name)} · Nv. {view.level}",
        "character",
        _keyboard(
            [
                [_button("✏️ Renomear Personagem · Identidade", "account:rename")],
                [_button("🗑️ Excluir Personagem · Exclusão", "account:delete")],
                [_button("← Configurações", "settings:root")],
            ]
        ),
        parse_mode="HTML",
    )


def render_rename_start(view: AccountView) -> Screen:
    if view.rename_available_at is not None:
        return Screen(
            "✏️ Renomear Personagem\n\n"
            f"🏷️ Nome Atual · {escape(view.name)}\n\n"
            f"🔒 Renome disponível em · {_date(view.rename_available_at)}",
            "character",
            _keyboard([[_button("← Conta", "account:root")]]),
            parse_mode="HTML",
        )
    return Screen(
        "✏️ Renomear Personagem\n\n"
        f"🏷️ Nome Atual · {escape(view.name)}\n\n"
        "✅ Renome · Disponível\n\nEnvie no chat o novo nome do personagem.",
        "character",
        _keyboard(
            [
                [_button("Enviar novo nome", "account:rename:input")],
                [_button("← Conta", "account:root")],
            ]
        ),
        parse_mode="HTML",
    )


def render_rename_preview(view: RenameInputView) -> Screen:
    if view.status != "preview" or not view.new_name:
        message = {
            "format": "O nome deve seguir as mesmas regras usadas na criação do personagem.",
            "same": "Escolha um nome diferente do atual.",
            "unavailable": "Este nome está em uso ou reservado.",
        }.get(view.error or "", "O nome não está disponível.")
        return Screen(
            f"✏️ Renomear Personagem\n\n{message}",
            "character",
            _keyboard(
                [
                    [_button("Alterar Nome", "account:rename:input")],
                    [_button("← Conta", "account:root")],
                ]
            ),
        )
    return Screen(
        "✏️ Renomear Personagem\n\n"
        f"🏷️ Nome Atual · {escape(view.current_name)}\n"
        f"✨ Novo Nome · {escape(view.new_name)}\n\n"
        "🪙 Custo · 2.500 Coroas\n⏳ Recarga · 30 dias",
        "character",
        _keyboard(
            [
                [_button("Confirmar Renome", f"account:r:confirm:{_base36(view.revision)}")],
                [_button("Alterar Nome", "account:rename:input")],
                [_button("← Conta", "account:root")],
            ]
        ),
        parse_mode="HTML",
    )


def render_delete_confirmation(view: AccountView) -> Screen:
    if view.deletion_preview_id is None:
        return render_expired_action()
    return Screen(
        "🗑️ Excluir Personagem\n\n"
        f"{escape(view.name)} · Nv. {view.level}\n\n"
        "⚠️ Tem certeza? A exclusão é imediata e definitiva.\n"
        "Todo o progresso deste personagem será apagado e não há recuperação.\n"
        "Depois você poderá criar um novo personagem.\n\n"
        "Para confirmar, você vai digitar o nome do personagem.",
        "character",
        _keyboard(
            [
                [_button("Digitar o nome para excluir", "account:d:input")],
                [_button("← Conta", "account:root")],
            ]
        ),
        parse_mode="HTML",
    )


def render_deletion_pending(view: AccountView) -> Screen:
    due = view.deletion_due_at
    remaining = _remaining(due) if due else "—"
    return Screen(
        "⏳ Exclusão Pendente\n\n"
        f"{escape(view.name)}\n\n"
        f"⏳ Tempo Restante · {remaining}\n"
        "🔄 Recuperação · Disponível",
        "character",
        _keyboard(
            [
                [
                    _button(
                        "Cancelar Exclusão",
                        f"account:d:cancel:{_base36(view.deletion_revision or 0)}",
                    )
                ],
                [_button("Excluir agora (digitar o nome)", "account:d:input")],
                [_button("← Conta", "account:root")],
            ]
        ),
        parse_mode="HTML",
    )


def render_expired_action() -> Screen:
    return Screen(
        "⏳ Ação Expirada\n\nEsta ação não está mais disponível. Atualize a tela para continuar.",
        "menu",
        _keyboard([[_button("Atualizar", "account:root"), _button("← Menu", "menu:back")]]),
    )


def _date(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC")


def _remaining(value: datetime) -> str:
    seconds = max(0, int((value - datetime.now(UTC)).total_seconds()))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    return f"{days}d {hours}h {minutes}min"

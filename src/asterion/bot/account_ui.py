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

# Ajuda/Wiki (decisão do autor 2026-11-26 §35.3): um assunto por botão, na ordem do molde.
# Os textos vêm das explicações já existentes, separadas por assunto.
HELP_TOPICS = (
    ("start", "📖", "Tutorial",
     "Use o Menu para abrir Aventura, Personagem, Códice e Configurações. "
     "O jogo salva seu progresso no servidor."),
    ("combat", "⚔️", "Combate",
     "Durante um combate, escolha uma ação disponível no painel. /menu e /start "
     "retomam a atividade ativa sem encerrá-la."),
    ("explore", "⛰️", "Desbravar",
     "A exploração revela informações e locais conforme as escolhas disponíveis. "
     "Descobertas podem aparecer no Mapa e no Códice."),
    ("character", "👤", "Personagem",
     "Atributos mostram os valores atuais. Perfil guarda uma História opcional."),
    ("equipment", "🛡️", "Equipamentos",
     "Inventário e Equipamentos mostram itens adquiridos. Aprimoramentos alteram a "
     "configuração conforme as regras do jogo."),
    ("arts", "✨", "Artes", "Artes equipadas podem ser usadas em combate."),
    ("talents", "🌟", "Talentos",
     "Talentos têm requisitos próprios e podem ser configurados em locais permitidos."),
    ("path", "🧭", "Caminho",
     "O Caminho tem requisitos próprios e pode ser configurado em locais permitidos."),
    ("hunt", "🐺", "Caçada", "Caçadas são encontros manuais."),
    ("round", "🔄", "Ronda",
     "Rondas resolvem um lote de encontros conforme a preparação e as regras da atividade."),
    ("dungeon", "🗝️", "Masmorras",
     "Masmorras conhecidas podem ser iniciadas nas dificuldades liberadas. A run "
     "mantém seu estado ao reconectar."),
    ("group", "👥", "Grupo", "O Grupo reúne até 4 personagens."),
    ("professions", "⚒️", "Ofícios", "Ofícios liberam receitas."),
    ("craft", "🛠️", "Criação",
     "A Criação mostra custos e resultado antes da confirmação, e valida materiais e "
     "Coroas no commit."),
    ("runes", "🔮", "Runas",
     "Runas modificam Equipamentos. Consulte o detalhe do item para compatibilidade, "
     "custos e ações disponíveis."),
    ("enchantments", "✨", "Encantamentos",
     "Encantamentos modificam Equipamentos. Consulte o detalhe do item para "
     "compatibilidade, custos e ações disponíveis."),
    ("bestiary", "🐾", "Bestiário",
     "O Bestiário guarda apenas criaturas observadas durante a jornada."),
    ("codex", "📚", "Códice",
     "O Códice guarda apenas conhecimentos adquiridos durante a jornada."),
    ("doctrines", "⚜️", "Doutrinas",
     "Doutrinas salvam referências à configuração de combate e respeitam os bloqueios de "
     "atividade."),
    ("cosmetics", "🎨", "Cosméticos", "Cosméticos mudam a apresentação."),
    ("account", "👤", "Conta", "Na Conta você renomeia ou apaga o personagem."),
    ("settings", "⚙️", "Configurações", "Nas Configurações você ajusta as notificações."),
)  # fmt: skip


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


def _html(*parts: str | None) -> str:
    return "\n\n".join(part for part in parts if part)


def _back(data: str, label: str = "↩️ Retornar") -> list[InlineKeyboardButton]:
    return [_button(label, data)]


def render_settings() -> Screen:
    """Configurações (decisão do autor 2026-11-26 §35.1)."""
    return Screen(
        _html(
            "⚙️ <b>Configurações</b>",
            "<i>Aqui você gerencia as preferências da sua conta, as notificações e as opções "
            "de ajuda de Asterion.</i>",
        ),
        "menu",
        _keyboard(
            [
                [_button("🔔 Notificações", "settings:notifications"), _button("🆘 Ajuda", "help:root")],  # noqa: E501
                [_button("👤 Conta", "account:root")],
                _back("menu:back"),
            ]
        ),
        parse_mode="HTML",
    )


def render_notifications(view: NotificationPreferenceView) -> Screen:
    """Notificações (§35.2)."""
    state = "Ativas" if view.enabled else "Silenciadas"
    toggle = "🔕 Desativar" if view.enabled else "🔔 Ativar"
    return Screen(
        _html(
            "🔔 <b>Notificações</b>",
            "<i>Controle as mensagens automáticas que Asterion envia sobre ações iniciadas "
            "por você.</i>",
            f"🔔 <b>Essenciais</b> · <code>{state}</code>",
            "<i>Mensagens necessárias para concluir ou acompanhar ações iniciadas por você "
            "continuam sendo exibidas.</i>",
        ),
        "menu",
        _keyboard(
            [
                [
                    _button(
                        toggle,
                        f"settings:n:essentials:{_base36(view.revision)}:{int(view.enabled)}",
                    )
                ],
                _back("settings:root"),
            ]
        ),
        parse_mode="HTML",
    )


def render_help_root() -> Screen:
    """Ajuda/Wiki (§35.3): cada assunto em um botão, duas colunas."""
    buttons = [_button(f"{emoji} {title}", f"help:{key}") for key, emoji, title, _ in HELP_TOPICS]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    return Screen(
        _html(
            "🆘 <b>Ajuda</b>",
            "<i>Consulte os sistemas de Asterion e encontre explicações rápidas sobre cada "
            "parte da sua jornada.</i>",
        ),
        "menu",
        _keyboard([*rows, _back("settings:root")]),
        parse_mode="HTML",
    )


def render_help_topic(key: str) -> Screen:
    topic = next((item for item in HELP_TOPICS if item[0] == key), None)
    if topic is None:
        return render_help_root()
    _key, emoji, title, body = topic
    return Screen(
        _html(f"{emoji} <b>{escape(title)}</b>", f"<i>{escape(body)}</i>"),
        "menu",
        _keyboard([_back("help:root")]),
        parse_mode="HTML",
    )


def _status_block(identity, stats) -> str | None:
    """Classe + nome + nível, Título dinâmico e HP/Vigor/XP com barras (§35.4)."""
    from asterion.bot.character_ui import resource_bars
    from asterion.bot.ui_format import DEFAULT_TITLE
    from asterion.bot.world_ui import CLASS_EMOJI

    if identity is None:
        return None
    head = (
        f"{CLASS_EMOJI.get(identity.character_class, '👤')} <b>{escape(identity.name)}</b> · "
        f"<code>Nv. {identity.level}</code>\n"
        f"🎖️ <code>{escape(identity.selected_title or DEFAULT_TITLE)}</code>"
    )
    if stats is None:
        return head
    bars = resource_bars(
        stats.hp, stats.max_hp, stats.vigor, stats.max_vigor, stats.xp, stats.xp_required
    )
    return f"{head}\n\n{bars}"


def render_account(view: AccountView, identity=None, stats=None) -> Screen:
    """Conta (§35.4): imagem do personagem, status e Renomear/Apagar lado a lado."""
    if view.deletion_pending:
        return Screen(
            _html(
                "👤 <b>Conta</b>",
                f"{escape(view.name)} · <code>Nv. {view.level}</code>",
                f"⏳ <b>Exclusão Pendente</b> · <code>{_remaining(view.deletion_due_at)}</code>",
            ),
            "character",
            _keyboard([[_button("⏳ Exclusão", "account:d:pending")], _back("settings:root")]),
            parse_mode="HTML",
        )
    status = _status_block(identity, stats) or (
        f"<b>{escape(view.name)}</b> · <code>Nv. {view.level}</code>"
    )
    return Screen(
        _html(
            "👤 <b>Conta</b>",
            "<i>Aqui você gerencia a identidade da sua conta e acompanha os principais "
            "status do seu personagem.</i>",
            status,
        ),
        "character",
        _keyboard(
            [
                [_button("✏️ Renomear", "account:rename"), _button("🗑️ Apagar", "account:delete")],
                _back("settings:root"),
            ]
        ),
        parse_mode="HTML",
    )


def render_rename_prompt(error: str | None = None) -> Screen:
    """Renomear (§35.5): o pedido usa a própria tela, sem botão de Identidade."""
    return Screen(
        _html(
            "✏️ <b>Renomear</b>",
            "<i>Escolha um novo nome para o seu personagem.</i>",
            escape(error) if error else None,
            "✏️ <b>Envie o novo nome do personagem.</b>",
        ),
        "character",
        _keyboard([_back("account:root")]),
        parse_mode="HTML",
    )


def render_rename_start(view: AccountView) -> Screen:
    """Renome em recarga: mostra quando volta a ficar disponível."""
    return Screen(
        _html(
            "✏️ <b>Renomear</b>",
            f"🏷️ <b>Nome Atual</b> · <code>{escape(view.name)}</code>",
            "🔒 <b>Renome disponível em</b> · "
            f"<code>{_date(view.rename_available_at) if view.rename_available_at else '—'}</code>",
        ),
        "character",
        _keyboard([_back("account:root")]),
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
                    [_button("✏️ Alterar", "account:rename")],
                    [_button("↩️ Retornar", "account:root")],
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
                [_button("✏️ Alterar", "account:rename")],
                [_button("↩️ Retornar", "account:root")],
            ]
        ),
        parse_mode="HTML",
    )


def render_delete_confirmation(view: AccountView, identity=None, stats=None) -> Screen:
    """Apagar Personagem (§35.6). O aviso ⚠️ é texto normal, sem negrito."""
    if view.deletion_preview_id is None:
        return render_expired_action()
    status = _status_block(identity, stats) or (
        f"<b>{escape(view.name)}</b> · <code>Nv. {view.level}</code>"
    )
    return Screen(
        _html(
            "🗑️ <b>Apagar Personagem</b>",
            status,
            "<i>Apagar o personagem é uma ação definitiva. Todo o progresso, equipamentos e "
            "dados vinculados a este personagem serão removidos.</i>",
            "⚠️ Essa ação não pode ser desfeita.",
        ),
        "character",
        _keyboard([[_button("🗑️ Apagar", "account:d:now")], _back("account:root", "↩️ Cancelar")]),
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
                [_button("↩️ Retornar", "account:root")],
            ]
        ),
        parse_mode="HTML",
    )


def render_deleted(name: str) -> Screen:
    return Screen(
        f"🗑️ <b>Apagar Personagem</b>\n\n<i>{escape(name)} foi apagado. Use /start para "
        "criar um novo personagem.</i>",
        "menu",
        None,
        parse_mode="HTML",
    )


def render_expired_action() -> Screen:
    return Screen(
        "⏳ Ação Expirada\n\nEsta ação não está mais disponível. Atualize a tela para continuar.",
        "menu",
        _keyboard([[_button("Atualizar", "account:root"), _button("↩️ Retornar", "menu:back")]]),
    )


def _date(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC")


def _remaining(value: datetime) -> str:
    seconds = max(0, int((value - datetime.now(UTC)).total_seconds()))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    return f"{days}d {hours}h {minutes}min"

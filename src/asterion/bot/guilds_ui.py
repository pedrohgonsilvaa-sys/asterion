"""Telegram presentation for Guilds (GDD v1.7.1 §30; decisões do autor 2026-11-26 §9–§16).

Every button carries ids (never a Name or TAG) packed as 22-character urlsafe
base64 so the callback stays under Telegram's 64-byte limit. The server
revalidates each id on click. Telas seguem os moldes fechados pelo autor: título em
negrito, explicações em itálico, valores em monoespaçado e ``↩️ Retornar``.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from datetime import datetime
from html import escape
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.guilds import (
    CharacterCandidateView,
    GuildApplicationView,
    GuildInviteView,
    GuildPage,
    GuildView,
    PublicGuildView,
    TreasuryEntryView,
)
from asterion.bot.creation_ui import Screen
from asterion.bot.ui_format import BACK_LABEL, blocks, mono, narrative, number
from asterion.bot.world_ui import CLASS_EMOJI, CLASS_LABEL
from asterion.domain.guilds import (
    GUILD_SYMBOLS,
    LODGING_CAPACITY,
    MAX_PROJECT_LEVEL,
    GuildRole,
    ProjectKind,
    Recruitment,
    project_build_time,
    project_cost,
)

IMAGE = "links"
CANCEL_LABEL = "↩️ Cancelar"

GUILD_TEXT = (
    "Uma Guilda reúne aventureiros sob um mesmo nome e cria um espaço para enfrentar "
    "Asterion em conjunto."
)
NO_GUILD_TEXT = (
    "Encontre uma Guilda para caminhar com outros aventureiros, procure uma Guilda aberta "
    "ou funde a sua própria."
)

# Obras: nome completo (listagem e tela da Obra), emoji e rótulo curto do botão.
OBRAS = (
    (ProjectKind.LODGING, "🏠", "Alojamentos", "Alojamentos"),
    (ProjectKind.FORGE, "⚒️", "Forja", "Forja"),
    (ProjectKind.VEIL_ALTAR, "🔥", "Altar do Véu", "Altar"),
    (ProjectKind.TREASURY, "🪙", "Tesouraria", "Tesouraria"),
    (ProjectKind.VEIL_ARCHIVE, "📚", "Arquivo do Véu", "Arquivo"),
    (ProjectKind.HUNTERS_POST, "🏹", "Posto dos Caçadores", "Caçadores"),
    (ProjectKind.WAR_HALL, "⚔️", "Salão de Guerra", "Guerra"),
)
OBRA_LABELS = {kind: label for kind, _emoji, label, _short in OBRAS}
OBRA_EMOJI = {kind: emoji for kind, emoji, _label, _short in OBRAS}

ROLE_LABELS = {
    GuildRole.LEADER: "Líder",
    GuildRole.OFFICER: "Oficial",
    GuildRole.MEMBER: "Membro",
}

TREASURY_KINDS = {
    "deposit": "Depósito",
    "project_funding": "Obra",
    "rename": "Renome",
    "forfeit": "Encerramento",
    "oath": "Juramento",
    "expedition": "Expedição",
}

# One Portuguese message per GuildError code (the two name codes come from the
# domain's normalisers and are raised through GuildError as well).
GUILD_ERROR_MESSAGES = {
    "character_missing": "Personagem indisponível.",
    "invalid_name": "O Nome da Guilda precisa ter de 3 a 16 letras, sem espaços ou números.",
    "invalid_tag": "A TAG precisa ter exatamente 3 letras.",
    "invalid_symbol": "Escolha um dos símbolos da lista.",
    "name_or_tag_taken": "Já existe uma Guilda com esse Nome ou essa TAG.",
    "already_in_guild": "Este personagem já está em uma Guilda.",
    "not_in_guild": "Você não está em uma Guilda.",
    "switch_cooldown": "Você saiu de uma Guilda há pouco. Aguarde a recarga de 12 horas.",
    "no_permission": "Você não tem permissão para fazer isso.",
    "guild_missing": "Essa Guilda não existe mais.",
    "guild_full": "A Guilda está cheia.",
    "recruitment_closed": "Essa Guilda está com o recrutamento fechado.",
    "character_not_found": "Não encontrei esse personagem neste servidor.",
    "cannot_invite_self": "Você não pode convidar o próprio personagem.",
    "invite_refused": "Esse personagem não pode receber o convite.",
    "cannot_target_self": "Você não pode fazer isso com o próprio personagem.",
    "target_in_guild": "Esse personagem já está em uma Guilda.",
    "target_not_member": "Esse personagem não é membro da sua Guilda.",
    "invite_unusable": "Esse convite expirou, foi cancelado ou já foi respondido.",
    "application_pending": "Você já tem uma inscrição pendente nessa Guilda.",
    "application_missing": "Essa inscrição não existe mais.",
    "application_closed": "Essa inscrição já foi encerrada.",
    "application_rate_limited": (
        "Você enviou inscrições demais em pouco tempo. Aguarde um pouco para tentar de novo."
    ),
    "too_many_pending": "Você já tem 3 inscrições pendentes. Cancele uma para enviar outra.",
    "leader_must_transfer": "O Líder não pode sair. Transfira a liderança antes.",
    "guild_battle_roster_locked": (
        "Esse personagem está no roster travado de uma Batalha de Guildas. "
        "Espere a Batalha terminar."
    ),
    "wrong_server": "Isso pertence a outro servidor.",
    "invalid_amount": "Informe uma quantia inteira de Coroas maior que zero.",
    "not_enough_crowns": "Você não tem Coroas suficientes.",
    "treasury_insufficient": "A Tesouraria não tem Coroas suficientes.",
    "guild_dissolving": "A Guilda está em dissolução. Tesouraria e Obras estão congeladas.",
    "project_active": "Essa Obra já está em Financiamento ou Construção.",
    "too_many_projects": "A Guilda já tem 2 Obras em andamento.",
    "project_max_level": "Essa Obra já está no nível máximo.",
    "project_missing": "Essa Obra não existe mais.",
    "project_not_funding": "Essa Obra não está mais recebendo contribuições.",
    "rename_unchanged": "O novo Nome e a nova TAG são iguais aos atuais.",
    "rename_cooldown": "O Renome está em recarga. Ele pode ser usado uma vez a cada 30 dias.",
    "name_or_tag_reserved": "Esse Nome ou TAG foi usado há pouco por outra Guilda e está reservado.",  # noqa: E501
    "dissolve_has_members": "A Guilda não pode ser dissolvida enquanto houver outros membros.",
    "dissolve_commitment": (
        "A Guilda tem Batalha de Guildas, Juramento ou Expedição em andamento. "
        "Conclua o compromisso antes de dissolver."
    ),
}
GUILD_ERROR_FALLBACK = "Não foi possível concluir essa ação."


def error_text(code: str) -> str:
    return GUILD_ERROR_MESSAGES.get(code, GUILD_ERROR_FALLBACK)


def pack(value: UUID) -> str:
    return base64.urlsafe_b64encode(value.bytes).decode("ascii").rstrip("=")


def unpack(token: str) -> UUID:
    if len(token) != 22:
        raise ValueError("invalid id token")
    return UUID(bytes=base64.urlsafe_b64decode(token + "=="))


def _button(text: str, data: str) -> InlineKeyboardButton:
    assert len(data.encode("utf-8")) <= 64, data
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(rows: Sequence[Sequence[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(row) for row in rows if row])


def _back(data: str, label: str = BACK_LABEL) -> list[InlineKeyboardButton]:
    return [_button(label, data)]


def _screen(text: str, rows: Sequence[Sequence[InlineKeyboardButton]]) -> Screen:
    return Screen(text, IMAGE, _keyboard(rows), "HTML")


def _pairs(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    return [buttons[index : index + 2] for index in range(0, len(buttons), 2)]


def _crowns(value: int) -> str:
    return number(value)


def _b(text: str) -> str:
    return f"<b>{escape(text)}</b>"


def _field(emoji: str, label: str, value: str) -> str:
    return f"{emoji} {_b(label)} · {mono(value)}"


def guild_title(symbol: str, tag: str, name: str) -> str:
    """``🥀 **[RSN] Rosas Negras**`` (TAG sempre antes do nome)."""
    return f"{symbol} {_b(f'[{tag}] {name}')}"


def _members(count: int, capacity: int) -> str:
    return _field("👥", "Membros", f"{count}/{capacity}")


def _leader(name: str | None) -> str | None:
    return _field("👑", "Líder", name) if name else None


def _recruitment_label(recruitment: Recruitment) -> str:
    return "Aberto" if recruitment is Recruitment.OPEN else "Fechado"


def character_card(name: str, level: int, character_class: str) -> str:
    """``👤 **Cael** · `Nv. 10` `` e, abaixo, ``🛡️ **Sentinela**`` (emoji só na Classe)."""
    emoji = CLASS_EMOJI.get(character_class, "👤")
    label = CLASS_LABEL.get(character_class, character_class.title())
    return f"👤 {_b(name)} · {mono(f'Nv. {level}')}\n{emoji} {_b(label)}"


def _class_button(name: str, character_class: str, data: str) -> InlineKeyboardButton:
    return _button(f"{CLASS_EMOJI.get(character_class, '👤')} {name}", data)


def _guild_button(symbol: str, name: str, data: str) -> InlineKeyboardButton:
    return _button(f"{symbol} {name}", data)


def _nav(prev_data: str | None, next_data: str | None) -> list[InlineKeyboardButton]:
    row: list[InlineKeyboardButton] = []
    if prev_data:
        row.append(_button("◀️ Anterior", prev_data))
    if next_data:
        row.append(_button("▶️ Próxima", next_data))
    return row


def _can_manage(guild: GuildView) -> bool:
    return guild.viewer_role in (GuildRole.LEADER, GuildRole.OFFICER)


# ------------------------------------------------------------------ §9.1 / §9.2


def render_guild_menu(guild: GuildView | None, **_ignored) -> Screen:
    if guild is None:
        return _screen(
            blocks("🏰 <b>Guilda</b>", narrative(NO_GUILD_TEXT), narrative(GUILD_TEXT)),
            [
                [_button("⚒️ Fundar", "guild:found"), _button("🔎 Procurar", "guild:search")],
                [_button("🏰 Guildas", "guild:browse:0"), _button("📝 Inscrições", "guild:myapps")],
                [_button("✉️ Convites", "guild:inbox")],
                _back("menu:back"),
            ],
        )
    gid = pack(guild.guild_id)
    info = "\n".join(
        (
            guild_title(guild.symbol, guild.tag, guild.name),
            _members(guild.member_count, guild.capacity),
            _field("🚪", "Recrutamento", _recruitment_label(guild.recruitment)),
            _field("🪙", "Tesouraria", f"{_crowns(guild.treasury_crowns)} Coroas"),
        )
    )
    return _screen(
        blocks("🏰 <b>Guilda</b>", info, narrative(GUILD_TEXT)),
        [
            [_button("👥 Gerenciar", f"guild:mgmt:{gid}"), _button("💰 Tesouraria", f"guild:works:{gid}")],  # noqa: E501
            [_button("🏗️ Obras", f"guild:obras:{gid}"), _button("⚔️ Batalha", "gb:hub")],
            [_button("⚜️ Juramento", "oath:hub"), _button("🚩 Expedição", "exp:hub")],
            _back("menu:back"),
        ],
    )


# ---------------------------------------------------------------------- §9.3


def render_manage(guild: GuildView) -> Screen:
    gid = pack(guild.guild_id)
    leader = guild.viewer_role is GuildRole.LEADER
    buttons: list[InlineKeyboardButton] = []
    if _can_manage(guild):
        buttons += [
            _button("📨 Convidar", f"guild:invite:{gid}"),
            _button("📢 Recrutar", f"guild:recruit:{gid}"),
            _button("📝 Inscrições", f"guild:recv:{gid}"),
        ]
    buttons.append(_button("👥 Membros", f"guild:mem:{gid}"))
    if leader:
        buttons += [
            _button("✏️ Renomear", f"guild:ren:{gid}"),
            _button("🗑️ Dissolver", f"guild:diss:{gid}"),
        ]
    return _screen(
        blocks(
            "⚙️ <b>Gerenciar</b>",
            narrative("Administre os membros, o recrutamento e as configurações da Guilda."),
        ),
        [*_pairs(buttons), _back("guild:root")],
    )


def render_members(guild: GuildView) -> Screen:
    """Membros da Guilda e as ações que o cargo do jogador permite."""
    gid = pack(guild.guild_id)
    leader = guild.viewer_role is GuildRole.LEADER
    cards = [
        f"{character_card(m.name, m.level, m.character_class)} · {mono(ROLE_LABELS[m.role])}"
        for m in guild.members
    ]
    rows: list[list[InlineKeyboardButton]] = []
    for member in guild.members:
        if member.character_id == guild.viewer_character_id:
            continue
        cid = pack(member.character_id)
        label = member.name[:12]
        if leader and member.role is GuildRole.MEMBER:
            rows.append([_button(f"⬆️ {label}", f"guild:pro:{gid}:{cid}")])
        if leader and member.role is GuildRole.OFFICER:
            rows.append([_button(f"⬇️ {label}", f"guild:dem:{gid}:{cid}")])
        if leader:
            rows.append([_button(f"👑 {label}", f"guild:lead:{gid}:{cid}")])
        can_kick = leader or (
            guild.viewer_role is GuildRole.OFFICER and member.role is GuildRole.MEMBER
        )
        if can_kick:
            rows.append([_button(f"🚪 {label}", f"guild:kick:{gid}:{cid}")])
    if not leader:
        rows.append([_button("🚪 Sair", f"guild:leave:{gid}")])
    rows.append(_back(f"guild:mgmt:{gid}"))
    return _screen(blocks("👥 <b>Membros</b>", "\n\n".join(cards)), rows)


# Compatibilidade com chamadores antigos.
render_manage_members = render_members


# ---------------------------------------------------------------------- §9.4


def render_invite_prompt(guild: GuildView, *, error: str | None = None) -> Screen:
    return _screen(
        blocks(
            "📨 <b>Convidar</b>",
            narrative("Digite o nome do personagem que deseja convidar."),
            escape(error) if error else None,
            "✏️ <b>Digite o nome do personagem.</b>",
        ),
        [_back(f"guild:mgmt:{pack(guild.guild_id)}")],
    )


def render_invite_candidates(
    guild: GuildView, candidates: Sequence[CharacterCandidateView]
) -> Screen:
    gid = pack(guild.guild_id)
    if len(candidates) == 1:
        only = candidates[0]
        return _screen(
            blocks(
                "📨 <b>Convidar</b>",
                character_card(only.name, only.level, only.character_class),
            ),
            [
                [_button("📨 Convidar", f"guild:invc:{gid}:{pack(only.character_id)}")],
                _back(f"guild:mgmt:{gid}"),
            ],
        )
    cards = [character_card(c.name, c.level, c.character_class) for c in candidates]
    rows = [
        [_class_button(c.name, c.character_class, f"guild:invp:{gid}:{pack(c.character_id)}")]
        for c in candidates
    ]
    return _screen(
        blocks(
            "👤 <b>Personagem</b>",
            narrative("Foram encontrados vários personagens com esse nome."),
            "\n\n".join(cards),
        ),
        [*rows, _back(f"guild:mgmt:{gid}")],
    )


# ---------------------------------------------------------------------- §9.5


def render_recruit(guild: GuildView) -> Screen:
    gid = pack(guild.guild_id)
    open_ = guild.recruitment is Recruitment.OPEN
    toggle = (
        _button("🔴 Fechar", f"guild:recr:c:{gid}")
        if open_
        else _button("🟢 Abrir", f"guild:recr:o:{gid}")
    )
    return _screen(
        blocks(
            "📢 <b>Recrutar</b>",
            narrative(
                "Defina se sua Guilda estará disponível para receber solicitações de entrada."
            ),
            _field("🚪", "Recrutamento", _recruitment_label(guild.recruitment)),
        ),
        [[toggle], _back(f"guild:mgmt:{gid}")],
    )


# ---------------------------------------------------------------------- §9.6


def render_received_applications(
    guild_id: UUID, applications: Sequence[GuildApplicationView]
) -> Screen:
    gid = pack(guild_id)
    cards = [
        character_card(a.character_name, a.character_level, a.character_class)
        for a in applications
    ]
    rows = [
        [
            _class_button(
                a.character_name, a.character_class, f"guild:appv:{gid}:{pack(a.application_id)}"
            )
        ]
        for a in applications
    ]
    return _screen(
        blocks(
            "📝 <b>Inscrições</b>",
            narrative("Veja os aventureiros que solicitaram entrada na Guilda."),
            "\n\n".join(cards) if cards else None,
        ),
        [*rows, _back(f"guild:mgmt:{gid}")],
    )


def render_application(guild_id: UUID, application: GuildApplicationView) -> Screen:
    gid = pack(guild_id)
    token = pack(application.application_id)
    return _screen(
        blocks(
            "📝 <b>Inscrição</b>",
            character_card(
                application.character_name,
                application.character_level,
                application.character_class,
            ),
            narrative("Este aventureiro deseja entrar para a Guilda."),
        ),
        [
            [
                _button("✅ Aceitar", f"guild:app:a:{gid}:{token}"),
                _button("❌ Recusar", f"guild:app:r:{gid}:{token}"),
            ],
            _back(f"guild:recv:{gid}"),
        ],
    )


# ---------------------------------------------------------------------- §9.7


def render_treasury(guild: GuildView) -> Screen:
    gid = pack(guild.guild_id)
    return _screen(
        blocks(
            "💰 <b>Tesouraria</b>",
            _field("🪙", "Saldo", f"{_crowns(guild.treasury_crowns)} Coroas"),
            narrative(
                "Os recursos da Guilda são compartilhados entre seus membros. "
                "Depósitos e contribuições são definitivos."
            ),
        ),
        [
            [_button("🪙 Depositar", f"guild:dep:{gid}"), _button("📜 Histórico", f"guild:hist:{gid}")],  # noqa: E501
            _back("guild:root"),
        ],
    )


# Compatibilidade: a antiga tela "Tesouraria e Obras" virou a Tesouraria.
render_works = render_treasury

DEPOSIT_PRESETS = (1, 10, 100)


def render_deposit(guild: GuildView) -> Screen:
    gid = pack(guild.guild_id)
    presets = [
        _button(f"🪙 {amount} {'Coroa' if amount == 1 else 'Coroas'}", f"guild:depv:{gid}:{amount}")
        for amount in DEPOSIT_PRESETS
    ]
    return _screen(
        blocks(
            "🪙 <b>Depositar</b>",
            _field("🪙", "Saldo", f"{_crowns(guild.viewer_crowns)} Coroas"),
            narrative("Escolha quanto deseja contribuir para a Tesouraria."),
        ),
        [
            presets[0:2],
            [presets[2], _button("✏️ Quantia", f"guild:depq:{gid}")],
            _back(f"guild:works:{gid}"),
        ],
    )


def render_deposit_prompt(guild: GuildView, *, error: str | None = None) -> Screen:
    return _screen(
        blocks(
            "🪙 <b>Depositar</b>",
            _field("🪙", "Saldo", f"{_crowns(guild.viewer_crowns)} Coroas"),
            escape(error) if error else None,
            "✏️ <b>Digite a quantia de Coroas.</b>",
        ),
        [_back(f"guild:dep:{pack(guild.guild_id)}")],
    )


def render_treasury_history(guild: GuildView, entries: Sequence[TreasuryEntryView]) -> Screen:
    lines = []
    for entry in entries:
        sign = "+" if entry.amount > 0 else "−"
        who = f" · {escape(entry.character_name)}" if entry.character_name else ""
        lines.append(
            f"{_b(entry.created_at.strftime('%d/%m/%Y, %H:%M'))}\n"
            f"🪙 {escape(TREASURY_KINDS.get(entry.kind, entry.kind))}{who} · "
            f"{mono(f'{sign}{_crowns(abs(entry.amount))} Coroas')}"
        )
    return _screen(
        blocks(
            "📜 <b>Histórico</b>",
            "\n\n".join(lines) if lines else mono("❌ Vazio."),
        ),
        [_back(f"guild:works:{pack(guild.guild_id)}")],
    )


# ---------------------------------------------------------------------- §9.8


def _levels(guild: GuildView) -> dict[ProjectKind, int]:
    return dict(guild.obra_levels)


def render_obras(guild: GuildView) -> Screen:
    gid = pack(guild.guild_id)
    levels = _levels(guild)
    lines = [
        f"{emoji} {_b(label)} · {mono(f'Nv. {levels.get(kind, 0)}')}"
        for kind, emoji, label, _short in OBRAS
    ]
    buttons = [
        _button(f"{emoji} {short}", f"guild:obra:{gid}:{kind.value}")
        for kind, emoji, _label, short in OBRAS
    ]
    return _screen(
        blocks(
            "🏗️ <b>Obras</b>",
            narrative("Construa melhorias para ampliar as possibilidades da Guilda."),
            "\n".join(lines),
        ),
        [*_pairs(buttons), _back("guild:root")],
    )


def _hours(level: int) -> str:
    return f"{int(project_build_time(level).total_seconds() // 3600)}h"


def render_obra(guild: GuildView, kind: ProjectKind) -> Screen:
    gid = pack(guild.guild_id)
    level = _levels(guild).get(kind, 0)
    emoji = OBRA_EMOJI[kind]
    label = OBRA_LABELS[kind]
    project = next((p for p in guild.active_projects if p.kind is kind), None)
    parts: list[str | None] = [f"{emoji} <b>{escape(label)}</b>"]
    current = [_field(emoji, "Nv. Atual", str(level))]
    if kind is ProjectKind.LODGING:
        current.append(_field("👥", "Vagas", str(LODGING_CAPACITY[level])))
    parts.append("\n".join(current))
    rows: list[list[InlineKeyboardButton]] = []
    if level >= MAX_PROJECT_LEVEL:
        parts.append(narrative("Esta Obra já alcançou o nível máximo."))
    else:
        upcoming = level + 1
        nxt = [_field("⬆️", "Próximo Nv.", str(upcoming))]
        if kind is ProjectKind.LODGING:
            extra = LODGING_CAPACITY[upcoming] - LODGING_CAPACITY[level]
            nxt.append(_field("👥", "Novas Vagas", f"+{extra}"))
        parts.append("\n".join(nxt))
        cost = project.cost if project is not None else project_cost(upcoming)
        parts.append(
            "\n".join(
                (
                    _field("🪙", "Custo", f"{_crowns(cost)} Coroas"),
                    _field("⏱️", "Tempo", _hours(upcoming)),
                )
            )
        )
        if project is not None and project.status == "building":
            done = project.completes_at.strftime("%d/%m às %H:%M") if project.completes_at else ""
            parts.append(narrative(f"A Obra está em construção até {done}."))
        else:
            if project is not None:
                parts.append(_field("🪙", "Arrecadado", f"{_crowns(project.funded)} Coroas"))
            parts.append(narrative("Os recursos necessários ainda não foram arrecadados."))
            rows.append([_button("🪙 Financiar", f"guild:fin:{gid}:{kind.value}")])
    rows.append(_back(f"guild:obras:{gid}", "↩️ Obras"))
    return _screen(blocks(*parts), rows)


def finances_from_treasury(guild: GuildView) -> bool:
    """O Líder financia com a Tesouraria; os demais membros, com a própria carteira."""
    return guild.viewer_role is GuildRole.LEADER


def render_finance_prompt(
    guild: GuildView, kind: ProjectKind, *, error: str | None = None
) -> Screen:
    balance = guild.treasury_crowns if finances_from_treasury(guild) else guild.viewer_crowns
    label = "Tesouraria" if finances_from_treasury(guild) else "Saldo"
    return _screen(
        blocks(
            f"{OBRA_EMOJI[kind]} <b>{escape(OBRA_LABELS[kind])}</b>",
            _field("🪙", label, f"{_crowns(balance)} Coroas"),
            escape(error) if error else None,
            "✏️ <b>Digite a quantia de Coroas.</b>",
        ),
        [_back(f"guild:obra:{pack(guild.guild_id)}:{kind.value}", "↩️ Obras")],
    )


def parse_crowns(text: str) -> int | None:
    """Accept `20000` or `20.000`; anything else is not an amount."""
    digits = text.strip().replace(".", "")
    if not digits.isdigit() or len(digits) > 12:
        return None
    return int(digits)


# --------------------------------------------------------------------- §9.11


def render_rename_name(guild: GuildView, *, error: str | None = None) -> Screen:
    return _screen(
        blocks(
            "✏️ <b>Renomear Guilda</b>",
            _field("🏰", "Nome Atual", guild.name),
            narrative(
                "Escolha um novo nome para sua Guilda. O nome será usado para identificar "
                "sua Guilda em Asterion."
            ),
            escape(error) if error else None,
            "✏️ Envie o novo nome da Guilda.",
        ),
        [_back(f"guild:mgmt:{pack(guild.guild_id)}")],
    )


def render_rename_tag(guild: GuildView, new_name: str, *, error: str | None = None) -> Screen:
    return _screen(
        blocks(
            "🏷️ <b>Renomear Guilda</b>",
            "\n".join((_field("🏰", "Nome", new_name), _field("🏷️", "TAG Atual", guild.tag))),
            narrative("Escolha uma nova TAG para identificar sua Guilda de forma abreviada."),
            escape(error) if error else None,
            "🏷️ Envie a nova TAG da Guilda.",
        ),
        [_back(f"guild:mgmt:{pack(guild.guild_id)}")],
    )


def render_rename_confirm(guild: GuildView, new_name: str, new_tag: str) -> Screen:
    gid = pack(guild.guild_id)
    return _screen(
        blocks(
            "✏️ <b>Renomear Guilda</b>",
            "\n".join((_field("🏰", "Nome", new_name), _field("🏷️", "TAG", new_tag))),
            narrative("Confira os novos dados da Guilda antes de confirmar a alteração."),
        ),
        [
            [_button("✅ Confirmar", f"guild:renok:{gid}"), _button(CANCEL_LABEL, f"guild:mgmt:{gid}")],  # noqa: E501
        ],
    )


# --------------------------------------------------------------------- §9.12


def render_dissolve(guild: GuildView) -> Screen:
    gid = pack(guild.guild_id)
    header = f"{guild_title(guild.symbol, guild.tag, guild.name)} · " + _members(
        guild.member_count, guild.capacity
    )
    if guild.member_count > 1:
        return _screen(
            blocks(
                "🗑️ <b>Dissolver Guilda</b>",
                header,
                narrative(
                    "Uma Guilda só pode ser dissolvida quando o Líder for o único membro. "
                    "Remova os demais membros antes de continuar."
                ),
                "⚠️ A Guilda não pode ser dissolvida enquanto houver outros membros.",
            ),
            [[_button("👥 Gerenciar", f"guild:mgmt:{gid}")], _back(f"guild:mgmt:{gid}")],
        )
    return _screen(
        blocks(
            "🗑️ <b>Dissolver Guilda</b>",
            header,
            narrative(
                "Ao dissolver a Guilda, ela será encerrada imediatamente e seus recursos e "
                "Obras serão perdidos."
            ),
            "⚠️ Essa ação é definitiva.",
        ),
        [[_button("🗑️ Dissolver", f"guild:dissok:{gid}")], _back(f"guild:mgmt:{gid}", CANCEL_LABEL)],
    )


# ---------------------------------------------------------------------- §10


def render_browse(page: GuildPage, *, first: bool = True, page_index: int = 0) -> Screen:
    blocks_ = [
        "\n".join(
            line
            for line in (
                guild_title(item.symbol, item.tag, item.name),
                _leader(item.leader_name),
                _members(item.member_count, item.capacity),
            )
            if line
        )
        for item in page.items
    ]
    rows = [
        [_guild_button(item.symbol, item.name, f"guild:page:{pack(item.guild_id)}")]
        for item in page.items
    ]
    nav = _nav(
        f"guild:browse:{page_index - 1}" if page_index > 0 else None,
        f"guild:browse:{page_index + 1}" if page.next_after is not None else None,
    )
    return _screen(
        blocks(
            "🏰 <b>Guildas</b>",
            narrative(
                "Encontre Guildas com inscrições abertas e escolha uma para conhecer melhor."
            ),
            "\n\n".join(blocks_) if blocks_ else None,
        ),
        [*rows, nav, _back("guild:root")],
    )


# ---------------------------------------------------------------------- §11


def render_public_page(
    page: PublicGuildView | None,
    *,
    can_apply: bool = True,
    pending_application: UUID | None = None,
    back: str = "guild:root",
) -> Screen:
    if page is None:
        return _screen(
            blocks("🏰 <b>Guilda</b>", narrative("Essa Guilda não existe mais.")),
            [_back(back)],
        )
    info = "\n".join(
        line
        for line in (_leader(page.leader_name), _members(page.member_count, page.capacity))
        if line
    )
    rows: list[list[InlineKeyboardButton]] = []
    if pending_application is not None:
        rows.append([_button("❌ Cancelar", f"guild:cancelapp:{pack(pending_application)}")])
    elif can_apply and page.accepts_applications:
        rows.append([_button("📨 Solicitar Entrada", f"guild:apply:{pack(page.guild_id)}")])
    rows.append(_back(back))
    return _screen(blocks(guild_title(page.symbol, page.tag, page.name), info), rows)


# ---------------------------------------------------------------------- §12


def render_search_prompt(*, error: str | None = None) -> Screen:
    return _screen(
        blocks(
            "🔎 <b>Procurar Guilda</b>",
            narrative("Encontre uma Guilda pelo nome ou pela TAG."),
            narrative("Você pode pesquisar usando o nome completo da Guilda ou apenas a TAG."),
            escape(error) if error else None,
            "✏️ <b>Digite o nome ou a TAG da Guilda.</b>",
        ),
        [_back("guild:root")],
    )


def render_search_results(query: str, results: Sequence[PublicGuildView]) -> Screen:
    if not results:
        return render_search_prompt(error=f"❌ Nenhuma Guilda encontrada para “{query}”.")
    if len(results) == 1:
        return render_public_page(results[0])
    rows = [
        [_guild_button(item.symbol, item.name, f"guild:page:{pack(item.guild_id)}")]
        for item in results
    ]
    return _screen(
        blocks(
            "🔎 <b>Procurar Guilda</b>",
            "\n\n".join(
                f"{guild_title(i.symbol, i.tag, i.name)}\n{_members(i.member_count, i.capacity)}"
                for i in results
            ),
        ),
        [*rows, _back("guild:root")],
    )


# ---------------------------------------------------------------------- §13


def render_inbox(invites: Sequence[GuildInviteView]) -> Screen:
    if not invites:
        return _screen(
            blocks(
                "✉️ <b>Convites</b>",
                narrative("Você não possui convites de Guilda pendentes no momento."),
            ),
            [_back("guild:root")],
        )
    if len(invites) == 1:
        return render_invite(invites[0], back="guild:root")
    rows = [
        [_guild_button(i.guild_symbol, i.guild_name, f"guild:invv:{pack(i.invite_id)}")]
        for i in invites
    ]
    return _screen(
        blocks(
            "✉️ <b>Convites</b>",
            narrative("Você recebeu convites de outras Guildas."),
            narrative("Escolha uma Guilda para visualizar o convite."),
        ),
        [*rows, _back("guild:root")],
    )


def render_invite(invite: GuildInviteView, *, back: str = "guild:inbox") -> Screen:
    token = pack(invite.invite_id)
    info = "\n".join(
        line
        for line in (_leader(invite.leader_name), _members(invite.member_count, invite.capacity))
        if line
    )
    return _screen(
        blocks(
            "✉️ <b>Convite para Guilda</b>",
            narrative("Você recebeu um convite para se juntar à seguinte Guilda:"),
            guild_title(invite.guild_symbol, invite.guild_tag, invite.guild_name),
            info,
            narrative("Faça parte da Guilda e atravesse Asterion ao lado de outros aventureiros."),
        ),
        [
            [_button("✅ Aceitar", f"guild:inv:a:{token}"), _button("❌ Recusar", f"guild:inv:d:{token}")],  # noqa: E501
            _back(back),
        ],
    )


# ---------------------------------------------------------------------- §14

APPLICATIONS_PAGE = 5


def render_my_applications(
    applications: Sequence[GuildApplicationView], *, page_index: int = 0
) -> Screen:
    pending = [a for a in applications if a.status == "pending"]
    start = page_index * APPLICATIONS_PAGE
    shown = pending[start : start + APPLICATIONS_PAGE]
    cards = [
        f"{guild_title(a.guild_symbol, a.guild_tag, a.guild_name)}\n"
        f"{_members(a.member_count, a.capacity)}"
        for a in shown
    ]
    rows = [
        [_guild_button(a.guild_symbol, a.guild_name, f"guild:mapp:{pack(a.application_id)}")]
        for a in shown
    ]
    nav = _nav(
        f"guild:myapps:{page_index - 1}" if page_index > 0 else None,
        f"guild:myapps:{page_index + 1}" if start + APPLICATIONS_PAGE < len(pending) else None,
    )
    return _screen(
        blocks(
            "📝 <b>Inscrições</b>",
            narrative(
                "Aqui ficam as Guildas para as quais você enviou uma solicitação de entrada."
            ),
            "\n\n".join(cards) if cards else None,
        ),
        [*rows, nav, _back("guild:root")],
    )


# ------------------------------------------------------------------ §15 / §16


def render_found_name(*, error: str | None = None) -> Screen:
    return _screen(
        blocks(
            "⚒️ <b>Fundar Guilda</b>",
            narrative(GUILD_TEXT),
            escape(error) if error else None,
            "✏️ Envie o nome da Guilda.",
        ),
        [_back("guild:root")],
    )


def render_found_tag(name: str, *, error: str | None = None) -> Screen:
    return _screen(
        blocks(
            "🏷️ <b>Fundar Guilda</b>",
            _field("🏰", "Nome", name),
            narrative("Escolha uma TAG para identificar sua Guilda de forma abreviada."),
            escape(error) if error else None,
            "🏷️ Envie a TAG da Guilda.",
        ),
        [_back("guild:found")],
    )


def render_symbol_picker() -> Screen:
    buttons = [
        _button(symbol, f"guild:sym:{index}") for index, symbol in enumerate(GUILD_SYMBOLS)
    ]
    rows = [buttons[index : index + 5] for index in range(0, len(buttons), 5)]
    return _screen(
        blocks(
            "🏰 <b>Símbolo da Guilda</b>",
            narrative("Escolha um símbolo para representar sua Guilda."),
        ),
        [*rows, _back("guild:found")],
    )


def render_found_confirm(name: str, tag: str, symbol: str) -> Screen:
    return _screen(
        blocks(
            "⚒️ <b>Fundar Guilda</b>",
            guild_title(symbol, tag, name),
            narrative("Confira os dados da Guilda antes de confirmar a fundação."),
        ),
        [[_button("✅ Confirmar", "guild:foundok"), _button(CANCEL_LABEL, "guild:root")]],
    )


# -------------------------------------------------------------------- comuns


def render_confirm(text: str, confirm_data: str, cancel_data: str = "guild:root") -> Screen:
    return _screen(
        escape(text),
        [[_button("✅ Confirmar", confirm_data), _button(CANCEL_LABEL, cancel_data)]],
    )


def render_expired() -> Screen:
    return _screen(
        blocks(
            "⏳ <b>Ação Expirada</b>",
            narrative("Esta ação não está mais disponível. Atualize a tela para continuar."),
        ),
        [[_button("🔄 Atualizar", "guild:root")], _back("menu:back")],
    )


def when(value: datetime) -> str:
    return value.strftime("%d/%m às %H:%M")

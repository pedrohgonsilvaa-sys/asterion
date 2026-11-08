"""Telegram presentation for Guilds (GDD v1.6.0 §30, §44.1).

Every button carries ids (never a Name or TAG) packed as 22-character urlsafe
base64 so the callback stays under Telegram's 64-byte limit. The server
revalidates each id on click.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.guilds import (
    GuildApplicationView,
    GuildInviteView,
    GuildPage,
    GuildView,
    PublicGuildView,
)
from asterion.bot.creation_ui import Screen
from asterion.domain.guilds import (
    MAX_ACTIVE_PROJECTS,
    MAX_PROJECT_LEVEL,
    GuildRole,
    ProjectKind,
    Recruitment,
    project_build_time,
    project_cost,
)

FOUND_PROMPT = "Envie o Nome e a TAG da Guilda, separados por espaço. Exemplo: Aurora AUR"
SEARCH_PROMPT = "Envie o Nome ou a TAG da Guilda que você procura."
INVITE_PROMPT = "Envie o nome do personagem que você quer convidar para a Guilda."
DEPOSIT_PROMPT = (
    "Envie quantas Coroas da sua carteira depositar na Tesouraria. O depósito é definitivo."
)
RENAME_PROMPT = (
    "Envie o novo Nome e a nova TAG, separados por espaço. Use - para manter um deles. "
    "Exemplo: Aurora - . O Renome custa 15.000 Coroas da Tesouraria e tem recarga de 30 dias."
)
CONTRIBUTE_WALLET_PREFIX = "Quantas Coroas da sua carteira para a Obra "
CONTRIBUTE_TREASURY_PREFIX = "Quantas Coroas da Tesouraria para a Obra "

OBRA_LABELS = {
    ProjectKind.LODGING: "Alojamentos",
    ProjectKind.FORGE: "Forja",
    ProjectKind.VEIL_ALTAR: "Altar do Véu",
    ProjectKind.TREASURY: "Tesouraria",
    ProjectKind.VEIL_ARCHIVE: "Arquivo do Véu",
    ProjectKind.HUNTERS_POST: "Posto dos Caçadores",
    ProjectKind.WAR_HALL: "Salão de Guerra",
}

ROLE_LABELS = {
    GuildRole.LEADER: "Líder",
    GuildRole.OFFICER: "Oficial",
    GuildRole.MEMBER: "Membro",
}

# One Portuguese message per GuildError code (the two name codes come from the
# domain's normalisers and are raised through GuildError as well).
GUILD_ERROR_MESSAGES = {
    "character_missing": "Personagem indisponível.",
    "invalid_name": "O Nome da Guilda precisa ter de 3 a 16 letras, sem espaços ou números.",
    "invalid_tag": "A TAG precisa ter exatamente 3 letras.",
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
    return InlineKeyboardMarkup(inline_keyboard=[list(row) for row in rows])


def _recruitment_label(recruitment: Recruitment) -> str:
    return "Aberto" if recruitment is Recruitment.OPEN else "Fechado"


def render_guild_menu(
    guild: GuildView | None, *, invites: int = 0, applications: int = 0
) -> Screen:
    if guild is None:
        return Screen(
            "🏰 Guilda\n\nVocê ainda não faz parte de uma Guilda. Funde a sua, procure uma "
            "Guilda aberta ou responda aos convites que recebeu.",
            "links",
            _keyboard(
                [
                    [_button("Fundar Guilda", "guild:found")],
                    [_button("Procurar Guilda", "guild:search")],
                    [_button("Guildas abertas", "guild:browse:0")],
                    [_button("Minhas Inscrições", "guild:myapps")],
                    [_button(f"Convites recebidos · {invites}", "guild:inbox")],
                    [_button("← Vínculos", "links:root")],
                ]
            ),
        )
    lines = [
        f"🏰 {guild.name} [{guild.tag}]",
        "",
        f"Membros · {guild.member_count}/{guild.capacity}",
        f"Recrutamento · {_recruitment_label(guild.recruitment)}",
        f"Seu cargo · {ROLE_LABELS[guild.viewer_role]}",
    ]
    lines.append(f"Tesouraria · {_crowns(guild.treasury_crowns)} Coroas")
    if guild.over_cap:
        lines.append("⚠️ A Guilda está acima da capacidade e não aceita novos membros.")
    if guild.dissolution_due_at is not None:
        lines.append(
            f"⚠️ Dissolução marcada para {_when(guild.dissolution_due_at)}. "
            "Tesouraria e Obras estão congeladas."
        )
    lines.append("")
    for member in guild.members:
        lines.append(
            f"· {member.name} · Nv. {member.level} · "
            f"{member.character_class.title()} · {ROLE_LABELS[member.role]}"
        )
    gid = pack(guild.guild_id)
    rows: list[list[InlineKeyboardButton]] = []
    if guild.viewer_role in (GuildRole.LEADER, GuildRole.OFFICER):
        toggle = (
            _button("Fechar recrutamento", f"guild:recr:c:{gid}")
            if guild.recruitment is Recruitment.OPEN
            else _button("Abrir recrutamento", f"guild:recr:o:{gid}")
        )
        rows.extend(
            [
                [_button("Convidar", f"guild:invite:{gid}")],
                [_button(f"Inscrições recebidas · {applications}", f"guild:recv:{gid}")],
                [toggle],
            ]
        )
    if len(guild.members) > 1 and guild.viewer_role in (GuildRole.LEADER, GuildRole.OFFICER):
        rows.append([_button("Gerenciar membros", f"guild:mem:{gid}")])
    rows.append([_button("Tesouraria e Obras", f"guild:works:{gid}")])
    if guild.viewer_role is GuildRole.LEADER:
        if guild.dissolution_due_at is None:
            rows.append([_button("Renomear Guilda", f"guild:ren:{gid}")])
            rows.append([_button("Dissolver Guilda", f"guild:diss:{gid}")])
        else:
            rows.append([_button("Cancelar dissolução", f"guild:dissno:{gid}")])
    if guild.viewer_role is not GuildRole.LEADER:
        rows.append([_button("Sair da Guilda", f"guild:leave:{gid}")])
    rows.append([_button("← Vínculos", "links:root")])
    return Screen("\n".join(lines), "links", _keyboard(rows))


def _crowns(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _when(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%d/%m %H:%M UTC")


def contribute_prompt(kind: ProjectKind, *, from_treasury: bool) -> str:
    prefix = CONTRIBUTE_TREASURY_PREFIX if from_treasury else CONTRIBUTE_WALLET_PREFIX
    return f"{prefix}{OBRA_LABELS[kind]}? A contribuição é definitiva."


def kind_from_contribute_prompt(text: str) -> tuple[ProjectKind, bool] | None:
    for from_treasury in (False, True):
        for kind in OBRA_LABELS:
            if text == contribute_prompt(kind, from_treasury=from_treasury):
                return kind, from_treasury
    return None


def parse_crowns(text: str) -> int | None:
    """Accept `20000` or `20.000`; anything else is not an amount."""
    digits = text.strip().replace(".", "")
    if not digits.isdigit() or len(digits) > 12:
        return None
    return int(digits)


def render_works(guild: GuildView) -> Screen:
    """Treasury and Obras (§30.2). Members only; never shown on the public page."""
    gid = pack(guild.guild_id)
    leader = guild.viewer_role is GuildRole.LEADER
    frozen = guild.dissolution_due_at is not None
    levels = dict(guild.obra_levels)
    lines = [
        "🏛️ Tesouraria e Obras",
        "",
        f"Tesouraria · {_crowns(guild.treasury_crowns)} Coroas",
        "Depósitos e contribuições são definitivos: nada volta para a carteira.",
        "",
        "Obras",
    ]
    for kind, label in OBRA_LABELS.items():
        lines.append(f"· {label} · nível {levels.get(kind, 0)}/{MAX_PROJECT_LEVEL}")
    rows: list[list[InlineKeyboardButton]] = []
    if guild.active_projects:
        lines.extend(["", "Em andamento"])
    for project in guild.active_projects:
        label = OBRA_LABELS[project.kind]
        if project.status == "funding":
            lines.append(
                f"· {label} {_ROMAN[project.level]} · Financiamento · "
                f"{_crowns(project.funded)}/{_crowns(project.cost)}"
            )
            if not frozen:
                pid = pack(project.project_id)
                rows.append([_button(f"Contribuir · {label}", f"guild:con:w:{gid}:{pid}")])
                if leader:
                    rows.append([_button(f"Tesouraria → {label}", f"guild:con:t:{gid}:{pid}")])
        else:
            done = _when(project.completes_at) if project.completes_at else "—"
            lines.append(f"· {label} {_ROMAN[project.level]} · Construção até {done}")
    lines.extend(["", "Só Alojamentos tem efeito por enquanto: mais vagas na Guilda."])
    if frozen:
        lines.append("⚠️ A Guilda está em dissolução: Tesouraria e Obras estão congeladas.")
    else:
        rows.append([_button("Depositar na Tesouraria", f"guild:dep:{gid}")])
        if leader:
            rows.append([_button("Iniciar Obra", f"guild:newp:{gid}")])
    rows.append([_button("← Guilda", "guild:root")])
    return Screen("\n".join(lines), "links", _keyboard(rows))


def render_new_project(guild: GuildView) -> Screen:
    gid = pack(guild.guild_id)
    levels = dict(guild.obra_levels)
    active = {project.kind for project in guild.active_projects}
    lines = ["🏗️ Iniciar Obra", ""]
    rows: list[list[InlineKeyboardButton]] = []
    if len(guild.active_projects) >= MAX_ACTIVE_PROJECTS:
        lines.append("A Guilda já tem 2 Obras em andamento. Conclua uma antes de iniciar outra.")
    else:
        lines.append("Escolha a Obra. O próximo nível abre em Financiamento.")
        for kind, label in OBRA_LABELS.items():
            level = levels.get(kind, 0) + 1
            if kind in active or level > MAX_PROJECT_LEVEL:
                continue
            cost = _crowns(project_cost(level))
            hours = int(project_build_time(level).total_seconds() // 3600)
            rows.append(
                [
                    _button(
                        f"{label} {_ROMAN[level]} · {cost} · {hours}h",
                        f"guild:np:{gid}:{kind.value}",
                    )
                ]
            )
    rows.append([_button("← Tesouraria e Obras", f"guild:works:{gid}")])
    return Screen("\n".join(lines), "links", _keyboard(rows))


_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}


def render_manage_members(guild: GuildView) -> Screen:
    gid = pack(guild.guild_id)
    leader = guild.viewer_role is GuildRole.LEADER
    lines = ["👥 Gerenciar membros", ""]
    rows: list[list[InlineKeyboardButton]] = []
    for member in guild.members:
        if member.character_id == guild.viewer_character_id:
            continue
        lines.append(f"· {member.name} · {ROLE_LABELS[member.role]}")
        cid = pack(member.character_id)
        label = member.name[:8]
        row: list[InlineKeyboardButton] = []
        if leader and member.role is GuildRole.MEMBER:
            row.append(_button(f"Promover {label}", f"guild:pro:{gid}:{cid}"))
        if leader and member.role is GuildRole.OFFICER:
            row.append(_button(f"Rebaixar {label}", f"guild:dem:{gid}:{cid}"))
        if leader:
            row.append(_button(f"Liderança {label}", f"guild:lead:{gid}:{cid}"))
        can_kick = leader and member.role is not GuildRole.LEADER
        can_kick = can_kick or (
            guild.viewer_role is GuildRole.OFFICER and member.role is GuildRole.MEMBER
        )
        if can_kick:
            row.append(_button(f"Expulsar {label}", f"guild:kick:{gid}:{cid}"))
        for button in row:
            rows.append([button])
    if len(rows) == 0:
        lines.append("Nenhum membro que você possa gerenciar.")
    rows.append([_button("← Guilda", "guild:root")])
    return Screen("\n".join(lines), "links", _keyboard(rows))


def render_public_page(page: PublicGuildView | None, *, can_apply: bool = True) -> Screen:
    if page is None:
        return Screen(
            "🏰 Guilda\n\nEssa Guilda não existe mais.",
            "links",
            _keyboard([[_button("← Guilda", "guild:root")]]),
        )
    lines = [
        f"🏰 {page.name} [{page.tag}]",
        "",
        f"Membros · {page.member_count}/{page.capacity}",
        f"Recrutamento · {_recruitment_label(page.recruitment)}",
    ]
    rows: list[list[InlineKeyboardButton]] = []
    if can_apply and page.accepts_applications:
        rows.append([_button("Enviar Inscrição", f"guild:apply:{pack(page.guild_id)}")])
    elif can_apply:
        lines.extend(["", "Esta Guilda não aceita inscrições agora."])
    rows.append([_button("← Guilda", "guild:root")])
    return Screen("\n".join(lines), "links", _keyboard(rows))


def render_search_results(query: str, results: Sequence[PublicGuildView]) -> Screen:
    if not results:
        return Screen(
            f"🔎 Procurar Guilda\n\nNenhuma Guilda encontrada para “{query}”.",
            "links",
            _keyboard(
                [
                    [_button("Procurar de novo", "guild:search")],
                    [_button("← Guilda", "guild:root")],
                ]
            ),
        )
    rows = [
        [_button(f"{item.name} [{item.tag}] · {item.member_count}/{item.capacity}",
                 f"guild:page:{pack(item.guild_id)}")]
        for item in results
    ]
    rows.append([_button("← Guilda", "guild:root")])
    return Screen("🔎 Procurar Guilda\n\nEscolha uma Guilda.", "links", _keyboard(rows))


def render_browse(page: GuildPage, *, first: bool) -> Screen:
    if not page.items:
        return Screen(
            "🏰 Guildas abertas\n\nNenhuma Guilda está recrutando agora.",
            "links",
            _keyboard([[_button("← Guilda", "guild:root")]]),
        )
    rows = [
        [_button(f"{item.name} [{item.tag}] · {item.member_count}/{item.capacity}",
                 f"guild:page:{pack(item.guild_id)}")]
        for item in page.items
    ]
    nav: list[InlineKeyboardButton] = []
    if not first:
        nav.append(_button("« Início", "guild:browse:0"))
    if page.next_after is not None:
        nav.append(_button("Próxima »", f"guild:browse:{pack(page.next_after)}"))
    if nav:
        rows.append(nav)
    rows.append([_button("← Guilda", "guild:root")])
    return Screen(
        "🏰 Guildas abertas\n\nGuildas com vaga, em ordem estável (não é um ranking).",
        "links",
        _keyboard(rows),
    )


def render_my_applications(applications: Sequence[GuildApplicationView]) -> Screen:
    status = {
        "pending": "Pendente",
        "approved": "Aprovada",
        "rejected": "Recusada",
        "cancelled": "Cancelada",
    }
    if not applications:
        return Screen(
            "📨 Minhas Inscrições\n\nVocê não tem inscrições.",
            "links",
            _keyboard([[_button("← Guilda", "guild:root")]]),
        )
    lines = ["📨 Minhas Inscrições", ""]
    rows: list[list[InlineKeyboardButton]] = []
    for item in applications:
        label = status.get(item.status, item.status)
        lines.append(f"· {item.guild_name} [{item.guild_tag}] · {label}")
        if item.status == "pending":
            token = pack(item.application_id)
            rows.append([_button(f"Cancelar · {item.guild_tag}", f"guild:cancelapp:{token}")])
    rows.append([_button("← Guilda", "guild:root")])
    return Screen("\n".join(lines), "links", _keyboard(rows))


def render_inbox(invites: Sequence[GuildInviteView]) -> Screen:
    if not invites:
        return Screen(
            "📩 Convites recebidos\n\nVocê não tem convites pendentes.",
            "links",
            _keyboard([[_button("← Guilda", "guild:root")]]),
        )
    lines = ["📩 Convites recebidos", ""]
    rows: list[list[InlineKeyboardButton]] = []
    for index, invite in enumerate(invites, start=1):
        who = f" · convite de {invite.inviter_name}" if invite.inviter_name else ""
        lines.append(f"{index}. {invite.guild_name} [{invite.guild_tag}]{who}")
        token = pack(invite.invite_id)
        rows.append(
            [
                _button(f"Aceitar · {index}", f"guild:inv:a:{token}"),
                _button(f"Recusar · {index}", f"guild:inv:d:{token}"),
            ]
        )
    rows.append([_button("← Guilda", "guild:root")])
    return Screen("\n".join(lines), "links", _keyboard(rows))


def render_received_applications(
    guild_id: UUID, applications: Sequence[GuildApplicationView]
) -> Screen:
    back = _button("← Guilda", "guild:root")
    if not applications:
        return Screen(
            "📨 Inscrições recebidas\n\nNenhuma inscrição pendente.",
            "links",
            _keyboard([[back]]),
        )
    lines = ["📨 Inscrições recebidas", ""]
    rows: list[list[InlineKeyboardButton]] = []
    for index, item in enumerate(applications, start=1):
        lines.append(f"{index}. {item.character_name} · Nv. {item.character_level}")
        token = pack(item.application_id)
        rows.append(
            [
                _button(f"Aprovar · {index}", f"guild:app:a:{pack(guild_id)}:{token}"),
                _button(f"Recusar · {index}", f"guild:app:r:{pack(guild_id)}:{token}"),
            ]
        )
    rows.append([back])
    return Screen("\n".join(lines), "links", _keyboard(rows))


def render_confirm(text: str, confirm_data: str) -> Screen:
    return Screen(
        text,
        "links",
        _keyboard(
            [
                [_button("Confirmar", confirm_data)],
                [_button("Cancelar", "guild:root")],
            ]
        ),
    )


def render_expired() -> Screen:
    return Screen(
        "⏳ Ação Expirada\n\nEsta ação não está mais disponível. Atualize a tela para continuar.",
        "links",
        _keyboard([[_button("Atualizar", "guild:root")], [_button("← Vínculos", "links:root")]]),
    )

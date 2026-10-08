"""Telegram presentation for the initial Vínculos → Grupo surface."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.groups import GroupView, IncomingInviteView
from asterion.bot.creation_ui import Screen


def revision36(value: int) -> str:
    if value < 0:
        raise ValueError("revision must be nonnegative")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    output = ""
    while value:
        value, remainder = divmod(value, 36)
        output = alphabet[remainder] + output
    return output


def render_links(group: GroupView | None, incoming_count: int) -> Screen:
    group_line = (
        f"👥 Grupo · {len(group.members)}/4"
        if group is not None
        else "👥 Você ainda não faz parte de um Grupo."
    )
    text = f"🤝 Vínculos\n\n{group_line}\n📩 Convites · {incoming_count}"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Grupo", callback_data="group:root")],
            [InlineKeyboardButton(text="Convites", callback_data="group:inbox")],
            [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
        ]
    )
    return Screen(text, "links", keyboard)


def render_group(group: GroupView | None) -> Screen:
    if group is None:
        return Screen(
            "👥 Grupo\n\nCrie um Grupo persistente para convidar companheiros e preparar "
            "atividades em conjunto.",
            "links",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Criar Grupo", callback_data="group:create")],
                    [InlineKeyboardButton(text="Convites", callback_data="group:inbox")],
                    [InlineKeyboardButton(text="← Vínculos", callback_data="links:root")],
                ]
            ),
        )

    lines = [f"👥 Grupo · {len(group.members)}/4", ""]
    rows: list[list[InlineKeyboardButton]] = []
    for index, member in enumerate(group.members, start=1):
        leader = " · Líder" if member.is_leader else ""
        lines.append(
            f"{index}. {escape(member.name)} · Nv. {member.level} · "
            f"{escape(member.character_class.title())}{leader}"
        )
        if group.is_leader and not member.is_leader:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"Liderança · {member.name[:10]}",
                        callback_data=(
                            f"group:lead:{member.character_id.hex}:{revision36(group.revision)}"
                        ),
                    ),
                    InlineKeyboardButton(
                        text=f"Expulsar · {member.name[:10]}",
                        callback_data=(
                            f"group:kick:{member.character_id.hex}:{revision36(group.revision)}"
                        ),
                    ),
                ]
            )
    lines.extend(
        [
            "",
            "Convide pelo nome com /grupo convidar Nome. Convites expiram em 10 minutos.",
        ]
    )
    rows.extend(
        [
            [InlineKeyboardButton(text="Convites", callback_data="group:inbox")],
            [
                InlineKeyboardButton(
                    text="Sair do Grupo",
                    callback_data=f"group:leave:{revision36(group.revision)}",
                )
            ],
            [InlineKeyboardButton(text="← Vínculos", callback_data="links:root")],
        ]
    )
    return Screen("\n".join(lines), "links", InlineKeyboardMarkup(inline_keyboard=rows))


def render_invites(invites: tuple[IncomingInviteView, ...]) -> Screen:
    if not invites:
        text = "📩 Convites de Grupo\n\nVocê não tem convites pendentes."
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="← Grupo", callback_data="group:root")]]
        )
        return Screen(text, "links", keyboard)
    lines = ["📩 Convites de Grupo", ""]
    rows: list[list[InlineKeyboardButton]] = []
    for index, invite in enumerate(invites, start=1):
        lines.append(
            f"{index}. Grupo de {escape(invite.group_leader_name)} · "
            f"convite de {escape(invite.inviter_name)}"
        )
        token = invite.invite_id.hex
        revision = revision36(invite.revision)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Aceitar · {index}",
                    callback_data=f"group:invite:a:{token}:{revision}",
                ),
                InlineKeyboardButton(
                    text=f"Recusar · {index}",
                    callback_data=f"group:invite:d:{token}:{revision}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text="← Grupo", callback_data="group:root")])
    return Screen("\n".join(lines), "links", InlineKeyboardMarkup(inline_keyboard=rows))


def render_expired_group_action() -> Screen:
    return Screen(
        "⏳ Ação Expirada\n\nEsta ação não está mais disponível. Atualize a tela para continuar.",
        "links",
        InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Atualizar", callback_data="group:root")],
                [InlineKeyboardButton(text="← Vínculos", callback_data="links:root")],
            ]
        ),
    )

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p1 import P1View
from asterion.bot.creation_ui import Screen


def render_p1(view: P1View) -> Screen:
    if view.combat is not None:
        from asterion.application.prologue import CombatView
        from asterion.bot.combat_ui import render_combat

        return render_combat(
            CombatView(view.combat.id, view.combat.id, view.character_id, view.combat, "p1", 0)
        )
    if view.step == 1:
        text = (
            "📜 Vozes na Estrada\n\nA estrada guarda sinais recentes sob a cinza.\n\n"
            "Etapa 1 · Seguir pela Estrada das Cinzas."
        )
        action = "p1:follow"
    elif view.step == 2 and not view.progress.get("pegadas"):
        text = "👣 Pegadas na Cinza\n\nMarcas recentes cruzam a estrada."
        action = "p1:examine:pegadas"
    else:
        text = "〰️ Sulcos Recentes\n\nSulcos profundos desaparecem entre as pedras."
        action = "p1:examine:sulcos"
    return Screen(
        text,
        "p1",
        InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Examinar" if "examine" in action else "Seguir pela Estrada",
                        callback_data=action,
                    )
                ]
            ]
        ),
    )

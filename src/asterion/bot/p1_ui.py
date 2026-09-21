from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p1 import P1View
from asterion.bot.creation_ui import Screen


def _button(text, data):
    return InlineKeyboardButton(text=text, callback_data=data)


def render_p1(view: P1View) -> Screen:
    if view.combat is not None:
        from asterion.application.prologue import CombatView
        from asterion.bot.combat_ui import render_combat

        cv = CombatView(
            view.activity_id, view.encounter_id, view.character_id, view.combat, "p1", 0, "p1"
        )
        return render_combat(cv)
    p = view.progress or {}
    if view.step == 1:
        text = "📜 Vozes na Estrada\n\nSeguir pela Estrada das Cinzas."
        kb = [[_button("Seguir pela Estrada", f"p1:{view.state_version}:follow")]]
    elif view.step == 2 and not p.get("pegadas"):
        text = "👣 Pegadas na Cinza"
        kb = [[_button("Examinar", f"p1:{view.state_version}:examine:pegadas")]]
    elif view.step == 2:
        text = "〰️ Sulcos Recentes"
        kb = [[_button("Examinar", f"p1:{view.state_version}:examine:sulcos")]]
    elif view.step == 3 and p.get("defeat"):
        text = (
            "💀 Derrota\n\n🔥 Braseiro da Estrada\nEstrada das Cinzas · Terras do Ocaso\n\n"
            "❤️ HP · Restaurado\n\n📜 Vozes na Estrada · Em Andamento\n\n"
            "Recuperado no Braseiro da Estrada, você precisará retornar ao encontro e "
            "vencê-lo antes de seguir viagem."
        )
        kb = [
            [_button("Retornar à Estrada", f"p1:{view.state_version}:retry")],
            [_button("← Menu", "menu:back")],
        ]
    elif view.step == 4:
        text = "🏚️ Refúgio do Ocaso\n\nA estrada conduz a um abrigo entre as ruínas."
        kb = [[_button("Entrar no Refúgio", f"p1:{view.state_version}:refuge")]]
    elif view.step == 5:
        text = "Alda Veyr\n\nUma voz indica o caminho adiante."
        kb = [[_button("Seguir a Indicação", f"p1:{view.state_version}:alda")]]
    elif view.step == 6:
        text = "Oren Cal\n\nO caminho leva ao braseiro."
        kb = [[_button("Ir ao Braseiro", f"p1:{view.state_version}:oren")]]
    elif view.step == 7:
        text = "🔥 Braseiro do Refúgio\nRefúgio do Ocaso · Terras do Ocaso"
        kb = [[_button("Ativar Braseiro", f"p1:{view.state_version}:activate")]]
    else:
        text = "Vozes na Estrada"
        kb = []
    return Screen(text, "p1", InlineKeyboardMarkup(inline_keyboard=kb) if kb else None)

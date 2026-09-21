# ruff: noqa: E501
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p1 import P1View
from asterion.bot.creation_ui import Screen


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _mission_header() -> str:
    return "📜 Vozes na Estrada · Em Andamento\nMissão Principal · Terras do Ocaso"


def render_p1(view: P1View) -> Screen:
    if view.combat is not None:
        from asterion.application.prologue import CombatView
        from asterion.bot.combat_ui import render_combat

        return render_combat(
            CombatView(
                view.activity_id, view.encounter_id, view.character_id, view.combat, "p1", 0, "p1"
            )
        )
    p = view.progress or {}
    version = view.state_version
    if view.status == "completed":
        text = (
            "🔥 Braseiro do Refúgio\nRefúgio do Ocaso · Terras do Ocaso\n\n"
            "O calor é constante. Pela primeira vez, a estrada atrás de você parece ter um ponto de retorno.\n\n"
            "🔥 Braseiro · Descoberto\n❤️ Descansar · Restaura HP\n\n"
            "✅ Vozes na Estrada · Concluída"
        )
        keyboard = [[_button("Descansar", "world:rest")], [_button("← Menu", "menu:back")]]
        return Screen(text, "p1_completed", InlineKeyboardMarkup(inline_keyboard=keyboard))
    if view.step == 1:
        text = (
            f"{_mission_header()}\n\n"
            "<i>A chama deixada para trás desaparece pouco a pouco entre a fuligem. A Estrada das Cinzas segue adiante, irregular e silenciosa, mas desta vez há marcas recentes onde antes havia apenas abandono.</i>\n\n"
            "🎯 Objetivo · Seguir pela Estrada das Cinzas"
        )
        keyboard = [
            [_button("Seguir pela Estrada", f"p1:{version}:follow")],
            [_button("Ver no Mapa", "world:map")],
            [_button("← Missões", "world:missions")],
        ]
    elif view.step == 2 and not p.get("pegadas"):
        text = (
            f"{_mission_header()}\n\n👣 Pegadas na Cinza\n\n"
            "<i>Marcas de botas cortam a fuligem em uma única direção. As bordas ainda estão nítidas demais para terem permanecido ali por muito tempo.</i>\n\n"
            "🎯 Objetivo · Examinar Sinais · 0/2"
        )
        keyboard = [
            [_button("Examinar", f"p1:{version}:examine:pegadas")],
            [_button("← Missões", "world:missions")],
        ]
    elif view.step == 2:
        text = (
            f"{_mission_header()}\n\n🛞 Sulcos Recentes\n\n"
            "<i>Duas marcas estreitas atravessam a cinza ao lado das pegadas. A fuligem ainda não voltou a cobrir completamente os sulcos deixados pelas rodas.</i>\n\n"
            "🎯 Objetivo · Examinar Sinais · 1/2"
        )
        keyboard = [
            [_button("Examinar", f"p1:{version}:examine:sulcos")],
            [_button("← Missões", "world:missions")],
        ]
    elif view.step == 3 and p.get("defeat"):
        text = (
            "💀 Derrota\n\n🔥 Braseiro da Estrada\nEstrada das Cinzas · Terras do Ocaso\n\n"
            "❤️ HP · Restaurado\n\n📜 Vozes na Estrada · Em Andamento\n\n"
            "<i>Recuperado no Braseiro da Estrada, você precisará retornar ao encontro e vencê-lo antes de seguir viagem.</i>"
        )
        keyboard = [
            [_button("Retornar à Estrada", f"p1:{version}:retry")],
            [_button("← Menu", "menu:back")],
        ]
    elif view.step == 4:
        text = (
            f"{_mission_header()}\n\n🏚️ Refúgio do Ocaso\n\n"
            "<i>Mais adiante, a estrada deixa de ser apenas ruína. Pedras empilhadas, madeira reaproveitada e pontos de luz surgem através da fuligem.</i>\n\n"
            "<i>Não é uma cidade. Ainda assim, pela primeira vez desde que despertou na estrada, há sinais claros de que pessoas permanecem aqui.</i>\n\n"
            "🎯 Objetivo · Alcançar o Refúgio do Ocaso"
        )
        keyboard = [
            [_button("Entrar no Refúgio", f"p1:{version}:refuge")],
            [_button("← Missões", "world:missions")],
        ]
    elif view.step == 5:
        text = (
            "🪖 Alda Veyr\n\n"
            "<i>Uma mulher observa a estrada antes mesmo de olhar para você. Sua atenção passa primeiro pelas marcas da fuligem, depois por suas armas e só então pelo seu rosto.</i>\n\n"
            "<i>— Se chegou até aqui sozinho, já aprendeu a primeira regra do Ocaso: estrada nenhuma permanece segura só porque alguém a chamou de estrada.</i>\n\n"
            "<i>Ela explica que o Refúgio sobrevive mantendo rotas, recursos e vigias funcionando.</i>\n\n🎯 Objetivo · Falar com Alda Veyr"
        )
        keyboard = [
            [_button("Seguir a Indicação", f"p1:{version}:alda")],
            [_button("← Missões", "world:missions")],
        ]
    elif view.step == 6:
        text = (
            "✒️ Oren Cal\n\n"
            "<i>Alda indica um homem cercado por folhas, tábuas riscadas e fragmentos trazidos das estradas. Ele organiza cada peça como se perder uma palavra fosse tão grave quanto perder uma pessoa.</i>\n\n"
            "<i>— Se ouvir nomes no vento, não os descarte depressa. Há coisas nestas terras que sobrevivem apenas porque alguém se lembra delas.</i>\n\n"
            "<i>Ele registra relatos, nomes e inscrições trazidos das estradas.</i>\n\n🎯 Objetivo · Conhecer Oren Cal"
        )
        keyboard = [
            [_button("Ir ao Braseiro", f"p1:{version}:oren")],
            [_button("← Missões", "world:missions")],
        ]
    else:
        text = (
            "🔥 Braseiro do Refúgio\nRefúgio do Ocaso · Terras do Ocaso\n\n"
            "<i>No centro do Refúgio, uma chama resiste entre pedras marcadas pelo uso. Pessoas passam por ela sem cerimônia, mas nenhuma ignora completamente sua presença.</i>\n\n"
            "<i>O calor é constante. Pela primeira vez, a estrada atrás de você parece ter um ponto de retorno.</i>\n\n"
            "🎯 Objetivo · Ativar o Braseiro do Refúgio"
        )
        keyboard = [
            [_button("Ativar Braseiro", f"p1:{version}:activate")],
            [_button("← Missões", "world:missions")],
        ]
    return Screen(text, "p1", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

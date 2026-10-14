"""Telegram presentation for the opening Nareth campaign missions."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.nareth_missions import P13_ID, NarethMissionView
from asterion.bot.creation_ui import Screen


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _screen(text: str, rows: list[list[InlineKeyboardButton]]) -> Screen:
    return Screen(text, "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _route_to_expected_location(location: str, expected_location: str) -> str:
    if location == "Campinas do Meridiano" and expected_location == "Posto de Nareth":
        return "road:route:nareth_posto"
    if location == "Posto de Nareth" and expected_location == "Campinas do Meridiano":
        return "road:route:nareth_campinas"
    return "world:map"


def render_nareth_mission(view: NarethMissionView) -> Screen:
    quest_id = view.quest_id
    title = escape(view.title)
    version = view.state_version
    if view.kind == "offer":
        gate = (
            "P12 concluída · Nv.21 · entrada nas Campinas do Meridiano"
            if quest_id == P13_ID
            else "P13 concluída · Nv.22 · Posto de Nareth"
        )
        action = (
            _button("Acompanhar", f"nareth:mission:{quest_id}")
            if quest_id == P13_ID
            else _button("Aceitar Missão", f"nareth:start:{quest_id}")
        )
        return _screen(
            f"📜 {title}\n"
            f"Missão {'Principal' if quest_id == P13_ID else 'Secundária'} · "
            f"Planícies de Nareth\n\nRequer · {gate}",
            [[action], [_button("← Missões", "world:missions")]],
        )
    if view.kind == "unavailable":
        gate = (
            "P12 concluída, Nv.21 e estar nas Campinas do Meridiano"
            if quest_id == P13_ID
            else "P13 concluída, Nv.22 e estar no Posto de Nareth"
        )
        return _screen(
            f"📜 {title} · Indisponível\n\nRequer {gate}.",
            [[_button("← Missões", "world:missions")]],
        )
    if view.kind == "completed":
        reward = (
            "✨ 19.350 XP · 🪙 420 Coroas\n"
            "📦 Bronze de Marco · 1 · Vinculado\n"
            "📦 Couro de Horizonte · 1 · Vinculado"
            if quest_id == P13_ID
            else "✨ 8.260 XP · 🪙 220 Coroas"
        )
        return _screen(
            f"📜 {title} · Concluída\n\n{reward}\n\nRotas de Nareth foi atualizada.",
            [[_button("← Missões", "world:missions")], [_button("🗺️ Mapa", "world:map")]],
        )

    rows: list[list[InlineKeyboardButton]] = []
    if quest_id == P13_ID:
        expected_location = (
            "Campinas do Meridiano"
            if view.kind
            in {"line", "compare", "horizon_brazier", "follow_route", "arrive_posto"}
            else "Posto de Nareth"
        )
        descriptions = {
            "line": (
                "Examine a antiga linha de pedra nas Campinas.",
                "line",
                "Examinar a linha",
            ),
            "compare": (
                "Compare as marcações discordantes.",
                "compare",
                "Comparar marcações",
            ),
            "horizon_brazier": (
                "Registre o Braseiro do Horizonte.",
                "horizon_brazier",
                "Registrar Braseiro",
            ),
            "follow_route": (
                "Siga a rota verificada até o Posto.",
                "follow_route",
                "Registrar rota",
            ),
            "posto_brazier": (
                "Registre o Braseiro do Posto.",
                "posto_brazier",
                "Registrar Braseiro",
            ),
            "speak_nera": (
                "Fale com Nera Voss no Posto.",
                "speak_nera",
                "Falar com Nera",
            ),
            "record_codex": (
                "Registre as primeiras Rotas de Nareth.",
                "record_codex",
                "Registrar no Códice",
            ),
        }
        if view.location != expected_location:
            description = f"Continue em {expected_location} para avançar este objetivo."
            route = _route_to_expected_location(view.location, expected_location)
            rows.append([_button("Abrir rota", route)])
        elif view.kind == "arrive_posto":
            description = "Alcance o Posto de Nareth pela rota verificada."
            rows.append([_button("Seguir para o Posto", "road:route:nareth_posto")])
        else:
            description, action, label = descriptions.get(
                view.kind,
                ("Continue a investigação registrada.", "", ""),
            )
            if action:
                rows.append([_button(label, f"nareth:action:{quest_id}:{version}:{action}")])
    else:
        markers = list((view.progress or {}).get("markers", []))
        expected_location = (
            "Campinas do Meridiano"
            if view.kind in {"markers", "compare"}
            else "Posto de Nareth"
        )
        if view.location != expected_location:
            description = f"Continue em {expected_location} para avançar este objetivo."
            route = _route_to_expected_location(view.location, expected_location)
            rows.append([_button("Abrir rota", route)])
        elif view.kind == "markers":
            marker = ("a", "b", "c")[min(len(markers), 2)]
            labels = {
                "a": "Examinar primeira referência",
                "b": "Examinar segunda referência",
                "c": "Examinar terceira referência",
            }
            description = "Examine as três referências de rota nas Campinas."
            rows.append(
                [_button(labels[marker], f"nareth:ex:{quest_id}:{version}:{marker}")]
            )
        elif view.kind == "compare":
            description = "Compare as referências sem atribuir causa sobrenatural às diferenças."
            rows.append(
                [_button("Comparar referências", f"nareth:action:{quest_id}:{version}:compare")]
            )
        else:
            description = "Retorne a Nera Voss no Posto de Nareth."
            rows.append(
                [_button("Relatar a Nera", f"nareth:action:{quest_id}:{version}:report")]
            )
    text = (
        f"📜 {title} · Planícies de Nareth\n\n{description}"
        f"\n\n📍 Local Atual · {escape(view.location)}"
    )
    rows.extend(
        [
            [_button("📍 Local Atual", "world:local")],
            [_button("← Missões", "world:missions")],
        ]
    )
    return _screen(text, rows)

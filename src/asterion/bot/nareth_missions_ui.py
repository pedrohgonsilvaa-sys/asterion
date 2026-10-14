"""Telegram presentation for Nareth campaign missions and combat."""

# ruff: noqa: E501

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.nareth_missions import (
    MISSION_REWARD_CHOICES,
    P13_ID,
    P14_ID,
    P15_ID,
    P16_ID,
    S14_ID,
    S15_ID,
    S16_ID,
    NarethMissionView,
)
from asterion.application.prologue import CombatView
from asterion.bot.combat_ui import render_combat
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
    if quest_id in {P14_ID, S14_ID, P15_ID, S15_ID, P16_ID, S16_ID}:
        return _render_midgame_mission(view)
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


_MIDGAME_ROUTES = {
    "Campinas do Meridiano": ("nareth_campinas", "🌾"),
    "Posto de Nareth": ("nareth_posto", "🏘️"),
    "Canais Secos": ("nareth_canais", "🛤️"),
    "Campos Invertidos": ("nareth_campos", "🌾"),
    "Observatório do Eixo": ("nareth_observatorio", "🧭"),
}


def _route_toward(current: str, target: str) -> str | None:
    edges = {
        "Campinas do Meridiano": ("Posto de Nareth",),
        "Posto de Nareth": ("Campinas do Meridiano", "Canais Secos"),
        "Canais Secos": ("Posto de Nareth", "Campos Invertidos"),
        "Campos Invertidos": ("Canais Secos", "Observatório do Eixo"),
        "Observatório do Eixo": ("Campos Invertidos",),
    }
    if current not in edges or target not in edges:
        return None
    queue = [(current, None)]
    seen = {current}
    for location, first_hop in queue:
        for neighbor in edges[location]:
            if neighbor in seen:
                continue
            hop = neighbor if first_hop is None else first_hop
            if neighbor == target:
                route_key = _MIDGAME_ROUTES[hop][0]
                return f"road:route:{route_key}"
            seen.add(neighbor)
            queue.append((neighbor, hop))
    return None


_MIDGAME_STAGES = {
    P14_ID: {
        1: ("Posto de Nareth", "Receber de Nera o mapa de acesso aos Canais Secos.", "receive_map", "Receber mapa"),
        2: ("Canais Secos", "Descobrir os Canais Secos.", None, "Seguir aos Canais"),
        3: ("Canais Secos", "Examinar a comporta antiga e as marcas de medição.", "examine_gate", "Examinar comporta"),
        4: ("Canais Secos", "Seguir o leito até a junção de referências divergentes.", "follow_bed", "Seguir o leito"),
        5: ("Canais Secos", "Derrotar um Escaravelho de Canal Nv.23.", "combat_start", "Iniciar encontro"),
        6: ("Canais Secos", "Recuperar a placa de medição, sem valor econômico.", "recover_plate", "Recuperar placa"),
        7: ("Canais Secos", "Comparar a placa com o marco da entrada.", "compare_plate", "Comparar placa"),
        8: ("Posto de Nareth", "Retornar ao Posto.", None, "Retornar ao Posto"),
        9: ("Posto de Nareth", "Entregar a placa a Talen Orm.", "deliver_plate", "Entregar a Talen"),
    },
    S14_ID: {
        1: ("Posto de Nareth", "Receber duas rotas concorrentes.", "receive_routes", "Receber rotas"),
        2: ("Canais Secos", "Percorrer a rota alta.", None, "Percorrer rota alta"),
        3: ("Canais Secos", "Examinar a ponte estreita.", "examine_bridge", "Examinar ponte"),
        4: ("Canais Secos", "Percorrer a rota baixa.", "follow_low_route", "Percorrer rota baixa"),
        5: ("Canais Secos", "Marcar a passagem mais estável.", "mark_stable_route", "Marcar passagem"),
        6: ("Canais Secos", "Encontrar sinais de acesso subterrâneo; entrar na Masmorra não é necessário.", "find_access_signs", "Examinar sinais"),
        7: ("Posto de Nareth", "Retornar a Nera.", None, "Retornar ao Posto"),
        8: ("Posto de Nareth", "Relatar a rota a Nera.", "report", "Relatar a Nera"),
    },
    P15_ID: {
        1: ("Posto de Nareth", "Falar com Talen sobre registros incompatíveis.", "speak_talen", "Falar com Talen"),
        2: ("Campos Invertidos", "Descobrir os Campos Invertidos.", None, "Seguir aos Campos"),
        3: ("Campos Invertidos", "Medir uma distância curta entre dois marcos.", "measure_short_distance", "Medir distância"),
        4: ("Campos Invertidos", "Repetir o percurso usando outra referência.", "repeat_with_reference", "Repetir percurso"),
        5: ("Campos Invertidos", "Observar a divergência dos registros históricos após a Ruptura.", "review_historical_records", "Revisar registros"),
        6: ("Campos Invertidos", "Derrotar um Casco Invertido Nv.25.", "combat_start", "Iniciar encontro"),
        7: ("Campos Invertidos", "Examinar placas naturais sem tratá-las como prova de Avesso.", "examine_natural_plates", "Examinar placas"),
        8: ("Campos Invertidos", "Recuperar um fragmento de marco sem valor econômico.", "recover_marker", "Recuperar fragmento"),
        9: ("Posto de Nareth", "Retornar a Talen.", None, "Retornar ao Posto"),
        10: ("Posto de Nareth", "Escolher exatamente um Equipamento Raro de P15.", None, "Escolher equipamento"),
    },
    S15_ID: {
        1: ("Campos Invertidos", "Receber o último ponto confirmado.", "receive_last_point", "Receber ponto"),
        2: ("Campos Invertidos", "Seguir rastros humanos nos Campos.", "follow_tracks", "Seguir rastros"),
        3: ("Campos Invertidos", "Encontrar uma carga abandonada.", "find_cargo", "Examinar carga"),
        4: ("Campos Invertidos", "Localizar os viajantes em uma depressão protegida do vento.", "find_travelers", "Localizar viajantes"),
        5: ("Campos Invertidos", "Confirmar que não houve desaparecimento temporal nem duplicação de pessoas.", "confirm_no_displacement", "Registrar confirmação"),
        6: ("Campos Invertidos", "Marcar uma rota de retorno.", "mark_return_route", "Marcar retorno"),
        7: ("Posto de Nareth", "Voltar ao Posto.", None, "Retornar ao Posto"),
    },
    P16_ID: {
        1: ("Posto de Nareth", "Receber de Talen a tradução parcial da placa de P14.", "receive_translation", "Receber tradução"),
        2: ("Observatório do Eixo", "Seguir a linha de marcos até o Observatório.", None, "Seguir ao Observatório"),
        4: ("Observatório do Eixo", "Examinar a plataforma de alinhamento.", "examine_alignment", "Examinar plataforma"),
        5: ("Observatório do Eixo", "Examinar o braço mecânico de medição.", "examine_arm", "Examinar braço"),
        6: ("Observatório do Eixo", "Encontrar um registro com termos de referência, desvio e estabilidade.", "record_terms", "Registrar termos"),
        7: ("Observatório do Eixo", "Derrotar um Vigia do Meridiano Nv.28.", "combat_start", "Iniciar encontro"),
        8: ("Observatório do Eixo", "Acessar o painel analógico de registro.", "read_analog_panel", "Ler painel analógico"),
        9: ("Posto de Nareth", "Retornar a Talen.", None, "Retornar ao Posto"),
    },
    S16_ID: {
        1: ("Posto de Nareth", "Receber de Nera quatro pontos de verificação.", "receive_checkpoints", "Receber pontos"),
        2: ("Campos Invertidos", "Confirmar um marco nos Campos Invertidos.", None, "Confirmar marco"),
        3: ("Canais Secos", "Confirmar uma linha de pedra próxima aos Canais.", None, "Confirmar linha"),
        4: ("Canais Secos", "Rejeitar uma rota antiga que não fecha com as referências atuais.", "reject_old_route", "Rejeitar rota"),
        5: ("Observatório do Eixo", "Verificar um ponto na borda do Observatório.", None, "Verificar ponto"),
        6: ("Observatório do Eixo", "Registrar a diferença entre mapa antigo e percurso atual.", "record_difference", "Registrar diferença"),
        7: ("Posto de Nareth", "Retornar a Nera.", None, "Retornar ao Posto"),
        8: ("Posto de Nareth", "Criar ou atualizar Cartografia do Erro no Códice.", "update_codex", "Atualizar Códice"),
    },
}


def _render_midgame_mission(view: NarethMissionView) -> Screen:
    quest = view.quest_id
    title = escape(view.title)
    version = view.state_version
    if view.kind == "combat" and view.combat is not None and view.activity_id is not None:
        hud = render_combat(
            CombatView(
                activity_id=view.activity_id,
                encounter_id=view.encounter_id or view.activity_id,
                character_id=view.character_id,
                combat=view.combat,
                stage="campaign",
                xp=0,
                context="nareth",
                consumable_options=view.consumable_options,
                consumable_screen=view.consumable_screen,
                selected_consumable_id=view.selected_consumable_id,
                selected_target_id=view.selected_target_id,
                selection_parent=view.selection_parent,
                consumable_notice=view.consumable_notice,
                consumable_quantities=view.consumable_quantities,
                consumable_budget_limit=view.consumable_budget_limit,
                ready_consumable_option=view.ready_consumable_option,
                combat_actor_key=view.combat_actor_key,
            )
        )
        return Screen(
            f"📜 {title} · Planícies de Nareth\n⚔️ Encontro Roteirizado · "
            f"{escape(view.location)}\n\n{hud.text}",
            "missions",
            hud.keyboard,
            parse_mode=hud.parse_mode,
        )
    if view.kind == "offer":
        return _screen(
            f"📜 {title}\nMissão {'Principal' if quest in {P14_ID, P15_ID, P16_ID} else 'Secundária'}"
            f" · Planícies de Nareth\n\nRequisitos atendidos. A jornada permanece individual "
            "para progresso e recompensas.",
            [[_button("Iniciar Missão" if quest in {P14_ID, P15_ID, P16_ID} else "Aceitar Missão", f"nareth:start:{quest}")],
             [_button("← Missões", "world:missions")]],
        )
    if view.kind == "unavailable":
        gates = {
            P14_ID: "P13 concluída · Nv.23 · Posto de Nareth",
            S14_ID: "P14 concluída · Nv.24 · Posto de Nareth",
            P15_ID: "P14 concluída · Nv.25 · Posto de Nareth",
            S15_ID: "Campos Invertidos acessíveis · P15 ativa/concluída · Nv.25",
            P16_ID: "P15 concluída · Nv.27 · Posto de Nareth",
            S16_ID: "P16 ativa/concluída · Nv.27 · Posto de Nareth",
        }
        return _screen(
            f"📜 {title} · Indisponível\n\nRequer · {gates[quest]}.",
            [[_button("← Missões", "world:missions")]],
        )
    if view.kind == "choice" and quest == P15_ID:
        rows = [
            [_button(f"{name} · {slot}", f"nareth:choice:{quest}:{version}:{choice}")]
            for choice, (name, slot) in MISSION_REWARD_CHOICES.items()
        ]
        rows.append([_button("← Missões", "world:missions")])
        return _screen(
            f"📜 {title} · Escolha individual\n\nEscolha exatamente 1 equipamento Raro, Nv.25, +0 e vinculado.",
            rows,
        )
    if view.kind == "completed":
        rewards = {
            P14_ID: "22.000 XP · 450 Coroas · 1 Bronze de Marco · 2 Ervas de Vento · 1 Pó de Eixo",
            S14_ID: "16.380 XP · 350 Coroas · 1 Erva de Vento · 1 Pó de Eixo",
            P15_ID: "24.800 XP · 480 Coroas · escolha Rara: " + MISSION_REWARD_CHOICES.get(str((view.progress or {}).get("reward_choice")), ("equipamento selecionado", ""))[0],
            S15_ID: "9.920 XP · 240 Coroas · 2 Couros de Horizonte",
            P16_ID: "27.800 XP · 640 Coroas · 2 Bronzes de Marco · 2 Pós de Eixo",
            S16_ID: "19.460 XP · 380 Coroas · 2 Bronzes de Marco · 1 Couro de Horizonte · 1 Pó de Eixo",
        }
        return _screen(
            f"✅ {title} · Concluída\n\n{escape(rewards[quest])}",
            [[_button("← Missões", "world:missions")], [_button("🗺️ Mapa", "world:map")]],
        )
    if view.kind == "combat_result":
        return _screen(
            f"⚔️ Encontro de Campanha encerrado\n\nA participação foi registrada para {escape(title)}.",
            [[_button("← Missões", "world:missions")]],
        )

    step = view.step or 1
    stage = _MIDGAME_STAGES[quest].get(step)
    if stage is None:
        return _screen(
            f"📜 {title} · Planícies de Nareth\n\nAcompanhe a etapa persistida da missão.",
            [[_button("← Missões", "world:missions")]],
        )
    expected_location, description, action, label = stage
    rows: list[list[InlineKeyboardButton]] = []
    if view.location != expected_location:
        route = _route_toward(view.location, expected_location)
        if route:
            rows.append([_button(f"Seguir para {expected_location}", route)])
        else:
            rows.append([_button("Abrir mapa", "world:map")])
    elif view.kind == "combat_start":
        if (view.progress or {}).get("awaiting_retry"):
            description = f"O encontro terminou. {description}"
            label = "Tentar novamente"
        rows.extend(
            [
                [_button(label + " · Solo", f"nareth:combat:{quest}:{version}:solo")],
                [_button("Formar Grupo", f"nareth:combat:{quest}:{version}:group")],
            ]
        )
    elif action:
        rows.append([_button(label, f"nareth:action:{quest}:{version}:{action}")])
    elif view.kind in {"travel_canais", "travel_campos", "travel_observatorio", "return_posto"}:
        route = _route_toward(view.location, expected_location)
        if route:
            rows.append([_button(label, route)])
    if view.proposal_id is not None and view.proposal_status == "pending":
        description = "Confirmação enviada ao Grupo. Consulte o painel do Grupo para acompanhar a entrada."
    text = (
        f"📜 {title} · Planícies de Nareth\n\n🎯 {description}"
        f"\n\nEtapa · {step}\n📍 {escape(view.location)}"
    )
    rows.extend(
        [[_button("📍 Local Atual", "world:local")], [_button("← Missões", "world:missions")]]
    )
    return _screen(text, rows)

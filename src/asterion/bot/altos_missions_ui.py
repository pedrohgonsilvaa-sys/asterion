"""Telegram screens for the Altos Cinéreos opening mission."""

# ruff: noqa: E501

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.altos_missions import (
    P25_TITLE,
    P26_TITLE,
    P27_REWARD_OPTIONS,
    P27_TITLE,
    P28_TITLE,
    P29_PRIORITY_RECORDS,
    P29_TITLE,
    AltosMissionView,
)
from asterion.application.prologue import CombatView
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def render_altos_mission(view: AltosMissionView) -> Screen:
    fallback_title = (
        P28_TITLE if view.quest_id == "P28"
        else P29_TITLE if view.quest_id == "P29"
        else P27_TITLE if view.quest_id == "P27"
        else P26_TITLE if view.quest_id == "P26"
        else P25_TITLE
    )
    title = escape(view.title or fallback_title)
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "combat" and view.combat is not None and view.activity_id is not None:
        hud = render_combat(
            CombatView(
                activity_id=view.activity_id,
                encounter_id=view.encounter_id or view.activity_id,
                character_id=view.character_id,
                combat=view.combat,
                stage="campaign",
                xp=0,
                context="altos",
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
            f"📜 {title} · Altos Cinéreos\n⚔️ Encontro roteirizado · {'Bastilha de Carga' if view.quest_id in {'P28', 'P29'} else 'Pedreiras Suspensas' if view.quest_id == 'P27' else 'Escarpa da Cinza'}\n\n{hud.text}",
            "missions",
            hud.keyboard,
            parse_mode=hud.parse_mode,
        )

    if view.quest_id == "P27":
        return _render_p27(view, title, rows)
    if view.quest_id == "P28":
        return _render_p28(view, title, rows)
    if view.quest_id == "P29":
        return _render_p29(view, title, rows)
    if view.quest_id == "P26":
        return _render_p26(view, title, rows)

    if view.status == "completed":
        text = (
            f"📜 {title} · Concluída\n\n"
            "✨ 53.500 XP · 720 Coroas\n"
            "📦 1 Ferro de Contrapeso · 1 Líquen de Pedreira"
        )
        rows.append([_button("← Missões", "world:missions")])
        return Screen(text, "missions", InlineKeyboardMarkup(inline_keyboard=rows))

    step_text = {
        2: "Examine os três pontos de sustentação visíveis: contraforte, cabo e escora.",
        3: "Vença o encontro roteirizado contra o Lobo de Escarpa (Nv. 41).",
        4: "Alcance e registre o Braseiro da Escarpa.",
        5: "Acompanhe Hesa Tor e confirme a dependência da rota em reparos redundantes.",
        6: "Chegue ao Abrigo do Peso.",
        7: "Registre o Braseiro do Abrigo.",
        8: "Fale pessoalmente com Rava Kern e Doren Vask.",
        9: "Registre no Códice o trecho Carga Observável.",
    }.get(view.step, "Retome a etapa atual da missão.")
    lines = [f"📜 {title} · Em Andamento", "Altos Cinéreos · Escarpa da Cinza", "", step_text]

    if view.step == 2:
        support_points = set(view.progress.get("support_points", ()))
        options = (
            ("inspect_contraforte", "Examinar o contraforte"),
            ("inspect_cabo", "Examinar o cabo"),
            ("inspect_escora", "Examinar a escora"),
        )
        for action, label in options:
            if action not in support_points:
                rows.append(
                    [_button(label, f"altos:action:{view.state_version}:{action}")]
                )
    elif view.step == 3:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:{view.state_version}:solo")],
                    [_button("Solicitar encontro em Grupo", f"altos:combat:{view.state_version}:group")],
                )
            )
    elif view.step == 4:
        rows.append(
            [_button("Registrar Braseiro da Escarpa", f"altos:action:{view.state_version}:register_escarpa_brazier")]
        )
    elif view.step == 5:
        rows.append(
            [_button("Confirmar reparos redundantes", f"altos:action:{view.state_version}:confirm_redundant_repairs")]
        )
    elif view.step == 6:
        rows.append([_button("Seguir para o Abrigo do Peso", "road:route:altos_abrigo")])
    elif view.step == 7:
        rows.append(
            [_button("Registrar Braseiro do Abrigo", f"altos:action:{view.state_version}:register_abrigo_brazier")]
        )
    elif view.step == 8:
        if not view.progress.get("spoke_rava"):
            rows.append([_button("Falar com Rava Kern", f"altos:action:{view.state_version}:speak_rava")])
        if not view.progress.get("spoke_doren"):
            rows.append([_button("Falar com Doren Vask", f"altos:action:{view.state_version}:speak_doren")])
    elif view.step == 9:
        if not view.progress.get("codex_recorded"):
            rows.append([_button("Registrar Carga Observável", f"altos:action:{view.state_version}:record_codex")])
        else:
            rows.append([_button("Concluir com Rava Kern", f"altos:action:{view.state_version}:conclude_with_rava")])

    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_p26(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "suspended":
        return Screen(
            f"📜 {title} · Suspensa\n\nP25 deve estar concluída e o personagem precisa alcançar Nv. 43 para receber a ordem de Sel Ardan.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )
    if view.status == "available":
        rows.append([_button("Receber ordem de Sel Ardan", "altos:action:0:receive_order")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Disponível\nAltos Cinéreos · Abrigo do Peso\n\nSel Ardan entrega uma ordem sem contexto suficiente.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "completed":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\n✨ 57.900 XP · 750 Coroas\n📦 3 Ferros de Contrapeso · 1 Cinza de Basalto",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    step_text = {
        2: "Alcance e descubra Pontes de Fuligem.",
        3: "Examine três estações de ordem com datas e selos físicos diferentes.",
        4: "Verifique a ponte mantida em espera por uma autorização incompatível.",
        5: "Compare os registros com Sel Ardan.",
        6: "Registre pela primeira vez o nome Regência de Continuidade no Códice.",
        7: "Conclua que a Regência era uma autoridade emergencial, sem reconstruir sua cadeia integral de decisões.",
    }.get(view.step, "Retome a etapa atual da missão.")
    local = "Pontes de Fuligem" if view.step in {2, 3, 4, 5, 6, 7} else "Abrigo do Peso"
    lines = [f"📜 {title} · Em Andamento", f"Altos Cinéreos · {local}", "", step_text]
    if view.step == 2:
        rows.append([_button("Seguir para Pontes de Fuligem", "road:route:altos_pontes")])
    elif view.step == 3:
        examined = set(view.progress.get("order_stations", ()))
        for action, label in (
            ("inspect_order_station_1", "Examinar estação de ordem I"),
            ("inspect_order_station_2", "Examinar estação de ordem II"),
            ("inspect_order_station_3", "Examinar estação de ordem III"),
        ):
            if action not in examined:
                rows.append([_button(label, f"altos:action:{view.state_version}:{action}")])
    elif view.step == 4:
        rows.append([_button("Verificar a ponte em espera", f"altos:action:{view.state_version}:verify_waiting_bridge")])
    elif view.step == 5:
        if view.location == "Pontes de Fuligem":
            rows.append([_button("Comparar registros com Sel Ardan", f"altos:action:{view.state_version}:compare_records_with_sel")])
        else:
            rows.append([_button("Retornar a Pontes de Fuligem", "road:route:altos_pontes")])
    elif view.step == 6:
        rows.append([_button("Registrar Regência de Continuidade", f"altos:action:{view.state_version}:record_regencia_codex")])
    elif view.step == 7:
        rows.append([_button("Concluir a análise com Sel Ardan", f"altos:action:{view.state_version}:conclude_emergency_authority")])
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_p27(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "suspended":
        return Screen(
            f"📜 {title} · Suspensa\n\nP26 deve estar concluída e o personagem precisa alcançar Nv. 45 para iniciar a jornada com Doren Vask e Rava Kern.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )
    if view.status == "available":
        rows.extend(
            (
                [_button("Iniciar P27 com Doren e Rava", "altos:action:0:activate_p27")],
                [_button("← Missões", "world:missions")],
            )
        )
        return Screen(
            f"📜 {title} · Disponível\nAltos Cinéreos · Abrigo do Peso\n\nDoren Vask e Rava Kern apresentam registros de prioridades de sustentação.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "completed":
        selected = view.progress.get("reward_item_id", "Equipamento Raro escolhido")
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\n✨ 62.400 XP · 780 Coroas\n🎁 Equipamento escolhido: {escape(str(selected))}",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    step_text = {
        1: "Alcance e descubra Pedreiras Suspensas.",
        2: "Examine uma rota de blocos, um registro de cabo e uma tabela de distribuição.",
        3: "Vença a Carcaça Mineral Nv. 45 em um encontro roteirizado.",
        4: "Recupere a placa sem valor econômico sobre prioridades de sustentação.",
        5: "Compare a placa com Doren Vask e Rava Kern.",
        6: "Registre Prioridades de Carga no Códice.",
        7: "Escolha pessoalmente um Equipamento Raro Nv. 45.",
    }.get(view.step, "Retome a etapa atual da missão.")
    local = "Abrigo do Peso" if view.step == 1 else "Pedreiras Suspensas"
    lines = [f"📜 {title} · Em Andamento", f"Altos Cinéreos · {local}", "", step_text]
    if view.step == 1:
        rows.append([_button("Seguir para Pedreiras Suspensas", "road:route:altos_pedreiras")])
    elif view.step == 2:
        examined = set(view.progress.get("pedreira_records", ()))
        for action, label in (
            ("inspect_block_route", "Examinar rota de blocos"),
            ("inspect_cable_record", "Examinar registro de cabo"),
            ("inspect_distribution_table", "Examinar tabela de distribuição"),
        ):
            if action not in examined:
                rows.append([_button(label, f"altos:action:{view.state_version}:{action}")])
    elif view.step == 3:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:P27:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:P27:{view.state_version}:solo")],
                    [_button("Solicitar encontro em Grupo", f"altos:combat:P27:{view.state_version}:group")],
                )
            )
    elif view.step == 4:
        rows.append([_button("Recuperar a placa de prioridades", f"altos:action:{view.state_version}:recover_priority_plate")])
    elif view.step == 5:
        rows.append([_button("Comparar com Doren e Rava", f"altos:action:{view.state_version}:compare_plate_with_doren_and_rava")])
    elif view.step == 6:
        rows.append([_button("Registrar Prioridades de Carga", f"altos:action:{view.state_version}:record_priorities_codex")])
    elif view.step == 7:
        selected = view.progress.get("reward_choice")
        for key, (_item_id, name, _slot) in P27_REWARD_OPTIONS.items():
            if key != selected:
                rows.append([_button(name, f"altos:choice:P27:{view.state_version}:{key}")])

    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_p28(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "suspended":
        return Screen(
            f"📜 {title} · Suspensa\n\nP27 deve estar concluída e o personagem precisa alcançar Nv. 47 para seguir para a Bastilha de Carga.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )
    if view.status == "available":
        rows.extend(
            (
                [_button("Iniciar P28 com Sel e Maro", "altos:action:0:activate_p28")],
                [_button("← Missões", "world:missions")],
            )
        )
        return Screen(
            f"📜 {title} · Disponível\nAltos Cinéreos · Pedreiras Suspensas\n\nSel Ardan e Maro Keln apresentam duas fontes sobre os Desvelados.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "completed":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\n✨ 67.100 XP · 1.010 Coroas\n📦 2 Ferros de Contrapeso · 1 Couro de Escarpa · 1 Cinza de Basalto",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    step_text = {
        1: "Alcance e descubra a Bastilha de Carga.",
        2: "Localize o arquivo oficial de contenção de informação.",
        3: "Localize o memorial crítico preservado fora da cadeia oficial.",
        4: "Enfrente o Vigia de Carga (Nv. 47) em um combate roteirizado.",
        5: "Compare as duas fontes com Sel Ardan e Maro Keln.",
        6: "Registre a origem dos Desvelados no Códice, distinguindo oposição legítima da radicalização posterior.",
        7: "Registre que a sabotagem da Âncora Central não pode ser atribuída ao movimento nem confirmada como fato concluído.",
    }.get(view.step, "Retome a etapa atual da missão.")
    local = "Pedreiras Suspensas" if view.step == 1 else "Bastilha de Carga"
    lines = [f"📜 {title} · Em Andamento", f"Altos Cinéreos · {local}", "", step_text]
    if view.step == 1:
        rows.append([_button("Seguir para Bastilha de Carga", "road:route:altos_bastilha")])
    elif view.step == 2:
        rows.append(
            [_button("Localizar arquivo de contenção", f"altos:action:{view.state_version}:locate_containment_archive")]
        )
    elif view.step == 3:
        rows.append(
            [_button("Localizar memorial crítico", f"altos:action:{view.state_version}:locate_critical_memorial")]
        )
    elif view.step == 4:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:P28:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:P28:{view.state_version}:solo")],
                    [_button("Solicitar encontro em Grupo", f"altos:combat:P28:{view.state_version}:group")],
                )
            )
    elif view.step == 5:
        rows.append(
            [_button("Comparar fontes com Sel e Maro", f"altos:action:{view.state_version}:compare_sources_with_sel_and_maro")]
        )
    elif view.step == 6:
        rows.append(
            [_button("Registrar origem dos Desvelados", f"altos:action:{view.state_version}:record_desvelados_codex")]
        )
    elif view.step == 7:
        rows.append(
            [_button("Registrar limites da conclusão", f"altos:action:{view.state_version}:record_non_attribution")]
        )
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_p29(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "suspended":
        return Screen(
            f"📜 {title} · Suspensa\n\nP28 deve estar concluída e o personagem precisa alcançar Nv. 49 para prosseguir.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )
    if view.status == "available":
        rows.extend(
            (
                [_button("Iniciar P29 com Sel e Maro", "altos:action:0:activate_p29")],
                [_button("← Missões", "world:missions")],
            )
        )
        return Screen(
            f"📜 {title} · Disponível\nAltos Cinéreos · Bastilha de Carga\n\nSel Ardan e Maro Keln apresentam os riscos documentados da Convergência.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "completed":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\n✨ 72.000 XP · 1.050 Coroas\n📦 2 Ferros de Contrapeso · 1 Líquen de Pedreira · 1 Cinza de Basalto",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    step_text = {
        1: "Reúna os três registros de prioridade já acessíveis na Bastilha.",
        2: "Localize Convergência em uma ordem técnica.",
        3: "Verifique o esquema físico de rede e acoplamento, sem acessar os minutos finais da Ruptura.",
        4: "Vença o Supervisor de Carga (Nv. 49) em um encontro roteirizado.",
        5: "Compare com Sel Ardan e Maro Keln os riscos documentados de prosseguir e interromper.",
        6: "Registre no Códice que a Convergência buscava recalibrar a rede; a probabilidade final de sucesso permanece desconhecida.",
        7: "Abra a rota ao Coração do Colosso.",
    }.get(view.step, "Retome a etapa atual da missão.")
    lines = [f"📜 {title} · Em Andamento", "Altos Cinéreos · Bastilha de Carga", "", step_text]
    if view.step == 1:
        records = set(view.progress.get("priority_records", ()))
        for record in P29_PRIORITY_RECORDS:
            if record not in records:
                index = P29_PRIORITY_RECORDS.index(record) + 1
                rows.append(
                    [_button(f"Reunir registro de prioridade {index}/3", f"altos:action:{view.state_version}:collect_{record}")]
                )
    elif view.step == 2:
        rows.append([_button("Localizar ordem técnica", f"altos:action:{view.state_version}:locate_convergence_order")])
    elif view.step == 3:
        rows.append([_button("Verificar esquema físico", f"altos:action:{view.state_version}:inspect_network_coupling_diagram")])
    elif view.step == 4:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:P29:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:P29:{view.state_version}:solo")],
                    [_button("Solicitar encontro em Grupo", f"altos:combat:P29:{view.state_version}:group")],
                )
            )
    elif view.step == 5:
        rows.append([_button("Comparar riscos com Sel e Maro", f"altos:action:{view.state_version}:compare_documented_risks_with_sel_and_maro")])
    elif view.step == 6:
        rows.append([_button("Registrar objetivo no Códice", f"altos:action:{view.state_version}:record_convergence_codex")])
    elif view.step == 7:
        rows.append([_button("Abrir rota ao Coração", f"altos:action:{view.state_version}:open_route_to_coracao")])
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))

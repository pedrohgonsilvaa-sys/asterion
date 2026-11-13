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
    P30_REWARD_OPTIONS,
    P30_TITLE,
    P31_TITLE,
    P32_TITLE,
    P33_REWARD_OPTIONS,
    P33_TITLE,
    P34_TITLE,
    P35_TITLE,
    P36_REWARD_OPTIONS,
    P36_TITLE,
    S26_TITLE,
    S30_TITLE,
    S31_TITLE,
    S35_TITLE,
    S36_TITLE,
    AltosMissionView,
)
from asterion.application.prologue import CombatView
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_BASTILHA_LABEL,
    ALTOS_ESCARPA_LABEL,
    ALTOS_PEDREIRAS_LABEL,
    ALTOS_PONTES_LABEL,
    CONFINS_CAMARA_REGENCIA_LABEL,
    CONFINS_NO_CENTRAL_LABEL,
)
from asterion.bot.asset_catalog import with_mission_art
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def _render_altos_mission(view: AltosMissionView) -> Screen:
    fallback_title = (
        P36_TITLE if view.quest_id == "P36"
        else P35_TITLE if view.quest_id == "P35"
        else P34_TITLE if view.quest_id == "P34"
        else P33_TITLE if view.quest_id == "P33"
        else P32_TITLE if view.quest_id == "P32"
        else P31_TITLE if view.quest_id == "P31"
        else P28_TITLE if view.quest_id == "P28"
        else P29_TITLE if view.quest_id == "P29"
        else P27_TITLE if view.quest_id == "P27"
        else P26_TITLE if view.quest_id == "P26"
        else P30_TITLE if view.quest_id == "P30"
        else S30_TITLE if view.quest_id == "S30"
        else S31_TITLE if view.quest_id == "S31"
        else S35_TITLE if view.quest_id == "S35"
        else S36_TITLE if view.quest_id == "S36"
        else S26_TITLE if view.quest_id == "S26"
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
                campaign_shared=view.campaign_shared,
            )
        )
        combat_location = (
            view.location
            if view.quest_id in {"S26", "S31", "S34", "S35", "S36", "P31", "P32", "P33", "P34", "P35", "P36"}
            else "Coração do Colosso"
            if view.quest_id == "P30"
            else "Bastilha de Carga"
            if view.quest_id == "S30"
            else "Bastilha de Carga"
            if view.quest_id in {"P28", "P29"}
            else "Pedreiras Suspensas"
            if view.quest_id == "P27"
            else "Escarpa da Cinza"
        )
        encounter_label = (
            "Chefe opcional · economia zero"
            if view.quest_id == "S30"
            else "Encontro roteirizado · economia zero"
            if view.quest_id in {"S31", "S34", "S35", "S36", "P31", "P32", "P33", "P34", "P35", "P36"}
            else "Encontro roteirizado"
            if view.quest_id == "S26"
            else "Encontro de Campanha"
        )
        return Screen(
            f"📜 {title} · {'Confins do Véu' if view.quest_id in {'S31', 'P31', 'P32', 'P33', 'P34', 'P35', 'P36', 'S36'} else 'Altos Cinéreos'}\n⚔️ {encounter_label} · {escape(combat_location)}\n\n{hud.text}",
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
    if view.quest_id == "P30":
        return _render_p30(view, title, rows)
    if view.quest_id == "P31":
        return _render_p31(view, title, rows)
    if view.quest_id == "P32":
        return _render_p32(view, title, rows)
    if view.quest_id == "P33":
        return _render_p33(view, title, rows)
    if view.quest_id == "P34":
        return _render_p34(view, title, rows)
    if view.quest_id == "P35":
        return _render_p35(view, title, rows)
    if view.quest_id == "P36":
        return _render_p36(view, title, rows)
    if view.quest_id == "P26":
        return _render_p26(view, title, rows)
    if view.quest_id == "S26":
        return _render_s26_combat_step(view, title, rows)

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


def _render_p33(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "available":
        rows.extend(
            (
                [_button("Iniciar P33 com Roven e Talen", "altos:action:0:activate_p33")],
                [_button("← Missões", "world:missions")],
            )
        )
        return Screen(
            f"📜 {title} · Disponível\nConfins do Véu · Estradas Ausentes\n\n"
            "Roven Pell e Talen Nyr apresentam evidências físicas de referências incompatíveis.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "suspended":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Suspensa\n\nP33 requer P32 concluída e Nv.55. "
            "O acesso às Fraturas será retomado quando você atingir o nível exigido.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "completed":
        selected = escape(str(view.progress.get("reward_item_id", "Equipamento Raro escolhido")))
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\n✨ 87.650 XP · 920 Coroas\n"
            f"🎁 Equipamento Raro Nv.55: {selected}\n"
            "🏅 Feito · Nomear sem Dominar · Título Leitor de Incoerências",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    step_text = {
        1: "Atravesse às Fraturas do Limiar; observe as duas marcas físicas de referência discordantes.",
        2: "Examine três evidências físicas distintas nas Fraturas.",
        3: "Vença a Casca de Reflexo (Nv.55) em combate roteirizado.",
        4: "Com Roven Pell, compreenda o Avesso como um estado de relações não confiáveis, não como lugar ou vontade.",
        5: "Registre no Códice somente o conhecimento legitimamente adquirido.",
        6: "Escolha um Equipamento Raro Nv.55 com Roven e conclua P33.",
    }.get(view.step, "Retome a etapa atual da missão.")
    location = "Estradas Ausentes" if view.step == 1 else "Fraturas do Limiar"
    lines = [
        f"📜 {title} · Em Andamento",
        f"Confins do Véu · {location}",
        "",
        f"Etapa {view.step}/6 · {step_text}",
    ]
    if view.step == 1:
        rows.append([_button("Seguir para Fraturas do Limiar", "road:route:confins_fraturas_limiar")])
    elif view.step == 2:
        evidence = set(view.progress.get("physical_evidence_ids", ()))
        for action, label in (
            ("inspect_stone_position", "Examinar a posição da pedra"),
            ("inspect_wear_state", "Examinar o estado de desgaste"),
            ("inspect_trail_observation_sequence", "Verificar a sequência de observação da trilha"),
        ):
            if action not in evidence:
                rows.append([_button(label, f"altos:action:{view.state_version}:{action}")])
    elif view.step == 3:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:P33:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:P33:{view.state_version}:solo")],
                )
            )
    elif view.step == 4:
        rows.append([_button("Interpretar as evidências com Roven", f"altos:action:{view.state_version}:interpret_avesso_with_roven")])
    elif view.step == 5:
        rows.append([_button("Registrar no Códice", f"altos:action:{view.state_version}:record_avesso_codex")])
    elif view.step == 6:
        selected = view.progress.get("reward_choice")
        for key, (_item_id, name, _slot) in P33_REWARD_OPTIONS.items():
            if key != selected:
                rows.append([_button(name, f"altos:action:{view.state_version}:choose_p33_reward_{key}")])
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_p34(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "available":
        rows.extend(
            (
                [_button("Iniciar P34 com Eris e Sera", "altos:action:0:activate_p34")],
                [_button("← Missões", "world:missions")],
            )
        )
        return Screen(
            f"📜 {title} · Disponível\nConfins do Véu · Fraturas do Limiar\n\n"
            "P33 foi concluída. Nv.57 abre a investigação da Âncora Central; a ativação libera a rota individual ao Nó Central.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "suspended":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Suspensa\n\nP34 requer P33 concluída e Nv.57. "
            "A rota ao Nó Central será retomada quando você atingir o nível exigido.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "completed":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\n✨ 93.250 XP · 1.200 Coroas\n"
            "📦 2 Ferros de Baliza · 1 Couro de Marcha · 1 Pó de Referência\n"
            "🏅 Feito · Nó Não é Fonte",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    arrived = bool(view.progress.get("no_arrival_recorded"))
    location = "Nó Central" if arrived else "Fraturas do Limiar"
    step_text = {
        2: "Entre no Nó Central e examine condução de referência, alinhamento de rotas e comunicação de falha.",
        3: "Enfrente o Custódio Desfasado Nv.57 em encontro roteirizado, sem economia própria.",
        4: "Localize evidências de que diferentes Âncoras estabilizavam regiões antes da noite final.",
        5: "Compare a interpretação técnica de Eris com a documentação civil de Roven.",
        6: "Registre no Códice o papel de coordenação e referência da Âncora Central; conclua com Eris e Sera.",
    }.get(view.step, "Retome a etapa atual da missão.")
    lines = [
        f"📜 {title} · Em Andamento",
        f"Confins do Véu · {location}",
        "",
        f"Etapa {view.step}/6 · {step_text}",
    ]
    if view.step == 2:
        if not arrived:
            rows.append([_button("Seguir para o Nó Central", "road:route:confins_no_central")])
        else:
            evidence = set(view.progress.get("physical_point_evidence_ids", ()))
            for action, label in (
                ("inspect_reference_conduction", "Examinar a condução de referência"),
                ("inspect_route_alignment", "Examinar o alinhamento de rotas"),
                ("inspect_failure_communication", "Examinar a comunicação de falha"),
            ):
                if action not in evidence:
                    rows.append([_button(label, f"altos:action:{view.state_version}:{action}")])
    elif view.step == 3:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:P34:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:P34:{view.state_version}:solo")],
                )
            )
    elif view.step == 4:
        rows.append([_button("Registrar evidências das Âncoras regionais", f"altos:action:{view.state_version}:observe_regional_anchor_evidence")])
    elif view.step == 5:
        rows.append([_button("Comparar os registros com Roven", f"altos:action:{view.state_version}:compare_eris_with_roven")])
    elif view.step == 6:
        rows.append([_button("Registrar no Códice e concluir com Eris e Sera", f"altos:action:{view.state_version}:record_anchor_codex_and_conclude")])
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_p35(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "available":
        rows.extend(
            (
                [_button("Iniciar P35 com Eris, Roven e Sera", "altos:action:0:activate_p35")],
                [_button("← Missões", "world:missions")],
            )
        )
        return Screen(
            f"📜 {title} · Disponível\nConfins do Véu · Nó Central\n\n"
            "P34 foi concluída. Nv.59 permite iniciar a reconstrução documental da Noite da Convergência.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "suspended":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Suspensa\n\nP35 requer P34 concluída e Nv.59. "
            "Seu acesso anterior permanece registrado; a missão poderá ser iniciada ao atingir o nível exigido.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "completed":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\n✨ 98.950 XP · 1.220 Coroas\n"
            "📦 2 Ferros de Baliza · 1 Musgo de Limiar · 1 Pó de Referência\n"
            "🏅 Feito · A Noite Reconstruída\n🖼️ Moldura · Arquivo Duplo\n\n"
            "O Regente Fraturado ainda não foi enfrentado; o protocolo permanece aberto.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    chain_labels = {
        "custodia_ancoras": "Custódia das Âncoras",
        "regencia_continuidade": "Regência de Continuidade",
        "oposicao_desvelados": "Oposição dos Desvelados",
    }
    sequence_labels = {
        "pre_civil_deterioration": "Deterioração do Véu anterior à civilização asteriana",
        "anchors_stabilized": "Funcionamento inicial e efeito estabilizador das Âncoras",
        "growing_dependency_inequality": "Dependência crescente e desigualdade da rede",
        "coupled_convergence": "Convergência como operação coordenada de Âncoras acopladas",
    }
    step_text = {
        1: "No Nó Central, reúna as três cadeias documentais independentes.",
        2: "Confira materialmente os quatro elementos da sequência técnica.",
        3: "Vença o Vigia Desfasado Nv.59 em encontro roteirizado, sem Variante ou economia própria.",
        4: "Reconstrua com Eris e Roven a sabotagem consciente da ala radical, preservando a distinção entre oposição legítima e culpa coletiva.",
        5: "Registre a decisão de Cael Rhen e os riscos documentados de prosseguir ou interromper.",
        6: "Registre separadamente Convergência — Reconstrução e Cadeia da Ruptura, preservando lacunas documentais.",
        7: "Abra a rota física para a Câmara da Regência. O acesso individual é válido desde Nv.59; não inicia P36.",
        8: "Retorne a Sera Nol no Nó Central e conclua o relato.",
    }.get(view.step, "Retome a etapa atual da missão.")
    lines = [
        f"📜 {title} · Em Andamento",
        "Confins do Véu · Nó Central",
        "",
        f"Etapa {view.step}/8 · {step_text}",
    ]
    progress = view.progress
    if progress.get("s35_contextual_knowledge_available"):
        lines.append(
            "Contexto já registrado: S35 preservou duas ordens oficiais incompatíveis. "
            "Isso não substitui as três cadeias documentais nem as evidências próprias de P35."
        )
    if view.step == 1:
        evidence = set(progress.get("documentary_chain_evidence_ids", ()))
        for key, label in chain_labels.items():
            if key not in evidence:
                rows.append([_button(label, f"altos:action:{view.state_version}:record_chain_{key}")])
        lines.append(f"Cadeias registradas · {len(evidence)}/3")
    elif view.step == 2:
        evidence = set(progress.get("technical_sequence_evidence_ids", ()))
        for key, label in sequence_labels.items():
            if key not in evidence:
                rows.append([_button(label, f"altos:action:{view.state_version}:verify_sequence_{key}")])
        lines.append(f"Elementos verificados · {len(evidence)}/4")
    elif view.step == 3:
        if progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:P35:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:P35:{view.state_version}:solo")],
                )
            )
    elif view.step == 4:
        rows.append([_button("Registrar a reconstrução documental", f"altos:action:{view.state_version}:reconstruct_desvelados_sabotage")])
    elif view.step == 5:
        rows.append([_button("Registrar a decisão de Cael Rhen", f"altos:action:{view.state_version}:record_cael_rhen_decision_context")])
    elif view.step == 6:
        rows.append([_button("Registrar as duas entradas de Códice", f"altos:action:{view.state_version}:record_convergence_codices")])
    elif view.step == 7:
        if not progress.get("chamber_route_opened"):
            rows.append([_button("Abrir rota à Câmara da Regência", f"altos:action:{view.state_version}:open_chamber_route")])
    elif view.step == 8:
        if view.location == CONFINS_NO_CENTRAL_LABEL:
            rows.append([_button("Seguir à Câmara da Regência", "road:route:confins_camara_regencia")])
            rows.append([_button("Concluir relato com Sera Nol", f"altos:action:{view.state_version}:conclude_with_sera")])
        elif view.location == CONFINS_CAMARA_REGENCIA_LABEL:
            rows.append([_button("Retornar ao Nó Central", "road:route:confins_no_central")])
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_p36(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "completed":
        selected = escape(str(view.progress.get("reward_item_id", "Lendário escolhido")))
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Primeira jornada concluída\n\n"
            "O protocolo impossível foi encerrado para você. O Véu não foi curado e o Avesso permanece.\n"
            "✨ 183.420 XP nominais · 2.000 Coroas\n"
            "📦 3 Ferros de Baliza · 1 Couro de Marcha · 1 Musgo de Limiar · 3 Pós de Referência\n"
            f"🎁 Equipamento Lendário escolhido: {selected}\n"
            "A campanha permanece no Nv.60; o Legado é uma ação separada.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.status != "active":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Aguardando elegibilidade\n\n"
            "P36 exige P35 concluída e Nv.60. A Câmara continua acessível conforme o direito já concedido.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    step_text = {
        1: "Na Câmara, examine o registro institucional, a matéria local e as marcas de estados incompatíveis.",
        2: "Registre três evidências físicas finais e as lacunas que impedem um relato contínuo dos últimos minutos.",
        3: "Inicie conscientemente o confronto com o Regente Fraturado.",
        4: "A vitória válida avança a missão; uma derrota permite recuperar-se no Braseiro da Testemunha e tentar novamente.",
        5: "O Núcleo do Regente Fraturado é individual e concedido somente na primeira vitória válida.",
        6: "Leia o registro pós-confronto: o Regente é uma manifestação composta, não Cael Rhen vivo ou ressuscitado.",
        7: "Registre separadamente as duas entradas de Códice e revele a Receita diretamente.",
        8: "Escolha explicitamente um Lendário Nv.60 e encerre a jornada com Sera Nol.",
    }.get(view.step, "Retome a etapa atual da missão.")
    lines = [
        f"📜 {title} · Em Andamento",
        "Confins do Véu · Câmara da Regência",
        "",
        f"Etapa {view.step}/8 · {step_text}",
    ]
    progress = view.progress
    if view.step == 1:
        evidence = set(progress.get("chamber_evidence_ids", ()))
        for key, label in (
            ("institutional_record", "Examinar o registro institucional"),
            ("local_matter", "Examinar a matéria local"),
            ("incompatible_states", "Examinar marcas de estados incompatíveis"),
        ):
            if key not in evidence:
                rows.append([_button(label, f"altos:action:{view.state_version}:record_chamber_{key}")])
        lines.append(f"Elementos examinados · {len(evidence)}/3")
    elif view.step == 2:
        evidence = set(progress.get("final_evidence_ids", ()))
        for key, label in (
            ("final_evidence_a", "Examinar evidência física I"),
            ("final_evidence_b", "Examinar evidência física II"),
            ("final_evidence_c", "Examinar evidência física III"),
        ):
            if key not in evidence:
                rows.append([_button(label, f"altos:action:{view.state_version}:record_final_evidence_{key}")])
        lines.append(f"Evidências distintas · {len(evidence)}/3")
    elif view.step == 3:
        rows.extend(
            (
                [_button("Iniciar confronto Solo", f"altos:combat:P36:{view.state_version}:solo")],
                [_button("Solicitar confronto em Grupo", f"altos:combat:P36:{view.state_version}:group")],
            )
        )
    elif view.step == 4:
        if progress.get("awaiting_retry"):
            if view.location != CONFINS_CAMARA_REGENCIA_LABEL:
                rows.append([_button("Retornar à Câmara da Regência", "road:route:confins_camara_regencia")])
            else:
                rows.append([_button("Tentar novamente", f"altos:retry:P36:{view.state_version}")])
    elif view.step == 6:
        rows.append([_button("Registrar a natureza delimitada do Regente", f"altos:action:{view.state_version}:record_regent_nature")])
    elif view.step == 7:
        rows.append([_button("Registrar Códices e revelar Eco do Encerramento", f"altos:action:{view.state_version}:record_regent_codices_and_recipe")])
    elif view.step == 8:
        selected = progress.get("reward_choice")
        if selected is None:
            for key, (_item_id, name, _slot) in P36_REWARD_OPTIONS.items():
                rows.append([_button(name, f"altos:choice:P36:{view.state_version}:{key}")])
        else:
            selected_name = P36_REWARD_OPTIONS.get(selected, (None, "Lendário escolhido", None))[1]
            lines.append(f"Escolha confirmada · {escape(selected_name)}")
            rows.append([_button("Concluir pessoalmente com Sera Nol", f"altos:action:{view.state_version}:conclude_with_sera")])
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_s26_combat_step(view: AltosMissionView, title: str, rows) -> Screen:
    location = escape(view.location)
    if view.step == 3:
        step_text = "Vença o Carneiro do Peso (Nv.44) em combate roteirizado."
        if view.progress.get("awaiting_retry"):
            rows.append(
                [_button("Tentar novamente", f"altos:retry:S26:{view.state_version}")]
            )
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:S26:{view.state_version}:solo")],
                )
            )
    else:
        step_text = "Combate resolvido. Retome Turno sem Fim para continuar."
        rows.append([_button("Retomar Turno sem Fim", "s26:resume")])
    rows.append([_button("← Missões", "world:missions")])
    text = (
        f"📜 {title} · Em Andamento\nAltos Cinéreos · {location}\n\n"
        f"Etapa {view.step}/6 · {step_text}\n\n"
        "Encontro de missão · sem Variante e sem settlement econômico próprio."
    )
    return Screen(text, "missions", InlineKeyboardMarkup(inline_keyboard=rows))


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
    local = (
        "Abrigo do Peso"
        if view.step == 1 and view.location == ALTOS_ABRIGO_LABEL
        else "Pontes de Fuligem"
        if view.step == 1 and view.location == ALTOS_PONTES_LABEL
        else "Pedreiras Suspensas"
    )
    lines = [f"📜 {title} · Em Andamento", f"Altos Cinéreos · {local}", "", step_text]
    if view.step == 1:
        if view.location == ALTOS_ABRIGO_LABEL:
            rows.append([_button("Seguir para Pontes de Fuligem", "road:route:altos_pontes")])
        elif view.location == ALTOS_PONTES_LABEL:
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


def _render_p30(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "suspended":
        return Screen(
            f"📜 {title} · Suspensa\n\nP29 deve estar concluída e o personagem precisa alcançar Nv. 50 para iniciar P30.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )
    if view.status == "available":
        rows.extend(
            (
                [_button("Iniciar P30 com Rava e Sel", "altos:action:0:activate_p30")],
                [_button("← Missões", "world:missions")],
            )
        )
        return Screen(
            f"📜 {title} · Disponível\nAltos Cinéreos · Coração do Colosso\n\nRava Kern e Sel Ardan preparam a entrada no confronto final da Região.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "completed":
        selected = escape(str(view.progress.get("reward_item_id", "Épico escolhido")))
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\nO Colosso está inativo para você.\n✨ 134.100 XP · 1.700 Coroas\n📦 5 Ferros de Contrapeso · 3 Cinzas de Basalto · 1 Núcleo do Colosso\n🎁 Épico escolhido: {selected}",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    step_text = {
        1: "Entre no Coração do Colosso.",
        2: "Examine os três caminhos físicos de distribuição de carga.",
        3: "Recupere o registro incompleto do acoplamento excepcional.",
        4: "Inicie e derrote o Colosso Cinéreo (Nv. 50).",
        7: "Examine o registro pós-combate sobre a sabotagem da Âncora Central pela ala radicalizada dos Desvelados.",
        8: "Registre no Códice a evidência delimitada sobre a sabotagem.",
        9: "Revele diretamente a receita Continuidade do Colosso.",
        10: "Escolha pessoalmente um Equipamento Épico Nv. 50.",
    }.get(view.step, "Retome a etapa atual da missão.")
    lines = [f"📜 {title} · Em Andamento", "Altos Cinéreos · Coração do Colosso", "", step_text]
    if view.step == 1:
        rows.append([_button("Seguir para o Coração do Colosso", "road:route:altos_coracao")])
    elif view.step == 2:
        examined = set(view.progress.get("load_paths", ()))
        for key, label in (
            ("contraforte", "Examinar caminho do contraforte"),
            ("cabo", "Examinar caminho do cabo"),
            ("escora", "Examinar caminho da escora"),
        ):
            if key not in examined:
                rows.append([_button(label, f"altos:action:{view.state_version}:inspect_load_path_{key}")])
    elif view.step == 3:
        rows.append([_button("Recuperar registro incompleto", f"altos:action:{view.state_version}:recover_exceptional_coupling_record")])
    elif view.step == 4:
        if view.progress.get("awaiting_retry") and view.location != "Coração do Colosso":
            next_route = {
                ALTOS_ESCARPA_LABEL: ("Seguir ao Abrigo do Peso", "altos_abrigo"),
                ALTOS_ABRIGO_LABEL: ("Seguir para Pontes de Fuligem", "altos_pontes"),
                ALTOS_PONTES_LABEL: ("Seguir para Pedreiras Suspensas", "altos_pedreiras"),
                ALTOS_PEDREIRAS_LABEL: ("Seguir para Bastilha de Carga", "altos_bastilha"),
                ALTOS_BASTILHA_LABEL: ("Retornar ao Coração", "altos_coracao"),
            }.get(view.location)
            if next_route is not None:
                label, route_key = next_route
                rows.append([_button(label, f"road:route:{route_key}")])
        elif view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:P30:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:P30:{view.state_version}:solo")],
                    [_button("Solicitar encontro em Grupo", f"altos:combat:P30:{view.state_version}:group")],
                )
            )
    elif view.step == 7:
        rows.append([_button("Examinar registro pós-combate", f"altos:action:{view.state_version}:inspect_postcombat_sabotage_record")])
    elif view.step == 8:
        rows.append([_button("Registrar evidência no Códice", f"altos:action:{view.state_version}:record_sabotage_codex")])
    elif view.step == 9:
        rows.append([_button("Revelar Continuidade do Colosso", f"altos:action:{view.state_version}:reveal_colossus_recipe")])
    elif view.step == 10:
        selected = view.progress.get("reward_choice")
        for key, (_item_id, name, _slot) in P30_REWARD_OPTIONS.items():
            if key != selected:
                rows.append([_button(name, f"altos:action:{view.state_version}:choose_p30_reward_{key}")])
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_p31(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "completed":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\n✨ 77.050 XP · 860 Coroas\n"
            "📦 1 Ferro de Baliza · 1 Musgo de Limiar\n"
            "🏅 Feito · Primeira Marcha · Título Testemunha de Rota",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    step_text = {
        1: "Atravesse a fronteira dos Confins e registre sua chegada à Marcha Nebulosa.",
        2: "Examine os dois marcos da estrada e compare suas posições sem decidir qual leitura é falsa.",
        3: "Descubra o Braseiro do Marco Duplo.",
        4: "Derrote um Cão de Névoa (Nv. 51) no encontro roteirizado.",
        5: "Siga até o Último Refúgio.",
        6: "Descubra o Braseiro da Testemunha com Haro Sen.",
        7: "Compare as duas leituras com Sera Nol e Roven Pell.",
        8: "Registre “Dois marcos honestos” no Códice e conclua com Sera Nol.",
    }.get(view.step, "Retome a etapa atual da missão.")
    location = "Último Refúgio" if view.step in {6, 7, 8} else "Marcha Nebulosa"
    lines = [f"📜 {title} · Em Andamento", f"Confins do Véu · {location}", "", f"Etapa {view.step}/8 · {step_text}"]
    if view.step == 2:
        evidence = set(view.progress.get("route_marker_evidence", ()))
        for action, label in (
            ("inspect_talen_marker", "Examinar marco indicado por Talen"),
            ("inspect_ground_marker", "Examinar o segundo marco da estrada"),
        ):
            if action not in evidence:
                rows.append([_button(label, f"altos:action:{view.state_version}:{action}")])
    elif view.step == 3:
        rows.append([_button("Descobrir Braseiro do Marco Duplo", f"altos:action:{view.state_version}:discover_marco_duplo")])
    elif view.step == 4:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:P31:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:P31:{view.state_version}:solo")],
                )
            )
    elif view.step == 5:
        rows.append([_button("Seguir para o Último Refúgio", "road:route:confins_ultimo_refugio")])
    elif view.step == 6:
        rows.append([_button("Descobrir Braseiro da Testemunha", f"altos:action:{view.state_version}:discover_testemunha")])
    elif view.step == 7:
        rows.append([_button("Comparar as duas leituras", f"altos:action:{view.state_version}:compare_dual_readings")])
    elif view.step == 8:
        rows.append([_button("Registrar no Códice e concluir com Sera", f"altos:action:{view.state_version}:record_p31_codex_and_conclude")])
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def _render_p32(view: AltosMissionView, title: str, rows) -> Screen:
    if view.status == "available":
        rows.append([_button("Receber os traçados de Sera", "altos:action:0:activate_p32")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Disponível\nConfins do Véu · Último Refúgio\n\n"
            "Sera Nol apresenta dois traçados do mesmo percurso; Talen Nyr ajuda a examiná-los.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "suspended":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Suspensa\n\nP32 requer P31 concluída e Nv.53. "
            "O progresso anterior permanece preservado.",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.status == "completed":
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {title} · Concluída\n\n✨ 82.250 XP · 900 Coroas\n"
            "📦 2 Ferros de Baliza · 1 Musgo de Limiar · 1 Pó de Referência\n"
            "🏅 Feito · O Nome da Fratura",
            "missions",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    step_text = {
        1: "Receba de Sera dois traçados de ida e volta do mesmo trajeto, sem eleger uma versão como correta.",
        2: "Siga até Estradas Ausentes para registrar a chegada.",
        3: "Verifique os três indícios físicos distintos nas Estradas Ausentes.",
        4: "Enfrente um Andarilho Repetido (Nv.53) em encontro roteirizado e registre que não é clone nem alma.",
        5: "Compare as evidências com Talen Nyr e Sera Nol; a Fratura é localizada, não um portal.",
        6: "Registre a definição no Códice e conclua P32.",
    }.get(view.step, "Retome a etapa atual da missão.")
    location = (
        "Último Refúgio"
        if view.step in {1, 2} and not view.progress.get("estradas_arrival_recorded")
        else "Estradas Ausentes"
    )
    lines = [
        f"📜 {title} · Em Andamento",
        f"Confins do Véu · {location}",
        "",
        f"Etapa {view.step}/6 · {step_text}",
    ]
    if view.step == 1:
        rows.append(
            [_button("Receber os dois traçados de Sera", f"altos:action:{view.state_version}:receive_p32_route_traces")]
        )
    elif view.step == 2:
        rows.append([_button("Seguir para Estradas Ausentes", "road:route:confins_estradas_ausentes")])
    elif view.step == 3:
        evidence = set(view.progress.get("physical_fracture_evidence", ()))
        for action, label in (
            ("inspect_finished_foundation", "Examinar a fundação terminada"),
            ("inspect_absent_map_marker", "Conferir o marco ausente no mapa"),
            ("inspect_discordant_return_record", "Verificar o registro de retorno discordante"),
        ):
            if action not in evidence:
                rows.append([_button(label, f"altos:action:{view.state_version}:{action}")])
    elif view.step == 4:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:P32:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:P32:{view.state_version}:solo")],
                )
            )
    elif view.step == 5:
        rows.append([_button("Comparar as evidências com Talen e Sera", f"altos:action:{view.state_version}:compare_fracture_evidence")])
    elif view.step == 6:
        rows.append([_button("Registrar no Códice e concluir", f"altos:action:{view.state_version}:record_fracture_codex_and_conclude")])
    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))


def render_altos_mission(view: AltosMissionView) -> Screen:
    """Mission screen with the art of its quest (see asset_catalog)."""
    return with_mission_art(_render_altos_mission(view), view.quest_id)

"""Narrative and combat screens for the final TDO campaign mission."""
# ruff: noqa: E501

from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p6 import P6_CHAMBER, P6_CHOICES, P6_TITLE, P6View
from asterion.application.prologue import CombatView
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, RUINS
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _b(text, data):
    return InlineKeyboardButton(text=text, callback_data=data)


def _kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _combat(view):
    if view.combat is None or view.activity_id is None or view.encounter_id is None:
        return Screen(f"📜 {P6_TITLE} · O encontro está sendo reconstruído.", "p6",
                      _kb([[_b("Atualizar", "p6:resume")]]))
    hud = render_combat(CombatView(
        view.activity_id, view.encounter_id, view.character_id, view.combat,
        "p6", view.xp, context="p6", consumable_options=view.consumable_options,
        consumable_screen=view.consumable_screen,
        selected_consumable_id=view.selected_consumable_id,
        selected_target_id=view.selected_target_id, selection_parent=view.selection_parent,
        consumable_notice=view.consumable_notice,
        consumable_quantities=view.consumable_quantities,
        consumable_budget_limit=view.consumable_budget_limit,
        ready_consumable_option=view.ready_consumable_option,
        combat_actor_key=view.combat_actor_key,
    ))
    enemy = view.combat.fighters.get("enemy")
    phase = (
        "III · O Último Posto"
        if enemy and enemy.hp <= enemy.stats.hp * Decimal("0.35")
        else "II · A Fratura"
        if enemy and enemy.hp < enemy.stats.hp * Decimal("0.70")
        else "I · A Sentinela"
    )
    return Screen(f"📜 {P6_TITLE} · Câmara do Poente\n⚔️ Fase {phase}\n🛡️ Vigia Partido · Nv.10\n" + hud.text,
                  "p6", hud.keyboard, parse_mode=hud.parse_mode)


def _guidance(view):
    text = {
        "talents": "🌿 Há Pontos de Talento disponíveis para distribuir.",
        "trial": "✨ A Provação de Classe está disponível no Círculo da Cinza.",
        "path": "🎭 Sua escolha de Caminho está pendente.",
    }.get(view.guidance if view.step == 1 else None)
    return f"\n\n{text}" if text else ""


def _route_refuge(view):
    destination = {P6_CHAMBER: ("Retornar às Ruínas", f"p6:{view.state_version}:return_ruins"),
                   RUINS: ("Retornar ao Bosque", "road:route:bosque"),
                   BOSQUE: ("Seguir para a Charneca", "road:route:charneca"),
                   CHARNECA: ("Retornar ao Refúgio", "road:route:refuge")}
    label, callback = destination.get(view.location, ("Abrir Mapa", "world:map"))
    return _b(label, callback)


def _route_ruins(view):
    destination = {REFUGE: ("Seguir para a Charneca", "road:route:charneca"),
                   CHARNECA: ("Seguir para o Bosque", "road:route:bosque"),
                   BOSQUE: ("Seguir para as Ruínas", "road:route:ruinas")}
    label, callback = destination.get(view.location, ("Abrir Mapa", "world:map"))
    return _b(label, callback)


def _guidance_screen(view):
    text, callback, label = {
        "talents": (
            "🌿 Há Pontos de Talento disponíveis. Distribua-os em Personagem → Talentos antes de prosseguir.",
            "character:talents",
            "Abrir Talentos",
        ),
        "trial": (
            "✨ A Provação de Classe está disponível no Círculo da Cinza. Conclua-a antes de prosseguir.",
            "character:path",
            "Abrir Provação",
        ),
        "path": (
            "🎭 Sua escolha de Caminho está pendente. Defina-a antes de prosseguir.",
            "character:path",
            "Abrir Caminho",
        ),
    }.get(view.guidance, ("", "character:path", "Abrir Personagem"))
    return Screen(
        f"📜 {P6_TITLE} · Em Andamento\n\n{text}",
        "p6",
        _kb([[_b(label, callback)], [_b("← Missões", "world:missions")]]),
    )


def render_p6(view: P6View) -> Screen:
    v, p = view.state_version, view.progress or {}
    if view.kind == "combat":
        return _combat(view)
    if view.guidance and view.status == "active" and view.step == 1:
        return _guidance_screen(view)
    if view.kind == "completed" or view.status == "completed":
        name = P6_CHOICES.get(p.get("reward_choice"), ("Equipamento Épico", ""))[0]
        return Screen(f"✅ {P6_TITLE} · Concluída\nMissão Principal · Terras do Ocaso\n\n"
                      "✨ XP · 14.220\n🪙 Coroas · 500\n📦 Ferro de Fuligem · 4 · Vinculado\n"
                      f"📦 Resíduo do Ocaso · 4 · Vinculado\n🎁 {name} · Épico Nv.10 · Vinculado\n"
                      "📖 Âncora do Poente · Descoberta\n📜 Eco do Vigia Partido · Receita Revelada",
                      "p6", _kb([[_b("← Refúgio", "road:local")]]))
    if view.kind == "unavailable":
        return Screen(f"📜 {P6_TITLE} · Indisponível\nA Campanha final requer P5 concluída e Nv.10.",
                      "p6", _kb([[_b("← Missões", "world:missions")]]))
    if view.kind == "travel_ruins":
        return Screen(f"📜 {P6_TITLE} · Em Andamento\n\n🎯 Cruzar a Porta do Poente nas Ruínas do Vigia.\n📍 {view.location}",
                      "p6", _kb([[_route_ruins(view)], [_b("← Missões", "world:missions")]]))
    if view.kind == "cross_door":
        return Screen(f"📜 {P6_TITLE} · Câmara do Poente\n\n🎯 Cruzar a Porta do Poente.\n\nA estrutura permanece protegida; ainda não há passagem de retorno por ela.",
                      "p6", _kb([[_b("Cruzar a Porta", f"p6:{v}:cross_door")], [_b("← Missões", "world:missions")]]))
    if view.kind == "enter_chamber":
        return Screen(f"🚪 Porta do Poente\n📜 {P6_TITLE}\n\n🎯 Entrar na Câmara do Poente.",
                      "p6", _kb([[_b("Entrar na Câmara", f"p6:{v}:enter_chamber")], [_b("← Missões", "world:missions")]]))
    if view.kind == "travel_chamber":
        return Screen(f"📜 {P6_TITLE} · Em Andamento\n\n🎯 Retornar à Câmara do Poente pelas rotas conhecidas.\n📍 {view.location}",
                      "p6", _kb([[_b("Abrir Mapa", "world:map")], [_b("← Missões", "world:missions")]]))
    if view.kind == "inspect_before":
        return Screen(f"📜 {P6_TITLE} · Câmara do Poente\n\n🎯 Examinar a estrutura central.\n\nOren Cal\n<i>“Se a leitura estiver correta, o nome é ‘Âncora’. Não sabemos o que ancorava. Não transforme um nome em resposta.”</i>{_guidance(view)}",
                      "p6", _kb([[_b("Examinar estrutura", f"p6:{v}:inspect_before")], [_b("← Missões", "world:missions")]]), parse_mode="HTML")
    if view.kind == "start_boss":
        return Screen(f"📜 {P6_TITLE} · Câmara do Poente\n\n🎯 Enfrentar Vigia Partido.\n\nO combate começará quando você estiver pronto.{_guidance(view)}",
                      "p6", _kb([[_b("Iniciar Solo", f"p6:{v}:start_boss")],
                                  [_b("Formar Grupo", f"p6:{v}:group")],
                                  [_b("Grupo", "group:root")], [_b("← Missões", "world:missions")]]))
    if view.kind in {"retry", "retry_chamber", "retry_travel"}:
        rows = [[_b("Tentar novamente", f"p6:{v}:retry")],
                [_b("Formar Grupo", f"p6:{v}:group")]] if view.kind == "retry" else [[_b("Retornar à Câmara", f"p6:{v}:enter_chamber")]] if view.kind == "retry_chamber" else [[_route_ruins(view)]]
        rows.append([_b("← Missões", "world:missions")])
        return Screen(f"❌ Vigia Partido · Tentativa encerrada\n✅ Etapas anteriores preservadas\n📍 Recuperação · {p.get('recovery_brazier') or 'Braseiro do Refúgio'}\n❤️ HP restaurado · Vigor preservado\n\nA nova tentativa mantém o mesmo chefe, Nv.10 e configuração regional.{_guidance(view)}",
                      "p6_recovery", _kb(rows))
    if view.kind == "inspect_after":
        return Screen(f"📜 {P6_TITLE} · Câmara do Poente\n\n🎯 Examinar novamente a estrutura após a queda do Vigia.\n💠 Núcleo do Vigia Partido · Vinculado{_guidance(view)}",
                      "p6", _kb([[_b("Examinar estrutura", f"p6:{v}:inspect_after")], [_b("← Missões", "world:missions")]]))
    if view.kind == "record_anchor":
        return Screen(f"📜 {P6_TITLE} · Câmara do Poente\n\n🎯 Registrar o nome Âncora do Poente e os fatos confirmados.\n\nO Vigia a protegia; outras estruturas chamadas Âncoras existiram. Sua função permanece desconhecida.{_guidance(view)}",
                      "p6", _kb([[_b("Registrar no Códice", f"p6:{v}:record_anchor")], [_b("← Missões", "world:missions")]]))
    if view.kind in {"return_ruins", "return_refuge"}:
        return Screen(f"📜 {P6_TITLE} · Em Andamento\n🎯 Retornar ao Refúgio do Ocaso para relatar à Alda Veyr e a Oren Cal.\n📍 {view.location}{_guidance(view)}",
                      "p6", _kb([[_route_refuge(view)], [_b("← Missões", "world:missions")]]))
    if view.kind == "reports":
        reports = set(p.get("reports", ()))
        rows = []
        if "alda" not in reports:
            rows.append([_b("Reportar a Alda Veyr", f"p6:{v}:report_alda")])
        if "oren" not in reports:
            rows.append([_b("Reportar a Oren Cal", f"p6:{v}:report_oren")])
        rows.append([_b("← Missões", "world:missions")])
        return Screen(f"📜 {P6_TITLE} · Relato final\nRefúgio do Ocaso\n\n🎯 Reportes · {len(reports)}/2{_guidance(view)}",
                      "p6", _kb(rows))
    if view.kind == "choose_reward":
        rows = [[_b(name, f"p6:{v}:choice:{key}")] for key, (name, _) in P6_CHOICES.items()]
        rows.append([_b("← Missões", "world:missions")])
        return Screen(f"📜 {P6_TITLE} · Escolha final\n\nEscolha um Equipamento Épico · Nv.10 · Vinculado.\nA escolha será única.",
                      "p6", _kb(rows))
    return Screen(f"📜 {P6_TITLE} · Em Andamento", "p6",
                  _kb([[_b("Atualizar", "p6:resume")], [_b("← Missões", "world:missions")]]))

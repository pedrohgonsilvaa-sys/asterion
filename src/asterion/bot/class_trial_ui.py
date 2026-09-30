from __future__ import annotations

from html import escape
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.class_trials import ClassTrialView
from asterion.application.prologue import CombatView
from asterion.bot.combat_ui import (
    ClassTrialActionCallback,
    class_trial_action_ids,
    class_trial_target_ids,
    render_combat,
)
from asterion.bot.creation_ui import COPY, Screen
from asterion.domain.combat import Combat

CLASS_LABELS = {
    "sentinela": "SENTINELA",
    "errante": "ERRANTE",
    "vigia": "VIGIA",
    "tecelao": "TECELÃO",
    "oraculo": "ORÁCULO",
    "luminar": "LUMINAR",
}
CLASS_STAGES = {
    "sentinela": (
        ("Suportar", "Enfrente o impacto no momento certo."),
        ("Abrir a Guarda", "Encontre a abertura do Eco Blindado."),
        ("Guardar e Revidar", "Combine defesa e resposta."),
    ),
    "errante": (
        ("Primeiro Corte", "Aplique pressão com precisão."),
        ("Passo entre Golpes", "Responda à ameaça anunciada."),
        ("A Brecha", "Aproveite a abertura do Eco."),
    ),
    "vigia": (
        ("Marcar", "Observe o alvo e prepare sua resposta."),
        ("Três Disparos", "Enfrente as camadas de proteção."),
        ("O Momento do Tiro", "Escolha o momento do disparo."),
    ),
    "tecelao": (
        ("Acender", "Apresente a Chama Tecida à sequência."),
        ("Romper", "Enfrente os Ecos menores em conjunto."),
        ("Entrelaçar", "Alterne suas Artes e a defesa."),
    ),
    "oraculo": (
        ("O Sinal", "Observe o efeito do sinal no confronto."),
        ("Antes do Golpe", "Antecipe a ameaça anunciada."),
        ("O Futuro Possível", "Decida quando agir e quando se preservar."),
    ),
    "luminar": (
        ("Sustentar", "Mantenha o Eco Aliado em segurança."),
        ("Julgar", "Contenha a recuperação do Eco."),
        ("Escolha de Prioridade", "Decida como responder à pressão."),
    ),
}
_ROMAN = {1: "I", 2: "II", 3: "III"}


class ClassTrialPageCallback(CallbackData, prefix="trial"):
    action: str
    version: str

    @classmethod
    def for_action(cls, action: str, version: int):
        return cls(action=action, version=_base36(version))

    @property
    def state_version(self) -> int:
        return _from_base36(self.version)

def _base36(value: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = digits[remainder] + result
    return result


def _from_base36(value: str) -> int:
    return int(value, 36)


def _class_icon(character_class: str) -> str:
    copy = COPY.get(f"class:{character_class}", "")
    return copy.split(" ", 1)[0] if copy else "🎭"


def _class_title(character_class: str) -> str:
    return CLASS_LABELS.get(character_class, "CLASSE")


def _stage(character_class: str, stage: int) -> tuple[str, str]:
    rows = CLASS_STAGES.get(character_class, ())
    if 1 <= stage <= len(rows):
        return rows[stage - 1]
    return "Etapa", "Observe o Eco e avance."


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _class_path_screen(view: ClassTrialView) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    lines = ["🎭 Caminho", ""]
    if view.kind == "completed" or view.status == "completed":
        lines.extend(
            [
                "✅ Provação · Concluída",
                "✨ Escolha de Caminho · Pendente",
                "",
                "ℹ️ A primeira Arte do Caminho será desbloqueada no Nv.12.",
            ]
        )
    elif view.kind == "active":
        stage = view.current_stage or 1
        lines.extend(
            [
                "🔄 Provação · Em Andamento",
                f"Etapa {_ROMAN.get(stage, stage)}/III",
            ]
        )
        rows.append(
            [
                _button(
                    "Retomar Provação",
                    ClassTrialPageCallback.for_action("resume", view.state_version).pack(),
                )
            ]
        )
    elif view.status == "ready":
        stage = view.current_stage or 1
        lines.extend(
            [
                "🔄 Provação · Em Andamento",
                f"Etapa {_ROMAN.get(stage, stage)}/III",
            ]
        )
        rows.append(
            [
                _button(
                    "Retomar Provação",
                    ClassTrialPageCallback.for_action("resume", view.state_version).pack(),
                )
            ]
        )
    elif view.kind == "available":
        lines.append("✨ Provação de Classe · Disponível")
        rows.append(
            [
                _button(
                    "Iniciar Provação",
                    ClassTrialPageCallback.for_action("begin", view.state_version).pack(),
                )
            ]
        )
    elif view.blocker == "level" or view.level < 10:
        lines.append("🔒 Provação de Classe · Nv.10")
    elif view.blocker == "location":
        lines.append("🔒 Provação de Classe")
        lines.append("A Provação aguarda no Refúgio do Ocaso.")
    elif view.blocker == "foreground":
        lines.append("🔒 Provação de Classe")
        lines.append("Conclua a atividade em andamento para acessar.")
    else:
        lines.append("🔒 Provação de Classe · Indisponível")

    rows.append([_button("← Personagem", "character:root")])
    return Screen("\n".join(lines), "class_trial", _keyboard(rows))


def _stage_screen(view: ClassTrialView) -> Screen:
    character_class = view.character_class
    stage = view.current_stage or 1
    roman = _ROMAN.get(stage, str(stage))
    name, objective = _stage(character_class, stage)
    icon = _class_icon(character_class)
    title = _class_title(character_class)
    rows: list[list[InlineKeyboardButton]] = []
    lines = ["⚔️ Provação de Classe", "", f"{icon} {title}"]

    if view.retry_available:
        lines.extend(
            [
                f"Etapa {roman}/III · {name}",
                "",
                "❌ Tentativa Encerrada",
                "✅ Etapas Anteriores · Preservadas",
                "✨ Nova Tentativa · Disponível",
            ]
        )
        rows.append(
            [
                _button(
                    "Tentar Novamente",
                    ClassTrialPageCallback.for_action("retry", view.state_version).pack(),
                )
            ]
        )
    elif view.completed_stages:
        previous = max(view.completed_stages)
        previous_name, _ = _stage(character_class, previous)
        lines.extend(
            [
                f"✅ Etapa {_ROMAN.get(previous, previous)}/III · {previous_name} · Concluída",
                f"✨ Próxima Etapa · {roman} · {name}",
                "",
                objective,
            ]
        )
        if view.context == "refuge":
            rows.append(
                [
                    _button(
                        "Retornar ao Círculo",
                        ClassTrialPageCallback.for_action("circle", view.state_version).pack(),
                    )
                ]
            )
        else:
            rows.append(
                [
                    _button(
                        "Iniciar Próxima Etapa",
                        ClassTrialPageCallback.for_action("start", view.state_version).pack(),
                    )
                ]
            )
    else:
        lines.extend([f"Etapa {roman}/III · {name}", "", objective])
        if view.context == "refuge":
            rows.append(
                [
                    _button(
                        "Retornar ao Círculo",
                        ClassTrialPageCallback.for_action("circle", view.state_version).pack(),
                    )
                ]
            )
        else:
            rows.append(
                [
                    _button(
                        "Iniciar Etapa",
                        ClassTrialPageCallback.for_action("start", view.state_version).pack(),
                    )
                ]
            )
    rows.append([_button("← Caminho", "character:path")])
    return Screen("\n".join(lines), "class_trial", _keyboard(rows))


def render_class_trial(view: ClassTrialView) -> Screen:
    if view.kind in {"ready", "between_attempts"}:
        return _stage_screen(view)
    return _class_path_screen(view)


def render_class_path(view: ClassTrialView) -> Screen:
    """Render the Character → Path overview, independently of the stage view."""
    return _class_path_screen(view)


def render_trial_combat(view: ClassTrialView, combat: Combat) -> Screen:
    stage = view.current_stage or 1
    caption = f"Etapa {_ROMAN.get(stage, stage)}/III"
    combat_view = CombatView(
        activity_id=view.attempt_id or UUID(int=0),
        encounter_id=view.encounter_id or UUID(int=0),
        character_id=view.character_id,
        combat=combat,
        stage="combat",
        xp=0,
        context="class_trial",
        trial_stage_caption=caption,
    )
    return render_combat(combat_view)


async def render_class_trial_view(service, actor: int, view: ClassTrialView) -> Screen:
    if view.kind == "active" and view.attempt_id is not None:
        combat = await service.combat(actor, view.attempt_id)
        if combat is not None:
            return render_trial_combat(view, combat)
    return render_class_trial(view)


def render_trial_targets(
    view: ClassTrialView, combat: Combat, action_index: int
) -> Screen:
    actions = class_trial_action_ids(combat)
    if not 0 <= action_index < len(actions):
        return render_trial_combat(view, combat)
    action_id = actions[action_index]
    targets = class_trial_target_ids(combat, action_id)
    rows: list[list[InlineKeyboardButton]] = []
    lines = ["🎯 Escolha o Alvo", ""]
    buttons = []
    for index, target_id in enumerate(targets):
        fighter = next(
            (item for item in combat.fighters.values() if item.id == target_id),
            None,
        )
        if fighter is None or fighter.hp <= 0:
            continue
        side = fighter.side or ("player" if fighter.id == "player" else "enemy")
        icon = "✨" if side == "player" else "🜂"
        lines.append(f"{len(buttons) + 1} {icon} {escape(fighter.name)}")
        buttons.append(
            _button(
                str(len(buttons) + 1),
                ClassTrialActionCallback.for_intent(
                    view.attempt_id,
                    combat.version,
                    action_index,
                    _base36(index),
                ).pack(),
            )
        )
    if not buttons:
        return render_trial_combat(view, combat)
    for index in range(0, len(buttons), 5):
        rows.append(buttons[index : index + 5])
    rows.append(
        [
            _button(
                "← Combate",
                ClassTrialActionCallback.for_intent(
                    view.attempt_id,
                    combat.version,
                    action_index,
                    "b",
                ).pack(),
            )
        ]
    )
    return Screen("\n".join(lines), "class_trial", _keyboard(rows))

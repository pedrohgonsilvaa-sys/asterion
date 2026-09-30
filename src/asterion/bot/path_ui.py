"""Player-facing Path selection and change screens."""

from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.class_trials import ClassTrialView
from asterion.application.path_selection import PathView
from asterion.bot.class_trial_ui import ClassTrialPageCallback
from asterion.bot.creation_ui import COPY, Screen
from asterion.domain.paths import PATH_DEFINITIONS, paths_for_class


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _base36(value: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = digits[remainder] + result
    return result


def _percent(value: Decimal) -> str:
    amount = value * 100
    number = format(amount.normalize(), "f")
    return f"{number if amount < 0 else '+' + number}%"


def _modifiers(path_id: str) -> str:
    definition = PATH_DEFINITIONS[path_id]
    return "\n".join(f"{label} {_percent(value)}" for label, value in definition.modifiers())


def _path_block(path_id: str) -> str:
    definition = PATH_DEFINITIONS[path_id]
    return (
        f"{definition.emoji} {definition.name}\n"
        f"{definition.specialty}\n\n"
        f"{_modifiers(path_id)}\n\n"
        f"✨ {definition.passive_name}\n{definition.passive_summary}"
    )


def render_path_root(view: PathView, trial: ClassTrialView | None) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    lines = ["🎭 Caminho", ""]
    if not view.trial_completed:
        if trial is not None and trial.kind == "available":
            lines.append("✨ Provação de Classe · Disponível")
            rows.append(
                [
                    _button(
                        "Iniciar Provação",
                        ClassTrialPageCallback.for_action("begin", trial.state_version).pack(),
                    )
                ]
            )
        elif trial is not None and trial.kind in {"active", "ready", "between_attempts"}:
            lines.extend(
                [
                    "🔄 Provação · Em Andamento",
                    f"Etapa {trial.current_stage or 1}/III",
                ]
            )
            rows.append(
                [
                    _button(
                        "Retomar Provação",
                        ClassTrialPageCallback.for_action("resume", trial.state_version).pack(),
                    )
                ]
            )
        elif view.level < 10 or (trial is not None and trial.blocker == "level"):
            lines.append("🔒 Provação de Classe · Nv.10")
        elif trial is not None and trial.blocker == "location":
            lines.extend(["🔒 Provação de Classe", "A Provação aguarda no Círculo da Cinza."])
        elif trial is not None and trial.blocker == "foreground":
            lines.extend(
                ["🔒 Provação de Classe", "Conclua a atividade em andamento para acessar."]
            )
        else:
            lines.append("🔒 Provação de Classe · Indisponível")
        rows.append([_button("← Personagem", "character:root")])
        return Screen("\n".join(lines), "character", _keyboard(rows))

    if view.selected_path is None:
        lines.extend(
            [
                "✅ Provação · Concluída",
                "✨ Escolha de Caminho · Pendente",
            ]
        )
        rows.extend(
            [
                [_button("Escolher Caminho", "path:choose")],
                [_button("← Personagem", "character:root")],
            ]
        )
        return Screen("\n".join(lines), "character", _keyboard(rows))

    selected = PATH_DEFINITIONS[view.selected_path]
    class_copy = COPY.get(f"class:{view.character_class}", view.character_class)
    class_icon = class_copy.split(" ", 1)[0] if class_copy else "🎭"
    lines.extend(
        [
            f"{class_icon} {view.character_name}",
            f"{view.character_class.title()} · {selected.name}",
            "",
            f"1 {selected.emoji} {selected.name} · Caminho Atual",
        ]
    )
    paths = paths_for_class(view.character_class)
    other = next(path_id for path_id in paths if path_id != view.selected_path)
    other_definition = PATH_DEFINITIONS[other]
    lines.append(f"2 {other_definition.emoji} {other_definition.name} · Outro Caminho")
    version = _base36(view.configuration_version)
    rows.append(
        [
            _button(
                "1",
                f"path:detail:{view.selected_path}:{version}",
            ),
            _button("2", f"path:detail:{other}:{version}"),
        ]
    )
    rows.append([_button("← Personagem", "character:root")])
    return Screen("\n".join(lines), "character", _keyboard(rows))


def render_path_choices(view: PathView) -> Screen:
    paths = paths_for_class(view.character_class)
    rows = [
        [
            _button(
                "1",
                f"path:preview:{paths[0]}:{_base36(view.configuration_version)}",
            ),
            _button(
                "2",
                f"path:preview:{paths[1]}:{_base36(view.configuration_version)}",
            ),
        ],
        [_button("← Caminho", "path:root")],
    ]
    lines = ["🎭 Escolha de Caminho", ""]
    for index, path_id in enumerate(paths, 1):
        definition = PATH_DEFINITIONS[path_id]
        lines.append(f"{index} {definition.emoji} {definition.name}")
    return Screen("\n".join(lines), "character", _keyboard(rows))


def render_path_preview(view: PathView, path_id: str) -> Screen:
    lines = [
        "🎭 Caminho · Prévia",
        "",
        _path_block(path_id),
        "",
        "ℹ️ A primeira Arte do Caminho será desbloqueada no Nv.12.",
    ]
    rows = [
        [
            _button(
                "Confirmar Caminho", f"path:confirm:{path_id}:{_base36(view.configuration_version)}"
            )
        ],
        [_button("← Escolha de Caminho", "path:choose")],
    ]
    return Screen("\n".join(lines), "character", _keyboard(rows))


def render_path_detail(view: PathView, path_id: str) -> Screen:
    lines = ["🎭 Caminho", "", _path_block(path_id)]
    rows: list[list[InlineKeyboardButton]] = []
    if path_id == view.selected_path:
        lines.extend(
            ["", "✅ Caminho Atual", "ℹ️ A primeira Arte do Caminho será desbloqueada no Nv.12."]
        )
    else:
        rows.append(
            [
                _button(
                    "Trocar Caminho", f"path:swap:{path_id}:{_base36(view.configuration_version)}"
                )
            ]
        )
    rows.append([_button("← Caminho", "path:root")])
    return Screen("\n".join(lines), "character", _keyboard(rows))


def render_path_exchange(
    view: PathView,
    path_id: str,
    incompatible_art_count: int,
) -> Screen:
    current = PATH_DEFINITIONS[view.selected_path or ""]
    target = PATH_DEFINITIONS[path_id]
    lines = [
        "🎭 Troca de Caminho",
        "",
        f"{current.name} → {target.name}",
        f"🪙 Custo · {view.switch_cost:,} Coroas".replace(",", "."),
    ]
    can_confirm = True
    if not view.safe_location:
        lines.append("🔒 Local · Local Inapropriado")
        can_confirm = False
    elif view.foreground:
        lines.append("🔒 Atividade · Encerre a atividade em andamento")
        can_confirm = False
    elif view.crowns < view.switch_cost:
        lines.append("🔒 Coroas · Insuficientes")
        can_confirm = False
    if incompatible_art_count:
        lines.append(
            f"🎴 {incompatible_art_count} Arte(s) incompatível(is) será(ão) desequipada(s)."
        )
    rows: list[list[InlineKeyboardButton]] = []
    if can_confirm:
        rows.append(
            [
                _button(
                    "Confirmar Troca",
                    f"path:swapconfirm:{path_id}:{_base36(view.configuration_version)}",
                )
            ]
        )
    rows.append([_button("← Caminho", "path:root")])
    return Screen("\n".join(lines), "character", _keyboard(rows))

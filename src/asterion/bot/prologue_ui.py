"""Telegram screens of the Prologue: road scenes, first combat, outcome and ending.

Every player-facing name comes from the persisted character; nothing here may
carry a fixed protagonist name.
"""

import re
from decimal import Decimal
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.bot.creation_ui import Screen
from asterion.domain.combat import turn_seconds_left
from asterion.domain.prologue import prologue_enemy_for_name
from asterion.domain.turn_clock import TURN_SECONDS, format_remaining

SCENE_PREFIX = "pl:"
COMBAT_ENTRY = "prologue:continue"
FLAME_CALLBACK = "pl:chama"
ENDING_CALLBACK = "menu:back"
BAR_SEGMENTS = 9
ENCOUNTER_LOCATION = "tdo.location.estrada_das_cinzas"
_CONTINUE = "🛤️ Continuar a caminhada"
PURSE_LINE = "🪙 18 Coroas"
RESIDUE_LINE = "💧 1 Resíduo do Ocaso"
VICTORY_REWARD_LINES = ("✨ +320 XP", "🪙 +3 Coroas")
PURSE_NODE = "destrocos"

# node -> (title, narration, objects shown inside the scene, buttons[(label, target)]).
# A target of COMBAT_ENTRY starts the first combat directly.
SCENES: dict[str, tuple[str, str, tuple[str, ...], tuple[tuple[str, str], ...]]] = {
    "cinzas": (
        "🔥 Cinzas na Estrada",
        "O mundo desperta sob um céu sem cor. Cinzas atravessam a estrada como neve morta, "
        "cobrindo pedras, árvores retorcidas e os restos de algo que um dia talvez tenha sido "
        "um caminho seguro. À frente, entre a névoa e o silêncio, marcas recentes cortam a "
        "fuligem e indicam a direção de sua primeira jornada.",
        (),
        (
            ("🦶 Seguir os rastros", "rastros"),
            ("🔎 Examinar a estrada", "destrocos"),
            ("👂 Ouvir o silêncio", "silencio"),
        ),
    ),
    "rastros": (
        "👣 Seguindo os Rastros",
        "As pegadas atravessam a estrada… duas marcas estreitas aparecem entre as pedras.\n\n"
        "As marcas ainda estão parcialmente visíveis na fuligem, indicando que alguma coisa "
        "passou por ali há pouco tempo.",
        (),
        ((_CONTINUE, COMBAT_ENTRY),),
    ),
    "destrocos": (
        "🔎 Entre os Destroços",
        "Uma carroça tombada permanece parcialmente coberta pela cinza. Entre a madeira "
        "quebrada, uma pequena bolsa ainda está presa sob uma das tábuas.",
        (PURSE_LINE, RESIDUE_LINE),
        ((_CONTINUE, COMBAT_ENTRY), ("🔎 Examinar os destroços", "queimada")),
    ),
    "silencio": (
        "👂 O Silêncio",
        "O vento desaparece por alguns instantes, deixando a estrada imóvel entre as pedras e "
        "os destroços. Não há passos, vozes ou madeira rangendo ao longe.\n\n"
        "Então, um ruído baixo surge em algum ponto adiante, abafado pela fuligem e difícil "
        "de localizar.",
        (),
        (("🐾 Seguir o som", "pedras"), (_CONTINUE, COMBAT_ENTRY)),
    ),
    "queimada": (
        "🔎 A Estrada Queimada",
        "Os destroços revelam apenas madeira quebrada, ferro retorcido e cinza acumulada. "
        "Não há nada mais escondido entre as peças queimadas, e a estrada continua adiante "
        "entre as ruínas, silenciosa como antes.",
        (),
        ((_CONTINUE, COMBAT_ENTRY),),
    ),
    "pedras": (
        "🐾 Entre as Pedras",
        "O som vem de mais perto. A fuligem se move entre as pedras quando um rosnado baixo "
        "rompe o silêncio da estrada.\n\n"
        "Por alguns instantes, não há nada à vista, mas o ruído continua próximo o bastante "
        "para deixar claro que alguma coisa está escondida adiante.",
        (),
        ((_CONTINUE, COMBAT_ENTRY),),
    ),
}
SCENE_IDS = frozenset(SCENES)


def _column(buttons: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """Always one button per row."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=c)] for t, c in buttons]
    )


def render_scene(node_id: str, *, show_objects: bool = False) -> Screen:
    """Objects are shown only when they were really credited by this very visit."""
    title, narration, objects, buttons = SCENES[node_id]
    parts = [f"<b>{title}</b>", f"<i>{narration}</i>"]
    if objects and show_objects:
        parts.insert(2, "\n".join(objects))
    keyboard = _column(
        [
            (label, target if target == COMBAT_ENTRY else f"{SCENE_PREFIX}{target}")
            for label, target in buttons
        ]
    )
    return Screen("\n\n".join(parts), "prologue", keyboard, "HTML")


def scene_id_from_callback(data: str) -> str | None:
    node = data.removeprefix(SCENE_PREFIX) if data.startswith(SCENE_PREFIX) else None
    return node if node in SCENE_IDS else None


def hp_bar9(current: Decimal, maximum: Decimal) -> str:
    filled = min(BAR_SEGMENTS, max(0, int(current * BAR_SEGMENTS / maximum))) if maximum else 0
    return "🟩" * filled + "⬜" * (BAR_SEGMENTS - filled)


def _hud(emoji: str, name: str, hp: Decimal, maximum: Decimal) -> list[str]:
    from asterion.bot.combat_ui import number

    return [
        f"{emoji} <b>{escape(name)}</b>",
        f"❤️ <code>{number(hp)} / {number(maximum)}</code>",
        hp_bar9(hp, maximum),
        "",
    ]


def turn_line(turn: int, seconds_left: float | None) -> str:
    """Global turn/timer line: both values monospaced."""
    shown = TURN_SECONDS if seconds_left is None else seconds_left
    return f"🌐 <code>Turno {turn}</code> · ⏱️ <code>{format_remaining(shown)}</code>"


def prologue_turn_line(turn: int, seconds_left: float | None) -> str:
    """Prólogo turn/timer line: the whole line monospaced."""
    shown = TURN_SECONDS if seconds_left is None else seconds_left
    return f"<code>🌐 Turno {turn} · ⏱️ {format_remaining(shown)}</code>"


def _art_name(name: str) -> str:
    return re.sub(r"^[^\w]+", "", name).strip()


def _history_lines(combat, player, enemy, enemy_emoji: str) -> list[str]:
    visible = [event for event in combat.events if not event.internal]
    if not visible:
        return []
    last_round = max(event.round for event in visible)
    lines: list[str] = []
    for event in visible:
        if event.round != last_round:
            continue
        if event.actor == "player":
            actor, target = player, enemy
            if event.action == "hold":
                lines.append(f"⏱️ {escape(actor.name)} perdeu o turno.")
                continue
            if event.action == "defend":
                lines.append(f"🛡️ {escape(actor.name)} usou Defender.")
                continue
            action = combat.player_actions.get(event.action)
            if event.dodged:
                lines.append(f"💨 {escape(target.name)} esquivou do ataque.")
            elif event.action == "attack" or action is None:
                lines.append(f"⚔️ {escape(actor.name)} causou {event.damage} de dano.")
            else:
                lines.append(
                    f"✨ {escape(actor.name)} usou {escape(_art_name(action.name))} "
                    f"e causou {event.damage} de dano."
                )
        else:
            if event.dodged:
                lines.append(f"💨 {escape(player.name)} esquivou do ataque.")
            else:
                lines.append(f"{enemy_emoji} {escape(enemy.name)} causou {event.damage} de dano.")
    return lines


def render_prologue_combat(view, keyboard: InlineKeyboardMarkup | None) -> Screen:
    """Title, both HUDs and the mechanical history; the keyboard comes from the engine."""
    combat = view.combat
    player = combat.fighters["player"]
    enemy = combat.fighters["enemy"]
    creature = prologue_enemy_for_name(enemy.name)
    turn = max(1, player.opportunity)
    return render_standard_hud(
        "⚔️ O Primeiro Confronto",
        creature.emoji,
        enemy,
        player,
        turn,
        turn_seconds_left(combat),
        _history_lines(combat, player, enemy, creature.emoji),
        f"<i>{creature.emoji} {escape(creature.opening)}</i>",
        keyboard,
    )


def render_standard_hud(
    title: str,
    enemy_emoji: str,
    enemy,
    player,
    turn: int,
    seconds_left: float | None,
    history: list[str],
    opening_line: str,
    keyboard: InlineKeyboardMarkup | None,
    image_key: str = "prologue",
) -> Screen:
    """The shared combat HUD: title, turn+timer, both cards, then the history.

    The history sits directly under its heading, with no blank line between them.
    """
    lines = [f"<b>{title}</b>", "", prologue_turn_line(turn, seconds_left), ""]
    lines += _hud(enemy_emoji, enemy.name, enemy.hp, enemy.stats.hp)
    lines += _hud("👤", player.name, player.hp, player.stats.hp)
    lines.append("<b>📜 Histórico:</b>")
    lines.extend(history or [opening_line])
    return Screen(chr(10).join(lines), image_key, keyboard, "HTML")


def render_prologue_outcome(view) -> Screen:
    name = escape(view.combat.fighters["player"].name)
    if view.combat.result == "victory":
        text = (
            "<b>🔥 O Caminho Está Livre</b>\n\n"
            "<i>O último golpe derruba a criatura. Por alguns instantes, só o vento volta a "
            "ocupar a estrada.\n\n"
            f"A experiência adquirida no confronto fortalece {name}, enquanto mais adiante "
            "uma pequena chama permanece acesa entre as ruínas.</i>\n\n"
            + "\n".join(VICTORY_REWARD_LINES)
        )
    else:
        text = (
            "<b>🩸 O Caminho Interrompido</b>\n\n"
            f"<i>As forças abandonam {name}, e a estrada desaparece por alguns instantes "
            "atrás da fuligem.\n\n"
            "Quando a visão retorna, uma pequena chama permanece acesa entre as ruínas, "
            "iluminando o caminho adiante.</i>"
        )
    return Screen(text, "prologue", _column([("🔥 Seguir até a chama", FLAME_CALLBACK)]), "HTML")


def render_brazier(name: str, hp: Decimal, max_hp: Decimal) -> Screen:
    """First brazier. Shows the HP the character arrives with; resting is what refills it."""
    safe = escape(name)
    lines = [
        "<b>🔥 Braseiro da Estrada</b>",
        "",
        "<i>O fogo permanece aceso entre as pedras. O calor atravessa o corpo de "
        f"{safe}, enquanto a estrada permanece à frente, pronta para ser seguida.</i>",
        "",
        *_hud("👤", name, hp, max_hp),
    ]
    return Screen(
        "\n".join(lines).rstrip(),
        "brazier_estrada",
        _column([("🔥 Descansar", "world:rest")]),
        "HTML",
    )


def render_prologue_ending(name: str) -> Screen:
    text = (
        "<b>🏠 O Refúgio do Ocaso</b>\n\n"
        "<i>As chamas diminuem lentamente enquanto a estrada continua entre ruínas e campos "
        "de cinza. O primeiro trecho da jornada ficou para trás, mas o caminho adiante "
        "permanece aberto, levando para além da estrada que "
        f"{escape(name)} acabou de atravessar.</i>"
    )
    return Screen(text, "brazier_estrada", _column([("🛤️ Continuar", ENDING_CALLBACK)]), "HTML")

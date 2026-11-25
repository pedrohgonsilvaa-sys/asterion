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
from asterion.domain.turn_clock import TURN_SECONDS, format_turn_seconds

SCENE_PREFIX = "pl:"
COMBAT_ENTRY = "prologue:continue"
FLAME_CALLBACK = "pl:chama"
ENDING_CALLBACK = "menu:back"
BAR_SEGMENTS = 10
ENCOUNTER_LOCATION = "tdo.location.estrada_das_cinzas"
ROAD_IMAGE_KEY = "local:Estrada das Cinzas"
_CONTINUE = "🛤️ Continuar a caminhada"
PURSE_LINE = "🪙 <code>18 Coroas</code>"
RESIDUE_LINE = "💧 <code>1 Resíduo do Ocaso</code>"
VICTORY_REWARD_LINES = ("✨ <code>320 XP</code>", "🪙 <code>3 Coroas</code>")
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
            ("🦶 Seguir", "rastros"),
            ("🔎 Examinar", "destrocos"),
            ("👂 Ouvir", "silencio"),
        ),
    ),
    "rastros": (
        "👣 Seguindo os Rastros",
        "As pegadas atravessam a estrada. Duas marcas estreitas aparecem entre as pedras.\n\n"
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
        ((_CONTINUE, COMBAT_ENTRY), ("🔎 Examinar", "queimada")),
    ),
    "silencio": (
        "👂 O Silêncio",
        "O vento desaparece por alguns instantes, deixando a estrada imóvel entre as pedras e "
        "os destroços. Não há passos, vozes ou madeira rangendo ao longe.\n\n"
        "Então, um ruído baixo surge em algum ponto adiante, abafado pela fuligem e difícil "
        "de localizar.",
        (),
        (("🐾 Seguir", "pedras"), (_CONTINUE, COMBAT_ENTRY)),
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
        parts.insert(2, "\n".join(("🎁 <b>Recompensas:</b>", *objects)))
    keyboard = _column(
        [
            (label, target if target == COMBAT_ENTRY else f"{SCENE_PREFIX}{target}")
            for label, target in buttons
        ]
    )
    # Bloco UI 1 §8 item 10: "Cinzas na Estrada" usa a arte da Estrada.
    image = ROAD_IMAGE_KEY if node_id == "cinzas" else "prologue"
    return Screen("\n\n".join(parts), image, keyboard, "HTML")


def scene_id_from_callback(data: str) -> str | None:
    node = data.removeprefix(SCENE_PREFIX) if data.startswith(SCENE_PREFIX) else None
    return node if node in SCENE_IDS else None


def hp_bar9(current: Decimal, maximum: Decimal) -> str:
    filled = min(BAR_SEGMENTS, max(0, int(current * BAR_SEGMENTS / maximum))) if maximum else 0
    return "🟩" * filled + "⬜" * (BAR_SEGMENTS - filled)


def class_emoji(character_class: str | None) -> str:
    from asterion.bot.world_ui import CLASS_EMOJI

    return CLASS_EMOJI.get(character_class or "", "👤")


def _hud(emoji: str, name: str, hp: Decimal, maximum: Decimal) -> list[str]:
    from asterion.bot.combat_ui import number

    return [
        f"{emoji} <b>{escape(name)}</b>",
        f"❤️ <code>{number(hp)} / {number(maximum)}</code>",
        hp_bar9(hp, maximum),
        "",
    ]


def turn_line(turn: int, seconds_left: float | None) -> str:
    """Global turn/timer line (Bloco UI 1 §7): ``🌐 Turno N · ⏱️ 10s``.

    The turn number stays visible next to the timer; the timer reads the engine's
    authoritative deadline and counts down 10s → 0s.
    """
    shown = TURN_SECONDS if seconds_left is None else seconds_left
    return f"🌐 <b>Turno {turn}</b> · ⏱️ <code>{format_turn_seconds(shown)}</code>"


prologue_turn_line = turn_line


def _art_name(name: str) -> str:
    return re.sub(r"^[^\w]+", "", name).strip()


def art_label(name: str, action_id: str = "") -> str:
    """Art button/history label: the Art's own emoji and name (Bloco UI 1 §7).

    The emoji comes from the Art's canonical name when it carries one, or from the
    first class Art of the same id; otherwise the generic ✨ of the Bloco UI 1 mold.
    """
    clean = _art_name(name)
    lead = name.strip()[: len(name.strip()) - len(clean)].strip() if clean else ""
    if lead and lead != "🎴":
        return f"{lead} {clean}"
    from asterion.domain.arts import FIRST_CLASS_ART_IDS
    from asterion.domain.prologue import FIRST_ARTS

    for character_class, art_id in FIRST_CLASS_ART_IDS.items():
        first_name = FIRST_ARTS[character_class][0]
        if action_id == art_id or _art_name(first_name) == clean:
            return f"{first_name.split(' ', 1)[0]} {clean}"
    return f"✨ {clean}"


def _damage(value) -> str:
    """Damage is the one value highlighted in the history (Bloco UI 1 §7)."""
    from asterion.bot.combat_ui import number

    return f"<b>{number(value)} de dano</b>"


def _history_lines(combat, player, enemy, enemy_emoji: str) -> list[str]:
    """Plain-text history of the last round, without the character's name."""
    visible = [event for event in combat.events if not event.internal]
    if not visible:
        return []
    last_round = max(event.round for event in visible)
    foe = f"o {escape(enemy.name)}"
    lines: list[str] = []
    for event in visible:
        if event.round != last_round:
            continue
        if event.actor == "player":
            if event.action == "hold":
                lines.append("⏱️ O turno terminou sem ação.")
                continue
            if event.action == "defend":
                lines.append("🛡️ Defender foi usado.")
                continue
            action = combat.player_actions.get(event.action)
            if event.dodged:
                lines.append(f"💨 {foe[0].upper()}{foe[1:]} esquiva do ataque.")
            elif event.action == "attack" or action is None:
                lines.append(f"⚔️ O golpe atinge {foe} e causa {_damage(event.damage)}.")
            else:
                lines.append(
                    f"{escape(art_label(action.name, event.action))} atinge {foe} "
                    f"e causa {_damage(event.damage)}."
                )
        else:
            if event.dodged:
                lines.append(f"💨 O ataque d{foe} é evitado.")
            else:
                lines.append(
                    f"{enemy_emoji} O {escape(enemy.name)} ataca e causa {_damage(event.damage)}."
                )
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
        f"{creature.emoji} {escape(creature.opening)}",
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
    lines += _hud(class_emoji(player.character_class), player.name, player.hp, player.stats.hp)
    lines.append("<b>📜 Histórico:</b>")
    lines.extend(history or [opening_line])
    return Screen(chr(10).join(lines), image_key, keyboard, "HTML")


def render_prologue_outcome(view) -> Screen:
    """Resultado do primeiro combate, sem o nome do personagem na narrativa."""
    if view.combat.result == "victory":
        text = (
            "<b>🏆 O Caminho Está Livre</b>\n\n"
            "<i>O último golpe derruba a criatura. Por alguns instantes, apenas o vento volta "
            "a ocupar a estrada.</i>\n\n"
            "<i>A experiência adquirida no confronto permanece registrada, junto das "
            "recompensas obtidas durante a caçada.</i>\n\n"
            + "\n".join(("🎁 <b>Recompensas:</b>", *VICTORY_REWARD_LINES))
        )
    else:
        text = (
            "<b>🩸 O Caminho Interrompido</b>\n\n"
            "<i>As forças se esgotam, e a estrada desaparece por alguns instantes atrás da "
            "fuligem.</i>\n\n"
            "<i>Quando a visão retorna, uma pequena chama permanece acesa entre as ruínas, "
            "iluminando o caminho adiante.</i>"
        )
    return Screen(text, "prologue", _column([("🔥 Seguir até a chama", FLAME_CALLBACK)]), "HTML")


def render_brazier(name: str, hp: Decimal, max_hp: Decimal) -> Screen:
    """First brazier. Shows the HP the character arrives with; resting is what refills it."""
    lines = [
        "<b>🔥 Braseiro da Estrada</b>",
        "",
        "<i>O fogo permanece aceso entre as pedras. O calor atravessa o corpo, enquanto "
        "a estrada permanece à frente, pronta para ser seguida.</i>",
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

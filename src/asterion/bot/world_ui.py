from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.contracts import is_enabled as contracts_enabled
from asterion.application.legacy import LegacyView
from asterion.application.world import WorldView
from asterion.bot.asset_catalog import location_key
from asterion.bot.creation_ui import Screen
from asterion.bot.flavor_ui import with_flavor
from asterion.bot.refuge_hud import RefugeHud
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.tdo_hub import REFUGE_LABEL

LORE = (
    "Sob céus cobertos de fuligem, as estradas de Asterion seguem marcadas por ruínas, "
    "brasas antigas e promessas que nunca repousam por completo. Mesmo nos caminhos "
    "mais silenciosos, cada passo ainda parece ecoar a memória de algo que o mundo "
    "não conseguiu esquecer."
)


def bar(current, maximum, fill: str) -> str:
    # Bloco UI 1 §1: barras com 10 segmentos.
    segments = 10
    n = min(segments, max(0, int(current * segments / maximum))) if maximum else 0
    if current > 0 and maximum:
        n = max(1, n)
    return fill * n + "⬜" * (segments - n)


def number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


CLASS_LABELS = {
    "sentinela": "Sentinela",
    "errante": "Errante",
    "vigia": "Vigia",
    "tecelao": "Tecelão",
    "oraculo": "Oráculo",
    "luminar": "Luminar",
}
PATH_LABELS = {path_id: definition.name for path_id, definition in PATH_DEFINITIONS.items()}
LEGACY_LABELS = {
    0: "Legado",
    1: "Legado I",
    2: "Legado II",
    3: "Legado III",
    4: "Legado IV",
    5: "Legado V",
}


def render_campaign(
    location: str | None = None, principal_quest_title: str | None = None
) -> Screen:
    location_icon = {
        "Estrada das Cinzas": "🔥",
        "Refúgio do Ocaso": "🏚️",
        "Charneca da Fuligem": "🌑",
        "Bosque Calcinado": "🌲",
        "Ruínas do Vigia": "🪨",
    }.get(location, "📍")
    current = (
        f"📍 Local Atual\n{location_icon} {escape(location)}\nTerras do Ocaso\n\n"
        if location
        else ""
    )
    principal_quest = (
        f"📜 Missão Principal\n{escape(principal_quest_title)} · Em Andamento\n\n"
        if principal_quest_title
        else ""
    )
    text = (
        "📖 Campanha\n\n"
        f"{current}"
        f"{principal_quest}"
        "Siga a história: veja o Local Atual, abra o Mapa ou as Missões."
    )
    keyboard = [
        [
            InlineKeyboardButton(text="Local Atual", callback_data="world:local"),
            InlineKeyboardButton(text="Mapa", callback_data="world:map"),
        ],
        [InlineKeyboardButton(text="Missões", callback_data="world:missions")],
        [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
    ]
    if contracts_enabled():
        keyboard.insert(
            -1, [InlineKeyboardButton(text="Quadro de Contratos", callback_data="ctr:root")]
        )
    return Screen(text, "adventure", InlineKeyboardMarkup(inline_keyboard=keyboard))


ADVENTURE_ENTRY = "adv:hub"


ADVENTURE_TEXT = (
    "As Terras do Ocaso guardam caminhos que você ainda não percorreu. À medida que avança, "
    "novas trilhas, lugares esquecidos e perigos ocultos podem surgir diante de você. Cada "
    "caminho leva a uma nova parte da jornada."
)


def render_adventure() -> Screen:
    """Submenu ⚔️ Aventura (fluxo de UI aprovado §1.5): Desbravar e Masmorras.
    Só navegação: abrir o submenu não move o personagem."""
    from asterion.bot.ui_format import back, blocks, button, keyboard, narrative

    return Screen(
        blocks("<b>⚔️ Aventura</b>", narrative(ADVENTURE_TEXT)),
        "adventure",
        keyboard(
            [button("⛰️ Desbravar", DESBRAVAR_ENTRY), button("🗝️ Masmorras", "dungeon:known")],
            back("menu:back"),
        ),
        "HTML",
    )


RACE_LABEL = {
    "remanescente": "Remanescente", "velado": "Velado", "cinereo": "Cinéreo",
    "hemario": "Hemário", "alvorano": "Alvorano",
}
CLASS_LABEL = {
    "sentinela": "Sentinela", "errante": "Errante", "vigia": "Vigia",
    "tecelao": "Tecelão", "oraculo": "Oráculo", "luminar": "Luminar",
}


def render_world(view: WorldView) -> Screen:
    if view.kind == "brazier":
        from asterion.bot.prologue_ui import render_brazier

        return render_brazier(view.name, view.hp, view.max_hp)
    class_label = CLASS_LABELS.get(view.character_class, view.character_class)
    path_label = PATH_LABELS.get(view.selected_path or "", "Caminho")
    legacy_label = LEGACY_LABELS.get(view.legacy_level, "Legado")
    title_label = view.selected_title or "Título"
    identity = (
        f"👤 {escape(view.name)} · {class_label} · {path_label}\n"
        f"🏛️ Nv. {view.level} · {legacy_label}\n"
        f"🔰 {title_label}"
    )
    stats = "\n".join(
        (
            f"❤️ HP · {view.hp}/{view.max_hp}\n{bar(view.hp, view.max_hp, '🟥')}",
            f"⚡ Vigor · {view.vigor}/{view.max_vigor}\n"
            f"{bar(view.vigor, view.max_vigor, '🟨')}",
            f"✨ XP · {number(view.xp)}/{number(view.xp_required)}\n"
            f"{bar(view.xp, view.xp_required, '🟦')}",
        )
    )
    text = "\n\n".join(
        (
            "🌘 Refúgio do Ocaso",
            identity,
            stats,
            "━━━━━━━━━━━━━━━━━━",
        )
    )
    action_labels = [
        ("🧭 Desbravar", "road:explore:start"),
        ("🗡️ Caçada", "road:hunt"),
        ("🗝️ Masmorra", "dungeon:known"),
        ("🗺️ Mapa", "world:map"),
        ("📜 Missões", "world:missions"),
        ("👤 Personagem", "character:root"),
        ("🏰 Guilda", "guild:root"),
        ("🏟️ Arena", "pvp:hub"),
        ("🏪 Mercado", "mkt:root"),
        ("🏆 Classificação", "pvp:rank"),
        ("📖 Códice", "knowledge:codex"),
        ("📅 Calendário", "calendar:root"),
        ("🎁 Benefícios", "bn:root"),
        ("🌐 Comunidade", "community:open"),
        ("⚙️ Configurações", "settings:root"),
    ]
    rows = [[InlineKeyboardButton(text="🎁 Resgatar Recompensa Diária", callback_data="bn:gift")]]
    rows.extend(
        [InlineKeyboardButton(text=a, callback_data=b) for a, b in action_labels[i : i + 2]]
        for i in range(0, len(action_labels), 2)
    )
    return Screen(text, "menu", InlineKeyboardMarkup(inline_keyboard=rows))


CLASS_EMOJI = {
    "sentinela": "🛡️",
    "errante": "🗡️",
    "vigia": "🏹",
    "tecelao": "🪄",
    "oraculo": "🔮",
    "luminar": "☀️",
}
REFUGE_TITLE = "🌘 Terras do Ocaso"
REFUGE_IMAGE_KEY = location_key(REFUGE_LABEL)
DAILY_GIFT_BUTTON = "✨ Resgatar Dádiva Diária"
DESBRAVAR_ENTRY = "tdo:explore"
# Menu Principal (decisão do autor 2026-11-26 §3): Dádiva Diária em largura total, depois
# duas colunas. ⚔️ Aventura substitui ⛰️ Desbravar e reúne Refúgio, Desbravar, Caçadas e
# Masmorras. A Forja fica dentro do Mercado.
REFUGE_MENU = (
    (("⚔️ Aventura", ADVENTURE_ENTRY), ("🗺️ Mapa", "world:map")),
    (("👤 Personagem", "character:root"), ("🏪 Mercado", "mkt:root")),
    (("🏟️ Arena", "pvp:hub"), ("🏰 Guilda", "guild:root")),
    (("🌌 Eventos", "wev:hub"), ("📖 Códice", "knowledge:codex")),
    (("🏆 Classificação", "rank:level"), ("🎁 Benefícios", "bn:root")),
    (("🌐 Comunidade", "community:open"), ("⚙️ Configurações", "settings:root")),
)

DESBRAVAR_TEXT = (
    "As Terras do Ocaso se estendem além das trilhas conhecidas. Estradas cobertas de "
    "cinza, campos de fuligem, bosques consumidos pelo fogo e antigas estruturas de pedra "
    "guardam caminhos que ainda não revelaram tudo o que escondem.\n\n"
    "Entre rotas conhecidas e passagens esquecidas, cada descoberta pode levar a um novo "
    "lugar, um encontro inesperado ou uma ameaça à espreita."
)
DESBRAVAR_LOCAL_PREFIX = "tdo:desb:"
# Botão, rótulo do Local e chave de callback, na ordem fechada pelo autor (UI aprovada §1.6).
DESBRAVAR_LOCALS = (
    ("🔥 Estrada", "Estrada das Cinzas", "road"),
    ("🌑 Charneca", "Charneca da Fuligem", "charneca"),
    ("🌲 Bosque", "Bosque Calcinado", "bosque"),
    ("🏚️ Ruínas", "Ruínas do Vigia", "ruinas"),
    ("🕯️ Câmara", "Câmara do Poente", "camara"),
)
DESBRAVAR_LOCAL_BY_KEY = {key: label for _button, label, key in DESBRAVAR_LOCALS}


def render_desbravar() -> Screen:
    """Menu ⛰️ Desbravar (UI aprovada §1.6): Refúgio e os cinco Locais da Região."""
    from asterion.bot.ui_format import back, blocks, button, keyboard, narrative

    locals_ = [
        button(text, f"{DESBRAVAR_LOCAL_PREFIX}{key}") for text, _label, key in DESBRAVAR_LOCALS
    ]
    return Screen(
        blocks(
            "<b>⛰️ Desbravar</b>",
            *(narrative(part) for part in DESBRAVAR_TEXT.split("\n\n")),
        ),
        REFUGE_IMAGE_KEY,
        keyboard(
            [button("🌒 Refúgio", "refuge:local"), locals_[0]],
            [locals_[1], locals_[2]],
            [locals_[3], locals_[4]],
            back(ADVENTURE_ENTRY),
        ),
        "HTML",
    )


def roman(value: int) -> str:
    from asterion.bot.ui_format import roman as _roman

    return _roman(value)


FLAGELO_FILL = "🟪"
# Decisão do autor 2026-11-26 §5.2: emoji exclusivo de cada Flagelo.
FLAGELO_EMOJI = {
    "varkhenn": "🔥",
    "nharvek": "🐍",
    "azharel": "🪬",
    "hemrath": "🩸",
    "korvann": "⚖️",
    "vaelith": "🌀",
}


def patron_line(active: bool, until=None, *, now=None) -> str | None:
    """``👑 **Patrono de Asterion** · `X Dias` `` (dias restantes); ``None`` sem Patrono.

    Decisão do autor 2026-11-27: sem Patrono ativo, a HUD não mostra linha nenhuma.
    """
    if not active:
        return None
    if until is None:
        return "👑 <b>Patrono de Asterion</b>"
    from datetime import UTC, datetime

    from asterion.bot.ui_format import mono

    seconds = (until - (now or datetime.now(UTC))).total_seconds()
    days = max(1, -(-int(seconds) // 86400))
    return f"👑 <b>Patrono de Asterion</b> · {mono(f'{days} Dias' if days != 1 else '1 Dia')}"


def flagelo_heading(region_id: str) -> str:
    from asterion.domain.flagelos import REGIONS_BY_ID

    region = REGIONS_BY_ID.get(region_id)
    if region is None:
        return "<b>Despertar</b>"
    flagelo = region.flagelo
    emoji = FLAGELO_EMOJI.get(flagelo.flagelo_id, "🩸")
    return f"{emoji} <b>Despertar de {escape(flagelo.short_name)}</b>"


def _flagelo_emoji(hud) -> str:
    from asterion.domain.flagelos import REGIONS_BY_ID

    region = REGIONS_BY_ID.get(hud.flagelo.bar.region_id) if hud.flagelo else None
    return FLAGELO_EMOJI.get(region.flagelo.flagelo_id, "🔥") if region else "🔥"


def awakening_bar(points: int, threshold: int) -> str:
    """Barra do Despertar: 🟥 enquanto progride; em 100%, toda 🟪 (decisão 2026-11-26)."""
    if threshold and points >= threshold:
        return FLAGELO_FILL * 10
    return bar(points, threshold, "🟥")


def refuge_hud_text(view: WorldView, hud: RefugeHud | None = None) -> str:
    """HUD do Refúgio do Ocaso (decisão fechada do autor) em HTML do Telegram.

    Ordem: título; identidade, Título, Patrono e Coroas; HP, Vigor e XP; Flagelo.
    Valores ``atual/máximo`` sem espaços ao redor da barra.
    """
    from asterion.bot.ui_format import HP_FILL, VIGOR_FILL, XP_FILL, identity, mono

    hud = hud or RefugeHud()
    header = [
        identity(
            emoji=CLASS_EMOJI.get(view.character_class, "👤"),
            name=view.name,
            level=view.level,
            legacy_level=view.legacy_level,
            guild_tag=hud.guild_tag,
            title=view.selected_title,
        ),
        patron_line(view.patron_active, view.patron_until),
        f"🪙 <b>Coroas</b> · {mono(number(view.crowns))}",
    ]
    header = [line for line in header if line]
    stats = [
        f"❤️ <b>Vida</b> · {mono(f'{number(int(view.hp))}/{number(int(view.max_hp))}')}",
        bar(view.hp, view.max_hp, HP_FILL),
        f"⚡ <b>Vigor</b> · {mono(f'{view.vigor}/{view.max_vigor}')}",
        bar(view.vigor, view.max_vigor, VIGOR_FILL),
        f"✨ <b>XP</b> · {mono(f'{number(view.xp)}/{number(view.xp_required)}')}",
        bar(view.xp, view.xp_required, XP_FILL),
    ]
    parts = [f"<b>{REFUGE_TITLE}</b>", "\n".join(header), "\n".join(stats)]
    if hud.flagelo is not None:
        # Decisão do autor 2026-11-26 §5.2: emoji exclusivo + "Despertar de <nome curto>";
        # a barra começa vermelha e fica toda roxa em 100%.
        flagelo_bar = hud.flagelo.bar
        parts.append(
            f"{flagelo_heading(flagelo_bar.region_id)}\n"
            f"{awakening_bar(flagelo_bar.points, flagelo_bar.threshold)} "
            f"{mono(f'{flagelo_bar.percent}%')}"
        )
    return "\n\n".join(parts)


FLAGELO_BUTTON = ("🔥 Despertar", "flg:hub")


def refuge_menu_keyboard(
    *, gift_available: bool, flagelo_awake: bool = False, flagelo_emoji: str = "🔥"
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if gift_available:
        rows.append([InlineKeyboardButton(text=DAILY_GIFT_BUTTON, callback_data="bn:gift")])
    if flagelo_awake:
        # Leva ao hub do evento (barras, status e acesso ao combate), sem navegação paralela.
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{flagelo_emoji} Despertar", callback_data=FLAGELO_BUTTON[1]
                )
            ]
        )
    rows.extend(
        [InlineKeyboardButton(text=label, callback_data=data) for label, data in pair]
        for pair in REFUGE_MENU
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def render_refuge_dashboard(
    view: WorldView,
    *,
    route_destinations: tuple[str, ...] = (),
    explore_remaining: int | None = None,
    can_hunt: bool = True,
    known_dungeons: bool = True,
    hud: RefugeHud | None = None,
) -> Screen:
    """Tela principal do Refúgio do Ocaso: HUD do personagem e Menu Principal.

    Os parâmetros de rotas, exploração, caçada e masmorra ficam por compatibilidade com
    os chamadores; o menu fixo não depende deles (cada destino trata a própria
    indisponibilidade). Alda Veyr, Oren Cal e o Treinador de Armas saíram desta tela, mas
    seus callbacks (``p2:alda``, ``world:oren``, ``wpt:root``) seguem nos handlers.
    """
    if view.kind == "brazier":
        # O primeiro Braseiro mantém a tela própria do Prólogo.
        return render_world(view)
    hud = hud or RefugeHud()
    return Screen(
        refuge_hud_text(view, hud),
        REFUGE_IMAGE_KEY,
        refuge_menu_keyboard(
            gift_available=hud.gift_available,
            flagelo_awake=hud.flagelo is not None and hud.flagelo.flagelo_awake,
            flagelo_emoji=_flagelo_emoji(hud),
        ),
        "HTML",
    )


def render_legacy(
    view: LegacyView,
    *,
    confirmation_key: str | None = None,
    succeeded: bool = False,
) -> Screen:
    ranks = {
        0: "Sem Legado",
        1: "Legado I",
        2: "Legado II",
        3: "Legado III",
        4: "Legado IV",
        5: "Legado V",
    }
    next_rank = ranks.get(view.legacy_level + 1, "")
    cost_text = (
        "gratuito"
        if view.ascension_cost == 0
        else f"{view.ascension_cost:,} Coroas".replace(",", ".")
    )
    reasons = {
        "level_required": "Alcance o Nv.60.",
        "crowns_required": f"Reúna {cost_text} para este Legado.",
        "safe_location_required": "Descanse num Braseiro permanente.",
        "activity_locked": "Encerre atividades e vínculos incompatíveis antes de ascender.",
        "legacy_max_reached": "Você já alcançou o Legado V, o máximo.",
    }
    text = (
        "🔱 Legado\n\n"
        f"{ranks.get(view.legacy_level, 'Legado desconhecido')} · Nv. {view.level}\n"
        f"Multiplicador de XP elegível: ×{view.xp_factor}\n"
    )
    if succeeded:
        text += (
            "\nAscensão concluída. Sua campanha e conquistas permanecem; sua progressão foi "
            "reiniciada no Nv.1. Equipamentos incompatíveis continuam no Inventário.\n"
            "Uma nova vaga de Marca de Legado foi liberada."
        )
    elif confirmation_key is not None:
        text += (
            f"\nConfirme a Ascensão para {next_rank} ({cost_text}). O personagem voltará ao "
            "Nv.1 e perderá qualquer XP restante no Nv.60. A campanha e os itens serão "
            "preservados; itens incompatíveis serão desequipados. Esta ação não pode ser "
            "desfeita."
        )
    elif view.can_ascend:
        text += (
            f"\nVocê atende aos requisitos para {next_rank} ({cost_text}) em um local seguro."
        )
    else:
        text += f"\nPara {next_rank or 'a próxima Ascensão'}:"
        text += "\n" + "\n".join(
            f"• {reasons.get(reason.value, 'Requisito ainda não atendido.')}"
            for reason in view.reasons
        )

    if confirmation_key is not None:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Confirmar Ascensão",
                        callback_data=f"legacy:confirm:{confirmation_key}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Cancelar", callback_data=f"legacy:cancel:{confirmation_key}"
                    )
                ],
                [InlineKeyboardButton(text="← Personagem", callback_data="character:root")],
            ]
        )
    else:
        rows = []
        if view.can_ascend:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Preparar Ascensão",
                        callback_data=f"legacy:prepare:{view.configuration_version}",
                    )
                ]
            )
        rows.append(
            [InlineKeyboardButton(text="🎗️ Marcas de Legado", callback_data="lmk:root")]
        )
        rows.append(
            [InlineKeyboardButton(text="← Personagem", callback_data="character:root")]
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    return with_flavor(Screen(text, "menu", keyboard), "legado")

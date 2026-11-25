"""Bloco UI 1 v1.1.0: HUD/Refúgio, Explorar, Caçadas, Masmorras, Missões e Prólogo."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from aiogram.types import InlineKeyboardButton

from asterion.application.road import REFUGE, RoadView
from asterion.application.tdo_explore import ExploreResult
from asterion.application.world import WorldView
from asterion.bot import missions_ui, refuge_ui
from asterion.bot.asset_catalog import location_key
from asterion.bot.creation_ui import COPY
from asterion.bot.prologue_ui import (
    VICTORY_REWARD_LINES,
    art_label,
    render_scene,
)
from asterion.bot.road_ui import render_hunt_entry, render_road
from asterion.bot.tdo_hub_ui import render_explore_entry, render_explore_result
from asterion.bot.ui_format import bar, reward_html, rewards
from asterion.bot.world_ui import render_refuge_dashboard


def _view(**overrides) -> WorldView:
    data = dict(
        kind="menu",
        character_id=uuid4(),
        name="Ornn",
        race="remanescente",
        character_class="vigia",
        hp=Decimal("631"),
        max_hp=Decimal("631"),
        vigor=100,
        max_vigor=100,
        xp=320,
        region="Terras do Ocaso",
        location=REFUGE,
        quest_title=None,
        xp_required=4800,
        crowns=1250,
    )
    data.update(overrides)
    return WorldView(**data)


def _labels(screen) -> list[list[str]]:
    return [[button.text for button in row] for row in screen.keyboard.inline_keyboard]


def _callbacks(screen) -> list[str]:
    return [button.callback_data for row in screen.keyboard.inline_keyboard for button in row]


# ---- §1 padrão global ----------------------------------------------------------------


def test_bars_have_ten_segments():
    assert bar(320, 4800, "🟦") == "🟦" + "⬜" * 9
    assert bar(631, 631, "🟥") == "🟥" * 10
    assert len(bar(0, 100, "🟨")) == 10


def test_rewards_block_has_no_blank_line_plus_or_multiplier():
    block = rewards(["✨ <code>320 XP</code>", "🪙 <code>3 Coroas</code>"])
    assert block == "🎁 <b>Recompensas:</b>\n✨ <code>320 XP</code>\n🪙 <code>3 Coroas</code>"
    assert reward_html("✨ XP · 1.234") == "✨ <code>1.234 XP</code>"
    assert reward_html("🪙 Coroas · 80") == "🪙 <code>80 Coroas</code>"
    assert reward_html("📦 Ferro de Fuligem · 3") == "📦 <code>3 Ferro de Fuligem</code>"
    for line in VICTORY_REWARD_LINES:
        assert "+" not in line and "x3" not in line.lower()


# ---- §2 HUD e Refúgio -----------------------------------------------------------------


def test_hud_layout_and_menu_order():
    screen = render_refuge_dashboard(_view(legacy_level=1))
    blocks = screen.text.split("\n\n")
    assert blocks[0] == "<b>🌘 Refúgio do Ocaso</b>"
    assert blocks[1] == "<b>🏹 Ornn · Vigia</b>\n<b>🏛️ Nv. 1 · Legado I</b>"
    assert blocks[2].splitlines() == [
        "❤️ <b>HP</b> · <code>631 / 631</code>",
        "🟥" * 10,
        "⚡ <b>Vigor</b> · <code>100 / 100</code>",
        "🟨" * 10,
        "✨ <b>XP</b> · <code>320 / 4.800</code>",
        "🟦" + "⬜" * 9,
    ]
    assert blocks[3] == "💰 <b>Coroas</b> · <code>1.250</code>"
    assert _labels(screen) == [
        ["🌘 Refúgio do Ocaso"],
        ["🧭 Explorar", "🐺 Caçadas"],
        ["🗝️ Masmorras", "📜 Missões"],
        ["🌌 Eventos", "👤 Personagem"],
        ["🗺️ Mapa", "🏰 Guilda"],
        ["🏪 Mercado", "🏟️ Arena"],
        ["📖 Códice", "🏆 Classificação"],
        ["🎁 Benefícios", "⚙️ Configurações"],
        ["🌐 Comunidade"],
    ]


def test_hud_daily_gift_is_full_width_first_row():
    from asterion.bot.refuge_hud import RefugeHud

    screen = render_refuge_dashboard(_view(), hud=RefugeHud(gift_available=True))
    assert _labels(screen)[0] == ["🎁 Resgatar Dádiva Diária"]
    assert _labels(screen)[1] == ["🌘 Refúgio do Ocaso"]


def test_refuge_local_uses_refuge_art_and_lists_services():
    screen = refuge_ui.render_refuge_local()
    assert screen.image_key == location_key(REFUGE)
    assert screen.image_key != refuge_ui.REFUGE_BRAZIER_ID
    assert _labels(screen) == [
        ["🔥 Braseiro do Refúgio"],
        ["⚔️ Darian Veyr"],
        ["🧭 Alda Veyr"],
        ["📜 Oren Cal"],
        ["↩️ Voltar"],
    ]
    assert "Dádiva" not in screen.text


def test_brazier_shows_only_hp_and_hides_recover_when_full():
    hurt = refuge_ui.render_refuge_brazier(
        "Ornn", Decimal(420), Decimal(631), emoji="🏹", guild_tag="CIN"
    )
    assert "<b>🏹 [CIN] Ornn</b>\n❤️ <b>HP</b> · <code>420 / 631</code>\n" in hurt.text
    assert "Vigor" not in hurt.text
    assert _labels(hurt) == [["🔥 Recuperar-se"], ["↩️ Voltar"]]
    full = refuge_ui.render_refuge_brazier("Ornn", Decimal(631), Decimal(631), emoji="🏹")
    assert _labels(full) == [["↩️ Voltar"]]
    recovered = refuge_ui.render_refuge_brazier(
        "Ornn", Decimal(631), Decimal(631), emoji="🏹", recovered=True
    )
    assert "o calor devolve suas forças" in recovered.text
    assert "Ornn" not in recovered.text.split("\n\n")[1]


def test_darian_and_npcs():
    darian = refuge_ui.render_darian(shields=True)
    assert _labels(darian) == [["⚔️ Armas"], ["🥋 Armaduras"], ["🛡️ Escudos"], ["↩️ Voltar"]]
    assert ["🛡️ Escudos"] not in _labels(refuge_ui.render_darian(shields=False))
    # Bloco UI 1 §2: só descrição + Voltar (sem Missões nem Conversar).
    for npc in (refuge_ui.render_alda(), refuge_ui.render_oren()):
        assert _labels(npc) == [["↩️ Voltar"]]
        assert _callbacks(npc) == ["refuge:local"]
    assert "📜 <b>Oren Cal</b>" in refuge_ui.render_oren().text


# ---- §3 Explorar ----------------------------------------------------------------------


def test_explore_entry_has_three_paths_status_without_name_and_back():
    screen = render_explore_entry(_view(xp=1240), remaining=2)
    assert "Ornn" not in screen.text and "Vigia" not in screen.text
    assert "✨ <code>1.240 / 4.800</code>\n" + "🟦" * 2 + "⬜" * 8 in screen.text
    assert _labels(screen) == [
        ["👣 Seguir pela estrada"],
        ["🌲 Seguir pela trilha"],
        ["🪨 Explorar os arredores"],
        ["↩️ Voltar"],
    ]
    assert set(_callbacks(screen)[:3]) == {"tdo:explore:go"}
    assert _callbacks(screen)[-1] == "menu:back"
    empty = render_explore_entry(_view(), remaining=0)
    assert "Não há mais o que explorar por aqui." in empty.text
    assert _labels(empty) == [["↩️ Voltar"]]


def test_explore_discovery_mold():
    screen = render_explore_result(
        ExploreResult("discovered", label="Charneca da Fuligem", xp=120)
    )
    assert screen.text.startswith("🌑 <b>Charneca da Fuligem</b>\n\n<i>Depois de atravessar")
    assert (
        "🎁 <b>Recompensas:</b>\n🗺️ <b>Descoberta da Charneca da Fuligem</b>\n"
        "✨ <code>120 XP</code>"
    ) in screen.text
    assert screen.image_key == location_key("Charneca da Fuligem")
    assert _labels(screen) == [["🧭 Continuar explorando"], ["↩️ Voltar ao Refúgio"]]


# ---- §4 Caçadas -----------------------------------------------------------------------


def test_hunt_entry_has_manual_and_round_without_choosing_a_place():
    screen = render_hunt_entry()
    assert _labels(screen) == [["🎯 Caçada Manual"], ["🔄 Ronda de Caça"], ["↩️ Voltar"]]
    assert _callbacks(screen) == ["tdo:hunt:manual", "tdo:hunt:round", "menu:back"]


def test_hunt_victory_and_defeat_molds():
    victory = render_road(
        RoadView(
            "hunt_victory",
            uuid4(),
            "Charneca da Fuligem",
            activity_id=uuid4(),
            reward_lines=("✨ <code>120 XP</code>", "🪙 <code>80 Coroas</code>"),
        )
    )
    assert victory.text.startswith("🏆 <b>Vitória</b>\n\n<i>")
    assert "🎁 <b>Recompensas:</b>\n✨ <code>120 XP</code>\n🪙 <code>80 Coroas</code>" in (
        victory.text
    )
    assert _labels(victory) == [["🎯 Caçar novamente"], ["↩️ Voltar"]]
    defeat = render_road(
        RoadView("hunt_defeat", uuid4(), REFUGE, recovery_location=REFUGE)
    )
    assert defeat.text.startswith("💀 <b>Derrota</b>")
    assert "Recompensas" not in defeat.text
    # A recuperação real (Braseiro + HP restaurado) continua visível.
    assert "🔥 <b>Braseiro da Estrada</b> · ❤️ HP restaurado" in defeat.text
    assert _labels(defeat) == [["🎯 Tentar novamente"], ["↩️ Voltar"]]


# ---- §6 Missões -----------------------------------------------------------------------


def test_missions_board_is_split_in_entry_main_and_side():
    principal = [InlineKeyboardButton(text="Principal", callback_data="world:principal")]
    side = [InlineKeyboardButton(text="1", callback_data="s1:detail")]
    text = (
        "📜 Missões\n\nAcompanhe sua Missão Principal e as Missões Secundárias conhecidas."
        "\n\n🔥 Missão Principal\n\n📜 Vozes na Estrada · Em Andamento\nTerras do Ocaso"
        "\n\n📖 Missões Secundárias\n\n1 🕯️ Luzes sob as Cinzas · Em Andamento"
        "\n\n✅ Pedras que Ainda Vigiam · Concluída"
    )
    main_text, main_rows = missions_ui.split_board(text, [principal, side], [side])
    assert "Luzes" not in main_text and "Pedras que Ainda Vigiam" in main_text
    main = missions_ui.render_main(main_text, main_rows)
    assert "<b>Em andamento</b>" in main.text
    assert _labels(main) == [["📖 Vozes na Estrada"], ["↩️ Voltar"]]
    side_screen = missions_ui.render_side(
        [
            ("🕯️ Luzes sob as Cinzas · Em Andamento", "s1:detail"),
            ("📖 Os Nomes Esquecidos · Disponível para reaceite", "s2:offer"),
            ("📜 Vigília sem Voz · Bloqueada · Requer P4", None),
        ]
    )
    assert "<b>Ativas</b>" in side_screen.text
    assert _labels(side_screen) == [
        ["📜 Luzes sob as Cinzas"],
        ["▶️ Os Nomes Esquecidos"],
        ["↩️ Voltar"],
    ]
    entry = missions_ui.render_entry(any_mission=True)
    assert _labels(entry) == [
        ["📖 Missões Principais"],
        ["🗺️ Missões Secundárias"],
        ["📜 Contratos"],
        ["↩️ Voltar"],
    ]
    assert "Ainda não há novas missões" in missions_ui.render_entry(any_mission=False).text


# ---- §7/§8 Combate e Prólogo ----------------------------------------------------------


def test_art_button_uses_the_real_art_emoji_and_name():
    assert art_label("🏹 Disparo Preciso", "art") == "🏹 Disparo Preciso"
    assert art_label("Golpe de Guarda", "class_art.sentinela.golpe_de_guarda") == (
        "🗡️ Golpe de Guarda"
    )
    assert art_label("Quebra-Postura", "class_art.sentinela.quebra_postura") == (
        "✨ Quebra-Postura"
    )


def test_prologue_specific_corrections():
    cinzas = render_scene("cinzas")
    assert cinzas.image_key == location_key("Estrada das Cinzas")
    assert [row[0].text for row in cinzas.keyboard.inline_keyboard] == [
        "🦶 Seguir",
        "🔎 Examinar",
        "👂 Ouvir",
    ]
    assert "…" not in render_scene("rastros").text
    purse = render_scene("destrocos", show_objects=True)
    assert "🎁 <b>Recompensas:</b>\n🪙 <code>18 Coroas</code>" in purse.text


def test_creation_review_and_class_texts_are_objective():
    for key in ("confirm", "class"):
        text = COPY[key]
        assert "Seu " not in text and "Sua " not in text and "seu " not in text


# ---- §2 Darian Veyr: treinamentos ---------------------------------------------------


def test_weapon_training_lists_class_families_and_family_shows_canonical_terms():
    from asterion.application.weapon_proficiency import TrainerEntry, TrainerView
    from asterion.bot.weapon_trainer_ui import render_weapon_family, render_weapon_trainer
    from asterion.domain.weapon_proficiency import ProficiencyFamily, acquisition_terms

    terms = acquisition_terms(2)
    view = TrainerView(
        "vigia",
        10,
        1500,
        True,
        terms,
        (
            TrainerEntry(ProficiencyFamily.BOWS, True),
            TrainerEntry(ProficiencyFamily.SWORDS, False),
            TrainerEntry(ProficiencyFamily.SHIELD, False),
        ),
    )
    root = render_weapon_trainer(view)
    assert _labels(root) == [["🏹 Arcos", "🗡️ Espadas"], ["↩️ Voltar"]]
    assert "Coroas" not in root.text
    family = render_weapon_family(view, ProficiencyFamily.SWORDS)
    assert f"⭐ <b>Nível</b> · <code>{terms.min_level}</code>" in family.text
    assert "💰 <b>Custo</b> · <code>" in family.text and "1.500" not in family.text
    assert _labels(family) == [["⚔️ Adquirir Proficiência"], ["↩️ Voltar"]]
    owned = render_weapon_family(view, ProficiencyFamily.BOWS)
    assert "📜 <b>Proficiência</b> · <code>Adquirida</code>" in owned.text
    assert _labels(owned) == [["↩️ Voltar"]]
    shield = render_weapon_family(view, ProficiencyFamily.SHIELD)
    assert shield.text.startswith("🛡️ <b>Treinamento de Escudos</b>")
    assert _labels(shield)[0] == ["🛡️ Adquirir Proficiência"]


def test_armor_training_uses_canonical_terms():
    from asterion.application.armor_proficiency import ArmorTrainerEntry, ArmorTrainerView
    from asterion.bot.armor_trainer_ui import render_armor_class, render_armor_trainer
    from asterion.domain.armor_proficiency import ARMOR_TERMS

    view = ArmorTrainerView(
        12,
        900,
        True,
        tuple(ArmorTrainerEntry(t, t.armor_class == "veste") for t in ARMOR_TERMS.values()),
    )
    assert _labels(render_armor_trainer(view)) == [
        ["👘 Vestes"], ["🥋 Leves"], ["🦺 Médias"], ["⛑️ Pesadas"], ["↩️ Voltar"]
    ]
    media = render_armor_class(view, "media")
    assert "⭐ <b>Nível</b> · <code>20</code>" in media.text
    assert "💰 <b>Custo</b> · <code>4.000 Coroas</code>" in media.text
    assert "Adquirida" in render_armor_class(view, "veste").text


# ---- §5 Masmorras -------------------------------------------------------------------


def test_dungeon_screens_follow_the_mold_with_canonical_values():
    from asterion.application.dungeons import DungeonView
    from asterion.bot.dungeon_ui import render_dungeon_difficulty, render_dungeons

    base = dict(
        character_id=uuid4(),
        character_name="Ornn",
        level=5,
        location="Charneca da Fuligem",
        hp=Decimal(631),
        max_hp=Decimal(631),
        vigor=100,
        max_vigor=100,
        family_id="dungeon.tdo.cripta_ocaso",
        dungeon_name="Cripta do Ocaso",
        minimum_level=4,
        difficulty_gates=(("stable", "available"), ("fractured", "first_stable")),
    )
    known = render_dungeons(
        DungeonView(
            "known",
            known_dungeons=(
                ("dungeon.tdo.cripta_ocaso", "Cripta do Ocaso", "Nv.4–7", "Charneca", "TDO"),
                ("dungeon.tdo.galerias_vigia", "Galerias do Vigia", "Nv.8–10", "Ruínas", "TDO"),
            ),
            **base,
        )
    )
    assert _labels(known) == [["🏚️ Cripta do Ocaso"], ["🏛️ Galerias do Vigia"], ["↩️ Voltar"]]
    detail_view = DungeonView("detail", **base)
    detail = render_dungeons(detail_view)
    assert _labels(detail) == [["🟢 Estável"], ["🟠 Fraturada"], ["🔴 Ruptura"], ["↩️ Voltar"]]
    assert "Estável" not in detail.text.split("\n")[0]
    stable = render_dungeon_difficulty(detail_view, "s")
    assert "⭐ <b>Nível</b> · <code>4</code>" in stable.text
    assert "⚔️ <b>Encontros</b> · <code>5</code>" in stable.text
    assert "⚡ <b>Vigor</b> · <code>25</code>" in stable.text
    assert _labels(stable)[0] == ["🗝️ Iniciar Masmorra"]
    assert "⚡ <b>Vigor</b> · <code>35</code>" in render_dungeon_difficulty(detail_view, "f").text
    assert _labels(render_dungeon_difficulty(detail_view, "f"))[0] == ["🔒 Concluir Estável"]
    assert "⚡ <b>Vigor</b> · <code>50</code>" in render_dungeon_difficulty(detail_view, "r").text
    done = render_dungeons(
        DungeonView("completed", reward_lines=("✨ XP · 1.200", "🪙 Coroas · 300"), **base)
    )
    assert "🎁 <b>Recompensas:</b>\n✨ <code>1.200 XP</code>\n🪙 <code>300 Coroas</code>" in (
        done.text
    )
    # Recompensas só na conclusão: nenhum encontro intermediário mostra recompensa.
    for ordinal in range(1, 6):
        ready = render_dungeons(
            DungeonView("ready", run_id=uuid4(), ordinal=ordinal, environment="x", **base)
        )
        assert "Recompensas" not in ready.text and "XP" not in ready.text
    failed = render_dungeons(DungeonView("failed", **base))
    assert failed.text.startswith("💀 <b>Masmorra Falhada</b>")
    assert "Tentar" not in str(_labels(failed))

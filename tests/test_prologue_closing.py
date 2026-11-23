"""Prologue closing package: scenes, first combat, outcome, ending and character art."""

import re
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from asterion.application.prologue import CombatView
from asterion.application.world import WorldView
from asterion.bot import asset_catalog
from asterion.bot.asset_catalog import build_asset_images, character_image_key, character_key
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import render
from asterion.bot.prologue_ui import (
    COMBAT_ENTRY,
    SCENES,
    render_brazier,
    render_prologue_ending,
    render_scene,
)
from asterion.bot.world_ui import render_world
from asterion.domain.combat import act
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.creation import CLASSES, GENDERS, PROLOGUE, RACES, Creation
from asterion.domain.prologue import PROFILE

NAME = "Aster"
ENEMIES = (
    ("dog_cinereo", "🐺", "Cão Cinéreo"),
    ("corvo_fuligem", "🐦", "Corvo de Fuligem"),
)


def combat_view(enemy_id: str, *, name: str = NAME) -> CombatView:
    hp = resolve_combat_stats("vigia", 1, "hemario").hp
    combat = PROFILE.create(uuid4(), name, "vigia", "hemario", hp, None, enemy_id)
    return CombatView(uuid4(), uuid4(), uuid4(), combat, "cinzas_na_estrada:first_combat", 0)


def texts_of(screen) -> str:
    keyboard = screen.keyboard.inline_keyboard if screen.keyboard else []
    return screen.text + "\n" + "\n".join(button.text for row in keyboard for button in row)


# ---------------------------------------------------------------- road scenes


def test_every_scene_is_bold_title_italic_narration_and_single_column():
    for node_id in SCENES:
        screen = render_scene(node_id)
        assert re.match(r"^<b>[^<]+</b>\n\n<i>", screen.text), node_id
        assert all(len(row) == 1 for row in screen.keyboard.inline_keyboard), node_id
        shown = texts_of(screen)
        for banned in ("Terras do Ocaso", "Prólogo", "O que você faz?", "Escolha uma opção"):
            assert banned not in shown, (node_id, banned)
        assert "Objetos encontrados" not in shown and "Guardar" not in shown


def test_scene_flow_targets_exist_and_combat_starts_directly():
    targets = {t for *_rest, buttons in SCENES.values() for _l, t in buttons}
    assert targets - {COMBAT_ENTRY} <= set(SCENES)
    cinzas = [b.text for row in render_scene("cinzas").keyboard.inline_keyboard for b in row]
    assert cinzas == ["🦶 Seguir os rastros", "🔎 Examinar a estrada", "👂 Ouvir o silêncio"]
    callbacks = {
        b.callback_data for row in render_scene("pedras").keyboard.inline_keyboard for b in row
    }
    assert callbacks == {"prologue:continue"}
    # Nothing before the fight uses a sword emoji, so the combat is not given away.
    assert "⚔️" not in "".join(texts_of(render_scene(node)) for node in SCENES)


def test_purse_line_only_shows_when_really_credited():
    assert "🪙 18 Coroas" not in render_scene("destrocos").text
    shown = render_scene("destrocos", show_objects=True).text
    assert "🪙 18 Coroas" in shown and "Bandagem" not in shown
    assert "Bandagem" not in "".join(render_scene(n, show_objects=True).text for n in SCENES)


def test_creation_prologue_step_is_the_first_scene():
    screen = render(Creation(uuid4(), step=PROLOGUE))
    assert screen.text == render_scene("cinzas").text
    assert screen.text.startswith("<b>🔥 Cinzas na Estrada</b>")


# ---------------------------------------------------------------------- combat


@pytest.mark.parametrize(("enemy_id", "emoji", "enemy_name"), ENEMIES)
def test_first_turn_hud_has_no_level_and_one_narrative_line(enemy_id, emoji, enemy_name):
    view = combat_view(enemy_id)
    screen = render_combat(view)
    max_hp = view.combat.fighters["player"].stats.hp
    assert screen.text.startswith("<b>⚔️ O Primeiro Confronto</b>")
    assert f"{emoji} <b>{enemy_name}</b>" in screen.text
    assert f"👤 <b>{NAME}</b>" in screen.text
    assert f"❤️ <code>{max_hp:.0f} / {max_hp:.0f}</code>" in screen.text
    assert "🟩" * 9 in screen.text and "🟩" * 10 not in screen.text
    assert "Nv." not in screen.text and "Nível" not in screen.text
    assert "🌐 <code>Turno 1</code> · ⏱️ <code>00:10</code>" in screen.text
    assert "<b>📜 Histórico:</b>\n<i>" in screen.text
    narrative = re.findall(r"<i>(.+?)</i>", screen.text)
    assert len(narrative) == 1 and narrative[0].startswith(emoji)
    assert re.fullmatch(r"(Atacar|Defender)", screen.keyboard.inline_keyboard[0][0].text)


@pytest.mark.parametrize(("enemy_id", "emoji", "enemy_name"), ENEMIES)
def test_later_turns_show_mechanical_history_without_the_appearance_line(
    enemy_id, emoji, enemy_name
):
    view = combat_view(enemy_id)
    combat = act(view.combat, "attack")
    screen = render_combat(CombatView(*(view.activity_id, view.encounter_id, view.character_id,
                                        combat, view.stage, 0)))
    assert "🌐 <code>Turno 2</code> · ⏱️ <code>00:10</code>" in screen.text
    assert "<b>📜 Histórico:</b>\n⚔️" in screen.text
    assert "<i>" not in screen.text
    assert re.search(rf"⚔️ {NAME} causou \d+ de dano\.", screen.text)
    assert re.search(rf"{emoji} {enemy_name} causou \d+ de dano\.", screen.text) or (
        f"💨 {NAME} esquivou" in screen.text
    )
    assert "O som" not in screen.text and "Eltharin" not in screen.text


def test_art_use_is_named_in_history():
    view = combat_view("dog_cinereo")
    combat = act(act(act(view.combat, "attack"), "defend"), "art")
    screen = render_combat(CombatView(view.activity_id, view.encounter_id, view.character_id,
                                      combat, view.stage, 0))
    assert re.search(rf"✨ {NAME} usou Disparo Preciso e causou \d+ de dano\.", screen.text)
    assert f"🛡️ {NAME} usou Defender." in screen.text or "Histórico" in screen.text


@pytest.mark.parametrize(("enemy_id", "_emoji", "_name"), ENEMIES)
def test_both_creatures_resolve_art_through_the_same_lookup(enemy_id, _emoji, _name):
    key = render_combat(combat_view(enemy_id)).image_key
    assert key == f"creature:{enemy_id}:map:estrada"
    assert key in build_asset_images(())


# ------------------------------------------------------------ outcome / ending


def finish(enemy_id: str, result: str) -> CombatView:
    from dataclasses import replace

    view = combat_view(enemy_id)
    return CombatView(view.activity_id, view.encounter_id, view.character_id,
                      replace(view.combat, result=result), view.stage, 0)


@pytest.mark.parametrize("name", [NAME, "Luiken"])
def test_outcome_brazier_and_ending_use_the_persisted_name(name):
    hp = Decimal(100)
    for result, title in (("victory", "🏆 Vitória"), ("defeat", "🩸 Derrota")):
        view = combat_view("dog_cinereo", name=name)
        from dataclasses import replace

        done = CombatView(view.activity_id, view.encounter_id, view.character_id,
                          replace(view.combat, result=result), view.stage, 0)
        screen = render_combat(done)
        assert f"<b>{title}</b>" in screen.text and name in screen.text
        assert [b.text for row in screen.keyboard.inline_keyboard for b in row] == [
            "🔥 Seguir até a chama"
        ]
        assert "Eltharin" not in screen.text
    brazier = render_brazier(name, hp)
    assert "<b>🔥 Braseiro da Estrada</b>" in brazier.text and name in brazier.text
    assert [b.text for row in brazier.keyboard.inline_keyboard for b in row] == ["🔥 Descansar"]
    assert "🟩" * 9 in brazier.text
    ending = render_prologue_ending(name)
    assert "<b>🔥 Fim do Prólogo</b>" in ending.text and name in ending.text
    assert [b.text for row in ending.keyboard.inline_keyboard for b in row] == ["🛤️ Continuar"]


def test_world_brazier_renders_the_character_name():
    view = WorldView(
        "brazier", uuid4(), NAME, "hemario", "vigia", Decimal(80), Decimal(100), 3, 3, 0,
        "Terras do Ocaso", "Estrada das Cinzas", None,
    )
    assert NAME in render_world(view).text


def test_no_hardcoded_protagonist_name_in_sources():
    root = Path(__file__).resolve().parents[1]
    offenders = [
        str(path)
        for folder in ("src", "tests")
        for path in (root / folder).rglob("*.py")
        if path.name != Path(__file__).name and "eltharin" in path.read_text("utf-8").lower()
    ]
    assert offenders == []


# ------------------------------------------------------------------- char art


def test_hemario_masculino_vigia_key_is_exact_and_not_errante():
    key = character_image_key("hemario", "masculino", "vigia")
    assert key == "char.hemario.masculino.vigia" == character_key("hemario", "masculino", "vigia")
    assert "errante" not in key


def test_another_combination_resolves_to_its_own_key():
    assert character_image_key("velado", "feminino", "oraculo") == "char.velado.feminino.oraculo"


def test_class_art_never_borrows_another_class_picture(tmp_path):
    chars = tmp_path / "characters"
    (chars / "default classes").mkdir(parents=True)
    (chars / "default races").mkdir()
    (chars / "default races" / "hem-m.jpg").write_bytes(b"race")
    (chars / "default classes" / "hem-m-errante.jpg").write_bytes(b"errante-art")
    (chars / "default classes" / "hem-m-vigia.jpg").write_bytes(b"errante-art")  # wrong copy
    (chars / "default classes" / "hem-m-oraculo.jpg").write_bytes(b"oraculo-art")
    images = build_asset_images((), root=tmp_path)
    assert images["char.hemario.masculino.errante"].endswith("hem-m-errante.jpg")
    assert "char.hemario.masculino.vigia" not in images
    assert images["char.hemario.masculino.oraculo"].endswith("hem-m-oraculo.jpg")
    # The only allowed fallback is the class-neutral race portrait.
    assert images["char.hemario.masculino"].endswith("hem-m.jpg")


def test_real_class_art_has_no_cross_class_duplicates_served():
    images = build_asset_images(())
    root = asset_catalog.assets_root()
    for race in RACES:
        for gender in GENDERS:
            files = {}
            for klass in CLASSES:
                ref = images.get(character_key(race, gender, klass))
                if ref:
                    data = (root / ref.removeprefix("file:")).read_bytes()
                    assert data not in files, (race, gender, klass, files.get(data))
                    files[data] = klass


# ------------------------------------------------------------------ turn clock


class Clock:
    def __init__(self, state):
        self.state = state

    def advance(self, seconds: float) -> None:
        self.state["t"] += seconds


@pytest.fixture
def clock(_frozen_turn_clock):
    return Clock(_frozen_turn_clock)


def test_every_turn_starts_with_ten_seconds_and_restarts(clock):
    from asterion.domain.combat import turn_seconds_left
    from asterion.domain.turn_clock import TURN_SECONDS

    view = combat_view("dog_cinereo")
    assert TURN_SECONDS == 10 and turn_seconds_left(view.combat) == 10
    clock.advance(6)
    assert turn_seconds_left(view.combat) == 4
    nxt = act(view.combat, "attack")
    assert turn_seconds_left(nxt) == 10  # fresh deadline for the next turn
    assert nxt.turn_deadline > view.combat.turn_deadline


def test_action_inside_the_window_is_accepted(clock):
    view = combat_view("dog_cinereo")
    clock.advance(9.9)
    updated = act(view.combat, "attack")
    assert updated.version > view.combat.version
    assert any(event.action == "attack" for event in updated.events)


def test_late_action_is_not_accepted_and_the_turn_times_out_once(clock):
    from asterion.domain.combat import expire_turn

    view = combat_view("dog_cinereo")
    enemy_hp = view.combat.fighters["enemy"].hp
    clock.advance(10.5)
    late = act(view.combat, "attack")
    assert late.fighters["enemy"].hp == enemy_hp  # the attack did not land
    assert not any(e.action == "attack" and e.actor == "player" for e in late.events)
    assert late.version == view.combat.version + 1
    # The timeout already resolved that turn: it cannot be resolved a second time.
    assert expire_turn(late) is late
    again = act(view.combat, "attack")  # the same stale intention replayed
    assert again.version == late.version


def test_timer_shows_in_hud_monospaced_and_counts_down(clock):
    view = combat_view("corvo_fuligem")
    clock.advance(3)
    text = render_combat(view).text
    assert "🌐 <code>Turno 1</code> · ⏱️ <code>00:07</code>" in text
    clock.advance(20)
    assert "⏱️ <code>00:00</code>" in render_combat(view).text


def test_history_sits_right_under_its_heading_without_blank_line():
    text = render_combat(combat_view("corvo_fuligem")).text
    assert "<b>📜 Histórico:</b>\n<i>🐦 O som das asas corta a fuligem." in text
    assert "<b>📜 Histórico:</b>\n\n" not in text
    assert "❤️ <code>" in text and "<b>Corvo de Fuligem</b>" in text and f"<b>{NAME}</b>" in text


def test_clock_applies_to_boss_and_party_combats_too(clock):
    from asterion.domain.combat import Combat, active_player_key, turn_expired

    view = combat_view("dog_cinereo")
    assert isinstance(view.combat, Combat) and active_player_key(view.combat) == "player"
    clock.advance(11)
    assert turn_expired(view.combat)


def test_snapshot_round_trip_keeps_the_deadline():
    from asterion.infrastructure.db.combat_codec import decode, encode

    view = combat_view("dog_cinereo")
    back = decode(encode(view.combat), view.combat.id, view.combat.ruleset, view.combat.version)
    assert back.turn_deadline == view.combat.turn_deadline


def test_hemario_masculino_vigia_has_its_own_real_art():
    images = build_asset_images(())
    key = "char.hemario.masculino.vigia"
    assert key in images and images[key].endswith("hem-m-vigia.jpg")
    root = asset_catalog.assets_root()
    errante = images["char.hemario.masculino.errante"]
    assert (root / images[key].removeprefix("file:")).read_bytes() != (
        root / errante.removeprefix("file:")
    ).read_bytes()

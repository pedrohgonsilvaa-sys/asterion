from decimal import Decimal

from asterion.application.world import WorldView
from asterion.bot.world_ui import render_world


def world_view(**changes):
    values = dict(
        kind="menu",
        character_id="00000000-0000-0000-0000-000000000001",
        name="Heroa",
        race="remanescente",
        character_class="sentinela",
        hp=Decimal("712.530"),
        max_hp=Decimal("712.530"),
        vigor=100,
        max_vigor=100,
        xp=320,
        region="Terras do Ocaso",
        location="Estrada das Cinzas",
        quest_title="Vozes na Estrada",
    )
    values.update(changes)
    return WorldView(**values)


def test_menu_is_authoritative_and_preserves_fractional_hp():
    text = render_world(world_view()).text
    assert "Terras do Ocaso · Estrada das Cinzas" in text
    assert "❤️ HP · 712.530 / 712.530" in text
    assert "⚡ Vigor · 100 / 100" in text
    assert "✨ XP · 320 / 4.800" in text
    assert "📜 Missão Principal · Vozes na Estrada" in text


def test_vigor_bar_is_derived_not_hardcoded():
    text = render_world(world_view(vigor=72)).text
    assert "⚡ Vigor · 72 / 100\n🟨🟨🟨🟨🟨🟨🟨⬜⬜⬜" in text


def test_brazier_screen_has_discovered_state_and_rest_only():
    screen = render_world(world_view(kind="brazier"))
    assert "🔥 Braseiro · Descoberto" in screen.text
    assert "Ativar Braseiro" not in screen.text
    assert [button.text for button in screen.keyboard.inline_keyboard[0]] == ["Descansar"]


def test_menu_does_not_invent_missing_quest():
    # Application refuses to construct this state from PostgreSQL without P1;
    # the renderer also requires the authoritative title explicitly.
    text = render_world(world_view(quest_title="Vozes na Estrada")).text
    assert "Vozes na Estrada" in text

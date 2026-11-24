"""HUD principal do Refúgio do Ocaso: cabeçalho, status, estado, botões e imagem."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.application.chronicle import ChronicleService
from asterion.application.engagement import DailyGiftService
from asterion.application.road import REFUGE
from asterion.application.world import WorldView
from asterion.bot.asset_catalog import build_asset_images, location_key
from asterion.bot.media import assets_root, resolve_asset_file
from asterion.bot.refuge_hud import RefugeHud, RefugeHudLoader
from asterion.bot.world_ui import render_refuge_dashboard, roman
from asterion.infrastructure.db.models import Account, Character

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
ACTOR = 920001


def _view(**overrides) -> WorldView:
    data = dict(
        kind="menu",
        character_id=uuid4(),
        name="Tess",
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
        crowns=1500,
    )
    data.update(overrides)
    return WorldView(**data)


def _screen(hud: RefugeHud | None = None, **overrides):
    return render_refuge_dashboard(_view(**overrides), hud=hud)


def _buttons(screen):
    return [b for row in screen.keyboard.inline_keyboard for b in row]


def test_header_with_path_legacy_and_title():
    text = _screen(
        selected_path="atirador", legacy_level=2, level=12, selected_title="Aliado do Refúgio"
    ).text
    lines = text.split("\n\n")
    assert lines[0] == "<b>🌘 Refúgio do Ocaso</b>"
    assert lines[1].split("\n") == [
        "<b>🏹 Tess</b> · Atirador",
        "🏛️ Nv. 12 · Legado II",
        "🎖️ <i>Aliado do Refúgio</i>",
    ]
    assert "Caminho" not in text


def test_path_absent_hides_path_and_never_writes_caminho():
    text = _screen(selected_path=None).text
    assert "<b>🏹 Tess</b> · Vigia" in text
    assert "Atirador" not in text and "Caminho" not in text


def test_legacy_absent_shows_only_level():
    text = _screen(legacy_level=0, level=7).text
    assert "🏛️ Nv. 7\n" in text + "\n"
    assert "Legado" not in text


@pytest.mark.parametrize(
    ("level", "expected"), [(1, "I"), (2, "II"), (3, "III"), (4, "IV"), (5, "V")]
)
def test_legacy_uses_roman_numerals(level, expected):
    assert roman(level) == expected
    assert f"Legado {expected}" in _screen(legacy_level=level).text


def test_equipped_title_appears_and_no_title_hides_line():
    assert "🎖️ <i>Guardião da Chama</i>" in _screen(selected_title="Guardião da Chama").text
    text = _screen(selected_title=None).text
    assert "🎖️" not in text and "Título" not in text


def test_title_is_html_escaped():
    assert "<i>A &lt;b&gt;</i>" in _screen(selected_title="A <b>").text


def test_status_block_is_compact_bold_and_monospaced():
    text = _screen().text
    assert "<b>❤️ HP</b> · <code>631 / 631</code>\n🟥" in text
    assert "<b>⚡ Vigor</b> · <code>100 / 100</code>\n🟨" in text
    assert "<b>✨ XP</b> · <code>320 / 4.800</code>\n🟦" in text
    assert "━" not in text
    assert "<b>💰 Coroas</b> · <code>1.500</code>" in text


def test_state_lines_use_real_data_and_boss_is_absent():
    text = _screen(RefugeHud(supporter="Ativo até 08/12", chronicle="Sem data ainda")).text
    assert "<b>⭐ Apoiador de Asterion</b> · Ativo até 08/12" in text
    assert "<b>📖 Crônica</b> · Sem data ainda" in text
    assert "👹" not in text


def test_removed_items_do_not_appear():
    screen = _screen(RefugeHud(gift_available=True, chronicle="Sem data ainda"))
    everything = screen.text + " ".join(b.text for b in _buttons(screen))
    for gone in (
        "Poç", "Energia", "Calendário", "Locais descobertos", "Estrada das Cinzas",
        "Alda Veyr", "Oren Cal", "Treinador de Armas", "Aventura", "Título", "━",
    ):
        assert gone not in everything
    callbacks = {b.callback_data for b in _buttons(screen)}
    assert not callbacks & {"calendar:root", "cr:root", "p2:alda", "world:oren", "wpt:root"}


def test_chronicle_is_in_hud_not_a_button():
    screen = _screen(RefugeHud(chronicle="Em andamento · termina em 10/12 às 06:00"))
    assert "📖 Crônica" in screen.text
    assert all("Crônica" not in b.text for b in _buttons(screen))


def test_menu_layout_two_columns_and_eventos_direct():
    screen = _screen()
    rows = [[b.text for b in row] for row in screen.keyboard.inline_keyboard]
    assert rows == [
        ["🧭 Explorar", "🌘 Refúgio"],
        ["🐺 Caçadas", "🗝️ Masmorras"],
        ["📜 Missões", "🌌 Eventos"],
        ["👤 Personagem", "🗺️ Mapa"],
        ["🏰 Guilda", "🏪 Mercado"],
        ["🏟️ Arena", "📖 Códice"],
        ["🏆 Classificação", "🌐 Comunidade"],
        ["🎁 Benefícios", "⚙️ Configurações"],
    ]
    pairs = {b.text: b.callback_data for b in _buttons(screen)}
    assert pairs["🌌 Eventos"] == "wev:hub"
    assert pairs["🌘 Refúgio"] == "menu:back"  # só navegação: não move o personagem


def test_daily_gift_button_only_when_available_and_alone_on_first_row():
    available = _screen(RefugeHud(gift_available=True))
    first = available.keyboard.inline_keyboard[0]
    assert [(b.text, b.callback_data) for b in first] == [("🎁 Resgatar Dádiva Diária", "bn:gift")]
    claimed = _screen(RefugeHud(gift_available=False))
    assert all("Dádiva" not in b.text for b in _buttons(claimed))


def test_refuge_image_key_exists_in_real_catalog():
    key = location_key(REFUGE)
    assert _screen().image_key == key
    if not (assets_root() / "maps" / "terras do ocaso").is_dir():
        pytest.skip("assets/ not present")
    images = build_asset_images((), assets_root())
    assert key in images
    assert resolve_asset_file(images[key], assets_root()).name.startswith("refugio.v")


def test_refuge_image_key_resolves_from_synthetic_assets(tmp_path):
    for n in (1, 2):
        path = tmp_path / f"maps/terras do ocaso/refugio.v0{n}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
    images = build_asset_images((), tmp_path)
    assert images[_screen().image_key] == "file:maps/terras do ocaso/refugio.v*.jpg"


def test_brazier_screen_is_preserved():
    screen = render_refuge_dashboard(_view(kind="brazier"))
    assert "🔥 Braseiro da Estrada" in screen.text


@pytest.mark.asyncio
async def test_daily_gift_cycle_hides_after_claim_and_returns_next_day(database):
    async with database[1].begin() as session:
        session.add(Account(telegram_id=ACTOR))
        session.add(
            Character(
                telegram_id=ACTOR,
                server_id="ocaso",
                name="Tess",
                race="remanescente",
                character_class="vigia",
                stage="menu",
                ruleset_version="tdo-1.0.15",
                hp=Decimal("100"),
                max_hp=Decimal("100"),
                created_at=NOW,
            )
        )
    gifts = DailyGiftService(database[1], "ocaso")
    loader = RefugeHudLoader(gifts, ChronicleService(database[1], "ocaso"), database[1])

    assert (await loader(ACTOR, now=NOW)).gift_available is True
    await gifts.claim(ACTOR, now=NOW)
    claimed = await loader(ACTOR, now=NOW)
    assert claimed.gift_available is False
    assert all("Dádiva" not in b.text for b in _buttons(_screen(claimed)))
    # Mesmo ciclo diário (antes das 06:00 seguintes): continua resgatada.
    assert (await loader(ACTOR, now=NOW + timedelta(hours=1))).gift_available is False
    # Novo ciclo diário: o botão volta sozinho.
    nxt = await loader(ACTOR, now=NOW + timedelta(days=1))
    assert nxt.gift_available is True
    assert any("Dádiva" in b.text for b in _buttons(_screen(nxt)))
    # Sem conta de Patrono nem Crônica agendada: textos reais, sem inventar estado.
    assert nxt.supporter == "Inativo"
    assert nxt.chronicle == "Sem data ainda"

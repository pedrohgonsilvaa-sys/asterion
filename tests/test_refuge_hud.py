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
        "<b>🏹 Tess · Vigia · Atirador</b>",
        "<b>🏛️ Nv. 12 · Legado II</b>",
        "🎖️ <i>Aliado do Refúgio</i>",
    ]
    assert "Caminho" not in text


def test_path_absent_hides_path_and_never_writes_caminho():
    text = _screen(selected_path=None).text
    assert "<b>🏹 Tess · Vigia</b>\n" in text
    assert "Atirador" not in text and "Caminho" not in text


def test_legacy_absent_shows_only_level():
    text = _screen(legacy_level=0, level=7).text
    assert "<b>🏛️ Nv. 7</b>\n" in text + "\n"
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
    # Bloco UI 1 §2: HP, Vigor e XP juntos, sem linha vazia entre eles.
    assert (
        "❤️ <b>HP</b> · <code>631 / 631</code>\n" + "🟥" * 10 + "\n"
        "⚡ <b>Vigor</b> · <code>100 / 100</code>\n" + "🟨" * 10 + "\n"
        "✨ <b>XP</b> · <code>320 / 4.800</code>\n🟦"
    ) in text
    assert "━" not in text
    assert "💰 <b>Coroas</b> · <code>1.500</code>" in text


def test_state_lines_use_real_data_and_boss_is_absent():
    text = _screen(RefugeHud(chronicle="Sem data ainda")).text
    assert "Apoiador" not in text and "Patrono" not in text and "⭐" not in text
    assert "📖 <b>Crônica</b> · Sem data ainda" in text
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
    assert "📖 <b>Crônica</b>" in screen.text
    assert all("Crônica" not in b.text for b in _buttons(screen))


def test_menu_layout_two_columns_and_eventos_direct():
    screen = _screen()
    rows = [[b.text for b in row] for row in screen.keyboard.inline_keyboard]
    assert rows == [
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
    pairs = {b.text: b.callback_data for b in _buttons(screen)}
    assert pairs["🌌 Eventos"] == "wev:hub"
    assert pairs["🌘 Refúgio do Ocaso"] == "refuge:local"  # só navegação: não move o personagem


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
    loader = RefugeHudLoader(gifts, ChronicleService(database[1], "ocaso"))

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
    # Sem Crônica agendada: texto já usado pelo Calendário.
    assert nxt.chronicle == "Sem data ainda"


@pytest.mark.asyncio
async def test_real_flow_open_gift_claim_and_return_to_refuge(database):
    """/menu → bn:gift → bn:gift:claim → menu:back: o botão some na hora."""
    from unittest.mock import AsyncMock

    from aiogram import Bot, Dispatcher
    from aiogram.methods import EditMessageText
    from aiogram.types import Chat, User
    from aiogram.types import Message as TelegramMessage

    from asterion.application.p1 import P1Service
    from asterion.application.promo_codes import PromoCodeService
    from asterion.application.recruitment import RecruitmentService
    from asterion.application.world import WorldService
    from asterion.bot.benefits_handlers import benefits_router
    from asterion.bot.world_handlers import world_router
    from tests.test_character_surfaces_telegram import _last_screen
    from tests.test_creation_ui import callback_update, message_update
    from tests.test_road_integration import _seed_road
    from tests.test_tdo_refuge_menu_principal import _set_state

    actor, road = await _seed_road(database, actor=920777)
    sessions = database[1]
    await _set_state(sessions, actor, region="Terras do Ocaso", location=REFUGE)
    loader = RefugeHudLoader(
        DailyGiftService(sessions, "ocaso"), ChronicleService(sessions, "ocaso")
    )
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        benefits_router(
            DailyGiftService(sessions, "ocaso"),
            RecruitmentService(sessions, "ocaso"),
            PromoCodeService(sessions, "ocaso"),
            {},
        )
    )
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"),
            {},
            p1=P1Service(sessions, "ocaso"),
            road=road,
            refuge_hud=loader,
        )
    )
    bot = Bot("123456:local-test-token")

    async def respond(_bot, method, **_kwargs):
        if isinstance(method, EditMessageText):
            return TelegramMessage(
                message_id=method.message_id,
                date=1,
                chat=Chat(id=actor, type="private"),
                from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                text=method.text,
            )
        return True

    bot.session.make_request = AsyncMock(side_effect=respond)

    def labels():
        return [b.text for row in _last_screen(bot).reply_markup.inline_keyboard for b in row]

    await dispatcher.feed_raw_update(bot, message_update("/menu", actor=actor))
    assert labels()[0] == "🎁 Resgatar Dádiva Diária"
    await dispatcher.feed_raw_update(bot, callback_update("bn:gift", update_id=3, actor=actor))
    assert "Resgatar" in labels()
    await dispatcher.feed_raw_update(
        bot, callback_update("bn:gift:claim", update_id=4, actor=actor)
    )
    assert "Resgatar" not in labels()
    await dispatcher.feed_raw_update(bot, callback_update("menu:back", update_id=5, actor=actor))
    assert "🌘 Refúgio do Ocaso" in _last_screen(bot).text
    assert "🎁 Resgatar Dádiva Diária" not in labels()
    assert labels()[0] == "🌘 Refúgio do Ocaso"
    await bot.session.close()

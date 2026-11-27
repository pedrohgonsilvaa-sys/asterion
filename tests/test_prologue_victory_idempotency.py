"""Prologue victory/defeat is resolved exactly once per attempt (bug of the 3 victories),
plus the approved UI flow and the per-state Prologue art."""

import asyncio
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import func, select

from asterion.application.creation import CreationService
from asterion.application.dungeons import DungeonView
from asterion.application.prologue import PrologueService
from asterion.application.world import WorldService
from asterion.bot.asset_catalog import build_asset_images, creature_image_key
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import CombatCallback, render_combat
from asterion.bot.creation_handlers import creation_router
from asterion.bot.dungeon_ui import render_dungeons
from asterion.bot.prologue_ui import (
    ENCOUNTER_LOCATION,
    SCENE_IDS,
    render_brazier,
    render_prologue_ending,
    render_scene,
)
from asterion.bot.world_ui import render_adventure, render_desbravar
from asterion.domain.prologue import POST_COMBAT_STAGE, PROFILE, REWARD_XP
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    Character,
    CombatRecord,
    GameActivity,
    RewardGrant,
)
from tests.test_creation_ui import callback_update, message_update
from tests.test_prologue_persistence import character, lose, prepare_defeat_snapshot


@pytest.fixture
def telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def prologue(database):
    return PrologueService(database[1], "ocaso", PROFILE)


async def prepare_victory_snapshot(database):
    """One hit from victory: the next player attack always lands and kills."""
    async with database[1].begin() as session:
        activity = await session.scalar(select(GameActivity))
        record = await session.scalar(select(CombatRecord))
        state = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        enemy = state.fighters["enemy"]
        enemy.hp = Decimal(1)
        enemy.stats = replace(enemy.stats, evasion=Decimal(0), block=Decimal(0))
        state.used_attack = state.used_defend = state.used_art = True
        state.order = ("player", "enemy")
        state.turn_index = 0
        state.pending_response = None
        state.result = None
        state.dot_states.clear()
        record.snapshot = encode(state)


def _texts(telegram) -> list[str]:
    out = []
    for call in telegram.session.make_request.call_args_list:
        method = call.args[1]
        text = getattr(method, "text", None) or getattr(method, "caption", None)
        if text:
            out.append(text)
    return out


async def _counts(database):
    async with database[1]() as session:
        stored = await session.scalar(select(Character))
        return {
            "xp": stored.xp,
            "crowns": stored.crowns,
            "stage": stored.stage,
            "grants": await session.scalar(select(func.count()).select_from(RewardGrant)),
            "braziers": await session.scalar(select(func.count()).select_from(Brazier)),
            "feats": await session.scalar(
                select(func.count())
                .select_from(Achievement)
                .where(Achievement.achievement_id == "feat.tdo.cinzas_na_estrada")
            ),
            "activities": await session.scalar(select(func.count()).select_from(GameActivity)),
        }


# ------------------------------------------------------------------ service level


async def test_victory_is_resolved_once_and_every_repeat_is_a_safe_noop(prologue, database):
    await character(database)
    initial = await prologue.enter(1)
    await prepare_victory_snapshot(database)
    won = await prologue.action(1, initial.activity_id, initial.combat.version, "attack")
    assert won.combat.result == "victory" and won.resolved_now is True
    assert won.stage == POST_COMBAT_STAGE
    before = await _counts(database)
    assert before["xp"] == REWARD_XP and before["grants"] == 1 and before["feats"] == 1

    repeats = [
        # Same callback again, old version, current version, forged action, enter, resume.
        await prologue.action(1, won.activity_id, initial.combat.version, "attack"),
        await prologue.action(1, won.activity_id, won.combat.version - 1, "attack"),
        await prologue.action(1, won.activity_id, won.combat.version, "attack"),
        await prologue.action(1, won.activity_id, won.combat.version, "defend"),
        await prologue.enter(1),
        await prologue.resume(1),
    ]
    for view in repeats:
        assert view == won and view.resolved_now is False
        assert view.combat.version == won.combat.version
    assert await _counts(database) == before


async def test_two_fast_clicks_on_the_killing_blow_produce_one_conclusion(prologue, database):
    await character(database)
    initial = await prologue.enter(1)
    await prepare_victory_snapshot(database)
    services = [PrologueService(database[1], "ocaso", PROFILE) for _ in range(6)]
    views = await asyncio.gather(
        *(
            s.action(1, initial.activity_id, initial.combat.version, "attack")
            for s in services
        )
    )
    assert sum(1 for view in views if view.resolved_now) == 1
    assert all(view.combat.result == "victory" for view in views)
    counts = await _counts(database)
    assert counts["xp"] == REWARD_XP and counts["grants"] == 1
    assert counts["braziers"] == 1 and counts["feats"] == 1 and counts["activities"] == 1


async def test_reconnect_start_and_menu_after_victory_do_not_reopen_or_reprocess(
    prologue, database
):
    await character(database)
    initial = await prologue.enter(1)
    await prepare_victory_snapshot(database)
    await prologue.action(1, initial.activity_id, initial.combat.version, "attack")
    before = await _counts(database)
    for _ in range(3):
        # New process / other device: fresh services reading persisted state.
        fresh = PrologueService(database[1], "ocaso", PROFILE)
        view = await fresh.resume(1)
        assert view.resolved_now is False and view.combat.result == "victory"
        world = await WorldService(database[1], "ocaso").resume(1)
        # The final state points to the Braseiro da Estrada.
        assert world.kind == "brazier"
    assert await _counts(database) == before
    async with database[1]() as session:
        assert (await session.scalar(select(GameActivity))).status == "completed"
        assert (await session.scalar(select(Character))).stage == POST_COMBAT_STAGE


async def test_defeat_is_resolved_once_and_never_becomes_a_second_resolution(
    prologue, database
):
    await character(database)
    initial = await prologue.enter(1)
    defeated = await lose(prologue, initial, database)
    assert defeated.combat.result == "defeat" and defeated.resolved_now is True
    before = await _counts(database)
    assert before["xp"] == 0 and before["grants"] == 0
    # Even if the stored snapshot were rewound to a winnable state, the closed attempt
    # (activity completed) refuses any further action.
    await prepare_victory_snapshot(database)
    again = await prologue.action(1, initial.activity_id, defeated.combat.version, "attack")
    assert again.resolved_now is False
    assert await _counts(database) == before


async def test_resolved_combat_does_not_accept_old_combat_actions(prologue, database):
    await character(database)
    initial = await prologue.enter(1)
    await prepare_defeat_snapshot(prologue, initial, database)
    defeated = await prologue.action(1, initial.activity_id, initial.combat.version, "attack")
    for version in (initial.combat.version, defeated.combat.version):
        for action in ("attack", "defend", "art", "hold"):
            view = await prologue.action(1, initial.activity_id, version, action)
            assert view.combat == defeated.combat and view.resolved_now is False


# ------------------------------------------------------------------ handler level


async def test_dispatcher_shows_one_victory_screen_for_repeated_callbacks(database, telegram):
    await character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    initial = await service.enter(1)
    await prepare_victory_snapshot(database)
    dispatcher = Dispatcher(disable_fsm=True)
    world = WorldService(database[1], "ocaso")
    dispatcher.include_router(combat_router(service, {}, world))
    dispatcher.include_router(
        creation_router(CreationService(database[1], "ocaso"), {}, service, world)
    )
    callback = CombatCallback(
        activity=initial.activity_id.hex, version=initial.combat.version, action="attack"
    ).pack()
    # Double click, then a stale tap, then an old-version tap, then a stale "Avançar".
    for index in range(4):
        await dispatcher.feed_raw_update(
            telegram, callback_update(callback, update_id=10 + index, actor=1)
        )
    await dispatcher.feed_raw_update(
        telegram, callback_update("prologue:continue", update_id=20, actor=1)
    )
    victory = [text for text in _texts(telegram) if "Caminho Aberto" in text]
    assert len(victory) == 1
    assert "320 XP" in victory[0] and "3 Coroas" in victory[0]
    counts = await _counts(database)
    assert counts["xp"] == REWARD_XP and counts["grants"] == 1 and counts["braziers"] == 1


async def test_flame_button_leads_to_the_braseiro_and_start_does_not_replay_victory(
    database, telegram
):
    await character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    initial = await service.enter(1)
    await prepare_victory_snapshot(database)
    dispatcher = Dispatcher(disable_fsm=True)
    world = WorldService(database[1], "ocaso")
    dispatcher.include_router(combat_router(service, {}, world))
    dispatcher.include_router(
        creation_router(CreationService(database[1], "ocaso"), {}, service, world)
    )
    callback = CombatCallback(
        activity=initial.activity_id.hex, version=initial.combat.version, action="attack"
    ).pack()
    await dispatcher.feed_raw_update(telegram, callback_update(callback, update_id=1, actor=1))
    await dispatcher.feed_raw_update(telegram, callback_update("pl:chama", update_id=2, actor=1))
    assert "Braseiro da Estrada" in _texts(telegram)[-1]
    before = await _counts(database)
    await dispatcher.feed_raw_update(telegram, message_update("/start", update_id=3, actor=1))
    await dispatcher.feed_raw_update(telegram, message_update("/menu", update_id=4, actor=1))
    assert not any("Caminho Aberto" in text for text in _texts(telegram)[2:])
    assert await _counts(database) == before


# ------------------------------------------------------------------ approved UI copy


def test_victory_screen_matches_the_approved_copy():
    from tests.test_prologue_closing import combat_view

    view = combat_view("dog_cinereo")
    done = replace(view, combat=replace(view.combat, result="victory"))
    screen = render_combat(done)
    assert screen.text == (
        "<b>🏆 Caminho Aberto</b>\n\n"
        "<i>Você desfere o último golpe e a criatura cai. Por alguns instantes, apenas o vento "
        "volta a ocupar a estrada.</i>\n\n"
        "<i>O confronto chega ao fim. À sua frente, a estrada permanece aberta, coberta de "
        "cinzas e silêncio.</i>\n\n"
        "🎁 <b>Recompensas:</b>\n✨ <code>320 XP</code>\n🪙 <code>3 Coroas</code>"
    )
    assert [b.text for row in screen.keyboard.inline_keyboard for b in row] == ["🔥 Continuar"]


def test_aventura_screen_has_only_desbravar_masmorras_and_retornar():
    screen = render_adventure()
    assert screen.text.startswith("<b>⚔️ Aventura</b>\n\n<i>As Terras do Ocaso guardam")
    rows = [[b.text for b in row] for row in screen.keyboard.inline_keyboard]
    assert rows == [["⛰️ Desbravar", "🗝️ Masmorras"], ["↩️ Retornar"]]


def test_desbravar_screen_has_the_approved_two_paragraphs_and_buttons():
    screen = render_desbravar()
    head, first, second = screen.text.split("\n\n")
    assert head == "<b>⛰️ Desbravar</b>"
    assert first.startswith("<i>As Terras do Ocaso se estendem") and first.endswith("</i>")
    assert second.startswith("<i>Entre rotas conhecidas") and second.endswith("</i>")
    rows = [[b.text for b in row] for row in screen.keyboard.inline_keyboard]
    assert rows == [
        ["🌒 Refúgio", "🔥 Estrada"],
        ["🌑 Charneca", "🌲 Bosque"],
        ["🏚️ Ruínas", "🕯️ Câmara"],
        ["↩️ Retornar"],
    ]


def _dungeon_view(kind, family="dungeon.tdo.cripta_ocaso", name="Cripta do Ocaso", **extra):
    return DungeonView(
        kind=kind,
        character_id=uuid4(),
        character_name="Testador",
        level=5,
        location="Refúgio do Ocaso",
        hp=Decimal(100),
        max_hp=Decimal(100),
        vigor=100,
        max_vigor=100,
        family_id=family,
        dungeon_name=name,
        **extra,
    )


def test_masmorras_selection_uses_short_names_and_opens_full_name_screens():
    known = _dungeon_view(
        "known",
        known_dungeons=(
            ("dungeon.tdo.cripta_ocaso", "Cripta do Ocaso", "", "", ""),
            ("dungeon.tdo.galerias_vigia", "Galerias do Vigia", "", "", ""),
        ),
    )
    screen = render_dungeons(known)
    assert screen.text.startswith("🗝️ <b>Masmorras</b>\n\n<i>Alguns caminhos não terminam")
    rows = [[(b.text, b.callback_data) for b in row] for row in screen.keyboard.inline_keyboard]
    assert rows == [
        [("🏚️ Cripta", "dungeon:crypt"), ("🏛️ Galerias", "dungeon:galleries")],
        [("↩️ Retornar", "adv:hub")],
    ]
    assert "Alcázar" not in screen.text

    for family, name, emoji in (
        ("dungeon.tdo.cripta_ocaso", "Cripta do Ocaso", "🏚️"),
        ("dungeon.tdo.galerias_vigia", "Galerias do Vigia", "🏛️"),
    ):
        intro = render_dungeons(_dungeon_view("detail", family, name))
        assert intro.text.startswith(f"{emoji} <b>{name}</b>\n\n<i>Uma passagem esquecida")
        assert intro.image_key == family  # the dungeon's own art
        rows = [[b.text for b in row] for row in intro.keyboard.inline_keyboard]
        assert rows == [["⚔️ Entrar"], ["↩️ Retornar"]]
        # ⚔️ Entrar opens the difficulty choice of the same dungeon, back returns to the intro.
        levels = render_dungeons(_dungeon_view("detail", family, name), difficulties=True)
        assert name in levels.text
        assert levels.keyboard.inline_keyboard[-1][0].callback_data in {
            "dungeon:crypt",
            "dungeon:galleries",
        }


# ------------------------------------------------------------------ Prologue art


ASSETS = Path(__file__).resolve().parents[1] / "assets"


@pytest.mark.skipif(not ASSETS.is_dir(), reason="assets/ not present")
def test_every_prologue_state_resolves_to_a_real_contextual_image():
    from asterion.bot.prologue_ui import (
        OUTCOME_DEFEAT_IMAGE,
        OUTCOME_VICTORY_IMAGE,
    )

    images = build_asset_images(("tdo.brazier.estrada",), ASSETS)
    screens = {f"scene:{node}": render_scene(node) for node in SCENE_IDS}
    screens["victory"] = render_combat(_outcome("victory"))
    screens["defeat"] = render_combat(_outcome("defeat"))
    screens["brazier"] = render_brazier("x", Decimal(1), Decimal(1))
    screens["ending"] = render_prologue_ending()
    assert screens["victory"].image_key == OUTCOME_VICTORY_IMAGE
    assert screens["defeat"].image_key == OUTCOME_DEFEAT_IMAGE
    for label, screen in screens.items():
        assert images.get(screen.image_key), f"{label} has no image ({screen.image_key})"
    # Not one generic picture for everything: the Brazier, ending and defeat differ.
    refs = {label: images[screen.image_key] for label, screen in screens.items()}
    assert len({refs["brazier"], refs["ending"], refs["scene:cinzas"]}) == 3
    assert refs["defeat"] == refs["brazier"] or refs["defeat"] != refs["scene:cinzas"]
    # Both first-combat creatures resolve their own Estrada das Cinzas art.
    for creature in ("dog_cinereo", "corvo_fuligem"):
        key = creature_image_key(creature, ENCOUNTER_LOCATION)
        assert images.get(key), key
    dog, crow = (
        images[creature_image_key(c, ENCOUNTER_LOCATION)] for c in ("dog_cinereo", "corvo_fuligem")
    )
    assert dog != crow


def _outcome(result):
    from tests.test_prologue_closing import combat_view

    view = combat_view("dog_cinereo")
    return replace(view, combat=replace(view.combat, result=result))

from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.active_arts import (
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.application.class_trials import ClassTrialService
from asterion.application.path_selection import (
    PathMutationCode,
    PathMutationRejected,
    PathSelectionService,
    PathView,
)
from asterion.bot.path_handlers import path_router
from asterion.bot.path_ui import (
    render_path_choices,
    render_path_exchange,
    render_path_preview,
)
from asterion.domain.arts import FIRST_CLASS_ART_IDS, ActiveArtDefinition, active_art_definition
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.paths import PATH_DEFINITIONS, PATHS_BY_CLASS
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterActiveArtSlot,
    GameActivity,
    HuntRound,
    Unlock,
    WorldState,
)
from tests.test_creation_ui import callback_update

D = Decimal
REFUGE = "Refúgio do Ocaso"
REGION = "Terras do Ocaso"


async def _seed_character(
    database,
    actor: int,
    *,
    cls: str = "sentinela",
    level: int = 10,
    crowns: int = 1000,
    selected_path: str | None = None,
    trial_complete: bool = False,
    location: str = REFUGE,
    hp_ratio: D | None = None,
):
    if hp_ratio is None:
        hp_ratio = D(1)
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats(cls, level, "remanescente", selected_path=selected_path)
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        character = Character(
            id=character_id,
            telegram_id=actor,
            server_id="ocaso",
            name="Path" + "".join(chr(ord("a") + int(digit)) for digit in str(actor)[-4:]),
            race="remanescente",
            character_class=cls,
            selected_path=selected_path,
            stage="menu:ready",
            ruleset_version="gdd-1.4.7-baseline-1.0",
            level=level,
            xp=0,
            hp=stats.hp * hp_ratio,
            max_hp=stats.hp,
            vigor=73,
            max_vigor=100,
            crowns=crowns,
        )
        session.add(character)
        session.add(WorldState(character_id=character_id, region=REGION, location=location))
        if trial_complete:
            session.add(Unlock(character_id=character_id, unlock_id="class_trial_completed"))
    return character_id, sessions


def _buttons(screen):
    return [button for row in screen.keyboard.inline_keyboard for button in row]


@pytest.mark.asyncio
async def test_initial_choice_requires_completed_trial_and_is_atomic_idempotent(database):
    actor = 771201
    character_id, sessions = await _seed_character(
        database, actor, hp_ratio=D("0.5"), crowns=450
    )
    service = PathSelectionService(sessions, "ocaso")
    with pytest.raises(PathMutationRejected) as blocked:
        await service.choose_initial(actor, "bastiao", 0)
    assert blocked.value.code == PathMutationCode.TRIAL_REQUIRED

    async with sessions.begin() as session:
        session.add(Unlock(character_id=character_id, unlock_id="class_trial_completed"))
    before = await service.view(actor)
    chosen = await service.choose_initial(actor, "bastiao", before.configuration_version)
    assert chosen is not None and chosen.changed
    assert chosen.view.selected_path == "bastiao"
    assert chosen.view.crowns == 450
    assert chosen.view.configuration_version == before.configuration_version + 1

    expected = resolve_combat_stats("sentinela", 10, "remanescente", selected_path="bastiao")
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.selected_path == "bastiao"
        assert character.max_hp == expected.hp
        assert character.hp == (expected.hp / D(2)).to_integral_value(rounding="ROUND_FLOOR")

    repeated = await service.choose_initial(actor, "bastiao", chosen.view.configuration_version)
    assert repeated is not None and not repeated.changed
    assert repeated.view.configuration_version == chosen.view.configuration_version
    with pytest.raises(PathMutationRejected) as other_path:
        await service.choose_initial(actor, "devastador", chosen.view.configuration_version)
    assert other_path.value.code == PathMutationCode.ALREADY_SELECTED
    with pytest.raises(PathMutationRejected) as wrong_class:
        await service.exchange(actor, "carrasco", chosen.view.configuration_version)
    assert wrong_class.value.code == PathMutationCode.WRONG_PATH


@pytest.mark.asyncio
async def test_exchange_checks_location_balance_foreground_and_preserves_hp_ratio(database):
    actor = 771202
    character_id, sessions = await _seed_character(
        database,
        actor,
        selected_path="bastiao",
        trial_complete=True,
        hp_ratio=D("0.5"),
        crowns=1000,
        location="Bosque Calcinado",
    )
    service = PathSelectionService(sessions, "ocaso")
    before = await service.view(actor)
    with pytest.raises(PathMutationRejected) as wrong_location:
        await service.exchange(actor, "devastador", before.configuration_version)
    assert wrong_location.value.code == PathMutationCode.WRONG_LOCATION

    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        world.location = REFUGE
        character = await session.get(Character, character_id)
        character.crowns = 0
    with pytest.raises(PathMutationRejected) as poor:
        await service.exchange(actor, "devastador", before.configuration_version)
    assert poor.value.code == PathMutationCode.INSUFFICIENT_CROWNS

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.crowns = 1000
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=character_id,
                content_id="test.foreground",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    with pytest.raises(PathMutationRejected) as foreground:
        await service.exchange(actor, "devastador", before.configuration_version)
    assert foreground.value.code == PathMutationCode.FOREGROUND

    async with sessions.begin() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.character_id == character_id)
        )
        await session.delete(activity)
    with pytest.raises(PathMutationRejected) as same_path:
        await service.exchange(actor, "bastiao", before.configuration_version)
    assert same_path.value.code == PathMutationCode.SAME_PATH

    expected = resolve_combat_stats("sentinela", 10, "remanescente", selected_path="devastador")
    result = await service.exchange(actor, "devastador", before.configuration_version)
    assert result is not None and result.changed
    assert result.view.crowns == 620  # round10(1.5 × round10(100 + 15 × 10)) = 380.
    assert result.view.configuration_version == before.configuration_version + 1
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.selected_path == "devastador"
        assert character.max_hp == expected.hp
        assert character.hp == (expected.hp / D(2)).to_integral_value(rounding="ROUND_FLOOR")
        assert character.vigor == 73


@pytest.mark.asyncio
async def test_exchange_removes_only_incompatible_path_art_slots(database, monkeypatch):
    actor = 771203
    character_id, sessions = await _seed_character(
        database, actor, selected_path="bastiao", trial_complete=True
    )
    future_art = "class_art.sentinela.path.bastiao"
    async with sessions.begin() as session:
        session.add_all(
            [
                CharacterActiveArtSlot(
                    character_id=character_id,
                    slot=1,
                    art_id=FIRST_CLASS_ART_IDS["sentinela"],
                ),
                CharacterActiveArtSlot(
                    character_id=character_id,
                    slot=2,
                    art_id=future_art,
                ),
            ]
        )

    real_definition = active_art_definition

    def definition(art_id):
        if art_id == future_art:
            return ActiveArtDefinition(future_art, "sentinela", 12, "bastiao")
        return real_definition(art_id)

    monkeypatch.setattr("asterion.application.path_selection.active_art_definition", definition)
    service = PathSelectionService(sessions, "ocaso")
    count = await service.incompatible_art_count(actor, "devastador")
    before = await service.view(actor)
    assert count == 1
    result = await service.exchange(actor, "devastador", before.configuration_version)
    assert result is not None and result.changed
    async with sessions() as session:
        slots = list(
            (
                await session.scalars(
                    select(CharacterActiveArtSlot)
                    .where(CharacterActiveArtSlot.character_id == character_id)
                    .order_by(CharacterActiveArtSlot.slot)
                )
            ).all()
        )
    assert [(slot.slot, slot.art_id) for slot in slots] == [
        (1, FIRST_CLASS_ART_IDS["sentinela"])
    ]


@pytest.mark.asyncio
async def test_path_art_requires_matching_selected_path(database, monkeypatch):
    actor = 771205
    character_id, sessions = await _seed_character(
        database, actor, level=12, trial_complete=True
    )
    path_art = "path_art.sentinela.bastiao.fortaleza"
    real_definition = active_art_definition

    def definition(art_id):
        if art_id == path_art:
            return ActiveArtDefinition(path_art, "sentinela", 12, "bastiao")
        return real_definition(art_id)

    monkeypatch.setattr("asterion.application.active_arts.active_art_definition", definition)
    service = ActiveArtService(sessions, "ocaso")
    with pytest.raises(ActiveArtMutationRejected) as unavailable:
        await service.equip_art(actor, 1, path_art)
    assert unavailable.value.code == ActiveArtMutationCode.PATH_REQUIRED

    paths = PathSelectionService(sessions, "ocaso")
    view = await paths.view(actor)
    await paths.choose_initial(actor, "bastiao", view.configuration_version)
    equipped = await service.equip_art(actor, 1, path_art, expected_configuration_version=1)
    assert equipped is not None and equipped.changed
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        active = await load_active_art_configuration(session, character)
    assert active.art_ids == (path_art,)


@pytest.mark.parametrize("character_class", tuple(PATHS_BY_CLASS))
def test_path_screens_only_offer_the_class_pair_and_preview_passive(character_class):
    pair = PATHS_BY_CLASS[character_class]
    view = PathView(
        character_id=uuid4(),
        character_name="Luiken",
        character_class=character_class,
        level=10,
        crowns=1000,
        selected_path=None,
        trial_completed=True,
        trial_state_version=4,
        trial_status="completed",
        trial_stage=3,
        location=REFUGE,
        foreground=False,
        configuration_version=9,
    )
    choices = render_path_choices(view)
    for path_id in pair:
        definition = PATH_DEFINITIONS[path_id]
        assert definition.name in choices.text
        preview = render_path_preview(view, path_id)
        assert definition.passive_name in preview.text
        assert definition.specialty in preview.text
        assert "Nv.12" in preview.text
        assert len(_buttons(preview)[0].callback_data.encode()) <= 64
        assert "melhor" not in preview.text.lower()
    assert len(_buttons(choices)) == 3


def test_path_exchange_screen_hides_confirm_when_location_or_funds_are_invalid():
    view = PathView(
        character_id=uuid4(),
        character_name="Luiken",
        character_class="sentinela",
        level=10,
        crowns=100,
        selected_path="bastiao",
        trial_completed=True,
        trial_state_version=4,
        trial_status="completed",
        trial_stage=3,
        location="Bosque Calcinado",
        foreground=False,
        configuration_version=9,
    )
    blocked_location = render_path_exchange(view, "devastador", 1)
    assert "Local Inapropriado" in blocked_location.text
    assert "Confirmar Troca" not in [button.text for button in _buttons(blocked_location)]

    refuge = replace(view, location=REFUGE)
    blocked_crowns = render_path_exchange(refuge, "devastador", 1)
    assert "Coroas · Insuficientes" in blocked_crowns.text
    assert "Confirmar Troca" not in [button.text for button in _buttons(blocked_crowns)]


@pytest.mark.asyncio
async def test_path_exchange_screen_hides_confirm_during_interrupted_round(database):
    actor = 771208
    character_id, sessions = await _seed_character(
        database, actor, selected_path="bastiao", trial_complete=True
    )
    async with sessions.begin() as session:
        session.add(
            HuntRound(
                id=uuid4(),
                character_id=character_id,
                status="interrupted",
                batch_size=5,
                seed="path-round-lock",
            )
        )
    view = await PathSelectionService(sessions, "ocaso").view(actor)
    assert view is not None and view.foreground
    screen = render_path_exchange(view, "devastador", 0)
    assert "Atividade" in screen.text
    assert "Confirmar Troca" not in [button.text for button in _buttons(screen)]


@pytest.mark.asyncio
async def test_path_callback_flow_persists_once_and_reconnect_renders_selected_path(
    database,
):
    actor = 771204
    _character_id, sessions = await _seed_character(
        database, actor, cls="luminar", trial_complete=True
    )
    paths = PathSelectionService(sessions, "ocaso")
    trials = ClassTrialService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(path_router(paths, trials, {}))
    telegram = Bot("123456:local-test-token")
    telegram.session.make_request = AsyncMock(return_value=True)

    await dispatcher.feed_raw_update(
        telegram, callback_update("character:path", update_id=1, actor=actor)
    )
    displayed = telegram.session.make_request.call_args.args[1]
    assert "Escolha de Caminho · Pendente" in displayed.text

    await dispatcher.feed_raw_update(
        telegram, callback_update("path:choose", update_id=2, actor=actor)
    )
    choices = telegram.session.make_request.call_args.args[1]
    assert "Guardião" in choices.text and "Inquisidor" in choices.text
    assert "Agoureiro" not in choices.text

    await dispatcher.feed_raw_update(
        telegram, callback_update("path:preview:guardiao:0", update_id=3, actor=actor)
    )
    preview = telegram.session.make_request.call_args.args[1]
    assert "Aurora" in preview.text and "+5%" in preview.text

    await dispatcher.feed_raw_update(
        telegram, callback_update("path:confirm:guardiao:0", update_id=4, actor=actor)
    )
    root = telegram.session.make_request.call_args.args[1]
    assert "Guardião · Caminho Atual" in root.text
    assert "Escolha de Caminho · Pendente" not in root.text
    current = await paths.view(actor)
    assert current.selected_path == "guardiao"
    assert current.configuration_version == 1
    await dispatcher.feed_raw_update(
        telegram, callback_update("path:confirm:inquisidor:0", update_id=5, actor=actor)
    )
    current = await paths.view(actor)
    assert current.selected_path == "guardiao"
    assert current.configuration_version == 1

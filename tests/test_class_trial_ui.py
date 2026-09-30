from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher

from asterion.application.class_trials import ClassTrialService, ClassTrialView
from asterion.application.creation import CreationService
from asterion.application.world import WorldService
from asterion.bot.class_trial_handlers import class_trial_router
from asterion.bot.class_trial_ui import (
    CLASS_STAGES,
    ClassTrialPageCallback,
    render_class_path,
    render_class_trial,
    render_trial_combat,
    render_trial_targets,
)
from asterion.bot.combat_ui import (
    ClassTrialActionCallback,
    class_trial_action_ids,
    class_trial_target_ids,
)
from asterion.bot.creation_handlers import creation_router
from asterion.bot.world_handlers import world_router
from asterion.domain.arts import LUMINAR_ART_IDS, TECELAO_ART_IDS
from asterion.domain.class_trials import (
    LUMINAR_ALLY_ENTITY_ID,
    create_luminar_trial_combat,
    create_oraculo_trial_combat,
    create_tecelao_trial_combat,
    luminar_stage_definition,
    oraculo_stage_definition,
    tecelao_stage_definition,
)
from asterion.domain.combat import Fighter, start_combat
from asterion.domain.combat_math import CombatStats, resolve_combat_stats
from asterion.infrastructure.db.models import (
    Account,
    Character,
    ClassTrialState,
    GameActivity,
    WorldState,
)
from tests.test_creation_ui import callback_update, message_update

D = Decimal
REFUGE = "Refúgio do Ocaso"
REGION = "Terras do Ocaso"


def _view(
    *,
    character_class="sentinela",
    kind="available",
    status="unstarted",
    level=10,
    stage=1,
    completed=(),
    context="refuge",
    version=0,
    retry=False,
    active=False,
):
    return ClassTrialView(
        character_id=uuid4(),
        kind=kind,
        status=status,
        character_class=character_class,
        trial_id=f"trial.{character_class}.test",
        level=level,
        state_version=version,
        current_stage=stage,
        completed_stages=tuple(completed),
        context=context,
        attempt_id=uuid4() if active else None,
        encounter_id=uuid4() if active else None,
        combat_version=8 if active else None,
        retry_available=retry,
    )


def _player(character_class: str) -> Fighter:
    stats = CombatStats(D("1800"), D("250"), D("100"), D("999"))
    return Fighter(
        "player", "Aster", 10, stats, stats.hp, character_class=character_class
    )


def _buttons(screen):
    return [button for row in screen.keyboard.inline_keyboard for button in row]


def test_path_hub_renders_locked_available_active_and_completed_states():
    locked = render_class_path(_view(kind="unavailable", level=9, version=4))
    assert "🔒 Provação de Classe · Nv.10" in locked.text
    assert [button.text for button in _buttons(locked)] == ["← Personagem"]

    available = render_class_path(_view(kind="available", version=7))
    assert "✨ Provação de Classe · Disponível" in available.text
    assert [button.text for button in _buttons(available)] == [
        "Iniciar Provação",
        "← Personagem",
    ]
    assert ClassTrialPageCallback.unpack(_buttons(available)[0].callback_data).state_version == 7

    active = render_class_path(
        _view(kind="active", status="active", stage=2, version=9, active=True)
    )
    assert "🔄 Provação · Em Andamento" in active.text
    assert "Etapa II/III" in active.text
    assert [button.text for button in _buttons(active)] == [
        "Retomar Provação",
        "← Personagem",
    ]

    completed = render_class_path(
        _view(
            kind="completed",
            status="completed",
            stage=3,
            completed=(1, 2, 3),
            version=11,
        )
    )
    assert "✅ Provação · Concluída" in completed.text
    assert "✨ Escolha de Caminho · Pendente" in completed.text
    assert "Nv.12" in completed.text
    assert "Escolher Caminho" not in completed.text
    assert [button.text for button in _buttons(completed)] == ["← Personagem"]


@pytest.mark.parametrize(
    ("character_class", "stage", "name"),
    [
        (character_class, stage, row[0])
        for character_class, rows in CLASS_STAGES.items()
        for stage, row in enumerate(rows, start=1)
    ],
)
def test_all_six_trials_render_the_eighteen_official_stage_names(
    character_class, stage, name
):
    screen = render_class_trial(
        _view(
            character_class=character_class,
            kind="ready",
            status="ready",
            stage=stage,
            completed=tuple(range(1, stage)),
            context="circle",
        )
    )
    assert name in screen.text
    assert "trial_entity." not in screen.text
    assert "Consumível" not in screen.text
    assert all(len(button.callback_data.encode()) <= 64 for button in _buttons(screen))


def test_stage_transition_retry_and_path_return_have_contextual_actions():
    transition = render_class_trial(
        _view(
            kind="ready",
            status="ready",
            stage=3,
            completed=(1, 2),
            context="circle",
        )
    )
    assert "Etapa II/III · Abrir a Guarda · Concluída" in transition.text
    assert "Próxima Etapa · III" in transition.text
    assert [button.text for button in _buttons(transition)] == [
        "Iniciar Próxima Etapa",
        "← Caminho",
    ]

    failed = render_class_trial(
        _view(
            kind="between_attempts",
            status="ready",
            stage=2,
            completed=(1,),
            context="circle",
            retry=True,
        )
    )
    assert "Tentativa Encerrada" in failed.text
    assert [button.text for button in _buttons(failed)] == [
        "Tentar Novamente",
        "← Caminho",
    ]
    assert not any(word in failed.text for word in ("XP", "Coroas", "Vigor", "Saque"))

    refuge = render_class_trial(
        _view(
            kind="between_attempts",
            status="ready",
            stage=2,
            completed=(1,),
            context="refuge",
        )
    )
    assert [button.text for button in _buttons(refuge)] == [
        "Retornar ao Círculo",
        "← Caminho",
    ]


def test_tecelao_hud_supports_three_targets_passives_and_single_commit_aoe():
    art_ids = tuple(TECELAO_ART_IDS.values())[:3]
    definition = tecelao_stage_definition(2, allowed_art_ids=art_ids)
    combat = start_combat(create_tecelao_trial_combat(_player("tecelao"), definition))
    view = _view(
        character_class="tecelao",
        kind="active",
        status="active",
        stage=2,
        active=True,
    )
    screen = render_trial_combat(view, combat)
    assert "⚔️ Provação · Etapa II/III" in screen.text
    assert len(class_trial_target_ids(combat, "attack")) == 3
    assert "Consumível" not in screen.text

    action_ids = class_trial_action_ids(combat)
    attack_index = action_ids.index("attack")
    targets = render_trial_targets(view, combat, attack_index)
    target_buttons = _buttons(targets)[:-1]
    assert [button.text for button in target_buttons] == ["1", "2", "3"]
    target_names = ("Eco Menor",)
    assert all(name in targets.text for name in target_names)
    for index, button in enumerate(target_buttons):
        assert len(button.callback_data.encode()) <= 64
        callback = ClassTrialActionCallback.unpack(button.callback_data)
        assert callback.attempt_id == view.attempt_id
        assert callback.combat_version == combat.version
        assert callback.action_index == attack_index
        assert callback.target_index == index

    rupture = TECELAO_ART_IDS["ruptura_da_trama"]
    aoe_button = next(
        button
        for button in _buttons(screen)
        if ClassTrialActionCallback.unpack(button.callback_data).action_index
        == action_ids.index(rupture)
    )
    aoe_callback = ClassTrialActionCallback.unpack(aoe_button.callback_data)
    assert aoe_callback.target == "x"
    assert class_trial_target_ids(combat, rupture) == ()


def test_luminar_hud_and_target_selection_include_only_live_friendly_targets():
    art_ids = (
        LUMINAR_ART_IDS["fulgor"],
        LUMINAR_ART_IDS["renovacao"],
        LUMINAR_ART_IDS["egide_solar"],
    )
    definition = luminar_stage_definition(1, allowed_art_ids=art_ids)
    combat = start_combat(create_luminar_trial_combat(_player("luminar"), definition))
    combat.fighters[LUMINAR_ALLY_ENTITY_ID].hp = D(300)
    combat.fighters[LUMINAR_ALLY_ENTITY_ID].barrier = D(45)
    combat.fighters[LUMINAR_ALLY_ENTITY_ID].barrier_remaining = 2
    view = _view(
        character_class="luminar",
        kind="active",
        status="active",
        active=True,
    )
    screen = render_trial_combat(view, combat)
    assert "✨ <b>Eco Aliado</b>" in screen.text
    assert "300 / 480" in screen.text
    assert "Barreira de Eco Aliado" in screen.text
    assert "Atq" not in screen.text and "Consumível" not in screen.text

    assert set(class_trial_target_ids(combat, LUMINAR_ART_IDS["renovacao"])) == {
        "player",
        LUMINAR_ALLY_ENTITY_ID,
    }
    action_ids = class_trial_action_ids(combat)
    healing_index = action_ids.index(LUMINAR_ART_IDS["renovacao"])
    targets = render_trial_targets(view, combat, healing_index)
    assert "Eco Aliado" in targets.text
    assert "Aster" in targets.text
    assert [button.text for button in _buttons(targets)[:-1]] == ["1", "2"]
    assert all(len(button.callback_data.encode()) <= 64 for button in _buttons(targets))


def test_prepared_action_is_visible_and_trial_actions_are_only_equipped_arts():
    from asterion.domain.arts import ORACULO_ART_IDS

    equipped = (ORACULO_ART_IDS["vislumbre"],)
    definition = oraculo_stage_definition(2, allowed_art_ids=equipped)
    combat = start_combat(create_oraculo_trial_combat(_player("oraculo"), definition))
    hostile = definition.entities[0].entity_id
    prepared_id = next(
        key for key, action in combat.enemy_actions.items() if action.prepared
    )
    combat = replace(
        combat,
        prepared_action=prepared_id,
        prepared_source=hostile,
        prepared_target="player",
        prepared_action_instance_id="prepared-instance-1",
    )
    view = _view(
        character_class="oraculo",
        kind="active",
        status="active",
        stage=2,
        active=True,
    )
    screen = render_trial_combat(view, combat)
    assert "☄️ <b>Eco da Antevisão</b> prepara <b>Impacto Anunciado</b>." in screen.text
    assert set(class_trial_action_ids(combat)) == {
        "attack",
        "defend",
        equipped[0],
    }
    assert "Consumível" not in screen.text


async def _seed_trial(database, actor: int):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats("sentinela", 10, "remanescente")
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Heroa",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=10,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=37,
                max_vigor=100,
                crowns=23,
            )
        )
        session.add(
            WorldState(character_id=character_id, region=REGION, location=REFUGE)
        )
    return character_id, ClassTrialService(sessions, "ocaso")


@pytest.fixture
def telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


async def test_dispatch_start_menu_stale_callback_and_reconnect_keep_same_attempt(
    database, telegram
):
    actor = 982731
    _character_id, service = await _seed_trial(database, actor)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(class_trial_router(service, {}))
    dispatcher.include_router(
        creation_router(CreationService(database[1], "ocaso"), {}, class_trials=service)
    )
    dispatcher.include_router(
        world_router(WorldService(database[1], "ocaso"), {}, class_trials=service)
    )

    available = await service.resume(actor)
    await dispatcher.feed_raw_update(
        telegram, callback_update("character:path", update_id=1, actor=actor)
    )
    assert "Provação de Classe · Disponível" in telegram.session.make_request.call_args.args[1].text

    begin = ClassTrialPageCallback.for_action("begin", available.state_version).pack()
    await dispatcher.feed_raw_update(
        telegram, callback_update(begin, update_id=2, actor=actor)
    )
    ready = await service.resume(actor)
    begin_screen = telegram.session.make_request.call_args.args[1]
    assert [
        button.text
        for row in begin_screen.reply_markup.inline_keyboard
        for button in row
    ] == ["Iniciar Etapa", "← Caminho"]

    start = ClassTrialPageCallback.for_action("start", ready.state_version).pack()
    await dispatcher.feed_raw_update(
        telegram, callback_update(start, update_id=3, actor=actor)
    )
    active = await service.resume(actor)
    combat = await service.combat(actor, active.attempt_id)
    assert active.kind == "active" and combat is not None
    attempt_id = active.attempt_id
    initial_screen = render_trial_combat(active, combat)

    await dispatcher.feed_raw_update(
        telegram, message_update("/start", update_id=4, actor=actor)
    )
    assert telegram.session.make_request.call_args.args[1].text == initial_screen.text
    menu_update = message_update("/menu", update_id=5, actor=actor)
    menu_update["message"]["entities"] = [
        {"type": "bot_command", "offset": 0, "length": 5}
    ]
    await dispatcher.feed_raw_update(telegram, menu_update)
    assert telegram.session.make_request.call_args.args[1].text == initial_screen.text

    attack = next(
        button
        for button in _buttons(initial_screen)
        if button.text == "Atacar"
    )
    stale = ClassTrialActionCallback.unpack(attack.callback_data)
    assert stale.attempt_id == attempt_id
    await dispatcher.feed_raw_update(
        telegram, callback_update(attack.callback_data, update_id=6, actor=actor)
    )
    after = await service.resume(actor)
    assert after.kind == "active" and after.attempt_id == attempt_id
    after_combat = await service.combat(actor, attempt_id)
    assert after_combat.version > combat.version

    await dispatcher.feed_raw_update(
        telegram, callback_update(attack.callback_data, update_id=7, actor=actor)
    )
    after_stale = await service.combat(actor, attempt_id)
    assert after_stale.version == after_combat.version
    methods = [call.args[1] for call in telegram.session.make_request.call_args_list]
    assert any(
        getattr(method, "text", None) == "A Provação foi atualizada."
        for method in methods
    )
    assert "Turno 2" in telegram.session.make_request.call_args.args[1].text


async def test_failed_attempt_is_rebuilt_as_retry_and_reuses_same_stage(database, telegram):
    actor = 982732
    character_id, service = await _seed_trial(database, actor)
    initial = await service.resume(actor)
    begun = await service.begin(actor, initial.state_version)
    active = await service.start_attempt(actor, begun.state_version)
    attempt_id = active.attempt_id

    async with service.sessions.begin() as session:
        activity = await session.get(GameActivity, attempt_id)
        state = await session.get(ClassTrialState, character_id)
        activity.status = "failed"
        state.status = "ready"
        state.current_attempt_id = None
        state.attempt_state = None
        state.context = "circle"
        state.state_version += 1

    failed = await service.resume(actor)
    assert failed.current_stage == 1
    assert failed.completed_stages == ()
    assert failed.retry_available
    retry_screen = render_class_trial(failed)
    assert "Tentativa Encerrada" in retry_screen.text
    assert [button.text for button in _buttons(retry_screen)] == [
        "Tentar Novamente",
        "← Caminho",
    ]

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(class_trial_router(service, {}))
    retry_callback = ClassTrialPageCallback.for_action(
        "retry", failed.state_version
    ).pack()
    await dispatcher.feed_raw_update(
        telegram, callback_update(retry_callback, update_id=12, actor=actor)
    )
    retried = await service.resume(actor)
    assert retried.kind == "active"
    assert retried.current_stage == 1
    assert retried.attempt_id != attempt_id

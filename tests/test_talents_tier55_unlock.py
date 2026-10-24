"""Public Nv.55 acquisition, persistence, and combat acceptance."""

import asyncio
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.doctrines import DoctrineService
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    resolve_character_combat_stats,
)
from asterion.application.talents import (
    TalentMutationCode,
    TalentMutationRejected,
    TalentService,
)
from asterion.bot.character_progression_ui import render_talent_detail
from asterion.bot.doctrines_ui import render_talent_choices
from asterion.domain.arts import (
    CONJURADOR_ART_IDS,
    ERRANTE_ART_IDS,
    LUMINAR_ART_IDS,
    ORACULO_ART_IDS,
    SENTINEL_ART_IDS,
    VIGIA_ART_IDS,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, Combat, Fighter, act, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import equipment_configuration_from_data
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENTS_BY_CLASS,
    talent_points_at_level,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterTalentChoice,
    GameActivity,
    WorldState,
)

D = Decimal
CLASS_ORDER = ("sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar")
PATHS = {
    "sentinela": "bastiao",
    "errante": None,
    "vigia": "atirador",
    "tecelao": "conjurador",
    "oraculo": "agoureiro",
    "luminar": None,
}
TIER55 = {
    character_class: tuple(
        talent.talent_id
        for talent in definitions
        if talent.level == 55
    )
    for character_class, definitions in TALENTS_BY_CLASS.items()
}


async def _seed(database, actor: int, character_class: str, *, level: int, crowns=10000):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats(
        character_class,
        level,
        "remanescente",
        selected_path=PATHS[character_class],
    )
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Hero{chr(97 + actor % 26)}",
                race="remanescente",
                character_class=character_class,
                selected_path=PATHS[character_class],
                stage="menu:ready",
                ruleset_version="gdd-1.6.0",
                level=level,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=71,
                max_vigor=100,
                crowns=crowns,
            )
        )
        session.add(
            WorldState(
                character_id=character_id,
                region="Terras do Ocaso",
                location="Refúgio do Ocaso",
            )
        )
    return character_id, sessions


def _battle(character_class, path, talent_ids, stats, action_id):
    player = Fighter(
        "player.entity",
        "Nv55 Player",
        55,
        replace(stats, crit=D(0), evasion=D(0), block=D(0)),
        stats.hp,
        race="remanescente",
        character_class=character_class,
        selected_path=path,
        talent_ids=tuple(talent_ids),
        side="player",
        takes_turn=True,
    )
    enemy = Fighter(
        "enemy.entity",
        "Enemy",
        55,
        CombatStats(D(10000), D(100), D(0), D(100), evasion=D(0)),
        D(10000),
        side="enemy",
        takes_turn=False,
        required_for_victory=False,
    )
    player_actions = class_player_actions(character_class, (action_id,), path)
    state = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        {"player": player, "enemy": enemy},
        player_actions,
        {"wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")},
        ("wait",),
    )
    return start_combat(state)


def _verify_public_effect(character_class, talent_ids, stats):
    path = PATHS[character_class]
    if character_class == "sentinela":
        action_id, hp = SENTINEL_ART_IDS["golpe_de_guarda"], D(400)
    elif character_class == "errante":
        action_id, hp = ERRANTE_ART_IDS["corte_veloz"], D(350)
    elif character_class == "vigia":
        action_id, hp = VIGIA_ART_IDS["disparo_preciso"], D(350)
    elif character_class == "tecelao":
        action_id, hp = CONJURADOR_ART_IDS["estilhaco_do_veu"], D(400)
    elif character_class == "oraculo":
        action_id, hp = ORACULO_ART_IDS["ruina_predita"], D(350)
    else:
        action_id, hp = LUMINAR_ART_IDS["explosao_solar"], D(350)

    state = _battle(character_class, path, talent_ids, stats, action_id)
    target = state.fighters["enemy"]
    target.hp = hp
    if character_class == "tecelao":
        state.fighters["player"].path_state["trama_state"] = {
            "origin_art": "class_art.tecelao.other",
            "remaining": 2,
            "applied_opportunity": state.fighters["player"].opportunity,
        }
    result = act(state, action_id, target_id=target.id)
    event = next(item for item in reversed(result.events) if item.action == action_id)
    assert event.damage > 0
    expected = D("1.196") if character_class == "tecelao" else D("1.04")
    assert event.path_power_multiplier == expected


@pytest.mark.asyncio
async def test_all_six_classes_acquire_persist_reconstruct_and_use_nv55(database):
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    assert {character_class: len(ids) for character_class, ids in TIER55.items()} == {
        character_class: 3 for character_class in CLASS_ORDER
    }
    assert sum(map(len, TIER55.values())) == 18
    assert talent_points_at_level(55) == 11
    assert talent_points_at_level(60) == 12

    for index, character_class in enumerate(CLASS_ORDER):
        actor = 885500 + index
        character_id, sessions = await _seed(database, actor, character_class, level=54)
        service = TalentService(sessions, "ocaso")
        view = await service.view(actor)
        assert view is not None and view.total_points == 10 and view.available_points == 10
        definitions = tuple(item for item in TALENTS_BY_CLASS[character_class] if item.level == 55)
        assert tuple(item.talent_id for item in definitions) == TIER55[character_class]
        with pytest.raises(TalentMutationRejected) as level_gate:
            await service.acquire(
                actor, definitions[0].talent_id, view.combat_configuration_version
            )
        assert level_gate.value.code == TalentMutationCode.LEVEL_REQUIRED

        other_class = CLASS_ORDER[(index + 1) % len(CLASS_ORDER)]
        with pytest.raises(TalentMutationRejected) as wrong_class:
            await service.acquire(actor, TIER55[other_class][0], view.combat_configuration_version)
        assert wrong_class.value.code == TalentMutationCode.WRONG_CLASS

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            character.level = 55
        view = await service.view(actor)
        assert view is not None and view.total_points == 11 and view.available_points == 11
        with pytest.raises(TalentMutationRejected) as unknown:
            await service.acquire(
                actor, "talent.unknown.nv55", view.combat_configuration_version
            )
        assert unknown.value.code == TalentMutationCode.UNKNOWN_TALENT
        stale_version = view.combat_configuration_version
        for definition in definitions:
            detail = render_talent_detail(view, definition)
            assert "Adquirir Talento" in [
                button.text for row in detail.keyboard.inline_keyboard for button in row
            ]
            acquired = await service.acquire(
                actor, definition.talent_id, view.combat_configuration_version
            )
            assert acquired is not None and acquired.changed
            view = acquired.view
        assert view.available_points == 8
        assert [choice.point_slot for choice in view.choices] == [1, 2, 3]
        assert {choice.talent_id for choice in view.choices} == set(TIER55[character_class])
        with pytest.raises(TalentMutationRejected) as duplicate:
            await service.acquire(
                actor, definitions[0].talent_id, view.combat_configuration_version
            )
        assert duplicate.value.code == TalentMutationCode.DUPLICATE_TALENT
        with pytest.raises(TalentMutationRejected) as stale:
            await service.acquire(actor, definitions[0].talent_id, stale_version)
        assert stale.value.code == TalentMutationCode.STALE_CONFIGURATION

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            snapshot = await load_equipment_configuration(session, character)
            stats = resolve_character_combat_stats(character, snapshot)
            rows = list((await session.scalars(
                select(CharacterTalentChoice)
                .where(CharacterTalentChoice.character_id == character_id)
                .order_by(CharacterTalentChoice.point_slot)
            )).all())
        restored = equipment_configuration_from_data(snapshot.to_data("gdd-1.6.0"))
        talent_ids = tuple(talent for _, talent in restored.talent_choices)
        assert tuple(row.talent_id for row in rows) == TIER55[character_class]
        assert all(row.publicly_acquired for row in rows)
        assert validate_active_talent_ids(character_class, 55, talent_ids) == talent_ids
        _verify_public_effect(character_class, talent_ids, stats)


@pytest.mark.asyncio
async def test_nv60_accepts_nv55_and_preserves_twelve_point_budget(database):
    for index, character_class in enumerate(CLASS_ORDER):
        actor = 885520 + index
        _, sessions = await _seed(database, actor, character_class, level=60)
        service = TalentService(sessions, "ocaso")
        view = await service.view(actor)
        assert view is not None and view.total_points == 12 and view.available_points == 12
        result = await service.acquire(
            actor, TIER55[character_class][0], view.combat_configuration_version
        )
        assert result is not None and result.point_slot == 1
        assert result.view.total_points == 12 and result.view.available_points == 11


@pytest.mark.asyncio
async def test_nv55_doctrine_respec_and_configuration_lock(database):
    actor = 885540
    character_id, sessions = await _seed(database, actor, "luminar", level=55)
    doctrines = DoctrineService(sessions, "ocaso")
    created = await doctrines.create(actor, "Nv55 válido", 0)
    assert created is not None and created.doctrine_id is not None
    collection = await doctrines.view(actor)
    assert collection is not None
    doctrine = next(
        item for item in collection.doctrines if item.doctrine_id == created.doctrine_id
    )
    picker = render_talent_choices(collection, doctrine, 1)
    for talent_id in TIER55["luminar"]:
        definition = next(
            item for item in TALENTS_BY_CLASS["luminar"] if item.talent_id == talent_id
        )
        assert any(
            definition.name in button.text
            for row in picker.keyboard.inline_keyboard
            for button in row
        )
    edited = await doctrines.update_component(
        actor,
        created.doctrine_id,
        0,
        collection.configuration_version,
        "talents",
        [{"point_slot": 11, "talent_id": TIER55["luminar"][0]}],
    )
    assert edited is not None and edited.changed
    applied = await doctrines.apply(actor, created.doctrine_id, 1, edited.configuration_version)
    assert applied is not None and applied.changed
    view = await TalentService(sessions, "ocaso").view(actor)
    assert view is not None and view.choices[0].talent_id == TIER55["luminar"][0]

    async with sessions.begin() as session:
        session.add(
            GameActivity(
                character_id=character_id,
                content_id="c3-lock-test",
                status="active",
                state_version=0,
                ruleset_version="gdd-1.6.0",
            )
        )
    with pytest.raises(TalentMutationRejected) as locked:
        await TalentService(sessions, "ocaso").acquire(
            actor, TIER55["luminar"][1], view.combat_configuration_version
        )
    assert locked.value.code == TalentMutationCode.FOREGROUND

    async with sessions.begin() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.character_id == character_id)
        )
        activity.status = "completed"
    respec = await TalentService(sessions, "ocaso").respec(
        actor, view.combat_configuration_version
    )
    assert respec is not None and respec.changed and respec.view.available_points == 11


@pytest.mark.asyncio
async def test_nv55_concurrent_acquisition_and_rollback_are_atomic(database, monkeypatch):
    actor = 885560
    _, sessions = await _seed(database, actor, "sentinela", level=55)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    for talent in TALENTS_BY_CLASS["sentinela"][:10]:
        acquired = await service.acquire(actor, talent.talent_id, view.combat_configuration_version)
        assert acquired is not None
        view = acquired.view
    assert view.available_points == 1
    outcomes = await asyncio.gather(
        *(
            service.acquire(actor, talent_id, view.combat_configuration_version)
            for talent_id in TIER55["sentinela"][:2]
        ),
        return_exceptions=True,
    )
    assert sum(not isinstance(item, Exception) for item in outcomes) == 1
    failures = [item for item in outcomes if isinstance(item, TalentMutationRejected)]
    assert len(failures) == 1 and failures[0].code == TalentMutationCode.STALE_CONFIGURATION

    duplicate_actor = 885562
    _, duplicate_sessions = await _seed(database, duplicate_actor, "vigia", level=55)
    duplicate_service = TalentService(duplicate_sessions, "ocaso")
    duplicate_view = await duplicate_service.view(duplicate_actor)
    assert duplicate_view is not None
    duplicate_outcomes = await asyncio.gather(
        duplicate_service.acquire(
            duplicate_actor,
            TIER55["vigia"][0],
            duplicate_view.combat_configuration_version,
        ),
        duplicate_service.acquire(
            duplicate_actor,
            TIER55["vigia"][0],
            duplicate_view.combat_configuration_version,
        ),
        return_exceptions=True,
    )
    assert sum(not isinstance(item, Exception) for item in duplicate_outcomes) == 1
    duplicate_failures = [
        item for item in duplicate_outcomes if isinstance(item, TalentMutationRejected)
    ]
    assert len(duplicate_failures) == 1
    assert duplicate_failures[0].code == TalentMutationCode.STALE_CONFIGURATION

    rollback_actor = 885561
    rollback_id, rollback_sessions = await _seed(database, rollback_actor, "luminar", level=55)
    rollback_service = TalentService(rollback_sessions, "ocaso")
    rollback_view = await rollback_service.view(rollback_actor)
    assert rollback_view is not None

    async def fail_after_choice_flush(_session, _character):
        raise RuntimeError("test Nv55 rollback")

    monkeypatch.setattr(TalentService, "_reconcile_hp", staticmethod(fail_after_choice_flush))
    with pytest.raises(RuntimeError, match="test Nv55 rollback"):
        await rollback_service.acquire(
            rollback_actor,
            TIER55["luminar"][0],
            rollback_view.combat_configuration_version,
        )
    async with rollback_sessions() as session:
        character = await session.get(Character, rollback_id)
        rows = list((await session.scalars(
            select(CharacterTalentChoice).where(CharacterTalentChoice.character_id == rollback_id)
        )).all())
    assert rows == []
    assert character.combat_configuration_version == 0

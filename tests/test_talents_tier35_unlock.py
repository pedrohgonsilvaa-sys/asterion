"""Public release tests for the jointly enabled Nv.35 Talent tier."""

import asyncio
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.doctrines import DoctrineRejected, DoctrineService
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    resolve_character_combat_stats,
)
from asterion.application.talents import (
    TalentMutationCode,
    TalentMutationRejected,
    TalentService,
)
from asterion.bot.character_progression_ui import render_talent_detail, render_talent_list
from asterion.bot.doctrines_ui import render_talent_choices
from asterion.domain.arts import (
    ERRANTE_ART_IDS,
    LUMINAR_ART_IDS,
    ORACULO_ART_IDS,
    SENTINEL_ART_IDS,
    TECELAO_ART_IDS,
    VIGIA_ART_IDS,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, Combat, Effect, Fighter, act, start_combat
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
    validate_talent_choices,
)
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterTalentChoice,
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
TIER35 = {
    character_class: tuple(
        talent.talent_id for talent in definitions if talent.level == 35
    )
    for character_class, definitions in TALENTS_BY_CLASS.items()
}
PROBE_TALENT = {
    "sentinela": "talent.sentinela.barreira_densa",
    "errante": "talent.errante.oportunismo_ampliado",
    "vigia": "talent.vigia.alvo_exposto",
    "tecelao": "talent.tecelao.trama_agressiva",
    "oraculo": "talent.oraculo.profecia_dolorosa",
    "luminar": "talent.luminar.veredito_ardente",
}


async def _seed(
    database, actor: int, character_class: str, *, level: int, name_prefix: str = "A"
):
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
                name=f"{name_prefix}{character_class}",
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
                crowns=1000,
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


def _battle(character_class, path, talent_ids, stats, arts, *, enemy_effects=()):
    player = Fighter(
        "player.entity",
        "Nv35 Player",
        35,
        replace(stats, crit=D(0), evasion=D(0), block=D(0)),
        stats.hp,
        race="remanescente",
        character_class=character_class,
        selected_path=path,
        talent_ids=talent_ids,
        side="player",
        takes_turn=True,
    )
    enemy = Fighter(
        "enemy.entity",
        "Enemy",
        35,
        CombatStats(D(10000), D(100), D(0), D(100), evasion=D(0)),
        D(10000),
        effects=list(enemy_effects),
        side="enemy",
        takes_turn=False,
        required_for_victory=False,
    )
    player_actions = class_player_actions(character_class, arts, path)
    player_actions.setdefault(
        "attack", Action("attack", "Ataque Básico", D(1))
    )
    state = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        {"player": player, "enemy": enemy},
        player_actions,
        {"enemy.wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")},
        ("enemy.wait",),
    )
    state.configuration_snapshot = {
        "active_arts": tuple(
            {"slot": index, "art_id": art_id}
            for index, art_id in enumerate(arts, start=1)
        ),
        "talent_ids": tuple(talent_ids),
    }
    return start_combat(state)


def _event(state, action_id):
    return next(
        event
        for event in reversed(state.events)
        if event.actor_entity_id == "player.entity" and event.action == action_id
    )


def _observe_acquired_talent(character_class, path, talent_ids, stats):
    talent_id = PROBE_TALENT[character_class]
    if character_class == "sentinela":
        action_id = SENTINEL_ART_IDS["muralha_breve"]
        state = _battle(character_class, path, talent_ids, stats, (action_id,))
        result = act(state, action_id)
        baseline = _battle(character_class, path, (), stats, (action_id,))
        base_result = act(baseline, action_id)
        assert (
            _event(result, action_id).barrier_value
            > _event(base_result, action_id).barrier_value
        )
    elif character_class == "errante":
        action_id = ERRANTE_ART_IDS["ferida_profunda"]
        effect = Effect("public.debuff", "attack", D("0.10"), 2, 0, kind="debuff")
        state = _battle(
            character_class, path, talent_ids, stats, (action_id,), enemy_effects=(effect,)
        )
        assert (
            _event(act(state, action_id, target_id="enemy.entity"), action_id)
            .path_final_damage_bonus
            == D("0.10")
        )
    elif character_class == "vigia":
        action_id = VIGIA_ART_IDS["disparo_preciso"]
        state = _battle(character_class, path, talent_ids, stats, (action_id,))
        player, enemy = state.fighters["player"], state.fighters["enemy"]
        enemy.path_state["aim_from"] = {
            player.id: {
                "stacks": 2,
                "remaining": 2,
                "applied_opportunity": player.opportunity,
            }
        }
        assert (
            _event(act(state, action_id, target_id=enemy.id), action_id)
            .path_power_multiplier
            == D("1.03")
        )
    elif character_class == "tecelao":
        first = TECELAO_ART_IDS["fio_cortante"]
        action_id = TECELAO_ART_IDS["chama_tecida"]
        state = _battle(character_class, path, talent_ids, stats, (first, action_id))
        generated = act(state, first, target_id="enemy.entity")
        event = _event(act(generated, action_id, target_id="enemy.entity"), action_id)
        assert event.path_power_multiplier == D("1.17")
    elif character_class == "oraculo":
        action_id = ORACULO_ART_IDS["selo_da_queda"]
        state = _battle(character_class, path, talent_ids, stats, (action_id,))
        owner = state.fighters["player"]
        owner.path_state["omen_offensive"] = {
            "enemy.entity": {
                "remaining": 2,
                "applied_opportunity": owner.opportunity,
            }
        }
        event = _event(act(state, action_id, target_id="enemy.entity"), action_id)
        assert event.path_power_multiplier == D("1.1832")
    else:
        action_id = LUMINAR_ART_IDS["explosao_solar"]
        state = _battle(character_class, path, talent_ids, stats, (action_id,))
        state.fighters["player"].path_state["luminar_state"] = {
            "kind": "julgamento",
            "remaining": 2,
            "applied_opportunity": state.fighters["player"].opportunity,
        }
        event = _event(act(state, action_id), action_id)
        assert event.path_power_multiplier == D("1.122")
    assert talent_id in talent_ids


@pytest.mark.asyncio
async def test_all_six_classes_acquire_persist_and_use_nv35_talents(database):
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    assert {character_class: len(ids) for character_class, ids in TIER35.items()} == {
        character_class: 3 for character_class in CLASS_ORDER
    }
    assert sum(len(ids) for ids in TIER35.values()) == 18
    assert talent_points_at_level(35) == 7
    assert talent_points_at_level(60) == 12

    for index, character_class in enumerate(CLASS_ORDER):
        actor = 861350 + index
        character_id, sessions = await _seed(database, actor, character_class, level=34)
        service = TalentService(sessions, "ocaso")
        view = await service.view(actor)
        assert view is not None and view.total_points == 6 and view.available_points == 6
        tier35 = tuple(t for t in TALENTS_BY_CLASS[character_class] if t.level == 35)
        assert tuple(t.talent_id for t in tier35) == TIER35[character_class]
        with pytest.raises(TalentMutationRejected) as level_gate:
            await service.acquire(actor, tier35[0].talent_id, view.combat_configuration_version)
        assert level_gate.value.code == TalentMutationCode.LEVEL_REQUIRED

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            character.level = 35
        view = await service.view(actor)
        assert view is not None and view.total_points == 7 and view.available_points == 7
        other_class = next(name for name in CLASS_ORDER if name != character_class)
        wrong_class_id = TIER35[other_class][0]
        with pytest.raises(TalentMutationRejected) as wrong_class:
            await service.acquire(actor, wrong_class_id, view.combat_configuration_version)
        assert wrong_class.value.code == TalentMutationCode.WRONG_CLASS

        for definition in tier35:
            detail = render_talent_detail(view, definition)
            assert "Adquirir Talento" in [
                button.text
                for row in detail.keyboard.inline_keyboard
                for button in row
            ]
            result = await service.acquire(
                actor, definition.talent_id, view.combat_configuration_version
            )
            assert result is not None and result.changed
            view = result.view
        assert [choice.point_slot for choice in view.choices] == [1, 2, 3]
        assert {choice.talent_id for choice in view.choices} == set(TIER35[character_class])
        assert view.total_points == 7 and view.available_points == 4
        listing = render_talent_list(view)
        assert all(f"{definition.name} · Adquirido" in listing.text for definition in tier35)
        with pytest.raises(TalentMutationRejected) as duplicate:
            await service.acquire(actor, tier35[0].talent_id, view.combat_configuration_version)
        assert duplicate.value.code == TalentMutationCode.DUPLICATE_TALENT

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            snapshot = await load_equipment_configuration(session, character)
            stats = resolve_character_combat_stats(character, snapshot)
            rows = list(
                (
                    await session.scalars(
                        select(CharacterTalentChoice)
                        .where(CharacterTalentChoice.character_id == character_id)
                        .order_by(CharacterTalentChoice.point_slot)
                    )
                ).all()
            )
        restored = equipment_configuration_from_data(snapshot.to_data("gdd-1.6.0"))
        talent_ids = tuple(talent_id for _, talent_id in restored.talent_choices)
        assert len(rows) == 3
        assert validate_talent_choices(
            character_class,
            35,
            [(choice.point_slot, choice.talent_id) for choice in view.choices],
        ) == tuple((choice.point_slot, choice.talent_id) for choice in view.choices)
        assert talent_ids == TIER35[character_class]
        assert validate_active_talent_ids(character_class, 35, talent_ids) == talent_ids
        _observe_acquired_talent(character_class, PATHS[character_class], talent_ids, stats)

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            character.level = 60
        high_level = await service.view(actor)
        assert high_level is not None and high_level.total_points == 12
        assert validate_active_talent_ids(character_class, 60, talent_ids) == talent_ids
        for future_level in (55,):
            future_id = next(
                talent.talent_id
                for talent in TALENTS_BY_CLASS[character_class]
                if talent.level == future_level
            )
            with pytest.raises(TalentMutationRejected) as future:
                await service.acquire(
                    actor, future_id, high_level.combat_configuration_version
                )
            assert future.value.code == TalentMutationCode.TIER_NOT_IMPLEMENTED
        assert validate_active_talent_ids(
            character_class,
            60,
            (next(t.talent_id for t in TALENTS_BY_CLASS[character_class] if t.level == 45),),
        )

        high_actor = 862350 + index
        _, high_sessions = await _seed(
            database,
            high_actor,
            character_class,
            level=60,
            name_prefix="B",
        )
        high_service = TalentService(high_sessions, "ocaso")
        high_view = await high_service.view(high_actor)
        assert high_view is not None and high_view.available_points == 12
        high_acquired = await high_service.acquire(
            high_actor,
            TIER35[character_class][0],
            high_view.combat_configuration_version,
        )
        assert high_acquired is not None and high_acquired.point_slot == 1
        assert high_acquired.view.available_points == 11


@pytest.mark.asyncio
async def test_doctrine_accepts_nv35_and_keeps_nv55_invalid(database):
    character_class = "luminar"
    actor = 861360
    _, sessions = await _seed(database, actor, character_class, level=35)
    service = DoctrineService(sessions, "ocaso")
    created = await service.create(actor, "Tier35", 0)
    assert created is not None and created.doctrine_id is not None
    collection = await service.view(actor)
    assert collection is not None
    doctrine = next(
        item for item in collection.doctrines if item.doctrine_id == created.doctrine_id
    )
    available = render_talent_choices(collection, doctrine, 7)
    assert all(
        any(
            definition.name in button.text
            for row in available.keyboard.inline_keyboard
            for button in row
        )
        for definition in TALENTS_BY_CLASS[character_class]
        if definition.level == 35
    )
    talent_id = TIER35[character_class][0]
    edited = await service.update_component(
        actor,
        created.doctrine_id,
        0,
        collection.configuration_version,
        "talents",
        [{"point_slot": 7, "talent_id": talent_id}],
    )
    assert edited is not None and edited.changed
    applied = await service.apply(
        actor,
        created.doctrine_id,
        1,
        edited.configuration_version,
    )
    assert applied is not None and applied.changed
    saved = await TalentService(sessions, "ocaso").view(actor)
    assert saved is not None and saved.choices[-1].talent_id == talent_id
    invalid_id = next(
        talent.talent_id
        for talent in TALENTS_BY_CLASS[character_class]
        if talent.level == 55
    )
    fresh = await service.view(actor)
    assert fresh is not None
    with pytest.raises(DoctrineRejected, match="invalid_talents"):
        await service.update_component(
            actor,
            created.doctrine_id,
            1,
            fresh.configuration_version,
            "talents",
            [{"point_slot": 7, "talent_id": invalid_id}],
        )


@pytest.mark.asyncio
async def test_nv35_concurrent_acquisition_cannot_spend_last_point_twice(database):
    actor = 861361
    _, sessions = await _seed(database, actor, "sentinela", level=35)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    for talent in TALENTS_BY_CLASS["sentinela"][:6]:
        result = await service.acquire(
            actor, talent.talent_id, view.combat_configuration_version
        )
        assert result is not None
        view = result.view
    assert view.available_points == 1
    candidates = TIER35["sentinela"][:2]
    outcomes = await asyncio.gather(
        *(
            service.acquire(actor, talent_id, view.combat_configuration_version)
            for talent_id in candidates
        ),
        return_exceptions=True,
    )
    successes = [result for result in outcomes if not isinstance(result, Exception)]
    failures = [result for result in outcomes if isinstance(result, TalentMutationRejected)]
    assert len(successes) == 1 and len(failures) == 1
    assert failures[0].code == TalentMutationCode.STALE_CONFIGURATION
    saved = await service.view(actor)
    assert saved is not None and saved.available_points == 0
    assert len(saved.choices) == 7
    assert sum(choice.talent_id in candidates for choice in saved.choices) == 1


@pytest.mark.asyncio
async def test_nv35_concurrent_duplicate_and_failed_transaction_are_atomic(database, monkeypatch):
    actor = 861362
    character_id, sessions = await _seed(database, actor, "sentinela", level=35)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    talent_id = TIER35["sentinela"][0]
    outcomes = await asyncio.gather(
        service.acquire(actor, talent_id, view.combat_configuration_version),
        service.acquire(actor, talent_id, view.combat_configuration_version),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, Exception) for result in outcomes) == 1
    failures = [result for result in outcomes if isinstance(result, TalentMutationRejected)]
    assert len(failures) == 1 and failures[0].code == TalentMutationCode.STALE_CONFIGURATION

    rollback_actor = 861363
    rollback_id, rollback_sessions = await _seed(
        database, rollback_actor, "luminar", level=35
    )
    rollback_service = TalentService(rollback_sessions, "ocaso")
    rollback_view = await rollback_service.view(rollback_actor)
    assert rollback_view is not None

    async def fail_after_choice_flush(_session, _character):
        raise RuntimeError("test rollback")

    monkeypatch.setattr(
        TalentService, "_reconcile_hp", staticmethod(fail_after_choice_flush)
    )
    with pytest.raises(RuntimeError, match="test rollback"):
        await rollback_service.acquire(
            rollback_actor,
            TIER35["luminar"][0],
            rollback_view.combat_configuration_version,
        )
    async with rollback_sessions() as session:
        character = await session.get(Character, rollback_id)
        rows = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice).where(
                        CharacterTalentChoice.character_id == rollback_id
                    )
                )
            ).all()
        )
    assert rows == []
    assert character.combat_configuration_version == 0

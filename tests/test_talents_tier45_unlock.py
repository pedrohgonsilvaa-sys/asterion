"""Public acquisition and combat acceptance for the jointly released Nv.45 tier."""

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
from asterion.domain.combat import (
    Action,
    Combat,
    DotState,
    Effect,
    Fighter,
    act,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, resolve_combat_stats
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
TIER45 = {
    character_class: tuple(
        item.talent_id for item in definitions if item.level == 45
    )
    for character_class, definitions in TALENTS_BY_CLASS.items()
}


async def _seed(database, actor: int, character_class: str, *, level: int, crowns=1000):
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


def _battle(character_class, path, talent_ids, stats, action_id, *, enemy_effects=()):
    player = Fighter(
        "player.entity",
        "Nv45 Player",
        45,
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
        45,
        CombatStats(D(10000), D(100), D(0), D(100), evasion=D(0)),
        D(10000),
        effects=list(enemy_effects),
        side="enemy",
        takes_turn=False,
        required_for_victory=False,
    )
    actions = class_player_actions(character_class, (action_id,), path)
    state = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        {"player": player, "enemy": enemy},
        actions,
        {"wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")},
        ("wait",),
    )
    return start_combat(state)


def _observe_public_effect(character_class, path, talent_ids, stats):
    if character_class in {"sentinela", "errante"}:
        baseline = resolve_combat_stats(
            character_class, 45, "remanescente", selected_path=path
        )
        action_id = (
            SENTINEL_ART_IDS["golpe_de_guarda"]
            if character_class == "sentinela"
            else ERRANTE_ART_IDS["corte_veloz"]
        )
        state = _battle(character_class, path, talent_ids, stats, action_id)
        player = state.fighters["player"]
        assert player.stats.per == baseline.per + D(2)
        result = act(state, action_id, target_id=state.fighters["enemy"].id)
        event = next(item for item in reversed(result.events) if item.action == action_id)
        assert event.actor_entity_id == player.id and event.damage > 0
        return

    if character_class == "vigia":
        action_id = VIGIA_ART_IDS["disparo_preciso"]
        state = _battle(character_class, path, talent_ids, stats, action_id)
        owner, target = state.fighters["player"], state.fighters["enemy"]
        target.path_state["aim_from"] = {
            owner.id: {
                "stacks": 3,
                "remaining": 2,
                "applied_opportunity": owner.opportunity,
                "trigger": "direct",
            }
        }
        result = act(state, action_id, target_id=target.id)
        event = next(item for item in reversed(result.events) if item.action == action_id)
        assert event.path_crit_bonus == D(2)
        assert "vigia.ponto_fraco" in event.path_triggers
        return

    if character_class == "tecelao":
        action_id = CONJURADOR_ART_IDS["estilhaco_do_veu"]
        state = _battle(character_class, path, talent_ids, stats, action_id)
        target_id = state.fighters["enemy"].id
        state.dot_states[target_id] = [
            DotState("burn", 1, 2, D(10), state.fighters["player"].id, stack_cap=3)
        ]
        result = act(state, action_id, target_id=target_id)
        event = next(item for item in reversed(result.events) if item.action == action_id)
        assert event.path_power_multiplier == D("1.03")
        assert "tecelao.ruptura_profunda" in event.path_triggers
        return

    if character_class == "oraculo":
        action_id = ORACULO_ART_IDS["ruina_predita"]
        effect = Effect("enemy.attack.down", "attack", D("0.10"), 2, 0, kind="debuff")
        state = _battle(
            character_class, path, talent_ids, stats, action_id, enemy_effects=(effect,)
        )
        result = act(state, action_id, target_id=state.fighters["enemy"].id)
        event = next(item for item in reversed(result.events) if item.action == action_id)
        assert event.path_power_multiplier == D("1.03")
        assert "oraculo.fraqueza_prevista" in event.path_triggers
        return

    action_id = LUMINAR_ART_IDS["explosao_solar"]
    effect = Effect(
        "enemy.healing.down", "healing_received", D("0.20"), 2, 0, kind="debuff"
    )
    state = _battle(
        character_class, path, talent_ids, stats, action_id, enemy_effects=(effect,)
    )
    result = act(state, action_id, target_id=state.fighters["enemy"].id)
    event = next(item for item in reversed(result.events) if item.action == action_id)
    assert event.path_power_multiplier == D("1.03")
    assert "luminar.punicao_da_fraqueza" in event.path_triggers


@pytest.mark.asyncio
async def test_all_six_classes_acquire_persist_and_use_nv45_talents(database):
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    assert {character_class: len(ids) for character_class, ids in TIER45.items()} == {
        character_class: 3 for character_class in CLASS_ORDER
    }
    assert sum(len(ids) for ids in TIER45.values()) == 18
    assert talent_points_at_level(45) == 9
    assert talent_points_at_level(60) == 12

    for index, character_class in enumerate(CLASS_ORDER):
        actor = 884500 + index
        character_id, sessions = await _seed(database, actor, character_class, level=44)
        service = TalentService(sessions, "ocaso")
        view = await service.view(actor)
        assert view is not None and view.total_points == 8 and view.available_points == 8
        definitions = tuple(item for item in TALENTS_BY_CLASS[character_class] if item.level == 45)
        assert tuple(item.talent_id for item in definitions) == TIER45[character_class]
        with pytest.raises(TalentMutationRejected) as level_gate:
            await service.acquire(
                actor, definitions[0].talent_id, view.combat_configuration_version
            )
        assert level_gate.value.code == TalentMutationCode.LEVEL_REQUIRED

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            character.level = 45
        view = await service.view(actor)
        assert view is not None and view.total_points == 9 and view.available_points == 9
        wrong_class = next(name for name in CLASS_ORDER if name != character_class)
        wrong_id = TIER45[wrong_class][0]
        with pytest.raises(TalentMutationRejected) as wrong_class_error:
            await service.acquire(actor, wrong_id, view.combat_configuration_version)
        assert wrong_class_error.value.code == TalentMutationCode.WRONG_CLASS

        old_version = view.combat_configuration_version
        for definition in definitions:
            detail = render_talent_detail(view, definition)
            assert "Adquirir Talento" in [
                button.text
                for row in detail.keyboard.inline_keyboard
                for button in row
            ]
            acquired = await service.acquire(
                actor, definition.talent_id, view.combat_configuration_version
            )
            assert acquired is not None and acquired.changed
            view = acquired.view
        assert [choice.point_slot for choice in view.choices] == [1, 2, 3]
        assert {choice.talent_id for choice in view.choices} == set(TIER45[character_class])
        assert view.total_points == 9 and view.available_points == 6
        with pytest.raises(TalentMutationRejected) as duplicate:
            await service.acquire(
                actor, definitions[0].talent_id, view.combat_configuration_version
            )
        assert duplicate.value.code == TalentMutationCode.DUPLICATE_TALENT
        with pytest.raises(TalentMutationRejected) as stale:
            await service.acquire(actor, definitions[0].talent_id, old_version)
        assert stale.value.code == TalentMutationCode.STALE_CONFIGURATION

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
        talent_ids = tuple(item for _, item in restored.talent_choices)
        assert len(rows) == 3 and all(row.publicly_acquired for row in rows)
        assert talent_ids == TIER45[character_class]
        assert validate_active_talent_ids(character_class, 45, talent_ids) == talent_ids
        _observe_public_effect(character_class, PATHS[character_class], talent_ids, stats)


@pytest.mark.asyncio
async def test_nv60_can_acquire_nv45_and_nv55_within_point_budget(database):
    for index, character_class in enumerate(CLASS_ORDER):
        actor = 884520 + index
        _, sessions = await _seed(database, actor, character_class, level=60)
        service = TalentService(sessions, "ocaso")
        view = await service.view(actor)
        assert view is not None and view.available_points == 12
        acquired = await service.acquire(
            actor, TIER45[character_class][0], view.combat_configuration_version
        )
        assert acquired is not None and acquired.point_slot == 1
        assert acquired.view.available_points == 11
        nv55 = next(
            item.talent_id
            for item in TALENTS_BY_CLASS[character_class]
            if item.level == 55
        )
        nv55_result = await service.acquire(
            actor, nv55, acquired.view.combat_configuration_version
        )
        assert nv55_result is not None and nv55_result.point_slot == 2
        assert nv55_result.view.available_points == 10
        assert validate_active_talent_ids(character_class, 60, (nv55,)) == (nv55,)


@pytest.mark.asyncio
async def test_nv45_requires_an_unspent_point_but_no_lower_tier_prerequisite(database):
    actor = 884530
    _, sessions = await _seed(database, actor, "sentinela", level=45)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None and view.available_points == 9

    first_nv45 = await service.acquire(
        actor, TIER45["sentinela"][0], view.combat_configuration_version
    )
    assert first_nv45 is not None and first_nv45.point_slot == 1
    assert first_nv45.view.available_points == 8

    view = first_nv45.view
    for lower_tier_talent in TALENTS_BY_CLASS["sentinela"][:8]:
        acquired = await service.acquire(
            actor,
            lower_tier_talent.talent_id,
            view.combat_configuration_version,
        )
        assert acquired is not None
        view = acquired.view
    assert view.available_points == 0
    with pytest.raises(TalentMutationRejected) as exhausted:
        await service.acquire(
            actor, TIER45["sentinela"][1], view.combat_configuration_version
        )
    assert exhausted.value.code == TalentMutationCode.NO_POINTS


@pytest.mark.asyncio
async def test_nv45_talent_can_be_removed_by_normal_respec(database):
    actor = 884535
    _, sessions = await _seed(
        database, actor, "oraculo", level=45, crowns=10000
    )
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None and view.available_points == 9

    acquired = await service.acquire(
        actor, TIER45["oraculo"][0], view.combat_configuration_version
    )
    assert acquired is not None and acquired.view.available_points == 8

    result = await service.respec(actor, acquired.view.combat_configuration_version)
    assert result is not None and result.changed
    assert result.view.choices == ()
    assert result.view.available_points == 9
    assert result.view.crowns < 10000


@pytest.mark.asyncio
async def test_nv45_doctrine_and_service_reject_nv55_below_required_level(database):
    actor = 884540
    _, sessions = await _seed(database, actor, "luminar", level=45)
    doctrines = DoctrineService(sessions, "ocaso")
    created = await doctrines.create(actor, "Nv45 legal", 0)
    assert created is not None and created.doctrine_id is not None
    view = await doctrines.view(actor)
    assert view is not None
    doctrine = next(item for item in view.doctrines if item.doctrine_id == created.doctrine_id)
    picker = render_talent_choices(view, doctrine, 1)
    assert all(
        any(
            definition.name in button.text
            for row in picker.keyboard.inline_keyboard
            for button in row
        )
        for definition in TALENTS_BY_CLASS["luminar"]
        if definition.level == 45
    )
    talent_id = TIER45["luminar"][0]
    edited = await doctrines.update_component(
        actor,
        created.doctrine_id,
        0,
        view.configuration_version,
        "talents",
        [{"point_slot": 1, "talent_id": talent_id}],
    )
    assert edited is not None and edited.changed
    applied = await doctrines.apply(
        actor, created.doctrine_id, 1, edited.configuration_version
    )
    assert applied is not None and applied.changed
    public_view = await TalentService(sessions, "ocaso").view(actor)
    assert public_view is not None and public_view.choices[0].talent_id == talent_id

    current = await doctrines.view(actor)
    assert current is not None
    with pytest.raises(DoctrineRejected, match="invalid_talents"):
        await doctrines.update_component(
            actor,
            created.doctrine_id,
            1,
            current.configuration_version,
            "talents",
            [
                {
                    "point_slot": 1,
                    "talent_id": next(
                        item.talent_id
                        for item in TALENTS_BY_CLASS["luminar"]
                        if item.level == 55
                    ),
                }
            ],
        )


@pytest.mark.asyncio
async def test_nv45_concurrent_acquisition_cannot_spend_last_point_twice(database):
    actor = 884550
    _, sessions = await _seed(database, actor, "sentinela", level=45)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    for definition in TALENTS_BY_CLASS["sentinela"][:8]:
        acquired = await service.acquire(
            actor, definition.talent_id, view.combat_configuration_version
        )
        assert acquired is not None
        view = acquired.view
    assert view.available_points == 1
    outcomes = await asyncio.gather(
        *(
            service.acquire(actor, talent_id, view.combat_configuration_version)
            for talent_id in TIER45["sentinela"][:2]
        ),
        return_exceptions=True,
    )
    successes = [item for item in outcomes if not isinstance(item, Exception)]
    failures = [item for item in outcomes if isinstance(item, TalentMutationRejected)]
    assert len(successes) == 1 and len(failures) == 1
    assert failures[0].code == TalentMutationCode.STALE_CONFIGURATION
    saved = await service.view(actor)
    assert saved is not None and saved.available_points == 0 and len(saved.choices) == 9
    assert sum(item.talent_id in TIER45["sentinela"] for item in saved.choices) == 1


@pytest.mark.asyncio
async def test_nv45_acquisition_duplicate_and_failed_transaction_are_atomic(database, monkeypatch):
    actor = 884560
    character_id, sessions = await _seed(database, actor, "vigia", level=45)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    talent_id = TIER45["vigia"][0]
    outcomes = await asyncio.gather(
        service.acquire(actor, talent_id, view.combat_configuration_version),
        service.acquire(actor, talent_id, view.combat_configuration_version),
        return_exceptions=True,
    )
    assert sum(not isinstance(item, Exception) for item in outcomes) == 1
    failures = [item for item in outcomes if isinstance(item, TalentMutationRejected)]
    assert len(failures) == 1 and failures[0].code == TalentMutationCode.STALE_CONFIGURATION

    rollback_actor = 884561
    rollback_id, rollback_sessions = await _seed(
        database, rollback_actor, "luminar", level=45
    )
    rollback_service = TalentService(rollback_sessions, "ocaso")
    rollback_view = await rollback_service.view(rollback_actor)
    assert rollback_view is not None

    async def fail_after_choice_flush(_session, _character):
        raise RuntimeError("test Nv45 rollback")

    monkeypatch.setattr(
        TalentService, "_reconcile_hp", staticmethod(fail_after_choice_flush)
    )
    with pytest.raises(RuntimeError, match="test Nv45 rollback"):
        await rollback_service.acquire(
            rollback_actor,
            TIER45["luminar"][0],
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

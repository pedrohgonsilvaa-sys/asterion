"""Public PostgreSQL coverage for the Nv.15 Talent release."""

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
from asterion.bot.character_progression_ui import (
    render_talent_detail,
    render_talent_list,
    render_talent_root,
)
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
from asterion.domain.combat import (
    Action,
    Combat,
    DotState,
    Effect,
    Fighter,
    _aim_entry,
    act,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    direct_damage,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import (
    EquipmentConfigurationError,
    equipment_configuration_from_data,
)
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENTS_BY_CLASS,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterTalentChoice,
    GameActivity,
    WorldState,
)

D = Decimal
CLASS_ORDER = ("sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar")
PONTA = "talent.sentinela.ponta_revidada"
GUARDA = "talent.sentinela.guarda_preparada"
BRECHA_EXPOSTA = "talent.errante.brecha_exposta"
REFLEXO = "talent.errante.reflexo"
SANGUE_FRIO = "talent.errante.sangue_frio"
MIRA_ESTAVEL = "talent.vigia.mira_estavel"
TRAMA_DURADOURA = "talent.tecelao.trama_duradoura"
PRESSAGIO_CORTANTE = "talent.oraculo.pressagio_cortante"
SINAL_PERSISTENTE = "talent.oraculo.sinal_persistente"
JULGAMENTO_PRECISO = "talent.luminar.julgamento_preciso"
CONTRALUZ_PERSISTENTE = "talent.luminar.contraluz_persistente"


async def _seed_character(
    database,
    actor: int,
    character_class: str,
    *,
    level: int,
    location: str = "Estrada",
    crowns: int = 1000,
):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats(character_class, level, "remanescente")
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Hero{chr(ord('a') + actor % 26)}",
                race="remanescente",
                character_class=character_class,
                selected_path=None,
                stage="menu:ready",
                ruleset_version="gdd-1.4.9-baseline-1.0",
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
            WorldState(character_id=character_id, region="Terras do Ocaso", location=location)
        )
    return character_id, sessions


async def _acquire_and_load(database, actor: int, character_class: str, talent_ids, *, path=None):
    character_id, sessions = await _seed_character(
        database, actor, character_class, level=34
    )
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    for talent_id in talent_ids:
        mutation = await service.acquire(
            actor, talent_id, view.combat_configuration_version
        )
        assert mutation is not None and mutation.changed
        view = mutation.view
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.selected_path = path
        snapshot = await load_equipment_configuration(session, character)
        stats = resolve_character_combat_stats(character, snapshot)
        loaded = (
            character.character_class,
            character.level,
            character.race,
            character.selected_path,
            tuple(talent_id for _, talent_id in snapshot.talent_choices),
            snapshot,
            stats,
        )
    return character_id, sessions, loaded


def _battle(
    character_class: str,
    level: int,
    race: str,
    path: str | None,
    talent_ids: tuple[str, ...],
    stats: CombatStats,
    arts: tuple[str, ...],
    *,
    enemy_effects: tuple[Effect, ...] = (),
    enemy_dots: tuple[DotState, ...] = (),
    enemy_takes_turn: bool = False,
    player_hp: D | None = None,
) -> Combat:
    actor = Fighter(
        "player.entity",
        "Talent Hero",
        level,
        stats,
        stats.hp if player_hp is None else player_hp,
        race=race,
        character_class=character_class,
        selected_path=path,
        talent_ids=talent_ids,
        side="player",
        takes_turn=True,
    )
    enemy_stats = CombatStats(D(10000), D(100), D(10), D(0), evasion=D(0))
    enemy = Fighter(
        "enemy.entity",
        "Enemy",
        level,
        enemy_stats,
        enemy_stats.hp,
        effects=list(enemy_effects),
        side="enemy",
        takes_turn=enemy_takes_turn,
        required_for_victory=False,
    )
    player_actions = class_player_actions(character_class, arts, path)
    player_actions.setdefault("attack", Action("attack", "Ataque Básico", D(1)))
    enemy_actions = {
        "enemy.hit": Action("enemy.hit", "Golpe inimigo", D("0.30")),
        "enemy.wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self"),
    }
    state = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        {"player": actor, "enemy": enemy},
        player_actions,
        enemy_actions,
        ("enemy.hit",) if enemy_takes_turn else ("enemy.wait",),
    )
    if enemy_dots:
        state.dot_states[enemy.id] = list(enemy_dots)
    return start_combat(state)


def _event(state: Combat, action_id: str):
    return next(
        event
        for event in reversed(state.events)
        if event.actor_entity_id == state.fighters["player"].id
        and event.action == action_id
    )


def _combat_reconnect(state: Combat) -> Combat:
    return decode(encode(state), state.id, state.ruleset, state.version)


@pytest.mark.asyncio
async def test_all_six_classes_can_acquire_all_nv15_talents_and_reload_public_snapshots(database):
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15})
    assert sum(
        talent.level == 15
        for talents in TALENTS_BY_CLASS.values()
        for talent in talents
    ) == 18

    for index, character_class in enumerate(CLASS_ORDER):
        actor = 841500 + index
        character_id, sessions = await _seed_character(
            database, actor, character_class, level=14
        )
        service = TalentService(sessions, "ocaso")
        view = await service.view(actor)
        assert view is not None and view.total_points == 2
        tier15 = TALENTS_BY_CLASS[character_class][3:6]
        locked_detail = render_talent_detail(view, tier15[0])
        assert "Requer Nv.15" in locked_detail.text
        assert "Adquirir Talento" not in [
            button.text
            for row in locked_detail.keyboard.inline_keyboard
            for button in row
        ]
        with pytest.raises(TalentMutationRejected) as under_level:
            await service.acquire(actor, tier15[0].talent_id, view.combat_configuration_version)
        assert under_level.value.code == TalentMutationCode.LEVEL_REQUIRED

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            character.level = 15
        view = await service.view(actor)
        assert view is not None and view.total_points == 3 and view.available_points == 3
        assert "Disponíveis · 3" in render_talent_root(view).text
        for talent in tier15:
            detail = render_talent_detail(view, talent)
            assert "Adquirir Talento" in [
                button.text
                for row in detail.keyboard.inline_keyboard
                for button in row
            ]
        for talent in tier15:
            result = await service.acquire(
                actor, talent.talent_id, view.combat_configuration_version
            )
            assert result is not None and result.changed
            view = result.view
        assert view.total_points == 3 and view.available_points == 0
        assert [choice.point_slot for choice in view.choices] == [1, 2, 3]
        assert {choice.talent_id for choice in view.choices} == {
            talent.talent_id for talent in tier15
        }
        assert validate_active_talent_ids(
            character_class, 15, [choice.talent_id for choice in view.choices]
        )

        listing = render_talent_list(view)
        for talent in tier15:
            assert f"{talent.name} · Adquirido" in listing.text
        future = next(talent for talent in TALENTS_BY_CLASS[character_class] if talent.level == 25)
        assert f"{future.name} · Requer Nv.25" in listing.text
        detail = render_talent_detail(view, future)
        assert "Adquirir Talento" not in [
            button.text
            for row in detail.keyboard.inline_keyboard
            for button in row
        ]

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            snapshot = await load_equipment_configuration(session, character)
            stats = resolve_character_combat_stats(character, snapshot)
            persisted_rows = list(
                (
                    await session.scalars(
                        select(CharacterTalentChoice)
                        .where(CharacterTalentChoice.character_id == character_id)
                        .order_by(CharacterTalentChoice.point_slot)
                    )
                ).all()
            )
        restored = equipment_configuration_from_data(snapshot.to_data("gdd-1.6.0"))
        restored_ids = tuple(talent_id for _, talent_id in restored.talent_choices)
        assert len(persisted_rows) == 3
        assert stats == resolve_combat_stats(
            character_class, 15, "remanescente", talent_ids=restored_ids
        )
        static_ids = tuple(
            talent.talent_id
            for talent in tier15
            if talent.attack_percent
            or talent.hp_percent
            or talent.defense_percent
            or talent.agility_percent
            or talent.per_points
            or talent.crit_points
            or talent.evasion_points
            or talent.block_points
        )
        static_stats = resolve_combat_stats(
            character_class, 15, "remanescente", talent_ids=static_ids
        )
        assert stats == static_stats
        baseline = resolve_combat_stats(character_class, 15, "remanescente")
        assert stats.defense >= baseline.defense
        assert stats.crit == baseline.crit + sum(
            (talent.crit_points for talent in tier15), D(0)
        )
        assert stats.evasion == baseline.evasion + sum(
            (talent.evasion_points for talent in tier15), D(0)
        )

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            character.level = 60
        future_view = await service.view(actor)
        assert future_view is not None and future_view.total_points == 12
        assert future_view.available_points == 9
        future_id = next(
            talent.talent_id
            for talent in TALENTS_BY_CLASS[character_class]
            if talent.level == 25
        )
        with pytest.raises(TalentMutationRejected) as closed:
            await service.acquire(actor, future_id, future_view.combat_configuration_version)
        assert closed.value.code == TalentMutationCode.TIER_NOT_IMPLEMENTED


@pytest.mark.asyncio
async def test_publicly_acquired_sentinela_talents_drive_retalie_and_guard_barrier(database):
    _, sessions, loaded = await _acquire_and_load(
        database, 841520, "sentinela", (PONTA,), path="devastador"
    )
    cls, level, race, path, ids, snapshot, stats = loaded
    state = _battle(cls, level, race, path, ids, stats, (SENTINEL_ART_IDS["golpe_de_rechaco"],))
    state = _combat_reconnect(state)
    actor = state.fighters["player"]
    actor.retaliation_charges = 1
    actor.retaliation_remaining = 1
    actor.retaliation_activation_id = "public:retaliation"
    actor.retaliation_source_type = "defender"
    actor.retaliation_source_event_id = "public:defender"
    actor.retaliation_source_actor_id = state.fighters["enemy"].id
    result = act(state, SENTINEL_ART_IDS["golpe_de_rechaco"], target_id="enemy.entity")
    retribution_event = _event(result, SENTINEL_ART_IDS["golpe_de_rechaco"])
    assert retribution_event.path_per_bonus == D(10)  # O bônus de +4 entra no cálculo.
    assert retribution_event.calculated_damage == direct_damage(
        stats.attack,
        D("1.45"),
        state.fighters["enemy"].stats.defense,
        level,
        penetration=D(14),
    )
    assert result.fighters["player"].retaliation_charges == 0

    _, _, guard_loaded = await _acquire_and_load(
        database, 841521, "sentinela", (GUARDA,), path="bastiao"
    )
    cls, level, race, path, ids, _, stats = guard_loaded
    guarding = _battle(
        cls,
        level,
        race,
        path,
        ids,
        stats,
        (SENTINEL_ART_IDS["muralha_breve"],),
        enemy_takes_turn=True,
    )
    guarding = _combat_reconnect(guarding)
    guarded = act(guarding, "defend")
    incoming = next(
        event
        for event in guarded.events
        if event.actor_entity_id == guarded.fighters["enemy"].id
        and event.target == guarded.fighters["player"].id
    )
    assert incoming.defender_prevented_damage > 0
    shielded = act(guarded, SENTINEL_ART_IDS["muralha_breve"])
    barrier_event = _event(shielded, SENTINEL_ART_IDS["muralha_breve"])
    assert barrier_event.barrier_power_multiplier == D("1.06") * D("1.10")
    assert "sentinela.guarda_preparada" in barrier_event.path_triggers


@pytest.mark.asyncio
async def test_public_errante_brecha_exposta_and_sangue_frio_use_live_combat_triggers(database):
    _, _, loaded = await _acquire_and_load(
        database, 841522, "errante", (BRECHA_EXPOSTA,), path="carrasco"
    )
    cls, level, race, path, ids, _, stats = loaded
    negative = Effect("test.debuff", "defense", D("0.10"), 2, 0, kind="debuff")
    state = _battle(
        cls,
        level,
        race,
        path,
        ids,
        stats,
        (ERRANTE_ART_IDS["brecha_mortal"],),
        enemy_effects=(negative,),
    )
    state = _combat_reconnect(state)
    result = act(state, ERRANTE_ART_IDS["brecha_mortal"], target_id="enemy.entity")
    assert _event(result, ERRANTE_ART_IDS["brecha_mortal"]).path_per_bonus == D(14)

    _, _, loaded = await _acquire_and_load(
        database, 841523, "errante", (SANGUE_FRIO,)
    )
    cls, level, race, path, ids, _, stats = loaded
    stats = replace(stats, evasion=D(100))
    state = _battle(cls, level, race, path, ids, stats, (), enemy_takes_turn=True)
    state = _combat_reconnect(state)
    dodged = act(state, "defend")
    dodge_event = next(
        event
        for event in dodged.events
        if event.actor_entity_id == dodged.fighters["enemy"].id
        and event.target == dodged.fighters["player"].id
        and event.dodged
    )
    assert "errante.sangue_frio_preparado" in dodge_event.path_triggers
    dodged.fighters["enemy"].takes_turn = False
    restored = act(dodged, "attack", target_id="enemy.entity")
    direct_event = _event(restored, "attack")
    assert "errante.sangue_frio.crit" in direct_event.actor_effect_ids
    assert (
        "errante_sangue_frio_crit",
        "player.entity",
        1,
        0,
    ) in direct_event.class_resource_changes
    assert "errante_sangue_frio_crit" not in restored.fighters["player"].path_state


@pytest.mark.asyncio
async def test_public_vigia_mira_estavel_and_tecelao_trama_duradoura_drive_real_actions(database):
    _, _, loaded = await _acquire_and_load(
        database, 841524, "vigia", (MIRA_ESTAVEL,), path="atirador"
    )
    cls, level, race, path, ids, snapshot, stats = loaded
    state = _battle(cls, level, race, path, ids, stats, (VIGIA_ART_IDS["voleio"],))
    state = _combat_reconnect(state)
    result = act(state, VIGIA_ART_IDS["voleio"], target_id="enemy.entity")
    aim = _aim_entry(result.fighters["enemy"], result.fighters["player"])
    assert aim is not None and aim["remaining"] == 3
    assert aim["stacks"] == 1

    _, _, loaded = await _acquire_and_load(
        database, 841525, "tecelao", (TRAMA_DURADOURA,), path="conjurador"
    )
    cls, level, race, path, ids, _, stats = loaded
    state = _battle(cls, level, race, path, ids, stats, (TECELAO_ART_IDS["fio_cortante"],))
    state = _combat_reconnect(state)
    result = act(state, TECELAO_ART_IDS["fio_cortante"], target_id="enemy.entity")
    trama = result.fighters["player"].path_state["trama_state"]
    assert trama["remaining"] == 3
    assert trama["origin_art"] == TECELAO_ART_IDS["fio_cortante"]


@pytest.mark.asyncio
async def test_public_oraculo_marks_and_luminar_state_survive_the_real_consuming_art(database):
    _, _, loaded = await _acquire_and_load(
        database,
        841526,
        "oraculo",
        (PRESSAGIO_CORTANTE, SINAL_PERSISTENTE),
        path="agoureiro",
    )
    cls, level, race, path, ids, _, stats = loaded
    state = _battle(
        cls,
        level,
        race,
        path,
        ids,
        stats,
        (ORACULO_ART_IDS["sinal_funesto"], ORACULO_ART_IDS["selo_da_queda"]),
    )
    state = _combat_reconnect(state)
    marked = act(state, ORACULO_ART_IDS["sinal_funesto"], target_id="enemy.entity")
    omen = marked.fighters["player"].path_state["omen_offensive"]["enemy.entity"]
    assert omen["remaining"] == 3
    consumed = act(marked, ORACULO_ART_IDS["selo_da_queda"], target_id="enemy.entity")
    seal_event = _event(consumed, ORACULO_ART_IDS["selo_da_queda"])
    assert seal_event.path_per_bonus == D(2)
    assert consumed.fighters["player"].path_state["omen_offensive"]["enemy.entity"][
        "remaining"
    ] == 3

    _, _, loaded = await _acquire_and_load(
        database,
        841527,
        "luminar",
        (JULGAMENTO_PRECISO, CONTRALUZ_PERSISTENTE),
    )
    cls, level, race, path, ids, _, stats = loaded
    state = _battle(
        cls,
        level,
        race,
        path,
        ids,
        stats,
        (LUMINAR_ART_IDS["luz_restauradora"], LUMINAR_ART_IDS["explosao_solar"]),
        player_hp=stats.hp / D(2),
    )
    state = _combat_reconnect(state)
    supported = act(state, LUMINAR_ART_IDS["luz_restauradora"], target_id="player.entity")
    luminar_state = supported.fighters["player"].path_state["luminar_state"]
    assert luminar_state["kind"] == "julgamento" and luminar_state["remaining"] == 3
    solar = act(supported, LUMINAR_ART_IDS["explosao_solar"])
    solar_event = _event(solar, LUMINAR_ART_IDS["explosao_solar"])
    assert solar_event.path_crit_bonus == D(2)
    assert solar_event.path_power_multiplier == D("1.10")
    assert "luminar_state" not in solar.fighters["player"].path_state


@pytest.mark.asyncio
async def test_doctrine_editor_accepts_nv15_without_slot_prerequisites_and_apply_is_atomic(
    database,
):
    actor = 841528
    character_id, sessions = await _seed_character(
        database, actor, "sentinela", level=15, crowns=0, location="Estrada"
    )
    service = DoctrineService(sessions, "ocaso")
    created = await service.create(actor, "Nv15 legal", 0)
    assert created is not None and created.doctrine_id is not None
    collection = await service.view(actor)
    assert collection is not None
    doctrine = next(
        item for item in collection.doctrines if item.doctrine_id == created.doctrine_id
    )
    first = TALENTS_BY_CLASS["sentinela"][3]
    screen = render_talent_choices(collection, doctrine, 1)
    assert any(
        first.name in button.text
        for row in screen.keyboard.inline_keyboard
        for button in row
    )
    assert not any(
        "Nv.25" in button.text
        for row in screen.keyboard.inline_keyboard
        for button in row
    )
    assert "ainda não está disponível" in render_talent_choices(collection, doctrine, 4).text

    choices = [
        {"point_slot": slot, "talent_id": talent.talent_id}
        for slot, talent in enumerate(TALENTS_BY_CLASS["sentinela"][3:6], 1)
    ]
    edited = await service.update_component(
        actor,
        created.doctrine_id,
        0,
        collection.configuration_version,
        "talents",
        choices,
    )
    assert edited is not None and edited.changed
    applied = await service.apply(
        actor, created.doctrine_id, 1, collection.configuration_version
    )
    assert applied is not None and applied.changed
    async with sessions() as session:
        rows = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice)
                    .where(CharacterTalentChoice.character_id == character_id)
                    .order_by(CharacterTalentChoice.point_slot)
                )
            ).all()
        )
        assert [(row.point_slot, row.talent_id) for row in rows] == [
            (item["point_slot"], item["talent_id"]) for item in choices
        ]
    with pytest.raises(DoctrineRejected, match="invalid_talents"):
        await service.update_component(
            actor,
            created.doctrine_id,
            1,
            applied.configuration_version,
            "talents",
            [{"point_slot": 1, "talent_id": TALENTS_BY_CLASS["sentinela"][6].talent_id}],
        )


@pytest.mark.asyncio
async def test_same_last_point_cannot_be_spent_concurrently_by_two_nv15_talents(database):
    actor = 841529
    _, sessions = await _seed_character(database, actor, "vigia", level=15)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    for talent in TALENTS_BY_CLASS["vigia"][3:5]:
        result = await service.acquire(actor, talent.talent_id, view.combat_configuration_version)
        assert result is not None
        view = result.view
    candidates = (TALENTS_BY_CLASS["vigia"][5], TALENTS_BY_CLASS["vigia"][0])
    results = await asyncio.gather(
        *(
            service.acquire(actor, talent.talent_id, view.combat_configuration_version)
            for talent in candidates
        ),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, Exception) for result in results) == 1
    failures = [result for result in results if isinstance(result, TalentMutationRejected)]
    assert len(failures) == 1 and failures[0].code == TalentMutationCode.STALE_CONFIGURATION
    final = await service.view(actor)
    assert final is not None and final.available_points == 0 and len(final.choices) == 3


@pytest.mark.asyncio
async def test_talent_acquisition_transaction_rolls_back_after_persisting_choice_before_commit(
    database, monkeypatch
):
    actor = 841530
    character_id, sessions = await _seed_character(database, actor, "luminar", level=15)
    service = TalentService(sessions, "ocaso")

    async def fail_reconciliation(_service, _session, _character):
        raise RuntimeError("injected failure after choice flush")

    monkeypatch.setattr(TalentService, "_reconcile_hp", fail_reconciliation)
    with pytest.raises(RuntimeError, match="after choice flush"):
        await service.acquire(actor, TALENTS_BY_CLASS["luminar"][3].talent_id, 0)
    async with sessions() as session:
        character = await session.get(Character, character_id)
        rows = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice).where(
                        CharacterTalentChoice.character_id == character_id
                    )
                )
            ).all()
        )
    assert rows == []
    assert character is not None and character.combat_configuration_version == 0


@pytest.mark.asyncio
async def test_active_activity_lock_and_invalid_persisted_talent_prevent_unlock_bypass(database):
    actor = 841531
    character_id, sessions = await _seed_character(database, actor, "oraculo", level=15)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    async with sessions.begin() as session:
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=character_id,
                content_id="talent.unlock.lock",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    with pytest.raises(TalentMutationRejected) as locked:
        await service.acquire(actor, TALENTS_BY_CLASS["oraculo"][3].talent_id, 0)
    assert locked.value.code == TalentMutationCode.FOREGROUND

    _, other_sessions = database
    async with other_sessions.begin() as session:
        session.add(
            CharacterTalentChoice(
                character_id=character_id,
                point_slot=1,
                talent_id=TALENTS_BY_CLASS["oraculo"][3].talent_id,
            )
        )
        character = await session.get(Character, character_id)
        character.level = 14
    with pytest.raises(TalentMutationRejected) as invalid:
        await service.view(actor)
    assert invalid.value.code == TalentMutationCode.INVALID_CURRENT_CONFIGURATION
    async with sessions() as session:
        row = await session.scalar(
            select(CharacterTalentChoice).where(
                CharacterTalentChoice.character_id == character_id
            )
        )
        assert row is not None and row.talent_id == TALENTS_BY_CLASS["oraculo"][3].talent_id
        character = await session.get(Character, character_id)
        with pytest.raises(EquipmentConfigurationError):
            await load_equipment_configuration(session, character)

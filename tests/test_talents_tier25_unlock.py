"""Public acquisition, persistence, composition, and combat coverage for Nv.25."""

from dataclasses import replace
from decimal import ROUND_FLOOR, Decimal
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
    ERRANTE_ART_IDS,
    LUMINAR_ART_IDS,
    ORACULO_ART_IDS,
    TECELAO_ART_IDS,
    VIGIA_ART_IDS,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Combat,
    Effect,
    Fighter,
    _aim_entry,
    act,
    start_combat,
)
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
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterTalentChoice,
    WorldState,
)

D = Decimal
CLASS_ORDER = ("sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar")
TIER25 = {
    character_class: tuple(
        talent.talent_id
        for talent in talents
        if talent.level == 25
    )
    for character_class, talents in TALENTS_BY_CLASS.items()
}


async def _seed(database, actor: int, character_class: str, *, level: int, crowns: int = 1000,
                location: str = "Estrada"):
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
                name=f"Talent{chr(ord('a') + actor % 26)}",
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
    character_id, sessions = await _seed(database, actor, character_class, level=34)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    for talent_id in talent_ids:
        result = await service.acquire(actor, talent_id, view.combat_configuration_version)
        assert result is not None and result.changed
        view = result.view
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


def _battle(character_class, level, race, path, talent_ids, stats, arts, *,
            enemy_effects=(), enemy_takes_turn=False, player_hp=None, combat_id=None):
    player = Fighter(
        "player.entity",
        "Public Talent User",
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
        combat_id or uuid4(),
        CURRENT_COMBAT_RULESET,
        {"player": player, "enemy": enemy},
        player_actions,
        enemy_actions,
        ("enemy.hit",) if enemy_takes_turn else ("enemy.wait",),
    )
    state.fighters["enemy"].effects = list(enemy_effects)
    return start_combat(state)


def _event(state, action_id: str):
    return next(
        event
        for event in reversed(state.events)
        if event.actor_entity_id == "player.entity" and event.action == action_id
    )


def _reconnect(state):
    return decode(encode(state), state.id, state.ruleset, state.version)


@pytest.mark.parametrize(
    ("level", "points"),
    ((4, 0), (5, 1), (10, 2), (14, 2), (15, 3), (20, 4), (24, 4),
     (25, 5), (30, 6), (35, 7), (40, 8), (45, 9), (50, 10), (55, 11), (60, 12)),
)
def test_canonical_talent_point_milestones_remain_unchanged(level, points):
    assert talent_points_at_level(level) == points


@pytest.mark.asyncio
async def test_all_six_classes_acquire_nv25_nv35_nv45_and_reload_public_snapshots(database):
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    assert sum(map(len, TIER25.values())) == 18
    assert all(len(talent_ids) == 3 for talent_ids in TIER25.values())
    static_modifiers = {
        "errante": (("crit", D(2)), ("defense", D("1.02"))),
        "vigia": ("per", D(2)),
        "tecelao": ("per", D(2)),
        "oraculo": ("crit", D(2)),
        "luminar": ("per", D(2)),
    }

    for index, character_class in enumerate(CLASS_ORDER):
        actor = 841700 + index
        character_id, sessions = await _seed(database, actor, character_class, level=24)
        service = TalentService(sessions, "ocaso")
        view = await service.view(actor)
        assert view is not None and view.total_points == 4 and view.available_points == 4
        candidates = tuple(t for t in TALENTS_BY_CLASS[character_class] if t.level == 25)
        assert tuple(t.talent_id for t in candidates) == TIER25[character_class]
        detail = render_talent_detail(view, candidates[0])
        assert "Requer Nv.25" in detail.text
        with pytest.raises(TalentMutationRejected) as under_level:
            await service.acquire(actor, candidates[0].talent_id, view.combat_configuration_version)
        assert under_level.value.code == TalentMutationCode.LEVEL_REQUIRED

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            character.level = 25
        view = await service.view(actor)
        assert view is not None and view.total_points == 5 and view.available_points == 5
        other_class = next(value for value in CLASS_ORDER if value != character_class)
        wrong_id = TIER25[other_class][0]
        with pytest.raises(TalentMutationRejected) as wrong_class:
            await service.acquire(actor, wrong_id, view.combat_configuration_version)
        assert wrong_class.value.code == TalentMutationCode.WRONG_CLASS

        for candidate in candidates:
            screen = render_talent_detail(view, candidate)
            assert "Adquirir Talento" in [
                button.text
                for row in screen.keyboard.inline_keyboard
                for button in row
            ]
        for candidate in candidates:
            result = await service.acquire(
                actor, candidate.talent_id, view.combat_configuration_version
            )
            assert result is not None and result.changed
            view = result.view
        assert [choice.point_slot for choice in view.choices] == [1, 2, 3]
        assert {choice.talent_id for choice in view.choices} == set(TIER25[character_class])
        assert view.total_points == 5 and view.available_points == 2
        with pytest.raises(TalentMutationRejected) as duplicate:
            await service.acquire(actor, candidates[0].talent_id, view.combat_configuration_version)
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
        reloaded = equipment_configuration_from_data(snapshot.to_data("gdd-1.6.0"))
        active_ids = tuple(talent_id for _, talent_id in reloaded.talent_choices)
        assert len(rows) == 3
        assert validate_active_talent_ids(character_class, 25, active_ids) == active_ids
        assert stats == resolve_combat_stats(
            character_class, 25, "remanescente", talent_ids=active_ids
        )
        baseline = resolve_combat_stats(character_class, 25, "remanescente")
        if character_class in static_modifiers:
            modifiers = static_modifiers[character_class]
            if isinstance(modifiers[0], str):
                modifiers = (modifiers,)
            for stat_name, amount in modifiers:
                if stat_name in {"crit", "per"}:
                    assert getattr(stats, stat_name) == getattr(baseline, stat_name) + amount
                else:
                    assert stats.defense == (baseline.defense * amount).to_integral_value(
                        rounding=ROUND_FLOOR
                    )

        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            character.level = 60
        high_level = await service.view(actor)
        assert high_level is not None and high_level.total_points == 12
        assert high_level.available_points == 9
        tier35 = next(t for t in TALENTS_BY_CLASS[character_class] if t.level == 35)
        detail = render_talent_detail(high_level, tier35)
        assert "Adquirir Talento" in [
            button.text
            for row in detail.keyboard.inline_keyboard
            for button in row
        ]
        acquired35 = await service.acquire(
            actor, tier35.talent_id, high_level.combat_configuration_version
        )
        assert acquired35 is not None and acquired35.point_slot == 4
        high_level = acquired35.view
        assert high_level.available_points == 8
        tier45 = next(t for t in TALENTS_BY_CLASS[character_class] if t.level == 45)
        tier45_detail = render_talent_detail(high_level, tier45)
        assert "Adquirir Talento" in [
            button.text
            for row in tier45_detail.keyboard.inline_keyboard
            for button in row
        ]
        acquired45 = await service.acquire(
            actor, tier45.talent_id, high_level.combat_configuration_version
        )
        assert acquired45 is not None and acquired45.point_slot == 5
        high_level = acquired45.view
        assert high_level.available_points == 7

        future = next(t for t in TALENTS_BY_CLASS[character_class] if t.level == 55)
        future_detail = render_talent_detail(high_level, future)
        assert "Nv.55" in future_detail.text
        assert "Adquirir Talento" in [
            button.text
            for row in future_detail.keyboard.inline_keyboard
            for button in row
        ]
        acquired55 = await service.acquire(
            actor, future.talent_id, high_level.combat_configuration_version
        )
        assert acquired55 is not None and acquired55.point_slot == 6
        assert acquired55.view.available_points == 6


@pytest.mark.asyncio
async def test_publicly_acquired_sentinela_tier25_effects_run_in_combat(database):
    _, _, loaded = await _acquire_and_load(
        database, 841720, "sentinela", TIER25["sentinela"], path="bastiao"
    )
    cls, level, race, path, ids, _, stats = loaded
    defense_down = Effect("public.defense.down", "defense", D("0.10"), 2, 0, kind="debuff")
    pressure_state = _battle(
        cls, level, race, path, ids, stats, (), enemy_effects=(defense_down,)
    )
    pressure_result = act(pressure_state, "attack", target_id="enemy.entity")
    pressure_event = _event(pressure_result, "attack")
    assert pressure_event.path_power_multiplier == D("1.03")
    assert "sentinela.pressao_de_fissuras" in pressure_event.path_triggers

    incoming_state = _battle(
        cls, level, race, path, ids, stats, (), enemy_takes_turn=True
    )
    incoming_state.fighters["player"].stats = replace(
        incoming_state.fighters["player"].stats, defense=D(0)
    )
    incoming_state.fighters["enemy"].stats = replace(
        incoming_state.fighters["enemy"].stats, attack=D(5000)
    )
    incoming_result = act(incoming_state, "defend")
    incoming = next(
        event
        for event in incoming_result.events
        if event.actor_entity_id == "enemy.entity" and event.target == "player.entity"
    )
    player = incoming_result.fighters["player"]
    assert incoming.defender_prevented_damage > 0
    assert incoming.effective_damage >= player.stats.hp * D("0.08")
    assert player.retaliation_charges == 1 and player.retaliation_remaining == 2
    assert any(
        effect.id == "class_mechanic.sentinela.firme_sob_impacto.defense"
        and effect.magnitude == D("0.05")
        and effect.remaining == 1
        for effect in player.effects
    )
    restored = _reconnect(incoming_result)
    assert restored.fighters["player"].retaliation_remaining == 2


@pytest.mark.asyncio
async def test_publicly_acquired_errante_passos_activates_only_after_negative_application(database):
    _, _, loaded = await _acquire_and_load(
        database, 841721, "errante", TIER25["errante"], path="sabotador"
    )
    cls, level, race, path, ids, _, stats = loaded
    state = _battle(
        cls, level, race, path, ids, stats, (ERRANTE_ART_IDS["ferida_profunda"],)
    )
    state = _reconnect(state)
    result = act(state, ERRANTE_ART_IDS["ferida_profunda"], target_id="enemy.entity")
    event = _event(result, ERRANTE_ART_IDS["ferida_profunda"])
    enemy = result.fighters["enemy"]
    assert any(dot.kind == "bleed" for dot in result.dot_states[enemy.id])
    buff = next(
        effect for effect in result.fighters["player"].effects
        if effect.id == "class_mechanic.errante.passos_da_sombra.agility"
    )
    assert buff.magnitude == D("0.05") and buff.remaining == 1
    assert "errante.passos_da_sombra" in event.path_triggers
    assert buff.id not in event.actor_effect_ids


@pytest.mark.asyncio
async def test_publicly_acquired_vigia_tier25_effects_are_per_combat_and_per_target(database):
    _, _, loaded = await _acquire_and_load(
        database, 841722, "vigia", TIER25["vigia"], path="atirador"
    )
    cls, level, race, path, ids, _, stats = loaded
    # Mesmo id de combate nos dois: o sorteio de crítico é idêntico e só o talento difere.
    shared_id = uuid4()
    protected = _battle(
        cls, level, race, path, ids, stats, (), enemy_takes_turn=True, combat_id=shared_id
    )
    baseline = _battle(
        cls, level, race, path, (), stats, (), enemy_takes_turn=True, combat_id=shared_id
    )
    protected_result = act(protected, "defend")
    baseline_result = act(baseline, "defend")
    protected_hit = next(
        event for event in protected_result.events
        if event.actor_entity_id == "enemy.entity" and event.target == "player.entity"
    )
    baseline_hit = next(
        event for event in baseline_result.events
        if event.actor_entity_id == "enemy.entity" and event.target == "player.entity"
    )
    assert protected_hit.calculated_damage < baseline_hit.calculated_damage
    assert protected_result.fighters["player"].path_state["vigia_antecipacao_used"] is True
    restored_protection = _reconnect(protected_result)
    assert restored_protection.fighters["player"].path_state["vigia_antecipacao_used"] is True

    aim_state = _battle(
        cls, level, race, path, ids, stats, (VIGIA_ART_IDS["disparo_preciso"],)
    )
    aim_state = _reconnect(aim_state)
    aimed = act(aim_state, VIGIA_ART_IDS["disparo_preciso"], target_id="enemy.entity")
    aim = _aim_entry(aimed.fighters["enemy"], aimed.fighters["player"])
    assert aim is not None and aim["stacks"] == 2
    assert aimed.fighters["player"].path_state["aim_acquisition_used"]["enemy.entity"] is True
    restored_aim = _reconnect(aimed)
    assert (
        restored_aim.fighters["player"].path_state["aim_acquisition_used"]["enemy.entity"]
        is True
    )


@pytest.mark.asyncio
async def test_publicly_acquired_tecelao_effects_follow_barrier_and_trama_consumption(database):
    _, _, loaded = await _acquire_and_load(
        database, 841723, "tecelao", TIER25["tecelao"], path="conjurador"
    )
    cls, level, race, path, ids, _, stats = loaded
    state = _battle(
        cls,
        level,
        race,
        path,
        ids,
        stats,
        (TECELAO_ART_IDS["fio_cortante"], TECELAO_ART_IDS["veu_entrelacado"]),
    )
    generated = act(state, TECELAO_ART_IDS["fio_cortante"], target_id="enemy.entity")
    assert generated.fighters["player"].path_state["trama_state"]["origin_art"] == (
        TECELAO_ART_IDS["fio_cortante"]
    )
    assert not any(
        effect.id == "class_mechanic.tecelao.alternancia_fluida.agility"
        for effect in generated.fighters["player"].effects
    )
    generated = _reconnect(generated)
    consumed = act(
        generated, TECELAO_ART_IDS["veu_entrelacado"], target_id="player.entity"
    )
    event = _event(consumed, TECELAO_ART_IDS["veu_entrelacado"])
    expected_barrier = (
        stats.attack * D("0.90") * D("1.06") * D("1.05")
    ).to_integral_value(rounding=ROUND_FLOOR)
    actor = consumed.fighters["player"]
    assert event.barrier_value == expected_barrier
    assert "trama_state" not in actor.path_state
    assert event.path_triggers.count("tecelao.alternancia_fluida") == 1
    buff = next(
        effect for effect in actor.effects
        if effect.id == "class_mechanic.tecelao.alternancia_fluida.agility"
    )
    assert buff.magnitude == D("0.05") and buff.remaining == 1
    assert actor.stat("agility") == actor.stats.agility * D("1.05")
    restored = _reconnect(consumed)
    assert restored.fighters["player"].barrier == actor.barrier
    assert restored.fighters["player"].stat("agility") == actor.stat("agility")


@pytest.mark.asyncio
async def test_publicly_acquired_oraculo_tier25_effects_track_barrier_and_offensive_omen(
    database,
):
    _, _, loaded = await _acquire_and_load(
        database, 841724, "oraculo", TIER25["oraculo"], path="agoureiro"
    )
    cls, level, race, path, ids, _, stats = loaded
    state = _battle(
        cls,
        level,
        race,
        path,
        ids,
        stats,
        (ORACULO_ART_IDS["veu_premonitorio"], ORACULO_ART_IDS["sinal_funesto"]),
    )
    state = _reconnect(state)
    shielded = act(
        state, ORACULO_ART_IDS["veu_premonitorio"], target_id="player.entity"
    )
    oracle = shielded.fighters["player"]
    assert oracle.barrier > 0
    assert oracle.stat("defense") == oracle.stats.defense * D("1.05")
    shielded = _reconnect(shielded)
    assert shielded.fighters["player"].stat("defense") == oracle.stat("defense")

    marked = act(
        shielded, ORACULO_ART_IDS["sinal_funesto"], target_id="enemy.entity"
    )
    event = _event(marked, ORACULO_ART_IDS["sinal_funesto"])
    omen = marked.fighters["player"].path_state["omen_offensive"]["enemy.entity"]
    buff = next(
        effect for effect in marked.fighters["player"].effects
        if effect.id == "class_mechanic.oraculo.leitura_dos_sinais.agility"
    )
    assert omen["remaining"] == 2
    assert buff.magnitude == D("0.05") and buff.remaining == 1
    assert "oraculo.pressagio_offensive_criado" in event.path_triggers
    assert "oraculo.leitura_dos_sinais" in event.path_triggers


@pytest.mark.asyncio
async def test_publicly_acquired_luminar_tier25_effects_consume_fulgor_and_julgamento_once(
    database,
):
    _, _, loaded = await _acquire_and_load(
        database, 841725, "luminar", TIER25["luminar"]
    )
    cls, level, race, path, ids, _, stats = loaded
    barrier_state = _battle(
        cls, level, race, path, ids, stats, (LUMINAR_ART_IDS["egide_solar"],)
    )
    barrier_result = act(barrier_state, LUMINAR_ART_IDS["egide_solar"])
    barrier_event = _event(barrier_result, LUMINAR_ART_IDS["egide_solar"])
    expected_barrier = (stats.attack * D("0.90") * D("1.04")).to_integral_value(
        rounding=ROUND_FLOOR
    )
    assert barrier_event.barrier_value == expected_barrier
    assert "luminar.egide_densa" in barrier_event.path_triggers

    fulgor_state = _battle(
        cls,
        level,
        race,
        path,
        ids,
        stats,
        (LUMINAR_ART_IDS["fulgor"], LUMINAR_ART_IDS["luz_restauradora"]),
        player_hp=stats.hp / D(2),
    )
    generated = act(
        fulgor_state, LUMINAR_ART_IDS["fulgor"], target_id="enemy.entity"
    )
    assert generated.fighters["player"].path_state["luminar_state"]["kind"] == "fulgor"
    generated = _reconnect(generated)
    consumed = act(
        generated, LUMINAR_ART_IDS["luz_restauradora"], target_id="player.entity"
    )
    event = _event(consumed, LUMINAR_ART_IDS["luz_restauradora"])
    buff_id = "class_mechanic.luminar.alternancia_radiante.agility"
    assert "luminar.fulgor_consumido" in event.path_triggers
    assert "luminar.alternancia_radiante" in event.path_triggers
    assert "luminar_state" not in consumed.fighters["player"].path_state
    assert sum(effect.id == buff_id for effect in consumed.fighters["player"].effects) == 1

    judgment_state = _battle(
        cls,
        level,
        race,
        path,
        ids,
        stats,
        (LUMINAR_ART_IDS["luz_restauradora"], LUMINAR_ART_IDS["explosao_solar"]),
        player_hp=stats.hp / D(2),
    )
    prepared = act(
        judgment_state, LUMINAR_ART_IDS["luz_restauradora"], target_id="player.entity"
    )
    assert prepared.fighters["player"].path_state["luminar_state"]["kind"] == "julgamento"
    solar = act(prepared, LUMINAR_ART_IDS["explosao_solar"])
    solar_event = _event(solar, LUMINAR_ART_IDS["explosao_solar"])
    assert "luminar.julgamento_consumido" in solar_event.path_triggers
    assert "luminar.alternancia_radiante" in solar_event.path_triggers
    assert sum(effect.id == buff_id for effect in solar.fighters["player"].effects) == 1


@pytest.mark.asyncio
async def test_luminar_and_tecelao_public_barrier_talents_compose_by_source_and_recipient(
    database,
):
    _, _, luminar = await _acquire_and_load(
        database, 841730, "luminar", ("talent.luminar.egide_densa",)
    )
    _, _, tecelao = await _acquire_and_load(
        database, 841731, "tecelao", ("talent.tecelao.protecao_tecida",)
    )
    _, _, oraculo = await _acquire_and_load(
        database, 841732, "oraculo", ("talent.oraculo.antevisao_defensiva",)
    )
    lum_cls, level, race, path, lum_ids, _, lum_stats = luminar
    tec_cls, tec_level, tec_race, tec_path, tec_ids, _, tec_stats = tecelao
    ora_cls, ora_level, ora_race, ora_path, ora_ids, _, ora_stats = oraculo

    def add_allies(state):
        state.fighters["tecelao.ally"] = Fighter(
            "tecelao.ally", "Tecelão", tec_level, tec_stats, tec_stats.hp,
            race=tec_race, character_class=tec_cls, selected_path=tec_path,
            talent_ids=tec_ids, side="player", takes_turn=False,
        )
        state.fighters["oraculo.ally"] = Fighter(
            "oraculo.ally", "Oráculo", ora_level, ora_stats, ora_stats.hp,
            race=ora_race, character_class=ora_cls, selected_path=ora_path,
            talent_ids=ora_ids, side="player", takes_turn=False,
        )
        return state

    tecelao_state = add_allies(
        _battle(
            lum_cls,
            level,
            race,
            path,
            lum_ids,
            lum_stats,
            (LUMINAR_ART_IDS["luz_restauradora"],),
        )
    )
    tecelao_result = act(
        tecelao_state,
        LUMINAR_ART_IDS["luz_restauradora"],
        target_id="tecelao.ally",
    )
    tecelao_event = _event(tecelao_result, LUMINAR_ART_IDS["luz_restauradora"])
    expected_tecel_barrier = (
        lum_stats.attack * D("0.35") * D("1.04") * D("1.05")
    ).to_integral_value(rounding=ROUND_FLOOR)
    assert tecelao_event.barrier_value == expected_tecel_barrier
    tec_barrier = tecelao_result.fighters["tecelao.ally"].barrier
    restored_tec = _reconnect(tecelao_result)
    assert restored_tec.fighters["tecelao.ally"].barrier == tec_barrier

    oraculo_state = add_allies(
        _battle(
            lum_cls,
            level,
            race,
            path,
            lum_ids,
            lum_stats,
            (LUMINAR_ART_IDS["luz_restauradora"],),
        )
    )
    oraculo_result = act(
        oraculo_state,
        LUMINAR_ART_IDS["luz_restauradora"],
        target_id="oraculo.ally",
    )
    oraculo_event = _event(oraculo_result, LUMINAR_ART_IDS["luz_restauradora"])
    expected_oraculo_barrier = (
        lum_stats.attack * D("0.35") * D("1.04")
    ).to_integral_value(rounding=ROUND_FLOOR)
    assert oraculo_event.barrier_value == expected_oraculo_barrier
    oracle = oraculo_result.fighters["oraculo.ally"]
    assert oracle.barrier > 0
    assert oracle.stat("defense") == oracle.stats.defense * D("1.05")
    restored_ora = _reconnect(oraculo_result)
    assert restored_ora.fighters["oraculo.ally"].stat("defense") == oracle.stat("defense")


@pytest.mark.asyncio
async def test_doctrine_accepts_nv25_without_free_respec_and_rejects_invalid_state_atomically(
    database,
):
    actor = 841740
    character_id, sessions = await _seed(
        database, actor, "sentinela", level=25, crowns=0, location="Estrada"
    )
    service = DoctrineService(sessions, "ocaso")
    created = await service.create(actor, "Nv25 legal", 0)
    assert created is not None and created.doctrine_id is not None
    collection = await service.view(actor)
    assert collection is not None
    doctrine = next(
        item for item in collection.doctrines if item.doctrine_id == created.doctrine_id
    )
    tier25_definitions = tuple(t for t in TALENTS_BY_CLASS["sentinela"] if t.level == 25)
    screen = render_talent_choices(collection, doctrine, 1)
    assert all(
        any(
            definition.name in button.text
            for row in screen.keyboard.inline_keyboard
            for button in row
        )
        for definition in tier25_definitions
    )
    future_names = {
        talent.name for talent in TALENTS_BY_CLASS["sentinela"] if talent.level >= 45
    }
    assert not any(
        name in button.text
        for name in future_names
        for row in screen.keyboard.inline_keyboard
        for button in row
    )

    invalid_ids = (
        next(t.talent_id for t in TALENTS_BY_CLASS["sentinela"] if t.level == 55),
        "talent.errante.precisao_cruel",
    )
    for invalid_id in invalid_ids:
        with pytest.raises(DoctrineRejected, match="invalid_talents"):
            await service.update_component(
                actor,
                created.doctrine_id,
                0,
                collection.configuration_version,
                "talents",
                [{"point_slot": 1, "talent_id": invalid_id}],
            )

    choices = [
        {"point_slot": slot, "talent_id": definition.talent_id}
        for slot, definition in enumerate(tier25_definitions, 1)
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
        actor,
        created.doctrine_id,
        1,
        edited.configuration_version,
    )
    assert applied is not None and applied.changed
    no_change = await service.apply(
        actor,
        created.doctrine_id,
        1,
        applied.configuration_version,
    )
    assert no_change is not None and not no_change.changed

    changed_choices = [
        {"point_slot": 1, "talent_id": tier25_definitions[0].talent_id},
        {"point_slot": 2, "talent_id": tier25_definitions[1].talent_id},
        {"point_slot": 3, "talent_id": TALENTS_BY_CLASS["sentinela"][0].talent_id},
    ]
    changed = await service.update_component(
        actor,
        created.doctrine_id,
        1,
        applied.configuration_version,
        "talents",
        changed_choices,
    )
    assert changed is not None and changed.changed
    with pytest.raises(DoctrineRejected, match="safe_location_required"):
        await service.apply(
            actor,
            created.doctrine_id,
            2,
            changed.configuration_version,
        )

    async with sessions() as session:
        character = await session.get(Character, character_id)
        saved_rows = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice)
                    .where(CharacterTalentChoice.character_id == character_id)
                    .order_by(CharacterTalentChoice.point_slot)
                )
            ).all()
        )
    assert character is not None and character.crowns == 0
    assert [(row.point_slot, row.talent_id) for row in saved_rows] == [
        (choice["point_slot"], choice["talent_id"]) for choice in choices
    ]

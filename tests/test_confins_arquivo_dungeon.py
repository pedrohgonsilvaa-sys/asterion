from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.bestiary import CONFINS_ARQUIVO_BOSS_MASTERY
from asterion.application.dungeons import (
    CONFINS_ARQUIVO_FAMILY_ID,
    DUNGEON_FAMILIES,
    DungeonService,
    _encounter_specs,
    _enemy_rewards_for,
)
from asterion.domain.combat import (
    CombatEvent,
    _resolve_phase_triggers,
    act,
    action_target_ids,
    active_player_key,
    allowed_actions,
)
from asterion.domain.confins_arquivo_dungeon import (
    CONFINS_ARQUIVO_BASIC_MATERIAL_WEIGHTS,
    CONFINS_ARQUIVO_BOSS,
    CONFINS_ARQUIVO_CORE_ID,
    CONFINS_ARQUIVO_DISCOVERY_UNLOCK,
    CONFINS_ARQUIVO_ENVIRONMENTS,
    CONFINS_ARQUIVO_FIRST_CLEAR_PREFIX,
    CONFINS_ARQUIVO_PHASE_II,
    CONFINS_ARQUIVO_PHASE_III,
    CONFINS_ARQUIVO_RECIPE_UNLOCK,
    create_confins_arquivo_combat,
)
from asterion.domain.confins_arquivo_dungeon import (
    CONFINS_ARQUIVO_FAMILY_ID as DOMAIN_FAMILY_ID,
)
from asterion.domain.dungeons import (
    DIFFICULTIES,
    catalyst_material_id,
    difficulty_gate,
    fragment_material_id,
)
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.professions import canonical_recipe, recipe_crown_cost
from asterion.domain.road import (
    CONFINS_ARQUIVO_ECO,
    CONFINS_ARQUIVO_GUARDIAN,
    CONFINS_ESTRADAS_AUSENTES,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CodexEntry,
    CodexFragment,
    DungeonPityState,
    DungeonRun,
    DungeonRunEncounter,
    DungeonRunMember,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_s6_p6_integration import _seed_final_campaign

D = Decimal


def _combat(ordinal: int, *, difficulty: str = "stable", group_size: int = 1):
    return create_confins_arquivo_combat(
        uuid4(),
        name="Aventureiro",
        character_class="sentinela",
        race="remanescente",
        hp=D(5000),
        level=60 if difficulty == "rupture" else 57,
        difficulty=difficulty,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"confins-arquivo:{ordinal}:{difficulty}:{group_size}",
        initial_group_size=group_size,
    )


async def _seed_archive_actor(
    database, actor: int, *, level: int = 54, discovery: bool = True
):
    character_id, sessions = await _seed_final_campaign(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.vigor = 100
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = "Confins do Véu"
        world.location = CONFINS_ESTRADAS_AUSENTES
        session.add(
            Quest(
                character_id=character_id,
                quest_id="P32",
                title="A Fratura",
                status="completed",
                step=6,
                content_version="confins-1.0.0",
                progress={"completed": True},
            )
        )
        if discovery:
            session.add(
                Unlock(
                    character_id=character_id,
                    unlock_id=CONFINS_ARQUIVO_DISCOVERY_UNLOCK,
                )
            )
    return character_id, sessions


def test_confins_arquivo_family_roster_rewards_and_recipe_are_canonical():
    family = DUNGEON_FAMILIES[CONFINS_ARQUIVO_FAMILY_ID]
    assert family.family_id == DOMAIN_FAMILY_ID == "dungeon.confins.arquivo_retorno"
    assert family.name == "Arquivo do Retorno"
    assert family.entry_location == CONFINS_ESTRADAS_AUSENTES
    assert family.discovery_unlock == CONFINS_ARQUIVO_DISCOVERY_UNLOCK
    assert family.required_quest_ids == ("P32",)
    assert (family.minimum_level, family.reference_level, family.encounter_count) == (
        54,
        57,
        5,
    )
    assert dict(family.completion_xp_by_difficulty) == {
        "stable": 14_870,
        "fractured": 18_220,
        "rupture": 24_240,
    }
    assert dict(family.first_clear_xp_by_difficulty) == {
        "stable": 23_792,
        "fractured": 29_152,
        "rupture": 38_784,
    }
    assert dict(family.crowns_by_difficulty) == {
        "stable": 770,
        "fractured": 1_150,
        "rupture": 1_800,
    }
    assert family.basic_material_weights == CONFINS_ARQUIVO_BASIC_MATERIAL_WEIGHTS
    assert [DIFFICULTIES[key].vigor for key in ("stable", "fractured", "rupture")] == [
        25,
        35,
        50,
    ]
    assert [DIFFICULTIES[key].consumable_limit for key in ("stable", "fractured", "rupture")] == [
        6,
        5,
        4,
    ]
    assert [DIFFICULTIES[key].brazier_percent for key in ("stable", "fractured", "rupture")] == [
        70,
        40,
        20,
    ]
    assert [DIFFICULTIES[key].basic_materials for key in ("stable", "fractured", "rupture")] == [
        8,
        11,
        14,
    ]
    assert [DIFFICULTIES[key].catalysts for key in ("stable", "fractured", "rupture")] == [
        2,
        3,
        4,
    ]
    assert [DIFFICULTIES[key].cores for key in ("stable", "fractured", "rupture")] == [1, 2, 4]
    assert [DIFFICULTIES[key].fragments for key in ("stable", "fractured", "rupture")] == [
        2,
        4,
        7,
    ]
    assert [DIFFICULTIES[key].pity_points for key in ("stable", "fractured", "rupture")] == [
        1,
        2,
        4,
    ]
    assert [DIFFICULTIES[key].rune_chance for key in ("stable", "fractured", "rupture")] == [
        20,
        35,
        50,
    ]
    assert [DIFFICULTIES[key].recipe_chance for key in ("stable", "fractured", "rupture")] == [
        8,
        15,
        25,
    ]
    assert DIFFICULTIES["stable"].equipment_bands == (
        (2_500, "Comum"),
        (5_000, "Raro"),
        (2_200, "Épico"),
        (280, "Lendário"),
        (20, "Mítico"),
    )
    assert DIFFICULTIES["fractured"].equipment_bands == (
        (1_000, "Comum"),
        (4_500, "Raro"),
        (3_800, "Épico"),
        (650, "Lendário"),
        (50, "Mítico"),
    )
    assert DIFFICULTIES["rupture"].equipment_bands == (
        (0, "Comum"),
        (2_000, "Raro"),
        (6_000, "Épico"),
        (1_900, "Lendário"),
        (100, "Mítico"),
    )
    assert difficulty_gate(
        level=53,
        discovered=True,
        stable_first_clear=False,
        fractured_first_clear=False,
        minimum_level=54,
    )["stable"] == "level"

    expected = {
        1: [(CONFINS_ARQUIVO_ECO, 54)],
        2: [(CONFINS_ARQUIVO_ECO, 55), (CONFINS_ARQUIVO_ECO, 55)],
        3: [(CONFINS_ARQUIVO_GUARDIAN, 56)],
        4: [(CONFINS_ARQUIVO_ECO, 57)],
        5: [(CONFINS_ARQUIVO_BOSS, 57)],
    }
    run = type(
        "Run",
        (),
        {
            "dungeon_family_id": CONFINS_ARQUIVO_FAMILY_ID,
            "difficulty": "rupture",
            "initial_group_size": 4,
            "reference_level": 60,
        },
    )()
    for ordinal, expected_creatures in expected.items():
        specs = _encounter_specs(run, ordinal)
        assert [(spec.creature.creature_id, spec.level) for spec in specs] == expected_creatures
        assert len(_enemy_rewards_for(run, ordinal)) == len(expected_creatures)
    assert set(_enemy_rewards_for(run, 4)[0]) == {CONFINS_ARQUIVO_ECO, 57, "common"}
    assert "Placa de Registro de Entrada" in CONFINS_ARQUIVO_ENVIRONMENTS[4]
    assert "Placa de Registro de Saída" in CONFINS_ARQUIVO_ENVIRONMENTS[4]

    recipe = canonical_recipe(CONFINS_ARQUIVO_RECIPE_UNLOCK)
    assert recipe is not None
    assert recipe.output_id == "equipment.confins.special.relicario_entrada_duplicada"
    assert recipe.output_slot == "Artefato" and recipe.rarity == "Raro"
    assert recipe.grade == 6 and recipe.required_level == 15 and recipe.sw == 2
    assert recipe.fixed_materials == (
        type(recipe.fixed_materials[0])("material.confins.ferro_baliza", 10),
        type(recipe.fixed_materials[0])("material.confins.po_referencia", 6),
        type(recipe.fixed_materials[0])("material.tdo.fragmento_aprimoramento_vi", 8, False),
        type(recipe.fixed_materials[0])(CONFINS_ARQUIVO_CORE_ID, 1),
    )
    assert recipe_crown_cost(recipe, 60) == 700
    assert catalyst_material_id(57).endswith("catalisador_elite_vi")
    assert fragment_material_id(57).endswith("fragmento_aprimoramento_vi")


def test_confins_arquivo_boss_actions_scaling_and_three_persistent_phases():
    eco = _combat(1)
    assert set(eco.enemy_actions) == {
        "sinal_presenca",
        "passagem_repetida",
        "rasura_registro",
    }
    assert eco.enemy_actions["sinal_presenca"].coefficient == D("0.95")
    assert eco.enemy_actions["passagem_repetida"].coefficient == D("1.10")
    assert eco.enemy_actions["passagem_repetida"].cooldown == 2
    assert eco.enemy_actions["rasura_registro"].coefficient == D("0.85")
    assert eco.enemy_actions["rasura_registro"].effect_stat == "per"
    assert eco.enemy_actions["rasura_registro"].attack_debuff == D("0.10")
    assert eco.enemy_actions["rasura_registro"].duration == 2
    assert eco.enemy_actions["rasura_registro"].cooldown == 3

    guardian = _combat(3)
    assert guardian.enemy_actions["reconstituir_postura"].self_barrier_coefficient == D("1.00")
    assert guardian.enemy_actions["reconstituir_postura"].cooldown == 3
    assert guardian.enemy_actions["revisao_retorno"].coefficient == D("0.90")
    assert guardian.enemy_actions["revisao_retorno"].attack_debuff == D("0.10")
    assert guardian.enemy_actions["revisao_retorno"].effect_stat == "defense"
    assert guardian.enemy_actions["volta_indevida"].prepared
    assert guardian.enemy_actions["volta_indevida"].coefficient == D("1.75")
    assert guardian.enemy_actions["volta_indevida"].cooldown == 4

    book = _combat(4)
    dungeon_context = book.configuration_snapshot["dungeon"]
    assert dungeon_context["contextual_evidence"] == [
        "codex.fragment.confins.arquivo.placa_entrada",
        "codex.fragment.confins.arquivo.placa_saida",
    ]
    assert len([fighter for fighter in book.fighters.values() if fighter.side == "enemy"]) == 1
    restored_book = decode(encode(book), book.id, book.ruleset, book.version)
    assert restored_book.configuration_snapshot["dungeon"]["contextual_evidence"] == (
        dungeon_context["contextual_evidence"]
    )

    solo = _combat(5, difficulty="stable", group_size=1)
    group = _combat(5, difficulty="stable", group_size=4)
    fractured = _combat(5, difficulty="fractured", group_size=1)
    boss = solo.fighters["enemy"]
    assert boss.name == "O Que Chega Antes"
    assert set(solo.enemy_actions) == {
        "marca_chegada",
        "registro_antecipado",
        "cobertura_anterior",
        "queda_retorno",
        "retorno_sem_ida",
    }
    assert solo.enemy_actions["marca_chegada"].coefficient == D("1.00")
    registro = solo.enemy_actions["registro_antecipado"]
    assert registro.coefficient == D("0.90") and registro.effect_stat == "agility"
    assert registro.attack_debuff == D("0.10") and registro.duration == 2
    assert registro.cooldown == 3
    cobertura = solo.enemy_actions["cobertura_anterior"]
    assert cobertura.self_barrier_hp_fraction == D("0.08")
    assert cobertura.cooldown == 4 and cobertura.max_uses_per_combat == 2
    assert cobertura.phase_ids == ("II", "III")
    assert solo.enemy_actions["queda_retorno"].coefficient == D("0.80")
    assert solo.enemy_actions["queda_retorno"].target_mode == "all_opponents"
    prepared = solo.enemy_actions["retorno_sem_ida"]
    assert prepared.prepared and prepared.coefficient == D("1.80")
    assert prepared.cooldown == 5 and prepared.phase_ids == ("III",)
    assert boss.stats.hp < group.fighters["enemy"].stats.hp
    assert fractured.fighters["enemy"].stats.hp > boss.stats.hp
    assert solo.phase_id == "I"
    assert [
        (trigger.hp_fraction_at_most, trigger.phase_id)
        for trigger in solo.phase_triggers
    ] == [(D("0.70"), "II"), (D("0.35"), "III")]
    assert CONFINS_ARQUIVO_BOSS_MASTERY[CONFINS_ARQUIVO_BOSS] == {
        "first_victory",
        "phase:registro_antecipado",
        "phase:registro_refeito",
        "action:queda_retorno",
        "stable_first_clear",
    }

    boss.hp = boss.stats.hp * D("0.70")
    _resolve_phase_triggers(solo)
    assert solo.phase_id == "II"
    phase_ii_triggers = set(solo.phase_triggered_ids)
    _resolve_phase_triggers(solo)
    assert solo.phase_triggered_ids == phase_ii_triggers
    boss.hp = boss.stats.hp * D("0.35")
    _resolve_phase_triggers(solo)
    assert solo.phase_id == "III"
    restored = decode(encode(solo), solo.id, solo.ruleset, solo.version)
    assert restored.phase_id == "III"
    assert {CONFINS_ARQUIVO_PHASE_II, CONFINS_ARQUIVO_PHASE_III}.issubset(
        restored.phase_triggered_ids
    )
    assert restored.enemy_actions["retorno_sem_ida"].prepared

    telegraph = _combat(5)
    telegraph.fighters["enemy"].hp = (
        telegraph.fighters["enemy"].stats.hp * D("0.35")
    )
    _resolve_phase_triggers(telegraph)
    for action_id in (
        "cobertura_anterior",
        "registro_antecipado",
        "queda_retorno",
        "marca_chegada",
    ):
        telegraph.fighters["enemy"].cooldowns[action_id] = 999
    actor_key = active_player_key(telegraph)
    target = action_target_ids(telegraph, "attack", actor_key=actor_key)[0]
    telegraph = act(telegraph, "attack", target_id=target, actor_key=actor_key)
    assert telegraph.prepared_action == "retorno_sem_ida"
    assert telegraph.prepared_source == "enemy"
    restored_telegraph = decode(
        encode(telegraph), telegraph.id, telegraph.ruleset, telegraph.version
    )
    assert restored_telegraph.prepared_action == "retorno_sem_ida"
    assert restored_telegraph.prepared_source == "enemy"


def _scripted_result(state, action_id, *, target_id=None, actor_key=None, defeat=False):
    actor_key = actor_key or "player"
    if action_id not in allowed_actions(state, actor_key):
        return state
    if target_id not in action_target_ids(state, action_id, actor_key=actor_key):
        return state
    updated = deepcopy(state)
    active = updated.fighters[actor_key]
    updated.events.append(
        CombatEvent(
            len(updated.events),
            updated.round,
            actor_key,
            action_id,
            target=target_id,
            actor_entity_id=active.id,
        )
    )
    if defeat:
        updated.fighters[actor_key].hp = D(0)
        updated.result = "defeat"
    else:
        for fighter in updated.fighters.values():
            if fighter.side == "enemy" and fighter.required_for_victory:
                fighter.hp = D(0)
        updated.result = "victory"
    updated.version += 1
    return updated


def _script_actions(monkeypatch, *, brazier_by_difficulty, fail_once=None):
    brazier_rolls = []
    attempts = set()

    def roll_brazier(seed, difficulty):
        brazier_rolls.append((seed, difficulty))
        return brazier_by_difficulty[difficulty]

    def act(state, action_id, *, target_id=None, actor_key=None):
        ordinal = state.configuration_snapshot["dungeon"]["ordinal"]
        should_fail = fail_once == ordinal and ordinal not in attempts
        attempts.add(ordinal)
        return _scripted_result(
            state,
            action_id,
            target_id=target_id,
            actor_key=actor_key,
            defeat=should_fail,
        )

    monkeypatch.setattr("asterion.application.dungeons.roll_brazier", roll_brazier)
    monkeypatch.setattr("asterion.application.dungeons.act", act)
    return brazier_rolls


async def _clear_run(service, actor: int, difficulty: str):
    current = await service.start_solo(
        actor, difficulty, family_id=CONFINS_ARQUIVO_FAMILY_ID
    )
    assert current is not None and current.run_id is not None
    run_id = current.run_id
    assert current.has_brazier is None
    for ordinal in range(1, 6):
        if current.kind == "brazier":
            current = await service.activate_brazier(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
        fight = await service.begin_encounter(actor, run_id, current.state_version)
        assert fight is not None and fight.kind == "combat" and fight.combat is not None
        assert fight.activity_id is not None
        assert fight.combat.configuration_snapshot["dungeon"]["ordinal"] == ordinal
        enemies = [fighter for fighter in fight.combat.fighters.values() if fighter.side == "enemy"]
        expected_names = {
            1: ["Eco sem Origem"],
            2: ["Eco sem Origem", "Eco sem Origem"],
            3: ["Guardião do Retorno"],
            4: ["Eco sem Origem"],
            5: ["O Que Chega Antes"],
        }[ordinal]
        assert sorted(fighter.name for fighter in enemies) == sorted(expected_names)
        if ordinal == 2:
            assert len(enemies) == 2
            assert fight.combat.configuration_snapshot["dungeon"]["initial_group_size"] == 1
        target = action_target_ids(fight.combat, "attack", actor_key="player")[0]
        current = await service.action(
            actor,
            run_id,
            fight.activity_id,
            fight.combat.version,
            "attack",
            target,
        )
        assert current is not None
        if ordinal == 3:
            assert current.kind == "brazier" and current.has_brazier is True
            current = await service.activate_brazier(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
    assert current.kind == "completed"
    return current, run_id


@pytest.mark.asyncio
async def test_confins_arquivo_discovery_and_level_gates_are_persistent_postgres(database):
    actor = 991_401
    character_id, sessions = await _seed_archive_actor(
        database, actor, level=53, discovery=False
    )
    service = DungeonService(sessions, "ocaso")
    assert (await service.detail(actor, CONFINS_ARQUIVO_FAMILY_ID)).kind == "hidden"
    assert (await service.known(actor)).kind == "empty"
    blocked = await service.start_solo(actor, "stable", family_id=CONFINS_ARQUIVO_FAMILY_ID)
    assert blocked is not None and blocked.reason == "gate"

    async with sessions.begin() as session:
        session.add(
            Unlock(character_id=character_id, unlock_id=CONFINS_ARQUIVO_DISCOVERY_UNLOCK)
        )
    detail = await service.detail(actor, CONFINS_ARQUIVO_FAMILY_ID)
    assert detail is not None and detail.kind == "detail"
    assert dict(detail.difficulty_gates)["stable"] == "level"
    blocked = await service.start_solo(actor, "stable", family_id=CONFINS_ARQUIVO_FAMILY_ID)
    assert blocked is not None and blocked.reason == "level"
    known = await service.known(actor)
    assert known is not None and any(
        row[0] == CONFINS_ARQUIVO_FAMILY_ID for row in known.known_dungeons
    )

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 54
    detail = await service.detail(actor, CONFINS_ARQUIVO_FAMILY_ID)
    assert dict(detail.difficulty_gates)["stable"] == "available"
    created = await service.start_solo(actor, "stable", family_id=CONFINS_ARQUIVO_FAMILY_ID)
    assert created is not None and created.run_id is not None
    async with sessions() as session:
        run = await session.get(DungeonRun, created.run_id)
        assert run is not None
        assert run.reference_level == 57 and run.difficulty == "stable"
        assert run.has_brazier in {True, False}
        assert session is not None


@pytest.mark.asyncio
async def test_confins_arquivo_stable_run_brazier_retry_settlement_and_codex(
    database, monkeypatch
):
    actor = 991_402
    character_id, sessions = await _seed_archive_actor(database, actor, level=54)
    service = DungeonService(sessions, "ocaso")
    brazier_rolls = _script_actions(
        monkeypatch,
        brazier_by_difficulty={"stable": True, "fractured": True, "rupture": True},
        fail_once=4,
    )

    current = await service.start_solo(actor, "stable", family_id=CONFINS_ARQUIVO_FAMILY_ID)
    assert current is not None and current.run_id is not None and current.has_brazier is None
    run_id = current.run_id
    for ordinal in range(1, 6):
        if current.kind == "brazier":
            current = await service.activate_brazier(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
        fight = await service.begin_encounter(actor, run_id, current.state_version)
        assert fight is not None and fight.kind == "combat" and fight.combat is not None
        assert fight.combat.configuration_snapshot["dungeon"]["ordinal"] == ordinal
        enemies = [fighter for fighter in fight.combat.fighters.values() if fighter.side == "enemy"]
        assert len(enemies) == (2 if ordinal == 2 else 1)
        if ordinal == 4:
            assert fight.combat.configuration_snapshot["dungeon"]["contextual_evidence"] == [
                "codex.fragment.confins.arquivo.placa_entrada",
                "codex.fragment.confins.arquivo.placa_saida",
            ]
        target = action_target_ids(fight.combat, "attack", actor_key="player")[0]
        current = await service.action(
            actor,
            run_id,
            fight.activity_id,
            fight.combat.version,
            "attack",
            target,
        )
        assert current is not None
        if ordinal == 3:
            assert current.kind == "brazier" and current.has_brazier is True
            current = await service.activate_brazier(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
        elif ordinal == 4 and current.kind == "retry":
            failed = current
            current = await service.retry(actor, run_id, failed.state_version)
            assert current is not None and current.kind == "ready"
            current = await service.resume(actor)
            assert current is not None and current.kind == "ready"
            assert current.run_id == run_id and len(brazier_rolls) == 1
            async with sessions() as session:
                run = await session.get(DungeonRun, run_id)
                encounter = await session.get(DungeonRunEncounter, (run_id, 4))
                assert run is not None and run.status == "active"
                assert run.current_encounter_ordinal == 4
                assert encounter is not None and encounter.attempt_count == 1
            fight = await service.begin_encounter(actor, run_id, current.state_version)
            assert fight is not None and fight.kind == "combat" and fight.combat is not None
            target = action_target_ids(fight.combat, "attack", actor_key="player")[0]
            current = await service.action(
                actor,
                run_id,
                fight.activity_id,
                fight.combat.version,
                "attack",
                target,
            )
            assert current is not None and current.kind == "ready"
    assert current.kind == "completed" and current.first_clear
    assert len(brazier_rolls) == 1

    async with sessions() as session:
        run = await session.get(DungeonRun, run_id)
        assert run is not None and run.status == "completed"
        assert run.has_brazier and run.brazier_activated
        encounters = (
            await session.scalars(
                select(DungeonRunEncounter)
                .where(DungeonRunEncounter.run_id == run_id)
                .order_by(DungeonRunEncounter.encounter_ordinal)
            )
        ).all()
        assert len(encounters) == 5 and all(row.status == "completed" for row in encounters)
        assert encounters[3].attempt_count == 2
        events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id
                    == f"{DUNGEON_FAMILIES[CONFINS_ARQUIVO_FAMILY_ID].reward_prefix}{run_id.hex}",
                )
            )
        ).all()
        assert len(events) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == events[0].id)
            )
        ).all()
        by_kind = {row.kind: row for row in components if row.kind in {"xp", "crowns"}}
        assert by_kind["xp"].payload["completion"] == 23_792
        assert by_kind["xp"].payload["first_clear"] is True
        assert by_kind["crowns"].quantity == 770
        materials = {row.item_id: row.quantity for row in components if row.kind == "material"}
        assert sum(
            materials.get(item_id, 0) for item_id, _weight in CONFINS_ARQUIVO_BASIC_MATERIAL_WEIGHTS
        ) == 8
        assert materials[CONFINS_ARQUIVO_CORE_ID] == 1
        assert materials[catalyst_material_id(57)] == 2
        assert materials[fragment_material_id(57)] == 2
        assert sum(row.quantity for row in components if row.kind == "equipment") == 1
        pity = await session.get(DungeonPityState, character_id)
        assert pity is not None and pity.legendary_plus_points >= 0
        assert (
            await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character_id,
                    Achievement.achievement_id == "achievement.confins.arquivo_estavel",
                )
            )
        ) is not None
        codex_ids = set(
            (
                await session.scalars(
                    select(CodexEntry.entry_id).where(
                        CodexEntry.character_id == character_id,
                        CodexEntry.entry_id.in_(
                            {
                                "codex.confins.dungeon.arquivo_retorno",
                                "codex.confins.dungeon.registro_repetido",
                                "codex.confins.dungeon.chegada_antes",
                            }
                        ),
                    )
                )
            ).all()
        )
        assert codex_ids == {
            "codex.confins.dungeon.arquivo_retorno",
            "codex.confins.dungeon.registro_repetido",
            "codex.confins.dungeon.chegada_antes",
        }
        fragments = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id
                    )
                )
            ).all()
        )
        assert {
            "codex.fragment.confins.arquivo.cabecalho_entrada",
            "codex.fragment.confins.arquivo.livro_a",
            "codex.fragment.confins.arquivo.livro_b",
            "codex.fragment.confins.arquivo.guardiao_retorno",
            "codex.fragment.confins.arquivo.placa_entrada",
            "codex.fragment.confins.arquivo.placa_saida",
            "codex.fragment.confins.arquivo.chegada_antes",
        }.issubset(fragments)
        boss = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == CONFINS_ARQUIVO_BOSS,
            )
        )
        assert boss is not None and boss.stage != "dominated"
        evidence = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == CONFINS_ARQUIVO_BOSS,
                    )
                )
            ).all()
        )
        assert "first_victory" in evidence
        assert "phase:registro_antecipado" in evidence
        assert "stable_first_clear" in evidence
        assert (
            await session.scalar(
                select(func.count(RewardEvent.id)).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"bestiary.first_victory:{CONFINS_ARQUIVO_BOSS}",
                )
            )
            == 0
        )


@pytest.mark.asyncio
async def test_confins_arquivo_defeat_without_brazier_fails_and_refunds_vigor(
    database, monkeypatch
):
    actor = 991_403
    character_id, sessions = await _seed_archive_actor(database, actor, level=54)
    service = DungeonService(sessions, "ocaso")
    brazier_rolls = _script_actions(
        monkeypatch,
        brazier_by_difficulty={"stable": False, "fractured": False, "rupture": False},
        fail_once=1,
    )
    started = await service.start_solo(actor, "stable", family_id=CONFINS_ARQUIVO_FAMILY_ID)
    assert started is not None and started.run_id is not None and started.has_brazier is None
    fight = await service.begin_encounter(actor, started.run_id, started.state_version)
    target = action_target_ids(fight.combat, "attack", actor_key="player")[0]
    failed = await service.action(
        actor,
        started.run_id,
        fight.activity_id,
        fight.combat.version,
        "attack",
        target,
    )
    assert failed is not None and failed.kind == "failed"
    assert len(brazier_rolls) == 1
    retry = await service.retry(actor, started.run_id, failed.state_version)
    assert retry is not None and retry.kind == "stale"
    async with sessions() as session:
        run = await session.get(DungeonRun, started.run_id)
        member = await session.get(DungeonRunMember, (started.run_id, character_id))
        character = await session.get(Character, character_id)
        assert run is not None and run.status == "failed" and run.has_brazier is False
        assert run.progress["internal_xp"] == 0 and run.progress["internal_rewards"] == []
        assert member is not None and member.vigor_refunded and member.vigor_reserved == 0
        assert character is not None and character.vigor == 100
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id.startswith(
                    DUNGEON_FAMILIES[CONFINS_ARQUIVO_FAMILY_ID].reward_prefix
                ),
            )
        ) is None


@pytest.mark.asyncio
async def test_confins_arquivo_stable_fractured_rupture_progression_and_group_gate(
    database, monkeypatch
):
    leader = 991_404
    leader_id, sessions = await _seed_archive_actor(database, leader, level=60)
    excluded_actor = leader + 1
    _excluded_id, _ = await _seed_archive_actor(
        database, excluded_actor, level=60, discovery=False
    )
    service = DungeonService(sessions, "ocaso")
    group = await service.prepare_group(leader, CONFINS_ARQUIVO_FAMILY_ID, "stable")
    assert group is not None and group.lobby_id is not None
    # Resolve the unique seeded target name rather than assuming the factory's display name.
    async with sessions() as session:
        excluded = await session.get(Character, _excluded_id)
        assert excluded is not None
        excluded_name = excluded.name
    rejected = await service.invite_by_name(
        leader, group.lobby_id, group.lobby_version, excluded_name
    )
    assert rejected is not None and rejected.reason == "discovery"
    cancelled = await service.cancel_queue_or_lobby(
        leader, group.lobby_id, group.lobby_version
    )
    assert cancelled is not None

    brazier_rolls = _script_actions(
        monkeypatch,
        brazier_by_difficulty={"stable": True, "fractured": True, "rupture": True},
    )
    service = DungeonService(sessions, "ocaso")
    completions = []
    run_ids = []
    for difficulty, expected_reference, expected_completion, expected_crowns in (
        ("stable", 57, 23_792, 770),
        ("fractured", 57, 29_152, 1_150),
        ("rupture", 60, 38_784, 1_800),
    ):
        async with sessions.begin() as session:
            character = await session.get(Character, leader_id)
            assert character is not None
            character.vigor = 100
            world = await session.get(WorldState, leader_id)
            world.location = CONFINS_ESTRADAS_AUSENTES
        completed, run_id = await _clear_run(service, leader, difficulty)
        completions.append(completed)
        run_ids.append(run_id)
        async with sessions() as session:
            run = await session.get(DungeonRun, run_id)
            event = await session.scalar(
                select(RewardEvent).where(
                    RewardEvent.character_id == leader_id,
                    RewardEvent.source_id
                    == f"{DUNGEON_FAMILIES[CONFINS_ARQUIVO_FAMILY_ID].reward_prefix}{run_id.hex}",
                )
            )
            assert run is not None and run.reference_level == expected_reference
            assert event is not None
            xp = await session.scalar(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == event.id,
                    RewardComponent.kind == "xp",
                )
            )
            crowns = await session.scalar(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == event.id,
                    RewardComponent.kind == "crowns",
                )
            )
            assert xp.payload["completion"] == expected_completion
            assert crowns.quantity == expected_crowns
    assert [view.first_clear for view in completions] == [True, True, True]
    assert len(brazier_rolls) == 3
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == leader_id,
                Unlock.unlock_id == CONFINS_ARQUIVO_FIRST_CLEAR_PREFIX + "stable",
            )
        )
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == leader_id,
                Unlock.unlock_id == CONFINS_ARQUIVO_FIRST_CLEAR_PREFIX + "fractured",
            )
        )
        character = await session.get(Character, leader_id)
        assert character is not None and character.level == 60

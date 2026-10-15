from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.bestiary import (
    VARZEAS_DISTINCTIVE_BOSS_MASTERY,
    VARZEAS_DISTINCTIVE_ELITE_MASTERY,
)
from asterion.application.dungeons import (
    DUNGEON_FAMILIES,
    VARZEAS_CISTERN_FAMILY_ID,
    VARZEAS_INFIRMARY_FAMILY_ID,
    DungeonView,
    _encounter_specs,
    _enemy_rewards_for,
)
from asterion.application.road import REGION, VARZEAS_BREJOS, VARZEAS_GALERIAS
from asterion.bot.dungeon_ui import render_dungeons
from asterion.domain.combat import (
    Action,
    CombatEvent,
    action_target_ids,
    allowed_actions,
)
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.professions import canonical_recipe
from asterion.domain.road import VARZEAS_DUNGEON_CREATURES
from asterion.domain.varzeas_dungeons import (
    VARZEAS_HEART_PHASE_II,
    VARZEAS_HEART_PHASE_III,
    VARZEAS_PERSISTENT_PHASE_II,
    VARZEAS_PERSISTENT_PHASE_III,
    create_varzeas_dungeon_combat,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Brazier,
    CodexFragment,
    DungeonRun,
    DungeonRunEncounter,
    LocationDiscovery,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_s6_p6_integration import _seed_final_campaign

D = Decimal


def _combat(family_id, ordinal, *, difficulty="stable", group_size=1):
    family = DUNGEON_FAMILIES[family_id]
    return create_varzeas_dungeon_combat(
        uuid4(),
        family_id=family_id,
        name="Iona",
        character_class="sentinela",
        race="remanescente",
        hp=D(5000),
        level=40,
        difficulty=difficulty,
        reference_level=family.reference_level,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"varzeas:{family_id}:{ordinal}:{difficulty}:{group_size}",
        initial_group_size=group_size,
    )


def test_varzeas_dungeon_families_and_encounters_use_regional_reference_levels():
    infirmary = DUNGEON_FAMILIES[VARZEAS_INFIRMARY_FAMILY_ID]
    cistern = DUNGEON_FAMILIES[VARZEAS_CISTERN_FAMILY_ID]
    assert (infirmary.range_label, infirmary.minimum_level, infirmary.reference_level) == (
        "Nv.34–37",
        34,
        37,
    )
    assert (infirmary.entry_location, infirmary.region_display) == (
        "Brejos do Pulso",
        "Várzeas Carmesins",
    )
    assert (cistern.range_label, cistern.minimum_level, cistern.reference_level) == (
        "Nv.38–40",
        38,
        40,
    )
    assert cistern.entry_location == "Galerias de Transferência"

    expected = {
        VARZEAS_INFIRMARY_FAMILY_ID: {
            1: {"transfundido"},
            2: {"transfundido"},
            3: {"curador_vazio"},
            4: {"transfundido", "enxerto_horto"},
            5: {"o_persistente"},
        },
        VARZEAS_CISTERN_FAMILY_ID: {
            1: {"vigia_hemaris"},
            2: {"condutor_rubro"},
            3: {"vigia_hemaris"},
            4: {"executor_hemaris"},
            5: {"coracao_transferencia"},
        },
    }
    for family_id, encounters in expected.items():
        family = DUNGEON_FAMILIES[family_id]
        for ordinal, creature_ids in encounters.items():
            run = type(
                "Run",
                (),
                {
                    "dungeon_family_id": family_id,
                    "difficulty": "rupture",
                    "initial_group_size": 4,
                    # Rupture economic reference is 60; creature level stays regional.
                    "reference_level": 60,
                },
            )()
            specs = _encounter_specs(run, ordinal)
            assert {spec.creature.creature_id for spec in specs} == creature_ids
            assert {spec.level for spec in specs} == {family.reference_level}
            rewards = _enemy_rewards_for(run, ordinal)
            assert {creature_id for creature_id, _level, _category in rewards} == creature_ids
            assert {level for _creature_id, level, _category in rewards} == {
                family.reference_level
            }

    assert {
        creature.creature_id: creature.category
        for creature in VARZEAS_DUNGEON_CREATURES
    } == {
        "transfundido": "common",
        "curador_vazio": "elite",
        "o_persistente": "boss",
        "condutor_rubro": "elite",
        "executor_hemaris": "elite",
        "coracao_transferencia": "boss",
    }


def test_varzeas_dungeon_distinctive_mastery_evidence_is_exact():
    assert VARZEAS_DISTINCTIVE_ELITE_MASTERY["curador_vazio"] == {
        "first_victory",
        "action:cauterizacao_inadequada",
        "action:placa_procedimento",
        "action:intervencao_brusca",
    }
    assert VARZEAS_DISTINCTIVE_ELITE_MASTERY["condutor_rubro"] == {
        "first_victory",
        "action:linha_pressurizada",
        "action:descarga_fluxo",
        "action:fecho_seguranca",
    }
    assert VARZEAS_DISTINCTIVE_ELITE_MASTERY["executor_hemaris"] == {
        "first_victory",
        "action:fixar_incidente",
        "action:resposta_emergencia",
        "action:imobilizacao_pesada",
    }
    assert VARZEAS_DISTINCTIVE_BOSS_MASTERY["o_persistente"] == {
        "first_victory",
        "phase:persistencia",
        "phase:sem_alta",
        "action:protocolo_continuidade",
        "action:manutencao_repetida",
        "action:intervencao_final",
    }
    assert VARZEAS_DISTINCTIVE_BOSS_MASTERY["coracao_transferencia"] == {
        "first_victory",
        "action:linha_aberta",
        "action:linha_fechada",
        "action:transferencia_final",
    }


def test_varzeas_dungeon_known_and_detail_screens_expose_their_family_callbacks():
    infirmary_id = VARZEAS_INFIRMARY_FAMILY_ID
    cistern_id = VARZEAS_CISTERN_FAMILY_ID
    known = DungeonView(
        kind="known",
        character_id=uuid4(),
        character_name="Aventureiro",
        level=39,
        location="Hortos Hemaris",
        hp=D(500),
        max_hp=D(500),
        vigor=10,
        max_vigor=10,
        known_dungeons=(
            (
                infirmary_id,
                "Enfermaria Afundada",
                "Nv.34–37",
                "Brejos do Pulso",
                "Várzeas Carmesins",
            ),
            (
                cistern_id,
                "Cisterna de Transferência",
                "Nv.38–40",
                "Galerias de Transferência",
                "Várzeas Carmesins",
            ),
        ),
    )
    known_screen = render_dungeons(known)
    known_callbacks = {
        button.callback_data
        for row in known_screen.keyboard.inline_keyboard
        for button in row
    }
    assert "dungeon:varzeas-infirmary" in known_callbacks
    assert "dungeon:varzeas-cistern" in known_callbacks

    for family_id, family_key in ((infirmary_id, "i"), (cistern_id, "t")):
        detail = DungeonView(
            kind="detail",
            character_id=uuid4(),
            character_name="Aventureiro",
            level=39,
            location="Várzeas Carmesins",
            hp=D(500),
            max_hp=D(500),
            vigor=10,
            max_vigor=10,
            family_id=family_id,
            dungeon_name="Masmorra de Teste",
            range_label="Nv.34–40",
            entry_display="Local de Entrada",
            region_display="Várzeas Carmesins",
            minimum_level=34,
            difficulty_gates=(
                ("stable", "available"),
                ("fractured", "available"),
                ("rupture", "first_fractured"),
            ),
        )
        detail_screen = render_dungeons(detail)
        callbacks = {
            button.callback_data
            for row in detail_screen.keyboard.inline_keyboard
            for button in row
        }
        assert f"dungeon:start:{family_key}:s" in callbacks
        assert f"dungeon:group:{family_key}:f" in callbacks
        assert f"dungeon:queue:{family_key}:f" in callbacks


def test_varzeas_dungeon_barrier_durations_and_global_action_default():
    curator = _combat(VARZEAS_INFIRMARY_FAMILY_ID, 3).enemy_actions["placa_procedimento"]
    persistent = _combat(VARZEAS_INFIRMARY_FAMILY_ID, 5)
    conductor = _combat(VARZEAS_CISTERN_FAMILY_ID, 2).enemy_actions["linha_pressurizada"]
    heart_barrier = _combat(VARZEAS_CISTERN_FAMILY_ID, 5).enemy_actions["linha_fechada"]

    for barrier in (curator, conductor):
        assert barrier.self_barrier_duration == 2
        assert barrier.cooldown == 3
        assert barrier.skip_if_barrier_active is True
    protocol = persistent.enemy_actions["protocolo_continuidade"]
    assert protocol.self_barrier_hp_fraction == D("0.08")
    assert protocol.self_barrier_duration == 2
    assert protocol.cooldown == 4
    assert protocol.skip_if_barrier_active is True
    ordinary_barrier = Action(
        "ordinary", "Ordinary", D(0), self_barrier_coefficient=D("0.1")
    )
    assert ordinary_barrier.self_barrier_duration == 0
    assert heart_barrier.self_barrier_hp_fraction == D("0.08")
    assert heart_barrier.self_barrier_duration == 2
    assert heart_barrier.cooldown == 5


def test_varzeas_dungeon_published_action_coefficients_and_cooldowns():
    expected = (
        (VARZEAS_INFIRMARY_FAMILY_ID, 1, "golpe_assimetrico", "1.00", 0, False),
        (VARZEAS_INFIRMARY_FAMILY_ID, 1, "ferida_reaberta", "0.90", 2, False),
        (VARZEAS_INFIRMARY_FAMILY_ID, 3, "braco_suporte", "1.00", 0, False),
        (VARZEAS_INFIRMARY_FAMILY_ID, 3, "cauterizacao_inadequada", "0.85", 3, False),
        (VARZEAS_INFIRMARY_FAMILY_ID, 3, "placa_procedimento", "0", 3, False),
        (VARZEAS_INFIRMARY_FAMILY_ID, 3, "intervencao_brusca", "1.70", 4, True),
        (VARZEAS_INFIRMARY_FAMILY_ID, 5, "golpe_mantido", "1.00", 0, False),
        (VARZEAS_INFIRMARY_FAMILY_ID, 5, "sutura_forcada", "0.85", 3, False),
        (VARZEAS_INFIRMARY_FAMILY_ID, 5, "protocolo_continuidade", "0", 4, False),
        (VARZEAS_INFIRMARY_FAMILY_ID, 5, "manutencao_repetida", "0", 5, False),
        (VARZEAS_INFIRMARY_FAMILY_ID, 5, "intervencao_final", "1.75", 4, True),
        (VARZEAS_CISTERN_FAMILY_ID, 2, "impacto_valvula", "1.05", 0, False),
        (VARZEAS_CISTERN_FAMILY_ID, 2, "linha_pressurizada", "0", 3, False),
        (VARZEAS_CISTERN_FAMILY_ID, 2, "descarga_fluxo", "1.30", 3, False),
        (VARZEAS_CISTERN_FAMILY_ID, 2, "fecho_seguranca", "1.75", 4, True),
        (VARZEAS_CISTERN_FAMILY_ID, 4, "golpe_contencao_executor", "1.10", 0, False),
        (VARZEAS_CISTERN_FAMILY_ID, 4, "fixar_incidente", "0.90", 3, False),
        (VARZEAS_CISTERN_FAMILY_ID, 4, "resposta_emergencia", "1.40", 3, False),
        (VARZEAS_CISTERN_FAMILY_ID, 4, "imobilizacao_pesada", "1.80", 4, True),
        (VARZEAS_CISTERN_FAMILY_ID, 5, "pulso_bomba", "0.80", 3, False),
        (VARZEAS_CISTERN_FAMILY_ID, 5, "pressao_linha", "1.00", 3, False),
        (VARZEAS_CISTERN_FAMILY_ID, 5, "linha_aberta", "0", 5, False),
        (VARZEAS_CISTERN_FAMILY_ID, 5, "linha_fechada", "0", 5, False),
        (VARZEAS_CISTERN_FAMILY_ID, 5, "transferencia_final", "1.10", 5, True),
    )
    for family_id, ordinal, action_id, coefficient, cooldown, prepared in expected:
        action = _combat(family_id, ordinal).enemy_actions[action_id]
        assert action.coefficient == D(coefficient)
        assert action.cooldown == cooldown
        assert action.prepared is prepared

    heart = _combat(VARZEAS_CISTERN_FAMILY_ID, 5)
    opened = {effect.id: effect for effect in heart.enemy_actions["linha_aberta"].self_effects}
    closed = {effect.id: effect for effect in heart.enemy_actions["linha_fechada"].self_effects}
    assert opened["varzeas.cistern.line_open.attack"].magnitude == D("0.08")
    assert opened["varzeas.cistern.line_open.attack"].duration == 2
    assert opened["varzeas.cistern.line_open.defense"].magnitude == D("0.08")
    assert opened["varzeas.cistern.line_open.defense"].duration == 2
    assert closed["varzeas.cistern.line_closed.attack"].magnitude == D("0.08")
    assert closed["varzeas.cistern.line_closed.attack"].duration == 2


def test_varzeas_dungeon_special_recipes_match_published_contracts():
    infirmary = canonical_recipe(
        "recipe.varzeas.enfermaria.mascara_triagem_silenciosa"
    )
    cistern = canonical_recipe("recipe.varzeas.cisterna.peitoral_fluxo_contido")
    assert infirmary is not None
    assert (
        infirmary.profession_id,
        infirmary.required_level,
        infirmary.grade,
        infirmary.rarity,
        infirmary.output_name,
        infirmary.output_slot,
        infirmary.sw,
        infirmary.fixed_crown_cost,
    ) == ("leatherworker", 9, 4, "Raro", "Máscara da Triagem Silenciosa", "Cabeça", 1, None)
    assert [(row.material_id, row.quantity) for row in infirmary.fixed_materials] == [
        ("material.varzeas.couro_de_varzea", 6),
        ("material.varzeas.junco_ferruginoso", 2),
        ("material.varzeas.fragmento_aprimoramento_iv", 4),
        ("material.varzeas.nucleo_enfermaria_afundada", 1),
    ]
    assert cistern is not None
    assert (
        cistern.profession_id,
        cistern.required_level,
        cistern.grade,
        cistern.rarity,
        cistern.output_name,
        cistern.output_slot,
        cistern.sw,
        cistern.fixed_crown_cost,
    ) == ("blacksmith", 10, 4, "Épico", "Peitoral do Fluxo Contido", "Torso", 2, None)
    assert [(row.material_id, row.quantity) for row in cistern.fixed_materials] == [
        ("material.varzeas.ferro_de_salmoura", 14),
        ("material.varzeas.soro_antigo", 6),
        ("material.varzeas.catalisador_elite_iv", 4),
        ("material.varzeas.fragmento_aprimoramento_iv", 12),
        ("material.varzeas.nucleo_cisterna_transferencia", 1),
    ]

def test_varzeas_dungeon_boss_phases_uses_healing_and_telegraph_contracts():
    persistent = _combat(VARZEAS_INFIRMARY_FAMILY_ID, 5)
    assert persistent.phase_id == "I"
    assert [
        (trigger.hp_fraction_at_most, trigger.phase_id)
        for trigger in persistent.phase_triggers
    ] == [
        (D("0.70"), "II"),
        (D("0.35"), "III"),
    ]
    assert persistent.phase_triggers[0].trigger_id == VARZEAS_PERSISTENT_PHASE_II
    assert persistent.phase_triggers[1].trigger_id == VARZEAS_PERSISTENT_PHASE_III
    assert persistent.enemy_actions["protocolo_continuidade"].phase_ids == ("II",)
    assert persistent.enemy_actions["manutencao_repetida"].phase_ids == ("II",)
    heal = persistent.enemy_actions["manutencao_repetida"]
    assert heal.enemy_hp_fraction_at_most == D("0.65")
    assert heal.max_uses_per_combat == 2
    assert heal.heal_coefficient > 0
    assert persistent.enemy_actions["intervencao_final"].phase_ids == ("III",)
    assert persistent.enemy_actions["intervencao_final"].prepared is True

    heart = _combat(VARZEAS_CISTERN_FAMILY_ID, 5)
    assert [
        (trigger.hp_fraction_at_most, trigger.phase_id) for trigger in heart.phase_triggers
    ] == [
        (D("0.65"), "II"),
        (D("0.30"), "III"),
    ]
    assert heart.phase_triggers[0].trigger_id == VARZEAS_HEART_PHASE_II
    assert heart.phase_triggers[1].trigger_id == VARZEAS_HEART_PHASE_III
    opened = heart.enemy_actions["linha_aberta"]
    closed = heart.enemy_actions["linha_fechada"]
    final = heart.enemy_actions["transferencia_final"]
    assert opened.skip_if_self_effect_active == "varzeas.cistern.line_closed.attack"
    assert closed.skip_if_self_effect_active == "varzeas.cistern.line_open.attack"
    assert closed.phase_ids == ("I", "II")
    assert final.phase_ids == ("III",)
    assert final.prepared is True and final.cooldown == 5
    assert final.target_mode == "all_opponents"


def test_varzeas_dungeon_bosses_have_no_unpublished_global_pressure_bonus():
    for family_id in (VARZEAS_INFIRMARY_FAMILY_ID, VARZEAS_CISTERN_FAMILY_ID):
        boss = _combat(family_id, 5)
        assert boss.pressure_start_opportunity == 0
        assert boss.pressure_cap == 0


def test_varzeas_dungeon_self_effect_exclusion_survives_combat_codec():
    combat = _combat(VARZEAS_CISTERN_FAMILY_ID, 5)
    restored = decode(encode(combat))
    assert (
        restored.enemy_actions["linha_aberta"].skip_if_self_effect_active
        == "varzeas.cistern.line_closed.attack"
    )
    assert (
        restored.enemy_actions["linha_fechada"].skip_if_self_effect_active
        == "varzeas.cistern.line_open.attack"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("family_id", "entry_location", "minimum_level"),
    (
        (VARZEAS_INFIRMARY_FAMILY_ID, VARZEAS_BREJOS, 34),
        (VARZEAS_CISTERN_FAMILY_ID, VARZEAS_GALERIAS, 38),
    ),
)
async def test_varzeas_dungeons_use_global_run_settlement_and_run_scoped_checkpoint(
    database, monkeypatch, family_id, entry_location, minimum_level
):
    from asterion.application.dungeons import DungeonService

    actor = 994100 + minimum_level
    character_id, sessions = await _seed_final_campaign(
        database, actor, level=minimum_level
    )
    service = DungeonService(sessions, "ocaso")
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = REGION
        world.location = entry_location
        session.add_all(
            (
                Unlock(
                    character_id=character_id,
                    unlock_id=DUNGEON_FAMILIES[family_id].discovery_unlock,
                ),
                LocationDiscovery(
                    character_id=character_id,
                    location_id=(
                        "varzeas.location.enfermaria_afundada"
                        if family_id == VARZEAS_INFIRMARY_FAMILY_ID
                        else "varzeas.location.cisterna_transferencia"
                    ),
                ),
            )
        )
        braziers_before = set(
            (
                await session.scalars(
                    select(Brazier.brazier_id).where(
                        Brazier.character_id == character_id
                    )
                )
            ).all()
        )

    def controlled_victory(state, action_id, *, target_id=None, actor_key=None):
        actor_key = actor_key or "player"
        if action_id not in allowed_actions(state, actor_key):
            return state
        valid_targets = action_target_ids(state, action_id, actor_key=actor_key)
        if target_id not in valid_targets:
            return state
        updated = deepcopy(state)
        actor_fighter = updated.fighters[actor_key]
        updated.events.append(
            CombatEvent(
                len(updated.events),
                updated.round,
                actor_key,
                action_id,
                target=target_id,
                actor_entity_id=actor_fighter.id,
            )
        )
        for fighter in updated.fighters.values():
            if fighter.side == "enemy" and fighter.required_for_victory:
                fighter.hp = Decimal(0)
        updated.result = "victory"
        updated.version += 1
        return updated

    monkeypatch.setattr("asterion.application.dungeons.act", controlled_victory)
    monkeypatch.setattr(
        "asterion.application.dungeons.roll_brazier",
        lambda _seed, _difficulty: True,
    )
    created = await service.start_solo(actor, "stable", family_id=family_id)
    assert created is not None and created.run_id is not None
    run_id = created.run_id

    current = created
    for ordinal in range(1, 6):
        if current.kind == "brazier":
            current = await service.activate_brazier(
                actor, run_id, current.state_version
            )
            assert current is not None and current.kind == "ready"
        fight = await service.begin_encounter(actor, run_id, current.state_version)
        assert fight is not None and fight.kind == "combat" and fight.combat is not None
        assert fight.activity_id is not None
        targets = action_target_ids(fight.combat, "attack", actor_key="player")
        assert targets
        current = await service.action(
            actor,
            run_id,
            fight.activity_id,
            fight.combat.version,
            "attack",
            targets[0],
        )
        assert current is not None
        if ordinal == 3:
            assert current.kind == "brazier"
    assert current.kind == "completed"

    async with sessions() as session:
        run = await session.get(DungeonRun, run_id)
        assert run is not None and run.status == "completed"
        assert run.brazier_activated is True and run.has_brazier is True
        assert await session.scalar(
            select(func.count(DungeonRunEncounter.run_id)).where(
                DungeonRunEncounter.run_id == run_id
            )
        ) == 5
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"{family_id}.run.{run_id.hex}",
            )
        )
        assert event is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )
        ).all()
        core = [
            row
            for row in components
            if row.kind == "material" and row.item_id == DUNGEON_FAMILIES[family_id].core_id
        ]
        assert len(core) == 1 and core[0].quantity == 1
        boss_creature_id, milestone_xp, feat_id = (
            ("o_persistente", 2718, "feat.varzeas.sem_paciente")
            if family_id == VARZEAS_INFIRMARY_FAMILY_ID
            else ("coracao_transferencia", 3084, "feat.varzeas.fluxo_contido")
        )
        milestone = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"bestiary.first_victory:{boss_creature_id}",
            )
        )
        assert milestone is not None
        milestone_components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == milestone.id
                )
            )
        ).all()
        assert [(row.kind, row.quantity) for row in milestone_components] == [
            ("xp", milestone_xp)
        ]
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == DUNGEON_FAMILIES[family_id].first_clear_prefix + "stable",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == feat_id,
            )
        ) is not None
        bestiary = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == boss_creature_id,
            )
        )
        assert bestiary is not None and bestiary.stage != "dominated"
        evidence = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == boss_creature_id,
                    )
                )
            ).all()
        )
        assert "first_victory" in evidence
        codex_fragments = (
            (
                "codex.fragment.varzeas.enfermaria.afundada",
                "codex.fragment.varzeas.enfermaria.rotinas_de_suporte",
            )
            if family_id == VARZEAS_INFIRMARY_FAMILY_ID
            else (
                "codex.fragment.varzeas.cisterna.transferencia",
                "codex.fragment.varzeas.cisterna.linhas_ativas",
            )
        )
        found_fragments = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id,
                        CodexFragment.fragment_id.in_(codex_fragments),
                    )
                )
            ).all()
        )
        assert found_fragments == set(codex_fragments)
        braziers_after = set(
            (
                await session.scalars(
                    select(Brazier.brazier_id).where(
                        Brazier.character_id == character_id
                    )
                )
            ).all()
        )
        assert braziers_after == braziers_before

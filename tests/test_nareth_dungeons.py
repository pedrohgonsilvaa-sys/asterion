from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.dungeons import (
    DUNGEON_FAMILIES,
    DungeonService,
)
from asterion.application.knowledge_catalog import (
    CODEX_BY_ID,
    CREATURE_PRESENTATION,
    LOCATION_LABELS,
)
from asterion.domain.combat import (
    CombatEvent,
    _damage_aura_reduction,
    _enemy_action,
    _fighter_stat,
    _perform,
    _resolve_phase_triggers,
    action_target_ids,
    allowed_actions,
)
from asterion.domain.dungeons import DIFFICULTIES
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.nareth_bosses import configure_nareth_campaign_boss
from asterion.domain.nareth_dungeons import (
    NARETH_GALLERIES_FAMILY_ID,
    NARETH_GALLERIES_PHASE_II,
    NARETH_GALLERIES_PHASE_III,
    NARETH_GALLERIES_RETURN_RESOLVED,
    NARETH_OBSERVATORY_FAMILY_ID,
    NARETH_OBSERVATORY_PHASE_II,
    NARETH_OBSERVATORY_PHASE_III,
    create_nareth_dungeon_combat,
    nareth_dungeon_encounter_specs,
)
from asterion.domain.road import (
    CREATURE_CATALOG,
    NARETH_ARCONTE_INVERTIDO,
    NARETH_DUNGEON_BESTIARY_CREATURES,
    RULESET,
    CreatureCombatantSpec,
    create_creature_party_combat,
    creature_for,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Brazier,
    Character,
    DungeonRun,
    DungeonRunMember,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_s6_p6_integration import _seed_final_campaign

D = Decimal


def _combat(creature):
    return create_creature_party_combat(
        uuid4(),
        "Iona",
        "sentinela",
        "remanescente",
        D(3000),
        (CreatureCombatantSpec(creature, creature.unlock_level, "enemy"),),
        player_level=creature.unlock_level,
        ruleset_version=RULESET,
    )


def _dungeon_combat(family_id, ordinal, *, group_size=1):
    return create_nareth_dungeon_combat(
        uuid4(),
        family_id=family_id,
        name="Iona",
        character_class="sentinela",
        race="remanescente",
        hp=D(5000),
        level=30,
        difficulty="stable",
        reference_level=26 if family_id == NARETH_GALLERIES_FAMILY_ID else 29,
        equipment=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        ordinal=ordinal,
        run_seed=f"nareth-{family_id}-{ordinal}-{group_size}",
        initial_group_size=group_size,
    )


def test_nareth_barrier_durations_are_explicitly_two_turns_without_global_default():
    expected = {
        "escaravelho_canal": ("carapaca_baixa", D("0.70"), D(0), 4, None),
        "casco_invertido": ("placas_contrarias", D("0.85"), D(0), 3, None),
        "vigia_meridiano": ("egide_meridiano", D("0.90"), D(0), 3, None),
        "custodio_invertido": ("couraça_referencia", D("1.00"), D(0), 3, None),
        "escavador_eixo": ("travar_trilho", D("0.85"), D(0), 3, None),
        "o_que_retorna": ("casco_ciclo", D(0), D("0.08"), 4, 2),
        "custodio_meridiano": ("travar_referencia", D("0.90"), D(0), 3, None),
        "guardiao_referencia": ("ancora_local", D(0), D("0.08"), 4, 2),
    }
    by_id = {creature.creature_id: creature for creature in CREATURE_CATALOG}
    by_id.update(
        {
            creature.creature_id: creature
            for creature in NARETH_DUNGEON_BESTIARY_CREATURES
        }
    )

    for creature_id, (
        action_id,
        coefficient,
        hp_fraction,
        cooldown,
        max_uses,
    ) in expected.items():
        action = _combat(by_id[creature_id]).enemy_actions[action_id]
        assert action.self_barrier_duration == 2
        assert action.self_barrier_coefficient == coefficient
        assert action.self_barrier_hp_fraction == hp_fraction
        assert action.cooldown == cooldown
        assert action.max_uses_per_combat == max_uses

    archon = configure_nareth_campaign_boss(
        _combat(NARETH_ARCONTE_INVERTIDO), "arconte_invertido", shared=False
    )
    protocol = archon.enemy_actions["protocolo_continuidade"]
    assert protocol.self_barrier_duration == 2
    assert protocol.self_barrier_hp_fraction == D("0.08")
    assert protocol.cooldown == 5
    assert protocol.max_uses_per_combat == 2
    assert protocol.skip_if_barrier_active is True
    assert protocol.phase_ids == ("II",)


@pytest.mark.parametrize(
    ("family_id", "expected"),
    (
        (
            NARETH_GALLERIES_FAMILY_ID,
            (
                ("escaravelho_canal",),
                ("errante_valas", "escaravelho_canal"),
                ("escavador_eixo",),
                (
                    "casco_invertido",
                    "nareth_service_beacon_mechanic",
                    "nareth_service_beacon_mechanic",
                    "nareth_service_beacon_mechanic",
                ),
                (
                    "o_que_retorna",
                    "nareth_return_marker_mechanic",
                    "nareth_return_marker_mechanic",
                ),
            ),
        ),
        (
            NARETH_OBSERVATORY_FAMILY_ID,
            (
                ("vigia_meridiano",),
                ("vigia_meridiano", "casco_invertido"),
                ("custodio_meridiano",),
                (
                    "preceptor_eixo",
                    "nareth_calibration_beacon_mechanic",
                    "nareth_calibration_beacon_mechanic",
                    "nareth_calibration_beacon_mechanic",
                    "nareth_calibration_beacon_mechanic",
                ),
                (
                    "guardiao_referencia",
                    "nareth_calibration_axis_mechanic",
                    "nareth_calibration_axis_mechanic",
                    "nareth_calibration_axis_mechanic",
                ),
            ),
        ),
    ),
)
def test_nareth_dungeon_rosters_are_exact_and_mechanical_entities_are_not_cataloged(
    family_id, expected
):
    for ordinal, expected_ids in enumerate(expected, start=1):
        specs = nareth_dungeon_encounter_specs(family_id, ordinal, "stable", 1, 29)
        assert tuple(spec.creature.creature_id for spec in specs) == expected_ids
        assert all(spec.variant is None for spec in specs)

    catalog_ids = {creature.creature_id for creature in CREATURE_CATALOG}
    assert {
        "nareth_service_beacon_mechanic",
        "nareth_return_marker_mechanic",
        "nareth_calibration_beacon_mechanic",
        "nareth_calibration_axis_mechanic",
    }.isdisjoint(catalog_ids)
    assert creature_for("o_que_retorna").name == "O Que Retorna"
    assert creature_for("guardiao_referencia").name == "Guardião da Referência"


def test_nareth_dungeon_barriers_and_recalibration_follow_published_values():
    excavator = _dungeon_combat(NARETH_GALLERIES_FAMILY_ID, 3)
    assert excavator.enemy_actions["travar_trilho"].self_barrier_coefficient == D("0.85")
    assert excavator.enemy_actions["travar_trilho"].self_barrier_duration == 2
    assert excavator.enemy_actions["travar_trilho"].cooldown == 3

    returning = _dungeon_combat(NARETH_GALLERIES_FAMILY_ID, 5)
    shell = returning.enemy_actions["e0_casco_ciclo"]
    assert shell.self_barrier_hp_fraction == D("0.08")
    assert shell.self_barrier_duration == 2
    assert shell.cooldown == 4
    assert shell.max_uses_per_combat == 2
    assert shell.skip_if_barrier_active is True

    custodian = _dungeon_combat(NARETH_OBSERVATORY_FAMILY_ID, 3)
    lock = custodian.enemy_actions["travar_referencia"]
    assert lock.self_barrier_coefficient == D("0.90")
    assert lock.self_barrier_duration == 2
    assert lock.cooldown == 3

    preceptor = _dungeon_combat(NARETH_OBSERVATORY_FAMILY_ID, 4)
    recalibrate = preceptor.enemy_actions["e0_recalibrar_baliza"]
    assert recalibrate.revive_fighter_keys == (
        "calibration_1",
        "calibration_2",
        "calibration_3",
        "calibration_4",
    )
    assert recalibrate.revive_hp_fraction == D("0.50")
    assert recalibrate.max_uses_per_combat == 1

    guardian = _dungeon_combat(NARETH_OBSERVATORY_FAMILY_ID, 5)
    anchor = guardian.enemy_actions["e0_ancora_local"]
    assert anchor.self_barrier_hp_fraction == D("0.08")
    assert anchor.self_barrier_duration == 2
    assert anchor.cooldown == 4
    assert anchor.max_uses_per_combat == 2
    assert anchor.phase_ids == ("I", "II")
    assert guardian.enemy_actions["e0_referencia_absoluta"].phase_ids == ("III",)


def test_nareth_preceptor_recalibrates_exactly_one_destroyed_beacon():
    combat = _dungeon_combat(NARETH_OBSERVATORY_FAMILY_ID, 4)
    beacons = tuple(combat.fighters[f"calibration_{index}"] for index in range(1, 5))
    beacons[0].hp = D(0)
    beacons[1].hp = D(0)

    action_id = _enemy_action(combat, "preceptor")
    assert action_id == "e0_recalibrar_baliza"
    assert _perform(combat, "preceptor", action_id)
    assert sum(beacon.hp > 0 for beacon in beacons) == 3
    assert sum(beacon.hp == beacon.stats.hp * D("0.50") for beacon in beacons) == 1
    assert sum(beacon.hp == 0 for beacon in beacons) == 1
    assert combat.fighters["preceptor"].action_use_counts[action_id] == 1


def test_nareth_dungeon_bosses_use_global_dungeon_scaling_and_preserve_phase_entities():
    for family_id, ordinal, key in (
        (NARETH_GALLERIES_FAMILY_ID, 5, "enemy"),
        (NARETH_OBSERVATORY_FAMILY_ID, 5, "guardian"),
    ):
        for size in range(1, 5):
            state = _dungeon_combat(family_id, ordinal, group_size=size)
            profile = DIFFICULTIES["stable"]
            hp_group = D(1) + D("0.78") * (size - 1)
            attack_group = D(1) + D("0.07") * (size - 1)
            solo = _combat(
                next(
                    spec.creature
                    for spec in nareth_dungeon_encounter_specs(family_id, ordinal, "stable", 1, 29)
                    if spec.fighter_key == key
                )
            ).fighters["enemy"].stats
            expected_hp_factor = (
                D(3)
                / D("2.20")
                * profile.boss_hp_multiplier
                * hp_group
            )
            expected_attack_factor = profile.boss_attack_multiplier * attack_group
            assert state.fighters[key].stats.hp == solo.hp * expected_hp_factor
            assert state.fighters[key].stats.attack == solo.attack * expected_attack_factor
            assert state.fighters[key].stats.defense == solo.defense
            assert state.fighters[key].stats.agility == solo.agility

    galleries = _dungeon_combat(NARETH_GALLERIES_FAMILY_ID, 5)
    galleries.fighters["enemy"].hp = galleries.fighters["enemy"].stats.hp * D("0.70")
    _resolve_phase_triggers(galleries)
    assert galleries.phase_id == "II"
    assert NARETH_GALLERIES_PHASE_II in galleries.phase_triggered_ids
    assert {key for key in ("marker_1", "marker_2") if galleries.fighters[key].hp > 0} == {
        "marker_1",
        "marker_2",
    }
    galleries.fighters["enemy"].hp = galleries.fighters["enemy"].stats.hp * D("0.35")
    hp_before = galleries.fighters["enemy"].hp
    _resolve_phase_triggers(galleries)
    assert galleries.phase_id == "III"
    assert NARETH_GALLERIES_PHASE_III in galleries.phase_triggered_ids
    assert galleries.fighters["enemy"].hp == min(
        galleries.fighters["enemy"].stats.hp,
        hp_before + galleries.fighters["enemy"].stats.hp * D("0.06"),
    )
    assert all(galleries.fighters[key].hp == 0 for key in ("marker_1", "marker_2"))
    hp_after = galleries.fighters["enemy"].hp
    _resolve_phase_triggers(galleries)
    assert galleries.fighters["enemy"].hp == hp_after
    assert sum(
        event.action == f"phase:{NARETH_GALLERIES_RETURN_RESOLVED}"
        for event in galleries.mechanic_events
    ) == 1

    observatory = _dungeon_combat(NARETH_OBSERVATORY_FAMILY_ID, 5)
    boss = observatory.fighters["guardian"]
    boss.hp = boss.stats.hp * D("0.70")
    _resolve_phase_triggers(observatory)
    assert observatory.phase_id == "II"
    assert NARETH_OBSERVATORY_PHASE_II in observatory.phase_triggered_ids
    axes = ("axis_1", "axis_2", "axis_3")
    assert all(observatory.fighters[key].hp > 0 for key in axes)
    assert len(observatory.damage_auras) == 1
    boss.hp = boss.stats.hp * D("0.35")
    _resolve_phase_triggers(observatory)
    assert observatory.phase_id == "III"
    assert NARETH_OBSERVATORY_PHASE_III in observatory.phase_triggered_ids
    assert all(observatory.fighters[key].hp > 0 for key in axes)


def test_nareth_dungeon_mechanics_are_targetable_and_aura_stacks_are_live():
    circuit = _dungeon_combat(NARETH_GALLERIES_FAMILY_ID, 4)
    targets = set(action_target_ids(circuit, "attack", actor_key="player"))
    beacons = tuple(circuit.fighters[f"beacon_{index}"] for index in range(1, 4))
    assert all(beacon.id in targets for beacon in beacons)
    casco_defense = circuit.fighters["casco"].stats.defense
    assert _fighter_stat(circuit, "casco", "defense") == casco_defense * D("1.15")
    beacons[0].hp = 0
    assert _fighter_stat(circuit, "casco", "defense") == casco_defense * D("1.10")

    recalibration = _dungeon_combat(NARETH_OBSERVATORY_FAMILY_ID, 4)
    targets = set(action_target_ids(recalibration, "attack", actor_key="player"))
    calibration_beacons = tuple(
        recalibration.fighters[f"calibration_{index}"] for index in range(1, 5)
    )
    assert all(beacon.id in targets for beacon in calibration_beacons)
    preceptor_defense = recalibration.fighters["preceptor"].stats.defense
    assert _fighter_stat(recalibration, "preceptor", "defense") == (
        preceptor_defense * D("1.20")
    )

    guardian = _dungeon_combat(NARETH_OBSERVATORY_FAMILY_ID, 5)
    axes = tuple(guardian.fighters[f"axis_{index}"] for index in range(1, 4))
    targets = set(action_target_ids(guardian, "attack", actor_key="player"))
    assert all(axis.id not in targets for axis in axes)
    boss = guardian.fighters["guardian"]
    boss.hp = boss.stats.hp * D("0.70")
    _resolve_phase_triggers(guardian)
    targets = set(action_target_ids(guardian, "attack", actor_key="player"))
    assert all(axis.id in targets for axis in axes)
    assert _damage_aura_reduction(guardian, "guardian") == D("0.12")
    axes[0].hp = 0
    assert _damage_aura_reduction(guardian, "guardian") == D("0.08")


def test_nareth_dungeon_phase_and_mechanical_state_survive_codec_round_trip():
    galleries = _dungeon_combat(NARETH_GALLERIES_FAMILY_ID, 5)
    galleries.fighters["enemy"].hp = galleries.fighters["enemy"].stats.hp * D("0.70")
    _resolve_phase_triggers(galleries)
    galleries.fighters["enemy"].hp = galleries.fighters["enemy"].stats.hp * D("0.35")
    _resolve_phase_triggers(galleries)
    restored = decode(encode(galleries), galleries.id, galleries.ruleset, galleries.version)
    assert restored.phase_id == "III"
    assert restored.phase_triggered_ids == galleries.phase_triggered_ids
    assert restored.mechanic_events == galleries.mechanic_events
    assert {key: restored.fighters[key].hp for key in ("marker_1", "marker_2")} == {
        key: galleries.fighters[key].hp for key in ("marker_1", "marker_2")
    }

    observatory = _dungeon_combat(NARETH_OBSERVATORY_FAMILY_ID, 5)
    observatory.fighters["guardian"].hp = (
        observatory.fighters["guardian"].stats.hp * D("0.70")
    )
    _resolve_phase_triggers(observatory)
    restored = decode(
        encode(observatory), observatory.id, observatory.ruleset, observatory.version
    )
    assert restored.phase_id == "II"
    assert restored.damage_auras == observatory.damage_auras
    assert {key: restored.fighters[key].hp for key in ("axis_1", "axis_2", "axis_3")} == {
        key: observatory.fighters[key].hp for key in ("axis_1", "axis_2", "axis_3")
    }


def test_old_phase_trigger_snapshots_decode_without_nareth_extension_fields():
    combat = _dungeon_combat(NARETH_GALLERIES_FAMILY_ID, 5)
    payload = encode(combat)
    for trigger in payload["phase_triggers"]:
        trigger.pop("resolution_id", None)
        trigger.pop("heal_source_per_active_fighter_fraction", None)
        trigger.pop("consume_active_fighter_keys", None)

    restored = decode(payload, combat.id, combat.ruleset, combat.version)
    assert all(trigger.resolution_id is None for trigger in restored.phase_triggers)
    assert all(
        trigger.heal_source_per_active_fighter_fraction == 0
        and trigger.consume_active_fighter_keys == ()
        for trigger in restored.phase_triggers
    )


def test_nareth_dungeon_families_recipes_codex_and_bestiary_habitats_are_registered():
    expected = {
        NARETH_GALLERIES_FAMILY_ID: (
            "Galerias do Meridiano",
            "Nv.24–27",
            "Canais Secos",
            26,
            24,
            "recipe.nareth.galerias.relicario_circuito_retornado",
        ),
        NARETH_OBSERVATORY_FAMILY_ID: (
            "Observatório Afundado",
            "Nv.28–30",
            "Observatório do Eixo",
            29,
            28,
            "recipe.nareth.observatorio.guarda_referencia",
        ),
    }
    for family_id, values in expected.items():
        family = DUNGEON_FAMILIES[family_id]
        assert (
            family.name,
            family.range_label,
            family.entry_location,
            family.reference_level,
            family.minimum_level,
            family.recipe_unlock,
        ) == values

    for entry_id in (
        "codex.location.galerias_do_meridiano",
        "codex.history.juncao_circular",
        "codex.history.circuitos_de_servico",
        "codex.history.o_que_retorna",
        "codex.history.marcos_de_retorno",
        "codex.location.observatorio_afundado",
        "codex.history.sala_de_recalibracao",
        "codex.history.eixos_de_calibracao",
        "codex.history.guardiao_referencia",
        "codex.history.referencias_afundadas",
    ):
        assert entry_id in CODEX_BY_ID

    creature_ids = {
        creature.creature_id for creature in NARETH_DUNGEON_BESTIARY_CREATURES
    }
    assert creature_ids <= CREATURE_PRESENTATION.keys()
    for creature_id in creature_ids:
        assert all(
            location in LOCATION_LABELS
            for location in CREATURE_PRESENTATION[creature_id].habitats
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("family_id", "entry_location", "minimum_level", "first_creature"),
    (
        (
            NARETH_GALLERIES_FAMILY_ID,
            "Canais Secos",
            24,
            "Escaravelho de Canal",
        ),
        (
            NARETH_OBSERVATORY_FAMILY_ID,
            "Observatório do Eixo",
            28,
            "Vigia do Meridiano",
        ),
    ),
)
async def test_nareth_dungeon_discovery_gate_run_start_and_reconnect(
    database, family_id, entry_location, minimum_level, first_creature
):
    from asterion.application.road import NARETH_REGION

    actor = 993000 + minimum_level
    character_id, sessions = await _seed_final_campaign(
        database, actor, level=minimum_level
    )
    service = DungeonService(sessions, "ocaso")
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = NARETH_REGION
        world.location = entry_location

    blocked = await service.start_solo(actor, "stable", family_id=family_id)
    assert blocked is not None and blocked.reason == "gate"
    async with sessions.begin() as session:
        session.add(Unlock(character_id=character_id, unlock_id=family_id))

    detail = await service.detail(actor, family_id)
    assert detail is not None and dict(detail.difficulty_gates)["stable"] == "available"
    started = await service.start_solo(actor, "stable", family_id=family_id)
    assert started is not None and started.run_id is not None
    combat = await service.begin_encounter(actor, started.run_id, started.state_version)
    assert combat is not None and combat.kind == "combat"
    assert combat.combat is not None and combat.combat.fighters["enemy"].name == first_creature
    resumed = await service.resume(actor)
    assert resumed is not None and resumed.kind == "combat"
    assert resumed.run_id == started.run_id
    assert resumed.combat is not None and resumed.combat.id == combat.combat.id

    async with sessions() as session:
        run = await session.get(DungeonRun, started.run_id)
        member = await session.scalar(
            select(DungeonRunMember).where(DungeonRunMember.run_id == started.run_id)
        )
        assert run is not None and run.dungeon_family_id == family_id
        assert member is not None and member.vigor_reserved == DIFFICULTIES["stable"].vigor


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("family_id", "entry_location", "minimum_level"),
    (
        (NARETH_GALLERIES_FAMILY_ID, "Canais Secos", 24),
        (NARETH_OBSERVATORY_FAMILY_ID, "Observatório do Eixo", 28),
    ),
)
async def test_nareth_dungeon_invited_group_uses_shared_global_run(
    database, family_id, entry_location, minimum_level
):
    from asterion.application.road import NARETH_REGION
    from asterion.infrastructure.db.models import DungeonRun

    actors = (993400 + minimum_level, 993500 + minimum_level)
    seeded = [
        await _seed_final_campaign(database, actor, level=minimum_level)
        for actor in actors
    ]
    character_ids = [row[0] for row in seeded]
    sessions = seeded[0][1]
    async with sessions.begin() as session:
        for character_id in character_ids:
            world = await session.get(WorldState, character_id)
            assert world is not None
            world.region = NARETH_REGION
            world.location = entry_location
            session.add(Unlock(character_id=character_id, unlock_id=family_id))

    service = DungeonService(sessions, "ocaso")
    lobby = await service.prepare_group(actors[0], family_id, "stable")
    assert lobby is not None and lobby.lobby_id is not None
    async with sessions() as session:
        invitee = await session.get(Character, character_ids[1])
        assert invitee is not None
        invitee_name = invitee.name
    invited = await service.invite_by_name(
        actors[0], lobby.lobby_id, lobby.lobby_version, invitee_name
    )
    assert invited is not None and invited.reason == f"invited:{invitee_name}"
    pending = await service.pending_invite(actors[1])
    assert pending is not None and pending.invite_id is not None
    accepted = await service.respond_invite(actors[1], pending.invite_id, accept=True)
    assert accepted is not None and accepted.kind == "lobby"
    confirmation = await service.open_entry_confirmation(
        actors[0], lobby.lobby_id, accepted.lobby_version
    )
    assert confirmation is not None and confirmation.kind == "confirming"
    waiting = await service.confirm_entry(
        actors[0], lobby.lobby_id, confirmation.lobby_version, confirm=True
    )
    assert waiting is not None and waiting.kind == "confirming"
    entered = await service.confirm_entry(
        actors[1], lobby.lobby_id, confirmation.lobby_version, confirm=True
    )
    assert entered is not None and entered.kind == "ready" and entered.run_id is not None

    async with sessions() as session:
        run = await session.get(DungeonRun, entered.run_id)
        assert run is not None and run.initial_group_size == 2
    encounter = await service.begin_encounter(
        actors[0], entered.run_id, entered.state_version
    )
    assert encounter is not None and encounter.kind == "combat"
    assert encounter.combat is not None
    assert {key for key in encounter.combat.fighters if key.startswith("member_")} == {
        "member_1",
        "member_2",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("family_id", "entry_location", "minimum_level"),
    (
        (NARETH_GALLERIES_FAMILY_ID, "Canais Secos", 24),
        (NARETH_OBSERVATORY_FAMILY_ID, "Observatório do Eixo", 28),
    ),
)
async def test_nareth_dungeon_full_run_uses_global_settlement_and_run_scoped_brazier(
    database, monkeypatch, family_id, entry_location, minimum_level
):
    """Exercise the public run lifecycle with controlled combat outcomes, not a bot QA win."""
    from asterion.application.road import NARETH_REGION

    actor = 993200 + minimum_level
    character_id, sessions = await _seed_final_campaign(
        database, actor, level=minimum_level
    )
    service = DungeonService(sessions, "ocaso")
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        character = await session.get(Character, character_id)
        assert world is not None and character is not None
        world.region = NARETH_REGION
        world.location = entry_location
        session.add(Unlock(character_id=character_id, unlock_id=family_id))
        xp_before = character.xp
        crowns_before = character.crowns
        braziers_before = set(
            (
                await session.scalars(
                    select(Brazier.brazier_id).where(Brazier.character_id == character_id)
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
        # This harness verifies service progression and settlement. Encounter mechanics
        # and targetability are asserted separately against the real combat engine.
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
                fighter.hp = D(0)
        updated.result = "victory"
        updated.version += 1
        return updated

    monkeypatch.setattr("asterion.application.dungeons.act", controlled_victory)
    created = await service.start_solo(actor, "stable", family_id=family_id)
    assert created is not None and created.run_id is not None
    run_id = created.run_id
    async with sessions.begin() as session:
        run = await session.get(DungeonRun, run_id)
        assert run is not None
        # Force the deterministic test case to represent a run whose global roll
        # awarded the temporary brazier after encounter three.
        run.has_brazier = True

    current = created
    final_fight = None
    for ordinal in range(1, 6):
        if current.kind == "brazier":
            current = await service.activate_brazier(actor, run_id, current.state_version)
            assert current is not None and current.kind == "ready"
        fight = await service.begin_encounter(actor, run_id, current.state_version)
        assert fight is not None and fight.kind == "combat" and fight.combat is not None
        assert fight.activity_id is not None
        targets = action_target_ids(fight.combat, "attack", actor_key="player")
        assert targets
        final_fight = fight
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

    stale = await service.action(
        actor,
        run_id,
        final_fight.activity_id,
        final_fight.combat.version,
        "attack",
        "enemy",
    )
    assert stale is not None and stale.kind == "stale"

    async with sessions() as session:
        run = await session.get(DungeonRun, run_id)
        character = await session.get(Character, character_id)
        events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"{family_id}.run.{run_id.hex}",
                )
            )
        ).all()
        assert run is not None and run.status == "completed"
        assert character is not None
        assert len(events) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == events[0].id)
            )
        ).all()
        core = [
            row
            for row in components
            if row.kind == "material" and row.item_id == DUNGEON_FAMILIES[family_id].core_id
        ]
        assert len(core) == 1
        assert core[0].quantity == DIFFICULTIES["stable"].cores
        assert character.xp >= xp_before
        assert character.crowns >= crowns_before
        braziers_after = set(
            (
                await session.scalars(
                    select(Brazier.brazier_id).where(Brazier.character_id == character_id)
                )
            ).all()
        )
        assert braziers_after == braziers_before

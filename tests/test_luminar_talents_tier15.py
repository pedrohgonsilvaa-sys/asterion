from dataclasses import replace
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest

from asterion.domain.arts import LUMINAR_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, Combat, Fighter, act, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatRng,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    class_stats,
    direct_damage,
    finalize_primary_stats,
    racial_stats,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    _static_talent_secondary_modifier_totals,
    static_talent_modifiers,
    static_talent_secondary_modifiers,
    talent_points_at_level,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.combat_codec import decode, encode

ZERO = D(0)
JULGAMENTO_PRECISO = "talent.luminar.julgamento_preciso"
CORPO_CONSAGRADO = "talent.luminar.corpo_consagrado"
CONTRALUZ_PERSISTENTE = "talent.luminar.contraluz_persistente"
SOLAR = LUMINAR_ART_IDS["explosao_solar"]
FULGOR = LUMINAR_ART_IDS["fulgor"]
JULGAMENTO = LUMINAR_ART_IDS["julgamento"]
LUZ = LUMINAR_ART_IDS["luz_restauradora"]


def _internal_stats(
    talent_ids: tuple[str, ...],
    *,
    path: str | None = None,
    equipment: EquipmentStatContribution | None = None,
):
    definitions = tuple(TALENT_DEFINITIONS[talent_id] for talent_id in talent_ids)
    return _resolve_combat_stats_with_static_talent_modifiers(
        "luminar",
        34,
        "remanescente",
        equipment,
        path,
        _static_talent_modifier_totals(definitions),
        _static_talent_secondary_modifier_totals(definitions),
    )


def _fighter(
    fighter_id: str,
    *,
    hp: str = "10000",
    attack: str = "20",
    defense: str = "0",
    agility: str = "0",
    evasion: str = "0",
    crit: str = "0",
    block: str = "0",
    side: str = "enemy",
    character_class: str = "",
    race: str = "",
    takes_turn: bool = False,
) -> Fighter:
    stats = CombatStats(
        D(hp), D(attack), D(defense), D(agility),
        crit=D(crit), evasion=D(evasion), block=D(block),
    )
    return Fighter(
        fighter_id,
        fighter_id,
        34,
        stats,
        D(hp),
        race=race,
        character_class=character_class,
        side=side,
        takes_turn=takes_turn,
        required_for_victory=False,
    )


def _combat(
    *,
    path: str | None = None,
    arts: tuple[str, ...] = (SOLAR,),
    enemy_count: int = 1,
    talents: tuple[str, ...] = (),
    crit: str = "5",
    enemy_evasion: str = "0",
    enemy_defense: str = "0",
    combat_id: UUID | None = None,
    pvp: bool = False,
) -> Combat:
    stats = resolve_combat_stats("luminar", 34, "remanescente", selected_path=path)
    player = PROFILE.create(uuid4(), "Luminar", "luminar", "remanescente", stats.hp)
    player.tutorial = None
    player.ruleset = CURRENT_COMBAT_RULESET
    actor = player.fighters["player"]
    actor.level = 34
    actor.character_class = "luminar"
    actor.selected_path = path
    actor.talent_ids = talents
    actor.side = "player"
    actor.takes_turn = True
    actor.stats = replace(
        stats,
        hp=D(1000),
        attack=D(200),
        defense=D(100),
        agility=D(100),
        per=ZERO,
        crit=D(crit),
        evasion=ZERO,
        block=ZERO,
    )
    actor.hp = actor.stats.hp

    fighters = {"player": actor}
    for index in range(enemy_count):
        enemy = _fighter(
            f"enemy-{index}",
            defense=enemy_defense,
            evasion=enemy_evasion,
        )
        fighters[enemy.id] = enemy

    state = Combat(
        combat_id or uuid4(),
        CURRENT_COMBAT_RULESET,
        fighters,
        class_player_actions("luminar", arts, path),
        {"wait": Action("enemy.wait", "Aguardar", ZERO, target_mode="self")},
        ("wait",),
    )
    state.pvp_mode = pvp
    return start_combat(state)


def _events(state: Combat, action_id: str):
    actor_id = state.fighters["player"].id
    return [
        event
        for event in state.events
        if event.action == action_id and event.actor_entity_id == actor_id
    ]


def _set_luminar_state(state: Combat, kind: str, remaining: int = 2) -> None:
    actor = state.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": kind,
        "remaining": remaining,
        "applied_opportunity": actor.opportunity,
    }


def test_luminar_tier15_catalog_and_public_gate():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25})
    assert talent_points_at_level(15) == 3
    expected = {
        JULGAMENTO_PRECISO: ("Julgamento Preciso", D(15), D(0), D(0)),
        CORPO_CONSAGRADO: ("Corpo Consagrado", D(15), D(0), D("0.02")),
        CONTRALUZ_PERSISTENTE: ("Contraluz Persistente", D(15), D(0), D(0)),
    }
    for talent_id, (name, level, crit, defense) in expected.items():
        definition = TALENT_DEFINITIONS[talent_id]
        assert (definition.name, definition.level) == (name, level)
        assert definition.crit_points == crit
        assert definition.defense_percent == defense
        assert validate_active_talent_ids("luminar", 15, (talent_id,)) == (talent_id,)
        assert validate_talent_choices("luminar", 15, ((3, talent_id),)) == (
            (3, talent_id),
        )
        static_talent_modifiers("luminar", 15, (talent_id,))
        static_talent_secondary_modifiers("luminar", 15, (talent_id,))
        resolve_combat_stats("luminar", 15, "remanescente", talent_ids=(talent_id,))
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("luminar", 14, (talent_id,))
    tier25 = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "luminar" and definition.level == 25
    )
    assert validate_active_talent_ids("luminar", 25, (tier25,)) == (tier25,)
    future = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "luminar" and definition.level == 35
    )
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("luminar", 60, (future,))


@pytest.mark.parametrize("path", (None, "guardiao", "inquisidor"))
def test_corpo_consagrado_composes_two_percent_defense_once_with_all_static_stages(path):
    equipment = EquipmentStatContribution(
        defense=D("13.25"),
        crit=D("3.5"),
        rune_percent=(ZERO, ZERO, D("0.035"), ZERO, ZERO, ZERO, ZERO, ZERO),
        rune_points=(ZERO, ZERO, D("0.4"), ZERO, ZERO, ZERO, ZERO, ZERO),
        enchantment_percent=(ZERO, ZERO, D("0.025"), ZERO, ZERO, ZERO, ZERO, ZERO),
        enchantment_points=(ZERO, ZERO, D("0.3"), ZERO, ZERO, ZERO, ZERO, ZERO),
    )
    actual = _internal_stats((CORPO_CONSAGRADO,), path=path, equipment=equipment)
    baseline = _internal_stats((), path=path, equipment=equipment)

    base = class_stats("luminar", 34)
    path_defense = PATH_DEFINITIONS[path].defense if path else ZERO
    raw = base.defense * (D(1) + path_defense) * D("1.02") + equipment.defense
    raw = raw * (D(1) + equipment.rune_percent[2]) + equipment.rune_points[2]
    raw = (
        raw * (D(1) + equipment.enchantment_percent[2])
        + equipment.enchantment_points[2]
    )
    expected = finalize_primary_stats(
        racial_stats(replace(base, defense=raw), "remanescente")
    ).defense

    assert actual.defense == expected
    assert actual.defense > baseline.defense
    assert (
        actual.hp,
        actual.attack,
        actual.agility,
        actual.per,
        actual.crit,
        actual.evasion,
        actual.block,
    ) == (
        baseline.hp,
        baseline.attack,
        baseline.agility,
        baseline.per,
        baseline.crit,
        baseline.evasion,
        baseline.block,
    )
    assert _internal_stats((CORPO_CONSAGRADO,), path=path, equipment=equipment) == actual


def test_corpo_consagrado_composed_defense_survives_codec_without_reapplication():
    stats = _internal_stats((CORPO_CONSAGRADO,), path="guardiao")
    state = _combat(path="guardiao")
    state.fighters["player"].stats = stats
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].stats == stats
    assert _internal_stats((CORPO_CONSAGRADO,), path="guardiao") == stats


@pytest.mark.parametrize(
    ("path", "power"),
    ((None, D("1.10")), ("guardiao", D("1.06")), ("inquisidor", D("1.15"))),
)
def test_julgamento_preciso_buffs_each_solar_target_and_consumes_once(path, power):
    state = _combat(
        path=path,
        talents=(JULGAMENTO_PRECISO,),
        enemy_count=3,
        crit="5",
    )
    actor = state.fighters["player"]
    _set_luminar_state(state, "julgamento")
    state.rng_cursor = 0

    result = act(state, SOLAR)
    events = _events(result, SOLAR)

    assert len(events) == 3
    assert {event.path_power_multiplier for event in events} == {power}
    assert {event.path_crit_bonus for event in events} == {D(2)}
    assert "luminar_state" not in result.fighters["player"].path_state
    assert sum(bool(event.class_resource_changes) for event in events) == 1
    assert not any(
        "luminar.fulgor_gerado" in event.path_triggers for event in events
    )

    rng = CombatRng(result.id, 0)
    expected_crit = []
    for event in events:
        expected_crit.append(
            rng.chance(
                D("0.07"),
                f"critical:{actor.id}:{SOLAR}:{event.target}",
            )
        )
    assert [event.critical for event in events] == expected_crit


def test_julgamento_preciso_changes_actual_crit_chance_not_damage_critical_multiplier():
    state = _combat(
        arts=(SOLAR,),
        talents=(JULGAMENTO_PRECISO,),
        combat_id=UUID(int=42),
        crit="5",
    )
    _set_luminar_state(state, "julgamento")
    state.rng_cursor = 0
    result = act(state, SOLAR)
    event = _events(result, SOLAR)[0]
    purpose = f"critical:{state.fighters['player'].id}:{SOLAR}:enemy-0"

    assert not CombatRng(result.id, 0).chance(D("0.05"), purpose)
    assert CombatRng(result.id, 0).chance(D("0.07"), purpose)
    assert event.critical is True
    assert event.path_crit_bonus == D(2)
    assert event.calculated_damage == direct_damage(
        D(200), D("0.85") * D("1.10"), ZERO, 34, critical=True
    )


def test_julgamento_preciso_respects_pvp_crit_cap_of_forty_points():
    state = _combat(
        arts=(SOLAR,),
        talents=(JULGAMENTO_PRECISO,),
        combat_id=UUID(int=10),
        crit="45",
        pvp=True,
    )
    _set_luminar_state(state, "julgamento")
    state.rng_cursor = 0
    result = act(state, SOLAR)
    event = _events(result, SOLAR)[0]
    purpose = f"critical:{state.fighters['player'].id}:{SOLAR}:enemy-0"

    assert not CombatRng(result.id, 0).chance(D("0.40"), purpose)
    assert CombatRng(result.id, 0).chance(D("0.47"), purpose)
    assert event.critical is False
    assert event.path_crit_bonus == D(2)


@pytest.mark.parametrize("kind", ("fulgor", None))
def test_julgamento_preciso_does_not_apply_without_consuming_julgamento(kind):
    state = _combat(talents=(JULGAMENTO_PRECISO,))
    if kind is not None:
        _set_luminar_state(state, kind)
    result = act(state, SOLAR)
    event = _events(result, SOLAR)[0]
    assert event.path_crit_bonus == ZERO
    if kind == "fulgor":
        assert result.fighters["player"].path_state["luminar_state"]["kind"] == "fulgor"


@pytest.mark.parametrize("action_id", (FULGOR, JULGAMENTO, SOLAR))
def test_julgamento_preciso_is_shared_by_eligible_luminar_offenses(action_id):
    state = _combat(arts=(action_id,), talents=(JULGAMENTO_PRECISO,))
    _set_luminar_state(state, "julgamento")
    target_id = state.fighters["enemy-0"].id
    result = act(state, action_id, target_id=target_id)
    events = _events(result, action_id)
    assert len(events) == 1
    assert events[0].path_crit_bonus == D(2)
    assert "luminar_state" not in result.fighters["player"].path_state


def test_julgamento_consumption_is_committed_even_after_evasion_or_full_barrier():
    evaded = _combat(talents=(JULGAMENTO_PRECISO,), enemy_evasion="100")
    _set_luminar_state(evaded, "julgamento")
    after_evasion = act(evaded, SOLAR)
    event = _events(after_evasion, SOLAR)[0]
    assert event.dodged
    assert event.path_crit_bonus == D(2)
    assert "luminar_state" not in after_evasion.fighters["player"].path_state

    blocked = _combat(talents=(JULGAMENTO_PRECISO,))
    _set_luminar_state(blocked, "julgamento")
    target = blocked.fighters["enemy-0"]
    target.barrier = D(100000)
    target.barrier_remaining = 2
    after_barrier = act(blocked, SOLAR)
    barrier_event = _events(after_barrier, SOLAR)[0]
    assert barrier_event.effective_damage == ZERO
    assert barrier_event.path_crit_bonus == D(2)
    assert "luminar_state" not in after_barrier.fighters["player"].path_state


def test_invalid_solar_target_preserves_julgamento_and_does_not_start_cooldown():
    state = _combat(talents=(JULGAMENTO_PRECISO,))
    _set_luminar_state(state, "julgamento")
    actor = state.fighters["player"]
    assert act(state, SOLAR, target_id="outside-encounter") is state
    assert actor.path_state["luminar_state"]["kind"] == "julgamento"
    assert not actor.cooldowns
    assert not _events(state, SOLAR)


@pytest.mark.parametrize(
    ("talents", "expected_remaining"),
    (((), 2), ((CONTRALUZ_PERSISTENTE,), 3)),
)
def test_explosao_solar_generates_one_fulgor_after_aoe_resolution(
    talents, expected_remaining
):
    state = _combat(talents=talents, enemy_count=3)
    result = act(state, SOLAR)
    events = _events(result, SOLAR)
    fulgor = result.fighters["player"].path_state["luminar_state"]
    assert len(events) == 3
    assert {event.path_power_multiplier for event in events} == {D(1)}
    assert fulgor["kind"] == "fulgor"
    assert fulgor["remaining"] == expected_remaining
    assert fulgor["applied_opportunity"] == state.fighters["player"].opportunity
    assert sum(bool(event.class_resource_changes) for event in events) == 0


@pytest.mark.parametrize(
    ("talents", "expected_remaining"),
    (((), 2), ((CONTRALUZ_PERSISTENTE,), 3)),
)
def test_offensive_renews_fulgor_without_stacking(talents, expected_remaining):
    state = _combat(talents=talents)
    _set_luminar_state(state, "fulgor", remaining=1)
    result = act(state, SOLAR)
    current = result.fighters["player"].path_state["luminar_state"]
    assert current["kind"] == "fulgor"
    assert current["remaining"] == expected_remaining
    assert all(event.path_crit_bonus == ZERO for event in _events(result, SOLAR))


@pytest.mark.parametrize(
    ("talents", "expected_remaining"),
    (((), 2), ((CONTRALUZ_PERSISTENTE,), 3)),
)
def test_support_generates_julgamento_after_resolution(talents, expected_remaining):
    state = _combat(arts=(LUZ,), talents=talents)
    actor = state.fighters["player"]
    result = act(state, LUZ, target_id=actor.id)
    event = _events(result, LUZ)[0]
    assert event.healed == ZERO
    state_entry = result.fighters["player"].path_state["luminar_state"]
    assert state_entry["kind"] == "julgamento"
    assert state_entry["remaining"] == expected_remaining
    assert "luminar.fulgor_gerado" not in event.path_triggers


def test_support_consumes_fulgor_without_generating_opposite_state_even_at_zero_heal():
    state = _combat(arts=(LUZ,), talents=(CONTRALUZ_PERSISTENTE,))
    actor = state.fighters["player"]
    _set_luminar_state(state, "fulgor", remaining=3)
    result = act(state, LUZ, target_id=actor.id)
    event = _events(result, LUZ)[0]
    assert event.effective_healing == ZERO
    assert "luminar_state" not in result.fighters["player"].path_state
    assert "luminar.fulgor_consumido" in event.path_triggers
    assert "luminar.julgamento_gerado" not in event.path_triggers


def test_luz_restauradora_renews_julgamento_instead_of_generating_fulgor():
    state = _combat(arts=(LUZ,), talents=(CONTRALUZ_PERSISTENTE,))
    actor = state.fighters["player"]
    _set_luminar_state(state, "julgamento", remaining=1)
    result = act(state, LUZ, target_id=actor.id)
    event = _events(result, LUZ)[0]
    assert result.fighters["player"].path_state["luminar_state"]["kind"] == "julgamento"
    assert result.fighters["player"].path_state["luminar_state"]["remaining"] == 3
    assert "luminar.julgamento_gerado" in event.path_triggers
    assert "luminar.fulgor_gerado" not in event.path_triggers


def test_persistent_state_window_expires_on_luminar_opportunities_and_survives_reconnect():
    state = _combat(talents=(CONTRALUZ_PERSISTENTE,))
    generated = act(state, SOLAR)
    actor = generated.fighters["player"]
    assert actor.path_state["luminar_state"]["remaining"] == 3

    restored = decode(encode(generated), generated.id, generated.ruleset, generated.version)
    assert restored.fighters["player"].path_state["luminar_state"] == actor.path_state[
        "luminar_state"
    ]
    first = act(restored, "attack", target_id="enemy-0")
    assert first.fighters["player"].path_state["luminar_state"]["remaining"] == 2
    second = act(first, "attack", target_id="enemy-0")
    assert second.fighters["player"].path_state["luminar_state"]["remaining"] == 1
    third = act(second, "attack", target_id="enemy-0")
    assert "luminar_state" not in third.fighters["player"].path_state


def test_julgamento_aoe_crit_is_per_target_and_resource_consumption_is_per_action():
    state = _combat(
        talents=(JULGAMENTO_PRECISO,),
        enemy_count=3,
        combat_id=UUID(int=90210),
    )
    _set_luminar_state(state, "julgamento")
    state.rng_cursor = 0
    result = act(state, SOLAR)
    events = _events(result, SOLAR)
    assert len(events) == 3
    assert {event.path_crit_bonus for event in events} == {D(2)}
    assert sum(bool(event.class_resource_changes) for event in events) == 1
    assert "luminar_state" not in result.fighters["player"].path_state


def test_all_three_nv15_talents_coexist_in_controlled_combat_state():
    ids = (JULGAMENTO_PRECISO, CORPO_CONSAGRADO, CONTRALUZ_PERSISTENTE)
    stats = _internal_stats(ids, path="inquisidor")
    assert stats.defense == _internal_stats((CORPO_CONSAGRADO,), path="inquisidor").defense
    assert stats.crit == D(5)

    state = _combat(path="inquisidor", talents=ids)
    state.fighters["player"].stats = replace(stats, hp=D(1000), attack=D(200), crit=D(5))
    _set_luminar_state(state, "julgamento")
    result = act(state, SOLAR)
    event = _events(result, SOLAR)[0]
    assert event.path_power_multiplier == D("1.15")
    assert event.path_crit_bonus == D(2)
    assert "luminar_state" not in result.fighters["player"].path_state
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25})

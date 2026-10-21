import asyncio
from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.active_arts import (
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.application.round import RoundService
from asterion.bot.character_progression_ui import (
    _art_mechanics_lines,
    render_art_detail,
    render_art_slot_choice,
)
from asterion.bot.combat_ui import event_line
from asterion.bot.doctrines_ui import doctrine_art_ids
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ACTIVE_ART_IDS_BY_CLASS,
    LUMINAR_ART_IDS,
    LUMINAR_ART_LEVELS,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    BarrierLayer,
    Combat,
    CombatPhaseTrigger,
    Fighter,
    act,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    direct_damage,
    resolve_combat_stats,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterActiveArtSlot,
)

SOLAR = LUMINAR_ART_IDS["explosao_solar"]


def _fighter(
    fighter_id: str,
    *,
    hp: str = "5000",
    attack: str = "10",
    defense: str = "0",
    agility: str = "0",
    evasion: str = "0",
    crit: str = "0",
    side: str = "enemy",
    character_class: str = "",
    race: str = "",
    takes_turn: bool = False,
    required_for_victory: bool = False,
) -> Fighter:
    stats = CombatStats(
        D(hp),
        D(attack),
        D(defense),
        D(agility),
        evasion=D(evasion),
        crit=D(crit),
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
        required_for_victory=required_for_victory,
    )


def _combat(
    *,
    path: str | None = None,
    arts: tuple[str, ...] = (SOLAR,),
    count: int = 2,
    race: str = "remanescente",
    talents: tuple[str, ...] = (),
    enemies: tuple[Fighter, ...] = (),
    phase_triggers: tuple[CombatPhaseTrigger, ...] = (),
) -> Combat:
    player = _fighter(
        "player",
        hp="1000",
        attack="200",
        defense="100",
        agility="100",
        side="player",
        character_class="luminar",
        race=race,
        takes_turn=True,
    )
    player.selected_path = path
    player.talent_ids = talents
    fighters = {"player": player}
    for index in range(count):
        enemy = _fighter(f"enemy-{index}")
        fighters[enemy.id] = enemy
    for enemy in enemies:
        fighters[enemy.id] = enemy
    state = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        fighters,
        class_player_actions("luminar", arts, path),
        {"wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")},
        ("wait",),
        phase_triggers=phase_triggers,
    )
    return start_combat(state)


def _solar_events(state: Combat):
    return [event for event in state.events if event.actor == "player" and event.action == SOLAR]


def test_solar_has_canonical_class_art_and_shared_aoe_action_contract():
    definition = ACTIVE_ART_DEFINITIONS[SOLAR]
    assert SOLAR == "class_art.luminar.explosao_solar"
    assert definition.character_class == "luminar"
    assert definition.min_level == LUMINAR_ART_LEVELS[SOLAR] == 34
    assert definition.path_id is None
    assert definition.weapon_requirement == frozenset()
    assert SOLAR in ACTIVE_ART_IDS_BY_CLASS["luminar"]
    for path in (None, "guardiao", "inquisidor"):
        action = class_player_actions("luminar", (SOLAR,), path)[SOLAR]
        assert action.name == "Explosão Solar"
        assert action.coefficient == D("0.85")
        assert action.target_mode == "all_opponents"
        assert action.cooldown == 3 and action.hit_count == 1
        assert action.attack_debuff == 0 and not action.native_dot_kind
        assert action.heal_coefficient == action.target_barrier_coefficient == 0
    with pytest.raises(ValueError):
        class_player_actions("errante", (SOLAR,))
    with pytest.raises(ValueError):
        class_player_actions("luminar", (SOLAR, SOLAR, SOLAR, SOLAR))

    lines = _art_mechanics_lines(class_player_actions("luminar", (SOLAR,))[SOLAR])
    assert "⚔️ Dano · 85% ATQ" in lines
    assert "🎯 Alvo · Todos os Inimigos" in lines
    assert "⏳ Recarga · 3 Rodadas" in lines


@pytest.mark.parametrize("target_count", (1, 2, 3, 4))
def test_solar_resolves_85_percent_per_enemy_once_and_generates_one_fulgor(target_count):
    state = _combat(count=target_count)
    player = state.fighters["player"]
    opportunity = player.opportunity

    result = act(state, SOLAR)
    events = _solar_events(result)

    assert len(events) == target_count
    assert len({event.target for event in events}) == target_count
    assert len({event.action_instance_id for event in events}) == 1
    assert all(event.hit_count == 1 for event in events)
    for event in events:
        target = next(fighter for fighter in result.fighters.values() if fighter.id == event.target)
        assert event.calculated_damage == direct_damage(
            D(200), D("0.85"), target.stats.defense, 34, critical=False
        )
    updated_player = result.fighters["player"]
    assert updated_player.opportunity == opportunity + 1
    assert updated_player.action_use_counts[SOLAR] == 1
    assert updated_player.cooldowns[SOLAR] == opportunity + 3
    assert updated_player.path_state["luminar_state"]["kind"] == "fulgor"
    assert updated_player.path_state["luminar_state"]["remaining"] == 2
    assert sum(
        "luminar.fulgor_gerado" in event.path_triggers for event in events
    ) == 1
    generated_event = next(
        event for event in events if "luminar.fulgor_gerado" in event.path_triggers
    )
    assert "Fulgor gerado/renovado" in event_line(
        result, generated_event, viewer_key="player"
    )
    assert "Fulgor gerado/renovado" not in event_line(
        result, generated_event, viewer_key=events[0].target
    )


def test_solar_excludes_defeated_allied_and_out_of_encounter_fighters():
    dead = _fighter("dead-enemy", hp="0")
    ally = _fighter("ally", hp="1000", side="player")
    state = _combat(count=0, enemies=(dead, ally))
    result = act(state, SOLAR)
    assert {event.target for event in _solar_events(result)} == set()
    assert result is state


def test_solar_rejects_explicit_invalid_target_without_spending_julgamento():
    state = _combat(count=2)
    player = state.fighters["player"]
    player.path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 2,
        "applied_opportunity": player.opportunity,
    }
    ally = _fighter("ally", hp="1000", side="player")
    state.fighters[ally.id] = ally

    assert act(state, SOLAR, target_id="outside-encounter") is state
    assert act(state, SOLAR, target_id="ally") is state
    assert act(state, SOLAR, target_id="player") is state
    assert player.cooldowns == {}
    assert player.action_use_counts == {}
    assert player.path_state["luminar_state"]["kind"] == "julgamento"

    result = act(state, SOLAR, target_id="enemy-0")
    assert len(_solar_events(result)) == 2
    assert "luminar_state" not in result.fighters["player"].path_state


@pytest.mark.parametrize(
    ("path", "power"),
    ((None, D("1.10")), ("guardiao", D("1.06")), ("inquisidor", D("1.15"))),
)
def test_solar_consumes_julgamento_once_and_applies_path_power_to_every_target(path, power):
    state = _combat(path=path, count=3, talents=(
        "talent.luminar.julgamento_preciso",
        "talent.luminar.alternancia_radiante",
    ))
    player = state.fighters["player"]
    player.path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 2,
        "applied_opportunity": player.opportunity,
    }

    result = act(state, SOLAR)
    events = _solar_events(result)
    updated_player = result.fighters["player"]

    assert len(events) == 3
    assert {event.path_power_multiplier for event in events} == {power}
    assert all(event.path_crit_bonus == D(2) for event in events)
    assert "luminar_state" not in updated_player.path_state
    assert not any("luminar.fulgor_gerado" in event.path_triggers for event in events)
    assert sum(
        event.class_resource_changes == (("luminar_state", player.id, 1, 0),)
        for event in events
    ) == 1
    resource_event = next(event for event in events if event.class_resource_changes)
    assert "Julgamento consumido" in event_line(
        result, resource_event, viewer_key="player"
    )
    assert "Julgamento consumido" not in event_line(
        result, resource_event, viewer_key=resource_event.target
    )
    assert all("luminar.julgamento_consumido" in event.path_triggers for event in events)
    buffs = [
        effect for effect in updated_player.effects
        if effect.id == "class_mechanic.luminar.alternancia_radiante.agility"
    ]
    assert len(buffs) == 1 and buffs[0].remaining == 1


def test_solar_renews_fulgor_and_respects_persistent_duration():
    state = _combat(
        path="guardiao",
        talents=("talent.luminar.contraluz_persistente",),
    )
    player = state.fighters["player"]
    player.path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 1,
        "applied_opportunity": player.opportunity,
    }

    result = act(state, SOLAR)
    events = _solar_events(result)
    assert result.fighters["player"].path_state["luminar_state"]["kind"] == "fulgor"
    assert result.fighters["player"].path_state["luminar_state"]["remaining"] == 3
    assert not any("luminar.fulgor_consumido" in event.path_triggers for event in events)
    assert not any("luminar.julgamento_gerado" in event.path_triggers for event in events)
    assert sum("luminar.fulgor_gerado" in event.path_triggers for event in events) == 1


def test_solar_consumes_julgamento_on_committed_all_target_evasion():
    enemies = tuple(
        _fighter(f"enemy-{index}", evasion="100") for index in range(2)
    )
    state = _combat(count=0, enemies=enemies)
    player = state.fighters["player"]
    player.path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 1,
        "applied_opportunity": player.opportunity,
    }

    result = act(state, SOLAR)
    events = _solar_events(result)
    assert len(events) == 2 and all(event.dodged for event in events)
    assert "luminar_state" not in result.fighters["player"].path_state
    assert not any("luminar.fulgor_gerado" in event.path_triggers for event in events)
    assert sum(bool(event.class_resource_changes) for event in events) == 1


def test_solar_uses_independent_barriers_and_aggregates_vampirism_once():
    state = _combat(count=2, race="hemario")
    player = state.fighters["player"]
    player.hp = D(300)
    player.path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 2,
        "applied_opportunity": player.opportunity,
    }
    first, second = state.fighters["enemy-0"], state.fighters["enemy-1"]
    first.barrier_layers = [
        BarrierLayer("ward-a", "ward.a", D(50), 2, 1),
        BarrierLayer("ward-b", "ward.b", D(35), 3, 1),
    ]
    second.barrier = D(10000)
    second.barrier_remaining = 2

    result = act(state, SOLAR)
    events = {event.target: event for event in _solar_events(result)}
    assert events[first.id].barrier_absorbed == D(85)
    assert events[second.id].effective_damage == 0
    total_hp_damage = sum((event.effective_damage for event in events.values()), D(0))
    expected_heal = min(total_hp_damage * D("0.12"), D(30)).to_integral_value(
        rounding="ROUND_FLOOR"
    )
    assert result.fighters["player"].hp == D(300) + expected_heal
    assert sum(event.healed > 0 for event in events.values()) == 1
    assert "luminar_state" not in result.fighters["player"].path_state
    assert not any(
        "luminar.fulgor_gerado" in event.path_triggers for event in events.values()
    )
    assert sum(bool(event.class_resource_changes) for event in events.values()) == 1


def test_solar_aoe_uses_pre_event_target_state_before_phase_triggers():
    boss = _fighter("boss", hp="20")
    add = _fighter("add", hp="1000", defense="20")
    phase = CombatPhaseTrigger(
        "boss.crossed-half",
        "boss",
        D("0.50"),
        consume_active_fighter_keys=("add",),
        phase_id="II",
    )
    state = _combat(count=0, enemies=(boss, add), phase_triggers=(phase,))

    result = act(state, SOLAR)
    events = {event.target: event for event in _solar_events(result)}
    assert set(events) == {"boss", "add"}
    assert events["boss"].effective_damage > 0
    assert events["add"].calculated_damage == direct_damage(
        D(200), D("0.85"), D(20), 34, critical=False
    )
    assert result.phase_id == "II"


def test_solar_codec_reconnect_keeps_aoe_and_julgamento_consumption_idempotent():
    state = _combat(count=2)
    state.configuration_snapshot = {"active_arts": ({"slot": 2, "art_id": SOLAR},)}
    state.fighters["player"].path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 2,
        "applied_opportunity": state.fighters["player"].opportunity,
    }
    restored = decode(encode(state), state.id, state.ruleset, state.version)

    result = act(restored, "a2")
    restored_result = decode(encode(result), result.id, result.ruleset, result.version)
    assert len(_solar_events(restored_result)) == 2
    assert "luminar_state" not in restored_result.fighters["player"].path_state
    assert restored_result.fighters["player"].cooldowns[SOLAR]
    assert act(restored_result, "a2") is restored_result
    assert len(_solar_events(restored_result)) == 2


def test_solar_round_uses_shared_aoe_priority_only_with_multiple_targets():
    service = RoundService(None, "ocaso")
    round_state = type("Round", (), {"prepared_heal": False, "prepared_purify": False})()
    character = type("Character", (), {"id": uuid4()})()
    arts = (LUMINAR_ART_IDS["fulgor"], SOLAR)

    multiple = _combat(arts=arts, count=2)
    multiple.fighters["player"].last_action = "defend"
    assert asyncio.run(
        service._choose_round_action(object(), character, round_state, multiple)
    ) == ("action", SOLAR)

    single = _combat(arts=arts, count=1)
    single.fighters["player"].last_action = "defend"
    assert asyncio.run(
        service._choose_round_action(object(), character, round_state, single)
    ) == ("action", LUMINAR_ART_IDS["fulgor"])


def _actor_id() -> int:
    return 700_000_000 + uuid4().int % 100_000_000


async def _seed_luminar(database, *, level: int, path: str | None):
    _, sessions = database
    actor = _actor_id()
    character_id = uuid4()
    stats = resolve_combat_stats(
        "luminar", level, "remanescente", selected_path=path
    )
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor)[-5:])
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Solar{suffix}",
                race="remanescente",
                character_class="luminar",
                selected_path=path,
                stage="menu:ready",
                ruleset_version="gdd-1.6.0-baseline-1.0",
                level=level,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
    return actor, character_id, sessions


@pytest.mark.asyncio
@pytest.mark.parametrize("path", (None, "guardiao", "inquisidor"))
async def test_solar_level_gate_configuration_persistence_doctrine_and_ui(database, path):
    actor, character_id, sessions = await _seed_luminar(database, level=33, path=path)
    service = ActiveArtService(sessions, "ocaso")

    locked = await service.view(actor)
    assert locked is not None and SOLAR not in locked.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as rejected:
        await service.equip_art(actor, 1, SOLAR)
    assert rejected.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 34
    eligible = await service.view(actor)
    assert eligible is not None and SOLAR in eligible.available_art_ids
    screen = render_art_detail(eligible, SOLAR)
    assert "Explosão Solar" in screen.text
    assert "85% ATQ" in screen.text
    assert "Todos os Inimigos" in screen.text
    assert "Recarga · 3 Rodadas" in screen.text
    assert "Requisito de arma · Nenhum" in screen.text
    slot_screen = render_art_slot_choice(eligible, SOLAR)
    assert "85% ATQ" in slot_screen.text
    assert "Requisito de arma · Nenhum" in slot_screen.text

    await service.equip_art(actor, 3, SOLAR)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        configuration = await load_active_art_configuration(session, character)
        rows = list(
            (
                await session.scalars(
                    select(CharacterActiveArtSlot).where(
                        CharacterActiveArtSlot.character_id == character_id
                    )
                )
            ).all()
        )
    assert configuration.art_ids == (SOLAR,)
    assert [(row.slot, row.art_id) for row in rows] == [(3, SOLAR)]

    collection = DoctrineCollectionView(
        character_name="Luminar",
        character_class="luminar",
        selected_path=path,
        configuration_version=1,
        foreground=False,
        current_configuration={"path": path, "equipment": {}, "arts": {}, "talents": []},
        doctrines=(),
        crowns=1000,
        level=34,
    )
    doctrine = DoctrineView(
        doctrine_id=uuid4(),
        name="Explosão Solar",
        revision=1,
        configuration={"path": path, "equipment": {}, "arts": {"3": SOLAR}, "talents": []},
        is_current=False,
        incomplete_reason=None,
        can_apply=True,
    )
    assert SOLAR in doctrine_art_ids(collection, doctrine)

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 33
    ineligible = await service.view(actor)
    assert ineligible is not None and SOLAR in ineligible.ineligible_art_ids

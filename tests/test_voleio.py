import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.active_arts import (
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.application.equipment import equipment_instance_payload
from asterion.bot.character_progression_ui import _art_mechanics_lines
from asterion.bot.doctrines_ui import doctrine_art_ids
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    VIGIA_ART_IDS,
    weapon_requirement_satisfied,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    BarrierLayer,
    Combat,
    CombatPhaseTrigger,
    CombatStatAura,
    Fighter,
    act,
    action_target_ids,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    direct_damage,
    resolve_combat_stats,
)
from asterion.domain.road import materialize_equipment
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterActiveArtSlot,
    CharacterEquipmentSlot,
    EquipmentItem,
    GameActivity,
)

D = Decimal
VOLEIO = VIGIA_ART_IDS["voleio"]


def _fighter(
    key: str,
    *,
    fighter_id: str | None = None,
    hp: str = "5000",
    attack: str = "10",
    defense: str = "0",
    agility: str = "10",
    side: str = "enemy",
    character_class: str = "",
    race: str = "",
    takes_turn: bool = False,
    evasion: str = "0",
    crit: str = "0",
) -> Fighter:
    stats = CombatStats(
        D(hp), D(attack), D(defense), D(agility), evasion=D(evasion), crit=D(crit)
    )
    return Fighter(
        fighter_id or key,
        key,
        34,
        stats,
        D(hp),
        race=race,
        character_class=character_class,
        side=side,
        takes_turn=takes_turn,
        required_for_victory=False,
    )


def _battle(
    *,
    count: int = 2,
    path: str | None = None,
    arts: tuple[str, ...] = (VOLEIO,),
    race: str = "remanescente",
    attack: str = "200",
    enemies: tuple[Fighter, ...] | None = None,
    stat_auras: tuple[CombatStatAura, ...] = (),
    phase_triggers: tuple[CombatPhaseTrigger, ...] = (),
) -> Combat:
    player = _fighter(
        "player",
        fighter_id="player",
        hp="1000",
        attack=attack,
        defense="100",
        agility="100",
        side="player",
        character_class="vigia",
        race=race,
        takes_turn=True,
    )
    player.selected_path = path
    fighters = {"player": player}
    for index in range(count):
        key = f"enemy-{index}"
        fighters[key] = _fighter(key)
    for enemy in enemies or ():
        fighters[enemy.id] = enemy
    state = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        fighters,
        class_player_actions("vigia", arts, path),
        {},
        (),
        stat_auras=stat_auras,
        phase_triggers=phase_triggers,
    )
    return start_combat(state)


def _art_events(state: Combat):
    return [event for event in state.events if event.actor == "player" and event.action == VOLEIO]


def test_voleio_has_canonical_id_level_weapon_requirement_and_hud_contract():
    action = class_player_actions("vigia", (VOLEIO,))[VOLEIO]
    definition = ACTIVE_ART_DEFINITIONS[VOLEIO]
    assert VOLEIO == "class_art.vigia.voleio"
    assert definition.character_class == "vigia" and definition.min_level == 34
    assert action.coefficient == D("0.75")
    assert action.cooldown == 3 and action.hit_count == 1
    assert action.target_mode == "all_opponents"
    assert definition.weapon_requirement == frozenset(
        {"weapon.compat.bow", "weapon.compat.crossbow"}
    )
    assert weapon_requirement_satisfied(definition, frozenset({"weapon.compat.bow"}))
    assert weapon_requirement_satisfied(
        definition, frozenset({"weapon.compat.crossbow"})
    )
    assert not weapon_requirement_satisfied(definition, frozenset({"weapon.compat.melee"}))
    lines = _art_mechanics_lines(action)
    assert "⚔️ Dano · 75% ATQ" in lines
    assert "🎯 Alvo · Todos os Inimigos" in lines
    assert "⏳ Recarga · 3 Rodadas" in lines


@pytest.mark.parametrize("target_count", (1, 2, 3, 4))
def test_voleio_resolves_75_percent_per_living_enemy_once_per_action(target_count):
    state = _battle(count=target_count)
    player = state.fighters["player"]
    opportunity_before = player.opportunity
    result = act(state, VOLEIO)
    events = _art_events(result)

    assert len(events) == target_count
    assert len({event.target for event in events}) == target_count
    assert len({event.action_instance_id for event in events}) == 1
    assert all(event.hit_count == 1 for event in events)
    for event in events:
        target_key = next(
            key
            for key, fighter in result.fighters.items()
            if fighter.id == event.target
        )
        target = result.fighters[target_key]
        assert event.calculated_damage == direct_damage(
            D(200), D("0.75"), target.stats.defense, 34, critical=False
        )
    updated_player = result.fighters["player"]
    assert updated_player.action_use_counts[VOLEIO] == 1
    assert updated_player.cooldowns[VOLEIO] == opportunity_before + 3
    assert updated_player.opportunity == opportunity_before + 1


def test_voleio_resolves_target_specific_evasion_and_excludes_invalid_targets():
    dodger = _fighter("enemy-dodge", fighter_id="enemy-dodge", evasion="100")
    dead = _fighter("enemy-dead", fighter_id="enemy-dead", hp="0")
    ally = _fighter(
        "ally", fighter_id="ally", side="player", hp="1000", takes_turn=False
    )
    state = _battle(count=0, enemies=(dodger, dead, ally))
    assert set(action_target_ids(state, VOLEIO)) == {"enemy-dodge"}
    result = act(state, VOLEIO)
    events = _art_events(result)
    assert len(events) == 1
    assert events[0].target == "enemy-dodge" and events[0].dodged
    assert result.fighters["ally"].hp == D("1000")
    assert result.fighters["enemy-dead"].hp == D(0)


def test_voleio_uses_each_targets_barriers_and_keeps_mira_out_of_secondaries():
    state = _battle(count=2, path="rastreador")
    first, second = state.fighters["enemy-0"], state.fighters["enemy-1"]
    first.barrier_layers = [
        BarrierLayer("ward-a", "ward.a", D(35), 2, 1),
        BarrierLayer("ward-b", "ward.b", D(35), 2, 1),
    ]
    second.barrier = D(10_000)
    second.barrier_remaining = 2

    result = act(state, VOLEIO, target_id=first.id)
    events = {event.target: event for event in _art_events(result)}
    assert events[first.id].calculated_damage > 0
    assert events[first.id].barrier_absorbed == min(
        D(events[first.id].calculated_damage), D(70)
    )
    assert events[second.id].effective_damage == 0
    assert events[second.id].barrier_absorbed == D(events[second.id].calculated_damage)
    assert result.fighters["enemy-0"].path_state["aim_from"]["player"]["stacks"] == 1
    assert "aim_from" not in result.fighters["enemy-1"].path_state
    assert result.fighters["enemy-1"].barrier == D(10_000) - D(
        events[second.id].calculated_damage
    )


def test_voleio_without_primary_does_not_generate_mira_and_primary_miss_does_not_mark():
    no_primary = _battle(count=2, path="atirador")
    result = act(no_primary, VOLEIO)
    assert all("aim_from" not in fighter.path_state for fighter in result.fighters.values())

    miss = _battle(count=2, path="atirador")
    miss.fighters["enemy-0"].stats = CombatStats(
        D(5000), D(10), D(0), D(10), evasion=D(100)
    )
    result = act(miss, VOLEIO, target_id="enemy-0")
    events = {event.target: event for event in _art_events(result)}
    assert events["enemy-0"].dodged
    assert "aim_from" not in result.fighters["enemy-0"].path_state
    assert "aim_from" not in result.fighters["enemy-1"].path_state


def test_voleio_generates_one_primary_mira_after_positive_damage_even_through_barrier():
    state = _battle(count=2, path="rastreador")
    primary = state.fighters["enemy-0"]
    primary.barrier = D(10_000)
    primary.barrier_remaining = 2
    result = act(state, VOLEIO, target_id=primary.id)
    events = {event.target: event for event in _art_events(result)}
    assert events[primary.id].calculated_damage > 0
    assert events[primary.id].effective_damage == 0
    assert result.fighters[primary.id].path_state["aim_from"]["player"]["stacks"] == 1
    assert "aim_from" not in result.fighters["enemy-1"].path_state


def test_voleio_aquisicao_rapida_is_per_target_but_base_mira_stays_primary_only():
    state = _battle(count=3, path="atirador")
    state.fighters["player"].talent_ids = ("talent.vigia.aquisicao_rapida",)
    result = act(state, VOLEIO, target_id="enemy-0")
    assert result.fighters["enemy-0"].path_state["aim_from"]["player"]["stacks"] == 2
    assert result.fighters["player"].path_state["aim_acquisition_used"] == {
        "enemy-0": True,
        "enemy-1": True,
        "enemy-2": True,
    }
    assert result.fighters["enemy-1"].path_state["aim_from"]["player"]["stacks"] == 1
    assert result.fighters["enemy-2"].path_state["aim_from"]["player"]["stacks"] == 1

    without_primary = _battle(count=2, path="atirador")
    without_primary.fighters["player"].talent_ids = ("talent.vigia.aquisicao_rapida",)
    result = act(without_primary, VOLEIO)
    # The normal AoE Mira exception still requires an explicit primary. The
    # Talento's separately published per-target exception grants one Mira to
    # every target that takes eligible direct damage.
    assert all(
        result.fighters[key].path_state["aim_from"]["player"]["stacks"] == 1
        for key in ("enemy-0", "enemy-1")
    )


def test_voleio_uses_each_target_mira_snapshot_without_retroactive_bonus():
    state = _battle(count=2, path="atirador")
    primary = state.fighters["enemy-0"]
    primary.path_state["aim_from"] = {
        "player": {"stacks": 3, "remaining": 2, "applied_opportunity": 1}
    }
    result = act(state, VOLEIO, target_id=primary.id)
    events = {event.target: event for event in _art_events(result)}
    # The event records the post-resolution Mira total; the PER value is frozen
    # from the three stacks present before Voleio generated one more.
    assert events[primary.id].aim_stacks == 4
    assert events[primary.id].path_per_bonus == D(9)
    assert events[primary.id].path_crit_bonus == D(0)
    assert result.fighters[primary.id].path_state["aim_from"]["player"]["stacks"] == 4
    assert events["enemy-1"].aim_stacks == 0
    assert events["enemy-1"].path_per_bonus == D(0)
    assert events["enemy-1"].path_crit_bonus == D(0)
    assert "aim_from" not in result.fighters["enemy-1"].path_state


def test_voleio_aoe_calculates_all_primary_results_from_pre_event_aura_state():
    source = _fighter("source", fighter_id="a-source", hp="1")
    target = _fighter("target", fighter_id="z-target", hp="1000", defense="20")
    aura = CombatStatAura(
        "cover", "defense", ("a-source",), ("z-target",), D(1)
    )
    state = _battle(count=0, enemies=(source, target), stat_auras=(aura,))
    result = act(state, VOLEIO)
    target_event = next(event for event in _art_events(result) if event.target == "z-target")
    assert result.fighters["a-source"].hp == D(0)
    assert target_event.calculated_damage == direct_damage(
        D(200), D("0.75"), D(40), 34, critical=False
    )


def test_voleio_finishes_aoe_primary_results_before_encounter_phase_trigger():
    boss = _fighter("boss", fighter_id="a-boss", hp="20")
    add = _fighter("add", fighter_id="z-add", hp="1000")
    phase = CombatPhaseTrigger(
        "boss.crossed-half",
        "a-boss",
        D("0.50"),
        consume_active_fighter_keys=("z-add",),
        phase_id="II",
    )
    state = _battle(count=0, enemies=(boss, add), phase_triggers=(phase,))
    result = act(state, VOLEIO)
    events = {event.target: event for event in _art_events(result)}
    assert events["a-boss"].effective_damage > 0
    assert events["z-add"].effective_damage > 0
    assert result.fighters["z-add"].hp == D(0)
    assert result.phase_id == "II"
    assert any(event.action == "phase:boss.crossed-half" for event in result.mechanic_events)


def test_voleio_aggregates_hemario_vampirism_once_for_the_action():
    state = _battle(count=3, race="hemario")
    state.fighters["player"].hp = D(300)
    result = act(state, VOLEIO)
    events = _art_events(result)
    total_damage = sum((D(event.effective_damage) for event in events), D(0))
    assert len(events) == 3 and total_damage > 0
    assert result.fighters["player"].hp == D(300) + min(
        (total_damage * D("0.12")), D(30)
    ).to_integral_value(rounding="ROUND_FLOOR")
    assert sum(event.healed > 0 for event in events) == 1


def test_voleio_codec_reconnect_preserves_results_and_rejects_duplicate_action():
    state = _battle(count=2, path="rastreador")
    state.configuration_snapshot = {
        "active_arts": ({"slot": 2, "art_id": VOLEIO},),
    }
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.player_actions[VOLEIO].target_mode == "all_opponents"
    result = act(restored, "a2", target_id="enemy-0")
    restored_after = decode(encode(result), result.id, result.ruleset, result.version)
    events = _art_events(restored_after)
    assert len(events) == 2
    assert restored_after.fighters["enemy-0"].path_state["aim_from"]["player"]["stacks"] == 1
    duplicate = act(restored_after, "a2", target_id="enemy-0")
    assert duplicate is restored_after
    assert len(_art_events(duplicate)) == 2
    assert restored_after.fighters["player"].action_use_counts[VOLEIO] == 1


def test_voleio_round_prioritizes_aoe_only_when_at_least_two_targets_exist():
    from asterion.application.round import RoundService
    from asterion.domain.arts import VIGIA_ART_IDS

    service = RoundService(None, "ocaso")
    round_state = type("Round", (), {"prepared_heal": False, "prepared_purify": False})()
    character = type("Character", (), {"id": uuid4()})()
    arts = (VIGIA_ART_IDS["disparo_preciso"], VOLEIO)

    multiple = _battle(count=2, arts=arts)
    multiple.fighters["player"].last_action = "defend"
    assert asyncio.run(
        service._choose_round_action(object(), character, round_state, multiple)
    ) == ("action", VOLEIO)

    single = _battle(count=1, arts=arts)
    single.fighters["player"].last_action = "defend"
    assert asyncio.run(
        service._choose_round_action(object(), character, round_state, single)
    ) == ("action", VIGIA_ART_IDS["disparo_preciso"])


def _actor_id() -> int:
    return 800_000_000 + uuid4().int % 100_000_000


async def _seed_character(
    database,
    *,
    level: int,
    path: str | None,
    weapon_type_id: str | None,
    unknown_weapon: bool = False,
):
    _, sessions = database
    actor = _actor_id()
    character_id = uuid4()
    stats = resolve_combat_stats("vigia", level, "remanescente")
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor))
    payload = None
    if weapon_type_id is not None:
        payload = materialize_equipment(
            f"voleio:{actor}", "Comum", 1, weapon_type_id=weapon_type_id
        )
    elif unknown_weapon:
        payload = materialize_equipment(
            f"voleio:{actor}",
            "Comum",
            1,
            forced_name="Arco sem metadata",
            forced_slot="Principal",
        )
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Voleio{suffix}",
                race="remanescente",
                character_class="vigia",
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
        if payload is not None:
            equipment_id, payload = equipment_instance_payload(payload)
            session.add(
                EquipmentItem(
                    id=equipment_id,
                    character_id=character_id,
                    source_key=f"voleio:{actor}:weapon",
                    item_name=payload["item_name"],
                    rarity=payload["rarity"],
                    slot=payload["slot"],
                    item_level=payload["item_level"],
                    bound=False,
                    payload=payload,
                )
            )
            await session.flush()
            session.add(
                CharacterEquipmentSlot(
                    character_id=character_id,
                    slot="Principal",
                    equipment_item_id=equipment_id,
                )
            )
    return actor, character_id, sessions


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ("atirador", "rastreador", None))
async def test_voleio_unlocks_at_34_and_persists_for_both_paths_and_no_path(database, path):
    actor33, _, sessions = await _seed_character(
        database,
        level=33,
        path=path,
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )
    service = ActiveArtService(sessions, "ocaso")
    locked = await service.view(actor33)
    assert locked is not None and VOLEIO not in locked.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as blocked:
        await service.equip_art(actor33, 1, VOLEIO)
    assert blocked.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    actor34, character_id, _ = await _seed_character(
        database,
        level=34,
        path=path,
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )
    available = await service.view(actor34)
    assert available is not None and VOLEIO in available.available_art_ids
    assert VOLEIO not in available.weapon_incompatible_art_ids
    assert (await service.equip_art(actor34, 3, VOLEIO)).changed
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        snapshot = await load_active_art_configuration(session, character)
        rows = list(
            (
                await session.scalars(
                    select(CharacterActiveArtSlot).where(
                        CharacterActiveArtSlot.character_id == character_id
                    )
                )
            ).all()
        )
    assert snapshot.art_ids == (VOLEIO,)
    assert [(row.slot, row.art_id) for row in rows] == [(3, VOLEIO)]
    assert VOLEIO in class_player_actions("vigia", snapshot.art_ids, path)

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 33
    assert VOLEIO in (await service.view(actor34)).ineligible_art_ids


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("weapon_type_id", "compatible"),
    [
        ("weapon.type.tdo.arma_pesada_caminhante", True),
        ("weapon.type.vde.arma_pesada_lacos", True),
        ("weapon.type.tdo.arma_caminhante", False),
    ],
)
async def test_voleio_weapon_metadata_accepts_only_explicit_bow_or_crossbow(
    database, weapon_type_id, compatible
):
    actor, _, sessions = await _seed_character(
        database,
        level=34,
        path="rastreador",
        weapon_type_id=weapon_type_id,
    )
    service = ActiveArtService(sessions, "ocaso")
    if compatible:
        result = await service.equip_art(actor, 1, VOLEIO)
        assert result is not None and result.changed
    else:
        view = await service.view(actor)
        assert VOLEIO in view.weapon_incompatible_art_ids
        with pytest.raises(ActiveArtMutationRejected) as rejected:
            await service.equip_art(actor, 1, VOLEIO)
        assert rejected.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT


@pytest.mark.asyncio
async def test_voleio_rejects_unarmed_unknown_weapon_and_other_class(database):
    service = ActiveArtService(database[1], "ocaso")
    for unknown in (False, True):
        actor, _, sessions = await _seed_character(
            database,
            level=34,
            path="atirador",
            weapon_type_id=None,
            unknown_weapon=unknown,
        )
        view = await service.view(actor)
        assert VOLEIO in view.weapon_incompatible_art_ids
        with pytest.raises(ActiveArtMutationRejected) as rejected:
            await service.equip_art(actor, 1, VOLEIO)
        assert rejected.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT

    actor = _actor_id()
    stats = resolve_combat_stats("errante", 34, "remanescente")
    async with database[1].begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=uuid4(),
                telegram_id=actor,
                server_id="ocaso",
                name="Outro",
                race="remanescente",
                character_class="errante",
                selected_path="carrasco",
                stage="menu:ready",
                ruleset_version="gdd-1.6.0-baseline-1.0",
                level=34,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
    assert VOLEIO not in (await service.view(actor)).available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as rejected:
        await service.equip_art(actor, 1, VOLEIO)
    assert rejected.value.code == ActiveArtMutationCode.WRONG_CLASS


@pytest.mark.asyncio
async def test_voleio_respects_active_combat_configuration_lock(database):
    actor, character_id, sessions = await _seed_character(
        database,
        level=34,
        path="atirador",
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )
    async with sessions.begin() as session:
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=character_id,
                content_id="test.voleio.lock",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    with pytest.raises(CombatConfigurationLocked):
        await ActiveArtService(sessions, "ocaso").equip_art(actor, 1, VOLEIO)


def test_voleio_is_offered_in_doctrines_for_level_34_vigia():
    collection = DoctrineCollectionView(
        character_name="Vigia",
        character_class="vigia",
        selected_path="atirador",
        configuration_version=0,
        foreground=False,
        current_configuration={"path": "atirador", "equipment": {}, "arts": {}, "talents": []},
        doctrines=(),
        crowns=1000,
        level=34,
    )
    doctrine = DoctrineView(
        doctrine_id=uuid4(),
        name="Vigia",
        revision=1,
        configuration={"path": "atirador", "equipment": {}, "arts": {}, "talents": []},
        is_current=False,
        incomplete_reason=None,
        can_apply=True,
    )
    assert VOLEIO in doctrine_art_ids(collection, doctrine)

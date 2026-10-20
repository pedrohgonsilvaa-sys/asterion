import asyncio
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.active_arts import (
    ActiveArtConfigurationError,
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.application.equipment import equipment_instance_payload
from asterion.application.prologue import CombatView
from asterion.bot.character_progression_ui import render_art_detail
from asterion.bot.combat_ui import CombatCallback, event_line, render_combat
from asterion.bot.doctrines_ui import doctrine_art_ids, render_art_choices
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ACTIVE_ART_IDS_BY_CLASS,
    DEVASTADOR_ART_IDS,
    SENTINEL_ART_IDS,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Combat,
    Fighter,
    act,
    action_target_ids,
    allowed_actions,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, resolve_combat_stats
from asterion.domain.prologue import PROFILE
from asterion.domain.road import materialize_equipment
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterActiveArtSlot,
    CharacterEquipmentSlot,
    EquipmentItem,
)

D = Decimal
FIRMEZA = SENTINEL_ART_IDS["firmeza"]


async def _seed_character(
    database,
    actor: int,
    *,
    level: int,
    path: str | None = None,
    character_class: str = "sentinela",
    weapon_type_id: str | None = None,
):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats(
        character_class, level, "remanescente", selected_path=path
    )
    name_suffix = "".join(
        chr(ord("a") + int(digit)) for digit in str(actor)[-5:]
    )
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Firmeza{name_suffix}"[:16],
                race="remanescente",
                character_class=character_class,
                selected_path=path,
                stage="menu:ready",
                ruleset_version="gdd-1.4.9-baseline-1.0",
                level=level,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
        if weapon_type_id:
            payload = materialize_equipment(
                f"firmeza:{actor}", "Comum", 18, weapon_type_id=weapon_type_id
            )
            equipment_id, payload = equipment_instance_payload(payload)
            session.add(
                EquipmentItem(
                    id=equipment_id,
                    character_id=character_id,
                    source_key=f"firmeza:{actor}:weapon",
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
    return character_id, sessions


@pytest.mark.asyncio
async def test_firmeza_unlocks_at_level_18_for_both_sentinel_paths_and_no_path(database):
    service = ActiveArtService(database[1], "ocaso")
    cases = (
        (982101, 17, None, "sentinela", False),
        (982102, 18, None, "sentinela", True),
        (982103, 20, "bastiao", "sentinela", True),
        (982104, 20, "devastador", "sentinela", True),
        (982105, 20, "atirador", "vigia", False),
    )
    for actor, level, path, character_class, eligible in cases:
        await _seed_character(
            database,
            actor,
            level=level,
            path=path,
            character_class=character_class,
        )
        view = await service.view(actor)
        assert view is not None
        assert (FIRMEZA in view.available_art_ids) is eligible

    assert ACTIVE_ART_DEFINITIONS[FIRMEZA].min_level == 18
    assert ACTIVE_ART_DEFINITIONS[FIRMEZA].character_class == "sentinela"
    assert ACTIVE_ART_DEFINITIONS[FIRMEZA].path_id is None
    assert ACTIVE_ART_DEFINITIONS[FIRMEZA].weapon_requirement == frozenset()
    assert FIRMEZA in ACTIVE_ART_IDS_BY_CLASS["sentinela"]
    assert FIRMEZA not in ACTIVE_ART_IDS_BY_CLASS["vigia"]

    with pytest.raises(ActiveArtMutationRejected) as level_gate:
        await service.equip_art(982101, 1, FIRMEZA)
    assert level_gate.value.code == ActiveArtMutationCode.LEVEL_REQUIRED
    with pytest.raises(ActiveArtMutationRejected) as class_gate:
        await service.equip_art(982105, 1, FIRMEZA)
    assert class_gate.value.code == ActiveArtMutationCode.WRONG_CLASS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "weapon_type_id",
    (
        None,
        "weapon.type.tdo.arma_pesada_caminhante",
        "weapon.type.nareth.arma_pesada_horizonte",
    ),
)
async def test_firmeza_is_equipable_without_melee_metadata_and_survives_reconnect(
    database, weapon_type_id
):
    actor = 982110
    character_id, sessions = await _seed_character(
        database,
        actor,
        level=18,
        path=None,
        weapon_type_id=weapon_type_id,
    )
    service = ActiveArtService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None and FIRMEZA in view.available_art_ids
    assert FIRMEZA not in view.weapon_incompatible_art_ids

    result = await service.equip_art(
        actor, 2, FIRMEZA, expected_configuration_version=0
    )
    assert result is not None and result.changed
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        snapshot = await load_active_art_configuration(session, character)
        row = await session.scalar(
            select(CharacterActiveArtSlot).where(
                CharacterActiveArtSlot.character_id == character_id,
                CharacterActiveArtSlot.slot == 2,
            )
        )
    assert row is not None and row.art_id == FIRMEZA
    assert snapshot.art_ids == (FIRMEZA,)
    assert FIRMEZA in class_player_actions(
        "sentinela", snapshot.art_ids, "bastiao"
    )

    reconnected = await service.view(actor)
    assert reconnected is not None
    assert [(entry.slot, entry.art_id) for entry in reconnected.slots] == [(2, FIRMEZA)]
    detail = render_art_detail(reconnected, FIRMEZA)
    assert "+12% DEF" in detail.text
    assert "2T" in detail.text and "Recarga · 3" in detail.text
    assert "Requisito de arma" not in detail.text
    assert any(
        button.text == "Equipar Arte"
        for row in detail.keyboard.inline_keyboard
        for button in row
    ) is False

    with pytest.raises(ActiveArtMutationRejected) as stale:
        await service.equip_art(actor, 1, FIRMEZA, expected_configuration_version=0)
    assert stale.value.code == ActiveArtMutationCode.STALE_CONFIGURATION


@pytest.mark.asyncio
async def test_firmeza_remains_valid_with_a_bow_while_ariete_requires_melee(database):
    actor = 982113
    _, sessions = await _seed_character(
        database,
        actor,
        level=20,
        path="devastador",
        weapon_type_id="weapon.type.nareth.arma_pesada_horizonte",
    )
    service = ActiveArtService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    ariete = DEVASTADOR_ART_IDS["ariete"]
    assert FIRMEZA in view.available_art_ids
    assert FIRMEZA not in view.weapon_incompatible_art_ids
    assert ariete in view.weapon_incompatible_art_ids

    await service.equip_art(actor, 1, FIRMEZA)
    with pytest.raises(ActiveArtMutationRejected) as weapon_gate:
        await service.equip_art(actor, 2, ariete)
    assert weapon_gate.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT


@pytest.mark.asyncio
async def test_firmeza_revalidates_after_level_loss_and_uses_only_three_slots(database):
    actor = 982111
    character_id, sessions = await _seed_character(
        database,
        actor,
        level=18,
        path="bastiao",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    service = ActiveArtService(sessions, "ocaso")
    arts = (
        FIRMEZA,
        SENTINEL_ART_IDS["muralha_breve"],
        SENTINEL_ART_IDS["golpe_de_guarda"],
    )
    for slot, art in enumerate(arts, start=1):
        await service.equip_art(actor, slot, art)
    with pytest.raises(ActiveArtMutationRejected) as fourth_slot:
        await service.equip_art(actor, 4, FIRMEZA)
    assert fourth_slot.value.code == ActiveArtMutationCode.INVALID_SLOT

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 17
    view = await service.view(actor)
    assert view is not None and FIRMEZA in view.ineligible_art_ids
    with pytest.raises(ActiveArtConfigurationError, match="level requirement"):
        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            await load_active_art_configuration(session, character)


@pytest.mark.asyncio
async def test_firmeza_configuration_callbacks_are_serialized(database):
    actor = 982112
    _, sessions = await _seed_character(database, actor, level=18)
    service = ActiveArtService(sessions, "ocaso")
    outcomes = await asyncio.gather(
        service.equip_art(actor, 1, FIRMEZA, expected_configuration_version=0),
        service.equip_art(actor, 2, FIRMEZA, expected_configuration_version=0),
        return_exceptions=True,
    )
    succeeded = [item for item in outcomes if not isinstance(item, Exception)]
    rejected = [item for item in outcomes if isinstance(item, Exception)]
    assert len(succeeded) == 1 and succeeded[0].changed
    assert len(rejected) == 1
    assert isinstance(rejected[0], ActiveArtMutationRejected)
    assert rejected[0].code == ActiveArtMutationCode.STALE_CONFIGURATION

    view = await service.view(actor)
    assert view is not None and len(view.slots) == 1
    assert view.slots[0].art_id == FIRMEZA


def test_firmeza_is_available_in_doctrine_at_level_18_without_path_gate():
    collection = DoctrineCollectionView(
        character_name="Sentinela",
        character_class="sentinela",
        selected_path=None,
        configuration_version=1,
        foreground=False,
        current_configuration={"path": None, "equipment": {}, "arts": {}, "talents": []},
        doctrines=(),
        crowns=0,
        level=18,
    )
    doctrine = DoctrineView(
        doctrine_id=uuid4(),
        name="Postura",
        revision=1,
        configuration={"path": None, "equipment": {}, "arts": {}, "talents": []},
        is_current=False,
        incomplete_reason=None,
        can_apply=True,
    )
    assert FIRMEZA in doctrine_art_ids(collection, doctrine)
    screen = render_art_choices(collection, doctrine, 1)
    assert any(
        "Firmeza" in button.text
        for row in screen.keyboard.inline_keyboard
        for button in row
    )
    assert FIRMEZA not in doctrine_art_ids(replace(collection, level=17), doctrine)


def _firmeza_combat(combat_id):
    stats = resolve_combat_stats(
        "sentinela", 20, "remanescente", selected_path="devastador"
    )
    player = Fighter(
        "player",
        "Sentinela",
        20,
        stats,
        stats.hp,
        race="remanescente",
        character_class="sentinela",
        opportunity=0,
        retaliation_charges=1,
        retaliation_remaining=3,
        retaliation_applied_opportunity=1,
        retaliation_activation_id="defender:test",
        retaliation_source_type="defender",
        selected_path="devastador",
        path_state={
            "devastador_charge": {
                "expires_opportunity": 10,
                "source_action": "incoming-test-hit",
            }
        },
    )
    enemy_stats = CombatStats(D(10000), D(100), D(100), D(1), D(0), D(0), D(0), D(0))
    enemy = Fighter(
        "enemy",
        "Oponente",
        20,
        enemy_stats,
        enemy_stats.hp,
        character_class="errante",
        side="enemy",
    )
    player_actions = class_player_actions("sentinela", (FIRMEZA,), "devastador")
    player_actions["attack"] = Action("attack", "Ataque Básico", D(1))
    state = Combat(
        combat_id,
        CURRENT_COMBAT_RULESET,
        {"player": player, "enemy": enemy},
        player_actions,
        {"hit": Action("hit", "Golpe", D(1))},
        ("hit",),
        configuration_snapshot={
            "selected_path": "devastador",
            "active_arts": [{"slot": 2, "art_id": FIRMEZA}],
        },
    )
    return start_combat(state)


def test_firmeza_is_a_self_buff_with_exact_stat_duration_cooldown_and_snapshot():
    assert "Firmeza" == class_player_actions("sentinela", (FIRMEZA,))[FIRMEZA].name
    assert FIRMEZA not in class_player_actions("sentinela", (), "devastador")
    assert allowed_actions(_firmeza_combat(uuid4())).count(FIRMEZA) == 1
    state = _firmeza_combat(uuid4())
    assert action_target_ids(state, FIRMEZA) == (state.fighters["player"].id,)
    assert FIRMEZA in allowed_actions(state)

    player = state.fighters["player"]
    base_defense = player.stats.defense
    original_retaliation = player.retaliation_charges
    original_devastador_charge = player.path_state["devastador_charge"].copy()
    state = act(state, "a2")
    player = state.fighters["player"]
    effect = next(effect for effect in player.effects if effect.id == "sentinel.firmeza")
    assert effect.kind == "buff" and effect.stat == "defense"
    assert effect.magnitude == D("0.12") and effect.remaining == 2
    assert effect.stackable is False
    assert player.stat("defense") == base_defense * D("1.12")
    assert player.stats.defense == base_defense
    assert player.cooldowns[FIRMEZA] == 4
    assert player.retaliation_charges == original_retaliation
    assert player.path_state["devastador_charge"] == original_devastador_charge
    firm_event = next(event for event in state.events if event.action == FIRMEZA)
    assert firm_event.target == player.id
    assert firm_event.actor_effect_id == "sentinel.firmeza"
    assert firm_event.damage == 0 and firm_event.healed == 0 and firm_event.barrier_value == 0
    enemy_event = next(event for event in state.events if event.action == "hit")

    baseline = _firmeza_combat(state.id)
    baseline = act(baseline, "attack")
    baseline_enemy_event = next(event for event in baseline.events if event.action == "hit")
    assert enemy_event.calculated_damage < baseline_enemy_event.calculated_damage

    persisted = decode(encode(state), state.id, state.ruleset, state.version)
    persisted_player = persisted.fighters["player"]
    assert persisted_player.cooldowns[FIRMEZA] == player.cooldowns[FIRMEZA]
    assert next(
        effect for effect in persisted_player.effects if effect.id == "sentinel.firmeza"
    ).remaining == 2
    blocked = act(persisted, "a2")
    assert blocked.version == persisted.version

    state = act(state, "attack")
    assert next(
        effect for effect in state.fighters["player"].effects if effect.id == "sentinel.firmeza"
    ).remaining == 1
    state = act(state, "attack")
    assert not any(effect.id == "sentinel.firmeza" for effect in state.fighters["player"].effects)
    assert state.fighters["player"].stat("defense") == base_defense
    assert FIRMEZA in allowed_actions(state)


def test_firmeza_is_described_and_targeted_to_self_in_telegram_combat_ui():
    state = PROFILE.create(uuid4(), "Sentinela", "sentinela", "remanescente", D(700))
    state.tutorial = None
    state.player_actions = class_player_actions("sentinela", (FIRMEZA,))
    state.configuration_snapshot = {
        "active_arts": [{"slot": 2, "art_id": FIRMEZA}]
    }
    player = state.fighters["player"]
    player.level = 20
    available_view = CombatView(
        uuid4(), uuid4(), uuid4(), state, "combat", 0, context="road"
    )
    available_screen = render_combat(available_view)
    buttons = [
        button
        for row in available_screen.keyboard.inline_keyboard
        for button in row
    ]
    firm_button = next(button for button in buttons if button.text == "Firmeza")
    callback = CombatCallback.unpack(firm_button.callback_data)
    assert callback.action == "a2"

    state = act(state, "a2")
    view = CombatView(uuid4(), uuid4(), uuid4(), state, "combat", 0, context="road")
    screen = render_combat(view)
    assert "Firmeza · DEF +<code>12%</code> · <code>2T</code>" in screen.text
    firmeza_event = next(event for event in state.events if event.action == FIRMEZA)
    assert "eleva a própria DEF" in event_line(state, firmeza_event)

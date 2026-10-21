import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

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
from asterion.application.prologue import CombatView
from asterion.application.round import RoundService
from asterion.bot.character_progression_ui import render_art_detail
from asterion.bot.combat_ui import CombatCallback, event_line, render_combat
from asterion.bot.doctrines_ui import doctrine_art_ids, render_art_choices
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ACTIVE_ART_IDS_BY_CLASS,
    SENTINEL_ART_IDS,
    active_art_definition,
    weapon_requirement_satisfied,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, Combat, Fighter, act, allowed_actions, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    direct_damage,
)
from asterion.domain.equipment import EquipmentSlot, assignment_for_item_slot
from asterion.domain.road import materialize_equipment
from asterion.domain.weapon_metadata import WeaponMetadataStatus, resolve_weapon_metadata
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
ZERO = D(0)
RECHACO_ID = SENTINEL_ART_IDS["golpe_de_rechaco"]
PONTA_REVIDADA = "talent.sentinela.ponta_revidada"


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
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor)[-5:])
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Rechaco{suffix}"[:16],
                race="remanescente",
                character_class=character_class,
                selected_path=path,
                stage="menu:ready",
                ruleset_version="gdd-1.4.9-baseline-1.0",
                level=level,
                xp=0,
                hp=1000,
                max_hp=1000,
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
        if weapon_type_id is not None:
            payload = materialize_equipment(
                f"golpe-rechaco:{actor}",
                "Comum",
                level,
                weapon_type_id=weapon_type_id,
            )
            item_id, payload = equipment_instance_payload(payload)
            session.add(
                EquipmentItem(
                    id=item_id,
                    character_id=character_id,
                    source_key=f"golpe-rechaco:{actor}:weapon",
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
                    equipment_item_id=item_id,
                )
            )
    return character_id, sessions


def _combat(
    *,
    path: str | None = None,
    retaliation: bool = False,
    per: Decimal = ZERO,
    talents: tuple[str, ...] = (),
    enemy_evasion: Decimal = ZERO,
    enemy_barrier: Decimal = ZERO,
    devastador_charge: bool = False,
    equip: bool = True,
) -> Combat:
    player_stats = CombatStats(
        D(1000), D(100), D(0), D(100), per=per, crit=D(0), evasion=D(0), block=D(0)
    )
    player = Fighter(
        id="player",
        name="Sentinela",
        level=34,
        stats=player_stats,
        hp=D(1000),
        race="remanescente",
        character_class="sentinela",
        selected_path=path,
        talent_ids=talents,
        retaliation_charges=int(retaliation),
        retaliation_remaining=int(retaliation),
        retaliation_activation_id="test:retaliation" if retaliation else "",
        retaliation_source_type="defender" if retaliation else "",
        retaliation_source_event_id="test:defender-event" if retaliation else "",
        retaliation_source_actor_id="enemy" if retaliation else "",
    )
    if devastador_charge:
        player.path_state["devastador_charge"] = {
            "expires_opportunity": player.opportunity + 2,
            "source_action": "enemy.test_hit",
        }
    enemy_stats = CombatStats(
        D(10000), D(0), D(100), D(1), per=D(0), crit=D(0), evasion=enemy_evasion
    )
    enemy = Fighter(
        id="enemy",
        name="Alvo",
        level=34,
        stats=enemy_stats,
        hp=D(10000),
        side="enemy",
        takes_turn=False,
        barrier=enemy_barrier,
        barrier_remaining=2 if enemy_barrier else 0,
        barrier_source="test:protection" if enemy_barrier else "",
    )
    allowed = (RECHACO_ID,) if equip else ()
    actions = class_player_actions("sentinela", allowed, selected_path=path)
    state = Combat(
        id=UUID("b3ca4654-cfa6-a0dd-c3e9-a68f22b6fab1"),
        ruleset=CURRENT_COMBAT_RULESET,
        fighters={"player": player, "enemy": enemy},
        player_actions=actions,
        enemy_actions={"enemy.hit": Action("enemy.hit", "Golpe", D("0.50"))},
        ai_cycle=("enemy.hit",),
        configuration_snapshot={
            "selected_path": path,
            "active_arts": ([{"slot": 2, "art_id": RECHACO_ID}] if equip else []),
        },
    )
    return start_combat(state)


def _art_event(state: Combat):
    return next(event for event in state.events if event.action == RECHACO_ID)


def test_golpe_de_rechaco_has_exact_catalog_and_action_contract():
    definition = active_art_definition(RECHACO_ID)
    assert definition is not None
    assert definition.art_id == "class_art.sentinela.golpe_de_rechaco"
    assert definition.character_class == "sentinela"
    assert definition.min_level == 34
    assert definition.path_id is None
    assert definition.weapon_requirement == frozenset({"weapon.compat.melee"})
    assert RECHACO_ID in ACTIVE_ART_IDS_BY_CLASS["sentinela"]
    assert ACTIVE_ART_DEFINITIONS[RECHACO_ID] == definition

    action = class_player_actions("sentinela", (RECHACO_ID,))[RECHACO_ID]
    assert action.name == "Golpe de Rechaço"
    assert action.coefficient == D("1.45")
    assert action.cooldown == 4
    assert action.hit_count == 1
    assert action.target_mode == "opponent"
    assert action.attack_debuff == 0
    assert action.self_barrier_coefficient == 0
    assert action.target_barrier_coefficient == 0
    assert action.heal_coefficient == 0
    assert action.native_dot_kind is None
    assert action.conditional_modifiers[0].condition.resource == "retaliation"
    assert action.conditional_modifiers[0].condition.minimum == 1
    assert action.conditional_modifiers[0].component == "precision_bonus"
    assert action.conditional_modifiers[0].magnitude == D(10)
    assert action.conditional_modifiers[0].evaluation_scope == "per_action"


@pytest.mark.asyncio
async def test_golpe_de_rechaco_unlocks_at_34_for_both_paths_and_no_path(database):
    service = ActiveArtService(database[1], "ocaso")
    cases = (
        (983401, 33, None, "sentinela", False),
        (983402, 34, None, "sentinela", True),
        (983403, 34, "bastiao", "sentinela", True),
        (983404, 34, "devastador", "sentinela", True),
        (983405, 34, "atirador", "vigia", False),
    )
    for actor, level, path, character_class, eligible in cases:
        await _seed_character(
            database,
            actor,
            level=level,
            path=path,
            character_class=character_class,
            weapon_type_id="weapon.type.tdo.arma_caminhante"
            if character_class == "sentinela"
            else None,
        )
        view = await service.view(actor)
        assert view is not None
        assert (RECHACO_ID in view.available_art_ids) is eligible
    with pytest.raises(ActiveArtMutationRejected) as low_level:
        await service.equip_art(983401, 1, RECHACO_ID)
    assert low_level.value.code == ActiveArtMutationCode.LEVEL_REQUIRED
    with pytest.raises(ActiveArtMutationRejected) as wrong_class:
        await service.equip_art(983405, 1, RECHACO_ID)
    assert wrong_class.value.code == ActiveArtMutationCode.WRONG_CLASS


@pytest.mark.asyncio
async def test_golpe_de_rechaco_melee_gate_slots_persistence_and_reconnect(database):
    actor = 983410
    character_id, sessions = await _seed_character(
        database,
        actor,
        level=34,
        path="bastiao",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    service = ActiveArtService(sessions, "ocaso")
    result = await service.equip_art(actor, 2, RECHACO_ID, expected_configuration_version=0)
    assert result is not None and result.changed
    assert result.combat_configuration_version == 1

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        configuration = await load_active_art_configuration(session, character)
        row = await session.scalar(
            select(CharacterActiveArtSlot).where(
                CharacterActiveArtSlot.character_id == character_id,
                CharacterActiveArtSlot.slot == 2,
            )
        )
    assert row is not None and row.art_id == RECHACO_ID
    assert configuration.art_ids == (RECHACO_ID,)
    view = await service.view(actor)
    assert view is not None and [(slot.slot, slot.art_id) for slot in view.slots] == [
        (2, RECHACO_ID)
    ]
    assert RECHACO_ID not in view.weapon_incompatible_art_ids
    assert RECHACO_ID in class_player_actions("sentinela", configuration.art_ids, "bastiao")
    detail = render_art_detail(view, RECHACO_ID)
    assert "Desbloqueio · Nv.34" in detail.text
    assert "145% ATQ" in detail.text
    assert "+10 p.p. PER" in detail.text
    assert "Retaliação ativa no início da ação" in detail.text
    assert "Arma corpo a corpo compatível" in detail.text

    with pytest.raises(ActiveArtMutationRejected) as stale:
        await service.equip_art(actor, 1, RECHACO_ID, expected_configuration_version=0)
    assert stale.value.code == ActiveArtMutationCode.STALE_CONFIGURATION


@pytest.mark.asyncio
async def test_golpe_de_rechaco_rejects_non_melee_and_unmapped_equipment(database):
    service = ActiveArtService(database[1], "ocaso")
    cases = (
        (983420, None),
        (983421, "weapon.type.tdo.arma_pesada_caminhante"),
        (983422, "weapon.type.vde.arma_pesada_lacos"),
    )
    for actor, weapon_type_id in cases:
        await _seed_character(
            database,
            actor,
            level=34,
            path="devastador",
            weapon_type_id=weapon_type_id,
        )
        view = await service.view(actor)
        assert view is not None and RECHACO_ID in view.available_art_ids
        assert RECHACO_ID in view.weapon_incompatible_art_ids
        with pytest.raises(ActiveArtMutationRejected) as incompatible:
            await service.equip_art(actor, 1, RECHACO_ID)
        assert incompatible.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT

    unknown = resolve_weapon_metadata({"weapon_type_id": "weapon.type.unknown"})
    assert unknown.status is WeaponMetadataStatus.UNMAPPED
    assert unknown.definition is None
    assert not weapon_requirement_satisfied(
        active_art_definition(RECHACO_ID), frozenset()
    )
    # The active-Art gate consumes explicit tags only; handedness is enforced by
    # equipment slots. This contract also accepts an explicitly melee-tagged 2H item.
    assert weapon_requirement_satisfied(
        active_art_definition(RECHACO_ID), frozenset({"weapon.compat.melee"})
    )
    two_handed_assignment = assignment_for_item_slot("2H")
    assert two_handed_assignment is not None
    assert two_handed_assignment.two_handed
    assert two_handed_assignment.slot is EquipmentSlot.PRINCIPAL


@pytest.mark.asyncio
async def test_golpe_de_rechaco_revalidates_after_weapon_change_and_obeys_lock(database):
    actor = 983430
    character_id, sessions = await _seed_character(
        database,
        actor,
        level=34,
        path="devastador",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    service = ActiveArtService(sessions, "ocaso")
    await service.equip_art(actor, 1, RECHACO_ID)
    async with sessions.begin() as session:
        bow_payload = materialize_equipment(
            "golpe-rechaco:replacement-bow",
            "Comum",
            34,
            weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
        )
        item_id, bow_payload = equipment_instance_payload(bow_payload)
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character_id,
                source_key="golpe-rechaco:replacement-bow",
                item_name=bow_payload["item_name"],
                rarity=bow_payload["rarity"],
                slot=bow_payload["slot"],
                item_level=bow_payload["item_level"],
                bound=False,
                payload=bow_payload,
            )
        )
        await session.flush()
        slot = await session.scalar(
            select(CharacterEquipmentSlot).where(
                CharacterEquipmentSlot.character_id == character_id,
                CharacterEquipmentSlot.slot == "Principal",
            )
        )
        slot.equipment_item_id = item_id
    view = await service.view(actor)
    assert view is not None and RECHACO_ID in view.weapon_incompatible_art_ids
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        with pytest.raises(ValueError, match="weapon requirement"):
            await load_active_art_configuration(session, character)

    async with sessions.begin() as session:
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=character_id,
                content_id="test.golpe_de_rechaco",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    with pytest.raises(CombatConfigurationLocked):
        await service.equip_art(actor, 2, RECHACO_ID)


@pytest.mark.asyncio
async def test_golpe_de_rechaco_configuration_is_serialized_and_limited_to_three_slots(database):
    actor = 983440
    _, sessions = await _seed_character(
        database,
        actor,
        level=34,
        path="bastiao",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    service = ActiveArtService(sessions, "ocaso")
    results = await asyncio.gather(
        service.equip_art(actor, 1, RECHACO_ID, expected_configuration_version=0),
        service.equip_art(actor, 2, RECHACO_ID, expected_configuration_version=0),
        return_exceptions=True,
    )
    succeeded = [result for result in results if not isinstance(result, Exception)]
    rejected = [result for result in results if isinstance(result, Exception)]
    assert len(succeeded) == 1 and succeeded[0].changed
    assert len(rejected) == 1 and isinstance(rejected[0], ActiveArtMutationRejected)
    assert rejected[0].code == ActiveArtMutationCode.STALE_CONFIGURATION

    view = await service.view(actor)
    assert view is not None
    equipped_slots = {entry.slot for entry in view.slots}
    remaining_arts = iter(
        (SENTINEL_ART_IDS["golpe_de_guarda"], SENTINEL_ART_IDS["muralha_breve"])
    )
    for slot in (1, 2, 3):
        if slot not in equipped_slots:
            await service.equip_art(actor, slot, next(remaining_arts))
    view = await service.view(actor)
    assert view is not None and len(view.slots) == 3
    with pytest.raises(ActiveArtMutationRejected) as invalid_slot:
        await service.equip_art(actor, 4, SENTINEL_ART_IDS["golpe_de_guarda"])
    assert invalid_slot.value.code == ActiveArtMutationCode.INVALID_SLOT


def test_golpe_de_rechaco_is_available_to_doctrines_for_both_paths():
    for path in (None, "bastiao", "devastador"):
        collection = DoctrineCollectionView(
            character_name="Sentinela",
            character_class="sentinela",
            selected_path=path,
            configuration_version=1,
            foreground=False,
            current_configuration={"path": path, "equipment": {}, "arts": {}, "talents": []},
            doctrines=(),
            crowns=0,
            level=34,
        )
        doctrine = DoctrineView(
            doctrine_id=uuid4(),
            name="Rechaço",
            revision=1,
            configuration={"path": path, "equipment": {}, "arts": {"1": RECHACO_ID}, "talents": []},
            is_current=False,
            incomplete_reason=None,
            can_apply=True,
        )
        assert RECHACO_ID in doctrine_art_ids(collection, doctrine)
        screen = render_art_choices(collection, doctrine, 1)
        assert any(
            "Golpe de Rechaço" in button.text
            for row in screen.keyboard.inline_keyboard
            for button in row
        )
        assert RECHACO_ID not in doctrine_art_ids(
            DoctrineCollectionView(
                character_name="Sentinela",
                character_class="sentinela",
                selected_path=path,
                configuration_version=1,
                foreground=False,
                current_configuration={},
                doctrines=(),
                crowns=0,
                level=33,
            ),
            doctrine,
        )


@pytest.mark.parametrize(
    ("path", "retaliation", "per", "talents", "expected_per", "final_bonus"),
    [
        (None, False, D(0), (), D(0), D(0)),
        ("bastiao", True, D(0), (), D(10), D(0)),
        ("devastador", True, D(0), (PONTA_REVIDADA,), D(14), D(0)),
        ("bastiao", True, D(24), (PONTA_REVIDADA,), D(30), D(0)),
        ("devastador", True, D(0), (), D(10), D("0.12")),
    ],
)
def test_golpe_de_rechaco_resolves_145_percent_with_snapshot_per_and_shared_caps(
    path, retaliation, per, talents, expected_per, final_bonus
):
    state = _combat(
        path=path,
        retaliation=retaliation,
        per=per,
        talents=talents,
        devastador_charge=bool(final_bonus),
    )
    assert RECHACO_ID in allowed_actions(state)
    opportunity = state.fighters["player"].opportunity
    resolved = act(state, RECHACO_ID, target_id="enemy")
    event = _art_event(resolved)
    expected = direct_damage(
        D(100), D("1.45"), D(100), 34, penetration=expected_per
    )
    if final_bonus:
        expected = int(D(expected) * (D(1) + final_bonus))

    assert event.calculated_damage == expected
    assert event.path_per_bonus == (D(10) if retaliation else D(0))
    assert event.path_final_damage_bonus == final_bonus
    assert event.retaliation_used is retaliation
    assert resolved.fighters["player"].retaliation_charges == 0
    assert resolved.fighters["player"].cooldowns[RECHACO_ID] == opportunity + 4
    assert RECHACO_ID not in allowed_actions(resolved)
    assert sum(
        entry.retaliation_event == "consumed" for entry in resolved.mechanic_events
    ) == int(retaliation)


def test_golpe_de_rechaco_consumes_retaliation_on_dodge_or_full_barrier_absorption():
    dodged = _combat(retaliation=True, enemy_evasion=D(100))
    after_dodge = act(dodged, RECHACO_ID, target_id="enemy")
    dodge_event = _art_event(after_dodge)
    assert dodge_event.dodged is True
    assert dodge_event.retaliation_used is True
    assert dodge_event.path_per_bonus == D(10)
    assert after_dodge.fighters["player"].retaliation_charges == 0

    barriered = _combat(retaliation=True, enemy_barrier=D(10000))
    after_barrier = act(barriered, RECHACO_ID, target_id="enemy")
    barrier_event = _art_event(after_barrier)
    assert barrier_event.calculated_damage > 0
    assert barrier_event.effective_damage == 0
    assert barrier_event.barrier_absorbed >= barrier_event.calculated_damage
    assert barrier_event.retaliation_used is True
    assert after_barrier.fighters["player"].retaliation_charges == 0


def test_golpe_de_rechaco_uses_shared_retaliation_resolution_in_pvp_mode():
    state = _combat(retaliation=True)
    state.pvp_mode = True

    resolved = act(state, RECHACO_ID, target_id="enemy")

    event = _art_event(resolved)
    assert event.calculated_damage > 0
    assert event.retaliation_used is True
    assert event.path_per_bonus == D(10)
    assert resolved.fighters["player"].retaliation_charges == 0


def test_golpe_de_rechaco_uses_shared_hp_zero_and_victory_resolution():
    state = _combat(retaliation=True)
    state.fighters["enemy"].hp = D(1)

    resolved = act(state, RECHACO_ID, target_id="enemy")

    assert resolved.fighters["enemy"].hp == 0
    assert resolved.result == "victory"
    assert _art_event(resolved).retaliation_used is True
    assert resolved.fighters["player"].retaliation_charges == 0


def test_golpe_de_rechaco_rejected_before_commit_preserves_retaliation_and_cooldown():
    state = _combat(retaliation=True)
    state.fighters["enemy"].hp = D(0)
    rejected = act(state, RECHACO_ID, target_id="enemy")
    assert rejected is state
    assert state.fighters["player"].retaliation_charges == 1
    assert RECHACO_ID not in state.fighters["player"].cooldowns

    state = _combat(retaliation=True)
    state.fighters["ally"] = Fighter(
        id="ally",
        name="Aliado",
        level=34,
        stats=state.fighters["player"].stats,
        hp=D(1000),
        side="player",
        takes_turn=False,
    )
    rejected = act(state, RECHACO_ID, target_id="ally")
    assert rejected is state
    assert state.fighters["player"].retaliation_charges == 1
    assert RECHACO_ID not in state.fighters["player"].cooldowns

    state = _combat(retaliation=True)
    state.fighters["player"].cooldowns[RECHACO_ID] = (
        state.fighters["player"].opportunity + 4
    )
    rejected = act(state, RECHACO_ID, target_id="enemy")
    assert rejected is state
    assert state.fighters["player"].retaliation_charges == 1

    state = _combat(retaliation=True, equip=False)
    rejected = act(state, RECHACO_ID, target_id="enemy")
    assert rejected is state
    assert state.fighters["player"].retaliation_charges == 1


def test_golpe_de_rechaco_target_callback_ui_and_reconnect_preserve_action_context():
    state = _combat(path="devastador", retaliation=True)
    assert class_player_actions("sentinela", (), "devastador").get(RECHACO_ID) is None
    screen = render_combat(
        CombatView(uuid4(), uuid4(), uuid4(), state, "test", 0, context="road")
    )
    assert "Golpe de Rechaço" in screen.text
    assert "+10 p.p. PER" in screen.text
    action_button = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Golpe de Rechaço"
    )
    assert CombatCallback.unpack(action_button.callback_data).action == "a2"

    restored_before = decode(encode(state), state.id, state.ruleset, state.version)
    action_opportunity = restored_before.fighters["player"].opportunity
    assert restored_before.fighters["player"].retaliation_charges == 1
    assert restored_before.player_actions[RECHACO_ID].conditional_modifiers[0].magnitude == D(10)
    resolved = act(restored_before, "a2", target_id="enemy")
    event = _art_event(resolved)
    assert event.path_per_bonus == D(10)
    restored_after = decode(encode(resolved), resolved.id, resolved.ruleset, resolved.version)
    assert restored_after.fighters["player"].retaliation_charges == 0
    assert (
        restored_after.fighters["player"].cooldowns[RECHACO_ID]
        == action_opportunity + 4
    )
    assert _art_event(restored_after).path_per_bonus == D(10)
    duplicate = act(restored_after, "a2", target_id="enemy")
    assert duplicate is restored_after
    line = event_line(restored_after, _art_event(restored_after), viewer_key="player")
    assert "Retaliação" in line and "consumida" in line


def test_round_uses_equipped_rechaco_and_does_not_invent_it_when_unequipped():
    round_service = RoundService(None, "ocaso")
    round_state = type(
        "Round", (), {"prepared_heal": False, "prepared_purify": False}
    )()
    character = type("Character", (), {"id": uuid4()})()

    equipped = _combat(retaliation=True)
    equipped.fighters["player"].last_action = "defend"
    selected = asyncio.run(
        round_service._choose_round_action(
            object(), character, round_state, equipped
        )
    )
    assert selected == ("action", RECHACO_ID)
    resolved = act(equipped, selected[1], target_id="enemy")
    assert _art_event(resolved).path_per_bonus == D(10)
    assert resolved.fighters["player"].retaliation_charges == 0

    unequipped = _combat(equip=False)
    unequipped.fighters["player"].last_action = "defend"
    selected_without_art = asyncio.run(
        round_service._choose_round_action(
            object(), character, round_state, unequipped
        )
    )
    assert selected_without_art == ("action", "attack")

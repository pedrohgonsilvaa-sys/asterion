import asyncio
from decimal import ROUND_FLOOR, Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from asterion.application.active_arts import (
    ActiveArtCharacterView,
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    ActiveArtSlotSnapshot,
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
    ART_WEAPON_REQUIREMENTS,
    ERRANTE_ART_IDS,
    active_art_definition,
    weapon_requirement_satisfied,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Combat,
    DotState,
    Effect,
    Fighter,
    _remove_selected_effect_component,
    act,
    allowed_actions,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, direct_damage
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
ZERO = Decimal(0)
HP_DEFAULT = Decimal(10000)
BRECHA_ID = ERRANTE_ART_IDS["brecha_mortal"]
BRECHA_EXPOSTA = "talent.errante.brecha_exposta"
OPORTUNISMO_AMPLIADO = "talent.errante.oportunismo_ampliado"


async def _seed_errante(
    database,
    actor: int,
    *,
    level: int,
    path: str | None = None,
    character_class: str = "errante",
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
                name=f"Brecha{suffix}"[:16],
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
                f"brecha-mortal:{actor}",
                "Comum",
                level,
                weapon_type_id=weapon_type_id,
            )
            item_id, payload = equipment_instance_payload(payload)
            session.add(
                EquipmentItem(
                    id=item_id,
                    character_id=character_id,
                    source_key=f"brecha-mortal:{actor}:weapon",
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
    per: Decimal = ZERO,
    talents: tuple[str, ...] = (),
    level: int = 34,
    enemy_hp: Decimal = HP_DEFAULT,
    enemy_evasion: Decimal = ZERO,
    enemy_barrier: Decimal = ZERO,
    effects: tuple[Effect, ...] = (),
    dots: tuple[DotState, ...] = (),
    equipped: bool = True,
):
    player = Fighter(
        id="player",
        name="Errante",
        level=level,
        stats=CombatStats(D(1000), D(100), D(0), D(100), per=per, crit=D(0)),
        hp=D(1000),
        race="remanescente",
        character_class="errante",
        selected_path=path,
        talent_ids=talents,
    )
    enemy = Fighter(
        id="enemy",
        name="Alvo",
        level=level,
        stats=CombatStats(
            D(10000), D(0), D(100), D(1), per=D(0), crit=D(0),
            evasion=enemy_evasion,
        ),
        hp=enemy_hp,
        side="enemy",
        takes_turn=False,
        effects=list(effects),
        barrier=enemy_barrier,
        barrier_remaining=2 if enemy_barrier else 0,
        barrier_source="test:protection" if enemy_barrier else "",
    )
    actions = class_player_actions(
        "errante", (BRECHA_ID,) if equipped else (), selected_path=path
    )
    state = Combat(
        id=UUID("9ef5e4e7-c8bf-4795-8bc9-a9e9be8ba801"),
        ruleset=CURRENT_COMBAT_RULESET,
        fighters={"player": player, "enemy": enemy},
        player_actions=actions,
        enemy_actions={"enemy.hit": Action("enemy.hit", "Golpe", D("0.50"))},
        ai_cycle=("enemy.hit",),
        configuration_snapshot={
            "selected_path": path,
            "active_arts": ([{"slot": 2, "art_id": BRECHA_ID}] if equipped else []),
        },
    )
    state.dot_states["enemy"] = list(dots)
    return start_combat(state)


def _event(state: Combat):
    return next(event for event in state.events if event.action == BRECHA_ID)


def test_brecha_mortal_has_canonical_catalog_and_runtime_definition():
    definition = active_art_definition(BRECHA_ID)
    assert definition is not None
    assert definition.art_id == "class_art.errante.brecha_mortal"
    assert definition.character_class == "errante"
    assert definition.min_level == 34
    assert definition.path_id is None
    assert definition.weapon_requirement == frozenset({"weapon.compat.melee"})
    assert BRECHA_ID in ACTIVE_ART_IDS_BY_CLASS["errante"]
    assert ACTIVE_ART_DEFINITIONS[BRECHA_ID] == definition
    assert ART_WEAPON_REQUIREMENTS[BRECHA_ID] == frozenset({"weapon.compat.melee"})

    action = class_player_actions("errante", (BRECHA_ID,))[BRECHA_ID]
    assert action.name == "Brecha Mortal"
    assert action.coefficient == D("1.30")
    assert action.cooldown == 3
    assert action.hit_count == 1
    assert action.target_mode == "opponent"
    assert not action.attack_debuff and not action.native_dot_kind
    assert not action.heal_coefficient and not action.target_barrier_coefficient
    assert len(action.conditional_modifiers) == 1
    modifier = action.conditional_modifiers[0]
    assert modifier.id == "errante.brecha_mortal.opportunism_per"
    assert modifier.condition.kind == "target_has_normal_negative_effect"
    assert modifier.component == "precision_bonus"
    assert modifier.magnitude == D(10)
    assert modifier.target_scope == "primary_target"
    assert modifier.evaluation_scope == "per_action"


@pytest.mark.asyncio
async def test_brecha_mortal_level_paths_class_and_saved_configuration(database):
    service = ActiveArtService(database[1], "ocaso")
    cases = (
        (988101, 33, None, "errante", False),
        (988102, 34, None, "errante", True),
        (988103, 34, "carrasco", "errante", True),
        (988104, 34, "sabotador", "errante", True),
        (988105, 60, None, "vigia", False),
    )
    character_ids = {}
    for actor, level, path, character_class, eligible in cases:
        character_id, _ = await _seed_errante(
            database,
            actor,
            level=level,
            path=path,
            character_class=character_class,
            weapon_type_id="weapon.type.tdo.arma_caminhante"
            if character_class == "errante" and level >= 34
            else None,
        )
        character_ids[actor] = character_id
        view = await service.view(actor)
        assert view is not None
        assert (BRECHA_ID in view.available_art_ids) is eligible
    with pytest.raises(ActiveArtMutationRejected) as low_level:
        await service.equip_art(988101, 1, BRECHA_ID)
    assert low_level.value.code == ActiveArtMutationCode.LEVEL_REQUIRED
    with pytest.raises(ActiveArtMutationRejected) as wrong_class:
        await service.equip_art(988105, 1, BRECHA_ID)
    assert wrong_class.value.code == ActiveArtMutationCode.WRONG_CLASS

    for actor in (988102, 988103, 988104):
        result = await service.equip_art(actor, 2, BRECHA_ID)
        assert result is not None and result.changed
        async with database[1].begin() as session:
            character = await session.get(Character, character_ids[actor])
            configuration = await load_active_art_configuration(session, character)
            slot = await session.scalar(
                select(CharacterActiveArtSlot).where(
                    CharacterActiveArtSlot.character_id == character_ids[actor],
                    CharacterActiveArtSlot.slot == 2,
                )
            )
        assert configuration.art_ids == (BRECHA_ID,)
        assert slot is not None and slot.art_id == BRECHA_ID


@pytest.mark.asyncio
async def test_brecha_mortal_melee_requirement_and_combat_configuration_lock(database):
    service = ActiveArtService(database[1], "ocaso")
    await _seed_errante(database, 988111, level=34, weapon_type_id=None)
    view = await service.view(988111)
    assert view is not None and BRECHA_ID in view.available_art_ids
    assert BRECHA_ID in view.weapon_incompatible_art_ids
    with pytest.raises(ActiveArtMutationRejected) as unarmed:
        await service.equip_art(988111, 1, BRECHA_ID)
    assert unarmed.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT

    await _seed_errante(
        database,
        988112,
        level=34,
        path="sabotador",
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )
    incompatible = await service.view(988112)
    assert incompatible is not None
    assert BRECHA_ID in incompatible.weapon_incompatible_art_ids
    with pytest.raises(ActiveArtMutationRejected) as ranged:
        await service.equip_art(988112, 1, BRECHA_ID)
    assert ranged.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT

    await _seed_errante(
        database,
        988113,
        level=34,
        path="carrasco",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    await service.equip_art(988113, 1, BRECHA_ID)
    async with database[1].begin() as session:
        character_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == 988113)
        )
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=character_id,
                content_id="test.brecha_mortal",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    with pytest.raises(CombatConfigurationLocked):
        await service.equip_art(988113, 2, BRECHA_ID)


def test_brecha_mortal_weapon_tags_and_doutrina_choices_are_explicit():
    definition = active_art_definition(BRECHA_ID)
    assert not weapon_requirement_satisfied(definition, frozenset())
    assert not weapon_requirement_satisfied(
        definition, frozenset({"weapon.compat.bow", "weapon.compat.crossbow"})
    )
    assert weapon_requirement_satisfied(
        definition, frozenset({"weapon.compat.melee"})
    )
    unknown = resolve_weapon_metadata({"weapon_type_id": "weapon.type.unknown"})
    assert unknown.status is WeaponMetadataStatus.UNMAPPED
    assert unknown.definition is None

    view = DoctrineCollectionView(
        character_name="Errante",
        character_class="errante",
        selected_path=None,
        configuration_version=0,
        foreground=False,
        current_configuration={"path": None, "equipment": {}, "arts": {}, "talents": []},
        doctrines=(),
        crowns=0,
        level=34,
    )
    doctrine = DoctrineView(
        doctrine_id=uuid4(),
        name="Brecha",
        revision=1,
        configuration={"path": None, "equipment": {}, "arts": {}, "talents": []},
        is_current=False,
        incomplete_reason=None,
        can_apply=True,
    )
    assert BRECHA_ID in doctrine_art_ids(view, doctrine)
    choices = render_art_choices(view, doctrine, 1)
    assert any(
        "Brecha Mortal" in button.text
        for row in choices.keyboard.inline_keyboard
        for button in row
    )


def test_brecha_mortal_loses_opportunism_after_shared_purification_removal():
    state = _combat(
        effects=(Effect("removable_slow", "agility", D("0.10"), 2, 0),)
    )
    removed = _remove_selected_effect_component(
        state, "enemy", "e1", "purification"
    )
    assert removed == ("removable_slow", "effect")
    assert state.fighters["enemy"].effects == []
    resolved = act(state, BRECHA_ID, target_id="enemy")
    event = _event(resolved)
    assert event.path_per_bonus == D(0)
    assert event.path_final_damage_bonus == D(0)


@pytest.mark.parametrize(
    ("effects", "dots", "fixed_only", "expected_per", "expected_final"),
    [
        ((), (), False, D(0), D(0)),
        ((Effect("slow", "agility", D("0.10"), 2, 0),), (), False, D(10), D("0.08")),
        ((), (DotState("poison", 1, 2, D(20), "enemy"),), False, D(10), D("0.08")),
        ((Effect("expired", "attack", D("0.10"), 0, 0),), (), False, D(0), D(0)),
        ((Effect("fixed", "attack", D("0.10"), 2, 0, fixed_mechanic=True),), (), True, D(0), D(0)),
        ((Effect("positive", "attack", D("0.10"), 2, 0, kind="buff"),), (), False, D(0), D(0)),
    ],
)
def test_brecha_mortal_uses_only_valid_normal_negative_effects_snapshot(
    effects, dots, fixed_only, expected_per, expected_final
):
    state = _combat(effects=effects, dots=dots)
    if fixed_only:
        state.fighters["enemy"].path_state["boss_phase_mark"] = {
            "remaining": 2,
            "kind": "internal",
        }
    assert BRECHA_ID in allowed_actions(state)
    resolved = act(state, BRECHA_ID, target_id="enemy")
    event = _event(resolved)
    base = direct_damage(
        D(100), D("1.30"), D(100), 34,
        penetration=state.fighters["player"].stat("per") + expected_per,
    )
    expected_damage = int(
        (D(base) * (D(1) + expected_final)).to_integral_value(rounding=ROUND_FLOOR)
    )
    assert event.calculated_damage == expected_damage
    assert event.path_per_bonus == expected_per
    assert event.path_final_damage_bonus == expected_final
    assert ("oportunismo" in event.path_triggers) is bool(expected_final)
    assert resolved.fighters["player"].cooldowns[BRECHA_ID] == (
        state.fighters["player"].opportunity + 3
    )


def test_brecha_mortal_bonus_is_not_multiplied_by_negative_stack_count():
    state = _combat(
        effects=(
            Effect("attack_down", "attack", D("0.10"), 2, 0),
            Effect("defense_down", "defense", D("0.10"), 2, 0),
        ),
        dots=(DotState("poison", 2, 2, D(20), "enemy"),),
    )
    resolved = act(state, BRECHA_ID, target_id="enemy")
    event = _event(resolved)
    assert event.path_per_bonus == D(10)
    assert event.path_final_damage_bonus == D("0.08")


@pytest.mark.parametrize(
    ("path", "enemy_hp", "effects", "talents", "actor_per", "expected_per", "expected_final"),
    [
        (
            None,
            HP_DEFAULT,
            (Effect("slow", "agility", D("0.10"), 2, 0),),
            (),
            D(5),
            D(10),
            D("0.08"),
        ),
        (
            None,
            HP_DEFAULT,
            (Effect("slow", "agility", D("0.10"), 2, 0),),
            (BRECHA_EXPOSTA,),
            D(5),
            D(14),
            D("0.08"),
        ),
        (
            None,
            HP_DEFAULT,
            (Effect("slow", "agility", D("0.10"), 2, 0),),
            (BRECHA_EXPOSTA,),
            D(24),
            D(14),
            D("0.08"),
        ),
        (
            "carrasco",
            D(4000),
            (Effect("slow", "agility", D("0.10"), 2, 0),),
            (),
            D(0),
            D(10),
            D("0.16"),
        ),
        ("carrasco", D(4000), (), (), D(0), D(0), D("0.08")),
    ],
)
def test_brecha_mortal_combines_per_cap_opportunism_and_sentenca(
    path, enemy_hp, effects, talents, actor_per, expected_per, expected_final
):
    state = _combat(
        path=path,
        enemy_hp=enemy_hp,
        effects=effects,
        talents=talents,
        per=actor_per,
    )
    event = _event(act(state, BRECHA_ID, target_id="enemy"))
    assert event.path_per_bonus == expected_per
    assert event.path_final_damage_bonus == expected_final
    if actor_per + expected_per > 30:
        expected = direct_damage(
            D(100), D("1.30"), D(100), 34, penetration=D(30)
        )
        expected = int(
            (D(expected) * (D(1) + expected_final)).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        assert event.calculated_damage == expected
    if path == "carrasco" and enemy_hp == D(4000) and effects:
        assert "carrasco.sentenca" in event.path_triggers
        assert "oportunismo" in event.path_triggers


def test_brecha_mortal_oportunismo_ampliado_is_applied_once_only_when_selected():
    state = _combat(
        level=35,
        talents=(OPORTUNISMO_AMPLIADO,),
        effects=(Effect("slow", "agility", D("0.10"), 2, 0),),
    )
    event = _event(act(state, BRECHA_ID, target_id="enemy"))
    assert event.path_final_damage_bonus == D("0.10")
    assert event.path_per_bonus == D(10)
    assert event.path_triggers.count("oportunismo") == 1


def test_brecha_mortal_does_not_extend_or_apply_effects_under_interferencia():
    slow = Effect(
        "preexisting_slow", "agility", D("0.18"), 2, 0,
        kind="debuff", application_event="prior-application",
    )
    state = _combat(path="sabotador", effects=(slow,))
    resolved = act(state, BRECHA_ID, target_id="enemy")
    current = next(effect for effect in resolved.fighters["enemy"].effects if effect.id == slow.id)
    event = _event(resolved)
    assert current.magnitude == slow.magnitude
    assert current.remaining == slow.remaining
    assert current.application_event == "prior-application"
    assert event.target_effect_ids == (slow.id,)
    assert event.target_effect_application_event_ids == ("prior-application",)
    assert event.applied_effect_duration == 0
    assert event.path_per_bonus == D(10)


def test_brecha_mortal_resolves_one_hit_and_barrier_without_vampirism():
    barriered = _combat(enemy_barrier=D(10000))
    before_hp = barriered.fighters["player"].hp
    resolved = act(barriered, BRECHA_ID, target_id="enemy")
    event = _event(resolved)
    assert event.hit_count == 1
    assert event.calculated_damage > 0
    assert event.effective_damage == 0
    assert resolved.fighters["player"].hp == before_hp
    assert resolved.fighters["enemy"].barrier == D(10000) - event.calculated_damage

    partial = _combat(enemy_barrier=D(10))
    partial_resolved = act(partial, BRECHA_ID, target_id="enemy")
    partial_event = _event(partial_resolved)
    assert partial_event.barrier_absorbed == D(10)
    assert partial_event.effective_damage == partial_event.calculated_damage - 10


@pytest.mark.parametrize("invalid", ("defeated", "ally", "unequipped", "cooldown"))
def test_brecha_mortal_invalid_action_does_not_commit_or_start_cooldown(invalid):
    state = _combat(equipped=invalid != "unequipped")
    if invalid == "defeated":
        state.fighters["enemy"].hp = D(0)
    elif invalid == "ally":
        state.fighters["ally"] = Fighter(
            id="ally", name="Aliado", level=34,
            stats=state.fighters["player"].stats, hp=D(1000),
            side="player", takes_turn=False,
        )
    elif invalid == "cooldown":
        state.fighters["player"].cooldowns[BRECHA_ID] = (
            state.fighters["player"].opportunity + 3
        )
    original_cooldown = state.fighters["player"].cooldowns.get(BRECHA_ID)
    target = "ally" if invalid == "ally" else "enemy"
    rejected = act(state, BRECHA_ID, target_id=target)
    assert rejected is state
    assert state.fighters["player"].cooldowns.get(BRECHA_ID) == original_cooldown
    assert not any(event.action == BRECHA_ID for event in state.events)


def test_brecha_mortal_commit_cooldown_reconnect_and_duplicate_callback():
    state = _combat(
        path="carrasco",
        effects=(Effect("slow", "agility", D("0.10"), 2, 0),),
    )
    restored_before = decode(encode(state), state.id, state.ruleset, state.version)
    expected_cooldown = restored_before.fighters["player"].opportunity + 3
    assert BRECHA_ID in allowed_actions(restored_before)
    resolved = act(restored_before, BRECHA_ID, target_id="enemy")
    event = _event(resolved)
    assert event.path_per_bonus == D(10)
    assert event.path_final_damage_bonus == D("0.08")
    assert resolved.fighters["player"].cooldowns[BRECHA_ID] == expected_cooldown
    restored_after = decode(encode(resolved), resolved.id, resolved.ruleset, resolved.version)
    assert _event(restored_after).path_per_bonus == D(10)
    assert restored_after.fighters["player"].cooldowns[BRECHA_ID] == expected_cooldown
    duplicate = act(restored_after, BRECHA_ID, target_id="enemy")
    assert duplicate is restored_after
    assert sum(event.action == BRECHA_ID for event in duplicate.events) == 1


def test_brecha_mortal_detail_combat_hud_and_round_keep_equipped_action_context():
    state = _combat(effects=(Effect("slow", "agility", D("0.10"), 2, 0),))
    view = ActiveArtCharacterView(
        character_id=uuid4(), character_name="Errante", character_class="errante",
        level=34, selected_path=None, combat_configuration_version=1,
        slots=(ActiveArtSlotSnapshot(2, BRECHA_ID),), available_art_ids=(BRECHA_ID,),
        foreground=False,
    )
    detail = render_art_detail(view, BRECHA_ID)
    assert "Desbloqueio · Nv.34" in detail.text
    assert "130% ATQ" in detail.text
    assert "+10 p.p. PER" in detail.text
    assert "Arma corpo a corpo compatível" in detail.text

    screen = render_combat(
        CombatView(uuid4(), uuid4(), uuid4(), state, "test", 0, context="road")
    )
    assert "Brecha Mortal" in screen.text
    assert "Oportunismo · elegível" in screen.text
    button = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Brecha Mortal"
    )
    assert CombatCallback.unpack(button.callback_data).action == "a2"
    resolved = act(state, BRECHA_ID, target_id="enemy")
    line = event_line(resolved, _event(resolved), viewer_key="player")
    assert "Brecha Mortal" in line
    assert "PER da ação · +10 p.p." in line

    round_service = RoundService(None, "ocaso")
    round_state = type("Round", (), {"prepared_heal": False, "prepared_purify": False})()
    character = type("Character", (), {"id": uuid4()})()
    state.fighters["player"].last_action = "defend"
    selected = asyncio.run(
        round_service._choose_round_action(object(), character, round_state, state)
    )
    assert selected == ("action", BRECHA_ID)


@pytest.mark.asyncio
async def test_brecha_mortal_doutrina_weapon_and_slot_limit_regressions(database):
    actor = 988120
    _, sessions = await _seed_errante(
        database,
        actor,
        level=34,
        path="carrasco",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    service = ActiveArtService(sessions, "ocaso")
    for slot, art_id in (
        (1, ERRANTE_ART_IDS["corte_veloz"]),
        (2, ERRANTE_ART_IDS["corte_duplo"]),
        (3, BRECHA_ID),
    ):
        await service.equip_art(actor, slot, art_id)
    view = await service.view(actor)
    assert view is not None
    assert tuple(slot.art_id for slot in view.slots) == (
        ERRANTE_ART_IDS["corte_veloz"],
        ERRANTE_ART_IDS["corte_duplo"],
        BRECHA_ID,
    )
    assert BRECHA_ID not in view.weapon_incompatible_art_ids
    assert BRECHA_ID in class_player_actions("errante", (BRECHA_ID,), "carrasco")
    assert BRECHA_ID in class_player_actions("errante", (BRECHA_ID,), "sabotador")
    assert BRECHA_ID in class_player_actions("errante", (BRECHA_ID,), None)
    assert BRECHA_ID not in class_player_actions("errante", ())

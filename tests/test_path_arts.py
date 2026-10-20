from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.arts import DEVASTADOR_ART_IDS, FIRST_CLASS_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Combat, Fighter, act, allowed_actions, start_combat
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, direct_damage
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.path_arts import PATH_ART_ACTIONS
from asterion.domain.road import (
    CREATURES,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    create_road_combat,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ARIETE_ID = DEVASTADOR_ART_IDS["ariete"]


def _ariete_battle(*, retaliation: bool = False, charge: bool = False) -> Combat:
    player = Fighter(
        id="player",
        name="Sentinela",
        level=20,
        stats=CombatStats(D(1000), D(100), D(0), D(100), per=D(0), crit=D(0)),
        hp=D(1000),
        character_class="sentinela",
        selected_path="devastador",
        takes_turn=True,
    )
    enemy = Fighter(
        id="enemy",
        name="Alvo",
        level=20,
        stats=CombatStats(
            D(1000), D(0), D(100), D(0), per=D(0), crit=D(0), evasion=D(0)
        ),
        hp=D(1000),
        side="enemy",
        takes_turn=False,
    )
    if retaliation:
        player.retaliation_charges = 1
        player.retaliation_remaining = 1
        player.retaliation_activation_id = "test:retaliation"
        player.retaliation_source_type = "defender"
        player.retaliation_source_event_id = "test:defender-event"
        player.retaliation_source_actor_id = "enemy"
    if charge:
        player.path_state["devastador_charge"] = {
            "expires_opportunity": 3,
            "source_action": "enemy.hit",
        }
    return start_combat(
        Combat(
            UUID("f77365ce-14b2-467f-bcd4-395ac6e8f3a5"),
            CURRENT_COMBAT_RULESET,
            {"player": player, "enemy": enemy},
            {
                "attack": class_player_actions("sentinela", ())["attack"],
                ARIETE_ID: PATH_ART_ACTIONS[ARIETE_ID].action,
            },
            {},
            (),
        )
    )


def test_path_art_pipeline_requires_registered_identity_and_current_path():
    first_class_art = FIRST_CLASS_ART_IDS["sentinela"]
    actions = class_player_actions(
        "sentinela",
        (first_class_art, ARIETE_ID),
        selected_path="devastador",
    )
    assert set(actions) == {"attack", first_class_art, ARIETE_ID}

    with pytest.raises(ValueError, match="Path Art"):
        class_player_actions("sentinela", (ARIETE_ID,))
    with pytest.raises(ValueError, match="Path Art"):
        class_player_actions("sentinela", (ARIETE_ID,), selected_path="bastiao")
    with pytest.raises(ValueError, match="Path Art"):
        class_player_actions("vigia", (ARIETE_ID,), selected_path="devastador")
    with pytest.raises(ValueError, match="Path Art"):
        class_player_actions(
            "sentinela",
            ("path_art.sentinela.devastador.ruptor",),
            selected_path="devastador",
        )
    with pytest.raises(ValueError, match="three unique Arts"):
        class_player_actions(
            "sentinela",
            (
                first_class_art,
                "class_art.sentinela.quebra_postura",
                "class_art.sentinela.muralha_breve",
                ARIETE_ID,
            ),
            selected_path="devastador",
        )


def test_shared_road_combat_materializes_only_equipped_path_art_from_snapshot():
    combat = create_road_combat(
        UUID("a38909ea-5d26-4f05-a1c4-c3ea9305770a"),
        "Teste",
        "sentinela",
        "remanescente",
        D(1000),
        CREATURES[0],
        1,
        None,
        player_level=20,
        equipment_configuration=EquipmentConfigurationSnapshot(
            combat_configuration_version=8,
            selected_path="devastador",
        ),
        active_art_ids=(ARIETE_ID,),
    )
    assert ARIETE_ID in combat.player_actions
    assert "path_art.sentinela.devastador.ruptor" not in combat.player_actions
    assert combat.player_actions[ARIETE_ID].coefficient == D("1.35")
    assert combat.player_actions[ARIETE_ID].cooldown == 2


def test_group_combat_uses_each_members_path_art_snapshot_independently():
    configuration = EquipmentConfigurationSnapshot(
        combat_configuration_version=3,
        selected_path="devastador",
    )
    party = tuple(
        PlayerCombatantSpec(
            fighter_key=f"player-{index}",
            character_id=f"character-{index}",
            name=f"Sentinela {index}",
            character_class="sentinela",
            race="remanescente",
            level=20,
            hp=D(1000),
            equipment_configuration=configuration,
            active_art_ids=(ARIETE_ID,) if index == 1 else (),
            active_art_snapshots=(
                ({"slot": 2, "art_id": ARIETE_ID},) if index == 1 else ()
            ),
        )
        for index in (1, 2)
    )
    combat = create_creature_party_combat(
        UUID("f096450c-4c50-484c-ae77-613969343a11"),
        "Grupo",
        "sentinela",
        "remanescente",
        D(1000),
        (CreatureCombatantSpec(CREATURES[0], 1, "enemy"),),
        player_level=20,
        party=party,
        active_art_ids=(),
    )
    assert ARIETE_ID in combat.player_actions_by_fighter["player-1"]
    assert ARIETE_ID not in combat.player_actions_by_fighter["player-2"]
    assert combat.player_configuration_snapshots["player-1"]["selected_path"] == "devastador"


def test_ariete_resolves_135_percent_with_ten_per_points_and_cd2():
    combat = _ariete_battle()
    opportunity_before = combat.fighters["player"].opportunity
    updated = act(combat, ARIETE_ID, target_id="enemy")
    assert updated is not combat
    event = next(event for event in updated.events if event.action == ARIETE_ID)
    assert event.target == "enemy"
    assert event.effective_damage == direct_damage(
        D(100), D("1.35"), D(100), 20, penetration=D(10)
    )
    assert updated.fighters["player"].cooldowns[ARIETE_ID] == opportunity_before + 2
    assert ARIETE_ID not in allowed_actions(updated)
    assert updated.fighters["player"].opportunity == opportunity_before + 1
    restored = decode(encode(updated), updated.id, updated.ruleset, updated.version)
    assert restored.player_actions[ARIETE_ID].actor_per_bonus == D(10)
    assert restored.fighters["player"].cooldowns[ARIETE_ID] == opportunity_before + 2


def test_ariete_uses_retaliation_and_consumes_impacto_doloroso_only_on_valid_commit():
    invalid = _ariete_battle(retaliation=True, charge=True)
    invalid.fighters["enemy"].hp = D(0)
    rejected = act(invalid, ARIETE_ID, target_id="enemy")
    assert rejected is invalid
    assert invalid.fighters["player"].retaliation_charges == 1
    assert "devastador_charge" in invalid.fighters["player"].path_state

    combat = _ariete_battle(retaliation=True, charge=True)
    updated = act(combat, ARIETE_ID, target_id="enemy")
    event = next(event for event in updated.events if event.action == ARIETE_ID)
    assert event.retaliation_used is True
    assert event.path_final_damage_bonus == D("0.12")
    assert updated.fighters["player"].retaliation_charges == 0
    assert "devastador_charge" not in updated.fighters["player"].path_state


def test_path_art_action_is_a_full_shared_action_contract():
    action = PATH_ART_ACTIONS[ARIETE_ID].action
    assert action.coefficient == D("1.35")
    assert action.actor_per_bonus == D(10)
    assert action.cooldown == 2
    assert action.target_mode == "opponent"
    assert action.hit_count == 1
    assert action.native_dot_kind is None
    assert action.attack_debuff == D(0)
    assert action.self_barrier_coefficient == D(0)
    assert not action.target_effects

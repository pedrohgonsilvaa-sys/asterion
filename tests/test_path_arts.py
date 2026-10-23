from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.arts import (
    AGOUREIRO_ART_IDS,
    ATIRADOR_ART_IDS,
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    CONJURADOR_ART_IDS,
    DEVASTADOR_ART_IDS,
    FIRST_CLASS_ART_IDS,
    GUARDIAO_ART_IDS,
    INQUISIDOR_ART_IDS,
    INVOCADOR_ART_IDS,
    LUMINAR_ART_IDS,
    ORACULO_ART_IDS,
    RASTREADOR_ART_IDS,
    RUNICO_ART_IDS,
    SABOTADOR_ART_IDS,
    TECELAO_ART_IDS,
)
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


def _path_battle(
    character_class: str,
    path_id: str,
    art_id: str,
    *,
    target_hp=1000,
    action_ids: tuple[str, ...] | None = None,
    target_aim_stacks: int = 0,
    include_ally: bool = False,
    actor_talents: tuple[str, ...] = (),
):
    player = Fighter(
        id="player",
        name=character_class,
        level=20,
        stats=CombatStats(D(1000), D(100), D(0), D(100), per=D(0), crit=D(0)),
        hp=D(1000),
        character_class=character_class,
        selected_path=path_id,
        talent_ids=actor_talents,
        takes_turn=True,
    )
    enemy = Fighter(
        id="enemy",
        name="Alvo",
        level=20,
        stats=CombatStats(
            D(1000), D(0), D(100), D(0), per=D(0), crit=D(0), evasion=D(0)
        ),
        hp=D(target_hp),
        side="enemy",
        takes_turn=False,
    )
    if target_aim_stacks:
        enemy.path_state["aim_from"] = {
            "player": {
                "stacks": target_aim_stacks,
                "remaining": 2,
                "applied_opportunity": 0,
            }
        }
    fighters = {"player": player, "enemy": enemy}
    if include_ally:
        fighters["ally"] = Fighter(
            id="ally",
            name="Aliado",
            level=20,
            stats=CombatStats(D(1000), D(50), D(100), D(50)),
            hp=D(500),
            side="player",
            takes_turn=False,
        )
    return start_combat(
        Combat(
            UUID("317d88a1-877c-4bc5-ae77-ae87c90a9e21"),
            CURRENT_COMBAT_RULESET,
            fighters,
            class_player_actions(
                character_class,
                action_ids or (art_id,),
                selected_path=path_id,
            ),
            {},
            (),
        )
    )


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


def test_bastiao_escudo_de_cinzas_uses_fortaleza_barrier_pipeline_and_codec():
    art_id = BASTIAO_ART_IDS["escudo_de_cinzas"]
    combat = _path_battle("sentinela", "bastiao", art_id)
    opportunity_before = combat.fighters["player"].opportunity
    updated = act(combat, art_id, target_id="player")
    event = next(event for event in updated.events if event.action == art_id)

    # 95% ATQ is multiplied by Fortaleza's canonical 10%, then floored once.
    assert event.barrier_value == D(104)
    assert event.barrier_duration == 2
    assert event.barrier_power_multiplier == D("1.10")
    assert updated.fighters["player"].barrier == D(104)
    assert updated.fighters["player"].barriers[0].effect_definition_id == art_id
    assert updated.fighters["player"].cooldowns[art_id] == opportunity_before + 3

    restored = decode(encode(updated), updated.id, updated.ruleset, updated.version)
    assert restored.fighters["player"].barrier == D(104)
    assert restored.fighters["player"].barriers[0].remaining == 2


def test_corte_de_execucao_uses_action_start_hp_threshold_and_separate_sentenca():
    art_id = CARRASCO_ART_IDS["corte_de_execucao"]
    above = _path_battle("errante", "carrasco", art_id, target_hp=351)
    at_threshold = _path_battle("errante", "carrasco", art_id, target_hp=350)
    opportunity_before = at_threshold.fighters["player"].opportunity

    above_result = act(above, art_id, target_id="enemy")
    eligible_result = act(at_threshold, art_id, target_id="enemy")
    above_event = next(event for event in above_result.events if event.action == art_id)
    eligible_event = next(
        event for event in eligible_result.events if event.action == art_id
    )

    assert above_event.path_power_multiplier == D(1)
    # Sentença has its own 40% threshold; it remains separate from the Arte's 35% power bonus.
    assert above_event.path_final_damage_bonus == D("0.08")
    assert eligible_event.path_power_multiplier == D("1.15")
    assert eligible_event.path_final_damage_bonus == D("0.08")
    assert "errante.corte_de_execucao.low_hp_power" in eligible_event.path_triggers
    assert eligible_event.damage_power_multiplier == D(1)
    assert (
        eligible_result.fighters["player"].cooldowns[art_id]
        == opportunity_before + 3
    )


def test_sabotador_veneno_velado_applies_normal_poison_and_reconnects():
    art_id = SABOTADOR_ART_IDS["veneno_velado"]
    combat = _path_battle("errante", "sabotador", art_id)
    opportunity_before = combat.fighters["player"].opportunity
    updated = act(combat, art_id, target_id="enemy")
    event = next(event for event in updated.events if event.action == art_id)

    assert event.effective_damage > 0
    assert event.dot_kind == "poison"
    assert event.dot_application_event_id
    poison = updated.dot_states["enemy"][0]
    assert poison.kind == "poison"
    assert poison.stacks == 1
    assert poison.remaining == 3
    assert poison.snapshot_attack == D(100)
    assert updated.fighters["player"].cooldowns[art_id] == opportunity_before + 2

    restored = decode(encode(updated), updated.id, updated.ruleset, updated.version)
    assert restored.dot_states["enemy"][0].instance_id == poison.instance_id
    assert restored.dot_states["enemy"][0].remaining == 3


def test_atirador_tiro_perfurante_adds_action_precision_and_uses_mira_perfeita():
    art_id = ATIRADOR_ART_IDS["tiro_perfurante"]
    combat = _path_battle(
        "vigia", "atirador", art_id, target_aim_stacks=2
    )
    action = combat.player_actions[art_id]
    updated = act(combat, art_id, target_id="enemy")
    event = next(event for event in updated.events if event.action == art_id)

    assert action.coefficient == D("1.30")
    assert action.actor_per_bonus == D(10)
    assert event.aim_stacks == 3  # post-resolution stack; the snapshot bonus is below.
    assert event.path_per_bonus == D(6)
    assert event.calculated_damage == direct_damage(
        D(100), D("1.30"), D(100), 20, penetration=D(16)
    )
    assert updated.fighters["player"].cooldowns[art_id] == 3


def test_rastreador_flecha_serrilhada_applies_bleed_and_one_valid_mira():
    art_id = RASTREADOR_ART_IDS["flecha_serrilhada"]
    combat = _path_battle("vigia", "rastreador", art_id)
    updated = act(combat, art_id, target_id="enemy")
    event = next(event for event in updated.events if event.action == art_id)

    assert event.dot_kind == "bleed"
    assert event.dot_application_event_id
    assert updated.dot_states["enemy"][0].kind == "bleed"
    assert updated.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 1
    assert "vigia.mira_gerada" in event.path_triggers
    assert updated.fighters["player"].cooldowns[art_id] == 3

    blocked = _path_battle("vigia", "rastreador", art_id)
    blocked.fighters["enemy"].ward_charges = 1
    blocked.fighters["enemy"].ward_remaining = 2
    blocked_result = act(blocked, art_id, target_id="enemy")
    blocked_event = next(event for event in blocked_result.events if event.action == art_id)
    assert not blocked_event.dot_application_event_id
    assert not blocked_result.dot_states.get("enemy")
    # A successful direct hit still receives only its normal base Mira; the
    # blocked DoT does not produce an additional Rastros Múltiplos grant.
    assert blocked_result.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 1


def test_conjurador_estilhaco_consumes_trama_from_another_art_once():
    art_id = CONJURADOR_ART_IDS["estilhaco_do_veu"]
    fio_id = TECELAO_ART_IDS["fio_cortante"]
    combat = _path_battle(
        "tecelao",
        "conjurador",
        art_id,
        action_ids=(fio_id, art_id),
    )
    prepared = act(combat, fio_id, target_id="enemy")
    trama = prepared.fighters["player"].path_state["trama_state"]
    assert trama["origin_art"] == fio_id
    assert trama["remaining"] == 2

    consumed = act(prepared, art_id, target_id="enemy")
    event = next(event for event in consumed.events if event.action == art_id)
    assert event.path_power_multiplier == D("1.15")
    assert event.damage_power_multiplier == D(1)
    assert event.class_resource_changes == (("trama", "player", 1, 0),)
    assert "trama_state" not in consumed.fighters["player"].path_state

    restored = decode(encode(consumed), consumed.id, consumed.ruleset, consumed.version)
    assert "trama_state" not in restored.fighters["player"].path_state


def test_runico_runa_de_guarda_targets_ally_and_uses_trama_barrier_power():
    art_id = RUNICO_ART_IDS["runa_de_guarda"]
    veil_id = TECELAO_ART_IDS["veu_entrelacado"]
    combat = _path_battle(
        "tecelao",
        "runico",
        art_id,
        action_ids=(veil_id, art_id),
        include_ally=True,
    )
    prepared = act(combat, veil_id, target_id="player")
    assert prepared.fighters["player"].path_state["trama_state"]["origin_art"] == veil_id

    consumed = act(prepared, art_id, target_id="ally")
    event = next(event for event in consumed.events if event.action == art_id)
    assert event.target == "ally"
    assert event.barrier_value == D(120)
    assert event.barrier_duration == 2
    assert event.barrier_power_multiplier == D("1.15")
    assert event.class_resource_changes == (("trama", "player", 1, 0),)
    ally_barrier = consumed.fighters["ally"].barriers[0]
    assert ally_barrier.identity == ("player", art_id)
    assert ally_barrier.value == D(120)
    assert ally_barrier.remaining == 2
    assert "trama_state" not in consumed.fighters["player"].path_state

    restored = decode(encode(consumed), consumed.id, consumed.ruleset, consumed.version)
    assert restored.fighters["ally"].barriers[0].identity == ("player", art_id)
    assert restored.fighters["ally"].barrier == D(120)


def test_agoureiro_mau_agouro_integrates_debuff_omen_and_public_talent_hooks():
    art_id = AGOUREIRO_ART_IDS["mau_agouro"]
    signal_id = ORACULO_ART_IDS["sinal_funesto"]
    combat = _path_battle(
        "oraculo",
        "agoureiro",
        art_id,
        action_ids=(signal_id, art_id),
        actor_talents=(
            "talent.oraculo.leitura_dos_sinais",
            "talent.oraculo.pressagio_cortante",
            "talent.oraculo.profecia_dolorosa",
        ),
    )
    marked = act(combat, signal_id, target_id="enemy")
    assert marked.fighters["player"].path_state["omen_offensive"]["enemy"]["remaining"] > 0

    resolved = act(marked, art_id, target_id="enemy")
    event = next(event for event in resolved.events if event.action == art_id)
    debuff = next(
        effect
        for effect in resolved.fighters["enemy"].effects
        if effect.id == art_id and effect.stat == "attack"
    )
    assert event.calculated_damage > 0
    assert event.applied_effect_magnitude == D("0.10")
    assert event.applied_effect_duration == 2
    assert debuff.magnitude == D("0.10")
    assert event.path_power_multiplier == D("1.1832")  # 1.16 × Profecia Dolorosa 1.02.
    assert event.path_per_bonus == D(2)  # Presságio Cortante remains a separate PER source.
    assert event.class_resource_changes == (("omen_offensive", "enemy", 1, 0),)
    assert "oraculo.leitura_dos_sinais" in event.path_triggers
    assert resolved.fighters["player"].path_state["omen_offensive"]["enemy"]["remaining"] > 0


def test_invocador_lobo_is_an_action_and_uses_existing_manifestation_state():
    art_id = INVOCADOR_ART_IDS["lobo"]
    combat = _path_battle("oraculo", "invocador", art_id)
    actor = combat.fighters["player"]
    initial_fighter_count = len(combat.fighters)
    actor.path_state["manifestation_state"] = {
        "kind": "coruja",
        "remaining": 2,
        "expires_opportunity": actor.opportunity + 2,
    }

    resolved = act(combat, art_id, target_id="enemy")
    event = next(event for event in resolved.events if event.action == art_id)

    assert event.calculated_damage > 0
    assert event.path_power_multiplier == D("1.12")
    assert "invocador.triade" in event.path_triggers
    assert resolved.fighters["player"].path_state["manifestation_state"]["kind"] == "lobo"
    assert len(resolved.fighters) == initial_fighter_count
    assert all(fighter.id != "lobo" for fighter in resolved.fighters.values())

    restored = decode(encode(resolved), resolved.id, resolved.ruleset, resolved.version)
    assert restored.fighters["player"].path_state["manifestation_state"]["kind"] == "lobo"


def test_guardiao_cura_solar_consumes_fulgor_for_healing_and_generates_julgamento_otherwise():
    art_id = GUARDIAO_ART_IDS["cura_solar"]
    fulgor_id = LUMINAR_ART_IDS["fulgor"]
    combat = _path_battle(
        "luminar",
        "guardiao",
        art_id,
        action_ids=(fulgor_id, art_id),
        include_ally=True,
    )
    prepared = act(combat, fulgor_id, target_id="enemy")
    assert prepared.fighters["player"].path_state["luminar_state"]["kind"] == "fulgor"

    healed = act(prepared, art_id, target_id="ally")
    event = next(event for event in healed.events if event.action == art_id)
    assert event.healed == D(115)
    assert event.path_power_multiplier == D("1.15")
    assert event.class_resource_changes == (("luminar_state", "player", 1, 0),)
    assert "luminar_state" not in healed.fighters["player"].path_state

    restored = decode(encode(healed), healed.id, healed.ruleset, healed.version)
    assert restored.fighters["ally"].hp == D(615)
    assert "luminar_state" not in restored.fighters["player"].path_state

    without_fulgor = _path_battle(
        "luminar", "guardiao", art_id, include_ally=True
    )
    renewed = act(without_fulgor, art_id, target_id="ally")
    renewed_event = next(event for event in renewed.events if event.action == art_id)
    assert renewed_event.healed == D(100)
    assert renewed.fighters["player"].path_state["luminar_state"]["kind"] == "julgamento"
    assert "luminar.julgamento_gerado" in renewed_event.path_triggers

    zero_heal = _path_battle(
        "luminar",
        "guardiao",
        art_id,
        action_ids=(fulgor_id, art_id),
        include_ally=True,
    )
    zero_prepared = act(zero_heal, fulgor_id, target_id="enemy")
    zero_prepared.fighters["ally"].hp = zero_prepared.fighters["ally"].stats.hp
    zero_result = act(zero_prepared, art_id, target_id="ally")
    zero_event = next(event for event in zero_result.events if event.action == art_id)
    assert zero_event.healed == D(0)
    assert zero_event.class_resource_changes == (("luminar_state", "player", 1, 0),)
    assert "luminar_state" not in zero_result.fighters["player"].path_state


def test_inquisidor_lanca_de_luz_consumes_julgamento_and_generates_fulgor_when_unprepared():
    art_id = INQUISIDOR_ART_IDS["lanca_de_luz"]
    renovacao_id = LUMINAR_ART_IDS["renovacao"]
    combat = _path_battle(
        "luminar",
        "inquisidor",
        art_id,
        action_ids=(renovacao_id, art_id),
        include_ally=True,
    )
    prepared = act(combat, renovacao_id, target_id="ally")
    assert prepared.fighters["player"].path_state["luminar_state"]["kind"] == "julgamento"

    consumed = act(prepared, art_id, target_id="enemy")
    event = next(event for event in consumed.events if event.action == art_id)
    assert event.calculated_damage > 0
    assert event.path_power_multiplier == D("1.15")
    assert event.class_resource_changes == (("luminar_state", "player", 1, 0),)
    assert "luminar_state" not in consumed.fighters["player"].path_state

    without_julgamento = _path_battle("luminar", "inquisidor", art_id)
    renewed = act(without_julgamento, art_id, target_id="enemy")
    renewed_event = next(event for event in renewed.events if event.action == art_id)
    assert renewed_event.path_power_multiplier == D(1)
    assert renewed.fighters["player"].path_state["luminar_state"]["kind"] == "fulgor"
    assert "luminar.fulgor_gerado" in renewed_event.path_triggers

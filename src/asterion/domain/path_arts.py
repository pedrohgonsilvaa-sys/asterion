"""Runtime actions for Path Arts implemented by the shared combat engine.

The Action value is the shared combat contract, so a Path Art can declare the
same direct, area, multi-hit, healing, barrier, resource and target behaviors
as any other active Art. This registry intentionally contains only shipped
actions; canonical-but-unimplemented Path Arts are not equipable.
"""

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from asterion.domain.arts import (
    AGOUREIRO_ART_IDS,
    ATIRADOR_ART_IDS,
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    CONJURADOR_ART_IDS,
    DEVASTADOR_ART_IDS,
    GUARDIAO_ART_IDS,
    INQUISIDOR_ART_IDS,
    INVOCADOR_ART_IDS,
    RASTREADOR_ART_IDS,
    RUNICO_ART_IDS,
    SABOTADOR_ART_IDS,
)
from asterion.domain.combat import (
    Action,
    ActionCondition,
    ActionConditionalModifier,
    ActionEffect,
    ActionEffectRemoval,
    ActionResourceUse,
)


@dataclass(frozen=True, slots=True)
class PathArtActionDefinition:
    art_id: str
    character_class: str
    path_id: str
    action: Action


ARIETE_ART_ID = DEVASTADOR_ART_IDS["ariete"]
ESCUDO_DE_CINZAS_ART_ID = BASTIAO_ART_IDS["escudo_de_cinzas"]
INTERPOR_ART_ID = BASTIAO_ART_IDS["interpor"]
GOLPE_DE_RUPTURA_ART_ID = DEVASTADOR_ART_IDS["golpe_de_ruptura"]
CORTE_DE_EXECUCAO_ART_ID = CARRASCO_ART_IDS["corte_de_execucao"]
HEMORRAGIA_ART_ID = CARRASCO_ART_IDS["hemorragia"]
VENENO_VELADO_ART_ID = SABOTADOR_ART_IDS["veneno_velado"]
FIO_CORTADO_ART_ID = SABOTADOR_ART_IDS["fio_cortado"]
TIRO_PERFURANTE_ART_ID = ATIRADOR_ART_IDS["tiro_perfurante"]
FIXAR_ALVO_ART_ID = ATIRADOR_ART_IDS["fixar_alvo"]
FLECHA_SERRILHADA_ART_ID = RASTREADOR_ART_IDS["flecha_serrilhada"]
LACO_DE_CACA_ART_ID = RASTREADOR_ART_IDS["laco_de_caca"]
ESTILHACO_DO_VEU_ART_ID = CONJURADOR_ART_IDS["estilhaco_do_veu"]
INCENDIO_TRANCADO_ART_ID = CONJURADOR_ART_IDS["incendio_trancado"]
RUNA_DE_GUARDA_ART_ID = RUNICO_ART_IDS["runa_de_guarda"]
RUNA_DE_RUPTURA_ART_ID = RUNICO_ART_IDS["runa_de_ruptura"]
MAU_AGOURO_ART_ID = AGOUREIRO_ART_IDS["mau_agouro"]
DESTINO_LENTO_ART_ID = AGOUREIRO_ART_IDS["destino_lento"]
LOBO_ART_ID = INVOCADOR_ART_IDS["lobo"]
CORUJA_ART_ID = INVOCADOR_ART_IDS["coruja"]
CURA_SOLAR_ART_ID = GUARDIAO_ART_IDS["cura_solar"]
EGIDE_COMPARTILHADA_ART_ID = GUARDIAO_ART_IDS["egide_compartilhada"]
LANCA_DE_LUZ_ART_ID = INQUISIDOR_ART_IDS["lanca_de_luz"]
SELO_DA_PENITENCIA_ART_ID = INQUISIDOR_ART_IDS["selo_da_penitencia"]
CONTRA_GOLPE_ART_ID = BASTIAO_ART_IDS["contra_golpe"]
ABALO_ART_ID = DEVASTADOR_ART_IDS["abalo"]
MARCA_DA_MORTE_ART_ID = CARRASCO_ART_IDS["marca_da_morte"]
TRAVA_DE_PASSOS_ART_ID = SABOTADOR_ART_IDS["trava_de_passos"]
ULTIMA_MURALHA_ART_ID = BASTIAO_ART_IDS["ultima_muralha"]
RUPTOR_ART_ID = DEVASTADOR_ART_IDS["ruptor"]
CEIFA_ART_ID = CARRASCO_ART_IDS["ceifa"]
COLAPSO_PREPARADO_ART_ID = SABOTADOR_ART_IDS["colapso_preparado"]
DISPARO_TERMINAL_ART_ID = ATIRADOR_ART_IDS["disparo_terminal"]
PREDACAO_PERSISTENTE_ART_ID = RASTREADOR_ART_IDS["predacao_persistente"]
RASGO_CONJURADO_ART_ID = CONJURADOR_ART_IDS["rasgo_conjurado"]
CIRCULO_RUNICO_ART_ID = RUNICO_ART_IDS["circulo_runico"]
RAJADA_CONTROLADA_ART_ID = ATIRADOR_ART_IDS["rajada_controlada"]
CHUVA_DE_RASTROS_ART_ID = RASTREADOR_ART_IDS["chuva_de_rastros"]
CONVERGENCIA_ARCANA_ART_ID = CONJURADOR_ART_IDS["convergencia_arcana"]
RUNA_DE_RETORNO_ART_ID = RUNICO_ART_IDS["runa_de_retorno"]
CONDENACAO_ART_ID = AGOUREIRO_ART_IDS["condenacao"]
URSO_ART_ID = INVOCADOR_ART_IDS["urso"]
PURGACAO_LUMINOSA_ART_ID = GUARDIAO_ART_IDS["purgacao_luminosa"]
PURGA_ARDENTE_ART_ID = INQUISIDOR_ART_IDS["purga_ardente"]

CARRASCO_MARCA_DA_MORTE_CHAIN = "errante.carrasco.marca_da_morte"
AGOUREIRO_CONDENACAO_CHAIN = "oraculo.agoureiro.condemnacao"

PATH_ART_ACTIONS = MappingProxyType(
    {
        ESCUDO_DE_CINZAS_ART_ID: PathArtActionDefinition(
            art_id=ESCUDO_DE_CINZAS_ART_ID,
            character_class="sentinela",
            path_id="bastiao",
            action=Action(
                ESCUDO_DE_CINZAS_ART_ID,
                "Escudo de Cinzas",
                Decimal(0),
                cooldown=3,
                target_mode="self",
                self_barrier_coefficient=Decimal("0.95"),
                self_barrier_duration=2,
            ),
        ),
        INTERPOR_ART_ID: PathArtActionDefinition(
            art_id=INTERPOR_ART_ID,
            character_class="sentinela",
            path_id="bastiao",
            action=Action(
                INTERPOR_ART_ID,
                "Interpor",
                Decimal(0),
                cooldown=4,
                target_mode="ally",
                target_effects=(
                    ActionEffect(
                        "class_mechanic.sentinela.interpor",
                        "interpor_next_direct",
                        Decimal("0.25"),
                        2,
                        "buff",
                    ),
                ),
            ),
        ),
        ARIETE_ART_ID: PathArtActionDefinition(
            art_id=ARIETE_ART_ID,
            character_class="sentinela",
            path_id="devastador",
            action=Action(
                ARIETE_ART_ID,
                "Aríete",
                Decimal("1.35"),
                cooldown=2,
                actor_per_bonus=Decimal(10),
            ),
        ),
        GOLPE_DE_RUPTURA_ART_ID: PathArtActionDefinition(
            art_id=GOLPE_DE_RUPTURA_ART_ID,
            character_class="sentinela",
            path_id="devastador",
            action=Action(
                GOLPE_DE_RUPTURA_ART_ID,
                "Golpe de Ruptura",
                Decimal("1.25"),
                cooldown=3,
                conditional_modifiers=(
                    ActionConditionalModifier(
                        "sentinela.golpe_de_ruptura.retaliation_power",
                        ActionCondition(
                            "class_resource_at_least",
                            resource="retaliation",
                        ),
                        "damage_power",
                        Decimal("0.20"),
                        operation="multiply",
                    ),
                ),
            ),
        ),
        CORTE_DE_EXECUCAO_ART_ID: PathArtActionDefinition(
            art_id=CORTE_DE_EXECUCAO_ART_ID,
            character_class="errante",
            path_id="carrasco",
            action=Action(
                CORTE_DE_EXECUCAO_ART_ID,
                "Corte de Execução",
                Decimal("1.35"),
                cooldown=3,
                conditional_modifiers=(
                    ActionConditionalModifier(
                        "errante.corte_de_execucao.low_hp_power",
                        ActionCondition(
                            "target_hp_fraction_at_most", threshold=Decimal("0.35")
                        ),
                        "damage_power",
                        Decimal("0.15"),
                        operation="multiply",
                    ),
                ),
            ),
        ),
        HEMORRAGIA_ART_ID: PathArtActionDefinition(
            art_id=HEMORRAGIA_ART_ID,
            character_class="errante",
            path_id="carrasco",
            action=Action(
                HEMORRAGIA_ART_ID,
                "Hemorragia",
                Decimal("0.95"),
                cooldown=3,
                native_dot_kind="bleed",
                native_dot_stacks=2,
            ),
        ),
        VENENO_VELADO_ART_ID: PathArtActionDefinition(
            art_id=VENENO_VELADO_ART_ID,
            character_class="errante",
            path_id="sabotador",
            action=Action(
                VENENO_VELADO_ART_ID,
                "Veneno Velado",
                Decimal("0.85"),
                cooldown=2,
                native_dot_kind="poison",
                native_dot_stacks=1,
            ),
        ),
        FIO_CORTADO_ART_ID: PathArtActionDefinition(
            art_id=FIO_CORTADO_ART_ID,
            character_class="errante",
            path_id="sabotador",
            action=Action(
                FIO_CORTADO_ART_ID,
                "Fio Cortado",
                Decimal("0.95"),
                attack_debuff=Decimal("0.12"),
                duration=2,
                cooldown=3,
                effect_stat="attack",
                effect_id=FIO_CORTADO_ART_ID,
            ),
        ),
        TIRO_PERFURANTE_ART_ID: PathArtActionDefinition(
            art_id=TIRO_PERFURANTE_ART_ID,
            character_class="vigia",
            path_id="atirador",
            action=Action(
                TIRO_PERFURANTE_ART_ID,
                "Tiro Perfurante",
                Decimal("1.30"),
                cooldown=2,
                actor_per_bonus=Decimal(10),
            ),
        ),
        FIXAR_ALVO_ART_ID: PathArtActionDefinition(
            art_id=FIXAR_ALVO_ART_ID,
            character_class="vigia",
            path_id="atirador",
            action=Action(
                FIXAR_ALVO_ART_ID,
                "Fixar Alvo",
                Decimal("1.00"),
                cooldown=3,
            ),
        ),
        FLECHA_SERRILHADA_ART_ID: PathArtActionDefinition(
            art_id=FLECHA_SERRILHADA_ART_ID,
            character_class="vigia",
            path_id="rastreador",
            action=Action(
                FLECHA_SERRILHADA_ART_ID,
                "Flecha Serrilhada",
                Decimal("0.90"),
                cooldown=2,
                native_dot_kind="bleed",
                native_dot_stacks=1,
            ),
        ),
        LACO_DE_CACA_ART_ID: PathArtActionDefinition(
            art_id=LACO_DE_CACA_ART_ID,
            character_class="vigia",
            path_id="rastreador",
            action=Action(
                LACO_DE_CACA_ART_ID,
                "Laço de Caça",
                Decimal("0.80"),
                attack_debuff=Decimal("0.20"),
                duration=2,
                cooldown=3,
                effect_stat="agility",
                effect_id=LACO_DE_CACA_ART_ID,
            ),
        ),
        ESTILHACO_DO_VEU_ART_ID: PathArtActionDefinition(
            art_id=ESTILHACO_DO_VEU_ART_ID,
            character_class="tecelao",
            path_id="conjurador",
            action=Action(
                ESTILHACO_DO_VEU_ART_ID,
                "Estilhaço do Véu",
                Decimal("1.40"),
                cooldown=2,
            ),
        ),
        INCENDIO_TRANCADO_ART_ID: PathArtActionDefinition(
            art_id=INCENDIO_TRANCADO_ART_ID,
            character_class="tecelao",
            path_id="conjurador",
            action=Action(
                INCENDIO_TRANCADO_ART_ID,
                "Incêndio Trançado",
                Decimal("0.75"),
                cooldown=3,
                target_mode="all_opponents",
                native_dot_kind="burn",
                native_dot_stacks=1,
            ),
        ),
        RUNA_DE_GUARDA_ART_ID: PathArtActionDefinition(
            art_id=RUNA_DE_GUARDA_ART_ID,
            character_class="tecelao",
            path_id="runico",
            action=Action(
                RUNA_DE_GUARDA_ART_ID,
                "Runa de Guarda",
                Decimal(0),
                cooldown=3,
                target_mode="ally",
                target_barrier_coefficient=Decimal("1.05"),
                target_barrier_duration=2,
            ),
        ),
        RUNA_DE_RUPTURA_ART_ID: PathArtActionDefinition(
            art_id=RUNA_DE_RUPTURA_ART_ID,
            character_class="tecelao",
            path_id="runico",
            action=Action(
                RUNA_DE_RUPTURA_ART_ID,
                "Runa de Ruptura",
                Decimal("0.90"),
                attack_debuff=Decimal("0.10"),
                duration=2,
                cooldown=3,
                effect_stat="defense",
                effect_id=RUNA_DE_RUPTURA_ART_ID,
            ),
        ),
        MAU_AGOURO_ART_ID: PathArtActionDefinition(
            art_id=MAU_AGOURO_ART_ID,
            character_class="oraculo",
            path_id="agoureiro",
            action=Action(
                MAU_AGOURO_ART_ID,
                "Mau Agouro",
                Decimal("0.95"),
                attack_debuff=Decimal("0.10"),
                duration=2,
                cooldown=2,
                effect_stat="attack",
                effect_id=MAU_AGOURO_ART_ID,
            ),
        ),
        DESTINO_LENTO_ART_ID: PathArtActionDefinition(
            art_id=DESTINO_LENTO_ART_ID,
            character_class="oraculo",
            path_id="agoureiro",
            action=Action(
                DESTINO_LENTO_ART_ID,
                "Destino Lento",
                Decimal("0.70"),
                attack_debuff=Decimal("0.18"),
                duration=2,
                cooldown=3,
                effect_stat="agility",
                effect_id=DESTINO_LENTO_ART_ID,
            ),
        ),
        LOBO_ART_ID: PathArtActionDefinition(
            art_id=LOBO_ART_ID,
            character_class="oraculo",
            path_id="invocador",
            action=Action(
                LOBO_ART_ID,
                "Lobo",
                Decimal("1.25"),
                cooldown=2,
                manifestation_kind="lobo",
            ),
        ),
        CORUJA_ART_ID: PathArtActionDefinition(
            art_id=CORUJA_ART_ID,
            character_class="oraculo",
            path_id="invocador",
            action=Action(
                CORUJA_ART_ID,
                "Coruja",
                Decimal("0.85"),
                attack_debuff=Decimal("0.15"),
                duration=2,
                cooldown=3,
                effect_stat="agility",
                effect_id=CORUJA_ART_ID,
                manifestation_kind="coruja",
            ),
        ),
        CURA_SOLAR_ART_ID: PathArtActionDefinition(
            art_id=CURA_SOLAR_ART_ID,
            character_class="luminar",
            path_id="guardiao",
            action=Action(
                CURA_SOLAR_ART_ID,
                "Cura Solar",
                Decimal(0),
                cooldown=2,
                target_mode="ally",
                heal_coefficient=Decimal("1.00"),
            ),
        ),
        EGIDE_COMPARTILHADA_ART_ID: PathArtActionDefinition(
            art_id=EGIDE_COMPARTILHADA_ART_ID,
            character_class="luminar",
            path_id="guardiao",
            action=Action(
                EGIDE_COMPARTILHADA_ART_ID,
                "Égide Compartilhada",
                Decimal(0),
                cooldown=4,
                target_mode="ally",
                target_barrier_coefficient=Decimal("0.90"),
                target_barrier_duration=2,
                self_barrier_coefficient=Decimal("0.45"),
                self_barrier_duration=2,
            ),
        ),
        LANCA_DE_LUZ_ART_ID: PathArtActionDefinition(
            art_id=LANCA_DE_LUZ_ART_ID,
            character_class="luminar",
            path_id="inquisidor",
            action=Action(
                LANCA_DE_LUZ_ART_ID,
                "Lança de Luz",
                Decimal("1.35"),
                cooldown=2,
            ),
        ),
        SELO_DA_PENITENCIA_ART_ID: PathArtActionDefinition(
            art_id=SELO_DA_PENITENCIA_ART_ID,
            character_class="luminar",
            path_id="inquisidor",
            action=Action(
                SELO_DA_PENITENCIA_ART_ID,
                "Selo da Penitência",
                Decimal("1.00"),
                attack_debuff=Decimal("0.20"),
                duration=2,
                cooldown=3,
                effect_stat="healing_received",
                effect_id=SELO_DA_PENITENCIA_ART_ID,
            ),
        ),
        CONTRA_GOLPE_ART_ID: PathArtActionDefinition(
            art_id=CONTRA_GOLPE_ART_ID,
            character_class="sentinela",
            path_id="bastiao",
            action=Action(
                CONTRA_GOLPE_ART_ID,
                "Contra-Golpe",
                Decimal("1.20"),
                duration=2,
                cooldown=3,
                effect_stat="attack",
                effect_id=CONTRA_GOLPE_ART_ID,
                conditional_modifiers=(
                    ActionConditionalModifier(
                        "sentinela.contra_golpe.retaliation_attack_debuff",
                        ActionCondition(
                            "class_resource_at_least", resource="retaliation"
                        ),
                        "attack_debuff",
                        Decimal("0.10"),
                    ),
                ),
            ),
        ),
        ABALO_ART_ID: PathArtActionDefinition(
            art_id=ABALO_ART_ID,
            character_class="sentinela",
            path_id="devastador",
            action=Action(
                ABALO_ART_ID,
                "Abalo",
                Decimal("0.90"),
                attack_debuff=Decimal("0.08"),
                duration=2,
                cooldown=4,
                effect_stat="defense",
                effect_id=ABALO_ART_ID,
                target_mode="all_opponents",
            ),
        ),
        MARCA_DA_MORTE_ART_ID: PathArtActionDefinition(
            art_id=MARCA_DA_MORTE_ART_ID,
            character_class="errante",
            path_id="carrasco",
            action=Action(
                MARCA_DA_MORTE_ART_ID,
                "Marca da Morte",
                Decimal("0.80"),
                cooldown=4,
                prepares_chain=CARRASCO_MARCA_DA_MORTE_CHAIN,
                prepares_chain_duration=2,
                chain_power_bonus_damage=Decimal("0.12"),
            ),
        ),
        TRAVA_DE_PASSOS_ART_ID: PathArtActionDefinition(
            art_id=TRAVA_DE_PASSOS_ART_ID,
            character_class="errante",
            path_id="sabotador",
            action=Action(
                TRAVA_DE_PASSOS_ART_ID,
                "Trava de Passos",
                Decimal("0.80"),
                attack_debuff=Decimal("0.18"),
                duration=2,
                cooldown=3,
                effect_stat="agility",
                effect_id=TRAVA_DE_PASSOS_ART_ID,
            ),
        ),
        RAJADA_CONTROLADA_ART_ID: PathArtActionDefinition(
            art_id=RAJADA_CONTROLADA_ART_ID,
            character_class="vigia",
            path_id="atirador",
            action=Action(
                RAJADA_CONTROLADA_ART_ID,
                "Rajada Controlada",
                Decimal("0.45"),
                hit_count=3,
                cooldown=3,
            ),
        ),
        CHUVA_DE_RASTROS_ART_ID: PathArtActionDefinition(
            art_id=CHUVA_DE_RASTROS_ART_ID,
            character_class="vigia",
            path_id="rastreador",
            action=Action(
                CHUVA_DE_RASTROS_ART_ID,
                "Chuva de Rastros",
                Decimal("0.70"),
                cooldown=4,
                target_mode="all_opponents",
            ),
        ),
        CONVERGENCIA_ARCANA_ART_ID: PathArtActionDefinition(
            art_id=CONVERGENCIA_ARCANA_ART_ID,
            character_class="tecelao",
            path_id="conjurador",
            action=Action(
                CONVERGENCIA_ARCANA_ART_ID,
                "Convergência Arcana",
                Decimal("0.50"),
                hit_count=3,
                cooldown=3,
            ),
        ),
        RUNA_DE_RETORNO_ART_ID: PathArtActionDefinition(
            art_id=RUNA_DE_RETORNO_ART_ID,
            character_class="tecelao",
            path_id="runico",
            action=Action(
                RUNA_DE_RETORNO_ART_ID,
                "Runa de Retorno",
                Decimal(0),
                cooldown=4,
                target_mode="ally",
                heal_coefficient=Decimal("0.70"),
                effect_removal=ActionEffectRemoval(
                    kind="purification",
                    count=1,
                    selection_required=False,
                ),
            ),
        ),
        CONDENACAO_ART_ID: PathArtActionDefinition(
            art_id=CONDENACAO_ART_ID,
            character_class="oraculo",
            path_id="agoureiro",
            action=Action(
                CONDENACAO_ART_ID,
                "Condenação",
                Decimal("0.80"),
                cooldown=4,
                prepares_chain=AGOUREIRO_CONDENACAO_CHAIN,
                prepares_chain_duration=2,
                chain_power_bonus_damage=Decimal("0.20"),
            ),
        ),
        URSO_ART_ID: PathArtActionDefinition(
            art_id=URSO_ART_ID,
            character_class="oraculo",
            path_id="invocador",
            action=Action(
                URSO_ART_ID,
                "Urso",
                Decimal(0),
                cooldown=3,
                target_mode="self",
                target_barrier_coefficient=Decimal("1.00"),
                target_barrier_duration=2,
                manifestation_kind="urso",
            ),
        ),
        PURGACAO_LUMINOSA_ART_ID: PathArtActionDefinition(
            art_id=PURGACAO_LUMINOSA_ART_ID,
            character_class="luminar",
            path_id="guardiao",
            action=Action(
                PURGACAO_LUMINOSA_ART_ID,
                "Purgação Luminosa",
                Decimal(0),
                cooldown=4,
                target_mode="ally",
                heal_coefficient=Decimal("0.65"),
                effect_removal=ActionEffectRemoval(
                    kind="purification",
                    count=1,
                    selection_required=False,
                ),
            ),
        ),
        PURGA_ARDENTE_ART_ID: PathArtActionDefinition(
            art_id=PURGA_ARDENTE_ART_ID,
            character_class="luminar",
            path_id="inquisidor",
            action=Action(
                PURGA_ARDENTE_ART_ID,
                "Purga Ardente",
                Decimal("1.20"),
                cooldown=4,
                effect_removal=ActionEffectRemoval(
                    kind="dispel",
                    count=1,
                    trigger="successful_direct_hit",
                    selection_required=False,
                ),
            ),
        ),
        ULTIMA_MURALHA_ART_ID: PathArtActionDefinition(
            art_id=ULTIMA_MURALHA_ART_ID,
            character_class="sentinela",
            path_id="bastiao",
            action=Action(
                ULTIMA_MURALHA_ART_ID,
                "Última Muralha",
                Decimal(0),
                cooldown=5,
                target_mode="all_allies",
                target_barrier_coefficient=Decimal("0.65"),
                target_barrier_duration=2,
            ),
        ),
        RUPTOR_ART_ID: PathArtActionDefinition(
            art_id=RUPTOR_ART_ID,
            character_class="sentinela",
            path_id="devastador",
            action=Action(
                RUPTOR_ART_ID,
                "Ruptor",
                Decimal("1.70"),
                cooldown=5,
                conditional_modifiers=(
                    ActionConditionalModifier(
                        "sentinela.ruptor.low_hp_power",
                        ActionCondition(
                            "actor_hp_fraction_below", threshold=Decimal("0.50")
                        ),
                        "damage_power",
                        Decimal("0.10"),
                        operation="multiply",
                        evaluation_scope="per_action",
                    ),
                ),
            ),
        ),
        CEIFA_ART_ID: PathArtActionDefinition(
            art_id=CEIFA_ART_ID,
            character_class="errante",
            path_id="carrasco",
            action=Action(
                CEIFA_ART_ID,
                "Ceifa",
                Decimal("1.65"),
                cooldown=5,
                conditional_modifiers=(
                    ActionConditionalModifier(
                        "errante.ceifa.target_low_hp_crit",
                        ActionCondition(
                            "target_hp_fraction_at_most", threshold=Decimal("0.40")
                        ),
                        "crit_bonus",
                        Decimal(10),
                    ),
                ),
            ),
        ),
        COLAPSO_PREPARADO_ART_ID: PathArtActionDefinition(
            art_id=COLAPSO_PREPARADO_ART_ID,
            character_class="errante",
            path_id="sabotador",
            action=Action(
                COLAPSO_PREPARADO_ART_ID,
                "Colapso Preparado",
                Decimal("1.20"),
                cooldown=5,
                conditional_modifiers=tuple(
                    ActionConditionalModifier(
                        f"errante.colapso_preparado.distinct_negative_{count}",
                        ActionCondition(
                            "target_distinct_normal_negative_effects_at_least",
                            minimum=count,
                        ),
                        "damage_power",
                        Decimal("0.10"),
                        operation="add",
                    )
                    for count in (1, 2, 3)
                ),
            ),
        ),
        DISPARO_TERMINAL_ART_ID: PathArtActionDefinition(
            art_id=DISPARO_TERMINAL_ART_ID,
            character_class="vigia",
            path_id="atirador",
            action=Action(
                DISPARO_TERMINAL_ART_ID,
                "Disparo Terminal",
                Decimal("1.75"),
                cooldown=5,
                resource_uses=(
                    ActionResourceUse(
                        resource="aim",
                        minimum=4,
                        consume=4,
                        consume_at="after_resolution",
                        target_selector="primary_target",
                        required=True,
                    ),
                ),
                conditional_modifiers=(
                    ActionConditionalModifier(
                        "vigia.disparo_terminal.four_aim_crit",
                        ActionCondition(
                            "class_resource_at_least",
                            resource="aim",
                            minimum=4,
                        ),
                        "crit_bonus",
                        Decimal(15),
                        target_scope="primary_target",
                        evaluation_scope="per_action",
                    ),
                ),
            ),
        ),
        PREDACAO_PERSISTENTE_ART_ID: PathArtActionDefinition(
            art_id=PREDACAO_PERSISTENTE_ART_ID,
            character_class="vigia",
            path_id="rastreador",
            action=Action(
                PREDACAO_PERSISTENTE_ART_ID,
                "Predação Persistente",
                Decimal("1.35"),
                cooldown=4,
                conditional_modifiers=tuple(
                    ActionConditionalModifier(
                        f"vigia.predacao_persistente.distinct_negative_{count}",
                        ActionCondition(
                            "target_distinct_normal_negative_effects_at_least",
                            minimum=count,
                        ),
                        "damage_power",
                        Decimal("0.08"),
                        operation="add",
                    )
                    for count in (1, 2)
                ),
            ),
        ),
        RASGO_CONJURADO_ART_ID: PathArtActionDefinition(
            art_id=RASGO_CONJURADO_ART_ID,
            character_class="tecelao",
            path_id="conjurador",
            action=Action(
                RASGO_CONJURADO_ART_ID,
                "Rasgo Conjurado",
                Decimal("1.25"),
                cooldown=5,
                target_mode="all_opponents",
            ),
        ),
        CIRCULO_RUNICO_ART_ID: PathArtActionDefinition(
            art_id=CIRCULO_RUNICO_ART_ID,
            character_class="tecelao",
            path_id="runico",
            action=Action(
                CIRCULO_RUNICO_ART_ID,
                "Círculo Rúnico",
                Decimal(0),
                cooldown=5,
                target_mode="all_allies",
                target_barrier_coefficient=Decimal("0.60"),
                target_barrier_duration=2,
            ),
        ),
    }
)


def path_player_actions(
    character_class: str,
    selected_path: str | None,
    art_ids: tuple[str, ...],
) -> dict[str, Action]:
    """Resolve only equipped, implemented Path Arts for the frozen Path."""
    if len(art_ids) > 3 or len(set(art_ids)) != len(art_ids):
        raise ValueError("Path Art configuration accepts at most three unique Arts.")
    actions: dict[str, Action] = {}
    for art_id in art_ids:
        definition = PATH_ART_ACTIONS.get(art_id)
        if (
            definition is None
            or definition.character_class != character_class
            or definition.path_id != selected_path
        ):
            raise ValueError("Unknown or ineligible Path Art in combat configuration.")
        actions[art_id] = definition.action
    return actions

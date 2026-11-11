"""Encontros of Crônica I: the cr01 creatures and where each one fights (proposal §11).

Kits are in ``SIMULAR``: the coefficients are the ones of §11.3 and §11.4 and still need
the Balanceamento pass. Attributes come from the published formula of GDD §49.6, with no
new multiplier. The two Chefes (chapters 4 and 8) use the boss profile, phases at 70% and
35% and, in Group, the Campaign boss scaling of GDD §51.5. Creatures and Elites never
scale with the Group (``pr_cr01_encontro_grupo``).

The creatures themselves live in ``domain/road.py`` with the rest of the catalog. Two
things the shared engine does not do today are left out on purpose: creature Defender
(Carregador Repetido) and custom telegraph lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from decimal import Decimal

from asterion.domain.chronicle_content import (
    ALTOS,
    CONFINS,
    NARETH,
    OCASO,
    REGIONS_BY_NAME,
    VALES,
    VARZEAS,
)
from asterion.domain.combat import Combat, CombatPhaseTrigger
from asterion.domain.road import (
    CR01_AGUARDA_RESPOSTA,
    CR01_CARREGADOR_REPETIDO,
    CR01_ESCRIBA_REPETIDO,
    CR01_GUARDA_REPETIDA,
    CR01_MARCADOR,
    CR01_MESTRE_DE_TURNO,
    CR01_MULTIDAO_REPETIDA,
    CR01_REPETIDOR,
    Creature,
    CreatureCombatantSpec,
    StatMultipliers,
)

D = Decimal

ENCOUNTER_SOURCE = "rep_cr01_encontro"
REGION_LEVEL_SPAN = 10  # Ocaso 1–10, Vales 11–20 … Confins 51–60 (§11.1.2).

# §11.2: the creatures are made of the matter of the Região de Ressonância.
REGION_MATTER: dict[str, str] = {
    OCASO: "fuligem compactada, cinza e lascas de pedra escurecida",
    VALES: "raízes finas trançadas, turfa e musgo úmido",
    NARETH: "poeira de marco, capim seco e lama rachada",
    VARZEAS: "lodo ferruginoso, crosta de sal e juncos",
    ALTOS: "cascalho de basalto, cinza mineral e fiapos de cabo",
    CONFINS: "névoa condensada e pedra pálida",
}

# Multi-hit count and the "skip while the same DEF reduction is active" rule are not
# part of the positional creature tuple, so they are applied on the built combat.
_HIT_COUNTS = {"golpe_repetido": 2, "muitas_maos": 3}
_DEFENSE_MARKS = {
    "marca_desvio": "cr01.marca_desvio",
    "rasura": "cr01.rasura",
    "pedido_repetido": "cr01.pedido_repetido",
}
# AoEs that the AI only uses with 2+ living targets (§11.3 Coro, §11.4).
_GROUP_ONLY = ("coro", "ordem_coletiva", "insistencia")
_PREFIX = re.compile(r"^e\d+_")

PHASE_I, PHASE_II, PHASE_III = "phase_i", "phase_ii", "phase_iii"
PHASE_II_AT, PHASE_III_AT = D("0.70"), D("0.35")
ADD_KEY = "add"
ADD_HP_FACTOR = D("0.50")  # Chamada: Threat 0,50 as half HP (author decision, 2026-11-10).
ESPERA_EVERY = 4  # "a cada 4ª oportunidade", counted from the entry in Phase II.


def _keys(combat: Combat) -> dict[str, str]:
    """Base action id -> actual key (multi-enemy combats prefix keys with ``eN_``)."""
    keys: dict[str, str] = {}
    for key in combat.enemy_actions:
        keys.setdefault(_PREFIX.sub("", key), key)
    return keys


def configure_encounter(combat: Combat) -> Combat:
    actions = combat.enemy_actions
    for key in list(actions):
        base = _PREFIX.sub("", key)
        if base in _HIT_COUNTS:
            actions[key] = replace(actions[key], hit_count=_HIT_COUNTS[base])
        if base in _DEFENSE_MARKS:
            effect_id = _DEFENSE_MARKS[base]
            actions[key] = replace(
                actions[key], effect_id=effect_id, skip_if_target_effect_active=effect_id
            )
        if base in _GROUP_ONLY:
            actions[key] = replace(actions[key], min_living_opponents=2)
    keys = _keys(combat)
    if "chamada" in keys:
        _configure_mestre(combat, keys)
    elif "espera" in keys:
        _configure_aguarda(combat, keys)
    return combat


def _gate(combat: Combat, key: str, *phases: str, **changes) -> None:
    combat.enemy_actions[key] = replace(combat.enemy_actions[key], phase_ids=phases, **changes)


def _configure_mestre(combat: Combat, keys: dict[str, str]) -> None:
    """Fase I Turno, Fase II Chamada (add + Ordem Coletiva), Fase III Fim de Turno."""
    combat.phase_id = PHASE_I
    combat.phase_triggers = (
        CombatPhaseTrigger("cr01.mestre.phase_ii", "enemy", PHASE_II_AT, phase_id=PHASE_II),
        CombatPhaseTrigger("cr01.mestre.phase_iii", "enemy", PHASE_III_AT, phase_id=PHASE_III),
    )
    _gate(
        combat,
        keys["chamada"],
        PHASE_II,
        PHASE_III,
        revive_fighter_keys=(ADD_KEY,),
        requires_defeated_fighter_keys=(ADD_KEY,),
        revive_hp_fraction=D(1),
    )
    _gate(combat, keys["ordem_coletiva"], PHASE_II, PHASE_III)
    _gate(combat, keys["fim_de_turno"], PHASE_III)
    add = combat.fighters.get(ADD_KEY)
    if add is not None:
        add.encounter_hidden = True


def _configure_aguarda(combat: Combat, keys: dict[str, str]) -> None:
    """Fase I Oferta, Fase II Espera (every 4th opportunity), Fase III Sem Resposta."""
    espera = keys["espera"]
    combat.phase_id = PHASE_I
    combat.phase_triggers = (
        CombatPhaseTrigger(
            "cr01.aguarda.phase_ii",
            "enemy",
            PHASE_II_AT,
            phase_id=PHASE_II,
            cooldown_action_ids=(espera,),
            cooldown_opportunities=ESPERA_EVERY,
        ),
        CombatPhaseTrigger("cr01.aguarda.phase_iii", "enemy", PHASE_III_AT, phase_id=PHASE_III),
    )
    _gate(
        combat,
        espera,
        PHASE_II,
        self_effect_stat="defense",
        self_effect_magnitude=D("0.12"),
        self_effect_duration=1,
        self_effect_id="cr01.espera",
        self_effect_kind="debuff",
    )
    _gate(combat, keys["insistencia"], PHASE_II, PHASE_III)
    _gate(combat, keys["confirmacao_exigida"], PHASE_III)


def enemy_specs(
    creature: Creature, level: int, roster_size: int = 1
) -> tuple[CreatureCombatantSpec, ...]:
    """The enemies of one Encontro. Only a Chefe scales with the Group (GDD §51.5)."""
    if creature.category != "boss":
        return (CreatureCombatantSpec(creature, level, "enemy"),)
    boss = CreatureCombatantSpec(creature, level, "enemy", campaign_boss_group_size=roster_size)
    if creature is not CR01_MESTRE_DE_TURNO:
        return (boss,)
    # Chamada: 1 minor add with the Repetidor kit, no Group scaling, optional to defeat.
    add = CreatureCombatantSpec(
        CR01_REPETIDOR,
        level,
        ADD_KEY,
        stat_multipliers=StatMultipliers(ADD_HP_FACTOR, D(1), D(1), D(1)),
        required_for_victory=False,
        initially_inactive=True,
    )
    return (boss, add)


@dataclass(frozen=True, slots=True)
class Encounter:
    encounter_id: str
    objective_id: str
    creature: Creature
    scene: str
    feat_id: str | None = None

    @property
    def chapter(self) -> int:
        return int(self.objective_id[4:6])

    @property
    def boss(self) -> bool:
        return self.creature.category == "boss"

    @property
    def content_id(self) -> str:
        return f"chronicle.{self.encounter_id}"

    @property
    def repeat_content_id(self) -> str:
        return f"{self.content_id}.eco"


ENCOUNTERS: tuple[Encounter, ...] = (
    Encounter(
        "enc_cr01_c01",
        "cap_01_obj_04",
        CR01_REPETIDOR,
        "Durante um pulso, a matéria do chão se ergue numa forma humana sem rosto que "
        "repete um gesto de trabalho. Você está no caminho do gesto.",
    ),
    Encounter(
        "enc_cr01_c02",
        "cap_02_obj_02",
        CR01_MARCADOR,
        "Uma silhueta fina aponta sempre para o mesmo lado, mesmo quando o corpo gira. "
        "Depois de um pulso, passa a apontar para você.",
    ),
    Encounter(
        "enc_cr01_c03",
        "cap_03_obj_04",
        CR01_GUARDA_REPETIDA,
        "Uma forma pesada assume a postura de um guarda antigo diante de um posto que "
        "não existe mais. Você entrou nele.",
    ),
    Encounter(
        "enc_cr01_c04",
        "cap_04_obj_04",
        CR01_MESTRE_DE_TURNO,
        "No pulso mais longo até agora, uma forma grande ergue o braço num gesto de ordem, "
        "e formas menores se montam ao redor para obedecer. Ela dá ordens a quem já não "
        "está aqui, e eles ainda obedecem.",
        "feito_cr01_mestre_de_turno",
    ),
    Encounter(
        "enc_cr01_c05",
        "cap_05_obj_03",
        CR01_CARREGADOR_REPETIDO,
        "Uma forma curvada carrega há muito tempo algo que ninguém vê. No pulso, ela "
        "larga a carga em cima de você.",
    ),
    Encounter(
        "enc_cr01_c06",
        "cap_06_obj_04",
        CR01_MULTIDAO_REPETIDA,
        "Formas humanas fundidas ombro a ombro, cada uma repetindo um gesto diferente. "
        "No pulso, todas as bocas que não têm se abrem ao mesmo tempo.",
        "feito_cr01_multidao",
    ),
    Encounter(
        "enc_cr01_c07",
        "cap_07_obj_03",
        CR01_ESCRIBA_REPETIDO,
        "Uma figura curvada sobre uma prancha que não existe risca o ar com dedos longos "
        "demais. Cada traço deixa a mesma palavra incompleta em quem estiver perto.",
        "feito_cr01_escriba",
    ),
    Encounter(
        "enc_cr01_c08",
        "cap_08_obj_04",
        CR01_AGUARDA_RESPOSTA,
        "No pulso mais forte de todos, uma figura imensa se monta ajoelhada, oferecendo com "
        "os dois braços uma placa lisa a quem chega. Quando ninguém a pega, ela se levanta.",
        "feito_cr01_aguarda_resposta",
    ),
)
ENCOUNTERS_BY_OBJECTIVE: dict[str, Encounter] = {item.objective_id: item for item in ENCOUNTERS}
ENCOUNTERS_BY_CONTENT: dict[str, Encounter] = {
    content_id: item
    for item in ENCOUNTERS
    for content_id in (item.content_id, item.repeat_content_id)
}
CHRONICLE_CREATURES: dict[str, Creature] = {
    item.creature.creature_id: item.creature for item in ENCOUNTERS
}
FEAT_NAMES: dict[str, str] = {
    "feito_cr01_multidao": "Primeira vitória sobre a Multidão Repetida",
    "feito_cr01_escriba": "Primeira vitória sobre o Escriba Repetido",
    "feito_cr01_mestre_de_turno": "Fim de Turno",
    "feito_cr01_aguarda_resposta": "Sem Resposta",
}


def encounter_level(character_level: int, region_name: str) -> int:
    """The character's level, held inside the band of the Região de Ressonância."""
    low = REGIONS_BY_NAME[region_name].min_level
    return max(low, min(character_level, low + REGION_LEVEL_SPAN - 1))


def scene_text(encounter: Encounter, region_name: str) -> str:
    return f"{encounter.scene} A forma é feita de {REGION_MATTER[region_name]}."

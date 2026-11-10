"""Encontros of Crônica I: the cr01 creatures and where each one fights (proposal §11).

Kits are in ``SIMULAR``: the coefficients are the ones of §11.3 and still need the
Balanceamento pass. Attributes come from the published formula of GDD §49.6, with no
new multiplier. The two Chefes (chapters 4 and 8) are not here yet.

The creatures themselves live in ``domain/road.py`` with the rest of the catalog. Two
things the shared engine does not do today are left out on purpose: creature Defender
(Carregador Repetido) and custom telegraph lines.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from asterion.domain.chronicle_content import (
    ALTOS,
    CONFINS,
    NARETH,
    OCASO,
    REGIONS_BY_NAME,
    VALES,
    VARZEAS,
)
from asterion.domain.combat import Combat
from asterion.domain.road import (
    CR01_CARREGADOR_REPETIDO,
    CR01_ESCRIBA_REPETIDO,
    CR01_GUARDA_REPETIDA,
    CR01_MARCADOR,
    CR01_MULTIDAO_REPETIDA,
    CR01_REPETIDOR,
    Creature,
)

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
_DEFENSE_MARKS = {"marca_desvio": "cr01.marca_desvio", "rasura": "cr01.rasura"}


def configure_encounter(combat: Combat) -> Combat:
    actions = combat.enemy_actions
    for key, hits in _HIT_COUNTS.items():
        if key in actions:
            actions[key] = replace(actions[key], hit_count=hits)
    for key, effect_id in _DEFENSE_MARKS.items():
        if key in actions:
            actions[key] = replace(
                actions[key], effect_id=effect_id, skip_if_target_effect_active=effect_id
            )
    return combat


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
}


def encounter_level(character_level: int, region_name: str) -> int:
    """The character's level, held inside the band of the Região de Ressonância."""
    low = REGIONS_BY_NAME[region_name].min_level
    return max(low, min(character_level, low + REGION_LEVEL_SPAN - 1))


def scene_text(encounter: Encounter, region_name: str) -> str:
    return f"{encounter.scene} A forma é feita de {REGION_MATTER[region_name]}."

"""Canonical active-Art identities that are implemented by the current runtime."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActiveArtDefinition:
    art_id: str
    character_class: str
    min_level: int
    path_id: str | None = None

    def __post_init__(self) -> None:
        if not self.art_id or len(self.art_id) > 96:
            raise ValueError("Active Arts require a stable id.")
        if self.min_level < 1:
            raise ValueError("Active Art minimum level must be positive.")


FIRST_CLASS_ART_IDS = {
    "sentinela": "class_art.sentinela.golpe_de_guarda",
    "errante": "class_art.errante.corte_veloz",
    "vigia": "class_art.vigia.disparo_preciso",
    "tecelao": "class_art.tecelao.fio_cortante",
    "oraculo": "class_art.oraculo.sinal_funesto",
    "luminar": "class_art.luminar.fulgor",
}

SENTINEL_ART_IDS = {
    "golpe_de_guarda": FIRST_CLASS_ART_IDS["sentinela"],
    "quebra_postura": "class_art.sentinela.quebra_postura",
    "muralha_breve": "class_art.sentinela.muralha_breve",
    "impacto_resoluto": "class_art.sentinela.impacto_resoluto",
}

SENTINEL_ART_LEVELS = {
    SENTINEL_ART_IDS["golpe_de_guarda"]: 1,
    SENTINEL_ART_IDS["quebra_postura"]: 4,
    SENTINEL_ART_IDS["muralha_breve"]: 7,
    SENTINEL_ART_IDS["impacto_resoluto"]: 9,
}

ERRANTE_ART_IDS = {
    "corte_veloz": FIRST_CLASS_ART_IDS["errante"],
    "ferida_profunda": "class_art.errante.ferida_profunda",
    "passo_velado": "class_art.errante.passo_velado",
    "golpe_oportuno": "class_art.errante.golpe_oportuno",
}

ERRANTE_ART_LEVELS = {
    ERRANTE_ART_IDS["corte_veloz"]: 1,
    ERRANTE_ART_IDS["ferida_profunda"]: 4,
    ERRANTE_ART_IDS["passo_velado"]: 7,
    ERRANTE_ART_IDS["golpe_oportuno"]: 9,
}


ACTIVE_ART_DEFINITIONS = {
    art_id: ActiveArtDefinition(art_id, character_class, 1)
    for character_class, art_id in FIRST_CLASS_ART_IDS.items()
}
ACTIVE_ART_DEFINITIONS.update(
    {
        art_id: ActiveArtDefinition(art_id, "sentinela", min_level)
        for art_id, min_level in SENTINEL_ART_LEVELS.items()
    }
)
ACTIVE_ART_DEFINITIONS.update(
    {
        art_id: ActiveArtDefinition(art_id, "errante", min_level)
        for art_id, min_level in ERRANTE_ART_LEVELS.items()
    }
)


def active_art_definition(art_id: str) -> ActiveArtDefinition | None:
    """Return a runtime-backed Art definition; unknown/unimplemented Arts are not equipable."""
    return ACTIVE_ART_DEFINITIONS.get(art_id)

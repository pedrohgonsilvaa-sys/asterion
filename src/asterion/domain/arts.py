"""Canonical active-Art identities that are implemented by the current runtime."""

from dataclasses import dataclass, replace

from asterion.domain.weapon_metadata import VALID_COMPATIBILITY_TAGS


@dataclass(frozen=True, slots=True)
class ActiveArtDefinition:
    art_id: str
    character_class: str
    min_level: int
    path_id: str | None = None
    weapon_requirement: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.art_id or len(self.art_id) > 96:
            raise ValueError("Active Arts require a stable id.")
        if self.min_level < 1:
            raise ValueError("Active Art minimum level must be positive.")
        if not self.weapon_requirement <= VALID_COMPATIBILITY_TAGS:
            raise ValueError("Active Art weapon requirement contains an unknown tag.")


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
    "firmeza": "class_art.sentinela.firmeza",
    "golpe_de_rechaco": "class_art.sentinela.golpe_de_rechaco",
}

SENTINEL_ART_LEVELS = {
    SENTINEL_ART_IDS["golpe_de_guarda"]: 1,
    SENTINEL_ART_IDS["quebra_postura"]: 4,
    SENTINEL_ART_IDS["muralha_breve"]: 7,
    SENTINEL_ART_IDS["impacto_resoluto"]: 9,
    SENTINEL_ART_IDS["firmeza"]: 18,
    SENTINEL_ART_IDS["golpe_de_rechaco"]: 34,
}

ERRANTE_ART_IDS = {
    "corte_veloz": FIRST_CLASS_ART_IDS["errante"],
    "ferida_profunda": "class_art.errante.ferida_profunda",
    "passo_velado": "class_art.errante.passo_velado",
    "golpe_oportuno": "class_art.errante.golpe_oportuno",
    "corte_duplo": "class_art.errante.corte_duplo",
    "brecha_mortal": "class_art.errante.brecha_mortal",
}

ERRANTE_ART_LEVELS = {
    ERRANTE_ART_IDS["corte_veloz"]: 1,
    ERRANTE_ART_IDS["ferida_profunda"]: 4,
    ERRANTE_ART_IDS["passo_velado"]: 7,
    ERRANTE_ART_IDS["golpe_oportuno"]: 9,
    ERRANTE_ART_IDS["corte_duplo"]: 18,
    ERRANTE_ART_IDS["brecha_mortal"]: 34,
}

VIGIA_ART_IDS = {
    "disparo_preciso": FIRST_CLASS_ART_IDS["vigia"],
    "marca_da_presa": "class_art.vigia.marca_da_presa",
    "saraivada": "class_art.vigia.saraivada",
    "olho_da_vigilia": "class_art.vigia.olho_da_vigilia",
    "tiro_calculado": "class_art.vigia.tiro_calculado",
    "voleio": "class_art.vigia.voleio",
}

VIGIA_ART_LEVELS = {
    VIGIA_ART_IDS["disparo_preciso"]: 1,
    VIGIA_ART_IDS["marca_da_presa"]: 4,
    VIGIA_ART_IDS["saraivada"]: 7,
    VIGIA_ART_IDS["olho_da_vigilia"]: 9,
    VIGIA_ART_IDS["tiro_calculado"]: 18,
    VIGIA_ART_IDS["voleio"]: 34,
}

TECELAO_ART_IDS = {
    "fio_cortante": FIRST_CLASS_ART_IDS["tecelao"],
    "chama_tecida": "class_art.tecelao.chama_tecida",
    "ruptura_da_trama": "class_art.tecelao.ruptura_da_trama",
    "veu_entrelacado": "class_art.tecelao.veu_entrelacado",
    "geada_tecida": "class_art.tecelao.geada_tecida",
    "surto_do_veu": "class_art.tecelao.surto_do_veu",
}

TECELAO_ART_LEVELS = {
    TECELAO_ART_IDS["fio_cortante"]: 1,
    TECELAO_ART_IDS["chama_tecida"]: 4,
    TECELAO_ART_IDS["ruptura_da_trama"]: 7,
    TECELAO_ART_IDS["veu_entrelacado"]: 9,
    TECELAO_ART_IDS["geada_tecida"]: 18,
    TECELAO_ART_IDS["surto_do_veu"]: 34,
}

ORACULO_ART_IDS = {
    "sinal_funesto": FIRST_CLASS_ART_IDS["oraculo"],
    "vislumbre": "class_art.oraculo.vislumbre",
    "ruina_predita": "class_art.oraculo.ruina_predita",
    "veu_premonitorio": "class_art.oraculo.veu_premonitorio",
    "augurio_favoravel": "class_art.oraculo.augurio_favoravel",
    "selo_da_queda": "class_art.oraculo.selo_da_queda",
}

ORACULO_ART_LEVELS = {
    ORACULO_ART_IDS["sinal_funesto"]: 1,
    ORACULO_ART_IDS["vislumbre"]: 4,
    ORACULO_ART_IDS["ruina_predita"]: 7,
    ORACULO_ART_IDS["veu_premonitorio"]: 9,
    ORACULO_ART_IDS["augurio_favoravel"]: 18,
    ORACULO_ART_IDS["selo_da_queda"]: 34,
}

LUMINAR_ART_IDS = {
    "fulgor": FIRST_CLASS_ART_IDS["luminar"],
    "renovacao": "class_art.luminar.renovacao",
    "egide_solar": "class_art.luminar.egide_solar",
    "julgamento": "class_art.luminar.julgamento",
    "luz_restauradora": "class_art.luminar.luz_restauradora",
    "explosao_solar": "class_art.luminar.explosao_solar",
}

LUMINAR_ART_LEVELS = {
    LUMINAR_ART_IDS["fulgor"]: 1,
    LUMINAR_ART_IDS["renovacao"]: 4,
    LUMINAR_ART_IDS["egide_solar"]: 7,
    LUMINAR_ART_IDS["julgamento"]: 9,
    LUMINAR_ART_IDS["luz_restauradora"]: 18,
    LUMINAR_ART_IDS["explosao_solar"]: 34,
}

# Path Arts are registered only when the shared combat runtime can execute them.
# Future canonical Arts remain absent until their actions are implemented.
DEVASTADOR_ART_IDS = {
    "ariete": "path_art.sentinela.devastador.ariete",
    "golpe_de_ruptura": "path_art.sentinela.devastador.golpe_de_ruptura",
}

BASTIAO_ART_IDS = {
    "escudo_de_cinzas": "path_art.sentinela.bastiao.escudo_de_cinzas",
    "interpor": "path_art.sentinela.bastiao.interpor",
}

CARRASCO_ART_IDS = {
    "corte_de_execucao": "path_art.errante.carrasco.corte_de_execucao",
    "hemorragia": "path_art.errante.carrasco.hemorragia",
}

SABOTADOR_ART_IDS = {
    "veneno_velado": "path_art.errante.sabotador.veneno_velado",
    "fio_cortado": "path_art.errante.sabotador.fio_cortado",
}

ATIRADOR_ART_IDS = {
    "tiro_perfurante": "path_art.vigia.atirador.tiro_perfurante",
    "fixar_alvo": "path_art.vigia.atirador.fixar_alvo",
}

RASTREADOR_ART_IDS = {
    "flecha_serrilhada": "path_art.vigia.rastreador.flecha_serrilhada",
    "laco_de_caca": "path_art.vigia.rastreador.laco_de_caca",
}

CONJURADOR_ART_IDS = {
    "estilhaco_do_veu": "path_art.tecelao.conjurador.estilhaco_do_veu",
    "incendio_trancado": "path_art.tecelao.conjurador.incendio_trancado",
}

RUNICO_ART_IDS = {
    "runa_de_guarda": "path_art.tecelao.runico.runa_de_guarda",
    "runa_de_ruptura": "path_art.tecelao.runico.runa_de_ruptura",
}

AGOUREIRO_ART_IDS = {
    "mau_agouro": "path_art.oraculo.agoureiro.mau_agouro",
}

INVOCADOR_ART_IDS = {
    "lobo": "path_art.oraculo.invocador.lobo",
}

GUARDIAO_ART_IDS = {
    "cura_solar": "path_art.luminar.guardiao.cura_solar",
}

INQUISIDOR_ART_IDS = {
    "lanca_de_luz": "path_art.luminar.inquisidor.lanca_de_luz",
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
        DEVASTADOR_ART_IDS["ariete"]: ActiveArtDefinition(
            DEVASTADOR_ART_IDS["ariete"],
            "sentinela",
            12,
            path_id="devastador",
            weapon_requirement=frozenset({"weapon.compat.melee"}),
        )
    }
)

ART_IDS_BY_CLASS = {
    "sentinela": tuple(SENTINEL_ART_IDS.values()),
    "errante": tuple(ERRANTE_ART_IDS.values()),
    "vigia": tuple(VIGIA_ART_IDS.values()),
    "tecelao": tuple(TECELAO_ART_IDS.values()),
    "oraculo": tuple(ORACULO_ART_IDS.values()),
    "luminar": tuple(LUMINAR_ART_IDS.values()),
}
PATH_ART_IDS_BY_PATH = {
    "bastiao": tuple(BASTIAO_ART_IDS.values()),
    "devastador": tuple(DEVASTADOR_ART_IDS.values()),
    "carrasco": tuple(CARRASCO_ART_IDS.values()),
    "sabotador": tuple(SABOTADOR_ART_IDS.values()),
    "atirador": tuple(ATIRADOR_ART_IDS.values()),
    "rastreador": tuple(RASTREADOR_ART_IDS.values()),
    "conjurador": tuple(CONJURADOR_ART_IDS.values()),
    "runico": tuple(RUNICO_ART_IDS.values()),
    "agoureiro": tuple(AGOUREIRO_ART_IDS.values()),
    "invocador": tuple(INVOCADOR_ART_IDS.values()),
    "guardiao": tuple(GUARDIAO_ART_IDS.values()),
    "inquisidor": tuple(INQUISIDOR_ART_IDS.values()),
}
PATH_ART_IDS_BY_CLASS = {
    "sentinela": (*BASTIAO_ART_IDS.values(), *DEVASTADOR_ART_IDS.values()),
    "errante": (*CARRASCO_ART_IDS.values(), *SABOTADOR_ART_IDS.values()),
    "vigia": (*ATIRADOR_ART_IDS.values(), *RASTREADOR_ART_IDS.values()),
    "tecelao": (*CONJURADOR_ART_IDS.values(), *RUNICO_ART_IDS.values()),
    "oraculo": (*AGOUREIRO_ART_IDS.values(), *INVOCADOR_ART_IDS.values()),
    "luminar": (*GUARDIAO_ART_IDS.values(), *INQUISIDOR_ART_IDS.values()),
}
ACTIVE_ART_IDS_BY_CLASS = {
    character_class: tuple(
        (*class_art_ids, *PATH_ART_IDS_BY_CLASS.get(character_class, ()))
    )
    for character_class, class_art_ids in ART_IDS_BY_CLASS.items()
}
ACTIVE_ART_DEFINITIONS.update(
    {
        art_id: ActiveArtDefinition(art_id, "oraculo", min_level)
        for art_id, min_level in ORACULO_ART_LEVELS.items()
    }
)
ACTIVE_ART_DEFINITIONS.update(
    {
        art_id: ActiveArtDefinition(art_id, "luminar", min_level)
        for art_id, min_level in LUMINAR_ART_LEVELS.items()
    }
)
ACTIVE_ART_DEFINITIONS.update(
    {
        art_id: ActiveArtDefinition(art_id, "vigia", min_level)
        for art_id, min_level in VIGIA_ART_LEVELS.items()
    }
)
ACTIVE_ART_DEFINITIONS.update(
    {
        art_id: ActiveArtDefinition(art_id, "tecelao", min_level)
        for art_id, min_level in TECELAO_ART_LEVELS.items()
    }
)
ACTIVE_ART_DEFINITIONS.update(
    {
        art_id: ActiveArtDefinition(art_id, "errante", min_level)
        for art_id, min_level in ERRANTE_ART_LEVELS.items()
    }
)

ACTIVE_ART_DEFINITIONS.update(
    {
        BASTIAO_ART_IDS["escudo_de_cinzas"]: ActiveArtDefinition(
            BASTIAO_ART_IDS["escudo_de_cinzas"], "sentinela", 12, path_id="bastiao"
        ),
        CARRASCO_ART_IDS["corte_de_execucao"]: ActiveArtDefinition(
            CARRASCO_ART_IDS["corte_de_execucao"],
            "errante",
            12,
            path_id="carrasco",
            weapon_requirement=frozenset({"weapon.compat.melee"}),
        ),
        SABOTADOR_ART_IDS["veneno_velado"]: ActiveArtDefinition(
            SABOTADOR_ART_IDS["veneno_velado"],
            "errante",
            12,
            path_id="sabotador",
            weapon_requirement=frozenset({"weapon.compat.melee"}),
        ),
        ATIRADOR_ART_IDS["tiro_perfurante"]: ActiveArtDefinition(
            ATIRADOR_ART_IDS["tiro_perfurante"],
            "vigia",
            12,
            path_id="atirador",
            weapon_requirement=frozenset(
                {"weapon.compat.bow", "weapon.compat.crossbow"}
            ),
        ),
        RASTREADOR_ART_IDS["flecha_serrilhada"]: ActiveArtDefinition(
            RASTREADOR_ART_IDS["flecha_serrilhada"],
            "vigia",
            12,
            path_id="rastreador",
            weapon_requirement=frozenset(
                {"weapon.compat.bow", "weapon.compat.crossbow"}
            ),
        ),
        CONJURADOR_ART_IDS["estilhaco_do_veu"]: ActiveArtDefinition(
            CONJURADOR_ART_IDS["estilhaco_do_veu"],
            "tecelao",
            12,
            path_id="conjurador",
        ),
        RUNICO_ART_IDS["runa_de_guarda"]: ActiveArtDefinition(
            RUNICO_ART_IDS["runa_de_guarda"],
            "tecelao",
            12,
            path_id="runico",
        ),
        ATIRADOR_ART_IDS["fixar_alvo"]: ActiveArtDefinition(
            ATIRADOR_ART_IDS["fixar_alvo"],
            "vigia",
            22,
            path_id="atirador",
            weapon_requirement=frozenset(
                {"weapon.compat.bow", "weapon.compat.crossbow"}
            ),
        ),
        RASTREADOR_ART_IDS["laco_de_caca"]: ActiveArtDefinition(
            RASTREADOR_ART_IDS["laco_de_caca"],
            "vigia",
            22,
            path_id="rastreador",
            weapon_requirement=frozenset(
                {"weapon.compat.bow", "weapon.compat.crossbow"}
            ),
        ),
        CONJURADOR_ART_IDS["incendio_trancado"]: ActiveArtDefinition(
            CONJURADOR_ART_IDS["incendio_trancado"],
            "tecelao",
            22,
            path_id="conjurador",
        ),
        RUNICO_ART_IDS["runa_de_ruptura"]: ActiveArtDefinition(
            RUNICO_ART_IDS["runa_de_ruptura"],
            "tecelao",
            22,
            path_id="runico",
        ),
        AGOUREIRO_ART_IDS["mau_agouro"]: ActiveArtDefinition(
            AGOUREIRO_ART_IDS["mau_agouro"],
            "oraculo",
            12,
            path_id="agoureiro",
        ),
        INVOCADOR_ART_IDS["lobo"]: ActiveArtDefinition(
            INVOCADOR_ART_IDS["lobo"],
            "oraculo",
            12,
            path_id="invocador",
        ),
        GUARDIAO_ART_IDS["cura_solar"]: ActiveArtDefinition(
            GUARDIAO_ART_IDS["cura_solar"],
            "luminar",
            12,
            path_id="guardiao",
        ),
        INQUISIDOR_ART_IDS["lanca_de_luz"]: ActiveArtDefinition(
            INQUISIDOR_ART_IDS["lanca_de_luz"],
            "luminar",
            12,
            path_id="inquisidor",
        ),
    }
)

ACTIVE_ART_DEFINITIONS.update(
    {
        BASTIAO_ART_IDS["interpor"]: ActiveArtDefinition(
            BASTIAO_ART_IDS["interpor"], "sentinela", 22, path_id="bastiao"
        ),
        DEVASTADOR_ART_IDS["golpe_de_ruptura"]: ActiveArtDefinition(
            DEVASTADOR_ART_IDS["golpe_de_ruptura"],
            "sentinela",
            22,
            path_id="devastador",
            weapon_requirement=frozenset({"weapon.compat.melee"}),
        ),
        CARRASCO_ART_IDS["hemorragia"]: ActiveArtDefinition(
            CARRASCO_ART_IDS["hemorragia"],
            "errante",
            22,
            path_id="carrasco",
            weapon_requirement=frozenset({"weapon.compat.melee"}),
        ),
        SABOTADOR_ART_IDS["fio_cortado"]: ActiveArtDefinition(
            SABOTADOR_ART_IDS["fio_cortado"],
            "errante",
            22,
            path_id="sabotador",
            weapon_requirement=frozenset({"weapon.compat.melee"}),
        ),
    }
)

ART_WEAPON_REQUIREMENTS = {
    SENTINEL_ART_IDS["golpe_de_guarda"]: frozenset({"weapon.compat.melee"}),
    SENTINEL_ART_IDS["quebra_postura"]: frozenset({"weapon.compat.melee"}),
    SENTINEL_ART_IDS["impacto_resoluto"]: frozenset({"weapon.compat.melee"}),
    SENTINEL_ART_IDS["golpe_de_rechaco"]: frozenset({"weapon.compat.melee"}),
    ERRANTE_ART_IDS["corte_veloz"]: frozenset({"weapon.compat.melee"}),
    ERRANTE_ART_IDS["ferida_profunda"]: frozenset({"weapon.compat.melee"}),
    ERRANTE_ART_IDS["golpe_oportuno"]: frozenset({"weapon.compat.melee"}),
    ERRANTE_ART_IDS["corte_duplo"]: frozenset({"weapon.compat.melee"}),
    ERRANTE_ART_IDS["brecha_mortal"]: frozenset({"weapon.compat.melee"}),
    VIGIA_ART_IDS["disparo_preciso"]: frozenset({"weapon.compat.bow", "weapon.compat.crossbow"}),
    VIGIA_ART_IDS["marca_da_presa"]: frozenset({"weapon.compat.bow", "weapon.compat.crossbow"}),
    VIGIA_ART_IDS["saraivada"]: frozenset({"weapon.compat.bow", "weapon.compat.crossbow"}),
    VIGIA_ART_IDS["tiro_calculado"]: frozenset({"weapon.compat.bow", "weapon.compat.crossbow"}),
    VIGIA_ART_IDS["voleio"]: frozenset({"weapon.compat.bow", "weapon.compat.crossbow"}),
}
for _art_id, _weapon_requirement in ART_WEAPON_REQUIREMENTS.items():
    ACTIVE_ART_DEFINITIONS[_art_id] = replace(
        ACTIVE_ART_DEFINITIONS[_art_id],
        weapon_requirement=_weapon_requirement,
    )


def weapon_requirement_satisfied(
    definition: ActiveArtDefinition, equipped_tags: frozenset[str]
) -> bool:
    """Evaluate the Art's explicit tag requirement; empty means NONE."""
    return not definition.weapon_requirement or bool(
        definition.weapon_requirement & equipped_tags
    )


def weapon_requirement_label(definition: ActiveArtDefinition) -> str:
    """Return the approved player-facing wording for current Art requirements."""
    if not definition.weapon_requirement:
        return "Nenhum"
    if definition.weapon_requirement == frozenset({"weapon.compat.melee"}):
        return "Arma corpo a corpo compatível"
    if definition.weapon_requirement == frozenset(
        {"weapon.compat.bow", "weapon.compat.crossbow"}
    ):
        return "Arco ou Besta compatível"
    return "Arma compatível"



def active_art_definition(art_id: str) -> ActiveArtDefinition | None:
    """Return a runtime-backed Art definition; unknown/unimplemented Arts are not equipable."""
    return ACTIVE_ART_DEFINITIONS.get(art_id)

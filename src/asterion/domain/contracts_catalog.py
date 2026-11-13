# ruff: noqa: E501
"""Catalogo inicial dos Contratos Regionais (Documento B §36). Sem numeros de jogo."""

from __future__ import annotations

from dataclasses import dataclass

from asterion.domain.contracts_config import REGION_CODES, REWARD_PROFILES

TYPE_LABEL = {
    "CACA": "Caça",
    "COLETA": "Coleta",
    "ENTREGA": "Entrega",
    "INVESTIGACAO": "Investigação",
    "ESCOLTA": "Escolta",
}


@dataclass(frozen=True, slots=True)
class ContractDefinition:
    definition_id: str
    name: str
    contract_type: str
    region: str  # R1..R6
    description: str
    material_id: str | None = None  # so Coleta

    @property
    def reward_profile(self) -> str:
        return f"REWARD_{self.region}_{self.contract_type}"


def _d(i, name, kind, region, desc, material=None):
    return ContractDefinition(i, name, kind, region, desc, material)


_TDO = "material.tdo."
_VDE = "material.vde."
_NAR = "material.nareth."
_VAR = "material.varzeas."
_ALT = "material.altos."
_CDV = "material.confins."

CATALOG: tuple[ContractDefinition, ...] = (
    _d(
        "CON_TDO_01",
        "Cinza na Estrada",
        "CACA",
        "R1",
        "Uma ameaça voltou a aparecer nas rotas próximas. Elimine o alvo registrado no contrato e confirme a conclusão.",
    ),
    _d(
        "CON_TDO_02",
        "Ferro da Estrada",
        "COLETA",
        "R1",
        "Restos metálicos ainda podem ser recuperados nas áreas de passagem. Reúna o Material solicitado.",
        _TDO + "ferro_de_fuligem",
    ),
    _d(
        "CON_TDO_03",
        "Couro Escoriado",
        "COLETA",
        "R1",
        "Couro aproveitável ainda aparece entre os restos deixados pelas ameaças da estrada. Reúna o material solicitado.",
        _TDO + "couro_escoriado",
    ),
    _d(
        "CON_TDO_04",
        "Entrega do Refúgio",
        "ENTREGA",
        "R1",
        "Um carregamento precisa chegar ao destino sem ser perdido pelo caminho. Leve a entrega até o ponto indicado.",
    ),
    _d(
        "CON_TDO_05",
        "Sinais Recentes",
        "INVESTIGACAO",
        "R1",
        "Há sinais recentes na estrada. Examine o ponto indicado e registre a ocorrência.",
    ),
    _d(
        "CON_TDO_06",
        "Cinzas sem Resposta",
        "INVESTIGACAO",
        "R1",
        "Uma ocorrência estranha foi observada na região. Verifique o local e confirme o que pode ser registrado.",
    ),
    _d(
        "CON_VEN_01",
        "Ameaça nos Vales",
        "CACA",
        "R2",
        "Uma ameaça está interferindo nas rotas dos Vales. Elimine o alvo registrado no contrato.",
    ),
    _d(
        "CON_VEN_02",
        "Ferro Enredado",
        "COLETA",
        "R2",
        "Fragmentos de metal podem ser recuperados entre raízes e estruturas antigas. Reúna o material solicitado.",
        _VDE + "ferro_enredado",
    ),
    _d(
        "CON_VEN_03",
        "Couro Musgoso",
        "COLETA",
        "R2",
        "Materiais aproveitáveis aparecem em áreas úmidas dos Vales. Reúna o recurso indicado no contrato.",
        _VDE + "couro_musgoso",
    ),
    _d(
        "CON_VEN_04",
        "Entrega do Vale",
        "ENTREGA",
        "R2",
        "Um carregamento precisa atravessar uma rota dos Vales. Leve a entrega até o destino indicado.",
    ),
    _d(
        "CON_VEN_05",
        "Erva de Turfa",
        "COLETA",
        "R2",
        "Uma erva específica pode ser encontrada em áreas de turfa. Reúna o recurso solicitado.",
        _VDE + "erva_de_turfa",
    ),
    _d(
        "CON_VEN_06",
        "Resina Enredada",
        "COLETA",
        "R2",
        "Resina pode ser extraída de pontos adequados da região. Reúna o Material solicitado antes de concluir o contrato.",
        _VDE + "resina_enredada",
    ),
    _d(
        "CON_PDN_01",
        "Patrulha de Nareth",
        "CACA",
        "R3",
        "Uma ameaça foi identificada em uma rota das Planícies. Elimine o alvo registrado.",
    ),
    _d(
        "CON_PDN_02",
        "Coleta das Planícies",
        "COLETA",
        "R3",
        "Um recurso regional foi solicitado para abastecimento. Reúna a quantidade definida pelo contrato.",
        _NAR + "bronze_de_marco",
    ),
    _d(
        "CON_PDN_03",
        "Rota de Suprimentos",
        "ENTREGA",
        "R3",
        "Suprimentos precisam alcançar outro ponto da região. Faça a entrega no destino indicado.",
    ),
    _d(
        "CON_PDN_04",
        "Marca na Paisagem",
        "INVESTIGACAO",
        "R3",
        "Uma marca foi registrada na paisagem. Examine o local e confirme a ocorrência sem tirar conclusões além da evidência.",
    ),
    _d(
        "CON_PDN_05",
        "Vestígio na Estrada",
        "INVESTIGACAO",
        "R3",
        "Um vestígio recente foi encontrado em uma rota. Examine o ponto e registre o resultado.",
    ),
    _d(
        "CON_PDN_06",
        "Caçada nas Planícies",
        "CACA",
        "R3",
        "A presença de uma ameaça foi confirmada. Complete a Caça definida pelo contrato.",
    ),
    _d(
        "CON_VC_01",
        "Ameaça Carmesim",
        "CACA",
        "R4",
        "Uma ameaça interfere nas rotas das Várzeas. Elimine o alvo definido no contrato.",
    ),
    _d(
        "CON_VC_02",
        "Ferro de Salmoura",
        "COLETA",
        "R4",
        "Fragmentos metálicos podem ser recuperados nas áreas adequadas das Várzeas. Reúna o material solicitado.",
        _VAR + "ferro_de_salmoura",
    ),
    _d(
        "CON_VC_03",
        "Couro de Várzea",
        "COLETA",
        "R4",
        "Um couro regional é necessário para abastecimento. Reúna o recurso indicado.",
        _VAR + "couro_de_varzea",
    ),
    _d(
        "CON_VC_04",
        "Junco Ferruginoso",
        "COLETA",
        "R4",
        "Juncos com propriedades adequadas são procurados nas Várzeas. Reúna o material solicitado.",
        _VAR + "junco_ferruginoso",
    ),
    _d(
        "CON_VC_05",
        "Entrega das Várzeas",
        "ENTREGA",
        "R4",
        "Um carregamento precisa alcançar o destino através das Várzeas. Faça a entrega indicada.",
    ),
    _d(
        "CON_VC_06",
        "Soro Antigo",
        "COLETA",
        "R4",
        "Um recurso raro das Várzeas foi solicitado. Reúna o Soro necessário para concluir o contrato.",
        _VAR + "soro_antigo",
    ),
    _d(
        "CON_AC_01",
        "Ameaça da Escarpa",
        "CACA",
        "R5",
        "Uma ameaça foi identificada em uma rota elevada. Elimine o alvo indicado pelo contrato.",
    ),
    _d(
        "CON_AC_02",
        "Ferro de Contrapeso",
        "COLETA",
        "R5",
        "Metal usado em estruturas de sustentação ainda pode ser recuperado. Reúna o recurso solicitado.",
        _ALT + "ferro_contrapeso",
    ),
    _d(
        "CON_AC_03",
        "Couro de Escarpa",
        "COLETA",
        "R5",
        "Um couro resistente é necessário para abastecimento. Reúna o material regional solicitado.",
        _ALT + "couro_escarpa",
    ),
    _d(
        "CON_AC_04",
        "Líquen de Pedreira",
        "COLETA",
        "R5",
        "Um líquen específico cresce em áreas de pedreira. Reúna a quantidade solicitada.",
        _ALT + "liquen_pedreira",
    ),
    _d(
        "CON_AC_05",
        "Cinza de Basalto",
        "COLETA",
        "R5",
        "Cinza adequada pode ser recuperada em pontos específicos dos Altos. Reúna o material necessário.",
        _ALT + "cinza_basalto",
    ),
    _d(
        "CON_AC_06",
        "Registro da Escarpa",
        "INVESTIGACAO",
        "R5",
        "Um ponto estrutural precisa ser verificado. Examine a área e registre somente aquilo que puder ser observado.",
    ),
    _d(
        "CON_CDV_01",
        "Ameaça do Último Refúgio",
        "CACA",
        "R6",
        "Uma ameaça foi identificada nas rotas dos Confins. Elimine o alvo definido pelo contrato.",
    ),
    _d(
        "CON_CDV_02",
        "Ferro de Baliza",
        "COLETA",
        "R6",
        "Metal usado nas estruturas regionais precisa ser recuperado. Reúna o Material solicitado.",
        _CDV + "ferro_baliza",
    ),
    _d(
        "CON_CDV_03",
        "Couro de Marcha",
        "COLETA",
        "R6",
        "Um couro regional é necessário para manutenção de equipamentos e suprimentos. Reúna o recurso solicitado.",
        _CDV + "couro_marcha",
    ),
    _d(
        "CON_CDV_04",
        "Musgo de Limiar",
        "COLETA",
        "R6",
        "Um musgo específico é encontrado próximo às rotas dos Confins. Reúna o material solicitado.",
        _CDV + "musgo_limiar",
    ),
    _d(
        "CON_CDV_05",
        "Pó de Referência",
        "COLETA",
        "R6",
        "Um pó regional é necessário para registros e manutenção. Reúna a quantidade definida no contrato.",
        _CDV + "po_referencia",
    ),
    _d(
        "CON_CDV_06",
        "Registro do Limiar",
        "INVESTIGACAO",
        "R6",
        "Um registro precisa ser confirmado nos Confins. Examine o local e preserve a distinção entre evidência e interpretação.",
    ),
)

BY_ID = {item.definition_id: item for item in CATALOG}


def definitions_for(region: str) -> tuple[ContractDefinition, ...]:
    return tuple(item for item in CATALOG if item.region == region)


def validate_catalog() -> None:
    if len(CATALOG) != 36 or len(BY_ID) != 36:
        raise ValueError("catalog must hold 36 unique contracts")
    for region in REGION_CODES:
        if len(definitions_for(region)) != 6:
            raise ValueError(f"{region} must hold 6 contracts")
    for item in CATALOG:
        if item.contract_type == "ESCOLTA":
            raise ValueError("Escolta stays disabled")
        if item.reward_profile not in REWARD_PROFILES:
            raise ValueError(f"{item.definition_id}: unknown reward profile")
        if (item.contract_type == "COLETA") != (item.material_id is not None):
            raise ValueError(f"{item.definition_id}: only Coleta names a Material")


validate_catalog()

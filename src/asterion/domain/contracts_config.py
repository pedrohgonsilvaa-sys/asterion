"""Valores de jogo dos Contratos Regionais (Documento B §38).

PROPOSTA A APROVAR PELO AUTOR. Este e o UNICO arquivo com numeros do sistema:
nenhum outro modulo pode repetir recompensa, faixa de nivel, duracao, limite ou
multiplicador. O sistema nasce DESATIVADO (`ASTERION_CONTRACTS_ENABLED=false`) ate
o autor resolver `docs/CONTRATOS_REGIONAIS_CONFLITOS.md`.

Linhas marcadas `PENDENTE_AUTOR` nao existem no Documento B: sao valores minimos
para o sistema funcionar e precisam de decisao explicita.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

STATUS = "PROPOSTA_A_APROVAR"

# --- §38: limites -----------------------------------------------------------
SIMULTANEOUS_CONTRACTS = 3
BOARD_OFFERS = 6
BOARD_DURATION = timedelta(hours=24)
BOARD_REFRESH = timedelta(hours=24)
ACCEPTED_DURATION = timedelta(hours=48)
ABANDON_ECONOMIC_PENALTY = 0
MAX_BUTTONS = 8

# --- §38: tipos -------------------------------------------------------------
ACTIVE_TYPES = ("CACA", "COLETA", "ENTREGA", "INVESTIGACAO")
ALL_TYPES = ACTIVE_TYPES + ("ESCOLTA",)
TYPE_MULTIPLIER = {  # informativo: os perfis abaixo ja sao os valores finais
    "CACA": "1.00",
    "COLETA": "0.90",
    "ENTREGA": "0.95",
    "INVESTIGACAO": "0.90",
    "ESCOLTA": "1.10",
}
ESCORT_ACTIVE_CONTRACTS = 0

# --- §15/§16/§38: faixas e gates -------------------------------------------
REGION_CODES = ("R1", "R2", "R3", "R4", "R5", "R6")
REGION_NAMES = {
    "R1": "Terras do Ocaso",
    "R2": "Vales dos Enforcados",
    "R3": "Planícies de Nareth",
    "R4": "Várzeas Carmesins",
    "R5": "Altos Cinéreos",
    "R6": "Confins do Véu",
}
LEVEL_BAND = {
    "R1": (1, 10),
    "R2": (11, 20),
    "R3": (21, 30),
    "R4": (31, 40),
    "R5": (41, 50),
    "R6": (51, 60),
}
GATE_QUEST = {"R1": "P1", "R2": "P6", "R3": "P12", "R4": "P18", "R5": "P24", "R6": "P30"}

# --- §38: perfis de recompensa (xp, coroas, materiais) ----------------------
REWARD_PROFILES: dict[str, tuple[int, int, int]] = {
    "REWARD_R1_CACA": (120, 20, 2),
    "REWARD_R1_COLETA": (100, 15, 3),
    "REWARD_R1_ENTREGA": (110, 25, 2),
    "REWARD_R1_INVESTIGACAO": (105, 20, 2),
    "REWARD_R2_CACA": (260, 45, 2),
    "REWARD_R2_COLETA": (220, 35, 3),
    "REWARD_R2_ENTREGA": (240, 50, 2),
    "REWARD_R2_INVESTIGACAO": (230, 45, 2),
    "REWARD_R3_CACA": (480, 80, 3),
    "REWARD_R3_COLETA": (410, 65, 4),
    "REWARD_R3_ENTREGA": (440, 90, 3),
    "REWARD_R3_INVESTIGACAO": (425, 80, 3),
    "REWARD_R4_CACA": (850, 140, 3),
    "REWARD_R4_COLETA": (720, 115, 4),
    "REWARD_R4_ENTREGA": (780, 155, 3),
    "REWARD_R4_INVESTIGACAO": (750, 140, 3),
    "REWARD_R5_CACA": (1450, 240, 4),
    "REWARD_R5_COLETA": (1230, 195, 5),
    "REWARD_R5_ENTREGA": (1330, 265, 4),
    "REWARD_R5_INVESTIGACAO": (1280, 240, 4),
    "REWARD_R6_CACA": (2300, 380, 5),
    "REWARD_R6_COLETA": (1950, 310, 6),
    "REWARD_R6_ENTREGA": (2100, 420, 5),
    "REWARD_R6_INVESTIGACAO": (2050, 380, 5),
}


@dataclass(frozen=True, slots=True)
class Reward:
    xp: int
    crowns: int
    materials: int


def reward_profile(key: str) -> Reward:
    xp, crowns, materials = REWARD_PROFILES[key]
    return Reward(xp, crowns, materials)


# --- PENDENTE_AUTOR: o §36 nao define alvos nem materiais de recompensa -----
# Quantos objetivos cada tipo exige (Coleta = quantidade do Material exigido).
TARGET_BY_TYPE = {"CACA": 1, "COLETA": 3, "ENTREGA": 1, "INVESTIGACAO": 1}
# Material de recompensa dos tipos sem Material proprio (Caca/Entrega/Investigacao):
# o primeiro Material Basico regional. Coleta paga o proprio Material exigido.
REGION_REWARD_MATERIAL = {
    "R1": "material.tdo.ferro_de_fuligem",
    "R2": "material.vde.ferro_enredado",
    "R3": "material.nareth.bronze_de_marco",
    "R4": "material.varzeas.ferro_de_salmoura",
    "R5": "material.altos.ferro_contrapeso",
    "R6": "material.confins.ferro_baliza",
}
# Lugar do objetivo: "hub" = Hub da Regiao; inteiro = indice em RegionInfo.locals.
PLACE_BY_TYPE = {"ENTREGA": "hub", "INVESTIGACAO": 0}
PLACE_BY_DEFINITION = {"CON_TDO_06": 1, "CON_PDN_05": 1}

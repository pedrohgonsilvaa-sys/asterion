"""Presentation catalogs for knowledge already persisted by the game.

Only IDs emitted by the current TDO vertical slice are listed here. The
services still gate every entry, fragment, creature, variant, and achievement
on the character's persisted knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass

CODEX_CATEGORY_ORDER = (
    ("world", "🪐 Mundo e Cosmologia"),
    ("regions", "🗺️ Regiões e Locais"),
    ("peoples", "🏴 Povos e Facções"),
    ("figures", "👤 Figuras"),
    ("history", "📜 História e Acontecimentos"),
    ("mysteries", "👁️ Mistérios e Fenômenos"),
    ("chronicles", "🌌 Crônicas"),
)


@dataclass(frozen=True, slots=True)
class CodexPresentation:
    entry_id: str
    title: str
    category: str
    order: int
    location_id: str | None = None


CODEX_ENTRIES = (
    CodexPresentation(
        "codex.location.estrada_das_cinzas",
        "Estrada das Cinzas",
        "regions",
        10,
        "tdo.location.estrada_das_cinzas",
    ),
    CodexPresentation(
        "codex.location.ruinas_do_vigia",
        "Ruínas do Vigia",
        "regions",
        50,
        "tdo.location.ruinas_do_vigia",
    ),
    CodexPresentation(
        "codex.location.camara_do_poente",
        "Câmara do Poente",
        "regions",
        60,
        "tdo.location.camara_do_poente",
    ),
    CodexPresentation(
        "codex.location.cripta_do_ocaso",
        "Cripta do Ocaso",
        "regions",
        70,
        "tdo.location.cripta_do_ocaso",
    ),
    CodexPresentation(
        "codex.location.galerias_do_vigia",
        "Galerias do Vigia",
        "regions",
        80,
        "tdo.location.galerias_do_vigia",
    ),
    CodexPresentation("codex.figure.alda_veyr", "Alda Veyr", "figures", 10),
    CodexPresentation("codex.figure.oren_cal", "Oren Cal", "figures", 20),
    CodexPresentation("codex.history.antigos_asterianos", "Antigos Asterianos", "history", 10),
    CodexPresentation("codex.mystery.marcas_na_fuligem", "Marcas na Fuligem", "mysteries", 10),
    CodexPresentation("codex.mystery.peregrinos_do_ocaso", "Peregrinos do Ocaso", "history", 20),
    CodexPresentation("codex.phenomena.luzes_do_ocaso", "Luzes do Ocaso", "mysteries", 20),
    CodexPresentation(
        "codex.history.camadas_de_sepultamento", "Camadas de Sepultamento", "history", 30
    ),
    CodexPresentation("codex.history.camara_dos_nomes", "Câmara dos Nomes", "history", 40),
    CodexPresentation("codex.history.o_ultimo_guardiao", "O Último Guardião", "history", 50),
    CodexPresentation("codex.history.os_sem_nome", "Os Sem-Nome", "history", 60),
    CodexPresentation("codex.history.rede_de_defesa", "Rede de Defesa", "history", 70),
    CodexPresentation("codex.history.camara_de_contencao", "Câmara de Contenção", "history", 80),
    CodexPresentation("codex.history.primeiro_selo", "O Primeiro Selo", "history", 90),
    CodexPresentation(
        "codex.history.ordens_que_permanecem", "Ordens que Permanecem", "history", 100
    ),
    CodexPresentation("codex.mystery.ancora_do_poente", "Âncora do Poente", "mysteries", 30),
)
CODEX_BY_ID = {entry.entry_id: entry for entry in CODEX_ENTRIES}


@dataclass(frozen=True, slots=True)
class FragmentPresentation:
    title: str
    text: str


CODEX_FRAGMENTS = {
    "codex.fragment.estrada.memoria_viajantes": FragmentPresentation(
        "Memória de viajantes",
        "Vestígios na estrada preservam a memória de viajantes que passaram por ali.",
    ),
    "codex.fragment.estrada.luzes_na_estrada": FragmentPresentation(
        "Luzes na estrada", "Luzes foram observadas ao longo da Estrada das Cinzas."
    ),
    "codex.fragment.bosque.estrutura_enterrada": FragmentPresentation(
        "Estrutura enterrada",
        "Vestígios de uma estrutura antiga foram encontrados sob o Bosque Calcinado.",
    ),
    "codex.fragment.bosque.caminho_ocidental": FragmentPresentation(
        "Caminho ocidental", "Um caminho a oeste foi registrado no Bosque Calcinado."
    ),
    "codex.fragment.ruinas.estruturas_guarda": FragmentPresentation(
        "Estruturas de guarda", "As Ruínas contêm estruturas de guarda em trechos mais profundos."
    ),
    "codex.fragment.ruinas.ocupacao_posterior": FragmentPresentation(
        "Ocupação posterior", "Há sinais de ocupação posterior nas Ruínas."
    ),
    "codex.fragment.ruinas.porta_do_poente": FragmentPresentation(
        "Porta do Poente", "A Porta do Poente é uma estrutura deliberadamente protegida."
    ),
    "codex.fragment.ruinas.simbolo_recorrente": FragmentPresentation(
        "Símbolo recorrente",
        "Um símbolo recorrente foi registrado; seu significado permanece incerto.",
    ),
    "codex.fragment.peregrinos.ruinas.trilha_termina": FragmentPresentation(
        "Fim da trilha",
        "A trilha dos Peregrinos deixa de formar uma estrada e vira apenas vestígio.",
    ),
    "codex.fragment.ruinas.peregrinos_passaram": FragmentPresentation(
        "Passagem dos Peregrinos",
        "Os vestígios permitem registrar a passagem dos Peregrinos pelas Ruínas.",
    ),
    "codex.fragment.crypt.entry": FragmentPresentation(
        "Entrada", "A Cripta do Ocaso foi descoberta sob a Charneca da Fuligem."
    ),
    "codex.fragment.crypt.layers": FragmentPresentation(
        "Camadas", "Os registros descrevem diferentes camadas de sepultamento."
    ),
    "codex.fragment.crypt.names": FragmentPresentation(
        "Nomes", "A Câmara dos Nomes preserva inscrições encontradas na Cripta."
    ),
    "codex.fragment.crypt.last_guardian": FragmentPresentation(
        "Último guardião", "Um guardião foi encontrado nas profundezas da Cripta."
    ),
    "codex.fragment.crypt.sem_nome": FragmentPresentation(
        "Os Sem-Nome",
        "O nome foi registrado, mas a identidade anterior do Chefe permanece desconhecida.",
    ),
    "codex.fragment.galleries.entry": FragmentPresentation(
        "Entrada", "As Galerias do Vigia foram descobertas."
    ),
    "codex.fragment.galleries.defense_network": FragmentPresentation(
        "Rede de defesa", "Uma rede de defesa foi registrada nas Galerias."
    ),
    "codex.fragment.galleries.containment": FragmentPresentation(
        "Câmara de Contenção", "Uma Câmara de Contenção foi registrada nas Galerias."
    ),
    "codex.fragment.galleries.first_seal": FragmentPresentation(
        "Primeiro Selo", "O Primeiro Selo foi registrado após sua descoberta."
    ),
    "codex.fragment.galleries.orders_remain": FragmentPresentation(
        "Ordens que Permanecem", "Fragmentos registram ordens que permanecem."
    ),
    "codex.fragment.antigos_asterianos.outras_ancoras_existiram": FragmentPresentation(
        "Outras estruturas", "Registros indicam que outras estruturas chamadas Âncoras existiram."
    ),
    "codex.fragment.ancora_do_poente.nome_registrado": FragmentPresentation(
        "Nome registrado", "Esta estrutura é chamada Âncora do Poente."
    ),
    "codex.fragment.ancora_do_poente.protegida_pelo_vigia": FragmentPresentation(
        "Proteção", "O Vigia Partido protegia a estrutura."
    ),
    "codex.fragment.ancora_do_poente.outras_ancoras": FragmentPresentation(
        "Outras Âncoras", "Registros indicam que outras Âncoras existiram."
    ),
    "codex.fragment.camara_do_poente.estrutura_chamada_ancora": FragmentPresentation(
        "Estrutura central", "A estrutura central recebeu o nome Âncora do Poente."
    ),
    "codex.fragment.ruinas_do_vigia.vigia_protegia_estrutura": FragmentPresentation(
        "Proteção do Vigia", "O Vigia Partido protegia a estrutura central."
    ),
}


@dataclass(frozen=True, slots=True)
class AchievementPresentation:
    achievement_id: str
    name: str
    category: str
    description: str
    reward: str | None = None
    player_facing: bool = True


ACHIEVEMENT_CATEGORIES = (
    ("exploration", "🧭 Exploração"),
    ("combat", "⚔️ Combate"),
    ("pve", "⛓️ PvE"),
    ("pvp", "🏅 PvP"),
    ("guild", "🛡️ Guilda"),
    ("professions", "⚒️ Ofícios"),
    ("chronicles", "🌌 Crônicas"),
    ("bestiary", "🐾 Bestiário"),
    ("secrets", "👁️ Segredos"),
)
ACHIEVEMENTS = (
    AchievementPresentation(
        "feat.tdo.cinzas_na_estrada",
        "Cinzas na Estrada",
        "exploration",
        "Concluiu o Prólogo em Vitória ou Derrota válida.",
    ),
    AchievementPresentation(
        "feat.tdo.a_ultima_guarda",
        "A Última Guarda",
        "combat",
        "Derrotou o Vigia Partido pela primeira vez.",
        "Título · Vigia das Cinzas",
    ),
    AchievementPresentation(
        "feat.tdo.terras_do_ocaso",
        "Terras do Ocaso",
        "exploration",
        "Concluiu P6, alcançou Nv.10 e descobriu os cinco Locais principais.",
        "Banner · Ocaso",
    ),
    # P6 also stores this technical gate in Achievement. It is deliberately
    # not a player-facing Feito in the regional catalog.
    AchievementPresentation(
        "feat.tdo.campaign.completed",
        "",
        "",
        "",
        player_facing=False,
    ),
)
ACHIEVEMENT_BY_ID = {entry.achievement_id: entry for entry in ACHIEVEMENTS}


TDO_REGION_ID = "tdo"
TDO_REGION_LABEL = "🌑 Terras do Ocaso · Nv. 1–10"
TDO_LOCATIONS = {
    "tdo.location.estrada_das_cinzas": "Estrada das Cinzas",
    "tdo.location.refugio_do_ocaso": "Refúgio do Ocaso",
    "tdo.location.charneca_da_fuligem": "Charneca da Fuligem",
    "tdo.location.bosque_calcinado": "Bosque Calcinado",
    "tdo.location.ruinas_do_vigia": "Ruínas do Vigia",
    "tdo.location.camara_do_poente": "Câmara do Poente",
    "tdo.location.cripta_do_ocaso": "Cripta do Ocaso",
    "tdo.location.galerias_do_vigia": "Galerias do Vigia",
}
HABITAT_EVIDENCE_TO_LOCATION = {
    "estrada": "tdo.location.estrada_das_cinzas",
    "Estrada das Cinzas": "tdo.location.estrada_das_cinzas",
    "Charneca da Fuligem": "tdo.location.charneca_da_fuligem",
    "Bosque Calcinado": "tdo.location.bosque_calcinado",
    "Ruínas do Vigia": "tdo.location.ruinas_do_vigia",
    **{location_id: location_id for location_id in TDO_LOCATIONS},
}
MATERIAL_LABELS = {
    "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
    "material.tdo.couro_escoriado": "Couro Escoriado",
    "material.tdo.erva_cinzenta": "Erva Cinzenta",
    "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
    "material.tdo.fragmento_aprimoramento_i": "Fragmento de Aprimoramento I",
}


@dataclass(frozen=True, slots=True)
class CreaturePresentation:
    region_id: str
    habitats: tuple[str, ...]


CREATURE_PRESENTATION = {
    "dog_cinereo": CreaturePresentation(
        TDO_REGION_ID, ("tdo.location.estrada_das_cinzas", "tdo.location.charneca_da_fuligem")
    ),
    "corvo_fuligem": CreaturePresentation(
        TDO_REGION_ID, ("tdo.location.estrada_das_cinzas", "tdo.location.charneca_da_fuligem")
    ),
    "peregrino_calcinado": CreaturePresentation(
        TDO_REGION_ID,
        (
            "tdo.location.estrada_das_cinzas",
            "tdo.location.charneca_da_fuligem",
            "tdo.location.bosque_calcinado",
        ),
    ),
    "alfa_cinereo": CreaturePresentation(TDO_REGION_ID, ("tdo.location.estrada_das_cinzas",)),
    "aranha_cinza": CreaturePresentation(
        TDO_REGION_ID, ("tdo.location.charneca_da_fuligem", "tdo.location.bosque_calcinado")
    ),
    "cervo_escoriado": CreaturePresentation(
        TDO_REGION_ID, ("tdo.location.charneca_da_fuligem", "tdo.location.bosque_calcinado")
    ),
    "carnical_fuligem": CreaturePresentation(
        TDO_REGION_ID, ("tdo.location.bosque_calcinado", "tdo.location.ruinas_do_vigia")
    ),
    "mariposa_brasa": CreaturePresentation(
        TDO_REGION_ID, ("tdo.location.bosque_calcinado", "tdo.location.ruinas_do_vigia")
    ),
    "viuva_fuligem": CreaturePresentation(TDO_REGION_ID, ("tdo.location.bosque_calcinado",)),
    "vigia_rachado": CreaturePresentation(TDO_REGION_ID, ("tdo.location.ruinas_do_vigia",)),
    "custodio_sem_rosto": CreaturePresentation(TDO_REGION_ID, ("tdo.location.ruinas_do_vigia",)),
    "custodio_poente": CreaturePresentation(TDO_REGION_ID, ("tdo.location.ruinas_do_vigia",)),
    "vigia_partido": CreaturePresentation(TDO_REGION_ID, ("tdo.location.camara_do_poente",)),
    "profanador_calcinado": CreaturePresentation(TDO_REGION_ID, ("tdo.location.cripta_do_ocaso",)),
    "guardiao_lapides": CreaturePresentation(TDO_REGION_ID, ("tdo.location.cripta_do_ocaso",)),
    "sem_nome": CreaturePresentation(TDO_REGION_ID, ("tdo.location.cripta_do_ocaso",)),
    "vigia_integro": CreaturePresentation(TDO_REGION_ID, ("tdo.location.galerias_do_vigia",)),
    "preceptor_rachado": CreaturePresentation(TDO_REGION_ID, ("tdo.location.galerias_do_vigia",)),
    "custodio_primeiro_selo": CreaturePresentation(
        TDO_REGION_ID, ("tdo.location.galerias_do_vigia",)
    ),
}
CREATURE_NOTES = {
    # The regional source explicitly leaves this creature's origin and nature unconfirmed.
    "peregrino_calcinado": "Origem e natureza ainda não confirmadas.",
}
VARIANT_LABELS = {
    "furious": "Furioso",
    "agile": "Ágil",
    "resistant": "Resistente",
    "hemorrhagic": "Hemorrágico",
    "venomous": "Venenoso",
}

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
    CodexPresentation("codex.route.rotas_dos_vales", "Rotas dos Vales", "regions", 90),
    CodexPresentation(
        "codex.location.mata_suspensa",
        "Mata Suspensa",
        "regions",
        100,
        "vde.location.mata_suspensa",
    ),
    CodexPresentation(
        "codex.location.baixios_enredados",
        "Baixios Enredados",
        "regions",
        110,
        "vde.location.baixios_enredados",
    ),
    CodexPresentation(
        "codex.location.claustro_das_raizes",
        "Claustro das Raízes",
        "regions",
        120,
        "vde.location.claustro_das_raizes",
    ),
    CodexPresentation(
        "codex.location.berco_da_matriarca",
        "Berço da Matriarca",
        "regions",
        130,
        "vde.location.berco_da_matriarca",
    ),
    CodexPresentation("codex.figure.iven_raal", "Iven Raal", "figures", 30),
    CodexPresentation("codex.mystery.o_no_antigo", "O Nó Antigo", "mysteries", 50),
    CodexPresentation(
        "codex.mystery.estruturas_interligadas",
        "Estruturas Interligadas",
        "mysteries",
        60,
    ),
    CodexPresentation(
        "codex.mystery.a_rede_sob_os_vales",
        "A Rede sob os Vales",
        "mysteries",
        70,
    ),
    CodexPresentation(
        "codex.mystery.rotinas_que_permanecem",
        "Rotinas que Permanecem",
        "mysteries",
        80,
    ),
    CodexPresentation(
        "codex.mystery.raizes_que_seguem_pedra",
        "Raízes que Seguem Pedra",
        "mysteries",
        40,
    ),
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
    "codex.fragment.vales.routes.garganta_vigilia": FragmentPresentation(
        "Rota da Garganta à Vigília",
        "A rota conhecida liga a Garganta dos Laços à Vigília do Vale.",
    ),
    "codex.fragment.vales.routes.s7_marker_shift": FragmentPresentation(
        "Marcações deslocadas",
        "As raízes alteraram fisicamente o terreno e deslocaram marcações da rota.",
    ),
    "codex.fragment.mata.entrada_registrada": FragmentPresentation(
        "Entrada", "A Mata Suspensa foi alcançada pela rota aberta durante a missão."
    ),
    "codex.fragment.mata.raizes_sob_a_pedra": FragmentPresentation(
        "Raízes sob a pedra",
        "As raízes convergem para linhas antigas sob o solo; o crescimento não parece aleatório.",
    ),
    "codex.fragment.mata.rotas_adaptadas": FragmentPresentation(
        "Passagens adaptadas",
        "Os habitantes adaptam rotas e passarelas conforme as raízes avançam pelo terreno.",
    ),
    "codex.fragment.vales.routes.s8_alternate_passage": FragmentPresentation(
        "Rota alternativa",
        "Uma rota alternativa foi marcada após a passagem de suprimentos ser reorganizada.",
    ),
    "codex.fragment.baixios.entry_recorded": FragmentPresentation(
        "Baixios Enredados",
        "O fundo úmido dos Vales reúne água escura, turfa, raízes densas e caminhos sufocados.",
    ),
    "codex.fragment.iven.regional_register": FragmentPresentation(
        "Iven Raal",
        "Iven Raal registra os Vales e investiga as estruturas antigas.",
    ),
    "codex.fragment.no_antigo.translation_hypothesis": FragmentPresentation(
        "Inscrição danificada",
        "Um termo pode significar nó, junção ou ponto de ligação; "
        "a leitura permanece uma hipótese documental.",
    ),
    "codex.fragment.claustro.entry_recorded": FragmentPresentation(
        "Entrada do Claustro",
        "O Claustro das Raízes foi alcançado seguindo os marcos dos Baixios.",
    ),
    "codex.fragment.claustro.structures_linked": FragmentPresentation(
        "Estruturas interligadas",
        "Estruturas encontradas em diferentes Regiões não eram completamente isoladas; "
        "os registros apontam alguma forma de ligação entre pontos.",
    ),
    "codex.fragment.no_antigo.network_relation": FragmentPresentation(
        "Relação entre pontos",
        "Inscrições preservadas indicam organização ou ligação entre diferentes pontos; "
        "a função da rede permanece desconhecida.",
    ),
    "codex.fragment.no_antigo.entrada_santuario_descoberta": FragmentPresentation(
        "Entrada descoberta",
        "A entrada do Santuário do Nó Antigo foi descoberta no Claustro das Raízes.",
    ),
    "codex.fragment.vigia.rotinas_que_permanecem": FragmentPresentation(
        "Rotinas que Permanecem",
        "Alguns Vigias continuam executando rotinas antigas mesmo deformados e "
        "atravessados por raízes.",
    ),
    "codex.fragment.berco.access_opened": FragmentPresentation(
        "Acesso aberto",
        "O acesso ao Berço da Matriarca foi aberto a partir do Claustro das Raízes.",
    ),
    "codex.fragment.vales.network_and_matriarch": FragmentPresentation(
        "Convergência das raízes",
        "A estrutura asteriana é mais antiga que o crescimento atual. A Matriarca não "
        "construiu aquilo que existe sob os Vales. Quase todas as raízes anormais "
        "convergem para a área onde ela está.",
    ),
    "codex.fragment.mata.casca_camadas_externas": FragmentPresentation(
        "Camada externa",
        "A camada externa da Casca Errante possui propriedades próximas de matéria vegetal; "
        "sua origem permanece desconhecida.",
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
    hidden: bool = False


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
        "feat.tdo.cinzas_na_estrada", "Cinzas na Estrada", "exploration",
        "Concluiu o Prólogo.",
    ),
    AchievementPresentation(
        "feat.tdo.andarilho_das_cinzas", "Andarilho das Cinzas", "exploration",
        "Descobriu os Locais e Braseiros principais das Terras do Ocaso.",
        "Título · Andarilho das Cinzas",
    ),
    AchievementPresentation(
        "feat.tdo.sob_a_superficie", "Sob a Superfície", "secrets",
        "Descobriu as profundezas das Terras do Ocaso.",
        "Banner · Profundezas do Ocaso", hidden=True,
    ),
    AchievementPresentation(
        "feat.tdo.a_ultima_guarda", "A Última Guarda", "combat",
        "Derrotou o Vigia Partido pela primeira vez.",
        "Título · Vigia das Cinzas",
    ),
    AchievementPresentation(
        "feat.tdo.silencio_entre_os_nomes", "Silêncio entre os Nomes", "pve",
        "Concluiu a Cripta do Ocaso em dificuldade Estável pela primeira vez.",
        "Emblema · Lápide Raspada",
    ),
    AchievementPresentation(
        "feat.tdo.a_ordem_interrompida", "A Ordem Interrompida", "pve",
        "Concluiu as Galerias do Vigia em dificuldade Estável pela primeira vez.",
        "Emblema · Selo Fraturado",
    ),
    AchievementPresentation(
        "feat.tdo.cinzas_fraturadas", "Cinzas Fraturadas", "pve",
        "Concluiu a Cripta e as Galerias em dificuldade Fraturada.",
        "Moldura · Pedra Fraturada",
    ),
    AchievementPresentation(
        "feat.tdo.cacador_do_ocaso", "Caçador do Ocaso", "bestiary",
        "Dominou o conhecimento das criaturas-base das Terras do Ocaso.",
        "Título · Caçador do Ocaso",
    ),
    AchievementPresentation(
        "feat.tdo.entre_aquilo_que_caca", "Entre Aquilo que Caça", "secrets",
        "Dominou criaturas e descobriu as Variantes regionais.",
        "Aparência · Errante das Cinzas", hidden=True,
    ),
    AchievementPresentation(
        "feat.tdo.testemunha_dos_guardioes", "Testemunha dos Guardiões", "bestiary",
        "Estudou os guardiões conhecidos das Terras do Ocaso.",
        "Banner · Última Vigília",
    ),
    AchievementPresentation(
        "feat.tdo.nomes_sob_a_cinza", "Nomes sob a Cinza", "secrets",
        "Reuniu os registros disponíveis sobre a rota dos Peregrinos.",
        "Emblema · Nome Apagado", hidden=True,
    ),
    AchievementPresentation(
        "feat.tdo.a_ordem_ainda_permanece", "A Ordem Ainda Permanece", "secrets",
        "Reuniu os registros conhecidos sobre o Primeiro Selo e a Âncora.",
        "Moldura · Vigília Antiga", hidden=True,
    ),
    AchievementPresentation(
        "feat.tdo.terras_do_ocaso", "Terras do Ocaso", "exploration",
        "Concluiu a campanha principal das Terras do Ocaso.",
        "Banner · Ocaso",
    ),
    # Technical campaign gate; never listed as a player-facing Feito.
    AchievementPresentation(
        "feat.tdo.campaign.completed", "", "", "",
        player_facing=False, hidden=True,
    ),
)
ACHIEVEMENT_BY_ID = {entry.achievement_id: entry for entry in ACHIEVEMENTS}


TDO_REGION_ID = "tdo"
TDO_REGION_LABEL = "🌑 Terras do Ocaso · Nv. 1–10"
VDE_REGION_ID = "vde"
VDE_REGION_LABEL = "🪢 Vales dos Enforcados · Nv. 11–20"
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
VDE_LOCATIONS = {
    "vde.location.garganta_dos_lacos": "Garganta dos Laços",
    "vde.location.vigilia_do_vale": "Vigília do Vale",
    "vde.location.mata_suspensa": "Mata Suspensa",
    "vde.location.baixios_enredados": "Baixios Enredados",
    "vde.location.claustro_das_raizes": "Claustro das Raízes",
    "vde.location.berco_da_matriarca": "Berço da Matriarca",
}
LOCATION_LABELS = TDO_LOCATIONS | VDE_LOCATIONS
HABITAT_EVIDENCE_TO_LOCATION = {
    "estrada": "tdo.location.estrada_das_cinzas",
    "Estrada das Cinzas": "tdo.location.estrada_das_cinzas",
    "Charneca da Fuligem": "tdo.location.charneca_da_fuligem",
    "Bosque Calcinado": "tdo.location.bosque_calcinado",
    "Ruínas do Vigia": "tdo.location.ruinas_do_vigia",
    **{location_id: location_id for location_id in TDO_LOCATIONS},
    "Garganta dos Laços": "vde.location.garganta_dos_lacos",
    "Vigília do Vale": "vde.location.vigilia_do_vale",
    "Mata Suspensa": "vde.location.mata_suspensa",
    "Baixios Enredados": "vde.location.baixios_enredados",
    "Claustro das Raízes": "vde.location.claustro_das_raizes",
    "Berço da Matriarca": "vde.location.berco_da_matriarca",
    **{location_id: location_id for location_id in VDE_LOCATIONS},
}
MATERIAL_LABELS = {
    "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
    "material.tdo.couro_escoriado": "Couro Escoriado",
    "material.tdo.erva_cinzenta": "Erva Cinzenta",
    "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
    "material.tdo.fragmento_aprimoramento_i": "Fragmento de Aprimoramento I",
    "material.vde.ferro_enredado": "Ferro Enredado",
    "material.vde.couro_musgoso": "Couro Musgoso",
    "material.vde.erva_de_turfa": "Erva de Turfa",
    "material.vde.resina_enredada": "Resina Enredada",
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
    "lobo_musgoso": CreaturePresentation(
        VDE_REGION_ID,
        ("vde.location.garganta_dos_lacos", "vde.location.mata_suspensa"),
    ),
    "gralha_vale": CreaturePresentation(
        VDE_REGION_ID,
        ("vde.location.garganta_dos_lacos", "vde.location.mata_suspensa"),
    ),
    "peregrino_enredado": CreaturePresentation(
        VDE_REGION_ID,
        ("vde.location.garganta_dos_lacos", "vde.location.mata_suspensa"),
    ),
    "aranha_cipo": CreaturePresentation(
        VDE_REGION_ID,
        ("vde.location.mata_suspensa", "vde.location.baixios_enredados"),
    ),
    "cervo_no": CreaturePresentation(
        VDE_REGION_ID,
        ("vde.location.mata_suspensa", "vde.location.baixios_enredados"),
    ),
    "sanguessuga_turfa": CreaturePresentation(VDE_REGION_ID, ("vde.location.baixios_enredados",)),
    "casca_errante": CreaturePresentation(VDE_REGION_ID, ("vde.location.baixios_enredados",)),
    "mariposa_breu_verde": CreaturePresentation(VDE_REGION_ID, ("vde.location.baixios_enredados",)),
    "viuva_cipos": CreaturePresentation(
        VDE_REGION_ID,
        ("vde.location.mata_suspensa", "vde.location.baixios_enredados"),
    ),
    "vigia_enraizado": CreaturePresentation(VDE_REGION_ID, ("vde.location.baixios_enredados",)),
    "carrasco_casca": CreaturePresentation(VDE_REGION_ID, ("vde.location.baixios_enredados",)),
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

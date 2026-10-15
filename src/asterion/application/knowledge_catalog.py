"""Presentation catalogs for knowledge already persisted by the game."""

# ruff: noqa: E501

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
        "codex.location.campinas_do_meridiano",
        "Campinas do Meridiano",
        "regions",
        140,
        "nareth.location.campinas_do_meridiano",
    ),
    CodexPresentation(
        "codex.location.posto_de_nareth",
        "Posto de Nareth",
        "regions",
        150,
        "nareth.location.posto_de_nareth",
    ),
    CodexPresentation("codex.figure.nera_voss", "Nera Voss", "figures", 40),
    CodexPresentation("codex.route.rotas_de_nareth", "Rotas de Nareth", "regions", 160),
    CodexPresentation("codex.route.rotas_das_varzeas", "Rotas das Várzeas", "regions", 250),
    CodexPresentation("codex.figure.sera_morn", "Sera Morn", "figures", 60),
    CodexPresentation("codex.location.diques_rubros", "Diques Rubros", "regions", 260, "varzeas.location.diques_rubros"),
    CodexPresentation("codex.location.porto_da_salmoura", "Porto da Salmoura", "regions", 270, "varzeas.location.porto_da_salmoura"),
    CodexPresentation("codex.location.brejos_do_pulso", "Brejos do Pulso", "regions", 280, "varzeas.location.brejos_do_pulso"),
    CodexPresentation("codex.location.hortos_hemaris", "Hortos Hemaris", "regions", 290, "varzeas.location.hortos_hemaris"),
    CodexPresentation("codex.location.galerias_transferencia", "Galerias de Transferência", "regions", 295, "varzeas.location.galerias_transferencia"),
    CodexPresentation("codex.location.cisterna_transferencia", "Cisterna de Transferência", "regions", 296, "varzeas.location.cisterna_transferencia"),
    CodexPresentation(
        "codex.location.camara_da_matriz",
        "Câmara da Matriz",
        "regions",
        297,
        "varzeas.location.camara_da_matriz",
    ),
    CodexPresentation("codex.mystery.pulso_sob_a_lama", "Pulso sob a Lama", "mysteries", 281),
    CodexPresentation("codex.figure.ilyan_korr", "Ilyan Korr", "figures", 70),
    CodexPresentation("codex.history.projeto_hemaris_registro_inicial", "Projeto Hemaris — Registro Inicial", "history", 300),
    CodexPresentation("codex.history.transferencia", "Transferência", "history", 310),
    CodexPresentation("codex.mystery.protocolos_sem_paciente", "Protocolos sem Paciente", "mysteries", 311),
    CodexPresentation("codex.location.enfermaria_afundada", "Enfermaria Afundada", "regions", 312, "varzeas.location.enfermaria_afundada"),
    CodexPresentation("codex.history.restituicao_e_persistencia", "Restituição e Persistência", "history", 313),
    CodexPresentation("codex.mystery.linhas_transferencia_ativas", "Linhas de Transferência Ativas", "mysteries", 315),
    CodexPresentation("codex.history.protocolos_de_emergencia", "Protocolos de Emergência", "history", 316),
    CodexPresentation("codex.history.projeto_hemaris_custos_da_emergencia", "Projeto Hemaris — Custos da Emergência", "history", 317),
    CodexPresentation("codex.history.origem_ancestral_alteracoes_hemarias", "Origem Ancestral das Alterações Hemárias", "history", 318),
    CodexPresentation(
        "codex.history.queda_operacional_matriz_rubra",
        "Queda Operacional da Matriz Rubra",
        "history",
        319,
    ),
    CodexPresentation(
        "codex.mystery.quarentena_sem_supervisao",
        "Quarentena sem Supervisão",
        "mysteries",
        320,
    ),
    CodexPresentation("codex.figure.talen_orm", "Talen Orm", "figures", 50),
    CodexPresentation("codex.location.canais_secos", "Canais Secos", "regions", 170, "nareth.location.canais_secos"),
    CodexPresentation("codex.location.galerias_do_meridiano", "Galerias do Meridiano", "regions", 175, "nareth.location.galerias_do_meridiano"),
    CodexPresentation("codex.location.campos_invertidos", "Campos Invertidos", "regions", 180, "nareth.location.campos_invertidos"),
    CodexPresentation("codex.location.observatorio_do_eixo", "Observatório do Eixo", "regions", 190, "nareth.location.observatorio_do_eixo"),
    CodexPresentation("codex.location.observatorio_afundado", "Observatório Afundado", "regions", 195, "nareth.location.observatorio_afundado"),
    CodexPresentation("codex.location.camara_do_arconte", "Câmara do Arconte", "regions", 198, "nareth.location.camara_do_arconte"),
    CodexPresentation("codex.history.rede_de_medicao", "Rede de Medição", "history", 170),
    CodexPresentation("codex.mystery.horizonte_discordante", "Horizonte Discordante", "mysteries", 180),
    CodexPresentation("codex.mystery.linha_que_nao_fecha", "Linha que Não Fecha", "mysteries", 190),
    CodexPresentation("codex.mystery.o_eixo", "O Eixo", "mysteries", 200),
    CodexPresentation("codex.history.protocolos_de_referencia", "Protocolos de Referência", "history", 180),
    CodexPresentation("codex.history.cartografia_do_erro", "Cartografia do Erro", "history", 200),
    CodexPresentation("codex.history.custodia_das_ancoras", "Custódia das Âncoras", "history", 210),
    CodexPresentation("codex.history.estabilidade_do_veu", "Estabilidade do Véu", "history", 220),
    CodexPresentation("codex.history.juncao_circular", "Junção Circular", "history", 230),
    CodexPresentation("codex.history.circuitos_de_servico", "Circuitos de Serviço", "history", 231),
    CodexPresentation("codex.history.o_que_retorna", "O Que Retorna", "history", 232),
    CodexPresentation("codex.history.marcos_de_retorno", "Marcos de Retorno", "history", 233),
    CodexPresentation("codex.history.sala_de_recalibracao", "Sala de Recalibração", "history", 240),
    CodexPresentation("codex.history.eixos_de_calibracao", "Eixos de Calibração", "history", 241),
    CodexPresentation("codex.history.guardiao_referencia", "Guardião da Referência", "history", 242),
    CodexPresentation("codex.history.referencias_afundadas", "Referências Afundadas", "history", 243),
    CodexPresentation("codex.route.os_caminhos_que_nao_coincidem", "Os Caminhos que Não Coincidem", "regions", 230),
    CodexPresentation(
        "codex.location.mata_suspensa",
        "Mata Suspensa",
        "regions",
        100,
        "vde.location.mata_suspensa",
    ),
    CodexPresentation(
        "codex.location.fosso_das_raizes",
        "Fosso das Raízes",
        "regions",
        105,
        "vde.location.fosso_das_raizes",
    ),
    CodexPresentation(
        "codex.location.santuario_do_no_antigo",
        "Santuário do Nó Antigo",
        "regions",
        106,
        "vde.location.santuario_do_no_antigo",
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
        "codex.mystery.pulsacao_sob_a_pedra",
        "Pulsação sob a Pedra",
        "mysteries",
        75,
    ),
    CodexPresentation(
        "codex.mystery.rotinas_que_permanecem",
        "Rotinas que Permanecem",
        "mysteries",
        80,
    ),
    CodexPresentation(
        "codex.history.camara_das_quatro_raizes", "Câmara das Quatro Raízes", "history", 109
    ),
    CodexPresentation(
        "codex.history.protocolos_sepultados", "Protocolos Sepultados", "history", 110
    ),
    CodexPresentation("codex.history.selos_radicular", "Selos Radiculares", "history", 111),
    CodexPresentation("codex.history.guardiao_no_antigo", "Guardião do Nó Antigo", "history", 112),
    CodexPresentation(
        "codex.mystery.raizes_que_seguem_pedra",
        "Raízes que Seguem Pedra",
        "mysteries",
        40,
    ),
    CodexPresentation(
        "codex.mystery.cordas_sob_a_mata",
        "Cordas sob a Mata",
        "mysteries",
        105,
    ),
    CodexPresentation("codex.history.nos_pulsantes", "Nós Pulsantes", "history", 106),
    CodexPresentation(
        "codex.history.aquilo_que_pende", "Aquilo que Pende", "history", 107
    ),
    CodexPresentation(
        "codex.history.profundezas_suspensas",
        "Profundezas Suspensas",
        "history",
        108,
    ),
    CodexPresentation(
        "codex.history.nomes_dos_vales", "Nomes dos Vales", "history", 130
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
    "codex.fragment.fosso.entry": FragmentPresentation(
        "Entrada", "O Fosso das Raízes foi explorado sob a Mata Suspensa."
    ),
    "codex.fragment.fosso.cordas_sob_a_mata": FragmentPresentation(
        "Cordas sob a Mata",
        "Troncos, passarelas e raízes atravessam o vazio nas profundezas sob a Mata.",
    ),
    "codex.fragment.fosso.nos_pulsantes": FragmentPresentation(
        "Nós Pulsantes",
        "Nós ativos alteram a barreira recebida pela Casca Errante no Coração do Emaranhado.",
    ),
    "codex.fragment.fosso.aquilo_que_pende": FragmentPresentation(
        "Aquilo que Pende",
        "Uma criatura ocupa as profundezas e usa raízes e cordas para se sustentar.",
    ),
    "codex.fragment.fosso.profundezas_suspensas": FragmentPresentation(
        "Profundezas Suspensas",
        "Os registros do Fosso descrevem estruturas e raízes que atravessam o vazio sob a Mata.",
    ),
    "codex.fragment.sanctuary.entry": FragmentPresentation(
        "Entrada", "O Santuário do Nó Antigo foi descoberto sob o Claustro das Raízes."
    ),
    "codex.fragment.sanctuary.chamber": FragmentPresentation(
        "Câmara das Quatro Raízes",
        "Quatro raízes atravessam a câmara e sustentam a presença do Prelado Enraizado.",
    ),
    "codex.fragment.sanctuary.protocols": FragmentPresentation(
        "Protocolos Sepultados",
        "Registros do Santuário descrevem protocolos preservados sob as raízes.",
    ),
    "codex.fragment.sanctuary.radicular_seals": FragmentPresentation(
        "Selos Radiculares",
        "Três selos foram ativados na câmara do Guardião e alteraram a proteção recebida por ele.",
    ),
    "codex.fragment.sanctuary.guardian": FragmentPresentation(
        "Guardião do Nó Antigo",
        "Um guardião protege a câmara mais profunda do Santuário.",
    ),
    "codex.fragment.sanctuary.ancient_knot": FragmentPresentation(
        "O Nó Antigo",
        "Os registros do Santuário ampliam a evidência de ligação entre estruturas antigas; "
        "sua função permanece desconhecida.",
    ),
    "codex.fragment.sanctuary.interlinked_structures": FragmentPresentation(
        "Estruturas Interligadas",
        "Os registros do Santuário ampliam a evidência de ligação entre estruturas antigas; "
        "sua função permanece desconhecida.",
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
    "codex.fragment.nareth.p13.routes_initial": FragmentPresentation(
        "Rotas iniciais",
        "As Campinas e o Posto foram conectados por uma rota usada por viajantes; "
        "dois marcos não apontam na mesma direção.",
    ),
    "codex.fragment.nareth.s13.references": FragmentPresentation(
        "Referências verificadas",
        "Duas referências de passagem continuam úteis; a terceira não é confiável.",
    ),
    "codex.fragment.nareth.campinas.meridian_marker": FragmentPresentation(
        "Marco do Primeiro Meridiano",
        "A antiga estrada usava referências repetidas em intervalos regulares.",
    ),
    "codex.fragment.nareth.campinas.divergent_measures": FragmentPresentation(
        "Duas medidas para a mesma estrada",
        "Dois marcos que deveriam apontar a mesma rota divergem; "
        "sua função permanece desconhecida.",
    ),
    "codex.fragment.nareth.canais.entry": FragmentPresentation(
        "Canais Secos", "O leito seco e a antiga infraestrutura de orientação foram registrados."
    ),
    "codex.fragment.nareth.canais.brazier": FragmentPresentation(
        "Canal Alto", "O Braseiro do Canal Alto foi descoberto e registrado permanentemente."
    ),
    "codex.fragment.nareth.canais.measurement_gate": FragmentPresentation(
        "Comporta sem água", "Marcas de medição permanecem junto à comporta seca."
    ),
    "codex.fragment.nareth.canais.p14_plate": FragmentPresentation(
        "Placa de medição", "A placa de P14 registra termos de referência, desvio e estabilidade."
    ),
    "codex.fragment.nareth.canais.s14_route": FragmentPresentation(
        "Passagem estável", "A rota de suprimentos pelos Canais foi marcada como a mais estável."
    ),
    "codex.fragment.nareth.galerias.entry": FragmentPresentation(
        "Entrada", "Uma entrada das Galerias do Meridiano foi descoberta sob os Canais."
    ),
    "codex.fragment.nareth.galerias.circular_junction": FragmentPresentation(
        "Junção Circular", "A junção circular foi registrada durante a travessia das galerias."
    ),
    "codex.fragment.nareth.galerias.service_circuits": FragmentPresentation(
        "Circuitos de Serviço", "Balizas de serviço marcavam o circuito interno das galerias."
    ),
    "codex.fragment.nareth.galerias.returning_boss": FragmentPresentation(
        "O Que Retorna", "O encontro central foi registrado sem atribuir função além do observado."
    ),
    "codex.fragment.nareth.galerias.return_markers": FragmentPresentation(
        "Marcos de Retorno", "Marcos foram ativados durante a mudança de fase do encontro."
    ),
    "codex.fragment.nareth.galerias.return_resolved": FragmentPresentation(
        "Retorno ao Marco", "A resolução dos marcos restantes foi observada no encontro."
    ),
    "codex.fragment.nareth.observatory.recalibration_room": FragmentPresentation(
        "Sala de Recalibração", "Balizas de calibração estavam presentes na sala."
    ),
    "codex.fragment.nareth.observatory.calibration_axes": FragmentPresentation(
        "Eixos de Calibração", "Três Eixos de Calibração foram ativados durante o encontro."
    ),
    "codex.fragment.nareth.observatory.reference_guardian": FragmentPresentation(
        "Guardião da Referência", "O Guardião da Referência foi observado no encontro final."
    ),
    "codex.fragment.nareth.observatory.submerged_references": FragmentPresentation(
        "Referências Afundadas", "As referências afundadas foram registradas após a conclusão."
    ),
    "codex.fragment.nareth.campos.entry": FragmentPresentation(
        "Campos Invertidos", "O Local foi alcançado para comparar referências e distâncias."
    ),
    "codex.fragment.nareth.campos.brazier": FragmentPresentation(
        "Linha Quebrada", "O Braseiro da Linha Quebrada foi descoberto e registrado permanentemente."
    ),
    "codex.fragment.nareth.campos.line_does_not_close": FragmentPresentation(
        "Linha que Não Fecha", "A discrepância persiste sem identificar sua causa."
    ),
    "codex.fragment.nareth.campos.p15_records": FragmentPresentation(
        "Registros incompatíveis", "Registros históricos também divergiam após a Ruptura."
    ),
    "codex.fragment.nareth.campos.s15_routes": FragmentPresentation(
        "Rotas de retorno", "Os viajantes foram encontrados sem evidência de desaparecimento temporal ou duplicação."
    ),
    "codex.fragment.nareth.observatory.entry": FragmentPresentation(
        "Observatório do Eixo", "O Local contém uma plataforma de alinhamento e instrumentos mecânicos analógicos."
    ),
    "codex.fragment.nareth.observatory.brazier": FragmentPresentation(
        "Braseiro do Eixo", "O Braseiro do Eixo foi descoberto e registrado permanentemente."
    ),
    "codex.fragment.nareth.observatory.submerged_entry": FragmentPresentation(
        "Entrada", "A entrada do Observatório Afundado foi registrada como descoberta."
    ),
    "codex.fragment.nareth.observatory.off_center_plumb": FragmentPresentation(
        "Prumo fora do centro", "A leitura do prumo não coincide com o centro esperado."
    ),
    "codex.fragment.nareth.observatory.p16_protocol": FragmentPresentation(
        "Registro analógico", "O registro usa repetidamente termos de referência, desvio e estabilidade."
    ),
    "codex.fragment.nareth.observatory.s16_cartography": FragmentPresentation(
        "Cartografia do Erro", "O mapa atual registra diferenças entre a cartografia antiga e o percurso observado."
    ),
    "codex.fragment.nareth.observatory.s17_plumb_protocol": FragmentPresentation(
        "Leitura de prumo", "Uma ala cedida preserva referências geométricas e uma peça de calibração sem valor econômico."
    ),
    "codex.fragment.nareth.observatory.p17_anchor_custody": FragmentPresentation(
        "Custódia das Âncoras", "Um registro institucional associa a custódia das Âncoras ao monitoramento da estabilidade regional."
    ),
    "codex.fragment.nareth.chamber.incomplete_stability_record": FragmentPresentation(
        "Registro técnico incompleto", "O registro relaciona as Âncoras à estabilização do Véu, mas permanece incompleto."
    ),
    "codex.fragment.nareth.chamber.archon_identified": FragmentPresentation(
        "Arconte", "O custódio é identificado como Arconte técnico-administrativo."
    ),
    "codex.fragment.nareth.chamber.anchors_stabilized_veil": FragmentPresentation(
        "Estabilidade do Véu", "As Âncoras estabilizavam o Véu na região."
    ),
    "codex.fragment.nareth.chamber.regional_measurement": FragmentPresentation(
        "Medição regional", "Nareth media e comparava referências para cumprir essa função regional."
    ),
    "codex.fragment.nareth.chamber.continuity_crimson_direction": FragmentPresentation(
        "Continuidade logística", "Registros apontam uma direção logística para as Várzeas Carmesins."
    ),
    "codex.fragment.nareth.routes.s18_modern_route": FragmentPresentation(
        "Os Caminhos que Não Coincidem", "Uma rota moderna foi traçada usando pontos verificados, sem resolver a causa das discrepâncias."
    ),
    "codex.fragment.nareth.routes.s18_verified_points": FragmentPresentation(
        "Pontos verificados", "A rota registrada parte de referências verificadas nos diferentes Locais de Nareth."
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
    "codex.fragment.berco.matriarca_antiga_viva": FragmentPresentation(
        "A Matriarca",
        "A Matriarca é uma criatura viva antiga que se integrou progressivamente à rede "
        "de raízes; ela não era a origem completa do fenômeno.",
    ),
    "codex.fragment.vales.network_and_matriarch": FragmentPresentation(
        "Convergência das raízes",
        "A estrutura asteriana é mais antiga que o crescimento atual. A Matriarca não "
        "construiu aquilo que existe sob os Vales. Quase todas as raízes anormais "
        "convergem para a área onde ela está.",
    ),
    "codex.fragment.vales.pulsacao_estrutura_ativa": FragmentPresentation(
        "Pulsação sob a Pedra",
        "Após a queda da Matriarca, a estrutura antiga continua ativa. A correlação entre "
        "a estrutura e o crescimento anormal está registrada, mas a causalidade final "
        "permanece sem explicação.",
    ),
    "codex.fragment.vales.pos_vitoria": FragmentPresentation(
        "Após a Matriarca",
        "Após sua morte, as raízes pararam de reagir agressivamente. A estrutura asteriana "
        "sob o Berço permaneceu ativa. A correlação com o crescimento anormal é comprovada, "
        "mas a causalidade final não foi explicada.",
    ),
    "codex.fragment.vales.continuidade_nareth": FragmentPresentation(
        "Indício de continuidade",
        "Registros apontam indícios de continuidade da antiga rede em direção às Planícies "
        "de Nareth.",
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
    "codex.fragment.vales.nomes.registro_s10": FragmentPresentation(
        "Registro recuperado",
        "O registro de S10 confirma que um explorador retornou vivo; "
        "outra pessoa permanece desaparecida.",
    ),
    "codex.fragment.vales.nomes.registro_final": FragmentPresentation(
        "Último registro legível",
        "Marcas de passagem, um objeto pessoal e o último registro legível foram preservados. "
        "O encontro com um Peregrino Enredado não permitiu identificar sua origem.",
    ),
    "codex.fragment.vales.nomes.registro_vigilia": FragmentPresentation(
        "Nomes preservados",
        "A Vigília mantém um registro permanente dos desaparecidos. "
        "Alguns destinos são prováveis; outros permanecem sem resposta.",
    ),
    "codex.fragment.varzeas.p19.rotas_initial": FragmentPresentation(
        "Rotas iniciais",
        "Uma passagem segura entre os Diques Rubros e o Porto da Salmoura foi registrada "
        "a partir das indicações de viajantes atuais.",
    ),
    "codex.fragment.varzeas.diques.comporta_primeiro_dique": FragmentPresentation(
        "Comporta do Primeiro Dique",
        "Marcas de manutenção e níveis de água foram observados numa comporta parcialmente funcional.",
    ),
    "codex.fragment.varzeas.figure.sera_morn": FragmentPresentation(
        "Coordenação civil",
        "Sera Morn coordena a manutenção dos diques e a segurança das rotas.",
    ),
    "codex.fragment.varzeas.brejos.braseiro_juncos_baixos": FragmentPresentation(
        "Braseiro dos Juncos Baixos",
        "O Braseiro dos Juncos Baixos foi descoberto entre as passarelas alagadas.",
    ),
    "codex.fragment.varzeas.brejos.entrada_enfermaria_afundada": FragmentPresentation(
        "Entrada sob a lama",
        "Uma entrada da Enfermaria Afundada foi descoberta; seu interior ainda não foi explorado.",
    ),
    "codex.fragment.varzeas.brejos.pulso_de_pressao": FragmentPresentation(
        "Pulso de pressão",
        "A pressão sob a turfa coincide com pequenas elevações periódicas da água, sem determinar a origem do fenômeno.",
    ),
    "codex.fragment.varzeas.p20.pulso_sob_a_lama": FragmentPresentation(
        "Interpretação de Sera",
        "Os registros relacionam água, pressão, atividade biológica e infraestrutura antiga enterrada; sua origem permanece aberta.",
    ),
    "codex.fragment.varzeas.hortos.braseiro_horto_seco": FragmentPresentation(
        "Braseiro do Horto Seco",
        "O Braseiro do Horto Seco foi descoberto entre os antigos canais de cultivo.",
    ),
    "codex.fragment.varzeas.hortos.estufa_technical": FragmentPresentation(
        "Estufa de cultivo técnico",
        "A estufa preserva estruturas de cultivo técnico antigo; nenhuma função terapêutica foi associada ainda.",
    ),
    "codex.fragment.varzeas.hortos.estufa_therapeutic": FragmentPresentation(
        "Função terapêutica",
        "Após o registro inicial de P21, os cultivos dos Hortos podem ser relacionados a suporte e recuperação dentro do Projeto Hemaris.",
    ),
    "codex.fragment.varzeas.hortos.canteiro_dupla_funcao": FragmentPresentation(
        "Canteiro de Dupla Função",
        "Um canteiro combina funções distintas de cultivo e suporte, sem esclarecer estágios posteriores do projeto.",
    ),
    "codex.fragment.varzeas.figure.ilyan_korr": FragmentPresentation(
        "Registro de Ilyan Korr",
        "Ilyan Korr recebeu os registros técnicos dos Hortos e validou a leitura inicial da placa.",
    ),
    "codex.fragment.varzeas.p21.projeto_hemaris_registro_inicial": FragmentPresentation(
        "Placa técnica dos Hortos",
        "Uma placa relaciona cultivo e recuperação ao Projeto Hemaris. O registro comprova uma finalidade terapêutica/biológica inicial, sem esclarecer a operação completa do projeto.",
    ),
    "codex.fragment.varzeas.galerias.braseiro_valvulas": FragmentPresentation(
        "Braseiro das Válvulas",
        "O Braseiro das Válvulas foi registrado junto aos reservatórios das Galerias de Transferência.",
    ),
    "codex.fragment.varzeas.galerias.entrada_cisterna": FragmentPresentation(
        "Entrada da Cisterna",
        "Uma entrada da Cisterna de Transferência foi registrada; sua descoberta não significa que o interior foi explorado.",
    ),
    "codex.fragment.varzeas.galerias.linha_retorno": FragmentPresentation(
        "Linha de Retorno",
        "Uma linha de retorno foi identificada entre os reservatórios, sem determinar por si só todo o funcionamento do sistema.",
    ),
    "codex.fragment.varzeas.p22.transferencia": FragmentPresentation(
        "Registro técnico das Galerias",
        "O termo Transferência aparece como função técnica. Os registros indicam que recursos biológicos externos podiam sustentar organismos em colapso, sem estabelecer a extensão da coerção ou os protocolos posteriores.",
    ),
    "codex.fragment.varzeas.s22.protocolos_sem_paciente": FragmentPresentation(
        "Rotinas sem paciente válido",
        "As rotinas observadas continuavam preparando tratamento sem paciente válido. O registro descreve a ausência de contexto humano adequado sem estabelecer a origem ou o desfecho desses protocolos.",
    ),
    "codex.fragment.varzeas.enfermaria.afundada": FragmentPresentation(
        "Ala de triagem submersa",
        "A Enfermaria Afundada continha salas de triagem, retenção e persistência. As rotinas e equipamentos mostram manutenção clínica repetida, sem identificar responsáveis políticos.",
    ),
    "codex.fragment.varzeas.enfermaria.rotinas_de_suporte": FragmentPresentation(
        "Rotinas de suporte",
        "Registros da Enfermaria descrevem procedimentos de suporte que continuavam depois que o contexto de atendimento se perdeu.",
    ),
    "codex.fragment.varzeas.cisterna.transferencia": FragmentPresentation(
        "Canais da Cisterna",
        "A Cisterna armazenava e redistribuía recursos biológicos por linhas técnicas. O nome funcional não implica transferência espiritual ou necromancia.",
    ),
    "codex.fragment.varzeas.cisterna.linhas_ativas": FragmentPresentation(
        "Linhas ativas",
        "As linhas ainda mantinham estados de fluxo e contenção. A observação não determina por si só quem operava os protocolos.",
    ),
    "codex.fragment.varzeas.s23.protocolos_emergencia": FragmentPresentation(
        "Registros de emergência",
        "Marcações de emergência aparecem em linhas de transferência abertas fora do contexto normal. Os limites registrados foram reduzidos progressivamente; os documentos aqui reunidos ainda não identificam responsáveis políticos nem a cadeia integral dos acontecimentos.",
    ),
    "codex.fragment.varzeas.p23.custos_emergencia": FragmentPresentation(
        "Custos da emergência",
        "Os registros recompõem Restituição, Persistência, Transferência e Emergência. As práticas de emergência admitiram coerção e o uso de vida externa como recurso.",
    ),
    "codex.fragment.varzeas.p23.origem_ancestral": FragmentPresentation(
        "Alterações herdadas",
        "Evidências indicam alterações estáveis transmitidas por descendência em populações sobreviventes e sua contribuição aos ancestrais dos Hemários modernos. Hemários modernos não são experimentos, monstros, doença nem portadores de culpa coletiva; essa história não é prova de vampirismo.",
    ),
    "codex.fragment.varzeas.p24.queda_operacional_matriz_rubra": FragmentPresentation(
        "Estado pós-Ruptura",
        "A Matriz Rubra era um sistema biológico central de regulação do Projeto "
        "Hemaris e continuou operando após a Ruptura. Os registros descrevem a "
        "sequência de protocolos e o uso de recursos biológicos externos, sem "
        "identificar responsáveis políticos nem explicar a cadeia completa da Ruptura.",
    ),
    "codex.fragment.varzeas.s24.quarentena_sem_supervisao": FragmentPresentation(
        "Registro do posto lacrado",
        "Os registros indicam contenção biológica histórica, não punição moral. "
        "A observação não atribui culpa a Hemários modernos nem os trata como doença.",
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
    AchievementPresentation(
        "feat.nareth.primeiro_meridiano", "Primeiro Meridiano", "exploration",
        "Concluiu Linhas no Horizonte (P13).",
    ),
    AchievementPresentation(
        "feat.nareth.andarilho_de_nareth", "Andarilho de Nareth", "exploration",
        "Descobriu os cinco Locais principais e os cinco Braseiros permanentes de Nareth.",
        "Título · Andarilho de Nareth",
    ),
    AchievementPresentation(
        "feat.nareth.sob_o_mesmo_eixo", "Sob o Mesmo Eixo", "secrets",
        "Descobriu as Galerias do Meridiano e o Observatório Afundado.", hidden=True,
    ),
    AchievementPresentation(
        "feat.nareth.a_camara_se_cala", "A Câmara se Cala", "combat",
        "Derrotou o Arconte Invertido pela primeira vez.",
        "Título · Sobrevivente do Eixo",
    ),
    AchievementPresentation(
        "feat.nareth.o_que_retorna", "O Que Retorna", "pve",
        "Concluiu as Galerias do Meridiano em dificuldade Estável pela primeira vez.",
    ),
    AchievementPresentation(
        "feat.nareth.referencia_afundada", "Referência Afundada", "pve",
        "Concluiu o Observatório Afundado em dificuldade Estável pela primeira vez.",
    ),
    AchievementPresentation(
        "feat.nareth.eixos_fraturados", "Eixos Fraturados", "pve",
        "Concluiu as duas Masmorras de Nareth em dificuldade Fraturada.",
        "Moldura · Eixo Fraturado",
    ),
    AchievementPresentation(
        "feat.nareth.cacador_de_nareth", "Caçador de Nareth", "bestiary",
        "Dominou as nove criaturas-base de Nareth.", "Título · Caçador de Nareth",
    ),
    AchievementPresentation(
        "feat.nareth.horizonte_sem_norte", "Horizonte sem Norte", "secrets",
        "Dominou as criaturas de Nareth e descobriu cinco tipos de Variante.",
        "Aparência · Sobrevivente de Nareth", hidden=True,
    ),
    AchievementPresentation(
        "feat.nareth.a_medida_que_permanece", "A Medida que Permanece", "bestiary",
        "Estudou os cinco guardiões e referências regionais publicados.",
    ),
    AchievementPresentation(
        "feat.nareth.os_caminhos_que_nao_coincidem",
        "Os Caminhos que Não Coincidem", "secrets",
        "Concluiu S16 e S18 após reunir os trechos disponíveis de Rotas e Cartografia.",
        "Título · Sem Norte", hidden=True,
    ),
    AchievementPresentation(
        "feat.nareth.a_rede_mede_ainda", "A Rede Mede Ainda", "secrets",
        "Concluiu o Observatório Afundado em Estável após P18 e reuniu os registros disponíveis.",
        "Moldura · Meridiano Antigo", hidden=True,
    ),
    AchievementPresentation(
        "feat.nareth.planicies_de_nareth", "Planícies de Nareth", "exploration",
        "Concluiu P18 no Nv.30 e descobriu os cinco Locais principais.",
        "Moldura · Planícies de Nareth",
    ),
    AchievementPresentation(
        "feat.vde.o_berco_silencia", "O Berço Silencia", "combat",
        "Derrotou a Matriarca das Raízes pela primeira vez.",
        "Título · Sobrevivente do Berço",
    ),
    AchievementPresentation(
        "feat.vde.aquilo_que_pende",
        "Aquilo que Pende",
        "pve",
        "Concluiu o Fosso das Raízes em dificuldade Estável pela primeira vez.",
    ),
    AchievementPresentation(
        "feat.vde.sob_as_raizes", "Sob as Raízes", "secrets",
        "Descobriu o Fosso das Raízes e o Santuário do Nó Antigo.", hidden=True,
    ),
    AchievementPresentation(
        "feat.vde.o_no_antigo", "O Nó Antigo", "pve",
        "Concluiu o Santuário do Nó Antigo em dificuldade Estável pela primeira vez.",
    ),
    AchievementPresentation(
        "feat.vde.raizes_fraturadas", "Raízes Fraturadas", "pve",
        "Concluiu o Fosso e o Santuário em dificuldade Fraturada.",
        "Moldura · Raiz Fraturada",
    ),
    AchievementPresentation(
        "feat.vde.a_pedra_que_ainda_guarda", "A Pedra que Ainda Guarda", "bestiary",
        "Estudou o Vigia Enraizado, o Custódio, o Prelado e o Guardião do Nó Antigo.",
    ),
    AchievementPresentation(
        "feat.vde.vales_dos_enforcados", "Vales dos Enforcados", "exploration",
        "Concluiu a campanha dos Vales no Nv.20 e descobriu seus cinco Locais principais.",
        "Moldura · Vales dos Enforcados",
    ),
    AchievementPresentation(
        "feat.vde.a_rede_nao_dorme", "A Rede Não Dorme", "secrets",
        "Concluiu o Santuário após registrar os conhecimentos disponíveis sobre a rede.",
        "Moldura · Pedra Enlaçada", hidden=True,
    ),
    AchievementPresentation(
        "feat.vde.nomes_presos_madeira",
        "Nomes Presos à Madeira",
        "secrets",
        "Concluiu S10 e S12 após reunir os trechos disponíveis de Nomes dos Vales.",
        "Título · Nome Entalhado",
        hidden=True,
    ),
    AchievementPresentation(
        "feat.varzeas.agua_de_ferro",
        "Água de Ferro",
        "exploration",
        "Concluiu P19 — Águas de Ferro.",
    ),
    AchievementPresentation(
        "feat.varzeas.entre_os_diques",
        "Entre os Diques",
        "exploration",
        "Descobriu os resultados únicos publicados dos Diques Rubros.",
    ),
    AchievementPresentation(
        "feat.varzeas.o_pulso_sob_a_lama",
        "O Pulso sob a Lama",
        "exploration",
        "Concluiu P20 — O Pulso sob a Lama.",
    ),
    AchievementPresentation(
        "feat.varzeas.hortos_vazios",
        "Hortos Vazios",
        "exploration",
        "Concluiu P21 — Os Hortos Vazios.",
    ),
    AchievementPresentation(
        "feat.varzeas.nome_recuperado",
        "Nome Recuperado",
        "chronicles",
        "Registrou legitimamente Projeto Hemaris no Códice.",
    ),
    AchievementPresentation(
        "feat.varzeas.transferencia",
        "Transferência",
        "chronicles",
        "Concluiu P22 — Transferência.",
    ),
    AchievementPresentation(
        "feat.varzeas.sem_paciente",
        "Sem Paciente",
        "pve",
        "Concluiu a Enfermaria Afundada pela primeira vez em uma dificuldade elegível.",
    ),
    AchievementPresentation(
        "feat.varzeas.fluxo_contido",
        "Fluxo Contido",
        "pve",
        "Concluiu a Cisterna de Transferência pela primeira vez em uma dificuldade elegível.",
    ),
    AchievementPresentation(
        "feat.varzeas.persistencia_tem_preco",
        "Persistência tem Preço",
        "chronicles",
        "Concluiu P23 — O Custo da Persistência.",
    ),
    AchievementPresentation(
        "feat.varzeas.quarentena_encerrada",
        "Quarentena Encerrada",
        "pve",
        "Concluiu S24 — A Porta de Quarentena.",
    ),
    AchievementPresentation(
        "feat.varzeas.matriz_silenciada",
        "Matriz Silenciada",
        "combat",
        "Concluiu P24 — A Matriz Rubra.",
    ),
    AchievementPresentation(
        "feat.varzeas.naturalista_das_varzeas",
        "Naturalista das Várzeas",
        "bestiary",
        "Dominou o conhecimento das nove criaturas-base das Várzeas Carmesins.",
    ),
    AchievementPresentation(
        "feat.varzeas.cartografo_carmesim",
        "Cartógrafo Carmesim",
        "exploration",
        "Concluiu todos os resultados únicos de Desbravar das Várzeas Carmesins.",
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
NARETH_REGION_ID = "nareth"
NARETH_REGION_LABEL = "🌾 Planícies de Nareth · Nv. 21–30"
VARZEAS_REGION_ID = "varzeas"
VARZEAS_REGION_LABEL = "🥀 Várzeas Carmesins · Nv. 31–40"
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
    "vde.location.fosso_das_raizes": "Fosso das Raízes",
    "vde.location.santuario_do_no_antigo": "Santuário do Nó Antigo",
}
NARETH_LOCATIONS = {
    "nareth.location.campinas_do_meridiano": "Campinas do Meridiano",
    "nareth.location.posto_de_nareth": "Posto de Nareth",
    "nareth.location.canais_secos": "Canais Secos",
    "nareth.location.galerias_do_meridiano": "Galerias do Meridiano",
    "nareth.location.campos_invertidos": "Campos Invertidos",
    "nareth.location.observatorio_do_eixo": "Observatório do Eixo",
    "nareth.location.observatorio_afundado": "Observatório Afundado",
    "nareth.location.camara_do_arconte": "Câmara do Arconte",
}
VARZEAS_LOCATIONS = {
    "varzeas.location.diques_rubros": "Diques Rubros",
    "varzeas.location.porto_da_salmoura": "Porto da Salmoura",
    "varzeas.location.brejos_do_pulso": "Brejos do Pulso",
    "varzeas.location.hortos_hemaris": "Hortos Hemaris",
    "varzeas.location.galerias_transferencia": "Galerias de Transferência",
    "varzeas.location.cisterna_transferencia": "Cisterna de Transferência",
    "varzeas.location.enfermaria_afundada": "Enfermaria Afundada",
    "varzeas.location.camara_da_matriz": "Câmara da Matriz",
}
LOCATION_LABELS = TDO_LOCATIONS | VDE_LOCATIONS | NARETH_LOCATIONS | VARZEAS_LOCATIONS
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
    "Campinas do Meridiano": "nareth.location.campinas_do_meridiano",
    "Posto de Nareth": "nareth.location.posto_de_nareth",
    "Canais Secos": "nareth.location.canais_secos",
    "Galerias do Meridiano": "nareth.location.galerias_do_meridiano",
    "Campos Invertidos": "nareth.location.campos_invertidos",
    "Observatório do Eixo": "nareth.location.observatorio_do_eixo",
    "Observatório Afundado": "nareth.location.observatorio_afundado",
    "Câmara do Arconte": "nareth.location.camara_do_arconte",
    **{location_id: location_id for location_id in NARETH_LOCATIONS},
    "Diques Rubros": "varzeas.location.diques_rubros",
    "Porto da Salmoura": "varzeas.location.porto_da_salmoura",
    "Brejos do Pulso": "varzeas.location.brejos_do_pulso",
    "Galerias de Transferência": "varzeas.location.galerias_transferencia",
    "Cisterna de Transferência": "varzeas.location.cisterna_transferencia",
    "Enfermaria Afundada": "varzeas.location.enfermaria_afundada",
    "Câmara da Matriz": "varzeas.location.camara_da_matriz",
    **{location_id: location_id for location_id in VARZEAS_LOCATIONS},
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
    "material.vde.nucleo_fosso_raizes": "Núcleo do Fosso das Raízes",
    "material.vde.nucleo_no_antigo": "Núcleo do Nó Antigo",
    "material.nareth.bronze_de_marco": "Bronze de Marco",
    "material.nareth.couro_de_horizonte": "Couro de Horizonte",
    "material.nareth.erva_de_vento": "Erva de Vento",
    "material.nareth.po_de_eixo": "Pó de Eixo",
    "material.varzeas.ferro_de_salmoura": "Ferro de Salmoura",
    "material.varzeas.couro_de_varzea": "Couro de Várzea",
    "material.varzeas.junco_ferruginoso": "Junco Ferruginoso",
    "material.varzeas.soro_antigo": "Soro Antigo",
    "material.varzeas.catalisador_elite_iv": "Catalisador de Elite IV",
    "material.varzeas.fragmento_aprimoramento_iv": "Fragmento de Aprimoramento IV",
    "material.varzeas.nucleo_enfermaria_afundada": "Núcleo da Enfermaria Afundada",
    "material.varzeas.nucleo_cisterna_transferencia": "Núcleo da Cisterna de Transferência",
    "material.varzeas.nucleo_matriz_rubra": "Núcleo da Matriz Rubra",
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
    "galgo_meridiano": CreaturePresentation(
        NARETH_REGION_ID,
        ("nareth.location.campinas_do_meridiano", "nareth.location.canais_secos"),
    ),
    "abutre_marco": CreaturePresentation(
        NARETH_REGION_ID,
        ("nareth.location.campinas_do_meridiano", "nareth.location.canais_secos"),
    ),
    "errante_valas": CreaturePresentation(
        NARETH_REGION_ID,
        ("nareth.location.campinas_do_meridiano", "nareth.location.canais_secos"),
    ),
    "alfa_horizonte": CreaturePresentation(
        NARETH_REGION_ID,
        ("nareth.location.campinas_do_meridiano", "nareth.location.canais_secos"),
    ),
    "escaravelho_canal": CreaturePresentation(
        NARETH_REGION_ID,
        (
            "nareth.location.canais_secos",
            "nareth.location.campos_invertidos",
            "nareth.location.galerias_do_meridiano",
        ),
    ),
    "cervo_horizonte": CreaturePresentation(
        NARETH_REGION_ID,
        ("nareth.location.canais_secos", "nareth.location.campos_invertidos"),
    ),
    "serpe_campinas": CreaturePresentation(
        NARETH_REGION_ID, ("nareth.location.campos_invertidos",)
    ),
    "casco_invertido": CreaturePresentation(
        NARETH_REGION_ID,
        (
            "nareth.location.campos_invertidos",
            "nareth.location.observatorio_do_eixo",
            "nareth.location.galerias_do_meridiano",
            "nareth.location.observatorio_afundado",
        ),
    ),
    "mariposa_eixo": CreaturePresentation(
        NARETH_REGION_ID,
        ("nareth.location.campos_invertidos", "nareth.location.observatorio_do_eixo"),
    ),
    "vigia_meridiano": CreaturePresentation(
        NARETH_REGION_ID,
        (
            "nareth.location.observatorio_do_eixo",
            "nareth.location.observatorio_afundado",
        ),
    ),
    "serpe_eixo": CreaturePresentation(
        NARETH_REGION_ID,
        ("nareth.location.canais_secos", "nareth.location.campos_invertidos"),
    ),
    "custodio_invertido": CreaturePresentation(
        NARETH_REGION_ID,
        (
            "nareth.location.campos_invertidos",
            "nareth.location.observatorio_do_eixo",
        ),
    ),
    "custodio_sem_norte": CreaturePresentation(
        NARETH_REGION_ID, ("nareth.location.observatorio_do_eixo",)
    ),
    "cao_salmoura": CreaturePresentation(VARZEAS_REGION_ID, ("varzeas.location.diques_rubros",)),
    "garca_ferruginosa": CreaturePresentation(VARZEAS_REGION_ID, ("varzeas.location.diques_rubros",)),
    "portador_rubro": CreaturePresentation(VARZEAS_REGION_ID, ("varzeas.location.diques_rubros",)),
    "alfa_salmoura": CreaturePresentation(VARZEAS_REGION_ID, ("varzeas.location.diques_rubros",)),
    "aranha_junco": CreaturePresentation(
        VARZEAS_REGION_ID,
        ("varzeas.location.brejos_do_pulso", "varzeas.location.hortos_hemaris"),
    ),
    "cervo_ferrugem": CreaturePresentation(
        VARZEAS_REGION_ID,
        ("varzeas.location.brejos_do_pulso", "varzeas.location.hortos_hemaris"),
    ),
    "viuva_rubra": CreaturePresentation(
        VARZEAS_REGION_ID,
        ("varzeas.location.brejos_do_pulso", "varzeas.location.hortos_hemaris"),
    ),
    "lampreia_varzea": CreaturePresentation(VARZEAS_REGION_ID, ("varzeas.location.hortos_hemaris",)),
    "enxerto_horto": CreaturePresentation(VARZEAS_REGION_ID, ("varzeas.location.hortos_hemaris",)),
    "mariposa_soro": CreaturePresentation(VARZEAS_REGION_ID, ("varzeas.location.hortos_hemaris",)),
    "coletor_hematico": CreaturePresentation(VARZEAS_REGION_ID, ("varzeas.location.hortos_hemaris",)),
    "vigia_hemaris": CreaturePresentation(VARZEAS_REGION_ID, ("varzeas.location.galerias_transferencia",)),
    "arconte_invertido": CreaturePresentation(
        NARETH_REGION_ID, ("nareth.location.camara_do_arconte",)
    ),
    "escavador_eixo": CreaturePresentation(
        NARETH_REGION_ID, ("nareth.location.galerias_do_meridiano",)
    ),
    "o_que_retorna": CreaturePresentation(
        NARETH_REGION_ID, ("nareth.location.galerias_do_meridiano",)
    ),
    "custodio_meridiano": CreaturePresentation(
        NARETH_REGION_ID, ("nareth.location.observatorio_afundado",)
    ),
    "preceptor_eixo": CreaturePresentation(
        NARETH_REGION_ID, ("nareth.location.observatorio_afundado",)
    ),
    "guardiao_referencia": CreaturePresentation(
        NARETH_REGION_ID, ("nareth.location.observatorio_afundado",)
    ),
    "mariposa_breu_verde": CreaturePresentation(VDE_REGION_ID, ("vde.location.baixios_enredados",)),
    "viuva_cipos": CreaturePresentation(
        VDE_REGION_ID,
        ("vde.location.mata_suspensa", "vde.location.baixios_enredados"),
    ),
    "vigia_enraizado": CreaturePresentation(VDE_REGION_ID, ("vde.location.baixios_enredados",)),
    "carrasco_casca": CreaturePresentation(VDE_REGION_ID, ("vde.location.baixios_enredados",)),
    "tecela_fosso": CreaturePresentation(
        VDE_REGION_ID, ("vde.location.fosso_das_raizes",)
    ),
    "o_que_pende": CreaturePresentation(
        VDE_REGION_ID, ("vde.location.fosso_das_raizes",)
    ),
    "custodio_enredado": CreaturePresentation(
        VDE_REGION_ID, ("vde.location.santuario_do_no_antigo",)
    ),
    "prelado_enraizado": CreaturePresentation(
        VDE_REGION_ID, ("vde.location.santuario_do_no_antigo",)
    ),
    "guardiao_no_antigo": CreaturePresentation(
        VDE_REGION_ID, ("vde.location.santuario_do_no_antigo",)
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

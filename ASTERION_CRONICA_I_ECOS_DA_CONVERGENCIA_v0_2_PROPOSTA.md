# ASTERION — Crônica I · Ecos da Convergência
## Conteúdo da Crônica · v0.2 (proposta para aprovação)

> **Mudanças da v0.2:** cada capítulo passa a ter um **Encontro da Crônica** obrigatório (combate roteirizado); nova seção 11 com o bestiário próprio da Crônica: 4 criaturas, 2 Elites, 2 Chefes e 1 Chefe de Evento Mundial; pontos redistribuídos sem mudar o total de 250 por capítulo; nova fonte repetível de combate; Fase final, Códice, classificação e Dúvidas atualizados.

**Fontes:** GDD Estrutural v1.6.0 (regras e números: §5, §21, §33, §37.4, §49.13–49.17) · Bíblia Canônica v4.0.7 (lore, NPCs, travas de revelação) · seis Fontes Regionais FINAL (Locais, Masmorras, criaturas, gates).
**Regra deste documento:** nenhuma regra ou número das fontes foi alterado. Onde algo exige regra nova, aparece marcado como **PROPOSTA DE REGRA**. Pontos que as fontes não decidem estão em "Dúvidas para o autor", no fim.

> **Observação de versão:** o pedido cita a Bíblia v3.0, mas a versão anexada ao projeto é a **v4.0.7**, que substitui as anteriores. Este documento usa a v4.0.7.

---

## 0. Convenções

### 0.1 Calendário canônico

| ID | Momento | Quando |
|---|---|---|
| `cal_cr01_cap_01` | Capítulo 1 abre | D1 (lançamento) |
| `cal_cr01_cap_02` … `cal_cr01_cap_08` | Capítulos 2–8 abrem | D8, D15, D22, D29, D36, D43, D50 |
| `cal_cr01_voto_abre` | Votação abre | D50, junto com o Capítulo 8 (ver Dúvida 6) |
| `cal_cr01_voto_fecha` | Votação principal fecha + snapshot do eleitorado | T−48h (GDD §49.16) |
| `cal_cr01_runoff` | Runoff, se houver empate | 24h após o fechamento |
| `cal_cr01_fim` | `cycle_end_at` · epílogo publicado | T (fim da semana 8) |
| `cal_cr01_finalizacao` | Finalização real | T+2h |
| `cal_cr01_resgate_fim` | Fim do período de resgate e liquidação automática | T+14 dias |

Capítulos já liberados continuam jogáveis até o cutoff, o que permite catch-up dentro da Crônica (GDD §5.2).

### 0.2 Camadas de revelação (filtro de spoiler)

Todo texto da Crônica (resumo de capítulo, fala de NPC, Códice, voto, epílogo, Flavor) tem uma **versão base** segura para qualquer personagem e, quando indicado, **complementos de camada**. O jogador vê a base mais os complementos que seu `character_narrative_state` já permite. Isso é só filtragem de apresentação (GDD §3.4, §5, §37.4.3), não regra nova.

| Camada | Flag que libera | O texto pode nomear |
|---|---|---|
| **C0** | nenhuma | pulso, "estruturas antigas", inscrições, Custódios/Vigias, a palavra **CONVERGÊNCIA** apenas como inscrição sem significado, "a Sequência" (nome dado pelos registradores) |
| **C1** | P6 concluída | Âncora do Poente; existiram outras Âncoras |
| **C2** | P18 concluída | Âncoras estabilizavam o Véu e comparavam referências; Custódia das Âncoras |
| **H** | P24 concluída | Projeto Hemaris como programa médico/biológico (só no Capítulo 5) |
| **C3** | P29 concluída (P30 para "sabotagem") | Regência de Continuidade; objetivo da Convergência; Desvelados; sabotagem da Âncora Central (P30) |
| **C4** | P35 concluída | Avesso (P33); Âncora Central como nó (P34); a Noite da Convergência reconstruída |

Os nomes **Nó Central**, **Âncora Central**, **Regência**, **Desvelados**, **Hemaris** e **Avesso** nunca aparecem em texto base, em nome de Cosmético ou em título de Entrada visível a quem não tem a camada.

### 0.3 Adaptação regional

Definições usadas em todos os capítulos:

- **Região de Ressonância (RR):** a Região mais avançada com pelo menos um Local com acesso real (`unlock.location.*`) para o personagem.
- **Local de Ressonância (LR):** dentro de uma Região, o Local mais avançado com Desbravar já liberado pelos gates normais. Antes de P1 concluída não existe LR (ver Dúvida 4).
- **Hub de Ressonância (HR):** o hub da RR.
- **Região-foco:** a Região onde o capítulo acontece "de verdade".

Regras de conteúdo (dentro do GDD §5 "objetivos podem adaptar-se às Regiões já acessíveis"):

1. Se o personagem já acessou a Região-foco, o objetivo roda **em foco**, no LR daquela Região.
2. Se não acessou, o objetivo roda **em espelho**, no RR/LR/HR, com texto próprio que não nomeia nada que ele ainda não conhece.
3. Nada libera acesso antecipado. Estar em Grupo com alguém mais avançado não torna uma atividade elegível (Confins §2).
4. **Masmorra** é sempre opcional. Em foco: uma das 2 Masmorras da Região-foco com Estável liberada. Em espelho: qualquer Masmorra com Estável liberada. Se nenhuma estiver liberada, o objetivo aceita o **alternativo** `dsc_cr01_vestigio_profundo` (Desbravar no LR, mesmos pontos).
5. **Leituras** (evidência): ações contextuais "Examinar" em pontos fixos do Local (mesmo padrão dos três Pontos de Fuligem de P2). Custam 0 Vigor e 0 Coroas, dão 0 XP, não fazem roll e não geram economia. São flags de evidência, não itens de Inventário.
6. **Desbravar:** o objetivo acrescenta ao pool do Local um resultado narrativo da Crônica (`dsc_cr01_*`), elegível uma vez, com a proteção de 3 tentativas para conteúdo obrigatório (GDD §49.15). Por não conceder economia, não custa Vigor.
7. **Encontro da Crônica:** todo capítulo tem uma luta obrigatória contra uma criatura própria da Crônica. Diferente das investigações, o encontro **sempre acontece na RR do jogador**, no nível dele (o pulso alcança cada um onde está). Regras completas na seção 11.
8. **Evento Mundial:** vale a elegibilidade normal da ocorrência (≥2 fases + 8 Ações Significativas, GDD §49.15).
9. Narrativa e flags são por personagem. Pontos de Trilha são por `conta + servidor + Crônica`: um personagem recriado refaz a história, mas não gera os mesmos pontos de novo.

**NPCs por papel** (usados nos objetivos em espelho):

| Região | Hub | Coordenação | Registro | Herdeiro |
|---|---|---|---|---|
| Terras do Ocaso | Refúgio do Ocaso | Alda Veyr | Oren Cal | — |
| Vales dos Enforcados | Vigília do Vale | Dara Venn | Iven Raal | — |
| Planícies de Nareth | Posto de Nareth | Nera Voss | Talen Orm | — |
| Várzeas Carmesins | Porto da Salmoura | Sera Morn | Ilyan Korr | — |
| Altos Cinéreos | Abrigo do Peso | Rava Kern | Sel Ardan | Maro Keln |
| Confins do Véu | Último Refúgio | Sera Nol | Roven Pell | Eris Val |

Nenhum NPC muda de Região. Os Herdeiros chegam às outras Regiões só por cartas e cópias lidas pelo registrador local.

### 0.4 Pontos por capítulo

Cada capítulo: **250** pela conclusão (`cap_XX_conclusao`) + **250** divididos entre os objetivos. A conclusão exige os objetivos **obrigatórios** e uma cena final curta. Os opcionais só dão pontos. "Completar capítulo", para o voto, significa ter a conclusão registrada.

---

## 1. Premissa

**Texto de autor (não exibido ao jogador):** A Convergência foi a intervenção de sobrevivência com que a civilização asteriana tentou recalibrar a rede de Âncoras por meio de um acoplamento excepcional, coordenado pela Âncora Central. A sabotagem de uma ala dos Desvelados durante esse acoplamento, somada à decisão da Regência de prosseguir, desencadeou a falha em cascata que se tornou a Ruptura. A operação, porém, nunca terminou: foi interrompida no meio, e restos dos protocolos de coordenação, espalhados pelas estruturas regionais que ainda funcionam, guardaram uma última etapa à espera de uma confirmação que ninguém mais pode dar. Em *Ecos da Convergência*, essa etapa, que os registradores vão chamar de **Sequência Pendente**, desperta. Em todas as Regiões ao mesmo tempo, estruturas asterianas pulsam, referências se deslocam por instantes, Custódios interrompem suas rotinas e inscrições apagadas voltam a ser legíveis, repetindo uma palavra que para quase todos não significa nada: CONVERGÊNCIA. Braseiros não são afetados.

A Crônica é a investigação coletiva desse pulso, Região por Região, do Ocaso aos Confins, até a reconstrução da Sequência e a pergunta que ela impõe: o que fazer com o último pedaço de uma decisão antiga que nunca terminou. As quatro respostas possíveis ecoam posições históricas sem que o jogo declare qual está certa: conter o que não se entende (Selar), manter funcionando apesar do custo (Estabilizar), tornar o conhecimento comum (Entregar aos Herdeiros) e romper de vez com a rede (Destruir). Nenhuma delas cura o Véu, destrói o Avesso ou reabre a Ruptura (Bíblia §13; Confins §24). A tese continua a da Bíblia: ninguém escolhe destruir o mundo; escolhe-se sobreviver, e toda escolha tem um custo.

**Texto de abertura player-facing (C0), `txt_cr01_abertura`:**
> No mesmo instante, em todas as estradas, a pedra antiga estremeceu. Não houve desabamento nem fogo. Só um pulso seco, como um coração que não deveria existir. Nas inscrições apagadas, uma palavra voltou a aparecer, repetida: CONVERGÊNCIA. Ninguém sabe o que ela quer dizer.

---

## 2. Capítulos

### Capítulo 1 · `cap_01` — O Pulso
**Abre:** D1 · **Região-foco:** nenhuma; tudo acontece na RR de cada jogador.

**Resumo:** Em todas as Regiões, ao mesmo tempo, pedras antigas estremecem num pulso seco. Inscrições apagadas ficam legíveis por instantes, Custódios param a patrulha e marcos parecem apontar para outro lugar antes de voltar. Nos hubs, os registradores começam a comparar relatos. Uma palavra se repete: CONVERGÊNCIA.

**Adaptação:** como não há foco, todos jogam no próprio RR/LR/HR. Um jogador Nv.2 joga na Estrada das Cinzas; um Nv.55, nos Confins.

| ID | Objetivo | Tipo | Obrig. | Execução | Pontos |
|---|---|---|---|---|---|
| `cap_01_obj_01` | Relatar o Pulso | Falar com NPC | Sim | Registrador do HR | 50 |
| `cap_01_obj_02` | O Que a Pedra Repetiu | Explorar com Desbravar | Sim | `dsc_cr01_c01_pulso` no LR | 70 |
| `cap_01_obj_03` | Leituras do Pulso | Coletar evidência | Sim | 3 pontos `lei_cr01_c01_a/b/c` no LR | 60 |
| `cap_01_obj_04` | O Primeiro Eco | Derrotar (Encontro) | Sim | `enc_cr01_c01` contra **Repetidor** | 70 |
| | | | | **Total** | **250** |

**Encontro `enc_cr01_c01`:** durante um pulso, a matéria do chão se ergue numa forma humana sem rosto que repete um gesto de trabalho, e você está no caminho do gesto.

**Conclusão `cap_01_conclusao` (250):** o coordenador do HR decide tratar o pulso como risco de rota e pede que você acompanhe as próximas leituras.

---

### Capítulo 2 · `cap_02` — Pedras que Respondem
**Abre:** D8 · **Região-foco:** Terras do Ocaso.

**Resumo:** No Ocaso, o pulso ganha forma: a fuligem treme em linhas, marcas antigas vibram sem que ninguém as toque e, nas Ruínas, os Vigias trocam de rota a cada batida. Oren Cal compara cartas de outros registradores e descobre que o pulso volta em intervalos. E que em cada Região ele chega num momento um pouco diferente.

**Adaptação:** todo personagem tem acesso ao Ocaso, então a adaptação é por Local: o objetivo usa o LR do Ocaso. Quem tem C1 recebe a versão das Ruínas do Vigia/Câmara do Poente, com o complemento "o pulso é mais forte perto da Âncora do Poente". Veteranos voltam pela Travessia dos Braseiros.

| ID | Objetivo | Tipo | Obrig. | Execução | Pontos |
|---|---|---|---|---|---|
| `cap_02_obj_01` | Marcas que Vibram | Explorar com Desbravar | Sim | `dsc_cr01_c02_marcas` no LR do Ocaso | 60 |
| `cap_02_obj_02` | Quem Aponta | Derrotar (Encontro) | Sim | `enc_cr01_c02` contra **Marcador**, na RR do jogador | 70 |
| `cap_02_obj_03` | Cartas Cruzadas | Falar com NPC | Sim | Oren Cal | 50 |
| `cap_02_obj_04` | Sob as Pedras que Vigiam | Masmorra | Não | Galerias do Vigia ou Cripta do Ocaso; espelho/alternativo pela regra 0.3.4 | 70 |
| | | | | **Total** | **250** |

**Encontro `enc_cr01_c02`:** uma silhueta fina aponta sempre para o mesmo lado, mesmo quando o corpo gira. Depois de um pulso, passa a apontar para você.

**Conclusão `cap_02_conclusao` (250):** Alda Veyr manda marcar os horários de pulso nos registros de rota do Refúgio.

---

### Capítulo 3 · `cap_03` — Laços que se Tensionam
**Abre:** D15 · **Região-foco:** Vales dos Enforcados.

**Resumo:** Nos Vales, cada pulso contrai as raízes: cordas rangem, pontes torcem e a pedra do Claustro estala como madeira no frio. Dara Venn fecha travessias nos horários de pulso. Iven Raal cruza seus registros com os do Ocaso e confirma: o pulso não chega a todos ao mesmo tempo. Existe uma ordem.

**Adaptação (espelho):** uma carta da Vigília do Vale é lida pelo registrador do HR; Leituras e combates acontecem no RR. O texto espelho fala em "travessias distantes" sem descrever o Claustro.

| ID | Objetivo | Tipo | Obrig. | Execução | Pontos |
|---|---|---|---|---|---|
| `cap_03_obj_01` | Travessias Fechadas | Falar com NPC | Sim | Foco: Dara Venn · Espelho: coordenador do HR | 40 |
| `cap_03_obj_02` | A Ordem do Pulso | Coletar evidência | Sim | 3 pontos `lei_cr01_c03_*` no LR dos Vales (Claustro, se P10 concluída) · Espelho: LR | 70 |
| `cap_03_obj_03` | Onde as Raízes Descem | Masmorra | Não | Santuário do Nó Antigo ou Fosso das Raízes; regra 0.3.4 | 70 |
| `cap_03_obj_04` | O Posto Vazio | Derrotar (Encontro) | Sim | `enc_cr01_c03` contra **Guarda Repetida**, na RR do jogador | 70 |
| | | | | **Total** | **250** |

**Encontro `enc_cr01_c03`:** uma forma pesada assume a postura de um guarda antigo diante de um posto que não existe mais. Você entrou nele.

**Conclusão `cap_03_conclusao` (250):** Iven Raal (ou o registrador do HR) desenha a primeira tabela da ordem de chegada do pulso.

---

### Capítulo 4 · `cap_04` — Linhas que Discordam
**Abre:** D22 · **Região-foco:** Planícies de Nareth.

**Resumo:** Nas Planícies, durante cada pulso, todos os marcos apontam para o mesmo lado e depois voltam. Talen Orm mede o desvio e publica a correção com o próprio nome. Nera Voss suspende caravanas nos horários de pulso. Somando as leituras de três Regiões, os registradores chegam a uma conclusão incômoda: o pulso tem direção.

**Complemento C2:** para quem sabe o que as Âncoras faziam, o desvio parece uma comparação de referências que não recebe resposta.

**Adaptação (espelho):** os marcos e sombras do LR do jogador mostram um desvio menor; o registrador do HR recebe o mapa de Talen Orm por carta.

| ID | Objetivo | Tipo | Obrig. | Execução | Pontos |
|---|---|---|---|---|---|
| `cap_04_obj_01` | Marcos que Apontam | Explorar com Desbravar | Sim | `dsc_cr01_c04_marcos` no LR de Nareth (Observatório do Eixo, se liberado) · Espelho: LR | 50 |
| `cap_04_obj_02` | A Correção Publicada | Falar com NPC | Sim | Foco: Talen Orm · Espelho: registrador do HR | 50 |
| `cap_04_obj_03` | Ressonância | Evento Mundial | Não | Elegibilidade em ocorrência de `evt_cr01_ressonancia` (versão acessível), contra **O Compasso** | 60 |
| `cap_04_obj_04` | Fim de Turno | Derrotar (Chefe) | Sim | `enc_cr01_c04` contra o Chefe **Mestre de Turno**, na RR do jogador (exige Nv.5) | 90 |
| | | | | **Total** | **250** |

**Encontro `enc_cr01_c04` · Chefe intermediário:** no pulso mais longo até agora, uma forma grande ergue o braço num gesto de ordem, e formas menores se montam ao redor para obedecer. Ela dá ordens a quem já não está aqui, e eles ainda obedecem.

**Conclusão `cap_04_conclusao` (250):** o mapa conjunto dos registradores mostra o pulso vindo "de muito além das Planícies".

---

### Capítulo 5 · `cap_05` — Compasso sob a Água
**Abre:** D29 · **Região-foco:** Várzeas Carmesins.

**Resumo:** Nas Várzeas, o pulso antigo encontra o pulso dos Brejos e os dois entram em compasso. Válvulas antigas se movem a cada batida. Sera Morn isola canais e Niva Sol testa a água antes de liberar qualquer rota. Ilyan Korr encontra, em registros de manutenção, o pulso descrito como "sinal de confirmação".

**Complemento H:** os protocolos que ainda operam nas instalações Hemaris reagem como se aguardassem instrução de fora. Isso não diz nada sobre os Hemários de hoje.

**Adaptação (espelho):** o compasso aparece como água e umidade reagindo ao pulso no LR do jogador; Ilyan Korr não é citado, e o registrador do HR lê só a expressão "sinal de confirmação" numa cópia.

| ID | Objetivo | Tipo | Obrig. | Execução | Pontos |
|---|---|---|---|---|---|
| `cap_05_obj_01` | Antes de Liberar a Água | Falar com NPC | Sim | Foco: Sera Morn · Espelho: coordenador do HR | 50 |
| `cap_05_obj_02` | Compasso | Coletar evidência | Sim | 4 pontos `lei_cr01_c05_*` no LR das Várzeas (Galerias de Transferência, se liberadas) · Espelho: LR | 70 |
| `cap_05_obj_03` | O Peso que Ninguém Vê | Derrotar (Encontro) | Sim | `enc_cr01_c05` contra **Carregador Repetido**, na RR do jogador | 70 |
| `cap_05_obj_04` | O Que Ainda Bombeia | Masmorra | Não | Cisterna de Transferência ou Enfermaria Afundada; regra 0.3.4 | 60 |
| | | | | **Total** | **250** |

**Encontro `enc_cr01_c05`:** uma forma curvada carrega há muito tempo algo que ninguém vê. No pulso, ela larga a carga em cima de você.

**Conclusão `cap_05_conclusao` (250):** os registradores passam a chamar o conjunto dos pulsos de "a Sequência", porque ela parece pedir algo, passo a passo.

---

### Capítulo 6 · `cap_06` — Ordens sem Data
**Abre:** D36 · **Região-foco:** Altos Cinéreos.

**Resumo:** Nos Altos, uma ordem antiga gravada na Bastilha passa a se repetir a cada pulso, pedindo uma confirmação que ninguém sabe dar. Sel Ardan registra o comando sem data. Maro Keln reconhece nele o formato das instituições antigas, e Rava Kern proíbe que alguém tente "obedecer". Os Herdeiros propõem reunir as Leituras de todas as Regiões num único registro.

**Complemento C3:** a ordem é uma etapa da Convergência interrompida na noite da Ruptura.

**Adaptação (espelho):** uma cópia da ordem chega ao HR por carta dos Herdeiros, "estudiosos que guardam e comparam registros antigos". O registrador a lê em voz baixa: é uma pergunta à espera de resposta.

| ID | Objetivo | Tipo | Obrig. | Execução | Pontos |
|---|---|---|---|---|---|
| `cap_06_obj_01` | A Ordem sem Data | Falar com NPC | Sim | Foco: Sel Ardan · Espelho: registrador do HR | 50 |
| `cap_06_obj_02` | Ecos da Bastilha | Explorar com Desbravar | Sim | `dsc_cr01_c06_ordem` no LR dos Altos (Bastilha de Carga, se liberada) · Espelho: LR | 60 |
| `cap_06_obj_03` | Prioridades Incompatíveis | Masmorra | Não | Bastilha Profunda ou Pedreira do Contrapeso; regra 0.3.4 | 60 |
| `cap_06_obj_04` | Fila sem Fim | Derrotar (Elite) | Sim | `enc_cr01_c06` contra a Elite **Multidão Repetida**, na RR do jogador (exige Nv.3) | 80 |
| | | | | **Total** | **250** |

**Encontro `enc_cr01_c06` · Elite:** seis a oito formas humanas fundidas ombro a ombro, como uma fila de trabalhadores que se colou, cada uma repetindo um gesto diferente. No pulso, todas as bocas que não têm se abrem ao mesmo tempo.

**Conclusão `cap_06_conclusao` (250):** em foco, Maro Keln pede que as Leituras sigam para os Confins; em espelho, o registrador do HR envia as suas aos Herdeiros.

---

### Capítulo 7 · `cap_07` — A Etapa Pendente
**Abre:** D43 · **Região-foco:** Confins do Véu.

**Resumo:** Nos Confins, o pulso não chega de longe: parte dali. As referências de todas as Regiões convergem para um mesmo ponto, e uma sequência antiga tenta completar sua última etapa sem nunca receber confirmação. Sera Nol exige dupla testemunha de cada leitura; Roven Pell registra versões incompatíveis; Eris Val ajuda a reunir a Sequência Pendente. O pulso cresce até ser sentido no mundo inteiro.

**Complemento C4:** a origem está no Nó Central; a etapa pendente é o último passo de coordenação que nunca foi confirmado.

**Adaptação (espelho):** o registrador do HR recebe dos Herdeiros a Sequência reunida, e o pulso mais forte até agora atravessa a Região. O texto não diz de onde o pulso parte.

| ID | Objetivo | Tipo | Obrig. | Execução | Pontos |
|---|---|---|---|---|---|
| `cap_07_obj_01` | Dupla Testemunha | Coletar evidência | Sim | 4 pares de pontos `lei_cr01_c07_*` (cada Leitura confirmada em 2 pontos) no LR dos Confins · Espelho: LR | 60 |
| `cap_07_obj_02` | Registrar a Sequência | Falar com NPC | Sim | Foco: Roven Pell · Espelho: registrador do HR | 50 |
| `cap_07_obj_03` | O Registro que Risca | Derrotar (Elite) | Sim | `enc_cr01_c07` contra a Elite **Escriba Repetido**, na RR do jogador (exige Nv.3) | 80 |
| `cap_07_obj_04` | Ressonância Plena ★ | Evento Mundial | Não | Elegibilidade em ocorrência de `evt_cr01_ressonancia_plena`, contra **O Compasso** | 60 |
| | | | | **Total** | **250** |

★ = objetivo da fase final.

**Encontro `enc_cr01_c07` · Elite:** uma figura curvada sobre uma prancha que não existe risca o ar com dedos longos demais. Cada traço deixa a mesma palavra incompleta no chão, na pedra e em quem estiver perto.

**Conclusão `cap_07_conclusao` (250):** a Sequência Pendente está completa nos registros. Falta decidir o que fazer com ela.

---

### Capítulo 8 · `cap_08` — A Resposta
**Abre:** D50 · **Região-foco:** nenhuma; tudo acontece na RR de cada jogador.

**Resumo:** A Sequência está reunida e os pulsos ficam mais frequentes enquanto ninguém responde. Em cada hub, coordenadores e registradores ouvem testemunhos e apresentam quatro respostas: Selar, Estabilizar, Entregar aos Herdeiros, Destruir. A decisão será de quem acompanhou o Eco até aqui.

**Adaptação:** igual ao Capítulo 1.

| ID | Objetivo | Tipo | Obrig. | Execução | Pontos |
|---|---|---|---|---|---|
| `cap_08_obj_01` | Testemunho ★ | Falar com NPC | Sim | Coordenador do HR | 50 |
| `cap_08_obj_02` | A Última Leitura ★ | Explorar com Desbravar | Sim | `dsc_cr01_c08_ultima_leitura` no LR | 50 |
| `cap_08_obj_03` | Ressonância Plena ★ | Evento Mundial | Não | `evt_cr01_ressonancia_plena`, ocorrência diferente da usada em `cap_07_obj_04` | 50 |
| `cap_08_obj_04` | Sem Resposta ★ | Derrotar (Chefe) | Sim | `enc_cr01_c08` contra o Chefe final **O Que Aguarda Resposta**, na RR do jogador (exige Nv.5) | 100 |
| | | | | **Total** | **250** |

**Encontro `enc_cr01_c08` · Chefe final:** no pulso mais forte de todos, uma figura imensa se monta ajoelhada, oferecendo com os dois braços uma placa lisa a quem chega. Quando ninguém a pega, ela se levanta. Vencê-la cala o pulso por tempo suficiente para que o mundo responda.

**Conclusão `cap_08_conclusao` (250):** cena "Antes da Resposta", que apresenta as quatro opções. Votar **não** é exigido para concluir o capítulo.

---

## 3. Fase final

| ID | Objetivo | Acessível a | Disponível desde |
|---|---|---|---|
| `cap_07_obj_04` | Ressonância Plena (Evento Mundial) | quem alcança uma versão acessível do Evento | D43 |
| `cap_08_obj_01` | Testemunho (falar com NPC) | **todos** (qualquer HR) | D50 |
| `cap_08_obj_02` | A Última Leitura (Desbravar) | todos com LR | D50 |
| `cap_08_obj_03` | Ressonância Plena (Evento Mundial) | quem alcança uma versão acessível do Evento | D50 |
| `cap_08_obj_04` | Sem Resposta (Chefe final) | todos com Nv.5+ | D50 |

**Elegibilidade ao voto (GDD §5.1, sem alteração):** conclusão registrada em pelo menos **4 de 8** capítulos + pelo menos **1** objetivo desta tabela. `cap_08_obj_01` garante que nenhum jogador fique sem acesso à fase final por nível ou horário.

---

## 4. Voto final

Regras do GDD §5.1 mantidas: 1 voto ativo por `conta + servidor + Crônica`, alterável até o fechamento, idempotente; snapshot do eleitorado no fechamento; runoff de 24h só entre as empatadas e só para o eleitorado congelado.

**Apresentação:** cada opção mostra o texto base para todos e, logo abaixo, o complemento das camadas que o jogador já tem. Todas as opções têm o mesmo tamanho aproximado e citam o custo. Rodapé comum: *"Nenhuma resposta cura o mundo. Todas custam algo."*

**Consequência de todas as opções:** por padrão, **só narrativa e apresentação**. O resultado grava `world_state.cr01_desfecho` (versionado e idempotente, GDD §3.4) e muda: Entrada de Códice do desfecho, Flavor Text dos hubs e Locais afetados e falas pós-Crônica dos NPCs. Isso está dentro das regras atuais. Consequências de jogo estão separadas em 4.5 como **PROPOSTA DE REGRA**.

### 4.1 Selar · `voto_cr01_selar`

**Apresentação (base):**
> Isolar cada ponto onde o pulso nasce e lacrar a Sequência onde ela está. Os pulsos devem cessar. O que está escrito nela continuará ali, inteiro e ilegível: ninguém poderá lê-la, usá-la ou desfazê-la sem antes romper o selo. **Custo:** escolhemos não saber, e confiamos que o selo dure mais do que a pergunta.

**Complemento C3:** Selar guarda a última etapa da Convergência sem confirmá-la nem apagá-la, como a Custódia mantinha o que não podia resolver.

**Epílogo `epilogo_cr01_selar`:**
> Em cada Região, mantenedores e registradores fecham os pontos de pulso com o que têm: cunhas, cordas, lacres, pedra nova sobre pedra antiga. Em poucas semanas, o silêncio volta. As inscrições se apagam outra vez. Alda Veyr manda tirar os horários de pulso dos registros de rota. Oren Cal escreve na margem: "Selamos o que não entendemos. Espero que isso tenha sido prudência."
>
> *Complemento C3:* a etapa pendente continua intacta e inerte, à espera de uma confirmação que agora ninguém pode dar. O Véu continua tão frágil quanto antes.

`world_state.cr01_desfecho = selar` · **Só narrativa/apresentação.**

### 4.2 Estabilizar · `voto_cr01_estabilizar`

**Apresentação (base):**
> Aprender o ritmo do pulso e mantê-lo sob controle, ponto por ponto, para que as estruturas antigas ajudem a conferir rotas, marcos e pontes em vez de desorientá-las. A Sequência continua ativa, mas contida. **Custo:** quem mantém o ritmo passa a depender dele, e alguém sempre carrega mais peso que os outros.

**Complemento C3:** Estabilizar mantém viva uma parte da rede sem completar a Convergência, e traz de volta a dependência e a carga desigual que os antigos conheceram.

**Epílogo `epilogo_cr01_estabilizar`:**
> Os pulsos ficam regulares. Em Nareth, os marcos passam a ser conferidos a cada batida; nos Altos, as pontes são ajustadas no mesmo compasso; nos Vales, as travessias abrem e fecham por horário. O mundo fica um pouco mais previsível. Rava Kern pergunta, em voz alta, quem vai carregar o custo no dia em que o ritmo falhar. Ninguém responde.
>
> *Complemento C3:* a Sequência segue rodando em modo local e nunca chega à última etapa. É o mesmo pacto das Âncoras: tempo comprado, dependência criada.

`world_state.cr01_desfecho = estabilizar` · **Só narrativa/apresentação.**

### 4.3 Entregar aos Herdeiros · `voto_cr01_herdeiros`

**Apresentação (base):**
> Confiar a Sequência reunida aos Herdeiros, estudiosos que guardam e comparam registros antigos, para que a estudem, copiem e expliquem antes que alguém aja sobre ela. Os pulsos continuam por enquanto. **Custo:** a decisão fica adiada, e a chave inteira fica nas mãos de poucos, por mais honestos que sejam.

**Complemento C3:** Entregar torna comum o conhecimento que o segredo dos antigos escondeu, e repete o risco de concentrar em poucos uma decisão que afeta todos.

**Epílogo `epilogo_cr01_herdeiros`:**
> Cópias parciais da Sequência chegam a cada hub e ficam com os registradores, para quem quiser ler. Os Herdeiros guardam o registro completo e prometem explicar antes de decidir. Os pulsos continuam, mais fracos, e cada um é anotado. Nos Confins, Sera Nol exige que toda cópia tenha dupla testemunha. Nos Altos, alguém grava numa parede: "Quem guarda a chave?"
>
> *Complemento C3:* o Arquivo Comum dos antigos fazia isso: integrava registros para muitos. A Regência também guardou o essencial para poucos.

`world_state.cr01_desfecho = herdeiros` · **Só narrativa/apresentação.**

### 4.4 Destruir · `voto_cr01_destruir`

**Apresentação (base):**
> Desmontar os pontos de pulso e romper a Sequência para sempre. Os pulsos acabam. Nada do que estava registrado nela poderá ser lido, usado ou repetido. **Custo:** perdemos de vez uma pergunta que ninguém respondeu, e qualquer chance de entender o que ela pedia.

**Complemento C3:** Destruir encerra definitivamente a última etapa da Convergência. Foi o que uma ala dos Desvelados quis um dia; os motivos de hoje não precisam ser os mesmos.

**Epílogo `epilogo_cr01_destruir`:**
> Com martelo, alavanca e paciência, os pontos de pulso são desmontados. O último pulso é sentido em todas as Regiões ao mesmo tempo, como o primeiro. Depois, nada. Algumas inscrições racham e nunca mais serão lidas. Torren Vhal guarda uma das peças retiradas, sem saber para quê. Iven Raal registra a data e uma frase: "Esta pergunta não será respondida."
>
> *Complemento C4:* a Âncora Central não volta a receber pedido algum desta Sequência. O Véu continua deteriorando como sempre; o Avesso continua existindo. Destruir não é reparar.

`world_state.cr01_desfecho = destruir` · **Só narrativa/apresentação.**

### 4.5 Consequências de jogo (opcionais)

**PROPOSTA DE REGRA `pr_cr01_eco_residual` — Eco Residual com paridade.**
Depois da Crônica, o desfecho escolhe uma variante de um único Evento Mundial persistente na rotação normal: `evt_cr01_residual_selar` (manutenção dos lacres), `_estabilizar` (manutenção do ritmo), `_herdeiros` (escolta de cópias), `_destruir` (remoção dos restos). Em `em_espera`, nenhuma variante entra. Todas usam a economia padrão de Evento Mundial (GDD §49.15), sem recompensa exclusiva.
*Por que é regra nova:* o GDD não diz se um resultado de voto pode alterar a rotação de atividades do mundo. Seria preciso garantir em regra que nenhum desfecho dê vantagem econômica ou de poder, para o voto não virar decisão de farm. Os kits de combate das variantes também exigiriam Balanceamento.

**PROPOSTA DE REGRA `pr_cr01_feito_resposta` — Feito de participação.**
Feito **Respondeu ao Eco** (categoria Crônicas, sem Cosmético) para quem tiver voto válido no snapshot, qualquer que seja a opção.
*Por que é regra nova:* o GDD não define se votar pode gerar Feito. A recompensa precisa ser idêntica para todas as opções.

Se nenhuma proposta for aprovada, o desfecho continua só narrativo e o documento permanece válido.

---

## 5. Desfecho neutro predefinido · `epilogo_cr01_em_espera`

Aplica-se automaticamente se o runoff terminar em empate exato (GDD §5.1). Texto publicado nas regras da Crônica desde o D1.

> Ninguém chegou a uma resposta. Então a Sequência fez o que sempre tinha feito: esperou. Sem confirmação, os pulsos foram rareando até quase sumir. Nada foi selado, mantido, entregue ou destruído. Os registradores de todas as Regiões anotaram a mesma data e a mesma frase: "A pergunta continua aberta."
>
> *Complemento C3:* como tantos protocolos antigos, a última etapa da Convergência voltou a aguardar uma autorização que talvez nunca venha.

`world_state.cr01_desfecho = em_espera` · Só narrativa/apresentação. Deixa a questão aberta para uma Crônica futura sem prometer nada.

---

## 6. Entradas do Códice

Todas respeitam o GDD §33.2: sem contador, sem título antecipado, sem `???`. Complementos de camada são Trechos separados, liberados só com a flag correspondente.

### 6.1 Entrada contínua

**`codex_cr01_ecos` · Crônicas · "Ecos da Convergência"** — recebe um Trecho por conclusão de capítulo.

| Trecho | Liberado por | Texto |
|---|---|---|
| `codex_cr01_ecos_t01` | `cap_01_conclusao` | No primeiro dia, estruturas antigas pulsaram ao mesmo tempo em todas as Regiões. Os registradores chamaram o fenômeno de Eco, por falta de nome melhor. |
| `codex_cr01_ecos_t02` | `cap_02_conclusao` | O pulso volta em intervalos, e não chega a todas as Regiões no mesmo momento. |
| `codex_cr01_ecos_t03` | `cap_03_conclusao` | Comparando horários, os registradores encontraram uma ordem de chegada. |
| `codex_cr01_ecos_t04` | `cap_04_conclusao` | O pulso tem direção: vem de muito além das Planícies. |
| `codex_cr01_ecos_t05` | `cap_05_conclusao` | Registros antigos chamam o pulso de "sinal de confirmação". Os registradores passaram a chamá-lo de a Sequência. |
| `codex_cr01_ecos_t06` | `cap_06_conclusao` | Uma ordem sem data repete-se a cada pulso, pedindo confirmação. As Leituras foram reunidas. |
| `codex_cr01_ecos_t07` | `cap_07_conclusao` | A Sequência Pendente está completa nos registros: uma última etapa que nunca recebeu resposta. |
| `codex_cr01_ecos_t08` | `cap_08_conclusao` | Quatro respostas foram apresentadas ao mundo: Selar, Estabilizar, Entregar aos Herdeiros, Destruir. |

### 6.2 Entradas por capítulo

| ID | Cap. | Categoria | Título | Texto base | Trecho de camada |
|---|---|---|---|---|---|
| `codex_cr01_o_pulso` | 1 | Mistérios e Fenômenos | O Pulso | Um tremor seco na pedra antiga, sem desabamento nem fogo. Dura um instante. Braseiros não reagem. | `_c1`: Em Ocaso, o pulso é mais forte perto da Âncora do Poente. |
| `codex_cr01_formas_do_pulso` | 1 | Mistérios e Fenômenos | Formas do Pulso | Durante o pulso, a matéria do lugar se ergue em formas que repetem gestos de gente que não está ali. Não falam, não sangram e se desfazem quando derrotadas. Ninguém sabe o que são. | `_c4`: Talvez sejam estados que a Sequência ainda guarda, e não criaturas. O Códice não confirma. |
| `codex_cr01_marcas_que_vibram` | 2 | Regiões e Locais | Marcas que Vibram | No Ocaso, marcas e inscrições vibram a cada pulso, e os Vigias das Ruínas mudam de rota até o pulso passar. | — |
| `codex_cr01_ordem_do_pulso` | 3 | Mistérios e Fenômenos | A Ordem do Pulso | O pulso chega às Regiões em sequência, sempre na mesma ordem. Nos Vales, as raízes se contraem a cada batida. | — |
| `codex_cr01_direcao_do_pulso` | 4 | Mistérios e Fenômenos | A Direção do Pulso | Durante o pulso, marcos de Nareth apontam para o mesmo lado. Talen Orm publicou a medição com o próprio nome. | `_c2`: O desvio lembra a comparação de referências que as Âncoras faziam, sem resposta do outro lado. |
| `codex_cr01_sinal_de_confirmacao` | 5 | História e Acontecimentos | Sinal de Confirmação | Registros de manutenção das Várzeas descrevem o pulso como um sinal que pede confirmação. | `_h`: Protocolos das instalações Hemaris reagem ao pulso como se aguardassem instrução externa. |
| `codex_cr01_ordem_sem_data` | 6 | História e Acontecimentos | A Ordem sem Data | Uma ordem antiga repete-se a cada pulso. Não tem data nem autor, e pede uma confirmação que ninguém sabe dar. | `_c3`: A ordem pertence à Convergência, interrompida na noite da Ruptura. |
| `codex_cr01_herdeiros` | 6 | Povos e Facções | Os Herdeiros | Estudiosos que guardam e comparam registros antigos. Pediram que as Leituras de todas as Regiões fossem reunidas. | `_altos`: Maro Keln é um deles. · `_confins`: Eris Val também. |
| `codex_cr01_sequencia_pendente` | 7 | Crônicas | A Sequência Pendente | Reunidas, as Leituras formam uma sequência antiga que tenta completar sua última etapa, e nunca consegue. | `_c3`: É a etapa final da Convergência. · `_c4`: O pedido parte do Nó Central e nunca foi confirmado. |
| `codex_cr01_quatro_respostas` | 8 | Crônicas | As Quatro Respostas | Selar, Estabilizar, Entregar aos Herdeiros ou Destruir. Nenhuma cura o mundo; todas custam algo. | — |
| `codex_cr01_desfecho` | fim | Crônicas | O Que Foi Respondido | Um único Trecho conforme `world_state.cr01_desfecho`: `_selar`, `_estabilizar`, `_herdeiros`, `_destruir` ou `_em_espera`, com o texto base do epílogo correspondente. | Complementos C3/C4 do epílogo. |

---

## 7. Trilha da Crônica

Marco N exige N × 100 pontos (máximo 4.000; GDD §49.16).

### 7.1 Marcos Livres (pares)

| Marco | Pontos | Recompensa | ID |
|---|---|---|---|
| 2 | 200 | 250 Coroas | `trilha_cr01_livre_m02` |
| 4 | 400 | 3 materiais básicos vinculados | `trilha_cr01_livre_m04` |
| 6 | 600 | 2 Fragmentos vinculados | `trilha_cr01_livre_m06` |
| 8 | 800 | Título **Ouvinte dos Ecos** | `trilha_cr01_livre_m08` |
| 10 | 1.000 | 300 Coroas + 3 básicos | `trilha_cr01_livre_m10` |
| 12 | 1.200 | 2 Fragmentos + 3 básicos | `trilha_cr01_livre_m12` |
| 14 | 1.400 | 350 Coroas | `trilha_cr01_livre_m14` |
| 16 | 1.600 | 3 básicos + 2 Fragmentos | `trilha_cr01_livre_m16` |
| 18 | 1.800 | 400 Coroas | `trilha_cr01_livre_m18` |
| 20 | 2.000 | Moldura **do Pulso** + 2 Fragmentos | `trilha_cr01_livre_m20` |
| 22 | 2.200 | 450 Coroas + 3 básicos | `trilha_cr01_livre_m22` |
| 24 | 2.400 | 3 Fragmentos + 3 básicos | `trilha_cr01_livre_m24` |
| 26 | 2.600 | 500 Coroas | `trilha_cr01_livre_m26` |
| 28 | 2.800 | Título **Testemunha da Convergência** + 3 básicos | `trilha_cr01_livre_m28` |
| 30 | 3.000 | 550 Coroas + 2 Fragmentos | `trilha_cr01_livre_m30` |
| 32 | 3.200 | 3 básicos + 3 Fragmentos | `trilha_cr01_livre_m32` |
| 34 | 3.400 | 600 Coroas + 3 básicos | `trilha_cr01_livre_m34` |
| 36 | 3.600 | Moldura **das Leituras Cruzadas** + 2 Fragmentos | `trilha_cr01_livre_m36` |
| 38 | 3.800 | 700 Coroas + 3 básicos | `trilha_cr01_livre_m38` |
| 40 | 4.000 | Aparência **Manto de Quem Respondeu** + 900 Coroas + 2 Fragmentos | `trilha_cr01_livre_m40` |
| **Total** | | **5.000 Coroas · 30 básicos · 20 Fragmentos · 5 não econômicas** (2 Títulos, 2 Molduras, 1 Aparência) | |

Cosméticos Livres:

| ID | Tipo | Nome | Descrição |
|---|---|---|---|
| `cos_cr01_titulo_ouvinte_dos_ecos` | Título | Ouvinte dos Ecos | Para quem prestou atenção quando a pedra falou. |
| `cos_cr01_moldura_do_pulso` | Moldura | Moldura do Pulso | Couro escuro e ferro fosco nas laterais, com marcas de entalhe em intervalos regulares, como horários anotados à faca. |
| `cos_cr01_titulo_testemunha_convergencia` | Título | Testemunha da Convergência | Esteve presente quando a palavra voltou às pedras. |
| `cos_cr01_moldura_leituras_cruzadas` | Moldura | Moldura das Leituras Cruzadas | Laterais de madeira e pedra cruzadas por cordões de registro e plaquetas de leitura gastas. |
| `cos_cr01_aparencia_quem_respondeu` | Aparência | Manto de Quem Respondeu | Manto longo de viagem sobre camadas de estrada, com um estojo de registros ao peito e lacres partidos pendurados no cinto. |

### 7.2 Marcos Premium (múltiplos de 4) — só cosmético e prestígio

| Marco | Tipo | Nome | Descrição | ID |
|---|---|---|---|---|
| 4 | Título | Contador de Pulsos | Sabe de cor quanto tempo há entre uma batida e outra. | `cos_cr01_titulo_contador_de_pulsos` |
| 8 | Moldura | Moldura do Marco Gasto | Pedra e ferro com riscos de medição quase apagados, faixa simples no topo e na base. | `cos_cr01_moldura_marco_gasto` |
| 12 | Título | Que Seguiu o Eco | Atravessou estradas atrás de um som que ninguém explicava. | `cos_cr01_titulo_que_seguiu_o_eco` |
| 16 | Aparência | Vestes do Itinerante dos Ecos | Capa curta impermeabilizada, camadas reparadas, cordas de leitura e placas de anotação presas ao corpo. | `cos_cr01_aparencia_itinerante_ecos` |
| 20 | Título | Leitor de Inscrições Mudas | Lê o que a pedra disse antes de voltar a calar. | `cos_cr01_titulo_leitor_inscricoes` |
| 24 | Moldura | Moldura das Seis Estradas | Laterais em seis faixas de material, uma por Região: pedra fuliginosa, madeira de raiz, marco de linha, ferro salobro, basalto e pedra pálida. | `cos_cr01_moldura_seis_estradas` |
| 28 | Título | Voz entre os Ecos | Falou quando todos só escutavam. | `cos_cr01_titulo_voz_entre_ecos` |
| 32 | Aparência | Traje do Registrador de Campo | Sobrecamadas estreitas de tecido encerado, estojos de carvão e cera, lenço contra pó e luvas de dedos livres. | `cos_cr01_aparencia_registrador_campo` |
| 36 | Moldura | Moldura da Sequência Interrompida | Ferro gasto com uma fileira de entalhes regulares que para no meio, sem terminar. | `cos_cr01_moldura_sequencia_interrompida` |
| 40 | Aparência | Manto da Última Leitura | Manto pesado e escuro, com lacres, cordões de registro e uma placa de leitura rachada presa ao ombro. | `cos_cr01_aparencia_ultima_leitura` |

Regras de produção dos Cosméticos (Autoridade Visual): Molduras de material gasto, sem brilho, sem gema emissiva, sem ouro polido; Aparências de corpo inteiro, acomodando chifres Hemários e orelhas Veladas/Alvoranas sem exibi-los como ornamento; nenhum nome ou arte com conteúdo de camada C1+.

---

## 8. Atividades repetíveis da Trilha

Cada conclusão vale **25 pontos**, com o teto acumulado do GDD §49.16: **150 × semanas liberadas**, máximo **1.200** (6 conclusões por semana). Oportunidade total: 4.000 únicos + 1.200 repetíveis = 5.200.

| ID | Fonte | O que conta | Chave idempotente | Limite de conteúdo |
|---|---|---|---|---|
| `rep_cr01_masmorra` | Masmorra | Conclusão válida de run em qualquer das 12 Masmorras, qualquer dificuldade, para cada participante que cumpria os requisitos | `conta + servidor + crônica + run_id` | 1 por run |
| `rep_cr01_evento` | Evento Mundial | Elegibilidade em ocorrência de `evt_cr01_ressonancia` ou `evt_cr01_ressonancia_plena` | `conta + servidor + crônica + occurrence_id` | 1 por ocorrência |
| `rep_cr01_desbravar` | Desbravar | Resultado narrativo `dsc_cr01_vestigio` (sem economia) em qualquer Local com Desbravar liberado | `conta + servidor + crônica + attempt_id` | 2 por dia por conta |
| `rep_cr01_encontro` | Combate | Vitória ao **enfrentar de novo** um Encontro da Crônica já vencido (`[Enfrentar o Eco de novo]`, no LR). A repetição dá 0 XP e 0 economia; só Trilha e Bestiário normal | `conta + servidor + crônica + encounter_instance_id` | 2 por dia por conta |

Uma run ou ocorrência usada para cumprir um objetivo único também conta como repetível, porque são fontes distintas do GDD (ver Dúvida 13). Não contam: Caçada/Ronda, Duelo, Arena da Vigília, Batalha de Guildas, Juramento, Expedição e Dádiva Diária.

---

## 9. Classificação ao fim da Crônica

| Destino | ID / conteúdo | Observação |
|---|---|---|
| **Persiste** | `codex_cr01_*` (todas as Entradas e Trechos obtidos) | Permanentes por personagem, inclusive após Legado (GDD §33.2) |
| **Persiste** | `cos_cr01_*` resgatados ou liquidados | Entitlements normais |
| **Persiste** | `world_state.cr01_desfecho` | Estado global do servidor |
| **Persiste** | Flavor `flv_cr01_epilogo_*` e falas `dlg_cr01_pos_*` | Bancos de texto do desfecho nos hubs e Locais |
| **Persiste** | Feitos ligados à Crônica e snapshots do Salão da Vigília | Histórico de prestígio |
| **Persiste** | Entradas de Bestiário das criaturas `*.cr01.*` | O registro fica, mesmo sem a criatura no mundo |
| **Arquivado** | Capítulos `cap_01`–`cap_08` como **Crônica Arquivada** | Rejogáveis em instância pessoal para recuperar a história e o Códice; sem pontos, voto ou recompensa |
| **Arquivado** | Trilha (progresso, claims) após T+14 dias | Liquidação automática única antes de arquivar |
| **Arquivado** | Votos, snapshot do eleitorado, resultado e runoff | Registro auditável |
| **Arquivado** | Classificação da Vigília e da Batalha de Guildas do ciclo | GDD §5.3 |
| **Arquivado** | Flags de Leitura e de objetivo | Só como histórico |
| **Arquivado** | Encontros `enc_cr01_c01`–`c08` | Jogáveis só dentro da Crônica Arquivada, com as mesmas regras de economia zero |
| **Removido** | `evt_cr01_ressonancia` e `evt_cr01_ressonancia_plena` | Substituídos pelo Eco Residual só se `pr_cr01_eco_residual` for aprovada |
| **Removido** | Resultados `dsc_cr01_*` dos pools de Desbravar do mundo vivo | Existem só dentro da Crônica Arquivada |
| **Removido** | Pontos de leitura `lei_cr01_*` do mundo vivo | Idem |
| **Removido** | Fontes `rep_cr01_*` | Encerradas no cutoff |
| **Removido** | Criaturas `*.cr01.*` do mundo vivo, inclusive O Compasso | Um Chefe de Evento futuro só volta com `pr_cr01_eco_residual` aprovada |
| **Removido** | Compra do Passe da Crônica I | Bloqueada após o encerramento (GDD §5.2) |
| **Removido** | Flavor do pulso ativo `flv_cr01_pulso_*` | Substituído pelo Flavor do epílogo |

---

## 10. Flavor de resultado PvP

Texto de micro-combate (alvo 40–120 caracteres, GDD §49.17). Sem conteúdo de camada.

### Arena da Vigília

| ID | Resultado | Texto |
|---|---|---|
| `flv_arena_vitoria_01` | Vitória | A Vigília registra seu nome. Amanhã, alguém virá buscá-lo. |
| `flv_arena_vitoria_02` | Vitória | Você continua de pé. Ninguém aplaude; a Vigília apenas anota. |
| `flv_arena_vitoria_03` | Vitória | O Renome sobe como brasa soprada: quente agora, frágil depois. |
| `flv_arena_derrota_01` | Derrota | Caído, você ouve a Vigília anotar. Derrota também é registro. |
| `flv_arena_derrota_02` | Derrota | A Arena guarda mais nomes vencidos que vitoriosos. |
| `flv_arena_derrota_03` | Derrota | Levante-se. A janela ainda está aberta, e o erro já tem nome. |
| `flv_arena_empate_01` | Empate | Caíram juntos. A Vigília registra dois nomes na mesma linha. |
| `flv_arena_empate_02` | Empate | Nenhum dos dois ficou de pé. Nenhum dos dois perdeu sozinho. |
| `flv_arena_empate_03` | Empate | A pedra não decide o que os golpes não decidiram. |

### Duelo

| ID | Resultado | Texto |
|---|---|---|
| `flv_duelo_vitoria_01` | Vitória | O desafio foi aceito e respondido. A última palavra é sua. |
| `flv_duelo_vitoria_02` | Vitória | O outro sabe agora o que você sabe. |
| `flv_duelo_vitoria_03` | Vitória | Lâmina baixa, fôlego curto: a vitória pesa menos que o golpe. |
| `flv_duelo_derrota_01` | Derrota | Você aceitou o duelo e perdeu. Aceitar já foi coragem. |
| `flv_duelo_derrota_02` | Derrota | Perder um duelo é aprender o preço exato de um erro. |
| `flv_duelo_derrota_03` | Derrota | A mão estendida, ou não. A derrota é sua de qualquer jeito. |
| `flv_duelo_empate_01` | Empate | Dois corpos no chão, nenhum vencedor. O desafio continua aberto. |
| `flv_duelo_empate_02` | Empate | Caíram ao mesmo tempo. Fica a pergunta para outro dia. |
| `flv_duelo_empate_03` | Empate | Ninguém venceu. Os dois vão lembrar. |

### Batalha de Guildas

| ID | Resultado | Texto |
|---|---|---|
| `flv_gvg_vitoria_01` | Vitória | As frentes cederam do outro lado. Hoje, a Guilda se manteve. |
| `flv_gvg_vitoria_02` | Vitória | A vitória pertence a todos os nomes que estavam na linha. |
| `flv_gvg_vitoria_03` | Vitória | Vitória registrada. Na próxima noite, será preciso merecê-la de novo. |
| `flv_gvg_derrota_01` | Derrota | A Guilda recua junta. Ninguém perde sozinho numa batalha assim. |
| `flv_gvg_derrota_02` | Derrota | As frentes caíram. Contem os feridos, não os culpados. |
| `flv_gvg_derrota_03` | Derrota | Derrota registrada. A próxima batalha começa com esta lição. |
| `flv_gvg_empate_01` | Empate | Nenhuma Guilda cedeu. A noite termina sem vencedor. |
| `flv_gvg_empate_02` | Empate | Frente por frente, golpe por golpe: tudo igual até o fim. |
| `flv_gvg_empate_03` | Empate | As duas Guildas partem sabendo quanto a outra vale. |

---

## 11. Bestiário e Encontros da Crônica

Cada Crônica tem seu próprio bestiário, identificado pelo prefixo do ciclo (`cr01` nesta). Estas criaturas não entram nos pools de Caçada, Ronda ou Desbravar das Regiões: aparecem só nos Encontros da Crônica e no Evento Mundial dela.

### 11.1 Como os Encontros funcionam no bot

1. **Onde:** o objetivo de Encontro aparece na tela da Crônica com a ação `[Enfrentar]`. A luta acontece no LR da **Região de Ressonância** do jogador, mesmo quando as investigações do capítulo são em outra Região. Assim todo jogador luta no nível certo.
2. **Nível do encontro:** o nível do personagem, limitado à faixa da RR (Ocaso 1–10, Vales 11–20, Nareth 21–30, Várzeas 31–40, Altos 41–50, Confins 51–60), congelado na criação do encontro.
3. **Nível mínimo:** Elites exigem Nv.3 e Chefes exigem Nv.5. Abaixo disso, o objetivo mostra `⏳ Requer Nv. 3` ou `⏳ Requer Nv. 5` e os demais objetivos continuam disponíveis.
4. **Atributos:** fórmula do GDD §49.6 (`K(level) × categoria × arquétipo × variante × conteúdo × grupo`), com `Content_A = 1,00`. Nenhum multiplicador novo.
5. **Artes:** coeficientes dentro das faixas do GDD §49.6 e só status já existentes (Barreira, ⬇️ DEF, Ação Preparada). São parâmetros novos de conteúdo, em `SIMULAR` para validação do Balanceamento (GDD §49.20); nenhum valor publicado muda.
6. **Viabilidade Solo:** toda build legal vence com Ataque Básico e kit legal. Sem cura própria, Hard CC, enrage ou DPS check obrigatório.
7. **Recompensa da primeira vitória:** XP normal de inimigo da Categoria no nível do encontro (GDD §49.7) e progresso de Bestiário. **0 Coroas, 0 Materiais, 0 Saque, 0 Equipamento, 0 Vigor.** Uma vez por personagem por encontro.
8. **Derrota:** sem perda; o personagem volta ao Braseiro mais próximo do LR e pode tentar de novo quantas vezes quiser. O encontro é preservado, sem rerroll.
9. **Repetição:** depois da vitória, `[Enfrentar o Eco de novo]` fica disponível e alimenta `rep_cr01_encontro` (seção 8), com 0 XP e 0 economia.
10. **Visual:** as criaturas são feitas da matéria da RR onde a luta acontece (tabela 11.2). A anatomia é a mesma em todas as Regiões; muda só o material.

**PROPOSTA DE REGRA `pr_cr01_encontro_grupo` — Encontros em Grupo.**
Encontros da Crônica aceitam Solo ou Grupo de 1–4, com Confirmação de Entrada de 60s, como a Campanha (GDD §51.2–51.3). Todos os membros precisam ter o mesmo objetivo ativo e a mesma RR; o nível vem do Personagem de Referência. Criaturas e Elites não escalam com o Grupo, como o encontro roteirizado de P1 (GDD §51.4). Chefes da Crônica usam a escala de Chefe de Campanha (GDD §51.5: HP ×1,00/1,55/2,10/2,65; ATQ ×1,00/1,04/1,08/1,12).
*Por que é regra nova:* as regras de Grupo e de escala de Chefe do GDD cobrem a Campanha, não a Crônica. Sem esta proposta, os Encontros ficam só Solo.

### 11.2 Matéria por Região

| Região de Ressonância | Matéria das formas |
|---|---|
| Terras do Ocaso | fuligem compactada, cinza e lascas de pedra escurecida |
| Vales dos Enforcados | raízes finas trançadas, turfa e musgo úmido |
| Planícies de Nareth | poeira de marco, capim seco e lama rachada |
| Várzeas Carmesins | lodo ferruginoso, crosta de sal e juncos |
| Altos Cinéreos | cascalho de basalto, cinza mineral e fiapos de cabo |
| Confins do Véu | névoa condensada e pedra pálida |

**Leitura ecológica (produção, não player-facing):** Ecos (Bíblia §11). O jogo nunca confirma o que são: não são almas, fantasmas, mortos-vivos nem pessoas. Não têm rosto. Repetem gestos de trabalho e de serviço de gente que não está ali.

**Evitar em todas as fichas:** translucidez de fantasma, brilho, olhos brilhantes, aura mágica, chamas, caveira, demônio, rosto humano reconhecível, runas luminosas.

### 11.3 Criaturas e Elites

#### `creature.cr01.repetidor` — Repetidor
Comum/COMMON · Bruto · Nv.1–60 (adaptativo) · Encontro do Capítulo 1 · humanoide ~2 m

**Morfologia:** forma humana oca feita da matéria do lugar, com braços longos demais que repetem sem parar o mesmo gesto de trabalho, como erguer um martelo ou puxar uma corda. Onde deveria haver um rosto, a matéria afunda como a marca de um polegar. A cada pulso, desfaz-se e refaz-se meio passo à frente. Pose: braço erguido no topo do gesto, prestes a descer.
**O medo:** repete o trabalho de alguém que já não está aqui, e você está no caminho do gesto.

| Arte | Efeito | Recarga |
|---|---|---|
| Gesto de Ofício | `100% ATQ`, 1 alvo | básico |
| Golpe Repetido | multi-hit 2 golpes de `60% ATQ` (`120%` total), mesmo alvo | CD3 |

**IA:** (1) Golpe Repetido se disponível; (2) Gesto de Ofício.
**Função:** primeira luta da Crônica; apresenta o multi-hit.

#### `creature.cr01.marcador` — Marcador
Comum/COMMON · Controlador · Nv.1–60 (adaptativo) · Encontro do Capítulo 2 · ~2,4 m

**Morfologia:** silhueta alta e fina como uma vara de medição, com um único braço esticado que aponta sempre para o mesmo lado, mesmo quando o corpo gira. Do braço pendem fios de matéria como linhas de prumo. Não toca o chão: arrasta pontas que riscam linhas retas demais. Pose: corpo de lado, braço apontando para fora do quadro.
**O medo:** aponta para algo que você não vê, e então aponta para você.

| Arte | Efeito | Recarga |
|---|---|---|
| Toque de Medida | `95% ATQ`, 1 alvo | básico |
| Marca de Desvio | `90% ATQ` + `DEF −10%` por 2T | CD3 |

**IA:** (1) Marca de Desvio se disponível e o alvo não tiver redução de DEF igual ou maior; (2) Toque de Medida.

#### `creature.cr01.guarda_repetida` — Guarda Repetida
Incomum/RARE · Blindado · Nv.1–60 (adaptativo) · Encontro do Capítulo 3 · ~2,2 m, larga

**Morfologia:** forma larga e pesada na postura perfeita de um guarda antigo, segurando um escudo da mesma matéria do corpo, rachado ao meio. A postura é exata; o corpo, não: a cabeça vira devagar, sempre um pouco atrasada em relação ao resto. Pose: guarda baixa, escudo à frente, cabeça ainda virando.
**O medo:** guarda um posto que não existe mais, e você entrou nele.

| Arte | Efeito | Recarga |
|---|---|---|
| Golpe de Posto | `100% ATQ`, 1 alvo | básico |
| Postura Copiada | Barreira em si de `70% ATQ` | CD3 |
| Avanço de Posto | `125% ATQ`, 1 alvo | CD3 |

**IA:** (1) Postura Copiada se disponível e sem Barreira ativa; (2) Avanço de Posto; (3) Golpe de Posto.

#### `creature.cr01.carregador_repetido` — Carregador Repetido
Incomum/RARE · Equilibrado · Nv.1–60 (adaptativo) · Encontro do Capítulo 5 · ~2 m, curvado

**Morfologia:** corpo dobrado sob o peso de algo invisível, braços travados como se segurassem uma carga, pernas grossas e tortas. A coluna aparece em relevo sob a matéria. Quando larga a carga invisível, o chão afunda com um baque. Pose: joelhos dobrados, braços erguidos sobre a cabeça, prestes a largar.
**O medo:** carrega há muito tempo algo que ninguém vê, e larga em cima de você.

| Arte | Efeito | Recarga |
|---|---|---|
| Peso Largado | `105% ATQ`, 1 alvo | básico |
| Carga Preparada | Ação Preparada `160% ATQ`, 1 alvo; telegraph: "ergue algo que não está ali" | CD4 |

Pode usar Defender conforme a IA padrão do GDD §9.6.
**IA:** (1) resolver Carga Preparada pendente; (2) preparar Carga Preparada se disponível; (3) Defender, se devido; (4) Peso Largado.

#### `elite.cr01.multidao_repetida` — Multidão Repetida
Elite/ELITE · Conjurador · Nv.3–60 (adaptativo) · Encontro do Capítulo 6 · ~3 m de largura

**Morfologia:** seis a oito formas humanas fundidas lado a lado, ombro com ombro, como uma fila de trabalhadores que se colou. Cada uma repete um gesto diferente, fora de compasso; as cabeças sem rosto viram juntas. No pulso, todas abrem ao mesmo tempo uma boca que não têm. Pose: frontal, braços em gestos diferentes, cabeças voltadas para a câmera.
**O medo:** são muitos, e nenhum é alguém.

| Arte | Efeito | Recarga |
|---|---|---|
| Empurrão | `100% ATQ`, 1 alvo | básico |
| Muitas Mãos | multi-hit 3 golpes de `40% ATQ` (`120%` total) | CD2 |
| Coro | AoE `75% ATQ` | CD3 |
| A Palavra | Ação Preparada `170% ATQ`, 1 alvo; telegraph: todas as bocas formam a mesma palavra | CD4 |

**IA:** (1) resolver A Palavra pendente; (2) Coro se houver 2+ alvos válidos; (3) preparar A Palavra se disponível; (4) Muitas Mãos; (5) Empurrão. Solo, o Coro não é usado.
**Feito:** `feito_cr01_multidao` — Primeira vitória sobre a Multidão Repetida (sem Cosmético).

#### `elite.cr01.escriba_repetido` — Escriba Repetido
Elite/ELITE · Controlador · Nv.3–60 (adaptativo) · Encontro do Capítulo 7 · ~2,5 m sentado

**Morfologia:** figura sentada sobre nada, curvada sobre uma prancha que não existe, com dedos longos demais que riscam o ar. Cada traço deixa marcas no chão, na pedra e na pele de quem está perto: sempre a mesma palavra, que nunca se completa. Pose: inclinada para a frente, um dedo erguido no meio de um traço.
**O medo:** escreve você no registro, e depois risca.

| Arte | Efeito | Recarga |
|---|---|---|
| Traço | `100% ATQ`, 1 alvo | básico |
| Rasura | `90% ATQ` + `DEF −12%` por 2T | CD3 |
| Revisão | Barreira em si de `80% ATQ`; só abaixo de 50% HP | CD4, máx. 2 usos |
| Registro Imposto | Ação Preparada `160% ATQ`, 1 alvo; telegraph: "a palavra no chão começa a se fechar à sua volta" | CD4 |

**IA:** (1) resolver Registro Imposto pendente; (2) Revisão se abaixo de 50% HP, sem Barreira ativa e com usos; (3) Rasura se o alvo não tiver redução de DEF igual ou maior; (4) preparar Registro Imposto se disponível; (5) Traço.
**Feito:** `feito_cr01_escriba` — Primeira vitória sobre o Escriba Repetido (sem Cosmético).

### 11.4 Chefes

Perfil de Chefe do GDD §49.6 (`220% HP / 110% ATQ / 110% DEF / 100% AGI` sobre a referência), com o arquétipo indicado. Fases por HP em `70%` e `35%`; transições idempotentes e snapshotadas.

#### `boss.cr01.mestre_de_turno` — Mestre de Turno
Chefe/BOSS · Bruto · Nv.5–60 (adaptativo) · Chefe intermediário, Capítulo 4 · ~3,5 m

**Morfologia:** forma grande e ereta, com um braço terminado num martelo de matéria compacta e o outro erguido num gesto de ordem. Em volta do pescoço, uma corrente de placas, como fichas de turno, que batem umas nas outras a cada pulso. Formas menores se montam à sua volta e obedecem. Pose: braço de ordem erguido, martelo baixo, Repetidores menores ao fundo.
**O medo:** dá ordens a quem já não está aqui, e eles ainda obedecem.

| Arte | Efeito | Recarga / fase |
|---|---|---|
| Ordem de Turno | `100% ATQ`, 1 alvo | básico |
| Martelada de Ritmo | `135% ATQ`, 1 alvo | CD3 |
| Chamada | invoca 1 add menor (Threat `0,50`, GDD §49.6) com o kit do Repetidor; sem XP, Bestiário extra ou economia; não escala com Grupo | 1× ao entrar na Fase II |
| Ordem Coletiva | AoE `80% ATQ` | CD3 · Fase II+ |
| Fim de Turno | Ação Preparada `175% ATQ`, 1 alvo; telegraph: "todas as placas param de bater" | CD5 · Fase III |

- **Fase I — Turno** (`100→70%`): Ordem de Turno e Martelada de Ritmo.
- **Fase II — Chamada** (`70→35%`): invoca o add e libera Ordem Coletiva. Derrotar o add é opcional.
- **Fase III — Fim de Turno** (`≤35%`): libera Fim de Turno.

**IA:** (1) resolver Fim de Turno pendente; (2) Chamada na entrada da Fase II; (3) preparar Fim de Turno se disponível; (4) Ordem Coletiva se houver 2+ alvos válidos; (5) Martelada de Ritmo; (6) Ordem de Turno.
**Feito:** `feito_cr01_mestre_de_turno` — Fim de Turno (sem Cosmético).

#### `boss.cr01.o_que_aguarda_resposta` — O Que Aguarda Resposta
Chefe/BOSS · Equilibrado · Nv.5–60 (adaptativo) · Chefe final, Capítulo 8 · ~5 m ajoelhado

**Morfologia:** figura imensa ajoelhada, montada em camadas da matéria do lugar, com os dois braços estendidos à frente segurando uma placa lisa que oferece a quem chega. Não tem rosto: tem dezenas de marcas de dedo afundadas onde ele deveria estar. Quando ninguém pega a placa, ela se levanta. Pose: ajoelhada, braços estendidos, placa oferecida à câmera.
**O medo:** pede uma resposta que você não tem, e não aceita silêncio.

| Arte | Efeito | Recarga / fase |
|---|---|---|
| Oferta | `100% ATQ`, 1 alvo | básico |
| Pedido Repetido | `90% ATQ` + `DEF −12%` por 2T | CD3 |
| Insistência | AoE `80% ATQ` | CD3 |
| Selo Pendente | Barreira em si de `8% HP Máximo` | CD4 · máx. 2 usos |
| Espera | não ataca; aplica em si `DEF −12%` por 1T; telegraph: "estende a placa e espera" | Fase II, a cada 4ª oportunidade do Chefe |
| Confirmação Exigida | Ação Preparada `185% ATQ`, 1 alvo; telegraph: "a placa se volta para você" | CD5 · Fase III |

- **Fase I — Oferta** (`100→70%`): Oferta, Pedido Repetido e Selo Pendente.
- **Fase II — Espera** (`70→35%`): libera Insistência; a cada 4ª oportunidade, a Espera abre uma janela para bater mais forte.
- **Fase III — Sem Resposta** (`≤35%`): a Espera para de acontecer; libera Confirmação Exigida.

**IA:** (1) resolver Confirmação Exigida pendente; (2) Espera, quando devida na Fase II; (3) Selo Pendente se sem Barreira ativa e com usos; (4) preparar Confirmação Exigida se disponível; (5) Insistência se houver 2+ alvos válidos; (6) Pedido Repetido se o alvo não tiver redução de DEF igual ou maior; (7) Oferta.
**Feito:** `feito_cr01_aguarda_resposta` — Sem Resposta (sem Cosmético).

### 11.5 Chefe de Evento Mundial

#### `boss_evento.cr01.o_compasso` — O Compasso
Chefe de Evento · Equilibrado · usado em `evt_cr01_ressonancia` (semanas 1–7) e `evt_cr01_ressonancia_plena` (semanas 7–8) · ~8 m

**Morfologia:** coluna de matéria que pulsa, alta como uma torre baixa, feita de pedaços de todas as formas menores: braços, ombros, ferramentas, placas. A cada batida, o chão em volta afunda e volta. Dos lados, Repetidores se formam e se desfazem no mesmo ritmo. Pose: câmera baixa, coluna inteira em quadro, figuras pequenas de jogadores na base.
**O medo:** o mundo inteiro bate no ritmo dele.

**Regras do Evento (GDD §21 e §49.15, sem alteração):** HP atômico compartilhado; 3 fases; escala de HP por fase `N^0,88` (N máx. 200); ATQ `+1,5%` por participante adicional, máximo `+60%`; snapshot por fase; elegibilidade ≥2 fases + 8 Ações Significativas; reentrada após 2 minutos; economia padrão de Evento Mundial.

**Versões por Região:** uma por faixa, com nível de evento 10/20/30/40/50/60. Veteranos entram nas versões inferiores com Sintonização do Véu (`Lsync = min(Ljogador, Levento + 5)`). Ver Dúvida 5.

| Arte | Efeito | Recarga / fase |
|---|---|---|
| Batida | `100% ATQ`, 1 alvo | básico |
| Onda de Compasso | AoE `75% ATQ` | CD3 |
| Contratempo | `95% ATQ` + `DEF −10%` por 2T | CD3 |
| Batida Plena | Ação Preparada AoE `110% ATQ`; telegraph: "o chão inteiro afunda e não volta" | CD4 · Fase 2+ |
| Ressonância | Barreira em si de `6% HP Máximo` | 1× ao entrar na Fase 3 |

- **Fase 1 — Primeira Batida:** Batida e Contratempo.
- **Fase 2 — Compasso:** libera Onda de Compasso e Batida Plena. Na versão **Plena**, uma onda de Repetidores menores (swarm, Threat `0,30` por participante válido, dentro do limite de `1,50` por jogador).
- **Fase 3 — Batida Final:** Ressonância na entrada; todas as Artes disponíveis.

---

## Dúvidas para o autor

1. **Versão da Bíblia.** O pedido cita a v3.0; usei a v4.0.7 anexada. Confirmar.
2. **Quem são os Herdeiros.** As fontes só usam "Herdeiro/Herdeira" como função de Maro Keln e Eris Val, sem definir um grupo. Tratei como designação informal de estudiosos de registros antigos, sem Estado, culto ou hierarquia. Confirmar ou definir.
3. **Sequência Pendente.** O objeto do voto (uma etapa da Convergência que nunca terminou e desperta agora) é criação deste documento. Precisa de aprovação como cânone da Crônica, inclusive o complemento C4 de que o pedido "parte do Nó Central".
4. **Gate de entrada na Crônica.** O GDD diz que ela não é endgame-only, mas não diz a partir de quando um personagem novo participa. Recomendo P1 concluída, porque é quando Desbravar da Estrada é liberado.
5. **Evento Mundial da Crônica.** As ocorrências usam os horários normais (ter/qui/sáb, 12:00 e 20:00)? Cada horário roda as 6 versões de O Compasso ao mesmo tempo, para jogadores de nível baixo não ficarem de fora? Se só houver uma versão por horário, isso pode exigir regra.
6. **Abertura do voto.** O GDD fixa o fechamento (T−48h), não a abertura. Propus D50. Também falta definir a hora e o fuso de T.
7. **Destinatário da Entrada de desfecho.** Quem recebe `codex_cr01_desfecho`: todo personagem com pelo menos 1 capítulo concluído, só eleitores elegíveis, ou todos do servidor?
8. **Produção das Aparências.** Cada Aparência da Crônica segue o padrão regional de 60 variantes (5 raças × 2 gêneros × 6 Classes)? Que céu usam: o neutro das skins padrão ou um próprio da Crônica?
9. **Materiais básicos vinculados.** De qual Grau? Segue a mesma resolução da Dádiva Diária (nível ou Região do personagem no resgate)?
10. **Vestígio de Desbravar.** Inserir `dsc_cr01_vestigio` na categoria narrativa do pool está ok? Os limites de 2 por dia por conta (Desbravar e Encontro repetido) são declaração de conteúdo ou devem ir para o Balanceamento?
11. **Ajudante.** Um personagem que entra como Ajudante (sem o objetivo ativo ou sem cumprir requisitos próprios) conta para objetivos e repetíveis de Masmorra e de Encontro? Assumi que não.
12. **Fonte dupla.** Uma mesma run ou ocorrência pode valer para um objetivo único e para um repetível ao mesmo tempo? Assumi que sim.
13. **Alternativo de Masmorra.** Trocar Masmorra por Desbravar (`dsc_cr01_vestigio_profundo`) para quem não tem Masmorra liberada é aceitável, já que muda o tipo de ação?
14. **Ordem das opções no voto.** Fixa, na ordem do GDD, ou embaralhada por jogador para reduzir viés de posição?
15. **Crônica Arquivada.** Os capítulos e Encontros continuam jogáveis depois do encerramento, como instância pessoal sem pontos? O GDD permite o catch-up de história, mas não diz se o conteúdo arquivado fica jogável.
16. **Elegibilidade de Beta.** O GDD diz que 4/8 + 1 objetivo podem ser ajustados em Beta. Usei a referência; se mudar, a seção 3 continua valendo porque `cap_08_obj_01` é acessível a todos.
17. **Cânone das criaturas.** As 9 criaturas da seção 11 são novas: formas de matéria local que repetem gestos, classificadas como Ecos (Bíblia §11) e sem confirmação do que são. Precisam de aprovação de lore e de fichas no Bestiário vigente.
18. **Produção visual das criaturas.** A matéria muda por Região (tabela 11.2). Isso dá até 54 artes (9 criaturas × 6 materiais). Prefere assim ou um único material para todas?
19. **Kits em SIMULAR.** Todas as Artes usam faixas do GDD §49.6, mas são valores novos de conteúdo. O Balanceamento precisa validar viabilidade Solo e TTK, principalmente dos dois Chefes no Nv.5.
20. **XP da primeira vitória.** Os Encontros dão XP normal de inimigo e zero economia. Está ok, ou devem dar zero XP também?
21. **Níveis mínimos.** Elite com Nv.3 e Chefe com Nv.5 bastam? Um personagem novo que entra na semana 4 só conclui o Capítulo 4 depois do Nv.5.
22. **Encontro fora do foco.** A luta sempre na RR do jogador (e não na Região-foco) foi escolhida para que todos lutem no próprio nível. Um veterano faz a investigação do Capítulo 2 no Ocaso, mas luta nos Confins. Confirmar.

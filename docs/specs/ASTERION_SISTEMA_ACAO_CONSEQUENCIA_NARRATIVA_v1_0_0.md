# ASTERION — SISTEMA NARRATIVO DE AÇÃO × CONSEQUÊNCIA
## Especificação de Design e Handoff — v1.0.0

> **Status:** FECHADO PARA IMPLEMENTAÇÃO narrativa, sujeito apenas a QA de copy e testes de persistência.
> **Objetivo:** transformar decisões do jogador em memória persistente, consequências locais e reações futuras, sem criar 72 campanhas independentes.
> **Princípio:** **Ação → Consequência → Memória → Reação futura → Nova escolha.**

## 0. Autoridade e escopo

Esta especificação trabalha sobre o GDD Estrutural v1.6.0, a Bíblia Canônica v4.0.7, as seis Fontes Regionais vigentes e a Autoridade Visual v6.4.10. As Regionais continuam autoridades para missões, gates, recompensas, encontros e limites de revelação; esta especificação acrescenta a camada narrativa de escolha/memória.

**Não alterar:** XP, Coroas, Materiais, Equipamentos, pools, níveis, gates, kits, economia, combate, Bestiário, Códice ou progressão global, salvo flags narrativas e apresentação derivadas das decisões abaixo.

### 0.1 Decisões do responsável que sobrescrevem o comportamento narrativo anterior

1. **Toda Missão Principal e toda Missão Secundária possui pelo menos um nó de decisão narrativa.**
2. **Contratos podem permanecer objetivos e sem ramificação narrativa.**
3. **Coop narrativo é limitado exclusivamente a Chefes.** Missões narrativas comuns são solo no progresso, nos objetivos, nas escolhas e no estado narrativo. Um Grupo não pode avançar a história de outro personagem. Chefes de Campanha e demais encontros classificados como Chefe permanecem cooperativos conforme as regras globais de Chefe.
4. **Relacionamento não usa valor numérico exposto.** O estado é percebido por falas, confiança, distância, disponibilidade de conversa e tratamento.
5. **Toda escolha relevante deixa pelo menos uma memória ou consequência persistente.**
6. **Escolhas locais convergem.** Não criar ramos inteiros independentes quando uma memória, uma fala ou uma futura opção consegue produzir a sensação de consequência.
7. **NPC não é onisciente.** Ele só reage ao que presenciou, recebeu por relato ou encontra em registro que legitimamente possa consultar.
8. **Raça e Classe são identidade contextual.** Não são checkboxes decorativos nem justificativa automática de opinião/moralidade.

### 0.2 Nota de conflito com o GDD atual

O GDD v1.6.0 atualmente descreve Campanha individual em Solo ou Grupo de 1–4 a partir de P1. A presente decisão do responsável altera deliberadamente esse escopo para o sistema narrativo: **Missões Principais e Secundárias não avançam por Coop; somente Chefes aceitam Coop narrativo/combatente.** Esta alteração deve ser registrada na próxima revisão do GDD antes do merge definitivo.

## 1. Modelo de Ação × Consequência

Cada decisão possui cinco camadas:

- **Ação:** escolha explícita do jogador.
- **Consequência imediata:** reação na cena atual.
- **Memória:** uma ou mais tags persistentes no personagem e/ou NPC.
- **Reação futura:** uma cena posterior consulta essa memória quando houver conhecimento legítimo.
- **Nova escolha:** a memória pode alterar texto, opção disponível, ordem de prioridade ou enquadramento de uma decisão futura.

### 1.1 Tipos de memória

`FACTUAL` — registra o que o jogador fez/viu; `RELATIONAL` — registra como uma pessoa interpreta o personagem; `METHOD` — registra como o personagem costuma decidir; `ETHICAL` — registra limites ou prioridades demonstradas; `EVIDENCE` — registra método de trato com informação; `IDENTITY` — registra quando Raça/Classe realmente participou da situação.

### 1.2 Vocabulário controlado de tendências

`evidence_first`, `hypothesis_marked`, `corroborates`, `preserves_records`, `community_first`, `safety_first`, `risk_accepting`, `risk_averse`, `pragmatic`, `protective`, `questions_authority`, `institutional_trust`, `institutional_skepticism`, `continuity_first`, `limits_coercion`, `accepts_controlled_cost`, `context_before_judgment`, `preserves_contradiction`, `results_first`, `cause_first`.

As tags acumulam contexto; não são uma moralidade binária e não são mostradas ao jogador como pontuação.

## 2. Relacionamento com NPCs

Nenhuma barra de afinidade é exibida. Para NPCs com memória relevante, o jogo mantém:

`rapport_state`: `neutral`, `open`, `trusting`, `guarded`, `skeptical`, `respectful`, `strained`.

`memory_tags`: conjunto persistente de experiências que explicam o estado.

Uma nova escolha não precisa trocar o `rapport_state` imediatamente. Muitas consequências funcionam como memória que só altera o relacionamento quando outro evento oferece contexto para a reação.

## 3. Regras de percepção e conhecimento

1. Uma decisão pessoal não vira conhecimento mundial automaticamente.
2. Um NPC só reage se tiver presenciado, recebido relato, consultado registro permitido ou participado de uma etapa compartilhada legítima do **próprio contexto**.
3. Códice e conhecimento narrativo continuam pessoais.
4. Nenhuma escolha pessoal altera `world_state` global de servidor.
5. A apresentação deve filtrar o que o personagem legitimamente sabe.

## 4. Identidade: Raça × Classe

### 4.1 Raça

**Remanescente:** adaptação, sobrevivência histórica, experiência prática; não “humano padrão”.
**Velado:** percepção, controle e sensibilidade velar estabilizada; nunca sinônimo de drow, vampiro ou moralidade sombria. A pigmentação racial é cinza-fria conforme a Bíblia.
**Cinéreo:** tenacidade e resistência física; não implica brutalidade, tribalismo ou violência. Todos possuem as duas presas inferiores curtas.
**Hemário:** persistência e recuperação sob pressão. Em Várzeas, pode haver reconhecimento emocional ou histórico do Projeto Hemaris; nunca culpa racial automática.
**Alvorano:** prontidão e iniciativa; não implica pureza, religião, divindade ou superioridade.

### 4.2 Classe

**Sentinela:** guarda, contenção, proteção e leitura de risco físico.
**Errante:** deslocamento, rotas, oportunidades e leitura de terreno.
**Vigia:** observação, marcação, distância e atenção a detalhes.
**Tecelão:** leitura de Trama, estruturas mágicas/técnicas e padrões de interação.
**Oráculo:** Presságio, incerteza e leitura de possibilidades; nunca conhecimento onisciente.
**Luminar:** proteção, cura, Barreira e julgamento contextual; nunca prova de religião verdadeira.

### 4.3 Regra de combinação

Se Raça e Classe forem relevantes na mesma cena, o jogo pode oferecer uma **resposta combinada única** em vez de duas linhas redundantes. Exemplo: Hemário + Luminar em uma discussão de tratamento pode reconhecer simultaneamente o histórico de Hemaris e a experiência de proteção. A opção nunca atribui personalidade, moralidade ou cultura à Raça por automatismo.

## 5. Coop narrativo — regra fechada

**Somente Chefes aceitam Coop narrativo/combatente.**

- Missões Principais: Solo.
- Missões Secundárias: Solo.
- Contratos: Solo por padrão, sem ramificação narrativa.
- Elites, encontros roteirizados e encontros econômicos de missão: Solo.
- Chefes de Campanha: Solo ou Grupo 1–4.
- Chefes opcionais de Missão Secundária: Solo ou Grupo 1–4, conforme contrato global de Chefe.
- Chefes de Masmorra: seguem a regra global de Masmorra/Grupo, se classificados como Chefe.

O convidado não recebe a escolha do anfitrião, não grava a memória narrativa do anfitrião e não altera o estado narrativo pessoal do anfitrião. A luta compartilhada do Chefe pode ser comum; a narrativa antes/depois continua individual.

## 6. Execução técnica da decisão

Cada nó de decisão usa pelo menos:

```text
choice_id
mission_id
step_context
options[]
selected_option
committed_at
character_memory_tags[]
npc_memory_targets[]
future_hooks[]
identity_conditions[]
```

### 6.1 Regras de persistência

- Escolha é **commit once**; reconnect nunca rerrola.
- Callback duplicado nunca replica consequência.
- Abandono de Secundária não apaga memória já legitimamente registrada.
- Suspensão de Principal não apaga memória.
- Reaceite de Secundária não cria nova versão de memória da mesma decisão.
- O debug deve conseguir mostrar `choice_id → option → memories → future_hooks`.

### 6.2 Convergência

Após a decisão, a Missão retorna ao fluxo regional já publicado sempre que possível. A escolha altera narrativa, não a baseline econômica. Novas etapas só são criadas em uma revisão posterior se houver necessidade explícita de conteúdo; este documento trata os nós como **subetapas narrativas dentro das etapas existentes**.

## 7. Contrato das 72 Missões

Cada linha abaixo define o **mínimo obrigatório**. Copy final pode enriquecer a cena sem alterar a semântica do contrato.
### 🌑 Terras do Ocaso

#### P1 — Vozes na Estrada
**Nó:** `P1_choice_posture`
**Momento:** Etapa 5, primeira conversa com Alda.
**Pergunta dramática:** Como você se apresenta depois de sobreviver à estrada?

1. **Prudência: falar só do que viu.** → memória: `Alda:_cautela_no_relato;_Oren:_fatos_primeiro.`
2. **Abertura: admitir medo, mas pedir orientação.** → memória: `Alda:_aceita_vulnerabilidade;_Oren:_honestidade.`
3. **Curiosidade: perguntar pelos sinais antes de aceitar abrigo.** → memória: `Alda:_curiosidade_ativa;_Oren:_investigador.`
**Retorno futuro:** P2: Alda usa a postura para modular a primeira cobrança.
**Identidade contextual:** Classe: qualquer Classe pode ter uma formulação; Vigia recebe pergunta sobre sinais.

#### S1 — Luzes sob as Cinzas
**Nó:** `S1_response_to_light`
**Momento:** Depois de observar a luz distante.
**Pergunta dramática:** O que fazer com uma ocorrência sem explicação?

1. **Investigar a direção imediatamente.** → memória: `Oren:_respeita_ousadia;_memória:_busca_ativa.`
2. **Registrar e voltar sem perseguir.** → memória: `Oren:_respeita_prudencia;_memória:_preserva_evidencia.`
3. **Perguntar primeiro se alguém já viu o fenômeno.** → memória: `Oren:_prudencia_social;_memória:_busca_testemunha.`
**Retorno futuro:** S5: Oren lembra se você perseguiu o fenômeno ou preservou distância.
**Identidade contextual:** Classe: Oráculo pode formular uma pergunta sobre presságio sem afirmar certeza.

#### P2 — Fuligem sem Fogo
**Nó:** `P2_evidentiary_posture`
**Momento:** Etapa 5, ao levar o registro a Oren.
**Pergunta dramática:** Que tipo de conclusão você aceita sobre a Pedra Marcada?

1. **Registrar só a aparência e localização.** → memória: `Oren:_evidencia_primeiro;_memória:_documental.`
2. **Dizer que a marca parece escrita, mas marcar como hipótese.** → memória: `Oren:_hipotese_controlada;_memória:_inferencia.`
3. **Insistir que ainda falta contexto e procurar outro registro antes de concluir.** → memória: `Oren:_ceticismo_respeitado;_memória:_exige_corroboração.`
**Retorno futuro:** S2/P3: Oren escolhe o tipo de pergunta que fará depois; P4: Alda percebe seu grau de prudência.
**Identidade contextual:** Raça: Cinéreo pode ter reação de experiência prática; Classe: Vigia/Oráculo podem abrir observação contextual.

#### S2 — Os Nomes Esquecidos
**Nó:** `S2_priority`
**Momento:** Após o terceiro vestígio, antes de enfrentar o Peregrino Calcinado.
**Pergunta dramática:** O que merece prioridade diante de pessoas ausentes?

1. **Preservar os nomes e vestígios.** → memória: `Oren:_memoria_primaria;_memória:_preserva_identidades.`
2. **Perseguir o risco que ainda ameaça viajantes.** → memória: `Oren:_pragmatico;_memória:_vivos_primeiro.`
3. **Buscar evidência que una os dois objetivos.** → memória: `Oren:_equilibrado;_memória:_concilia_pessoas_e_prova.`
**Retorno futuro:** S6: Oren retoma a prioridade que você escolheu ao lidar com o último registro.
**Identidade contextual:** Classe: Luminar pode enfatizar proteção; Vigia pode enfatizar evidência.

#### P3 — Sob Galhos Calcinados
**Nó:** `P3_heritage_method`
**Momento:** Etapa 4, diante do fragmento entalhado.
**Pergunta dramática:** Como lidar com um vestígio asteriano que ainda não entende?

1. **Preservar sem tocar mais do que o necessário.** → memória: `Oren:_preservacionista;_memória:_preserva_artefato.`
2. **Examinar cuidadosamente mecanismos e marcas.** → memória: `Oren:_investigador;_memória:_inspeção_ativa.`
3. **Questionar a hipótese antes de aceitá-la como antiga.** → memória: `Oren:_ceticismo;_memória:_testa_autoria.`
**Retorno futuro:** P4/S4: Oren pode reconhecer seu método ao interpretar a função dos Vigias.
**Identidade contextual:** Classe: Tecelão/Vigia pode abrir análise técnica sem revelar lore.

#### S3 — Rastros sob os Galhos
**Nó:** `S3_priority`
**Momento:** Após localizar a carga abandonada.
**Pergunta dramática:** O que importa mais naquele instante?

1. **Descobrir o que causou a perda.** → memória: `Alda:_investigação_pratica;_memória:_causa_primeiro.`
2. **Garantir que a próxima carga passe segura.** → memória: `Alda:_pragmatismo;_memória:_segurança_primeiro.`
3. **Verificar primeiro quem será afetado pela próxima rota.** → memória: `Alda:_protetivo;_memória:_comunidade_primeiro.`
**Retorno futuro:** P4/P5: Alda adapta o enquadramento da próxima tarefa.
**Identidade contextual:** Classe: Errante/Vigia pode ter observação de rota.

#### P4 — Pedras que Ainda Vigiam
**Nó:** `P4_guard_protocol`
**Momento:** Etapa 4, ao perceber que a estrutura ainda impede passagem.
**Pergunta dramática:** Como tratar uma defesa antiga que continua ativa?

1. **Desviar e não interferir.** → memória: `Alda:_cautela_com_estruturas;_memória:_não_interfere.`
2. **Testar o limite da defesa com cuidado.** → memória: `Oren:_curiosidade_tecnica;_memória:_testa_sistema.`
3. **Tentar descobrir primeiro para quem a defesa parece operar.** → memória: `Alda/Oren:_investigação_de_funcao;_memória:_procura_finalidade.`
**Retorno futuro:** P5: a preparação para a Porta do Poente muda a conversa.
**Identidade contextual:** Classe: Sentinela/Vigia pode ganhar pergunta de leitura de defesa.

#### S4 — Vigília sem Voz
**Nó:** `S4_patrol_reading`
**Momento:** Etapa 5, onde a patrulha muda de direção sem obstáculo.
**Pergunta dramática:** Você trata a mudança como erro ou sinal?

1. **Registrar como anomalia sem explicação.** → memória: `Oren:_disciplina;_memória:_anomalia_documentada.`
2. **Testar a rota novamente.** → memória: `Oren:_experimental;_memória:_verifica_padrao.`
3. **Procurar uma função prática que explique a mudança.** → memória: `Oren:_racionalista;_memória:_busca_funcao.`
**Retorno futuro:** P5/P6: Oren recupera sua postura ao interpretar estruturas.
**Identidade contextual:** Classe: Oráculo pode receber uma formulação de pressentimento sem confirmar causa.

#### S5 — A Luz que Não Aquece
**Nó:** `S5_risk_posture`
**Momento:** Etapa 4, depois de medir direção e duração.
**Pergunta dramática:** Quanto risco você aceita para entender a luz?

1. **Acompanhar o fenômeno até onde for seguro.** → memória: `Oren:_prudente_ousado;_memória:_risco_calculado.`
2. **Encerrar a investigação e registrar o padrão.** → memória: `Oren:_prudente;_memória:_evita_risco.`
3. **Buscar outra testemunha antes de seguir.** → memória: `Oren:_socialmente_cauteloso;_memória:_procura_corroboração.`
**Retorno futuro:** P6: Oren pode usar seu histórico para enquadrar a atitude diante da Âncora.
**Identidade contextual:** Classe: Oráculo ganha linha especial de leitura, sem profecia automática.

#### P5 — A Porta do Poente
**Nó:** `P5_threshold`
**Momento:** Etapa 5, após registrar o símbolo recorrente.
**Pergunta dramática:** O que você fará com uma porta que claramente protege algo?

1. **Entrar assim que possível.** → memória: `Alda:_respeita_ousadia;_memória:_prioridade_descoberta.`
2. **Reunir mais evidência antes de atravessar.** → memória: `Oren:_respeita_prudencia;_memória:_prioridade_evidencia.`
3. **Preparar primeiro uma forma de retorno seguro.** → memória: `Alda:_respeita_planejamento;_memória:_prioridade_retorno.`
**Retorno futuro:** P6: o preâmbulo do Chefe muda conforme o preparo narrativo.
**Identidade contextual:** Classe: Sentinela/Vigia pode abrir opção de preparar defesa/rota.

#### P6 — O Vigia Partido
**Nó:** `P6_anchor_posture`
**Momento:** Etapa 7, depois de registrar Âncora do Poente.
**Pergunta dramática:** O que fazer com o primeiro nome que conecta tudo a uma estrutura maior?

1. **Registrar o nome e não extrapolar.** → memória: `Oren:_rigoroso;_memória:_limites_da_evidencia.`
2. **Procurar outra Âncora para comparar.** → memória: `Alda/Oren:_investigativo;_memória:_busca_corroboração.`
3. **Questionar quem ainda protege essas estruturas e por quê.** → memória: `Alda:_questiona_autoridade;_memória:_pergunta_por_guardioes.`
**Retorno futuro:** P7: o personagem carrega uma postura de investigação ou contenção, não uma resposta pronta.
**Identidade contextual:** Classe: Oráculo pode perguntar sobre presságio sem revelar o futuro.

### 🪢 Vales dos Enforcados

#### S6 — Onde os Nomes Terminaram
**Nó:** `S6_missing_people`
**Momento:** Etapa 5, depois de encontrar o último registro legível da rota.
**Pergunta dramática:** Quando um nome termina sem resposta, o que você faz com a ausência?

1. **Preservar o registro mesmo incompleto.** → memória: `Oren:_preserva_identidade;_memória:_não_apaga_ausencia.`
2. **Procurar mais uma pista para tentar completar o nome.** → memória: `Oren:_investigação;_memória:_busca_resposta.`
3. **Aceitar que a evidência acabou e não inventar uma identidade.** → memória: `Oren:_rigor;_memória:_não_inventa_vazio.`
**Retorno futuro:** P7: o personagem leva para os Vales uma postura definida sobre como tratar pessoas que desapareceram sem registro completo.
**Identidade contextual:** Classe: Luminar pode enfatizar dignidade; Vigia pode enfatizar rastreamento; nenhuma Raça recebe culpa ou privilégio automático.

#### P7 — A Estrada Estrangulada
**Nó:** `P7_route_priority`
**Momento:** Etapa 5, diante da pedra trabalhada sob raízes.
**Pergunta dramática:** O que merece atenção primeiro?

1. **Garantir que a rota continue segura.** → memória: `Dara:_pragmatismo;_memória:_segurança_rotas.`
2. **Examinar a estrutura antiga.** → memória: `Dara:_curiosidade;_memória:_ruina_investigada.`
3. **Marcar a estrutura e voltar depois.** → memória: `Dara:_planejamento;_memória:_preserva_pista.`
**Retorno futuro:** P8: Dara retoma sua prioridade ao escolher a próxima rota.
**Identidade contextual:** Classe: Errante/Vigia recebe leitura de terreno.

#### S7 — Cordas na Névoa
**Nó:** `S7_cordage_reading`
**Momento:** Etapa 3, diante da corda antiga.
**Pergunta dramática:** O que a corda significa para você?

1. **Uma ferramenta de rota que ainda pode salvar alguém.** → memória: `Dara:_utilitario;_memória:_recurso_reaproveitado.`
2. **Um vestígio que pode indicar quem usava a passagem.** → memória: `Iven:_investigativo;_memória:_origem_da_rota.`
3. **Algo que não deve ser tocado antes de entender o contexto.** → memória: `Iven:_cautela;_memória:_preservacao.`
**Retorno futuro:** S10: Dara/Iven podem lembrar sua postura diante de vestígios de passagem.
**Identidade contextual:** Classe: Errante pode sugerir uso prático; Vigia pode notar marcas de tensão.

#### P8 — Entre Galhos Suspensos
**Nó:** `P8_root_hypothesis`
**Momento:** Etapa 4, comparando as três concentrações de raízes.
**Pergunta dramática:** Você aceita uma explicação simples?

1. **Sim, até haver prova do contrário.** → memória: `Dara:_pragmático;_memória:_naturalista.`
2. **Não; procurar padrão intencional.** → memória: `Iven:_curiosidade;_memória:_busca_intencionalidade.`
3. **Manter as duas hipóteses abertas.** → memória: `Dara/Iven:_equilibrado;_memória:_hipoteses_duplas.`
**Retorno futuro:** P9/P10: a hipótese adotada muda como eles apresentam evidências.
**Identidade contextual:** Raça: Velado pode ter uma formulação de percepção, sem afirmar magia.

#### S8 — O Peso da Passagem
**Nó:** `S8_route_policy`
**Momento:** Etapa 5, ao definir a rota alternativa.
**Pergunta dramática:** Que princípio governa a nova rota?

1. **Menor risco imediato.** → memória: `Dara:_segurança;_memória:_risco_minimo.`
2. **Maior capacidade de suportar o próximo ciclo.** → memória: `Dara:_sustentabilidade;_memória:_longo_prazo.`
3. **Menor custo para quem mantém a passagem.** → memória: `Dara:_comunidade;_memória:_custo_compartilhado.`
**Retorno futuro:** S11: Dara pode lembrar qual custo você considera aceitável.
**Identidade contextual:** Classe: Sentinela pode abrir leitura de sustentação.

#### P9 — Sob a Madeira Morta
**Nó:** `P9_priority`
**Momento:** Etapa 5, depois de encontrar Baixios e registros.
**Pergunta dramática:** Quando vivos e registros entram em tensão, o que vem primeiro?

1. **Segurança dos vivos.** → memória: `Iven:_proteção;_memória:_vivos_primeiro.`
2. **Preservação do registro a qualquer custo razoável.** → memória: `Iven:_documental;_memória:_registro_primeiro.`
3. **Tentar proteger ambos mesmo com custo de tempo.** → memória: `Iven:_equilíbrio;_memória:_dupla_prioridade.`
**Retorno futuro:** P10/P11: Iven pode confiar mais sua investigação ao personagem.
**Identidade contextual:** Classe: Luminar/Sentinela pode reforçar proteção; Tecelão pode reforçar registro.

#### S9 — Sob a Casca
**Nó:** `S9_focus`
**Momento:** Etapa 4, após encontrar o padrão na casca.
**Pergunta dramática:** Você segue o fenômeno ou o problema prático?

1. **Seguir o fenômeno.** → memória: `Iven:_curioso;_memória:_segue_fenomeno.`
2. **Manter foco na ameaça local.** → memória: `Iven:_pragmático;_memória:_foco_ameaca.`
3. **Registrar a pista e voltar ao objetivo principal.** → memória: `Iven:_disciplinado;_memória:_não_abandona_objetivo.`
**Retorno futuro:** P10: Iven pode escolher confiar primeiro suas hipóteses ao personagem.
**Identidade contextual:** Raça: Cinéreo pode comentar persistência do terreno sem estereótipo.

#### P10 — Pedra sob as Raízes
**Nó:** `P10_structure_policy`
**Momento:** Etapa 4, diante da estrutura antiga no Claustro.
**Pergunta dramática:** O que fazer com algo que ainda funciona parcialmente?

1. **Preservar e contornar.** → memória: `Iven:_preservacionista;_memória:_não_destroi.`
2. **Testar seu comportamento para entender o limite.** → memória: `Iven:_experimental;_memória:_testa_limites.`
3. **Priorizar a passagem mesmo que a estrutura seja perdida.** → memória: `Iven:_pragmatismo_aceito;_memória:_custo_de_acesso.`
**Retorno futuro:** P11: a equipe pode discordar de você sem romper a confiança.
**Identidade contextual:** Classe: Sentinela/Vigia pode reconhecer mecanismo defensivo.

#### S10 — Água sem Reflexo
**Nó:** `S10_codex_method`
**Momento:** Etapa 6, ao registrar o fenômeno.
**Pergunta dramática:** Como o Códice deve tratar algo que você não consegue explicar?

1. **Fato observado, sem interpretação.** → memória: `Dara:_rigor;_memória:_observação_pura.`
2. **Hipótese explicitamente marcada.** → memória: `Iven:_raciocínio;_memória:_hipotese_marcada.`
3. **Comparação com testemunhas antes de registrar conclusão.** → memória: `Dara:_corroboração;_memória:_busca_testemunho.`
**Retorno futuro:** S12: a escolha define como os registros sobre os Vales são compostos.
**Identidade contextual:** Classe: Oráculo recebe reação especial para intuição sem afirmar verdade.

#### S11 — A Guarda que Não Dorme
**Nó:** `S11_guard_belief`
**Momento:** Etapa 3, diante do padrão de guarda persistente.
**Pergunta dramática:** Você trata o padrão como confiável?

1. **Sim, até encontrar contradição.** → memória: `Iven:_respeita_consistencia;_memória:_confiança_no_padrao.`
2. **Não, porque função antiga pode estar fora de contexto.** → memória: `Iven:_crítico;_memória:_contexto_importa.`
3. **Testar o padrão com uma hipótese controlada.** → memória: `Iven:_científico;_memória:_teste_controlado.`
**Retorno futuro:** P12: o personagem entra no clímax com uma postura definida diante de sistemas antigos.
**Identidade contextual:** Classe: Vigia/Sentinela pode ler protocolo de guarda.

#### P11 — Onde Tudo se Enreda
**Nó:** `P11_conflicting_evidence`
**Momento:** Etapa 5, diante de evidências conflitantes.
**Pergunta dramática:** Quando duas leituras parecem plausíveis, como agir?

1. **Escolher a leitura mais conservadora.** → memória: `Dara/Iven:_cauteloso;_memória:_conserva_duvida.`
2. **Escolher a leitura que melhor explica os fatos.** → memória: `Iven:_analítico;_memória:_modelo_explicativo.`
3. **Preservar as duas e agir pelo risco mais baixo.** → memória: `Dara:_segurança;_memória:_duas_hipoteses.`
**Retorno futuro:** P12: a equipe poderá apresentar a questão do Berço segundo sua postura.
**Identidade contextual:** Raça + Classe: Velado + Oráculo pode receber uma linha sobre percepção, nunca verdade absoluta.

#### P12 — A Matriarca das Raízes
**Nó:** `P12_climax_interpretation`
**Momento:** Etapa 7, depois da vitória.
**Pergunta dramática:** O que a vitória permite afirmar sobre os Vales?

1. **Só o que foi observado diretamente.** → memória: `Iven:_rigor;_memória:_pós_chefe_evidencia.`
2. **A ameaça é maior do que o que ainda conseguimos explicar.** → memória: `Dara:_prudência;_memória:_ameaça_aberta.`
3. **Temos informação suficiente para seguir investigando além da região.** → memória: `Ambos:_confiança;_memória:_impulso_investigativo.`
**Retorno futuro:** P13: o personagem leva uma postura de investigação, não uma solução cosmológica.
**Identidade contextual:** Classe: Oráculo pode interpretar pressentimento apenas como reação pessoal.

#### S12 — Os Nomes Presos à Madeira
**Nó:** `S12_names_policy`
**Momento:** Etapa 6, no último conjunto de nomes.
**Pergunta dramática:** O que vale mais: significado ou preservação?

1. **Descobrir o significado.** → memória: `Iven:_interpretação;_memória:_significado_primeiro.`
2. **Preservar os nomes mesmo sem entendê-los.** → memória: `Iven:_respeito;_memória:_preserva_nomes.`
3. **Comparar nomes com rotas e pessoas antes de interpretar.** → memória: `Iven:_corroboração;_memória:_nomes_contexto.`
**Retorno futuro:** Nareth: qualquer retorno à questão de registros pode lembrar o método.
**Identidade contextual:** Classe: Vigia pode priorizar evidência de percurso; Luminar, identidade das pessoas.

### 🌾 Planícies de Nareth

#### P13 — Linhas no Horizonte
**Nó:** `P13_reference_method`
**Momento:** Etapa 5, depois de chegar ao Posto.
**Pergunta dramática:** Qual referência deve guiar a próxima decisão?

1. **Viajar pela referência usada pelos moradores atuais.** → memória: `Nera:_confiança_comunidade;_memória:_referência_local.`
2. **Confiar nos marcos antigos enquanto testa a rota.** → memória: `Nera:_respeito_ao_arquivo;_memória:_referencia_antiga.`
3. **Comparar as duas antes de escolher.** → memória: `Nera:_método;_memória:_valida_duas_fontes.`
**Retorno futuro:** P14: Nera adapta seus próximos mapas conforme seu método.
**Identidade contextual:** Classe: Vigia recebe leitura de marcos; Errante, leitura de rota.

#### S13 — Pedras que Apontam
**Nó:** `S13_trust_marker`
**Momento:** Etapa 6, ao classificar o terceiro marco.
**Pergunta dramática:** Qual dos três marcos merece confiança provisória?

1. **O usado pelos viajantes atuais.** → memória: `Nera:_prática;_memória:_tradição_atual.`
2. **O mais antigo e ainda legível.** → memória: `Nera:_documental;_memória:_antiguidade_importa.`
3. **Nenhum sem uma rota de teste.** → memória: `Nera:_ceticismo;_memória:_validação_empírica.`
**Retorno futuro:** P14/S14: a próxima orientação pode refletir sua preferência.
**Identidade contextual:** Classe: Vigia pode abrir exame de desgaste/ângulo.

#### P14 — O Canal sem Norte
**Nó:** `P14_map_vs_world`
**Momento:** Etapa 5, diante da infraestrutura que contradiz o mapa.
**Pergunta dramática:** O que fazer quando a construção e o mapa discordam?

1. **Seguir a estrutura real.** → memória: `Nera:_pragmatismo;_memória:_mundo_atual.`
2. **Seguir o mapa e investigar onde a estrutura divergiu.** → memória: `Nera:_preservação_historica;_memória:_arquivo_atualizado.`
3. **Registrar a divergência antes de decidir.** → memória: `Nera:_rigor;_memória:_discrepancia_formal.`
**Retorno futuro:** P15: Talen recebe a abordagem adotada como ponto de partida.
**Identidade contextual:** Classe: Vigia/Tecelão pode notar detalhe técnico; Alvorano pode ter reação de organização sem nobreza implícita.

#### S14 — O Peso da Distância
**Nó:** `S14_route_cost`
**Momento:** Etapa 6, com a rota de suprimentos.
**Pergunta dramática:** Qual prioridade deve guiar a correção?

1. **Chegar mais rápido.** → memória: `Nera:_urgencia;_memória:_tempo_primeiro.`
2. **Reduzir o risco de erro futuro.** → memória: `Nera:_planejamento;_memória:_confiabilidade_primeiro.`
3. **Deixar uma rota redundante mesmo que leve mais tempo.** → memória: `Nera:_resiliencia;_memória:_redundancia.`
**Retorno futuro:** P16: Nera pode confiar ao personagem uma tarefa mais sensível.
**Identidade contextual:** Classe: Errante pode reconhecer risco de percurso; Sentinela, redundância.

#### P15 — A Distância Errada
**Nó:** `P15_anomaly_method`
**Momento:** Etapa 5, quando a discrepância deixa de parecer erro simples.
**Pergunta dramática:** Você força uma explicação ou preserva a anomalia?

1. **Testar a explicação mais simples primeiro.** → memória: `Talen:_racionalidade;_memória:_simples_primeiro.`
2. **Marcar a discrepância como não resolvida.** → memória: `Talen:_rigor;_memória:_não_resolvido.`
3. **Procurar uma terceira medição.** → memória: `Talen:_investigação;_memória:_terceira_verificação.`
**Retorno futuro:** P16/P17: Talen escolhe que tipo de dado compartilhar primeiro.
**Identidade contextual:** Classe: Oráculo pode perguntar sobre sensação de desvio; Tecelão sobre estrutura.

#### S15 — Sob o Mesmo Céu
**Nó:** `S15_result_vs_cause`
**Momento:** Etapa 5, quando a rota correta parte de um ponto aparentemente errado.
**Pergunta dramática:** O que você prefere: resultado ou explicação?

1. **Chegar ao destino primeiro.** → memória: `Talen:_pragmático;_memória:_resultado_primeiro.`
2. **Entender o ponto de partida antes de seguir.** → memória: `Talen:_curioso;_memória:_causa_primeiro.`
3. **Fazer a rota e registrar os dois fatos.** → memória: `Talen:_método;_memória:_fato_e_causa.`
**Retorno futuro:** S16: Talen usa esse padrão para apresentar o mapa.
**Identidade contextual:** Classe: Errante recebe opção de leitura de terreno.

#### P16 — O Eixo sob a Terra
**Nó:** `P16_axis_priority`
**Momento:** Etapa 7, diante do Vigia e do mecanismo.
**Pergunta dramática:** O que merece prioridade durante a descoberta?

1. **Garantir que o mecanismo não cause dano.** → memória: `Talen:_segurança;_memória:_preserva_operacao.`
2. **Entender como ele mede referências.** → memória: `Talen:_investigação;_memória:_função_primeiro.`
3. **Registrar tudo antes de tocar.** → memória: `Nera:_documentação;_memória:_cadeia_de_evidencia.`
**Retorno futuro:** P17: o registro técnico disponível pode ser apresentado de modo diferente.
**Identidade contextual:** Classe: Tecelão/Vigia ganha linha técnica; Sentinela, segurança.

#### S16 — Cartografia do Erro
**Nó:** `S16_mapping_policy`
**Momento:** Etapa 7, ao decidir o que entra no mapa.
**Pergunta dramática:** O que merece ser desenhado como rota?

1. **Somente caminhos verificados.** → memória: `Nera:_rigor;_memória:_mapa_conservador.`
2. **Incluir rotas antigas com aviso de risco.** → memória: `Nera:_memória_historica;_memória:_arquivo_util.`
3. **Marcar as divergências como camada separada.** → memória: `Nera:_transparência;_memória:_contradição_visível.`
**Retorno futuro:** P17: Nera confia em você para comparar fontes.
**Identidade contextual:** Classe: Vigia/Errante pode ter formulação própria de mapa.

#### S17 — O Prumo Afundado
**Nó:** `S17_calibration_policy`
**Momento:** Etapa 5, com a peça de calibração.
**Pergunta dramática:** O que fazer com uma peça que pode ser útil, mas é pouco compreendida?

1. **Devolver sem experimentar.** → memória: `Talen:_cautela;_memória:_não_experimenta.`
2. **Testar o funcionamento de modo controlado.** → memória: `Talen:_experimental;_memória:_teste_calibrado.`
3. **Registrar o estado e deixar para análise posterior.** → memória: `Talen:_planejamento;_memória:_adia_intervencao.`
**Retorno futuro:** P17: a abordagem influencia como a equipe trata o mecanismo central.
**Identidade contextual:** Classe: Tecelão pode abrir uma leitura técnica da peça.

#### P17 — Medir o que Permanece
**Nó:** `P17_veil_evidence`
**Momento:** Etapa 8, ao acessar o registro que liga Âncoras e Véu.
**Pergunta dramática:** Como reagir ao primeiro vínculo explícito com o Véu?

1. **Aceitar como evidência suficiente.** → memória: `Nera/Talen:_confiança;_memória:_aceita_registro.`
2. **Tratar como registro incompleto.** → memória: `Nera:_rigor;_memória:_registro_incompleto.`
3. **Buscar outra fonte antes de usar a conclusão.** → memória: `Talen:_investigativo;_memória:_corrobora_véu.`
**Retorno futuro:** P18: o preâmbulo do Arconte reconhece sua postura.
**Identidade contextual:** Raça: Velado pode receber linha de percepção; Classe: Oráculo/Tecelão pode abrir pergunta contextual.

#### P18 — O Arconte Invertido
**Nó:** `P18_anchors_posture`
**Momento:** Etapa final, após a revelação sobre Âncoras.
**Pergunta dramática:** O que você fará com o que aprendeu sobre a função das Âncoras?

1. **Registrar e preservar o conhecimento.** → memória: `Talen:_confiança;_memória:_arquivista_da_verdade.`
2. **Buscar confirmação em outras regiões.** → memória: `Nera:_investigativo;_memória:_atravessa_fronteiras.`
3. **Questionar quem decidiu usar as Âncoras e com quais custos.** → memória: `Talen/Nera:_crítico;_memória:_pergunta_por_responsabilidade.`
**Retorno futuro:** P19: a postura regional viaja como memória pessoal; não como segredo que todos conhecem.
**Identidade contextual:** Classe: Oráculo/Vigia pode receber linha extra sobre leitura; Alvorano não ganha autoridade automática.

#### S18 — Os Caminhos que Não Coincidem
**Nó:** `S18_route_closure`
**Momento:** Etapa 5, diante da rota obsoleta.
**Pergunta dramática:** Você resolve o problema atual ou preserva a rota antiga como evidência?

1. **Encerrar a rota e priorizar os viajantes.** → memória: `Nera:_comunidade;_memória:_presente_primeiro.`
2. **Manter a rota documentada, mesmo sem uso.** → memória: `Nera:_arquivo;_memória:_preserva_passado.`
3. **Testar se ainda existe alguma utilidade antes de fechar.** → memória: `Nera:_método;_memória:_encerra_com_testes.`
**Retorno futuro:** P19: memória pessoal de relação entre segurança e evidência.
**Identidade contextual:** Classe: Errante/Vigia pode abrir leitura da rota.

### 🥀 Várzeas Carmesins

#### P19 — Águas de Ferro
**Nó:** `P19_priority`
**Momento:** Etapa 6, chegada ao Porto.
**Pergunta dramática:** O que merece sua prioridade agora?

1. **Rotas e segurança.** → memória: `Sera:_confiança_pratica;_memória:_segurança.`
2. **Entender a infraestrutura antiga.** → memória: `Sera:_curiosidade_tecnica;_memória:_infraestrutura.`
3. **Ouvir primeiro quem vive ali.** → memória: `Sera:_empatia_local;_memória:_pessoas_primeiro.`
**Retorno futuro:** P20: Sera enquadra o pulso conforme sua prioridade.
**Identidade contextual:** Classe: Sentinela/Luminar podem ter reação de proteção; Hemário pode receber linha sobre cuidado sem culpa histórica.

#### S19 — Sal nas Feridas
**Nó:** `S19_response`
**Momento:** Etapa 4, após verificar a origem imediata do problema.
**Pergunta dramática:** Quando um problema é urgente e antigo, o que vem primeiro?

1. **Reparar agora.** → memória: `Sera:_pragmatismo;_memória:_reparo_primeiro.`
2. **Descobrir por que continua acontecendo.** → memória: `Sera:_investigação;_memória:_causa_primeiro.`
3. **Registrar o risco e criar um plano de contenção.** → memória: `Sera:_planejamento;_memória:_contenção.`
**Retorno futuro:** S20: Sera pode lembrar do método.
**Identidade contextual:** Classe: Luminar pode priorizar cuidado; Sentinela, segurança estrutural.

#### P20 — O Pulso sob a Lama
**Nó:** `P20_pulse_interpretation`
**Momento:** Etapa 4, diante do pulso periódico.
**Pergunta dramática:** Como tratar algo cujo significado ainda é incerto?

1. **Como ameaça até prova contrária.** → memória: `Sera:_cautela;_memória:_risco_primeiro.`
2. **Como fenômeno físico a ser medido.** → memória: `Ilyan:_rigor;_memória:_mede_fenomeno.`
3. **Como sinal de infraestrutura antiga que merece investigação.** → memória: `Ilyan:_histórico;_memória:_busca_funcao.`
**Retorno futuro:** P21: Ilyan apresenta Hemaris de acordo com o método escolhido.
**Identidade contextual:** Raça: Velado pode receber percepção; Hemário recebe respeito, não culpa.

#### S20 — Um Corpo que Continua
**Nó:** `S20_ethics`
**Momento:** Etapa 4, diante do dilema sobre o que está sendo preservado.
**Pergunta dramática:** Qual é o limite entre preservar vida e transformar vida em recurso?

1. **Vida vem antes do protocolo.** → memória: `Ilyan:_respeito;_memória:_vida_primeiro.`
2. **O protocolo merece ser entendido antes de julgá-lo.** → memória: `Ilyan:_analítico;_memória:_entende_antes_de_julgar.`
3. **Interromper qualquer processo que não tenha consentimento claro.** → memória: `Ilyan:_ética_firme;_memória:_consentimento_primeiro.`
**Retorno futuro:** P21/P22: Ilyan reconhece sua posição ao abordar o Projeto.
**Identidade contextual:** Hemário: opção de responder pessoalmente ao tema sem admitir culpa ancestral.

#### P21 — Os Hortos Vazios
**Nó:** `P21_hemeris_archive`
**Momento:** Etapa 5, ao identificar função médica/biológica.
**Pergunta dramática:** Como preservar um legado médico comprometido?

1. **Salvar os registros úteis e descartar o resto.** → memória: `Ilyan:_utilitario;_memória:_separa_uso_de_abuso.`
2. **Preservar tudo para impedir que a história seja apagada.** → memória: `Ilyan:_arquivista;_memória:_preserva_totalidade.`
3. **Separar evidência, prática e abuso em registros distintos.** → memória: `Ilyan:_rigor;_memória:_distingue_camadas.`
**Retorno futuro:** P22: os protocolos são apresentados conforme sua leitura ética.
**Identidade contextual:** Hemário recebe opção especial de comentar como o nome Hemaris é tratado, sem culpa.

#### S21 — Cicatrizes de Cultivo
**Nó:** `S21_resource_ethic`
**Momento:** Etapa 3, diante de cultivo antigo ainda funcional.
**Pergunta dramática:** O que fazer com um recurso que poderia ser útil hoje?

1. **Reaproveitar imediatamente.** → memória: `Ilyan:_pragmático;_memória:_reaproveita.`
2. **Preservar e estudar antes de usar.** → memória: `Ilyan:_cauteloso;_memória:_estudo_antes_de_uso.`
3. **Deixar intacto por não saber o custo.** → memória: `Ilyan:_prudente;_memória:_evita_risco_desconhecido.`
**Retorno futuro:** S22: o protocolo legado é lido à luz dessa escolha.
**Identidade contextual:** Classe: Alquimia não é Classe; Luminar pode reagir sobre cuidado, não profissão.

#### P22 — Transferência
**Nó:** `P22_protocol_response`
**Momento:** Etapa 5, diante dos protocolos que redistribuem recursos biológicos.
**Pergunta dramática:** Você interrompe o sistema, obedece ao protocolo ou registra antes?

1. **Interromper a rotina de uso da vida.** → memória: `Ilyan:_confiança_ética;_memória:_interrompe_coercao.`
2. **Deixar funcionar enquanto documenta o máximo possível.** → memória: `Ilyan:_tensão;_memória:_testemunha_o_abuso.`
3. **Buscar uma forma de limitar o dano sem destruir o registro.** → memória: `Ilyan:_pragmatismo_etico;_memória:_reduz_dano.`
**Retorno futuro:** P23: Ilyan pode confiar ou desconfiar da sua disposição para cortar sistemas antigos.
**Identidade contextual:** Hemário recebe linha de identidade forte, mas nunca de culpa coletiva.

#### S22 — Protocolos sem Paciente
**Nó:** `S22_protocol_legacy`
**Momento:** Etapa 4, ao encontrar protocolo sem sujeito.
**Pergunta dramática:** O que fazer com uma ordem que ninguém mais pode executar legitimamente?

1. **Arquivar como evidência.** → memória: `Ilyan:_documental;_memória:_prova_historica.`
2. **Desmontar o protocolo para impedir uso indevido.** → memória: `Ilyan:_protetor;_memória:_bloqueia_repeticao.`
3. **Manter o protocolo intacto, mas marcado como não aplicável.** → memória: `Ilyan:_preservacionista;_memória:_contexto_preservado.`
**Retorno futuro:** S24/P24: postura diante de legado técnico retorna.
**Identidade contextual:** Hemário: resposta pode reconhecer o peso histórico sem transformar o personagem em símbolo racial.

#### S23 — Fluxo de Emergência
**Nó:** `S23_priority`
**Momento:** Etapa 5, diante de prioridades conflitantes de recursos.
**Pergunta dramática:** Quem deve receber prioridade?

1. **Quem está em risco imediato.** → memória: `Sera:_pragmatismo;_memória:_urgencia_humana.`
2. **Quem sustenta a infraestrutura de todos.** → memória: `Sera:_continuidade;_memória:_sistema_primeiro.`
3. **Distribuir a decisão entre os dois riscos.** → memória: `Sera:_equilibrio;_memória:_peso_compartilhado.`
**Retorno futuro:** P24: Sera lembra sua lógica ao conversar sobre a Matriz.
**Identidade contextual:** Classe: Sentinela pode ter linha de proteção.

#### P23 — O Custo da Persistência
**Nó:** `P23_continuity_cost`
**Momento:** Etapa 5, depois de compreender o custo humano do sistema.
**Pergunta dramática:** Quanto custo você aceita para manter uma função útil?

1. **Nenhum custo humano adicional.** → memória: `Sera/Ilyan:_respeito_ético;_memória:_limite_humano.`
2. **Custo limitado se salvar mais vidas agora.** → memória: `Ilyan:_pragmatismo;_memória:_utilidade_sobre_custo.`
3. **Preservar o sistema somente se houver consentimento e controle.** → memória: `Sera:_equilíbrio;_memória:_continuidade_com_limites.`
**Retorno futuro:** P24: a pergunta sobre a Matriz é moldada pela resposta.
**Identidade contextual:** Hemário recebe reação que separa sua existência da história do projeto.

#### P24 — A Matriz Rubra
**Nó:** `P24_legacy_judgment`
**Momento:** Etapa 6, após confrontar a Matriz.
**Pergunta dramática:** O que você leva da Matriz como julgamento?

1. **Era uma máquina útil que foi deixada sem supervisão.** → memória: `Ilyan:_nuance;_memória:_sistema_sem_moralidade.`
2. **O problema central foi o uso humano coercitivo.** → memória: `Ilyan:_responsabiliza_agentes;_memória:_agencia_humana.`
3. **Ambas as coisas importam e não devem ser confundidas.** → memória: `Sera/Ilyan:_maturidade;_memória:_separa_sistema_e_responsabilidade.`
**Retorno futuro:** Altos: personagem leva uma postura sobre continuidade, responsabilidade e custo.
**Identidade contextual:** Hemário: linha especial sobre não herdar culpa; Alvorano não aparece aqui como autoridade.

#### S24 — A Porta de Quarentena
**Nó:** `S24_quarantine_choice`
**Momento:** Etapa 5, quando segurança e resgate entram em conflito.
**Pergunta dramática:** Quem ou o que recebe prioridade?

1. **Conter o risco primeiro.** → memória: `Ilyan:_segurança;_memória:_quarentena_primeiro.`
2. **Salvar quem ainda pode ser alcançado.** → memória: `Sera:_proteção;_memória:_resgate_primeiro.`
3. **Criar uma contenção mínima para tentar os dois.** → memória: `Sera/Ilyan:_respeito;_memória:_risco_com_contencao.`
**Retorno futuro:** Altos: pode haver referência a quem você prioriza em crises.
**Identidade contextual:** Classe: Sentinela/Luminar pode receber resposta contextual.

### ⛰️ Altos Cinéreos

#### P25 — O Peso Antigo
**Nó:** `P25_infrastructure_ethic`
**Momento:** Etapa 5, ao escolher a rota de sustentação.
**Pergunta dramática:** Qual princípio deve governar uma estrutura carregada?

1. **Manter a função atual.** → memória: `Rava:_continuidade;_memória:_função_primeiro.`
2. **Questionar se a função ainda serve aos moradores.** → memória: `Rava:_crítico;_memória:_função_deve_servir.`
3. **Buscar uma alternativa que preserve ambos.** → memória: `Rava:_planejamento;_memória:_sustentacao_alternativa.`
**Retorno futuro:** P26: ordens de emergência são apresentadas conforme sua confiança em continuidade.
**Identidade contextual:** Cinéreo: reação ligada a tenacidade, nunca cultura tribal.

#### S25 — A Ponte que Espera
**Nó:** `S25_priority`
**Momento:** Etapa 4, na disputa de prioridade de manutenção.
**Pergunta dramática:** Qual grupo deve receber a ponte primeiro?

1. **Quem corre maior risco agora.** → memória: `Rava:_urgencia;_memória:_risco_imediato.`
2. **Quem não tem alternativa de rota.** → memória: `Rava:_equidade;_memória:_vulnerabilidade.`
3. **Dividir o reparo em etapas para atender os dois.** → memória: `Rava:_planejamento;_memória:_solução_compartilhada.`
**Retorno futuro:** S26: prioridade de turnos pode refletir isso.
**Identidade contextual:** Classe: Sentinela pode reconhecer risco estrutural.

#### P26 — Ordens de Emergência
**Nó:** `P26_authority`
**Momento:** Etapa 6, diante de ordens conflitantes.
**Pergunta dramática:** O que fazer quando duas ordens parecem legítimas?

1. **Cumprir a mais recente.** → memória: `Rava:_disciplina;_memória:_ordem_recente.`
2. **Investigar a autoridade e o contexto de ambas.** → memória: `Rava:_ceticismo;_memória:_examina_autoridade.`
3. **Executar apenas o que protege vidas sem depender da hierarquia.** → memória: `Rava:_pragmatismo;_memória:_vidas_acima_ordem.`
**Retorno futuro:** P27/P28: registros de emergência podem ser lembrados conforme sua postura.
**Identidade contextual:** Classe: Sentinela ganha linha de dever; Oráculo de dúvida.

#### S26 — Turno sem Fim
**Nó:** `S26_burden_policy`
**Momento:** Etapa 4, diante de rotina que produz desgaste.
**Pergunta dramática:** O que vale mais: continuidade ou limite?

1. **Manter o turno até a falha.** → memória: `Rava:_desconfia_do_limite;_memória:_continuidade_excessiva.`
2. **Impor um limite e redistribuir carga.** → memória: `Rava:_respeita_limites;_memória:_limite_humano.`
3. **Documentar o desgaste antes de decidir.** → memória: `Rava:_rigor;_memória:_custo_documentado.`
**Retorno futuro:** P27: a questão do custo aparece novamente.
**Identidade contextual:** Cinéreo pode comentar resistência física, sem presumir que aguenta tudo.

#### P27 — A Continuidade a Qualquer Custo
**Nó:** `P27_continuity_cost`
**Momento:** Etapa 5, quando o preço da manutenção fica claro.
**Pergunta dramática:** Até onde o personagem aceita pagar para manter a estrutura?

1. **Manter a estrutura, mesmo com sacrifício controlado.** → memória: `Memória_global:_aceita_custo_controlado.`
2. **Recusar qualquer sacrifício humano adicional.** → memória: `Memória_global:_recusa_coercao.`
3. **Buscar uma terceira solução mesmo que atrase a resposta.** → memória: `Memória_global:_resolve_sem_coerção.`
**Retorno futuro:** P28/P29: o personagem já tem uma postura sobre continuidade versus pessoas.
**Identidade contextual:** Cinéreo/Hemário podem receber reação contextual sem transformar raça em moralidade.

#### S27 — Cabo Partido
**Nó:** `S27_repair_policy`
**Momento:** Etapa 3, depois de localizar a falha.
**Pergunta dramática:** Você repara ou procura a causa?

1. **Reparar agora.** → memória: `Rava:_pragmatismo;_memória:_reparo_imediato.`
2. **Descobrir por que partiu antes de reparar.** → memória: `Rava:_investigação;_memória:_causa_primeiro.`
3. **Registrar a falha, estabilizar e investigar depois.** → memória: `Rava:_método;_memória:_estabiliza_e_investiga.`
**Retorno futuro:** S30: a postura sobre manutenção volta a ser relevante.
**Identidade contextual:** Classe: Errante pode ter leitura de esforço/movimento.

#### P28 — Os Desvelados
**Nó:** `P28_dissident_reading`
**Momento:** Etapa 4, ao montar o quadro da dissidência.
**Pergunta dramática:** Como interpretar pessoas que começaram com críticas legítimas e depois radicalizaram?

1. **Críticas legítimas não justificam sabotagem.** → memória: `Rava/Eris:_nuance;_memória:_separa_critica_e_crime.`
2. **O contexto importa antes do julgamento.** → memória: `Eris:_contextual;_memória:_contexto_antes_de_julgamento.`
3. **A sabotagem mudou o peso moral do grupo.** → memória: `Eris:_responsabiliza_ato;_memória:_ato_com_consequencia.`
**Retorno futuro:** P29: a discussão sobre Convergência reconhece sua leitura.
**Identidade contextual:** Alvorano pode receber resposta sobre arquivo institucional; Cinéreo sobre custo material, sem estereótipo.

#### S28 — Cartas de Emergência
**Nó:** `S28_source_policy`
**Momento:** Etapa 5, ao escolher como preservar cartas conflitantes.
**Pergunta dramática:** Como você registra uma ordem que pode contradizer outra?

1. **Preservar ambas lado a lado.** → memória: `Memória:_preserva_fontes.`
2. **Escolher a mais confiável e anotar por quê.** → memória: `Memória:_hierarquiza_fontes.`
3. **Registrar a contradição como problema ainda aberto.** → memória: `Memória:_mantém_contradição.`
**Retorno futuro:** S29: a investigação dos que disseram não retoma esse método.
**Identidade contextual:** Classe: Vigia recebe leitura de procedência documental.

#### P29 — Antes da Convergência
**Nó:** `P29_convergence_ethic`
**Momento:** Etapa 5, quando o risco da intervenção fica claro.
**Pergunta dramática:** Como julgar uma solução que poderia salvar gerações e ainda assim era perigosa?

1. **Pelo benefício esperado.** → memória: `Memória:_utilidade_historica.`
2. **Pelo risco que não podia ser ignorado.** → memória: `Memória:_risco_primeiro.`
3. **Pelo fato de que ninguém tinha uma opção segura.** → memória: `Memória:_tragédia_sem_simplificação.`
**Retorno futuro:** P30: interpretação da sabotagem e Regência pode usar esta postura.
**Identidade contextual:** Oráculo/Tecelão podem ter linguagem própria sobre incerteza, sem previsão.

#### S29 — Os que Disseram Não
**Nó:** `S29_refusal`
**Momento:** Etapa 4, diante da recusa de uma ordem.
**Pergunta dramática:** Você julga a recusa como quê?

1. **Desobediência perigosa.** → memória: `Memória:_ordem_tem_peso.`
2. **Resistência legítima diante de uma ordem ruim.** → memória: `Memória:_questiona_autoridade.`
3. **Uma decisão compreensível que ainda teve consequências.** → memória: `Memória:_entende_sem__absolver.`
**Retorno futuro:** P30: o quadro de responsabilidade pode recuperar essa leitura.
**Identidade contextual:** Classe: Sentinela pode ter linha sobre dever; Errante sobre independência.

#### P30 — O Colosso Cinéreo
**Nó:** `P30_accountability`
**Momento:** Etapa 9, após a descoberta da sabotagem.
**Pergunta dramática:** Como registrar responsabilidade pelo que aconteceu?

1. **Nomear os atos e seus autores conhecidos.** → memória: `Memória:_responsabilidade_especifica.`
2. **Registrar apenas a cadeia de fatores.** → memória: `Memória:_causalidade_sistemica.`
3. **Manter os dois: ato individual e contexto sistêmico.** → memória: `Memória:_responsabilidade_e_contexto.`
**Retorno futuro:** Confins: essa postura influencia como o personagem lê Regência/Desvelados, sem que NPCs mágicos saibam.
**Identidade contextual:** Cinéreo recebe identidade contextual de presença física e custo, não autoridade racial.

#### S30 — A Ordem que Restou
**Nó:** `S30_legacy_routine`
**Momento:** Etapa 5, quando uma rotina antiga não tem mais autoridade clara.
**Pergunta dramática:** O que merece sobreviver?

1. **O procedimento mais comprovado.** → memória: `Memória:_preserva_procedimento.`
2. **O procedimento mais útil para os moradores.** → memória: `Memória:_utilidade_atual.`
3. **Um procedimento novo que combine ambos.** → memória: `Memória:_reforma_continua.`
**Retorno futuro:** Confins: Haro/Sera podem reconhecer sua relação com tradição e mudança.
**Identidade contextual:** Classe: Sentinela/Tecelão podem receber formulações de procedimento.

### 🌫️ Confins do Véu

#### P31 — Onde o Véu Afina
**Nó:** `P31_source_conflict`
**Momento:** Etapa 4, após duas leituras honestas incompatíveis.
**Pergunta dramática:** Como registrar duas versões que não cabem na mesma linha do tempo?

1. **Preservar ambas.** → memória: `Sera:_rigor;_memória:_fontes_preservadas.`
2. **Escolher a que tem melhor cadeia de custódia.** → memória: `Roven:_método;_memória:_procedencia_primeiro.`
3. **Registrar o conflito sem declarar vencedor.** → memória: `Sera/Roven:_maturidade;_memória:_conflito_aberto.`
**Retorno futuro:** S32/S35/P34: forma de tratamento de documentos reaparece.
**Identidade contextual:** Alvorano pode ter linha sobre arquivo; Velado sobre percepção de discrepância, sem magia automática.

#### S31 — Duas Vezes a Mesma Estrada
**Nó:** `S31_trail_method`
**Momento:** Etapa 5, comparando pegadas incompatíveis.
**Pergunta dramática:** O que você faz com duas trilhas plausíveis?

1. **Seguir a que tem mais evidência física.** → memória: `Talen:_empirico;_memória:_evidencia_fisica.`
2. **Preservar ambas e comparar o retorno.** → memória: `Talen:_experimental;_memória:_rota_comparada.`
3. **Não seguir nenhuma sem testemunha.** → memória: `Talen:_cautela;_memória:_evita_risco_inexplicado.`
**Retorno futuro:** P32: Talen reconhece seu método de investigação.
**Identidade contextual:** Classe: Errante/Vigia podem ter fala de terreno.

#### P32 — A Fratura
**Nó:** `P32_fracture_language`
**Momento:** Etapa 3, quando o fenômeno precisa ser nomeado.
**Pergunta dramática:** Como tratar algo que agora tem um nome, mas não uma explicação completa?

1. **Usar o termo e registrar limites.** → memória: `Roven:_rigor;_memória:_nome_sem_extrapolacao.`
2. **Evitar o termo até haver explicação.** → memória: `Roven:_ceticismo;_memória:_exige_definicao.`
3. **Usar o termo como ferramenta descritiva, não como entidade.** → memória: `Sera:_precisão;_memória:_termo_descritivo.`
**Retorno futuro:** P33: a escolha prepara a introdução do Avesso.
**Identidade contextual:** Velado pode receber linha de sensibilidade ao fenômeno sem explicá-lo.

#### S32 — A Casa que Não Chegou
**Nó:** `S32_record_conflict`
**Momento:** Etapa 5, comparando fichas de presença/ausência.
**Pergunta dramática:** Qual registro deve vencer?

1. **O que a matéria física demonstra.** → memória: `Roven:_material;_memória:_prova_material.`
2. **O documento com melhor cadeia de custódia.** → memória: `Roven:_documental;_memória:_cadeia_de_custodia.`
3. **Nenhum; preservar a coexistência.** → memória: `Roven:_respeito;_memória:_coexistencia_preservada.`
**Retorno futuro:** S35: ordem documental e matéria voltam a divergir.
**Identidade contextual:** Hemário Haro pode reagir ao custo humano de chamar alguém de mentiroso.

#### P33 — O Avesso
**Nó:** `P33_avesso_posture`
**Momento:** Etapa 6, depois de compreender Avesso como estado.
**Pergunta dramática:** O que significa saber que o Avesso existe?

1. **Uma nova coisa para estudar.** → memória: `Eris:_curiosidade_controlada;_memória:_avesso_como_estado.`
2. **Um limite que exige cautela, não explicação total.** → memória: `Sera:_prudência;_memória:_avesso_como_risco.`
3. **Uma prova de que nossas categorias são incompletas.** → memória: `Roven:_humildade;_memória:_limites_das_categorias.`
**Retorno futuro:** P34: leitura da Âncora Central pode refletir isso.
**Identidade contextual:** Oráculo/Tecelão podem ter formulação temática, sem criar poder novo.

#### S33 — Nomes em Ordem Errada
**Nó:** `S33_correction_policy`
**Momento:** Etapa 4, separando erro de discrepância real.
**Pergunta dramática:** Quando um registro está errado, o que você faz?

1. **Corrigir a cópia.** → memória: `Roven:_precisão;_memória:_corrige_copia.`
2. **Preservar o original e anexar correção.** → memória: `Roven:_cadeia_de_procedencia;_memória:_anexa_correcao.`
3. **Não decidir até achar mais evidência.** → memória: `Roven:_ceticismo;_memória:_adia_conclusao.`
**Retorno futuro:** S35: método de preservação dos dois lados é reconhecido.
**Identidade contextual:** Classe: Vigia pode observar materialidade das inscrições.

#### P34 — A Âncora Central
**Nó:** `P34_anchor_model`
**Momento:** Etapa 5, diante do registro técnico sobre coordenação.
**Pergunta dramática:** Como interpretar a Âncora Central?

1. **Como nó de coordenação.** → memória: `Eris:_concordância_tecnica;_memória:_ancora_como_no.`
2. **Como solução provável, mas não definitiva.** → memória: `Eris:_prudência;_memória:_ancora_sem_totalidade.`
3. **Procurar evidência do que ela não fazia.** → memória: `Roven/Eris:_investigação;_memória:_limites_da_ancora.`
**Retorno futuro:** P35: reconstrução da Convergência reconhece o seu modelo.
**Identidade contextual:** Alvorano Eris pode ter fala de identidade; Velado recebe linha de percepção técnica apenas se justificada.

#### S34 — A Testemunha de Ontem
**Nó:** `S34_temporal_discrepancy`
**Momento:** Etapa 5, registrando a discrepância temporal local.
**Pergunta dramática:** Como registrar um depoimento que parece anteceder seu próprio registro?

1. **Fato observável, sem teoria.** → memória: `Talen:_rigor;_memória:_tempo_sem_teoria.`
2. **Hipótese explicitamente marcada como impossível de provar ainda.** → memória: `Talen:_curiosidade;_memória:_hipotese_temporal.`
3. **Guardar o depoimento e buscar cadeia de custódia adicional.** → memória: `Talen:_prudência;_memória:_testemunho_em_revisao.`
**Retorno futuro:** P35/P36: personagem não recebe “verdade secreta” só porque investigou cedo.
**Identidade contextual:** Oráculo pode receber reação de intuição sem transformar em profecia.

#### P35 — A Noite da Convergência
**Nó:** `P35_responsibility_model`
**Momento:** Etapa 8, reconstruindo Regência, Custódia e Desvelados.
**Pergunta dramática:** Como distribuir responsabilidade?

1. **Separar decisões individuais de contexto institucional.** → memória: `Eris:_responsabilidade_especifica.`
2. **Registrar a cadeia de fatores como sistema.** → memória: `Roven:_causalidade_sistemica.`
3. **Preservar a incerteza onde a evidência não fecha.** → memória: `Sera:_rigor_epistemico.`
**Retorno futuro:** P36: o fechamento do protocolo ecoa a postura adotada na reconstrução.
**Identidade contextual:** Alvorano/Hemário/Velado podem receber linhas de identidade apenas quando testemunho/arquivo o justificar.

#### S35 — O Registro que Discorda
**Nó:** `S35_orders_policy`
**Momento:** Etapa 4, diante de duas ordens oficiais incompatíveis.
**Pergunta dramática:** Você apaga uma, escolhe uma ou preserva ambas?

1. **Preservar ambas.** → memória: `Roven:_memoria_documental.`
2. **Escolher a mais bem sustentada e registrar a outra.** → memória: `Eris:_hierarquia_critica.`
3. **Não escolher enquanto não houver prova adicional.** → memória: `Sera:_cautela.`
**Retorno futuro:** P36: registro final pode refletir sua preferência por preservação, hierarquia ou suspensão.
**Identidade contextual:** Classe: Vigia/Tecelão recebe leitura de procedência.

#### P36 — O Regente Fraturado
**Nó:** `P36_final_record`
**Momento:** Etapa 7, após o registro sobre o Regente.
**Pergunta dramática:** O que merece entrar no registro final da Campanha?

1. **Os fatos confirmados.** → memória: `Roven/Sera:_rigor;_memória:_final_factual.`
2. **Os fatos e as interpretações claramente marcadas.** → memória: `Eris:_contexto;_memória:_interpretação_marcada.`
3. **Os fatos, as lacunas e quem testemunhou o quê.** → memória: `Haro/Sera:_responsabilidade_testemunhal;_memória:_testemunho_preservado.`
**Retorno futuro:** Legado/Crônica: o personagem leva um perfil de como trata evidência e memória.
**Identidade contextual:** Alvorano/Hemário/Velado têm linhas finais possíveis sem tornar raça determinante.

#### S36 — Depois da Última Ordem
**Nó:** `S36_civil_continuity`
**Momento:** Etapa 6, decidindo como narrar continuidade civil.
**Pergunta dramática:** Que tipo de continuidade deve sobreviver?

1. **A rotina comprovadamente útil.** → memória: `Sera:_pragmatismo;_memória:_rotina_util.`
2. **A rotina que os moradores reconhecem como confiável.** → memória: `Haro:_comunidade;_memória:_rotina_comunitaria.`
3. **Uma combinação nova, registrada como decisão presente.** → memória: `Sera/Haro:_adaptação;_memória:_reforma_local.`
**Retorno futuro:** Pós-P36: não muda o mundo global; muda a memória pessoal sobre continuidade.
**Identidade contextual:** Classe: Sentinela/Tecelão pode ter reação sobre protocolo.

## 8. Fechamento de Design

### 8.1 O que este documento fecha

- Todas as 36 Principais possuem decisão narrativa.
- Todas as 36 Secundárias possuem decisão narrativa.
- Contratos ficam fora da exigência de ramificação.
- Relação com NPC é qualitativa e baseada em memória.
- Consequências são persistentes, locais e verificáveis.
- Não existe onisciência de NPC.
- Raça/Classe podem abrir identidade quando houver motivo real.
- Coop de história é exclusivamente por Chefes.
- Nenhuma decisão altera automaticamente economia, stats ou rewards.
- As escolhas convergem para preservar viabilidade de produção.

### 8.2 O que ainda é conteúdo editorial, não bloqueio técnico

- copy final de fala de cada opção;
- locuções/flavor adicionais;
- tradução;
- QA de tom;
- revisão de nomes de tags se o backend já possuir convenção equivalente.

### 8.3 Critérios de aceite para Claude Code

1. Não existe Principal/Secundária sem `choice_id` válido.
2. Nenhuma escolha pode ser repetida por reconnect/retry.
3. Toda escolha grava pelo menos uma memória persistente.
4. Reações futuras consultam somente memórias legitimamente disponíveis.
5. Nenhum NPC recebe memória de evento que não poderia conhecer.
6. Coop de missão comum não cria progresso narrativo compartilhado.
7. Coop de Chefe funciona conforme as regras globais de Chefe e mantém escolha/narrativa individual.
8. Abandono/reaceite não duplica memória ou recompensa.
9. Flags narrativas não mutam `world_state` global sem fonte explícita.
10. Debug permite auditar a cadeia completa da escolha.
11. Códice continua pessoal e nunca recebe spoiler por consequência de diálogo futuro.
12. Nenhum texto de UI revela tags internas ou valores numéricos de relacionamento.

## 9. Migração

Para personagens que já ultrapassaram um nó de decisão antes desta implementação, a migração usa `neutral_backfill` apenas quando não for possível reconstruir a escolha historicamente. Nenhuma consequência retroativa é inventada. Em Beta com wipe, todos os nós entram pelo fluxo completo desde P1.

## 10. Próxima camada de produção

Este arquivo é o contrato de **lógica narrativa**. A camada seguinte é o roteiro player-facing: falas, botões, variantes de resposta, reação de NPC, fallback comum e copy específica de Raça/Classe. Essa camada não pode criar nova regra de memória sem registrar o novo `choice_id` ou `future_hook` neste contrato.

**STATUS FINAL DESTE DOCUMENTO: pronto para handoff à implementação narrativa, após atualização do GDD com o override de Coop.**
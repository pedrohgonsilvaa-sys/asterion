# ASTERION — DOCUMENTO A
# Escolhas Narrativas do Prólogo

**Status:** PROPOSTA (aprovar)  
**Escopo:** Prólogo  
**Missão:** `PRO`  
**Tipo:** `prologo`  
**Região:** Terras do Ocaso  
**Objetivo:** adicionar escolhas narrativas ao Prólogo sem alterar progressão, economia, combate ou WorldState.

---

## 1. Regras gerais

As escolhas do Prólogo são exclusivamente narrativas.

Uma escolha:

- não altera XP;
- não altera Coroas;
- não altera Materiais;
- não altera Equipamento;
- não altera combate;
- não altera dificuldade;
- não altera raça;
- não altera Classe;
- não altera acesso a conteúdo;
- não altera gates;
- não altera WorldState;
- não cria rota narrativa alternativa;
- não muda a sequência do Prólogo;
- não altera a conclusão do Prólogo;
- não altera o resultado econômico de vitória ou derrota.

A escolha apenas registra uma memória interpretativa do personagem.

A memória poderá ser consultada posteriormente por sistemas narrativos que explicitamente decidam reagir a ela.

A escolha nunca deve ser tratada como uma variável de poder.

---

## 2. Fluxo oficial

O Prólogo permanece linear:

1. Abertura.
2. Primeiro combate.
3. Ensino de Ataque e Defesa.
4. Primeiro uso de Arte.
5. Primeiro Braseiro.
6. Encerramento do Prólogo.
7. Entrada em P1 — Vozes na Estrada.

As escolhas abaixo são inseridas dentro desse fluxo sem adicionar etapas de missão.

---

## 3. Catálogo de escolhas

### 3.1 `PRO_choice_aftermath`

| Campo | Valor |
|---|---|
| `choice_id` | `PRO_choice_aftermath` |
| `mission_id` | `PRO` |
| `mission_kind` | `prologo` |
| `title` | Depois da Cinza |
| `region` | `terras_do_ocaso` |
| `step` | após o primeiro combate |
| `rapport` | `neutral` |

**Contexto:** O primeiro confronto terminou. O personagem tem pouco tempo para interpretar o que acabou de acontecer antes de seguir pela estrada.

**Pergunta:** **O que você faz com o que acabou de aprender?**

#### Opção `o1`

**Label:** Examinar primeiro

**Memória**

- `memory_type`: `EVIDENCE`
- `character_memory_tags`:
  - `evidence_first`
  - `preserves_records`

**Interpretação:** o personagem tende a observar os sinais disponíveis antes de formar uma conclusão.

#### Opção `o2`

**Label:** Aceitar que ainda não sabe

**Memória**

- `memory_type`: `METHOD`
- `character_memory_tags`:
  - `hypothesis_marked`
  - `preserves_contradiction`

**Interpretação:** o personagem reconhece explicitamente a diferença entre aquilo que observou e aquilo que ainda não consegue explicar.

#### Opção `o3`

**Label:** Seguir enquanto é possível

**Memória**

- `memory_type`: `ETHICAL`
- `character_memory_tags`:
  - `pragmatic`
  - `risk_accepting`

**Interpretação:** o personagem prioriza continuidade e ação diante de informação incompleta.

---

### 3.2 `PRO_choice_first_fire`

| Campo | Valor |
|---|---|
| `choice_id` | `PRO_choice_first_fire` |
| `mission_id` | `PRO` |
| `mission_kind` | `prologo` |
| `title` | Diante do Braseiro |
| `region` | `terras_do_ocaso` |
| `step` | primeiro Braseiro |
| `rapport` | `neutral` |

**Contexto:** O personagem alcança o primeiro ponto seguro e tem um breve momento para decidir qual princípio pretende carregar consigo pela estrada.

**Pergunta:** **O que merece ser preservado antes de seguir?**

#### Opção `o1`

**Label:** Guardar o que foi visto

**Memória**

- `memory_type`: `EVIDENCE`
- `character_memory_tags`:
  - `preserves_records`
  - `evidence_first`

**Interpretação:** registrar o que aconteceu é tratado como forma de preservar conhecimento contra esquecimento ou distorção.

#### Opção `o2`

**Label:** Pensar em quem depende da estrada

**Memória**

- `memory_type`: `ETHICAL`
- `character_memory_tags`:
  - `community_first`
  - `protective`

**Interpretação:** o personagem prioriza as consequências das decisões para outras pessoas.

#### Opção `o3`

**Label:** Não deixar o medo decidir

**Memória**

- `memory_type`: `IDENTITY`
- `character_memory_tags`:
  - `risk_accepting`
  - `questions_authority`

**Interpretação:** o personagem demonstra disposição para agir mesmo diante de incerteza ou pressão.

---

## 4. Regra de raça e Classe

Raça e Classe podem fornecer contexto textual para a apresentação da escolha.

Isso é apenas contextualização.

Raça ou Classe:

- não remove opção;
- não cria opção adicional;
- não altera memória;
- não altera recompensa;
- não altera combate;
- não altera dificuldade;
- não altera gate;
- não altera WorldState.

Não existe requisito de Classe ou Raça para escolher qualquer uma das opções.

---

## 5. Memória de NPC

Nenhuma das escolhas do Prólogo deve registrar memória de NPC se o NPC não estiver efetivamente presente e capaz de testemunhar a decisão.

Isso preserva a regra de conhecimento local do mundo.

O catálogo inicial utiliza apenas memória de personagem e não cria artificialmente memória de NPC para personagens que ainda não presenciaram a escolha.

---

## 6. Ganchos futuros

Os ganchos abaixo são reações narrativas condicionais, não consequências mecânicas.

Eles não transformam as escolhas em caminhos diferentes.

### `PRO_choice_aftermath` → P1

**NPC:** Alda

**Condição narrativa:** personagem possui `evidence_first` ou `preserves_records`.

**Reação proposta:**

> Alda percebe que o viajante presta atenção aos sinais antes de seguir. Ela trata isso como uma qualidade útil para alguém que pretende atravessar uma estrada onde informações incompletas podem custar caro.

### `PRO_choice_aftermath` → S1

**NPC:** Oren

**Condição narrativa:** personagem possui `hypothesis_marked` ou `preserves_contradiction`.

**Reação proposta:**

> Oren percebe que o personagem não transforma imediatamente uma observação em certeza. Para ele, essa cautela torna o relato mais útil, porque uma pergunta preservada pode valer mais do que uma resposta inventada.

### `PRO_choice_aftermath` → S5

**NPC:** Oren

**Condição narrativa:** personagem possui `pragmatic` ou `risk_accepting`.

**Reação proposta:**

> Oren percebe que o personagem prefere continuar avançando mesmo quando ainda não existe explicação suficiente. Ele não trata isso como prova de que a interpretação está correta; apenas reconhece que aquela pessoa não costuma esperar certeza absoluta para agir.

### `PRO_choice_first_fire` → P1

**NPC:** Alda

**Condição narrativa:** personagem possui `preserves_records`.

**Reação proposta:**

> Alda nota que o personagem dá importância ao que pode ser registrado e lembrado. Para quem vive de manter uma comunidade funcionando, isso parece uma atitude prática, não uma teoria.

### `PRO_choice_first_fire` → S1

**NPC:** Oren

**Condição narrativa:** personagem possui `community_first` ou `protective`.

**Reação proposta:**

> Oren percebe que o personagem tende a pensar primeiro nas pessoas afetadas pelo que acontece na estrada. Isso muda a forma como ele apresenta um relato: não apenas como uma curiosidade, mas como algo que pode importar para quem precisa continuar viajando.

### `PRO_choice_first_fire` → S5

**NPC:** Oren

**Condição narrativa:** personagem possui `risk_accepting` ou `questions_authority`.

**Reação proposta:**

> Oren entende que o personagem não gosta de aceitar uma explicação simplesmente porque alguém a apresentou como certa. Ele pode discordar da conclusão, mas reconhece que a disposição de questionar precisa ser distinguida de uma prova.

---

## 7. Regra de coerência dos ganchos

Os ganchos não podem:

- revelar a origem de fenômenos;
- revelar Âncoras;
- revelar o Primeiro Selo;
- revelar a Convergência;
- revelar o Avesso;
- revelar os Desvelados;
- antecipar Projeto Hemaris;
- antecipar revelações posteriores da campanha;
- conceder conhecimento cosmológico;
- mudar a ordem das missões;
- alterar recompensa.

P1 continua sendo a chegada ao Refúgio, apresentação de Alda e Oren e ativação do Braseiro do Refúgio.

---

## 8. Jogadores antigos

Personagens criados antes da implantação das escolhas do Prólogo recebem:

```text
neutral_backfill
```

O backfill:

- não escolhe uma opção retrospectivamente;
- não cria tendência;
- não cria memória de personagem;
- não cria memória de NPC;
- não altera diálogo já concluído;
- não altera P1;
- não altera recompensas.

O personagem simplesmente permanece sem preferência registrada.

---

## 9. Idempotência

A escolha deve ser registrada de forma idempotente.

Uma repetição causada por reconnect, callback duplicado, reabertura da mensagem, `/start`, `/menu`, reconstrução da UI ou troca de dispositivo não pode:

- duplicar memória;
- gerar nova consequência;
- mudar a opção escolhida;
- gerar recompensa;
- criar nova entrada narrativa.

A escolha pertence ao personagem, não à mensagem do Telegram.

---

## 10. Compatibilidade com as 72 escolhas

O Prólogo utiliza a mesma estrutura conceitual das escolhas narrativas existentes:

```text
choice
├── choice_id
├── mission_id
├── mission_kind
├── title
├── region
├── step
├── context
├── question
└── options
    ├── option_id
    ├── label
    ├── memory
    └── identity_note opcional
```

Cada escolha possui exatamente três opções.

Nenhuma opção é apresentada como correta, incorreta, moralmente superior ou mecanicamente superior.

---

## 11. Tags de memória utilizadas

| Tag | Uso |
|---|---|
| `evidence_first` | priorizar observação e evidência |
| `preserves_records` | preservar registros |
| `hypothesis_marked` | distinguir hipótese de fato |
| `preserves_contradiction` | manter contradições abertas |
| `pragmatic` | priorizar solução prática |
| `risk_accepting` | aceitar risco |
| `community_first` | priorizar comunidade |
| `protective` | priorizar proteção |
| `questions_authority` | questionar autoridade |

Nenhuma tag cria bônus sistêmico.

---

## 12. Resumo executivo

| Choice ID | Momento | Opção 1 | Opção 2 | Opção 3 |
|---|---|---|---|---|
| `PRO_choice_aftermath` | Após primeiro combate | Examinar primeiro | Aceitar que ainda não sabe | Seguir enquanto é possível |
| `PRO_choice_first_fire` | Primeiro Braseiro | Guardar o que foi visto | Pensar em quem depende da estrada | Não deixar o medo decidir |

---

## 13. Valores a aprovar pelo autor

| Parâmetro | Proposta |
|---|---:|
| Quantidade de escolhas no Prólogo | 2 |
| Opções por escolha | 3 |
| Alteração de XP | 0 |
| Alteração de Coroas | 0 |
| Alteração de Materiais | 0 |
| Alteração de Equipamento | 0 |
| Alteração de combate | 0 |
| Alteração de dificuldade | 0 |
| Alteração de rapport | 0 |
| Memórias de NPC no Prólogo | 0 |
| Memórias de personagem por opção | 2 |
| `neutral_backfill` | 1 estado neutro |

---

## 14. Riscos de coerência com P1

| Risco | Tratamento |
|---|---|
| O Prólogo parecer criar uma rota alternativa | As escolhas convergem para o mesmo final |
| Alda ou Oren saberem algo que não testemunharam | Não registrar memória de NPC no Prólogo |
| P1 começar com conhecimento antecipado | Memórias são comportamentais, não lore |
| Escolha alterar recompensa | Proibido |
| Escolha alterar combate | Proibido |
| Escolha antecipar mistérios | Proibido |
| P1 ganhar etapas novas | Proibido |
| P1 mudar de ordem | Proibido |
| Jogador antigo receber preferência inventada | `neutral_backfill` |
| Callback duplicado duplicar memória | Persistência idempotente |

---

# FIM DO DOCUMENTO A

=== DOCUMENTO B ===

# ASTERION — DOCUMENTO B
# Contratos Regionais

**Status:** PROPOSTA (aprovar)  
**Natureza:** sistema complementar à Campanha  
**Canal:** Telegram Bot  
**Mini App:** não utilizado

---

## 1. O que é um Contrato

Contrato é uma atividade regional curta, repetível e objetiva, oferecida por um quadro local de oportunidades.

Contrato não é:

- Missão Principal;
- Missão Secundária;
- escolha narrativa;
- capítulo da Campanha;
- substituto de missão;
- rota narrativa;
- conteúdo com ramificação.

Contrato existe para criar atividade recorrente entre momentos da Campanha sem criar novas linhas narrativas.

---

## 2. Quem oferece

O Contrato é oferecido pelo quadro local de contratos da região.

Não é necessário criar um NPC novo para administrar o sistema.

O texto pode apresentar o quadro como uma lista de necessidades práticas:

- eliminar ameaça;
- obter material;
- levar algo;
- verificar ocorrência;
- cumprir uma tarefa objetiva.

---

## 3. Diferença entre Contrato e Missão

| Missão | Contrato |
|---|---|
| pertence à Campanha | atividade paralela |
| pode possuir narrativa | não possui narrativa ramificada |
| pode possuir escolhas | não possui Choice Node |
| pode alterar conhecimento narrativo | não altera lore principal |
| pode possuir NPC específico | utiliza quadro regional |
| possui estrutura própria | possui objetivo curto |
| pode ter recompensa única | recompensa de Contrato é repetível dentro das regras |
| participa da progressão da Campanha | não libera a Campanha |

---

## 4. Fonte dos Contratos

Cada região possui um quadro próprio.

O jogador acessa o quadro quando estiver elegível para a região.

A interface apresenta:

- Contratos disponíveis;
- Contratos aceitos pelo personagem;
- Contratos concluídos aguardando resgate.

O quadro não precisa existir fisicamente como objeto de mapa separado.

Ele é uma representação de UI de uma função regional.

---

## 5. Renovação do quadro

A renovação substitui oportunidades que chegaram ao fim de sua validade.

Um Contrato que expira sem ser aceito simplesmente deixa de estar disponível.

Um Contrato já aceito não vira uma nova instância quando o quadro é renovado.

Cada instância de Contrato possui identidade própria.

Isso impede:

- aceitar duas vezes o mesmo Contrato;
- concluir uma instância antiga usando a instância nova;
- receber duas recompensas pela mesma oferta.

---

## 6. Tipos de Contrato

O sistema inicial possui cinco tipos.

### 6.1 Caça

Objetivo: derrotar uma criatura elegível dentro do escopo regional.

**Exemplos:**

- eliminar uma ameaça próxima;
- abater uma criatura específica;
- concluir uma ocorrência de combate regional.

**Conclusão:** ocorre quando o objetivo de Caça definido pelo Contrato for validamente registrado para o personagem.

Não basta entrar no combate.

### 6.2 Coleta

Objetivo: obter Materiais através das ações de coleta suportadas pelo jogo.

**Exemplos:**

- reunir material regional;
- obter material associado a uma atividade;
- alcançar a quantidade exigida pelo Contrato.

**Conclusão:** ocorre quando a quantidade exigida de Material elegível estiver registrada no progresso.

### 6.3 Entrega

Objetivo: transportar ou entregar um recurso ou objetivo definido pelo Contrato.

**Exemplos:**

- levar um Material a um destino;
- entregar um pacote de suprimentos;
- concluir uma entrega regional.

**Conclusão:** ocorre no destino válido quando a entrega for confirmada pelo sistema.

Não existe comércio entre jogadores envolvido.

### 6.4 Investigação

Objetivo: examinar uma ocorrência, pista ou Local já suportado pelas mecânicas existentes.

**Exemplos:**

- examinar uma pista;
- registrar uma ocorrência;
- verificar uma estrutura;
- confirmar um ponto de interesse.

**Conclusão:** ocorre quando a ação de investigação definida pelo Contrato for registrada.

O Contrato não cria automaticamente uma nova descoberta de lore.

### 6.5 Escolta

**PROPOSTA (aprovar)**

Este tipo exige uma nova mecânica de deslocamento de um objetivo acompanhado.

**Classificação:** `MECÂNICA NOVA`

**Exemplos:**

- acompanhar um viajante;
- proteger uma carga;
- conduzir um objetivo até um destino.

**Conclusão:** o objetivo deve alcançar o destino definido sem que a condição de falha do Contrato seja acionada.

**Regra conservadora:** a Escolta permanece desativada na primeira implementação até que a mecânica seja especificada e aprovada.

Nenhum Contrato inicial depende dela.

---

## 7. Estados

Os estados autoritativos são:

```text
DISPONÍVEL
ACEITO
EM_ANDAMENTO
CONCLUÍDO
RESGATADO
EXPIRADO
ABANDONADO
```

### Disponível

Instância oferecida pelo quadro e ainda elegível.

### Aceito

O jogador aceitou o Contrato.

### Em andamento

O personagem executou alguma parte válida do objetivo.

### Concluído

Todos os requisitos do objetivo foram cumpridos.

A recompensa ainda não foi necessariamente entregue.

### Resgatado

A recompensa foi liquidada de maneira idempotente.

### Expirado

A instância perdeu validade antes de ser concluída.

Não gera recompensa.

### Abandonado

O jogador cancelou voluntariamente o Contrato.

Não gera recompensa.

---

## 8. Transições

Fluxo principal:

```text
DISPONÍVEL
    ↓
ACEITO
    ↓
EM_ANDAMENTO
    ↓
CONCLUÍDO
    ↓
RESGATADO
```

Também são permitidas:

```text
DISPONÍVEL → EXPIRADO
ACEITO → EXPIRADO
EM_ANDAMENTO → EXPIRADO

ACEITO → ABANDONADO
EM_ANDAMENTO → ABANDONADO
```

Não são permitidas:

```text
RESGATADO → qualquer estado
EXPIRADO → qualquer estado
ABANDONADO → qualquer estado
```

Um novo Contrato pode ser aceito posteriormente como uma nova instância.

---

## 9. Limite simultâneo

O personagem possui um limite de Contratos aceitos simultaneamente.

Contratos concluídos aguardando resgate continuam ocupando uma vaga até o resgate.

Contratos expirados e abandonados deixam de ocupar vaga.

---

## 10. Abandono

Abandonar um Contrato:

- encerra o progresso daquela instância;
- não entrega recompensa;
- não devolve a instância ao quadro;
- não cria outra instância automaticamente;
- não altera a Campanha.

**PROPOSTA (aprovar):** não existe multa econômica direta por abandono.

A consequência é a perda da oportunidade e do progresso daquela instância.

---

## 11. Recompensas

Contratos só podem conceder:

- XP;
- Coroas;
- Materiais.

Não podem conceder diretamente:

- Equipamento;
- Runa;
- Encantamento;
- Consumível;
- Receita;
- Núcleo;
- recompensa narrativa única;
- escolha de equipamento;
- item exclusivo de lore.

Materiais concedidos devem pertencer ao conjunto regional válido para o Contrato.

---

## 12. Fórmula de recompensa

A recompensa deve ser determinada pela combinação de:

```text
faixa regional
×
tipo de Contrato
×
perfil de dificuldade
```

O Contrato não deve gerar recompensa por quantidade indefinida de inimigos.

Um Contrato é uma unidade econômica.

---

## 13. Perfil de recompensa

Cada definição de Contrato recebe uma chave:

```text
REWARD_R1_CACA
REWARD_R1_COLETA
REWARD_R1_ENTREGA
REWARD_R1_INVESTIGACAO
```

e equivalentes para as demais faixas regionais.

O valor real dessas chaves fica centralizado na tabela **Valores a aprovar pelo autor**.

---

## 14. Requisitos

Um Contrato possui três dimensões de elegibilidade:

```text
nível mínimo
região
progressão Principal
```

O personagem deve satisfazer todas.

A progressão da Campanha é o gate principal.

O Contrato nunca serve para contornar um gate de região.

---

## 15. Faixas regionais

| Faixa | Região |
|---|---|
| `R1` | Terras do Ocaso |
| `R2` | Vales dos Enforcados |
| `R3` | Planícies de Nareth |
| `R4` | Várzeas Carmesins |
| `R5` | Altos Cinéreos |
| `R6` | Confins do Véu |

---

## 16. Gate de Campanha

A proposta utiliza a progressão das Principais como gate regional.

| Faixa | Gate |
|---|---|
| `R1` | pós-P1 |
| `R2` | pós-P6 |
| `R3` | pós-P12 |
| `R4` | pós-P18 |
| `R5` | pós-P24 |
| `R6` | pós-P30 |

**PROPOSTA (aprovar):** o Contrato não abre uma região antes da Campanha.

---

## 17. Solo e Cooperação

Contratos são **Solo por padrão**.

Não existe cooperação para Contratos normais na primeira implementação.

Conteúdo cooperativo permanece concentrado nas regras já existentes da Campanha e nos conteúdos que explicitamente suportam Grupo.

---

## 18. Anti-exploit

### Farm infinito

O Contrato possui instância e identidade próprias.

O settlement é realizado uma única vez.

Reexecutar a mesma ação não cria nova recompensa.

### Reaceitar a mesma instância

Uma instância que já estiver:

- aceita;
- em andamento;
- concluída;
- resgatada;
- expirada;
- abandonada;

não pode voltar para `DISPONÍVEL`.

### Callback duplicado

Toda conclusão e todo resgate devem ser idempotentes.

Dois callbacks iguais produzem um único resultado econômico.

### Troca de recompensa entre contas

Não existe transferência de recompensa de Contrato.

A recompensa pertence ao personagem elegível que concluiu a atividade.

### Multiaccount

Como Contratos são Solo:

- não existe compartilhamento de progresso;
- não existe transferência de progresso;
- não existe assistência econômica;
- não existe divisão de recompensa.

---

## 19. Relação com outros sistemas

### Guilda

**Nenhuma integração inicial.**

### Mercado

**Nenhuma integração inicial.**

### Crônica

**Nenhuma integração inicial.**

### Arena

**Nenhuma integração inicial.**

---

## 20. Bestiário

O tipo Caça pode interagir com o Bestiário somente através dos registros normais que já seriam produzidos por um encontro válido.

O Contrato não cria conhecimento automático.

---

## 21. Combate

Um Contrato de Caça utiliza o sistema de combate existente.

Não cria:

- novo sistema de turno;
- novo cálculo de dano;
- nova economia de Vigor;
- nova regra de scaling;
- nova categoria de criatura.

---

## 22. Telegram — Quadro

Mensagem:

```text
📜 QUADRO DE CONTRATOS

Escolha um contrato disponível para ver seus detalhes.

[Contrato 1]
[Contrato 2]
[Contrato 3]
[Contrato 4]
[Contrato 5]
[Contrato 6]
[Meus Contratos]
[Voltar]
```

A quantidade efetiva de botões disponíveis permanece limitada pelo valor aprovado.

---

## 23. Telegram — Detalhe

Mensagem:

```text
📜 CONTRATO

[Nome do Contrato]

Tipo: [tipo]
Região: [região]

[Descrição curta]

Requisitos:
[requisitos]

Recompensa:
[perfil de recompensa]

[ACEITAR]
[VOLTAR]
```

---

## 24. Telegram — Contrato aceito

Mensagem:

```text
📜 MEU CONTRATO

[Nome]

Estado: Em andamento

Progresso:
[progresso atual]

[CONTINUAR]
[ABANDONAR]
[QUADRO]
```

---

## 25. Telegram — Contrato concluído

Mensagem:

```text
✅ CONTRATO CONCLUÍDO

[Nome]

O objetivo foi concluído.

Recompensa disponível:
[XP]
[Coroas]
[Materiais]

[RESGATAR]
[QUADRO]
```

---

## 26. Telegram — Confirmação de abandono

Mensagem:

```text
⚠️ ABANDONAR CONTRATO?

O progresso deste Contrato será encerrado.
A recompensa não será recebida.

[CONFIRMAR ABANDONO]
[MANTER CONTRATO]
```

---

## 27. Regra de botões

Nenhuma tela de Contrato deve ultrapassar o limite global de botões aprovado.

Botões que não sejam aplicáveis ao estado atual não devem aparecer.

Callbacks devem revalidar:

- personagem;
- contrato;
- estado;
- elegibilidade;
- validade;
- versão da instância.

A UI nunca é a autoridade final.

---

## 28. Persistência

A persistência deve ser por personagem.

Campos mínimos:

```text
contract_instance_id
contract_definition_id
region_id
contract_type
state
accepted_at
started_at
completed_at
expires_at
abandoned_at
claimed_at
progress
target
version
claimed
reward_profile
source_refresh_id
eligibility_snapshot
last_validated_at
```

Não é necessário definir SQL neste documento.

O requisito é comportamental.

---

## 29. Integridade da instância

Cada instância deve possuir identidade própria.

```text
contract_definition_id
=
definição do contrato

contract_instance_id
=
oferta concreta daquela definição
```

Isso permite que o quadro seja renovado sem transformar uma oferta antiga em uma oferta nova com a mesma identidade.

---

## 30. Expiração durante combate

**PROPOSTA (aprovar):** se uma ação válida que iniciou antes do vencimento do Contrato produzir a conclusão do objetivo após o vencimento, a conclusão é aceita.

O motivo é evitar que uma atividade legítima seja invalidada apenas porque a resolução do combate ocorreu depois do timestamp de expiração.

A autoridade deve ser o momento de início da ação relevante, não a mensagem visual do Telegram.

---

## 31. Expiração fora de combate

Se o Contrato estiver expirado antes de uma ação válida ser iniciada:

- a ação não conclui o Contrato;
- o Contrato passa para `EXPIRADO`;
- não existe recompensa;
- o progresso é encerrado.

---

## 32. Servidor reiniciado

Após reinício:

- o estado persistido permanece autoritativo;
- o Contrato não é recriado;
- recompensa não é duplicada;
- progresso não é perdido;
- callback antigo deve revalidar o estado atual.

Se o Contrato tiver expirado durante indisponibilidade, a primeira operação posterior deve normalizar o estado para `EXPIRADO`.

---

## 33. Região bloqueada

Se o personagem perder temporariamente acesso a uma região:

- o Contrato não é convertido em missão;
- o progresso não é automaticamente concluído;
- o Contrato não ignora o gate;
- o estado persistido permanece válido até expirar, ser concluído ou abandonado.

Se a definição exigir uma região permanentemente incompatível, a instância deve ser invalidada pelo sistema de elegibilidade antes de permitir novas ações.

---

## 34. Personagem deletado

Se o personagem for excluído:

- os Contratos associados deixam de ser jogáveis;
- nenhuma recompensa é migrada;
- nenhuma instância é transferida;
- nenhuma conta recebe o settlement.

---

## 35. Recompensa pendente

Se um Contrato estiver `CONCLUÍDO`, a recompensa ainda não deve ser considerada paga.

O pagamento acontece somente na transição:

```text
CONCLUÍDO → RESGATADO
```

Essa transição deve ser transacional e idempotente.

---

# 36. Catálogo inicial

## Terras do Ocaso

| ID | Nome | Tipo | Região | Nível mínimo | Condição | Recompensa | Descrição |
|---|---|---|---|---|---|---|---|
| `CON_TDO_01` | Cinza na Estrada | Caça | Terras do Ocaso | `FAIXA_R1` | Concluir o objetivo de Caça definido | `REWARD_R1_CACA` | Uma ameaça voltou a aparecer nas rotas próximas. Elimine o alvo registrado no contrato e confirme a conclusão. |
| `CON_TDO_02` | Ferro da Estrada | Coleta | Terras do Ocaso | `FAIXA_R1` | Obter o Material exigido | `REWARD_R1_COLETA` | Restos metálicos ainda podem ser recuperados nas áreas de passagem. Reúna o Material solicitado. |
| `CON_TDO_03` | Couro Escoriado | Coleta | Terras do Ocaso | `FAIXA_R1` | Obter o Material exigido | `REWARD_R1_COLETA` | Couro aproveitável ainda aparece entre os restos deixados pelas ameaças da estrada. Reúna o material solicitado. |
| `CON_TDO_04` | Entrega do Refúgio | Entrega | Terras do Ocaso | `FAIXA_R1` | Realizar a entrega no destino definido | `REWARD_R1_ENTREGA` | Um carregamento precisa chegar ao destino sem ser perdido pelo caminho. Leve a entrega até o ponto indicado. |
| `CON_TDO_05` | Sinais Recentes | Investigação | Terras do Ocaso | `FAIXA_R1` | Examinar o ponto de investigação definido | `REWARD_R1_INVESTIGACAO` | Há sinais recentes na estrada. Examine o ponto indicado e registre a ocorrência. |
| `CON_TDO_06` | Cinzas sem Resposta | Investigação | Terras do Ocaso | `FAIXA_R1` | Confirmar a ocorrência definida | `REWARD_R1_INVESTIGACAO` | Uma ocorrência estranha foi observada na região. Verifique o local e confirme o que pode ser registrado. |

## Vales dos Enforcados

| ID | Nome | Tipo | Região | Nível mínimo | Condição | Recompensa | Descrição |
|---|---|---|---|---|---|---|---|
| `CON_VEN_01` | Ameaça nos Vales | Caça | Vales dos Enforcados | `FAIXA_R2` | Concluir o objetivo de Caça definido | `REWARD_R2_CACA` | Uma ameaça está interferindo nas rotas dos Vales. Elimine o alvo registrado no contrato. |
| `CON_VEN_02` | Ferro Enredado | Coleta | Vales dos Enforcados | `FAIXA_R2` | Obter o Material exigido | `REWARD_R2_COLETA` | Fragmentos de metal podem ser recuperados entre raízes e estruturas antigas. Reúna o material solicitado. |
| `CON_VEN_03` | Couro Musgoso | Coleta | Vales dos Enforcados | `FAIXA_R2` | Obter o Material exigido | `REWARD_R2_COLETA` | Materiais aproveitáveis aparecem em áreas úmidas dos Vales. Reúna o recurso indicado no contrato. |
| `CON_VEN_04` | Entrega do Vale | Entrega | Vales dos Enforcados | `FAIXA_R2` | Realizar a entrega no destino | `REWARD_R2_ENTREGA` | Um carregamento precisa atravessar uma rota dos Vales. Leve a entrega até o destino indicado. |
| `CON_VEN_05` | Erva de Turfa | Coleta | Vales dos Enforcados | `FAIXA_R2` | Obter o Material exigido | `REWARD_R2_COLETA` | Uma erva específica pode ser encontrada em áreas de turfa. Reúna o recurso solicitado. |
| `CON_VEN_06` | Resina Enredada | Coleta | Vales dos Enforcados | `FAIXA_R2` | Obter o Material exigido | `REWARD_R2_COLETA` | Resina pode ser extraída de pontos adequados da região. Reúna o Material solicitado antes de concluir o contrato. |

## Planícies de Nareth

| ID | Nome | Tipo | Região | Nível mínimo | Condição | Recompensa | Descrição |
|---|---|---|---|---|---|---|---|
| `CON_PDN_01` | Patrulha de Nareth | Caça | Planícies de Nareth | `FAIXA_R3` | Concluir o objetivo de Caça definido | `REWARD_R3_CACA` | Uma ameaça foi identificada em uma rota das Planícies. Elimine o alvo registrado. |
| `CON_PDN_02` | Coleta das Planícies | Coleta | Planícies de Nareth | `FAIXA_R3` | Obter o Material exigido | `REWARD_R3_COLETA` | Um recurso regional foi solicitado para abastecimento. Reúna a quantidade definida pelo contrato. |
| `CON_PDN_03` | Rota de Suprimentos | Entrega | Planícies de Nareth | `FAIXA_R3` | Realizar a entrega no destino | `REWARD_R3_ENTREGA` | Suprimentos precisam alcançar outro ponto da região. Faça a entrega no destino indicado. |
| `CON_PDN_04` | Marca na Paisagem | Investigação | Planícies de Nareth | `FAIXA_R3` | Examinar o ponto definido | `REWARD_R3_INVESTIGACAO` | Uma marca foi registrada na paisagem. Examine o local e confirme a ocorrência sem tirar conclusões além da evidência. |
| `CON_PDN_05` | Vestígio na Estrada | Investigação | Planícies de Nareth | `FAIXA_R3` | Confirmar a investigação | `REWARD_R3_INVESTIGACAO` | Um vestígio recente foi encontrado em uma rota. Examine o ponto e registre o resultado. |
| `CON_PDN_06` | Caçada nas Planícies | Caça | Planícies de Nareth | `FAIXA_R3` | Concluir o objetivo de Caça | `REWARD_R3_CACA` | A presença de uma ameaça foi confirmada. Complete a Caça definida pelo contrato. |

## Várzeas Carmesins

| ID | Nome | Tipo | Região | Nível mínimo | Condição | Recompensa | Descrição |
|---|---|---|---|---|---|---|---|
| `CON_VC_01` | Ameaça Carmesim | Caça | Várzeas Carmesins | `FAIXA_R4` | Concluir o objetivo de Caça | `REWARD_R4_CACA` | Uma ameaça interfere nas rotas das Várzeas. Elimine o alvo definido no contrato. |
| `CON_VC_02` | Ferro de Salmoura | Coleta | Várzeas Carmesins | `FAIXA_R4` | Obter o Material exigido | `REWARD_R4_COLETA` | Fragmentos metálicos podem ser recuperados nas áreas adequadas das Várzeas. Reúna o material solicitado. |
| `CON_VC_03` | Couro de Várzea | Coleta | Várzeas Carmesins | `FAIXA_R4` | Obter o Material exigido | `REWARD_R4_COLETA` | Um couro regional é necessário para abastecimento. Reúna o recurso indicado. |
| `CON_VC_04` | Junco Ferruginoso | Coleta | Várzeas Carmesins | `FAIXA_R4` | Obter o Material exigido | `REWARD_R4_COLETA` | Juncos com propriedades adequadas são procurados nas Várzeas. Reúna o material solicitado. |
| `CON_VC_05` | Entrega das Várzeas | Entrega | Várzeas Carmesins | `FAIXA_R4` | Realizar a entrega | `REWARD_R4_ENTREGA` | Um carregamento precisa alcançar o destino através das Várzeas. Faça a entrega indicada. |
| `CON_VC_06` | Soro Antigo | Coleta | Várzeas Carmesins | `FAIXA_R4` | Obter o Material exigido | `REWARD_R4_COLETA` | Um recurso raro das Várzeas foi solicitado. Reúna o Soro necessário para concluir o contrato. |

## Altos Cinéreos

| ID | Nome | Tipo | Região | Nível mínimo | Condição | Recompensa | Descrição |
|---|---|---|---|---|---|---|---|
| `CON_AC_01` | Ameaça da Escarpa | Caça | Altos Cinéreos | `FAIXA_R5` | Concluir o objetivo de Caça | `REWARD_R5_CACA` | Uma ameaça foi identificada em uma rota elevada. Elimine o alvo indicado pelo contrato. |
| `CON_AC_02` | Ferro de Contrapeso | Coleta | Altos Cinéreos | `FAIXA_R5` | Obter o Material exigido | `REWARD_R5_COLETA` | Metal usado em estruturas de sustentação ainda pode ser recuperado. Reúna o recurso solicitado. |
| `CON_AC_03` | Couro de Escarpa | Coleta | Altos Cinéreos | `FAIXA_R5` | Obter o Material exigido | `REWARD_R5_COLETA` | Um couro resistente é necessário para abastecimento. Reúna o material regional solicitado. |
| `CON_AC_04` | Líquen de Pedreira | Coleta | Altos Cinéreos | `FAIXA_R5` | Obter o Material exigido | `REWARD_R5_COLETA` | Um líquen específico cresce em áreas de pedreira. Reúna a quantidade solicitada. |
| `CON_AC_05` | Cinza de Basalto | Coleta | Altos Cinéreos | `FAIXA_R5` | Obter o Material exigido | `REWARD_R5_COLETA` | Cinza adequada pode ser recuperada em pontos específicos dos Altos. Reúna o material necessário. |
| `CON_AC_06` | Registro da Escarpa | Investigação | Altos Cinéreos | `FAIXA_R5` | Examinar o ponto definido | `REWARD_R5_INVESTIGACAO` | Um ponto estrutural precisa ser verificado. Examine a área e registre somente aquilo que puder ser observado. |

## Confins do Véu

| ID | Nome | Tipo | Região | Nível mínimo | Condição | Recompensa | Descrição |
|---|---|---|---|---|---|---|---|
| `CON_CDV_01` | Ameaça do Último Refúgio | Caça | Confins do Véu | `FAIXA_R6` | Concluir o objetivo de Caça | `REWARD_R6_CACA` | Uma ameaça foi identificada nas rotas dos Confins. Elimine o alvo definido pelo contrato. |
| `CON_CDV_02` | Ferro de Baliza | Coleta | Confins do Véu | `FAIXA_R6` | Obter o Material exigido | `REWARD_R6_COLETA` | Metal usado nas estruturas regionais precisa ser recuperado. Reúna o Material solicitado. |
| `CON_CDV_03` | Couro de Marcha | Coleta | Confins do Véu | `FAIXA_R6` | Obter o Material exigido | `REWARD_R6_COLETA` | Um couro regional é necessário para manutenção de equipamentos e suprimentos. Reúna o recurso solicitado. |
| `CON_CDV_04` | Musgo de Limiar | Coleta | Confins do Véu | `FAIXA_R6` | Obter o Material exigido | `REWARD_R6_COLETA` | Um musgo específico é encontrado próximo às rotas dos Confins. Reúna o material solicitado. |
| `CON_CDV_05` | Pó de Referência | Coleta | Confins do Véu | `FAIXA_R6` | Obter o Material exigido | `REWARD_R6_COLETA` | Um pó regional é necessário para registros e manutenção. Reúna a quantidade definida no contrato. |
| `CON_CDV_06` | Registro do Limiar | Investigação | Confins do Véu | `FAIXA_R6` | Examinar o ponto definido | `REWARD_R6_INVESTIGACAO` | Um registro precisa ser confirmado nos Confins. Examine o local e preserve a distinção entre evidência e interpretação. |

---

# 37. Critérios de aceitação

### AC-01 — oferta

**Dado** um personagem elegível para uma região,  
**quando** abrir o quadro regional,  
**então** o sistema apresenta somente Contratos atualmente disponíveis e elegíveis.

### AC-02 — personagem inelegível

**Dado** um personagem sem o gate regional necessário,  
**quando** acessar o quadro,  
**então** os Contratos daquela faixa não podem ser aceitos.

### AC-03 — aceite

**Dado** um Contrato disponível,  
**quando** o jogador pressionar `[ACEITAR]`,  
**então** uma instância persistente é criada no estado `ACEITO`.

### AC-04 — duplicação de aceite

**Dado** um callback duplicado de `[ACEITAR]`,  
**quando** ambos forem processados,  
**então** somente uma instância válida permanece aceita.

### AC-05 — progresso

**Dado** um Contrato aceito,  
**quando** o personagem executar uma ação que corresponda ao objetivo,  
**então** o progresso válido é registrado.

### AC-06 — ação inválida

**Dado** um Contrato aceito,  
**quando** o personagem executar uma ação que não corresponda ao objetivo,  
**então** o progresso do Contrato não é alterado.

### AC-07 — conclusão

**Dado** um Contrato em andamento,  
**quando** todos os requisitos forem satisfeitos,  
**então** o estado passa para `CONCLUÍDO`.

### AC-08 — recompensa

**Dado** um Contrato concluído,  
**quando** o jogador pressionar `[RESGATAR]`,  
**então** XP, Coroas e Materiais definidos pelo perfil são entregues uma única vez.

### AC-09 — resgate duplicado

**Dado** um Contrato já resgatado,  
**quando** um callback antigo de `[RESGATAR]` for recebido,  
**então** nenhuma recompensa adicional é concedida.

### AC-10 — abandono

**Dado** um Contrato aceito,  
**quando** o jogador confirmar `[CONFIRMAR ABANDONO]`,  
**então** o estado passa para `ABANDONADO`.

### AC-11 — abandono sem confirmação

**Dado** um Contrato aceito,  
**quando** o jogador selecionar `[MANTER CONTRATO]`,  
**então** o Contrato permanece ativo.

### AC-12 — expiração

**Dado** um Contrato cuja validade terminou,  
**quando** o sistema validar sua instância,  
**então** o estado passa para `EXPIRADO` se ainda não tiver sido concluído.

### AC-13 — expiração durante combate

**Dado** um objetivo de combate iniciado antes da expiração,  
**quando** o combate terminar validamente depois da expiração,  
**então** a conclusão do objetivo pode ser registrada.

### AC-14 — ação iniciada depois da expiração

**Dado** um Contrato já expirado,  
**quando** uma nova ação de objetivo for iniciada,  
**então** ela não pode concluir o Contrato.

### AC-15 — reinício

**Dado** um servidor reiniciado,  
**quando** um personagem consultar seu Contrato,  
**então** o estado persistido é restaurado sem duplicação.

### AC-16 — personagem deletado

**Dado** um personagem excluído,  
**quando** houver Contratos associados,  
**então** nenhum Contrato pode continuar jogável ou transferir recompensa.

### AC-17 — região bloqueada

**Dado** um Contrato associado a uma região que o personagem não pode acessar,  
**quando** tentar iniciar uma ação incompatível,  
**então** o sistema rejeita a ação.

### AC-18 — ausência de equipamento

**Dado** um Contrato disponível,  
**quando** o jogador o concluir,  
**então** o Contrato não pode gerar Equipamento como recompensa.

### AC-19 — narrativa

**Dado** qualquer Contrato,  
**quando** for concluído,  
**então** nenhuma escolha narrativa de Campanha é registrada.

### AC-20 — Campanha

**Dado** um personagem que complete vários Contratos,  
**quando** consultar a Campanha,  
**então** nenhum Contrato pode substituir, desbloquear ou concluir uma Missão Principal.

### AC-21 — troca entre contas

**Dado** dois personagens diferentes,  
**quando** um deles concluir um Contrato,  
**então** a recompensa não pode ser transferida para o outro.

### AC-22 — quadro renovado

**Dado** uma oferta que expirou no quadro,  
**quando** o quadro for renovado,  
**então** uma nova instância possui identidade própria e não reutiliza a instância anterior.

### AC-23 — recompensa pendente

**Dado** um Contrato `CONCLUÍDO`,  
**quando** o personagem ainda não tiver selecionado `[RESGATAR]`,  
**então** a recompensa permanece pendente e não pode ser contabilizada novamente.

### AC-24 — UI stale

**Dado** uma mensagem antiga do Telegram,  
**quando** o jogador pressionar um botão cujo estado já mudou,  
**então** o backend revalida a instância antes de executar qualquer mutação.

---

# 38. Valores a aprovar pelo autor

Esta é a única tabela do Documento B que deve conter os números de jogo propostos.

| Parâmetro | Proposta |
|---|---:|
| Quantidade de Contratos no catálogo inicial | 36 |
| Contratos por região | 6 |
| Quantidade de regiões | 6 |
| Tipos de Contrato ativos inicialmente | 4 |
| Tipos definidos no sistema incluindo Escolta | 5 |
| Contratos simultâneos por personagem | 3 |
| Ofertas simultâneas no quadro | 6 |
| Regiões de progressão | R1–R6 |
| Gate R1 | pós-P1 |
| Gate R2 | pós-P6 |
| Gate R3 | pós-P12 |
| Gate R4 | pós-P18 |
| Gate R5 | pós-P24 |
| Gate R6 | pós-P30 |
| Duração da oferta no quadro | 24 horas |
| Frequência de renovação | 24 horas |
| Duração de Contrato aceito | 48 horas |
| Penalidade econômica por abandono | 0 |
| Multiplicador Caça | 1,00 |
| Multiplicador Coleta | 0,90 |
| Multiplicador Entrega | 0,95 |
| Multiplicador Investigação | 0,90 |
| Multiplicador Escolta | 1,10 |
| Faixa R1 | níveis 1–10 |
| Faixa R2 | níveis 11–20 |
| Faixa R3 | níveis 21–30 |
| Faixa R4 | níveis 31–40 |
| Faixa R5 | níveis 41–50 |
| Faixa R6 | níveis 51–60 |
| Contratos iniciais de Escolta ativos | 0 |
| Limite máximo de botões na tela | 8 |

### Perfis econômicos propostos

| Perfil | XP | Coroas | Materiais |
|---|---:|---:|---:|
| `REWARD_R1_CACA` | 120 | 20 | 2 |
| `REWARD_R1_COLETA` | 100 | 15 | 3 |
| `REWARD_R1_ENTREGA` | 110 | 25 | 2 |
| `REWARD_R1_INVESTIGACAO` | 105 | 20 | 2 |
| `REWARD_R2_CACA` | 260 | 45 | 2 |
| `REWARD_R2_COLETA` | 220 | 35 | 3 |
| `REWARD_R2_ENTREGA` | 240 | 50 | 2 |
| `REWARD_R2_INVESTIGACAO` | 230 | 45 | 2 |
| `REWARD_R3_CACA` | 480 | 80 | 3 |
| `REWARD_R3_COLETA` | 410 | 65 | 4 |
| `REWARD_R3_ENTREGA` | 440 | 90 | 3 |
| `REWARD_R3_INVESTIGACAO` | 425 | 80 | 3 |
| `REWARD_R4_CACA` | 850 | 140 | 3 |
| `REWARD_R4_COLETA` | 720 | 115 | 4 |
| `REWARD_R4_ENTREGA` | 780 | 155 | 3 |
| `REWARD_R4_INVESTIGACAO` | 750 | 140 | 3 |
| `REWARD_R5_CACA` | 1.450 | 240 | 4 |
| `REWARD_R5_COLETA` | 1.230 | 195 | 5 |
| `REWARD_R5_ENTREGA` | 1.330 | 265 | 4 |
| `REWARD_R5_INVESTIGACAO` | 1.280 | 240 | 4 |
| `REWARD_R6_CACA` | 2.300 | 380 | 5 |
| `REWARD_R6_COLETA` | 1.950 | 310 | 6 |
| `REWARD_R6_ENTREGA` | 2.100 | 420 | 5 |
| `REWARD_R6_INVESTIGACAO` | 2.050 | 380 | 5 |

> **Nota de aprovação:** os valores acima são exclusivamente propostas de balanceamento. Eles não substituem os valores canônicos de XP, Coroas ou Materiais já definidos para conteúdos existentes. A implementação deve validar conflitos contra a Fonte Mestra antes de ativar o sistema.

---

# 39. Fora do escopo

Ficam fora deste documento:

- novos NPCs;
- nova região;
- nova moeda;
- nova categoria de recompensa;
- Equipamento exclusivo de Contrato;
- Runa exclusiva de Contrato;
- Encantamento exclusivo de Contrato;
- Consumível exclusivo de Contrato;
- narrativa ramificada;
- Choice Node em Contratos;
- avanço de Campanha por Contratos;
- PvP;
- Arena;
- Guilda;
- Mercado como sistema de Contrato;
- Crônica;
- Mini App;
- sistema completo de Escolta;
- criação de nova mecânica de combate;
- criação de nova mecânica de coleta;
- alteração das regras globais de combate;
- alteração dos gates da Campanha;
- alteração das 36 Missões Principais;
- alteração das 36 Missões Secundárias;
- alteração das escolhas narrativas existentes;
- alteração do Prólogo além das escolhas definidas no Documento A.

---

# FIM DO DOCUMENTO B

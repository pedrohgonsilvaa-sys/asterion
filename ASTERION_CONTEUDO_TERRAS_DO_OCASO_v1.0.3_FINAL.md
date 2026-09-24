# ASTERION — Fonte de Conteúdo Regional
## Terras do Ocaso · v1.0.3 FINAL

**Data de consolidação:** 2026-09-22  
**Escopo:** vertical slice / primeira jornada / Nv.1–10, com saída para Nv.11  
**Autoridade estrutural:** `ASTERION_GDD_Estrutural_v1.4.5_Fonte_Mestra.md`  
**Autoridade Visual/UI:** `ASTERION_UI_DECISOES_2026-09-22_FINAL_SYNC_v1.4.5_TDO_v1.0.3.md`  

> Esta Fonte contém **conteúdo regional**, não redefine sistemas globais. Em conflito estrutural, prevalece a Fonte Mestra v1.4.5. Em conflito de apresentação, prevalece a Fonte Visual/UI vigente.

> **Status FINAL:** conteúdo regional fechado para implementação da vertical slice. Esta revisão **v1.0.3** substitui integralmente `v1.0.2 FINAL` e não reabre balanceamento, economia, XP, pools, chances ou narrativa. Integra apenas semânticas de IA já fechadas e sincronização documental com a Fonte Mestra/Visual vigentes.

**Correções v1.0.1:** kits numéricos dos 3 Elites e do Vigia Partido; pools completos de Caçada/Variantes; Desbravar completo; Provações de Classe completas; configuração implementável do Bestiário; aquisição determinística do Núcleo/Receita do Vigia Partido; auditoria de XP da Cripta corrigida.

**Correções v1.0.2:** consolidação implementável de P1 — Vozes na Estrada; sinais fixos da Etapa 2; Cão Cinéreo fixo no encontro roteirizado; recompensa própria do encontro explicitada como zero; derrota/retry/recovery; textos de transição; ordem dos registros permanentes; descoberta do Braseiro do Refúgio; idempotência e fronteiras técnicas de implementação.

**Correções v1.0.3:** prioridade implementável de IA do Corvo de Fuligem, Peregrino Calcinado e Alfa Cinéreo; Caçada em Grupo passa a herdar a referência global de nível do GDD v1.4.5; Receitas especiais de Masmorra permanecem no roll global salvo revelação direta explícita; autoridade documental e Visual/UI sincronizados. Nenhum valor numérico foi alterado.

---

# 1. Identidade regional

**Região:** Terras do Ocaso  
**Faixa:** Nv.1–10  
**Saída:** Nv.11 para Vales dos Enforcados  
**Campanha:** As Cinzas da Ruptura  
**Chefe regional:** Vigia Partido  

Progressão temática:

`Estrada das Cinzas → Refúgio do Ocaso → Charneca da Fuligem → Bosque Calcinado → Ruínas do Vigia → Câmara do Poente`

A região ensina e testa progressivamente:

- Ataque Básico e Defender;
- primeira Arte da Classe;
- Caçada e Ronda;
- Desbravar;
- Veneno, Sangramento e Queimadura;
- telegraphs;
- Barreiras e DEF;
- Elites;
- duas Masmorras;
- Bestiário e Códice;
- primeiro Talento no Nv.5;
- segundo Talento, Provação e Caminho no Nv.10;
- primeiro Chefe regional.

---

# 2. Progressão Nv.1–10

| Nv. | Conteúdo principal |
|---:|---|
| 1 | Prólogo; Tutorial; P1; Ataque Básico; Defender; primeira Arte; Cão Cinéreo |
| 2 | S1; Caçada/Ronda da Estrada já podem estar ativas; pool regional normal |
| 3 | P2; Charneca da Fuligem; primeiro Elite elegível |
| 4 | S2; segunda Arte da Classe; Veneno; Cripta do Ocaso elegível após descoberta |
| 5 | P3 + S3; primeiro Ponto de Talento; telegraphs |
| 6 | faixa sistêmica; Sangramento; Cripta/Bosque/Caçadas/Desbravar sustentam progresso |
| 7 | P4 + S4; terceira Arte da Classe |
| 8 | S5; Ruínas do Vigia; Galerias do Vigia elegível após descoberta |
| 9 | P5; quarta Arte da Classe; Custódio do Poente |
| 10 | P6 + S6; segundo Ponto de Talento; Provação; escolha de Caminho; Vigia Partido |
| 11 | saída regional para Vales dos Enforcados quando gates forem satisfeitos |

## Correção de gate inicial

Após concluir P1, mesmo ainda no Nv.1:

- `Caçada Manual · Estrada das Cinzas` fica disponível;
- `Desbravar · Estrada das Cinzas` fica disponível.

A Ronda local desbloqueia após a primeira vitória manual válida naquele Local.

Isso evita hard lock de XP entre Nv.1 e Nv.2.

---

# 3. Locais

## 3.1 Estrada das Cinzas

**Faixa:** Nv.1–3  
**Função:** prólogo, primeiro Braseiro, tutorial de combate, primeira Caçada e primeira exploração sistêmica.

## 3.2 Refúgio do Ocaso

**Função:** hub seguro regional.

Não possui pool normal de Caçada nem Ronda.

Sistemas apresentados/centralizados:

- NPCs regionais;
- Ofícios;
- Caminho/Provação quando elegível;
- serviços seguros compatíveis;
- Travessia por Braseiros.

## 3.3 Charneca da Fuligem

**Faixa:** Nv.3–5  
**Função:** primeiro salto de dificuldade, Veneno, descoberta da Cripta.

## 3.4 Bosque Calcinado

**Faixa:** Nv.5–8  
**Função:** Sangramento, Queimadura, telegraphs, segundo estágio de exploração, Elite regional.

## 3.5 Ruínas do Vigia

**Faixa:** Nv.8–10  
**Função:** Barreiras, DEF, estrutura de guarda, segunda Masmorra, preparação do clímax.

## 3.6 Câmara do Poente

Local de clímax narrativo ligado ao P6 e à revelação controlada da Âncora do Poente.

---

# 4. Braseiros permanentes

1. **Braseiro da Estrada** — Prólogo.
2. **Braseiro do Refúgio** — chegada ao Refúgio/P1.
3. **Braseiro do Vento Morto** — Desbravar na Charneca.
4. **Braseiro dos Galhos Mortos** — Desbravar no Bosque.
5. **Braseiro do Poente** — Desbravar nas Ruínas.

Braseiros de Masmorra não entram na Travessia permanente.

---

# 5. Missões

A região possui exatamente:

- **6 Missões Principais**;
- **6 Missões Secundárias**.

Offsets, XP, Coroas, Materiais e Equipamentos seguem integralmente a Fonte Mestra. Os roteiros abaixo são a versão oficial consolidada da vertical slice.

## 5.1 Resumo implementável

| ID | Nv. | Tipo | Título | Início | Local principal |
|---|---:|---|---|---|---|
| P1 | 1 | Principal | Vozes na Estrada | Automática após o Prólogo | Estrada / Refúgio |
| S1 | 2 | Curta | Luzes sob as Cinzas | Oren Cal | Estrada |
| P2 | 3 | Principal | Fuligem sem Fogo | Alda Veyr | Charneca |
| S2 | 4 | Padrão | Os Nomes Esquecidos | Oren Cal | Charneca |
| P3 | 5 | Principal | Sob Galhos Calcinados | Oren Cal | Bosque |
| S3 | 5 | Curta | Rastros sob os Galhos | Alda Veyr | Bosque |
| P4 | 7 | Principal | Pedras que Ainda Vigiam | Alda Veyr | Bosque / Ruínas |
| S4 | 7 | Padrão | Vigília sem Voz | Oren Cal | Ruínas |
| S5 | 8 | Padrão | A Luz que Não Aquece | Oren Cal | Ruínas |
| P5 | 9 | Principal | A Porta do Poente | Alda Veyr | Ruínas |
| P6 | 10 | Principal · Clímax | O Vigia Partido | Automática após P5 + Nv.10 | Câmara do Poente |
| S6 | 10 | Longa | Onde os Nomes Terminaram | Oren Cal | Ruínas |

### Dependências

Principais:

`Prólogo → P1 → P2 → P3 → P4 → P5 → P6`

Cada Principal também respeita seu nível recomendado como gate normal da primeira jornada.

Secundárias:

- S1 exige P1 concluída e Nv.2.
- S2 exige P2 concluída e Nv.4.
- S3 exige acesso ao Bosque, P3 ativa ou concluída e Nv.5.
- S4 exige P4 concluída e Nv.7.
- S5 exige P4 concluída e Nv.8.
- S6 exige S2 concluída, P5 concluída e Nv.10.

Missões Secundárias podem ser abandonadas/reaceitas sem duplicar flags permanentes ou recompensas únicas.

---

## 5.2 Recompensas exatas

| ID | XP | Coroas | Materiais Básicos vinculados | Equipamento |
|---|---:|---:|---|---|
| P1 | 2.400 | 120 | 1 Ferro de Fuligem + 1 Couro Escoriado | — |
| P2 | 3.300 | 140 | 1 Ferro de Fuligem + 2 Ervas Cinzentas + 1 Resíduo do Ocaso | — |
| P3 | 4.400 | 180 | — | escolha entre 3 Raros Nv.5 |
| P4 | 5.700 | 250 | 2 Ferros de Fuligem + 2 Resíduos do Ocaso | — |
| P5 | 7.100 | 300 | 3 Ferros de Fuligem + 1 Resíduo do Ocaso | — |
| P6 | 14.220 | 500 | 4 Ferros de Fuligem + 4 Resíduos do Ocaso | escolha entre 3 Épicos Nv.10 |
| S1 | 1.140 | 60 | — | — |
| S2 | 2.695 | 120 | 1 Erva Cinzenta + 1 Resíduo do Ocaso | — |
| S3 | 1.760 | 90 | 2 Couros Escoriados | — |
| S4 | 3.990 | 150 | 2 Ferros de Fuligem + 1 Couro Escoriado + 1 Resíduo do Ocaso | — |
| S5 | 4.480 | 160 | 1 Ferro de Fuligem + 1 Erva Cinzenta + 2 Resíduos do Ocaso | — |
| S6 | 7.900 | 310 | 2 Ferros de Fuligem + 2 Couros Escoriados + 2 Ervas Cinzentas + 2 Resíduos do Ocaso | — |

Todos os Materiais de Missão acima são **vinculados**, conforme `1 UM = 2 Materiais Básicos regionais vinculados`.

### Escolha de P3

Escolher 1:

1. **Véu do Bosque** · Cabeça · Raro · `item_level 5` · `+0` · Vinculado ao Adquirir.
2. **Selo do Galho Morto** · Acessório · Raro · `item_level 5` · `+0` · Vinculado ao Adquirir.
3. **Relicário da Cinza Verde** · Artefato · Raro · `item_level 5` · `+0` · Vinculado ao Adquirir.

Nenhum possui efeito exclusivo fora do orçamento Raro normal do slot.

### Escolha de P6

Escolher 1:

1. **Guarda do Último Posto** · Torso · Épico · `item_level 10` · `+0` · Vinculado ao Adquirir.
2. **Selo do Poente** · Acessório · Épico · `item_level 10` · `+0` · Vinculado ao Adquirir.
3. **Relicário da Âncora Velada** · Artefato · Épico · `item_level 10` · `+0` · Vinculado ao Adquirir.

Nenhum possui proc ou poder acima do orçamento Épico normal.

---

## 5.3 P1 — Vozes na Estrada · Conteúdo Implementável

### 5.3.1 Escopo

Este bloco complementa exclusivamente **P1 — Vozes na Estrada**.

Não altera:

- as 7 etapas já aprovadas;
- recompensa da Missão;
- NPCs;
- efeitos permanentes já definidos;
- balanceamento global;
- progressão Nv.1→11;
- tutorial/prólogo;
- sistemas de Caçada, Bestiário, Vigor ou Saque.

**Início:** automático após conclusão válida do Prólogo/tutorial.

**Objetivo narrativo:** levar o personagem do fim do tutorial ao primeiro núcleo seguro e estabelecer Alda Veyr, Oren Cal e o Refúgio do Ocaso.

---

### 5.3.2 Etapas oficiais

A estrutura permanece exatamente:

1. Seguir pela Estrada das Cinzas.
2. Examinar dois sinais recentes de passagem.
3. Sobreviver a um encontro roteirizado simples da Estrada.
4. Alcançar o **Refúgio do Ocaso**.
5. Falar com **Alda Veyr**.
6. Conhecer **Oren Cal**.
7. Ativar o **Braseiro do Refúgio**.

Nenhuma etapa é adicionada, removida ou reordenada.

---

### 5.3.3 Etapa 1 — Seguir pela Estrada das Cinzas

#### Texto player-facing

*A chama deixada para trás desaparece pouco a pouco entre a fuligem. A Estrada das Cinzas segue adiante, irregular e silenciosa, mas desta vez há marcas recentes onde antes havia apenas abandono.*

A progressão leva diretamente aos dois sinais da Etapa 2.

Não existe combate nesta transição.

---

### 5.3.4 Etapa 2 — Dois sinais recentes de passagem

Os dois sinais são fixos e aparecem nesta ordem.

#### 5.3.4.1 👣 Pegadas na Cinza

##### Texto player-facing

**👣 Pegadas na Cinza**

*Marcas de botas cortam a fuligem em uma única direção. As bordas ainda estão nítidas demais para terem permanecido ali por muito tempo.*

##### Informação transmitida

O personagem pode concluir apenas que:

- alguém passou recentemente;
- seguia adiante pela Estrada.

Não identifica:

- Alda;
- Oren;
- Refúgio do Ocaso;
- quantidade exata de viajantes.

Ao examinar, o jogo deve persistir de forma idempotente que o **primeiro sinal recente de passagem foi examinado**.

##### ID técnico sugerido

`p1.sign.pegadas_na_cinza`

Uma implementação pode, por exemplo, representar o estado como:

`p1_recent_sign_1 = true`

Esses nomes são apenas sugestões de implementação e não constituem schema obrigatório da Fonte.

---

#### 5.3.4.2 🛞 Sulcos Recentes

##### Texto player-facing

**🛞 Sulcos Recentes**

*Duas marcas estreitas atravessam a cinza ao lado das pegadas. A fuligem ainda não voltou a cobrir completamente os sulcos deixados pelas rodas.*

##### Informação transmitida

O personagem pode concluir apenas que:

- algum tipo de carroça ou carga passou pela rota;
- as marcas seguem na mesma direção das pegadas.

Não cria item, recurso ou entrada de Códice.

Ao examinar, o jogo deve persistir de forma idempotente que o **segundo sinal recente de passagem foi examinado**.

##### ID técnico sugerido

`p1.sign.sulcos_recentes`

Uma implementação pode, por exemplo, representar o estado como:

`p1_recent_sign_2 = true`

Esses nomes são apenas sugestões de implementação.

---

#### 5.3.4.3 Conclusão da Etapa 2

A Etapa 2 conclui somente quando os **dois sinais obrigatórios** tiverem sido examinados validamente.

A implementação deve persistir esse progresso de modo que reconnect ou reconstrução da interface não obriguem o jogador a repetir sinais já validados.

Depois disso, a progressão dispara a entrada narrativa do encontro da Etapa 3.

---

### 5.3.5 Etapa 3 — Encontro roteirizado

#### 5.3.5.1 Criatura oficial

O encontro é **fixo**.

Criatura:

**🐺 Cão Cinéreo**

Configuração autoritativa:

- Cão Cinéreo;
- Nv.1;
- Categoria Comum;
- Solo;
- sem Variante;
- sem sorteio no pool normal de Caçada.

Não realizar seleção entre Cão Cinéreo e Corvo de Fuligem.

Não consultar o pool normal de Caçada da Estrada para selecionar o inimigo.

IDs, enums e nomes de campos internos ficam a critério da implementação.

---

### 5.3.6 Motivo da criatura fixa

O Cão Cinéreo já foi introduzido no Prólogo.

P1 utiliza a mesma espécie para transformar o conceito recém-ensinado em um combate normal, sem introduzir simultaneamente:

- nova criatura;
- novo bônus genérico de primeira observação;
- nova camada econômica.

Isso também torna P1 determinística e elimina divergência entre jogadores na primeira Missão Principal.

---

### 5.3.7 Entrada narrativa do encontro

Após examinar o segundo sinal:

*Os sulcos desaparecem onde a estrada se estreita entre pedras partidas. Antes que você possa seguir as marcas, um rosnado baixo rompe o silêncio.*

*Um Cão Cinéreo emerge da fuligem e fecha a passagem.*

O combate começa diretamente.

---

### 5.3.8 Diferença para o tutorial

Este encontro **não utiliza** o perfil especial do primeiro combate do Prólogo.

Não utiliza a máscara pedagógica.

Não obriga:

- Atacar;
- Defender;
- primeira Arte.

Desde a primeira oportunidade do jogador, a HUD utiliza o combate normal e apresenta todas as ações atualmente válidas.

O Cão utiliza seu perfil normal de conteúdo correspondente ao Nv.1.

Não reutilizar os multiplicadores especiais de HP/ATQ/DEF/AGI do Cão tutorial.

A intenção é:

**tutorial = aprender as ações**

**P1 = usar livremente aquilo que acabou de aprender**

---

### 5.3.9 Condição de conclusão da Etapa 3

Embora a redação da etapa permaneça:

**“Sobreviver a um encontro roteirizado simples da Estrada.”**

a condição autoritativa para avançar é:

**vitória do personagem.**

Derrota não conclui a etapa.

Após vitória válida, a Etapa 3 deve ser registrada como concluída de forma idempotente e a missão avança para:

**Etapa 4 — Alcançar o Refúgio do Ocaso.**

Uma implementação pode utilizar uma flag como:

`p1_step_3_complete`

mas o nome do campo não é normativo.

---

### 5.3.10 Recompensas do encontro de P1

Este encontro é um **combate roteirizado de Missão sem recompensa econômica própria**.

Uma implementação pode possuir internamente um perfil equivalente a:

`mission_scripted_no_economy`

mas esse identificador não é obrigatório.

O comportamento abaixo é a parte autoritativa.

#### XP normal de inimigo

`0 XP`

Não aplicar a conversão normal de XP de inimigos.

A vitória contra este Cão não acrescenta os aproximadamente `240 XP` de um Comum Nv.1.

#### Bônus de primeira observação do Bestiário

`0 XP adicional`

Este encontro de P1 **nunca funciona como nova fonte do bônus genérico de primeira observação**.

Se o Cão Cinéreo já estiver **Observado** pelo Prólogo, o conhecimento é simplesmente preservado.

Se um estado legado ou inconsistente exigir reparo do conhecimento já legitimamente adquirido, o reparo deve ser:

- idempotente;
- limitado ao estado de conhecimento que já deveria existir;
- sem concessão de XP.

P1 não concede novamente nem cria uma nova oportunidade para o bônus genérico de primeira observação.

#### Progresso de Bestiário

O encontro pode registrar normalmente evidências ou BKP que sejam legitimamente elegíveis pelas regras globais do Bestiário e ainda não tenham sido obtidos.

Isso não cria XP adicional por si só.

P1 não configura nenhum marco adicional de XP de Bestiário para este encontro.

#### Saque

`nenhum Saque`

#### Coroas do encontro

`0`

#### Materiais do encontro

`0`

#### Equipamento

`0`

#### Vigor

`0 consumido`

O encontro não é uma Caçada econômica.

---

### 5.3.11 Auditoria de XP preservada

Depois da conclusão integral de P1:

Tutorial:

`320 XP`

P1:

`2.400 XP`

Encontro interno de P1:

`0 XP`

Bônus adicional de primeira observação:

`0 XP`

Total:

`2.720 / 4.800 XP`

Portanto permanece válida a auditoria oficial:

`Tutorial + P1 = 2.720 / 4.800 XP`

Nenhum comportamento deste encontro pode criar uma nova fonte de XP que altere essa auditoria.

---

### 5.3.12 Derrota na Etapa 3

Se o personagem for **Derrotado**:

1. o encontro atual termina como derrota;
2. a Etapa 3 permanece incompleta;
3. P1 continua ativa;
4. Etapas 1 e 2 permanecem concluídas;
5. nenhum efeito permanente das Etapas 4–7 é registrado;
6. nenhuma recompensa de P1 é entregue;
7. nenhum Vigor é consumido pelo encontro;
8. Consumíveis realmente utilizados permanecem consumidos.

Não existe falha permanente de P1.

P1 continua sendo uma Missão Principal e não pode ser abandonada.

---

### 5.3.13 Recovery após Derrota

Após a Derrota:

o personagem renasce no:

**🔥 Braseiro da Estrada**

já descoberto durante o Prólogo.

Aplicar as regras normais de Braseiro permanente:

- HP restaurado a `100%`;
- estados comuns de combate removidos;
- Vigor não restaurado;
- Consumíveis gastos não restaurados.

A missão permanece em:

**Etapa 3 — Sobreviver a um encontro roteirizado simples da Estrada.**

---

### 5.3.14 Retry

Ao retomar P1:

o personagem retorna ao gatilho narrativo da Etapa 3.

Uma nova tentativa materializa novamente:

**🐺 Cão Cinéreo · Nv.1**

Não existe novo sorteio porque o alvo é fixo.

A nova tentativa começa:

- personagem com o estado atual após recovery;
- Cão Cinéreo com HP integral;
- efeitos do encontro anterior encerrados;
- combate normal desde a primeira oportunidade.

A tentativa derrotada deve permanecer registrada como resolvida em derrota.

A nova tentativa recebe uma nova identidade de encontro vinculada à mesma Etapa 3.

Reconnect durante uma tentativa ainda ativa deve retomar o encontro existente em vez de criar outro.

O formato exato de `encounter_id`, chaves ou campos persistidos pertence ao schema técnico da implementação.

---

### 5.3.15 Etapa 4 — Alcançar o Refúgio do Ocaso

Após vencer o Cão:

#### Texto de transição

*Mais adiante, a estrada deixa de ser apenas ruína. Pedras empilhadas, madeira reaproveitada e pontos de luz surgem através da fuligem.*

*Não é uma cidade. Ainda assim, pela primeira vez desde que despertou na estrada, há sinais claros de que pessoas permanecem aqui.*

**🏚️ Refúgio do Ocaso**

---

### 5.3.16 Registro permanente da Etapa 4

No momento em que a chegada ao Refúgio é validada:

**Refúgio do Ocaso torna-se um Local descoberto permanentemente.**

Esse registro ocorre **na Etapa 4**, antes da conversa com Alda.

A descoberta é:

- permanente;
- idempotente;
- disponível para sistemas que consultem Locais conhecidos.

#### Representação técnica sugerida

Uma implementação pode representar esse estado de forma equivalente a:

`location.refugio_do_ocaso.discovered = true`

O identificador exato não é obrigatório.

A Etapa 4 então conclui.

---

### 5.3.17 Etapa 5 — Alda Veyr

Ao entrar no núcleo do Refúgio:

#### Texto de apresentação

*Uma mulher observa a estrada antes mesmo de olhar para você. Sua atenção passa primeiro pelas marcas da fuligem, depois por suas armas e só então pelo seu rosto.*

**Alda Veyr**

Preservar obrigatoriamente a fala oficial:

**Alda Veyr:**  
“Se chegou até aqui sozinho, já aprendeu a primeira regra do Ocaso: estrada nenhuma permanece segura só porque alguém a chamou de estrada.”

Após a fala, Alda contextualiza de forma breve que o Refúgio sobrevive mantendo rotas, recursos e vigias funcionando.

Não acrescentar título político formal.

---

### 5.3.18 Registro permanente da Etapa 5

Ao concluir a primeira conversa obrigatória com Alda:

**Alda Veyr torna-se uma Figura conhecida no Códice.**

Esse registro ocorre na:

**Etapa 5**

e é idempotente.

#### Representação técnica sugerida

Uma implementação pode utilizar algo equivalente a:

`codex.figure.alda_veyr.discovered = true`

sem obrigação de utilizar esse nome de campo.

---

### 5.3.19 Etapa 6 — Oren Cal

Depois de Alda:

#### Texto de transição

*Alda indica um homem cercado por folhas, tábuas riscadas e fragmentos trazidos das estradas. Ele organiza cada peça como se perder uma palavra fosse tão grave quanto perder uma pessoa.*

**Oren Cal**

Preservar obrigatoriamente a fala oficial:

**Oren Cal:**  
“Se ouvir nomes no vento, não os descarte depressa. Há coisas nestas terras que sobrevivem apenas porque alguém se lembra delas.”

Oren pode contextualizar brevemente sua função de registrar relatos, nomes e inscrições.

Não apresentar suas interpretações como verdades absolutas.

---

### 5.3.20 Registro permanente da Etapa 6

Ao concluir a apresentação obrigatória de Oren:

**Oren Cal torna-se uma Figura conhecida no Códice.**

Esse registro ocorre na:

**Etapa 6**

e é idempotente.

#### Representação técnica sugerida

Uma implementação pode utilizar algo equivalente a:

`codex.figure.oren_cal.discovered = true`

sem obrigação de utilizar esse nome de campo.

---

### 5.3.21 Etapa 7 — Braseiro do Refúgio

Após conhecer Oren:

#### Texto de transição

*No centro do Refúgio, uma chama resiste entre pedras marcadas pelo uso. Pessoas passam por ela sem cerimônia, mas nenhuma ignora completamente sua presença.*

**🔥 Braseiro do Refúgio**

*O calor é constante. Pela primeira vez, a estrada atrás de você parece ter um ponto de retorno.*

A Etapa 7 mantém o verbo player-facing:

**Ativar o Braseiro do Refúgio.**

A Etapa conclui quando o personagem interage validamente com o Braseiro e sua descoberta permanente é registrada.

Não é necessária uma segunda tela de confirmação depois do registro válido.

---

### 5.3.22 Registro permanente da Etapa 7

Na interação válida:

**Braseiro do Refúgio torna-se permanentemente descoberto.**

#### Representação técnica sugerida

Uma implementação pode utilizar algo equivalente a:

`brazier.refugio_do_ocaso.discovered = true`

O nome exato do campo não é normativo.

O Braseiro do Refúgio passa a ser um **Braseiro permanente conhecido e utilizável**, apto a:

- servir para descanso;
- servir para renascimento;
- integrar a Travessia dos Braseiros quando todos os requisitos gerais aplicáveis estiverem satisfeitos.

A “ativação” da Etapa 7 é o ato narrativo que registra essa descoberta permanente.

Ela **não reutiliza o estado técnico de checkpoint ativo de Masmorra**.

Não utilizar como requisito global de mundo um campo equivalente a:

`active = true`

destinado ao estado de checkpoint de run de Masmorra.

Esse registro ocorre antes do commit final da conclusão de P1.

---

### 5.3.23 Conclusão de P1

Depois que o Braseiro do Refúgio foi registrado como descoberto:

**P1 é concluída.**

A conclusão é atômica e idempotente.

Somente nesse momento são concedidas as recompensas já aprovadas:

- `2.400 XP`;
- `120 Coroas`;
- `1 Ferro de Fuligem` vinculado;
- `1 Couro Escoriado` vinculado.

Não alterar esses valores.

---

### 5.3.24 Desbloqueios concedidos na conclusão

No mesmo commit autoritativo de conclusão de P1:

- **Caçada Manual da Estrada das Cinzas é desbloqueada**;
- **Desbravar na Estrada das Cinzas é desbloqueado**.

Esses desbloqueios ocorrem:

**na conclusão da Etapa 7 / conclusão de P1**

e não antes.

Eles são válidos mesmo se o personagem ainda estiver no Nv.1.

#### Representação técnica sugerida

Uma implementação pode utilizar estados equivalentes a:

`hunt_manual.estrada_das_cinzas = unlocked`

`explore.estrada_das_cinzas = unlocked`

Esses identificadores não são schema obrigatório da Fonte.

---

### 5.3.25 Ronda da Estrada

P1 **não desbloqueia diretamente** a Ronda.

Após P1:

Caçada Manual está disponível.

A primeira vitória posterior em uma **Caçada Manual válida** na Estrada registra a familiaridade necessária.

Somente então:

**Ronda da Estrada é desbloqueada.**

O Cão roteirizado da Etapa 3 de P1:

**não conta como essa primeira vitória manual**, porque não é uma Caçada Manual.

Uma implementação pode representar esse unlock através de flag própria, desde que preserve exatamente esse comportamento.

---

### 5.3.26 Ordem exata dos efeitos permanentes

| Momento | Registro autoritativo |
|---|---|
| Etapa 4 · chegada | Refúgio do Ocaso descoberto |
| Etapa 5 · conversa concluída | Alda Veyr registrada no Códice |
| Etapa 6 · apresentação concluída | Oren Cal registrado no Códice |
| Etapa 7 · interação com Braseiro | Braseiro do Refúgio descoberto e utilizável |
| Conclusão da Etapa 7 / P1 | recompensa de P1 |
| Conclusão da Etapa 7 / P1 | Caçada Manual da Estrada desbloqueada |
| Conclusão da Etapa 7 / P1 | Desbravar da Estrada desbloqueado |
| Depois de P1, primeira vitória em Caçada Manual | Ronda da Estrada desbloqueada |

Todos os registros são idempotentes.

Reconnect, callback duplicado ou reconstrução de UI não podem:

- conceder novamente recompensa;
- registrar novamente descoberta;
- duplicar entrada de Códice;
- liberar Ronda antecipadamente.

---

### 5.3.27 Representação técnica recomendada do encontro

O bloco abaixo é **exemplo de representação técnica**, não schema obrigatório:

```text
mission = P1
step = 3

encounter_type = MISSION_SCRIPTED
enemy = CAO_CINEREO
enemy_level = 1
variant_roll = false
tutorial_mask = false
hunt_pool_roll = false
vigor_cost = 0

enemy_xp = 0
first_observation_bonus_xp = 0
loot = none
crowns = 0
materials = none
equipment = none

completion_condition = player_victory
defeat_advances_step = false
defeat_recovery = BRASEIRO_DA_ESTRADA

retry_enemy = CAO_CINEREO
retry_reroll = false
```

O Codex pode utilizar outros:

- nomes de campos;
- enums;
- IDs;
- estruturas de tabela;
- nomes de flags.

O comportamento obrigatório é:

- Cão Cinéreo fixo Nv.1;
- sem Variante;
- sem roll de Caçada;
- sem XP de inimigo;
- sem bônus genérico adicional de primeira observação;
- sem Saque, Coroas, Materiais ou Equipamento;
- sem Vigor;
- vitória necessária para avançar;
- derrota retorna ao Braseiro da Estrada;
- retry mantém a mesma criatura e não rerrola o encontro;
- reconnect não duplica tentativa ativa.

---

### 5.3.28 Resultado narrativo de P1

P1 termina com o personagem sabendo apenas que:

- existe um núcleo seguro chamado **Refúgio do Ocaso**;
- Alda Veyr coordena necessidades práticas e segurança;
- Oren Cal registra relatos, nomes e inscrições;
- outros sobreviventes/viajantes utilizam a Estrada;
- Braseiros permanentes podem servir como pontos seguros.

P1 não revela antecipadamente:

- Antigos Asterianos;
- Âncoras;
- Primeiro Selo;
- Convergência;
- Avesso;
- Desvelados;
- qualquer mistério reservado às missões posteriores.
---

## 5.4 S1 — Luzes sob as Cinzas

**Objetivo narrativo:** apresentar o primeiro mistério regional sem explicar sua origem.

**Giver:** Oren Cal.

### Etapas

1. Investigar três pontos marcados da Estrada.
2. Examinar cinzas sem fonte de calor recente.
3. Observar uma luz distante em uma ocorrência roteirizada.
4. Retornar a Oren.

Combate não é obrigatório. Se ocorrer encontro incidental, usa o pool normal do Local.

### Fala-chave

**Oren Cal:**  
“Luz é uma coisa simples quando há fogo. Quando não há, ela se torna uma pergunta.”

### Efeitos

- atualiza Estrada das Cinzas no Códice;
- pode registrar Trecho **Luzes na Estrada** caso ainda não tenha sido obtido por Desbravar;
- não revela causa, Âncora, Avesso ou qualquer conclusão cosmológica.

---

## 5.5 P2 — Fuligem sem Fogo

**Objetivo narrativo:** abrir a Charneca e introduzir as Marcas na Fuligem.

**Giver:** Alda Veyr.

### Etapas

1. Viajar até a **Charneca da Fuligem**.
2. Examinar três pontos onde a fuligem aparece sem queima recente.
3. Derrotar um inimigo roteirizado elegível da Charneca.
4. Examinar a **Pedra Marcada** da rota principal.
5. Levar um registro da marca a Oren Cal.
6. Reportar a situação a Alda.

### Encontro

Preferência de conteúdo: **Aranha de Cinza** se já elegível; caso contrário, **Peregrino Calcinado**. `variant_roll=false`.

### Falas-chave

**Alda Veyr:**  
“Fuligem sem fogo significa que alguém chegou antes de nós — ou que estamos olhando para o problema errado.”

**Oren Cal:**  
“Esta marca não é decoração. Também não vou chamá-la de escrita até termos prova.”

### Efeitos

- descobre Charneca da Fuligem;
- cria/atualiza **Marcas na Fuligem**;
- habilita conteúdo normal da Charneca;
- não identifica autoria das marcas.

---

## 5.6 S2 — Os Nomes Esquecidos

**Objetivo narrativo:** apresentar os Peregrinos do Ocaso e iniciar o arco que termina em S6.

**Giver:** Oren Cal.

### Etapas

1. Encontrar um acampamento abandonado na Charneca.
2. Examinar três vestígios pessoais sem valor econômico.
3. Encontrar um Peregrino Calcinado em encontro roteirizado.
4. Vencer ou sobreviver ao encontro conforme a resolução normal.
5. Recuperar um fragmento de registro carbonizado.
6. Retornar a Oren.

### Fala-chave

**Oren Cal:**  
“Não preciso saber quem eram todos eles. Preciso apenas provar que foram pessoas antes de virarem aquilo que encontramos.”

### Efeitos

- cria **Peregrinos do Ocaso** no Códice;
- registra que grupos atravessaram a região antes do estado atual das rotas;
- não declara a natureza verdadeira dos Peregrinos Calcinados.

---

## 5.7 P3 — Sob Galhos Calcinados

**Objetivo narrativo:** abrir plenamente o Bosque e apresentar vestígios dos Antigos Asterianos.

**Giver:** Oren Cal.

### Etapas

1. Entrar no **Bosque Calcinado**.
2. Localizar três fragmentos de construção entre raízes e cinza.
3. Sobreviver a um encontro com ataque Preparado claramente telegrafado.
4. Examinar um fragmento entalhado de estrutura antiga.
5. Retornar a Oren com o registro.
6. Escolher 1 dos 3 Equipamentos Raros de Campanha.

### Encontro pedagógico

Usar **Cervo Escoriado** com **Carga do Ocaso** como ataque Preparado principal. `variant_roll=false`.

### Fala-chave

**Oren Cal:**  
“Pedra trabalhada debaixo de árvores queimadas. Isto estava aqui antes do Bosque ser como o conhecemos.”

### Efeitos

- descobre Bosque Calcinado;
- cria **Antigos Asterianos** no Códice;
- atualiza **Marcas na Fuligem** apenas com associação material/arquitetônica prudente;
- concede escolha Rara de P3.

---

## 5.8 S3 — Rastros sob os Galhos

**Status:** conteúdo novo aprovado formalmente nesta consolidação; substitui a lacuna textual do histórico não recuperado.

**Tipo:** Curta.

**Giver:** Alda Veyr.

**Objetivo narrativo:** mostrar que a ameaça do Bosque afeta rotas e suprimentos sem criar um novo arco de lore.

### Etapas

1. Examinar uma rota de suprimentos interrompida no Bosque.
2. Seguir três rastros entre os galhos.
3. Derrotar um **Cervo Escoriado**.
4. Verificar a carga abandonada.
5. Reportar a Alda.

`variant_roll=false`.

### Fala-chave

**Alda Veyr:**  
“Nem toda perda precisa esconder um mistério. Às vezes basta descobrir o que derrubou a carga antes que derrube a próxima.”

### Efeitos

- fornece evidência legítima de Habitat/combate do Cervo quando aplicável;
- não cria entrada nova de Códice;
- reforça o Bosque como zona de risco logístico.

---

## 5.9 P4 — Pedras que Ainda Vigiam

**Objetivo narrativo:** conduzir o jogador às Ruínas do Vigia e estabelecer que estruturas antigas ainda exercem função de guarda.

**Giver:** Alda Veyr.

### Etapas

1. Seguir o Caminho Ocidental a partir do Bosque.
2. Alcançar os limites das **Ruínas do Vigia**.
3. Derrotar um **Vigia Rachado** roteirizado.
4. Examinar duas estruturas de guarda.
5. Identificar uma rota segura de retorno.
6. Reportar a Alda e Oren.

### Fala-chave

**Alda Veyr:**  
“Uma muralha abandonada é pedra. Uma muralha que ainda impede passagem é outra coisa.”

**Oren Cal:**  
“Não sabemos quem lhes deu a ordem. Só sabemos que ela ainda produz consequências.”

### Efeitos

- descobre Ruínas do Vigia;
- atualiza Antigos Asterianos;
- registra a função de guarda sem afirmar consciência dos Vigias;
- libera Desbravar/Ruínas conforme gates normais.

---

## 5.10 S4 — Vigília sem Voz

**Status:** conteúdo novo aprovado formalmente nesta consolidação; substitui a lacuna textual do histórico não recuperado.

**Tipo:** Padrão.

**Giver:** Oren Cal.

**Objetivo narrativo:** aprofundar a lógica de patrulha dos Vigias sem antecipar O Primeiro Selo ou a Âncora.

### Etapas

1. Investigar três antigos pontos de vigia nas Ruínas.
2. Registrar a orientação das marcas de patrulha.
3. Derrotar um **Vigia Rachado**.
4. Encontrar um ponto onde a patrulha muda de direção sem obstáculo visível.
5. Examinar o local.
6. Retornar a Oren.

### Fala-chave

**Oren Cal:**  
“Eles não patrulham ao acaso. Isso não prova vontade. Prova que houve uma ordem bastante precisa para sobreviver a quem a deu.”

### Efeitos

- fornece evidência de Bestiário para Vigia Rachado quando válida;
- atualiza apenas contexto já conhecido das Ruínas;
- não cria **Ordens que Permanecem**, que continua vinculada às Galerias;
- não revela O Primeiro Selo.

---

## 5.11 S5 — A Luz que Não Aquece

**Objetivo narrativo:** transformar as luzes observadas anteriormente em um fenômeno regional reconhecido, ainda sem explicar sua causa.

**Giver:** Oren Cal.

### Etapas

1. Investigar um relato de luz nas Ruínas.
2. Examinar dois pontos onde existe luminosidade sem calor correspondente.
3. Sobreviver a um encontro elegível das Ruínas.
4. Registrar a direção e duração do fenômeno.
5. Retornar a Oren.

### Encontro

Preferência: **Mariposa de Brasa** ou **Custódio Sem Rosto**, conforme elegibilidade. `variant_roll=false`.

### Fala-chave

**Oren Cal:**  
“A primeira vez podia ser engano. A segunda, coincidência. Agora temos um padrão — e ainda não temos uma explicação.”

### Efeitos

- cria **Luzes do Ocaso**;
- associa o fenômeno a vestígios antigos apenas como correlação observada;
- não revela função de Âncora.

---

## 5.12 P5 — A Porta do Poente

**Objetivo narrativo:** localizar a passagem para o clímax regional e provar que algo nas Ruínas era protegido de forma deliberada.

**Giver:** Alda Veyr.

### Etapas

1. Seguir as estruturas de guarda mais profundas das Ruínas.
2. Encontrar a **Porta do Poente**.
3. Derrotar o **Custódio do Poente** em encontro roteirizado.
4. Examinar três elementos do mecanismo/estrutura ao redor da Porta.
5. Registrar o símbolo recorrente encontrado ali.
6. Reportar a Alda e Oren.

### Encontro

**Custódio do Poente · Elite · Nv.9**, sem Variante.

A vitória conta normalmente para Bestiário e para o marco importante configurado, se ainda não obtidos.

### Fala-chave

**Alda Veyr:**  
“Se puseram um guardião diante dessa porta, então o que existe depois dela importava mais do que estas ruínas inteiras.”

### Efeitos

- atualiza Ruínas do Vigia;
- aprofunda Antigos Asterianos;
- registra Porta do Poente;
- prepara P6;
- ainda não cria Âncora do Poente.

---

## 5.13 P6 — O Vigia Partido

**Objetivo narrativo:** concluir o arco regional, derrotar o Vigia Partido e revelar apenas o conhecimento permitido sobre a Âncora do Poente.

**Início:** automático quando P5 está concluída e o personagem alcança Nv.10.

### Etapas

1. Cruzar a Porta do Poente.
2. Entrar na **Câmara do Poente**.
3. Examinar a estrutura central sem conseguir interpretá-la integralmente.
4. Enfrentar **Vigia Partido**.
5. Derrotar o Chefe.
6. Examinar novamente a estrutura após a queda do Vigia.
7. Registrar o nome **Âncora do Poente**.
8. Retornar ao Refúgio ou concluir o relatório narrativo equivalente.
9. Escolher 1 dos 3 Equipamentos Épicos de Campanha.

### Fala-chave antes do Chefe

**Oren Cal, sobre o registro disponível:**  
“Se a leitura estiver correta, o nome é ‘Âncora’. Não sabemos o que ancorava. Não transforme um nome em resposta.”

### Revelação após a vitória

O personagem pode concluir legitimamente apenas que:

- a estrutura é chamada **Âncora do Poente**;
- o Vigia Partido a protegia;
- outras estruturas chamadas Âncoras existiram.

Não revelar:

- função real das Âncoras;
- estabilização do Véu;
- Convergência;
- Projeto Hemaris;
- Desvelados;
- Avesso.

### Efeitos

- descobre Câmara do Poente;
- cria **Âncora do Poente** no Códice;
- atualiza Antigos Asterianos e Ruínas;
- registra primeira vitória de Vigia Partido;
- concede uma única vez `1 Núcleo do Vigia Partido` como recompensa específica do encontro;
- revela a Receita `Eco do Vigia Partido`;
- conclui o marco regional da Campanha;
- concede escolha Épica de P6;
- permite a saída para Vales dos Enforcados quando o gate de nível também estiver satisfeito.

---

## 5.14 S6 — Onde os Nomes Terminaram

**Objetivo narrativo:** concluir o arco secundário iniciado em S2 sem transformar a Cripta em requisito obrigatório.

**Giver:** Oren Cal.

### Etapas

1. Revisar com Oren os fragmentos recuperados em S2.
2. Seguir três marcas de passagem dos Peregrinos nas Ruínas.
3. Examinar um abrigo abandonado.
4. Derrotar um **Custódio Sem Rosto**.
5. Encontrar o último registro legível da rota.
6. Retornar a Oren.

### Fala-chave

**Oren Cal:**  
“Não encontrei o nome de cada um. Talvez nunca encontremos. Mas sabemos onde a trilha deles deixou de ser uma estrada e virou apenas vestígio.”

### Efeitos

- atualiza **Peregrinos do Ocaso**;
- atualiza Ruínas do Vigia;
- não exige Cripta;
- não identifica O Sem-Nome;
- não revela uma causa definitiva para o destino dos Peregrinos.

---

## 5.15 Regras de encontros de Missão

Por padrão:

`allow_random_variant = false`

para todos os encontros roteirizados acima.

Eles:

- podem conceder XP/Bestiário quando explicitamente elegíveis pelas regras normais;
- não recebem perfil econômico de Caçada automaticamente;
- não consomem Vigor apenas por pertencerem a Missão;
- não podem ser rerrolados por reconnect;
- usam `encounter_id` persistente quando um combate é materializado.

Recompensas de Missão são concedidas somente uma vez.

**Exceção explícita de P1:** o encontro da Etapa 3 de Vozes na Estrada segue integralmente o perfil específico definido em §5.3: 0 XP de inimigo, 0 XP adicional de primeira observação e nenhuma recompensa econômica própria. Progresso legítimo de conhecimento do Bestiário permanece separado dessa recompensa.

---

## 5.16 Estado final das Missões

Com esta consolidação:

- S3 oficial passa a ser **Rastros sob os Galhos**;
- S4 oficial passa a ser **Vigília sem Voz**;
- as 12 Missões possuem título, requisitos, etapas, responsáveis, efeitos narrativos e recompensa implementável;
- não há dependência de NPC adicional;
- não existe bloco de Missão pendente para migração.

# 6. NPCs oficiais da vertical slice

A vertical slice das Terras do Ocaso utiliza **cinco NPCs nomeados persistentes**. Não são necessários NPCs adicionais para fechar a região.

## Alda Veyr

Coordena segurança, rotas e necessidades do Refúgio. Sua autoridade decorre da necessidade prática, não de título político formal estabelecido nesta região.

Funções de conteúdo:

- eixo da Campanha regional;
- segurança e progressão territorial;
- giver de P2, P4, P5 e S3;
- fechamento/relato de P1 e P6 quando aplicável.

## Oren Cal

Escriba dedicado a preservar relatos, nomes e inscrições. Suas traduções devem ser apresentadas como hipóteses enquanto não houver evidência suficiente.

Funções de conteúdo:

- Códice;
- investigação histórica;
- giver de S1, S2, P3, S4, S5 e S6;
- apoio narrativo em P1, P2, P4, P5 e P6.

## Torren Vhal

NPC de introdução contextual para:

- Ferreiro;
- Crafting;
- Desmontagem;
- Aprimoramento.

Não substitui o sistema de Ofícios do jogador e não executa crafting gratuito.

## Sila Renn

NPC de introdução contextual para:

- Alquimista;
- Cura;
- Purificação;
- Antídoto.

Não cria loja obrigatória nem fonte paralela de Consumíveis.

## Vael Orin

Ponto narrativo das Provações de Classe no Refúgio do Ocaso.

Abre acesso ao **Círculo da Cinza**; não concede Caminho diretamente e não executa uma segunda Provação para troca posterior.

### Fechamento documental

Qualquer personagem sem nome utilizado apenas em Flavor — sobrevivente, viajante, corpo encontrado, registro antigo — permanece figurante contextual e não entra no catálogo de NPCs persistentes.

Portanto, **não existe migração de NPC pendente para o v1.0.3 FINAL**.

# 7. Materiais regionais

## Materiais Básicos · Grau I

- **Ferro de Fuligem** · Metal
- **Couro Escoriado** · Couro
- **Erva Cinzenta** · Reagente
- **Resíduo do Ocaso** · Essência

## Recursos especiais

- Catalisador de Elite I
- Fragmento de Aprimoramento I
- Núcleo da Cripta do Ocaso
- Núcleo das Galerias do Vigia
- Núcleo do Vigia Partido

---

# 8. Criaturas de mundo aberto

## 8.1 Cão Cinéreo

**Categoria:** Comum  
**Arquétipo:** Predador  
**Faixa:** Nv.1–3

Artes:

- Mordida Faminta · `100% ATQ`
- Investida Curta · `110% ATQ`, CD2

Material temático conhecido: Couro Escoriado.

Variantes: Furioso, Ágil.

O Cão do tutorial possui `variant_roll=disabled` e recompensa fixa de `320 XP`.

## 8.2 Corvo de Fuligem

**Categoria:** Comum  
**Arquétipo:** Predador  
**Faixa:** Nv.1–4

- Bicada · `95% ATQ`
- Rasante · `90% ATQ` + `AGI −8% · 1T`, CD2

IA: **Rasante se disponível → caso contrário Bicada**. Não usa condição adicional por HP, Classe, Caminho ou build.

Variantes: Ágil, Furioso.

## 8.3 Peregrino Calcinado

**Categoria:** Comum  
**Arquétipo:** Equilibrado  
**Faixa:** Nv.2–5

- Golpe Desesperado · `105% ATQ`
- pode utilizar Defender conforme IA.

IA: **Golpe Desesperado → Golpe Desesperado → Defender → repetir**. Se Defender estiver devido mas for ilegal naquela oportunidade, usa Golpe Desesperado e mantém Defender como devido até a próxima oportunidade legal. Oportunidade perdida sem ação comprometida não avança o ciclo.

Materiais temáticos possíveis: Ferro de Fuligem ou Erva Cinzenta.

Variantes: Furioso, Resistente, Hemorrágico.

Sua natureza/origem não é confirmada como fato nesta região.

## 8.4 Aranha de Cinza

**Categoria:** Incomum  
**Perfil Bestiário:** RARE  
**Arquétipo:** Controlador  
**Faixa:** Nv.3–6

- Picada Tóxica · `80% ATQ` +1 Veneno, CD2
- Mordida · `95% ATQ`

Fraqueza: Queimadura `+10%`.

Resistência: Veneno `−10%`.

Variantes: Venenoso, Ágil.

## 8.5 Cervo Escoriado

**Categoria:** Comum  
**Arquétipo:** Bruto  
**Faixa:** Nv.4–7

- Chifrada · `105% ATQ`
- Carga do Ocaso · Preparada · `160% ATQ`

Variantes: Furioso, Resistente.

## 8.6 Carniçal de Fuligem

**Categoria:** Comum  
**Arquétipo:** Bruto  
**Faixa:** Nv.5–8

- Dilacerar · `90% ATQ` +1 Sangramento, CD2
- Arrancada · `125% ATQ`, CD3

Fraqueza: Queimadura `+10%`.

Resistência: Sangramento `−10%`.

Variantes: Hemorrágico, Resistente.

## 8.7 Mariposa de Brasa

**Categoria:** Incomum  
**Perfil Bestiário:** RARE  
**Arquétipo:** Conjurador  
**Faixa:** Nv.6–9

- Toque Incandescente · `80% ATQ` +1 Queimadura, CD2
- Clarão de Cinzas · `120% ATQ`, CD3

Resistência: Queimadura `−10%`.

Variantes: Ágil, Furioso.

## 8.8 Vigia Rachado

**Categoria:** Comum  
**Arquétipo:** Blindado  
**Faixa:** Nv.7–10

- Golpe de Pedra · `100% ATQ`
- Guarda Rachada · Barreira `70% ATQ`, CD3

Variantes: Resistente, Furioso.

## 8.9 Custódio Sem Rosto

**Categoria:** Incomum  
**Perfil Bestiário:** RARE  
**Arquétipo:** Controlador  
**Faixa:** Nv.8–10

- Marca do Peso · `90% ATQ` + `AGI −10% · 2T`, CD3
- Proteção Antiga · Barreira `80% ATQ`, CD3
- Impacto · `120% ATQ`, CD3

Variantes: Resistente, Ágil.

---

# 9. Elites regionais

Os três Elites de mundo aberto usam a Categoria global **Elite** e o Arquétipo indicado. Stats absolutos são derivados da Fonte Mestra; abaixo ficam fechados apenas kit, comportamento e função regional.

## 9.1 Alfa Cinéreo

**Habitat:** Estrada das Cinzas  
**Categoria:** Elite  
**Arquétipo:** Predador  
**Faixa:** Nv.3–4

Artes:

- **Mordida Alfa** · `100% ATQ`.
- **Investida Rasgante** · `90% ATQ` + `1 Sangramento`, CD2.
- **Salto Predatório** · ação Preparada · `160% ATQ`, CD4.

Comportamento:

Prioridade implementável completa:

1. se **Salto Predatório** estiver pendente, resolver a Ação Preparada pelas regras globais;
2. se o alvo possui `0 Sangramento` e **Investida Rasgante** está disponível, usar Investida Rasgante;
3. caso contrário, se **Salto Predatório** está disponível, preparar Salto Predatório;
4. caso contrário, se **Investida Rasgante** está disponível e o alvo permanece abaixo do cap global de Sangramento, usar Investida Rasgante;
5. caso contrário, usar **Mordida Alfa**.

Não reaplica Sangramento apenas para ultrapassar o máximo global. Salto Predatório sempre utiliza telegraph completo antes da resolução e não possui Hard CC.

Função: primeiro Elite regional e primeira demonstração de pressão predatória + DoT + ataque Preparado fora de Masmorra.

## 9.2 Viúva da Fuligem

**Habitat:** Bosque Calcinado  
**Categoria:** Elite  
**Arquétipo:** Controlador  
**Faixa:** Nv.6–7

Artes:

- **Picada da Viúva** · `80% ATQ` + `1 Veneno`, CD2.
- **Teia de Fuligem** · `75% ATQ` + `AGI −15% · 2T`, CD3.
- **Bote da Viúva** · `130% ATQ`, CD3; contra alvo com Veneno recebe `+10 p.p. PER` apenas nessa ação.

Comportamento:

- tenta estabelecer Veneno antes de Bote da Viúva;
- usa Teia de Fuligem para criar janela de pressão, não como loop permanente;
- **não utiliza Stun** ou outro Hard CC.

Função: Elite de controle leve; combina Veneno, perda de AGI e ataque forte sem retirar turnos do jogador.

## 9.3 Custódio do Poente

**Habitat:** Ruínas do Vigia  
**Categoria:** Elite  
**Arquétipo:** Blindado  
**Faixa:** Nv.9–10

Artes:

- **Golpe do Custódio** · `100% ATQ`.
- **Guarda do Poente** · Barreira `90% ATQ`, CD3.
- **Marca do Poente** · `85% ATQ` + `DEF −10% · 2T`, CD3.
- **Queda do Poente** · ação Preparada · `170% ATQ`, CD4.

Comportamento:

- não lança Guarda do Poente enquanto ainda possuir Barreira relevante da própria Arte;
- busca aplicar Marca do Poente antes de uma janela ofensiva, quando disponível;
- Queda do Poente sempre possui telegraph completo;
- não possui Cura nem Hard CC.

Função: último Elite de mundo aberto e ensaio direto das linguagens defensivas usadas pelos Vigias e pelo clímax regional.

# 10. Pools oficiais de Caçada

## 10.1 Seleção

A Caçada resolve:

`Local → criatura-base elegível → Variante opcional`

Pesos são relativos. Entradas inelegíveis são removidas antes do sorteio e os pesos restantes são normalizados.

Depois de desbloqueada, a criatura permanece no pool. O nível efetivo do encontro é:

Em Solo: `enemy_level = min(player_level, max_enemy_level)`. Em Grupo, nível, unlock mínimo e congelamento do encontro seguem integralmente a política global da Fonte Mestra v1.4.5.

sempre respeitando `player_level ≥ unlock_level`.

O `encounter_id` materializa criatura, nível, Variante e scaling; reconnect/abandono não rerrola o encontro.

## 10.2 Estrada das Cinzas

| Criatura | Categoria | Unlock | Máx. | Peso |
|---|---|---:|---:|---:|
| Cão Cinéreo | Comum | 1 | 3 | 34 |
| Corvo de Fuligem | Comum | 1 | 4 | 33 |
| Peregrino Calcinado | Comum | 2 | 5 | 30 |
| Alfa Cinéreo | Elite | 3 | 4 | 3 |

Com pool completo: `97%` Comuns / `3%` Elite.  
Chance de Variante: `8%`.

Caçada Manual fica disponível após P1, mesmo no Nv.1. Ronda fica disponível após a primeira vitória manual válida no Local.

## 10.3 Charneca da Fuligem

| Criatura | Categoria | Unlock | Máx. | Peso |
|---|---|---:|---:|---:|
| Peregrino Calcinado | Comum | 2 | 5 | 31 |
| Cão Cinéreo | Comum | 1 | 3 | 31 |
| Aranha de Cinza | Incomum | 3 | 6 | 18 |
| Cervo Escoriado | Comum | 4 | 7 | 20 |

Pool completo: `82%` Comuns / `18%` Incomum.  
Chance de Variante: `10%`.

Não há Elite natural neste pool.

## 10.4 Bosque Calcinado

| Criatura | Categoria | Unlock | Máx. | Peso |
|---|---|---:|---:|---:|
| Cervo Escoriado | Comum | 4 | 7 | 27 |
| Carniçal de Fuligem | Comum | 5 | 8 | 30 |
| Aranha de Cinza | Incomum | 3 | 6 | 20 |
| Mariposa de Brasa | Incomum | 6 | 9 | 20 |
| Viúva da Fuligem | Elite | 6 | 7 | 3 |

Pool completo: `57%` Comuns / `40%` Incomuns / `3%` Elite.  
Chance de Variante: `12%`.

## 10.5 Ruínas do Vigia

| Criatura | Categoria | Unlock | Máx. | Peso |
|---|---|---:|---:|---:|
| Carniçal de Fuligem | Comum | 5 | 8 | 25 |
| Vigia Rachado | Comum | 7 | 10 | 32 |
| Mariposa de Brasa | Incomum | 6 | 9 | 20 |
| Custódio Sem Rosto | Incomum | 8 | 10 | 20 |
| Custódio do Poente | Elite | 9 | 10 | 3 |

Pool completo: `57%` Comuns / `40%` Incomuns / `3%` Elite.  
Chance de Variante: `15%`.

## 10.6 Variantes elegíveis

| Criatura | Variantes |
|---|---|
| Cão Cinéreo | Furioso, Ágil |
| Corvo de Fuligem | Ágil, Furioso |
| Peregrino Calcinado | Furioso, Resistente, Hemorrágico |
| Aranha de Cinza | Venenoso, Ágil |
| Cervo Escoriado | Furioso, Resistente |
| Carniçal de Fuligem | Hemorrágico, Resistente |
| Mariposa de Brasa | Ágil, Furioso |
| Vigia Rachado | Resistente, Furioso |
| Custódio Sem Rosto | Resistente, Ágil |

Quando o roll de Variante ocorre, apenas as Variantes válidas daquela criatura participam, com peso igual. Máximo `1 Variante/encontro`.

Modificadores são os globais:

- Furioso: `ATQ +8% / DEF −8%`;
- Resistente: `DEF +10% / ATQ −6%`;
- Ágil: `AGI +12% / HP −7%`;
- Hemorrágico: habilita pacote de Sangramento e `ATQ −5%`;
- Venenoso: habilita pacote de Veneno e `HP −5%`.

Variante não altera Categoria, multiplicador-base de XP ou loot-base.

## 10.7 Ronda e encontros roteirizados

- Variante normal não interrompe Ronda.
- Alfa Cinéreo, Viúva da Fuligem e Custódio do Poente interrompem a Ronda **antes do combate automático**.
- O Elite materializado conserva o mesmo `encounter_id`; não há reroll ao reabrir o fluxo.
- Encontros de Missão, tutorial, Provação e Masmorra usam `allow_random_variant=false` por padrão.
- O Cão Cinéreo do tutorial nunca recebe Variante.
- Refúgio do Ocaso possui `normal_hunt_pool=none`.

# 11. Desbravar

## 11.1 Regras regionais

Desbravar está disponível em Estrada, Charneca, Bosque e Ruínas. Refúgio do Ocaso é Local seguro e não possui Desbravar ativo.

Aplicar integralmente a Fonte Mestra:

- recarga `5 min`;
- máximo `6 tentativas / Local / 60 min`;
- Solo;
- pool-base `8/22/15/25/10/20`;
- anti-repetição;
- proteção de até 3 tentativas **somente** quando um resultado se torna objetivo obrigatório de conteúdo ativo;
- `4 Vigor` apenas quando um resultado repetível realmente paga sua economia.

Pool-base:

| Categoria | Peso |
|---|---:|
| Grande Descoberta | 8 |
| Conhecimento | 22 |
| Narrativo | 15 |
| Combate | 25 |
| Pequeno Recurso | 10 |
| Atmosférico | 20 |

Se uma categoria não possuir resultado elegível, seu peso é redistribuído proporcionalmente entre as categorias elegíveis.

Resultados `Únicos` saem permanentemente do pool após resolução válida e permanecem concluídos através do Legado.

XP:

- Grande Descoberta única: `FixedPercentXP(reference_level, 8%)`;
- Descoberta Menor única: `FixedPercentXP(reference_level, 2,5%)`;
- Atmosférico/repetível contextual: `0 XP adicional de exploração`.

## 11.2 Estrada das Cinzas

### Grande Descoberta

**Marco dos Viajantes** · `explore.tdo.estrada.marco_viajantes`  
Único · ref Nv.2 · subpeso100.

Revela vestígios de antigas passagens e desbloqueia o Trecho **Memória dos Viajantes** em Estrada das Cinzas.

XP: `456`.

### Conhecimento

- **Rastros Cinéreos** · repetível · peso60. Pode fornecer evidência contextual de Habitat para Cão Cinéreo, Corvo de Fuligem ou Peregrino Calcinado.
- **Sinais à Margem** · repetível · peso40. Flavor/contexto já conhecido; não duplica Trechos.

### Narrativo

- **Luzes na Estrada** · Descoberta Menor · Único · ref Nv.2 · peso70. Registra luminosidade sem fogo evidente, sem concluir sua origem. XP `143`.
- **Vozes Levadas pelo Vento** · repetível · peso30 · sem estado permanente.

### Combate

Cão40 / Corvo35 / Peregrino25.  
Usa `encounter_id`; Variante usa a chance normal do Local.

### Pequeno Recurso

Ferro30 / Couro30 / Erva20 / Resíduo20.

### Atmosférico

Cinza sobre as Pegadas34 / Carroça sem Rodas33 / Fogueira Fria33.

## 11.3 Charneca da Fuligem

### Grandes Descobertas

- **Braseiro do Vento Morto** · `explore.tdo.charneca.braseiro` · Único · ref Nv.4 · peso50 · registra Braseiro permanente. XP `616`.
- **Entrada da Cripta do Ocaso** · `explore.tdo.charneca.cripta` · Único · ref Nv.4 · peso50 · elegível em Nv.4+ · revela a Masmorra e seu Caminho Conhecido. XP `616`.

### Conhecimento

- **Pedra Marcada** · Descoberta Menor · Único · ref Nv.4 · peso60 · atualiza Marcas na Fuligem sem definir autoria/finalidade. XP `193`.
- **Vestígios na Fuligem** · repetível · peso40 · evidência contextual de Aranha, Cervo ou Peregrino.

### Narrativo

- **Vento Morto** · Descoberta Menor · Único · ref Nv.4 · peso65 · observação ambiental, sem conclusão sobrenatural. XP `193`.
- **Cinzas que Não Assentam** · repetível · peso35.

### Combate

Peregrino35 / Aranha35 / Cervo30. Sem Elite genérico.

### Pequeno Recurso

Erva45 / Resíduo30 / Couro25.

### Atmosférico

Pedras Negras34 / Capim Coberto de Cinza33 / Silêncio sem Pássaros33.

## 11.4 Bosque Calcinado

### Grandes Descobertas

- **Braseiro dos Galhos Mortos** · `explore.tdo.bosque.braseiro` · Único · ref Nv.6 · peso50 · registra Braseiro permanente. XP `800`.
- **Estrutura Enterrada** · `explore.tdo.bosque.estrutura_enterrada` · Único · ref Nv.6 · peso50 · atualiza Bosque e Antigos Asterianos sem revelar função de Âncora. XP `800`.

### Conhecimento

- **Caminho Ocidental** · Descoberta Menor · Único · ref Nv.6 · peso60 · conhecimento geográfico; não ignora gate de Campanha para Ruínas. XP `250`.
- **Rastros entre os Galhos** · repetível · peso40 · evidência contextual de Cervo, Carniçal, Aranha ou Mariposa.

### Narrativo

Árvores que Ainda Fumegam55 / Cinzas sob as Raízes45 · repetíveis; sem conclusão cosmológica.

### Combate

Cervo25 / Carniçal30 / Aranha20 / Mariposa25. Viúva da Fuligem não entra no resultado genérico.

### Pequeno Recurso

Couro35 / Erva30 / Resíduo35.

### Atmosférico

Troncos Ocos34 / Brasa sob a Casca33 / Som entre os Galhos33.

## 11.5 Ruínas do Vigia

### Grandes Descobertas

- **Braseiro do Poente** · `explore.tdo.ruinas.braseiro` · Único · ref Nv.9 · peso50 · registra Braseiro permanente. XP `1.136`.
- **Entrada das Galerias do Vigia** · `explore.tdo.ruinas.galerias` · Único · ref Nv.9 · peso50 · elegível em Nv.8+ · revela a Masmorra e seu Caminho Conhecido. XP `1.136`.

### Conhecimento

- **Estruturas de Guarda** · Descoberta Menor · Único · ref Nv.9 · peso40 · registra arquitetura defensiva organizada. XP `355`.
- **Ocupação Posterior** · Descoberta Menor · Único · ref Nv.9 · peso40 · registra reutilização posterior sem identificar automaticamente seus responsáveis. XP `355`.
- **Marcas de Patrulha** · repetível · peso20 · contexto de deslocamento de Vigias/Custódios conhecidos.

### Narrativo

Passos onde Ninguém Passa50 / Pedra ainda em Vigília50 · repetíveis. Podem sugerir permanência de funções de guarda, mas não criam antecipadamente Ordens que Permanecem, O Primeiro Selo ou Âncora do Poente.

### Combate

Vigia Rachado35 / Custódio Sem Rosto30 / Carniçal20 / Mariposa15. Custódio do Poente não entra no resultado genérico.

### Pequeno Recurso

Ferro45 / Resíduo35 / Erva10 / Couro10.

### Atmosférico

Porta que Não Abre34 / Estátua sem Rosto33 / Eco sob a Pedra33. Não revela a Porta do Poente de P5 antes do gate narrativo.

## 11.6 Economia de Desbravar

**Pequeno Recurso:** `0,10 × C(nível aplicável) + 1 Material Básico`.

**Combate repetível:** `0,15 × C(nível aplicável) + 1 Material Básico +20% de chance de +1 Material Básico`.

Ambos consomem `4 Vigor` somente quando a economia é efetivamente concedida.

Combate usa `loot_profile=exploration_combat`, não a tabela completa de Saque da Caçada. O inimigo continua elegível à XP de combate e ao Bestiário pelas regras globais.

Com `Vigor <4`, a tentativa ainda pode ocorrer, mas não paga Coroas/Materiais repetíveis; nenhum Vigor parcial é consumido e XP repetível aplica o fator global de `25%` quando pertinente.

## 11.7 Anti-repetição

- resultado imediatamente anterior: `peso=0`;
- se o mesmo resultado apareceu entre os últimos 3 resultados válidos: `peso ×0,35`;
- a penalidade é aplicada ao resultado específico, não à categoria inteira.

## 11.8 Fechamento de exploração

Grandes Descobertas configuradas: `7`.  
Descobertas Menores configuradas: `6`.

XP total única:

- Grandes: `5.560 XP`;
- Menores: `1.489 XP`;
- total: `7.049 XP`, aproximadamente `7,21%` do requisito Nv.1→11.

Braseiros permanentes obtidos por Desbravar: Vento Morto, Galhos Mortos, Poente.  
Masmorras descobertas por Desbravar: Cripta do Ocaso, Galerias do Vigia.

# 12. Masmorra A — Cripta do Ocaso

**Faixa:** Nv.4–7  
**Entrada:** Charneca da Fuligem  
**Reference level Estável/Fraturada:** 6  
**Ruptura:** 60  
**Família:** `dungeon.tdo.cripta_ocaso`  
**Núcleo:** Núcleo da Cripta do Ocaso

Descoberta: Desbravar na Charneca.

## Encontro 1 — Vestíbulo Raspado

Nv.4 · `1× Profanador Calcinado` · Comum · Equilibrado.

- Ferramenta Quebrada · `100% ATQ`
- Golpe Impuro · `85% ATQ` + `DEF −10% · 2T`, CD3

## Encontro 2 — Ossário da Fuligem

Nv.5 · `1× Profanador Calcinado +1× Carniçal de Fuligem`.

Função: pressão de dois alvos, redução de DEF e Sangramento.

## Encontro 3 — Guardião das Lápides

Nv.6 · Elite · Bruto.

- Pancada de Pedra · `100% ATQ`
- Lápide Partida · `85% ATQ` +1 Sangramento, CD2
- Peso dos Mortos · Preparado · `165% ATQ`

## Braseiro de Masmorra

Se sorteado para a run, aparece depois do Encontro 3:

**Braseiro do Silêncio**.

Não integra a Travessia permanente.

## Encontro 4 — Câmara dos Nomes

Nv.6 · `2× Profanador Calcinado` + `3× Lápide sem Nome`.

Cada Lápide ativa concede aos Profanadores `DEF final +5%`.

Lápide:

- HP = 20% do HP-base de um Comum do mesmo nível;
- DEF = 80% da referência;
- 0 XP / 0 Saque / 0 Bestiário.

Encontro termina ao derrotar os Profanadores.

## Encontro 5 — O Sem-Nome

Nv.7 · Chefe de Masmorra · Bruto/Controlador.

- Golpe de Lápide · `100% ATQ`
- Marca Apagada · `90% ATQ` + `AGI −10% ·2T`, CD3
- Peso do Sepulcro · Preparado · `170% ATQ`
- Mãos dos Esquecidos · AoE `80% ATQ`, CD3

Fases:

1. `100→70%` · O Guardião do Túmulo
2. `70→35%` · O Peso dos Mortos
3. `≤35%` · Ninguém Restou

Não revelar sua identidade verdadeira.

## Códice

- Cripta do Ocaso
- Camadas de Sepultamento
- Câmara dos Nomes
- O Último Guardião
- Os Sem-Nome

---

# 13. Masmorra B — Galerias do Vigia

**Faixa:** Nv.8–10  
**Entrada:** Ruínas do Vigia  
**Reference level Estável/Fraturada:** 9  
**Ruptura:** 60  
**Família:** `dungeon.tdo.galerias_vigia`  
**Núcleo:** Núcleo das Galerias do Vigia

Descoberta: Desbravar nas Ruínas.

## Encontro 1 — Corredor de Guarda

Nv.8 · `1× Vigia Rachado`.

## Encontro 2 — Junção dos Vigias

Nv.8 · `1× Vigia Rachado +1× Custódio Sem Rosto`.

## Encontro 3 — Vigia Íntegro

Nv.9 · Elite · Blindado.

- Golpe de Guarda · `100% ATQ`
- Égide Íntegra · Barreira `80% ATQ`, CD3
- Marca de Restrição · `90% ATQ` + `AGI −10% ·2T`, CD3
- Queda da Guarda · Preparado · `160% ATQ`

## Braseiro de Masmorra

Se sorteado:

**Braseiro da Vigília**.

## Encontro 4 — Câmara dos Condutores

Nv.9 · `1× Preceptor Rachado` + `2× Condutor de Guarda`.

Preceptor: Elite · Controlador.

Condutor:

- HP = 30% do HP-base de Comum do mesmo nível;
- DEF = 100% da referência;
- cada ativo concede `DEF final +10%` ao Preceptor;
- 0 XP / 0 Saque / 0 Bestiário.

Preceptor:

- Impacto Regulador · `100% ATQ`
- Peso da Ordem · `90% ATQ` + `ATQ −10% ·2T`, CD3
- Restabelecer Conduto · 1 uso/encontro; restaura 1 Condutor destruído com 50% HP e consome a oportunidade ofensiva.

## Encontro 5 — Custódio do Primeiro Selo

Nv.10 · Chefe de Masmorra · Blindado/Controlador.

- Golpe Regulador · `100% ATQ`
- Marca de Contenção · `90% ATQ` + `AGI −10% ·2T`, CD3
- Égide do Selo · Barreira `8% HP Máximo`, CD4, máximo 2 usos
- Varredura do Selo · AoE `80% ATQ`, CD3
- Ruptura do Primeiro Selo · Preparado · `175% ATQ`

Fragmentos de Guarda:

- 2 objetos;
- HP = 25% do HP-base de Comum do nível de referência;
- cada ativo reduz dano recebido pelo Chefe em 5% final;
- 0 XP / 0 Saque / 0 Bestiário.

Fases:

1. `100→70%` · Protocolo de Guarda
2. aos `70%` · ativa 2 Fragmentos; Ordem de Contenção
3. aos `35%` · reconstitui uma única vez Fragmentos destruídos com 50% HP; Última Ordem; libera Ruptura do Primeiro Selo

## Códice

- Galerias do Vigia
- Rede de Defesa
- Câmara de Contenção
- Primeiro Selo
- Ordens que Permanecem

Não afirmar consciência das máquinas.

---

# 14. Chefe regional — Vigia Partido

**Nv.:** 10  
**Categoria:** Chefe normal  
**Arquétipo:** Equilibrado  
**Papel:** Chefe do P6 / clímax regional.

Stats-base utilizam diretamente o perfil global de Chefe normal:

`HP 220% / ATQ 110% / DEF 110% / AGI 100%`

antes dos demais modificadores globais pertinentes.

## 14.1 Artes

### Golpe do Vigia

`100% ATQ`.

### Marca da Sentinela

`90% ATQ` + `DEF −10% · 2T`, CD3.

### Égide Partida

Barreira `90% ATQ`, CD4.  
Máximo `2 usos por tentativa`.

### Varredura Fraturada

AoE `80% ATQ`, CD3.

### Peso da Ruína

`135% ATQ`, CD3.

### Queda do Ocaso

Ação Preparada · `185% ATQ`, CD5.  
Sempre possui telegraph completo e não aplica Hard CC.

## 14.2 Fases

### Fase I — A Sentinela

`100% → 70% HP`.

Usa Golpe do Vigia, Marca da Sentinela e Égide Partida. O objetivo é apresentar a lógica de guarda antes da ruptura do padrão.

### Fase II — A Fratura

`70% → 35% HP`.

Desbloqueia Varredura Fraturada e Peso da Ruína. Continua podendo usar as Artes da Fase I dentro de suas Recargas.

### Fase III — O Último Posto

`≤35% HP`.

Desbloqueia Queda do Ocaso. A primeira ocorrência sempre respeita o telegraph integral; a Arte segue CD5 e não pode ser usada em oportunidades consecutivas.

Não possui Cura, adds obrigatórios ou ciclo de Barreira infinito.

## 14.3 Recompensa e XP

P6 já concede sua recompensa fixa de Missão. Por isso o Vigia Partido **não concede EnemyXP genérica adicional**:

`campaign_boss_enemy_xp = 0`

A primeira vitória válida concede, uma única vez:

`1 Núcleo do Vigia Partido`

como recompensa específica do encontro, sem aplicar a tabela econômica repetível de Caçada/Boss.

A conclusão de P6 revela diretamente a Receita:

`recipe.tdo.vigia_partido.eco`

**Eco do Vigia Partido**.

Assim, a Receita não depende de um roll de 6% em um Chefe de campanha não-farmável. Se o jogador não estiver com Artífice ativo, a Receita permanece conhecida e poderá ser usada futuramente quando os requisitos forem cumpridos.

O Núcleo é consumível de procedência e não retorna na Desmontagem; a vertical slice garante um craft do Eco por primeira jornada. Fontes futuras adicionais para esse Núcleo precisam ser explicitamente configuradas.

## 14.4 Lore

A ligação com a **Âncora do Poente** só é estabelecida após o gate narrativo de P6.

Nesta região é permitido concluir apenas que:

- a estrutura é chamada Âncora do Poente;
- o Vigia Partido a protegia;
- outras Âncoras existiram.

Não revelar:

- verdadeira função cosmológica das Âncoras;
- estabilização do Véu;
- Convergência;
- sabotagem;
- Desvelados;
- Avesso.

# 15. Bestiário regional

Progressão player-facing:

`Observado → Conhecido → Estudado → Dominado`

Mapeamento técnico:

| Categoria de Combate | Perfil de Bestiário |
|---|---|
| Comum | COMMON |
| Incomum | RARE |
| Elite | ELITE |
| Chefe | BOSS |

`RARE` é nome técnico do perfil BKP e **não** renomeia uma criatura Incomum para “Rara” na UI.

## 15.1 Thresholds

- COMMON: Conhecido10 / Estudado30 + ≥2 categorias de evidência / Dominado60 + ≥3 categorias.
- RARE: Conhecido8 / Estudado22 / Dominado40 + ≥2 categorias de evidência.
- ELITE: Conhecido10 / Estudado25 / Dominado45 + vitória + mecânica/evidência especial configurada.
- BOSS: Conhecido10 / Estudado30 + ≥1 vitória + ≥2 mecânicas/fases; Dominado50 + `mastery_required` completo.

BKP e repetição usam a Fonte Mestra; esta seção apenas configura conteúdo regional.

## 15.2 Mundo aberto

### Cão Cinéreo

Habitat conhecido: Estrada das Cinzas / Charneca da Fuligem.  
Material conhecido: Couro Escoriado.  
Variantes: Furioso, Ágil.  
Sem fraqueza/resistência especial configurada.

### Corvo de Fuligem

Habitat conhecido: Estrada das Cinzas / Charneca da Fuligem.  
Variantes: Ágil, Furioso.  
Sem fraqueza/resistência especial configurada.

### Peregrino Calcinado

Habitat: Estrada / Charneca.  
Materiais conhecidos possíveis: Ferro de Fuligem, Erva Cinzenta.  
Variantes: Furioso, Resistente, Hemorrágico.  
Origem/natureza permanece não confirmada.

### Aranha de Cinza

Habitat: Charneca / Bosque.  
Materiais conhecidos possíveis: Erva Cinzenta, Resíduo do Ocaso.  
Fraqueza: Queimadura `+10%`.  
Resistência: Veneno `−10%`.  
Variantes: Venenoso, Ágil.

### Cervo Escoriado

Habitat: Charneca / Bosque.  
Variantes: Furioso, Resistente.  
Sem fraqueza/resistência especial.

### Carniçal de Fuligem

Habitat: Bosque / Ruínas.  
Fraqueza: Queimadura `+10%`.  
Resistência: Sangramento `−10%`.  
Variantes: Hemorrágico, Resistente.

### Mariposa de Brasa

Habitat: Bosque / Ruínas.  
Resistência: Queimadura `−10%`.  
Variantes: Ágil, Furioso.

### Vigia Rachado

Habitat: Ruínas do Vigia.  
Variantes: Resistente, Furioso.  
Sem fraqueza/resistência especial.

### Custódio Sem Rosto

Habitat: Ruínas do Vigia.  
Variantes: Resistente, Ágil.  
Sem fraqueza/resistência especial.

## 15.3 Elites de mundo aberto

### Alfa Cinéreo

Habitat: Estrada das Cinzas.  
Para Dominado, além do BKP Elite, exige primeira vitória, observar **Investida Rasgante** com Sangramento e testemunhar **Salto Predatório** preparado.

### Viúva da Fuligem

Habitat: Bosque Calcinado.  
Para Dominado, exige primeira vitória, evidência de Veneno e de redução de AGI, além do BKP Elite.

### Custódio do Poente

Habitat: Ruínas do Vigia.  
Para Dominado, exige primeira vitória, observar **Guarda do Poente** e **Queda do Poente**, além do BKP Elite.

## 15.4 Cripta do Ocaso

- **Profanador Calcinado** · Comum · Habitat: Cripta do Ocaso.
- **Guardião das Lápides** · Elite · Habitat: Cripta. Dominado exige vitória, observar Lápide Partida e Peso dos Mortos.
- **O Sem-Nome** · Boss · Habitat: Cripta.

`mastery_required` de O Sem-Nome:

1. ao menos 1 vitória;
2. alcançar a Fase III **Ninguém Restou**;
3. observar **Peso do Sepulcro**;
4. observar **Mãos dos Esquecidos**;
5. possuir Primeira Conclusão Estável da Cripta.

A identidade anterior do Chefe nunca é preenchida automaticamente.

## 15.5 Galerias do Vigia

- **Vigia Íntegro** · Elite · Habitat: Galerias. Dominado exige vitória, observar Égide Íntegra e Queda da Guarda.
- **Preceptor Rachado** · Elite · Habitat: Galerias. Dominado exige vitória, observar Condutores ativos e Restabelecer Conduto.
- **Custódio do Primeiro Selo** · Boss · Habitat: Galerias.

`mastery_required` do Custódio do Primeiro Selo:

1. ao menos 1 vitória;
2. alcançar Última Ordem;
3. observar Fragmentos de Guarda ativos;
4. observar **Ruptura do Primeiro Selo**;
5. possuir Primeira Conclusão Estável das Galerias.

## 15.6 Vigia Partido

**Perfil:** BOSS.

`mastery_required`:

1. concluir P6 e derrotá-lo;
2. alcançar **A Fratura**;
3. alcançar **O Último Posto**;
4. observar **Égide Partida**;
5. observar **Queda do Ocaso**.

## 15.7 Variantes

Subseções de Variante ficam completamente ausentes antes da primeira descoberta válida.

Tipos usados regionalmente:

- Furioso;
- Resistente;
- Ágil;
- Hemorrágico;
- Venenoso.

Dominar a criatura-base não revela Variante oculta. Bestiário pode mostrar materiais já conhecidos, mas nunca porcentagens de loot.

# 16. Códice regional

## Regiões e Locais

- Terras do Ocaso
- Estrada das Cinzas
- Refúgio do Ocaso
- Charneca da Fuligem
- Bosque Calcinado
- Ruínas do Vigia
- Câmara do Poente
- Cripta do Ocaso
- Galerias do Vigia

## Figuras

- Alda Veyr
- Oren Cal

## História e Acontecimentos

- Antigos Asterianos
- Peregrinos do Ocaso
- Os Sem-Nome
- Ordens que Permanecem

## Mistérios e Fenômenos

- Marcas na Fuligem
- Luzes do Ocaso
- O Primeiro Selo
- Âncora do Poente

## Ordem narrativa

- Prólogo: Terras / Estrada
- P1: Refúgio / Alda / Oren
- S1: atualização da Estrada
- P2: Charneca / Marcas
- S2: Peregrinos
- P3: Bosque / Antigos / atualização de Marcas
- Cripta: Os Sem-Nome por descoberta/progresso/clear
- P4: Ruínas / atualização de Antigos
- Galerias: Ordens que Permanecem / O Primeiro Selo após clear
- S5: Luzes do Ocaso
- P5: Ruínas / Antigos
- S6: Peregrinos / Ruínas
- P6: Câmara do Poente / Âncora do Poente

Ao final de P6, um jogador apenas de Campanha pode saber legitimamente:

- existiram Antigos Asterianos;
- as Ruínas tinham função de guarda;
- os Vigias protegiam estruturas;
- existe uma estrutura chamada Âncora do Poente;
- outras Âncoras existiram.

Não extrapolar a função real dessas estruturas.

---

# 17. Feitos e Cosméticos

## Feitos

1. **Cinzas na Estrada** · Exploração · concluir Prólogo · sem cosmético.
2. **Andarilho das Cinzas** · descobrir 5 Locais principais + 5 Braseiros · Título `Andarilho das Cinzas`.
3. **Sob a Superfície** · oculto · descobrir Cripta + Galerias · Banner `Profundezas do Ocaso`.
4. **A Última Guarda** · derrotar Vigia Partido pela primeira vez · Título `Vigia das Cinzas`.
5. **Silêncio entre os Nomes** · primeira conclusão Estável da Cripta · Emblema `Lápide Raspada`.
6. **A Ordem Interrompida** · primeira conclusão Estável das Galerias · Emblema `Selo Fraturado`.
7. **Cinzas Fraturadas** · concluir ambas em Fraturada · Moldura `Pedra Fraturada`.
8. **Caçador do Ocaso** · alcançar Dominado nas 9 criaturas-base · Título `Caçador do Ocaso`.
9. **Entre Aquilo que Caça** · oculto · 9 criaturas-base Dominadas + 3 Elites Dominados + Variante legitimamente descoberta/requerida por tipo · Aparência `Errante das Cinzas`.
10. **Testemunha dos Guardiões** · Estudado em Vigia Rachado, Custódio Sem Rosto, Custódio do Poente, Vigia Íntegro, Preceptor Rachado, Custódio do Primeiro Selo e Vigia Partido · Banner `Última Vigília`.
11. **Nomes sob a Cinza** · oculto · S2 + S6 + Cripta + primeira Estável + Trechos disponíveis de Os Sem-Nome · Emblema `Nome Apagado`.
12. **A Ordem Ainda Permanece** · oculto · primeira Estável Galerias + P6 + conteúdo disponível de Ordens/O Primeiro Selo/Âncora · Moldura `Vigília Antiga`.
13. **Terras do Ocaso** · P6 + Nv.10 + 5 Locais principais · Banner `Ocaso`.

## Catálogo cosmético regional

Títulos:

- Andarilho das Cinzas
- Vigia das Cinzas
- Caçador do Ocaso

Emblemas:

- Lápide Raspada
- Selo Fraturado
- Nome Apagado

Molduras:

- Pedra Fraturada
- Vigília Antiga

Banners:

- Profundezas do Ocaso
- Última Vigília
- Ocaso

Aparência:

- Errante das Cinzas

Total: **12 cosméticos permanentes** em 13 Feitos.

Não criar percentual público de “100% da região”, moeda de Feitos ou ranking regional.

---

# 18. Ofícios e crafting regional

Ofícios disponíveis no Refúgio:

- Ferreiro
- Artífice
- Alquimista
- Curteiro
- Joalheiro

## Catálogo oficial de Equipamentos regionais

### Ferreiro

- Arma do Caminhante · Principal
- Guarda do Caminhante · Secundária
- Arma Pesada do Caminhante · 2H
- Elmo de Fuligem · Cabeça
- Couraça de Fuligem · Torso
- Manoplas de Fuligem · Mãos
- Passos de Fuligem · Pés

### Curteiro

- Capuz das Cinzas · Cabeça
- Veste do Caminhante · Torso
- Luvas de Fuligem · Mãos
- Botas da Estrada · Pés

### Joalheiro

- Selo Enegrecido · Acessório
- Relicário de Cinzas · Artefato

Essas famílias usam Comum/Raro/Épico conforme requisito de Ofício.

## Equipamentos exclusivos de Campanha

P3:

- Véu do Bosque · Cabeça · Raro Nv.5
- Selo do Galho Morto · Acessório · Raro Nv.5
- Relicário da Cinza Verde · Artefato · Raro Nv.5

P6:

- Guarda do Último Posto · Torso · Épico Nv.10
- Selo do Poente · Acessório · Épico Nv.10
- Relicário da Âncora Velada · Artefato · Épico Nv.10

## Equipamentos de Receita especial

- Relicário dos Sem-Nome · Artefato · Raro
- Guarda do Primeiro Selo · Arma Secundária · Épico

### Fechamento documental

Este catálogo passa a ser o catálogo oficial de nomes individuais da vertical slice. Nomes eventualmente produzidos em rascunhos antigos e não recuperados **não fazem parte do cânone** até futura inclusão explícita por Conteúdo.

Não existe migração de Equipamento pendente para o v1.0.3 FINAL.

# 19. Runas Grau I

Famílias:

- Runa da Brasa · ATQ
- Runa da Pedra · DEF
- Runa do Caminhante · AGI
- Runa da Fresta · PER
- Runa do Presságio · CRIT
- Runa da Persistência · HP
- Runa do Desvio · Esquiva
- Runa da Guarda · Bloqueio

Potência Grau I:

| Atributo | Rara | Épica | Lendária |
|---|---:|---:|---:|
| HP | +0,35% | +0,45% | +0,55% |
| ATQ | +0,35% | +0,45% | +0,55% |
| DEF | +0,55% | +0,80% | +1,00% |
| AGI | +0,55% | +0,80% | +1,00% |
| PER | +0,25 p.p. | +0,50 p.p. | +0,50 p.p. |
| CRIT | +0,25 p.p. | +0,50 p.p. | +0,50 p.p. |
| Esquiva | +0,25 p.p. | +0,25 p.p. | +0,25 p.p. |
| Bloqueio | +0,25 p.p. | +0,50 p.p. | +0,50 p.p. |

Vertical slice normal: Rara no Ofício5; Épica no Ofício10.

---

# 20. Encantamentos Grau I

- Fio Cinéreo · ATQ
- Pele de Pedra · DEF
- Passo de Fuligem · AGI
- Marca da Fresta · PER
- Eco do Presságio · CRIT
- Sopro Persistente · HP
- Véu de Desvio · Esquiva
- Selo de Guarda · Bloqueio

Potência Grau I:

| Atributo | Raro | Épico | Lendário |
|---|---:|---:|---:|
| HP | +0,10% | +0,20% | +0,30% |
| ATQ | +0,10% | +0,20% | +0,30% |
| DEF | +0,20% | +0,40% | +0,55% |
| AGI | +0,20% | +0,40% | +0,55% |
| PER | +0,25 p.p. | +0,25 p.p. | +0,50 p.p. |
| CRIT | +0,25 p.p. | +0,25 p.p. | +0,50 p.p. |
| Esquiva | +0,25 p.p. | +0,25 p.p. | +0,25 p.p. |
| Bloqueio | +0,25 p.p. | +0,25 p.p. | +0,50 p.p. |

---

# 21. Alquimia regional

## Poção de Cura · Grau I

Ofício1.  
`3 Ervas Cinzentas +1 Resíduo do Ocaso +20 Coroas`.

Efeito: `22% HP Máximo`.

## Preparado de Purificação · Grau I

Ofício1.  
`2 Ervas Cinzentas +2 Resíduos do Ocaso +40 Coroas`.

Remove 1 efeito negativo removível.

## Antídoto Cinzento · Grau I

Ofício5.  
`4 Ervas Cinzentas +1 Resíduo do Ocaso +40 Coroas`.

Remove todos os stacks de um DoT removível selecionado.

## Poção de Vigor · Grau I

Ofício10.  
`6 Ervas Cinzentas +4 Resíduos do Ocaso +1 Catalisador de Elite I +120 Coroas`.

Efeito `+20 Vigor`; fora de combate; máximo 1/ciclo diário; exige Vigor≤80.

---

# 22. Receitas especiais regionais

## Relicário dos Sem-Nome

`recipe.tdo.cripta.relicario_sem_nome`

**Descoberta:** usa o roll global de Receita especial da Masmorra conforme a dificuldade da conclusão elegível; não é garantida na primeira conclusão.

Joalheiro5 · Artefato · Raro · Grau I · SW2.

Materiais:

- 10 Ferro de Fuligem
- 6 Resíduos do Ocaso
- 8 Fragmentos de Aprimoramento I
- 1 Núcleo da Cripta do Ocaso
- taxa normal do Craft Raro conforme item_level

Sem efeito exclusivo acima do budget Raro.

## Guarda do Primeiro Selo

`recipe.tdo.galerias.guarda_primeiro_selo`

**Descoberta:** usa o roll global de Receita especial da Masmorra conforme a dificuldade da conclusão elegível; não é garantida na primeira conclusão.

Ferreiro10 · Arma Secundária · Épico · Grau I · SW1.

Materiais:

- 7 Ferro de Fuligem
- 3 Resíduos do Ocaso
- 2 Catalisadores de Elite I
- 6 Fragmentos de Aprimoramento I
- 1 Núcleo das Galerias do Vigia
- taxa normal do Craft Épico conforme item_level

Sem proc exclusivo.

## Eco do Vigia Partido

`recipe.tdo.vigia_partido.eco`

**Descoberta:** revelação direta na conclusão de P6; não usa roll de Receita especial do Chefe de campanha.

Artífice10 · Encantamento Épico de PER · Grau I.

Materiais:

- 5 Resíduos do Ocaso
- 2 Ferros de Fuligem
- 1 Catalisador de Elite I
- 1 Núcleo do Vigia Partido
- 100 Coroas

Potência exatamente igual a um Encantamento Épico PER Grau I.

Núcleos não retornam na Desmontagem.

---

# 23. Provações de Classe · Nv.10

## 23.1 Desbloqueio e regras gerais

Ao alcançar Nv.10, o personagem recebe acesso à **única Provação da própria Classe** no **Círculo da Cinza**, conduzido narrativamente por Vael Orin no Refúgio do Ocaso.

O Círculo da Cinza:

- não é Local do Mapa;
- não é Masmorra, Caçada ou Profundeza;
- não gera Bestiário/Códice econômico;
- é uma instância exclusivamente pedagógica de Classe.

Requisitos:

- personagem Nv.10+;
- Classe válida;
- Refúgio do Ocaso conhecido;
- Provação ainda não concluída.

Não exige P6, Masmorra, Secundária, Vigor, pagamento ou Grupo.

Cada tentativa:

- é Solo;
- começa em `100% HP`;
- limpa estados temporários;
- não concede XP, Saque ou Coroas;
- não usa durabilidade nem Vigor;
- pode ser repetida imediatamente após falha, sem custo econômico.

A Provação usa apenas Ataque Básico, Defender e as Artes de Classe disponíveis até Nv.10 (`Nv.1/4/7/9`). Não antecipa Arte de Caminho.

Entidades de treinamento usam IDs `trial_entity.*`, não entram no Bestiário, não concedem Saque/XP e não contam para Feitos de criaturas.

## 23.2 Sentinela — Provação da Guarda

`trial.sentinela.guarda`

**Tema:** escolher qual impacto receber e quando transformar defesa em resposta.

### Etapa I — Suportar

Eco de Impacto executa três ações, sendo uma claramente Preparada e mais forte. A etapa recompensa Defender/Muralha Breve na ameaça correta.

### Etapa II — Abrir a Guarda

Eco Blindado possui DEF elevada. O objetivo pedagógico é utilizar **Quebra-Postura** e atacar durante a redução de DEF.

### Etapa III — Guardar e Revidar

Eco alterna ataque Preparado e janela ofensiva. O jogador deve combinar Defender/Muralha Breve, Retaliação e **Impacto Resoluto**.

Conclusão torna disponíveis:

- **Bastião · Proteção**;
- **Devastador · Pressão**.

## 23.3 Errante — Provação da Brecha

`trial.errante.brecha`

**Tema:** reconhecer e explorar uma abertura curta.

### Etapa I — Primeiro Corte

Aplicar **Ferida Profunda** e sustentar pressão com Sangramento.

### Etapa II — Passo entre Golpes

O inimigo prepara ataque forte. **Passo Velado** demonstra seu valor defensivo e a janela ofensiva subsequente; a etapa não depende de uma Esquiva RNG obrigatória para ser vencível.

### Etapa III — A Brecha

Eco entra periodicamente em estado Exposto, válido como efeito negativo. **Golpe Oportuno** deve ser utilizado em uma janela debilitada.

Caminhos:

- **Carrasco · Execução**;
- **Sabotador · Interferência**.

## 23.4 Vigia — Provação do Alvo

`trial.vigia.alvo`

**Tema:** observar, preparar e decidir onde o disparo importa.

### Etapa I — Marcar

Eco com DEF elevada; **Marca da Presa** cria a janela ofensiva.

### Etapa II — Três Disparos

Proteção de treinamento possui três pequenas camadas, uma removida por hit. **Saraivada** demonstra ataque múltiplo sem ser a única forma matemática de vencer.

### Etapa III — O Momento do Tiro

Eco alterna `Protegido → Exposto`; o jogador combina **Olho da Vigília** com Artes ofensivas na janela correta.

Caminhos:

- **Atirador · Precisão**;
- **Rastreador · Rastreamento**.

## 23.5 Tecelão — Provação dos Fios

`trial.tecelao.fios`

**Tema:** uma Arte preparar a próxima.

### Etapa I — Acender

Alvo principal + duas manifestações menores; **Chama Tecida** apresenta Queimadura e prepara sequência.

### Etapa II — Romper

Três Ecos menores tornam **Ruptura da Trama** naturalmente eficiente.

### Etapa III — Entrelaçar

Sequência de pressão exige alternância de Artes e uso de **Véu Entrelaçado**, respeitando a lógica real de Trama Encadeada: normal → Arte diferente fortalecida → normal.

Caminhos:

- **Conjurador · Ofensiva**;
- **Rúnico · Proteção**.

## 23.6 Oráculo — Provação do Presságio

`trial.oraculo.pressagio`

**Tema:** antecipar ameaça em vez de apenas reagir.

### Etapa I — O Sinal

**Sinal Funesto** demonstra redução de ATQ sobre um Eco ofensivo.

### Etapa II — Antes do Golpe

Ataque pesado anunciado pode ser respondido por **Vislumbre**, **Véu Premonitório** ou Defender; não existe solução única.

### Etapa III — O Futuro Possível

O Eco alterna janela ofensiva e preparação perigosa. O jogador decide quando usar **Ruína Predita** e quando preservar resposta defensiva.

Caminhos:

- **Agoureiro · Presságio**;
- **Invocador · Manifestações**.

As manifestações do Invocador continuam sendo efeitos do Oráculo, não pets/combatentes independentes.

## 23.7 Luminar — Provação da Luz

`trial.luminar.luz`

**Tema:** decidir entre sustentar e julgar.

### Etapa I — Sustentar

Um **Eco Aliado** possui HP, não possui turno ofensivo e existe somente na Provação. O Luminar deve impedir sua derrota com **Renovação** e/ou **Égide Solar**.

### Etapa II — Julgar

Eco inimigo possui recuperação periódica de treinamento; **Julgamento** demonstra redução de Cura recebida.

### Etapa III — Escolha de Prioridade

Luminar e Eco Aliado sofrem pressão simultânea. O jogador decide entre Cura, Barreira, ataque e redução de Cura.

Caminhos:

- **Guardião · Proteção**;
- **Inquisidor · Julgamento**.

## 23.8 Conclusão e escolha

Ao concluir:

`class_trial_completed = true`

permanente através do Legado.

Então:

- os dois Caminhos daquela Classe ficam permanentemente disponíveis;
- jogador escolhe o Caminho inicial sem custo;
- Passiva e modificadores inerentes do Caminho escolhido entram em vigor;
- primeira Arte de Caminho permanece bloqueada até Nv.12.

A performance nunca escolhe, recomenda ou bloqueia um Caminho.

Antes da confirmação, mostrar Preview do Caminho, Passiva e modificadores inerentes. Após confirmar, usar o fluxo normal de Personagem → Caminho definido na Fonte Visual/UI.

Troca posterior não repete a Provação: usa o sistema normal de troca em local apropriado e custo em Coroas definido pela Fonte Mestra.

Fluxo recomendado da primeira jornada:

`Nv.10 → segundo Ponto de Talento → Provação → escolha de Caminho → P6`

P6 não é requisito da Provação; essa ordem apenas permite experimentar a Passiva de Caminho no clímax regional.

# 24. XP regional e auditoria

XP total de Nv.1→11:

`97.800 XP`.

## 24.1 Fontes fixas

### Principais

`37.120 XP` ≈ `37,96%`.

### Secundárias

`21.965 XP` ≈ `22,46%`.

A meta sistêmica é referência de composição, não cap rígido; portanto não há nerf das Secundárias por `+0,46 p.p.`.

### Exploração única configurada

`7.049 XP` ≈ `7,21%`.

### Tutorial

Cão Cinéreo: `320 XP` fixos; não recebe separadamente o bônus genérico de primeira observação.

## 24.2 Cripta do Ocaso — primeira Estável

`reference_level=6`.

Conclusão Estável: `3.400 XP`.  
Primeira Conclusão `×1,60`: `5.440 XP`.

XP interna é calculada aplicando o fator de Masmorra `0,25` **antes do único round_10 final** de cada recompensa, sem arredondar EnemyXP normal intermediariamente.

Com a composição desta Fonte:

- Vestíbulo Raspado: `80`;
- Ossário: `80 +80`;
- Guardião das Lápides: `230`;
- Câmara dos Nomes: `90 +90`;
- O Sem-Nome: `550`.

Total interno: `1.200 XP`.

Primeira Estável completa, antes de outros marcos únicos:

`5.440 +1.200 = 6.640 XP`.

## 24.3 Galerias do Vigia — primeira Estável

`reference_level=9`.

Conclusão Estável: `4.050 XP`.  
Primeira Conclusão `×1,60`: `6.480 XP`.

XP interna:

- Corredor de Guarda: `100`;
- Junção dos Vigias: `100 +130`;
- Vigia Íntegro: `280`;
- Preceptor Rachado: `280`;
- Custódio do Primeiro Selo: `640`.

Total interno: `1.530 XP`.

Primeira Estável completa:

`8.010 XP`.

## 24.4 Bestiário

Primeira observação válida usa `1%` pelo sistema, com `FixedPercentXP`; o Cão do tutorial é exceção ao bônus de XP.

Marcos importantes de primeira vitória configurados nesta região:

- Alfa Cinéreo · ref Nv.3 · `198 XP`;
- Viúva da Fuligem · ref Nv.6 · `300 XP`;
- Custódio do Poente · ref Nv.9 · `426 XP`;
- O Sem-Nome · ref Nv.7 · `342 XP`;
- Custódio do Primeiro Selo · ref Nv.10 · `474 XP`;
- Vigia Partido · ref Nv.10 · `474 XP`.

Total desses seis marcos: `2.214 XP`.

O total efetivo de primeira observação depende do nível/referência válida de cada registro no momento em que ocorre e não é usado como gate obrigatório de progressão. Bestiário + marcos permanece dentro da banda-alvo quando o jogador interage naturalmente com a região.

## 24.5 Conversão de inimigos

`EnemyXPUnit(n) = XP_ref(n) / [20 × H(n)]`.

Valores aproximados de Comum equivalente, mesmo nível:

| Nv. | XP |
|---:|---:|
| 1 | 240 |
| 2 | 260 |
| 3 | 280 |
| 4 | 300 |
| 5 | 320 |
| 6 | 340 |
| 7 | 360 |
| 8 | 390 |
| 9 | 410 |
| 10 | 430 |

## 24.6 Gate inicial validado

Após Tutorial + P1:

`320 +2.400 =2.720 /4.800`.

Por isso Caçada Manual e Desbravar da Estrada liberam imediatamente após P1, ainda no Nv.1. Sem essa regra existiria hard lock.

## 24.7 Nv.10→11

P6 concede `14.220 /15.800 XP` (`90%`). Portanto S6 não se torna obrigatória: aproximadamente quatro Comuns Nv.10 equivalentes já cobrem a diferença em um cenário hipotético sem outra XP pendente.

## 24.8 Conclusão

Não existe hard lock conhecido de XP entre Nv.1 e Nv.11.

As duas Masmorras, todas as Secundárias, Bestiário Dominado e segredos permanecem opcionais para saída regional. A quantidade real de Caçadas/Ronda necessária deve ser validada por Alpha/Telemetria, não por nova regra estrutural.

# 25. Saída para Vales dos Enforcados

A saída da primeira jornada exige os gates estruturais globais:

- nível mínimo correspondente;
- marco de Campanha pertinente.

Terras do Ocaso não exige para saída:

- todas as Secundárias;
- ambas as Masmorras;
- Bestiário Dominado;
- todos os Feitos;
- todos os segredos.

---

# 26. Sincronização com a Fonte Visual/UI

A Fonte `ASTERION_UI_DECISOES_2026-09-22_FINAL_SYNC_v1.4.5_TDO_v1.0.3.md` é a autoridade player-facing vigente para a vertical slice e está sincronizada com a Fonte Mestra v1.4.5 e esta revisão regional.

As decisões gerais de interface já consolidadas — padrão de Missões, HUD de combate, Menu Principal, Braseiros, Códice, navegação, P1 e apresentação de Equipamentos/Runas — continuam válidas.

A camada específica de P1 — sinais da Estrada, transições, Alda/Oren, ativação do Braseiro do Refúgio, conclusão, recovery e reconnect — já está consolidada na Fonte Visual/UI vigente. Não existe pendência player-facing de P1 conhecida nesta revisão.

As faixas já sincronizadas permanecem:

- `Cripta do Ocaso · Nv.4–7`;
- `Galerias do Vigia · Nv.8–10`.

O estágio final player-facing do Bestiário permanece **Dominado**.

---

# 27. Estado de implementação

## Conteúdo regional fechado

Pode seguir para implementação utilizando conjuntamente as três fontes oficiais vigentes:

- tutorial/prólogo;
- 12 Missões completas;
- 5 NPCs persistentes;
- Locais e Braseiros;
- Caçadas e Ronda;
- Variantes;
- Desbravar;
- duas Masmorras;
- Chefes;
- Bestiário;
- Códice;
- Feitos;
- Provações;
- materiais;
- catálogo de Equipamentos;
- crafting Grau I;
- Runas e Encantamentos;
- Alquimia;
- Receitas especiais;
- XP repetível;
- gates Nv.1→11.

Não existe bloco regional conhecido aguardando migração textual.

---

# 28. Autoridade e manutenção

Este arquivo é a **Fonte oficial de Conteúdo das Terras do Ocaso v1.0.3 FINAL**.

Hierarquia:

1. Fonte Mestra estrutural vigente;
2. Fonte Visual/UI vigente;
3. esta Fonte regional para conteúdo específico das Terras do Ocaso.

Em conflito:

- sistema/regra global → Fonte Mestra;
- apresentação/UI → Fonte Visual/UI;
- nomes, encontros, missões, pools, lore permitido e conteúdo regional → esta Fonte.

Ajustes futuros oriundos de testes reais devem ser tratados como:

**Balanceamento / Telemetria / Patch de Conteúdo**

e não como reabertura informal deste arquivo.

As regras estruturais e semânticas globais necessárias estão incorporadas na Fonte Mestra v1.4.5. A camada de apresentação geral e a apresentação específica de P1 estão cobertas pela Fonte Visual/UI vigente.

Esta Fonte regional pode ser usada como autoridade de conteúdo e regras específicas das Terras do Ocaso em conjunto com a Fonte Mestra v1.4.5 e a sincronização Visual/UI vigente.

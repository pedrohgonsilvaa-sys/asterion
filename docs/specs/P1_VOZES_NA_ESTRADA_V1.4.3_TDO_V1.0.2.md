# Especificação de implementação — P1 Vozes na Estrada

> Autoridade: **GDD Estrutural v1.4.3 + Terras do Ocaso v1.0.2 FINAL + Visual/UI 2026-09-21 sincronizada com v1.4.3/TDO v1.0.2**.
>
> Estado de partida do repositório: `main@a0f154efe5e1e449748e4fb485edf6f74c756c4e`.
>
> Esta especificação começa exatamente na fronteira já implementada: Prólogo concluído, Feito `Cinzas na Estrada` registrado, P1 ativa na Etapa 1 e Menu Principal reconstruível.

## 1. Escopo

Implementar integralmente **P1 — Vozes na Estrada**, do primeiro clique de execução até a conclusão no Braseiro do Refúgio:

`Menu pós-Prólogo → Missões → Seguir pela Estrada → Pegadas → Sulcos → Cão Cinéreo roteirizado → Refúgio → Alda → Oren → Braseiro do Refúgio → conclusão → Menu pós-P1`.

O PR também deve criar somente a persistência genérica mínima exigida pelos efeitos permanentes e pela recompensa de P1:

- progresso detalhado e versionado de Missão;
- descoberta de Local;
- Entradas de Códice;
- desbloqueios de conteúdo;
- saldo de Coroas;
- stacks de Materiais vinculados;
- reward event/component idempotente;
- segundo Braseiro permanente.

Não implementar neste PR:

- Caçada Manual jogável;
- Ronda;
- Desbravar jogável;
- Inventário player-facing completo;
- Mercado, Crafting ou Armazém;
- P2;
- Bestiário completo;
- Travessia dos Braseiros completa;
- Consumíveis, salvo compatibilidade do renderer: o botão só existe se outro sistema realmente fornecer item elegível.

Os desbloqueios de Caçada Manual e Desbravar são **persistidos** na conclusão de P1, mas seus fluxos jogáveis ficam para o bloco seguinte.

## 2. Compatibilidade com o estado já persistido

O código atual cria P1 com:

- `quest_id = P1`;
- `status = active`;
- `step = 1`;
- `content_version = tdo-1.0.1`.

A nova autoridade é `tdo-1.0.2`.

A migration deste PR deve atualizar **somente** P1 antiga ainda no estado que o código atual é capaz de produzir:

- `quest_id = P1`;
- `status = active`;
- `step = 1`;
- nenhuma progressão jogável de P1 existente.

Esse estado pode migrar para `tdo-1.0.2` porque v1.0.2 preserva o início de P1 e apenas fecha sua execução.

Não reinterpretar silenciosamente qualquer P1 antiga que já possua `step > 1`, status concluído ou progresso incompatível. Se tal estado existir no momento da migration, falhar de forma explícita para revisão.

Combates do Prólogo já materializados continuam no próprio `ruleset_version`. O combate novo de P1 usa `gdd-1.4.3-baseline-1.0`.

## 3. Máquina autoritativa de P1

`Quest.step` continua representando as sete etapas oficiais.

A implementação pode usar JSONB/subestado equivalente, mas o comportamento precisa ser exatamente:

### Etapa 1

Estado: P1 ativa, Etapa 1 pendente.

Ação válida:

`[Seguir pela Estrada]`

Commit:

- validar P1 ativa, v1.0.2, step 1;
- avançar para step 2;
- incrementar versão de estado da Missão;
- renderizar Pegadas.

### Etapa 2

Subestado inicial:

- Pegadas não examinadas;
- Sulcos não examinados.

Primeiro `[Examinar]`:

- registra `p1.sign.pegadas_na_cinza` ou equivalente de forma idempotente;
- mantém step 2;
- incrementa versão;
- abre Sulcos.

Segundo `[Examinar]`:

- só é válido se Pegadas já estiver registrada;
- registra `p1.sign.sulcos_recentes`;
- conclui step 2;
- materializa imediatamente a tentativa da Etapa 3;
- não cria botão intermediário;
- entra diretamente no combate.

Sinais nunca podem ser repetidos para gerar uma segunda transição.

### Etapa 3

Condição de avanço: **vitória**.

Enquanto a tentativa está ativa:

- P1 permanece step 3;
- existe exatamente uma atividade Foreground ativa;
- reconnect retoma o mesmo `game_activity_id`, `encounter_id` e `combat_id`.

Derrota:

- atividade atual → `failed`;
- P1 continua ativa em step 3;
- registrar subestado de recovery/derrota suficiente para reconstruir a tela;
- HP do personagem → 100%;
- remover estados comuns persistentes, quando existirem;
- WorldState → Estrada das Cinzas;
- Vigor inalterado;
- nenhuma recompensa;
- nenhum efeito das etapas 4–7.

`[Retornar à Estrada]` após derrota:

- cria **nova** atividade/tentativa;
- novo `game_activity_id`;
- novo `encounter_id`;
- novo `combat_id`;
- mesmo Cão Cinéreo fixo Nv.1;
- Cão com HP integral;
- personagem com o estado pós-recovery;
- não reutiliza a tentativa derrotada.

Vitória:

- atividade atual → `completed`;
- persistir HP restante;
- P1 → step 4;
- não conceder XP de inimigo;
- não conceder bônus adicional de primeira observação;
- não conceder Saque, Coroas, Material ou Equipamento;
- Vigor permanece inalterado;
- renderizar diretamente a chegada ao Refúgio.

### Etapa 4

Tela: chegada ao Refúgio.

`[Entrar no Refúgio]`:

na mesma transação:

- registrar descoberta permanente do Local **Refúgio do Ocaso**;
- atualizar WorldState para `Terras do Ocaso · Refúgio do Ocaso`;
- avançar P1 para step 5;
- incrementar versão.

A descoberta ocorre antes de Alda.

### Etapa 5

`[Seguir a Indicação]`:

- registrar idempotentemente `Alda Veyr` em Códice → Figuras;
- avançar P1 para step 6;
- incrementar versão;
- abrir Oren.

### Etapa 6

`[Ir ao Braseiro]`:

- registrar idempotentemente `Oren Cal` em Códice → Figuras;
- avançar P1 para step 7;
- incrementar versão;
- abrir Braseiro do Refúgio.

### Etapa 7

`[Ativar Braseiro]`:

uma única transação lógica deve:

1. registrar o Braseiro do Refúgio como Braseiro permanente descoberto;
2. marcar P1 como `completed`;
3. conceder reward event de P1 uma única vez;
4. conceder `2.400 XP`;
5. conceder `120 Coroas`;
6. entregar `1 Ferro de Fuligem` vinculado;
7. entregar `1 Couro Escoriado` vinculado;
8. registrar unlock de Caçada Manual da Estrada;
9. registrar unlock de Desbravar da Estrada;
10. **não** registrar unlock de Ronda;
11. preservar HP atual;
12. preservar Vigor atual;
13. preservar WorldState no Refúgio.

Ativar Braseiro **não** chama a lógica de Descansar.

A resposta imediata ao commit é a tela de conclusão no próprio Braseiro.

Em nova sessão após P1 concluída, reconstruir Menu/navegação normal, não a Missão ativa.

## 4. Perfil do combate roteirizado

Conteúdo fixo:

- `content_id` estável equivalente a `p1_step3_scripted_dog`;
- Cão Cinéreo;
- Nv.1;
- Comum;
- Predador;
- Solo;
- sem Variante;
- sem pool de Caçada;
- sem máscara de tutorial.

Stats devem ser **derivados**, não hardcoded, usando a Baseline v1.0:

`enemy_stats(1, CATEGORY_COMMON, PREDATOR)`.

Valor de regressão esperado com a fórmula vigente:

- HP 406;
- ATQ 91;
- DEF 60;
- AGI 87.

Artes normais da Fonte Regional:

- **Mordida Faminta** · `100% ATQ`;
- **Investida Curta** · `110% ATQ`, CD2.

Para a cadência determinística já usada como comportamento normal do Cão, mapear:

`Mordida Faminta → Mordida Faminta → Investida Curta → repetir`.

A cadência satisfaz naturalmente CD2 da Investida.

O jogador começa com todas as ações normais que realmente possui:

- Ataque Básico;
- Defender, se válido;
- primeira Arte da Classe quando fora de Recarga;
- Consumível somente se um sistema real já fornecer Consumível elegível. Neste PR não criar Consumíveis fictícios.

Reutilizar o motor determinístico existente. Não duplicar fórmula de dano, iniciativa, raça, crítico, Defender ou Recarga.

## 5. Refatoração mínima do combate

O renderer atual está acoplado ao Prólogo e mostra `320 XP` em qualquer vitória.

Antes de reutilizá-lo em P1:

- tornar a apresentação de combate capaz de diferenciar contexto de Prólogo e contexto P1;
- o recibo `320 XP` permanece exclusivamente no tutorial;
- vitória de P1 não mostra `320 XP` nem qualquer recompensa do Cão;
- ao vencer P1, transicionar direto para a tela do Refúgio;
- preservar o cabeçalho `Turno X · Nome`, sem `⚔️`;
- preservar `👉 {emoji da Classe} Nome`;
- não mostrar nível nem Classe textual na HUD.

A entrada narrativa oficial de P1 aparece no primeiro render da tentativa e pode sair depois da primeira ação.

Não inventar novo texto de Registro de Combate se não for necessário. O log mecânico continua derivado dos eventos do backend.

## 6. Persistência nova mínima

A migration seguinte deve ser `20260921_0005` ou o próximo revision id livre equivalente.

### 6.1 Quest

Estender `quests` para suportar callbacks e subprogresso persistente:

- `state_version BIGINT NOT NULL DEFAULT 0`, check `>= 0`;
- `progress JSONB NOT NULL DEFAULT '{}'` ou estrutura relacional equivalente;
- default de `content_version` para novos registros passa a `tdo-1.0.2`.

A Fonte não obriga os nomes internos do JSON.

O progresso deve permitir no mínimo:

- Pegadas examinadas;
- Sulcos examinados;
- estado da Etapa 3: pronta/ativa/derrota resolvida;
- reconstrução determinística da tela atual.

### 6.2 Descoberta de Locais

Criar persistência genérica equivalente a:

`character_location_discoveries(character_id, location_id, discovered_at)`

com unique por personagem + Local.

IDs estáveis recomendados:

- `tdo.location.estrada_das_cinzas`;
- `tdo.location.refugio_do_ocaso`.

Backfill da Estrada para personagens que já possuem o Braseiro da Estrada/WorldState compatível.

### 6.3 Códice

Criar persistência genérica de Entrada conhecida, com unique por personagem + entrada.

IDs estáveis:

- `codex.figure.alda_veyr`;
- `codex.figure.oren_cal`.

Não implementar a UI completa do Códice neste PR.

### 6.4 Unlocks

Criar persistência genérica com unique por personagem + unlock.

IDs estáveis recomendados:

- `hunt_manual.estrada_das_cinzas`;
- `explore.estrada_das_cinzas`.

Não criar unlock de Ronda em P1.

### 6.5 Coroas

Adicionar saldo autoritativo de Coroas ao personagem ou wallet server-bound equivalente:

- inteiro de pelo menos 64 bits;
- default 0;
- nunca negativo.

Neste estágio, a solução mais simples compatível com o repositório é `Character.crowns BIGINT NOT NULL DEFAULT 0`, salvo se o PR introduzir uma wallet genérica igualmente segura.

### 6.6 Materiais no Inventário

P1 é a primeira fonte física de Materiais no repositório atual. Criar persistência mínima reutilizável para stacks de Inventário.

Requisitos:

- quantidade inteira;
- stack de Material máximo 999;
- propriedades econômicas iguais para fundir, inclusive bind;
- os dois Materiais de P1 são vinculados;
- unique/lock suficiente para impedir duplicação em retry/conclusão concorrente.

IDs recomendados:

- `material.tdo.ferro_de_fuligem`;
- `material.tdo.couro_escoriado`.

Bind técnico pode usar `bound` ou equivalente; player-facing é `Vinculado`.

O PR não precisa implementar telas completas de Inventário.

Como o repositório atual ainda não possui outras fontes de item e a migration começa sem stacks, a entrega de P1 cabe diretamente no Inventário. Mesmo assim, a modelagem não deve impedir a futura aplicação das capacidades 60/100/20 e Entregas Pendentes.

### 6.7 Reward event idempotente

Não reutilizar o `RewardGrant` do Prólogo como se ele representasse toda economia de P1; aquele modelo é histórico e específico do grant de XP ligado a `GameActivity`.

Criar reward event genérico equivalente a:

- um `reward_event_id` único para `P1 completion`;
- componentes individualmente registrados;
- unique que impeça segundo evento de conclusão para o mesmo personagem/fonte.

Componentes de P1:

- `xp = 2400`;
- `crowns = 120`;
- `material.tdo.ferro_de_fuligem = 1, bound`;
- `material.tdo.couro_escoriado = 1, bound`.

Conclusão da Missão e entrega física são conceitos separados, mas neste PR podem ser commitados na mesma transação porque todos os destinos necessários estão disponíveis.

Falha Telegram depois do commit não desfaz reward.

## 7. Navegação e UI que entram no PR

### 7.1 Menu

Antes de P1 concluída:

- manter `📜 Missão Principal · Vozes na Estrada`.

Depois de P1 concluída:

- Local = Refúgio do Ocaso;
- XP normal = `2.720 / 4.800`;
- P1 não aparece mais na HUD;
- não inventar P2 ativa/suspensa;
- HP/Vigor são os valores persistidos reais.

`WorldView.quest_title` precisa aceitar ausência de Missão Principal.

### 7.2 Aventura

Tornar funcional no mínimo:

`Menu → [Aventura] → Aventura → [Missões]`.

A raiz de Aventura segue a Fonte Visual vigente. Botões fora do escopo podem continuar sem mutação, mas não devem criar conteúdo fictício.

### 7.3 Missões

Implementar:

- raiz de Missões;
- `[Principal]`;
- detalhe completo de P1;
- `[Ver Objetivo]` como navegação sem mutação;
- `[← Missões]`;
- `[← Aventura]`.

Se P1 estiver concluída e nenhuma outra Missão estiver ativa, a raiz pode preservar somente cabeçalho/lore oficial e retorno, sem inventar missão.

### 7.4 Ver no Mapa

Mostrar `[Ver no Mapa]` somente quando o Local pertinente já for conhecido.

Para este PR basta uma visualização mínima do Mapa baseada nos Locais conhecidos:

- Estrada das Cinzas antes/durante P1;
- Refúgio somente depois do commit da Etapa 4.

Não implementar Travessia nem acesso a conteúdo futuro.

### 7.5 Telas contextuais

Copiar os textos oficiais da Fonte Visual/UI v1.4.3/TDO v1.0.2:

- Seguir pela Estrada;
- Pegadas;
- Sulcos;
- Derrota;
- Refúgio;
- Alda;
- Oren;
- Braseiro;
- conclusão.

Não reescrever lore.

Callbacks de mutação devem carregar identidade/versão suficiente para que mensagem antiga seja somente intenção do cliente.

## 8. Foreground e resolução de comandos

Criar um único caminho de resolução para `/start`, `/menu`, reconnect e troca de dispositivo.

Prioridade:

1. atividade Foreground ativa;
2. fronteira especial do primeiro Braseiro do Prólogo, se ainda aplicável;
3. navegação/missão persistida;
4. Menu normal.

Enquanto o combate de P1 estiver ativo:

- `/start` retoma o mesmo combate;
- `/menu` retoma o mesmo combate;
- nenhum handler pode abrir Menu por cima da atividade;
- callback de outra mensagem não cria segundo encounter.

Depois de derrota resolvida:

- não existe Foreground ativo;
- `/menu` abre Menu normal;
- P1 continua ativa;
- `Missões → Principal → Ver Objetivo` reconstrói a tela de Derrota;
- `Retornar à Estrada` cria a nova tentativa.

Não confiar em ordem de routers como regra de negócio. A prioridade deve ser derivada do backend.

## 9. Concorrência e locks

Toda mutação de P1 deve bloquear a identidade autoritativa do personagem e revalidar:

- ownership;
- servidor;
- P1 atual;
- `content_version`;
- step/subestado;
- `state_version`;
- Foreground existente;
- callback action permitido no estado atual.

Casos concorrentes:

- dois `Examinar` do mesmo sinal;
- dois `Examinar` do segundo sinal tentando criar combate;
- dois `Retornar à Estrada`;
- callback antigo de etapa anterior;
- dois `Entrar no Refúgio`;
- dois callbacks de Alda/Oren;
- dois `Ativar Braseiro`;
- `Ativar Braseiro` concorrendo com reconnect;
- Telegram falhando depois do commit.

Somente o primeiro commit lógico válido produz efeito; os demais reconstroem estado atual.

## 10. Descansar no Braseiro do Refúgio

Após P1 concluída, `[Descansar]`:

- exige personagem no Refúgio;
- exige Braseiro do Refúgio descoberto;
- não pode existir Foreground incompatível;
- restaura HP a 100%;
- remove estados comuns persistentes quando houver;
- não altera Vigor;
- não altera XP;
- não repete recompensa;
- não reabre P1.

Callback antigo de Descansar não deve permitir cura remota se o personagem futuramente não estiver mais no Refúgio.

## 11. Bestiário

Não implementar o sistema completo do Bestiário neste PR.

Regras obrigatórias:

- encontro de P1 concede **0 XP adicional** de primeira observação;
- nunca transformar P1 em nova fonte do bônus genérico de primeira observação;
- não apagar conhecimento do Prólogo;
- se uma futura camada de Bestiário já estiver presente durante integração, o encontro pode registrar apenas evidência legitimamente elegível sem XP adicional.

Ausência do Bestiário completo não pode bloquear P1.

## 12. Testes obrigatórios

Usar PostgreSQL real no CI. Nenhum teste do novo bloco deve depender só de SQLite/mocks.

Cobrir no mínimo:

1. migration atualiza P1 `tdo-1.0.1 step1 active` para `tdo-1.0.2`;
2. migration recusa estado antigo de P1 incompatível em vez de reinterpretar;
3. backfill de descoberta da Estrada é idempotente;
4. `/start` pós-Prólogo mostra Menu com P1;
5. Menu → Aventura → Missões → Principal funciona;
6. detalhe mostra recompensa correta;
7. `Ver Objetivo` não muta estado;
8. Etapa 1 avança uma vez;
9. Pegadas avançam uma vez;
10. Sulcos exigem Pegadas;
11. segundo sinal cria exatamente uma tentativa;
12. falha Telegram após criação do combate retoma o mesmo encounter;
13. Cão P1 deriva 406/91/60/87;
14. Cão usa Mordida Faminta 100% e Investida Curta 110% CD2;
15. P1 não possui Tutorial/máscara pedagógica;
16. jogador possui ações normais válidas desde a primeira oportunidade;
17. combate P1 não mostra recibo de 320 XP;
18. vitória do Cão P1 não altera XP/Coroas/Materiais/Vigor;
19. derrota restaura HP a 100% e mantém Vigor;
20. derrota mantém P1 step3;
21. `/menu` após derrota abre Menu;
22. `Ver Objetivo` após derrota reconstrói recovery;
23. retry cria novos activity/encounter/combat IDs;
24. retry não rerrola criatura;
25. reconnect em tentativa ativa mantém IDs;
26. vitória avança para Refúgio sem recompensa de inimigo;
27. Refúgio não é conhecido antes de `Entrar no Refúgio`;
28. `Entrar no Refúgio` descobre Local e atualiza WorldState uma vez;
29. Alda entra no Códice uma vez;
30. Oren entra no Códice uma vez;
31. Braseiro do Refúgio é registrado uma vez;
32. Ativar Braseiro não cura;
33. conclusão deixa quest `completed`;
34. conclusão concede XP exatamente uma vez;
35. conclusão concede 120 Coroas exatamente uma vez;
36. conclusão entrega os dois stacks vinculados exatamente uma vez;
37. conclusão desbloqueia Caçada Manual e Desbravar;
38. conclusão não desbloqueia Ronda;
39. XP final normal é 2720/4800;
40. Menu pós-P1 está no Refúgio e omite P1;
41. Menu pós-P1 não inventa P2;
42. Descansar no Refúgio cura HP e preserva Vigor;
43. dois `Ativar Braseiro` concorrentes não duplicam reward;
44. callbacks antigos não retrocedem step nem duplicam descoberta/Códice;
45. falha Telegram depois do commit final recupera estado concluído;
46. outro dispositivo observa o mesmo progresso;
47. todas as 30 combinações Classe × Raça conseguem materializar o encontro sem regra excepcional;
48. executar uma validação determinística de segurança das 30 combinações; se alguma combinação ficar matematicamente sem caminho de vitória sob as ações normais disponíveis, **não alterar balanceamento no PR**: parar e reportar;
49. `alembic check`;
50. migration upgrade/downgrade/upgrade quando seguro;
51. `ruff check .`;
52. pytest completo com PostgreSQL real e zero skips;
53. `git diff --check`.

## 13. Downgrade

Downgrade deve ser conservador.

Se já existir progresso novo de P1 v1.0.2, recompensa, descoberta do Refúgio, Códice, unlocks, stacks ou Braseiro do Refúgio, não fingir que o schema antigo consegue representar tudo.

Nessa situação, downgrade deve falhar explicitamente em vez de apagar/rebaixar estado silenciosamente.

## 14. Limite do PR

Pare quando:

- P1 estiver jogável integralmente até a conclusão;
- estado pós-P1 estiver persistente/reconstruível;
- reward e desbloqueios estiverem registrados;
- Descansar no Braseiro do Refúgio funcionar;
- Menu pós-P1 estiver correto.

Não iniciar P2, Caçada, Ronda ou Desbravar jogável no mesmo PR.

## 15. Critério de aceite

O PR só está pronto para review quando:

- comportamento player-facing corresponde à seção 46 da Fonte Visual/UI vigente;
- conteúdo corresponde à seção 5.3 de Terras do Ocaso v1.0.2;
- nenhuma recompensa extra aparece no Cão de P1;
- nenhuma migração reinterpreta silenciosamente estado histórico;
- todas as mutações são idempotentes;
- CI completo está verde.


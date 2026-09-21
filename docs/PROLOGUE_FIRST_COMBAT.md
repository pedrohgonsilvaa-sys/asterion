# Primeiro combate persistente do prólogo

Este bloco foi implementado sob `gdd-1.4.2-baseline-1.0` e cobre somente
`Seguir pela Estrada → Cão Cinéreo → vitória → estado pronto para o primeiro Braseiro`.
A Fonte vigente passou a ser **GDD v1.4.3 + Terras do Ocaso v1.0.2 FINAL**.
Combates já instanciados em v1.4.2 devem continuar reprodutíveis no ruleset original;
novas transições seguras passam a adotar v1.4.3 conforme a especificação seguinte.

## Domínio e determinismo

`domain/combat_math.py` contém a curva `G(n)`, composição de atributos, redução
por DEF, dano e o gerador determinístico. `domain/combat.py` executa um duelo a
partir de snapshots puros; não importa aiogram nem SQLAlchemy.
`domain/prologue.py` descreve o conteúdo específico do encontro como dados:
primeiras Artes, Cão, respostas pedagógicas e ciclo de IA.

O Cão usa a composição genérica sem arredondamento intermediário:

`K(1) × Comum × Predador × Variante(1,00) × prologue_first_combat × Solo(1,00)`

e produz `244 HP / 50 ATQ / 45 DEF / 56 AGI`. CD2 avança por oportunidades do
proprietário: uso em N bloqueia N+1 e volta em N+2.

O RNG usa SHA-256 com `combat_id`, cursor persistido, propósito e tentativa. Não
usa `random`, `hash()`, relógio ou ordem do processo. Críticos, desempate de
iniciativa e eventual duração racial do Velado podem ser reproduzidos a partir do
snapshot. A IA do Cão não usa RNG.

## Persistência e concorrência

A migration `20260920_0003` adiciona progressão mínima ao personagem e cria:

- `game_activities`: atividade Foreground, conteúdo, status, `state_version` e
  `ruleset_version`;
- `encounters`: identidade estável do encontro;
- `combats`: identidade estável e snapshot JSONB lossless do combate;
- `reward_grants`: concessão auditável e única de XP por atividade.

Um índice parcial único permite somente uma atividade Foreground `active` por
personagem. Outro índice impede uma segunda ocorrência de
`prologue_first_combat`, inclusive depois da conclusão. A conta e o personagem
são bloqueados durante cada comando, serializando dispositivos concorrentes.
Callbacks carregam somente `game_activity_id`, `state_version` e intenção; todo o
restante é recuperado e validado no PostgreSQL.

A migration converte explicitamente personagens ainda em
`cinzas_na_estrada:intro` de v1.4.1 para v1.4.2 e inicializa Nv.1, XP 0 e HP
autoritativo. Novos personagens já são criados sob v1.4.2.
O downgrade de schema não rebaixa esse marcador de Fonte: uma versão de ruleset
adotada por dado persistente nunca é silenciosamente reinterpretada.

Ao vencer, a mesma transação persiste HP restante, conclui atividade, grava o
grant e soma exatamente 320 XP. A chave primária do grant e o lock impedem nova
concessão por retry, reconnect ou dois dispositivos. Não existem campos ou grants
de Vigor, Coroas, Material, Saque ou bônus de Bestiário neste bloco.

## Recuperação e Telegram

`/start` consulta primeiro a atividade e o estado mundial do personagem. Durante o
combate, renderiza diretamente o snapshot atual. Depois da vitória, o backend
reconstrói o **Braseiro da Estrada** já descoberto, sem reiniciar o Cão ou conceder
XP novamente. Log, HP, barras, cooldowns e ações disponíveis vêm do backend. A
mídia continua opcional e usa o fallback texto + inline keyboard. Falha ao editar
ou enviar uma mensagem ocorre depois do commit e não desfaz o jogo.

O estágio pós-vitória é
`cinzas_na_estrada:ready_for_first_brazier`. Nessa fronteira já existem o Braseiro
da Estrada e o `WorldState` de **Terras do Ocaso · Estrada das Cinzas**. O Feito do
Prólogo e P1 ainda não existem nesse instante. `[Descansar]` encerra o Prólogo e
transiciona autoritativamente para `menu:ready`.

A Fonte não define neste bloco uma interface ou recuperação narrativa para uma
eventual derrota. O motor persiste `result=defeat` e encerra a atividade de forma
segura, sem inventar texto, botão ou regra de retry; essa continuação fica
deliberadamente pendente de Fonte.

## Limite econômico

Os 320 XP permanecem um grant fixo de story content para o tutorial. A Fonte
Mestra v1.4.3 encerrou a antiga reabertura da conversão global de XP de inimigos;
este documento histórico não deve ser usado como autoridade para fórmulas de XP
repetível. Para conteúdo novo, consultar a v1.4.3 e Terras do Ocaso v1.0.2.
## Revisão de apresentação e cura

O passo pedagógico da primeira Arte permanece dentro da HUD: durante `tutorial_stage == art`, a tela mostra o nome da Arte em negrito, `Arte de Classe`, o coeficiente de dano, a recarga `2` e, para Sinal Funesto, o efeito de redução de ATQ por 2T. O botão usa somente o nome limpo da Arte. Depois do uso válido, essas linhas desaparecem.

O Registro de Combate usa linhas curtas em linguagem natural, com nomes e Artes em negrito e números mecânicos em monoespaçado. Todo conteúdo dinâmico é escapado antes do parse HTML do Telegram.

Vampirismo do Hemário é cura: calcula dano direto real, aplica o limite de 3% do HP Máximo e o HP faltante, então usa `floor`, com mínimo zero.

A barra de HP usa blocos preenchidos e `⬜` para a parte ausente. Os limiares oficiais para escolher entre 🟩, 🟨 e 🟥 ainda não foram definidos pela Fonte Visual/Balanceamento; a seleção dinâmica permanece pendente e não é inferida neste bloco.
## Fronteira v1.4.3

Após a vitória do primeiro combate, a mesma transação encerra o combate, preserva o HP restante, mantém o grant único de `320 XP`, registra o **Braseiro da Estrada** e o `WorldState` de **Terras do Ocaso · Estrada das Cinzas**, e coloca o personagem em `cinzas_na_estrada:ready_for_first_brazier`. **Não** registra ainda o Feito do Prólogo nem P1. O personagem adota `gdd-1.4.3-baseline-1.0` somente nessa fronteira segura; snapshots de combates v1.4.2 continuam identificados pelo ruleset original.

`Descansar` aceita `cinzas_na_estrada:ready_for_first_brazier`, restaura HP sem alterar Vigor e, na mesma transação lógica, conclui o Prólogo, registra uma única vez `feat.tdo.cinzas_na_estrada`, cria **P1 — Vozes na Estrada** ativa na Etapa 1 e transiciona para `menu:ready`. A implementação desse bloco foi criada quando a autoridade regional era TDO v1.0.1, por isso o registro histórico de Quest usa `content_version = tdo-1.0.1`.

A autoridade vigente passou a ser **TDO v1.0.2 + Visual/UI 2026-09-21 sincronizada com TDO v1.0.2**. A futura implementação jogável de P1 deve tratar a atualização de versão de conteúdo de forma explícita e segura, sem reescrever progresso já materializado silenciosamente. Como o `main` atual só cria P1 na Etapa 1 e ainda não implementa suas etapas jogáveis, essa migração deve ser resolvida no próximo bloco técnico antes de avançar a missão.

Depois de `menu:ready`, callbacks antigos de Descansar são no-op e apenas reconstroem o Menu. O Menu exige Braseiro, WorldState, Feito e Quest P1 persistidos; não usa defaults para inventar conteúdo. HP permanece Decimal e as barras de HP/Vigor são derivadas do estado autoritativo.

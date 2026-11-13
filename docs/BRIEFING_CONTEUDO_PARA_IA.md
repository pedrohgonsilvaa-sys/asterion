# Asterion: pedido de conteúdo para uma IA parceira (2026-11-12)

## Como usar

1. Abra uma conversa nova na outra IA.
2. Anexe estes arquivos: este briefing e `ASTERION_BIBLIA_CANONICA_v4_0_7.md` (a Bíblia é a fonte de Lore; sem ela a IA inventa).
3. Cole o "Pedido" abaixo e converse. Peça um bloco por vez (Eventos, depois Provações, depois Rotas).
4. Traga o resultado de volta em Markdown, no formato da seção "Formato de entrega".

## Pedido (cole na outra IA)

> Você é roteirista de um RPG dark fantasy para Telegram chamado Asterion. Anexei a Bíblia Canônica v4.0.7: ela manda em Lore, nomes, NPCs e limites. Não contradiga a Bíblia e não crie mecânica nova. Se uma ideia precisar de regra que não existe, escreva como pergunta no fim, não como conteúdo.
>
> Preciso de três catálogos. Textos curtos, em português, tom sombrio e contido (o jogo roda em mensagens de Telegram). Para cada catálogo, primeiro me proponha uma lista de títulos e uma frase de ideia para cada um, para eu escolher. Só depois escreva os escolhidos por completo.

## O que o jogo já decidiu (não reabrir)

**Mundo:** 6 Regiões; níveis 1 a 60; 6 Classes. A Bíblia dá nomes, Regiões, criaturas e NPCs.

**Criaturas:** os números (vida, ataque etc.) não são escritos à mão. O roteirista escolhe o **perfil** (Bruto, Equilibrado, Ágil…) e **3 a 5 ações descritas em palavras**. A engenharia calcula o resto pela categoria (Elite ou Chefe) e pelo nível.

### 1. Eventos Públicos (6 sugeridos, 1 por Região)

Regras fixas: 3 fases; 1 Chefe por fase, cada um com a própria barra de vida; 5 minutos de reunião antes da Fase 1; a fase só avança quando a vida zera.

Por Evento entregar:

- `event_id` (minúsculo, ex.: `evt_tdo_cerco_das_cinzas`), nome, Região, nível de referência (1 a 60);
- Fases 1, 2 e 3: Chefe (nome, perfil, 3 a 5 ações) e 1 a 3 frases de flavor;
- texto de conclusão (ao vencer a Fase 3);
- Sintonizado? (sim/não) e nível mínimo de entrada, se diferente do padrão.

### 2. Provações do Juramento (4 a 6)

Regras fixas: 3 combates seguidos, na ordem **Elite, Elite, Chefe**; a vida continua entre os combates.

Por Provação entregar:

- `trial_id` (ex.: `jur_guardioes_do_limiar`) e nome;
- Combate 1 (Elite), 2 (Elite) e 3 (Chefe): criatura (nome, perfil, ações) e flavor de 1 a 3 frases. A criatura pode ser nova ou reaproveitar uma do Bestiário da Bíblia (dizer qual);
- texto de conclusão.

### 3. Rotas da Expedição (4 a 6)

Regras fixas: 3 estágios de 24 horas; cada estágio tem **exatamente 3 opções**: uma favorável, uma neutra e uma ruim. A pista de qual é qual fica no texto do estágio, sem ser óbvia.

Por Rota entregar:

- `route_id` (ex.: `exp_trilha_dos_vales`) e nome;
- Estágios 1, 2 e 3: flavor com a pista (2 a 4 frases) e as 3 opções, cada uma com rótulo curto (cabe num botão do Telegram) e a qualidade (favorável, neutra ou ruim);
- texto de retorno (ao fim do estágio 3).

## Formato de entrega

Um arquivo Markdown por bloco (Eventos, Provações, Rotas), com uma seção por item e os campos acima. A engenharia transcreve para os catálogos, gera as criaturas pela fórmula e roda os testes.

## Perguntas para discutir com a IA (e decidir você)

- Quais Regiões merecem o Evento mais marcante no Beta?
- As Provações e Rotas devem contar uma história contínua entre si ou ser episódios soltos?
- Qual o tom: horror contido, melancolia ou ameaça aberta?
- Quais criaturas do Bestiário podem reaparecer como Elite?

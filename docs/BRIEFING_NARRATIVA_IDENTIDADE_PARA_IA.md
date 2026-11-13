# Asterion: pedido de narrativa por identidade, NPCs e relacionamento (2026-11-12)

## Como usar

1. Abra uma conversa nova na outra IA.
2. Anexe: este briefing, `ASTERION_BIBLIA_CANONICA_v4_0_7.md` (fonte de Lore, nomes e NPCs) e, se tiver, `ASTERION_DECISAO_FINAL_MISSOES_NARRATIVA_E_COOP_v1_0_0.md`.
3. Cole o "Pedido" abaixo. Peça um bloco por vez (A, B, C, D).
4. Em cada bloco, a IA primeiro propõe uma lista curta. Você escolhe. Só depois ela escreve o texto completo.
5. Traga o resultado de volta em Markdown, no "Formato de entrega". A engenharia transcreve para o catálogo e roda os testes.

## Pedido (cole na outra IA)

> Você é roteirista de um RPG dark fantasy para Telegram chamado Asterion. Anexei a Bíblia Canônica: ela manda em Lore, nomes, NPCs e limites. Não contradiga a Bíblia. Não crie mecânica nova nem invente números de jogo. Se uma ideia precisar de regra que não existe, escreva como pergunta no fim, não como conteúdo.
>
> O objetivo é que o jogador sinta: "meu personagem pertence a este mundo e as pessoas percebem quem ele é". Não quero uma fala diferente em toda conversa só para provar que o sistema existe. Use Raça ou Classe só quando houver motivo dramático, social, cultural ou profissional real. Cada cena precisa de uma fala comum que funcione para qualquer personagem. As variações vêm depois dela, nunca no lugar dela.
>
> Textos curtos, em português, tom sombrio e contido. O jogo roda em mensagens de Telegram.

## O que o jogo já decidiu (não reabrir)

**Raças (ids):** `remanescente`, `velado`, `cinereo`, `hemario`, `alvorano`.
**Classes (ids):** `sentinela`, `errante`, `vigia`, `tecelao`, `oraculo`, `luminar`.

**Como a cena é montada:** uma cena tem falas e opções. Cada uma pode ser restrita por:
- Missão (estado e passo);
- consequência já registrada (flag);
- Raça;
- Classe;
- par exato Raça + Classe;
- descoberta feita (Local, Braseiro, Códice);
- Local atual.

Vale a mais específica. Se empatar, vale a de `priority` maior. Toda fala precisa de uma versão comum (fallback).

**Regras de narrativa:**
- A narrativa é individual. Dois jogadores na mesma cena veem falas e opções diferentes.
- No Coop de combate, o convidado não recebe a narrativa do anfitrião nem altera as escolhas dele.
- Não existe votação narrativa.
- Não duplicar missão por Raça ou Classe. A variação acontece dentro da mesma missão.
- Não mostrar conteúdo oculto como `???`.

**Limites já conhecidos:**
- "Cinéreo" não descreve a cor da pele (Bíblia v3.0 §2).
- Hemário não tem fala na oferta da P2, porque o único gancho seria Hemaris, protegido pelo limite de revelação das Terras do Ocaso.
- Não existe hoje nenhum modelo de relacionamento ou reputação com NPC no código.

**Já pronto (não refazer):** a oferta da P2 com Alda Veyr:
- Cinéreo: Alda liga o nome à história das rotas de cinza.
- Vigia: Alda reconhece o ofício.
- Cinéreo + Vigia: opção `[Perguntar pelas rotas antigas]`.

## Bloco A: catálogo de cenas

Peça à IA: "Liste as cenas da Campanha (P1 a P36) e das Secundárias (S1 a S36) em que a identidade do personagem teria relevância real. Para cada cena, uma frase dizendo por quê."

A IA propõe a lista. Você escolhe quais entram. Depois, para cada cena escolhida, entregar:

- `scene_id` (minúsculo, ex.: `p4_encontro_na_charneca`), missão e passo em que aparece, NPC que fala, Local;
- **Fala comum** (obrigatória, vale para todos);
- **Variações**, cada uma com:
  - condição: Raça, Classe, par Raça + Classe, descoberta ou flag;
  - texto;
  - `priority`, só se duas variações puderem valer ao mesmo tempo;
- **Opções de diálogo extras**, cada uma com:
  - condição;
  - rótulo curto (cabe num botão do Telegram);
  - resposta do NPC;
  - se muda algo (flag registrada) ou se é só fala.

## Bloco B: relacionamento e reputação (decisão de design)

Hoje não existe. Antes de escrever texto que dependa disso, o autor precisa decidir se vai existir. Peça à IA para **discutir**, sem escrever conteúdo ainda:

1. Faz falta um valor de relacionamento por NPC, ou as flags de consequência já bastam?
2. Se faz falta: o que o move? Escolha de diálogo, missão concluída, presente?
3. Existe reputação por facção ou comunidade, além de por NPC?
4. Reputação aparece para o jogador? Como (texto no diálogo, número, nada)?
5. Algum NPC lembra de você de uma missão para outra?

A IA responde com 2 a 3 modelos possíveis, do mais simples ao mais completo, e o custo de cada um em palavras. **Não aceitar números** (limiares, pontos). Se precisar de número, ela escreve como pergunta para o autor.

## Bloco C: NPCs que reagem à identidade

Peça à IA: "Do elenco da Bíblia, quais NPCs recorrentes deveriam reconhecer Raça ou Classe do personagem? Para cada um, por que e em quais Regiões."

Entregar por NPC escolhido:

- nome, Região, papel;
- que Raças ele reconhece e como (hostil, neutro, respeitoso, curioso);
- que Classes ele reconhece e como;
- se algum par Raça + Classe abre algo que nenhum dos dois abre sozinho;
- o que ele **não** pode revelar (limite de revelação da Região).

## Bloco D: o caso Alda (Entregar, Ajudar, Abandonar)

Hoje "Entregar Alda", "Ajudar Alda" e "Abandonar Alda" **não são conteúdo canônico**. O teste usa flags de teste. Peça à IA:

- Essas três escolhas existem na Bíblia? Se não, propor 3 escolhas canônicas para a Alda, com a cena que as oferece e a consequência de cada uma em um parágrafo.
- Qual é o impacto de cada escolha nas cenas seguintes (só o que muda de fala, sem mecânica)?

## Formato de entrega

Um arquivo Markdown por bloco, uma seção por item, com os campos acima. Marque no topo de cada item: `APROVADO` ou `RASCUNHO`. Só os `APROVADO` entram no catálogo.

## Perguntas para decidir (você)

- Quantas cenas com identidade entram no Beta? Todas as missões, ou só algumas marcantes por Região?
- Relacionamento e reputação entram no Beta, ou ficam depois?
- As escolhas da Alda são canônicas? Se sim, o texto vem da Bíblia ou da outra IA?
- Hemário e Alvorano precisam de cenas próprias, respeitando os limites de revelação?
- O Coop deve se limitar a Chefes (brief) ou continuar como o GDD v1.6.0 diz (não limitado a Chefes)? Isso não depende da outra IA, mas muda o que ela pode escrever para cenas de Coop.

# Autoridade das Fontes

## Fonte Mestra vigente

A implementação do Asterion deve usar como autoridade principal:

**ASTERION — GDD Estrutural v1.4.3 — Fonte Mestra Consolidada**

Estado oficial:

- a v1.4.3 substitui integralmente a v1.4.2 e versões anteriores;
- a Baseline Numérica v1.0 está fechada para implementação e testes;
- a reabertura anterior da conversão absoluta da unidade de XP de inimigo foi encerrada na v1.4.3;
- não existe reabertura numérica vigente na baseline.

## Fonte regional vigente

A vertical slice Nv.1–10 usa como autoridade de conteúdo:

**ASTERION — Conteúdo: Terras do Ocaso v1.0.1 FINAL**

Ela define Locais, Braseiros permanentes, Missões, Feitos, Bestiário, inimigos, descobertas e demais conteúdo regional consolidado das Terras do Ocaso.

Quando a Fonte Regional especificar conteúdo dentro de parâmetros sistêmicos da Fonte Mestra, ambas devem ser aplicadas em conjunto. Em conflito estrutural ou numérico, a Fonte Mestra prevalece; em conteúdo regional fechado, Terras do Ocaso v1.0.1 prevalece sobre rascunhos ou versões regionais anteriores.

## Fonte Visual/UI

A apresentação player-facing deve seguir:

**ASTERION — Consolidação de Visual & UI — atualização 2026-09-20, sincronizada com Fonte Mestra v1.4.3 + Terras do Ocaso v1.0.1 FINAL**

Ela define nomenclatura, texto, estrutura de telas, navegação, estados visuais e UX do Bot do Telegram. É subordinada à Fonte Mestra para regras mecânicas/números e à Fonte Regional para conteúdo regional oficial.

Exemplos de mockup não criam regra mecânica ou conteúdo canônico quando a autoridade correspondente já definir outro valor/estado.

## Decisão adicional aprovada no projeto

Em 20/09/2026 foi aprovada explicitamente a seguinte regra de estado inicial, necessária antes da primeira exposição de Vigor na HUD:

**Personagem novo inicia com 100 / 100 Vigor.**

Esta é uma decisão aprovada pelo projeto e deve ser tratada como autoritativa para implementação até sua incorporação em futura consolidação textual da Fonte Mestra. Ela não altera:

- Vigor Máximo = 100;
- regeneração +1 a cada 14m24s;
- reset das 06:00 não reabastece;
- custos de Vigor já definidos;
- regra de que Braseiro permanente não restaura Vigor.

## Regra para implementação

Antes de implementar um sistema:

1. localizar a regra estrutural/mecânica na Fonte Mestra;
2. localizar o conteúdo correspondente em Terras do Ocaso v1.0.1 quando for regional;
3. localizar a apresentação correspondente na Fonte Visual/UI;
4. aplicar decisões adicionais explicitamente aprovadas e registradas neste documento;
5. não inventar comportamento para preencher lacunas;
6. registrar conflito real em vez de escolher silenciosamente uma interpretação;
7. preservar IDs estáveis, idempotência, estado autoritativo, transações e `ruleset_version` onde aplicável.

## Baseline atual relevante — criação e primeiro combate

O fluxo implementado permanece:

`/start → nome → raça → classe → confirmação final → prólogo Cinzas na Estrada → Cão Cinéreo`

O primeiro encontro continua com:

- Cão Cinéreo Nv.1, Comum, Predador;
- 244 HP / 50 ATQ / 45 DEF / 56 AGI;
- tutorial Atacar/Defender/primeira Arte;
- 320 XP fixos;
- 0 Vigor consumido;
- sem Saque/Coroas/Materiais;
- suppress do bônus adicional de 1% de primeira observação nesta ocorrência.

A implementação histórica do combate foi instanciada sob `gdd-1.4.2-baseline-1.0`. Patches não devem reescrever silenciosamente combates ativos. Combates antigos devem continuar reprodutíveis no ruleset armazenado; novas instâncias/transições seguras devem adotar v1.4.3.

## Baseline atual relevante — primeiro Braseiro e fim do Prólogo

Após a vitória do tutorial:

- o personagem chega ao **Braseiro da Estrada**, primeiro Braseiro permanente das Terras do Ocaso;
- ele já aparece como **Descoberto**; não existe `[Ativar Braseiro]` nesse passo;
- `[Descansar]` restaura HP a 100% e remove estados comuns de combate;
- Braseiro permanente não restaura Vigor;
- não existe segunda tela de “Braseiro ativado”;
- concluir esse passo encerra o Prólogo;
- registrar idempotentemente o Feito **Cinzas na Estrada** (sem cosmético);
- iniciar automaticamente a Missão Principal **P1 — Vozes na Estrada**;
- abrir diretamente o Menu Principal;
- no primeiro Menu, o personagem está em **Terras do Ocaso · Estrada das Cinzas**, Nv.1, com **320 / 4.800 XP**;
- por decisão aprovada do projeto, Vigor inicial é **100 / 100**.

A especificação focada está em `docs/specs/PROLOGUE_BRAZIER_MENU_V1.4.3_TDO_V1.0.1.md`.

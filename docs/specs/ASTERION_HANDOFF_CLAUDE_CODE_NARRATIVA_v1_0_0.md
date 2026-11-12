# ASTERION — HANDOFF PARA CLAUDE CODE
## Camada Narrativa de Ação × Consequência · v1.0.0

Leia primeiro:

`ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md`

Esse arquivo é a especificação de design da camada narrativa. Não reinterprete as decisões nele contidas como sugestões.

## Objetivo de implementação

Implementar uma camada data-driven de:

**Ação → Consequência → Memória → Reação futura → Nova escolha.**

O sistema deve ser reutilizável pelas 72 missões da primeira jornada, sem criar 72 árvores independentes.

## Decisões fechadas

- 36 Principais + 36 Secundárias possuem pelo menos 1 nó de escolha narrativa.
- Contratos ficam fora da exigência de ramificação.
- Coop narrativo é EXCLUSIVO de Chefes.
- Missões Principais/Secundárias são solo para progresso, objetivos, escolhas e estado narrativo.
- Chefes podem ser Solo ou Grupo 1–4 segundo as regras globais de Chefe.
- Estado narrativo é pessoal.
- Escolha é commit-once e idempotente.
- NPCs não são oniscientes.
- Relação não aparece como número na UI.
- Memória pode alterar futuras falas/opções sem necessariamente criar outra missão.
- Raça e Classe só criam variantes quando houver motivo narrativo real.
- Nenhuma consequência narrativa altera automaticamente XP, Coroas, Materiais, Equipamentos, combate ou economia.
- Nenhuma escolha pessoal muda `world_state` global sem uma fonte explícita que autorize isso.

## Override obrigatório do GDD

O GDD Estrutural v1.6.0 descreve Campanha em Grupo a partir de P1. A decisão atual do projeto para a camada narrativa é mais restritiva: **somente Chefes usam Coop**.

Registrar essa divergência como alteração explícita de design. Não reativar Coop de Missão por inferência a partir do GDD antigo.

## Contrato técnico mínimo

Cada escolha deve persistir pelo menos:

```text
choice_id
mission_id
step_context
selected_option
committed_at
character_memory_tags[]
npc_memory_targets[]
future_hooks[]
identity_conditions[]
```

## Ordem de implementação recomendada

### Fase 1 — motor narrativo

Implementar:

1. Choice Node.
2. Persistência idempotente.
3. Character Narrative Memory.
4. NPC Memory.
5. Rapport qualitativo.
6. Future Hook resolver.
7. Condições de Raça/Classe.
8. Auditoria/debug de `choice_id → option → memories → future_hooks`.
9. Bloqueio de Coop em Missão.
10. Exceção de Coop para Chefe.

### Fase 2 — vertical slice narrativa

Usar primeiro:

- P1 — Vozes na Estrada
- S1 — Luzes sob as Cinzas
- P2 — Fuligem sem Fogo

A vertical slice deve provar que uma ação em P1 pode alterar uma reação em P2, e que uma decisão em S1 pode retornar em S5 sem reescrever a missão.

### Fase 3 — carga dos dados

Carregar os demais 69 nós exatamente conforme o catálogo principal.

### Fase 4 — QA

Testar no mínimo:

- escolha duplicada por reconnect;
- callback duplicado;
- abandono/reaceite de Secundária;
- suspensão de Principal;
- personagem sem escolha registrada por migração;
- Coop tentando avançar missão comum;
- Coop em Chefe;
- memória de NPC sem fonte legítima;
- opção de Raça indisponível;
- opção de Classe indisponível;
- consequência futura sem memória necessária;
- consequência futura com memória correta;
- Códice sem spoiler;
- `world_state` sem mutação indevida.

## Não fazer

Não criar:

- sistema de karma global;
- barra de relacionamento visível;
- moralidade binária;
- romance automático;
- nova moeda;
- nova progressão;
- nova economia;
- novo sistema de Coop de Missões;
- nova mecânica de viagem;
- nova mecânica de combate para suportar escolhas;
- NPC onisciente;
- escolha que reescreva retroativamente o Lore canônico.

## Critério de pronto

A implementação está pronta quando as 72 missões possuem seus `choice_id` registrados, cada decisão persiste de forma idempotente, cada memória possui escopo correto, e as reações futuras consultam apenas conhecimento legitimamente disponível ao personagem/NPC.

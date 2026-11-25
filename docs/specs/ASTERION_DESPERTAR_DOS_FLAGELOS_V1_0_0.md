# ASTERION — O DESPERTAR DOS FLAGELOS
## Especificação de Implementação V1.0.0

**Status:** FECHADO PARA IMPLEMENTAÇÃO  
**Projeto:** ASTERION  
**Feature:** O Despertar dos Flagelos  
**Escopo:** backend, combate, persistência, UI Telegram, recompensas, receitas, Bestiário/Códice, notificações e testes  
**Branch autorizada:** `claude/gifted-noether-0phq4y`  
**Branch proibida:** `main`

> Este documento é o contrato de implementação da feature. Não criar sistemas paralelos quando o GDD ou o código existente já fornece uma infraestrutura equivalente.

---

# 1. ORDEM DE AUTORIDADE

Antes de alterar código:

1. Ler o GDD estrutural vigente e os contratos existentes.
2. Inspecionar a implementação atual na branch de trabalho.
3. Reutilizar infraestrutura existente de:
   - combate;
   - World Events;
   - outbox/notificações;
   - idempotência;
   - loot/materialização;
   - crafting;
   - Bestiário/Códice;
   - HUD de combate;
   - persistência.
4. Não alterar `main`.
5. Não inventar uma arquitetura paralela sem evidência de necessidade.

Quando houver conflito entre esta especificação e o GDD, tratar como possível contradição real de design e NÃO “resolver” silenciosamente. Registrar o conflito antes de codificar.

---

# 2. OBJETIVO

Implementar o evento permanente **O Despertar dos Flagelos**.

Existem seis regiões permanentes e um Flagelo associado a cada uma.

A progressão regional é acumulada por atividades PvE normais. Ao atingir 500 pontos, o Flagelo daquela região desperta.

O Flagelo permanece vivo até ser derrotado.

Após a derrota, a barra regional retorna a zero e um novo ciclo começa imediatamente.

---

# 3. REGIÕES E FLAGELOS

| Região | ID sugerido | Nível ref. | Flagelo | Fragmento |
|---|---|---:|---|---|
| Terras do Ocaso | `tdo` | 10 | Varkhenn, o Flagelo das Cinzas | Fragmento de Cinza Condensada |
| Vales dos Enforcados | `vde` | 20 | Nharvek, o Flagelo dos Laços | Fibra do Laço Morto |
| Planícies de Nareth | `nareth` | 30 | Azharel, o Flagelo do Meridiano | Marco do Meridiano Partido |
| Várzeas Carmesins | `varzeas` | 40 | Hemrath, o Flagelo Rubro | Coágulo de Salmoura Rubra |
| Altos Cinéreos | `altos` | 50 | Korvann, o Flagelo do Contrapeso | Peso Fraturado |
| Confins do Véu | `confins` | 60 | Vaelith, o Flagelo da Fratura | Fragmento de Leitura Incompatível |

Os Flagelos são entidades próprias e NÃO substituem os Chefes de Campanha:

- Vigia Partido
- Matriarca das Raízes
- Arconte Invertido
- Matriz Rubra
- Colosso Cinéreo
- Regente Fraturado

---

# 4. PROGRESSO REGIONAL

## 4.1 Barra

Cada região possui:

```text
current_points: integer >= 0
threshold: 500
```

UI:

```text
current / 500
```

Percentual é derivado da quantidade absoluta.

Não armazenar apenas percentual.

## 4.2 Contribuições

| Atividade válida concluída | Pontos |
|---|---:|
| Caçada | +1 |
| Caçada em Grupo | +1 por participante elegível |
| Desbravar | +1 |
| Contrato Regional | +2 |
| Missão Regional | +4 |
| Masmorra | +6 |
| Outro PvE equivalente | configurável |

Regras:

- toda atividade válida concluída contribui;
- sem limite diário de Caçadas;
- sem limite individual;
- sem diminishing returns;
- sem bônus por região atrasada;
- sem seleção manual de região;
- a região alvo vem naturalmente da atividade;
- só atividade concluída gera contribuição;
- exatamente uma contribuição por `activity_id + character_id`.

A contribuição deve ser persistente e idempotente.

---

# 5. TRANSIÇÕES

## 5.1 Spawn

Quando uma região alcançar:

```text
500 / 500
```

o backend deve, atomicamente:

1. reconhecer o threshold;
2. impedir criação duplicada;
3. criar o Flagelo ativo daquela região;
4. congelar a barra;
5. registrar `spawned_at`;
6. criar o evento de notificação;
7. manter o evento sobrevivente a restart.

Se múltiplas regiões atingirem 500 de forma concorrente, NÃO criar múltiplos Flagelos simultâneos.

Existe apenas um Flagelo global ativo.

A implementação deve usar transação/lock/constraint/idempotency key equivalente para garantir isso.

## 5.2 Durante Flagelo ativo

A barra daquela região permanece congelada.

Contribuições posteriores daquela região NÃO aumentam a barra até a morte do Flagelo.

Atividades continuam normalmente para seus demais efeitos.

## 5.3 Morte

Ao derrotar o Flagelo:

1. resolver combate;
2. registrar morte exatamente uma vez;
3. liquidar recompensas;
4. registrar `defeated_at`;
5. registrar lifetime;
6. zerar a barra da região;
7. encerrar o Flagelo;
8. iniciar novo ciclo;
9. emitir notificação de morte exatamente uma vez.

Não resetar antes da confirmação autoritativa da derrota.

---

# 6. FLAGELO GLOBAL

A V1 possui:

```text
0 ou 1 Flagelo ativo globalmente
```

Não implementar seis Chefes simultâneos.

Todos os jogadores do servidor enfrentam o mesmo Flagelo ativo.

---

# 7. COMBATE

## 7.1 Arquitetura

O Flagelo usa o motor de combate existente.

NÃO criar:

- Raid Engine;
- Raid Party;
- combate separado;
- pipeline alternativo;
- cálculo de dano paralelo.

É um World Boss compartilhado integrado ao combate existente.

## 7.2 Capacidade

Capacidade operacional inicial:

```text
200 combatentes simultâneos por Flagelo
```

Esse número é capacidade do encontro, não multiplicador de poder.

## 7.3 Relógio

Cada oportunidade de ação usa:

```text
TURN_SECONDS = 10
```

Fluxo:

1. jogadores escolhem ações;
2. Flagelo escolhe ação;
3. janela fecha;
4. motor existente resolve simultaneamente;
5. estado final;
6. próxima oportunidade.

## 7.4 Pipeline

Preservar integralmente o pipeline global:

1. validação de ação/alvo;
2. hit/evasão;
3. dano bruto;
4. crítico;
5. modificadores ofensivos;
6. penetração/-DEF;
7. DEF;
8. Defender/bloqueio/mitigação;
9. Barreira;
10. HP;
11. Vampirismo;
12. status/on-hit;
13. derrota/triggers.

Não duplicar lógica.

## 7.5 Snapshot

Ao entrar em um combate contra o Flagelo:

- atributos do Flagelo são snapshotados;
- scaling não altera aquele combate;
- mudança de estado global do Flagelo não deve alterar retroativamente um combate já iniciado.

---

# 8. ESCALONAMENTO POR ABANDONO

Scaling ocorre SOMENTE quando:

```text
active_combat_count == 0
```

Se pelo menos um jogador estiver em combate:

```text
scaling_paused = true
```

A cada 15 minutos consecutivos sem combate:

```text
HP +8%
ATQ +3%
```

DEF e AGI não escalam.

Caps:

```text
HP +80%
ATQ +30%
```

Tabela:

| Minutos sem combate | HP | ATQ |
|---:|---:|---:|
| 0 | +0% | +0% |
| 15 | +8% | +3% |
| 30 | +16% | +6% |
| 45 | +24% | +9% |
| 60 | +32% | +12% |
| 75 | +40% | +15% |
| 90 | +48% | +18% |
| 105 | +56% | +21% |
| 120 | +64% | +24% |
| 135 | +72% | +27% |
| 150+ | +80% | +30% |

Fórmula:

```text
effective_max_hp = base_hp * (1 + hp_abandonment_bonus)
effective_atq    = base_atq * (1 + atq_abandonment_bonus)
```

Aumentar HP máximo NÃO cura o Flagelo.

Scaling reseta somente quando o Flagelo morre.

Lifetime do Flagelo é métrica separada do timer de abandono.

---

# 9. ATRIBUTOS

Usar atributos absolutos configurados por Flagelo.

NÃO implementar uma regra genérica `20x` no código.

Os valores abaixo são baseline de implementação/QA:

| Flagelo | Nv. | HP | ATQ | DEF | AGI |
|---|---:|---:|---:|---:|---:|
| Varkhenn | 10 | 35.060 | 138 | 100 | 94 |
| Nharvek | 20 | 51.000 | 195 | 120 | 101 |
| Azharel | 30 | 53.300 | 198 | 160 | 165 |
| Hemrath | 40 | 63.880 | 320 | 177 | 190 |
| Korvann | 50 | 98.740 | 310 | 306 | 204 |
| Vaelith | 60 | 107.840 | 401 | 322 | 334 |

Não criar tabela paralela de curva de atributos.

Quando um valor precisar ser derivado de uma fórmula global já existente, usar o materializador global.

---

# 10. KIT DOS FLAGELOS

## Varkhenn

- Golpe de Cinza — 100% ATQ
- Sopro de Fuligem — AoE 80% ATQ + 1 Queimadura
- Cinza no Pulso — 90% ATQ + ATQ −10% · 2T, CD3
- Peso do Entulho — 130% ATQ, CD3
- Última Fagulha — Preparada 180% ATQ, CD5

Identidade: desgaste.

## Nharvek

- Golpe do Laço — 100% ATQ
- Tranco das Raízes — 90% ATQ + AGI −10% · 2T, CD3
- Nó de Peso — 120% ATQ + DEF −10% · 2T, CD3
- Tensão Compartilhada — AoE 80% ATQ
- Estrangulamento Final — Preparada 180% ATQ, CD5

Identidade: debuff/ritmo.

## Azharel

- Golpe de Referência — 100% ATQ
- Correção de Linha — 90% ATQ + DEF −10% · 2T, CD3
- Medida Contrária — 125% ATQ, CD3
- Meridiano Divergente — AoE 80% ATQ + AGI −10% · 2T, CD4
- Linha Absoluta — Preparada 180% ATQ, CD5

Identidade: precisão/referência.

## Hemrath

- Golpe de Salmoura — 100% ATQ
- Pressão de Válvula — 90% ATQ + DEF −10% · 2T, CD3
- Soro Corrosivo — 85% ATQ + 1 Veneno, CD3
- Restituição Rubra — cura própria 5% HP Máximo, CD5, máximo 3 usos
- Sobrecarga de Matriz — Preparada 180% ATQ, CD5

Identidade: pressão/sustentação.

## Korvann

- Golpe de Contrapeso — 100% ATQ
- Carga Distribuída — 90% ATQ + DEF −10% · 2T, CD3
- Escora Inversa — ATQ +8%, DEF −8%, 2T, CD5
- Ruptura de Cabo — AoE 85% ATQ, CD4
- Queda do Contrapeso — Preparada 180% ATQ, CD5

Identidade: peso/defesa.

## Vaelith

- Golpe Desalinhado — 100% ATQ
- Duas Leituras — 90% ATQ + ATQ −10% · 2T, CD3
- Reflexo Partido — 125% ATQ, CD3
- Fratura Local — AoE 80% ATQ
- Protocolo Incompatível — Preparada 180% ATQ, CD5

Identidade: incompatibilidade/fratura.

Não adicionar fases, adds, Hard CC, teleporte temporal ou mecânicas fora do contrato.

---

# 11. REENTRADA

- jogador derrotado pode retornar;
- jogador que saiu pode retornar;
- nenhuma quantidade máxima de tentativas;
- nenhuma penalidade especial;
- recarga de reentrada: 2 minutos;
- Vigor: 0.

Reentrada não restaura HP do Flagelo.

Reentrada não reseta scaling.

---

# 12. PARTICIPAÇÃO

Mínimo:

```text
3 Participation Points
```

Ganhos:

| Acontecimento | Pontos |
|---|---:|
| effective_damage > 0 | +1 |
| effective_healing > 0 | +1 |
| barrier_absorbed > 0 | +1 |
| defender_prevented_damage > 0 | +1 |
| aplicação significativa de efeito | +1 |

Defender sem prevenção real = 0.

Um jogador pode ser elegível sem ter contribuído para a barra regional.

Contribuir para a barra regional NÃO concede recompensa do Flagelo sem participação.

Um jogador que entrou legitimamente no combate pode receber recompensa mesmo que não tenha contribuído para a barra.

---

# 13. RANKINGS

Três categorias:

### Ofensivo

```text
effective_damage
```

### Defensivo

```text
defender_prevented_damage + barrier_absorbed
```

Não usar dano bruto recebido.

### Suporte

```text
effective_healing
```

Overheal excluído.

Top 3 de cada categoria.

Um jogador pode aparecer em mais de uma categoria.

Desempate:

1. métrica principal;
2. Participation Points;
3. timestamp em que atingiu a métrica;
4. character_id estável.

---

# 14. RECOMPENSAS

Todo participante elegível:

- XP;
- Coroas;
- 3 materiais básicos regionais;
- 1 fragmento do Flagelo.

XP:

```text
0.08 * XP(reference_level)
```

Coroas:

```text
0.50 * crowns_per_level(reference_level)
```

Arredondamento deve usar a convenção global existente.

## Equipamento

Exatamente 1 equipamento por morte do Flagelo.

Roll:

- somente participantes elegíveis;
- chance igual;
- duplicatas permitidas;
- negociável;
- sem last hit.

## Ranking

| Posição | Fragmentos | Materiais básicos |
|---|---:|---:|
| 1º | +3 | +3 |
| 2º | +2 | +2 |
| 3º | +1 | +1 |

---

# 15. EQUIPAMENTOS

Cada região recebe nove templates especiais:

1. Principal
2. 2H
3. Secundária
4. Cabeça
5. Torso
6. Mãos
7. Pés
8. Acessório
9. Artefato

Total:

```text
9 * 6 = 54 receitas
```

Não criar:

- nova raridade;
- novos atributos;
- set bonus;
- proc paralelo;
- orçamento paralelo.

Usar:

- item level regional;
- SlotWeight;
- SW;
- raridade;
- orçamento de secundários;
- aprimoramento;
- Runas;
- Encantamentos;
- Reroll;
- regras de negociabilidade existentes.

---

# 16. RECEITAS

Uma receita produz um template fixo.

Não criar sistema novo de “escolha entre 3”.

Cada Flagelo possui 9 receitas especiais.

Enquanto houver receitas desconhecidas:

```text
25% por morte do Flagelo
```

Sem pity.

A descoberta deve ser idempotente e persistida.

Crafting deve reutilizar o sistema global existente.

Não duplicar fórmula econômica.

O fragmento específico do Flagelo é componente adicional da receita especial, sem substituir custos globais de Crafting.

---

# 17. UI

## HUD regional

Mostrar as seis barras simultaneamente.

Exemplo:

```text
⚔️ O Despertar dos Flagelos

🌑 Ocaso       420 / 500
🪢 Vales       310 / 500
🌾 Nareth      271 / 500
🥀 Várzeas     412 / 500
⛰️ Altos       198 / 500
🌫️ Confins     337 / 500

[ Enfrentar o Flagelo ]
```

## Flagelo ativo

```text
⚔️ Varkhenn, o Flagelo das Cinzas

❤️ 31.840 / 35.060

⏱️ Ativo há 18m

[ Enfrentar o Flagelo ]
```

Reutilizar o padrão visual/HUD de combate existente.

Não criar formato visual paralelo.

---

# 18. NOTIFICAÇÕES

Usar infraestrutura existente de World Event + outbox/idempotência.

Somente dois eventos:

### Spawn

```text
⚠️ O Despertar começou.

Varkhenn, o Flagelo das Cinzas, despertou nas Terras do Ocaso.
```

### Morte

```text
🏆 O Flagelo foi derrotado.

Varkhenn caiu. O ciclo do Despertar recomeçou.
```

Uma comunidade/grupo/tópico compartilhado pelas seis regiões.

Não notificar cada contribuição.

---

# 19. BESTIÁRIO E CÓDICE

Cada Flagelo deve possuir:

- Bestiário;
- entrada de Códice;
- registro de ocorrência;
- primeira derrota;
- material associado;
- identidade visual;
- lore compatível com a região.

Não revelar lore futuro através da imagem.

Não tornar:

- Avesso;
- Regente;
- Âncoras;
- cosmologia futura

mais explícitos do que o conteúdo canônico permite.

---

# 20. PERSISTÊNCIA MÍNIMA

A implementação deve possuir equivalente funcional a:

```text
flagelo_event
- id
- region_id
- status
- spawned_at
- defeated_at
- lifetime_seconds
- base_hp
- base_atq
- base_def
- base_agi
- hp_current
- abandonment_steps
- hp_scaling_bonus
- atq_scaling_bonus
- last_zero_combat_at
- version
```

Progresso:

```text
flagelo_region_progress
- region_id
- current_points
- threshold
- active_flagelo_id nullable
- version
```

Contribuição idempotente:

```text
flagelo_contribution
- activity_id
- character_id
- region_id
- points
- created_at
```

Participação:

```text
flagelo_participation
- flagelo_id
- character_id
- participation_points
- effective_damage
- effective_healing
- barrier_absorbed
- defender_prevented_damage
- meaningful_effects
- first_metric_timestamps
```

Recompensa:

```text
flagelo_reward_settlement
- flagelo_id
- character_id
- reward_type
- settlement_key
- status
```

Os nomes físicos podem seguir o padrão do projeto.

---

# 21. IDEMPOTÊNCIA

Obrigatória para:

- contribuição;
- threshold;
- spawn;
- morte;
- scaling;
- participação;
- ranking;
- XP;
- Coroas;
- materiais;
- fragmento;
- equipamento;
- receita;
- notificação;
- reconnect;
- retry;
- restart.

Callbacks antigos/inválidos devem falhar com segurança.

Crash/recovery nunca pode gerar recompensa duplicada.

---

# 22. CONCORRÊNCIA

Testar especificamente:

1. duas atividades cruzando 500 simultaneamente;
2. duas threads tentando criar o Flagelo;
3. dois processos tentando registrar a morte;
4. dois callbacks tentando pagar recompensa;
5. restart durante settlement;
6. restart durante spawn;
7. restart durante scaling;
8. jogador entrando exatamente no fechamento da janela;
9. jogador morrendo durante settlement;
10. dois jogadores disputando último lugar do ranking.

---

# 23. TESTES DE BALANCEAMENTO

Medir pelo menos:

- TTK Solo;
- TTK com 4;
- TTK com 10;
- TTK com 25;
- TTK com 50;
- TTK com 100;
- impacto do scaling;
- comportamento no cap de scaling;
- uptime do Flagelo;
- distribuição de participação;
- distribuição de recompensas;
- concentração de ranking;
- frequência de equipamentos;
- frequência de receitas.

Não alterar os valores de balanceamento silenciosamente.

Se os números forem ruins, registrar como **Balanceamento** e não reescrever a regra estrutural.

---

# 24. CRITÉRIOS DE ACEITE

A feature só é considerada pronta quando:

- [ ] uma atividade incrementa a barra corretamente;
- [ ] contribuição duplicada não pontua duas vezes;
- [ ] 500 gera exatamente um Flagelo;
- [ ] duas condições simultâneas não geram dois Flagelos;
- [ ] barra congela durante Flagelo;
- [ ] Flagelo sobrevive a restart;
- [ ] combate usa motor existente;
- [ ] capacidade 200 é respeitada;
- [ ] scaling só ocorre sem combatentes;
- [ ] scaling pausa com um único combatente;
- [ ] scaling aplica exatamente 15m/+8%/+3%;
- [ ] caps são respeitados;
- [ ] scaling não cura HP;
- [ ] snapshot de combate permanece estável;
- [ ] reentrada de 2m funciona;
- [ ] morte do Flagelo é idempotente;
- [ ] barra volta a zero;
- [ ] recompensas não duplicam;
- [ ] participação de 3 pontos funciona;
- [ ] rankings usam métricas corretas;
- [ ] equipamento é sorteado apenas entre elegíveis;
- [ ] receitas descobrem corretamente;
- [ ] HUD mostra as seis regiões;
- [ ] notificações são idempotentes;
- [ ] Bestiário/Códice registram corretamente;
- [ ] restart/recovery não corrompe o evento;
- [ ] nenhum arquivo de `main` é alterado.

---

# 25. REGRAS DE IMPLEMENTAÇÃO PARA CLAUDE CODE

Antes de codificar:

1. inspecione a árvore do projeto;
2. identifique o módulo atual de World Events;
3. identifique o motor de combate;
4. identifique os modelos de Boss/Enemy;
5. identifique o sistema de Loot;
6. identifique Crafting;
7. identifique Bestiário/Códice;
8. identifique notificações/outbox;
9. identifique testes existentes.

Depois:

1. faça o menor conjunto de alterações necessário;
2. reutilize serviços existentes;
3. não crie duplicação;
4. não migre arquitetura sem necessidade;
5. adicione testes junto com o código;
6. rode lint/typecheck/testes relevantes;
7. faça inspeção final de diff;
8. confirme explicitamente que `main` não foi alterada.

Não fazer push para `main`.

---

# 26. PROMPT DE EXECUÇÃO — CLAUDE CODE

Use este prompt junto com este arquivo:

> Você está implementando **O Despertar dos Flagelos** no projeto ASTERION.
>
> Leia primeiro:
>
> - o GDD estrutural vigente;
> - os contratos de combate;
> - o sistema atual de World Events;
> - loot/materialização;
> - crafting;
> - Bestiário/Códice;
> - notificações/outbox;
> - testes existentes.
>
> A especificação completa está neste arquivo: `ASTERION_DESPERTAR_DOS_FLAGELOS_V1_0_0.md`.
>
> ## Regras obrigatórias
>
> 1. Trabalhe EXCLUSIVAMENTE na branch `claude/gifted-noether-0phq4y`.
> 2. NÃO altere `main`.
> 3. Não faça cherry-pick/rebase/push em `main`.
> 4. Não crie Raid Engine ou combate paralelo.
> 5. Reutilize o motor de combate existente.
> 6. Reutilize World Events/outbox/idempotência existentes.
> 7. Reutilize Loot/Crafting/Bestiário/Códice existentes.
> 8. Não invente novas regras fora da especificação.
> 9. Não substitua valores publicados do GDD por valores arbitrários.
> 10. Se encontrar uma contradição real entre código, GDD e esta especificação, pare a alteração daquele ponto, documente a contradição e apresente a evidência.
>
> ## Ordem de execução
>
> ### Fase 1 — Auditoria
>
> Inspecione o código e produza internamente um mapa:
>
> - combate;
> - World Events;
> - Boss/Enemy;
> - persistência;
> - loot;
> - crafting;
> - notificações;
> - Bestiário/Códice;
> - HUD;
> - testes.
>
> Não altere código ainda.
>
> ### Fase 2 — Implementação
>
> Implemente:
>
> - progresso regional;
> - contribuições idempotentes;
> - threshold 500;
> - spawn único;
> - Flagelo global;
> - combate compartilhado;
> - scaling de abandono;
> - snapshot;
> - reentrada;
> - participação;
> - rankings;
> - settlement;
> - equipamento;
> - receitas;
> - HUD;
> - notificações;
> - Bestiário/Códice.
>
> Siga literalmente os valores deste documento.
>
> ### Fase 3 — Testes
>
> Adicione/execute testes para:
>
> - concorrência no threshold;
> - idempotência;
> - restart;
> - scaling;
> - snapshot;
> - reentrada;
> - settlement;
> - ranking;
> - loot;
> - crafting;
> - notificações.
>
> ### Fase 4 — Verificação
>
> Execute:
>
> - testes unitários relevantes;
> - testes de integração;
> - typecheck;
> - lint;
> - build, se aplicável.
>
> Depois inspecione o diff completo.
>
> Confirme:
>
> - nenhuma alteração em `main`;
> - nenhum sistema paralelo desnecessário;
> - nenhuma recompensa duplicável;
> - nenhum callback não idempotente;
> - nenhuma regra fora da especificação.
>
> ### Fase 5 — Relatório
>
> Ao terminar, informe:
>
> 1. arquivos alterados;
> 2. migrations adicionadas;
> 3. testes adicionados;
> 4. testes executados;
> 5. resultado do lint/typecheck/build;
> 6. eventuais pendências;
> 7. confirmação de que `main` não foi tocada.
>
> Não declare a feature pronta se algum critério de aceite deste documento estiver quebrado.

---

# 27. DEFINITION OF DONE

A implementação está concluída quando:

**Código + persistência + combate + recompensas + UI + notificações + testes + recovery + idempotência estão funcionando conjuntamente.**

Não basta compilar.

A feature precisa sobreviver a:

- reconnect;
- restart;
- concorrência;
- callbacks duplicados;
- derrota;
- reentrada;
- múltiplos participantes;
- ausência de participantes;
- scaling prolongado;
- morte do Flagelo.

---

## FIM DA ESPECIFICAÇÃO

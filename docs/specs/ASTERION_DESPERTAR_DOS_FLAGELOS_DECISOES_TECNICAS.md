# O Despertar dos Flagelos — decisões técnicas da implementação (2026-11-25)

Fonte: `ASTERION_DESPERTAR_DOS_FLAGELOS_V1_0_0.md` + decisões do autor de 2026-11-25
(registradas em `SOURCE_AUTHORITY.md`, seção "Exceção autoral — O Despertar dos Flagelos").

Classificação pedida pelo autor:

- **A** — regra geral existente (GDD, motor ou sistema já implementado), reaproveitada;
- **B** — exceção autoral do Flagelo (aprovada);
- **C** — lacuna não definida: não inventada; fica pendente ou com o comportamento mínimo
  descrito.

## Arquitetura (o que foi reaproveitado)

| Necessidade | Infraestrutura existente usada |
|---|---|
| Rodada de 10 s simultânea | lote `domain/veu_combat.resolve_batch` (A Ruptura do Véu) |
| Dano/cura/Barreira/efeitos do jogador | motor `domain/combat.py` via `EngineRoundSimulator` do Véu |
| Kits do Flagelo | `VeuAction`/`ActionKind` do Bestiário do Véu (campos opcionais novos) |
| Coroas e materiais | `grant_bundle` e `return_to_owner` (Inventário → Pending → retenção) |
| XP | `level_xp` + `world_events.reward_xp` (`FixedPercentXP` 8%) |
| Receitas | `Unlock` (mesmo vínculo das Receitas especiais do Crafting) |
| Bestiário/Códice | `BestiaryRecorder`, `CodexEntry`, `knowledge_catalog` |
| Notificações | Transactional Outbox (`OutboxMessage`, `dedup_key` única) |
| Job | `round_scheduler` com a trava exclusiva de jobs |

Extensões mínimas em código compartilhado (comportamento anterior preservado; as suítes do
Véu e do motor continuam verdes):

- `combat.py`: coeficientes de tick de DoT expostos como constantes públicas (mesmos valores).
- `veu_bestiary.VeuAction`: campos opcionais `dot_kind`, `dot_stacks`, `heal_hp_fraction`,
  `second_stat`, `second_magnitude`; `ActionKind.HEAL`. Os kits do Véu não os usam.
- `veu_combat`: `resolve_batch(..., kit=, level=)` (padrão = Véu), DoT em jogador com a regra
  do motor, cura própria, buff próprio com dois atributos, AoE com debuff, e a medição
  `prevented_by_character` (dano sem Defender − dano com Defender).
- `world_event_veu_combat.EngineRoundSimulator`: nível de referência por instância e um gancho
  `_attack_intent` (o Véu devolve o mesmo `PlayerIntent` de antes).
- `bestiary.py`: nome do Flagelo no aviso de estágio (o catálogo da estrada não o conhece).
- `world_event_veu_ui.py`: um botão "⚔️ O Despertar dos Flagelos" na tela de Eventos.

## Decisões

| # | Tema | Classe | Comportamento |
|---|---|---|---|
| 1 | Sem deadline; vivo até a morte | B | `flagelo_events.status = active` até a morte |
| 2 | Escalonamento por abandono | B | 15 min completos sem combatente: +8% HP Máx/+3% ATQ, teto 10 passos; não cura |
| 3 | 0 Vigor; `0,50×C + 3 básicos + 1 Fragmento` | B | `flagelos.reward_bundle` + Fragmento próprio |
| 4 | 3 Participation Points | B | `flagelos.is_eligible` |
| 5 | Arredondamento das Coroas | A | `round_10` global (meio-par): Nv.10 → 120 Coroas |
| 6 | Arredondamento de HP/ATQ escalados | A | `round_half_up` uma vez (GDD v1.4.9) |
| 7 | Materiais do prêmio vinculados (Bound) | A | mesma convenção de `grant_bundle` dos Eventos |
| 8 | Reentrada após derrota com vida cheia | A | regra do Evento Mundial existente; vida do Flagelo e escalonamento não mudam |
| 9 | Inatividade | A | GDD §49 (PvE compartilhado): 3 oportunidades seguidas sem ação = sai do combate (com a reentrada de 2 min). Sem isso um personagem parado pausaria o escalonamento para sempre |
| 10 | Defender | A | 45% do motor; ponto só quando o golpe do Flagelo realmente atingiu quem defendia |
| 11 | DoT (Queimadura/Veneno) | A | duração, teto de pilhas e coeficiente do motor; tick no fim da rodada |
| 12 | Preparada | A | decidida na abertura, anunciada durante a janela de 10 s e resolvida no fechamento: uma janela de resposta, como o motor e o Véu. Recarga 5 respeitada |
| 13 | IA | decisão do autor | Preparada → especial → básico. "Maior prioridade" entre especiais: maior recarga primeiro, empate pela ordem do kit na especificação |
| 14 | Cura própria (Hemrath) | decisão técnica | não é executável com HP cheio (sem mudança de estado) e nunca reergue o Flagelo |
| 15 | Aplicação significativa de efeito | decisão do autor | só quando o motor aplicou/renovou/empilhou um efeito no Flagelo, ou um buff de proteção num aliado; efeitos que jogadores aplicam no Flagelo persistem entre rodadas |
| 16 | Ações simultâneas no mesmo efeito | decisão técnica | todas partem do mesmo estado; fica a versão mais forte (duração, pilha) |
| 17 | Ranking | decisão do autor | métrica, Participation Points, instante do backend, `character_id`. Métrica zero não entra no Top 3 |
| 18 | Contribuição | decisão técnica | gravada na transação da atividade (única por `activity_id + character_id`); somada por um aplicador serializado no job (até ~2 s depois) |
| 19 | Barra acima de 500 | decisão técnica | a barra é `atual / 500`: o excedente não é guardado |
| 20 | Duas regiões em 500 | decisão técnica | só um Flagelo (índice único parcial). A outra fica em 500/500 e desperta quando o atual morrer, em ordem de chegada (sem prioridade inventada entre regiões) |
| 21 | Contribuição durante o Flagelo | B (§5.2) | registrada com `counted_points = 0` |
| 22 | Missão Regional | decisão técnica | um ouvinte `after_flush` grava +4 quando uma `Quest` passa a `completed`; Região pelo catálogo narrativo canônico (Missão → Região) |
| 23 | Contrato Regional | decisão técnica | +2 no `claim` (o único ponto de pagamento do Contrato), na Região do Contrato |
| 24 | Caçada em Grupo | B (§4.2) | +1 por membro, na liquidação da atividade de cada membro |
| 25 | Desbravar | decisão técnica | +1 por tentativa liquidada |
| 26 | Masmorra | B (§4.2) | +6 por membro que recebeu a conclusão |
| 27 | Equipamento | decisão do autor | sorteio único e definitivo entre elegíveis; entrega registrada como `pending_catalog` |
| 28 | Receita | decisão técnica | sorteio de 25% por participante elegível (receitas são por personagem); com catálogo vazio registra `pending_catalog` |
| 29 | Códice | decisão do autor | `CodexEntry` gravada; invisível até existir texto canônico |
| 30 | Notificação | A + B | Outbox, só nascimento e morte, uma por ocorrência; grupo da comunidade (`ASTERION_COMMUNITY_CHAT_ID`) e tópico opcional novo `ASTERION_COMMUNITY_EVENTS_TOPIC_ID`; botão para `/start flagelo` |
| 31 | HUD | A (UI v1.6.2) | hub do evento com as 6 barras, entrada pela tela de Eventos. O Refúgio do Ocaso e a Aventura não mudaram (telas canônicas da UI v1.6.2) |

## Lacunas e limitações (C)

1. **Catálogo dos 54 equipamentos/receitas**, raridade/template do equipamento sorteado,
   custos de receita e de fragmentos: pendentes (`flagelos.PENDING`).
2. **Textos de Bestiário/Códice e imagens**: pendentes. Os Flagelos aparecem no Bestiário da
   própria Região só com nome e ações observadas; usam a arte genérica de Eventos.
3. **"Outro PvE equivalente"** (ex.: Ronda de Caça): nenhum valor definido, não contribui.
4. **Lock da Configuração de Combate (GDD §21)**: o GDD manda travar a Configuração durante a
   participação. Num evento sem fim isso travaria o equipamento indefinidamente; o Véu também
   não trava. Fica pendente de decisão: o Flagelo usa a Configuração atual a cada rodada.
5. **Golpes do Flagelo não rolam evasão/crítico/bloqueio**: limitação herdada do lote do Véu
   (os passos 2, 4 e 8 do pipeline só existem no lado do jogador; o Defender é aplicado). Por
   isso os debuffs de AGI de Nharvek e Azharel não mudam a chance de acerto do Flagelo.
6. **AoE sem recarga na especificação** (Sopro de Fuligem, Tensão Compartilhada, Fratura
   Local): implementadas literalmente, então são usadas sempre que as especiais com recarga
   estão em espera. **Balanceamento** a revisar, não alterado.
7. **Balanceamento (§23)** — medição preliminar com o motor real (Sentinela no nível de
   referência, **sem equipamento e sem Artes**, só Atacar; dano médio de 6 oportunidades; TTK
   = HP ÷ (dano × N) × 10 s, sem escalonamento). Serve de piso, não de previsão:

   | Flagelo | Nv. | HP | Dano/oport. | Solo | 4 | 10 | 25 | 50 | 100 |
   |---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
   | Varkhenn | 10 | 35.060 | 75 | 78 min | 19,5 min | 7,8 min | 3,1 min | 1,6 min | 0,8 min |
   | Nharvek | 20 | 51.000 | 91 | 93 min | 23,4 min | 9,3 min | 3,7 min | 1,9 min | 0,9 min |
   | Azharel | 30 | 53.300 | 112 | 79 min | 19,8 min | 7,9 min | 3,2 min | 1,6 min | 0,8 min |
   | Hemrath | 40 | 63.880 | 146 | 73 min | 18,2 min | 7,3 min | 2,9 min | 1,5 min | 0,7 min |
   | Korvann | 50 | 98.740 | 157 | 105 min | 26,2 min | 10,5 min | 4,2 min | 2,1 min | 1,0 min |
   | Vaelith | 60 | 107.840 | 207 | 87 min | 21,7 min | 8,7 min | 3,5 min | 1,7 min | 0,9 min |

   Não medidos ainda: sobrevivência (o Flagelo também causa dano; solo o personagem cai antes),
   impacto real do escalonamento no TTK, uptime, distribuição de participação/recompensa,
   concentração de ranking e frequência de equipamento/receita com jogadores reais. Nenhum
   valor foi alterado.

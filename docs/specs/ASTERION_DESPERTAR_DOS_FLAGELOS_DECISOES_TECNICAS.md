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
| 31 | HUD | A (UI v1.6.2) | hub do evento com as 6 barras, entrada pela tela de Eventos (o HUD da Região foi acrescentado pela especificação final, #46) |

## Especificação final (2026-11-25) — o que mudou

Fonte: `ASTERION_O_DESPERTAR_DOS_FLAGELOS_ESPEC_FINAL.md`. As lacunas 1, 2, 4 e 5 da versão
anterior deste documento foram fechadas pelo autor:

| # | Tema | Classe | Comportamento |
|---|---|---|---|
| 32 | 54 templates | B (§10–§11) | `domain/flagelo_catalog.py`; raridade/SW/Ofício por slot; todos +0; sem classe de armadura |
| 33 | Armas | B (§10) | 18 identidades novas no registro de Weapon Metadata (forma, mãos, slot e tag explícitos). Maça 2H usa a identidade de Proficiência Martelo de Guerra (a única contundente de duas mãos) |
| 34 | Receitas | B (§12) | 54 Receitas especiais no Crafting global, IDs literais; só aparecem com `Unlock` |
| 35 | Custo | A + B (§12) | `8/10/14 básicos × SW` + Catalisador/Fragmento de Aprimoramento do Grau + Núcleo de Masmorra × SW (só Lendário; ver #48) + 1 Fragmento do Flagelo × SW. Divisão dos básicos igual às Receitas regionais do mesmo Ofício (Ferreiro metal+4º 70/30, Curteiro couro+erva 70/30, Joalheiro metal+4º 60/40) |
| 36 | Lendário no Crafting | A (GDD §49) | requisito de Ofício 16 e taxa `C(n)×SW×0,75` (valores globais do GDD; o código não tinha Lendário) |
| 37 | Grau | decisão técnica | Grau da Região (TDO I … Confins VI), a mesma faixa de nível do Flagelo |
| 38 | Equipamento da morte | B (§6/§11) | 1/9 por template, determinístico pela ocorrência; materializador global no nível do Flagelo; entrega Inventário → Pendentes → retenção |
| 39 | Bind do equipamento | decisão do autor (2026-11-25) | **Equipamentos regionais do Flagelo: Vinculado ao Adquirir.** Os 54 equipamentos nascem Vinculados (`bound=True`) e permanecem assim: não podem ser negociados, vendidos nem transferidos (a porta global `equipment_block_reason` os recusa por `item_bound`). Mecanismo global reaproveitado, sem sistema paralelo. Fluxo auditado: queda → Inventário (`EquipmentItem.bound`) ou Pendentes (`payload.bound`) → resgate (`bound` preservado); Crafting: o resultado das 54 Receitas é sempre Vinculado, também com ingredientes sem Bind (`CraftingService._result_bound`). Testes: `tests/test_flagelos_bind.py`. |
| 40 | Descoberta de Receita | B (§12) | por elegível (Receita é conhecimento do personagem): 25%, uma desconhecida uniforme, no máximo uma por morte; com as 9 conhecidas não sorteia (`skipped`, motivo `all_known`) |
| 41 | Lock da Configuração | B (§3) | `in_combat` do participante é o lock, lido pelo guarda global. Liberam: derrota, Sair do combate, inatividade do GDD §49 e morte do Flagelo. Tela, `/start`, `/menu`, reconexão não liberam. Entrada com outra atividade autoritativa ativa é recusada (`busy`) |
| 42 | Snapshot | B (§3) | `entry_snapshot` = atributos do Flagelo + Configuração (versão, equipamento, Caminho, Talentos, Artes). Reentrada grava outro |
| 43 | Esquiva | B (§3) | golpes do Flagelo rolam a Esquiva do motor (`CombatRng`, mesma trava anti-sequência de 2). Golpe esquivado não causa dano, DoT nem debuff. Implementado como opção do lote compartilhado; o Véu não a usa |
| 44 | Bestiário | B (§15) | texto aprovado como nota da criatura no Bestiário da Região |
| 45 | Códice | B (§16) | entrada geral + uma por Flagelo, em Mistérios e Fenômenos, com o texto como fragmento; concedidas aos elegíveis na morte |
| 46 | HUD da Região | B (§17) | barra `atual / 500` (%) no HUD do Refúgio; botão "Enfrentar o Flagelo" quando há um desperto, apontando para o hub do evento |
| 47 | Telas do evento | B (§17) | hub e combate mostram escala, métricas próprias (dano, defesa, cura) e a recompensa do último Flagelo |
| 48 | Núcleo das Lendárias | decisão do autor (2026-11-25) | **estabelece a regra correta dos Núcleos**: a versão anterior do §14 da especificação final ("Núcleos do Flagelo", com Núcleos próprios) ficou superada, e o §14 foi corrigido em `c163d05`. Não existe Núcleo do Flagelo. As 2 Receitas lendárias de cada Região (2H SW3 → 3 Núcleos; Artefato SW2 → 2 Núcleos) usam o Núcleo de Masmorra já existente da **2ª Masmorra da Região**: TDO `material.tdo.nucleo_galerias_vigia`, VDE `material.vde.nucleo_no_antigo`, Nareth `material.nareth.nucleo_observatorio_afundado`, Várzeas `material.varzeas.nucleo_cisterna_transferencia`, Altos `material.special.altos.core.bastilha_profunda`, Confins `material.special.confins.core.camara_contradicoes`. Quantidade **× SW** (§12), não o 1 fixo das Receitas regionais. Núcleos de Chefe de Campanha não entram. Obtenção: a da própria Masmorra (GDD §49: Estável 1, Fraturada 2, Ruptura 4 por conclusão) |
| 49 | Nome repetido | decisão do autor (2026-11-25) | "Relicário do Peso Suspenso" existe na Pedreira do Contrapeso (`equipment.altos.special.relicario_peso_suspenso`, Raro) e no Flagelo (`equipment.flagelo.altos.relicario.peso_suspenso`, Lendário). Nomes aprovados mantidos; IDs distintos. Problema concreto de UI vira pendência separada, sem renomear |
| 50 | Outros PvE equivalentes | decisão do autor (2026-11-25) | **V1: não existem atividades adicionais.** O conjunto efetivo de contribuição é exatamente Caçada +1, Caçada em Grupo +1 por participante elegível, Desbravar +1, Contrato Regional +2, Missão Regional +4 e Masmorra +6. Qualquer outra atividade (inclusive Ronda de Caça) concede 0 ponto: `contribution_points` devolve 0 e `record_contribution` não grava. A capacidade configurável de `CONTRIBUTION_POINTS` permanece, sem outra atividade. Testes: `tests/test_flagelos_scope.py`. |
| 51 | Balanceamento | decisão do autor (2026-11-25) | **Nenhum kit nem baseline foi alterado.** Em vez de números novos, existe uma suíte determinística sobre o motor real (`tests/flagelo_balance.py`, `tests/test_flagelos_balance.py`) que gera `docs/balance/FLAGELOS_BALANCEAMENTO_V1.md` (TTK por nº de participantes, dano recebido, AoE, Preparada, debuffs, Restituição Rubra, escalonamento 0/5/10 e diferença relativa entre os seis). Serve para ver dados e outliers; não aplica buff/nerf. Ajustar números continua decisão do autor. |

## Lacunas e limitações (C)

1. **Núcleos**: resolvido pela decisão #48. As 12 Receitas lendárias são craftáveis com o
   Núcleo da 2ª Masmorra da Região.
2. **Imagens**: fora do escopo (a cargo do autor). Os Flagelos usam a arte genérica de Eventos.
3. **"Outro PvE equivalente"** (ex.: Ronda de Caça): fechado na V1 pela decisão #50: não há
   atividade adicional; nenhuma outra atividade concede pontos.
4. **Talentos ativados por esquiva** (ex.: Desvio Ofensivo do Errante) não disparam quando o
   personagem esquiva um golpe do Flagelo: o lote compartilhado não executa gatilhos de Talento
   do lado defensivo. A chance de esquiva em si é a do motor.
5. **Crítico/bloqueio dos golpes do Flagelo**: o lote não rola crítico nem bloqueio do inimigo
   (limitação herdada do Véu). A especificação final só exigiu a esquiva.
6. **AoE sem recarga na especificação** (Sopro de Fuligem, Tensão Compartilhada, Fratura
   Local): implementadas literalmente, então são usadas sempre que as especiais com recarga
   estão em espera. **Balanceamento** a revisar, não alterado.
7. **Balanceamento (§23)** — medição completa e determinística em
   `docs/balance/FLAGELOS_BALANCEAMENTO_V1.md` (decisão #51); nenhum valor foi alterado. Abaixo,
   a medição preliminar anterior (histórico): medição preliminar com o motor real (Sentinela no nível de
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

   A medição de `docs/balance/` já cobre sobrevivência (derrotas e reentrada), impacto das AoE,
   das Preparadas, dos debuffs e da Restituição Rubra, e o escalonamento de 0, 5 e 10 passos. Ainda
   não medidos (dependem de jogadores reais ou de decisão do autor): uptime real, distribuição de
   participação/recompensa, concentração de ranking e frequência de equipamento/receita. Nenhum
   valor foi alterado.

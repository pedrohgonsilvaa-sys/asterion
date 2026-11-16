# RASCUNHO — Override da Fonte Mestra para Terras do Ocaso v1.0.18

> **Aplicado em 2026-11-14.** Os 9 itens foram registrados em `SOURCE_AUTHORITY.md` (seção "Override regional — Terras do Ocaso v1.0.18"). Este rascunho fica como histórico; a autoridade é o `SOURCE_AUTHORITY.md`.

**Status:** RASCUNHO para o autor. Não é canônico. **Não altera** `SOURCE_AUTHORITY.md` nem o GDD. Só vale depois que o autor registrar o override no índice (como foi feito com Ação × Consequência) e o incluir na próxima revisão do GDD.<br>
**Data:** 2026-11-14<br>
**Origem:** seção 9(a) da proposta `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_PROPOSTA.md` (revisão 6) e decisões do autor de 2026-11-14.<br>
**Fonte regional consolidada:** `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_FINAL.md`, seção 33.14.<br>
**Fonte Mestra afetada:** `ASTERION_GDD_Estrutural_v1.7.1_Fonte_Mestra.md`.

Por que existe: Fonte Regional não sobrescreve regra global (`SOURCE_AUTHORITY.md`). A v1.0.18 contraria a Fonte Mestra nos pontos abaixo. Sem este registro, o `programmer` não pode implementá-los.

---

## 1. Texto proposto para o índice (`SOURCE_AUTHORITY.md`)

> **Override regional — Terras do Ocaso v1.0.18.** Por decisão do autor (2026-11-14), a Fonte Regional Terras do Ocaso v1.0.18 prevalece sobre a Fonte Mestra (`ASTERION_GDD_Estrutural_v1.7.1_Fonte_Mestra.md`) apenas nos pontos abaixo e apenas para a Região 1 (Terras do Ocaso). Nada além disto é sobrescrito.
>
> 1. **Desbravar — recarga e limite por hora (GDD §18.3 e §49.15, linha 4208).** Não existem recarga de 5 min nem limite de 6 tentativas por Local por 60 min nas Terras do Ocaso. Existe limite técnico anti-spam: intervalo mínimo de 3 s entre tentativas por personagem e 1 tentativa em resolução por vez. Ele não é regra econômica e não altera recompensa. O Vigor continua pago só quando o resultado paga economia.
> 2. **Explorar e Desbravar — "Local conectado", "não ignora gates", "não ignora requisitos de nível", "não teleporta" (GDD §18.3, linha 1123).** Nas Terras do Ocaso, a revelação de Local é feita pela ação **Explorar no Refúgio do Ocaso**: ação própria, 0 Vigor, anti-spam de 3 s. Cada clique revela um Local ainda não descoberto da Região (Charneca, Bosque, Ruínas e Câmara do Poente), por sorteio uniforme, sem exigir conexão e sem verificar nível. "Local novo" não é resultado de Desbravar. **Nenhum Local é liberado por Missão:** Missão pode exigir o Local descoberto, não o revela. A revelação não concede Braseiro.
> 3. **Hub e "não existe exploração remota" (GDD §18.3, linha 1049).** O Refúgio do Ocaso é o hub da Região: liga a todos os Locais descobertos e todos voltam a ele; não há ligação Local–Local. Toda ida a um Local parte do Refúgio. Caçar, no Refúgio, escolhe o Local descoberto. Desbravar e Ronda atuam sobre o Local atual, o que preserva "sem exploração remota". Ida e volta custam 0 Vigor, 0 Coroas, 0 XP, fora de combate. A Travessia dos Braseiros fica oculta na Região, sem alterar a regra global. Braseiros seguem como checkpoint e recovery, com recovery no Braseiro do próprio Local (Câmara do Poente, sem Braseiro: Refúgio do Ocaso). Ao abrir o jogo, o personagem aparece onde estava.
> 4. **Faixas de Masmorra (GDD §49.15, linha 4182).** As faixas Nv.4–7 (Cripta do Ocaso) e Nv.8–10 (Galerias do Vigia) são recomendação de apresentação. Permanece um nível mínimo individual de entrada (GDD linha 1341): Cripta do Ocaso Nv.4, Galerias do Vigia Nv.8, em Solo e em Grupo.
> 5. **Meta de Exploração e "descoberta 100%" (GDD §49.7).** Nas Terras do Ocaso, a Exploração única fica entre 7,70% (piso, 7.529 XP) e 8,43% (teto, 8.242 XP) do requisito Nv.1→11 (97.800 XP), dentro da meta de 7–9%. O XP de descoberta de Local é `FixedPercentXP(min(nível de referência do Local, nível do personagem), 2,5%)`, só por Explorar, uma vez por Local; isto substitui, para descoberta de Local, a regra de 100% sem fator por nível. Referências: Charneca 4, Bosque 6, Ruínas 9, Câmara do Poente 10.
> 6. **Missões Principais de alto nível (GDD linha 849).** Nas Terras do Ocaso, Missões Principais e Secundárias não têm requisito de nível; dependem só do encadeamento de Missões. A linha 849 permanece válida nos demais contextos (por exemplo, Ascensão). O gate de nível da saída da Região (GDD §25) **não** é alterado.
> 7. **Nível do inimigo e `unlock_level`.** Em **Solo**, o nível do inimigo é o `max_enemy_level` do Local/região e não escala com o jogador; o `unlock_level` das criaturas não se aplica (a linha 899 já delega o Solo à Fonte Regional). Em **Grupo**, o nível do inimigo também é o `max_enemy_level` do Local. **Conflito:** a linha 899 define, em Grupo, `encounter_reference_level` = maior nível atual entre os participantes válidos e `enemy_level = min(encounter_reference_level, max_enemy_level da criatura)`, congelado no `encounter_id`. Este item sobrescreve essa regra de nível. O `unlock_level` continua como requisito individual de cada membro em Grupo (isto já é a regra da linha 899 e não conflita). Se nenhuma criatura do Local é elegível para todos os membros, a Caçada não abre e a interface informa qual membro não cumpre o `unlock_level`. Reescrita necessária na consolidação do GDD: a regra `enemy_level = min(player_level, max_enemy_level)` não está no GDD (nem na v1.6.0 nem na v1.7.1); vem das Fontes Regionais v1.0.11 a v1.0.17 e deste índice (conferido em 2026-11-14).
> 8. **PowerlevelFactor em Coop de Chefe.** O PowerlevelFactor (GDD linha 3795: `100/70/45/20/5%` para diferença `0-10 / 11-15 / 16-20 / 21-30 / 31+`) se aplica também à XP fixa de Missão em Coop de Chefe (P5, P6, S6). O GDD aplica o fator só à XP de inimigo (linha 3822) e não o define para XP fixa de Missão (linhas 3840-3842); esta Fonte Regional o define para P5, P6 e S6 (conferido em 2026-11-14, decisão do autor: manter como override).
> 9. **Ronda em Grupo.** A vitória manual válida em Grupo libera a Ronda do Local para todos os membros que participaram da vitória.

---

## 2. O que NÃO é override (conferido)

- **BKP de investigação Desbravar e de Habitat (decisão 9, marco único por criatura e por Local).** Conferido contra a Fonte Mestra v1.7.1: ela define os valores-base (linha 4241: "Habitat 3; investigação Desbravar 8") e não diz que sejam repetíveis. Prevê "marcos únicos" como ferramenta anti-farming (linha 2629), não registra de novo "marcos únicos de conhecimento" para o mesmo `encounter_id` (linha 911) e exige "marcos/IDs estáveis e idempotentes" (linha 3420). **Sem conflito; configuração regional, não override.** Limite: a Fonte Mestra não enuncia expressamente "por criatura e por Local"; a granularidade é a escolha do autor.
- **S4 e S5 em Grupo (decisão 8).** Contagem de criaturas por Missão é conteúdo regional; não toca regra global.
- **Recovery por Local, Travessia oculta na Região.** A regra global da Travessia e do Braseiro permanece; a Região só deixa de usá-la.

## 3. Como registrar (passos para o autor)

1. Ler a lista da seção 1 e aprovar ou pedir ajuste de cada item.
2. Pedir ao `game-director` para atualizar `SOURCE_AUTHORITY.md`: apontar a v1.0.18 FINAL como vigente da Região 1 e copiar o texto da seção 1 como "Override regional".
3. Na próxima revisão do GDD, incorporar os 9 itens e a reescrita da regra de `enemy_level` em Grupo (que não tem linha no GDD).
4. Só então o `programmer` implementa.

## Lacunas para o autor

- **O1.** Os itens 1 a 9 precisam do seu registro explícito. Sem ele, nada vai para código. Recomendo aprovar todos de uma vez, porque Solo e Grupo ficariam com regras diferentes se o item 7 ficasse de fora.
- **O2.** Item 8: confirmar se o PowerlevelFactor em Coop de Chefe já é a regra global (então sai da lista de override) ou se precisa ficar registrado. Recomendo manter registrado até conferir a linha 3795. **Resolvida em 2026-11-14:** a linha 3795 não confirma regra global; o autor manteve o item como override.
- **O3.** Linha 895 do GDD: o conflito do item 7 em Grupo foi decidido por você (nível do Local). Recomendo registrar o motivo no índice: coerência com o estilo soulslike e carona coberta pelo `unlock_level` individual.
- **O4.** Valor do `min()` do XP de Local e das referências (4, 6, 9, 10) já foram decididos; nenhum número novo é proposto aqui.

## Critérios de aceite

1. O `SOURCE_AUTHORITY.md` lista a v1.0.18 FINAL como vigente da Região 1 e contém o texto da seção 1 (9 itens), com data.
2. Cada item do texto cita o trecho da Fonte Mestra que contraria (linha ou seção), como na seção 1.
3. O texto limita o override à Região 1 e diz que nada além dos 9 itens é sobrescrito.
4. O gate de nível da saída da Região (GDD §25) não aparece como alterado.
5. O QA só marca como testáveis os critérios da v1.0.18 que dependem do override (33.16, itens 2, 6, 9, 14, 15 e 21) depois deste registro.

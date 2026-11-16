# Auditoria de farm e XP — Terras do Ocaso v1.0.18 PROPOSTA

**Data:** 2026-11-14
**Autor da auditoria:** systems-designer
**Alvo:** `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_PROPOSTA.md`, seção 7, pontos A1 a A9.
**Base comparada:** `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.17_FINAL.md` (vigente, Região 1 em `SOURCE_AUTHORITY.md`) e `ASTERION_GDD_Estrutural_v1.6.0_Fonte_Mestra.md` (Fonte Mestra vigente).
**Método:** conferência de cada número da proposta contra a v1.0.17 e a Fonte Mestra; contas em Python; simulação Monte Carlo (20.000 execuções) do pool de Desbravar. Nada em `src/`, `alembic/`, `SOURCE_AUTHORITY.md` ou na proposta foi alterado.

Termos usados: **Vigor** = recurso que limita ganho econômico (máx. 100, +1 a cada 14m24s, GDD §17). **Ronda** = Caçada automática em lotes (GDD §18.2). **Unlock** = nível mínimo para a criatura aparecer no pool. **FixedPercentXP** = XP fixo = `round_half_up(XP(nível de referência) × %)` (GDD §49.7). **Pool** = lista de resultados sorteáveis.

---

## 0. Resumo dos vereditos

| Ponto | Tema | Veredito |
|---|---|---|
| A1 | Desbravar sem recarga e sem limite por hora | OK com condição (economia é limitada por Vigor); RISCO técnico no anti-spam |
| A2 | Combate de Desbravar sem teto (XP) | OK |
| A3 | Nova fonte única "Local novo" (XP) | RISCO (alto) |
| A4 | Frequência e tempo até Locais Nv.9-10 | RISCO |
| A5 | Remoção de travas de nível | BLOQUEIO parcial (Masmorras e encontros de Missão por elegibilidade); resto RISCO |
| A6 | Ronda em Local alto por jogador baixo | RISCO baixo a médio |
| A7 | Missões sem função de chave | OK, com um incentivo torto a corrigir |
| A8 | Braseiros cedo, Travessia e recovery | RISCO médio (desenho, não economia) |
| A9 | Ritmo de encontros e Variantes | OK |

Bloqueios gerais antes de qualquer código (fora de A1-A9): override da Fonte Mestra precisa cobrir mais do que a recarga (ver seção 11).

---

## 1. Números da proposta conferidos

Conferido e correto:

- Principais `37.120` = 2.400+3.300+4.400+5.700+7.100+14.220 (v1.0.17 §5.2). Secundárias `21.965` = 1.140+2.695+1.760+3.990+4.480+7.900. Juntas: 59.085 XP = 60,4% de 97.800.
- `97.800` = soma de `XP(1..10)` com `XP(n)=round_100(4000+750n+43n²)` (GDD §49.7). Confere.
- `456 / 616 / 800 / 1.136` = 8% de XP(2/4/6/9) = 5.700 / 7.700 / 10.000 / 14.200. Confere.
- Grandes atuais `5.560` = 456 + 2×616 + 2×800 + 2×1.136. Menores `1.489` = 143+193+193+250+355+355. Total `7.049` = 7,21% de 97.800. Confere.
- `8.112` = 5.560+616+800+1.136. `9.601` = 8.112+1.489. Confere.
- P6 `14.220/15.800` = 90%. Confere (v1.0.17 §24.7).
- Pesos novos 50/50, 25/25/50: soma 100 em cada Local. Confere.

Números ou afirmações que a proposta traz errados ou imprecisos:

| # | Onde na proposta | Problema | Fonte |
|---|---|---|---|
| E1 | §3.5 e Pendência 3 ("XP da Câmara não aparece na fonte lida") | O número existe: `XP(10)=15.800` (GDD §49.7, "Pontos: 10→11 15.800"). 8% = **1.264**. Grandes ficam `9.376`; exploração única total `10.865` = **11,11%** de 97.800. | GDD §49.7; v1.0.17 §24.1 |
| E2 | §3.6 e critério de aceite 12 ("prioridade Poente, Galhos Mortos, Vento Morto, Refúgio") | A prioridade é **por Local**, não global. Charneca: só Vento Morto, senão Refúgio (v1.0.17 §11.9). Bosque: Galhos, Vento, Refúgio (§29.9). Ruínas: Poente, Galhos, Vento, Refúgio (§30.7). | v1.0.17 §11.9, §29.9, §30.7 |
| E3 | A9 ("Variantes de 12% a 15% conforme o Local") | A chance real é 8% Estrada, 10% Charneca, 12% Bosque, 15% Ruínas. | v1.0.17 §10.2-§10.5 |
| E4 | §3.2 e A4 ("cerca de 4% por tentativa, 1 a cada 25") | Só vale no estado inicial. Estrada: 4% até achar o Marco, depois **8%**. Charneca/Bosque/Ruínas: 4%, depois 5,33% (uma Grande achada), depois 8% (duas achadas). Média medida na Estrada: 1ª revelação em 18,6 tentativas, não 25. | simulação, seção 5 |
| E5 | Seção 6 ("Auditar (A2)") sobre §24.7 | A2 trata de combate de Desbravar, não de P6. Referência cruzada trocada (nenhum efeito numérico). | proposta §6 e §7 |
| E6 | Aviso de topo (só cita recarga e limite por hora) | O conflito com a Fonte Mestra é maior. Ver seção 11. | GDD §18.3, §49.15 |
| E7 | A5 (lista de encontros fixos) | Incompleta: falta S2 (Peregrino Calcinado Nv.4 fixo, v1.0.17 §5.6) e S4/S5 (Vigia Rachado; Mariposa ou Custódio Sem Rosto "conforme elegibilidade", §5.10/§5.11). | v1.0.17 |
| E8 | A5 ("requisito de nível do Equipamento é regra global, fora do escopo") | A regra existe e resolve o ponto: equipar exige nível do personagem ≥ `item_level` (GDD §1608 e §3982). Ver A5. | GDD |
| E9 | v1.0.17 §11.9 (texto herdado) | "o conteúdo normal da Charneca requer P2 concluída" fica falso na v1.0.18. A consolidação em FINAL precisa reescrever esse trecho (não só os que a proposta cita). | v1.0.17 §11.9 |

Ambiguidade que pode virar bug: a proposta cria 4 IDs (`explore.tdo.local.charneca`, `.bosque`, `.ruinas`, `.camara_poente`) mas fala de "um resultado Local novo de peso 50" com sorteio de alvo (Pendência 2). Se o programmer implementar 4 resultados de peso 50 cada, a chance de revelar sobe (200 contra 50 no sub-pool). Precisa decisão (D4).

---

## 2. A1 — Desbravar sem recarga e sem limite por hora

**Veredito: OK para economia. RISCO técnico no anti-spam.**

**Evidência.**

1. A economia repetível de Desbravar só paga com Vigor (v1.0.17 §11.6; GDD §17, §18.3). Só dois resultados pagam: Combate (25% da categoria) e Pequeno Recurso (10%). Chance de uma tentativa pagar: 35%. Custo: 4 Vigor.
2. O Vigor, não o limite por hora, já era o freio dominante. Limite antigo: 6 tentativas/Local/h, ou seja 2,1 pagamentos/h/Local, ou 8,4 Vigor/h. Regeneração: 4,17 Vigor/h. O limite antigo só atrasava a queima do estoque de 100 Vigor (25 pagamentos = cerca de 71 tentativas = 11,9 h em um Local, ou 3 h em quatro Locais). Agora o estoque queima em minutos. O teto de longo prazo é o mesmo: 100 Vigor/dia de regeneração = 25 pagamentos/dia.
3. Coroas por Vigor (C = unidade econômica, GDD §49.10):
   - Desbravar Combate: 0,15×C / 4 = **0,0375×C por Vigor**.
   - Desbravar Pequeno Recurso: 0,10×C / 4 = 0,025×C por Vigor.
   - Média ponderada (25:10): 0,0339×C por Vigor.
   - Caçada Comum: 0,05×C / 2 = 0,025×C por Vigor; Incomum 0,04×C.
   - Mistura da Charneca em Nv.4+: cerca de 0,0277×C.
   - Desbravar paga cerca de 22% mais Coroas por Vigor que a Caçada da Charneca, mas paga menos Materiais por Vigor (0,29 contra 0,40 da Caçada Comum) e não tem Equipamento nem Runa. A Fonte Mestra (§18.3) pede que Desbravar não seja superior à Caçada em economia: no limite, e inalterado pela proposta.
4. Tentativas sem pagamento não geram valor repetível: Conhecimento repetível, Narrativo repetível e Atmosférico dão 0 XP e 0 economia. Valor único (Códice, Bestiário, descobertas) é finito.

**Lacunas.**

- Sem o valor do anti-spam não há como calcular o ritmo máximo (A1a). Como referência de leitura, não de regra: tentativas por hora = 3.600 / intervalo em segundos (intervalo de 2 s dá 1.800/h; de 5 s dá 720/h). Em qualquer valor, o Vigor limita o ganho.
- Cada tentativa grava uma linha própria (`exploration_attempt_id`, GDD §18.3). Sem recarga, um cliente automatizado pode gerar dezenas de milhares de linhas por dia. É risco de banco e de antiexploit (§36), não de balanceamento.
- Feitos ou contadores de "N tentativas de Desbravar" não foram vistos na v1.0.17 §17. Se existirem ou vierem a existir, o limite de 6/h deixa de proteger. Não verificado no código (fora do escopo).
- Bestiário: o GDD lista BKP "investigação Desbravar 8" e "Habitat 3" (GDD §49, linha de BKP). Não está escrito se o ganho é uma vez por criatura. Rastros Cinéreos, Vestígios e Rastros entre os Galhos são repetíveis e dão "evidência contextual". Precisa confirmação de que é marco único por criatura/Local (D9).

**Mitigação.**

- Definir o anti-spam como atraso mínimo entre cliques (recomendação da própria proposta, Pendência 1A) e limite técnico de tentativas abertas por personagem. Não deve tocar recompensa.
- Teste de QA: 1.000 tentativas seguidas com Vigor 100 e com Vigor 0; conferir que Coroas/Materiais totais não passam de 25 pagamentos e que XP repetível usa fator 0,25.
- Conferir no programmer que "Vigor < 4" não consome Vigor parcial (v1.0.17 §11.6).

---

## 3. A2 — Combate de Desbravar sem teto de ritmo

**Veredito: OK.**

**Evidência.**

1. Com Vigor < 4, a vitória em Combate de Desbravar dá XP ×0,25 (v1.0.17 §11.6; GDD §49.7 "Conteúdo repetível com Vigor insuficiente: 25% XP"). Mesma regra vale para Caçada Manual com Vigor insuficiente, que já não tem recarga nem limite por hora.
2. Seja `d` a duração de um combate e `t` a de uma tentativa sem combate. Tentativa de Desbravar: 25% de chance de combate. Razão de XP por hora, Desbravar sobre Caçada Manual no mesmo estado de Vigor: `0,25·d / (0,25·d + 0,75·t)`. É sempre menor que 1; tende a 1 só se `t` tender a 0 (limite técnico do anti-spam). Exemplo ilustrativo, valores supostos (d=3 min, t=0,5 min, não vêm da fonte): razão 0,67.
3. O pool de combate de Desbravar não tem Elite (Alfa, Viúva, Custódio do Poente ficam de fora: v1.0.17 §11.2-§11.5, §29.6), então o XP médio por combate de Desbravar é igual ou menor que o da Caçada do mesmo Local.
4. Referência de grandeza (GDD §49.7, `EnemyXPUnit = XP(n)/(20·H(n))`, Comum equivalente): Nv.5 = 320 XP; ×0,25 = 80 XP por vitória. Ronda a 3 min por encontro com Vigor: 20 encontros/h × 320 = 6.394 XP/h no Nv.5 (taxa de desenho). Mas a Ronda para com Vigor < 2 (GDD §17): 100 Vigor dão 50 encontros. Sustentado só pela regeneração: 2,08 encontros/h. Sem Vigor, a Caçada Manual a 25% e d=3 min dá cerca de 1.600 XP/h no Nv.5 (suposição de d).
5. Observação de sistema, anterior à proposta e não causada por ela: o XP sustentado por hora depende mais do "grind sem Vigor a 25%" da Caçada Manual do que da Ronda. Se o combate manual real durar bem menos que os 3 min do desenho, o grind sem Vigor sobe de forma proporcional. Vale medir na Telemetria do Alpha. A proposta não piora isso.

**Mitigação.** Nenhuma regra nova. Teste de QA: XP por hora medida de Desbravar Combate contra Caçada Manual com Vigor 0, mesmo Local e nível; esperado ≤ 1,0.

---

## 4. A3 — Nova fonte única "Local novo" (XP)

**Veredito: RISCO (alto, decisão de autor).**

**Evidência.**

1. Número recalculado (E1): Câmara = 1.264. Locais novos somam 616 + 800 + 1.136 + 1.264 = **3.816 XP**. Grandes: 9.376. Exploração única total: **10.865 XP = 11,11%** do requisito Nv.1→11 (97.800). Antes: 7,21%.
2. A meta global de Exploração é **7-9%** da primeira jornada (GDD §49.7). 11,11% passa de 9% em 2,1 pontos percentuais. A v1.0.17 §24.1 tratava a meta como referência, não teto; ainda assim a proposta não diz que aceita ficar fora da banda.
3. FixedPercentXP não tem fator por nível (GDD §49.7: "descoberta grande inédita 8% do requisito do nível"; descoberta é 100%). Um Nv.1 recebe Nv.9 e Nv.10 integralmente:
   - 3.816 XP de "Local novo" = **79,5% do Nv.1→2** (4.800).
   - Com o fim das travas Nv.4+/Nv.8+/Nv.6+ (proposta §3.2), as 7 Grandes e 6 Menores antigas também ficam acessíveis no Nv.1. Tudo junto, 10.865 XP, igual ao acumulado para chegar ao Nv.3 (10.500). Ou seja, só com exploração e sem combate um Nv.1 chega ao Nv.3.
4. Ritmo: o desenho do GDD gasta H(1)+H(2) = 2,09 h de jogo para ir do Nv.1 ao Nv.3. Pela simulação, esgotar a exploração única de Estrada, Charneca, Bosque e Ruínas custa cerca de 150-200 tentativas (soma das médias da simulação: Estrada 15,7 + Charneca 25,5 + Bosque 25,1 + Ruínas 26,6 sem "Local novo", mais cerca de 63 para revelar os quatro Locais). Com tempo por tentativa suposto de 0,5 a 1,1 min (ilustrativo), são 1,5 a 3 h. Ritmo próximo do desenho, mas **concentrado nos primeiros níveis e quase sem combate**: cerca de 63% do XP do Nv.1→3 viria de exploração, contra 7-9% da meta da jornada inteira.
5. Segurança: no Nv.1, Bosque e Ruínas têm pool de combate vazio (todas as criaturas têm unlock ≥ 3; seção 7). Desbravar ali não encontra combate. O Nv.1 explora Ruínas com risco quase nulo.
6. Incentivo torto (A7): descoberta feita por Missão dá 0 XP; descoberta por Desbravar dá XP. Quem segue a Missão primeiro perde até 3.816 XP de "Local novo", quem explora primeiro ganha. Dois jogadores terminam o mesmo conteúdo com XP total diferente em 3,9% do requisito.

**Mitigação (opções para o autor; valores recalculados, nenhum inventado).**

- **A. Aceitar como está.** Exige registrar que a Exploração fica em 11,11% (acima da banda 7-9%) e que o início fica concentrado em exploração.
- **B. XP de descoberta independe da via (recomendada).** A primeira descoberta de cada Local dá o mesmo FixedPercentXP por Missão ou por Desbravar, uma só vez. Todos terminam com o mesmo total e o incentivo torto some.
- **C. Limitar o nível de referência ao nível do personagem** (`min(ref, nível)`), por exemplo para "Local novo" e para Grandes/Menores únicas. No Nv.1, os quatro Locais novos pagariam 8% de 4.800 = 384 cada (1.536 no total, em vez de 3.816). Mantém o total da jornada perto da banda para quem sobe no ritmo normal. Muda a regra global "descoberta 100%" (GDD §49.7), portanto exige override.
- **D. "Local novo" sem XP** (só desbloqueia o Local). Exploração fica em 7,21% como hoje. É a opção mais conservadora; o autor decidiu em 9.10 pelo contrário, então só se ele rever.

---

## 5. A4 — Frequência de "Local novo" e tempo até Locais Nv.9-10

**Veredito: RISCO.**

**Evidência (simulação com os pools da v1.0.17 §11.2-§11.5, pesos da proposta §3.2, anti-repetição §11.7; um resultado "Local novo" por Local; alvo por sorteio uniforme; jogador permanece na Estrada, o que só vale se a Pendência 6 permitir).**

Chance instantânea de "Local novo" por tentativa:

| Estado | Chance |
|---|---|
| Estrada, Marco ainda não achado | 4,00% |
| Estrada, Marco achado | 8,00% |
| Charneca/Bosque/Ruínas, nenhuma Grande achada | 4,00% |
| Uma das duas Grandes achada | 5,33% |
| As duas Grandes achadas | 8,00% |

Tentativas na Estrada até revelar (média / mediana / percentil 90):

| Alvo | Média | Mediana | P90 |
|---|---:|---:|---:|
| Charneca | 41,5 | 37 | 79 |
| Bosque | 41,8 | 38 | 80 |
| Ruínas (Nv.9) | 41,4 | 37 | 79 |
| Câmara (Nv.10) | 41,4 | 37 | 79 |
| Os quatro | 63,1 | 59 | 99 |

A primeira revelação (qualquer alvo) sai em média na tentativa 18,6. Cerca de 41 tentativas até Ruínas é perto de 40 a 80 minutos com os tempos supostos de A3 (ilustrativo). Antes: 6 tentativas/h por Local e travas Nv.8+; as mesmas 41 tentativas levariam cerca de 7 h num só Local.

Efeitos de redistribuição:

- Se "Local novo" sai do pool (sem alvo restante), a categoria Grande Descoberta só some se as outras Grandes também estiverem consumidas; aí seu peso 8 é redistribuído proporcionalmente (regra §11.1). Não há risco de pool vazio, porque Conhecimento, Narrativo, Atmosférico e Recurso têm resultados repetíveis.
- Descoberta Menor e Grande únicas somem do pool e a chance relativa dos repetíveis sobe. Efeito pequeno e previsível.

**Pontos de atenção.**

- O sorteio uniforme pode revelar a Câmara do Poente primeiro. Isso gasta uma revelação no Local sem Desbravar, Caçada nem Ronda (proposta §3.6), paga 1.264 XP no Nv.1 e antecipa a existência da Âncora do Poente no mapa, o que o GDD §18.3 trata com cuidado (spoiler). Decisão narrativa para o game-designer/narrative-designer.
- Tempo por tentativa não existe na fonte. Todos os "minutos" acima são ilustrativos; o QA deve medir.

**Mitigação.** Recomendação qualitativa: tornar o alvo ordenado ou ponderado para que a Câmara só entre depois de uma condição narrativa, ou excluí-la dos alvos de "Local novo" (continua revelada por P6 Etapa 2). Valor de pesos por alvo (Pendência 2B) é decisão do autor.

---

## 6. A5 — Remoção de travas de nível

**Veredito: BLOQUEIO parcial. Masmorras e encontros por elegibilidade precisam de decisão antes de código. Resto: RISCO.**

**Evidência e conta.**

1. **Equipamentos de Campanha cedo: OK.** Equipar exige nível ≥ `item_level` (GDD linhas 1608 e 3982). Raro Nv.5 de P3 e Épico Nv.10 de P6 podem ser recebidos cedo, ficam vinculados e inúteis até o nível certo. Sem ganho de poder antecipado. A frase da proposta de que isso é "fora do escopo" é desnecessária: está resolvido pela regra global.
2. **Missões P1-P6 (37.120 XP) e Secundárias (21.965 XP).** O encadeamento de Missão continua. O que impede o salto de curva é a dificuldade dos encontros fixos, não uma regra. Encontros fixos: Aranha Nv.3 (P2), Peregrino Nv.4 (S2), Cervo Nv.5 (P3), Vigia Rachado Nv.7 (P4), Custódio do Poente Nv.9 Elite (P5), Guardião do Último Rastro Nv.10 (S6), Vigia Partido (P6 Chefe).
   - Um Nv.1 que vença o Custódio Nv.9 recebe LevelFactor 110% (diferença ≥ +5, GDD §49.7): EnemyXP ≈ **1.230**. Chefe Nv.10: ≈ **2.820** (6,0 × 428 × 1,10). Inimigos muito acima do nível não dão XP menor, dão maior.
   - Sem simulação de combate não dá para afirmar a taxa de vitória de um Nv.1 contra encontros fixos Nv.3-Nv.7. **Medição pendente (QA)**; não rodei simulador de combate nesta auditoria.
3. **Coop de Chefe como carona (RISCO).** P5, P6 e S6 aceitam Coop (override de Coop de Missão, `SOURCE_AUTHORITY.md`). Antes, o Nv.9-10 de entrada barrava Nv.1-8. Agora um personagem de nível baixo pode ser carregado por veterano. PowerlevelFactor (GDD §49.7) corta o XP do carregado só quando a diferença passa de 10 níveis (100% até 10, 70% de 11 a 15, 45% de 16 a 20). Não está dito se esse fator se aplica a XP fixa de Missão (P5 7.100 + P6 14.220 + S6 7.900 = 29.220 XP, que cobre o Nv.1→6, cumulativo 33.600 para Nv.6). Precisa decisão (D7).
4. **Masmorras (BLOQUEIO parcial).** A "Faixa" Nv.4-7 e Nv.8-10 também é regra global (GDD §49 linha 4113: "Faixas por Região iniciada em L: A L+3→L+6; B L+7→L+9"), não só texto regional. Primeira Estável: Cripta 6.640 XP (5.440 + 1.200), Galerias 8.010 XP (6.480 + 1.530); inimigos de nível de referência 6 e 9. Com Nv.1 + veterano de até 10 níveis acima (PowerlevelFactor 100%), uma única corrida dá 6.640 XP, cerca de 1,4 nível do Nv.1. Fraturada exige Primeira Conclusão Estável e Ruptura exige Nv.60 (GDD §49), então o dano fica na Estável. A elegibilidade global de Masmorra lista "nível mínimo" (GDD linhas 1330-1340); a proposta o remove sem substituir.
5. **Encontros de Missão por elegibilidade (BLOQUEIO de especificação).** S4 ("Derrotar um Vigia Rachado") e S5 ("Mariposa de Brasa ou Custódio Sem Rosto, conforme elegibilidade", v1.0.17 §5.11) dependem do unlock da criatura (7, 6 e 8). Um Nv.1 não tem criatura elegível; o comportamento fica indefinido. A proposta não trata esse caso.
6. **Pool vazio por unlock (Pendência 4A).** No Nv.1-2 o Bosque tem pool de Caçada vazio; no Nv.1-4 as Ruínas também (unlock mínimo 5). Sem Caçada manual vencida não há Ronda. Comportamento da UI com Local sem pool não está definido.

**Mitigação.**

- Recomendação qualitativa: **manter** um nível mínimo individual para entrada nas Masmorras (ou aplicar a elegibilidade global de nível mínimo), mesmo que o resto das travas saia. É a trava que impede carona de XP alto no Nv.1. Decisão do autor (D6).
- Definir, para encontros de Missão por elegibilidade, a regra de fallback: criatura fixa com nível fixo (como P2 já faz) ou nível mínimo da Missão. Valor a decidir (D8).
- Definir o texto de UI para Local sem pool elegível (ex.: "nada para caçar aqui ainda").
- Confirmar com o GDD (linha 845, "Missões Principais de alto nível ficam Suspensas enquanto o requisito de nível não estiver satisfeito"): o texto fala de Ascensão, mas o termo "requisito de nível" de Missão Principal existe na Fonte Mestra; a proposta precisa registrar isso no override (seção 11).
- Teste de QA: taxa de vitória de Nv.1, Nv.2 e Nv.3 contra cada encontro fixo e contra Cripta Estável.

---

## 7. A6 — Ronda em Local alto por jogador baixo

**Veredito: RISCO baixo a médio (depende de manter a Pendência 4 opção A).**

**Evidência.**

1. Com `enemy_level = min(player_level, max_enemy_level)` e unlock por criatura (v1.0.17 §10.1), o nível, o XP e o `loot_reference_level` seguem o nível do jogador, não o do Local (GDD linha 3885: item_level = enemy_level). Um Nv.1 não recebe Saque Nv.9. Ronda continua 2 Vigor por encontro e para com Vigor < 2.
2. Não há Ronda no Nv.1-2 no Bosque nem no Nv.1-4 nas Ruínas: precisa de uma vitória manual antes, e o pool está vazio.
3. **Pool afinado.** Com poucas criaturas elegíveis, a proporção de Incomuns sobe. Cálculo (sem Elite, que tem unlock alto), multiplicadores contra a Estrada de mesmo nível (Comum = 1,00):

| Local e nível | % Incomum | XP por encontro | Coroas por encontro | Materiais por encontro |
|---|---:|---:|---:|---:|
| Estrada (qualquer) | 0 | 1,000 | 1,000 | 0,80 |
| Charneca Nv.3 (pool natural) | 22 | 1,079 | 1,135 | 0,96 |
| **Bosque Nv.3** (só Aranha) | **100** | **1,350** | **1,600** | **1,50** |
| Bosque Nv.4 | 43 | 1,149 | 1,255 | 1,10 |
| Bosque Nv.5 | 26 | 1,091 | 1,156 | 0,98 |
| Ruínas Nv.6 | 44 | 1,156 | 1,267 | 1,11 |
| Pool completo (Bosque/Ruínas Nv.8+) | 41 | 1,144 | 1,247 | 1,09 |

   Bosque Nv.3 rende 25% mais XP, 41% mais Coroas e 57% mais Materiais por encontro do que a Charneca para o mesmo jogador, e não tem Elite interrompendo a Ronda. A Aranha Nv.3 é Controlador e mais difícil que um Comum; parte do ganho é pago em risco. Mesmo assim é um atalho de farm que não existia (Bosque exigia Nv.5).

**Mitigação.** Opções qualitativas para o autor: (A) aceitar (ganho pequeno, bloqueado pela dificuldade); (B) exigir mínimo de criaturas elegíveis para o Local abrir Caçada/Ronda; (C) o Local só abre Ronda quando houver pelo menos uma criatura Comum elegível no pool. Nenhuma exige número novo se escolher B ou C com "pelo menos uma Comum". Não adotar Pendência 4B (piso de nível por Local): quebraria `loot_reference_level` e tornaria Nv.1 em Local Nv.9 fonte de Saque Nv.9.

---

## 8. A7 — Missões sem função de chave

**Veredito: OK, com ajuste de incentivo.**

**Evidência.**

- Recompensas totais de Missão (v1.0.17 §5.2): 59.085 XP (60,4% do Nv.1→11); Coroas 1.490 (Principais) + 890 (Secundárias) = **2.380**; Materiais vinculados: 16 Ferro, 14 Resíduo, 6 Couro, 6 Erva = 42 unidades; 1 Raro Nv.5 e 1 Épico Nv.10.
- Comparação em Coroas: 100 Vigor em Caçada Comum Nv.5 (C=180) = 50 encontros × 0,05 × 180 = **450 Coroas**. As Missões valem cerca de 5,3 dias de Vigor inteiro. Continuam sendo a maior fonte de XP e a única fonte de Equipamento de Campanha.
- Materiais de Missão são vinculados (não vendem): valor só para Crafting.
- O que cai: o papel de chave de acesso (P2, P3, P4). Isso é a decisão 4=C do autor e não cria loop.

**Problema real.** Já descrito em A3: descoberta por Missão dá 0 XP, por Desbravar dá XP (diferença de até 3.816 XP). Isso penaliza quem segue a campanha.

**Mitigação.** Opção B de A3 (XP de primeira descoberta igual por qualquer via).

---

## 9. A8 — Braseiros descobertos cedo (Travessia e recovery)

**Veredito: RISCO médio (desenho, não economia).**

**Evidência.**

1. Descobrir um Braseiro por Desbravar fica mais fácil por tempo, mas **mais lento por tentativa**: a chance por tentativa do Braseiro do Vento Morto cai de 4% (antes: 8% × 50/100) para 2% (agora: 8% × 25/100), subindo para 2,67% e 4% quando as outras Grandes saem. Efeito líquido: mais rápido em horas, não em tentativas.
2. Travessia custa 0 Coroas e 0 Vigor (GDD §49.10). Origem precisa ser um Braseiro permanente; destino precisa estar descoberto (GDD §40). Um Nv.1 que descubra o Braseiro do Poente pode ir da Estrada às Ruínas sem rota. Nas Ruínas, no Nv.1, não há combate nem Caçada. Dano econômico nulo.
3. **Recovery.** A prioridade é por Local (E2). Derrota nas Ruínas leva ao Poente, o que é bom. Derrota em Local mais acima sem Braseiro leva ao Refúgio, sem rota Refúgio↔Ruínas nem Charneca↔Ruínas (v1.0.17 §30.3). O jogador terá de andar Refúgio→Charneca→Bosque→Ruínas (rotas gratuitas, sem encontro).
4. **Pendência 6, opção A** (Local de ação escolhido livremente entre os descobertos, sem rota, 0 Vigor) torna a Travessia dos Braseiros redundante dentro da região e dá teleporte livre entre Locais. Isso contraria "Desbravar atua sobre o Local atual; não existe exploração remota" (GDD §18.3, linha 1045) e esvazia o valor de descobrir Braseiros.

**Mitigação.** Recomendação qualitativa: não adotar 6A sem decidir o papel da Travessia. 6B (manter rotas gratuitas, sem encontro) não cria farm e preserva o valor dos Braseiros. Se o autor quiser 6A, definir se há custo (tempo ou Vigor) e qual o papel da Travessia na região.

---

## 10. A9 — Ritmo de encontros e Variantes

**Veredito: OK.**

**Evidência.**

- "Variante não altera Categoria, multiplicador-base de XP ou loot-base" (v1.0.17 §10.6). Variante só muda status (Furioso, Resistente, Ágil, Hemorrágico, Venenoso). Logo, as chances 8/10/12/15% não aumentam loot nem XP por hora.
- Encontros por hora: limitado por duração do combate e por Vigor. Pagamento só com Vigor (2 em Caçada, 4 em Desbravar). Estoque de 100 Vigor e regeneração 4,17/h (A1).
- Ganho único de Variante: BKP "Variante descoberta 8 + primeira vitória 6" (GDD §49), marco único por Variante. Mais Desbravar acelera esse ganho, mas ele é finito.
- Erro de texto: a faixa citada na proposta está errada (E3).

**Mitigação.** Nenhuma regra. QA: confirmar que a Variante não cria entrada extra de Saque.

---

## 11. Conflitos com a Fonte Mestra além dos citados no aviso da proposta

A proposta avisa que remover recarga e limite por hora contraria a Fonte Mestra (GDD §49.15, linha 4139). Outros pontos da Fonte Mestra afetados e não citados:

1. GDD §18.3, linha 1119: Desbravar "pode revelar um Local **conectado** ao Local atual, mas a descoberta não ignora gates de acesso, não teleporta e não ignora requisitos de nível". "Local novo" revela Local qualquer, sem conexão, e sem nível.
2. GDD §18.3, linha 1045: "Não existe exploração remota de outro Local no lançamento." A Pendência 6A a contraria.
3. GDD §49.15, linha 4113: Faixas das Masmorras A e B por Região (A5).
4. GDD §49.7: meta de Exploração 7-9% (A3) e "descoberta 100%" sem fator por nível (A3, opção C).
5. GDD linha 845: "Missões Principais de alto nível" com requisito de nível (A5).

`SOURCE_AUTHORITY.md` diz que Fonte Regional não sobrescreve regra global. O override registrado pelo autor precisa listar todos esses itens, não só a recarga.

---

## 12. Decisões que o autor precisa tomar

Cada item traz opções e uma recomendação. Nenhum número novo foi inventado: onde o valor falta, a decisão é do autor.

- **D1. XP de "Local novo" e de descobertas únicas para jogador de nível baixo (A3).**
  Opções: A aceitar (Exploração 11,11%); B XP igual por qualquer via, inclusive Missão; C limitar nível de referência ao nível do personagem; D "Local novo" sem XP.
  Recomendação: B, e registrar a banda de Exploração como 11,11% aceita ou ajustar o alvo global.
- **D2. XP da Câmara do Poente (Pendência 3).** Resolvido por fórmula: 1.264 (8% de 15.800). Autor só confirma.
- **D3. Quem recebe "Local novo" primeiro: ordem dos alvos (Pendência 2).**
  Opções: A sorteio uniforme; B pesos por alvo; C excluir a Câmara dos alvos (continua revelada por P6).
  Recomendação: A ou C. A Câmara revelada cedo é decisão narrativa.
- **D4. Modelo do resultado "Local novo" (E4/ambiguidade).** Um resultado de peso 50 com sorteio de alvo, ou quatro resultados. Recomendação: um resultado de peso 50 (mantém os 4%/8%).
- **D5. Anti-spam técnico (Pendência 1).** Atraso mínimo (recomendação da proposta) ou janela. Valor é do autor. Definir também limite de tentativas abertas por personagem.
- **D6. Nível mínimo das Masmorras (A5).** Manter um mínimo individual (qual valor, o autor decide) ou remover como na proposta. Recomendação: manter.
- **D7. PowerlevelFactor sobre XP fixa de Missão em Coop de Chefe (A5).** Aplica ou não. Recomendação: aplicar.
- **D8. Encontros de Missão por elegibilidade (S4, S5) para nível abaixo do unlock (A5).** Fixar nível e criatura como P2, ou exigir nível mínimo da criatura.
- **D9. Bestiário: BKP de "investigação Desbravar" e de "Habitat" por Desbravar repetível (A1).** Confirmar marco único por criatura/Local.
- **D10. Pendência 4 (nível efetivo e unlock).** Recomendação: A (manter `min(player_level, max_enemy_level)` e unlock). Não adotar B.
- **D11. Local com pool de Caçada vazio ou quase vazio (A5, A6).** Texto de UI e regra mínima (por exemplo, exigir ao menos uma criatura Comum elegível para abrir Ronda).
- **D12. Pendência 6 (deslocamento).** Recomendação: B (manter rotas). Se A, definir papel e custo da Travessia.
- **D13. Pendência 5.** Confirmar a remoção das travas de nível citadas por extensão. Recomendação: aceitar, desde que D6, D8 e D11 sejam resolvidos.
- **D14. Override da Fonte Mestra (Pendência 7).** Deve listar os cinco itens da seção 11, não só a recarga.
- **D15. Correção documental.** Corrigir E2 (prioridade de recovery por Local), E3 (Variantes 8/10/12/15%), E5 e E9 antes da consolidação em FINAL.

---

## 13. Limites desta auditoria

- Não rodei simulador de combate: taxa de vitória de Nv.1-3 contra encontros fixos e Masmorras está marcada como medição pendente (QA).
- Tempos por tentativa e por combate são suposições ilustrativas, sinalizadas no texto. A fonte só define 3 min por encontro na Ronda.
- A simulação de A4 considera o jogador na Estrada, sem deslocamento. O resultado depende da Pendência 6.
- Não li o código (`src/`): nada aqui afirma como o programmer implementaria; só compara documentos.

---

# Revisão 2 — 2026-11-14

**Autor:** systems-designer.
**Alvo:** proposta v1.0.18, revisão 3 (seções 0, 2, 3, 6, 7.0, 8, 11).
**O que mudou desde a seção anterior (decisões do autor, 2026-11-14):** nível do inimigo é o do Local (sai `min(player_level, max_enemy_level)`); todo Local, Câmara inclusive, só por Explorar; Missão não revela Local; Refúgio do Ocaso é hub (ida e volta grátis); leitura sugerida (decisão 22, não aprovada): Explorar é ação própria do Refúgio, sem Vigor, anti-spam de 3 s, e "Local novo" sai de Desbravar.
**Método:** contas em Python sobre `XP(n)` (GDD §49.7), leitura de `combat_math.py` (somente leitura) e conferência do GDD. Não alterei `src/`, `alembic/` nem `SOURCE_AUTHORITY.md`.

Termos: **LevelFactor** = multiplicador do XP de inimigo pela diferença entre nível do inimigo e do jogador (GDD linha 3738). **PowerlevelFactor** = corte de XP de quem é carregado por veterano em Grupo (GDD linha 3740). **Teto** = todos os Locais descobertos com nível >= referência. **Piso** = os quatro Locais descobertos no Nv.1.

## R2.1 Tarefa 1 — XP de exploração (ajuste aplicado na proposta)

**Problema.** Meta de Exploração única: 7% a 9% de 97.800 XP, ou seja `6.846` a `8.802 XP` (GDD §49.7). Valores da proposta na revisão 3: Grandes `5.560`, Menores `1.489` (juntas `7.049 = 7,21%`) mais XP de "Local novo" a 8% da referência (`616 + 800 + 1.136 + 1.264 = 3.816`). Total no teto `10.865 = 11,11%`, piso `8.585 = 8,78%`.

**Efeito das regras novas.** O XP de Local agora só vem de Explorar. Explorar grátis e repetível não cria XP extra, porque o XP é pago uma vez por Local e só há 4 Locais. Então o total depende só do percentual, não do custo nem da chance de Explorar. O que Explorar grátis muda é o piso: um Nv.1 revela os quatro Locais em segundos, sem risco, e colhe o XP do `min()` (`384` por Local a 8%, `1.536` no total, 32% do Nv.1→2).

**Conta (Python).** O orçamento para Locais no teto de 9% é `8.802 − 7.049 = 1.753 XP`. A soma das referências é `XP(4)+XP(6)+XP(9)+XP(10) = 7.700+10.000+14.200+15.800 = 47.700`. Percentual máximo que cabe: `1.753 / 47.700 = 3,67%`.

| Percentual de Local | Locais no teto | Total no teto | % | Total no piso | % no piso | Cabe em 7-9% |
|---|---:|---:|---:|---:|---:|---|
| 8% (proposta) | 3.816 | 10.865 | 11,11% | 8.585 | 8,78% | não (teto) |
| 4% | 1.908 | 8.957 | 9,16% | 7.817 | 7,99% | não (teto) |
| 3,5% | 1.670 | 8.719 | 8,92% | 7.721 | 7,89% | sim, rente ao teto |
| 3% | 1.431 | 8.480 | 8,67% | 7.625 | 7,80% | sim |
| **2,5% (escolhida)** | **1.193** (193+250+355+395) | **8.242** | **8,43%** | **7.529** (4 × 120 + 7.049) | **7,70%** | **sim** |
| 0% | 0 | 7.049 | 7,21% | 7.049 | 7,21% | sim |

**Opção escolhida: XP de Local a 2,5% em vez de 8%, `min()` mantido.** Motivos: (1) é o menor ajuste de texto: troca um percentual; (2) 2,5% não é número inventado, é o percentual que a proposta já usa nas Descobertas Menores; (3) o teto fica em 8,43% e o piso em 7,70%, os dois dentro da meta, sem o autor ter de aceitar banda fora dela (a decisão 20 da proposta perde o objeto); (4) mantém a decisão 9.10 do autor (Local novo paga XP); (5) o piso do Nv.1 cai para `480` (10% do Nv.1→2), aceitável para uma ação grátis.

**Alternativas.**
- **B. Local sem XP (0%).** Total `7.049 = 7,21%`. A mais simples e segura, mas contraria a decisão 9.10 e deixa Explorar grátis sem recompensa nenhuma.
- **C. 3% (ou 3,5%).** Total `8.480 = 8,67%` (ou `8.719 = 8,92%`). Cabe, mas usa percentual novo sem fonte e deixa pouca folga para qualquer descoberta única futura.
- Manter 8% e estender o `min()` às 7 Grandes e 6 Menores (decisão 19) não resolve: o teto continua 11,11%.

**Ressalvas.** (a) O `min()` só limita o piso; o teto depende só do percentual. (b) A Câmara (referência 10) paga `395` no teto. (c) Missão não paga XP de descoberta, então o total de Missão não muda (`59.085 / 97.800 = 60,4%`).

**Onde apliquei na proposta** (todas com a marca "[SUGESTÃO systems-designer — aguarda aprovação do autor]"): §3.1 (bloco XP de descoberta), §3.2 (nota de XP), §3.5 (totais e conta), seção 2 (XP de descoberta pela Missão), seção 6 (§24.1 e §24.7), seção 8.2 (item 3), critérios 2, 3, 4 e 19. **Não editei** (fora do pedido) e ficam desatualizados: seção 9(a) item 5 (cita `8,78%-11,11%` e `8%`), changelog item 6 (cita `8%`), seção 7.2 (primeiro item cita `8,78%-11,11%`), seção 7.3 A3 (cita `10.865`), seção 8.3 decisões 19 e 20 (citam `3.816`, `1.536` e a banda), e a última lista de §3.5 ("só se não foi descoberto antes por Missão"). O game-designer ou o autor precisa varrer esses trechos depois da aprovação.

## R2.2 Regra global de nível de inimigo no GDD (precisa entrar no override 9a?)

Achados na Fonte Mestra (`ASTERION_GDD_Estrutural_v1.6.0_Fonte_Mestra.md`):

1. **Linha 895 (Caçada), Solo.** "Em Solo, o `enemy_level` continua seguindo a regra regional/configurada da criatura." Em Solo o GDD delega à Fonte Regional; a decisão P4 não conflita com a Fonte Mestra.
2. **Linha 895, mesma linha, Grupo.** Em Grupo vale regra global: `encounter_reference_level = maior nível atual entre os participantes válidos`; `enemy_level = min(encounter_reference_level, max_enemy_level_da_criatura)`; a entrada só é elegível quando todos os participantes cumprem o unlock individual; nível congelado no `encounter_id`. **Isto conflita com "nível do Local" em Grupo** e não está no override 9a: o item 7 da seção 9a fala do nível "do Local/região" sem dizer o que acontece em Grupo.
3. **Linhas 3884-3889 (Saque).** `loot_reference_level = enemy_level` em Caçada e em combate econômico de Desbravar; em Masmorra `loot_reference_level = dungeon_reference_level`; `item_level = loot_reference_level`. Com P4, Saque e Coroas seguem o nível do Local, não do jogador. Não exige override, mas muda a conta de A5/A6.
4. **Linhas 3738 e 3740 (XP).** LevelFactor (`>=+5 = 110%`, `+3/+4 = 105%`, `-2..+2 = 100%`, `-3..-5 = 80%`, `-6..-10 = 50%`, `-11..-20 = 20%`, `<=-21 = 5%`) e PowerlevelFactor (`100/70/45/20/5%` para diferença `0-10 / 11-15 / 16-20 / 21-30 / 31+`) já existem e valem sem override. Não há outra regra global de nível de inimigo (busquei `enemy_level`, `max_enemy_level`, `loot_reference_level`, `LevelFactor`, `PowerlevelFactor`).
5. **Linha 3689 (atributos).** `EnemyStat` usa `K_A(level)`: a força do inimigo depende de `enemy_level`. Sem conflito.
6. **Texto herdado na v1.0.17.** §10.1 (linha 1909) e o resumo da linha 3683 ("max level limita enemy_level = min(player_level, max_enemy_level)"). Os dois precisam ser reescritos na consolidação em FINAL.

**Conclusão para o override 9a (só relato, não editei):** o item 7 precisa dizer (i) o que vale em Grupo (nível do Local, ou a regra global da linha 895) e (ii) o que acontece com o `unlock_level` individual em Grupo. Sem isso, Solo e Grupo ficam com regras diferentes.

## R2.3 Nível do Local: lacuna que trava as contas

A proposta (seção 4) deixa em aberto qual número é o "nível do Local" (decisão 18). Opções com números que já existem na fonte:
- **1. `max_enemy_level` de cada criatura** (v1.0.17 §10.2-§10.5): Estrada 3-5, Charneca 3-7, Bosque 6-9, Ruínas 8-10. É o que melhor bate com a fala do autor ("Local Nv.9-10").
- **2. `reference_level` do Local** (Charneca 4, Bosque 6, Ruínas 9). Não existe para a Estrada: precisa número do autor.
- **3. `unlock_level` de cada criatura:** Estrada 1-3, Charneca 1-4, Bosque 3-6, Ruínas 5-9. Mais suave, mas não bate com "Local Nv.9-10".

**Recomendação: opção 1.** O autor decide. As contas abaixo usam nível de inimigo 9 e 10 para as Ruínas.

## R2.4 A3 — XP e vitória de Nv.1 em Local alto

**XP por vitória (Python, GDD §49.7).** `EnemyXPUnit(n) = XP(n) / (20 × H(n))`. Jogador Nv.1; LevelFactor pela diferença.

| Inimigo | Unidade | Nv.1 recebe | % do Nv.1→2 (4.800) |
|---|---:|---:|---:|
| Comum Nv.1 (mesmo nível, 100%) | 240 | 240 | 5,0% |
| Comum Nv.4 (diferença +3, 105%) | 300 | 320 | 6,7% |
| Comum Nv.9 (diferença +8, 110%) | 405 | 450 | 9,4% |
| Elite Nv.9 (Custódio do Poente, categoria 2,75, 110%) | 405 | 1.230 | 25,6% |

**Pode vencer? (indicativo, não é simulação).** Usei `class_stats(classe, 1)` e `enemy_stats(nível)` de `combat_math.py`, golpe básico (coeficiente 1,0) dos dois lados, inimigo "neutro" (sem multiplicador de categoria, arquétipo ou Variante), sem Artes, consumíveis nem crítico. Razão `r` = (golpes que o inimigo precisa para matar o jogador) / (golpes que o jogador precisa para matar o inimigo). `r >= 1`: o jogador ganha. `r < 1`: perde. Média das 6 classes (mínimo e máximo ficam a 0,05 da média):

| Nível do inimigo | r com jogador Nv.1 | r com jogador Nv.2 |
|---:|---:|---:|
| 1 | 1,00 | 1,07 |
| 3 | 0,86 | 0,93 |
| 4 | 0,80 | 0,86 |
| 5 | 0,74 | 0,80 |
| 6 | 0,69 | 0,74 |
| 8 | 0,60 | 0,65 |
| 9 | 0,56 | 0,60 |
| 10 | 0,52 | 0,56 |

Leitura: o combate está no equilíbrio quando os níveis são iguais. Nv.1 contra Nv.9-10 tira só cerca de 52-56% do HP do inimigo antes de morrer num duelo de golpes básicos. Solo, derrota provável; só Artes, consumíveis, Variante favorável ou sorte mudam isso. **Taxa de vitória real continua pendente (QA).** A tabela também mostra que a Estrada com `max_enemy_level` (Nv.3-5) já é dura para um Nv.1 recém-saído de P1 (`r` 0,74 a 0,86); o autor deve conferir o início.

**Veredito A3 (novo): de RISCO alto para OK com o ajuste de R2.1.** Razões:
- O furo antigo ("Nv.1 colhe 3.816 XP sem combate") fecha em duas frentes: o XP de Local cai para 480 no Nv.1, e o combate de Desbravar agora tem inimigo de nível do Local (antes o pool de Bosque e Ruínas ficava vazio no Nv.1 e a exploração era sem risco). Com P4, Desbravar em Local alto tem 25% de chance de combate contra inimigo muito acima do nível. A exploração das 7 Grandes e 6 Menores passa a ter risco real.
- O XP por vitória de Nv.1 contra Nv.9 é 1,9 vez o do Nv.1 contra Nv.1 (450 contra 240), com taxa de vitória quase pela metade. Sem ganho desproporcional por Caçada solo.
- Resta risco em Grupo (R2.5).

## R2.5 A5 — Remoção de travas sob nível do Local

1. **Equipamento de Campanha:** sem mudança, OK (regra global de equipar).
2. **Encontros fixos de Missão** (Aranha Nv.3, Peregrino Nv.4, Cervo Nv.5, Vigia Rachado Nv.7, Custódio Nv.9, Guardião Nv.10, Vigia Partido): já eram fixos; sem mudança. Em Solo, a vitória de um Nv.1 segue a tabela de R2.4 (`r` 0,52 a 0,86): a barreira é a dificuldade, não uma regra.
3. **Masmorras (BLOQUEIO parcial, mantido).** O `loot_reference_level` já era `dungeon_reference_level` (6 e 9), fixo; P4 não muda. O risco de carona continua: Nv.1 + veterano até 10 níveis acima, PowerlevelFactor 100%, 6.640 XP na Cripta Estável. Mantenho a recomendação de um mínimo individual (decisão 6).
4. **S4/S5 (decisão 8).** O fallback só existe por causa do `unlock_level`. Se o `unlock_level` sair, a decisão 8 some (qualquer criatura é elegível, no nível do Local). Se ficar, o bloqueio continua.
5. **Pool vazio por unlock (A5 item 6).** Também some se o `unlock_level` sair.
6. **Coop de Chefe (decisão 7):** inalterada.
7. **Coop de Caçada (novo, importante).** Hoje a linha 895 do GDD protege o Grupo pelo unlock individual: a entrada só é elegível se todos cumprem o requisito. Um Nv.1 em Grupo com um Nv.10 enfrenta só Cão e Corvo (unlock 1). Se o `unlock_level` sair (decisão 18), um Nv.1 em Grupo nas Ruínas recebe, por Comum Nv.9, 450 XP (9,4% de um nível) com PowerlevelFactor 100% (diferença menor que 10); por Elite, 1.230 XP (25,6%); Coroas `0,05 × C(9) = 12` por vitória (o dobro de `0,05 × C(1) = 6`); e Equipamento de `item_level 9`. É carona de XP e Saque de nível alto sem barreira.

**Veredito A5 (novo): BLOQUEIO parcial mantido (mínimo individual de Masmorra; decisão 18 sobre `unlock_level`), mais risco alto de carona em Coop de Caçada se o `unlock_level` sair por completo.**

**Recomendação para a decisão 18 (autor decide):** manter o `unlock_level` **só como requisito individual de Grupo** (como a linha 895 já escreve) e abrir Solo por completo. Efeitos: Solo é soulslike puro (Nv.1 entra, enfrenta, provavelmente perde); Grupo continua sem carona e sem número novo; as decisões 8 e 11 passam a valer só em Grupo. Alternativa: tirar o `unlock_level` por completo e aceitar a carona (não recomendo).

## R2.6 A6 — Ronda em Local alto e farm

1. **Ronda exige a primeira vitória manual no Local.** Nv.1 solo em Ruínas (`r` 0,56) dificilmente vence a primeira, então Ronda alta fica fora do alcance de Solo baixo. Em Grupo, a proposta não diz se a vitória conta para quem não deu o golpe final. Pendente.
2. **Ronda para com Vigor < 2.** 100 Vigor dão 50 encontros (GDD §17). O teto de ganho por Vigor é o mesmo da auditoria anterior.
3. **Farm por Local.** O nível do inimigo é fixo, então a recompensa por Vigor sobe com o Local (Coroas `0,05 × C(nível)`: Estrada Nv.4 = 8, Ruínas Nv.9 = 12 por Comum) e o jogador só sobe quando aguenta. É a progressão pretendida, sem laço de recurso novo.
4. **Jogador de nível alto em Local baixo.** O inimigo não escala: Nv.10 na Estrada enfrenta Nv.3-5. LevelFactor `-5..-7` dá 80% ou 50% do XP, e Coroas/Saque ficam no nível do inimigo (8 por vitória contra 12,5 do nível 10). A Estrada não vira atalho de farm.
5. **Pool afinado.** O ganho de "Bosque Nv.3 só com Aranha" (+25% XP, +41% Coroas, +57% Materiais, tabela da auditoria anterior) depende do `unlock_level`. Se o Solo abrir (recomendação), ele some e o pool completo vale desde o primeiro acesso (57% Comum, 40% Incomum, 3% Elite; +14% XP, +25% Coroas, +9% Materiais sobre a Estrada de mesmo nível).
6. **Hub.** Caçar parte do Refúgio com escolha de Local, sem custo. Trocar de Local custa 0, mas a recompensa é por Vigor, e o Vigor é o freio. Nenhum risco novo de economia.

**Veredito A6 (novo): RISCO baixo** (antes: baixo a médio). Depende da decisão 18 e da definição de "vitória manual válida" em Grupo.

## R2.7 Decisão 23 — risco de travar P2, P3, P4 e P6 no sorteio

Depende da leitura de Explorar (decisão 22):

- **Leitura 0.7 (Explorar só revela Local; "Local novo" sai de Desbravar).** Cada clique revela um Local ainda não descoberto (sorteio uniforme). Com 4 alvos, são no máximo 4 cliques (12 s a 3 s por clique) e, para um Local específico, 2,5 cliques em média (posição esperada de um alvo numa permutação de 4). Explorar é grátis e não falha. **Não há risco real de travar.** A proteção de 3 tentativas é desnecessária e nem cobre o pior caso (4 cliques).
- **Leitura inversa ("Local novo" continua dentro de Desbravar, 4% a 8% por tentativa).** A média para um Local específico é de 41 tentativas (P90 = 79-80). O risco é real.
- **Se Explorar puder falhar,** vale o mesmo cálculo: média de `1/chance` cliques por Local.

**Parecer sobre a proteção de 3 tentativas (opção B da seção 2).**
1. Na leitura 0.7, não adotar: é regra extra sem problema a resolver.
2. Nas leituras com falha, a proteção existente (até 3 tentativas para objetivo obrigatório) só funciona se **forçar o alvo da Missão**. Com sorteio uniforme entre os não descobertos, 3 tentativas não garantem o Local pedido. Forçar o alvo é, na prática, a Missão revelar o Local depois de 3 cliques, o que fere o espírito de "Missão não revela Local" (R3-1). O autor decide se aceita.
3. Pontos de borda para o texto: (a) quem já descobriu tudo não tem mais o que Explorar, e a UI precisa dizer isso; (b) a Câmara revelada cedo (spoiler, narrative-designer); (c) o aviso "explore para achar o Local" não pode virar bloqueio sem saída.

**Recomendação.** Se Explorar revela a cada clique: decisão 23 = aceitar sem proteção. Se o autor quiser que Explorar possa falhar: aprovar a proteção B **com alvo forçado**, deixando claro que é exceção a "Missão não revela Local".

**Efeito colateral.** Com Explorar grátis e sem falha, um Nv.1 revela Ruínas e Câmara em segundos. Isso só é seguro porque a barreira passa a ser o combate (R2.4) e o Grupo (R2.5). A descoberta deixa de ser um jogo e vira um menu. O custo é de apresentação, não de economia.

## R2.8 Decisões que o autor ainda precisa tomar

1. **Aprovar o XP de Local a 2,5%** (R2.1): 8,43% no teto, 7,70% no piso. Alternativas: 0% (7,21%) ou 3% (8,67%).
2. **Decisão 18, nível do Local:** opção 1 (`max_enemy_level`), 2 (`reference_level`, falta número da Estrada) ou 3 (`unlock_level`). Recomendação: 1, conferindo o início da Estrada para um Nv.1.
3. **Destino do `unlock_level`:** recomendação = só requisito individual de Grupo, Solo aberto. Alternativa = sai por completo (aceitar carona).
4. **Regra de nível em Grupo** (override 9a item 7): nível do Local ou regra da linha 895 do GDD.
5. **Decisão 6 (mínimo individual de Masmorra):** manter (recomendação).
6. **Decisão 7 (PowerlevelFactor em XP fixa de Missão em Coop):** aplicar (recomendação).
7. **Decisão 22 (Explorar):** revela a cada clique, sem falha (recomendado) ou com chance; Vigor 0 e anti-spam de 3 s.
8. **Decisão 23:** aceitar sem proteção (se Explorar nunca falha) ou aprovar a proteção com alvo forçado.
9. **"Vitória manual válida" em Grupo** para liberar Ronda: conta ou não para quem não deu o golpe final.
10. **Varredura dos trechos com números antigos** (lista no fim de R2.1), depois da aprovação.

## R2.9 Limites desta revisão

- A tabela de `r` é indicativa: golpe básico, inimigo neutro, sem Artes, categoria, Variante ou consumíveis. Taxa de vitória real exige simulação de combate (QA).
- Tempo por clique e por combate continuam suposições (a única fonte é 3 min por encontro na Ronda).
- Li só `combat_math.py` no código, para as curvas; nada afirma como o programmer implementaria.

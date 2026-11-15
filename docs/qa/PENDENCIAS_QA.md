# Pendências de QA

Lista de medições e verificações que o QA ainda deve fazer. Cada item diz o que medir, o limite, como medir e o que bloqueia.

## QA-001. Taxa de vitória real do Nv.1 (TDO v1.0.18)

- **Registrada em:** 2026-11-14
- **Estado:** MEDIDA em 2026-11-15 (bloco B no código, ainda não commitado). Números abaixo. Sem limite de aprovação definido pelo autor: o QA só reporta, não aprova nem reprova. A decisão sobre dureza fica com o autor.
- **Tamanho da amostra (decisão do autor, 2026-11-15):** 1.000 lutas por classe e por caso, semente fixa.
- **Fontes:**
  - `docs/specs/AUDITORIA_FARM_XP_TDO_v1.0.18_2026-11-14.md` (tabela `r`, R2.4). A PROPOSTA v1.0.18, que tinha a seção 7.4, foi apagada em 2026-11-14; o conteúdo vale pela FINAL.
  - `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_FINAL.md`, §33.15, lacuna L6.

### O que medir

Taxa de vitória real (não a razão indicativa `r`) do personagem Nv.1 em dois pontos:

1. **(a) Estrada logo após a P1.** Inimigo no nível do Local (`max_enemy_level` 3 a 5). `r` indicativa: 0,74 a 0,86 (jogador perde na média; pode estar dura demais para o início). Medir por classe, com e sem Artes e consumíveis de P1.
2. **(b) Locais Nv.9–10 (Ruínas), Nv.1 solo.** `r` indicativa: 0,52 a 0,56; derrota provável em Solo. Confirmar se é a barreira pretendida (soulslike) e se Caçada/Desbravar não paga XP desproporcional a quem ganha por sorte. Referência da seção 7.4: Comum Nv.9 = 450 XP (9,4% do Nv.1→2); Elite Nv.9 = 1.230 XP (25,6%).

A tabela `r` da auditoria (R2.4) é só indicativa: golpe básico, inimigo neutro, sem Artes, Variante ou consumíveis.

### Critério / limite de aprovação

**LACUNA.** A seção 7.4 e a L6 dizem "sem número de aprovação definido pelo autor". Não há limiar de taxa de vitória. O QA mede e reporta os números; não aprova nem reprova sem o autor definir o limite. Se o caso (a) mostrar dureza excessiva, a correção é decisão do autor (a fonte não propõe número).

### Como medir (quando houver código)

- Simulação de combate com o motor real do jogo (não a fórmula indicativa), Nv.1, por classe.
- Caso (a): com e sem Artes e consumíveis de P1.
- Caso (b): Solo, Nv.1, inimigos Comum e Elite do Local Nv.9–10; registrar também o XP pago em vitória.
- Número de amostras: **LACUNA**, a fonte não define. Propor um tamanho ao autor antes de rodar e fixar semente/crítico para o resultado ser reproduzível.
- Reportar: taxa de vitória por classe e por caso, XP por vitória, e a comparação com as `r` indicativas.

### Resultados (2026-11-15)

Motor real: `domain.combat.act` com `create_road_combat`. Script em scratchpad (fora do repositório), `qa001_sim.py`, semente base `qa001-2026-11-15` (combate = `uuid5` da semente; criatura e Variante sorteadas por `weighted_choice`/`select_variant` reais). Nv.1, raça Remanescente, HP cheio, arma inicial Comum +0 Grau I da Classe (kit pós-spec de Proficiências: só a arma). 1.000 lutas por classe e por linha. 0 estouros de limite de turnos.

**Suposições (documentadas porque o motor não define política de jogador):**
- "Sem Artes": só Atacar (e Defender quando o inimigo prepara golpe). "Com Artes": a Arte Nv.1 da Classe equipada; usa-se a Arte sempre que fora de recarga, senão Atacar.
- P1 não entrega Consumível (só Ferro, Couro Escoriado, XP e Coroas). "Consumíveis" = hipótese: 3 Poções de Cura (`consumable.heal`, 22% do HP) usadas quando HP < 40%.
- Defender só quando há golpe preparado. Sensibilidade (300 lutas, sem nunca Defender): diferença de até 3 pontos percentuais; os números abaixo não dependem dessa regra.
- Caso (b): "Comum" = Carniçal de Fuligem Nv.8 e Vigia Rachado Nv.10 (pesos reais do pool); "Elite" = Custódio do Poente Nv.10 (única Elite do Local). Não existe Comum Nv.9 no pool das Ruínas.
- XP = `enemy_xp(nível_inimigo, categoria, player_level=1)` com Vigor cheio; não inclui bônus de primeira observação.

**Caso (a): Estrada pós-P1, Nv.1, pool inteiro (Cão Nv.3, Corvo Nv.4, Peregrino Nv.5, Alfa Elite Nv.4). Taxa de vitória:**

| Classe | Sem Artes | Com Artes | Com Artes + 3 Poções |
|---|---|---|---|
| Sentinela | 96,3% | 96,3% | 96,4% |
| Errante | 96,6% | 96,6% | 96,6% |
| Vigia | 96,9% | 96,9% | 96,9% |
| Tecelão | 97,0% | 97,4% | 97,4% |
| Oráculo | 97,1% | 97,1% | 97,1% |
| Luminar | 97,5% | 97,6% | 97,6% |

Por criatura (Com Artes, 6 classes somadas): Cão, Corvo e Peregrino 100%; Alfa Cinéreo (Elite Nv.4, 3% do pool) 0%, todas as classes. A taxa geral é 100% menos o peso do Alfa. XP por vitória: Cão 280, Corvo 320, Peregrino 340 (média ~312 por vitória no pool; Alfa Elite Nv.4 valeria 870, nunca vencido). `r` indicativa 0,74 a 0,86 previa derrota na média; o motor real dá vitória quase certa contra Comum.

**Caso (b): Ruínas, Solo Nv.1. Taxa de vitória (XP por vitória entre colchetes):**

| Classe | Comum sem Artes | Comum com Artes | Elite (Custódio Nv.10) |
|---|---|---|---|
| Sentinela | 7,5% | 30,4% | 0% (sem XP) |
| Errante | 68,5% | 98,5% | 0% |
| Vigia | 95,9% | 99,9% | 0% |
| Tecelão | 86,6% | 99,0% | 0% |
| Oráculo | 52,0% | 100,0% | 0% |
| Luminar | 18,3% | 57,0% | 0% |

XP por vitória Comum: 420 (Carniçal Nv.8) ou 470 (Vigia Rachado Nv.10); média 421 a 450 conforme a Classe. Elite: 0 vitórias em 12.000 lutas (6 Classes x 2 políticas x 1.000), logo nenhum XP pago; se vencida, `enemy_xp(10, elite, player_level=1)` = 1.290 (referência da §7.4: 1.230 no Nv.9). Referência Comum Nv.9 = 450 (9,4% do Nv.1 a 2). `r` indicativa 0,52 a 0,56 (derrota provável): o motor real dá derrota quase certa só contra Elite e para Sentinela/Luminar; Vigia, Tecelão, Errante e Oráculo vencem o Comum com Artes em 98 a 100%.

**Pontos para o autor:** (1) Estrada Nv.1 não está dura demais contra Comum; só o Alfa Cinéreo (Elite) é intransponível. (2) Ruínas Nv.1 Solo: Comum vencível por 4 de 6 Classes, Elite impossível; XP por vitória ~420 a 470 sem proporcionalidade com a chance (Comum Nv.1 rende 240). Dureza por Classe muito desigual (Sentinela 30%, Vigia 100%). Isso é resultado do motor, não defeito do bloco B.

## QA-002. Bloco A da TdO v1.0.18: Caçada em Local descoberto só por Explorar

- **Registrada em:** 2026-11-14
- **Estado:** CORRIGIDA e revalidada em 2026-11-15 (sonda sem xfail, lote 265 passed, 1 skipped, ruff limpo). Restam os itens do bloco D abaixo.
- **Critério:** §33.16 item 12 e §33.16 item 5 (Local descoberto tem Caçada sem Missão).
- **Evidência:** `tests/test_tdo_hub_qa_probe.py` (xfail strict). Charneca, Bosque e Ruínas descobertos por `LocationDiscovery` sem P2/P3/P4: `RoadService.start_hunt` devolve `None`. Causa: `_available_local_profile` em `src/asterion/application/road.py` (~linha 5437) ainda exige P2/P3/P4 concluídas e Nv.8 nas Ruínas.
- **Bloqueia:** fechar o bloco A. Tirar o `xfail` ao corrigir.
- **Também aberto (bloco D):** botões de Missão (P4, P5, P6, S2) com `road:route:*` Local–Local ficam mortos; P6 legada ainda grava `LocationDiscovery` da Câmara (`application/p6.py` linhas 173 e 183), contra §33.16 item 18.

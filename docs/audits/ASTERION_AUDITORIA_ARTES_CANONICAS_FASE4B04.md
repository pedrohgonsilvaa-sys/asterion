# Asterion — Auditoria das 84 Artes Canônicas · Fase 4B-04

**Natureza:** auditoria somente leitura do checkout local. Nenhum código, teste, fonte oficial ou número de balanceamento foi alterado nesta fase.

## A. Resumo executivo

O GDD v1.6.0 define 36 Artes de Classe e 48 Artes de Caminho. O checkout contém definições executáveis para **26/84**: as 24 Artes de Classe de Nv.1/4/7/9, Firmeza e Aríete. A leitura das definições confirma os valores publicados para essas Artes, mas não há prova de conformidade PostgreSQL arte por arte para as 24 Artes iniciais. Firmeza e Aríete têm evidências de validação focal nas fases anteriores; esses resultados são históricos, não foram repetidos aqui.

### Contagem exclusiva por estado

| Estado primário | Quantidade | Definição usada nesta auditoria |
|---|---:|---|
| Implementada e validada (evidência histórica focal) | 2 | Firmeza e Aríete têm fluxo de catálogo/configuração/combate/UI e teste focal PostgreSQL reportado em tarefa anterior. Não houve nova execução nesta auditoria. |
| Implementada sem validação suficiente | 24 | As quatro Artes iniciais de cada Classe estão registradas e têm ação real no motor. Há testes de Classe/combate, mas não há validação recente e completa de cada contrato individual em todos os modos. |
| Parcialmente implementada | 0 | Não foi classificada uma Arte com execução parcial identificada; a ausência de uma Arte inteira não foi contada como parcial. |
| Apenas declarada | 11 | Os nomes aparecem na copy estática de criação de Classe, mas não têm ID de Arte, definição ativa ou ação executável no runtime. |
| Ausente | 47 | As demais Artes de Caminho não têm definição/ação executável nem entrada no catálogo runtime. |
| **Total canônico** | **84** | 36 de Classe + 48 de Caminho. |

Assim, o runtime registra 25 Artes de Classe (das quais 2 têm evidência focal suficiente nesta classificação) e 1 Arte de Caminho. As 11 Artes de Classe sem runtime e as 47 Artes de Caminho sem runtime somam **58 Artes indisponíveis como ações de jogador**. O sistema já fornece uma fundação útil para slots, validação, snapshot e resolução, mas ainda não é um catálogo de 84 Artes.

Não há evidência de exploração econômica ou corrupção causada pelo estado atual das Artes; logo, nenhum achado P0 foi confirmado. A ausência de 58 Artes canônicas é uma pendência P1 de completude de lançamento. A falta de remoção de efeitos como efeito de Arte é uma lacuna confirmada do contrato compartilhado, necessária antes de implementar algumas Artes futuras.

## B. Autoridades, método e preservação

### Estado inicial do checkout

* Branch: `main`; HEAD de entrada: `4748add6dc079c6a7e785bbf9de6dd0af17cec0d`, igual ao esperado.
* Antes da criação deste relatório, havia exatamente dois arquivos tracked modificados e nada staged: `tests/test_tdo_full_playthrough.py` e `tests/test_vde_full_playthrough.py`.
* Também estavam untracked `.worktrees/` e `ASTERION_CONTEUDO_ALTOS_CINEREOS_v1.0.1_PROPOSTA.md`. Permaneceram intocados e fora do commit.
* `git status` reportou `Permission denied` para `.pytest_tmp/`; o diretório não foi aberto nem modificado.
* SHA-256 do GDD consultado: `0c9245861da2af8ed13944607f47b9122165d38e5a919f8b3dbaa668b65550aa`.

### Fontes verificadas

* `ASTERION_GDD_Estrutural_v1.6.0_Fonte_Mestra.md`: §§8, 49.1, 49.3, 49.4, 49.5, 55.3, 56 e 57. O GDD controla identidade, requisitos, níveis, potência, duração, cooldown e compatibilidade.
* `ASTERION_BIBLIA_CANONICA_MUNDO_REGIOES_BESTIARIO_NPCS_v3.0_FINAL.md`: SHA-256 verificado `f42484b09bff21712e8fb72d71d7eba3d19e0c3b4543a5b2d94adb1e7e864a15`.
* `ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.0.0_FINAL.md`: SHA-256 verificado `c283b398949dc0a864d98b9e0e9031080a50b937db6932ffcde7d46e600aa740`.
* `SOURCE_AUTHORITY.md` e `docs/SOURCE_AUTHORITY.md`: ambos selecionam GDD v1.6.0, Bíblia v3.0 FINAL e Contrato Weapon Metadata v1.0.0 FINAL. As duas cópias apontam a mesma autoridade; não há divergência de seleção que afete esta auditoria.

### Evidência inspecionada

Foram examinados os registros em `src/asterion/domain/arts.py`, as fábricas de ação em `src/asterion/domain/class_trials.py`, `src/asterion/domain/path_arts.py`, o serviço `src/asterion/application/active_arts.py`, modelo e migration de slots, validação de Caminho e Doutrina, codec/snapshot de Combate, handlers e telas Telegram, e os módulos de testes relacionados.

O código registra **25 IDs de Classe** e **1 ID de Caminho** em `ACTIVE_ART_DEFINITIONS`; `PATH_ART_ACTIONS` contém somente Aríete. `ART_IDS_BY_CLASS` cobre as quatro Artes iniciais por Classe e Firmeza para Sentinela. `PATH_ART_IDS_BY_PATH` cobre somente Aríete. Nomes na copy de criação não são considerados IDs, catálogo nem implementação.

**Testes nesta fase:** nenhum teste foi executado. Não se afirma aprovação PostgreSQL nesta auditoria. Evidências de fases anteriores são explicitamente históricas. Os playthroughs modificados foram inspecionados somente para preservar seu estado; não foram editados, adicionados ao staging ou incluídos no commit.

### Legenda da matriz

Cada linha traz o contrato canônico e o estado de todas as camadas.

* **R** — ID/definição no catálogo; gate por Classe/Caminho/nível; seleção limitada aos três slots; validação de configuração; elegibilidade de Doutrina; snapshot congelado; ação entregue ao motor; efeitos codificados; persistência via slots/codec; tela/handler Telegram. R confirma a existência desses componentes para a Arte, mas não significa que todos os casos de uso foram testados.
* **V-hist** — R, efeito conferido contra o GDD e evidência focal PostgreSQL histórica registrada em fase anterior; não executada novamente aqui.
* **D** — somente nome em `src/asterion/bot/creation_copy.json`; sem ID de runtime, configuração, execução, snapshot de ação, UI de ação ou teste da Arte.
* **A** — sem definição/ação/catalogação de runtime identificada; slots, desbloqueio, configuração, Doutrina, snapshot, execução, UI e testes da Arte não existem.
* `—` em arma/recurso significa que a fonte não declara requisito/custo próprio. “Alvo conforme contrato” aponta a distinção explícita entre inimigo, próprio, aliado e área indicada na linha.

**Ações universais, fora das 84:** Ataque Básico é 100% ATQ, Dano Direto a um inimigo, sem Recarga; Defender segue o contrato global de §49.1. Ambas são ações do motor compartilhado em `domain/combat.py`, e não são Artes/slots do catálogo. Testes de combate existentes exercitam essas ações, mas não foram executados nesta auditoria.

Os testes citados por módulo exercitam fábricas, serviços ou casos correlatos; salvo Firmeza/Aríete, não demonstram por si só cada porcentagem, duração, cooldown, alvo, requisito e integração de cada linha.

## C. Matriz individual das 36 Artes de Classe

### Sentinela

| Arte canônica (Nv.) | Contrato GDD: potência/ação, alvo, duração, CD, arma, recurso e interação | Runtime e ID | Testes/evidência e lacuna |
|---|---|---|---|
| Golpe de Guarda (1) | 110% ATQ, Dano Direto a um inimigo; duração —; CD2; melee compatível; sem recurso próprio. Retaliação geral só é consumida por ofensiva direta válida. | **R** `class_art.sentinela.golpe_de_guarda` | `test_sentinel_trial.py`, `test_class_trials.py`, `test_active_arts.py`; efeito configurado em `sentinel_player_actions`. Sem conformance PG isolada por todos os campos nesta auditoria. |
| Quebra-Postura (4) | 90% ATQ + −10% DEF no inimigo por 2T; CD3; melee compatível; sem custo próprio. | **R** `class_art.sentinela.quebra_postura` | Mesmos módulos de Sentinela; código registra dano, debuff, duração e CD. Falta teste de contrato completo isolado e transversal. |
| Muralha Breve (7) | Barreira própria de 70% ATQ por 2T; CD3; sem requisito de arma/recurso. Interage com as regras globais de Barreira e efeitos da Sentinela. | **R** `class_art.sentinela.muralha_breve` | `test_sentinel_trial.py`, `test_class_trials.py`, `test_talents.py`; código registra Barreira própria. Sem verificação focal PG de todas as regras de expiração/stacking por Arte. |
| Impacto Resoluto (9) | 135% ATQ, Dano Direto a um inimigo; CD3; melee compatível; Retaliação e efeitos de Caminho aplicáveis pelo motor global. | **R** `class_art.sentinela.impacto_resoluto` | `test_sentinel_trial.py`, `test_class_trials.py`, `test_class_mechanics.py`; não houve matriz de resultados por Classe/Caminho/armamento nesta auditoria. |
| Firmeza (18) | Buff próprio de +12% DEF por 2T; CD3; arma: nenhuma; não causa dano nem consome/concede Retaliação ou Ímpeto Doloroso. | **V-hist** `class_art.sentinela.firmeza` | `tests/test_firmeza.py` cobre desbloqueio, armas, slots, reconnect, Doutrina, Buff/expiração, UI e Retaliação. Resultado histórico reportado: bateria focal PostgreSQL e regressões da fase 4B-03C passaram; não repetido aqui. |
| Golpe de Rechaço (34) | 145% ATQ; com Retaliação +10 p.p. PER; Dano Direto a um inimigo; CD4; melee compatível; usa Retaliação conforme §56.2. | **D** sem ID de runtime | Nome apenas na copy da Sentinela em `creation_copy.json`; não há definição nem ação. Sem configuração, execução, persistência, UI funcional ou teste da Arte. |

### Errante

| Arte canônica (Nv.) | Contrato GDD: potência/ação, alvo, duração, CD, arma, recurso e interação | Runtime e ID | Testes/evidência e lacuna |
|---|---|---|---|
| Corte Veloz (1) | 115% ATQ, Dano Direto a um inimigo; CD2; melee compatível; Oportunismo pode atuar quando o alvo tiver efeito negativo válido. | **R** `class_art.errante.corte_veloz` | `test_errante_trial.py`, `test_class_trials.py`, `test_class_mechanics.py`; implementação em `errante_player_actions`. Sem validação completa de contrato em PG nesta auditoria. |
| Ferida Profunda (4) | 90% ATQ + 1 Sangramento; inimigo único; CD2; melee compatível; DoT segue duração/stack global e Oportunismo. | **R** `class_art.errante.ferida_profunda` | `test_errante_trial.py` comprova aplicação/tick correlacionado para objetivos do treino; não cobre todo o contrato de Sangramento e stack no conteúdo real. |
| Passo Velado (7) | Próprio: +15 p.p. Esquiva 1T; prepara +10 p.p. CRIT no próximo Dano Direto dentro de 2T; CD4; arma: nenhuma. Efeito preparatório deve sobreviver ao estado/codec corretamente. | **R** `class_art.errante.passo_velado` | `test_errante_trial.py`, `test_class_trials.py`; há teste de resposta a Ação Preparada e codec. Sem validação PG focada de cada janela/cancelamento. |
| Golpe Oportuno (9) | 125% ATQ a um inimigo; +15 p.p. CRIT se o alvo tiver efeito negativo; CD3; melee compatível; também sujeito à regra geral do Errante. | **R** `class_art.errante.golpe_oportuno` | `test_errante_trial.py` testa janela de alvo exposto; `test_class_mechanics.py` testa Oportunismo geral. Sem teste isolado de precisão, crítico, cooldown e requisito em PG. |
| Corte Duplo (18) | 2 × 60% ATQ no mesmo inimigo dentro de uma ação; CD3; melee compatível; precisão/crítico e resolução por hit segundo contrato global. | **D** sem ID de runtime | Somente nome na copy `creation_copy.json`; não há `Action(hit_count=2)` vinculada a ID/catálogo. O motor multi-hit existente não equivale à Arte implementada. |
| Brecha Mortal (34) | 130% ATQ; alvo com efeito negativo recebe +10 p.p. PER naquela ação; inimigo único; CD3; melee compatível; regra de Oportunismo pode incidir conforme §49.1. | **D** sem ID de runtime | Somente nome na copy; sem ID/ação/configuração/testes da Arte. |

### Vigia

| Arte canônica (Nv.) | Contrato GDD: potência/ação, alvo, duração, CD, arma, recurso e interação | Runtime e ID | Testes/evidência e lacuna |
|---|---|---|---|
| Disparo Preciso (1) | 115% ATQ, tiro direto a um inimigo; CD2; Arco ou Besta compatível; interage com aquisição/limite de Mira quando válido. | **R** `class_art.vigia.disparo_preciso` | `test_vigia_tecelao_trials.py`, `test_class_trials.py`, `test_weapon_metadata_integration.py`; sem verificação individual completa dos requisitos e cálculos nesta auditoria. |
| Marca da Presa (4) | 85% ATQ + −8% DEF no inimigo por 2T; CD3; Arco/Besta compatível; aplicação pode gerar Mira conforme Rastreador. | **R** `class_art.vigia.marca_da_presa` | `test_vigia_tecelao_trials.py` comprova efeito real correlacionado a alvo; `test_class_mechanics.py` cobre Mira. Falta bateria completa de stacking/duração e arma em PG por Arte. |
| Saraivada (7) | 3 × 40% ATQ contra inimigo; CD3; Arco/Besta compatível; acerto e crítico resolvidos por hit; Mira conforme regras do Vigia. | **R** `class_art.vigia.saraivada` | Teste de multi-hit em `test_vigia_tecelao_trials.py`; ação de classe em `class_trials.py`. Não prova, por si só, distribuição canônica de precisão/crítico em todos os contextos. |
| Olho da Vigília (9) | Buff próprio +12 p.p. PER e +8 p.p. CRIT por 2T; CD4; sem requisito de arma; preparação de Vigia. | **R** `class_art.vigia.olho_da_vigilia` | `test_vigia_tecelao_trials.py`, `test_class_trials.py`; efeitos como `ActionEffect` existem. Falta validação focal PG por efeito/duração/reconnect. |
| Tiro Calculado (18) | 125% ATQ a um inimigo; com ≥2 Mira, +10 p.p. CRIT; CD3; Arco/Besta compatível; consulta Mira sem custo adicional publicado. | **D** sem ID de runtime | Nome apenas na copy; sem definição ativa, ação ou teste da Arte. O recurso Mira genérico não a torna utilizável. |
| Voleio (34) | 75% ATQ em todos os inimigos elegíveis; CD3; Arco/Besta compatível; ação AoE única. | **D** sem ID de runtime | Nome apenas na copy; sem ID/execução/UI/testes de Arte. O motor tem AoE genérico, mas não existe esta ação. |

### Tecelão

| Arte canônica (Nv.) | Contrato GDD: potência/ação, alvo, duração, CD, arma, recurso e interação | Runtime e ID | Testes/evidência e lacuna |
|---|---|---|---|
| Fio Cortante (1) | 120% ATQ, dano a inimigo único; CD2; arma: nenhuma; participa de Trama Encadeada conforme §49.4/§56.5. | **R** `class_art.tecelao.fio_cortante` | `test_vigia_tecelao_trials.py`, `test_class_trials.py`, `test_class_mechanics.py`; há testes de cadeia/expiração. Falta matriz completa de ação em PG por Arte. |
| Chama Tecida (4) | 85% ATQ + Queimadura; inimigo único; CD2; arma: nenhuma; Queimadura segue stack/duração global e pode consumir/preparar Trama. | **R** `class_art.tecelao.chama_tecida` | Testes de DoT e Trama em `test_vigia_tecelao_trials.py`/`test_class_mechanics.py`; falta comprovação integral de 15%/stack, duração, cura reduzida e reconnect por Arte. |
| Ruptura da Trama (7) | 80% ATQ em todos os inimigos elegíveis; CD3; arma: nenhuma; Trama é uma única ação, com alvos correlacionados e sem ações extras. | **R** `class_art.tecelao.ruptura_da_trama` | `test_vigia_tecelao_trials.py` testa AoE como um action instance e cadeia; sem teste PG de área real com todos os efeitos e estados. |
| Véu Entrelaçado (9) | Barreira própria de 90% ATQ por 2T; CD3; arma: nenhuma; aplica regras de Barreira e Trama. | **R** `class_art.tecelao.veu_entrelacado` | `test_vigia_tecelao_trials.py`, `test_class_mechanics.py`; há teste de potência com Trama. Falta conformance PG individual de duração/stack/codec. |
| Geada Tecida (18) | 90% ATQ + −15% AGI inimiga por 2T; CD3; arma: nenhuma; debuff numérico e Trama conforme regra de cadeia. | **D** sem ID de runtime | Nome apenas na copy; sem ID, ação, cooldown real ou teste da Arte. |
| Surto do Véu (34) | 145% ATQ, alvo inimigo único; CD3; arma: nenhuma; interação com a Trama comum do Tecelão. | **D** sem ID de runtime | Nome apenas na copy; sem definição executável. |

### Oráculo

| Arte canônica (Nv.) | Contrato GDD: potência/ação, alvo, duração, CD, arma, recurso e interação | Runtime e ID | Testes/evidência e lacuna |
|---|---|---|---|
| Sinal Funesto (1) | 105% ATQ + −8% ATQ inimigo por 2T; CD2; arma: nenhuma; gera Presságio ofensivo quando o efeito negativo realmente se aplica, conforme §56. | **R** `class_art.oraculo.sinal_funesto` | `test_oraculo_luminar_trials.py`, `test_class_trials.py`, `test_class_mechanics.py`; motor contém Presságio. Falta conformance focal PG de geração/consumo junto do efeito. |
| Vislumbre (4) | +10% AGI por 2T em si ou aliado válido; CD3; arma: nenhuma; buff não ataca. | **R** `class_art.oraculo.vislumbre` | `test_oraculo_luminar_trials.py`, `test_class_trials.py`; alvo aliado está no contrato genérico. Sem validação completa de escolha de alvo e aplicação em cada modo. |
| Ruína Predita (7) | 120% ATQ a inimigo único; CD2; arma: nenhuma; interação com Presságio ofensivo geral. | **R** `class_art.oraculo.ruina_predita` | Testes de trial e recurso Oráculo; sem teste isolado do cálculo e de cada gatilho de Presságio em PG. |
| Véu Premonitório (9) | Barreira própria de 70% ATQ por 2T; enquanto ativa reduz magnitude de Debuff numérico em 10%; CD4; arma: nenhuma; não é imunidade. | **R** `class_art.oraculo.veu_premonitorio` | `test_oraculo_luminar_trials.py`, `test_class_mechanics.py`; ação tem Barreira e redução. Falta teste PostgreSQL de expiração e debuff mitigado/reconnect. |
| Augúrio Favorável (18) | Buff +10% ATQ por 2T em si/aliado; CD4; arma: nenhuma; Presságio defensivo aplica regras globais. | **D** sem ID de runtime | Apenas copy de Oráculo; não consta em catálogo, ação, slots, snapshots nem testes. |
| Selo da Queda (34) | 100% ATQ + −10% DEF no inimigo por 2T; CD3; arma: nenhuma; Presságio ofensivo conforme aplicação válida. | **D** sem ID de runtime | Apenas copy; sem definição/execução da Arte. |

### Luminar

| Arte canônica (Nv.) | Contrato GDD: potência/ação, alvo, duração, CD, arma, recurso e interação | Runtime e ID | Testes/evidência e lacuna |
|---|---|---|---|
| Fulgor (1) | 110% ATQ de dano de Luz a inimigo único; CD2; arma: nenhuma; interage com os efeitos de alternância/fluxo Luminar. | **R** `class_art.luminar.fulgor` | `test_oraculo_luminar_trials.py`, `test_class_trials.py`, `test_class_mechanics.py`; não há validação do conjunto de alternância em todos os modos. |
| Renovação (4) | Cura 85% em si ou aliado válido; CD2; arma: nenhuma; Cura final limitada por HP máximo e modificadores globais. | **R** `class_art.luminar.renovacao` | `test_oraculo_luminar_trials.py`, `test_class_trials.py`, `test_class_mechanics.py`; faltam casos PG por alvo, overheal, debuff e reconnect específicos da Arte. |
| Égide Solar (7) | Barreira 90% ATQ em si ou aliado válido por 2T; CD3; arma: nenhuma; stacking/duração seguem GDD. | **R** `class_art.luminar.egide_solar` | Testes de trial e mechanics; falta teste focal da barreira efetiva por arte/slot/reconnect. |
| Julgamento (9) | 130% ATQ + −15% Cura recebida no inimigo por 2T; CD3; arma: nenhuma; estado de Luz pode influenciar modificadores de classe. | **R** `class_art.luminar.julgamento` | Testes de trial/mechanics cobrem efeitos Luminar correlatos, mas não demonstram cada caso de cura recebida e duração em PG. |
| Luz Restauradora (18) | Cura 70% + Barreira 35% por 2T; CD4; arma: nenhuma; alvo é um destinatário legal de Cura/Barreira, não especificado mais estreitamente na linha §49.4. | **D** sem ID de runtime | Nome na copy; `Action` admite campos combinados de Cura/Barreira, mas não existe ação/ID configurado ou teste. |
| Explosão Solar (34) | 85% ATQ de dano de Luz contra todos os inimigos elegíveis; CD3; arma: nenhuma; uma ação AoE. | **D** sem ID de runtime | Nome na copy; sem ID/definição executável. O AoE genérico não prova esta Arte. |

## D. Matriz individual das 48 Artes de Caminho

Os níveis dos quatro espaços são 12/22/38/52. “Recurso/passiva” descreve a interação do Caminho publicada em §49.3; não converte passiva em Arte. Para qualquer linha **A**, todos os campos de runtime — identidade, desbloqueio, seleção, configuração, Doutrina, snapshot, execução, efeito, persistência, reconnect, UI de ação e teste — estão ausentes.

### Sentinela · Bastião

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Escudo de Cinzas (12) | Barreira própria 95% ATQ, 2T, CD3; arma nenhuma; Fortaleza aumenta Barreira aplicada segundo o modificador do Caminho. | **A** sem ID/ação. Há passiva Bastião em `paths.py`, mas não esta Arte. |
| Interpor (22) | Próximo Dano Direto recebido pelo aliado-alvo dentro de 2T é −25%; CD4; arma nenhuma; proteção não é ataque/Barreira. | **A** sem ação/target effect declarado; teste ausente. |
| Contra-Golpe (38) | 120% ATQ a inimigo; com Retaliação, −10% ATQ do alvo por 2T; CD3; melee compatível; consome Retaliação em commit válido. | **A**; Retaliação é genérica, mas não há identidade/ação de Caminho. |
| Última Muralha (52) | Barreira 65% ATQ a todos aliados por 2T; CD5; arma nenhuma; Barreira em área, aplica modificador de Fortaleza. | **A**; motor tem alvo aliado/AoE e Barreira, mas sem a Arte/ação específica. |

### Sentinela · Devastador

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Aríete (12) | 135% ATQ +10 p.p. PER naquela ação; inimigo único; CD2; melee compatível; elegível a Retaliação e Ímpeto Doloroso (+12% dano final à próxima Arte direta após condição válida). | **V-hist** `path_art.sentinela.devastador.ariete`; `path_arts.py`. Testes `test_path_arts.py`, `test_active_arts.py`, `test_firmeza.py`; validação PostgreSQL histórica na entrega 4B-03A. |
| Golpe de Ruptura (22) | 125% ATQ, ou 150% com Retaliação; inimigo único; CD3; melee compatível; Retaliação é consumida uma vez no commit válido. | **A** sem ID/ação. O motor de Retaliação e Aríete não substituem esta Arte. |
| Abalo (38) | 90% ATQ AoE + −8% DEF 2T; CD4; melee compatível; uma ação, custo/efeitos por alvo conforme regra global. | **A** sem registro; o AoE e debuff genéricos existem, mas não a Arte. |
| Ruptor (52) | 170% ATQ a inimigo; <50% HP próprio, +10% potência; CD5; melee compatível; consulta HP próprio no momento de resolução. | **A**; campo genérico de limiar existe, mas não há ação/ID nem validação. |

### Errante · Carrasco

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Corte de Execução (12) | 135% ATQ; alvo ≤35% HP recebe +15% potência; inimigo único; CD3; melee compatível; Sentença/Oportunismo conforme o alvo e §49.1. | **A** sem ID/action/configuração. |
| Hemorragia (22) | 95% ATQ +2 Sangramentos em um inimigo; CD3; melee compatível; DoT segue stack/duração e gatilhos globais. | **A**; DoT global existe; Arte e aplicação de 2 stacks ausentes. |
| Marca da Morte (38) | 80% ATQ; próxima Arte direta de Carrasco dentro de 2T recebe +12%; CD4; melee compatível; janela não pode ser consumida por ação inválida. | **A**; janela condicional e identity path art ausentes. |
| Ceifa (52) | 165% ATQ; se alvo ≤40% HP, +10 p.p. CRIT; CD5; melee compatível; Sentença/Oportunismo seguem regra global. | **A**; sem ação executável. |

### Errante · Sabotador

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Veneno Velado (12) | 85% ATQ + Veneno; inimigo único; CD2; melee compatível; Veneno segue 12% ATQ/stack/tick, 3T, máximo 3. Interferência não estende DoT. | **A**; DoT existe, ação não. |
| Fio Cortado (22) | 95% ATQ + −12% ATQ inimigo por 2T; CD3; melee compatível; Interferência amplia debuffs elegíveis, sem hard CC/DoT. | **A**. |
| Trava de Passos (38) | 80% ATQ + −18% AGI inimiga por 2T; CD3; melee compatível; Interferência conforme elegibilidade global. | **A**. |
| Colapso Preparado (52) | 120% ATQ +10% por efeito negativo distinto válido no alvo, teto +30%; CD5; melee compatível; Debuffs/DoTs distintos não devem ser contados em duplicidade. | **A**; condição e contabilização por efeitos distintos não configuradas. |

### Vigia · Atirador

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Tiro Perfurante (12) | 130% ATQ +10 p.p. PER ao tiro; inimigo único; CD2; Arco/Besta compatível; Mira Perfeita concede bônus por stack. | **A**; Mira/Precisão existem em parte do motor, mas falta Arte/ID. |
| Fixar Alvo (22) | 100% ATQ +1 Mira; inimigo único; CD3; Arco/Besta; Mira Perfeita/limite 4 e troca de alvo conforme §§49.3/56. | **A**. |
| Rajada Controlada (38) | 3×45% ATQ, ação multi-hit a um alvo; CD3; Arco/Besta; acerto/crítico por hit e custo de turno uma vez. | **A**; o padrão de multi-hit é exercitado por Saraivada, não esta Arte. |
| Disparo Terminal (52) | Requer 4 Mira; consome 4 após resolução; 175% ATQ +15 p.p. CRIT; CD5; Arco/Besta; Mira Perfeita. | **A** sem ID/definição. Há lógica de Mira e ramo que reconhece sufixo/identidade `disparo_terminal` em `combat.py`, além de teste sintético em `test_class_mechanics.py`; não existe ação player equipável do GDD. |

### Vigia · Rastreador

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Flecha Serrilhada (12) | 90% ATQ + Sangramento em um inimigo; CD2; Arco/Besta; Sangramento segue regra global; Rastros Múltiplos concede Mira pela aplicação válida. | **A**. |
| Laço de Caça (22) | 80% ATQ + −20% AGI inimiga por 2T; CD3; Arco/Besta; Rastros Múltiplos concede Mira ao aplicar redução de AGI válida. | **A**. |
| Chuva de Rastros (38) | AoE 70% ATQ +1 Mira por alvo válido; CD4; Arco/Besta; Mira por alvo com exceção e limite publicados. | **A**; Mira/AoE existentes não são esta ação. |
| Predação Persistente (52) | 135% ATQ +8% por DoT/Debuff distinto no alvo, máximo +16%; CD4; Arco/Besta; não duplicar fontes do mesmo efeito. | **A**; sem Arte nem verificação de efeitos distintos. |

### Tecelão · Conjurador

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Estilhaço do Véu (12) | 140% ATQ/potência publicada em alvo inimigo único; CD2; arma nenhuma; Convergência melhora dano de Trama em +15% e Cura/Barreira em +6% conforme §49.3. | **A** sem ação. |
| Incêndio Trançado (22) | AoE 75% + Queimadura; CD3; arma nenhuma; Queimadura global; Convergência aplica componente de dano. | **A**; Chama Tecida já prova DoT, não cobre AoE/esta Arte. |
| Convergência Arcana (38) | 3×50% em inimigo(s) conforme alvo publicado; CD3; arma nenhuma; multi-hit resolve cada acerto na mesma ação; Convergência. | **A**; multi-hit existe, ação ausente. |
| Rasgo Conjurado (52) | AoE 125%; CD5; arma nenhuma; Convergência incide no dano conforme regra do Caminho. | **A**. |

### Tecelão · Rúnico

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Runa de Guarda (12) | Barreira 105% ATQ por 2T ao alvo de proteção válido; CD3; arma nenhuma; Inscrição aumenta componente de Barreira em 15%. | **A** sem ação. |
| Runa de Ruptura (22) | 90% + −10% DEF inimiga por 2T; CD3; arma nenhuma; Inscrição modifica dano de Trama em +6%. | **A**. |
| Runa de Retorno (38) | Cura 70% + purifica 1 efeito elegível do alvo; CD4; arma nenhuma; Inscrição aumenta cura em 15%. | **A**. **Gap de motor:** remoção de efeito aparece em funções de consumível (`use_purification_consumable`), não como componente de `Action`. |
| Círculo Rúnico (52) | Barreira AoE 60% ATQ por 2T aos aliados; CD5; arma nenhuma; Inscrição melhora Barreira. | **A**; combinação de AoE/barreira não está ligada a uma ação de Caminho. |

### Oráculo · Agoureiro

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Mau Agouro (12) | 95% + −10% ATQ inimigo por 2T; CD2; arma nenhuma; Mau Presságio eleva bônus do Presságio ofensivo consumido a +16%. | **A**. |
| Destino Lento (22) | 70% + −18% AGI inimiga por 2T; CD3; arma nenhuma; Presságio e debuff seguem ciclo global. | **A**. |
| Condenação (38) | 80% ATQ; prepara +20% à próxima Arte de Agoureiro dentro de 2T; CD4; arma nenhuma; efeito precisa sobreviver ao codec e só ser consumido em ação válida. | **A**; preparação específica não configurada. |
| Eclipse Previsto (52) | 150% ATQ; se consumir Presságio, −15% Cura recebida no alvo por 2T; CD5; arma nenhuma; consumo condicional. | **A**; ação e consumidor condicional ausentes. |

### Oráculo · Invocador

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Lobo (12) | 125% em inimigo único; CD2; arma nenhuma; marca manifestação Lobo para janela Tríade de 2T. | **A**; `manifestation_kind` e lógica Tríade genérica em `combat.py` não criam a Arte. |
| Coruja (22) | 85% + −15% AGI inimiga por 2T; CD3; arma nenhuma; registra manifestação Coruja. | **A**. |
| Urso (38) | Barreira 100% por 2T ao próprio Invocador; CD3; arma nenhuma; registra manifestação Urso. | **A**. |
| Tríade Encarnada (52) | CD5; resultado condicionado à manifestação anterior ainda válida: Lobo→155% dano; Coruja→95% + −20% AGI 2T; Urso→Barreira 120% 2T. Não atualiza manifestação nem dispara alternância. | **A**; falta ação ramificada/target/component; a lógica de bônus de alternância no motor não implementa os três resultados da Arte. |

### Luminar · Guardião

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Cura Solar (12) | Cura 100% ao alvo aliado elegível; CD2; arma nenhuma; Aurora melhora componente de Cura Fulgor conforme §49.3. | **A**. |
| Égide Compartilhada (22) | Barreira 90% no aliado-alvo +45% em si; CD4; se Luminar é o alvo, recebe apenas 90%, não soma; arma nenhuma. | **A**; Action suporta barreiras a alvo e próprio, mas sem regra/ação desta exceção. |
| Purgação Luminosa (38) | Cura 65% + remove/purifica 1 efeito elegível; CD4; arma nenhuma; Aurora/benefícios de Cura globais. | **A**. **Gap de motor:** componente de remoção de efeito por Arte ausente. |
| Aurora Guardiã (52) | Cura AoE 55% aos aliados elegíveis; CD5; arma nenhuma; cura limitada e calculada individualmente por alvo. | **A**; resolução genérica AoE/Cura existe como componentes separados, mas ação não existe. |

### Luminar · Inquisidor

| Arte (Nv.) | Contrato canônico: potência/ação, alvo, duração, CD, arma, recurso/interação | Runtime / evidência / lacuna |
|---|---|---|
| Lança de Luz (12) | 135% ATQ a inimigo único; CD2; arma nenhuma; Julgamento Implacável aplica bônus de classe ao dano conforme regra. | **A**. |
| Selo da Penitência (22) | 100% + −20% Cura recebida no inimigo por 2T; CD3; arma nenhuma; compatível com debuff numérico. | **A**. |
| Purga Ardente (38) | 120% ATQ + dispel de 1 efeito positivo do inimigo; CD4; arma nenhuma; remoção deve respeitar elegibilidade de dispel. | **A**. **Gap de motor:** `Action` não declara dispel; helpers de consumível não fazem da Arte uma ação. |
| Veredito (52) | 170% ATQ; se alvo tiver Debuff, +10 p.p. CRIT; inimigo único; CD5; arma nenhuma; Julgamento Implacável aplica sua interação. | **A**. |

## E. Cobertura transversal do motor

| Camada/mecanismo | Situação observada | Evidência e limite |
|---|---|---|
| Identidade e desbloqueio | Implementados para 26 IDs; nível, Classe e `path_id` são validados. 58 sem registro. | `domain/arts.py`; `ActiveArtDefinition`, `ACTIVE_ART_DEFINITIONS`, `ART_IDS_BY_CLASS`, `PATH_ART_IDS_BY_PATH`. |
| Três slots e edição | Implementados para IDs existentes; limites, unicidade, versão de configuração, lock e requisito de arma são validados no serviço. | `application/active_arts.py`; tabela `character_active_art_slots`, PK por personagem/slot, unique por personagem/Arte, check 1–3 em `models.py:1997+`; migration `20260929_0013_active_art_slots.py`. |
| Configuração e Doutrinas | Atual catálogo é a fonte de Artes selecionáveis; definição exige Classe/nível/Caminho; handler serializa versão e respeita atividade foreground. | `application/doctrines.py`, `bot/doctrines_ui.py:343–357`, `bot/character_progression_handlers.py`, testes `test_doctrine_path_arts.py` e `test_firmeza.py`. |
| Snapshot/persistência/reconnect | IDs equipados são congelados em `active_arts` na configuração de Combate; codec serializa combate, efeitos, cooldown e estado; campanhas, Ronda, Caçada/Grupo, Masmorras e PvPvE consomem o snapshot. | `active_arts.py`; `infrastructure/db/combat_codec.py`; integrações em `application/road.py`, `round.py`, `dungeons.py`, `group_hunts.py`, `pvpve.py`, módulos `p1`–`p36`/regionais. Evidência de integração não cobre cada Arte em cada modo. |
| Dano Direto/precisão/crítico | Suportado por `Action.coefficient`, bônus PER/CRIT e cálculo global; Aríete exercita bônus de PER. | `domain/combat.py:89+`; `path_arts.py`; `test_path_arts.py`. Regras específicas futuras devem ser declaradas/validadas por Arte. |
| Buffs/Debuffs numéricos | `ActionEffect` modela stat, magnitude, duração, tipo e modo multiplicativo/p.p.; Firmeza usa efeito próprio temporário. | `combat.py:73+`; `test_firmeza.py`. Regras de stacking/reaplicação ainda exigem teste específico por efeito. |
| DoT, multi-hit e AoE | Tipos DoT nativos, stacks e `hit_count`; cada hit resolve por ação; `target_mode` inclui all_opponents/all_allies. | `combat.py:89+`, `TARGET_MODES`, resolução multi-hit; `test_vigia_tecelao_trials.py`, `test_class_mechanics.py`. Capacidade geral não substitui as Artes ausentes. |
| Cura, Barreira, self/ally | Campos de Cura/Barreira em `Action` e alvo self/ally dão suporte a componentes individuais e combinados; teste de Luminar e mecânicas comprova parte. | `combat.py:89+`; `test_oraculo_luminar_trials.py`, `test_class_mechanics.py`. Faltam as Artes combinadas futuras e conformance de alvo/ordem. |
| Purificação/Dispel por Arte | **Lacuna confirmada.** `Action`/`ActionEffect` não declara operação para remover DoT/debuff/efeito positivo. Remoção está em fluxo de Consumível. | `use_purification_consumable`, `use_combat_consumable` em `combat.py:4721+`; nenhum campo equivalente na definição de `Action` em `combat.py:89–160`. Necessário para Runa de Retorno, Purgação Luminosa e Purga Ardente. |
| Recursos de Classe/Caminho | Existem estados e resolução para Retaliação, Mira, Trama, Presságio, Tríade, Luz/Contraluz e Ímpeto, e Aríete interage com Devastador. Parte dos gatilhos é específica pelo ID/nome, em vez de configuração genérica de ação. | `combat.py` (preparação/commit de recurso), `class_trials.py`, `test_class_mechanics.py`, `test_path_arts.py`. Terminal de Mira tem reconhecimento específico por `disparo_terminal`; para as 47 restantes faltam IDs/ações e validação de requisito/consumo. |
| Snapshots e UI de combate | UI gera ação apenas a partir do snapshot equipado e apresenta cooldown/efeitos; callbacks carregam intenção e versão. | `bot/combat_ui.py:1222–1240, 1342+`; `test_combat_ui.py`, `test_firmeza.py`, `test_talents.py`. Exibição de Arte ainda disponível depende de catálogo implementado. |
| Copy estática de Classe | A introdução de Classe enumera as seis Artes canônicas por Classe, incluindo 11 sem runtime. | `bot/creation_copy.json:12–17`. Não confundir apresentação de nome com oferta selecionável; há risco de expectativa de jogador. |
| Weapon Metadata | Requisitos de Artes atuais são tags explícitas; nenhuma inferência por nome ou `weapon_family`. Firmeza não exige arma; Aríete exige `weapon.compat.melee`. | `arts.py:201–215`; `application/weapon_metadata.py`; `test_weapon_metadata_integration.py`, `test_firmeza.py`, `test_path_arts.py`. A metadata futura ainda precisa ser explicitada em cada definição e testada. |
| PvE/Grupo/Ronda/Masmorra | Há pontos de composição de snapshot para campanha, Caçada/Grupo, Ronda, Masmorra e PvPvE. Ronda usa a configuração frozen; não foi provado que todas as ações futuras têm política automática válida. | `application/road.py`, `group_hunts.py`, `round.py`, `dungeons.py`, `pvpve.py`; ver matriz de cobertura por modo acima. |
| PvP competitivo separado | O código encontrado integra Artes ao serviço PvPvE. A auditoria não encontrou fluxo de Arena/duelo competitivo implantado que possa ser validado como integração de Artes; não declarar integração ausente por defeito da Arte em modo não demonstrado. | `application/pvpve.py:1365+`; classificação: não verificado/não aplicável ao runtime de PvP competitivo ausente/incompleto reportado na auditoria global 4A. |
| Idempotência/concorrência | Configuração serializa com lock/versionamento; ação de combate é versionada e persistida pelos serviços. Não há prova por teste para cada futura ação de consumo multi-recursos. | `active_arts.py`; `combat_handlers.py`; testes de configuração concorrente, stale callback, codec e ação em módulos existentes. Exigir testes por efeitos/consumo ao implementar cada novo tipo. |

### Mecanismos especiais requeridos pela lista do proprietário

| Arte especial | Resultado desta auditoria |
|---|---|
| Firmeza | Implementada e com validação histórica focal: Buff DEF próprio, 2T, CD3, sem requisito de arma. |
| Aríete | Implementada e com validação histórica: 135%, +10 p.p. PER, CD2, melee; interações Devastador cobertas em testes focais. |
| Corte Duplo | Ausente; `hit_count` do motor é reutilizável, mas não há ID/action/configuração dela. |
| Saraivada | Presente; código declara 3×40%; cobertura de multi-hit existe, mas validação integral por hit/metadata em cada contexto não foi repetida nesta fase. |
| Explosão Solar | Ausente; AoE existe genericamente, sem ação/ID da Arte. |
| Luz Restauradora | Ausente; Action pode combinar Cura e Barreira, mas não há ação configurada. |
| Runa de Retorno | Ausente e requer extensão do motor para Purificação como componente de Arte. |
| Égide Compartilhada | Ausente; componentes Barrier self+target existem, mas precisa regra de exceção “self-target recebe só 90%” e teste. |
| Tríade Encarnada | Ausente; estado/alternância de manifestação existe, mas falta resolução condicional Lobo/Coruja/Urso com três componentes de resultado. |
| Última Muralha | Ausente; motor tem alvo all_allies e barreira, mas ação/Arte não existe. |
| Disparo Terminal | Ausente como ação/catalog entry. O motor possui lógica de teste/recurso nomeada, mas não deve ser contabilizada como Arte executável. |

## F. Impacto na jornada por faixa

| Faixa | Desbloqueios canônicos | Estado do checkout e impacto comprovado |
|---|---|---|
| Nv.1–10 | Classe: 1, 4, 7, 9. Provação/Caminho em 10. Sem Arte de Caminho antes de 12. | Quatro Artes iniciais de cada Classe estão disponíveis no código (24), mas sua validação completa ainda é insuficiente. O jogador pode configurar até três. |
| Nv.11–20 | Arte de Caminho I no 12; Classe V no 18. | Aríete Devastador Nv.12 e Firmeza Sentinela Nv.18 disponíveis. As outras cinco Artes de Classe Nv.18 e 11 das 12 primeiras Artes de Caminho estão ausentes. Para P12, Sentinela Devastadora Nv.20 pode usar Firmeza e Aríete se configuradas; o playthrough local segue modificado e não foi executado nesta auditoria. Não declarar P12 resolvida. |
| Nv.21–30 | Arte de Caminho II no 22. | Todas as 12 Artes do segundo espaço de Caminho estão ausentes. Não há evidência de que P13–P18 exijam um Caminho específico; a lacuna é de completude/builds, não gate obrigatório provado. |
| Nv.31–40 | Classe VI no 34; Arte de Caminho III no 38. | Seis Artes de Classe Nv.34 e 12 Artes de Caminho Nv.38 estão ausentes. |
| Nv.41–50 | Sem novos desbloqueios de Arte publicados nesta faixa. | Não há novas Artes para obter; falta conteúdo já esperado de Nv.34/38 continua afetando builds de níveis altos. |
| Nv.51–60 | Arte de Caminho IV no 52. Nv.60 deveria ter 6 de Classe +4 do Caminho escolhido e até 3 equipadas. | Todas as 12 Artes de Caminho Nv.52 estão ausentes. À exceção de Sentinela Devastadora, as demais classes não têm qualquer Arte de Caminho runtime. Catálogo no Nv.60 fica muito abaixo das 10 Artes elegíveis da fonte. |

As Artes são conteúdo/progressão de build. A ausência não transforma missão, Caminho ou atividade opcional em gate obrigatório; este relatório não recomenda exigir masmorras, secundárias ou PvP para compensar Artes ausentes.

## G. Achados e gravidade

| ID | Severidade/categoria | Sistema e fonte | Evidência e impacto | Dependências, recomendação e aceite objetivo |
|---|---|---|---|---|
| ARTS-001 | **P1 · IMPLEMENTACAO_PARCIAL** | Cobertura global das 84 Artes; GDD §§49.3–49.4 | 26/84 IDs/ações runtime; 11 apenas em copy e 47 Caminho ausentes. Builds e funções de Classe/Caminho publicados não estão disponíveis ao jogador. | Base de catálogo/snapshot já existe. Implementar cada Arte em fatias verticais com ID, gate, requisitos, ação, efeito, UI e testes. Aceite: 84 IDs legítimos, sem duplicação, 84 contratos identificáveis, builds/slots válidos e testes PG por mecânica. |
| ARTS-002 | **P1 · IMPLEMENTACAO_AUSENTE** | Purificação/Dispel como componente de Arte; GDD §49.3 e §49.4 | `Action` não declara remoção de efeitos; purificação e dispel presentes em fluxo de consumíveis. Três Arts conhecidas (Runa de Retorno, Purgação Luminosa, Purga Ardente) dependem disso. | Antes dessas Artes, introduzir uma resolução de remoção de efeito compatível com tipos/flags globais, autorização de alvo e commit único. Aceite: um efeito elegível removido por ação, não removível respeitado, snapshot/reconnect e idempotência testados. |
| ARTS-003 | **P1 · IMPLEMENTACAO_PARCIAL** | Recursos e condições declarativas de Arte; GDD §§49.3, 55–56 | Mira/Terminal, Tríade e outros fluxos têm tratamento acoplado a IDs e hooks específicos; `Action` não expressa genericamente pré-requisito/consumo de todos os recursos ou ramificação do resultado. Uma parte existe como hook, mas Arte não é runtime sem definição. | Quando implementadas, documentar e testar consumo/condição específica em commit separado; acrescentar API genérica somente onde várias Artes a requerem, sem novo motor paralelo. Aceite: requisito rejeita sem mutação, consome em commit válido uma vez, persiste após reconnect e não duplica em multi-hit. |
| ARTS-004 | **P2 · COBERTURA_INSUFICIENTE** | 24 Artes iniciais de Classe | IDs, ação e código existem; testes de trial/mechanics cobrem grupos, mas esta auditoria não encontrou uma prova PostgreSQL de todos os campos para cada Arte em todos os modos. | Criar matriz de conformance parametrizada por ID contra o GDD e cobertura PG de slots/config/snapshot/combat/reconnect. Aceite: cada Arte existente checada em potência/efeito/target/duration/CD/weapon e pelo menos um fluxo real de combate. |
| ARTS-005 | **P2 · INTEGRACAO_AUSENTE** | Copy de criação Telegram | `creation_copy.json` enumera 11 Artes sem ID/ação. Pode criar expectativa de escolha imediata; as telas dinâmicas só listam catálogo implementado. | Após decidir apresentação com fonte visual vigente, alinhar copy ou mostrar status/desbloqueio apenas se o catálogo tiver a definição. Aceite: nenhuma Arte não executável apresentada como ação obtida/equipável. |
| ARTS-006 | **P2 · COBERTURA_INSUFICIENTE** | Ronda/Grupo/Masmorra/PvPvE | Snapshot é integrado em pontos de serviço, mas não há cobertura conformance das 84 ações e políticas automáticas futuras; PvP competitivo standalone não foi validado. | Validar cada mecânica nova em Solo/Grupo e modo automatizado afetado. Não afirmar integração da Arena/Duelo enquanto esses motores não estiverem disponíveis. |
| ARTS-007 | **P3 · MELHORIA_OPCIONAL** | Legibilidade do diagnóstico de configuração | A UI dinâmica tem avisos para arma/elegibilidade. Ao crescer catálogo, filtros por Classe/Caminho/nível podem ficar extensos. Não foi comprovado defeito atual. | Rever experiência após catálogo maior. Aceite: requisitos, bloqueios e slots compreensíveis sem revelar ação não disponível. |

**P0:** nenhum achado confirmado nesta auditoria. Não foi demonstrada exploração de economia, perda de estado ou quebra crítica do motor. P1 indica conteúdo obrigatório ausente/incompleto para o inventário canônico, não risco de corrupção já observado.

## H. Plano de implementação verificável

As tarefas abaixo são propostas de sequenciamento, sem implementação nesta auditoria.

| Ordem | Entrega isolada | Dependências | Testes necessários | Critério de conclusão |
|---:|---|---|---|---|
| 1 | Fechar contrato do framework compartilhado para remoção/purificação/dispel e requisitos/consumo condicional de recurso. | GDD v1.6.0 §§49, 55–57; modelo `Action`, efeitos e codec atuais. | Unitários de ação válida/inválida, alvos, efeito protegido/não removível, concorrência, reconnect e PostgreSQL. | Framework pode representar os contratos Runa de Retorno, Purgação Luminosa, Purga Ardente e custo de Mira sem alterar Arte existente; estado de recurso é consumido uma vez no commit. |
| 2 | Classe Nv.18: cinco Artes ausentes (Errante Corte Duplo, Vigia Tiro Calculado, Tecelão Geada Tecida, Oráculo Augúrio Favorável, Luminar Luz Restauradora). | Framework dos componentes de hit_count, Mira, buff, Cura+Barreira; catálogo e snapshot existentes. | Teste por Arte de gate, slot/arma/alvo/CD/efeito; um combate PostgreSQL por classe; Doutrina e UI. | Cinco Artes entram no catálogo correto e executam exatamente conforme §49.4, sem alterar slots/Artes antigas. |
| 3 | Classe Nv.34: Golpe de Rechaço, Brecha Mortal, Voleio, Surto do Véu, Selo da Queda e Explosão Solar. | Framework e catálogo; dados §49.4/§55.3. | Teste unitário e PostgreSQL por interação, requisito de arma, alvo, cooldown e gates. | Seis Artes Nv.34 registradas somente nos seus donos e com nível/cooldown corretos. |
| 4 | Cobertura de Classe completa, níveis 1/4/7/9/18/34. | Entregas 2–3. | Catálogo por Classe/nível; configuração máxima de três; interações e Doutrina. | Cada Classe tem seis definições válidas; total de Classe =36; nomes/IDs únicos. |
| 5 | Caminhos Sentinela (Bastião e Devastador): 7 Artes restantes após Aríete. | Extensão de área/alvo/Barreira, regra de proteção Interpor, Retaliação e Ímpeto. | alvos próprios/aliados/AoE, 2T, 3/4/5 CD, Barreiras e redução de dano, consumo e retry. | 8/8 Artes de ambos Caminhos selecionáveis apenas quando Caminho/nível atuais permitem. |
| 6 | Caminhos Errante (Carrasco/Sabotador): 8 Artes. | DoT, efeitos distintos, janela de próxima Arte, Oportunismo/Sentença e elegibilidade de armamento. | stack/tick, janela válida, contagem de distintos, combate/snapshot/reconnect. | 8/8 ações corretas, nenhum efeito duplicado e 3 slots preservados. |
| 7 | Caminhos Vigia (Atirador/Rastreador): 8 Artes. | Mira, requisito de Arco/Besta, multi-hit, alvo distribuído e consumo Terminal. | 4-Mira insuficiente/suficiente, consumo após resolução, troca de alvo, AoE por alvo e Grupo. | 8/8 ações testadas e metadata explícita; nenhuma inferência de arma. |
| 8 | Caminhos Tecelão (Conjurador/Rúnico): 8 Artes. | Trama e componentes de Cura/Barreira/Purificação; AoE e multi-hit. | Ordem e duração de Trama, buff componente, DoT, AoE, Cura, Barreira, limpeza válida. | Sequência canônica de Trama e 8/8 ações corretas; codec/reconnect. |
| 9 | Caminhos Oráculo (Agoureiro/Invocador): 8 Artes. | Presságio e efeito de preparação; manifestation state e ação condicional Tríade. | condicional presente/expirado/ausente, resultado Lobo/Coruja/Urso, ação não atualiza manifestação. | 8/8 ações respeitam caminho, recurso e janela, sem alteração de Presságio em ação inválida. |
| 10 | Caminhos Luminar (Guardião/Inquisidor): 8 Artes. | Cura, Barreira distribuída, AoE, purificação e dispel. | alvo self/ally/allies, exceção Égide, Cura recebida, efeitos não removíveis e dispel seletivo. | 8/8 ações funcionais; remoção e resolução de suporte transacionais. |
| 11 | Conformance transversal e sincronização Telegram/Doutrinas/Ronda. | Catálogo das 84 Artes implementado. | Playwright/handlers se disponíveis; PostgreSQL de configuração/lock; Solo/Grupo, Masmorra, Ronda e PvPvE pertinente. | Todas as Artes só aparecem quando elegíveis, congelam no snapshot e comportam reconnect; nenhuma executada se conhecida mas não equipada. |
| 12 | Reavaliar e completar playthrough Solo P12. | Entregas de Arte necessárias para a build sentinela e tarefa própria de estratégia; jamais usar flags artificiais. | Jornada integral PostgreSQL P7–P12, atividade e economia legítimas, vitória/settlement/conclusão/Nareth. | P12 completa por serviço real sem alterar Matriarca, recursos, XP ou gates; manter tarefa separada da implementação de Artes. |
| 13 | Regressão global das 84 Artes e dos modos. | 1–12. | Suíte completa PostgreSQL, Weapon Metadata, Alembic, Ruff, tests sem skips artificiais. | Matriz 84/84 com testes apropriados, zero falha atribuível, sem efeito em economia/níveis e sem ação além das três equipadas. |

**Contagem do plano:** são cinco Classes ausentes em Nv.18 (Firmeza de Sentinela já existe) e seis em Nv.34; portanto, 11 Artes de Classe faltantes. Tiro Calculado é Nv.18 e pertence à entrega 2, não à entrega 3.

## I. Critérios de lançamento quanto às Artes

| Critério | Estado | Base |
|---|---|---|
| Catálogo canônico oferece as 84 Artes, com nível/Classe/Caminho exatos | **NAO_PRONTO** | Runtime identificável para apenas 26. |
| 24 Artes iniciais de Classe com execução existente | **NAO_VERIFICADO** | Código e testes existem; contrato integral de cada uma não foi validado nesta auditoria. |
| Firmeza e Aríete executáveis | **PRONTO (histórico)** | Validação focal PostgreSQL foi reportada em fases anteriores; não repetida nesta execução. |
| Todas as categorias de efeito exigidas por 84 Arts | **NAO_PRONTO** | Remoção/Purificação/Dispel por Arte ausente; recursos condicionais ainda requerem contratos específicos. |
| Três slots, persistência e integração de snapshot para IDs runtime atuais | **PRONTO (escopo atual)** | Serviço/modelo/codec e testes existentes; não implica cobertura futura. |
| 84 Artes em Telegram, Doutrinas e modos PvE | **NAO_PRONTO** | Só IDs de runtime aparecem dinamicamente; a maioria não existe. |
| PvP competitivo standalone com Artes | **NAO_VERIFICADO** | Não foi encontrado fluxo competitivo completo em que validar; PvPvE tem ponto de snapshot. |
| Jornada Solo P12 | **NAO_VERIFICADO** | Os arquivos do playthrough têm modificações locais preservadas, mas não foram executados nesta auditoria. |

## J. Conclusão

Se o Asterion fosse aberto hoje e as 84 Artes fossem parte do inventário público de lançamento, **58 Artes não poderiam ser equipadas nem usadas**: 11 aparecem apenas como nomes na copy de Classe e 47 Artes de Caminho não têm runtime. O motor atual entrega catálogo/configuração/snapshot e execução real para 26; para 24 delas a validação ainda é insuficiente; Firmeza e Aríete têm validação focal histórica.

As lacunas mais concretas antes de implementar a próxima leva são o mecanismo de remoção de efeitos em ações de Arte e uma representação/commit auditável dos requisitos e consumos de recursos condicionais. A primeira entrega recomendada é a fundação para purificação/dispel e condições de recurso, seguida das cinco Artes Classe Nv.18 ainda ausentes; depois, as seis Classe Nv.34 e os Caminhos em lotes por mecânica, cada lote com testes por contrato. Somente após isso deve-se repetir o playthrough Solo P12 e a regressão global.

### Referências principais de código e testes

* Catálogo/níveis/metadata: `src/asterion/domain/arts.py:12–244`.
* Ações de Classe: `src/asterion/domain/class_trials.py:345–1211`.
* Aríete e fábrica de Artes de Caminho: `src/asterion/domain/path_arts.py:1–63`.
* Persistência/validação/locks: `src/asterion/application/active_arts.py`; `src/asterion/infrastructure/db/models.py:1997–2012`; `alembic/versions/20260929_0013_active_art_slots.py`.
* UI/handlers: `src/asterion/bot/character_progression_ui.py:180–470`; `src/asterion/bot/character_progression_handlers.py`; `src/asterion/bot/combat_ui.py:1222–1240,1342+`; `src/asterion/bot/doctrines_ui.py:343–357`.
* Motor/efeitos: `src/asterion/domain/combat.py:73–160,2290–2540,2880–2960,4721–4970`.
* Testes: `tests/test_active_arts.py`, `test_path_arts.py`, `test_firmeza.py`, `test_class_trials.py`, `test_sentinel_trial.py`, `test_errante_trial.py`, `test_vigia_tecelao_trials.py`, `test_oraculo_luminar_trials.py`, `test_class_mechanics.py`, `test_doctrine_path_arts.py`, `test_combat_ui.py`, `test_talents.py`, `test_weapon_metadata_integration.py`.
* Evidência histórica de lacuna P12: `docs/audits/ASTERION_DIAGNOSTICO_REGRESSOES_FASE4B00.md`; esta auditoria não repete o percurso.

# ASTERION — Reauditoria das 84 Artes Canônicas · Fase 4B-07

Data: 2026-10-21
Branch/HEAD auditados: main / 865f4dd961b5948ff1a9442f3700d8a6d14341b7
Escopo documental: não foram executados testes nesta fase.

## 1. Escopo, autoridades e método

Universo: 36 Artes de Classe (seis por Classe) e 48 Artes de Caminho (quatro por Caminho). Ataque Básico, Defender, passivas, Talentos e recursos de Classe que não sejam Artes não são contados.

Autoridades consultadas: GDD Estrutural v1.6.0, §§49.3–49.4, 49.12, 55 e 56; Bíblia Canônica Mundo/Regiões/Bestiário/NPCs v3.0 FINAL; Contrato Global Weapon Metadata v1.0.0 FINAL; SOURCE_AUTHORITY.md, docs/SOURCE_AUTHORITY.md e relatório histórico 4B-04. Os índices selecionam essas mesmas versões. O GDD governa regras e números; a Bíblia, identidades; Weapon Metadata, tags explícitas.

Código inspecionado: src/asterion/domain/arts.py, class_trials.py, path_arts.py, paths.py, combat.py, application/active_arts.py, serviços de Doutrina/Ronda, snapshot/codec, HUD e testes relacionados. Nome em copy ou componente genérico não prova implementação: exige ID runtime e Action registrada que chega ao motor.

Estados mutuamente exclusivos:
- IMPLEMENTADA_VALIDADA: executável e teste pertinente comprova o contrato central.
- IMPLEMENTADA_TESTES_INSUFICIENTES: executável, sem evidência específica suficiente do contrato/integração.
- PARCIAL: execução existe, mas incompleta ou diverge do cânone de forma comprovada.
- SOMENTE_REFERENCIADA: nome em copy/UI/texto, mas sem execução.
- AUSENTE: sem execução e sem referência de produto encontrada.
Quando a Fonte não publica ID de máquina, o relatório não inventa um.

Checkout inicial: main, HEAD 865f4dd961b5948ff1a9442f3700d8a6d14341b7, staging vazio. Permaneceram modificados tests/test_tdo_full_playthrough.py e tests/test_vde_full_playthrough.py; untracked preexistentes .worktrees/ e ASTERION_CONTEUDO_ALTOS_CINEREOS_v1.0.1_PROPOSTA.md. A leitura de .pytest_tmp/ foi recusada pelo sistema; não foi aberto nem alterado. Nenhum teste foi executado.

Hashes antes da auditoria:
- TDO: D4ABFE6B97860F981E3BE1B270F0D2DFC0D850015D7FCDB89B841D9006CE67A
- VDE: FCE5B37074299FE89B183939A5B767D0A7C29F02E3509DEE174A45EBA5FFD4D8

## 2. Resumo e comparação com 4B-04

| Estado | Total |
|---|---:|
| IMPLEMENTADA_VALIDADA | 7 |
| IMPLEMENTADA_TESTES_INSUFICIENTES | 24 |
| PARCIAL | 0 |
| SOMENTE_REFERENCIADA | 6 |
| AUSENTE | 47 |
| **Total** | **84** |

4B-04 encontrara 26 IDs executáveis: 24 Artes Classe Nv.1/4/7/9, Firmeza e Aríete. Agora são 31: entraram Corte Duplo, Tiro Calculado, Geada Tecida, Augúrio Favorável e Luz Restauradora (+5). Firmeza já estava incluída na contagem histórica. Das 11 Artes Classe somente referenciadas em 4B-04, cinco Nv.18 agora são executáveis; restam seis Nv.34. As 47 Artes de Caminho sem Aríete seguem ausentes. Os números de evidência histórica sobem de duas para sete; nenhum teste foi executado nesta reauditoria.

## 3. Matriz das 36 Artes de Classe

Para as 24 Artes Nv.1/4/7/9: o catálogo/IDs está em arts.py, Actions em class_trials.py; os slots, a validação de Classe/nível/arma, Doutrina, snapshot e persistência usam o pipeline active_arts.py/combate. Os testes citados abaixo exercitam o sistema, mas não provam todos os valores, alvos, duração, cooldown, armamento e reconnect de cada Arte. Portanto, todas as 24 são classificadas conservadoramente como IMPLEMENTADA_TESTES_INSUFICIENTES.

| Classe | Arte (Nv.) | ID runtime | Contrato GDD resumido (§49.4/55/56) | Código/testes/commit | Estado e lacuna |
|---|---|---|---|---|---|
| Sentinela | Golpe de Guarda (1) | class_art.sentinela.golpe_de_guarda | 110% ATQ, inimigo único, CD2, melee; Retaliação global. | sentinel_player_actions; test_sentinel_trial.py, test_class_trials.py, test_active_arts.py; base pré-4B04. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta conformance PG completa. |
| Sentinela | Quebra-Postura (4) | class_art.sentinela.quebra_postura | 90% + −10% DEF por 2T, CD3, melee. | class_trials.py; test_sentinel_trial.py, test_class_trials.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta prova por Arte de magnitude, duração e reconnect. |
| Sentinela | Muralha Breve (7) | class_art.sentinela.muralha_breve | Barreira própria 70% ATQ por 2T, CD3, sem arma. | class_trials.py; test_sentinel_trial.py, test_class_trials.py, test_talents.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta teste próprio completo de source/reaplicação. |
| Sentinela | Impacto Resoluto (9) | class_art.sentinela.impacto_resoluto | 135% ATQ, inimigo único, CD3, melee; recursos conforme regra global. | class_trials.py; test_sentinel_trial.py, test_class_trials.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta matriz integrada de arma/Caminho/recurso. |
| Sentinela | Firmeza (18) | class_art.sentinela.firmeza | +12% DEF própria por 2T, CD3; sem arma. | arts.py/class_trials.py; tests/test_firmeza.py; commit 4748add6dc079c6a7e785bbf9de6dd0af17cec0d. | IMPLEMENTADA_VALIDADA; teste cobre gate, Caminhos, slots, Doutrina, DEF/expiração, reconnect e Retaliação; validação PG histórica. |
| Sentinela | Golpe de Rechaço (34) | sem ID runtime | 145% ATQ; com Retaliação, +10 p.p. PER; CD4, melee. | Somente creation_copy.json; sem Action/configuração/teste. | SOMENTE_REFERENCIADA; Retaliação genérica não é a Arte. |
| Errante | Corte Veloz (1) | class_art.errante.corte_veloz | 115% ATQ, inimigo único, CD2, melee; Oportunismo quando elegível. | errante_player_actions; test_errante_trial.py, test_class_trials.py, test_class_mechanics.py; base 6e3532a e predecessores. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta conformance PG integral. |
| Errante | Ferida Profunda (4) | class_art.errante.ferida_profunda | 90% + 1 Sangramento, CD2, melee, inimigo único. | class_trials.py; test_errante_trial.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; faltam stack/tick/reconnect por Arte. |
| Errante | Passo Velado (7) | class_art.errante.passo_velado | +15 p.p. Esquiva própria 1T; próximo Dano Direto +10 p.p. CRIT em 2T; CD4, sem arma. | class_trials.py/codec; test_errante_trial.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta cobertura PG completa de janela/cancelamento. |
| Errante | Golpe Oportuno (9) | class_art.errante.golpe_oportuno | 125% ATQ; alvo com efeito negativo: +15 p.p. CRIT; CD3, melee. | class_trials.py; test_errante_trial.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta prova integrada do bônus, arma e CD por Arte. |
| Errante | Corte Duplo (18) | class_art.errante.corte_duplo | Dois hits separados de 60%, um alvo/ação, CD3, melee. | hit_count=2; test_errante_trial.py, test_active_arts.py, test_weapon_metadata.py; commit 91249e72d23ffa4375bdee0e1bd31be6888afdfa; mocks 7faae02. | IMPLEMENTADA_VALIDADA; testes cobrem resolução por hit, Oportunismo por ação e persistência/reconnect. |
| Errante | Brecha Mortal (34) | sem ID runtime | 130% ATQ; alvo sob efeito negativo: +10 p.p. PER; CD3, melee. | Somente copy; sem Action/configuração. | SOMENTE_REFERENCIADA; Oportunismo não implementa a Arte. |
| Vigia | Disparo Preciso (1) | class_art.vigia.disparo_preciso | 115% ATQ, inimigo único, CD2, Arco/Besta; Mira global. | vigia_player_actions; test_vigia_tecelao_trials.py, test_class_trials.py, test_weapon_metadata_integration.py; base c3977d5. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta conformance PG integral. |
| Vigia | Marca da Presa (4) | class_art.vigia.marca_da_presa | 85% + −8% DEF por 2T, CD3, Arco/Besta. | class_trials.py; test_vigia_tecelao_trials.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta prova integrada de debuff/Mira/arma. |
| Vigia | Saraivada (7) | class_art.vigia.saraivada | 3×40% ATQ, CD3, Arco/Besta; resolução por hit. | Action multi-hit; test_vigia_tecelao_trials.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; testes correlatos não provam todas resoluções por modo. |
| Vigia | Olho da Vigília (9) | class_art.vigia.olho_da_vigilia | +12 p.p. PER e +8 p.p. CRIT por 2T, CD4, sem arma. | class_trials.py; test_vigia_tecelao_trials.py, test_class_trials.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta conformance PG de stats/duração/reconnect. |
| Vigia | Tiro Calculado (18) | class_art.vigia.tiro_calculado | 125%; com ≥2 Miras no alvo no começo, +10 p.p. CRIT; CD3, Arco/Besta; não consome Mira. | tests/test_tiro_calculado.py, test_active_arts.py, test_doctrine_path_arts.py, test_weapon_metadata.py; commit 01da91877db7b772e1812f0ae0f9c45b7aab4fb4; mocks 747f5e6. | IMPLEMENTADA_VALIDADA; teste cobre bônus na resolução, seleção de alvo e não retroatividade. |
| Vigia | Voleio (34) | sem ID runtime | 75% ATQ AoE contra todos inimigos elegíveis, CD3, Arco/Besta. | Só creation_copy; sem Action. | SOMENTE_REFERENCIADA; AoE genérica não é Arte. |
| Tecelão | Fio Cortante (1) | class_art.tecelao.fio_cortante | 120% ATQ, inimigo único, CD2, sem arma; Trama. | tecelao_player_actions; test_vigia_tecelao_trials.py, test_class_mechanics.py; base c3977d5. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta conformance PG integral. |
| Tecelão | Chama Tecida (4) | class_art.tecelao.chama_tecida | 85% + Queimadura, CD2, sem arma, inimigo único. | class_trials.py; test_vigia_tecelao_trials.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; faltam stack/tick/reconnect por Arte. |
| Tecelão | Ruptura da Trama (7) | class_art.tecelao.ruptura_da_trama | AoE 80% ATQ, CD3, sem arma; uma ação/Trama. | test_vigia_tecelao_trials.py, test_multi_target_combat.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta conformance integrada de todos alvos/efeitos. |
| Tecelão | Véu Entrelaçado (9) | class_art.tecelao.veu_entrelacado | Barreira própria 90% ATQ/2T, CD3, sem arma; Trama. | test_vigia_tecelao_trials.py, test_class_mechanics.py, test_barrier_sources.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta configuração/source/expiração por Arte em PG. |
| Tecelão | Geada Tecida (18) | class_art.tecelao.geada_tecida | 90% + −15% AGI por 2T, CD3, sem arma; Trama. | tests/test_geada_tecida.py; commit 693937507f70772e3103b62578c3b7bf514f5f94. | IMPLEMENTADA_VALIDADA; teste cobre dano, efeito/duração, erro, Trama, Caminhos e configuração PG. |
| Tecelão | Surto do Véu (34) | sem ID runtime | 145% ATQ, alvo único, CD3, sem arma; Trama. | Só copy; sem Action. | SOMENTE_REFERENCIADA. |
| Oráculo | Sinal Funesto (1) | class_art.oraculo.sinal_funesto | 105% + −8% ATQ por 2T, CD2, sem arma; Presságio ofensivo válido. | oraculo_player_actions; test_oraculo_luminar_trials.py, test_class_mechanics.py; base b918075. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta prova PG específica do ciclo de Presságio. |
| Oráculo | Vislumbre (4) | class_art.oraculo.vislumbre | +10% AGI por 2T a si/aliado, CD3, sem arma. | class_trials.py; test_oraculo_luminar_trials.py, test_class_trials.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta seleção/modo/reconnect específicos. |
| Oráculo | Ruína Predita (7) | class_art.oraculo.ruina_predita | 120% ATQ, CD2, sem arma, interage com Presságio. | class_trials.py; test_oraculo_luminar_trials.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta conformance de bônus/consumo por Arte. |
| Oráculo | Véu Premonitório (9) | class_art.oraculo.veu_premonitorio | Barreira 70% ATQ própria/2T; −10% magnitude de Debuff enquanto ativa; CD4, sem arma. | class_trials.py; test_oraculo_luminar_trials.py, test_class_mechanics.py, test_barrier_sources.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta prova de duração/reconnect específica. |
| Oráculo | Augúrio Favorável (18) | class_art.oraculo.augurio_favoravel | +10% ATQ por 2T a si/aliado; CD4, sem arma; Presságio Defensivo após buff válido. | tests/test_augurio_favoravel.py, test_oraculo_luminar_trials.py, test_round_domain.py; commit e790fb976a8961a223c07eb34ca95f1479e9dd9a. | IMPLEMENTADA_VALIDADA; prova buff/alvo/marca/renovação/configuração. |
| Oráculo | Selo da Queda (34) | sem ID runtime | 100% + −10% DEF por 2T, CD3, sem arma; Presságio segundo regra global. | Só copy; sem Action/configuração. | SOMENTE_REFERENCIADA. |
| Luminar | Fulgor (1) | class_art.luminar.fulgor | 110% ATQ Luz, inimigo único, CD2, sem arma; máquina Fulgor/Julgamento. | class_trials.py/combat.py; test_oraculo_luminar_trials.py, test_class_mechanics.py; base b918075. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta alternância PG em todos modos. |
| Luminar | Renovação (4) | class_art.luminar.renovacao | Cura 85% ATQ a si/aliado, CD2, sem arma. | Action de Cura; test_oraculo_luminar_trials.py, test_class_trials.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; faltam alvo/overheal/reconnect por Arte. |
| Luminar | Égide Solar (7) | class_art.luminar.egide_solar | Barreira 90% ATQ por 2T em alvo elegível, CD3, sem arma. | Action; test_oraculo_luminar_trials.py, test_class_mechanics.py, test_barrier_sources.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta conformance PG por Arte. |
| Luminar | Julgamento (9) | class_art.luminar.julgamento | 130% + −15% Cura recebida por 2T, CD3, sem arma; estado de Luz. | Action de dano/debuff; test_oraculo_luminar_trials.py, test_class_mechanics.py. | IMPLEMENTADA_TESTES_INSUFICIENTES; falta prova PG do debuff/duração por Arte. |
| Luminar | Luz Restauradora (18) | class_art.luminar.luz_restauradora | Cura 70% + Barreira 35% ATQ por 2T, CD4, sem arma; híbrida. | tests/test_luz_restauradora.py, test_barrier_sources.py; commit 865f4dd; motor dd24e30; estabilização 747f5e6. | IMPLEMENTADA_VALIDADA; teste focal cobre híbrido, alvo/recurso/source; histórico, não repetido. |
| Luminar | Explosão Solar (34) | sem ID runtime | AoE Luz 85% ATQ, CD3, sem arma. | Só copy; AoE genérica não é registro. | SOMENTE_REFERENCIADA. |

## 4. Matriz individual das 48 Artes de Caminho

O GDD não publica IDs de máquina; Aríete é o único Path Art com ID runtime. arts.py/PATH_ART_IDS_BY_PATH e path_arts.py/PATH_ART_ACTIONS registram só Aríete. Para as outras 47, a ausência de Action também significa ausência de elegibilidade, slot, Doutrina, snapshot de ação e UI executável. Teste de componente compartilhado não é teste da Arte.

| Classe · Caminho | Arte (Nv.) | Contrato GDD resumido (§49.3/55/56) | Evidência atual e estado |
|---|---|---|---|
| Sentinela · Bastião | Escudo de Cinzas (12) | Barreira própria 95% ATQ/2T, CD3; sem arma; Fortaleza melhora Barreira. | Sem registro ou Action; barreira genérica não conta. AUSENTE. |
| Sentinela · Bastião | Interpor (22) | Próximo Dano Direto recebido pelo aliado em 2T −25%; CD4; sem arma. | Sem ID/Action/proteção-alvo. AUSENTE. |
| Sentinela · Bastião | Contra-Golpe (38) | 120% ATQ; com Retaliação aplica −10% ATQ/2T; CD3; melee; consome carga elegível. | Retaliação existe, Action não. AUSENTE. |
| Sentinela · Bastião | Última Muralha (52) | Barreira 65% ATQ em todos aliados/2T; CD5; sem arma. | Sem Action aliada AoE. AUSENTE. |
| Sentinela · Devastador | Aríete (12) | 135% ATQ +10 p.p. PER; alvo único; CD2; melee; Retaliação/Ímpeto Doloroso. | path_art.sentinela.devastador.ariete em path_arts.py; catálogo/gate/metadata e snapshot; test_path_arts.py, test_active_arts.py, test_firmeza.py; c181c00; PG histórico. IMPLEMENTADA_VALIDADA. |
| Sentinela · Devastador | Golpe de Ruptura (22) | 125% ou 150% ATQ com Retaliação; CD3; melee; consumo no commit. | Sem Action; teste de Retaliação só cobre a fundação. AUSENTE. |
| Sentinela · Devastador | Abalo (38) | AoE 90% + −8% DEF/2T; CD4; melee. | Sem híbrido de Caminho. AUSENTE. |
| Sentinela · Devastador | Ruptor (52) | 170%; se HP próprio <50%, +10% potência; CD5; melee. | Condição HP genérica não define a Arte. AUSENTE. |
| Errante · Carrasco | Corte de Execução (12) | 135%; alvo ≤35% HP recebe +15% potência; CD3; melee; Sentença/Oportunismo. | Sem ID/Action. AUSENTE. |
| Errante · Carrasco | Hemorragia (22) | 95% +2 Sangramentos; CD3; melee. | DoT geral não configura stacks da Arte. AUSENTE. |
| Errante · Carrasco | Marca da Morte (38) | 80%; próxima Arte direta Carrasco em 2T +12%; CD4; melee. | Sem efeito preparado vinculado. AUSENTE. |
| Errante · Carrasco | Ceifa (52) | 165%; alvo ≤40% HP: +10 p.p. CRIT; CD5; melee. | Sem condição/Action. AUSENTE. |
| Errante · Sabotador | Veneno Velado (12) | 85% + Veneno; CD2; melee; DoT conforme regra geral. | Veneno não é registro da Arte. AUSENTE. |
| Errante · Sabotador | Fio Cortado (22) | 95% + −12% ATQ/2T; CD3; melee; Interferência se elegível. | Sem Action. AUSENTE. |
| Errante · Sabotador | Trava de Passos (38) | 80% + −18% AGI/2T; CD3; melee; Interferência. | Debuff de Geada não é a Arte. AUSENTE. |
| Errante · Sabotador | Colapso Preparado (52) | 120% +10% por efeito negativo distinto, teto +30%; CD5; melee. | Sem Action/contagem distinta. AUSENTE. |
| Vigia · Atirador | Tiro Perfurante (12) | 130% +10 p.p. PER; CD2; Arco/Besta; Mira Perfeita. | Tiro Calculado e Mira genérica não são a Action. AUSENTE. |
| Vigia · Atirador | Fixar Alvo (22) | 100% +1 Mira; CD3; Arco/Besta; limites/troca Atirador. | Sem Action/ID. AUSENTE. |
| Vigia · Atirador | Rajada Controlada (38) | 3×45%; CD3; um alvo; Arco/Besta. | Saraivada/Corte Duplo não são a Arte. AUSENTE. |
| Vigia · Atirador | Disparo Terminal (52) | Requer 4 Miras; 175% +15 p.p. CRIT; CD5; consome 4 pós-resolução; Arco/Besta. | Ramo sintético de Mira não registra Action. AUSENTE. |
| Vigia · Rastreador | Flecha Serrilhada (12) | 90% + Sangramento; CD2; Arco/Besta; Mira pelo gatilho válido. | Sem Action. AUSENTE. |
| Vigia · Rastreador | Laço de Caça (22) | 80% + −20% AGI/2T; CD3; Arco/Besta; Mira conforme gatilho. | Debuff de Geada é infraestrutura. AUSENTE. |
| Vigia · Rastreador | Chuva de Rastros (38) | AoE 70% +1 Mira por alvo; CD4; Arco/Besta. | AoE/Mira genéricas não formam a Action. AUSENTE. |
| Vigia · Rastreador | Predação Persistente (52) | 135% +8% por DoT/Debuff distinto, máximo +16%; CD4; Arco/Besta. | Sem Action/contagem por alvo. AUSENTE. |
| Tecelão · Conjurador | Estilhaço do Véu (12) | 140% ATQ, inimigo único; CD2; sem arma; Convergência. | Trama comum não implementa Arte. AUSENTE. |
| Tecelão · Conjurador | Incêndio Trançado (22) | AoE 75% + Queimadura; CD3; sem arma. | Chama Tecida não é AoE/Arte de Caminho. AUSENTE. |
| Tecelão · Conjurador | Convergência Arcana (38) | 3×50%; CD3; alvo(s) conforme fonte; sem arma; Trama. | Multi-hit genérico não é Action. AUSENTE. |
| Tecelão · Conjurador | Rasgo Conjurado (52) | AoE 125%; CD5; sem arma. | Sem registro. AUSENTE. |
| Tecelão · Rúnico | Runa de Guarda (12) | Barreira 105%/2T; CD3; alvo de proteção; sem arma; Inscrição +15%. | Motor multi-barreira não é a Action. AUSENTE. |
| Tecelão · Rúnico | Runa de Ruptura (22) | 90% + −10% DEF/2T; CD3; sem arma; Inscrição. | Geada compartilha debuff, sem identidade da Arte. AUSENTE. |
| Tecelão · Rúnico | Runa de Retorno (38) | Cura 70% + Purificação 1; CD4; sem arma; Inscrição +15% Cura. | 9b886db é fundação, não Action da Runa. AUSENTE. |
| Tecelão · Rúnico | Círculo Rúnico (52) | Barreira AoE 60%/2T a aliados; CD5; sem arma. | Sem Action de suporte AoE. AUSENTE. |
| Oráculo · Agoureiro | Mau Agouro (12) | 95% + −10% ATQ/2T; CD2; sem arma; Mau Presságio. | Presságio genérico não implementa Arte. AUSENTE. |
| Oráculo · Agoureiro | Destino Lento (22) | 70% + −18% AGI/2T; CD3; sem arma. | Sem Action. AUSENTE. |
| Oráculo · Agoureiro | Condenação (38) | 80%; próxima Arte Agoureiro +20% por 2T; CD4; sem arma. | Sem preparação específica. AUSENTE. |
| Oráculo · Agoureiro | Eclipse Previsto (52) | 150%; se consumir Presságio, −15% Cura recebida/2T; CD5; sem arma. | Sem consumidor Action. AUSENTE. |
| Oráculo · Invocador | Lobo (12) | 125%; CD2; sem arma; manifestação Lobo em janela 2T. | Tríade genérica não é Arte equipável. AUSENTE. |
| Oráculo · Invocador | Coruja (22) | 85% + −15% AGI/2T; CD3; sem arma; manifestação. | Sem Action. AUSENTE. |
| Oráculo · Invocador | Urso (38) | Barreira própria 100%/2T; CD3; sem arma; manifestação. | Sem Action. AUSENTE. |
| Oráculo · Invocador | Tríade Encarnada (52) | CD5; Lobo→155% dano; Coruja→95% + −20% AGI/2T; Urso→Barreira 120%/2T; não altera manifestação. | Máquina Tríade não tem os três resultados da Arte. AUSENTE. |
| Luminar · Guardião | Cura Solar (12) | Cura 100% ATQ a aliado; CD2; sem arma; Aurora. | Renovação/Luz não são esta Action. AUSENTE. |
| Luminar · Guardião | Égide Compartilhada (22) | Barreira 90% no aliado +45% em si; CD4; self-target só recebe 90%; sem arma. | Barreiras genéricas não implementam exceção. AUSENTE. |
| Luminar · Guardião | Purgação Luminosa (38) | Cura 65% + Purificação 1; CD4; sem arma. | Purificação 9b886db não registra Arte. AUSENTE. |
| Luminar · Guardião | Aurora Guardiã (52) | Cura AoE 55% para aliados; CD5; sem arma. | Sem execução da Arte. AUSENTE. |
| Luminar · Inquisidor | Lança de Luz (12) | 135% Luz, inimigo único; CD2; sem arma; Julgamento Implacável. | Julgamento genérico não é Action. AUSENTE. |
| Luminar · Inquisidor | Selo da Penitência (22) | 100% + −20% Cura recebida/2T; CD3; sem arma. | Sem registro. AUSENTE. |
| Luminar · Inquisidor | Purga Ardente (38) | 120% + Dispel 1 efeito positivo; CD4; sem arma. | Fundação 9b886db não registra essa híbrida. AUSENTE. |
| Luminar · Inquisidor | Veredito (52) | 170%; alvo com Debuff: +10 p.p. CRIT; CD5; sem arma. | Sem Action. AUSENTE. |

## 5. Seis Artes de Classe Nv.18

| Arte | Evidência inspecionada | Estado |
|---|---|---|
| Firmeza — Sentinela | arts.py/class_trials.py; tests/test_firmeza.py; 4748add6dc079c6a7e785bbf9de6dd0af17cec0d. | IMPLEMENTADA_VALIDADA. Buff +12% DEF/2T/CD3; gates, caminhos, arma, slots/Doutrina, efeito, expiração e reconnect cobertos; PG reportado historicamente. |
| Corte Duplo — Errante | Action hit_count=2; tests/test_errante_trial.py; 91249e72d23ffa4375bdee0e1bd31be6888afdfa; mocks 7faae02. | IMPLEMENTADA_VALIDADA. 2×60%, CD3; hits separados, Oportunismo por ação, snapshot e persistência cobertos. |
| Tiro Calculado — Vigia | tests/test_tiro_calculado.py; 01da91877db7b772e1812f0ae0f9c45b7aab4fb4; mocks regionais 747f5e6. | IMPLEMENTADA_VALIDADA. 125%, +10 p.p. CRIT com 2+ Miras no alvo no início, CD3, Arco/Besta; bônus real e não retroatividade testados. |
| Geada Tecida — Tecelão | tests/test_geada_tecida.py; 693937507f70772e3103b62578c3b7bf514f5f94. | IMPLEMENTADA_VALIDADA. 90%, −15% AGI/2T, CD3; Trama, Conjurador/Rúnico, erro/expiração e configuração cobertos. |
| Augúrio Favorável — Oráculo | tests/test_augurio_favoravel.py; e790fb976a8961a223c07eb34ca95f1479e9dd9a. | IMPLEMENTADA_VALIDADA. +10% ATQ/2T, CD4; self/ally, Presságio defensivo, renovação e configuração cobertos. |
| Luz Restauradora — Luminar | tests/test_luz_restauradora.py; 865f4dd961b5948ff1a9442f3700d8a6d14341b7; motor dd24e30; mocks 747f5e6. | IMPLEMENTADA_VALIDADA. Cura 70% + Barreira 35%/2T, CD4; ação híbrida, Fulgor/Julgamento, target e fontes de barreira cobertos. Evidência histórica, não repetida. |

As seis são Artes de Classe Nv.18, não dependem de Caminho específico; permanecem sob o limite de três slots e suas respectivas regras de arma. Nada aqui adiciona slot ou torna outra Classe elegível.

## 6. Seis Artes Nv.34

| Arte | Contrato GDD | Estado/dependências e aceite futuro |
|---|---|---|
| Golpe de Rechaço — Sentinela | 145% ATQ; com Retaliação, +10 p.p. PER; CD4; melee. | Só referenciada. Reutilizar Retaliação/condicionais. Testar gate, carga presente/ausente, PER na resolução, consumo no commit, erro posterior, tag, Doutrina e reconnect. |
| Brecha Mortal — Errante | 130%; alvo com efeito negativo: +10 p.p. PER; CD3; melee. | Só referenciada. Reutilizar Oportunismo e snapshot inicial. Testar condição por alvo e não retroatividade, Precisão, arma e slots. |
| Voleio — Vigia | 75% contra todos inimigos elegíveis; AoE; CD3; Arco/Besta. | Só referenciada. Reutilizar AoE/metadata. Testar alvos, resolução e efeitos por alvo versus ação, Grupo. |
| Surto do Véu — Tecelão | 145%, inimigo único, CD3, sem arma; Trama. | Só referenciada. Reutilizar Trama; testar origem/consumo, erro pós-commit, sem dupla potência, persistência. |
| Selo da Queda — Oráculo | 100% + −10% DEF/2T; CD3; sem arma; Presságio quando elegível. | Só referenciada. Reutilizar Debuff/Presságio; testar imunidade, aplicação real, alvo e duração. |
| Explosão Solar — Luminar | AoE Luz 85%; CD3; sem arma; Fulgor/Julgamento conforme elegibilidade de Dano Direto. | Só referenciada. Reutilizar AoE/estado Luminar; testar multi-alvo e consumo único. |

As seis não têm ID/Action nem teste próprio; componentes compartilhados não contam como implementação.

## 7. Fundações e riscos transversais

| Área | Evidência local | Estado/limite |
|---|---|---|
| Catálogo, gates, slots | arts.py: 30 Artes de Classe; active_arts.py valida Classe/nível/Caminho/arma, três slots e persistência. path_arts.py: uma Arte. | Pipeline compartilhado; 53 ações ausentes. |
| Dano/acerto/crítico e condições | combat.py; test_class_mechanics.py; testes das Artes recentes. | Motor existe, não existe matriz de conformidade 84/84. |
| Multi-hit | Action.hit_count, Saraivada e Corte Duplo; test_vigia_tecelao_trials.py/test_errante_trial.py. | Casos concretos validados, não as Artes futuras. |
| AoE | Resolvedor multi-alvo; test_multi_target_combat.py. | Não implica Voleio/Explosão Solar nem Artes AoE de Caminho. |
| Buff/Debuff/DoT/duração | ActionEffect/estados; Firmeza e Geada. | Reaplicação, imunidade e duração ainda requerem prova por Arte. |
| Cura+Barreira | Luz Restauradora em uma Action. | Um híbrido provado, não todas as combinações/áreas. |
| Múltiplas Barreiras | Fonte por applier+effect, substituição da mesma fonte, FIFO determinístico, cap agregado PvP e leitura legada; dd24e30, test_barrier_sources.py. | Infraestrutura compartilhada; não implementa Artes ausentes. |
| Purificação/Dispel | Fundação 9b886db. | Runa de Retorno, Purgação Luminosa e Purga Ardente não são executáveis. |
| Recursos condicionais | Fundação 8421010; Retaliação, Oportunismo, Mira, Trama, Presságio, Fulgor/Julgamento; test_class_mechanics.py. | Não transforma consumidores ausentes, como Disparo Terminal, em Artes executáveis. |
| Alvos self/ally | Augúrio e Luz têm seleção explícita e testes. | Não prova target AoE/Grupo das futuras Artes. |
| Snapshot/reconnect/idempotência | active_arts e codecs; testes de Firmeza, Corte Duplo, Tiro, Geada, Augúrio, Luz; mocks estabilizados 7faae02/747f5e6. | Cobertura desigual para 24 iniciais; requer regressões por novo ID. |
| Weapon Metadata/Doutrina | Tags explícitas em arts.py/application/weapon_metadata.py; test_weapon_metadata.py, test_weapon_metadata_integration.py, test_doctrine_path_arts.py. | Toda Arte futura precisa declarar e testar sua tag; sem inferência por nome. |
| Ronda | application/round.py tem política de recuperação que considera Artes equipadas com componente de Cura, incluindo Luz Restauradora. | Não foi executada nesta auditoria; Augúrio Favorável não é Arte de recuperação e não é selecionada por essa regra. |
| Provações | test_class_trials.py e módulos por Classe. | test_final_checkpoint_unlocks_both_paths_once_without_selection_or_reward[luminar-expected_paths0-art_ids0-997309] permanece historicamente intermitente, causa desconhecida; não executado. |
| P12 | docs/audits/ASTERION_DIAGNOSTICO_REGRESSOES_FASE4B00.md documenta playthrough não concluído; arquivos atuais seguem modificados. | Vitória e conclusão Solo legítimas seguem pendentes. |

## 8. Impacto por nível

| Faixa | Estado |
|---|---|
| Nv.1–10 | 24 Artes de Classe executáveis; testes específicos ainda insuficientes. |
| Nv.11–20 | Seis Artes de Classe Nv.18 e Aríete estão disponíveis; outras 11 primeiras Artes de Caminho ausentes. |
| Nv.21–30 | As 12 Artes de Caminho Nv.22 estão ausentes. |
| Nv.31–40 | Seis Artes de Classe Nv.34 só referenciadas; 12 Artes de Caminho Nv.38 ausentes. |
| Nv.41–50 | Não há novo nível de Arte; lacunas anteriores persistem. |
| Nv.51–60 | As 12 Artes de Caminho Nv.52 estão ausentes; nível 60 tem 30 IDs de Classe e um ID de Caminho, não 84. |

Disponibilidade não significa uso simultâneo: três slots permanecem o limite.

## 9. Riscos P0–P3

| Nível | Achado | Impacto |
|---|---|---|
| P0 | Nenhuma corrupção, exploração ou quebra sistêmica grave comprovada pela inspeção estática. | Nenhum P0 identificado. |
| P1 | 47 Artes de Caminho ausentes + seis Artes Nv.34 somente referenciadas. | 53/84 contratos não são jogáveis. |
| P2 | 24 Artes iniciais sem evidência específica de todos os campos; flakiness histórica do Luminar sem causa; auditoria atual sem execução de testes; P12 sem conclusão provada. | Riscos de contrato, integração e validação; P12 é pendência operacional separada. |
| P3 | Nenhuma melhoria não bloqueante comprovada. | Nenhum P3 novo. |

## 10. Fila de implementação

| Ordem | Escopo | Dependências e critérios de aceite |
|---:|---|---|
| 1 | Harness de conformidade para as 31 Artes executáveis. | GDD §49, Weapon Metadata e pipeline atual. Para cada ID testar dono, nível, Caminho, arma, alvo, potência/efeito, duração/CD, slot/Doutrina, snapshot e combate. Não registrar futuro. |
| 2 | Golpe de Rechaço, próxima recomendada. | Primeira Arte Classe Nv.34; Retaliação/condicionais e tag melee existem. Testar Nv.33/34, carga, +10 p.p. PER efetiva, commit, erro posterior, CD4, Doutrina/reconnect. |
| 3 | Demais Artes Nv.34 em commits isolados: Brecha Mortal, Voleio, Surto do Véu, Selo da Queda, Explosão Solar. | Oportunismo, AoE/arma, Trama, Presságio e Fulgor/Julgamento. Testar contrato individual, recursos, alvos, UI e integração pertinente. |
| 4 | Caminhos Sentinela (7 faltantes). | Barreira, proteção de próximo dano, Retaliação, AoE/debuff, threshold HP; testar source/alvo/duração/commit. |
| 5 | Caminhos Errante (8). | DoT/stacks, Oportunismo, condições de HP, efeitos preparados/distintos; testar snapshots, arma, consumo e reconnect. |
| 6 | Caminhos Vigia (8). | Mira, custo pós-resolução, AoE/multi-hit, tags Arco/Besta; testar limites, alvos, ação/hit, consumo e mudança de alvo. |
| 7 | Caminhos Tecelão (8). | Trama, AoE/multi-hit, cura/barreira/Purificação; testar origem, consumo único, híbridos e codec. |
| 8 | Caminhos Oráculo (8). | Presságio, preparação, manifestações; testar alvo/marca, janelas e resultados ramificados. |
| 9 | Caminhos Luminar (8). | Cura/Barreira, AoE, Purificação/Dispel, Fulgor/Julgamento; testar alvo vivo, source, recursos e Ronda. |
| 10 | Regressão transversal e P12 como tarefa independente. | PostgreSQL reproduzível; posteriormente playthrough legal P7–P12 com vitória, settlement, conclusão e gate Nareth. |
| 11 | Reauditoria 84/84. | 84 IDs/Actions reais e teste, sem contar infraestrutura, skips ou xfails como implementação. |

Próxima recomendada: Golpe de Rechaço. É a primeira Arte de Classe Nv.34 e reutiliza Retaliação e requisitos condicionais já existentes, limitando novas dependências. Isso não implica mudança de balanceamento nem resolução de P12.

## 11. Limitações e verificações documentais

Inspecionados código, testes, fontes e commits; não houve PostgreSQL, pytest, Ruff, AST de execução, Alembic ou suíte global, conforme escopo. Resultados anteriores são históricos. Existência de módulo de teste não comprova todos os campos de cada Arte. Classificação das 24 iniciais é conservadora.

Conferência: 84 entradas únicas; 36 Artes de Classe, seis por Classe; 48 de Caminho, quatro por Caminho; soma dos estados 7+24+0+6+47=84. Ataque Básico, Defender, passivas e Talentos excluídos. Nenhuma fonte, produção, teste ou regra numérica foi alterada. Este relatório é o único arquivo novo da tarefa.

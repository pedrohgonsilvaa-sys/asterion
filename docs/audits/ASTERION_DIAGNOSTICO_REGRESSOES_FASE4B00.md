# ASTERION — Diagnóstico das regressões da Fase 4B-00

**Data:** 2026-10-19
**Escopo:** diagnóstico das duas falhas reportadas na suíte global; nenhuma correção de produção, teste, migration ou balanceamento foi feita.

## Resumo executivo

O checkout estava em `main`, no HEAD esperado `1ba18415cb62a970c10edab4019e3fbd4650b397`, com arquivos rastreados e staged limpos no início. O SHA-256 da Bíblia Canônica v3.0 FINAL foi confirmado como `f42484b09bff21712e8fb72d71d7eba3d19e0c3b4543a5b2d94adb1e7e864a15`.

As duas falhas têm naturezas diferentes:

1. **Várzeas:** a falha é comprovadamente uma expectativa de data obsoleta no teste. O índice de autoridade foi atualizado em 18/10; a Fonte Regional foi consolidada em 15/10. Não há divergência de versão ou de autoridade, e as verificações de Barreira aplicáveis continuam válidas.
2. **P12:** o percurso chega legitimamente à Matriarca, mas o plano automatizado de oito tentativas não a derrota. Uma execução anterior falhou ainda na preparação por incompatibilidade entre o equipamento selecionado e a troca de Artes; a reexecução ultrapassou essa falha, chegou ao chefe e perdeu na tentativa final com 893/2.548 HP restantes. O motivo imediato da falha do teste está demonstrado; não há evidência suficiente para atribuir o resultado a defeito de combate, progressão ou persistência, nem para afirmar desequilíbrio ou inviabilidade da Classe. A política exercitada deixa recursos táticos sem avaliação conclusiva.

**Conclusão diagnóstica:** A tem causa raiz fechada. B é uma falha reproduzida do roteiro/preparação de teste; permanece por provar se uma estratégia legal alternativa vence em fluxo público. Não houve alteração de código ou testes e a suíte global de 1.630 casos não foi repetida, conforme o escopo desta investigação.

## 1. Checkout e autoridades conferidas

| Item | Evidência |
|---|---|
| Branch / HEAD inicial | `main` / `1ba18415cb62a970c10edab4019e3fbd4650b397` |
| Estado inicial | Nenhuma alteração tracked/staged. Havia conteúdo untracked preexistente em `.worktrees/` e `ASTERION_CONTEUDO_ALTOS_CINEREOS_v1.0.1_PROPOSTA.md`; ambos foram preservados. O tracking local indicava `main` 56 commits à frente de `origin/main`; não foi feito fetch nem operação remota. |
| Bíblia v3.0 FINAL | SHA-256 verificado: `f42484b09bff21712e8fb72d71d7eba3d19e0c3b4543a5b2d94adb1e7e864a15`. |
| GDD v1.6.0 | Presente; SHA-256 local `0c9245861da2af8ed13944607f47b9122165d38e5a919f8b3dbaa668b65550aa`. |
| Contrato Global Weapon Metadata | Presente e registrado; SHA-256 local `c283b398949dc0a864d98b9e0e9031080a50b937db6932ffcde7d46e600aa740`. |
| Índices de autoridade | `SOURCE_AUTHORITY.md` e `docs/SOURCE_AUTHORITY.md` são idênticos. A seleção atual indica Várzeas v1.0.3 FINAL e Confins v1.0.0 FINAL. |
| Fontes Regionais FINAL | TDO v1.0.16 `8fdbe5e61216d0a2b9b62b60e5666361584055b266afbf2238437abc59b4954b`; Vales v1.0.6 `d88a247dcf1d384ebc3385faa77c80f25b0cef114ccc6e71191b112117159247`; Nareth v1.0.2 `758add317d856f6890284c4a7fd09457716b3f21f8094b2619c21245ba7e8470`; Várzeas v1.0.3 `d3772463786daff9f7748dff9a1bbf2761c3bf0f4f96848b460e16131cd70628`; Altos v1.0.1 `e3ee5a1dbbe81b51cd63464cdc043629afff705a0167cd60feee9abe80d54d6f`; Confins v1.0.0 `c86a0208888d14bbd653cda6174956df89b2233304dcca523d878b5b42a102fc`. |

O aviso de `git status` não conseguiu enumerar `.pytest_tmp/` por falta de permissão. Nenhum conteúdo desse diretório foi lido, alterado ou limpo; ele não foi usado pelos testes (`-p no:cacheprovider`).

## 2. Falha A — autoridade das Várzeas

### Resultado da reprodução

Teste isolado executado:

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe -m pytest -q tests/test_varzeas_v1_0_1_source_contract.py::test_varzeas_source_authority_is_current_and_has_no_global_barrier_default
```

**Resultado:** 1 failed. A falha ocorre em `tests/test_varzeas_v1_0_1_source_contract.py:65`, na asserção literal:

```python
assert "**Índice atualizado:** 2026-10-15." in authority
```

Reexecução de todo o módulo, sem cache de pytest:

```powershell
$env:PYTHONPATH='src;.'
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -vv tests/test_varzeas_v1_0_1_source_contract.py
```

**Resultado:** 3 passed, 1 failed. A única falha continua sendo a asserção de data.

### Causa raiz comprovada

O teste compara a data do cabeçalho de `SOURCE_AUTHORITY.md`, não a data de consolidação da Fonte Regional. O índice atual, na linha 3, declara `2026-10-18`; sua sincronização regional de 18/10 registra Confins e mantém Várzeas v1.0.3 como vigente. Já a Fonte `ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.3_FINAL.md`, linha 4, declara **data de consolidação `2026-10-15`**. São datas de eventos diferentes, portanto não indicam conflito de autoridade.

O teste passa pelas asserções anteriores de espelhamento dos índices, seleção da v1.0.3 e arquivo vigente antes de parar na data. As verificações de duração de Barreira do módulo passaram:

* `test_varzeas_source_revision_only_closes_six_barrier_durations`;
* `test_varzeas_v1_0_2_only_adds_persistente_barrier_duration`;
* `test_varzeas_v1_0_2_publishes_all_seven_barrier_durations_explicitly`.

Além disso, a entrada da v1.0.3 em `SOURCE_AUTHORITY.md:75–79` diz que preserva todas as durações regionais de Barreira em `2T` e não cria default ou sistema universal. A Fonte v1.0.3 mantém seu escopo de esclarecimento e não altera os parâmetros de duração. As afirmações posteriores ao assert de data na função falha não foram executadas naquele teste; a ausência de default foi também conferida diretamente no texto atual do índice.

### Correção mínima recomendada

Corrigir apenas a expectativa do teste para distinguir a atualização do índice (`2026-10-18`) da consolidação da Fonte (`2026-10-15`). Manter as verificações de identidade/versão, arquivo vigente, espelho byte a byte, sucessão de versão e ausência de default global. Não modificar nenhum dos documentos oficiais.

**Aceite para a correção futura:** o teste isolado e todo o módulo passam contra os dois índices atuais; versões antigas, divergência entre espelhos e introdução de default global continuam provocando falha.

## 3. Falha B — percurso Solo TDO → P12

### Banco e execução

Foi usado PostgreSQL **16.15**, temporário, isolado e saudável, com porta dinâmica publicada somente em `127.0.0.1:50405`, diretório de dados em tmpfs e sem volume persistente. A fixture `tests/conftest.py:21–38` cria o engine de teste e chama `alembic upgrade head` usando a conexão PostgreSQL. Não houve conexão com produção. Ao terminar, foram removidos somente o container `asterion-4b00-pg16-mvfvqu1m` e a rede `asterion-4b00-net-mvfvqu1m` criados nesta execução.

O teste foi executado individualmente com `PYTHONPATH=src;.` e ambos os URLs de banco de teste apontando para o PostgreSQL temporário, além de `ASTERION_RUN_VDE_FULL_PLAYTHROUGH=1`:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -ra tests/test_vde_full_playthrough.py::test_vde_full_playthrough_from_fresh_tdo_exit
```

Uma tentativa inicial com `-s` foi interrompida por `UnicodeEncodeError` do console Windows CP1252 ao imprimir emoji. Isso é uma limitação de captura de saída e não foi contado como diagnóstico de jogo. A execução sem `-s` corrigiu essa limitação.

### Reproduções observadas

| Execução | Resultado | Evidência |
|---|---|---|
| Primeira execução sem `-s` | 1 failed após 270,89 s, antes do combate da Matriarca | O setup S6 tentou aplicar `P6_DIAGNOSTIC_LOADOUTS["B"]` — `Muralha Breve`, `Quebra Postura` e `Impacto Resoluto` — enquanto a otimização de equipamento havia selecionado `Arma Pesada do Caminhante`. A metadata canônica da arma é `weapon.form.bow`, duas mãos, slot principal de duas mãos e `weapon.compat.bow`; as três Artes exigem `weapon.compat.melee`. `ActiveArtService.equip_art` rejeitou a configuração candidata como `invalid_current_configuration`. |
| Segunda execução sem `-s` | 1 failed após 793,28 s; completou TDO e a preparação regional, entrou em P12, mas esgotou as oito tentativas | O assert final `tests/test_vde_full_playthrough.py:1593–1595` recebeu um estado de retry, não `examine_center`. Na oitava tentativa: Sentinela Nv.20 / Caminho Devastador; loadout C; chefe em Fase II com `893/2.548 HP` (`35,05%`); jogador terminou em `0/1.213 HP`; 19 ações/rodadas; 1.655 de dano efetivo causado e 1.213 recebidos. Não houve Consumível usado, alvo de Conexão selecionado ou Conexão destruída nessa tentativa. O chefe ficou imediatamente acima do gatilho de Fase III (`≤35%`). |

A execução atual corresponde à falha B solicitada e a reproduz. Como referência histórica, a auditoria Fase 4A havia registrado uma derrota anterior em `905/2.548 HP`, após 20 ações. As duas derrotas finais ficaram perto do limiar de 35%, mas são tentativas distintas e não provam um bloqueio matemático.

### Classe, progressão e preparação legal

O roteiro cria personagem novo e percorre TDO e Vales por serviços de jogo; não injeta XP nem ajusta diretamente atributos para obter a vitória. Ele chega ao gate P12 em Nv.20, como exige a missão. A captura de estado disponível durante o percurso registrou classe `sentinela`, caminho `devastador`, XP `18.820` e 8.180 Coroas antes do chefe. As oito tentativas usam os loadouts C, A e D e políticas Devastador/Sentinela-Devastador definidas no próprio teste.

Na tentativa final, os dados preservados no diagnóstico dão HP máximo de 1.213. A configuração ativa foi `golpe_de_guarda`, `muralha_breve` e `impacto_resoluto`; talentos `talent.sentinela.aco_desperto` e `talent.sentinela.carne_de_pedra`. O inventário de combate tinha três cada de Antídoto II, Proteção II e Purificação II, sem item de cura entre as opções daquela luta. A política consome cura somente se `consumable.heal.vde.ii` ou `consumable.heal` aparecer nas opções e HP ficar em 60% ou menos. O helper de preparação tenta fabricar até quatro curas II e também Antídoto/Proteção/Purificação pelas receitas públicas, mas o registro final não preserva aqui os motivos individuais pelos quais a cura não estava disponível; insuficiência de ingredientes/profissão é hipótese, não causa confirmada.

O equipamento da tentativa final era equipamento legal obtido pelo fluxo público e otimizado pelo helper do teste: arma comum `Arma do Vale` Nv.20, secundária `Guarda do Caminhante` Nv.19, peças comuns de corpo/pés Nv.20, cabeça rara Nv.12 e artefato raro Nv.5. O snapshot não mostrou Runa ou Encantamento nesses itens. O helper registra nível, HP, ATQ, DEF, AGI, PER, CRIT, Esquiva, Bloqueio, profissões, equipamento e estoque, mas os valores exatos de ATQ/DEF/AGI/PER/CRIT/Esquiva/Bloqueio e os motivos de indisponibilidade das receitas não foram recuperáveis do resumo de falha retido nesta execução; não são inferidos neste relatório.

### Comportamento da política de combate

`tests/test_vde_full_playthrough.py:1399–1435` executa estas prioridades:

1. Defender somente se há Ação Preparada `estrangulamento_vale`.
2. Usar cura apenas abaixo de 60% e se a opção constar na view.
3. Havendo Conexões vivas, usar a melhor Arte AoE legal disponível; se não houver, o alvo padrão vai ao chefe, exceto nas duas entradas do retry plan marcadas para perseguir Conexões.
4. Delegar as outras ações à política `choose_p6_policy_action`.

O plano `tests/test_vde_full_playthrough.py:1457–1466` limita a busca a oito configurações; duas tentativas priorizam uma Conexão e as demais focam o chefe. A derrota final não utilizou Consumível, não destruiu Conexões, não defendeu e usou `muralha_breve` seis vezes. As Conexões são opcionais, não hard gate; cada uma viva reduz em 4% o dano final do chefe. O combate havia causado dano suficiente para chegar a 35,05%, mas o personagem foi derrotado antes de reduzir o chefe aos 35% que iniciam a Fase III. Não há no registro uma vitória alternativa demonstrada.

### Contrato da Matriarca e evidência de implementação

A Fonte Vales v1.0.6, §14.1–14.4, determina Chefe de Campanha `HP 220% / ATQ 110% / DEF 110% / AGI 100%` antes dos demais modificadores; ataques básicos, Raiz Constritiva, Seiva Corrompida, Chicote, Varredura AoE, Abraço de Barreira e Estrangulamento preparado; três Conexões opcionais a partir de 70%; fase III em `≤35%`; sem cura própria e sem Estrangulamento em oportunidades consecutivas.

Evidência no código:

* `src/asterion/application/vde_missions.py:1185–1194` e `:1661–1670` criam o encontro P12 chamando `create_campaign_boss_profile` e `configure_matriarch_combat`.
* `src/asterion/application/campaign_coop.py:48` centraliza o perfil/scaling de Chefe de Campanha.
* `src/asterion/domain/vde_matriarch.py:29–145` instala as Artes, fases e três objetos/Conexões com aura de mitigação.
* `tests/test_vde_p12_matriarch_combat.py` contém as verificações de perfil/scaling, ativação das Conexões, Artes/fases/telegraph, snapshot de reconexão e seleção/destruição de Conexões.

Testes auxiliares executados:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -vv tests/test_vde_p12_matriarch_combat.py
```

**Resultado:** 5 passed.

```powershell
$env:PYTHONPATH='src;.'
# ASTERION_DATABASE_URL e ASTERION_TEST_DATABASE_URL apontaram ao PostgreSQL 16 temporário
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -ra -vv tests/test_vde_p12_matriarch_integration.py tests/test_vde_matriarch_bestiary_milestone.py
```

**Resultado PostgreSQL:** 3 passed em 15,89 s: vitória/settlement/choice, scaling Grupo e settlement elegível, e marco de Bestiário único. O teste de integração Solo materializa uma vitória ao ajustar diretamente o snapshot de combate para o chefe com 1 HP e fase III; ele testa settlement e idempotência, não a viabilidade de vencer naturalmente. Portanto, os testes unitários e de settlement não anulam a falha do percurso natural.

### Diagnóstico: comprovado, não demonstrado e hipóteses

**Comprovado**

* A jornada e a progressão alcançam P12 em Nv.20; a falha não é um bloqueio prévio de nível ou ativação.
* Uma execução falhou na preparação porque o resultado variável de equipamento e a troca de Artes do teste não formaram configuração compatível. A rejeição de metadata é explícita em `src/asterion/application/active_arts.py:219–266`; a metadata da arma é de arco, enquanto o loadout B contém Artes melee.
* Na execução que superou a preparação, o roteiro alcançou o combate e perdeu oito lutas/retries sem liquidar P12. O último combate teve HP, ações, dano, política, alvo e consumíveis registrados acima.
* O comportamento normal dos serviços auxiliares da Matriarca — perfil, fases/objetos, telegraph, snapshot, scaling Grupo e settlement — passou nos 8 testes focais (5 unitários + 3 PostgreSQL).

**Não demonstrado**

* Que uma build legal da Sentinela ou qualquer uma das seis Classes seja incapaz de vencer P12.
* Que a Matriarca tenha atributos ou IA fora da Fonte/GDD, ou que exista defeito de dano, cooldown, fase, RNG, persistência ou recompensa.
* Que a derrota se deva a um desequilíbrio numérico. A margem final pequena não demonstra impossibilidade; nenhuma varredura de estratégias ou execução controlada de vitória natural foi feita.
* Que a tentativa final possuía cura fabricada mas deixou de selecioná-la: o estoque/opções visíveis não continha cura. O motivo de disponibilidade não foi preservado na evidência retida.

**Hipóteses a testar, sem tratá-las como fatos**

* O plano automatizado cobre poucas políticas e pode encerrar antes de explorar combinações legais de cura, defesa, uso de Artes e alocação das Conexões.
* O helper escolhe equipamento por vetor de estatísticas sem coordenar a compatibilidade de arma com as Artes pretendidas, deixando uma lacuna entre otimização de equipamento e configuração de combate no harness.
* O craft/restock pode estar limitado pelos materiais e profissões realmente adquiridos no percurso; o diagnóstico não retém os motivos de todas as receitas indisponíveis para confirmar isso.
* Variações de drops/equipamento durante o percurso podem alterar a configuração de uma execução fresca. A causa específica da diferença entre a falha de preparação e a execução que chegou ao chefe não foi isolada por seed ou replay fixado.

## 4. Correções isoladas e testes recomendados

### Correção A — primeiro

Alterar apenas a expectativa de data do contrato de teste, mantendo as demais verificações. Rodar o teste isolado e o módulo inteiro. Em seguida, a suíte global completa, sem exclusões, deve confirmar a resolução do falso negativo documental.

### Diagnóstico/correção B — segundo

Não alterar a Matriarca nem recompensas antes de um replay informativo. Melhorar o diagnóstico do teste para persistir em falha o snapshot integral de preparo (incluindo razões de craft indisponível e opções reais de consumíveis por luta), rota de equipamento/metadata, todas as ações e efeitos, RNG/seed quando o motor oferecer controle suportado e HP a cada fase. Tornar a preparação do teste compatível: o loadout de Artes deve ser selecionado junto com arma legal compatível; a troca deve continuar usando os serviços públicos e não contornar `ActiveArtService`.

Depois, executar contra PostgreSQL 16 uma vitória natural de P12 por serviço público, sem alterar snapshot, HP, XP, equipamento ou drops por fixture. Avaliar e comparar ao menos: política focada no chefe; política que limpa Conexões; uso de cura que o personagem fabricou legitimamente; Artes ofensivas/defensivas compatíveis com o armamento. Registrar todas as builds/decisões testadas e manter progressão econômica legal. Se houver vitória, atualizar o roteiro para reproduzir essa estratégia sem hardcode de estado. Se todas as estratégias legais examinadas falharem, só então abrir análise de balanceamento com replay quantitativo; não mudar a baseline neste diagnóstico.

**Critério objetivo de encerramento de B:** teste de ponta a ponta TDO→P12 ganha naturalmente com setup de equipamento/Artes compatível e recursos obtidos no próprio percurso; ou uma investigação ampliada documenta uma falha de produto reproduzível e delimita a regra/serviço responsável. Incluir uma vitória preparada por mutação do snapshot não satisfaz esse critério.

## 5. Efeito sobre a auditoria global

A suíte global anterior registrada em `docs/audits/ASTERION_AUDITORIA_GLOBAL_LANCAMENTO_FASE4A.md` foi `1.628 passed, 2 failed, 0 errors, 0 skipped`. Esta execução não repetiu a bateria de 1.630, conforme autorizado pelo escopo diagnóstico.

* A falha A é uma asserção de teste obsoleta e não indica conteúdo Várzeas inválido.
* A falha B permanece um bloqueio de validação da jornada Solo inicial. Não é correto marcá-la como defeito confirmado de produto ou considerá-la resolvida pelos testes de settlement/scaling.
* Após a correção isolada de A e o diagnóstico adicional de B, deve-se executar a suíte global completa para atualizar o sinal real de regressão.

## 6. Evidência operacional e escopo

| Execução | Resultado |
|---|---|
| Teste de autoridade isolado | 1 failed — expectativa de data em `:65`. |
| Módulo de contrato Várzeas | 3 passed, 1 failed — única falha a data obsoleta. |
| Percurso TDO→P12, primeira execução válida sem `-s` | 1 failed antes da luta, incompatibilidade durante troca de Artes. |
| Percurso TDO→P12, reprodução subsequente | 1 failed após 793,28 s, assert final; oitava tentativa perdeu com Matriarca em 893/2.548 HP. |
| Combate unitário da Matriarca | 5 passed. |
| Integração PostgreSQL P12/Bestiário | 3 passed em 15,89 s. |
| Suíte completa de 1.630 | Não executada nesta tarefa; a execução anterior continua sendo a referência. |
| Produção/testes/migrations/balanceamento | Sem alterações. |

O banco PostgreSQL 16.15 temporário foi removido. Nenhuma correção foi aplicada. O único arquivo novo desta tarefa é este relatório.

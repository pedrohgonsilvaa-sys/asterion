# Registro de decisões do autor

Este arquivo é o **diário de decisões** do projeto. Cada decisão tem data, texto e o que ela muda. Regras de uso:

- Só se **acrescenta**. Decisão antiga não é apagada nem reescrita. Se uma decisão nova mudar uma antiga, a nova diz qual substitui e a antiga ganha a marca "substituída por".
- Este arquivo **registra**, não promove. Quem escolhe a versão válida de cada documento continua sendo o `SOURCE_AUTHORITY.md`.
- Número, regra ou conteúdo que o autor ainda não aprovou **não entra aqui**. O que falta decidir fica em "Pendências abertas".

## Decisões anteriores que continuam valendo

Resumo de decisões já registradas em outros arquivos. O texto completo continua nos arquivos de origem, que não foram alterados.

| Data | Decisão | Onde está o texto |
|---|---|---|
| 2026-11-11 | Bíblia Canônica v4.0.7 rege Lore, identidades, NPCs e limites (substitui a v3.0 e, por sucessão, a v3.2 e a v3.3). | `SOURCE_AUTHORITY.md` |
| 2026-11-12 | Coop de Missão é exclusivo de Chefes; objetivos comuns, Elites e encontros roteirizados são Solo. Sobrescreve o GDD v1.6.0 §51.3/§55.1. | `SOURCE_AUTHORITY.md`, seção "Camada narrativa" |
| 2026-11-12 | Sistema de Ação × Consequência v1.0.0 rege as 72 Missões; `rapport_state` fica `neutral` até o autor definir as transições; textos de reação seguem a v1.0.1, subordinados ao contrato. | `SOURCE_AUTHORITY.md`, seção "Camada narrativa" |
| 2026-11-12 | TDO v1.0.17 adotada (resolve a divergência com a v1.0.16). | `PLANO_DE_ACAO.md`, Trilha C |
| 2026-11-12 | Balanceamento dos kits da Crônica (C6) fechado sem mudar valores; ajuste fino de TTK fica para a telemetria do Beta. | `HANDOFF.md` §8 item 4 |
| 2026-11-13 | GDD Estrutural v1.7.0 e Contrato de Weapon Metadata v1.1.0 viram a fonte vigente (depois, v1.7.1 e v1.1.1 conforme o índice). | `SOURCE_AUTHORITY.md` |
| 2026-11-13 | Contratos Regionais: lacunas de design e balanceamento fechadas na v1.0.0 (existe no código; a flag segue desligada). | `SOURCE_AUTHORITY.md`, `docs/specs/ASTERION_CONTRATOS_REGIONAIS_DECISOES_FECHADAS_v1_0_0.md` |
| 2026-11-13 | Fase 2E: 3 pendências de Game Design aprovadas, mas o pacote v1.9.x segue **candidato e não canônico**; importação, migration, flag, merge e deploy continuam NO-GO. | `docs/FASE2E_DECISOES_GD_2026-11-13.md` |
| 2026-11-13 | Proficiências de arma: arma inicial Comum, Treinador no Refúgio do Ocaso, Maça como Arma do Contrapeso. | `SOURCE_AUTHORITY.md`, seção "Proficiências de Armas" |
| 2026-11-14 | Armaduras regionais ficam só como nome (sem `armor_class` nem efeito) até o autor aprovar efeitos, Treinador e tabela de templates antigos. | `HANDOFF.md` §9 item 8 |
| Antes de 2026-11-11 | Monetização (§35): Patrono R$ 14,90 e Passe R$ 24,90; entra por último. | `HANDOFF.md` §9 item 6, `PLANO_DE_ACAO.md` |

---

## 2026-11-14 — Bloco 1 do Beta

O autor fechou as decisões abaixo para o Beta. Nenhuma delas altera código por si só; o trabalho de cada uma está planejado em etapas e depende de autorização (ver "Próximos passos").

### D-BETA-01 — Gênero e catálogo de assets

- Gênero **entra no Beta**.
- O modelo de gênero do Beta é **masculino/feminino**. Isso descreve a versão Beta e **não impede** uma expansão futura por nova migration.
- A migration `0051`, o `asset_catalog.py` e o `tests/test_asset_catalog.py` devem entrar **juntos no mesmo PR**.
- Critérios de validação do QA antes do merge:
  1. `alembic upgrade head` → `downgrade` → `upgrade` sem erro;
  2. `alembic check` limpo;
  3. testes passando (banco de teste ligado, pois teste pulado não conta);
  4. Ruff limpo;
  5. personagem antigo com `gender = NULL` continua funcionando.
- A **procedência e a licença dos assets** devem ser verificadas pelo QA antes do merge.

### D-BETA-02 — Prólogo e Contratos

- **Documento A (Prólogo): APROVADO COM AJUSTES** (`docs/specs/ASTERION_DECISOES_PROLOGO_E_CONTRATOS_v1_0_0.md`, parte A do arquivo; a parte B é o Documento B). Definição oficial, dada pelo autor em 2026-11-14:
  - **2 escolhas** no Prólogo, com **3 opções** cada.
  - **6 reações** de Alda/Oren (os 6 ganchos do documento: cada escolha tem uma reação em P1, S1 e S5).
  - O `choice_id` de cada escolha deve ser compatível com o contrato oficial da spec Ação × Consequência.
  - Cada escolha deve ter `future_hook`.
  - O Prólogo **não concede XP nem Coroas e não inicia combate**.
  - `rapport_state` permanece `neutral` no Beta.
  - Os textos finais continuam **sujeitos à aprovação do autor**.
  - Regra já escrita no contrato: nenhuma camada nova cria memória sem registrar o `choice_id` ou `future_hook` nele. Integração ao contrato: Etapa 3 do plano, ainda não feita.
- **Documento B (Contratos Regionais): fica para depois do Beta.**

### D-BETA-03 — Beta fechado e "Dia 1"

- Data-alvo do Beta fechado: **05/12/2026**. É um **alvo de desenvolvimento**, não uma promessa pública.
- "Dia 1 do lançamento" significa o **lançamento público**, e não o início do Beta fechado.
- O Beta pode funcionar **sem iniciar a temporada competitiva da Crônica**.

### D-BETA-04 — Telemetria de TTK

- Criar telemetria mínima de TTK (tempo para derrotar, *time to kill*) **antes** do Beta.
- Registrar, no mínimo: duração do combate, quantidade de ações, criatura, região, dificuldade e resultado.
- Objetivo: permitir ajuste de balanceamento depois, com dados reais do Beta (cumpre o "ajuste fino de TTK fica para a telemetria do Beta" da decisão C6).

### D-BETA-05 — Conteúdo dos catálogos

- O Beta cobre as **6 regiões**.
- Conteúdo **mínimo**: 6 Eventos (1 por região), 4 Provações, 4 Rotas.
- **Eventos**: o autor quer **criar criaturas novas** quando isso melhorar o conteúdo. Não se limita a criaturas existentes.
  - Narrative Designer: identidade e lore das criaturas novas.
  - Game Designer: perfil e ações.
  - Systems Designer: valida regras e balanceamento.
  - Autor: aprova o conteúdo narrativo/conceitual.
  - QA: valida a implementação.
- **Provações e Rotas**: sempre que possível, reaproveitam criaturas existentes, para reduzir escopo.

### D-BETA-06 — Smoke test

- Smoke test **interno**, no **bot de staging**.
- O autor participa da execução do fluxo principal.
- O QA prepara e acompanha o checklist.
- **Não abrir teste externo** antes da validação interna.

### D-BETA-07 — Lore e textos

- **Auditoria completa da Crônica contra a Bíblia v4.0.7** antes do Beta fechado.
- Ordem: o Narrative Designer audita primeiro. Cada achado traz **arquivo, linha, trecho, regra da Bíblia, problema e correção**.
- O autor faz a aprovação final dos textos canônicos e do tom. O Programmer aplica as correções. O QA valida.
- O `flavor_catalog.py` entra nessa revisão.
- A proposta **v0.2 da Crônica NÃO** é promovida agora ao `SOURCE_AUTHORITY.md`. Só se promove uma versão **revisada e aprovada**.

### Pendências abertas (nada disto foi inventado; precisa do autor)

1. ~~Ajustes do Documento A.~~ Resolvido em 2026-11-14: a definição oficial está em D-BETA-02. Falta só conferir, na Etapa 3, que o texto do documento bate com ela (por exemplo, os `choice_id` hoje são `PRO_choice_aftermath` e `PRO_choice_first_fire`; o contrato e o catálogo ainda não os conhecem).
2. **Criaturas novas dos Eventos.** Nomes, perfil, ações e números não existem ainda. Nada será inventado: seguem o fluxo da D-BETA-05.
3. **Staging (busca feita em 2026-11-14).** Procurei no código, docs, CI (`.github/workflows`), `docker-compose*.yml`, `Caddyfile`, `.env.example`, `scripts/` e no histórico do Git. **Não existe bot nem ambiente de staging definido.** A única menção é a auditoria `GLOBAL-AUD-028` (docs/audits), que recomenda criar um bot de teste separado e diz que não havia staging. Nada foi criado nem alterado. O autor precisa dizer se o bot de staging existe fora do repositório ou se será criado depois; isso bloqueia o smoke test (D-BETA-06).
4. **Data do Dia 1.** A data do Dia 1 da Crônica continua configurável e **indefinida**. A D-BETA-03 só fixa o significado da expressão.

### Divergências encontradas entre estas decisões e o estado do repositório

Registradas em 2026-11-14. As de `HANDOFF.md`, `PLANO_DE_ACAO.md` e `BRIEFING_CONTEUDO.md` foram corrigidas na Etapa 1; as demais seguem abertas.

- **Gênero já está na `main`.** A migration `20261113_0051_character_gender.py` (commit `ee11812`) e o `src/asterion/bot/asset_catalog.py` (commit `cad7167`) já estão em `origin/main`, e as migrations `0052` e `0053` já foram empilhadas sobre a `0051`. Já a decisão pede os três arquivos "juntos no mesmo PR". Por isso, a decisão vira **gate de validação do QA sobre o que já está na `main`** (e correção por novo PR se algo falhar), e não um PR novo de implementação. O `HANDOFF.md` §9 item 7 ainda diz que gênero e imagens estão "em andamento"; está desatualizado.
- **Catálogos já têm mais que o mínimo.** O `HANDOFF.md` §9 item 4 diz que o catálogo já tem 5 Rotas, 11 Provações e 6 Eventos Públicos. O mínimo do Beta (6/4/4) já é atingido em quantidade; o que muda é a decisão de **criar criaturas novas para os Eventos** e a validação do QA. Falta confirmar no código quais criaturas os 6 Eventos usam hoje.
- **"Dia 1".** O `PLANO_DE_ACAO.md` e o `BRIEFING_CONTEUDO.md` falam do Dia 1 da Crônica como "depois de algumas semanas do Beta". Isso é compatível com a D-BETA-03, mas os textos precisam usar a mesma palavra ("lançamento público").

### Próximos passos

Etapa 1 (só documentação) autorizada e feita em 2026-11-14: `DECISIONS.md`, `HANDOFF.md` (§9 itens 4 e 7), `docs/PLANO_DE_ACAO.md` e `docs/BRIEFING_CONTEUDO.md`. As Etapas 2 a 7 aguardam autorização. Nenhum código, migration ou teste foi alterado.

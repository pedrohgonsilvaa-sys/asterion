# ASTERION — Auditoria Global de Completude para Lançamento (Fase 4A)

Data da auditoria: 2026-10-19
Checkout auditado: C:\dev\asterion
Branch: main
HEAD auditado: 41cdaae3e94313b7ef3c779017cb85ebaaab863d
HEAD inicial esperado: 41cdaae3e94313b7ef3c779017cb85ebaaab863d
Escopo: diagnóstico; nenhum código, teste, balanceamento, migration ou fonte oficial foi alterado.

## A. Resumo executivo

O checkout local está no HEAD esperado e contém a entrega regional mais recente da Câmara das Contradições. A branch main local está 54 commits à frente da referência local origin/main (d76b4204028827d4c4ac849152980d77f5d794a9). A referência remota não foi buscada nem usada para substituir o checkout.

Há conteúdo implementado substancial para as seis regiões: o catálogo de código e os testes cobrem P1–P36, S1–S36 e as 12 Masmorras. Há serviços, persistência e handlers para campanha, combate PvE, Caçada, Ronda, Desbravar, equipamento e as atividades regionais. Isso não equivale a prontidão do lançamento: sistemas expressamente incluídos na seção 48 do GDD continuam sem implementação comprovada, inclusive execução do Legado I–V, Crônica, eventos públicos, Guildas, Mercado, Troca Direta, Arena/Duelo, Trilha/Passe e pagamentos.

Resultado de produto: NAO_PRONTO para o escopo público integral da seção 48. O código oferece uma jornada PvE regionalmente extensa, mas faltam sistemas sociais, competitivos, recorrentes e pós-campanha fundamentais; há também lacunas operacionais (backup/restore, entrega durável, telemetria, deploy/drain) e a jornada orgânica completa até o Legado não está comprovada por um teste de ponta a ponta.

A suíte completa foi executada e terminou com 1.628 passed e 2 failed, sem errors ou skips. Uma falha é uma asserção documental desatualizada; a outra é a jornada integrada Solo TDO→Vales que não concluiu a Matriarca de P12 no plano de oito tentativas. Essa segunda falha impede declarar a progressão inicial Solo validada e requer diagnóstico, mas não prova que todas as estratégias/builds Sentinel sejam inviáveis.

Contagens da matriz GDD §48:

* IMPLEMENTADO_E_VALIDADO: 10 sistemas.
* IMPLEMENTADO_SEM_VALIDACAO_SUFICIENTE: 1 sistema.
* PARCIAL: 14 sistemas.
* AUSENTE: 16 sistemas.
* BLOQUEADO: 0 sistemas classificados na matriz. Duas fontes obrigatórias ausentes criam bloqueio de autoridade transversal descrito abaixo.
* NAO_APLICAVEL: 0 sistemas.

Não foi confirmado achado P0 nesta execução. Os P1 são itens obrigatórios ausentes/parciais que impedem afirmar prontidão do escopo completo; P0 deve permanecer reservado para corrupção/exploração crítica comprovada.

### Fontes e limites de autoridade

| Autoridade consultada | Estado observado |
|---|---|
| GDD Estrutural v1.6.0 | Presente; hash recalculado: 0C9245861DA2AF8ED13944607F47B9122165D38E5A919F8B3DBAA668B65550AA. §§48–49 e regras sistêmicas consultadas. |
| SOURCE_AUTHORITY.md e docs/SOURCE_AUTHORITY.md | Presentes e byte a byte idênticos; SHA-256 D50FB7B618D9D80540536AAB8102A491D40CE6B9FA0E077006656F93AB73FD8B. |
| Contrato Global Weapon Metadata v1.0.0 FINAL | Presente; hash C283B398949DC0A864D98B9E0E9031080A50B937DB6932FFCDE7D46E600AA740; índice o declara vigente. |
| Fontes Regionais FINAL 1–6 | Presentes e selecionadas pelos índices: TDO v1.0.16, Vales v1.0.6, Nareth v1.0.2, Várzeas v1.0.3, Altos v1.0.1, Confins v1.0.0. Hashes: 8FDBE5E61216D0A2B9B62B60E5666361584055B266AFBF2238437ABC59B4954B; D88A247DCF1D384EBC3385FAA77C80F25B0CEF114CCC6E71191B112117159247; 758ADD317D856F6890284C4A7FD09457716B3F21F8094B2619C21245BA7E8470; D3772463786DAFF9F7748DFF9A1BBF2761C3BF0F4F96848B460E16131CD70628; E3EE5A1DBBE81B51CD63464CDC043629AFFF705A0167CD60FEEE9ABE80D54D6F; C86A0208888D14BBD653CDA6174956DF89B2233304DCCA523D878B5B42A102FC. |
| Bíblia Canônica Mundo/Regiões/Bestiário/NPCs v3.0 FINAL | SOURCE_AUTHORITY a declara superior, mas o arquivo exato não existe no checkout. Existe ASTERION_LORE_BIBLE_CANON_v1.2.md, classificada pelo índice como complementar; ela não foi usada como substituta. Validação canônica completa fica bloqueada. |
| Fonte Visual de Skins v1.2.0 FINAL solicitada | O arquivo exato não existe no checkout. O índice seleciona outra autoridade: Consolidação Visual/UI v1.6.0 sincronizada em 2026-10-13 e fontes complementares de skins em versões distintas. Não foram tratadas como substitutas do documento pedido. |
| Fonte Visual/UI selecionada por SOURCE_AUTHORITY | Presente: ASTERION_UI_DECISOES_2026-10-13_FINAL_SYNC_v1.6.0_TDO_v1.0.15_VALES_v1.0.6.md; hash recalculado C4D6B5807AF6E3BFFF646287D19E416715A9B51D098774267F0073AF760815AC. |

### Integridade do checkout

HEAD inicial e final da auditoria: 41cdaae3e94313b7ef3c779017cb85ebaaab863d. A verificação tracked/staged mostrou árvore limpa antes de iniciar o relatório. O checkout contém a proposta regional e .worktrees como entradas untracked preexistentes; não foram lidos, alterados ou adicionados. Um comando inicial de status do Git retornou “could not open directory .pytest_tmp/ Permission denied”; não foi lido nem alterado conteúdo dessa pasta. As verificações subsequentes limitaram-se a arquivos tracked. Nenhuma operação de rede Git foi executada.

## B. Matriz integral do escopo do GDD §48

Cada coluna de camada descreve separadamente domínio/aplicação, persistência, interface Telegram e testes. “Validado” abaixo significa coberto por evidência local e pela suíte executada nesta auditoria, não certificação de produção. Itens sem evidência suficiente não foram promovidos a completos.

| Sistema do lançamento | Status Domínio | Status Persistência | Status UI | Status Testes | Situação Final | Achados |
|---|---|---|---|---|---|---|
| Campanha 1–60, P1–P36 | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | INSUFICIENTE para uma jornada orgânica P1→P36→Legado | IMPLEMENTADO_SEM_VALIDACAO_SUFICIENTE | 001, 002 |
| 36 missões secundárias S1–S36 | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | COBERTO por testes regionais e de integração; limites narrativos dependem da Bíblia ausente | IMPLEMENTADO_E_VALIDADO | 001 |
| 12 Masmorras | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | COBERTO por testes focais, multiplayer, run, recovery e economia; lançamento integral ainda precisa da suíte completa abaixo | IMPLEMENTADO_E_VALIDADO | 001 |
| Seis Classes, 12 Caminhos, Artes, Talentos e Doutrinas | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | Testes de classe/provação, caminhos, passivas, talentos e Artes | IMPLEMENTADO_E_VALIDADO | 027 |
| Combate PvE, Chefes e scaling Solo/Grupo | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | Motores e testes de combate, chefes, grupos e Masmorras | IMPLEMENTADO_E_VALIDADO | 027 |
| PvP | PARCIAL: há PvPvE de Caçada, não subsistemas PvP completos | PARCIAL | PARCIAL | Testes de PvPvE/Ronda; sem Duel/Arena | PARCIAL | 012, 013 |
| Caçada, Ronda, Desbravar, Vigor e Braseiros | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | Testes de domínio, integração, multiplayer, persistência e UI | IMPLEMENTADO_E_VALIDADO | 002 |
| Eventos públicos e Sintonização do Véu | AUSENTE como motor/configuração de lançamento | AUSENTE | AUSENTE | Nenhum teste de fluxo de Evento | AUSENTE | 004 |
| Equipamentos, slots e Weapon Metadata | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | Registry canônico exato, inventário, equipamento, escolha e integração | IMPLEMENTADO_E_VALIDADO | — |
| Runas, Encantamentos, Crafting e Desmontagem | IMPLEMENTADO para uso pessoal | IMPLEMENTADO | IMPLEMENTADO | Testes de Crafting, inventário, runas, receita e modificações | IMPLEMENTADO_E_VALIDADO | — |
| Ofícios e Serviços entre jogadores | PARCIAL: profissão/Crafting pessoal existe; oferta e execução de serviço para terceiros não comprovadas | PARCIAL | PARCIAL | Cobertura pessoal/regional; sem fluxo econômico entre prestador e cliente | PARCIAL | 009 |
| Mercado, Loja Pessoal, Código Único e divulgação comunitária | AUSENTE | AUSENTE | AUSENTE | Sem serviço, tabelas, handlers ou testes de marketplace | AUSENTE | 007 |
| Troca Direta de itens | AUSENTE | AUSENTE | AUSENTE | Sem proposta, reserva, confirmação ou settlement de troca | AUSENTE | 008 |
| Guildas, convites, procura, recrutamento e inscrições | AUSENTE | AUSENTE | AUSENTE | Sem domínio/persistência/rotas de guilda; Group Social não é Guilda | AUSENTE | 010 |
| Juramento de Guilda | AUSENTE | AUSENTE | AUSENTE | Sem atividade ou settlement de Juramento | AUSENTE | 011 |
| Expedição de Guilda | AUSENTE | AUSENTE | AUSENTE | Sem preparação, run ou recompensa de Expedição | AUSENTE | 011 |
| Batalha de Guildas | AUSENTE | AUSENTE | AUSENTE | Sem pareamento, roster, combate, rating ou histórico GvG | AUSENTE | 011 |
| Duelo | AUSENTE | AUSENTE | AUSENTE | Sem desafio PvP persistente ou testes | AUSENTE | 012 |
| Arena da Vigília, MMR, Elos e temporadas | AUSENTE | AUSENTE | AUSENTE | Sem filas, rating, placement, decay ou testes de Arena | AUSENTE | 013 |
| Doutrinas | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | Catálogo, serviço, router e testes | IMPLEMENTADO_E_VALIDADO | — |
| Legado I–V e Marcas | AUSENTE como execução jogável | AUSENTE | AUSENTE | P36 só concede elegibilidade; nenhum ciclo de ascensão testado | AUSENTE | 003 |
| Bestiário, Códice e Feitos | IMPLEMENTADO | IMPLEMENTADO | IMPLEMENTADO | Marcos, entradas, procedência e grants cobertos por testes | IMPLEMENTADO_E_VALIDADO | 001 |
| Cosméticos: Aparência, Título, Moldura e seleção | PARCIAL: catálogo/entitlements de recompensas existem; assets e ciclo comercial/temporário não comprovados | PARCIAL | PARCIAL | Testes de cosméticos e Feitos; não validam ativos visuais integrados | PARCIAL | 014, 026 |
| Perfil, História e Relatos | PARCIAL: superfície de perfil/história implementada; Relatos públicos/moderação/privacidade não comprovados | PARCIAL | PARCIAL | Testes character_surfaces; escopo social completo não coberto | PARCIAL | 017 |
| Vínculos: Amigos, convites, bloqueios, recentes e privacidade | PARCIAL: grupos/convites e tela “Vínculos” existem, mas grafo de amigos e políticas não estão demonstrados | PARCIAL | PARCIAL | Testes de Grupo não validam amigos/bloqueio/visibilidade | PARCIAL | 016 |
| Crônica I e Nova Vigília | AUSENTE | AUSENTE | AUSENTE | Sem motor de capítulo/votação/ciclo | AUSENTE | 005 |
| Trilha/Passe da Crônica, 40 Marcos e resgates | AUSENTE | AUSENTE | AUSENTE | Sem progressão, entitlements ou testes | AUSENTE | 006 |
| Patrono de Asterion, pagamentos e entitlements temporários | AUSENTE | AUSENTE | AUSENTE | Sem integração de compra/webhook/reconciliação; provedor externo também não configurado | AUSENTE | 014 |
| Dádiva Diária, Chamado, Comunidade e Códigos | AUSENTE | AUSENTE | AUSENTE | Sem claims/referências/códigos; sem testes | AUSENTE | 015 |
| Flavor Text Contextual versionado | PARCIAL: há texto contextual embutido em regiões/combate; não há catálogo/seleção geral versionada comprovada | PARCIAL | PARCIAL | Sem contrato geral e cobertura completa | PARCIAL | 024 |
| UX Telegram transversal e navegação do §48 | PARCIAL: fluxos centrais existentes; sistemas ausentes não possuem telas; estados vazios, stale callbacks e erros não foram auditados exaustivamente em produção | IMPLEMENTADO para features presentes | PARCIAL | Testes de UI/handlers por feature; não há E2E real do bot publicado | PARCIAL | 025 |
| Persistência transacional, idempotência e foreground para fluxos existentes | IMPLEMENTADO | IMPLEMENTADO | PARCIAL em sincronização transversal | Testes concorrentes/idempotência e PostgreSQL existentes; não cobre sistemas ainda ausentes | IMPLEMENTADO_E_VALIDADO | — |
| Sincronização multidispositivo | PARCIAL: snapshots e bloqueios por atividade existem; sincronização consistente de sessões/menus simultâneos não comprovada ponta a ponta | PARCIAL | PARCIAL | Testes de lock/versionamento local; sem matriz de dispositivos concorrentes | PARCIAL | 018 |
| Transactional Outbox e entrega durável | PARCIAL: tabela OutboxMessage/dedup existe; worker/claim/retry/observabilidade não foram encontrados | PARCIAL | PARCIAL | Sem teste de worker ou entrega após restart | PARCIAL | 018 |
| Scheduler durável e distribuído | PARCIAL: APScheduler em processo para Ronda; não é scheduler persistente/distribuído de ciclos | PARCIAL | NÃO APLICÁVEL isoladamente | Sem recuperação de jobs/ciclos após restart e execução multi-instância | PARCIAL | 018 |
| Administração, moderação, sanções e auditoria administrativa/financeira | PARCIAL/insuficiente: não foi encontrado painel/serviço administrativo abrangente; endpoints de saúde não são administração | PARCIAL | AUSENTE como console/admin UI | Sem testes de autorização/auditoria administrativa | PARCIAL | 019 |
| Segurança, autorização, rate limiting e antiexploit | PARCIAL: identidade Telegram, webhook secret, locks/uniques e validações locais; não há rate limiter e ferramentas abrangentes de anti-RMT/boosting/multiaccount | PARCIAL | PARCIAL | Testes de alguns ataques de callback/concorrência; sem teste de carga/abuso integral | PARCIAL | 020 |
| Telemetria, logs estruturados, métricas e alertas | PARCIAL/insuficiente: health/ready e logging básico; pipeline de métricas, dashboards e alertas não demonstrado | PARCIAL | NÃO APLICÁVEL | Sem verificação operacional de alertas | PARCIAL | 021 |
| Deploy, manutenção, drain e lifecycle de migrations/patches | PARCIAL: Docker Compose dev e CI existem; configuração de produção, rollout/drain e rollback documentados/testados não foram encontrados | PARCIAL | NÃO APLICÁVEL | CI não valida deploy/restore real | PARCIAL | 022 |
| Backups, restauração e reconciliação | AUSENTE como procedimento testado | AUSENTE/sem evidência de backup automatizado | AUSENTE | Nenhum teste de restore/reconciliação encontrado | AUSENTE | 023 |
| Assets oficiais e integração visual/skins | AUSENTE no checkout de assets rastreados: 0 imagens raster/vetor rastreadas; creation_images é configuração externa vazia por padrão | NÃO APLICÁVEL ao arquivo, mas entitlements de cosmético são parciais | PARCIAL com fallback/texto, sem pacote visual | Sem teste de inventário/integração de assets; fonte de skins solicitada não está presente | AUSENTE | 001, 026 |

## C. Auditoria regional

Os contadores abaixo são sustentados pelos módulos regionais, registros de conteúdo e testes de missão/masmorra. Eles significam “implementado no checkout”, não validação editorial completa: a Bíblia Canônica v3.0 referenciada pelo índice não foi fornecida no repositório. Os testes longos integrados variam por região e não substituem uma jornada natural contínua atravessando todas as regiões.

| Região | Código de campanha | Secundárias | Masmorras | Evidência representativa | Situação |
|---|---:|---:|---:|---|---|
| Terras do Ocaso, Nv.1–10 | P1–P6 | S1–S6 | 2 | application/p1.py–p6.py, s1.py–s6.py, domain/tdo_crypt.py, domain/tdo_galleries.py; testes test_p1*, test_s*, test_tdo_* e test_tdo_full_playthrough.py | Implementado; percurso global completo não demonstrado |
| Vales dos Enforcados, Nv.11–20 | P7–P12 | S7–S12 | 2 | application/vde_missions.py; domain/vde_fosso.py, vde_santuario.py; test_vde_* e test_vde_full_playthrough.py | Implementado; percurso integrado completo não demonstrado |
| Planícies de Nareth, Nv.21–30 | P13–P18 | S13–S18 | 2 | application/nareth_missions.py; domain/nareth_dungeons.py, nareth_bosses.py; test_nareth_* | Implementado; jornada Solo/Grupo de ponta a ponta insuficiente |
| Várzeas Carmesins, Nv.31–40 | P19–P24 | S19–S24 | 2 | application/varzeas_missions.py; domain/varzeas_dungeons.py, varzeas_bosses.py; test_varzeas_* | Implementado; jornada Solo/Grupo de ponta a ponta insuficiente |
| Altos Cinéreos, Nv.41–50 | P25–P30 | S25–S30 | 2 | application/altos_missions.py, application/s25.py–s30.py; domain/altos_pedreira_dungeon.py, altos_bastilha_dungeon.py; test_altos_* | Implementado; cobertura focada extensa |
| Confins do Véu, Nv.51–60 | P31–P36 | S31–S36 | 2 | application/altos_missions.py e application/s31.py–s36.py; domain/confins_regent.py, confins_arquivo_dungeon.py, confins_contradictions_dungeon.py; test_confins_* | Implementado; validação depende também das fontes canônicas ausentes |
| **Total** | **36** | **36** | **12** | Inventário de módulos e testes do checkout | **O inventário de conteúdo está presente; não prova operação pública integral** |

### Cobertura transversal por região

* Missões, gates, combates roteirizados, recompensas, Códice, Bestiário, Feitos, atividades locais e as duas Masmorras são representados em módulos e testes focais.
* Estradas/Travel, grupo, configuração de combate, economia e persistência usam serviços compartilhados, não um motor por região.
* O runtime registra os routers regionais e os routers compartilhados; ver src/asterion/bot/runtime.py, criação dos serviços e include_router para P/S, dungeon, combat e world.
* Nenhuma das seis regiões tem implementação de Guilda, Mercado, Arena, Crônica ou Legado — esses são sistemas globais, não defeitos regionais isolados.
* Ativos visuais regionais não estão no conjunto de arquivos de imagem rastreados. Algumas configurações permitem Telegram file_id/path externo, porém isso não é inventário versionado nem prova de distribuição.
* A contagem de 12 Masmorras corresponde às duas por região definidas no escopo; a presença dos seis módulos de conteúdo e seus testes foi verificada, sem executar uma run manual de produção.

## D. Auditoria por sistema do lançamento

Cada item corresponde a uma linha da matriz B. A evidência distingue serviço/domain, persistência, router e testes; ausência significa que a pesquisa cruzada de aplicação, modelos, runtime e testes não encontrou implementação de fluxo, não apenas ausência de um módulo com determinado nome.

### D.01 Campanha principal

P1–P36 e gates regionais estão presentes nas aplicações regionais e integrados ao runtime. P36 persiste unlock.campaign.first_journey_complete e legacy_eligible em application/altos_missions.py, mas a busca por um serviço, estado, handler ou operação de ascensão não encontrou execução de Legado. Testes test_confins_p36.py/test_confins_s36.py verificam elegibilidade e conclusão; isso não demonstra campanha natural completa nem Legado.

### D.02 Secundárias

S1–S36 estão em serviços dedicados ou regionais, com aceite, progresso, abandono/reaceite, persistência, UI e testes focais. O runtime registra routers S31–S36 e as famílias anteriores. A limitação é de autoridade de lore ausente, não evidência de conteúdo regional ausente no código.

### D.03 Masmorras

Há motor comum em application/dungeons.py e domain/dungeons.py, modelos de lobby/run/encontro, handlers em dungeon_handlers.py e UI compartilhada. Doze configurações de Masmorra são cobertas por testes próprios, core, multiplayer e Telegram. A conclusão da suíte completa é registrada na seção F; não se infere cobertura de operação produtiva a partir do motor.

### D.04 Personagem, Classes e Caminhos

Account/Character, trials, paths, arts, talents e doctrines têm serviços, modelos e routers. Testes incluem classes/provações, combinações raciais, passivas, Artes e Talentos. Não foi localizado um percurso integrado e balanceado das seis Classes atravessando a campanha completa, nem execução real de Legado.

### D.05 Combate PvE

Combat e PvPvE são motores distintos. Há motor de combate e regras de configuração/snapshot, encontros roteirizados, Chefes de campanha e de Masmorra, objetos físicos e testes de combate, preparação, grupos e dungeons. A camada PvP do GDD não é satisfeita por PvPvE.

### D.06 PvP

application/pvpve.py trata resolução de confrontos simultâneos de Caçada e integração com Ronda. tests/test_pvpve_* e test_round_pvpve_integration.py cobrem esse escopo. Não foram encontrados desafios de Duelo, fila/classificação de Arena, MMR, Elos ou temporadas; ver achados 012–013.

### D.07 Caçada, Ronda, Desbravar, Vigor e Braseiros

application/hunt.py, round.py, explore.py e dungeons.py, modelos correspondentes, handlers e testes regionais/shared implementam esses fluxos para regiões abertas e dungeons. Existem testes de persistência, elegibilidade, settlement e recuperação. A conclusão não substitui prova de progressão legal 1–60 nem todos os ambientes de produção.

### D.08 Eventos Públicos

Não foi encontrado motor configurado de eventos públicos, participação, contribuição, chefe de evento, settlement ou estado de Sintonização. Preferências de notificação com categoria events em account.py/models.py são apenas preferências e não implementação de Evento.

### D.09 Equipamento e Weapon Metadata

equipment.py, equipment_modifications.py e weapon_metadata.py junto a Inventory/Equipment models e routers implementam catálogo, equipar/retirar e contratos canônicos de armas. tests/test_weapon_metadata.py valida registry explícito, inclusive 24 entradas presentes no estado local; testes de equipamento e inventário cobrem o fluxo.

### D.10 Runas, Encantamentos, Crafting e Desmontagem

crafting.py, equipment_modifications.py, professions.py e modelos/routers integram receitas, materiais, fabricação e modificações. Há testes de crafting, runas, inventário, receitas regionais e settlement. Essa validação cobre fabricação pessoal; não prova Serviços de profissionais entre jogadores.

### D.11 Ofícios e Serviços

Profissões e crafting pessoal são implementados. Não foi encontrado fluxo completo para publicar um serviço a terceiros, ligar oferta a Loja Pessoal, reservar taxa/materiais, executar o trabalho, liquidar direitos e recuperar cancelamento. Ver achado 009.

### D.12 Mercado e Loja Pessoal

Não há serviço/modelo/router de anúncio, listing, código único, compra parcial, escrow, payout ao vendedor ou reconciliação. A inexistência foi confirmada em buscas cruzadas de modelos, aplicação, runtime e testes. Ver achado 007.

### D.13 Troca Direta

Não foi encontrado fluxo de oferta, seleção de quantidades, reservas, confirmações por ambas as partes, invalidação de termos alterados ou liquidação atômica. Ver achado 008.

### D.14 Guildas

models.py contém SocialGroup e lobbies/participantes de grupo, e groups.py implementa cooperação. Isso não oferece guilda persistente com TAG/nome, papéis, convites, inscrições, recrutamento, tesouraria, obras ou auditoria. Ver achado 010.

### D.15 Juramento

Não há ciclo cooperativo de Juramento, participação/contribuição ou recompensa de Guilda. É dependente de identidade e estado de Guilda. Ver achado 011.

### D.16 Expedição

Não foram encontrados preparação, seleção/elegibilidade de integrantes, execução ou liquidação da Expedição de Guilda. É dependente de Guilda e da base de atividades em grupo. Ver achado 011.

### D.17 Batalha de Guildas

PvPvE não é GvG. Não há pareamento de Guildas, rosters, configuração congelada de batalha, resolução de empate, rating, histórico ou integração com Crônica. Ver achado 011.

### D.18 Duelo

Sem fluxo de desafio/aceite, combate PvP individual persistido, desistência, Exaustão, proteção antiabuso ou UI. Ver achado 012.

### D.19 Arena da Vigília e Elos

Sem filas, MMR, placements, Renome, Elos, temporada, soft reset, decay ou reentrada. Ver achado 013.

### D.20 Doutrinas

application/doctrines.py, modelo, router e tests/test_bot_base_b2.py (test_doctrines_snapshot_apply_cost_noop_foreground_and_limit) sustentam o sistema publicado. Está integrado à Configuração de Combate sem ser confundido com caminho/profissão.

### D.21 Legado I–V

Só foi encontrado o direito de elegibilidade persistido por P36; não há serviço de ação voluntária em local seguro, ascensão I–V, marcas, multiplicadores ou redistribuição. Ver achado 003.

### D.22 Bestiário, Códice e Feitos

Há serviços/catálogos/models, integração regional, milestones e testes de persistência/idempotência. Testes específicos de Confins e de dungeons existem. O lore canônico superior v3.0 ausente impede a validação final de limites narrativos.

### D.23 Cosméticos

CosmeticService e cosmetic_catalog.py apresentam títulos/molduras/recompensas e UI; as tabelas de entitlement permitem registros. Não há assets rastreados, seleção visual final completa nem integração de entitlement temporário de Patrono. Ver achados 014 e 026.

### D.24 Perfil, História e Relatos

character_surfaces.py e CharacterProfile armazenam superfícies do personagem, incluindo história, com testes Telegram. Não foi comprovada publicação/moderação de Relatos, regras completas de privacidade, moderação e proteção de spoiler. Ver achado 017.

### D.25 Vínculos

Groups e invites são cooperação. A opção de navegação Vínculos aponta para links:root; não se encontrou grafo persistente de amigos, pedidos, bloqueios, jogadores recentes ou políticas de visibilidade. Ver achado 016.

### D.26 Crônica I e Nova Vigília

Não foram encontrados modelos/serviços/handlers/testes para capítulos, cadência de sete dias, votação, voto único, desempate, estado mundial versionado, arquivo histórico ou Nova Vigília. Ver achado 005.

### D.27 Trilha/Passe

Não há sequência de 40 marcos, trilhas Livre/Premium, resgates, entitlement retroativo, janela de compra ou liquidação pós-Crônica. Ver achado 006.

### D.28 Patrono e pagamentos

Não há checkout, webhook de pagamento, IDs de compra, reconciliação, revogação auditável, prazo, renovação ou fallback cosmético de Patrono. Nenhum provedor/credencial foi configurado; nenhuma compra real foi executada. Ver achado 014.

### D.29 Dádiva, Chamado, Comunidade e Códigos

Não foram encontrados claims diários, ciclo, referral validation, limite por conta/servidor, códigos resgatáveis ou auditoria. Ver achado 015.

### D.30 Flavor Text Contextual

Há linhas textuais específicas em conteúdo e UI, porém não foi encontrado catálogo geral versionado com seletores contextuais reutilizáveis e procedência. Ver achado 024.

### D.31 UI Telegram

runtime.py constrói e registra routers para criação, personagem, campanha, atividades regionais, grupos, combate, dungeons, equipamento, profissões, cosméticos e doutrinas. Não registra recursos dos sistemas ausentes. Testes de handlers e callbacks existem por partes; não há teste de operação do bot com Telegram real, nem fluxo unificado de erros/obsolescência para tudo. Ver achado 025.

### D.32 Persistência e idempotência

SQLAlchemy/PostgreSQL, Alembic, constraints, locks, snapshots e deduplication aparecem em modelos/serviços e testes de concorrência. Esta base valida os sistemas presentes. Não estende proteção automaticamente a sistemas ausentes.

### D.33 Multidispositivo

Há estado foreground, versões de estado e snapshots por atividades. Não foi comprovado comportamento consistente entre dois dispositivos com callbacks cruzados, mensagens antigas e simultaneidade de menus/combate para o conjunto completo. Ver achado 018.

### D.34 Outbox

OutboxMessage existe em models.py com chave de deduplicação; docs/ARCHITECTURE.md descreve a tabela como fundamento e deixa o worker para etapa futura. Não foi encontrado worker que reivindica mensagens, reenvia com backoff, marca conclusão ou recupera após restart. Ver achado 018.

### D.35 Scheduler

round_scheduler.py cria AsyncIOScheduler em processo e executa RoundService a cada 15 segundos. Não é scheduler distribuído/durável. O GDD requer scheduler persistente para ciclos e recuperação operacional. Ver achado 018.

### D.36 Administração

Não foi localizada superfície completa de administração, RBAC, moderação, suspensão, inspeção de auditoria financeira ou histórico de ação. Health/ready não são painel administrativo. Ver achado 019.

### D.37 Segurança e antiexploit

Existem autorização baseada em identidade Telegram, segredo do webhook, validação de callbacks/estado em alguns fluxos, constraints e locks. Não foi demonstrada política transversal de rate limiting, anti-RMT, anti-boosting, multiaccount ou abuso social/econômico. Nenhum exploit econômico foi confirmado pela auditoria estática; a falta de controles e testes mantém risco não validado. Ver achado 020.

### D.38 Telemetria

API oferece /health e /ready (PostgreSQL e Redis). Não foram encontrados dashboards, métricas de negócio, alertas de falha/latência, tracing nem SLOs validados. Ver achado 021.

### D.39 Deploy e manutenção

Docker Compose e workflow CI existem, porém os serviços Compose são configurados como development; não foi encontrado pipeline/manifesto de produção, migração com rollout seguro, drain de atividades, rollback/patch ou runbook testado. Ver achado 022.

### D.40 Backup e restore

Não foi encontrado procedimento automatizado de backup, retenção, chaveamento, restauração isolada, teste de integridade ou reconciliação financeira. Ver achado 023.

### D.41 Visuais

SOURCE_AUTHORITY seleciona uma fonte Visual/UI e fontes complementares de skins, porém não há arquivos de imagem rastreados no checkout; creation_images tem default vazio e permite IDs/paths externos. Assim, documentar asset ou fallback não prova entrega visual. A fonte v1.2.0 FINAL pedida também está ausente. Ver achados 001 e 026.

## E. Fluxo real do jogador e integrações críticas

### Criação → P36 → Nv.60 → Legado

Criação, prólogo e campanha regional estão implementados em fluxo sequencial e com gates por nível. Há testes focalizados para regiões, Solo/Grupo e duas jornadas longas opt-in (TDO e Vales). Os testes e serviços permitem fixtures para níveis/gates; não há evidência de um único teste PostgreSQL natural que caminhe todas as etapas desde criação, usando somente recompensas legítimas, até P36, Nv.60 e primeira ascensão. P36 grava o entitlement de conclusão e elegibilidade, mas a execução voluntária de Legado I–V não existe no checkout. Logo, a transição pós-campanha é incompleta e o proprietário não pode validar o loop do primeiro Legado como jogador real.

Não foi feita análise matemática independente de horas reais de progressão nesta execução. GDD §49 permanece autoridade numérica, e alterar XP/recompensas está fora do escopo. A conclusão operacional a provar é uma simulação de jornada legal por atividade, classes e grupo, sem injetar XP ou nível.

### Economia

Economia individual de missões, atividades e dungeons implementa rewards idempotentes, inventário, materiais, receitas, equipamentos, runas/pity e limites. Não há economia entre jogadores: sem Loja/Escrow/Troca/Serviços. A reconciliação econômica operacional e trilha de auditoria financeira abrangente também não foram encontradas.

### Guildas e PvP

Grupos são cooperação de sessão; não são identidade persistente de Guilda. PvPvE de caçadas não implementa Duelo ou Arena. Sem Crônica, temporadas não podem alimentar Elos, GvG e Trilha.

### Crônica e recorrência

Sem capítulos, votação e Nova Vigília, não há ciclo de lançamento recorrente nem estado mundial versionado. Eventos e Sintonização também não estão configurados.

### Telegram

O bot expõe experiência navegável para as funcionalidades existentes. Os recursos ausentes na seção B também não têm handlers reais. O runtime registra polling/webhook configurado, mas o teste local não demonstra identidade, webhook público, operação contínua ou recuperação com Telegram de produção.

### Fontes visuais

Zero assets gráficos foram encontrados em arquivos rastreados. A configuração creation_images é um mapa opcional de identificadores/path e começa vazio. O critério visual deve inventariar entregáveis exigidos pela autoridade efetivamente aprovada e então conferir integração/fallback. A falta da fonte de skins solicitada impede definir o conjunto canônico dessa auditoria sem pedir a fonte.

## F. Testes e validação

### Infraestrutura

Foi iniciado PostgreSQL 16 real e isolado, em container temporário sem volume e rede dedicada. A porta foi dinâmica e publicada somente em 127.0.0.1; imagem reportou PostgreSQL 16.15. Banco: asterion_audit. Não foi usado banco de produção. O serviço permaneceu ativo durante a bateria. Identificadores temporários registrados para remoção: container 94996e96c06e4daa0395320426c46d1325137986c2792c5cf03da52c35b62bee; rede f8e47d13e4fb605b97b4e489c7de0bd9f4097ec60223aefae621b6200db9b6b9. Serão removidos ao fim.

Comando completo, sem seleção, exclusões, xfails novos ou cache do pytest:

    $env:PYTHONPATH='src;.'
    $env:ASTERION_TEST_DATABASE_URL='postgresql+asyncpg://postgres:<senha temporaria>@127.0.0.1:<porta dinamica>/asterion_audit'
    $env:ASTERION_DATABASE_URL=$env:ASTERION_TEST_DATABASE_URL
    $env:PYTHONDONTWRITEBYTECODE='1'
    $env:ASTERION_RUN_TDO_FULL_PLAYTHROUGH='1'
    $env:ASTERION_RUN_VDE_FULL_PLAYTHROUGH='1'
    .venv\Scripts\python.exe -m pytest -p no:cacheprovider -ra

As variáveis das jornadas longas habilitaram testes opt-in preexistentes. Uma tentativa preliminar sem essas variáveis foi interrompida após detectar a condição opt-in; não é contada como resultado de teste. A tentativa válida é a única usada nos números finais abaixo.

**Resultado final da tentativa completa:** terminou com código de saída 1: **1.628 passed, 2 failed, 0 errors, 0 skipped**, 6 warnings, em 4.239,92 s (1 h 10 min 39,92 s). A execução foi completa, sem exclusões, com ambos os flags de playthrough iguais a 1.

Falhas reproduzíveis:

1. tests/test_varzeas_v1_0_1_source_contract.py::test_varzeas_source_authority_is_current_and_has_no_global_barrier_default, linha 65. O teste exige que o cabeçalho do índice diga 2026-10-15, enquanto o SOURCE_AUTHORITY vigente local indica 2026-10-18; a mesma verificação confirma a versão Várzeas v1.0.3 FINAL. A divergência é a expectativa histórica do teste, não evidência de conteúdo aprovado alterado.
2. tests/test_vde_full_playthrough.py::test_vde_full_playthrough_from_fresh_tdo_exit. O fluxo percorreu a saída TDO e chegou à P12 de Vales; a Matriarca permaneceu viva após as tentativas do plano e o teste falhou no assert que exige kind == examine_center. A última tentativa registrada foi derrota após 20 ações: Sentinela Nv.20, HP 1.220/1.220 no início, chefe 2.548 HP no início, 905 HP restantes, jogador 0 HP, fase II, sem consumíveis usados, 5 cargas Devastador consumidas e nenhuma conexão destruída. É uma falha concreta de conclusão deste plano Solo; causa raiz de produto versus estratégia de teste ainda não isolada. Não foi corrigida nesta auditoria.

Os seis warnings foram deprecations de Starlette/httpx, AnyIO BlockingPortal e FastAPI on_event; não causaram erro de teste.

### Qualidade estática já executada

| Verificação | Comando/resultado |
|---|---|
| Ruff | .venv\Scripts\python.exe -m ruff check --no-cache src tests alembic — passou: “All checks passed!” |
| Sintaxe | AST parse de Python em src, tests e alembic — passou, 418 arquivos. |
| Alembic heads | .venv\Scripts\python.exe -m alembic heads — 20261010_0027 (head). |
| Alembic contra PostgreSQL temporário | Passou: alembic upgrade head aplicou a cadeia inteira até 20261010_0027; alembic check retornou “No new upgrade operations detected.” |
| git diff --check | Executar após validar o documento e antes do commit. |
| Weapon Metadata | A suíte completa incluiu o teste: 22 linhas históricas + Guarda do Último Protocolo P36 + Guarda das Duas Versões da Câmara = 24 entradas locais; não consta entre as falhas. O teste preserva IDs/metadata exatos e rejeita duplicação e weapon_family. |

Contagem local antes da coleta: 178 arquivos em tests, 173 arquivos com função test_ literal e 1.223 funções de teste literais em busca anterior; esses números não substituem itens parametrizados nem o total coletado do pytest.

### Cobertura e limitações

Dois playthroughs longos opt-in (TDO e Vales) foram habilitados. Eles não cobrem jornada 1–60 contínua, todas as seis classes de ponta a ponta, nem execução de Legado. Testes por módulo e integrações regionais cobrem os outros sistemas existentes. Se o runner reportar skips internos de critérios amostrais de um playthrough, eles serão apresentados como skips observados, não omitidos nem tratados como aprovado.

## G. Inventário priorizado de achados

Severidades seguem os critérios desta auditoria: P1 significa sistema obrigatório do lançamento ausente/incompleto; P2 significa integração/cobertura ou UX significativa; P3 é melhoria não bloqueante. Não houve evidência suficiente para classificar como P0. “Fonte” abaixo usa GDD §§48–49 e a seção mais específica do GDD citada pelo próprio requisito.

### GLOBAL-AUD-001 — Fontes canônicas solicitadas não estão no checkout

Severidade P1 · Categoria OPERACAO_NAO_VALIDADA · Sistemas: Lore e visuais. Fonte: SOURCE_AUTHORITY e solicitação de auditoria; GDD governança/hierarquia.

Requisito: validar lore pela Bíblia Canônica v3.0 FINAL e assets/skins pela autoridade vigente aplicável. Encontrado: Bíblia v3.0 e “Fonte Visual de Skins v1.2.0 FINAL” não estão presentes; há somente Lore v1.2 complementar e outra fonte Visual/UI selecionada pelo índice. Evidência: SOURCE_AUTHORITY.md identifica os arquivos vigentes; Test-Path/search do nome exato não os localizou. Impacto: não se pode aprovar completamente limites de lore nem inventariar assets canônicos. Dependências: disponibilizar documentos finais ou corrigir governança documental em tarefa autorizada. Recomendação: sincronizar as fontes oficiais sem reescrevê-las; refazer comparação de lore/skins. Aceite: hash e status aprovados registrados e ambas as matrizes sem referência ausente. Testes: verificação de hash/índice e validação editorial cruzada; nenhum código.

### GLOBAL-AUD-002 — Jornada orgânica completa não comprovada

Severidade P1 · Categoria COBERTURA_INSUFICIENTE · Sistema: campanha/progressão. Fonte: GDD §§4, 16, 48–49.

Requisito: jornada legal criação→P1–P36→Nv.60→elegibilidade de Legado, sem flags artificiais. Encontrado: suítes regionais e dois playthroughs longos regionais; testes criam níveis/gates para conteúdo alto, e não há fluxo integrado único atravessando seis regiões. Impacto: risco não medido de progressão/XP, saída entre regiões, gates cumulativos, perfil de classe e economia de longo prazo. Dependências: Legacy jogável (003), seleção de ambiente/fixtures e todas as recompensas canônicas. Recomendação: construir teste de jornada natural por atividade com seis classes e caminhos representativos, sem mudar baseline. Aceite: percurso PostgreSQL desde criação até P36 Nv.60 com log de XP/saldo/gates; nenhum nível ou moeda injetado. Testes: jornada full playthrough, reconexão e casos Solo/Grupo.

### GLOBAL-AUD-003 — Legado I–V não é executável

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Sistema: Legado. Fonte: GDD §16 e §48.

Requisito: ascensão voluntária em Local Seguro, níveis I–V, multiplicadores, Marcas e redistribuição, preservando direitos e revalidando gates atuais. Encontrado: P36 grava unlock.campaign.first_journey_complete e legacy_eligible; não há serviço, entidade, comando ou handler de execução. Evidência: src/asterion/application/altos_missions.py (liquidação P36); busca em application/bot/models não encontrou motor de Legado. Impacto: loop pós-Nv.60 anunciado não é jogável. Dependências: P36 e progressão persistente. Recomendação: implementar como sistema próprio sob contrato global, com ação separada de P36. Aceite: fluxos I–V persistem em PostgreSQL, respeitam bloqueios e Marcas, mantêm a campanha concluída, e permitem jogar novamente em nível atual sem reabrir P1. Testes: transições I→V, custos, rollback, reentrada, direitos persistentes e gates de conteúdo. Esforço: Muito Grande.

### GLOBAL-AUD-004 — Eventos Públicos e Sintonização não implementados

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§21, 48–49.

Requisito: conteúdo de evento com agenda/gatilhos, participação, contribuição, resolução e recompensa integrada ao Véu. Encontrado: nenhuma aplicação/modelo/router ou teste de evento; preference category “events” é somente configuração. Impacto: parte pública recorrente do escopo não existe. Dependências: scheduler durable (018), estado de mundo/Crônica (005), economia e participantes. Recomendação: definir configuração de eventos da Crônica I em autoridade vigente e implementar motor + conteúdo. Aceite: execução agendada e acionável em PostgreSQL, contribuição individual persistente, resolução única e recuperação pós-restart. Testes: janela, concorrência, participação, reward, reset e estado mundial. Esforço: Grande.

### GLOBAL-AUD-005 — Crônica I e Nova Vigília não implementadas

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§5, 21, 48–49.

Requisito: oito capítulos, cadência semanal, objetivos, atividade cooperativa, votação com regra única, desempate, consequência/estado mundial versionado, Códice e arquivo histórico. Encontrado: nenhuma entidade/serviço/rota/teste de Crônica; categoria de notificação não comprova motor. Impacto: lançamento sem eixo sazonal e sem Nova Vigília. Dependências: scheduler e Outbox (018), Events (004), persistência versionada e governança. Recomendação: implementar ciclo, votação e New Vigil separadamente da Trilha/Passe. Aceite: oito capítulos com calendário, voto único conta/servidor/Crônica, desempate determinístico, consequências versionadas e arquivo imutável após fechamento. Testes: concorrência no voto, reinício de janela, multi-dispositivo e recuperação. Esforço: Muito Grande.

### GLOBAL-AUD-006 — Trilha/Passe da Crônica não implementados

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§5, 34–36, 48–49.

Requisito: 40 marcos, recompensas Livres/Premium, progressão única, entitlement retroativo, janela de compra e período de 14 dias para resgate/liquidação. Encontrado: nenhum modelo/serviço/router/teste. Impacto: uma superfície de progressão e recompensa pública está ausente. Dependências: Crônica (005), Cosméticos e pagamentos (014). Recomendação: persistir progresso independente da compra e habilitar retro-resgate somente para entitlement válido. Aceite: 40 marcos imutáveis, recompensas livres sem pagamento, premium sem poder, compra retroativa e janela/arquivamento corretos. Testes: concorrência de claim, compra tardia, expiração e não pay-to-win. Esforço: Grande.

### GLOBAL-AUD-007 — Mercado e Loja Pessoal não implementados

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§28, 34, 36, 48–49.

Requisito: Loja Pessoal, Código Único, busca/divulgação, listings, compra parcial, taxas, escrow, entrega, payout, pendências e recuperação. Encontrado: nenhum modelo, serviço, router ou teste de listing/escrow/checkout. Impacto: comércio entre jogadores não é possível. Dependências: inventário, ledger econômico, idempotência, rate limiting/admin (019–020). Recomendação: implementar ledger/escrow atomicamente antes da UI comunitária. Aceite: compra concorrente não duplica item/moeda; cancelamento libera escrow; vínculo/inelegibilidade impede anúncio; recuperação após interrupção reconcilia ambos os lados. Testes: two buyers, partial fill, stale callbacks, seller/buyer disconnect e suspensão. Esforço: Muito Grande.

### GLOBAL-AUD-008 — Troca Direta não implementada

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§29, 34, 48.

Requisito: proposta, itens/quantidades, aceite de ambas as partes, travamento, invalidar confirmação após alteração e settlement atômico. Encontrado: nenhum trade service/schema/handler/teste. Impacto: usuários não conseguem trocar itens diretamente com segurança. Dependências: inventário/ledger e controles de segurança (020). Recomendação: implementar transação com versionamento de oferta e escrows temporários. Aceite: termos não podem mudar após confirmação sem invalidá-la; uma única conclusão transfere exatamente os bens/moedas. Testes: duplo aceite, alteração concorrente, cancelamento e desconexão. Esforço: Grande.

### GLOBAL-AUD-009 — Serviços de Ofícios entre jogadores ausentes

Severidade P1 · Categoria IMPLEMENTACAO_PARCIAL · Fonte: GDD §§27–28, 48.

Requisito: profissional oferece serviço, cliente contrata, materiais/taxa são reservados e liquidados por execução legítima. Encontrado: Crafting pessoal e profissão estão implementados; fluxo de oferta via Loja, reserva e execução por outro personagem não encontrado. Impacto: ofícios não entregam o componente econômico/social prometido. Dependências: Mercado (007), ledger e sanções. Recomendação: service listings dependentes da Loja pessoal, com contrato e escrow próprios. Aceite: serviço só executa se requisito de ofício for válido; cancelamento/falha recupera recursos sem duplicação. Testes: profissional inelegível, material parcial, conclusão/reversal e callbacks duplicados. Esforço: Grande.

### GLOBAL-AUD-010 — Guilda persistente não implementada

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §30, §48.

Requisito: criação, nome/TAG, custos, convites, procurar, recrutamento, inscrição, capacidade, cargos, liderança, saída/dissolução, tesouraria, obras e histórico. Encontrado: Group Social de sessão existe; guilda não aparece como modelo/serviço/rota/teste. Impacto: identidade e cooperação persistentes de comunidade não existem. Dependências: account/character, audit/admin, ledger e callbacks concorrentes. Recomendação: primeira etapa da cadeia Guilda antes de Juramento/Expedição/GvG. Aceite: permissões validadas pelo servidor, capacidade serializada, histórico auditável e liderança recuperável. Testes: inscrição concorrente no último slot, eleição/saída do líder, saque de tesouraria e callbacks velhos. Esforço: Muito Grande.

### GLOBAL-AUD-011 — Juramento, Expedição e GvG ausentes

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§14–15, 22, 30, 48.

Requisito: atividades de guilda com ciclo, elegibilidade, roster, resolução, recompensa e histórico; GvG precisa pareamento, combate, resultado/rating e integração de temporada. Encontrado: nenhum dos três subsistemas e nenhuma persistência/testes; PvPvE e Group não são substitutos. Impacto: conteúdo multiplayer de Guilda é inoperante. Dependências: Guilda (010), Crônica/Scheduler (005/018), combate/snapshot já existente. Recomendação: implementar em tarefas separadas: Juramento; Expedição; GvG. Aceite por tarefa: sessão persistente e resultados idempotentes, roster congelado, recompensa uma vez; GvG com empate, rating e histórico versionados. Testes: corrida de roster, disconnect, reset, rating e payoff. Esforço: Muito Grande.

### GLOBAL-AUD-012 — Duelo não implementado

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§14, 48.

Requisito: desafio/aceite, elegibilidade, PvP individual, vitória/derrota/desistência, persistência e Exaustão. Encontrado: PvPvE de Caçada apenas; sem serviço/entidade/handler de duelo. Impacto: PvP de duelo não pode ser usado. Dependências: combate PvP, autorização e proteção contra abuso. Recomendação: sessão de duelo com snapshot/participantes e sem settlement econômico não aprovado. Aceite: convite expira, combate persiste e resultado não é duplicado/boostable. Testes: aceitação concorrente, desconexão, desistência e bloqueios. Esforço: Médio/Grande.

### GLOBAL-AUD-013 — Arena/MRR/Elos e temporadas ausentes

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§14–15, 48–49.

Requisito: matchmaking, MMR oculto, placement/Renome, seis Elos, temporada, reset/decay/recompensas, abandono e anti-boosting. Encontrado: sem fila, rating, leaderboard ou integração temporal. Impacto: modo competitivo declarado no lançamento não existe. Dependências: Crônica (005), scheduler (018), telemetry/security (020/021), combate snapshotado. Recomendação: implementar primeiro baseline de Arena e depois integração de temporadas. Aceite: resultados válidos atualizam MMR uma vez, season transition determinística e auditada, disconnect/boost cases resolvidos conforme GDD. Testes de ranking, reset, grupos e adversarial. Esforço: Muito Grande.

### GLOBAL-AUD-014 — Patrono, pagamentos e cosmetização temporal ausentes

Severidade P1 · Categoria DEPENDENCIA_EXTERNA e IMPLEMENTACAO_AUSENTE · Fonte: GDD §§34–36, 48.

Requisito: pagamento verificado/idempotente, entitlement e expiração/fallback/reversal; Patrono e Passe não podem dar poder. Encontrado: nenhum fluxo de compra, webhook, ledger de pagamento ou provedor configurado. Impacto: monetização pública não é operável; compra não deve ser liberada. Dependências: escolha/contratação de provedor e credenciais fora do checkout, catálogo cosmético (023/026), admin auditável. Recomendação: selecionar provedor sem fazer transação real na auditoria e desenhar verificação de assinatura/reconciliação. Aceite: webhook repetido/reordenado não duplica entitlement, reversal é auditado, cosméticos expiram com fallback e nenhum poder é vendido. Testes: assinatura inválida, replay, chargeback, entitlement e restore. Esforço: Grande, mais integração externa.

### GLOBAL-AUD-015 — Dádiva, Chamado, Comunidade e Códigos ausentes

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§31–32, 36, 48.

Requisito: claim diário, convite/referral, validação, limites por identidade, recompensa, códigos e prevenção de abuso. Encontrado: sem modelos/serviços/handlers/tests. Impacto: loop de engajamento e comunidade ausente. Dependências: account identity, scheduler (018), admin (019), anti-abuse (020), ledger. Recomendação: separar Daily Gift, Chamado e códigos em entregas pequenas após idempotência/admin. Aceite: claim por ciclo e limites account/character/server são enforced transacionalmente e auditáveis. Testes: rollover UTC/timezone, multiaccount, self-referral, code replay e concorrência. Esforço: Grande.

### GLOBAL-AUD-016 — Amigos, bloqueios e Vínculos incompletos

Severidade P1 · Categoria IMPLEMENTACAO_PARCIAL · Fonte: GDD §§31–32, 48.

Requisito: pedidos, amigos, block, busca/visibilidade, recentes, privacidade, persistência e integração com Group/Guild. Encontrado: Group/invite existe; menu Vínculos leva a links:root, sem relação social completa encontrada. Impacto: social discovery e controle de contato insuficientes. Dependências: account privacy, moderação/admin (019), grupos/guilda. Recomendação: adicionar grafo social separado de Group. Aceite: blocks impedem invites/search conforme política, pedidos idempotentes e revogação consistente em todos os dispositivos. Testes: privacidade, block, duplicate requests e autorização. Esforço: Grande.

### GLOBAL-AUD-017 — Relatos e controles de privacidade do Perfil não comprovados

Severidade P2 · Categoria IMPLEMENTACAO_PARCIAL · Fonte: GDD §§31–33, 48.

Requisito: perfil/história/relatos exibíveis com visibilidade, moderação e proteção de spoilers. Encontrado: CharacterProfile e character_surfaces cobrem história/superfície; nenhuma ferramenta de Relatos/moderação ampla foi demonstrada. Impacto: conteúdo social pode ficar indisponível ou expor dado privado. Dependências: Friends/Privacy (016), admin (019). Recomendação: fechar schema de visibilidade, denúncia/moderação e integração de cosméticos. Aceite: cada campo respeita visibilidade, bloqueio e anti-spoiler; ações moderativas auditadas. Testes: permissões por público, edição e report. Esforço: Médio.

### GLOBAL-AUD-018 — Entrega Outbox, scheduler e sincronização multidispositivo

Severidade P1 · Categoria IMPLEMENTACAO_PARCIAL · Fonte: GDD §§43.5–43.6, 44, 47–48.

Requisito: entrega transacional com retries e scheduler/ciclos duráveis, foreground e callbacks sincronizados entre dispositivos. Encontrado: OutboxMessage dedup sem worker; APScheduler local de 15s para Ronda; snapshots/locks parciais. Impacto: notificações e jobs podem não sobreviver a restart ou duas instâncias; callbacks podem apresentar estado desatualizado. Dependências: DB/outbox, deployment (022), Events/Crônica (004/005). Recomendação: worker durável com claim/lease/backoff/dead-letter; jobs persistentes com liderança; versão de sessão por conta/personagem. Aceite: crash/restart e duas instâncias retomam um job sem dupla liquidação e callbacks stale são recusados. Testes: crash injection, lease expiration, multidevice e dedup. Esforço: Grande.

### GLOBAL-AUD-019 — Administração/moderação e auditoria não completas

Severidade P1 · Categoria IMPLEMENTACAO_PARCIAL · Fonte: GDD §§43.7, 46–48.

Requisito: papéis de admin, sanções, inspeção e trilha imutável de ações, reconciliação e suporte. Encontrado: endpoints health/ready; sem console/admin service amplo identificado. Impacto: suporte, intervenção segura e tratamento de fraude não estão prontos. Dependências: identidade admin, logs/outbox (018/021), pagamento/market (007/014). Recomendação: criar admin APIs/commands segregados, RBAC e auditoria append-only antes de sistemas de economia aberta. Aceite: toda ação crítica registra autor/alvo/razão/diff, ações não autorizadas são negadas e recuperáveis. Testes de permissão, replay e integridade. Esforço: Grande.

### GLOBAL-AUD-020 — Segurança transversal e antiexploit insuficientes

Severidade P1 · Categoria OPERACAO_NAO_VALIDADA · Fonte: GDD §§34–36, 43–47.

Requisito: rate limiting, anti-RMT/boosting/multiaccount, callback authorization, idempotência e limites. Encontrado: algumas proteções e testes locais; cobertura transversal e rate limiting não demonstrados. Impacto: risco de abuso crescerá especialmente com Market, referral e Arena. Não há exploit confirmado neste diagnóstico. Dependências: admin/audit, outbox, economia entre jogadores. Recomendação: threat model de lançamento e controles antes de abrir economia competitiva. Aceite: controles têm limites observáveis, sanção reversível auditada e casos de abuso simulados. Testes: replay/fuzz/rate, corrida concorrente e abuse cases. Esforço: Grande.

### GLOBAL-AUD-021 — Observabilidade sem métricas e alertas comprovados

Severidade P1 · Categoria OPERACAO_NAO_VALIDADA · Fonte: GDD §§43, 48.

Requisito: logs estruturados, métricas, alertas e detecção de falhas. Encontrado: health/ready e logging básico; nenhum conjunto de alertas/SLOs validado. Impacto: equipe pode não detectar economia travada, falha de jobs ou indisponibilidade. Dependências: operação/deploy. Recomendação: instrumentar métricas de negócio/infra, dashboards e alertas testáveis. Aceite: falha simulada de DB, Redis, worker e settlement dispara alerta e permite localizar correlação. Testes/runbook de chaos. Esforço: Médio/Grande.

### GLOBAL-AUD-022 — Deploy/patch/drain de produção não validados

Severidade P1 · Categoria OPERACAO_NAO_VALIDADA · Fonte: GDD §43.6 e §48.

Requisito: deploy, migrations compatíveis, drain, manutenção e patch lifecycle. Encontrado: CI e Compose de development; sem evidência de ambiente e rollout produção testado. Impacto: releases podem interromper atividades ou deixar schema incompatível. Dependências: observabilidade e backups (021/023). Recomendação: pipeline de staging com expand/contract migrations, drain dos workers, health gate e rollback. Aceite: deploy simulado com atividade ativa, upgrade e recuperação executam sem perda/duplo reward. Testes: migration upgrade/downgrade aplicável, rolling restart e rollback runbook. Esforço: Grande.

### GLOBAL-AUD-023 — Backup, restore e reconciliação não validados

Severidade P1 · Categoria IMPLEMENTACAO_AUSENTE · Fonte: GDD §§43.2, 43.6, 48.

Requisito: backup, retenção, restauração testada e reconciliação de dados econômicos. Encontrado: Compose de dev declara volumes locais; não equivale a backup/restore de produção. Nenhum restore test foi encontrado. Impacto: risco alto de perda irrecuperável de personagens e ledger. Dependências: deploy, auditoria e secrets/infra. Recomendação: job de backup criptografado/retido, runbook e restore isolado automatizado. Aceite: restore em ambiente limpo satisfaz RPO/RTO aprovados e checksums de ledger/rewards. Testes: restore periódico e reconciliação. Esforço: Grande.

### GLOBAL-AUD-024 — Flavor contextual sem contrato transversal

Severidade P2 · Categoria IMPLEMENTACAO_PARCIAL · Fonte: GDD §§37–39, 48.

Requisito: contextualizar mensagens conforme personagem/atividade/evento sem criar fatos incompatíveis. Encontrado: texto contextual embutido em módulos regionais, mas não catálogo/seleção geral versionada. Impacto: repetição, inconsistência e manutenção textual localizada. Dependências: fontes canônicas e UI. Recomendação: catalogar IDs e critérios contextuais sem alterar a narrativa aprovada. Aceite: rendering escolhe contexto válido e fallback neutro, com procedência testada. Testes por atividade e anti-spoiler. Esforço: Médio.

### GLOBAL-AUD-025 — UX Telegram transversal e E2E de fluxo real incompletos

Severidade P2 · Categoria COBERTURA_INSUFICIENTE · Fonte: GDD §§37–39, 48.

Requisito: fluxo completo por menus, callbacks autorizados, bloqueios claros, reconexão, mensagens obsoletas, estado vazio e erro tratado. Encontrado: routers e testes por feature; sistemas ausentes não têm UI e não há E2E com runtime implantado. Impacto: fricção e falhas de navegação não medidas. Dependências: implementação dos sistemas; atualização de fonte visual. Recomendação: após cada feature, teste de caminho feliz/blocked/stale/error com callback Telegram simulado. Aceite: todos os itens do menu §48 levam a serviço real ou mensagem de disponibilidade aprovada; nenhum botão morto. Testes de router/runtime e reconnect. Esforço: Médio/Grande.

### GLOBAL-AUD-026 — Pipeline de assets e integração visual ausentes

Severidade P2 (pode tornar-se P1 conforme critério de publicação) · Categoria IMPLEMENTACAO_AUSENTE · Fonte: Fonte Visual/UI registrada em SOURCE_AUTHORITY; GDD §§33, 37–39, 48.

Requisito: assets oficiais de criação, raça/classe, ambientes, criaturas, boss e cosméticos, com fallback. Encontrado: zero imagens rastreadas; creation_images vazio por default; fonte de skins solicitada ausente. Impacto: apresentação visual entregue é majoritariamente texto e não verificável. Dependências: documentos finais/fonte visual (001), pipeline Telegram e direitos de asset. Recomendação: matriz asset→fonte→arquivo/Telegram file_id→tela/fallback, sem inventar arte canônica. Aceite: todos assets requeridos estão versionados ou com ID gerenciado, licença/procedência conhecida e fallback testado. Testes: validador de inventário e telas sem asset. Esforço: Grande.

### GLOBAL-AUD-027 — Cobertura de jornada por Classe insuficiente

Severidade P2 · Categoria COBERTURA_INSUFICIENTE · Fonte: GDD §§6–13, 48–49.

Requisito: seis Classes legais em jornada Solo e conteúdo Grupo com combate/scaling. Encontrado: testes unitários/combinatórios de classes, Arts e caminhos; não há evidência de campanhas completas por seis Classes. Impacto: classes podem funcionar em combates locais e falhar na progressão longa. Dependências: teste natural (002). Recomendação: simular por orçamento e rodar jornadas representativas para cada Classe, incluindo Grupo sem alterar balanceamento. Aceite: todas as Classes completam checkpoints legais e conteúdo essencial sem bypass, com invariantes de equipamento. Testes: six-class journey, boss solo, dungeon group e economy. Esforço: Grande.

### GLOBAL-AUD-028 — Teste de operação real do Telegram e staging ausentes

Severidade P2 · Categoria DEPENDENCIA_EXTERNA · Fonte: GDD §§37–39, 43–48.

Requisito: executar fluxo de jogador em staging com Telegram e dependências sem dados reais. Encontrado: handlers/testes locais e endpoints de webhook; não foi fornecido ambiente de staging nem tokens/credenciais (nenhum segredo foi lido). Impacto: webhook, retries, rate limits de plataforma e deploy público não estão validados. Dependências: deploy/ops (022), tokens próprios e ambiente externo controlado. Recomendação: criar staging/test bot separado, sem pagamento real. Aceite: smoke test de /start→criação→menu→combate→reconnect e rollback de webhook. Testes: staging automatizado e runbook. Esforço: Médio.

### GLOBAL-AUD-029 — Teste de autoridade de Várzeas usa data de sincronização antiga

Severidade P2 · Categoria DEFEITO_CONFIRMADO (asserção de teste; não é defeito confirmado da Fonte/código de produção) · Sistema: governança de autoridade/testes. Fonte: SOURCE_AUTHORITY.md e regra de sincronização dos índices.

Requisito: teste de contrato deve validar a autoridade vigente sem fixar uma data histórica. Encontrado: o índice diz 2026-10-18 e seleciona Várzeas v1.0.3 FINAL; o teste exige 2026-10-15 e falha. Evidência: tests/test_varzeas_v1_0_1_source_contract.py:65, conteúdo atual de SOURCE_AUTHORITY.md e espelho idêntico. Impacto: suíte integral fica vermelha por teste obsoleto, reduzindo confiança no sinal de regressão. Dependências: somente regra de teste/autoridade; fontes aprovadas não devem ser modificadas. Recomendação: conferir o significado da data no contrato e atualizar a expectativa de forma explícita, preservando hash/versão/precedência verificadas. Aceite: teste passa com a autoridade atualmente registrada e continua rejeitando versão/hash divergentes. Testes: teste isolado e suíte completa sem exclusão. Esforço: Pequeno.

### GLOBAL-AUD-030 — Jornada Solo integrada não vence P12 da Matriarca no plano exercitado

Severidade P1 · Categoria COBERTURA_INSUFICIENTE (falha de fluxo reproduzida; universalidade do problema não estabelecida) · Sistema: jornada Solo/combatibilidade de Chefe. Fonte: GDD §§4, 9–13, 49.1, 49.6 e 51.6.

Requisito: progressão Solo funcional e Chefe de campanha viável com build legal, sem nível/recompensa fabricados. Encontrado: test_vde_full_playthrough_from_fresh_tdo_exit percorreu TDO→Vales mas esgotou o plano de retries de P12 sem vitória. Evidência: traceback pytest e última tentativa: Sentinela Nv.20, início 1.220 HP contra Matriarca 2.548 HP, derrota em 20 ações com 905 HP de boss restante, sem Consumíveis usados e sem destruir Conexões. Impacto: a jornada 1–20 não foi validada para este caminho de combate; não se pode afirmar que o cenário representa todos os jogadores ou provar impossibilidade de vitória. Dependências: revisar a estratégia/política automatizada, preparação adquirida legalmente, Consumíveis e escala de P12; não mudar baseline nesta tarefa. Recomendação: analisar replay e executar estratégias legais alternativas antes de concluir se há defeito de balanceamento ou inadequação do harness. Aceite: teste natural Solo chega a P12 e vence por serviço público, ou o harness documenta uma estratégia legítima reproduzível sem bypass; as seis Classes precisam de cobertura equivalente. Testes: replay determinístico com trace, retries/consumíveis/Conexões, jornadas por Classe e regressão PG. Esforço: Médio para diagnóstico; potencialmente Grande para correção se confirmada.

## H. Backlog recomendado em tarefas pequenas

| Ordem | IDs | Entrega independente recomendada | Esforço | Saída de aceite |
|---|---|---|---|---|
| 0 | 001 | Sincronizar as duas autoridades ausentes; revalidar conteúdo/lore e visuais sem alterar fontes | Pequeno/Operacional | Hash/status vigentes acessíveis e índice coerente |
| 0a | 029 | Alinhar somente a asserção do teste de Várzeas com a data vigente do índice, mantendo as verificações de versão/conteúdo | Pequeno | Teste de contrato passa contra a data efetivamente aprovada |
| 0b | 030 | Diagnosticar replay e estratégia Solo de P12; decidir com evidência se é harness/preparação ou comportamento de produto | Médio | P12 vence em fluxo público legal, ou causa técnica documentada e encaminhada sem contornar baseline |
| 1 | 003 | Implementar Legado I com ação voluntária e persistência | Grande | Ascensão I completa sem reset indevido |
| 2 | 003 | Implementar Legado II–V, Marcas, investimento e redistribuição | Muito Grande | Fluxo I→V e gates revalidados |
| 3 | 002, 027 | Jornada natural e seis Classes, depois do Legado I | Grande | E2E PG criação→P36→Nv.60→Legado I |
| 4 | 018 | Worker Outbox com claim, retry, dedup e recuperação | Grande | Envio retoma após crash sem dupla entrega |
| 5 | 018 | Scheduler persistente/distribuído para ciclos e jobs | Grande | Duas instâncias e restart não duplicam nem perdem job |
| 6 | 021 | Métricas, logs estruturados, dashboards e alertas | Médio/Grande | Falhas simuladas de DB, Redis e worker geram alertas acionáveis |
| 7 | 022 | Deploy, migration compatível, drain e rollback | Grande | Rolling deploy com atividade em curso e recuperação demonstrados |
| 8 | 023 | Backups, restore isolado e reconciliação | Grande | Restore periódico satisfaz RPO/RTO aprovados e confere ledger |
| 9 | 019 | Administração, RBAC, sanções e trilha de auditoria | Grande | Ações privilegiadas autorizadas e auditáveis |
| 10 | 020 | Threat model, rate limiting e controles antiabuso | Grande | Replay/abuso/rate tests passam antes de economias abertas |
| 11 | 010 | Guilda básica, permissões, capacidade e liderança | Grande | Ciclo de guilda sem corridas |
| 12 | 016 | Amigos, busca, bloqueios e privacidade | Grande | Blocks e visibilidade aplicados em todos os convites/superfícies |
| 13 | 017 | Perfil e Relatos com visibilidade/moderação | Médio | Campos públicos/privados e moderação aplicados |
| 14 | 007 | Loja pessoal, Código Único e escrow | Muito Grande | Compra parcial/reconciliação segura |
| 15 | 008 | Troca Direta | Grande | Reserva e settlement atômicos |
| 16 | 009 | Serviços de Ofícios integrados à Loja | Grande | Cliente/fornecedor com reserva e recuperação |
| 17 | 005 | Crônica I e Nova Vigília | Muito Grande | Capítulos, votação e arquivamento reproduzíveis |
| 18 | 004 | Eventos Públicos e Sintonização | Grande | Evento agendado e idempotente |
| 19 | 013 | Arena, MMR e Elos | Muito Grande | Placement, partidas, temporadas e reset |
| 20 | 012 | Duelo | Médio/Grande | Convite, combate, resultado e desistência |
| 21 | 011 | Juramento de Guilda | Grande | Ciclo e contribuições persistem uma vez |
| 22 | 011 | Expedição de Guilda | Grande | Preparação, roster e recompensa persistentes |
| 23 | 011 | Batalha de Guildas | Muito Grande | Pareamento, combate, rating, empate e histórico |
| 24 | 006 | Trilha/Passe da Crônica | Grande | 40 marcos, entitlement retroativo e resgate |
| 25 | 014 | Patrono e pagamentos após seleção de provedor | Grande + externo | Webhook assinado, entitlement e reversão auditáveis em sandbox |
| 26 | 015 | Dádiva Diária | Médio | Claim diário único e recuperação comprovados |
| 27 | 015 | Chamado de Asterion | Médio/Grande | Indicações limitadas e antiabuso testados |
| 28 | 015 | Comunidade e Códigos de Asterion | Médio | Publicação, validade e resgates auditáveis |
| 29 | 026 | Pipeline e integração de visuais após autoridade confirmada | Grande | Inventário de assets e fallback |
| 30 | 024 | Catálogo de Flavor contextual | Médio | Seleção contextual e fallback neutro com procedência |
| 31 | 025, 028 | Fechamento de UX Telegram e smoke test de staging | Médio/Grande | Menu sem ações mortas e fluxo real smoke testado |

Essa ordem põe autoridade e validações críticas primeiro; cria Legado antes de validar o loop pós-Nv.60; estabelece Outbox, scheduler, observabilidade, deploy, backup, admin e segurança antes de abrir economias sociais; estabelece Guilda antes de atividades dependentes; cria Crônica antes de temporadas/Trilha; e exige provedor antes de pagamento. Cada linha é uma entrega pequena/coesa, com critério próprio.

## I. Matriz de dependências

| Dependência | Motivo comprovado |
|---|---|
| Bíblia/skins finais → auditoria canônica/visual | Sem autoridade selecionada e arquivo local não há base para comparar lore e lista de assets. |
| Outbox + scheduler + operação → Crônica, eventos, daily/referral e temporadas | GDD exige ciclos e entrega persistente; scheduler atual é em processo e Outbox não tem worker. |
| Guilda → Juramento, Expedição, GvG | Os três modos exigem identidade, roster, permissão e persistência de guilda. |
| Combate/snapshot existente + Guilda → GvG | GvG depende de roster congelado e resolução de batalha; os alicerces PvE podem ser reaproveitados sem substituir guilda. |
| Crônica → temporadas de Arena/GvG, Trilha e Nova Vigília | Cronograma/estado mundial/arquivo da Crônica ancora temporada e marcos. |
| Loja/Escrow → Serviços de Ofícios | §48 manda integrar Serviços às Lojas; serviço pessoal de Crafting não fornece escrow ou venda. |
| Ledger/inventário + Admin/segurança → Mercado e Troca | Escrow/transferência exige settlement atômico, auditoria, autorização e recuperação. |
| Provedor de pagamentos → Patrono/Passe Premium | Entitlement só pode ser concedido após verificação e reconciliação externa. |
| Legado → pós-Nv.60 e gates pós-ascensão | Elegibilidade isolada não executa o ciclo nem revalida nível atual. |
| Telemetria + backups + deploy/drain → lançamento público | Recuperação e suporte não são demonstrados pelo CI local. |
| Fonte visual + pipeline → Cosméticos/apresentação de criação | Catálogo de entitlement não produz nem distribui assets. |

## J. Critérios de lançamento

| Critério | Estado | Evidência/condição |
|---|---|---|
| Seis regiões, P1–P36, S1–S36 e 12 Masmorras no checkout | PRONTO em conteúdo de código; NAO_VERIFICADO em uma jornada completa | Módulos regionais/12 dungeons e testes focais; Bíblia v3 ausente e E2E global inexistente |
| Combate PvE, atividade regional, inventário e crafting pessoal | PRONTO no escopo testado localmente | Serviços, handlers, persistência e testes; suíte final em F deve ser lida após término |
| Weapon Metadata | PRONTO no checkout | 24 linhas canônicas atuais, verificação explícita de tags e ausência de weapon_family; suíte completa ainda em curso |
| Legado I–V executável | NAO_PRONTO | Somente flag de elegibilidade; sem ação/serviço/marcas |
| Mercado, Troca e Serviços entre jogadores | NAO_PRONTO | Serviços/fluxos ausentes |
| Guildas e suas três atividades | NAO_PRONTO | Ausentes |
| Duelo/Arena/Elos | NAO_PRONTO | Ausentes; PvPvE existente não substitui |
| Crônica I, Nova Vigília, Eventos e Trilha | NAO_PRONTO | Motores/fluxos ausentes |
| Patrono/pagamentos | NAO_PRONTO | Fluxos ausentes e provedor não selecionado/configurado |
| Amigos/Perfil/Relatos completos | NAO_PRONTO | Implementações parciais e regras não demonstradas |
| Telegram de sistemas existentes em staging | NAO_VERIFICADO | Testes locais existem; nenhum staging externo foi disponibilizado |
| Operação de produção, alertas e restore | NAO_PRONTO | Compose dev/CI não equivalem a procedimento de produção/restore testado |
| Visuais/skins oficiais entregues | NAO_VERIFICADO / NAO_PRONTO para critério visual completo | Zero assets rastreados; fonte de skins solicitada ausente |
| Autoridades canônicas de lore | NAO_VERIFICADO | Bíblia v3.0 citada não presente |

Resposta objetiva: se o Asterion fosse aberto hoje, a maior parte da experiência regional PvE estaria no checkout, mas os sistemas públicos obrigatórios de Legado, comércio, guildas, modos PvP, Crônica/recorrência, pagamentos e várias ferramentas de comunidade estariam ausentes ou incompletos. Operação de recuperação/observabilidade e assets visuais também não têm comprovação suficiente. O lançamento integral da seção 48 não está pronto.

## K. Estimativa de trabalho e síntese

| Métrica | Contagem observada |
|---|---:|
| Sistemas implementados e validados | 10 |
| Implementados sem validação suficiente | 1 |
| Parciais | 14 |
| Ausentes | 16 |
| Defeitos de produto confirmados | 0 confirmados independentemente; 1 divergência confirmada em expectativa de teste e 1 fluxo Solo falho ainda sem causa raiz isolada |
| Dependências externas | Provedor de pagamentos/credenciais; publicação e staging Telegram; distribuição de assets; entrega das fontes finais ausentes |
| Achados P0/P1/P2/P3 | 0 / 23 / 7 / 0 |

Os esforços são qualitativos porque não há desenho suficiente para estimar prazo com confiança. Sistemas sociais e competitivos têm esforço Grande/Muito Grande; são especialmente interdependentes e exigem novos modelos, transações, handlers, segurança e testes PostgreSQL/concorrência. A primeira tarefa de implementação recomendada, depois de fechar a autoridade documental, é **Legado I como uma fatia vertical pequena e isolada**: ação voluntária em Local Seguro, persistência de ascensão, bloqueios globais e um teste PostgreSQL ponta a ponta. Em paralelo, a próxima validação diagnóstica necessária é a jornada orgânica legal até P36, que depende do sistema de Legado estar executável.

### Fechamento da auditoria

Estado do documento: concluído com limitações explicitadas. A suíte completa terminou com duas falhas reproduzidas; Alembic upgrade/check e verificações estáticas foram registrados. O produto não satisfaz o escopo completo de lançamento da seção 48. A ausência de fontes finais e a falha do percurso P12 impedem declarar a validação global completa, ainda que o diagnóstico deste checkout esteja documentado.

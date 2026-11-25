# Autoridade das Fontes

**Índice atualizado:** 2026-11-19.

> **Índice geral único:** `SOURCE_AUTHORITY.md` é o registro de governança que seleciona as versões autoritativas por escopo. Patches de sincronização são artefatos operacionais e não constituem uma segunda autoridade. Em conflito com índices/patches anteriores, este arquivo prevalece quanto à seleção de versões, sem alterar o conteúdo interno das Fontes.

> **Sincronização 2026-10-17:** este índice registra Fonte Mestra v1.6.0, Terras do Ocaso v1.0.17 FINAL (adotada em 2026-11-12), Vales dos Enforcados v1.0.6 FINAL, Planícies de Nareth v1.0.2 FINAL, Várzeas Carmesins v1.0.3 FINAL, Altos Cinéreos v1.0.1 FINAL, Lore v1.2, Visual/UI de 2026-10-13 e anatomia racial v2.0. Notas históricas mais abaixo podem citar versões anteriores apenas como registro; não reativam autoridade superada.

> **Sincronização 2026-10-18:** Confins do Véu v1.0.0 FINAL (`FINAL_APPROVED`, conteúdo regional C aprovado) está registrado na Região 6. O Contrato Global de Weapon Metadata v1.0.0 FINAL permanece íntegro e vigente, SHA-256 `c283b398949dc0a864d98b9e0e9031080a50b937db6932ffcde7d46e600aa740`. O GDD v1.7.1 é a Fonte Mestra para sistemas globais; a Bíblia Canônica Consolidada v4.0.7 (`ASTERION_BIBLIA_CANONICA_v4_0_7.md`) rege Lore, identidades e limites; a Fonte Regional rege o conteúdo fechado da Região 6. **HANDOFF À ENGENHARIA AUTORIZADO** após esta sincronização; isto não declara P31 implementada.

> **Sincronização 2026-11-11:** a Bíblia Canônica Consolidada de Mundo, Raças, NPCs e Regiões **v4.0.7** (`ASTERION_BIBLIA_CANONICA_v4_0_7.md`, SHA-256 `011ad3fb0ab2f2e940baca5cbe11ee89460353ee9709693005dcc26c398a431d`) passa a reger Lore, identidades, NPCs e limites, por decisão do autor. Substitui a v3.0 FINAL e, por sucessão, a v3.2 e a v3.3. O arquivo v3.0 permanece no repositório só como registro histórico. Nenhuma regra mecânica muda; o GDD v1.7.1 segue superior para sistemas.

> **Sincronização 2026-11-12:** a especificação **Ação × Consequência Narrativa v1.0.0** (`docs/specs/ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md`) passa a reger a camada de escolha/memória das 72 Missões, por decisão do autor. Ela **sobrescreve explicitamente o GDD v1.6.0 §51.3/§55.1** quanto ao Coop: Principais e Secundárias são Solo em progresso, objetivos, escolhas e estado narrativo; só encontros de Chefe aceitam Grupo 1–4. Esta divergência deve entrar na próxima revisão do GDD. Nenhum número de jogo muda.

> **Sincronização 2026-11-13:** a Fonte Mestra passa a ser o **GDD Estrutural v1.7.0** (`ASTERION_GDD_Estrutural_v1.7.0_Fonte_Mestra.md`) e o Contrato Global de Weapon Metadata passa a ser a **v1.1.0 FINAL** (`ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.1.0_FINAL.md`), por decisão do autor. Entram: Proficiências de Equipamento e Treinamento, categorias de proteção corporal (Vestes, Leve, Média, Pesada), Escudo não-arma, kits de Equipamentos de Origem, núcleos corporais por categoria e núcleo de Escudo (revogando o total fixo HP305/ATQ56/DEF33/AGI16), pesos de Saque v0.4 e a cobertura de Confins do Véu no mapeamento de armas (27 armas). **Não entram** IDs de template, receitas, vínculos nem elegibilidade individual de Saque da Fase 2E: continuam candidatos e não canônicos até a conciliação com o snapshot de release. Importação, migration, flag, merge e deploy da Fase 2E continuam NO-GO. A divergência de Coop de Missão de 2026-11-12 continua registrada neste índice e ainda não foi incorporada ao texto do GDD. As versões v1.6.0 e v1.0.0 permanecem no repositório como registro histórico.

> **Sincronização 2026-11-13 (Proficiências de Armas):** por decisão do autor, a **Especificação Final de Proficiências de Armas, Catálogo de Armas e Regras de Equipamento v1.0.0** (`docs/specs/ASTERION_ESPECIFICACAO_FINAL_PROFICIENCIAS_EQUIPAMENTO_v1_0_0.md`) substitui o sistema de Proficiências da v1.7.0. A Fonte Mestra passa a ser o **GDD Estrutural v1.7.1** (`ASTERION_GDD_Estrutural_v1.7.1_Fonte_Mestra.md`) e o Contrato Global de Weapon Metadata passa a ser a **v1.1.1 FINAL** (`ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.1.1_FINAL.md`). Ficam **revogados**: categorias de proteção corporal (Vestes, Leve, Média, Pesada) e seus núcleos, Proficiências naturais múltiplas, Treinamento em etapas I–IV e kits de Origem de 34 templates; volta o núcleo corporal por slot (Conjunto HP305/ATQ56/DEF33/AGI16). Entram: 8 famílias + Escudo, catálogo final de 19 armas + Escudo, matriz por Classe, 1 Proficiência inicial, Treinador de Armas no Refúgio do Ocaso (1.000 a 20.000 Coroas, Nível 10 a 50, sem teto) e arma inicial Comum +0 Grau I. O núcleo de Escudo e os pesos de Saque v0.4 não mudam. As versões v1.7.0 e v1.1.0 permanecem no repositório como registro histórico.
> **Sincronização 2026-11-14:** o autor adotou **Terras do Ocaso v1.0.18 FINAL** como Fonte Regional vigente da Região 1 (a v1.0.17 FINAL passa a histórica) e registrou o **Override regional** da Fonte Mestra descrito na seção "Override regional — Terras do Ocaso v1.0.18", logo após a Região 1. A Fonte Visual/UI recebeu a seção 66 (mapa, Explorar e Câmara do Poente). A `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_PROPOSTA.md` está superada pela FINAL e não tem autoridade. O GDD v1.7.1 continua superior fora dos 9 itens do override; ele deve incorporá-los na próxima revisão.

> **Sincronização 2026-11-16:** por decisão do autor, a **Consolidação de Visual & UI v1.6.2** (`ASTERION_UI_DECISOES_2026-11-16_FINAL_SYNC_v1.6.2_TDO_v1.0.18_VALES_v1.0.6.md`) passa a ser a Fonte Visual/UI vigente, substituindo a v1.6.1. A seção 66.1 define o Refúgio do Ocaso como tela principal nas Terras do Ocaso, incorpora os atalhos globais aprovados, preserva a abertura no Local atual e direciona os retornos regionais ao Refúgio. Campanha/Aventura permanecem nas demais regiões. Esta revisão não altera regras mecânicas nem conteúdo regional.

> **Sincronização 2026-11-19 (autoridade vigente):** a Fonte Mestra vigente é o **GDD Estrutural v1.7.1**; a Fonte Visual/UI vigente é a **Consolidação de Visual & UI v1.6.2**; a Fonte Regional vigente da Região 1 é **Terras do Ocaso v1.0.18 FINAL**. A **Especificação de Classes de Armadura v1.0.0** (`docs/specs/ASTERION_ESPECIFICACAO_CLASSES_DE_ARMADURA_v1_0_0.md`) é **exceção canônica, por decisão autoral**, ao GDD v1.7.1: mantém as categorias de proteção corporal Vestes, Leve, Média e Pesada, com Proficiências de Armadura e camada de Esquiva/Bloqueio. Essa exceção revoga, só nesse ponto, a revogação de 2026-11-13 descrita acima; o restante do GDD v1.7.1 permanece como está.

> **Sincronização 2026-11-25 (Receitas regionais nos Ofícios):** por decisão do autor, a **Especificação de Receitas Regionais nos Ofícios v1.0.0** (`docs/specs/ASTERION_ESPECIFICACAO_RECEITAS_REGIONAIS_OFICIOS_v1_0_0.md`) define quais Ofícios fabricam os 42 itens por região do catálogo de `domain/regional_equipment.py` (756 receitas: Comum, Raro e Épico). Os custos seguem o GDD v1.7.1 §49.11, sem número novo. Override regional: a regra de Confins do Véu v1.0.0 §19 Regra A ("sem armadura leve/média/pesada mecânica") fica superada pela exceção de Classes de Armadura, e Confins fabrica as 4 classes. A Fase 2E (pacote v1.9.x) foi encerrada como superada em 2026-11-25 e não tem autoridade (`docs/audits/ASTERION_AUDITORIA_FASE2E_v1.9.1_VS_MAIN_2026-11-25.md`).

> **Decisões do autor registradas em 2026-11-19 (somente documentação; nenhuma mudança em `src/`, `tests/` ou `alembic/` nesta etapa):**
>
> 1. **Criação de Personagem.** O fluxo canônico é **Nome → Gênero → Raça → Classe → Confirmação Final → Prólogo** (UI §45; ver a seção "Decisão aprovada pelo autor — Gênero na criação de personagem" no fim deste índice). **Gênero é obrigatório e revisável na Confirmação Final.** Nenhuma implementação deve removê-lo.
> 2. **Cosméticos.** As categorias canônicas são **Aparência, Título e Moldura** (GDD §33.4 e §37.2). **Emblema é mapeado para Título e Banner é mapeado para Moldura.** Qualquer migração de dados, de constraint do banco ou de código (hoje há `emblem` e `banner` em `COSMETIC_TYPES` e no CHECK de `cosmetic_type`) será feita em etapa própria.
> 3. **Terras do Ocaso — retornos.** Dentro das Terras do Ocaso, `← Menu`, `← Campanha` e `← Aventura` abrem/retornam à **tela do Refúgio do Ocaso** com o rótulo `[Voltar ao Refúgio]` (UI §66.1 item 6). Isso é **navegação de interface, não teletransporte**: o `location` persistido do personagem **não muda** por esse botão. O personagem continua podendo abrir o jogo no Local em que estava (UI §66.1 item 8). Esclarece a ambiguidade da §66.1 item 6; ajustar o código (hoje `open_region_home` chama `road.travel_route(..., REFUGE)`) fica para etapa própria.
> 4. **Menu regional.** A UI §66.1 é **override regional do Menu Principal**: dentro das Terras do Ocaso, o **Refúgio do Ocaso substitui o Menu Principal**; fora das Terras do Ocaso permanece o **Menu Principal geral** (entradas Campanha e Aventura). Os mockups de Menu Principal das UI §45.9 e §46.15 valem fora desse override.
> 5. **Coroas.** **Não há teto numérico de carteira de Coroas** atualmente. A decisão do autor de 2026-11-08 (venda sempre credita o valor integral ao vendedor) **permanece válida** sob o GDD v1.7.1. O **Crédito Financeiro Pendente por atingir teto** (GDD §28.14) fica **adiado** até o autor definir o teto. Nenhum valor foi inventado.
>
> Estas decisões não alteram decisões históricas anteriores registradas neste índice.

> **Nota 2026-11-14:** A Crônica I anterior foi pausada em 2026-11-14 para reprojeto futuro. A proposta v0.2 e suas decisões não constituem canon nem compromisso da futura implementação.

## Legado I–V — decisões do autor (2026-11-20)

Registro de autoridade do bloco de Legado. Estas decisões prevalecem sobre a redação histórica do GDD Estrutural v1.6.0 §16 onde houver conflito. Constituem **override autoral** das regras históricas conflitantes do GDD §16; nenhuma outra regra do GDD v1.7.1 ou das Fontes vigentes é alterada.

- **Legado I:** exige somente **Nv.60**. P36, campanha principal e missões principais ou secundárias **não** são requisito.
- **Legados II–V:** exigem o Legado imediatamente anterior concluído + **Nv.60**. Nenhum requisito de P36, campanha, missão principal ou missão secundária.
- **Custos (Coroas):** I = 0; II = 10.000; III = 20.000; IV = 40.000; V = 80.000.
- **Multiplicadores de XP:** I = 1,75×; II = 2,00×; III = 2,25×; IV = 2,50×; V = 2,75×.
- **Ascensão:** retorna o personagem para **Nv.1**.
- **Preservado após o Legado:** mapa, Locais descobertos e Braseiros permanentes.
- **Destino pós-ascensão:** Refúgio do Ocaso (Braseiro permanente já existente em Terras do Ocaso). Não é local novo.
- **Viagem para Local já descoberto:** não há gate de nível. O personagem pode viajar para qualquer Local já descoberto, independentemente do próprio nível ou do nível regional do Local. Vale também após o Legado e o retorno a Nv.1.
- **Gates de entrada de Região:** permanecem inalterados.
- **`_permanent_brazier_rest_gate`:** permanece inalterado.
- **Regra específica das Ruínas do Braseiro:** permanece inalterada.
- **Gates de nível de conteúdo:** continuam válidos quando definidos pelo próprio conteúdo (Missões, Masmorras, atividades, encontros). Não se transformam em gate geográfico do Local.
- **Override do GDD v1.6.0 §16 (decisão do autor, 2026-11-20):** "Primeiro Legado exige Nv.60 + campanha principal concluída" fica substituído por "Legado I exige somente Nv.60". Regras históricas que exigem nível para viajar a Regiões ou Locais já conhecidos após o Legado ficam substituídas por esta seção.

## Fonte Mestra vigente

A implementação do Asterion deve usar como autoridade principal:

**ASTERION — GDD Estrutural v1.7.1 — Fonte Mestra Consolidada**

Arquivo vigente: `ASTERION_GDD_Estrutural_v1.7.1_Fonte_Mestra.md`.
SHA-256 verificado: `2d4ffe0f3310d0f64d54b06fc3038a616dae746f6f8bb61b59666c91645a7db9` (arquivo com quebras de linha Windows CRLF).

Estado oficial:

- a v1.7.1 substitui integralmente a v1.7.0 e versões anteriores; a v1.7.1 troca o sistema de Proficiências pela Especificação de Proficiências de Armas v1.0.0 (§24.2, §24.5, §24.7, §49.8, §55.3); a v1.7.0 substituiu a v1.6.0 e a v1.7.0 acrescenta Proficiências de Equipamento, categorias de proteção corporal, núcleos corporais, Escudo, kits de Origem e pesos de Saque v0.4 (registro no próprio GDD, sem alterar a Baseline Numérica v1.0 fora desses pontos);
- a Baseline Numérica v1.0 está fechada para implementação e testes;
- a v1.4.9 formaliza o fechamento único de `HP Máximo`, `ATQ`, `DEF` e `AGI` estáticos finais em pontos inteiros com `round_half_up`, além de HP atual inteiro; não altera percentuais, curvas, custos, recompensas ou parâmetros de balanceamento;
- a reabertura anterior da conversão absoluta da unidade de XP de inimigo foi encerrada na v1.4.3;
- não existe reabertura numérica vigente na baseline;
- a v1.4.9 formaliza que HP Máximo, ATQ, DEF e AGI estáticos finais fecham uma única vez com `round_half_up` após toda a composição estática; HP atual autoritativo é inteiro e HP legado fracionário é fechado para baixo em fronteira segura;
- Cosméticos possui três categorias oficiais: Aparência, Título e Moldura.

## Contrato Global Complementar — Weapon Metadata

**ASTERION — Contrato Global de Weapon Metadata v1.1.1 FINAL**

Arquivo vigente: `ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.1.1_FINAL.md`.
SHA-256 verificado: `85cc57fdb168bd81cf5366af530bde22aa68d348da98f3b0ca5766757f44feb5` (arquivo com quebras de linha Windows CRLF, mesma convenção da v1.0.0).

A v1.1.1 acrescenta sete formas descritivas (Chakram, Lâmina Dupla, Alabarda, Azagaia, Cetro, Orbe, Escudo), remove `weapon.form.rod`, publica o catálogo-base de 20 templates (§9.9), a identidade de Proficiência de cada arma publicada (§9.10) e a migração dos três drops legados de Terras do Ocaso (§10.5). A família de Proficiência é um registro separado; `weapon_family` continua fora do modelo de metadata.

Este contrato global complementa o GDD Estrutural v1.7.1 e fecha, exclusivamente para armas player-equippable, `weapon_form` descritiva, `handedness`, elegibilidade de slot, tags explícitas de compatibilidade, mapeamento canônico das armas publicadas na tabela §9 e política de legado `EXACT_CANONICAL_MAPPING_OR_UNMAPPED`. `weapon_family` não é conceito canônico e não deve ser armazenado nem inferido.

O contrato não redefine economia regional nem conteúdo regional fora desse escopo, e não substitui nem rebaixa versões regionais vigentes. O GDD Estrutural v1.7.1 permanece a autoridade estrutural superior. Este contrato não é autoridade visual: assets e apresentação visual não determinam metadata mecânica.

A presença de entradas de Altos Cinéreos na tabela de metadata limita-se aos itens nela mapeados. Ela não registra nem substitui a Fonte Regional de Altos Cinéreos nem define seus gates; essa autoridade está registrada como Altos Cinéreos v1.0.1 FINAL na Região 5 abaixo.

A §19.2 de Confins do Véu v1.0.0 FINAL declara metadata explícita para as cinco armas regionais Grau VI usando os vocabulários de forma, handedness, slot e tags funcionais deste contrato. A compatibilidade foi conferida; `weapon_family` permanece não armazenado e não inferível. O conteúdo regional está registrado separadamente na Região 6.


## Proficiências de Armas

> **Sincronização 2026-11-14 (Classes de Armadura):** por decisão do autor, a **Especificação de Classes de Armadura e Proficiência de Armadura v1.0.0** (`docs/specs/ASTERION_ESPECIFICACAO_CLASSES_DE_ARMADURA_v1_0_0.md`) é a autoridade vigente para classes de armadura. Ela **revoga a revogação de 13/11 só para esta parte**: Veste, Leve, Média e Pesada voltam como classe do *template* de Cabeça, Torso, Mãos e Pés, com camada separada de Esquiva/Bloqueio por peça equipada e quatro Proficiências de Armadura (Veste inicial; Leve Nv. 10 / 1.000; Média Nv. 20 / 4.000; Pesada Nv. 30 / 10.000 Coroas) numa aba "Armaduras" do Treinador do Refúgio do Ocaso. Continuam revogados os núcleos corporais por categoria e os kits de Origem; o núcleo por slot, `SlotWeight`, `EconomySW` e os pools de secundários não mudam, e não há peso físico. Os valores foram aprovados como ponto de partida e exigem teste de balanceamento. Registro em código: `src/asterion/domain/regional_equipment.py` e `src/asterion/domain/armor_proficiency.py`.

**ASTERION — Especificação Final de Proficiências de Armas, Catálogo de Armas e Regras de Equipamento v1.0.0**

Arquivo: `docs/specs/ASTERION_ESPECIFICACAO_FINAL_PROFICIENCIAS_EQUIPAMENTO_v1_0_0.md`.
SHA-256 verificado: `babba9f4c0db746fa0fcfbc31165131de2764a03d5535ac0f6de3b4b35a4dc03`.

- Rege famílias de Proficiência, catálogo final de armas, matriz por Classe, Proficiência inicial, Treinador de Armas e equipamento inicial. O GDD v1.7.1 §24.2/§24.7 e o contrato v1.1.1 §9.9/§9.10 estão sincronizados com ela.
- Decisões do autor na implementação (2026-11-13): arma inicial Comum, só a arma (sem armaduras); Treinador no Refúgio do Ocaso; Arma do Contrapeso (martelo 1 mão) = Maça; drops legados de Terras do Ocaso migrados e demais armas sem identidade recusadas no equipar.
- Registro em código: `src/asterion/domain/weapon_proficiency.py`.
- Classes de Armadura (emenda 2026-11-14): a Proficiência de Armas não muda; a Proficiência de Armadura é independente e fica na aba "Armaduras" do mesmo Treinador. Ver a sincronização de 2026-11-14 acima.

## Camada narrativa — Ação × Consequência

**ASTERION — Sistema Narrativo de Ação × Consequência v1.0.0**

Arquivos: `docs/specs/ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md` (contrato) e `docs/specs/ASTERION_HANDOFF_CLAUDE_CODE_NARRATIVA_v1_0_0.md` (handoff).

- Rege os 72 nós de escolha (36 Principais + 36 Secundárias), as memórias de personagem e de NPC, o rapport qualitativo e os ganchos futuros. Contratos ficam fora.
- **Override do GDD v1.6.0 §51.3/§55.1 (decisão do autor, 2026-11-12):** Coop de Missão é exclusivo de Chefes (P5, P6, S6, P12, P18, S18, P24, S24, P30, P36, S30, S36). Objetivos comuns, Elites e encontros roteirizados são Solo. Não reativar Coop de Missão por inferência a partir do GDD.
- As Fontes Regionais continuam autoridade de missões, gates, recompensas e encontros. A camada narrativa não altera XP, Coroas, Materiais, Equipamentos, combate, economia nem `world_state`.
- O catálogo `src/asterion/domain/narrative_choices_catalog.json` é derivado do contrato por `scripts/build_narrative_choice_catalog.py`; não editar à mão.
- `rapport_state` fica `neutral` até o autor definir as transições.
- Falas de reação: `docs/specs/ASTERION_TEXTOS_REACAO_NPCS_v1_0_1.md` (v1.0.0 substituída), subordinado ao contrato (decisão do autor, 2026-11-12). Fala com `choice_id` fora do contrato, ou dita por NPC sem a memória da opção, não é exibida. Pendências de 2026-11-12 resolvidas na v1.0.1 (histórico em `docs/audits/TEXTOS_REACAO_PENDENCIAS_2026-11-12.md`).

## Fechamento de sistema — Contratos Regionais

**ASTERION — Contratos Regionais: Decisões de Design e Balanceamento v1.0.0**

Arquivo: `docs/specs/ASTERION_CONTRATOS_REGIONAIS_DECISOES_FECHADAS_v1_0_0.md`.

Fecha, por decisão do autor (2026-11-13), as lacunas do Documento B de Contratos Regionais: alvo individual por contrato, regra de contagem de Caça (só vitória Manual Solo) e Coleta (só ganho pós-ativação, exclui estoque prévio/prêmio próprio/transferência), regra de Material de recompensa (primeiro Material Básico regional; Coleta paga o próprio Material-alvo), os dois mapeamentos de Material (Ferro da Estrada → Ferro de Fuligem; Coleta das Planícies → Bronze de Marco), recalibração de XP/Coroas para ~25% (faixa 20–30%) do ganho de referência da região, e ausência de teto diário adicional (mantém 3 contratos simultâneos + renovação 24h). Não altera sistemas fora do escopo de Contratos Regionais.

## Exceção autoral — O Despertar dos Flagelos (2026-11-25)

**ASTERION — O Despertar dos Flagelos — Especificação de Implementação V1.0.0**

Arquivo: `docs/specs/ASTERION_DESPERTAR_DOS_FLAGELOS_V1_0_0.md`.
SHA-256 verificado: `04bf379472aca6e8690c7bac3a7426e1ecf760287c0d6c79580f99044a5470e2`.
Decisões técnicas e pendências: `docs/specs/ASTERION_DESPERTAR_DOS_FLAGELOS_DECISOES_TECNICAS.md`.

Por decisão do autor (2026-11-25), O Despertar dos Flagelos é uma **exceção autoral formal ao GDD v1.7.1 §21 e §49.15**. A regra geral de Evento Mundial continua válida; a exceção vale **somente** para o sistema dos Flagelos e **não altera** o Evento Mundial genérico (`domain/world_events.py`) nem A Ruptura do Véu.

- **Persistência:** o Flagelo não expira. Depois de nascer, permanece ativo até ser derrotado. Não existe deadline de 60 minutos.
- **Escalonamento:** próprio, por abandono. Só quando ninguém está em combate com o Flagelo; a cada 15 minutos completos, +8% HP Máximo e +3% ATQ; teto +80% HP e +30% ATQ; DEF e AGI não escalam; não cura; só volta a zero com a morte do Flagelo. Não se aplica `N^0,88` nem o ATQ por participante.
- **Vigor e recompensa:** 0 Vigor. Recompensa-base `0,50×C + 3 materiais básicos regionais + 1 Fragmento/material específico do Flagelo`, com a infraestrutura de recompensa existente.
- **Elegibilidade:** 3 Participation Points. Não exige fases nem as 8 Ações Significativas do Evento Mundial genérico.

Também por decisão do autor (2026-11-25): IA simples e determinística (Preparada elegível → especial elegível de maior prioridade → ataque básico; recarga e alvo respeitados; recalcula se a ação deixou de ser executável); "aplicação significativa de efeito" é só o efeito que o motor de fato aplicou e que mudou o estado do alvo; desempate de ranking pelo instante do backend em que a métrica atingiu o valor; capacidade 200; reentrada 2 min sem limite.

**Especificação final aprovada (2026-11-25):** `docs/specs/ASTERION_O_DESPERTAR_DOS_FLAGELOS_ESPEC_FINAL.md` (SHA-256 `2d4d0e540dba48edb6c8074c6636359acc4d79898de71e1fc3ea6a4bfd7be021`). Fecha o que a V1.0.0 deixava pendente: os 54 equipamentos e as 54 Receitas (IDs literais), raridade/SW/Ofício por slot, metadata das armas, custo de Receita (fórmula global de Crafting × SW + Fragmento do Flagelo), sorteio do equipamento (1/9 por template), descoberta de Receita (25%, uma por morte, sem pity), textos de Bestiário/Códice, lock da Configuração durante o combate e esquiva global nos golpes do Flagelo. Prevalece sobre a V1.0.0 onde as duas diferem. Implementação: `src/asterion/domain/flagelo_catalog.py` e `src/asterion/domain/flagelo_lore.py`.

**Núcleo das Receitas lendárias (decisão do autor, 2026-11-25):** o §14 da especificação final foi corrigido em `c163d05` para refletir esta decisão (a versão anterior, com Núcleo próprio do Flagelo, está superada). Não existe "Núcleo do Flagelo". As Receitas lendárias usam o Núcleo de Masmorra já existente da 2ª Masmorra da Região (Galerias do Vigia, Nó Antigo, Observatório Afundado, Cisterna de Transferência, Bastilha Profunda, Câmara das Contradições), na quantidade 1 × SW; Núcleos de Chefe de Campanha não entram. Detalhe na decisão #48 de `docs/specs/ASTERION_DESPERTAR_DOS_FLAGELOS_DECISOES_TECNICAS.md`.

**Fechamentos da V1 (decisão do autor, 2026-11-25):** (1) **Bind:** os 54 equipamentos regionais do Flagelo são **Vinculados ao Adquirir**, pelo mecanismo global de Bind (sem sistema paralelo); (2) **Outros PvE equivalentes:** na V1 não existem; a contribuição é exatamente Caçada +1, Caçada em Grupo +1 por participante elegível, Desbravar +1, Contrato Regional +2, Missão Regional +4 e Masmorra +6, e nenhuma outra atividade concede pontos; (3) **Balanceamento:** kits e atributos baseline dos seis Flagelos permanecem como estão; a medição determinística sobre o motor real está em `docs/balance/FLAGELOS_BALANCEAMENTO_V1.md` (sem buff/nerf automático). Detalhe nas decisões #39, #50 e #51 de `docs/specs/ASTERION_DESPERTAR_DOS_FLAGELOS_DECISOES_TECNICAS.md`. A especificação final não foi editada (o SHA-256 acima continua válido).

**Pendente:** imagens dos seis Flagelos (a cargo do autor).

## Fontes regionais vigentes

As Fontes Regionais FINAL possuem o mesmo nível hierárquico entre si dentro de seus respectivos escopos. Todas permanecem subordinadas à Fonte Mestra v1.7.1 para sistemas globais e não podem sobrescrever conteúdo de outra Região.

### Região 1 — Terras do Ocaso · Nv.1–10

**ASTERION — Conteúdo: Terras do Ocaso v1.0.18 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_FINAL.md`.

> **Sincronização 2026-11-14:** o autor adotou a v1.0.18 FINAL no lugar da v1.0.17 FINAL, que passa a **histórica** (preservada só como registro, sem autoridade). A v1.0.18 reestrutura a navegação da Região: Refúgio do Ocaso como hub, Locais revelados pela ação Explorar, Travessia dos Braseiros oculta, nível do inimigo pelo Local, XP de descoberta de Local, Câmara do Poente com dois textos de entrada e remoção de travas de nível de Missão. Os pontos que contrariam a Fonte Mestra só valem pelo override registrado abaixo. A `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_PROPOSTA.md` está **superada** pela FINAL: não é autoridade e não deve ser usada.

> **Histórico — v1.0.17 FINAL (2026-11-12):** o autor adotou a v1.0.17 no lugar da v1.0.16. A única mudança é a duração de `2T` da Barreira da **Égide do Selo** (mantém 8% do HP Máximo, CD4 e máximo 2 usos). O código já usava `2T` (`domain/road.py`, `egide_selo`); nenhum outro conteúdo ou valor regional muda.

A v1.0.16 substituiu integralmente a v1.0.15 como autoridade regional vigente. Preserva o conteúdo e os valores anteriores e fecha exclusivamente os pools temáticos de Material Básico do **Corvo de Fuligem**, **Alfa Cinéreo** e **Peregrino Calcinado**. Os pesos escolhem somente a identidade de cada unidade depois que chance e quantidade globais do contexto já foram resolvidas; não alteram Catalisadores, XP, Coroas, Equipamentos, Caçadas, Rondas, Desbravar ou qualquer outra regra econômica.

#### Override regional — Terras do Ocaso v1.0.18

> **Override regional — Terras do Ocaso v1.0.18.** Por decisão do autor (2026-11-14), a Fonte Regional Terras do Ocaso v1.0.18 prevalece sobre a Fonte Mestra (`ASTERION_GDD_Estrutural_v1.7.1_Fonte_Mestra.md`) apenas nos pontos abaixo e apenas para a Região 1 (Terras do Ocaso). Nada além disto é sobrescrito. Detalhe na Fonte Regional, seção 33.14.
>
> 1. **Desbravar — recarga e limite por hora (GDD §18.3 e §49.15, linha 4208).** Não existem recarga de 5 min nem limite de 6 tentativas por Local por 60 min nas Terras do Ocaso. Existe limite técnico anti-spam: intervalo mínimo de 3 s entre tentativas por personagem e 1 tentativa em resolução por vez. Ele não é regra econômica e não altera recompensa. O Vigor continua pago só quando o resultado paga economia.
> 2. **Explorar e Desbravar — "Local conectado", "não ignora gates", "não ignora requisitos de nível", "não teleporta" (GDD §18.3, linha 1123).** Nas Terras do Ocaso, a revelação de Local é feita pela ação **Explorar no Refúgio do Ocaso**: ação própria, 0 Vigor, anti-spam de 3 s. Cada clique revela um Local ainda não descoberto da Região (Charneca, Bosque, Ruínas e Câmara do Poente), por sorteio uniforme, sem exigir conexão e sem verificar nível. "Local novo" não é resultado de Desbravar. **Nenhum Local é liberado por Missão:** Missão pode exigir o Local descoberto, não o revela. A revelação não concede Braseiro.
> 3. **Hub e "não existe exploração remota" (GDD §18.3, linha 1049).** O Refúgio do Ocaso é o hub da Região: liga a todos os Locais descobertos e todos voltam a ele; não há ligação Local–Local. Toda ida a um Local parte do Refúgio. Caçar, no Refúgio, escolhe o Local descoberto. Desbravar e Ronda atuam sobre o Local atual, o que preserva "sem exploração remota". Ida e volta custam 0 Vigor, 0 Coroas, 0 XP, fora de combate. A Travessia dos Braseiros fica oculta na Região, sem alterar a regra global. Braseiros seguem como checkpoint e recovery, com recovery no Braseiro do próprio Local (Câmara do Poente, sem Braseiro: Refúgio do Ocaso). Ao abrir o jogo, o personagem aparece onde estava.
> 4. **Faixas de Masmorra (GDD §49.15, linha 4182).** As faixas Nv.4–7 (Cripta do Ocaso) e Nv.8–10 (Galerias do Vigia) são recomendação de apresentação. Permanece um nível mínimo individual de entrada (GDD linha 1341): Cripta do Ocaso Nv.4, Galerias do Vigia Nv.8, em Solo e em Grupo.
> 5. **Meta de Exploração e "descoberta 100%" (GDD §49.7).** Nas Terras do Ocaso, a Exploração única fica entre 7,70% (piso, 7.529 XP) e 8,43% (teto, 8.242 XP) do requisito Nv.1→11 (97.800 XP), dentro da meta de 7–9%. O XP de descoberta de Local é `FixedPercentXP(min(nível de referência do Local, nível do personagem), 2,5%)`, só por Explorar, uma vez por Local; isto substitui, para descoberta de Local, a regra de 100% sem fator por nível. Referências: Charneca 4, Bosque 6, Ruínas 9, Câmara do Poente 10.
> 6. **Missões Principais de alto nível (GDD linha 849).** Nas Terras do Ocaso, Missões Principais e Secundárias não têm requisito de nível; dependem só do encadeamento de Missões. A linha 849 permanece válida nos demais contextos (por exemplo, Ascensão). O gate de nível da saída da Região (GDD §25) **não** é alterado.
> 7. **Nível do inimigo e `unlock_level`.** Em **Solo**, o nível do inimigo é o `max_enemy_level` do Local/região e não escala com o jogador; o `unlock_level` das criaturas não se aplica (a linha 899 já delega o Solo à Fonte Regional). Em **Grupo**, o nível do inimigo também é o `max_enemy_level` do Local. **Conflito:** a linha 899 define, em Grupo, `encounter_reference_level` = maior nível atual entre os participantes válidos e `enemy_level = min(encounter_reference_level, max_enemy_level da criatura)`, congelado no `encounter_id`. Este item sobrescreve essa regra de nível. O `unlock_level` continua como requisito individual de cada membro em Grupo (isto já é a regra da linha 899 e não conflita). Se nenhuma criatura do Local é elegível para todos os membros, a Caçada não abre e a interface cita **todos** os membros que não cumprem o `unlock_level`. Reescrita necessária na consolidação do GDD: a regra `enemy_level = min(player_level, max_enemy_level)` não está no GDD (nem na v1.6.0 nem na v1.7.1); vem das Fontes Regionais v1.0.11 a v1.0.17 e deste índice (conferido em 2026-11-14). Motivo registrado: coerência com o estilo soulslike e carona coberta pelo `unlock_level` individual.
> 8. **PowerlevelFactor em Coop de Chefe.** O PowerlevelFactor (GDD linha 3795: `100/70/45/20/5%` para diferença `0-10 / 11-15 / 16-20 / 21-30 / 31+`) se aplica também à XP fixa de Missão em Coop de Chefe (P5, P6, S6). O GDD aplica o fator só à XP de inimigo (linha 3822) e não o define para XP fixa de Missão (linhas 3840-3842); esta Fonte Regional o define para P5, P6 e S6 (conferido em 2026-11-14, decisão do autor: manter como override).
> 9. **Ronda em Grupo.** A vitória manual válida em Grupo libera a Ronda do Local para todos os membros que participaram da vitória.

Não são override (conferido contra a Fonte Mestra): BKP de investigação Desbravar e de Habitat como marco único por criatura e por Local; S4 e S5 em Grupo; recovery por Local e Travessia oculta na Região (a regra global da Travessia e do Braseiro permanece). O texto de trabalho está em `docs/specs/RASCUNHO_OVERRIDE_FONTE_MESTRA_TDO_v1.0.18.md`. Os 9 itens devem entrar na próxima revisão do GDD.

### Região 2 — Vales dos Enforcados · Nv.11–20

**Vales dos Enforcados v1.0.6 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_VALES_DOS_ENFORCADOS_v1.0.6_FINAL.md`.

A v1.0.6 sucede a v1.0.5 exclusivamente para fechar o perfil numérico do encontro roteirizado da Etapa 7 de S12 — Os Nomes Presos à Madeira. Não altera economia, progressão, narrativa regional, demais criaturas, pools, Caçada, Ronda, Masmorras ou recompensas regionais.

### Região 3 — Planícies de Nareth · Nv.21–30

**Planícies de Nareth v1.0.2 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_PLANICIES_DE_NARETH_v1.0.2_FINAL.md`.

A v1.0.2 sucede a v1.0.1 exclusivamente para fechar em 2T as durações das nove Barreiras inimigas publicadas. Preserva o mapeamento de Material Básico por criatura em Caçada/Ronda definido na v1.0.1 e todo o restante do conteúdo regional.

### Região 4 — Várzeas Carmesins · Nv.31–40

**Várzeas Carmesins v1.0.3 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.3_FINAL.md`.

A v1.0.3 sucede a v1.0.2 exclusivamente para esclarecer que sucesso ou falha/omissão na ação contextual dos Reservatórios Operacionais não altera a potência publicada de Transferência Externa (`165% ATQ`) nem cria consequências numéricas ou econômicas; cada Reservatório usado é consumido e não retorna, até o máximo publicado de três. Preserva todas as durações regionais de Barreira em `2T` e não cria default ou sistema universal. Todo o restante do conteúdo regional permanece inalterado. A Região cobre Nv.31–40 com saída para Nv.41 e define Locais, P19–P24, S19–S24, NPCs, Materiais Grau IV, criaturas, pools, economia, Crafting, Bestiário, Códice, Feitos e sistemas regionais, subordinados às regras globais da Fonte Mestra.

### Região 5 — Altos Cinéreos · Nv.41–50

**Altos Cinéreos v1.0.1 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_ALTOS_CINEREOS_v1.0.1_FINAL.md`.

A v1.0.1 FINAL harmoniza acesso persistente, navegação e atividades por Local. Escarpa exige P24 concluída + Nv.41 e registra acesso na etapa 1 de P25; Abrigo é descoberto na etapa 6 de P25. Pontes, Pedreiras e Bastilha abrem, respectivamente, pela ativação válida de P26 após P25 concluída + Nv.43, P27 após P26 concluída + Nv.45 e P28 após P27 concluída + Nv.47. Coração abre na etapa 7 de P29; Nv.50 continua exigido para iniciar P30. Caçada e Desbravar só são habilitados no Local correspondente após a conclusão de sua missão; Ronda exige também a primeira vitória manual válida posterior em Caçada no mesmo Local. S25 examina a ponte pelo lado da Escarpa sem antecipar acesso às Pontes. A revisão preserva os demais valores e conteúdos aprovados e não cria mecânica global.

Quando uma Fonte Regional especificar conteúdo dentro de parâmetros sistêmicos da Fonte Mestra, ambas devem ser aplicadas em conjunto. Em conflito estrutural ou numérico global, a Fonte Mestra prevalece; em conteúdo regional fechado dentro do próprio escopo, a revisão Regional vigente prevalece sobre rascunhos ou versões regionais anteriores.

### Região 6 — Confins do Véu · Nv.51–60

**Confins do Véu v1.0.0 FINAL — FINAL_APPROVED**

Arquivo vigente: `ASTERION_CONTEUDO_CONFINS_DO_VEU_v1.0.0_FINAL.md`.
SHA-256 integral verificado: `c86a0208888d14bbd653cda6174956df89b2233304dcca523d878b5b42a102fc`.

A aprovação de conteúdo regional C foi confirmada em 2026-10-18. Para sistemas, fórmulas e regras globais, prevalece o GDD Estrutural v1.7.1; para Lore, NPCs, identidades e limites, prevalece a Bíblia Canônica Consolidada v4.0.7 (substitui a v3.0 FINAL); esta Fonte define as decisões regionais C aprovadas, sem sobrepor aquelas autoridades. A §19.2 está sincronizada com o Contrato Global de Weapon Metadata v1.0.0 FINAL, registrado acima.

**Handoff à Engenharia:** autorizado após o registro desta Fonte FINAL e do Contrato Global de Weapon Metadata no índice. O handoff não significa que o conteúdo tenha sido implementado.

## Fonte Visual/UI

A apresentação player-facing deve seguir:

**ASTERION — Consolidação de Visual & UI v1.6.2 — sincronizada com Fonte Mestra v1.7.1 + Terras do Ocaso v1.0.18 + Vales dos Enforcados v1.0.6**

Arquivo vigente: `ASTERION_UI_DECISOES_2026-11-16_FINAL_SYNC_v1.6.2_TDO_v1.0.18_VALES_v1.0.6.md`.

> **Atualização 2026-11-16:** a v1.6.2 é cópia versionada da v1.6.1 com a seção 66.1 reescrita por decisão do autor. Nas Terras do Ocaso, o Refúgio passa a tela principal e recebe as ações regionais e atalhos globais aprovados; retornos regionais e fim de Missão levam ao Refúgio. O personagem continua reabrindo no Local atual. Após o Prólogo, fica fisicamente no Refúgio; a etapa 1 de P1 conduz à Estrada. A seção 66.1 prevalece sobre indicações conflitantes das seções 45.9 e 46.2. Campanha/Aventura não aparecem nas Terras do Ocaso e permanecem nas demais regiões. A v1.6.1 e a v1.6.0 passam a históricas.

Ela define nomenclatura, texto, estrutura de telas, navegação, estados visuais e UX do Bot do Telegram. É subordinada à Fonte Mestra para regras mecânicas/números e à Fonte Regional para conteúdo regional oficial.

Exemplos de mockup não criam regra mecânica ou conteúdo canônico quando a autoridade correspondente já definir outro valor/estado.

## Fontes complementares de Lore e Direção Visual

As Fontes abaixo complementam as autoridades estrutural, regional e de Visual/UI. Elas não podem sobrescrever regra mecânica, conteúdo regional FINAL ou apresentação player-facing já fechada em autoridade superior.

### Lore canônica complementar

**Arquivo vigente:** `ASTERION_LORE_BIBLE_CANON_v1.2.md`

A v1.2 substitui a v1.1. Preserva a Lore consolidada e atualiza o fundamento fisiológico das cinco Raças para anatomia racial v2.0, mantendo nomes, mecânicas, compatibilidade biológica e núcleos narrativos. Quando um fato já estiver definido em Fonte Mestra ou Regional vigente, essas Fontes superiores prevalecem.

### Direção visual especializada — personagens humanoides

**Arquivo vigente:** `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md`

A v2.0 substitui a v1.5 para toda produção/refação futura. Mantém Classes, Caminhos, NPCs e identidade individual, mas torna as cinco Raças imediatamente distinguíveis por anatomia/silhueta e atualiza as dez identidades canônicas das duas primeiras Regiões para a nova fisiologia.

### Direção visual especializada — Aparência Errante das Cinzas

**Arquivo vigente:** `ASTERION_APARENCIA_ERRANTE_DAS_CINZAS_FONTE_VISUAL_v1.3.md`

A v1.3 é a autoridade visual específica da Aparência regional **Errante das Cinzas**. Define identidade de coleção, variação de poses/olhares, famílias de armamento permitidas no escopo cosmético, materiais, fundos e QA do lote de 60 assets. Em seu escopo, prevalece sobre instruções genéricas da Matriz de Produção quando houver divergência, sem criar ou alterar mecânica, proficiência, inventário, Classe, Raça ou conteúdo regional.

### Direção visual especializada — criaturas e biomas

**Arquivo vigente:** `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md`

Define ecologia visual, anatomia, silhueta, materiais, escala, habitats, Variantes, Elites, criaturas de Masmorra e Chefes. Nas Regiões 1–2, mecânica e conteúdo continuam pertencendo às Fontes Regionais FINAL.

A v1.1 substitui a v1.0 para produção futura e acrescenta o dossiê visual canônico do **Guardião do Último Rastro**, preservando ambiguidade de identidade/origem e diferenciação obrigatória de Peregrino Calcinado, Custódio Sem Rosto, Guardião das Lápides, O Sem-Nome e Vigia Partido.

### Direção visual especializada — ambientes

**Arquivo:** `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md`

Define identidade ambiental, arquitetura, materiais, função histórica, Locais, hubs, clímax, Masmorras, progressão visual e limites de spoiler.

### Especificação técnica de geração

**Arquivo:** `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md`

Define **como renderizar** o conteúdo já autorizado: canvas, proporção, pixel art, materiais, anatomia técnica, integridade de armas/focos, estados de pose, transparência, pós-processamento, nomenclatura e QA. Não cria Lore nem substitui as Bíblias especializadas.

### Controle operacional de produção

**Arquivo:** `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md`

Documento de produção, não Fonte de cânone. A v2.0 substitui a v1.3 e refaz as 10 âncoras raciais para anatomia v2.0, mantendo as 60 combinações Raça × Classe, armas, poses e fundos como estrutura operacional. Qualquer linha que conflite com Fonte autoritativa deve ser corrigida na Matriz, nunca na Fonte superior.

### Padrão global de Aparências temáticas

**Arquivo vigente:** `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md`

A v1.1 substitui a v1.0 e torna a anatomia racial v2.0 obrigatória em todas as Aparências temáticas.

### Direção visual especializada — Aparência Sobrevivente dos Vales

**Arquivo vigente:** `ASTERION_APARENCIA_SOBREVIVENTE_DOS_VALES_FONTE_VISUAL_v1.1.md`

A v1.1 substitui a v1.0 para incorporar anatomia racial v2.0 e referências documentais atualizadas; neste contêiner v2.0.1 também foi corrigido um carryover editorial indevido de exceções de armamento de `Errante das Cinzas`. `Sobrevivente dos Vales` segue as assinaturas globais de Classe; identidade regional e fundos permanecem.

### Guia operacional Raça × Classe

**Arquivo vigente:** `ASTERION_GUI_GERACAO_SKINS_RACA_CLASSE_v1.3.md`

A v1.3 substitui a v1.2 e exige que Classe e equipamento acomodem fisicamente chifres/orelhas/proporções raciais.

### Bundle Visual de recuperação

**Arquivo vigente:** `ASTERION_BUNDLE_VISUAL_CHATGPT_v2.0.md`

Espelho operacional dos documentos visuais vigentes para uso em Projeto ChatGPT. Não cria autoridade nova; em conflito prevalecem os documentos individuais acima.

### Contêiner visual do Projeto ChatGPT

**Arquivo vigente:** `ASTERION_CONSOLIDADO_RACAS_E_VISUAL_v2.0.2_PROJETO_FINAL.md`

Contêiner documental para economizar slots de Fontes do Projeto. Incorpora o índice de autoridade e as Fontes visuais especializadas, preservando a precedência interna de cada documento. Não cria mecânica, Lore ou conteúdo regional novo.

## Decisão visual vigente — legibilidade racial e anatomia v2.0

Para assets de seleção e personagens jogáveis, a identidade racial não pode depender apenas de postura, roupa ou texto. As cinco Raças possuem famílias fenotípicas recorrentes, com exceções possíveis por descendência mista. Assets de seleção usam o centro fenotípico; skins Raça × Classe preservam ao menos dois marcadores raciais fortes.

Fundos de seleção racial passam a usar motivos de herança próprios; fundos Raça × Classe combinam herança racial + função da Classe + adaptação regional quando aplicável. O mesmo fundo genérico de ruínas para todo o catálogo deve ser rejeitado.

## Regra para produção visual

Antes de gerar, refazer ou aprovar um asset:

1. localizar a entidade e o conteúdo na Fonte Mestra/Regional;
2. aplicar a Lore canônica e o gate de spoiler correspondente;
3. aplicar a Bíblia visual especializada do assunto;
4. aplicar a Fonte Visual/UI quando o asset pertencer a uma tela específica;
5. aplicar a Bíblia Técnica de Geração;
6. aplicar a Matriz de Produção quando houver âncora/linha correspondente;
7. reprovar assets com anatomia quebrada, objeto impossível, spoiler ou identidade visual contraditória mesmo que a atmosfera geral esteja boa;
8. não usar documentos antigos de prompts como autoridade quando divergirem das Fontes vigentes.

## Decisão visual aprovada em 06/10/2026 — arma-assinatura de Classe

Para as 60 Aparências padrão Raça × Classe, **toda skin deve exibir a arma-assinatura da Classe em leitura imediata**: Sentinela = arma de uma mão + escudo; Errante = duas armas curtas, preferencialmente uma em cada mão; Vigia = arco/besta; Tecelão = arma-foco de Trama; Oráculo = arma-foco simbólica/oracular; Luminar = cajado/bastão de combate-foco.

Estados `mãos livres`, Repouso ou Contemplação podem mudar a posição do armamento, mas não eliminar a assinatura. Tecelão, Oráculo e Luminar devem permanecer distinguíveis também pela linguagem formal de seus focos: técnico/Trama, simbólico/possibilidades e centrado/Luz, respectivamente.

As seis Classes da mesma Raça não podem reutilizar o mesmo traje-base como solução padrão. A diferenciação deve envolver arquitetura do torso, distribuição de equipamento, arma-assinatura e postura. Fundos monumentais genéricos repetidos — castelos, aquedutos, bandeiras e skylines épicos — devem ser rejeitados quando não vierem de fonte específica.

Esta decisão é **direção visual**, não regra mecânica de equipamento, proficiência, dano, inventário ou loadout.

## Decisão adicional aprovada no projeto

Em 20/09/2026 foi aprovada explicitamente a seguinte regra de estado inicial, necessária antes da primeira exposição de Vigor na HUD:

**Personagem novo inicia com 100 / 100 Vigor.**

Esta é uma decisão aprovada pelo projeto e deve ser tratada como autoritativa para implementação até sua incorporação em futura consolidação textual da Fonte Mestra. Ela não altera:

- Vigor Máximo = 100;
- regeneração +1 a cada 14m24s;
- reset das 06:00 não reabastece;
- custos de Vigor já definidos;
- regra de que Braseiro permanente não restaura Vigor.

## Decisão aprovada pelo autor — Gênero na criação de personagem (2026-11-13, reconfirmada em 2026-11-19)

O fluxo canônico de criação de personagem é:

**Nome → Gênero → Raça → Classe → Confirmação Final → Prólogo jogável "Cinzas na Estrada".**

- Gênero (Masculino ou Feminino) é uma escolha **obrigatória** da criação, entre Nome e Raça, e é revisável na Confirmação Final.
- A Fonte Mestra v1.7.1 e a Consolidação de Visual & UI v1.6.2 descrevem o fluxo sem Gênero. Nesse ponto específico, esta decisão as sobrepõe. Elas devem incorporá-la na próxima revisão.
- A especificação operacional do fluxo é `docs/specs/CHARACTER_CREATION_UI.md` (§45).
- **Não é válida** qualquer decisão anterior de remover Gênero da criação. Nenhuma implementação deve removê-lo.
- Esta decisão não define efeito mecânico de Gênero. Não altera Raça, Classe, números nem balanceamento.

## Regra para implementação

Antes de implementar um sistema:

1. localizar a regra estrutural/mecânica na Fonte Mestra;
2. localizar o conteúdo correspondente na Fonte Regional vigente quando for regional;
3. localizar a apresentação correspondente na Fonte Visual/UI;
4. aplicar decisões adicionais explicitamente aprovadas e registradas neste documento;
5. não inventar comportamento para preencher lacunas;
6. registrar conflito real em vez de escolher silenciosamente uma interpretação;
7. preservar IDs estáveis, idempotência, estado autoritativo, transações e `ruleset_version` onde aplicável.

## Snapshot de implementação histórico — criação e primeiro combate

As seções de implementação abaixo foram preservadas como registro operacional e não substituem as Fontes oficiais vigentes nem o snapshot mais recente de `REPASSE_TECNICO.md`.

O fluxo implementado permanece:

`/start → nome → raça → classe → confirmação final → prólogo Cinzas na Estrada → Cão Cinéreo`

O primeiro encontro continua com:

- Cão Cinéreo Nv.1, Comum, Predador;
- 244 HP / 50 ATQ / 45 DEF / 56 AGI;
- tutorial Atacar/Defender/primeira Arte;
- 320 XP fixos;
- 0 Vigor consumido;
- sem Saque/Coroas/Materiais;
- suppress do bônus adicional de 1% de primeira observação nesta ocorrência.

A implementação histórica do combate foi instanciada sob `gdd-1.4.2-baseline-1.0`. Patches não devem reescrever silenciosamente combates ativos. Combates antigos devem continuar reprodutíveis no ruleset armazenado; novas instâncias/transições seguras devem adotar a Fonte Mestra vigente.

## Snapshot histórico — primeiro Braseiro e fim do Prólogo

Após a vitória do tutorial:

- o personagem chega ao **Braseiro da Estrada**, primeiro Braseiro permanente das Terras do Ocaso;
- ele já aparece como **Descoberto**; não existe `[Ativar Braseiro]` nesse passo;
- `[Descansar]` restaura HP a 100% e remove estados comuns de combate;
- Braseiro permanente não restaura Vigor;
- não existe segunda tela de “Braseiro ativado”;
- concluir esse passo encerra o Prólogo;
- registrar idempotentemente o Feito **Cinzas na Estrada** (sem cosmético);
- iniciar automaticamente a Missão Principal **P1 — Vozes na Estrada**;
- abrir diretamente o Menu Principal;
- no primeiro Menu, o personagem está em **Terras do Ocaso · Estrada das Cinzas**, Nv.1, com **320 / 4.800 XP**;
- por decisão aprovada do projeto, Vigor inicial é **100 / 100**.

A especificação focada histórica da implementação desse limite está em `docs/specs/PROLOGUE_BRAZIER_MENU_V1.4.3_TDO_V1.0.1.md`. Ela permanece como registro do PR que implementou o bloco e não substitui as Fontes vigentes para conteúdo posterior.

## Snapshot histórico — P1 Vozes na Estrada

A Fonte Regional v1.0.13 e a Fonte Visual/UI de 2026-10-04 eram as referências vigentes para P1 naquele momento. O fluxo abaixo é uma nota de implementação preservada como snapshot histórico e não substitui as autoridades atuais definidas acima.

O fluxo autoritativo é:

`Menu pós-Prólogo → Seguir pela Estrada → Pegadas na Cinza → Sulcos Recentes → Cão Cinéreo roteirizado → Refúgio do Ocaso → Alda Veyr → Oren Cal → Braseiro do Refúgio → conclusão de P1`.

Regras essenciais para a próxima implementação:

- os dois sinais são fixos e persistentes;
- o encontro da Etapa 3 usa **Cão Cinéreo Nv.1, Comum, Solo, sem Variante**, fora do pool normal de Caçada;
- o combate usa HUD normal, sem máscara pedagógica;
- esse encontro concede `0 XP` de inimigo, `0 XP` adicional de primeira observação e nenhuma recompensa econômica própria;
- derrota retorna ao **Braseiro da Estrada**, mantém P1 na Etapa 3 e permite nova tentativa com novo encontro;
- reconnect de tentativa ainda ativa retoma o mesmo encontro;
- Refúgio, Alda, Oren e Braseiro do Refúgio são registrados na ordem definida pela Fonte Regional;
- `[Ativar Braseiro]` não equivale a `[Descansar]` e não restaura HP;
- concluir P1 concede uma única vez `2.400 XP`, `120 Coroas`, `1 Ferro de Fuligem` vinculado e `1 Couro Escoriado` vinculado;
- no mesmo commit de conclusão são liberados Caçada Manual e Desbravar na Estrada; Ronda continua dependente da primeira vitória manual válida posterior;
- no fluxo normal, o Menu pós-P1 fica em **Refúgio do Ocaso**, Nv.1, `2.720 / 4.800 XP`, sem reapresentar P1 como ativa;
- a UI separa detalhe oficial da Missão de telas contextuais e usa `[Ver Objetivo]` apenas como navegação sem mutação;
- callbacks antigos, reconnect e outro dispositivo sempre reconstroem a partir do estado persistido.

A implementação jogável de P1 foi integrada ao `main` no commit squash `bc45b2746e4cf5666134d39291fa32a6cdac524e` (PR #10). A especificação técnica de P1 permanece como registro histórico em `docs/specs/P1_VOZES_NA_ESTRADA_V1.4.3_TDO_V1.0.2.md`.

## Próximo bloco aprovado — snapshot histórico

O plano abaixo descreve uma etapa anterior do desenvolvimento. Use `REPASSE_TECNICO.md` para o estado de implementação e próximos passos registrados mais recentemente.

O próximo bloco de produção parte do estado pós-P1 e implementa **Travessia Refúgio ↔ Estrada + Caçada Manual Solo + familiaridade da Ronda + Desbravar da Estrada**, sem iniciar ainda a execução automática da Ronda, Caçada em Grupo, P2/S1 ou outro Local.

A especificação técnica focada está em `docs/specs/ROAD_HUNT_EXPLORE_V1.4.3_TDO_V1.0.2.md`.

Para este bloco, esse documento também registra as decisões adicionais já aprovadas e ainda pendentes de consolidação textual nas Fontes: materialização global de Equipamento/Runa de Saque; identidade regional de Materiais; textos/registro de Desbravar; UI pós-combate/exploração; IA PvE normal; Ação Preparada; e pacotes Hemorrágico/Venenoso. Essas decisões são autoridade de implementação **somente no escopo explicitamente fechado pela especificação** e não autorizam reabrir balanceamento ou extrapolar para conteúdo não coberto.

---

## Nota de escopo do pacote essencial

Este consolidado é suficiente como autoridade de **design, Lore, direção visual e produção de assets** quando usado com Fonte Mestra, Fontes Regionais e Visual/UI do pacote essencial. Referências históricas a `REPASSE_TECNICO.md` e referências de implementação a `docs/specs/OPTIONAL_SIDE_QUEST_BOSSES_V2.md` permanecem externas: elas não foram fornecidas neste conjunto e não são reconstruídas por inferência. Para tarefas estritamente de estado de código/implementação ou da regra técnica específica de Chefe opcional de S18, anexar a especificação correspondente.

---

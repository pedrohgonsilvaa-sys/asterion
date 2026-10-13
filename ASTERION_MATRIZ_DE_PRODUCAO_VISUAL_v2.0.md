# ASTERION — MATRIZ DE PRODUÇÃO VISUAL v2.0

**Data de consolidação:** 2026-10-12  
**Escopo:** controle editorial de identidade fenotípica, diversidade, continuidade visual, pose, variação e fundos para seleção racial e produção Raça × Classe  
**Estado:** documento operacional de produção — subordinado às Fontes canônicas e à Bíblia Visual de Personagens v2.0

> A v1.3 substitui a v1.2. Preserva integralmente a distribuição fenotípica, poses e fundos aprovados e fecha **arma-assinatura de Classe obrigatória para as 60 Aparências padrão**: Sentinela com escudo + arma, Errante com par de lâminas curtas, Vigia com arco/besta, Tecelão com arma-foco de Trama, Oráculo com arma-foco simbólica/oracular e Luminar com cajado/bastão de combate-foco. A decisão é visual/editorial e não cria equipamento mecânico.

> **A v2.0 substitui a v1.3 para toda produção/refação de personagem.** Preserva IDs, Classes, armas, poses e fundos, mas substitui as âncoras raciais anteriores pela anatomia v2.0. Assets antigos devem ser tratados como escala/composição, não como anatomia racial autoritativa.

---

# 1. FUNÇÃO E ESCOPO DO LOTE

Esta Matriz controla dois conjuntos relacionados:

- **10 âncoras de seleção racial:** 5 Raças × 2 apresentações;
- **60 âncoras Raça × Classe:** 5 Raças × 6 Classes × 2 apresentações.

As 60 âncoras Raça × Classe podem originar mais de uma Aparência. Para a frente inicial:

- Aparência padrão: 60 imagens;
- Errante das Cinzas: 60 imagens;
- seleção racial: 10 imagens;
- total planejado: **130 imagens**.

Asterion permite qualquer gênero em seu cânone; masculino/feminino são apenas as duas apresentações do lote visual inicial.

Os 10 representantes raciais são **âncoras de leitura**, não “o rosto oficial” de toda a Raça.

---

# 2. REGRA DE CONTINUIDADE ENTRE APARÊNCIAS

Quando a Aparência padrão e `Errante das Cinzas` representarem a mesma âncora Raça × Classe, preservar:

- rosto e estrutura facial;
- tom/subtom de pele;
- idade aparente;
- textura e cor principal do cabelo;
- constituição corporal;
- leitura racial;
- gênero/apresentação;
- sinais individuais importantes.

Pode variar entre Aparências:

- roupa/armadura aparente;
- reparos;
- acessórios;
- grau de fuligem/cinza;
- acabamento;
- estado de pose;
- estado visível da arma/foco, desde que não gere leitura mecânica enganosa.

---

# 3. IDENTIDADE DE “ERRANTE DAS CINZAS” PARA PRODUÇÃO

A Fonte Regional define `Errante das Cinzas` como Aparência conquistada pelo Feito **Entre Aquilo que Caça**. Para produção:

- vestuário de estrada funcional e muito usado;
- cinza e fuligem físicas;
- couro ressecado;
- metal fosco e reparado;
- tecido seco e desbotado;
- proteção adaptada à Classe;
- nenhuma transformação corporal pela Região;
- nenhum poder de cinzas inventado.

Adaptação de Classe:

- **Sentinela:** casaco/armadura de estrada reforçada, placas parciais, base firme; escudo opcional.
- **Errante:** camadas mais leves, manto/casaco dividido, bainhas e cintas funcionais, pernas livres.
- **Vigia:** proteção leve/média, capa curta controlável, aljava/sistema de munição quando aplicável.
- **Tecelão:** camadas que permitam precisão, braceletes/luvas/instrumentos técnicos; sem “magia de cinzas”.
- **Oráculo:** roupa de viagem prática com placas, fios ou marcadores discretos quando usados; sem cartomante teatral.
- **Luminar:** proteção funcional e vestuário marcado pela fuligem; Luz apenas quando a Classe/pose pedir, nunca halo ou santidade.

---

# 4. NOMENCLATURA

Âncora de seleção racial:

```text
RAC-<RACA>-<M/F>
```

Arquivo:

```text
raca_<raca>_<masculino|feminino>.png
```

Âncora Raça × Classe:

```text
PV-<RACA>-<CLASSE>-<M/F>
```

Arquivos:

```text
aparencia_padrao_<raca>_<classe>_<masculino|feminino>.png
errante_das_cinzas/errante_das_cinzas_<classe>_<raca>_<masculino|feminino>.png
```

Os nomes são de produção; IDs de backend permanecem responsabilidade de Implementação.

---

# 5. MATRIZ DAS 10 ÂNCORAS DE SELEÇÃO RACIAL

| ID | Raça | Apresentação | Idade | Pele | Cabelo | Constituição | Anatomia racial obrigatória | Pose | Fundo de herança |
|---|---|---|---|---|---|---|---|---|---|
| RAC-REM-M | Remanescente | Masculina | 34–40 | negra retinta | crespo preto, curto | média funcional | anatomia humana; nenhum apêndice racial; rosto individual forte | Contemplação | reconstrução em camadas |
| RAC-REM-F | Remanescente | Feminina | 38–45 | castanha média quente | ondulado/cacheado castanho-escuro | média funcional | anatomia humana; nenhum apêndice racial; pessoa claramente distinta do masculino | Deslocamento leve | reconstrução/oficina civil |
| RAC-VEL-M | Velado | Masculina | 29–35 | clara fria | liso preto, médio preso | baixo longilíneo | 1,58–1,64 m visual; orelhas largas laterais recuadas; olhos 10–15% maiores; dedos longos | Repouso controlado | limiar de pedra fria |
| RAC-VEL-F | Velado | Feminina | 42–49 | oliva muito clara fria | liso prateado-branco | baixa esguia | 1,52–1,60 m visual; orelhas largas laterais; olhos maiores; queixo estreito | Contemplação | umbrais frios quase alinhados |
| RAC-CIN-M | Cinéreo | Masculina | 46–54 | castanha média terrosa | ondulado preto, curto e espesso | baixo-médio muito denso | 1,64–1,72 m visual; mãos grandes; mandíbula/pescoço fortes; caninos inferiores curtos | Repouso firme | terreno rochoso e sustentação |
| RAC-CIN-F | Cinéreo | Feminina | 30–38 | negra retinta quente | crespo preto, curto e denso | compacta robusta | 1,58–1,66 m visual; mãos grandes; estrutura óssea forte; caninos inferiores curtos | Vigilância cotidiana | ponte curta pesada |
| RAC-HEM-M | Hemário | Masculina | 30–37 | clara quente/rubra | ondulado auburn escuro | atlético tenso | par de chifres médios varridos para trás; assinatura vascular viva; sem cauda/asas | Repouso tenso | pátio Hemaris envelhecido |
| RAC-HEM-F | Hemário | Feminina | 33–40 | castanha escura cobre | cacheado preto-auburn | atlética funcional | par de chifres curvos controlados; base integrada ao crânio; zonas de circulação vivas | Deslocamento controlado | corredor logístico envelhecido |
| RAC-ALV-M | Alvorano | Masculina | 31–38 | bronzeada dourada | liso preto, médio preso | alto ágil | 1,86–1,96 m visual; orelhas longas pontiagudas para cima/trás; membros discretamente alongados | Vigilância | terraço civil pré-Ruptura |
| RAC-ALV-F | Alvorano | Feminina | 34–41 | oliva dourada clara | ondulado castanho-cobre | alta coordenada | 1,78–1,88 m visual; orelhas longas pontiagudas; corpo alto e pronto para deslocamento | Deslocamento leve | posto civil ao amanhecer |

### Regra de aprovação das 10 âncoras

- o jogador deve distinguir as cinco Raças sem ler o nome;
- Velado e Remanescente não podem parecer apenas variações de roupa da mesma população;
- a anatomia diagnóstica deve ser reconhecível em silhueta: Velado (porte menor + orelhas largas/olhos maiores), Cinéreo (massa compacta + caninos curtos), Hemário (par de chifres), Alvorano (porte alto + orelhas longas), Remanescente (anatomia humana sem apêndice obrigatório);
- fundos devem ser diferentes entre as cinco Raças e subordinados ao personagem;
- apresentações M/F da mesma Raça compartilham a família histórica do fundo, mas não o mesmo enquadramento exato.

---

# 5.1 CONTROLE ANTI-GENÉRICO DE CLASSE

Para as 60 skins Raça × Classe:

- **toda Aparência padrão deve mostrar a arma-assinatura da Classe**;
- a arma-assinatura não pode ser substituída por mapa, placa, fio, sino, ferramenta civil ou efeito visual;
- `mãos livres`, Repouso e Contemplação apenas mudam o estado/posição do armamento;
- a escolha visual não cria regra mecânica de equipamento;
- dentro de uma mesma Raça, não reciclar o mesmo conjunto de túnica + lenço/capa + braçadeiras nas seis Classes;
- Sentinela, Errante, Vigia, Tecelão, Oráculo e Luminar devem possuir arquitetura de torso, distribuição de equipamento e família de armamento diferentes;
- não repetir castelo monumental, aqueduto, bandeiras ou skyline épico como fundo-padrão de várias Classes.

## 5.2 ASSINATURA DE ARMAMENTO POR CLASSE

| Classe | Regra obrigatória de leitura |
|---|---|
| Sentinela | arma de uma mão + escudo visível |
| Errante | duas armas curtas visíveis; preferir uma em cada mão quando a pose permitir |
| Vigia | arco ou besta sempre como arma principal visível |
| Tecelão | arma-foco de Trama visível e tecnicamente distinta de arma comum |
| Oráculo | arma-foco oracular/simbólica visível; foco ritual não pode parecer ferramenta civil comum |
| Luminar | cajado/bastão de combate-foco visível como assinatura principal |

## 5.3 ARMAMENTO VISÍVEL OBRIGATÓRIO — 60 APARÊNCIAS PADRÃO

Esta tabela complementa a coluna `Aparência padrão`. Em conflito de estado, preservar a pose e reposicionar o armamento sem apagar a assinatura da Classe.

| ID | Arma-assinatura obrigatória |
|---|---|
| PV-REM-SEN-M | espada de uma mão + escudo médio visível |
| PV-REM-SEN-F | maça curta + escudo médio visível |
| PV-REM-ERR-M | espada curta + adaga, preferencialmente uma em cada mão |
| PV-REM-ERR-F | duas adagas/lâminas curtas, uma em cada mão |
| PV-REM-VIG-M | arco longo nas costas + faca de campo secundária |
| PV-REM-VIG-F | arco recurvo abaixado + adaga secundária |
| PV-REM-TEC-M | bastão-foco curto de Trama + bracelete técnico |
| PV-REM-TEC-F | lâmina-foco de Trama + faca técnica secundária |
| PV-REM-ORA-M | cetro/bastão oracular curto + lâmina simbólica embainhada |
| PV-REM-ORA-F | lâmina simbólica ritual + bastão/cetro oracular preso |
| PV-REM-LUM-M | cajado de combate-foco médio, sem Luz ativa |
| PV-REM-LUM-F | cajado de combate-foco curto apoiado, sem brilho |
| PV-VEL-SEN-M | martelo de uma mão + escudo estreito |
| PV-VEL-SEN-F | espada reta + escudo leve |
| PV-VEL-ERR-M | duas lâminas curtas estreitas, uma em cada mão quando possível |
| PV-VEL-ERR-F | espada curta + adaga off-hand |
| PV-VEL-VIG-M | besta leve + adaga secundária |
| PV-VEL-VIG-F | arco longo + faca longa secundária |
| PV-VEL-TEC-M | cetro técnico de Trama + lâmina-foco secundária |
| PV-VEL-TEC-F | agulha/fuso de Trama de combate + bracelete técnico |
| PV-VEL-ORA-M | cajado oracular esguio + lâmina simbólica curta |
| PV-VEL-ORA-F | duas lâminas simbólicas + cetro oracular curto |
| PV-VEL-LUM-M | cajado de combate-foco médio |
| PV-VEL-LUM-F | bastão de combate-foco + Luz localizada mínima quando permitido |
| PV-CIN-SEN-M | machado curto + escudo robusto |
| PV-CIN-SEN-F | maça + escudo robusto |
| PV-CIN-ERR-M | duas facas longas/lâminas curtas de dorso largo |
| PV-CIN-ERR-F | espada curta + adaga curta |
| PV-CIN-VIG-M | arco robusto + faca de campo |
| PV-CIN-VIG-F | arco recurvo robusto + lâmina curta secundária |
| PV-CIN-TEC-M | haste segmentada de Trama + lâmina-foco curta |
| PV-CIN-TEC-F | lâmina-foco robusta + bracelete de tensão |
| PV-CIN-ORA-M | bastão oracular marcado + faca/lâmina simbólica |
| PV-CIN-ORA-F | lâmina simbólica curta + cetro oracular preso |
| PV-CIN-LUM-M | cajado de combate-foco curto e robusto |
| PV-CIN-LUM-F | cajado de combate-foco médio + Luz localizada quando permitida |
| PV-HEM-SEN-M | espada de uma mão + escudo médio |
| PV-HEM-SEN-F | lança curta de uma mão + escudo pequeno |
| PV-HEM-ERR-M | sabre curto + adaga off-hand |
| PV-HEM-ERR-F | duas lâminas curtas rápidas, uma em cada mão |
| PV-HEM-VIG-M | besta compacta + espada curta secundária |
| PV-HEM-VIG-F | arco longo + faca de campo |
| PV-HEM-TEC-M | lâmina-foco estreita + placa de inscrição técnica |
| PV-HEM-TEC-F | bastão-foco curto de Trama + lâmina secundária |
| PV-HEM-ORA-M | cetro oracular + lâmina simbólica curta |
| PV-HEM-ORA-F | lâmina simbólica baixa + bastão oracular curto |
| PV-HEM-LUM-M | cajado de combate-foco + escudo pequeno opcional secundário |
| PV-HEM-LUM-F | cajado/bastão de combate-foco baixo |
| PV-ALV-SEN-M | martelo curto + escudo pequeno |
| PV-ALV-SEN-F | espada reta + escudo leve |
| PV-ALV-ERR-M | espada curta + adaga utilitária, duas mãos armadas quando possível |
| PV-ALV-ERR-F | duas lâminas leves/curtas, uma em cada mão |
| PV-ALV-VIG-M | arco recurvo + lâmina curta secundária |
| PV-ALV-VIG-F | arco longo + espada curta secundária |
| PV-ALV-TEC-M | cetro técnico de Trama/agulha de tensão + braceletes |
| PV-ALV-TEC-F | lâmina-foco de Trama em uso |
| PV-ALV-ORA-M | bastão/cetro oracular + lâmina simbólica curta |
| PV-ALV-ORA-F | lâmina simbólica + cetro oracular curto |
| PV-ALV-LUM-M | cajado de combate-foco em guarda |
| PV-ALV-LUM-F | cajado de combate-foco + Barreira curta quando permitida |

---

# 6. MATRIZ DAS 60 ÂNCORAS RAÇA × CLASSE

## Remanescente

**Regra anatômica para todas as linhas Remanescentes:** anatomia humana individual; não adicionar chifres, orelhas raciais alongadas ou caninos/tusks como marcador de Raça.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-REM-SEN-M | Sentinela | Masculina | 24–29 | negra retinta | crespo curto preto | atlético leve | **Vigilância** — espada de uma mão baixa + escudo médio no braço | **Deslocamento** — espada baixa; casaco cinéreo reforçado |
| PV-REM-SEN-F | Sentinela | Feminina | 31–37 | castanha média quente | cacheado castanho-escuro, médio | robusta funcional | **Repouso** — maça apoiada + escudo médio visível | **Vigilância** — escudo apoiado e maça na mão |
| PV-REM-ERR-M | Errante | Masculina | 40–48 | oliva média | ondulado preto, curto | compacta | **Deslocamento** — espada curta + adaga, uma em cada mão | **Vigilância** — espada leve baixa sob manto dividido |
| PV-REM-ERR-F | Errante | Feminina | 27–34 | castanha clara quente | cacheado castanho, curto | esguia | **Vigilância** — duas lâminas curtas, uma em cada mão | **Deslocamento** — lâmina guardada, passos pela cinza |
| PV-REM-VIG-M | Vigia | Masculina | 50–58 | castanho-escura | crespo grisalho, curto | robusta | **Contemplação** — arco nas costas; mãos livres; faca de campo visível | **Vigilância** — arco abaixado; cinza no manto curto |
| PV-REM-VIG-F | Vigia | Feminina | 22–28 | oliva clara quente | ondulado castanho-escuro, curto | longilínea | **Vigilância** — arco abaixado; adaga secundária visível | **Contemplação** — arco nas costas olhando horizonte |
| PV-REM-TEC-M | Tecelão | Masculina | 35–42 | castanha média | tranças curtas escuras | atlética | **Contemplação** — bastão-foco curto de Trama na mão; outra mão examina relação espacial | **Vigilância** — braceletes cobertos de fuligem; sem efeito |
| PV-REM-TEC-F | Tecelão | Feminina | 29–36 | negra | crespo volumoso preso | alta e forte | **Vigilância** — lâmina-foco baixa e bracelete técnico | **Contemplação** — examinando pedra rachada com lâmina-foco baixa |
| PV-REM-ORA-M | Oráculo | Masculina | 44–52 | oliva média | ondulado grisalho, médio | média | **Contemplação** — cetro oracular curto + placa marcada; lâmina simbólica visível | **Vigilância** — placa marcada baixa; cinza passando ao fundo |
| PV-REM-ORA-F | Oráculo | Feminina | 25–31 | castanha escura | cacheado curto preto | compacta e ágil | **Vigilância** — lâmina simbólica curta + fio de marcadores; cetro preso | **Contemplação** — pequenos marcadores nas mãos, sem brilho |
| PV-REM-LUM-M | Luminar | Masculina | 33–40 | castanha clara quente | ondulado preto, curto | média | **Repouso** — cajado de combate-foco apoiado; sem Luz ativa | **Vigilância** — espada baixa; traço de calor contido na mão |
| PV-REM-LUM-F | Luminar | Feminina | 47–55 | negra retinta | tranças longas presas | robusta e estável | **Contemplação** — cajado de combate-foco curto; sem brilho | **Repouso** — arma guardada; tecido cinéreo sem Luz ativa |

## Velado

**Regra anatômica para todas as linhas Veladas:** porte baixo/esguio, orelhas largas varridas lateralmente para trás, olhos discretamente maiores e dedos relativamente longos. Capuzes/elmos acomodam as orelhas.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-VEL-SEN-M | Sentinela | Masculina | 28–35 | clara fria | liso preto, médio e preso | longilíneo | **Contemplação** — martelo de uma mão guardado + escudo estreito visível; mãos livres | **Preparação** — arma sendo erguida, placas cobertas de cinza |
| PV-VEL-SEN-F | Sentinela | Feminina | 36–44 | pálida fria | liso prateado, médio | baixa e esguia | **Preparação** — espada reta sendo sacada + escudo leve | **Repouso** — espada embainhada, ombro contra ruína |
| PV-VEL-ERR-M | Errante | Masculina | 23–30 | oliva clara fria | liso castanho-acinzentado, médio | esguio | **Repouso** — duas lâminas curtas visíveis, uma baixa e outra guardada | **Preparação** — mão no cabo, casaco de estrada aberto |
| PV-VEL-ERR-F | Errante | Feminina | 41–49 | clara fria | liso grisalho-escuro, curto | baixa/média e alongada | **Ação controlada** — passo lateral com espada curta + adaga off-hand | **Contemplação** — observando pegadas com arma embainhada |
| PV-VEL-VIG-M | Vigia | Masculina | 31–38 | pálida rosada fria | ondulado preto, preso baixo | baixo longilíneo atlético | **Deslocamento** — besta carregada baixa + adaga secundária | **Preparação** — retirando flecha, sem tensão |
| PV-VEL-VIG-F | Vigia | Feminina | 52–60 | oliva muito clara fria | liso branco-prateado, curto | baixa/média e contida | **Preparação** — retirando flecha; arco visível + faca longa | **Deslocamento** — besta baixa entre ruínas |
| PV-VEL-TEC-M | Tecelão | Masculina | 26–33 | clara fria | liso preto, longo preso | esguia | **Repouso** — cetro técnico de Trama apoiado + lâmina-foco secundária | **Preparação** — linhas curtas de Trama entre dedos |
| PV-VEL-TEC-F | Tecelão | Feminina | 34–42 | pálida fria | ondulado prateado, curto | média | **Preparação** — agulha/fuso de Trama + bracelete técnico | **Repouso** — bastão curto apoiado, tecido seco e desbotado |
| PV-VEL-ORA-M | Oráculo | Masculina | 45–53 | oliva clara fria | liso preto com grisalho, curto | baixa/média e magra | **Repouso** — cajado oracular esguio apoiado + lâmina simbólica | **Preparação** — fio simples entre dedos, olhar antecipatório |
| PV-VEL-ORA-F | Oráculo | Feminina | 24–31 | clara fria | liso branco, médio preso | longilínea | **Preparação** — duas lâminas simbólicas + cetro oracular curto | **Repouso** — objetos guardados sob manto de estrada |
| PV-VEL-LUM-M | Luminar | Masculina | 38–46 | pálida rosada | liso castanho-acinzentado com grisalho | média | **Vigilância** — cajado de combate-foco baixo; postura centrada | **Preparação** — maça baixa e Luz pequena no antebraço |
| PV-VEL-LUM-F | Luminar | Feminina | 29–36 | oliva clara fria | ondulado preto, curto | esguia atlética | **Preparação** — bastão de combate-foco + Luz localizada mínima | **Contemplação** — bastão apoiado diante de limiar frio |

## Cinéreo

**Regra anatômica para todas as linhas Cinéreas:** corpo compacto/denso, mãos grandes, mandíbula forte e caninos inferiores curtos; pele nunca mineral.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-CIN-SEN-M | Sentinela | Masculina | 32–39 | castanha média terrosa | crespo curto preto e espesso | compacto e denso | **Deslocamento** — machado curto baixo + escudo robusto | **Ação controlada** — passo de interceptação; escudo opcional |
| PV-CIN-SEN-F | Sentinela | Feminina | 24–31 | castanha escura quente | cacheado escuro preso curto | robusta e estável | **Ação controlada** — guarda com maça + escudo robusto | **Contemplação** — arma baixa diante de estrutura de carga |
| PV-CIN-ERR-M | Errante | Masculina | 46–54 | negra retinta | crespo baixo, barba grisalha curta | médio-baixo e assentado | **Contemplação** — duas facas longas visíveis; uma guardada e outra baixa | **Ação controlada** — mudança lateral de linha, uma lâmina curta |
| PV-CIN-ERR-F | Errante | Feminina | 28–35 | bronzeada média | ondulado preto e espesso, curto | média e firme | **Preparação** — espada curta + adaga sendo acessadas | **Repouso** — faca utilitária à cintura, mãos livres |
| PV-CIN-VIG-M | Vigia | Masculina | 37–45 | castanho-escura | tranças curtas grossas presas | atlético denso | **Repouso** — arco robusto apoiado no ombro + faca de campo | **Ação controlada** — mira curta com arco tensionado |
| PV-CIN-VIG-F | Vigia | Feminina | 52–60 | castanha média terrosa | ondulado grisalho, curto e espesso | robusta | **Ação controlada** — arco recurvo robusto erguido + lâmina curta | **Repouso** — arco apoiado, capa castigada pelo vento |
| PV-CIN-TEC-M | Tecelão | Masculina | 23–29 | negra | crespo médio preso alto | compacta e ágil | **Deslocamento** — haste segmentada de Trama baixa + lâmina-foco curta | **Ação controlada** — tensão localizada dobrando poeira no ar |
| PV-CIN-TEC-F | Tecelão | Feminina | 41–49 | castanha clara bronzeada | cacheado castanho-escuro, curto e denso | média-baixa e estável | **Ação controlada** — lâmina-foco robusta e linhas de Trama localizadas | **Deslocamento** — instrumentos de inscrição presos ao corpo |
| PV-CIN-ORA-M | Oráculo | Masculina | 30–37 | bronzeada escura | ondulado preto, raspado lateral | médio e firme | **Deslocamento** — bastão oracular marcado + pequeno sino + lâmina simbólica | **Ação controlada** — duas trajetórias incompletas muito discretas |
| PV-CIN-ORA-F | Oráculo | Feminina | 26–33 | castanha escura | crespo curto e espesso | robusta funcional | **Ação controlada** — lâmina simbólica curta + cetro oracular; trajetória incompleta | **Deslocamento** — sino pequeno preso, sem teatralidade |
| PV-CIN-LUM-M | Luminar | Masculina | 43–51 | castanha média quente | ondulado grisalho, médio preso | compacto | **Deslocamento** — cajado de combate-foco curto; brilho ausente | **Ação controlada** — barreira curta e densa, sem símbolo religioso |
| PV-CIN-LUM-F | Luminar | Feminina | 34–41 | negra retinta | tranças grossas curtas | alta e densa | **Ação controlada** — cajado de combate-foco + Luz localizada, sem halo | **Deslocamento** — espada curta baixa; camadas estruturadas |

## Hemário

**Regra anatômica para todas as linhas Hemárias:** exatamente um par de chifres de queratina integrado ao crânio; sem cauda/asas/cascos obrigatórios.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-HEM-SEN-M | Sentinela | Masculina | 25–32 | oliva quente/rubra | liso preto, curto | atlético tenso | **Repouso** — espada de uma mão embainhada + escudo médio apoiado | **Vigilância** — escudo no braço, arma ainda baixa |
| PV-HEM-SEN-F | Sentinela | Feminina | 39–47 | negra de subtom cobre | crespo curto preto com cobre e grisalho discreto | robusta funcional | **Vigilância** — lança curta de uma mão + escudo pequeno | **Deslocamento** — lança curta carregada verticalmente |
| PV-HEM-ERR-M | Errante | Masculina | 30–37 | clara quente/rubra | ondulado ruivo-escuro, curto | médio e musculatura funcional | **Vigilância** — sabre curto + adaga off-hand, corpo em transição | **Deslocamento** — manto dividido acompanhando passo |
| PV-HEM-ERR-F | Errante | Feminina | 22–28 | castanha escura de subtom rubro | cacheado preto com reflexo auburn, médio preso | esguia atlética | **Deslocamento** — duas lâminas curtas visíveis, uma em cada mão | **Vigilância** — espada baixa e corpo angulado |
| PV-HEM-VIG-M | Vigia | Masculina | 48–56 | castanho-escura quente | raspado, barba castanho-avermelhada grisalha | compacto e vigoroso | **Vigilância** — besta compacta baixa + espada curta secundária | **Contemplação** — ajoelhado observando terreno; arco no chão ao lado |
| PV-HEM-VIG-F | Vigia | Feminina | 33–40 | clara cobre | liso castanho-avermelhado, médio | alta e forte | **Contemplação** — arco longo ao lado do corpo + faca de campo | **Preparação** — encaixando flecha |
| PV-HEM-TEC-M | Tecelão | Masculina | 27–34 | negra retinta de subtom quente | tranças curtas preto-auburn | atlética compacta | **Contemplação** — lâmina-foco estreita + placa de inscrição técnica | **Contemplação** — mão sobre marca física, sem círculo mágico |
| PV-HEM-TEC-F | Tecelão | Feminina | 42–50 | oliva quente | ondulado auburn com grisalho | média e tensa | **Preparação** — bastão-foco curto de Trama + lâmina secundária | **Vigilância** — foco baixo e olhar técnico |
| PV-HEM-ORA-M | Oráculo | Masculina | 35–43 | castanha média cobre | cacheado castanho-escuro/auburn preso | robusto ágil | **Contemplação** — cetro oracular + lâmina simbólica curta; estojo fechado | **Contemplação** — observando estrutura distante, mãos livres |
| PV-HEM-ORA-F | Oráculo | Feminina | 23–30 | clara rosada quente | cacheado cobre-escuro, curto | esguia e vigorosa | **Vigilância** — lâmina simbólica baixa + bastão oracular curto | **Vigilância** — lâmina simbólica baixa, sem aura |
| PV-HEM-LUM-M | Luminar | Masculina | 51–59 | negra de subtom rubro | crespo preto-grisalho baixo | alto e forte | **Repouso** — cajado de combate-foco apoiado + escudo pequeno secundário | **Vigilância** — escudo pequeno no braço, sem halo |
| PV-HEM-LUM-F | Luminar | Feminina | 31–38 | castanha clara quente | liso preto com reflexo castanho-avermelhado, longo preso | atlética | **Vigilância** — cajado/bastão de combate-foco baixo; tórax centrado | **Preparação** — mão aberta com brilho neutro localizado |

## Alvorano

**Regra anatômica para todas as linhas Alvoranas:** porte médio-alto/alto, orelhas longas pontiagudas orientadas para cima/trás e coordenação corporal evidente; sem halo/asas.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-ALV-SEN-M | Sentinela | Masculina | 23–30 | bronzeada dourada | liso preto, curto | atlético e leve | **Deslocamento** — martelo curto baixo + escudo pequeno no braço | **Repouso** — arma apoiada, manto curto chamuscado |
| PV-ALV-SEN-F | Sentinela | Feminina | 34–41 | oliva dourada clara | ondulado castanho-cobre, curto | média e móvel | **Preparação** — espada reta em guarda + escudo leve | **Ação controlada** — guarda firme sem efeito sobrenatural |
| PV-ALV-ERR-M | Errante | Masculina | 45–53 | oliva média dourada | liso castanho-escuro com grisalho, curto | alto e coordenado | **Preparação** — espada curta + adaga, duas mãos armadas | **Contemplação** — ajoelhado examinando terreno, arma guardada |
| PV-ALV-ERR-F | Errante | Feminina | 27–34 | bronzeada média | liso/ondulado preto preso curto | compacta e ágil | **Repouso** — duas lâminas leves/curtas visíveis, uma apoiada e outra guardada | **Preparação** — lâmina sendo sacada sem pose de assassino |
| PV-ALV-VIG-M | Vigia | Masculina | 31–38 | oliva clara dourada | ondulado castanho, médio | esguio atlético | **Preparação** — encaixando flecha; arco recurvo + lâmina curta secundária | **Vigilância** — besta apoiada no ombro |
| PV-ALV-VIG-F | Vigia | Feminina | 50–58 | bronzeada escura | liso preto com grisalho, curto | robusta móvel | **Ação controlada** — mira com arco longo tensionado + espada curta secundária | **Deslocamento** — arco baixo e passo cuidadoso |
| PV-ALV-TEC-M | Tecelão | Masculina | 25–32 | castanha média dourada | liso castanho-escuro, médio preso | alta e ágil | **Vigilância** — cetro técnico/agulha de Trama + luvas técnicas | **Preparação** — placa marcada e linha tensionada discreta |
| PV-ALV-TEC-F | Tecelão | Feminina | 38–46 | oliva clara | ondulado preto-cobre, curto | média e pronta | **Ação controlada** — lâmina-foco resolvendo tensão localizada | **Ação controlada** — resolução de Trama curta, sem aura ampla |
| PV-ALV-ORA-M | Oráculo | Masculina | 29–36 | bronzeada média | liso castanho-escuro, médio preso | atlético | **Preparação** — bastão/cetro oracular + fio de marcação + lâmina simbólica | **Preparação** — marcadores sobre placa simples |
| PV-ALV-ORA-F | Oráculo | Feminina | 42–50 | oliva dourada clara | ondulado cobre-escuro, curto | compacta e coordenada | **Ação controlada** — lâmina simbólica + cetro curto; duplicação breve de gesto | **Ação controlada** — gesto duplicado sutil, sem fumaça moralizada |
| PV-ALV-LUM-M | Luminar | Masculina | 33–40 | castanha bronzeada | liso preto, curto e preso | alto e leve | **Preparação** — cajado de combate-foco em guarda; Luz apenas localizada | **Repouso** — foco guardado, respiração centrada |
| PV-ALV-LUM-F | Luminar | Feminina | 24–31 | oliva clara dourada | ondulado castanho-cobre, longo preso | esguia atlética | **Ação controlada** — cajado de combate-foco + barreira curta translúcida | **Ação controlada** — Luz concentrada em projeção curta |

---

# 7. REGRA DE DISTRIBUIÇÃO FENOTÍPICA

A regra de distribuição consolidada na v1.1 substituiu a regra antiga de distribuição uniforme entre todas as Raças.

Agora:

- cada Raça possui um **centro fenotípico reconhecível** definido pela Bíblia Visual v1.4;
- a diversidade acontece primeiro **dentro da faixa racial**;
- descendência mista permite exceções deliberadas, mas a exceção deve ser uma decisão de personagem, não aleatoriedade do gerador;
- não usar a mesma combinação de pele, cabelo, rosto e corpo como default para múltiplas Raças;
- representação negra permanece distribuída de modo forte entre Remanescentes, Cinéreos e Hemários, além de poder aparecer em indivíduos de outras linhagens por família mista;
- Velados de seleção usam contraste frio e cabelo preto/prateado/branco para legibilidade;
- Alvoranos usam centro oliva/dourado/bronze humano sem estética angelical;
- nenhum marcador racial autoriza estereótipo moral ou cultural.

---

# 8. ESTADOS DE POSE — CONTROLE DO LOTE

Antes de gerar o lote final, verificar a distribuição global dos sete estados:

- Repouso;
- Contemplação;
- Vigilância;
- Deslocamento;
- Preparação;
- Ação controlada;
- Ação intensa.

Objetivo editorial: não permitir que Preparação + Ação dominem visualmente o catálogo.

---

# 9. FUNDOS DE HERANÇA DAS 5 RAÇAS

| Raça | Motivo de fundo | O que comunica | Proibido |
|---|---|---|---|
| Remanescente | reconstrução em camadas, via/ponte/oficina reaproveitada | persistência, mistura histórica, adaptação | miséria caricata, ruína vazia, cenário genérico idêntico aos outros |
| Velado | limiar frio, arcos/umbrais repetidos, névoa fina | sensibilidade liminar e percepção | Avesso, portal, void purple, cemitério gótico |
| Cinéreo | terreno severo, sustentação, contrapesos, vento | populações moldadas por carga e condições duras | lava, magma, pele/arquitetura “racialmente de pedra” |
| Hemário | pátio clínico/logístico Hemaris envelhecido | origem histórica no Projeto Hemaris | gore, experimento gráfico, laboratório sci-fi, Matriz Rubra explícita |
| Alvorano | terraço/rota civil pré-Ruptura, horizonte e marcadores | linhagem natural anterior à Ruptura, prontidão | templo solar, halo, arquitetura celestial |

Esses fundos são vinhetas de herança e **não criam novos Locais de Mapa**.

---

# 10. MATRIZ DOS 30 FUNDOS RAÇA × CLASSE

A mesma combinação serve como família para as apresentações masculina e feminina; variar câmera, lado do ponto focal, horário e detalhe secundário para não duplicar exatamente a composição.

| Raça | Classe | Fundo-base |
|---|---|---|
| Remanescente | Sentinela | portão reconstruído com pedra de épocas diferentes e madeira nova; área de guarda comunitária |
| Remanescente | Errante | bifurcação entre rua antiga e passarela reparada, com várias rotas improvisadas |
| Remanescente | Vigia | torre/andaime reconstruído sobre ruína baixa, oferecendo linha de visão sobre assentamento vivo |
| Remanescente | Tecelão | oficina de reparo instalada sobre juntas antigas de pedra, medições físicas e peças reaproveitadas |
| Remanescente | Oráculo | encruzilhada de rotas remendadas com placas de direção de épocas diferentes, sem profecia explícita |
| Remanescente | Luminar | posto comunitário de recuperação junto a abrigo reconstruído e braseiro funcional discreto |
| Velado | Sentinela | umbral frio e estreito entre arcos quase alinhados, transformado em passagem defensiva |
| Velado | Errante | sequência de corredores/escadas liminares com duas saídas visualmente próximas e névoa fina |
| Velado | Vigia | mirante de pedra pálida com arcos repetidos e horizonte parcialmente oculto por névoa |
| Velado | Tecelão | galeria fria de juntas geométricas e placas técnicas antigas, linhas físicas quase coincidentes |
| Velado | Oráculo | cruzamento de três umbrais semelhantes com marcadores discretos; caminhos possíveis sem destino afirmado |
| Velado | Luminar | abrigo liminar de pedra clara com foco de calor funcional e sombras suaves, sem templo ou aura |
| Cinéreo | Sentinela | passagem entre muros de contenção e blocos pesados, feita para receber carga e impacto |
| Cinéreo | Errante | trilha estreita entre rocha e contrapesos, com vento lateral e apoios firmes |
| Cinéreo | Vigia | mirante de pedra robusta acima de terreno severo, marcos de distância presos contra vento |
| Cinéreo | Tecelão | estação de manutenção de contrapesos e juntas estruturais, pedra/metal sob tensão física |
| Cinéreo | Oráculo | entroncamento de passagens pesadas marcado por pilares, correntes e orientação redundante |
| Cinéreo | Luminar | posto de recuperação protegido do vento por paredes baixas e lã/couro, calor funcional discreto |
| Hemário | Sentinela | portão interno de antiga instalação Hemaris, placas de proteção e corredor clínico-logístico gasto |
| Hemário | Errante | passagem de serviço entre alas antigas, tubos/canais cobertos e rotas de manutenção laterais |
| Hemário | Vigia | plataforma logística elevada sobre pátio médico antigo, visão longa e ferrugem controlada |
| Hemário | Tecelão | sala de manutenção analógica com placas, escalas e juntas de infraestrutura Hemaris, sem sci-fi |
| Hemário | Oráculo | cruzamento de corredores clínicos com sinalização apagada e múltiplas rotas possíveis |
| Hemário | Luminar | posto de triagem/recuperação antigo, leitos vazios ou bancos funcionais sem gore, luz quente pequena |
| Alvorano | Sentinela | posto civil pré-Ruptura de controle de passagem, linhas limpas e horizonte aberto |
| Alvorano | Errante | terraço de rota com duas rampas e marcadores baixos, sugerindo decisão rápida de deslocamento |
| Alvorano | Vigia | plataforma de orientação com horizonte amplo, marcos de distância e instrumentos analógicos simples |
| Alvorano | Tecelão | pátio técnico pré-Ruptura com placas de medição, juntas e organização metódica, sem brilho |
| Alvorano | Oráculo | cruzamento civil de rotas com marcadores duplicados e caminhos divergentes sob luz clara |
| Alvorano | Luminar | pátio de apoio e recuperação pré-Ruptura com foco de calor funcional e equipamentos organizados, sem templo |

### Regra de composição

Cada fundo Raça × Classe deve conter:

1. **motivo histórico racial** reconhecível;
2. **função espacial da Classe**;
3. quando a Aparência for regional, **materiais da Região** como terceira camada.

Exemplo: um **Velado Vigia em Errante das Cinzas** mantém um mirante/limiar frio de leitura Velada, recebe linha longa de visão de Vigia e ganha cinza/couro seco/metal fosco das Terras do Ocaso. Não vira simplesmente “o mesmo fundo de ruínas do Ocaso” usado por todos.

---

# 11. FUNDO DO LOTE TERRAS DO OCASO

Para as Aparências produzidas durante a frente de Terras do Ocaso:

- formato 1:1;
- corpo inteiro;
- personagem centralizado;
- fundo contextual discreto, nunca batalha completa;
- materiais regionais de cinza/pedra podem ser adicionados como terceira camada;
- luz fria/desaturada quando coerente;
- nenhum spoiler de Âncora, Avesso ou revelação posterior;
- **não apagar o fundo de herança racial nem o motivo funcional de Classe com uma ruína genérica igual para todo o catálogo**;
- diferença entre Aparência padrão e Errante das Cinzas vem principalmente do personagem/material regional, preservando a família espacial da combinação quando útil.

---

# 12. CONTROLE DE STATUS

| Campo | Valores recomendados |
|---|---|
| Status | Não iniciado / Gerado / Revisar / Regenerar / Aprovado |
| Anatomia | OK / Falha |
| Fenótipo racial | OK / Fraco / Falha |
| Classe | OK / Falha |
| Fundo racial | OK / Genérico / Falha |
| Fundo de Classe | OK / Fraco / Falha |
| Pose | OK / Repetitiva / Falha |
| Arma/foco | OK / Corrigir / Falha |
| Pixel art | OK / Lisa demais / Ruído |
| Spoiler | OK / Falha |
| Arquivo final | caminho/nome |

Não considerar “bonita” uma imagem equivalente a “aprovada”. Se a Raça não for distinguível em leitura rápida, o asset deve ser regenerado mesmo que anatomia e atmosfera estejam boas.

---

# 13. MIGRAÇÃO DA v1.0

Os assets raciais e prompts produzidos com a v1.0 antes deste fechamento devem ser revisados. Em especial:

- `raca_remanescente_masculino.png`;
- `raca_remanescente_feminino.png`;
- `raca_velado_masculino.png`;
- `raca_velado_feminino.png`;
- qualquer prompt Raça × Classe que use a distribuição antiga “qualquer tom/cabelo em qualquer Raça” como regra principal;
- qualquer skin que use o mesmo fundo genérico de ruínas para todas as Raças.

Esses assets não são automaticamente inválidos como ilustração, mas **não devem ser aprovados como âncoras oficiais de identificação racial** se a linhagem não estiver legível sem o nome.

---

# 14. FECHAMENTO

A Matriz v1.3 existe para impedir três problemas:

1. aleatoriedade sem direção;
2. padronização excessiva dentro de uma Raça;
3. intercambialidade visual entre Raças diferentes.

Frase-guia:

> **Diversidade é planejada dentro de famílias reconhecíveis; identidade racial precisa sobreviver ao figurino, à Classe e ao fundo.**

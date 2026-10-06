# ASTERION — MATRIZ DE PRODUÇÃO VISUAL v1.0

**Data de consolidação:** 2026-10-05  
**Escopo:** controle editorial de diversidade, continuidade visual, pose e variação para produção de personagens jogáveis; estrutura reutilizável para os demais lotes de assets  
**Estado:** documento operacional de produção — não redefine cânone biológico, mecânico ou regional

> Esta Matriz é subordinada a `SOURCE_AUTHORITY.md`, às Fontes canônicas e às Bíblias Visuais. Ela distribui escolhas concretas de produção para evitar repetição e deriva. Um tom de pele, corte de cabelo, idade ou constituição listado aqui pertence à **âncora daquele asset**, não à Raça inteira.

---

# 1. FUNÇÃO

A primeira função desta Matriz é fechar as **60 âncoras humanoides** do conjunto inicial de personagem:

- 5 Raças;
- 6 Classes;
- 2 apresentações utilizadas no lote inicial de produção (masculina/feminina);
- total de 60 combinações-base.

Asterion permite qualquer gênero em seu cânone; as duas apresentações acima são apenas o escopo do lote visual inicialmente planejado e não limitam a Lore.

Cada âncora pode originar mais de uma Aparência. Para o lote inicial:

- **Aparência padrão:** 60 imagens;
- **Errante das Cinzas:** 60 imagens;
- total planejado desta frente: **120 imagens de personagem**, preservando as mesmas 60 identidades-base.

---

# 2. REGRA DE CONTINUIDADE ENTRE APARÊNCIAS

Quando a Aparência padrão e `Errante das Cinzas` representarem a mesma âncora, preservar:

- rosto e estrutura facial;
- tom de pele;
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

A Fonte Regional define `Errante das Cinzas` como Aparência conquistada pelo Feito **Entre Aquilo que Caça**, ligado ao domínio do Bestiário regional. A apresentação Visual/UI descreve alguém que atravessa terras cobertas de cinza e retorna carregando no próprio semblante os sinais de ter aprendido a caminhar entre aquilo que caça e aquilo que é caçado.

Para produção, isso se traduz em:

- vestuário de estrada funcional e muito usado;
- cinza e fuligem acumuladas de forma física;
- couro ressecado;
- metal fosco e reparado;
- tecido seco e desbotado;
- camadas, cintas e reparos que sugerem permanência prolongada no Ocaso;
- proteção adaptada à Classe;
- nenhuma transformação corporal pela Região;
- nenhum “caçador de monstros” genérico coberto de troféus;
- nenhum crânio, dente, osso ou pele de criatura como obrigação;
- nenhum poder de cinzas inventado;
- nenhum efeito sobrenatural novo criado pelo cosmético.

Adaptação de Classe:

- **Sentinela:** casaco/armadura de estrada reforçada, placas parciais, base firme; escudo opcional.
- **Errante:** camadas mais leves, manto/casaco dividido, bainhas e cintas funcionais, pernas livres.
- **Vigia:** proteção leve/média, capa curta controlável, aljava/sistema de munição quando aplicável.
- **Tecelão:** camadas que permitam precisão, braceletes/luvas/instrumentos técnicos; sem “magia de cinzas”.
- **Oráculo:** roupa de viagem prática com placas, fios ou marcadores discretos quando usados; sem cartomante teatral.
- **Luminar:** proteção funcional e vestuário marcado pela fuligem; Luz apenas quando a Classe/pose pedir, nunca halo ou santidade.

---

# 4. NOMENCLATURA

ID de âncora:

```text
PV-<RACA>-<CLASSE>-<M/F>
```

Arquivos recomendados:

```text
aparencia_padrao_<raca>_<classe>_<masculino|feminino>.png
aparencia_errante_das_cinzas_<raca>_<classe>_<masculino|feminino>.png
```

Os nomes são de produção. IDs de backend permanecem responsabilidade de Implementação.

---

# 5. MATRIZ DAS 60 ÂNCORAS

## Remanescente

| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-REM-SEN-M | Sentinela | Masculina | 24–29 | negra retinta | crespo curto preto | atlético leve | **Vigilância** — espada de uma mão abaixada; sem escudo | **Deslocamento** — espada baixa; casaco cinéreo reforçado |
| PV-REM-SEN-F | Sentinela | Feminina | 31–37 | oliva média | ondulado castanho-escuro, médio | robusta funcional | **Repouso** — maça apoiada; escudo pequeno ao lado | **Vigilância** — escudo apoiado e maça na mão |
| PV-REM-ERR-M | Errante | Masculina | 40–48 | castanha média | raspado com barba curta escura | compacta | **Deslocamento** — espada leve baixa | **Vigilância** — espada leve baixa sob manto dividido |
| PV-REM-ERR-F | Errante | Feminina | 27–34 | clara quente | cacheado ruivo-escuro, curto | esguia | **Vigilância** — lâmina curta embainhada, mão próxima ao cabo | **Deslocamento** — lâmina guardada, passos pela cinza |
| PV-REM-VIG-M | Vigia | Masculina | 50–58 | castanho-escura | crespo grisalho, curto | robusta | **Contemplação** — arco nas costas; mãos livres | **Vigilância** — arco abaixado; cinza no manto curto |
| PV-REM-VIG-F | Vigia | Feminina | 22–28 | clara fria | liso castanho-claro, curto | longilínea | **Vigilância** — arco abaixado; flecha ainda na aljava | **Contemplação** — arco nas costas olhando horizonte |
| PV-REM-TEC-M | Tecelão | Masculina | 35–42 | castanha clara | tranças curtas escuras | atlética | **Contemplação** — sem foco; mãos examinando uma relação espacial | **Vigilância** — braceletes cobertos de fuligem; sem efeito |
| PV-REM-TEC-F | Tecelão | Feminina | 29–36 | negra | crespo volumoso preso | alta e forte | **Vigilância** — lâmina-foco baixa | **Contemplação** — examinando pedra rachada com lâmina-foco baixa |
| PV-REM-ORA-M | Oráculo | Masculina | 44–52 | oliva clara | ondulado grisalho, médio | média | **Contemplação** — placa marcada pequena nas mãos | **Vigilância** — placa marcada baixa; cinza passando ao fundo |
| PV-REM-ORA-F | Oráculo | Feminina | 25–31 | castanha escura | cacheado curto preto | compacta e ágil | **Vigilância** — fio curto com marcadores, sem efeito | **Contemplação** — pequenos marcadores nas mãos, sem brilho |
| PV-REM-LUM-M | Luminar | Masculina | 33–40 | clara rosada | liso ruivo, curto | média | **Repouso** — espada embainhada; sem Luz ativa | **Vigilância** — espada baixa; traço de calor contido na mão |
| PV-REM-LUM-F | Luminar | Feminina | 47–55 | negra retinta | tranças longas presas | robusta e estável | **Contemplação** — bastão curto apoiado; sem brilho | **Repouso** — arma guardada; tecido cinéreo sem Luz ativa |

## Velado

| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-VEL-SEN-M | Sentinela | Masculina | 28–35 | castanha escura | liso preto, médio e preso | longilíneo | **Contemplação** — arma embainhada; mãos livres | **Preparação** — arma sendo erguida, placas cobertas de cinza |
| PV-VEL-SEN-F | Sentinela | Feminina | 36–44 | negra | crespo curto muito controlado | alta e esguia | **Preparação** — espada sendo sacada; sem escudo | **Repouso** — espada embainhada, ombro contra ruína |
| PV-VEL-ERR-M | Errante | Masculina | 23–30 | oliva clara | ondulado castanho, médio | esguio | **Repouso** — faca utilitária visível, arma principal guardada | **Preparação** — mão no cabo, casaco de estrada aberto |
| PV-VEL-ERR-F | Errante | Feminina | 41–49 | clara quente | liso grisalho-escuro, curto | média e alongada | **Ação controlada** — passo lateral com espada leve | **Contemplação** — observando pegadas com arma embainhada |
| PV-VEL-VIG-M | Vigia | Masculina | 31–38 | castanha média | cacheado escuro preso baixo | longilíneo atlético | **Deslocamento** — besta carregada baixa, sem mira | **Preparação** — retirando flecha, sem tensão |
| PV-VEL-VIG-F | Vigia | Feminina | 52–60 | negra retinta | raspado com grisalho nas têmporas | alto e contido | **Preparação** — retirando uma flecha da aljava | **Deslocamento** — besta baixa entre ruínas |
| PV-VEL-TEC-M | Tecelão | Masculina | 26–33 | clara fria | ondulado preto, longo preso | esguia | **Repouso** — bastão curto apoiado | **Preparação** — linhas curtas de Trama entre dedos |
| PV-VEL-TEC-F | Tecelão | Feminina | 34–42 | oliva média | cacheado curto castanho-escuro | média | **Preparação** — bracelete técnico e mão marcando tensão | **Repouso** — bastão curto apoiado, tecido seco e desbotado |
| PV-VEL-ORA-M | Oráculo | Masculina | 45–53 | castanho-escura | tranças finas curtas | alta e magra | **Repouso** — objeto de observação guardado; mãos livres | **Preparação** — fio simples entre dedos, olhar antecipatório |
| PV-VEL-ORA-F | Oráculo | Feminina | 24–31 | negra | crespo médio preso | longilínea | **Preparação** — duas lâminas simbólicas simples, sem brilho | **Repouso** — objetos guardados sob manto de estrada |
| PV-VEL-LUM-M | Luminar | Masculina | 38–46 | clara rosada | liso castanho-escuro com grisalho | média | **Vigilância** — maça baixa; postura centrada | **Preparação** — maça baixa e Luz pequena no antebraço |
| PV-VEL-LUM-F | Luminar | Feminina | 29–36 | castanha clara | ondulado ruivo-escuro, curto | esguia atlética | **Preparação** — mão livre à frente; Luz localizada mínima | **Contemplação** — bastão apoiado diante do crepúsculo |

## Cinéreo

| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-CIN-SEN-M | Sentinela | Masculina | 32–39 | castanha média | crespo curto preto | compacto e denso | **Deslocamento** — machado curto baixo; escudo preso às costas | **Ação controlada** — passo de interceptação; escudo opcional |
| PV-CIN-SEN-F | Sentinela | Feminina | 24–31 | clara quente | ondulado castanho, preso curto | robusta e estável | **Ação controlada** — guarda com maça; sem escudo | **Contemplação** — arma baixa diante de horizonte de cinzas |
| PV-CIN-ERR-M | Errante | Masculina | 46–54 | negra retinta | raspado, barba grisalha curta | alto e assentado | **Contemplação** — lâmina guardada, observando rota | **Ação controlada** — mudança lateral de linha, uma lâmina curta |
| PV-CIN-ERR-F | Errante | Feminina | 28–35 | oliva média | liso preto, curto | média e firme | **Preparação** — lâmina curta sendo sacada | **Repouso** — faca utilitária à cintura, mãos livres |
| PV-CIN-VIG-M | Vigia | Masculina | 37–45 | castanho-escura | tranças curtas presas | atlético denso | **Repouso** — arco apoiado no ombro | **Ação controlada** — mira curta com arco tensionado |
| PV-CIN-VIG-F | Vigia | Feminina | 52–60 | clara fria | ondulado grisalho, curto | robusto | **Ação controlada** — arco erguido sem tensão máxima | **Repouso** — arco apoiado, capa coberta de fuligem |
| PV-CIN-TEC-M | Tecelão | Masculina | 23–29 | negra | crespo médio preso alto | compacta e ágil | **Deslocamento** — instrumento de inscrição guardado; foco discreto | **Ação controlada** — tensão localizada dobrando cinza no ar |
| PV-CIN-TEC-F | Tecelão | Feminina | 41–49 | castanha clara | cacheado castanho-escuro, curto | alta e estável | **Ação controlada** — linhas de Trama localizadas entre mão e foco | **Deslocamento** — instrumentos de inscrição presos ao corpo |
| PV-CIN-ORA-M | Oráculo | Masculina | 30–37 | oliva clara | raspado lateral com topo ondulado | médio e firme | **Deslocamento** — pequeno sino preso ao cinto; olhar antecipatório | **Ação controlada** — duas trajetórias incompletas muito discretas |
| PV-CIN-ORA-F | Oráculo | Feminina | 26–33 | castanha escura | crespo curto | robusta funcional | **Ação controlada** — trajetória incompleta sugerida perto da mão | **Deslocamento** — sino pequeno preso, sem teatralidade |
| PV-CIN-LUM-M | Luminar | Masculina | 43–51 | clara rosada | liso grisalho, médio preso | compacto | **Deslocamento** — espada curta baixa; brilho ausente | **Ação controlada** — barreira curta e densa, sem símbolo religioso |
| PV-CIN-LUM-F | Luminar | Feminina | 34–41 | negra retinta | tranças grossas curtas | alta e densa | **Ação controlada** — Luz concentrada na mão/foco, sem halo | **Deslocamento** — espada curta baixa; cinza nas camadas |

## Hemário

| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-HEM-SEN-M | Sentinela | Masculina | 25–32 | oliva média | liso preto, curto | atlético tenso | **Repouso** — espada embainhada; escudo apoiado no chão | **Vigilância** — escudo no braço, arma ainda baixa |
| PV-HEM-SEN-F | Sentinela | Feminina | 39–47 | negra | crespo curto com grisalho discreto | robusta funcional | **Vigilância** — lança curta vertical; sem escudo | **Deslocamento** — lança curta carregada verticalmente |
| PV-HEM-ERR-M | Errante | Masculina | 30–37 | clara quente | ondulado ruivo-escuro, curto | médio e musculatura funcional | **Vigilância** — espada leve baixa e corpo em transição | **Deslocamento** — manto dividido acompanhando passo |
| PV-HEM-ERR-F | Errante | Feminina | 22–28 | castanha escura | cacheado preto, médio preso | esguia atlética | **Deslocamento** — duas ferramentas de cintura; uma lâmina curta visível | **Vigilância** — espada baixa e corpo angulado |
| PV-HEM-VIG-M | Vigia | Masculina | 48–56 | castanho-escura | raspado com barba grisalha | compacto e vigoroso | **Vigilância** — besta baixa enquanto observa o terreno | **Contemplação** — ajoelhado observando terreno; arco no chão ao lado |
| PV-HEM-VIG-F | Vigia | Feminina | 33–40 | clara fria | liso castanho-escuro, médio | alta e forte | **Contemplação** — arco ao lado do corpo, olhando horizonte | **Preparação** — encaixando flecha |
| PV-HEM-TEC-M | Tecelão | Masculina | 27–34 | negra retinta | tranças curtas | atlética compacta | **Contemplação** — placa de inscrição na mão, sem efeito | **Contemplação** — mão sobre marca física, sem círculo mágico |
| PV-HEM-TEC-F | Tecelão | Feminina | 42–50 | oliva clara | ondulado castanho com grisalho | média e tensa | **Preparação** — bastão curto erguido, efeito mínimo | **Vigilância** — foco baixo e olhar técnico |
| PV-HEM-ORA-M | Oráculo | Masculina | 35–43 | castanha média | crespo médio preso | robusto ágil | **Contemplação** — cartas/lâminas simbólicas fechadas em estojo | **Contemplação** — observando ruína distante, mãos livres |
| PV-HEM-ORA-F | Oráculo | Feminina | 23–30 | clara rosada | cacheado ruivo, curto | esguia e vigorosa | **Vigilância** — placa marcada baixa; olhar fora do eixo | **Vigilância** — lâmina simbólica baixa, sem aura |
| PV-HEM-LUM-M | Luminar | Masculina | 51–59 | negra | crespo grisalho baixo | alto e forte | **Repouso** — escudo pequeno apoiado; arma guardada | **Vigilância** — escudo pequeno no braço, sem halo |
| PV-HEM-LUM-F | Luminar | Feminina | 31–38 | castanha clara | liso preto, longo preso | atlética | **Vigilância** — bastão baixo; tórax centrado | **Preparação** — mão aberta com brilho neutro localizado |

## Alvorano

| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-ALV-SEN-M | Sentinela | Masculina | 23–30 | negra | crespo curto | atlético e leve | **Deslocamento** — arma curta baixa; escudo pequeno no braço | **Repouso** — arma apoiada, manto curto chamuscado |
| PV-ALV-SEN-F | Sentinela | Feminina | 34–41 | clara quente | ondulado castanho-claro, curto | média e móvel | **Preparação** — espada reta em guarda; sem escudo | **Ação controlada** — guarda firme sem efeito sobrenatural |
| PV-ALV-ERR-M | Errante | Masculina | 45–53 | oliva média | liso grisalho-escuro, curto | alto e coordenado | **Preparação** — faca utilitária em uma mão, principal ainda embainhada | **Contemplação** — ajoelhado examinando terreno, arma guardada |
| PV-ALV-ERR-F | Errante | Feminina | 27–34 | castanha escura | tranças curtas presas | compacta e ágil | **Repouso** — espada leve apoiada junto à perna | **Preparação** — lâmina sendo sacada sem pose de assassino |
| PV-ALV-VIG-M | Vigia | Masculina | 31–38 | clara fria | cacheado castanho, médio | esguio atlético | **Preparação** — encaixando flecha sem puxar a corda | **Vigilância** — besta apoiada no ombro |
| PV-ALV-VIG-F | Vigia | Feminina | 50–58 | negra retinta | raspado com grisalho | robusto móvel | **Ação controlada** — mira com arco tensionado, geometria simples | **Deslocamento** — arco baixo e passo cuidadoso |
| PV-ALV-TEC-M | Tecelão | Masculina | 25–32 | castanha média | crespo médio preso | alta e ágil | **Vigilância** — luvas técnicas; sem foco principal | **Preparação** — placa marcada e linha tensionada discreta |
| PV-ALV-TEC-F | Tecelão | Feminina | 38–46 | oliva clara | ondulado preto, curto | média e pronta | **Ação controlada** — lâmina-foco resolvendo tensão localizada | **Ação controlada** — resolução de Trama curta, sem aura ampla |
| PV-ALV-ORA-M | Oráculo | Masculina | 29–36 | castanho-escura | liso castanho-escuro, médio preso | atlético | **Preparação** — fio de marcação entre os dedos, geometria simples | **Preparação** — marcadores sobre placa simples |
| PV-ALV-ORA-F | Oráculo | Feminina | 42–50 | clara rosada | cacheado ruivo-escuro, curto | compacta e coordenada | **Ação controlada** — duplicação breve de gesto, muito discreta | **Ação controlada** — gesto duplicado sutil, sem fumaça moralizada |
| PV-ALV-LUM-M | Luminar | Masculina | 33–40 | negra retinta | tranças finas curtas | alto e leve | **Preparação** — espada curta em guarda e Luz apenas na lâmina/mão | **Repouso** — foco guardado, respiração centrada |
| PV-ALV-LUM-F | Luminar | Feminina | 24–31 | castanha clara | ondulado castanho, longo preso | esguia atlética | **Ação controlada** — barreira curta translúcida junto ao braço | **Ação controlada** — Luz concentrada em projeção curta |

---

# 6. REGRA DE DISTRIBUIÇÃO

A matriz acima foi construída para que:

- nenhum tom de pele seja associado a uma única Raça;
- nenhuma textura de cabelo funcione como marcador racial obrigatório;
- Velados não sejam sistematicamente pálidos ou de cabelo branco;
- Cinéreos não sejam sistematicamente baixos, extremamente musculosos ou “de pedra”;
- Hemários não sejam sistematicamente pálidos, góticos ou sanguinolentos;
- Alvoranos não sejam sistematicamente claros, dourados ou “angelicais”;
- Remanescentes não funcionem como “humano padrão neutro”;
- homens e mulheres apareçam nas seis Classes;
- Sentinelas nem sempre usem escudo;
- Vigias nem sempre estejam mirando;
- Tecelões nem sempre conjurem;
- Oráculos nem sempre exibam efeitos;
- Luminares nem sempre emitam Luz.

---

# 7. ESTADOS DE POSE — CONTROLE DO LOTE

Antes de gerar o lote final, verificar a distribuição global dos sete estados:

- Repouso;
- Contemplação;
- Vigilância;
- Deslocamento;
- Preparação;
- Ação controlada;
- Ação intensa.

Objetivo editorial: **não permitir que Preparação + Ação dominem visualmente o catálogo**. Ação intensa é reservada a poucas artes promocionais ou casos em que a leitura realmente se beneficie dela.

---

# 8. FUNDO DO LOTE INICIAL

Para as skins completas produzidas durante a frente de Terras do Ocaso:

- formato 1:1;
- corpo inteiro;
- personagem centralizado;
- fundo contextual discreto, nunca uma batalha completa;
- chão de cinza/pedra compatível;
- 1–2 formas ambientais simples;
- luz fria/desaturada;
- nenhum spoiler de Âncora, Avesso ou revelação posterior;
- diferença entre Aparência padrão e Errante das Cinzas deve vir principalmente do personagem, não de trocar o cenário por uma cena totalmente diferente.

---

# 9. CONTROLE DE STATUS

Para cada asset produzido, registrar externamente ou abaixo da matriz:

| Campo | Valores recomendados |
|---|---|
| Status | Não iniciado / Gerado / Revisar / Regenerar / Aprovado |
| Anatomia | OK / Falha |
| Raça | OK / Falha |
| Classe | OK / Falha |
| Pose | OK / Repetitiva / Falha |
| Arma/foco | OK / Corrigir / Falha |
| Pixel art | OK / Lisa demais / Ruído |
| Spoiler | OK / Falha |
| Arquivo final | caminho/nome |

Não considerar “bonita” uma imagem equivalente a “aprovada”. Anatomia, identidade e integridade técnica têm prioridade.

---

# 10. MATRIZ PARA CRIATURAS E CENÁRIOS

Para lotes não humanoides, usar a mesma lógica de controle sem inventar diversidade humana. Cada linha futura deve registrar no mínimo:

## Criatura

- nome canônico;
- Região/Local;
- categoria;
- habitat;
- silhueta-chave;
- pose/comportamento;
- fundo;
- elementos proibidos;
- status de QA.

## Cenário

- nome canônico;
- Região;
- função histórica;
- bioma;
- arquitetura;
- composição;
- luz/clima;
- mistério permitido;
- elementos proibidos;
- status de QA.

As Bíblias de Bestiário e Ambientes continuam sendo a autoridade do conteúdo dessas linhas.

---

# 11. FECHAMENTO

A Matriz existe para impedir dois problemas opostos:

1. **aleatoriedade sem direção**, em que o gerador decide sozinho quem aparece em Asterion;
2. **padronização excessiva**, em que toda Raça, Classe ou gênero acaba recebendo o mesmo rosto, corpo, cor e pose.

Frase-guia:

> **Diversidade é planejada no conjunto; identidade é preservada em cada personagem.**

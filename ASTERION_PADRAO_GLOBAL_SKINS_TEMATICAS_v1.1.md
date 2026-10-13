# ASTERION — PADRÃO GLOBAL DE SKINS TEMÁTICAS v1.1

**Data de consolidação:** 2026-10-12  
**Escopo:** produção, geração, revisão e QA de Aparências/skins temáticas de personagens jogáveis  
**Estado:** fonte visual operacional global aprovada para produção futura  
**Aplicação:** prospectiva para novas levas e imediata para levas ainda em produção; assets já aprovados não são reabertos automaticamente  

> Este documento não cria Lore, mecânica, proficiência, inventário, Raça, Classe, Caminho, Região, Local ou Cosmético. Ele formaliza o **método global de produção** de skins temáticas para que Asterion permaneça visualmente coerente entre lotes, Regiões e ferramentas de geração.

---

# 1. POSIÇÃO NA HIERARQUIA DE FONTES

Para uma skin temática, usar as fontes nesta ordem:

1. `SOURCE_AUTHORITY.md` ou sua atualização vigente;
2. Fonte Mestra vigente;
3. Fonte Regional FINAL vigente, quando a Aparência pertencer a uma Região;
4. `ASTERION_LORE_BIBLE_CANON_v1.2.md` ou revisão vigente;
5. `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md` ou revisão vigente;
6. **este `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md`**;
7. Fonte Visual Especializada da Aparência, quando existir;
8. `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md` quando houver Região/Local real;
9. Fonte Visual/UI vigente quando o asset pertencer a uma tela específica;
10. `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md` ou revisão vigente;
11. `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md` ou revisão vigente.

## 1.1 Regra de precedência

- conteúdo regional FINAL nunca é substituído por uma decisão estética genérica;
- identidade de Raça e Classe vem da Bíblia Visual vigente;
- a Bíblia Técnica continua definindo canvas, pixel art, anatomia e QA técnico;
- este padrão fecha **consistência de catálogo, escala, câmera, variação e construção de fundo para skins temáticas**;
- uma Fonte Visual Especializada de Aparência pode criar exceção ao padrão global **somente no escopo explicitamente declarado** e somente quando registrada na Autoridade das Fontes;
- documento antigo de prompts não é autoridade se divergir das Fontes vigentes.

Exemplo já existente: `ASTERION_APARENCIA_ERRANTE_DAS_CINZAS_FONTE_VISUAL_v1.3.md` preserva suas exceções específicas de armamento e composição e não é reaberto por este documento.

---

# 2. PRINCÍPIO GLOBAL

Toda skin temática deve comunicar, nesta ordem de leitura:

1. **Pessoa / indivíduo** — não parecer um personagem diferente por acidente;
2. **Classe** — função imediatamente legível por silhueta, equipamento, arma/foco e postura;
3. **Raça** — fenótipo reconhecível sem depender de texto, roupa ou símbolo;
4. **Aparência/tema** — materiais, desgaste, solução de traje e assinatura cosmética;
5. **Região**, quando aplicável — ambiente, clima e materialidade coerentes com o conteúdo regional.

Regra-guia:

> **A skin muda a apresentação; não apaga a pessoa, a Raça, a Classe nem o mundo ao redor dela.**

---

# 3. IDENTIDADE TÉCNICA OBRIGATÓRIA

Todas as skins temáticas devem preservar a identidade visual global de Asterion:

- dark fantasy medieval;
- estética de fim da era 16-bit / início da era 32-bit;
- **pixel art nativa**, não pintura suave com filtro de pixel;
- pixels deliberadamente visíveis;
- clusters intencionais;
- formas grandes antes de microdetalhe;
- materiais físicos antes de efeitos;
- saturação baixa/moderada;
- fantasia contida;
- anatomia humanoide legível;
- fundo subordinado ao personagem.

Reprovar:

- concept art painterly suavizada e depois pixelizada;
- 3D/CGI com pixels falsos;
- acabamento moderno liso;
- blur amplo;
- bloom/glow para esconder forma ou anatomia;
- ruído de pixel uniforme em toda a imagem;
- microdetalhe que destrói a leitura da silhueta.

---

# 4. CANVAS, ESCALA E PADRÃO DE “TAMANHO DE TELA”

## 4.1 Formato

Para skin jogável:

- proporção `1:1`;
- master `1024×1024`;
- PNG;
- corpo inteiro;
- cabeça e pés completos;
- margens seguras em todos os lados;
- arma/foco/equipamento principal integral sempre que possível.

## 4.2 Escala vertical — regra global

A Bíblia Técnica permite normalmente **72–84% da altura do quadro** para a figura. Para lotes temáticos, este documento fecha um alvo operacional mais estreito para reduzir deriva:

- **alvo preferencial de catálogo:** aproximadamente **76–80%** da altura do quadro, medido do topo natural da cabeça/cabelo até a sola do pé mais baixo;
- **faixa operacional aceitável:** **72–82%** quando pose, arma, cabelo, chapéu ou constituição justificarem;
- **83–84%:** apenas exceção deliberada de silhueta, nunca default de geração;
- acima de 84% ou abaixo de 72%: reprovar salvo Fonte Especializada explícita.

A arma longa, arco, cajado ou adereço não deve obrigar o corpo a ficar minúsculo; ajustar composição e ângulo para preservar o tamanho corporal do catálogo.

## 4.3 Padrão de enquadramento

A imagem deve manter:

- respiro claramente visível acima da cabeça;
- pés totalmente visíveis e assentados no terreno;
- chão suficiente para dar peso físico ao personagem;
- margens laterais que não comprimam escudo, arma, arco, cajado ou capa;
- eixo cabeça–tórax–quadril próximo do centro visual;
- personagem dominante, **porém não gigante**;
- ambiente ainda legível como contexto.

## 4.4 Câmera

Padrão para skins:

- distância média de câmera;
- perspectiva neutra ou levemente dinâmica;
- leitura de corpo inteiro prioritária;
- câmera à altura aproximada do torso/peito ou próxima da linha natural de observação;
- pequena variação de altura é permitida para composição, sem transformar a arte em pôster heroico.

Evitar:

- grande-angular aparente;
- câmera excessivamente próxima;
- ângulo muito baixo de “herói gigante”;
- vista aérea extrema;
- foreshortening forte;
- braço, perna, arma ou escudo projetados para a lente de modo a aumentar artificialmente o tamanho da figura;
- pose em que um pé avançado ocupe área desproporcional do primeiro plano.

## 4.5 Coerência entre assets

Em um mesmo lote:

- diferenças reais de altura/constituição podem existir, mas **não podem parecer diferenças de zoom**;
- personagens altos continuam altos por proporção anatômica, não por ocupar mais canvas;
- personagens robustos ganham massa horizontal, não escala de câmera maior;
- personagem esguio não deve ser afastado da câmera só para parecer menor;
- Classes com equipamento volumoso não recebem automaticamente enquadramento mais fechado.

Ao comparar o lote em grade, nenhuma imagem deve parecer claramente “zoomada” ou “miniaturizada” sem motivo explícito.

---

# 5. BENCHMARK VISUAL E CALIBRAÇÃO DE LOTE

Antes de produzir uma nova leva grande:

1. selecionar entre **6 e 10 skins já aprovadas** que representem o padrão atual do jogo;
2. usar essas imagens como **benchmark de tamanho de tela, densidade de pixel art, contraste e relação personagem/fundo**;
3. gerar um pequeno lote de calibração antes da produção completa;
4. comparar em grade/contato visual;
5. somente depois travar a produção do restante do lote.

Para um lote de 60 assets, recomenda-se calibrar no mínimo:

- 1 Sentinela;
- 1 Errante;
- 1 Vigia;
- 1 Classe extraordinária;
- 2 combinações adicionais cobrindo constituições/alturas diferentes.

Se o teste apresentar deriva de escala, câmera ou cenário, corrigir **o padrão do prompt/matriz antes** de continuar a produção em massa.

---

# 6. IDENTIDADE RACIAL EM SKINS TEMÁTICAS

## 6.1 Regra obrigatória

A skin não pode depender de texto, cor de roupa ou adereço para comunicar Raça. Na v1.1, a anatomia racial v2.0 é prioritária: chifres Hemários, orelhas Alvoranas, conjunto auricular/ocular Velado e densidade/dentição Cinérea não podem ser apagados pela temática.

Cada prompt individual de nova leva temática deve explicitar, quando a Matriz/Fonte possuir esses dados:

- profundidade e subtom natural de pele;
- cor e textura de cabelo;
- penteado funcional da imagem específica;
- cor dos olhos;
- estrutura/traços faciais relevantes;
- constituição corporal;
- pelo menos um marcador anatômico diagnóstico obrigatório da Raça quando aplicável, mais marcadores fenotípicos secundários;
- sinais individuais, quando definidos.

## 6.2 Iluminação não muda fenótipo

O prompt deve distinguir explicitamente:

- pigmentação natural;
- luz quente/fria do ambiente;
- lama, cinza, fuligem, umidade, sangue, poeira ou musgo superficial.

Exemplo de regra:

> “A luz âmbar pode aquecer highlights, mas não deve trocar o subtom natural da pele nem fazer um Velado parecer Hemário.”

## 6.3 Cabelo e variedade

Penteados podem variar entre skins temáticas desde que:

- permaneçam dentro da faixa racial/individual;
- não troquem textura natural sem justificativa;
- sejam funcionais para a Classe, clima e tema;
- não façam a pessoa parecer outra identidade por acidente.

Evitar repetir o mesmo penteado em todo o lote.

---

# 7. IDENTIDADE DE CLASSE E ARMAMENTO

## 7.1 Regra-base

Sem Fonte Especializada autorizando exceção, usar as assinaturas vigentes:

- **Sentinela:** arma de uma mão + escudo visível;
- **Errante:** duas armas curtas visíveis;
- **Vigia:** arco ou besta;
- **Tecelão:** arma-foco de Trama claramente técnica;
- **Oráculo:** arma-foco oracular/simbólica;
- **Luminar:** cajado/bastão de combate-foco.

A assinatura visual não cria regra mecânica de equipamento.

## 7.2 Variedade interna

Uma skin temática pode variar:

- modelo exato da arma dentro da família autorizada;
- posição da arma;
- estado ativo/passivo;
- bainha, suporte, aljava, foco e acessórios;
- proporção entre couro, tecido, malha e metal;
- arquitetura do torso e distribuição de equipamento.

Não variar a ponto de apagar a Classe.

## 7.3 Fonte Especializada de Aparência

Uma Aparência específica pode ampliar famílias de armamento ou criar exceções cosméticas, como ocorre em `Errante das Cinzas`.

Essas exceções:

- valem somente para a Aparência declarada;
- devem ser registradas em Fonte Especializada;
- não retroagem para a assinatura global de Classe;
- não criam proficiência ou loadout mecânico.

---

# 8. POSE, OLHAR E DINAMISMO DE CATÁLOGO

## 8.1 Estados oficiais

Usar os sete estados já reconhecidos pelo projeto:

1. Repouso;
2. Contemplação;
3. Vigilância;
4. Deslocamento;
5. Preparação;
6. Ação controlada;
7. Ação intensa.

Ação intensa deve continuar sendo minoria.

## 8.2 Vetor corporal

Variar deliberadamente:

- frontal;
- 3/4 esquerdo;
- 3/4 direito;
- perfil parcial esquerdo;
- perfil parcial direito;
- rotação contrária entre torso e cabeça;
- peso na perna dianteira/traseira;
- passo, subida, apoio, guarda ou repouso.

## 8.3 Cabeça e olhar

Para lotes grandes, declarar explicitamente em cada linha/prompt:

- direção da cabeça;
- direção dominante do olhar;
- relação entre olhar e arma/foco.

Regra de diversidade de produção para lotes de aproximadamente 60 assets:

- não repetir automaticamente a mesma direção dominante em assets consecutivos;
- evitar mais de duas imagens consecutivas com o mesmo vetor principal;
- em qualquer janela de seis assets, buscar pelo menos quatro vetores distintos de cabeça/olhar quando a matriz permitir;
- não permitir que “3/4 olhando para a direita” se torne pose default da ferramenta.

Essa regra generaliza o controle de composição que se mostrou eficaz na Fonte Especializada `Errante das Cinzas`.

---

# 9. FUNDO: REGRA GLOBAL

## 9.1 Fórmula

Para skins temáticas com contexto regional:

`REGIÃO/APARÊNCIA + FUNÇÃO ESPACIAL DA CLASSE + MOTIVO RACIAL COMPATÍVEL + VARIAÇÃO DE SUBCENÁRIO`

A Região/Aparência deve dominar quando a arte representa um ambiente real.

## 9.2 Fundo subordinado

O fundo precisa:

- ter contraste local e microdetalhe menores que o personagem;
- usar 1–3 formas ambientais reconhecíveis em vez de competir com a figura;
- contextualizar sem transformar a skin em concept art de cenário;
- evitar batalhas completas, multidões ou Chefes escondidos ao fundo;
- respeitar o gate de spoiler.

## 9.3 Motivo racial não é geografia automática

Os fundos de herança racial são motivos históricos/evocativos, não autorização para transplantar Locais raciais para qualquer Região.

Portanto:

- um Hemário nos Vales **não exige** uma instalação Hemaris literal ao fundo;
- um Alvorano nos Vales **não exige** um terraço civil pré-Ruptura específico;
- um Velado nos Vales **não exige** um umbral “do povo Velado”;
- um Cinéreo nos Vales **não exige** arquitetura dos Altos Cinéreos;
- um Remanescente nos Vales **não exige** um assentamento reconstruído dominante.

Quando o motivo racial literal inventaria geografia ou Lore, transferir a herança para:

- organização do equipamento;
- reparos;
- materiais pessoais;
- distribuição de acessórios;
- pequenos padrões estruturais não geográficos;
- gestual e solução funcional do personagem.

## 9.4 Função espacial da Classe

O fundo pode apoiar a Classe sem se repetir:

- **Sentinela:** gargalo, passagem defensiva, ruína estreita, barricada mínima, parapeito;
- **Errante:** bifurcação, trilha partida, passagem lateral, ponte, mudança de nível;
- **Vigia:** mirante, borda elevada, linha longa de visão, passarela alta;
- **Tecelão:** junta estrutural, reparo de campo, ruína técnica, ponto de manutenção;
- **Oráculo:** encruzilhada, marcadores de rota, caminhos divergentes, umbral funcional;
- **Luminar:** abrigo de estrada, posto de recuperação, braseiro funcional, área de apoio pequena.

Essas funções não obrigam um único Local ou a repetição do mesmo posto em todas as skins.

---

# 10. DIVERSIDADE DE CENÁRIOS DENTRO DE UMA REGIÃO

## 10.1 Assinatura fixa + subcenário variável

Uma coleção regional deve funcionar como:

> **mesma Região, muitos trechos do caminho.**

Manter constante:

- paleta regional;
- clima;
- materiais;
- vegetação/geologia;
- arquitetura compatível;
- tipo de desgaste;
- lógica de iluminação;
- fantasia central da Região.

Variar:

- Local ou microbioma;
- terreno;
- altura/profundidade;
- densidade de vegetação;
- quantidade de ruína;
- presença/ausência de estrutura humana;
- direção do caminho;
- foreground/midground;
- hora/luz compatível;
- chuva, névoa, vento, água ou cinza quando autorizados;
- lado do ponto de interesse.

## 10.2 Matriz ambiental de lote

Toda leva regional grande deve possuir uma **matriz de fundo** antes da geração em massa.

Campos mínimos:

- ID do asset;
- Região;
- Local/microbioma ou vinheta regional;
- função espacial da Classe;
- terreno;
- estrutura principal;
- elemento natural principal;
- clima/atmosfera;
- luz;
- enquadramento do fundo;
- restrição de spoiler.

## 10.3 Distribuição

Para lote de aproximadamente 60 assets:

- usar pelo menos **4–6 famílias ambientais** quando a Região possuir variedade canônica suficiente;
- não usar o mesmo Local/microcenário como default do catálogo;
- evitar repetir o mesmo subcenário em mais de dois assets consecutivos;
- apresentações masculina/feminina da mesma combinação devem variar enquadramento, ponto de interesse ou microcenário;
- o hub seguro **não deve dominar** um cosmético regional, salvo se a própria Aparência for explicitamente centrada no hub;
- como alvo editorial, hubs devem ocupar uma parcela minoritária do lote, idealmente não mais que cerca de um quinto quando houver alternativas canônicas suficientes;
- Masmorras, clímax e Locais tardios só entram quando o gate de conhecimento da Aparência permitir.

## 10.4 Local real versus vinheta regional

Quando a arte usa um Local nomeado:

- seguir `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS` e a Fonte Regional;
- não inventar arquitetura ou função ausente;
- não revelar elementos que o jogador ainda não deveria conhecer.

Quando não for necessário fixar um Local real:

- criar uma **vinheta regional derivada do cânone**, sem nomear ou inventar um novo Local de Mapa.

---

# 11. EXEMPLO DE APLICAÇÃO — VALES DOS ENFORCADOS

Este capítulo é exemplo operacional, não nova Fonte Regional.

A assinatura constante dos Vales permanece:

- desfiladeiros úmidos e profundos;
- raízes gigantes;
- árvores inclinadas;
- musgo;
- água escura;
- turfa;
- névoa baixa;
- passarelas;
- ruínas suspensas/aprisionadas;
- madeira escura/molhada;
- cinza de pedra úmida;
- verde escuro dessaturado;
- acentos discretos de resina/âmbar.

Fantasia central:

> **A natureza não reconquistou as ruínas; aprisionou-as.**

Para variar skins regionais sem perder a assinatura, distribuir o lote entre famílias como:

### Garganta dos Laços

- paredões altos;
- raízes descendo das paredes;
- restos de estrada;
- estruturas presas no alto;
- cordas e passagens improvisadas;
- leitura vertical estreita.

### Vigília do Vale

- uso minoritário no lote quando a Aparência for regional e não centrada no hub;
- madeira tratada;
- pedra;
- coberturas inclinadas;
- passarelas;
- drenagem;
- Braseiro protegido;
- sensação de ponto de sobrevivência, não vila em árvore.

### Mata Suspensa

- árvores inclinadas;
- níveis verticais;
- raízes formando passagens;
- troncos sustentando ruínas;
- passarelas naturais e artificiais;
- estruturas acima e abaixo do personagem.

### Baixios Enredados

- água escura;
- turfa;
- juncos;
- raízes submersas;
- vegetação fechada;
- terreno baixo e encharcado.

### Claustro das Raízes

- arquitetura asteriana comprimida;
- pedra antiga ainda discernível;
- raízes atravessando estrutura;
- sensação de pressão e confinamento.

### Berço / Masmorras / conteúdo tardio

Somente usar quando o gate narrativo e o momento de obtenção da Aparência permitirem. Se houver dúvida, não usar; preferir uma vinheta regional segura.

A coleção deve parecer uma travessia pelos Vales, **não sessenta personagens diante do mesmo posto de madeira**.

---

## 11.5 Nomenclatura global de arquivos temáticos

Para Aparências temáticas, usar pasta e basename com o slug do tema:

```text
<nome_da_skin>/<nome_da_skin>_<classe>_<raca>_<masculino|feminino>.png
```

Regras: minúsculas, `snake_case`, sem acentos. Exemplos: `cinereo`, `hemario`, `tecelao`, `oraculo`. Esta convenção prevalece sobre exemplos históricos de basename curto dentro das Fontes Especializadas.

---

# 12. TRAJE TEMÁTICO E MATERIALIDADE

A Aparência temática deve ser reconhecível sem uniformizar todas as Classes.

Separar três camadas:

1. **Classe:** arquitetura do torso, proteção, liberdade de movimento, distribuição de equipamento, arma/foco;
2. **Tema/Aparência:** material, acabamento, desgaste, adaptações, elementos recorrentes;
3. **Região:** clima, sujeira, umidade, cinza, vento, calor, vegetação, lama ou corrosão.

Reprovar se as seis Classes de uma Raça parecerem o mesmo traje-base com a arma trocada.

Elementos recorrentes do tema podem existir, mas variar:

- comprimento de capa;
- posição de amarrações;
- distribuição de couro/tecido/metal;
- estado de desgaste;
- bolsas e suportes;
- proteção de pernas/braços;
- detalhes de fechamento;
- tratamento regional.

---

# 13. MODELO DE PROMPT PARA COPIAR E COLAR NO PROJETO

Todo prompt individual de produção futura deve começar com um bloco deste tipo:

```text
Antes de gerar, leia e respeite as fontes disponíveis nesta conversa/projeto, na ordem de autoridade vigente.

Use obrigatoriamente:
- SOURCE_AUTHORITY vigente;
- Fonte Regional vigente, se a skin for regional;
- ASTERION_LORE_BIBLE_CANON vigente;
- ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS vigente;
- ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS vigente;
- Fonte Visual Especializada desta Aparência, se existir;
- ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS quando o fundo representar a Região/Local;
- ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS vigente;
- ASTERION_MATRIZ_DE_PRODUCAO_VISUAL vigente quando houver linha correspondente.

Se alguma Fonte necessária não estiver acessível, não invente a lacuna como fato canônico.
```

Em seguida, o prompt individual deve explicitar:

- nome da Aparência;
- ID/nome do arquivo;
- Raça;
- Classe;
- apresentação;
- identidade fenotípica/individual;
- arma/foco;
- traje;
- estado de pose;
- direção de corpo/cabeça/olhar;
- escala/enquadramento;
- família ambiental/subcenário;
- assinatura regional;
- negativos específicos;
- checklist final.

---

# 14. QA INDIVIDUAL OBRIGATÓRIO

Reprovar a imagem se qualquer item crítico falhar:

1. Formato 1:1 correto.
2. Corpo inteiro, cabeça e pés intactos.
3. Escala dentro do padrão do catálogo; sem aparência de zoom acidental.
4. Câmera neutra; sem grande-angular/foreshortening dominante.
5. Anatomia humanoide íntegra.
6. Raça reconhecível sem texto.
7. Identidade individual preservada quando houver âncora.
8. Classe reconhecível em miniatura.
9. Arma/foco fisicamente coerente e legível.
10. Traje pertence à Classe e ao tema.
11. Pixel art nativa; sem acabamento liso moderno.
12. Região/Aparência reconhecível quando aplicável.
13. Fundo subordinado ao personagem.
14. Fundo não inventa Lore ou Local inexistente.
15. Nenhum spoiler visual indevido.
16. Pose/olhar não repetem mecanicamente o padrão recente do lote.
17. Fundo não é cópia quase idêntica de outro asset.
18. A skin continua parecendo parte do mesmo jogo e do mesmo catálogo.

---

# 15. QA DE LOTE

Além do QA individual, lotes grandes devem ser avaliados em conjunto.

Criar uma grade/contact sheet e verificar:

- uniformidade de tamanho de tela;
- distribuição de altura aparente;
- equilíbrio entre corpos altos, baixos, robustos e esguios sem mudança de zoom;
- diversidade de pose;
- diversidade de direção de olhar;
- distribuição de armas dentro das famílias autorizadas;
- variedade de cabelo e rosto;
- preservação das famílias raciais;
- variedade de subcenários;
- ausência de um único hub/ruína/skyline dominando o lote;
- consistência de paleta regional;
- consistência de pixel art;
- ausência de uma Classe inteira com o mesmo traje-base;
- ausência de uma Raça inteira com o mesmo rosto/penteado;
- nenhum asset claramente maior ou menor por erro de câmera.

Se a grade parecer uma sequência de variações do mesmo pôster, o lote ainda não está aprovado.

---

# 16. FLUXO PADRÃO PARA UMA NOVA APARÊNCIA TEMÁTICA

## Etapa 1 — confirmar cânone

Localizar:

- origem/recompensa da Aparência;
- Região e gate de progressão;
- Classes e Raças envolvidas;
- restrições narrativas;
- conteúdo visual permitido.

## Etapa 2 — criar Fonte Visual Especializada quando necessário

Para levas grandes, especialmente `5 Raças × 6 Classes × 2 apresentações`, criar:

`ASTERION_APARENCIA_<NOME>_FONTE_VISUAL_v1.0.md`

Ela deve fechar:

- identidade da coleção;
- materiais do tema;
- variedade de armamento permitida;
- distribuição de poses/olhares;
- matriz de fundos/subcenários;
- exceções explícitas ao padrão global;
- QA específico.

## Etapa 3 — construir matriz dos assets

Antes de gerar as imagens, cada asset deve possuir:

- ID;
- Raça;
- Classe;
- apresentação;
- idade aproximada;
- pele/subtom;
- cabelo;
- rosto/marcadores;
- corpo;
- pose;
- olhar;
- arma/foco;
- subcenário;
- arquivo final.

## Etapa 4 — calibrar

Gerar 6–10 assets de teste e conferir:

- escala;
- câmera;
- pixel art;
- leitura racial;
- leitura de Classe;
- assinatura temática;
- fundo.

## Etapa 5 — produção

Somente após calibração, produzir o restante do lote na ordem definida pela Matriz/Fonte Especializada.

## Etapa 6 — QA de lote

Avaliar contact sheet antes de considerar a coleção encerrada.

---

# 17. CONTINUIDADE E RETROATIVIDADE

Este padrão entra em vigor para:

- novas Aparências temáticas;
- novas versões ainda não fechadas de Aparências em produção;
- regenerações solicitadas explicitamente.

Não reabre automaticamente:

- assets antigos já aprovados;
- `Errante das Cinzas v1.2.2`;
- Aparências concluídas que não apresentem problema visual relatado.

Quando uma coleção antiga for revisitada, aplicar este padrão apenas se a revisão for deliberadamente aberta.

---

# 18. PRINCÍPIOS FINAIS

> **Mesma escala de jogo, não mesmo corpo.**

> **Mesma assinatura regional, não mesmo cenário.**

> **Mesma Classe reconhecível, não mesma pose.**

> **Mesma Raça reconhecível, não mesmo rosto.**

> **Mesmo tema, não mesmo traje.**

> **Asterion deve parecer um único jogo mesmo quando cada skin for produzida em um momento diferente.**

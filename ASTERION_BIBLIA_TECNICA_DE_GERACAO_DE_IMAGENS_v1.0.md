# ASTERION — BÍBLIA TÉCNICA DE GERAÇÃO DE IMAGENS v1.0

**Data de consolidação:** 2026-10-05  
**Escopo:** especificação técnica de produção, geração, revisão, pós-processamento e exportação dos assets visuais de Asterion  
**Uso principal:** transformar as Bíblias de Lore e Direção Visual em imagens coerentes entre si, reduzindo deriva estilística, erros anatômicos, artefatos de IA e inconsistência de pixel art

> Esta Fonte não cria Lore, mecânica, conteúdo regional, Raça, Classe, Caminho, criatura, Local ou cosmético. Ela define **como renderizar** aquilo que as Fontes autoritativas já definem. Em conflito de conteúdo, prevalecem `SOURCE_AUTHORITY.md`, Fonte Mestra, Fonte Regional, Fonte Visual/UI e a Bíblia visual especializada do assunto.

---

# 1. OBJETIVO

Asterion precisa parecer um único jogo mesmo quando seus assets forem produzidos em momentos diferentes, por prompts diferentes ou por ferramentas diferentes.

Esta Bíblia fecha:

- proporção e canvas de produção;
- linguagem técnica de pixel art;
- agrupamento de pixels e controle de borda;
- sombreamento, dithering, contraste e saturação;
- renderização de materiais;
- anatomia e integridade de mãos, membros e rostos;
- coerência de armas, focos e equipamentos;
- estados de pose;
- regras específicas de arco/besta;
- composição de personagens, criaturas e cenários;
- transparência e overlays;
- pós-processamento;
- nomeação de arquivos;
- QA visual antes de aprovação.

Não fecha:

- identidade visual de Raça/Classe/Caminho, que pertence à Bíblia Visual de Personagens;
- anatomia/ecologia de criaturas, que pertence à Bíblia de Bestiário Visual;
- arquitetura/bioma de cenários, que pertence à Bíblia de Ambientes;
- composição de tela do Bot, que pertence à Fonte Visual/UI.

---

# 2. ORDEM DE USO PARA PRODUÇÃO

Para qualquer asset, aplicar na seguinte ordem:

1. identificar o conteúdo canônico na Fonte Mestra/Regional;
2. consultar a Bíblia de Lore quando houver origem, cosmologia ou spoiler envolvidos;
3. consultar a Bíblia visual especializada:
   - humanoide → Personagens/Raças/Classes/NPCs;
   - criatura → Bestiário Visual e Biomas;
   - ambiente → Ambientes, Locais e Masmorras;
4. consultar a Fonte Visual/UI quando a imagem pertencer a uma tela específica;
5. aplicar esta Bíblia Técnica para renderização, composição e QA;
6. aplicar a Matriz de Produção Visual quando existir uma atribuição concreta para aquele asset.

A Matriz de Produção Visual não pode contradizer nenhuma Fonte acima.

---

# 3. IDENTIDADE TÉCNICA GLOBAL

Toda imagem de Asterion deve perseguir simultaneamente:

- dark fantasy medieval;
- decadência e materialidade;
- estética de fim da era 16-bit / início da era 32-bit;
- pixels deliberadamente visíveis;
- silhueta legível em tela pequena;
- formas reconhecíveis antes de microdetalhe;
- materiais físicos antes de efeitos;
- fantasia contida;
- iluminação funcional;
- ausência de acabamento liso de pintura digital moderna.

Asterion **não usa pixelização como filtro decorativo**. A imagem precisa ser concebida como pixel art desde a leitura das formas.

Rejeitar imagens que sejam essencialmente:

- pintura digital suave com mosaico aplicado por cima;
- ilustração 3D/CGI com pixels falsos;
- anime com filtro retrô;
- concept art painterly reduzida;
- vetor com ruído pixelado;
- imagem excessivamente nítida e lisa que apenas simule baixa resolução.

---

# 4. FORMATOS E CANVAS DE PRODUÇÃO

## 4.1 Masters de produção

| Categoria | Proporção | Master recomendado | Formato |
|---|---:|---:|---|
| Personagem jogável | 1:1 | 1024×1024 | PNG |
| NPC humanoide | 1:1 | 1024×1024 | PNG |
| Criatura / Elite / Chefe | 1:1 | 1024×1024 | PNG |
| Região / Local / Masmorra / Braseiro / cena narrativa | 4:3 horizontal | 1024×768 | PNG |
| Mapa ilustrado | 4:3 horizontal | 1024×768 | PNG |
| Moldura cosmética | 1:1 | 1024×1024 | PNG RGBA |
| Overlay de tela | igual ao canvas-alvo | igual ao master-alvo | PNG RGBA |

Essas dimensões são **masters de produção**, não uma afirmação sobre a resolução lógica dos pixels do mundo.

## 4.2 Área segura

### Personagem/criatura 1:1

- manter cabeça e pés inteiros;
- preservar margem visual em todos os lados;
- figura normalmente ocupa aproximadamente 72–84% da altura;
- evitar armas, galhadas, asas ou acessórios tocando a borda sem necessidade;
- o eixo cabeça–tórax–quadril deve permanecer próximo ao centro em skins completas.

### Cenário 4:3

- nenhum elemento narrativo indispensável deve tocar os 4% externos do quadro;
- manter leitura clara de foreground, midground e background quando aplicável;
- quando a imagem for usada como fundo de personagem/perfil, preservar uma zona de contraste moderado no centro;
- não esconder informação importante em áreas que provavelmente receberão personagem, moldura ou recorte.

### Moldura

- exterior transparente;
- centro transparente;
- decoração concentrada em bordas/cantos;
- evitar invadir excessivamente a área útil do personagem;
- elementos de prestígio podem ser assimétricos, mas a leitura do perfil continua prioritária.

---

# 5. GRAMÁTICA DE PIXEL ART

## 5.1 Clusters

Priorizar **clusters de pixels** com intenção clara.

Usar:

- massas contínuas de sombra;
- bordas quebradas de forma deliberada;
- pixels isolados somente quando cumprem função de brilho, poeira, faísca ou textura específica;
- microdetalhe subordinado à forma maior.

Evitar:

- ruído de 1 pixel espalhado por toda a imagem;
- “sal e pimenta” em superfícies;
- textura igualmente intensa em pele, tecido, pedra e céu;
- bordas serrilhadas sem ritmo.

## 5.2 Anti-aliasing

O padrão é **sem anti-aliasing borrado**.

Permitido:

- anti-aliasing manual e localizado;
- uma transição curta de cor em curvas importantes;
- suavização mínima quando ela não destrói a leitura dos pixels.

Proibido:

- blur de borda;
- feathering amplo;
- glow usado para esconder serrilhado;
- interpolação bilinear/bicúbica em redimensionamento final de pixel art.

## 5.3 Dithering

Dithering é recurso pontual, não textura padrão.

Usos adequados:

- névoa;
- céu de transição curta;
- pedra muito gasta;
- metal oxidado;
- fumaça/cinza dispersa;
- passagem entre dois valores quando uma superfície exige granulação.

Evitar dithering forte em:

- pele;
- olhos;
- rosto;
- couro liso;
- superfícies pequenas;
- toda a imagem simultaneamente.

## 5.4 Gradientes

Gradiente suave contínuo deve ser evitado.

Preferir:

- bandas de valor;
- transições quebradas;
- massas de luz/sombra;
- dithering contido quando necessário.

---

# 6. VALOR, CONTRASTE E SATURAÇÃO

## 6.1 Hierarquia de valor

Cada asset precisa funcionar primeiro em valores, depois em cor.

Regras:

- silhueta principal distinguível do fundo;
- rosto/cabeça legíveis quando forem foco;
- arma/foco separado do corpo quando importante;
- pontos de luz não podem competir em quantidade com o foco principal;
- fundo recebe menos contraste local que o sujeito principal quando houver personagem/criatura.

## 6.2 Saturação

Asterion trabalha majoritariamente com saturação baixa a moderada.

Acentos saturados devem ser:

- pequenos;
- justificados por material, fogo, biologia, Trama, Presságio, Luz ou função regional;
- subordinados à composição.

Não usar saturação alta como atalho para “raridade”, “magia” ou “importância”.

## 6.3 Luz

Preferir:

- uma fonte dominante compreensível;
- luz secundária apenas quando justificada;
- sombras coerentes com a direção da luz;
- highlights concentrados em material apropriado.

Evitar:

- rim light genérico em todos os personagens;
- glow em todo objeto extraordinário;
- iluminação de estúdio moderna em cena medieval;
- luz contraditória apenas para recortar a silhueta.

---

# 7. RENDERIZAÇÃO DE MATERIAIS

## 7.1 Pele

- volumes do rosto e mãos legíveis;
- poucas faixas de valor bem controladas;
- textura não deve parecer pedra, plástico ou metal;
- tons de pele preservam diversidade definida na Bíblia de Personagens;
- fuligem, poeira, umidade ou sangue seco são camadas ambientais, não mudança racial.

## 7.2 Cabelo e barba

- tratar como massas antes de fios;
- mechas maiores definem volume;
- textura crespa/cacheada é construída por agrupamentos, não ruído aleatório;
- evitar fios individuais demais em resolução de pixel art;
- brilho deve seguir volume, não parecer plástico.

## 7.3 Tecido

- dobras principais indicam peso e direção;
- pano seco: borda mais rígida e poeira;
- pano encerado/úmido: massa mais pesada e brilho discreto;
- evitar tecido flutuando sem vento.

## 7.4 Couro

- menos brilho que metal;
- vincos próximos a articulações e fechos;
- desgaste em bordas e pontos de uso;
- não transformar todo couro em preto brilhante.

## 7.5 Metal

- highlights compactos;
- contraste mais duro que tecido/couro;
- ferrugem/oxidação localizadas;
- superfícies antigas continuam estruturais e não viram sucata amorfa;
- metal asteriano não parece cromado sci-fi.

## 7.6 Pedra

- massas grandes antes de rachaduras;
- rachaduras seguem tensão/idade, não padrão aleatório uniforme;
- ruína antiga conserva função arquitetônica legível;
- evitar cobrir toda pedra com runas.

## 7.7 Madeira

- veios sugeridos por poucos agrupamentos;
- madeira carbonizada usa preto/cinza com volume ainda legível;
- madeira úmida fica mais escura e pesada, não necessariamente verde.

## 7.8 Água, névoa e fumaça

- água: planos de valor e reflexo interrompido;
- névoa: reduz contraste, não apaga a cena inteira;
- fumaça/cinza: massas suaves construídas em pixels, sem brush airbrushed;
- nenhuma dessas camadas pode encobrir anatomia crítica sem motivo.

## 7.9 Fogo, brasa e Luz

- núcleo mais claro deve ocupar área pequena;
- bordas quentes se dissipam rapidamente;
- brasa é ponto de calor, não lava;
- Luz do Luminar não é automaticamente dourada, sagrada ou angelical.

---

# 8. ANATOMIA HUMANOIDE — QA OBRIGATÓRIO

A IA não pode ser autorizada a “resolver” anatomia por sugestão visual quando a imagem é usada como asset oficial.

## 8.1 Estrutura geral

Confirmar:

- uma cabeça;
- dois braços;
- duas pernas;
- ombros conectados corretamente ao tronco;
- cotovelos e joelhos em posições plausíveis;
- mãos conectadas aos punhos;
- pés conectados às pernas;
- nenhuma duplicação de membro causada por capa, sombra ou arma;
- roupa acompanhando o corpo sem atravessá-lo de forma impossível.

## 8.2 Mãos

Quando a mão estiver suficientemente visível:

- cinco dígitos no total, incluindo polegar;
- polegar em lado anatômico correto;
- dedos não duplicados;
- dedos não fundidos em massa sem motivo de perspectiva;
- empunhadura coerente com o objeto;
- palma e punho conectados.

Quando a pose tornaria a mão extremamente complexa e ela não for importante para a leitura, preferir:

- mão parcialmente coberta por luva/manopla;
- ângulo mais simples;
- objeto segurado por geometria limpa;
- pose diferente.

Não esconder erros anatômicos com fumaça, glow, partículas ou tecido aleatório.

## 8.3 Rosto

Confirmar:

- dois olhos quando ambos deveriam estar visíveis;
- nariz e boca alinhados com a perspectiva;
- orelhas coerentes com a cabeça;
- cabelo nasce do couro cabeludo e não atravessa face/olhos;
- barba conecta-se ao rosto;
- ausência de orelhas élficas em Velados;
- ausência de presas vampíricas raciais em Hemários;
- ausência de pele mineral racial em Cinéreos;
- ausência de halo/asas raciais em Alvoranos.

## 8.4 Pés

- ambos completos quando visíveis;
- contato claro com o chão;
- botas não podem fundir-se com pedra/sombra;
- direção dos pés precisa acompanhar a postura.

---

# 9. ESTADOS DE POSE

Usar os sete estados definidos na Bíblia Visual de Personagens:

1. Repouso;
2. Contemplação;
3. Vigilância;
4. Deslocamento;
5. Preparação;
6. Ação controlada;
7. Ação intensa.

## Regra de distribuição

Em uma coleção grande de personagens:

- não concentrar todos em Preparação/Ação;
- Repouso, Contemplação, Vigilância e Deslocamento devem aparecer com frequência real;
- Ação intensa deve ser minoria;
- classes diferentes podem compartilhar o mesmo estado sem repetir exatamente a mesma pose;
- duas versões cosméticas do mesmo personagem podem usar estados diferentes, mantendo a identidade física.

## Regra de legibilidade

A pose nunca pode sacrificar:

- anatomia;
- leitura racial;
- leitura da Classe;
- integridade da arma;
- centralização quando a arte for skin completa.

---

# 10. ARMAS, FOCOS E EQUIPAMENTO

Toda arma/foco deve parecer:

- completa;
- utilizável;
- equilibrada;
- conectada corretamente;
- compatível com metalurgia/artesanato de Asterion;
- segura na mão, bainha, suporte ou alça.

Rejeitar:

- lâmina sem cabo;
- cabo que atravessa a mão;
- duas pontas incompatíveis geradas por duplicação;
- escudo fundido ao antebraço;
- aljava atravessando capa;
- arma que muda de formato entre frente e fundo;
- foco flutuante sem motivo canônico;
- arma moderna.

## 10.1 Estado do equipamento

O equipamento pode estar:

- guardado;
- apoiado;
- carregado;
- preparado;
- em guarda;
- em uso.

A ferramenta não precisa dominar a imagem para comunicar Classe.

## 10.2 Escudos

- escudo é opcional para Sentinela salvo asset específico;
- mão/antebraço devem conectar-se ao sistema de pegada/alça;
- perspectiva do escudo deve coincidir com a postura;
- não ocultar metade do corpo em toda arte de Sentinela;
- não transformar escudo em símbolo religioso automático.

## 10.3 Arcos

### Estado relaxado

Permitido:

- arco nas costas;
- arco abaixado;
- arco apoiado no ombro;
- arco segurado lateralmente;
- arco durante deslocamento.

A corda continua existindo e conecta as duas extremidades.

### Preparação

Permitido:

- retirar flecha da aljava;
- posicionar flecha;
- encaixar nock;
- erguer o arco;
- ajustar postura.

### Tensionado

Obrigatório:

- uma corda contínua;
- corda presa às duas extremidades;
- uma flecha coerente;
- nock alinhado à corda;
- mão do arco segurando o grip;
- mão da corda puxando em direção plausível;
- flecha orientada para a linha de mira;
- membros do arco flexionados de maneira consistente.

Rejeitar imediatamente:

- duas cordas;
- corda atravessando torso/rosto;
- flecha sem ponta/haste contínua;
- flecha atravessando mão;
- arco com membros desconectados;
- aljava na frente da corda durante a puxada;
- flecha flutuando sem contato com arco/corda.

## 10.4 Bestas

- coronha, arco, corda e trilho precisam formar um único objeto;
- virote alinhado ao trilho;
- não transformar em rifle moderno;
- mecanismo medieval/fantástico plausível e simples.

## 10.5 Focos de Tecelão/Oráculo/Luminar

- nenhum foco é universal;
- objeto extraordinário deve parecer fisicamente segurável/transportável;
- efeitos surgem ao redor do gesto/foco, não substituem sua geometria;
- não criar cajado obrigatório para Tecelão;
- não criar bola de cristal obrigatória para Oráculo;
- não criar símbolo religioso obrigatório para Luminar.

---

# 11. PERSONAGENS E APARÊNCIAS

## 11.1 Identidade persistente

Quando duas imagens representam a mesma âncora de personagem em Aparências diferentes, preservar preferencialmente:

- estrutura facial;
- tom de pele;
- textura/cor de cabelo, salvo mudança cosmética intencional;
- idade aparente;
- constituição corporal;
- traços raciais centrais;
- gênero/apresentação escolhidos.

A Aparência pode mudar roupa, armadura aparente, acabamento, acessórios, desgaste e tema regional conforme a Fonte de Personagens.

## 11.2 Aparência não reescreve Classe

Uma Aparência deve adaptar-se à Classe sem apagar a Classe.

Exemplos:

- Errante das Cinzas + Sentinela continua lendo como Sentinela;
- Errante das Cinzas + Vigia continua lendo como Vigia;
- Errante das Cinzas + Tecelão não vira “mago de cinzas”.

## 11.3 Equipamento real

Quando o contexto da tela fizer a arma mecânica real importar, não usar uma Aparência fixa que induza leitura falsa do equipamento. Nesses contextos, a implementação pode:

- usar arte sem arma dominante;
- escolher variante compatível;
- renderizar arma separadamente no futuro;
- ou usar imagem contextual diferente.

Isso é uma restrição de apresentação, não criação de sistema novo.

---

# 12. CRIATURAS

Para criaturas, aplicar integralmente a Bíblia de Bestiário Visual antes desta seção.

Regras técnicas adicionais:

- contar membros quando a anatomia tiver número definido;
- patas devem tocar o chão ou superfície de forma plausível;
- mandíbula e olhos não podem se duplicar por textura;
- asas, galhadas, caudas e carapaças devem conectar-se ao corpo;
- não usar fumaça/sombra para esconder erro estrutural;
- Elite deve diferenciar-se por design, não apenas escala;
- Chefe precisa de silhueta reconhecível em miniatura.

---

# 13. CENÁRIOS

Para ambientes, aplicar integralmente a Bíblia de Ambientes antes desta seção.

## 13.1 Profundidade

Usar, quando aplicável:

- foreground com formas de enquadramento;
- midground com ação espacial principal;
- background com horizonte/arquitetura/bioma.

A profundidade deve surgir por:

- sobreposição;
- escala;
- contraste decrescente;
- saturação decrescente;
- névoa atmosférica controlada.

Evitar desfoque fotográfico intenso.

## 13.2 Perspectiva

- linhas arquitetônicas devem convergir de forma consistente;
- escadas, portas e passagens precisam ser utilizáveis;
- pilares não podem mudar de espessura sem motivo;
- pontes e plataformas precisam conectar-se a algo;
- ruína pode estar quebrada, mas sua função anterior ainda deve ser inferível.

## 13.3 Céu e clima

- céu serve ao bioma e à luz;
- não usar tempestade dramática por padrão;
- nuvens não precisam ter o mesmo contraste do foco principal;
- névoa deve obedecer profundidade.

---

# 14. TRANSPARÊNCIA E COMPOSIÇÃO

## 14.1 PNG RGBA

Usar transparência somente quando o asset tiver função real de composição:

- Moldura;
- Overlay;
- elemento isolado explicitamente reutilizável.

Não exigir transparência de todo personagem ou criatura se a arte oficial utilizar fundo contextual.

## 14.2 Alpha

- bordas transparentes precisam ser limpas;
- evitar halo branco/preto ao redor do recorte;
- nenhum pixel semitransparente amplo usado para fingir blur;
- sombras projetadas só permanecem quando fizerem sentido no contexto de composição.

## 14.3 Overlay

Overlay não substitui imagem-base.

- deve comunicar estado sem ocultar contexto;
- ornamento ocupa borda/áreas negativas;
- centro preserva leitura do evento;
- não adicionar texto dentro do PNG salvo decisão explícita de UI;
- canvas e proporção precisam coincidir exatamente com a imagem-base.

---

# 15. PÓS-PROCESSAMENTO

Permitido:

- limpeza manual de pixels;
- correção de anatomia localizada;
- ajuste controlado de valor/saturação;
- remoção de artefatos;
- reforço de cluster;
- conversão/exportação PNG;
- redimensionamento por nearest-neighbor quando a escala for inteira.

Evitar:

- filtro automático de pixelização como solução para arte lisa;
- sharpen forte;
- denoise que apague clusters;
- blur;
- interpolação bicúbica no master final;
- JPEG intermediário;
- chromatic aberration;
- film grain fotográfico;
- bloom genérico.

Se a geração-base não possui linguagem de pixel art suficiente, **regenerar** é preferível a tentar “salvar” com filtro.

---

# 16. ARQUITETURA DE PROMPT

Todo prompt oficial deve conter, nesta ordem lógica:

1. tipo de asset;
2. identidade canônica;
3. Região/contexto;
4. anatomia/silhueta;
5. Classe/Caminho ou função, quando aplicável;
6. roupa/equipamento/material;
7. estado de pose;
8. ação específica, se houver;
9. ambiente/fundo;
10. iluminação;
11. composição e centralização;
12. gramática de pixel art;
13. elementos obrigatórios;
14. proibições específicas;
15. negative prompt técnico global.

Não depender apenas de uma frase como “pixel art 16-bit”.

---

# 17. NEGATIVE PROMPT TÉCNICO GLOBAL

Acrescentar conceitualmente, adaptando à ferramenta:

- smooth digital painting;
- painterly brushwork;
- photorealism;
- 3D render;
- CGI;
- vector illustration;
- fake pixel filter;
- blurry edges;
- soft airbrush gradients;
- excessive bloom;
- chromatic aberration;
- film grain;
- JPEG artifacts;
- oversharpening;
- extra fingers;
- missing fingers;
- fused fingers;
- duplicated hands;
- duplicated arms;
- duplicated legs;
- malformed feet;
- disconnected limbs;
- broken weapon geometry;
- duplicated weapon;
- floating weapon parts;
- impossible grip;
- text;
- logo;
- watermark;
- UI baked into the art unless explicitly requested.

Somar a isso os negativos de Raça, Classe, criatura, Região ou Local definidos nas Bíblias especializadas.

---

# 18. NOMENCLATURA DE ARQUIVOS

Padrão de produção recomendado:

- letras minúsculas;
- `snake_case`;
- sem acentos;
- sem espaços;
- sem versão no nome do asset final de runtime quando o pipeline já possuir versionamento externo;
- nome deve indicar entidade antes de estado secundário.

Exemplos:

```text
mapa_terras_do_ocaso.png
cao_cinereo.png
vigia_partido.png
alda_veyr.png
moldura_pedra_fraturada.png
aparencia_errante_das_cinzas_remanescente_sentinela_masculino.png
```

Para arquivos de produção/revisão, sufixos temporários são permitidos:

```text
_rascunho01
_revisao02
_aprovado
```

Remover esses sufixos do nome final consumido pelo runtime, se a implementação esperar um identificador estável.

---

# 19. QA DE PERSONAGEM / NPC

Antes de aprovar:

- [ ] Raça correta sem caricatura?
- [ ] Classe/função correta?
- [ ] Estado de pose declarado e legível?
- [ ] Corpo inteiro quando exigido?
- [ ] Cabeça–tórax–quadril centralizados quando exigido?
- [ ] Exatamente dois braços e duas pernas?
- [ ] Mãos plausíveis e sem dedos extras/fundidos?
- [ ] Pés completos e apoiados?
- [ ] Rosto coerente?
- [ ] Cabelo/barba conectados corretamente?
- [ ] Arma/foco é um objeto completo?
- [ ] Empunhadura é plausível?
- [ ] Arco/besta passa o checklist específico, se presente?
- [ ] Roupa não atravessa corpo/arma?
- [ ] Materiais parecem diferentes entre si?
- [ ] Fundo está subordinado?
- [ ] Pixel art é estrutural, não filtro?
- [ ] Não há texto/logo/watermark?
- [ ] Não há spoiler?

Qualquer falha anatômica crítica reprova o asset mesmo quando a atmosfera estiver boa.

---

# 20. QA DE CRIATURA

- [ ] espécie/natureza canônica legível?
- [ ] número e conexão de membros corretos?
- [ ] silhueta reconhecível?
- [ ] habitat coerente?
- [ ] variante/Elite/Chefe não substitui identidade-base indevidamente?
- [ ] materiais biológicos/minerais coerentes?
- [ ] sem aura genérica de raridade?
- [ ] sem membros/olhos/bocas duplicados por erro?
- [ ] fundo subordinado?
- [ ] pixel art coerente com personagens/cenários?

---

# 21. QA DE CENÁRIO

Além do checklist da Bíblia de Ambientes:

- [ ] proporção 4:3 correta?
- [ ] perspectiva consistente?
- [ ] passagens/escadas/portas possuem função espacial?
- [ ] foreground, midground e background estão separados?
- [ ] clima não apaga a leitura?
- [ ] materiais possuem tratamento próprio?
- [ ] sem excesso de microtextura?
- [ ] sem gradiente liso dominante?
- [ ] sem runas/luzes genéricas?
- [ ] sem elementos cortados na borda que pareçam erro?
- [ ] nenhuma informação crítica está na área de risco da interface?

---

# 22. POLÍTICA DE REGENERAÇÃO

## Regenerar obrigatoriamente quando houver

- anatomia quebrada;
- mão importante com erro evidente;
- arma/foco estruturalmente impossível;
- arco/besta incoerente;
- identidade racial contraditória;
- identidade de Classe perdida;
- criatura transformada em outro arquétipo;
- cenário em Região errada;
- spoiler visual;
- linguagem visual claramente fora de Asterion;
- pintura lisa impossível de corrigir sem filtro agressivo.

## Pode ser corrigido manualmente quando houver

- 1–3 pixels isolados de ruído;
- pequeno artefato de borda;
- assimetria mínima não intencional;
- contraste local ligeiramente ruim;
- detalhe secundário simples desconectado;
- pequeno erro de transparência.

A correção manual não deve reescrever silenciosamente o design canônico.

---

# 23. MATRIZ DE PRODUÇÃO VISUAL

`ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v1.0.md` funciona como controle editorial/operacional.

Ela pode definir, para um lote específico:

- idade aparente;
- tom de pele;
- cabelo;
- constituição;
- estado de pose;
- visibilidade da arma/foco;
- variação de enquadramento;
- ordem de produção;
- estado de aprovação.

Essas atribuições **não transformam tais características em regra biológica de Raça ou Classe**. Elas existem para garantir diversidade, consistência e evitar repetição no conjunto oficial de assets.

---

# 24. FECHAMENTO

Com esta Bíblia Técnica, a produção visual de Asterion passa a separar claramente três perguntas:

1. **O que existe?** — Fontes canônicas e regionais.
2. **Como isso deve parecer?** — Bíblias visuais especializadas.
3. **Como isso deve ser renderizado e aprovado?** — esta Bíblia Técnica.

A frase-guia de produção é:

> **Pixels visíveis não bastam. A forma, a matéria, a anatomia e a função precisam sobreviver ao pixel.**

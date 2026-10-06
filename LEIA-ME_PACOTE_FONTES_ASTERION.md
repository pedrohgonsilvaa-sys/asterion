# ASTERION — LEIA-ME DO PACOTE DE FONTES

**Pacote:** Lore + Conteúdo + UI + Direção Visual + Produção Técnica  
**Data:** 2026-10-06

Este pacote serve como base autocontida para reconstrução, geração e revisão de imagens, skins de criaturas, personagens jogáveis, NPCs, Regiões, Locais, Masmorras, Molduras e demais assets de Asterion.

A regra central é separar claramente:

- **cânone e mecânica**;
- **conteúdo regional**;
- **apresentação player-facing**;
- **direção visual especializada**;
- **execução técnica da arte**;
- **controle editorial do lote de produção**.

A atualização de 06/10/2026 também fecha **famílias fenotípicas reconhecíveis das cinco Raças** e **fundos de herança / fundos Raça × Classe**, evitando que personagens de linhagens diferentes pareçam apenas variações do mesmo humanoide com outra roupa.

---

## Ordem de autoridade

1. `SOURCE_AUTHORITY_v1.4.9.md` — política formal de precedência das Fontes.
2. `ASTERION_GDD_Estrutural_v1.4.9_Fonte_Mestra.md` — sistemas, estruturas e regras globais.
3. Fontes Regionais FINAL — conteúdo específico de cada Região já fechada.
4. `ASTERION_UI_DECISOES_2026-10-05_FINAL_SYNC_v1.4.9_TDO_v1.0.13_VALES_v1.0.3.md` — apresentação, nomenclatura player-facing, iconografia e UX.
5. `ASTERION_LORE_BIBLE_CANON_v1.1.md` — verdade narrativa complementar, cosmologia e limites de revelação.
6. **Bíblias visuais especializadas por domínio**, no mesmo nível relativo e sem sobrescrever umas às outras fora de seu assunto:
   - `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v1.2.md` — humanoides;
   - `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.0.md` — criaturas e ecologia/biomas;
   - `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md` — cenários, arquitetura e espaços.
7. `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.0.md` — especificação de renderização, pixel art, anatomia técnica, canvas, armas, transparência e QA.
8. `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v1.1.md` — controle editorial do lote; **não é Fonte de cânone**.

Em qualquer conflito, não “misturar” as versões: corrigir o documento subordinado.

---

## Arquivos incluídos

- `SOURCE_AUTHORITY_v1.4.9.md`
- `ASTERION_GDD_Estrutural_v1.4.9_Fonte_Mestra.md`
- `ASTERION_UI_DECISOES_2026-10-05_FINAL_SYNC_v1.4.9_TDO_v1.0.13_VALES_v1.0.3.md`
- `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.13_FINAL.md`
- `ASTERION_CONTEUDO_VALES_DOS_ENFORCADOS_v1.0.3_FINAL.md`
- `ASTERION_LORE_BIBLE_CANON_v1.1.md`
- `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v1.2.md`
- `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.0.md`
- `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md`
- `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.0.md`
- `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v1.1.md`
- este arquivo.

---

## Para gerar um personagem jogável

Usar, nesta ordem prática:

1. Fonte Mestra — nomes/regras globais;
2. Fonte Regional quando a imagem tiver contexto regional específico;
3. Bíblia de Lore — verdade narrativa e spoilers;
4. Bíblia Visual de Personagens v1.2 — Raça, Classe, Caminho, famílias fenotípicas, fundos de herança, anatomia, presença, materiais e pose;
5. Fonte Visual/UI — formato de apresentação quando ligado a uma tela;
6. Bíblia Técnica — canvas, pixel art, anatomia técnica, arma/foco, exportação e QA;
7. Matriz de Produção — identidade concreta daquela âncora, quando existente.

Para **seleção de Raça**, exigir leitura fenotípica imediata: pelo menos 3 dos 4 eixos `pigmentação + cabelo + rosto + corpo/presença` devem estar no centro fenotípico da linhagem, e o fundo deve usar a família de herança correspondente. Para **Raça × Classe**, preservar pelo menos 2 desses 4 eixos mesmo quando equipamento e pose de Classe dominarem.

### Aparências e âncoras raciais

Uma Aparência cosmética não substitui Raça, Classe ou identidade física central. A Matriz v1.1 fecha dois conjuntos relacionados:

- **10 âncoras de seleção racial** — 5 Raças × 2 apresentações;
- **60 âncoras Raça × Classe** — 5 Raças × 6 Classes × 2 apresentações.

As 60 âncoras Raça × Classe são reutilizadas entre:

- Aparência padrão — 60 imagens;
- `Errante das Cinzas` — 60 imagens.

Com as 10 âncoras raciais, o total planejado desta frente passa a ser **130 imagens**, preservando 60 identidades-base entre as duas Aparências. Assets de seleção racial usam o centro fenotípico da linhagem e seu fundo de herança; skins Raça × Classe preservam pelo menos dois marcadores raciais fortes e combinam herança racial + função de Classe no fundo.

---

## Para gerar um NPC

Priorizar:

1. Fonte Regional, se o NPC já estiver definido;
2. Bíblia Visual de Personagens;
3. Bíblia de Lore para função/origem e spoilers;
4. Fonte Visual/UI se vinculado a uma tela;
5. Bíblia Técnica.

Não inventar Raça individual de NPC quando a Fonte não a declarou.

---

## Para gerar uma criatura

Priorizar:

1. Bestiário Visual e Biomas;
2. Fonte Regional correspondente quando Terras/Vales;
3. Lore Bible para natureza/origem e limites de spoiler;
4. Ambientes para o fundo/habitat, quando necessário;
5. UI apenas se a imagem estiver vinculada a uma tela específica;
6. Bíblia Técnica para renderização e QA.

Não transformar categoria, habitat, natureza ou função já fechados em “interpretação artística”.

---

## Para gerar um cenário, Local ou Masmorra

Priorizar:

1. Ambientes, Locais e Masmorras;
2. Fonte Regional correspondente quando Terras/Vales;
3. Lore Bible para função histórica e limites de revelação;
4. Fonte Visual/UI para formato de apresentação;
5. Bíblia Técnica para perspectiva, materiais, canvas, pixel art e QA.

A Masmorra deve continuar parecendo um lugar que existia por uma função antes de virar conteúdo de combate.

---

## Para gerar Moldura ou Overlay

Usar:

1. Fonte Mestra/Regional para saber se a recompensa/categoria realmente existe;
2. Fonte Visual/UI para função e apresentação;
3. Bíblia visual relevante para tema regional;
4. Bíblia Técnica para transparência, área segura, composição e exportação.

Não recriar categorias cosméticas removidas. A estrutura global vigente de Cosméticos é:

- Aparência;
- Título;
- Moldura.

---

## Regra de spoiler

Arte player-facing nunca deve revelar visualmente informação que a Campanha ainda não autorizou.

Uma imagem pode sugerir:

- antiguidade;
- função;
- desgaste;
- conexão incompleta;
- presença de algo não compreendido.

Não pode transformar segredo futuro em evidência explícita antes do gate narrativo.

---

## Estado das Bíblias Visuais

### Personagens v1.2

Fecha para direção visual:

- anatomia/presença das 5 Raças;
- famílias fenotípicas reconhecíveis e descendência mista;
- fundos de herança das 5 Raças;
- composição dos fundos Raça × Classe;
- leitura das 6 Classes;
- leitura dos 12 Caminhos;
- vestuário civil;
- adaptação material regional;
- NPCs de Terras do Ocaso e Vales dos Enforcados;
- Aparências cosméticas;
- estados de pose e intensidade;
- diversidade de gênero nas artes;
- composição, negative prompt e checklist de humanoides.

### Bestiário Visual v1.0

Fecha para produção:

- seis biomas;
- criaturas-base;
- Elites;
- criaturas de Masmorra;
- Chefes regionais;
- linguagem de construtos;
- Variantes;
- anatomia e leitura combatente.

### Ambientes v1.0

Fecha para produção:

- Regiões;
- materiais;
- arquitetura antiga e moderna;
- Locais;
- hubs;
- clímax;
- Masmorras;
- função histórica;
- progressão visual;
- limites de spoiler.

### Bíblia Técnica v1.0

Fecha a execução gráfica comum:

- masters 1:1 e 4:3;
- pixel clusters;
- anti-aliasing e dithering;
- materiais;
- luz/valor/saturação;
- mãos, membros, rosto e pés;
- integridade de armas/focos;
- regra de arco/besta;
- transparência/overlays;
- pós-processamento;
- nomenclatura;
- QA e regeneração.

### Matriz de Produção v1.1

Fecha o controle das 10 âncoras de seleção racial e das 60 âncoras Raça × Classe, incluindo famílias fenotípicas, diversidade interna, continuidade, pose, estado de arma/foco e os 30 fundos-base Raça × Classe.

---

## Documentos antigos de prompts

Arquivos antigos de prompts, planilhas de prompt, documentos `SKINS_*`, `PROMPTS_*` ou versões anteriores de reconstrução **não são Fontes autoritativas**.

Eles podem ser usados somente como referência histórica ou banco de ideias quando não houver conflito.

Quando divergirem das Fontes atuais, especialmente em:

- obrigatoriedade de escudo;
- estereótipos raciais;
- cor de pele/cabelo;
- pose de combate obrigatória;
- foco/cajado obrigatório;
- leitura religiosa do Luminar;
- “magia de cinzas” inventada;
- composição incompatível;

eles devem ser descartados e o prompt deve ser reconstruído a partir das Fontes vigentes.

---

## Regra final de aprovação

Uma imagem não é aprovada apenas porque está “bonita”.

Ela precisa passar simultaneamente por:

1. cânone;
2. identidade visual;
3. anatomia/integridade técnica;
4. coerência regional;
5. ausência de spoiler;
6. composição;
7. linguagem de pixel art;
8. função real dentro do Bot/jogo.

Falha crítica em qualquer uma dessas camadas exige correção ou regeneração.

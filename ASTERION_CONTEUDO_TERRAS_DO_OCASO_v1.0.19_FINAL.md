# ASTERION — Fonte de Conteúdo Regional
## Terras do Ocaso · v1.0.19 FINAL

**Data de consolidação:** 2026-11-26 (v1.0.19); v1.0.18 consolidada em 2026-11-14; v1.0.17 em 2026-10-23<br>
**Base:** `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_FINAL.md`<br>
**Escopo:** vertical slice / primeira jornada / Nv.1–10, com saída para Nv.11<br>
**Autoridade estrutural:** `ASTERION_GDD_Estrutural_v1.7.1_Fonte_Mestra.md`<br>
**Autoridade Visual/UI:** `ASTERION_UI_DECISOES_2026-11-26_FINAL_SYNC_v1.6.3_TDO_v1.0.19_VALES_v1.0.6.md`<br>

> Esta Fonte contém **conteúdo regional**, não redefine sistemas globais. Em conflito estrutural, prevalece a Fonte Mestra vigente. Em conflito de apresentação, prevalece a Fonte Visual/UI vigente.

> **Status FINAL (v1.0.19, 2026-11-26):** cópia versionada da v1.0.18 FINAL com a seção 33 revista por decisão do autor de 2026-11-26: a ação **Explorar** é substituída pelo menu **Desbravar**; **todos os Locais nascem descobertos** (fim do Prólogo; personagens existentes pela migration 0062), sem XP; o toque num Local do menu Desbravar leva o personagem até ele pelo hub e gera o evento do Local pelo Desbravar canônico; a Câmara do Poente é clicável e ainda não tem evento; o XP de descoberta de Local deixa de existir. O autor aceitou a nova meta de Exploração: `7.049 XP` = `7,21%` (item 5 de 33.14; 33.10). No Prólogo (§1.1), a Vitória passa a conceder 3 Coroas e a bolsa dos destroços concede 18 Coroas e 1 Resíduo do Ocaso. Nenhum outro conteúdo ou valor regional muda. Os trechos das seções 1 a 32 que citam descoberta por Explorar (por exemplo, §3.6 e §16) ficam superados pela seção 33 desta versão.

> **Histórico — Status FINAL (v1.0.18, 2026-11-14):** conteúdo regional fechado, aprovado pelo autor em 2026-11-14. Consolida a v1.0.17 FINAL com a navegação de mapa único (Refúgio do Ocaso como hub, descoberta de Locais só por Explorar), a remoção de travas de nível, o nível do inimigo igual ao do Local, a nova regra de XP de descoberta e as decisões do autor listadas em "Correções v1.0.18". **Precedência interna:** a **seção 33 (Fechamento v1.0.18)** e as notas marcadas "v1.0.18" prevalecem sobre qualquer trecho das seções 1 a 32 que as contrarie; trechos antigos que contrariam a v1.0.18 permanecem só como histórico de conteúdo e não valem como regra. Onde a v1.0.18 contraria a Fonte Mestra, vale o override registrado na seção 33.14 e em `docs/specs/RASCUNHO_OVERRIDE_FONTE_MESTRA_TDO_v1.0.18.md` (**registrado no `SOURCE_AUTHORITY.md`**, Sincronização 2026-11-14, Região 1). Esta revisão não altera recompensas de Missão, kits de criaturas, Masmorras (exceto o nível mínimo de entrada), Chefe, Provações de Classe, Ofícios, Feitos nem Códice.

> **Histórico v1.0.17:** substituiu integralmente a v1.0.16 FINAL e registrou exclusivamente que a Égide do Selo aplica Barreira de 8% do HP Máximo por 2T, CD4, máximo 2 usos.
> **Sincronização editorial 2026-10-13:** referência Visual/UI atualizada para o documento compatível com Vales v1.0.6; nenhuma regra ou conteúdo regional foi alterado.

**Correções v1.0.1:** kits numéricos dos 3 Elites e do Vigia Partido; pools completos de Caçada/Variantes; Desbravar completo; Provações de Classe completas; configuração implementável do Bestiário; aquisição determinística do Núcleo/Receita do Vigia Partido; auditoria de XP da Cripta corrigida.

**Correções v1.0.2:** consolidação implementável de P1 — Vozes na Estrada; sinais fixos da Etapa 2; Cão Cinéreo fixo no encontro roteirizado; recompensa própria do encontro explicitada como zero; derrota/retry/recovery; textos de transição; ordem dos registros permanentes; descoberta do Braseiro do Refúgio; idempotência e fronteiras técnicas de implementação.

**Correções v1.0.3:** prioridade implementável de IA do Corvo de Fuligem, Peregrino Calcinado e Alfa Cinéreo; Caçada em Grupo passa a herdar a referência global de nível da Fonte Mestra vigente; Receitas especiais de Masmorra permanecem no roll global salvo revelação direta explícita; autoridade documental e Visual/UI sincronizados. Nenhum valor numérico foi alterado.

**Correções v1.0.4:** formalização da conclusão do Prólogo em Vitória ou Derrota; Derrota conclui sem os 320 XP e ambos os resultados seguem ao Braseiro da Estrada; P1 inicia normalmente nos dois caminhos; auditoria de XP pós-P1 distingue os totais de 2.720 / 4.800 e 2.400 / 4.800; Feito **Cinzas na Estrada** permanece baseado na conclusão do Prólogo. Nenhum outro balanceamento ou conteúdo regional foi alterado.

**Correções v1.0.5:** fechamento implementável do gate Nv.3 e da disponibilidade de P2 com Alda; acesso contextual e descoberta permanente da Charneca na chegada; três pontos fixos de fuligem; Aranha de Cinza determinística no fluxo válido; economia, XP e Bestiário do encontro; Derrota, recovery e retry; Pedra Marcada e registro prudente no Códice; retorno a Oren/Alda; e momento de liberação de Caçada/Desbravar/Ronda local. Não altera os demais conteúdos, valores econômicos ou sistemas globais.

**Correções v1.0.6:** fechamento exclusivo da rota terrestre conhecida Refúgio ↔ Charneca; ação contextual de retorno após recovery da Etapa 3; navegação contextual de retorno após a Pedra Marcada; e acesso normal nos dois sentidos após a conclusão de P2. Não altera balanceamento, economia, encontros, recompensas ou conteúdo regional.

**Correções v1.0.7:** fechamento exclusivo da prioridade determinística de IA da Aranha de Cinza, dos pesos de seu pool temático de Materiais e do Material Básico do Cervo Escoriado, com pools válidos nos Locais em que cada criatura aparece salvo override futuro explícito. Nenhum valor global de chance ou quantidade, pool/peso de criatura ou balanceamento de stats/Artes foi alterado.

**Correções v1.0.8:** fechamento regional do recovery de PvE normal na Charneca; Braseiro do Refúgio como destino enquanto o Braseiro do Vento Morto não tiver sido descoberto validamente; prioridade do Braseiro do Vento Morto após a descoberta; integração desse Braseiro à rede permanente da Travessia, preservando a distinção e coexistência com a rota terrestre Refúgio ↔ Charneca. Nenhum valor numérico ou econômico foi alterado.

**Correções v1.0.9:** fechamento implementável de S2 — Os Nomes Esquecidos: requisitos, oferta/aceite, acampamento e três vestígios persistentes, encontro roteirizado com Peregrino Calcinado Nv.4 cuja conclusão exige Vitória, recovery/retry regional, fragmento como progresso de missão, Códice, recompensa única, abandono/reaceite e apresentação player-facing. Nenhuma regra global, valor numérico ou conteúdo de P3/Bosque foi alterado.

**Correções v1.0.10:** fechamento implementável de P3 — Sob Galhos Calcinados; entrada missionária no Bosque; fragmentos de construção; encontro pedagógico com Cervo Escoriado; escolha idempotente de Equipamento; conteúdo normal do Bosque; Carniçal, Mariposa e Viúva; pools de Caçada/Desbravar; rota Charneca ↔ Bosque; Travessia e Braseiro dos Galhos Mortos; recovery regional determinístico. Nenhum valor global de economia ou combate foi alterado.

**Correções v1.0.11:** fechamento implementável de S3 — Rastros sob os Galhos e P4 — Pedras que Ainda Vigiam; entrada missionária e normal nas Ruínas; Vigia Rachado roteirizado; Barreira inimiga por 2T; pools temáticos; Hunt, Explore e Round; Braseiro do Poente; rota Bosque ↔ Ruínas; Travessia e recovery determinístico. Nenhum valor global de economia foi alterado.

**Correções v1.0.12:** fechamento implementável das seis Provações de Classe do Círculo da Cinza, incluindo atributos das entidades de treinamento, ações determinísticas, parâmetros das ameaças Preparadas, camadas de proteção, manifestações, Eco Aliado, recuperação de treinamento, condições pedagógicas de conclusão, derrota/retry e persistência de etapa. Nenhuma Arte, Talento, Caminho, economia ou regra global foi alterada.

**Correções v1.0.13:** atualização exclusiva da distribuição cosmética dos 13 Feitos regionais, preservando requisitos e registros; catálogo consolidado em 4 Títulos, 3 Molduras e 1 Aparência.

**Correções v1.0.14:** S6 — Onde os Nomes Terminaram passa a usar o **Guardião do Último Rastro** como Chefe roteirizado Nv.10 em lugar do Custódio Sem Rosto; fecha seu kit já implementado, ausência de Cura/Barreira/invocações/adds/Variante, função de bloqueio do último registro e limites rígidos de revelação. O Custódio Sem Rosto permanece inalterado em Caçada, Desbravar, S5, Galerias e demais conteúdos onde já era válido. Direção visual sincronizada com `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md`.

**Correções v1.0.15:** sincronização estrutural com GDD v1.5.0: P1 e demais Missões a partir de P1 podem ser jogadas Solo ou em Grupo conforme regra global, com registros e rewards por personagem; S6 e o Guardião do Último Rastro aceitam Solo ou Grupo de 1–4. Os stats Solo, kit, identidade, recompensas, gates, narrativa e economia regional permanecem inalterados; scaling cooperativo usa exclusivamente a regra global de Chefe de Campanha.

**Correções v1.0.16:** fechamento exclusivo dos pools temáticos de Material Básico do Corvo de Fuligem (Resíduo do Ocaso · peso interno 100), do Alfa Cinéreo (Couro Escoriado · peso interno 100) e do Peregrino Calcinado (Ferro de Fuligem · peso interno 50 / Erva Cinzenta · peso interno 50). Os pesos selecionam somente a identidade de cada unidade após a aplicação das regras globais de chance e quantidade; nenhum outro valor econômico ou regra foi alterado.

**Correções v1.0.17:** duração de 2T registrada para a Barreira da Égide do Selo; mantém 8% do HP Máximo, CD4 e máximo 2 usos. Nenhum outro conteúdo ou valor regional foi alterado.

**Correções v1.0.18 (2026-11-14, aprovadas pelo autor):** navegação de mapa único e revisão de acesso, XP e nível. Texto normativo completo na **seção 33**. Resumo:

1. **Refúgio do Ocaso é o hub** (hub-and-spoke): liga a todos os Locais descobertos; todos voltam a ele; toda ida a um Local parte do Refúgio; ida e volta custam 0 Vigor, 0 Coroas, 0 XP. Rotas Refúgio↔Charneca, Charneca↔Bosque e Bosque↔Ruínas deixam de ser caminhos de jogo. Travessia dos Braseiros fica oculta nas Terras do Ocaso (regra global intacta). Braseiros seguem como checkpoint e recovery.
2. **Explorar** é ação própria no Refúgio (0 Vigor, anti-spam de 3 s): todo clique revela um Local não descoberto, sorteio uniforme entre Charneca, Bosque, Ruínas e Câmara do Poente. **Nenhum Local é liberado por Missão**; Missão pode exigir o Local já descoberto. "Local novo" sai dos pools de Desbravar.
3. **Travas de nível removidas** de Missões (P1 a P6, S1 a S6), Locais, Grandes Descobertas e rotas. Faixas viram "recomendada". Masmorras mantêm nível mínimo individual: Cripta do Ocaso Nv.4, Galerias do Vigia Nv.8.
4. **Desbravar sem recarga de 5 min e sem limite de 6 tentativas por Local por 60 min**; anti-spam técnico de 3 s e 1 tentativa em resolução. Vigor só quando o resultado paga economia.
5. **Nível do inimigo = nível do Local** (`max_enemy_level` de cada criatura), em Solo e em Grupo; `min(player_level, max_enemy_level)` removido (reescrita do §10.1). `unlock_level` não se aplica em Solo; em Grupo é requisito individual de cada membro.
6. **XP de descoberta de Local** = `FixedPercentXP(min(referência do Local, nível do personagem), 2,5%)`, só por Explorar, uma vez por Local. Exploração única: teto `8.242 XP` (8,43%), piso `7.529 XP` (7,70%).
7. **Ronda** em Grupo: a vitória manual libera para todos os membros que participaram da vitória. **PowerlevelFactor** se aplica à XP fixa de Missão em Coop de Chefe.
8. **Recovery** pelo Braseiro do próprio Local; Câmara do Poente (sem Braseiro) recupera no Refúgio do Ocaso. Ao abrir o jogo, o personagem aparece onde estava.
9. **Câmara do Poente (decisão de 2026-11-14, pendência 17):** fica no sorteio de Explorar com a mesma chance dos outros Locais; tem **dois textos de entrada** (antes e depois de P6), exibidos conforme P6 concluída ou não; a Missão só muda o texto, não libera o Local. P6 **não** descobre a Câmara (efeito removido). Textos reservados aos marcadores `[[TEXTO_CAMARA_PRE_P6]]` e `[[TEXTO_CAMARA_POS_P6]]` (narrative-designer).
10. **S4 e S5 em Grupo (decisão 8, 2026-11-14):** qualquer Vigia Rachado, Mariposa de Brasa ou Custódio Sem Rosto conta, como em Solo, sem checar o `unlock_level` de cada membro.
11. **BKP de Bestiário (decisão 9, 2026-11-14):** o BKP de investigação Desbravar e o de Habitat valem uma única vez (marco único) por criatura e por Local.
12. **Caçada em Grupo sem criatura elegível (decisão 11, 2026-11-14):** a Caçada não abre e a UI informa qual membro não cumpre o `unlock_level`.
13. Reescritas de consolidação: §10.1 (seleção, nível do inimigo) e §11.9 (recovery e texto herdado de P2). Texto herdado "requer P2 concluída" corrigido.

---

# 1. Identidade regional

**Região:** Terras do Ocaso<br>
**Faixa:** Nv.1–10<br>
**Saída:** Nv.11 para Vales dos Enforcados<br>
**Campanha:** As Cinzas da Ruptura<br>
**Chefe regional:** Vigia Partido<br>

Progressão temática:

`Estrada das Cinzas → Refúgio do Ocaso → Charneca da Fuligem → Bosque Calcinado → Ruínas do Vigia → Câmara do Poente`

A região ensina e testa progressivamente:

- Ataque Básico e Defender;
- primeira Arte da Classe;
- Caçada e Ronda;
- Desbravar;
- Veneno, Sangramento e Queimadura;
- telegraphs;
- Barreiras e DEF;
- Elites;
- duas Masmorras;
- Bestiário e Códice;
- primeiro Talento no Nv.5;
- segundo Talento, Provação e Caminho no Nv.10;
- primeiro Chefe regional.

## 1.1 Primeiro encontro do Prólogo — Cinzas na Estrada

O encontro tutorial do **🐺 Cão Cinéreo** é único, narrativo e não é uma Caçada econômica. A máquina pedagógica vigente — [Atacar], [Defender], primeira Arte, IA, atributos, dano, Recarga, RNG e HP — permanece integralmente inalterada.

### Resultado — Vitória

Vitória resolve o encontro e conclui o Prólogo. **[v1.0.19, decisão do autor de 2026-11-26]** Concede 320 XP e **3 Coroas**, nenhum Saque e nenhum Material, consome 0 Vigor e segue ao **🔥 Braseiro da Estrada**. As 3 Coroas são creditadas uma única vez por personagem. (v1.0.18: 0 Coroas.)

### Bolsa nos destroços [v1.0.19, decisão do autor de 2026-11-26]

Na cena **🔎 Entre os Destroços**, antes do combate, a bolsa presa sob a carroça concede **18 Coroas** e **1 Resíduo do Ocaso**, uma única vez por personagem, em Vitória ou em Derrota posterior. Não é Saque de combate e não muda o encontro do Cão Cinéreo.

### Resultado — Derrota

Derrota resolve definitivamente o encontro e conclui o Prólogo. Concede 0 XP (sem XP parcial ou fórmula normal de XP de inimigo), 0 Coroas, nenhum Saque e nenhum Material, consome 0 Vigor e segue ao mesmo **🔥 Braseiro da Estrada**. Não há penalidade econômica: Coroas, Equipamentos, Materiais, itens, XP prévio e progressão permanente são preservados.

TutorialXP = 320 somente em player_victory; TutorialXP = 0 em player_defeat. Esta regra não cria retry, recovery, nova identidade de encontro, reroll, segundo combate, softlock ou falha permanente.

Vitória e Derrota convergem para o estado já existente do Braseiro. [Descansar] e a restauração seguem a regra normal do Braseiro; a Derrota não restaura HP fora dele. Após a resolução, o combate deixa de ser Foreground. Reconnect, /start, /menu e troca de dispositivo retomam o estado pós-encontro, começando pelo Braseiro enquanto for a próxima etapa pendente; callbacks antigos não reativam a tentativa resolvida.

O encontro pode registrar normalmente a observação/evidência legítima do Cão Cinéreo no Bestiário, inclusive em Derrota, sem conceder separadamente o bônus genérico de 1% de XP da primeira observação.

P1 — **Vozes na Estrada** inicia normalmente após a conclusão do Prólogo em ambos os resultados; nenhum gate exige vitória no tutorial. Essa exceção se aplica somente ao encontro do Prólogo. P1 mantém sua própria regra: a Etapa 3 exige Vitória e conserva seu recovery e retry.

---

# 2. Progressão Nv.1–10

> **v1.0.18.** A coluna de nível desta tabela e as faixas de nível dos Locais (§3.1 a §3.5) são **recomendação de apresentação e referência de balanceamento**. Não são condição de acesso. O nível continua definindo XP e as Artes/Talentos de Classe (regras globais). **O nível do inimigo é o do Local/região e não escala com o jogador** (seção 33.5). Frases desta tabela como "elegível após descoberta" significam apenas que o Local ou a Masmorra precisa estar descoberto.

| Nv. recomendado | Conteúdo principal |
|---:|---|
| 1 | Prólogo; Tutorial; P1; Ataque Básico; Defender; primeira Arte; Cão Cinéreo |
| 2 | S1; Caçada/Ronda da Estrada já podem estar ativas; pool regional normal |
| 3 | P2; Charneca da Fuligem; primeiro Elite elegível |
| 4 | S2; segunda Arte da Classe; Veneno; Cripta do Ocaso elegível após descoberta |
| 5 | P3 + S3; primeiro Ponto de Talento; telegraphs |
| 6 | faixa sistêmica; Sangramento; Cripta/Bosque/Caçadas/Desbravar sustentam progresso |
| 7 | P4 + S4; terceira Arte da Classe |
| 8 | S5; Ruínas do Vigia; Galerias do Vigia elegível após descoberta |
| 9 | P5; quarta Arte da Classe; Custódio do Poente |
| 10 | P6 + S6; segundo Ponto de Talento; Provação; escolha de Caminho; Vigia Partido |
| 11 | saída regional para Vales dos Enforcados quando gates forem satisfeitos |

## Correção de gate inicial

**v1.0.18 — superada.** A Estrada das Cinzas nasce descoberta, com Caçada Manual e Desbravar liberados desde o início, sem depender de P1 concluída. A Ronda local desbloqueia após a primeira vitória manual válida naquele Local. Isso mantém o objetivo original: evitar hard lock de XP entre Nv.1 e Nv.2.

---

# 3. Locais

> **v1.0.18.** Onde as faixas abaixo dizem "Faixa", leia **"Faixa recomendada"** (sem efeito de acesso). Hub, Explorar e descoberta de Locais: seção 33.

## 3.1 Estrada das Cinzas

**Faixa recomendada:** Nv.1–3<br>
**Descoberta (v1.0.18):** nasce descoberta. Os demais Locais são revelados por Explorar no Refúgio (seção 33.2).<br>
**Função:** prólogo, primeiro Braseiro, tutorial de combate, primeira Caçada e primeira exploração sistêmica.

## 3.2 Refúgio do Ocaso

**Função:** hub seguro regional. **v1.0.18:** é também o **hub de navegação** da região (seção 33.1) e a tela onde ficam **Explorar** e a escolha de Local do **Caçar**.

Não possui pool normal de Caçada nem Ronda.

Sistemas apresentados/centralizados:

- NPCs regionais;
- Ofícios;
- Caminho/Provação quando elegível;
- serviços seguros compatíveis;
- Explorar, Caçar (escolha do Local), Masmorra (Covil), Missões e Personagem;
- ~~Travessia por Braseiros~~ (v1.0.18: oculta nas Terras do Ocaso, ver 33.4).

## 3.3 Charneca da Fuligem

**Faixa recomendada:** Nv.3–5<br>
**Função:** primeiro salto de dificuldade, Veneno, descoberta da Cripta.

## 3.4 Bosque Calcinado

**Faixa recomendada:** Nv.5–8<br>
**Função:** Sangramento, Queimadura, telegraphs, segundo estágio de exploração, Elite regional.

## 3.5 Ruínas do Vigia

**Faixa recomendada:** Nv.8–10<br>
**Função:** Barreiras, DEF, estrutura de guarda, segunda Masmorra, preparação do clímax.

## 3.6 Câmara do Poente

Local de clímax narrativo ligado ao P6 e à revelação controlada da Âncora do Poente.

**v1.0.18 [DECIDIDO 2026-11-14].** A Câmara é descoberta **somente por Explorar**, no sorteio de Locais não descobertos, com a **mesma chance** dos outros Locais. A Missão P6 **não** a revela: a Etapa 2 exige a Câmara já descoberta. A Câmara **não tem Desbravar, Caçada, Ronda, pool próprio nem Braseiro**; volta ao Refúgio do Ocaso. O Chefe Vigia Partido continua acessível apenas pela Missão P6. Referência de nível para XP de descoberta: 10.

**Texto de entrada em dois estados (decisão de 2026-11-14, pendência 17).** A Câmara tem dois textos de entrada. A Missão **só muda o texto exibido** (a UI lê se P6 foi concluída) e **não libera o Local**. O texto da descoberta por Explorar é neutro.

- **Antes da P6 concluída:** um recinto fechado e neutro, **sem a palavra "Âncora"** e **sem descrever a estrutura central**. Texto `[[TEXTO_CAMARA_PRE_P6]]`:
  > Um recinto fechado. As paredes são de pedra escura, sem marca nem janela. O ar está parado, e o pó no chão não tem pegadas. Nada aqui responde a quem chega. Nada aqui cede.
- **Depois da P6 concluída:** texto que usa o nome **Âncora do Poente**. Texto `[[TEXTO_CAMARA_POS_P6]]`:
  > O Vigia Partido não se levanta mais. Os registros chamam a estrutura de Âncora do Poente, e o Vigia a guardava. Outras Âncoras existiram. O recinto está calado, e ninguém sabe o que ela segurava.
- **Descoberta por Explorar (neutro):** texto `[[TEXTO_CAMARA_DESCOBERTA]]`:
  > Entre as pedras do Poente há um recinto fechado.

Os três textos acima foram escritos pelo narrative-designer em 2026-11-14 e são canônicos. Os identificadores entre colchetes duplos servem só de referência para a implementação.

## 3.7 Rota terrestre conhecida — Refúgio ↔ Charneca

> **v1.0.18 — SUPERADA como caminho de jogo.** As rotas Refúgio↔Charneca, Charneca↔Bosque e Bosque↔Ruínas deixam de existir como caminhos; ficam substituídas pelas ligações do hub (Refúgio ↔ cada Local descoberto, seção 33.1). Valem ainda: custo zero, 0 XP, sem encontro, sem nome próprio nem lore para a ligação. A restrição "só nos contextos autorizados da Missão", "uso normal depende de P2 concluída" e "a chegada de P2 descobre a Charneca" **não valem**: a Charneca é descoberta por Explorar. A ordem das etapas de P2 é garantida pelo estado da própria Missão. O texto abaixo é histórico da v1.0.17.

Existe uma conexão regional por **rota terrestre conhecida** entre **Refúgio do Ocaso** e **Charneca da Fuligem**. Não criar nome próprio ou lore para a rota. A chegada válida da Etapa 1 de P2 descobre a Charneca e torna conhecida a conexão física percorrida; não criar outro Local, Braseiro ou descoberta independente para representá-la. O conhecimento da rota não libera, por si só, o conteúdo normal da Charneca; o uso normal depende de P2 concluída.

Durante P2, a rota só é usada pelos contextos autorizados da própria Missão: chegada contextual da Etapa 1, retorno à Charneca no recovery da Etapa 3 e retorno ao Refúgio após a Pedra Marcada. Esses deslocamentos não permitem circulação livre que pule ou altere a ordem das etapas. Após P2 concluída, a conexão pode ser usada normalmente nos dois sentidos entre os Locais conhecidos.

A rota terrestre custa 0 Vigor e 0 Coroas, concede 0 XP, Material ou recompensa, não faz roll e não cria encontro por si só. A única exceção de encontro é a ação contextual de retorno à Charneca durante recovery da Etapa 3, que pode materializar diretamente o retry já autorizado pelas regras de P2. Deslocamento normal é bloqueado por Foreground incompatível; ações contextuais de P2 acima permanecem válidas nos estados previstos.

Essa conexão não é Travessia dos Braseiros, fast travel, teleporte, Braseiro, Masmorra, Desbravar, Caçada ou Missão nova. A rota terrestre permanece utilizável antes e depois da descoberta do Braseiro do Vento Morto. A Travessia dos Braseiros continua sendo um sistema separado que liga somente Braseiros permanentes descobertos; a descoberta do Vento Morto o integra à rede, sem substituir ou remover a conexão terrestre.

---

# 4. Braseiros permanentes

1. **Braseiro da Estrada** — Prólogo.
2. **Braseiro do Refúgio** — chegada ao Refúgio/P1.
3. **Braseiro do Vento Morto** — Desbravar na Charneca.
4. **Braseiro dos Galhos Mortos** — Desbravar no Bosque.
5. **Braseiro do Poente** — Desbravar nas Ruínas.

Braseiros de Masmorra não entram na Travessia permanente.

**v1.0.18.** Nas Terras do Ocaso a **Travessia dos Braseiros fica oculta** (o hub já leva a qualquer Local descoberto de graça; regra global intacta para outras regiões). Os Braseiros seguem como **checkpoint e recovery** e como conteúdo de Desbravar. A Câmara do Poente não tem Braseiro. Seção 33.4.

---

# 5. Missões

A região possui exatamente:

- **6 Missões Principais**;
- **6 Missões Secundárias**.

Offsets, XP, Coroas, Materiais e Equipamentos seguem integralmente a Fonte Mestra. Os roteiros abaixo são a versão oficial consolidada da vertical slice.

## 5.1 Resumo implementável

> **v1.0.18.** A coluna passa a **Nv. recomendado**; não é requisito. P6 inicia automaticamente quando P5 está concluída (sem Nv.10).

| ID | Nv. recomendado | Tipo | Título | Início | Local principal |
|---|---:|---|---|---|---|
| P1 | 1 | Principal | Vozes na Estrada | Automática após o Prólogo | Estrada / Refúgio |
| S1 | 2 | Curta | Luzes sob as Cinzas | Oren Cal | Estrada |
| P2 | 3 | Principal | Fuligem sem Fogo | Alda Veyr | Charneca |
| S2 | 4 | Padrão | Os Nomes Esquecidos | Oren Cal | Charneca |
| P3 | 5 | Principal | Sob Galhos Calcinados | Oren Cal | Bosque |
| S3 | 5 | Curta | Rastros sob os Galhos | Alda Veyr | Bosque |
| P4 | 7 | Principal | Pedras que Ainda Vigiam | Alda Veyr | Bosque / Ruínas |
| S4 | 7 | Padrão | Vigília sem Voz | Oren Cal | Ruínas |
| S5 | 8 | Padrão | A Luz que Não Aquece | Oren Cal | Ruínas |
| P5 | 9 | Principal | A Porta do Poente | Alda Veyr | Ruínas |
| P6 | 10 | Principal · Clímax | O Vigia Partido | Automática após P5 concluída | Câmara do Poente |
| S6 | 10 | Longa | Onde os Nomes Terminaram | Oren Cal | Ruínas |

### Dependências

Principais:

`Prólogo → P1 → P2 → P3 → P4 → P5 → P6`

**v1.0.18:** apenas encadeamento de Missões, sem nível. (Removida a frase "Cada Principal também respeita seu nível recomendado como gate normal da primeira jornada".)

Secundárias (sem nível):

- S1 exige P1 concluída.
- S2 exige P2 concluída.
- S3 exige Bosque descoberto e P3 ativa ou concluída.
- S4 exige P4 concluída.
- S5 exige P4 concluída.
- S6 exige S2 concluída e P5 concluída.

Removidos: Nv.2 (S1), Nv.4 (S2), Nv.5 (S3), Nv.7 (S4), Nv.8 (S5), Nv.10 (S6). As recompensas de §5.2 não mudam.

**Regra nova, vale para todas as Missões [DECIDIDO 2026-11-14]: Missão não revela Local.** O Local da etapa "Entrar em / Viajar até" precisa **já estar descoberto por Explorar**. A etapa conclui na chegada válida ao Local, que parte do Refúgio (hub). Se o Local ainda não foi descoberto, a etapa fica aguardando e a interface mostra que é preciso explorar. A Missão **não grava** `LocationDiscovery` e **não paga XP de descoberta**. Exceções: a Estrada nasce descoberta e o Refúgio é descoberto na Etapa 4 de P1 (tutorial). Onde os roteiros abaixo ainda dizem "a chegada descobre o Local" ou "registra a descoberta", **vale esta regra**. Seção 33.2.

Missões Secundárias podem ser abandonadas/reaceitas sem duplicar flags permanentes ou recompensas únicas.

---

## 5.2 Recompensas exatas

| ID | XP | Coroas | Materiais Básicos vinculados | Equipamento |
|---|---:|---:|---|---|
| P1 | 2.400 | 120 | 1 Ferro de Fuligem + 1 Couro Escoriado | — |
| P2 | 3.300 | 140 | 1 Ferro de Fuligem + 2 Ervas Cinzentas + 1 Resíduo do Ocaso | — |
| P3 | 4.400 | 180 | — | escolha entre 3 Raros Nv.5 |
| P4 | 5.700 | 250 | 2 Ferros de Fuligem + 2 Resíduos do Ocaso | — |
| P5 | 7.100 | 300 | 3 Ferros de Fuligem + 1 Resíduo do Ocaso | — |
| P6 | 14.220 | 500 | 4 Ferros de Fuligem + 4 Resíduos do Ocaso | escolha entre 3 Épicos Nv.10 |
| S1 | 1.140 | 60 | — | — |
| S2 | 2.695 | 120 | 1 Erva Cinzenta + 1 Resíduo do Ocaso | — |
| S3 | 1.760 | 90 | 2 Couros Escoriados | — |
| S4 | 3.990 | 150 | 2 Ferros de Fuligem + 1 Couro Escoriado + 1 Resíduo do Ocaso | — |
| S5 | 4.480 | 160 | 1 Ferro de Fuligem + 1 Erva Cinzenta + 2 Resíduos do Ocaso | — |
| S6 | 7.900 | 310 | 2 Ferros de Fuligem + 2 Couros Escoriados + 2 Ervas Cinzentas + 2 Resíduos do Ocaso | — |

Todos os Materiais de Missão acima são **vinculados**, conforme `1 UM = 2 Materiais Básicos regionais vinculados`.

### Escolha de P3

Escolher 1:

1. **Véu do Bosque** · Cabeça · Raro · `item_level 5` · `+0` · Vinculado ao Adquirir.
2. **Selo do Galho Morto** · Acessório · Raro · `item_level 5` · `+0` · Vinculado ao Adquirir.
3. **Relicário da Cinza Verde** · Artefato · Raro · `item_level 5` · `+0` · Vinculado ao Adquirir.

Nenhum possui efeito exclusivo fora do orçamento Raro normal do slot.

### Escolha de P6

Escolher 1:

1. **Guarda do Último Posto** · Torso · Épico · `item_level 10` · `+0` · Vinculado ao Adquirir.
2. **Selo do Poente** · Acessório · Épico · `item_level 10` · `+0` · Vinculado ao Adquirir.
3. **Relicário da Âncora Velada** · Artefato · Épico · `item_level 10` · `+0` · Vinculado ao Adquirir.

Nenhum possui proc ou poder acima do orçamento Épico normal.

---

## 5.3 P1 — Vozes na Estrada · Conteúdo Implementável

### 5.3.1 Escopo

Este bloco complementa exclusivamente **P1 — Vozes na Estrada**.

Não altera:

- as 7 etapas já aprovadas;
- recompensa da Missão;
- NPCs;
- efeitos permanentes já definidos;
- balanceamento global;
- progressão Nv.1→11;
- tutorial/prólogo;
- sistemas de Caçada, Bestiário, Vigor ou Saque.

**Início:** automático após conclusão válida do Prólogo/tutorial.

**Objetivo narrativo:** levar o personagem do fim do tutorial ao primeiro núcleo seguro e estabelecer Alda Veyr, Oren Cal e o Refúgio do Ocaso.

---

### 5.3.2 Etapas oficiais

A estrutura permanece exatamente:

1. Seguir pela Estrada das Cinzas.
2. Examinar dois sinais recentes de passagem.
3. Sobreviver a um encontro roteirizado simples da Estrada.
4. Alcançar o **Refúgio do Ocaso**.
5. Falar com **Alda Veyr**.
6. Conhecer **Oren Cal**.
7. Ativar o **Braseiro do Refúgio**.

Nenhuma etapa é adicionada, removida ou reordenada.

---

### 5.3.3 Etapa 1 — Seguir pela Estrada das Cinzas

#### Texto player-facing

*A chama deixada para trás desaparece pouco a pouco entre a fuligem. A Estrada das Cinzas segue adiante, irregular e silenciosa, mas desta vez há marcas recentes onde antes havia apenas abandono.*

A progressão leva diretamente aos dois sinais da Etapa 2.

Não existe combate nesta transição.

---

### 5.3.4 Etapa 2 — Dois sinais recentes de passagem

Os dois sinais são fixos e aparecem nesta ordem.

#### 5.3.4.1 👣 Pegadas na Cinza

##### Texto player-facing

**👣 Pegadas na Cinza**

*Marcas de botas cortam a fuligem em uma única direção. As bordas ainda estão nítidas demais para terem permanecido ali por muito tempo.*

##### Informação transmitida

O personagem pode concluir apenas que:

- alguém passou recentemente;
- seguia adiante pela Estrada.

Não identifica:

- Alda;
- Oren;
- Refúgio do Ocaso;
- quantidade exata de viajantes.

Ao examinar, o jogo deve persistir de forma idempotente que o **primeiro sinal recente de passagem foi examinado**.

##### ID técnico sugerido

`p1.sign.pegadas_na_cinza`

Uma implementação pode, por exemplo, representar o estado como:

`p1_recent_sign_1 = true`

Esses nomes são apenas sugestões de implementação e não constituem schema obrigatório da Fonte.

---

#### 5.3.4.2 🛞 Sulcos Recentes

##### Texto player-facing

**🛞 Sulcos Recentes**

*Duas marcas estreitas atravessam a cinza ao lado das pegadas. A fuligem ainda não voltou a cobrir completamente os sulcos deixados pelas rodas.*

##### Informação transmitida

O personagem pode concluir apenas que:

- algum tipo de carroça ou carga passou pela rota;
- as marcas seguem na mesma direção das pegadas.

Não cria item, recurso ou entrada de Códice.

Ao examinar, o jogo deve persistir de forma idempotente que o **segundo sinal recente de passagem foi examinado**.

##### ID técnico sugerido

`p1.sign.sulcos_recentes`

Uma implementação pode, por exemplo, representar o estado como:

`p1_recent_sign_2 = true`

Esses nomes são apenas sugestões de implementação.

---

#### 5.3.4.3 Conclusão da Etapa 2

A Etapa 2 conclui somente quando os **dois sinais obrigatórios** tiverem sido examinados validamente.

A implementação deve persistir esse progresso de modo que reconnect ou reconstrução da interface não obriguem o jogador a repetir sinais já validados.

Depois disso, a progressão dispara a entrada narrativa do encontro da Etapa 3.

---

### 5.3.5 Etapa 3 — Encontro roteirizado

#### 5.3.5.1 Criatura oficial

O encontro é **fixo**.

Criatura:

**🐺 Cão Cinéreo**

Configuração autoritativa:

- Cão Cinéreo;
- Nv.1;
- Categoria Comum;
- Solo;
- sem Variante;
- sem sorteio no pool normal de Caçada.

Não realizar seleção entre Cão Cinéreo e Corvo de Fuligem.

Não consultar o pool normal de Caçada da Estrada para selecionar o inimigo.

IDs, enums e nomes de campos internos ficam a critério da implementação.

---

### 5.3.6 Motivo da criatura fixa

O Cão Cinéreo já foi introduzido no Prólogo.

P1 utiliza a mesma espécie para transformar o conceito recém-ensinado em um combate normal, sem introduzir simultaneamente:

- nova criatura;
- novo bônus genérico de primeira observação;
- nova camada econômica.

Isso também torna P1 determinística e elimina divergência entre jogadores na primeira Missão Principal.

---

### 5.3.7 Entrada narrativa do encontro

Após examinar o segundo sinal:

*Os sulcos desaparecem onde a estrada se estreita entre pedras partidas. Antes que você possa seguir as marcas, um rosnado baixo rompe o silêncio.*

*Um Cão Cinéreo emerge da fuligem e fecha a passagem.*

O combate começa diretamente.

---

### 5.3.8 Diferença para o tutorial

Este encontro **não utiliza** o perfil especial do primeiro combate do Prólogo.

Não utiliza a máscara pedagógica.

Não obriga:

- Atacar;
- Defender;
- primeira Arte.

Desde a primeira oportunidade do jogador, a HUD utiliza o combate normal e apresenta todas as ações atualmente válidas.

O Cão utiliza seu perfil normal de conteúdo correspondente ao Nv.1.

Não reutilizar os multiplicadores especiais de HP/ATQ/DEF/AGI do Cão tutorial.

A intenção é:

**tutorial = aprender as ações**

**P1 = usar livremente aquilo que acabou de aprender**

---

### 5.3.9 Condição de conclusão da Etapa 3

Embora a redação da etapa permaneça:

**“Sobreviver a um encontro roteirizado simples da Estrada.”**

a condição autoritativa para avançar é:

**vitória do personagem.**

Derrota não conclui a etapa.

Após vitória válida, a Etapa 3 deve ser registrada como concluída de forma idempotente e a missão avança para:

**Etapa 4 — Alcançar o Refúgio do Ocaso.**

Uma implementação pode utilizar uma flag como:

`p1_step_3_complete`

mas o nome do campo não é normativo.

---

### 5.3.10 Recompensas do encontro de P1

Este encontro é um **combate roteirizado de Missão sem recompensa econômica própria**.

Uma implementação pode possuir internamente um perfil equivalente a:

`mission_scripted_no_economy`

mas esse identificador não é obrigatório.

O comportamento abaixo é a parte autoritativa.

#### XP normal de inimigo

`0 XP`

Não aplicar a conversão normal de XP de inimigos.

A vitória contra este Cão não acrescenta os aproximadamente `240 XP` de um Comum Nv.1.

#### Bônus de primeira observação do Bestiário

`0 XP adicional`

Este encontro de P1 **nunca funciona como nova fonte do bônus genérico de primeira observação**.

Se o Cão Cinéreo já estiver **Observado** pelo Prólogo, o conhecimento é simplesmente preservado.

Se um estado legado ou inconsistente exigir reparo do conhecimento já legitimamente adquirido, o reparo deve ser:

- idempotente;
- limitado ao estado de conhecimento que já deveria existir;
- sem concessão de XP.

P1 não concede novamente nem cria uma nova oportunidade para o bônus genérico de primeira observação.

#### Progresso de Bestiário

O encontro pode registrar normalmente evidências ou BKP que sejam legitimamente elegíveis pelas regras globais do Bestiário e ainda não tenham sido obtidos.

Isso não cria XP adicional por si só.

P1 não configura nenhum marco adicional de XP de Bestiário para este encontro.

#### Saque

`nenhum Saque`

#### Coroas do encontro

`0`

#### Materiais do encontro

`0`

#### Equipamento

`0`

#### Vigor

`0 consumido`

O encontro não é uma Caçada econômica.

---

### 5.3.11 Auditoria de XP preservada

Depois da conclusão integral de P1:

Tutorial, conforme o resultado do Prólogo:

- Vitória: 320 XP;
- Derrota: 0 XP.

P1:

2.400 XP

Encontro interno de P1:

0 XP

Bônus adicional de primeira observação:

0 XP

Totais válidos:

- Caminho com Vitória no Prólogo: 2.720 / 4.800 XP;
- Caminho com Derrota no Prólogo: 2.400 / 4.800 XP.

A auditoria Tutorial + P1 = 2.720 / 4.800 XP descreve especificamente o caminho com Vitória no Prólogo. No caminho com Derrota, a auditoria correspondente é Tutorial + P1 = 2.400 / 4.800 XP. P1 mantém sua recompensa de 2.400 XP; nenhum XP adicional é criado pelo encontro interno ou pela primeira observação.

---

### 5.3.12 Derrota na Etapa 3

Se o personagem for **Derrotado**:

1. o encontro atual termina como derrota;
2. a Etapa 3 permanece incompleta;
3. P1 continua ativa;
4. Etapas 1 e 2 permanecem concluídas;
5. nenhum efeito permanente das Etapas 4–7 é registrado;
6. nenhuma recompensa de P1 é entregue;
7. nenhum Vigor é consumido pelo encontro;
8. Consumíveis realmente utilizados permanecem consumidos.

Não existe falha permanente de P1.

P1 continua sendo uma Missão Principal e não pode ser abandonada.

---

### 5.3.13 Recovery após Derrota

Após a Derrota:

o personagem renasce no:

**🔥 Braseiro da Estrada**

já descoberto durante o Prólogo.

Aplicar as regras normais de Braseiro permanente:

- HP restaurado a `100%`;
- estados comuns de combate removidos;
- Vigor não restaurado;
- Consumíveis gastos não restaurados.

A missão permanece em:

**Etapa 3 — Sobreviver a um encontro roteirizado simples da Estrada.**

---

### 5.3.14 Retry

Ao retomar P1:

o personagem retorna ao gatilho narrativo da Etapa 3.

Uma nova tentativa materializa novamente:

**🐺 Cão Cinéreo · Nv.1**

Não existe novo sorteio porque o alvo é fixo.

A nova tentativa começa:

- personagem com o estado atual após recovery;
- Cão Cinéreo com HP integral;
- efeitos do encontro anterior encerrados;
- combate normal desde a primeira oportunidade.

A tentativa derrotada deve permanecer registrada como resolvida em derrota.

A nova tentativa recebe uma nova identidade de encontro vinculada à mesma Etapa 3.

Reconnect durante uma tentativa ainda ativa deve retomar o encontro existente em vez de criar outro.

O formato exato de `encounter_id`, chaves ou campos persistidos pertence ao schema técnico da implementação.

---

### 5.3.15 Etapa 4 — Alcançar o Refúgio do Ocaso

Após vencer o Cão:

#### Texto de transição

*Mais adiante, a estrada deixa de ser apenas ruína. Pedras empilhadas, madeira reaproveitada e pontos de luz surgem através da fuligem.*

*Não é uma cidade. Ainda assim, pela primeira vez desde que despertou na estrada, há sinais claros de que pessoas permanecem aqui.*

**🏚️ Refúgio do Ocaso**

---

### 5.3.16 Registro permanente da Etapa 4

No momento em que a chegada ao Refúgio é validada:

**Refúgio do Ocaso torna-se um Local descoberto permanentemente.**

Esse registro ocorre **na Etapa 4**, antes da conversa com Alda.

A descoberta é:

- permanente;
- idempotente;
- disponível para sistemas que consultem Locais conhecidos.

#### Representação técnica sugerida

Uma implementação pode representar esse estado de forma equivalente a:

`location.refugio_do_ocaso.discovered = true`

O identificador exato não é obrigatório.

A Etapa 4 então conclui.

---

### 5.3.17 Etapa 5 — Alda Veyr

Ao entrar no núcleo do Refúgio:

#### Texto de apresentação

*Uma mulher observa a estrada antes mesmo de olhar para você. Sua atenção passa primeiro pelas marcas da fuligem, depois por suas armas e só então pelo seu rosto.*

**Alda Veyr**

Preservar obrigatoriamente a fala oficial:

**Alda Veyr:**<br>
“Se chegou até aqui sozinho, já aprendeu a primeira regra do Ocaso: estrada nenhuma permanece segura só porque alguém a chamou de estrada.”

Após a fala, Alda contextualiza de forma breve que o Refúgio sobrevive mantendo rotas, recursos e vigias funcionando.

Não acrescentar título político formal.

---

### 5.3.18 Registro permanente da Etapa 5

Ao concluir a primeira conversa obrigatória com Alda:

**Alda Veyr torna-se uma Figura conhecida no Códice.**

Esse registro ocorre na:

**Etapa 5**

e é idempotente.

#### Representação técnica sugerida

Uma implementação pode utilizar algo equivalente a:

`codex.figure.alda_veyr.discovered = true`

sem obrigação de utilizar esse nome de campo.

---

### 5.3.19 Etapa 6 — Oren Cal

Depois de Alda:

#### Texto de transição

*Alda indica um homem cercado por folhas, tábuas riscadas e fragmentos trazidos das estradas. Ele organiza cada peça como se perder uma palavra fosse tão grave quanto perder uma pessoa.*

**Oren Cal**

Preservar obrigatoriamente a fala oficial:

**Oren Cal:**<br>
“Se ouvir nomes no vento, não os descarte depressa. Há coisas nestas terras que sobrevivem apenas porque alguém se lembra delas.”

Oren pode contextualizar brevemente sua função de registrar relatos, nomes e inscrições.

Não apresentar suas interpretações como verdades absolutas.

---

### 5.3.20 Registro permanente da Etapa 6

Ao concluir a apresentação obrigatória de Oren:

**Oren Cal torna-se uma Figura conhecida no Códice.**

Esse registro ocorre na:

**Etapa 6**

e é idempotente.

#### Representação técnica sugerida

Uma implementação pode utilizar algo equivalente a:

`codex.figure.oren_cal.discovered = true`

sem obrigação de utilizar esse nome de campo.

---

### 5.3.21 Etapa 7 — Braseiro do Refúgio

Após conhecer Oren:

#### Texto de transição

*No centro do Refúgio, uma chama resiste entre pedras marcadas pelo uso. Pessoas passam por ela sem cerimônia, mas nenhuma ignora completamente sua presença.*

**🔥 Braseiro do Refúgio**

*O calor é constante. Pela primeira vez, a estrada atrás de você parece ter um ponto de retorno.*

A Etapa 7 mantém o verbo player-facing:

**Ativar o Braseiro do Refúgio.**

A Etapa conclui quando o personagem interage validamente com o Braseiro e sua descoberta permanente é registrada.

Não é necessária uma segunda tela de confirmação depois do registro válido.

---

### 5.3.22 Registro permanente da Etapa 7

Na interação válida:

**Braseiro do Refúgio torna-se permanentemente descoberto.**

#### Representação técnica sugerida

Uma implementação pode utilizar algo equivalente a:

`brazier.refugio_do_ocaso.discovered = true`

O nome exato do campo não é normativo.

O Braseiro do Refúgio passa a ser um **Braseiro permanente conhecido e utilizável**, apto a:

- servir para descanso;
- servir para renascimento;
- integrar a Travessia dos Braseiros quando todos os requisitos gerais aplicáveis estiverem satisfeitos.

A “ativação” da Etapa 7 é o ato narrativo que registra essa descoberta permanente.

Ela **não reutiliza o estado técnico de checkpoint ativo de Masmorra**.

Não utilizar como requisito global de mundo um campo equivalente a:

`active = true`

destinado ao estado de checkpoint de run de Masmorra.

Esse registro ocorre antes do commit final da conclusão de P1.

---

### 5.3.23 Conclusão de P1

Depois que o Braseiro do Refúgio foi registrado como descoberto:

**P1 é concluída.**

A conclusão é atômica e idempotente.

Somente nesse momento são concedidas as recompensas já aprovadas:

- `2.400 XP`;
- `120 Coroas`;
- `1 Ferro de Fuligem` vinculado;
- `1 Couro Escoriado` vinculado.

Não alterar esses valores.

---

### 5.3.24 Desbloqueios concedidos na conclusão

> **v1.0.18.** A Estrada das Cinzas nasce descoberta, com Caçada Manual e Desbravar liberados (seção 33.2). Os desbloqueios abaixo deixam de depender da conclusão de P1 como **regra de acesso**; a conclusão de P1 não revela nem libera mais a Estrada. Se a UI deve esconder Caçada/Desbravar enquanto P1 está em andamento (fluxo do tutorial) é **LACUNA** (seção 33.15, item L3). O texto abaixo é histórico da v1.0.17.

No mesmo commit autoritativo de conclusão de P1:

- **Caçada Manual da Estrada das Cinzas é desbloqueada**;
- **Desbravar na Estrada das Cinzas é desbloqueado**.

Esses desbloqueios ocorrem:

**na conclusão da Etapa 7 / conclusão de P1**

e não antes.

Eles são válidos mesmo se o personagem ainda estiver no Nv.1.

#### Representação técnica sugerida

Uma implementação pode utilizar estados equivalentes a:

`hunt_manual.estrada_das_cinzas = unlocked`

`explore.estrada_das_cinzas = unlocked`

Esses identificadores não são schema obrigatório da Fonte.

---

### 5.3.25 Ronda da Estrada

P1 **não desbloqueia diretamente** a Ronda.

Após P1:

Caçada Manual está disponível.

A primeira vitória posterior em uma **Caçada Manual válida** na Estrada registra a familiaridade necessária.

Somente então:

**Ronda da Estrada é desbloqueada.**

O Cão roteirizado da Etapa 3 de P1:

**não conta como essa primeira vitória manual**, porque não é uma Caçada Manual.

Uma implementação pode representar esse unlock através de flag própria, desde que preserve exatamente esse comportamento.

---

### 5.3.26 Ordem exata dos efeitos permanentes

| Momento | Registro autoritativo |
|---|---|
| Etapa 4 · chegada | Refúgio do Ocaso descoberto |
| Etapa 5 · conversa concluída | Alda Veyr registrada no Códice |
| Etapa 6 · apresentação concluída | Oren Cal registrado no Códice |
| Etapa 7 · interação com Braseiro | Braseiro do Refúgio descoberto e utilizável |
| Conclusão da Etapa 7 / P1 | recompensa de P1 |
| Conclusão da Etapa 7 / P1 | Caçada Manual da Estrada desbloqueada |
| Conclusão da Etapa 7 / P1 | Desbravar da Estrada desbloqueado |
| Depois de P1, primeira vitória em Caçada Manual | Ronda da Estrada desbloqueada |

Todos os registros são idempotentes.

Reconnect, callback duplicado ou reconstrução de UI não podem:

- conceder novamente recompensa;
- registrar novamente descoberta;
- duplicar entrada de Códice;
- liberar Ronda antecipadamente.

---

### 5.3.27 Representação técnica recomendada do encontro

O bloco abaixo é **exemplo de representação técnica**, não schema obrigatório:

```text
mission = P1
step = 3

encounter_type = MISSION_SCRIPTED
enemy = CAO_CINEREO
enemy_level = 1
variant_roll = false
tutorial_mask = false
hunt_pool_roll = false
vigor_cost = 0

enemy_xp = 0
first_observation_bonus_xp = 0
loot = none
crowns = 0
materials = none
equipment = none

completion_condition = player_victory
defeat_advances_step = false
defeat_recovery = BRASEIRO_DA_ESTRADA

retry_enemy = CAO_CINEREO
retry_reroll = false
```

O Codex pode utilizar outros:

- nomes de campos;
- enums;
- IDs;
- estruturas de tabela;
- nomes de flags.

O comportamento obrigatório é:

- Cão Cinéreo fixo Nv.1;
- sem Variante;
- sem roll de Caçada;
- sem XP de inimigo;
- sem bônus genérico adicional de primeira observação;
- sem Saque, Coroas, Materiais ou Equipamento;
- sem Vigor;
- vitória necessária para avançar;
- derrota retorna ao Braseiro da Estrada;
- retry mantém a mesma criatura e não rerrola o encontro;
- reconnect não duplica tentativa ativa.

---

### 5.3.28 Resultado narrativo de P1

P1 termina com o personagem sabendo apenas que:

- existe um núcleo seguro chamado **Refúgio do Ocaso**;
- Alda Veyr coordena necessidades práticas e segurança;
- Oren Cal registra relatos, nomes e inscrições;
- outros sobreviventes/viajantes utilizam a Estrada;
- Braseiros permanentes podem servir como pontos seguros.

P1 não revela antecipadamente:

- Antigos Asterianos;
- Âncoras;
- Primeiro Selo;
- Convergência;
- Avesso;
- Desvelados;
- qualquer mistério reservado às missões posteriores.
---

## 5.4 S1 — Luzes sob as Cinzas

**Objetivo narrativo:** apresentar o primeiro mistério regional sem explicar sua origem.

**Giver:** Oren Cal.

### Etapas

1. Investigar três pontos marcados da Estrada.
2. Examinar cinzas sem fonte de calor recente.
3. Observar uma luz distante em uma ocorrência roteirizada.
4. Retornar a Oren.

Combate não é obrigatório. Se ocorrer encontro incidental, usa o pool normal do Local.

### Fala-chave

**Oren Cal:**<br>
“Luz é uma coisa simples quando há fogo. Quando não há, ela se torna uma pergunta.”

### Efeitos

- atualiza Estrada das Cinzas no Códice;
- pode registrar Trecho **Luzes na Estrada** caso ainda não tenha sido obtido por Desbravar;
- não revela causa, Âncora, Avesso ou qualquer conclusão cosmológica.

---

## 5.5 P2 — Fuligem sem Fogo

**Objetivo narrativo:** abrir a Charneca da Fuligem e introduzir as Marcas na Fuligem sem antecipar autoria, função ou explicação cosmológica.

**Giver:** Alda Veyr, no Refúgio do Ocaso.

### Disponibilidade e início

P2 fica disponível somente depois de **P1 concluída** (**v1.0.18:** sem exigência de nível; removidos "Nv.3 ou superior" e a frase sobre estado novo não começar no Nv.1 ou Nv.2). S1 não é requisito.

Antes dos requisitos não existe P2 ativa ou suspensa, progresso P2, recompensa reservada ou acesso à Charneca pela Missão. Quando elegível, a interação válida com Alda no Refúgio apresenta o contexto oficial e inicia P2 sem confirmação redundante; a Missão passa a `Em Andamento` na Etapa 1. A fala-chave está registrada ao final desta seção.

### Seis etapas oficiais

1. Viajar até a **Charneca da Fuligem**.
2. Examinar três pontos onde a fuligem aparece sem queima recente.
3. Derrotar um inimigo roteirizado da Charneca.
4. Examinar a **Pedra Marcada** da rota principal.
5. Levar um registro da marca a Oren Cal.
6. Reportar a situação a Alda Veyr.

São exatamente seis etapas. Deslocamentos entre Charneca e Refúgio são navegação/contexto dentro delas, não etapas adicionais.

### Etapa 1 — Charneca já descoberta e chegada (v1.0.18)

**v1.0.18 [DECIDIDO 2026-11-14].** A Etapa 1 **exige a Charneca já descoberta por Explorar**. Se não estiver descoberta, a etapa fica aguardando e a interface mostra que é preciso explorar (sem bloqueio sem saída: Explorar não falha). Com a Charneca descoberta, a Etapa 1 conclui na **chegada válida à Charneca, partindo do Refúgio (hub)**, com ação equivalente a `[Seguir para a Charneca]` (rótulo da Fonte Visual/UI; não usar `[Continuar]` genérico). **A chegada não descobre a Charneca nem grava `LocationDiscovery`**. Não existe "conexão terrestre física" a tornar conhecida: vale o hub (33.1). O trecho histórico a seguir da v1.0.17 ("descoberta na chegada", rota conhecida) **não vale**.

*(Histórico v1.0.17: "Antes da chegada válida, Charneca ainda não é Local conhecido… Na chegada, uma transição idempotente registra permanentemente o Local…".)*

### Etapa 2 — três Pontos de Fuligem

Existem exatamente três pontos fixos, persistentes e idempotentes, examináveis em qualquer ordem, apresentados como `Ponto de Fuligem · 1`, `Ponto de Fuligem · 2` e `Ponto de Fuligem · 3`, ou equivalente. Cada ponto tem identidade estável, não posição volátil de callback. Objetivo: `Examinar Pontos de Fuligem · 0/3` até `3/3`; reconnect mostra somente pontos pendentes.

Exames não concedem XP, item, Material ou economia, não criam três Entradas de Códice e não inventam lore sobre autoria, causa, magia, Âncora, Avesso ou origem da fuligem. O terceiro exame válido conclui a etapa e materializa diretamente o encontro da Etapa 3, sem confirmação.

### Etapa 3 — encontro roteirizado

**v1.0.18:** removido o texto "Todo fluxo novo válido ocorre em Nv.3+". Um personagem Nv.1 ou Nv.2 pode enfrentar a Aranha. O encontro é sempre **Aranha de Cinza · Nv.3**, fixa mesmo se P2 for iniciada por personagem de qualquer nível; não escala com o jogador. Configuração: categoria **Incomum**, perfil de Bestiário interno `RARE`, arquétipo **Controlador**, Solo, encontro roteirizado de Missão, sem Variante e `variant_roll=false`. Não sortear nem consultar o pool normal de Caçada, nem usar Cão, Cervo ou Elite. A IA usa a prioridade canônica de §8.4. O encontro roteirizado conserva sua exceção econômica: não concede Material, Coroas ou Saque de Caçada.

**Peregrino Calcinado** fica somente como fallback defensivo para estado legado/inconsistente em que a Aranha não seja elegível; não é alcançável por novo fluxo válido. O encontro roteirizado não usa roll, pesos ou Variante de Caçada.

#### Economia, XP e Bestiário

Entrada da Missão consome 0 Vigor. O encontro não usa perfil econômico de Caçada e concede 0 Coroas, nenhum Material, Saque ou Equipamento de Caçada. Em Vitória, aplicar a fórmula global normal de XP de inimigo com `enemy_level=3` e `CategoryMultiplier=1,35` (Incomum), além dos demais fatores globais pertinentes; não usar override de tutorial, tabela paralela de Caçada nem redução de Vigor. É conteúdo story/único, sem custo de Vigor.

Ao materializar e identificar legitimamente a Aranha pela primeira vez, podem ser registrados uma única vez a primeira Observação válida, Habitat da Charneca e primeiro contato/combate quando seus marcos globais forem validados. A primeira observação não depende de Vitória e conhecimento legitimamente registrado antes da Derrota permanece. Se ainda elegível, seu bônus global de primeira observação usa `FixedPercentXP` com `reference_level=3`: `1% × XP_ref(3)=1% × 6.600=66 XP`; pode ser concedido no momento da observação mesmo que a tentativa termine em Derrota. Reconnect/retry não repete esse bônus.

Somente Vitória registra primeira vitória e evidências cuja condição global exija Vitória. Derrota não concede XP de vitória do inimigo nem apaga conhecimento legitimamente observado antes dela. Demais BKP/evidências — Observação, primeiro combate, Arte/comportamento, Habitat e Missão — seguem suas condições globais normais. Consumíveis usados não são devolvidos.

#### Derrota, recovery e retry

Derrota resolve somente a tentativa. P2 continua ativa na Etapa 3; Etapas 1–2 e descoberta da Charneca permanecem concluídas; não há recompensa final ou recompensa econômica de Caçada, nem falha permanente.

Enquanto o Braseiro do Vento Morto não foi descoberto, recovery ocorre no **Braseiro do Refúgio** (prioridade por Local de §11.9), pelas regras normais: HP a 100%, estados comuns removidos, Vigor não restaurado e Consumíveis gastos não devolvidos. A tela de recovery oferece a ação contextual `[Retornar à Charneca]`, usando a rota terrestre conhecida, sem custo ou recompensa e sem criar etapa.

O commit válido de `[Retornar à Charneca]` atualiza o Local atual para Charneca e retorna diretamente ao gatilho da Etapa 3, materializando exatamente um retry autorizado com novo `encounter_id`, novamente Aranha Nv.3 sem Variante/reroll e HP integral; a tentativa anterior permanece Derrota. Não inserir confirmação redundante. Antes do retorno, reconnect reconstrói recovery no Refúgio com a ação; depois do commit, reconstrói Charneca e a tentativa correspondente. Callback duplicado/stale não viaja novamente nem cria outra tentativa. Reconnect durante tentativa ativa retoma o mesmo `encounter_id`. Não copiar perfil econômico especial de P1. Somente Vitória conclui a Etapa 3 e avança à Pedra, registra primeira vitória/evidências que dependam de vitória e concede XP normal de inimigo uma única vez. Observação e seu bônus são resolvidos no momento em que forem legitimamente obtidos, independentemente do resultado posterior. Callback stale/duplicado não repete efeitos.

### Etapa 4 — Pedra Marcada

Pedra Marcada é objeto/ponto de interesse da rota principal, não Local, sub-Local ou item. Exame válido conclui a etapa, registra evidência e cria/atualiza `Marcas na Fuligem` no Códice. Não concede XP de Desbravar, item ou Material e não consome o resultado único sistêmico de Desbravar. A descoberta de Desbravar Nv.4 `Pedra Marcada` continua elegível uma única vez e pode conceder os `193 XP` aprovados quando legitimamente obtida; representa investigação sistêmica mais profunda do ponto já conhecido, não a primeira aparição do objeto. Não criar uma segunda Pedra.

Conhecimento limita-se às marcas recorrentes associadas à fuligem/rota e à evidência concreta da Pedra; autoria e função permanecem desconhecidas. Não confirmar que são escrita nem revelar Antigos Asterianos como autoria, Âncoras, Primeiro Selo, Avesso, Convergência, Desvelados ou explicação cosmológica. Não criar fragmento textual sem definição na Fonte.

### Etapas 5 e 6 — Oren e Alda no Refúgio

Após Etapa 4, a Etapa 5 oferece a ação contextual `[Retornar ao Refúgio]` (v1.0.18: equivale à ligação do hub Charneca → Refúgio; a volta ao Refúgio também está sempre disponível pela tela do Local). Não é Travessia dos Braseiros, teleport, Braseiro, descoberta, Caçada, Desbravar ou etapa adicional. Não custa Vigor nem Coroas, não concede XP/recompensa e não cria encontro. A transição válida atualiza o Local atual para `Refúgio do Ocaso`, preserva o progresso de P2 e a descoberta da Charneca, e mostra diretamente o contexto de Oren/Etapa 5. Antes do retorno, reconnect reconstrói a ação na Charneca; depois dele, reconstrói Oren no Refúgio. Callback stale/duplicado não duplica progresso. Travessia genérica Charneca↔Refúgio continua indisponível sem os Braseiros permanentes apropriados.

Oren Cal só pode ser atendido no Refúgio; conversa remota não conclui Etapa 5. Preservar: “Esta marca não é decoração. Também não vou chamá-la de escrita até termos prova.”

Etapa 6 exige conversa válida com Alda Veyr no Refúgio; relatório remoto não conclui P2.

### Conclusão e recompensa

Conclusão com Alda é atômica, idempotente e única. Conceder exatamente `3.300 XP`, `140 Coroas`, `1 Ferro de Fuligem vinculado`, `2 Ervas Cinzentas vinculadas`, `1 Resíduo do Ocaso vinculado` e nenhum Equipamento. Consolidar XP/nível pelas regras globais. Respeitar capacidade de Inventário e Entregas Pendentes; Entrega Pendente permitida pela Fonte Mestra não bloqueia conclusão. Callback/retry/reconnect não duplica prêmio.

### Conteúdo normal da Charneca depois de P2

**v1.0.18 (texto herdado reescrito).** Assim que a Charneca é descoberta, liberar o conteúdo normal local e a utilização normal da ligação Refúgio ↔ Charneca nos dois sentidos (hub). **P2 concluída deixa de liberar conteúdo.** Título histórico: "depois de P2".

- **Caçada Manual:** pool completo do Local em Solo (v1.0.18: sem `unlock_level` em Solo, seção 33.5).
- **Desbravar:** liberado na descoberta, sem recarga de 5 min nem limite de 6 por hora (33.7).
- **Ronda de Caça:** P2 não a libera. Até primeira Vitória manual válida em Caçada na Charneca, estado `🔒 Ronda de Caça · Vença uma Caçada neste Local`. Essa Vitória libera a Ronda local. Familiaridade é independente por Local; Vitória na Estrada não libera Ronda da Charneca.

Preservar pool/pesos de §10.3 (v1.0.18: em Solo todo o pool do Local está disponível desde o primeiro acesso, sem `unlock_level`; o Cervo Escoriado deixa de ser inelegível até Nv.4). Sem Elite natural; Alfa Cinéreo permanece na elegibilidade própria da Estrada. Encontro roteirizado não usa o pool.

**v1.0.18:** removidos os textos "P2 não antecipa gates Nv.4+", "Desbravar Nv.4" e "inelegível até Nv.4". O Braseiro do Vento Morto e a Entrada da Cripta seguem como resultados de Desbravar, sem trava de nível. O Material Básico do Cervo Escoriado e seu pool temático estão definidos em §8.5; isso não antecipa o Cervo nem altera as regras econômicas globais.

### Falas-chave e efeitos

**Alda Veyr:** “A fuligem sem fogo significa que alguém chegou antes de nós — ou que estamos olhando para o problema errado.”

**Oren Cal:** “Esta marca não é decoração. Também não vou chamá-la de escrita até termos prova.”

- Inicia após P1 concluída e interação válida com Alda (sem nível).
- Exige a Charneca já descoberta por Explorar na Etapa 1; **não descobre a Charneca** (v1.0.18).
- Persiste/idempotente nos três pontos, encontro e efeitos.
- Cria/atualiza `Marcas na Fuligem` sem definir autoria/função.
- Conclui e recompensa somente após Etapa 6 com Alda.
- Não libera Caçada/Desbravar (já liberados na descoberta, v1.0.18); Ronda exige primeira Vitória manual local.


## 5.6 S2 — Os Nomes Esquecidos

**Objetivo narrativo:** apresentar os Peregrinos do Ocaso e iniciar o arco que termina em S6.

**Tipo:** Missão Secundária padrão.<br>
**ID persistido:** `S2`.<br>
**Giver e Local de oferta/conclusão:** Oren Cal, somente no Refúgio do Ocaso.<br>
**Requisitos (v1.0.18):** P2 concluída (sem nível). S2 não é requisito para P3. O Peregrino Calcinado Nv.4 do encontro roteirizado permanece fixo e não escala.<br>
**Versão de conteúdo:** `tdo-1.0.9`.

**Giver:** Oren Cal.

Oferta e visualização não criam uma Quest. Aceite explícito cria uma única Quest `S2`; reaceite de uma Quest abandonada reutiliza essa linha e segue a semântica de abandono de S1. Oren não pode oferecer, avançar ou concluir S2 por interação remota pelo Mapa.

### Etapas e progresso persistido

1. **Encontrar o acampamento abandonado na Charneca.** É um contexto da Missão, não um Local global: não cria `LocationDiscovery`, recompensa, atividade econômica ou resultado de Desbravar. O avanço exige interação válida na Charneca e é salvo em `Quest.progress`.
2. **Examinar três vestígios pessoais.** Usar IDs estáveis `s2.vestige.1`, `s2.vestige.2` e `s2.vestige.3`. Podem ser examinados em qualquer ordem, cada um conta uma vez e não possuem valor econômico. São objetivos exclusivos de S2; não criam nem consomem `ExplorationAttempt`.
3. **Encontrar o Peregrino Calcinado roteirizado.** O terceiro vestígio materializa automaticamente um encontro solo fixo de missão, `s2_scripted_peregrino_calcinado`.
4. **Vencer o encontro.** O requisito é Vitória; sobreviver sem vencer não conclui a etapa. O encontro usa o Peregrino Calcinado canônico, Comum, Nv.4, sem Variante, pelo combat engine compartilhado. Não é Caçada: não cria `HuntContext`, não consome Vigor, não concede Familiaridade e não executa settlement de Hunt. Consumíveis PvE elegíveis permanecem sujeitos às regras globais.
5. **Recuperar o fragmento de registro carbonizado.** A interação contextual após a Vitória atualiza somente `Quest.progress`; o fragmento não é Material, não entra no Inventário econômico, não pode ser vendido/craftado e não tem recompensa própria.
6. **Retornar a Oren Cal no Refúgio do Ocaso.** A Missão só conclui por interação válida com Oren no Refúgio. Não conclui remotamente pelo Mapa.

O encontro pode conceder somente o XP normal de inimigo do Peregrino Nv.4 na Vitória e registros de Bestiário/XP de Observação quando legitimamente elegíveis segundo as regras globais. Esses efeitos são idempotentes e vinculados à criatura ou à identidade da atividade, conforme o sistema compartilhado. O encontro não concede Coroas, Materiais, Equipamento, Runa, Fragmento econômico ou outra recompensa de Hunt; não há bônus especial de XP de missão no combate.

### Derrota e retry

Derrota encerra a identidade atual do encontro e mantém S2 ativa no objetivo do Peregrino. Acampamento e vestígios examinados permanecem; não há reroll de criatura/Variante nem recompensa de Vitória. Aplicam-se ao encontro roteirizado de S2 as regras regionais de recovery normal da Charneca da seção 11.9: antes da descoberta válida de `tdo.brazier.vento_morto`, recovery no Braseiro do Refúgio/Refúgio; depois, no Braseiro do Vento Morto/Charneca. HP e estados são resolvidos pelas regras globais de recovery; Vigor não é restaurado e Consumíveis usados permanecem consumidos.

Depois do recovery, o jogador pode iniciar uma nova tentativa somente quando estiver na Charneca. Se recovery ocorreu no Refúgio, deve retornar pela ligação do hub Refúgio → Charneca (v1.0.18; a Charneca já está descoberta). A nova tentativa materializa novo `encounter_id`, mas sempre o mesmo Peregrino Calcinado Nv.4, Comum, sem Variante. Não há teleporte ou retry automático. Reconnect/callback não materializa outro encontro.

Abandonar S2 fora de combate reinicia etapa e progresso transitório quando houver reaceite, como em S1. A identidade de uma tentativa já resolvida, Bestiário, Códice e quaisquer recompensas permanentes legitimamente obtidas não são removidos nem duplicados. S2 não usa estado Suspensa.

### Fala-chave

**Oren Cal:**<br>
“Não preciso saber quem eram todos eles. Preciso apenas provar que foram pessoas antes de virarem aquilo que encontramos.”

### Efeitos

- na conclusão válida, cria/atualiza a Entrada **Peregrinos do Ocaso** no Códice (`codex.mystery.peregrinos_do_ocaso`), de forma idempotente;
- registra que grupos atravessaram a região antes do estado atual das rotas;
- registra que havia pessoas/identidades antes da condição atualmente observada;
- não declara a natureza verdadeira dos Peregrinos Calcinados.

Recompensa final única: **2.695 XP**, **120 Coroas**, **1 Erva Cinzenta vinculada** e **1 Resíduo do Ocaso vinculado**. Usar a entrega existente de Inventário/Entregas Pendentes/BlockedDelivery; falta de espaço não perde Material nem impede a conclusão. Evento e componentes são idempotentes. A recompensa só é concedida com a conclusão em Oren, nunca no combate, acampamento, vestígios ou coleta do fragmento.

Os nomes dos três vestígios são apresentados de forma neutra e numerada (`Vestígio Pessoal 1–3`) enquanto não houver copy regional específica aprovada; não acrescentar autoria, identidade, cosmologia ou interpretação além da fala-chave e dos efeitos acima.

---

## 5.7 P3 — Sob Galhos Calcinados

**Objetivo narrativo:** abrir plenamente o Bosque e apresentar vestígios dos Antigos Asterianos.

**Giver:** Oren Cal.

**Requisitos (v1.0.18):** P2 concluída (sem Nv.5+) e **Bosque já descoberto por Explorar**. A entrada missionária Charneca → Bosque vira Refúgio → Bosque (hub). O "modo missionário" do Bosque (§29.2) é removido: Bosque descoberto tem Caçada, Desbravar e ligação liberados mesmo com P3 ativa. Os três fragmentos, o encontro do Cervo Nv.5 (fixo, sem Variante) e a escolha entre os três Raros mantêm-se. **Equipar exige nível do personagem ≥ `item_level` (regra global)**: o Raro Nv.5 pode ser recebido antes do nível, fica vinculado e inutilizável até o nível certo.

### Etapas

1. Entrar no **Bosque Calcinado** (já descoberto).
2. Localizar três fragmentos de construção entre raízes e cinza.
3. Sobreviver a um encontro com ataque Preparado claramente telegrafado.
4. Examinar um fragmento entalhado de estrutura antiga.
5. Retornar a Oren com o registro.
6. Escolher 1 dos 3 Equipamentos Raros de Campanha.

### Encontro pedagógico

Usar **Cervo Escoriado** com **Carga do Ocaso** como ataque Preparado principal. `variant_roll=false`.

### Fala-chave

**Oren Cal:**<br>
“Pedra trabalhada debaixo de árvores queimadas. Isto estava aqui antes do Bosque ser como o conhecemos.”

### Efeitos

- ~~descobre Bosque Calcinado~~ (v1.0.18: a Missão não descobre Local; exige o Bosque já descoberto);
- cria **Antigos Asterianos** no Códice;
- atualiza **Marcas na Fuligem** apenas com associação material/arquitetônica prudente;
- concede escolha Rara de P3.

---

## 5.8 S3 — Rastros sob os Galhos

**Status:** conteúdo novo aprovado formalmente nesta consolidação; substitui a lacuna textual do histórico não recuperado.

**Tipo:** Curta.

**Giver:** Alda Veyr.

**Requisitos (v1.0.18):** Bosque descoberto e P3 ativa ou concluída; sem Nv.5+.

**Objetivo narrativo:** mostrar que a ameaça do Bosque afeta rotas e suprimentos sem criar um novo arco de lore.

### Etapas

1. Examinar uma rota de suprimentos interrompida no Bosque.
2. Seguir três rastros entre os galhos.
3. Derrotar um **Cervo Escoriado**.
4. Verificar a carga abandonada.
5. Reportar a Alda.

`variant_roll=false`.

### Fala-chave

**Alda Veyr:**<br>
“Nem toda perda precisa esconder um mistério. Às vezes basta descobrir o que derrubou a carga antes que derrube a próxima.”

### Efeitos

- fornece evidência legítima de Habitat/combate do Cervo quando aplicável;
- não cria entrada nova de Códice;
- reforça o Bosque como zona de risco logístico.

---

## 5.9 P4 — Pedras que Ainda Vigiam

**Objetivo narrativo:** conduzir o jogador às Ruínas do Vigia e estabelecer que estruturas antigas ainda exercem função de guarda.

**Giver:** Alda Veyr.

**Requisitos (v1.0.18):** P3 concluída (sem Nv.7+) e **Ruínas já descobertas por Explorar**. Bosque → Ruínas vira Refúgio → Ruínas (hub). O Vigia Rachado roteirizado Nv.7 (Guarda Rachada, Barreira 70% ATQ, 2T, CD3) permanece fixo. Recompensas inalteradas.

### Etapas

1. Seguir o Caminho Ocidental a partir do Bosque (v1.0.18: contexto narrativo; a chegada às Ruínas parte do Refúgio).
2. Alcançar os limites das **Ruínas do Vigia** (já descobertas).
3. Derrotar um **Vigia Rachado** roteirizado.
4. Examinar duas estruturas de guarda.
5. Identificar uma rota segura de retorno.
6. Reportar a Alda e Oren.

### Fala-chave

**Alda Veyr:**<br>
“Uma muralha abandonada é pedra. Uma muralha que ainda impede passagem é outra coisa.”

**Oren Cal:**<br>
“Não sabemos quem lhes deu a ordem. Só sabemos que ela ainda produz consequências.”

### Efeitos

- ~~descobre Ruínas do Vigia~~ (v1.0.18: a Missão não descobre Local; exige as Ruínas já descobertas);
- atualiza Antigos Asterianos;
- registra a função de guarda sem afirmar consciência dos Vigias;
- ~~libera Desbravar/Ruínas~~ (v1.0.18: já liberado na descoberta); continua sem liberar Ronda.

---

## 5.10 S4 — Vigília sem Voz

**Status:** conteúdo novo aprovado formalmente nesta consolidação; substitui a lacuna textual do histórico não recuperado.

**Tipo:** Padrão.

**Giver:** Oren Cal.

**Requisitos (v1.0.18):** P4 concluída; sem Nv.7. **Etapa 3 em Solo ou Grupo [DECIDIDO 2026-11-14, decisão 8]:** qualquer **Vigia Rachado** derrotado conta, sem checar o `unlock_level` de cada membro em Grupo. Não há fallback de elegibilidade.

**Objetivo narrativo:** aprofundar a lógica de patrulha dos Vigias sem antecipar O Primeiro Selo ou a Âncora.

### Etapas

1. Investigar três antigos pontos de vigia nas Ruínas.
2. Registrar a orientação das marcas de patrulha.
3. Derrotar um **Vigia Rachado**.
4. Encontrar um ponto onde a patrulha muda de direção sem obstáculo visível.
5. Examinar o local.
6. Retornar a Oren.

### Fala-chave

**Oren Cal:**<br>
“Eles não patrulham ao acaso. Isso não prova vontade. Prova que houve uma ordem bastante precisa para sobreviver a quem a deu.”

### Efeitos

- fornece evidência de Bestiário para Vigia Rachado quando válida;
- atualiza apenas contexto já conhecido das Ruínas;
- não cria **Ordens que Permanecem**, que continua vinculada às Galerias;
- não revela O Primeiro Selo.

---

## 5.11 S5 — A Luz que Não Aquece

**Objetivo narrativo:** transformar as luzes observadas anteriormente em um fenômeno regional reconhecido, ainda sem explicar sua causa.

**Giver:** Oren Cal.

**Requisitos (v1.0.18):** P4 concluída; sem Nv.8.

### Etapas

1. Investigar um relato de luz nas Ruínas.
2. Examinar dois pontos onde existe luminosidade sem calor correspondente.
3. Sobreviver a um encontro elegível das Ruínas.
4. Registrar a direção e duração do fenômeno.
5. Retornar a Oren.

### Encontro

**Mariposa de Brasa** ou **Custódio Sem Rosto**: qualquer um dos dois conta. `variant_roll=false`. **[DECIDIDO 2026-11-14, decisão 8]** Em Solo e em Grupo, qualquer Mariposa de Brasa ou Custódio Sem Rosto derrotado conta, sem checar o `unlock_level` de cada membro. (Removido "conforme elegibilidade".)

### Fala-chave

**Oren Cal:**<br>
“A primeira vez podia ser engano. A segunda, coincidência. Agora temos um padrão — e ainda não temos uma explicação.”

### Efeitos

- cria **Luzes do Ocaso**;
- associa o fenômeno a vestígios antigos apenas como correlação observada;
- não revela função de Âncora.

---

## 5.12 P5 — A Porta do Poente

**Objetivo narrativo:** localizar a passagem para o clímax regional e provar que algo nas Ruínas era protegido de forma deliberada.

**Giver:** Alda Veyr.

**Requisitos (v1.0.18):** sem nível recomendado como gate (era Nv.9). O Custódio do Poente Nv.9 roteirizado continua fixo. PowerlevelFactor se aplica à XP fixa de Missão em Coop de Chefe (P5, P6, S6).

### Etapas

1. Seguir as estruturas de guarda mais profundas das Ruínas.
2. Encontrar a **Porta do Poente**.
3. Derrotar o **Custódio do Poente** em encontro roteirizado.
4. Examinar três elementos do mecanismo/estrutura ao redor da Porta.
5. Registrar o símbolo recorrente encontrado ali.
6. Reportar a Alda e Oren.

### Encontro

**Custódio do Poente · Elite · Nv.9**, sem Variante.

A vitória conta normalmente para Bestiário e para o marco importante configurado, se ainda não obtidos.

### Fala-chave

**Alda Veyr:**<br>
“Se puseram um guardião diante dessa porta, então o que existe depois dela importava mais do que estas ruínas inteiras.”

### Efeitos

- atualiza Ruínas do Vigia;
- aprofunda Antigos Asterianos;
- registra Porta do Poente;
- prepara P6;
- ainda não cria Âncora do Poente.

---

## 5.13 P6 — O Vigia Partido

**Objetivo narrativo:** concluir o arco regional, derrotar o Vigia Partido e revelar apenas o conhecimento permitido sobre a Âncora do Poente.

**Início (v1.0.18):** automático quando P5 está concluída (sem exigência de Nv.10).

**Câmara do Poente (v1.0.18).** A Etapa 2 **exige a Câmara já descoberta por Explorar** e conclui na chegada válida, partindo do Refúgio. P6 **não** revela a Câmara. A Câmara não tem outra saída: ao fim da Missão (Etapa 8) o personagem volta ao Refúgio, como de qualquer Local. O texto de entrada da Câmara tem dois estados (antes e depois de P6 concluída); ver §3.6 e 33.3.

### Etapas

1. Cruzar a Porta do Poente.
2. Entrar na **Câmara do Poente** (já descoberta).
3. Examinar a estrutura central sem conseguir interpretá-la integralmente.
4. Enfrentar **Vigia Partido**.
5. Derrotar o Chefe.
6. Examinar novamente a estrutura após a queda do Vigia.
7. Registrar o nome **Âncora do Poente**.
8. Retornar ao Refúgio ou concluir o relatório narrativo equivalente.
9. Escolher 1 dos 3 Equipamentos Épicos de Campanha.

### Fala-chave antes do Chefe

**Oren Cal, sobre o registro disponível:**<br>
“Se a leitura estiver correta, o nome é ‘Âncora’. Não sabemos o que ancorava. Não transforme um nome em resposta.”

### Revelação após a vitória

O personagem pode concluir legitimamente apenas que:

- a estrutura é chamada **Âncora do Poente**;
- o Vigia Partido a protegia;
- outras estruturas chamadas Âncoras existiram.

Não revelar:

- função real das Âncoras;
- estabilização do Véu;
- Convergência;
- Projeto Hemaris;
- Desvelados;
- Avesso.

### Efeitos

- cria **Âncora do Poente** no Códice;
- atualiza Antigos Asterianos e Ruínas;
- registra primeira vitória de Vigia Partido;
- concede uma única vez `1 Núcleo do Vigia Partido` como recompensa específica do encontro;
- revela a Receita `Eco do Vigia Partido`;
- conclui o marco regional da Campanha;
- concede escolha Épica de P6;
- ao concluir P6, a UI passa a exibir o texto **pós-P6** da Câmara do Poente (`[[TEXTO_CAMARA_POS_P6]]`); a conclusão **não** libera nem revela o Local;
- permite a saída para Vales dos Enforcados quando o gate de nível também estiver satisfeito (o gate de nível da saída é estrutural global, §25, e **não** é alterado pela v1.0.18).

---

## 5.14 S6 — Onde os Nomes Terminaram

**Objetivo narrativo:** concluir o arco secundário iniciado em S2 sem transformar a Cripta em requisito obrigatório.

**Giver:** Oren Cal.

**Requisitos (v1.0.18):** S2 concluída e P5 concluída; sem Nv.10. O Guardião do Último Rastro Nv.10 segue fixo.

### Etapas

1. Revisar com Oren os fragmentos recuperados em S2.
2. Seguir três marcas de passagem dos Peregrinos nas Ruínas.
3. Examinar um abrigo abandonado.
4. Encontrar a passagem bloqueada pelo **Guardião do Último Rastro** e derrotá-lo.
5. Atravessar a passagem e encontrar o último registro legível da rota.
6. Retornar a Oren.

### Encontro — Guardião do Último Rastro

**Papel:** Chefe roteirizado exclusivo de S6.<br>
**Nv.:** 10.<br>
**Formato:** Solo ou Grupo · 1–4.<br>
**Variante:** nenhuma; `allow_random_variant=false`.

Artes já definidas/implementadas:

- **Golpe da Última Trilha** · `100% ATQ`;
- **Marca do Rastro** · `90% ATQ` + `AGI −10% · 2T`, CD3;
- **Queda da Travessia** · ação **Preparada** · `165% ATQ`, CD4.

Limites do encontro:

- não possui Cura;
- não possui Barreira;
- não invoca criaturas;
- não materializa adds;
- não recebe Variante;
- **Queda da Travessia** usa a leitura/telegraph global de Ação Preparada;
- a passagem para o último registro legível permanece bloqueada até a Vitória válida;
- derrota/retry/reconnect seguem as regras de encontro roteirizado já vigentes e não autorizam reroll da criatura.

### Limite narrativo do Chefe

O nome **Guardião do Último Rastro** descreve sua função observável naquele encontro; não confirma origem, cargo histórico ou identidade anterior.

A S6 e o Bestiário podem afirmar apenas que:

- uma figura humanoide desconhecida bloqueava o último trecho da rota;
- ela manejava equipamento de travessia profundamente desgastado e uma longa haste reforçada;
- seu comportamento em combate priorizava controle de passagem, comprometimento de mobilidade e um grande golpe preparado;
- sua aparência carregava sinais das Terras do Ocaso e de longa exposição/desgaste.

Não afirmar, por texto, imagem, Códice ou Bestiário, que:

- ele é **O Sem-Nome**;
- ele é ou foi um Peregrino específico;
- ele representa o destino coletivo dos Peregrinos do Ocaso;
- ele é morto-vivo, espírito, possuído ou cadáver reanimado;
- ele é um construto asteriano, Vigia ou Custódio;
- ele é uma Raça jogável alterada;
- ele está ligado ao Avesso, à Âncora do Poente, à Convergência ou a qualquer causa cosmológica específica.

O Chefe deve ampliar o mistério da rota sem resolvê-lo.

### Fala-chave

**Oren Cal:**<br>
“Não encontrei o nome de cada um. Talvez nunca encontremos. Mas sabemos onde a trilha deles deixou de ser uma estrada e virou apenas vestígio.”

### Efeitos

- atualiza **Peregrinos do Ocaso**;
- atualiza Ruínas do Vigia;
- não exige Cripta;
- não identifica O Sem-Nome;
- não revela uma causa definitiva para o destino dos Peregrinos.

---

## 5.15 Regras de encontros de Missão

Por padrão:

`allow_random_variant = false`

para todos os encontros roteirizados acima.

Eles:

- podem conceder XP/Bestiário quando explicitamente elegíveis pelas regras normais;
- não recebem perfil econômico de Caçada automaticamente;
- não consomem Vigor apenas por pertencerem a Missão;
- não podem ser rerrolados por reconnect;
- usam `encounter_id` persistente quando um combate é materializado.

Recompensas de Missão são concedidas somente uma vez.

**Exceção explícita de P1:** o encontro da Etapa 3 de Vozes na Estrada segue integralmente o perfil específico definido em §5.3: 0 XP de inimigo, 0 XP adicional de primeira observação e nenhuma recompensa econômica própria. Progresso legítimo de conhecimento do Bestiário permanece separado dessa recompensa.

---

## 5.16 Estado final das Missões

Com esta consolidação:

- S3 oficial passa a ser **Rastros sob os Galhos**;
- S4 oficial passa a ser **Vigília sem Voz**;
- as 12 Missões possuem título, requisitos, etapas, responsáveis, efeitos narrativos e recompensa implementável;
- não há dependência de NPC adicional;
- não existe bloco de Missão pendente para migração.

# 6. NPCs oficiais da vertical slice

A vertical slice das Terras do Ocaso utiliza **cinco NPCs nomeados persistentes**. Não são necessários NPCs adicionais para fechar a região.

## Alda Veyr

Coordena segurança, rotas e necessidades do Refúgio. Sua autoridade decorre da necessidade prática, não de título político formal estabelecido nesta região.

Funções de conteúdo:

- eixo da Campanha regional;
- segurança e progressão territorial;
- giver de P2, P4, P5 e S3;
- fechamento/relato de P1 e P6 quando aplicável.

## Oren Cal

Escriba dedicado a preservar relatos, nomes e inscrições. Suas traduções devem ser apresentadas como hipóteses enquanto não houver evidência suficiente.

Funções de conteúdo:

- Códice;
- investigação histórica;
- giver de S1, S2, P3, S4, S5 e S6;
- apoio narrativo em P1, P2, P4, P5 e P6.

## Torren Vhal

NPC de introdução contextual para:

- Ferreiro;
- Crafting;
- Desmontagem;
- Aprimoramento.

Não substitui o sistema de Ofícios do jogador e não executa crafting gratuito.

## Sila Renn

NPC de introdução contextual para:

- Alquimista;
- Cura;
- Purificação;
- Antídoto.

Não cria loja obrigatória nem fonte paralela de Consumíveis.

## Vael Orin

Ponto narrativo das Provações de Classe no Refúgio do Ocaso.

Abre acesso ao **Círculo da Cinza**; não concede Caminho diretamente e não executa uma segunda Provação para troca posterior.

### Fechamento documental

Qualquer personagem sem nome utilizado apenas em Flavor — sobrevivente, viajante, corpo encontrado, registro antigo — permanece figurante contextual e não entra no catálogo de NPCs persistentes.

Portanto, **não existe migração de NPC pendente para o v1.0.4 FINAL**.

# 7. Materiais regionais

## Materiais Básicos · Grau I

- **Ferro de Fuligem** · Metal
- **Couro Escoriado** · Couro
- **Erva Cinzenta** · Reagente
- **Resíduo do Ocaso** · Essência

## Recursos especiais

- Catalisador de Elite I
- Fragmento de Aprimoramento I
- Núcleo da Cripta do Ocaso
- Núcleo das Galerias do Vigia
- Núcleo do Vigia Partido

---

# 8. Criaturas de mundo aberto

## 8.1 Cão Cinéreo

**Categoria:** Comum<br>
**Arquétipo:** Predador<br>
**Faixa:** Nv.1–3

Artes:

- Mordida Faminta · `100% ATQ`
- Investida Curta · `110% ATQ`, CD2

Material temático conhecido: Couro Escoriado.

Variantes: Furioso, Ágil.

O Cão do tutorial possui `variant_roll=disabled`; sua recompensa é `320 XP` somente em Vitória e `0 XP` em Derrota. Não se aplica a fórmula normal de XP de inimigo.

## 8.2 Corvo de Fuligem

**Categoria:** Comum<br>
**Arquétipo:** Predador<br>
**Faixa:** Nv.1–4

- Bicada · `95% ATQ`
- Rasante · `90% ATQ` + `AGI −8% · 1T`, CD2

IA: **Rasante se disponível → caso contrário Bicada**. Não usa condição adicional por HP, Classe, Caminho ou build.

Variantes: Ágil, Furioso.

Material Básico temático: **Resíduo do Ocaso · peso interno 100**. O peso seleciona a identidade da unidade de Material Básico somente quando o contexto global já conceder uma; não define chance de obtenção nem altera a quantidade global aplicável.

## 8.3 Peregrino Calcinado

**Categoria:** Comum<br>
**Arquétipo:** Equilibrado<br>
**Faixa:** Nv.2–5

- Golpe Desesperado · `105% ATQ`
- pode utilizar Defender conforme IA.

IA: **Golpe Desesperado → Golpe Desesperado → Defender → repetir**. Se Defender estiver devido mas for ilegal naquela oportunidade, usa Golpe Desesperado e mantém Defender como devido até a próxima oportunidade legal. Oportunidade perdida sem ação comprometida não avança o ciclo.

Materiais temáticos: **Ferro de Fuligem · peso interno 50; Erva Cinzenta · peso interno 50**. Para cada unidade de Material Básico concedida pelas regras globais do contexto, o pool seleciona a identidade em proporção 50/50; o peso interno não define chance de obtenção nem altera quantidade.

Variantes: Furioso, Resistente, Hemorrágico.

Sua natureza/origem não é confirmada como fato nesta região.

## 8.4 Aranha de Cinza

**Categoria:** Incomum<br>
**Perfil Bestiário:** RARE<br>
**Arquétipo:** Controlador<br>
**Faixa:** Nv.3–6

- Picada Tóxica · `80% ATQ` +1 Veneno, CD2
- Mordida · `95% ATQ`

IA: **Picada Tóxica se disponível → caso contrário Mordida.** A prioridade não depende de HP, Classe, Caminho, build ou Variante e não usa RNG. Não adicionar Defender ou condição de HP. A Recarga global CD2 permanece inalterada; sem interferência legítima de estado/oportunidade, a disponibilidade resultante alterna Picada Tóxica e Mordida. Não criar ciclo separado.

Picada Tóxica é aplicação nativa de Veneno. Continua válida quando o alvo está no cap global e aplica a regra global de stacking, inclusive substituição do stack mais antigo conforme a Fonte Mestra. Se uma futura ocorrência com Variante Venenoso usar Picada Tóxica, a aplicação nativa já satisfaz o pacote de Variante e não gera stack adicional nessa mesma ação.

Fraqueza: Queimadura `+10%`.

Resistência: Veneno `−10%`.

Variantes: Venenoso, Ágil.

Materiais Básicos temáticos possíveis, no mesmo pool para Charneca da Fuligem e Bosque Calcinado, salvo override futuro explicitamente documentado:

- Erva Cinzenta · peso 50;
- Resíduo do Ocaso · peso 50.

Quando o perfil econômico aplicável gerar mais de uma unidade de Material, cada unidade usa um sub-roll independente nesse pool, determinístico a partir da seed/contexto econômico e de ordinal próprio. Não forçar Materiais distintos. O pool define somente qual Material é escolhido depois da quantidade e chance aplicáveis ao contexto; não altera regras globais de Categoria. Em Desbravar, usar o pool somente quando a economia vigente do resultado/contexto gerar Material; não acrescentar Material a resultado narrativo/atmosférico. O encontro roteirizado de P2 não usa liquidação de Caçada e continua concedendo nenhum Material.

Para Caçada normal, permanece a regra global da Categoria Incomum: `100% → 1–2 Materiais Básicos`. A TDO define somente o pool temático acima; a quantidade é resolvida primeiro e cada unidade resultante escolhe seu Material independentemente.

## 8.5 Cervo Escoriado

**Categoria:** Comum<br>
**Arquétipo:** Bruto<br>
**Faixa:** Nv.4–7

- Chifrada · `105% ATQ`
- Carga do Ocaso · Preparada · `160% ATQ`

Variantes: Furioso, Resistente.

Material Básico temático: **Couro Escoriado · peso interno 100**. Este é o único Material Básico no pool normal do Cervo, em Charneca da Fuligem e Bosque Calcinado, salvo override futuro explicitamente documentado. Aplicar a chance e quantidade do perfil econômico já vigente para o contexto: como criatura Comum em Caçada, primeiro resolver o roll global de 80%; somente no sucesso conceder exatamente `1 Couro Escoriado`. Em Desbravar de combate, aplicar a economia `exploration_combat` vigente e escolher as unidades de Material desse mesmo pool; não acrescentar Material a resultado narrativo/atmosférico. Peso 100 significa 100% do pool interno após o roll global, não chance de drop de 100%. O pool não cria Material por si só.

## 8.6 Carniçal de Fuligem

**Categoria:** Comum<br>
**Arquétipo:** Bruto<br>
**Faixa:** Nv.5–8

- Dilacerar · `90% ATQ` +1 Sangramento, CD2
- Arrancada · `125% ATQ`, CD3

Fraqueza: Queimadura `+10%`.

Resistência: Sangramento `−10%`.

Variantes: Hemorrágico, Resistente.

## 8.7 Mariposa de Brasa

**Categoria:** Incomum<br>
**Perfil Bestiário:** RARE<br>
**Arquétipo:** Conjurador<br>
**Faixa:** Nv.6–9

- Toque Incandescente · `80% ATQ` +1 Queimadura, CD2
- Clarão de Cinzas · `120% ATQ`, CD3

Resistência: Queimadura `−10%`.

Variantes: Ágil, Furioso.

## 8.8 Vigia Rachado

**Categoria:** Comum<br>
**Arquétipo:** Blindado<br>
**Faixa:** Nv.7–10

- Golpe de Pedra · `100% ATQ`
- Guarda Rachada · Barreira `70% ATQ`, CD3

Variantes: Resistente, Furioso.

## 8.9 Custódio Sem Rosto

**Categoria:** Incomum<br>
**Perfil Bestiário:** RARE<br>
**Arquétipo:** Controlador<br>
**Faixa:** Nv.8–10

- Marca do Peso · `90% ATQ` + `AGI −10% · 2T`, CD3
- Proteção Antiga · Barreira `80% ATQ`, CD3
- Impacto · `120% ATQ`, CD3

Variantes: Resistente, Ágil.

## 8.10 Guardião do Último Rastro

**Papel:** Chefe roteirizado de S6 — Onde os Nomes Terminaram.<br>
**Faixa:** Nv.10.<br>
**Formato:** Solo ou Grupo · 1–4.<br>
**Variante:** nenhuma.

- Golpe da Última Trilha · `100% ATQ`
- Marca do Rastro · `90% ATQ` + `AGI −10% · 2T`, CD3
- Queda da Travessia · Preparada · `165% ATQ`, CD4

Não possui Cura, Barreira, invocações ou adds.

Sua origem e identidade permanecem **não confirmadas**. O nome de Bestiário não deve ser usado como prova de que pertencera a uma ordem formal de Guardiões. A aparência pode sugerir corpo humanoide e equipamento de travessia acumulado, mas não pode classificá-lo ontologicamente.

O Guardião do Último Rastro é exclusivo do encontro roteirizado de S6 e **não entra** em pool normal de Caçada, Desbravar, Ronda, Masmorra ou Variante.

---

# 9. Elites regionais

Os três Elites de mundo aberto usam a Categoria global **Elite** e o Arquétipo indicado. Stats absolutos são derivados da Fonte Mestra; abaixo ficam fechados apenas kit, comportamento e função regional.

## 9.1 Alfa Cinéreo

**Habitat:** Estrada das Cinzas<br>
**Categoria:** Elite<br>
**Arquétipo:** Predador<br>
**Faixa:** Nv.3–4

Artes:

- **Mordida Alfa** · `100% ATQ`.
- **Investida Rasgante** · `90% ATQ` + `1 Sangramento`, CD2.
- **Salto Predatório** · ação Preparada · `160% ATQ`, CD4.

Comportamento:

Prioridade implementável completa:

1. se **Salto Predatório** estiver pendente, resolver a Ação Preparada pelas regras globais;
2. se o alvo possui `0 Sangramento` e **Investida Rasgante** está disponível, usar Investida Rasgante;
3. caso contrário, se **Salto Predatório** está disponível, preparar Salto Predatório;
4. caso contrário, se **Investida Rasgante** está disponível e o alvo permanece abaixo do cap global de Sangramento, usar Investida Rasgante;
5. caso contrário, usar **Mordida Alfa**.

Não reaplica Sangramento apenas para ultrapassar o máximo global. Salto Predatório sempre utiliza telegraph completo antes da resolução e não possui Hard CC.

Material Básico temático: **Couro Escoriado · peso interno 100**. O peso seleciona a identidade da unidade de Material Básico somente quando o contexto global já conceder uma; não define chance de obtenção nem altera a quantidade global aplicável.

Função: primeiro Elite regional e primeira demonstração de pressão predatória + DoT + ataque Preparado fora de Masmorra.

## 9.2 Viúva da Fuligem

**Habitat:** Bosque Calcinado<br>
**Categoria:** Elite<br>
**Arquétipo:** Controlador<br>
**Faixa:** Nv.6–7

Artes:

- **Picada da Viúva** · `80% ATQ` + `1 Veneno`, CD2.
- **Teia de Fuligem** · `75% ATQ` + `AGI −15% · 2T`, CD3.
- **Bote da Viúva** · `130% ATQ`, CD3; contra alvo com Veneno recebe `+10 p.p. PER` apenas nessa ação.

Comportamento:

- tenta estabelecer Veneno antes de Bote da Viúva;
- usa Teia de Fuligem para criar janela de pressão, não como loop permanente;
- **não utiliza Stun** ou outro Hard CC.

Função: Elite de controle leve; combina Veneno, perda de AGI e ataque forte sem retirar turnos do jogador.

## 9.3 Custódio do Poente

**Habitat:** Ruínas do Vigia<br>
**Categoria:** Elite<br>
**Arquétipo:** Blindado<br>
**Faixa:** Nv.9–10

Artes:

- **Golpe do Custódio** · `100% ATQ`.
- **Guarda do Poente** · Barreira `90% ATQ`, CD3.
- **Marca do Poente** · `85% ATQ` + `DEF −10% · 2T`, CD3.
- **Queda do Poente** · ação Preparada · `170% ATQ`, CD4.

Comportamento:

- não lança Guarda do Poente enquanto ainda possuir Barreira relevante da própria Arte;
- busca aplicar Marca do Poente antes de uma janela ofensiva, quando disponível;
- Queda do Poente sempre possui telegraph completo;
- não possui Cura nem Hard CC.

Função: último Elite de mundo aberto e ensaio direto das linguagens defensivas usadas pelos Vigias e pelo clímax regional.

# 10. Pools oficiais de Caçada

## 10.1 Seleção

A Caçada resolve:

`Local → criatura-base elegível → Variante opcional`

Pesos são relativos. Entradas inelegíveis são removidas antes do sorteio e os pesos restantes são normalizados.

**Reescrita v1.0.18 (substitui integralmente o texto da v1.0.17 desta seção).**

**Nível do inimigo.** O nível do inimigo é o do Local/região e **não escala com o jogador**. Para cada criatura, `enemy_level = max_enemy_level` dessa criatura (coluna "Máx." das tabelas §10.2 a §10.5). A fórmula `enemy_level = min(player_level, max_enemy_level)` da v1.0.17 **é removida**. Vale em **Solo e em Grupo**; em Grupo o nível **não** é o maior nível entre os participantes (override da linha 899 da Fonte Mestra, seção 33.14). O nível congelado no `encounter_id` continua valendo. Um personagem Nv.1 pode entrar em qualquer Local descoberto e enfrenta criaturas no nível delas.

**`unlock_level` (coluna "Unlock" das tabelas).**
- **Solo:** não se aplica. Todo o pool do Local está disponível desde o primeiro acesso; nenhuma criatura é excluída por `unlock_level`.
- **Grupo:** é requisito **individual de cada membro**. Uma criatura só é elegível se **todos** os participantes cumprem o seu `unlock_level`.
- **Grupo sem criatura elegível [DECIDIDO 2026-11-14, decisão 11]:** se nenhuma criatura do Local for elegível para todos os membros, a Caçada **não abre** e a interface informa **qual membro não cumpre o `unlock_level`**. O texto "nada para caçar aqui ainda" fica reservado para outros casos de pool vazio.

Depois de elegível, a criatura permanece no pool.

O `encounter_id` materializa criatura, nível, Variante e scaling; reconnect/abandono não rerrola o encontro.

## 10.2 Estrada das Cinzas

| Criatura | Categoria | Unlock | Máx. | Peso |
|---|---|---:|---:|---:|
| Cão Cinéreo | Comum | 1 | 3 | 34 |
| Corvo de Fuligem | Comum | 1 | 4 | 33 |
| Peregrino Calcinado | Comum | 2 | 5 | 30 |
| Alfa Cinéreo | Elite | 3 | 4 | 3 |

Com pool completo: `97%` Comuns / `3%` Elite.<br>
Chance de Variante: `8%`.

Caçada Manual fica disponível na Estrada, que nasce descoberta (v1.0.18), mesmo no Nv.1. Ronda fica disponível após a primeira vitória manual válida no Local. Em Grupo, a vitória manual libera a Ronda para todos os membros que participaram da vitória.

## 10.3 Charneca da Fuligem

| Criatura | Categoria | Unlock | Máx. | Peso |
|---|---|---:|---:|---:|
| Peregrino Calcinado | Comum | 2 | 5 | 31 |
| Cão Cinéreo | Comum | 1 | 3 | 31 |
| Aranha de Cinza | Incomum | 3 | 6 | 18 |
| Cervo Escoriado | Comum | 4 | 7 | 20 |

Pool completo: `82%` Comuns / `18%` Incomum.<br>
Chance de Variante: `10%`.

Não há Elite natural neste pool.

## 10.4 Bosque Calcinado

| Criatura | Categoria | Unlock | Máx. | Peso |
|---|---|---:|---:|---:|
| Cervo Escoriado | Comum | 4 | 7 | 27 |
| Carniçal de Fuligem | Comum | 5 | 8 | 30 |
| Aranha de Cinza | Incomum | 3 | 6 | 20 |
| Mariposa de Brasa | Incomum | 6 | 9 | 20 |
| Viúva da Fuligem | Elite | 6 | 7 | 3 |

Pool completo: `57%` Comuns / `40%` Incomuns / `3%` Elite.<br>
Chance de Variante: `12%`.

## 10.5 Ruínas do Vigia

| Criatura | Categoria | Unlock | Máx. | Peso |
|---|---|---:|---:|---:|
| Carniçal de Fuligem | Comum | 5 | 8 | 25 |
| Vigia Rachado | Comum | 7 | 10 | 32 |
| Mariposa de Brasa | Incomum | 6 | 9 | 20 |
| Custódio Sem Rosto | Incomum | 8 | 10 | 20 |
| Custódio do Poente | Elite | 9 | 10 | 3 |

Pool completo: `57%` Comuns / `40%` Incomuns / `3%` Elite.<br>
Chance de Variante: `15%`.

## 10.6 Variantes elegíveis

| Criatura | Variantes |
|---|---|
| Cão Cinéreo | Furioso, Ágil |
| Corvo de Fuligem | Ágil, Furioso |
| Peregrino Calcinado | Furioso, Resistente, Hemorrágico |
| Aranha de Cinza | Venenoso, Ágil |
| Cervo Escoriado | Furioso, Resistente |
| Carniçal de Fuligem | Hemorrágico, Resistente |
| Mariposa de Brasa | Ágil, Furioso |
| Vigia Rachado | Resistente, Furioso |
| Custódio Sem Rosto | Resistente, Ágil |

Quando o roll de Variante ocorre, apenas as Variantes válidas daquela criatura participam, com peso igual. Máximo `1 Variante/encontro`.

Modificadores são os globais:

- Furioso: `ATQ +8% / DEF −8%`;
- Resistente: `DEF +10% / ATQ −6%`;
- Ágil: `AGI +12% / HP −7%`;
- Hemorrágico: habilita pacote de Sangramento e `ATQ −5%`;
- Venenoso: habilita pacote de Veneno e `HP −5%`.

Variante não altera Categoria, multiplicador-base de XP ou loot-base.

## 10.7 Ronda e encontros roteirizados

- Variante normal não interrompe Ronda.
- Alfa Cinéreo, Viúva da Fuligem e Custódio do Poente interrompem a Ronda **antes do combate automático**.
- O Elite materializado conserva o mesmo `encounter_id`; não há reroll ao reabrir o fluxo.
- Encontros de Missão, tutorial, Provação e Masmorra usam `allow_random_variant=false` por padrão.
- O Cão Cinéreo do tutorial nunca recebe Variante.
- Refúgio do Ocaso possui `normal_hunt_pool=none`.

# 11. Desbravar

## 11.1 Regras regionais

**Texto novo v1.0.18 (substitui o da v1.0.17).**

Desbravar está disponível em Estrada, Charneca, Bosque e Ruínas, **a partir do momento em que o Local é descoberto**, e age sobre o **Local atual** (o jogador entra no Local e desbrava ali; não há exploração remota). Refúgio do Ocaso é Local seguro e não possui Desbravar. A Câmara do Poente não possui Desbravar.

**"Local novo" não é resultado de Desbravar.** A revelação de Locais é a ação **Explorar**, no Refúgio (seção 33.2). Não existem identificadores `explore.tdo.local.*` no pool de Desbravar.

Aplicar a Fonte Mestra, **exceto o que a v1.0.18 altera por override do autor** (seção 33.14; registrado no `SOURCE_AUTHORITY.md`):

- ~~recarga `5 min`~~ — **removida**;
- ~~máximo `6 tentativas / Local / 60 min`~~ — **removido**;
- **limite técnico anti-spam** [DECIDIDO 2026-11-14]: intervalo mínimo de **3 segundos** entre tentativas por personagem e no máximo **1 tentativa em resolução** por vez. Vale para Desbravar e para Explorar. É limite técnico, não econômico: não concede nem bloqueia recompensa;
- Solo;
- pool-base `8/22/15/25/10/20`;
- anti-repetição (§11.7);
- proteção de até 3 tentativas **somente** quando um resultado se torna objetivo obrigatório de conteúdo ativo (não se aplica a revelar Local, que saiu de Desbravar);
- `4 Vigor` apenas quando um resultado repetível realmente paga sua economia.

**Bestiário [DECIDIDO 2026-11-14, decisão 9].** O BKP de **investigação Desbravar** e o BKP de **Habitat** são **marco único** por criatura e por Local. Seção 33.9 e §15.1.

Pool-base:

| Categoria | Peso |
|---|---:|
| Grande Descoberta | 8 |
| Conhecimento | 22 |
| Narrativo | 15 |
| Combate | 25 |
| Pequeno Recurso | 10 |
| Atmosférico | 20 |

Se uma categoria não possuir resultado elegível, seu peso é redistribuído proporcionalmente entre as categorias elegíveis.

Resultados `Únicos` saem permanentemente do pool após resolução válida e permanecem concluídos através do Legado.

XP:

- Grande Descoberta única: `FixedPercentXP(reference_level, 8%)`;
- Descoberta Menor única: `FixedPercentXP(reference_level, 2,5%)`;
- Atmosférico/repetível contextual: `0 XP adicional de exploração`;
- **XP de descoberta de Local (v1.0.18, só por Explorar):** `FixedPercentXP(min(nível de referência do Local, nível do personagem), 2,5%)`, uma vez por Local (seção 33.2.3).

## 11.2 Estrada das Cinzas

> **v1.0.18.** Nos §11.2 a §11.5, os subpesos da Grande Descoberta são os já publicados (Estrada: Marco 100; Charneca, Bosque e Ruínas: 50/50). Travas de nível dos resultados estão **removidas**: "elegível em Nv.4+" (Entrada da Cripta e Braseiro do Vento Morto), "elegível em Nv.8+" (Entrada das Galerias) e "exigem explicitamente Nv.6+" (Braseiro dos Galhos Mortos e Estrutura Enterrada). O `reference_level` continua sendo referência de XP, não trava. O **Caminho Ocidental** continua Conhecimento Único (peso 60), mas é só conhecimento geográfico, sem efeito de acesso e sem texto de "não ignora gate de Campanha para Ruínas".

### Grande Descoberta

**Marco dos Viajantes** · `explore.tdo.estrada.marco_viajantes`<br>
Único · ref Nv.2 · subpeso100.

Revela vestígios de antigas passagens e desbloqueia o Trecho **Memória dos Viajantes** em Estrada das Cinzas.

XP: `456`.

### Conhecimento

- **Rastros Cinéreos** · repetível · peso60. Pode fornecer evidência contextual de Habitat para Cão Cinéreo, Corvo de Fuligem ou Peregrino Calcinado.
- **Sinais à Margem** · repetível · peso40. Flavor/contexto já conhecido; não duplica Trechos.

### Narrativo

- **Luzes na Estrada** · Descoberta Menor · Único · ref Nv.2 · peso70. Registra luminosidade sem fogo evidente, sem concluir sua origem. XP `143`.
- **Vozes Levadas pelo Vento** · repetível · peso30 · sem estado permanente.

### Combate

Cão40 / Corvo35 / Peregrino25.<br>
Usa `encounter_id`; Variante usa a chance normal do Local.

### Pequeno Recurso

Ferro30 / Couro30 / Erva20 / Resíduo20.

### Atmosférico

Cinza sobre as Pegadas34 / Carroça sem Rodas33 / Fogueira Fria33.

## 11.3 Charneca da Fuligem

### Grandes Descobertas

- **Braseiro do Vento Morto** · `explore.tdo.charneca.braseiro` · Único · ref Nv.4 · peso50 · registra Braseiro permanente. XP `616`.
- **Entrada da Cripta do Ocaso** · `explore.tdo.charneca.cripta` · Único · ref Nv.4 · peso50 · revela a Masmorra e seu Caminho Conhecido (v1.0.18: sem "elegível em Nv.4+"). XP `616`.

### Conhecimento

- **Pedra Marcada** · Descoberta Menor · Único · ref Nv.4 · peso60 · atualiza Marcas na Fuligem sem definir autoria/finalidade. XP `193`.
- **Vestígios na Fuligem** · repetível · peso40 · evidência contextual de Aranha, Cervo ou Peregrino.

### Narrativo

- **Vento Morto** · Descoberta Menor · Único · ref Nv.4 · peso65 · observação ambiental, sem conclusão sobrenatural. XP `193`.
- **Cinzas que Não Assentam** · repetível · peso35.

### Combate

Peregrino35 / Aranha35 / Cervo30. Sem Elite genérico.

### Pequeno Recurso

Erva45 / Resíduo30 / Couro25.

### Atmosférico

Pedras Negras34 / Capim Coberto de Cinza33 / Silêncio sem Pássaros33.

## 11.4 Bosque Calcinado

### Grandes Descobertas

- **Braseiro dos Galhos Mortos** · `explore.tdo.bosque.braseiro` · Único · ref Nv.6 · peso50 · registra Braseiro permanente. XP `800`.
- **Estrutura Enterrada** · `explore.tdo.bosque.estrutura_enterrada` · Único · ref Nv.6 · peso50 · atualiza Bosque e Antigos Asterianos sem revelar função de Âncora. XP `800`.

### Conhecimento

- **Caminho Ocidental** · Descoberta Menor · Único · ref Nv.6 · peso60 · conhecimento geográfico, sem efeito de acesso (v1.0.18). XP `250`.
- **Rastros entre os Galhos** · repetível · peso40 · evidência contextual de Cervo, Carniçal, Aranha ou Mariposa.

### Narrativo

Árvores que Ainda Fumegam55 / Cinzas sob as Raízes45 · repetíveis; sem conclusão cosmológica.

### Combate

Cervo25 / Carniçal30 / Aranha20 / Mariposa25. Viúva da Fuligem não entra no resultado genérico.

### Pequeno Recurso

Couro35 / Erva30 / Resíduo35.

### Atmosférico

Troncos Ocos34 / Brasa sob a Casca33 / Som entre os Galhos33.

## 11.5 Ruínas do Vigia

### Grandes Descobertas

- **Braseiro do Poente** · `explore.tdo.ruinas.braseiro` · Único · ref Nv.9 · peso50 · registra Braseiro permanente. XP `1.136`.
- **Entrada das Galerias do Vigia** · `explore.tdo.ruinas.galerias` · Único · ref Nv.9 · peso50 · revela a Masmorra e seu Caminho Conhecido (v1.0.18: sem "elegível em Nv.8+"). XP `1.136`.

### Conhecimento

- **Estruturas de Guarda** · Descoberta Menor · Único · ref Nv.9 · peso40 · registra arquitetura defensiva organizada. XP `355`.
- **Ocupação Posterior** · Descoberta Menor · Único · ref Nv.9 · peso40 · registra reutilização posterior sem identificar automaticamente seus responsáveis. XP `355`.
- **Marcas de Patrulha** · repetível · peso20 · contexto de deslocamento de Vigias/Custódios conhecidos.

### Narrativo

Passos onde Ninguém Passa50 / Pedra ainda em Vigília50 · repetíveis. Podem sugerir permanência de funções de guarda, mas não criam antecipadamente Ordens que Permanecem, O Primeiro Selo ou Âncora do Poente.

### Combate

Vigia Rachado35 / Custódio Sem Rosto30 / Carniçal20 / Mariposa15. Custódio do Poente não entra no resultado genérico.

### Pequeno Recurso

Ferro45 / Resíduo35 / Erva10 / Couro10.

### Atmosférico

Porta que Não Abre34 / Estátua sem Rosto33 / Eco sob a Pedra33. Não revela a Porta do Poente de P5 antes do gate narrativo.

## 11.6 Economia de Desbravar

**Pequeno Recurso:** `0,10 × C(nível aplicável) + 1 Material Básico`.

**Combate repetível:** `0,15 × C(nível aplicável) + 1 Material Básico +20% de chance de +1 Material Básico`.

Ambos consomem `4 Vigor` somente quando a economia é efetivamente concedida.

Combate usa `loot_profile=exploration_combat`, não a tabela completa de Saque da Caçada. O inimigo continua elegível à XP de combate e ao Bestiário pelas regras globais.

Com `Vigor <4`, a tentativa ainda pode ocorrer, mas não paga Coroas/Materiais repetíveis; nenhum Vigor parcial é consumido e XP repetível aplica o fator global de `25%` quando pertinente.

## 11.7 Anti-repetição

- resultado imediatamente anterior: `peso=0`;
- se o mesmo resultado apareceu entre os últimos 3 resultados válidos: `peso ×0,35`;
- a penalidade é aplicada ao resultado específico, não à categoria inteira.

## 11.8 Fechamento de exploração

**Valores v1.0.18 (substituem `7.049 XP` / `7,21%` da v1.0.17), no teto (todos os Locais descobertos por Explorar com personagem de nível ≥ referência):**

Grandes Descobertas configuradas: `7`.<br>
Descobertas Menores configuradas: `6`.

XP total única:

- Grandes: `5.560 XP`;
- Menores: `1.489 XP`;
- Locais descobertos por Explorar: `193 + 250 + 355 + 395 = 1.193 XP` (Charneca, Bosque, Ruínas, Câmara do Poente);
- total: `8.242 XP`, `8,43%` do requisito Nv.1→11 (`97.800 XP`). Meta de 7–9% = `6.846` a `8.802 XP`.

Piso (os quatro Locais descobertos no Nv.1; o `min()` vale só no XP de Local): `4 × 120 = 480`; total `480 + 5.560 + 1.489 = 7.529 XP` = `7,70%`. A exploração fica entre `7,70%` e `8,43%`.

Braseiros permanentes obtidos por Desbravar: Vento Morto, Galhos Mortos, Poente.<br>
Masmorras descobertas por Desbravar: Cripta do Ocaso, Galerias do Vigia.<br>
Locais descobertos por Explorar: Charneca, Bosque, Ruínas, Câmara do Poente (cada um uma única vez; Missão não descobre Local).

## 11.9 Recovery normal de PvE na Charneca

**Reescrita v1.0.18.** A prioridade do Braseiro de recovery é **por Local**, nunca global, e nunca usa `LocationDiscovery`. O recovery **não** manda sempre ao Refúgio: volta ao Braseiro do próprio Local.

| Local de origem | Ponto de recovery (prioridade) |
|---|---|
| Estrada das Cinzas | Braseiro da Estrada |
| Charneca da Fuligem (§11.9) | Braseiro do Vento Morto, senão Refúgio |
| Bosque Calcinado (§29.9) | Galhos Mortos, senão Vento Morto, senão Refúgio |
| Ruínas do Vigia (§30.7) | Poente, senão Galhos Mortos, senão Vento Morto, senão Refúgio |
| Câmara do Poente | **Refúgio do Ocaso** (não tem Braseiro) [DECIDIDO 2026-11-14] |

Como Charneca, Bosque e Ruínas podem ser descobertos antes das Missões, o recovery segue o Braseiro permanente descoberto. A volta de qualquer Local ao Refúgio é direta e gratuita pelo hub.

Esta regra regional aplica-se ao conteúdo normal da Charneca (liberado na descoberta do Local, **v1.0.18**): Caçada Manual, combate originado por Desbravar, derrota durante Ronda de Caça e encontro roteirizado de S2. Ela não se aplica à derrota roteirizada da P2. Para recovery originado na Charneca, o destino é determinado de forma fixa pela descoberta persistente do Braseiro do Vento Morto:

| Estado do Braseiro do Vento Morto | Ponto de recovery | Local resultante |
|---|---|---|
| Descoberto validamente como `tdo.brazier.vento_morto` | **Braseiro do Vento Morto** | **Charneca da Fuligem** |
| Ainda não descoberto | **Braseiro do Refúgio** | **Refúgio do Ocaso** |

A decisão consulta a descoberta válida do Braseiro permanente, não a `LocationDiscovery` da Charneca. Não há escolha manual do ponto de recovery, sorteio, preferência configurável ou uso do último Braseiro visitado. Conhecer a Charneca não equivale a conhecer seu Braseiro. Como o conteúdo normal da Charneca é liberado na descoberta do Local, por qualquer via, o Braseiro do Refúgio e a ligação Refúgio ↔ Charneca (hub) estão disponíveis assim que a Charneca é descoberta.

Em qualquer dos dois destinos, a recuperação segue a regra global do Braseiro permanente: a atividade/encontro derrotado termina conforme as próprias regras; o `WorldState` passa ao Local do Braseiro escolhido; HP é restaurado a `100%`; estados comuns de combate são removidos; Vigor não é restaurado; Consumíveis efetivamente usados permanecem consumidos; nenhuma recompensa adicional é concedida pelo recovery; não é criado novo encontro nem rerrolada a tentativa derrotada. Progresso e recompensas já legitimamente persistidos são preservados conforme as regras da atividade.

### Caçada Manual

Na derrota de Caçada Manual normal da Charneca, o encontro termina como Derrota e não cria recompensa econômica para o encontro derrotado. Reconnect ou callback repetido reconstrói o estado resolvido sem criar outro inimigo. Uma Caçada iniciada posteriormente é uma nova tentativa normal, não um retry do encontro derrotado.

Enquanto o recovery ocorrer no Refúgio, a tela contextual pode oferecer `[Retornar à Charneca]`. A ação usa a ligação do hub Refúgio → Charneca (v1.0.18), custa `0 Vigor` e `0 Coroas`, concede `0 XP`, Coroas, Materiais ou outra recompensa, não cria encontro e não reabre a Caçada derrotada. Depois da viagem, o jogador retorna à navegação normal da Charneca e pode iniciar uma nova atividade elegível.

### Desbravar · combate

Se um combate originado por Desbravar terminar em derrota, a tentativa de Desbravar termina como falha e seu resultado não é rerrolado. Recompensas dependentes de vitória não são concedidas. Descobertas que já tenham sido legitimamente persistidas antes do combate permanecem conforme sua definição; não é criada uma segunda tentativa automática. O recovery segue a prioridade regional desta seção.

### Ronda de Caça

Uma derrota durante Ronda da Charneca encerra a Ronda como Derrota. Encontros anteriormente concluídos permanecem válidos, e suas recompensas legitimamente concedidas são preservadas; Consumíveis realmente usados permanecem consumidos. O recovery segue a prioridade regional desta seção. A Ronda derrotada não reinicia, não há retry do lote e nenhum encontro anterior é rerrolado. Preservar integralmente o shell global de resultado da Ronda; somente `{Nome do Braseiro}` e o Local resultante variam conforme a prioridade regional acima.

### Fronteiras desta regra

Este fechamento não altera derrota/recovery roteirizado de P2, Prólogo, P1, Braseiros de Masmorra, Retry de Masmorra nem conteúdo que tenha destino de recovery explícito próprio. Também não altera regras globais de HP, Vigor ou Consumíveis, economia, pools, recompensas ou qualquer mecânica de combate.

## 11.10 Braseiro do Vento Morto e Travessia dos Braseiros

**v1.0.18.** Removido "Nv.4+". A **Travessia dos Braseiros fica oculta nas Terras do Ocaso** (seção 33.4): a coexistência "rota terrestre × Travessia" deste texto deixa de existir. O Braseiro do Vento Morto segue como checkpoint e recovery. Regra global da Travessia intacta para outras regiões.

A descoberta do Braseiro continua sendo exclusivamente o resultado único `explore.tdo.charneca.braseiro` de Desbravar (sem trava de nível). Ao resolver validamente esse resultado e registrar `tdo.brazier.vento_morto`, o Braseiro do Vento Morto passa a ser um Braseiro permanente descoberto e um destino elegível da Travessia dos Braseiros. A descoberta não inicia viagem automaticamente. Aplicam-se todos os gates globais da Travessia: origem em Braseiro permanente válido, destino permanentemente descoberto e ausência de Foreground incompatível, além das demais regras vigentes.

A rede regional conhecida pode conter o Braseiro da Estrada, o Braseiro do Refúgio e o Braseiro do Vento Morto, conforme cada Braseiro tenha sido legitimamente descoberto pelo personagem. `LocationDiscovery` da Charneca não equivale ao registro `Brazier` do Vento Morto. Somente a resolução válida da Grande Descoberta específica registra esse Braseiro; o resultado narrativo **Vento Morto** não o descobre.

*(Histórico v1.0.17, superado pela v1.0.18: "A rota terrestre gratuita Refúgio do Ocaso ↔ Charneca da Fuligem e a Travessia dos Braseiros permanecem sistemas distintos e coexistentes". Agora vale o hub; a Travessia está oculta na região.)*

# 12. Masmorra A — Cripta do Ocaso

**Faixa recomendada:** Nv.4–7<br>
**Nível mínimo individual de entrada (v1.0.18) [DECIDIDO 2026-11-14]:** Nv.4 (início da Faixa). Quem não cumpre não entra, em Solo ou em Grupo.<br>
**Entrada:** Charneca da Fuligem<br>
**Reference level Estável/Fraturada:** 6<br>
**Ruptura:** 60<br>
**Família:** `dungeon.tdo.cripta_ocaso`<br>
**Núcleo:** Núcleo da Cripta do Ocaso

Descoberta: Desbravar na Charneca.

## Encontro 1 — Vestíbulo Raspado

Nv.4 · `1× Profanador Calcinado` · Comum · Equilibrado.

- Ferramenta Quebrada · `100% ATQ`
- Golpe Impuro · `85% ATQ` + `DEF −10% · 2T`, CD3

## Encontro 2 — Ossário da Fuligem

Nv.5 · `1× Profanador Calcinado +1× Carniçal de Fuligem`.

Função: pressão de dois alvos, redução de DEF e Sangramento.

## Encontro 3 — Guardião das Lápides

Nv.6 · Elite · Bruto.

- Pancada de Pedra · `100% ATQ`
- Lápide Partida · `85% ATQ` +1 Sangramento, CD2
- Peso dos Mortos · Preparado · `165% ATQ`

## Braseiro de Masmorra

Se sorteado para a run, aparece depois do Encontro 3:

**Braseiro do Silêncio**.

Não integra a Travessia permanente.

## Encontro 4 — Câmara dos Nomes

Nv.6 · `2× Profanador Calcinado` + `3× Lápide sem Nome`.

Cada Lápide ativa concede aos Profanadores `DEF final +5%`.

Lápide:

- HP = 20% do HP-base de um Comum do mesmo nível;
- DEF = 80% da referência;
- 0 XP / 0 Saque / 0 Bestiário.

Encontro termina ao derrotar os Profanadores.

## Encontro 5 — O Sem-Nome

Nv.7 · Chefe de Masmorra · Bruto/Controlador.

- Golpe de Lápide · `100% ATQ`
- Marca Apagada · `90% ATQ` + `AGI −10% ·2T`, CD3
- Peso do Sepulcro · Preparado · `170% ATQ`
- Mãos dos Esquecidos · AoE `80% ATQ`, CD3

Fases:

1. `100→70%` · O Guardião do Túmulo
2. `70→35%` · O Peso dos Mortos
3. `≤35%` · Ninguém Restou

Não revelar sua identidade verdadeira.

## Códice

- Cripta do Ocaso
- Camadas de Sepultamento
- Câmara dos Nomes
- O Último Guardião
- Os Sem-Nome

---

# 13. Masmorra B — Galerias do Vigia

**Faixa recomendada:** Nv.8–10<br>
**Nível mínimo individual de entrada (v1.0.18) [DECIDIDO 2026-11-14]:** Nv.8 (início da Faixa). Quem não cumpre não entra, em Solo ou em Grupo.<br>
**Entrada:** Ruínas do Vigia<br>
**Reference level Estável/Fraturada:** 9<br>
**Ruptura:** 60<br>
**Família:** `dungeon.tdo.galerias_vigia`<br>
**Núcleo:** Núcleo das Galerias do Vigia

Descoberta: Desbravar nas Ruínas.

## Encontro 1 — Corredor de Guarda

Nv.8 · `1× Vigia Rachado`.

## Encontro 2 — Junção dos Vigias

Nv.8 · `1× Vigia Rachado +1× Custódio Sem Rosto`.

## Encontro 3 — Vigia Íntegro

Nv.9 · Elite · Blindado.

- Golpe de Guarda · `100% ATQ`
- Égide Íntegra · Barreira `80% ATQ`, CD3
- Marca de Restrição · `90% ATQ` + `AGI −10% ·2T`, CD3
- Queda da Guarda · Preparado · `160% ATQ`

## Braseiro de Masmorra

Se sorteado:

**Braseiro da Vigília**.

## Encontro 4 — Câmara dos Condutores

Nv.9 · `1× Preceptor Rachado` + `2× Condutor de Guarda`.

Preceptor: Elite · Controlador.

Condutor:

- HP = 30% do HP-base de Comum do mesmo nível;
- DEF = 100% da referência;
- cada ativo concede `DEF final +10%` ao Preceptor;
- 0 XP / 0 Saque / 0 Bestiário.

Preceptor:

- Impacto Regulador · `100% ATQ`
- Peso da Ordem · `90% ATQ` + `ATQ −10% ·2T`, CD3
- Restabelecer Conduto · 1 uso/encontro; restaura 1 Condutor destruído com 50% HP e consome a oportunidade ofensiva.

## Encontro 5 — Custódio do Primeiro Selo

Nv.10 · Chefe de Masmorra · Blindado/Controlador.

- Golpe Regulador · `100% ATQ`
- Marca de Contenção · `90% ATQ` + `AGI −10% ·2T`, CD3
- Égide do Selo · Barreira `8% HP Máximo` por `2T`, CD4, máximo 2 usos
- Varredura do Selo · AoE `80% ATQ`, CD3
- Ruptura do Primeiro Selo · Preparado · `175% ATQ`

Fragmentos de Guarda:

- 2 objetos;
- HP = 25% do HP-base de Comum do nível de referência;
- cada ativo reduz dano recebido pelo Chefe em 5% final;
- 0 XP / 0 Saque / 0 Bestiário.

Fases:

1. `100→70%` · Protocolo de Guarda
2. aos `70%` · ativa 2 Fragmentos; Ordem de Contenção
3. aos `35%` · reconstitui uma única vez Fragmentos destruídos com 50% HP; Última Ordem; libera Ruptura do Primeiro Selo

## Códice

- Galerias do Vigia
- Rede de Defesa
- Câmara de Contenção
- Primeiro Selo
- Ordens que Permanecem

Não afirmar consciência das máquinas.

---

# 14. Chefe regional — Vigia Partido

**Nv.:** 10<br>
**Categoria:** Chefe normal<br>
**Arquétipo:** Equilibrado<br>
**Papel:** Chefe do P6 / clímax regional.

Stats-base utilizam diretamente o perfil global de Chefe normal:

`HP 220% / ATQ 110% / DEF 110% / AGI 100%`

antes dos demais modificadores globais pertinentes.

## 14.1 Artes

### Golpe do Vigia

`100% ATQ`.

### Marca da Sentinela

`90% ATQ` + `DEF −10% · 2T`, CD3.

### Égide Partida

Barreira `90% ATQ`, CD4.<br>
Máximo `2 usos por tentativa`.

### Varredura Fraturada

AoE `80% ATQ`, CD3.

### Peso da Ruína

`135% ATQ`, CD3.

### Queda do Ocaso

Ação Preparada · `185% ATQ`, CD5.<br>
Sempre possui telegraph completo e não aplica Hard CC.

## 14.2 Fases

### Fase I — A Sentinela

`100% → 70% HP`.

Usa Golpe do Vigia, Marca da Sentinela e Égide Partida. O objetivo é apresentar a lógica de guarda antes da ruptura do padrão.

### Fase II — A Fratura

`70% → 35% HP`.

Desbloqueia Varredura Fraturada e Peso da Ruína. Continua podendo usar as Artes da Fase I dentro de suas Recargas.

### Fase III — O Último Posto

`≤35% HP`.

Desbloqueia Queda do Ocaso. A primeira ocorrência sempre respeita o telegraph integral; a Arte segue CD5 e não pode ser usada em oportunidades consecutivas.

Não possui Cura, adds obrigatórios ou ciclo de Barreira infinito.

## 14.3 Recompensa e XP

P6 já concede sua recompensa fixa de Missão. Por isso o Vigia Partido **não concede EnemyXP genérica adicional**:

`campaign_boss_enemy_xp = 0`

A primeira vitória válida concede, uma única vez:

`1 Núcleo do Vigia Partido`

como recompensa específica do encontro, sem aplicar a tabela econômica repetível de Caçada/Boss.

A conclusão de P6 revela diretamente a Receita:

`recipe.tdo.vigia_partido.eco`

**Eco do Vigia Partido**.

Assim, a Receita não depende de um roll de 6% em um Chefe de campanha não-farmável. Se o jogador não estiver com Artífice ativo, a Receita permanece conhecida e poderá ser usada futuramente quando os requisitos forem cumpridos.

O Núcleo é consumível de procedência e não retorna na Desmontagem; a vertical slice garante um craft do Eco por primeira jornada. Fontes futuras adicionais para esse Núcleo precisam ser explicitamente configuradas.

## 14.4 Lore

A ligação com a **Âncora do Poente** só é estabelecida após o gate narrativo de P6.

Nesta região é permitido concluir apenas que:

- a estrutura é chamada Âncora do Poente;
- o Vigia Partido a protegia;
- outras Âncoras existiram.

Não revelar:

- verdadeira função cosmológica das Âncoras;
- estabilização do Véu;
- Convergência;
- sabotagem;
- Desvelados;
- Avesso.

# 15. Bestiário regional

Progressão player-facing:

`Observado → Conhecido → Estudado → Dominado`

Mapeamento técnico:

| Categoria de Combate | Perfil de Bestiário |
|---|---|
| Comum | COMMON |
| Incomum | RARE |
| Elite | ELITE |
| Chefe | BOSS |

`RARE` é nome técnico do perfil BKP e **não** renomeia uma criatura Incomum para “Rara” na UI.

## 15.1 Thresholds

- COMMON: Conhecido10 / Estudado30 + ≥2 categorias de evidência / Dominado60 + ≥3 categorias.
- RARE: Conhecido8 / Estudado22 / Dominado40 + ≥2 categorias de evidência.
- ELITE: Conhecido10 / Estudado25 / Dominado45 + vitória + mecânica/evidência especial configurada.
- BOSS: Conhecido10 / Estudado30 + ≥1 vitória + ≥2 mecânicas/fases; Dominado50 + `mastery_required` completo.

BKP e repetição usam a Fonte Mestra; esta seção apenas configura conteúdo regional.

**v1.0.18 [DECIDIDO 2026-11-14, decisão 9] — marcos únicos regionais.** Nas Terras do Ocaso, o BKP de **investigação Desbravar** e o BKP de **Habitat** (valores-base da Fonte Mestra, GDD §49.17: investigação Desbravar 8; Habitat 3) são concedidos **uma única vez** (marco único) **por criatura e por Local**. Repetir o mesmo resultado de Desbravar ou rever o mesmo Habitat não concede BKP de novo. Isto é uso do mecanismo "marcos únicos" que a Fonte Mestra já prevê (GDD, Bestiário, "Anti-farming") e não altera nenhum valor de BKP, threshold ou categoria. Checagem feita contra a Fonte Mestra v1.6.0 e reconferida na v1.7.1 (2026-11-14): sem conflito (ver seção 33.9).

## 15.2 Mundo aberto

### Cão Cinéreo

Habitat conhecido: Estrada das Cinzas / Charneca da Fuligem.<br>
Material conhecido: Couro Escoriado.<br>
Variantes: Furioso, Ágil.<br>
Sem fraqueza/resistência especial configurada.

### Corvo de Fuligem

Habitat conhecido: Estrada das Cinzas / Charneca da Fuligem.<br>
Material conhecido: Resíduo do Ocaso.<br>
Variantes: Ágil, Furioso.<br>
Sem fraqueza/resistência especial configurada.

### Peregrino Calcinado

Habitat: Estrada / Charneca.<br>
Materiais conhecidos possíveis: Ferro de Fuligem, Erva Cinzenta.<br>
Variantes: Furioso, Resistente, Hemorrágico.<br>
Origem/natureza permanece não confirmada.

### Aranha de Cinza

Habitat: Charneca / Bosque.<br>
Materiais conhecidos possíveis: Erva Cinzenta, Resíduo do Ocaso.<br>
Fraqueza: Queimadura `+10%`.<br>
Resistência: Veneno `−10%`.<br>
Variantes: Venenoso, Ágil.

### Cervo Escoriado

Habitat: Charneca / Bosque.<br>
Material conhecido: Couro Escoriado.<br>
Variantes: Furioso, Resistente.<br>
Sem fraqueza/resistência especial.

O Bestiário pode apresentar somente os Materiais conhecidos conforme o estágio e padrão Visual/UI vigentes; não exibe pesos nem porcentagens de drop.

### Carniçal de Fuligem

Habitat: Bosque / Ruínas.<br>
Fraqueza: Queimadura `+10%`.<br>
Resistência: Sangramento `−10%`.<br>
Variantes: Hemorrágico, Resistente.

### Mariposa de Brasa

Habitat: Bosque / Ruínas.<br>
Resistência: Queimadura `−10%`.<br>
Variantes: Ágil, Furioso.

### Vigia Rachado

Habitat: Ruínas do Vigia.<br>
Variantes: Resistente, Furioso.<br>
Sem fraqueza/resistência especial.

### Custódio Sem Rosto

Habitat: Ruínas do Vigia.<br>
Variantes: Resistente, Ágil.<br>
Sem fraqueza/resistência especial.

### Guardião do Último Rastro

**Perfil:** BOSS.<br>
**Habitat conhecido:** Ruínas do Vigia, em passagem roteirizada exclusiva de S6.<br>
**Variante:** nenhuma.

O Bestiário pode registrar apenas fatos observáveis: porte humanoide, equipamento de travessia desgastado, haste reforçada e as Artes efetivamente testemunhadas. Origem, identidade anterior, relação com Peregrinos e natureza ontológica permanecem ausentes enquanto não houver descoberta futura explícita que as autorize.

Esta revisão não adiciona material temático, drop exclusivo, prêmio fixo de primeira vitória ou requisito econômico próprio para o Chefe. Recompensas e progressão de S6 permanecem as já definidas para a Missão.

## 15.3 Elites de mundo aberto

### Alfa Cinéreo

Habitat: Estrada das Cinzas.<br>
Material conhecido: Couro Escoriado.<br>
Para Dominado, além do BKP Elite, exige primeira vitória, observar **Investida Rasgante** com Sangramento e testemunhar **Salto Predatório** preparado.

### Viúva da Fuligem

Habitat: Bosque Calcinado.<br>
Para Dominado, exige primeira vitória, evidência de Veneno e de redução de AGI, além do BKP Elite.

### Custódio do Poente

Habitat: Ruínas do Vigia.<br>
Para Dominado, exige primeira vitória, observar **Guarda do Poente** e **Queda do Poente**, além do BKP Elite.

## 15.4 Cripta do Ocaso

- **Profanador Calcinado** · Comum · Habitat: Cripta do Ocaso.
- **Guardião das Lápides** · Elite · Habitat: Cripta. Dominado exige vitória, observar Lápide Partida e Peso dos Mortos.
- **O Sem-Nome** · Boss · Habitat: Cripta.

`mastery_required` de O Sem-Nome:

1. ao menos 1 vitória;
2. alcançar a Fase III **Ninguém Restou**;
3. observar **Peso do Sepulcro**;
4. observar **Mãos dos Esquecidos**;
5. possuir Primeira Conclusão Estável da Cripta.

A identidade anterior do Chefe nunca é preenchida automaticamente.

## 15.5 Galerias do Vigia

- **Vigia Íntegro** · Elite · Habitat: Galerias. Dominado exige vitória, observar Égide Íntegra e Queda da Guarda.
- **Preceptor Rachado** · Elite · Habitat: Galerias. Dominado exige vitória, observar Condutores ativos e Restabelecer Conduto.
- **Custódio do Primeiro Selo** · Boss · Habitat: Galerias.

`mastery_required` do Custódio do Primeiro Selo:

1. ao menos 1 vitória;
2. alcançar Última Ordem;
3. observar Fragmentos de Guarda ativos;
4. observar **Ruptura do Primeiro Selo**;
5. possuir Primeira Conclusão Estável das Galerias.

## 15.6 Vigia Partido

**Perfil:** BOSS.

`mastery_required`:

1. concluir P6 e derrotá-lo;
2. alcançar **A Fratura**;
3. alcançar **O Último Posto**;
4. observar **Égide Partida**;
5. observar **Queda do Ocaso**.

## 15.7 Variantes

Subseções de Variante ficam completamente ausentes antes da primeira descoberta válida.

Tipos usados regionalmente:

- Furioso;
- Resistente;
- Ágil;
- Hemorrágico;
- Venenoso.

Dominar a criatura-base não revela Variante oculta. Bestiário pode mostrar materiais já conhecidos, mas nunca porcentagens de loot.

# 16. Códice regional

## Regiões e Locais

- Terras do Ocaso
- Estrada das Cinzas
- Refúgio do Ocaso
- Charneca da Fuligem
- Bosque Calcinado
- Ruínas do Vigia
- Câmara do Poente
- Cripta do Ocaso
- Galerias do Vigia

### Entrada de Códice — Câmara do Poente (v1.0.18, L9 resolvida em 2026-11-14)

**Gatilho:** a entrada é criada **na descoberta da Câmara por Explorar** (única via de descoberta, §33.2). P6 **não** cria a entrada e não descobre o Local. **Seguem a P6 de quem vê** (progresso individual, §33.15 L5) dois estados do texto; concluir P6 só **troca o texto**, não cria nova entrada.

- **Antes da P6 concluída** (sem "Âncora"; sem descrever a estrutura central). Texto `[[TEXTO_CODICE_CAMARA_PRE_P6]]`:
  > Um recinto fechado entre as pedras do Poente. Paredes de pedra escura, sem marca nem janela. O ar não se move, e o pó no chão não tem pegadas. Quem chega não encontra resposta.
- **Depois da P6 concluída** (usa só o que P6 revela). Texto `[[TEXTO_CODICE_CAMARA_POS_P6]]`:
  > Um recinto fechado entre as pedras do Poente. Os registros chamam a estrutura que há nele de Âncora do Poente, e o Vigia Partido a guardava. Outras Âncoras existiram. O que ela segurava, ninguém sabe.

A entrada de **Âncora do Poente** (Mistérios e Fenômenos) continua sendo criada só por P6.

## Figuras

- Alda Veyr
- Oren Cal

## História e Acontecimentos

- Antigos Asterianos
- Peregrinos do Ocaso
- Os Sem-Nome
- Ordens que Permanecem

## Mistérios e Fenômenos

- Marcas na Fuligem
- Luzes do Ocaso
- O Primeiro Selo
- Âncora do Poente

## Ordem narrativa

- Prólogo: Terras / Estrada
- P1: Refúgio / Alda / Oren
- S1: atualização da Estrada
- P2: Charneca / Marcas
- S2: Peregrinos
- P3: Bosque / Antigos / atualização de Marcas
- Cripta: Os Sem-Nome por descoberta/progresso/clear
- P4: Ruínas / atualização de Antigos
- Galerias: Ordens que Permanecem / O Primeiro Selo após clear
- S5: Luzes do Ocaso
- P5: Ruínas / Antigos
- S6: Peregrinos / Ruínas
- P6: Câmara do Poente / Âncora do Poente

Ao final de P6, um jogador apenas de Campanha pode saber legitimamente:

- existiram Antigos Asterianos;
- as Ruínas tinham função de guarda;
- os Vigias protegiam estruturas;
- existe uma estrutura chamada Âncora do Poente;
- outras Âncoras existiram.

Não extrapolar a função real dessas estruturas.

---

# 17. Feitos e Cosméticos

## Feitos

1. **Cinzas na Estrada** · Exploração · concluir o Prólogo em Vitória ou Derrota válida · sem cosmético.
2. **Andarilho das Cinzas** · descobrir 5 Locais principais + 5 Braseiros · Título `Andarilho das Cinzas`.
3. **Sob a Superfície** · oculto · descobrir Cripta + Galerias · sem cosmético.
4. **A Última Guarda** · derrotar Vigia Partido pela primeira vez · Título `Vigia das Cinzas`.
5. **Silêncio entre os Nomes** · primeira conclusão Estável da Cripta · sem cosmético.
6. **A Ordem Interrompida** · primeira conclusão Estável das Galerias · sem cosmético.
7. **Cinzas Fraturadas** · concluir ambas em Fraturada · Moldura `Pedra Fraturada`.
8. **Caçador do Ocaso** · alcançar Dominado nas 9 criaturas-base · Título `Caçador do Ocaso`.
9. **Entre Aquilo que Caça** · oculto · 9 criaturas-base Dominadas + 3 Elites Dominados + Variante legitimamente descoberta/requerida por tipo · Aparência `Errante das Cinzas`.
10. **Testemunha dos Guardiões** · Estudado em Vigia Rachado, Custódio Sem Rosto, Custódio do Poente, Vigia Íntegro, Preceptor Rachado, Custódio do Primeiro Selo e Vigia Partido · sem cosmético.
11. **Nomes sob a Cinza** · oculto · S2 + S6 + Cripta + primeira Estável + Trechos disponíveis de Os Sem-Nome · Título `Nome Apagado`.
12. **A Ordem Ainda Permanece** · oculto · primeira Estável Galerias + P6 + conteúdo disponível de Ordens/O Primeiro Selo/Âncora · Moldura `Vigília Antiga`.
13. **Terras do Ocaso** · P6 + Nv.10 + 5 Locais principais · Moldura `Ocaso`.

## Catálogo cosmético regional

Títulos:

- Andarilho das Cinzas
- Vigia das Cinzas
- Caçador do Ocaso
- Nome Apagado

Molduras:

- Pedra Fraturada
- Vigília Antiga
- Ocaso

Aparência:

- Errante das Cinzas

Total: **8 Cosméticos permanentes em 13 Feitos**.

Os Feitos sem Cosmético permanecem válidos, com seus requisitos, flags e registros permanentes. Não existe quota regional nem compensação automática por recompensa cosmética removida.

Não criar percentual público de “100% da região”, moeda de Feitos ou ranking regional.

---

# 18. Ofícios e crafting regional

Ofícios disponíveis no Refúgio:

- Ferreiro
- Artífice
- Alquimista
- Curteiro
- Joalheiro

## Catálogo oficial de Equipamentos regionais

### Ferreiro

- Arma do Caminhante · Principal
- Guarda do Caminhante · Secundária
- Arma Pesada do Caminhante · 2H
- Elmo de Fuligem · Cabeça
- Couraça de Fuligem · Torso
- Manoplas de Fuligem · Mãos
- Passos de Fuligem · Pés

### Curteiro

- Capuz das Cinzas · Cabeça
- Veste do Caminhante · Torso
- Luvas de Fuligem · Mãos
- Botas da Estrada · Pés

### Joalheiro

- Selo Enegrecido · Acessório
- Relicário de Cinzas · Artefato

Essas famílias usam Comum/Raro/Épico conforme requisito de Ofício.

## Equipamentos exclusivos de Campanha

P3:

- Véu do Bosque · Cabeça · Raro Nv.5
- Selo do Galho Morto · Acessório · Raro Nv.5
- Relicário da Cinza Verde · Artefato · Raro Nv.5

P6:

- Guarda do Último Posto · Torso · Épico Nv.10
- Selo do Poente · Acessório · Épico Nv.10
- Relicário da Âncora Velada · Artefato · Épico Nv.10

## Equipamentos de Receita especial

- Relicário dos Sem-Nome · Artefato · Raro
- Guarda do Primeiro Selo · Arma Secundária · Épico

### Fechamento documental

Este catálogo passa a ser o catálogo oficial de nomes individuais da vertical slice. Nomes eventualmente produzidos em rascunhos antigos e não recuperados **não fazem parte do cânone** até futura inclusão explícita por Conteúdo.

Não existe migração de Equipamento pendente para o v1.0.4 FINAL.

# 19. Runas Grau I

Famílias:

- Runa da Brasa · ATQ
- Runa da Pedra · DEF
- Runa do Caminhante · AGI
- Runa da Fresta · PER
- Runa do Presságio · CRIT
- Runa da Persistência · HP
- Runa do Desvio · Esquiva
- Runa da Guarda · Bloqueio

Potência Grau I:

| Atributo | Rara | Épica | Lendária |
|---|---:|---:|---:|
| HP | +0,35% | +0,45% | +0,55% |
| ATQ | +0,35% | +0,45% | +0,55% |
| DEF | +0,55% | +0,80% | +1,00% |
| AGI | +0,55% | +0,80% | +1,00% |
| PER | +0,25 p.p. | +0,50 p.p. | +0,50 p.p. |
| CRIT | +0,25 p.p. | +0,50 p.p. | +0,50 p.p. |
| Esquiva | +0,25 p.p. | +0,25 p.p. | +0,25 p.p. |
| Bloqueio | +0,25 p.p. | +0,50 p.p. | +0,50 p.p. |

Vertical slice normal: Rara no Ofício5; Épica no Ofício10.

---

# 20. Encantamentos Grau I

- Fio Cinéreo · ATQ
- Pele de Pedra · DEF
- Passo de Fuligem · AGI
- Marca da Fresta · PER
- Eco do Presságio · CRIT
- Sopro Persistente · HP
- Véu de Desvio · Esquiva
- Selo de Guarda · Bloqueio

Potência Grau I:

| Atributo | Raro | Épico | Lendário |
|---|---:|---:|---:|
| HP | +0,10% | +0,20% | +0,30% |
| ATQ | +0,10% | +0,20% | +0,30% |
| DEF | +0,20% | +0,40% | +0,55% |
| AGI | +0,20% | +0,40% | +0,55% |
| PER | +0,25 p.p. | +0,25 p.p. | +0,50 p.p. |
| CRIT | +0,25 p.p. | +0,25 p.p. | +0,50 p.p. |
| Esquiva | +0,25 p.p. | +0,25 p.p. | +0,25 p.p. |
| Bloqueio | +0,25 p.p. | +0,25 p.p. | +0,50 p.p. |

---

# 21. Alquimia regional

## Poção de Cura · Grau I

Ofício1.<br>
`3 Ervas Cinzentas +1 Resíduo do Ocaso +20 Coroas`.

Efeito: `22% HP Máximo`.

## Preparado de Purificação · Grau I

Ofício1.<br>
`2 Ervas Cinzentas +2 Resíduos do Ocaso +40 Coroas`.

Remove 1 efeito negativo removível.

## Antídoto Cinzento · Grau I

Ofício5.<br>
`4 Ervas Cinzentas +1 Resíduo do Ocaso +40 Coroas`.

Remove todos os stacks de um DoT removível selecionado.

## Poção de Vigor · Grau I

Ofício10.<br>
`6 Ervas Cinzentas +4 Resíduos do Ocaso +1 Catalisador de Elite I +120 Coroas`.

Efeito `+20 Vigor`; fora de combate; máximo 1/ciclo diário; exige Vigor≤80.

---

# 22. Receitas especiais regionais

## Relicário dos Sem-Nome

`recipe.tdo.cripta.relicario_sem_nome`

**Descoberta:** usa o roll global de Receita especial da Masmorra conforme a dificuldade da conclusão elegível; não é garantida na primeira conclusão.

Joalheiro5 · Artefato · Raro · Grau I · SW2.

Materiais:

- 10 Ferro de Fuligem
- 6 Resíduos do Ocaso
- 8 Fragmentos de Aprimoramento I
- 1 Núcleo da Cripta do Ocaso
- taxa normal do Craft Raro conforme item_level

Sem efeito exclusivo acima do budget Raro.

## Guarda do Primeiro Selo

`recipe.tdo.galerias.guarda_primeiro_selo`

**Descoberta:** usa o roll global de Receita especial da Masmorra conforme a dificuldade da conclusão elegível; não é garantida na primeira conclusão.

Ferreiro10 · Arma Secundária · Épico · Grau I · SW1.

Materiais:

- 7 Ferro de Fuligem
- 3 Resíduos do Ocaso
- 2 Catalisadores de Elite I
- 6 Fragmentos de Aprimoramento I
- 1 Núcleo das Galerias do Vigia
- taxa normal do Craft Épico conforme item_level

Sem proc exclusivo.

## Eco do Vigia Partido

`recipe.tdo.vigia_partido.eco`

**Descoberta:** revelação direta na conclusão de P6; não usa roll de Receita especial do Chefe de campanha.

Artífice10 · Encantamento Épico de PER · Grau I.

Materiais:

- 5 Resíduos do Ocaso
- 2 Ferros de Fuligem
- 1 Catalisador de Elite I
- 1 Núcleo do Vigia Partido
- 100 Coroas

Potência exatamente igual a um Encantamento Épico PER Grau I.

Núcleos não retornam na Desmontagem.

---

# 23. Provações de Classe · Nv.10

## 23.1 Desbloqueio e regras gerais

Ao alcançar Nv.10, o personagem recebe acesso à **única Provação da própria Classe** no **Círculo da Cinza**, conduzido narrativamente por Vael Orin no Refúgio do Ocaso.

O Círculo da Cinza:

- não é Local do Mapa;
- não é Masmorra, Caçada ou Profundeza;
- não gera Bestiário/Códice econômico;
- é uma instância exclusivamente pedagógica de Classe.

Requisitos:

- personagem Nv.10+;
- Classe válida;
- Refúgio do Ocaso conhecido;
- Provação ainda não concluída.

Não exige P6, Masmorra, Secundária, Vigor, pagamento ou Grupo.

Cada tentativa:

- é Solo;
- começa em `100% HP`;
- limpa estados temporários;
- não concede XP, Saque ou Coroas;
- não usa durabilidade nem Vigor;
- pode ser repetida imediatamente após falha, sem custo econômico.

A Provação usa apenas Ataque Básico, Defender e as Artes de Classe disponíveis até Nv.10 (`Nv.1/4/7/9`). Não antecipa Arte de Caminho.

Entidades de treinamento usam IDs `trial_entity.*`, não entram no Bestiário, não concedem Saque/XP e não contam para Feitos de criaturas.

## 23.2 Sentinela — Provação da Guarda

`trial.sentinela.guarda`

**Tema:** escolher qual impacto receber e quando transformar defesa em resposta.

### Etapa I — Suportar

Eco de Impacto executa três ações, sendo uma claramente Preparada e mais forte. A etapa recompensa Defender/Muralha Breve na ameaça correta.

### Etapa II — Abrir a Guarda

Eco Blindado possui DEF elevada. O objetivo pedagógico é utilizar **Quebra-Postura** e atacar durante a redução de DEF.

### Etapa III — Guardar e Revidar

Eco alterna ataque Preparado e janela ofensiva. O jogador deve combinar Defender/Muralha Breve, Retaliação e **Impacto Resoluto**.

Conclusão torna disponíveis:

- **Bastião · Proteção**;
- **Devastador · Pressão**.

## 23.3 Errante — Provação da Brecha

`trial.errante.brecha`

**Tema:** reconhecer e explorar uma abertura curta.

### Etapa I — Primeiro Corte

Aplicar **Ferida Profunda** e sustentar pressão com Sangramento.

### Etapa II — Passo entre Golpes

O inimigo prepara ataque forte. **Passo Velado** demonstra seu valor defensivo e a janela ofensiva subsequente; a etapa não depende de uma Esquiva RNG obrigatória para ser vencível.

### Etapa III — A Brecha

Eco entra periodicamente em estado Exposto, válido como efeito negativo. **Golpe Oportuno** deve ser utilizado em uma janela debilitada.

Caminhos:

- **Carrasco · Execução**;
- **Sabotador · Interferência**.

## 23.4 Vigia — Provação do Alvo

`trial.vigia.alvo`

**Tema:** observar, preparar e decidir onde o disparo importa.

### Etapa I — Marcar

Eco com DEF elevada; **Marca da Presa** cria a janela ofensiva.

### Etapa II — Três Disparos

Proteção de treinamento possui três pequenas camadas, uma removida por hit. **Saraivada** demonstra ataque múltiplo sem ser a única forma matemática de vencer.

### Etapa III — O Momento do Tiro

Eco alterna `Protegido → Exposto`; o jogador combina **Olho da Vigília** com Artes ofensivas na janela correta.

Caminhos:

- **Atirador · Precisão**;
- **Rastreador · Rastreamento**.

## 23.5 Tecelão — Provação dos Fios

`trial.tecelao.fios`

**Tema:** uma Arte preparar a próxima.

### Etapa I — Acender

Alvo principal + duas manifestações menores; **Chama Tecida** apresenta Queimadura e prepara sequência.

### Etapa II — Romper

Três Ecos menores tornam **Ruptura da Trama** naturalmente eficiente.

### Etapa III — Entrelaçar

Sequência de pressão exige alternância de Artes e uso de **Véu Entrelaçado**, respeitando a lógica real de Trama Encadeada: normal → Arte diferente fortalecida → normal.

Caminhos:

- **Conjurador · Ofensiva**;
- **Rúnico · Proteção**.

## 23.6 Oráculo — Provação do Presságio

`trial.oraculo.pressagio`

**Tema:** antecipar ameaça em vez de apenas reagir.

### Etapa I — O Sinal

**Sinal Funesto** demonstra redução de ATQ sobre um Eco ofensivo.

### Etapa II — Antes do Golpe

Ataque pesado anunciado pode ser respondido por **Vislumbre**, **Véu Premonitório** ou Defender; não existe solução única.

### Etapa III — O Futuro Possível

O Eco alterna janela ofensiva e preparação perigosa. O jogador decide quando usar **Ruína Predita** e quando preservar resposta defensiva.

Caminhos:

- **Agoureiro · Presságio**;
- **Invocador · Manifestações**.

As manifestações do Invocador continuam sendo efeitos do Oráculo, não pets/combatentes independentes.

## 23.7 Luminar — Provação da Luz

`trial.luminar.luz`

**Tema:** decidir entre sustentar e julgar.

### Etapa I — Sustentar

Um **Eco Aliado** possui HP, não possui turno ofensivo e existe somente na Provação. O Luminar deve impedir sua derrota com **Renovação** e/ou **Égide Solar**.

### Etapa II — Julgar

Eco inimigo possui recuperação periódica de treinamento; **Julgamento** demonstra redução de Cura recebida.

### Etapa III — Escolha de Prioridade

Luminar e Eco Aliado sofrem pressão simultânea. O jogador decide entre Cura, Barreira, ataque e redução de Cura.

Caminhos:

- **Guardião · Proteção**;
- **Inquisidor · Julgamento**.

## 23.8 Conclusão e escolha

Ao concluir:

`class_trial_completed = true`

permanente através do Legado.

Então:

- os dois Caminhos daquela Classe ficam permanentemente disponíveis;
- jogador escolhe o Caminho inicial sem custo;
- Passiva e modificadores inerentes do Caminho escolhido entram em vigor;
- primeira Arte de Caminho permanece bloqueada até Nv.12.

A performance nunca escolhe, recomenda ou bloqueia um Caminho.

Antes da confirmação, mostrar Preview do Caminho, Passiva e modificadores inerentes. Após confirmar, usar o fluxo normal de Personagem → Caminho definido na Fonte Visual/UI.

Troca posterior não repete a Provação: usa o sistema normal de troca em local apropriado e custo em Coroas definido pela Fonte Mestra.

Fluxo recomendado da primeira jornada:

`Nv.10 → segundo Ponto de Talento → Provação → escolha de Caminho → P6`

P6 não é requisito da Provação; essa ordem apenas permite experimentar a Passiva de Caminho no clímax regional.

## 23.9 Fechamento implementável — checkpoints e configuração

As regras desta seção completam os parâmetros de implementação das seis Provações sem alterar as Artes do personagem, a baseline de combate ou as regras globais.

Todas as Provações:

- são individuais, no Nv.10, dentro do Círculo da Cinza;
- usam somente Ataque Básico, Defender e até três Artes de Classe aprendidas até Nv.10 e efetivamente equipadas na Configuração de Combate;
- não permitem Arte apenas aprendida e não equipada, Arte de Caminho, Arte acima do nível ou Consumível externo;
- usam entidades `trial_entity.*`, sem Variante, fora de pools comuns e sem Bestiário, Códice econômico, Feitos de criatura, XP, Coroas, Saque, Vigor ou Consumíveis externos;
- mantêm a Configuração de Combate legítima usada no início da etapa.

Cada Provação possui três etapas persistentes. A conclusão válida de uma etapa é registrada idempotentemente; a etapa seguinte torna-se corrente e o reconnect a reconstrói sem repetir etapas concluídas. A condição pedagógica é registrada uma vez durante a tentativa corrente. Derrota não a preserva para a etapa atual; checkpoints de etapas anteriores permanecem.

No início de cada etapa, o personagem começa com `100% HP`, sem estados temporários comuns ou Barreiras, com Recargas e recursos combat-scoped reiniciados. As entidades da etapa são materializadas do zero. Isso não altera Equipamentos, Talentos ou Artes equipadas.

Derrota da etapa encerra a tentativa, retorna o personagem ao Círculo da Cinza e oferece retry da mesma etapa. O retry não tem custo, não rerrola conteúdo ou parâmetros e usa nova identidade de encounter/activity quando necessário. O personagem pode sair entre tentativas ou etapas para o Refúgio do Ocaso, mantendo as etapas concluídas e a etapa corrente; pode ajustar sua Configuração de Combate antes de retornar. Não há custo para sair ou retomar.

A condição pedagógica obrigatória e a condição final de cada etapa são ambas necessárias para avançar. Derrotar todos os alvos sem cumprir a condição pedagógica não conclui a etapa.

## 23.10 Sentinela — parâmetros de treinamento

Todas as entidades a seguir são Nv.10, sem Variante.

| Etapa | Entidade | HP | ATQ | DEF | AGI | Ação e ciclo | Condição pedagógica; conclusão |
|---|---|---:|---:|---:|---:|---|---|
| I — Suportar | `trial_entity.sentinela.impacto` · Eco de Impacto | 650 | 105 | 90 | 80 | Golpe Contido `100% ATQ`; ciclo: Golpe Contido → preparar Impacto Anunciado → resolver Impacto Anunciado `165% ATQ` → Golpe Contido → repetir. | Mitigar ao menos uma resolução de Impacto Anunciado por Defender válido ou por Barreira ainda ativa de Muralha Breve que absorva pelo menos 1 ponto; então derrotar o Eco. |
| II — Abrir a Guarda | `trial_entity.sentinela.blindado` · Eco Blindado | 620 | 90 | 135 | 75 | Golpe de Pedra de Treino `95% ATQ` em toda oportunidade válida. | Aplicar Quebra-Postura validamente e causar Dano Direto enquanto o `−10% DEF · 2T` estiver ativo; então derrotar o Eco. |
| III — Guardar e Revidar | `trial_entity.sentinela.revidar` · Eco | 700 | 105 | 100 | 85 | Golpe de Guarda de Treino `100% ATQ`; ciclo: Golpe de Guarda de Treino → preparar Martelo Anunciado → resolver Martelo Anunciado `160% ATQ` → aplicar ao Eco `Guarda Aberta · DEF −20% · 1T` → repetir. | Obter Retaliação pelas regras globais de Sentinela, usar Impacto Resoluto enquanto a Retaliação for válida, sobreviver ao ciclo e derrotar o Eco. Não exigir crítico. |

`Guarda Aberta` é estado exclusivo desta Provação.

## 23.11 Errante — parâmetros de treinamento

Todas as entidades são Nv.10, sem Variante.

| Etapa | Entidade | HP | ATQ | DEF | AGI | Ação e ciclo | Condição pedagógica; conclusão |
|---|---|---:|---:|---:|---:|---|---|
| I — Primeiro Corte | `trial_entity.errante.primeiro_corte` · Eco | 580 | 95 | 85 | 90 | Corte de Treino `100% ATQ`. | Aplicar Ferida Profunda e registrar ao menos 1 tick legítimo do Sangramento dessa aplicação; então derrotar o Eco. |
| II — Passo entre Golpes | `trial_entity.errante.passo` · Eco | 620 | 105 | 85 | 90 | Corte Curto `95% ATQ`; ciclo: Corte Curto → preparar Golpe de Ruptura de Treino `165% ATQ` → resolver → repetir. | Usar Passo Velado enquanto uma ação Preparada estiver pendente e causar Dano Direto dentro da janela ofensiva de `2T` concedida por Passo Velado; então derrotar o Eco. Não exigir que ocorra Esquiva por RNG. |
| III — A Brecha | `trial_entity.errante.brecha` · Eco | 620 | 100 | 90 | 95 | Corte de Treino `95% ATQ` duas vezes; depois entra em `Exposto · 1T` sem causar dano naquela oportunidade; repetir. | Usar Golpe Oportuno enquanto Exposto estiver ativo; então derrotar o Eco. |

`Exposto` é efeito negativo de treinamento válido para Golpe Oportuno.

## 23.12 Vigia — parâmetros de treinamento

Todas as entidades são Nv.10, sem Variante.

| Etapa | Entidade | HP | ATQ | DEF | AGI | Ação e estado | Condição pedagógica; conclusão |
|---|---|---:|---:|---:|---:|---|---|
| I — Marcar | `trial_entity.vigia.marca` · Eco | 600 | 95 | 125 | 85 | Disparo de Treino `95% ATQ`. | Aplicar Marca da Presa e causar Dano Direto enquanto `−8% DEF · 2T` estiver ativo; então derrotar o Eco. |
| II — Três Disparos | `trial_entity.vigia.camadas` · Eco | 650 | 90 | 90 | 85 | Disparo de Treino `95% ATQ`; começa com 3 Camadas de Proteção de Treino. | Remover as três camadas; então derrotar o Eco. |
| III — O Momento do Tiro | `trial_entity.vigia.momento` · Eco | 650 | 100 | 90 | 90 | Disparo de Treino `100% ATQ`; por oportunidade própria alterna `Protegido → Exposto → Protegido → Exposto`. | Manter Olho da Vigília ativo e, durante Exposto, causar Dano Direto com uma Arte ofensiva; então derrotar o Eco. |

Cada Camada de Proteção de Treino reduz Dano Direto recebido em `12% final`. Reduções acumulam aditivamente somente dentro dessa mecânica: três camadas reduzem `36%`, duas `24%` e uma `12%`. Cada hit válido recebido remove uma camada, no máximo uma por hit; multi-hit pode remover uma camada por cada hit que resolver validamente. Saraivada pode remover as três em uma ação se os três hits resolverem validamente. Ataques separados também podem removê-las.

Protegido reduz Dano Direto recebido em `25% final`; Exposto não aplica essa redução.

## 23.13 Tecelão — parâmetros de treinamento

Todas as entidades são Nv.10, sem Variante. Manifestações são entidades reais de treinamento, possuem HP e podem ser alvos; recebem AoE, não entram no Bestiário e não concedem recompensa. Uma manifestação passiva não tem oportunidade ofensiva nem executa ação. Isso não cria pet ou Grupo.

| Etapa | Entidade(s) | Atributos | Ação e ciclo | Condição pedagógica; conclusão |
|---|---|---|---|---|
| I — Acender | Principal `trial_entity.tecelao.acender.principal`: HP 560, ATQ 95, DEF 90, AGI 85. Duas manifestações passivas: HP 180 e DEF 70 cada, sem ação ofensiva. | Principal usa Fio de Treino `95% ATQ`. | Chama Tecida deve aplicar Queimadura; em seguida, uma Arte diferente deve consumir Trama Encadeada. Todos os alvos hostis da etapa devem ser derrotados. |
| II — Romper | Três Ecos menores, cada um: HP 230, ATQ 55, DEF 65, AGI 80. | Cada Eco usa Pulso Menor `80% ATQ`. | Uma única Ruptura da Trama deve atingir validamente pelo menos dois dos três Ecos; então os três devem ser derrotados. Não é necessário atingir os três com a Arte. |
| III — Entrelaçar | `trial_entity.tecelao.entrelacar` · Eco: HP 680, ATQ 100, DEF 90, AGI 90. | Fio de Pressão `95% ATQ`; ciclo: Fio de Pressão → Fio de Pressão → preparar Ruptura Anunciada `160% ATQ` → resolver → repetir. | Consumir Trama Encadeada com Arte diferente pelo menos duas vezes; durante uma resolução de Ruptura Anunciada, Véu Entrelaçado deve absorver pelo menos 1 ponto; então derrotar o Eco. |

## 23.14 Oráculo — parâmetros de treinamento

Todas as entidades são Nv.10, sem Variante.

| Etapa | Entidade | HP | ATQ | DEF | AGI | Ação e ciclo | Condição pedagógica; conclusão |
|---|---|---:|---:|---:|---:|---|---|
| I — O Sinal | `trial_entity.oraculo.sinal` · Eco | 620 | 110 | 90 | 85 | Golpe do Eco `110% ATQ`. | Aplicar Sinal Funesto; o Eco deve executar ao menos uma ação ofensiva enquanto `−8% ATQ · 2T` estiver ativo; então derrotá-lo. |
| II — Antes do Golpe | `trial_entity.oraculo.antes_do_golpe` · Eco | 640 | 110 | 90 | 85 | Pressão `95% ATQ`; ciclo: Pressão → preparar Golpe Anunciado `170% ATQ` → resolver → repetir. | Durante o telegraph, responder validamente com pelo menos uma destas ações: Vislumbre, Véu Premonitório ou Defender; então derrotar o Eco. Não exigir Esquiva por RNG. |
| III — O Futuro Possível | `trial_entity.oraculo.futuro` · Eco | 700 | 110 | 95 | 90 | Pressão do Eco `100% ATQ`; ciclo: Pressão do Eco → preparar Ruptura Anunciada `165% ATQ` → resolver → aplicar ao Eco `Janela Ofensiva · DEF −15% · 1T` → repetir. | Responder a pelo menos uma Ruptura Anunciada com Defender, Vislumbre ou Véu Premonitório; usar Ruína Predita enquanto Janela Ofensiva estiver ativa; então derrotar o Eco. |

## 23.15 Luminar — parâmetros de treinamento

O Eco Aliado `trial_entity.luminar.aliado` tem HP 480 e DEF 80. Não possui ATQ, ação ou iniciativa ofensiva. Pode receber Cura, Barreira e Artes de suporte válidas; não pode ser controlado pelo jogador, não recebe XP e não entra no Bestiário. Em uma etapa que exija que permaneça vivo, chegar a HP zero falha imediatamente a etapa.

Todas as entidades são Nv.10 e não possuem Variante.

| Etapa | Inimigo | HP | ATQ | DEF | AGI | Ciclo | Condição pedagógica; conclusão |
|---|---|---:|---:|---:|---:|---|---|
| I — Sustentar | `trial_entity.luminar.sustentar` · alvo da ação: Eco Aliado | 600 | 105 | 90 | 85 | Golpe contra o Eco `105% ATQ`, sempre dirigido ao Eco Aliado. | Aplicar ao Eco Aliado Renovação com Cura efetiva ou Égide Solar com Barreira positiva; derrotar o inimigo e manter o Eco Aliado vivo. |
| II — Julgar | `trial_entity.luminar.julgar` · Eco | 650 | 95 | 90 | 85 | Ataque de Treino `95% ATQ` duas vezes → Recuperação de Treino → repetir. | Julgamento deve estar ativo durante ao menos uma Recuperação de Treino e reduzir legitimamente a Cura recebida; então derrotar o Eco. |
| III — Escolha de Prioridade | `trial_entity.luminar.prioridade` · Eco; Eco Aliado conforme acima | 720 | 105 | 95 | 90 | Atacar Luminar `100% ATQ` → atacar Eco Aliado `100% ATQ` → Recuperação de Treino `6% HP Máximo` → repetir. | Aplicar Renovação ou Égide Solar ao Eco Aliado pelo menos uma vez; reduzir ao menos uma Recuperação de Treino por Julgamento; manter Eco Aliado vivo e derrotar o inimigo. |

Recuperação de Treino substitui a ação ofensiva daquela oportunidade, cura o próprio Eco em `8% HP Máximo` na Etapa II ou `6% HP Máximo` na Etapa III, não Crita e sofre normalmente redução de Cura recebida.

## 23.16 Derrota, retry e persistência

Se HP do personagem chegar a zero em qualquer etapa, a etapa falha sem recompensa e sem manter as condições pedagógicas daquela tentativa. As etapas anteriores concluídas permanecem; o jogador retorna ao Círculo da Cinza e pode tentar novamente a mesma etapa. Não se usa recovery de Braseiro.

O retry preserva a entidade, atributos, ações, ciclos, estados de treinamento e condições fixas da etapa. A identidade técnica de uma nova tentativa pode ser nova, mas reconnect e callbacks repetidos não criam outra tentativa ou alteram os parâmetros. No começo do retry aplicam-se os resets de etapa desta seção.

Entre etapas ou tentativas, o jogador pode sair ao Refúgio do Ocaso. Sair não abandona a Provação nem apaga `trial_stage`; configuração de Artes, Talentos e Equipamento pode ser ajustada fora da atividade e a etapa corrente pode ser retomada sem custo.

## 23.17 Conclusão

Após conclusão válida da Etapa III, persistir `class_trial_completed = true` de forma idempotente. A Provação concede zero XP, zero Coroas e nenhum item. Os dois Caminhos daquela Classe tornam-se disponíveis e o jogador escolhe um; não há escolha automática por desempenho. As passivas/modificadores do Caminho escolhido seguem exatamente a Fonte Mestra §49.3. A primeira Arte de Caminho permanece bloqueada até Nv.12.

# 24. XP regional e auditoria

XP total de Nv.1→11:

`97.800 XP`.

## 24.1 Fontes fixas

### Principais

`37.120 XP` ≈ `37,96%`.

### Secundárias

`21.965 XP` ≈ `22,46%`.

A meta sistêmica é referência de composição, não cap rígido; portanto não há nerf das Secundárias por `+0,46 p.p.`.

### Exploração única configurada

**v1.0.18:** no teto `8.242 XP` = `8,43%`; no piso (todos os Locais descobertos no Nv.1) `7.529 XP` = `7,70%`. Dentro da meta de 7–9% do GDD §49.7. Conta em §11.8. Histórico v1.0.17 (sem validade): `7.049 XP` ≈ `7,21%`.

### Tutorial

Cão Cinéreo do tutorial: `320 XP` somente em Vitória e `0 XP` em Derrota; em nenhum resultado recebe separadamente o bônus genérico de primeira observação.

## 24.2 Cripta do Ocaso — primeira Estável

`reference_level=6`.

Conclusão Estável: `3.400 XP`.<br>
Primeira Conclusão `×1,60`: `5.440 XP`.

XP interna é calculada aplicando o fator de Masmorra `0,25` **antes do único round_10 final** de cada recompensa, sem arredondar EnemyXP normal intermediariamente.

Com a composição desta Fonte:

- Vestíbulo Raspado: `80`;
- Ossário: `80 +80`;
- Guardião das Lápides: `230`;
- Câmara dos Nomes: `90 +90`;
- O Sem-Nome: `550`.

Total interno: `1.200 XP`.

Primeira Estável completa, antes de outros marcos únicos:

`5.440 +1.200 = 6.640 XP`.

## 24.3 Galerias do Vigia — primeira Estável

`reference_level=9`.

Conclusão Estável: `4.050 XP`.<br>
Primeira Conclusão `×1,60`: `6.480 XP`.

XP interna:

- Corredor de Guarda: `100`;
- Junção dos Vigias: `100 +130`;
- Vigia Íntegro: `280`;
- Preceptor Rachado: `280`;
- Custódio do Primeiro Selo: `640`.

Total interno: `1.530 XP`.

Primeira Estável completa:

`8.010 XP`.

## 24.4 Bestiário

Primeira observação válida usa `1%` pelo sistema, com `FixedPercentXP`; o Cão do tutorial é exceção ao bônus de XP.

Marcos importantes de primeira vitória configurados nesta região:

- Alfa Cinéreo · ref Nv.3 · `198 XP`;
- Viúva da Fuligem · ref Nv.6 · `300 XP`;
- Custódio do Poente · ref Nv.9 · `426 XP`;
- O Sem-Nome · ref Nv.7 · `342 XP`;
- Custódio do Primeiro Selo · ref Nv.10 · `474 XP`;
- Vigia Partido · ref Nv.10 · `474 XP`.

Total desses seis marcos: `2.214 XP`.

O total efetivo de primeira observação depende do nível/referência válida de cada registro no momento em que ocorre e não é usado como gate obrigatório de progressão. Bestiário + marcos permanece dentro da banda-alvo quando o jogador interage naturalmente com a região.

## 24.5 Conversão de inimigos

`EnemyXPUnit(n) = XP_ref(n) / [20 × H(n)]`.

Valores aproximados de Comum equivalente, mesmo nível:

| Nv. | XP |
|---:|---:|
| 1 | 240 |
| 2 | 260 |
| 3 | 280 |
| 4 | 300 |
| 5 | 320 |
| 6 | 340 |
| 7 | 360 |
| 8 | 390 |
| 9 | 410 |
| 10 | 430 |

## 24.6 Gate inicial validado

Após P1, os totais dependem do resultado do Prólogo:

- Vitória: 320 + 2.400 = 2.720 / 4.800;
- Derrota: 0 + 2.400 = 2.400 / 4.800.

**v1.0.18:** a Estrada nasce descoberta com Caçada Manual e Desbravar liberados (a frase "liberam imediatamente após P1" da v1.0.17 fica superada). Os totais 2.720/4.800 e 2.400/4.800 após P1 não mudam. O loop normal liberado permite obter o XP restante sem hard lock.

## 24.7 Nv.10→11

**v1.0.18:** o valor não muda, mas o caminho até ele muda (Principais sem trava de nível; Missão não descobre Local e não paga XP de descoberta, então o ritmo das Missões não muda). O PowerlevelFactor (GDD linha 3795) se aplica à XP fixa de Missão em Coop de Chefe (P5, P6, S6).

P6 concede `14.220 /15.800 XP` (`90%`). Portanto S6 não se torna obrigatória: aproximadamente quatro Comuns Nv.10 equivalentes já cobrem a diferença em um cenário hipotético sem outra XP pendente.

## 24.8 Conclusão

Não existe hard lock conhecido de XP entre Nv.1 e Nv.11.

As duas Masmorras, todas as Secundárias, Bestiário Dominado e segredos permanecem opcionais para saída regional. A quantidade real de Caçadas/Ronda necessária deve ser validada por Alpha/Telemetria, não por nova regra estrutural.

# 25. Saída para Vales dos Enforcados

A saída da primeira jornada exige os gates estruturais globais:

- nível mínimo correspondente;
- marco de Campanha pertinente.

Terras do Ocaso não exige para saída:

- todas as Secundárias;
- ambas as Masmorras;
- Bestiário Dominado;
- todos os Feitos;
- todos os segredos.

---

# 26. Sincronização com a Fonte Visual/UI

A Fonte `ASTERION_UI_DECISOES_2026-11-16_FINAL_SYNC_v1.6.2_TDO_v1.0.18_VALES_v1.0.6.md` é a autoridade player-facing vigente. Esta revisão aplica a regra global de Grupo e atualiza a compatibilidade de P1 e o formato cooperativo de S6; as demais decisões de apresentação permanecem na Fonte Visual/UI. A Fonte Mestra vigente é v1.7.1.

As decisões gerais de interface já consolidadas — padrão de Missões, HUD de combate, Menu Principal, Braseiros, Códice, navegação, P1 e apresentação de Equipamentos/Runas — continuam válidas.

A camada específica de P1 — sinais da Estrada, transições, Alda/Oren, ativação do Braseiro do Refúgio, conclusão, recovery e reconnect — já está consolidada na Fonte Visual/UI vigente. Não existe pendência player-facing de P1 conhecida nesta revisão. A seção 60 da Fonte Visual/UI consolida P2, Charneca da Fuligem e sua rota terrestre conforme as regras regionais desta v1.0.8.

As faixas já sincronizadas permanecem (v1.0.18: como **faixa recomendada**, sem efeito de acesso):

- `Cripta do Ocaso · Nv.4–7`;
- `Galerias do Vigia · Nv.8–10`.

**v1.0.18 — sincronização pendente.** A navegação de mapa único (Refúgio como hub, Explorar, Caçar com escolha de Local, tela do Local, Câmara com dois textos de entrada, mensagem de bloqueio de Caçada em Grupo) muda a estrutura de telas, que pertence à Fonte Visual/UI. O delta de apresentação está em `docs/specs/RASCUNHO_DELTA_FONTE_VISUAL_UI_TDO_v1.0.18.md`. **A Fonte Visual/UI não foi editada.** Até o autor aprovar e sincronizar a Visual/UI, a apresentação segue o documento de 2026-10-13 e o delta é só rascunho.

O estágio final player-facing do Bestiário permanece **Dominado**.

---

# 27. Estado de implementação

## Conteúdo regional fechado

Pode seguir para implementação utilizando conjuntamente as três fontes oficiais vigentes:

- tutorial/prólogo;
- 12 Missões completas;
- 5 NPCs persistentes;
- Locais e Braseiros;
- Caçadas e Ronda;
- Variantes;
- Desbravar;
- duas Masmorras;
- Chefes;
- Bestiário;
- Códice;
- Feitos;
- Provações;
- materiais;
- catálogo de Equipamentos;
- crafting Grau I;
- Runas e Encantamentos;
- Alquimia;
- Receitas especiais;
- XP repetível;
- gates Nv.1→11.

Não existe bloco regional conhecido aguardando migração textual.

**v1.0.18:** a lista acima descreve o conteúdo regional fechado; a implementação das mudanças de navegação, acesso, XP e nível da v1.0.18 (seção 33) é trabalho novo do `programmer`, usa o override da Fonte Mestra já registrado no `SOURCE_AUTHORITY.md` (33.14) e da sincronização da Fonte Visual/UI (seção 26). Nenhum código foi alterado por esta consolidação.

---

# 28. Autoridade e manutenção

Este arquivo é a **Fonte oficial de Conteúdo das Terras do Ocaso v1.0.18 FINAL** (base v1.0.17 FINAL). **Vigente desde a Sincronização 2026-11-14 do `SOURCE_AUTHORITY.md`**, que substituiu a v1.0.17 FINAL.

Hierarquia:

1. Fonte Mestra estrutural vigente;
2. Fonte Visual/UI vigente;
3. esta Fonte regional para conteúdo específico das Terras do Ocaso.

Em conflito:

- sistema/regra global → Fonte Mestra;
- apresentação/UI → Fonte Visual/UI;
- nomes, encontros, missões, pools, lore permitido e conteúdo regional → esta Fonte.

Ajustes futuros oriundos de testes reais devem ser tratados como:

**Balanceamento / Telemetria / Patch de Conteúdo**

e não como reabertura informal deste arquivo.

As regras estruturais e semânticas globais necessárias estão incorporadas na Fonte Mestra vigente. A camada de apresentação geral e as apresentações específicas de P1 e P2 estão cobertas pela Fonte Visual/UI vigente.

Esta Fonte regional pode ser usada como autoridade de conteúdo e regras específicas das Terras do Ocaso em conjunto com a Fonte Mestra vigente e a sincronização Visual/UI vigente.

**Correções v1.0.10:** fechamento implementável de P3 — Sob Galhos Calcinados; entrada missionária no Bosque; fragmentos de construção; encontro pedagógico com Cervo Escoriado; escolha idempotente de Equipamento; conteúdo normal do Bosque; Carniçal, Mariposa e Viúva; pools de Caçada/Desbravar; rota Charneca ↔ Bosque; Travessia e Braseiro dos Galhos Mortos; recovery regional determinístico. Nenhum valor global de economia ou combate foi alterado.

---

# 29. Fechamento implementável v1.0.10 — P3 e Bosque Calcinado

Esta seção fecha as decisões de implementação de P3 e do Bosque Calcinado. Em divergência com descrições anteriores deste documento, esta seção prevalece para P3/Bosque. A Fonte Mestra continua sendo autoridade para regras globais.

> **v1.0.18 — prevalece sobre esta seção 29 onde a contrariar:** sem Nv.5+ em P3; o Bosque é descoberto por Explorar e a Missão não o descobre; sem "modo missionário" do Bosque; sem rota Charneca ↔ Bosque (hub: Refúgio ↔ Bosque); Desbravar sem recarga de 5 min e sem limite de 6 por 60 min; sem "Nv.6+" nas Grandes Descobertas; nível do inimigo = nível do Local; recovery pela prioridade por Local (29.9, inalterada). Detalhes em 33.

## 29.1 P3 — Sob Galhos Calcinados

**Tipo:** Missão Principal. **Giver:** Oren Cal. **Oferta/conclusão:** somente no Refúgio do Ocaso. **Requisitos (v1.0.18):** P2 concluída e Bosque já descoberto por Explorar; sem Nv.5+. S2 não é requisito. Visualizar oferta não cria Quest; aceite explícito cria uma única Quest. P3 não pode ser abandonada.

Etapas, nesta ordem:

1. Entrar no Bosque Calcinado.
2. Localizar três fragmentos de construção entre raízes e cinza.
3. Vencer o encontro roteirizado com Cervo Escoriado e ataque Preparado.
4. Examinar o fragmento entalhado.
5. Retornar a Oren Cal com o registro.
6. Escolher exatamente um dos três Equipamentos Raros de Campanha.

A condição da etapa 3 é **Vitória**. “Sobreviver” em formulações anteriores significa vencer; derrota mantém a etapa ativa.

## 29.2 Acesso missionário, descoberta e fragmentos

**v1.0.18:** após o aceite no Refúgio, o personagem continua no Refúgio. O acesso ao Bosque (já descoberto por Explorar) ocorre pela ligação do hub Refúgio → Bosque. Essa passagem custa zero Vigor/Coroas, concede zero XP/Materiais, não cria encontro e não é Travessia dos Braseiros. A chegada **não** registra `tdo.location.bosque_calcinado` nem `route.tdo.charneca_bosque`. **Não existe "modo missionário"**: com P3 ativa, o Bosque descoberto oferece Caçada, Desbravar e circulação normais. *(Histórico v1.0.17: rota Refúgio → Charneca → Bosque, descoberta na chegada, modo missionário.)*

A etapa 2 possui somente os objetivos persistentes p3.fragment.1, p3.fragment.2 e p3.fragment.3. Podem ser examinados em qualquer ordem e cada um avança uma vez. Não são itens, Materiais, resultados de Desbravar ou recompensa econômica. O terceiro fragmento inicia diretamente o combate, sem confirmação.

## 29.3 Encontro P3, vitória e derrota

O encontro usa Cervo Escoriado, Nv.5, Comum, Bruto, Solo, sem Variante (variant_roll=false), como encontro de Missão. Não cria HuntContext, não consome Vigor e não libera Familiaridade. Usa o motor compartilhado. A primeira ação inimiga elegível prepara Carga do Ocaso e mantém o telegraph e a response window globais. Após essa primeira Carga, o Cervo segue o ciclo normal existente. Esta instrução só personaliza a instância P3 e não altera a IA normal do Cervo.

Na Vitória, pode ser concedida somente a EnemyXP normal do Cervo Comum Nv.5, de forma idempotente por atividade; Bestiário segue os critérios globais. Não há Coroas/Materiais/Equipamento/Runa/Fragmento de Hunt, Familiaridade ou settlement de Caçada.

Na Derrota, a atividade termina e P3 permanece na etapa 3, com os fragmentos preservados. Não há recompensa de Vitória, reroll, Variante ou reabertura automática. Uma nova tentativa exige ação explícita, recebe novo encounter_id e materializa o mesmo Cervo Nv.5 sem Variante; a primeira ação elegível prepara Carga novamente. Reconnect e callback stale não criam tentativa.

Recovery do encontro roteirizado P3 usa a mesma prioridade regional do PvE normal do Bosque, descrita em 29.9. HP e estados seguem o recovery global; Vigor não é restaurado e Consumíveis usados permanecem consumidos.

## 29.4 Fragmento entalhado, retorno e conclusão

Após Vitória, a ação Fragmento Entalhado registra progresso narrativo da Quest. Não é item e não concede economia nem resultado de Desbravar. O registro autorizado é material/arquitetônico; não identifica autoria ou finalidade cosmológica.

**v1.0.18:** o retorno é direto, Bosque → Refúgio (hub). A frase da v1.0.17 "Bosque → Charneca e Charneca → Refúgio… não existe atalho Bosque → Refúgio" fica superada. Não há teleporte nem Travessia artificial. Oren só interage localmente no Refúgio.

Após a interação de conclusão com Oren, mostrar as escolhas:

1. **Véu do Bosque** · Cabeça · Raro · item_level 5 · +0 · Vinculado ao Adquirir.
2. **Selo do Galho Morto** · Acessório · Raro · item_level 5 · +0 · Vinculado ao Adquirir.
3. **Relicário da Cinza Verde** · Artefato · Raro · item_level 5 · +0 · Vinculado ao Adquirir.

A escolha materializa exatamente um item pelo orçamento normal de Equipamento Raro Nv.5 do slot: nome, slot, raridade e nível são fixos; +0; sem Runa/Encantamento; bound=true. A distribuição de core e secondary usa o materializador normal. A seed é determinística por source P3, personagem e escolha. Reabrir a tela não rerrola os atributos.

Escolha válida conclui P3 atomicamente e concede 4.400 XP, 180 Coroas e exatamente o item escolhido, sem Material. Usar RewardEvent/delivery normal, incluindo Pending/BlockedDelivery; o item não pode desaparecer por inventário cheio. Callback duplicado não muda a escolha nem repete entrega, XP ou Coroas.

Na conclusão, criar idempotentemente codex.history.antigos_asterianos e atualizar codex.mystery.marcas_na_fuligem somente com associação material/arquitetônica prudente. Não revelar função de Âncoras, Primeiro Selo, Avesso, Convergência, Desvelados ou explicação cosmológica reservada.

## 29.5 Conteúdo normal e gates do Bosque

Local tdo.location.bosque_calcinado, label Bosque Calcinado, faixa player-facing Nv.5–8 (recomendada), região Terras do Ocaso, sem sub-região. **v1.0.18:** a descoberta do Bosque por Explorar libera hunt_manual.bosque_calcinado e explore.bosque_calcinado; P3 concluída não libera mais nada disso nem a rota (que saiu). P3 não libera Ronda: somente a primeira vitória de Caçada Manual normal no Bosque cria hunt_round.bosque_calcinado. Explore, viagem e P3 não concedem Familiaridade.

Perfil de Caçada (v1.0.18: em Solo sem filtro por `unlock_level`; em Grupo vale o `unlock_level` individual, §10.1):

| Criatura | Unlock | Máximo | Peso |
|---|---:|---:|---:|
| Cervo Escoriado | 4 | 7 | 27 |
| Carniçal de Fuligem | 5 | 8 | 30 |
| Aranha de Cinza | 3 | 6 | 20 |
| Mariposa de Brasa | 6 | 9 | 20 |
| Viúva da Fuligem | 6 | 7 | 3 |

Variante: 12%; Viúva sem Variante. **v1.0.18:** em Solo as cinco entradas participam desde o primeiro acesso (removido "No Nv.5 são elegíveis Cervo, Carniçal e Aranha"). Elite interrompe Ronda antes do combate automático pelo mecanismo existente.

## 29.6 Criaturas e materiais temáticos

**Carniçal de Fuligem**: Comum, Bruto, Nv.5–8. Dilacerar: 90% ATQ, +1 Sangramento, CD2. Arrancada: 125% ATQ, CD3. Fraqueza Queimadura +10%; resistência Sangramento −10%; variantes Hemorrágico/Resistente. IA determinística repetida: Dilacerar → Arrancada → Dilacerar → Defender; o ciclo de quatro oportunidades repete e cooldowns do engine são respeitados. Sem RNG ou condições por HP/build. Pool temático compartilhável com Ruínas salvo override: Ferro de Fuligem 50 / Resíduo do Ocaso 50. Em Hunt Common, primeiro 80% global → 1 Material; só então sorteio temático.

**Mariposa de Brasa**: Incomum, perfil Bestiário RARE, Conjurador, Nv.6–9. Toque Incandescente: 80% ATQ, +1 Queimadura, CD2. Clarão de Cinzas: 120% ATQ, CD3. Resistência Queimadura −10%; variantes Ágil/Furioso. IA determinística repetida: Toque Incandescente → Clarão de Cinzas → Toque Incandescente → Defender; respeita cooldowns, sem RNG/HP/build. Pool compartilhável com Ruínas salvo override: Erva Cinzenta 50 / Resíduo do Ocaso 50. Mantém a economia global Incomum: 100% → 1–2 Materiais; resolver quantidade primeiro e usar sub-roll independente 50/50 por ordinal, sem forçar diversidade.

**Viúva da Fuligem**: Elite, Controlador, Nv.6–7, peso 3 somente nos pools normais de Hunt/Round; não entra em Explore combat e não tem Variante. Picada da Viúva: 80% ATQ, +1 Veneno, CD2. Teia de Fuligem: 75% ATQ, AGI −15% por 2T, CD3. Bote da Viúva: 130% ATQ, CD3; contra alvo com Veneno ativo, +10 pontos percentuais de PER somente nessa ação. IA determinística repetida: Picada → Teia → Bote → Picada → Defender; respeita cooldowns, não usa Hard CC e não é adaptada por build/HP. Bote recebe somente seu modificador da ação, não um buff persistente. Pool temático: Erva Cinzenta 50 / Resíduo do Ocaso 50, uma subescolha independente por unidade, mantendo a economia Elite global.

Bestiário: Carniçal Common com Habitat Bosque/Ruínas, fraqueza Burn e resistência Bleed; Mariposa RARE com Habitat Bosque/Ruínas e resistência Burn; Viúva Elite com Habitat Bosque e evidências de primeira vitória (referência Nv.6 → 300 XP), Veneno observado, redução de AGI observada e BKP Elite, sempre pelo BestiaryRecorder/idempotência existente.

## 29.7 Desbravar normal do Bosque

Usa categorias globais 8/22/15/25/10/20 e anti-repeat local vigente. **v1.0.18:** sem cooldown de 5 minutos e sem máximo de 6/Local/60 minutos; vale o anti-spam técnico de 3 s (§11.1). Se uma categoria não possuir subresultado elegível, seu peso é removido antes do draw e redistribuído entre as categorias elegíveis. Subresultados:

- **Grande Descoberta:** Braseiro dos Galhos Mortos (explore.tdo.bosque.braseiro) 50 / Estrutura Enterrada (explore.tdo.bosque.estrutura_enterrada) 50. Ambos únicos, ref Nv.6 (v1.0.18: sem "exigem Nv.6+"), XP800. Ambos consumidos removem a categoria.
- **Conhecimento:** Caminho Ocidental (explore.tdo.bosque.caminho_ocidental) único, peso60, ref Nv.6, XP250 e known_path.tdo.caminho_ocidental; conhecimento geográfico, sem efeito de acesso (v1.0.18). Rastros entre os Galhos, repetível, peso40, oferece somente evidência contextual conhecida de Cervo/Carniçal/Aranha/Mariposa.
- **Narrativo:** Árvores que Ainda Fumegam 55 / Cinzas sob as Raízes 45; repetíveis, sem XP permanente.
- **Combate:** Cervo25 / Carniçal30 / Aranha20 / Mariposa25; sem level gate antes do draw em Solo (v1.0.18); sem Viúva. exploration_combat normal.
- **Pequeno Recurso:** Couro Escoriado35 / Erva Cinzenta30 / Resíduo do Ocaso35; sem Ferro.
- **Atmosférico:** Troncos Ocos34 / Brasa sob a Casca33 / Som entre os Galhos33; sem economia, estado ou XP extra.

Combat/resource preservam integralmente as regras globais de Desbravar (Vigor, Coroas, Material e XP, inclusive low vigor), material temático vem da criatura em combate, e recibos/unique são idempotentes. Não acrescentar economia a narrativa/atmosfera.

## 29.8 Rota terrestre, Braseiro e Travessia

**v1.0.18:** a rota `route.tdo.charneca_bosque` **deixa de ser caminho de jogo**; vale a ligação do hub Refúgio ↔ Bosque (gratuita, sem XP, encontro ou reward, fora de combate; callback stale revalida origem, destino e foreground). A Travessia por Brazier fica oculta na região (33.4).

explore.tdo.bosque.braseiro registra tdo.brazier.galhos_mortos ao resolver validamente a descoberta única (v1.0.18: sem Nv.6+). LocationDiscovery não concede Brazier. Não há viagem automática. O Braseiro dos Galhos Mortos segue como checkpoint e recovery.

## 29.9 Recovery normal do Bosque

Para derrota normal de Hunt, combate de Explore, Ronda e encontro roteirizado P3, selecionar o destino sem RNG e sem escolha do jogador, nesta prioridade:

1. se tdo.brazier.galhos_mortos foi legitimamente descoberto: **Braseiro dos Galhos Mortos**, WorldState Bosque Calcinado;
2. senão, se tdo.brazier.vento_morto foi legitimamente descoberto: **Braseiro do Vento Morto**, WorldState Charneca da Fuligem;
3. senão: **Braseiro do Refúgio**, WorldState Refúgio do Ocaso.

Em todos os casos: HP 100%, estados comuns removidos conforme recovery global, Vigor preservado, Consumíveis usados continuam consumidos, atividade derrotada encerrada, sem recompensa de recovery ou reroll automático. Recompensas válidas de encontros anteriores da Ronda e persistências válidas anteriores permanecem. Uma nova Hunt, Explore ou tentativa P3 precisa de ação explícita. Nenhum retry ignora rota terrestre.

## 29.10 Fronteiras

Esta consolidação não implementa S3, P4, Ruínas do Vigia, Cripta, Galerias, dungeon gameplay ou novas economias globais. Não altera CURRENT_COMBAT_RULESET, Fonte Mestra v1.4.8, conteúdo de Vales, pools/regras existentes de Estrada/Charneca nem qualquer valor global de XP, Crown, Material, Equipamento, Runa, Vigor ou Consumíveis. Nenhuma migration é prevista.

# 30. Fechamento implementável v1.0.11 — S3, P4 e Ruínas do Vigia

Esta seção fecha S3, P4 e o Local normal Ruínas do Vigia. Em divergência de formulações anteriores, esta seção prevalece para estes conteúdos. A Fonte Mestra v1.4.8 continua autoridade para regras globais. Não implementa S4, S5, P5, P6, Câmara do Poente ou gameplay das Galerias.

> **v1.0.18 — prevalece sobre esta seção 30 onde a contrariar:** sem Nv.5+ (S3), Nv.7+ (P4) e Nv.8+ (Ruínas, rota, Galerias); as Ruínas são descobertas por Explorar e P4 não as descobre; sem rota Bosque ↔ Ruínas (hub: Refúgio ↔ Ruínas); Desbravar sem cooldown de 5 min e sem limite de 6/Local/60 min; nível do inimigo = nível do Local (`max_enemy_level`), sem `min(player_level, …)`; recovery 30.7 inalterado. Detalhes em 33.

## 30.1 S3 — Rastros sob os Galhos

S3 é missão Curta de Alda Veyr, oferecida e concluída somente no Refúgio do Ocaso. Requisitos (v1.0.18): Bosque descoberto por Explorar e P3 ativa ou concluída; sem Nv.5+. Visualizar a oferta não cria Quest; aceite explícito cria/reutiliza uma única Quest. S3 pode ser abandonada e reaceita conforme S1. S3 não exige P3 concluída. (Removida a frase "não libera gameplay normal do Bosque enquanto P3 estiver ativa".)

Etapas: examinar rota de suprimentos interrompida; seguir três rastros persistentes em qualquer ordem; derrotar Cervo Escoriado; verificar carga abandonada; reportar a Alda. Rastros e carga são progresso de Quest, sem XP individual, item, Material, ExploreAttempt, economia ou nova entrada de Códice. P3 e S3 possuem progresso e encontros independentes.

O encontro usa Cervo Escoriado Nv.5, Common/Brute, Solo, sem Variante, HuntContext, Vigor ou Familiaridade. Usa Chifrada e Carga do Ocaso Preparada no motor compartilhado. Vitória é obrigatória. Pode conceder EnemyXP normal e Bestiário legítimo, sem settlement de Hunt, Coroas/Materiais/Equipamento/Runa/Fragmento de Hunt ou Familiaridade. Derrota encerra a tentativa, mantém missão e rastros, não concede reward de vitória nem rerrola. Retry explícito cria novo encounter_id para o mesmo Cervo Nv.5 sem Variante. Recovery segue 30.9.

A conclusão local com Alda concede uma vez 1.760 XP, 90 Coroas e 2 Couros Escoriados vinculados. Carga não é item nem reward. Não se cria entrada de Códice. Reconnect/callback repetido não duplica progresso, encontro ou recompensa.

## 30.2 P4 — Pedras que Ainda Vigiam

P4 é Missão Principal de Alda Veyr, oferecida no Refúgio, com P3 concluída e as Ruínas já descobertas por Explorar (v1.0.18; sem Nv.7+). S2/S3 não são requisitos. Visualizar não cria Quest; aceite explícito cria uma única P4. Caminho Ocidental de Explore não é requisito. P4 não libera Ronda.

Etapas: seguir Caminho Ocidental desde o Bosque; alcançar limites das Ruínas; vencer Vigia Rachado roteirizado; examinar duas estruturas; identificar rota segura de retorno; reportar a Alda e Oren. Estruturas e rota são progresso de Quest, sem item, XP ou ExploreAttempt. Reportes locais no Refúgio podem ocorrer em qualquer ordem; ambos são necessários para concluir.

**v1.0.18:** a chegada às Ruínas (já descobertas) parte do Refúgio (hub) e não exige/consome a descoberta única `explore.tdo.bosque.caminho_ocidental` nem paga seu XP. A chegada **não** registra `tdo.location.ruinas_do_vigia` nem `route.tdo.bosque_ruinas`. O bloqueio de "conteúdo normal, rota normal e Travessia pelas Ruínas" durante P4 é **removido**. Sem "Nv.8+" e sem rota.

Vigia Rachado roteirizado Nv.7, Common/Armored, Solo, sem Variante, HuntContext, Vigor ou Familiaridade. Usa motor compartilhado e Guarda Rachada (Barreira 70% ATQ por 2T, CD3). Vitória obrigatória. Pode conceder somente EnemyXP normal e Bestiário legítimo. Sem settlement, Material, Coroas, Equipment, Rune, Fragment ou Familiaridade. Derrota encerra a tentativa, preserva progresso e discovery, usa recovery 30.9; retry explícito cria novo encounter_id do mesmo Vigia Nv.7.

Após duas estruturas, identificar rota segura (progresso de Quest). **v1.0.18:** o retorno é direto, Ruínas → Refúgio (hub); "Ruínas→Bosque→Charneca→Refúgio" fica superado. Alda e Oren recebem reportes no Refúgio em qualquer ordem. Conclusão atômica concede uma vez 5.700 XP, 250 Coroas, 2 Ferros de Fuligem vinculados e 2 Resíduos do Ocaso vinculados; atualiza prudentemente codex.history.antigos_asterianos. Não libera Hunt/Explore (já liberados na descoberta) e não libera Ronda.

## 30.3 Faixa e acesso normal

Local tdo.location.ruinas_do_vigia, Ruínas do Vigia, Terras do Ocaso, faixa player-facing Nv.8–10. A faixa é apresentação/recomendação. **v1.0.18:** acesso normal = `LocationDiscovery` (Explorar) e Foreground compatível; sem "P4 concluída" e sem "Nv.8+". A rota route.tdo.bosque_ruinas **saiu**; vale a ligação do hub Refúgio ↔ Ruínas (gratuita, sem XP/Vigor/Coroas/Materiais/encontro). Travessia oculta na região.

## 30.4 Barreira inimiga

Guarda Rachada, Proteção Antiga e Guarda do Poente aplicam Barreira própria por 2T, floor(ATQ × coeficiente): 70%, 80%, 90%. A aplicação consome oportunidade normal e respeita CD. Duração conta nas oportunidades do afetado; aplicação na própria oportunidade não consome duração nela. Mesma fonte substitui valor e duração conforme regra global. Novos campos opcionais de Action usam defaults neutros; snapshots antigos continuam decodificáveis; ruleset histórico não muda.

## 30.5 Criaturas e pools

Vigia Rachado: Common/Armored, Nv.7–10, Hunt peso32, variantes Resistente/Furioso; Golpe de Pedra100%; Guarda Rachada Barreira70% ATQ/2T/CD3. Política PvE global: especial elegível como prioridade, Golpe como fallback. Pool: Ferro de Fuligem50/Resíduo do Ocaso50.

Custódio Sem Rosto: Uncommon, Bestiary RARE, Controller, Nv.8–10, peso20, variantes Resistente/Ágil. Marca do Peso90%, AGI−10%/2T/CD3; Proteção Antiga Barreira80%/2T/CD3; Impacto120%/CD3. Política determinística global. Pool: Ferro50/Resíduo50.

Custódio do Poente: Elite/Armored, Nv.9–10, peso3, sem Variante. Golpe do Custódio100%; Guarda do Poente Barreira90%/2T/CD3; Marca do Poente85%, DEF−10%/2T/CD3; Queda do Poente Preparada170%/CD4. Não reaplica Guarda enquanto sua Barreira está ativa; busca Marca quando disponível antes de janela ofensiva; Queda usa telegraph completo. Sem cura/Hard CC. Interrompe Ronda pelo mecanismo Elite existente. Pool: Ferro50/Resíduo50. Economia Elite global preservada.

Carniçal mantém Ferro50/Resíduo50; Mariposa mantém Erva50/Resíduo50. Pools por criatura, sem alterar chance/quantidade/Categoria global, cada unidade com sub-roll próprio.

## 30.6 Hunt, Explore e Round

Hunt Ruínas: Carniçal25, Vigia32, Mariposa20, Custódio Sem Rosto20, Custódio do Poente3; variante15%. **v1.0.18:** em Solo o pool completo (inclui Poente) está disponível desde o primeiro acesso; `enemy_level` = `max_enemy_level` da criatura (removido `min(player_level,max_enemy_level)`); em Grupo vale o `unlock_level` individual (§10.1). Viúva fora do perfil.

Explore usa categorias globais 8/22/15/25/10/20 e anti-repeat local (v1.0.18: sem cooldown de 5 min e sem limite de 6/Local/60 min; anti-spam técnico de 3 s). Grande: Braseiro do Poente explore.tdo.ruinas.braseiro, único peso50 ref9 XP1136; Galerias explore.tdo.ruinas.galerias, único peso50 ref9 XP1136 (v1.0.18: sem `min Nv.8`). Ambos elegíveis quando não consumidos. Conhecimento: Estruturas de Guarda única peso40 ref9 XP355; Ocupação Posterior única peso40 ref9 XP355; Marcas de Patrulha repetível peso20. Narrativo: Passos onde Ninguém Passa50; Pedra ainda em Vigília50. Combate: Vigia35, Custódio Sem Rosto30, Carniçal20, Mariposa15; sem Custódio do Poente (v1.0.18: sem filtro de nível antes do sorteio em Solo). Recurso Ferro45/Resíduo35/Erva10/Couro10. Atmosférico Porta que Não Abre34/Estátua sem Rosto33/Eco sob a Pedra33, sem revelar P5. Reference level é XP reference, não gate, salvo min_level explícito. Economia/cooldown/rate seguem pipeline global.

Braseiro registra permanentemente tdo.brazier.poente sem viagem automática; LocationDiscovery não equivale a Brazier. Após descobrir, integra Travessia. Galerias registra dungeon.tdo.galerias_vigia e known_path.tdo.galerias_vigia, somente descoberta/caminho conhecido, sem gameplay.

Round requer Familiaridade própria, somente primeira vitória de Hunt Manual Ruínas; lotes ×5/×10/×20, snapshot, Consumíveis e settlement existentes. Custódio do Poente interrompe antes do combate automático e preserva encounter_id no reconnect. P4/Explore/rota/Travessia não liberam Familiaridade.

## 30.7 Braseiro e recovery

Recovery para Hunt, Explore combat, Round e encontro P4 escolhe sem RNG, último Brazier ou escolha manual: (1) tdo.brazier.poente → Braseiro do Poente/Ruínas; (2) senão tdo.brazier.galhos_mortos → Braseiro dos Galhos Mortos/Bosque; (3) senão tdo.brazier.vento_morto → Braseiro do Vento Morto/Charneca; (4) senão Braseiro do Refúgio/Refúgio. HP100%, estados comuns removidos, Vigor e Consumíveis usados preservados, activity encerrada, sem reward, reroll ou auto-retry; rewards anteriores legítimos permanecem.

## 30.8 Fronteiras

Não implementa S4/S5, P5/P6, Câmara do Poente, Vigia Partido, dungeon framework ou gameplay das Galerias. Fonte Mestra v1.4.8, ruleset histórico, economia global e Vales permanecem inalterados. Nenhuma migration.

---

# 31. Fechamento v1.0.14 — Guardião do Último Rastro

Esta seção prevalece sobre qualquer formulação anterior que use **Custódio Sem Rosto** como encontro fixo da Etapa 4 de S6.

## 31.1 Substituição restrita

A alteração é exclusivamente:

`S6 Etapa 4: Custódio Sem Rosto → Guardião do Último Rastro`

O **Custódio Sem Rosto** continua integralmente válido como criatura Incomum das Ruínas do Vigia e em todos os demais usos já fechados, incluindo pools normais, S5 quando elegível e conteúdo das Galerias.

## 31.2 Mecânica fechada do Chefe

- Nv.10;
- Solo ou Grupo · 1–4;
- Golpe da Última Trilha `100% ATQ`;
- Marca do Rastro `90% ATQ` + `AGI −10% ·2T`, CD3;
- Queda da Travessia Preparada `165% ATQ`, CD4;
- sem Cura;
- sem Barreira;
- sem invocações;
- sem adds;
- sem Variante.

Nenhum outro número, recompensa, economia ou regra global é reaberto por esta revisão.

## 31.3 Lore fechada

O Guardião bloqueia a passagem que leva ao último registro legível da rota. **Motivo, identidade anterior e natureza real permanecem desconhecidos.**

Sua imagem e seus textos não podem confirmar relação de identidade com O Sem-Nome nem provar que seja um Peregrino desaparecido. A conexão temática com passagem, rastro e desgaste é deliberada; conexão ontológica é proibida sem futura Fonte explícita.

## 31.4 Direção visual

A direção detalhada está consolidada em `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md`.

---

# 32. Sincronização cooperativa v1.0.15

Esta seção aplica a regra global de Campanha cooperativa da Fonte Mestra v1.7.1 sem substituir o conteúdo regional detalhado. P1 é cooperativa depois do Prólogo Solo: os dois sinais, o encontro roteirizado do Cão Cinéreo, a chegada válida ao Refúgio e a descoberta do Braseiro podem registrar progresso próprio para participantes elegíveis e presentes. Diálogo, respostas e flags pessoais continuam individuais. O encontro do Cão mantém exatamente sua identidade, template, kit, Vigor e ausência de recompensa econômica própria; por não ser um Chefe de Campanha, não recebe automaticamente o novo multiplicador reservado a esses Chefes.

S6 — Onde os Nomes Terminaram aceita Solo ou Grupo de 1–4. O Guardião do Último Rastro conserva a ficha Solo, Artes, ausência de Variante, Cura, Barreira e adds, Lore, gates e recompensa de S6. Em Grupo aplica-se somente o scaling global de Chefe de Campanha do GDD v1.5.0, congelado na criação; não existe scaling adicional de fases/Artes nem alteração de conteúdo regional.

As demais Principais e Secundárias de Terras do Ocaso seguem a regra global por referência. Progresso e settlement permanecem individuais; ajudantes não regridem e não repetem recompensas one-time.

---

# 33. Fechamento v1.0.18 — Mapa único, descoberta por Explorar, nível do Local (revisto na v1.0.19)

> **Revisão v1.0.19 (2026-11-26, decisão do autor):** Explorar é substituído por Desbravar e todos os Locais nascem descobertos. Mudam as seções 33.1 (ações), 33.2, 33.3 (sorteio e texto de descoberta), 33.10, 33.12, 33.14 (itens 2 e 5), 33.15 e 33.16 (itens 1, 2, 4, 18 e 19). O texto da v1.0.18 dessas partes fica preservado no arquivo `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_FINAL.md`, sem validade.

**Data:** 2026-11-14. **Aprovado pelo autor em 2026-11-14.** Esta seção **prevalece sobre qualquer trecho das seções 1 a 32** que a contrarie. Origem: proposta v1.0.18 (revisão 6), auditoria `docs/specs/AUDITORIA_FARM_XP_TDO_v1.0.18_2026-11-14.md` e decisões do autor de 2026-11-14 (pendência 17 e decisões 8, 9 e 11). A seção 33.14 lista os pontos em que a v1.0.18 contraria a Fonte Mestra; eles dependem de **registro do autor** no índice. Nenhum valor numérico novo foi inventado: 2,5% é o percentual já usado nas Descobertas Menores; as referências 4, 6, 9 e 10 foram confirmadas pelo autor; `XP(n)` vem do GDD §49.7; 3 s e 1 tentativa em resolução vêm da decisão P1 do autor; `max_enemy_level` vem de §10.2 a §10.5.

## 33.1 Refúgio do Ocaso como hub [DECIDIDO 2026-11-14]

- Modelo hub-and-spoke. O Refúgio liga a **todos os Locais descobertos**; **todos os Locais voltam ao Refúgio**. Não existe ligação direta Local–Local.
- Toda ida a um Local **parte do Refúgio**.
- Ida e volta custam 0 Vigor, 0 Coroas, 0 XP; sem encontro; só de local seguro / fora de combate.
- Antes de P1 concluir a Etapa 4, o personagem ainda está na Estrada e o hub não existe (Refúgio ainda não descoberto). Depois, a Estrada é um destino como os outros.
- A Câmara do Poente também volta ao Refúgio.
- **Rotas antigas** Refúgio↔Charneca, Charneca↔Bosque e Bosque↔Ruínas deixam de ser caminhos de jogo. A Charneca deixa de ser passagem para o Bosque, e o Bosque para as Ruínas. Valem: custo zero, 0 XP, sem encontro, sem nome próprio nem lore para a ligação.
- **Estado ao abrir o jogo:** o personagem aparece onde estava; não há teletransporte ao Refúgio.

### Ações na tela do Refúgio e do Local

| Ação | Onde | Como funciona |
|---|---|---|
| **Desbravar (menu)** | Menu Principal, Refúgio ou qualquer Local | Abre o menu com Masmorras, Refúgio do Ocaso e os cinco Locais (33.2). Abrir o menu não move o personagem. |
| **Toque num Local do menu Desbravar** | Menu Desbravar | Leva o personagem ao Local pelo hub (de outro Local, primeiro ao Refúgio; custo 0) e gera o evento do Local pelo Desbravar canônico (33.7). Câmara do Poente: só abre a entrada (33.3). |
| **Caçar** | Refúgio | Abre a escolha de Local descoberto com Caçada (Estrada, Charneca, Bosque, Ruínas). A Câmara não aparece. Depois de escolher, o personagem **passa a estar nesse Local**. |
| **Desbravar** | Dentro do Local | Age no Local atual (sem exploração remota). O evento gerado pelo toque no menu também acontece no Local atual, depois da chegada pelo hub. |
| **Ronda** | Dentro do Local | Ação do Local atual; regra da primeira vitória manual válida no Local. Em Grupo, a vitória manual libera a Ronda para **todos os membros que participaram da vitória** [DECIDIDO 2026-11-14]. |
| **Voltar ao Refúgio** | Dentro do Local | Sempre disponível fora de combate. |
| **Missões**, **Personagem**, **Masmorra (Covil)** | Refúgio | Masmorra lista só as descobertas. |

## 33.2 Descoberta de Locais e menu Desbravar [REVISTO 2026-11-26]

1. **Todos os Locais nascem descobertos:** Estrada das Cinzas, Charneca da Fuligem, Bosque Calcinado, Ruínas do Vigia e Câmara do Poente. A descoberta (`LocationDiscovery`) de Charneca, Bosque, Ruínas e Câmara é gravada **no fim do Prólogo**, junto com a entrada de Códice `codex.location.camara_do_poente`, **sem XP**. Personagens que já passaram do Prólogo recebem o mesmo pela migration 0062, sem XP. A gravação é idempotente. O Refúgio continua descoberto na Etapa 4 de P1.
2. **A ação Explorar deixa de existir.** Não há sorteio de Local, nem clique de revelação, nem texto "Não há mais o que explorar por aqui."
3. **Não existe mais XP de descoberta de Local.** A regra `FixedPercentXP(min(nível de referência do Local, nível do personagem), 2,5%)` da v1.0.18 fica sem efeito. Impacto na meta de Exploração: seção 33.10.
4. **Menu Desbravar:** abre Masmorras (só as descobertas), Refúgio do Ocaso e os cinco Locais. Tocar num Local leva o personagem até ele pelo hub (33.1; ida e volta custam 0 Vigor, 0 Coroas, 0 XP) e, depois da chegada, gera **um** evento do Local pelo **Desbravar canônico** (33.7), com as mesmas regras de Vigor, pool-base e anti-repetição. O anti-spam técnico de 3 s e 1 tentativa em resolução continua valendo para o Desbravar.
5. **Nenhum Local é liberado por Missão.** Missão pode exigir o Local descoberto (P2, P3, P4, P6 e S3); como todos nascem descobertos, a etapa de chegada nunca fica aguardando descoberta. Missão não grava `LocationDiscovery` e não paga XP de descoberta.
6. "Local novo" **não é** resultado de Desbravar. Identificadores `explore.tdo.local.*` não existem no pool.

## 33.3 Câmara do Poente [DECIDIDO 2026-11-14, pendência 17]

- **Descoberta [REVISTO 2026-11-26]:** a Câmara nasce descoberta, como os outros Locais (33.2). Não há sorteio. No menu Desbravar ela é clicável: o toque leva o personagem até ela pelo hub e abre a tela de entrada, **sem evento**. A Câmara ainda não tem evento próprio; criar um exige decisão do autor (33.15, L16).
- **P6 não descobre a Câmara.** O efeito "descobre Câmara do Poente" foi **removido** de §5.13. A Etapa 2 de P6 **exige a Câmara já descoberta**.
- **Sem Caçada, Desbravar, Ronda, pool próprio nem Braseiro.** Recovery = Refúgio do Ocaso. Volta ao Refúgio como todo Local. O Chefe Vigia Partido continua acessível só pela Missão P6.
- **Textos de entrada em dois estados.** A Missão **só muda o texto exibido**: a UI lê se o personagem concluiu P6; **não libera o Local**.
  - **Antes da P6 concluída:** recinto fechado e neutro, **sem a palavra "Âncora"** e **sem descrever a estrutura central**. `[[TEXTO_CAMARA_PRE_P6]]`
  - **Depois da P6 concluída:** texto que usa o nome **Âncora do Poente**. `[[TEXTO_CAMARA_POS_P6]]`
  - O texto de descoberta por Explorar (`[[TEXTO_CAMARA_DESCOBERTA]]`, neutro) deixa de ser exibido, porque Explorar não existe mais. Fica em §3.6 só como registro.
- Os três textos estão escritos em §3.6 (narrative-designer, 2026-11-14).

## 33.4 Travessia, Braseiros e recovery [DECIDIDO 2026-11-14]

- **Travessia dos Braseiros** (sistema global): **oculta nas Terras do Ocaso**; regra global intacta para outras regiões; não é removida do GDD.
- **Braseiros** continuam como checkpoint e recovery e como conteúdo de Desbravar (Braseiro, Masmorra). Perdem apenas o papel de rede de deslocamento. Não há viagem rápida entre Braseiros (sugestão P6 da revisão 2 **descartada**).
- **Recovery** volta ao Braseiro **do próprio Local**, pela prioridade de §11.9 (tabela): Estrada → Braseiro da Estrada; Charneca → Vento Morto, senão Refúgio; Bosque → Galhos Mortos, senão Vento Morto, senão Refúgio; Ruínas → Poente, senão Galhos Mortos, senão Vento Morto, senão Refúgio; **Câmara do Poente → Refúgio do Ocaso**. Nunca usa `LocationDiscovery`.

## 33.5 Nível do inimigo, `unlock_level` e Grupo [DECIDIDO 2026-11-14]

- **Nível do inimigo = nível do Local** (`max_enemy_level` de cada criatura): Estrada 3–5, Charneca 3–7, Bosque 6–9, Ruínas 8–10. Em **Solo e em Grupo**. Sem escala para o jogador (estilo soulslike). §10.1 reescrito.
- **`unlock_level`:** não se aplica em **Solo** (pool completo do Local desde o primeiro acesso). Em **Grupo** é requisito **individual de cada membro**: a criatura só é elegível se todos o cumprem.
- **Decisão 11 [DECIDIDO 2026-11-14]:** em Grupo, se **nenhuma** criatura do Local for elegível para todos os membros, a **Caçada não abre** e a interface diz **qual membro não cumpre o `unlock_level`**. O texto "nada para caçar aqui ainda" fica para **outros** casos de pool vazio (por exemplo, pool vazio por outro motivo que não `unlock_level`).
- **Decisão 8 [DECIDIDO 2026-11-14]:** nas Missões **S4** e **S5**, em Solo **e em Grupo**, qualquer **Vigia Rachado** (S4), **Mariposa de Brasa** ou **Custódio Sem Rosto** (S5) derrotado conta, **sem checar o `unlock_level`** de cada membro. Não há fallback de elegibilidade.
- **Coop de Chefe (P5, P6, S6):** o PowerlevelFactor se aplica à XP fixa de Missão (GDD linha 3795: `100/70/45/20/5%` para diferença `0-10 / 11-15 / 16-20 / 21-30 / 31+`).

## 33.6 Remoção de travas de nível [DECIDIDO 2026-11-14]

- Missões (P1 a P6, S1 a S6) sem nível mínimo; dependem só de encadeamento: `Prólogo → P1 → P2 → P3 → P4 → P5 → P6`; S1←P1; S2←P2; S3←Bosque descoberto + P3 ativa ou concluída; S4←P4; S5←P4; S6←S2 + P5.
- Removidos: Bosque Nv.6+, Braseiro do Vento Morto Nv.4+, Entrada da Cripta Nv.4+, Entrada das Galerias Nv.8+, Grandes Descobertas do Bosque Nv.6+, P5 Nv.9, rota Bosque→Ruínas Nv.8+, P6 Nv.10 (início automático após P5).
- Encontros roteirizados **fixos** (não escalam): Aranha de Cinza Nv.3 (P2), Peregrino Calcinado Nv.4 (S2), Cervo Escoriado Nv.5 (P3, S3), Vigia Rachado Nv.7 (P4), Custódio do Poente Nv.9 Elite (P5), Guardião do Último Rastro Nv.10 (S6), Vigia Partido (P6, Chefe).
- **Equipar exige nível do personagem ≥ `item_level` (regra global).** O Raro Nv.5 de P3 e o Épico Nv.10 de P6 podem ser recebidos antes do nível e ficam vinculados e inutilizáveis até lá.
- O gate de nível da **saída da região** (§25) é estrutural global e **não** é alterado.
- Faixas de nível dos Locais viram "faixa recomendada" (apresentação).

## 33.7 Desbravar [DECIDIDO 2026-11-14]

Sem recarga de 5 min e sem limite de 6 tentativas por Local por 60 min. Anti-spam técnico de 3 s e 1 em resolução. Vigor (4) só quando o resultado repetível paga economia; com `Vigor < 4` a tentativa ocorre sem Coroas/Materiais repetíveis e o XP repetível aplica o fator global de `25%`. Sem freio de jogo além do Vigor para tentativas sem pagamento (aceito pelo autor). Pool-base `8/22/15/25/10/20` e anti-repetição (§11.7) mantidos. Subpesos da Grande Descoberta como na v1.0.17 (Estrada: Marco 100; Charneca, Bosque e Ruínas: 50/50). Chance de Variante: 8% Estrada, 10% Charneca, 12% Bosque, 15% Ruínas.

## 33.8 Masmorras [DECIDIDO 2026-11-14, decisão 6]

Nível mínimo individual de entrada: **Cripta do Ocaso Nv.4; Galerias do Vigia Nv.8** (início da Faixa), em Solo e em Grupo. A Masmorra só aparece no menu depois de descoberta. `Reference level` (6 e 9), Ruptura, encontros, Braseiros de Masmorra, recompensas e Códices permanecem. O mínimo impede carona de XP alto no Nv.1 e é compatível com a elegibilidade global (GDD linha 1341).

## 33.9 Bestiário: BKP de investigação Desbravar e de Habitat [DECIDIDO 2026-11-14, decisão 9]

- O BKP de **investigação Desbravar** e o BKP de **Habitat** valem **uma única vez** (marco único) **por criatura e por Local**.
- **Checagem contra a Fonte Mestra vigente (v1.7.1, conforme `SOURCE_AUTHORITY.md`):** a Fonte Mestra define os valores-base (GDD §49.17, linha 4241: "Habitat 3; investigação Desbravar 8") e **não diz que sejam repetíveis**. Ela prevê "marcos únicos" como ferramenta anti-farming (linha 2629: "O sistema pode utilizar ganho reduzido por repetição, limite por fonte, marcos únicos…"), exige que o mesmo `encounter_id` não registre "marcos únicos de conhecimento" de novo (linha 911) e que o Bestiário use "marcos/IDs estáveis e idempotentes" (linha 3420). Para Habitat, "Novos habitats podem ampliar a entrada" (linha 2593). Conclusão: **sem conflito**; a decisão é configuração regional compatível, não override. Nenhum valor de BKP, threshold ou categoria muda.
- **Limite da checagem:** a Fonte Mestra não enuncia expressamente "por criatura e por Local" para esses dois BKP; a granularidade é a escolha do autor registrada aqui. Se a implementação divergir (por exemplo, Habitat contado por Região), o `programmer` deve parar e perguntar.

## 33.10 XP de exploração [DECIDIDO 2026-11-26]

**v1.0.18 (sem validade a partir da v1.0.19):** Grandes `5.560` (7 Grandes), Menores `1.489` (6 Menores), Locais `1.193`: total `8.242 XP` = `8,43%` do requisito Nv.1→11 (`97.800 XP`), no teto. Piso (quatro Locais descobertos no Nv.1): `480 + 5.560 + 1.489 = 7.529 XP` = `7,70%`. Meta de 7–9% = `6.846` a `8.802 XP`.

**Impacto do fim do XP de descoberta (só aritmética com os números acima; nenhum valor novo):**

| | v1.0.18 teto | v1.0.18 piso | Sem XP de descoberta |
|---|---|---|---|
| Grandes | 5.560 | 5.560 | 5.560 |
| Menores | 1.489 | 1.489 | 1.489 |
| Locais | 1.193 | 480 | 0 |
| **Total** | **8.242** | **7.529** | **7.049** |
| % de 97.800 | 8,43% | 7,70% | **7,21%** |
| Sai da meta | — | — | 1.193 XP (−1,22 p.p.) no teto; 480 XP (−0,49 p.p.) no piso |

- `7.049 / 97.800 = 7,21%`. O total fica **dentro** da meta de 7–9% (`6.846` a `8.802 XP`), `203 XP` acima do piso da meta (`7.049 − 6.846`).
- Piso e teto deixam de ser diferentes: sem a parcela que dependia do nível na descoberta, a Exploração única passa a ter um valor só.
- **Decisão do autor (2026-11-26):** a nova meta de Exploração única nas Terras do Ocaso é `7.049 XP` = `7,21%` do requisito Nv.1→11, sem compensação. Fica dentro da meta global de 7–9%. Item 5 de 33.14.
- Personagens que já receberam XP de descoberta por Explorar antes da v1.0.19 mantêm esse XP (a migration 0062 não retira nem paga XP).

## 33.11 Reescritas de consolidação aplicadas

- **§10.1:** nível do inimigo e `unlock_level` (33.5).
- **§11.9:** tabela de recovery por Local (33.4); texto "requer P2 concluída" substituído por "liberado na descoberta do Local, por qualquer via".
- **§5.5 (P2):** Etapa 1 exige a Charneca descoberta; texto de "Conteúdo normal da Charneca depois de P2" reescrito; "Nv.3 ou superior" removido.
- **§5.13 (P6):** efeito "descobre Câmara do Poente" removido.
- **Varredura:** a v1.0.17 foi varrida por "requer P2 concluída", "após P2", "P3/P4 concluída libera", "Nv.N+" de acesso, `min(player_level, …)`, "cooldown 5 min / 6 por 60 min" e "descobre". Ocorrências remanescentes de seções históricas (§3.7, §5.3.24, §29, §30) estão marcadas como superadas.

## 33.12 Decisões do autor, com data

| Decisão | Resultado | Data |
|---|---|---|
| Todo Local por Explorar, Câmara incluída; nenhum Local por Missão | DECIDIDA | 2026-11-14 |
| Refúgio é hub; toda ida parte do Refúgio | DECIDIDA | 2026-11-14 |
| Anti-spam 3 s e 1 em resolução (Explorar e Desbravar) | DECIDIDA | 2026-11-14 |
| Sorteio uniforme; Estrada e Refúgio fora do sorteio | DECIDIDA | 2026-11-14 |
| XP de Local 2,5% com `min()` | DECIDIDA | 2026-11-14 |
| Nível do inimigo = nível do Local (Solo e Grupo) | DECIDIDA | 2026-11-14 |
| `unlock_level` só individual em Grupo | DECIDIDA | 2026-11-14 |
| Mínimo de Masmorra: Cripta 4, Galerias 8 | DECIDIDA | 2026-11-14 |
| PowerlevelFactor em Coop de Chefe | DECIDIDA | 2026-11-14 |
| Ronda em Grupo para quem participou da vitória | DECIDIDA | 2026-11-14 |
| Abrir o jogo onde estava | DECIDIDA | 2026-11-14 |
| Rotas antigas substituídas; Travessia oculta; Braseiros checkpoint/recovery | DECIDIDA | 2026-11-14 |
| Recovery da Câmara = Refúgio; Desbravar e Ronda no Local atual | DECIDIDA | 2026-11-14 |
| **Pendência 17:** Câmara no sorteio com mesma chance; dois textos de entrada; Missão só muda o texto | **DECIDIDA** | 2026-11-14 |
| **Decisão 8:** S4/S5 em Grupo, qualquer criatura do tipo conta | **DECIDIDA** | 2026-11-14 |
| **Decisão 9:** BKP Desbravar e Habitat, marco único por criatura e Local | **DECIDIDA** (sem conflito com a Fonte Mestra, 33.9) | 2026-11-14 |
| **Decisão 11:** Grupo sem criatura elegível, Caçada não abre e mostra o membro | **DECIDIDA** | 2026-11-14 |
| Explorar substituído pelo menu Desbravar | **DECIDIDA** | 2026-11-26 |
| Todos os Locais nascem descobertos (fim do Prólogo; existentes pela migration 0062), sem XP | **DECIDIDA** | 2026-11-26 |
| Toque num Local do Desbravar: viagem pelo hub e evento do Desbravar canônico; Câmara sem evento | **DECIDIDA** | 2026-11-26 |
| Fim do XP de descoberta de Local | **DECIDIDA** | 2026-11-26 |
| Meta de Exploração sem o XP de descoberta: `7.049 XP` = `7,21%`, sem compensação (item 5 de 33.14) | **DECIDIDA** | 2026-11-26 |
| Prólogo: Vitória com 3 Coroas; bolsa dos destroços com 18 Coroas e 1 Resíduo do Ocaso (§1.1) | **DECIDIDA** | 2026-11-26 |

## 33.13 Fronteiras

Esta seção não altera recompensas de Missão, kits de criaturas, Chefe, Provações de Classe, Ofícios, Feitos nem Códice. Não altera o gate de nível da saída da região. Não altera `src/`, `alembic/`, `SOURCE_AUTHORITY.md` nem a Fonte Visual/UI. Nada nesta Fonte trata de conteúdo em fase candidata.

## 33.14 Override da Fonte Mestra (depende de registro do autor)

Texto completo e rascunho em `docs/specs/RASCUNHO_OVERRIDE_FONTE_MESTRA_TDO_v1.0.18.md`. Pontos em que a v1.0.18 contraria a Fonte Mestra v1.7.1, só para a Região 1:

1. Desbravar sem recarga de 5 min e sem limite de 6 por Local por 60 min (GDD §18.3 e §49.15, linha 4208); fica o anti-spam técnico.
2. **[Revisto 2026-11-26]** Todos os Locais nascem descobertos, sem exigir conexão nem verificar nível; Explorar não existe mais; o toque num Local do menu Desbravar leva ao Local pelo hub e gera o evento do Desbravar canônico; "Local conectado", "não ignora gates", "não teleporta" (linha 1123). Nenhum Local por Missão.
3. Hub do Refúgio e "sem exploração remota" (linha 1049); ida e volta de graça; Travessia oculta na região.
4. Faixas de Masmorra como recomendação (linha 4182), mantido o mínimo individual (linha 1341): Cripta 4, Galerias 8.
5. **[Revisto 2026-11-26]** Meta de Exploração e "descoberta 100%" (§49.7). Não existe XP de descoberta de Local: a descoberta não paga XP (substitui, para descoberta de Local, a regra de 100% sem fator por nível). A Exploração única nas Terras do Ocaso é `7.049 XP` = `7,21%` do requisito Nv.1→11 (`97.800 XP`), dentro da meta de 7–9% (33.10).
6. Missões Principais e Secundárias sem requisito de nível (linha 849); saída da região (§25) intacta.
7. Nível do inimigo em Solo e em **Grupo** = `max_enemy_level` do Local; contraria a linha 899 (Grupo: maior nível do grupo). `unlock_level` individual em Grupo **não** conflita.
8. PowerlevelFactor em Coop de Chefe: vale também para a XP fixa de Missão em Coop de Chefe (P5, P6, S6). O GDD aplica o fator só à XP de inimigo (linha 3822) e não o define para XP fixa de Missão (linhas 3840-3842); esta Fonte Regional o define para P5, P6 e S6 (conferido em 2026-11-14, decisão do autor: manter como override).
9. Ronda em Grupo liberada para quem participou da vitória.

**Os itens 1 a 9 só valem depois que o autor registrar o override no `SOURCE_AUTHORITY.md`.** Até lá, a v1.0.18 não vai para código.

## 33.15 Lacunas para o autor

**Pendências da proposta: nenhuma continua aberta como decisão de regra.** Todas as marcas PENDENTE da proposta foram tratadas (ver 33.12), exceto os itens abaixo, que são lacunas de conteúdo ou de registro, não decisões de regra.

| Item | O que falta | Quem |
|---|---|---|
| L1 | **Resolvida em 2026-11-14:** textos pré-P6, pós-P6 e de descoberta escritos em §3.6. | narrative-designer |
| L2 | Registrar o override da Fonte Mestra (33.14) no `SOURCE_AUTHORITY.md` e, depois, na próxima revisão do GDD. Atualizar o índice para apontar a v1.0.18 como vigente. | autor |
| L3 | **Decidida pelo autor em 2026-11-14:** durante P1 em andamento, Caçada e Desbravar da Estrada ficam **escondidos**; liberam ao concluir P1 (fluxo do tutorial de §5.3.24 e §24.6). | autor |
| L4 | **Decidida pelo autor em 2026-11-14:** na decisão 11, se mais de um membro não cumpre o `unlock_level`, a mensagem cita **todos** eles. | autor |
| L5 | **Decidida pelo autor em 2026-11-14:** o texto pré/pós P6 da Câmara segue a P6 **de quem vê** (progresso individual, por personagem). | autor |
| L6 | Taxa de vitória real de Nv.1 na Estrada logo após P1 (indicativo `r` 0,74–0,86, pode estar dura) e de Nv.1 solo em Locais Nv.9–10 (indicativo `r` 0,52–0,56). Exige simulação; sem limiar de aprovação definido. Registrada como pendência de QA em docs/qa/PENDENCIAS_QA.md. | QA |
| L7 | Nome técnico da ação Explorar e identificadores novos. | programmer |
| L8 | Sincronizar a Fonte Visual/UI (rascunho do delta pronto). | autor |
| L9 | **Resolvida em 2026-11-14:** entrada de Códice "Câmara do Poente" escrita em §16 (Regiões e Locais), com gatilho na descoberta por Explorar e dois textos (pré e pós P6 de quem vê). Gatilho proposto pelo narrative-designer e confirmado pelo autor em 2026-11-14. | narrative-designer + autor |
| L10 | **Resolvida em 2026-11-14 (autor):** personagens existentes mantêm os Locais já descobertos pelo fluxo antigo (Missão ou rota), sem XP de Explorar; Explorar sorteia só os que faltam. | autor |
| L11 | **Resolvida em 2026-11-14 (autor):** personagem que está num Local não descoberto pelo novo fluxo fica onde está, e esse Local conta como descoberto (sem XP de Explorar). | autor |
| L12 | **Resolvida em 2026-11-14 (autor):** Explorar é individual também em Grupo; cada personagem tem as próprias descobertas. | autor |
| L13 | **Resolvida em 2026-11-14 (autor):** o horário do último clique do anti-spam de 3 s (Explorar e Desbravar) é persistido no banco, por personagem. | autor + programmer |
| L15 | **Resolvida em 2026-11-26 (autor):** nova meta de Exploração `7.049 XP` = `7,21%`, sem compensação (33.10). | autor |
| L16 | Evento próprio da Câmara do Poente no menu Desbravar (hoje só abre a entrada). | autor |
| L14 | **Resolvida em 2026-11-14 (autor):** na reconciliação da L11, se o Local reconciliado for a Câmara do Poente, cria-se também a entrada de Códice `codex.location.camara_do_poente` (idempotente), sem XP. | autor |

## 33.16 Critérios de aceite (usados pelo QA)

Itens que dependem do override (L2) ou da Visual/UI (L8) só são testáveis depois deles.

1. **[v1.0.19]** Ao fim do Prólogo, Estrada, Charneca, Bosque, Ruínas e Câmara do Poente estão descobertos, sem XP; personagens existentes recebem o mesmo pela migration 0062, sem XP.
2. **[v1.0.19]** Não existe ação Explorar. O menu Desbravar mostra Masmorras, Refúgio do Ocaso e os cinco Locais; tocar num Local leva o personagem até ele pelo hub (0 Vigor, 0 Coroas, 0 XP; de outro Local, antes pelo Refúgio) e gera um evento do Desbravar canônico; tocar na Câmara abre a entrada sem evento. Intervalo mínimo de 3 s e 1 em resolução. Desbravar não tem resultado "Local novo".
3. Subpesos da Grande Descoberta de Desbravar iguais aos da v1.0.17; não existe proteção de 3 tentativas para revelar Local.
4. **[v1.0.19]** Não existe XP de descoberta de Local; nenhuma descoberta paga XP.
5. Local descoberto tem Caçada e Desbravar sem Missão; Ronda só após a primeira vitória manual válida naquele Local; Câmara não tem Caçada, Desbravar, Ronda nem Braseiro.
6. Sem recarga de 5 min nem limite de 6 por Local por 60 min em Desbravar; existe intervalo mínimo de 3 s e 1 em resolução, sem efeito sobre recompensa.
7. Vigor: 4 Vigor só quando o resultado paga economia; com `Vigor < 4` a tentativa ocorre sem economia repetível. Com 1.000 tentativas seguidas, Coroas e Materiais totais não passam de 25 pagamentos com Vigor 100; XP repetível usa fator 0,25.
8. Nenhuma Missão tem nível mínimo; encadeamento mantido. Missão nunca grava `LocationDiscovery`: P2, P3, P4 e P6 com o Local não descoberto ficam aguardando, sem erro; com o Local descoberto, a etapa conclui na chegada válida, sem descoberta duplicada.
9. Cripta e Galerias aparecem no menu Masmorra só depois de descobertas; Cripta entra com Nv.4 e recusa Nv.3; Galerias entra com Nv.8 e recusa Nv.7, em Solo e em Grupo.
10. Recompensas de Missão, kits, Chefe, Masmorras e Provações permanecem idênticos à v1.0.17.
11. Hub: de qualquer Local descoberto (inclusive a Câmara) o jogador volta ao Refúgio; do Refúgio chega a qualquer Local descoberto; nunca há ida direta Local–Local; ida e volta custam 0 Vigor, 0 Coroas, 0 XP e não ocorrem em combate. Travessia dos Braseiros não aparece nas Terras do Ocaso. Condicional à Visual/UI.
12. Caçar no Refúgio lista só Locais descobertos com Caçada (Estrada, Charneca, Bosque, Ruínas); a Câmara não aparece; Local não descoberto nunca aparece. Depois de escolher, o personagem está no Local, com Caçar, Desbravar, Ronda (se liberada) e Voltar ao Refúgio.
13. Recovery pelo Braseiro do próprio Local (33.4); Câmara → Refúgio; nunca usa `LocationDiscovery`.
14. Inimigo de Caçada e de Combate de Desbravar tem o nível do Local (`max_enemy_level` da criatura), em Solo e em Grupo; Nv.1 pode entrar nas Ruínas e enfrenta o nível das Ruínas. Não existe `min(player_level, max_enemy_level)`. Em Solo nenhuma criatura é excluída por `unlock_level`.
15. **Grupo e `unlock_level`:** a criatura só é elegível se todos os membros cumprem o seu `unlock_level`. **Decisão 11:** se nenhuma criatura do Local é elegível para todos, a Caçada **não abre** e a UI informa qual membro não cumpre o `unlock_level`; o texto "nada para caçar aqui ainda" aparece só em outros casos de pool vazio.
16. **Decisão 8:** em S4 e S5, em Solo e em Grupo, qualquer Vigia Rachado (S4) ou Mariposa de Brasa / Custódio Sem Rosto (S5) derrotado conta; o `unlock_level` de cada membro não é checado.
17. **Decisão 9:** o BKP de investigação Desbravar e o de Habitat são concedidos uma única vez por criatura e por Local; repetir não concede de novo; nenhum valor de BKP muda.
18. **Câmara:** **[v1.0.19]** nasce descoberta e é clicável no menu Desbravar, sem evento; antes de P6 concluída a tela de entrada usa `[[TEXTO_CAMARA_PRE_P6]]` (sem a palavra "Âncora" e sem descrever a estrutura central); depois de P6 concluída usa `[[TEXTO_CAMARA_POS_P6]]` (usa "Âncora do Poente"); a conclusão de P6 não libera nem revela o Local; P6 Etapa 2 com a Câmara não descoberta fica aguardando.
19. **[v1.0.19]** Soma de exploração sem XP de descoberta: Grandes 5.560 + Menores 1.489 = 7.049 XP = 7,21% (meta aceita pelo autor em 2026-11-26). Nenhum texto ou teste usa 10.865 / 11,11% / 8.585 / 8,78% / 8% de Local, nem 8.242 / 8,43% / 7.529 / 7,70%, como regra.
20. Equipar exige nível ≥ `item_level`: Raro Nv.5 de P3 e Épico Nv.10 de P6 recebidos antes do nível ficam vinculados e não equipáveis. Chance de Variante: 8% Estrada, 10% Charneca, 12% Bosque, 15% Ruínas. Ao abrir o jogo, o personagem aparece onde estava.
21. Ronda em Grupo: a vitória manual libera a Ronda para todos os membros que participaram da vitória, e só para eles. PowerlevelFactor se aplica à XP fixa de Missão em Coop de Chefe (P5, P6, S6).
22. Esta consolidação não altera `src/`, `alembic/`, `SOURCE_AUTHORITY.md` nem a Fonte Visual/UI.

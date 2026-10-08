# ASTERION — GDD ESTRUTURAL v1.5.0

**Fonte Mestra Consolidada do Projeto**  
**Status:** Estruturalmente fechado para implementação e testes — Baseline Numérica v1.0 autoritativa e sem reaberturas numéricas vigentes  
**Escopo:** regras oficiais consolidadas, substituindo versões anteriores quando houver conflito  
**Uso recomendado:** fonte de referência para os chats de Visual & UI, Desenvolvimento, Conteúdo, Balanceamento e Testes

> Este documento consolida as decisões aprovadas do projeto ASTERION. Ele não registra a ordem histórica das discussões; registra apenas o estado oficial atual. **Esta versão v1.5.0 substitui integralmente a Fonte Mestra v1.4.9 e todas as versões anteriores.** A Baseline Numérica v1.0 está consolidada na seção 49. A v1.5.0 formaliza Grupo persistente, Campanha cooperativa, escala de Chefes de Campanha, sequência PvPvE e suas salvaguardas econômicas, sem alterar os valores Solo existentes ou os demais sistemas numéricos.

## 1. Governança do GDD e estado do projeto

- O GDD estrutural v1.5.0 está consolidado como Fonte Mestra vigente. Novos achados gerais devem, por padrão, ser classificados em **Implementação**, **Balanceamento** ou **Beta/Telemetria**, salvo quando surgir uma contradição real de design.
- Asterion será lançado inicialmente como **Bot do Telegram**, sem Mini App.
- O lançamento público pretende oferecer o mundo persistente completo do Nv.1 ao Nv.60. Alpha e Beta internas podem usar wipes quando necessário.
- O desenvolvimento deve começar por uma **vertical slice** das Terras do Ocaso e dos sistemas centrais antes de produzir todo o conteúdo do lançamento.
- `SIMULAR` permanece disponível como status de governança para mecânicas futuras ou explicitamente reabertas. A Baseline Numérica v1.0 não possui reabertura numérica vigente nesta versão. Ajustes posteriores decorrentes de Alpha/Beta são Balanceamento/Telemetria versionados, não valores implicitamente abertos.
- As principais áreas futuras de trabalho são: **Visual & UI**, **Desenvolvimento**, **Conteúdo**, **Balanceamento** e **Testes & Bugs**.

## 2. Identidade, proposta e limites de lançamento

- Nome oficial: **ASTERION**.
- Gênero e tom: RPG/MMORPG dark fantasy medieval, decadente, melancólico e misterioso.
- Referência de sensibilidade: profundidade e sensação de descoberta de dark fantasy moderno, sem copiar propriedades intelectuais específicas.
- O nível máximo permanente é **Nv.60**. Não haverá aumento infinito de level cap.
- Não há Mana como recurso universal.
- Todo personagem possui **Ataque Básico** e **Defender**.
- São 6 Classes principais e 12 **Caminhos**.
- Não haverá pets tradicionais no lançamento.
- Não haverá durabilidade de equipamento.
- Não haverá Aparências cosméticas de armas ou equipamentos no lançamento.
- Não existe transferência de personagem entre servidores no lançamento.


### 2.1 Nomenclatura oficial de interface

Asterion diferencia **nome de interface (UI)** de **nome técnico/interno**. A documentação de backend pode manter termos técnicos estáveis; quando houver um nome de UI definido abaixo, é ele que deve ser priorizado nas telas, mensagens e materiais voltados ao jogador.

O nome oficial da obra/projeto permanece **ASTERION**. Em títulos e textos normais da interface player-facing, o nome é apresentado como **Asterion**. A forma **ASTERION** pode permanecer em usos de marca, documentação, identificadores ou contextos que adotem explicitamente caixa alta. O cabeçalho player-facing do Menu Principal utiliza **Asterion**. Esta convenção é apenas de apresentação e não altera lore, identidade ou o nome oficial do projeto.

Mapeamentos oficiais:

- **Ranked → Arena da Vigília**.
- **GvG → Batalha de Guildas**.
- **Builds/presets → Doutrinas**.
- **Skills → Artes**.
- **Subclasse → Caminho**.
- **Profissões → Ofícios**.
- **Social → Vínculos**.
- **Login Diário → Dádiva Diária**.
- **Supporter Asterion → Patrono de Asterion**.
- **Recrutamento / Indicações → Chamado de Asterion**.
- **Códigos Promocionais → Códigos de Asterion**.
- **Fast Travel → Travessia dos Braseiros**.
- **Fast Access de Masmorra → Caminho Conhecido**.
- **Auto Hunt → Ronda de Caça**.
- **Hall da Fama / histórico competitivo → Salão da Vigília**.
- **Trilha de progressão do Passe da Crônica → Trilha da Crônica**; o produto/acesso Premium pode continuar sendo denominado **Passe da Crônica**.
- **Leaderboard competitivo principal → Classificação da Vigília**.
- **Explorar → Desbravar**.
- **Conquistas → Feitos**.
- **Epíteto → Título**.
- **Skin do personagem → Aparência**; o termo player-facing oficial é **Aparência**.
- **Cosméticos** é o hub player-facing de apresentação do personagem: Aparência, Título e Moldura.
- **Projetos da Guilda → Obras da Guilda**.
- **Coroas/moeda comum → Coroas**.
- **PR/rating visível → Renome**; MMR continua oculto e técnico.

Padronização de termos expostos ao jogador:

- `ready check` → **Confirmação de Entrada**;
- `matchmaking` → **Pareamento**;
- `cooldown` → **Recarga**;
- `loadout` → **Configuração de Combate**;
- `first clear` → **Primeira Conclusão**;
- `Trade` → **Troca Direta**;
- Terminologia de negociabilidade → **Negociável/Negociáveis** na linguagem de design/UI; nomes técnicos internos podem manter identificadores estáveis quando necessário.
- `Champion` → **Campeão**;
- `Boss` → **Chefe**, quando o termo for exibido ao jogador;
- `loot` → **Saque** ou **Recompensas**, conforme o contexto.

Esses mapeamentos são de nomenclatura/apresentação e não alteram regras mecânicas, econômicas ou de backend.

## 3. Mundo, cosmologia e geografia

### 3.1 Asterion e os antigos

- **Asterion** é o mundo jogável como um todo; não é o nome da civilização antiga.
- A civilização antiga é chamada de **civilização asteriana** ou **antigos asterianos**.
- Os antigos perceberam que o Véu estava se deteriorando e construíram âncoras para estabilizá-lo.
- A **Convergência** fazia parte da tentativa de estabilização/sobrevivência.
- Os **Desvelados** sabotaram a âncora central, contribuindo para a **Ruptura do Véu**.
- A história oficial culpa a busca por poder proibido; a verdade narrativa é mais complexa.
- O **Projeto Hemaris** está ligado a experimentos de sobrevivência e à origem/transformação dos Hemários.

### 3.2 O Avesso

- O termo cosmológico oficial é **Avesso**.
- O Véu separa e estabiliza Asterion em relação ao Avesso.
- No Avesso, memória, matéria, tempo, vida e morte podem obedecer a regras anormais.
- O Avesso **não é uma sétima região**. Ele se manifesta como domínios, reflexos e distorções ligados a lugares conhecidos.
- Antes da descoberta narrativa, o Avesso permanece oculto no Mapa, Códice e demais interfaces.

### 3.3 Regiões permanentes

A hierarquia oficial é:

**Asterion → Região → Local → Profundeza / Masmorra / Segredo / Fratura → Avesso**

As seis regiões são:

1. **Terras do Ocaso** — Nv.1–10.
2. **Vales dos Enforcados** — Nv.11–20.
3. **Planícies de Nareth** — Nv.21–30.
4. **Várzeas Carmesins** — Nv.31–40.
5. **Altos Cinéreos** — Nv.41–50.
6. **Confins do Véu** — Nv.51–60.

Filosofia de mundo: **“Poucas regiões. Muitos lugares. Muitas camadas.”**

Locais secretos/desconhecidos não aparecem como espaços vazios ou `???`; permanecem ausentes até serem descobertos, quando apropriado.

### 3.4 Estado global e estado pessoal

- `world_state` representa o estado atual global daquele servidor.
- `character_narrative_state` representa o ponto pessoal do personagem na história.
- Conteúdo antigo pode utilizar instâncias contextuais para mostrar uma versão histórica de um Local/NPC sem reverter o estado global.
- Mutações de `world_state` são versionadas, condicionais e idempotentes. Evento Mundial e Crônica não podem sobrescrever cegamente o mesmo estado.
- Sistemas de apresentação, incluindo **Flavor Text Contextual**, podem consultar `world_state`, `character_narrative_state`, progresso, descobertas e outros estados oficiais para determinar qual conteúdo é elegível para exibição.
- Essa consulta é somente de apresentação: selecionar ou exibir Flavor Text não modifica estado global, estado narrativo, economia, progressão ou combate.

## 4. Campanha principal

- Nome: **As Cinzas da Ruptura**.
- Estrutura: **36 missões principais**, 6 por Região.
- Bosses regionais:
  - Terras do Ocaso: **Vigia Partido**.
  - Vales dos Enforcados: **Matriarca das Raízes**.
  - Planícies de Nareth: **Arconte Invertido**.
  - Várzeas Carmesins: **Matriz Rubra**.
  - Altos Cinéreos: **Colosso Cinéreo**.
  - Confins do Véu: **Regente Fraturado**.
- A campanha revela gradualmente civilização asteriana, âncoras, Convergência, Projeto Hemaris, Desvelados, Avesso e a verdadeira Ruptura.
- Marcos, Missões e acontecimentos da Campanha podem criar ou atualizar Entradas/Trechos do **Códice** quando o conhecimento correspondente for legitimamente adquirido; isso respeita `character_narrative_state` e nunca antecipa revelações posteriores.
- Na **primeira jornada**, avançar para a próxima Região principal exige **nível mínimo + marco narrativo correspondente da campanha**.
- Depois do Legado, a campanha não é repetida; os gates narrativos já concluídos permanecem concluídos e retornam apenas os gates combatentes/de nível pertinentes.
- Missões principais **não podem ser abandonadas**. Elas podem ficar ativas, suspensas ou contextualizadas.
- **Suspensa** é um estado exclusivo de Missão Principal: a missão continua pertencendo à Campanha do personagem e preserva integralmente o progresso já conquistado, mas não pode avançar enquanto uma condição externa, de requisito, acesso ou contexto narrativo ainda não estiver satisfeita.
- Suspensão **não é abandono**, não pode ser escolhida manualmente como forma de desistência e não apaga progresso, decisões, flags ou recompensas já legitimamente registradas.
- Quando a condição que causou a suspensão volta a ser satisfeita, a Missão Principal retorna automaticamente ao estado **Em Andamento** quando aplicável.
- A UI deve apresentar a causa objetiva da suspensão quando ela puder ser revelada sem spoiler, por exemplo `⏳ Requer Nv. 8`; não utiliza ação genérica `[Retomar]` para esse estado.
- Missões Secundárias **não utilizam o estado Suspensa** por padrão; podem usar abandono/reaceitação conforme suas próprias regras.
- Abandonar/reaceitar uma Missão Secundária nunca remove flags narrativas permanentes, decisões irreversíveis, first-clears ou claims únicos já usados.

### 4.1 Missão Secundária acompanhada

- O jogador pode marcar **uma Missão Secundária ativa por vez** como acompanhada.
- Acompanhar outra Missão Secundária substitui automaticamente a anterior.
- Deixar de acompanhar uma missão não a abandona, conclui, reinicia nem altera seu progresso; acompanhamento é apenas uma seleção persistente de referência/HUD.
- A Missão Principal não depende desse sistema e continua sendo determinada pela Campanha.
- Se a Missão Secundária acompanhada deixar de estar ativa por conclusão, abandono ou outra condição válida, ela deixa automaticamente de ocupar o estado de acompanhada.
- O estado de acompanhamento pertence ao personagem, é persistido no backend e sobrevive a `/menu`, reconnect, reconstrução da interface e troca de dispositivo. `ui_session` nunca é autoridade para esse estado.
- Layout, ação/botão de acompanhar e forma de apresentação pertencem à Fonte de Visual/UI, não a esta regra mecânica.

## 5. Crônica I — Ecos da Convergência

- Nome: **Ecos da Convergência**.
- Duração: **8 semanas**.
- Estrutura: **8 capítulos principais, liberados em cadência exata de 7 dias**; o Capítulo 1 abre no início da Crônica e os Capítulos 2–8 a cada 7 dias.
- Começa no Dia 1 do lançamento e **não é endgame-only**.
- O progresso global pertence ao servidor; a apresentação narrativa é filtrada pelo progresso pessoal para evitar spoilers.
- Objetivos podem adaptar-se às Regiões já acessíveis ao jogador.
- Estados históricos de campanha podem usar instâncias pessoais mesmo quando o mundo público já mudou.
- Flavor Text relacionado à Crônica segue a mesma filtragem de progresso pessoal e proteção contra spoilers usada pelas demais apresentações narrativas.
- Crônicas podem criar ou atualizar Entradas/Trechos do **Códice** conforme o progresso pessoal; o conhecimento legitimamente descoberto pode permanecer como registro histórico depois do ciclo sem reabrir atividades, votos, economia ou recompensas encerradas.

### 5.1 Votação final

As quatro opções oficiais são:

- **Selar**.
- **Estabilizar**.
- **Entregar aos Herdeiros**.
- **Destruir**.

Elegibilidade de referência:

- completar pelo menos **4/8 capítulos**;
- participar de ao menos **1 objetivo da fase final**.

Os números podem ser ajustados em Beta.

Regras:

- O jogador possui 1 voto ativo por `conta + servidor + Crônica`.
- Pode alterar o voto até o deadline; nova escolha substitui a anterior.
- Excluir/recriar personagem não cria novo voto.
- O voto é idempotente.
- A votação principal termina antes do fechamento técnico da Crônica para permitir desempate e epílogo.
- Ao fechar a votação principal, cria-se um **snapshot dos eleitores elegíveis**.
- Em empate pelo primeiro lugar, há **runoff de 24h** apenas entre as opções empatadas e somente para o eleitorado congelado no fechamento da votação principal.
- O runoff usa o mesmo eleitorado congelado.
- Se persistir empate exato, aplica-se um desfecho neutro/predefinido e publicado nas regras, nunca escolha arbitrária do administrador.

### 5.2 Catch-up e arquivamento

- Jogador atrasado pode recuperar a história pessoal e escolhas permitidas.
- Catch-up **não** reabre votação global, Passe antigo, leaderboard, geração econômica sazonal ou recompensas competitivas expiradas.
- Conteúdo da Crônica deve ser classificado em **Persistir / Arquivar / Remover**.
- Existe período pós-Crônica de **14 dias**, exclusivamente para resgate de recompensas já desbloqueadas; depois disso a liquidação final automática é idempotente.
- Durante o período de resgate não se ganha novos pontos nem se altera o resultado global.
- Compra do Passe da Crônica após o encerramento oficial da Crônica fica bloqueada.
- Catch-up realizado enquanto a Crônica ainda estiver ativa pode conceder progresso da Trilha somente através das fontes que continuarem legitimamente disponíveis.
- Catch-up posterior ao encerramento nunca reabre a Trilha nem gera novos Marcos.
- O período pós-Crônica existe apenas para resolver recompensas da Trilha já desbloqueadas; ao fim desse período, direitos ainda pendentes são liquidados automaticamente uma única vez e a Trilha é arquivada.

### 5.3 Crônica como ciclo competitivo

- Cada Crônica também funciona como o ciclo competitivo principal da **Arena da Vigília (Ranked)** e da **Batalha de Guildas (GvG)**.
- No encerramento: a **Classificação da Vigília**/leaderboard aplicável é fechada, recompensas cosméticas/prestígio são calculadas e o histórico é arquivado.
- O MMR oculto não é zerado entre Crônicas.
- **Renome** (PR/rating visível) sofre o **soft reset entre Crônicas** definido na seção 49; não existe reset total na baseline v1.0.
- O ciclo possui duas etapas: **fechamento de entrada** e **finalização real**, após atividades já iniciadas terminarem ou atingirem a grace period.
- O leaderboard só é congelado após a finalização real.
- Extensão excepcional de ciclo é permitida apenas antes do processo de fechamento, com `cycle_end_at` explícito, log e comunicação pública.

### 5.4 Trilha da Crônica

#### Função

A **Trilha da Crônica** é a progressão sazonal vinculada à Crônica vigente. O **Passe da Crônica** é o produto que libera o acesso às recompensas Premium da mesma Trilha.

A Trilha possui:

- uma única progressão;
- **Marcos** sequenciais;
- recompensas Livres;
- recompensas Premium.

Livre e Premium utilizam **exatamente o mesmo progresso**. Não existe XP/pontuação Premium separada. Quantidade de Marcos, thresholds e distribuição de recompensas estão consolidados na seção 49.

#### Escopo do progresso

O progresso é persistido por:

`conta + servidor + Crônica`

Excluir ou recriar personagem não reinicia a Trilha, não recria direitos de recompensa, não permite repetir Marcos e não duplica claims.

#### Ganho de progresso

O jogador progride principalmente através das **atividades normais da própria Crônica**, incluindo quando explicitamente configuradas:

- conclusão de capítulos;
- objetivos da Crônica;
- objetivos narrativos;
- descobertas relacionadas;
- Desbravar associado à Crônica;
- Eventos Mundiais associados;
- Masmorras ou outros conteúdos vinculados;
- outros marcos definidos pelo Conteúdo da Crônica.

Cada fonte declara quantidade de progresso, escopo, se é única ou repetível e limites aplicáveis. Valores e limites estão consolidados na seção 49.

No lançamento, a Trilha **não possui uma segunda lista independente de desafios criada apenas para alimentar o Passe**. O jogador progride jogando a própria Crônica e os conteúdos que ela integra.

Fontes repetíveis precisam possuir limite/escopo quando necessário. O mesmo evento, objetivo ou conclusão não gera progresso novamente por callback repetido, reconnect, troca de dispositivo, retry técnico, job duplicado ou processamento repetido.

#### Marcos

Cada Marco possui requisito de progresso e pode conter recompensa Livre, Premium, ambas ou, quando necessário pelo design, apenas uma delas.

Atingir um Marco:

- registra permanentemente seu desbloqueio naquela Crônica;
- não consome o progresso acumulado;
- não impede avanço aos Marcos seguintes.

Não existe compra de Marcos, níveis, pontos ou skip de progresso no lançamento.

#### Recompensas Livres

A trilha Livre está disponível a todos os participantes elegíveis da Crônica.

Pode conceder:

- Aparências;
- Títulos;
- Molduras;
- outros colecionáveis somente se uma nova categoria for explicitamente aprovada; este fechamento não cria categoria adicional;
- prestígio;
- recompensas gratuitas controladas de gameplay/economia explicitamente previstas pelo Balanceamento.

Recompensa econômica Livre não decorre de pagamento, possui quantidade limitada, respeita as regras gerais de economia e não deve substituir Caçadas, Masmorras, Eventos ou outros loops econômicos normais. Tipos e valores estão consolidados na seção 49.

#### Recompensas Premium

A camada Premium é desbloqueada pelo **Passe da Crônica**.

Recompensas Premium ficam restritas a apresentação, coleção e prestígio, incluindo:

- Aparências;
- Títulos;
- Molduras;
- outros colecionáveis sem vantagem de gameplay somente se uma nova categoria for explicitamente aprovada; este fechamento não cria categoria adicional.

A camada Premium **não concede** XP, Coroas, Vigor, Poções, Equipamentos, Runas, materiais, aumento de drop, tentativas adicionais, progresso de Legado, Renome/MMR, votos, vantagem em Arena da Vigília, vantagem em Batalha de Guildas ou qualquer outro benefício econômico/de poder.

Recompensas Premium são não negociáveis e, quando constituírem cosméticos pagos, seguem as regras gerais de entitlement.

#### Compra tardia do Passe

O Passe pode ser adquirido enquanto a Crônica estiver ativa e a janela de compra permanecer aberta.

Comprar o Passe:

- não adiciona progresso;
- não altera thresholds;
- não compra Marcos;
- não modifica recompensas Livres já obtidas.

Ao ativar o Passe, todos os Marcos Premium já alcançados pelo progresso normal tornam-se **retroativamente elegíveis para resgate**. A retroatividade usa o progresso persistido e não recalcula nem rerrola atividades anteriores.

Depois do encerramento oficial da Crônica, novas compras daquele Passe ficam bloqueadas.

#### Resgate

Alcançar um Marco cria elegibilidade para a recompensa correspondente. A interface pode utilizar uma ação agregada, como **Resgatar Disponíveis**, evitando exigir uma confirmação individual para cada Marco.

O backend determina as recompensas desbloqueadas, elegíveis e ainda não entregues. Cada recompensa possui registro próprio de claim/grant; múltiplos cliques, callbacks antigos, reconnect ou jobs repetidos não duplicam entrega nem entitlement.

Recompensa física que não possa ser entregue diretamente utiliza Entrega Pendente. Cosméticos/entitlements não dependem de espaço no Inventário.

#### Encerramento da Crônica

A Trilha segue o fechamento da própria Crônica.

- novas fontes de progresso deixam de ser aceitas conforme o cutoff oficial;
- atividades validamente iniciadas antes do fechamento podem resolver-se durante a grace period quando sua regra permitir;
- após a finalização real, o progresso é congelado;
- nenhum novo Marco pode ser alcançado;
- não se obtêm novos pontos;
- não é possível comprar o Passe daquela Crônica.

Somente recompensas já desbloqueadas permanecem disponíveis durante o período pós-Crônica, cuja duração está consolidada na seção 49.

No término desse período, recompensas já conquistadas e ainda não resgatadas são **liquidadas automaticamente uma única vez**, usando Entrega Pendente ou entitlement quando necessário. O fim da janela nunca cria novos direitos; apenas resolve direitos já existentes.

#### Idempotência

Progresso, desbloqueio de Marco e recompensa são estados distintos e idempotentes.

Chaves conceituais podem incluir:

- `account + server + chronicle + progress_event`;
- `account + server + chronicle + milestone`;
- `account + server + chronicle + milestone + free_reward`;
- `account + server + chronicle + milestone + premium_reward`.

A implementação pode usar estrutura equivalente, desde que exclusão/recriação de personagem, callback antigo, crash/recovery, troca de dispositivo ou repetição de webhook/pagamento não criem progresso, desbloqueio ou recompensa duplicados.

## 6. Conta, personagem e criação

- 1 conta Telegram = **1 personagem por servidor**.
- Múltiplas contas Telegram são permitidas, sujeitas às regras antiabuso.
- Uma conta é um único ator lógico mesmo se estiver aberta em vários dispositivos.
- Nome do personagem: 3–16 letras A–Z, sem acentos, números, espaços ou símbolos; unicidade por servidor; comparação case-insensitive; capitalização visual padronizada.
- Nomes ofensivos, reservados ou administrativos são bloqueados.
- Criação: **nome → raça → classe → confirmação final → prólogo jogável “Cinzas na Estrada”**.
- O prólogo ensina Ataque/Defender, depois habilidade, primeiro Braseiro e menu inicial.
- `/start` recupera o personagem persistente existente.
- Callbacks antigos ou inválidos falham com segurança.

#### Primeiro encontro do prólogo — Cão Cinéreo

Ao acionar `[Seguir pela Estrada]`, o prólogo cria um encontro Foreground autoritativo e persistente com o **🐺 Cão Cinéreo**. Este é um encontro **único, narrativo e tutorial**, não uma Caçada econômica.

Perfil autoritativo:

- nível **Nv.1**;
- categoria **Comum**;
- arquétipo **Predador**;
- sem Variante;
- Grupo Solo `1,00×`;
- perfil de conteúdo `prologue_first_combat`: HP `0,60×`, ATQ `0,55×`, DEF `0,75×`, AGI `0,65×`;
- atributos finais: **244 HP / 50 ATQ / 45 DEF / 56 AGI**;
- **Mordida Cinérea:** `100% ATQ`, Dano Direto, 1 alvo;
- **Investida Cinérea:** `120% ATQ`, Dano Direto, 1 alvo;
- sem DoT, Debuff, Cura, Barreira, Bloqueio próprio, Esquiva própria ou mecânica especial;
- comportamento normal determinístico após a fase pedagógica: **Mordida → Mordida → Investida → repetir**. Ao encerrar a etapa obrigatória da primeira Arte, se o Cão continuar vivo, a sequência normal começa em **Mordida**.

### Resultado — Vitória

Vitória válida:

- resolve o encontro e conclui o Prólogo;
- concede os 320 XP do tutorial;
- concede 0 Coroas;
- não concede Saque nem Material;
- não consome Vigor;
- segue ao **🔥 Braseiro da Estrada**.

### Resultado — Derrota

Derrota válida:

- resolve definitivamente o encontro e conclui o Prólogo;
- não concede os 320 XP do tutorial e concede 0 XP;
- concede 0 Coroas;
- não concede Saque nem Material;
- não consome Vigor;
- segue ao mesmo **🔥 Braseiro da Estrada**.

TutorialXP = 320 somente em player_victory; TutorialXP = 0 em player_defeat. Não existe XP parcial, recompensa compensatória nem aplicação da fórmula normal de XP de inimigo na Derrota.

Vitória e Derrota são resultados válidos de conclusão do Prólogo. A Derrota não cria retry, recovery de missão, segunda identidade de encontro, reroll, segundo combate, softlock ou falha permanente. Ela não remove Coroas existentes, Equipamentos, Materiais, itens, XP previamente obtido nem progressão permanente; sua única diferença de recompensa é não conceder os 320 XP do tutorial.

Ambos os resultados convergem para o estado já existente do **🔥 Braseiro da Estrada**. O Braseiro continua usando [Descansar] e as regras normais de restauração; a Derrota não restaura HP fora dele. Depois da resolução válida, o combate deixa de ser Foreground. Reconnect, /start, /menu e troca de dispositivo reconstroem o estado pós-encontro, começando pelo Braseiro enquanto essa for a próxima etapa pendente; callbacks antigos falham com segurança e nunca reativam o combate resolvido.

Após a conclusão válida do Prólogo e a passagem normal pelo Braseiro, P1 — **Vozes na Estrada** inicia normalmente nos dois resultados. O gate é a conclusão do Prólogo; não pode exigir Vitória nem prologue_victory = true. Esta regra é específica do encontro tutorial e não altera as condições de derrota de outras atividades. Em particular, P1 mantém sua própria exigência de Vitória na Etapa 3 e seu recovery/retry.

O encontro do tutorial pode registrar normalmente a observação/evidência legítima do Cão Cinéreo no Bestiário, mesmo em Derrota, mas não concede separadamente o bônus genérico de 1% de XP da primeira observação. Os thresholds e a regra geral do Bestiário permanecem inalterados.

Máquina pedagógica do primeiro combate:

1. estado inicial: `[Atacar] [Defender]` simultaneamente;
2. o jogador escolhe livremente uma das duas ações;
3. após **Atacar**, o Cão responde com **Mordida Cinérea**; após **Defender**, responde com **Investida Cinérea**, demonstrando a mitigação;
4. na oportunidade seguinte, apenas a ação pedagógica entre Atacar/Defender ainda não utilizada permanece válida;
5. depois que Atacar e Defender tiverem sido usados ao menos uma vez, revelar somente a **primeira Arte da Classe** como próximo passo pedagógico obrigatório;
6. após o primeiro uso válido dessa Arte, a máscara pedagógica termina e a HUD/IA passam às regras normais; se a Arte derrotar o Cão, o combate termina antes de qualquer resposta inimiga.

O tutorial controla apenas a disponibilidade player-facing das ações durante essas etapas; não altera o desbloqueio real da Arte nem as regras normais de Ataque Básico, Defender, Recarga, dano, status ou iniciativa.

### 6.1 Classe, Raça e Caminho (Subclasse)

- Classe e Raça são **permanentes no lançamento**.
- Subclasse é reversível em cidade/local apropriado mediante Coroas.
- Mudança futura de Classe/Raça, se existir, exigirá sistema próprio.

### 6.2 Escopo administrativo da Conta

Na organização player-facing, **Configurações → Conta** é reservado a ações administrativas/sensíveis do personagem:

1. ✏️ **Renomear Personagem · Identidade**;
2. 🗑️ **Excluir Personagem · Exclusão**.

Aparência, Títulos e Molduras não pertencem a Conta; ficam em **Personagem → Cosméticos**.

### 6.3 Exclusão

- Exclusão do personagem possui período pendente/cancelável de **7 dias**; nomes permanecem reservados por **30 dias** após exclusão definitiva.
- Enquanto pendente, o personagem continua ocupando o slot, nome permanece reservado e novas operações competitivas/econômicas incompatíveis podem ser bloqueadas.
- Cancelar a exclusão restaura o mesmo personagem.
- Exclusão definitiva é workflow transacional: resolve Guilda, Mercado, escrow, Serviços, Trades, filas, rosters, grupos, recompensas pendentes e vínculos.
- Logs econômicos, competitivos e administrativos não são apagados junto do personagem.
- Entitlements pagos account-wide sobrevivem à exclusão.

## 7. Raças

Raças oficiais:

- **Remanescentes** — identidade flexível.
- **Velados** — melhor preservação de efeitos positivos/resistência a negativos; a implementação deve respeitar turnos inteiros, sem duração fracionária; detalhe numérico conforme a seção 49.
- **Cinéreos** — Defender ligeiramente melhor.
- **Hemários** — recuperação/vampirismo quando em HP baixo, controlado.
- **Alvoranos** — iniciativa e resistência a debuffs.

Impacto racial deve ser pequeno, aproximadamente 3–5% de referência, sem criar combinações obrigatórias. Valores finais consolidados na seção 49.

## 8. Classes, Caminhos (Subclasses), Artes (Skills) e Talentos

### 8.1 Classes e Caminhos (Subclasses)

- **Sentinela:** Bastião / Devastador.
- **Errante:** Carrasco / Sabotador.
- **Vigia:** Atirador / Rastreador.
- **Tecelão:** Conjurador / Rúnico.
- **Oráculo:** Agoureiro / Invocador.
- **Luminar:** Guardião / Inquisidor.

### 8.2 Provação e Caminho (Subclasse)

- Cada Classe possui **uma única Provação de Classe**.
- A Provação desbloqueia permanentemente o sistema de Subclasse e torna as duas Subclasses daquela Classe disponíveis.
- O jogador escolhe a Subclasse inicial após a Provação.
- Troca posterior: cidade/local apropriado + Coroas.
- Não existe segunda Provação para trocar.
- A Provação permanece concluída através do Legado.

### 8.3 Artes (Skills)

- Artes de Classe/Caminho são desbloqueadas automaticamente por nível/requisitos.
- Não existe moeda genérica de pontos de Arte no lançamento.
- O personagem equipa **até 3 Artes Ativas**.
- Ataque Básico e Defender não ocupam esses 3 slots.
- Passivas raciais, de Classe/Caminho e Talentos também ficam fora desses slots.
- Não existe sistema separado de “Ultimate”; Artes fortes usam Recarga/condição normal.
- Invocador usa manifestações de Lobo/Coruja/Urso como efeitos do Oráculo, não como pets/combatentes: sem HP, turno ou iniciativa próprios.
- Em conteúdos com automação de combate explicitamente prevista, como a **Ronda de Caça**, o sistema só pode executar automaticamente as Artes Ativas equipadas na Configuração de Combate registrada para a atividade.
- Artes aprendidas, mas não equipadas, não ficam disponíveis para a automação.
- Ataque Básico e Defender continuam disponíveis por suas regras universais.
- Toda Arte utilizada automaticamente continua obedecendo normalmente a Recarga, recursos, custos, condições, alvo, requisitos e demais regras de execução.
- Automação nunca concede acesso excepcional a uma Arte que uma ação manual válida não poderia executar naquele mesmo estado.

### 8.4 Talentos

- Pontos de Talento são obtidos por progressão de nível.
- Quantidade, níveis e tamanho da árvore estão consolidados na seção 49.
- Após Legado, apenas os pontos compatíveis com o nível atual ficam ativos; os demais retornam conforme o personagem sobe.
- Respec de Talentos ocorre apenas em local seguro apropriado, com custo em Coroas conforme a seção 49 e **sem Recarga temporal** na baseline v1.0.
- Uma Doutrina pode salvar uma distribuição desejada, mas não concede respec gratuito.
- Se uma Doutrina exige distribuição diferente, o sistema solicita o respec e aplica suas regras.
- Patch que remova/modifique Talento migra ou invalida com segurança as Doutrinas correspondentes.

### 8.5 Doutrinas (Builds / presets)

- Cada personagem pode possuir até **5 Doutrinas** no lançamento.
- As 5 Doutrinas são gratuitas e podem receber nomes personalizados pelo jogador.
- Uma Doutrina registra o estado desejado de:
  - **Caminho**;
  - **Equipamentos** específicos dos 8 slots, por `item_instance_id`;
  - **3 Artes Ativas** e seus slots;
  - **distribuição de Talentos**.
- **Runas e Encantamentos não são campos separados da Doutrina.** Eles pertencem ao estado atual da `item_instance` referenciada. Se uma Runa ou Encantamento do equipamento mudar, a Doutrina usa aquele mesmo item em seu estado atual; nunca recria uma configuração antiga do item.
- **Consumíveis ficam fora da Doutrina geral.** Em PvE manual, eles não exigem preparação ou preset prévio: Consumíveis elegíveis presentes no Inventário ficam disponíveis pelas regras do conteúdo. Conteúdos automatizados podem exigir autorização/preparação própria.
- Ataque Básico, Defender e passivas raciais/de Classe/Caminho/Talentos não precisam ser registrados como campos do preset; são derivados do estado válido do personagem.
- Carregar uma Doutrina não ignora custo, local, Recarga ou qualquer outra regra de troca de Caminho ou respec de Talentos.
- A aplicação completa da Doutrina é validada **atomicamente**. Se o estado final for inválido, nada é alterado silenciosamente pela metade.
- Uma Doutrina pode ficar **Incompleta** ou **Requer Respec** quando houver item ausente, item no Armazém/escrow, requisito de nível não atendido, Arte indisponível, Caminho incompatível, Talento migrado por patch ou qualquer outra dependência inválida.
- Doutrina incompleta nunca recria item, ignora requisito ou força estado ilegal.
- Após Legado e patches, Doutrinas são revalidadas pelas mesmas regras centrais de equipamento, Caminho, Talentos e Artes.
- Conteúdos automatizados podem registrar uma preparação/autorização própria de Consumíveis separada da Doutrina.
- Na Ronda de Caça, iniciar o lote registra a Configuração de Combate válida e a preparação de Consumíveis selecionada para aquela Ronda.
- A automação utiliza essa configuração; não cria uma Doutrina alternativa nem acessa opções fora dela.
- Durante atividades com Configuração de Combate travada, carregar/trocar Doutrina ou alterar qualquer componente combatente fica sujeito à regra global da seção 39.

## 9. Combate — fundamentos

### 9.1 Turnos e iniciativa

- Combate é por turnos.
- Iniciativa global usa AGI do maior para o menor, uma vez por rodada.
- Mudanças de AGI afetam a próxima rodada.
- Empate de AGI usa prioridade determinística definida no início do combate pelo RNG do `combat_id` e permanece estável na luta.
- Não há grid, distância física, linha de frente/trás ou movimentação espacial no lançamento.
- “Melee” e “Ranged” são tags/identidades mecânicas, não posições.
- Não há friendly fire por padrão.

### 9.2 Fórmula base

- Dano bruto: `ATQ × coeficiente`.
- Redução por DEF: `DEF / [DEF + (100 + 5 × nível do atacante)]`.
- Perfuração/-DEF entram antes da fórmula de DEF.
- Precisão interna é alta; arredondamento ocorre apenas ao final da quantidade.
- Dano final positivo usa `floor` e mínimo de 1 quando houve acerto válido, salvo imunidade/efeito que zere explicitamente.
- Cura e Barreira usam `floor`, mínimo 0.
- Floors universais: HP Máximo ≥ 1; ATQ/DEF/AGI ≥ 0; HP atual entre 0 e HP Máximo; CRIT/Esquiva/Bloqueio respeitam caps.
- Overheal é descartado por padrão e não vira Barreira automaticamente.

### 9.3 Crítico, Esquiva, Bloqueio e Defender

Valores oficiais da Baseline Numérica v1.0:

- Chance-base de CRIT: **5%**; dano crítico-base: **150%**.
- PvP: chance de CRIT cap **40%**; dano crítico cap **200%**.
- DoTs e Curas não critam por padrão.
- Esquiva-base **0%**; cap PvP **25%**.
- Após 2 Esquivas consecutivas, o próximo ataque básico/ofensivo direto elegível contra aquele alvo não pode ser Esquivado.
- Bloqueio-base **0%**; cap **30%**; redução em bloqueio válido **35%**.
- Defender reduz **45%** do dano direto até o próximo turno; não pode ser executado em oportunidades consecutivas nas quais Defender foi de fato usado.
- Se um turno intermediário foi perdido por Stun e Defender não foi executado, a próxima oportunidade pode usar Defender.
- Na Ruptura Final, Defender reduz **30%**.
- Mitigação ativa multiplicativa possui cap **65%**, separado da redução natural de DEF.
- PER base: **0%** e cap de PER: **30%**.

### 9.4 HP, Cura, Barreira e Vampirismo

- Cura: `ATQ × coeficiente × bônus`.
- Cura em PvP: **90%** do valor PvE antes da Exaustão.
- Barreira é HP temporário.
- Barreiras de fontes diferentes podem coexistir até cap; em PvP o cap é **35% do HP Máximo**.
- “Mesma fonte” = `applier_id + effect_definition_id`.
- Nova Barreira da mesma fonte substitui valor e duração pela nova aplicação, salvo regra explícita de renovação.
- Barreira absorve DoT, salvo exceção explícita.
- Se mudança de HP Máximo reduz o cap de Barreira, excesso é cortado imediatamente.
- Vampirismo usa apenas dano direto real causado ao HP depois de mitigação/Barreira, sem overkill e sem DoT.
- Vampirismo de uma ação AoE/multi-hit é agregado e aplicado como **um único evento de cura por ação**, salvo exceção explícita.
- Ordem consolidada: dano primário → Barreira → HP de todos os alvos → Vampirismo agregado da ação → determinação das derrotas primárias → triggers/reactions posteriores.
- Vampirismo não ressuscita alguém que já estava Derrotado antes da ação.

### 9.5 Derrota e ressurreição

- Não existe ressurreição em combate no lançamento.
- Cura/Barreira comum não pode mirar personagem Derrotado.
- Efeitos independentes já aplicados, como DoT, podem persistir após a fonte ser derrotada.
- Aura, Link, Canal ou efeito que exige presença ativa da fonte termina quando a fonte deixa de estar válida.

### 9.6 IA PvE normal e Ações Preparadas

#### IA PvE normal

- Criaturas PvE utilizam decisão **server-authoritative e determinística por padrão**.
- Em cada oportunidade válida da criatura, a precedência normal é: **(1)** resolver Ação Preparada pendente e apta; **(2)** aplicar condições/prioridades explicitamente definidas pelo Conteúdo; **(3)** avaliar Defender quando a criatura possuir permissão/política para usá-lo; **(4)** escolher Arte especial válida e fora de Recarga; **(5)** usar ataque simples/fallback.
- Sequência fixa ou prioridade explicitamente declarada pelo Conteúdo sempre prevalece sobre a política genérica. Isso inclui máquinas pedagógicas, Chefes, Elites e qualquer comportamento regional explicitamente fechado.
- Quando mais de uma Arte especial estiver simultaneamente válida e o Conteúdo não declarar prioridade própria, utiliza-se a **ordem canônica das Artes na definição da criatura**. Empate técnico residual usa `action_definition_id` estável.
- A política padrão não usa RNG. Conteúdo que explicitamente exigir comportamento aleatório pode usar apenas o RNG determinístico/idempotente do combate; reconnect, retry ou reconstrução da UI nunca rerrolam decisão já materializada.
- Ação especial só é candidata quando passa sua validação normal, incluindo estado/fase, Recarga, condição declarada, alvo válido e impedimentos de execução. Quando nenhuma especial for válida, utiliza-se o ataque simples/fallback.
- A IA não consulta informação oculta ou futura que a criatura não deveria conhecer, como Inventário do jogador, ação ainda não comprometida, troca futura de Doutrina ou intenção de uso de Consumível.
- Criatura só pode usar Defender quando o Conteúdo permitir. Quando o Conteúdo disser apenas que a criatura **pode utilizar Defender conforme IA**, sem política adicional, usa-se o padrão determinístico: **duas ações ofensivas comprometidas → Defender → repetir**. Defender válido zera o contador. Oportunidade perdida sem ação comprometida não incrementa nem zera. Se Defender estiver devido, mas for ilegal naquela oportunidade, a criatura usa seu fallback ofensivo e mantém Defender como devido para a próxima oportunidade em que seja legal.

#### Ação Preparada

- Uma Arte marcada como **Preparada** é uma ação em duas etapas: **preparação/telegraph** e **resolução**.
- Iniciar a preparação consome a oportunidade atual da fonte, não aplica ainda o dano/efeito final, persiste o estado de preparação e compromete a Recarga naquele momento. A oportunidade de preparação não conta como primeiro tick da própria Recarga.
- Depois da preparação, o alvo deve possuir **ao menos uma oportunidade normal de turno** antes da resolução. Preparada não concede turno extra, remove CC ou cria exceção às regras normais dessa oportunidade.
- A resolução ocorre na primeira oportunidade elegível posterior da fonte depois que a janela de resposta do alvo ocorreu. Se uma alteração de iniciativa fizer a fonte receber nova oportunidade antes dessa resposta, a preparação permanece pendente e não resolve antecipadamente.
- A resolução é continuação da mesma ação comprometida: não seleciona nova Arte, não inicia nova Recarga e não realiza novo pagamento de custo; consome a oportunidade de resolução da fonte.
- Se a fonte for Derrotada antes da resolução, a preparação termina sem efeito. Se continuar válida mas perder a oportunidade por Stun ou impedimento equivalente, a preparação permanece pendente e tenta resolver na próxima oportunidade elegível, salvo cancelamento explicitamente definido.
- Se o alvo único estiver Derrotado, removido ou inválido no momento da resolução, a ação termina sem retarget automático e sem restituição de oportunidade/Recarga. Em ação multi-alvo, somente alvos ainda válidos continuam elegíveis.
- Condições táticas usadas pela IA para decidir **iniciar** a preparação não são reavaliadas para cancelar arbitrariamente uma ação já comprometida; na resolução, revalidam-se apenas requisitos necessários à execução válida.
- Defender não é ignorado por Ação Preparada. Se sua proteção estiver válida quando o Dano Direto preparado resolver, aplica-se normalmente.
- O snapshot persistido precisa representar de forma equivalente: `action_id`, fonte, alvo(s), oportunidade de preparação, janela de resposta, Recarga comprometida, estado de resolução e uma identidade idempotente da ação.
- Reconnect ou outro dispositivo reconstruem o telegraph pendente a partir desse estado. Callback repetido, retry ou recovery não podem preparar novamente, reiniciar Recarga nem resolver a mesma ação mais de uma vez.

## 10. Efeitos, duração, cooldowns e CC

### 10.1 Duração em T

- Interface usa **T**, não R, para efeitos pessoais: por exemplo `🩸² 2T`, `☣️² 3T`, `⬇️ DEF 2T`.
- `NT` = próximas N oportunidades de turno do personagem afetado após a aplicação.
- Se efeito é aplicado no próprio turno, o turno atual não consome duração.
- Se aplicado no alvo antes de ele agir, a próxima oportunidade dele conta como primeiro T.
- DoTs normalmente tickam no fim do turno do afetado e depois decrementam duração.
- Cooldowns também avançam por oportunidade de turno do proprietário.
- Stun consome a oportunidade e faz cooldowns/durações avançarem.
- Cooldowns sempre resolvem para oportunidades inteiras; não há `1,6T` invisível.

### 10.2 Cooldown

Exemplo oficial: skill CD2 usada no T1 fica indisponível no T2 e volta no T3. O turno de uso não é o primeiro tick do cooldown.

### 10.3 Stacking

- Efeito stackável acumula até o cap próprio.
- Não-stack de mesma potência renova para a maior duração válida.
- Versão mais forte substitui **potência e duração** pela nova aplicação.
- Versão mais fraca não substitui a forte, salvo regra explícita.
- O mesmo framework vale para buffs e debuffs.
- Purificação comum remove 1 stack de um efeito stackável ou remove completamente 1 efeito não-stack.
- Dispel, se existir, é categoria separada para remover efeitos positivos.

### 10.4 DoTs

Valores oficiais:

- **Veneno:** `12% ATQ` por stack/tick, `3T`, máximo **3** stacks.
- **Sangramento:** `10% ATQ` por stack/tick, `2T`, máximo **3** stacks; cada ação agressiva do afetado causa adicional de `3% ATQ snapshot` por stack.
- **Queimadura:** `15% ATQ` por stack/tick, `2T`, máximo **2** stacks; `-5% Cura recebida` por stack.

Regras:

- Cada stack mantém fonte e snapshot ofensivo próprios.
- A duração visual do status é compartilhada.
- Nova aplicação em status no cap substitui o stack mais antigo.
- Purificação comum também remove o stack mais antigo.
- DoT faz snapshot de ATQ na aplicação, não crita, não gera Vamp, não faz novo teste de Esquiva e usa **50% da DEF efetiva normal** por padrão, salvo definição explícita diferente.
- Se a fonte já foi Derrotada, o DoT independente continua e preserva crédito estatístico, mas passivas que exigem fonte ativa não disparam.

### 10.5 CC e aplicação de status

- Pipeline: tentativa → imunidade absoluta → resistência/redução válida → stacking/substituição → duração.
- Ação válida que encontra Imunidade/Resistência ainda consome recursos e cooldowns; apenas ação rejeitada antes da execução não consome, salvo exceção explícita.
- Bosses convertem hard CC em redução parcial/postura/mecânica própria quando apropriado.
- Não há stun-lock comum, silêncio total recorrente, medo/confusão/taunt forçado generalizado.
- Geada atua em AGI/ritmo.
- Tenacidade/imunidade individual usa T; rodadas ficam para mecânicas globais.

### 10.6 Pacotes operacionais de Variantes

- **Hemorrágico** mantém seu modificador de stats global e habilita um pacote de Sangramento. Toda ação ofensiva elegível de **Dano Direto** pode carregar no máximo `+1 Sangramento` por alvo e por ação através desse pacote.
- São elegíveis: ataque simples, Arte de Dano Direto, Ação Preparada de Dano Direto, AoE e multi-hit. Em AoE/multi-hit, a Variante aplica no máximo uma vez por alvo para a ação inteira.
- Não são elegíveis: tick de DoT, Dano de Reação, Dano Refletido, Dano Ambiental, Cura, Barreira, Defender ou ação sem Dano Direto.
- Se uma ação já aplica Sangramento nativamente, o pacote Hemorrágico **não adiciona outro stack naquela mesma ação**; a aplicação nativa satisfaz o pacote.
- Para uma ação que recebeu Sangramento exclusivamente pela Variante, a aplicação ocorre somente enquanto o alvo estiver abaixo do cap global; no cap, o rider adicional da Variante é omitido. Aplicações nativas continuam obedecendo integralmente às regras globais normais de stacking/substituição.
- O pacote Hemorrágico não possui Recarga interna própria. Ele acompanha a ação que o carrega e usa o mesmo pipeline de validade/acerto/status; não cria teste independente.
- **Venenoso** segue a mesma semântica operacional, substituindo Sangramento por Veneno: no máximo `+1 Veneno` por alvo e por ação ofensiva elegível de Dano Direto, sem stack adicional quando a própria ação já aplica Veneno, sem Recarga interna e respeitando o cap global.
- **Furioso, Resistente e Ágil** alteram apenas os stats definidos em seus pacotes globais. Por si mesmas, essas Variantes não alteram prioridade de IA, Recarga, frequência de Defender, preferência de alvo, telegraph ou condições das Artes.

## 11. Tipos de dano, AoE, multi-hit e triggers

Tipos internos:

- **Dano Direto**.
- **DoT**.
- **Dano de Reação**.
- **Dano Refletido**.
- **Dano Ambiental**.

Defaults:

- Refletido não crita, não gera Vamp e não gera novo Reflexo.
- Reação não inicia cadeias recursivas infinitas e só ativa triggers explicitamente permitidos.
- Ambiental segue a mecânica do cenário/Boss e não precisa usar interações ofensivas comuns.

AoE/multi-hit:

- Skill pode declarar `hit_count`, `crit_per_hit`, `accuracy_per_hit` e escopo de triggers.
- Dano multi-hit é resolvido golpe a golpe; hits elegíveis podem critar separadamente.
- Triggers declaram `per_action`, `per_hit` ou `per_target`.
- Recursos pessoais são `per_action` por padrão.
- Seleção limitada de alvos nunca depende da ordem do banco; usa critério determinístico ou RNG idempotente.
- Para AoE simultâneo, todos os resultados primários usam o estado pré-evento. Um alvo morrer não buffa retroativamente o dano do mesmo AoE nos demais.

## 12. Ordem de resolução e RNG

### 12.1 Ordem geral de ataque

Validação de ação/alvo → acerto/Esquiva → bruto → crítico → modificadores ofensivos → Perfuração/-DEF → DEF → Defender/Bloqueio/mitigação → Barreira → HP → Vampirismo quando aplicável → status/on-hit → resolução de derrotas/triggers conforme as fases do evento.

### 12.2 Simultaneidade

- Eventos simultâneos calculam resultados com estado pré-evento e aplicam em lote.
- Fases fixas: evento primário → prevenção/substituição → dano/cura → estado final → derrotas → triggers de derrota → pós-evento → limpeza de expirados.
- Morte simultânea entre lados = empate quando aplicável.
- Uma trigger não pode reativar infinitamente a própria cadeia; cada trigger é limitada por evento conforme definição.

### 12.3 RNG

- RNG de recompensa/crafting/reroll é idempotente: o evento persiste um único resultado.
- RNG de combate também é determinístico/idempotente, ligado a `combat_id + action_id + event_id`.
- Crítico, Esquiva, Bloqueio, desempate de AGI, IA aleatória e mecânicas aleatórias de Boss repetem exatamente o mesmo resultado em retry.
- O cliente nunca controla seed.

## 13. Exaustão no PvP

- Rodadas 1–19: Cura/Barreira em **100%** do valor PvP normal.
- Rodada 20: **90%**; 21: **80%**; 22: **70%**; 23: **60%**; 24: **50%**; 25+: **35%**.
- Na Rodada 25 entra **Ruptura Final**: Defender passa de 45% para **30%**; Cinéreo passa de 52% para **37%**.
- A partir da Rodada 26, Dano Final de combatentes recebe `+10% × (Rodada − 25)`, sem cap artificial.

## 14. PvP — Duelo e Arena da Vigília (Ranked)

### 14.1 Regra central

**Nenhum modo PvP equaliza ou normaliza atributos.** Poder real do personagem é utilizado.

### 14.2 Duelo

- Disponível mais cedo que Arena da Vigília.
- Consentido.
- Pode permitir diferença extrema de nível, pois não oferece recompensa econômica significativa.
- Mostra nível/Classe do oponente antes de confirmar.
- Sem normalização.
- Após ambos os jogadores aceitarem validamente o Duelo, suas **Configurações de Combate são snapshotadas e travadas** até a resolução.
- Nenhum participante pode observar o adversário confirmado e então alterar Equipamentos, Runas, Encantamentos, Caminho, Talentos, Artes ou Doutrina.
- Troca de dispositivo, reconexão, `/start`, `/menu`, deep link ou mensagem antiga não removem o lock.
- O Duelo obedece integralmente às regras globais de atividade autoritativa e Configuração de Combate da seção 39.

### 14.3 Arena da Vigília (Ranked)

- Lançamento: **1v1**.
- Desbloqueio: **Nv.30 atual**.
- Pareamento prioriza MMR + nível próximo e expande gradualmente até limite configurável.
- Se Nv.30 × Nv.60 ficar ruim, primeiro ajuste é Pareamento/limites, não normalização.
- Existem **2 janelas diárias**: **12:00–13:00** e **19:00–20:00**, `America/Sao_Paulo`.
- Ao fechar a janela: novas entradas param; partidas já formadas continuam; fila não casada é liberada sem punição.
- A **Confirmação de Entrada** não revela o oponente até ambos aceitarem.
- Dodge/no-show repetidos usam Recarga em janela móvel de 60min: 1º sem penalidade, 2º **5min**, 3º **15min**, 4º+ **30min**.
- Estado competitivo começa limpo: HP cheio, Recargas prontas, sem buffs/debuffs/barreiras/DoTs externos; apenas Configuração de Combate válida e passivas permanentes.
- Ao terminar, o estado do mundo é restaurado; timers wall-clock externos continuam contando o tempo real.
- Sem consumíveis externos.
- Rendição = derrota normal e fica disponível a partir da **Rodada 5**.
- Recompensa por partida não deve gerar economia negociável ilimitada; foco em **Renome/MMR/histórico/marcos/cosméticos/prestígio**.
- Legado não reseta MMR, Renome ou histórico atual nem pausa decay.
- Para voltar à Arena da Vigília após Legado, precisa recuperar Nv.30 atual.
- A **Configuração de Combate fica travada a partir da entrada válida na fila competitiva** e permanece travada durante o fluxo correspondente até saída/cancelamento válido ou conclusão da partida.
- A revelação do adversário nunca abre janela de reconfiguração.
- Outro dispositivo não pode ser usado para trocar Doutrina, Equipamentos, Runas, Encantamentos, Artes, Talentos, Caminho ou outra parte da Configuração de Combate.
- Disconnect não pausa PvP; AFK continua; falha reconhecida do servidor é tratada separadamente.
- Morte simultânea = empate; MMR processa empate.
- Queue sniping/rematches recentes têm prioridade reduzida e pares suspeitos entram em antiboosting.
- Decay começa em **Arauto III (Renome ≥2.400)** após **7 dias** sem partida ranqueada; a cada segunda-feira 06:00 aplica `−50 Renome`, com floor 2.399.
- Snapshot, lock, callbacks e sincronização multidispositivo obedecem à seção 39 e à seção 44.

### 14.4 Elos da Arena da Vigília

A nomenclatura competitiva substitui tiers genéricos como Bronze/Prata/Ouro por Elos temáticos de Asterion.

Progressão oficial, do menor para o maior:

1. **Brasa III → Brasa II → Brasa I**.
2. **Chama III → Chama II → Chama I**.
3. **Forjado III → Forjado II → Forjado I**.
4. **Ascendente III → Ascendente II → Ascendente I**.
5. **Arauto III → Arauto II → Arauto I**.
6. **Regente** — elo máximo, sem divisões internas.

Regras:

- **Renome** é a apresentação de UI do PR/rating visível e determina a progressão exibida entre Elos conforme thresholds de Balanceamento.
- O **MMR permanece oculto** e pode divergir do Renome por razões de Pareamento e integridade competitiva.
- Limites de Renome por Elo/divisão, ganhos/perdas, placement e reset/soft reset entre Crônicas estão consolidados na seção 49.
- **Regente** é uma categoria especial de topo e não utiliza divisões III/II/I.
- A **Classificação da Vigília** registra a competição do ciclo e o **Salão da Vigília** preserva snapshots históricos/prestígio quando aplicável.

## 15. Batalha de Guildas (GvG)

- Termo oficial: **Guilda**.
- A Batalha de Guildas/GvG exige Nv.30 atual.
- Poder real, sem normalização.
- Duas frentes oficiais no lançamento: **Frente I 2v2** e **Frente II 3v3**; motor pode suportar 4v4 futuramente sem alterar a baseline.
- Cada frente vale 1 ponto; empate da frente = 0,5/0,5.
- Empate geral leva a **Campeão 1v1**.
- O Campeão é pré-registrado e pode ser alguém que já lutou numa frente.
- O Campeão começa com HP cheio/Recargas prontas/sem estados residuais, mantendo a **Configuração de Combate registrada**.
- Se o Campeão também empatar por morte simultânea, a Batalha de Guildas termina em empate.
- Um personagem só pode ocupar uma frente; o Campeão é a exceção posterior já descrita.
- A **Confirmação de Entrada registra e trava a Configuração de Combate completa** do personagem por toda sua participação válida na Batalha de Guildas.
- O lock abrange todas as partes descritas na seção 39 e não apenas a Doutrina salva.
- O mesmo snapshot permanece válido entre a Frente registrada e eventual participação posterior como Campeão.
- Outro dispositivo não pode alterar a configuração entre a Frente e o desempate.
- Roster fica travado antes da batalha; ações que invalidem elegibilidade são bloqueadas.
- No-show após registro/roster/pareamento gera derrota competitiva.
- A Batalha de Guildas possui rating técnico de Guilda para parear forças semelhantes, nunca normalização de poder.
- Número ímpar pode gerar bye rotativo: sem vitória/rating/recompensa, mas conta como participação de calendário quando aplicável.
- Ranking final pode exigir mínimo de batalhas reais, conforme a seção 49.
- Recompensas evitam snowball de poder.
- Snapshot, lock, callbacks e sincronização multidispositivo obedecem às regras globais das seções 39 e 44.

## 16. Legado

- Progressão: **Sem Legado → Legado I → II → III → IV → V**.
- Primeiro Legado exige **Nv.60 + campanha principal concluída**.
- Ascensão volta o nível para 1.
- Reprogressão recebe multiplicador de XP por Legado: **I 1,75×; II 2,00×; III 2,25×; IV 2,50×; V 2,75×**.
- Mantém: Classe, Caminho (Subclasse) escolhido, Provação, equipamentos, Inventário, Armazém, Coroas, Ofícios, Guilda, Mercado/Vínculos, mapa, Braseiros, Códice, Bestiário, Feitos, Títulos, cosméticos, decisões narrativas, Crônicas, segredos e Primeiras Conclusões/first-clears.
- Campanha não reinicia.
- Regiões de nível alto voltam a ter gate de entrada por nível, mesmo permanecendo conhecidas.
- Braseiros permanentes do mundo já descobertos continuam visíveis, mas viagem a Regiões altas respeita o nível atual. **Braseiros de Masmorra são estado temporário de run e nunca são preservados como destino ou descoberta permanente através do Legado.**
- Masmorras permanecem descobertas, porém o Caminho Conhecido respeita novamente os requisitos de nível/combate.
- Artes/Skills são lembradas, mas reativadas apenas nos níveis correspondentes.
- Talentos respeitam os pontos do nível atual.
- Missões Principais de alto nível ficam **Suspensas** enquanto o requisito de nível não estiver satisfeito e retornam automaticamente a **Em Andamento** quando o requisito retornar.
- Sistemas como Guilda, Mercado, Ofícios, Vínculos, Códice e Calendário permanecem desbloqueados após primeiro unlock.
- Legado só pode ser realizado em local seguro apropriado; após ascender, reaparece em hub/Braseiro válido para Nv.1.
- Ascensão é bloqueada em combate, Masmorra, fila, grupo incompatível, Batalha de Guildas/GvG ou roster travado.
- Equipamentos ilegais após redução de nível são desequipados com segurança.

### 16.1 Marcas de Legado

- 10 opções horizontais de QoL, escolher no máximo 5.
- Não concedem atributos de combate.
- Respec das Marcas de Legado ocorre em local seguro por **5.000 Coroas**, com **Recarga de 7 dias**; o custo é fixo para impedir redução artificial após Ascensão ao Nv.1.
- Não pode remover Marca se isso criaria estado inválido, como reduzir capacidade ocupada abaixo do uso atual.

## 17. Vigor

- Vigor Máximo: **100**; regeneração contínua total em **24h** (`+1` a cada **14m24s**); reset diário não reabastece Vigor.
- Vigor é **limitador econômico**, não bloqueador absoluto de gameplay.
- Com Vigor positivo, atividades repetíveis concedem economia normal.
- Em Vigor zero, conteúdo repetível pode continuar para história, missão, **Desbravar**, Bestiário, descoberta e XP reduzida quando apropriado, mas sem Coroas farmáveis, materiais negociáveis, equipamento negociável aleatório ou drops econômicos raros.
- **Desbravar não exige Vigor para ser iniciado.** Com Vigor zero, continua disponível para exploração, descoberta, história, Códice e Bestiário, respeitando a proibição de economia repetível definida nesta seção.
- Resultado repetível de Desbravar que conceda economia farmável deve consumir Vigor no momento da recompensa ou utilizar outro limite econômico explicitamente definido.
- Ronda de Caça só inicia/continua um encontro econômico quando possui Vigor suficiente para o custo integral; na baseline, **para quando o Vigor disponível é `<2`**.
- Custos fixos reservam o custo completo; não há consumo parcial de “resto” quando insuficiente.
- Fila não reserva Vigor; depois da Confirmação de Entrada, imediatamente antes de criar a run, reserva-se de forma atômica.
- Em Masmorras, o Vigor de cada participante é reservado imediatamente antes da criação válida da `run_id` e permanece reservado enquanto a run estiver ativa.
- Conclusão válida com recompensa econômica consome a reserva conforme as regras da atividade.
- Se a run terminar como **Masmorra Falhada por derrota total sem Braseiro de Masmorra ativo**, a reserva é **liberada integralmente**.
- Não existe consumo parcial de Vigor por essa falha; não há regra de perda de metade do Vigor.
- Falha não devolve Consumíveis realmente utilizados nem outros recursos legitimamente consumidos durante a run.
- Retry através de Braseiro de Masmorra ativo não encerra a run e, portanto, não libera nem consome naquele momento a reserva de Vigor.
- Falha/abandono válido sem recompensa libera a reserva quando aplicável; falha reconhecida do servidor nunca cobra.
- Em Caçada, Vigor é consumido quando o encontro concede recompensa econômica. Derrota/abandono sem recompensa não consomem, mas `encounter_id` persiste, impedindo reroll gratuito.
- Poções de Vigor não podem ultrapassar o cap; desperdício deve ser bloqueado/alertado.
- Recompensas únicas de história/Códice podem existir sem Vigor, preferencialmente vinculadas/limitadas.
- Toda atividade repetível que gera economia precisa ter Vigor **ou outro limitador explícito** de recompensa.

## 18. Caçadas, Ronda de Caça e Desbravar

### 18.1 Caçada Manual

- O jogador escolhe **Região → Local**; em uma Caçada normal, **não escolhe diretamente o inimigo**.
- Cada encontro é selecionado aleatoriamente entre os inimigos elegíveis do pool daquele Local.
- O pool pode usar pesos e condições de conteúdo para criaturas comuns, incomuns, elites, encontros especiais ou variações equivalentes.
- Uma vez criado, o encontro recebe `encounter_id` persistente. Abandono, reconexão ou repetição do mesmo fluxo não podem ser usados para rerrolar gratuitamente um inimigo indesejado.
- Missões, eventos ou encontros roteirizados podem forçar um alvo específico como **exceção explícita** à Caçada normal.
- Manual não recebe bônus de recompensa sobre Ronda de Caça.
- Pode ser Solo ou Grupo de até 4.
- Cada jogador possui Vigor e Saque/Recompensas individuais.
- Grupo não ignora requisitos individuais de acesso/progressão.
- Scaling de Caçada em Grupo é congelado no nascimento do `encounter_id` para aquele encontro.
- Em Solo, o `enemy_level` continua seguindo a regra regional/configurada da criatura. Em Grupo, define-se `encounter_reference_level = maior nível atual entre os participantes válidos` no nascimento do encontro; para uma criatura elegível, `enemy_level = min(encounter_reference_level, max_enemy_level_da_criatura)`, respeitando o unlock mínimo e os requisitos individuais de acesso/progressão. Uma entrada de pool com unlock individual explícito só é elegível quando todos os participantes do encontro satisfazem esse requisito. O nível resultante fica congelado no `encounter_id`.
- Novo membro só participa do próximo encontro; ninguém entra no meio do combate.
- Jogador derrotado em Grupo sai dos turnos; demais continuam. Wipe ocorre se todos forem derrotados.
- Derrotado pode receber recompensa se o Grupo vencer e ele teve contribuição válida.
- Após o encontro, derrotado retorna ao Braseiro e deve reagrupar-se antes do próximo.
- Reconnect grace existe quando aplicável.
- Solo PvE instanciado também possui reconnect grace; expirada a janela, resolve como abandono/falha.
- A criação/início válido do `encounter_id` adquire o lock da Configuração de Combate para aquele encontro.
- O lock permanece até vitória, derrota, abandono válido ou outra resolução oficial do encontro.
- Não é permitido sair visualmente do combate, alterar a Configuração de Combate e retornar ao mesmo `encounter_id`.
- Reconexão ou troca de dispositivo retoma o mesmo encontro e a mesma Configuração de Combate.
- Encontrar, enfrentar e derrotar criaturas elegíveis em Caçadas pode registrar Observação e progresso do **Bestiário** conforme a seção 33.1; progresso de conhecimento é separado da recompensa econômica.
- O mesmo `encounter_id`, reconnect ou callback repetido não registra novamente marcos únicos de conhecimento.

### 18.2 Ronda de Caça (Auto Hunt)

- Exclusivamente **Solo** no lançamento.
- Exige familiaridade/desbloqueio apropriado.
- Lotes oficiais da Ronda: **×5 / ×10 / ×20**, com cadência de **3 minutos por encontro** e custo de **2 Vigor por encontro economicamente recompensado**.
- Internamente resolve encontro por encontro.
- Cada novo encontro utiliza a mesma seleção do pool **Região → Local**, com novo sorteio válido e persistência própria de `encounter_id`.
- HP persiste entre encontros.
- Vigor é verificado/consumido encontro a encontro, não reservado para o lote inteiro.
- Level-up entre encontros passa a valer no próximo encontro.
- Cancelamento só ocorre entre encontros; encontros concluídos ficam válidos, os seguintes nunca começam.
- Elite, evento especial, Inventário/Pending impeditivo e **Vigor disponível inferior ao custo integral do próximo encontro econômico** continuam interrompendo a Ronda; na baseline, isso significa `<2 Vigor`.
- Não deve existir horas de farm offline; lote backend pode resolver de forma compacta, mas não é tarefa ociosa de várias horas.
- A cadência efetiva oficial da baseline é **3 minutos por encontro**, preservando o custo temporal usado na curva de progressão.

#### Configuração registrada da Ronda

Ao iniciar o lote:

- a Configuração de Combate atual é registrada e travada **durante todo o lote**, inclusive entre encontros;
- somente as até **3 Artes Ativas equipadas naquele momento** ficam disponíveis para a automação;
- Ataque Básico e Defender continuam disponíveis;
- a preparação de Consumíveis específica da Ronda é registrada;
- nenhuma alteração manual dessa configuração é permitida até o lote encerrar ou parar validamente.

A Ronda não pode:

- selecionar Arte aprendida que não esteja equipada;
- trocar Artes;
- trocar Doutrina;
- trocar Equipamentos;
- modificar Runas ou Encantamentos;
- trocar Caminho;
- redistribuir Talentos;
- buscar outra configuração do personagem em resposta ao inimigo encontrado.

Um level-up validamente consolidado entre encontros continua produzindo seus efeitos sistêmicos normais no encontro seguinte, mas não libera reconfiguração manual.

#### Execução automática do combate

Durante cada turno do personagem, o servidor determina automaticamente uma ação válida utilizando apenas os recursos autorizados para a Ronda.

O conjunto potencial inclui:

- Arte Ativa equipada e utilizável;
- Poção de Cura preparada e elegível;
- Consumível de Purificação preparado e elegível;
- Defender;
- Ataque Básico.

Toda ação automática passa pelo mesmo pipeline de validação de uma ação manual. Antes do commit, o backend valida conforme aplicável Arte equipada, Recarga, recursos/custos, condições, alvo, Consumível preparado, quantidade disponível e estado do personagem.

O commit permanece atômico. A automação não ignora Recarga, custos, resistência, condições de alvo ou qualquer outra regra de combate.

A lógica exata de prioridade entre Cura, Purificação, Defender, Artes e Ataque Básico está consolidada na seção 49, mas deve ser **determinística e autoritativa no servidor**. Qualquer desempate que exija RNG utiliza o RNG determinístico/idempotente do combate.

#### Poções de Cura e HP baixo

- Antes de iniciar o lote, o jogador pode preparar Poções de Cura elegíveis para uso automático.
- Somente Poções previamente preparadas para aquela Ronda podem ser utilizadas.
- O sistema não busca Poções no Armazém, Mercado, Pending ou outra origem; não compra, fabrica nem repõe Consumíveis sozinho.
- Usar Poção consome uma ação normalmente e a unidade é consumida no commit.
- Poção usada não é devolvida por derrota, cancelamento ou interrupção.
- A automação deve evitar desperdício evidente quando a cura não produzir benefício relevante.
- Limiar de HP e critérios exatos de uso estão consolidados na seção 49.
- A antiga regra de que “HP baixo interrompe a Ronda” é substituída: atingir o limiar de recuperação não interrompe imediatamente a Ronda quando existir recuperação automática válida.
- Enquanto houver Poção de Cura preparada, disponível e utilizável, a automação pode tentar a recuperação em uma oportunidade válida de ação.
- A Ronda é interrompida por HP baixo quando não houver Poção válida disponível, a Poção não puder ser usada ou, após as recuperações possíveis, o personagem continuar abaixo do limiar de segurança.
- Ao fim de cada encontro, antes de iniciar o próximo, o backend verifica o HP atual; se estiver abaixo do limiar de segurança, o próximo encontro não começa.
- Não existe uso gratuito de Poção entre encontros para evitar essa interrupção.
- Limiar de recuperação, limiar de segurança e critérios relacionados estão consolidados na seção 49.

#### Purificação automática

- A Ronda pode utilizar automaticamente Consumível de Purificação previamente preparado quando houver efeito negativo removível considerado relevante.
- O Consumível deve existir em quantidade válida e ser elegível naquele estado.
- Critérios de severidade, duração restante, impacto e prioridade em relação a Cura/Defender/Arte estão consolidados na seção 49.
- Purificação consome ação quando sua definição assim exigir e consome o item no commit.
- A automação não utiliza Purificação indiscriminadamente em qualquer debuff e não repõe itens automaticamente.

#### O que a Ronda nunca automatiza

A Ronda não utiliza automaticamente:

- Poções de Vigor;
- compra de Consumíveis;
- Crafting;
- retirada do Armazém;
- Mercado;
- Troca Direta;
- alteração de Equipamento;
- alteração de Runa;
- alteração de Encantamento;
- troca de Caminho;
- respec de Talentos;
- troca de Artes;
- aplicação de outra Doutrina.

Elite e evento especial continuam interrompendo a Ronda em vez de serem enfrentados silenciosamente pela automação.

#### Interrupção e multidispositivo

A Ronda pode parar por cancelamento voluntário entre encontros, HP abaixo do limiar de segurança sem recuperação válida, Elite, evento especial, Inventário/Pending impeditivo, **Vigor disponível inferior ao custo integral do próximo encontro econômico**, derrota ou outra condição explicitamente definida pelo conteúdo.

Ao interromper:

- encontros concluídos permanecem válidos;
- encontro não iniciado não é criado;
- Consumíveis já utilizados permanecem consumidos;
- a Configuração de Combate deixa de estar travada somente depois de persistido o encerramento válido do lote.

Trocar de dispositivo, abrir Telegram Desktop, usar `/start`, `/menu`, callback antigo ou outra mensagem não cria Ronda paralela, não altera a Configuração registrada, não repõe Consumíveis e não reinicia o lote. Outro dispositivo retoma/visualiza a mesma Ronda ativa conforme as regras globais da seção 39.

### 18.3 Desbravar — Exploração Ativa

#### Princípio

**Desbravar** representa a exploração ativa do **Local atual** do personagem.

Seu objetivo principal é descobrir novas camadas de Asterion — caminhos, lugares, conhecimento, segredos e acontecimentos — e não funcionar como substituto das Caçadas para combate repetível ou geração de economia.

Desbravar segue a filosofia:

> **“Poucas regiões. Muitos lugares. Muitas camadas.”**

O jogador explora mais profundamente um Local existente e pode revelar conteúdo conectado a ele.

#### Início da exploração

Para iniciar Desbravar:

- o personagem precisa estar em um Local conhecido e acessível;
- o Local atual precisa permitir exploração;
- o personagem não pode estar em atividade Foreground incompatível;
- requisitos narrativos, de nível, Campanha, Crônica ou estado de mundo continuam sendo respeitados.

Desbravar atua sobre o **Local atual**. Não existe exploração remota de outro Local no lançamento. Para Desbravar outro Local, o jogador deve chegar até ele pelas formas normais de deslocamento.

Desbravar é **Solo no lançamento**.

#### Tentativa de exploração

Ao iniciar Desbravar, o backend cria uma tentativa autoritativa de exploração com identificador próprio, como `exploration_attempt_id` ou equivalente.

A tentativa registra no mínimo personagem, servidor, Região, Local, contexto relevante, `ruleset_version`, resultado persistente e estado da tentativa.

- A seleção do resultado ocorre uma única vez.
- Reconexão, troca de dispositivo, callback repetido, mensagem antiga, restart do Bot ou reconstrução da interface não rerrolam o resultado.
- Enquanto uma tentativa estiver ativa/incompleta, o personagem não pode criar outra tentativa Foreground concorrente.

#### Pool de Exploração

Cada Local pode possuir seu próprio **pool de exploração**.

Os resultados elegíveis podem depender de Região, Local, nível, Campanha, Crônica, missões, descobertas anteriores, segredos conhecidos, `world_state`, `character_narrative_state`, estado de Evento Mundial e requisitos específicos de conteúdo.

Entre os tipos possíveis de resultado estão:

- descoberta de novo Local ou caminho;
- descoberta de Profundeza;
- descoberta de entrada de Masmorra;
- descoberta de Segredo;
- descoberta de Fratura;
- descoberta de Braseiro permanente do mundo;
- entrada ou progresso de Códice;
- progresso de Bestiário;
- indício ou observação de criatura;
- evento narrativo;
- rumor ou acontecimento contextual;
- pista de missão;
- interação relacionada à Campanha ou Crônica;
- encontro de combate;
- pequena descoberta de recurso;
- resultado atmosférico sem descoberta permanente;
- outros resultados explicitamente definidos pelo conteúdo.

Nem toda tentativa precisa produzir uma nova descoberta permanente.

#### Seleção, pesos e anti-reroll

- Resultados podem utilizar pesos, requisitos, condições de elegibilidade, prioridade contextual, exclusão de resultados já concluídos e regras anti-repetição.
- Chances, pesos, frequência de resultados e quantidade de conteúdo por Local estão consolidados na seção 49.
- Uma tentativa concluída não pode ter seu resultado rerrolado.
- Abandono, reconexão ou callback repetido não podem funcionar como mecanismo para rejeitar gratuitamente um resultado indesejado e sortear outro dentro da mesma tentativa.
- O sistema pode utilizar cadência, limites de tentativa, proteção contra repetição excessiva ou mecanismos equivalentes para impedir spam de exploração; valores quantitativos estão consolidados na seção 49.

#### Conteúdo oculto e Flavor Text

- Conteúdo não descoberto permanece **completamente ausente da interface**.
- Desbravar não exibe `???`, espaços reservados de segredo, nomes de Locais ocultos, entradas secretas de Masmorra, criaturas ocultas, Avesso, Segredos, transformações de Chefe, consequências narrativas futuras ou qualquer conteúdo ainda não descoberto.
- O backend pode considerar conteúdo oculto internamente no pool de elegibilidade sem revelar sua existência antes da descoberta válida.
- Desbravar é um dos sistemas em que Flavor Text Narrativo/Contextual pode ter maior presença, seguindo integralmente a seção 37.4.
- Flavor pode sugerir sinais, rastros, ruídos, rumores e mudanças ambientais sem nomear aquilo que o personagem ainda desconhece.
- Flavor não cria descoberta sozinho nem modifica estado.

#### Descobertas permanentes

Quando uma tentativa produz descoberta permanente válida, o backend registra essa descoberta de forma autoritativa e idempotente.

A mesma descoberta não pode ser concedida duas vezes por retry, callback duplicado ou concorrência.

Depois de registrada, ela passa a alimentar normalmente Mapa, Códice, Bestiário, Caminho Conhecido de Masmorras quando aplicável, Travessia dos Braseiros quando aplicável, Missões, Feitos e outros sistemas oficiais dependentes.

Para conhecimento:

- uma descoberta pode criar nova Entrada do **Códice** ou acrescentar Trecho a Entrada já conhecida; Desbravar não concede progresso genérico abstrato de Códice;
- pode registrar primeira observação, Habitat, comportamento, rastros, mecânica ou outra evidência de **Bestiário** sem exigir necessariamente abate;
- conteúdo ainda não descoberto permanece totalmente invisível;
- a mesma tentativa não pode conceder novamente o mesmo Trecho/marco por reconnect, callback ou recovery.

Desbravar pode revelar um Local conectado ao Local atual, mas a descoberta não ignora gates de acesso, não teleporta automaticamente o personagem e não ignora requisitos de nível, Campanha ou estado narrativo. Um Local pode ser conhecido e ainda não estar acessível.

#### Braseiros permanentes

Desbravar pode ser uma das formas orgânicas de descobrir **Braseiros permanentes do mundo**.

Quando encontrado validamente:

- a descoberta é registrada de forma idempotente;
- o Braseiro passa a aparecer conforme as regras do Mapa;
- pode integrar a Travessia dos Braseiros;
- todos os gates normais continuam sendo respeitados.

Essa regra não se aplica a **Braseiros de Masmorra**, que pertencem temporariamente à `run_id` e nunca entram na rede permanente de Travessia.

#### Combate encontrado ao Desbravar

Uma tentativa pode resultar em encontro PvE.

Nesse caso:

- o resultado não é descartado;
- é criado um `encounter_id`;
- Desbravar transita para combate mantendo a mesma atividade Foreground autoritativa;
- o combate utiliza as regras normais de PvE;
- Configuração de Combate fica travada pelas regras globais;
- reconectar ou trocar de dispositivo retoma o mesmo encontro;
- abandonar não permite rerrolar o resultado daquela tentativa.

Desbravar não utiliza obrigatoriamente o pool comum de Caçada; pode possuir encontros de exploração próprios.

Se o resultado exigir vitória, descoberta, recompensa, progresso ou missão são finalizados somente após resolução válida do combate conforme a definição daquele conteúdo.

Se o personagem for Derrotado:

- o encontro termina como derrota;
- a tentativa de Desbravar é encerrada como falha;
- não existe reroll do mesmo resultado;
- o personagem segue a recuperação normal de PvE através de Braseiro permanente válido;
- recompensas dependentes de vitória não são concedidas.

Descobertas explicitamente definidas como ocorrendo **antes do combate**, como observar uma criatura ao encontrá-la, podem permanecer registradas se o conteúdo assim definir.

#### Vigor e economia

- Desbravar **não exige Vigor para ser iniciado**.
- Pode ser utilizado em Vigor zero para exploração, história, descoberta, Códice, Bestiário, Segredos, progresso narrativo elegível e XP reduzida quando apropriado.
- Descobertas únicas podem conceder recompensas únicas controladas.
- Recompensas econômicas repetíveis são secundárias e não devem tornar Desbravar superior à Caçada como fonte de economia.
- Coroas farmáveis, materiais negociáveis, equipamento negociável aleatório e drops econômicos raros obedecem ao Vigor ou a outro limite explícito.
- Com Vigor zero, esses componentes econômicos repetíveis não são concedidos.
- Se um resultado repetível conceder economia usando Vigor, o consumo ocorre somente quando a recompensa econômica é efetivamente concedida.
- Eficiência econômica, chances, valores e tabelas estão consolidados na seção 49.

#### Conclusão e relação com outros sistemas

Uma tentativa de Desbravar termina quando seu resultado selecionado é resolvido: descoberta registrada, evento narrativo encerrado, resultado atmosférico concluído, recurso entregue, encontro vencido/perdido, abandono válido ou outro encerramento explícito.

A finalização é idempotente e uma tentativa já resolvida não conclui novamente por callback antigo, recovery ou repetição de request.

Desbravar pode ser objetivo de Missão, revelar Local necessário, disparar evento narrativo previamente definido ou avançar objetivo de exploração, mas não ignora requisitos da Campanha nem altera arbitrariamente `character_narrative_state`.

A Crônica pode adicionar resultados temporários aos pools, modificar Flavor, criar sinais/eventos ou utilizar Desbravar como objetivo, sempre filtrando progresso pessoal e sem reabrir capítulos, votações ou recompensas encerradas.

Desbravar pode revelar sinais/contexto de Evento Mundial, mas não cria nova ocorrência global nem duplica `occurrence_id`; participação e recompensa do Evento continuam seguindo suas regras próprias.

O pool pode consultar `world_state` e `character_narrative_state`. Sortear um resultado não modifica `world_state` por si só; qualquer mudança global/pessoal explícita usa transição oficial, versionada, condicional e idempotente.

## 19. Masmorras

- 1–4 jogadores; solo é suportado; sem papel obrigatório.
- Primeira descoberta é orgânica; após descobrir, **Caminho Conhecido** fica disponível, respeitando requisitos atuais.
- Masmorra secreta não aparece antes da descoberta.
- Dificuldades: **Estável**, **Fraturada**, **Ruptura**; Ruptura é normalmente Nv.60/endgame.
- Uma run pode possuir ou não **Braseiro de Masmorra**, conforme a seção 19.1.
- A ausência de Braseiro faz parte da pressão e do desgaste esperados da Masmorra, especialmente em Fraturada e Ruptura.
- Todos os membros precisam cumprir individualmente os requisitos e desbloqueios da Masmorra e da dificuldade selecionada.
- Convites e Pareamento de Masmorra obedecem à **Elegibilidade Preventiva** da seção 20.1; jogador inelegível não avança como opção válida no fluxo.
- Pareamento pode formar 2/3/4 e usa Confirmação de Entrada.
- Vigor é reservado por jogador imediatamente antes de criar a `run_id`; a criação coletiva é tudo-ou-nada.
- Scaling fica travado no tamanho inicial do Grupo durante toda a run; saída não reduz dificuldade.
- Sem reposição de membro no meio da run no lançamento.
- HP persiste entre encontros.
- Recargas, recursos combat-scoped e efeitos comuns resetam na fronteira de cada novo encontro.
- Somente efeitos `dungeon_persistent` atravessam encontros.
- Consumíveis normais não podem ser usados livremente entre encontros para contornar desgaste; o uso válido ocorre pelas ações e regras autorizadas do conteúdo.
- Em Masmorras, Consumíveis elegíveis presentes no **Inventário** do personagem ficam disponíveis sem preparação prévia, respeitando o **limite de usos por jogador e por `run_id`** definido para aquela Masmorra/dificuldade.
- O limite de Consumíveis de Masmorra **não reinicia entre encontros, após wipe, Retry ou Braseiro de Masmorra**. Ter unidades adicionais no Inventário não aumenta esse limite.
- O valor exato do limite pode variar por Masmorra/dificuldade e está consolidado na seção 49; conteúdos mais longos ou de dificuldade distinta podem receber orçamento próprio de usos sem alterar a regra estrutural por run.
- Quando o jogador atingir o limite de usos da run, novas ações de Consumível ficam inválidas pelo restante daquela `run_id`, mesmo que ainda existam unidades no Inventário.
- Na criação válida da run, a **Configuração de Combate de cada participante é snapshotada e travada durante toda a run**, inclusive entre encontros.
- O lock inclui Equipamentos, Runas, Encantamentos, Caminho, Talentos e Artes conforme a seção 39. Consumíveis do PvE manual não são uma escolha preparada da Configuração de Combate; a run registra e controla apenas suas regras, limite e contador de usos aplicáveis.
- Checkpoint técnico/Braseiro de Masmorra não libera automaticamente a Configuração de Combate.
- Retry não libera a Configuração de Combate.
- A única exceção é ponto de reconfiguração explicitamente projetado pela própria Masmorra. Nesse caso, a mudança é executada pelo backend dentro da run e um novo snapshot válido substitui o anterior de forma atômica.
- Sair da mensagem, navegar por outra tela, reconectar ou trocar de dispositivo não equivale a sair da run; `/start` e retomadas reconstroem o contexto da `run_id` vigente.

### 19.1 Derrota, Braseiro de Masmorra e Retry

#### Braseiro de Masmorra

Quando uma Masmorra possuir checkpoint técnico durante uma run, ele é apresentado ao jogador como um **Braseiro de Masmorra com nome próprio**, nunca como “checkpoint”.

- Cada Masmorra possui previamente um nome temático aprovado para seu possível Braseiro, coerente com região, história, atmosfera ou identidade.
- O nome não é gerado proceduralmente durante a run.
- Exemplo conceitual: **Cripta do Ocaso → Braseiro do Silêncio**.
- O termo `checkpoint` pode permanecer apenas como nomenclatura técnica/backend.
- Na apresentação player-facing, o título e seu Flavor Text permanecem visualmente juntos, sem linha vazia entre eles.

#### Geração por run

A existência do Braseiro não é garantida.

Probabilidades definitivas da baseline v1.0:

- **Estável:** **70%**;
- **Fraturada:** **40%**;
- **Ruptura:** **20%**.

A dificuldade é o principal modificador padrão no lançamento. Não existe fórmula automática adicional por nível/tier. Conteúdo específico pode futuramente possuir override explícito quando houver justificativa de design.

- A existência ou ausência do Braseiro é determinada autoritativamente quando a `run_id` é criada e permanece fixa durante toda a run.
- Reconnect, troca de dispositivo, atualização de mensagem, Retry, restart do Bot ou recovery da mesma `run_id` não realizam novo sorteio.
- O jogador não precisa ser informado na entrada se aquela run possui Braseiro; a descoberta é orgânica durante a progressão.
- A determinação utiliza RNG autoritativo e persistido/idempotente para a tentativa.
- O backend deve impedir **reroll gratuito** da disponibilidade do Braseiro por abandono, falha, reconnect ou recriação artificial de fluxo. O mecanismo técnico pode utilizar seed/registro persistente de tentativa ou equivalente, sem inventar um novo custo/cooldown de gameplay apenas para isso.
- Falha reconhecida do servidor ou recovery legítimo nunca gera nova disponibilidade.

#### Ativação

Quando a run possuir Braseiro e o grupo alcançá-lo validamente:

- ele se torna o checkpoint técnico ativo da `run_id`;
- personagens Derrotados são recuperados fora de combate;
- o grupo é restaurado para **100% do HP**;
- o Braseiro passa a ser o ponto oficial de Retry da run.

A ativação normal ocorre uma vez. Retornar fisicamente ao Braseiro não restaura HP repetidamente e não permite cura infinita por backtracking.

O Braseiro não restaura Vigor, Consumíveis usados, tentativas/limites externos ou outros recursos não explicitamente pertencentes à sua função.

#### Derrota individual

- Personagem Derrotado deixa de participar dos combates seguintes daquela run.
- Pode voltar quando um Braseiro de Masmorra válido for alcançado e ativado, quando ocorrer Retry válido através de Braseiro já ativo ou por outra regra explícita da própria Masmorra fora de combate.
- Não existe ressurreição comum durante combate.
- Se a run não possuir Braseiro, um personagem Derrotado permanece fora dos combates restantes, salvo regra específica do conteúdo, podendo ainda seguir as regras normais de contribuição/elegibilidade se o grupo concluir validamente.

#### Derrota total sem Braseiro ativo

Se **todos os participantes forem Derrotados** e não existir Braseiro de Masmorra ativo naquela `run_id`:

- a run é encerrada imediatamente como **Masmorra Falhada**;
- não existe Retry a partir da entrada da Masmorra;
- não existe reinício gratuito daquela mesma run;
- a reserva de Vigor é **liberada integralmente**;
- não existe consumo parcial de Vigor;
- Consumíveis realmente utilizados permanecem consumidos;
- recompensas econômicas provisórias dependentes de conclusão válida são descartadas;
- progresso/recompensa repetível provisório é resolvido conforme as regras de finalização de falha;
- conhecimento, lore ou descoberta única explicitamente persistente após tentativa fracassada continua preservado;
- o encerramento é autoritativo, atômico e idempotente.

A mesma regra vale quando a run possui um Braseiro, mas o grupo sofre derrota total **antes de alcançá-lo e ativá-lo**. A existência física de um Braseiro ainda não ativado não concede direito a Retry.

#### Derrota total com Braseiro ativo

Se todos forem Derrotados depois que um Braseiro foi ativado validamente:

- a run permanece ativa;
- o grupo retorna ao Braseiro ativo pelo Retry oficial;
- personagens Derrotados são recuperados;
- o grupo retorna com 100% do HP;
- Consumíveis realmente utilizados permanecem consumidos;
- o Chefe/encontro correspondente reinicia integralmente quando aplicável;
- a Configuração de Combate continua obedecendo ao lock da run;
- a reserva de Vigor continua reservada;
- a existência do Braseiro não é novamente sorteada;
- Retry nunca cria nova `run_id`.

Recompensas/progresso de encontros já registrados continuam protegidos por `run_id + encounter_id` e não podem ser obtidos novamente através de Retry.

#### Run sem Braseiro enquanto o grupo permanece vivo

A ausência de Braseiro não altera a progressão normal da Masmorra. O grupo continua atravessando encontros, mecânicas, exploração interna e Chefe até concluir ou sofrer derrota total.

Não apresentar ao jogador qualquer aviso de que a run não possui Braseiro.

### 19.2 Recompensas, Saque e finalização

- Saque, XP econômico e progresso repetível podem permanecer provisórios até conclusão válida quando apropriado.
- Cada encontro concede recompensa/progresso elegível no máximo uma vez por `run_id + encounter_id`.
- Retry nunca transforma encontro já registrado em nova fonte de recompensa.
- Mecânicas internas como chaves/cristais pertencem ao estado da run, não ao Inventário econômico.
- Saque provisório não pode ser equipado, usado, negociado ou desmontado antes de sua finalização.
- Ao marcar `run=completed`, recompensas conquistadas finalizam automaticamente; não dependem de botão “Coletar”. A reserva de Vigor é consumida conforme as regras da atividade.
- Ao marcar `run=failed` por derrota total sem Braseiro ativo, a reserva de Vigor é liberada integralmente e recompensas econômicas provisórias dependentes de conclusão são descartadas.
- Nenhum componente descartado pode ser posteriormente reivindicado por callback, mensagem antiga ou Retry.
- Conhecimento/lore/descobertas explicitamente persistentes após tentativa fracassada continuam seguindo suas regras próprias.
- Criaturas, Elites e Chefes encontrados em Masmorras podem conceder progresso do Bestiário quando a condição correspondente ocorrer; Retry não repete marcos únicos já registrados.
- Masmorras, Segredos internos, acontecimentos e Chefes podem criar/atualizar Entradas ou Trechos do Códice em marcos explicitamente definidos. Conhecimento que exija vitória/conclusão só é concedido depois dessa condição.
- Consumíveis utilizados durante uma run Falhada não são restaurados.
- Se a run possuir Braseiro ativo e entrar em Retry, ela ainda não está finalizada; recompensas permanecem vinculadas à run vigente.
- Finalização de conclusão ou falha é idempotente: repetir job, callback, recovery ou processamento não duplica recompensa, consumo/liberação de Vigor ou devolução de recurso.
- Se Inventário + Pending não comportarem recompensa final legitimamente conquistada, aplicam-se as regras normais de Entrega Pendente.
- Run expira após **4h de inatividade** ou **24h absolutas**; encerramento resolve reservas e descarta somente recompensa provisória não conquistada.
- Líder social não é dono técnico da `run_id`; saída transfere liderança sem destruir a instância.

## 20. Grupo e Contribuição

### 20.1 Elegibilidade Preventiva para Convites e Pareamento

Atividades de Grupo com requisitos individuais, especialmente **Masmorras**, aplicam verificação preventiva de elegibilidade antes de permitir que um personagem avance pelo fluxo de convite ou Pareamento.

Para uma atividade e configuração específicas — incluindo, quando aplicável, a dificuldade selecionada — o sistema deve avaliar a elegibilidade individual de cada personagem antes de apresentá-lo como opção válida ou permitir sua entrada em fila.

A elegibilidade considera todos os requisitos individuais definidos para aquela atividade, incluindo quando aplicável:

- nível mínimo;
- desbloqueio da atividade ou Masmorra;
- desbloqueio da dificuldade selecionada;
- requisitos de progressão;
- requisitos de acesso;
- outros requisitos individuais explicitamente definidos pelo conteúdo ou sistema correspondente.

Regras de fluxo:

- personagem inelegível **não aparece como opção válida** na lista de convite para aquela atividade/configuração;
- personagem inelegível **não pode entrar no Pareamento** correspondente;
- a filtragem preventiva reduz fluxos inválidos, mas **não substitui validações autoritativas posteriores**;
- a elegibilidade é obrigatoriamente revalidada no **aceite do convite**;
- quando houver **Confirmação de Entrada**, a elegibilidade é novamente revalidada nessa etapa;
- imediatamente antes da reserva de Vigor ou de qualquer outro recurso e antes da criação da `run_id`, todos os participantes são revalidados novamente;
- se um personagem se tornar inelegível depois de já ter entrado no fluxo por mudança de estado, configuração ou requisito aplicável, ele não pode participar da criação da run enquanto a condição permanecer inválida;
- tentativa inválida **não cria `run_id`, não reserva Vigor e não consome recursos**;
- quando a elegibilidade mudar depois da entrada no fluxo, o personagem afetado recebe explicação contextual do motivo da invalidação, sem revelar informação protegida ou conteúdo ainda não descoberto.

A criação coletiva de uma atividade continua obedecendo às regras transacionais próprias do conteúdo. Em Masmorras, a revalidação final ocorre antes da reserva atômica de Vigor e da criação válida da `run_id`.

Exemplo autoritativo: se uma Masmorra/dificuldade exigir **Nv. 8**, um personagem **Nv. 7** não aparece como opção válida de convite para esse contexto e não consegue entrar na fila de Pareamento correspondente.

### 20.2 Contribuição de Grupo

- Loot de Grupo é individual.
- Líder não controla loot.
- Escolhas narrativas permanentes são individuais.
- Decisões operacionais da run podem usar votação; empate pode ser decidido pelo Líder social salvo regra própria do conteúdo.
- Contribuição considera dano, Cura efetiva, Barreira efetivamente absorvida, mitigação real, debuffs úteis, mecânicas, ações válidas e presença.
- Nunca é apenas DPS.
- Overheal ou spam sem impacto não contam integralmente.
- AFK/leech não recebe crédito automático.
- Crédito de missão em Grupo exige presença e participação adequadas à natureza do objetivo.
- Líder não pode gastar Vigor, tentativa ou lockout dos demais sem ready check/consentimento individual.
- Se Líder sair, liderança transfere para outro membro ativo elegível.

## 21. Eventos Públicos e Sintonização do Véu

- Evento Mundial usa `event_id + occurrence_id`; restart/deploy não cria duplicata da mesma ocorrência.
- Scaling é congelado por fase, não recalculado continuamente com entradas/saídas.
- Nova fase pode recalcular participantes válidos sem restaurar vida já perdida.
- Recompensa exige participação/contribuição substancial; “dar um hit e ir embora” não basta.
- Contribuição é registrada por `occurrence_id + character_id` e não duplica ao reentrar.
- Derrota permite reentrada após **2 minutos** quando o Evento autoriza; a participação continua a mesma.
- Evento sem participantes termina/expira conforme deadline; não fica eterno.
- Chefe compartilhado/global usa HP atômico; morre uma vez. Ao confirmar morte global, instâncias ativas sincronizam e não aceitam dano pós-morte.
- Overkill de uma forma de Chefe não passa automaticamente para uma nova forma com nova barra de HP, salvo regra explícita.
- Ao assumir participação combatente válida em uma ocorrência, o personagem registra uma **Configuração de Combate** para aquela participação.
- Durante fases/etapas contínuas da mesma participação, a configuração não pode ser alterada oportunisticamente; mudança de fase não libera o lock automaticamente.
- Se o conteúdo permitir reentrada após derrota, o direito de reentrada mantém a mesma Configuração registrada.
- Se o jogador encerrar definitivamente sua participação para liberar o lock, também encerra seu direito de reentrada naquela ocorrência, salvo exceção explícita do Evento.
- Um Evento pode possuir ponto explícito de reconfiguração quando isso fizer parte de seu design.
- Uma ocorrência pode acrescentar conhecimento ao **Códice** quando possuir consequência ou descoberta narrativa explicitamente definida; esse registro é separado de participação, contribuição e recompensa econômica da ocorrência.

### 21.1 Sintonização do Véu

- Existe apenas em conteúdos PvE compartilhados explicitamente marcados, principalmente Calamidades/Ecos de regiões inferiores.
- Não afeta Caçadas normais, Masmorras normais, Desbravar normal, Arena da Vigília, Duelo ou Batalha de Guildas.
- Reduz orçamento numérico do veterano sem apagar identidade de Doutrina/Artes.
- Não melhora a tabela econômica do evento antigo.
- Contribuição usa valores já sintonizados.
- A Sintonização modifica o orçamento numérico autorizado pelo conteúdo, mas **não constitui troca de Configuração de Combate** e não libera seu lock.

## 22. Juramento e Expedição

### 22.1 Juramento

#### Estrutura do ciclo

- O Juramento é uma atividade cooperativa periódica da Guilda.
- Possui janela de ativação de **48h**, de sexta 18:00 a domingo 18:00.
- Durante a janela, membros elegíveis podem realizar **Provações**.
- **Provação** é o termo player-facing para cada tentativa individual do Juramento; backend pode manter `attempt`/tentativa.
- Grupos possuem até 4 participantes.
- Cada Provação começa com HP cheio, Recargas prontas e sem efeitos residuais.
- Quantidade de Provações disponíveis por ciclo, limites de contribuição e demais valores estão consolidados na seção 49.

#### Início e consumo da Provação

Cada Provação recebe `attempt_id` próprio ou identificador equivalente.

O início válido:

- revalida participantes e Guilda;
- revalida disponibilidade de Provação no ciclo;
- registra o grupo e `guild_id + cycle_id`;
- registra/trava a Configuração de Combate de cada participante;
- consome uma Provação disponível de cada participante após o commit válido de início.

Uma Provação validamente iniciada é consumida mesmo que termine posteriormente em derrota, abandono ou falha causada pelos jogadores.

Falha reconhecida do servidor ou fluxo que não chegou ao commit válido de início não consome Provação. Reconexão/troca de dispositivo retomam a mesma Provação e não criam tentativa nova.

#### Configuração de Combate

Cada Provação possui lock próprio de Configuração de Combate durante toda a tentativa, incluindo múltiplas etapas internas quando existirem.

Após resolução válida, o lock é liberado e o personagem pode preparar outra Configuração antes de nova Provação, desde que continue elegível e possua tentativa disponível. As regras globais das seções 39 e 44 continuam aplicáveis.

#### Contribuição

A contribuição do Juramento representa **progresso efetivamente conquistado através de objetivos, etapas e marcos válidos da Provação**. Não corresponde simplesmente a dano causado, número de turnos, presença passiva ou entrada na atividade.

Cada objetivo/marco elegível possui registro autoritativo e idempotente.

Uma Provação pode produzir:

- **contribuição coletiva**, aplicada uma única vez ao progresso do Juramento daquela Guilda;
- **registro de contribuição individual**, associado aos participantes que cumpriram os requisitos de participação válida.

A contribuição coletiva de uma mesma Provação não é multiplicada pelo número de integrantes do grupo. A contribuição individual serve para determinar elegibilidade pessoal às recompensas do ciclo. Critérios, pesos, limites e thresholds estão consolidados na seção 49.

#### Falha e contribuição parcial

Uma Provação não precisa ser concluída integralmente para registrar contribuição.

Se objetivos ou marcos elegíveis já foram concluídos e commitados antes da falha:

- essa contribuição permanece válida;
- a falha posterior não a remove.

Objetivos não concluídos não concedem contribuição parcial apenas por dano/progresso incompleto, salvo quando o próprio objetivo possuir etapas explicitamente registráveis.

Conclusão integral pode possuir contribuição adicional própria; valores estão consolidados na seção 49.

Derrota ou abandono depois do início válido consomem a Provação normalmente.

#### Resultado coletivo

Durante o ciclo, a Guilda acumula contribuição pelas Provações válidas de seus membros vinculados ao ciclo.

O Juramento utiliza **faixas de resultado coletivo** determinadas pela contribuição total validada. Quantidade de faixas, thresholds e recompensas estão consolidados na seção 49.

A Guilda recebe a maior faixa alcançada ao final do ciclo. Não existe necessidade de sucesso/falha binário além do caso em que nenhuma faixa mínima tenha sido alcançada.

Atingir uma faixa não consome contribuição nem impede continuar avançando enquanto a janela estiver aberta.

#### Elegibilidade individual

Pertencer a uma Guilda que alcançou uma faixa não concede automaticamente recompensa individual.

Para ser elegível, o personagem precisa:

- possuir vínculo válido com aquela Guilda e aquele ciclo;
- ter realizado ao menos uma Provação validamente iniciada;
- atingir o requisito individual de contribuição do ciclo, conforme a seção 49;
- não estar invalidado por fraude/exploit/regra administrativa aplicável.

Não é obrigatório concluir integralmente uma Provação se a contribuição parcial legitimamente registrada for suficiente. Elegibilidade é snapshotada de forma autoritativa.

#### Encerramento da janela

Quando o deadline é alcançado:

- novas Provações não podem ser iniciadas;
- Provações já validamente iniciadas podem concluir dentro de **30 minutos de grace period**;
- após a grace period, tentativas ainda abertas são finalizadas conforme o estado válido existente;
- somente contribuição legitimamente commitada permanece.

Depois de resolvidas as tentativas pendentes, o ciclo entra em **finalização**.

A finalização:

- congela a contribuição coletiva;
- determina a maior faixa alcançada;
- congela snapshots individuais de elegibilidade;
- cria os direitos de recompensa;
- marca o ciclo como encerrado.

A finalização é autoritativa e idempotente. Depois dela não é possível acrescentar contribuição, iniciar Provação ou alterar retroativamente a faixa alcançada.

#### Recompensas

O Juramento pode conceder **recompensa coletiva da Guilda e recompensa individual aos participantes elegíveis**.

A recompensa coletiva depende da faixa final alcançada e pertence à Guilda. A recompensa individual depende da faixa coletiva e só existe para personagens que atingiram elegibilidade individual.

Conteúdo, quantidade e progressão das recompensas estão consolidados na seção 49.

Nenhuma recompensa pode ser duplicada por callback, claim repetido, job repetido, reconnect ou troca de dispositivo.

Na finalização, cada direito legitimamente conquistado recebe registro autoritativo/idempotente, como `reward_grant` ou equivalente, com chave adequada incluindo `cycle_id`, `guild_id`, personagem quando aplicável e tipo de recompensa.

A interface pode utilizar entrega automática ou ação de **Resgatar**. Se houver claim manual, múltiplos cliques não duplicam entrega; falta de espaço utiliza Entrega Pendente quando aplicável.

#### Participante sem elegibilidade

Personagem que realizou Provações, mas não atingiu o requisito individual:

- mantém sua contribuição legitimamente registrada para a Guilda;
- não recebe a recompensa individual daquele ciclo;
- pode visualizar que participou, mas não alcançou elegibilidade.

Não existe recompensa parcial implícita apenas por participação, salvo recompensa explicitamente definida pelo Conteúdo.

Personagem que não realizou nenhuma Provação válida não possui contribuição individual, não é elegível à recompensa individual e pode apenas visualizar o resultado coletivo da Guilda.

#### Proteção contra guild hopping

A primeira Provação validamente iniciada pelo personagem em determinado ciclo cria seu vínculo de Juramento com `guild_id + cycle_id`.

Contribuição permanece pertencendo à Guilda vinculada naquele ciclo.

Sair ou ser expulso:

- não remove contribuição já registrada;
- não transfere contribuição para outra Guilda;
- não permite contribuir novamente para o Juramento de outra Guilda no mesmo ciclo;
- não cria direito a uma segunda recompensa do Juramento.

Se o personagem já conquistou legitimamente um direito de recompensa e ele foi snapshotado, saída/expulsão posterior não apaga esse direito.

Entrar em outra Guilda no mesmo ciclo não altera o vínculo anterior do Juramento; participação no Juramento da nova Guilda só volta a ser possível no ciclo seguinte. Essa limitação é específica do Juramento e não impede associação à nova Guilda quando as regras gerais permitirem.

### 22.2 Expedição assíncrona

- Duração oficial da Expedição: **72 horas**, de segunda-feira 18:00 a quinta-feira 18:00.
- É **Background Commitment**, não prende o personagem em Foreground.
- Possui `expedition_id`, roster congelado, rota, estágio, escolhas, deadline e reward state.
- Personagem continua jogando normalmente durante a Expedição.
- Escolhas têm janela; ausência de resposta usa default pré-definido.
- Não fica eternamente aguardando voto.
- Recompensas usam elegibilidade individual + resultado coletivo.
- Sair da Guilda depois do início não apaga retroativamente o histórico registrado; política de reward segue snapshot/ciclo.
- A Expedição, por ser Background, **não trava Configuração de Combate apenas por estar ativa**; qualquer combate Foreground iniciado durante ela segue suas próprias regras de lock.

## 23. Inventário, Armazém e Entregas Pendentes

- Capacidades: **Inventário 60 / Armazém 100 / Entregas Pendentes 20**.
- Favorito ⭐ e Locked 🔒.
- Locked não pode ser vendido, desmontado, consumido, negociado ou usado em operação incompatível até desbloquear.
- Mítico exige dupla confirmação em ações destrutivas/Trade/Mercado.
- Stacks: **Materiais 999 / Consumíveis 99**; Runas idênticas podem stackar quando todas as propriedades econômicas coincidirem.
- Stacks só fundem se todas as propriedades econômicas relevantes forem iguais, inclusive bind.
- Split/merge conserva quantidade exatamente e é transacional.

### 23.1 Armazém

- Acessível apenas em locais seguros apropriados.
- Item no Armazém não equipa, usa, Trade ou Mercado diretamente; primeiro precisa ir ao Inventário.
- Doutrina/Build com item no Armazém aparece incompleta.
- Crafting em contexto seguro pode consumir materiais do Inventário + Armazém, com preview exato dos stacks.

### 23.2 Entregas Pendentes

- Backend unifica Pending de Loot, Mercado, Crafting, Serviço e Recompensa, registrando origem.
- Itens Pending não podem ser equipados, usados, craftados, desmontados, negociados ou enviados voluntariamente para lá.
- Pode bloquear novas atividades geradoras de item até o jogador liberar espaço.
- Market Return e Resultado Pendente são estados de entrega, não Armazém alternativo.
- Compra/Trade voluntários exigem destino final válido; não usam Pending de propósito.

## 24. Equipamentos — slots e regras oficiais

### 24.1 Slots

Total: **8 slots**.

1. **Arma Principal**.
2. **Arma Secundária**.
3. **Cabeça**.
4. **Torso**.
5. **Mãos**.
6. **Pés**.
7. **Acessório**.
8. **Artefato**.

Não existem dois slots separados de anel no modelo atual. Há apenas **1 Acessório**.

### 24.2 Nível, categorias, armas e raridades

- Todo Equipamento possui `item_level` e exige **nível do personagem ≥ item_level** para ser equipado. Na baseline, `required_level = item_level`; não existe um segundo requisito numérico de nível separado.
- Um personagem pode possuir, receber, armazenar, negociar ou manter no Inventário/Armazém um Equipamento acima do próprio nível, respeitando bind e demais regras econômicas; apenas a ação de equipar é bloqueada até o requisito ser satisfeito.
- Após Legado ou qualquer redução válida de nível, Equipamentos cujo `item_level` exceda o nível atual tornam-se inelegíveis e são desequipados com segurança pelas regras centrais já vigentes; não são destruídos nem rebaixados.
- As categorias mecânicas de Equipamento no lançamento são os **8 slots oficiais** e a regra especial de **Arma 2H**. Não existe sistema mecânico global de armadura **leve / média / pesada**.
- Não existe **Peso físico, carga máxima ou equip load**. O termo técnico `SlotWeight` usado nas fórmulas da seção 49 representa apenas peso de orçamento/custo do slot e nunca carga carregada pelo personagem.
- Armas podem possuir um **subtipo/forma descritiva opcional** — por exemplo espada, machado, adaga, arco, besta, cajado ou equivalente definido por Conteúdo — para nome, lore, pixel art e apresentação. Esse subtipo não concede atributo, fórmula, proficiência, penalidade, restrição de Classe/Caminho ou regra de combate automaticamente.
- Peças de Cabeça/Torso/Mãos/Pés também podem receber descrição visual/material temática, mas isso não cria classe mecânica de armadura.
- Qualquer restrição de Classe/Caminho, proficiência ou requisito especial só existe quando declarada explicitamente pela definição do item e validada pelo Equipment Validator; não é inferida pelo subtipo visual.
- Arma de 2 mãos ocupa Arma Principal e bloqueia Arma Secundária.
- O item anterior de Off-hand precisa ser movido validamente ao Inventário na mesma transação; não fica oculto equipado.
- Raridades: **Comum, Raro, Épico, Lendário, Mítico**.
- Máximo de **1 equipamento Mítico equipado**.
- Upgrade: **+0 a +10**, garantido; sem falha, destruição ou downgrade.
- Crescimento por Aprimoramento é garantido e usa os multiplicadores oficiais da seção 49, chegando a **1,25× no +10**.
- Sem durabilidade.
- Sem Aparências cosméticas de armas ou equipamentos no lançamento.

### 24.3 Secundários, Reroll e Bind

- Pode existir reroll de um secundário escolhido; depois de selecionar, só aquele secundário pode ser rerrolado.
- No reroll, a nova identidade é selecionada entre secundários compatíveis do slot que não dupliquem os demais secundários existentes; na ausência de peso explícito, a seleção é uniforme. Se não existir candidato legal, o reroll não pode ser comprometido.
- A magnitude não preserva o número literal do atributo anterior: ela é **recalculada deterministicamente para a nova identidade usando o mesmo share de budget secundário da instância**, pelas fórmulas oficiais.
- Se patch remove esse secundário, migração mapeia equivalente ou libera nova seleção sem punir o jogador.
- Maioria dos equipamentos é Negociável; alguns usam Bind-on-Equip ou Bind-on-Acquire.
- Doutrina que equipa item Bind-on-Equip pela primeira vez precisa de confirmação agregada; se vários itens serão vinculados, uma única tela lista todos.
- Item com componente removível vinculado não pode ser negociado enquanto o componente estiver instalado.
- Ao extrair, equipamento recupera sua negociabilidade original e componente preserva o próprio bind.
- Componente permanente vinculado pode tornar o equipamento permanentemente vinculado conforme sua definição.

### 24.4 Mudança de HP por equipamento

- Fora de combate, alteração de HP Máximo preserva a porcentagem atual.
- Personagem vivo nunca cai abaixo de 1 HP apenas por recalcular equipamento: `max(1, floor(percentual × novo HP Máximo))`.
- Personagem já Derrotado continua em 0.

### 24.5 Equipment Validator

Toda mudança de equipamento passa pelo mesmo validador central: slot, nível, Classe/Subclasse, 2H/off-hand, máximo de Mítico, bind, componentes, estado do item, requisito especial e capacidade final do Inventário.

Trocas de Doutrina/equipamento são atômicas: simula-se o estado final completo; se válido, aplica tudo; se inválido, nada muda.

### 24.6 Materialização global de Equipamento

- `item_level` é **imutável durante a vida da `item_instance`**. Aprimoramento, Reroll, Runa, Encantamento, Trade, Bind, Legado ou mudança de proprietário não alteram `item_level` nem `required_level`.
- O Grau do Equipamento é derivado somente do `item_level`: `1–10=I`, `11–20=II`, `21–30=III`, `31–40=IV`, `41–50=V`, `51–60=VI`. Implementações devem usar uma função central equivalente a `equipment_grade(item_level)`.
- Toda origem que cria Equipamento — Saque, Crafting, recompensa de Campanha, Receita especial ou outra fonte — utiliza o mesmo **materializador de `item_instance`**. A origem fornece ou resolve, antes do commit, pelo menos: `template_id`, raridade, `item_level`, política de bind e uma identidade/seed determinística de materialização.
- A raridade determina a quantidade de secundários: Comum `0`, Raro `1`, Épico `2`, Lendário `3`, Mítico `4`.
- Secundários são selecionados no pool compatível do slot **uniformemente por padrão, sem reposição e sem duplicação**. Conteúdo pode declarar pesos explícitos; Classe, Caminho, build atual ou necessidade percebida do personagem nunca funcionam como smart loot implícito.
- Para os secundários do próprio Equipamento, Arma 2H utiliza o pool de **Principal**. A afinidade Principal/Secundária permanece regra das duas Runas da 2H, não cria pool híbrido de secundários do Equipamento.
- Um template só é elegível para uma raridade quando seu pool permitir selecionar a quantidade exigida de secundários distintos, salvo exceção explícita do próprio template. Na baseline atual, Torso possui apenas `HP / DEF / Bloqueio`; portanto **Torso Mítico genérico é inelegível** enquanto Mítico exigir quatro secundários distintos e esse pool permanecer com três identidades.
- Depois de resolver secundários, o materializador calcula núcleo/base, budget de raridade e magnitudes exclusivamente pelas fórmulas globais vigentes. Não existe roll adicional de potência fora dessas fórmulas.
- Equipamento nasce `+0`, sem Runa instalada e sem Encantamento, salvo quando a fonte declarar explicitamente outro estado inicial. Bind é fornecido pela fonte/template: Campanha preserva seu Bind-on-Acquire, Crafting deriva a restrição pelas regras de materiais/receita, e Saque genérico usa a regra da seção 49.9.
- A `item_instance` completa é persistida antes da apresentação/entrega. Reconnect, callback duplicado, retry, recovery ou troca de dispositivo recuperam a instância existente e nunca rerrolam template, secundários, valores ou bind.

## 25. Runas e Encantamentos

### 25.1 Runas

- Runa é componente inserido/removível.
- Identidade e bind da Runa são preservados ao inserir/extrair.
- Extração exige espaço válido no Inventário antes do commit.
- Se não houver espaço, operação não começa.
- Runa vinculada dentro de equipamento impede Trade/Mercado do equipamento enquanto instalada.

### 25.2 Encantamentos

- Cada equipamento pode possuir **até 1 Encantamento**.
- Runa e Encantamento são independentes; item pode ter ambos.
- Encantamento é modificação aplicada à `item_instance`, não componente em slot.
- Aplicar novo Encantamento substitui e **destrói** o anterior, com aviso explícito.
- Aplicação ocorre fora de combate e não em item bloqueado/escrow/competitivo.
- Por padrão, Encantamento não vincula o item, salvo receita/material que explicitamente imponha bind.
- Encantamento acompanha o equipamento se o item continuar negociável.
- Artífice é a principal profissão relacionada a Encantamentos/serviços correspondentes.
- Catálogo e números conforme a seção 49.

### 25.3 Grau e compatibilidade de componentes

- Runa e Encantamento possuem Grau I–VI. Para instalação/aplicação, exige-se `grau_do_componente ≤ equipment_grade(item_level)`.
- Componente de Grau inferior pode ser usado em Equipamento de Grau superior e mantém sua própria potência; não é promovido automaticamente ao Grau do Equipamento.
- Componente de Grau superior não pode ser instalado/aplicado em Equipamento de Grau inferior. O Equipment Validator rejeita a operação antes do commit.
- Extração de Runa preserva integralmente família, raridade, Grau, potência e bind da `rune_instance`.
- A compatibilidade de efeito por slot e as afinidades A/B de 2H continuam independentes desta regra de Grau e devem ser satisfeitas simultaneamente.

## 26. Consumíveis

- PvP não permite Consumíveis externos.
- PvE usa Consumíveis estratégicos de recuperação, Purificação, proteção e situação, evitando buffs obrigatórios de ATQ/DEF empilháveis.
- O catálogo global do **Alquimista** possui sete famílias: **Poção de Cura**, **Preparado de Purificação**, **Antídoto**, **Poção de Vigor**, **Preparado de Proteção**, **Dissipador** e **Preparado de Resguardo**.
- **PvE manual não exige preparação prévia de Consumíveis.** Consumíveis elegíveis que estejam no Inventário do personagem ficam disponíveis diretamente quando o conteúdo permitir seu uso.
- Armazém, Mercado, Pending, Crafting ou outras origens externas não são consultados automaticamente para suprir uma ação de Consumível durante o combate; a unidade utilizada precisa estar disponível no Inventário no momento da validação/commit.
- Cada conteúdo PvE pode definir quais Consumíveis são elegíveis e o limite de uso aplicável. Quantidades finais estão consolidadas na seção 49.
- Em **Masmorras**, o limite é autoritativamente **por jogador e por `run_id`**, podendo variar por Masmorra e dificuldade. Ele não reinicia entre encontros, wipe, Retry ou Braseiro de Masmorra.
- Possuir mais unidades no Inventário do que o limite da atividade não concede usos adicionais. Ao atingir o limite da run, novas ações de Consumível ficam bloqueadas para aquele jogador até o encerramento da `run_id`.
- Na interface de combate, a ação/botão **Consumível** deve ficar indisponível quando o jogador não possuir nenhum Consumível elegível/utilizável ou quando o limite aplicável tiver sido esgotado; quando necessário, o contexto informa o motivo do bloqueio.
- A disponibilidade de um Consumível exige simultaneamente: item elegível, quantidade real suficiente no Inventário, estado válido para uso e orçamento/limite restante no conteúdo.
- Todo Consumível de combate validamente utilizado consome **1 ação**, **1 unidade** e **1 uso do orçamento/limite normal de Consumíveis** da atividade, salvo override explícito de conteúdo.
- Todos os Consumíveis de combate compartilham **CD2**.
- Consumível é efetivamente gasto somente no commit da ação.
- Consumível utilizado não retorna após wipe, Retry, derrota ou interrupção válida.
- Tentativa rejeitada antes do commit por item, requisito, estado, turno, Recarga, limite, alvo ou efeito inválido **não consome unidade, ação, uso do orçamento nem CD2**.
- Poção de Vigor recupera **+20**, fora de combate, com limite de **1 uso por ciclo diário** e sem ultrapassar 100; não é vendida por dinheiro real.
- **Preparado de Proteção**, **Dissipador** e **Preparado de Resguardo** são utilizáveis somente durante combate PvE e não criam preparação obrigatória antes do encontro.
- A **Ronda de Caça** é exceção ao modelo direto do Inventário porque sua automação exige preparação/autorização explícita antes do lote, conforme a seção 26.1.

### 26.1 Consumíveis da Ronda de Caça

- A Ronda possui preparação própria de Consumíveis antes do início do lote.
- Essa preparação pode incluir **Poções de Cura** e **Consumíveis de Purificação** elegíveis.
- A preparação permanece travada durante todo o lote.
- Somente itens preparados podem ser utilizados automaticamente.
- A automação nunca repõe Consumíveis por Armazém, Mercado, Crafting, Pending ou outro sistema.
- Critérios de Cura e Purificação automática estão consolidados na seção 49.
- Poções de Vigor nunca fazem parte da automação da Ronda.
- **Preparado de Proteção**, **Dissipador** e **Preparado de Resguardo** não entram automaticamente na preparação nem na IA da Ronda; qualquer automação futura exige aprovação explícita própria.

### 26.2 Preparado de Proteção

- Consumível próprio, utilizável somente durante combate PvE.
- Concede `floor(12% × HP Máximo)` de **Barreira** por **2T**.
- A Barreira segue integralmente as regras globais normais de Barreira: é HP temporário e absorve dano antes do HP conforme a seção 9.4.
- A fonte lógica é `applier_id + consumable.protecao`.
- Não acumula consigo mesmo. Nova aplicação substitui a Barreira restante pelo novo valor e reinicia a duração em `2T`; não soma valores nem cria segunda instância.
- Grau mínimo **II**; requisito da família **Alquimista Nv.5**.
- Materiais por unidade: `3 Reagentes + 2 Essências` do Grau da Receita.
- A potência básica não aumenta com o Grau.

### 26.3 Dissipador

- Consumível ofensivo/utilitário direcionado a **1 inimigo válido**, utilizável somente durante combate PvE.
- Remove **1 efeito positivo removível selecionado** do alvo.
- Não exige teste de acerto, chance aleatória de falha ou resistência percentual própria do Consumível. Se a ação permanece válida no commit, o Dispel acontece.
- Efeito positivo não-stack: remove o efeito inteiro.
- Efeito positivo stackável: remove **1 stack**, o mais antigo.
- Nunca remove fase, mecânica fixa, estado `unremovable`, efeito protegido de Chefe ou Buff explicitamente marcado como não dissipável.
- Grau mínimo **III**; requisito da família **Alquimista Nv.10**.
- Materiais por unidade: `2 Reagentes + 3 Essências` do Grau da Receita.
- A potência básica não aumenta com o Grau.

### 26.4 Preparado de Resguardo

- Consumível próprio preventivo, utilizável somente durante combate PvE.
- Concede **Resguardo · 2T · 1 carga**.
- Durante a janela, a primeira aplicação elegível de efeito negativo que efetivamente teria sucesso é bloqueada integralmente e consome a carga.
- Se nenhum efeito elegível ocorrer em `2T`, o Resguardo expira sem efeito.
- O dano direto da ação que carregava o efeito resolve normalmente.
- Pipeline de interceptação: `tentativa → imunidade absoluta → resistência/redução válida → Resguardo → stacking/substituição → duração`. Uma aplicação que já falharia por imunidade ou resistência não consome o Resguardo.
- Elegíveis por padrão: DoT removível; Debuff numérico removível de ATQ/DEF/AGI/PER/CRIT/Bloqueio/Esquiva; redução removível de Cura Recebida; outro Debuff numérico removível; restrição removível de ação que não seja Hard CC.
- Não elegíveis por padrão: Hard CC; Stun ou efeito que consome integralmente a oportunidade; fase/mecânica fixa; estado `unremovable`; efeito protegido de Chefe; marca/recurso interno não tratado como Debuff removível normal.
- Para efeito especial fora das categorias padrão, `resguardo_eligible = false` por default, salvo declaração explícita `true` do conteúdo/sistema. Declaração explícita `false` sempre prevalece.
- Uma única aplicação multi-stack do mesmo efeito no mesmo `application_event` é bloqueada integralmente com consumo de 1 carga.
- Aplicações independentes são eventos separados: o Resguardo bloqueia somente o primeiro evento elegível na ordem autoritativa de resolução, é consumido e os eventos seguintes resolvem normalmente.
- Não acumula cargas. Nova aplicação enquanto ativo mantém **1 carga total** e reinicia a janela em `2T`.
- Grau mínimo **IV**; requisito da família **Alquimista Nv.12**.
- Materiais por unidade: `4 Reagentes + 2 Essências` do Grau da Receita.
- A potência básica não aumenta com o Grau.

## 27. Ofícios (Profissões), Crafting, Serviços e Desmontagem

### 27.1 Ofícios (Profissões)

- **Ferreiro**.
- **Artífice**.
- **Alquimista**.
- **Curteiro**.
- **Joalheiro**.

Cada personagem mantém **1 Ofício Principal** e **1 Ofício Secundário** ativos.

- O **Ofício Principal** pode utilizar a progressão completa do sistema.
- O **Ofício Secundário** possui limite de nível inferior ao Principal.
- Ofícios ativos: **Principal Nv.30 + Secundário Nv.15** como caps oficiais.
- Um Ofício ativo pode ser movido entre Principal e Secundário sem ser considerado abandonado.
- Ao mover um Ofício do slot Principal para o Secundário, seu nível é reduzido ao teto do Secundário caso esteja acima dele; **todo progresso excedente é perdido e não permanece armazenado**.
- Ao promover o Ofício Secundário a Principal, o progresso que ele possui naquele momento é mantido e ele pode continuar avançando até o limite do Principal.
- Como consequência, apenas o Ofício atualmente Principal pode possuir progressão acima do teto do Secundário; inverter os dois Ofícios ativos nunca preserva uma progressão excedente oculta no Ofício rebaixado.
- **Abandonar um Ofício**, removendo-o dos dois slots ativos, **reseta seu progresso de nível**. Se esse Ofício for escolhido novamente no futuro, retorna ao nível inicial.
- Receitas já descobertas permanecem conhecidas mesmo após o abandono, mas só podem ser utilizadas quando o Ofício estiver ativo novamente e o personagem recuperar todos os requisitos de nível e demais condições da receita.
- O personagem não mantém níveis acumulados de Ofícios inativos/abandonados.
- Troca de Ofício ocorre em cidade/local apropriado por Coroas.
- Crafting é instantâneo, sem timer.
- Receitas vêm de progresso, exploração, Boss, Dungeon, evento e Crônica.
- **Descobrir/conhecer uma Receita não exige que o Ofício correspondente esteja ativo nem que o personagem já cumpra o nível do Ofício.** Elegibilidade de descoberta é determinada pela fonte, progressão e condições explícitas do conteúdo, além de a Receita ainda ser desconhecida. Utilizar a Receita continua exigindo Ofício ativo, nível e todos os demais requisitos normais.

### 27.2 Crafting

- Preview → confirmação → commit atômico.
- Antes do commit pode cancelar; depois, craft aconteceu.
- Craft comum valida destino antes de consumir recursos.
- Se uma operação já confirmada precisar gerar item e não houver espaço por condição inevitável, usa Resultado/Entrega Pendente.
- Em local seguro, pode usar materiais de Inventário + Armazém.
- Preview mostra exatamente quais stacks serão consumidos e qual será o bind do resultado.
- Se combinações de materiais mudarem propriedades econômicas, usuário precisa visualizar/confirmar a combinação válida.
- Componentes estruturais vinculados podem transmitir a restrição mais forte.
- Catalisadores de upgrade/serviço não transmitem bind por padrão, salvo definição explícita.
- RNG de craft é persistido uma vez; crash/retry não rerrola.
- Quando o resultado for Equipamento, Crafting usa o materializador global da seção 24.6: a Receita fixa `template_id` e raridade, `item_level` segue a regra da seção 49.11, bind deriva da Receita/materiais e os secundários são materializados uma única vez no commit. Preview com RNG mostra garantias/faixas, nunca promete uma combinação ainda não comprometida.

### 27.3 Serviços

- Backend/escrow; cliente fornece materiais + pagamento.
- Craft/serviço executa sem exigir aceitação manual posterior do artesão.
- Se houver RNG, preview mostra garantias e faixas.
- Oferta só fica ativa enquanto Ofício/receita/nível continuam válidos.
- No commit, Ofício, nível, receita, preço e materiais são revalidados.
- Subprodutos/sobras da receita pertencem ao cliente salvo regra explícita anterior.
- Próprio personagem não pode contratar o próprio Serviço público; usa Craft normal.
- Serviços entram no monitoramento anti-manipulação econômica.
- **Serviços públicos são apresentados através da Loja Pessoal do artesão.**
- Cada oferta pública de Serviço pertence à `shop_id` do personagem que a oferece.
- Cada oferta pública possui duração de **7 dias**; ao expirar, deixa de aparecer na Loja e precisa ser renovada/republicada para voltar a ficar ativa.
- Não existe diretório global separado de Serviços nem busca global por Serviço no lançamento.
- O comprador encontra o Serviço acessando a Loja do artesão por Código/divulgação.
- Serviços não consomem slots de listing de itens; cada Loja pode manter **até 3 ofertas públicas de Serviço simultâneas**.
- Uma Loja pode possuir apenas listings de itens, apenas Serviços, ambos ou nenhuma oferta ativa.
- Alteração material de receita por patch continua podendo suspender ofertas correspondentes.
- O preço de uma oferta de Serviço **pode ser editado diretamente enquanto a oferta estiver ativa e sem commit em andamento**. A edição incrementa `service_offer_revision`; qualquer preview/confirmação baseado em revisão anterior é invalidado e precisa ser refeito. Alterar Receita/output exige cancelar e recriar a oferta.

### 27.4 Desmontagem

- Equipamento elegível pode ser destruído irreversivelmente para materiais por categoria/raridade.
- Não gera Coroas diretamente.
- Sem chance de falha.
- Favorito/Locked não pode ser desmontado.
- Mítico exige confirmação reforçada.
- Equipado precisa ser desequipado pelo Equipment Validator.
- Desmontagem nunca reduz restrição econômica: material derivado de item Bound permanece restrito o suficiente para impedir lavagem de Bind.

## 28. Mercado e Loja Pessoal

### 28.1 Princípio do Mercado

O Mercado de Asterion é estruturado em torno de **Lojas Pessoais de jogadores**, e não de uma casa de leilões ou catálogo global.

Não existem no lançamento:

- catálogo global de itens;
- diretório navegável de todas as Lojas;
- navegação global por categorias;
- busca global por item retornando vendedores;
- ranking ou recomendação automática de Lojas.

A descoberta de uma Loja ocorre principalmente por:

- **Código Único da Loja**;
- divulgação da Loja no tópico oficial **Mercado** da Comunidade;
- compartilhamento do Código entre jogadores;
- deep link oficial do Bot quando tecnicamente utilizado.

O Bot continua sendo a autoridade para listings, escrow, compras, Coroas, Serviços, validações e integridade econômica. A Comunidade atua como principal espaço social de divulgação, nunca como fonte de verdade econômica.

### 28.2 Loja Pessoal

Depois que o personagem possuir acesso válido ao Mercado conforme as regras de progressão aplicáveis, ele possui uma **Loja Pessoal** vinculada ao seu personagem naquele servidor.

Cada Loja possui, no mínimo:

- `shop_id` interno e imutável;
- `owner_character_id`;
- `server_id`;
- Código Único da Loja;
- Nome Público customizado opcional;
- Descrição pública opcional;
- listings/ofertas de itens;
- ofertas de Serviços quando aplicável;
- estado necessário para operações econômicas e auditoria.

A Loja é server-bound e não permite movimentação econômica entre servidores.

A Loja Pessoal possui **6 listings de itens** e **3 ofertas públicas de Serviço** simultâneas; cada listing dura **7 dias**.

A Loja permanece existente mesmo quando não possui ofertas ativas.

### 28.3 Código Único da Loja

Cada Loja Pessoal possui um **Código Único da Loja**, público e compartilhável.

O Código:

- identifica uma única `shop_id`;
- não depende do nome do personagem;
- não depende de Telegram username, telefone, Telegram ID ou outro dado privado;
- permanece associado à mesma Loja enquanto ela existir;
- não funciona como autorização ou credencial;
- pode ser digitado e compartilhado no Telegram;
- utiliza representação adequada à digitação manual e deve evitar caracteres visualmente ambíguos quando tecnicamente apropriado;
- deve ser opaco e não sequencial, evitando enumeração trivial de Lojas.

Formato, comprimento, alfabeto e mecanismo de geração pertencem à **Implementação**, não ao Balanceamento. A geração deve garantir unicidade atomicamente.

No lançamento, o Código é **permanente durante a existência daquela Loja** e não pode ser regenerado livremente pelo proprietário.

Renomear o personagem ou editar a apresentação pública da Loja não altera o Código.

Se a Loja deixar definitivamente de existir, seu Código antigo não deve ser reutilizado para uma Loja diferente, impedindo que divulgações antigas passem a apontar para outro proprietário.

Uma eventual regeneração futura exigirá regra própria de segurança/migração, ação explícita e nunca altera a `shop_id`.

### 28.4 Buscar Loja

O Menu Mercado possui a ação **Buscar Loja**.

Fluxo estrutural:

**Mercado → Buscar Loja → informar Código → validar → abrir Loja.**

A busca utiliza o Código Único da Loja. Não existe busca pública de Loja por Telegram username, Telegram ID, telefone, item ou categoria.

O backend normaliza e valida o Código. Se não corresponder a Loja acessível:

- retorna resposta simples de Loja indisponível/código inválido;
- permite nova tentativa;
- não revela dados internos;
- aplica rate limiting apropriado contra flood e enumeração automatizada.

Conhecer o Código concede apenas capacidade de localizar e visualizar a Loja pública.

### 28.5 Apresentação pública da Loja

Cada Loja pode possuir:

- **Nome Público da Loja** customizado;
- **Descrição da Loja** curta e opcional.

Esses campos são conteúdo de apresentação criado pelo jogador e não alteram `shop_id`, Código, proprietário, `server_id`, listings, Serviços, escrow, preços, quantidades, permissões ou histórico econômico.

#### Nome Público

- É opcional, editável e removível pelo proprietário.
- Não precisa ser único e nunca funciona como identificador técnico.
- Quando não existir Nome Público customizado, a interface utiliza automaticamente: **Loja de {Nome atual do personagem proprietário}**.
- Se o personagem for renomeado, o fallback acompanha o novo nome; um Nome Público customizado já existente permanece até ser editado/removido.
- O nome deve ser curto e legível em uma linha.
- Nome Público da Loja: máximo de **36 caracteres**.

#### Descrição

- É opcional, editável e removível.
- Serve somente para identidade/apresentação.
- Pode aparecer na Loja pública e, de forma resumida, na divulgação para a Comunidade.
- Quando estiver vazia, a seção desaparece completamente; não existe placeholder “Sem descrição”.
- Descrição da Loja: máximo de **240 caracteres**.
- Links externos arbitrários não são permitidos na Descrição no lançamento.

#### Editar Loja

A ação **Editar Loja** modifica exclusivamente os elementos de apresentação pública.

Pode permitir:

- Editar Nome;
- Remover Nome customizado e retornar ao fallback;
- Editar Descrição;
- Remover Descrição.

Editar Loja **não** permite alterar Código, `shop_id`, proprietário, listings, preço, quantidade, escrow ou Serviços.

A edição de preço pertence à própria listing através de **Editar Preço**.

Nome e Descrição seguem validação, sanitização e moderação de conteúdo. O backend deve impedir abuso de formatação, caracteres de controle, markup malicioso, tentativa enganosa de imitar mensagens de sistema, spam, fraude ou conteúdo proibido. Não existe cooldown de gameplay obrigatório para editar Nome/Descrição; rate limiting técnico pode ser aplicado contra flood/automação abusiva.

### 28.6 Loja vazia

Uma Loja sem ofertas continua existente e mantém `shop_id`, proprietário, Código, Nome/fallback e Descrição quando houver.

Acessar o Código de Loja sem ofertas informa simplesmente que não existem ofertas disponíveis no momento.

A Loja não é apagada, ocultada estruturalmente nem recebe novo Código por ficar vazia.

### 28.7 Minha Loja

O proprietário possui acesso a **Minha Loja**.

Esse fluxo centraliza, conforme aplicável:

- Código da Loja;
- Nome/Descrição públicos;
- listings ativas;
- adicionar ofertas;
- Editar Preço de oferta ativa;
- Remover da Loja;
- Serviços públicos;
- Editar Loja;
- Divulgar Loja.

Operações administrativas sempre validam ownership por `shop_id + character/account + server`. O Código nunca concede permissão administrativa.

### 28.8 Divulgar Loja na Comunidade

Cada Loja possui a ação **Divulgar Loja**, direcionada ao tópico oficial **Mercado** da Comunidade de Asterion.

A divulgação pode conter, de forma curta:

- Nome Público atual ou fallback;
- identificação do proprietário quando apropriado;
- Código Único da Loja;
- quantidade de ofertas disponíveis no momento;
- versão resumida da Descrição quando apropriado;
- deep link oficial, quando implementado.

A divulgação não publica automaticamente o catálogo completo nem gera mensagem excessivamente longa.

O compartilhamento possui proteção antispam e Recarga/cooldown, com valor final consolidado na seção 49.

A publicação representa um **snapshot promocional**. Alterações posteriores de Nome, Descrição, preço, quantidade ou Serviços não precisam editar retroativamente mensagens antigas.

Ao abrir a Loja, o Bot sempre consulta o estado atual.

### 28.9 Deep links de Loja

O Bot pode utilizar deep link para facilitar abertura de Loja divulgada na Comunidade.

- Deep link é apenas mecanismo de navegação.
- Resolve para a mesma `shop_id` associada ao Código.
- Parâmetros nunca são tratados como autorização e sempre são revalidados server-side.
- Não ignora `server_id`, estado da Loja, ownership, disponibilidade ou restrições globais da atividade.
- Link antigo não preserva estado antigo de listing.
- O Código Único continua existindo mesmo quando deep link é utilizado.

### 28.10 Listings, escrow e termos da oferta

Uma listing representa oferta persistente vinculada ao item/quantidade colocados em escrow.

- Listing possui expiração configurável.
- O item permanece em escrow enquanto a listing estiver ativa.
- A **quantidade inicial colocada à venda é imutável para edição manual do vendedor**.
- Compras parciais reduzem naturalmente a quantidade restante.
- O **Preço de Venda pode ser alterado diretamente pelo proprietário**, sem cancelar/recriar a listing.
- Alterar preço não remove o item do escrow, não cria segunda listing e não altera `listing_id`.
- Para mudar manualmente a quantidade inicial/remanescente oferecida, o proprietário deve Remover/Cancelar a listing e criar outra com a quantidade desejada.
- Item/materialmente alterado por patch força revisão; patch relevante pode suspender automaticamente listings afetadas.

### 28.11 Editar Preço e versionamento da oferta

O proprietário pode utilizar **Editar Preço** em listing ativa elegível.

A operação:

- recebe o novo Preço de Venda em Coroas;
- valida ownership e estado atual da listing;
- valida o valor conforme as regras econômicas;
- atualiza o preço atomicamente;
- atualiza a **versão dos termos da listing**;
- registra a alteração para auditoria.

Durante a operação, o item permanece em escrow e não pode ser equipado, negociado por Troca Direta, utilizado em outra listing, desmontado ou consumido por fluxo incompatível.

Cada alteração material dos termos da listing invalida confirmações de compra baseadas na versão anterior.

O comprador deve confirmar com referência suficiente ao estado apresentado, incluindo no mínimo:

- `listing_id`;
- versão dos termos;
- preço apresentado;
- quantidade solicitada.

No commit, o backend revalida listing ativa, comprador/proprietário, preço, versão, quantidade, escrow, Coroas disponíveis, destino final e demais regras econômicas.

Se preço ou termos mudaram desde a visualização:

- a compra não conclui;
- nenhuma Coroa é debitada;
- nenhum item é entregue;
- o jogador é informado de que a oferta foi atualizada;
- o estado/preço atual é apresentado;
- nova confirmação é exigida.

Uma confirmação antiga nunca é reinterpretada silenciosamente usando preço novo.

### 28.12 Compra parcial e concorrência

- Pilhas podem ser compradas parcialmente quando permitido.
- Compra parcial é atômica e conserva quantidade exata.
- Redução de quantidade por compra válida não é edição manual da listing.
- Outra compra parcial anterior não invalida necessariamente uma confirmação se os termos continuam válidos e ainda existe quantidade suficiente para a quantidade solicitada.
- Se não houver quantidade suficiente, a operação falha com segurança e apresenta o estado atual.
- Em compras concorrentes, o primeiro commit válido vence; quantidade nunca fica negativa e item nunca é duplicado.

Compra e Editar Preço competem atomicamente pelo estado da mesma listing:

- se a compra baseada na versão vigente commitou primeiro, conclui pelo preço apresentado/confirmado; a alteração posterior só pode afetar a quantidade restante se a listing continuar ativa;
- se Editar Preço commitou primeiro, a versão muda e qualquer compra baseada na versão anterior falha;
- se a compra consumir toda a quantidade e encerrar a listing, tentativa posterior de editar preço falha porque a listing não está mais ativa.

Nenhuma ordem concorrente produz estado parcial.

### 28.13 Remover da Loja

O proprietário pode remover/cancelar listing ativa.

- A operação é server-side e atômica.
- Encerra a listing.
- Devolve somente a quantidade ainda restante.
- Respeita destino/capacidade e Entrega Pendente quando aplicável.
- Invalida ações de compra não commitadas.
- Registra a operação.
- Nunca duplica item ou quantidade.

### 28.14 Compra, crédito e segurança econômica

- Compra usa sempre o estado atual e valida espaço/destino final.
- O proprietário não pode comprar a própria listing.
- Coroas líquidas são creditadas automaticamente ao vendedor, inclusive offline; não existe “Coletar Vendas”.
- Se a carteira estiver no teto, excedente cria **Crédito Financeiro Pendente**, auditável e não utilizável até haver capacidade.
- Não existe vendedor NPC que compre equipamento por Coroas no lançamento; vender equipamento significa utilizar Loja Pessoal. Desmontagem é a alternativa sem comprador.
- Código, Nome, Descrição, deep link, mensagem comunitária ou callback público nunca constituem autorização econômica.
- Abrir a mesma Loja em celular/Desktop representa a mesma `shop_id` e o mesmo estado autoritativo.

### 28.15 Auditoria de preço

Alterações de preço são auditáveis. O histórico interno deve permitir determinar no mínimo listing, proprietário, preço anterior, novo preço, data/hora e versão correspondente.

Esse histórico não precisa ser exibido integralmente na UI comum. Uma venda registra o preço efetivamente utilizado no commit.

### 28.16 Serviços na Loja

Serviços públicos são encontrados dentro da Loja Pessoal do artesão conforme a seção 27.3. Não existe diretório global ou busca global de Serviços no lançamento.

### 28.17 Taxa

- Transações da Loja continuam sujeitas às taxas econômicas definidas pelo sistema.
- Coroas usam valor inteiro.
- Arredondamento é determinístico e não pode ser explorado dividindo uma pilha em muitas compras.
- Fórmula/taxa final conforme a seção 49.

## 29. Troca Direta (Trade)

- Troca Direta é alternativa independente à Loja Pessoal e não exige Código de Loja.
- É um dos três pilares do Menu Mercado: **Buscar Loja / Minha Loja / Troca Direta**.
- Troca direta de **itens** é permitida.
- Coroas diretas entre jogadores **não** são permitidas.
- Pode haver item↔item ou presente unilateral.
- Apenas itens **Negociáveis**, desbloqueados e fora de escrow/estado incompatível.
- Duas etapas de confirmação; qualquer alteração reseta confirmações.
- Itens ficam reservados temporariamente; sessão possui timeout.
- Commit é atômico e simula o estado final de ambos os Inventários, permitindo full→full 1-por-1 quando o estado final cabe.
- Mítico exige confirmação extra.
- Patch material em item antes do commit reseta confirmações e mostra o estado atualizado.
- Logs registram IDs, quantidades e relações relevantes.
- Troca Direta não deve servir para Coroas/RMT indireto; padrões suspeitos são analisados.

## 30. Guildas

- Nome oficial: **Guilda**.
- Cap de lançamento: **12 membros**.
- Nome: 3–16 letras A–Z, sem espaços/números/acentos/símbolos, case-insensitive, único por servidor.
- TAG: exatamente 3 letras A–Z, uppercase, única por servidor.
- Cargos: **Líder / Oficial / Membro**.
- Líder possui controle total e ações irreversíveis críticas.
- Oficial administra operações cotidianas autorizadas, mas não dissolve Guilda nem transfere liderança sozinho.
- Membro participa/contribui.
- Ações administrativas relevantes são logadas.
- Permissão é revalidada no commit; botão antigo não preserva privilégio.

### 30.1 Entrada, Convites, Recrutamento e Inscrições

#### Regra comum de entrada

- Um personagem pode pertencer a **no máximo uma Guilda por servidor**.
- Toda entrada é processada de forma **atômica**, seja por Convite ou por aprovação de Inscrição.
- No commit, o backend revalida personagem sem Guilda, mesmo servidor, capacidade válida, ausência de `over-cap`, origem ainda válida, cooldown/restrição vigente de troca e ausência de concorrência que já tenha consumido personagem ou última vaga.
- Disponibilidade/vaga exibida anteriormente nunca garante entrada futura.
- Se duas operações tentarem inserir o mesmo personagem simultaneamente, apenas uma conclui.
- Se duas entradas disputarem a última vaga, apenas uma conclui.
- Nunca é permitido personagem em duas Guildas nem capacidade acima do máximo por race condition.
- Se a capacidade for reduzida e a Guilda ficar acima do cap, entra em `over-cap`; ninguém é expulso automaticamente, mas novas entradas ficam bloqueadas até a capacidade voltar a ser válida.

#### Convites

- O sistema de **Convites de Guilda permanece oficial** e funciona em paralelo às Inscrições.
- Convites não dependem do estado Aberto/Fechado de recrutamento; uma Guilda Fechada ainda pode convidar diretamente quando autorizado.
- Aceitar Convite executa a mesma validação atômica de entrada.
- Convite antigo não garante entrada se o personagem já estiver em outra Guilda, não houver vaga ou outra restrição tiver surgido.
- Após entrada válida em qualquer Guilda, demais Convites incompatíveis deixam de ser utilizáveis.

#### Estado de Recrutamento

Cada Guilda possui estado:

- **Aberto** — jogadores elegíveis podem enviar Inscrições.
- **Fechado** — novas Inscrições não podem ser enviadas.

Regras:

- **Líder e Oficiais** podem alterar o estado de recrutamento, por se tratar de administração cotidiana autorizada.
- Membros comuns não podem alterar esse estado.
- Cargo/permissão são revalidados no commit.
- Fechar recrutamento impede novas Inscrições, mas não cancela automaticamente as Pendentes já existentes.
- Inscrições Pendentes ainda podem ser analisadas por Líder/Oficiais.
- Recrutamento Fechado não impede Convites diretos autorizados.
- Recrutamento Aberto nunca ignora capacidade ou outra restrição de entrada.

#### Procurar Guilda

Personagens sem Guilda possuem acesso a **Procurar Guilda**.

O sistema oferece:

- busca por **Nome oficial da Guilda**;
- busca por **TAG**;
- listagem paginada de Guildas com recrutamento Aberto aptas a receber candidaturas.

Regras:

- Busca/resultados são restritos ao servidor atual.
- Nome e TAG obedecem às regras oficiais de normalização/unicidade.
- Guildas com recrutamento Fechado podem aparecer em busca direta por Nome/TAG, mas não oferecem Enviar Inscrição.
- Guildas cheias ou em `over-cap` não oferecem Enviar Inscrição.
- A listagem de recrutamento não constitui ranking nem recomendação competitiva.
- Paginação usa `guild_id` estável internamente; Nome/TAG não são identidade técnica de ação.
- Jogadores que já pertençam a Guilda não podem enviar Inscrições. Consulta pública a outras Guildas pode ser permitida pela UI, mas não é necessária ao fluxo inicial.

#### Página pública da Guilda

Ao selecionar uma Guilda, o jogador pode visualizar resumo público contendo no mínimo:

- `[TAG] Nome`;
- quantidade atual de membros;
- capacidade máxima;
- estado de recrutamento.

A página não expõe Tesouraria, administração interna, compromissos privados ou outros dados exclusivos dos membros.

Esta versão não cria **Lore da Guilda** nem **Mural da Guilda**. Se forem aprovados futuramente, Lore explicitamente pública poderá aparecer na página; eventual Mural permanecerá privado aos membros e seus links/conteúdo não serão expostos pela busca pública.

#### Inscrições de Guilda

Um personagem pode enviar Inscrição quando:

- não pertence a Guilda;
- a Guilda está com recrutamento Aberto;
- existe capacidade válida para novas entradas;
- o personagem respeita cooldown/restrições existentes de troca de Guilda;
- nenhuma outra condição estrutural impede entrada.

Ao enviar, cria-se registro contendo no mínimo `guild_id`, `character_id`, `server_id`, data/hora e estado.

Estados oficiais no lançamento:

- **Pendente**;
- **Aprovada**;
- **Recusada**;
- **Cancelada**.

Não existe expiração automática obrigatória no lançamento. Uma eventual expiração futura exigirá regra própria antes de introduzir estado **Expirada**.

- Não pode existir mais de uma Inscrição Pendente do mesmo personagem para a mesma Guilda.
- O personagem pode manter Inscrições Pendentes em Guildas diferentes até limite global, conforme a seção 49.
- O jogador pode cancelar Inscrição enquanto permanecer Pendente, liberando espaço no limite.
- Inscrição Recusada deixa de estar Pendente.
- Rate limiting contra flood existe; limites quantitativos/temporais estão consolidados na seção 49.
- Não existe cooldown específico obrigatório de reaplicação após Recusa no lançamento além das proteções gerais de spam.
- Histórico pode permanecer registrado para segurança/auditoria sem continuar ativo.

#### Minhas Inscrições

- O jogador pode consultar suas Inscrições e estados.
- Inscrição Pendente oferece **Cancelar Inscrição**.
- Estado exibido deriva sempre do backend; mensagem antiga não preserva estado Pendente após resolução.

#### Gestão das Inscrições

Líder e Oficiais podem:

- visualizar Inscrições recebidas;
- abrir o Perfil Público do candidato;
- **Aprovar**;
- **Recusar**.

Não existe ficha intermediária obrigatória; o Perfil Público existente pode cumprir essa função.

Membros comuns não podem aprovar/recusar. Toda ação é logada e a permissão é revalidada no commit.

#### Aprovação e entrada atômica

**Aprovar uma Inscrição representa a tentativa de entrada imediata do personagem na Guilda.** Não existe segunda confirmação obrigatória do candidato.

No commit da aprovação, revalidar atomicamente:

- Inscrição continua Pendente;
- responsável ainda possui permissão;
- personagem continua sem Guilda;
- Guilda ainda possui vaga e não está em `over-cap`;
- cooldown/restrições de troca continuam satisfeitos;
- nenhuma entrada concorrente já ocorreu;
- estado atual permite a operação.

Somente depois de todas as condições passarem:

- vínculo de membro é criado;
- Inscrição passa para **Aprovada**;
- capacidade final é consolidada;
- demais Inscrições Pendentes do personagem são automaticamente **Canceladas pelo sistema**;
- demais Convites incompatíveis deixam de ser utilizáveis.

Essas alterações fazem parte da mesma transação lógica.

Se a entrada não puder concluir, a Inscrição não pode ser marcada falsamente como Aprovada.

Se a falha ocorrer apenas porque a Guilda ficou sem vaga, a Inscrição pode continuar Pendente até ser recusada, cancelada ou tornar-se novamente aprovável. Se o personagem já entrou em outra Guilda, a Inscrição deixa de poder ser aprovada e é encerrada pelo sistema.

#### Concorrência entre Convites e Inscrições

Convites e Inscrições competem pela mesma condição única de pertencimento à Guilda.

Em duas aprovações simultâneas, aprovação concorrendo com aceite de Convite ou duas candidaturas disputando a última vaga:

- apenas o primeiro commit válido produz entrada;
- operações seguintes revalidam e falham com segurança;
- personagem nunca pertence a duas Guildas;
- capacidade nunca ultrapassa o limite;
- nenhum estado parcialmente concluído é preservado.

- Renome de Guilda/TAG custa **15.000 Coroas da Tesouraria** e possui **30 dias de Recarga**, com histórico e retenção do nome antigo.

### 30.2 Obras da Guilda (Projetos) e Tesouraria

Obras da Guilda:

- Alojamentos.
- Forja.
- Altar do Véu.
- Tesouraria.
- Arquivo do Véu.
- Posto dos Caçadores.
- Salão de Guerra.

Regras:

- Máximo 2 simultâneos.
- Alojamentos possui progressão definitiva de capacidade **5→7→9→10→11→12**.
- Tesouraria pertence à Guilda; não existe saque livre para carteira pessoal.
- Contribuições são finais/não reembolsáveis.
- Contribuição ao projeto é atômica e limitada ao restante necessário.
- Estados: **Financiamento** e **Construção**.
- Projeto em construção não é cancelável no lançamento.
- Durante dissolução, projeto ainda em Financiamento pode ser encerrado com perda explícita dos recursos comprometidos para evitar deadlock.
- Projeto em Construção precisa ser concluído/resolvido antes da dissolução final.

### 30.3 Dissolução e sucessão

- Dissolução possui safety/cancel period de **72h**.
- Depósitos podem ser congelados e compromissos resolvidos.
- Saldo restante não é distribuído aos membros; é forfeitado como sink com aviso explícito.
- Não pode finalizar dissolução com Batalha de Guildas, Juramento, Expedição, Obra/compromisso coletivo incompatível ativo.
- Sucessão por inatividade ocorre após **168h / 7 dias completos** sem atividade autenticada do Líder.
- Ban definitivo do Líder inicia sucessão apropriada sem esperar inatividade comum.
- Sem Oficial elegível, usa membro elegível por critério determinístico.
- Cooldown de troca de Guilda é **12h**, com escopo `conta + servidor`, protegido contra reset por recriação.
- Sair remove imediatamente benefícios ativos da Guilda.

### 30.4 Recompensas coletivas

- Atividades periódicas são `cycle-bound` para impedir guild hopping.
- Snapshot de elegibilidade individual impede ingresso tardio oportunista seguido de recompensa sem participação válida.
- Se recompensa já foi legitimamente conquistada e snapshotada, saída/expulsão posterior não a apaga.
- No **Juramento**, o vínculo do personagem com `guild_id + cycle_id` é estabelecido na primeira Provação validamente iniciada daquele ciclo.
- Contribuição do Juramento não migra entre Guildas e o mesmo personagem não pode receber recompensas de Juramento de múltiplas Guildas no mesmo ciclo.
- Resultado coletivo e elegibilidade individual são estados distintos: a Guilda atingir uma faixa não torna automaticamente todos os membros elegíveis.

## 31. Vínculos (Social) e Comunidade

- Limites sociais: **100 Amigos; 20 Pedidos enviados Pendentes; 30 recebidos Pendentes; 30 Recentes por 14 dias; 100 Bloqueados**.
- Sem DM interno no lançamento.
- Busca por nome do personagem; nunca expor Telegram ID, telefone ou username privado.
- Perfil público pode mostrar nome, nível, Legado, raça, Classe/Caminho, Guilda, Título, Elo, Feitos, histórico de Crônicas e **História do Personagem**; Doutrina escondida por padrão.
- A História do Personagem só aparece no perfil público quando existir conteúdo salvo pelo jogador.
- Block impede amizade, convite direto de Grupo, Troca Direta, convite de Guilda e LFG direcionado.
- Block não precisa impedir pareamento aleatório de fila pública nem compra em Loja pública.
- Tópicos oficiais: **Global, Eventos, Mercado, Guildas, LFG, Crônicas, Relatos, Atualizações, Sugestões, Bugs**.
- Internamente, referências usam IDs imutáveis, nunca nome como chave.
- O tópico oficial **Mercado** é o principal espaço comunitário para divulgação voluntária de Lojas Pessoais.
- Divulgação pode incluir Código Único e deep link oficial validado pelo Bot, além de apresentação pública permitida da Loja.
- Mensagens comunitárias de Loja são snapshots promocionais e **não são fonte de verdade econômica**; preço, quantidade, Serviços e disponibilidade são sempre reconsultados no backend.
- O tópico Mercado não funciona como catálogo global, banco de dados de listings ou garantia de disponibilidade.

### 31.1 Histórias de Personagem e Relatos

- Cada personagem pode possuir uma **História do Personagem** escrita pelo próprio jogador.
- A História do Personagem representa background, personalidade, acontecimentos ou interpretação pessoal daquele personagem dentro de Asterion.
- História do Personagem: máximo de **600 caracteres**.
- A História é opcional. Personagem sem História cadastrada não exibe seção vazia nem placeholder no perfil público.
- O jogador pode editar ou remover sua própria História.
- Salvar ou editar a História não a publica automaticamente na Comunidade Oficial.
- O jogador pode usar uma ação explícita de **Compartilhar História** para publicar um **Relato** no tópico oficial **Relatos** da Comunidade.
- A publicação utiliza snapshot do texto existente no momento do compartilhamento. Alterações posteriores no perfil não precisam modificar publicações anteriores.
- O Relato identifica claramente o personagem autor e pode oferecer botão/deep link para abrir seu Perfil público no Bot.
- Compartilhamento de História/Relato possui **Recarga de 6h** por personagem.
- Histórias e Relatos são conteúdo criado por jogadores e **não constituem lore canônica oficial** de Asterion.
- Conteúdo escrito pelo jogador não pode alterar `world_state`, `character_narrative_state` oficial, Campanha, Crônica, Códice, missões, NPCs, decisões globais ou qualquer outra fonte canônica de verdade.
- O jogador pode interpretar acontecimentos oficiais através da perspectiva do próprio personagem, mas sua História não transforma alegações pessoais em fatos oficiais do universo.
- Escrever, editar, compartilhar ou receber reações em Histórias não concede XP, Coroas, Vigor, itens, poder de combate, Renome/MMR ou outra vantagem econômica/competitiva.
- Eventos comunitários de escrita podem existir futuramente, mas qualquer recompensa deve ser definida separadamente e priorizar Aparências, Títulos, Molduras ou prestígio, sem tornar a participação obrigatória para progressão.
- Histórias e Relatos estão sujeitos às regras de moderação da Comunidade.
- Deve existir forma de denunciar conteúdo inadequado.
- Links externos e conteúdo usado principalmente para spam, propaganda ou fraude podem ser bloqueados.
- A remoção/moderação de uma História ou Relato não altera progressão, estado narrativo, economia ou demais dados do personagem.
- Edição da própria História é acessível pelo Perfil do personagem; não exige nova entrada no Menu Principal.

## 32. Sistemas de Engajamento & Comunidade

### 32.1 Dádiva Diária (Login Diário)

- Existe sistema de **Dádiva Diária** (Login Diário/Check-in).
- Recompensa é controlada e não pode gerar vantagem competitiva obrigatória/P2W.
- Dádiva Diária usa ciclo persistente de **7 claims**; perder um dia apenas adia o próximo claim, sem reiniciar a sequência.
- Perder um dia não precisa zerar toda a sequência; o progresso avança quando o check-in válido é realizado.
- Claim é idempotente e usa escopo apropriado como `conta + servidor + ciclo diário`.
- Recompensas exatas seguem a tabela consolidada da seção 49: **500 Coroas + 6 Materiais Básicos vinculados + 5 Fragmentos vinculados** por ciclo completo de 7 claims.

### 32.2 Chamado de Asterion (Recrutamento / Indicações)

- Cada jogador pode possuir link/código de recrutamento.
- Novato vincula recrutador dentro de janela inicial definida.
- Recompensas são liberadas por marcos reais de progressão, não apenas por criar conta.
- Auto-recrutamento, multiboxing ou criação de contas para farmar recompensa é proibido.
- Recompensas devem priorizar prestígio/cosméticos e economia pequena/controlada, nunca fonte forte de poder/Coroas.
- Os marcos e os nomes das recompensas do Chamado seguem a sequência consolidada na seção 49.19.
- Detecção gera análise, não ban automático por associação.

### 32.3 Comunidade Oficial

- O Bot possui acesso permanente à **Comunidade Oficial**.
- **Comunidade** é uma entrada permanente e direta do Menu Principal; não pertence a Configurações.
- Quando tecnicamente apropriado, essa entrada pode levar diretamente à Comunidade Oficial sem submenu intermediário.
- **Ajuda** pode referenciar a Comunidade contextualmente, sem alterar sua posição como entrada direta do Menu Principal.
- No onboarding, o convite aparece depois de o jogador já compreender minimamente o jogo, não antes da criação do personagem.
- Link é configuração administrativa, não hardcoded.

### 32.4 Códigos de Asterion (Códigos Promocionais)

- Sistema permite códigos criados pelo ADM ou gerados automaticamente.
- Código pode ter início, expiração, limite global, usos por conta, escopo, recompensa e estado ativo/inativo.
- Pode existir código de prêmio fixo ou de recompensa aleatória dentro de tabela previamente configurada.
- Em prêmio aleatório, o sorteio é persistido uma única vez por `code_redemption_id`; crash/retry não rerrola.
- Padrão: 1 resgate por `conta + servidor` salvo campanha que declare outro escopo.
- Exclusão/recriação não concede novo resgate quando o escopo é account-based.
- Resgate é atômico e idempotente.

## 33. Bestiário, Códice, Feitos, Títulos e Cosméticos

### 33.1 Bestiário

O Bestiário representa o conhecimento adquirido pelo personagem sobre as criaturas de Asterion.

Estágios oficiais:

**Observado → Conhecido → Estudado → Dominado**

O estágio representa combinação de contato, descoberta, combate, observação de comportamentos e conhecimento legitimamente adquirido; não é apenas contagem de abates.

Criaturas ainda não descobertas permanecem **completamente ausentes**. Não utilizar `???`, slots vazios, silhuetas ou qualquer apresentação que revele antecipadamente que determinada criatura existe.

#### Observado

Uma criatura torna-se **Observada** quando o personagem a identifica validamente pela primeira vez através de uma fonte elegível.

Revela, quando aplicável:

- nome;
- estágio de conhecimento;
- Região → Local legitimamente conhecido onde foi observada;
- classificação/tipo básico;
- descrição curta de identificação;
- elemento visual correspondente.

Não revela automaticamente atributos detalhados, fraquezas, resistências, imunidades, Artes, comportamento avançado, materiais raros, recompensas especiais, lore profundo ou Variantes não encontradas.

A primeira observação pode permanecer mesmo que o personagem seja posteriormente Derrotado, desde que a identificação tenha sido validamente registrada antes da derrota.

#### Conhecido

**Conhecido** representa familiaridade suficiente para reconhecer hábitos e características recorrentes.

Além de Observado, pode revelar:

- lore básico;
- descrição ecológica/comportamental;
- habitats já conhecidos;
- tendência geral de combate;
- características ofensivas/defensivas evidentes;
- efeitos recorrentes reconhecíveis;
- materiais comuns conhecidos quando aplicável.

Informações mecânicas permanecem em nível geral quando o conhecimento ainda não justificar detalhes profundos.

#### Estudado

**Estudado** representa compreensão tática consistente.

Além das informações anteriores, pode revelar:

- Artes e comportamentos relevantes;
- principais efeitos aplicados;
- resistências;
- fraquezas;
- imunidades conhecidas;
- respostas especiais a tipos de ação/controle;
- fases ou mecânicas próprias quando aplicável;
- perfil de atributos relevante;
- materiais e recompensas associados;
- lore expandido.

A apresentação pode usar valores exatos, faixas ou descrições qualitativas conforme a natureza da informação e a política de Conteúdo/Balanceamento.

#### Dominado

**Dominado** é o estágio máximo de conhecimento da entrada principal daquela criatura.

Revela todo o dossiê legitimamente disponível naquele momento, incluindo quando aplicável:

- lore completo;
- habitats conhecidos completos;
- perfil de atributos;
- Artes;
- padrões comportamentais;
- fraquezas;
- resistências;
- imunidades;
- mecânicas/condições especiais;
- materiais/recompensas conhecidos;
- observações táticas;
- relações relevantes com o mundo ou outras criaturas.

Dominado nunca ignora spoilers. Não revela automaticamente Variante ainda não descoberta, Local secreto desconhecido, fase narrativa futura, transformação ainda não encontrada, recompensa secreta condicionada ou informação incompatível com `world_state`/`character_narrative_state` do personagem.

#### Habitat

Habitat usa sempre **Região → Local** e mostra apenas Locais legitimamente conhecidos pelo personagem. Descobrir que uma criatura também existe em Local oculto não revela antecipadamente esse Local.

Novos habitats podem ampliar a entrada sem necessariamente alterar seu estágio.

#### Progresso interno

Cada criatura pode possuir progresso interno oculto entre os quatro estágios. A UI **não apresenta barra numérica de progresso** no lançamento.

O backend pode registrar pontos internos, marcos de observação, flags de mecânicas observadas, derrotas válidas, contextos de encontro, Variantes, objetivos e outras evidências previstas pelo Conteúdo.

Valores, thresholds, pesos e combinações estão consolidados na seção 49.

Avanço de estágio não precisa depender exclusivamente de um número. Criaturas podem exigir marcos como observar Arte específica, sobreviver a mecânica, encontrar em mais de um contexto, enfrentar Elite/Variante, concluir investigação por Desbravar ou objetivo narrativo relacionado.

#### Fontes de progresso

Podem conceder conhecimento quando explicitamente elegíveis:

- encontrar/observar pela primeira vez;
- enfrentar em combate;
- derrotar;
- observar Arte/comportamento ainda não registrado;
- sofrer, resistir ou interagir com mecânica relevante;
- Desbravar e resultados investigativos;
- Missão/objetivo relacionado;
- encontrar ou derrotar Elite;
- encontrar Variante;
- Masmorras;
- Chefes;
- mecânicas específicas;
- outras fontes aprovadas de conhecimento.

Uma mesma ação não concede progresso duplicado por callback, reconnect, retry ou processamento repetido.

#### Anti-farming

Repetir indefinidamente o mesmo encontro não deve ser a melhor forma de dominar uma criatura.

O sistema pode utilizar ganho reduzido por repetição, limite por fonte, marcos únicos, bônus por variedade, maior valor para novas mecânicas, Elites, Variantes, exploração e descobertas. Valores e limites estão consolidados na seção 49.

Progresso de Bestiário pode ocorrer sem Vigor porque é conhecimento, não recompensa econômica.

#### Raras, Elites e Chefes

Criaturas raras, Elites e Chefes podem utilizar requisitos próprios e não precisam seguir a mesma curva de repetição de uma criatura comum.

Seu progresso pode privilegiar primeira observação, mecânicas distintas testemunhadas, fases alcançadas, vitória, Primeira Conclusão, investigação, aparições em contextos diferentes e objetivos narrativos. Quantidade/thresholds estão consolidados na seção 49.

#### Variantes

Uma criatura pode possuir entrada principal e uma ou mais Variantes relacionadas.

- Variante permanece completamente ausente até descoberta válida;
- dominar a criatura principal não revela Variante oculta;
- encontrar Variante pode gerar conhecimento para a entrada principal;
- informação exclusiva da Variante mantém registro próprio;
- mecânica exclusiva só aparece depois de legitimamente observada/estudada;
- repetição da mesma Variante não duplica marcos únicos.

Não é obrigatório apresentar quatro estágios independentes para toda Variante. O backend pode manter progresso específico quando necessário e a UI pode apresentá-la como subseção da criatura principal. Variante suficientemente distinta pode ser conteúdo definido como entrada própria.

#### Permanência

Estágio e conhecimento do Bestiário são permanentes por personagem e persistem através do Legado.

Adicionar posteriormente novas informações/Variantes não rebaixa o estágio já obtido; novo conteúdo permanece sujeito às próprias regras de descoberta.

No lançamento, Bestiário não concede atributos diretos de combate; foco em conhecimento, lore, mecânicas, Feitos e prestígio.

### 33.2 Códice de Asterion

#### Função

O **Códice de Asterion** é o registro persistente do conhecimento narrativo e histórico legitimamente adquirido pelo personagem durante sua jornada.

Registra conhecimento sobre:

- Asterion e sua cosmologia;
- Regiões e Locais;
- povos e culturas;
- facções e instituições;
- figuras históricas ou narrativamente relevantes;
- acontecimentos passados/presentes;
- fenômenos;
- mistérios e Segredos descobertos;
- história revelada pela Campanha;
- conhecimento obtido durante Crônicas;
- outras descobertas explicitamente definidas pelo Conteúdo.

O Códice representa **aquilo que o personagem aprendeu**, não todo o conhecimento existente no banco do jogo. Não é uma wiki onisciente; novas descobertas podem ampliar, contextualizar ou reinterpretar conhecimento anterior.

#### Categorias oficiais

1. **Mundo e Cosmologia**;
2. **Regiões e Locais**;
3. **Povos e Facções**;
4. **Figuras**;
5. **História e Acontecimentos**;
6. **Mistérios e Fenômenos**;
7. **Crônicas**.

Entradas/grupos cuja própria presença constituiria spoiler permanecem ausentes até a descoberta legítima correspondente. Nenhuma categoria revela quantidade total de Entradas ou conteúdo ainda oculto.

#### Entradas e Trechos

Uma **Entrada de Códice** representa um assunto conhecido. Pode ser revelada integralmente por uma descoberta, receber novos **Trechos** ao longo da progressão, possuir subseções internas quando necessário e ser ampliada por fontes diferentes.

Os Trechos são unidades discretas de conhecimento; backend pode usar `codex_fragment`, `codex_section` ou equivalente. A UI não precisa utilizar a palavra “fragmento”.

#### Descoberta parcial

Uma Entrada parcialmente conhecida mostra **somente o conteúdo legitimamente descoberto**.

Conteúdo desconhecido:

- não aparece como `???`;
- não ocupa espaço reservado;
- não aparece como seção bloqueada/silhueta;
- não mostra título antecipado;
- não mostra contador;
- não contribui para porcentagem visível;
- não informa que existe outro Trecho esperando descoberta.

Uma Entrada pode parecer completa segundo o conhecimento atual e receber novas informações depois.

O Códice não utiliza barra/porcentagem pública de conclusão e não exibe contagens como “42/80 Entradas”, “3/7 Segredos” ou percentual por Região.

#### Fontes de conhecimento

Uma Entrada/Trecho pode ser descoberto por fontes explicitamente configuradas, incluindo:

- Desbravar;
- Missões principais e Missões Secundárias;
- Campanha;
- capítulos/objetivos de Crônica;
- eventos narrativos;
- descoberta de Região/Local;
- Profundezas;
- Segredos;
- Masmorras;
- Primeira Conclusão quando aplicável;
- encontros/fases de Chefe;
- Eventos Mundiais;
- interações narrativas;
- objetos, inscrições, documentos ou vestígios previstos pelo Conteúdo;
- outras fontes aprovadas.

Nem toda atividade precisa atualizar o Códice; a atualização existe apenas quando contém conhecimento específico definido pelo Conteúdo.

#### Relação com Desbravar

Desbravar é uma das principais fontes de Códice. Um resultado pode criar Entrada nova ou acrescentar Trecho a Entrada existente, revelar informação sobre Local, acontecimento histórico, fenômeno, facção, figura, Segredo, Campanha ou Crônica.

Uma tentativa já resolvida não concede novamente o mesmo conteúdo por reconnect, callback, recovery ou repetição da request.

#### Relação com Campanha e Missões

Campanha/Missões podem criar ou atualizar Códice quando o conhecimento narrativo correspondente for legitimamente adquirido.

Missões continuam responsáveis por objetivo atual, progresso, requisito, recompensa e estado ativo/concluído. O Códice preserva o **conhecimento** adquirido através delas e não substitui o Diário de Missões.

Concluir, abandonar ou reaceitar Missão Secundária não duplica Trechos já obtidos. Conhecimento permanente não é removido porque uma missão deixa de estar ativa.

#### Relação com Crônicas

Crônicas podem criar ou atualizar Entradas/Trechos conforme o progresso pessoal. O conhecimento pode permanecer como registro histórico depois do ciclo.

Isso não reabre capítulo, votação, objetivo sazonal, pontos, Passe, economia ou recompensa encerrada. A categoria Crônicas registra conhecimento narrativo; não substitui a interface ativa da Crônica.

#### Relação com Mapa

O **Mapa** é responsável por posição, geografia, Regiões/Locais conhecidos, acesso, caminhos, Braseiros, navegação e deslocamento.

O **Códice** é responsável por história, contexto, acontecimentos, cultura, fenômenos e conhecimento aprendido sobre esses lugares.

Descobrir uma Entrada sobre um Local não concede automaticamente acesso físico. Local secreto desconhecido não é revelado apenas porque uma Entrada relacionada existe internamente.

#### Relação com Bestiário

O Bestiário é o sistema especializado em criaturas: identificação, Habitat, comportamento combatente, Artes, atributos, resistências, fraquezas, imunidades, mecânicas, materiais/recompensas e Variantes.

O Códice pode mencionar criaturas como parte da história/ecologia, mas não replica o dossiê mecânico. UI futura pode navegar entre referências já descobertas sem duplicar dados.

#### Eventos, Chefes e Masmorras

Eventos Mundiais podem acrescentar acontecimento, causas/consequências conhecidas e contexto narrativo ao Códice sem duplicar `occurrence_id`, participação ou recompensa.

Masmorras/Chefes podem conceder conhecimento através de descoberta, progressão interna, elemento narrativo, Primeira Conclusão, fase, vitória ou Segredo. O Conteúdo define o momento exato.

Informação observada antes de uma derrota pode persistir quando explicitamente definida como descoberta válida; informação que exige vitória/conclusão só é concedida depois da condição correspondente. Retry não repete Trechos já registrados.

#### Segredos e política de spoilers

Conteúdo condicionado permanece completamente ausente antes da descoberta válida, incluindo quando aplicável Locais secretos, Profundezas, Masmorras secretas, Segredos, Fraturas, Avesso, figuras desconhecidas, transformações de Chefe, acontecimentos futuros, verdades por trás de mistérios e consequências futuras de Campanha/Crônica.

Não mostrar título oculto, espaço reservado, contador, ícone bloqueado, seção cinza, `???` ou texto que revele que algo específico ainda existe para descobrir.

O próprio nome da Entrada não aparece antes de ser legitimamente conhecido.

`world_state`, `character_narrative_state`, Campanha, Crônica e flags de descoberta determinam elegibilidade. Estado global atual nunca revela ao personagem conhecimento que sua progressão pessoal ainda não permite conhecer.

#### Modelo de progressão

O Códice **não possui barra genérica de conhecimento**.

O progresso ocorre pela aquisição de Entrada, Trecho, descoberta ou flag narrativa específica. Caso um conteúdo precise de múltiplas evidências para liberar determinado Trecho, o progresso técnico pode permanecer oculto; valores/thresholds estão consolidados na seção 49.

#### Permanência

Entradas e Trechos legitimamente descobertos são permanentes por personagem e persistem através do Legado.

Não são removidos por derrota, Vigor zero, troca de Caminho/Guilda, encerramento de Crônica ou Legado. Conteúdo temporário pode desaparecer do mundo sem apagar o registro histórico já adquirido.

#### Conteúdo adicionado posteriormente

Patch que adiciona novos Trechos a Entrada conhecida:

- preserva Trechos antigos;
- mantém Trechos novos ocultos até a própria condição de descoberta;
- não informa ao jogador que conteúdo desconhecido adicional passou a existir.

Correção editorial/técnica de conhecimento já conhecido pode ser migrada/versionada para personagens elegíveis. Conteúdo narrativo genuinamente novo não é concedido retroativamente só porque a Entrada principal já era conhecida.

IDs de Entrada/Trecho não são reutilizados para conteúdos diferentes.

#### Recompensas e Feitos

A função principal do Códice é **conhecimento, lore e descoberta**.

Não concede atributos de combate nem cria economia repetível própria.

Descobertas específicas podem desbloquear Feitos, Títulos/prestígio, requisitos de conteúdo ou recompensa única controlada quando explicitamente prevista. Não existe recompensa genérica por porcentagem de Códice, número total de Entradas ou “completar todas as páginas”.

Feitos relacionados a Segredos permanecem ocultos até obtenção válida.

#### Idempotência

Conhecimento é registrado pelo backend com chave idempotente apropriada, conceitualmente semelhante a:

`character_id + codex_entry_id + codex_fragment_id`

ou estrutura equivalente.

O mesmo Trecho não pode ser registrado duas vezes por callback, reconnect, retry, troca de dispositivo, processamento duplicado, restart do Bot ou reexecução de job.

Quando descoberta de Códice também concede recompensa, registro do conhecimento e entrega da recompensa são componentes distintos/idempotentes do mesmo evento quando apropriado. Falha de entrega física não desfaz conhecimento legitimamente adquirido.

### 33.3 Feitos e Títulos

Categorias de Feitos incluem exploração, combate, PvE, PvP, Guilda, Ofícios, Crônicas, Bestiário e Segredos.

- Feito oculto não aparece antes de desbloqueado.
- Feitos podem conceder Títulos, Aparências, Molduras e prestígio conforme definição do Conteúdo.
- Cosmético secreto/recompensa oculta não é revelado antecipadamente quando isso constituir spoiler.
- Um Feito pode não conceder Cosmético; seu registro permanente já constitui uma recompensa de prestígio.
- A remoção de uma recompensa cosmética não remove nem invalida o Feito correspondente.
- Feito legitimamente obtido continua permanentemente registrado e não é removido porque conteúdo adicional foi adicionado depois.

#### Títulos

Títulos são elementos de identidade, prestígio e apresentação do personagem.

- O personagem pode possuir múltiplos Títulos desbloqueados.
- Apenas **1 Título pode ser equipado por vez**.
- Equipar/trocar Título não altera atributos, poder, economia ou mecânicas de combate.
- A tela player-facing chama-se **Títulos**.
- O termo oficial player-facing é **Título**; nomes técnicos/backend anteriores podem permanecer internamente quando conveniente.

### 33.4 Cosméticos do Personagem

**Cosméticos** é o hub player-facing de apresentação visual do personagem.

Hierarquia oficial:

1. 🧍 **Aparência · Visual**
2. 🎖️ **Título · Identidade**
3. 🖼️ **Moldura · Perfil**

Cosméticos não são Equipamentos, não ocupam slots de equipamento e não alteram atributos, HP, ATQ/DEF, XP, Renome/MMR, Vigor, economia, drops, Configuração de Combate ou qualquer vantagem de gameplay.

Cada categoria continua obedecendo às próprias regras de desbloqueio/disponibilidade/seleção. No Perfil, a apresentação pública pode usar Aparência, Título e Moldura conforme o contexto.

#### Valor e distribuição das recompensas

- **Aparência** é o cosmético visual de maior impacto e deve permanecer relativamente rara, principalmente para grandes marcos, domínio amplo, Feitos excepcionais, Crônicas, Patrono e prestígio máximo.
- **Título** é o principal cosmético textual/de identidade e pode aparecer com maior frequência em exploração, Chefes, Bestiário, descobertas, Feitos narrativos, marcos intermediários, PvP, Crônicas, prestígio, Chamado e Patrono.
- **Moldura** é o principal cosmético visual de prestígio associado ao Perfil, indicada para dificuldades elevadas, Masmorras, domínio, PvP relevante, conclusão regional, grandes marcos, Crônicas, Patrono e prestígio.
- Não há quota fixa de cosméticos por Feito ou Região. Regiões futuras podem conceder Título, Moldura, Aparência ou nenhum Cosmético; as contagens das Regiões já revisadas não são uma fórmula para conteúdo futuro.
- Não conceder recompensa econômica, Cosmético ou outra recompensa automática apenas para compensar uma remoção. Não existe conversão obrigatória um a um.

#### Migração de recompensas cosméticas legadas

Recompensas antigas da categoria **Emblema** podem tornar-se Títulos quando sua identidade funcionar naturalmente como expressão textual do personagem; nos demais casos, podem deixar de existir como recompensa cosmética. Recompensas antigas da categoria **Banner** podem tornar-se Molduras quando representarem prestígio visual relevante; nos demais casos, podem deixar de existir. Aparência não é substituta automática. Não criar uma categoria cosmética equivalente com outro nome.

#### Aparência

**Aparência** é o visual cosmético principal do personagem e a nomenclatura oficial player-facing.

- Todo personagem possui sempre uma **Aparência padrão válida**.
- Apenas Aparências legitimamente desbloqueadas podem ser selecionadas.
- A Aparência selecionada persiste entre sessões.
- Seleção/troca é server-side e idempotente.
- Trocar Aparência não altera, move, consome ou substitui Equipamentos.
- Aparência é independente dos 8 slots de Equipamento e não faz parte da Configuração de Combate.
- Aparências podem ser obtidas por Feitos, Crônicas, Trilha/Passe da Crônica, Patrono de Asterion, Eventos, aquisição cosmética ou outras fontes explicitamente definidas.
- Aparências pagas seguem as regras de entitlements cosméticos.
- Aparências/colecionáveis não precisam existir como itens físicos no Inventário.

No lançamento:

- não existem Aparências cosméticas de armas;
- não existem Aparências cosméticas individuais de peças de Equipamento.

#### Entitlements e fallback

Cosméticos adquiridos como entitlement:

- são registrados no backend como desbloqueios/colecionáveis;
- não ocupam espaço de Inventário;
- não são perdidos por descarte de item;
- seguem o escopo definido pelo entitlement.

Cosméticos pagos continuam, por padrão, não negociáveis, fora do Mercado/Troca Direta e account-wide entre servidores futuros salvo produto explicitamente `server-bound`.

A seleção equipada é estado separado do direito de possuir o Cosmético.

Se entitlement temporário expirar, for validamente revogado ou deixar de estar disponível, o sistema aplica fallback para opção válida; na ausência de alternativa válida, utiliza o padrão da categoria. Para Aparência, a Aparência padrão garante que o personagem nunca fique sem visual válido. Fallback é autoritativo/idempotente.

#### Persistência

O backend preserva separadamente:

- Cosméticos desbloqueados;
- entitlements correspondentes;
- Aparência selecionada;
- Título equipado;
- Moldura selecionada, quando aplicável;

Seleções válidas persistem entre sessões e através do Legado.

## 34. Calendário, reset e tempo

- Reset diário: **06:00, America/Sao_Paulo**.
- Nova Vigília semanal: **segunda-feira, 06:00, America/Sao_Paulo**.
- Backend usa timezone `America/Sao_Paulo`, não UTC-3 fixo.
- `cycle_id` é capturado no início da atividade.
- Atividade que atravessa reset termina dentro do ciclo original quando a regra permitir.
- Reset/ciclo é calculado logicamente pela data/hora; não depende de job rodar exatamente às 06:00.
- Scheduler serve para notificações/manutenção/tarefas, não para “fazer o dia existir”.
- Tempos relevantes usam relógio autoritativo do servidor.
- Há distinção entre **wall-clock** (Loja, sanção, exclusão, claim etc.) e **gameplay-clock**.
- Evitar buffs importantes de combate baseados em “30 minutos reais” no lançamento quando possível.

## 35. Monetização

- Monetização: **Passe da Crônica + Patrono de Asterion + Cosméticos**.
- Sem P2W: nada de XP, Coroas, drop, Vigor, Poções, Equipamentos, Runas, materiais, tentativas, Renome/MMR, Legado, votos ou vantagem em Batalha de Guildas/Arena da Vigília por pagamento.
- **Trilha da Crônica**: progressão única com Marcos Livres e Premium; Livre e Premium usam os mesmos pontos; não existe compra de níveis, Marcos ou progresso.
- O **Passe da Crônica** libera exclusivamente a camada Premium; compra durante a Crônica libera retroativamente recompensas Premium dos Marcos já alcançados.
- Recompensas Premium da Trilha são exclusivamente cosméticas, colecionáveis ou de prestígio e nunca concedem vantagem econômica, de progressão ou combate.
- Cosméticos/recompensas pagas são não negociáveis e não entram em Mercado/Troca Direta.
- Por padrão, cosméticos pagos são **account-wide entre servidores futuros**, salvo produto explicitamente `server-bound`.
- Cosméticos pagos são entitlements/colecionáveis, não itens físicos de Inventário.
- Podem incluir **Aparência, Título e Moldura**.
- Selecionar/equipar Cosmético não consome o entitlement.

### 35.1 Patrono de Asterion (Supporter Asterion)

- Produto exclusivamente de apoio/cosmético.
- Enquanto ativo, concede o Título temporário **Patrono das Cinzas** e a Moldura temporária **Vigília do Patrono**, além de reconhecimento visual genérico que não constitua uma nova categoria cosmética.
- Pode ser assinatura ou outro formato compatível com a plataforma.
- Cada benefício declara `permanent_entitlement` ou `subscription_entitlement`.
- Ao expirar entitlement temporário, seleção ativa cai para alternativa válida/padrão da categoria conforme a seção 33.4.
- Refund/reversal remove apenas entitlements correspondentes às linhas realmente revertidas; histórico permanece auditável.

### 35.2 Pagamentos

- Cada transação externa usa `payment_id` único e idempotente.
- Webhook precisa ser autenticado/verificado segundo o provedor antes do processamento.
- Estados como `paid`, `refunded`, `reversed` são preservados.
- Revogação de entitlement é operação auditada, nunca apagar compra silenciosamente.
- Após restore de backup, sistema reconcilia webhooks/pagamentos antigos sem duplicar entitlement.
- Políticas específicas da plataforma digital/Telegram devem ser verificadas no momento da implementação.

## 36. Múltiplas contas e antiexploit

- Múltiplas contas Telegram são permitidas, inclusive pagantes.
- É proibido usar contas próprias simultaneamente para multiplicar recompensas, ocupar vagas artificialmente ou manipular competição/economia.
- Exemplos proibidos: mesmo Grupo/Masmorra/Caçada/Juramento/frente de Batalha de Guildas, contas enfrentando-se deliberadamente na Arena da Vigília, manipulação de voto, contribuição artificial, boosting e RMT.
- Jogar contas diferentes separadamente é permitido.
- Relação/IP por si só não prova culpa.
- Detecção gera flags e análise; não ban automático apenas por associação.

## 37. Bot Telegram e UX

### 37.1 Comandos

Conjunto mínimo:

- `/start`
- `/menu`
- `/perfil`
- `/ajuda`
- possivelmente `/cancelar`

### 37.2 Menu principal

Núcleo:

- **Aventura**.
- **Personagem**.
- **Guilda**.
- **Mercado**.
- **Códice**.
- **Calendário**.

Demais entradas diretas:

- **Vínculos** (Social).
- **Classificação da Vigília**.
- **Benefícios**.
- **Comunidade**.
- **Configurações**.

**Classificação da Vigília** é a entrada player-facing direta para o leaderboard competitivo atual. O **Salão da Vigília** permanece como histórico competitivo e é acessado a partir da Classificação da Vigília. **Comunidade** é entrada direta e permanente do Menu Principal. Não existe hub genérico **Mais** destinado a esconder essas entradas.

Aventura: Mapa, Missões, Caçadas, Masmorras, **Desbravar** (Explorar), Eventos Mundiais, PvP.

Não existe entrada genérica permanente **Continuar** dentro de Aventura. Quando houver atividade Foreground persistente/interrompida que exija retomada, a interface apresenta uma ação contextual e específica da própria atividade, como **Retomar Masmorra**, **Retomar Combate** ou **Retomar Ronda**, conforme as regras autoritativas da seção 39. `/start`, `/menu`, reconstrução da interface, reconnect e troca de dispositivo continuam priorizando a atividade Foreground vigente quando necessário.

Personagem: **Inventário**, **Equipamentos**, **Artes** (Skills), **Doutrinas** (Builds), **Talentos**, **Atributos**, **Ofícios** (Profissões), **Cosméticos**, **Perfil**, **Caminho** (Subclasse), **Legado**.

Entrada de Personagem para apresentação visual:

> 🎨 **Cosméticos · Aparência**

Dentro de **Personagem → Cosméticos**:

1. 🧍 **Aparência · Visual**
2. 🎖️ **Título · Identidade**
3. 🖼️ **Moldura · Perfil**

Mercado: **Buscar Loja, Minha Loja, Troca Direta**. Serviços públicos são acessados dentro da Loja Pessoal do artesão; descoberta global por item/categoria e Favoritos de Loja não fazem parte do modelo de lançamento.

#### Resumo contextual do Menu Principal

O Menu Principal pode consultar estados já autoritativos do personagem para apresentar um resumo contextual, quando aplicável, incluindo **Região e Local atuais, HP, Vigor, XP, Missão Principal atual, Missão Secundária acompanhada, objetivo pessoal/relevante da Crônica atual e progresso de Evento Mundial relevante**.

Essas informações são somente apresentação de estados já existentes e não criam novas mecânicas. Quando uma informação não for aplicável, a interface pode omiti-la. Layout, barras, emojis, lore, ordem gráfica e quantidade de linhas pertencem à Fonte de Visual/UI.

#### Benefícios

**Benefícios** centraliza sistemas de recompensa, apoio e campanhas que não pertencem naturalmente a Configurações ou Calendário.

Conteúdo do menu:

- **Dádiva Diária** (Login Diário).
- **Trilha da Crônica / Passe da Crônica**.
- **Patrono de Asterion** (Supporter Asterion).
- **Chamado de Asterion** (Recrutamento / Indicações).
- **Códigos de Asterion** (Códigos Promocionais).

Regras:

- Códigos de Asterion são acessados por Benefícios e não ficam escondidos em Configurações.
- Calendário continua responsável por ciclos, horários, Nova Vigília, Crônica e atividades programadas.
- Configurações permanece responsável por preferências e pelos fluxos de **Notificações**, **Ajuda** e **Conta**. **Comunidade não pertence a Configurações**; Ajuda pode apenas referenciá-la contextualmente.
- **Configurações → Conta** é reservado a: 1 ✏️ **Renomear Personagem · Identidade**; 2 🗑️ **Excluir Personagem · Exclusão**.
- Aparência e demais Cosméticos ficam exclusivamente em **Personagem → Cosméticos**, não em Conta.
- Benefícios não cria novas vantagens de gameplay além das permitidas pelas regras já estabelecidas de monetização e engajamento.
- Dádiva Diária, Trilha/Passe da Crônica, Patrono de Asterion, Chamado de Asterion e Códigos de Asterion continuam obedecendo às regras específicas das respectivas seções do GDD.
- A mudança é de navegação/UX e não modifica regras econômicas, de progressão ou monetização.

### 37.3 Princípios

Cada tela deve responder:

- Onde estou?
- O que está acontecendo?
- O que posso fazer agora?

Preferências:

- editar a mesma mensagem quando possível;
- listas paginadas;
- botões contextuais;
- cerca de 4–8 ações por tela como alvo de legibilidade.

O **Menu Principal** é uma exceção consciente a esse alvo por funcionar como hub global do jogo e pode manter todas as entradas diretas definidas na seção 37.2. Essa exceção não autoriza aumentar indiscriminadamente a quantidade de ações nas demais telas nem cria obrigação de agrupar o Menu Principal em submenus artificiais.

Paginação nunca usa posição como identidade; botões carregam ID estável + contexto/versão.

Mensagem apagada pelo usuário não apaga atividade. `/start`/`/menu` reconstrói a interface a partir do backend.

`ui_session` é separada de `game_activity`; menu expirado não encerra atividade real.

- Pode haver diferentes `ui_session` ou mensagens visíveis em dispositivos distintos, mas todas representam o mesmo personagem e consultam a mesma `game_activity` autoritativa.
- Se existir atividade Foreground que exija retomada, `/start`, `/menu`, mensagens reconstruídas, deep links e acessos por outro dispositivo priorizam o contexto dessa atividade.
- Mensagem apagada, interface expirada, reconnect ou mudança de dispositivo nunca encerram atividade nem liberam Configuração de Combate.
- Telas auxiliares de consulta podem ser permitidas sem se transformar em fluxos independentes de mutação.

Notificações podem ser separadas por Essenciais, Eventos, PvP/Batalha de Guildas, Guilda, Mercado e Crônica.

- Telas predominantemente funcionais devem priorizar legibilidade, dados mecânicos e ações disponíveis. Flavor Text nunca deve competir com informação necessária para tomada de decisão.
- Telas de exploração e narrativa podem dedicar proporcionalmente mais espaço à ambientação quando isso não prejudicar navegação e compreensão.
- Flavor Text é complementar e não substitui diálogos, cenas narrativas, descrições formais de conteúdo, entradas do Códice, objetivos de missão ou outras fontes oficiais de informação.

### 37.4 Flavor Text Contextual

A interface do Telegram pode apresentar pequenos textos narrativos e atmosféricos, denominados **Flavor Text**, para reforçar identidade, lore, ambientação e sensação de mundo.

Flavor Text é uma **camada de apresentação**. Por si só, não altera `world_state`, `character_narrative_state`, progressão, economia, combate, missões ou qualquer outro estado oficial do jogo.

#### 37.4.1 Flavor de Sistema

Usado principalmente em telas funcionais, como Personagem, Inventário, Equipamentos, Artes/Skills, Talentos, Doutrinas/Builds, Ofícios/Profissões, Legado, Mercado, Guilda, Benefícios e sistemas semelhantes.

- Deve ser curto, normalmente em torno de **2 linhas**.
- Pode ser fixo ou utilizar um pequeno conjunto de variações previamente aprovadas.
- Não deve empurrar informações mecânicas importantes para fora da área principal.
- Não deve criar etapas adicionais de navegação apenas para apresentar ambientação.
- Em caso de conflito entre atmosfera e clareza mecânica, **clareza mecânica tem prioridade**.

#### 37.4.2 Flavor Narrativo/Contextual

Usado principalmente em Aventura, Mapa, Regiões, Locais, Desbravar/Exploração, Braseiros, Masmorras, Eventos Mundiais e outros contextos fortemente ligados ao mundo.

- Pode possuir aproximadamente **4–5 linhas curtas** quando isso melhorar a ambientação.
- Pode abordar atmosfera, história conhecida, rumores, sinais ambientais, estado atual do Local, consequências narrativas já conhecidas, percepção do personagem e mudanças provocadas por acontecimentos oficiais.
- Um mesmo Local, Região ou contexto pode possuir um **banco de múltiplos Flavor Texts**.

#### 37.4.3 Elegibilidade contextual e spoilers

O conjunto de Flavor Texts elegíveis pode depender de condições oficiais já existentes, incluindo:

- Região;
- Local;
- progresso da Campanha;
- progresso da Crônica;
- descobertas realizadas;
- segredos conhecidos;
- estado de Evento Mundial;
- `world_state`;
- `character_narrative_state`;
- outros estados oficiais relevantes.

Regras:

- Flavor Text **nunca pode revelar informação que o personagem ainda não deveria conhecer**.
- Continuam protegidos antes da descoberta: Avesso, Locais secretos, criaturas ocultas, transformações de Chefe/Boss, resultados futuros de decisões, segredos e qualquer conteúdo narrativo ainda não alcançado.
- Conteúdo secreto continua ausente antes da descoberta; Flavor Text não pode ser usado como atalho para antecipá-lo.
- Um Flavor pode evoluir conforme o conhecimento do personagem. Antes de uma descoberta, pode mencionar sinais ambientais sem nomear sua origem; depois da descoberta, pode fazer referência direta ao conhecimento legitimamente adquirido.

#### 37.4.4 Seleção e estabilidade

- Quando houver várias entradas válidas, o backend pode selecionar Flavor Text aleatoriamente, por peso, por prioridade contextual ou por combinação dessas regras.
- A seleção **não é refeita a cada clique, paginação ou simples atualização da mesma tela**.
- Uma vez escolhido para determinado contexto/sessão narrativa, o Flavor permanece estável até ocorrer gatilho válido de renovação, como mudança de Local, novo acesso posterior, mudança relevante de estado, descoberta importante, alteração de Campanha/Crônica, início/fim de Evento ou outro gatilho configurado.
- Se uma mudança de estado tornar o Flavor atual inelegível ou potencialmente spoiler, ele é substituído por uma entrada válida.
- Reconstrução visual da mesma tela pelo Bot não causa reroll por si só.

#### 37.4.5 Autoria, canon e versionamento editorial

- Todo Flavor Text do lançamento pertence a um **banco de textos previamente escritos e aprovados**.
- Não será utilizada geração livre de IA em tempo real como fonte canônica de Flavor Text no lançamento.
- Todo Flavor deve respeitar a lore oficial e utilizar somente fatos, personagens, eventos e relações autorizados.
- Flavor não pode inventar acontecimentos canônicos nem transformar atmosfera, percepção ou rumor em fato oficial sem autorização narrativa.
- Rumores podem ser apresentados como rumores, suspeitas ou percepção subjetiva quando essa for a intenção do conteúdo.

#### 37.4.6 Relação com outros conteúdos

Flavor Text não substitui:

- diálogos;
- cenas;
- missões;
- textos de NPC;
- Códice;
- Bestiário;
- descrições formais de itens/conteúdo;
- objetivos;
- tutoriais;
- História do Personagem escrita pelo jogador.

Ele serve exclusivamente como reforço contextual e atmosférico.

## 38. Barras e UI de combate

Referência de apresentação:

- HP: `❤️ 842/1.180` + barra de 10 blocos, mudando visualmente por faixa de HP.
- XP: barra azul.
- Vigor: barra amarela.
- Combatente: Nome / HP numérico / barra / linha de efeitos 1 / linha de efeitos 2.
- Efeitos devem permanecer visíveis no corpo principal, com cerca de 2 linhas por combatente quando possível.
- Efeitos coletivos podem ser separados.
- `☣️` Veneno; `💀` Derrotado.
- Labels usam espaços: `⬇️ DEF 2T`; stacks anexados: `🩸² 2T`.
- Imagem inimiga estática; troca apenas em transformação importante de Chefe/Boss.
- Deve ser testado em Telegram iOS, Android e Desktop.
- Backend é fonte de verdade; Telegram é apresentação.
- Durante combate ativo, informação mecânica possui prioridade absoluta sobre Flavor Text. Flavor narrativo pode aparecer em introduções, transições, chegada de Chefe/Boss ou momentos explicitamente preparados, mas não deve ocupar o espaço necessário para HP, efeitos, turnos e ações.

## 39. Atividade Autoritativa, Foreground/Background e Integridade da Configuração de Combate

### 39.1 Foreground e Background

Cada personagem pode possuir no máximo **uma atividade Foreground incompatível ativa por vez**.

Exemplos de Foreground incluem:

- combate ativo;
- Caçada;
- Ronda de Caça;
- Desbravar ativo;
- Masmorra;
- Arena da Vigília;
- Batalha de Guildas;
- Duelo;
- tentativa ativa de Juramento;
- participação ativa em Evento Mundial quando o conteúdo exigir compromisso Foreground;
- Troca Direta em confirmação;
- Confirmação de Entrada;
- outros fluxos explicitamente classificados como Foreground.

Estados Foreground incompatíveis não podem coexistir.

Atividades Background incluem, entre outras:

- Expedição assíncrona;
- listings da Loja;
- Serviços;
- Obras da Guilda;
- progresso de Crônica;
- outros compromissos explicitamente classificados como Background.

Atividade Background não cria uma segunda sessão jogável do personagem e não contorna restrições da atividade Foreground.

Ações de consulta sem mutação podem permanecer disponíveis quando forem compatíveis com o conteúdo ativo. Consultar informações não concede permissão para alterar estado bloqueado.

A atividade Foreground ativa é estado persistido do jogo no backend e não pertence a uma mensagem, aparelho ou sessão visual do Telegram.

### 39.2 Travamento Global da Configuração de Combate

Todo conteúdo de combate declara o momento em que adquire e libera seu **lock de Configuração de Combate**.

Durante qualquer encontro de combate já iniciado, a Configuração de Combate permanece travada até a resolução válida do encontro ou até ponto de reconfiguração explicitamente definido pelo conteúdo.

Conteúdos estruturados podem manter o lock por período maior que um encontro, como toda uma run, lote, tentativa, participação competitiva ou sequência de fases.

Enquanto o lock estiver ativo, nenhuma ação do jogador pode alterar sua Configuração de Combate efetiva.

O lock abrange, no mínimo:

- Equipamentos equipados nos 8 slots;
- Arma Principal e Arma Secundária;
- equipar/desequipar item;
- Runas instaladas nos equipamentos utilizados;
- inserção, extração ou substituição de Runa;
- Encantamentos dos equipamentos utilizados;
- aplicação/substituição de Encantamento;
- upgrade, reroll, Serviço ou outra modificação que altere propriedades combatentes dos equipamentos utilizados;
- Caminho;
- distribuição de Talentos;
- 3 Artes Ativas e seus slots;
- carregamento/troca de Doutrina;
- preparação/autorização de Consumíveis apenas quando o conteúdo possuir preparação prévia explícita, como a Ronda de Caça; Consumíveis do PvE manual não entram no lock como seleção preparada;
- qualquer outra escolha mutável capaz de alterar atributos, Artes disponíveis, passivas derivadas ou configuração efetiva de combate.

O lock não congela mudanças sistêmicas legítimas que não sejam escolhas configuráveis do jogador, como dano recebido, efeitos, consumo de recursos, progressão autorizada entre encontros ou outros estados produzidos pelas regras do próprio conteúdo.

Uma atividade que permita reconfiguração deve possuir **ponto de reconfiguração explícito**. Apenas esse ponto pode suspender/substituir o lock conforme as regras daquele conteúdo.

Sair da tela, apagar mensagem, usar `/start`, `/menu`, abrir outra mensagem, deep link, trocar de dispositivo, fechar Telegram, desconectar ou reconectar **não libera o lock**.

O lock somente termina por transição válida de estado da atividade.

### 39.3 Snapshot da Configuração de Combate

Ao adquirir um lock, a atividade registra representação autoritativa da Configuração de Combate utilizada.

O snapshot contém ou referencia, conforme a arquitetura:

- personagem e atividade;
- `combat_id`, `encounter_id`, `run_id`, `occurrence_id` ou identificador aplicável;
- Equipamentos e `item_instance_id` utilizados;
- estado/versionamento relevante desses equipamentos;
- Runas;
- Encantamentos;
- Caminho;
- Talentos;
- Artes Ativas e slots;
- preparação/autorização de Consumíveis quando aplicável a conteúdo automatizado ou outro fluxo que a exija explicitamente;
- limite e contador autoritativos de usos de Consumíveis quando o conteúdo manual possuir orçamento próprio, como Masmorras;
- versão da Configuração de Combate;
- `ruleset_version`;
- demais dados necessários à reprodução/validação da configuração autorizada.

Itens pertencentes a Configuração travada não podem sofrer mutações incompatíveis enquanto o lock estiver ativo. Isso inclui, quando aplicável, modificar/aprimorar/rerrolar, extrair/substituir Runa, substituir Encantamento, desmontar, negociar, colocar em Loja, entregar a Serviço incompatível ou remover da configuração por outro fluxo.

O snapshot não cria cópias econômicas dos itens e não altera ownership; apenas registra/protege o estado usado pela atividade.

### 39.4 Sincronização Multidispositivo e Atividade Autoritativa

Uma conta/personagem é **um único ator lógico**, independentemente de quantos dispositivos ou clientes Telegram estejam abertos.

Não existe “personagem do celular”, “personagem do computador”, sessão combatente independente por dispositivo ou Menu paralelo com autoridade própria.

Todos os dispositivos consultam e interagem com o **mesmo estado persistido e autoritativo**.

Enquanto existir atividade Foreground ativa:

- qualquer dispositivo detecta essa atividade;
- o Bot apresenta ou permite retomar o contexto atual;
- abrir o Bot em outro dispositivo não cria nova atividade;
- trocar de dispositivo não reinicia, duplica ou encerra atividade;
- a Configuração de Combate travada permanece a mesma;
- HP, efeitos, turno, rodada, participantes, progresso e demais estados continuam os mesmos;
- ações incompatíveis são rejeitadas no backend.

`/start` e `/menu`, durante atividade Foreground que exija retomada, devem reconstruir prioritariamente o estado dessa atividade ou apresentar tela contextual de retomada, e não criar Menu independente capaz de contornar restrições.

Uma ação como **Retomar Masmorra**, **Retomar Combate**, **Retomar Ronda** ou equivalente pode ser usada quando melhorar a UX, mas nunca representa segunda sessão de jogo.

O dispositivo secundário pode assumir a interação com a atividade atual normalmente, utilizando o mesmo estado autoritativo.

### 39.5 Consultas durante atividade ativa

O lock não exige bloquear toda leitura do jogo.

Conteúdos estritamente consultivos podem continuar disponíveis quando seguros, por exemplo Códice, Bestiário, informações do personagem, Calendário e regras da atividade.

Essas telas são apenas visualizações auxiliares e não substituem a atividade Foreground ativa. Uma interface de consulta nunca concede autoridade para executar mutação proibida no contexto atual.

A política final de quais consultas ficam acessíveis durante cada atividade pertence a UX/Implementação, não a Balanceamento.

## 40. Travessia dos Braseiros (Fast Travel)

- **Travessia dos Braseiros** normal funciona de **Braseiro permanente do mundo → Braseiro permanente do mundo**.
- O personagem precisa estar em Braseiro permanente válido para usar a rede, salvo exceção explícita.
- Em Grupo, viagem é individual por padrão; Líder não teleporta os demais.
- Travessia é bloqueada durante combate, fila, instância, Troca Direta ativa, narrativa bloqueadora ou atividade que exija permanência.
- Braseiro permanente inválido por patch usa fallback: último Braseiro válido → hub da Região → hub global seguro.
- Descansar/renascer em Braseiro permanente restaura HP a 100% e remove estados comuns de combate.
- Braseiro permanente não restaura Vigor, Consumíveis, tentativas, limites diários ou economia.
- **Desbravar pode ser uma forma orgânica de descobrir Braseiros permanentes do mundo.** A descoberta é registrada de forma idempotente e só integra a rede quando todos os requisitos aplicáveis estiverem satisfeitos.
- **Braseiros de Masmorra são explicitamente excluídos da Travessia dos Braseiros.**
- Braseiro de Masmorra pertence exclusivamente à `run_id`, não é registrado como destino permanente, não permite entrada externa na Masmorra, não permanece após a run e não altera os Braseiros normais descobertos pelo personagem.
- Braseiros de Masmorra utilizam suas próprias regras de ativação/restauração/Retry da seção 19.1.
- Marca de Legado “Chamado do Braseiro”, se mantida no catálogo final, pode oferecer exceção de retorno conforme sua definição, sem transformar Braseiro de Masmorra em destino permanente.

## 41. Regras de XP e progressão

- Primeira jornada tem referência central de **220h**, faixa saudável de **200–250h** até Nv.60; completionistas podem ultrapassar **300h** conforme exploração e conteúdo opcional.
- XP em Nv.60 não se acumula escondida para Legado.
- Recompensa concluída quando já está Nv.60 não guarda a parcela de XP para depois.
- XP grande pode atravessar vários níveis até o cap; só excedente além do Nv.60 é descartado.
- Nível não muda no meio do combate; XP é consolidada na fronteira válida do encontro/atividade.
- Progressão de personagem carregado por veterano usa PowerlevelFactor individual: **100/70/45/20/5%** para diferenças de `0–10/11–15/16–20/21–30/31+` níveis, aplicado após o LevelFactor do conteúdo.

## 42. Nomes, renome e histórico

- Personagem e Guilda usam unicidade atômica no banco.
- Disponibilidade exibida não garante reserva até o commit.
- Durante exclusão pendente, nome continua reservado.
- Nome antigo permanece reservado por **30 dias** após Renome e por **30 dias** após exclusão definitiva para reduzir impersonação.
- Renome registra `character_id`, nome antigo, novo, timestamp e origem.
- Histórico competitivo captura o nome/Guilda/TAG exibidos no momento do snapshot da temporada.
- Renomear Personagem custa **2.500 Coroas** e possui **30 dias de Recarga**.

## 43. Backend e arquitetura planejada

Stack planejado:

- Python.
- aiogram 3.
- FastAPI.
- PostgreSQL.
- SQLAlchemy 2.
- Alembic.
- Redis.
- APScheduler ou scheduler persistente apropriado.
- Pytest.
- Docker.
- Git/GitHub.
- Arquitetura inicial: modular monolith.
- Polling em desenvolvimento; webhook em produção.

### 43.1 Fonte de verdade e integridade

- Banco persistente é a autoridade final.
- Redis nunca é a única proteção contra duplicação/unicidade.
- Operações críticas são atômicas e idempotentes.
- IDs únicos para itens, runs, combates, encontros, eventos, explorações, rewards, pagamentos etc.
- Nomes nunca são chaves internas.
- `server_id` faz parte da integridade; recursos server-bound não podem cruzar servidores.
- O backend mantém uma única fonte autoritativa para a atividade Foreground do personagem.
- O estado autoritativo inclui, conforme aplicável: `game_activity_id`, tipo/status, `combat_id`, `encounter_id`, `run_id`, `occurrence_id`, `exploration_attempt_id`, Configuração de Combate/snapshot vigente, versão do snapshot, turno/rodada, participantes, progresso interno, Confirmação de Entrada e demais estados necessários.
- Nenhum cliente Telegram, mensagem, `ui_session` ou dispositivo possui autoridade independente sobre esses valores.
- Após crash/restart, atividade persistente é recuperada a partir do estado autoritativo; ausência da interface Telegram não implica encerramento.
- Pertencimento a Guilda é relação server-bound com unicidade estrutural suficiente para impedir duas Guildas simultâneas por personagem.
- Inscrições de Guilda usam IDs estáveis e restrições adequadas para impedir duplicação Pendente do mesmo personagem para a mesma Guilda.
- Aprovação de Inscrição, criação do vínculo, validação de capacidade e invalidação das demais candidaturas/Convites incompatíveis formam uma única operação transacional lógica.
- Cada Loja utiliza `shop_id` imutável; Código Único é identificador público resolvível para essa Loja, nunca chave de autorização.
- Código, deep link e callback público resolvem para IDs internos antes de qualquer operação econômica.
- Código aposentado de Loja não pode ser reassociado silenciosamente a outra Loja.
- A existência/ausência de Braseiro de Masmorra é resultado autoritativo persistido da tentativa/run e não pode ser rerrolada por recovery.

### 43.2 Item state, saldo e capacidade

- Cada `item_instance_id` possui estado canônico: disponível, equipado, reservado, escrow de Mercado, escrow de Troca Direta, Serviço, Pending etc.
- Mesmo item não pode existir em dois fluxos incompatíveis.
- `item_instance` pertencente a Configuração de Combate travada recebe proteção contra mutações incompatíveis enquanto o lock estiver vigente.
- A proteção de combate independe do item estar visualmente acessível por outra mensagem/dispositivo; toda operação revalida o lock no commit.
- Listing e Serviço pertencem explicitamente à Loja/proprietário/servidor correspondentes.
- Toda compra revalida `shop_id`, `listing_id`, owner, buyer, `server_id`, versão dos termos, quantidade, preço vigente, escrow, estado do item e capacidade de destino no commit.
- Código antigo, divulgação, Nome/Descrição ou deep link nunca preservam preço/quantidade antigos.
- Débito de Coroas/material/Vigor/recurso é atômico no commit.
- Saldos/quantidades usam inteiros de pelo menos 64 bits e limites explícitos.
- Nunca há saldo negativo, stack negativo ou overflow silencioso.
- Capacidade de Inventário/Guilda/Loja é validada no commit.

### 43.3 Rewards

- Recompensas usam IDs únicos e idempotentes.
- Reward composto (XP + Coroas + item) usa um `reward_event_id` com componentes individualmente registrados; retry só completa o componente faltante.
- Conclusão de missão/Feito/Primeira Conclusão é separada da entrega física da recompensa.
- Missão pode ficar `completed` mesmo se item precisar ir para Pending.
- Descobertas e resultados de Desbravar utilizam IDs próprios e operações idempotentes.
- Conhecimento de **Bestiário** e **Códice** utiliza marcos/IDs estáveis e idempotentes; conhecimento já commitado não é duplicado por retry/reconnect/callback.
- Progresso/Marcos/claims da **Trilha da Crônica** são estados separados e idempotentes no escopo `conta + servidor + Crônica`.
- Direitos/recompensas de **Juramento** usam `cycle_id` e snapshots de elegibilidade, sem duplicação por claim/job repetido.
- Recompensa e descoberta podem ser componentes separados do mesmo evento; descoberta legítima não é perdida apenas porque a entrega física de recompensa precisou ir para Pending.
- Finalização de Masmorra concluída/falhada, consumo/liberação de Vigor e descarte/finalização de recompensa provisória são idempotentes.

### 43.4 Ruleset, versões e conteúdo

- Atividade instanciada carrega `ruleset_version`.
- Patch não muda regras no meio de run; nova atividade usa nova versão.
- Código/implementação de versões ainda vivas precisa permanecer disponível até drenar atividades antigas.
- IDs permanentes de conteúdo nunca são reutilizados; conteúdo removido fica tombstoned/arquivado.
- Missões, receitas, Feitos, Bestiário, Códice, Cosméticos/entitlements, Títulos, Doutrinas/presets, Trilha da Crônica e claims possuem migração.
- Dependências de conteúdo são validadas antes do deploy; remover algo ainda referenciado exige migração explícita.
- Patches que alteram requisitos estruturais revalidam equipamentos/Doutrinas; instâncias em andamento usam snapshot antigo e revalidam ao sair.
- Mudanças normais de Item Definition afetam instâncias existentes, preservando propriedades individuais como upgrade, bind, Runa e owner.
- Entradas de Flavor Text são conteúdo versionável e possuem identidade estável. Alterações, desativações ou substituições devem respeitar o versionamento de conteúdo e não podem deixar referências contextuais inválidas ou revelar conteúdo fora da elegibilidade narrativa.

### 43.5 Transactional Outbox e efeitos externos

- Estado do jogo e registro de side effect externo são gravados na mesma transação.
- Worker entrega Telegram/notificação depois.
- Falha visual não desfaz a operação do jogo.
- Notificações usam chave de deduplicação.
- Ordem é preservada quando mensagens dependem logicamente umas das outras.

### 43.6 Jobs, manutenção e deploy

- Jobs de reset/fechamento/recompensa são idempotentes.
- Scheduler distribuído garante uma execução lógica, mesmo com várias instâncias.
- Manutenção planejada usa **drain**: bloqueia novas entradas e deixa atividades existentes terminarem dentro da janela.
- Downtime reconhecido não gera derrota, rating loss, AFK ou punição de presença.
- Deploy de schema segue expandir → migrar → trocar leitores/escritores → remover legado.
- Feature flags podem bloquear novas entradas sem apagar estado, sempre com log quando relevante.
- Backups exigem restore tests e reconciliação com sistemas externos.

### 43.7 Admin e auditoria

- Painel administrativo registra toda ação relevante.
- Ações normais do ADM passam pelos mesmos validadores do jogo.
- Bypass exige ação privilegiada explícita, motivo e log.
- Rollback econômico usa transações compensatórias, não apaga silenciosamente histórico.
- Toda criação/destruição econômica relevante possui proveniência auditável: `reward_event_id`, `craft_event_id`, `market_transaction_id`, `trade_id`, `admin_action_id`, `payment_id` etc.

## 44. Concorrência, callbacks e segurança

- Turno usa `combat_id + turn_id + state_version`; ação e timeout competem atomicamente e só uma transição válida vence.
- Callback nunca é prova de autorização. Backend revalida conta, personagem, servidor, ownership, permissões, atividade Foreground, locks, versão de estado e demais precondições no commit.
- Botões usam IDs/contexto/versionamento suficientes para detectar estado obsoleto.
- Duas telas/dispositivos da mesma conta nunca criam atores independentes.
- Mensagem antiga pode permanecer visível, mas não preserva direito de executar ação que deixou de ser válida.
- Botões antigos de Equipar, Aplicar Doutrina, modificar Runa/Encantamento, Melhorar, redistribuir Talentos, trocar Caminho ou ação equivalente falham com segurança quando houver lock incompatível.
- `/start`, `/menu`, deep links, callbacks, mensagens antigas, reconexão ou outro cliente Telegram sempre consultam a mesma atividade autoritativa.
- Toda mutação da Configuração de Combate revalida ausência de lock incompatível **no commit**, mesmo se a tela/operação tiver sido aberta antes do lock existir.
- Aquisição do lock de atividade e snapshot da Configuração de Combate são atômicos em relação às mutações dessa configuração.
- Se uma alteração válida da Configuração de Combate concluir primeiro, a atividade iniciada depois registra o estado final resultante.
- Se o lock concluir primeiro, a mutação concorrente posterior falha.
- Nunca existe estado parcialmente aplicado em que parte da Doutrina/configuração pertença a uma versão anterior e parte à posterior.
- Aplicar Doutrina continua sendo operação atômica.
- Operações concorrentes podem utilizar transação, lock de linha, versionamento otimista/`state_version`, constraint ou mecanismo equivalente; a escolha técnica não altera a regra funcional.
- Restart do Bot, disconnect ou falha de apresentação não liberam lock persistente.
- Confirmação de Entrada/fila cancelada por falha reconhecida do sistema não pune jogadores e resolve/reverte locks conforme o estado persistido.
- Fila transitória após restart pode ser reconstruída ou cancelada com segurança, sem Vigor/derrota/punição.

### 44.1 Guildas — callbacks e concorrência

- Callbacks de Procurar Guilda, Enviar/Cancelar Inscrição, Aprovar/Recusar e Aceitar Convite sempre revalidam estado atual.
- Resultado antigo de busca não garante que recrutamento, capacidade ou elegibilidade continuem válidos.
- Botão antigo de Aprovar não preserva permissão caso o Oficial tenha perdido o cargo.
- Nome/TAG nunca substituem `guild_id` como identidade técnica da operação.
- Envios, aprovações e aceites concorrentes obedecem à mesma regra de commit atômico de pertencimento/capacidade.

### 44.2 Loja — código, callbacks e concorrência

- Buscar Loja por Código é operação de localização, não autorização.
- Código inválido não revela identificadores internos ou informações privadas.
- Busca por Código usa rate limiting contra flood/enumeração automatizada.
- Callback antigo de Comprar revalida `listing_id`, versão dos termos, quantidade restante, preço, comprador, proprietário, escrow e capacidade.
- Se duas compras disputarem a última unidade, apenas uma pode efetivar o consumo do escrow.
- Edição de preço e compra competem atomicamente pela mesma listing conforme seção 28.
- Abrir a mesma Loja em celular, Desktop ou múltiplas mensagens representa a mesma `shop_id` e o mesmo estado autoritativo.
- Deep links/divulgações podem ficar antigos; nenhuma operação econômica confia no snapshot da mensagem.
- Ações administrativas de Minha Loja exigem ownership atual e nunca são autorizadas apenas pelo conhecimento do Código.

### 44.3 Tentativas e reroll

- `encounter_id`, `run_id`, `exploration_attempt_id` e resultados persistidos não são rerrolados por callback repetido, reconnect, recovery ou troca de dispositivo.
- Ronda de Caça mantém seus encontros/lote autoritativos; Desbravar mantém o resultado da tentativa; Masmorra mantém a decisão de Braseiro da tentativa/run.
- Proteções contra abandono/recriação abusivos podem utilizar seed/chave/estado persistente apropriado, sem depender apenas da interface.

## 45. Regras de patches e migração

- Patch material que muda item em listing pode suspender listing para revisão.
- Patch material em item de Trade reseta confirmações.
- Patch que altera receitas/Serviços suspende ofertas afetadas.
- Patch que remove Arte/skill, Talento, Runa, Encantamento ou item referenciado em Doutrina/preset migra ou marca como indisponível; nunca crasha.
- Quest ativa cujo objetivo é removido deve ser migrada/preservada/compensada; nunca soft-lock silencioso.
- Conquista já obtida permanece obtida.
- Braseiro removido usa fallback seguro.
- World state usa transições condicionais/versionadas.

## 46. Sanções e estados econômicos ativos

- Suspensão temporária pode suspender listings/Serviços apropriados; valores já legitimamente recebidos permanecem registrados.
- Trade ativo é cancelado e reservas liberadas.
- Serviços ainda não executados são resolvidos/refundados conforme estado.
- Ban definitivo não deixa itens presos indefinidamente; economia é preservada para auditoria.
- Líder de Guilda banido definitivamente aciona sucessão apropriada.

## 47. Scope de limites e idempotência

- Todo limite destinado a impedir farm declara seu escopo: por exemplo `account + server + daily_cycle`, `character + chronicle`, `account + reward` etc.
- Limites econômicos importantes não podem ser resetados por recriação.
- Todo sistema de reward/claim/voto/pagamento/RNG possui chave idempotente adequada.
- Bestiário usa chaves/marcos únicos por criatura/evidência; Códice usa chave equivalente a `character + entry + trecho`.
- Trilha da Crônica usa escopo `conta + servidor + Crônica` para progresso, Marco e reward.
- Juramento usa `guild_id + cycle_id + attempt_id` e snapshots individuais/collectivos suficientes para impedir dupla contribuição/recompensa e guild hopping.
- Toda operação que consome recurso e gera resultado deve ser atômica, idempotente e recuperável após crash sem rerrolar, duplicar ou perder valor.
- Tentativas de **Desbravar** possuem chave própria e resultado persistido; reconnect, callback repetido, recovery ou request duplicado nunca geram novo sorteio para a mesma tentativa.
- Limites/cadência contra spam de exploração declaram escopo explícito; valores estão consolidados na seção 49.
- Inscrições de Guilda, divulgação/busca de Loja e outros fluxos sujeitos a flood utilizam limites/rate limits com escopo explícito quando necessário; valores quantitativos estão consolidados na seção 49.
- Proteções anti-reroll de Braseiro de Masmorra e encontros persistentes devem distinguir nova tentativa legítima de recriação abusiva de fluxo.

## 48. Estado de conteúdo e lançamento

Escopo público pretendido inclui:

- 6 Regiões completas e campanha 1–60.
- 6 Classes / 12 Caminhos.
- Combate PvE/PvP.
- Caçadas, **Ronda de Caça**, **Desbravar / Exploração**, Masmorras, Eventos, Vigor e Braseiros.
- Braseiros permanentes do mundo e Braseiros de Masmorra instanciados conforme suas regras próprias.
- Bestiário detalhado por conhecimento e Códice progressivo por Entradas/Trechos, sem checklist pública.
- Equipamentos, Runas, Encantamentos, Crafting, Desmontagem.
- Ofícios e Serviços.
- Mercado por **Loja Pessoal + Código Único + divulgação comunitária**, Serviços integrados às Lojas e Troca Direta de itens.
- Guildas com Convites, **Procurar Guilda, Recrutamento Aberto/Fechado e Inscrições**, Juramento, Expedição e Batalha de Guildas.
- Arena da Vigília e Duelo.
- Elos: Brasa, Chama, Forjado, Ascendente, Arauto e Regente.
- Doutrinas.
- Legado.
- Feitos/Títulos, **Cosméticos** (Aparência, Título e Moldura), Perfil, História do Personagem, Relatos e Vínculos.
- Crônica I + Nova Vigília.
- Trilha/Passe da Crônica com Marcos Livres/Premium, Patrono de Asterion e Cosméticos.
- Dádiva Diária, Chamado de Asterion, Comunidade e Códigos de Asterion.
- Flavor Text Contextual.
- Atividade Foreground autoritativa, travamento de Configuração de Combate e sincronização multidispositivo.
- Administração, segurança, telemetria e backups.

## 49. Baseline Numérica v1.0 — consolidada

Esta seção substitui integralmente a antiga lista de itens propositalmente abertos. Ela é a **fonte numérica autoritativa** da baseline de lançamento. Quando uma referência numérica histórica nas seções 1–48 divergir desta seção, **prevalece a seção 49**. Valores futuros alterados por Alpha/Beta devem ser versionados como Balanceamento/Telemetria; não ficam implicitamente abertos.

### 49.0 Convenções matemáticas e de arredondamento

As funções de arredondamento fazem parte da regra e devem produzir o mesmo resultado no backend, testes e ferramentas de balanceamento:

- `floor(x)`: maior inteiro `≤x`.
- `ceil(x)`: menor inteiro `≥x`.
- `round_half_up(x)`: inteiro mais próximo; empate exato `.5` sobe para o inteiro seguinte. É usado somente quando a fórmula cita explicitamente `round_half_up`, como nos atributos planos de Equipamento.
- `round_10(x)`: múltiplo de 10 mais próximo; empate exato entre dois múltiplos usa **ties-to-even** no quociente por 10. Exemplos: `115→120`, `125→120`, `135→140`, `145→140`. Essa definição preserva as curvas oficiais de Coroas e PXP.
- `round_100(x)`: múltiplo de 100 mais próximo usando a mesma regra **ties-to-even**.
- Quando uma grandeza possui passo explícito — por exemplo `0,25 p.p.` — arredonda-se ao passo mais próximo com `ties-to-even`, salvo regra que determine `floor`, `ceil` ou mínimo positivo.
- Implementações não podem depender do arredondamento padrão da linguagem sem teste de conformidade contra estas regras.
- **Coroas são sempre inteiras.** Quando uma fórmula monetária aplica multiplicador sobre `C(n)` — por exemplo `1,25 UC`, `1,5×C` ou `0,75×C` — o resultado monetário final usa `round_10` depois da multiplicação, salvo fórmula que declare outro arredondamento explicitamente.
- **Fechamento dos atributos primários estáticos:** após concluir toda a composição estática aplicável — Classe, modificadores inerentes de Caminho sobre a parcela de Classe, Talentos, Equipamento, Aprimoramento, Runas, Encantamentos e modificadores raciais de atributo final — `HP Máximo`, `ATQ`, `DEF` e `AGI` recebem **um único `round_half_up` final para ponto inteiro**. Não existe arredondamento intermediário novo nessas etapas. `PER`, `CRIT`, `Esquiva` e `Bloqueio` preservam seus passos próprios em pontos percentuais e podem permanecer fracionários. Buffs/Debuffs temporários podem operar internamente em alta precisão sobre esses atributos-base já fechados; cada quantidade resolvida continua seguindo sua regra específica de arredondamento.
- **HP atual é autoritativamente inteiro.** Após qualquer fronteira segura de reconciliação que possa alterar `HP Máximo` ou carregar estado legado, o HP atual é limitado a `0…HP Máximo` e qualquer fração legada é descartada com `floor`; nunca se arredonda HP atual para cima. Assim, `0 < HP < 1` não constitui sobrevivência válida e não pode ser produzido por novos estados. Dano continua inteiro; Cura e Barreira continuam seguindo seus próprios `floor` já definidos.

### 49.1 Combate, atributos e Classes

Constantes globais:

- Chance-base de CRIT **5%**; dano crítico-base **150%**.
- PvP: CRIT cap **40%**; dano crítico cap **200%**; Esquiva cap **25%**; Bloqueio cap **30%**.
- Bloqueio válido reduz **35%** do dano correspondente.
- Defender reduz **45%** do Dano Direto até o próximo turno; em Ruptura Final reduz **30%**.
- Cap de mitigação ativa multiplicativa: **65%**, separado da redução natural por DEF.
- Cura em PvP: **90%** do valor PvE antes da Exaustão.
- Barreira em PvP: cap de **35% do HP Máximo**.
- PER base **0%**, cap **30%**; `DEF_eff = max(0, DEF_mod × (1 − PER/100))` antes da fórmula normal de DEF.
- DoTs padrão usam **50% da DEF efetiva normal**, não Critam, não geram Vampirismo e não fazem novo teste de Esquiva.
- Após **2 Esquivas consecutivas**, o próximo ataque básico/ofensivo direto elegível contra aquele alvo não pode ser Esquivado.

Atributos inerentes de referência no **Nv.60**:

| Classe | HP | ATQ | DEF | AGI |
|---|---:|---:|---:|---:|
| 🛡️ Sentinela | 2808 | 368 | 324 | 276 |
| 🗡️ Errante | 2470 | 424 | 282 | 330 |
| 🏹 Vigia | 2522 | 420 | 288 | 321 |
| 🪄 Tecelão | 2418 | 436 | 273 | 300 |
| 🔮 Oráculo | 2574 | 400 | 291 | 309 |
| ☀️ Luminar | 2678 | 384 | 309 | 288 |

Curva inerente oficial de Nv.1–60:

`G(n)=4^((n−60)/59)`

Para cada Classe `C`, atributo `A ∈ {HP, ATQ, DEF, AGI}` e nível `1≤n≤60`:

`ClassStat_C,A(n) = round_half_up(ClassStat_C,A(60) × G(n))`.

O `round_half_up` é parte explícita desta fórmula e não constitui arredondamento implícito universal. A curva preserva exatamente os valores de Nv.60, possui `G(1)=0,25` e crescimento bruto constante de aproximadamente `+2,37747%` por nível. Diferenças proporcionais entre Classes são preservadas antes do arredondamento; empates pontuais de inteiros podem ocorrer sem criar inversão de identidade verificada na baseline.

Vetores de verificação `HP / ATQ / DEF / AGI`:

| Classe | Nv.1 | Nv.10 | Nv.20 | Nv.30 | Nv.40 | Nv.50 | Nv.60 |
|---|---|---|---|---|---|---|---|
| 🛡️ Sentinela | 702 / 92 / 81 / 69 | 867 / 114 / 100 / 85 | 1.097 / 144 / 127 / 108 | 1.388 / 182 / 160 / 136 | 1.755 / 230 / 203 / 173 | 2.220 / 291 / 256 / 218 | 2.808 / 368 / 324 / 276 |
| 🗡️ Errante | 618 / 106 / 71 / 83 | 763 / 131 / 87 / 102 | 965 / 166 / 110 / 129 | 1.221 / 210 / 139 / 163 | 1.544 / 265 / 176 / 206 | 1.953 / 335 / 223 / 261 | 2.470 / 424 / 282 / 330 |
| 🏹 Vigia | 631 / 105 / 72 / 80 | 779 / 130 / 89 / 99 | 985 / 164 / 113 / 125 | 1.246 / 208 / 142 / 159 | 1.576 / 263 / 180 / 201 | 1.994 / 332 / 228 / 254 | 2.522 / 420 / 288 / 321 |
| 🪄 Tecelão | 605 / 109 / 68 / 75 | 747 / 135 / 84 / 93 | 945 / 170 / 107 / 117 | 1.195 / 215 / 135 / 148 | 1.511 / 273 / 171 / 188 | 1.912 / 345 / 216 / 237 | 2.418 / 436 / 273 / 300 |
| 🔮 Oráculo | 644 / 100 / 73 / 77 | 795 / 124 / 90 / 95 | 1.006 / 156 / 114 / 121 | 1.272 / 198 / 144 / 153 | 1.609 / 250 / 182 / 193 | 2.035 / 316 / 230 / 244 | 2.574 / 400 / 291 / 309 |
| ☀️ Luminar | 670 / 96 / 77 / 72 | 827 / 119 / 95 / 89 | 1.046 / 150 / 121 / 113 | 1.323 / 190 / 153 / 142 | 1.674 / 240 / 193 / 180 | 2.117 / 304 / 244 / 228 | 2.678 / 384 / 309 / 288 |

A ordem de composição de atributos é:

`Classe inerente → modificadores inerentes de Caminho sobre a parcela de Classe → Talentos → núcleo de Equipamento → secundários → Aprimoramento → Runas → Encantamentos → modificadores raciais de atributo final aplicáveis → Buffs/Debuffs de combate → floors/caps`.

Modificadores percentuais inerentes de Caminho **não multiplicam a parcela de Equipamento**. Para evitar implementações divergentes, **Adaptabilidade dos Remanescentes** (`+1,5% HP/ATQ/DEF/AGI`) e o **+5% AGI dos Alvoranos** são modificadores de **atributo estático final**: aplicam-se depois de Equipamento/Runas/Encantamentos e antes de Buffs/Debuffs temporários e floors/caps.

### 49.2 Raças

- 🕯️ **Remanescentes — Adaptabilidade:** `+1,5%` a HP Máximo, ATQ, DEF e AGI estáticos finais, após Equipamento/Runas/Encantamentos e antes de Buffs/Debuffs e floors/caps; não afeta PER/CRIT/Esquiva/Bloqueio.
- 🌘 **Velados — Eco do Véu:** Buff elegível de base `≥2T` aplicado ao Velado tem **25%** de chance de `+1T`; Debuff elegível de base `≥2T` tem **25%** de chance de `−1T`, mínimo `1T`. Exclui Barreira, Cura, DoT, hard CC, marcas/recursos internos, mecânicas fixas de Chefe/Masmorra e efeitos imutáveis. RNG determinístico de combate.
- 🌪️ **Cinéreos — Tenacidade Cinérea:** Defender `+7 p.p.`: `45%→52%`; em Ruptura Final `30%→37%`.
- 🩸 **Hemários — Fome Hemária:** enquanto `HP ≤40%`, `+12%` de Vampirismo racial; Cura passiva resultante capada em **3% HP Máximo por ação** após agregação. Sem DoT/reflexão/ambiental/barreira-only/overkill; deixa de operar acima de 40%.
- 🔆 **Alvoranos — Primeiro Clarão:** `+5% AGI estático final`, após Equipamento/Runas/Encantamentos e antes de Buffs/Debuffs e floors/caps; magnitude de Debuffs numéricos removíveis recebidos `−12%`. Exclui DoT, hard CC, duração, dano direto, marcas/recursos e mecânicas fixas.

Impacto racial-alvo permanece na faixa de **3–5%**, sem combinações obrigatórias.

### 49.3 Caminhos

Progressão comum: `Nv.10 Provação/Caminho + Passiva`, Arte de Caminho I `Nv.12`, II `Nv.22`, III `Nv.38`, IV `Nv.52`.

**Sentinela**

- 🏰 **Bastião:** HP `+5%`, ATQ `−5%`, DEF `+7%`, AGI `−2%`. **Fortaleza:** Barreiras aplicadas `+10%`; quando Defender efetivamente reduz Dano Direto e ativa Retaliação, recebe Barreira de `4% HP Máximo` até o próximo turno, sem auto-stack. Artes: **Escudo de Cinzas** Barreira `95% ATQ 2T CD3`; **Interpor** próximo Dano Direto ao alvo dentro de `2T` `−25%`, `CD4`; **Contra-Golpe** `120%`, com Retaliação aplica `−10% ATQ 2T`, `CD3`; **Última Muralha** Barreira em todos aliados `65% ATQ 2T`, `CD5`.
- 💥 **Devastador:** HP `−2%`, ATQ `+8%`, DEF `−4%`, AGI `+2%`. **Ímpeto Doloroso:** se uma ação inimiga remover `≥8% HP Máximo` de HP real, próxima Arte de Dano Direto em `2T` recebe `+12% Dano Final`, máximo 1 carga; dano totalmente absorvido por Barreira não ativa. Artes: **Aríete** `135%` + `10 p.p. PER` na ação, `CD2`; **Golpe de Ruptura** `125%`, ou `150%` com Retaliação, `CD3`; **Abalo** AoE `90%` + `−8% DEF 2T`, `CD4`; **Ruptor** `170%`, com HP próprio `<50%` recebe `+10% potência`, `CD5`.

**Errante**

- ☠️ **Carrasco:** HP `−3%`, ATQ `+7%`, DEF `−2%`, AGI `+2%`. **Sentença:** Dano Direto contra alvo `≤40% HP` recebe `+8% final`; acumula com Oportunismo apenas na janela de execução. Artes: **Corte de Execução** `135%`, alvo `≤35%` `+15% potência`, `CD3`; **Hemorragia** `95%` + `2` Sangramentos, `CD3`; **Marca da Morte** `80%`, próxima Arte direta de Carrasco em `2T` `+12%`, `CD4`; **Ceifa** `165%`, alvo `≤40%` `+10 p.p. CRIT`, `CD5`.
- 🕷️ **Sabotador:** HP `+2%`, ATQ `−2%`, DEF `0%`, AGI `+5%`. **Interferência:** Debuffs não-CC de base `1–2T` recebem `+1T`, máximo `3T`; não afeta DoT/hard CC. Artes: **Veneno Velado** `85%` + Veneno, `CD2`; **Fio Cortado** `95%` + `−12% ATQ 2T`, `CD3`; **Trava de Passos** `80%` + `−18% AGI 2T`, `CD3`; **Colapso Preparado** `120%` + `10%` por efeito negativo distinto, máximo `+30%`, `CD5`.

**Vigia**

- 🎯 **Atirador:** HP `−1%`, ATQ `+7%`, DEF `−3%`, AGI `+2%`. **Mira Perfeita:** máximo de Mira `3→4`; cada Mira concede `+3 p.p. PER`; com 4 Miras também `+6 p.p. CRIT`; trocar de alvo remove Mira. Artes: **Tiro Perfurante** `130%` + `10 p.p. PER`, `CD2`; **Fixar Alvo** `100%` + 1 Mira extra, `CD3`; **Rajada Controlada** `3×45%`, `CD3`; **Disparo Terminal** requer 4 Miras, consome após resolução, `175% +15 p.p. CRIT`, `CD5`.
- 👣 **Rastreador:** HP `+2%`, ATQ `−1%`, DEF `+2%`, AGI `+3%`. **Rastros Múltiplos:** Mira máximo 2 por alvo em até 3 alvos; aplicar DoT ou redução de AGI concede 1 Mira. Artes: **Flecha Serrilhada** `90%` + Sangramento, `CD2`; **Laço de Caça** `80%` + `−20% AGI 2T`, `CD3`; **Chuva de Rastros** AoE `70%` +1 Mira em cada alvo, `CD4`; **Predação Persistente** `135%` + `8%` por DoT/Debuff distinto, máximo `+16%`, `CD4`.

**Tecelão**

- 🌀 **Conjurador:** HP `−3%`, ATQ `+8%`, DEF `−4%`, AGI `0%`. **Convergência:** Trama consumida por dano passa de `+10%` para `+15%`; em Cura/Barreira vale `+6%`. Artes: **Estilhaço do Véu** `140%`, `CD2`; **Incêndio Trançado** AoE `75%` + Queimadura, `CD3`; **Convergência Arcana** `3×50%`, `CD3`; **Rasgo Conjurado** AoE `125%`, `CD5`.
- 🔷 **Rúnico:** HP `+4%`, ATQ `−4%`, DEF `+5%`, AGI `−1%`. **Inscrição:** Trama em Cura/Barreira `+15%`; em dano `+6%`. Artes: **Runa de Guarda** Barreira `105% 2T`, `CD3`; **Runa de Ruptura** `90%` + `−10% DEF 2T`, `CD3`; **Runa de Retorno** Cura `70%` + Purificação 1, `CD4`; **Círculo Rúnico** Barreira AoE `60% 2T`, `CD5`.

**Oráculo**

- 🦉 **Agoureiro:** HP `−1%`, ATQ `+3%`, DEF `−1%`, AGI `+2%`. **Mau Presságio:** Presságio ofensivo consumido passa de `+12%` para `+16%`; defensivo permanece `+12%`. Artes: **Mau Agouro** `95%` + `−10% ATQ 2T`, `CD2`; **Destino Lento** `70%` + `−18% AGI 2T`, `CD3`; **Condenação** `80%`, próxima Arte de Agoureiro `+20%` em `2T`, `CD4`; **Eclipse Previsto** `150%`; se consumir Presságio, alvo recebe `−15% Cura recebida 2T`, `CD5`.
- 🐺 **Invocador:** HP `+3%`, ATQ `−1%`, DEF `+1%`, AGI `−1%`. **Tríade:** usar manifestação diferente da anterior em `2T` concede `+12% potência`. **Lobo** `125% CD2`; **Coruja** `85% −15% AGI 2T CD3`; **Urso** Barreira `100% 2T CD3`; **Tríade Encarnada CD5:** último Lobo → `155%` dano; Coruja → `95% −20% AGI 2T`; Urso → Barreira `120% 2T`; Tríade Encarnada não atualiza a última manifestação nem ativa alternância por si só.

**Luminar**

- 🪬 **Guardião:** HP `+5%`, ATQ `−5%`, DEF `+5%`, AGI `−2%`. **Aurora:** Fulgor em Cura/Barreira `+10%→+15%`; Julgamento em dano `+6%`. Artes: **Cura Solar** Cura `100% CD2`; **Égide Compartilhada** Barreira `90%` no alvo + `45%` em si, `CD4`; se o próprio Luminar for alvo recebe apenas `90%`, não soma; **Purgação Luminosa** Cura `65%` + Purificação 1, `CD4`; **Aurora Guardiã** Cura AoE `55%`, `CD5`.
- ⚖️ **Inquisidor:** HP `−3%`, ATQ `+8%`, DEF `−3%`, AGI `+2%`. **Julgamento Implacável:** Julgamento em Dano Direto `+10%→+15%`; Fulgor em Cura/Barreira `+6%`. Artes: **Lança de Luz** `135% CD2`; **Selo da Penitência** `100% −20% Cura recebida 2T CD3`; **Purga Ardente** `120%` + Dispel de 1 efeito positivo, `CD4`; **Veredito** `170%`, alvo com Debuff `+10 p.p. CRIT`, `CD5`.

### 49.4 Artes de Classe e DoTs

Desbloqueio de Artes de Classe: `Nv.1 / 4 / 7 / 9 / 18 / 34`. Caminho: `Nv.12 / 22 / 38 / 52`. Cada personagem Nv.60 possui `6 Artes de Classe + 4 do Caminho atual = 10` disponíveis e equipa até 3.

Universais: **Ataque Básico 100% ATQ**, Dano Direto, um inimigo, sem Recarga; Defender conforme 49.1.

DoTs:

- Veneno `12% ATQ/stack/tick`, `3T`, máximo 3.
- Sangramento `10% ATQ/stack/tick`, `2T`, máximo 3; ação agressiva do afetado gera adicional de `3% ATQ snapshot/stack`.
- Queimadura `15% ATQ/stack/tick`, `2T`, máximo 2; `−5% Cura recebida/stack`.

Artes de Classe:

- **Sentinela:** Nv1 Golpe de Guarda `110% CD2`; Nv4 Quebra-Postura `90% −10% DEF 2T CD3`; Nv7 Muralha Breve Barreira `70% 2T CD3`; Nv9 Impacto Resoluto `135% CD3`; Nv18 Firmeza `+12% DEF 2T` em si `CD3`; Nv34 Golpe de Rechaço `145%`, com Retaliação `+10 p.p. PER`, `CD4`.
- **Errante:** Nv1 Corte Veloz `115% CD2`; Nv4 Ferida Profunda `90% + Sangramento CD2`; Nv7 Passo Velado `+15 p.p. Esquiva 1T` e próximo Dano Direto em `2T +10 p.p. CRIT`, `CD4`; Nv9 Golpe Oportuno `125%`, alvo com efeito negativo `+15 p.p. CRIT`, `CD3`; Nv18 Corte Duplo `2×60% CD3`; Nv34 Brecha Mortal `130%`, alvo negativo `+10 p.p. PER`, `CD3`.
- **Vigia:** Nv1 Disparo Preciso `115% CD2`; Nv4 Marca da Presa `85% −8% DEF 2T CD3`; Nv7 Saraivada `3×40%`, Crit/precisão por hit, `CD3`; Nv9 Olho da Vigília `+12 p.p. PER/+8 p.p. CRIT 2T CD4`; Nv18 Tiro Calculado `125%`, com ≥2 Mira `+10 p.p. CRIT`, `CD3`; Nv34 Voleio AoE `75% CD3`.
- **Tecelão:** Nv1 Fio Cortante `120% CD2`; Nv4 Chama Tecida `85% + Queimadura CD2`; Nv7 Ruptura da Trama AoE `80% CD3`; Nv9 Véu Entrelaçado Barreira `90% 2T CD3`; Nv18 Geada Tecida `90% −15% AGI 2T CD3`; Nv34 Surto do Véu `145% CD3`. Uma Arte que consome Trama Encadeada **não gera nova Trama**; sequência normal → Arte diferente fortalecida → normal → fortalecida.
- **Oráculo:** Nv1 Sinal Funesto `105% −8% ATQ 2T CD2`; Nv4 Vislumbre `+10% AGI 2T` em si/aliado `CD3`; Nv7 Ruína Predita `120% CD2`; Nv9 Véu Premonitório Barreira `70% 2T`, enquanto ativa magnitude de Debuff numérico `−10%`, `CD4`; Nv18 Augúrio Favorável `+10% ATQ 2T` em si/aliado `CD4`; Nv34 Selo da Queda `100% −10% DEF 2T CD3`.
- **Luminar:** Nv1 Fulgor `110% CD2`; Nv4 Renovação Cura `85%` em si/aliado `CD2`; Nv7 Égide Solar Barreira `90% 2T CD3`; Nv9 Julgamento `130% −15% Cura recebida 2T CD3`; Nv18 Luz Restauradora Cura `70% + Barreira 35% 2T CD4`; Nv34 Explosão Solar AoE `85% CD3`.

### 49.5 Talentos

- **12 Pontos de Talento**, um nos níveis `5,10,15,20,25,30,35,40,45,50,55,60`.
- Cada Classe possui **18 Talentos**, organizados em Pressão/Resistência/Técnica, 6 tiers (`Nv.5/15/25/35/45/55`), um rank, sem pré-requisitos; no Nv.60 escolhe-se 12/18.
- Orçamento-alvo total: aproximadamente **9–11%**, hard cap de referência **~12%**.
- Sem redução universal de Recarga, turnos extras, hard CC recorrente, ressurreição, slots extras, bônus de economia/drop/XP/Vigor ou benefícios PvP-only.
- Respec completo em local seguro por `2 × C(nível atual)`; no Nv.60 = **2.000 Coroas**; sem Recarga temporal.
- Doutrina salva a distribuição desejada, mas não concede respec gratuito.
- Legado salva 12 slots de ponto `T1 Nv5 ... T12 Nv60`; somente os slots compatíveis com nível atual permanecem ativos.

**Sentinela:** Nv5 Aço Desperto `+1% ATQ`; Carne de Pedra `+1% HP`; Ritmo de Guarda Retaliação→`+5% AGI` até fim do próximo turno. Nv15 Ponta Revidada ação com Retaliação `+4 p.p. PER`; Placas Internas `+2% DEF`; Guarda Preparada após Defender reduzir Dano Direto, próxima Barreira em `2T +6%`. Nv25 Pressão de Fissuras `+3% Dano Direto` contra `−DEF`; Firme sob Impacto ação inimiga que remove ≥8% HP → `+5% DEF 1T`; Retaliação Persistente `+1T` de duração, sem carga extra. Nv35 Olho de Combate `+2 p.p. CRIT`; Barreira Densa Barreiras recebidas `+5%`; Contrapeso após Retaliação `+4% DEF 1T`. Nv45 Ponta Penetrante `+2 p.p. PER`; Postura de Ferro Defender `+2 p.p.`; Vigília: primeira vez `≤50% HP` recebe 1 Retaliação. Nv55 Punição Final `+4% Dano Direto` contra alvo `≤40%`; Persistência própria `≤35% HP` → `+7% DEF`; Guarda Íntegra após Defender, próximo Debuff numérico removível antes do próximo turno tem magnitude `−10%`.

**Errante:** Nv5 Fio Afiado `+1% ATQ`; Passo Prudente `+1% HP`; Instinto Rápido `+3% AGI`. Nv15 Brecha Exposta: ação com Oportunismo `+4 p.p. PER`; Reflexo `+1 p.p. Esquiva`; Sangue Frio: Esquiva bem-sucedida → próximo Dano Direto em `2T +5 p.p. CRIT`. Nv25 Precisão Cruel `+2 p.p. CRIT`; Couro Leve `+2% DEF`; Passos da Sombra ao aplicar efeito negativo `+5% AGI` até próximo turno. Nv35 Oportunismo Ampliado `+8%→+10%`; Sobrevivência própria `≤40%` → `+5% DEF`; Desvio Ofensivo após Esquiva próximo Dano Direto `+4 p.p. PER`. Nv45 Fio Perfurante `+2 p.p. PER`; Pele Endurecida `−8% dano de DoT`; Ritmo Predatório após Oportunismo `+5% AGI` no próximo turno. Nv55 Fim Próximo `+4% Dano Direto` contra alvo `≤35%`; Primeiro Desvio primeiro Dano Direto recebido no combate `−8%`; Instinto de Fuga primeira vez `≤30%` → `+10 p.p. Esquiva` até próximo turno.

**Vigia:** Nv5 Mão Firme `+1% ATQ`; Sobrevivente das Trilhas `+1% HP`; Passo do Caçador `+3% AGI`. Nv15 Olho Afiado `+2 p.p. CRIT`; Postura Vigilante `+2% DEF`; Mira Estável Mira `+1T`. Nv25 Perfuração Calculada `+2 p.p. PER`; Antecipação primeiro Dano Direto `−7%`; Aquisição Rápida primeiro Dano Direto contra alvo sem Mira gera 1 Mira extra, 1×/alvo/combate. Nv35 Alvo Exposto com ≥2 Mira `+3% Dano Direto`; Recuo Instintivo primeira vez `≤40%` → `+8% DEF 1T`; Visão Persistente ao trocar alvo preserva 1 Mira no anterior por `1T`. Nv45 Ponto Fraco com ≥3 Mira `+2 p.p. CRIT`; Couro de Campo `−8% dano de DoT`; Leitura de Movimento ao aplicar `−AGI` → `+5% AGI 1T`. Nv55 Disparo Implacável `+4% Dano Direto` contra alvo `≤35%`; Último Horizonte próprio `≤35%` → `+6% DEF`; Caçada Metódica ao atingir alvo em Mira máxima, próximo Dano Direto em `2T +3 p.p. PER`.

**Tecelão:** Nv5 Fio Potente `+1% ATQ`; Trama Vital `+1% HP`; Passo Entre Fios `+3% AGI`. Nv15 Fenda Precisa `+2 p.p. CRIT`; Véu Denso `+2% DEF`; Trama Duradoura janela de consumo `2→3T`. Nv25 Fio Perfurante `+2 p.p. PER`; Proteção Tecida Barreiras recebidas `+5%`; Alternância Fluida consumir Trama → `+5% AGI 1T`. Nv35 Trama Agressiva Trama consumida por dano `+2 p.p. potência`; Reforço do Véu enquanto Barreira `+5% DEF`; Fio Persistente primeira Trama que expira sem uso no combate renova `1T`. Nv45 Ruptura Profunda Dano Direto contra alvo com DoT `+3%`; Tecelagem Defensiva primeira Barreira própria no combate `+10%`; Eco de Alternância consumir Trama com Arte diferente → próxima ofensiva em `2T +3 p.p. PER`. Nv55 Sobrecarga Controlada `+4% potência` quando dano consome Trama contra alvo `≤40%`; Véu de Emergência primeira vez próprio `≤30%` → Barreira `6% HP 1T`; Trama Precisa: ofensiva consumida `+2 p.p. CRIT`; Cura/Barreira consumida `+2% potência`.

**Oráculo:** Nv5 Visão Cruel `+1% ATQ`; Pressentimento Vital `+1% HP`; Passos do Destino `+3% AGI`. Nv15 Presságio Cortante ofensivo consome Presságio `+2 p.p. PER`; Véu Cauteloso `+2% DEF`; Sinal Persistente Presságio `+1T`. Nv25 Destino Exposto `+2 p.p. CRIT`; Antevisão Defensiva enquanto Barreira `+5% DEF`; Leitura dos Sinais ao aplicar Presságio em inimigo `+5% AGI 1T`. Nv35 Profecia Dolorosa ofensiva consome Presságio `+2% potência`; Destino Adiado primeiro Dano Direto `−7%`; Presságio Flexível primeiro Presságio que expira sem uso no combate renova `1T`. Nv45 Fraqueza Prevista `+3% Dano Direto` contra alvo com Debuff; Mente Velada magnitude de Debuff numérico removível recebido `−6%`; Sequência Profética consumir Presságio → `+3% AGI 1T`. Nv55 Fim Anunciado `+4% Dano Direto` contra alvo `≤35%`; Última Visão primeira vez próprio `≤30%` → Barreira `6% HP 1T`; Sinais Convergentes defensivo consumido `+3% potência`, ofensivo consumido `+2 p.p. CRIT`.

**Luminar:** Nv5 Luz Incisiva `+1% ATQ`; Vitalidade Solar `+1% HP`; Clarão Ágil `+3% AGI`. Nv15 Julgamento Preciso ofensiva fortalecida por Julgamento `+2 p.p. CRIT`; Corpo Consagrado `+2% DEF`; Contraluz Persistente Fulgor/Julgamento `+1T`. Nv25 Luz Perfurante `+2 p.p. PER`; Égide Densa Barreiras aplicadas `+4%`; Alternância Radiante consumir Fulgor/Julgamento → `+4% AGI 1T`. Nv35 Veredito Ardente Dano Direto fortalecido por Julgamento `+2% potência`; Cura Prudente Cura alvo `≤40% +5%`; Ciclo Luminoso primeiro Fulgor/Julgamento que expira sem uso no combate renova `1T`. Nv45 Punição da Fraqueza `+3% Dano Direto` contra alvo com Cura reduzida; Luz Protetora enquanto Barreira `+5% DEF`; Fluxo Restaurador Cura efetiva consumindo Fulgor → alvo `+4% DEF 1T`. Nv55 Sentença Solar `+4% Dano Direto` contra alvo `≤35%`; Último Alvorecer primeira vez próprio `≤30%` → Cura `5% HP` sem Crit/triggers/bônus; Contraluz Perfeita: Fulgor consumido em Cura/Barreira `+2% potência`; Julgamento em Dano Direto `+2 p.p. PER`.

### 49.6 Inimigos e Chefes

Modelo: `K(level) × categoria × arquétipo × variante × conteúdo × grupo`.

`K(level)` é o vetor neutro de referência derivado da média aritmética exata dos seis vetores inerentes de Classe no Nv.60:

`K60 = (15470/6 HP; 2432/6 ATQ; 1767/6 DEF; 304 AGI)`

Para leitura humana: `2578,333333… HP / 405,333333… ATQ / 294,5 DEF / 304 AGI`.

Para cada atributo `A`:

`K_A(n) = K60_A × G(n)`.

O atributo final de um inimigo é:

`EnemyStat = round_half_up(K_A(level) × Category_A × Archetype_A × Variant_A × Content_A × Group_A)`.

Regras operacionais: cálculos intermediários em alta precisão; multiplicador ausente = `1,00`; **nenhum arredondamento intermediário**; um único `round_half_up` no atributo final. A tabela abaixo arredonda `K` apenas para conferência humana — a implementação utiliza o valor bruto.

| Nv. | K HP | K ATQ | K DEF | K AGI |
|---:|---:|---:|---:|---:|
| 1 | 645 | 101 | 74 | 76 |
| 10 | 796 | 125 | 91 | 94 |
| 20 | 1.007 | 158 | 115 | 119 |
| 30 | 1.274 | 200 | 146 | 150 |
| 40 | 1.612 | 253 | 184 | 190 |
| 50 | 2.038 | 320 | 233 | 240 |
| 60 | 2.578 | 405 | 295 | 304 |

Categorias Solo relativas ao personagem de referência:

| Categoria | HP | ATQ | DEF | AGI |
|---|---:|---:|---:|---:|
| Comum | 70% | 82% | 90% | 95% |
| Incomum | 85% | 90% | 95% | 100% |
| Elite | 150% | 105% | 105% | 102% |
| Chefe | **220%** | 110% | 110% | 100% |

Correção integrada: Chefe normal utiliza **220% HP**, substituindo a referência anterior de 300%, para manter TTK aproximado de 12–18 ações equivalentes.

Arquétipos: Equilibrado `100/100/100/100`; Bruto `HP115/ATQ112/DEF95/AGI85`; Predador `90/110/90/120`; Blindado `HP110/ATQ88/DEF120/AGI85`; Conjurador `85/115/88/100`; Controlador `95/90/100/110`.

Variantes-base data-driven: **Furioso** `ATQ +8% / DEF −8%`; **Resistente** `DEF +10% / ATQ −6%`; **Ágil** `AGI +12% / HP −7%`; **Hemorrágico** habilita pacote de Sangramento e aplica `ATQ −5%`; **Venenoso** habilita pacote de Veneno e aplica `HP −5%`. A semântica operacional dos pacotes e a confirmação de que Furioso/Resistente/Ágil não alteram IA por si mesmos estão na seção 10.6. Variantes adicionais precisam declarar orçamento equivalente e não somam poder gratuitamente fora do perfil configurado.

Fraqueza/Resistência normal modifica o dano correspondente em **±10%**. Versões fortes de **±20%** são excepcionais e precisam ser explicitamente definidas; nenhuma fraqueza/resistência genérica pode invalidar uma Classe/Caminho.

Coeficientes-base de Artes inimigas: simples `90–110% ATQ`; forte `120–145%`; telegráfica `150–190%`; AoE `65–100%`; multi-hit `110–150%` total; DoT/impacto híbrido `70–100%`; Barreira `60–100% ATQ`; Cura `50–80% ATQ`.

Grupo em Caçadas: `HP_group = HP_solo × [1 + 0,72(N−1)]` → `1 / 1,72 / 2,44 / 3,16`; ATQ `×[1+0,08(N−1)]` → `1 / 1,08 / 1,16 / 1,24`; DEF sem escala por tamanho. Threat Budget: Comum `1,00`; dois menores `0,55` cada; swarm `0,38×3`; Elite `2,00–2,30`.

Chefes de Masmorra: base Solo **300% HP**, ATQ 110%, DEF 110%, AGI 100%. Grupo: HP `×[1+0,78(N−1)]` → `1/1,78/2,56/3,34`; ATQ `×[1+0,07(N−1)]` → `1/1,07/1,14/1,21`. Dificuldade: Estável `HP1,00 ATQ1,00`; Fraturada `HP1,15 ATQ1,08`; Ruptura `HP1,30 ATQ1,15`. Fases típicas `70%/35%`; telegráficos Preparados `150–180% ATQ`; Críticos excepcionais `180–220%`. Pressure Crescente `+3% ATQ final/stack`, máximo 5; inicia na oportunidade 12/10/8 do Chefe em Estável/Fraturada/Ruptura.

Adds de Chefe: swarm `0,25–0,35` Threat; menor `0,40–0,55`; comum `0,70–1,00`; especial `1,00–1,40`; uma onda normal não excede **1,50 Threat por jogador** salvo mecânica excepcional explicitamente telegráfica. AoE normal de Chefe `65–85% ATQ`; AoE preparado `90–120%`; Cura própria `3–6% HP Máximo` quando prevista, com uso limitado; Barreira `5–10% HP Máximo`. Hard CC é raro, máximo **1T**, com telegraph/condição clara. DoTs de jogadores não recebem redução blanket contra Chefes; resistências precisam ser específicas. O scaling de Grupo fica congelado na criação da run/encontro.

### 49.7 XP, Missões e Legado

XP para `n→n+1`, `n=1…59`:

`XP(n) = round_100(4000 + 750n + 43n²)`.

Total Nv.1→60: **4.582.500 XP**. Tempo central: `H(n)=0,905903 + 0,094097n` horas por level-up; soma aproximada **220h**. Faixa saudável da primeira jornada: **200–250h**.

Pontos: `1→2 4.800`; `10→11 15.800`; `20→21 36.200`; `30→31 65.200`; `40→41 102.800`; `50→51 149.000`; `59→60 197.900`.

LevelFactor de conteúdo: `≥+5 =110%`; `+3/+4=105%`; `−2…+2=100%`; `−3…−5=80%`; `−6…−10=50%`; `−11…−20=20%`; `≤−21=5%`.

PowerlevelFactor individual pela diferença para o membro de maior nível: `0–10=100%`; `11–15=70%`; `16–20=45%`; `21–30=20%`; `≥31=5%`, aplicado após LevelFactor.

XP de inimigos por unidade: Comum `1,00`; Incomum `1,35`; Elite `2,75`; Chefe `6,00`. Grupo não divide XP; participação: normal 100%, baixa 70%, muito baixa 25%, AFK 0%; suporte conta. Conteúdo repetível com Vigor insuficiente: **25% XP**; único/story/discovery permanece 100%.

#### Unidade absoluta de XP de inimigo

Para `1 ≤ n ≤ 59`:

`XP_ref(n) = XP(n)`

`XP_por_hora(n) = XP_ref(n) / H(n)`

Como a cadência-base da Ronda de Caça é de **3 minutos por encontro**:

`EnemyXPUnit(n) = XP_ref(n) / [20 × H(n)]`

Essa unidade representa `1,00` unidade de XP de inimigo.

Multiplicadores de categoria permanecem:

- Comum `1,00`;
- Incomum `1,35`;
- Elite `2,75`;
- Chefe `6,00`.

Fórmula final:

`EnemyXP = round_10(EnemyXPUnit(enemy_level) × CategoryMultiplier × LevelFactor × PowerlevelFactor × ParticipationFactor × VigorXPFactor × LegacyXPFactor)`

Aplicar somente os fatores pertinentes ao contexto. Não arredondar valores intermediários; usar `round_10` uma única vez no resultado final.

O primeiro **Cão Cinéreo** do prólogo concede override fixo de **320 XP** somente em player_victory; em player_defeat, TutorialXP = 0. Nenhum dos dois resultados usa a fórmula normal de XP de inimigo.

Para sistemas que explicitamente usam `reference_level=60`, sem criar Nv.61:

`XP_ref(60) = round_100(4000 + 750×60 + 43×60²) = 203.800`

`H_ref(60) = 0,905903 + 0,094097×60 = 6,551723h`

`XP_por_hora(60) = XP_ref(60) / H_ref(60)`

A referência Nv.60 existe apenas para normalização econômica/temporal de conteúdo endgame.

#### Arredondamento de recompensas percentuais fixas

`FixedPercentXP = round_half_up(XP(reference_level) × percentual)`

Aplicar a recompensas fixas definidas como percentual da curva de XP, incluindo Missões quando necessário, Descoberta grande, Descoberta menor, primeira observação do Bestiário e marco importante configurado do Bestiário. Não substituir fórmulas que já possuam arredondamento próprio.

Distribuição-alvo da primeira jornada: Campanha/Principais **35–38%**; Secundárias **18–22%**; Caçadas/Ronda **18–22%**; Masmorras **8–12%**; Exploração **7–9%**; Bestiário/Eventos **4–8%**. É uma meta de composição, não um cap rígido por personagem.

Exploração: descoberta grande inédita **8%** do requisito do nível; descoberta menor inédita **2,5%**; resultado atmosférico **0% adicional**. Bestiário: primeira observação válida **1%**; marco importante configurado **3%**. Inimigos internos de Masmorra concedem **25% da XP normal de Caçada** para impedir farm por reset de trash; a conclusão usa sua fórmula própria.

Missões do lançamento: **36 Principais + 36 Secundárias = 72**; 6 + 6 por Região. Principal por Região nos offsets `L+0,+2,+4,+6,+8,+9`; Secundárias `L+1 curta,+3 padrão,+4 curta,+6 padrão,+7 padrão,+9 longa`. XP: Principal padrão 50%, clímax 90%; Secundária curta 20%, padrão 35%, longa 50% do requisito do nível recomendado.

Recompensas relativas de Missão usam `C(n)=round_10(100+15n)` Coroas por `1 UC`; `1 UM = 2` Materiais Básicos regionais vinculados. Tabela autoritativa por Região:

| Missão | XP | Coroas | Materiais | Equipamento |
|---|---:|---:|---:|---|
| P1 | 50% | `1,00 UC` | `1 UM` | — |
| P2 | 50% | `1,00 UC` | `2 UM` | — |
| P3 | 50% | `1,00 UC` | — | 1 escolha entre 3 |
| P4 | 50% | `1,25 UC` | `2 UM` | — |
| P5 | 50% | `1,25 UC` | `2 UM` | — |
| P6 · Clímax | 90% | `2,00 UC` | `4 UM` | 1 escolha entre 3 |
| S1 · Curta | 20% | `0,50 UC` | — | — |
| S2 · Padrão | 35% | `0,75 UC` | `1 UM` | — |
| S3 · Curta | 20% | `0,50 UC` | `1 UM` | — |
| S4 · Padrão | 35% | `0,75 UC` | `2 UM` | — |
| S5 · Padrão | 35% | `0,75 UC` | `2 UM` | — |
| S6 · Longa | 50% | `1,25 UC` | `4 UM` | — |

Totais por Região: Principais **7,5 UC + 11 UM + 2 Equipamentos**; Secundárias **4,5 UC + 10 UM**; total **12 UC + 21 UM**. Jornada completa: **72 UC convertidos no nível recomendado de cada Missão**, com cada recompensa monetária calculada como `round_10(C(n)×UC)`, totalizando exatamente **41.330 Coroas**, **126 UM = 252 materiais vinculados** e **12 Equipamentos de Campanha garantidos**. P3 de cada Região = **Raro**; P6 Regiões 1–5 = **Épico**; P6 Confins do Véu = **Lendário**; sempre `item_level = nível recomendado`, `+0`, Vinculado ao Adquirir, escolha entre 3 opções válidas.

XP de Masmorra repetível é normalizada por tempo, substituindo percentuais fixos antigos: `XP_por_hora(reference_level) × duração_referência × eficiência`. Estável `30m ×1,00`; Fraturada `35m ×1,05`; Ruptura `42,5m ×1,10`. Primeira Conclusão recebe **+60% sobre a recompensa repetível** daquela run.

Legado: XP elegível de reprogressão `I 1,75× / II 2,00× / III 2,25× / IV 2,50× / V 2,75×`. Não multiplica Coroas, Saque, Vigor ou materiais. Respec de Marcas de Legado: **5.000 Coroas + Recarga de 7 dias**, em local seguro.

### 49.8 Equipamentos, Runas e Encantamentos

8 slots com `SlotWeight` técnico de orçamento/custo: Principal 18, Secundária 10, Cabeça 10, Torso 16, Mãos 10, Pés 10, Acessório 12, Artefato 14 = 100 de `SlotWeight`; 2H = 28, equivalente a Principal + Secundária. `SlotWeight` não representa Peso físico, carga ou equip load.

`EconomySW` — abreviado documentalmente como `SW` — é um multiplicador econômico **discreto e diferente de `SlotWeight`**: slots de `SlotWeight 10 → SW1`; Acessório/Artefato/Torso/Principal → `SW2`; 2H → `SW3`. Implementações não devem tratar `SW` e `SlotWeight` como o mesmo campo.

Raridade/budget: Comum `1,00`; Raro `1,07`; Épico `1,15`; Lendário `1,24`; Mítico `1,45`. Secundários: `0/1/2/3/4`. Máximo de **1 Mítico equipado**.

`G(n)=4^((n−60)/59)`. Núcleo Comum +0 Nv.60 por slot: Principal ATQ25; Secundária ATQ7 DEF5; Cabeça HP45 DEF6; Torso HP95 DEF12; Mãos ATQ10 DEF5; Pés HP60 AGI8; Acessório HP50 ATQ7 AGI4; Artefato HP55 ATQ7 DEF5 AGI4. Conjunto: HP305 ATQ56 DEF33 AGI16. Valores intermediários = `round_half_up(Value60 × G(n))`.

Aprimoramento garantido +0→+10 usa multiplicadores **totais** sobre o valor-base do item: `+0=1,00×`; `+1=1,02×`; `+2=1,04×`; `+3=1,06×`; `+4=1,08×`; `+5=1,10×`; `+6=1,125×`; `+7=1,15×`; `+8=1,175×`; `+9=1,20×`; `+10=1,25×`. Bônus acumulado equivalente: `0/2/4/6/8/10/12,5/15/17,5/20/25%`. Sem falha/downgrade/destruição.

Pools de secundários de Equipamento:

| Slot | Secundários elegíveis |
|---|---|
| Principal | ATQ, AGI, PER, CRIT |
| Secundária | ATQ, DEF, PER, CRIT, Bloqueio |
| Cabeça | HP, DEF, PER, CRIT |
| Torso | HP, DEF, Bloqueio |
| Mãos | ATQ, AGI, PER, CRIT |
| Pés | HP, DEF, AGI, Esquiva |
| Acessório | HP, ATQ, AGI, PER, CRIT, Esquiva |
| Artefato | HP, ATQ, DEF, PER, CRIT, Bloqueio |

Não existem restrições automáticas de Classe/Caminho por secundário além de requisito explícito do item.

Premium budget secundário = `SlotWeight × (RarityMult−1)` dividido pelo número de secundários. Por 1,0 budget no Nv.60: HP8,5; ATQ1,35; DEF2,30; AGI3,00; PER0,80 p.p.; CRIT0,67 p.p.; Esquiva0,33 p.p.; Bloqueio0,95 p.p. Percentuais usam `Q(n)=sqrt(G(n))`, passos de 0,25 p.p. e mínimo positivo 0,25 p.p.

2H ofensiva Comum Nv.60: ATQ35. Reroll troca somente a identidade de um secundário selecionado por outra identidade legal sem duplicata; a magnitude é recalculada deterministicamente para o novo atributo com o mesmo share de budget da instância.

Runas: 1 slot por item normal; 2 em 2H; máximo 8. Raridades Rara/Épica/Lendária. Grau VI: HP/ATQ `+0,60/+0,80/+1,00%`; DEF/AGI `+1,0/+1,4/+1,8%`; PER/CRIT `+0,50/+0,75/+1,00 p.p.`; Esquiva `+0,25/+0,50/+0,50`; Bloqueio `+0,50/+0,75/+1,00`. Enchant: HP/ATQ `0,20/0,35/0,50%`; DEF/AGI `0,40/0,70/1,00%`; PER/CRIT `0,25/0,50/0,75 p.p.`; Esquiva `0,25/0,25/0,50`; Bloqueio `0,25/0,50/0,75`.

Pools compatíveis de Runas/Encantamentos:

| Slot | Efeitos elegíveis |
|---|---|
| Principal | ATQ, AGI, PER, CRIT |
| Secundária | ATQ, DEF, PER, CRIT, Bloqueio |
| Cabeça | HP, DEF, PER, CRIT |
| Torso | HP, DEF, Bloqueio |
| Mãos | ATQ, DEF, AGI, PER, CRIT |
| Pés | HP, DEF, AGI, Esquiva |
| Acessório | HP, ATQ, AGI, PER, CRIT, Esquiva |
| Artefato | HP, ATQ, DEF, PER, CRIT, Bloqueio |

Arma 2H possui duas Runas: afinidade A usa o pool de Principal e afinidade B usa o pool de Secundária. 2H possui **um** Encantamento; sua potência é `×2` apenas quando o efeito existe em ambos os pools — ATQ, PER ou CRIT — e é normal quando existe em apenas um.

Graus I–VI de Runas/Encantamentos escalam pelo `Q(teto_do_Grau)`: I `0,556`; II `0,625`; III `0,703`; IV `0,791`; V `0,889`; VI `1,000`. Percentuais de HP/ATQ/DEF/AGI arredondam em 0,05 p.p.; PER/CRIT/Esquiva/Bloqueio em 0,25 p.p.

### 49.9 Saque, materiais e Desmontagem

Por encontro economicamente válido existem rolls separados de materiais, Equipamento, Runa e especial; seed individual persistida antes da apresentação.

Chance de Equipamento em Caçada: Comum `8%`; Incomum `14%`; Elite `35%`; Chefe `70%`. Raridade condicional: Comum `78/19/2,8/0,2/0%`; Incomum `65/29/5,5/0,5/0`; Elite `45/42/11/1,9/0,1`; Chefe `25/45/25/4,7/0,3` para Comum/Raro/Épico/Lendário/Mítico.

Masmorra concede 1 roll garantido por conclusão elegível; tabela: Estável `25/50/22/2,8/0,2`; Fraturada `10/45/38/6,5/0,5`; Ruptura `0/20/60/19/1`. Pity de Masmorra: pontos `1/2/4` por Estável/Fraturada/Ruptura; hard pity Lendário+ **24 pontos**; hard pity Mítico **200 pontos**. Hunt pity: 12 drops de Equipamento Elite/Chefe sem Épico+ → próximo ≥Épico; 50 sem Lendário+ → próximo ≥Lendário.

Chance de Runa em Caçada: Comum `0,5%`; Incomum `1,5%`; Elite `5%`; Chefe `12%`. Raridade: Comum/Incomum `90/9,5/0,5`; Elite `80/18/2`; Chefe `65/31/4`. Masmorra: chance de Runa Estável `20%`, Fraturada `35%`, Ruptura `50%`; raridade `70/28/2`, `55/40/5`, `35/55/10`.

#### Materialização de Equipamento de Saque

A chance de Equipamento, a raridade resultante e qualquer promoção por pity são resolvidas antes desta etapa e não são rerroladas durante a materialização.

Toda fonte repetível que use o gerador normal de Saque possui `loot_reference_level`:

- Caçada e encontro econômico baseado em criatura: `loot_reference_level = enemy_level` já materializado;
- resultado de Desbravar que gere combate econômico normal: mesma referência do `enemy_level` do encontro;
- Masmorra: `loot_reference_level = dungeon_reference_level`; Estável/Fraturada usam a referência regional configurada e Ruptura usa `60`;
- outra fonte que reutilize este gerador deve declarar explicitamente sua referência; não existe fallback silencioso para o nível atual do personagem.

Para Equipamento de Saque, `item_level = loot_reference_level`, limitado a `1–60`, e a instância usa o materializador global da seção 24.6.

A seleção normal usa oito grupos: `Principal / Secundária / Cabeça / Torso / Mãos / Pés / Acessório / Artefato`. Arma 2H não constitui nono grupo: templates 2H participam do grupo `Principal` e, depois de materializados, ocupam Principal e bloqueiam Secundária pelas regras normais.

O gerador filtra primeiro templates regionais normais explicitamente elegíveis para Saque genérico. Equipamentos exclusivos de Campanha, Receita especial ou fonte específica ficam fora salvo configuração explícita. Depois aplica a elegibilidade da raridade/quantidade de secundários da seção 24.6. Grupos que ficarem vazios são removidos.

Na ausência de pesos explícitos, a seleção do grupo é uniforme e a seleção do template dentro do grupo também é uniforme. Conteúdo pode fornecer pesos explícitos. `SlotWeight`, `SW`, Classe, Caminho, equipamento atual ou necessidade percebida do personagem nunca funcionam implicitamente como peso de drop.

A disponibilidade de uma raridade no Crafting não limita a raridade possível do template em Saque: um template regional normal pode materializar como Comum/Raro/Épico/Lendário/Mítico quando a tabela de Saque produzir aquela raridade, sem conceder Receita de Crafting correspondente.

Equipamento genérico de Saque nasce `+0`, sem Runa, sem Encantamento e **Negociável**, salvo regra explícita de bind da fonte/template.

#### Materialização de Runa de Saque

A Runa usa o mesmo `loot_reference_level` da fonte econômica que a originou. Seu Grau é `1–10→I / 11–20→II / 21–30→III / 31–40→IV / 41–50→V / 51–60→VI`, equivalente a `floor((loot_reference_level−1)/10)+1`, limitado a I–VI. Em Masmorra Ruptura, a referência 60 produz Runa Grau VI mesmo quando a família/nomenclatura é regional de conteúdo anterior.

Depois de resolvida a raridade, seleciona-se uma família entre as famílias regionais normais elegíveis. Na ausência de pesos explícitos, a seleção é uniforme. Não existe smart loot automático por Classe, Caminho, build, Inventário ou slots atuais.

Compatibilidade com slot de Equipamento **não filtra o drop da Runa**; ela existe como componente independente e sua compatibilidade de efeito/Grau é validada somente na instalação.

Potência deriva exclusivamente de família/efeito + raridade + Grau pelas tabelas/fórmulas globais. Runa genérica de Saque nasce **Negociável**, salvo regra explícita da fonte/família.

#### Determinismo do materializador de Saque

A seed individual já persistida pela fonte governa toda materialização. Implementações devem usar decisões determinísticas estáveis para grupo/slot, template, secundários e família de Runa; subdraws identificados como `equipment.slot`, `equipment.template`, `equipment.secondary.N` e `rune.family` são uma forma válida de evitar dependência acidental da ordem interna de chamadas.

Depois que uma `item_instance` ou `rune_instance` existir, recovery carrega a instância persistida em vez de executar novamente a materialização. Criação/entrega usa chave idempotente equivalente a contexto econômico + destinatário + tipo de roll + ordinal; processamento duplicado nunca produz segunda instância.

Materiais básicos por Região: Metal, Couro, Reagente, Essência × Graus I–VI = 24 materiais-base. Recursos especiais: Catalisador de Elite por Grau, Núcleo de Chefe por família, Fragmento de Aprimoramento por Grau e, quando configurado, Núcleo de Masmorra por `dungeon_family_id`. Graus de Fragmento por item level: `1–10 I / 11–20 II / ... / 51–60 VI`; sem conversão automática para Grau superior.

Caçada: Comum `80%→1` material básico; Incomum `100%→1–2`; Elite `3–4` garantidos +1 Catalisador; Chefe `5–7` +2 Catalisadores +1 Núcleo de Chefe. Fragmento: Comum 0; Incomum `5%→1`; Elite `40%→1`; Chefe `2` garantidos.

Masmorra por conclusão: Estável `8 básicos,2 Catalisadores,1 Núcleo de Masmorra,2 Fragmentos`; Fraturada `11,3,2,4`; Ruptura `14,4,4,7`.

Desmontagem por `EconomySW` (`SW`): slots de `SlotWeight 10→SW1`; Acessório/Artefato/Torso/Principal→`SW2`; 2H→`SW3`. Comum `1 básico×SW`; Raro `2 básicos×SW +1 Fragmento×SW`; Épico `3 básicos×SW + ceil(SW/2) Catalisador +2 Fragmentos×SW`; Lendário `4 básicos×SW +1 Catalisador×SW +4 Fragmentos×SW`; Mítico `6 básicos×SW +2 Catalisadores×SW +8 Fragmentos×SW`. Aprimoramento não aumenta retorno; Núcleos usados na criação não retornam.

Descoberta de Receita especial quando há desconhecida elegível: Comum 0; Incomum 0; Elite 1%; Chefe 6%; Masmorra Estável 8%; Fraturada 15%; Ruptura 25%. Seleciona apenas desconhecidas; sem duplicatas. `Elegível` aqui significa permitida pela fonte/progressão/condições explícitas do Conteúdo e ainda desconhecida; não exige Ofício ativo nem nível de Ofício. Exceção determinística só existe quando o Conteúdo declarar explicitamente revelação direta/garantida.

### 49.10 Economia

`C(n)=round_10(100+15n)` é a unidade econômica de Coroas por nível: Nv1 120; Nv10 250; Nv20 400; Nv30 550; Nv40 700; Nv50 850; Nv60 1.000.

Caçada: Comum `0,05×C`; Incomum `0,08×C`; Elite `0,25×C`; Chefe `0,60×C`. Masmorra: Estável `0,80×C`; Fraturada `1,20×C`; Ruptura `1,80×C`. Desbravar econômico: `0,10–0,25×C` conforme perfil.

Troca de Caminho: `1,5×C(nível atual)`; Nv60 **1.500**. Respec de Talentos: `2×C`; Nv60 **2.000**. Renomear Personagem: **2.500 Coroas + 30 dias**. Travessia dos Braseiros: **0 Coroas**.

Aprimoramento — base por Grau: I30, II60, III100, IV160, V240, VI340. Raridade: Comum1,00; Raro1,05; Épico1,15; Lendário1,30; Mítico1,60. Fator da etapa para +1…+10: `1,0/1,1/1,2/1,4/1,6/1,9/2,2/2,6/3,1/3,7`. Fórmula: `BaseGrau × SlotWeight/10 × RarityCost × StepFactor`, arredondada para 10. Full set Grau VI Lendário +10 ≈ **87.500 Coroas**.

Fragmentos por `SW` para etapas +1…+10: `1,1,1,1,2,2,3,3,4,5`; total **23×SW**; conjunto completo = **276 Fragmentos**.

Reroll por `item_instance`: `0,50 / 0,75 / 1,00 / 1,50 / 2,00×C(item_level)` no 1º/2º/3º/4º/5º+; contador não reseta por troca/equip/aprimoramento/componentes.

Mercado e Serviços: taxa **5%** sobre pagamento ao vendedor/prestador; sem taxa de anúncio/cancelamento. Compra parcial usa taxa acumulada `floor(gross_sold_total×0,05)` para impedir exploração por arredondamento. Loja: **6 listings de itens** e **3 ofertas de Serviço** simultâneas; ambos expiram em **7 dias**. Preço de Serviço pode ser editado diretamente com incremento de `service_offer_revision`; previews antigos são invalidados. Alterar Receita/output exige cancelar e recriar a oferta.

Dádiva Diária, ciclo de 7 claims: D1 100 Coroas; D2 2 básicos vinculados; D3 1 Fragmento vinculado; D4 150 Coroas; D5 4 básicos; D6 2 Fragmentos; D7 250 Coroas +2 Fragmentos. Total: **500 Coroas +6 básicos +5 Fragmentos**.

Obras da Guilda I–V: `20k/35k/60k/100k/160k` Coroas; construção `6h/12h/24h/48h/72h`; total 375k por Obra. 7 Obras = 2,625M. Alojamentos: base5→7→9→10→11→12. Renome de Guilda/TAG: **15.000 Coroas da Tesouraria +30 dias**, uma operação pode alterar Nome, TAG ou ambos.

### 49.11 Ofícios e Crafting

Caps: Principal **Nv.30**, Secundário **Nv.15**. Inverter ativos: `0,50×C(nível)`; substituir um Ofício: `1,00×C(nível)`, sem Recarga temporal.

PXP: `round_10(100+20n+5n²)` para `n→n+1`, total `1→15 = 8.540`, `1→30 = 54.300`. PXP por Receita: `80+20×required_profession_level`. Anti-spam usa Grau econômico: Grau atual 100%; 1 abaixo 50%; 2 abaixo 20%; ≥3 abaixo 0. Referência de planejamento: cerca de **43 crafts relevantes até Nv.15** e **170 até Nv.30**; a curva de PXP é autoritativa, não uma quantidade fixa de crafts.

Grau/Requisito de Ofício: I1, II3, III6, IV9, V12, VI15. Raridade: Comum1, Raro5, Épico10, Lendário16 + Receita especial, Mítico26 + Receita específica.

Equipamento craftado por `SW`: Comum `5 básicos`; Raro `8 básicos +4 Fragmentos`; Épico `10 básicos +2 Catalisadores +6 Fragmentos`; Lendário `14 básicos +4 Catalisadores +12 Fragmentos +1 Núcleo`; Mítico no mínimo `20 básicos +8 Catalisadores +20 Fragmentos +3 Núcleos especiais` por SW. Craft sempre +0, sem falha; secundários respeitam o mesmo budget do Saque.

Taxa de Crafting de Equipamento: `C(n)×SW×RarityFactor`, com fatores Comum0,25/Raro0,35/Épico0,50/Lendário0,75. Receita Mítica não é genérica.

Runas — taxa Nv60 Rara/Épica/Lendária `300/600/1.000`; materiais: Rara `4 Essências+2 Metal+2 Fragmentos`; Épica `7 Essências+3 Metal+1 Catalisador+4 Fragmentos`; Lendária `10 Essências+4 Metal+2 Catalisadores+8 Fragmentos`.

Encantamentos — taxa Nv60 `200/400/700`; materiais: Raro `3 Essências+1 Metal`; Épico `5 Essências+2 Metal+1 Catalisador`; Lendário `8 Essências+3 Metal+2 Catalisadores+3 Fragmentos`.

Ferreiro: 7 famílias (Principal, Secundária, 2H, Cabeça, Torso, Mãos, Pés), baseline 70% Metal/30% Essência. Curteiro: Cabeça/Torso/Mãos/Pés, 70% Couro/30% Reagente. Joalheiro: Acessório/Artefato, 60% Metal/40% Essência. Artífice: 8 famílias de Runas +8 de Encantamentos. Alquimista: Cura, Purificação, Antídoto, Vigor, Proteção, Dissipador, Resguardo.

#### Item level de Equipamento craftado

O `item_level` de um Equipamento craftado é determinado pelo nível atual do destinatário, limitado à faixa do Grau da Receita:

| Grau | item_level permitido |
|---|---|
| I | 1–10 |
| II | 11–20 |
| III | 21–30 |
| IV | 31–40 |
| V | 41–50 |
| VI | 51–60 |

`item_level = min(nível_atual_do_destinatário, teto_do_Grau)`

O destinatário deve atender ao piso do Grau. Em Craft próprio, destinatário = próprio personagem; em Serviço, destinatário = cliente. O Preview calcula e exibe o `item_level`; o commit revalida nível, Grau, Receita, Ofício, materiais e preço. O jogador não escolhe livremente um `item_level` futuro.

Para qualquer origem de Equipamento, inclusive Crafting, Campanha e Saque, a regra de equipar permanece global: **nível atual do personagem ≥ `item_level`**. O `item_level` já materializado é o requisito de nível do item.

#### Arredondamento das proporções de Materiais Básicos

`Primário = floor(Total × Proporção_Primária + 0,5)`

`Secundário = Total − Primário`

O arredondamento ocorre uma única vez sobre o total da Receita após o `SW`; não arredondar cada unidade de `SW` separadamente. Mantêm-se Ferreiro `70% Metal / 30% Essência`, Curteiro `70% Couro / 30% Reagente` e Joalheiro `60% Metal / 40% Essência`. Catalisadores, Fragmentos e Núcleos não participam dessa proporção.

#### Taxas de Runas por Grau

A potência continua escalando por `Q(Grau)`. A taxa econômica escala por `C(teto_do_Grau)` em relação ao valor oficial do Grau VI:

`Taxa(Grau) = round_10(Taxa_GrauVI × C(teto_do_Grau) / C(60))`

Com `C(60)=1.000`:

| Grau | Rara | Épica | Lendária |
|---|---:|---:|---:|
| I | 80 | 150 | 250 |
| II | 120 | 240 | 400 |
| III | 160 | 330 | 550 |
| IV | 210 | 420 | 700 |
| V | 260 | 510 | 850 |
| VI | 300 | 600 | 1.000 |

As quantidades de materiais por raridade permanecem as já vigentes; apenas o Grau dos materiais acompanha o Grau da Runa.

#### Taxas de Encantamentos por Grau

`Taxa(Grau) = round_10(Taxa_GrauVI × C(teto_do_Grau) / C(60))`

| Grau | Raro | Épico | Lendário |
|---|---:|---:|---:|
| I | 50 | 100 | 180 |
| II | 80 | 160 | 280 |
| III | 110 | 220 | 380 |
| IV | 140 | 280 | 490 |
| V | 170 | 340 | 600 |
| VI | 200 | 400 | 700 |

Materiais por raridade permanecem os já vigentes.

### 49.12 Consumíveis e Vigor

Poção de Cura: **22% HP Máximo**, própria, 1 ação, não Crita, sofre Cura recebida e não ativa recursos/Talentos que exigem Arte. Purificação: remove 1 efeito negativo removível conforme regra normal. Antídoto: remove todos os stacks de um único DoT removível selecionado. Poção de Vigor: **+20**, fora de combate, máximo **1 uso por ciclo diário**, só quando Vigor≤80, sem ultrapassar 100; não vendida por dinheiro real.

Preparado de Proteção: somente em combate PvE; Barreira `floor(12% × HP Máximo)` por `2T`; mesma fonte não acumula e nova aplicação substitui valor e duração. Dissipador: somente em combate PvE; remove 1 efeito positivo removível selecionado de 1 inimigo válido, sem RNG próprio; não-stack é removido integralmente e efeito stackável perde 1 stack, o mais antigo. Preparado de Resguardo: somente em combate PvE; `2T`, `1 carga`; bloqueia a primeira aplicação elegível de efeito negativo removível que efetivamente teria sucesso, sem bloquear o Dano Direto associado; não bloqueia Hard CC, mecânica fixa ou efeito protegido por default.

Todos os Consumíveis de combate compartilham **CD2**. Uso válido consome **1 ação + 1 unidade + 1 uso do limite normal** da atividade. Tentativa rejeitada antes do commit não consome unidade, ação, limite nem CD2.

Limites por encontro: Comum1, Incomum1, Elite2, Chefe3. Masmorra por run: Estável6, Fraturada5, Ruptura4. Evento Mundial: 2 por ocorrência. Juramento: 3 por Provação. PvP: nenhum Consumível externo.

A Ronda permanece automatizando somente **Poção de Cura** e **Consumível de Purificação** conforme suas regras vigentes. Proteção, Dissipador e Resguardo não entram automaticamente na preparação/IA da Ronda.

#### Alquimia Graus I–VI

Os efeitos das sete famílias de Consumíveis permanecem independentes do Grau. As quantidades de materiais permanecem constantes por família; o Grau dos materiais acompanha o Grau da Receita. Famílias com Grau mínimo superior simplesmente não possuem Receita nos Graus anteriores:

- Cura: `3 Reagentes +1 Essência`;
- Purificação: `2 Reagentes +2 Essências`;
- Antídoto: `4 Reagentes +1 Essência`;
- Vigor: `6 Reagentes +4 Essências +1 Catalisador`;
- Proteção: `3 Reagentes +2 Essências`, Grau mínimo II, requisito de família Alquimista5, Taxa Grau VI `200`;
- Dissipador: `2 Reagentes +3 Essências`, Grau mínimo III, requisito de família Alquimista10, Taxa Grau VI `250`;
- Resguardo: `4 Reagentes +2 Essências`, Grau mínimo IV, requisito de família Alquimista12, Taxa Grau VI `300`.

Taxa:

`Taxa(Grau) = round_10(Taxa_GrauVI × C(teto_do_Grau) / 1.000)`

| Grau | Cura | Purificação | Antídoto | Vigor | Proteção | Dissipador | Resguardo |
|---|---:|---:|---:|---:|---:|---:|---:|
| I | 20 | 40 | 40 | 120 | — | — | — |
| II | 40 | 60 | 60 | 200 | 80 | — | — |
| III | 60 | 80 | 80 | 280 | 110 | 140 | — |
| IV | 70 | 100 | 100 | 350 | 140 | 180 | 210 |
| V | 80 | 130 | 130 | 420 | 170 | 210 | 260 |
| VI | 100 | 150 | 150 | 500 | 200 | 250 | 300 |

Requisitos de Grau permanecem I1, II3, III6, IV9, V12, VI15. Para uma Receita com requisito próprio de família/raridade:

`required_profession_level = max(requisito_do_Grau, requisito_da_família/raridade)`

Requisitos finais das novas famílias:

| Grau | Proteção | Dissipador | Resguardo |
|---|---:|---:|---:|
| I | — | — | — |
| II | Alquimista5 | — | — |
| III | Alquimista6 | Alquimista10 | — |
| IV | Alquimista9 | Alquimista10 | Alquimista12 |
| V | Alquimista12 | Alquimista12 | Alquimista12 |
| VI | Alquimista15 | Alquimista15 | Alquimista15 |

#### Proteção — fechamento numérico

- Barreira: `floor(12% × HP Máximo)`.
- Duração: `2T`.
- Fonte: `applier_id + consumable.protecao`.
- Reaplicação substitui Barreira restante e duração; não soma nem cria segunda instância.
- Grau mínimo II; Alquimista5; `3 Reagentes +2 Essências`; Taxa Grau VI `200`.

#### Dissipador — fechamento numérico/operacional

- Remove `1 efeito positivo removível selecionado` de 1 inimigo válido.
- Não possui teste de acerto, resistência percentual própria ou RNG de Dispel.
- Efeito não-stack: remoção integral.
- Efeito stackável: remove `1 stack`, o mais antigo.
- Estados `unremovable`, fases, mecânicas fixas, efeitos protegidos de Chefe e Buffs explicitamente não dissipáveis são inelegíveis.
- Grau mínimo III; Alquimista10; `2 Reagentes +3 Essências`; Taxa Grau VI `250`.

#### Resguardo — fechamento numérico/operacional

- `Resguardo · 2T · 1 carga`.
- Intercepta somente uma aplicação que, após imunidade absoluta e resistência/redução válida, ainda seria efetivamente aplicada.
- Elegíveis por padrão: DoT removível; Debuffs numéricos removíveis de ATQ/DEF/AGI/PER/CRIT/Bloqueio/Esquiva; redução removível de Cura Recebida; outro Debuff numérico removível; restrição removível de ação que não seja Hard CC.
- Não elegíveis: Hard CC; Stun/efeito que consome integralmente a oportunidade; fase/mecânica fixa; `unremovable`; efeito protegido de Chefe; marca/recurso interno fora do framework normal de Debuffs.
- Para efeitos especiais fora das categorias padrão, `resguardo_eligible = false` por default; conteúdo/sistema pode declarar explicitamente `true/false`.
- Multi-stack do mesmo efeito em um único `application_event`: bloqueia todos os stacks daquela aplicação e consome 1 carga.
- Eventos independentes: bloqueia somente o primeiro evento elegível na ordem autoritativa; a carga desaparece antes dos seguintes.
- Reaplicação não acumula: mantém 1 carga e reinicia `2T`.
- Grau mínimo IV; Alquimista12; `4 Reagentes +2 Essências`; Taxa Grau VI `300`.

Vigor: máximo100; `+1` a cada 14m24s; reset 06:00 não reabastece. Caçada/Ronda **2** por encontro econômico; Desbravar econômico **4**; Masmorra Estável25/Fraturada35/Ruptura50. PvP/Crafting/Mercado não gastam. Legado não recupera.

Ronda: lotes 5/10/20, 3min por encontro; recovery threshold 50% HP, safety threshold 35%, crítico≤30%, Cura efetiva mínima 10% HP. Ordem determinística: evitar morte previsível por efeito removível → Arte de recuperação crítica → Poção crítica → Purificação critical → Arte de recuperação baixa → Poção baixa → Purificação high → defesa/Barreira em perigo → Defender → melhor Arte ofensiva → Ataque Básico. Perigo: HP≤35% ou ataque telegráfico conhecido ≥30% HP antes da próxima oportunidade. AoE ofensivo ganha prioridade com ≥2 alvos; não reaplica DoT no cap/Debuff sem valor nem setup em alvo estimado para morrer na próxima ação direta. As três novas famílias não alteram essa prioridade enquanto não houver aprovação explícita de automação própria.

### 49.13 Masmorras

Lançamento: **12 Masmorras, 2 por Região**. Faixas por Região iniciada em L: A `L+3→L+6`; B `L+7→L+9`. Estável desbloqueada por descoberta/requisitos; Fraturada exige Primeira Conclusão Estável; Ruptura exige Nv.60 + Primeira Conclusão Fraturada.

Estável/Fraturada usam referência regional; **Ruptura usa `dungeon_reference_level=60`** em todas as 12 Masmorras, substituindo a interpretação antiga que tornaria Saque regional obsoleto no endgame.

Baseline: **5 encontros**: introdutório; misto; Elite/minichefe; mecânico/Elite; Chefe final. Duração ativa: Estável25–35m; Fraturada30–40m; Ruptura35–50m. Braseiro: `70%/40%/20%`, no máximo 1, após encontro 3; existência sorteada uma vez por run e oculta até descoberta. Retry ilimitado enquanto a mesma run válida existir; Consumíveis e Vigor reservado não resetam. Expiração: **4h de inatividade / 24h absoluta**.

Confirmação de Entrada após Pareamento: **60s**. Scaling congela no tamanho inicial; sem reposição no lançamento.

### 49.14 Arena da Vigília e Batalha de Guildas

Duelo: **Nv.10**. Arena: **Nv.30+**, 1v1, sem normalização, sem Consumíveis externos, sem Vigor. Janelas diárias: **12:00–13:00 e 19:00–20:00**, America/Sao_Paulo.

Renome/Elos: Brasa III 0–199; Brasa II 200–399; Brasa I 400–599; Chama III 600–799; Chama II 800–999; Chama I 1000–1199; Forjado III 1200–1399; II 1400–1599; I 1600–1799; Ascendente III 1800–1999; II 2000–2199; I 2200–2399; Arauto III 2400–2599; II 2600–2799; I 2800–2999; Regente ≥3000.

Placement inicial: 5 partidas; Renome por vitórias `0→400,1→600,2→800,3→1000,4→1200,5→1400`. Depois, `E=1/[1+10^((Rop−Rjog)/400)]`; `Δ=round(40×(S−E))`. Floor 0.

MMR oculto: inicial1500; K48 nas primeiras20 partidas da carreira, depois K32; persiste entre Crônicas. Pareamento: 0–45s ±100 MMR/±3 níveis; 45–90 ±175/±5; 90–150 ±275/±8; 150–240 ±400/±12; 240s+ ±500/±15; hard cap 15 níveis. Confirmação 45s. Turno PvP 90s; 2 timeouts consecutivos ou 3 totais = derrota por AFK. Rendição a partir da Rodada5. Dodge/no-show em 60min: 1º sem penalidade, 2º 5m, 3º 15m, 4º+30m.

Exaustão: Cura/Barreira 100% R1–19, 90 R20, 80 R21, 70 R22, 60 R23, 50 R24, 35 R25+. Ruptura Final R25. Dano R26+ = `1+0,10×(R−25)`.

Decay: Arauto III+ (≥2400), após 7 dias sem partida; cada segunda 06:00 `−50`, floor2399. Soft reset de Crônica: `1000+0,5×(Rantigo−1000)`, min400/max2400. Recompensa de Elo exige ≥20 partidas; Regente ≥3000 e ≥30 partidas.

Batalha de Guildas: quarta e domingo **21:00**; Frente I2v2 + Frente II3v3; 5 combatentes únicos; até 2 reservas administrativas; Campeão entre os 5. Inscrição abre 24h antes, fecha20:30; confirmação até20:50; início21:00. Turno60s; mesma regra AFK. Rating técnico Guilda1500, K48 primeiras5 batalhas reais, depois32, persiste entre Crônicas. Classificação: vitória3/empate1/derrota0/bye0; mínimo **10 batalhas reais** para recompensa final; indivíduo ≥4 participações reais. Bye sem vitória/rating/recompensa.

### 49.15 Desbravar, Evento Mundial, Expedição e Juramento

Desbravar: Recarga **5min**; máximo **6 tentativas/Local/60min**. Pool-base: grande descoberta8%, conhecimento22%, narrativo15%, combate25%, pequeno recurso10%, atmosférico20%, redistribuindo apenas entre resultados elegíveis. Conteúdo obrigatório elegível tem proteção de 3 tentativas. Anti-repetição: resultado imediatamente anterior peso0; se apareceu nas últimas3, peso×0,35. Pequeno recurso: `0,10×C +1 básico`; combate repetível genérico: `0,15×C +1 básico +20% de +1`; ambos custam 4 Vigor quando concedem economia.

Eventos Mundiais: terça/quinta/sábado **12:00 e 20:00**; 3 fases; duração30–45m, deadline60m; entrada primeiros15m ou até fase final. HP scale por fase `N^0,88`, N cap200; ATQ `+1,5%` por participante adicional, cap+60%; snapshot por fase. Elegibilidade: ≥2 fases +8 Ações Significativas; objetivo `major_contribution` vale4. Reentrada após derrota2m. Economia: 10 Vigor → `0,40×C +2 básicos +1 Fragmento`; XP8% do requisito do nível de referência.

Sintonização do Véu: `Lsync=min(Ljogador, Levento+5)`; atributos inerentes recalculados em Lsync e parcelas planas de Equipamento acima dele reduzidas pela curva G; identidade/Artes/Talentos/raridade/secundários/Runas/Encantamentos permanecem.

Expedição: 1/Guilda/semana; seg18:00→qui18:00; roster3–6; 3 estágios de24h; 1 escolha ativa/membro/estágio, default explícito em ausência; score0–300: Fracassada0–99, Concluída100–179, Profunda180–239, Excepcional240–300. Recompensa individual requer ≥2 estágios ativos: Concluída `0,50×C+3 básicos`; Profunda `0,80×C+5 básicos+1 Fragmento`; Excepcional `1,25×C+8 básicos+3 Fragmentos`. Tesouraria: 1.500/3.000/5.000 Coroas.

Juramento: sex18:00→dom18:00, grace30m; **3 Provações por personagem/ciclo**. Cada Provação: objetivos `10/15/20` + conclusão `15` =60 máximo. Máximo individual180; elegibilidade individual ≥60. Faixas coletivas: 120/300/540/780. Consumíveis3/Provação. Tesouraria por faixa: 2k/4k/7k/10k. Recompensa individual: I `0,50×C+4 básicos`; II `0,75×C+6 básicos+1 Fragmento`; III `1,00×C+8 básicos+2 Fragmentos+1 Catalisador`; IV `1,25×C+10 básicos+3 Fragmentos+1 Catalisador`.

### 49.16 Crônica e Trilha

Crônica: **8 semanas / 8 capítulos**, desbloqueio a cada 7 dias. Trilha: **40 Marcos**, 100 pontos cada, máximo4.000. Cada capítulo oferece500 pontos únicos: conclusão250 + objetivos/descobertas250. Conteúdo repetível associado:25 pontos/conclusão, catch-up acumulado `150 × semanas liberadas`, máximo1.200. Oportunidade total5.200 para completar4.000.

Camada Livre: 20 Marcos (pares), economia total máxima **5.000 Coroas +30 básicos vinculados +20 Fragmentos vinculados +5 recompensas não econômicas**. Premium: 10 Marcos (múltiplos de4), exclusivamente cosmético/prestígio, zero economia/poder.

Voto final: elegível com ≥4/8 capítulos +1 objetivo da fase final. Votação principal fecha `T−48h`; empate → runoff24h; empate persistente → desfecho neutro predefinido. `cycle_end_at=T`; grace de finalização2h; finalização real T+2h. Pós-Crônica: 14 dias apenas para resgates já desbloqueados, depois liquidação automática.

### 49.17 Bestiário, Códice e Flavor Text

Bestiário usa BKP oculto. Comum: Conhecido10/Estudado30/Dominado60; Estudado exige ≥2 categorias, Dominado ≥3. Rara8/22/40 e ≥2 categorias para Dominado. Elite10/25/45, com vitória/mecânica especial e evidências especiais. Chefe10/30/50; Estudado exige 1 vitória +2 mecânicas/fases; Dominado exige `mastery_required` completo.

Mapeamento técnico entre Categoria de Combate e perfil interno do Bestiário:

| Categoria de Combate | Perfil interno do Bestiário |
|---|---|
| Comum | `COMMON` |
| Incomum | `RARE` |
| Elite | `ELITE` |
| Chefe | `BOSS` |

`RARE` é nome técnico do perfil BKP e não renomeia player-facing uma criatura Incomum para “Rara”. A progressão player-facing permanece **Observado → Conhecido → Estudado → Dominado**. O identificador interno `mastery_required` pode permanecer técnico para Chefes; a UI apresenta **Dominado** como estágio final.

BKP-base: primeira observação4; primeiro combate3; primeira vitória5; nova Arte/comportamento4; nova mecânica5; Habitat3; investigação Desbravar8; Missão10; Variante descoberta8 + primeira vitória6; forma Elite8 + primeira vitória6. Comum: vitórias2ª–5ª +2, 6ª–10ª +1, marcos15/25/40 +3; demais0. Rara pontua repetição só até5ª. Elite: 2ª+3, 3ª+2, 4ª–5ª+1.

Códice não possui XP genérica. Trechos `multiple`: 2 evidências para corroboração simples, 3 para profundo, 4 para segredo maior; em 3–4 exige ≥2 famílias de fonte distintas. `direct_reveal` pode liberar imediatamente. Progresso técnico permanece oculto.

Flavor: Sistema recomendado80–180 chars, hard220; Narrativo180–360, hard420; micro-combate40–120, hard140. Banco-base: tela de Sistema3; Região6; Local5; Desbravar+3; Masmorra4; Evento/template4; Braseiro importante3. Prioridades100/200/300; peso25–200, normal100. Anti-repeat exclui últimas2 se ≥3 elegíveis. Estabilidade: Sistema6h; contexto narrativo30m; Masmorra por run/contexto; Evento por occurrence+phase; mudança real de estado/spoiler invalida imediatamente.

### 49.18 Limites operacionais, Vínculos, Guildas e lifecycle

Inventário60; Armazém100; Pending20. Nome Público da Loja36 chars; Descrição240; divulgação30m; Buscar Loja20/min com burst5/10s. Inscrições de Guilda: 3 Pendentes simultâneas, máximo6 novas/60min e 1 para mesma Guilda/10min. Troca de Guilda: **12h conta+servidor**. Dissolução: **72h**. Sucessão por inatividade do Líder: **168h**; prioridade Oficial com maior tempo contínuo como Oficial, depois maior tempo na Guilda, depois menor `character_id`; ban definitivo inicia imediatamente.

Exclusão de personagem: 7 dias pendente/cancelável. Nome antigo após Renome ou exclusão definitiva: reservado30 dias. Vínculos: Amigos100; Pedidos enviados20; recebidos30; Recentes30 por14d; Bloqueados100. Busca de jogador20/min. História600 chars; Compartilhar História/Relato CD6h.

Solo PvE manual: expira após **30min sem ação válida**, retomável no mesmo estado antes disso. PvE compartilhado/Grupo: **180s por oportunidade**; timeout perde oportunidade; 3 consecutivos marcam `inactive_for_contribution` até ação válida. Não existe AFK/reconnect global separado. Troca Direta: timeout de inatividade10min, máximo absoluto30min.

### 49.19 Patrono, Chamado e Códigos

Chamado: vínculo até **72h após criação** e antes de Nv.10; recrutador precisa Nv.10+. Nenhuma recompensa por vincular. Marcos do recruta Nv10/Nv30/Nv60: **100/200/300 Coroas para cada lado**. Recrutador recebe economia apenas pelos primeiros10 recrutas válidos por servidor → máximo6.000 Coroas. Prestígio cosmético: 1 recruta Nv10→Título **Guia da Estrada**; 3 Nv30→Título **Voz que Reúne**; 5 Nv60→Moldura **Laço das Cinzas**; 10 Nv60→Moldura **Círculo dos Caminhantes**; 20 Nv60→Aparência **Arauto de Asterion**. Os dois Títulos e as duas Molduras são recompensas distintas. Antiabuso usa flag/análise, não ban automático por IP/dispositivo.

Códigos: 6–24 chars, A–Z/0–9/`-`, case-insensitive; 5 tentativas/min e20/h; expiração padrão30 dias quando não explicitada; padrão1 resgate por conta+servidor. Recompensa promocional normal até `0,50×C +4 básicos vinculados +2 Fragmentos`; hard cap por Código normal `1,00×C +8 básicos +3 Fragmentos`; sem Vigor, XP, Equipamento, Runa, Núcleo, Catalisador, Renome/MMR, Talento, Legado ou progresso de Crônica. Compensação administrativa usa fluxo próprio.

Patrono: um único nível de apoio no lançamento; entitlement de **30 dias**, cumulativo a partir do maior entre agora e `patron_active_until`. Enquanto ativo: reconhecimento visual genérico + Título temporário **Patrono das Cinzas** e Moldura temporária **Vigília do Patrono**. Prestígio permanente por apoio pago válido acumulado: 30d Título **Aliado do Refúgio**; 90d Título **Guardião da Chama**; 180d Moldura **Luz do Refúgio**; 270d Moldura **Chama Perene**; 360d Aparência **Manto do Patrono**. Os dois Títulos e as duas Molduras permanentes são recompensas distintas. Zero benefício de combate, economia, slots, fila, Vigor, Saque ou progressão. Preço real é configuração comercial externa, não parâmetro de balanceamento do GDD.

### 49.20 Status da baseline

A Baseline Numérica v1.0 permanece autoritativa e fechada para implementação e testes. A reabertura pontual da conversão absoluta da unidade de XP de inimigo foi encerrada na v1.4.3 após auditoria matemática da primeira jornada das Terras do Ocaso. A v1.4.6 preservou integralmente a Baseline Numérica v1.0 e incorporou o fechamento global das famílias Preparado de Proteção, Dissipador e Preparado de Resguardo, incluindo seus valores e semânticas já aprovados em Balanceamento. A v1.4.7 formalizou a recompensa condicional do primeiro encontro do Prólogo. A v1.4.8 manteve integralmente a baseline e consolidou a hierarquia global de Cosméticos. **Esta v1.4.9 mantém integralmente todos os valores da baseline e apenas formaliza o fechamento matemático dos atributos primários estáticos finais em pontos inteiros, além do HP atual inteiro, eliminando estados fracionários residuais sem alterar potência efetiva intencional de qualquer bônus.** Faixas como **impacto racial 3–5%**, **jornada saudável 200–250h**, **completionista 300h+**, quantidade típica de ações por tela e comprimentos editoriais de Flavor continuam deliberadamente como **metas/faixas**, não como constantes matemáticas a serem forçadas.

Ajustes posteriores por Alpha/Beta devem ser registrados como mudança de Balanceamento/Telemetria, com versionamento de ruleset/configuração quando afetarem estado persistente ou reprodutibilidade. Novos conteúdos podem introduzir novos parâmetros em `SIMULAR`, mas isso não reabre automaticamente os demais valores acima.

## 50. Fonte de verdade para os próximos chats

Quando outro chat do projeto precisar de uma decisão oficial, deve:

1. Priorizar este documento consolidado v1.5.0 sobre versões históricas/rascunhos.
2. Tratar as regras aqui como oficiais, salvo decisão posterior explicitamente declarada como substituição.
3. A Baseline Numérica v1.0 da seção 49 é autoritativa. Um valor só volta ao estado `SIMULAR` se uma nova mecânica ou uma reabertura explícita de Balanceamento o declarar dessa forma; isso exige versionamento e não invalida silenciosamente a baseline vigente.
4. Se descobrir uma contradição real, registrar o conflito e propor correção pontual, sem reabrir todo o GDD automaticamente.
5. Para Visual & UI, preservar os nomes e estruturas oficiais — especialmente a nomenclatura temática de interface da seção 2.1, hierarquia de Cosméticos/Aparência/Título/Moldura, slots de equipamento, menus, Elos, estados, raridades, nomenclaturas de `T`, Braseiros, Guilda, Crônica e Avesso.

---

## 51. Grupo persistente e Campanha cooperativa

### 51.1 Grupo social, papéis e atividade

- Um Grupo social persistente contém até **4 personagens** e permanece após Missões e atividades. Ele é separado do roster ativo de cada Caçada, Masmorra, encontro ou outra atividade.
- Convites expiram em **10 minutos** e exigem aceite ou recusa explícita. Adesão e limite do Grupo são validados atomicamente. O Grupo pode conter membros offline ou em Locais diferentes. Um membro online pode propor atividade, mesmo que o Líder Social esteja offline.
- Qualquer membro pode propor uma atividade. O roster é formado pelo subconjunto online e elegível que confirmar a entrada; participantes com Foreground incompatível ficam fora dessa atividade sem deixar de pertencer ao Grupo. Sua composição fica congelada quando a atividade/encontro válido é criado. Membros não entram no meio de combate.
- Líder Social, Personagem de Referência da Jornada e Host Técnico são papéis separados. A liderança social administra o Grupo, mas não controla progresso individual, Configuração de Combate ou recompensas de outro personagem. O Host Técnico é uma responsabilidade operacional; o servidor e o estado persistido continuam sendo a autoridade.
- Offline não dissolve o Grupo. Quando o Líder Social sai, a liderança passa ao membro restante ativo mais antigo. Saída da Referência fora de combate permite sucessão por um participante legitimamente no mesmo checkpoint; sem sucessor, a Jornada ativa pausa ou encerra segundo o estado persistido, sem dissolver o Grupo.
- Kick é permitido somente fora de Foreground compartilhado. Sair ou expulsar alguém não pode funcionar como fuga de Foreground: kick e saída social não removem participante nem encerram combate compartilhado; a atividade aplica sua própria regra de abandono, morte ou reconnect.

### 51.2 Confirmação de Entrada

Caçada em Grupo e Chefe cooperativo usam uma **Confirmação de Entrada de 60 segundos**, com consentimento individual e revalidação de elegibilidade no commit. A confirmação congela a proposta de roster, contexto, custos e risco. Sem unanimidade, por recusa, expiração ou inelegibilidade, o fluxo retorna ao lobby sem criar encontro/run econômico, reservar ou consumir Vigor, registrar derrota ou aplicar lockout. O roster pode ser ajustado e confirmado novamente.

### 51.3 Campanha individual em Solo ou Grupo

- O Prólogo permanece Solo.
- De P1 em diante, todas as Missões Principais e Secundárias podem ser concluídas Solo ou em Grupo de **1–4**, salvo exceção Solo explicitamente publicada para o conteúdo. Este princípio aplica-se às 36 Principais e 36 Secundárias planejadas; o conteúdo de cada etapa classifica os objetivos como compartilháveis, pessoais ou adaptados.
- A Campanha, seus gates, estado narrativo, escolhas, conhecimento e recompensas pertencem individualmente a cada personagem. O Grupo compartilha a experiência, não um save narrativo coletivo. Nível e poder do personagem não ignoram gates pessoais nem concedem etapas futuras.
- Evidência objetiva de derrotar inimigo/Chefe, sobreviver, alcançar Local, atravessar trecho, examinar pista, encontrar objeto/estrutura, resolver puzzle compartilhável, concluir encontro roteirizado ou participar de descoberta objetiva pode ser registrada para cada personagem elegível e presente. Presença deve corresponder ao objetivo; pertencer ao Grupo, por si só, não basta. Cada concessão individual é idempotente. Não se exige que membros repitam o mesmo clique apenas para replicar uma interação compartilhada legítima.
- Escolhas narrativas, respostas pessoais, decisões irreversíveis, flags incompatíveis, gates e escolha de recompensa permanecem individuais. Códice e Bestiário continuam pessoais, mas uma descoberta compartilhada legítima pode registrar conhecimento para os participantes elegíveis presentes.
- Ajudante que já concluiu a etapa pode voltar sem regressão. Ele recebe somente recompensas repetíveis que a própria fonte já permita. Se a recompensa for one-time, seu settlement econômico é zero. Recompensas próprias de primeira conclusão permanecem disponíveis para o personagem no checkpoint que ainda tem direito a elas. Nenhum ajudante duplica XP/Coroas únicos de Quest, materiais únicos, Equipamento escolhido, Núcleo, Receita, first clear, flags, Feitos ou conhecimento one-time.

### 51.4 P1 e retorno de progresso

P1 — Vozes na Estrada é cooperativa após o Prólogo Solo. Os dois sinais podem ser investigados pelo Grupo; o encontro fixo do Cão Cinéreo pode ser enfrentado pelo roster confirmado; vitória válida registra o objetivo para os participantes elegíveis presentes; chegada válida ao Refúgio e descoberta do Braseiro podem ser registradas individualmente na mesma descoberta compartilhada. Diálogos e flags pessoais continuam individuais. O Cão do encontro roteirizado mantém identidade, template e regras regionais: não recebe automaticamente o scaling de Chefe de Campanha, não cria recompensa econômica própria, não consome Vigor e não consulta pools/rerolls de Caçada.

O fluxo de recuperação deve suportar: A/B/C/D iniciam P1; A sai; B/C/D avançam; depois B/C/D retornam como Ajudantes para o checkpoint de A. O progresso de B/C/D não regride e A não recebe etapas futuras sem cumprir seus próprios objetivos.

### 51.5 Chefes de Campanha

Chefe de Campanha aceita Solo ou Grupo de 1–4. Solo usa exatamente os atributos canônicos existentes. Na criação do encontro, congelar N pelo roster ativo inicial e calcular, uma única vez, HP e ATQ:

| Participantes | HP do Chefe | ATQ do Chefe |
| ---: | ---: | ---: |
| 1 | ×1,00 | ×1,00 |
| 2 | ×1,55 | ×1,04 |
| 3 | ×2,10 | ×1,08 |
| 4 | ×2,65 | ×1,12 |

`HP_group = HP_solo × [1 + 0,55 × (N−1)]`; `ATQ_group = ATQ_solo × [1 + 0,04 × (N−1)]`. DEF e AGI não escalam. Aplicar a materialização central e o arredondamento global de atributos, sem multiplicador intermediário ou fórmula paralela. Morte, saída ou disconnect não alteram o scaling do encontro corrente. Não adicionar scaling de fase, Artes, Cura, Barreira ou adds sem regra de conteúdo explícita.

### 51.6 Poder real e viabilidade Solo

Personagens mantêm nível, Equipamentos e poder reais; não há sincronização ou normalização de veterano nesta baseline. Um veterano pode carregar um novato, mas não ignora seus gates nem transfere recompensas únicas.

Toda build legal deve conseguir concluir a Campanha Solo. Duração e DPS podem variar, mas não pode existir soft-lock matemático causado por cura/barreira do Chefe superior ao dano mínimo legal, DPS check impossível, enrage incompatível ou função obrigatória ausente. Ataque Básico e ferramentas legais da Classe devem permitir progresso. Testes e telemetria devem cobrir builds defensivas e de suporte sem rebalancear Classes por esta regra.

## 52. Caçada em Grupo, PvPvE e Domínio do Rastro

### 52.1 Caçada em Grupo

Caçada em Grupo usa o Grupo social existente; não cria outra entidade social. O roster pode ser subconjunto do Grupo (por exemplo, 3 participantes ativos de um Grupo 4/4). Qualquer membro pode propor a Caçada; os participantes elegíveis confirmam por 60 segundos. Roster, Configurações de Combate, nível de referência, scaling, contribuição e settlement são individuais e ficam congelados pelas regras de Caçada. Ninguém entra durante combate. Pareamento PvPvE só considera o roster ativo e exige lados com o mesmo tamanho. A Caçada preserva sua própria escala de grupo, pool, Vigor, contribuição e recompensas da seção 49; não usa a escala de Chefe de Campanha desta Fonte.

### 52.2 Sequência PvPvE

PvPvE resolve em duas etapas e não cria uma batalha simultânea contra jogadores e monstro no Beta:

1. Na fronteira segura da Caçada, antes de materializar a próxima presa, o serviço procura rival elegível no mesmo Local e de mesmo tamanho de roster. Caçada Manual/Grupo pode permanecer elegível até 20 minutos; Ronda até 75 minutos, conforme o estado de Caçada/Ronda. Sair da área ou iniciar atividade incompatível torna o lado inelegível. Se não houver rival, a Caçada continua normalmente. Encontro de monstro já descoberto por Desbravar termina antes de iniciar pareamento.
2. Em colisão válida: PvP → identificar participantes vencedores, sobreviventes e ainda elegíveis → materializar a presa PvE → combate PvE → settlement normal. O encontro da presa e seu nível de referência, roster, scaling, seed e rewards são criados depois do PvP. Uma presa já materializada/iniciada não é rerrolada.

Aceitar/iniciar a Caçada já autoriza o pareamento PvPvE vigente; não há segunda Confirmação de Entrada quando a colisão ocorre. IDs de Caçada, colisão PvP, combate PvP, presa PvE e settlement são distintos. PvP custa **0 Vigor** e não concede XP, Coroas, Materiais, Equipamento, Runas ou pity. Derrotado não segue à presa e usa recovery normal. Empate ou morte simultânea encerra aquela oportunidade sem Domínio.

### 52.3 Domínio do Rastro e recompensas

Vitória PvP só cria estado individual temporário de Domínio para personagem vencedor que contribuiu validamente, sobreviveu e permaneceu elegível à presa. Depois de vitória econômica PvE válida, cada personagem qualificado recebe **0,05 × C(loot_reference_level)** Coroas, com o arredondamento monetário global, e **1 Material Básico regional**. Não há XP, Equipamento, Runa ou pity PvP. A presa mantém integralmente seu Vigor e seu settlement normal; o Domínio não tem custo adicional.

O lock econômico de **30 minutos** bloqueia somente a materialização de um novo bônus Domínio do Rastro. Ele nunca suprime, reduz ou adia XP normal elegível, Coroas, Materiais, Equipamento, Runa, pity, Bestiário ou quaisquer demais efeitos normais da Caçada da presa.

O lock é simétrico por par de contas e começa quando um bônus Domínio válido é materializado. É registrado por contas participantes, nunca por `group_id`. Alternar o vencedor de um confronto entre as mesmas contas não reabre o bônus antes da expiração. Em Grupo, verificar cada vencedor individualmente contra as contas adversárias participantes pertinentes. Como o pacote individual não é fracionado por adversário, qualquer par pertinente ainda bloqueado torna somente aquele vencedor inelegível ao bônus nesta resolução: **0 Coroas adicionais e 0 Material Básico adicional**. Isso não reduz a recompensa PvE normal nem remove o bônus de outro vencedor que continue elegível.

Mantêm-se: Recarga geral PvPvE de **3 minutos** após confronto resolvido; **10 minutos** sem novo pareamento contra o mesmo adversário/roster; **30 minutos** até novo bônus Domínio envolvendo o mesmo par de contas; sem limite diário. Trocar Grupo/composição não limpa o histórico. Pareamento prioriza adversário não recente e respeita as Recargas hard gate; suspeita gera telemetria, não ban automático no Beta.

### 52.4 Ronda e Assumir Combate

Ronda de Caça continua Solo e presente no Local enquanto ativa. Pode parear com Caçada Manual Solo ou outra Ronda Solo; Caçada Manual também pode parear com Ronda. PvPvE só ocorre entre encontros/antes da próxima presa válida; nunca retroativamente sobre PvE já liquidado. IA usa a Configuração de Combate registrada. `[Assumir Combate]` transfere controle do dono na próxima oportunidade válida, sem trocar build; a IA não espera takeover e o adversário não recebe indicação de controle manual/IA. Vitória PvP mantém o lote e segue à presa; ETA pode aumentar. Derrota termina o lote e não executa encontros futuros, preservando todos os encontros/recompensas já liquidados. Empate encerra a oportunidade e usa recovery. Não há suspensão/retomada de lote.

## 53. Desbravar, navegação e Crônicas

- Desbravar permanece Solo. Tentativa, RNG, descoberta, Vigor, recompensa, Códice e Bestiário pertencem a cada personagem. Não criar Mineração, Minerador, ferramenta ou sistema dedicado de coleta. Recursos contextuais continuam apenas em resultados já autorizados por conteúdo/economia. Uma criatura descoberta por Desbravar encerra o combate antes do pareamento PvPvE; só se aplica o fluxo global na fronteira segura seguinte quando elegível.
- Grupo é acessado por **Vínculos → Grupo**, sem botão raiz permanente no Menu Principal. Atalhos contextuais `[Grupo]` podem aparecer em Missão, Caçada, Masmorra e Local autorizado. Dashboard compacto pode exibir `👥 Grupo · X/4`. Missão Solo apresenta `[Seguir Objetivo] [Formar Grupo]`; em Grupo, `[Seguir Objetivo] [Grupo]`. Antes de atividade compartilhada, a interface identifica elegível, Ajudante e inelegível, checkpoint/Jornada e recompensas pessoais elegíveis.
- A ordem de entrega aprovada é: infraestrutura MMO/Grupo e Campanha coop; QA integral de Terras do Ocaso; Vales P7–P12/S7–S12 sobre a mesma arquitetura; infraestrutura real de Crônicas e testes de scheduler, objetivos, voto, Trilha, filtros de spoiler e recovery; Regiões 3–6; preparação completa de Ecos da Convergência.
- Crônica I começa no Dia 1 e conserva seu cânone de **8 semanas, 8 capítulos e 7 dias por capítulo**. Acelerar relógio é permitido somente em ambiente de engenharia/teste e não altera tempo canônico.
- O combate de S12 permanece bloqueado até existir kit numérico autoritativo. Esse bloqueio não impede a arquitetura cooperativa nem os demais conteúdos cujo kit já esteja fechado.

## 54. Persistência, idempotência e telemetria MMO

O estado persistido deve distinguir Grupo social, convites, liderança, Jornada/Referência, ready check, roster de atividade, instância/Host Técnico, snapshots individuais, encontro/combate, evidência pessoal de objetivo, progresso/reward por personagem, colisão PvP, presa PvE, Domínio, settlement e locks por par de contas. Reconnect, callbacks duplicados, `/start`, `/menu`, crash e multidispositivo retomam ou reconstroem o mesmo estado; não criam atividade, objetivo, loot ou reward duplicado. Callback, UI, `group_id` ou conta Telegram não substituem validação de elegibilidade, ownership e idempotência no commit.

Telemetria de Beta registra, no mínimo, composição/níveis/poder do roster, diferença veterano-conteúdo, scaling congelado, participação/contribuição, ações, dano, cura, barreira, mitigação, fase, duração, morte, disconnect, reconnect, abandono e resultado. PvPvE registra pareamentos/rosters, cooldowns, adversários por conta, resultado, Domínio, presa, vigor e settlement normal separado do bônus. Ronda registra lote previsto/concluído/interrompido e ETA. Telemetria apoia análise de carry, experiência Solo/Grupo e anti-farm; não substitui estado autoritativo/ledger e não altera regras automaticamente.

### 54.1 Autoridade e precedência

As regras desta seção prevalecem sobre qualquer formulação anterior incompatível acerca de Campanha Solo obrigatória, P1 Solo, convocação S6 sem escala, reward de Ajudante, ausência de scaling cooperativo de Chefe de Campanha, PvPvE simultâneo, pagamento direto por PvP, efeito do lock de 30 minutos ou interrupção da Ronda. Esta seção não reabre a Baseline Numérica v1.0 fora dos novos multiplicadores de Chefe de Campanha explicitamente listados em 51.5, nem altera kits, stats Solo, economia normal, custos de Vigor, loot ou conteúdo narrativo já fechado.

**ASTERION — GDD ESTRUTURAL v1.5.0 — FONTE MESTRA CONSOLIDADA**
**Estado:** versão oficial consolidada para servir como referência do projeto; a v1.5.0 substitui integralmente versões anteriores e está pronta para Visual & UI, Arquitetura de Desenvolvimento, Conteúdo, Balanceamento e Testes. A Baseline Numérica v1.0 permanece vigente, fora dos novos multiplicadores cooperativos de Chefe de Campanha formalizados nesta revisão.

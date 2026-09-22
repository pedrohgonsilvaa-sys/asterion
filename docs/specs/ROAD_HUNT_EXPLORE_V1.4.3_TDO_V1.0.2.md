# Especificação de implementação — Estrada das Cinzas: Caçada Manual + Desbravar

> Autoridade-base: **GDD Estrutural v1.4.3 + Terras do Ocaso v1.0.2 FINAL + Visual/UI 2026-09-21 sincronizada com v1.4.3/TDO v1.0.2**.
>
> Decisões adicionais aprovadas para este bloco, ainda pendentes de consolidação nas Fontes: **materialização global de Equipamento/Runa de Saque; identidade regional de Materiais da Caçada; conteúdo textual/registro de Desbravar na Estrada; apresentação pós-combate e de exploração; IA PvE normal, Ação Preparada e pacotes Hemorrágico/Venenoso**.
>
> Estado de partida do repositório: `main@bc45b2746e4cf5666134d39291fa32a6cdac524e`, com **P1 — Vozes na Estrada já implementada e concluível**.
>
> **Leitura obrigatória para implementação no Codex:** `docs/specs/ROAD_HUNT_EXPLORE_IMPLEMENTATION_BASELINE_V1.4.3_TDO_V1.0.2.md`. Esse complemento transcreve para dentro do repositório as constantes globais/regionais que esta especificação referencia (stats de inimigos, EnemyXP, C(n), chances de Saque, budgets de Equipamento, catálogo e Runas), sem criar balanceamento novo.

## 1. Escopo

Implementar o primeiro loop repetível jogável após P1:

`Refúgio do Ocaso → Travessia dos Braseiros → Estrada das Cinzas → Caçada Manual Solo / Desbravar → combate ou resultado → recompensa/registro → retorno à Estrada`.

Entram neste PR:

- detalhe funcional de Local para Refúgio e Estrada;
- Travessia permanente Refúgio ↔ Estrada;
- Caçada Manual **Solo** da Estrada;
- pool oficial, nível, Variante e IA das quatro criaturas elegíveis;
- recompensa econômica normal da Caçada;
- materialização concreta de Equipamento e Runa quando seus rolls ocorrerem;
- persistência mínima de Inventário/Pending necessária a drops repetíveis;
- Bestiário mínimo reutilizável para observação, combate, vitória, Habitat, Artes/mecânicas e Variantes;
- familiaridade local da Ronda após a primeira vitória manual válida;
- Desbravar Solo da Estrada;
- cooldown, janela de tentativas, anti-repetição e resultados oficiais;
- combate `exploration_combat` com economia própria;
- Códice/Trechos mínimos exigidos por Marco dos Viajantes e Luzes na Estrada;
- Foreground/reconnect/idempotência para Caçada e Desbravar.

Não entram neste PR:

- execução automática da **Ronda de Caça**;
- Caçada em Grupo;
- sistema social de Grupo;
- Desbravar de Charneca/Bosque/Ruínas;
- P2/S1;
- tela completa de Inventário, Bestiário ou Códice;
- Mercado/Crafting/Armazém;
- Masmorras.

### 1.1 Limites temporários de interface

A Fonte Visual já mostra `Grupo` na preparação e os botões de Ronda após familiaridade. Como os dois sistemas ficam fora deste PR:

- `[2] Grupo` pode permanecer visível, mas seu callback deve ser **não mutante** e nunca criar `encounter_id`;
- após a familiaridade, `[Ronda ×5] [Ronda ×10] [Ronda ×20]` podem ser mostrados, mas seus callbacks devem ser **não mutantes** até o PR específico de Ronda;
- esses callbacks devem responder como indisponibilidade de implementação, sem inventar regra de gameplay e sem alterar estado.

Nenhum desses limites pode bloquear Solo, Travessia, Caçada Manual ou Desbravar.

## 2. Estado inicial e gates

P1 concluída já persiste:

- `hunt_manual.estrada_das_cinzas`;
- `explore.estrada_das_cinzas`;
- Braseiro da Estrada descoberto;
- Braseiro do Refúgio descoberto;
- WorldState no Refúgio do Ocaso.

Logo, um personagem normal pós-P1 começa no **Refúgio**, onde não existe Caçada nem Desbravar. Para acessar o novo loop ele precisa viajar validamente para a Estrada.

### 2.1 Travessia

Travessia normal exige:

- personagem atualmente em Braseiro permanente válido;
- destino com Braseiro permanente descoberto e acessível;
- nenhuma atividade Foreground incompatível.

Refúgio e Estrada são destinos permanentes válidos pós-P1.

Selecionar destino válido:

1. bloquear personagem/WorldState;
2. revalidar origem, destino, Braseiros, Foreground e gates;
3. atualizar WorldState para o Local de destino;
4. **não** cobrar Coroas;
5. **não** restaurar HP/Vigor;
6. renderizar diretamente o detalhe do Local de destino.

Callback antigo nunca permite viagem remota depois que o personagem deixou o Braseiro/origem válida.

## 3. Detalhe da Estrada

Depois da Travessia:

```text
[Imagem contextual da Estrada das Cinzas]

🔥 Estrada das Cinzas · Local Atual
Terras do Ocaso · Nv. 1–10

🔥 Braseiro · Descoberto
🧭 Desbravar · Disponível
🦌 Caçada · Disponível

🔒 Ronda de Caça · Vença uma Caçada neste Local

[Caçar] [Desbravar]
[Travessia dos Braseiros]
[← Terras do Ocaso]
```

Após a primeira vitória manual válida, a familiaridade deixa de estar bloqueada e a navegação passa a expor os controles de Ronda conforme a Fonte Visual. Não criar popup de desbloqueio.

## 4. Caçada Manual — criação do encontro

### 4.1 Preparação

Usar o padrão aprovado de preparação com HP/Vigor exatos e barra.

`[1] Solo` é a única opção funcional deste PR.

Ao selecionar Solo, numa única mutação autoritativa:

1. validar personagem na Estrada;
2. validar unlock de Caçada Manual;
3. validar ausência de Foreground incompatível;
4. travar Configuração de Combate para o encontro;
5. criar `GameActivity`/atividade de Caçada ativa;
6. materializar `encounter_id` persistente;
7. selecionar criatura elegível;
8. materializar `enemy_level`;
9. materializar Variante, quando houver;
10. materializar stats/kit/IA sob o `ruleset_version` vigente;
11. entrar diretamente no HUD de combate.

Não existe tela `Encontro Encontrado`.

### 4.2 Pool oficial da Estrada

| Criatura | Categoria | Unlock | Máx. | Peso |
|---|---|---:|---:|---:|
| Cão Cinéreo | Comum | 1 | 3 | 34 |
| Corvo de Fuligem | Comum | 1 | 4 | 33 |
| Peregrino Calcinado | Comum | 2 | 5 | 30 |
| Alfa Cinéreo | Elite | 3 | 4 | 3 |

Antes do sorteio:

- remover entradas cujo `player_level < unlock_level`;
- normalizar pesos restantes;
- `enemy_level = min(player_level, max_enemy_level)`.

O `encounter_id` congela criatura, nível, Variante e scaling. Reconnect/abandono/callback antigo não rerrola.

### 4.3 Variante

Chance da Estrada: `8%`.

Se o roll ocorrer, selecionar uniformemente entre as Variantes válidas da criatura. Máximo 1 Variante.

- Cão: Furioso, Ágil;
- Corvo: Ágil, Furioso;
- Peregrino: Furioso, Resistente, Hemorrágico;
- Alfa: sem Variante aleatória configurada no catálogo regional atual; não inventar.

Furioso/Resistente/Ágil alteram apenas stats, não IA.

## 5. IA PvE e combate normal

A decisão inimiga é server-authoritative e determinística por padrão.

Em cada oportunidade válida:

1. resolver Preparada pendente e apta;
2. aplicar prioridades explícitas de conteúdo;
3. avaliar Defender se autorizado;
4. selecionar Arte especial válida/fora de Recarga;
5. fallback ofensivo.

Sem prioridade própria, usar ordem canônica das Artes e depois `action_definition_id` estável. Não usar RNG salvo perfil explicitamente aleatório; nesse caso usar RNG determinístico do combate.

### 5.1 Cão Cinéreo

Preservar comportamento já fechado:

`Mordida Faminta → Mordida Faminta → Investida Curta → repetir`.

Artes:

- Mordida Faminta `100% ATQ`;
- Investida Curta `110% ATQ`, CD2.

### 5.2 Corvo de Fuligem

- Bicada `95% ATQ`;
- Rasante `90% ATQ + AGI −8% · 1T`, CD2.

Política:

`Rasante disponível → Rasante; senão → Bicada`.

### 5.3 Peregrino Calcinado

- Golpe Desesperado `105% ATQ`;
- Defender permitido.

Política determinística:

`Golpe → Golpe → Defender → repetir`.

Se Defender estiver devido mas ilegal naquela oportunidade, usar Golpe e manter Defender devido para a próxima oportunidade legal.

### 5.4 Alfa Cinéreo

- Mordida Alfa `100% ATQ`;
- Investida Rasgante `90% ATQ +1 Sangramento`, CD2;
- Salto Predatório `Preparada · 160% ATQ`, CD4.

Prioridade:

1. resolver Salto pendente;
2. se alvo possui 0 Sangramento e Investida disponível → Investida;
3. se Salto disponível → preparar Salto;
4. se Investida disponível e Sangramento abaixo do cap → Investida;
5. Mordida Alfa.

Não aplicar Investida somente para tentar ultrapassar cap.

### 5.5 Ação Preparada

Ao preparar:

- consome a oportunidade atual;
- não aplica dano/efeito final ainda;
- persiste telegraph/estado da mesma ação;
- compromete Recarga naquele momento.

Antes da resolução, o alvo precisa receber ao menos uma oportunidade normal de resposta.

Resolver na primeira oportunidade elegível posterior da fonte depois da janela de resposta.

Defender válido mitiga normalmente o ataque Preparado.

Se a fonte morrer antes da resolução, a ação é cancelada sem ataque póstumo. Se perder oportunidade por impedimento normal, preparação permanece e tenta resolver na próxima oportunidade elegível. Alvo único inválido encerra a ação sem retarget e sem devolver Recarga.

O snapshot precisa persistir semântica equivalente a:

- action id;
- source/target;
- oportunidade de preparação;
- janela de resposta observada;
- cooldown comprometido;
- estado de resolução;
- identidade idempotente da ação.

Reconnect reconstrói o telegraph pendente; nunca reinicia preparação ou dano.

### 5.6 Hemorrágico/Venenoso

Pacote de Variante aplica no máximo `+1` DoT por alvo e por **ação ofensiva de Dano Direto elegível**.

Elegíveis: ataque simples, Arte de Dano Direto, Preparada, AoE/multi-hit (máximo 1 rider por alvo para a ação inteira).

Não elegíveis: tick de DoT, Refletido, Reação, Ambiental, Cura, Barreira, Defender, ação sem Dano Direto.

Se a Arte já aplica o mesmo DoT nativamente, o pacote não adiciona segundo stack nessa ação. Não existe cooldown interno adicional. Rider exclusivo da Variante é omitido quando o alvo já está no cap global.

Hemorrágico mantém `ATQ −5%`; Venenoso mantém `HP −5%`.

## 6. Resultado da Caçada e economia

### 6.1 Vitória

Ao primeiro commit válido de vitória:

1. atividade/encounter → completed;
2. persistir HP restante;
3. calcular XP normal do inimigo;
4. processar Bestiário elegível;
5. resolver economia da Caçada;
6. consumir `2 Vigor` **somente se a recompensa econômica for concedida**;
7. persistir reward event e componentes;
8. se for a primeira vitória manual válida no Local, registrar familiaridade da Ronda;
9. liberar lock de Configuração somente após resolução persistida;
10. renderizar recibo pós-vitória.

Vitória manual válida inclui Variante legítima. Não contam P1, Desbravar, Missão, derrota ou abandono.

**Caçada Manual não exige 2 Vigor para criar o encontro.** Vigor é limitador econômico, não bloqueador absoluto do combate manual. Na resolução da vitória:

- com `Vigor >=2`, conceder a economia normal e consumir exatamente `2 Vigor` no mesmo commit;
- com `Vigor <2`, conceder **0 Coroas farmáveis, 0 Materiais negociáveis, 0 Equipamento, 0 Runa e 0 especial econômico**, consumir `0 Vigor` e aplicar `VigorXPFactor=25%` à XP repetível pertinente;
- Bestiário/knowledge continuam elegíveis normalmente;
- a vitória continua válida para familiaridade da Ronda, pois o gatilho é a vitória manual válida e não a obtenção de drop.

Não existe consumo parcial de 1 Vigor.

### 6.2 XP de inimigo

Usar a fórmula global `EnemyXP` com `enemy_level` e categoria materializados.

Primeira observação válida de Bestiário, quando realmente inédita e elegível, usa sua recompensa única própria; P1 continua sendo a exceção já suprimida.

### 6.3 Coroas

Caçada:

- Comum: `0,05 × C(enemy_level)`;
- Elite: `0,25 × C(enemy_level)`.

Usar o arredondamento global já vigente para recompensa econômica.

### 6.4 Materiais

Regras de quantidade globais permanecem:

- Comum: `80% → 1 Material Básico`;
- Elite: `3–4 básicos garantidos +1 Catalisador`;
- Fragmento Elite: `40% →1`.

Identidade regional quando um Material Básico é devido:

- Cão → Couro Escoriado `100%`;
- Corvo → Resíduo do Ocaso `100%`;
- Peregrino → Ferro de Fuligem / Erva Cinzenta, seleção uniforme por unidade;
- Alfa → Couro Escoriado `100%`.

Variantes não trocam o pool material da criatura.

### 6.5 Equipamento

Chance por categoria permanece a global. Quando o roll tiver sucesso:

`loot_reference_level = enemy_level`

`item_level = loot_reference_level`.

Materialização:

1. raridade já resolvida, inclusive pity;
2. secundários exigidos: `0/1/2/3/4` para Comum/Raro/Épico/Lendário/Mítico;
3. grupos: Principal, Secundária, Cabeça, Torso, Mãos, Pés, Acessório, Artefato;
4. 2H participa de Principal, não cria nono grupo;
5. filtrar templates regionais normais `generic_loot_eligible`;
6. 2H usa pool de secundários de Principal;
7. remover template cujo pool não comporte a quantidade de secundários distintos;
8. selecionar grupo uniforme salvo peso explícito;
9. selecionar template uniforme salvo peso explícito;
10. secundários uniformes, sem reposição/duplicação;
11. calcular núcleo/budget/magnitudes pelas fórmulas globais;
12. criar item `+0`, sem Runa, sem Encantamento, Negociável salvo override;
13. persistir antes da apresentação.

Templates normais elegíveis da região são os 13 do catálogo Ferreiro/Curteiro/Joalheiro. Itens de Campanha e Receita especial ficam fora do gerador genérico.

Crafting Comum/Raro/Épico não limita a raridade possível em Saque.

Consequência vigente: Torso Mítico genérico é inelegível enquanto Torso tiver apenas três secundários possíveis e Mítico exigir quatro distintos.

### 6.6 Runa

Chance/raridade permanecem globais.

`loot_reference_level = enemy_level`

`rune_grade = floor((loot_reference_level - 1) / 10) + 1`, limitado I–VI.

Na Estrada, portanto, drops normais são Grau I.

Selecionar uniformemente entre as oito famílias regionais na ausência de peso explícito:

- Brasa · ATQ;
- Pedra · DEF;
- Caminhante · AGI;
- Fresta · PER;
- Presságio · CRIT;
- Persistência · HP;
- Desvio · Esquiva;
- Guarda · Bloqueio.

Não filtrar por slot/equipamento atual. Compatibilidade é validada apenas ao instalar.

Runa genérica nasce Negociável salvo override. Persistir família, raridade, Grau, potência e bind antes da apresentação.

### 6.7 Determinismo do Saque

Cada roll econômico possui seed persistida antes da apresentação.

Usar subdraws estáveis equivalentes a:

- `equipment.slot`;
- `equipment.template`;
- `equipment.secondary.N`;
- `rune.family`;
- materiais/quantidades/especiais com chaves próprias.

Depois que item/runa/reward component existe, recovery carrega a instância persistida; não rerrola RNG.

Chave idempotente precisa distinguir `source activity/encounter + character + roll_type + ordinal` ou equivalente.

## 7. Inventário e Pending mínimos

Este PR introduz drops repetíveis de Equipamento/Runa, então não pode depender da suposição de Inventário infinito.

Implementar a persistência mínima reutilizável compatível com:

- Inventário 60 slots;
- Pending 20 slots;
- Materiais stack 999;
- Runas idênticas podem agrupar quando propriedades econômicas coincidirem;
- Equipamento é instância individual;
- itens Pending não podem ser usados/equipados/negociados.

A UI completa de Inventário/Pending fica fora do PR, mas entrega precisa ser segura:

- tentar fundir em stack compatível antes de gastar novo slot;
- se Inventário não comportar componente físico, criar entrega Pending quando houver capacidade;
- se Inventário + Pending não comportarem, não duplicar nem descartar silenciosamente; atividade deve finalizar com estado de entrega impeditivo/auditável e impedir novo gerador de item até resolução futura.

Reward event e descoberta/conclusão são separados da entrega física; retry só completa componente faltante.

## 8. Bestiário mínimo reutilizável

Criar persistência suficiente para a progressão oficial sem implementar a tela completa.

Modelo lógico recomendado:

- `BestiaryEntry(character_id, creature_id, profile, bkp, stage, wins, ...)`;
- `BestiaryEvidence(character_id, creature_id, evidence_id, category, ...)` unique;
- estado específico de Variante pode ser evidência/subregistro ligado à criatura.

A UI não exibe BKP numérico.

### 8.1 Eventos elegíveis neste PR

Conforme aplicável e apenas uma vez por marco:

- primeira observação: +4 BKP;
- primeiro combate: +3;
- primeira vitória: +5;
- nova Arte/comportamento observada: +4;
- nova mecânica: +5;
- Habitat: +3;
- investigação Desbravar: +8 somente quando uma regra de conteúdo realmente a conceder;
- Variante descoberta: +8;
- primeira vitória da Variante: +6;
- forma Elite: +8;
- primeira vitória de Elite: +6;
- repetição de vitória conforme perfil global.

Estágios derivam dos thresholds globais e categorias de evidência. Conteúdo oculto permanece ausente.

### 8.2 Observação em combate

Encontrar a criatura pode registrar primeira observação e primeiro combate quando elegíveis. A primeira observação pode sobreviver a derrota se já commitada antes dela.

Arte/mecânica só é registrada quando realmente executada/observada.

Para Alfa, o requisito regional de Dominado inclui vitória, observar Investida Rasgante com Sangramento e testemunhar Salto Predatório preparado.

## 9. Derrota da Caçada

Na derrota Solo:

- atividade → failed;
- nenhuma economia de vitória;
- nenhum `2 Vigor` consumido por derrota sem recompensa;
- consumíveis gastos permanecem consumidos;
- knowledge já legitimamente observado pode permanecer;
- personagem recupera pelo Braseiro permanente válido da Estrada: HP 100%, estados comuns removidos, Vigor inalterado;
- WorldState fica/retorna à Estrada;
- lock de Configuração é liberado após resolução persistida.

Tela:

```text
💀 Derrota

🔥 Braseiro da Estrada
Estrada das Cinzas · Terras do Ocaso

❤️ HP · Restaurado

🦌 Caçada · Encerrada

[Caçar Novamente]
[← Estrada das Cinzas]
```

`Caçar Novamente` volta à preparação; não cria encontro automaticamente.

## 10. UI pós-vitória da Caçada

Recibo, nunca claim:

```text
🏆 Vitória

{criatura}
{Variante somente se houver}

🎁 Recompensas

{somente componentes realmente concedidos}

[Caçar Novamente]
[← Estrada das Cinzas]
```

Mostrar apenas linhas existentes:

- XP;
- Coroas;
- Material;
- Equipamento: `Nome · +0`, raridade/slot, `Nível do Item`, Negociável/Vinculado quando relevante;
- Runa: família, raridade, Grau, bind quando relevante;
- Catalisador/Fragmento/especial;
- Bestiário somente se houve atualização qualitativa nova.

Nunca mostrar `Nenhum Equipamento`, `+0 XP` ou blocos vazios.

## 11. Familiaridade da Ronda

Persistir familiaridade uma única vez na primeira vitória creditada ao personagem em **Caçada Manual da Estrada gerada pelo pool oficial**, inclusive Variante legítima.

Não contam:

- P1;
- Desbravar;
- Missão;
- derrota/abandono.

ID recomendado:

`hunt_round.estrada_das_cinzas`

Pode reutilizar `Unlock` com unique por personagem + unlock.

Não conceder recompensa, popup ou XP pela familiaridade.

## 12. Desbravar — tentativa e rate limits

### 12.1 Entrada

Somente na Estrada atual, Local conhecido, unlock presente e sem Foreground incompatível.

Desbravar é Solo.

Não exige Vigor para iniciar.

UI informa:

`⚡ Economia Repetível · 4 Vigor quando concedida`.

Se Vigor <4, exploração continua disponível; apenas a camada econômica repetível é suprimida.

### 12.2 Cooldown e janela

- cooldown: `5 min`, contado a partir do **commit de criação da tentativa**;
- máximo: `6 tentativas / Local / 60 min`, contado pelos commits de criação das tentativas;
- UI mostra tempo restante `MM:SS`;
- quando bloqueado, não mostrar botão desabilitado.

A checagem é server-authoritative no commit. Callback antigo não ignora janela.

### 12.3 Persistência

Criar tentativa com identidade própria, preferencialmente ligada a `GameActivity`:

- character/server;
- Região/Local;
- ruleset_version;
- seed;
- categoria selecionada;
- resultado específico selecionado;
- estado active/completed/failed;
- timestamps para cooldown/janela;
- encounter_id se transicionar para combate;
- reward/knowledge IDs associados.

Resultado é sorteado **uma vez** e persistido antes da apresentação.

## 13. Pool de Desbravar — Estrada

Pool-base por categoria:

- Grande Descoberta `8`;
- Conhecimento `22`;
- Narrativo `15`;
- Combate `25`;
- Pequeno Recurso `10`;
- Atmosférico `20`.

Subpesos oficiais da Estrada:

- Grande Descoberta: Marco dos Viajantes `100`;
- Conhecimento: Rastros Cinéreos `60` / Sinais à Margem `40`;
- Narrativo: Luzes na Estrada `70` / Vozes Levadas pelo Vento `30`;
- Combate: Cão `40` / Corvo `35` / Peregrino `25`;
- Pequeno Recurso: Ferro `30` / Couro `30` / Erva `20` / Resíduo `20`;
- Atmosférico: Cinza sobre as Pegadas `34` / Carroça sem Rodas `33` / Fogueira Fria `33`.

Remover resultados inelegíveis e redistribuir apenas entre elegíveis, preservando a hierarquia categoria → resultado.

Anti-repetição por resultado específico:

- resultado imediatamente anterior: peso `0`;
- se apareceu entre os últimos 3 válidos: peso `×0,35`.

Resultados Únicos saem permanentemente do pool depois de resolução válida.

### 13.1 Grande Descoberta

**Marco dos Viajantes** · único · XP 456.

Texto oficial:

> Um marco de pedra inclina-se à margem da estrada. Marcas gastas ao redor mostram que viajantes paravam aqui muito antes das passagens mais recentes.

Commit idempotente:

- resultado único concluído;
- garantir/usar a Entrada de Códice `Estrada das Cinzas`;
- Trecho `Memória dos Viajantes` nessa Entrada;
- 456 XP uma única vez.

IDs estáveis recomendados: `codex.location.estrada_das_cinzas` e `codex.fragment.estrada.memoria_viajantes`.

ID: `explore.tdo.estrada.marco_viajantes`.

### 13.2 Conhecimento — Rastros Cinéreos

Texto-base:

> Marcas interrompidas atravessam a fuligem e desaparecem alguns passos adiante. Há sinais suficientes para reconhecer que alguma criatura utiliza esta rota.

Elegibilidade para conceder Habitat:

1. considerar Cão, Corvo, Peregrino;
2. remover criatura bloqueada por `unlock_level`;
3. exigir entrada de Bestiário já legitimamente conhecida/observada;
4. entre as que ainda não possuam `Habitat · Estrada das Cinzas`, escolher uniformemente;
5. registrar uma vez Habitat da Estrada.

Textos contextuais:

Cão:
> Pegadas de quatro patas cortam a fuligem em passadas rápidas. Marcas de garras indicam que a criatura percorre a Estrada com frequência.

Corvo:
> Pequenas marcas interrompem a cinza junto a riscos estreitos no chão. Algo pousa e parte repetidamente deste trecho da Estrada.

Peregrino:
> Passadas irregulares seguem por alguns metros antes de desaparecer entre pedra e fuligem. O mesmo padrão já foi associado aos Peregrinos da região.

Se todas as evidências elegíveis já existirem, ainda resolver Rastros como contexto repetível: selecionar criatura elegível apenas para Flavor, sem novo BKP/XP/estado.

Se **nenhuma** criatura estiver atualmente elegível para identificação contextual — por exemplo, nenhuma das entradas permitidas ainda foi legitimamente observada — mostrar apenas o texto-base de Rastros, sem nomear criatura.

Rastros Cinéreos concede, quando aplicável, somente a evidência global de **Habitat** (`+3 BKP` pelas regras vigentes). **Não** conceder adicionalmente os `+8 BKP` de investigação Desbravar apenas por este resultado.

Não revelar criatura ainda não conhecida.

ID: `explore.tdo.estrada.rastros_cinereos`.

### 13.3 Conhecimento — Sinais à Margem

Texto:

> Pedras movidas, tecido preso aos espinhos e cinza revolvida mostram que viajantes ainda usam as margens da Estrada para descansar ou passar despercebidos.

Repetível, sem estado permanente, XP ou economia própria.

ID: `explore.tdo.estrada.sinais_margem`.

### 13.4 Narrativo — Luzes na Estrada

Único · XP 143.

Texto:

> Uma luz pálida surge entre as pedras por alguns instantes. Não há chama nem calor suficiente para explicá-la; quando você se aproxima, ela já desapareceu.

Trecho compartilhado:

`Estrada das Cinzas / Luzes na Estrada`.

Usar a mesma Entrada estável `codex.location.estrada_das_cinzas`; ID recomendado do Trecho: `codex.fragment.estrada.luzes_na_estrada`.

Se Desbravar vier primeiro: registrar Trecho +143 XP; S1 futura reconhece Trecho existente.

Se S1 vier primeiro: Desbravar ainda pode resolver seu evento único e conceder 143 XP, mas não duplica Trecho.

ID: `explore.tdo.estrada.luzes`.

### 13.5 Narrativo — Vozes Levadas pelo Vento

Texto:

> O vento atravessa a estrada e traz um som que lembra uma voz distante. Quando você tenta segui-lo, resta apenas o ruído da cinza contra a pedra.

Repetível; nenhum estado permanente/economia/XP próprio.

ID: `explore.tdo.estrada.vozes_vento`.

### 13.6 Combate

Subpool:

- Cão `40`;
- Corvo `35`;
- Peregrino `25`.

Aplicar unlock_level e normalizar. Chance de Variante da Estrada: 8%.

Selecionado o resultado:

- persistir tentativa;
- criar `encounter_id` dentro da mesma atividade Foreground;
- entrar diretamente no combate normal;
- reconnect retoma o mesmo resultado/encontro.

Não existe tela intermediária.

### 13.7 Pequeno Recurso

Subpool:

- Ferro 30;
- Couro 30;
- Erva 20;
- Resíduo 20.

Textos:

Ferro:
> Entre pedras partidas, um veio escuro de metal aflora sob a fuligem. Há material suficiente para ser recolhido.

Couro:
> Entre restos secos à margem da estrada, uma porção de couro ainda aproveitável resistiu à cinza e ao tempo.

Erva:
> Folhas acinzentadas crescem entre rachaduras protegidas do vento. Algumas ainda podem ser colhidas.

Resíduo:
> Um depósito escuro se acumulou entre as pedras. A substância é fina, mas distinta da fuligem comum da Estrada.

Quando Vigor >=4 e economia puder ser concedida:

- consumir 4 Vigor no mesmo commit;
- Coroas `0,10 × C(nível aplicável)`;
- +1 Material Básico sorteado pelo subpool `30/30/20/20`.

Quando Vigor <4:

- resultado narrativo/contextual ainda resolve;
- 0 Coroas repetíveis;
- 0 Material repetível;
- 0 Vigor parcial.

### 13.8 Atmosféricos

Cinza sobre as Pegadas:
> Uma rajada atravessa a Estrada. Em poucos instantes, a cinza cobre marcas antigas até não restar indicação de quem passou por ali.

Carroça sem Rodas:
> A estrutura apodrecida de uma carroça repousa fora da estrada. As rodas desapareceram há muito; o restante já não guarda nada de valor.

Fogueira Fria:
> Pedras enegrecidas cercam uma fogueira antiga. A cinza está fria e nenhum sinal recente indica quem a acendeu.

Todos repetíveis, sem XP adicional, economia, Códice ou Bestiário próprio.

## 14. Economia do combate de Desbravar

`loot_profile = exploration_combat`.

Não executar rolls completos de Equipamento/Runa/especial da Caçada.

Na vitória:

- XP normal de combate pelas regras globais, com fator de Vigor reduzido quando pertinente;
- Bestiário normal;
- se Vigor >=4 e economia for concedida: consumir 4 Vigor, `0,15 × C(nível aplicável)`, +1 Material Básico e 20% de +1 adicional;
- cada unidade de Material Básico usa seleção independente no pool `Ferro30/Couro30/Erva20/Resíduo20`;
- com Vigor <4, não pagar Coroas/Materiais repetíveis nem consumir Vigor parcial; XP repetível aplica o fator global de 25% quando pertinente.

Tela pós-combate só mostra componentes realmente concedidos e nunca sugere Equipamento/Runa/especial.

## 15. Derrota no combate de Desbravar

- encontro → failed;
- tentativa → failed/concluída como falha;
- não rerrolar o resultado;
- recompensas dependentes de vitória não são concedidas;
- knowledge legitimamente commitado antes da derrota pode permanecer;
- recovery PvE normal pelo Braseiro da Estrada;
- HP 100%, Vigor inalterado;
- Consumíveis gastos permanecem consumidos;
- retorno à Estrada.

Não existe retry do mesmo resultado.

## 16. UI de Desbravar

### 16.1 Entrada

```text
🧭 Desbravar

🔥 Estrada das Cinzas
Terras do Ocaso · Nv. 1–10

Explore os arredores do Local em busca de sinais, descobertas, recursos e acontecimentos.

👤 Exploração · Solo
⚡ Economia Repetível · 4 Vigor quando concedida

[Desbravar]
[← Estrada das Cinzas]
```

Com Vigor <4, comunicar que exploração/descobertas continuam disponíveis e que economia repetível requer 4 Vigor.

### 16.2 Cooldown/limite

Cooldown:

`⏳ Desbravar · Disponível em MM:SS`.

Limite:

`🔒 Desbravar · Limite recente atingido`
`⏳ Disponível em · MM:SS`.

Não exibir pesos, seed, `6/6`, botão desabilitado ou detalhes de janela deslizante.

### 16.3 Resultados

Shell:

```text
🧭 Desbravar
Estrada das Cinzas · Terras do Ocaso

{emoji} {Nome}

{texto oficial}

{somente consequências reais}

⏳ Desbravar · Disponível em {MM:SS}

[Desbravar Novamente]  # apenas se legal naquele momento
[← Estrada das Cinzas]
```

Consequências possíveis:

- XP;
- Material/Coroas;
- Códice/Trecho;
- Bestiário/Habitat.

Nunca mostrar componentes ausentes.

## 17. Foreground, reconnect e comandos

Prioridade global de reconstrução:

1. Foreground ativo de Caçada/Desbravar/P1/outro conteúdo;
2. resultado persistido ainda pendente de apresentação quando aplicável;
3. navegação do Local;
4. Menu normal.

Enquanto combate de Caçada ou combate de Desbravar estiver ativo:

- `/start` e `/menu` retomam o mesmo combate;
- troca de dispositivo retoma o mesmo encounter;
- callback antigo de Mapa/Local não cria nova atividade;
- Configuração de Combate permanece travada;
- decisão inimiga, Variante, loot seed e resultado de exploração não rerrolam.

Depois de resultado persistido:

- reward não é concedido novamente;
- familiaridade não duplica;
- Bestiário/Códice não duplicam;
- resultado de Desbravar não rerrola;
- `/menu` volta a funcionar normalmente.

Solo PvE manual expira após 30min sem ação válida conforme regra global; antes disso é retomável no mesmo estado.

## 18. Concorrência e locks

Toda mutação revalida sob lock do personagem/atividade:

- ownership + server;
- WorldState/Local;
- unlock;
- Foreground único;
- activity/encounter/attempt id;
- state_version;
- callback action válida;
- cooldown/janela de tentativas;
- Vigor no commit da economia;
- reward event/component;
- capacidade de Inventário/Pending;
- familiaridade;
- knowledge IDs.

Casos obrigatórios de corrida:

- dois `Solo` tentando criar Caçada;
- `Solo` concorrendo com `Desbravar`;
- dois callbacks de ação de combate;
- vitória processada duas vezes;
- reward Telegram falhando após commit;
- dois Desbravar simultâneos;
- callback antigo de tentativa resolvida;
- primeira vitória concorrente tentando criar familiaridade;
- item/runa já materializado durante retry;
- cooldown/janela mudando entre render e commit.

Somente o primeiro commit lógico válido produz efeito.

## 19. Migration/persistência

Criar a próxima revision Alembic após `20260921_0005`.

Persistência nova mínima esperada:

- contexto de Caçada repetível ligado a `GameActivity`/Encounter;
- tentativa de exploração;
- seed/resultados persistidos;
- BestiaryEntry/Evidence ou equivalente;
- Trechos de Códice (a tabela atual de `CodexEntry` sozinha não representa múltiplos Trechos de uma Entrada);
- ItemInstance;
- Runa persistente/stack compatível;
- entrega Pending mínima;
- capacidade/estado de Inventário suficiente;
- reward linkage idempotente para atividades repetíveis;
- familiaridade via Unlock ou equivalente.

Não apagar/reinterpretar P1 existente.

Downgrade deve ser conservador: se houver Caçada/Exploração/reward/item/runa/knowledge novos materializados, falhar explicitamente em vez de perder estado silenciosamente.

## 20. Testes obrigatórios

Usar PostgreSQL real no CI. Cobrir no mínimo:

1. pós-P1 no Refúgio não permite Caçar/Desbravar remotamente;
2. Travessia Refúgio→Estrada e Estrada→Refúgio funciona e custa 0;
3. Travessia bloqueada por Foreground;
4. Solo cria exatamente um encounter e entra direto no combate;
5. pool Nv.1 contém apenas Cão/Corvo, com pesos normalizados;
6. Peregrino entra no Nv.2; Alfa entra no Nv.3;
7. `enemy_level` respeita o teto individual;
8. chance/seleção de Variante usa seed persistida e máximo 1;
9. Cão mantém a cadência oficial;
10. Corvo usa Rasante/Bicada conforme prioridade oficial;
11. Peregrino usa Golpe/Golpe/Defender conforme política oficial;
12. Alfa respeita prioridade, Sangramento e Salto Preparado;
13. Preparada cria telegraph, concede janela de resposta e resolve uma vez;
14. Defender mitiga Preparada normalmente;
15. derrota da fonte cancela Preparada;
16. reconnect preserva Preparada e telegraph;
17. Hemorrágico aplica no máximo 1 rider por ação e não duplica Sangramento nativo;
18. Venenoso aplica regra equivalente para Veneno;
19. Furioso/Resistente/Ágil não mudam IA;
20. reconnect da Caçada mantém activity/encounter/combat/configuração;
21. vitória concede XP/Coroas corretos quando a economia é elegível;
22. derrota não concede economia nem consome Vigor;
23. vitória com Vigor>=2 consome exatamente 2 Vigor uma vez;
24. vitória manual com Vigor<2 não paga economia, não consome Vigor, aplica o fator de XP pertinente e ainda conta para familiaridade;
25. Cão→Couro; Corvo→Resíduo; Peregrino→Ferro/Erva; Alfa→Couro;
26. Elite entrega 3–4 básicos + Catalisador e Fragmento conforme roll;
27. Equipamento respeita chances/raridade globais e `item_level=enemy_level`;
28. seleção de grupo/template/secundários é determinística;
29. 2H participa de Principal e usa pool de secundários de Principal;
30. Torso Mítico genérico é filtrado por pool insuficiente;
31. Equipamento nasce +0, sem Runa/Encantamento e com bind correto;
32. Runa usa Grau I na Estrada e família uniforme/determinística;
33. Runa não usa smart loot nem compatibilidade de slot no drop;
34. reward repetido não cria segundo item/runa;
35. Inventário/Pending não perde nem duplica reward;
36. primeira vitória manual válida registra familiaridade uma vez;
37. P1 e Desbravar não registram familiaridade;
38. Bestiário: primeira observação/combate/vitória são idempotentes;
39. Arte/mecânica só é registrada quando realmente observada;
40. Variante permanece oculta até descoberta legítima;
41. Desbravar exige Local atual/unlock e não exige Vigor para iniciar;
42. cooldown de 5 min começa no commit de criação da tentativa;
43. máximo de 6 tentativas/Local/60 min usa commits de criação;
44. pesos exatos de categoria `8/22/15/25/10/20` e subpesos da Estrada são preservados;
45. resultado é persistido antes da apresentação e não rerrola;
46. anti-repetição aplica peso 0 ao resultado anterior e ×0,35 aos últimos 3 válidos;
47. resultados Únicos saem do pool após resolução válida;
48. Marco concede 456 XP + Trecho uma vez;
49. Luzes concede 143 XP uma vez e Trecho é idempotente;
50. Rastros não revela criatura desconhecida e concede Habitat apenas a criatura elegível;
51. Rastros sem criatura elegível mostra só o texto-base; com evidências esgotadas permanece contexto sem novo progresso;
52. Rastros não concede +8 BKP de investigação apenas por esse resultado;
53. Sinais/Vozes/Atmosféricos não criam reward artificial;
54. Pequeno Recurso com Vigor>=4 consome 4 e paga a economia correta;
55. Pequeno Recurso com Vigor<4 resolve contexto sem economia nem Vigor parcial;
56. combate de Desbravar usa `40/35/25` e Variante 8%;
57. `exploration_combat` nunca executa rolls de Equipamento/Runa/especial;
58. vitória de `exploration_combat` paga `0,15×C + material +20% extra` quando houver Vigor suficiente;
59. cada unidade de material de `exploration_combat` usa seleção independente no pool `30/30/20/20`;
60. com Vigor<4, economia repetível é suprimida e XP usa o fator pertinente;
61. derrota de exploração encerra a tentativa sem reroll;
62. `/start` e `/menu` durante Foreground retomam a atividade;
63. callback antigo não cria segunda atividade/reward/knowledge;
64. falha Telegram pós-commit reconstrói resultado sem duplicar efeitos;
65. outro dispositivo observa o mesmo estado persistido;
66. migration upgrade/downgrade/upgrade quando seguro;
67. `alembic check`;
68. `ruff check .`;
69. pytest completo com PostgreSQL real e zero skips;
70. `git diff --check`.

## 21. Limite do PR de código

Parar quando:

- Travessia entre os dois Braseiros pós-P1 estiver funcional;
- Caçada Manual Solo da Estrada estiver jogável de ponta a ponta;
- Saque/Bestiário/familiaridade estiverem persistentes e idempotentes;
- Desbravar da Estrada estiver jogável em todos os seus resultados;
- exploration_combat estiver correto;
- reconnect/recovery forem seguros;
- CI estiver verde.

Não iniciar Ronda automática, Grupo, P2/S1 ou outro Local no mesmo PR.

## 22. Critério de aceite

O bloco só está pronto para review quando:

- nenhuma regra numérica das Fontes foi reaberta;
- as decisões adicionais aprovadas neste documento estão implementadas literalmente;
- nenhum roll materializado pode ser rerrolado por reconnect/callback/retry;
- nenhuma recompensa/knowledge/familiaridade pode duplicar;
- P1 continua intacta;
- UI não revela conteúdo oculto;
- Caçada e Desbravar mantêm economias distintas;
- PostgreSQL CI completo está verde.

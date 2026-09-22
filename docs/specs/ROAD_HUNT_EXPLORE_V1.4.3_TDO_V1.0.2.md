# Especificação de implementação — Estrada das Cinzas: Caçada Manual + Desbravar

> Autoridade-base: **GDD Estrutural v1.4.3 + Terras do Ocaso v1.0.2 FINAL + Visual/UI 2026-09-21 sincronizada com v1.4.3/TDO v1.0.2**.
>
> Decisões adicionais aprovadas para este bloco, ainda pendentes de consolidação nas Fontes: **materialização global de Equipamento/Runa de Saque; identidade regional de Materiais da Caçada; conteúdo textual/registro de Desbravar na Estrada; apresentação pós-combate e de exploração; IA PvE normal, Ação Preparada e pacotes Hemorrágico/Venenoso**.
>
> Estado de partida do repositório: `main@bc45b2746e4cf5666134d39291fa32a6cdac524e`, com **P1 — Vozes na Estrada já implementada e concluível**.

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

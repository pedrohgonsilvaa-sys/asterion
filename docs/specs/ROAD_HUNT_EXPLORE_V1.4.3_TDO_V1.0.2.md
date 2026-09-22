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

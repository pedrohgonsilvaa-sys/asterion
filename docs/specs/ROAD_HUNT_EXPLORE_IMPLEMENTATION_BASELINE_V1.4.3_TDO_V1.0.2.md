# Baseline autocontida de implementação — Estrada das Cinzas

> Complemento normativo da especificação `docs/specs/ROAD_HUNT_EXPLORE_V1.4.3_TDO_V1.0.2.md`.
>
> Este documento **não cria balanceamento novo**. Ele apenas transcreve, para dentro do repositório, os valores necessários ao PR de Caçada/Desbravar que já existem nas autoridades externas: GDD Estrutural v1.4.3 e Terras do Ocaso v1.0.2 FINAL.
>
> Motivo: o repositório atual contém `SOURCE_AUTHORITY.md` e a especificação focada, mas não contém cópias integrais das três Fontes. O Codex deve poder implementar este bloco sem depender de acesso externo a essas Fontes nem inventar constantes.

## 1. Convenções de arredondamento necessárias neste bloco

- `round_half_up(x)`: inteiro mais próximo; empate exato `.5` sobe.
- `round_10(x)`: múltiplo de 10 mais próximo; empate usa **ties-to-even** no quociente por 10.
  - exemplos: `115→120`, `125→120`, `135→140`, `145→140`.
- `round_100(x)`: múltiplo de 100 mais próximo, também ties-to-even.
- grandeza em passos de `0,25 p.p.`: arredondar ao passo mais próximo com ties-to-even, salvo mínimo positivo explicitamente definido.
- Coroas são inteiras; multiplicadores monetários sobre `C(n)` usam `round_10` no resultado final salvo regra diferente explícita.

## 2. Atributos de inimigos — fórmula já usada pelo repositório

Reutilizar a curva e os helpers já existentes em `src/asterion/domain/combat_math.py`. Não duplicar a curva em uma segunda implementação.

Referência neutra por nível já existente no código:

- HP60 de referência = `7735/3`;
- ATQ60 = `1216/3`;
- DEF60 = `294.5`;
- AGI60 = `304`;
- curva `G(n)=4^((n−60)/59)`.

Atributo neutro do nível = valor60 × `G(n)`.

Os multiplicadores de **Categoria** e **Arquétipo** são aplicados multiplicativamente antes do único `round_half_up` final por atributo.

### 2.1 Categoria Solo

| Categoria | HP | ATQ | DEF | AGI |
|---|---:|---:|---:|---:|
| Comum | 0.70 | 0.82 | 0.90 | 0.95 |
| Incomum | 0.85 | 0.90 | 0.95 | 1.00 |
| Elite | 1.50 | 1.05 | 1.05 | 1.02 |
| Chefe | 2.20 | 1.10 | 1.10 | 1.00 |

### 2.2 Arquétipos

| Arquétipo | HP | ATQ | DEF | AGI |
|---|---:|---:|---:|---:|
| Equilibrado | 1.00 | 1.00 | 1.00 | 1.00 |
| Bruto | 1.15 | 1.12 | 0.95 | 0.85 |
| Predador | 0.90 | 1.10 | 0.90 | 1.20 |
| Blindado | 1.10 | 0.88 | 1.20 | 0.85 |
| Conjurador | 0.85 | 1.15 | 0.88 | 1.00 |
| Controlador | 0.95 | 0.90 | 1.00 | 1.10 |

### 2.3 Mapeamento das quatro criaturas deste bloco

- Cão Cinéreo = **Comum + Predador**.
- Corvo de Fuligem = **Comum + Predador**.
- Peregrino Calcinado = **Comum + Equilibrado**.
- Alfa Cinéreo = **Elite + Predador**.

Faixas regionais:

- Cão: Nv.1–3;
- Corvo: Nv.1–4;
- Peregrino: Nv.2–5;
- Alfa: Nv.3–4.

A Caçada usa `enemy_level = min(player_level, max_enemy_level)`, depois de respeitar o `unlock_level`.

### 2.4 Valores de regressão derivados da fórmula vigente

Estes valores são **derivados** das constantes acima e servem para testes, não substituem a fórmula:

| Criatura | Nv. | HP | ATQ | DEF | AGI |
|---|---:|---:|---:|---:|---:|
| Cão/Corvo | 1 | 406 | 91 | 60 | 87 |
| Cão/Corvo | 2 | 416 | 94 | 61 | 89 |
| Cão/Corvo | 3 | 426 | 96 | 63 | 91 |
| Corvo | 4 | 436 | 98 | 64 | 93 |
| Peregrino | 2 | 462 | 85 | 68 | 74 |
| Peregrino | 3 | 473 | 87 | 69 | 76 |
| Peregrino | 4 | 484 | 89 | 71 | 77 |
| Peregrino | 5 | 496 | 91 | 73 | 79 |
| Alfa | 3 | 912 | 123 | 73 | 97 |
| Alfa | 4 | 934 | 126 | 75 | 100 |

Variantes são aplicadas depois do perfil categoria+arquétipo conforme a especificação:
- Furioso: ATQ +8%, DEF −8%;
- Resistente: DEF +10%, ATQ −6%;
- Ágil: AGI +12%, HP −7%;
- Hemorrágico: ATQ −5% + pacote de Sangramento;
- Venenoso: HP −5% + pacote de Veneno.

## 3. EnemyXP completo para Caçada/Exploração

Para `1 ≤ n ≤ 59`:

`XP(n) = round_100(4000 + 750n + 43n²)`

`H(n) = 0.905903 + 0.094097n`

`XP_ref(n) = XP(n)`

`EnemyXPUnit(n) = XP_ref(n) / [20 × H(n)]`

Multiplicador por categoria:

- Comum `1.00`;
- Incomum `1.35`;
- Elite `2.75`;
- Chefe `6.00`.

Fórmula:

`EnemyXP = round_10(EnemyXPUnit(enemy_level) × CategoryMultiplier × LevelFactor × PowerlevelFactor × ParticipationFactor × VigorXPFactor × LegacyXPFactor)`

Não arredondar intermediários.

### 3.1 LevelFactor

Usar `delta = enemy_level - recipient_level`:

- `delta ≥ +5 → 110%`;
- `+3/+4 → 105%`;
- `−2…+2 → 100%`;
- `−3…−5 → 80%`;
- `−6…−10 → 50%`;
- `−11…−20 → 20%`;
- `≤−21 → 5%`.

### 3.2 Demais fatores neste PR Solo

- PowerlevelFactor Solo normal: `100%`.
- ParticipationFactor Solo válido: `100%`.
- VigorXPFactor:
  - economia repetível elegível com Vigor suficiente → `100%`;
  - conteúdo repetível com Vigor insuficiente → `25%`.
- LegacyXPFactor na primeira jornada normal → `100%`.

### 3.3 Regressão de Comum equivalente no mesmo nível

| Nv. | XP Comum |
|---:|---:|
| 1 | 240 |
| 2 | 260 |
| 3 | 280 |
| 4 | 300 |
| 5 | 320 |

Elite equivalente no mesmo nível, derivado com `2.75×` e um único `round_10` final:

- Nv.3 → `760 XP`;
- Nv.4 → `830 XP`.

## 4. Coroas

`C(n)=round_10(100+15n)`

Pontos de regressão:

- Nv.1 → 120;
- Nv.2 → 130;
- Nv.3 → 140;
- Nv.4 → 160;
- Nv.5 → 180;
- Nv.10 → 250.

Caçada:
- Comum `0.05×C(enemy_level)`;
- Elite `0.25×C(enemy_level)`.

Aplicar `round_10` ao resultado monetário final.

Desbravar deste bloco preserva a própria spec:
- Pequeno Recurso: `0.10×C(nível aplicável)`;
- `exploration_combat`: `0.15×C(nível aplicável)`.

## 5. Saque da Caçada — tabelas globais necessárias

Todos os rolls são separados e derivados da seed persistida do encontro.

### 5.1 Materiais

Comum:
- `80% → 1` Material Básico.

Elite:
- `3–4` Materiais Básicos garantidos;
- `+1 Catalisador de Elite I` garantido;
- Fragmento de Aprimoramento I: `40% → 1`.

Comum não possui Fragmento normal.

Identidade regional do Material Básico já fechada na spec:
- Cão → Couro Escoriado;
- Corvo → Resíduo do Ocaso;
- Peregrino → Ferro de Fuligem / Erva Cinzenta, uniforme por unidade;
- Alfa → Couro Escoriado.

### 5.2 Equipamento — chance

- Comum: `8%`;
- Elite: `35%`.

Raridade condicional, na ordem Comum / Raro / Épico / Lendário / Mítico:

- drop de Comum: `78 / 19 / 2.8 / 0.2 / 0 %`;
- drop de Elite: `45 / 42 / 11 / 1.9 / 0.1 %`.

Pity de Caçada:
- 12 **drops de Equipamento** Elite/Chefe sem Épico+ → próximo drop elegível é ≥Épico;
- 50 sem Lendário+ → próximo drop elegível é ≥Lendário.

Não incrementar esses contadores em encontro Comum nem em tentativa sem drop de Equipamento, salvo se a implementação existente da autoridade já modelar de forma equivalente; a semântica autoritativa é “drops de Equipamento Elite/Chefe”.

### 5.3 Runa — chance

- Comum: `0.5%`;
- Elite: `5%`.

Raridade da Runa na ordem Rara / Épica / Lendária:

- Comum: `90 / 9.5 / 0.5 %`;
- Elite: `80 / 18 / 2 %`.

### 5.4 Receita especial

A regra global só tenta Receita quando existe receita desconhecida **elegível para aquela fonte**.

Neste bloco da Estrada não há Receita especial configurada como elegível para a Caçada genérica. Portanto:
- não inventar Receita de Caçada;
- não reutilizar Receitas de Campanha/Masmorra como drop genérico da Estrada.

## 6. Materialização de Equipamento — números necessários

### 6.1 SlotWeight

- Principal: `18`;
- Secundária: `10`;
- Cabeça: `10`;
- Torso: `16`;
- Mãos: `10`;
- Pés: `10`;
- Acessório: `12`;
- Artefato: `14`;
- 2H: `28` (equivale Principal + Secundária).

### 6.2 Raridade / secundários

| Raridade | Mult | Secundários |
|---|---:|---:|
| Comum | 1.00 | 0 |
| Raro | 1.07 | 1 |
| Épico | 1.15 | 2 |
| Lendário | 1.24 | 3 |
| Mítico | 1.45 | 4 |

### 6.3 Núcleo Comum +0 Nv.60

- Principal: ATQ 25;
- Secundária: ATQ 7, DEF 5;
- Cabeça: HP 45, DEF 6;
- Torso: HP 95, DEF 12;
- Mãos: ATQ 10, DEF 5;
- Pés: HP 60, AGI 8;
- Acessório: HP 50, ATQ 7, AGI 4;
- Artefato: HP 55, ATQ 7, DEF 5, AGI 4;
- 2H ofensiva: ATQ 35.

Para `item_level=n`:

`G(n)=4^((n−60)/59)`

Cada atributo-base plano intermediário:

`round_half_up(Value60 × G(n))`.

Neste PR todo Equipamento da Estrada usa `item_level = enemy_level`.

### 6.4 Pools de secundários

- Principal: ATQ, AGI, PER, CRIT.
- Secundária: ATQ, DEF, PER, CRIT, Bloqueio.
- Cabeça: HP, DEF, PER, CRIT.
- Torso: HP, DEF, Bloqueio.
- Mãos: ATQ, AGI, PER, CRIT.
- Pés: HP, DEF, AGI, Esquiva.
- Acessório: HP, ATQ, AGI, PER, CRIT, Esquiva.
- Artefato: HP, ATQ, DEF, PER, CRIT, Bloqueio.
- 2H usa o pool de Principal para secundários do próprio Equipamento.

### 6.5 Budget dos secundários

`budget_por_secundário = SlotWeight × (RarityMult − 1) / secondary_count`.

Valor por `1.0` budget no Nv.60:
- HP 8.5;
- ATQ 1.35;
- DEF 2.30;
- AGI 3.00;
- PER 0.80 p.p.;
- CRIT 0.67 p.p.;
- Esquiva 0.33 p.p.;
- Bloqueio 0.95 p.p.

Atributos percentuais usam:

`Q(n)=sqrt(G(n))`

e são arredondados ao passo de `0.25 p.p.`, ties-to-even, com mínimo positivo de `0.25 p.p.`.

Não criar duplicata de secundário no mesmo item.

Torso Mítico genérico permanece inelegível porque o pool de Torso possui apenas 3 identidades e Mítico exige 4 distintas.

## 7. Catálogo regional elegível para loot genérico

Somente estas 13 famílias normais entram no gerador:

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

Não entram:
- exclusivos de P3/P6;
- Relicário dos Sem-Nome;
- Guarda do Primeiro Selo;
- qualquer nome histórico não presente no catálogo oficial.

Seleção segue a spec:
1. grupo de slot uniforme entre grupos elegíveis;
2. template uniforme dentro do grupo na ausência de peso explícito;
3. 2H participa do grupo Principal, não cria nono grupo.

## 8. Runas Grau I

Famílias elegíveis:
- Runa da Brasa · ATQ
- Runa da Pedra · DEF
- Runa do Caminhante · AGI
- Runa da Fresta · PER
- Runa do Presságio · CRIT
- Runa da Persistência · HP
- Runa do Desvio · Esquiva
- Runa da Guarda · Bloqueio

Na Estrada, `loot_reference_level 1–10 → Grau I`.

Potência Grau I:

| Efeito | Rara | Épica | Lendária |
|---|---:|---:|---:|
| HP | +0.35% | +0.45% | +0.55% |
| ATQ | +0.35% | +0.45% | +0.55% |
| DEF | +0.55% | +0.80% | +1.00% |
| AGI | +0.55% | +0.80% | +1.00% |
| PER | +0.25 p.p. | +0.50 p.p. | +0.50 p.p. |
| CRIT | +0.25 p.p. | +0.50 p.p. | +0.50 p.p. |
| Esquiva | +0.25 p.p. | +0.25 p.p. | +0.25 p.p. |
| Bloqueio | +0.25 p.p. | +0.50 p.p. | +0.50 p.p. |

Família é uniforme salvo peso explícito; este bloco não declara peso especial.
Não há smart loot.
Compatibilidade de slot só é validada ao instalar a Runa.

## 9. Bestiário — números necessários

Perfis:
- Comum → `COMMON`;
- Elite → `ELITE`.

Thresholds regionais:
- COMMON: Conhecido 10 / Estudado 30 + ≥2 categorias de evidência / Dominado 60 + ≥3 categorias.
- ELITE: Conhecido 10 / Estudado 25 / Dominado 45 + vitória + mecânica/evidência especial configurada.

BKP-base:
- primeira observação +4;
- primeiro combate +3;
- primeira vitória +5;
- nova Arte/comportamento +4;
- nova mecânica +5;
- Habitat +3;
- investigação Desbravar +8 **somente quando uma regra de conteúdo realmente a conceder**;
- Variante descoberta +8;
- primeira vitória da Variante +6;
- forma Elite +8;
- primeira vitória de Elite +6.

Repetição:
- Comum: vitórias 2ª–5ª +2; 6ª–10ª +1; marcos 15/25/40 +3; demais 0.
- Elite: 2ª +3; 3ª +2; 4ª–5ª +1.

Alfa Cinéreo, para Dominado, além do BKP Elite exige:
- primeira vitória;
- observar Investida Rasgante com Sangramento;
- testemunhar Salto Predatório preparado.

## 10. Desbravar — baseline global compacta

- cooldown 5 min;
- máximo 6 tentativas / Local / 60 min;
- Solo;
- categorias `8/22/15/25/10/20`;
- resultado imediatamente anterior peso 0;
- resultado nas últimas 3 tentativas válidas peso ×0.35;
- resultado único sai permanentemente após resolução válida;
- Pequeno Recurso: `0.10×C +1 básico`;
- combate repetível genérico: `0.15×C +1 básico +20% de +1`;
- ambos consomem 4 Vigor **somente quando concedem economia**;
- com Vigor insuficiente, conteúdo repetível usa `VigorXPFactor=25%` onde houver XP repetível.

Os subpesos e textos específicos da Estrada continuam na especificação principal.

## 11. Regra de implementação

Se houver divergência entre:
1. esta baseline autocontida;
2. a especificação principal;
3. código histórico do repositório;

não escolher silenciosamente.

A especificação principal prevalece para as **decisões adicionais aprovadas especificamente para este bloco**. Esta baseline prevalece apenas como transcrição dos valores globais/regionais que a spec referencia. Código histórico não pode sobrescrever as autoridades sem migração/regra explícita.

Se ainda faltar uma constante necessária depois de considerar os dois documentos, parar e reportar a constante exata ausente antes de programar.

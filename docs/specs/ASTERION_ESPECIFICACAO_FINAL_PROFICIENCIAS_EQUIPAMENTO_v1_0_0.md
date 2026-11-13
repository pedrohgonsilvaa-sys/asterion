# ASTERION — ESPECIFICAÇÃO FINAL CONSOLIDADA
## Proficiências de Armas, Catálogo de Armas e Regras de Equipamento

**Versão:** v1.0.0
**Status:** Design fechado para implementação
**Destinatário:** equipe de implementação / Claude Code
**Escopo:** sistema global de Proficiências de Armas, identidade de armas, compatibilidade por Classe e integração com Equipamento e Artes.

---

# 0. PRINCÍPIO DE AUTORIDADE

Esta especificação representa o desenho fechado aprovado nesta etapa do projeto. Ela não deve inventar novas mecânicas para preencher lacunas.

A implementação deve respeitar a hierarquia existente de Asterion:

1. GDD Estrutural vigente = sistemas e regras globais.
2. Contrato global de metadata de armas vigente = metadata canônica de itens de arma.
3. Fontes Regionais FINAL = conteúdo publicado e armas concretas de suas regiões.
4. Bíblia Canônica = lore, raças, NPCs e travas de conteúdo.
5. Fontes visuais = apresentação visual; nunca criam mecânica.

Este documento introduz e fecha o **novo sistema de Proficiências**, mas deve ser integrado ao cânone existente de forma explícita, versionada e testável.

---

# 1. OBJETIVO DO SISTEMA

Proficiência de Arma é uma autorização permanente de uso de uma família/categoria de armamento compatível com a Classe do personagem.

A Proficiência:

- permite equipar armas da família correspondente;
- não concede atributos;
- não aumenta dano;
- não fornece bônus de ataque;
- não reduz cooldown;
- não modifica crítico, bloqueio, esquiva ou precisão;
- não cria árvore de habilidades;
- não cria maestria separada;
- não cria XP de arma;
- não cria níveis internos da proficiência;
- não cria penalidade por arma não treinada;
- não cria postura de arma;
- não cria combo;
- não cria ataque extra;
- não cria regra de dual wield;
- não cria alcance numérico;
- não cria arremesso/projétil/ammo.

A função da Proficiência é exclusivamente de **elegibilidade permanente de equipamento**, limitada pela identidade da Classe.

---

# 2. PRINCÍPIOS FECHADOS

## 2.1 Liberdade dentro da identidade

O jogador deve possuir liberdade real para montar o personagem, mas essa liberdade ocorre dentro do conjunto coerente de armas da sua Classe.

## 2.2 Coerência por Classe

Cada Classe possui uma lista explícita de armas/famílias que pode aprender. Essa compatibilidade não deve ser inferida por nome, animação, estética, atributo ou lore.

Exemplo de princípio: uma arma lançável não torna automaticamente a Classe Vigia compatível com toda e qualquer haste pesada. Compatibilidade é um registro explícito.

## 2.3 Sem simetria artificial

Classes mágicas podem aprender armas marciais quando isso fizer sentido para sua identidade. Não existe obrigação de todas as Classes possuírem o mesmo número de opções.

## 2.4 Sem teto artificial

Não existe limite global como “máximo de 3 proficiências”. Um personagem pode aprender todas as Proficiências que legalmente conseguir adquirir.

## 2.5 Permanente

Uma Proficiência adquirida é permanente e não possui sistema de reset/troca.

---

# 3. FAMÍLIAS DE PROFICIÊNCIA

O sistema possui 8 famílias de armas e 1 categoria separada de Escudo.

| Família/Categoria | Função conceitual |
|---|---|
| Espadas | Lâminas de espada de uso convencional e pesado |
| Lâminas | Armas leves, rápidas e exóticas de lâmina |
| Contundentes | Maças e martelos |
| Machados | Machados de uma e duas mãos |
| Hastes | Lança, alabarda e azagaia |
| Arcos | Armas de arco |
| Bestas | Armas de besta |
| Focos Arcanos | Cetro, orbe e cajado |
| Escudo | Categoria defensiva secundária, separada das famílias ofensivas |

**Importante:** `weapon_family` não existe atualmente no modelo canônico vigente. Nesta especificação, “família” é uma abstração funcional do sistema de Proficiências. A implementação deve decidir se ela será um registro separado, um campo explícito ou um mapeamento equivalente, sem conflitar com a semântica existente de `weapon_form`.

---

# 4. CATÁLOGO FINAL DE ARMAS

## 4.1 Espadas

- **Espada** — 1H — principal.
- **Espada de Guerra** — 2H — principal; bloqueia secundária.

## 4.2 Lâminas

- **Adaga** — 1H.
- **Adaga de Arremesso** — 1H.
- **Chakram** — 1H.
- **Lâmina Dupla** — 2H.

## 4.3 Contundentes

- **Maça** — 1H.
- **Martelo de Guerra** — 2H.

## 4.4 Machados

- **Machado** — 1H.
- **Machado de Guerra** — 2H.

## 4.5 Hastes

- **Lança** — 1H.
- **Alabarda** — 2H.
- **Azagaia** — 1H.

## 4.6 Arcos

- **Arco** — 2H.

## 4.7 Bestas

- **Besta de Mão** — 1H.
- **Besta Pesada** — 2H.

## 4.8 Focos Arcanos

- **Cetro** — 1H.
- **Orbe** — 1H.
- **Cajado** — 2H.

## 4.9 Escudo

- **Escudo** — categoria separada, secundária.

Escudo não é uma família ofensiva e não deve virar uma “família de arma” convencional.

**Regra fechada:** Escudo não cria uma mecânica especial de bloqueio por si só. Ele usa as regras normais do slot Secundária e os atributos/effects explicitamente declarados pelo item. Não inventar bônus universal de bloqueio, redução, resistência, cobertura ou postura de escudo.

---

# 5. REMOÇÕES E CONSOLIDAÇÕES DE CATÁLOGO

Os seguintes nomes não devem voltar como tipos independentes no catálogo-base:

- Espada Longa — consolidada em Espada / Espada de Guerra.
- Espada Bastarda — consolidada em Espada / Espada de Guerra.
- Faca de Combate — consolidada em Adaga.
- Kukri — removida como tipo independente.
- Massa/Mangual e variantes redundantes — não fazem parte do catálogo-base; usar Maça ou Martelo de Guerra quando aplicável.
- Glaive e variantes adicionais de haste — não fazem parte do catálogo-base; usar Lança / Alabarda / Azagaia.
- Arco Curto / Arco de Guerra — consolidados em Arco.
- Bastão — consolidado em Cajado.
- Varinha — não é categoria própria do catálogo-base.
- Grimório — removido do catálogo-base.
- Adaga Cerimonial — removida do catálogo-base.
- “Arremesso” como Proficiência independente — não existe.

---

# 6. ARREMESSO, PROJÉTEIS E ARMAS EXÓTICAS

Adaga de Arremesso, Chakram e Azagaia existem como identidades de equipamento do catálogo final, mas **não introduzem mecânica de arremesso nesta versão**.

Não implementar:

- ação “Arremessar”;
- dano de arremesso;
- alcance numérico;
- munição;
- projétil físico;
- retorno de projétil;
- regra de distância;
- penalidade por alcance;
- troca automática para ataque à distância;
- ataque extra derivado de arremesso.

A presença de “de Arremesso” no nome é identidade de item e não autorização para criar um subsistema de projeção.

Se o modelo canônico atual não comportar uma forma visualmente distinta sem adicionar nova mecânica, a solução deve ser uma extensão explícita de metadata/forma, não um comportamento oculto.

---

# 7. FORMAS DE ARMA E COMPATIBILIDADE

A forma (`weapon_form`) continua sendo descritiva e não deve ser usada para inferir:

- mãos;
- slot;
- Classe;
- Proficiência;
- requisito de Arte;
- dano;
- alcance;
- cadência;
- regra de combate.

A implementação deve manter explícitos e independentes:

- identidade concreta do item/template;
- família de Proficiência;
- `handedness`;
- elegibilidade de slot;
- tags de compatibilidade com Artes;
- atributos do item;
- raridade/Grau/item_level;
- runas/encantamentos;
- restrições de Classe/Caminho quando existirem.

Se a lista fechada atual de `weapon_form` não comportar corretamente a identidade final de itens como Chakram, Lâmina Dupla, Cetro, Orbe ou Azagaia, a lista deve ser expandida de maneira versionada e explícita. Não colapsar silenciosamente identidades distintas em formas incompatíveis apenas para evitar migração.

---

# 8. REGRAS 1H / 2H / SLOTS

As regras canônicas atuais permanecem:

- 1H não significa automaticamente “qualquer mão”.
- A elegibilidade de slot é explícita no item.
- 2H ocupa Arma Principal e bloqueia Arma Secundária.
- A troca de equipamento deve ser atômica.
- Um item secundário ocupado deve ser movido validamente ao Inventário quando uma 2H assumir o estado.
- Não existe estado oculto de “off-hand equipada” fora da configuração efetiva.

Não existe regra global de dual wield.

Uma personagem pode possuir dois itens de uma mão somente quando os dois templates concretos forem legalmente equipáveis nos slots correspondentes. Isso **não** cria:

- bônus por duas armas;
- ataque extra;
- ataque secundário automático;
- penalidade de dual wield;
- Proficiência de dual wield;
- postura de dual wield.

---

# 9. MATRIZ FINAL DE COMPATIBILIDADE POR CLASSE

A matriz de Classe abaixo é a fonte de coerência do sistema. Uma Proficiência de família nunca ultrapassa a whitelist concreta da Classe.

## 9.1 Sentinela

**Permitidos:**

- Espada
- Espada de Guerra
- Adaga
- Adaga de Arremesso
- Chakram
- Lâmina Dupla
- Maça
- Martelo de Guerra
- Machado
- Machado de Guerra
- Lança
- Alabarda
- Azagaia
- Escudo

**Não permitidos:** Arco, Besta de Mão, Besta Pesada, Cetro, Orbe, Cajado.

## 9.2 Errante

**Permitidos:**

- Espada
- Adaga
- Adaga de Arremesso
- Chakram
- Lâmina Dupla
- Besta de Mão
- Machado

**Não permitidos:** Espada de Guerra, Maça, Martelo de Guerra, Machado de Guerra, Lança, Alabarda, Azagaia, Arco, Besta Pesada, Escudo, Cetro, Orbe, Cajado.

## 9.3 Vigia

**Permitidos:**

- Espada
- Adaga
- Adaga de Arremesso
- Chakram
- Arco
- Besta de Mão
- Besta Pesada

**Não permitidos:** Espada de Guerra, Lâmina Dupla, Maça, Martelo de Guerra, Machado, Machado de Guerra, Lança, Alabarda, Azagaia, Escudo, Cetro, Orbe, Cajado.

## 9.4 Tecelão

**Permitidos:**

- Cajado
- Orbe
- Cetro
- Espada
- Adaga

**Não permitidos:** Espada de Guerra, Maça, Martelo de Guerra, Machado, Machado de Guerra, Lança, Alabarda, Azagaia, Arco, Besta de Mão, Besta Pesada, Escudo.

## 9.5 Oráculo

**Permitidos:**

- Cajado
- Orbe
- Cetro
- Maça
- Adaga
- Escudo

**Não permitidos:** Espada, Espada de Guerra, Martelo de Guerra, Machado, Machado de Guerra, Lança, Alabarda, Azagaia, Arco, Besta de Mão, Besta Pesada.

## 9.6 Luminar

**Permitidos:**

- Cajado
- Orbe
- Cetro
- Espada
- Maça
- Machado
- Escudo

**Não permitidos:** Espada de Guerra, Martelo de Guerra, Machado de Guerra, Lança, Alabarda, Azagaia, Arco, Besta de Mão, Besta Pesada.

---

# 10. INTERPRETAÇÃO DA MATRIZ: FAMÍLIA + WHITELIST CONCRETA

A Proficiência é adquirida por família/categoria, mas nunca substitui a compatibilidade concreta da Classe.

Exemplo:

- Errante pode aprender **Espadas**.
- Espadas contém Espada e Espada de Guerra.
- A whitelist do Errante contém Espada, mas não Espada de Guerra.
- Portanto, a Proficiência em Espadas permite ao Errante usar Espada, mas não Espada de Guerra.

O mesmo princípio se aplica a todos os outros casos de 1H/2H e variantes pesadas.

Uma Classe só pode aprender uma família se houver pelo menos uma identidade concreta compatível naquela família.

---

# 11. PROFICIÊNCIA INICIAL POR CLASSE

Cada personagem começa com exatamente **1 Proficiência inicial gratuita**, definida pela Classe.

| Classe | Proficiência inicial | Equipamento inicial |
|---|---|---|
| Sentinela | Espadas | Espada, +0, Grau I |
| Errante | Lâminas | Adaga, +0, Grau I |
| Vigia | Arcos | Arco, +0, Grau I |
| Tecelão | Focos Arcanos | Cajado, +0, Grau I |
| Oráculo | Focos Arcanos | Orbe, +0, Grau I |
| Luminar | Focos Arcanos | Cetro, +0, Grau I |

Equipamento inicial segue as regras globais existentes de item_level/Grau/+0.

---

# 12. EQUIPAMENTO INICIAL — O QUE NÃO INICIA EQUIPADO

Não iniciar equipado:

- Acessório/Amuleto;
- Artefato;
- Consumíveis;
- Escudo, salvo se uma futura fonte de conteúdo declarar explicitamente outro estado.

Não criar slots adicionais.

---

# 13. APRENDIZADO DE NOVAS PROFICIÊNCIAS

Novas Proficiências são aprendidas por um **Treinador de Armas**.

## 13.1 Regras

- compra/aprendizado é permanente;
- sem reset;
- sem troca de proficiência;
- sem XP de arma;
- sem sistema de maestria;
- sem árvore;
- sem teto global;
- apenas famílias legalmente compatíveis com a Classe ficam disponíveis;
- o sistema deve impedir treinamento de família sem nenhuma identidade concreta utilizável pela Classe.

## 13.2 Progressão proposta fechada

| Proficiência adquirida | Nível mínimo |
|---:|---:|
| 1ª | 1 |
| 2ª | 10 |
| 3ª | 20 |
| 4ª | 30 |
| 5ª | 40 |
| 6ª+ | 50 |

## 13.3 Custo em Coroas

| Proficiência adquirida | Custo |
|---:|---:|
| 1ª | gratuita na criação |
| 2ª | 1.000 Coroas |
| 3ª | 2.500 Coroas |
| 4ª | 5.000 Coroas |
| 5ª | 10.000 Coroas |
| 6ª+ | 20.000 Coroas |

Não existe custo de XP para aprender Proficiência.

Não criar descontos automáticos por build, Classe, Caminho, rarity ou “necessidade” percebida.

---

# 14. INTERAÇÃO COM O EQUIPMENT VALIDATOR

Toda tentativa de equipar uma arma deve validar, atomicamente:

1. ownership/bind quando aplicável;
2. estado do item;
3. `item_level` vs nível do personagem;
4. slot elegível;
5. Classe/Caminho se explicitamente exigidos pelo item;
6. Proficiência da família/categoria;
7. whitelist concreta de compatibilidade da Classe;
8. regra 2H / Secundária;
9. máximo de 1 Mítico equipado;
10. demais precondições globais já vigentes.

A Proficiência não substitui o Equipment Validator. Ela vira uma precondição adicional.

---

# 15. INTERAÇÃO COM ARTES

O novo sistema de Proficiências **não substitui** `weapon_requirement` das Artes.

A regra existente permanece:

- cada Arte declara explicitamente o próprio requisito;
- requisito não pode ser inferido da Classe, Caminho, nome, animação ou forma visual;
- `none` continua significando que a Arte pode ser usada sem arma específica quando o restante do estado permitir;
- tags de compatibilidade continuam explícitas por item.

Proficiência responde à pergunta:

> “Este personagem pode equipar esta arma?”

`weapon_requirement` responde à pergunta:

> “Esta arma/equipamento satisfaz o requisito desta Arte?”

As duas camadas são independentes.

Não criar requisito de Foco Arcano para Artes existentes apenas porque Tecelão/Oráculo/Luminar usam Focos.

Não alterar a regra da Ataque Básico para exigir arma sem uma decisão separada.

---

# 16. REGRAS DE COMBATE QUE NÃO MUDAM

Esta reformulação NÃO adiciona:

- dano base de arma;
- coeficiente de arma;
- velocidade de arma;
- ataques por turno derivados da arma;
- alcance;
- grade/distância;
- dano físico/mágico por tipo de arma;
- crítico próprio da arma;
- bloqueio próprio da arma;
- precisão própria da arma;
- durabilidade;
- munição;
- combo;
- postura;
- cone;
- cleave genérico de arma;
- projeção;
- retorno de projétil;
- dual wield mecânico.

Armas continuam participando do combate por suas propriedades já existentes no sistema de Equipamento, principalmente atributos, slot, mãos, tags, runas/encantamentos, aprimoramento, raridade/Grau/item_level e compatibilidade.

---

# 17. REGRAS DE EQUIPAMENTO QUE PERMANECEM

Preservar integralmente a baseline existente:

- 8 slots oficiais;
- sem armadura leve/média/pesada;
- sem peso físico/equip load;
- `SlotWeight` continua sendo orçamento/custo de slot;
- `item_level` é imutável;
- `required_level = item_level`;
- Grau I–VI deriva de item_level;
- raridades Comum/Raro/Épico/Lendário/Mítico;
- secundários 0/1/2/3/4;
- máximo de 1 Mítico equipado;
- +0 a +10 garantido;
- sem falha/downgrade/destruição;
- equipamento nasce +0, sem runa/encantamento salvo declaração explícita da fonte;
- materialização determinística e idempotente;
- smart loot continua proibido por Classe/Caminho/build.

---

# 18. MIGRAÇÃO DO CÂNONE ATUAL

A revisão técnica atual indica que o modelo canônico vigente ainda não possui Proficiências/Mastery, e que `weapon_family` não existe no modelo atual. Portanto, esta especificação exige uma migração explícita.

## 18.1 O que deve ser adicionado

- sistema persistente de Proficiências por personagem;
- catálogo/registro de famílias de Proficiência;
- registry de compatibilidade Classe → item/família;
- regra de aprendizado permanente;
- treinador e custo/progressão;
- validação da Proficiência dentro do Equipment Validator;
- seed inicial de Proficiência por Classe;
- equipamento inicial por Classe;
- testes de regressão.

## 18.2 O que NÃO deve ser adicionado

- árvore de talentos de arma;
- XP de arma;
- níveis de maestria;
- bônus de atributo por proficiência;
- penalidade por falta de proficiência;
- dual wield;
- arremesso;
- alcance;
- munição;
- novas regras de combate derivadas da forma da arma.

## 18.3 Catálogo de formas

O modelo canônico atual usa uma lista fechada de `weapon_form`. A implementação deve auditar todos os itens concretos do novo catálogo e decidir explicitamente se:

1. a forma existente representa corretamente a identidade; ou
2. a lista de formas precisa ser ampliada.

Não fazer mapeamentos silenciosos que destruam identidade semântica.

---

# 19. MIGRAÇÃO DAS ARMAS JÁ PUBLICADAS

Antes de alterar dados:

1. inventariar todas as armas publicadas no código/arquivos de conteúdo;
2. preservar IDs estáveis;
3. atribuir cada item à família final correta;
4. validar `handedness` explícito;
5. validar slot eligibility explícito;
6. validar tags de compatibilidade com Artes;
7. validar compatibilidade com cada Classe;
8. identificar qualquer arma regional que esteja fora do mapa global de metadata;
9. não apagar conteúdo publicado sem uma decisão de migração documentada.

Caso exista conflito entre um item regional e esta especificação, preservar o ID e sinalizar a migração concreta que deve ser aplicada.

---

# 20. TESTES OBRIGATÓRIOS

## 20.1 Proficiência

- personagem recebe 1 Proficiência inicial correta por Classe;
- família incompatível não aparece como opção;
- família sem item compatível na Classe não pode ser aprendida;
- custo e nível mínimo são respeitados;
- compra duplicada é recusada/idempotente;
- Proficiência permanece após reconnect/restart;
- não existe reset implícito;
- não existe cap artificial.

## 20.2 Equipamento

- arma compatível e treinada equipa;
- arma compatível mas não treinada falha;
- arma treinada mas não permitida pela Classe falha;
- item acima do nível falha;
- 2H bloqueia Secundária;
- troca 2H é atômica;
- Mítico continua limitado a 1;
- callbacks duplicados não geram estado parcial.

## 20.3 Classes

Testar pelo menos um caso positivo e negativo para cada Classe e para as variantes pesadas:

- Sentinela: Espada de Guerra permitida;
- Errante: Espada permitida, Espada de Guerra recusada;
- Vigia: Besta Pesada permitida;
- Tecelão: Espada permitida;
- Oráculo: Escudo permitido, Espada recusada;
- Luminar: Machado permitido, Machado de Guerra recusado.

## 20.4 Artes

- Proficiência não altera `weapon_requirement`;
- Arte `none` continua funcionando sem arma específica quando permitido;
- Arte melee continua exigindo tag melee explícita;
- Arte bow/crossbow continua exigindo tag correspondente;
- nenhuma compatibilidade é inferida por nome da arma.

---

# 21. CRITÉRIO DE CONCLUSÃO

A implementação está correta quando:

1. o sistema atual de Equipamento continua funcionando;
2. Proficiências passam a ser o único gate de treinamento permanente de armas;
3. cada Classe mantém uma identidade coerente e auditável;
4. a liberdade do jogador aumenta sem criar uma árvore ou um segundo sistema de progressão de combate;
5. nenhuma regra nova de combate é criada implicitamente;
6. todos os itens publicados têm metadata/mapeamento explícito;
7. o estado é persistente, atômico e idempotente;
8. testes cobrem positivos, negativos, migração e regressão.

---

# 22. FONTE TÉCNICA DE CONTEXTO

A baseline atual do GDD estabelece que armas podem ter subtipo/forma descritiva sem que isso crie automaticamente atributos, proficiência, restrição ou regra de combate; 2H ocupa Principal e bloqueia Secundária. O Equipment Validator já é a autoridade de validação de equipamento e as mudanças são atômicas.

A seção 55.3 do GDD vigente também declara atualmente que não existem Proficiências globais de arma e que `weapon_requirement` das Artes é explícito, independente de Classe, Caminho e forma visual. Esta especificação é a mudança deliberada dessa regra para introduzir o sistema de Proficiências, sem romper as demais separações conceituais.

**Decisão estrutural:** a implementação deve alterar apenas o que esta especificação redefine; todo o restante do sistema atual permanece vigente.

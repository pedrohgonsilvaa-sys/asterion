# Asterion — Eventos Públicos
## Catálogo consolidado — versão de implementação

> Todas as criaturas são novas e exclusivas de Evento Público. Nenhuma reutiliza ficha do Bestiário canônico.
> Eventos Públicos são **Eventos Mundiais**, não conteúdo de Guilda.
> Não existe trava de nível mínimo de entrada. `reference_level` é referência de conteúdo/scaling, não gate.

## Regras estruturais do catálogo

- Cada ocorrência usa `event_id + occurrence_id`.
- Há **5 minutos de reunião** antes do início da Fase 1.
- Cada ocorrência possui **3 fases** e **1 Chefe por fase**.
- A fase seguinte só começa quando o Chefe da fase atual chega a **0 HP**.
- O scaling do encontro fica congelado por fase; nova fase não restaura vida perdida.
- Todos os seis Eventos estão marcados como **Sintonizado: Sim**.
- Reentrada após derrota segue a regra global de 2 minutos quando autorizada pelo conteúdo.
- Participação e contribuição continuam vinculadas à `occurrence_id + character_id`.

## Fechamento de combate para implementação

### Coeficientes de ação
Todos os multiplicadores seguem §49.6 do GDD e usam o ponto médio da faixa do tipo de ação:

| Tipo | Multiplicador |
|---|---:|
| Simples | 100% ATQ |
| Forte | 132,5% ATQ |
| Preparada / telegráfica | 170% ATQ |
| AoE | 82,5% ATQ |
| Multi-hit | 130% ATQ total |
| DoT / híbrida | 85% ATQ |
| Barreira | 80% ATQ |
| Cura | 65% ATQ |

Nenhuma ação destes dois catálogos usa valores fora das faixas do GDD. O arredondamento dos atributos do inimigo continua sendo o da Fonte Mestra; estes valores são apenas os coeficientes das Artes.

### IA
A IA é **server-authoritative, determinística e sem RNG**. A ordem declarada nas fichas é a prioridade de conteúdo. Em toda oportunidade:

1. resolver Ação Preparada pendente e apta;
2. avaliar as prioridades da ficha, de cima para baixo;
3. executar a primeira ação especial válida e fora de Recarga;
4. usar a ação Simples como fallback.

`CD` usa a regra global de §10.2: uma ação usada no T1 com CD2 fica indisponível no T2 e retorna no T3. Condições táticas de preparação não são reavaliadas para cancelar uma Ação Preparada já comprometida.

### Alvos
- Ação de alvo único: menor HP atual entre os alvos válidos, salvo quando a condição da ação exige um efeito ausente; nesse caso, priorizar o menor HP entre alvos que ainda não possuem o efeito.
- AoE: todos os alvos válidos.
- Barreira: próprio inimigo.
- Em ações com condição "sem efeito relevante", não repetir o efeito apenas para renovar uma duração já relevante.

### Efeitos
Os DoTs usam exatamente as regras globais do GDD: Veneno `3T`, Sangramento `2T`, Queimadura `2T`; cap e stacking seguem §10.4. Debuffs numéricos indicados nas fichas têm a duração publicada na própria ação.

Não há Stun, silêncio, medo, confusão ou outro Hard CC nestes catálogos.

### Variante Ágil nos casos específicos

- `O Cortador de Marcos` — Predador + Variante Ágil.
- `O Passante de Duas Bordas` — Predador + Variante Ágil.
- Nenhuma dessas criaturas usa "Ágil" como arquétipo. O arquétipo continua sendo Predador.

---

## 1. O Cerco das Cinzas

**event_id:** `evt_tdo_cerco_das_cinzas`  
**Região:** Terras do Ocaso  
**Nível de referência:** 10  
**Sintonizado:** Sim

### Fase 1 — O Cortador de Marcos

**Categoria:** Chefe  
**Arquétipo:** Predador + Variante Ágil

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Quebra de Passagem | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Rasgo de Rota | forte | 132,5% ATQ | AGI −10% | 2T | CD2 | Alvo sem AGI−10% 2T |
| 3 | Passagem Lateral | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Corte de Marco | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Os primeiros sinais do cerco não são gritos. São marcos de estrada tombando um após o outro.

**Notas de design:**
- Variante aplicada somente aos atributos globais: `AGI +12% / HP −7%`. A Variante não altera a IA por si só.
- Sem Hard CC.


### Fase 2 — O Arrastador de Fornalha

**Categoria:** Chefe  
**Arquétipo:** Blindado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Investida de Fornalha | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Muralha de Cinza | barreira | 80% ATQ | Barreira própria | 2T | CD3 | HP próprio ≤60% e sem Barreira relevante ativa |
| 3 | Golpe Incandescente | forte | 132,5% ATQ | 1 Queimadura | 2T | CD2 | Alvo sem Queimadura ou abaixo do cap global |
| 4 | Arrasto de Fornalha | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> A estrada começa a escurecer quando o inimigo puxa uma fornalha ainda acesa para dentro da passagem.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 3 — O Quebrador do Último Marco

**Categoria:** Chefe  
**Arquétipo:** Bruto

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Investida Final | preparada | 170% ATQ | — | — | CD4 | HP próprio ≤40% e CD disponível; resolve na oportunidade seguinte |
| 2 | Golpe de Demolição | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 3 | Avanço de Cinzas | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Golpe do Último Marco | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O último marco cai. O que resta da estrada precisa ser defendido sem qualquer sinal para guiá-los.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


**Conclusão:**
> O cerco termina quando o último marco já não existe. A estrada permanece, mas agora depende de quem aprendeu a atravessá-la sem sinais para guiá-los.

---

## 2. A Raiz que Puxa

**event_id:** `evt_vales_raiz_que_puxa`  
**Região:** Vales dos Enforcados  
**Nível de referência:** 20  
**Sintonizado:** Sim

### Fase 1 — O Escavador de Laços

**Categoria:** Chefe  
**Arquétipo:** Equilibrado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Mergulho de Laço | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Puxão de Raiz | forte | 132,5% ATQ | AGI −10% | 2T | CD3 | Alvo sem AGI−10% 2T |
| 3 | Rasgo de Solo | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Escavação de Laço | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> A terra se move antes que qualquer coisa apareça. Quando a primeira raiz rompe a superfície, alguém já foi marcado.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 2 — O Trançador de Ossos

**Categoria:** Chefe  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Aprisionamento Preparado | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Trança de Ossos | DoT/híbrida | 85% ATQ | 1 Sangramento | 2T | CD2 | Alvo abaixo do cap de Sangramento |
| 3 | Nó Imóvel | forte | 132,5% ATQ | AGI −15% | 2T | CD3 | Alvo sem AGI−15% 2T |
| 4 | Arrasto Cruzado | AoE | 82,5% ATQ | DEF −10% | 2T | CD3 | 2+ alvos válidos sem DEF−10% 2T |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> As raízes não crescem sozinhas. Algo está usando restos antigos para dar forma ao que prende os vivos.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 3 — O Nó que Caminha

**Categoria:** Chefe  
**Arquétipo:** Bruto

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Quebra de Raiz | preparada | 170% ATQ | — | — | CD4 | HP próprio ≤40% e CD disponível; resolve na oportunidade seguinte |
| 2 | Aperto Convergente | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 3 | Arrasto Coletivo | AoE | 82,5% ATQ | AGI −10% | 2T | CD3 | 2+ alvos válidos sem AGI−10% 2T |
| 4 | Passo do Nó | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O emaranhado deixa de estar preso ao chão e começa a caminhar em direção ao grupo.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


**Conclusão:**
> Quando o nó se desfaz, as raízes permanecem. O vale não ficou mais seguro; apenas voltou a lembrar que ainda tem chão.

---

## 3. O Campo que Não Devolve

**event_id:** `evt_nareth_campo_que_nao_devolve`  
**Região:** Planícies de Nareth  
**Nível de referência:** 30  
**Sintonizado:** Sim

### Fase 1 — O Contador de Passagens

**Categoria:** Chefe  
**Arquétipo:** Equilibrado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Retorno ao Ponto | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Registro de Alvo | forte | 132,5% ATQ | PER −10 p.p. | 2T | CD3 | Alvo sem PER−10 p.p. 2T |
| 3 | Correção de Rota | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Contagem de Passagem | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O inimigo não ataca primeiro. Ele observa cada passagem e parece registrar quem já cruzou o campo.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 2 — O Recolhedor Vazio

**Categoria:** Chefe  
**Arquétipo:** Blindado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Retenção de Passagem | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Caixa Vazia | barreira | 80% ATQ | Barreira própria | 2T | CD3 | HP próprio ≤60% e sem Barreira relevante ativa |
| 3 | Avanço Pesado | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 4 | Recolha de Vestígio | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Objetos deixados no campo desaparecem quando chegam perto dele. Não há sinal do que acontece depois.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 3 — O Lavrador de Ausências

**Categoria:** Chefe  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Repetição de Caminho | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Sulco de Ausência | forte | 132,5% ATQ | AGI −10% | 2T | CD3 | Alvo sem AGI−10% 2T |
| 3 | Campo Negado | AoE | 82,5% ATQ | PER −10 p.p. | 2T | CD3 | 2+ alvos válidos sem PER−10 p.p. 2T |
| 4 | Sinal de Sulco | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> As marcas no chão formam linhas onde ninguém deveria ter passado.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


**Conclusão:**
> O campo não devolve o que toma. A única certeza é que algumas passagens continuam sendo registradas.

---

## 4. A Água Vermelha

**event_id:** `evt_varzeas_agua_vermelha`  
**Região:** Várzeas Carmesins  
**Nível de referência:** 40  
**Sintonizado:** Sim

### Fase 1 — O Carregador de Reservas

**Categoria:** Chefe  
**Arquétipo:** Equilibrado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Sobrecarga do Reservatório | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Descarga Controlada | forte | 132,5% ATQ | 1 Queimadura | 2T | CD2 | Alvo sem Queimadura ou abaixo do cap global |
| 3 | Avanço de Tanque | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Transporte de Reserva | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> A água sobe entre estruturas antigas enquanto alguma coisa transporta recipientes que ainda não deveriam estar cheios.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 2 — O Operador de Membranas

**Categoria:** Chefe  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Ruptura de Conduto | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Vedação Local | barreira | 80% ATQ | Barreira própria | 2T | CD3 | HP próprio ≤60% e sem Barreira relevante ativa |
| 3 | Pressão de Membrana | forte | 132,5% ATQ | ATQ −10% | 2T | CD3 | Alvo sem ATQ−10% 2T |
| 4 | Golpe de Membrana | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O operador não parece lutar contra o grupo. Parece tentar manter uma instalação funcionando apesar dele.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 3 — O Triador de Emergência

**Categoria:** Chefe  
**Arquétipo:** Bruto

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Sobrecarga Final | preparada | 170% ATQ | — | — | CD4 | HP próprio ≤40% e CD disponível; resolve na oportunidade seguinte |
| 2 | Desvio de Emergência | forte | 132,5% ATQ | Cura recebida −15% | 2T | CD3 | Alvo sem redução de Cura recebida 2T |
| 3 | Colisão de Contenção | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Triagem Brutal | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> A estrutura não distingue aliado de ameaça. Ela apenas continua decidindo o que pode ser preservado.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


**Conclusão:**
> A água baixa. Os diques permanecem. O que foi separado para sobreviver à emergência nunca volta ao mesmo lugar.

---

## 5. O Peso que Cede

**event_id:** `evt_altos_peso_que_cede`  
**Região:** Altos Cinéreos  
**Nível de referência:** 50  
**Sintonizado:** Sim

### Fase 1 — O Rachador de Tirantes

**Categoria:** Chefe  
**Arquétipo:** Bruto

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Queda de Escarpa | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Pancada de Contraforte | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 3 | Ruptura de Cabo | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Corte de Tirante | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Uma estrutura acima da estrada range. O inimigo começa pelo que parece suportá-la.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 2 — O Distribuidor de Peso

**Categoria:** Chefe  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Compensação de Estrutura | barreira | 80% ATQ | Barreira própria | 2T | CD3 | HP próprio ≤60% e sem Barreira relevante ativa |
| 2 | Pressão Cruzada | forte | 132,5% ATQ | ATQ −10% | 2T | CD3 | Alvo sem ATQ−10% 2T |
| 3 | Desvio de Peso | AoE | 82,5% ATQ | AGI −10% | 2T | CD3 | 2+ alvos válidos sem AGI−10% 2T |
| 4 | Redistribuição de Carga | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O problema deixa de ser derrubar a ponte e passa a ser descobrir qual parte ainda merece ser sustentada.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 3 — O Sustentador Partido

**Categoria:** Chefe  
**Arquétipo:** Blindado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Queda Contida | preparada | 170% ATQ | — | — | CD4 | HP próprio ≤40% e CD disponível; resolve na oportunidade seguinte |
| 2 | Reforço de Emergência | barreira | 80% ATQ | Barreira própria | 2T | CD3 | HP próprio ≤60% e sem Barreira relevante ativa |
| 3 | Carga Invertida | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 4 | Guarda do Contraforte | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> A criatura foi feita para sustentar. Agora tenta sustentar a própria ruína.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


**Conclusão:**
> O peso não desaparece. Ele apenas deixa de cair sobre a mesma estrutura.

---

## 6. Duas Estradas para o Mesmo Lugar

**event_id:** `evt_confins_duas_estradas`  
**Região:** Confins do Véu  
**Nível de referência:** 60  
**Sintonizado:** Sim

### Fase 1 — O Passante de Duas Bordas

**Categoria:** Chefe  
**Arquétipo:** Predador + Variante Ágil

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Salto entre Bordas | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Travessia Cruzada | forte | 132,5% ATQ | AGI −10% | 2T | CD2 | Alvo sem AGI−10% 2T |
| 3 | Dupla Margem | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Passagem de Borda | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> A primeira estrada termina no mesmo ponto em que a segunda começa. Ninguém lembra quando as duas deixaram de ser diferentes.

**Notas de design:**
- Variante aplicada somente aos atributos globais: `AGI +12% / HP −7%`. A Variante não altera a IA por si só.
- Sem Hard CC.


### Fase 2 — O Escrivão Desfasado

**Categoria:** Chefe  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Reescrita Final | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Rasura de Linha | forte | 132,5% ATQ | PER −10 p.p. | 2T | CD3 | Alvo sem PER−10 p.p. 2T |
| 3 | Página Desfasada | AoE | 82,5% ATQ | ATQ −10% | 2T | CD3 | 2+ alvos válidos sem ATQ−10% 2T |
| 4 | Registro Incompleto | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O registro muda enquanto é lido. A tinta parece obedecer a uma ordem que nunca foi a mesma.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


### Fase 3 — O Retornador Incompleto

**Categoria:** Chefe  
**Arquétipo:** Equilibrado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Retorno sem Chegada | preparada | 170% ATQ | — | — | CD4 | HP próprio ≤40% e CD disponível; resolve na oportunidade seguinte |
| 2 | Passo Repetido | forte | 132,5% ATQ | AGI −10% | 2T | CD3 | Alvo sem AGI−10% 2T |
| 3 | Reaparição | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Retorno Incompleto | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Algo retorna sem ter terminado de partir. A repetição é pequena demais para ser chamada de milagre.

**Notas de design:**
- Arquétipo único. Nenhum pacote duplo de atributos.
- Sem Hard CC.


**Conclusão:**
> As duas estradas continuam visíveis. O problema é que ambas chegam ao mesmo lugar sem explicar por quê.

---

## Registro de decisões desta revisão

- Arquétipos oficiais: somente Equilibrado, Bruto, Predador, Blindado, Conjurador e Controlador.
- Perfis duplos não existem no código; nenhum Evento Público desta revisão usa perfil duplo.
- Nível mínimo de entrada dos Eventos foi removido por não ser regra estabelecida pelo GDD.
- Valores das ações foram fechados pelo ponto médio das faixas de §49.6.

### Fonte de autoridade

- `ASTERION_GDD_Estrutural_v1_6_0.md` — Eventos Mundiais, Sintonização, IA PvE, efeitos/DoTs e coeficientes de Artes inimigas.
- `ASTERION_BIBLIA_CANONICA_v4_0_7.md` — escopo de canon e proteção de revelações.
- `ASTERION_BESTIARIO_CANONICO_VISUAL_v2_1_3.md` — apenas para garantir que estas criaturas não sejam reutilizações do Bestiário.

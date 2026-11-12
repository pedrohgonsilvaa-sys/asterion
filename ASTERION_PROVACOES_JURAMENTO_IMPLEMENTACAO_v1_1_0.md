# Asterion — Provações do Juramento
## Catálogo consolidado — versão de implementação

> Todas as criaturas são novas e exclusivas das Provações do Juramento. Nenhuma reutiliza ficha do Bestiário canônico.
> Juramento é conteúdo **de Guilda**, distinto de Evento Público.

## Regras estruturais do catálogo

- Cada Provação usa um `attempt_id` próprio e registra `guild_id + cycle_id`.
- A estrutura é fixa: **Elite → Elite → Chefe**.
- A vida do grupo e dos inimigos **persiste entre os três combates** da mesma Provação.
- A Configuração de Combate fica travada durante toda a tentativa.
- Ao resolver a Provação, o lock é liberado para uma tentativa futura.
- Cada Provação começa com HP cheio, Recargas prontas e sem efeitos residuais.
- A contribuição do Juramento é objetiva e idempotente; dano isolado não substitui os marcos de conteúdo.

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

### Perfis resolvidos nesta revisão

- Provação 2 · Combate 3: **Blindado**.
- Provação 3 · Combate 3: **Controlador**.
- Provação 4 · Combate 2: **Controlador**.
- Provação 5 · Combate 3: **Bruto**.
- Provação 6 · Combate 3: **Equilibrado**.
- Provação 3 · Combate 1: **Predador + Variante Ágil**.

---

## 1. O Juramento da Última Guarda

**trial_id:** `oath.ultima_guarda`

### Combate 1 — O Sentinela do Portão

**Categoria:** Elite  
**Arquétipo:** Blindado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Ordem de Permanência | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Guarda do Portão | barreira | 80% ATQ | Barreira própria | 2T | CD3 | HP próprio ≤60% e sem Barreira relevante ativa |
| 3 | Golpe de Contenção | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 4 | Travar Passagem | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O portão não precisa ser forte. Precisa apenas encontrar alguém disposto a permanecer diante dele.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 2 — A Guarda sem Relevo

**Categoria:** Elite  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Chamado do Revezamento | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Interdição | forte | 132,5% ATQ | AGI −10% | 2T | CD3 | Alvo sem AGI−10% 2T |
| 3 | Linha de Vigília | AoE | 82,5% ATQ | ATQ −10% | 2T | CD3 | 2+ alvos válidos sem ATQ−10% 2T |
| 4 | Marcar o Chão | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O primeiro guardava uma porta. O segundo guardava o espaço entre vocês.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 3 — O Último que Fica

**Categoria:** Chefe  
**Arquétipo:** Bruto

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Fim da Vigília | preparada | 170% ATQ | — | — | CD5 | HP próprio ≤35% e CD disponível; resolve na oportunidade seguinte |
| 2 | Não Recuarei | barreira | 80% ATQ | Barreira própria | 2T | CD4 | HP próprio ≤50% e sem Barreira relevante ativa |
| 3 | Avançar sem Alívio | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 4 | Golpe da Sentinela | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 5 | Última Guarda | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Quando o último guardião caiu, não havia nada atrás dele. Talvez esse tenha sido o motivo de ele ter permanecido.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


**Conclusão narrativa:**
> O Juramento continua depois que a testemunha desaparece.

---

## 2. O Juramento do Peso Compartilhado

**trial_id:** `oath.peso_compartilhado`

### Combate 1 — O Carregador Partido

**Categoria:** Elite  
**Arquétipo:** Bruto

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Retomar a Carga | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Arrasto | forte | 132,5% ATQ | AGI −10% | 2T | CD3 | Alvo sem AGI−10% 2T |
| 3 | Soltar o Peso | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Impacto de Carga | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Ele não parecia forte. Parecia acostumado.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 2 — A Distribuidora

**Categoria:** Elite  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Compensação | barreira | 80% ATQ | Barreira própria | 2T | CD3 | HP próprio ≤60% e sem Barreira relevante ativa |
| 2 | Carga Cruzada | forte | 132,5% ATQ | ATQ −10% | 2T | CD3 | Alvo sem ATQ−10% 2T |
| 3 | Equilíbrio Forçado | AoE | 82,5% ATQ | DEF −10% | 2T | CD3 | 2+ alvos válidos sem DEF−10% 2T |
| 4 | Redistribuir Pressão | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O peso não aumentou. Vocês apenas começaram a percebê-lo.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 3 — O Peso que Permanece

**Categoria:** Chefe  
**Arquétipo:** Blindado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Tudo Cai | preparada | 170% ATQ | — | — | CD5 | HP próprio ≤35% e CD disponível; resolve na oportunidade seguinte |
| 2 | Contrapeso | barreira | 80% ATQ | Barreira própria | 2T | CD4 | HP próprio ≤60% e sem Barreira relevante ativa |
| 3 | Peso Repartido | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 4 | Sobrecarga | AoE | 82,5% ATQ | ATQ −10% | 2T | CD3 | 2+ alvos válidos sem ATQ−10% 2T |
| 5 | Carga Total | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Quando o peso desapareceu, ninguém comemorou. Todos perceberam quanto tempo haviam confundido carregar com suportar.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


**Conclusão narrativa:**
> Algumas cargas só deixam de ser fardos quando deixam de pertencer a uma pessoa só.

---

## 3. O Juramento da Linha Rompida

**trial_id:** `oath.linha_rompida`

### Combate 1 — O Que Abre a Linha

**Categoria:** Elite  
**Arquétipo:** Predador + Variante Ágil

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Retorno Imediato | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Passagem Forçada | forte | 132,5% ATQ | AGI −10% | 2T | CD2 | Alvo sem AGI−10% 2T |
| 3 | Pressão Lateral | AoE | 82,5% ATQ | — | — | CD3 | 2+ alvos válidos |
| 4 | Rasgo de Formação | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Não foi o primeiro golpe que separou a linha. Foi o segundo passo.

- Sem Hard CC.
- Variante: `AGI +12% / HP −7%`; não altera a prioridade de IA.


### Combate 2 — Aquele que Explora a Falha

**Categoria:** Elite  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Fechar o Cerco | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Aproveitar Abertura | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 3 | Cortar Retorno | AoE | 82,5% ATQ | AGI −10% | 2T | CD3 | 2+ alvos válidos sem AGI−10% 2T |
| 4 | Fissura Marcada | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O segundo não precisava abrir a linha. Só precisava esperar.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 3 — O Rompedor de Formação

**Categoria:** Chefe  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Linha Quebrada | preparada | 170% ATQ | — | — | CD5 | HP próprio ≤35% e CD disponível; resolve na oportunidade seguinte |
| 2 | Linha Fixa | barreira | 80% ATQ | Barreira própria | 2T | CD4 | HP próprio ≤50% e sem Barreira relevante ativa |
| 3 | Deslocamento Brutal | forte | 132,5% ATQ | ATQ −10% | 2T | CD3 | Alvo sem ATQ−10% 2T |
| 4 | Quebra de Eixo | AoE | 82,5% ATQ | DEF −10% | 2T | CD3 | 2+ alvos válidos sem DEF−10% 2T |
| 5 | Fratura Central | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Uma linha pode ser quebrada sem que ninguém desapareça. O Juramento existe para decidir o que acontece depois.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


**Conclusão narrativa:**
> Permanecer unido nunca significou permanecer imóvel.

---

## 4. O Juramento do Nome Mantido

**trial_id:** `oath.nome_mantido`

### Combate 1 — O Esquecedor de Marcas

**Categoria:** Elite  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Repetição sem Origem | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Nome Vazio | forte | 132,5% ATQ | PER −10 p.p. | 2T | CD3 | Alvo sem PER−10 p.p. 2T |
| 3 | Rasura | AoE | 82,5% ATQ | ATQ −10% | 2T | CD3 | 2+ alvos válidos sem ATQ−10% 2T |
| 4 | Apagar Marca | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O problema não era esquecer. Era começar a chamar outra coisa pelo mesmo nome.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 2 — O Reescritor

**Categoria:** Elite  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Correção Forçada | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Versão Anterior | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 3 | Contradição | AoE | 82,5% ATQ | PER −10 p.p. | 2T | CD3 | 2+ alvos válidos sem PER−10 p.p. 2T |
| 4 | Substituir Registro | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Primeiro apagaram a marca. Depois ofereceram outra no lugar.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 3 — O Nome que Não Cede

**Categoria:** Chefe  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | O Que Permanece | preparada | 170% ATQ | — | — | CD5 | HP próprio ≤35% e CD disponível; resolve na oportunidade seguinte |
| 2 | Sem Segundo Nome | barreira | 80% ATQ | Barreira própria | 2T | CD4 | HP próprio ≤50% e sem Barreira relevante ativa |
| 3 | Recusar a Substituição | forte | 132,5% ATQ | PER −10 p.p. | 2T | CD3 | Alvo sem PER−10 p.p. 2T |
| 4 | Marca Persistente | AoE | 82,5% ATQ | AGI −10% | 2T | CD3 | 2+ alvos válidos sem AGI−10% 2T |
| 5 | Nomear o Erro | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O Nome não foi recuperado. Foi mantido. E talvez essa diferença seja o que um Juramento realmente exige.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


**Conclusão narrativa:**
> Um compromisso permanece quando a memória já não oferece uma resposta fácil.

---

## 5. O Juramento do Preço

**trial_id:** `oath.preco`

### Combate 1 — O Cobrador

**Categoria:** Elite  
**Arquétipo:** Equilibrado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Saldo Aberto | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Juros | forte | 132,5% ATQ | ATQ −10% | 2T | CD3 | Alvo sem ATQ−10% 2T |
| 3 | Retenção | AoE | 82,5% ATQ | AGI −10% | 2T | CD3 | 2+ alvos válidos sem AGI−10% 2T |
| 4 | Cobrança | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O preço nunca foi alto. Apenas nunca foi zero.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 2 — O Penhorista

**Categoria:** Elite  
**Arquétipo:** Controlador

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Oferta Recusada | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Tomar em Garantia | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 3 | Devolver com Custo | AoE | 82,5% ATQ | Cura recebida −15% | 2T | CD3 | 2+ alvos válidos sem redução de Cura recebida 2T |
| 4 | Penhor | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Quando tudo tem preço, a dificuldade deixa de ser pagar. É decidir o que vale ser preservado.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 3 — O Credor do Fim

**Categoria:** Chefe  
**Arquétipo:** Bruto

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Preço Final | preparada | 170% ATQ | — | — | CD5 | HP próprio ≤35% e CD disponível; resolve na oportunidade seguinte |
| 2 | Sem Troco | forte | 132,5% ATQ | ATQ −10% | 2T | CD3 | Alvo sem ATQ−10% 2T |
| 3 | Cobrança Fracionada | multi-hit | 2×65% ATQ (130% total) | — | — | CD3 | Sempre que válida |
| 4 | Conta Fechada | AoE | 82,5% ATQ | Cura recebida −15% | 2T | CD3 | 2+ alvos válidos sem redução de Cura recebida 2T |
| 5 | Cobrar Tudo | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> O preço não estava escondido. Ele estava em cada escolha que vocês fizeram antes de chegar aqui.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


**Conclusão narrativa:**
> Toda decisão deixa uma marca. O Juramento apenas impede que vocês finjam que ela não existe.

---

## 6. O Juramento que Permanece

**trial_id:** `oath.que_permanece`

### Combate 1 — O Persistente

**Categoria:** Elite  
**Arquétipo:** Blindado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Passo Inevitável | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Guarda Desgastada | barreira | 80% ATQ | Barreira própria | 2T | CD3 | HP próprio ≤60% e sem Barreira relevante ativa |
| 3 | Reerguer-se | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 4 | Persistir | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Ele não precisava acreditar. Só precisava continuar.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 2 — O Último Fiel

**Categoria:** Elite  
**Arquétipo:** Equilibrado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Continuar Mesmo Assim | preparada | 170% ATQ | — | — | CD4 | Preparar quando CD disponível; resolve na oportunidade seguinte |
| 2 | Resposta Fiel | forte | 132,5% ATQ | ATQ −10% | 2T | CD3 | Alvo sem ATQ−10% 2T |
| 3 | Sem Atalho | AoE | 82,5% ATQ | AGI −10% | 2T | CD3 | 2+ alvos válidos sem AGI−10% 2T |
| 4 | Retomar Posição | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Continuar não significava fazer a mesma coisa. Significava não abandonar o propósito.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


### Combate 3 — O Juramento que Permanece

**Categoria:** Chefe  
**Arquétipo:** Equilibrado

**Ações e prioridade de IA:**

| Prioridade | Ação | Tipo | Valor | Efeito | Duração | CD | Condição |
|---:|---|---|---:|---|---:|---:|---|
| 1 | Ainda de Pé | preparada | 170% ATQ | — | — | CD5 | HP próprio ≤35% e CD disponível; resolve na oportunidade seguinte |
| 2 | Recusar a Queda | barreira | 80% ATQ | Barreira própria | 2T | CD4 | HP próprio ≤50% e sem Barreira relevante ativa |
| 3 | Resposta ao Propósito | forte | 132,5% ATQ | DEF −10% | 2T | CD3 | Alvo sem DEF−10% 2T |
| 4 | Sem Recomeço | AoE | 82,5% ATQ | ATQ −10% | 2T | CD3 | 2+ alvos válidos sem ATQ−10% 2T |
| 5 | Permanecer | simples | 100% ATQ | — | — | — | Sempre que válida |

**IA fechada:** Ação Preparada pendente resolve primeiro. Depois, seguir a ordem da tabela; a ação Simples permanece como fallback quando nenhuma especial estiver válida.

> Um Juramento não prova seu valor quando tudo dá certo. Prova quando ainda existe alguém disposto a cumpri-lo depois que o motivo mais fácil para continuar desapareceu.

- Sem Hard CC.
- Arquétipo único; nenhuma combinação dupla de perfis é usada.


**Conclusão narrativa:**
> O compromisso não terminou. Só perdeu a justificativa mais fácil.

---

## Registro de decisões desta revisão

- Estrutura fixa: Elite → Elite → Chefe.
- Perfis duplos foram resolvidos para um único arquétipo no código.
- `Ágil` foi tratado apenas como Variante de Predador onde necessário.
- Os valores das ações usam o ponto médio das faixas de §49.6.
- A Provação não ganha revelação cosmológica nova; o tom permanece contido, melancólico e temático.

### Fonte de autoridade

- `ASTERION_GDD_Estrutural_v1_6_0.md` — Juramento, locks, IA PvE, efeitos/DoTs e coeficientes de Artes inimigas.
- `ASTERION_BIBLIA_CANONICA_v4_0_7.md` — canon e locks de revelação.
- `ASTERION_BESTIARIO_CANONICO_VISUAL_v2_1_3.md` — verificação de exclusividade das criaturas.

# ASTERION — Contratos Regionais
## Decisões de Design e Balanceamento — Fechamento Canônico

**Status:** FECHADO  
**Versão:** 1.0.0  
**Data:** 2026-11-13  
**Escopo:** decisões finais para habilitação/ajuste do sistema de Contratos Regionais.

---

## 1. Status final

Não há mais decisão de design pendente identificada para esta feature com base no material canônico revisado.

As decisões abaixo foram aprovadas integralmente e devem ser tratadas como referência para a implementação final.

> **Regra de precedência:** este documento consolida as decisões tomadas nesta revisão. Ele não substitui as regras gerais do GDD nem o conteúdo canônico das regiões; serve como fechamento específico dos Contratos Regionais.

---

## 2. Estrutura dos contratos

### 2.1 Tipos ativos

Os contratos regionais ativos são:

- **Caça**
- **Coleta**
- **Entrega**
- **Investigação**

**Escolta** permanece desabilitada.

### 2.2 Quantidades padrão

A variação entre contratos deve ocorrer principalmente pelo **alvo**, e não por quantidades arbitrárias.

| Tipo | Alvo | Quantidade/regra |
|---|---|---|
| Caça | Criatura específica | 1 vitória |
| Coleta | Material específico | 3 unidades |
| Entrega | Destino específico | Chegar ao destino e confirmar |
| Investigação | Local/ponto específico | Chegar ao local e confirmar |

Os 36 contratos permanecem fixos: **6 por região, R1–R6**.

---

## 3. Caça

### 3.1 Alvo individual

Cada contrato de Caça pode especificar uma criatura individual como alvo.

A seleção específica do alvo é uma exceção de conteúdo do contrato e não altera a regra geral da Caçada Manual: o contrato pode exigir a criatura determinada pelo conteúdo.

### 3.2 Progresso válido

Conta somente:

- **Caçada Manual**
- **Solo**
- **Vitória efetiva**

Não conta:

- Ronda de Caça
- Caça em Grupo
- outras fontes que não representem a vitória Manual Solo exigida pelo contrato.

### 3.3 Quantidade

Padrão: **1 vitória**.

---

## 4. Coleta

### 4.1 Alvo individual

Cada contrato de Coleta especifica um Material determinado.

### 4.2 Quantidade

Padrão: **3 unidades** do Material-alvo.

### 4.3 Regra de contagem

O contrato deve contar Materiais recebidos por fontes legítimas do jogo, desde que:

1. o Material tenha sido recebido **depois da aceitação/ativação do contrato**;
2. seja o Material exigido pelo contrato;
3. não seja o próprio Material concedido como recompensa pelo contrato.

Fontes legítimas de obtenção podem contar normalmente.

### 4.4 Exclusões

Não devem completar o contrato:

- Materiais que já estavam no inventário antes da ativação;
- o próprio prêmio do contrato;
- transferência entre jogadores;
- comércio/troca que permita contornar a progressão normal de obtenção.

Essa trava evita que o jogador conclua instantaneamente um contrato usando estoque pré-existente ou transferência artificial.

---

## 5. Entrega

### 5.1 Objetivo

O contrato especifica um destino.

### 5.2 Interação

Manter o fluxo mínimo já adotado pelo sistema:

**CONTINUAR**

Ao estar no local correto, o jogador usa a confirmação para concluir a etapa.

Não criar uma falsa mecânica de "entregar item" enquanto o jogo não possuir uma ação nativa correspondente.

### 5.3 Quantidade

Uma entrega por contrato.

---

## 6. Investigação

### 6.1 Objetivo

O contrato especifica um Local/ponto de investigação.

### 6.2 Interação

Manter o fluxo:

**CONTINUAR**

Se o personagem estiver no local correto, a ação confirma a investigação.

Não inventar uma ação de "examinar" separada apenas para os contratos.

### 6.3 Quantidade

Uma investigação por contrato.

---

## 7. Recompensas de Material

### 7.1 Regra regional

Para **Caça, Entrega e Investigação**, a recompensa de Material segue a regra simples:

> **primeiro Basic Material da respectiva região.**

Para **Coleta**, a recompensa de Material é o próprio Material-alvo definido pelo contrato.

### 7.2 Materiais vinculados

Os Materiais concedidos pelos Contratos Regionais são:

> **VINCULADOS AO PERSONAGEM**

A regra segue o tratamento adotado para Materiais de Missão.

### 7.3 Mapeamentos canônicos aprovados

Dois nomes do catálogo não correspondem exatamente a um Material existente no jogo. Os seguintes mapeamentos ficam aprovados:

| Contrato/catálogo | Material usado |
|---|---|
| **CON_TDO_02 — Ferro da Estrada** | **Ferro de Fuligem** |
| **CON_PDN_02 — Coleta das Planícies** | **Bronze de Marco** |

---

## 8. XP e Coroas

### 8.1 Problema identificado

Os pagamentos provisórios apresentavam escala desigual em relação aos ganhos normais do personagem:

- regiões iniciais: aproximadamente **12–21%**;
- regiões finais: aproximadamente **31–48%**.

Isso fazia os contratos das regiões avançadas pagarem proporcionalmente mais.

### 8.2 Regra final

Normalizar **XP e Coroas** dos contratos para um alvo aproximado de:

> **25% do ganho normal de referência**

Faixa prática aceitável:

> **20–30%**

O objetivo é manter os contratos relevantes sem transformá-los em uma fonte econômica desproporcional nas regiões avançadas.

### 8.3 Natureza da alteração

Este item é **balanceamento**, não mudança estrutural do sistema.

---

## 9. Limite de recompensa / frequência

### 9.1 Decisão

**Não adicionar um limite diário extra.**

Manter:

- até **3 contratos simultâneos**;
- renovação de contratos a cada **24h**.

Esses mecanismos são considerados o limitador explícito de recompensa/frequência para esta atividade.

Não criar, neste fechamento:

- limite diário adicional de contratos concluídos;
- cooldown extra;
- gasto de Vigor adicional;
- cap paralelo de recompensas.

---

## 10. Resumo executivo para implementação

### Aprovado

- [x] Alvos individuais por contrato.
- [x] Quantidades padrão por tipo.
- [x] `CONTINUAR` para Entrega.
- [x] `CONTINUAR` para Investigação.
- [x] Primeiro Basic Material regional para Caça/Entrega/Investigação.
- [x] Material-alvo como recompensa de Coleta.
- [x] `Ferro da Estrada` → `Ferro de Fuligem`.
- [x] `Coleta das Planícies` → `Bronze de Marco`.
- [x] Caça conta apenas vitória Manual Solo.
- [x] Coleta conta ganhos legítimos posteriores à ativação.
- [x] Estoque pré-existente não conta.
- [x] Recompensa do próprio contrato não conta para progresso.
- [x] Transferência/comércio entre jogadores não conta para progresso.
- [x] Materiais de contrato são vinculados.
- [x] XP/Coroas normalizados para ~25%, com faixa prática de 20–30%.
- [x] Sem novo limite diário.
- [x] 3 contratos simultâneos.
- [x] Renovação em 24h.

---

## 11. Checklist de fechamento

Antes de habilitar a feature flag, validar no código:

1. Os 36 contratos estão usando os alvos definidos individualmente.
2. Caça registra apenas vitória Manual + Solo válida.
3. Coleta registra somente ganho posterior à ativação e exclui as fontes proibidas.
4. Entrega e Investigação concluem corretamente via `CONTINUAR`.
5. Recompensas de Material seguem as regras regionais.
6. Materiais de contrato estão vinculados.
7. Os dois mapeamentos de Material estão aplicados.
8. XP e Coroas foram recalibrados para a faixa de 20–30% do ganho de referência.
9. O limite operacional continua em 3 contratos simultâneos + renovação de 24h.
10. A feature flag pode ser habilitada após os testes funcionais e de balanceamento.

---

## 12. Conclusão

**CONTRATOS REGIONAIS — DECISÕES DE DESIGN: FECHADAS.**

Não há decisão adicional necessária neste momento.

O trabalho restante é de **implementação, ajuste dos valores de balanceamento e validação/testes**, não de definição de regra.

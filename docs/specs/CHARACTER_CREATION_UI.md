# Especificação player-facing — Criação de Personagem

> Extraída da Fonte Visual/UI consolidada de 2026-09-20 para implementação. Em conflito mecânico ou numérico, a Fonte Mestra v1.4.2 prevalece.

## 45. Criação de Personagem e Prólogo — fluxo consolidado

A Criação de Personagem segue o fluxo autoritativo:

**Nome → Gênero → Raça → Classe → Confirmação Final → Prólogo jogável “Cinzas na Estrada”.**

> Decisão Visual/UI consolidada em 2026-11-21: o fluxo usa títulos em **negrito**, flavor text em *itálico*, seleção por botões e retorno com **↩️ Voltar** nas telas de Gênero/Raça/Classe. A confirmação final mantém o layout já aprovado.

Regras gerais:

- `/start` sem personagem existente entra diretamente em **Nome do Personagem**.
- Existe 1 personagem por servidor por conta Telegram.
- Raça e Classe são permanentes no lançamento.
- Gênero é obrigatório e possui as opções Masculino e Feminino.
- Caminho não é escolhido na criação; os dois Caminhos futuros da Classe aparecem apenas no detalhe da Classe.
- Aparência não integra a criação inicial.
- Não usar tag de Guilda durante a criação ou prólogo.
- Não criar tela de “personagem criado com sucesso”; após a confirmação final, entrar diretamente no prólogo.

### 45.1 Nome do Personagem

```text
[Imagem contextual de Asterion]

👤 Nome do Personagem

Todo caminho começa com um nome. Escolha como seu personagem será conhecido em Asterion.

Envie no chat o nome desejado.
```

Apresentação:
- Título em **negrito**.
- Flavor em *itálico*.
- O jogador envia o nome diretamente no chat.
- Não criar botão de confirmação de nome.
- Nome válido e disponível avança diretamente para Gênero.

### 45.1b Gênero do Personagem

```text
🎭 Gênero do Personagem

Existe o rosto que o mundo vai reconhecer. Escolha como seu personagem se apresenta em Asterion.

[Masculino] [Feminino]

[↩️ Voltar]
```

- Título em **negrito**.
- Flavor em *itálico*.
- A escolha é feita em um toque.
- **↩️ Voltar** retorna ao Nome sem apagar as demais escolhas.

### 45.2 Raça do Personagem — lista

```text
🕯️ Raça do Personagem

Povos distintos sobreviveram às marcas deixadas sobre Asterion. Sua origem acompanhará permanentemente este personagem e influenciará, de forma sutil, a maneira como ele enfrenta os perigos do mundo.

[🕯️ Remanescente] [🌘 Velado]
[🌪️ Cinéreo] [🩸 Hemário]
[☀️ Alvorano]

[↩️ Voltar]
```

A lista **não** repete descrições como “Identidade Flexível”, “Efeitos e Resistência” ou equivalentes.

### 45.2.1 Detalhe de Raça

Estrutura canônica:

```text
🕯️ Remanescente

Entre os povos que persistiram após as grandes rupturas de Asterion, os Remanescentes aprenderam a sobreviver menos pela especialização e mais pela capacidade de se adaptar ao que o mundo exige.

🧩 Adaptabilidade · Passiva Racial

Os valores finais estáticos recebem +1,5% de HP Máximo, ATQ, DEF e AGI. A passiva não afeta PER, Crítico, Esquiva ou Bloqueio.

[🕯️ Escolher Remanescente]

[↩️ Voltar]
```

Regras:
- Título em **negrito**.
- Flavor da Raça em *itálico*.
- Não usar bloco **🧭 Para quem é**.
- A Passiva Racial aparece como um cabeçalho em **negrito** seguido de um **parágrafo único** com o efeito completo.
- Não transformar a passiva em quatro linhas soltas de atributo.

### 45.3 Classe do Personagem — lista

```text
⚔️ Classe do Personagem

Sua Classe define as bases do seu estilo de combate e os Caminhos que poderão ser despertados mais adiante. Escolha com cuidado: esta decisão acompanhará permanentemente o personagem.

[🛡️ Sentinela] [🗡️ Errante]
[🏹 Vigia] [🪄 Tecelão]
[🔮 Oráculo] [☀️ Luminar]

[↩️ Voltar]
```

A lista **não** mostra:
- descrições das Classes;
- os dois Caminhos de cada Classe;
- Artes de Classe;
- blocos de status.

### 45.3.1 Detalhe de Classe

Estrutura canônica:

```text
🛡️ Sentinela

Sentinelas avançam onde outros hesitam. Resistência, proteção e contra-ataques sustentam seu estilo de combate, permitindo suportar pressão enquanto criam oportunidades para devolver o impacto recebido.

🎭 Caminhos Futuros

🏰 Bastião
Especializa o Sentinela em HP, DEF, Barreiras e proteção do grupo.

💥 Devastador
Troca parte da resistência por ATQ e transforma dano recebido em oportunidades de contra-ataque mais fortes.

[🛡️ Escolher Sentinela]

[↩️ Voltar]
```

Regras:
- Título em **negrito**.
- Flavor da Classe em *itálico*.
- Não mostrar **🧭 Para quem é**.
- Não mostrar **🎴 Artes de Classe** nesta tela.
- Não mostrar lista de Artes.
- Não transformar a área de Caminhos Futuros em uma lista de Artes.
- Mostrar somente os dois Caminhos futuros com seus nomes e descrições.
- Os nomes dos Caminhos usam a iconografia canônica.

### 45.4 Confirmação Final

A confirmação final mantém o layout aprovado:

```text
📜 Confirmar Personagem

Seu nome foi escolhido, sua origem foi definida e sua vocação começa a tomar forma. Antes de seguir pela estrada, revise o que o mundo saberá sobre você. Ao confirmar, sua jornada por Asterion terá início.

🏷️ Nome · Luiken
🎭 Gênero · Masculino
🕯️ Raça · Remanescente
🧩 Adaptabilidade · Passiva Racial
🗡️ Classe · Errante

⚠️ Raça e Classe não poderão ser alteradas após a criação do personagem.

[✅ Confirmar Personagem]

[Nome] [Gênero]
[Raça] [Classe]

[← Classes]
```

Regras:
- Não mostrar tag de Guilda.
- Não repetir Caminhos Futuros na confirmação.
- Nome, Gênero, Raça e Classe permitem revisar a respectiva etapa sem apagar as demais escolhas válidas.
- Após confirmar, entrar diretamente no prólogo.

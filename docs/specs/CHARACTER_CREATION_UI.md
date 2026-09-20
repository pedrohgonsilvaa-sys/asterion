# Especificação player-facing — Criação de Personagem

> Extraída da Fonte Visual/UI consolidada de 2026-09-20 para implementação. Em conflito mecânico ou numérico, a Fonte Mestra v1.4.1 prevalece.

## 45. Criação de Personagem e Prólogo — fluxo consolidado

A Criação de Personagem segue o fluxo autoritativo da Fonte Mestra:

**Nome → Raça → Classe → Confirmação Final → Prólogo jogável “Cinzas na Estrada”.**

Regras gerais:

- `/start` sem personagem existente entra diretamente em **Nome do Personagem**; não criar uma tela intermediária `[Novo Personagem]` sem decisão real.
- Existe **1 personagem por servidor** por conta Telegram.
- Raça e Classe são permanentes no lançamento.
- Caminho não é escolhido na criação; os dois Caminhos futuros da Classe são apresentados apenas como informação e serão escolhidos depois da Provação.
- Aparência não integra a criação inicial; permanece em **Personagem → Cosméticos → Aparência**.
- Não usar tag de Guilda durante a criação ou prólogo; ela só existe depois de o personagem ingressar em uma Guilda.
- Não criar tela de “personagem criado com sucesso”; após a confirmação final, entrar diretamente no prólogo.

### 45.1 Nome do Personagem

Tela inicial:

```text
[Imagem contextual de Asterion]

🏷️ Nome do Personagem

Todo caminho começa com um nome. Escolha como seu personagem será conhecido entre aqueles que ainda percorrem as terras de Asterion.

ℹ️ 3–16 letras, A–Z, sem acentos, números, espaços ou símbolos. Envie no chat o nome desejado.
```

Regras visuais:

- O jogador envia o nome diretamente no chat; não criar `[Confirmar Nome]`.
- Nome válido e disponível avança diretamente para **Raça**.
- Ao editar o Nome a partir da Confirmação Final, um novo nome válido retorna à Confirmação Final sem apagar Raça ou Classe já escolhidas.

Erro de formato:

```text
🏷️ Nome do Personagem

⚠️ Nome inválido. Envie outro nome no chat. 3–16 letras, A–Z, sem acentos, números, espaços ou símbolos.
```

Nome que o sistema não aceita por unicidade, reserva, moderação ou regra equivalente:

```text
🏷️ Nome do Personagem

🚫 Luiken · Inválido

⚠️ Esse nome não pode ser utilizado. Escolha outro nome para continuar. Envie outro nome no chat.
```

### 45.2 Seleção de Raça

Lista:

```text
[Imagem contextual das Raças de Asterion]

🕯️ Raça

Povos distintos sobreviveram às marcas deixadas sobre Asterion. Sua origem acompanhará permanentemente este personagem e influenciará, de forma sutil, a maneira como ele enfrenta os perigos do mundo.

1 🕯️ Remanescente · Identidade Flexível
2 🌘 Velado · Efeitos e Resistência
3 🌪️ Cinéreo · Defesa
4 🩸 Hemário · Recuperação
5 🔆 Alvorano · Iniciativa

[1] [2] [3] [4] [5]

[← Nome]
```

A lista resume identidade. O detalhe de cada Raça precisa mostrar **o efeito racial completo**, porque a escolha é permanente.

#### 🕯️ Remanescente

```text
[Imagem contextual dos Remanescentes]

🕯️ Remanescente

Entre os povos que persistiram após as grandes rupturas de Asterion, os Remanescentes aprenderam a sobreviver menos pela especialização e mais pela capacidade de se adaptar ao que o mundo exige.

🧩 Adaptabilidade · Passiva Racial

❤️ HP Máximo · +1,5%
⚔️ ATQ · +1,5%
🛡️ DEF · +1,5%
💨 AGI · +1,5%

ℹ️ Os bônus são permanentes e se aplicam aos valores finais estáticos do personagem. Não afetam PER, Crítico, Esquiva ou Bloqueio.

[Escolher Remanescente]

[← Raças]
```

#### 🌘 Velado

```text
[Imagem contextual dos Velados]

🌘 Velado

Os Velados vivem próximos demais de forças que poucos conseguem perceber por inteiro. Aquilo que os fortalece tende a permanecer por mais tempo, enquanto efeitos hostis encontram dificuldade maior para se fixar.

🌫️ Eco do Véu · Passiva Racial

🟢 Buffs com 2T+ · 25% chance +1T
🔻 Debuffs com 2T+ · 25% chance −1T

ℹ️ A passiva só afeta Buffs e Debuffs elegíveis com duração base de 2 Turnos ou mais. Quando a redução de um Debuff é ativada, sua duração nunca pode cair abaixo de 1 Turno. Não afeta Barreira, Cura, DoT, Controle Rígido, marcas, recursos internos, efeitos imutáveis ou mecânicas fixas de Chefes e Masmorras.

[Escolher Velado]

[← Raças]
```

#### 🌪️ Cinéreo

```text
[Imagem contextual dos Cinéreos]

🌪️ Cinéreo

Forjados em regiões onde cinza, pedra e vento castigam sem descanso, os Cinéreos aprenderam que resistir ao impacto certo pode ser tão decisivo quanto desferi-lo.

🛡️ Tenacidade Cinérea · Passiva Racial

🛡️ Defender · 45% → 52%
🌌 Ruptura Final · 30% → 37%

ℹ️ A passiva aumenta em 7 pontos percentuais a redução de dano concedida por Defender. Durante a Ruptura Final, quando Defender normalmente cai para 30%, o Cinéreo ainda mantém 37%. O efeito não aumenta outras fontes de DEF, Bloqueio ou redução de dano.

[Escolher Cinéreo]

[← Raças]
```

#### 🩸 Hemário

```text
[Imagem contextual dos Hemários]

🩸 Hemário

Há algo antigo na vitalidade dos Hemários. Quando o corpo se aproxima do limite, essa herança desperta e transforma violência em sobrevivência.

🦇 Fome Hemária · Passiva Racial

❤️ Ativação · HP ≤ 40%
🩸 Vampirismo · +12%
❤️ Cura Máxima por Ação · 3% do HP Máximo

ℹ️ A passiva fica ativa enquanto o personagem estiver com 40% de HP ou menos e termina quando ele ultrapassa esse limite. O Vampirismo recupera HP apenas a partir de dano direto elegível e nunca pode curar mais de 3% do HP Máximo em uma única ação. Não é ativado por DoT, Reflexão, dano ambiental, dano causado apenas contra Barreira ou excesso de dano.

[Escolher Hemário]

[← Raças]
```

#### 🔆 Alvorano

```text
[Imagem contextual dos Alvoranos]

🔆 Alvorano

Nos Alvoranos, movimento e clareza parecem anteceder o perigo. Sua presença se revela na rapidez com que tomam a iniciativa e na dificuldade de enfraquecê-los por meios convencionais.

🌟 Primeiro Clarão · Passiva Racial

💨 AGI · +5%
🛡️ Debuffs Numéricos · −12% de Magnitude

ℹ️ A passiva aumenta permanentemente a AGI do personagem e reduz em 12% a intensidade de Debuffs numéricos removíveis que o afetem. Não reduz a duração dos efeitos e não afeta DoT, Controle Rígido, Dano Direto, marcas, recursos internos ou mecânicas fixas.

[Escolher Alvorano]

[← Raças]
```

### 45.3 Seleção de Classe

Lista:

```text
[Imagem contextual das Classes de Asterion]

⚔️ Classe

Sua Classe define as bases do seu estilo de combate, suas Artes e os Caminhos que poderão ser despertados mais adiante. Escolha com cuidado: esta decisão acompanhará permanentemente o personagem.

1 🛡️ Sentinela
🏰 Bastião · Caminho
💥 Devastador · Caminho

2 🗡️ Errante
☠️ Carrasco · Caminho
🕷️ Sabotador · Caminho

3 🏹 Vigia
🎯 Atirador · Caminho
👣 Rastreador · Caminho

4 🪄 Tecelão
🌀 Conjurador · Caminho
🔷 Rúnico · Caminho

5 🔮 Oráculo
🦉 Agoureiro · Caminho
🐺 Invocador · Caminho

6 ☀️ Luminar
🪬 Guardião · Caminho
⚖️ Inquisidor · Caminho

[1] [2] [3]
[4] [5] [6]

[← Raças]
```

Os Caminhos aparecem apenas como informação sobre a evolução futura; não são escolhidos nesta etapa.

#### 🛡️ Sentinela

```text
[Imagem contextual do Sentinela]

🛡️ Sentinela

Sentinelas avançam onde outros hesitam. Resistência, proteção e contra-ataques sustentam seu estilo de combate, permitindo suportar pressão enquanto criam oportunidades para devolver o impacto recebido.

⚔️ Estilo de Luta · Resistência e Retaliação

❤️ HP · Muito Alto
🛡️ DEF · Muito Alta
⚔️ ATQ · Baixo
💨 AGI · Baixa

🎴 Artes de Classe

🗡️ Golpe de Guarda · Dano
🛡️ Quebra-Postura · Reduz DEF
🔰 Muralha Breve · Barreira
💥 Impacto Resoluto · Dano
🛡️ Firmeza · Aumenta DEF
⚔️ Golpe de Rechaço · Retaliação

🎭 Caminhos Futuros

🏰 Bastião · Proteção
Especializa o Sentinela em HP, DEF, Barreiras e proteção do grupo.

💥 Devastador · Pressão
Troca parte da resistência por ATQ e transforma dano recebido em oportunidades de contra-ataque mais fortes.

[Escolher Sentinela]

[← Classes]
```

#### 🗡️ Errante

```text
[Imagem contextual do Errante]

🗡️ Errante

Errantes sobrevivem pela velocidade, pela leitura de brechas e pela capacidade de transformar um instante de vantagem em pressão constante. Seu estilo favorece ataques rápidos, mobilidade e exploração de inimigos já enfraquecidos.

⚔️ Estilo de Luta · Mobilidade e Oportunismo

❤️ HP · Médio
🛡️ DEF · Baixa
⚔️ ATQ · Alto
💨 AGI · Muito Alta

🎴 Artes de Classe

🗡️ Corte Veloz · Dano
🩸 Ferida Profunda · Sangramento
💨 Passo Velado · Esquiva e Crítico
⚔️ Golpe Oportuno · Crítico
🗡️ Corte Duplo · Ataque Múltiplo
🎯 Brecha Mortal · Perfuração

🎭 Caminhos Futuros

☠️ Carrasco · Execução
Especializa o Errante em finalizar inimigos feridos, aumentando sua pressão contra alvos com HP baixo.

🕷️ Sabotador · Interferência
Especializa o Errante em efeitos negativos, controle de ritmo e exploração de alvos já debilitados.

[Escolher Errante]

[← Classes]
```

#### 🏹 Vigia

```text
[Imagem contextual do Vigia]

🏹 Vigia

Vigias observam antes de agir. Precisão, leitura do alvo e ataques calculados definem seu estilo de luta, permitindo explorar pontos fracos e transformar preparação em disparos cada vez mais perigosos.

⚔️ Estilo de Luta · Precisão e Mira

❤️ HP · Médio
🛡️ DEF · Média
⚔️ ATQ · Alto
💨 AGI · Alta

🎴 Artes de Classe

🏹 Disparo Preciso · Dano
🎯 Marca da Presa · Reduz DEF
🏹 Saraivada · Ataque Múltiplo
👁️ Olho da Vigília · PER e Crítico
🎯 Tiro Calculado · Mira e Crítico
🌧️ Voleio · Dano em Área

🎭 Caminhos Futuros

🎯 Atirador · Precisão
Concentra Mira sobre um único inimigo, acumulando Perfuração e Crítico para preparar disparos de alto impacto.

👣 Rastreador · Rastreamento
Distribui sua atenção entre vários inimigos, usando Sangramento, redução de AGI e rastros para manter pressão sobre múltiplos alvos.

[Escolher Vigia]

[← Classes]
```

#### 🪄 Tecelão

```text
[Imagem contextual do Tecelão]

🪄 Tecelão

Tecelões manipulam as tramas que atravessam o Véu, encadeando Artes para alterar o fluxo do combate. Seu poder recompensa variedade e sequência, transformando diferentes manifestações da trama em ataques, Barreiras e efeitos cada vez mais intensos.

⚔️ Estilo de Luta · Trama e Poder Arcano

❤️ HP · Baixo
🛡️ DEF · Baixa
⚔️ ATQ · Muito Alto
💨 AGI · Média

🎴 Artes de Classe

🪄 Fio Cortante · Dano
🔥 Chama Tecida · Queimadura
💥 Ruptura da Trama · Dano em Área
🔰 Véu Entrelaçado · Barreira
❄️ Geada Tecida · Reduz AGI
🌌 Surto do Véu · Dano

🎭 Caminhos Futuros

🌀 Conjurador · Ofensiva
Amplifica o potencial destrutivo da Trama, favorecendo dano elevado, ataques múltiplos e efeitos em área.

🔷 Rúnico · Proteção
Direciona a Trama para Runas, Barreiras e recuperação, oferecendo maior controle defensivo e suporte ao grupo.

[Escolher Tecelão]

[← Classes]
```

#### 🔮 Oráculo

```text
[Imagem contextual do Oráculo]

🔮 Oráculo

Oráculos leem sinais onde outros enxergam apenas acaso. Presságios, antecipação e manipulação do destino permitem enfraquecer inimigos, fortalecer aliados e preparar o combate antes que suas consequências se revelem por completo.

⚔️ Estilo de Luta · Presságios e Controle

❤️ HP · Médio
🛡️ DEF · Média
⚔️ ATQ · Médio
💨 AGI · Alta

🎴 Artes de Classe

🔮 Sinal Funesto · Dano e Reduz ATQ
👁️ Vislumbre · Aumenta AGI
🌑 Ruína Predita · Dano
🛡️ Véu Premonitório · Barreira e Resistência
✨ Augúrio Favorável · Aumenta ATQ
📜 Selo da Queda · Dano e Reduz DEF

🎭 Caminhos Futuros

🦉 Agoureiro · Presságio
Especializa o Oráculo em previsões ofensivas, enfraquecimento e exploração de Presságios para tornar suas Artes mais perigosas.

🐺 Invocador · Manifestações
Canaliza as manifestações de Lobo, Coruja e Urso para alternar entre dano, enfraquecimento e proteção.

[Escolher Oráculo]

[← Classes]
```

#### ☀️ Luminar

```text
[Imagem contextual do Luminar]

☀️ Luminar

Luminars canalizam luz como força de proteção, restauração e julgamento. Seu estilo alterna entre sustentar aliados, erguer Barreiras e punir inimigos com poder concentrado.

⚔️ Estilo de Luta · Suporte e Julgamento

❤️ HP · Alto
🛡️ DEF · Alta
⚔️ ATQ · Baixo
💨 AGI · Baixa

🎴 Artes de Classe

☀️ Fulgor · Dano
❤️ Renovação · Cura
🛡️ Égide Solar · Barreira
⚖️ Julgamento · Dano e Reduz Cura
✨ Luz Restauradora · Cura e Barreira
💥 Explosão Solar · Dano em Área

🎭 Caminhos Futuros

🪬 Guardião · Proteção
Especializa o Luminar em Cura, Barreiras, Purificação e sustentação do grupo.

⚖️ Inquisidor · Julgamento
Converte parte de sua vocação protetora em pressão ofensiva, redução de Cura e remoção de efeitos positivos dos inimigos.

[Escolher Luminar]

[← Classes]
```

### 45.4 Confirmação Final

A confirmação final é a única confirmação obrigatória do fluxo, porque torna Raça e Classe definitivas para o personagem no lançamento.

```text
[Imagem contextual do personagem]

🪪 Confirmar Personagem

Seu nome foi escolhido, sua origem foi definida e sua vocação começa a tomar forma. Ao confirmar, sua jornada por Asterion terá início.

🏷️ Nome · Luiken
🕯️ Raça · Remanescente
🧩 Adaptabilidade · Passiva Racial
🗡️ Classe · Errante

⚠️ Raça e Classe não poderão ser alteradas após a criação do personagem.

[Confirmar Personagem]

[Nome] [Raça] [Classe]

[← Classes]
```

- Não mostrar tag de Guilda.
- Não repetir Caminhos Futuros nesta tela; eles já foram apresentados no detalhe da Classe.
- `[Nome]`, `[Raça]` e `[Classe]` permitem revisar o respectivo passo e retornar à confirmação sem apagar as demais escolhas válidas.
- Após confirmar, entrar diretamente no prólogo; não criar tela de sucesso.

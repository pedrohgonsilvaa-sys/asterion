# ASTERION — Consolidação de Visual & UI
## Decisões aprovadas para integração à Fonte Mestra

Data de consolidação: 2026-09-26
Atualização consolidada: 2026-09-26 — sincronizada com a Fonte Mestra v1.4.7, a Baseline Numérica v1.0, Terras do Ocaso v1.0.5 FINAL e Vales dos Enforcados v1.0.2 FINAL; preserva a formalização da Derrota com continuidade no Prólogo e fecha a apresentação implementável de P2 — Fuligem sem Fogo e Charneca da Fuligem.
Auditoria anterior: 2026-09-24 — preservadas as correções anteriores e integrada a padronização Visual/UI global de Consumíveis, incluindo Proteção, Dissipação e Resguardo, então sincronizada com a Fonte Mestra v1.4.6 e Vales dos Enforcados v1.0.2 FINAL.
Autoridade estrutural: `ASTERION_GDD_Estrutural_v1.4.7_Fonte_Mestra.md`
Autoridades regionais: `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.5_FINAL.md` e `ASTERION_CONTEUDO_VALES_DOS_ENFORCADOS_v1.0.2_FINAL.md`
Escopo: Telegram Bot, sem Mini App.
Esta revisão preserva a iconografia/UI regional dos Vales dos Enforcados, a padronização cruzada de resultados, recompensas, Bestiário, Códice, Feitos, materiais e fluxos de PvE/PvP e a padronização global de Consumíveis da seção 59; a seção 60 fecha a apresentação player-facing de P2 e da Charneca da Fuligem.

> Este documento consolida as decisões de Visual/UI tomadas na revisão do projeto. Valores numéricos, custos, recompensas e nomes de conteúdo usados apenas para demonstrar telas permanecem **SIMULAR**, salvo quando já definidos pela Fonte Mestra ou pela autoridade regional vigente.

---

## 1. Princípios gerais de interface

A interface player-facing de Asterion no Telegram segue esta composição:

1. imagem contextual em pixel art;
2. texto formatado do Telegram;
3. emojis semânticos usados com parcimônia;
4. botões inline apenas para ações úteis.

### Regras gerais

- Navegação e ações devem preferir editar a mesma mensagem/mídia, evitando spam no chat.
- Evitar telas intermediárias, confirmações e mensagens de sucesso quando a ação for reversível e sem risco relevante.
- Confirmações permanecem para compras/gastos relevantes, exclusão de personagem e outras ações destrutivas exigidas pelo sistema.
- Não usar botões `OK`, `Continuar`, `Fechar` ou equivalentes sem função real.
- Botão de retorno é sempre o último grupo.
- `[← Menu]` retorna ao menu principal.
- `[← Nome da Seção]` retorna ao pai conhecido.
- `[← Voltar]` fica reservado a contextos temporários em que o pai não seja semanticamente melhor.
- Itens indisponíveis não recebem botão desabilitado. A indisponibilidade aparece em texto, por exemplo: `🔒 Ruptura · Indisponível`.
- Listas utilizam números arábicos e botões numéricos quando necessário.
- Quando uma opção já estiver identificada por número em uma lista imediatamente acima e o botão apenas selecionar essa opção, usar botões numéricos correspondentes (`[1] [2] [3]`). Botões que representem ação, comando ou destino sem correspondência numérica direta mantêm o nome da ação.
- Nomes importantes em **negrito**.
- Metadados, valores, níveis, raridades, tipos e estados mecânicos em `monoespaçado`.
- Lore e ambientação em *itálico*.
- `·` separa metadados pertencentes à mesma entidade.
- `│` pode separar valores paralelos quando a leitura permanecer confortável.
- Informações do mesmo bloco ficam próximas; blocos conceitualmente distintos recebem uma linha em branco.
- O nome do jogo em títulos e textos normais player-facing usa **Asterion**; `ASTERION` fica reservado a marca/documentação quando a caixa alta for intencional.
- Datas player-facing usam o formato **`DD/MM/AAAA`**, por exemplo `20/06/2026`.

---

## 2. Nomenclatura player-facing consolidada

- Ranked → **Arena da Vigília**
- GvG → **Batalha de Guildas**
- Builds / Presets → **Doutrinas**
- Skills → **Artes**
- Subclasse → **Caminho**
- Profissões → **Ofícios**
- Social → **Vínculos**
- Login Diário → **Dádiva Diária**
- Supporter → **Patrono de Asterion**
- Recruitment / Referrals → **Chamado de Asterion**
- Promo Codes → **Códigos de Asterion**
- Fast Travel → **Travessia dos Braseiros**
- Dungeon Fast Access → **Caminho Conhecido**
- Auto Hunt → **Ronda de Caça**
- Hall of Fame / History → **Salão da Vigília**
- Battle Pass progression → **Trilha da Crônica**
- Premium Battle Pass → **Passe da Crônica**
- Main leaderboard → **Classificação da Vigília**
- Explore → **Desbravar**
- Achievements → **Feitos**
- Side Quests → **Missões Secundárias**
- Epíteto → **Título**
- Guild Projects → **Obras da Guilda**
- Currency → **Coroas**
- PvP visible rating → **Renome**
- Ready check → **Confirmação de Entrada**
- Matchmaking → **Pareamento**
- Cooldown → **Recarga**
- Loadout → **Configuração de Combate**
- First Clear → **Primeira Conclusão**
- Trade → **Troca Direta**
- Champion → **Campeão**
- Boss → **Chefe**
- Loot → **Saque / Recompensas**
- Tradable → **Negociável**

---

## 3. Registro oficial de iconografia

### Sistemas

- 🎒 Inventário
- 🗄️ Armazém
- 📦 Entregas Pendentes
- 🗺️ Mapa
- 🧭 Desbravar
- 🐾 Bestiário
- 📖 Códice
- 🏆 Feitos
- 🎖️ Títulos
- ⛓️ Masmorras
- 🦌 Caçada
- 🏕️ Ronda de Caça
- 🌍 Eventos Mundiais
- 🚩 Expedição
- ⚜️ Juramento
- ⚔️ Arena da Vigília
- 🤝 Vínculos
- 🏆 Classificação da Vigília
- 🏛️ Salão da Vigília
- 🛡️ Guilda
- 🛒 Mercado
- 📅 Calendário
- 🌤️ Dádiva Diária
- 📣 Chamado de Asterion
- 🎟️ Códigos de Asterion
- 🔱 Patrono de Asterion
- 🌌 Crônica
- 📚 Trilha da Crônica
- 💠 Passe da Crônica
- 💬 Comunidade
- 🎛️ Configurações
- 🔔 Notificações
- 🛟 Ajuda
- 👤 Conta

### Regiões

- 🌑 Terras do Ocaso — Nv. 1–10
- 🪢 Vales dos Enforcados — Nv. 11–20
- 🌾 Planícies de Nareth — Nv. 21–30
- 🥀 Várzeas Carmesins — Nv. 31–40
- ⛰️ Altos Cinéreos — Nv. 41–50
- 🌫️ Confins do Véu — Nv. 51–60

### Raças

- 🕯️ Remanescentes
- 🌘 Velados
- 🌪️ Cinéreos
- 🩸 Hemários
- 🔆 Alvoranos

### Classes

- 🛡️ Sentinela
- 🗡️ Errante
- 🏹 Vigia
- 🪄 Tecelão
- 🔮 Oráculo
- ☀️ Luminar

### Caminhos

- 🏰 Bastião
- 💥 Devastador
- ☠️ Carrasco
- 🕷️ Sabotador
- 🎯 Atirador
- 👣 Rastreador
- 🌀 Conjurador
- 🔷 Rúnico
- 🦉 Agoureiro
- 🐺 Invocador
- 🪬 Guardião
- ⚖️ Inquisidor

### Ofícios

- ⚒️ Ferreiro
- ⚙️ Artífice
- ⚗️ Alquimista
- 🧵 Curteiro
- 💎 Joalheiro

### Progressão / Personagem

- 🎴 Artes
- 🌿 Talentos
- 🧩 Doutrinas
- 🎭 Caminho
- 🏛️ Legado
- 📇 Perfil
- 📈 Atributos

### Equipamentos

- 🗡️ Arma Principal
- ⚔️ Arma Secundária
- 🪖 Cabeça
- 🥋 Torso
- 🧤 Mãos
- 🥾 Pés
- 💍 Acessório
- 🧿 Artefato

### Melhoria de itens

- 🛠️ Criação
- 🔥 Forja
- ♻️ Desmontagem
- 🔷 Runas
- 💫 Encantamento
- 🔼 Aprimoramento

### Cosméticos / Prestígio

- 🎨 Cosméticos
- 🧍 Aparência
- 🎖️ Título
- 🔰 Emblema
- 🖼️ Moldura
- 🏳️ Banner
- 🎗️ Prestígio

### Recursos e atributos

- ❤️ HP
- ⚡ Vigor
- 🪙 Coroas
- ✨ XP
- 🏅 Renome
- 🎁 Recompensas
- 📦 Entrega Pendente
- ⚔️ ATQ
- 🛡️ DEF
- 💨 AGI
- 🗡️ PER
- 💥 Crítico

### Materiais e recursos de criação

Iconografia por família, reutilizável entre Regiões:

- ⛏️ Metal — ex.: Ferro de Fuligem, Ferro Enredado
- 🐾 Couro — ex.: Couro Escoriado, Couro Musgoso
- 🌿 Reagente — ex.: Erva Cinzenta, Erva de Turfa
- 💧 Essência — ex.: Resíduo do Ocaso, Resina Enredada
- ⚗️ Catalisador — Catalisador de Elite por Grau
- 🪨 Fragmento de Aprimoramento — por Grau
- 💠 Núcleo — Núcleo de Chefe/Masmorra/família conforme conteúdo
- 🔷 Runa — preserva o ícone global já vigente
- 🧱 Materiais — cabeçalho/categoria de Inventário, Receita e Criação

A mesma família mantém o mesmo emoji entre Regiões. Reutilização de emoji em contextos diferentes é permitida quando semanticamente clara; evitar ambiguidade principalmente dentro da mesma tela/bloco.

### Raridades

- ⚪ Comum
- 🔵 Raro
- 🟣 Épico
- 🟠 Lendário
- 🔴 Mítico

### Estados de item

- ⭐ Favorito
- ✅ Equipado
- 🔗 Vinculado
- 🔃 Negociável
- 🔒 Bloqueado

### Estados gerais

- ✅ Concluído / Recebido / Confirmado
- ✨ Disponível / Destaque
- ⏳ Pendente / Aguardando
- 🔒 Indisponível / Bloqueado
- ⚠️ Alerta / Interrompido
- 🔄 Retomada / Recuperação
- 🟢 Ativo
- ⚪ Inativo

### Missão Principal — Suspensa

- **Suspensa** é reservada à Missão Principal quando ela permanece válida e com progresso preservado, mas aguarda requisito narrativo, externo ou contextual ainda não satisfeito.
- Usar **⏳** para comunicar o requisito/condição aguardada.
- Não usar botão `[Retomar]` para Missão Principal Suspensa. Esse estado não representa interrupção técnica.
- **🔄 Retomada / Recuperação** permanece reservado a atividades efetivamente interrompidas que podem ser retomadas.
- Quando a condição volta a ser válida, a Missão Principal retorna automaticamente para **Em Andamento**.
- Missões Secundárias não usam **Suspensa** no estado atual do design.

Exemplos:

```text
📜 [NOME DA MISSÃO PRINCIPAL] · Suspensa
⏳ Requer Nv. 8

A jornada continuará quando seu personagem estiver preparado para seguir adiante.
```

```text
📜 [NOME DA MISSÃO PRINCIPAL] · Suspensa
⏳ Aguarda um novo marco da Campanha
```

---

## 4. Personagem — organização final

A tela **Personagem** deve funcionar como hub, não como ficha completa de atributos. Os atributos ficam em submenu próprio.

A ordem deve privilegiar sistemas usados com maior frequência.

### Estrutura

```text
[Imagem contextual do personagem]

🪪 Personagem

Cada batalha, escolha e descoberta deixa marcas em quem você se torna. Aqui estão os caminhos, conquistas e escolhas que dão forma à sua jornada por Asterion.

🎒 Inventário · Itens
🛡️ Equipamentos · Arsenal
🎴 Artes · Combate
🧩 Doutrinas · Configuração
🌿 Talentos · Evolução
📈 Atributos · Status
⚒️ Ofícios · Criação
🎨 Cosméticos · Aparência
📇 Perfil · Identidade
🎭 Caminho · Especialização
🏛️ Legado · Ascensão

[Inventário] [Equipamentos]
[Artes] [Doutrinas]
[Talentos] [Atributos]
[Ofícios] [Cosméticos]
[Perfil] [Caminho]
[Legado]

[← Menu]
```

---

## 5. Perfil e História do Personagem

**Perfil** pertence a Personagem e concentra identidade pública/social do personagem.

A História do Personagem é escrita pelo próprio jogador, opcional e editável. Pode ser compartilhada diretamente na área apropriada da Comunidade, como Relato, sem uma página intermediária desnecessária.

### Perfil

```text
[Imagem contextual do perfil]

📇 Perfil

🗡️ [VLT] Luiken · Nv. 24
Errante · Sabotador

🎖️ Caçador do Ocaso
🛡️ Guilda · [VLT] Valtaris
🏅 Elo · Chama II

📖 História

Nasci onde as cinzas cobriam os campos antes mesmo que o sol pudesse tocá-los. Aprendi cedo que sobreviver não significava permanecer inteiro, apenas continuar caminhando quando tudo ao redor já havia parado.

[Editar História] [Compartilhar História]

[← Personagem]
```

Quando não houver história:

```text
📖 História

Conte quem seu personagem era, o que encontrou pelo caminho e o que ainda busca em Asterion.

[Escrever História]
```

---

## 6. Atributos

Atributos permanece como submenu próprio. Não usar modelo híbrido com atributos repetidos na raiz de Personagem.

Os valores devem aparecer verticalmente, um abaixo do outro.

```text
[Imagem contextual do personagem]

📈 Atributos

Força, resistência e instinto são moldados por tudo aquilo que seu personagem aprende, veste e aperfeiçoa. Estes valores representam sua condição atual diante dos perigos de Asterion.

🗡️ [VLT] Luiken · Nv. 24
Errante · Sabotador

❤️ HP · 1.240 / 1.240
⚡ Vigor · 72 / 100

⚔️ ATQ · 318
🛡️ DEF · 224
💨 AGI · 187
🗡️ PER · 96

💥 Crítico · 18%
💨 Esquiva · 12%
🛡️ Bloqueio · 5%

[← Personagem]
```

Valores são SIMULAR.

---

## 7. Cosméticos

Formalizar a hierarquia:

**Personagem → Cosméticos**

1. 🧍 Aparência · Visual
2. 🎖️ Título · Identidade
3. 🔰 Emblema · Distinção
4. 🖼️ Moldura · Perfil
5. 🏳️ Banner · Exibição

`Skin` não deve ser usado player-facing. O termo oficial é **Aparência**.

Aparência é exclusivamente cosmética e independente de Equipamentos.

### Hub

```text
🎨 Cosméticos

Escolha como seu personagem se apresenta em Asterion e quais marcas de sua jornada deseja carregar consigo.

1 🧍 Aparência · Visual
2 🎖️ Título · Identidade
3 🔰 Emblema · Distinção
4 🖼️ Moldura · Perfil
5 🏳️ Banner · Exibição

[1] [2] [3] [4] [5]

[← Personagem]
```

### Aparências

A Aparência atualmente usada é destacada no topo. Não escrever `Equipada`, `Atual` ou estado equivalente. A posição visual comunica o estado.

Mostrar a **origem** das Aparências em vez de `Desbloqueada`.

```text
[Imagem do personagem com a Aparência atual]

🧍 Aparência

As marcas de uma jornada também vivem na forma como ela é lembrada. Escolha o visual que acompanhará seu personagem pelos caminhos de Asterion.

🌌 Vestígio da Convergência
Crônica · Ecos da Convergência

🗂️ Outras Aparências

1 🧍 Viajante de Asterion · Padrão
2 🌑 Errante das Cinzas · Feito
3 🔱 Manto do Patrono · Patrono

[1] [2] [3]

[← Cosméticos]
```

Detalhe:

```text
[Imagem do personagem com a Aparência em prévia]

🌑 Errante das Cinzas
Feito · Bestiário

Há quem atravesse as terras cobertas de cinza e volte carregando apenas cicatrizes. Outros retornam trazendo no próprio semblante os sinais de que aprenderam a caminhar entre aquilo que caça e aquilo que é caçado.

[Equipar]

[← Aparências]
```

Ao equipar, retornar à lista e mover a Aparência para o destaque superior. Sem confirmação ou tela de sucesso.

### Títulos

Título usado em destaque no topo, sem estado escrito.

```text
🎖️ Títulos

Alguns nomes são recebidos ao nascer. Outros precisam ser conquistados. Escolha qual marca de sua jornada acompanhará seu nome por Asterion.

🏷️ Caçador do Ocaso
Bestiário · Terras do Ocaso

📜 Outros Títulos

1 🎖️ Andarilho das Cinzas · Exploração
2 🎖️ Forjado na Vigília · PvP
3 🎖️ Eco da Convergência · Crônica
```

Detalhe inclui origem, lore e `[Usar Título]`.

### Emblemas

Emblema usado em destaque superior; coleção abaixo.

Cabeçalho da coleção: `🗃️ Outros Emblemas`.

Detalhe inclui procedência, lore e `[Usar Emblema]`.

### Molduras

Moldura usada em destaque superior; coleção abaixo.

Cabeçalho da coleção: `🪟 Outras Molduras`.

Detalhe inclui prévia do perfil, procedência, lore e `[Usar Moldura]`.

### Banners

Banner usado em destaque superior; coleção abaixo.

Cabeçalho da coleção: `🚩 Outros Banners`.

Detalhe inclui prévia do perfil, procedência, lore e `[Usar Banner]`.

---

## 8. Conta

Conta fica reservada a ações administrativas/sensíveis. Cosméticos não pertencem a Conta.

### Raiz

```text
👤 Conta

Algumas decisões alteram sua identidade ou a continuidade de sua jornada em Asterion. Aqui ficam as ações que exigem maior cuidado.

1 ✏️ Renomear Personagem · Identidade
2 🗑️ Excluir Personagem · Exclusão

[1] [2]

[← Configurações]
```

### Renomear Personagem

Fluxo mínimo: **Conta → Renomear → digitar novo nome → confirmar**.

```text
✏️ Renomear Personagem

O nome que você carrega atravessa batalhas, alianças e histórias. Escolha como deseja ser reconhecido daqui em diante por Asterion.

🏷️ Nome Atual · Luiken
✅ Renome · Disponível

Envie no chat o novo nome do personagem.

[← Conta]
```

Após digitar:

```text
✏️ Renomear Personagem

Uma nova identidade está pronta para ser assumida.

🏷️ Nome Atual · Luiken
✨ Novo Nome · Vaelric

🪙 Custo · 2.500 Coroas
⏳ Recarga · 30 dias

[Confirmar Renome]
[Alterar Nome]

[← Conta]
```

Custo e recarga desta tela são autoritativos pela Fonte Mestra v1.4.7: **2.500 Coroas + Recarga de 30 dias**.

Nome indisponível usa `🔒`; nome inválido usa `⚠️`. Não abrir página de erro separada.

Após confirmar, retornar à Conta com aviso contextual temporário `✅ Nome Alterado · Vaelric`; sem página de sucesso.

### Excluir Personagem

```text
🗑️ Excluir Personagem

Algumas jornadas chegam ao fim por escolha de quem as iniciou. A exclusão não será imediata e ainda poderá ser interrompida antes de sua conclusão.

⚔️ [VLT] Luiken · Nv. 24

⏳ Período de Exclusão · 7 dias
🔄 Recuperação · Durante o Prazo
🔒 Exclusão Definitiva · Após o Prazo

[Confirmar Exclusão]

[← Conta]
```

Estado pendente:

```text
⏳ Exclusão Pendente

Esta jornada está marcada para terminar, mas ainda pode ser recuperada antes do encerramento do prazo.

⚔️ [VLT] Luiken · Nv. 24

⏳ Tempo Restante · 6d 18h
🔄 Recuperação · Disponível

[Cancelar Exclusão]

[← Conta]
```

Cancelar exclusão é ação segura e não exige nova confirmação.

---

## 9. Equipamentos

### Padrão oficial de nome aprimorado

Todo equipamento aprimorado deve ser exibido assim:

**`🗡️ Lâmina da Ruptura · +6`**

O nível de aprimoramento fica depois do nome, separado por `·`.

Aplicar em Equipamentos, Inventário, Armazém, Mercado, detalhes, Runas, Encantamentos, Aprimoramento, Saque e demais contextos.

### Padrão geral de item

```text
🗡️ Lâmina da Ruptura · +6
🔴 Mítico · Arma Principal
⚔️ ATQ +128 │ 🗡️ PER +9%
```

Estados aparecem apenas quando relevantes:

```text
🔗 Vinculado
```

### Tela de Equipamentos

Oito slots fixos:

1. Arma Principal
2. Arma Secundária
3. Cabeça
4. Torso
5. Mãos
6. Pés
7. Acessório
8. Artefato

Slots vazios permanecem visíveis, por exemplo: `5 🧤 Mãos · Vazio`.

### Detalhe do equipamento

```text
[Imagem contextual da arma]

🗡️ Lâmina da Ruptura · +6
🔴 Mítico · Arma Principal
🔗 Vinculado
📈 Nível do Item · 60

⚔️ ATQ +128
🗡️ PER +9%

🔷 Runa da Ruptura · Grau VI · PER +4%
💫 Eco Fraturado · CRIT +3%

O metal escurecido da lâmina carrega fissuras vivas, como se a Ruptura ainda pulsasse em seu interior.

[Trocar] [Desequipar]
[Runas] [Encantamento]
[Aprimorar]

[← Equipamentos]
```

Regras de nível:

- o detalhe de Equipamento mostra `📈 Nível do Item · X`;
- como regra global, `required_level = item_level`;
- quando o personagem estiver abaixo do requisito, mostrar também `⏳ Requer Nv. X` e não oferecer `[Equipar]`;
- Inventário/Armazém/Mercado podem continuar exibindo e armazenando o item normalmente; a restrição é de equipar, não de possuir;
- Aprimoramento `+0→+10`, Reroll, Runa ou Encantamento não alteram o Nível do Item.

Ordem visual aprovada:

1. identidade;
2. raridade/tipo/estado;
3. atributos;
4. Runa e Encantamento;
5. lore;
6. ações.

---

## 10. Runas

### Tela de Runas do equipamento

```text
[Imagem contextual da arma]

🔷 Runas

🗡️ Lâmina da Ruptura · +6
🔴 Mítico · Arma Principal
🔷 Runa da Ruptura · Grau VI · PER +4%

🎒 Runas Disponíveis

1 🔷 Runa do Véu
🔵 Raro · Grau VI · DEF +5%

2 🔷 Runa Cinérea
🟣 Épico · Grau VI · ATQ +6%

3 🔷 Runa da Vigília
🟠 Lendário · Grau VI · CRIT +4%

[1] [2] [3]
[Remover Runa]
[← Lâmina da Ruptura]
```

Quantidade oficial de slots de Runa: **1 por Equipamento normal; 2 em Arma 2H**. Em 2H, a afinidade A usa o pool de Principal e a afinidade B usa o pool de Secundária.

A UI deve mostrar o **Grau da Runa**. Uma Runa só pode ser instalada quando `Grau da Runa ≤ Grau do Equipamento` e o efeito for compatível com o slot/afinidade; incompatibilidade não altera o Inventário da Runa, apenas bloqueia a instalação.

### Substituição

Não usar seta para representar troca de Runas. Usar bloco de substituição:

```text
[Imagem contextual da arma]

🗡️ Lâmina da Ruptura · +6

🔷 Runa Cinérea
🟣 Épico · Runa · Grau VI
⚔️ ATQ +6%

♻️ Substituição

Atual · 🔷 Runa da Ruptura · Grau VI · PER +4%
Nova · 🔷 Runa Cinérea · Grau VI · ATQ +6%

[Substituir Runa]
[← Runas]
```

Formatação:

- `Atual` e `Nova` em monoespaçado;
- nome da Runa em negrito;
- `ATQ`, `PER` e demais valores mecânicos em monoespaçado.

---

## 11. Encantamento

Equipamento pode possuir até 1 Encantamento. Ao aplicar outro, o anterior é destruído conforme regra do sistema.

A UI mostra o Grau do Encantamento quando ele for apresentado/selecionado. Aplicação exige `Grau do Encantamento ≤ Grau do Equipamento`, além da compatibilidade normal do efeito com o slot.

A tela segue linguagem visual semelhante às Runas.

```text
💫 Encantamento

🗡️ Lâmina da Ruptura · +6
🔴 Mítico · Arma Principal
💫 Eco Fraturado · CRIT +3%

🪄 Encantamentos Disponíveis

1 💫 Fio Voraz
🟣 Épico · ATQ +5%

2 💫 Marca do Véu
🔵 Raro · PER +4%

3 💫 Pulso Cinéreo
🟠 Lendário · CRIT +5%
```

Substituição:

```text
🗡️ Lâmina da Ruptura · +6

💫 Fio Voraz
🟣 Épico · Encantamento
⚔️ ATQ +5%

♻️ Substituição

Atual · 💫 Eco Fraturado · CRIT +3%
Novo · 💫 Fio Voraz · ATQ +5%

⚠️ O Encantamento atual será destruído.

[Aplicar Encantamento]
[← Encantamentos]
```

---

## 12. Aprimoramento

O Aprimoramento utiliza `🔼`.

Não mostrar `Sucesso Garantido` em toda tentativa. Se o sistema é sempre garantido, isso é regra ensinada pela Ajuda/introdução, não estado necessário na interface recorrente.

A seta é aceitável **na comparação numérica de aprimoramento**, porque representa evolução direta do mesmo atributo.

### Tela final

```text
[Imagem contextual da arma]

🔼 Aprimoramento

🗡️ Lâmina da Ruptura · +6
🔴 Mítico · Arma Principal
🔗 Vinculado

📈 Aprimoramento · +7

⚔️ ATQ · 128 → 142 (+14)
🗡️ PER · 9% → 10% (+1%)

🪨 Fragmento de Aprimoramento {Grau aplicável} · 18 / 12
🪙 Coroas · 4.200

[Aprimorar]

[← Lâmina da Ruptura]
```

Se faltarem recursos, remover `[Aprimorar]` e mostrar estado textual apropriado; nunca usar botão desabilitado.

---

## 13. Artes

### Identidade do personagem nas telas

Padrão:

```text
🗡️ [VLT] Luiken
Errante · Sabotador
```

Nome/tag e Classe/Caminho ficam em linhas distintas.

### Tela principal

```text
[Imagem contextual do personagem]

🎴 Artes

Cada Arte revela uma forma diferente de enfrentar o perigo. Algumas nascem da disciplina, outras do instinto, mas todas carregam a marca do caminho escolhido.

🗡️ [VLT] Luiken
Errante · Sabotador

🎴 Artes Equipadas

1 🗡️ Corte Sombrio · Ataque
2 💨 Passo Velado · Mobilidade
3 🩸 Ferida Profunda · Efeito

📚 Outras Artes

4 ⚔️ Golpe Oportuno · Ataque
5 🌑 Véu Cinéreo · Defesa
6 🕷️ Marca do Sabotador · Controle

[1] [2] [3]
[4] [5] [6]

[← Personagem]
```

### Detalhe

```text
[Imagem contextual da Arte]

🎴 Corte Sombrio
Arte Ativa · Sabotador

Um golpe executado no instante em que a guarda adversária vacila. A lâmina atravessa a abertura antes que o alvo perceba que a própria sombra o denunciou.

⚔️ Dano · 145% ATQ
🩸 Aplica · Sangramento
🎯 Alvo · 1 Inimigo
⏳ Recarga · 3 Rodadas

🧩 Slot · 1

[Substituir Arte]

[← Artes]
```

### Equipar / substituir

Estrutura aprovada:

```text
[Imagem contextual da Arte]

🎴 Equipar Arte

⚔️ Golpe Oportuno
Arte Ativa · Errante

⚔️ Dano 125% ATQ
💥 Crítico Aumentado

🎴 Artes Equipadas

1 🗡️ Corte Sombrio · Ataque
2 💨 Passo Velado · Mobilidade
3 🩸 Ferida Profunda · Efeito

Escolha qual Arte deseja substituir.

[1] [2] [3]

[← Golpe Oportuno]
```

Ao escolher o slot, substituir imediatamente. Não exigir confirmação, pois a ação é reversível e sem custo.

Se houver apenas um slot vazio, equipar diretamente sem tela de seleção.

---

## 14. Doutrinas

Doutrinas representam configurações salvas de combate. A tela deve parecer uma coleção de estratégias, não um painel técnico.

### Raiz

```text
[Imagem contextual do personagem]

🧩 Doutrinas

Com o tempo, cada combatente desenvolve maneiras próprias de enfrentar os perigos de Asterion. Preserve suas configurações e retome uma estratégia quando ela voltar a ser necessária.

🗡️ Véu Cortante
Sabotador · Configuração Atual

📚 Outras Doutrinas

1 🛡️ Passos do Sobrevivente · Sabotador
2 🩸 Lâmina Rubra · Carrasco
3 ⚔️ Caçador da Vigília · Sabotador

[1] [2] [3]

[Nova Doutrina]

[← Personagem]
```

Não escrever `Completa` em toda Doutrina válida. Estados aparecem apenas quando houver problema relevante, por exemplo `⚠️ Requer Respec` ou `⚠️ Incompleta`.

O detalhamento interno de Doutrina foi consolidado posteriormente nesta mesma revisão; ver seção 28.

---

## 15. Bestiário

Estrutura fechada:

**Observado → Conhecido → Estudado → Dominado**.

- Criaturas ocultas não aparecem antes da descoberta.
- Não usar `???`, silhueta ou contador de criaturas desconhecidas.
- Progressão interna não é exibida por barras ou contadores públicos.
- Habitat usa Região → Local conhecidos.
- Variantes permanecem ocultas até descoberta.
- Progressão é permanente por personagem e persiste no Legado conforme regra estrutural.

### Navegação

Bestiário → Região → criatura conhecida → detalhe.

Regiões mostram apenas quantidade conhecida, por exemplo `12 Criaturas Conhecidas`, sem denominador total.

Detalhe não recebe cabeçalho redundante `Bestiário`; começa diretamente pela criatura.

### Conteúdo por estágio

**Observado:** identificação + localização + lore curta.

**Conhecido:** lore, hábitos opcionais e materiais comuns.

**Estudado:** combate, efeitos, Artes, materiais e lore ampliada. Habitat, Fraqueza e Resistência são apresentados preferencialmente de forma narrativa/contextual nas descrições e Notas de Campo; os modificadores técnicos permanecem autoritativos no Conteúdo/backend, sem exposição percentual automática na UI.

**Dominado:** dossiê legítimo completo, incluindo prioridades, atributos qualitativos e Notas de Campo, preservando spoilers protegidos. Quando uma Fraqueza/Resistência precisar de linha técnica para clareza, usar descrição sem percentual player-facing, salvo exceção futura explicitamente aprovada.

---

## 16. Códice

Códice é memória/conhecimento do personagem, não wiki onisciente nem checklist de conclusão.

Categorias:

1. 🪐 Mundo e Cosmologia
2. 🗺️ Regiões e Locais
3. 🏴 Povos e Facções
4. 👤 Figuras
5. 📜 História e Acontecimentos
6. 👁️ Mistérios e Fenômenos
7. 🌌 Crônicas

Conteúdo desconhecido fica ausente.

### Hierarquia de Regiões e Locais

**Códice → Regiões e Locais → Região → Local → detalhe do Local**.

Não misturar Região, Local e entrada narrativa na mesma lista.

Exemplo:

```text
🗺️ Regiões e Locais

1 🌑 Terras do Ocaso · Nv. 1–10
2 🪢 Vales dos Enforcados · Nv. 11–20
...
```

Dentro da Região, listar apenas Locais conhecidos. Dentro do Local, podem aparecer lore, Braseiro conhecido, criaturas conhecidas por nome e trechos narrativos. Mecânicas das criaturas permanecem no Bestiário; deslocamento permanece no Mapa/Travessia.

---

## 17. Feitos e Títulos

Feitos usam as categorias:

- 🧭 Exploração
- ⚔️ Combate
- ⛓️ PvE
- 🏅 PvP
- 🛡️ Guilda
- ⚒️ Ofícios
- 🌌 Crônicas
- 🐾 Bestiário
- 👁️ Segredos

Feitos ocultos permanecem ausentes até desbloqueio.

Recompensas são principalmente Títulos, Emblemas, Molduras, Banners e Prestígio. Não inventar XP como recompensa genérica de Feito.

Não criar tela adicional de detalhe do Feito quando a lista já comportar descrição e recompensa.

`Epíteto` foi substituído por **Título** player-facing em toda a interface.

---

## 18. Calendário

Calendário semanal fixo, consultado por dia da semana. Horário vem antes da atividade.

```text
📅 Calendário

📆 Segunda-feira
06:00 ☀️ Novo Dia
06:00 🌅 Nova Vigília
07:00 ⚔️ Arena da Vigília
12:00 🌍 Evento Mundial
18:00 🚩 Expedição
21:00 🛡️ Batalha de Guildas

[Seg] [Ter] [Qua] [Qui]
[Sex] [Sáb] [Dom]

[← Menu]
```

Horários de atividades não definidos permanecem SIMULAR. Reset diário e Nova Vigília seguem definições estruturais existentes.

Dia vazio: `Nenhuma atividade programada para este dia.`

---

## 19. Dádiva Diária

Sistema usa 🌤️.

Estados:

- ✅ dia já recebido;
- ✨ dia atual disponível;
- ⏳ dia futuro.

Exemplo:

```text
🌤️ Dádiva Diária

✅ Dia 1 · 🪙 500 Coroas
✅ Dia 2 · 🧪 Poção Rubra · 2x
✨ Dia 3 · 🪨 Fragmento de Aprimoramento {Grau} · 10x
⏳ Dia 4 · ...

✨ Dádiva Disponível · Dia 3

[Receber Dádiva]
[← Benefícios]
```

Valores/recompensas SIMULAR.

---

## 20. Chamado, Códigos, Patrono e Trilha

### Chamado de Asterion

```text
📣 Chamado de Asterion

🔗 Seu Chamado
ASTERION-LUIKEN

👥 Recrutas Vinculados · 3
...

[Compartilhar Chamado] [Recompensas]
[← Benefícios]
```

### Códigos de Asterion

Tela simples com `[Inserir Código]`. Código válido mostra `🎟️ Código Resgatado` + recompensas. Inválido/usado/expirado atualiza a mesma mensagem.

### Patrono de Asterion

Descrição oficial deve usar **jogabilidade**, nunca `gameplay`.

Patrono concede apenas benefícios visuais/prestígio, sem poder, atributos, XP, Coroas, Vigor, drop, equipamentos ou vantagens econômicas.

### Trilha da Crônica

Progressão linear por **Marcos**, compartilhada entre Livre e Premium.

- Premium = Passe da Crônica.
- Premium concede somente cosméticos/colecionáveis/prestígio.
- Compra retroativa para Marcos já alcançados.
- Não vender progresso/skip.
- Recompensas disponíveis podem ser resgatadas em agregado com `[Resgatar Disponíveis]`.
- Após o fim da Crônica, progresso congela, compra Premium encerra e permanece apenas janela de resgate conforme regra estrutural.

---

## 21. Configurações, Comunidade, Ajuda e Conta

### Comunidade

Comunidade é entrada direta do Menu Principal. Como existe apenas uma ação, não criar submenu adicional.

O botão **Comunidade** pode redirecionar diretamente para a comunidade oficial quando tecnicamente possível.

Label oficial: `💬 Comunidade`, não `Comunidade Oficial`.

### Configurações

Contém:

- 🔔 Notificações
- 🛟 Ajuda
- 👤 Conta

Comunidade não fica dentro de Configurações.

### Ajuda

Ajuda deve comportar orientação não apenas para sistemas macro, mas também para mecânicas como Classes, Caminhos, Artes, Runas, Encantamentos, Equipamentos e demais conceitos relevantes previstos no GDD.

---

## 22. Estados de erro, vazio e recuperação

### Ação Expirada

```text
⏳ Ação Expirada

Esta ação não está mais disponível. Atualize a tela para continuar.

[Atualizar]
[← Menu]
```

### Falha Temporária

```text
⚠️ Falha Temporária

Não foi possível processar esta ação no momento.

[Tentar Novamente]
[← Voltar]
```

### Retomada Disponível

```text
🔄 Retomada Disponível

A ação foi interrompida, mas seu progresso permanece salvo.

[Retomar]
[← Voltar]
```

### Atividade em Andamento

Mostrar diretamente a atividade existente e permitir retomada; não usar uma tela genérica sem contexto.

Estados vazios devem conter título, texto curto e ação útil quando existir.

Inventário cheio não cria tela genérica dentro do próprio Inventário; falta de espaço aparece contextualmente na ação externa que tentava entregar o item.

---

## 23. Combate — padrão visual

- Título player-facing: `Turno X · Nome`. `Nome` funciona como metadado em monoespaçado.
- `👉` marca o combatente ativo na linha do combatente, nunca no cabeçalho.
- Adversário/criatura aparece acima dos personagens jogadores.
- Em preparação/lobby, HP e Vigor usam valor exato + barra de 10 blocos.
- Em combate, exibir HP exato + barra; **Vigor não aparece na HUD de combate**.
- HP restante usa 🟩/🟨/🟥 conforme a faixa; Vigor restante usa 🟨; `⬜` representa parte consumida/ausente.
- Registro oficial: `📜 Registro de Combate · Recentes`.
- Uma linha em branco após o cabeçalho do Registro; entradas do log ficam contínuas.
- Log em linguagem natural.
- Uma ação/emoji no início da entrada.
- Tags de Guilda podem ser omitidas do log para legibilidade.
- Nomes e Artes em negrito; dano em monoespaçado.
- Durante combate/atividade, não usar cabeçalhos redundantes `Aliados`, `Adversários`, `Grupo` quando a disposição já comunica isso.
- Lobby pré-atividade pode usar `Grupo · x/4` e numeração; combate ativo não mantém numeração de lobby.
- Em Masmorras, convite e Pareamento devem ser **pré-filtrados por elegibilidade** para a Masmorra/dificuldade selecionada: jogador inelegível não aparece como opção válida de convite e não entra na fila. A interface normal do lobby não deve carregar membros inválidos apenas para exibir linhas como `🔒 Requisito · Nv. X`; exceções por mudança de estado são tratadas contextualmente e revalidadas antes da `run_id`.

---

## 24. Sistemas já estruturalmente fechados na auditoria

As seguintes áreas já possuem direção Visual/UI consolidada e devem preservar as regras registradas nesta revisão e na Fonte Mestra:

- Masmorras
- Caçada
- Ronda de Caça
- Desbravar
- Eventos Mundiais (template genérico)
- Expedição
- Juramento
- Arena da Vigília / PvP / Duelo
- Guilda / Batalha de Guildas
- Mercado / Loja / Troca Direta / Serviços
- Armazém
- Entregas Pendentes
- Bestiário
- Códice
- Feitos / Títulos
- Calendário
- Dádiva Diária
- Chamado de Asterion
- Códigos de Asterion
- Patrono de Asterion
- Trilha / Passe da Crônica
- Configurações / Ajuda / Comunidade / Conta
- erros, vazios e recuperação
- Inventário
- Talentos
- Ofícios
- Caminho
- Legado / Marcas de Legado
- Aventura
- Mapa / Travessia dos Braseiros
- Missões
- Criação de Personagem
- Prólogo jogável “Cinzas na Estrada”
- resultados/recibos finais de PvE, PvP e atividades coletivas
- iconografia e padrões regionais dos Vales dos Enforcados

---

## 25. Pontos ainda não fechados

A **Baseline Numérica v1.0 da Fonte Mestra v1.4.7 é autoritativa para implementação e testes** e não possui reabertura numérica vigente. Números, custos, limites, slots e fórmulas já consolidados na Fonte Mestra não permanecem `SIMULAR` nesta Fonte Visual/UI.

Continuam não finais apenas:

- nomes, valores e conteúdo usados exclusivamente como exemplos de mockup quando não correspondem a um valor autoritativo da Fonte Mestra;
- conteúdo/nomenclatura final de eventos, recompensas e itens ainda não definidos pela Fonte Mestra;
- mecânicas futuras ou explicitamente reabertas por Balanceamento e marcadas novamente como `SIMULAR`;
- quaisquer mecânicas não explicitamente definidas pela Fonte Mestra ou por decisões estruturais posteriores.

Em caso de conflito, a Fonte Mestra v1.4.7 prevalece. Exemplos de UI nunca substituem a Baseline Numérica vigente.

---

## 26. Direção de arte

- Dark fantasy medieval em pixel art.
- Atmosfera sombria, melancólica e legível.
- Imagens são contextuais: mostram o que/onde; texto mostra estado; botões mostram ação.
- Não incorporar valores dinâmicos ou HUD falso dentro das imagens.
- Imagem pode mudar conforme local, foco ou estado da atividade.
- Interfaces devem parecer parte de um RPG, não formulários administrativos.
- Lore curta e bem escrita deve ser usada quando contribuir para identidade do objeto, local, Arte, Aparência ou sistema, sem esconder informação mecânica importante.

---

## 27. Regra de integração à Fonte Mestra

Ao integrar este documento:

1. preservar regras mecânicas já existentes que não sejam explicitamente alteradas aqui;
2. tratar decisões deste documento como atualização de nomenclatura, apresentação, navegação e UX player-facing;
3. não transformar exemplos SIMULAR em balanceamento oficial;
4. substituir nomenclaturas player-facing antigas pelas consolidadas quando houver conflito;
5. manter termos técnicos/backend quando necessários, desde que não vazem para a interface player-facing;
6. registrar eventuais conflitos estruturais para reconciliação, em vez de inventar novas mecânicas.
---

## 28. Doutrinas — detalhamento consolidado

As decisões abaixo substituem a observação antiga de que o detalhe interno de Doutrina ainda estava pendente.

### 28.1 Estado e identificação

- Uma Doutrina não fica permanentemente “equipada”.
- Exibir `Configuração Atual` apenas enquanto Caminho, Equipamentos, Artes e Talentos do personagem coincidirem com o estado salvo daquela Doutrina.
- Qualquer alteração manual que quebre essa correspondência remove `Configuração Atual`; não criar rótulo `Configuração Personalizada`.
- Quando nenhuma Doutrina corresponder ao estado atual, mostrar apenas a lista de Doutrinas salvas.
- Não escrever `Completa` em Doutrinas válidas.
- Qualquer incompatibilidade relevante usa o estado geral `⚠️ Doutrina Incompleta`; o componente afetado mostra o motivo específico.

Exemplo de raiz quando há correspondência:

```text
🧩 Doutrinas

🗡️ Véu Cortante
Sabotador · Configuração Atual

📚 Outras Doutrinas

1 🛡️ Passos do Sobrevivente · Sabotador
2 🩸 Lâmina Rubra · Carrasco

[1] [2]
[Nova Doutrina]
[← Personagem]
```

### 28.2 Criação e limite

- `[Nova Doutrina]` solicita apenas o nome e salva automaticamente a Configuração de Combate atual válida.
- Não usar confirmação nem tela de sucesso após a criação.
- No limite de 5/5, remover `[Nova Doutrina]` e mostrar `🔒 Limite de Doutrinas · 5/5`.

### 28.3 Detalhe

Padrão:

```text
🧩 Véu Cortante
Sabotador · Configuração Atual

🛡️ Equipamentos
...

🎴 Artes
...

🌿 Talentos · Distribuição Salva

[Editar Doutrina]
[← Doutrinas]
```

- Quando a Doutrina não for a configuração atual e puder ser aplicada, mostrar `[Aplicar Doutrina]`.
- Caminho não precisa de bloco próprio no detalhe; o Caminho salvo já aparece no subtítulo.
- Runas e Encantamentos aparecem como estado atual do equipamento salvo quando necessário para distinguir a `item_instance`; não são campos independentes da Doutrina.

### 28.4 Editar Doutrina

Hub aprovado:

```text
✏️ Editar Doutrina

🧩 Passos do Sobrevivente
Sabotador

1 Nome · Passos do Sobrevivente
2 Caminho · Sabotador
3 Equipamentos · 8/8
4 Artes · 3/3
5 Talentos · Distribuição Salva

[1] [2] [3] [4] [5]
[Usar Configuração Atual]
[Excluir Doutrina]
[← Passos do Sobrevivente]
```

- `Usar Configuração Atual` sobrescreve o estado salvo após uma tela de revisão simples; não cria nova Doutrina.
- Alterar Caminho dentro da Doutrina não apaga silenciosamente Artes ou Talentos incompatíveis; eles permanecem salvos e podem tornar a Doutrina incompleta.
- Em seleção de Equipamento, mostrar atributos relevantes e, se existirem, Runa e Encantamento da instância específica.
- Em listas gerais de Equipamentos do Inventário, não repetir esse nível de detalhe.
- Em seleção de Artes da Doutrina, não repetir `Arte Ativa` em cada linha; o contexto já comunica isso.

### 28.5 Aplicação, custo e incompletude

- Se a aplicação não tiver custo nem condição especial, `[Aplicar Doutrina]` aplica imediatamente e retorna ao detalhe como `Configuração Atual`.
- Se houver troca de Caminho, redistribuição de Talentos, custo ou condição relevante, usar uma revisão agregada antes do commit.
- Se a Doutrina for impossível no estado atual, remover `[Aplicar Doutrina]`.
- Se houver uma condição resolvível no próprio fluxo, o botão pode permanecer e encaminhar para a revisão necessária.
- Exemplos de componente inválido: `⚠️ Arma Secundária · Item Indisponível`, `⚠️ Talentos · Distribuição Inválida`.
- Excluir Doutrina exige uma confirmação; depois retorna diretamente à raiz de Doutrinas.

---

## 29. Inventário — padrão consolidado

A raiz do Inventário pode organizar as categorias **Equipamentos**, **Consumíveis**, **Materiais** e **Runas**.

### 29.1 Equipamentos no Inventário

Na lista, mostrar identidade, raridade, slot e estados relevantes. Não mostrar atributos na listagem.

```text
1 🗡️ Lâmina da Ruptura · +6
🔴 Mítico · Arma Principal
⭐ Favorito
🔒 Bloqueado
```

- Se um item possuir mais de um estado, cada estado fica em linha própria.
- O detalhe pode mostrar atributos, Runa, Encantamento, estados, lore e ações.
- Se equipado, mostrar `✅ Equipado` e `[Desequipar]`.
- Não usar `[Trocar]` no Inventário; troca contextual pertence ao fluxo de Equipamentos.
- Item bloqueado não recebe ações incompatíveis.

### 29.2 Consumíveis

- Lista mostra nome, quantidade, categoria e estados relevantes.
- O padrão consolidado de listagem usa `{número} 🧪 {Nome} · {quantidade}` e, na linha seguinte, `Consumível · Grau {Grau}`.
- Detalhe mostra efeito, quantidade, estado, lore e ações válidas.
- Item bloqueado não recebe `[Usar]`.
- A disponibilidade em combate PvE segue as regras do conteúdo; o Inventário não precisa de preset manual para PvE manual.
- A apresentação completa e os fluxos de Consumíveis são autoritativamente detalhados na seção 59.

### 29.3 Materiais

- Lista mostra quantidade, categoria e estados.
- Detalhe mantém ordem: identidade → tipo → estado → lore → ações.
- Materiais não recebem `[Usar]`.

### 29.4 Runas

- A lista de Runas não mostra efeitos; efeitos aparecem no detalhe.
- Não usar `[Instalar]` a partir do Inventário. Instalação começa em **Equipamentos → Runas**.

---

## 30. Talentos — padrão consolidado

Raiz:

```text
🌿 Talentos

🗡️ [VLT] Luiken · Nv.24
Errante · Sabotador

🌿 Pontos de Talento
Disponíveis · 2

[Ver Talentos]
[Redistribuir Talentos]
[← Personagem]
```

### 30.1 Árvore/lista

- Não usar árvore ASCII.
- A Fonte Mestra v1.4.7 consolida **18 Talentos por Classe**, organizados em **6 tiers** (`Nv.5/15/25/35/45/55`), com 1 rank por Talento e escolha de 12/18 no Nv.60. A UI não deve tratar esses números como `SIMULAR`.
- Estados visuais principais: `✅ Adquirido`, `✨ Disponível`, `🔒 Requer X`.
- Detalhe de Talento mostra lore, benefício mecânico e estado.
- Talento disponível pode usar `[Adquirir Talento]` sem confirmação individual quando o custo for apenas o ponto normal e a ação fizer parte do fluxo esperado.

### 30.2 Redistribuição

- Mostrar pontos recuperados, custo, Local e Recarga quando aplicáveis.
- Se indisponível por Local, Recarga ou Coroas, mostrar o motivo e remover a ação.
- Redistribuição segue a Fonte Mestra v1.4.7: local seguro apropriado, custo de `2 × C(nível atual)` e **sem Recarga temporal** na Baseline v1.0. No Nv.60, o custo é **2.000 Coroas**.

---

## 31. Ofícios — padrão consolidado

### 31.1 Raiz

```text
⚒️ Ofícios

⚒️ Ferreiro
Ofício Principal · Nv.18

⚗️ Alquimista
Ofício Secundário · Nv.9

📚 Outros Ofícios
1 ⚙️ Artífice · Runas e Encantamentos
2 🧵 Curteiro · Armaduras
3 💎 Joalheiro · Acessórios

[Criação]
[Trocar Ofícios]
[← Personagem]
```

Descritores curtos aprovados para leitura player-facing, quando úteis:

- Ferreiro · `Armas e Armaduras`
- Artífice · `Runas e Encantamentos`
- Alquimista · `Consumíveis`
- Curteiro · `Armaduras`
- Joalheiro · `Acessórios`

Esses descritores são auxiliares de UI; nomes finais de especialidades de conteúdo podem ser refinados sem alterar a estrutura.

### 31.2 Detalhe e receitas

- Detalhe de Ofício ativo mostra nome, nível, lore, `📚 Receitas · Consultar` e `🛠️ Criação · Produzir`.
- Ofício inativo pode permitir consultar Receitas, mas Criação aparece apenas como estado textual, por exemplo `🔒 Criação · Ofício Inativo`, sem botão desabilitado.
- Receitas desconhecidas ficam ausentes; não usar `???`.
- Detalhe de Receita mostra resultado e materiais necessários; pode encaminhar para `[Ir para Criação]`.

### 31.3 Criação

- Lista de criação pode usar `✨ Disponível`, `🔒 Materiais Insuficientes` e `🔒 Requisito Inválido`.
- Tela final mostra item, atributos relevantes, materiais, `📈 Nível do Item · X` e `🎒 Destino · Inventário`.
- `📈 Nível do Item · X` é calculado pelo nível atual do destinatário limitado ao Grau da Receita; em Serviço, o destinatário é o cliente.
- O Preview continua mostrando o Bind final antes da confirmação quando componentes transmitirem restrição.
- Item indisponível não recebe `[Criar]`.
- Runas, Encantamentos e Alquimia exibem o preço efetivo do Grau fornecido pelo backend; não reutilizar automaticamente os antigos exemplos de taxa do Nv.60 em Graus inferiores.

### 31.4 Troca de Ofícios

- Separar escolha de **Principal** e **Secundário**.
- Ao abandonar um Ofício ativo e substituí-lo por outro, mostrar explicitamente a perda de progresso quando houver.
- Receitas conhecidas permanecem conhecidas, mas exigem novamente os requisitos do Ofício.
- Ao rebaixar Principal para Secundário acima do teto secundário, mostrar que o progresso excedente será perdido.
- Ao promover Secundário para Principal, o nível atual é preservado.
- A Fonte Mestra v1.4.7 fixa os caps em **Principal Nv.30** e **Secundário Nv.15**. Inverter os dois Ofícios ativos custa `0,50 × C(nível)`; substituir um Ofício custa `1,00 × C(nível)`, sem Recarga temporal na Baseline v1.0.

---

## 32. Caminho — padrão consolidado

### 32.0 Estados da Provação e escolha inicial no Nv.10

Antes do Nv.10:

```text
🎭 Caminho

🔒 Provação de Classe · Nv.10

[← Personagem]
```

Quando elegível e a Provação ainda não estiver concluída:

```text
🎭 Caminho

✨ Provação de Classe · Disponível

[Iniciar Provação]
[← Personagem]
```

Após concluir a Provação e antes de confirmar o Caminho:

```text
🎭 Caminho

✅ Provação · Concluída
✨ Escolha de Caminho · Pendente

[Escolher Caminho]
[← Personagem]
```

A escolha inicial mostra somente os dois Caminhos válidos para a Classe e informa:

`ℹ️ A primeira Arte do Caminho será desbloqueada no Nv.12.`

Antes do commit, a confirmação mostra Passiva e modificadores inerentes do Caminho escolhido. Após confirmar, retornar diretamente ao estado normal do Personagem; não criar tela intermediária de sucesso sem decisão real.

Raiz:

```text
🎭 Caminho

🗡️ [VLT] Luiken
Errante · Sabotador

1 🕷️ Sabotador · Caminho Atual
2 ☠️ Carrasco · Outro Caminho

[1] [2]
[← Personagem]
```

- O detalhe do Caminho atual não precisa repetir `Atual`; o contexto da raiz já informa isso.
- Detalhe do Caminho atual pode oferecer `[Artes]`.
- Detalhe de outro Caminho pode oferecer `[Artes]` e `[Trocar Caminho]`.
- `[Trocar Caminho]` existe apenas no Caminho alternativo.

### Troca de Caminho

- Mostrar `Atual → Novo`, custo e condição de Local quando aplicáveis.
- Se o Local for inválido, remover a confirmação e mostrar `🔒 Local · Local Inapropriado` ou equivalente curto.
- Se Artes forem incompatíveis, informar quantas serão desequipadas; slots incompatíveis ficam vazios.
- Doutrinas não são reescritas; podem permanecer salvas e ficar `⚠️ Doutrina Incompleta`.
- Não criar tela de sucesso após a troca.

---

## 33. Legado — padrão consolidado

### 33.1 Raiz

```text
🏛️ Legado

🗡️ [VLT] Luiken · Nv.60
Errante · Sabotador

🏛️ Legado Atual · Sem Legado

✨ Ascensão · Disponível
🎗️ Marcas de Legado · Consultar

[Ascender]
[Marcas de Legado]
[← Personagem]
```

- Quando a Ascensão não estiver disponível, preferir estado curto como `🔒 Ascensão · Requisitos Pendentes`.

### 33.2 Confirmação de Ascensão

- Mostrar novo Legado e redução de nível.
- Resumir o que **Mantém** em texto agrupado, evitando listas longas de cada subsistema.
- Resumir **Após a Ascensão** em texto agrupado: gates de nível voltam a valer, Artes reativam conforme nível, Talentos respeitam pontos disponíveis e Equipamentos incompatíveis são desequipados.
- Ascensão exige confirmação.

### 33.3 Marcas de Legado

- Mostrar `Marcas Ativas · x/5`.
- Na listagem, usar descritor funcional, não `Ativa/Disponível` em todas as linhas, por exemplo `Chamado do Braseiro · Retorno`.
- No detalhe, estado usa `✅ Marca Ativa` ou `🚫 Marca Inativa`.
- Quando 5/5, remover `[Ativar Marca]` e mostrar `🔒 Marcas Ativas · 5/5`.
- Redistribuição mostra custo, Local e Recarga quando aplicáveis.
- Na seleção, Marca indisponível continua visível se já conhecida, mas sem botão acionável.

---

## 34. Aventura — raiz consolidada

**Remover `Continuar` da raiz de Aventura.**

Motivo de UX: a retomada de atividade Foreground já é contextual e específica (`Retomar Masmorra`, `Retomar Combate`, `Retomar Ronda` etc.). Um botão permanente e genérico `Continuar` não possui função mecânica própria e conflita com a regra de não usar `Continuar` sem função real.

Raiz aprovada:

```text
[Imagem contextual do Local atual]

🗺️ Aventura

Estradas, ruínas e caminhos esquecidos se estendem por Asterion. Escolha como deseja seguir sua jornada.

🗺️ Mapa · Mundo
📜 Missões · Objetivos
🦌 Caçadas · Combate
⛓️ Masmorras · Desafios
🧭 Desbravar · Exploração
🌍 Eventos Mundiais · Ocorrências
⚔️ PvP · Competição

[Mapa] [Missões]
[Caçadas] [Masmorras]
[Desbravar] [Eventos]
[PvP]

[← Menu]
```

- Se existir atividade Foreground que exija retomada, a interface deve priorizar o próprio contexto daquela atividade, não um `Continuar` genérico em Aventura.

---

## 35. Mapa e Travessia dos Braseiros

### 35.1 Raiz do Mapa

```text
[Imagem contextual da Região atual]

🗺️ Mapa

🌑 Terras do Ocaso · Nv. 1–10
🔥 Estrada das Cinzas · Local Atual

...

🗺️ Regiões Conhecidas

1 🌑 Terras do Ocaso · Nv. 1–10
2 🪢 Vales dos Enforcados · Nv. 11–20

[1] [2]
[← Aventura]
```

- Mostrar apenas Regiões conhecidas pelo personagem.
- Não usar `???` nem espaços reservados para conhecimento oculto.

### 35.2 Região

- Mostrar Região + faixa de nível e o Local atual logo abaixo.
- Listar apenas Locais conhecidos.
- Local atual pode usar `🔥 Nome · Local Atual`.
- Local conhecido e acessível usa `Acessível`.
- Local conhecido, mas bloqueado, permanece visível com o requisito objetivo, por exemplo `🏰 Ruínas do Vigia · Nv. 8`, sem botão.

### 35.3 Detalhe do Local

Local atual:

```text
🔥 Estrada das Cinzas · Local Atual
Terras do Ocaso · Nv. 1–10

...

🔥 Braseiro · Descoberto
🧭 Desbravar · Disponível
🦌 Caçadas · Disponível

[Desbravar] [Caçadas]
[Travessia dos Braseiros]
[← Terras do Ocaso]
```

Local conhecido que não é o atual:

```text
🏚️ Refúgio do Ocaso
Terras do Ocaso · Nv. 1–10

...

🔥 Braseiro · Descoberto
🚫 Desbravar · Indisponível
🚫 Caçadas · Indisponível

[Travessia dos Braseiros]
[← Terras do Ocaso]
```

Local conhecido, porém inacessível:

```text
🏰 Ruínas do Vigia
Terras do Ocaso · Nv. 1–10

🔒 Acesso ao Local · Nv. 8

...

🚫 Desbravar · Indisponível
🚫 Caçadas · Indisponível

[← Terras do Ocaso]
```

### 35.4 Travessia dos Braseiros

- Mostrar Braseiro atual e destinos permanentes já descobertos.
- Destino descoberto, mas bloqueado, pode permanecer visível com requisito e sem botão.
- Selecionar um destino válido realiza a Travessia imediatamente; não criar confirmação quando não houver custo/risco adicional definido.
- Braseiros de Masmorra nunca aparecem na rede permanente de Travessia.
- Após a viagem, mostrar diretamente o detalhe do novo Local atual.

---

## 36. Missões — padrão consolidado

Nomenclatura player-facing: **Missões Secundárias**, não `Side Quests`.

### 36.1 Raiz

```text
[Imagem contextual da jornada]

📜 Missões

Objetivos, promessas e caminhos ainda inacabados acompanham sua jornada por Asterion.

🔥 Missão Principal

📜 [NOME DA MISSÃO PRINCIPAL] · Em Andamento
Terras do Ocaso · Nv. 1–10

📖 Missões Secundárias

1 🕯️ Luzes sob as Cinzas · Em Andamento
2 🪦 Os Nomes Esquecidos · Em Andamento

[Principal]
[1] [2]
[← Aventura]
```

### 36.2 Missão Principal Suspensa

- `Suspensa` é reservada à Missão Principal.
- Na raiz, acrescentar a condição diretamente abaixo, por exemplo `⏳ Requer · Nv. 8` ou `⏳ Aguarda · Marco da Campanha`.
- Não usar `[Retomar]`, `[Continuar]` ou `[Ativar Missão]`.
- Ao cumprir a condição, a missão retorna automaticamente para `Em Andamento`.

### 36.3 Detalhe da Missão Principal

- Mostrar estado, `Missão Principal · Região`, lore/contexto, Objetivo, Local e Recompensas.
- `[Ver no Mapa]` pode existir tanto em `Em Andamento` quanto em `Suspensa` quando o Local for conhecido.
- Em `Suspensa`, mostrar a condição no bloco mecânico, sem criar página especial de erro.

### 36.4 Missões Secundárias

- Detalhe pode mostrar objetivo, Local, progresso contextual e recompensas.
- Preferir progresso semântico, por exemplo `🐺 Lobos Derrotados · 3/6`, em vez de barra genérica.
- `[Abandonar Missão]` aparece apenas quando aquela Missão Secundária permitir abandono.
- Abandono exige confirmação quando tiver consequência relevante.
- A tela de confirmação deve explicitar, conforme a regra daquela missão, se o progresso será `Reiniciado` ou `Preservado` e se a reaceitação permanecerá possível.
- Após abandono válido, retornar à lista de Missões; não criar tela de sucesso.
- Não criar lista permanente de “Missões Abandonadas” sem definição mecânica própria.

### 36.5 Missão Secundária acompanhada

- Uma Missão Secundária ativa pode ocupar o estado de acompanhamento da HUD.
- No detalhe de uma Missão Secundária elegível, usar `[Acompanhar]` quando ela ainda não for a acompanhada.
- Se já estiver acompanhada, a ação pode aparecer como `[Deixar de Acompanhar]`.
- Acompanhar outra Missão Secundária substitui a anterior sem alterar progresso, estado ou possibilidade de abandono.
- O acompanhamento é apenas referência de HUD; não transforma a Missão Secundária em Missão Principal.
- Quando a missão acompanhada deixar de estar ativa, sua linha desaparece da HUD.

---

## 37. Caçada — entrada e lobby

### 37.1 Região e Local

- Caçada normal usa **Região → Local**.
- Não listar inimigos como opções selecionáveis; o encontro é determinado pelo pool elegível do Local.
- Locais conhecidos e bloqueados permanecem visíveis sem botão, conforme o padrão do Mapa.

### 37.2 Preparação

Padrão aprovado:

```text
[Imagem contextual do Local]

🦌 Caçada

🔥 Estrada das Cinzas
Terras do Ocaso · Nv. 1–10

...

🗡️ [VLT] Luiken
❤️ 842 / 1.000
🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜
⚡ 72 / 100
🟨🟨🟨🟨🟨🟨🟨⬜⬜⬜

1 👤 Solo · Individual
2 👥 Grupo · Comunidade

[1] [2]
[← Terras do Ocaso]
```

- Em preparação/lobby, sempre mostrar **valor exato + barra** de HP e Vigor.
- Ordem por personagem: nome → HP exato → barra de HP → Vigor exato → barra de Vigor.
- Quadrado branco `⬜` representa a parte consumida/ausente da barra.
- HP restante usa 🟩, 🟨 ou 🟥 conforme a faixa visual de vida.
- Vigor restante usa 🟨.
- Valores e thresholds exatos de mudança de cor são responsabilidade do sistema/balanceamento quando não definidos.

### 37.3 Solo

- Selecionar `Solo` cria o encontro válido e entra diretamente no combate.
- Não usar tela intermediária `Encontro Encontrado` ou confirmação adicional.
- O `encounter_id` persistente impede reroll visual gratuito.

### 37.3.1 Desbloqueio inicial da Estrada e familiaridade da Ronda

Após P1, **Estrada das Cinzas** pode exibir:

`[Caçar] [Desbravar]`

mesmo se o personagem ainda estiver no Nv.1.

A Ronda local permanece bloqueada até a primeira vitória manual válida naquele Local:

`🔒 Ronda de Caça · Vença uma Caçada neste Local`

Após a primeira vitória manual válida, a mesma interface passa a oferecer a seleção do lote em lista numerada:

```text
1 🏕️ Ronda · 5 Encontros
2 🏕️ Ronda · 10 Encontros
3 🏕️ Ronda · 20 Encontros

[1] [2] [3]
```

Selecionar `[1]`, `[2]` ou `[3]` abre a preparação normal da Ronda já consolidada, com o tamanho escolhido refletido em `🎯 Ronda · {X} Encontros`. Não criar tela extra para “familiaridade adquirida”; apenas atualizar o estado da interface.

### 37.4 Grupo

- Lobby usa `👥 Grupo · x/4` e numeração dos membros.
- Cada membro mostra HP e Vigor no padrão de preparação.
- Pode usar `[Convidar]` e `[Iniciar Caçada]` quando válidos.
- Depois que o combate começa, remover numeração e `Grupo · x/4` da HUD de combate.
- Ninguém entra no meio de um encontro já iniciado.

---

## 38. Masmorras — entrada, dificuldade e formação

### 38.1 Lista de Masmorras Conhecidas

Cada Masmorra conhecida deve priorizar duas informações:

1. faixa de nível na mesma linha do nome;
2. `Região · Local` na linha abaixo.

Exemplo:

```text
1 🕯️ Cripta do Ocaso · Nv. 4–7
Terras do Ocaso · Charneca da Fuligem
```

- Não mostrar Masmorras secretas antes da descoberta.
- Não usar `???` para entradas ocultas.
- Na Fonte regional oficial: `Cripta do Ocaso · Nv. 4–7` e `Galerias do Vigia · Nv. 8–10`. Quando exemplos dessas Masmorras forem usados, preservar essas faixas.

### 38.2 Detalhe e dificuldade

Padrão aprovado:

```text
🕯️ Cripta do Ocaso · Nv. 4–7
Terras do Ocaso · Charneca da Fuligem

...

⚔️ Dificuldade

1 🟢 Estável · Disponível
2 🔒 Fraturada · Concluir Estável
3 🔒 Ruptura · Nv. 60

[1]
[← Masmorras]
```

- `🟢` representa Estável.
- `🟠` representa Fraturada quando a dificuldade estiver disponível; enquanto bloqueada, usar `🔒 Fraturada · Concluir Estável`.
- Fraturada exige Primeira Conclusão Estável.
- Ruptura exige Nv. 60 + Primeira Conclusão Fraturada; se o nível já estiver satisfeito mas faltar a conclusão, usar `🔒 Ruptura · Concluir Fraturada`.
- Quando Ruptura estiver bloqueada, usar `🔒` e não adicionar outro emoji de cor na mesma linha.
- Se o requisito objetivo for conhecido, preferir o requisito real (`Nv. 60`) a `Indisponível`.
- Se o bloqueio não puder ser resumido em um requisito objetivo, usar `Indisponível`.

### 38.3 Preparação

```text
[Imagem contextual da Masmorra]

⛓️ Cripta do Ocaso
Estável · Nv. 4–7

...

🗡️ [VLT] Luiken
❤️ 842 / 1.000
🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜
⚡ 72 / 100
🟨🟨🟨🟨🟨🟨🟨⬜⬜⬜

1 👤 Solo · Individual
2 👥 Grupo · Até 4 Jogadores
3 🔎 Pareamento · 2–4 Jogadores

[1] [2] [3]
[← Cripta do Ocaso]
```

- HP e Vigor aparecem na preparação e nos lobbies pré-run.
- Consumíveis de PvE manual **não exigem tela de preparação**; itens elegíveis no Inventário ficam disponíveis diretamente conforme as regras do conteúdo.

### 38.4 Grupo e Elegibilidade Preventiva

- Lobby usa `Grupo · x/4`, numeração, HP e Vigor completos.
- Convite de Masmorra mostra apenas jogadores elegíveis para a Masmorra/dificuldade selecionadas.
- Jogador inelegível não entra como membro inválido apenas para exibir erro no lobby.
- Pareamento também bloqueia preventivamente quem não cumprir os requisitos.
- Mudanças de elegibilidade posteriores são tratadas de forma contextual e revalidadas antes da `run_id`.

### 38.5 Pareamento e Confirmação de Entrada

Durante busca:

```text
🔎 Pareamento

👥 Formação · 2–4 Jogadores
⏳ Estado · Procurando

[Cancelar Pareamento]
```

- Enquanto o Pareamento for a atividade Foreground ativa, não é necessário botão de retorno concorrente; a ação relevante é cancelar o Pareamento quando permitido.

Na Confirmação de Entrada:

- mostrar `👥 Grupo · x/4`;
- cada participante mantém HP e Vigor de preparação;
- estado por membro pode usar `⏳ Aguardando` ou `✅ Confirmado`;
- o jogador local recebe `[Confirmar Entrada]` e `[Recusar]` enquanto ainda não respondeu;
- depois de confirmar, a tela passa a aguardar os demais;
- não usar outra tela de `[Continuar]` ou `[Iniciar]` depois que todos confirmarem;
- todos confirmados → revalidação final → reserva autoritativa → criação da `run_id` → entrada direta na Masmorra.

### 38.6 Braseiro de Masmorra

- Não antecipar na tela de entrada se a run possuirá Braseiro de Masmorra.
- A existência/ausência deve ser descoberta organicamente durante a run.
- Braseiro de Masmorra não integra a Travessia permanente.

---

## 39. Combate — atualização consolidada

Esta seção complementa e, quando houver conflito, substitui o item 23 deste documento.

### 39.1 Cabeçalho e combatente ativo

- Player-facing usa **`Turno X · Nome`**, sem emoji `⚔️` antes de `Turno`, e não `Rodada X · Nome`.
- `Nome` no cabeçalho funciona como metadado e deve permanecer em `monoespaçado`.
- `👉` marca o combatente que está agindo **na linha do próprio combatente**, nunca no cabeçalho.
- Personagens jogadores mantêm o **emoji da Classe** junto ao nome na linha do combatente, por exemplo `👉 🗡️ Nome`.
- Não mostrar nível nem nome textual da Classe dentro da HUD de combate.
- A palavra **Rodada** pode continuar existindo apenas quando tiver significado mecânico próprio no sistema; não deve ser usada como contador principal da HUD de ações do jogador.

### 39.2 Ordem visual

- Adversário/criatura aparece visualmente **acima** dos personagens jogadores.
- Um pequeno Flavor contextual pode aparecer entre o adversário e os jogadores quando houver espaço e valor narrativo.
- Durante combate ativo, informação mecânica tem prioridade; Flavor não pode deslocar HP, efeitos, turno ou ações essenciais.

### 39.3 HP e Vigor

- Em preparação/lobby: mostrar HP e Vigor com **valor exato + barra de 10 blocos**.
- Em combate: mostrar **HP exato + barra de HP**.
- **Vigor não aparece na HUD de combate.**
- `⬜` representa parte consumida/ausente.
- HP restante usa 🟩, 🟨 ou 🟥 conforme a faixa de vida.
- Vigor restante usa 🟨.

Exemplo de preparação:

```text
❤️ 842 / 1.000
🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜
⚡ 72 / 100
🟨🟨🟨🟨🟨🟨🟨⬜⬜⬜
```

### 39.4 Registro de Combate

Cabeçalho oficial:

```text
📜 Registro de Combate · Recentes
```

- `Recentes` em `monoespaçado`.
- Uma linha em branco após o cabeçalho.
- Entradas contínuas, sem espaço extra entre cada linha.
- Linguagem natural e curta.
- Cada entrada começa com emoji/ação apropriado.
- Nomes de personagens, criaturas e Artes em **negrito**.
- Valores de dano e números mecânicos em `monoespaçado`.
- Tags de Guilda podem ser omitidas dentro do log para preservar legibilidade.
- Textos de log usados em mockups são exemplos de conteúdo; o formato acima é a decisão consolidada.

### 39.5 Ações e Consumíveis

- No turno do jogador, a HUD pode oferecer `[Atacar]`, `[Defender]`, Artes disponíveis e `[Consumível]` quando válido.
- Em PvE manual, `[Consumível]` consulta apenas Consumíveis elegíveis presentes no **Inventário**; não abre Armazém, Mercado, Pending, Crafting ou outra fonte externa.
- Não existe preparação manual prévia de Consumíveis para PvE manual.
- A **Ronda de Caça** permanece exceção e usa preparação própria antes do lote.
- Em Masmorras, disponibilidade de Consumível respeita o limite de usos do jogador naquela `run_id`.
- Esse limite não reinicia entre encontros, wipe, Retry ou Braseiro de Masmorra.
- Ter unidades adicionais no Inventário não aumenta o orçamento de usos da run.
- `[Consumível]` aparece somente quando existir Consumível válido/elegível segundo as regras normais do contexto. Quando nenhum Consumível for elegível/utilizável ou o limite tiver sido esgotado, o botão não aparece; quando necessário, o contexto informa o motivo sem criar botão desabilitado.
- Poção de Vigor permanece fora de combate.
- PvP não exibe Consumíveis externos.
- A seleção `[Consumível]`, os fluxos de Proteção/Dissipador/Resguardo, HUD, Registro, revalidação e retornos semânticos são detalhados autoritativamente na seção 59.

---

## 40. Menu Principal — dashboard definitivo

O Menu Principal é o hub global player-facing de Asterion. Ele é uma exceção consciente ao alvo geral de aproximadamente 4–8 ações por tela e **não usa hub `[Mais]`** para esconder entradas aprovadas.

### 40.1 Estrutura e HUD

Padrão aprovado:

```text
[Imagem contextual de Asterion]

🌑 Asterion
Terras do Ocaso · Estrada das Cinzas

Sob céus cobertos de fuligem, as estradas de Asterion seguem marcadas por ruínas, brasas antigas e promessas que nunca repousam por completo. Mesmo nos caminhos mais silenciosos, cada passo ainda parece ecoar a memória de algo que o mundo não conseguiu esquecer.

🗡️ [VLT] Luiken · Nv. 11
Errante · Sabotador

❤️ HP · 842 / 1.000
🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜
⚡ Vigor · 72 / 100
🟨🟨🟨🟨🟨🟨🟨⬜⬜⬜
✨ XP · 15.560 / 18.696
🟦🟦🟦🟦🟦🟦🟦🟦⬜⬜

📜 Missão Principal · [NOME DA MISSÃO PRINCIPAL]
📖 Missão Secundária · Luzes sob as Cinzas
🌌 Objetivo da Crônica · Ecos da Convergência

🌍 Evento Mundial · 17%
🟧🟧⬜⬜⬜⬜⬜⬜⬜⬜

[Aventura] [Personagem]
[Guilda] [Mercado]
[Códice] [Calendário]
[Vínculos] [Classificação]
[Benefícios] [Comunidade]
[Configurações]
```

Regras:

- O cabeçalho usa **`🌑 Asterion`**, com apenas o `A` maiúsculo no texto player-facing.
- A linha seguinte mostra `Região · Local` atuais.
- A lore do Menu pode ser mais trabalhada do que Flavor sistêmico curto, desde que permaneça legível e não desloque o estado essencial do personagem.
- Mostrar nome, tag de Guilda quando aplicável, nível, Classe e Caminho.
- HP, Vigor e XP usam valor exato + barra de 10 blocos.
- HP segue 🟩/🟨/🟥 conforme faixa; Vigor usa 🟨; XP usa 🟦; `⬜` representa parte faltante/consumida.
- As barras são derivadas dinamicamente dos valores reais persistidos. O renderer vigente é responsável pelo preenchimento/arredondamento visual; a quantidade de blocos exibida em um mockup não cria regra mecânica independente. Os valores numéricos são a fonte mecânica de referência.
- O ícone oficial de XP permanece **✨**, mesmo quando sua barra utiliza blocos azuis.
- A HUD pode mostrar a **Missão Principal** pelo nome, sem acrescentar `Suspensa` na linha do Menu. O estado completo e seu requisito pertencem à tela de Missões.
- A HUD mostra no máximo uma **Missão Secundária acompanhada**. Sem missão acompanhada, a linha desaparece.
- `Objetivo da Crônica` aparece apenas quando houver objetivo pessoal/relevante aplicável ao personagem.
- `Evento Mundial` e sua barra aparecem apenas quando houver Evento Mundial ativo/relevante para o contexto. Não manter bloco vazio ou `0%` sem função.
- O Menu apresenta contexto; não substitui as telas detalhadas de Missões, Crônica ou Eventos Mundiais.

### 40.2 Entradas diretas

Entradas definitivas:

- Aventura;
- Personagem;
- Guilda;
- Mercado;
- Códice;
- Calendário;
- Vínculos;
- Classificação da Vigília;
- Benefícios;
- Comunidade;
- Configurações.

Na grade de botões, **Classificação da Vigília** pode usar o rótulo curto `[Classificação]` por limitação de espaço, sem alterar o nome oficial da seção.

---

## 41. Vínculos — fluxo consolidado

### 41.1 Raiz

```text
[Imagem contextual de Vínculos]

🤝 Vínculos

Companheiros encontrados ao longo da jornada podem permanecer próximos mesmo quando seus caminhos seguem por regiões diferentes.

🤝 Amigos · 12/100
📩 Pedidos · 2
🕘 Recentes · Jogadores Encontrados
🚫 Bloqueados · 3
🔎 Buscar Jogador · Nome

[Amigos] [Pedidos]
[Recentes] [Bloqueados]
[Buscar Jogador]

[← Menu]
```

- Valores quantitativos usados no exemplo permanecem `SIMULAR` quando não definidos pela Fonte Mestra.
- Não inventar presença `Online/Offline` sem regra estrutural correspondente.

### 41.2 Amigos

Lista compacta:

```text
1 🛡️ [NOM] Aster · Nv. 28
Sentinela · Bastião
```

Ao abrir um amigo, usar o Perfil público:

```text
[Imagem contextual do personagem]

📇 [NOM] Aster · Nv. 28

🛡️ Sentinela · Bastião
🕯️ Raça · Remanescente
🏛️ Legado · Legado I
🛡️ Guilda · [NOM] Nômades
🎖️ Título · Vigia das Cinzas
🏅 Elo · Forjado

🏆 Feitos · Consultar
📜 História do Personagem · Consultar

[Feitos] [História]
[Remover Amigo]

[← Amigos]
```

- História só aparece quando existir conteúdo válido.
- Doutrinas permanecem ocultas por padrão no Perfil público.
- `[Remover Amigo]` fica no detalhe, não na listagem.

### 41.3 Pedidos

Lista usa nome, nível e Classe/Caminho. O detalhe reutiliza o Perfil público e oferece:

```text
[Aceitar] [Recusar]
[← Pedidos]
```

- Aceitar ou recusar não cria tela de sucesso intermediária.

### 41.4 Recentes

- Lista jogadores encontrados recentemente em atividades elegíveis, sem inventar janela temporal/limite quando não definidos.
- O detalhe reutiliza o Perfil público e pode oferecer `[Adicionar Amigo]`.
- Se já for amigo, a ação não aparece.

### 41.5 Bloqueados

Lista compacta de jogadores bloqueados. No detalhe, reduzir exposição social desnecessária e priorizar o estado:

```text
🚫 Vínculo · Bloqueado

[Desbloquear]
[← Bloqueados]
```

- Não exigir confirmação para desbloquear.

### 41.6 Buscar Jogador

Tela inicial:

```text
🔎 Buscar Jogador

Digite o nome do personagem que deseja encontrar.

[← Vínculos]
```

Resultados usam nome, nível e Classe/Caminho. Ao abrir um resultado, reutilizar Perfil público e oferecer `[Adicionar Amigo]` quando aplicável.

- Busca player-facing é pelo nome do personagem.
- Não expor Telegram ID, telefone, username privado ou outro identificador sensível.
- Se houver vínculo/estado pré-existente, as ações devem respeitá-lo; não oferecer amizade a jogador bloqueado nem duplicar pedido válido.

---

## 42. Classificação da Vigília — fluxo consolidado

### 42.1 Raiz

A **Classificação da Vigília** é entrada direta do Menu Principal; não criar hub player-facing `Rankings`.

```text
[Imagem contextual da Arena da Vigília]

🏆 Classificação da Vigília

🌌 Crônica Atual · SIMULAR

Os nomes que mais se destacam na Vigília permanecem registrados enquanto o ciclo competitivo estiver em andamento.

🏅 Posição Atual

🗡️ [VLT] Luiken · #128
Forjado II · 1.842 Renome

🏆 Destaques da Vigília

1 👑 [ARC] Vaelor
Regente · 3.920 Renome

2 ⚔️ [NOM] Seris
Arauto I · 3.714 Renome

3 🛡️ [FER] Kael
Arauto I · 3.680 Renome

[Minha Posição]
[Salão da Vigília]

[← Menu]
```

- Usar **Posição Atual**, não `Sua Classificação` ou `Sua Posição`.
- Exibir Renome + Elo; MMR permanece oculto.
- Nomes, valores e Crônica usados em mockups permanecem `SIMULAR` quando não definidos.

### 42.2 Minha Posição

Mostrar um recorte local da classificação ao redor do personagem:

```text
🏅 Posição Atual

#127 🛡️ [NOM] Aster
Forjado II · 1.849 Renome

👉 #128 🗡️ [VLT] Luiken
Forjado II · 1.842 Renome

#129 🔮 Elyra
Forjado II · 1.836 Renome

[Ver Topo]
[← Classificação da Vigília]
```

- `👉` identifica imediatamente o próprio personagem no recorte.
- `[Ver Topo]` retorna às primeiras posições da classificação atual.

---

## 43. Salão da Vigília — histórico competitivo

O **Salão da Vigília** é acessado a partir da Classificação da Vigília e preserva o histórico aplicável de Crônicas encerradas.

### 43.1 Raiz

```text
[Imagem contextual do Salão da Vigília]

🏛️ Salão da Vigília

Quando uma Crônica termina, os nomes gravados na Vigília permanecem como testemunho daqueles que alcançaram suas maiores posições.

📜 Crônicas Encerradas

1 🌌 Crônica da Ruptura · 20/06/2026
2 🌑 Crônica do Ocaso · 14/03/2026
3 🔥 Crônica das Cinzas · 07/12/2025

[1] [2] [3]

[← Classificação da Vigília]
```

### 43.2 Crônica encerrada

```text
[Imagem contextual da Crônica]

🌌 Crônica da Ruptura
Encerrada · 20/06/2026

🏆 Classificação Final

1 👑 [ARC] Vaelor
Regente · 3.920 Renome

2 ⚔️ [NOM] Seris
Arauto I · 3.714 Renome

3 🛡️ [FER] Kael
Arauto I · 3.680 Renome

🏅 Posição Final

🗡️ [VLT] Luiken · #128
Forjado II · 1.842 Renome

[Ver Posição]

[← Salão da Vigília]
```

- Datas usam `DD/MM/AAAA`.
- `Classificação Final` mostra o topo do snapshot; `Posição Final` mostra o personagem consultante quando houver dado aplicável.
- `[Ver Posição]` abre o recorte histórico ao redor da posição final do personagem.
- MMR não é exibido no histórico.

---

## 44. Convenções finais de apresentação e navegação

- Nome player-facing do jogo em títulos comuns: **Asterion**.
- Data player-facing: **`DD/MM/AAAA`**.
- **Comunidade** permanece entrada direta do Menu Principal e não pertence a Configurações.
- **Classificação da Vigília** permanece entrada direta; **Salão da Vigília** é filho dessa seção.
- A raiz da Classificação aberta pelo Menu usa `[← Menu]`; retornos internos usam o pai conhecido.
- **Perfil** pertence ao hub Personagem.
- O Menu Principal pode exceder 8 ações por ser o hub global; não criar `[Mais]` para esconder entradas aprovadas.
- Missão Secundária acompanhada é representada na HUD por uma única linha; o estado detalhado continua nas telas de Missões.
- Não reabrir sistemas já declarados fechados apenas para criar telas intermediárias sem decisão real.

---

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

### 45.5 Prólogo — abertura

**Cinzas na Estrada** é o nome do **Prólogo**. Não confundir com a primeira Missão Principal regional, **P1 — Vozes na Estrada**, definida pela Fonte de Conteúdo Terras do Ocaso v1.0.4 FINAL.

```text
[Imagem contextual da Estrada das Cinzas]

🔥 Cinzas na Estrada
Prólogo · Terras do Ocaso

O mundo desperta sob um céu sem cor. Cinzas atravessam a estrada como neve morta, cobrindo pedras, árvores retorcidas e os restos de algo que um dia talvez tenha sido um caminho seguro. À frente, entre a névoa e o silêncio, formas quebradas marcam a direção de sua primeira jornada.

[Seguir pela Estrada]
```

### 45.6 Prólogo — Ataque e Defender

O primeiro encontro usa a HUD normal de combate, mas aplica uma máscara pedagógica temporária às ações disponíveis. O **Cão Cinéreo oficial possui 244 HP Máximo**. HP do personagem e HP atual do inimigo são sempre lidos do estado autoritativo real; os marcadores entre chaves abaixo representam valores dinâmicos do renderer e **nunca aparecem literalmente ao jogador**.

```text
[Imagem contextual do encontro]

Turno 1 · Luiken

🐺 Cão Cinéreo
❤️ 244 / 244
🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩

Um rosnado rompe o silêncio da estrada. Entre as cinzas, uma criatura faminta avança para impedir sua passagem.

👉 🗡️ Luiken
❤️ {HP atual} / {HP máximo}
🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩

📜 Registro de Combate · Recentes

🐺 Cão Cinéreo bloqueia o caminho.

⚔️ Atacar · Causa Dano
🛡️ Defender · Reduz Dano até seu próximo Turno

[Atacar] [Defender]
```

- Durante o prólogo, o personagem ainda não possui tag de Guilda.
- Em combate, não acrescentar nível nem nome textual da Classe ao lado do personagem; o emoji da Classe faz a identificação visual.
- No primeiro turno, `[Atacar]` e `[Defender]` aparecem simultaneamente.
- Depois que o jogador usa uma das duas ações, a outra passa a ser a **única ação pedagógica válida** na oportunidade seguinte.
- Após **Atacar**, o Cão responde com **Mordida Cinérea · 100% ATQ**. Após **Defender**, responde com **Investida Cinérea · 120% ATQ**, para demonstrar a mitigação.
- As linhas explicativas de Atacar/Defender são temporárias e desaparecem depois que ambos os conceitos tiverem sido usados.
- HP e barras devem ser derivados do estado de combate; não armazenar números de mockup como estado autoritativo.

### 45.7 Prólogo — primeira Arte

Depois que **Atacar e Defender** tiverem sido usados ao menos uma vez, o tutorial apresenta a primeira Arte desbloqueada da Classe escolhida dentro da própria HUD de combate; não criar popup intermediário. Durante esta oportunidade pedagógica, somente essa primeira Arte fica disponível como ação necessária.

Exemplo para Errante; os marcadores entre chaves são valores dinâmicos do renderer e não aparecem literalmente ao jogador:

```text
Turno 3 · Luiken

🐺 Cão Cinéreo
❤️ {HP atual} / 244
{barra de HP real}

...

👉 🗡️ Luiken
❤️ {HP atual} / {HP máximo}
{barra de HP real}

📜 Registro de Combate · Recentes

...

🎴 Corte Veloz · Arte de Classe
⚔️ Dano · 115% ATQ
⏳ Recarga · 2

[Corte Veloz]
```

- A Arte exibida depende da Classe escolhida.
- O exemplo acima usa **Errante → Corte Veloz** e não transforma esse nome em regra universal do prólogo.
- O HP do Cão neste momento é **dinâmico** e depende das ações e resultados reais anteriores; não usar `132 / 240` nem outro valor fixo de mockup.
- Após o primeiro uso válido da Arte, a máscara pedagógica termina; sua explicação temporária some e a HUD passa imediatamente às regras normais de combate.
- Se a Arte derrotar o Cão, o combate termina normalmente antes de qualquer resposta inimiga. Se ele permanecer vivo, a IA normal determinística começa em **Mordida** e segue `Mordida → Mordida → Investida → repetir`.

### 45.8 Prólogo — primeiro Braseiro

```text
[Imagem contextual do Braseiro]

🔥 Braseiro
Estrada das Cinzas · Terras do Ocaso

Entre pedras escurecidas pela fuligem, uma chama permanece acesa onde tudo ao redor parece ter sido abandonado. Seu calor atravessa o silêncio da estrada e oferece, pela primeira vez, um lugar seguro para recuperar as forças.

🔥 Braseiro · Descoberto
❤️ Descansar · Restaura HP

ℹ️ Braseiros permanentes podem servir para descanso e, quando outros forem descobertos, conectar diferentes pontos de Asterion através da Travessia dos Braseiros.

[Descansar]
```

- Não exigir `[Ativar Braseiro]` nessa introdução.
- `[Descansar]` restaura o HP conforme as regras autoritativas do Braseiro.
- Não criar segunda tela de “Braseiro ativado”.

#### Resolução do encontro tutorial

Vitória e Derrota válidas no primeiro combate concluem o Prólogo e levam à mesma tela/estado já existente do Braseiro da Estrada. A Derrota não cria tela de retry, recovery, game over, confirmação, Reviver ou segundo combate. O Registro/resultado normal pode comunicar a Derrota; o próximo estado navegável é o Braseiro.

A Vitória concede 320 XP; a Derrota concede 0 XP. Ambas mantêm 0 Coroas, nenhum Saque, nenhum Material e 0 Vigor. Não existe penalidade econômica adicional nem perda de progresso, itens ou recursos anteriores. [Descansar] continua sendo a ação normal do Braseiro e usa as regras vigentes de restauração.

Depois da resolução válida, o combate não permanece ativo. Reconnect, /start, /menu e troca de dispositivo reconstroem o estado pós-encontro; callbacks antigos não podem ressuscitar o combate. P1 inicia normalmente após a conclusão do Prólogo em qualquer dos resultados. Esta regra é exclusiva do encontro tutorial: a Etapa 3 de P1 continua exigindo Vitória e mantém seu próprio recovery/retry.

### 45.9 Primeiro Menu Principal

Depois do Braseiro e do fechamento do tutorial, apresentar o Menu Principal já no padrão definitivo de dashboard. Com a sincronização regional v1.0.4, **P1 — Vozes na Estrada já está automaticamente ativa** neste momento e deve aparecer na HUD, tanto após Vitória quanto após Derrota no Prólogo.

O exemplo abaixo representa Vitória no Prólogo. Após Derrota, o XP inicial esperado é 0 / 4.800; o renderer sempre exibe o valor persistido real.

```text
[Imagem contextual de Asterion]

🌑 Asterion
Terras do Ocaso · Estrada das Cinzas

Sob céus cobertos de fuligem, as estradas de Asterion seguem marcadas por ruínas, brasas antigas e promessas que nunca repousam por completo. Mesmo nos caminhos mais silenciosos, cada passo ainda parece ecoar a memória de algo que o mundo não conseguiu esquecer.

{emoji da Classe} {Personagem} · Nv. 1
{Classe}

❤️ HP · {HP atual} / {HP máximo}
{barra de HP derivada do valor real}
⚡ Vigor · {Vigor atual} / {Vigor máximo}
{barra de Vigor derivada do valor real}
✨ XP · 320 / 4.800
{barra azul de XP derivada do valor real}

📜 Missão Principal · Vozes na Estrada

[Aventura] [Personagem]
[Guilda] [Mercado]
[Códice] [Calendário]
[Vínculos] [Classificação]
[Benefícios] [Comunidade]
[Configurações]
```

- O exemplo mostra o caminho de Vitória: após Vitória, normalmente 320 / 4.800; após Derrota, normalmente 0 / 4.800. O renderer usa sempre o XP persistido real.
- A barra de XP é azul e derivada dinamicamente do valor numérico real; este mockup não fixa uma regra independente de arredondamento/preenchimento.
- HP e Vigor seguem o mesmo princípio: valores reais persistidos são autoritativos e o renderer deriva as barras.
- Não inventar Missão Secundária, Objetivo da Crônica ou Evento Mundial apenas para preencher a HUD inicial.
- P1 inicia automaticamente após a conclusão válida do Prólogo, em Vitória ou Derrota; a conclusão, e não a vitória no tutorial, é o requisito.
- Depois desse ponto, o personagem passa a usar a navegação normal do jogo.

---

## 46. P1 — Vozes na Estrada · Visual/UI FINAL

Esta seção formaliza exclusivamente a apresentação player-facing implementável de **P1 — Vozes na Estrada**, em sincronização com `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.5_FINAL.md`.

Não altera conteúdo, balanceamento, narrativa, recompensas, ordem das sete etapas, regras regionais ou mecânicas globais. P1 continua semanticamente idêntica. Em caso de conflito de conteúdo, prevalece a Fonte regional v1.0.5; em caso de conflito estrutural, prevalece a Fonte Mestra v1.4.7.

### 46.1 Natureza das telas de P1

As telas abaixo são **telas contextuais de execução de P1**:

- Seguir pela Estrada;
- Pegadas na Cinza;
- Sulcos Recentes;
- chegada ao Refúgio do Ocaso;
- Alda Veyr;
- Oren Cal;
- Braseiro do Refúgio.

Elas permanecem enxutas e não precisam repetir Local e Recompensas em cada etapa.

O **detalhe oficial da Missão Principal**, aberto em `Aventura → Missões → [Principal]`, é uma tela distinta e completa. Ele apresenta estado, `Missão Principal · Terras do Ocaso`, lore/contexto pertinente, Objetivo atual, Local pertinente e Recompensas.

O fluxo contextual preservado é:

`Seguir pela Estrada → Pegadas na Cinza → Sulcos Recentes → combate direto → Refúgio do Ocaso → Alda Veyr → Oren Cal → Braseiro do Refúgio → conclusão de P1`.

### 46.2 Menu Principal antes de executar P1

P1 inicia automaticamente após a conclusão válida do Prólogo, independentemente de Vitória ou Derrota. O primeiro Menu Principal pós-Prólogo já deve refletir esse estado autoritativo.

O exemplo abaixo representa Vitória no Prólogo; após Derrota, normalmente será exibido 0 / 4.800. A UI deve sempre usar o XP persistido real.

```text
[Imagem contextual de Asterion]

🌑 Asterion
Terras do Ocaso · Estrada das Cinzas

Sob céus cobertos de fuligem, as estradas de Asterion seguem marcadas por ruínas, brasas antigas e promessas que nunca repousam por completo. Mesmo nos caminhos mais silenciosos, cada passo ainda parece ecoar a memória de algo que o mundo não conseguiu esquecer.

{emoji da Classe} {Personagem} · Nv. 1
{Classe}

❤️ HP · {HP atual} / {HP máximo}
{barra de HP derivada do valor real}

⚡ Vigor · {Vigor atual} / {Vigor máximo}
{barra de Vigor derivada do valor real}

✨ XP · 320 / 4.800
{barra azul de XP derivada do valor real}

📜 Missão Principal · Vozes na Estrada

[Aventura] [Personagem]
[Guilda] [Mercado]
[Códice] [Calendário]
[Vínculos] [Classificação]
[Benefícios] [Comunidade]
[Configurações]
```

- O exemplo representa Vitória: após Vitória, normalmente 320 / 4.800; após Derrota, normalmente 0 / 4.800. O renderer usa sempre o valor persistido real.
- As barras de HP, Vigor e XP são derivadas dinamicamente dos respectivos valores reais. O renderer vigente define o preenchimento visual; blocos mostrados em mockups não criam regra independente de arredondamento.
- Não inventar Missão Secundária, Objetivo da Crônica ou Evento Mundial para preencher a HUD.

### 46.3 Raiz de Missões

```text
[Imagem contextual da jornada]

📜 Missões

Objetivos, promessas e caminhos ainda inacabados acompanham sua jornada por Asterion.

🔥 Missão Principal

📜 Vozes na Estrada · Em Andamento
Terras do Ocaso · Nv. 1–10

[Principal]

[← Aventura]
```

- `[Principal]` abre o **detalhe oficial completo** de `Vozes na Estrada`.
- Não abrir diretamente uma tela contextual ao pressionar `[Principal]`.
- Se não houver Missões Secundárias ativas, não mostrar bloco vazio de Secundárias.

### 46.4 Detalhe oficial de Vozes na Estrada

Padrão inicial:

```text
[Imagem contextual da Estrada das Cinzas]

📜 Vozes na Estrada · Em Andamento
Missão Principal · Terras do Ocaso

A chama deixada para trás desaparece pouco a pouco entre a fuligem. A Estrada das Cinzas segue adiante, irregular e silenciosa, mas desta vez há marcas recentes onde antes havia apenas abandono.

🎯 Objetivo · Seguir pela Estrada das Cinzas

📍 Estrada das Cinzas · Terras do Ocaso

🎁 Recompensas

✨ XP · 2.400
🪙 Coroas · 120
⛏️ Ferro de Fuligem · 1
🐾 Couro Escoriado · 1

[Ver Objetivo]
[Ver no Mapa]

[← Missões]
```

Regras:

- O detalhe oficial sempre reflete o **estado autoritativo atual** de P1.
- Contexto, Objetivo e Local pertinente são atualizados conforme o estado persistido; Recompensas permanecem as autoritativas acima.
- `[Ver Objetivo]` é **navegação pura**. Abre a tela contextual correspondente ao estado atual e não registra progresso, não conclui Etapa, não cria atividade, não cria encounter e não funciona como `[Continuar]` genérico.
- Se o estado atual for a tela de recovery após Derrota já resolvida, `[Ver Objetivo]` reconstrói a tela de **💀 Derrota / Braseiro da Estrada**.
- `[Ver no Mapa]` aparece somente quando o Local pertinente já for conhecido.
- Na chegada ao Refúgio, o Local pode ser mencionado no detalhe/contexto, mas `[Ver no Mapa]` permanece ausente até a descoberta permanente do Refúgio ser validada na Etapa 4.
- Não é obrigatório oferecer no detalhe uma ação que progrida a Missão. Se uma ação contextual válida além de `[Ver Objetivo]` for usada futuramente, ela deve corresponder diretamente a uma ação já definida para o estado atual; nunca criar `[Continuar]` genérico.

Objetivos por estado:

| Estado persistido | Objetivo player-facing | Local pertinente |
|---|---|---|
| Etapa 1 | `Seguir pela Estrada das Cinzas` | Estrada das Cinzas |
| Etapa 2 · nenhum sinal | `Examinar Sinais · 0/2` | Estrada das Cinzas |
| Etapa 2 · Pegadas examinadas | `Examinar Sinais · 1/2` | Estrada das Cinzas |
| Etapa 3 · tentativa ativa | `Sobreviver ao encontro na Estrada` | Estrada das Cinzas |
| Etapa 3 · derrota resolvida | `Sobreviver ao encontro na Estrada` | Estrada das Cinzas |
| Etapa 4 | `Alcançar o Refúgio do Ocaso` | Refúgio do Ocaso |
| Etapa 5 | `Falar com Alda Veyr` | Refúgio do Ocaso |
| Etapa 6 | `Conhecer Oren Cal` | Refúgio do Ocaso |
| Etapa 7 | `Ativar o Braseiro do Refúgio` | Refúgio do Ocaso |

### 46.5 Tela contextual — Seguir pela Estrada

```text
[Imagem contextual da Estrada das Cinzas]

📜 Vozes na Estrada · Em Andamento
Missão Principal · Terras do Ocaso

A chama deixada para trás desaparece pouco a pouco entre a fuligem. A Estrada das Cinzas segue adiante, irregular e silenciosa, mas desta vez há marcas recentes onde antes havia apenas abandono.

🎯 Objetivo · Seguir pela Estrada das Cinzas

[Seguir pela Estrada]

[Ver no Mapa]
[← Missões]
```

- `[Seguir pela Estrada]` registra validamente a Etapa 1 e abre **Pegadas na Cinza**.
- Reconnect antes do commit reconstrói esta tela; após o commit, não retrocede para ela.

### 46.6 Tela contextual — Pegadas na Cinza

```text
[Imagem contextual das pegadas]

📜 Vozes na Estrada · Em Andamento
Missão Principal · Terras do Ocaso

👣 Pegadas na Cinza

Marcas de botas cortam a fuligem em uma única direção. As bordas ainda estão nítidas demais para terem permanecido ali por muito tempo.

🎯 Objetivo · Examinar Sinais · 0/2

[Examinar]

[← Missões]
```

- `[Examinar]` registra de forma idempotente o primeiro sinal.
- Após o commit válido, abre diretamente **Sulcos Recentes**.
- Sinal já examinado permanece examinado em reconnect/reconstrução.

### 46.7 Tela contextual — Sulcos Recentes

```text
[Imagem contextual dos sulcos]

📜 Vozes na Estrada · Em Andamento
Missão Principal · Terras do Ocaso

🛞 Sulcos Recentes

Duas marcas estreitas atravessam a cinza ao lado das pegadas. A fuligem ainda não voltou a cobrir completamente os sulcos deixados pelas rodas.

🎯 Objetivo · Examinar Sinais · 1/2

[Examinar]

[← Missões]
```

- O segundo `[Examinar]` registra idempotentemente o segundo sinal e conclui a Etapa 2.
- Depois do segundo commit válido, o encontro da Etapa 3 começa **diretamente**.
- Não inserir `[Seguir]`, `[Enfrentar]`, `[Iniciar Combate]` ou qualquer confirmação intermediária.

### 46.8 Entrada narrativa e combate da Etapa 3

A entrada narrativa é apresentada em um único parágrafo no primeiro render do encontro:

```text
Os sulcos desaparecem onde a estrada se estreita entre pedras partidas. Antes que você possa seguir as marcas, um rosnado baixo rompe o silêncio. Um Cão Cinéreo emerge da fuligem e fecha a passagem.

Turno 1 · {Personagem}

🐺 Cão Cinéreo
❤️ {HP atual} / {HP máximo}
{barra de HP}

[…]

👉 {emoji da Classe} {Personagem}
❤️ {HP atual} / {HP máximo}
{barra de HP}

📜 Registro de Combate · Recentes

[…]

[Atacar] [Defender]
[Artes válidas…]
[Consumível]
```

Regras específicas:

- O cabeçalho permanece **`Turno X · {Personagem}`**, sem `⚔️` antes de `Turno`.
- `👉` permanece na linha do combatente ativo.
- O personagem usa o emoji da Classe junto ao nome.
- Não mostrar nível nem nome textual da Classe dentro da HUD de combate.
- O inimigo é sempre **🐺 Cão Cinéreo · Nv.1 · Comum · Solo · sem Variante**.
- Não consultar o pool normal de Caçada para selecionar o inimigo.
- O combate é normal e não usa máscara pedagógica; desde a primeira oportunidade, todas as ações atualmente válidas são apresentadas.
- `[Consumível]` aparece **somente** quando existir Consumível válido/elegível segundo as regras normais de PvE manual. Se não houver Consumível elegível, o botão não aparece.
- A linha `[Artes válidas…]` representa as Artes realmente disponíveis ao personagem; não é rótulo literal de botão.
- Depois da primeira ação, a entrada narrativa pode sair e a HUD permanece no padrão normal de combate.
- Vitória é a condição autoritativa para concluir a Etapa 3. Derrota não conclui a etapa.

### 46.9 Derrota e recovery no Braseiro da Estrada

Quando a Derrota é validamente resolvida, o encontro atual termina; P1 permanece ativa na Etapa 3.

```text
[Imagem contextual do Braseiro da Estrada]

💀 Derrota

🔥 Braseiro da Estrada
Estrada das Cinzas · Terras do Ocaso

❤️ HP · Restaurado

📜 Vozes na Estrada · Em Andamento

Recuperado no Braseiro da Estrada, você precisará retornar ao encontro e vencê-lo antes de seguir viagem.

[Retornar à Estrada]

[← Menu]
```

Apresentação:

- A frase contextual de recovery é *lore/contexto* e deve ser renderizada em itálico.
- `💀` é o marcador de Derrota; não usar `⚠️` nesse estado.

Efeitos e ações:

- Aplicar recovery normal do Braseiro da Estrada: HP a `100%` e estados comuns de combate removidos.
- Vigor não é restaurado.
- Consumíveis realmente utilizados permanecem consumidos.
- `[Retornar à Estrada]` retorna ao gatilho narrativo da Etapa 3 e cria a nova tentativa prevista pela Fonte regional.
- A nova tentativa recebe nova identidade de encontro e materializa novamente **🐺 Cão Cinéreo · Nv.1**, com HP integral.
- Não rerrolar criatura nem Variante.

### 46.10 Tela contextual — chegada ao Refúgio do Ocaso

Após vitória válida contra o Cão:

```text
[Imagem contextual do Refúgio do Ocaso]

📜 Vozes na Estrada · Em Andamento
Missão Principal · Terras do Ocaso

🏚️ Refúgio do Ocaso

Mais adiante, a estrada deixa de ser apenas ruína. Pedras empilhadas, madeira reaproveitada e pontos de luz surgem através da fuligem.

Não é uma cidade. Ainda assim, pela primeira vez desde que despertou na estrada, há sinais claros de que pessoas permanecem aqui.

🎯 Objetivo · Alcançar o Refúgio do Ocaso

[Entrar no Refúgio]

[← Missões]
```

- `[Entrar no Refúgio]` valida a chegada e registra **Refúgio do Ocaso** como Local descoberto permanentemente.
- Esse registro ocorre antes da conversa com Alda.
- Antes desse commit, o Refúgio não deve aparecer como Local conhecido no Mapa.
- Após esse commit, reconnect/reconstrução não repetem a descoberta e seguem para Alda quando ela ainda estiver pendente.

### 46.11 Tela contextual — Alda Veyr

```text
[Imagem contextual de Alda Veyr]

🪖 Alda Veyr

Uma mulher observa a estrada antes mesmo de olhar para você. Sua atenção passa primeiro pelas marcas da fuligem, depois por suas armas e só então pelo seu rosto.

— Se chegou até aqui sozinho, já aprendeu a primeira regra do Ocaso: estrada nenhuma permanece segura só porque alguém a chamou de estrada.

Ela explica que o Refúgio sobrevive mantendo rotas, recursos e vigias funcionando.

🎯 Objetivo · Falar com Alda Veyr

[Seguir a Indicação]

[← Missões]
```

Apresentação:

- O nome da NPC aparece uma única vez no cabeçalho; não repetir `Alda Veyr:` no corpo.
- A fala direta usa travessão e é renderizada em itálico, sem aspas.
- Descrição/contexto ao redor da fala também segue o padrão de lore em itálico.

Ação:

- `[Seguir a Indicação]` conclui validamente a primeira conversa obrigatória.
- Alda Veyr é registrada em `Códice → Figuras` de forma idempotente.
- Depois do commit, abrir Oren Cal.

### 46.12 Tela contextual — Oren Cal

```text
[Imagem contextual de Oren Cal]

✒️ Oren Cal

Alda indica um homem cercado por folhas, tábuas riscadas e fragmentos trazidos das estradas. Ele organiza cada peça como se perder uma palavra fosse tão grave quanto perder uma pessoa.

— Se ouvir nomes no vento, não os descarte depressa. Há coisas nestas terras que sobrevivem apenas porque alguém se lembra delas.

Ele registra relatos, nomes e inscrições trazidos das estradas.

🎯 Objetivo · Conhecer Oren Cal

[Ir ao Braseiro]

[← Missões]
```

Apresentação:

- O nome da NPC aparece uma única vez no cabeçalho; não repetir `Oren Cal:` no corpo.
- A fala direta usa travessão e é renderizada em itálico, sem aspas.
- Descrição/contexto ao redor da fala também segue o padrão de lore em itálico.

Ação:

- `[Ir ao Braseiro]` conclui validamente a apresentação obrigatória.
- Oren Cal é registrado em `Códice → Figuras` de forma idempotente.
- Depois do commit, abrir o Braseiro do Refúgio.

### 46.13 Tela contextual — Braseiro do Refúgio

```text
[Imagem contextual do Braseiro do Refúgio]

🔥 Braseiro do Refúgio
Refúgio do Ocaso · Terras do Ocaso

No centro do Refúgio, uma chama resiste entre pedras marcadas pelo uso. Pessoas passam por ela sem cerimônia, mas nenhuma ignora completamente sua presença.

O calor é constante. Pela primeira vez, a estrada atrás de você parece ter um ponto de retorno.

🎯 Objetivo · Ativar o Braseiro do Refúgio

[Ativar Braseiro]

[← Missões]
```

- `[Ativar Braseiro]` registra **Braseiro do Refúgio** como Braseiro permanente descoberto e utilizável.
- O registro é idempotente e ocorre antes do commit final de P1.
- **Ativar Braseiro não significa Descansar.** A ativação, por si só, não restaura HP.
- Vigor não é restaurado.
- Somente `[Descansar]`, quando acionado, aplica a restauração normal de HP do Braseiro.

### 46.14 Conclusão de P1 na própria tela do Braseiro

Após a interação válida com `[Ativar Braseiro]`, o Braseiro é registrado e P1 é concluída atomicamente com suas recompensas e desbloqueios autoritativos. Não criar segunda tela separada de “Missão Concluída”.

A mesma mensagem é atualizada para:

```text
[Imagem contextual do Braseiro do Refúgio]

🔥 Braseiro do Refúgio
Refúgio do Ocaso · Terras do Ocaso

O calor é constante. Pela primeira vez, a estrada atrás de você parece ter um ponto de retorno.

🔥 Braseiro · Descoberto
❤️ Descansar · Restaura HP

✅ Vozes na Estrada · Concluída

[Descansar]

[← Menu]
```

- A conclusão concede uma única vez: `2.400 XP`, `120 Coroas`, `1 Ferro de Fuligem · Vinculado` e `1 Couro Escoriado · Vinculado`.
- No mesmo commit autoritativo são desbloqueados `Caçada Manual · Estrada das Cinzas` e `Desbravar · Estrada das Cinzas`.
- P1 não desbloqueia diretamente a Ronda; o Cão roteirizado da Etapa 3 não conta como primeira vitória em Caçada Manual.
- Se o jogador usar `[Descansar]`, o HP é restaurado conforme as regras normais do Braseiro.
- Se usar `[← Menu]` sem descansar, o HP restante real é preservado.
- Vigor permanece no valor real e não é restaurado pelo Braseiro.

### 46.15 Menu Principal imediatamente após P1

Ao retornar ao Menu depois da conclusão válida:

O exemplo abaixo corresponde ao caminho com Vitória no Prólogo. Após a conclusão de P1, normalmente haverá 2.720 / 4.800 nesse caminho e 2.400 / 4.800 no caminho com Derrota no Prólogo; o renderer usa sempre o XP persistido real.

```text
[Imagem contextual de Asterion]

🌑 Asterion
Terras do Ocaso · Refúgio do Ocaso

Sob céus cobertos de fuligem, as estradas de Asterion seguem marcadas por ruínas, brasas antigas e promessas que nunca repousam por completo. Mesmo nos caminhos mais silenciosos, cada passo ainda parece ecoar a memória de algo que o mundo não conseguiu esquecer.

{emoji da Classe} {Personagem} · Nv. 1
{Classe}

❤️ HP · {HP real persistido} / {HP máximo}
{barra de HP derivada do valor real}

⚡ Vigor · {Vigor real persistido} / {Vigor máximo}
{barra de Vigor derivada do valor real}

✨ XP · 2.720 / 4.800
{barra azul de XP derivada do valor real}

[Aventura] [Personagem]
[Guilda] [Mercado]
[Códice] [Calendário]
[Vínculos] [Classificação]
[Benefícios] [Comunidade]
[Configurações]
```

Regras:

- `Terras do Ocaso · Refúgio do Ocaso` é o contexto de localização imediatamente após P1.
- O personagem permanece no `Nv. 1` no fluxo normal Tutorial + P1.
- O exemplo representa o caminho de Vitória no Prólogo: 2.720 / 4.800. No caminho de Derrota, normalmente será 2.400 / 4.800. O renderer usa sempre o valor persistido real.
- A barra de XP é derivada dinamicamente do valor real; o mockup não fixa arredondamento independente.
- HP mostra o valor real persistido: restaurado se `[Descansar]` foi usado, ou o valor restante se o jogador voltou ao Menu sem descansar.
- Vigor mostra o valor real persistido e não é restaurado pelo Braseiro.
- Não mostrar novamente `📜 Missão Principal · Vozes na Estrada`, porque P1 está concluída.
- Não inventar automaticamente P2 ativa, P2 `Suspensa` ou outra Missão Principal apenas para preencher a HUD.
- Quando existir futuramente uma Missão Principal em estado autoritativo aplicável, a linha volta a aparecer conforme a regra geral do Menu.

### 46.16 Persistência, callbacks e reconstrução por estado

Regra geral:

> Todo progresso player-facing de P1 é reconstruído a partir do **estado autoritativo persistido**. A mensagem do Telegram, callback, sessão ou dispositivo nunca é fonte de verdade.

Consequências obrigatórias:

- sinal já examinado permanece examinado;
- Etapa concluída não retrocede;
- Refúgio já descoberto não é descoberto novamente;
- Alda já registrada não duplica entrada no Códice;
- Oren já registrado não duplica entrada no Códice;
- Braseiro já descoberto não duplica registro;
- recompensa de P1 nunca é concedida novamente;
- desbloqueios permanentes não repetem efeitos;
- callback antigo ou duplicado é revalidado contra o estado atual e não pode regredir a Missão nem repetir efeitos permanentes.

Reconstrução determinística:

| Estado autoritativo | Tela contextual reconstruída |
|---|---|
| P1 ativa, Etapa 1 pendente | Seguir pela Estrada |
| Etapa 1 concluída, nenhum sinal validado | Pegadas na Cinza |
| Pegadas validada | Sulcos Recentes |
| Tentativa da Etapa 3 ativa | Mesmo combate existente |
| Tentativa resolvida em derrota | 💀 Derrota / Braseiro da Estrada |
| Etapa 3 vencida, chegada pendente | Refúgio do Ocaso |
| Refúgio descoberto, Alda pendente | Alda Veyr |
| Alda registrada, Oren pendente | Oren Cal |
| Oren registrado, Braseiro pendente | Braseiro do Refúgio |
| Braseiro registrado + commit final | P1 concluída |
| P1 concluída em nova sessão | Menu/navegação normal |

### 46.17 Foreground, reconnect e `/menu`

Enquanto a tentativa contra o Cão estiver ativa:

- reconnect retoma o mesmo encontro;
- reconstrução da interface retoma o mesmo encontro;
- troca de dispositivo retoma o mesmo encontro;
- `/start` respeita a prioridade global da atividade Foreground e retoma o mesmo encontro;
- `/menu` respeita a prioridade global da atividade Foreground e retoma o mesmo encontro;
- não criar novo Cão nem novo encounter enquanto a tentativa anterior continuar ativa.

Quando uma Derrota já tiver sido validamente resolvida:

- aquele encontro deixa de estar ativo;
- P1 permanece na Etapa 3;
- não existe mais combate Foreground que obrigue retomada;
- `/menu` pode abrir o Menu Principal normalmente;
- o progresso de P1 permanece preservado;
- ao retornar por `Aventura → Missões → [Principal] → [Ver Objetivo]`, reconstruir a tela de **💀 Derrota / Braseiro da Estrada**;
- `[Retornar à Estrada]` cria a nova tentativa com nova identidade de encontro contra o mesmo Cão Cinéreo fixo Nv.1;
- não rerrolar criatura.

---


## 47. Resultados, Saque e Recompensas — padrão global final

Esta seção prevalece sobre exemplos anteriores quando o contexto for especificamente uma **tela de resultado/recibo de Recompensas**.

### 47.1 Ordem e densidade do recibo

Em recibos de atividade, mostrar apenas componentes realmente concedidos. Não exibir linhas `Nenhum`, `0`, slot vazio ou roll que não ocorreu.

Ordem visual padrão quando os componentes existirem:

1. ✨ XP;
2. 🪙 Coroas;
3. Materiais Básicos;
4. recursos especiais (Catalisador, Fragmento, Núcleo etc.);
5. Equipamentos;
6. Runas.

**Exceção de Missões:** o padrão de Missão permanece `XP → Coroas → Materiais → Equipamento/outros`, conforme a ordem já aprovada. O preview de recompensa de Missão não antecipa `Vinculado`; o estado econômico aparece após aquisição no detalhe/Inventário quando aplicável.

### 47.2 Equipamento e Runa em recibo

Recibos usam forma compacta de uma linha:

```text
🪖 Capuz Musgoso · Raro
💍 Selo dos Laços · Épico
🔷 Runa do Nó · Raro
```

Não mostrar slot, atributos, Nível do Item, Runa instalada, Encantamento ou Bind no recibo. Esses dados pertencem ao detalhe/Inventário.

Se houver múltiplos Equipamentos, listar mini-itens consecutivos, sem linha vazia obrigatória entre eles.

**Importante:** essa compactação é uma exceção de recibo. Inventário, Equipamentos, Mercado, Armazém e telas de escolha de recompensa continuam usando o nível de detalhe apropriado ao contexto.

### 47.3 Caçada Manual — vitória

```text
[Imagem contextual após o combate]

🏆 Vitória · {Criatura}
{Local} · {Região}

{Flavor Text curto de vitória}

🎁 Recompensas

{componentes realmente concedidos}

[← Caçada]
```

- `Vitória` já comunica que a criatura foi derrotada; não repetir `· Derrotado` em segunda linha.
- O Flavor fica entre contexto e Recompensas, impedindo que a tela pareça apenas um relatório mecânico.
- Flavor Text deve respeitar conhecimento atual, Local, criatura e estado narrativo; exemplos produzidos durante design são referência de tom, não lore automática global.
- Combate roteirizado de Missão pode avançar diretamente para a próxima cena e não precisa gerar esse recibo; P1 é precedente explícito.

### 47.4 Ronda de Caça — conclusão

```text
[Imagem contextual do Local]

🏆 Ronda de Caça · Concluída
{Local} · {Região}

⚔️ Encontros · {X}/{X}

{Flavor Text curto de conclusão}

🎁 Recompensas

{totais agregados do lote concluído}

[← Caçada]
```

- Recursos empilháveis são agregados pelo total do lote.
- Equipamentos e Runas permanecem individualizados.
- Não detalhar recompensa encontro a encontro em Ronda ×5/×10/×20.
- Interrupção por Elite/evento especial mantém tela própria de interrupção; não enfrenta automaticamente o alvo especial.

### 47.4.1 Ronda de Caça — encerramentos sistêmicos

Os encerramentos sistêmicos restantes da Ronda utilizam **dois shells visuais**:

1. shell próprio para **Derrota**, com retorno/recuperação pelo Braseiro permanente válido;
2. shell compartilhado `🏕️ Ronda de Caça · Encerrada` para HP abaixo do limiar de segurança sem recuperação válida, Vigor insuficiente e Inventário/Entregas Pendentes em estado impeditivo.

Esses estados não reabrem nem substituem os encerramentos já consolidados `🏆 Ronda de Caça · Concluída`, `🏕️ Ronda de Caça · Interrompida` para Elite/Evento Especial, `🏕️ Ronda de Caça · Cancelada` e `⏳ Cancelamento · Após o Encontro Atual`.

Regras comuns aos quatro encerramentos:

- `⚔️ Encontros · {X}/{Total}` permanece visível;
- encontros já concluídos permanecem válidos;
- recompensas válidas dos encontros concluídos são apresentadas de forma agregada, sem detalhamento encontro a encontro;
- componentes inexistentes não são exibidos; se nenhum componente tiver sido efetivamente concedido, omitir integralmente o bloco `🎁 Recompensas`;
- não criar tela adicional de confirmação ou sucesso;
- o lote é considerado encerrado depois que o estado final foi persistido;
- a Configuração de Combate deixa de permanecer travada somente após esse encerramento válido.

#### Derrota durante encontro automático

```text
[Imagem contextual do Braseiro]

💀 Ronda de Caça · Derrota

🔥 {Nome do Braseiro}
{Local} · {Região}

⚔️ Encontros · {X}/{Total}
❤️ HP · Restaurado

🎁 Recompensas

{totais dos encontros concluídos validamente}

[← Caçada]
```

Apresentação e ações:

- `💀` é o marcador de Derrota; não usar `⚠️` nesse estado;
- usar imagem contextual do Braseiro de recuperação, não a imagem genérica do Local;
- a tela é mostrada já após a recuperação normal pelo Braseiro permanente válido;
- `❤️ HP · Restaurado` comunica a consequência player-facing relevante;
- não repetir permanentemente `Vigor não restaurado` ou `Consumíveis não restaurados`;
- não oferecer `[Tentar Novamente]`, `[Retomar Ronda]` ou `[Iniciar Ronda]`;
- a Ronda terminou e o jogador retorna ao fluxo normal de Caçada.

A recuperação segue as regras globais do Braseiro permanente: HP restaurado a 100%, estados comuns de combate removidos, Vigor não restaurado e Consumíveis realmente usados permanecem consumidos.

#### HP abaixo do limiar de segurança sem recuperação válida

```text
[Imagem contextual do Local]

🏕️ Ronda de Caça · Encerrada
{Local} · {Região}

⚔️ Encontros · {X}/{Total}

❤️ HP · Abaixo do Limite Seguro

🎁 Recompensas

{totais dos encontros concluídos validamente}

[← Caçada]
```

- usar `Encerrada`, não `Interrompida`;
- não especificar internamente se faltou Poção, se a recuperação falhou ou se o Consumível terminou;
- comunicar somente o estado final relevante ao jogador;
- não oferecer ação automática de recuperação nessa tela.

#### Vigor insuficiente

```text
[Imagem contextual do Local]

🏕️ Ronda de Caça · Encerrada
{Local} · {Região}

⚔️ Encontros · {X}/{Total}

⚡ Vigor · Insuficiente

🎁 Recompensas

{totais dos encontros concluídos validamente}

[← Caçada]
```

- não mostrar o custo do próximo encontro;
- não usar formato como `1/2 Vigor`;
- não explicar reserva de lote ou cálculo econômico;
- `⚡ Vigor · Insuficiente` é a informação player-facing suficiente para comunicar por que a Ronda não prosseguiu.

#### Inventário / Entregas Pendentes em estado impeditivo

Usar o mesmo shell `Encerrada`, mas mostrar o bloqueador real.

Inventário impeditivo:

```text
[Imagem contextual do Local]

🏕️ Ronda de Caça · Encerrada
{Local} · {Região}

⚔️ Encontros · {X}/{Total}

🎒 Inventário · Espaço Insuficiente

🎁 Recompensas

{totais já entregues/validados}

[Inventário]

[← Caçada]
```

Entregas Pendentes impeditivas:

```text
[Imagem contextual do Local]

🏕️ Ronda de Caça · Encerrada
{Local} · {Região}

⚔️ Encontros · {X}/{Total}

📦 Entregas Pendentes · Limite Atingido

🎁 Recompensas

{totais já entregues/validados}

[Entregas Pendentes]

[← Caçada]
```

Se Inventário e Entregas Pendentes forem simultaneamente impeditivos, mostrar ambos os estados e ambas as ações:

```text
🎒 Inventário · Espaço Insuficiente
📦 Entregas Pendentes · Limite Atingido

[Inventário] [Entregas Pendentes]
[← Caçada]
```

- não criar ação genérica `[Liberar Espaço]`;
- os botões levam diretamente aos sistemas existentes.

Resumo player-facing:

| Condição | Estado/título | Shell |
|---|---|---|
| Derrota | `💀 Ronda de Caça · Derrota` | próprio, com Braseiro e recuperação |
| HP abaixo do limiar seguro | `🏕️ Ronda de Caça · Encerrada` | sistêmico |
| Vigor insuficiente | `🏕️ Ronda de Caça · Encerrada` | sistêmico |
| Inventário/Pending impeditivo | `🏕️ Ronda de Caça · Encerrada` | sistêmico com ação corretiva |

### 47.5 Masmorra — conclusão

```text
[Imagem contextual após o Chefe]

🏆 Masmorra · Concluída
{Nome da Masmorra} · {Dificuldade}

{texto oficial de conclusão}

🎁 Recompensas

{componentes realmente concedidos}

[← Masmorras]
```

- O acontecimento `Masmorra · Concluída` vem antes da identificação resumida da run.
- A Região não precisa ser repetida no cabeçalho final quando o nome da Masmorra já for inequívoco.
- Primeira Conclusão mostra o XP final calculado; não criar linha permanente `+60%` apenas para explicar a fórmula.
- Aplicar retroativamente às Masmorras das Terras do Ocaso e às dos Vales.

---

## 48. Resultados competitivos e coletivos — padrão final

### 48.1 Arena da Vigília

Vitória:

```text
[Imagem contextual da Arena]

🏆 Arena da Vigília · Vitória
{Jogador} vs {Oponente}

{Flavor competitivo curto}

🏅 Renome · {antes} → {depois} ({variação})
🔥 Elo · {elo atual ou transição real}

[← PvP]
```

Derrota usa `💀 Arena da Vigília · Derrota`. Empate usa `⚖️ Arena da Vigília · Empate`.

- Mostrar `Elo A → Elo B` apenas quando o Elo realmente mudar.
- Se permanecer no mesmo Elo, mostrar apenas `🔥 Elo · {Elo}`.
- MMR permanece oculto.
- Não usar `🎁 Recompensas` como bloco padrão de partida; Renome/histórico/marcos são consequências competitivas, não loot de Caçada.

### 48.2 Duelo

```text
🏆 Duelo · Vitória
{Jogador} vs {Oponente}

{Flavor curto}

[← PvP]
```

Derrota usa `💀`; empate usa `⚖️`. Duelo não recebe bloco econômico genérico.

### 48.3 Batalha de Guildas

Vitória direta:

```text
🏆 Batalha de Guildas · Vitória
{Guilda A} vs {Guilda B}

⚔️ Frentes · 2–0

{Flavor curto}

📈 Classificação · +3

[← Guilda]
```

Quando as Frentes terminarem empatadas e houver Campeão:

```text
🏆 Batalha de Guildas · Vitória
{Guilda A} vs {Guilda B}

⚔️ Frentes · 1–1
👑 Campeão · Vitória

{Flavor curto}

📈 Classificação · +3

[← Guilda]
```

Empate final:

```text
⚖️ Batalha de Guildas · Empate
{Guilda A} vs {Guilda B}

⚔️ Frentes · 1–1
👑 Campeão · Empate

{Flavor curto}

📈 Classificação · +1

[← Guilda]
```

Não transformar o Campeão automaticamente em “terceiro ponto” no placar das Frentes. Mostrar Frentes e Campeão como resultados separados.

### 48.4 Evento Mundial

Participante elegível:

```text
🏆 Evento Mundial · Concluído
{Nome do Evento} · {Região}

{Flavor oficial de consequência}

✅ Participação · Elegível

🎁 Recompensas
{recompensas reais}

[← Eventos]
```

Participante sem elegibilidade individual:

```text
🏆 Evento Mundial · Concluído
{Nome do Evento} · {Região}

{Flavor oficial de consequência}

⚠️ Participação · Insuficiente

[← Eventos]
```

O resultado global do Evento permanece concluído mesmo quando o personagem não atinge elegibilidade individual. Nesse caso, omitir o bloco de Recompensas; não mostrar `Recompensas · Nenhuma`.

### 48.5 Expedição

Expedição preserva sua escala oficial de resultado e usa o ícone do sistema, não `🏆` como padrão:

```text
🚩 Expedição · {Fracassada | Concluída | Profunda | Excepcional}
{Nome/Rota}

📊 Pontuação · {valor}/300

{Flavor de retorno}

🏛️ Tesouraria · {ganho coletivo, quando houver}

🎁 Recompensas
{recompensa individual, quando elegível}

[← Expedição]
```

Tesouraria e recompensa individual são blocos distintos.

### 48.6 Juramento

Fim de uma Provação:

```text
⚜️ Provação · Concluída
Juramento · {Guilda}

{Flavor curto}

📈 Contribuição · +{pontos}
⚜️ Ciclo · {total}/180

[← Juramento]
```

Fim do ciclo com recompensa individual:

```text
⚜️ Juramento · Faixa III
{Guilda}

📈 Contribuição · {valor}/180

{Flavor de encerramento}

🏛️ Tesouraria · +7.000 Coroas

🎁 Recompensas
{recompensa individual real}

[← Juramento]
```

Sem elegibilidade individual, omitir o bloco `🎁 Recompensas` e explicar a situação no Flavor; a Tesouraria coletiva continua aparecendo quando devida. Não usar `⚠️ Não Elegível` quando o texto contextual já comunicar claramente a situação.

---

## 49. Vales dos Enforcados — registro Visual/UI regional

A apresentação específica dos Vales passa a ser fechada por esta Fonte Visual/UI. A Fonte regional v1.0.2 continua autoridade de conteúdo.

### 49.1 Locais

- 🪨 Garganta dos Laços
- 🏕️ Vigília do Vale
- 🌳 Mata Suspensa
- 🪷 Baixios Enredados
- 🏛️ Claustro das Raízes
- 🪺 Berço da Matriarca

Masmorras:

- 🕳️ Fosso das Raízes
- 🕯️ Santuário do Nó Antigo

### 49.2 NPCs persistentes

- 🪖 Dara Venn
- ✒️ Iven Raal
- 🛠️ Mira Sel
- 🌿 Saera Nol
- 🧭 Edras Vhal

Somente Dara Venn e Iven Raal recebem automaticamente Entrada própria em **Figuras** do Códice por sua função regional. Os demais NPCs podem permanecer apenas como personagens presentes enquanto não houver conhecimento específico que justifique Entrada própria.

### 49.3 Criaturas

Criaturas-base:

- 🐺 Lobo Musgoso
- 🐦‍⬛ Gralha do Vale
- 🚶 Peregrino Enredado
- 🕷️ Aranha de Cipó
- 🦌 Cervo do Nó
- 🪱 Sanguessuga de Turfa
- 🪵 Casca Errante
- 🦋 Mariposa do Breu Verde
- 🗿 Vigia Enraizado

Elites de mundo aberto:

- 🪢 Nó-Feroz
- 🕷️ Viúva dos Cipós
- 🪵 Carrasco de Casca

Masmorras:

- 🕸️ Tecelã do Fosso · Elite
- 🪝 O Que Pende · Chefe
- 🛡️ Custódio Enredado · Elite
- 🕯️ Prelado Enraizado · Elite
- 🪢 Guardião do Nó Antigo · Chefe

Chefe regional:

- 🌿 Matriarca das Raízes

### 49.4 Mistérios e elementos mecânicos

Mistérios/Fenômenos:

- 🌿 Raízes que Seguem Pedra
- 🪢 O Nó Antigo
- 🧵 Cordas sob a Mata
- 🕸️ A Rede sob os Vales
- 🪺 O Berço da Matriarca
- 💓 Pulsação sob a Pedra

Elementos mecânicos, sem entrada própria de Bestiário:

- 💓 Nó Pulsante
- 🌿 Raiz de Contenção
- 🔒 Selo Radicular
- 🔗 Conexão Radicular

### 49.5 Braseiros permanentes

- 🔥 Braseiro dos Laços
- 🔥 Braseiro da Vigília
- 🔥 Braseiro das Copas Suspensas
- 🔥 Braseiro da Turfa Fria
- 🔥 Braseiro das Pedras Enlaçadas

O **Berço da Matriarca não possui Braseiro permanente normal**. Braseiros de Masmorra não entram na Travessia permanente.

### 49.6 Metadados regionais

Detalhe de Local:

```text
🪨 Garganta dos Laços
`Vales dos Enforcados · Nv. 11–13`
```

Listagem de Masmorra:

```text
🕳️ Fosso das Raízes · Nv. 14–17
`Vales dos Enforcados · Mata Suspensa`
```

Usar a segunda linha como metadado inteiro em monoespaçado quando a informação for equivalente. Missões preservam a exceção `📍 Local · Região` já definida.

---

## 50. Vales — Missões, hub e progressão player-facing

### 50.1 Campanha e Secundárias

P7–P12 e S7–S12 usam integralmente o padrão global de Missões. Não inventar diálogo, encontro específico ou conclusão causal onde a Fonte regional deixa o conteúdo em produção ou deliberadamente indeterminado.

Regras de apresentação importantes:

- P7 e P8 não recebem criatura específica inventada quando a Fonte não a define.
- P9 usa Casca Errante roteirizada; Variante não deve ser inventada.
- P10 usa Vigia de campanha conforme conteúdo, sem Variante inventada.
- P11 mantém encontro roteirizado regional não especificado.
- P12 usa a Matriarca e suas fases oficiais.
- S10 resgata um explorador; o segundo permanece desaparecido sem cadáver ou destino confirmado.
- S12 não identifica o Peregrino como o desaparecido de S10.
- S12 começa com leitura do registro recuperado em S10; a Fonte não define onde a bolsa foi encontrada de forma suficiente para criar inferência adicional player-facing.
- P11 abre acesso ao Berço, mas não equivale a entrar nele; P12 executa a entrada.
- A conclusão de P12 não abre automaticamente Nareth sem `P12 concluída + Nv.21`.

### 50.2 Vigília do Vale

A Vigília é hub seguro regional. Pode concentrar Pessoas, Ofícios, Caminho e Travessia. Não possui pool normal de Caçada/Ronda.

Quando for necessário comunicar indisponibilidade por **natureza do Local**, usar `🚫` em vez de `🔒`:

```text
🚫 Desbravar · Indisponível
🚫 Caçadas · Indisponível
```

- `🚫` = atividade não oferecida naquele Local por design.
- `🔒` = atividade existente, porém bloqueada por requisito.
- Não repetir uma linha separada de Ronda indisponível quando a própria Caçada não existe no Local.

Edras Vhal pode contextualizar troca de Caminho, mas a UI não inventa nova Provação, recomendação ou troca gratuita.

### 50.3 Recompensa de escolha — P9/P12 e equivalentes

Lista:

```text
🎁 Recompensa · Selecione 1

1 🪖 Capuz das Copas Suspensas
`🔵 Raro · Cabeça`

2 💍 Selo do Caminho Enredado
`🔵 Raro · Acessório`

3 🧿 Relicário do Nó Velado
`🔵 Raro · Artefato`

[1] [2] [3]
[← Missão]
```

- Não mostrar `+0`, Nível do Item ou `Vinculado` na lista.
- Ao abrir uma opção: imagem contextual → nome → raridade/slot → atributos → Runa/Encantamento quando realmente houver → lore oficial → `[Escolher]` → `[← Recompensas]`.
- Esse padrão vale também para as escolhas equivalentes de Terras do Ocaso.
- Após aquisição, o item segue o detalhe normal e mostra Bind/Nível quando aplicável.

---

## 51. Vales — Desbravar, Caçada e Ronda

### 51.1 Desbravar

Desbravar atua somente no Local atual e começa sem custo de Vigor. Tela de disponibilidade:

```text
[Imagem contextual do Local]

🧭 Desbravar
{Local}
`Vales dos Enforcados · Nv. X–Y`

{Flavor contextual}

[Desbravar]
[← Local]
```

Recarga usa `⏳ Recarga · {tempo}` e remove o botão enquanto indisponível.

Resultados internos/categorias do pool permanecem ocultos. Descobertas únicas mostram diretamente a consequência real — por exemplo `🔥 Braseiro · Descoberto`, `⛓️ Masmorra · Descoberta`, `📖 Códice · {Entrada}` — sem uma tela genérica `Descoberta Registrada`.

Resultado econômico mostra apenas o que foi realmente obtido. Combate transita diretamente para combate normal e mantém o mesmo resultado persistente da tentativa; derrota encerra a tentativa conforme Fonte Mestra.

### 51.2 Caçada Manual

Preparação:

```text
[Imagem contextual do Local]

🦌 Caçada
{Local}
`Vales dos Enforcados · Nv. X–Y`

{Flavor curto}

❤️ HP · {valor}
⚡ Vigor · {valor}

1 Solo
2 Grupo

[1] [2]
[← Local]
```

Antes da familiaridade:

```text
🔒 Ronda de Caça · Vença uma Caçada neste Local
```

Depois da primeira vitória manual válida, a mesma interface passa a oferecer a seleção do lote em lista numerada:

```text
1 🏕️ Ronda · 5 Encontros
2 🏕️ Ronda · 10 Encontros
3 🏕️ Ronda · 20 Encontros

[1] [2] [3]
```

Selecionar `[1]`, `[2]` ou `[3]` abre a preparação normal da Ronda já consolidada, com o tamanho escolhido refletido em `🎯 Ronda · {X} Encontros`. Não criar tela extra de desbloqueio.

Pools regionais normais existem em Garganta, Mata, Baixios e Claustro. Vigília e Berço não recebem pool normal.

### 51.3 Ronda de Caça

Preparação:

```text
🏕️ Ronda de Caça
{Local}
`Vales dos Enforcados · Nv. X–Y`

❤️ HP · {valor}
⚡ Vigor · {valor}

🎯 Ronda · 10 Encontros
⏱️ Cadência · 3 min por Encontro
🧪 Consumíveis · {estado}

[Consumíveis]
[Iniciar Ronda]
[← Caçada]
```

- Não mostrar `2 Vigor × 10` nem reserva de lote; o custo é por encontro econômico conforme backend.
- Durante a Ronda: estado `Andamento`, progresso `X/10`, HP/Vigor, timer e `[Cancelar Ronda]`; sem botão de retorno concorrente.
- Elite/evento especial interrompe a Ronda; não existe combate automático contra Elite.
- Conclusão usa o recibo `🏆 Ronda de Caça · Concluída` da seção 47; Derrota e encerramentos sistêmicos por HP, Vigor ou Inventário/Entregas Pendentes usam os shells globais da seção 47.4.1.

---

## 52. Vales — Masmorras e Chefes

### 52.1 Dificuldades

Padrão global:

```text
1 🟢 Estável · Disponível
2 🔒 Fraturada · Concluir Estável
3 🔒 Ruptura · Nv. 60
```

Depois de Estável:

```text
2 🟠 Fraturada · Disponível
```

Se Nv.60 já foi atingido mas Fraturada não foi concluída:

```text
3 🔒 Ruptura · Concluir Fraturada
```

`🟢` significa dificuldade Estável, não conclusão. `🟠` significa Fraturada.

### 52.2 Entrada e preparação

Preparação mostra Masmorra, dificuldade/Nível, HP/Vigor e os modos Solo/Grupo/Pareamento. Não criar preparação manual separada de Consumíveis para PvE manual; Consumíveis elegíveis aparecem no combate conforme regras da run.

Solo cria a run imediatamente após validação/reserva. Não mostrar contador permanente `Encontro X/5` na HUD de combate. Encontros ambientais podem usar título/lore antes do combate.

### 52.3 Braseiros de Masmorra

- Fosso: `🔥 Braseiro das Cordas Mortas` quando sorteado.
- Santuário: `🔥 Braseiro do Nó Silencioso` quando sorteado.
- São instanciados, não entram na Travessia permanente.
- Ao ativar: `🔥 Braseiro · Ativado`; não acrescentar linha genérica `HP Restaurado` quando o estado já for comunicado pelo próprio fluxo.
- Retry pelo Braseiro não é viagem.

### 52.4 Fases de Chefes — HUD e Bestiário

No primeiro encontro com um Chefe, a fase inicial não recebe rótulo `Fase I`. Somente fases posteriores reveladas ganham `Fase II`, `Fase III` quando efetivamente alcançadas.

O Que Pende:

- fase inicial: nome de fase não antecipado; Bestiário posterior pode registrar **Aquilo que Espera**;
- Fase II: **Cordas Tensas**;
- Fase III: **Nada Sustenta**.

Guardião do Nó Antigo:

- fase inicial: Bestiário posterior pode registrar **Protocolo Sepultado**;
- Fase II: **O Nó se Fecha**;
- Fase III: **Raiz e Pedra**.

Matriarca das Raízes:

- fase inicial: Bestiário posterior pode registrar **A Criatura**;
- Fase II: **A Rede**;
- Fase III: **Aquilo que Permanece**.

Elementos mecânicos como Nós, Raízes, Selos e Conexões não recebem entrada de Bestiário própria.

---

## 53. Bestiário — padronização cruzada final

### 53.1 Estrutura

`Observado → Conhecido → Estudado → Dominado` permanece global.

- desconhecido fica ausente;
- Região mostra apenas quantidade conhecida, sem denominador;
- Variante fica ausente antes da descoberta legítima;
- Elites não recebem uma Variante adicional implícita;
- `Chefe Regional` é reservado a Boss regional de Campanha; Boss de Masmorra usa `Chefe`.

### 53.2 Habitat, Fraqueza e Resistência

Habitat deve surgir naturalmente em descrição/Notas de Campo ou em metadado de localização quando necessário; evitar transformar o dossiê em formulário.

Fraqueza/Resistência técnicas (`+10%` / `−10%` no Conteúdo) permanecem backend/conteúdo autoritativo. Na UI, preferir descrição narrativa/qualitativa. Só criar linha técnica sem percentual quando a clareza não puder ser obtida por narrativa.

### 53.3 Variantes

Rótulos player-facing:

- 🔥 Furioso · `Agressivo e Vulnerável`
- 🛡️ Resistente · `Robusto e Contido`
- 🌀 Ágil · `Veloz e Frágil`
- 🩸 Hemorrágico · `Lacerante e Contido`
- ☣️ Venenoso · `Tóxico e Frágil`

Em combate: `Variante · Furioso` etc.

### 53.4 Artes e Preparadas

Arte no Bestiário:

```text
☄️ Despencar · Golpe Preparado
```

Usar **☄️** consistentemente para Arte Preparada quando o estado/telegraph for a informação relevante; não reutilizar `💥` como ícone genérico de Preparada.

### 53.5 Notas de Campo de Chefes

Fases e mecânicas legitimamente observadas aparecem sob:

```text
📓 Notas de Campo
```

- usar nomes narrativos oficiais de fases/mecânicas;
- não mostrar thresholds percentuais, cooldowns ou lógica de IA;
- Bestiário só mostra fases já conhecidas;
- Dominado pode exibir o dossiê legitimamente completo sem romper mistérios protegidos.

Aplicar também retroativamente a **O Sem-Nome**, **Custódio do Primeiro Selo** e **Vigia Partido** nas Terras do Ocaso.

---

## 54. Códice — padronização cruzada final

### 54.1 Estrutura global

Categorias permanecem:

1. 🪐 Mundo e Cosmologia
2. 🗺️ Regiões e Locais
3. 🏴 Povos e Facções
4. 👤 Figuras
5. 📜 História e Acontecimentos
6. 👁️ Mistérios e Fenômenos
7. 🌌 Crônicas

Não usar percentual, contador total, `???`, fragmentos desconhecidos ou espaços reservados para conteúdo ainda não descoberto.

### 54.2 Região e Local

`Códice → Regiões e Locais → Região → Local → detalhe`.

Vales, quando conhecidos, podem listar os seis Locais de mundo e as duas Masmorras. O detalhe de Local usa lore oficial e pode mostrar Braseiro conhecido e criaturas conhecidas. Mecânicas permanecem no Bestiário; deslocamento permanece no Mapa.

Braseiro conhecido pode aparecer, por exemplo:

```text
🔥 Braseiro dos Laços · Descoberto
```

### 54.3 Vales — conteúdo conhecido

Figuras automáticas:

- Dara Venn;
- Iven Raal.

História e Acontecimentos:

- 📜 Rotas dos Vales
- 📜 Nomes dos Vales
- 📜 Vigília do Vale
- 📜 Rotinas que Permanecem
- 📜 Estruturas Interligadas

Mistérios e Fenômenos usam os ícones definidos na seção 49.4.

### 54.4 Entradas atualizadas

Uma mesma Entrada pode receber novos Trechos sem criar uma cópia ou um estado interno `Atualizado` no cartão. Notificação externa pode usar:

```text
📖 Códice · O Nó Antigo · Atualizado
```

**O Nó Antigo** expande conforme P9 → P10 → Santuário. **A Rede sob os Vales** expande em P11/P12. **Pulsação sob a Pedra** surge quando legitimamente conhecida em P12. Não antecipar causalidade além da Fonte regional.

---

## 55. Feitos e Cosméticos — Vales e regra global

### 55.1 Estados de Feitos

- Feito não secreto e conhecido/incompleto: `⏳`.
- Feito obtido: `✅`.
- Feitos secretos ficam completamente ausentes antes da obtenção/descoberta legítima; não usar `🔒` nem placeholder.
- Não mostrar percentual regional de conclusão, recompensa de 100%, moeda regional de Feitos ou ranking de conclusão.
- Feito sem cosmético não recebe linha `Sem Recompensa`.

### 55.2 Feitos dos Vales

1. **Estrada Estrangulada** · Exploração · concluir P7 · sem cosmético.
2. **Andarilho dos Vales** · Exploração · descobrir 5 Locais principais + 5 Braseiros permanentes · Título **Andarilho dos Vales**.
3. **Sob as Raízes** · 👁️ Segredo · descobrir Fosso + Santuário · Banner **Profundezas Enredadas**.
4. **O Berço Silencia** · Combate · derrotar a Matriarca pela primeira vez · Título **Sobrevivente do Berço**.
5. **Aquilo que Pende** · PvE · primeira Estável do Fosso · Emblema **Nó Suspenso**.
6. **O Nó Antigo** · PvE · primeira Estável do Santuário · Emblema **Selo Radicular**.
7. **Raízes Fraturadas** · PvE · concluir ambas as Masmorras em Fraturada · Moldura **Raiz Fraturada**.
8. **Caçador dos Vales** · Bestiário · Dominar as 9 criaturas-base · Título **Caçador dos Vales**.
9. **Entre Galhos e Presas** · 👁️ Segredo · 9 bases Dominadas + 3 Elites Dominados + cinco tipos de Variante legitimamente descobertos · Aparência **Sobrevivente dos Vales**.
10. **A Pedra que Ainda Guarda** · Bestiário · Estudado em Vigia Enraizado, Custódio Enredado, Prelado Enraizado e Guardião do Nó Antigo · Banner **Nó Antigo**.
11. **Nomes Presos à Madeira** · 👁️ Segredo · S10 + S12 + Trechos disponíveis de Nomes dos Vales · Emblema **Nome Entalhado**.
12. **A Rede Não Dorme** · 👁️ Segredo · primeira Estável do Santuário + P12 + conhecimento disponível de O Nó Antigo/Estruturas Interligadas/A Rede sob os Vales · Moldura **Pedra Enlaçada**.
13. **Vales dos Enforcados** · Exploração · P12 + Nv.20 + 5 Locais principais descobertos · Banner **Vales dos Enforcados**.

### 55.3 Catálogo cosmético regional

Títulos: **Andarilho dos Vales**, **Sobrevivente do Berço**, **Caçador dos Vales**.

Emblemas: **Nó Suspenso**, **Selo Radicular**, **Nome Entalhado**.

Molduras: **Raiz Fraturada**, **Pedra Enlaçada**.

Banners: **Profundezas Enredadas**, **Nó Antigo**, **Vales dos Enforcados**.

Aparência: **Sobrevivente dos Vales**.

Coleções de Cosméticos mostram **origem resumida** (Exploração, Combate, PvE, Bestiário, Segredo); o Feito mostra o tipo/nome da recompensa.

Categoria usa `🧍 Aparência`. Uma Aparência individual pode usar ícone temático de origem/região quando definido — por exemplo `🌑 Errante das Cinzas` ou `🪢 Sobrevivente dos Vales` — e usa `🧍` como fallback. Isso não altera o ícone da categoria.

Não inventar lore cosmético quando a Fonte regional não o fornece; usar texto oficial quando produzido.

---

## 56. Inventário, Criação, Desmontagem e Aprimoramento — fechamento final

### 56.1 Materiais no Inventário

Cabeçalho:

```text
🧱 Materiais
```

Material Básico:

```text
1 ⛏️ Ferro Enredado · 23
`Metal · Grau II`
```

Detalhe:

```text
[Imagem contextual]

⛏️ Ferro Enredado · 23
`Metal · Grau II`
🔗 Vinculado

{lore oficial}

[← Materiais]
```

O estado `🔗 Vinculado` aparece apenas quando aquele stack real for vinculado.

Recursos especiais também preservam categoria/tipo na lista para cumprir o padrão de Inventário; não omitir metadado apenas por o nome já sugerir a função. Exemplos:

```text
⚗️ Catalisador de Elite II · 3
`Recurso Especial · Grau II`

🪨 Fragmento de Aprimoramento II · 7
`Recurso Especial · Grau II`

💠 Núcleo do Fosso das Raízes · 1
`Núcleo de Masmorra`
```

### 56.2 Receita e Criação

Detalhe de Receita:

```text
[Imagem contextual]

📚 Receita

{Equipamento}
`{raridade} · {slot}`

🧱 Materiais
{material} · {possuído} / {necessário}

[Ir para Criação]
[← Receitas]
```

Criação final:

```text
[Imagem contextual]

🛠️ Criação

{Item}
{atributos relevantes}

🧱 Materiais
{quantidades exatas consumidas}

📈 Nível do Item · {nível}
🎒 Destino · Inventário

[Criar]
[← Criação]
```

Se componentes transmitirem Bind, mostrar `🔗 Vinculado` antes da confirmação. Preview usa stacks exatos do backend.

### 56.3 Desmontagem

```text
[Imagem contextual]

♻️ Desmontagem

{Equipamento}
`{raridade} · {slot}`

🎁 Materiais Recuperados
{saída autoritativa calculada}

⚠️ O equipamento será destruído permanentemente.

[Desmontar]
[← {Equipamento}]
```

- Não concede Coroas.
- Aprimoramento não aumenta retorno.
- Equipamento Favorito/Bloqueado não é elegível enquanto o estado impedir a ação.
- Equipado passa pelo Equipment Validator/desequipamento apropriado.
- Mítico exige confirmação reforçada conforme regra global.
- Núcleos consumidos na criação não retornam por Desmontagem.

### 56.4 Aprimoramento

Substituir qualquer legado `Fragmento Cinéreo` por **Fragmento de Aprimoramento** do Grau correspondente ao Nível do Item:

`1–10 I / 11–20 II / 21–30 III / 31–40 IV / 41–50 V / 51–60 VI`.

Exemplo genérico:

```text
🪨 Fragmento de Aprimoramento {Grau aplicável} · {possuído} / {necessário}
🪙 Coroas · {custo}
```

Não usar um Grau concreto em mockup quando o Nível do Item do exemplo não estiver explicitamente conhecido. O sistema continua +0→+10 garantido; não repetir `Sucesso Garantido` em toda tentativa.

---

## 57. Auditoria cruzada e precedência desta revisão

A sincronização anterior de 2026-09-24 reuniu a Fonte Mestra v1.4.6, Terras do Ocaso v1.0.3 FINAL, Vales dos Enforcados v1.0.2 FINAL e as decisões de Visual/UI aprovadas até aquela data.

A atualização anterior de 2026-09-25 sincronizou a apresentação com a Fonte Mestra v1.4.7 e Terras do Ocaso v1.0.4 e formalizou a continuidade do Prólogo em caso de Derrota. A presente revisão preserva essas decisões e adiciona o fechamento player-facing de P2 e Charneca da Fuligem na seção 60, sincronizado com Terras do Ocaso v1.0.5.

Correções consolidadas:

- `Fragmento Cinéreo` deixa de ser nomenclatura de UI e é substituído por **Fragmento de Aprimoramento {Grau}**;
- Materiais Básicos deixam de usar `📦` como ícone genérico e passam a usar família semântica;
- preview de recompensa de Missão não mostra `Vinculado`; o estado continua autoritativo após aquisição;
- recibos de Recompensa usam Equipamento/Runa compactos em uma linha;
- telas de Inventário/Equipamento preservam raridade + slot em segunda linha e dados detalhados no detalhe;
- Caçada, Ronda, Masmorra, Arena, Duelo, Batalha de Guildas, Evento Mundial, Expedição e Juramento passam a compartilhar uma linguagem de resultado coerente sem apagar as diferenças de cada sistema;
- seleções player-facing em listas numeradas usam botões numéricos quando o botão apenas seleciona a opção correspondente; isso se aplica explicitamente à escolha do lote da Ronda (`5/10/20`) e à raiz de Caminho;
- Bestiário passa a tratar Habitat/Fraqueza/Resistência de forma narrativa por padrão e usa `☄️` para Preparadas;
- Boss Notes são consolidadas sob `📓 Notas de Campo`;
- Vales recebe iconografia individual oficial para Locais, NPCs, criaturas, Mistérios e elementos mecânicos;
- `🚫` fica reservado à ausência de atividade por design do Local; `🔒` continua para bloqueio por requisito;
- cosméticos de Aparência podem usar ícone temático individual sem alterar `🧍` como ícone da categoria;
- não há Braseiro permanente normal no Berço da Matriarca;
- Mission rewards mantêm ordem `XP → Coroas → Materiais → Equipamento/outros`;
- telas de resultado podem usar Flavor Text contextual, mas Flavor não pode antecipar conhecimento nem substituir informação mecânica essencial.

Em conflito de apresentação entre trechos antigos deste mesmo arquivo e as seções 47–60 desta revisão, **as seções 47–60 prevalecem**. Em conflito mecânico/global, prevalece a Fonte Mestra v1.4.7. Em conflito de conteúdo regional, prevalece a Fonte regional correspondente.

---

## 58. Estado desta consolidação

Com esta atualização, passam a ser considerados visualmente fechados ou consolidados nesta revisão:

- detalhamento interno de Doutrinas;
- Inventário;
- Talentos;
- Ofícios;
- Caminho;
- Legado e Marcas de Legado;
- raiz de Aventura;
- Mapa e Travessia dos Braseiros;
- Missões, incluindo Missão Principal Suspensa, Missões Secundárias e o fluxo específico de P2 da seção 60;
- entrada/preparação de Caçada;
- entrada/preparação, Grupo, Pareamento e Confirmação de Entrada de Masmorras;
- padrão atualizado de HUD de combate;
- consequência visual do modelo direto de Consumíveis do Inventário em PvE manual;
- padronização global de Consumíveis, incluindo `🧪`, `Consumível · Grau {Grau}`, seleção `[Consumível]`, Proteção, Dissipador, Resguardo, HUD, Registro, revalidação e retornos semânticos;
- Menu Principal em formato dashboard/HUD;
- Vínculos;
- Classificação da Vigília;
- Salão da Vigília;
- formato oficial de data player-facing;
- capitalização player-facing de Asterion;
- Criação de Personagem;
- Prólogo jogável **Cinzas na Estrada**, incluindo Ataque/Defender, primeira Arte, primeiro Braseiro, conclusão após Vitória ou Derrota sem retry e transição para o Menu Principal.
- P1 — **Vozes na Estrada**, incluindo detalhe oficial da Missão, execução contextual, combate normal, derrota/retry, Refúgio, Alda Veyr, Oren Cal, Braseiro do Refúgio, conclusão, persistência, recovery e reconnect;
- UI/iconografia regional dos **Vales dos Enforcados**;
- resultados e recibos globais de Caçada, Ronda, Masmorra, Arena, Duelo, Batalha de Guildas, Evento Mundial, Expedição e Juramento, incluindo os encerramentos sistêmicos restantes da Ronda por Derrota, HP, Vigor e Inventário/Entregas Pendentes;
- padronização cruzada de Materiais, Equipamentos/Runas em recibo, Bestiário, Códice, Feitos e Cosméticos entre as duas primeiras Regiões.

Com isso, a arquitetura e o Visual/UI player-facing de alto nível, **incluindo Terras do Ocaso e Vales dos Enforcados**, ficam considerados **fechados para esta fase de design**, salvo conflito estrutural futuro explicitamente aprovado.

A Baseline Numérica v1.0 da Fonte Mestra v1.4.7 é autoritativa para implementação e testes e não possui reabertura numérica vigente. Permanecem fora desta consolidação nomes/conteúdo usados exclusivamente como exemplos de UI quando ainda não definidos, além de mecânicas futuras ou explicitamente reabertas pela Fonte Mestra como `SIMULAR`. Em qualquer divergência numérica, a Fonte Mestra v1.4.7 prevalece.



---

## 59. Consumíveis — Proteção, Dissipação e Resguardo · Visual/UI FINAL

### 59.0 Escopo

Fechar exclusivamente a apresentação e os fluxos player-facing das novas famílias globais:

- **Preparado de Proteção**;
- **Dissipador**;
- **Preparado de Resguardo**.

Este fechamento também formaliza um **template visual comum para Consumíveis**, de modo que as famílias novas permaneçam consistentes com:

- Poção de Cura;
- Preparado de Purificação;
- Antídoto;
- Poção de Vigor.

Essa padronização não altera efeitos, balanceamento, requisitos, materiais, custos, limites, economia ou regras de uso das famílias já existentes.

### 59.1 Identidade visual global de Consumíveis

Todo item pertencente à categoria Consumível utiliza:

```text
🧪
```

como ícone principal de identidade.

Isso vale para:

```text
🧪 Poção de Cura
🧪 Preparado de Purificação
🧪 Antídoto
🧪 Poção de Vigor
🧪 Preparado de Proteção
🧪 Dissipador
🧪 Preparado de Resguardo
```

Ícones funcionais podem aparecer em linhas de efeito, HUD e Registro de Combate, mas **não substituem `🧪` como identidade principal do item**.

Padrão funcional:

```text
❤️ Cura
✨ Purificação
☣️ Antídoto
⚡ Vigor
🔰 Barreira
✨ Dissipação
🛡️ Resguardo
```

Purificação e Dissipação podem compartilhar `✨` porque ambas representam remoção de estado; o texto deixa claro se o efeito removido é negativo ou positivo.

### 59.2 Template global no Inventário

A raiz continua usando normalmente:

```text
🎒 Inventário
→ Consumíveis
```

A listagem de Consumíveis segue o padrão:

```text
{número} 🧪 {Nome} · {quantidade}
Consumível · Grau {Grau}
```

A listagem mantém somente duas informações no metadado:

```text
Consumível · Grau {Grau}
```

A família/função não é repetida nessa segunda linha.

Ela permanece identificável:

- pelo próprio nome do item;
- pelo detalhe do Consumível;
- pela linha funcional apresentada durante a seleção em combate.

O Grau mostrado é sempre o Grau real do item.

O Grau mínimo da família não substitui o Grau do item apresentado.

#### Terras do Ocaso

```text
1 🧪 Poção de Cura · 4
Consumível · Grau I

2 🧪 Preparado de Purificação · 2
Consumível · Grau I

3 🧪 Antídoto Cinzento · 3
Consumível · Grau I

4 🧪 Poção de Vigor · 1
Consumível · Grau I
```

#### Vales dos Enforcados

```text
1 🧪 Poção de Cura do Vale · 4
Consumível · Grau II

2 🧪 Preparado de Purificação Enredada · 2
Consumível · Grau II

3 🧪 Antídoto de Turfa · 3
Consumível · Grau II

4 🧪 Poção de Vigor dos Laços · 1
Consumível · Grau II
```

Essa formalização é apenas visual.

### 59.3 Novas famílias no Inventário

#### Preparado de Proteção

Nos Vales:

```text
5 🧪 Preparado de Proteção Enredada · 4
Consumível · Grau II
```

#### Dissipador

Usar o nome regional legítimo quando existir.

Template:

```text
6 🧪 {Nome do Dissipador} · 2
Consumível · Grau {Grau}
```

Não inventar variante regional somente para preencher a UI.

#### Preparado de Resguardo

Template:

```text
7 🧪 {Nome do Preparado de Resguardo} · 3
Consumível · Grau {Grau}
```

Novamente, não criar nome regional sem definição de conteúdo.

### 59.4 Detalhe — Preparado de Proteção

Exemplo oficial dos Vales:

```text
[Imagem contextual do Consumível]

🧪 Preparado de Proteção Enredada · Grau II
Consumível · Proteção

🎒 Quantidade · 4

🔰 Barreira · 12% do HP Máximo
⏳ Duração · 2T
🎯 Alvo · Próprio

⚔️ Uso · Somente em Combate PvE

[← Consumíveis]
```

Não mostrar ao jogador:

```text
floor(12% × HP Máximo)
```

O arredondamento permanece responsabilidade mecânica.

Player-facing:

```text
🔰 Barreira · 12% do HP Máximo
```

é suficiente.

Como o item é exclusivamente de combate, seu detalhe no Inventário não possui:

```text
[Usar]
```

### 59.5 Detalhe — Dissipador

```text
[Imagem contextual do Consumível]

🧪 {Nome do Dissipador} · Grau {Grau}
Consumível · Dissipador

🎒 Quantidade · {quantidade}

✨ Dissipação · 1 Efeito Positivo Removível
🎯 Alvo · 1 Inimigo

ℹ️ Efeitos acumuláveis perdem 1 Acúmulo. Efeitos protegidos ou não removíveis não são opções válidas.

⚔️ Uso · Somente em Combate PvE

[← Consumíveis]
```

Não expor no detalhe:

- ordem interna dos stacks;
- flags técnicas;
- pipeline de aplicação;
- teste interno de validade;
- ausência de RNG como informação técnica.

Quando `stack` precisar ser comunicado player-facing, usar:

```text
Acúmulo
```

### 59.6 Detalhe — Preparado de Resguardo

```text
[Imagem contextual do Consumível]

🧪 {Nome do Preparado de Resguardo} · Grau {Grau}
Consumível · Resguardo

🎒 Quantidade · {quantidade}

🛡️ Resguardo · 2T · 1 Carga

Bloqueia a primeira aplicação elegível de Efeito Negativo removível.

ℹ️ O Dano Direto associado continua normalmente. Não bloqueia Controle Rígido, fases, mecânicas fixas ou efeitos protegidos.

⚔️ Uso · Somente em Combate PvE

[← Consumíveis]
```

Não expandir o detalhe para listar todas as exceções técnicas da mecânica.

### 59.7 Poção de Vigor permanece fora do combate

A Poção de Vigor segue normalmente o mesmo padrão visual no Inventário:

```text
🧪 Poção de Vigor dos Laços · Grau II
Consumível · Vigor

🎒 Quantidade · 1

⚡ Vigor · +20
🎯 Alvo · Próprio

🌙 Uso · Fora de Combate

[Usar]

[← Consumíveis]
```

Seu `[Usar]` só aparece quando suas condições próprias forem satisfeitas.

Ela **não aparece dentro da seleção `[Consumível]` da HUD de combate**.

### 59.8 Entrada pelo combate

A HUD normal permanece:

```text
Turno {X} · {Personagem}

{HUD normal do combate}

[Atacar] [Defender]
[Artes válidas...]
[Consumível]
```

`[Consumível]` aparece somente quando existir pelo menos um Consumível de combate elegível e utilizável naquele estado.

Não mostrar botão desabilitado quando nenhuma opção existir.

PvP continua sem Consumíveis externos.

### 59.9 Template global da seleção `[Consumível]`

A tela de seleção deve deixar todas as famílias visualmente equivalentes.

Exemplo completo nos Vales:

```text
🧪 Consumíveis
Turno {X} · {Personagem}

1 🧪 Poção de Cura do Vale · 4
❤️ Cura · 22% HP Máximo

2 🧪 Preparado de Purificação Enredada · 2
✨ Purificação · 1 Efeito Negativo

3 🧪 Antídoto de Turfa · 2
☣️ Antídoto · 1 DoT

4 🧪 Preparado de Proteção Enredada · 3
🔰 Barreira · 12% HP Máximo · 2T

5 🧪 {Nome do Dissipador} · 2
✨ Dissipação · 1 Efeito Positivo

6 🧪 {Nome do Preparado de Resguardo} · 2
🛡️ Resguardo · 2T · 1 Carga

[1] [2] [3] [4] [5] [6]

[← Combate]
```

Esse passa a ser o padrão comum.

A primeira linha identifica:

```text
🧪 Nome · quantidade
```

A segunda resume exclusivamente a função relevante para a escolha em combate.

Não repetir nessa tela:

```text
Consumível · Grau II
Alquimista Nv.X
```

Essas informações pertencem ao Inventário/detalhe e não são necessárias durante a decisão de Turno.

### 59.10 Regra numérica

Como os Consumíveis estão apresentados em uma lista numerada e os botões apenas selecionam a opção correspondente:

```text
[1] [2] [3]
```

é o padrão correto.

Não utilizar:

```text
[Cura]
[Purificação]
[Proteção]
```

quando já existir lista numerada imediatamente acima.

A mesma regra vale para listas de:

- inimigos;
- efeitos positivos;
- outras escolhas equivalentes dentro deste fluxo.

### 59.11 Seleção com apenas um Consumível

Mesmo quando houver apenas um Consumível elegível, `[Consumível]` continua abrindo a seleção.

Exemplo:

```text
🧪 Consumíveis
Turno {X} · {Personagem}

1 🧪 Preparado de Proteção Enredada · 3
🔰 Barreira · 12% HP Máximo · 2T

[1]

[← Combate]
```

O jogador ainda escolhe explicitamente consumir o item.

A regra de eliminar telas sem decisão real passa a valer **depois da escolha do Consumível**, especialmente no fluxo de alvo/efeito do Dissipador.

Abrir `[Consumível]` por si só nunca gasta item.

### 59.12 Preparado de Proteção — fluxo

O Preparado de Proteção possui alvo próprio.

Depois de selecionar o item:

```text
[Consumível]
→ [Preparado de Proteção]
→ commit
→ HUD normal
```

Não criar:

```text
Escolha o Alvo
```

Não criar:

```text
[Usar]
```

depois da seleção.

Não criar confirmação:

```text
Tem certeza?
```

A seleção do próprio Consumível já representa a intenção de uso.

### 59.13 Preparado de Proteção — HUD

Depois do uso válido:

```text
👉 {emoji da Classe} {Personagem}
❤️ {HP atual} / {HP máximo}
{barra de HP}

🔰 Barreira · {valor atual} · 2T
```

Se a Barreira sofrer dano:

```text
🔰 Barreira · {valor restante} · {T restante}
```

Se expirar ou atingir zero, a linha desaparece.

Não manter:

```text
🔰 Barreira · 0
```

na HUD.

Nova aplicação válida da mesma fonte apenas atualiza:

- valor;
- duração.

Não criar segunda linha de Barreira da mesma fonte.

### 59.14 Preparado de Proteção — Registro de Combate

Exemplo:

```text
🧪 **Luiken** usa **Preparado de Proteção Enredada**.
🔰 Barreira · `120` · `2T`
```

Não criar aviso separado:

```text
Consumível usado com sucesso.
```

O Registro e a alteração da HUD são feedback suficiente.

### 59.15 Dissipador — elegibilidade na seleção

O Dissipador só aparece na tela `[Consumível]` quando houver pelo menos:

```text
1 inimigo válido
+
1 Efeito Positivo removível válido
```

Se existirem Buffs ativos, mas todos forem:

- protegidos;
- não removíveis;
- pertencentes a mecânica fixa;
- inelegíveis pelas regras existentes;

o Dissipador não aparece como opção utilizável.

Não mostrar uma opção desabilitada.

### 59.16 Dissipador — múltiplos inimigos elegíveis

Depois de escolher o Dissipador, quando mais de um inimigo possuir efeito removível:

```text
✨ Dissipador · Escolha o Alvo

1 🐺 {Inimigo A}
Efeitos Removíveis · 2

2 🕷️ {Inimigo B}
Efeitos Removíveis · 1

[1] [2]

[← Consumíveis]
```

A lista contém apenas inimigos realmente elegíveis.

Não mostrar inimigos sem Buff removível.

Não revelar informação oculta de combate/Bestiário.

### 59.17 Dissipador — somente um inimigo elegível

Se apenas um inimigo possuir Efeito Positivo removível:

**não criar tela de seleção de alvo.**

O sistema avança diretamente.

Se houver vários Buffs válidos:

```text
Dissipador
→ único alvo válido
→ Escolha o Efeito
```

Se houver apenas um Buff válido:

```text
Dissipador
→ único alvo
→ único efeito
→ commit direto
```

Nenhuma tela sem escolha real é criada.

### 59.18 Dissipador — múltiplos Buffs removíveis

Se o alvo possuir mais de um:

```text
✨ Dissipador · Escolha o Efeito

🐺 {Inimigo}

1 🟢 {Efeito Positivo A} · 2T
2 🟢 {Efeito Positivo B} · 3 Acúmulos · 1T

[1] [2]

[← Alvos]
```

Mostrar somente efeitos:

- ativos;
- visíveis legitimamente;
- removíveis;
- elegíveis.

Não mostrar efeitos protegidos como opções bloqueadas.

### 59.19 Retorno da seleção de Buff

Quando o jogador chegou à tela de efeitos depois de selecionar um alvo:

```text
[← Alvos]
```

Quando o alvo foi escolhido automaticamente porque só havia um:

```text
[← Consumíveis]
```

Não usar:

```text
[← Voltar]
```

quando o pai semântico é conhecido.

### 59.20 Dissipador — apenas um Buff

Se, após a seleção de alvo, só existir um Buff válido:

```text
[Alvo]
→ único Buff elegível
→ commit
```

Não criar:

```text
1 Buff
[1]
```

quando não resta decisão.

### 59.21 Dissipador — Registro de Combate

Para efeito não acumulável:

```text
🧪 **Luiken** usa **{Dissipador}** em **{Inimigo}**.
✨ **{Efeito}** · Removido
```

Para efeito acumulável:

```text
🧪 **Luiken** usa **{Dissipador}** em **{Inimigo}**.
✨ **{Efeito}** · 1 Acúmulo Removido
```

Não mostrar:

```text
stack mais antigo removido
dispell roll
sem teste de acerto
RNG = 0
```

Esses detalhes não pertencem ao player-facing.

### 59.22 Dissipador — atualização da HUD

Depois do commit:

- Buff integralmente removido desaparece da HUD;
- Buff acumulável permanece com a quantidade atualizada;
- não criar banner separado de sucesso.

O Registro de Combate comunica a ação.

### 59.23 Preparado de Resguardo — fluxo

Resguardo possui alvo próprio.

```text
[Consumível]
→ [Preparado de Resguardo]
→ commit
→ HUD normal
```

Não existe:

- seleção de alvo;
- confirmação;
- tela adicional de uso.

### 59.24 Preparado de Resguardo — HUD

Depois da aplicação:

```text
👉 {emoji da Classe} {Personagem}
❤️ {HP atual} / {HP máximo}
{barra de HP}

🛡️ Resguardo · 2T · 1 Carga
```

Com duração restante:

```text
🛡️ Resguardo · 1T · 1 Carga
```

Nova aplicação válida volta para:

```text
🛡️ Resguardo · 2T · 1 Carga
```

Nunca mostrar:

```text
🛡️ Resguardo · 2 Cargas
```

### 59.25 Proteção + Resguardo simultâneos

Como representam efeitos distintos, ambos aparecem:

```text
👉 {emoji da Classe} {Personagem}
❤️ {HP atual} / {HP máximo}
{barra de HP}

🔰 Barreira · {valor} · {T}
🛡️ Resguardo · {T} · 1 Carga
```

Não agrupar como:

```text
🛡️ Proteções · 2
```

porque o jogador precisa conhecer separadamente:

- valor da Barreira;
- duração;
- carga de Resguardo.

### 59.26 Consumo do Resguardo

Quando uma aplicação elegível de efeito negativo seria aplicada:

1. o Dano Direto associado resolve normalmente;
2. o Efeito Negativo elegível é bloqueado;
3. a carga de Resguardo é consumida;
4. a linha de Resguardo desaparece;
5. o Registro comunica o bloqueio.

Exemplo:

```text
⚔️ **{Inimigo}** causa `126` de dano a **Luiken**.
🛡️ Resguardo bloqueia **Sangramento** em **Luiken**.
```

Não mostrar depois:

```text
🛡️ Resguardo · 0 Cargas
```

O efeito já terminou.

### 59.27 Resguardo contra aplicação multi-stack

Quando toda uma aplicação multi-stack elegível for bloqueada como um único evento:

```text
🛡️ Resguardo bloqueia **{Efeito}** em **{Personagem}**.
```

é suficiente.

A UI não precisa explicar a regra de atomicidade daquela aplicação.

### 59.28 Resguardo expirado sem uso

Ao expirar:

- remover da HUD;
- não criar tela;
- não criar notificação especial de “não utilizado”.

Se a HUD/Registro normal já comunicar expiração de efeitos, Resguardo pode seguir exatamente esse padrão geral.

### 59.29 Validação no commit

Toda escolha é revalidada imediatamente antes do commit.

Isso vale para:

- item;
- quantidade;
- turno;
- Recarga compartilhada;
- limite do conteúdo;
- alvo;
- efeito escolhido;
- estado do combate.

A UI nunca força uma seleção antiga a continuar válida.

Uma tentativa rejeitada antes do commit:

- não consome o Consumível;
- não consome a ação;
- não concede efeito;
- não escolhe automaticamente uma alternativa diferente.

### 59.30 Consumível deixou de estar disponível

Se o Consumível deixar de existir ou ser utilizável depois de a tela ter sido aberta:

```text
🧪 Consumíveis
Turno {X} · {Personagem}

⚠️ Consumível · Não está mais disponível.

{lista atualizada de Consumíveis válidos}

[1] [2]

[← Combate]
```

Não criar página de erro.

Se nenhuma opção continuar válida, reconstruir a HUD normal e remover `[Consumível]`.

### 59.31 Recarga compartilhada tornou a ação inválida

Se CD2 já estiver vigente no momento da revalidação:

retornar à HUD autoritativa.

Feedback contextual:

```text
⏳ Consumíveis · Em Recarga
```

`[Consumível]` deixa de aparecer enquanto nenhuma opção puder ser utilizada.

Não manter a seleção antiga aberta.

### 59.32 Limite de Consumíveis atingido

Quando o limite aplicável tiver sido alcançado:

```text
🔒 Consumíveis · Limite Atingido
```

Reconstruir a HUD normal.

`[Consumível]` desaparece.

Não criar:

```text
[Consumível 🔒]
```

ou botão desabilitado equivalente.

### 59.33 Alvo do Dissipador ficou inválido

Se o inimigo selecionado:

- for Derrotado;
- deixar o encontro;
- deixar de possuir Buff removível;
- ficar inválido por regra normal;

o item não é consumido.

Se outros alvos válidos existirem:

```text
✨ Dissipador · Escolha o Alvo

⚠️ Alvo · Não está mais disponível.

1 🐺 {Alvo válido}
2 🕷️ {Alvo válido}

[1] [2]

[← Consumíveis]
```

Se nenhum permanecer:

retornar aos Consumíveis com aviso:

```text
⚠️ Dissipador · Sem Alvo Válido
```

e retirar o Dissipador da lista atualizada.

### 59.34 Buff escolhido ficou inválido

Se o efeito escolhido:

- expirar;
- for removido;
- for substituído;
- tornar-se não removível;
- deixar de existir;

o Dissipador não é gasto.

Se ainda houver outros Buffs elegíveis:

```text
✨ Dissipador · Escolha o Efeito

⚠️ Efeito · Não está mais disponível.

1 🟢 {Efeito válido}
2 🟢 {Efeito válido}

[1] [2]

[← Alvos]
```

Quando a etapa de alvo tiver sido automática:

```text
[← Consumíveis]
```

Se nenhum Buff válido permanecer:

```text
⚠️ Dissipador · Sem Efeito Removível
```

e retornar à seleção de Consumíveis atualizada.

### 59.35 Estado geral do combate mudou

Se antes do commit:

- o Turno terminou;
- outra ação já foi consolidada;
- o personagem foi Derrotado;
- o encontro terminou;
- o combate passou para outro estado;

a tela antiga é descartada.

Reconstruir diretamente a HUD/resultados autoritativos atuais.

Não mostrar linguagem técnica como:

```text
Callback Expirado
Estado Inválido
Session Mismatch
Commit Rejeitado
```

### 59.36 Retornos oficiais

Seleção de Consumíveis:

```text
[← Combate]
```

Seleção de alvo:

```text
[← Consumíveis]
```

Seleção de efeito após escolha manual de alvo:

```text
[← Alvos]
```

Seleção de efeito com alvo automático:

```text
[← Consumíveis]
```

Não usar `[← Voltar]` quando o destino já é conhecido.

### 59.37 Confirmação de uso

Uso normal de Consumível em combate **não possui confirmação adicional**.

Não criar:

```text
⚠️ Usar Consumível?

[Confirmar Uso]
[Cancelar]
```

A escolha do Consumível e, quando necessário, do alvo/efeito já expressa intenção suficiente.

### 59.38 Registro de Combate

Consumíveis seguem o Registro global:

```text
📜 Registro de Combate · Recentes
```

com linguagem curta e natural.

#### Cura

```text
🧪 **Luiken** usa **Poção de Cura do Vale**.
❤️ **Luiken** recupera `220` HP.
```

#### Purificação

```text
🧪 **Luiken** usa **Preparado de Purificação Enredada**.
✨ **{Efeito Negativo}** · Removido
```

#### Antídoto

```text
🧪 **Luiken** usa **Antídoto de Turfa**.
☣️ **{DoT}** · Removido
```

#### Proteção

```text
🧪 **Luiken** usa **Preparado de Proteção Enredada**.
🔰 Barreira · `120` · `2T`
```

#### Dissipador

```text
🧪 **Luiken** usa **{Dissipador}** em **{Inimigo}**.
✨ **{Efeito Positivo}** · Removido
```

#### Resguardo

Aplicação:

```text
🧪 **Luiken** usa **{Preparado de Resguardo}**.
🛡️ Resguardo · `2T` · `1 Carga`
```

Ativação:

```text
🛡️ Resguardo bloqueia **{Efeito Negativo}** em **Luiken**.
```

Não criar página de sucesso para nenhuma dessas ações.

### 59.39 Ronda de Caça

Este fechamento não adiciona nenhuma das três novas famílias à automação da Ronda.

Portanto:

- Preparado de Proteção não entra em Uso Automático;
- Dissipador não entra em Uso Automático;
- Preparado de Resguardo não entra em Uso Automático.

Mesmo se estiverem no Inventário, não passam a aparecer na tela:

```text
🧪 Consumíveis da Ronda
```

como elegíveis para automação apenas por este fechamento.

Permanecem válidos somente os Consumíveis já explicitamente aprovados para a Ronda.

### 59.40 PvP

Nada muda.

PvP não mostra:

```text
[Consumível]
```

para Consumíveis externos.

Proteção, Dissipador e Resguardo não criam exceção.

### 59.41 Fluxo resumido — Preparado de Proteção

```text
HUD
→ [Consumível]
→ lista padronizada
→ [Preparado de Proteção]
→ commit
→ HUD

🔰 Barreira · valor · 2T
```

Sem:

- alvo;
- confirmação;
- tela de sucesso.

### 59.42 Fluxo resumido — Dissipador

#### Múltiplos alvos + múltiplos Buffs

```text
HUD
→ [Consumível]
→ Dissipador
→ Escolha o Alvo
→ Escolha o Efeito
→ commit
→ HUD
```

#### Um alvo + vários Buffs

```text
HUD
→ [Consumível]
→ Dissipador
→ Escolha o Efeito
→ commit
```

#### Vários alvos, mas apenas um elegível

```text
HUD
→ [Consumível]
→ Dissipador
→ alvo automático
→ Escolha o Efeito, se necessário
```

#### Uma única combinação válida

```text
HUD
→ [Consumível]
→ Dissipador
→ commit direto
```

Nunca criar uma etapa cuja única função seja selecionar a única escolha existente.

### 59.43 Fluxo resumido — Preparado de Resguardo

```text
HUD
→ [Consumível]
→ Preparado de Resguardo
→ commit
→ HUD

🛡️ Resguardo · 2T · 1 Carga
```

Quando ativado:

```text
Ação inimiga
→ Dano Direto resolve normalmente
→ primeira aplicação negativa elegível é bloqueada
→ Registro comunica bloqueio
→ Resguardo desaparece
```

### 59.44 Padrão final das famílias

A apresentação passa a seguir esta família visual:

```text
🧪 {Nome do Consumível}
{ícone funcional} {efeito resumido}
```

Exemplos:

```text
🧪 Poção de Cura
❤️ Cura

🧪 Preparado de Purificação
✨ Purificação

🧪 Antídoto
☣️ Antídoto

🧪 Poção de Vigor
⚡ Vigor

🧪 Preparado de Proteção
🔰 Barreira

🧪 Dissipador
✨ Dissipação

🧪 Preparado de Resguardo
🛡️ Resguardo
```

Assim, nenhum dos três Consumíveis novos recebe uma linguagem visual privilegiada ou mais detalhada que as famílias antigas.

### 59.45 Decisões finais

Ficam fechados:

- `🧪` como identidade global de Consumíveis;
- Inventário usa `Consumível · Grau {Grau}`, sem terceira informação na mesma linha;
- família/função não é repetida na listagem geral do Inventário;
- família/função permanece disponível no detalhe e na seleção contextual de combate;
- template comum de Inventário para famílias antigas e novas;
- template comum da seleção `[Consumível]`;
- segunda linha funcional compacta na seleção de combate;
- números + `[1] [2] [3]` para seleção de Consumíveis;
- Preparado de Proteção aplicado diretamente ao próprio personagem;
- Dissipador com seleção dinâmica de inimigo e Buff;
- etapas sem escolha real são automaticamente puladas no Dissipador;
- Preparado de Resguardo aplicado diretamente ao próprio personagem;
- `🔰 Barreira · {valor} · {T}` na HUD;
- `🛡️ Resguardo · {T} · 1 Carga` na HUD;
- consumo do Resguardo comunicado pelo Registro;
- Dissipação comunicada pelo Registro;
- uso normal sem confirmação;
- revalidação autoritativa antes do commit;
- tentativa inválida antes do commit não consome item;
- retornos semânticos `[← Combate]`, `[← Consumíveis]` e `[← Alvos]`;
- Poção de Vigor permanece fora da seleção de combate;
- nenhuma nova família passa a ser automatizada pela Ronda;
- PvP permanece sem Consumíveis externos.

### 59.46 Impacto

Este fechamento altera somente:

- Visual/UI;
- nomenclatura player-facing;
- disposição das escolhas;
- feedback da HUD;
- Registro de Combate;
- navegação de seleção de Consumíveis.

Não altera:

- efeitos;
- potência;
- duração;
- número de cargas;
- stacking;
- materiais;
- custos;
- Graus;
- requisitos de Alquimia;
- CD2 compartilhado;
- limites de uso;
- economia;
- RNG;
- regras de alvo;
- efeitos protegidos;
- Hard CC;
- PvP;
- automação da Ronda;
- IA;
- balanceamento.

As famílias antigas não sofrem mudança mecânica. Sua presença neste fechamento serve exclusivamente para estabelecer o **mesmo padrão visual que passa a reger todos os Consumíveis de Asterion**.


---

## 60. P2 — Fuligem sem Fogo e Charneca da Fuligem

Esta seção fecha a apresentação player-facing de P2 conforme TDO v1.0.5. Regras gerais de Missões, Mapa, resultados e Códice permanecem, exceto onde P2 é especificada.

### 60.1 Disponibilidade e início com Alda

P2 só inicia após **P1 concluída** e no **Nv.3+**. S1 não é requisito. Antes disso, raiz de Missões não mostra P2 ativa, suspensa ou em andamento, nem progresso ou recompensa reservada.

Quando elegível, interação com Alda no Refúgio apresenta: “A fuligem sem fogo significa que alguém chegou antes de nós — ou que estamos olhando para o problema errado.” A escolha explícita da interação inicia a Missão e leva ao contexto da Etapa 1 no mesmo fluxo, sem tela separada de confirmação, `[Aceitar]` redundante ou sucesso genérico. A raiz passa a mostrar `📜 Fuligem sem Fogo · Em Andamento`; detalhe usa o template global de Missão Principal.

### 60.2 Detalhe da Missão Principal

```text
📜 Fuligem sem Fogo
Missão Principal · Terras do Ocaso

🎯 Objetivo · Viajar até a Charneca da Fuligem
📍 Destino contextual · Charneca da Fuligem
🎁 Recompensas · 3.300 XP · 140 Coroas · 1 Ferro de Fuligem · 2 Ervas Cinzentas · 1 Resíduo do Ocaso

[Ver Objetivo]
[← Missões]
```

Antes da chegada, `[Ver Objetivo]` abre a rota contextual; Charneca não aparece como Local conhecido nem recebe `[Ver no Mapa]`. Após descoberta na chegada, `[Ver no Mapa]` pode aparecer quando ela for o Local pertinente. Estado, objetivo, Local e recompensas seguem o template global.

| Etapa | Objetivo player-facing | Local pertinente |
|---|---|---|
| 1 | `Viajar até a Charneca da Fuligem` | Charneca como destino contextual, ainda desconhecido |
| 2 | `Examinar Pontos de Fuligem · {0/3}` | Charneca da Fuligem |
| 3 | `Derrotar a ameaça na Charneca` | Charneca da Fuligem |
| 3 após Derrota | `Derrotar a ameaça na Charneca` | Charneca; recovery no Refúgio |
| 4 | `Examinar a Pedra Marcada` | Charneca (ponto de interesse) |
| 5 | `Levar o registro a Oren Cal` | Charneca → Refúgio por retorno contextual |
| 6 | `Reportar a situação a Alda Veyr` | Refúgio do Ocaso |

A viagem de retorno ao Refúgio é navegação dentro das etapas 5–6, não cria uma etapa adicional nem usa Travessia dos Braseiros.

### 60.3 Etapa 1 — rota contextual e chegada

```text
📜 Fuligem sem Fogo · Etapa 1
🎯 Objetivo · Viajar até a Charneca da Fuligem

[Seguir para a Charneca]
[← Missões]
```

Charneca desconhecida não aparece no Mapa nem como destino de Travessia por Braseiro. Usar ação contextual específica, sem `[Continuar]` genérico. Na chegada válida, descobrir permanentemente o Local, atualizar Local atual e concluir Etapa 1 de forma atômica/idempotente. Mapa, WorldState e reconnect passam a reconhecê-lo. Não mostrar `🔥 Braseiro · Descoberto`: Vento Morto depende de Desbravar Nv.4. A descoberta não libera conteúdo normal; a etapa contextual tem prioridade.

### 60.4 Etapa 2 — três Pontos de Fuligem

```text
📜 Fuligem sem Fogo · Etapa 2
🎯 Objetivo · Examinar Pontos de Fuligem · {0/3}

[Ponto de Fuligem · 1] [Ponto de Fuligem · 2]
[Ponto de Fuligem · 3]
[← Missões]
```

Mostrar apenas pontos pendentes; contador persistido `0/3 → 1/3 → 2/3 → 3/3`. Pontos fixos, examináveis em qualquer ordem, com identidade estável e sem depender da posição de callback. Reconnect mostra somente pendentes. Não conceder XP/item/Material, nem criar três entradas de Códice/lore nova. Terceiro exame conclui e abre diretamente o combate, sem confirmação.

### 60.5 Etapa 3 — combate, Derrota e retry

Objetivo: `Derrotar a ameaça na Charneca`.

No fluxo novo válido (P1 concluída, Nv.3+), mostrar **Aranha de Cinza · Nv.3**, fixa mesmo se o personagem tiver Nv.4+, sem escalar com o jogador. Configuração: categoria Incomum, perfil Bestiário `RARE`, arquétipo Controlador, Solo, encontro roteirizado de Missão, sem Variante e `variant_roll=false`. Não consultar nem sortear o pool normal de Caçada, nem usar Cão, Cervo ou Elite. Peregrino Calcinado é fallback apenas para estado legado/inconsistente.

Usar HUD e recibo normal. Encontro não consome Vigor nem concede Coroas, Material, Saque ou Equipamento de Caçada. Vitória aplica a fórmula global normal de XP de inimigo com `enemy_level=3` e `CategoryMultiplier=1,35` (Incomum), além dos demais fatores globais pertinentes; sem override de tutorial, tabela paralela de Caçada ou redução de Vigor.

Quando a Aranha for materializada e identificada legitimamente pela primeira vez, pode registrar uma única vez primeira Observação válida, Habitat da Charneca e primeiro contato/combate quando os respectivos marcos globais forem validados. A Observação não depende de Vitória e o conhecimento registrado antes de uma Derrota permanece. Se ainda elegível, o bônus global de primeira observação usa `FixedPercentXP`, `reference_level=3`, `1% × XP_ref(3)=1% × 6.600=66 XP`; pode ser concedido no momento da Observação mesmo se a tentativa terminar em Derrota. Reconnect/retry não repete o bônus.

Somente Vitória registra primeira vitória e evidências cuja condição global exija Vitória. Derrota não concede XP de vitória do inimigo nem apaga conhecimento legitimamente observado antes dela. Demais BKP/evidências de Observação, primeiro combate, Arte/comportamento, Habitat e Missão seguem suas condições globais normais.

Derrota encerra tentativa e recovery ocorre no `🔥 Braseiro do Refúgio`: HP 100%, estados comuns removidos, Vigor e Consumíveis não restaurados. P2 permanece na Etapa 3 com o mesmo objetivo `Derrotar a ameaça na Charneca`; etapas 1–2 e descoberta ficam concluídas; sem prêmio final. Após recovery, ação específica, por exemplo `[Enfrentar a Aranha de Cinza]`, cria tentativa com novo `encounter_id`, mesma Aranha Nv.3, sem reroll e HP integral. Reconnect de combate ativo retoma o mesmo ID. Callback stale/duplicado não repete XP/Bestiário/etapa. Só Vitória conclui Etapa 3, concede XP normal do inimigo e registra marcos condicionados à Vitória; Observação e bônus já legitimamente obtidos antes da Derrota permanecem e não se repetem.

### 60.6 Etapa 4 — Pedra Marcada

Objetivo `Examinar a Pedra Marcada`, ação contextual `[Examinar]`. A Pedra é ponto de interesse, não Local, sub-Local ou item. Exame registra evidência e cria/atualiza `📖 Marcas na Fuligem`, sem XP de Desbravar/item/Material e sem consumir o resultado único sistêmico de Desbravar. O resultado de Desbravar Nv.4 `Pedra Marcada` continua elegível uma vez e pode conceder os `193 XP` aprovados quando legitimamente obtido; trata-se de investigação sistêmica mais profunda do ponto conhecido, não de uma segunda Pedra nem da primeira aparição visual.

### 60.7 Etapas 5 e 6 — Oren e Alda

Após examinar a Pedra, a tela de Etapa 5 permanece na Charneca e oferece o retorno contextual:

```text
📜 Fuligem sem Fogo · Etapa 5
🎯 Objetivo · Levar o registro a Oren Cal

[Retornar ao Refúgio]
[← Missões]
```

`[Retornar ao Refúgio]` é backtracking narrativo pela rota já percorrida, exclusivo da progressão válida de P2. Não é Travessia dos Braseiros, teleport, Braseiro, descoberta, Caçada, Desbravar ou etapa adicional; não custa Vigor/Coroas, não concede XP/recompensa e não cria encontro. A ação atualiza o Local atual para `Refúgio do Ocaso`, preserva progresso e descoberta da Charneca, e abre diretamente o contexto de Oren. Antes dela, reconnect reconstrói a tela na Charneca com o botão; depois, reconstrói Oren no Refúgio. A Travessia genérica continua exigindo os Braseiros permanentes apropriados.

Oren só é atendido no Refúgio. Objetivo: `Levar o registro a Oren Cal`.

```text
✒️ Oren Cal
“Esta marca não é decoração. Também não vou chamá-la de escrita até termos prova.”
[Conversar]
[← Missões]
```

Conversa válida ali conclui etapa 5. Em seguida, `Reportar a situação a Alda Veyr`; conversa válida com Alda também exige Refúgio e conclui P2. Diálogo/relatório remoto não progride a Missão.

### 60.8 Conclusão e recibo

```text
🏆 Fuligem sem Fogo · Concluída
✨ XP · 3.300
🪙 Coroas · 140
⛏️ Ferro de Fuligem · 1
🌿 Erva Cinzenta · 2
💧 Resíduo do Ocaso · 1
```

Seguir recibo global XP → Coroas → Materiais → Equipamento/outros. Consolidar nível e respeitar capacidade do Inventário/Entregas Pendentes; entrega pendente permitida pela Fonte não bloqueia conclusão. Callback/reconnect/retry não duplica recompensa.

### 60.9 Mapa e conteúdo local

**Antes da chegada:** Charneca não é Local conhecido, não aparece no Mapa, não recebe `[Ver no Mapa]` e não tem Travessia por Braseiro; pode ser destino contextual. **Após chegar:** Mapa/WorldState/reconnect refletem descoberta/Local atual; não marcar Vento Morto descoberto.

Durante P2, conteúdo contextual tem prioridade e conteúdo normal permanece fechado. Após concluir P2, Caçada Manual/Desbravar ficam disponíveis conforme gates próprios. Ronda permanece `🔒 Ronda de Caça · Vença uma Caçada neste Local` até a primeira Vitória manual válida em Caçada na Charneca. Vitória na Estrada não desbloqueia a Ronda local; familiaridade é por Local.

Não antecipar Vento Morto (Desbravar Nv.4), Entrada da Cripta (Desbravar Nv.4+) ou Cervo (pool Nv.4). Preservar pool/pesos e ausência de Elite natural.

### 60.10 Persistência e mídia

Reconstruir etapa, pontos, tentativa, descoberta e Local a partir do estado autoritativo persistido. Callback stale/duplicado, reconnect ou troca de dispositivo não duplica progresso, XP, Bestiário ou recompensa. Tentativa derrotada encerra; retry só nasce por ação contextual após recovery. Interações validam Local/estado. Imagem é opcional; fallback textual funciona sem asset ou media key novo.


**Sincronização vigente:** Fonte Mestra v1.4.7 + Terras do Ocaso v1.0.5 FINAL + Vales dos Enforcados v1.0.2 FINAL. Esta consolidação substitui a Fonte Visual/UI sincronizada anterior e versões anteriores como autoridade de apresentação geral da vertical slice e da segunda Região.

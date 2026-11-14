# Asterion — Moldes visuais do bot (v1, rascunho para aprovação)

Escopo: só aparência (texto, emojis, botões, barras). Nenhuma regra de jogo, número ou conteúdo narrativo muda.
Textos de lore são preservados; só mudam de lugar ou de formatação.

## Regras gerais

- Formatação em HTML do Telegram (`parse_mode=HTML`). Fim do Markdown com `*` literal.
- Sem divisores (`───`) em nenhuma tela.
- Linha em branco só entre grupos. Nunca entre linhas do mesmo grupo.
- Títulos em negrito, sem CAIXA ALTA. Separador de informação: `·`.
- Lore em citação (`<blockquote>`), nunca em itálico solto. Texto longo usa `<blockquote expandable>`.
- Todo botão tem emoji e rótulo curto (até ~14 caracteres, para não ser cortado em 2 colunas). Sem números nos botões.
- Cada tela tem no máximo ~15 linhas e ~10 botões. O que sobra vai para "Mais" ou para uma tela de detalhe.
- Texto de apoio que repete os botões é removido.
- Moeda se chama Coroas.

## Fichas (tokens) visuais

- Barra do Hub: 10 quadrados, em linha própria abaixo do rótulo e do valor.
- Barra de combate: 8 quadrados, na mesma linha, `❤️ 611/713 🟩🟩🟩🟩🟩🟩🟩⬛`. Se quebrar de linha em tela pequena, cai para linha própria.
- Cores: HP dinâmico (🟩 acima de 60%, 🟨 acima de 30%, 🟥 abaixo), Vigor 🟨, XP 🟦, HP de inimigo sempre 🟥, vazio ⬛.
- Estados: 🔥 em andamento, ✅ concluído, ▫️ pendente, 🔒 bloqueado, 📍 local atual.
- Ícones fixos: 🌑 Asterion, 🗺️ Aventura/Mapa, 👤 Personagem, 📜 Missão, 🎁 Recompensas, 🎯 Objetivo, ⚔️ Combate, 🏪 Mercado, 🪙 Coroas, ✨ XP, ⚡ Vigor, ❤️ HP, 🎒 Mochila, ⚠️ Aviso, ← Voltar.

## Molde 1 — Hub

```
🌑 Asterion · Terras do Ocaso
📍 Estrada das Cinzas

[RSN] Tess · Nv. 1
🛡️ Sentinela · Vigia · Legado II

❤️ HP 713/713
🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩
⚡ Vigor 100/100
🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨
✨ XP 320/4.800
🟦⬛⬛⬛⬛⬛⬛⬛⬛⬛

📜 Vozes na Estrada
```
- Linha de identidade: linha 1 `[TAG] Nome · Nv. X` (tag só se estiver em guilda). Linha 2 `Classe · Caminho · Legado` (cada parte só se existir, sem estrela).
- O parágrafo de lore sai do Hub. Aparece em "Local Atual" (e, a decidir, ao entrar numa região nova).
- O nome da região no cabeçalho e a faixa de nível ficam em aberto (ver Pendências).
- Botões (2 colunas): 🗺️ Aventura, 👤 Personagem, 📖 Códice, 📅 Calendário, 🤝 Vínculos, 🏪 Mercado, 🏆 Classificação, 🎁 Benefícios, 💬 Comunidade, ⚙️ Configurações.

## Molde 2 — Menu de seção (Aventura, Personagem)

Título, uma linha de contexto, botões. Sem lista de texto que repita os botões. A frase final em itálico de Personagem ("Cada cicatriz aqui tem dono e data...") é mantida.

## Molde 3 — Lista (Missões, Mapa, Inventário, Códice, Ranking, Mercado)

```
📜 Missões · 1 ativa

🔥 Vozes na Estrada

Secundárias
🔒 Vigília sem Voz
🔒 A Luz que Não Aquece
```
- Cada item é um botão com o nome (sem número). Embaixo: `‹ 1/2 ›` e `← Aventura`.
- Requisitos longos ("Requer ... concluída") vão para a tela de detalhe da missão bloqueada.
- Sem nível nem região nas linhas (decisão do autor: mapa é de descoberta).

## Molde 4 — Detalhe (missão, item, local)

```
🔥 Vozes na Estrada

▎A chama deixada para trás desaparece
▎pouco a pouco entre a fuligem...

🎯 Objetivo
Seguir pela Estrada das Cinzas

🎁 Recompensas
✨ 2.400 XP
🪙 120 Coroas
📦 Ferro de Fuligem ×1
📦 Couro Escoriado ×1
```
- O estado vai como ícone no título. Sem "Principal · Região · Em andamento".
- Recompensas uma por linha. Botões: 🎯 Ver Objetivo, 🗺️ Ver no Mapa, ← Missões.

## Molde 5 — Combate (turno)

```
⚔️ Turno 4

🐺 Cão Cinéreo
❤️ 99/244 🟥🟥🟥⬛⬛⬛⬛⬛

🛡️ Tess
❤️ 639/713 🟩🟩🟩🟩🟩🟩🟩⬛

▎Tess usa Defender.
▎Cão Cinéreo usa Investida Cinérea: 18 de dano.
▎Tess usa Golpe de Guarda: 76 de dano. ♻️ Retaliação (restam 0)
▎Cão Cinéreo usa Mordida Cinérea: 28 de dano.
```
- Lore de abertura só no turno 1, em citação. Nunca repete.
- Inimigo sempre em cima, jogador embaixo. Sem 👉.
- Log mostra só as últimas 3 a 4 ações, em frase curta. A informação de efeitos é mantida de forma abreviada.
- A lista "Atacar · Causa Dano / Defender · Reduz Dano..." sai da mensagem. A explicação aparece só no turno 1.
- Botões: ⚔️ Atacar, 🛡️ Defender, e uma linha por habilidade com recarga, por exemplo `🗡️ Golpe de Guarda · CD1`.

## Molde 6 — Resultado (vitória e derrota)

```
🏆 Vitória · Cão Cinéreo

🎁 Recompensas
✨ +100 XP
🪙 +15 Coroas
📦 Anel das Sombras de Pedra Alta ×1

📜 Vozes na Estrada
▫️ Guardião Ósseo Profanado 2/10
▫️ Javali Corrompido das Ruínas 1/5

🎒 Mochila 21/25
```
- Derrota: `💀 Derrota · Nome` e um bloco curto com o que foi perdido, se houver.
- Botões: ⚔️ Caçar de novo, 🗺️ Mapa, 📜 Ver log.

## Molde 7 — Mapa e viagem

```
🗺️ Mapa
📍 Estrada das Cinzas

Regiões conhecidas
```
- Botões: um por região conhecida, `📍 Nome` para a atual, `🔒 Nome` para a bloqueada. Paginação e `← Aventura`.
- Regiões não descobertas não aparecem. Sem faixa de nível e sem lore por região na lista.

## Molde 8 — Mercado

```
🏪 Mercado
🪙 52 Coroas

Toque num item para ver detalhes.
```
- Itens como botões: `🟢 Poção de Vida · 🪙149` (ponto de raridade só se o item tiver raridade).
- Detalhe do item: nome, efeito em uma linha, preço, e botões de quantidade `+1`, `+10`, `+100` com o total, mais `✍️ Digitar` e `← Mercado`.

## Molde 9 — Confirmação

```
⚠️ Excluir personagem

Esta ação não pode ser desfeita.
Digite o nome do personagem para confirmar.
```
Botões: ✅ Confirmar, ✖️ Cancelar. Mostra custo e consequência em linhas curtas.

## Molde 10 — Narrativa (Prólogo, cenas)

Imagem opcional, texto em citação, um botão de continuar.

## Plano de implementação (uma etapa por PR, pequenos)

Regra de trabalho (decisão do autor): fazer UMA etapa por vez. Ao terminar a etapa, abrir o PR, esperar CI verde e AVISAR o autor. O autor testa no celular e só então o PR é mergeado e a próxima etapa começa. Nunca antecipar etapas seguintes.

1. `src/asterion/bot/ui_kit.py`: funções `identidade()`, `barra()`, `bloco()`, `citacao()`, `grade_botoes()`, `paginacao()`, com testes unitários. Mais o Hub.
2. Menus, listas e detalhes: Aventura, Personagem, Missões, Mapa, Códice.
3. Combate e resultado.
4. Mercado, Inventário, Equipamentos, Ofícios, Guilda.
5. As telas restantes.

Testes que comparam texto exato vão precisar de atualização. O banco descartável da regra do projeto continua valendo.

## Pendências (não decididas)

- Mapa de descoberta (estilo Elden Ring): se a região aparece no cabeçalho do Hub e como a faixa de nível é exibida. Decidir depois de ver o visual pronto.
- Banners e imagens por tela: usar `asset_catalog.py` (em rascunho) ou não.
- Rótulos longos (ex.: "Classificação da Vida...") precisam de nome curto aprovado pelo autor.

# Criação persistente: implementação e operação

Escopo: criação até a tela inicial de **Cinzas na Estrada**. Esta implementação foi concluída sob a Fonte Mestra v1.4.1 / Baseline Numérica v1.0. A Fonte vigente passou a ser **GDD Estrutural v1.4.2**, que substitui integralmente a v1.4.1; o próximo bloco de prólogo/combate deve adotar o ruleset v1.4.2 e migrar qualquer marcador técnico ainda preso à versão anterior antes de instanciar o primeiro combate. Texto e botões:
`docs/specs/CHARACTER_CREATION_UI.md`. As passivas e Artes são apresentadas com o
conteúdo oficial; nenhuma mecânica de combate é implementada nesta etapa.

## Estado e identidade

- `accounts.telegram_id` identifica uma conta em todos os dispositivos.
- `ASTERION_SERVER_ID` identifica o servidor lógico da implantação. Não é chat,
  dispositivo nem parâmetro aceito do callback. Polling e webhook do mesmo servidor
  devem usar a mesma configuração e banco.
- `creation_drafts` contém tela atual, versão, nome, raça, classe, contexto de edição
  e eventual erro de nome. Páginas de detalhe também são persistidas.
- `characters` contém as escolhas definitivas, `stage=cinzas_na_estrada:intro` e
  `ruleset_version=gdd-1.4.1-baseline-1.0`.
- Não existe estado crítico em FSM, Redis ou `message_id`. O router atende chats
  privados; a identidade vem de `from_user.id`, não do autor da mensagem do bot.

## Transações e callbacks

Os comandos bloqueiam a linha da conta com `SELECT ... FOR UPDATE`. A criação
inicial da conta usa `INSERT ... ON CONFLICT DO NOTHING`, protegendo também dois
`/start` simultâneos antes de existir draft.

Cada callback contém UUID do draft, versão e intenção. A aplicação valida conta,
servidor, UUID, versão e se a intenção corresponde à tela atual antes de alterar o
draft. Callback obsoleto reconstrói a tela vigente sem modificar o estado. Callback
sem draft não cria conta nem inicia criação. Entrada textual usa `update_id` do
Telegram em `creation_inputs` para deduplicação persistente, inclusive após retornar
à edição do nome; esse identificador não determina nenhuma regra de gameplay.

Na confirmação, uma única transação revalida o nome, insere o personagem com o
estágio inicial do prólogo e conclui o draft. Constraints garantem um personagem
por conta/servidor e índice único `(server_id, lower(name))` arbitra a disputa de
nomes entre contas. Se houver conflito, o draft volta ao erro de Nome, preservando
Raça e Classe; um nome disponível retorna à confirmação. O nome não é reservado
por drafts incompletos.

Após o commit, a apresentação Telegram pode falhar sem desfazer a criação.
`/start` ou retry recuperam o mesmo personagem. O outbox existente é preservado;
este fluxo não depende de entrega garantida de notificação nem grava recompensas
ou efeitos econômicos. `Seguir pela Estrada` apenas reconhece a intenção e
reconstrói a tela, sem mudar estágio ou iniciar combate **na implementação atual**. A Fonte Mestra v1.4.2 agora define que esse botão cria o primeiro encontro Foreground autoritativo; essa transição pertence ao próximo bloco de implementação.

## Política de nomes

Formato ASCII estrito de 3–16 letras, sem remoção silenciosa de espaços. A
capitalização visual usa inicial maiúscula e demais letras minúsculas. O banco
também valida o formato final. `ASTERION_BLOCKED_CHARACTER_NAMES` recebe um array
JSON da política editorial oficial (ofensivos, reservados e administrativos).
O padrão é vazio porque essa lista ainda não foi fornecida. A política é verificada
ao enviar o nome e na confirmação final. Alterações de configuração exigem reinício
dos processos, com a mesma política em todas as instâncias.

## Mídia opcional

`ASTERION_CREATION_IMAGES` recebe um objeto JSON com as chaves:

- `name`, `race`, `class`, `confirm`;
- `race:remanescente`, `race:velado`, `race:cinereo`, `race:hemario`, `race:alvorano`;
- `class:sentinela`, `class:errante`, `class:vigia`, `class:tecelao`, `class:oraculo`,
  `class:luminar`;
- `cinzas_na_estrada:intro`.

Cada valor é um `file_id` oficial do Telegram ou um caminho com prefixo `file:`.
Arquivo ausente ou chave sem configuração usa texto + teclado inline. Nenhuma
imagem é incluída, gerada ou baixada nesta implementação. As imagens futuras em
pixel art são responsabilidade dos assets oficiais. Os textos cabem no limite de
legenda do Telegram sem truncamento. Quando possível, callbacks editam a mensagem
ou mídia existente; mensagens removidas/ineditáveis têm fallback de novo envio.

## Validação

`ruff check .` e `pytest` com `ASTERION_TEST_DATABASE_URL` definido executam lint,
testes existentes, regras de nome, contrato textual com a especificação,
roteamento aiogram, limites de callback/legenda e integração em PostgreSQL real.
O CI disponibiliza PostgreSQL 16. Os testes verificam disputa sincronizada do
mesmo nome, confirmações simultâneas, retomada por conexão nova, edição,
deduplicação, escopo por servidor, constraints, rollback e falha Telegram após
commit. A migration é validada com upgrade, downgrade, novo upgrade e
`alembic check` contra os modelos.

# Autoridade das Fontes

## Fonte Mestra vigente

A implementação do Asterion deve usar como autoridade principal:

**ASTERION — GDD Estrutural v1.4.1 — Fonte Mestra Consolidada**

Estado oficial da fonte:

- estrutural e numericamente fechada para implementação e testes;
- Baseline Numérica v1.0 consolidada;
- substitui integralmente v1.4 e todas as versões anteriores;
- nenhuma regra da baseline de lançamento permanece numericamente aberta.

O marcador `SIMULAR` continua existindo apenas para mecânicas futuras ou explicitamente reabertas por Balanceamento. Ele não deve ser usado para ignorar um valor já definido na Baseline Numérica v1.0.

## Fonte Visual/UI

A apresentação player-facing deve seguir:

**ASTERION — Consolidação de Visual & UI — atualização 2026-09-20**

Ela é subordinada à Fonte Mestra para regras mecânicas e números. Sua função é definir nomenclatura, texto, estrutura de telas, navegação, estados visuais e UX do Bot do Telegram.

Quando um mockup usar nome, recompensa ou número apenas ilustrativo, isso não cria regra mecânica. Quando a Fonte Mestra já definir o valor correspondente, o valor da Fonte Mestra prevalece.

## Regra para implementação

Antes de implementar um sistema:

1. localizar a regra estrutural/mecânica na Fonte Mestra;
2. localizar a apresentação correspondente na Fonte Visual/UI;
3. não inventar comportamento para preencher lacunas;
4. registrar conflito real em vez de escolher silenciosamente uma interpretação;
5. preservar IDs estáveis, idempotência, estado autoritativo e `ruleset_version` onde aplicável.

## Baseline atual relevante

A criação de personagem está fechada em alto nível:

`/start → nome → raça → classe → confirmação final → prólogo Cinzas na Estrada`

Regras centrais:

- 1 conta Telegram = 1 personagem por servidor;
- nome com 3–16 letras A–Z, sem acentos, números, espaços ou símbolos;
- unicidade do nome por servidor, comparação case-insensitive;
- nomes ofensivos, reservados ou administrativos são bloqueados;
- Raça e Classe são permanentes no lançamento;
- `/start` recupera personagem persistente existente;
- callbacks antigos ou inválidos falham com segurança;
- sem personagem existente, `/start` entra diretamente em Nome do Personagem;
- não existe tela intermediária "Novo Personagem";
- Caminho e Aparência não são escolhidos durante a criação;
- não existe tela de "personagem criado com sucesso"; a confirmação final entra diretamente no prólogo.

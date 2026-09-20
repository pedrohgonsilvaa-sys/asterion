# Autoridade das Fontes

## Fonte Mestra vigente

A implementação do Asterion deve usar como autoridade principal:

**ASTERION — GDD Estrutural v1.4.2 — Fonte Mestra Consolidada**

Estado oficial da fonte:

- a v1.4.2 substitui integralmente a v1.4.1 e todas as versões anteriores;
- a Baseline Numérica v1.0 permanece autoritativa para implementação e testes;
- existe uma única reabertura numérica pontual vigente: a **conversão absoluta da unidade global de XP de inimigo**, descrita na seção 49.7;
- essa reabertura bloqueia a implementação econômica/repetível que dependa dessa conversão global, como Caçadas, Ronda de Caça e XP interno repetível de Masmorras;
- ela **não** bloqueia conteúdo único/story cuja recompensa fixa esteja explicitamente definida, como os **320 XP totais** do primeiro encontro do prólogo.

O marcador `SIMULAR` continua existindo para mecânicas futuras ou explicitamente reabertas. Não deve ser usado para ignorar um valor já consolidado na Baseline Numérica v1.0.

## Fonte Visual/UI

A apresentação player-facing deve seguir:

**ASTERION — Consolidação de Visual & UI — atualização 2026-09-20, sincronizada com a Fonte Mestra v1.4.2**

Ela é subordinada à Fonte Mestra para regras mecânicas e números. Sua função é definir nomenclatura, texto, estrutura de telas, navegação, estados visuais e UX do Bot do Telegram.

Quando um mockup usar nome, recompensa ou número apenas ilustrativo, isso não cria regra mecânica. Quando a Fonte Mestra já definir o valor correspondente, o valor da Fonte Mestra prevalece.

## Regra para implementação

Antes de implementar um sistema:

1. localizar a regra estrutural/mecânica na Fonte Mestra;
2. localizar a apresentação correspondente na Fonte Visual/UI;
3. não inventar comportamento para preencher lacunas;
4. registrar conflito real em vez de escolher silenciosamente uma interpretação;
5. preservar IDs estáveis, idempotência, estado autoritativo, transações e `ruleset_version` onde aplicável;
6. não transformar a reabertura de XP global em uma fórmula implícita.

## Baseline atual relevante — criação

O fluxo autoritativo permanece:

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

## Baseline atual relevante — primeiro combate do prólogo

A v1.4.2 formaliza o primeiro encontro de **Cinzas na Estrada**:

- `[Seguir pela Estrada]` cria um encontro Foreground autoritativo e persistente;
- inimigo: **Cão Cinéreo**, Nv.1, Comum, Predador, sem Variante, Solo;
- atributos finais: **244 HP / 50 ATQ / 45 DEF / 56 AGI**;
- ações: **Mordida Cinérea 100% ATQ** e **Investida Cinérea 120% ATQ**;
- IA normal após a máscara pedagógica: **Mordida → Mordida → Investida → repetir**;
- tutorial: `[Atacar] [Defender]` simultaneamente; após a primeira escolha, a ação pedagógica ainda não usada vira a única válida; depois de ambas, revelar e exigir a primeira Arte da Classe; após seu uso, liberar HUD e IA normais;
- recompensa total fixa: **320 XP**;
- **0 Vigor**, sem Saque, Coroas ou Materiais;
- essa ocorrência pode registrar o Cão Cinéreo no Bestiário, mas não dispara separadamente o bônus genérico de 1% de XP da primeira observação;
- HP e barras na UI são sempre derivados do estado autoritativo real.

A especificação focada para implementação está em `docs/specs/PROLOGUE_FIRST_COMBAT_V1.4.2.md`.

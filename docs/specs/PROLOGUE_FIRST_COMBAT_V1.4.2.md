# Especificação de implementação — Primeiro Combate do Prólogo (v1.4.2)

> Escopo focado para o próximo bloco de desenvolvimento. Autoridade mecânica: **ASTERION — GDD Estrutural v1.4.2 / Baseline Numérica v1.0**. Autoridade player-facing: **Fonte Visual/UI sincronizada com v1.4.2**. Em qualquer conflito, a Fonte Mestra prevalece.

## 1. Limite do bloco

Implementar:

`[Seguir pela Estrada] → criação/retomada de atividade Foreground → primeiro combate com Cão Cinéreo → tutorial de Atacar/Defender/primeira Arte → vitória e estado persistente pós-combate`.

Não implementar neste bloco:

- primeiro Braseiro;
- Descansar;
- Menu Principal;
- Caçadas/Ronda;
- XP global de inimigos;
- Saque/economia repetível.

Ao vencer, persistir um estágio pós-combate inequívoco e pronto para a próxima etapa do prólogo, sem inventar UI adicional além do necessário para reconstruir o estado.

## 2. Estado autoritativo e recuperação

Ao acionar `[Seguir pela Estrada]`, criar ou retomar um único encontro Foreground autoritativo do personagem.

A implementação deve possuir IDs estáveis, no mínimo equivalentes a:

- `game_activity_id`;
- `encounter_id`;
- `combat_id`;
- `state_version`;
- `ruleset_version = gdd-1.4.2-baseline-1.0`.

PostgreSQL é a autoridade. Telegram, `message_id`, FSM e Redis não podem ser a única fonte do estado.

`/start`, reconnect, callback repetido/antigo, mensagem apagada e uso em outro dispositivo devem reconstruir o mesmo combate ou o estado pós-combate sem duplicar encontro, turno, dano ou recompensa.

A transição a partir do estágio antigo `cinzas_na_estrada:intro` deve ser idempotente. A implementação atual ainda contém marcadores técnicos v1.4.1; o próximo bloco deve atualizar/migrar o que for necessário antes de instanciar o combate v1.4.2.

## 3. Curva inerente das Classes

`G(n)=4^((n-60)/59)`

Para cada Classe `C`, atributo `A ∈ {HP, ATQ, DEF, AGI}` e `1≤n≤60`:

`ClassStat_C,A(n) = round_half_up(ClassStat_C,A(60) × G(n))`.

Valores Nv.60:

| Classe | HP | ATQ | DEF | AGI |
|---|---:|---:|---:|---:|
| Sentinela | 2808 | 368 | 324 | 276 |
| Errante | 2470 | 424 | 282 | 330 |
| Vigia | 2522 | 420 | 288 | 321 |
| Tecelão | 2418 | 436 | 273 | 300 |
| Oráculo | 2574 | 400 | 291 | 309 |
| Luminar | 2678 | 384 | 309 | 288 |

Vetores Nv.1 oficiais de verificação:

| Classe | HP | ATQ | DEF | AGI |
|---|---:|---:|---:|---:|
| Sentinela | 702 | 92 | 81 | 69 |
| Errante | 618 | 106 | 71 | 83 |
| Vigia | 631 | 105 | 72 | 80 |
| Tecelão | 605 | 109 | 68 | 75 |
| Oráculo | 644 | 100 | 73 | 77 |
| Luminar | 670 | 96 | 77 | 72 |

## 4. Raças relevantes ao primeiro combate

- **Remanescente:** +1,5% a HP Máximo, ATQ, DEF e AGI estáticos finais. Aplica-se depois de Equipamento/Runas/Encantamentos e antes de Buffs/Debuffs e floors/caps.
- **Velado:** efeitos elegíveis de duração; não muda os atributos base deste encontro. RNG racial, quando aplicável, deve ser determinístico pelo combate.
- **Cinéreo:** Defender 45% → **52%**.
- **Hemário:** enquanto HP ≤40%, +12% Vampirismo racial, cura resultante limitada a 3% do HP Máximo por ação elegível.
- **Alvorano:** +5% AGI estático final; magnitude de Debuffs numéricos removíveis recebidos −12%.

Não inventar Equipamento, Talento, Caminho ou bônus adicionais no prólogo. O teste conservador oficial considera o personagem sem essas fontes.

## 5. Fundamentos de combate necessários

### Turnos e iniciativa

- combate por turnos;
- iniciativa por AGI, maior para menor, uma vez por rodada;
- mudança de AGI afeta a próxima rodada;
- empate de AGI usa prioridade determinística definida no início pelo RNG do `combat_id` e permanece estável durante a luta.

### Dano

Dano bruto:

`ATQ × coeficiente`

Redução por DEF:

`DEF / [DEF + (100 + 5 × nível do atacante)]`

Perfuração e redução de DEF entram antes da fórmula de DEF.

Usar alta precisão internamente. Dano final positivo usa `floor` apenas no final e mínimo 1 após acerto válido, salvo efeito que zere explicitamente.

Chance-base de Crítico: **5%**. Dano crítico-base: **150%**.

Para este encontro, Esquiva e Bloqueio base são 0% quando nenhuma outra fonte os concede.

### Universais

- Ataque Básico: **100% ATQ**, Dano Direto, um inimigo, sem Recarga.
- Defender: reduz **45%** do Dano Direto até o próximo turno; Cinéreo usa **52%**.
- Defender não pode ser executado em oportunidades consecutivas nas quais ele foi de fato usado.

## 6. Primeiras Artes Nv.1

| Classe | Arte | Efeito |
|---|---|---|
| Sentinela | Golpe de Guarda | 110% ATQ, CD2 |
| Errante | Corte Veloz | 115% ATQ, CD2 |
| Vigia | Disparo Preciso | 115% ATQ, CD2 |
| Tecelão | Fio Cortante | 120% ATQ, CD2 |
| Oráculo | Sinal Funesto | 105% ATQ + −8% ATQ por 2T, CD2 |
| Luminar | Fulgor | 110% ATQ, CD2 |

A Arte já está aprendida no Nv.1. O tutorial controla apenas quando o botão é revelado.

Recarga, conforme Fonte Mestra §10.2: uma skill CD2 usada no T1 fica indisponível
no T2 e volta no T3. O turno de uso não é o primeiro tick do cooldown. Cooldowns
avançam por oportunidade de turno do proprietário: uso em N bloqueia N+1 e permite
novo uso em N+2.

## 7. K(level) e composição de inimigos

Centro neutro Nv.60:

`K60 = (2578,333333… HP; 405,333333… ATQ; 294,5 DEF; 304 AGI)`.

Por atributo:

`K_A(n)=K60_A × G(n)`.

Atributo final:

`EnemyStat = round_half_up(K_A(level) × Category_A × Archetype_A × Variant_A × Content_A × Group_A)`.

Regras:

- alta precisão intermediária;
- multiplicador ausente = 1,00;
- nenhum arredondamento intermediário;
- um único `round_half_up` no atributo final.

Categoria Solo **Comum**, conforme Fonte Mestra §49.6:

- HP 70%;
- ATQ 82%;
- DEF 90%;
- AGI 95%.

Esses fatores `Category_A` entram na composição antes de qualquer arredondamento,
junto de Arquétipo, Variante, Conteúdo e Grupo. Comum não equivale a 1,00.

## 8. Cão Cinéreo — primeiro encontro oficial

- Nível: 1
- Categoria: Comum
- Arquétipo: Predador
- Variante: nenhuma
- Grupo: Solo ×1,00
- Tipo: encontro único, narrativo e tutorial

Predador:

- HP 90%
- ATQ 110%
- DEF 90%
- AGI 120%

Perfil de conteúdo `prologue_first_combat`:

- HP 0,60
- ATQ 0,55
- DEF 0,75
- AGI 0,65

Resultado final obrigatório:

- **244 HP**
- **50 ATQ**
- **45 DEF**
- **56 AGI**

Ações:

- **Mordida Cinérea:** 100% ATQ, Dano Direto, um alvo.
- **Investida Cinérea:** 120% ATQ, Dano Direto, um alvo.

IA normal, depois da máscara pedagógica:

`Mordida → Mordida → Investida → repetir`.

Sem RNG na escolha de ação do Cão.

## 9. Máquina pedagógica

### T0

Mostrar simultaneamente:

`[Atacar] [Defender]`

O jogador escolhe livremente.

### Se Atacar vier primeiro

1. executar Ataque Básico;
2. Cão responde com Mordida Cinérea;
3. na próxima oportunidade do jogador, somente Defender é ação pedagógica válida;
4. executar Defender;
5. Cão responde com Investida Cinérea, demonstrando a mitigação.

### Se Defender vier primeiro

1. executar Defender;
2. Cão responde com Investida Cinérea;
3. na próxima oportunidade do jogador, somente Atacar é ação pedagógica válida;
4. executar Ataque Básico;
5. Cão responde com Mordida Cinérea.

### Depois de ambos

- revelar somente a primeira Arte da Classe como próxima ação pedagógica;
- exigir um uso válido;
- se a Arte derrotar o Cão, encerrar o combate antes de qualquer resposta inimiga;
- se o Cão sobreviver, remover a máscara pedagógica e iniciar a IA normal pela primeira **Mordida** do ciclo;
- liberar a HUD normal compatível com as regras implementadas.

A máscara pedagógica não muda desbloqueio, dano, Recarga, iniciativa ou demais regras mecânicas.

## 10. Recompensa e Bestiário

Ao vencer:

- **320 XP totais do tutorial**;
- **0 Vigor**;
- sem Saque;
- 0 Coroas;
- nenhum Material.

Os 320 XP são uma recompensa fixa do conteúdo e **não** definem a conversão absoluta da unidade global de XP de inimigo.

A ocorrência pode registrar a primeira observação/evidência do Cão Cinéreo no Bestiário, mas **não pode conceder separadamente** o bônus genérico de 1% de XP da primeira observação. O pacote de 320 XP substitui qualquer XP adicional de descoberta/Bestiário produzido por esta ocorrência específica.

A concessão de XP deve ser idempotente e transacional. Repetição de callback, reconnect, retry de Telegram ou reexecução não pode conceder XP novamente.

A conversão global de `Comum 1,00 / Incomum 1,35 / Elite 2,75 / Chefe 6,00` para XP absoluto permanece explicitamente aberta e não deve ser inferida.

## 11. UI player-facing

A abertura já existente permanece:

```text
🔥 Cinzas na Estrada
Prólogo · Terras do Ocaso

O mundo desperta sob um céu sem cor. Cinzas atravessam a estrada como neve morta, cobrindo pedras, árvores retorcidas e os restos de algo que um dia talvez tenha sido um caminho seguro. À frente, entre a névoa e o silêncio, formas quebradas marcam a direção de sua primeira jornada.

[Seguir pela Estrada]
```

Primeira HUD do combate:

```text
Turno 1 · {nome}

🐺 Cão Cinéreo
❤️ 244 / 244
{barra de HP real}

Um rosnado rompe o silêncio da estrada. Entre as cinzas, uma criatura faminta avança para impedir sua passagem.

👉 {emoji da Classe} {nome}
❤️ {HP atual} / {HP máximo}
{barra de HP real}

📜 Registro de Combate · Recentes

🐺 Cão Cinéreo bloqueia o caminho.

⚔️ Atacar · Causa Dano
🛡️ Defender · Reduz Dano até seu próximo Turno

[Atacar] [Defender]
```

Os marcadores entre chaves são valores dinâmicos do renderer e nunca aparecem literalmente.

Regras:

- sem tag de Guilda no prólogo;
- não acrescentar nível nem nome textual da Classe ao lado do personagem na HUD de combate; o emoji identifica a Classe;
- HP e barras vêm do estado autoritativo real;
- não usar `240/240`, `132/240` ou `SIMULAR/SIMULAR` no combate;
- depois de usar Atacar/Defender, mostrar somente a ação pedagógica restante;
- depois de ambos, mostrar somente a primeira Arte da Classe;
- não criar popup entre fundamentos e Arte;
- preferir editar a mesma mensagem/mídia quando apropriado;
- assets contextuais permanecem opcionais; ausência de asset usa fallback textual sem placeholder literal.

## 12. Testes mínimos do próximo PR

Cobrir, no mínimo:

- curva de Classe Nv.1 e vetores oficiais;
- `K(level)` e Cão Cinéreo = 244/50/45/56;
- dano/DEF, Crítico e `floor` com vetores determinísticos;
- Defender 45% e Cinéreo 52%;
- iniciativa por AGI e desempate determinístico por `combat_id`;
- todas as seis primeiras Artes;
- Sinal Funesto e duração de 2T;
- entrada idempotente por `Seguir pela Estrada`;
- somente uma atividade Foreground do personagem;
- duas ordens pedagógicas: Atacar→Defender→Arte e Defender→Atacar→Arte;
- callbacks inválidos, obsoletos, duplicados e de outro ator;
- dois dispositivos concorrentes;
- reinício/reconnect em cada passo;
- morte do Cão pela Arte sem resposta posterior;
- sobrevivência do Cão após Arte iniciando IA normal em Mordida;
- ciclo normal Mordida→Mordida→Investida;
- 320 XP concedidos exatamente uma vez;
- nenhum Saque/Coroa/Material/Vigor;
- suppress do XP adicional de primeira observação desta ocorrência;
- reconstrução da HUD a partir do backend;
- falha Telegram após commit sem rollback do estado de jogo;
- lint e suíte completa em PostgreSQL real.

## 13. Pendência explícita que não pertence a este PR

Não definir nem implementar `EnemyXPBase(level)` ou fórmula equivalente para conteúdo econômico/repetível. Essa conversão permanece reaberta na Fonte Mestra v1.4.2 e deve ser fechada somente quando a densidade real da primeira jornada permitir validação.

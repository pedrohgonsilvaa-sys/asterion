# ASTERION — World Events Design
## v1.0.0 — decisões consolidadas

Documento de referência das decisões aprovadas no redesenho dos Eventos Mundiais. Itens marcados como ABERTO não são regras canônicas.

## 1. Princípios
- Um Evento Mundial é uma ocorrência global única.
- O evento pode ser dividido em múltiplas Frentes simultâneas.
- O jogo informa estado e consequências, mas não recomenda onde o jogador deve ir.
- Não existe distribuição automática nem limite de participantes por Frente.
- Contribuição não é sinônimo de dano.
- World Events não usam o limite normal de grupos de 4.
- Backend é a fonte de verdade.

## 2. Estrutura
EVENTO MUNDIAL → FRENTE → combate/objetivo → estado global

Uma Frente é uma unidade jogável e pode representar localização, batalha, defesa, ritual, criatura, estrutura ou outro objetivo definido pelo conteúdo. Frentes podem ser criadas, resolvidas, colapsar ou ser substituídas.

## 3. Estados do Evento
- \`AGENDADO\`: existe, mas ainda indisponível.
- \`ABERTO\`: disponível para entrada e pode iniciar atividade.
- \`EM ANDAMENTO\`: evento ativo.
- \`CONCLUÍDO\`: condição global de sucesso atingida.
- \`FRACASSADO\`: condição global de fracasso atingida.
- \`ENCERRADO\`: estado terminal após resolução/entrega.

A janela inicial de 15 minutos não é um lobby obrigatório. O evento pode executar Rodadas durante ela. No deadline, uma Rodada já em \`RESOLVENDO\` termina antes da avaliação global.

## 4. Estados da Frente
- \`ATIVA\`
- \`RESOLVENDO\`
- \`RESOLVIDA\`
- \`COLAPSADA\`
- \`SUBSTITUÍDA\`

Transições principais: \`ATIVA → RESOLVENDO → ATIVA/RESOLVIDA/COLAPSADA\` e \`ATIVA → SUBSTITUÍDA → nova ATIVA\`.

Quando uma Frente deixa de estar ATIVA, seus participantes são removidos e retornam ao painel de Frentes. Sem perda de Vigor ou punição. O significado exato de resolvida, colapsada e substituída é definido pelo conteúdo.

## 5. Participação
- Entrada em Frente não iniciada: normal.
- Entrada durante Rodada: aguarda o próximo ciclo.
- Troca de Frente: permitida.
- Após sair, há intervalo de 1 Rodada antes de agir na nova Frente.
- Saída voluntária: permitida, sem punição pesada.
- Frente sem jogadores não recebe NPCs automaticamente.
- Consequências de deixar uma Frente vazia são estratégicas.

Entrada, saída e troca não alteram retroativamente decisões já comprometidas.

## 6. Rodadas simultâneas
Cada Frente é um combate compartilhado, não uma coleção de combates individuais contra o mesmo HP.

Fluxo:
1. início da Rodada;
2. janela de decisão;
3. cada jogador escolhe uma Ação;
4. Ação é registrada;
5. janela fecha;
6. Ações são validadas;
7. resultados são calculados com o mesmo estado inicial;
8. resultados são aplicados em lote;
9. inimigo, mortes, efeitos de fim, objetivo e mudanças de fase são resolvidos;
10. novo estado e próxima Rodada.

Clique/latência não determina ordem. A resolução usa o motor oficial de combate de Asterion.

Regra:
Toda Ação válida no início da resolução participa da Rodada. Ações não são canceladas pela resolução de outras Ações da mesma Rodada, salvo quando a própria regra da Ação determinar explicitamente o contrário.

## 7. Ações
Universais:
- ⚔️ Atacar
- 🛡️ Defender

Artes Ativas equipadas aparecem diretamente na tela principal. Não existe menu separado de Artes. Máximo de 3 Artes Ativas equipadas, conforme o sistema canônico.

Ações específicas de Frente podem existir quando o conteúdo exigir.

Fluxo: Escolher → Registrar → Fechar Rodada → Resolver.

Não existe Alterar Ação. Se houver um único alvo válido, a seleção pode ser omitida. Se houver múltiplos, o jogador escolhe. Se a Ação ficar inválida e não houver alternativa definida pela própria Ação, ela falha sem efeito.

## 8. AFK
- 1 Rodada sem Ação: AFK 1/3.
- 2 Rodadas consecutivas: AFK 2/3.
- 3 Rodadas consecutivas: remoção da Frente.
- Uma Rodada com Ação reseta o contador.

Pode reentrar enquanto o evento estiver ativo, respeitando o intervalo de entrada/troca.

## 9. Suporte e histórico
Título: \`🤝 Suporte:\`.

Mostrar somente suporte diretamente dirigido a outros participantes. Ataques, debuffs, marcas e ofensivas não entram nesse bloco. Se não houver suporte na Rodada atual, o bloco inteiro não aparece.

Histórico usa \`📜 Histórico:\` e somente nomenclatura/efeitos canônicos.

## 10. Tela principal da Frente
Estrutura aprovada de referência:

🔥 Fornalha Abandonada

⚔️ Rodada 12 · ⏱️ 00:08

[estado da criatura/objetivo]
❤️ 6.840 / 9.000
[barra de HP]

[telegráfo quando necessário]

🤝 Suporte:
[suportes da Rodada, se houver]

📜 Histórico:
[eventos relevantes]

[⚔️ Atacar]
[🛡️ Defender]
[Arte 1]
[Arte 2]
[Arte 3]
[👥 Participantes]
[↩️ Frentes]

Após registrar: \`✅ Ação registrada.\` A tela principal não precisa ser reescrita a cada clique.

## 11. Tela de Frentes
A visão geral mostra informação essencial sem obrigar abertura de cada Frente.

Exemplo estrutural:

🔥 O Cerco das Cinzas
⏱️ Evento em andamento
⚔️ Fase atual · 2/3
⏳ Tempo restante · 18:42

🔥 Frentes Ativas

🔥 Portões de Cinza
👥 18 participantes
🎯 [objetivo]

🔥 Fornalha Abandonada
👥 7 participantes
🎯 [objetivo]

🌫️ Estrada das Cinzas
👥 3 participantes
🎯 [objetivo]

[🔥 Portões de Cinza]
[🔥 Fornalha Abandonada]
[🌫️ Estrada das Cinzas]
[🔙 Voltar]

Contagens simples de participantes usam números normais, não monoespaçados. Frente indisponível não recebe botão de entrada; mostra apenas seu estado.

## 12. Participantes
- 5 por página.
- Ícone/classe canônico antes do nome.
- HP numérico + barra de 10 blocos.
- Sem efeitos/debuffs nessa tela.
- Paginação simples.

## 13. IA inimiga
Reutilizar o motor de combate existente; não criar um segundo sistema de IA para World Events.

Aprovado:
- inimigo participa em cada Rodada;
- IA escolhe ação e alvo antes das escolhas dos jogadores;
- prioridades antes da aleatoriedade;
- empates por RNG determinístico;
- ações importantes/perigosas podem ter telegráfo;
- ataques normais não precisam de telegráfo;
- telegráfo informa, não recomenda;
- decisão inimiga fica comprometida;
- AoE/múltiplos alvos seguem o motor existente;
- mudanças de fase ocorrem após a Rodada;
- comportamento pode mudar por fase.

Não existe regra universal de menor HP; preferência de alvo pertence à Ação/conteúdo.

## 14. GDD já canônico
Agenda: terça, quinta e sábado; 12:00 e 20:00; America/Sao_Paulo.
- 3 fases;
- duração esperada 30–45 min;
- deadline 60 min;
- entrada inicial 15 min;
- reentrada 2 min;
- HP N^0.88, cap 200;
- ATQ +1,5% por participante adicional, cap +60%;
- contribuição: mínimo 2 fases + 8 Ações significativas;
- contribuição maior vale 4;
- 10 Vigor;
- recompensa-base: 0,40×C + 2 materiais básicos + 1 Fragmento;
- XP: 8% da referência de nível.

## 15. ABERTO
1. Anatomia completa de uma Frente.
2. Tipos de objetivo e como cada um é medido.
3. Frentes de cada Evento.
4. Objetivos reais de cada Frente.
5. Condições de criação, progresso, resolução, colapso e substituição.
6. Vitória/fracasso global de cada evento.
7. Mecânicas específicas de cada Frente.
8. Duração exata da janela de decisão.
9. Balanceamento de escala entre múltiplas Frentes.
10. Contribuição distribuída entre Frentes e recompensas por objetivos sem dano.
11. UI para mudanças especiais durante o evento.
12. Migração final para código e testes.

## 16. Exemplos NÃO canônicos
Portões de Cinza, Fornalha Abandonada, Estrada das Cinzas e os objetivos “Defender os Portões”, “Controlar a Fornalha” e “Manter a Estrada” são exemplos de UI até serem definidos pelo conteúdo. Números de HP/participantes e ícones de personagens usados nos exemplos também não são canônicos.

## Próxima etapa
Definir a anatomia de uma Frente: o que ela precisa ter, tipos de objetivo, medição, início, progresso, resolução/colapso e informações visíveis ao jogador. Depois disso, preencheremos os Eventos Mundiais concretos.

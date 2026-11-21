# ASTERION — World Events Design
## v2.0.0 — Proposta completa para aceite

**Status:** PROPOSTA COMPLETA. Esta versão fecha as lacunas de design do redesenho de Eventos Mundiais. Não deve ser tratada como canon aprovado até aceite explícito.

**Base:** GDD Estrutural v1.6.0 + conteúdo regional atual + decisões já consolidadas no documento v1.0.0. Onde a Fonte Mestra não define uma regra necessária para Frentes simultâneas, esta versão registra uma **decisão de proposta**.

---

# 1. Objetivo

Transformar Eventos Mundiais de uma sequência de combates individuais contra o mesmo HP em uma **ocorrência global única com múltiplas Frentes simultâneas**, mantendo:

- 3 fases;
- duração esperada de 30–45 min;
- deadline de 60 min;
- janela inicial de entrada de 15 min;
- reentrada após derrota de 2 min;
- scaling congelado por fase;
- contribuição individual;
- recompensa econômica já publicada;
- backend como autoridade;
- integração com o motor de combate existente.

O redesign não cria um segundo motor de combate.

---

# 2. Regras que continuam canônicas

Permanecem exatamente como publicadas no GDD:

- agenda: terça, quinta e sábado;
- horários: 12:00 e 20:00;
- fuso: America/Sao_Paulo;
- 3 fases;
- duração esperada: 30–45 min;
- deadline: 60 min;
- entrada inicial: primeiros 15 min ou até o início da fase final;
- reentrada após derrota: 2 min;
- HP scaling por N^0,88;
- N limitado a 200 para scaling;
- ATQ +1,5% por participante adicional, limitado a +60%;
- scaling congelado por fase;
- elegibilidade: pelo menos 2 fases + 8 Ações Significativas;
- major_contribution vale 4 pontos;
- 10 Vigor;
- recompensa-base: 0,40 × C + 2 materiais básicos + 1 Fragmento;
- XP: 8% da referência de nível;
- Configuração de Combate permanece travada durante a participação;
- HP compartilhado é atômico dentro do encontro;
- overkill não passa automaticamente para outra forma/fase.

Fonte: GDD Estrutural v1.6.0, especialmente §§21, 39 e 49.15. fileciteturn167file0 fileciteturn167file9

---

# 3. Decisão central

## 3.1 Estrutura

O Evento Mundial passa a ter uma ocorrência global única:

EVENTO → FASE → 3 FRENTES SIMULTÂNEAS → RODADAS → RESULTADO DA FASE → PRÓXIMA FASE

O jogador nunca entra em uma luta privada contra o mesmo chefe.

Cada Frente é um combate/objetivo compartilhado por todos os personagens que escolherem aquela Frente.

## 3.2 Limite de Frentes

Existem **exatamente 3 Frentes ativas por vez**.

Cada Frente pode representar:

- combate;
- defesa;
- progresso;
- sobrevivência;
- contenção;
- ritual;
- estrutura;
- criatura;
- local;
- outro objetivo específico do conteúdo.

A implementação usa modelos simples. A UI mostra apenas o objetivo compreensível ao jogador.

## 3.3 Um único relógio de Rodada

Todas as Frentes usam a **mesma Rodada global**.

Portanto:

- Rodada 12 é Rodada 12 em todas as Frentes;
- todas abrem e fecham a janela juntas;
- todas resolvem juntas;
- não existem relógios paralelos;
- entrada no meio da Rodada significa aguardar a próxima Rodada.

---

# 4. Papel das três Frentes

Cada fase possui:

### Frente principal
- contém a criatura da fase publicada no catálogo do Evento;
- usa HP compartilhado único;
- é obrigatória para a conclusão da fase.

### Duas Frentes alternativas
- representam outros problemas simultâneos;
- podem ser combate ou objetivo não combatente;
- pelo menos uma precisa ser resolvida;
- ambas colapsadas significam fracasso da fase.

Regra:

FASE SUCEDE = Frente Principal Resolvida + pelo menos 1 Frente Alternativa Resolvida

FASE FALHA = Frente Principal Colapsada OU as 2 Alternativas Colapsadas

Isso cria escolha estratégica sem recomendar onde o jogador deve ir.

A informação é factual; a decisão é do jogador.

---

# 5. Anatomia completa de uma Frente

Toda Frente possui no backend:

- front_id;
- occurrence_id;
- phase;
- slot;
- nome;
- descrição curta;
- objetivo principal;
- condição de sucesso;
- condição de fracasso;
- estado mensurável;
- estado da Frente;
- regras de entrada;
- ação contextual, quando houver;
- regras de IA/ambiente, quando houver;
- telegraphs, quando houver;
- estado de substituição;
- referência de conteúdo;
- histórico de resolução;
- vínculo com as participações.

O estado mensurável deve ser simples o suficiente para aparecer no Telegram.

Exemplos:

❤️ 6840 / 9000

🛡️ Integridade 72 / 100

🎯 Progresso 47 / 100

⏳ 8 / 12 rodadas

Não existe uma barra genérica de “contribuição da Frente”.

---

# 6. Modelos de objetivo

A proposta usa quatro modelos técnicos.

## 6.1 Derrotar

Estado = HP.

Sucesso:

HP ≤ 0

Usado para a criatura da fase.

## 6.2 Preservar

Estado = Integridade.

Sucesso = condição de preservação atingida.

Fracasso:

Integridade ≤ 0

Pode representar defesa de estrutura, rota, mecanismo ou elemento do conteúdo.

## 6.3 Progredir

Estado = Progresso.

Sucesso:

Progresso = máximo

Fracasso = condição explicitamente definida pelo conteúdo.

## 6.4 Suportar

A Frente exige sobreviver por determinada quantidade de Rodadas ou até uma condição externa.

Sucesso = condição atingida.

Fracasso = condição crítica atingida.

Não existe um motor separado para “Controle”, “Recuperação”, “Contenção” ou “Catástrofe”. Esses conceitos são expressos por Preservar, Progredir ou Suportar.

---

# 7. Regra de objetivo único

Uma Frente possui **um objetivo principal por vez**.

Se houver múltiplas etapas:

- são sequenciais;
- a segunda só começa quando a primeira termina;
- não existem duas barras de objetivos simultâneas por padrão.

Exemplo:

Progredir → Preservar → Derrotar

Apenas uma etapa está ativa por vez.

---

# 8. Estados da Frente

Estados:

- ATIVA;
- RESOLVENDO;
- RESOLVIDA;
- COLAPSADA;
- SUBSTITUÍDA.

### ATIVA
Recebe participantes, ações e novas Rodadas.

### RESOLVENDO
Estado interno curto. Não aceita novas ações, entradas ou nova Rodada.

### RESOLVIDA
Objetivo cumprido.

### COLAPSADA
Condição de fracasso atingida.

### SUBSTITUÍDA
A Frente terminou por regra de conteúdo sem contar como sucesso ou fracasso.

Quando existir substituta:

SUBSTITUÍDA → nova Frente ATIVA

Limite: no máximo 1 substituição por slot por fase.

---

# 9. Transições

ATIVA → RESOLVENDO → RESOLVIDA

ATIVA → RESOLVENDO → COLAPSADA

ATIVA → SUBSTITUÍDA → nova ATIVA

Quando uma Frente termina:

1. consolida a Rodada;
2. remove participantes daquela Frente;
3. devolve todos ao painel de Frentes;
4. não aplica punição econômica;
5. reavalia a fase.

---

# 10. Progressão da fase

A fase é avaliada **somente depois da resolução consolidada da Rodada**.

Nunca existe cancelamento de uma Ação porque outra Ação chegou primeiro.

Depois da resolução:

1. atualizar HP/Integridade/Progresso;
2. aplicar derrotas;
3. aplicar triggers;
4. aplicar pós-evento;
5. limpar efeitos expirados;
6. avaliar Frentes;
7. avaliar a fase;
8. iniciar nova fase, se necessário;
9. iniciar próxima Rodada.

Isso segue a simultaneidade já definida no GDD. fileciteturn167file9

---

# 11. Fases do Evento

Todo Evento continua tendo exatamente 3 fases.

Cada fase possui:

- 1 Frente principal;
- 2 Frentes alternativas;
- 1 condição de avanço;
- 1 condição de fracasso.

A mudança de fase ocorre somente no limite entre Rodadas.

Quando a fase termina:

- Frentes restantes são encerradas;
- participantes retornam ao painel;
- 3 novas Frentes são criadas;
- jogadores escolhem novamente;
- o scaling da nova fase recebe novo snapshot.

---

# 12. Resultado global

## Sucesso

As três fases foram concluídas.

## Fracasso

Ocorre quando:

- uma fase falha;
- ou o deadline é atingido sem sucesso global.

## Deadline

Se o deadline chegar durante uma Rodada:

1. fecha a janela;
2. resolve a Rodada aberta;
3. não cria nova Rodada;
4. avalia fase;
5. avalia Evento;
6. entra em encerramento.

---

# 13. Estado do Evento

Estados:

- AGENDADO;
- ABERTO;
- EM ANDAMENTO;
- CONCLUÍDO;
- FRACASSADO;
- ENCERRADO.

ABERTO não é lobby.

O Evento pode iniciar Rodadas durante sua janela inicial.

---

# 14. Início real das Rodadas

O Evento abre no horário.

A primeira Rodada começa quando houver pelo menos um participante.

Depois disso:

- o relógio continua;
- ausência de jogadores não pausa o Evento;
- não surgem NPCs substitutos;
- Frentes podem avançar ou colapsar segundo suas próprias regras.

---

# 15. Janela de decisão

Valor fechado nesta proposta:

**20 segundos por Rodada.**

Fluxo:

- 20s de decisão;
- fechamento;
- resolução autoritativa;
- próxima Rodada.

Todas as Frentes compartilham a janela.

---

# 16. Ações

Universais:

- ⚔️ Atacar;
- 🛡️ Defender.

As até 3 Artes Ativas equipadas aparecem diretamente.

Consumíveis seguem o sistema PvE existente e o limite publicado para a ocorrência.

Uma Frente pode apresentar **1 Ação Contextual especial por vez**, quando o conteúdo exigir.

Exemplo:

[🔧 Interagir]

Não existe catálogo universal de ações contextuais.

---

# 17. Registro da Ação

Fluxo:

Escolher → Registrar → Fechar Rodada → Resolver

Depois do registro:

✅ Ação registrada.

Não existe “Alterar Ação”.

O jogador pode navegar. A Ação continua comprometida.

---

# 18. Validação

No registro:

- personagem;
- participação;
- Rodada;
- lock;
- ação;
- alvo;
- Recarga;
- recursos;
- condições.

No fechamento:

- revalidar estado autoritativo;
- manter a Ação que continuar válida;
- rejeitar a que realmente se tornou inválida;
- não cancelar uma Ação válida apenas porque outra Ação mudou o estado.

Sem alternativa explícita:

sem efeito.

Não converter automaticamente para Defender.

---

# 19. Simultaneidade

Todas as Ações da Rodada usam o mesmo estado pré-Rodada.

Ordem:

1. evento primário;
2. prevenção/substituição;
3. dano/cura;
4. estado final;
5. derrotas;
6. triggers;
7. pós-evento;
8. limpeza de expirados;
9. avaliação da Frente;
10. avaliação da fase.

Duas Ações válidas no mesmo alvo continuam válidas.

Clique/latência não decide prioridade.

---

# 20. Entrada em Frente

Antes da primeira Rodada: entrada normal.

Durante Rodada:

- participação aceita;
- nenhuma Ação naquela Rodada;
- começa a atuar na próxima.

Frente encerrada:

- entrada bloqueada.

---

# 21. Movimento entre Frentes

O personagem só pode estar em **uma Frente por vez**.

Pode trocar de Frente.

Ao trocar voluntariamente:

- Ação já registrada continua na Frente anterior;
- nova Frente é registrada;
- o jogador precisa esperar **1 Rodada completa** antes de agir na nova Frente.

Troca não custa Vigor.

---

# 22. Remoção automática

Quando a Frente termina:

- todos saem dela;
- retornam ao painel;
- podem escolher outra Frente ativa;
- não sofrem penalidade;
- não pagam Vigor adicional.

A remoção automática não conta como troca voluntária.

---

# 23. Sair do Evento

Sair voluntariamente da ocorrência encerra a participação ativa.

Isso:

- libera o lock quando aplicável;
- encerra o direito de reentrada;
- não apaga contribuição;
- não apaga elegibilidade já obtida;
- não duplica recompensa.

Isso segue a regra global já publicada para encerramento da participação e Configuração de Combate. fileciteturn167file0

---

# 24. Derrota e reentrada

Ao ser derrotado:

- deixa a Frente;
- mantém a participação na ocorrência;
- mantém contribuição;
- mantém a Configuração de Combate;
- espera 2 minutos para reentrar.

Após 2 minutos:

- pode entrar em qualquer Frente ATIVA;
- aguarda uma janela válida de decisão;
- não recebe penalidade de troca adicional.

Recovery segue as regras normais de PvE aplicáveis ao Evento.

---

# 25. AFK

Uma Rodada sem Ação:

- 1ª consecutiva: AFK 1/3;
- 2ª consecutiva: AFK 2/3;
- 3ª consecutiva: remoção da Frente.

Qualquer Ação validamente registrada reinicia o contador.

Remoção por AFK:

- não encerra participação na ocorrência;
- não apaga contribuição;
- permite reentrada enquanto o Evento estiver ativo.

---

# 26. IA

O World Event reutiliza o motor de combate.

A IA:

- decide no início da Rodada;
- respeita fase;
- respeita Recarga;
- respeita condições;
- prioriza antes da aleatoriedade;
- usa RNG determinístico nos empates;
- pode ter telegraph;
- mantém a decisão comprometida.

Ataques normais não precisam de telegraph.

Telegraph informa, não recomenda.

---

# 27. Entrada e saída durante ação inimiga

Se um alvo sair antes da aplicação:

- não recebe o efeito;
- demais alvos válidos continuam.

Se alguém entrar depois da decisão:

- não recebe uma ação inimiga retroativa;
- pode ser alvo a partir da próxima Rodada.

---

# 28. AoE e múltiplos alvos

AoE usa o motor existente.

Resultados primários são calculados pelo estado pré-evento.

Morte de um alvo não aumenta retroativamente o dano em outro.

---

# 29. Scaling

Esta é uma das principais decisões novas para adaptar o parâmetro canônico à arquitetura de Frentes.

## N da Frente

N = quantidade de participantes ativos naquela Frente no momento do snapshot da fase.

Não é:

- o total do servidor;
- o total de todas as Frentes.

## Snapshot

Se houver participantes no início da fase:

- snapshot imediato.

Se estiver vazia:

- snapshot é adiado até o primeiro participante entrar.

Depois do snapshot:

- entradas não alteram N;
- saídas não alteram N.

## Fórmulas

HP:

N^0,88

ATQ:

+1,5% × (N − 1)

Cap de ATQ:

+60%

Cap de N:

200

Participantes acima de 200 continuam aparecendo e contando para participação, mas não aumentam o scaling acima do cap.

---

# 30. HP compartilhado

Na Frente principal:

- uma única barra de HP;
- todos atacam o mesmo alvo;
- não existem cópias por jogador;
- derrota do alvo acontece uma única vez.

Isso substitui o modelo antigo de instância individual contra HP compartilhado.

---

# 31. Mudança de fase do chefe

Ao concluir a Frente principal:

- encerra o HP da criatura;
- overkill não passa para a próxima forma;
- nova criatura começa na nova fase;
- novo scaling é calculado pelo snapshot da nova fase.

As três criaturas de fase existentes continuam sendo as criaturas das três Frentes principais do Evento. fileciteturn167file0

---

# 32. Frentes sem jogadores

Frente vazia:

- não recebe NPC;
- não recebe jogador artificial;
- não recebe cura;
- não ganha bônus automático.

O conteúdo pode possuir consequência ambiental ou perda de estado enquanto a Frente estiver vazia.

---

# 33. Objetivos sem combate

Uma Frente pode não possuir criatura.

Nesse caso:

- continua usando Rodadas;
- ações ainda são registradas;
- Ação Contextual pode existir;
- Artes podem interagir quando o conteúdo permitir;
- objetivo é atualizado na resolução;
- telegraph pode informar perigo.

Não criar uma interface paralela de puzzle.

---

# 34. Ação Contextual

Ação Contextual:

- existe somente quando o conteúdo declara;
- aparece somente quando válida;
- entra na resolução simultânea;
- pode ter alvo;
- pode contar como Ação Significativa;
- pode ser major_contribution.

Ela não cria um subsistema novo.

---

# 35. Contribuição

Registrada por:

occurrence_id + character_id

Não é zerada por:

- derrota;
- reentrada;
- troca de Frente;
- reconnect;
- troca de dispositivo.

## Fase válida

Uma fase conta para o personagem quando ele realiza pelo menos uma Ação Significativa em qualquer Frente naquela fase.

## Ação Significativa

Conta quando existe impacto real:

- dano efetivo;
- Cura efetiva;
- Barreira efetivamente absorvida;
- mitigação efetiva;
- Debuff/efeito útil aplicado;
- Ação Contextual que altera o objetivo;
- interrupção/mecânica explicitamente marcada pelo conteúdo;
- Defender que efetivamente reduz dano.

Não conta integralmente:

- ataque com 0 dano;
- Cura com 0 efeito;
- Barreira sem absorção;
- spam sem impacto;
- navegação.

Cada Ação pode gerar no máximo 1 ponto de Ação Significativa.

---

# 36. Major Contribution

major_contribution é um evento de contribuição explicitamente marcado pelo conteúdo.

Valor:

**4 pontos**

Um mesmo milestone concede esse crédito no máximo uma vez por personagem.

Esses pontos servem para elegibilidade; não criam multiplicador secreto de recompensa.

---

# 37. Elegibilidade

Elegível quando:

- participou de pelo menos 2 fases;
- atingiu pelo menos 8 pontos de contribuição.

A participação é global da ocorrência.

Dar um hit e sair não basta.

---

# 38. Recompensa

Em Evento bem-sucedido:

10 Vigor → recompensa-base publicada

0,40 × C + 2 materiais básicos + 1 Fragmento

XP:

8% da referência de nível.

Não criar:

- moeda de Evento;
- reward por Frente;
- reward comunitário;
- tier de DPS;
- tier de suporte.

Evento fracassado:

- não concede a recompensa-base de conclusão;
- não duplica economia;
- conhecimento narrativo explicitamente definido pelo conteúdo pode persistir separadamente.

---

# 39. Consumíveis

World Events usam o limite canônico de Consumíveis por ocorrência.

Quando houver uso disponível:

[🥤 Consumíveis]

A seleção é uma Ação da Rodada.

O consumo é idempotente.

Não criar lógica específica de Consumível para cada Frente.

---

# 40. Configuração de Combate

Ao assumir participação:

- registra snapshot;
- trava Equipamentos;
- trava Artes;
- trava Caminho/Talentos/Doutrina conforme GDD;
- não permite troca oportunista.

Trocar de Frente não libera o lock.

Derrota não libera o lock.

Reentrada usa a mesma Configuração.

---

# 41. Sintonização do Véu

Quando marcada pelo conteúdo:

Lsync = min(Ljogador, Levento + 5)

Aplicar regras publicadas de Sintonização.

Sintonização:

- não troca Classe;
- não troca Artes;
- não libera reconfiguração;
- não quebra lock;
- não melhora economia.

---

# 42. Tela de Frentes

Estrutura final:

🔥 Nome do Evento

⏱️ Evento em andamento

⚔️ Fase atual · 2/3

⏳ Tempo restante · 18:42

Texto contextual.

Depois:

🔥 Frentes Ativas

Cada bloco mostra:

- nome;
- participantes;
- objetivo;
- estado mensurável;
- informação factual necessária para entender a progressão.

Exemplo:

🔥 Frente X
👥 18 participantes
🎯 Defender a estrutura
🛡️ Integridade 72 / 100

Contagens simples usam números normais, não monoespaçados.

Botões ficam separados dos blocos informativos.

Não mostrar:

- recomendação;
- melhor Frente;
- prioridade sugerida;
- composição ideal;
- DPS.

Quando uma Frente for obrigatória para avançar, pode aparecer:

📌 Necessária para avançar a fase

Isso é informação, não recomendação.

---

# 43. Tela principal da Frente

Estrutura:

🔥 Nome da Frente

⚔️ Rodada 12 · ⏱️ 00:08

Estado da criatura/objetivo.

HP/Integridade/Progresso.

Telegraph quando necessário.

🤝 Suporte:

Somente suporte diretamente dirigido a outros participantes na Rodada atual.

📜 Histórico:

Eventos relevantes da última resolução.

Ações:

[⚔️ Atacar]
[🛡️ Defender]
[Arte 1]
[Arte 2]
[Arte 3]
[🥤 Consumíveis] quando disponível
[Ação Contextual] quando existir
[👥 Participantes]
[↩️ Frentes]

Não existe:

- “Sua Ação” persistente;
- “Alterar Ação”;
- menu permanente separado de Artes.

---

# 44. Histórico

Não é um log infinito.

Mostrar:

- máximo 4 linhas;
- somente eventos relevantes da última resolução;
- consolidação de repetições;
- nomenclatura canônica.

Log completo pertence ao backend.

---

# 45. Suporte

Título exato:

🤝 Suporte:

Somente ações de suporte diretamente dirigidas a outro participante.

Se não houver suporte na Rodada:

**omitir a seção inteira**.

Não mostrar:

- ataques;
- debuffs;
- marcas;
- ofensivas.

---

# 46. Participantes

Tela separada:

- 5 por página;
- ícone/classe canônico;
- HP;
- barra de 10 blocos;
- sem efeitos/debuffs;
- paginação simples.

Não exibir papel, prioridade ou recomendação.

---

# 47. Feedback de clique

Callback:

✅ Ação registrada.

Não reescrever a tela inteira em cada clique.

Atualização principal acontece no limite da Rodada.

---

# 48. Reconnect e múltiplos dispositivos

O backend é autoridade.

Após reconnect:

- reconstruir Frente;
- reconstruir Rodada;
- preservar Ação;
- preservar timer;
- preservar AFK;
- preservar contribuição;
- preservar lock.

Nenhuma reconexão cria nova participação.

---

# 49. Callbacks stale

Callback deve validar:

- ocorrência;
- Frente;
- Rodada;
- Ação;
- identidade do personagem.

Se estiver fora da Rodada:

- não altera estado;
- não aplica dano;
- não consome recurso;
- devolve estado atual.

Mensagem:

⏱️ A Rodada já foi encerrada.

Depois, reconstruir a tela.

---

# 50. Idempotência

Ação de jogador possui identidade única.

Callback duplicado:

- não aplica duas vezes;
- não conta duas vezes;
- não consome duas vezes;
- não duplica reward.

RNG segue a regra determinística/idempotente já publicada. fileciteturn167file9

---

# 51. Estado persistido mínimo

## WorldEventOccurrence

- event_id;
- occurrence_id;
- scheduled_at;
- started_at;
- deadline_at;
- state;
- phase;
- round;
- phase_started_at;
- active_front_ids;
- front_slots;
- participant_ids;
- global_result;
- settlement_state.

## WorldEventParticipation

- occurrence_id;
- character_id;
- combat_configuration_snapshot;
- current_front_id;
- joined_at;
- last_action_round;
- afk_streak;
- defeat_at;
- reentry_at;
- voluntarily_left;
- eligible_phases;
- significant_actions;
- major_contributions;
- reward_settled.

## WorldEventFront

- front_id;
- occurrence_id;
- phase;
- slot;
- state;
- objective_type;
- objective_state;
- objective_max;
- success_condition;
- failure_condition;
- replacement_count;
- scaling_snapshot;
- content_key.

---

# 52. Ordem autoritativa de uma Rodada

1. abrir Rodada;
2. IA decide;
3. abrir timer de 20s;
4. receber ações;
5. fechar timer;
6. validar;
7. marcar Frente como RESOLVENDO;
8. calcular resultados pelo estado pré-Rodada;
9. prevenção/substituição;
10. dano/cura;
11. estado final;
12. derrotas;
13. triggers;
14. pós-evento;
15. limpeza de expirados;
16. atualizar objetivo;
17. calcular contribuição;
18. atualizar AFK;
19. resolver Frentes;
20. avaliar fase;
21. avaliar deadline/Evento;
22. atualizar UI;
23. próxima Rodada, se aplicável.

---

# 53. Ordem de prioridade de estados

Quando houver várias mudanças:

1. motor de combate;
2. objetivo da Frente;
3. estado da Frente;
4. estado da fase;
5. estado do Evento;
6. retirada de participantes;
7. settlement.

Nunca entregar reward no meio da Rodada.

---

# 54. Compatibilidade com o motor de combate

O conteúdo define:

- criatura;
- objetivo;
- valores;
- sucesso;
- fracasso;
- telegraph;
- ação contextual;
- texto;
- Códice;
- mecânicas especiais.

O motor comum define:

- dano;
- cura;
- Barreira;
- efeitos;
- acerto;
- crítico;
- Defesa;
- Defender;
- simultaneidade;
- RNG;
- persistência;
- lock;
- idempotência.

Não criar uma cópia do motor para World Events.

---

# 55. As seis Classes

O Evento deve oferecer oportunidade real de contribuição para as seis Classes.

Isso não cria trindade.

Uma contribuição pode vir de:

- dano;
- Cura;
- Barreira;
- mitigação;
- Debuff;
- execução;
- controle;
- Ação Contextual;
- mecânica de objetivo.

Não criar rótulos Tank/Healer/DPS/Support.

---

# 56. Recorrência

O catálogo atual de seis Eventos permanece.

Não introduzir variantes aleatórias no primeiro lançamento do redesign.

A seleção do Evento continua determinística.

Motivo:

- seis identidades já existem;
- cada uma possui três fases;
- as Frentes e objetivos já fornecem variação suficiente;
- evita expandir conteúdo antes da vertical slice.

Variantes poderão ser adicionadas depois como conteúdo.

---

# 57. Eventos existentes

Permanecem:

1. O Cerco das Cinzas — Terras do Ocaso.
2. Os Que Ainda Pendem — Vales dos Enforcados.
3. A Linha que Não Termina — Planícies de Nareth.
4. A Água que se Ergue — Várzeas Carmesins.
5. O Último Contrapeso — Altos Cinéreos.
6. O Silêncio entre as Camadas — Confins do Véu.

As três criaturas já publicadas para cada Evento passam a ser as criaturas das três Frentes principais correspondentes às suas fases.

O catálogo atual e seus níveis, nomes e textos permanecem as referências de conteúdo. fileciteturn167file0

---

# 58. O Cerco das Cinzas — primeira vertical slice

Para a primeira implementação:

- utilizar as três criaturas já publicadas;
- usar locais já existentes de Terras do Ocaso nas Frentes alternativas;
- priorizar locais já canônicos antes de criar nomes novos;
- começar com objetivos de Defesa, Progresso e Suportar;
- evitar introduzir uma mecânica regional nova só para demonstrar o sistema.

Nomes como “Portões de Cinza”, “Fornalha Abandonada” e “Estrada das Cinzas” usados em mocks anteriores devem permanecer marcados como proposta até serem incorporados ao Documento Regional.

As fontes regionais atuais confirmam Estrada das Cinzas e Refúgio do Ocaso como locais existentes, entre outros, mas não definem a nova taxonomia de Frentes aqui proposta. fileciteturn167file7

---

# 59. O que esta proposta rejeita

Não usar:

- combate separado por jogador contra o mesmo HP;
- limite artificial de jogadores por Frente;
- limite social de Grupo 4 em World Events;
- 20–30 personagens em uma mesma tela;
- trindade MMO;
- ranking de DPS;
- recompensa por DPS;
- NPC automático para Frente vazia;
- recomendação de melhor Frente;
- recomendação de Classe;
- menu permanente de Artes;
- tela permanente de “Sua Ação”;
- botão “Alterar Ação”;
- barra pública de contribuição;
- moeda nova de Evento;
- variante aleatória obrigatória;
- IA paralela específica;
- segundo motor de objetivo;
- pontuação oculta que decide o resultado sem estado visível.

---

# 60. Conteúdo versus sistema

Depois desta proposta, os dados que ainda precisam ser preenchidos pelo Conteúdo são:

- nomes das Frentes;
- textos;
- modelo de objetivo;
- valores;
- condição de sucesso;
- condição de fracasso;
- Ação Contextual, quando houver;
- telegraphs;
- relação com Códice;
- textos de transição.

Isso não é uma lacuna de arquitetura.

É autoria de conteúdo.

---

# 61. Implementação

## Etapa A — Estado

Criar:

- ocorrência;
- participação;
- Frente;
- Rodada;
- snapshot de scaling;
- contribuição.

## Etapa B — Motor de Rodada

Implementar:

- timer 20s;
- fechamento;
- lock da Rodada;
- resolução simultânea;
- idempotência;
- callbacks stale.

## Etapa C — Frentes

Implementar:

- 3 slots;
- entrada;
- saída;
- troca;
- resolução;
- colapso;
- substituição;
- transição de fase.

## Etapa D — Combate

Conectar:

- Ataque;
- Defender;
- Artes;
- Consumíveis;
- IA;
- telegraph;
- HP compartilhado.

## Etapa E — UI

Implementar:

- calendário;
- visão geral;
- painel de Frentes;
- Frente ativa;
- Participantes;
- callbacks;
- AFK.

## Etapa F — Settlement

Implementar:

- contribuição;
- elegibilidade;
- reward;
- XP;
- Códice;
- idempotência.

---

# 62. Testes obrigatórios

## Rodada

- dois ataques no mesmo alvo;
- ataque + cura;
- ataque + Barreira;
- morte simultânea;
- AoE;
- alvo removido;
- callback stale;
- callback duplicado.

## Frentes

- troca;
- entrada tardia;
- saída;
- resolução;
- colapso;
- substituição;
- Frente vazia;
- nenhuma entrada.

## Fase

- principal + alternativa resolvidas;
- principal resolvida + ambas alternativas colapsadas;
- principal colapsada;
- transição no limite da Rodada;
- overkill;
- scaling novo.

## Participação

- AFK 1/3;
- AFK 2/3;
- AFK 3/3;
- derrota;
- reentrada 2m;
- saída voluntária;
- reconnect;
- troca de dispositivo.

## Economia

- 1 reserva de Vigor;
- 1 reward;
- nenhuma duplicação;
- falha sem reward;
- XP idempotente;
- contribuição preservada.

---

# 63. Critérios de aceite do sistema

A implementação somente é compatível quando:

1. nenhum jogador possui combate privado contra o mesmo HP;
2. todos os participantes da mesma Frente enxergam o mesmo estado;
3. todas as Frentes usam a mesma Rodada;
4. nenhum clique define ordem;
5. Ações válidas não são canceladas por ordem de resolução;
6. jogador atrasado não trava a ocorrência;
7. scaling congelado não é recalculado por entrada/saída;
8. Frente vazia não recebe NPC;
9. reward não depende de DPS;
10. reconnect reconstrói a ocorrência;
11. callbacks duplicados são idempotentes;
12. ocorrência termina no máximo no deadline;
13. Configuração de Combate permanece protegida;
14. parâmetros publicados do GDD permanecem intactos;
15. Conteúdo consegue preencher uma Frente sem criar um segundo motor.

---

# 64. Decisão final desta proposta

**Um Evento Mundial é uma ocorrência global de 3 fases. Cada fase possui 3 Frentes simultâneas: uma principal obrigatória e duas alternativas. Todas compartilham o mesmo relógio de Rodadas. Cada personagem escolhe uma única Frente por vez e executa uma Ação por Rodada. Todas as Ações válidas são resolvidas simultaneamente pelo motor oficial. A fase avança quando a Frente principal e pelo menos uma alternativa são resolvidas. A fase falha quando a Frente principal colapsa ou as duas alternativas colapsam. O Evento termina com sucesso após as 3 fases ou fracassa no primeiro fracasso de fase/deadline.**

Esta proposta fecha as lacunas de **arquitetura e regra de sistema** levantadas no documento v1.0.0.

O que fica para depois é somente preenchimento de Conteúdo, Balanceamento e implementação.

---

# 65. Relação com v1.0.0

Esta versão v2.0.0 substitui as decisões abertas da seção 15 do documento v1.0.0 quando houver conflito.

As decisões já aprovadas do documento v1.0.0 permanecem válidas quando não houver conflito.

Após aceite explícito desta proposta, ela pode se tornar a nova baseline oficial do redesenho.

**Próximo passo após aceite:** transformar a proposta em baseline de implementação e testes, começando pela máquina de estado de WorldEventOccurrence + WorldEventFront + Round.

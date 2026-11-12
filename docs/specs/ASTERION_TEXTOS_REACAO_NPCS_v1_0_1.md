# ASTERION — Textos de Reação dos NPCs
## Pacote player-facing para Ação × Consequência · v1.0.1

**Objetivo:** fornecer as falas que materializam as memórias registradas pelo sistema narrativo.

**Uso:** cada opção abaixo é uma variante da reação futura correspondente ao `choice_id`. O runtime deve exibir somente a variante compatível com a memória pessoal legitimamente disponível.

**Regra:** estas falas não criam Lore nova, não revelam informação protegida, não transformam memória pessoal em conhecimento global e não substituem os `future_hooks` da especificação narrativa.

**Tom:** dark fantasy medieval, humano, contido. NPCs reconhecem comportamento, método ou decisão anterior; eles não leem a ficha interna do jogador.

**Fonte estrutural:** `ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md`.

**Revisão v1.0.1:** pendências de copy de 2026-11-12 resolvidas. O contrato prevalece; escolhas que somente registram memória do personagem permanecem deliberadamente sem reação de NPC.
**Fonte canônica de personagens/lore:** `ASTERION_BIBLIA_CANONICA_v4_0_7.md` e conteúdos regionais correspondentes.

---

# 1. Terras do Ocaso

## P1 — Vozes na Estrada → reação em P2
**choice_id:** `P1_choice_posture`
**future_hook:** Alda modula a primeira cobrança conforme a postura adotada em P1.

### Opção 1 — Prudência
**Alda Veyr:** “Você não enfeitou o relato. Isso facilita o trabalho. Quando eu pedir uma hipótese, você vai saber que estou pedindo uma hipótese — não um fato.”

### Opção 2 — Abertura
**Alda Veyr:** “Você admitiu que a estrada assustou você e ainda assim voltou. Não preciso que finja coragem aqui. Preciso que me diga quando algo passar do limite.”

### Opção 3 — Curiosidade
**Alda Veyr:** “Você perguntou pelos sinais antes de aceitar abrigo. Então não vou desperdiçar seu tempo com ordens vagas. Veja o que puder e me traga algo que eu consiga usar.”

---

## S1 — Luzes sob as Cinzas → reação em S5
**choice_id:** `S1_response_to_light`
**future_hook:** Oren retoma se o personagem perseguiu o fenômeno ou preservou distância.

### Opção 1 — Investigar imediatamente
**Oren Cal:** “Você foi atrás da luz mesmo sem saber o que esperava encontrar. Não digo que estava certo. Digo que, pelo menos, trouxe uma observação que os outros não teriam.”

### Opção 2 — Registrar e voltar
**Oren Cal:** “Você deixou a luz onde estava e trouxe o registro. Às vezes, preservar a pergunta é mais útil do que correr atrás dela.”

### Opção 3 — Buscar testemunha
**Oren Cal:** “Você preferiu saber quem mais viu antes de seguir. Isso reduz a chance de transformar uma impressão particular em uma certeza pública.”

---

## P2 — Fuligem sem Fogo → reação em S2/P3/P4
**choice_id:** `P2_evidentiary_posture`
**future_hook:** Oren muda o tipo de pergunta; Alda percebe o grau de prudência.

### Opção 1 — Só aparência e localização
**Oren Cal:** “Você não deu nome ao que não conhecia. Ótimo. Vamos continuar trabalhando com aquilo que a pedra realmente mostra.”

### Opção 2 — Hipótese marcada
**Oren Cal:** “Você chamou de escrita, mas deixou claro que era uma hipótese. Essa diferença parece pequena até alguém começar a copiar a hipótese como se fosse fato.”

### Opção 3 — Exigir contexto
**Oren Cal:** “Você segurou a conclusão. É uma irritação útil. Agora eu sei que, quando faltar uma peça, você vai dizer que falta uma peça.”

---

## S2 — Os Nomes Esquecidos → reação em S6
**choice_id:** `S2_priority`
**future_hook:** Oren retoma a prioridade escolhida ao lidar com o último registro.

### Opção 1 — Preservar nomes e vestígios
**Oren Cal:** “Você voltou aos nomes antes de fechar a história. Vamos fazer o mesmo aqui. Um registro incompleto ainda é um registro.”

### Opção 2 — Perseguir o risco atual
**Oren Cal:** “Você escolheu os vivos primeiro. Eu não esqueci. Quando encontrarmos outra ameaça, não vou presumir que você queira sacrificar quem está aqui por um nome que já se perdeu.”

### Opção 3 — Unir pessoas e prova
**Oren Cal:** “Você tentou manter as duas coisas na mesma mão. É mais difícil, mas evita que a prova sobreviva enquanto as pessoas ficam para trás.”

---

## P3 — Sob Galhos Calcinados → reação em P4/S4
**choice_id:** `P3_heritage_method`
**future_hook:** Oren reconhece o método ao interpretar a função dos Vigias.

### Opção 1 — Preservar sem tocar
**Oren Cal:** “Você sabe quando uma descoberta precisa de espaço. O fragmento ainda está inteiro porque você resistiu à tentação de arrancar mais dele.”

### Opção 2 — Inspeção ativa
**Oren Cal:** “Você examina antes de nomear. Isso me serve. Só não confunda examinar mais com entender mais.”

### Opção 3 — Testar autoria
**Oren Cal:** “Você questionou a própria origem da peça. É uma boa defesa contra o hábito de ver 'antigo' e preencher o resto com imaginação.”

---

## S3 — Rastros sob os Galhos → reação em P4/P5
**choice_id:** `S3_priority`
**future_hook:** Alda enquadra a tarefa seguinte conforme sua prioridade.

### Opção 1 — Causa da perda
**Alda Veyr:** “Você sempre quer saber por que a rota falhou. Então vou lhe dar o problema antes da solução. Quero a causa, não apenas um caminho remendado.”

### Opção 2 — Segurança da próxima carga
**Alda Veyr:** “Você colocou a próxima viagem acima da explicação. Entendido. Primeiro deixamos a rota utilizável. Depois perguntamos por que ela quase matou alguém.”

### Opção 3 — Pessoas afetadas
**Alda Veyr:** “Você perguntou primeiro por quem passaria pela rota. Isso muda o cálculo. Uma estrada não é segura só porque parece segura no mapa.”

---

## P4 — Pedras que Ainda Vigiam → reação em P5
**choice_id:** `P4_guard_protocol`
**future_hook:** A preparação para a Porta do Poente muda a conversa.

### Opção 1 — Desviar
**Alda Veyr:** “Você não mexeu na defesa. Foi prudente. Na Porta do Poente, quero o mesmo princípio até termos motivo para arriscar.”

### Opção 2 — Testar limite
**Oren Cal:** “Você preferiu descobrir o limite da defesa sem quebrá-la. Isso me diz como lhe apresentar a Porta: primeiro o comportamento, depois a interpretação.”

### Opção 3 — Procurar finalidade
**Alda Veyr:** “Você quis saber para quem aquela defesa ainda operava. Na próxima porta, essa pergunta vem antes de qualquer ordem para atravessar.”

---

## S4 — Vigília sem Voz → reação em P5/P6
**choice_id:** `S4_patrol_reading`
**future_hook:** Oren retoma a postura diante das estruturas.

### Opção 1 — Anomalia documentada
**Oren Cal:** “Você registrou a mudança sem inventar motivo. É assim que uma anomalia continua sendo útil depois que a surpresa passa.”

### Opção 2 — Verificar padrão
**Oren Cal:** “Você repetiu a rota para testar a mudança. Bom. Um único desvio é uma história; dois começos de padrão são outra coisa.”

### Opção 3 — Buscar função
**Oren Cal:** “Você procurou uma função prática antes de procurar um significado maior. Vou apresentar o que sabemos da mesma forma.”

---

## S5 — A Luz que Não Aquece → reação em P6
**choice_id:** `S5_risk_posture`
**future_hook:** Oren enquadra a atitude diante da Âncora segundo seu histórico.

### Opção 1 — Risco calculado
**Oren Cal:** “Você se aproxima quando consegue medir o preço. Então, quando eu disser que algo é incerto, não vou esperar nem imprudência nem recuo automático — vou esperar cálculo.”

### Opção 2 — Evitar risco
**Oren Cal:** “Você soube encerrar a busca. Diante da Âncora, isso importa. Há coisas que podem ser observadas sem serem tocadas.”

### Opção 3 — Buscar corroboração
**Oren Cal:** “Você procura uma segunda testemunha antes de apostar na primeira leitura. É o melhor antídoto que temos contra o fascínio do inexplicável.”

---

## P5 — A Porta do Poente → reação em P6
**choice_id:** `P5_threshold`
**future_hook:** O preâmbulo do Chefe muda conforme o preparo narrativo.

### Opção 1 — Entrar assim que possível
**Alda Veyr:** “Você não esperou que a porta ficasse confortável. Então vamos entrar sabendo que sua escolha foi descoberta primeiro e segurança depois.”

### Opção 2 — Reunir evidência
**Oren Cal:** “Você segurou a travessia por mais uma prova. Não sabemos se isso será suficiente. Mas agora a entrada não acontece sem que o que encontramos esteja registrado.”

### Opção 3 — Preparar retorno
**Alda Veyr:** “Você preparou a volta antes de apostar na ida. Isso não torna a Câmara segura. Só significa que você pensou no que acontece se ela não for.”

---

## P6 — O Vigia Partido → reação futura em P7
**choice_id:** `P6_anchor_posture`
**future_hook:** A postura de investigação/contensão acompanha o personagem para os Vales.

### Opção 1 — Registrar sem extrapolar
**Oren Cal:** “Você saiu com o nome e deixou o resto em aberto. Leve isso com você. Nos Vales, uma lacuna continua sendo melhor do que uma resposta inventada.”

### Opção 2 — Buscar outra Âncora
**Alda Veyr:** “Você quer comparar antes de fechar a história. Faz sentido. Só não deixe a busca por uma segunda pedra fazer você esquecer a primeira.”

### Opção 3 — Questionar os guardiões
**Alda Veyr:** “Você quer saber quem ainda protege essas estruturas. É uma pergunta legítima. A resposta não está aqui, então não aceite a primeira pessoa que se oferecer como dona da verdade.”

---

## S6 — Onde os Nomes Terminaram → reação em P7
**choice_id:** `S6_missing_people`
**future_hook:** O personagem leva para os Vales uma postura sobre desaparecidos e registros incompletos.

### Opção 1 — Preservar o registro
**Oren Cal:** “Você deixou o vazio escrito em vez de apagá-lo. Isso importa. O nome não terminou só porque a resposta terminou.”

### Opção 2 — Buscar outra pista
**Oren Cal:** “Você ainda quer completar o nome. Está certo — desde que a busca continue sendo busca. Não vamos preencher o silêncio com certeza.”

### Opção 3 — Aceitar o limite da evidência
**Oren Cal:** “Você soube parar antes de inventar quem faltava. É uma disciplina rara. Leve-a para os Vales.”

---

# 2. Vales dos Enforcados

## P7 — A Estrada Estrangulada → reação em P8
**choice_id:** `P7_route_priority`
**future_hook:** Dara retoma a prioridade ao escolher a próxima rota.

### Opção 1 — Segurança
**Dara Venn:** “Você fechou a questão da rota primeiro. Então vamos partir dessa regra: qualquer pista que nos mate antes de esclarecer o resto não ajuda ninguém.”

### Opção 2 — Investigar ruína
**Dara Venn:** “Você parou a passagem para olhar a pedra. Na próxima rota, vou considerar que você aceita perder tempo se houver algo antigo que valha ser compreendido.”

### Opção 3 — Marcar e voltar
**Dara Venn:** “Você deixou a estrutura onde está e guardou a pista para depois. Gosto disso. Nem toda descoberta precisa ser resolvida no mesmo minuto.”

---

## S7 — Cordas na Névoa → reação em S10
**choice_id:** `S7_cordage_reading`
**future_hook:** Dara/Iven lembram sua postura diante de vestígios de passagem.

### Opção 1 — Ferramenta útil
**Dara Venn:** “Você viu a corda e pensou primeiro em quem pode precisar dela. É assim que eu separo um traste de um recurso.”

### Opção 2 — Origem da rota
**Iven Raal:** “Você tratou a corda como pista de quem passava por aqui. Então, quando eu lhe mostrar outra marca de travessia, vou começar pela origem, não pela aparência.”

### Opção 3 — Preservação
**Iven Raal:** “Você não tocou antes de entender. Às vezes é a única maneira de garantir que a próxima pessoa ainda tenha algo para estudar.”

---

## P8 — Entre Galhos Suspensos → reação em P9/P10
**choice_id:** `P8_root_hypothesis`
**future_hook:** Dara/Iven apresentam evidências conforme a postura adotada.

### Opção 1 — Hipótese simples
**Dara Venn:** “Você aceita uma explicação simples até ela falhar. Então vou trazer primeiro o que funciona no terreno, não a teoria mais bonita.”

### Opção 2 — Intencionalidade
**Iven Raal:** “Você procura padrão onde outros veem acaso. Tudo bem — mas vou continuar separando o padrão observado da intenção que você imagina por trás dele.”

### Opção 3 — Duas hipóteses
**Dara Venn:** “Você quer manter duas leituras abertas. Melhor assim. Escolher cedo demais faz a estrada parecer obedecer ao mapa.”

---

## S8 — O Peso da Passagem → reação em S11
**choice_id:** `S8_route_policy`
**future_hook:** Dara lembra o custo considerado aceitável.

### Opção 1 — Menor risco
**Dara Venn:** “Você prefere a rota que arrisca menos agora. Vou considerar isso antes de mandar alguém testar uma passagem só para ganhar tempo.”

### Opção 2 — Sustentabilidade
**Dara Venn:** “Você aceita um custo maior hoje para não repetir o problema amanhã. É uma escolha difícil quando todo mundo quer chegar logo.”

### Opção 3 — Custo comunitário
**Dara Venn:** “Você olha para quem mantém a passagem, não só para quem a usa. Isso muda o que chamamos de uma rota 'barata'.”

---

## P9 — Sob a Madeira Morta → reação em P10/P11
**choice_id:** `P9_priority`
**future_hook:** Iven passa a confiar mais a investigação conforme a prioridade.

### Opção 1 — Vivos primeiro
**Iven Raal:** “Você tirou as pessoas do caminho antes de salvar o papel. Eu não vou pedir que faça o contrário só porque eu gosto de documentos.”

### Opção 2 — Registro primeiro
**Iven Raal:** “Você protegeu a evidência mesmo quando seria mais rápido abandonar tudo. Agora sei que posso lhe entregar uma peça frágil sem esperar que ela seja sacrificada ao próximo perigo.”

### Opção 3 — Proteger ambos
**Iven Raal:** “Você tentou salvar o registro e quem ainda estava aqui. Não é sempre possível. Mas sei que essa é a tentativa que você fará primeiro.”

---

## S9 — Sob a Casca → reação em P10
**choice_id:** `S9_focus`
**future_hook:** Iven escolhe confiar primeiro suas hipóteses ao personagem.

### Opção 1 — Seguir fenômeno
**Iven Raal:** “Você seguiu a pista mesmo quando ela desviava do problema imediato. Quando eu tiver uma hipótese difícil de encaixar, vou mostrar primeiro a você.”

### Opção 2 — Foco na ameaça
**Iven Raal:** “Você não deixou a curiosidade tomar o lugar da ameaça. Eu respeito isso. Uma hipótese não vale a vida que ela coloca em risco.”

### Opção 3 — Registrar e voltar
**Iven Raal:** “Você anotou a pista e voltou ao objetivo. É o tipo de disciplina que impede uma investigação de virar desculpa para abandonar o que foi prometido.”

---

## P10 — Pedra sob as Raízes → reação em P11
**choice_id:** `P10_structure_policy`
**future_hook:** A equipe diverge de você sem quebrar a confiança.

### Opção 1 — Preservar
**Iven Raal:** “Você protege a estrutura mesmo quando ela ainda pode ser útil. Eu discordo de parte do custo, mas sei que sua cautela não é descaso.”

### Opção 2 — Testar limite
**Iven Raal:** “Você aceita tocar no mecanismo para descobrir onde ele falha. Posso não escolher o mesmo caminho, mas agora sei que sua curiosidade tem um método.”

### Opção 3 — Priorizar passagem
**Iven Raal:** “Você aceita perder a estrutura se isso mantiver a rota aberta. Não é minha escolha favorita, mas sei por que você a fez.”

## S10 — Água sem Reflexo → reação em S12
**choice_id:** `S10_codex_method`
**future_hook:** A escolha define como os registros dos Vales são compostos.

### Opção 1 — Fato observado
**Dara Venn:** “Então o Códice vai começar pelo que os olhos conseguem sustentar. O resto fica separado até alguém trazer prova.”

### Opção 2 — Hipótese marcada
**Iven Raal:** “Hipótese marcada, certo. Assim podemos pensar sem esquecer onde a observação termina.”

### Opção 3 — Testemunhas
**Dara Venn:** “Você quer ouvir mais gente antes de fechar o registro. Faz sentido. Estradas diferentes produzem histórias diferentes — e às vezes uma delas entrega o detalhe que falta.”

## S11 — A Guarda que Não Dorme → reação em P12
**choice_id:** `S11_guard_belief`
**future_hook:** A postura diante de sistemas antigos reaparece no clímax.

### Opção 1 — Confiar até contradizer
**Iven Raal:** “Você concede crédito ao padrão até que ele prove que falhou. Vou manter essa mesma ordem no que ainda nos falta observar.”

### Opção 2 — Contexto importa
**Iven Raal:** “Você não confia em uma função antiga sem saber para quem ela servia. É uma boa trava contra tratar ruína como autoridade.”

### Opção 3 — Teste controlado
**Iven Raal:** “Você quer um teste antes de aceitar a regra. Quando chegarmos ao Berço, essa será a pergunta certa.”

---

## P11 — Onde Tudo se Enreda → reação em P12
**choice_id:** `P11_conflicting_evidence`
**future_hook:** A equipe apresenta o Berço conforme sua postura.

### Opção 1 — Leitura conservadora
**Dara Venn:** “Você prefere errar pelo lado da contenção. Então é assim que vou colocar o risco quando chegarmos ao centro.”

### Opção 2 — Modelo explicativo
**Iven Raal:** “Você quer a leitura que encaixa melhor os fatos. Eu vou lhe mostrar primeiro o modelo e depois onde ele ainda quebra.”

### Opção 3 — Duas hipóteses e menor risco
**Dara Venn:** “Você aceita duas versões enquanto escolhe a ação menos perigosa. Isso é uma boa forma de não transformar dúvida em aposta.”

---

## P12 — A Matriarca das Raízes → reação em P13
**choice_id:** `P12_climax_interpretation`
**future_hook:** A postura investigativa acompanha o personagem para Nareth.

### Opção 1 — Só observável
**Iven Raal:** “Você não saiu do Berço com uma resposta maior que a prova. Em Nareth, vou confiar nessa mesma disciplina.”

### Opção 2 — Ameaça maior que explicação
**Dara Venn:** “Você viu o tamanho do perigo antes de fingir que o entendia. Isso é prudência, não pessimismo.”

### Opção 3 — Informação suficiente para seguir
**Iven Raal:** “Você acha que já temos base para continuar. Talvez. A diferença é que você quer investigar, não declarar encerrada a pergunta.”

---

## S12 — Os Nomes Presos à Madeira → reação em Nareth
**choice_id:** `S12_names_policy`
**future_hook:** O método diante de nomes retorna quando registros forem discutidos em Nareth.

### Opção 1 — Significado primeiro
**Iven Raal:** “Quando um nome aparecer de novo, vou lembrar que você quer descobrir o que ele quer dizer antes de simplesmente arquivá-lo.”

### Opção 2 — Preservar nomes
**Iven Raal:** “Você não deixou os nomes desaparecerem só porque ainda não os entende. Isso tem valor aqui também.”

### Opção 3 — Nomes + contexto
**Iven Raal:** “Você prefere nome, rota e pessoa na mesma comparação. Ótimo. Registro isolado costuma esconder tanto quanto revela.”

# 3. Planícies de Nareth

## P13 — Linhas no Horizonte → reação em P14
**choice_id:** `P13_reference_method`
**future_hook:** Nera ajusta seus mapas conforme a referência escolhida.

### Opção 1 — Referência local atual
**Nera Voss:** “Você segue o que os moradores usam agora. Então vou começar pelos caminhos que existem de verdade, antes de abrir os mapas antigos.”

### Opção 2 — Marcos antigos
**Nera Voss:** “Você ainda dá peso aos marcos antigos. Vou manter essas referências visíveis — mas sempre contra o terreno.”

### Opção 3 — Comparar as duas
**Nera Voss:** “Você quer duas fontes antes de escolher. Certo. Vou lhe mostrar onde elas concordam e onde começam a mentir de modos diferentes.”

---

## S13 — Pedras que Apontam → reação em P14/S14
**choice_id:** `S13_trust_marker`
**future_hook:** A próxima orientação reflete a preferência de confiança.

### Opção 1 — Marco atual
**Nera Voss:** “Você confia no marco que ainda serve às pessoas. Isso diz muito sobre o tipo de mapa que você considera útil.”

### Opção 2 — Marco antigo
**Nera Voss:** “Você dá valor ao que sobreviveu ao tempo. Então vou manter a antiguidade como dado, sem confundi-la com autoridade.”

### Opção 3 — Nenhum sem teste
**Nera Voss:** “Você não aceita nenhum dos três sem passar pela estrada. Faz sentido. O chão não mente do mesmo modo que um desenho pode mentir.”

---

## P14 — O Canal sem Norte → reação em P15
**choice_id:** `P14_map_vs_world`
**future_hook:** Talen recebe sua abordagem como ponto de partida.

### Opção 1 — Estrutura real
**Nera Voss:** “Você seguiu a obra diante de você. Quando eu lhe mostrar um mapa velho, vou tratá-lo como referência — não como ordem.”

### Opção 2 — Mapa + divergência
**Nera Voss:** “Você quer saber onde o mundo deixou o mapa para trás. Isso transforma a divergência em dado, não em erro de navegação.”

### Opção 3 — Registrar primeiro
**Nera Voss:** “Você anotou a diferença antes de escolher. É exatamente o que precisamos quando versões diferentes precisam ser comparadas depois.”

## S14 — O Peso da Distância → reação em P16
**choice_id:** `S14_route_cost`
**future_hook:** Nera confia ao personagem uma tarefa mais sensível.

### Opção 1 — Tempo primeiro
**Nera Voss:** “Você paga risco para ganhar tempo quando a situação aperta. Eu lhe entrego tarefas rápidas quando cada minuto realmente importar.”

### Opção 2 — Confiabilidade primeiro
**Nera Voss:** “Você aceita gastar mais para errar menos. É a postura que eu procuro quando uma rota não pode falhar duas vezes.”

### Opção 3 — Redundância
**Nera Voss:** “Você prefere uma segunda rota a uma única estrada perfeita. Isso é útil quando o primeiro caminho deixa de existir.”

---

## P15 — A Distância Errada → reação em P16/P17
**choice_id:** `P15_anomaly_method`
**future_hook:** Talen escolhe que tipo de dado compartilhar primeiro.

### Opção 1 — Testar a explicação mais simples primeiro
**Talen Orm:** “Você quis testar a explicação mais simples antes de abrir outras frentes. Na próxima discrepância, vou lhe dar primeiro o dado que permite fazer exatamente esse teste.”

### Opção 2 — Marcar a discrepância como não resolvida
**Talen Orm:** “Você preferiu deixar o que não sabemos explicitamente aberto. Então não vou preencher o vazio com uma resposta só porque ela parece conveniente.”

### Opção 3 — Procurar uma terceira medição
**Talen Orm:** “Você não aceitou escolher entre duas medidas que não fechavam. Quando houver outro ponto disponível, vou lhe mostrar essa terceira verificação antes da conclusão.”

## S15 — Sob o Mesmo Céu → reação em S16
**choice_id:** `S15_result_vs_cause`
**future_hook:** Talen usa esse padrão para apresentar o mapa.

### Opção 1 — Chegar ao destino primeiro
**Talen Orm:** “Você quis chegar antes de explicar. Quando eu lhe mostrar o mapa, vou começar pelo que permite alcançar o destino sem transformar o caminho em uma teoria.”

### Opção 2 — Entender o ponto de partida antes de seguir
**Talen Orm:** “Você quer entender o ponto de partida antes de aceitar a rota. Vou mostrar primeiro o que explica de onde a divergência começa.”

### Opção 3 — Fazer a rota e registrar os dois fatos
**Talen Orm:** “Você preferiu fazer o caminho e guardar resultado e causa juntos. Então o próximo mapa virá com os dois registros lado a lado.”

## P16 — O Eixo sob a Terra → reação em P17
**choice_id:** `P16_axis_priority`
**future_hook:** O registro técnico disponível pode ser apresentado de modo diferente.

### Opção 1 — Garantir que o mecanismo não cause dano
**Talen Orm:** “Você quis garantir que o mecanismo não causasse dano antes de entender o resto. No próximo registro, vou separar primeiro o que mantém a operação segura.”

### Opção 2 — Entender como ele mede referências
**Talen Orm:** “Você quis saber como ele mede referências antes de decidir o que significa. Então começo pela função que podemos observar, não pela interpretação.”

### Opção 3 — Registrar tudo antes de tocar
**Nera Voss:** “Você registrou antes de tocar. Então vou lhe entregar a cadeia do que foi observado antes de pedir qualquer intervenção.”

## S16 — Cartografia do Erro → reação em P17
**choice_id:** `S16_mapping_policy`
**future_hook:** Nera confia em você para comparar fontes.

### Opção 1 — Somente caminhos verificados
**Nera Voss:** “Você quer que o mapa carregue apenas caminhos verificados. Certo. O restante ficará fora da rota principal até termos confirmação.”

### Opção 2 — Incluir rotas antigas com aviso de risco
**Nera Voss:** “Você aceita preservar rotas antigas, desde que o risco viaje junto com o desenho. Assim ninguém confunde memória de caminho com segurança atual.”

### Opção 3 — Marcar as divergências como camada separada
**Nera Voss:** “Você prefere mostrar a contradição em vez de escondê-la. Então as divergências ficam visíveis, mas separadas do caminho confirmado.”

## S17 — O Prumo Afundado → reação em P17
**choice_id:** `S17_calibration_policy`
**future_hook:** A abordagem influencia como a equipe trata o mecanismo central.

### Opção 1 — Devolver sem experimentar
**Talen Orm:** “Você devolveu a peça sem experimentar. Vou tratar o que não testamos como desconhecido, não como defeito comprovado.”

### Opção 2 — Testar o funcionamento de modo controlado
**Talen Orm:** “Você aceitou um teste controlado. Então cada mudança fica registrada antes de qualquer nova tentativa.”

### Opção 3 — Registrar o estado e deixar para análise posterior
**Talen Orm:** “Você preferiu registrar o estado e adiar a intervenção. Quando retomarmos isso, teremos um ponto de partida claro.”

## P17 — Medir o que Permanece → reação em P18
**choice_id:** `P17_veil_evidence`
**future_hook:** O preâmbulo do Arconte reconhece sua postura.

### Opção 1 — Aceitar como evidência suficiente
**Talen Orm:** “Você considerou o registro suficiente para trabalhar a partir dele. Vou lhe apresentar o próximo material como continuidade dessa evidência, sem tratá-la como prova de tudo.”

### Opção 2 — Tratar como registro incompleto
**Nera Voss:** “Você tratou o registro como incompleto. Então o que faltar continuará marcado como falta, mesmo quando uma resposta fácil estiver à mão.”

### Opção 3 — Buscar outra fonte antes de usar a conclusão
**Talen Orm:** “Você quis outra fonte antes de usar a conclusão. Quando chegarmos ao Arconte, vou separar claramente o que este registro sustenta do que ainda precisa de corroboração.”

## P18 — O Arconte Invertido → reação em P19
**choice_id:** `P18_anchors_posture`
**future_hook:** A postura regional viaja como memória pessoal; não como segredo global.

### Opção 1 — Registrar e preservar o conhecimento
**Talen Orm:** “Você escolheu registrar e preservar o que aprendeu. Então, quando essa informação voltar a ser útil, vou tratar seu registro com o cuidado que você exige.”

### Opção 2 — Buscar confirmação em outras regiões
**Nera Voss:** “Você quer confirmação em outras regiões antes de fechar a leitura. Quando outra fonte aparecer, vou lembrar que a comparação ainda faz parte do trabalho.”

### Opção 3 — Questionar quem decidiu usar as Âncoras e com quais custos
**Talen Orm:** “Você não quis parar no funcionamento; quis saber quem decidiu e quem pagaria o custo. Quando houver registro para seguir essa pergunta, vou colocá-lo na frente.”

## S18 — Os Caminhos que Não Coincidem → reação em P19
**choice_id:** `S18_route_closure`
**future_hook:** P19: memória pessoal de relação entre segurança e evidência.

### Opção 1 — Encerrar a rota e priorizar os viajantes
**Nera Voss:** “Você encerrou a rota quando ela deixou de servir aos viajantes. Em terreno instável, vou lembrar que segurança não é um detalhe do mapa.”

### Opção 2 — Manter a rota documentada, mesmo sem uso
**Nera Voss:** “Você manteve a rota registrada mesmo sem usá-la. Quando uma fonte antiga voltar a ser útil, vou saber que você prefere preservar o passado antes de apagá-lo.”

### Opção 3 — Testar se ainda existe alguma utilidade antes de fechar
**Nera Voss:** “Você quis testar uma última utilidade antes de fechar. Então, quando avaliarmos uma rota obsoleta de novo, vou considerar esse teste parte do encerramento.”

# 4. Várzeas Carmesins

## P19 — Águas de Ferro → reação em P20
**choice_id:** `P19_priority`
**future_hook:** Sera enquadra o pulso conforme a prioridade adotada.

### Opção 1 — Rotas e segurança
**Sera Morn:** “Você colocou passagem segura antes do mistério. Então, quando o pulso aparecer, eu vou lhe dizer primeiro o que ele ameaça.”

### Opção 2 — Entender a infraestrutura antiga
**Sera Morn:** “Você quer entender a infraestrutura antes de mexer nela. Certo. Só não esqueça que a água continua passando enquanto estudamos.”

### Opção 3 — Ouvir primeiro quem vive ali
**Sera Morn:** “Você perguntou primeiro por quem vive aqui. É assim que vou enquadrar o resto: o que isso faz com as pessoas vem antes do que isso significa.”

## S19 — Sal nas Feridas → reação em S20
**choice_id:** `S19_response`
**future_hook:** Sera lembra o método de decisão.

### Opção 1 — Reparar agora
**Sera Morn:** “Você prefere fechar o vazamento antes de descobrir toda a história. Eu consigo trabalhar com isso.”

### Opção 2 — Causa primeiro
**Sera Morn:** “Você quer saber por que o problema continua. Quando eu lhe mostrar o próximo ponto, vou incluir o que temos da origem — não só o dano.”

### Opção 3 — Contenção
**Sera Morn:** “Você cria contenção antes de decidir o reparo. É uma boa maneira de ganhar tempo sem fingir que o risco sumiu.”

---

## P20 — O Pulso sob a Lama → reação em P21
**choice_id:** `P20_pulse_interpretation`
**future_hook:** Ilyan apresenta Hemaris conforme o método escolhido.

### Opção 1 — Tratar como ameaça
**Sera Morn:** “Você quer risco primeiro. Então, quando eu falar de Hemaris, vou separar o que exige cautela do que exige apenas investigação.”

### Opção 2 — Medir fenômeno
**Ilyan Korr:** “Você quer medida antes de significado. É uma boa defesa contra confundir um efeito com uma intenção.”

### Opção 3 — Buscar função
**Ilyan Korr:** “Você procura para que a estrutura servia antes de julgar o que ela fez. É assim que pretendo lhe mostrar os registros.”

---

## S20 — Um Corpo que Continua → reação em P21/P22
**choice_id:** `S20_ethics`
**future_hook:** Ilyan reconhece sua posição ao abordar o Projeto.

### Opção 1 — Vida antes do protocolo
**Ilyan Korr:** “Você colocou a vida antes da regra. Quando chegarmos aos registros, não vou esconder de você quem pagava o preço por uma rotina.”

### Opção 2 — Entender antes de julgar
**Ilyan Korr:** “Você quer entender o protocolo antes de condená-lo. Tudo bem. Vou mostrar onde termina a descrição e começa o julgamento.”

### Opção 3 — Consentimento primeiro
**Ilyan Korr:** “Você foi direto sobre consentimento. Isso vai voltar quando encontrarmos o nome Hemaris. E eu vou tratar o assunto com a mesma precisão.”

---

## P21 — Os Hortos Vazios → reação em P22
**choice_id:** `P21_hemeris_archive`
**future_hook:** Os protocolos são apresentados conforme sua leitura ética.

### Opção 1 — Salvar uso, descartar resto
**Ilyan Korr:** “Você separa o que ainda pode ajudar do que nunca deveria ser repetido. Vou organizar os protocolos dessa forma.”

### Opção 2 — Preservar tudo
**Ilyan Korr:** “Você não quer que o abuso desapareça junto com a utilidade. Então o arquivo vai carregar as duas coisas, lado a lado.”

### Opção 3 — Separar camadas
**Ilyan Korr:** “Você quer função, prática e abuso em registros diferentes. É exatamente o tipo de distinção que impede um arquivo de virar defesa ou acusação.”

---

## S21 — Cicatrizes de Cultivo → reação em S22
**choice_id:** `S21_resource_ethic`
**future_hook:** O protocolo legado é lido à luz da escolha.

### Opção 1 — Reaproveitar
**Ilyan Korr:** “Você usa primeiro e pergunta depois quando o recurso pode ajudar agora. Vou lhe dizer de antemão onde esse impulso encontra limite.”

### Opção 2 — Estudar antes
**Ilyan Korr:** “Você quer entender o custo antes de usar. Nesse caso, vou lhe mostrar não só o que funciona, mas o que pode voltar a funcionar errado.”

### Opção 3 — Deixar intacto
**Ilyan Korr:** “Você prefere não tocar no que ainda não entende. É uma escolha prudente quando o preço de descobrir tarde demais é alto.”

---

## P22 — Transferência → reação em P23
**choice_id:** `P22_protocol_response`
**future_hook:** Ilyan mede confiança/desconfiança conforme sua disposição para cortar sistemas antigos.

### Opção 1 — Interromper coerção
**Ilyan Korr:** “Você corta uma rotina quando ela passa a usar pessoas sem consentimento. Eu sei exatamente onde você vai traçar a linha.”

### Opção 2 — Documentar antes
**Ilyan Korr:** “Você suportou ver o processo continuar para registrar o máximo possível. Não é uma escolha simples. Eu não a confundirei com aprovação.”

### Opção 3 — Reduzir dano
**Ilyan Korr:** “Você quer diminuir o dano sem destruir o registro. É a parte mais difícil: preservar a prova sem continuar alimentando o mecanismo.”

---

## S22 — Protocolos sem Paciente → reação em S24/P24
**choice_id:** `S22_protocol_legacy`
**future_hook:** A postura diante de legado técnico retorna.

### Opção 1 — Arquivar
**Ilyan Korr:** “Você deixa a ordem como evidência. Certo. Um arquivo não precisa obedecer ao que descreve.”

### Opção 2 — Bloquear repetição
**Ilyan Korr:** “Você desmonta o protocolo para impedir que alguém o use de novo. Eu vou marcar isso como decisão de segurança, não como apagamento da história.”

### Opção 3 — Preservar com contexto
**Ilyan Korr:** “Você mantém o texto e marca que ele já não é aplicável. É uma forma de preservar o passado sem entregá-lo ao presente.”

---

## S23 — Fluxo de Emergência → reação em P24
**choice_id:** `S23_priority`
**future_hook:** Sera lembra a lógica usada diante da Matriz.

### Opção 1 — Risco imediato
**Sera Morn:** “Você escolhe quem corre perigo agora. Então vou apresentar a Matriz primeiro pelo dano que ela ainda pode causar.”

### Opção 2 — Continuidade do sistema
**Sera Morn:** “Você olha para quem mantém a infraestrutura em pé. Eu vou mostrar o que quebra quando essa estrutura falha — e quem fica sem ela.”

### Opção 3 — Peso compartilhado
**Sera Morn:** “Você distribui o risco em vez de entregá-lo a um único lado. É assim que vamos discutir a Matriz.”

---

## P23 — O Custo da Persistência → reação em P24
**choice_id:** `P23_continuity_cost`
**future_hook:** A pergunta sobre a Matriz é moldada pela resposta.

### Opção 1 — Nenhum custo humano adicional
**Ilyan Korr:** “Você não aceita chamar outra pessoa de custo necessário. Então vamos medir a Matriz por aquilo que ela exige, não só pelo que ela produz.”

### Opção 2 — Custo limitado para salvar mais vidas
**Ilyan Korr:** “Você aceita um custo quando o ganho é concreto e imediato. Vou lhe mostrar onde a Matriz deixa de caber nessa justificativa.”

### Opção 3 — Continuidade com consentimento
**Sera Morn:** “Você não é contra continuidade. É contra continuidade sem limite. Isso muda a conversa inteira.”

---

## P24 — A Matriz Rubra → reação futura nos Altos
**choice_id:** `P24_legacy_judgment`
**future_hook:** Postura sobre continuidade, responsabilidade e custo viaja como memória pessoal.

### Opção 1 — Sistema útil sem supervisão
**Ilyan Korr:** “Você não chamou a máquina de má. Chamou o abandono de problema. É uma distinção que vai ajudar quando encontrarmos outras estruturas.”

### Opção 2 — Responsabilidade humana
**Ilyan Korr:** “Você colocou a escolha humana no centro. Então, quando um sistema antigo parecer culpado por si só, vou lembrar que você prefere procurar quem decidiu usá-lo.”

### Opção 3 — Separar sistema e responsabilidade
**Ilyan Korr:** “Você recusou uma resposta simples. Sistema, uso e responsabilidade ficam separados no seu registro. Boa prática para uma história cheia de camadas.”

---

## S24 — A Porta de Quarentena → reação futura nos Altos
**choice_id:** `S24_quarantine_choice`
**future_hook:** Em crises futuras, NPCs podem reconhecer a prioridade escolhida.

### Opção 1 — Conter risco
**Ilyan Korr:** “Você fecha primeiro quando o risco pode se espalhar. Então é isso que vou presumir quando a próxima crise não der tempo para debate.”

### Opção 2 — Resgatar primeiro
**Sera Morn:** “Você tenta alcançar quem ainda pode ser salvo. Eu vou lembrar disso antes de chamar uma porta fechada de solução.”

### Opção 3 — Contenção mínima + resgate
**Sera Morn:** “Você não aceita escolher entre salvar e conter sem tentar uma terceira via. Nem sempre vai funcionar. Mas sei qual tentativa vem primeiro.”

---

# 5. Altos Cinéreos

## P25 — O Peso Antigo → reação em P26
**choice_id:** `P25_infrastructure_ethic`
**future_hook:** Rava apresenta ordens de emergência conforme sua confiança em continuidade.

### Opção 1 — Manter função
**Rava Kern:** “Você começa pela função que já mantém gente de pé. Então, antes de abandonar um sistema, vou lhe mostrar o que dependia dele.”

### Opção 2 — Questionar função
**Rava Kern:** “Você não aceita manutenção só porque sempre foi assim. Certo. Quando chegar uma ordem de emergência, vou lhe dar também o motivo — não apenas a instrução.”

### Opção 3 — Alternativa
**Rava Kern:** “Você procura uma forma de manter a utilidade sem carregar o mesmo peso. É mais trabalho, mas pode ser o único caminho que vale a pena.”

---

## S25 — A Ponte que Espera → reação em S26
**choice_id:** `S25_priority`
**future_hook:** A prioridade escolhida influencia a ordem dos turnos.

### Opção 1 — Maior risco agora
**Rava Kern:** “Você atende primeiro quem pode cair primeiro. Vou manter isso em mente quando a ponte exigir mais de uma equipe.”

### Opção 2 — Quem não tem alternativa
**Rava Kern:** “Você prioriza quem não pode simplesmente procurar outro caminho. É uma medida de vulnerabilidade, não de barulho.”

### Opção 3 — Reparo compartilhado
**Rava Kern:** “Você divide o serviço para não deixar dois grupos esperando pela mesma solução. É o tipo de planejamento que uma montanha exige.”

---

## P26 — Ordens de Emergência → reação em P27/P28
**choice_id:** `P26_authority`
**future_hook:** Registros de emergência lembram a postura diante da autoridade.

### Opção 1 — Ordem mais recente
**Rava Kern:** “Você segue o documento mais novo. Quando lhe trouxer duas versões, vou lhe dizer qual chegou por último antes de pedir sua decisão.”

### Opção 2 — Investigar autoridade
**Rava Kern:** “Você pergunta quem tinha o direito de mandar antes de obedecer. É incômodo, mas evita que uma assinatura seja tratada como prova de legitimidade.”

### Opção 3 — Proteger vidas
**Rava Kern:** “Você coloca a vida acima da hierarquia quando as duas entram em conflito. Eu não vou fingir que isso é simples — só que você já mostrou onde fica sua prioridade.”

---

## S26 — Turno sem Fim → reação em P27
**choice_id:** `S26_burden_policy`
**future_hook:** A questão do custo reaparece.

### Opção 1 — Até falha
**Rava Kern:** “Você aceita empurrar a estrutura até ela quebrar. Então, quando falarmos de custo, vou considerar que seu limite é mais distante que o meu.”

### Opção 2 — Limite humano
**Rava Kern:** “Você impõe limite antes da falha. Isso não é fraqueza. É reconhecer que uma estrutura pode sobreviver mais que quem a mantém.”

### Opção 3 — Documentar desgaste
**Rava Kern:** “Você registra antes de decidir. Bom. Quando a mesma pressão aparecer em outro sistema, teremos números e não só memória.”

---

## P27 — A Continuidade a Qualquer Custo → reação em P28/P29
**choice_id:** `P27_continuity_cost`
**future_hook:** A postura sobre continuidade versus pessoas acompanha o personagem.

### Opção 1 — Custo controlado
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 2 — Recusar coerção
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 3 — Terceira solução
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

---

## S27 — Cabo Partido → reação em S30
**choice_id:** `S27_repair_policy`
**future_hook:** A postura de manutenção reaparece mais tarde.

### Opção 1 — Reparar agora
**Rava Kern:** “Você conserta primeiro para não deixar o lugar cair. Quando o próximo dano surgir, vou saber que essa será sua primeira preocupação.”

### Opção 2 — Causa primeiro
**Rava Kern:** “Você quer a causa antes do remendo. Então, se eu lhe entregar uma falha, não espere que eu ofereça só uma ferramenta — oferecerei o que sabemos sobre a origem.”

### Opção 3 — Estabilizar e investigar
**Rava Kern:** “Você não escolhe entre remendo e causa. Primeiro segura, depois pergunta. É uma ordem de trabalho que eu consigo respeitar.”

---

## P28 — Os Desvelados → reação em P29
**choice_id:** `P28_dissident_reading`
**future_hook:** A discussão sobre Convergência reconhece a leitura adotada.

### Opção 1 — Crítica não justifica sabotagem
**Eris Val:** “Você separa a crítica do crime. Isso significa que não precisamos apagar a primeira para condenar o segundo.”

### Opção 2 — Contexto antes do julgamento
**Eris Val:** “Você quer o contexto antes da sentença. Então vou lhe mostrar a cadeia de decisões antes de pedir que chame qualquer grupo de culpado.”

### Opção 3 — O ato muda o peso moral
**Eris Val:** “Você reconhece o contexto, mas não deixa que ele apague a consequência. Isso será importante quando reconstruirmos a Convergência.”

> **Nota de integração:** a fonte narrativa registra `Rava/Eris` neste nó. Eris Val é NPC canônica dos Confins. Não alterar o target sem revisão de autoria narrativa.

---

## S28 — Cartas de Emergência → reação em S29
**choice_id:** `S28_source_policy`
**future_hook:** O método de preservação documental retorna.

### Opção 1 — Preservar ambas
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 2 — Hierarquizar fontes
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 3 — Manter aberto
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

---

## P29 — Antes da Convergência → reação em P30
**choice_id:** `P29_convergence_ethic`
**future_hook:** A interpretação da sabotagem e da Regência reconhece a postura.

### Opção 1 — Benefício esperado
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 2 — Risco incontornável
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 3 — Tragédia sem simplificação
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

---

## S29 — Os que Disseram Não → reação em P30
**choice_id:** `S29_refusal`
**future_hook:** O quadro de responsabilidade recupera a leitura da recusa.

### Opção 1 — Desobediência perigosa
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 2 — Resistência legítima
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 3 — Compreender sem absolver
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

---

## P30 — O Colosso Cinéreo → reação em Confins
**choice_id:** `P30_accountability`
**future_hook:** A postura de responsabilidade influencia leituras futuras, sem conhecimento mágico.

### Opção 1 — Atos e autores
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 2 — Cadeia sistêmica
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 3 — Ato + sistema
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

---

## S30 — A Ordem que Restou → reação em Confins
**choice_id:** `S30_legacy_routine`
**future_hook:** Haro/Sera reconhecem a relação com tradição e mudança.

### Opção 1 — Procedimento comprovado
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 2 — Utilidade atual
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

### Opção 3 — Reforma contínua
**Sem fala NPC:** memória apenas do personagem; não gerar reação de NPC aqui.

---

# 6. Confins do Véu

## P31 — Onde o Véu Afina → reação em S32/S35/P34
**choice_id:** `P31_source_conflict`
**future_hook:** O tratamento de documentos contraditórios retorna.

### Opção 1 — Preservar ambas
**Sera Nol:** “Você deixou as duas leituras abertas. Aqui, isso não é indecisão. É impedir que o arquivo escolha uma realidade por nós.”

### Opção 2 — Procedência primeiro
**Roven Pell:** “Você olha primeiro para a cadeia de custódia. Então, quando duas folhas disserem coisas diferentes, começaremos por quem tocou cada uma delas e quando.”

### Opção 3 — Conflito aberto
**Sera Nol:** “Você aceitou deixar o conflito escrito. Prefiro isso a uma paz fabricada por apagamento.”

---

## S31 — Duas Vezes a Mesma Estrada → reação em P32
**choice_id:** `S31_trail_method`
**future_hook:** Talen Nyr reconhece seu método de investigação.

### Opção 1 — Evidência física
**Talen Nyr:** “Você segue a marca que o terreno consegue sustentar. No próximo trecho, vou separar primeiro pegada, desgaste e impressão.”

### Opção 2 — Comparar rotas
**Talen Nyr:** “Você quer ver as duas trilhas sobreviverem à comparação. Bom. Uma rota que só funciona uma vez não é uma rota em que eu confio.”

### Opção 3 — Não seguir sem testemunha
**Talen Nyr:** “Você não entra em uma trilha sem entender o que torna a outra falsa. Às vezes isso salva mais do que velocidade.”

---

## P32 — A Fratura → reação em P33
**choice_id:** `P32_fracture_language`
**future_hook:** O uso do termo prepara a introdução do Avesso.

### Opção 1 — Termo com limite
**Roven Pell:** “Você aceita o nome sem transformá-lo em explicação. É assim que uma palavra continua sendo ferramenta.”

### Opção 2 — Evitar termo sem definição
**Roven Pell:** “Você prefere não usar o nome antes de sabermos o que ele cobre. É um freio útil quando a linguagem começa a correr na frente da prova.”

### Opção 3 — Termo descritivo
**Sera Nol:** “Você usa 'Fratura' para descrever o que vemos, não para dizer que já entendemos o fenômeno. Essa distinção vai nos poupar problemas.”

---

## S32 — A Casa que Não Chegou → reação em S35
**choice_id:** `S32_record_conflict`
**future_hook:** A divergência entre matéria e documentação reaparece.

### Opção 1 — Matéria física
**Roven Pell:** “Você confia no que a parede, o chão e o objeto conseguem provar. Então vou colocar os elementos físicos à frente quando outra ficha discordar.”

### Opção 2 — Cadeia de custódia
**Roven Pell:** “Você segue a origem do documento. Certo. Vamos descobrir quem escreveu, quem guardou e quem trouxe antes de chamá-lo de falso.”

### Opção 3 — Coexistência
**Roven Pell:** “Você não apagou nenhum dos dois. Isso será útil quando uma nova prova discordar dos dois ao mesmo tempo.”

---

## P33 — O Avesso → reação em P34
**choice_id:** `P33_avesso_posture`
**future_hook:** A leitura da Âncora Central reconhece a postura adotada.

### Opção 1 — Novo objeto de estudo
**Eris Val:** “Você vê o Avesso como algo que ainda pode ser estudado. Ótimo — mas continue tratando o nome como descrição, não como explicação.”

### Opção 2 — Risco e cautela
**Sera Nol:** “Você prefere cautela a uma resposta total. Nesse lugar, isso pode ser a diferença entre observar e repetir um erro.”

### Opção 3 — Categorias incompletas
**Roven Pell:** “Você reconhece que nossas categorias falham. É uma forma honesta de continuar o arquivo sem forçar o mundo a caber nele.”

---

## S33 — Nomes em Ordem Errada → reação em S35
**choice_id:** `S33_correction_policy`
**future_hook:** O método de preservar original e correção retorna.

### Opção 1 — Corrigir a cópia
**Roven Pell:** “Você corrige a cópia para não espalhar o erro. Certo. O original, ainda assim, continua guardado.”

### Opção 2 — Anexar correção
**Roven Pell:** “Você quer o original intacto e a correção junto. É a forma mais segura de mostrar o que mudou sem fingir que nunca esteve errado.”

### Opção 3 — Adiar decisão
**Roven Pell:** “Você prefere deixar a marca aberta até termos mais prova. Então não vou fechar o registro antes de você.”

---

## P34 — A Âncora Central → reação em P35
**choice_id:** `P34_anchor_model`
**future_hook:** A reconstrução da Convergência reconhece o modelo adotado.

### Opção 1 — Nó de coordenação
**Eris Val:** “Você a trata como nó de coordenação. É uma leitura útil — desde que continuemos lembrando que útil não significa completa.”

### Opção 2 — Solução provável
**Eris Val:** “Você aceita a hipótese sem chamá-la de resposta final. É assim que devemos reconstruir a Convergência: por aproximações, não por certezas emprestadas.”

### Opção 3 — Procurar limites
**Roven Pell:** “Você pergunta o que a Âncora não fazia. Boa pergunta. Limite também é evidência.”

---

## S34 — A Testemunha de Ontem → reação em P35/P36
**choice_id:** `S34_temporal_discrepancy`
**future_hook:** A investigação precoce não concede verdade secreta; o método é reconhecido.

### Opção 1 — Fato sem teoria
**Talen Nyr:** “Você guardou o depoimento sem explicar o impossível. É assim que uma anomalia continua sendo revisável.”

### Opção 2 — Hipótese marcada
**Talen Nyr:** “Você marcou a hipótese e deixou a prova faltando à vista. Isso me permite continuar a investigação sem herdar sua certeza.”

### Opção 3 — Cadeia adicional
**Talen Nyr:** “Você quer reforçar a cadeia antes de confiar no depoimento. Justo. Uma testemunha sem procedência ainda é uma peça incompleta.”

---

## P35 — A Noite da Convergência → reação em P36
**choice_id:** `P35_responsibility_model`
**future_hook:** O fechamento do protocolo ecoa a postura de reconstrução.

### Opção 1 — Responsabilidade específica
**Eris Val:** “Você separou decisão de contexto. Então, no registro final, nomes e instituições ficarão ligados apenas onde a evidência permitir.”

### Opção 2 — Causalidade sistêmica
**Roven Pell:** “Você quer a cadeia inteira. O registro final vai acompanhar causas, decisões e consequências sem reduzir tudo a um único culpado.”

### Opção 3 — Incerteza preservada
**Sera Nol:** “Você não força o arquivo a responder onde ele ainda não consegue. Isso também é uma decisão responsável.”

---

## S35 — O Registro que Discorda → reação em P36
**choice_id:** `S35_orders_policy`
**future_hook:** O registro final reflete a preferência por preservação, hierarquia ou suspensão.

### Opção 1 — Preservar ambas
**Roven Pell:** “Você não apagou nenhuma das ordens. Então o registro final carregará o conflito em vez de fingir que uma delas nunca existiu.”

### Opção 2 — Hierarquizar com registro
**Eris Val:** “Você escolhe a ordem melhor sustentada, mas mantém a outra visível. É decisão sem limpeza artificial.”

### Opção 3 — Suspender julgamento
**Sera Nol:** “Você prefere esperar por mais prova. Então a ausência de decisão ficará registrada como escolha, não como esquecimento.”

---

## P36 — O Regente Fraturado → reação em Legado/Crônica
**choice_id:** `P36_final_record`
**future_hook:** O personagem leva um perfil pessoal de como trata evidência e memória.

### Opção 1 — Fatos confirmados
**Roven Pell:** “Seu registro termina onde termina a prova. Isso é uma marca útil: quando você diz 'confirmado', eu sei o que essa palavra vale.”

### Opção 2 — Fatos + interpretação marcada
**Eris Val:** “Você permite interpretação, mas não a esconde dentro do fato. É assim que uma crônica continua aberta a revisão.”

### Opção 3 — Fatos + lacunas + testemunhas
**Haro Sen:** “Você guardou também quem viu o quê. Não é só história. É responsabilidade por quem ficou para contar.”

---

## S36 — Depois da Última Ordem → reação pós-P36
**choice_id:** `S36_civil_continuity`
**future_hook:** A continuidade civil vira memória pessoal, sem alterar o mundo global.

### Opção 1 — Rotina comprovada
**Sera Nol:** “Você escolheu o que já provou que funciona. Talvez seja simples. Às vezes é justamente por isso que sobrevive.”

### Opção 2 — Rotina comunitária
**Haro Sen:** “Você ouviu quem continua vivendo aqui. Uma rotina só vale como continuidade quando as pessoas ainda reconhecem nela um lugar para ficar.”

### Opção 3 — Reforma local
**Sera Nol:** “Você escolheu mudar sem fingir que o passado nunca existiu. Vamos registrar a nova rotina como decisão de agora, não como verdade eterna.”

---

# 7. Notas de integração

1. Estas falas são **camada de copy**. Não devem criar `choice_id`, `memory_tag` ou `future_hook` novos.
2. A exibição deve consultar somente memórias legitimamente disponíveis ao NPC.
3. NPCs não devem citar tags internas, valores de relacionamento, IDs ou termos técnicos do sistema.
4. Uma reação futura pode ser curta e reaparecer em uma conversa posterior apenas se o `future_hook` permitir; não duplicar a memória.
5. O texto não deve converter Raça ou Classe em estereótipo. Linhas de identidade só entram quando a condição contextual da especificação for satisfeita.
6. Hemários modernos não devem ser tratados como culpados pelo Projeto Hemaris. Linhas sobre Hemaris devem distinguir história do projeto e identidade presente.
7. Nenhuma fala acima confirma automaticamente: Âncoras como solução cosmológica, Convergência integral, Projeto Hemaris completo, Avesso como entidade causal final, identidade dos Chefes ou outras revelações protegidas.
8. **P28** possui na fonte estrutural o alvo `Rava/Eris`; isso foi preservado, mas requer validação de autoria antes do wiring final.
9. **P27/P29/P30/S28/S29/S30** não têm alvo de NPC no contrato (só memória do personagem): todas as opções estão marcadas `Sem fala NPC` e o runtime não gera reação de NPC nesses nós. Se uma revisão do contrato passar a dar alvo de NPC a eles, a copy precisa ser escrita de novo.
10. **S6, S12, P18 e P24** têm retorno além da região original; a reação é memória pessoal, não transmissão automática de conhecimento a NPCs distantes. **P30 e S30** também retornam em outra região, mas hoje não têm fala de NPC (nota 9).

# 8. QA de copy — pendências 2026-11-12 resolvidas

- Os 9 nós com divergência de `choice_id`/opções foram alinhados ao contrato estrutural.
- As 29 falas que violavam escopo de conhecimento foram corrigidas: 11 receberam o NPC que realmente possui a memória e 18 foram convertidas em `Sem fala NPC`, pois a memória é exclusivamente do personagem.
- `Sera Morn` (Várzeas) e `Sera Nol` (Confins) permanecem distintos.
- `Talen Orm` (Nareth) e `Talen Nyr` (Confins) permanecem distintos.
- Nenhuma revisão de copy altera memória, Lore, world state, recompensa ou regra de Coop. Os `choice_id` dos 9 nós do item 1 passaram a ser os do contrato (§7).
- Os `future_hook` de S15, P16, S16, P17 e S18 foram reescritos para repetir o texto do contrato; o sentido de S18 passou a ser o do contrato (retorno em P19, memória pessoal).
- Duas frases foram retocadas fora da lista de pendências: P10/opção 1 ("ainda pode ser útil") e P14/opção 3.
- Conferência automática contra o catálogo do contrato (72 nós): todos os `choice_id` batem; todo NPC que fala recebe a memória da opção; toda opção `Sem fala NPC` não tem alvo de NPC no contrato.
- P14: as falas são de Nera Voss porque só Nera recebe a memória; o gancho (Talen em P15) descreve outro momento e segue como está no contrato. P20/opção 1: fala de Sera Morn pelo mesmo motivo; o gancho cita Ilyan em P21.

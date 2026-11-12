# ASTERION — Textos de Reação dos NPCs
## Pacote player-facing para Ação × Consequência · v1.0.0

**Objetivo:** fornecer as falas que materializam as memórias registradas pelo sistema narrativo.

**Uso:** cada opção abaixo é uma variante da reação futura correspondente ao `choice_id`. O runtime deve exibir somente a variante compatível com a memória pessoal legitimamente disponível.

**Regra:** estas falas não criam Lore nova, não revelam informação protegida, não transformam memória pessoal em conhecimento global e não substituem os `future_hooks` da especificação narrativa.

**Tom:** dark fantasy medieval, humano, contido. NPCs reconhecem comportamento, método ou decisão anterior; eles não leem a ficha interna do jogador.

**Fonte estrutural:** `ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md`.
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
**Iven Raal:** “Você protege a estrutura mesmo quando ela poderia ser útil. Eu discordo de parte do custo, mas sei que sua cautela não é descaso.”

### Opção 2 — Testar limite
**Iven Raal:** “Você aceita tocar no mecanismo para descobrir onde ele falha. Posso não escolher o mesmo caminho, mas agora sei que sua curiosidade tem um método.”

### Opção 3 — Priorizar passagem
**Dara Venn:** “Você aceita perder a estrutura se isso mantiver a rota aberta. Não é minha escolha favorita, mas sei por que você a fez.”

---

## S10 — Água sem Reflexo → reação em S12
**choice_id:** `S10_codex_method`
**future_hook:** A escolha define como os registros dos Vales são compostos.

### Opção 1 — Fato observado
**Iven Raal:** “Então o Códice vai começar pelo que os olhos conseguem sustentar. O resto fica separado até alguém trazer prova.”

### Opção 2 — Hipótese marcada
**Iven Raal:** “Hipótese marcada, certo. Assim podemos pensar sem esquecer onde a observação termina.”

### Opção 3 — Testemunhas
**Dara Venn:** “Você quer ouvir mais gente antes de fechar o registro. Faz sentido. Estradas diferentes produzem histórias diferentes — e às vezes uma delas entrega o detalhe que falta.”

---

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
**Nera Voss:** “Quando um nome aparecer de novo, vou lembrar que você quer descobrir o que ele quer dizer antes de simplesmente arquivá-lo.”

### Opção 2 — Preservar nomes
**Nera Voss:** “Você não deixou os nomes desaparecerem só porque ainda não os entende. Isso tem valor aqui também.”

### Opção 3 — Nomes + contexto
**Talen Orm:** “Você prefere nome, rota e pessoa na mesma comparação. Ótimo. Registro isolado costuma esconder tanto quanto revela.”

---

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
**Talen Orm:** “Você seguiu a obra diante de você. Quando eu lhe mostrar um mapa velho, vou tratá-lo como referência — não como ordem.”

### Opção 2 — Mapa + divergência
**Talen Orm:** “Você quer saber onde o mundo deixou o mapa para trás. Isso transforma a divergência em dado, não em erro de navegação.”

### Opção 3 — Registrar primeiro
**Talen Orm:** “Você anotou a diferença antes de escolher. É exatamente o que preciso de alguém que vai comparar versões depois.”

---

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
**choice_id:** `P15_deviation_reading`
**future_hook:** Talen escolhe que tipo de dado compartilhar primeiro.

### Opção 1 — Sensação/pressentimento
**Talen Orm:** “Você percebe o desvio antes de conseguir desenhá-lo. Quando isso acontecer de novo, vou ouvir sua descrição antes de procurar medida.”

### Opção 2 — Estrutura
**Talen Orm:** “Você quer saber o que fisicamente saiu do lugar. Ótimo. Vou começar por escala, apoio e direção antes de falar sobre causas.”

### Opção 3 — Evidência comparada
**Talen Orm:** “Você quer o dado que sobrevive à comparação. Então será o primeiro conjunto que eu lhe entregar.”

---

## S15 — Sob o Mesmo Céu → reação em S16
**choice_id:** `S15_map_pattern`
**future_hook:** Talen usa o padrão escolhido para apresentar o mapa.

### Opção 1 — Terreno
**Talen Orm:** “Você lê o chão antes do papel. Então o mapa começa com relevo, passagem e distância — e só depois com nomes.”

### Opção 2 — Correspondência de registros
**Talen Orm:** “Você quer o padrão que aparece em mais de uma fonte. Vou lhe mostrar as coincidências antes das diferenças.”

### Opção 3 — Marcas de percurso
**Talen Orm:** “Você confia em sinais de quem realmente atravessou o lugar. Isso ajuda a separar o mapa que parece certo do mapa que foi usado.”

---

## P16 — O Eixo sob a Terra → reação em P17
**choice_id:** `P16_structure_axis`
**future_hook:** O registro técnico é apresentado segundo seu método.

### Opção 1 — Técnica
**Talen Orm:** “Você quer medidas, apoio e comportamento. Então é isso que vou lhe mostrar primeiro. O resto fica depois.”

### Opção 2 — Segurança
**Nera Voss:** “Você quer saber o que ainda pode cair antes de saber por que foi construído. Não é menos importante. É o motivo de ainda estarmos vivos.”

### Opção 3 — Relação entre partes
**Talen Orm:** “Você procura a relação entre as peças. Vou lhe mostrar o eixo como sistema, não como uma pedra isolada.”

---

## S16 — Cartografia do Erro → reação em P17
**choice_id:** `S16_cartography_method`
**future_hook:** Nera confia ao personagem a comparação de fontes.

### Opção 1 — Procedência
**Nera Voss:** “Você quer saber de onde veio cada desenho antes de colocá-los lado a lado. Certo. Vou lhe dar o caminho de cada registro.”

### Opção 2 — Confronto direto
**Nera Voss:** “Você prefere colocar os dois mapas na mesa e ver onde quebram. Às vezes é a forma mais honesta de encontrar o erro.”

### Opção 3 — Teste no terreno
**Nera Voss:** “Você quer resolver o mapa no chão, não no papel. Então essa comparação vai começar pelo próximo trecho de estrada.”

---

## S17 — O Prumo Afundado → reação em P17
**choice_id:** `S17_mechanism_response`
**future_hook:** A abordagem influencia como a equipe trata o mecanismo central.

### Opção 1 — Preservar peça
**Talen Orm:** “Você quer manter o mecanismo intacto. Eu vou partir do princípio de que cada dano que evitarmos é uma informação que continua disponível.”

### Opção 2 — Testar funcionamento
**Talen Orm:** “Você aceita testar para saber o limite. Então vou marcar cada mudança antes de qualquer nova tentativa.”

### Opção 3 — Priorizar acesso
**Nera Voss:** “Você aceita perder a peça se ela estiver impedindo a passagem. Entendi. Primeiro vamos definir o custo que essa escolha realmente traz.”

---

## P17 — Medir o que Permanece → reação em P18
**choice_id:** `P17_measurement_posture`
**future_hook:** O preâmbulo do Arconte reconhece a postura.

### Opção 1 — Medir antes de explicar
**Talen Orm:** “Você quer a medida antes da história. Com o Arconte, vou começar pelaquilo que ainda podemos verificar.”

### Opção 2 — Modelo técnico
**Talen Orm:** “Você prefere uma estrutura explicativa, desde que ela continue presa aos dados. É assim que vou apresentar o próximo conjunto.”

### Opção 3 — Pressentimento marcado
**Nera Voss:** “Você sente que há algo errado, mas não chamou isso de prova. Muito bem. Aqui, sensação serve como alerta — não como sentença.”

---

## P18 — O Arconte Invertido → reação em P19
**choice_id:** `P18_archon_posture`
**future_hook:** A postura regional viaja como memória pessoal; não como segredo global.

### Opção 1 — Ler o fenômeno com contenção
**Nera Voss:** “Você saiu daqui sem transformar o Arconte em resposta para tudo. Vou levar essa cautela comigo.”

### Opção 2 — Questionar a leitura
**Talen Orm:** “Você quer separar o que sabemos do que estamos projetando. Concordo. É assim que um registro sobrevive à próxima versão.”

### Opção 3 — Buscar mais correlação
**Nera Voss:** “Você quer comparar antes de fechar a leitura. Então, quando a mesma questão surgir adiante, vou lembrar que ainda não terminamos.”

---

## S18 — Os Caminhos que Não Coincidem → reação em P19
**choice_id:** `S18_route_evidence`
**future_hook:** Memória pessoal sobre segurança e evidência aparece em Nareth/Várzeas.

### Opção 1 — Segurança primeiro
**Nera Voss:** “Você prefere uma rota segura mesmo sem entender tudo. Isso é útil quando o chão não espera pela nossa conclusão.”

### Opção 2 — Evidência primeiro
**Talen Orm:** “Você demora a decidir porque quer sustentar a decisão depois. Eu posso trabalhar com isso.”

### Opção 3 — Segurança + evidência
**Nera Voss:** “Você tenta não escolher entre as duas. É mais difícil, mas evita que uma resposta rápida destrua uma prova importante.”

---

# 4. Várzeas Carmesins

## P19 — Águas de Ferro → reação em P20
**choice_id:** `P19_region_priority`
**future_hook:** Sera enquadra o pulso conforme a prioridade adotada.

### Opção 1 — Rotas e segurança
**Sera Morn:** “Você colocou passagem segura antes do mistério. Então, quando o pulso aparecer, eu vou lhe dizer primeiro o que ele ameaça.”

### Opção 2 — Infraestrutura antiga
**Sera Morn:** “Você quer entender a estrutura antes de mexer nela. Certo. Só não esqueça que a água continua passando enquanto estudamos.”

### Opção 3 — Pessoas primeiro
**Sera Morn:** “Você perguntou primeiro por quem vive aqui. É assim que vou enquadrar o resto: o que isso faz com as pessoas vem antes do que isso significa.”

---

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
**Ilyan Korr:** “Você quer risco primeiro. Então, quando eu falar de Hemaris, vou separar o que exige cautela do que exige apenas investigação.”

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
**Rava Kern:** “Você não chamou a máquina de má. Chamou o abandono de problema. É uma distinção que vai ajudar quando encontrarmos outras estruturas.”

### Opção 2 — Responsabilidade humana
**Ilyan Korr:** “Você colocou a escolha humana no centro. Então, quando um sistema antigo parecer culpado por si só, vou lembrar que você prefere procurar quem decidiu usá-lo.”

### Opção 3 — Separar sistema e responsabilidade
**Ilyan Korr:** “Você recusou uma resposta simples. Sistema, uso e responsabilidade ficam separados no seu registro. Boa prática para uma história cheia de camadas.”

---

## S24 — A Porta de Quarentena → reação futura nos Altos
**choice_id:** `S24_quarantine_choice`
**future_hook:** Em crises futuras, NPCs podem reconhecer a prioridade escolhida.

### Opção 1 — Conter risco
**Sera Morn:** “Você fecha primeiro quando o risco pode se espalhar. Então é isso que vou presumir quando a próxima crise não der tempo para debate.”

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
**Rava Kern:** “Você aceita pagar quando o custo é conhecido e limitado. Então não vou esconder o preço das próximas decisões atrás da palavra 'necessário'.”

### Opção 2 — Recusar coerção
**Rava Kern:** “Você não aceita chamar sacrifício humano de manutenção. Entendido. Vou lhe dizer primeiro quem seria cobrado pela solução.”

### Opção 3 — Terceira solução
**Rava Kern:** “Você prefere atrasar a resposta a repetir a mesma violência. É uma escolha difícil. Mas é uma escolha clara.”

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
**Rava Kern:** “Você deixou as duas cartas visíveis. Bom. Uma contradição não desaparece porque escolhemos a mais conveniente.”

### Opção 2 — Hierarquizar fontes
**Rava Kern:** “Você escolheu a fonte que sustenta melhor a decisão e guardou a outra. Isso permite agir sem fingir que o conflito não existe.”

### Opção 3 — Manter aberto
**Rava Kern:** “Você deixou a divergência sem vencedor. Às vezes é a única forma de impedir que uma decisão de arquivo vire uma mentira.”

---

## P29 — Antes da Convergência → reação em P30
**choice_id:** `P29_convergence_ethic`
**future_hook:** A interpretação da sabotagem e da Regência reconhece a postura.

### Opção 1 — Benefício esperado
**Eris Val:** “Você pesa uma decisão pelo que pretendia salvar. Isso não absolve o risco, mas muda a pergunta que precisamos fazer.”

### Opção 2 — Risco incontornável
**Eris Val:** “Você começa pelo que podia dar errado e ainda assim exige que isso seja contado. Vou manter esse peso na reconstrução.”

### Opção 3 — Tragédia sem simplificação
**Eris Val:** “Você não chama de escolha fácil uma situação que não oferecia saída segura. Isso é diferente de absolver alguém.”

---

## S29 — Os que Disseram Não → reação em P30
**choice_id:** `S29_refusal`
**future_hook:** O quadro de responsabilidade recupera a leitura da recusa.

### Opção 1 — Desobediência perigosa
**Rava Kern:** “Você trata a recusa como risco para o conjunto. Então vou lhe mostrar também o que a ordem pretendia proteger.”

### Opção 2 — Resistência legítima
**Eris Val:** “Você reconhece que uma ordem pode estar errada. Isso não resolve a decisão de quem resistiu, mas muda o ponto de partida.”

### Opção 3 — Compreender sem absolver
**Eris Val:** “Você consegue entender por que alguém recusou sem apagar o dano que veio depois. É uma distinção importante.”

---

## P30 — O Colosso Cinéreo → reação em Confins
**choice_id:** `P30_accountability`
**future_hook:** A postura de responsabilidade influencia leituras futuras, sem conhecimento mágico.

### Opção 1 — Atos e autores
**Roven Pell:** “Você quer nomes e atos quando houver evidência para ambos. Isso evita que o contexto apague a responsabilidade pessoal.”

### Opção 2 — Cadeia sistêmica
**Roven Pell:** “Você prefere registrar o caminho inteiro até o resultado. É útil quando um erro não pertence a uma única mão.”

### Opção 3 — Ato + sistema
**Roven Pell:** “Você não escolhe entre pessoa e sistema. Vai manter os dois no mesmo registro, cada um no lugar que a prova permitir.”

---

## S30 — A Ordem que Restou → reação em Confins
**choice_id:** `S30_legacy_routine`
**future_hook:** Haro/Sera reconhecem a relação com tradição e mudança.

### Opção 1 — Procedimento comprovado
**Haro Sen:** “Você guarda o que já provou que funciona. No Refúgio, vou mostrar primeiro as rotinas que ainda seguram as pessoas de pé.”

### Opção 2 — Utilidade atual
**Sera Nol:** “Você prefere o que serve agora, não só o que sobreviveu ao passado. Isso importa quando uma tradição chega ao fim.”

### Opção 3 — Reforma contínua
**Haro Sen:** “Você não quer jogar fora a rotina nem obedecer a ela para sempre. Então vamos registrar a mudança como decisão presente.”

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
9. **P27/P29/P30/S28/S29/S30** possuem parte das memórias como globais ou com alvo incompleto; as falas acima usam o NPC regional mais próximo do contexto, mas o runtime deve respeitar o `npc_memory_targets` efetivamente canonizado na implementação.
10. **S6, S12, P18, P24, P30 e S30** têm retorno além da região original; a reação é memória pessoal, não transmissão automática de conhecimento a NPCs distantes.

# ASTERION --- O DESPERTAR DOS FLAGELOS

## Especificação final de conteúdo e implementação

**Status:** APROVADO PELO AUTOR\
**Escopo:** conteúdo, regras, equipamentos, receitas, Bestiário, Códice
e decisões de combate\
**Branch de implementação:** `claude/gifted-noether-0phq4y-i95bsl`\
**Regra:** `main` não deve ser alterada.

------------------------------------------------------------------------

## 1. Autoridade e princípio

Este documento consolida o pacote aprovado para **O Despertar dos
Flagelos**.

O Flagelo reutiliza a infraestrutura existente de World Events, combate,
Crafting, Bestiário/Códice, notificações e persistência. Não criar um
sistema paralelo de raid.

As regras específicas do Flagelo são exceções autorais deliberadas às
regras genéricas de World Event quando explicitamente indicadas neste
documento: - não expira por falta de participantes; - scaling próprio; -
0 Vigor; - recompensa própria; - elegibilidade por 3 Participation
Points.

As regras globais de combate, lock, materialização, Crafting,
idempotência e segurança continuam valendo quando este documento não
disser o contrário.

------------------------------------------------------------------------

# 2. Evento global

Seis regiões contribuem simultaneamente:

-   `tdo` --- Terras do Ocaso
-   `vde` --- Vales dos Enforcados
-   `nareth` --- Planícies de Nareth
-   `varzeas` --- Várzeas Carmesins
-   `altos` --- Altos Cinéreos
-   `confins` --- Confins do Véu

### Barra

-   limiar: **500 pontos por região**;
-   backend guarda número absoluto;
-   UI mostra `atual / 500` e porcentagem;
-   toda atividade válida concluída contribui;
-   cada `activity_id + character_id` só pode contribuir uma vez;
-   sem cap individual;
-   sem diminishing returns;
-   sem bônus para região atrasada;
-   enquanto o Flagelo estiver ativo, a barra daquela região fica
    congelada;
-   ao atingir 500, nasce imediatamente o Flagelo;
-   crossings simultâneos geram um único Flagelo;
-   o Flagelo persiste até derrota;
-   servidor reiniciado não perde estado;
-   morte zera a barra e inicia imediatamente novo ciclo.

### Contribuição

  Atividade                                         Pontos
  ------------------------- ------------------------------
  Caçada                                                +1
  Caçada em Grupo             +1 por participante elegível
  Desbravar                                             +1
  Contrato Regional                                     +2
  Missão Regional                                       +4
  Masmorra                                              +6
  Outros PvE equivalentes               valor configurável

Não existe cap diário de Caçada em V1.

### Notificações

Somente: - nascimento do Flagelo; - morte do Flagelo.

Uma comunidade/tópico compartilhado para as seis regiões. Reutilizar
outbox/idempotência e padrão visual existente.

------------------------------------------------------------------------

# 3. Combate do Flagelo

-   um único combatente compartilhado;
-   capacidade máxima: 200 participantes;
-   uma ação por oportunidade do Flagelo;
-   rodada global: 10 segundos;
-   resolução simultânea usando o motor existente;
-   sem sistema novo de party/raid;
-   sem núcleos/objetivos secundários em V1;
-   jogador derrotado pode reentrar;
-   cooldown de reentrada: 2 minutos;
-   sem limite de tentativas;
-   sem penalidade especial por morte;
-   HP do Flagelo é persistente;
-   sair/morrer não restaura HP;
-   scaling não reseta por saída;
-   scaling só reseta na morte.

### Vigor

**0 Vigor** para entrar no combate do Flagelo.

### Lock da Configuração

Ao entrar no combate, adquirir lock global da Configuração de Combate e
registrar snapshot autoritativo.

Enquanto o lock estiver ativo não pode mudar: - equipamentos; - armas; -
equipar/desequipar; - Runas; - Encantamentos; - upgrade/reroll/Serviço
incompatível; - Caminho; - Talentos; - 3 Artes Ativas; - Doutrina; -
outras escolhas que alterem a configuração efetiva.

Sair da tela, `/start`, `/menu`, fechar Telegram, trocar dispositivo,
desconectar/reconectar ou deep link não libera o lock.

O lock termina somente pela resolução válida do encontro. Uma nova
entrada cria novo snapshot.

### Esquiva

Flagelos usam a **esquiva global normalmente**.

Não existe regra de "chefe sempre acerta". Ataques básicos, especiais,
AoE e Preparados passam pela resolução global de acerto. Nenhum kit
atual declara precisão garantida.

------------------------------------------------------------------------

# 4. Scaling

O scaling fica pausado enquanto houver pelo menos um jogador em combate.

Quando ninguém estiver combatendo: - a cada 15 minutos: +8% HP Máximo; -
a cada 15 minutos: +3% ATQ; - DEF não escala; - cap HP: +80%; - cap ATQ:
+30%; - cap alcançado em 150 minutos.

Aumento de HP Máximo não cura HP atual.

O combate iniciado usa snapshot dos atributos do Flagelo no momento de
entrada.

------------------------------------------------------------------------

# 5. Participação e ranking

Para recompensa-base: **3 Participation Points**.

Pontos: - +1 effective damage \> 0; - +1 effective healing \> 0; - +1
barrier actually absorbed; - +1 Defender actually prevented damage; - +1
meaningful effect application.

Aplicação significativa exige mudança real de estado. Resistência,
imunidade e no-op não contam. Mudança real de duração/stack conta.

### Ranking

Ofensivo: `effective_damage`

Defensivo: `defender_prevented_damage + barrier_absorbed`

Suporte: `effective_healing`

Overheal não conta.

Top 3 em cada categoria. O mesmo personagem pode ocupar múltiplas
categorias.

Desempate: 1. métrica primária; 2. Participation Points; 3. timestamp em
que a métrica registrada foi atingida; 4. `character_id`.

------------------------------------------------------------------------

# 6. Recompensas

Cada participante elegível: - XP = `8% × level_xp(reference_level)`; -
Coroas = `50% × crowns_per_level(reference_level)`; - 3 materiais
básicos regionais; - 1 Fragmento do Flagelo.

Por morte: - exatamente 1 equipamento; - sorteado entre participantes
elegíveis; - templates com chance igual; - duplicatas permitidas; - sem
pity.

Ranking: - 1º: +3 Fragmentos +3 básicos; - 2º: +2 Fragmentos +2
básicos; - 3º: +1 Fragmento +1 básico.

Sem recompensa de last hit.

------------------------------------------------------------------------

# 7. Os seis Flagelos

  ---------------------------------------------------------------------------------------
  Região    Flagelo             Nv        HP       ATQ       DEF       AGI Fragmento
  --------- ------------ --------- --------- --------- --------- --------- --------------
  TDO       Varkhenn, o         10    35.060       138       100        94 Fragmento de
            Flagelo das                                                    Cinza
            Cinzas                                                         Condensada

  VDE       Nharvek, o          20    51.000       195       120       101 Fibra do Laço
            Flagelo dos                                                    Morto
            Laços                                                          

  Nareth    Azharel, o          30    53.300       198       160       165 Marco do
            Flagelo do                                                     Meridiano
            Meridiano                                                      Partido

  Várzeas   Hemrath, o          40    63.880       320       177       190 Coágulo de
            Flagelo                                                        Salmoura Rubra
            Rubro                                                          

  Altos     Korvann, o          50    98.740       310       306       204 Peso Fraturado
            Flagelo do                                                     
            Contrapeso                                                     

  Confins   Vaelith, o          60   107.840       401       322       334 Fragmento de
            Flagelo da                                                     Leitura
            Fratura                                                        Incompatível
  ---------------------------------------------------------------------------------------

Esses valores são baseline de configuração do Flagelo, não uma
substituição da curva global de inimigos.

------------------------------------------------------------------------

# 8. Kits

## Varkhenn

-   Golpe de Cinza --- 100% ATQ
-   Sopro de Fuligem --- AoE 80% ATQ + 1 Queimadura
-   Cinza no Pulso --- 90% ATQ + ATQ -10% · 2T, CD3
-   Peso do Entulho --- 130% ATQ, CD3
-   Última Fagulha --- Preparada 180% ATQ, CD5

## Nharvek

-   Golpe do Laço --- 100% ATQ
-   Tranco das Raízes --- 90% ATQ + AGI -10% · 2T, CD3
-   Nó de Peso --- 120% ATQ + DEF -10% · 2T, CD3
-   Tensão Compartilhada --- AoE 80% ATQ
-   Estrangulamento Final --- Preparada 180% ATQ, CD5

## Azharel

-   Golpe de Referência --- 100% ATQ
-   Correção de Linha --- 90% ATQ + DEF -10% · 2T, CD3
-   Medida Contrária --- 125% ATQ, CD3
-   Meridiano Divergente --- AoE 80% ATQ + AGI -10% · 2T, CD4
-   Linha Absoluta --- Preparada 180% ATQ, CD5

## Hemrath

-   Golpe de Salmoura --- 100% ATQ
-   Pressão de Válvula --- 90% ATQ + DEF -10% · 2T, CD3
-   Soro Corrosivo --- 85% ATQ + Veneno, CD3
-   Restituição Rubra --- cura própria 5% HP Máximo, CD5, máximo 3 usos
-   Sobrecarga de Matriz --- Preparada 180% ATQ, CD5

## Korvann

-   Golpe de Contrapeso --- 100% ATQ
-   Carga Distribuída --- 90% ATQ + DEF -10% · 2T, CD3
-   Escora Inversa --- ATQ +8%, DEF -8%, 2T, CD5
-   Ruptura de Cabo --- AoE 85% ATQ, CD4
-   Queda do Contrapeso --- Preparada 180% ATQ, CD5

## Vaelith

-   Golpe Desalinhado --- 100% ATQ
-   Duas Leituras --- 90% ATQ + ATQ -10% · 2T, CD3
-   Reflexo Partido --- 125% ATQ, CD3
-   Fratura Local --- AoE 80% ATQ
-   Protocolo Incompatível --- Preparada 180% ATQ, CD5

------------------------------------------------------------------------

# 9. IA

1.  Preparada elegível pronta → usar;
2.  senão, especial elegível de maior prioridade;
3.  senão, básico;
4.  respeitar cooldown;
5.  validar alvo;
6.  se ficar inválida, recalcular;
7.  sem aleatoriedade não determinística.

Preparadas devem usar o mecanismo existente de Prepared
Chains/telegraph.

------------------------------------------------------------------------

# 10. Equipamentos

Cada região possui 9 templates:

1.  Principal --- Épico --- SW2 --- Ferreiro
2.  Secundária --- Raro --- SW1 --- Ferreiro
3.  2H --- Lendário --- SW3 --- Ferreiro
4.  Cabeça --- Raro --- SW1 --- Ferreiro
5.  Torso --- Épico --- SW2 --- Ferreiro
6.  Mãos --- Raro --- SW1 --- Curteiro
7.  Pés --- Raro --- SW1 --- Curteiro
8.  Acessório --- Épico --- SW2 --- Joalheiro
9.  Artefato --- Lendário --- SW2 --- Joalheiro

Não criar classe mecânica de armadura. Veste/Leve/Média/Pesada não é
categoria global.

Armas: - Principal: espada, 1H, melee; - Secundária: adaga, 1H, melee; -
2H: - TDO: maça; - VDE: espada; - Nareth: arco; - Várzeas: maça; -
Altos: maça; - Confins: arco.

Usar metadata canônica de `form`, `handedness`, slot e tags; não inferir
compatibilidade pelo nome.

------------------------------------------------------------------------

# 11. Os 54 equipamentos

## TDO

1.  Lâmina da Última Brasa --- Principal --- Épico
2.  Guarda da Fuligem Presa --- Secundária --- Raro
3.  Maça do Entulho Morto --- 2H --- Lendário
4.  Elmo da Cinza Baixa --- Cabeça --- Raro
5.  Couraça do Poente Queimado --- Torso --- Épico
6.  Luvas do Último Fôlego --- Mãos --- Raro
7.  Botas da Estrada Carbonizada --- Pés --- Raro
8.  Selo da Fagulha Extinta --- Acessório --- Épico
9.  Relicário dos Nomes Queimados --- Artefato --- Lendário

## VDE

10. Lâmina do Laço Fechado --- Principal --- Épico
11. Guarda da Raiz Tensa --- Secundária --- Raro
12. Espada do Nó Profundo --- 2H --- Lendário
13. Elmo das Raízes Suspensas --- Cabeça --- Raro
14. Couraça do Berço Enredado --- Torso --- Épico
15. Luvas do Estrangulamento --- Mãos --- Raro
16. Botas da Turfa Presa --- Pés --- Raro
17. Selo do Nó Morto --- Acessório --- Épico
18. Relicário da Rede Sem Fim --- Artefato --- Lendário

## Nareth

19. Lâmina da Linha Exata --- Principal --- Épico
20. Guarda do Marco Partido --- Secundária --- Raro
21. Arco do Horizonte Contrário --- 2H --- Lendário
22. Elmo da Medida Divergente --- Cabeça --- Raro
23. Couraça do Eixo Desviado --- Torso --- Épico
24. Luvas da Linha Corrigida --- Mãos --- Raro
25. Botas do Meridiano Errado --- Pés --- Raro
26. Selo da Referência Contrária --- Acessório --- Épico
27. Relicário das Duas Coordenadas --- Artefato --- Lendário

## Várzeas

28. Lâmina da Salmoura Coagulada --- Principal --- Épico
29. Guarda da Válvula Rubra --- Secundária --- Raro
30. Maça da Matriz Sobrecarga --- 2H --- Lendário
31. Elmo da Pressão Carmesim --- Cabeça --- Raro
32. Couraça do Fluxo Contido --- Torso --- Épico
33. Luvas do Soro Corrosivo --- Mãos --- Raro
34. Botas do Dique Rubro --- Pés --- Raro
35. Selo da Restituição Rubra --- Acessório --- Épico
36. Relicário da Matriz Saturada --- Artefato --- Lendário

## Altos

37. Lâmina do Contrapeso Invertido --- Principal --- Épico
38. Guarda da Escora Profunda --- Secundária --- Raro
39. Maça do Peso Suspenso --- 2H --- Lendário
40. Elmo da Carga Distribuída --- Cabeça --- Raro
41. Couraça da Sustentação Final --- Torso --- Épico
42. Luvas do Cabo Tensionado --- Mãos --- Raro
43. Botas da Escarpa Travada --- Pés --- Raro
44. Selo da Carga Compartilhada --- Acessório --- Épico
45. Relicário do Peso Suspenso --- Artefato --- Lendário

## Confins

46. Lâmina das Duas Leituras --- Principal --- Épico
47. Guarda da Fratura Local --- Secundária --- Raro
48. Arco do Protocolo Incompatível --- 2H --- Lendário
49. Elmo da Referência Partido --- Cabeça --- Raro
50. Couraça da Marcha Fraturada --- Torso --- Épico
51. Luvas da Leitura Desalinhada --- Mãos --- Raro
52. Botas do Limiar Incompatível --- Pés --- Raro
53. Selo das Duas Versões --- Acessório --- Épico
54. Relicário do Retorno Impossível --- Artefato --- Lendário

Todos começam +0. Materialização, secundários, Bind, Runas,
Encantamentos, upgrade, reroll e demais propriedades seguem o sistema
global.

------------------------------------------------------------------------

# 12. Receitas

Cada equipamento acima possui uma Receita própria, totalizando 54.

IDs:

### TDO

-   `recipe.flagelo.tdo.lamina_ultima_brasa`
-   `recipe.flagelo.tdo.guarda.fuligem_presa`
-   `recipe.flagelo.tdo.maca.entulho_morto`
-   `recipe.flagelo.tdo.elmo.cinza_baixa`
-   `recipe.flagelo.tdo.couraca.poente_queimado`
-   `recipe.flagelo.tdo.luvas.ultimo_folego`
-   `recipe.flagelo.tdo.botas.estrada_carbonizada`
-   `recipe.flagelo.tdo.selo.fagulha_extinta`
-   `recipe.flagelo.tdo.relicario.nomes_queimados`

### VDE

-   `recipe.flagelo.vde.lamina.laco_fechado`
-   `recipe.flagelo.vde.guarda.raiz_tensa`
-   `recipe.flagelo.vde.espada.no_profundo`
-   `recipe.flagelo.vde.elmo.raizes_suspensas`
-   `recipe.flagelo.vde.couraca.berco_enredado`
-   `recipe.flagelo.vde.luvas.estrangulamento`
-   `recipe.flagelo.vde.botas.turfa_presa`
-   `recipe.flagelo.vde.selo.no_morto`
-   `recipe.flagelo.vde.relicario.rede_sem_fim`

### Nareth

-   `recipe.flagelo.nareth.lamina.linha_exata`
-   `recipe.flagelo.nareth.guarda.marco_partido`
-   `recipe.flagelo.nareth.arco.horizonte_contrario`
-   `recipe.flagelo.nareth.elmo.medida_divergente`
-   `recipe.flagelo.nareth.couraca.eixo_desviado`
-   `recipe.flagelo.nareth.luvas.linha_corrigida`
-   `recipe.flagelo.nareth.botas.meridiano_errado`
-   `recipe.flagelo.nareth.selo.referencia_contraria`
-   `recipe.flagelo.nareth.relicario.duas_coordenadas`

### Várzeas

-   `recipe.flagelo.varzeas.lamina.salmoura_coagulada`
-   `recipe.flagelo.varzeas.guarda.valvula_rubra`
-   `recipe.flagelo.varzeas.maca.matriz_sobrecarga`
-   `recipe.flagelo.varzeas.elmo.pressao_carmesim`
-   `recipe.flagelo.varzeas.couraca.fluxo_contido`
-   `recipe.flagelo.varzeas.luvas.soro_corrosivo`
-   `recipe.flagelo.varzeas.botas.dique_rubro`
-   `recipe.flagelo.varzeas.selo.restituicao_rubra`
-   `recipe.flagelo.varzeas.relicario.matriz_saturada`

### Altos

-   `recipe.flagelo.altos.lamina.contrapeso_invertido`
-   `recipe.flagelo.altos.guarda.escora_profunda`
-   `recipe.flagelo.altos.maca.peso_suspenso`
-   `recipe.flagelo.altos.elmo.carga_distribuida`
-   `recipe.flagelo.altos.couraca.sustentacao_final`
-   `recipe.flagelo.altos.luvas.cabo_tensionado`
-   `recipe.flagelo.altos.botas.escarpa_travada`
-   `recipe.flagelo.altos.selo.carga_compartilhada`
-   `recipe.flagelo.altos.relicario.peso_suspenso`

### Confins

-   `recipe.flagelo.confins.lamina.duas_leituras`
-   `recipe.flagelo.confins.guarda.fratura_local`
-   `recipe.flagelo.confins.arco.protocolo_incompativel`
-   `recipe.flagelo.confins.elmo.referencia_partida`
-   `recipe.flagelo.confins.couraca.marcha_fraturada`
-   `recipe.flagelo.confins.luvas.leitura_desalinhada`
-   `recipe.flagelo.confins.botas.limiar_incompativel`
-   `recipe.flagelo.confins.selo.duas_versoes`
-   `recipe.flagelo.confins.relicario.duas_versoes`

### Descoberta

-   25% por morte enquanto houver receitas desconhecidas daquele
    Flagelo;
-   uma receita desconhecida escolhida uniformemente;
-   no máximo uma descoberta por morte;
-   sem pity;
-   após 9 descobertas, sem roll.

### Custo

Usar custo global de Crafting por SW, acrescentando o Fragmento do
Flagelo.

Raro:
`8 básicos × SW + 4 Fragmentos de Aprimoramento × SW + 1 Fragmento do Flagelo × SW`

Épico:
`10 básicos × SW + 2 Catalisadores de Elite × SW + 6 Fragmentos de Aprimoramento × SW + 1 Fragmento do Flagelo × SW`

Lendário:
`14 básicos × SW + 4 Catalisadores de Elite × SW + 12 Fragmentos de Aprimoramento × SW + 1 Núcleo × SW + 1 Fragmento do Flagelo × SW`

Os custos globais existentes devem ser consultados no código/fonte
vigente antes de materialização; não criar nomenclatura econômica
paralela.

------------------------------------------------------------------------

# 13. Materiais regionais

Usar os materiais já existentes de cada Região:

-   TDO: Ferro de Fuligem, Couro Escoriado, Erva Cinzenta, Resíduo do
    Ocaso.
-   VDE: Ferro Enredado, Couro Musgoso, Erva de Turfa, Resina Enredada.
-   Nareth: Bronze de Marco, Couro de Horizonte, Erva de Vento, Pó de
    Eixo.
-   Várzeas: Ferro de Salmoura, Couro de Várzea, Junco Ferruginoso, Soro
    Antigo.
-   Altos: Ferro de Contrapeso, Couro de Escarpa, Líquen de Pedreira,
    Cinza de Basalto.
-   Confins: Ferro de Baliza, Couro de Marcha, Musgo de Limiar, Pó de
    Referência.

Não criar materiais básicos paralelos.

------------------------------------------------------------------------

# 14. Núcleos

Núcleos específicos das receitas lendárias:

-   Núcleo do Flagelo das Cinzas
-   Núcleo do Flagelo dos Laços
-   Núcleo do Flagelo do Meridiano
-   Núcleo do Flagelo Rubro
-   Núcleo do Flagelo do Contrapeso
-   Núcleo do Flagelo da Fratura

O sistema de aquisição deve ser implementado conforme o pacote de
recompensa aprovado; não criar moeda alternativa.

------------------------------------------------------------------------

# 15. Bestiário

## Varkhenn

Varkhenn não parece carregar cinzas. Parece ter sido construído por
elas. O corpo é coberto por placas escuras, rachadas e impregnadas de
fuligem. Entre as fissuras há pontos de calor baixo, como brasas que
resistiram mais tempo do que deveriam. Ele avança sem pressa, e cada
golpe parece carregar o peso de alguma coisa que já caiu. Os registros
associam Varkhenn ao desgaste, queimaduras, redução ofensiva e golpes
pesados.

**Conhecimento:** criatura anômala associada ao desgaste das Terras do
Ocaso; origem desconhecida.

## Nharvek

Nharvek parece uma criatura presa à própria estrutura. Fibras grossas
atravessam seu corpo e desaparecem sob placas de matéria vegetal
endurecida. Um puxão, uma tensão, um nó; depois o alvo percebe que já
não se move como antes. Os registros associam Nharvek à redução de
Agilidade e Defesa e à pressão sobre vários combatentes.

**Conhecimento:** criatura anômala associada a laços, pressão e
alteração de ritmo.

## Azharel

Azharel é difícil de descrever de frente. A posição das placas parece
mudar conforme o ponto de observação. Uma linha pode parecer reta de um
lado e inclinada de outro. Não há evidência de teletransporte ou viagem
temporal. Há apenas referências que deixam de concordar.

**Conhecimento:** criatura anômala ligada a referências incompatíveis.
Nenhuma conclusão sobre o Avesso deve ser extraída deste registro.

## Hemrath

Hemrath apresenta anatomia que lembra estrutura médica deformada, mas
não há evidência de que seja criação de Hemaris. Placas rubras, válvulas
naturais e bolsas se contraem sob pressão. Quando ferido, parece
reorganizar o próprio dano.

**Conhecimento:** criatura anômala de pressão biológica e sustentação.
Relação com Hemaris não estabelecida.

## Korvann

Korvann parece ter sido montado ao redor de um princípio: nada pode cair
sem que alguma coisa carregue o peso. Placas de pedra, cabos e massas de
metal estão presos ao corpo em pontos semelhantes a sistemas de
sustentação. Seus golpes não são rápidos; são inevitáveis.

**Conhecimento:** criatura anômala associada a carga, sustentação e
contrapeso.

## Vaelith

Vaelith é difícil de registrar porque dois registros honestos podem
discordar. Uma testemunha descreve uma lâmina; outra descreve duas. Uma
registra uma postura; outra registra uma postura incompatível. O corpo,
entretanto, permanece presente.

**Conhecimento:** criatura anômala associada a leituras incompatíveis e
fraturas locais. Isso não prova que o Avesso seja senciente nem prova
viagem temporal.

------------------------------------------------------------------------

# 16. Códice

### O Despertar dos Flagelos

Seis ocorrências anômalas surgem após atividade regional acumulada. Não
são os seis Chefes de Campanha e não os substituem. A cada derrota, o
ciclo regional reinicia. Ainda não existe explicação única para o
fenômeno.

### Cinzas e Varkhenn

Varkhenn concentra características das Terras do Ocaso: desgaste,
fuligem, peso e persistência. Sua relação exata com a atividade regional
permanece desconhecida.

### Laços e Nharvek

Nharvek apresenta estruturas semelhantes à rede subterrânea dos Vales.
Isso não demonstra que a Matriarca das Raízes o criou nem que faça parte
da mesma rede.

### Meridiano e Azharel

Azharel reproduz o problema de referências que deveriam concordar e
deixam de concordar. Não há evidência suficiente para concluir
deslocamento temporal, duplicação física ou consciência independente.

### Hemaris e Hemrath

Semelhança visual não estabelece origem. Hemários modernos não são
experimentos vivos nem culpados coletivos pelo Projeto Hemaris.

### Peso e Korvann

Korvann reproduz princípios de carga, sustentação e contrapeso
conhecidos dos Altos. Isso não prova que seja máquina antiga ou
fabricação asteriana.

### Fraturas e Vaelith

Vaelith demonstra que registros incompatíveis podem continuar sendo
testemunhos honestos. Sua existência não prova consciência do Avesso nem
viagem temporal.

Bestiário e Códice registram conhecimento do personagem; não são
conhecimento onisciente.

------------------------------------------------------------------------

# 17. Identidade visual

Imagens ficam a cargo do autor.

Direção: - Dark Fantasy 2D ilustrado; - horror trágico; - desenho
manual; - linhas finas de tinta; - cores pintadas dessaturadas; -
textura discreta; - predominância de sombra; - silhuetas memoráveis; -
criaturas devem parecer erradas antes de atacar.

Imagem não cria mecânica ou lore novo.

------------------------------------------------------------------------

# 18. Ciclo de morte

Ao derrotar: 1. fechar combate; 2. resolver métricas; 3. determinar
elegíveis; 4. calcular ranking; 5. resolver recompensas; 6. resolver
equipamento; 7. registrar morte; 8. notificar; 9. zerar barra; 10.
iniciar novo ciclo.

Todas as operações devem ser atômicas/idempotentes e resistentes a
crash/retry.

------------------------------------------------------------------------

# 19. Fora de escopo

-   imagens;
-   novo motor de raid;
-   novos sistemas de party;
-   nova economia;
-   novas classes;
-   novos atributos;
-   novos efeitos;
-   novos sistemas de Crafting;
-   novos sistemas de equipamento;
-   mudança de `main`;
-   lore adicional não aprovado.

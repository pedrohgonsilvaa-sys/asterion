# Asterion — Rotas da Expedição
## Catálogo consolidado

> Expedição é atividade de Guilda em Background, assíncrona. Cada rota possui 3 estágios de 24h e exatamente 3 opções por estágio: favorável, neutra e ruim.
> As pistas foram incorporadas ao texto para permitir interpretação sem revelar diretamente a escolha correta.

## 1. A Estrada que Perde Marcos

**route_id:** `expedition.estrada_perde_marcos`

### Estágio 1 — O Marco Ausente · 24h
A expedição encontra a primeira marca de estrada. O suporte ainda está de pé, mas a indicação que deveria apontar a direção desapareceu.

- **Examinar o suporte** — **Favorável**. A equipe procura marcas secundárias, desgaste no chão e sinais de passagem antes de escolher uma direção. A pedra está firme, mas o solo ao redor foi pisado recentemente em mais de uma direção.
- **Seguir a trilha usada** — **Neutra**. A equipe escolhe o caminho com maior evidência de trânsito recente. Há mais pegadas na trilha da esquerda, mas nenhuma prova que seja a rota correta.
- **Avançar sem o marco** — **Ruim**. A Guilda abandona a referência e segue por terreno aberto. Depois de algum tempo, outra pedra aparece à distância e parece apontar para um lugar diferente.

### Estágio 2 — Duas Marcas · 24h
Mais adiante surgem dois marcos intactos. Ambos têm sinais de uso recente, mas suas orientações não parecem concordar.

- **Comparar os dois marcos** — **Favorável**. A equipe registra distância, posição e relação entre as duas marcas. O desgaste de uma é mais antigo; a outra apresenta uma borda recentemente exposta, como se tivesse sido recolocada.
- **Escolher a marca mais conservada** — **Neutra**. A Guilda assume que a pedra mais preservada é a referência mais confiável. Ela é mais legível, mas suas costas têm a mesma erosão da marca anterior.
- **Confiar só nos mapas** — **Ruim**. Os registros da Guilda viram a referência principal. A rota registrada passa por uma elevação que, no terreno, parece ter mudado de função há muito tempo.

### Estágio 3 — O Caminho que Continua · 24h
A estrada termina diante de uma bifurcação sem marco. Um caminho aparenta ser moderno; o outro está quase tomado pela vegetação, mas possui sinais recentes de uso.

- **Investigar o caminho antigo** — **Favorável**. Há marcas de carga, mas nenhum acampamento recente. Quem passou por ali carregava algo pesado e não voltou pelo mesmo trajeto.
- **Seguir pela rota moderna** — **Neutra**. A estrada chega ao destino esperado. O caminho antigo, porém, aparece no mapa de retorno como uma linha que nunca deveria ter desaparecido.
- **Dividir a expedição** — **Ruim**. As equipes cobrem as duas opções. Ao reunir os registros, ambas descrevem a mesma colina de maneiras diferentes.

**Retorno:**
> A estrada não desapareceu. O que desapareceu foi a certeza de que seus marcos ainda significavam a mesma coisa.

## 2. O Rio que Mudou de Leito

**route_id:** `expedition.rio_mudou_leito`

### Estágio 1 — A Água Fora do Mapa · 24h
O primeiro curso d’água surge antes do ponto previsto nos registros.

- **Mapear o novo curso** — **Favorável**. A água é mais profunda do que parece, mas a margem oposta mostra marcas de carroças antigas.
- **Procurar uma passagem rasa** — **Neutra**. O trecho mais raso existe; pedras estão dispostas em intervalos quase regulares dentro da água.
- **Atravessar imediatamente** — **Ruim**. Quando o primeiro grupo atravessa, uma segunda corrente aparece atrás das pedras e muda rapidamente a distribuição da água.

### Estágio 2 — O Leito Antigo · 24h
A Guilda encontra marcas de um antigo curso seco que contradiz o traçado atual.

- **Comparar com registros antigos** — **Favorável**. As margens antigas apresentam o mesmo tipo de erosão observado onde o rio atual passa.
- **Usar o leito seco** — **Neutra**. O terreno é firme e oferece passagem. Pequenos depósitos de barro seco formam uma linha contínua sob a vegetação.
- **Desviar do rio** — **Ruim**. Quanto mais a expedição se afasta, mais frequentes ficam pequenas áreas de solo úmido sem água visível.

### Estágio 3 — A Ponte sem Rio · 24h
Uma ponte antiga surge diante da expedição. A estrutura parece preservada para uma corrente que já não existe.

- **Estudar a ponte** — **Favorável**. O centro está mais gasto que as extremidades; quem passava ali carregava peso regularmente.
- **Usar a ponte** — **Neutra**. A travessia é segura. Do outro lado, porém, existem marcas de água acima do nível atual do terreno.
- **Ignorar a ponte** — **Ruim**. A margem aparentemente firme cede em um trecho onde não deveria haver água.

**Retorno:**
> O rio não contou à Guilda quando mudou de caminho. Só deixou sinais de que um dia já correu por outro lugar.

## 3. Cinzas sobre a Estrada

**route_id:** `expedition.cinzas_sobre_estrada`

### Estágio 1 — A Carga Abandonada · 24h
A Guilda encontra carroças vazias e uma carga parcialmente intacta.

- **Inventariar primeiro** — **Favorável**. Certos tipos de carga foram retirados, enquanto outros permaneceram.
- **Recuperar o utilizável** — **Neutra**. O estoque permite reconstruir boa parte da carga, mas algumas caixas foram abertas sem que o conteúdo fosse levado.
- **Abandonar a carga** — **Ruim**. Entre as caixas há registros de transporte que não correspondem à rota esperada.

### Estágio 2 — A Estrada Quente · 24h
O caminho apresenta cinza recente, mas nenhuma fonte evidente.

- **Procurar a origem** — **Favorável**. Não há fogo; há uma faixa de cinza acumulada dentro de depressões do terreno, sempre voltada para o mesmo lado.
- **Usar a parte limpa** — **Neutra**. A faixa limpa é segura, mas passa entre dois trechos onde a cinza se acumulou.
- **Atravessar a área coberta** — **Ruim**. A cinza é leve demais para ter permanecido ali por acaso; sob ela, a estrada está quase intacta.

### Estágio 3 — O Último Carregamento · 24h
A expedição encontra a última carga da rota. Ela permanece organizada, como se a interrupção tivesse acontecido antes do carregamento terminar.

- **Verificar por que não partiu** — **Favorável**. O inventário está completo. O registro de saída, entretanto, já foi preenchido.
- **Retomar a rota** — **Neutra**. A carga segue intacta, mas a rota oficial continua marcada como interrompida.
- **Desmontar e selecionar** — **Ruim**. Entre os itens havia material destinado a uma parada que não aparece em nenhum registro da Guilda.

**Retorno:**
> As cinzas cobriam a estrada, mas não explicavam o abandono.

## 4. O Posto sem Testemunhas

**route_id:** `expedition.posto_sem_testemunhas`

### Estágio 1 — Portas Abertas · 24h
O posto está destrancado e aparenta ter sido abandonado há pouco tempo.

- **Inspecionar antes de usar** — **Favorável**. As ferramentas estão organizadas; o registro mais recente foi escrito com tinta diferente das linhas anteriores.
- **Usar como abrigo** — **Neutra**. O abrigo é seguro. O relógio da sala marca uma hora que ninguém consegue confirmar.
- **Levar ferramentas** — **Ruim**. A parede atrás da bancada possui marcas recentes de remoção de equipamento.

### Estágio 2 — O Livro de Passagem · 24h
Os registros apresentam décadas de entradas e saídas.

- **Comparar nomes e datas** — **Favorável**. Algumas pessoas aparecem entrando em períodos em que o posto deveria estar fechado.
- **Aceitar o livro como válido** — **Neutra**. A caligrafia permanece consistente por várias páginas; páginas seguintes parecem rearranjadas.
- **Ignorar o livro** — **Ruim**. Sem ele, desaparece a única referência sobre quem utilizava a passagem antes do abandono.

### Estágio 3 — A Testemunha Ausente · 24h
A Guilda encontra uma pequena construção nos fundos do posto. Há um banco, uma caneca e uma janela voltada para a estrada.

- **Investigar o ponto de observação** — **Favorável**. A janela oferece visão perfeita da passagem. O banco está gasto apenas em uma das extremidades.
- **Procurar alguém** — **Neutra**. Não há ninguém; há apenas sinais de que alguém continua verificando a estrada.
- **Declarar abandono** — **Ruim**. Quando a Guilda parte, a porta deixada aberta aparece fechada no registro de saída.

**Retorno:**
> O posto tinha tudo o que uma passagem precisava para funcionar. Só faltava alguém disposto a afirmar que ainda funcionava.

## 5. Três Registros, Uma Rota

**route_id:** `expedition.tres_registros_uma_rota`

### Estágio 1 — O Primeiro Registro · 24h
O primeiro documento descreve uma estrada ampla e estável.

- **Procurar fisicamente o trecho** — **Favorável**. O terreno atual não corresponde ao desenho, mas conserva marcas de uma passagem antiga.
- **Usar o registro como mapa** — **Neutra**. A direção geral funciona; distâncias e pontos de referência não.
- **Descartar por inconsistência** — **Ruim**. Mesmo incorreto em detalhes, o documento contém uma indicação de segurança que os outros dois não possuem.

### Estágio 2 — O Segundo Registro · 24h
O segundo documento apresenta a mesma rota como estreita, inclinada e difícil.

- **Comparar as duas descrições** — **Favorável**. Ambas mencionam uma estrutura na mesma altura, mas descrevem funções diferentes para ela.
- **Priorizar o mais recente** — **Neutra**. A data é posterior; a autoria não é indicada.
- **Seguir a descrição mais simples** — **Ruim**. O caminho simples leva ao mesmo ponto, mas não explica por que o segundo registro recomenda cautela.

### Estágio 3 — O Terceiro Registro · 24h
O último documento contradiz ambos em um detalhe importante: indica que a estrada possui duas passagens onde os outros registros mostram apenas uma.

- **Procurar a segunda passagem sem assumir sua posição** — **Favorável**. Existe uma segunda marca, mas ela não ocupa a posição descrita; a distância entre as duas permanece estranhamente regular.
- **Tratar como erro cartográfico** — **Neutra**. É possível explicar a diferença como erro, mas a mesma diferença aparece nos três documentos em lugares distintos.
- **Escolher um registro como definitivo** — **Ruim**. O trecho seguinte confirma parte de cada documento e contradiz outra parte de cada um.

**Retorno:**
> Três pessoas descreveram uma estrada. O mais estranho não foi discordarem. Foi cada uma ter registrado algo que as outras não poderiam simplesmente inventar.

## 6. A Estrada que Continua

**route_id:** `expedition.estrada_que_continua`

### Estágio 1 — O Portão Reaberto · 24h
Um antigo portão de estrada está aberto.

- **Examinar mecanismo e marcas** — **Favorável**. O mecanismo não foi quebrado; uma peça apresenta desgaste recente e deliberado.
- **Passar pelo portão** — **Neutra**. O caminho continua transitável durante o primeiro trecho.
- **Forçar o portão** — **Ruim**. A estrutura se move, mas o som percorre a estrada por muito mais tempo do que deveria.

### Estágio 2 — A Estrada Conservada · 24h
A Guilda encontra uma seção da estrada surpreendentemente bem mantida.

- **Identificar quem conserva o trecho** — **Favorável**. Não há trabalhadores. Há ferramentas recentes e uma substituição de pedra cuja cor não combina com o restante.
- **Aproveitar a passagem** — **Neutra**. O trecho é seguro; mais adiante, a manutenção termina.
- **Remover material conservado** — **Ruim**. Sob a pedra retirada existe uma antiga marca de orientação que não aparece nos mapas da Guilda.

### Estágio 3 — O Destino Aberto · 24h
A estrada termina diante de um ponto que não deveria estar conectado à rota moderna.

- **Registrar a conexão primeiro** — **Favorável**. A estrutura seguinte foi construída para receber viajantes, mas não há indicação de quem deveria chegar por ali.
- **Usar como atalho** — **Neutra**. A passagem economiza tempo e funciona; o retorno exige uma decisão diferente da ida.
- **Reivindicar como caminho permanente** — **Ruim**. A estrada pode ser usada, mas nada garante que a Guilda compreenda por que voltou a funcionar.

**Retorno:**
> A estrada estava fechada há anos. Ainda assim, alguém — ou alguma coisa — continuou preparando o caminho para quem viesse depois.

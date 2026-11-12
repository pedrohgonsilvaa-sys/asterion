"""Banco de Flavor Text (GDD v1.6.0 §37.4, §49.17).

Textos escritos a partir da Bíblia Canônica v4.0.7 (identidade e ambiente de cada
Região). Regras seguidas:

- só atmosfera, percepção e costumes já públicos; nada de segredo de autor, Avesso,
  Ruptura, Hemaris, Chefes ou revelação futura (§37.4.3);
- nenhum número, mecânica ou fato novo de lore (§37.4.5);
- todas as entradas têm prioridade 100 e peso 100: ainda não há flags de progresso
  para diferenciar variantes de antes e depois de descobertas.

Ficam com ``draft=False`` por delegação do autor (2026-11-12). Para tirar uma frase
de circulação sem apagar o id, use ``active=False``.
"""

# ruff: noqa: E501  (frases longas de prosa; o limite é de caracteres do Flavor, não de linha)

from __future__ import annotations

from asterion.domain.flavor import FlavorEntry, FlavorKind


def _bank(
    kind: FlavorKind, scope: str, key: str, prefix: str, lines: tuple[str, ...]
) -> tuple[FlavorEntry, ...]:
    return tuple(
        FlavorEntry(
            id=f"{prefix}.{index:02d}",
            kind=kind,
            scope=scope,
            key=key,
            text=text,
            draft=False,
        )
        for index, text in enumerate(lines, start=1)
    )


def _system(key: str, lines: tuple[str, ...]) -> tuple[FlavorEntry, ...]:
    return _bank(FlavorKind.SYSTEM, "system", key, f"system.{key}", lines)


def _region(key: str, lines: tuple[str, ...]) -> tuple[FlavorEntry, ...]:
    return _bank(FlavorKind.NARRATIVE, "region", key, f"region.{key}", lines)


FLAVOR_CATALOG: tuple[FlavorEntry, ...] = (
    # --- Telas de Sistema (§37.4.1): curtas, sem lore novo ---
    *_system(
        "personagem",
        (
            "Cada cicatriz aqui tem dono e data. O resto é o que você ainda vai se tornar.",
            "O nome fica gravado; o que ele significa ainda está sendo escrito pelos seus atos.",
            "Olhe com calma. O que você carrega diz mais do que o que você promete.",
        ),
    ),
    *_system(
        "inventario",
        (
            "Tudo o que cabe na bolsa já pesou em outra mão. Escolha o que vale carregar.",
            "Cada item guarda uma história que ninguém contou. A bolsa só guarda o peso.",
            "Peso é decisão. A estrada cobra de quem leva demais e de quem leva de menos.",
        ),
    ),
    *_system(
        "mercado",
        (
            "Preço é só uma promessa em voz alta. Confira antes de apertar a mão.",
            "Quem vende tem pressa; quem compra tem tempo. Use a sua vantagem.",
            "No balcão, toda moeda conta uma pequena história de necessidade.",
        ),
    ),
    *_system(
        "equipamentos",
        (
            "O que você veste diz ao mundo o que você espera dele. Cada peça já protegeu alguém.",
            "Metal gasto, couro remendado: ninguém anda com equipamento novo por muito tempo.",
            "Ajuste as correias e confira os fechos. A estrada não perdoa o que ficou solto.",
        ),
    ),
    *_system(
        "artes",
        (
            "Uma Arte é um gesto repetido até virar costume. O corpo lembra quando a cabeça cansa.",
            "Cada técnica custa fôlego e atenção. Escolha poucas e conheça-as bem.",
            "O que se pratica no escuro dura mais do que o que se promete à luz.",
        ),
    ),
    *_system(
        "talentos",
        (
            "Talento é o que sobra quando o treino acaba e a estrada começa. Escolha com cuidado.",
            "Cada escolha fecha uma porta e abre outra. Sem pressa: o caminho se faz andando.",
            "Ninguém nasce pronto. Aprende-se a ser o que a estrada exige, uma decisão por vez.",
        ),
    ),
    *_system(
        "oficios",
        (
            "Quem sabe consertar nunca fica sozinho por muito tempo. O ofício é uma forma honesta de ser útil.",
            "Mãos calejadas guardam um saber que nenhum registro alcança. Pratique, e o ofício responde.",
            "Fazer bem leva tempo, e é isso que o torna valioso num mundo que quebra com facilidade.",
        ),
    ),
    *_system(
        "legado",
        (
            "O que você deixa não cabe numa bolsa. Cabe numa lembrança, num nome repetido por quem ficou.",
            "Toda vida deixa marca, mesmo as curtas. A questão é quem vai lê-la depois.",
            "O que recebemos deve alcançar quem virá depois. É assim que um nome continua.",
        ),
    ),
    *_system(
        "guilda",
        (
            "Ninguém atravessa a escuridão sozinho por muito tempo. Uma Guilda é um nome dito em conjunto.",
            "Nomes juntos pesam mais que um nome só. Cuide de quem divide a estrada com você.",
            "A Guilda guarda o que o grupo construiu. Cada membro é, ao mesmo tempo, peso e apoio.",
        ),
    ),
    *_system(
        "calendario",
        (
            "O tempo aqui não passa; acumula. O Calendário diz o que ainda cabe neste dia.",
            "Cada dia herda o que o anterior deixou. Confira o que está aberto antes que feche.",
            "Prazo é a forma como o mundo lembra que as coisas acabam. Aproveite o que ainda está de pé.",
        ),
    ),
    # --- Regiões (§37.4.2): Bíblia Canônica v4.0.7 ---
    *_region(
        "tdo",  # Terras do Ocaso
        (
            "A estrada segue entre ruínas e campos de cinza, quebrada em trechos que ninguém consertou. O mundo continuou depois do colapso, mas não voltou a ser o mesmo. Adiante, uma fumaça fina marca onde ainda há gente.",
            "Cinza fria cobre a pedra escurecida e a vegetação baixa, mesmo onde nenhum fogo passou há muito tempo. Há ferrugem discreta nas ferragens abandonadas. Tudo aqui lembra que alguém construiu, e depois deixou de poder cuidar.",
            "No Refúgio, perder uma ferramenta pesa tanto quanto perder uma rota. Cada nome escrito num registro é um pequeno ato de teimosia. Os vigias dormem em turnos, e ninguém promete mais do que consegue manter.",
            "O crepúsculo daqui às vezes vem cobreado, coado pela fumaça. Não é presságio; é só o fim de mais um dia que a luz mal conseguiu atravessar. Os Braseiros seguem sendo o único calor confiável do mundo.",
            "Entre a cinza aparecem lajes bem cortadas, canais e metal envelhecido: obra de uma civilização que media tudo. Quem passa por elas aprende a andar em silêncio. Nem tudo o que ronda por ali é viajante.",
            "Quem passa por aqui deixa registros simples e evita grandes promessas. Valoriza-se quem mantém algo funcionando: uma lâmpada, uma ponte, uma palavra dada. É assim que se mede um bom dia no Ocaso.",
        ),
    ),
    *_region(
        "vde",  # Vales dos Enforcados
        (
            "Raízes gigantes descem pelos paredões e seguram restos de estrada onde a pedra já cedeu. A névoa baixa esconde o chão. Uma ponte boa ontem pode amanhecer torcida, e o Vale não pede desculpas.",
            "Cordas, nós e marcas de passagem são a língua do Vale, e não magia. Cada nó diz por onde alguém passou e quando. Quem desaparece é lembrado pelo nome e pela última rota conhecida; ninguém presume destino sem evidência.",
            "A madeira escura goteja o tempo todo, e o musgo cobre o que se deixa para trás. Estruturas suspensas rangem acima da cabeça. Ruínas antigas foram engolidas aos poucos, sem pressa e sem testemunhas.",
            "Água escura sobe pelos baixios e prende a bota. A névoa pesada devolve o som atrasado, e cada passo parece ter companhia. Na Vigília dizem que o Vale pune certezas e recompensa quem confere duas vezes.",
            "Pedra asteriana e raiz disputam o mesmo espaço, e nenhuma das duas cede. Onde a ruína foi comprimida, o silêncio é de coisa apertada. Caminhar ali pede cuidado com tudo o que parece firme.",
            "A Vigília vive de passagem segura, coleta e reparo de pontes. Ninguém ali fala em sorte; fala-se em tábuas trocadas e cordas revistas. A cada manhã o terreno é lido de novo antes de qualquer decisão.",
        ),
    ),
    *_region(
        "nareth",  # Planícies de Nareth
        (
            "A planície se abre em gramíneas secas sob um céu frio. Linhas antigas correm quase retas demais, e os marcos são a primeira língua da Região. O horizonte é belo, mas ninguém aqui o aceita sem conferir.",
            "No Posto de Nareth, prestígio vem de corrigir mapas em público, e não de fingir precisão. Os cartógrafos repetem trajetos só para saber se o mapa ainda descreve o mundo. Distância é algo que se verifica.",
            "Os canais secos cortam a planície como cicatrizes de engenharia: leitos rachados, comportas antigas, pontes estreitas. A água que um dia correu por aqui foi medida e dividida por gente cuidadosa. Hoje só o vento passa.",
            "Em certos trechos a sombra aponta para o lado errado, e a distância não bate com o passo. Nada desmorona; apenas deixa de concordar. Quem caminha por Nareth aprende a desconfiar com educação.",
            "Cisternas reparadas, estábulos e caravanas que partem e voltam para comparar rotas. A Mesa dos Marcos cuida do que é de todos. A planície parece vazia, mas está inteira coberta de medidas.",
            "Nareth também é escura, mesmo sob o céu aberto. A luz que há é fria e não aquece. O Braseiro continua sendo o único lugar onde o frio recua um pouco, e os viajantes se reúnem em volta dele sem falar de distância.",
        ),
    ),
    *_region(
        "varzeas",  # Várzeas Carmesins
        (
            "A água tem cor de ferrugem, e o ar tem gosto de sal. Barragens e passagens elevadas cortam o pântano em pedaços. O vermelho daqui é mineral e orgânico; é só o que a terra deixou na água.",
            "Juncos altos se dobram sem vento. No Porto da Salmoura, barqueiros e boticários cuidam da água como quem cuida de gente: com quarentena, com paciência e com pouca conversa. Ali ninguém atravessa o cais com pressa.",
            "Do fundo do brejo sobe, de tempos em tempos, uma pulsação surda. Pressão, fauna e o que está enterrado se combinam em ritmos que ninguém explica por inteiro. Convém contar os intervalos antes de atravessar.",
            "Tubos, reservatórios e salas antigas aparecem entre a vegetação, cercados de juncos. Foram feitos para cuidar, e a forma como resistem ao tempo incomoda. A natureza avança sobre eles devagar, sem pedir licença.",
            "As Casas do Pulso guardam nomes e linhagens, especialmente entre os Hemários, sem culto a nada. Consentimento, água limpa e quarentena responsável são assuntos de todo dia nas Várzeas. Aqui se aprende cedo a perguntar antes de tocar.",
            "O cais range sob barcos que levam gente e remédios de um dique a outro. A salmoura endurece as cordas. Quem vive aqui cheira a sal e a erva, e todos sabem pesar o que compram. Nas Várzeas, cuidado é uma forma de moeda.",
        ),
    ),
    *_region(
        "altos",  # Altos Cinéreos
        (
            "O vento corta a escarpa de basalto e leva a cinza mineral montanha abaixo. Pilares quebrados ainda seguram o que podem. Tudo aqui foi feito para repartir peso, e o peso continua pedindo quem o carregue.",
            "Pontes de cabo e contrapesos monumentais atravessam o vazio. É a escala da integração asteriana vista de baixo, pequena e silenciosa. Cada travessia lembra que alguém decidiu que valia manter aquele caminho.",
            "No Abrigo do Peso, manutenção é política: escolher qual ponte recebe material é escolher quais comunidades seguem ligadas. Os Mantenedores sabem disso e trabalham mesmo assim. O que só permanece porque ninguém pode abandoná-lo já começou a falhar.",
            "Guindastes antigos pendem sobre cortes de montanha, e plataformas de extração seguem de pé em silêncio. A pedra tirada daqui sustentou coisas que já não existem. Os Altos são de todos os povos; ninguém os possui.",
            "Companhias de Escarpa e Leitores de Ordem guardam o que sabem: rotas, resgates, a memória das cargas. Na altitude, o frio exige corda e paciência. Ninguém sobe sozinho por teimosia mais de uma vez.",
            "Cabos longos vibram ao vento com um som baixo, quase de voz. Basalto escuro, nuvem rasa, cinza nos ombros. Mesmo aqui a luz é rara, e a gente fala baixo para não cansar o que ainda aguenta.",
        ),
    ),
    *_region(
        "confins",  # Confins do Véu
        (
            "A névoa dos Confins é névoa de verdade, e ainda assim os marcos parecem mudar de lugar. Aqui se aprende a comparar antes de duvidar de si. Contradição é dado, e não fracasso. Anote o que viu e confira de novo no caminho de volta.",
            "No Último Refúgio tudo é registrado em dobro: duas placas, duas testemunhas, duas rotas. Não é ritual, e nenhum procedimento controla o Véu. É só o que basta para viver onde memória e matéria às vezes divergem.",
            "Há estradas que o mapa jura existir e o chão nega, e outras que o chão mostra e a memória não reconhece. Os Cartógrafos da Ausência anotam as duas versões, lado a lado, e seguem adiante sem decidir qual delas está certa.",
            "Certos objetos guardam estados quase iguais e, ainda assim, contraditórios. Uma porta que se lembra aberta e fechada ao mesmo tempo. Não é magia; é o mundo tendo dificuldade de manter a própria conta.",
            "Os Braseiros dos Confins são materiais, seguros, verificáveis, e nenhum deles é portal. Ficar perto de um é lembrar que o calor existe e que alguém já esteve aqui antes, deixando marcas que ainda conferem.",
            "A Vigília de Referência compara marcas, repete rotas de ida e volta e confia em testemunhas independentes. Quem entra na Marcha Nebulosa leva uma linha, um registro e alguém que lembre. Sozinho, o mundo é difícil de provar.",
        ),
    ),
)

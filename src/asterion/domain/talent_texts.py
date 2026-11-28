"""Textos de apresentação dos Talentos (ASTERION_TALENTOS_FLUXO_E_ESPECIFICACAO_COMPLETA §6).

Efeito e descrição narrativa são só apresentação; a mecânica fica em ``talents.py``.
"""

TALENT_TEXTS: dict[str, tuple[str, str]] = {
    'talent.sentinela.aco_desperto': (
        '+1% ATQ',
        (
            'A experiência de combate desperta uma força que já estava presente no corpo. O '
            'Sentinela transforma firmeza e presença em golpes mais seguros e pesados.'
        ),
    ),
    'talent.sentinela.carne_de_pedra': (
        '+1% HP',
        (
            'O Sentinela aprende a suportar o impacto sem ceder. Cada confronto endurece o corpo '
            'e torna mais difícil derrubá-lo.'
        ),
    ),
    'talent.sentinela.ritmo_de_guarda': (
        'Retaliação → +5% AGI até o fim do próximo turno',
        (
            'Depois de receber um impacto e responder a ele, o Sentinela encontra um ritmo '
            'próprio. A guarda passa a conduzir o próximo movimento.'
        ),
    ),
    'talent.sentinela.ponta_revidada': (
        'ação com Retaliação → +4 p.p. PER',
        (
            'Quando o adversário abre uma brecha ao atacar, o Sentinela responde no instante em '
            'que a defesa se transforma em oportunidade.'
        ),
    ),
    'talent.sentinela.placas_internas': (
        '+2% DEF',
        (
            'A proteção deixa de depender apenas da armadura visível. Postura, encaixe e '
            'experiência fazem o corpo absorver melhor aquilo que não pode evitar.'
        ),
    ),
    'talent.sentinela.guarda_preparada': (
        'após Defender reduzir Dano Direto, próxima Barreira em 2T recebe +6%',
        (
            'Uma defesa bem executada prepara o corpo para o impacto seguinte. O Sentinela '
            'transforma o tempo ganho ao se proteger em uma reserva de segurança.'
        ),
    ),
    'talent.sentinela.pressao_de_fissuras': (
        '+3% Dano Direto contra alvo com −DEF',
        (
            'O Sentinela reconhece quando uma defesa já começou a ceder. Nessas fissuras, cada '
            'golpe encontra menos resistência.'
        ),
    ),
    'talent.sentinela.firme_sob_impacto': (
        'ação inimiga que remove ≥8% HP → +5% DEF 1T',
        (
            'Grandes impactos não fazem o Sentinela recuar. Quando um golpe realmente pesa, o '
            'corpo se fecha ainda mais para suportar o que vier depois.'
        ),
    ),
    'talent.sentinela.retaliacao_persistente': (
        '+1T de duração da Retaliação, sem carga extra',
        (
            'Uma oportunidade de resposta não desaparece imediatamente. O Sentinela conserva a '
            'tensão da guarda até que o momento certo apareça.'
        ),
    ),
    'talent.sentinela.olho_de_combate': (
        '+2 p.p. CRIT',
        (
            'Depois de tantos confrontos, certos movimentos se tornam previsíveis. O Sentinela '
            'reconhece o instante em que um golpe pode encontrar um ponto decisivo.'
        ),
    ),
    'talent.sentinela.barreira_densa': (
        'Barreiras recebidas +5%',
        (
            'Quando uma proteção se forma ao redor do Sentinela, ela encontra uma base mais '
            'estável. O corpo sustenta a defesa em vez de simplesmente depender dela.'
        ),
    ),
    'talent.sentinela.contrapeso': (
        'após Retaliação → +4% DEF 1T',
        (
            'Toda resposta deixa uma consequência. Ao devolver um golpe, o Sentinela reorganiza '
            'sua postura e permanece preparado para o próximo impacto.'
        ),
    ),
    'talent.sentinela.ponta_penetrante': (
        '+2 p.p. PER',
        (
            'A força deixa de ser suficiente. O Sentinela direciona cada ataque para o ponto em '
            'que a defesa oferece menor resistência.'
        ),
    ),
    'talent.sentinela.postura_de_ferro': (
        'Defender +2 p.p.',
        (
            'Defender-se torna-se um ato consciente, não uma reação desesperada. A postura '
            'permanece firme mesmo quando o combate tenta quebrá-la.'
        ),
    ),
    'talent.sentinela.vigilia': (
        'primeira vez ≤50% HP → recebe 1 Retaliação',
        (
            'Quando o perigo realmente se aproxima, os sentidos do Sentinela se aguçam. O momento '
            'em que muitos recuariam se torna uma oportunidade de resposta.'
        ),
    ),
    'talent.sentinela.punicao_final': (
        '+4% Dano Direto contra alvo ≤40% HP',
        (
            'O Sentinela reconhece quando uma luta está chegando ao fim. Quando o adversário '
            'perde terreno, cada golpe passa a carregar o peso de uma decisão.'
        ),
    ),
    'talent.sentinela.persistencia': (
        'próprio HP ≤35% → +7% DEF',
        (
            'Mesmo ferido, o Sentinela permanece de pé. A proximidade da derrota desperta uma '
            'resistência que não existia no início do combate.'
        ),
    ),
    'talent.sentinela.guarda_integra': (
        (
            'após Defender, próximo Debuff numérico removível antes do próximo turno tem '
            'magnitude −10%'
        ),
        (
            'Uma guarda perfeita não protege apenas contra o golpe. Ela preserva o corpo contra '
            'aquilo que tenta permanecer depois dele.'
        ),
    ),
    'talent.errante.fio_afiado': (
        '+1% ATQ',
        (
            'Um golpe mais limpo, mais direto e preciso. O Errante transforma pequenos espaços de '
            'abertura em ataques que encontram o alvo com maior eficiência.'
        ),
    ),
    'talent.errante.passo_prudente': (
        '+1% HP',
        'O Errante aprende a preservar o corpo e avançar sem se expor além do necessário.',
    ),
    'talent.errante.instinto_rapido': (
        '+3% AGI',
        (
            'Movimentos rápidos e respostas imediatas permitem ao Errante agir antes que a '
            'situação se feche.'
        ),
    ),
    'talent.errante.brecha_exposta': (
        'ação com Oportunismo → +4 p.p. PER',
        (
            'Quando uma abertura surge, o Errante sabe exatamente onde pressionar para '
            'transformá-la em vantagem.'
        ),
    ),
    'talent.errante.reflexo': (
        '+1 p.p. Esquiva',
        'O corpo reage antes do pensamento, desviando de golpes que pareciam inevitáveis.',
    ),
    'talent.errante.sangue_frio': (
        'Esquiva bem-sucedida → próximo Dano Direto em 2T recebe +5 p.p. CRIT',
        (
            'Depois de escapar de um golpe, o Errante mantém a calma e encontra uma oportunidade '
            'para contra-atacar.'
        ),
    ),
    'talent.errante.precisao_cruel': (
        '+2 p.p. CRIT',
        (
            'Ataques contra pontos vulneráveis tornam-se ainda mais perigosos quando executados '
            'sem hesitação.'
        ),
    ),
    'talent.errante.couro_leve': (
        '+2% DEF',
        (
            'Equipamento e postura são ajustados para resistir ao impacto sem comprometer a '
            'mobilidade.'
        ),
    ),
    'talent.errante.passos_da_sombra': (
        'ao aplicar efeito negativo → +5% AGI até próximo turno',
        (
            'Ao enfraquecer o inimigo, o Errante aproveita a confusão para desaparecer da linha '
            'de resposta.'
        ),
    ),
    'talent.errante.oportunismo_ampliado': (
        'Oportunismo +8% → +10%',
        (
            'Uma abertura pequena pode se transformar em uma vantagem decisiva para quem sabe '
            'esperar o momento certo.'
        ),
    ),
    'talent.errante.sobrevivencia': (
        'próprio HP ≤40% → +5% DEF',
        (
            'Quando a luta se torna perigosa, cada movimento passa a ser guiado pela necessidade '
            'de permanecer de pé.'
        ),
    ),
    'talent.errante.desvio_ofensivo': (
        'após Esquiva → próximo Dano Direto +4 p.p. PER',
        (
            'Um desvio bem executado não encerra o movimento: ele cria a abertura para o próximo '
            'golpe.'
        ),
    ),
    'talent.errante.fio_perfurante': (
        '+2 p.p. PER',
        (
            'O Errante concentra força e precisão em pontos onde a defesa oferece menor '
            'resistência.'
        ),
    ),
    'talent.errante.pele_endurecida': (
        '−8% dano de DoT',
        (
            'A experiência torna o corpo mais preparado para suportar os efeitos persistentes '
            'deixados pelo combate.'
        ),
    ),
    'talent.errante.ritmo_predatorio': (
        'após Oportunismo → +5% AGI no próximo turno',
        (
            'Depois de encontrar uma oportunidade, o Errante acelera o ritmo e não permite que o '
            'alvo recupere o controle.'
        ),
    ),
    'talent.errante.fim_proximo': (
        '+4% Dano Direto contra alvo ≤35% HP',
        (
            'Quando o inimigo já está enfraquecido, o Errante sabe exatamente quando transformar '
            'vantagem em desfecho.'
        ),
    ),
    'talent.errante.primeiro_desvio': (
        'primeiro Dano Direto recebido no combate −8%',
        'O primeiro golpe de uma batalha raramente encontra o Errante desprevenido.',
    ),
    'talent.errante.instinto_de_fuga': (
        'primeira vez ≤30% HP → +10 p.p. Esquiva até próximo turno',
        (
            'Quando a situação chega ao limite, o instinto assume o controle e transforma perigo '
            'em distância.'
        ),
    ),
    'talent.vigia.mao_firme': (
        '+1% ATQ',
        (
            'O Vigia mantém a mão estável mesmo quando o campo de batalha se move ao redor. A '
            'precisão começa antes mesmo do disparo.'
        ),
    ),
    'talent.vigia.sobrevivente_das_trilhas': (
        '+1% HP',
        (
            'Longas jornadas ensinam o Vigia a suportar frio, cansaço e terreno hostil sem perder '
            'a capacidade de continuar avançando.'
        ),
    ),
    'talent.vigia.passo_do_cacador': (
        '+3% AGI',
        (
            'O Vigia se move como quem conhece o terreno antes de pisar nele, economizando '
            'movimentos e mantendo distância quando necessário.'
        ),
    ),
    'talent.vigia.olho_afiado': (
        '+2 p.p. CRIT',
        'Um instante de observação basta para encontrar uma falha que outros não percebem.',
    ),
    'talent.vigia.postura_vigilante': (
        '+2% DEF',
        (
            'Mesmo enquanto observa, o Vigia permanece pronto para o impacto. A atenção nunca '
            'significa descuido.'
        ),
    ),
    'talent.vigia.mira_estavel': (
        'Mira +1T',
        (
            'Uma vez encontrado o alvo, o Vigia mantém a leitura por mais tempo, esperando o '
            'momento em que o disparo será decisivo.'
        ),
    ),
    'talent.vigia.perfuracao_calculada': (
        '+2 p.p. PER',
        (
            'O Vigia não dispara contra a armadura; dispara contra o ponto onde ela deixa de '
            'proteger.'
        ),
    ),
    'talent.vigia.antecipacao': (
        'primeiro Dano Direto recebido −7%',
        (
            'A observação começa antes do confronto. O primeiro movimento hostil raramente '
            'surpreende quem já estava esperando por ele.'
        ),
    ),
    'talent.vigia.aquisicao_rapida': (
        'primeiro Dano Direto contra alvo sem Mira gera 1 Mira extra, 1×/alvo/combate',
        (
            'O primeiro contato com um alvo fornece ao Vigia uma quantidade incomum de '
            'informação. Um único disparo pode revelar mais do que parece.'
        ),
    ),
    'talent.vigia.alvo_exposto': (
        'com ≥2 Mira → +3% Dano Direto',
        (
            'Quanto mais o Vigia compreende um alvo, menos espaço resta para esconder seus pontos '
            'vulneráveis.'
        ),
    ),
    'talent.vigia.recuo_instintivo': (
        'primeira vez ≤40% HP → +8% DEF 1T',
        (
            'Quando o perigo alcança o Vigia, o corpo recua antes que a mente precise ordenar. A '
            'distância conquistada permite reorganizar a defesa.'
        ),
    ),
    'talent.vigia.visao_persistente': (
        'ao trocar de alvo, preserva 1 Mira no anterior por 1T',
        (
            'Uma observação não desaparece simplesmente porque o olhar mudou. O Vigia conserva '
            'parte da leitura enquanto procura uma nova ameaça.'
        ),
    ),
    'talent.vigia.ponto_fraco': (
        'com ≥3 Mira → +2 p.p. CRIT',
        (
            'Depois de observar o suficiente, o Vigia deixa de procurar uma abertura e passa a '
            'saber onde ela está.'
        ),
    ),
    'talent.vigia.couro_de_campo': (
        '−8% dano de DoT',
        (
            'A vida nas trilhas ensinou o Vigia a reconhecer e suportar os efeitos persistentes '
            'que o terreno e os inimigos deixam no corpo.'
        ),
    ),
    'talent.vigia.leitura_de_movimento': (
        'ao aplicar −AGI → +5% AGI 1T',
        (
            'Ao reduzir a mobilidade de um inimigo, o Vigia entende melhor o ritmo do confronto e '
            'usa essa leitura para se mover antes dele.'
        ),
    ),
    'talent.vigia.disparo_implacavel': (
        '+4% Dano Direto contra alvo ≤35% HP',
        (
            'Quando o alvo já está enfraquecido, o Vigia não desperdiça o momento. O disparo '
            'final nasce de toda a observação acumulada.'
        ),
    ),
    'talent.vigia.ultimo_horizonte': (
        'próprio HP ≤35% → +6% DEF',
        (
            'Mesmo cercado e ferido, o Vigia procura o espaço necessário para continuar de pé e '
            'manter a visão do campo.'
        ),
    ),
    'talent.vigia.cacada_metodica': (
        'ao atingir alvo em Mira máxima → próximo Dano Direto em 2T recebe +3 p.p. PER',
        (
            'Quando todas as pistas apontam para o mesmo ponto, o Vigia transforma observação em '
            'uma execução precisa.'
        ),
    ),
    'talent.tecelao.fio_potente': (
        '+1% ATQ',
        (
            'O Tecelão tensiona a Trama até que sua força se manifeste no momento certo, fazendo '
            'cada ação carregar mais intenção.'
        ),
    ),
    'talent.tecelao.trama_vital': (
        '+1% HP',
        (
            'O corpo encontra estabilidade ao permanecer ligado àquilo que o cerca. O Tecelão '
            'aprende a não deixar que a tensão o desfaça.'
        ),
    ),
    'talent.tecelao.passo_entre_fios': (
        '+3% AGI',
        (
            'Mover-se entre forças invisíveis exige precisão. O Tecelão atravessa os espaços da '
            'batalha sem romper a própria concentração.'
        ),
    ),
    'talent.tecelao.fenda_precisa': (
        '+2 p.p. CRIT',
        (
            'A Trama revela pequenas irregularidades no instante certo. O Tecelão transforma '
            'essas falhas em pontos de ruptura.'
        ),
    ),
    'talent.tecelao.veu_denso': (
        '+2% DEF',
        'Camadas de proteção se sobrepõem até formar uma defesa difícil de atravessar.',
    ),
    'talent.tecelao.trama_duradoura': (
        'janela de consumo 2 → 3T',
        (
            'Nem toda tensão precisa ser resolvida imediatamente. O Tecelão conserva uma trama '
            'preparada sem perder seu controle.'
        ),
    ),
    'talent.tecelao.fio_perfurante': (
        '+2 p.p. PER',
        (
            'Um fio bem colocado pode atravessar uma estrutura inteira. O Tecelão direciona sua '
            'força para o ponto exato de menor resistência.'
        ),
    ),
    'talent.tecelao.protecao_tecida': (
        'Barreiras recebidas +5%',
        (
            'Uma Barreira bem construída não é apenas uma camada. Ela se ajusta ao corpo e '
            'absorve melhor aquilo que tenta atravessá-la.'
        ),
    ),
    'talent.tecelao.alternancia_fluida': (
        'consumir Trama → +5% AGI 1T',
        (
            'Trocar tensão por movimento se torna natural. O Tecelão deixa uma ação alimentar '
            'imediatamente a próxima.'
        ),
    ),
    'talent.tecelao.trama_agressiva': (
        'Trama consumida por dano → +2 p.p. potência',
        (
            'Quando a Trama é convertida em força ofensiva, o Tecelão extrai dela uma intensidade '
            'maior sem perder o controle.'
        ),
    ),
    'talent.tecelao.reforco_do_veu': (
        'enquanto Barreira → +5% DEF',
        (
            'A presença de uma proteção permite ao Tecelão trabalhar com mais segurança, '
            'reforçando a estrutura enquanto ela permanece intacta.'
        ),
    ),
    'talent.tecelao.fio_persistente': (
        'primeira Trama que expira sem uso renova 1T',
        (
            'Uma tensão que parecia perdida pode ser recuperada. O Tecelão agarra o último '
            'instante antes que o fio desapareça.'
        ),
    ),
    'talent.tecelao.ruptura_profunda': (
        'Dano Direto contra alvo com DoT +3%',
        'Quando uma ferida continua aberta, a Trama encontra mais caminhos para aprofundá-la.',
    ),
    'talent.tecelao.tecelagem_defensiva': (
        'primeira Barreira própria no combate +10%',
        (
            'A primeira grande proteção estabelece o padrão para o restante do confronto. O '
            'Tecelão prepara a estrutura antes que a pressão aumente.'
        ),
    ),
    'talent.tecelao.eco_de_alternancia': (
        'consumir Trama com Arte diferente → próxima ofensiva em 2T recebe +3 p.p. PER',
        (
            'A mudança entre técnicas deixa um eco na Trama. O Tecelão aproveita essa transição '
            'para tornar a próxima ofensiva mais precisa.'
        ),
    ),
    'talent.tecelao.sobrecarga_controlada': (
        '+4% potência quando dano consome Trama contra alvo ≤40% HP',
        (
            'Quando o inimigo já está próximo do limite, o Tecelão concentra a tensão restante em '
            'uma descarga cuidadosamente controlada.'
        ),
    ),
    'talent.tecelao.veu_de_emergencia': (
        'primeira vez ≤30% HP → Barreira 6% HP 1T',
        'Quando toda margem desaparece, a Trama responde antes que o corpo seja vencido.',
    ),
    'talent.tecelao.trama_precisa': (
        'ofensiva consumida +2 p.p. CRIT; Cura/Barreira consumida +2% potência',
        (
            'O Tecelão reconhece o destino de cada fio e ajusta sua tensão conforme aquilo que '
            'precisa ser realizado.'
        ),
    ),
    'talent.oraculo.visao_cruel': (
        '+1% ATQ',
        (
            'O Oráculo aprende a enxergar não apenas aquilo que está diante dos olhos, mas o '
            'instante em que uma possibilidade se torna inevitável.'
        ),
    ),
    'talent.oraculo.pressentimento_vital': (
        '+1% HP',
        (
            'Há momentos em que o corpo recua antes do perigo chegar. O Oráculo aprende a confiar '
            'nesse aviso silencioso.'
        ),
    ),
    'talent.oraculo.passos_do_destino': (
        '+3% AGI',
        (
            'O Oráculo parece se mover um instante antes da decisão acontecer, como se já tivesse '
            'percebido o caminho que o combate tomaria.'
        ),
    ),
    'talent.oraculo.pressagio_cortante': (
        'ofensiva que consome Presságio +2 p.p. PER',
        (
            'Um sinal corretamente interpretado pode transformar uma previsão em um golpe '
            'inevitável.'
        ),
    ),
    'talent.oraculo.veu_cauteloso': (
        '+2% DEF',
        (
            'O Oráculo envolve o próprio corpo com uma cautela que nasce daquilo que ainda não '
            'aconteceu.'
        ),
    ),
    'talent.oraculo.sinal_persistente': (
        'Presságio +1T',
        (
            'Nem todo presságio desaparece quando o momento passa. Alguns sinais permanecem tempo '
            'suficiente para revelar seu verdadeiro significado.'
        ),
    ),
    'talent.oraculo.destino_exposto': (
        '+2 p.p. CRIT',
        (
            'Quando o caminho provável de um inimigo se torna claro, o Oráculo sabe exatamente '
            'onde intervir.'
        ),
    ),
    'talent.oraculo.antevisao_defensiva': (
        'enquanto Barreira → +5% DEF',
        'Uma proteção ganha força quando o Oráculo já conhece o perigo que está por vir.',
    ),
    'talent.oraculo.leitura_dos_sinais': (
        'ao aplicar Presságio em inimigo → +5% AGI 1T',
        (
            'Cada sinal deixado no inimigo fornece ao Oráculo uma nova leitura do campo de '
            'batalha.'
        ),
    ),
    'talent.oraculo.profecia_dolorosa': (
        'ofensiva que consome Presságio +2% potência',
        (
            'Alguns futuros são difíceis de evitar. Quando o Oráculo decide revelá-los através de '
            'um ataque, a previsão ganha peso sobre o alvo.'
        ),
    ),
    'talent.oraculo.destino_adiado': (
        'primeiro Dano Direto recebido −7%',
        (
            'Nem todo acontecimento precisa acontecer quando parece inevitável. O Oráculo '
            'encontra um instante para adiar aquilo que deveria atingi-lo.'
        ),
    ),
    'talent.oraculo.pressagio_flexivel': (
        'primeiro Presságio que expira sem uso renova 1T',
        (
            'Um sinal perdido pode voltar a aparecer. O Oráculo aprende que uma previsão ignorada '
            'nem sempre deixa de ter importância.'
        ),
    ),
    'talent.oraculo.fraqueza_prevista': (
        '+3% Dano Direto contra alvo com Debuff',
        (
            'Quando um inimigo já carrega sinais de sua própria ruína, o Oráculo reconhece a '
            'fraqueza antes que ela se manifeste completamente.'
        ),
    ),
    'talent.oraculo.mente_velada': (
        'magnitude de Debuff numérico removível recebido −6%',
        (
            'Nem toda influência consegue alcançar uma mente que aprendeu a desconfiar até das '
            'próprias certezas.'
        ),
    ),
    'talent.oraculo.sequencia_profetica': (
        'consumir Presságio → +3% AGI 1T',
        (
            'Uma previsão conduz naturalmente à próxima. O Oráculo se move entre esses sinais '
            'como quem segue uma sequência já conhecida.'
        ),
    ),
    'talent.oraculo.fim_anunciado': (
        '+4% Dano Direto contra alvo ≤35% HP',
        (
            'Quando o fim já pode ser percebido, o Oráculo não precisa esperar que ele aconteça. '
            'Basta reconhecer o momento.'
        ),
    ),
    'talent.oraculo.ultima_visao': (
        'primeira vez ≤30% HP → Barreira 6% HP 1T',
        (
            'No limite, uma última possibilidade se revela. O Oráculo a transforma em proteção '
            'antes que o destino se feche.'
        ),
    ),
    'talent.oraculo.sinais_convergentes': (
        'defensivo consumido +3% potência; ofensivo consumido +2 p.p. CRIT',
        (
            'Quando vários sinais apontam para o mesmo resultado, o Oráculo deixa de interpretar '
            'possibilidades isoladas e age sobre a convergência.'
        ),
    ),
    'talent.luminar.luz_incisiva': (
        '+1% ATQ',
        (
            'A luz do Luminar não serve apenas para iluminar. Ela revela o ponto em que um golpe '
            'pode atravessar a escuridão.'
        ),
    ),
    'talent.luminar.vitalidade_solar': (
        '+1% HP',
        (
            'O Luminar preserva a própria força como uma brasa que precisa continuar acesa mesmo '
            'em meio à adversidade.'
        ),
    ),
    'talent.luminar.clarao_agil': (
        '+3% AGI',
        (
            'Um movimento rápido pode mudar a posição de toda uma luta. O Luminar responde antes '
            'que a oportunidade desapareça.'
        ),
    ),
    'talent.luminar.julgamento_preciso': (
        'ofensiva fortalecida por Julgamento +2 p.p. CRIT',
        (
            'Quando o julgamento já foi pronunciado, o Luminar transforma a sentença em um golpe '
            'que encontra seu destino.'
        ),
    ),
    'talent.luminar.corpo_consagrado': (
        '+2% DEF',
        (
            'A disciplina do Luminar transforma o próprio corpo em um ponto de estabilidade '
            'diante do caos.'
        ),
    ),
    'talent.luminar.contraluz_persistente': (
        'Fulgor/Julgamento +1T',
        (
            'Uma manifestação de luz não precisa desaparecer imediatamente. O Luminar a mantém '
            'presente enquanto ainda houver propósito.'
        ),
    ),
    'talent.luminar.luz_perfurante': (
        '+2 p.p. PER',
        'A luz encontra frestas onde os olhos comuns só veem uma superfície fechada.',
    ),
    'talent.luminar.egide_densa': (
        'Barreiras aplicadas +4%',
        (
            'Uma proteção sustentada pelo Luminar ganha consistência e permanece firme mesmo sob '
            'pressão.'
        ),
    ),
    'talent.luminar.alternancia_radiante': (
        'consumir Fulgor/Julgamento → +4% AGI 1T',
        (
            'A passagem entre ataque e proteção torna-se fluida. Cada manifestação de luz deixa o '
            'corpo preparado para a próxima.'
        ),
    ),
    'talent.luminar.veredito_ardente': (
        'Dano Direto fortalecido por Julgamento +2% potência',
        (
            'Quando a decisão já foi tomada, o Luminar concentra sua força no instante em que o '
            'julgamento deixa de ser palavra e se torna consequência.'
        ),
    ),
    'talent.luminar.cura_prudente': (
        'Cura em alvo ≤40% HP +5%',
        (
            'O Luminar reconhece quando uma vida precisa de cuidado imediato, direcionando sua '
            'força para quem está mais próximo do limite.'
        ),
    ),
    'talent.luminar.ciclo_luminoso': (
        'primeiro Fulgor/Julgamento que expira sem uso renova 1T',
        (
            'A luz pode desaparecer sem realmente se perder. O Luminar recupera uma manifestação '
            'antes que seu ciclo termine.'
        ),
    ),
    'talent.luminar.punicao_da_fraqueza': (
        '+3% Dano Direto contra alvo com Cura reduzida',
        (
            'Quando a recuperação de um inimigo já foi comprometida, o Luminar reconhece a '
            'oportunidade de encerrar aquilo que permanece de pé.'
        ),
    ),
    'talent.luminar.luz_protetora': (
        'enquanto Barreira → +5% DEF',
        (
            'A presença de uma proteção reforça a postura do Luminar, permitindo que permaneça '
            'firme enquanto a luz ainda o envolve.'
        ),
    ),
    'talent.luminar.fluxo_restaurador': (
        'Cura efetiva consumindo Fulgor → alvo +4% DEF 1T',
        (
            'Uma cura bem direcionada não termina quando a ferida fecha. Ela deixa no corpo '
            'restaurado a força necessária para resistir ao próximo impacto.'
        ),
    ),
    'talent.luminar.sentenca_solar': (
        '+4% Dano Direto contra alvo ≤35% HP',
        (
            'Quando o combate chega ao último instante, o Luminar concentra toda a certeza de sua '
            'luz em uma sentença final.'
        ),
    ),
    'talent.luminar.ultimo_alvorecer': (
        'primeira vez ≤30% HP → Cura 5% HP, sem Crit/triggers/bônus',
        (
            'Quando a escuridão parece próxima demais, resta uma última reserva. O Luminar '
            'encontra força para permanecer de pé sem transformar o momento em espetáculo.'
        ),
    ),
    'talent.luminar.contraluz_perfeita': (
        'Fulgor em Cura/Barreira +2% potência; Julgamento em Dano Direto +2 p.p. PER',
        (
            'O Luminar distingue o destino de cada manifestação. A mesma luz pode restaurar ou '
            'punir, desde que sua intenção esteja perfeitamente definida.'
        ),
    ),
}

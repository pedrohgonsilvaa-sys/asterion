# O Despertar dos Flagelos — medição de balanceamento (V1)

Gerado por `tests/flagelo_balance.py` (determinístico; nenhum valor foi alterado).
Piso, não previsão: Sentinela no nível do Flagelo, sem equipamento, Talentos nem Artes,
só Atacar; morto volta em 2 min com vida cheia. Sem Artes de cura/Barreira e sem Defender
(exceto onde dito). O Flagelo começa cheio em cada escalonamento medido.

## Perfil do participante (motor real)

| Flagelo | Nv. | HP jogador | DEF | Esquiva | Ataque (média) | Ataque c/ ATQ −10% |
|---|---:|---:|---:|---:|---:|---:|
| Varkhenn | 10 | 880 | 102 | 0.0 | 71 | 64 |
| Nharvek | 20 | 1113 | 129 | 0.0 | 96 | 83 |
| Azharel | 30 | 1409 | 162 | 0.0 | 116 | 103 |
| Hemrath | 40 | 1781 | 206 | 0.0 | 149 | 133 |
| Korvann | 50 | 2253 | 260 | 0.0 | 157 | 141 |
| Vaelith | 60 | 2850 | 329 | 0.0 | 215 | 186 |

## 1. TTK (minutos, sem escalonamento)

| N | Varkhenn | Nharvek | Azharel | Hemrath | Korvann | Vaelith |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 51.5 | 54.2 | 40.3 | 45.5 | 50.3 | 45.0 |
| 5 | 25.7 | 26.7 | 20.5 | 20.2 | 27.5 | 22.2 |
| 6 | 20.0 | 21.0 | 16.8 | 16.2 | 22.0 | 18.3 |
| 9 | 11.5 | 12.0 | 10.5 | 9.2 | 13.7 | 11.5 |
| 12 | 9.0 | 9.3 | 6.7 | 7.0 | 10.0 | 7.2 |
| 20 | 4.2 | 4.5 | 3.8 | 4.2 | 5.3 | 4.3 |
| 30 | 2.8 | 3.0 | 2.7 | 2.8 | 3.5 | 2.8 |
| 50 | 1.7 | 1.8 | 1.7 | 1.7 | 2.2 | 1.8 |

## 2. Diferença relativa de TTK (÷ mediana dos seis)

| N | Varkhenn | Nharvek | Azharel | Hemrath | Korvann | Vaelith | máx ÷ mín |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 1.07 | 1.13 | 0.84 | 0.95 | 1.05 | 0.94 | 1.34 |
| 5 | 1.07 | 1.11 | 0.86 | 0.84 | 1.15 | 0.93 | 1.36 |
| 6 | 1.04 | 1.10 | 0.88 | 0.84 | 1.15 | 0.96 | 1.36 |
| 9 | 1.00 | 1.04 | 0.91 | 0.80 | 1.19 | 1.00 | 1.49 |
| 12 | 1.11 | 1.15 | 0.82 | 0.87 | 1.24 | 0.89 | 1.50 |
| 20 | 0.98 | 1.06 | 0.90 | 0.98 | 1.25 | 1.02 | 1.39 |
| 30 | 1.00 | 1.06 | 0.94 | 1.00 | 1.24 | 1.00 | 1.31 |
| 50 | 0.95 | 1.05 | 0.95 | 0.95 | 1.24 | 1.05 | 1.30 |

## 3. Dano recebido por participante (% do HP máximo por rodada presente) e mortes

| N | Varkhenn | Nharvek | Azharel | Hemrath | Korvann | Vaelith |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 7.1% / 35☠ | 7.2% / 37☠ | 5.3% / 23☠ | 6.5% / 30☠ | 4.0% / 24☠ | 5.0% / 24☠ |
| 5 | 4.7% / 22☠ | 4.6% / 23☠ | 3.6% / 14☠ | 3.0% / 12☠ | 2.9% / 17☠ | 3.1% / 14☠ |
| 6 | 4.1% / 19☠ | 4.0% / 20☠ | 3.0% / 12☠ | 2.4% / 8☠ | 2.7% / 14☠ | 2.8% / 13☠ |
| 9 | 3.3% / 11☠ | 2.9% / 10☠ | 2.5% / 9☠ | 1.4% / 2☠ | 2.2% / 9☠ | 2.2% / 9☠ |
| 12 | 3.0% / 12☠ | 2.7% / 12☠ | 2.1% / 3☠ | 1.0% / 0☠ | 2.0% / 10☠ | 1.8% / 1☠ |
| 20 | 2.6% / 0☠ | 2.1% / 1☠ | 1.9% / 0☠ | 0.6% / 0☠ | 1.7% / 0☠ | 1.6% / 0☠ |
| 30 | 2.2% / 0☠ | 1.8% / 0☠ | 1.6% / 0☠ | 0.4% / 0☠ | 1.6% / 0☠ | 1.4% / 0☠ |
| 50 | 2.2% / 0☠ | 1.8% / 0☠ | 1.5% / 0☠ | 0.2% / 0☠ | 1.8% / 0☠ | 1.3% / 0☠ |

## 4. Ações isoladas contra 10 participantes de vida cheia

| Flagelo | Ação | Tipo | Alvos | Dano por alvo (% HP) | Dano do grupo | Efeitos / DoT |
|---|---|---|---:|---:|---:|---|
| Varkhenn | Golpe de Cinza | Golpe | 1 | 9.3% | 82 | — |
| Varkhenn | Sopro de Fuligem | AoE | 10 | 7.4% | 650 | burn |
| Varkhenn | Cinza no Pulso | Golpe + debuff | 1 | 8.3% | 73 | attack |
| Varkhenn | Peso do Entulho | Golpe | 1 | 12.0% | 106 | — |
| Varkhenn | Última Fagulha | Preparada | 1 | 16.7% | 147 | — |
| Nharvek | Golpe do Laço | Golpe | 1 | 10.6% | 118 | — |
| Nharvek | Tranco das Raízes | Golpe + debuff | 1 | 9.5% | 106 | agility |
| Nharvek | Nó de Peso | Golpe + debuff | 1 | 12.8% | 142 | defense |
| Nharvek | Tensão Compartilhada | AoE | 10 | 8.4% | 940 | — |
| Nharvek | Estrangulamento Final | Preparada | 1 | 19.1% | 213 | — |
| Azharel | Golpe de Referência | Golpe | 1 | 8.5% | 120 | — |
| Azharel | Correção de Linha | Golpe + debuff | 1 | 7.7% | 108 | defense |
| Azharel | Medida Contrária | Golpe | 1 | 10.6% | 150 | — |
| Azharel | Meridiano Divergente | AoE | 10 | 6.8% | 960 | agility |
| Azharel | Linha Absoluta | Preparada | 1 | 15.3% | 216 | — |
| Hemrath | Golpe de Salmoura | Golpe | 1 | 10.6% | 189 | — |
| Hemrath | Pressão de Válvula | Golpe + debuff | 1 | 9.5% | 170 | defense |
| Hemrath | Soro Corrosivo | Golpe | 1 | 9.0% | 161 | poison |
| Hemrath | Restituição Rubra | Cura própria | 0 | 0.0% | 0 | — |
| Hemrath | Sobrecarga de Matriz | Preparada | 1 | 19.1% | 341 | — |
| Korvann | Golpe de Contrapeso | Golpe | 1 | 7.9% | 177 | — |
| Korvann | Carga Distribuída | Golpe + debuff | 1 | 7.1% | 160 | defense |
| Korvann | Escora Inversa | Buff próprio | 0 | 0.0% | 0 | — |
| Korvann | Ruptura de Cabo | AoE | 10 | 6.7% | 1510 | — |
| Korvann | Queda do Contrapeso | Preparada | 1 | 14.2% | 320 | — |
| Vaelith | Golpe Desalinhado | Golpe | 1 | 7.7% | 220 | — |
| Vaelith | Duas Leituras | Golpe + debuff | 1 | 6.9% | 198 | attack |
| Vaelith | Reflexo Partido | Golpe | 1 | 9.6% | 275 | — |
| Vaelith | Fratura Local | AoE | 10 | 6.2% | 1760 | — |
| Vaelith | Protocolo Incompatível | Preparada | 1 | 13.9% | 396 | — |

## 5. Peso de cada família de ações (N = 10, 0 passos)

| Flagelo | Variação | TTK (min) | Δ TTK | Dano recebido total | Mortes |
|---|---|---:|---:|---:|---:|
| Varkhenn | base | 10.3 | — | 13912 | 10 |
| Varkhenn | sem AoE | 8.3 | -19.4% | 4975 | 0 |
| Varkhenn | sem Preparada | 12.3 | +19.4% | 18740 | 21 |
| Varkhenn | sem debuffs/DoT | 10.2 | -1.6% | 11135 | 10 |
| Nharvek | base | 11.0 | — | 17176 | 10 |
| Nharvek | sem AoE | 9.0 | -18.2% | 7564 | 1 |
| Nharvek | sem Preparada | 11.2 | +1.5% | 20853 | 15 |
| Nharvek | sem debuffs/DoT | 11.0 | +0.0% | 17160 | 10 |
| Azharel | base | 9.3 | — | 15164 | 10 |
| Azharel | sem AoE | 7.7 | -17.9% | 6530 | 1 |
| Azharel | sem Preparada | 9.7 | +3.6% | 16478 | 10 |
| Azharel | sem debuffs/DoT | 9.3 | +0.0% | 15164 | 10 |
| Hemrath | base | 8.3 | — | 10621 | 2 |
| Hemrath | sem AoE | 8.3 | +0.0% | 10621 | 2 |
| Hemrath | sem Preparada | 8.3 | +0.0% | 9298 | 1 |
| Hemrath | sem debuffs/DoT | 8.3 | +0.0% | 9643 | 1 |
| Hemrath | sem cura própria | 7.3 | -12.0% | 9993 | 1 |
| Korvann | base | 12.5 | — | 30230 | 10 |
| Korvann | sem AoE | 10.5 | -16.0% | 10660 | 0 |
| Korvann | sem Preparada | 12.5 | +0.0% | 28373 | 10 |
| Korvann | sem debuffs/DoT | 12.5 | +0.0% | 30208 | 10 |
| Vaelith | base | 9.8 | — | 29853 | 10 |
| Vaelith | sem AoE | 8.5 | -13.6% | 13651 | 0 |
| Vaelith | sem Preparada | 10.5 | +6.8% | 38554 | 10 |
| Vaelith | sem debuffs/DoT | 9.7 | -1.7% | 29059 | 8 |

### Participação de cada ação no dano recebido (N = 10)

| Flagelo | Ação | Usos | Dano recebido | % do total | Esquivados |
|---|---|---:|---:|---:|---:|
| Varkhenn | Sopro de Fuligem | 12 | 6317 | 45.4% | 0 |
| Varkhenn | Última Fagulha | 13 | 3225 | 23.2% | 0 |
| Varkhenn | Peso do Entulho | 18 | 2311 | 16.6% | 0 |
| Varkhenn | Cinza no Pulso | 19 | 2059 | 14.8% | 0 |
| Nharvek | Tensão Compartilhada | 13 | 10129 | 59.0% | 0 |
| Nharvek | Nó de Peso | 19 | 2526 | 14.7% | 0 |
| Nharvek | Estrangulamento Final | 14 | 2396 | 13.9% | 0 |
| Nharvek | Tranco das Raízes | 20 | 2125 | 12.4% | 0 |
| Azharel | Meridiano Divergente | 11 | 8955 | 59.1% | 0 |
| Azharel | Linha Absoluta | 12 | 2295 | 15.1% | 0 |
| Azharel | Medida Contrária | 11 | 1480 | 9.8% | 0 |
| Azharel | Golpe de Referência | 11 | 1320 | 8.7% | 0 |
| Azharel | Correção de Linha | 11 | 1114 | 7.3% | 0 |
| Hemrath | Sobrecarga de Matriz | 10 | 3676 | 34.6% | 0 |
| Hemrath | Pressão de Válvula | 14 | 2551 | 24.0% | 0 |
| Hemrath | Soro Corrosivo | 13 | 2179 | 20.5% | 0 |
| Hemrath | Golpe de Salmoura | 10 | 2159 | 20.3% | 0 |
| Hemrath | Restituição Rubra | 3 | 56 | 0.5% | 0 |
| Korvann | Ruptura de Cabo | 15 | 20660 | 68.3% | 0 |
| Korvann | Queda do Contrapeso | 15 | 4575 | 15.1% | 0 |
| Korvann | Golpe de Contrapeso | 15 | 2612 | 8.6% | 0 |
| Korvann | Carga Distribuída | 15 | 2383 | 7.9% | 0 |
| Korvann | Escora Inversa | 15 | 0 | 0.0% | 0 |
| Vaelith | Fratura Local | 12 | 17419 | 58.3% | 0 |
| Vaelith | Protocolo Incompatível | 12 | 4752 | 15.9% | 0 |
| Vaelith | Reflexo Partido | 17 | 4172 | 14.0% | 0 |
| Vaelith | Duas Leituras | 18 | 3510 | 11.8% | 0 |

### Debuffs de atributo (−10%, 2 turnos), efeito direto medido

| Flagelo | Dano do jogador com ATQ −10% | Dano recebido no golpe básico com DEF −10% |
|---|---:|---:|
| Varkhenn | -9.9% | +3.7% |
| Nharvek | -13.5% | +4.2% |
| Azharel | -11.2% | +4.2% |
| Hemrath | -10.7% | +4.2% |
| Korvann | -10.2% | +4.5% |
| Vaelith | -13.5% | +4.5% |

### Preparada: golpe isolado, sem e com Defender

| Flagelo | Preparada | Dano (% HP) | Com Defender | Prevenido | Mortes por golpe |
|---|---|---:|---:|---:|---|
| Varkhenn | Última Fagulha | 16.7% | 9.2% | 45% | não (precisa de ≥ 6 golpes seguidos) |
| Nharvek | Estrangulamento Final | 19.1% | 10.5% | 45% | não (precisa de ≥ 6 golpes seguidos) |
| Azharel | Linha Absoluta | 15.3% | 8.4% | 45% | não (precisa de ≥ 7 golpes seguidos) |
| Hemrath | Sobrecarga de Matriz | 19.1% | 10.5% | 45% | não (precisa de ≥ 6 golpes seguidos) |
| Korvann | Queda do Contrapeso | 14.2% | 7.8% | 45% | não (precisa de ≥ 8 golpes seguidos) |
| Vaelith | Protocolo Incompatível | 13.9% | 7.6% | 45% | não (precisa de ≥ 8 golpes seguidos) |

### Restituição Rubra (Hemrath, N = 10)

- usos: 3 (máximo 3); curado no total: 9368 de 63880 HP.

## 6. Escalonamento por abandono (N = 10)

| Flagelo | 0 passos | 5 passos | 10 passos | Δ 10 passos |
|---|---:|---:|---:|---:|
| Varkhenn | 10.3 min · 10☠ | 15.7 min · 21☠ | 21.7 min · 36☠ | +109.7% |
| Nharvek | 11.0 min · 10☠ | 16.7 min · 22☠ | 22.8 min · 35☠ | +107.6% |
| Azharel | 9.3 min · 10☠ | 13.0 min · 12☠ | 17.8 min · 20☠ | +91.1% |
| Hemrath | 8.3 min · 2☠ | 12.5 min · 7☠ | 16.8 min · 12☠ | +102.0% |
| Korvann | 12.5 min · 10☠ | 18.7 min · 20☠ | 24.7 min · 30☠ | +97.3% |
| Vaelith | 9.8 min · 10☠ | 14.3 min · 14☠ | 19.7 min · 22☠ | +100.0% |

## Outliers detectados

Limiar: TTK fora de 0.67–1.50× a mediana dos seis Flagelos.

- nenhum

## Pontos de atenção (dados, não decisões)

- Nharvek: a AoE causa 58% do dano recebido (N = 10); sem ela as mortes caem de 10 para 1.
- Azharel: a AoE causa 59% do dano recebido (N = 10); sem ela as mortes caem de 10 para 1.
- Korvann: a AoE causa 68% do dano recebido (N = 10); sem ela as mortes caem de 10 para 0.
- Vaelith: a AoE causa 58% do dano recebido (N = 10); sem ela as mortes caem de 10 para 0.
- Varkhenn: com 3 participantes ocorrem 35 derrotas até a morte (51.5 min).
- Nharvek: com 3 participantes ocorrem 37 derrotas até a morte (54.2 min).
- Azharel: com 3 participantes ocorrem 23 derrotas até a morte (40.3 min).
- Hemrath: com 3 participantes ocorrem 30 derrotas até a morte (45.5 min).
- Korvann: com 3 participantes ocorrem 24 derrotas até a morte (50.3 min).
- Vaelith: com 3 participantes ocorrem 24 derrotas até a morte (45.0 min).
- Varkhenn: com 5 participantes ocorrem 22 derrotas até a morte (25.7 min).
- Nharvek: com 5 participantes ocorrem 23 derrotas até a morte (26.7 min).

Esquiva global: o Sentinela sem equipamento tem Esquiva 0, então a esquiva do Flagelo
não é exercida nesta medição (a Esquiva real depende de equipamento e Talentos).

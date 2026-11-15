# Textos de UI do hub (bloco A) - TdO v1.0.18

Revisão de textos escritos sem fonte. Referência de tom: seção 66 do UI v1.6.1 (66.1 e 66.2). Nenhum número ou regra alterado. `src/` não foi tocado: o programador aplica as trocas marcadas "mudar".

| # | Texto atual | Texto final | Arquivo:linha | Decisão e justificativa |
|---|---|---|---|---|
| 1 | Explorar só está disponível no Refúgio do Ocaso. | Explorar só está disponível no Refúgio do Ocaso. | `src/asterion/bot/tdo_hub_ui.py:139` | Manter. Curto, direto, sem jargão. |
| 2 | Termine a atividade em andamento antes de explorar. | Termine o que está fazendo antes de explorar. | `src/asterion/bot/tdo_hub_ui.py:140` | Mudar. "Atividade em andamento" soa a sistema; versão mais seca e natural. |
| 3 | Escolha o Local da caçada. | Escolha onde caçar. | `src/asterion/bot/tdo_hub_ui.py:101` | Mudar. Mais curto; evita "Local da caçada" repetido com o título "Caçar". |
| 4 | Revela um Local | Revela um Local | `src/asterion/bot/tdo_hub_ui.py:68` | Manter. A seção 66.2 diz que Explorar revela um Local; sem spoiler. |
| 5 | Locais descobertos | Locais descobertos | `src/asterion/bot/tdo_hub_ui.py:75` | Manter. É o termo exato de 66.1 item 2. |
| 6a | Local revelado (ícone + nome) | igual | `src/asterion/bot/tdo_hub_ui.py:123` | Manter. 66.2 pede "o Local revelado". |
| 6b | XP de descoberta · {xp} | XP de descoberta · {xp} | `src/asterion/bot/tdo_hub_ui.py:126` | Manter. Termo de 66.2; número vem do resultado. |
| 6c | {Local} agora aparece no Refúgio. | {Local} agora aparece no Refúgio. | `src/asterion/bot/tdo_hub_ui.py:127` | Manter. Reproduz 66.2 ("agora aparece no Refúgio"). |

## Já com fonte (não mexer)

- `Não há mais o que explorar por aqui.` (`tdo_hub_ui.py:27`), `Aguarde um instante.` (`tdo_hub_ui.py:28`): 66.2.
- Texto de descoberta da Câmara (`tdo_hub.py:44`): vem da Fonte Regional §3.6; a UI não altera. Não conferi o texto literal contra §3.6 nesta revisão.

## Perguntas ao autor

- Nenhuma lacuna de lore. Resultado de Explorar para Charneca, Bosque e Ruínas usa o mesmo modelo, sem texto de ambientação próprio; só a Câmara tem texto de §3.6. Se o autor quiser uma frase de ambientação por Local, ela precisa ser escrita por ele.
- `explore_remaining` / `Explore para encontrar este lugar.` (66.2, Missão aguardando Local): não achei uso no bloco A; confirmar que entra em bloco posterior.

# A Ruptura do Véu — decisões técnicas (lacunas da v1.3.0)

Fonte: especificação final v1.3.0. Onde ela não define a regra, vale o comportamento existente
mais próximo do repositório. Nada abaixo muda número canônico. Janela de decisão: 10 s para
todas as lutas (decisão autoral posterior à v1.3.0; a spec cita 20 s).

- Início: no horário da agenda (§3.3, sem lobby parado). Fim: prazo de 60 min marca FRACASSADO;
  CONCLUIDO/FRACASSADO são acertados e viram ENCERRADO no mesmo ciclo do scheduler.
- Snapshot de N da Fase I: congela na primeira entrada em um Núcleo (quando a participação
  começa), contando quem já entrou no Evento; Fases II e III congelam ao avançar (§12.2).
- Núcleo RESOLVIDA: todas as criaturas derrotadas; em D e E basta a principal. RESOLVENDO volta a
  ATIVA se o objetivo não foi concluído. COLAPSADA não é usada (§61).
- Núcleo remanescente ao avançar de fase: fica como está.
- Arquétipos sem perfil de motor: Resistente→armored, Técnico→controller, Suporte e
  Equilibrado/Controlador→balanced. Barreira dos kits: 2 turnos (como `creature_kits`).
- IA: ação válida escolhida por semente determinística; prioridade explícita só onde a fonte
  fixa (Tecelão: Trama Óssea com 3+ participantes). "Maior contribuição recente" não tem janela
  definida: o alvo segue a semente. Fronteira de 70% do VEU-18 não tem comportamento (só há
  nomes de forma, sem regra).
- Efeitos dos kits: só os explícitos (ATQ/DEF/AGI/PER −10% por 2T), no tipo `combat.Effect`;
  o impacto vem de `Fighter.stat`. Efeito novo vale a partir da rodada seguinte e dura os
  turnos do kit.
- Suporte direto: medido pelo motor em instância de grupo (apoiador + até 3 aliados);
  cura/Barreira/proteção aplicadas em lote. Conta como Ação Significativa: cura efetiva,
  Barreira efetivamente absorvida e proteção que reduziu dano real.
- Ações contextuais: a fonte só dá exemplos e não liga nenhuma Núcleo a elas; nenhuma foi criada.
- Bestiário: `bestiary.veu.NN_*` no `BestiaryRecorder`, grupo "Bestiário do Véu" separado das
  Regiões; primeira observação quando a criatura participa com ação válida.

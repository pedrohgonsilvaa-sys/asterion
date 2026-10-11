# ASTERION — Cooperação e PvPvE · Roadmap técnico v2

**Estado:** plano técnico aprovado, subordinado à Fonte Mestra v1.6.0 e à especificação `MMO_PVPVE_FINAL_SPEC_V1.md`.

## Sequência de entrega

1. **Grupo persistente:** entidade social até quatro, convites de 10 minutos, liderança social, sair/kick, offline/reconnect, roster subset por atividade, Convite/Confirmação de Entrada e versionamento stale-safe.
2. **Motor de Campanha cooperativa:** jornada/referência separada do Grupo e do Host técnico; elegibilidade por personagem; evidência compartilhável e escrita individual idempotente; rewards individuais; escolhas pessoais; P1 como piloto.
3. **Chefes e Ajudantes:** snapshots individuais, Configuração de Combate congelada, scaling aprovado apenas para Chefe de Campanha, reconnect, morte/abandono sem rebalanceamento dinâmico, progresso/reward por personagem. Integrar P5/P6 e S6 preservando conteúdos regionais.
4. **Caçada em Grupo e PvPvE:** roster subset do Grupo, Confirmação de Entrada, pareamento de lados iguais, PvP separado da presa, Domínio do Rastro, lock simétrico de 30 minutos por par de contas e settlement PvE normal sem supressão.
5. **Ronda × PvPvE:** resolver pareamento na fronteira segura antes da próxima presa; takeover na próxima oportunidade; vitória continua à presa; derrota encerra lote; settlements anteriores permanecem.
6. **QA TDO:** jornada Solo e cooperativa, retorno como Ajudante, Vigor, Caçadas, Ronda, PvPvE, Masmorras, reconnect, multidispositivo, Bestiário/Códice, loot e idempotência.
7. **Vales:** P7–P12/S7–S12 pela mesma arquitetura; conteúdo numérico ausente permanece bloqueado sem invenção.
8. **Crônicas:** após Vales funcionalmente estabelecidos, construir scheduler/objetivos/voto/Trilha e validação de spoilers. Crônica I canônica permanece Dia 1; relógio acelerado somente em teste.

## Limites de arquitetura

- Grupo social, roster de atividade, Referência da Jornada e Host técnico são identidades distintas.
- Nenhum membro ganha acesso além de seus gates pessoais. Poder de veterano permanece real, sem sincronização.
- Campanha Solo precisa ser concluível por toda build legal; incluir teste/telemetria de baixo dano e suporte.
- S12 pode receber infraestrutura estrutural, mas o combate exige kit numérico autoritativo.
- Cada PR funcional deve manter `main` implantável, migration linear e verificações de banco fresco/upgrade.

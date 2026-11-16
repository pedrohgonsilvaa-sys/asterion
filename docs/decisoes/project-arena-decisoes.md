---
name: project-arena-decisoes
description: "Decisões da Arena e do Duelo (GDD §14) que a fonte não define, delegadas pelo autor em 2026-11-08"
metadata:
  node_type: memory
  type: project
  originSessionId: 197c4bc8-689d-45e0-84a2-109737e5345a
  modified: 2026-11-08T19:44:07.654Z
---

Lacunas da §14/§49.14, decididas por Claude com delegação do autor ("decida o que achar melhor") em 2026-11-08:

1. Duelo: desafio pelo nome do personagem; convite vale 45s.
2. Duelo usa as regras da Arena: HP cheio e estado limpo, turno 90s, AFK, rendição na Rodada 5; o HP do mundo é restaurado ao fim.
3. Revanche recente = 10 min (emprestado do PvPvE §52): só repete oponente se não houver outro compatível.
4. Jogador colocado contra oponente em colocação: Rop = valor da tabela de placement para as vitórias atuais do oponente.
5. Timeout único de turno: perde só aquele turno.
6. Crônica não existe no código: soft reset fica como função testada e sem gatilho; recompensas de Elo e Salão da Vigília ficam para quando a Crônica existir.
7. "{Flavor curto}" da tela de resultado: linha omitida até o autor escrever os textos.

Juntado ao `main` em 2026-11-08 pelo PR 101 (merge 3877410), migration 20261108_0038. Sem teste manual no Telegram real nem imagem contextual da Arena até essa data.

**Why:** a fonte não fecha esses pontos; não são valores canônicos, e o 10 min e os 45s do Duelo foram emprestados de outras regras.
**How to apply:** tratar como decisão revisável, não como regra do GDD. Antiexploit na Arena/Duelo só marca, nunca bloqueia ([[project-antiexploit-decisoes]]). Etapa 4 do [[project-escopo-beta]].

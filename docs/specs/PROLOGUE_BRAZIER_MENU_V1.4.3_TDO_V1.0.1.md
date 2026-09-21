# Especificação de implementação — Primeiro Braseiro, fim do Prólogo e Menu Principal

## Status documental

Esta é a especificação histórica usada para implementar o limite **primeiro Braseiro → fim do Prólogo → Menu Principal** sob Terras do Ocaso v1.0.1. O bloco já está implementado no `main`.

A autoridade vigente para trabalho novo é **GDD v1.4.3 + Terras do Ocaso v1.0.2 FINAL + Visual/UI 2026-09-21 sincronizada com TDO v1.0.2**. Este arquivo não deve ser usado como autoridade para as etapas jogáveis de P1. O `content_version = tdo-1.0.1` citado abaixo descreve corretamente o estado persistido pela implementação histórica e deve ser tratado explicitamente na próxima migração de P1.

> Autoridade: **GDD Estrutural v1.4.3 + Terras do Ocaso v1.0.1 FINAL + Visual/UI sincronizada v1.4.3/TDO v1.0.1**.
>
> Decisão adicional aprovada no projeto: **personagem novo inicia com 100 / 100 Vigor**. Essa decisão ainda não está textualizada na Fonte Mestra v1.4.3 e é registrada em `docs/SOURCE_AUTHORITY.md` como addendum autoritativo do projeto.

## 1. Escopo deste bloco

Implementar somente:

`estado pós-vitória do Cão Cinéreo → Braseiro da Estrada → Descansar → conclusão do Prólogo → Feito Cinzas na Estrada → início automático de P1 Vozes na Estrada → Menu Principal`.

Não implementar neste bloco:

- etapas jogáveis de P1 além de ativá-la e persistir o primeiro passo;
- Refúgio do Ocaso;
- Braseiro do Refúgio;
- Caçada/Ronda;
- Desbravar;
- Inventário/equipamento;
- Mercado/Guilda/Códice/Calendário/Vínculos/Classificação/Benefícios/Comunidade além das entradas de Menu;
- regeneração operacional de Vigor ou consumo de Vigor;
- sistemas completos de Feitos ou Missões além da persistência mínima reutilizável necessária.

## 2. Compatibilidade de ruleset

A Fonte vigente é `gdd-1.4.3-baseline-1.0`.

A implementação anterior criou combates sob `gdd-1.4.2-baseline-1.0`.

Regras:

- não reescrever silenciosamente um combate ativo v1.4.2;
- combate ativo v1.4.2 deve continuar reprodutível e concluível no ruleset armazenado;
- nova criação/personagem em estado seguro deve adotar v1.4.3;
- nova instância do primeiro combate, quando criada depois desta atualização, usa v1.4.3;
- após um combate antigo v1.4.2 terminar e o personagem entrar na fronteira segura do Braseiro, o estado persistente do personagem pode migrar para v1.4.3;
- snapshots antigos continuam identificados pelo ruleset em que foram criados.

## 3. Estado inicial de Vigor — decisão aprovada

Regra aprovada:

**personagem novo inicia com 100 / 100 Vigor.**

A Fonte Mestra continua definindo:

- Vigor Máximo = 100;
- regeneração +1 a cada 14m24s;
- reset das 06:00 não reabastece;
- Braseiro permanente não restaura Vigor.

Neste PR:

- persistir Vigor atual autoritativamente;
- novos personagens recebem 100;
- personagens existentes do ambiente atual podem ser migrados para 100 porque nenhuma mecânica anterior do repositório podia consumir Vigor;
- constraint 0–100;
- não implementar scheduler/lazy regeneration ainda, pois nenhum sistema deste escopo reduz Vigor;
- Descansar deve preservar o valor atual de Vigor sem alteração.

## 4. Braseiro da Estrada

Conteúdo regional oficial:

- ID técnico estável: usar slug documentado equivalente a `tdo.brazier.estrada`;
- nome player-facing: **Braseiro da Estrada**;
- Região: **Terras do Ocaso**;
- Local: **Estrada das Cinzas**;
- tipo: Braseiro permanente do mundo;
- é o primeiro Braseiro do Prólogo.

Ao concluir o combate tutorial com vitória:

- manter os 320 XP já concedidos exatamente uma vez;
- persistir HP restante;
- encerrar a atividade Foreground do combate;
- transicionar o personagem para o estado do primeiro Braseiro;
- registrar a descoberta do Braseiro da Estrada idempotentemente;
- não criar segunda descoberta por retry, reconnect ou callback duplicado.

A tela deve aparecer como já descoberta. Não existe `[Ativar Braseiro]`.

### UI exata

```text
🔥 Braseiro
Estrada das Cinzas · Terras do Ocaso

Entre pedras escurecidas pela fuligem, uma chama permanece acesa onde tudo ao redor parece ter sido abandonado. Seu calor atravessa o silêncio da estrada e oferece, pela primeira vez, um lugar seguro para recuperar as forças.

🔥 Braseiro · Descoberto
❤️ Descansar · Restaura HP

ℹ️ Braseiros permanentes podem servir para descanso e, quando outros forem descobertos, conectar diferentes pontos de Asterion através da Travessia dos Braseiros.

[Descansar]
```

Assets continuam opcionais; sem asset oficial, usar texto + inline keyboard sem placeholder literal.

## 5. Descansar

A ação `[Descansar]`:

- exige ownership atual e estágio correto;
- é transacional e idempotente;
- restaura HP para 100% do HP Máximo autoritativo;
- remove estados comuns de combate quando houver estado persistente aplicável;
- não restaura Vigor;
- não restaura Consumíveis, tentativas, limites diários ou economia;
- não concede XP, Coroas, Material ou Saque;
- não cria tela intermediária de “Braseiro ativado”.

A mesma transação de conclusão do passo deve:

1. marcar o Prólogo `Cinzas na Estrada` como concluído;
2. registrar o Feito correspondente;
3. iniciar P1;
4. atualizar estado de navegação para o Menu Principal;
5. preservar Região/Local como Terras do Ocaso · Estrada das Cinzas;
6. manter XP = 320 e nível = 1;
7. manter Vigor = valor atual, que para personagem novo é 100.

Retry/duplo clique/dois dispositivos não podem duplicar nenhuma dessas consequências.

## 6. Feito do Prólogo

Terras do Ocaso v1.0.1 define:

**Cinzas na Estrada · Exploração · concluir Prólogo · sem cosmético.**

Persistir de forma reutilizável, com unique por personagem + feito.

ID técnico estável recomendado:

`feat.tdo.cinzas_na_estrada`

Não exibir popup/tela adicional neste bloco. O registro é autoritativo e idempotente.

## 7. P1 — Vozes na Estrada

Conteúdo oficial:

- ID regional: **P1**;
- título: **Vozes na Estrada**;
- tipo: Missão Principal;
- nível recomendado: 1;
- início: **automático após a conclusão do Prólogo/tutorial**;
- Local principal: Estrada / Refúgio.

Persistir estado mínimo reutilizável:

- personagem;
- mission/content id;
- versão de conteúdo `tdo-1.0.1`;
- status `active`;
- etapa atual = 1;
- timestamps/versão de estado necessários para idempotência.

Primeira etapa oficial:

**Seguir pela Estrada das Cinzas.**

Não implementar o avanço dessa etapa neste PR.

Não conceder a recompensa de P1 neste PR. A recompensa de P1 só ocorre quando a missão for concluída no futuro.

## 8. Menu Principal inicial

Depois de Descansar e fechar o Prólogo, entrar diretamente no Menu Principal, sem tela de sucesso intermediária.

Estado autoritativo neste momento:

- Região: Terras do Ocaso;
- Local: Estrada das Cinzas;
- personagem Nv.1;
- sem Guilda;
- sem Caminho;
- HP = HP Máximo;
- Vigor = 100 / 100 para personagem novo;
- XP = 320 / 4.800;
- P1 ativa: Vozes na Estrada.

### Texto e estrutura

Usar o padrão definitivo:

```text
🌑 Asterion
Terras do Ocaso · Estrada das Cinzas

Sob céus cobertos de fuligem, as estradas de Asterion seguem marcadas por ruínas, brasas antigas e promessas que nunca repousam por completo. Mesmo nos caminhos mais silenciosos, cada passo ainda parece ecoar a memória de algo que o mundo não conseguiu esquecer.

{emoji da Classe} {nome} · Nv. 1
{Classe}

❤️ HP · {HP máximo} / {HP máximo}
{barra de HP real}

⚡ Vigor · 100 / 100
🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨

✨ XP · 320 / 4.800
{barra de XP derivada do estado real}

📜 Missão Principal · Vozes na Estrada

[Aventura] [Personagem]
[Guilda] [Mercado]
[Códice] [Calendário]
[Vínculos] [Classificação]
[Benefícios] [Comunidade]
[Configurações]
```

Regras:

- não mostrar tag de Guilda inexistente;
- não mostrar Caminho antes da Provação;
- não mostrar Missão Secundária, Crônica ou Evento Mundial sem estado aplicável;
- P1 pode e deve aparecer porque já existe estado autoritativo após a conclusão do Prólogo;
- datas e demais convenções seguem a Fonte Visual;
- não inventar telas internas dos destinos do Menu neste PR.

Botões de destinos ainda não implementados podem ser reconhecidos/acknowledged com segurança sem mutar o estado. Não criar conteúdo player-facing fictício para esses destinos.

## 9. Recovery e comandos

Depois da vitória e antes de Descansar:

- `/start` e `/menu` devem reconstruir prioritariamente o primeiro Braseiro;
- não reiniciar o Cão;
- não repetir 320 XP.

Depois de Descansar/concluir o Prólogo:

- `/start` e `/menu` abrem o Menu Principal autoritativo;
- não recriar Feito;
- não recriar P1;
- não restaurar HP novamente por simples abertura do Menu;
- não modificar Vigor.

Dois dispositivos devem observar o mesmo estado.

## 10. Persistência mínima recomendada

A implementação pode escolher nomes de tabelas compatíveis com a arquitetura, mas precisa suportar genericamente:

- Vigor atual do personagem;
- descoberta de Braseiro permanente;
- Feito adquirido;
- Missão ativa e etapa;
- Região/Local atuais ou estado mundial equivalente;
- estágio narrativo/progressão do Prólogo.

Constraints/uniques devem impedir duplicação de Braseiro, Feito e Missão por personagem.

Não usar Redis/FSM/message_id como fonte de verdade.

## 11. Concorrência e idempotência

Testar no PostgreSQL real:

- dois Descansar simultâneos;
- callback duplicado;
- callback antigo;
- outro ator;
- dois dispositivos;
- falha Telegram após commit;
- reconnect em Braseiro;
- reconnect/Menu após conclusão;
- tentativa de reabrir combate concluído;
- Feito único;
- P1 única;
- Braseiro único.

Uma única transação lógica deve vencer quando aplicável; demais tentativas retornam/reconstroem o estado atual.

## 12. Testes mínimos

Cobrir, no mínimo:

1. migration para v1.4.3 sem reescrever combate ativo v1.4.2;
2. novos personagens usam v1.4.3;
3. novo personagem inicia 100 Vigor;
4. constraint de Vigor 0–100;
5. personagem existente sem consumo prévio migra para 100;
6. vitória do Cão apresenta Braseiro da Estrada;
7. Braseiro é registrado uma única vez;
8. tela do Braseiro corresponde à Fonte Visual;
9. não existe botão Ativar Braseiro;
10. Descansar restaura HP a 100%;
11. Descansar não altera Vigor;
12. Descansar não concede XP adicional;
13. Feito Cinzas na Estrada é registrado exatamente uma vez;
14. P1 Vozes na Estrada inicia exatamente uma vez;
15. P1 começa ativa na etapa 1;
16. P1 não concede recompensa antecipada;
17. Menu mostra Região/Local corretos;
18. Menu mostra Nv.1;
19. Menu mostra HP cheio;
20. Menu mostra 100/100 Vigor;
21. Menu mostra 320/4.800 XP;
22. Menu mostra Missão Principal · Vozes na Estrada;
23. Menu não mostra Guilda/Caminho/Crônica/Secundária/Evento inexistentes;
24. todos os 11 botões aprovados do Menu aparecem;
25. destinos não implementados não mutam estado;
26. `/start` no Braseiro reconstrói Braseiro;
27. `/menu` no Braseiro não contorna o Prólogo;
28. `/start` após conclusão abre Menu;
29. `/menu` após conclusão abre Menu;
30. dois Descansar concorrentes não duplicam efeitos;
31. callbacks velhos/forjados não mutam;
32. falha Telegram após commit não desfaz conclusão;
33. migration upgrade/downgrade/upgrade quando seguro;
34. `alembic check`;
35. `ruff check .`;
36. pytest completo com PostgreSQL real e zero skips;
37. `git diff --check`.

## 13. Limite do PR

Pare quando o Menu Principal inicial estiver reconstruível e persistente.

Não iniciar as etapas jogáveis de P1. A próxima implementação começa a partir de **P1 — Vozes na Estrada · etapa 1**.

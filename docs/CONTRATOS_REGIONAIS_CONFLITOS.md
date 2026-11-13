# Contratos Regionais: conferência com a Fonte Mestra

**Estado:** sistema DESATIVADO por flag (`ASTERION_CONTRACTS_ENABLED=false`, padrão).
**Fontes comparadas:** `docs/specs/ASTERION_DECISOES_PROLOGO_E_CONTRATOS_v1_0_0.md` (Documento B)
contra o GDD Estrutural v1.6.0 (Fonte Mestra, conforme `SOURCE_AUTHORITY.md`) e o código.
**Todos os números** do Documento B estão em `src/asterion/domain/contracts_config.py`, marcados
"proposta a aprovar".

## O que confere

- Faixas de nível R1–R6 (1–10 … 51–60) batem com `RegionInfo.min_level` (1/11/21/31/41/51) e com as Regiões da Fonte.
- Gates pós-P1/P6/P12/P18/P24/P30 usam as Principais que fecham cada Região.
- `1 UM = 2 Materiais` (GDD §49.7): os perfis dão 2–6 Materiais (1–3 UM).
- Recompensa só XP, Coroas e Materiais; sem Equipamento, Runa, Encantamento, Consumível, Receita ou Núcleo.
- Contratos são Solo; Escolta existe como tipo mas não está ativa.

## Decisões pendentes do autor

O sistema só deve ser ativado depois destas respostas.

1. **O §36 não define o alvo de cada contrato.** Faltam: qual criatura (Caça), quantas unidades (Coleta), qual destino (Entrega) e qual ponto (Investigação). Valores provisórios no config (`TARGET_BY_TYPE`, `PLACE_BY_TYPE`, `PLACE_BY_DEFINITION`): Caça 1 vitória, Coleta 3 unidades, Entrega no Hub da Região, Investigação no 1º Local da Região.
2. **Entrega e Investigação não têm mecânica existente.** O §6.4 diz "já suportadas pelas mecânicas existentes" e o §39 proíbe nova mecânica, mas o jogo não tem ação genérica de entregar nem de examinar. Implementei o mínimo: o botão `CONTINUAR` confirma o objetivo se o personagem estiver no lugar certo. Aprovar ou definir outra ação.
3. **Quais Materiais pagam os tipos sem Material próprio** (Caça, Entrega, Investigação). A Fonte diz só "Materiais Básicos regionais vinculados". Provisório: o primeiro Material Básico da Região (`REGION_REWARD_MATERIAL`). Coleta paga o próprio Material exigido.
4. **Nomes do §36 sem Material Básico exato no catálogo.** "Ferro da Estrada" (CON_TDO_02) assumido como Ferro de Fuligem. "Coleta das Planícies" (CON_PDN_02, "recurso regional") assumido como Bronze de Marco.
5. **Caça conta só vitória manual e Solo** em Caçada. Ronda (automática) e Caçada em Grupo não contam (o §6.1 diz que "não basta entrar no combate"; Contratos são Solo).
6. **Coleta conta Material recebido de qualquer fonte do jogo** (Caçada, Desbravar, recompensas), menos recompensa de Contrato. Aprovar ou restringir.
7. **Materiais de recompensa saem vinculados** (`bound`), como nas Missões.

## Atenção de balanceamento (não é conflito direto)

Os perfis do §38 não escalam como a Fonte. Coroas por contrato como parte de `C(n) = round_10(100+15n)`: R1 ≈ 12–21%, R3 ≈ 15–21%, R5 ≈ 27–37%, R6 ≈ 31–48%. XP por contrato como parte de `XP(n)`: R1 ≈ 2,1–2,5%, R2–R6 ≈ 1,3–1,5%. Além disso, a distribuição-alvo de XP do GDD §49.7 não prevê Contratos, e não há teto diário (24 h de renovação, 3 simultâneos). Decisão de balanceamento do autor.

## Mudanças técnicas ligadas ao documento

- `hunt_contexts.started_at` (migration 0052): o §30 exige o início da ação como autoridade de expiração.
- Nenhum Choice Node: `validate_node` já recusa tudo que não for Principal, Secundária ou Prólogo.

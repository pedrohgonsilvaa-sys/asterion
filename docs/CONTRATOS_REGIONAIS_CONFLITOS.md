# Contratos Regionais: conferência com a Fonte Mestra

**Estado:** RESOLVIDO. As 7 pendências listadas neste documento foram decididas
pelo autor em `docs/specs/ASTERION_CONTRATOS_REGIONAIS_DECISOES_FECHADAS_v1_0_0.md`
(2026-11-13) e aplicadas ao código. Este arquivo fica como registro histórico.

## O que confere (sem mudança)

- Faixas de nível R1–R6 (1–10 … 51–60) batem com `RegionInfo.min_level` e com as Regiões da Fonte.
- Gates pós-P1/P6/P12/P18/P24/P30 usam as Principais que fecham cada Região.
- `1 UM = 2 Materiais` (GDD §49.7): os perfis dão 2–6 Materiais (1–3 UM).
- Recompensa só XP, Coroas e Materiais; sem Equipamento, Runa, Encantamento, Consumível, Receita ou Núcleo.
- Contratos são Solo; Escolta existe como tipo mas não está ativa.

## Pendências resolvidas pelo fechamento v1.0.0

1. **Alvo de cada contrato:** mantidos os valores provisórios (Caça 1 vitória, Coleta 3 unidades, Entrega no destino do contrato, Investigação no local do contrato) como regra padrão por tipo — aprovado no fechamento §2.2/§3.3/§4.2/§5.3/§6.3.
2. **Mecânica de Entrega/Investigação:** o botão `CONTINUAR` confirmando no local correto foi aprovado como fluxo definitivo — fechamento §5.2/§6.2.
3. **Material de recompensa de Caça/Entrega/Investigação:** confirmado o primeiro Material Básico regional — fechamento §7.1.
4. **Mapeamentos de nome:** `Ferro da Estrada` → `Ferro de Fuligem` e `Coleta das Planícies` → `Bronze de Marco` aprovados — fechamento §7.3.
5. **Contagem de Caça:** confirmado só vitória Manual Solo; Ronda e Grupo não contam — fechamento §3.2.
6. **Contagem de Coleta:** confirmado ganho de qualquer fonte legítima pós-ativação, excluindo estoque prévio, a própria recompensa do contrato e transferência/comércio entre jogadores — fechamento §4.3/§4.4.
7. **Vínculo dos Materiais de recompensa:** confirmado que saem vinculados, como nas Missões — fechamento §7.2.

## Balanceamento (resolvido)

XP e Coroas foram recalibrados para ~25% (faixa prática 20–30%) do ganho de referência da região (`level_xp`/`crowns_per_level` no nível mínimo da faixa), substituindo os valores provisórios que variavam de ~12% a ~48% — fechamento §8. O limite operacional (3 contratos simultâneos + renovação de 24h) foi confirmado sem teto diário adicional — fechamento §9.

## Mudanças técnicas ligadas ao documento

- `hunt_contexts.started_at` (migration 0052): o §30 exige o início da ação como autoridade de expiração.
- Nenhum Choice Node: `validate_node` já recusa tudo que não for Principal, Secundária ou Prólogo.

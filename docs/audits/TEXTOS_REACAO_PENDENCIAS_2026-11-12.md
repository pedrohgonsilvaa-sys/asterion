# Textos de Reação dos NPCs v1.0.0 — pendências de copy (2026-11-12)

> **Resolvido na v1.0.1** (`docs/specs/ASTERION_TEXTOS_REACAO_NPCS_v1_0_1.md`). Este arquivo fica como histórico do que foi pedido.

Decisão do autor (2026-11-12): **o contrato `ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md` prevalece** sobre o pacote de textos, e a regra de NPC não onisciente (§3 e critério de aceite 5) não tem exceção. O runtime já carrega as falas compatíveis; os itens abaixo ficam sem fala até a copy ser revista. O catálogo é regenerado por `scripts/build_narrative_reaction_copy.py`, que imprime estas mesmas listas.

## A. Nós com `choice_id` e opções diferentes do contrato (9)

Reescrever as três falas usando o `choice_id` e as opções do contrato (§7).

| Texto atual | Contrato | Opções do contrato |
|---|---|---|
| `P15_deviation_reading` | `P15_anomaly_method` | 1. Testar a explicação mais simples primeiro · 2. Marcar a discrepância como não resolvida · 3. Procurar uma terceira medição |
| `S15_map_pattern` | `S15_result_vs_cause` | 1. Chegar ao destino primeiro · 2. Entender o ponto de partida antes de seguir · 3. Fazer a rota e registrar os dois fatos |
| `P16_structure_axis` | `P16_axis_priority` | 1. Garantir que o mecanismo não cause dano · 2. Entender como ele mede referências · 3. Registrar tudo antes de tocar |
| `S16_cartography_method` | `S16_mapping_policy` | 1. Somente caminhos verificados · 2. Incluir rotas antigas com aviso de risco · 3. Marcar as divergências como camada separada |
| `S17_mechanism_response` | `S17_calibration_policy` | 1. Devolver sem experimentar · 2. Testar o funcionamento de modo controlado · 3. Registrar o estado e deixar para análise posterior |
| `P17_measurement_posture` | `P17_veil_evidence` | 1. Aceitar como evidência suficiente · 2. Tratar como registro incompleto · 3. Buscar outra fonte antes de usar a conclusão |
| `P18_archon_posture` | `P18_anchors_posture` | 1. Registrar e preservar o conhecimento · 2. Buscar confirmação em outras regiões · 3. Questionar quem decidiu usar as Âncoras e com quais custos |
| `S18_route_evidence` | `S18_route_closure` | 1. Encerrar a rota e priorizar os viajantes · 2. Manter a rota documentada, mesmo sem uso · 3. Testar se ainda existe alguma utilidade antes de fechar |
| `P19_region_priority` | `P19_priority` | 1. Rotas e segurança · 2. Entender a infraestrutura antiga · 3. Ouvir primeiro quem vive ali |

## B. Fala de NPC que não recebeu a memória daquela opção (29)

Trocar quem fala por um NPC que recebe a memória da opção (coluna "Quem sabe"). Quando a opção só grava memória do personagem ("—"), nenhum NPC sabe: a fala precisa ser do próprio personagem/narração, ou o contrato precisa ganhar um alvo de NPC numa revisão.

| Nó / opção | Fala atual de | Quem sabe |
|---|---|---|
| P10/o3 | Dara Venn | Iven |
| S10/o1 | Iven Raal | Dara |
| S12/o1, o2 | Nera Voss | Iven |
| S12/o3 | Talen Orm | Iven |
| P14/o1, o2, o3 | Talen Orm | Nera |
| P20/o1 | Ilyan Korr | Sera Morn |
| P24/o1 | Rava Kern | Ilyan |
| S24/o1 | Sera Morn | Ilyan |
| P27/o1, o2, o3 | Rava Kern | — |
| S28/o1, o2, o3 | Rava Kern | — |
| P29/o1, o2, o3 | Eris Val | — |
| S29/o1 | Rava Kern | — |
| S29/o2, o3 | Eris Val | — |
| P30/o1, o2, o3 | Roven Pell | — |
| S30/o1, o3 | Haro Sen | — |
| S30/o2 | Sera Nol | — |

## C. Nomes

Sera Morn (Várzeas) e Sera Nol (Confins) são NPCs diferentes, assim como Talen Orm (Nareth) e Talen Nyr (Confins). O runtime guarda a memória de cada um separadamente; a copy deve sempre usar o nome completo do NPC certo.

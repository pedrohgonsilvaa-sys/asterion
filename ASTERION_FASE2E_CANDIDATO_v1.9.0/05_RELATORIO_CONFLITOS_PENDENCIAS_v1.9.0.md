# Conflitos e pendências — revisão candidata v1.9.0

**Estado:** documento de trabalho não canônico.  
**Escopo:** diferenças documentais e gates verificáveis para a preparação das minutas.

## Conflitos com as fontes instaladas

| Fonte vigente | Contradição atual | Tratamento na minuta |
|---|---|---|
| GDD v1.6.0 §24.2 | Afirma que não há categorias mecânicas globais de armadura e que forma de arma não concede Proficiência; também trata requisitos como declarações excepcionais por item. | Substituir somente as frases conflitantes por quatro categorias de proteção e requisito de Proficiência aprovado; preservar as demais regras de nível, slots, raridade e equipamento. |
| GDD v1.6.0 §24.5 | Não inclui Proficiência na lista de requisitos verificados pelo validador. | Acrescentar verificação da Proficiência declarada sem modificar o restante do validador. |
| GDD v1.6.0 §49.8 | Publica núcleos-base genéricos para os quatro slots corporais e não publica núcleo de Escudo. | Substituir somente esses núcleos pelos valores aprovados v0.7 e adicionar o núcleo de Escudo; manter fórmulas e pools por slot. |
| GDD v1.6.0 §49.9 | Seleção de template é uniforme na ausência de pesos e não contém pesos v0.4. | Incluir pesos aprovados depois dos filtros, sem alterar chance global nem distribuição de raridade. |
| GDD v1.6.0 §49.7 | Não registra permanência das Proficiências aprendidas no Legado. | Acrescentar somente essa permanência, sem reescrever o Legado. |
| GDD v1.6.0 §55.3 | Afirma que não existem Proficiências globais de arma. | Manter requisitos de Arte e tags intactos; diferenciar Proficiência de equipagem. |
| Weapon Metadata v1.0.0 §§2,6–8 | Forma, ausência de Proficiência global e regra atual de Escudo não representam o sistema aprovado. | A minuta v1.1.0 define Proficiência em eixo separado, Escudo não-arma de Secundária e compatibilidade com 2H. |
| Weapon Metadata v1.0.0 §5 | Não diferencia lista de tags explicitamente vazia de campo ausente/null. | A minuta declara [] válido e explícito; ausente/null permanecem inválidos quando a declaração é exigida. |
| Weapon Metadata v1.0.0 §9.1 e §15 | Alega que não existe Fonte Regional FINAL de Confins. | Corrigir pela autoridade raiz e pelas cinco declarações da §19.2 de Confins v1.0.0. |

## Pendências de Game Design — exatamente as três linhas da matriz v1.8.0

| ID | Estado corrigido |
|---|---|
| GD-NEW-CATALOG-66-RECIPES | Os atributos individuais dos 66 regionais estão aprovados. Permanecem pendentes a confirmação dos IDs no registry de release, as 198 receitas/output links propostos, e as demais vinculações de receita em relação ao snapshot. Não criar receitas Lendárias ou Míticas. |
| GD-WEAPON-METADATA-CONTRACT | A decisão de manter tags vazias explícitas em 12 armas foi aprovada; a revisão global e sua publicação versionada continuam pendentes. |
| GD-LOOT-ELIGIBILITY-TEMPLATE-RARITY | 24 pares Torso/Mítico estão aprovados como inelegíveis; 63 pares têm evidência local favorável sem aprovação final; 633 seguem pendentes. Não marcar os 696 pares restantes como elegíveis finais. |

Os 34 atributos individuais de Origem também estão aprovados; esta decisão não aparece como pendência na matriz. A matriz candidata v1.8.0 contém três linhas pendentes e o array do manifesto antigo continha quatro itens incorretos; o manifesto derivado alinha o array às três linhas.

## Gates que não são decisão numérica de Game Design

- **Snapshot:** não existe snapshot autorizado; nenhuma conexão a release, staging ou produção foi feita.
- **Identidade em release:** 0/226 template IDs verificados. IDs locais/candidatos não se tornam canônicos por constarem do pacote.
- **Receitas:** vínculos existentes e receitas candidatas continuam por confrontar com registry, output IDs e materiais de release.
- **Campanha:** os 24 vínculos locais preservam mission_id, RewardEvent.source_id, EquipmentItem.source_key e equipment_template_id separados; identidade de release continua desconhecida.
- **Baseline TDO:** a raiz e docs selecionam v1.0.16. TDO v1.0.17 está presente no worktree Phase2B como arquivo não rastreado, hash verificado no preflight, e permanece apenas baseline-alvo aprovado. Não é autoridade operacional.
- **Publicação:** GDD, contrato, adendos regionais e SOURCE_AUTHORITY continuam sem alteração.
- **Regra de guarda do kit:** a proteção candidata contra perda do último loadout funcional, no adendo de Origem v1.4.0, está identificada como sujeita à validação transacional. Foi deliberadamente excluída do texto normativo desta minuta; não se presume homologada aqui.

## Resultado

**GO** para revisão documental candidata e revisão por Game Design.  
**NO-GO** para publicação canônica, validação de IDs em release, importação, migração, ativação da feature flag, merge ou deploy. A revisão não autentica o catálogo no release.

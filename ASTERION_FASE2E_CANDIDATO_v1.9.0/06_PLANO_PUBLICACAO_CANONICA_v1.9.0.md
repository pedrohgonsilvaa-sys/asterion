# Plano de publicação canônica — sujeito a aprovação posterior

**Estado:** plano candidato. Nenhum passo abaixo foi executado.

1. **Aprovar as minutas.** Game Design e responsáveis por GDD/contrato revisam o texto proposto, confirmam a correspondência com as três linhas pendentes e autorizam uma revisão canônica versionada.
2. **Obter snapshot imutável.** Release/DBA entrega o snapshot conforme o contrato vigente de topo v1.7.0, com proveniência, timestamp, versão/schema, escopo, hashes SHA-256, export de registry, vínculos e disponibilidade. Não se solicita conexão direta ao banco.
3. **Reconciliar identidades e namespaces.** Comparar os 226 template IDs candidatos, recipe_id/output_id, 24 recompensas e instâncias disponíveis no snapshot. Preservar mission_id, RewardEvent.source_id, EquipmentItem.source_key e equipment_template_id como namespaces distintos. Resolver colisões antes de qualquer publicação.
4. **Fechar receitas e Saque.** Decidir e registrar os 198 vínculos/receitas propostos e as 696 combinações de elegibilidade não resolvidas; preservar os 24 pares inelegíveis, 63 evidências locais e 633 pendências até decisão. Não criar receitas Lendárias/Míticas sem fonte aprovada.
5. **Revisar fontes documentais.** Gerar versões candidatas completas do GDD, Weapon Metadata e adendos regionais; aplicar somente os trechos aprovados e reconciliados. Incluir as 34 peças de Origem e suas restrições aprovadas sem copiar dados não verificados.
6. **Revalidar integridade e autoridade.** Conferir diffs contra cada fonte vigente, versões, contagens, hashes e links. A mudança de TDO para v1.0.17 só se torna autoridade operacional em uma atualização do SOURCE_AUTHORITY.md explicitamente aprovada e aplicada; atualizar também a cópia operacional conforme o procedimento do projeto.
7. **Gate separado de integração.** Depois da publicação documental autorizada, submeter plano de integração e dados a autorização própria. A aprovação documental não libera importação, migrations, backfill, feature flag, staging ou produção.
8. **Gate de lançamento.** Qualquer merge, deploy ou ativação permanece dependente de aprovação específica e das validações técnicas e operacionais correspondentes.

## Resultado presente

Somente as minutas candidatas, o manifesto derivado e suas evidências locais foram preparados. Snapshot de release, publicação canônica e integração operacional continuam ausentes.

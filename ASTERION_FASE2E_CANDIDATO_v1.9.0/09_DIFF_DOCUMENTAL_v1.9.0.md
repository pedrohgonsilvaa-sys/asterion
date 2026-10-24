# Diff documental — derivação v1.9.0 sobre v1.8.0

**Tipo:** revisão candidata de documentos de trabalho.  
**ZIP pai:** v1.8.0 preservado integralmente em inputs/; SHA-256 igual ao original.

## Alterações introduzidas

1. Criadas minutas separadas do GDD Estrutural e do Contrato Global de Weapon Metadata, com referências às seções exatas que devem ser complementadas ou substituídas.
2. Criada matriz de correspondência entre as decisões homologadas, suas evidências, os documentos-alvo e as pendências que permanecem.
3. O array ativo decisions.remaining_game_design_decisions do manifesto derivado contém exatamente as três chaves existentes na matriz pendente v1.8.0: GD-NEW-CATALOG-66-RECIPES, GD-WEAPON-METADATA-CONTRACT e GD-LOOT-ELIGIBILITY-TEMPLATE-RARITY.
4. Removidas da lista ativa as afirmações incorretas de que os atributos individuais dos 66 regionais ou dos 34 itens de Origem estão pendentes. Ambos os conjuntos continuam aprovados nas evidências v1.8.0.
5. A referência vigente ao snapshot foi corrigida para o contrato de topo 07_CONTRATO_SNAPSHOT_RELEASE_v1.7.0.md. A cópia em inputs/v1.6.0/07_CONTRATO_SNAPSHOT_RELEASE_v1.6.0.md permanece identificada como artefato histórico.
6. Adicionado baseline de autoridade com hashes das seis fontes regionais selecionadas pelo SOURCE_AUTHORITY.md raiz e registro separado de TDO v1.0.17 como alvo não operacional do worktree Phase2B.
7. Adicionado manifesto derivado com hashes dos novos artefatos e proveniência/hashes históricos reaproveitados sem alteração.
8. Adicionados relatório de conflitos, matriz GO/NO-GO e plano de publicação dependente de aprovações futuras.

## Preservação explícita

- 226 template IDs e suas proveniências: sem regeneração ou alteração nesta revisão.
- Valores candidatos e estados aprovados dos 66 equipamentos regionais e 34 Equipamentos de Origem: sem alteração.
- 24 vínculos locais de Campanha e seus namespaces: sem alteração.
- Valores numéricos candidatos anteriormente congelados: sem alteração.
- Fonte GDD v1.6.0, contrato Weapon Metadata v1.0.0, seis fontes regionais e ambos os SOURCE_AUTHORITY: sem alteração.
- Nenhum snapshot, importação, migração, ativação de flag, merge ou deploy realizado.

O manifesto novo é autoritativo apenas para a revisão candidata v1.9.0. O manifesto e os hashes antigos continuam dentro do ZIP pai imutável.

# Fase 2E: decisões de Game Design (2026-11-13)

Registro das três pendências de Game Design do pacote candidato v1.9.1, decididas pelo autor em 2026-11-13. Este documento **não publica nada**: o pacote continua candidato e não canônico, e `SOURCE_AUTHORITY.md` não muda.

## Decisões do autor

| Pendência | Decisão |
|---|---|
| `GD-NEW-CATALOG-66-RECIPES` | Aprovados os IDs candidatos dos 66 equipamentos regionais e as 198 receitas/output links propostos (3 por item: Comum, Raro, Épico). Não há receitas Lendárias nem Míticas. |
| `GD-WEAPON-METADATA-CONTRACT` | Aprovada a revisão global do contrato de metadados de arma (minuta v1.1.0), incluindo a lista de tags vazia explícita nas 12 armas já aprovadas. |
| `GD-LOOT-ELIGIBILITY-TEMPLATE-RARITY` | Os 63 pares com indício favorável e os 633 pendentes, 696 no total, passam a ser **elegíveis** ao Saque. Os 24 pares Torso/Mítico continuam **inelegíveis** (já aprovado antes). |

## O que a engenharia conferiu (2026-11-13)

Conferência feita contra o código do `main`, não contra um snapshot de release:

- Os 226 IDs do ledger são únicos.
- Os 66 IDs novos e os 34 de Origem não colidem com nenhum ID já existente no código.
- Das 198 receitas, 0 existem no código; os 66 `output_id` distintos também não.
- Dos 46 itens "existentes", 20 aparecem no código; os 26 restantes não puderam ser confirmados aqui.

## O que foi publicado (autorizado pelo autor em 2026-11-13)

Só as **regras de sistema**, que não dependem de ID de release:

- `ASTERION_GDD_Estrutural_v1.7.0_Fonte_Mestra.md` (substitui a v1.6.0): Proficiências e Treinamento, categorias de proteção, Escudo, kits de Origem, núcleos corporais por categoria e núcleo de Escudo, pesos de Saque v0.4, permanência no Legado.
- `ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.1.0_FINAL.md` (substitui a v1.0.0): Proficiência como eixo separado, Escudo, lista vazia explícita, Confins do Véu (27 armas).
- `SOURCE_AUTHORITY.md` (raiz e `docs/`) aponta para as duas versões novas.

As versões v1.6.0 e v1.0.0 ficam no repositório como registro histórico. A publicação não altera código: a implementação da Fase 2E continua pendente.

## O que continua NO-GO

As aprovações acima fecham as decisões de Game Design, mas estes gates são técnicos e seguem abertos:

1. **Snapshot de release.** Não existe export assinado e com hash do release (contrato v1.7.0). Sem ele, os 226 IDs, os 160 vínculos existentes, os 24 vínculos de Campanha e os materiais das receitas não foram validados no release.
2. **Publicação dos IDs e adendos regionais.** Ainda não publicados: IDs de template, receitas, vínculos, elegibilidade individual de Saque (os 696 pares) e os adendos das Fontes Regionais. Dependem do snapshot (item 1).
3. **Importação, migration, flag, merge e deploy** da Fase 2E.
4. **Regra de guarda do kit** (proteção contra perder o último loadout funcional): fora da minuta, depende de validação transacional.

## Fonte

Pacote `ASTERION_FASE2E_v1.9.1_PARA_HOMOLOGACAO_GD.zip` (na raiz, fora do Git). Relatório: `05_RELATORIO_CONFLITOS_PENDENCIAS_v1.9.1.md`. Matriz: `07_MATRIZ_GO_NO_GO_v1.9.1.csv`.

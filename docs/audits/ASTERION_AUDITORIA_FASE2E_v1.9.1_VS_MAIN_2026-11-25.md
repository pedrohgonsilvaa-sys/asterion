# Auditoria: Fase 2E v1.9.1 contra a `main` (2026-11-25)

Este documento não é fonte canônica. Ele não publica nem aprova nada. Ele compara o pacote candidato `ASTERION_FASE2E_v1.9.1_PARA_HOMOLOGACAO_GD.zip` (e o pacote v1.8.0 que vem dentro dele) com o código e as fontes da `main` no commit `a9e9e12`.

## 1. Autoridade vigente (SOURCE_AUTHORITY.md na `main`)

| Assunto | Versão vigente | Pacote Fase 2E usa |
|---|---|---|
| Fonte Mestra | GDD Estrutural v1.7.1 | minuta sobre v1.6.0/v1.7.0 |
| Weapon Metadata | Contrato v1.1.1 FINAL | minuta v1.1.0 |
| Proficiências de Armas | Spec v1.0.0 (8 famílias + Escudo, 19 armas), na `main` (`77e5727`) | matriz 4×4 e Treinamento I–IV |
| Classes de Armadura | Spec v1.0.0 (Veste/Leve/Média/Pesada por template), na `main` (PR 172) | categorias de proteção v1.7.0 |
| Terras do Ocaso | v1.0.18 FINAL | v1.0.16 FINAL |

Foram revogados em 2026-11-13 e continuam revogados: kits de Origem de 34 templates, núcleos corporais por categoria, Treinamento em etapas e `weapon.form.rod` (Bastão).

## 2. Os 226 IDs do ledger

| Partição | Total | ID achado no código | Nome achado no código |
|---|---|---|---|
| `normal_generic` | 78 | 3 | 62 |
| `campaign` | 36 | 12 | 36 |
| `special_recipe` | 12 | 8 | 12 |
| `origin` | 34 | 0 | 0 |
| `new_candidate` | 66 | 0 | 0 |

Conclusões:

- **Os IDs do ledger usam outro esquema de nomes.** O código identifica a maior parte dos itens por chaves próprias, por exemplo `meridian_boots` em `domain/professions.py`, e não por `equipment.nareth.normal.botas_do_meridiano`. Existem 120 itens no código pelo nome, mas só 23 pelo ID do ledger.
- **Os 34 de Origem estão mortos.** Os kits de Origem foram revogados, e a arma inicial passou a seguir a spec de Proficiências.
- **Os 66 itens novos não existem em nenhuma Fonte Regional FINAL** (busca pelos 66 nomes em todos os `.md` da `main`: zero ocorrências). A única origem deles é o próprio pacote candidato ("v1.3.0 new_candidate / registro 1"). Na prática, eles são conteúdo novo, e não itens já canônicos que faltava implementar.

## 3. Os 66 itens novos (11 por região, 6 regiões)

- Slots: 12 Cabeça, 12 Torso, 12 Mãos, 12 Pés, 12 Principal e 6 Secundária (Escudo).
- **6 armas usam `weapon.form.rod` (Bastão)**, que foi removido no contrato v1.1.1. Cada uma precisa de uma nova forma e de uma família de Proficiência da spec v1.0.0. Essa é uma decisão de Game Design.
- Proficiência das armaduras: 24 Vestes e 24 Pesada. Isso é compatível com as Classes de Armadura v1.0.0 (Veste e Pesada existem), mas precisa de conferência de nomes e tags.
- Atributos: todos marcados "Nv.60, Comum, +0". O pacote v1.8.0 usa os núcleos v0.7 **por categoria**, que foram revogados. A regra vigente é o núcleo **por slot**. Os números aprovados dos 66 precisam de recálculo e auditoria pelo systems-designer antes de qualquer uso.

## 4. Receitas

- As 198 receitas propostas (3 por item novo: Comum, Raro e Épico) não estão no código: 0 de 198. Elas dependem dos 66 itens.
- Dos 160 vínculos receita → item de itens existentes, 27 `recipe_id` estão no código. O resto usa IDs que o código não conhece, que é o mesmo problema de esquema da seção 2.

## 5. Saque (720 pares)

| Partição | Elegível aprovado em 13/11 | Inelegível (Torso/Mítico) |
|---|---|---|
| `normal_generic` | 378 (63 com evidência + 315 pendentes) | 12 |
| `new_candidate` | 318 | 12 |

- Nenhum par envolve template de Origem, então a revogação dos kits não afeta o Saque.
- 318 dos 696 pares só fazem sentido se os 66 itens novos entrarem no jogo.
- Os 378 pares de itens existentes usam IDs do ledger e precisam ser mapeados para as chaves do código.
- Os pesos de Saque v0.4 continuam vigentes (SOURCE_AUTHORITY, 13/11).

## 6. Snapshot de release

Continua sem existir um snapshot assinado. Esta auditoria mostra que o problema é anterior ao snapshot: o ledger e o código usam esquemas de ID diferentes. Antes de qualquer snapshot, é preciso decidir qual esquema vale.

## 7. Decisões para o autor

1. **Esquema de ID:** adotar as chaves que já estão no código como identidade oficial e mapear o ledger para elas, ou migrar o código para os IDs do ledger.
2. **Os 66 itens novos:** entram como conteúdo novo, com adendo nas Fontes Regionais, ou ficam fora?
3. **As 6 armas Bastão:** se os 66 entrarem, qual forma e qual família cada uma recebe?
4. **Atributos dos 66:** autorizar o systems-designer a recalcular pelo núcleo por slot vigente, para aprovação posterior.
5. **Saque:** aplicar agora só os 378 pares de itens existentes, e os 318 restantes só depois da decisão 2?

## 8. Decisões do autor (2026-11-25)

1. Esquema de ID: as chaves do código são a identidade oficial. O ledger é mapeado para elas.
2. Os 66 itens novos entram como conteúdo novo: o game-designer escreve os adendos regionais e o systems-designer recalcula os atributos pelo núcleo por slot vigente. O autor aprova antes de qualquer código.
3. Bastão fica fora. A engenharia retirou as 6 armas `weapon.form.rod` dos itens novos (66 viram 60), junto com as 18 receitas e os pares de Saque delas. Não houve conversão para Cajado, porque cada região já tem 1 Cajado.
4. Próximo passo: spec de implementação do Saque dos 378 pares de itens existentes. Migration, flag, merge e deploy continuam NO-GO.

## 9. Achado posterior: o Saque regional já está na `main`

Depois das decisões da seção 8, a engenharia encontrou em `src/asterion/domain/regional_equipment.py` (commits `2983b81`, `b99963e` e PR 172) um catálogo regional de Saque que já roda, com nomes de `ASTERION_CATALOGO_REGIONAL_ARMAS_E_ARMADURAS.md`:

- 20 armas por região (19 da spec de Proficiências + Escudo), ligadas a `weapon.type.base.*`;
- 16 armaduras por região (Veste, Leve, Média e Pesada × Cabeça, Torso, Mãos e Pés);
- 3 Selos + 3 Relicários por região;
- sorteio em `domain/road.py::materialize_equipment`: grupo uniforme, template uniforme no grupo, 2H dentro de Principal e Torso/Mítico excluído.

Consequências:

- **Saque dos 378 pares:** com só itens existentes, os pesos v0.4 dão probabilidade igual dentro de cada grupo, que é o mesmo comportamento do código atual. Mas o catálogo do código não é o catálogo do ledger: 49 dos 78 nomes do ledger não estão no pool regional do código. Implementar os 378 pares significaria **trocar** o pool regional que já roda.
- **Os 66 novos:** Veste/Pesada, Cajado e Escudo regionais já existem no pool do código com outros nomes. Os 60 restantes (sem Bastão) duplicariam essas funções.
- **O que de fato falta:** os Ofícios (`domain/professions.py`) não fabricam nenhum item do catálogo regional. As receitas regionais são a lacuna real.

## 10. Decisão final do autor (2026-11-25)

A Fase 2E está **encerrada como superada**. As decisões da seção 8 sobre os 66 itens novos e sobre a spec do Saque dos 378 pares ficam canceladas. O pacote v1.9.x continua fora do Git e sem autoridade.

Próxima tarefa, separada: escrever a spec para os Ofícios fabricarem os itens do catálogo regional que já existe em `domain/regional_equipment.py`. Materiais e custos serão propostos pelo game-designer e pelo systems-designer e aprovados pelo autor.

# ASTERION — Especificação: Classes de Armadura e Proficiência de Armadura v1.0.0

**Status:** aprovada pelo autor em 2026-11-14. **Ainda não implementada.**
**Origem:** `ASTERION_PLANO_EQUIPAMENTOS_DROPAVEIS_POR_REGIAO_v1_0_0.md` (Etapas C e D).
**Valores:** os números abaixo foram propostos pelo assistente e aprovados pelo autor como ponto de partida. Exigem teste de balanceamento depois; não são resultado de simulação.

## 1. Escopo (D1 = A)
Cabeça, Torso, Mãos e Pés têm uma classe de armadura: `veste`, `leve`, `media` ou `pesada`.
Acessório e Artefato não têm classe. A classe pertence ao **template** (não ao slot, ao personagem, à Região nem à raridade).

## 2. Efeito (D2 e D3 = A: camada separada, orçamento do slot intocado)
Cada peça equipada com classe soma ao personagem, em pontos percentuais (p.p.):

| Classe | Esquiva | Bloqueio |
|---|---:|---:|
| Veste | +1,00 | 0 |
| Leve | +0,75 | +0,25 |
| Média | +0,50 | +0,50 |
| Pesada | 0 | +1,00 |

- Não altera `CORE60`, `SlotWeight`, `EconomySW`, pools de secundários nem a fórmula de secundários.
- Soma com os secundários Esquiva/Bloqueio do item e com os demais bônus; o teto de cada atributo segue a regra global já existente.
- Não existe peso físico nem equip load. `SlotWeight` continua não sendo peso.

## 3. Mistura (D6 = A)
Sem bônus e sem penalidade por conjunto. Cada peça vale por si.

## 4. Quem pode usar (D4)
As seis Classes de personagem podem usar as quatro classes de armadura. A trava é só a Proficiência (D5) e o nível. Sem restrição por Classe de personagem e sem smart loot.

## 5. Proficiência de Armadura (D5 = A)
Quatro Proficiências independentes, no mesmo Treinador de Armas do Refúgio do Ocaso, em uma aba nova "Armaduras". Não altera a Proficiência de Armas.

| Proficiência | Nível mínimo | Custo |
|---|---:|---:|
| Veste | — (inicial, grátis) | 0 |
| Leve | 10 | 1.000 Coroas |
| Média | 20 | 4.000 Coroas |
| Pesada | 30 | 10.000 Coroas |

Compra atômica e idempotente; sem Coroas ou sem nível, não gasta nada. Sem devolução/reescolha nesta versão.

## 6. Ordem de validação ao equipar (Equipment Validator central)
1. item existe e está em estado permitido; 2. slot válido; 3. nível; 4. regras 2H/Secundária; 5. Proficiência de Arma; 6. **Proficiência de Armadura**; 7. máximo de 1 Mítico; 8. bind/estado; 9. commit atômico.
Mensagem de bloqueio sempre específica, por exemplo: "Proficiência de Armadura Pesada não aprendida." A UI só mostra o motivo; o validador decide.

## 7. Itens antigos (D11 = A), por `template_id`
Só existem 8 armaduras antigas, todas de Terras do Ocaso (`region.terras_do_ocaso`):

| Item antigo | Classe |
|---|---|
| Capuz das Cinzas, Veste do Caminhante, Luvas de Fuligem, Botas da Estrada | Veste |
| Elmo de Fuligem, Couraça de Fuligem, Manoplas de Fuligem, Passos de Fuligem | Leve (decisão delegada ao assistente) |

Itens já existentes não são destruídos, rerrolados nem têm `item_level` alterado. Quem já usa as peças Leve sem a Proficiência Leve fica com a peça equipada, mas não consegue equipar outra Leve até aprender; definir esse tratamento no commit de implementação e avisar o autor.

## 8. Armaduras regionais já no catálogo
As 96 armaduras regionais (`domain/regional_equipment.py`) hoje não têm classe. A implementação deve atribuir a classe pelo agrupamento do catálogo regional: Veste, Leve, Média, Pesada (4 slots cada, por Região).

## 9. Documentos a emendar na implementação
- `SOURCE_AUTHORITY.md`: registrar esta especificação como vigente para classes de armadura (revoga a revogação de 13/11 só para esta parte).
- `ASTERION_ESPECIFICACAO_FINAL_PROFICIENCIAS_EQUIPAMENTO_v1_0_0.md`: §17 e regras de equipar.
- `HANDOFF.md`: item 8 dos próximos passos.

## 10. Testes obrigatórios
Equipar cada classe com e sem Proficiência; nível insuficiente; item antigo com/sem classe; compra idempotente; Mítico máx. 1; 2H preservado; soma de Esquiva/Bloqueio por classe; determinismo do drop inalterado.

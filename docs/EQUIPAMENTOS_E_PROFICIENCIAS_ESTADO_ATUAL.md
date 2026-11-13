# Equipamentos e proficiências: o que existe hoje

Gerado em 2026-11-13 a pedido do autor, para servir de base na refação das decisões que estavam no Codex e se perderam. Este arquivo NÃO é fonte canônica. Ele só lista o que foi encontrado no código, nos documentos e na memória de trabalho.

## 1. Formas de arma no código

Fonte: `src/asterion/domain/weapon_metadata.py`, constante `WEAPON_FORM_LABELS`.

| ID | Nome | Situação |
|---|---|---|
| `weapon.form.sword` | Espada | existe |
| `weapon.form.dagger` | Adaga | existe |
| `weapon.form.axe` | Machado | existe |
| `weapon.form.hammer` | Martelo | existe |
| `weapon.form.mace` | Maça | existe no código, mas o autor removeu do jogo |
| `weapon.form.spear` | Lança | existe |
| `weapon.form.bow` | Arco | existe |
| `weapon.form.crossbow` | Besta | existe |
| `weapon.form.staff` | Cajado | existe |
| `weapon.form.rod` | Bastão | existe |

Não existem no código: Orbe, Cetro, Chakram.

A Maça é usada em pelo menos 8 armas do catálogo (por exemplo `weapon.type.tdo.guarda_primeiro_selo`, `weapon.type.nareth.guarda_referencia`, `weapon.type.varzeas.arma_dique`, `equipment.altos.campaign.p30.guarda_contraforte_final`). Cada uma precisa de nova forma quando a Maça sair.

## 2. Outros atributos de arma já definidos

Fonte: contrato de Weapon Metadata (`ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.0.0_FINAL.md`, em `.worktrees/asterion-proficiency-phase2b/`).

- Mãos: `weapon.hands.one` (1 mão) e 2H (2 mãos). Arma 2H bloqueia a mão secundária.
- Slot: `weapon.slot.main_only` (só mão principal) e `weapon.slot.secondary_only` (só mão secundária).
- Compatibilidade: `weapon.compat.melee` (corpo a corpo). Arco e Besta têm compatibilidade própria.
- A forma da arma serve só para nome, lore e visual. Ela não concede atributo, fórmula, proficiência nem restrição.

## 3. Proficiências nas fontes oficiais (GDD v1.6.0 e contrato de Weapon Metadata)

- Não existe proficiência global de arma por Classe.
- Não existem proficiências, perícias ou árvores globais de arma.
- O requisito de uma Arte vem da Fonte da Arte. Ele pode exigir "arma corpo a corpo compatível" ou "Arco/Besta".
- Cada item declara explicitamente as tags de compatibilidade que satisfaz. Arma desconhecida não satisfaz requisito específico.
- Tecelão, Oráculo e Luminar não recebem proficiência nem restrição de arma implícita.

Conclusão: nas fontes oficiais, NÃO há grupos "corpo a corpo / à distância / mágica" como proficiência de Classe. Essa divisão que o autor lembra veio do Codex e não está em nenhum arquivo.

## 4. Fase 2E (candidata, não canônica)

- Criou uma matriz 4×4 de proficiências, atrás da flag `PROFICIENCY_EQUIPMENT_V1_ENABLED` (desligada).
- A matriz real por Classe e os kits oficiais nunca foram carregados.
- Os 34 templates de Origem em `balanceamento/` (v1.4.0 a v1.9.1) usam o kit ANTIGO.
- Gates técnicos (snapshot do release, publicação canônica, importação, migration, flag, deploy) seguem NO-GO.

## 5. Kit de Origem novo (palavras do autor, 2026-11-13)

| Classe | Arma | Armadura | Pendência |
|---|---|---|---|
| Sentinela | Espada | Elmo, Couraça, Manoplas, Grevas Pesadas | sem Escudo |
| Errante | Adaga | 4 peças Leves | nenhuma |
| Vigia | Arco 2H | 4 Leves | nenhuma (inalterado) |
| Tecelão | Cajado 2H | 4 Vestes | nenhuma (inalterado) |
| Oráculo | somente Orbe (sem Bastão, sem Adaga) | a confirmar se perde as 4 Vestes | armadura |
| Luminar | Cetro no lugar da Maça | perde escudo e as 4 armaduras médias | confirmar se o kit é só o Cetro |

- Orbe e Cetro: armas de 1 mão. A Orbe vai na mão principal. Ambas podem ir na secundária.
- Números (nível 1, Comum) de Orbe e Cetro: não definidos.
- Personagem novo nasce sem kit no código atual (`src/` não concede nada na criação).

## 6. Categorias de armadura citadas

Aparecem nas anotações do kit: Leve, Média, Pesada e Veste (Elmo, Couraça, Manoplas, Grevas como peças). Não achei arquivo que defina formalmente as categorias de armadura nem quem pode usar cada uma. Confirmar.

## 7. O que o autor lembra do Codex (não está em arquivo)

- Divisão das armas em três grupos: corpo a corpo, à distância e mágica.
- Existência de formas como Chakram.
- Troca de proficiências em relação ao que está nos documentos.

## 8. Perguntas para refazer

1. Quais formas de arma entram em cada grupo (corpo a corpo, à distância, mágica)? Onde ficam Chakram, Orbe e Cetro?
2. Quais grupos cada Classe domina? E os Caminhos mudam isso?
3. Proficiência é regra (bloqueia equipar) ou só bônus?
4. Armaduras: quais categorias existem e qual Classe usa qual?
5. Qual forma substitui a Maça nas 8 armas do catálogo?
6. Números de Orbe e Cetro (nível 1, Comum).
7. Armaduras do Oráculo e do Luminar no kit novo.

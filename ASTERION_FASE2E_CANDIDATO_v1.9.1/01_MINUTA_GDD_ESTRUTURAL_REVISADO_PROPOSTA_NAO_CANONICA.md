# Minuta de revisão do GDD Estrutural v1.6.0
## PROPOSTA_NAO_CANONICA · revisão candidata para Game Design

**Estado:** minuta documental. Não altera nem substitui a Fonte Mestra v1.6.0 instalada.  
**Versão canônica futura:** não atribuída nesta minuta.  
**Base normativa de trabalho:** decisões expressamente homologadas pelo Game Design e matrizes aprovadas preservadas no pacote candidato v1.8.0.  
**Uso:** inserir ou substituir apenas os trechos indicados; todo o restante do GDD v1.6.0 permanece fora desta proposta.

## 1. Mapa preciso de alterações

| Seção vigente | Operação proposta |
|---|---|
| §24.1 Slots | Complementar: registrar Escudo como equipamento não-arma no slot Secundária e a incompatibilidade com Principal 2H. Manter os oito slots. |
| §24.2 Nível, categorias, armas e raridades | Substituir somente as afirmações de §24.2 que negam categorias mecânicas de proteção e Proficiências globais. Complementar com a lista de 15 Proficiências, a matriz natural por Classe, as regras de equipagem e a mistura livre de categorias. Preservar nível, raridade, aprimoramento e demais regras atuais. |
| §24.5 Equipment Validator | Complementar a lista de validações com a Proficiência exigida pelo item/categoria. Preservar a validação atômica do estado final já descrita. |
| Após §24.6 Materialização global de Equipamento | Inserir §24.7 com a composição aprovada dos seis kits de Origem, concessão única e restrições econômicas expressas. |
| §49.7 XP, Missões e Legado | Complementar com uma frase: Proficiências aprendidas permanecem após Legado. Não redefinir qualquer outra regra de Legado. |
| §49.8 Equipamentos, Runas e Encantamentos | Substituir os núcleos corporais pelos 16 vetores homologados, revogar o antigo total agregado fixo HP305/ATQ56/DEF33/AGI16 e manter os quatro totais corporais aprovados. Preservar fórmulas, raridades, secundários, Runas e Encantamentos vigentes. |
| §49.9 Saque, materiais e Desmontagem | Complementar com os pesos relativos v0.4 após os filtros de elegibilidade. Não alterar as chances globais de equipamento nem as tabelas de raridade. |
| §55.3 Armas × Artes × Equipamento | Substituir apenas os parágrafos que negam Proficiências de equipagem. Preservar a matriz de requisitos de Artes, que continua independente. |

## 2. Texto proposto para §24.1–§24.2

### §24.1 — complemento

O modelo continua com os oito slots oficiais. Escudo é equipamento **não-arma** de Arma Secundária. Exige a Proficiência Escudo e não pode coexistir equipado com uma arma 2H na Arma Principal. Escudo não recebe weapon_form, handedness ou compatibility tags.

### §24.2 — substituir os trechos incompatíveis

As categorias de proteção corporal são **Vestes, Leve, Média e Pesada**. Cabeça, Torso, Mãos e Pés declaram uma dessas categorias e exigem a Proficiência correspondente. Uma peça pode ser equipada quando o nível e a Proficiência exigida forem atendidos.

As dez classificações especiais aprovadas são: Véu do Bosque — Leve; Guarda do Berço Silente — Média; Peitoral do Fluxo Contido — Média; Guarda do Último Posto — Pesada; Capuz das Copas Suspensas — Vestes; Capuz dos Marcos Longos — Leve; Máscara da Salmoura — Média; Capuz do Vento Preso — Vestes; Capuz da Dupla Leitura — Leve; Máscara da Triagem Silenciosa — Vestes. A confirmação das identidades desses itens no registry de release continua pendente.

Proficiência é requisito para equipar. Por si só, não concede atributo, bônus numérico de combate, tag de Arte ou requisito de Arte. Raça e Caminho não concedem Proficiências naturais.

As quatro categorias podem ser misturadas livremente entre os quatro slots corporais, conforme as Proficiências do personagem. Não há bônus de conjunto, penalidade de peso/carga ou restrição adicional por combinação.

A forma da arma permanece descritiva. A Proficiência necessária para equipá-la é declarada separadamente na definição do item. Forma não concede Proficiência nem compatibility tag automaticamente. Os requisitos de Artes continuam declarados por cada Arte, conforme §55.3 e o contrato global de Weapon Metadata.

Todos os demais itens de §24.2 — requisito de nível, raridades, limite Mítico, aprimoramento, durabilidade e cosméticos — permanecem sem alteração.

### Lista de Proficiências de Equipamento

Armas: **Espada, Adaga, Maça, Machado, Martelo, Lança, Arco, Besta, Cajado e Bastão**.  
Equipamentos não-arma: **Escudo, Vestes, Leve, Média e Pesada**.

### Proficiências naturais por Classe

| Classe | Proficiências naturais |
|---|---|
| Sentinela | Espada, Machado, Martelo, Maça, Lança, Escudo, Média, Pesada |
| Errante | Espada, Adaga, Leve, Média |
| Vigia | Arco, Besta, Adaga, Leve, Média |
| Tecelão | Cajado, Bastão, Adaga, Vestes, Leve |
| Oráculo | Cajado, Bastão, Adaga, Vestes, Leve |
| Luminar | Cajado, Bastão, Maça, Espada, Escudo, Vestes, Média |

Proficiências naturais são concedidas gratuitamente conforme a Classe. Raça e Caminho não alteram esta matriz.

### Treinamento opcional v0.4 aprovado

O requisito de cada etapa é cumulativo. O custo é cobrado por cada Proficiência nova aprendida, não pela etapa. Proficiências naturais e já possuídas não são cobradas.

| Etapa | Requisito cumulativo | Proficiências que podem ser aprendidas | Custo por Proficiência |
|---|---|---|---:|
| I | Nível 10 + P6 concluída | Espada, Adaga, Bastão, Vestes, Leve | 250 Coroas |
| II | Nível 20 + P12 concluída | Maça, Cajado, Escudo, Média, Pesada | 400 Coroas |
| III | Nível 30 + P18 concluída | Machado, Arco, Besta | 550 Coroas |
| IV | Nível 40 + P24 concluída | Martelo, Lança | 700 Coroas |

Treinamento é opcional. Proficiências aprendidas permanecem depois do Legado. A implementação deve respeitar a aquisição transacional e idempotente aprovada, sem acrescentar regras de interface, local de treinamento ou progressão além dos requisitos acima.

## 3. Texto proposto para §24.5 — Equipment Validator

Acrescentar à lista existente: **Proficiência exigida pela definição do item ou pela categoria de proteção**. A validação de Proficiência é independente de compatibility tags e dos requisitos das Artes. Preservar os demais requisitos e o comportamento de validação de estado final já definidos em §24.5.

## 4. Novo §24.7 — Equipamentos de Origem

O catálogo de Equipamentos de Origem contém 34 templates distribuídos nos seis kits de Classe abaixo. Esta tabela registra somente a composição aprovada por Classe e slot; os template IDs candidatos, nomes e atributos individuais permanecem exatamente nas matrizes aprovadas, sem declaração de validação em release.

| Classe | Principal | Secundária | Cabeça, Torso, Mãos e Pés | Acessório | Artefato |
|---|---|---|---|---|---|
| Sentinela | Espada | Escudo | quatro peças Pesadas | vazio | vazio |
| Errante | Espada | Adaga | quatro peças Leves | vazio | vazio |
| Vigia | Arco 2H | vazio | quatro peças Leves | vazio | vazio |
| Tecelão | Cajado 2H | vazio | quatro peças de Vestes | vazio | vazio |
| Oráculo | Bastão 1H | Adaga | quatro peças de Vestes | vazio | vazio |
| Luminar | Maça | Escudo | quatro peças Médias | vazio | vazio |

A distribuição aprovada totaliza 34 templates: seis para Sentinela, seis para Errante, cinco para Vigia, cinco para Tecelão, seis para Oráculo e seis para Luminar. Nenhum template, ID, valor individual, vínculo ou requisito de slot é criado ou alterado por esta tabela.

O kit correspondente à Classe é concedido uma única vez durante a criação do personagem. Legado não concede o kit novamente. Recuperação não concede novamente o kit, não gera outro exemplar e não pode gerar valor econômico. Esta minuta não define o procedimento de recuperação.

Equipamentos de Origem não podem ser vendidos, trocados, listados para venda ou troca, desmontados, reembolsados nem gerar cashback. Também não podem ser aprimorados, rerrolados, receber Runas ou receber Encantamentos. Estas proibições aplicam-se às operações econômicas e de customização indicadas; não estabelecem valor, fluxo de interface ou migração.

## 5. Texto proposto para §49.7 — Legado

Acrescentar ao parágrafo de Legado: **Proficiências aprendidas permanecem após o Legado.** Nenhuma outra regra de transição, reset, equipamento, inventário ou recuperação é modificada por esta inclusão.

## 6. Texto proposto para §49.8 — núcleos

Os valores abaixo são os núcleos de referência **Nv.60, Comum, +0**, na ordem **HP / ATQ / DEF / AGI**. As fórmulas vigentes de nível, raridade e aprimoramento do próprio §49.8 continuam aplicáveis sem alteração.

| Categoria | Cabeça | Torso | Mãos | Pés | Total corporal (quatro slots) |
|---|---|---|---|---|---|
| Vestes | 35/2/5/0 | 85/3/10/0 | 0/11/4/0 | 38/3/0/8 | 158/19/19/8 |
| Leve | 40/0/5/3 | 80/0/8/10 | 0/11/0/4 | 53/0/4/6 | 173/11/17/23 |
| Média | 45/0/6/0 | 95/0/12/0 | 0/10/5/0 | 60/0/0/8 | 200/10/23/8 |
| Pesada | 40/0/7/0 | 91/0/13/0 | 26/3/10/0 | 63/0/3/3 | 220/3/33/3 |

Fica revogado o antigo total agregado fixo de conjunto HP305/ATQ56/DEF33/AGI16. Ele não é um total garantido nem obrigatório para um loadout. Os quatro totais da tabela acima são exclusivamente a soma dos slots corporais Cabeça, Torso, Mãos e Pés de um conjunto puro na categoria indicada; não incluem Principal, Secundária, Acessório ou Artefato.

As quatro categorias podem ser misturadas livremente conforme as Proficiências do personagem. O núcleo corporal total resulta das peças efetivamente equipadas. Não há bônus de conjunto, penalidade de peso ou restrição adicional à mistura. Permanecem vigentes os demais núcleos e fórmulas dos slots não corporais, os pools de atributos secundários e as regras de Runas e Encantamentos.

### Núcleo de Escudo

Escudo, como item não-arma de Secundária, usa **HP 25 / ATQ 0 / DEF 10 / AGI 0**, referência Nv.60, Comum, +0. Seu Bloqueio inerente é **0**. A presença do Escudo não concede chance de Bloqueio por si só. O núcleo de armas de Secundária permanece inalterado.

## 7. Texto proposto para §49.9 — pesos de Saque v0.4

Aplicar estes pesos por template somente depois dos filtros de disponibilidade e elegibilidade de raridade. Renormalizar entre templates elegíveis dentro do grupo. Se o grupo não tiver template elegível, removê-lo da seleção; manter a regra vigente de seleção dos grupos não vazios.

| Grupo | Templates | Peso relativo por template |
|---|---|---:|
| Principal | existentes | 30 |
| Principal | novos | 20 |
| Cabeça, Torso, Mãos, Pés | existentes | 30 |
| Cabeça, Torso, Mãos, Pés | novos | 20 |
| Secundária | armas existentes | 60 |
| Secundária | Escudos novos | 40 |
| Acessório e Artefato | catálogo existente | 100 |

As chances globais de obtenção de Equipamento e as distribuições globais de raridade permanecem inalteradas. Recompensas de Campanha e itens de Receita especial ficam fora do Saque normal, salvo inclusão explícita. A elegibilidade individual por template × raridade continua dependente de decisão/evidência própria; os pesos não a concedem.

O §24.6 vigente já define a inelegibilidade estrutural de Torso Mítico quando o pool de três atributos não comporta quatro secundários distintos. Os 24 pares aprovados continuam registrados na matriz candidata e só poderão ser associados a identidades de release após sua conciliação.

## 8. Texto proposto para §55.3 — Armas × Artes × Equipamento

Substituir somente os parágrafos iniciais que afirmam que não existem Proficiências globais de arma. Texto proposto:

> Proficiência de Equipamento determina se o personagem pode equipar o item; não concede bônus de combate e não satisfaz requisitos de Artes. Cada definição de arma declara sua Proficiência de equipagem separadamente de weapon_form, handedness, slot e compatibility tags. A forma descreve o item e não concede Proficiência nem tag automaticamente.
>
> Cada Arte mantém seu requisito explícito NONE ou TAG_ANY_OF, declarado pela respectiva fonte. Proficiência e compatibility tags são eixos independentes. As regras de Arte, a tabela de requisitos das Artes vigente e a avaliação de tags permanecem inalteradas.
>
> Proficiências naturais são concedidas pela Classe conforme a matriz da §24.2. Raça e Caminho não as concedem. Arma 2H continua ocupando Principal e bloqueando Secundária.

A tabela completa de Artes de §55.3 permanece sem alteração. Não se inferem tags por forma, Classe, Caminho ou nome.

## 9. Limites desta minuta

- As seis Fontes Regionais e os dez registros de classificação especial não são modificados por este documento.
- Os 100 atributos individuais aprovados são preservados nas matrizes regionais candidatas; esta minuta não altera valores, IDs, receitas ou vínculos.
- Nenhum dos 226 template IDs é declarado validado em release.
- Os 24 pares Torso/Mítico permanecem exclusões aprovadas na matriz candidata; não são promovidos a IDs de release.
- Não se acrescenta ao GDD a proteção candidata que impede descarte quando o último loadout funcional seria perdido; o registro de Origem v1.4.0 classifica essa guarda como candidata sujeita a validação transacional.
- Nenhuma regra de comércio além das proibições listadas, nenhuma interface, sistema de migração, alteração de dados persistidos ou detalhe de implementação é criada nesta minuta.

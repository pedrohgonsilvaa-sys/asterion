# RASCUNHO — Delta da Fonte Visual/UI para Terras do Ocaso v1.0.18

> **Aplicado em 2026-11-14** como seção 66 de `ASTERION_UI_DECISOES_2026-10-13_FINAL_SYNC_v1.6.0_TDO_v1.0.15_VALES_v1.0.6.md`, com as decisões extras do autor (L3, L4/decisão 11, L5). Este rascunho fica como histórico; a autoridade é a Fonte Visual/UI.

**Status:** RASCUNHO para o autor. Não é canônico. **A Fonte Visual/UI (`ASTERION_UI_DECISOES_2026-10-13_FINAL_SYNC_v1.6.0_TDO_v1.0.15_VALES_v1.0.6.md`) não foi editada.** Este delta só entra na Visual/UI quando o autor aprovar e o `game-director` sincronizar.<br>
**Data:** 2026-11-14<br>
**Origem:** seção 9(b) da proposta v1.0.18 (revisão 6), seção 33 da Fonte regional `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_FINAL.md` e decisões do autor de 2026-11-14.<br>
**Regra:** a Visual/UI define estrutura de telas e texto; regra mecânica e números vêm da Fonte Mestra e da Fonte regional. Rótulos finais dos botões e posição na tela são decisão da Visual/UI; os rótulos abaixo são sugestão.

---

## 1. Delta de apresentação — mapa das Terras do Ocaso

1. **A tela do Refúgio do Ocaso é o menu do mapa (hub).** É aberta a partir do Menu Principal e não o substitui.
2. **Ações da tela do Refúgio:** **Explorar**, **Caçar** (abre a lista de Locais descobertos com Caçada; o jogador escolhe onde caçar), **Masmorra (Covil)** (só as descobertas), **Missões**, **Personagem**, e a lista de Locais descobertos para entrar.
3. **Tela do Local:** **Caçar**, **Desbravar**, **Ronda** (só após a primeira vitória manual no Local) e **Voltar ao Refúgio**. A Estrada, após P1, é Local como os outros. Depois de escolher um Local em Caçar, o personagem passa a estar nele.
4. **Travessia dos Braseiros** não aparece nas Terras do Ocaso. Regra global intacta. Não há viagem rápida entre Braseiros.
5. **Tela de resultado do Explorar:** mostra o Local revelado, o XP de descoberta e que ele agora aparece no Refúgio. O personagem continua no Refúgio. Sem custo de Vigor (a tela não mostra Vigor). Sem Local para revelar, Explorar aparece indisponível com texto próprio. Clique antes de 3 s do anterior é recusado sem efeito (sugestão de aviso curto: "Aguarde um instante.").
6. **Câmara do Poente:** aparece na lista de Locais descobertos, sem Caçar, Desbravar nem Ronda, e tem **Voltar ao Refúgio**. Telas de entrada na seção 2.
7. **Local sem inimigos elegíveis (só Grupo):** texto "nada para caçar aqui ainda" ou equivalente, **apenas** para pool vazio por outro motivo. Para `unlock_level`, vale a mensagem da seção 3.
8. **Ao abrir o jogo**, o personagem aparece onde estava (sem teletransporte ao Refúgio).
9. Rótulos finais dos botões e posição na tela: decisão da Visual/UI.

## 2. Tela da Câmara do Poente, antes e depois da P6

A Câmara tem **dois textos de entrada**. A Missão só muda o texto exibido: a UI lê se o **personagem que vê a tela** concluiu P6. Concluir P6 **não libera nem revela o Local** (a Câmara já foi descoberta por Explorar, no sorteio uniforme).

### 2.1 Resultado de Explorar ao descobrir a Câmara (neutro)

- Título do Local: `Câmara do Poente`.
- Texto de descoberta: **neutro**; não usa "Âncora" e não descreve a estrutura central. Texto a escrever pelo narrative-designer (lacuna U1).
- Mesmo formato dos outros Locais (Local revelado, XP de descoberta, "agora aparece no Refúgio").

### 2.2 Entrada na Câmara — P6 não concluída

```
🕯 Câmara do Poente

[[TEXTO_CAMARA_PRE_P6]]

[Voltar ao Refúgio]
```

- O marcador `[[TEXTO_CAMARA_PRE_P6]]` será um recinto fechado e neutro: **sem a palavra "Âncora"** e **sem descrever a estrutura central**.
- Sem botões de Caçar, Desbravar ou Ronda.
- Se P6 está disponível e o jogador está aqui na Etapa 2, a ação da Missão tem prioridade na tela (padrão de Missões da Visual/UI).

### 2.3 Entrada na Câmara — P6 concluída

```
🕯 Câmara do Poente

[[TEXTO_CAMARA_POS_P6]]

[Voltar ao Refúgio]
```

- O marcador `[[TEXTO_CAMARA_POS_P6]]` será um texto que usa o nome **Âncora do Poente**.
- Sem botões de Caçar, Desbravar ou Ronda. O Chefe Vigia Partido não é reencenado por esta tela.

### 2.4 Regras de exibição

- A escolha do texto é por personagem (progresso de Missão é individual). Confirmar na lacuna U2.
- O ícone `🕯` acima é sugestão; a Visual/UI decide o ícone.
- Se o marcador ainda não foi substituído, a UI não inventa texto: mostra o marcador só em ambiente de desenvolvimento e nunca em produção.

## 3. Mensagem de bloqueio da Caçada em Grupo (decisão 11)

Quando, em Grupo, **nenhuma criatura do Local é elegível para todos os membros**, a Caçada **não abre** e a interface cita todos os membros que não cumprem o `unlock_level`.

Sugestão de texto (a Visual/UI decide o texto final):

```
⚠ Caçada indisponível

{Nome do membro} ainda não cumpre o nível mínimo de nenhuma criatura deste Local.

[Voltar]
```

- `{Nome do membro}` é o personagem que não cumpre. Se mais de um membro não cumpre, ver lacuna U3 (recomendo listar todos).
- Não mostra número de nível mínimo se a Visual/UI preferir esconder; mostrar o número é decisão da Visual/UI (a Fonte regional tem os valores em §10.2 a §10.5).
- Esta mensagem **não** reaproveita "nada para caçar aqui ainda", que fica para outros casos de pool vazio.
- Em Solo esta mensagem nunca aparece (o pool é completo desde o primeiro acesso).

## 4. Textos de estado do Explorar

| Estado | Texto (sugestão) |
|---|---|
| Há Local para revelar | botão `Explorar` |
| Todos os Locais descobertos | `Não há mais o que explorar por aqui.` (indisponível) |
| Clique antes de 3 s | `Aguarde um instante.` |
| Etapa de Missão aguardando Local não descoberto | `Explore para encontrar este lugar.` (não bloqueia sem saída: Explorar não falha) |

## Lacunas para o autor

- **U1.** Resolvida em 2026-11-14: os textos de descoberta, pré-P6 e pós-P6 da Câmara estão escritos na Fonte regional v1.0.18_FINAL, §3.6.
- **U2.** O texto pré/pós P6 lê o P6 de quem vê (por personagem)? Recomendo sim.
- **U3.** Decisão 11: se mais de um membro não cumpre, citar todos ou só um? Recomendo todos.
- **U4.** Mostrar ou não o nível mínimo na mensagem de bloqueio. Recomendo não mostrar o número e só o nome do membro, para manter a regra de "progresso oculto" do Bestiário (o `unlock_level` é de criatura).
- **U5.** Rótulos finais, ícones e posição dos botões: decisão da Visual/UI.
- **U6.** Durante P1 em andamento, Caçada e Desbravar da Estrada ficam escondidos ou disponíveis? Recomendo manter o fluxo do tutorial (escondidos até concluir P1).
- **U7.** Entrada de Códice "Câmara do Poente": gatilho e texto não podem citar "Âncora" antes de P6.

## Critérios de aceite

1. A tela do Refúgio mostra Explorar, Caçar, Masmorra (Covil), Missões, Personagem e a lista de Locais descobertos; não mostra Travessia dos Braseiros.
2. A tela do Local mostra Caçar, Desbravar, Ronda (só após a primeira vitória manual no Local) e Voltar ao Refúgio.
3. Caçar no Refúgio lista só Locais descobertos com Caçada; a Câmara não aparece.
4. Explorar: resultado mostra Local revelado, XP e "aparece no Refúgio"; sem Vigor; clique antes de 3 s recusado; sem Local restante, indisponível com texto próprio.
5. Câmara descoberta: o texto de descoberta é neutro e não contém "Âncora".
6. Câmara com P6 não concluída: a tela usa `[[TEXTO_CAMARA_PRE_P6]]`; o texto não contém a palavra "Âncora" e não descreve a estrutura central.
7. Câmara com P6 concluída: a tela usa `[[TEXTO_CAMARA_POS_P6]]`; o texto contém "Âncora do Poente".
8. Concluir P6 muda só o texto da tela; não altera a lista de Locais descobertos nem cria `LocationDiscovery`.
9. A Câmara não tem botões de Caçar, Desbravar nem Ronda, e tem Voltar ao Refúgio.
10. Grupo sem criatura elegível para todos: a Caçada não abre e a mensagem cita o membro que não cumpre o `unlock_level`; a mensagem "nada para caçar aqui ainda" não aparece nesse caso. Em Solo a mensagem de bloqueio nunca aparece.
11. Ao abrir o jogo, a tela mostra o Local onde o personagem estava.
12. A Fonte Visual/UI de 2026-10-13 permanece sem alteração até a aprovação do autor.

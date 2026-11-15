# Pendências de QA

Lista de medições e verificações que o QA ainda deve fazer. Cada item diz o que medir, o limite, como medir e o que bloqueia.

## QA-001. Taxa de vitória real do Nv.1 (TDO v1.0.18)

- **Registrada em:** 2026-11-14
- **Estado:** BLOQUEADA. Só começa quando houver implementação da v1.0.18 no código (inimigo no nível do Local, Explorar, Estrada pós-P1). Hoje não há o que simular.
- **Fontes:**
  - `docs/specs/AUDITORIA_FARM_XP_TDO_v1.0.18_2026-11-14.md` (tabela `r`, R2.4). A PROPOSTA v1.0.18, que tinha a seção 7.4, foi apagada em 2026-11-14; o conteúdo vale pela FINAL.
  - `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_FINAL.md`, §33.15, lacuna L6.

### O que medir

Taxa de vitória real (não a razão indicativa `r`) do personagem Nv.1 em dois pontos:

1. **(a) Estrada logo após a P1.** Inimigo no nível do Local (`max_enemy_level` 3 a 5). `r` indicativa: 0,74 a 0,86 (jogador perde na média; pode estar dura demais para o início). Medir por classe, com e sem Artes e consumíveis de P1.
2. **(b) Locais Nv.9–10 (Ruínas), Nv.1 solo.** `r` indicativa: 0,52 a 0,56; derrota provável em Solo. Confirmar se é a barreira pretendida (soulslike) e se Caçada/Desbravar não paga XP desproporcional a quem ganha por sorte. Referência da seção 7.4: Comum Nv.9 = 450 XP (9,4% do Nv.1→2); Elite Nv.9 = 1.230 XP (25,6%).

A tabela `r` da auditoria (R2.4) é só indicativa: golpe básico, inimigo neutro, sem Artes, Variante ou consumíveis.

### Critério / limite de aprovação

**LACUNA.** A seção 7.4 e a L6 dizem "sem número de aprovação definido pelo autor". Não há limiar de taxa de vitória. O QA mede e reporta os números; não aprova nem reprova sem o autor definir o limite. Se o caso (a) mostrar dureza excessiva, a correção é decisão do autor (a fonte não propõe número).

### Como medir (quando houver código)

- Simulação de combate com o motor real do jogo (não a fórmula indicativa), Nv.1, por classe.
- Caso (a): com e sem Artes e consumíveis de P1.
- Caso (b): Solo, Nv.1, inimigos Comum e Elite do Local Nv.9–10; registrar também o XP pago em vitória.
- Número de amostras: **LACUNA**, a fonte não define. Propor um tamanho ao autor antes de rodar e fixar semente/crítico para o resultado ser reproduzível.
- Reportar: taxa de vitória por classe e por caso, XP por vitória, e a comparação com as `r` indicativas.

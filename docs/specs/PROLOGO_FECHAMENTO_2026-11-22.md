# Fechamento do Prólogo + correções da Criação (2026-11-22)

Decisão atual do produto (mensagem do autor); prevalece sobre texto antigo.

- Cenas da estrada: `src/asterion/bot/prologue_ui.py` (`SCENES`). Botões em coluna única; combate inicia direto por `prologue:continue`.
- Primeiro combate sorteia `dog_cinereo` OU `corvo_fuligem` (`domain/prologue.py: PROLOGUE_ENEMIES`, `application/prologue.py: choose_enemy_id`). P1 não muda.
- Tela de combate: título `⚔️ O Primeiro Confronto`, HUD sem nível, barra de 9 🟩, histórico mecânico por turno; linha narrativa só no Turno 1.
- Vitória/Derrota → `pl:chama` → Braseiro → Descansar → Fim do Prólogo → `menu:back`.
- Nome sempre de `character.name`. Teste varre `src/` e `tests/` por nome fixo.
- Criação: aviso `⚠️ Gênero, Raça e Classe não poderão ser alterados após a criação do personagem.`
- Arte do personagem: `char.<raça>.<gênero>.<classe>`. `build_asset_images` não serve classe cujo arquivo seja cópia byte a byte de outra classe da mesma raça/gênero. Único fallback permitido: retrato neutro `char.<raça>.<gênero>` (com log de aviso).
- Asset pendente: `assets/characters/default classes/hem-m-vigia.jpg` é cópia de `hem-m-errante.jpg`; precisa da arte real do Vigia Hemário masculino.

## Timer global de turno (10s)

- Motor: `domain/turn_clock.py` (`TURN_SECONDS = 10`, relógio injetável) + `Combat.turn_deadline` (carimbado em `_begin_turn`, persistido no snapshot). Servidor é a autoridade.
- `act` e `use_combat_consumable`: ação após o prazo não é aceita; o turno vencido vira `pass_turn` (perde o turno) e abre novo prazo. `expire_turn` é idempotente (versão do snapshot).
- Prólogo: `PrologueService` também expira o turno em `resume`. Concorrência protegida pelo lock da linha + versão.
- `arena.TURN_TTL` (PvP, Batalha de Guildas) e `GROUP_HUNT_TURN_TIMEOUT_SECONDS` agora = `TURN_SECONDS`.
- HUD: `prologue_ui.render_standard_hud` (prólogo). Linha `🌐 Turno N · ⏱️ MM:SS` (monoespaçada) em todas as telas de combate de `combat_ui._render_combat`.
- Limite conhecido: o relógio só atualiza quando a tela é renderizada; sem tick automático (Telegram limita edições).

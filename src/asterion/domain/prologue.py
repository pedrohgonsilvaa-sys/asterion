"""Content configuration, independent of the duel engine and Telegram handlers."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import Action, Combat, Fighter, Tutorial, start_combat
from asterion.domain.combat_math import Stats, class_stats, enemy_stats, racial_stats

D = Decimal
RULESET = "gdd-1.4.2-baseline-1.0"
CONTENT_ID = "prologue_first_combat"
COMBAT_STAGE = "cinzas_na_estrada:first_combat"
POST_COMBAT_STAGE = "cinzas_na_estrada:ready_for_first_brazier"
FAILED_STAGE = "cinzas_na_estrada:first_combat_defeat"
REWARD_XP = 320
LEVEL_TWO_XP = 4800
CATEGORY_COMMON = Stats(D("0.70"), D("0.82"), D("0.90"), D("0.95"))
PREDATOR = Stats(D("0.90"), D("1.10"), D("0.90"), D("1.20"))
PROLOGUE_MULTIPLIERS = Stats(D("0.60"), D("0.55"), D("0.75"), D("0.65"))
FIRST_ARTS = {
    "sentinela": ("🗡️ Golpe de Guarda", "1.10"),
    "errante": ("🗡️ Corte Veloz", "1.15"),
    "vigia": ("🏹 Disparo Preciso", "1.15"),
    "tecelao": ("🪄 Fio Cortante", "1.20"),
    "oraculo": ("🔮 Sinal Funesto", "1.05"),
    "luminar": ("☀️ Fulgor", "1.10"),
}


def first_art(character_class: str, blocked_opportunities: int) -> Action:
    name, coefficient = FIRST_ARTS[character_class]
    return Action(
        "art",
        name,
        D(coefficient),
        blocked_opportunities,
        D("0.08") if character_class == "oraculo" else D(0),
        2 if character_class == "oraculo" else 0,
    )


@dataclass(frozen=True)
class PrologueProfile:
    enemy: Stats
    art_blocked_opportunities: int

    def create(
        self,
        combat_id: UUID,
        name: str,
        character_class: str,
        race: str,
        hp: Decimal,
    ) -> Combat:
        stats = racial_stats(class_stats(character_class, 1), race)
        state = Combat(
            combat_id,
            RULESET,
            fighters={
                "player": Fighter("player", name, 1, stats, hp, race, character_class),
                "enemy": Fighter("enemy", "🐺 Cão Cinéreo", 1, self.enemy, self.enemy.hp),
            },
            player_actions={
                "attack": Action("attack", "⚔️ Atacar", D(1)),
                "art": first_art(character_class, self.art_blocked_opportunities),
            },
            enemy_actions={
                "bite": Action("bite", "Mordida Cinérea", D(1)),
                "charge": Action("charge", "Investida Cinérea", D("1.20")),
            },
            ai_cycle=("bite", "bite", "charge"),
            tutorial=Tutorial({"attack": "bite", "defend": "charge"}),
            flavor=(
                "Um rosnado rompe o silêncio da estrada. Entre as cinzas, uma criatura "
                "faminta avança para impedir sua passagem."
            ),
            opening_log="🐺 Cão Cinéreo bloqueia o caminho.",
        )
        return start_combat(state)


# CD2 used in N blocks N+1 and is available in N+2 (Fonte Mestra §10.2).
PROFILE = PrologueProfile(enemy_stats(1, CATEGORY_COMMON, PREDATOR, PROLOGUE_MULTIPLIERS), 1)

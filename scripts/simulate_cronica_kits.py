"""Etapa C6 da Crônica I: as 6 Classes contra os 9 kits cr01 (proposta v0.2 §11.3–§11.5).

Simulação determinística: cada luta usa um ``combat_id`` derivado de uma seed fixa, e o
motor sorteia a partir dele (``combat_math``). Nada é reimplementado: a luta é montada com
``create_creature_party_combat`` + ``configure_encounter`` (Encontros) ou
``configure_compasso`` (O Compasso, uma luta por Fase do Evento), como o jogo faz.

Personagem de referência: sem equipamento, Raça ``remanescente``, HP cheio e o kit
inicial da Classe. É o mesmo referencial do GDD §49.6 (inimigos medidos contra o
personagem de referência). Duas políticas:

- ``basico``: só Ataque Básico (o piso de viabilidade Solo do §11.1.6);
- ``kit``: usa a Arte quando o motor deixa, senão Ataque Básico.

O Compasso é medido por Fase com 1 participante (HP ``N^0,88`` com N=1). No jogo, o HP é
compartilhado entre os participantes; aqui a coluna mostra a luta Solo de cada Fase.

Uso::

    PYTHONPATH=src python scripts/simulate_cronica_kits.py --runs 200 --out tabela.md
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from asterion.domain.chronicle_encounters import configure_encounter, enemy_specs
from asterion.domain.chronicle_events import configure_compasso
from asterion.domain.combat import Combat, act, allowed_actions
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.creation import CLASSES
from asterion.domain.road import (
    CR01_AGUARDA_RESPOSTA,
    CR01_CARREGADOR_REPETIDO,
    CR01_ESCRIBA_REPETIDO,
    CR01_GUARDA_REPETIDA,
    CR01_MARCADOR,
    CR01_MESTRE_DE_TURNO,
    CR01_MULTIDAO_REPETIDA,
    CR01_O_COMPASSO,
    CR01_REPETIDOR,
    CreatureCombatantSpec,
    create_creature_party_combat,
    creature_for,
)
from asterion.domain.world_events import boss_engine_multipliers

D = Decimal
SEED = "asterion:c6:cronica-kits:v1"
RACE = "remanescente"
MAX_PLAYER_ACTIONS = 200
LEVELS = (5, 10, 30, 60)
POLICIES = ("basico", "kit")
ALIVE_HP = D(10**9)  # kept-alive runs: no single action can defeat the player


def _max_hp(character_class: str, level: int) -> Decimal:
    """Full HP at creation: a faster enemy can act before the player's first action."""
    return D(resolve_combat_stats(character_class, level, RACE, None, None, ()).hp)


@dataclass(frozen=True)
class Kit:
    name: str
    build: Callable[[str, int, str], Combat]


def _encounter(creature) -> Callable[[str, int, str], Combat]:
    def build(character_class: str, level: int, seed: str) -> Combat:
        return create_creature_party_combat(
            uuid5(NAMESPACE_URL, seed),
            "Sim",
            character_class,
            RACE,
            _max_hp(character_class, level),
            enemy_specs(creature, level),
            player_level=level,
            configure_combat=configure_encounter,
        )

    return build


def _compasso(phase: int) -> Callable[[str, int, str], Combat]:
    def build(character_class: str, level: int, seed: str) -> Combat:
        boss = CreatureCombatantSpec(
            CR01_O_COMPASSO, level, "enemy", stat_multipliers=boss_engine_multipliers(1)
        )
        return create_creature_party_combat(
            uuid5(NAMESPACE_URL, seed),
            "Sim",
            character_class,
            RACE,
            _max_hp(character_class, level),
            (boss,),
            player_level=level,
            configure_combat=lambda state: configure_compasso(state, phase, resonance=True),
        )

    return build


KITS: tuple[Kit, ...] = (
    Kit("Repetidor", _encounter(CR01_REPETIDOR)),
    Kit("Marcador", _encounter(CR01_MARCADOR)),
    Kit("Guarda Repetida", _encounter(CR01_GUARDA_REPETIDA)),
    Kit("Carregador Repetido", _encounter(CR01_CARREGADOR_REPETIDO)),
    Kit("Multidão Repetida", _encounter(CR01_MULTIDAO_REPETIDA)),
    Kit("Escriba Repetido", _encounter(CR01_ESCRIBA_REPETIDO)),
    Kit("Mestre de Turno", _encounter(CR01_MESTRE_DE_TURNO)),
    Kit("O Que Aguarda Resposta", _encounter(CR01_AGUARDA_RESPOSTA)),
    Kit("O Compasso F1", _compasso(1)),
    Kit("O Compasso F2", _compasso(2)),
    Kit("O Compasso F3", _compasso(3)),
)
# Published regional creatures, same level and same reference character, for comparison.
CONTROLS: tuple[Kit, ...] = tuple(
    Kit(
        f"controle: {creature_for(cid).name} ({creature_for(cid).category})",
        _encounter(creature_for(cid)),
    )
    for cid in ("profanador_calcinado", "custodio_sem_rosto", "guardiao_lapides", "sem_nome")
)
ALL_KITS = KITS + CONTROLS
KITS_BY_NAME = {kit.name: kit for kit in ALL_KITS}


@dataclass(frozen=True)
class Outcome:
    win: bool
    ttk: int  # player actions to defeat the enemy with the player kept alive
    pressure: Decimal  # damage taken per player action, as a fraction of max HP


def _choose(combat: Combat, policy: str) -> str:
    return "art" if policy == "kit" and "art" in allowed_actions(combat) else "attack"


def real_fight(combat: Combat, policy: str) -> bool:
    actions = 0
    while not combat.result and actions < MAX_PLAYER_ACTIONS:
        combat = act(combat, _choose(combat, policy), target_id="enemy")
        actions += 1
    return combat.result == "victory"


def kept_alive_fight(combat: Combat, policy: str) -> tuple[int, Decimal]:
    """TTK and pressure: the player is healed back to full before each action."""
    taken = D(0)
    actions = 0
    opening = combat.fighters["player"]
    taken += opening.stats.hp - D(opening.hp)  # enemy opening, when it is faster
    while not combat.result and actions < MAX_PLAYER_ACTIONS:
        combat.fighters["player"].hp = ALIVE_HP
        combat = act(combat, _choose(combat, policy), target_id="enemy")
        actions += 1
        taken += ALIVE_HP - D(combat.fighters["player"].hp)
    return actions, taken / actions / D(combat.fighters["player"].stats.hp)


def fight(build: Callable[[str, int, str], Combat], args: tuple[str, int, str, str]) -> Outcome:
    character_class, level, seed, policy = args
    win = real_fight(build(character_class, level, seed), policy)
    ttk, pressure = kept_alive_fight(build(character_class, level, seed), policy)
    return Outcome(win, ttk, pressure)


@dataclass(frozen=True)
class Cell:
    win_rate: float
    ttk: float
    actions_to_die: float

    def render(self) -> str:
        return f"{self.win_rate:.0%} · {self.ttk:.1f} · {self.actions_to_die:.1f}"


def _cell_job(job: tuple[str, str, int, str, int]) -> tuple[tuple[str, str, int, str], Cell]:
    kit_name, character_class, level, policy, runs = job
    build = KITS_BY_NAME[kit_name].build
    job_key = f"{kit_name}:{character_class}:{level}"
    outcomes = [
        fight(build, (character_class, level, f"{SEED}:{job_key}:{i}", policy)) for i in range(runs)
    ]
    pressure = sum(item.pressure for item in outcomes) / runs
    cell = Cell(
        sum(item.win for item in outcomes) / runs,
        sum(item.ttk for item in outcomes) / runs,
        float(1 / pressure) if pressure else float("inf"),
    )
    return (kit_name, character_class, level, policy), cell


def table(runs: int, levels: tuple[int, ...], policies: tuple[str, ...], jobs: int) -> str:
    work = [
        (kit.name, character_class, level, policy, runs)
        for policy in policies
        for level in levels
        for kit in ALL_KITS
        for character_class in CLASSES
    ]
    with ProcessPoolExecutor(jobs) as pool:
        cells = dict(pool.map(_cell_job, work))
    lines = [
        f"Seed `{SEED}`, {runs} lutas por célula. Célula: **vitória%** (luta real) · "
        "**TTK** (ações do jogador para derrotar o inimigo, jogador mantido vivo) · "
        "**ações até morrer** (HP máximo ÷ dano recebido por ação). Personagem de "
        f"referência sem equipamento, Raça `{RACE}`. Linhas `controle:` são criaturas "
        "regionais já publicadas, no mesmo nível, para comparação.",
        "",
    ]
    for policy in policies:
        for level in levels:
            lines += [
                f"### Política `{policy}` · Nv.{level}",
                "",
                "| Kit | " + " | ".join(CLASSES) + " |",
                "|---|" + "---|" * len(CLASSES),
            ]
            for kit in ALL_KITS:
                row = [cells[(kit.name, c, level, policy)].render() for c in CLASSES]
                lines.append(f"| {kit.name} | " + " | ".join(row) + " |")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=200)
    parser.add_argument("--levels", type=int, nargs="*", default=list(LEVELS))
    parser.add_argument("--policies", nargs="*", default=list(POLICIES))
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--out")
    args = parser.parse_args()
    text = table(args.runs, tuple(args.levels), tuple(args.policies), args.jobs)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()

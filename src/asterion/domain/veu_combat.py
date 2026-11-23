"""Resolução de rodada de A Ruptura do Véu (domínio puro, sem banco nem motor).

Modelo (v1.3.0 §13, §17): a IA do inimigo decide antes da janela; todas as ações válidas são
calculadas a partir do estado inicial da rodada e aplicadas em lote. O dano dos jogadores
(Atacar e Artes) vem do motor de combate existente, medido por ação pela camada de aplicação;
aqui só entram a soma em lote, a Barreira/Defender, a resposta inimiga e as mortes.

Decisões técnicas (a fonte não define; comportamento existente mais próximo):

- Desempate da IA: ação válida escolhida por ``seed`` entre as que não estão em recarga.
- Defender reduz o dano recebido em 45% (``combat.py``, ``defender_reduction``).
- Dano inimigo usa ``combat_math.direct_damage`` com o ATQ e o nível de referência do Evento.
- Debuffs dos kits sobre jogadores não persistem entre rodadas nesta primeira versão
  (só a parte de dano é aplicada); buffs próprios e Barreiras do inimigo duram os turnos do kit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat_math import direct_damage
from asterion.domain.veu_bestiary import (
    BARRIER_DURATION_TURNS,
    EVENT_REFERENCE_LEVEL,
    ActionKind,
    VeuAction,
    creature,
)

D = Decimal
DEFEND_MITIGATION = D("0.45")


@dataclass(slots=True)
class EnemyUnit:
    code: str
    hp: Decimal
    max_hp: Decimal
    attack: Decimal
    defense: Decimal
    barrier: Decimal = D(0)
    barrier_turns: int = 0
    cooldowns: dict[str, int] = field(default_factory=dict)
    uses: dict[str, int] = field(default_factory=dict)
    last_action: str | None = None
    buff_attack: Decimal = D(0)  # fração, ex.: 0.10
    buff_turns: int = 0
    agility: Decimal = D(0)

    @property
    def defeated(self) -> bool:
        return self.hp <= 0

    def to_data(self) -> dict:
        return {
            "hp": str(self.hp),
            "max_hp": str(self.max_hp),
            "attack": str(self.attack),
            "defense": str(self.defense),
            "barrier": str(self.barrier),
            "barrier_turns": self.barrier_turns,
            "cooldowns": dict(self.cooldowns),
            "uses": dict(self.uses),
            "last_action": self.last_action,
            "buff_attack": str(self.buff_attack),
            "buff_turns": self.buff_turns,
            "agility": str(self.agility),
        }

    @classmethod
    def from_data(cls, code: str, data: dict) -> EnemyUnit:
        return cls(
            code=code,
            hp=D(data["hp"]),
            max_hp=D(data["max_hp"]),
            attack=D(data["attack"]),
            defense=D(data["defense"]),
            barrier=D(data.get("barrier", "0")),
            barrier_turns=int(data.get("barrier_turns", 0)),
            cooldowns={k: int(v) for k, v in data.get("cooldowns", {}).items()},
            uses={k: int(v) for k, v in data.get("uses", {}).items()},
            last_action=data.get("last_action"),
            buff_attack=D(data.get("buff_attack", "0")),
            buff_turns=int(data.get("buff_turns", 0)),
            agility=D(data.get("agility", "0")),
        )


@dataclass(slots=True)
class PlayerUnit:
    character_id: UUID
    hp: Decimal
    max_hp: Decimal
    defense: Decimal


@dataclass(frozen=True, slots=True)
class PlayerIntent:
    character_id: UUID
    kind: str  # attack | defend | art
    target: str | None  # código do inimigo; None em defender
    damage: int  # medido pelo motor sobre o estado inicial; 0 em defender


@dataclass(frozen=True, slots=True)
class EnemyDecisionData:
    enemy_code: str
    action_key: str
    target_ids: tuple[UUID, ...]
    telegraph: bool


@dataclass(slots=True)
class RoundOutcome:
    damage_by_character: dict[UUID, int] = field(default_factory=dict)  # dano efetivo
    absorbed_by_character: dict[UUID, int] = field(default_factory=dict)  # Barreira inimiga
    kills_by_character: dict[UUID, list[str]] = field(default_factory=dict)
    damage_taken: dict[UUID, int] = field(default_factory=dict)
    defeated_players: list[UUID] = field(default_factory=list)
    defeated_enemies: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)  # linhas estruturadas, sem texto


def kit_action(code: str, action_key: str) -> VeuAction:
    return next(a for a in creature(code).actions if a.key == action_key)


def decide_enemy(
    enemy: EnemyUnit,
    present: list[UUID],
    round_number: int,
    seed: int,
) -> EnemyDecisionData | None:
    """Ação e alvos do inimigo, antes da janela dos jogadores (§17.1)."""
    if enemy.defeated or not present:
        return None
    options = []
    for action in creature(enemy.code).actions:
        if enemy.cooldowns.get(action.key, 0) > 0:
            continue
        if action.max_uses is not None and enemy.uses.get(action.key, 0) >= action.max_uses:
            continue
        if action.not_consecutive and enemy.last_action == action.key:
            continue
        if action.kind is ActionKind.BARRIER and enemy.barrier > 0:
            continue
        options.append(action)
    if not options:
        return None
    chosen = options[seed % len(options)]
    ordered = sorted(present, key=str)
    if chosen.kind is ActionKind.AOE:
        targets = tuple(ordered)
    elif chosen.kind in (ActionKind.BARRIER, ActionKind.SELF_BUFF):
        targets = ()
    else:
        count = min(chosen.targets or 1, len(ordered))
        start = (seed // 7) % len(ordered)
        targets = tuple(ordered[(start + step) % len(ordered)] for step in range(count))
    return EnemyDecisionData(
        enemy.code, chosen.key, targets, chosen.prepared or chosen.always_telegraphed
    )


def resolve_batch(
    enemies: dict[str, EnemyUnit],
    players: dict[UUID, PlayerUnit],
    intents: list[PlayerIntent],
    decisions: list[EnemyDecisionData],
) -> RoundOutcome:
    """Aplica a rodada em lote a partir do estado inicial (§13.1 passos 8–11)."""
    outcome = RoundOutcome()
    initial_barrier = {code: enemy.barrier for code, enemy in enemies.items()}
    defending = {i.character_id for i in intents if i.kind == "defend"}

    # 1) dano dos jogadores, ordem determinística; overkill não conta.
    for intent in sorted(intents, key=lambda i: str(i.character_id)):
        if intent.kind == "defend" or intent.target is None or intent.damage <= 0:
            continue
        enemy = enemies.get(intent.target)
        if enemy is None or enemy.defeated:
            continue
        remaining = D(intent.damage)
        absorbed = min(initial_barrier[enemy.code], remaining)
        if absorbed > 0:
            initial_barrier[enemy.code] -= absorbed
            enemy.barrier -= absorbed
            remaining -= absorbed
            outcome.absorbed_by_character[intent.character_id] = (
                outcome.absorbed_by_character.get(intent.character_id, 0) + int(absorbed)
            )
            outcome.history.append(
                {"kind": "barrier_absorbed", "enemy": enemy.code, "amount": int(absorbed)}
            )
        effective = min(remaining, enemy.hp)
        if effective > 0:
            enemy.hp -= effective
            outcome.damage_by_character[intent.character_id] = (
                outcome.damage_by_character.get(intent.character_id, 0) + int(effective)
            )
            outcome.history.append(
                {"kind": "enemy_damaged", "enemy": enemy.code, "amount": int(effective)}
            )
            if enemy.hp <= 0 and enemy.code not in outcome.defeated_enemies:
                outcome.defeated_enemies.append(enemy.code)
                outcome.kills_by_character.setdefault(intent.character_id, []).append(enemy.code)
                outcome.history.append({"kind": "enemy_defeated", "enemy": enemy.code})

    # 2) resposta inimiga: decisões já comprometidas; inimigo derrotado nesta rodada ainda age
    # (as ações são simultâneas a partir do estado inicial, §13.4).
    for decision in decisions:
        enemy = enemies[decision.enemy_code]
        action = kit_action(enemy.code, decision.action_key)
        enemy.uses[action.key] = enemy.uses.get(action.key, 0) + 1
        enemy.last_action = action.key
        if action.cooldown:
            enemy.cooldowns[action.key] = action.cooldown
        attack = enemy.attack * (D(1) + (enemy.buff_attack if enemy.buff_turns > 0 else D(0)))
        if action.kind is ActionKind.BARRIER:
            amount = (
                enemy.max_hp * action.barrier_hp_fraction
                if action.barrier_hp_fraction is not None
                else enemy.attack * (action.barrier_attack_coefficient or D(0))
            )
            enemy.barrier = D(int(amount))
            enemy.barrier_turns = BARRIER_DURATION_TURNS
            outcome.history.append(
                {"kind": "enemy_barrier", "enemy": enemy.code, "action": action.key}
            )
            continue
        if action.kind is ActionKind.SELF_BUFF:
            if action.stat == "ATQ":
                enemy.buff_attack = abs(action.magnitude or D(0))
                enemy.buff_turns = action.turns or 0
            outcome.history.append(
                {"kind": "enemy_buff", "enemy": enemy.code, "action": action.key}
            )
            continue
        if action.coefficient is None or action.kind is ActionKind.DEBUFF:
            continue
        for target_id in decision.target_ids:
            player = players.get(target_id)
            if player is None or player.hp <= 0:
                continue
            value = direct_damage(
                attack,
                action.coefficient,
                player.defense,
                EVENT_REFERENCE_LEVEL,
                mitigation=DEFEND_MITIGATION if target_id in defending else D(0),
            )
            dealt = min(D(value), player.hp)
            player.hp -= dealt
            outcome.damage_taken[target_id] = outcome.damage_taken.get(target_id, 0) + int(dealt)
            outcome.history.append(
                {
                    "kind": "player_damaged",
                    "enemy": enemy.code,
                    "action": action.key,
                    "character": str(target_id),
                    "amount": int(dealt),
                }
            )
            if player.hp <= 0 and target_id not in outcome.defeated_players:
                outcome.defeated_players.append(target_id)

    # 3) fim da rodada: recargas, Barreira e buff envelhecem.
    for enemy in enemies.values():
        enemy.cooldowns = {k: v - 1 for k, v in enemy.cooldowns.items() if v - 1 > 0}
        if enemy.barrier_turns > 0:
            enemy.barrier_turns -= 1
            if enemy.barrier_turns == 0:
                enemy.barrier = D(0)
        if enemy.buff_turns > 0:
            enemy.buff_turns -= 1
            if enemy.buff_turns == 0:
                enemy.buff_attack = D(0)
    return outcome

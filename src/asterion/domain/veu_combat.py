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

from asterion.domain.combat import Effect
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


STAT_MAP = {"ATQ": "attack", "DEF": "defense", "AGI": "agility", "PER": "per"}

# Prioridade explícita do conteúdo (§10, Núcleo D): com 3 ou mais participantes ativos o
# Tecelão de Ossos usa Trama Óssea em prioridade quando disponível.
CONTENT_PRIORITY = {"VEU-09": ("trama_ossea", 3)}


@dataclass(slots=True)
class PlayerEffect:
    """Efeito sobre um jogador, no contrato do ``combat.Effect`` do motor.

    ``Fighter.stat`` do motor aplica ``kind``/``magnitude``/``stat``; aqui só se guarda e
    envelhece por rodada. Não existe um segundo sistema de status.
    """

    id: str
    stat: str  # attack | defense | agility | per
    magnitude: Decimal  # fração positiva; kind diz o sentido
    remaining: int
    kind: str = "debuff"  # debuff | buff
    source: str = ""  # personagem que apoiou (buff) ou criatura (debuff)

    def to_data(self) -> dict:
        return {
            "id": self.id,
            "stat": self.stat,
            "magnitude": str(self.magnitude),
            "remaining": self.remaining,
            "kind": self.kind,
            "source": self.source,
        }

    @classmethod
    def from_data(cls, data: dict) -> PlayerEffect:
        return cls(
            data["id"],
            data["stat"],
            D(data["magnitude"]),
            int(data["remaining"]),
            data.get("kind", "debuff"),
            data.get("source", ""),
        )


@dataclass(slots=True)
class PlayerUnit:
    character_id: UUID
    hp: Decimal
    max_hp: Decimal
    defense: Decimal
    barrier: Decimal = D(0)
    barrier_turns: int = 0
    barrier_source: UUID | None = None
    effects: list[PlayerEffect] = field(default_factory=list)

    def state_data(self) -> dict:
        return {
            "barrier": str(self.barrier),
            "barrier_turns": self.barrier_turns,
            "barrier_source": str(self.barrier_source) if self.barrier_source else None,
            "effects": [effect.to_data() for effect in self.effects],
        }

    def load_state(self, data: dict) -> None:
        self.barrier = D(data.get("barrier", "0"))
        self.barrier_turns = int(data.get("barrier_turns", 0))
        source = data.get("barrier_source")
        self.barrier_source = UUID(source) if source else None
        self.effects = [PlayerEffect.from_data(item) for item in data.get("effects", ())]


@dataclass(frozen=True, slots=True)
class SupportResult:
    """Suporte direto medido pelo motor: o que uma Arte fez em outro participante."""

    source: UUID
    target: UUID
    kind: str  # heal | barrier | protection
    amount: int = 0
    barrier_turns: int = 0
    effects: tuple[PlayerEffect, ...] = ()


@dataclass(frozen=True, slots=True)
class PlayerIntent:
    character_id: UUID
    kind: str  # attack | defend | art
    target: str | None  # código do inimigo; None em defender
    damage: int  # medido pelo motor sobre o estado inicial; 0 em defender
    support: tuple[SupportResult, ...] = ()


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
    # Impacto real de suporte creditado a quem apoiou (§23.3): cura efetiva, Barreira
    # efetivamente absorvida e proteção que de fato reduziu dano de um aliado.
    heal_by_character: dict[UUID, int] = field(default_factory=dict)
    barrier_absorbed_for: dict[UUID, int] = field(default_factory=dict)
    protection_credit: set[UUID] = field(default_factory=set)
    history: list[dict] = field(default_factory=list)  # linhas estruturadas, sem texto


def engine_effect(effect: PlayerEffect) -> Effect:
    """O mesmo efeito no tipo do motor; ``Fighter.stat`` calcula o impacto nos atributos."""
    return Effect(
        id=effect.id,
        stat=effect.stat,
        magnitude=effect.magnitude,
        remaining=effect.remaining,
        applied_opportunity=0,
        kind=effect.kind,
    )


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
    prioritized = CONTENT_PRIORITY.get(enemy.code)
    if prioritized is not None and len(present) >= prioritized[1]:
        forced = next((a for a in options if a.key == prioritized[0]), None)
        if forced is not None:
            chosen = forced
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


def support_kinds(action) -> tuple[str, ...]:
    """Categorias de suporte direto de uma ação do motor (``combat.Action``).

    Só cura, Barreira e proteção/mitigação em aliado entram (§22.1); ataque, debuff e
    controle ofensivo não.
    """
    if action.target_mode not in {"ally", "all_allies"}:
        return ()
    kinds = []
    if action.heal_coefficient > 0:
        kinds.append("heal")
    if action.target_barrier_coefficient > 0:
        kinds.append("barrier")
    if any(effect.kind == "buff" for effect in action.target_effects):
        kinds.append("protection")
    return tuple(kinds)


def _tick(player: PlayerUnit) -> None:
    player.effects = [
        PlayerEffect(e.id, e.stat, e.magnitude, e.remaining - 1, e.kind, e.source)
        for e in player.effects
        if e.remaining - 1 > 0
    ]
    if player.barrier_turns > 0:
        player.barrier_turns -= 1
        if player.barrier_turns == 0:
            player.barrier = D(0)
            player.barrier_source = None


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
    start_hp = {character_id: player.hp for character_id, player in players.items()}
    start_effects = {
        character_id: [e for e in player.effects if e.kind == "buff"]
        for character_id, player in players.items()
    }

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
    # (as ações são simultâneas a partir do estado inicial, §13.4). A vida dos jogadores é
    # acumulada sem piso: curas da mesma rodada entram antes da checagem de derrota.
    pending_effects: dict[UUID, list[PlayerEffect]] = {}
    unclamped = dict(start_hp)
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
        for target_id in decision.target_ids:
            player = players.get(target_id)
            if player is None or start_hp[target_id] <= 0:
                continue
            if action.coefficient is not None and action.kind is not ActionKind.DEBUFF:
                value = D(
                    direct_damage(
                        attack,
                        action.coefficient,
                        player.defense,
                        EVENT_REFERENCE_LEVEL,
                        mitigation=DEFEND_MITIGATION if target_id in defending else D(0),
                    )
                )
                absorbed = min(player.barrier, value)
                if absorbed > 0:
                    player.barrier -= absorbed
                    if player.barrier_source is not None:
                        outcome.barrier_absorbed_for[player.barrier_source] = (
                            outcome.barrier_absorbed_for.get(player.barrier_source, 0)
                            + int(absorbed)
                        )
                dealt = value - absorbed
                before = max(unclamped[target_id], D(0))
                unclamped[target_id] -= dealt
                shown = min(dealt, before)
                outcome.damage_taken[target_id] = outcome.damage_taken.get(target_id, 0) + int(
                    shown
                )
                outcome.history.append(
                    {
                        "kind": "player_damaged",
                        "enemy": enemy.code,
                        "action": action.key,
                        "character": str(target_id),
                        "amount": int(shown),
                    }
                )
                if dealt > 0:
                    for effect in start_effects[target_id]:
                        if effect.stat == "defense" and effect.source:
                            outcome.protection_credit.add(UUID(effect.source))
            if action.kind in (ActionKind.DAMAGE_DEBUFF, ActionKind.DEBUFF):
                stat = STAT_MAP.get(action.stat or "")
                if stat and action.turns:
                    pending_effects.setdefault(target_id, []).append(
                        PlayerEffect(
                            f"veu:{enemy.code}:{action.key}",
                            stat,
                            abs(action.magnitude or D(0)),
                            action.turns,
                            "debuff",
                            enemy.code,
                        )
                    )

    # 3) suporte direto (cura, Barreira, proteção): efetivo e simultâneo ao dano.
    for intent in sorted(intents, key=lambda i: str(i.character_id)):
        for result in intent.support:
            target = players.get(result.target)
            if target is None or start_hp[result.target] <= 0:
                continue
            if result.kind == "heal" and result.amount > 0:
                room = target.max_hp - max(unclamped[result.target], D(0))
                effective = max(D(0), min(D(result.amount), room))
                unclamped[result.target] += effective
                if effective > 0:
                    outcome.heal_by_character[result.source] = (
                        outcome.heal_by_character.get(result.source, 0) + int(effective)
                    )
            elif result.kind == "barrier" and result.amount > 0:
                target.barrier += D(result.amount)
                target.barrier_turns = max(target.barrier_turns, result.barrier_turns)
                target.barrier_source = result.source
            elif result.kind == "protection":
                pending_effects.setdefault(result.target, []).extend(result.effects)

    # 4) vida final e derrotas; envelhecimento; efeitos novos valem a partir da próxima rodada.
    for character_id, player in players.items():
        player.hp = min(player.max_hp, max(unclamped[character_id], D(0)))
        if start_hp[character_id] > 0 and unclamped[character_id] <= 0:
            outcome.defeated_players.append(character_id)
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
    for character_id, player in players.items():
        # Quem recebeu Barreira nesta rodada ainda não a gastou: só a anterior envelhece.
        fresh_barrier = any(
            r.kind == "barrier" and r.target == character_id
            for i in intents
            for r in i.support
        )
        turns_before = player.barrier_turns
        _tick(player)
        if fresh_barrier:
            player.barrier_turns = turns_before
        for effect in pending_effects.get(character_id, ()):
            player.effects = [e for e in player.effects if e.id != effect.id]
            player.effects.append(
                PlayerEffect(
                    effect.id,
                    effect.stat,
                    effect.magnitude,
                    effect.remaining,
                    effect.kind,
                    effect.source,
                )
            )
    return outcome

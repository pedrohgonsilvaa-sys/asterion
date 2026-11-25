"""O Despertar dos Flagelos: rodada sobre o motor de combate existente (sem Raid Engine).

Reaproveita o simulador de A Ruptura do Véu (``EngineRoundSimulator``): cada ação válida roda
numa instância do motor com o equipamento, as Artes e os efeitos reais do personagem, contra o
Flagelo com os atributos congelados da rodada. Este módulo só acrescenta o que o Flagelo pede:

- nível de referência do Flagelo (não o do Véu);
- efeitos e DoTs que jogadores aplicam no Flagelo persistem entre rodadas (``Effect`` e
  ``DotState`` do próprio motor) e entram nas instâncias seguintes;
- "aplicação significativa de efeito" (decisão do autor, 2026-11-25): só conta quando o motor
  de fato aplicou um efeito novo, renovou a duração ou aumentou a pilha no Flagelo. Efeito
  resistido, bloqueado ou sem mudança de estado não conta.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal

from asterion.application.world_event_veu_combat import EngineRoundSimulator
from asterion.domain import veu_combat as vc
from asterion.domain.combat import (
    DOT_DEFAULT_TICK_COEFFICIENT,
    DOT_TICK_COEFFICIENTS,
    DotState,
    Effect,
    Fighter,
)
from asterion.domain.combat_math import CombatStats, dot_damage

_PLAYER = "player"


def _json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


def effect_to_data(effect: Effect) -> dict:
    return _json(asdict(effect))


def effect_from_data(data: dict) -> Effect:
    return Effect(**(dict(data) | {"magnitude": Decimal(data["magnitude"])}))


@dataclass(slots=True)
class BossDot:
    """``DotState`` do motor + o necessário para o tick fora da instância."""

    state: DotState
    source_character: str  # character_id que aplicou (crédito do dano efetivo)
    source_level: int
    source_per: Decimal = Decimal(0)

    def to_data(self) -> dict:
        return {
            "state": _json(asdict(self.state)),
            "source_character": self.source_character,
            "source_level": self.source_level,
            "source_per": str(self.source_per),
        }

    @classmethod
    def from_data(cls, data: dict) -> BossDot:
        raw = dict(data["state"])
        state = DotState(
            **(
                raw
                | {
                    "snapshot_attack": Decimal(raw["snapshot_attack"]),
                    "stack_snapshots": [Decimal(v) for v in raw.get("stack_snapshots", [])],
                }
            )
        )
        return cls(
            state,
            data["source_character"],
            int(data["source_level"]),
            Decimal(data.get("source_per", "0")),
        )


@dataclass(slots=True)
class BossEffects:
    effects: list[Effect] = field(default_factory=list)
    dots: list[BossDot] = field(default_factory=list)

    def to_data(self) -> dict:
        return {
            "effects": [effect_to_data(effect) for effect in self.effects],
            "dots": [dot.to_data() for dot in self.dots],
        }

    @classmethod
    def from_data(cls, data: dict | None) -> BossEffects:
        data = data or {}
        return cls(
            [effect_from_data(item) for item in data.get("effects", ())],
            [BossDot.from_data(item) for item in data.get("dots", ())],
        )

    def stat(self, stats: CombatStats, name: str) -> Decimal:
        """O mesmo ``Fighter.stat`` do motor sobre os efeitos carregados."""
        fighter = Fighter("flagelo", "flagelo", 1, stats, stats.hp, effects=list(self.effects))
        return fighter.stat(name)


def _stacks(dot: DotState) -> int:
    return len(dot.stack_snapshots) if dot.stack_snapshots else dot.stacks


def _changed(before_effects, before_dots, after_effects, after_dots) -> bool:
    """O motor aplicou/renovou/empilhou algo de fato no alvo?"""
    old = {effect.id: effect for effect in before_effects}
    for effect in after_effects:
        previous = old.get(effect.id)
        if previous is None:
            return True
        if effect.remaining > previous.remaining or effect.stacks > previous.stacks:
            return True
    old_dots = {dot.kind: dot for dot in before_dots}
    for dot in after_dots:
        previous = old_dots.get(dot.kind)
        if previous is None:
            return True
        if dot.remaining > previous.remaining or _stacks(dot) > _stacks(previous):
            return True
    return False


class FlageloRoundSimulator(EngineRoundSimulator):
    def __init__(self, reference_level: int, boss: BossEffects | None = None):
        super().__init__(reference_level)
        self.boss = boss or BossEffects()
        # Resultados por personagem: efeitos/DoTs do Flagelo depois da ação daquele jogador.
        self.applied: list[tuple[str, list[Effect], list[BossDot]]] = []

    def _sync_enemies(self, combat, enemies) -> None:  # type: ignore[override]
        EngineRoundSimulator._sync_enemies(combat, enemies)
        for code in enemies:
            fighter = combat.fighters.get(code)
            if fighter is None:
                continue
            fighter.effects = [effect_from_data(effect_to_data(e)) for e in self.boss.effects]
            if self.boss.dots:
                combat.dot_states[fighter.id] = [
                    BossDot.from_data(dot.to_data()).state for dot in self.boss.dots
                ]

    def _attack_intent(self, ctx, action_type, target, damage, before, updated):
        applied = False
        if updated is not None and target in updated.fighters:
            target_before = before.fighters[target]
            target_after = updated.fighters[target]
            dots_before = before.dot_states.get(target_before.id, [])
            dots_after = updated.dot_states.get(target_after.id, [])
            applied = _changed(target_before.effects, dots_before, target_after.effects, dots_after)
            if applied:
                player = updated.fighters[_PLAYER]
                known = {dot.state.kind: dot for dot in self.boss.dots}
                dots = []
                for dot in dots_after:
                    previous = known.get(dot.kind)
                    fresh = previous is None or _changed([], [previous.state], [], [dot])
                    dots.append(
                        BossDot(
                            dot,
                            str(ctx.character.id) if fresh else previous.source_character,
                            ctx.character.level if fresh else previous.source_level,
                            Decimal(player.stat("per")) if fresh else previous.source_per,
                        )
                    )
                self.applied.append((str(ctx.character.id), list(target_after.effects), dots))
        return vc.PlayerIntent(
            ctx.character.id, action_type, target, damage, effect_applied=applied
        )

    def merged(self) -> BossEffects:
        """Efeitos do Flagelo depois do lote: por id/tipo, fica o mais forte (duração, pilha).

        Ações simultâneas partem do mesmo estado inicial (§7.3); a ordem por personagem é
        estável, como a ordenação do lote existente.
        """
        effects = {effect.id: effect for effect in self.boss.effects}
        dots = {dot.state.kind: dot for dot in self.boss.dots}
        for _, after_effects, after_dots in sorted(self.applied, key=lambda item: item[0]):
            for effect in after_effects:
                current = effects.get(effect.id)
                if current is None or (effect.remaining, effect.stacks) > (
                    current.remaining,
                    current.stacks,
                ):
                    effects[effect.id] = effect
            for dot in after_dots:
                current = dots.get(dot.state.kind)
                if current is None or (_stacks(dot.state), dot.state.remaining) > (
                    _stacks(current.state),
                    current.state.remaining,
                ):
                    dots[dot.state.kind] = dot
        return BossEffects(list(effects.values()), list(dots.values()))


def tick_boss(boss: BossEffects, defense: Decimal) -> tuple[BossEffects, list[tuple[str, int]]]:
    """Fim da rodada: DoTs já carregados causam o tick oficial do motor e envelhecem; efeitos
    envelhecem uma rodada. Devolve o novo estado e ``(character_id, dano)`` por tick."""
    ticks: list[tuple[str, int]] = []
    dots: list[BossDot] = []
    for dot in boss.dots:
        snapshots = dot.state.stack_snapshots or [dot.state.snapshot_attack] * dot.state.stacks
        damage = dot_damage(
            snapshots,
            DOT_TICK_COEFFICIENTS.get(dot.state.kind, DOT_DEFAULT_TICK_COEFFICIENT),
            defense,
            dot.source_level,
            penetration=dot.source_per,
        )
        ticks.append((dot.source_character, damage))
        dot.state.remaining -= 1
        if dot.state.remaining > 0:
            dots.append(dot)
    effects = []
    for effect in boss.effects:
        effect.remaining -= 1
        if effect.remaining > 0:
            effects.append(effect)
    return BossEffects(effects, dots), ticks


def next_boss_state(
    before: BossEffects, merged: BossEffects, defense: Decimal
) -> tuple[BossEffects, list[tuple[str, int]]]:
    """Estado do Flagelo para a próxima rodada.

    O que já estava carregado tica e envelhece (``tick_boss``); o que um jogador aplicou ou
    renovou nesta rodada entra novo, sem envelhecer, e vale a partir da próxima rodada (mesma
    regra dos efeitos sobre jogadores no lote existente).
    """
    aged, ticks = tick_boss(BossEffects.from_data(before.to_data()), defense)
    old_effects = {id(effect) for effect in before.effects}
    old_dots = {id(dot) for dot in before.dots}
    effects = {effect.id: effect for effect in aged.effects}
    for effect in merged.effects:
        if id(effect) not in old_effects:
            effects[effect.id] = effect
    dots = {dot.state.kind: dot for dot in aged.dots}
    for dot in merged.dots:
        if id(dot) not in old_dots:
            dots[dot.state.kind] = dot
    return BossEffects(list(effects.values()), list(dots.values())), ticks

"""Simulador de rodada de A Ruptura do Véu sobre o motor de combate existente.

Para cada ação válida cria uma instância do motor com o equipamento, as Artes e os efeitos
reais do personagem, contra os inimigos do Núcleo com o HP/atributos do início da rodada, e
mede o resultado (§13.1 passo 8: tudo parte do estado inicial):

- Atacar e Artes ofensivas: dano causado ao alvo inimigo (``Fighter.stat`` do motor já
  reflete os efeitos que o jogador carrega, inclusive os debuffs dos kits).
- Artes de suporte (alvo aliado): instância em grupo com o apoiador e o(s) aliado(s); mede cura,
  Barreira e efeitos de proteção aplicados pelo próprio motor.
- Defender: sem dano; a redução é aplicada na resposta inimiga (``domain.veu_combat``).

Decisões técnicas (a fonte não define): Arte ``all_allies`` atinge o apoiador e até 3 aliados
presentes (limite de 4 membros do motor), os de menor fração de vida primeiro; Arte aliada sem
alvo válido não faz nada.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.world_event_veu import RoundInputs
from asterion.domain import veu_combat as vc
from asterion.domain.combat import act, allowed_actions, player_actions_for
from asterion.domain.combat_math import CombatStats
from asterion.domain.road import (
    CREATURES,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)
from asterion.domain.road import (
    RULESET as COMBAT_RULESET,
)
from asterion.domain.veu_bestiary import EVENT_REFERENCE_LEVEL
from asterion.infrastructure.db.models import Character, VeuEventAction, VeuEventParticipant

_ACTOR = "player"
# Criatura-molde do motor: só o corpo da instância; atributos e HP vêm do estado do Evento.
_MOLD = CREATURES[0]
MAX_ALLIES = 3


@dataclass(slots=True)
class _Ctx:
    participant: VeuEventParticipant
    character: Character
    equipment: object
    arts: object
    unit: vc.PlayerUnit | None = None


class EngineRoundSimulator:
    """``reference_level``: nível das instâncias-molde do inimigo (o Véu usa o do Evento)."""

    def __init__(self, reference_level: int = EVENT_REFERENCE_LEVEL):
        self.reference_level = reference_level

    async def prepare(
        self,
        session: AsyncSession,
        participants: Sequence[VeuEventParticipant],
        actions: Sequence[VeuEventAction],
        enemies: dict[str, vc.EnemyUnit],
        combat_key: str,
    ) -> RoundInputs:
        by_action = {action.character_id: action for action in actions}
        characters = {
            row.id: row
            for row in (
                await session.scalars(
                    select(Character).where(
                        Character.id.in_([p.character_id for p in participants])
                    )
                )
            ).all()
        }
        contexts: dict[UUID, _Ctx] = {}
        for participant in participants:
            character = characters.get(participant.character_id)
            if character is None:
                continue
            contexts[character.id] = _Ctx(
                participant,
                character,
                await load_equipment_configuration(session, character),
                await load_active_art_configuration(session, character),
            )
        # Estado de cada jogador no início da rodada: vida, Barreira e efeitos carregados.
        for ctx in contexts.values():
            combat = self._solo(ctx, enemies, f"{combat_key}|{ctx.character.id}|state")
            stats = combat.fighters[_ACTOR]
            hp = ctx.participant.hp if ctx.participant.hp is not None else stats.stats.hp
            ctx.unit = vc.PlayerUnit(
                ctx.character.id,
                Decimal(hp),
                Decimal(stats.stats.hp),
                Decimal(stats.stat("defense")),
            )
            ctx.unit.load_state(ctx.participant.combat_state or {})
            self._apply_effects(combat.fighters[_ACTOR], ctx.unit)
            ctx.unit.defense = Decimal(combat.fighters[_ACTOR].stat("defense"))
        players = {cid: ctx.unit for cid, ctx in contexts.items() if ctx.unit is not None}
        intents: list[vc.PlayerIntent] = []
        for ctx in contexts.values():
            action = by_action.get(ctx.character.id)
            if action is None or ctx.unit.hp <= 0:
                continue
            key = f"{combat_key}|{ctx.character.id}"
            if action.action_type == "defend":
                intents.append(vc.PlayerIntent(ctx.character.id, "defend", None, 0))
                continue
            art_id = self._art_id(ctx, action)
            solo = self._solo(ctx, enemies, key)
            definition = player_actions_for(solo, _ACTOR).get(art_id)
            mode = definition.target_mode if definition is not None else "opponent"
            if action.action_type == "art" and mode in {"ally", "all_allies", "self"}:
                results = self._support(ctx, action, art_id, mode, contexts, enemies, key)
                intents.append(
                    vc.PlayerIntent(ctx.character.id, "art", None, 0, tuple(results))
                )
                continue
            target = self._target(action, enemies)
            if target is None:
                continue
            damage, updated = self._measure_with_result(solo, art_id, target)
            intents.append(
                self._attack_intent(ctx, action.action_type, target, damage, solo, updated)
            )
        return RoundInputs(intents, players)

    def _attack_intent(self, ctx, action_type, target, damage, before, updated):
        """Gancho: o Véu só usa o dano; os Flagelos também leem o efeito aplicado."""
        return vc.PlayerIntent(ctx.character.id, action_type, target, damage)

    # ------------------------------------------------------------------ alvos / ações

    @staticmethod
    def _art_id(ctx: _Ctx, action: VeuEventAction) -> str:
        if action.action_type != "art":
            return "attack"
        slot = action.art_slot or 0
        ids = list(ctx.arts.art_ids)
        wanted = ids[slot - 1] if 0 < slot <= len(ids) else "art"
        return wanted

    @staticmethod
    def _target(action: VeuEventAction, enemies: dict[str, vc.EnemyUnit]) -> str | None:
        alive = sorted(code for code, unit in enemies.items() if not unit.defeated)
        if not alive:
            return None
        if action.target_ref in alive:
            return action.target_ref
        # Um só alvo válido: não há escolha (§21). Com dois ou mais e sem alvo, o primeiro.
        return alive[0]

    # --------------------------------------------------------------- instâncias do motor

    def _enemy_specs(self, enemies: dict[str, vc.EnemyUnit]):
        level = self.reference_level
        return tuple(
            CreatureCombatantSpec(_MOLD, level, code, passive=True)
            for code, unit in sorted(enemies.items())
            if not unit.defeated
        ) or (CreatureCombatantSpec(_MOLD, level, "sentinel", passive=True),)

    @staticmethod
    def _sync_enemies(combat, enemies: dict[str, vc.EnemyUnit]) -> None:
        for code, unit in enemies.items():
            fighter = combat.fighters.get(code)
            if fighter is None:
                continue
            fighter.stats = CombatStats(
                unit.max_hp, unit.attack, unit.effective_defense, unit.agility
            )
            fighter.hp = unit.hp

    @staticmethod
    def _apply_effects(fighter, unit: vc.PlayerUnit) -> None:
        fighter.effects = [vc.engine_effect(effect) for effect in unit.effects]

    def _solo(self, ctx: _Ctx, enemies, key: str):
        combat = create_creature_party_combat(
            uuid5(NAMESPACE_URL, key),
            ctx.character.name,
            ctx.character.character_class,
            ctx.character.race,
            Decimal(ctx.character.max_hp),
            self._enemy_specs(enemies),
            player_level=ctx.character.level,
            equipment_configuration=ctx.equipment,
            ruleset_version=COMBAT_RULESET,
            active_art_ids=tuple(ctx.arts.art_ids),
        )
        self._sync_enemies(combat, enemies)
        fighter = combat.fighters[_ACTOR]
        if ctx.unit is not None:
            fighter.hp = ctx.unit.hp
            self._apply_effects(fighter, ctx.unit)
        return combat

    @staticmethod
    def _measure(combat, action_id: str, target: str) -> int:
        return EngineRoundSimulator._measure_with_result(combat, action_id, target)[0]

    @staticmethod
    def _measure_with_result(combat, action_id: str, target: str):
        """Dano no alvo e o estado do motor depois da ação (``None`` se nada aconteceu)."""
        allowed = allowed_actions(combat, _ACTOR)
        if action_id not in allowed:
            action_id = "art" if action_id != "attack" and "art" in allowed else action_id
        before = combat.fighters[target].hp
        updated = act(combat, action_id, target_id=target, actor_key=_ACTOR)
        if updated.version == combat.version:
            return 0, None
        return max(0, int(before - updated.fighters[target].hp)), updated

    # ------------------------------------------------------------------------- suporte

    def _support(self, ctx, action, art_id, mode, contexts, enemies, key):
        allies: list[_Ctx] = []
        if mode == "ally":
            ref = (action.target_ref or "")
            target = next(
                (c for c in contexts.values() if f"c:{c.character.id.hex}" == ref), None
            )
            if target is not None and target.character.id != ctx.character.id:
                allies = [target]
            elif target is None:
                return []
        elif mode == "all_allies":
            others = sorted(
                (c for c in contexts.values() if c.character.id != ctx.character.id
                 and c.unit is not None and c.unit.hp > 0),
                key=lambda c: (c.unit.hp / c.unit.max_hp, str(c.character.id)),
            )
            allies = others[:MAX_ALLIES]
        members = [ctx, *allies]
        if len(members) == 1:
            combat = self._solo(ctx, enemies, key)
            keys = {_ACTOR: ctx}
            target_key = _ACTOR
            actor_key = _ACTOR
        else:
            specs = tuple(
                PlayerCombatantSpec(
                    fighter_key=f"p{index}",
                    character_id=str(member.character.id),
                    name=member.character.name,
                    character_class=member.character.character_class,
                    race=member.character.race,
                    level=member.character.level,
                    hp=Decimal(member.unit.hp),
                    equipment_configuration=member.equipment,
                    active_art_ids=tuple(member.arts.art_ids),
                    active_art_snapshots=tuple(slot.to_data() for slot in member.arts.slots),
                )
                for index, member in enumerate(members, start=1)
            )
            combat = create_creature_party_combat(
                uuid5(NAMESPACE_URL, key + "|support"),
                ctx.character.name,
                ctx.character.character_class,
                ctx.character.race,
                Decimal(ctx.unit.hp),
                self._enemy_specs(enemies),
                player_level=ctx.character.level,
                equipment_configuration=ctx.equipment,
                ruleset_version=COMBAT_RULESET,
                party=specs,
            )
            self._sync_enemies(combat, enemies)
            keys = {f"p{index}": member for index, member in enumerate(members, start=1)}
            for fighter_key, member in keys.items():
                combat.fighters[fighter_key].hp = member.unit.hp
                self._apply_effects(combat.fighters[fighter_key], member.unit)
            actor_key = "p1"
            target_key = "p2" if mode == "ally" else None
        before = {
            k: (
                Decimal(combat.fighters[k].hp),
                Decimal(combat.fighters[k].barrier),
                {e.id for e in combat.fighters[k].effects},
            )
            for k in keys
        }
        if art_id not in allowed_actions(combat, actor_key):
            return []
        updated = act(combat, art_id, target_id=target_key, actor_key=actor_key)
        if updated.version == combat.version:
            return []
        results: list[vc.SupportResult] = []
        for fighter_key, member in keys.items():
            fighter = updated.fighters[fighter_key]
            hp0, barrier0, effects0 = before[fighter_key]
            heal = int(Decimal(fighter.hp) - hp0)
            if heal > 0 and (fighter_key != actor_key or mode == "self"):
                results.append(
                    vc.SupportResult(ctx.character.id, member.character.id, "heal", heal)
                )
            gained = Decimal(fighter.barrier) - barrier0
            if gained > 0:
                results.append(
                    vc.SupportResult(
                        ctx.character.id,
                        member.character.id,
                        "barrier",
                        int(gained),
                        int(fighter.barrier_remaining),
                    )
                )
            buffs = tuple(
                vc.PlayerEffect(
                    f"support:{ctx.character.id.hex}:{effect.id}",
                    effect.stat,
                    Decimal(effect.magnitude),
                    int(effect.remaining),
                    "buff",
                    str(ctx.character.id),
                )
                for effect in fighter.effects
                if effect.id not in effects0 and effect.kind == "buff"
            )
            if buffs:
                results.append(
                    vc.SupportResult(
                        ctx.character.id, member.character.id, "protection", 0, 0, buffs
                    )
                )
        return results

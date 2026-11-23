"""Simulador de rodada de A Ruptura do Véu sobre o motor de combate existente.

Para cada ação válida (Atacar e Artes) cria uma instância do motor com o equipamento e as
Artes reais do personagem, contra os inimigos do Núcleo com o HP/atributos do início da
rodada, e mede o dano causado (§13.1 passo 8: tudo parte do estado inicial). Defender não
causa dano. O resto da rodada (Barreira, resposta inimiga, mortes) é ``domain.veu_combat``.

Decisão técnica: Artes de suporte/cura ou efeitos sobre outros jogadores não têm alvo
aliado nesta instância; só o dano sobre os inimigos entra na rodada.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.world_event_veu import RoundInputs
from asterion.domain import veu_combat as vc
from asterion.domain.combat import act, allowed_actions
from asterion.domain.combat_math import CombatStats
from asterion.domain.equipment_stats import equipment_configuration_from_data
from asterion.domain.road import (
    CREATURES,
    CreatureCombatantSpec,
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


class EngineRoundSimulator:
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
        players: dict[UUID, vc.PlayerUnit] = {}
        intents: list[vc.PlayerIntent] = []
        for participant in participants:
            character = characters.get(participant.character_id)
            if character is None:
                continue
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            configuration = equipment.to_data(COMBAT_RULESET) | arts.to_data()
            art_ids = tuple(
                str(entry["art_id"])
                for entry in configuration.get("active_arts", ())
                if isinstance(entry, dict) and entry.get("art_id")
            )
            action = by_action.get(participant.character_id)
            combat = self._instance(
                character, configuration, art_ids, enemies, f"{combat_key}|{character.id}"
            )
            stats = combat.fighters[_ACTOR].stats
            hp = participant.hp if participant.hp is not None else stats.hp
            players[character.id] = vc.PlayerUnit(
                character.id, Decimal(hp), Decimal(stats.hp), Decimal(stats.defense)
            )
            if action is None or players[character.id].hp <= 0:
                continue
            if action.action_type == "defend":
                intents.append(vc.PlayerIntent(character.id, "defend", None, 0))
                continue
            target = self._target(action, enemies)
            if target is None:
                continue
            action_id = "attack"
            if action.action_type == "art":
                slot = action.art_slot or 0
                wanted = art_ids[slot - 1] if 0 < slot <= len(art_ids) else "art"
                allowed = allowed_actions(combat, _ACTOR)
                action_id = wanted if wanted in allowed else "art"
            damage = self._measure(combat, action_id, target)
            intents.append(vc.PlayerIntent(character.id, action.action_type, target, damage))
        return RoundInputs(intents, players)

    @staticmethod
    def _target(action: VeuEventAction, enemies: dict[str, vc.EnemyUnit]) -> str | None:
        alive = sorted(code for code, unit in enemies.items() if not unit.defeated)
        if not alive:
            return None
        if action.target_ref in alive:
            return action.target_ref
        # Um só alvo válido: não há escolha (§21). Com dois ou mais e sem alvo, o primeiro.
        return alive[0]

    @staticmethod
    def _instance(character, configuration, art_ids, enemies, key):
        specs = tuple(
            CreatureCombatantSpec(_MOLD, EVENT_REFERENCE_LEVEL, code)
            for code, unit in sorted(enemies.items())
            if not unit.defeated
        ) or (CreatureCombatantSpec(_MOLD, EVENT_REFERENCE_LEVEL, "sentinel"),)
        combat = create_creature_party_combat(
            uuid5(NAMESPACE_URL, key),
            character.name,
            character.character_class,
            character.race,
            Decimal(character.max_hp),
            specs,
            player_level=character.level,
            equipment_configuration=equipment_configuration_from_data(configuration),
            ruleset_version=COMBAT_RULESET,
            active_art_ids=art_ids,
        )
        for code, unit in enemies.items():
            fighter = combat.fighters.get(code)
            if fighter is None:
                continue
            fighter.stats = CombatStats(unit.max_hp, unit.attack, unit.defense, unit.agility)
            fighter.hp = unit.hp
        return combat

    @staticmethod
    def _measure(combat, action_id: str, target: str) -> int:
        before = combat.fighters[target].hp
        updated = act(combat, action_id, target_id=target, actor_key=_ACTOR)
        if updated.version == combat.version:
            return 0
        return max(0, int(before - updated.fighters[target].hp))

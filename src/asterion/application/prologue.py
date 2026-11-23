"""Transactional entry, recovery, actions and fixed one-off prologue reward."""

import secrets
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.domain.combat import (
    Combat,
    CombatConsumableOption,
    act,
    expire_turn,
    turn_expired,
)
from asterion.domain.creation import PROLOGUE
from asterion.domain.creation import RULESET as CHARACTER_RULESET
from asterion.domain.prologue import (
    COMBAT_STAGE,
    CONTENT_ID,
    FAILED_STAGE,
    POST_COMBAT_STAGE,
    PROLOGUE_ENEMY_IDS,
    REWARD_XP,
    SUPPORTED_COMBAT_RULESETS,
    PrologueProfile,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    BestiaryEvidence,
    Brazier,
    Character,
    CombatRecord,
    Encounter,
    GameActivity,
    LocationDiscovery,
    RewardComponent,
    RewardEvent,
    WorldState,
)

PURSE_SOURCE = "prologue.destrocos.bolsa"
PURSE_CROWNS = 18


@dataclass(frozen=True)
class CombatView:
    activity_id: UUID
    encounter_id: UUID
    character_id: UUID
    combat: Combat
    stage: str
    xp: int
    context: str = "prologue"
    consumable_options: tuple[CombatConsumableOption, ...] = ()
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    consumable_quantities: tuple[tuple[str, int], ...] = ()
    consumable_budget_limit: int = 0
    ready_consumable_option: CombatConsumableOption | None = None
    trial_stage_caption: str | None = None
    combat_actor_key: str | None = None
    campaign_shared: bool | None = None


def choose_enemy_id() -> str:
    """Draw the first-combat creature; both possibilities belong to the same encounter."""
    return secrets.choice(PROLOGUE_ENEMY_IDS)


def view(character: Character, activity: GameActivity, encounter: Encounter, record: CombatRecord):
    return CombatView(
        activity.id,
        encounter.id,
        character.id,
        decode(record.snapshot, record.id, activity.ruleset_version, activity.state_version),
        character.stage,
        character.xp,
        "prologue",
    )


class PrologueService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        profile: PrologueProfile,
    ):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id
        self.profile = profile

    async def resume(self, actor: int) -> CombatView | None:
        return await self._command(actor)

    async def enter(self, actor: int) -> CombatView | None:
        return await self._command(actor, enter=True)

    async def action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str,
    ) -> CombatView | None:
        return await self._command(actor, intent=(activity_id, version, action))

    async def collect_wreck_purse(self, actor: int) -> bool:
        """Credit the wreck's purse once per character; True only on the crediting call."""
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if character is None or character.stage != PROLOGUE:
                return False
            claimed = await session.scalar(
                pg_insert(RewardEvent)
                .values(character_id=character.id, source_id=PURSE_SOURCE)
                .on_conflict_do_nothing(index_elements=["character_id", "source_id"])
                .returning(RewardEvent.id)
            )
            if claimed is None:
                return False
            session.add(
                RewardComponent(reward_event_id=claimed, kind="crowns", quantity=PURSE_CROWNS)
            )
            character.crowns += PURSE_CROWNS
            return True

    async def _command(
        self,
        actor: int,
        *,
        enter: bool = False,
        intent: tuple[UUID, int, str] | None = None,
    ) -> CombatView | None:
        async with self.sessions.begin() as session:
            repo = CombatRepository(session)
            character = await repo.owned_character(actor, self.server_id)
            if character is None:
                return None
            activity = await repo.activity(character, CONTENT_ID)
            if activity is None:
                if not enter or character.stage != PROLOGUE or character.level != 1:
                    return None
                if character.ruleset_version not in SUPPORTED_COMBAT_RULESETS | {
                    CHARACTER_RULESET
                }:
                    raise ValueError("Character has not been migrated to the supported ruleset")
                equipment_configuration = await load_equipment_configuration(
                    session, character
                )
                reconcile_character_hp(character, equipment_configuration)
                enemy_id = choose_enemy_id()
                state = self.profile.create(
                    uuid4(),
                    character.name,
                    character.character_class,
                    character.race,
                    character.hp,
                    equipment_configuration,
                    enemy_id,
                )
                activity, encounter, record = await repo.create(character, CONTENT_ID, state)
                await self._ensure_tutorial_bestiary(session, character, enemy_id)
                character.stage = COMBAT_STAGE
                return view(character, activity, encounter, record)
            if activity.content_id != CONTENT_ID:
                # An incompatible Foreground already owns the character. Never replace it.
                return None
            encounter, record = await repo.combat(activity)
            current = view(character, activity, encounter, record)
            if (
                intent is None
                and activity.status == "failed"
                and character.stage == FAILED_STAGE
                and activity.ruleset_version in SUPPORTED_COMBAT_RULESETS
                and current.combat.result == "defeat"
            ):
                # Reconcile only the provable pre-v1.4.7 tutorial softlock.
                await self._complete_prologue_after_combat(session, character, activity)
                return view(character, activity, encounter, record)
            if activity.status == "active" and turn_expired(current.combat):
                # Server-side timeout: the overdue turn is spent exactly once, whether
                # it is found by a late action or by a plain resume.
                expired = expire_turn(current.combat)
                if expired.version != current.combat.version:
                    activity.state_version = expired.version
                    record.snapshot = encode(expired)
                    character.hp = expired.fighters["player"].hp
                    if expired.result == "defeat":
                        await self._complete_prologue_after_combat(session, character, activity)
                    return view(character, activity, encounter, record)
            if (
                intent is None
                or intent[:2] != (activity.id, activity.state_version)
                or activity.status != "active"
            ):
                return current
            if activity.ruleset_version not in SUPPORTED_COMBAT_RULESETS:
                raise ValueError(
                    "Unsupported combat ruleset; existing snapshots cannot be rebalanced"
                )
            updated = act(current.combat, intent[2])
            if updated.version == current.combat.version:
                return current
            activity.state_version = updated.version
            record.snapshot = encode(updated)
            character.hp = updated.fighters["player"].hp
            if updated.result == "victory":
                await repo.grant(character, activity, REWARD_XP)
                await self._complete_prologue_after_combat(session, character, activity)
            elif updated.result == "defeat":
                await self._complete_prologue_after_combat(session, character, activity)
            return view(character, activity, encounter, record)

    async def _complete_prologue_after_combat(
        self, session: AsyncSession, character: Character, activity: GameActivity
    ) -> None:
        """Converge valid tutorial results on the first brazier boundary."""
        activity.status = "completed"
        character.stage = POST_COMBAT_STAGE
        character.ruleset_version = CHARACTER_RULESET

        await session.execute(
            pg_insert(Brazier)
            .values(character_id=character.id, brazier_id="tdo.brazier.estrada")
            .on_conflict_do_nothing()
        )
        await session.execute(
            pg_insert(WorldState)
            .values(
                character_id=character.id,
                region="Terras do Ocaso",
                location="Estrada das Cinzas",
            )
            .on_conflict_do_update(
                index_elements=[WorldState.character_id],
                set_={"region": "Terras do Ocaso", "location": "Estrada das Cinzas"},
            )
        )
        await session.execute(
            pg_insert(LocationDiscovery)
            .values(
                character_id=character.id,
                location_id="tdo.location.estrada_das_cinzas",
            )
            .on_conflict_do_nothing()
        )
        from asterion.application.tdo_feats import reconcile_tdo_feats

        await reconcile_tdo_feats(session, character)

    async def _ensure_tutorial_bestiary(
        self, session, character, creature_id: str = "dog_cinereo"
    ) -> None:
        """Record the tutorial creature observation without granting observation XP."""
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character.id,
                BestiaryEntry.creature_id == creature_id,
            )
            .with_for_update()
        )
        if entry is None:
            entry = BestiaryEntry(
                character_id=character.id,
                creature_id=creature_id,
                bkp=7,
                stage="observed",
            )
            session.add(entry)
        for evidence_id, category in (
            ("first_observation", "observation"),
            ("first_combat", "combat"),
        ):
            exists = await session.scalar(
                select(BestiaryEvidence).where(
                    BestiaryEvidence.character_id == character.id,
                    BestiaryEvidence.creature_id == creature_id,
                    BestiaryEvidence.evidence_id == evidence_id,
                )
            )
            if exists is None:
                session.add(
                    BestiaryEvidence(
                        character_id=character.id,
                        creature_id=creature_id,
                        evidence_id=evidence_id,
                        category=category,
                    )
                )

"""Transactional entry, recovery, actions and fixed one-off prologue reward."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.domain.combat import Combat, CombatConsumableOption, act
from asterion.domain.creation import PROLOGUE
from asterion.domain.prologue import (
    COMBAT_STAGE,
    CONTENT_ID,
    FAILED_STAGE,
    LEGACY_RULESET,
    POST_COMBAT_STAGE,
    REWARD_XP,
    RULESET,
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
    WorldState,
)


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
                if character.ruleset_version not in {RULESET, LEGACY_RULESET}:
                    raise ValueError("Character has not been migrated to the supported ruleset")
                state = self.profile.create(
                    uuid4(),
                    character.name,
                    character.character_class,
                    character.race,
                    character.hp,
                )
                activity, encounter, record = await repo.create(character, CONTENT_ID, state)
                await self._ensure_tutorial_bestiary(session, character)
                character.stage = COMBAT_STAGE
                return view(character, activity, encounter, record)
            if activity.content_id != CONTENT_ID:
                # An incompatible Foreground already owns the character. Never replace it.
                return None
            encounter, record = await repo.combat(activity)
            current = view(character, activity, encounter, record)
            if (
                intent is None
                or intent[:2] != (activity.id, activity.state_version)
                or activity.status != "active"
            ):
                return current
            if activity.ruleset_version not in {RULESET, LEGACY_RULESET}:
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
                activity.status = "completed"
                character.stage = POST_COMBAT_STAGE
                character.ruleset_version = RULESET
                session.add(Brazier(character_id=character.id, brazier_id="tdo.brazier.estrada"))
                session.add(
                    WorldState(
                        character_id=character.id,
                        region="Terras do Ocaso",
                        location="Estrada das Cinzas",
                    )
                )
                session.add(
                    LocationDiscovery(
                        character_id=character.id,
                        location_id="tdo.location.estrada_das_cinzas",
                    )
                )
            elif updated.result == "defeat":
                activity.status = "failed"
                character.stage = FAILED_STAGE
            return view(character, activity, encounter, record)

    async def _ensure_tutorial_bestiary(self, session, character) -> None:
        """Record the tutorial Cão observation without granting observation XP."""
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character.id,
                BestiaryEntry.creature_id == "dog_cinereo",
            )
            .with_for_update()
        )
        if entry is None:
            entry = BestiaryEntry(
                character_id=character.id,
                creature_id="dog_cinereo",
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
                    BestiaryEvidence.creature_id == "dog_cinereo",
                    BestiaryEvidence.evidence_id == evidence_id,
                )
            )
            if exists is None:
                session.add(
                    BestiaryEvidence(
                        character_id=character.id,
                        creature_id="dog_cinereo",
                        evidence_id=evidence_id,
                        category=category,
                    )
                )

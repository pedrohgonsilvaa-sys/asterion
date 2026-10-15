"""Idempotent Feat reconciliation for the published Várzeas opening."""

from sqlalchemy import select

from asterion.infrastructure.db.models import Achievement, ExplorationAttempt, Quest

DIQUES_UNIQUES = (
    "explore.varzeas.diques.comporta_primeiro_dique",
    "explore.varzeas.diques.agua_sobe_sem_chuva",
)


async def reconcile_varzeas_feats(session, character) -> None:
    p19_complete = await session.scalar(
        select(Quest.id).where(
            Quest.character_id == character.id,
            Quest.quest_id == "P19",
            Quest.status == "completed",
        )
    )
    if p19_complete:
        await _ensure(session, character.id, "feat.varzeas.agua_de_ferro")

    resolved = set(
        (
            await session.scalars(
                select(ExplorationAttempt.result_id).where(
                    ExplorationAttempt.character_id == character.id,
                    ExplorationAttempt.local_id == "varzeas.location.diques_rubros",
                    ExplorationAttempt.status == "completed",
                    ExplorationAttempt.result_id.in_(DIQUES_UNIQUES),
                )
            )
        ).all()
    )
    if set(DIQUES_UNIQUES).issubset(resolved):
        await _ensure(session, character.id, "feat.varzeas.entre_os_diques")


async def _ensure(session, character_id, achievement_id: str) -> None:
    found = await session.scalar(
        select(Achievement.id).where(
            Achievement.character_id == character_id,
            Achievement.achievement_id == achievement_id,
        )
    )
    if found is None:
        session.add(Achievement(character_id=character_id, achievement_id=achievement_id))

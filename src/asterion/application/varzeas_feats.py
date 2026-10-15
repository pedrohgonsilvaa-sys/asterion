"""Idempotent Feat reconciliation for published Várzeas content."""

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

    p20_complete = await session.scalar(
        select(Quest.id).where(
            Quest.character_id == character.id,
            Quest.quest_id == "P20",
            Quest.status == "completed",
        )
    )
    if p20_complete:
        await _ensure(session, character.id, "feat.varzeas.o_pulso_sob_a_lama")

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

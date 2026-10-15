"""Idempotent Feat reconciliation for published Várzeas content."""

from sqlalchemy import select

from asterion.infrastructure.db.models import (
    Achievement,
    CodexEntry,
    ExplorationAttempt,
    Quest,
    Unlock,
)

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

    p21_complete = await session.scalar(
        select(Quest.id).where(
            Quest.character_id == character.id,
            Quest.quest_id == "P21",
            Quest.status == "completed",
        )
    )
    if p21_complete:
        await _ensure(session, character.id, "feat.varzeas.hortos_vazios")

    p22_complete = await session.scalar(
        select(Quest.id).where(
            Quest.character_id == character.id,
            Quest.quest_id == "P22",
            Quest.status == "completed",
        )
    )
    if p22_complete:
        await _ensure(session, character.id, "feat.varzeas.transferencia")

    p23_complete = await session.scalar(
        select(Quest.id).where(
            Quest.character_id == character.id,
            Quest.quest_id == "P23",
            Quest.status == "completed",
        )
    )
    if p23_complete:
        await _ensure(session, character.id, "feat.varzeas.persistencia_tem_preco")

    for family_id, feat_id in (
        (
            "dungeon.varzeas.enfermaria_afundada",
            "feat.varzeas.sem_paciente",
        ),
        (
            "dungeon.varzeas.cisterna_transferencia",
            "feat.varzeas.fluxo_contido",
        ),
    ):
        first_clear = await session.scalar(
            select(Unlock.id)
            .where(
                Unlock.character_id == character.id,
                Unlock.unlock_id.like(f"{family_id}.first_clear.%"),
            )
            .limit(1)
        )
        if first_clear:
            await _ensure(session, character.id, feat_id)

    hemaris_recorded = await session.scalar(
        select(CodexEntry.id).where(
            CodexEntry.character_id == character.id,
            CodexEntry.entry_id == "codex.history.projeto_hemaris_registro_inicial",
        )
    )
    if hemaris_recorded:
        await _ensure(session, character.id, "feat.varzeas.nome_recuperado")

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

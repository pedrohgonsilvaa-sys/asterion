"""O Despertar dos Flagelos: registro idempotente das contribuições regionais (§4.2).

Cada atividade PvE válida concluída grava UMA linha ``flagelo_contributions`` por
``activity_id + character_id``, na mesma transação da conclusão (``ON CONFLICT DO NOTHING``:
retry, reconnect e callback duplicado não pontuam duas vezes). A soma na barra, o congelamento
e o nascimento do Flagelo ficam no aplicador serializado de ``application/flagelos.py``.

A região alvo vem da atividade (Masmorra, Contrato, Missão) ou do lugar onde o personagem está
ao concluí-la (Caçada, Desbravar). Não existe seleção manual de região.

Missões: as 72 Missões concluem a ``Quest`` em dezenas de módulos. Em vez de tocar cada um, um
único ouvinte ``after_flush`` grava a contribuição quando uma ``Quest`` passa a ``completed``,
dentro da mesma transação. A região vem do catálogo narrativo canônico (Missão → Região).
"""

from __future__ import annotations

from sqlalchemy import event, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from asterion.domain import flagelos as fl
from asterion.infrastructure.db.models import Character, FlageloContribution, Quest, WorldState


def _values(server_id: str, character_id, activity_id: str, region_id: str, kind: str) -> dict:
    return {
        "server_id": server_id,
        "activity_id": activity_id[:160],
        "character_id": character_id,
        "region_id": region_id,
        "kind": kind,
        "points": fl.contribution_points(kind),
    }


def _statement(values: dict):
    return (
        insert(FlageloContribution)
        .values(**values)
        .on_conflict_do_nothing(constraint="uq_flagelo_contribution")
    )


async def record_contribution(
    session,
    character: Character,
    kind: str,
    activity_id: str,
    *,
    region: str | None = None,
    region_id: str | None = None,
) -> bool:
    """Grava a contribuição da atividade concluída. ``True`` se foi nova.

    ``region``: nome da Região (como em ``WorldState.region``); sem ela, vale a Região atual.
    """
    if fl.contribution_points(kind) <= 0:
        return False
    target = fl.REGIONS_BY_ID.get(region_id) if region_id else None
    if target is None:
        if region is None:
            region = await session.scalar(
                select(WorldState.region).where(WorldState.character_id == character.id)
            )
        target = fl.REGIONS_BY_NAME.get(region or "")
    if target is None:
        return False
    result = await session.execute(
        _statement(
            _values(character.server_id, character.id, activity_id, target.region_id, kind)
        ).returning(FlageloContribution.seq)
    )
    return result.first() is not None


def _mission_region(quest_id: str) -> fl.FlageloRegion | None:
    from asterion.domain.narrative_choices import narrative_catalog

    node = narrative_catalog().by_mission(quest_id)
    return fl.REGIONS_BY_MISSION.get(node.region) if node is not None else None


def _completed_now(state, quest: Quest) -> bool:
    if quest.status != "completed":
        return False
    if state.pending or state.transient:
        return True
    history = state.attrs.status.history
    return "completed" in (history.added or ()) and "completed" not in (history.deleted or ())


@event.listens_for(Session, "after_flush")
def _record_completed_missions(session: Session, _flush_context) -> None:
    quests = [obj for obj in (*session.new, *session.dirty) if isinstance(obj, Quest)]
    if not quests:
        return
    connection = session.connection()
    for quest in quests:
        state = sa_inspect(quest)
        if not _completed_now(state, quest) or quest.character_id is None:
            continue
        target = _mission_region(quest.quest_id)
        if target is None:
            continue
        server_id = connection.execute(
            select(Character.server_id).where(Character.id == quest.character_id)
        ).scalar()
        if server_id is None:
            continue
        connection.execute(
            _statement(
                _values(
                    server_id,
                    quest.character_id,
                    f"mission:{quest.id}",
                    target.region_id,
                    "mission",
                )
            )
        )

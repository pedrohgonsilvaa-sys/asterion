"""Metadata-driven cleanup for the currently implemented character graph."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import and_, delete, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.schema import ForeignKeyConstraint, Table

import asterion.infrastructure.db.models  # noqa: F401 - populate the declarative metadata
from asterion.infrastructure.db.base import Base


def _owning_constraints(table: Table) -> list[ForeignKeyConstraint]:
    """FKs that mean ownership. ON DELETE SET NULL is a mere reference: the row
    (an audit entry, someone else's invite) must survive and only lose the link."""
    return [
        constraint
        for constraint in table.foreign_key_constraints
        if (constraint.ondelete or "").upper() != "SET NULL"
    ]


def _character_descendants() -> tuple[list[Table], dict[str, set[str]]]:
    tables = dict(Base.metadata.tables)
    children: dict[str, set[str]] = defaultdict(set)
    parents_by_child: dict[str, set[str]] = defaultdict(set)
    for table in tables.values():
        for constraint in _owning_constraints(table):
            for element in constraint.elements:
                parent_name = element.column.table.name
                if parent_name in tables:
                    children[parent_name].add(table.name)
                    parents_by_child[table.name].add(parent_name)

    reachable = {"characters"}
    frontier = ["characters"]
    while frontier:
        parent = frontier.pop()
        for child in children[parent]:
            if child not in reachable:
                reachable.add(child)
                frontier.append(child)

    dependencies = {
        name: parents_by_child[name] & reachable - {name}
        for name in reachable
        if name != "characters"
    }
    ordered_names = ["characters"]
    while len(ordered_names) < len(reachable):
        ready = sorted(
            name
            for name, required in dependencies.items()
            if name not in ordered_names and required.issubset(ordered_names)
        )
        if not ready:
            raise RuntimeError("Character-owned database graph contains a foreign-key cycle.")
        ordered_names.extend(ready)
    return [tables[name] for name in ordered_names], dependencies


async def delete_character_owned_data(session: AsyncSession, character_id: UUID) -> None:
    """Delete all FK descendants of one Character, leaves first, then the root."""
    ordered, _dependencies = _character_descendants()
    key_sets: dict[str, set[tuple[object, ...]]] = {}
    root = ordered[0]
    key_sets[root.name] = {(character_id,)}

    for child in ordered[1:]:
        child_pk = tuple(child.primary_key.columns)
        child_keys: set[tuple[object, ...]] = set()
        for constraint in _owning_constraints(child):
            elements = tuple(constraint.elements)
            if not elements:
                continue
            parent = elements[0].column.table
            parent_keys = key_sets.get(parent.name)
            if not parent_keys:
                continue
            join_predicate = and_(
                *(element.parent == element.column for element in elements)
            )
            parent_pk = tuple(parent.primary_key.columns)
            statement = (
                select(*child_pk)
                .select_from(child.join(parent, join_predicate))
                .where(tuple_(*parent_pk).in_(parent_keys))
            )
            rows = (await session.execute(statement)).all()
            child_keys.update(tuple(row) for row in rows)
        key_sets[child.name] = child_keys

    for table in reversed(ordered):
        keys = key_sets.get(table.name, set())
        if not keys:
            continue
        primary_key = tuple(table.primary_key.columns)
        await session.execute(delete(table).where(tuple_(*primary_key).in_(keys)))

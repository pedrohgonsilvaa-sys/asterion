"""Terras do Ocaso v1.0.18 (33.5, decisão 11): texto do bloqueio da Caçada em Grupo.

Texto da UI v1.6.1, seção 66.4. Não mostra o número do nível mínimo e não
reaproveita "nada para caçar aqui ainda".
"""

from collections.abc import Sequence

HUNT_UNLOCK_BLOCKED_TITLE = "⚠ Caçada indisponível"


def hunt_unlock_blocked_message(names: Sequence[str]) -> str:
    """Cita todos os membros que não cumprem; verbo no singular com um nome."""
    if not names:
        raise ValueError("at least one blocked member name is required")
    listed = ", ".join(names[:-1]) + (" e " if len(names) > 1 else "") + names[-1]
    verb = "cumpre" if len(names) == 1 else "cumprem"
    return (
        f"{HUNT_UNLOCK_BLOCKED_TITLE}\n\n"
        f"{listed} ainda não {verb} o nível mínimo de nenhuma criatura deste Local."
    )

"""Writes to the append-only audit log (C1).

Callers add the entry to their own session, so it commits (or rolls back) in the
same transaction as the change it describes.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.models import ActorType, AuditLog, Role

_ROLE_ACTOR = {
    Role.CUSTOMER: ActorType.CUSTOMER,
    Role.REVIEWER: ActorType.REVIEWER,
    Role.ADMIN: ActorType.ADMIN,
}


def actor_for_role(role: Role) -> ActorType:
    return _ROLE_ACTOR[role]


def record(
    session: AsyncSession,
    *,
    actor_type: ActorType,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    return_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        action=action,
        return_id=return_id,
        details=details or {},
    )
    session.add(entry)
    return entry

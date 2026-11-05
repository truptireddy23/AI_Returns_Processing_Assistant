"""Admin: automation settings and the audit log (M8)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from returnguard import audit
from returnguard.auth import DbSession, require_role
from returnguard.models import ActorType, AuditLog, Role, Settings, User

router = APIRouter(prefix="/api/admin", tags=["admin"])

Admin = Annotated[User, Depends(require_role(Role.ADMIN))]


class SettingsOut(BaseModel):
    automation_enabled: bool
    risk_limit: Decimal
    high_value_limit_cents: int
    qa_sample_rate: Decimal
    updated_at: datetime


def _settings_out(row: Settings) -> SettingsOut:
    return SettingsOut(
        automation_enabled=row.automation_enabled,
        risk_limit=row.risk_limit,
        high_value_limit_cents=row.high_value_limit_cents,
        qa_sample_rate=row.qa_sample_rate,
        updated_at=row.updated_at,
    )


@router.get("/settings", response_model=SettingsOut)
async def get_settings(_: Admin, db: DbSession) -> SettingsOut:
    row = await db.get_one(Settings, 1)
    return _settings_out(row)


class SettingsUpdate(BaseModel):
    """Every field optional: only what's sent changes. Ranges match the
    database's own CHECK constraints (migration 0002) so a bad value is
    rejected with a clear message rather than a raw constraint-violation error.
    """

    automation_enabled: bool | None = None
    risk_limit: Decimal | None = Field(default=None, ge=0, le=1)
    high_value_limit_cents: int | None = Field(default=None, gt=0)
    qa_sample_rate: Decimal | None = Field(default=None, ge=0, le=1)


@router.patch("/settings", response_model=SettingsOut)
async def update_settings(body: SettingsUpdate, user: Admin, db: DbSession) -> SettingsOut:
    row = await db.get_one(Settings, 1, with_for_update=True)
    changes: dict[str, Any] = body.model_dump(exclude_unset=True)
    if not changes:
        return _settings_out(row)

    before = _settings_out(row).model_dump(mode="json")
    for field, value in changes.items():
        setattr(row, field, value)
    row.updated_by_user_id = user.id

    audit.record(
        db,
        actor_type=ActorType.ADMIN,
        actor_user_id=user.id,
        action="admin.settings_updated",
        details={"before": before, "changes": {k: str(v) for k, v in changes.items()}},
    )
    await db.commit()
    await db.refresh(row)
    return _settings_out(row)


# --- Audit log --------------------------------------------------------------


class AuditLogEntryOut(BaseModel):
    id: int
    created_at: datetime
    actor_type: str
    actor_user_id: str | None
    action: str
    return_id: str | None
    details: dict[str, Any]


@router.get("/audit-log", response_model=list[AuditLogEntryOut])
async def list_audit_log(
    _: Admin,
    db: DbSession,
    return_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[AuditLogEntryOut]:
    if not 1 <= limit <= 500:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "limit must be 1-500")
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if return_id is not None:
        stmt = stmt.where(AuditLog.return_id == return_id)
    rows = await db.scalars(stmt)
    return [
        AuditLogEntryOut(
            id=r.id,
            created_at=r.created_at,
            actor_type=r.actor_type.value,
            actor_user_id=str(r.actor_user_id) if r.actor_user_id else None,
            action=r.action,
            return_id=str(r.return_id) if r.return_id else None,
            details=r.details,
        )
        for r in rows
    ]

"""Admin: automation settings (editing arrives in M8)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from returnguard.auth import DbSession, require_role
from returnguard.models import Role, Settings, User

router = APIRouter(prefix="/api/admin", tags=["admin"])

Admin = Annotated[User, Depends(require_role(Role.ADMIN))]


class SettingsOut(BaseModel):
    automation_enabled: bool
    risk_limit: Decimal
    high_value_limit_cents: int
    qa_sample_rate: Decimal
    updated_at: datetime


@router.get("/settings", response_model=SettingsOut)
async def get_settings(_: Admin, db: DbSession) -> SettingsOut:
    row = await db.get_one(Settings, 1)
    return SettingsOut(
        automation_enabled=row.automation_enabled,
        risk_limit=row.risk_limit,
        high_value_limit_cents=row.high_value_limit_cents,
        qa_sample_rate=row.qa_sample_rate,
        updated_at=row.updated_at,
    )

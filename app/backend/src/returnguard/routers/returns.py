"""Returns: customers start and follow them; staff can view them.

Creating a return writes the return, its photo record, and a `jobs` row in one
transaction (the outbox pattern), so the pipeline worker (M4) can never miss a
submitted return. The photo itself is uploaded to object storage first; if the
transaction then fails, the orphaned object is deleted.
"""

import uuid
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from returnguard import audit
from returnguard.auth import CurrentSession, DbSession, require_role
from returnguard.config import get_settings
from returnguard.images import ProcessedPhoto, UploadRejected, process_upload
from returnguard.jobs import REVIEW_JOB
from returnguard.models import (
    ActorType,
    Job,
    Order,
    OrderItem,
    Return,
    ReturnPhoto,
    ReturnReason,
    ReturnStatus,
    Role,
    User,
)
from returnguard.pipeline.checks import PHOTO_REASONS
from returnguard.ratelimit import rate_limit
from returnguard.storage import StorageError, get_storage
from returnguard.wake import nudge_worker

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/returns", tags=["returns"])

Customer = Annotated[User, Depends(require_role(Role.CUSTOMER))]

MAX_NOTE_LENGTH = 1000


def customer_status(s: ReturnStatus) -> ReturnStatus:
    """What the customer sees: a pipeline failure looks like 'under review'."""
    return ReturnStatus.UNDER_REVIEW if s == ReturnStatus.FAILED else s


# --- Schemas ----------------------------------------------------------------


class PhotoOut(BaseModel):
    id: str
    url: str
    width: int | None
    height: int | None


class ReturnOut(BaseModel):
    id: str
    case_number: int
    order_number: int
    order_item_id: str
    product_name: str
    product_photo_url: str | None
    reason: ReturnReason
    reason_text: str
    refund_amount_cents: int
    status: ReturnStatus
    photo_required: bool
    photos: list[PhotoOut]
    decided_by_type: str | None
    customer_message: str | None
    created_at: datetime
    updated_at: datetime


def _return_out(
    r: Return, item: OrderItem, order: Order, photos: list[ReturnPhoto], *, staff: bool
) -> ReturnOut:
    return ReturnOut(
        id=str(r.id),
        case_number=r.case_number,
        order_number=order.order_number,
        order_item_id=str(item.id),
        product_name=item.product.name,
        product_photo_url=item.product.photo_key,
        reason=r.reason,
        reason_text=r.reason_text,
        refund_amount_cents=r.refund_amount_cents,
        status=r.status if staff else customer_status(r.status),
        photo_required=r.reason in PHOTO_REASONS,
        photos=[
            PhotoOut(
                id=str(p.id),
                url=f"/api/returns/{r.id}/photos/{p.id}",
                width=p.metadata_summary.get("width"),
                height=p.metadata_summary.get("height"),
            )
            for p in photos
        ],
        decided_by_type=r.decided_by_type.value if r.decided_by_type else None,
        customer_message=r.customer_message,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


async def _load(
    db: DbSession, return_id: uuid.UUID
) -> tuple[Return, OrderItem, Order, list[ReturnPhoto]]:
    # populate_existing: reload columns the database sets (e.g. updated_at) rather
    # than touching an expired attribute, which async SQLAlchemy can't lazy-load.
    ret = await db.scalar(
        select(Return).where(Return.id == return_id).execution_options(populate_existing=True)
    )
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return not found")
    item = await db.scalar(
        select(OrderItem)
        .where(OrderItem.id == ret.order_item_id)
        .options(selectinload(OrderItem.product), selectinload(OrderItem.order))
    )
    assert item is not None
    photos = list(
        await db.scalars(
            select(ReturnPhoto)
            .where(ReturnPhoto.return_id == ret.id)
            .order_by(ReturnPhoto.created_at)
        )
    )
    return ret, item, item.order, photos


def _can_see(user: User, ret: Return) -> bool:
    return user.role in (Role.REVIEWER, Role.ADMIN) or ret.customer_id == user.id


async def _read_photo(photo: UploadFile | None) -> ProcessedPhoto | None:
    """Validate and clean an uploaded photo; None if no file was sent."""
    if photo is None or not photo.filename:
        return None
    settings = get_settings()
    raw = await photo.read(settings.upload_max_bytes + 1)
    if len(raw) > settings.upload_max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Photos must be under {settings.upload_max_bytes // (1024 * 1024)} MB",
        )
    try:
        return process_upload(
            raw, max_pixels=settings.upload_max_pixels, max_side=settings.upload_max_side
        )
    except UploadRejected as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


async def _store_photo(db: DbSession, return_id: uuid.UUID, processed: ProcessedPhoto) -> str:
    """Upload to object storage and add the photo row. Rolls back on failure."""
    key = f"returns/{return_id}/{uuid.uuid4()}.jpg"
    try:
        await get_storage().put(key, processed.data, processed.content_type)
    except StorageError as exc:
        await db.rollback()  # discard anything half-created
        log.error("returns.photo_store_failed", error=str(exc))
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "We couldn't save your photo right now. Please try again.",
        ) from exc
    db.add(
        ReturnPhoto(
            return_id=return_id,
            storage_key=key,
            content_type=processed.content_type,
            size_bytes=len(processed.data),
            sha256=processed.sha256,
            perceptual_hash=processed.perceptual_hash,
            metadata_summary={
                **processed.metadata,
                "width": processed.width,
                "height": processed.height,
            },
        )
    )
    return key


async def _commit_or_cleanup(db: DbSession, key: str | None) -> None:
    """Commit; if that fails, delete the photo we already uploaded."""
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        if key is not None:
            try:
                await get_storage().delete(key)
            except StorageError:
                log.warning("returns.orphan_photo", key=key)
        raise


# --- Routes -----------------------------------------------------------------


@router.post(
    "",
    response_model=ReturnOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(get_settings().return_rate_limit, "returns"))],
)
async def start_return(
    user: Customer,
    db: DbSession,
    order_item_id: Annotated[uuid.UUID, Form()],
    reason: Annotated[ReturnReason, Form()],
    background: BackgroundTasks,
    reason_text: Annotated[str, Form(max_length=MAX_NOTE_LENGTH)] = "",
    photo: Annotated[UploadFile | None, File()] = None,
) -> ReturnOut:
    item = await db.scalar(
        select(OrderItem)
        .join(Order)
        .where(OrderItem.id == order_item_id, Order.customer_id == user.id)
        .options(selectinload(OrderItem.product), selectinload(OrderItem.order))
    )
    if item is None:  # someone else's item looks the same as a missing one
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order item not found")
    if item.order.delivered_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This item hasn't been delivered yet")
    if existing := await db.scalar(select(Return.id).where(Return.order_item_id == item.id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A return for this item already exists ({existing})",
        )

    processed = await _read_photo(photo)

    ret = Return(
        id=uuid.uuid4(),
        order_item_id=item.id,
        customer_id=user.id,
        reason=reason,
        reason_text=reason_text.strip(),
        refund_amount_cents=item.unit_price_cents * item.quantity,
        status=ReturnStatus.SUBMITTED,
    )
    db.add(ret)
    # Insert the return first: the photo, job, and audit rows reference it.
    await db.flush()

    key = await _store_photo(db, ret.id, processed) if processed is not None else None

    # Outbox: the job is committed together with the return, or not at all.
    db.add(Job(kind=REVIEW_JOB, return_id=ret.id))
    audit.record(
        db,
        actor_type=ActorType.CUSTOMER,
        actor_user_id=user.id,
        action="return.submitted",
        return_id=ret.id,
        details={
            "reason": reason.value,
            "refund_amount_cents": ret.refund_amount_cents,
            "photo": processed is not None,
        },
    )
    await _commit_or_cleanup(db, key)
    background.add_task(nudge_worker)

    log.info("return.submitted", case_number=ret.case_number, photo=processed is not None)
    ret, item, order, photos = await _load(db, ret.id)
    return _return_out(ret, item, order, photos, staff=False)


@router.post(
    "/{return_id}/photos",
    response_model=ReturnOut,
    dependencies=[Depends(rate_limit(get_settings().return_rate_limit, "returns"))],
)
async def add_photo(
    return_id: uuid.UUID,
    user: Customer,
    db: DbSession,
    background: BackgroundTasks,
    photo: Annotated[UploadFile, File()],
) -> ReturnOut:
    """Send the photo the data check asked for; the return is then reviewed again (M6)."""
    ret = await db.scalar(
        select(Return)
        .where(Return.id == return_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if ret is None or ret.customer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return not found")
    if ret.status is not ReturnStatus.NEEDS_INFO:
        raise HTTPException(status.HTTP_409_CONFLICT, "This return isn't waiting for a photo")
    processed = await _read_photo(photo)
    if processed is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please choose a photo.")

    key = await _store_photo(db, ret.id, processed)
    ret.status = ReturnStatus.SUBMITTED
    ret.route = None
    ret.customer_message = None
    db.add(Job(kind=REVIEW_JOB, return_id=ret.id))
    audit.record(
        db,
        actor_type=ActorType.CUSTOMER,
        actor_user_id=user.id,
        action="return.photo_added",
        return_id=ret.id,
    )
    await _commit_or_cleanup(db, key)
    background.add_task(nudge_worker)
    log.info("return.photo_added", case_number=ret.case_number)
    ret, item, order, photos = await _load(db, ret.id)
    return _return_out(ret, item, order, photos, staff=False)


@router.get("", response_model=list[ReturnOut])
async def list_my_returns(user: Customer, db: DbSession) -> list[ReturnOut]:
    returns = await db.scalars(
        select(Return).where(Return.customer_id == user.id).order_by(Return.created_at.desc())
    )
    out = []
    for r in list(returns):
        fresh, item, order, photos = await _load(db, r.id)
        out.append(_return_out(fresh, item, order, photos, staff=False))
    return out


@router.get("/{return_id}", response_model=ReturnOut)
async def get_return(return_id: uuid.UUID, session: CurrentSession, db: DbSession) -> ReturnOut:
    ret, item, order, photos = await _load(db, return_id)
    if not _can_see(session.user, ret):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return not found")
    staff = session.user.role in (Role.REVIEWER, Role.ADMIN)
    return _return_out(ret, item, order, photos, staff=staff)


@router.get(
    "/{return_id}/photos/{photo_id}",
    responses={200: {"content": {"image/jpeg": {}}}},
    response_class=Response,
)
async def get_return_photo(
    return_id: uuid.UUID, photo_id: uuid.UUID, session: CurrentSession, db: DbSession
) -> Response:
    ret = await db.get(Return, return_id)
    photo = await db.get(ReturnPhoto, photo_id)
    if ret is None or photo is None or photo.return_id != ret.id or not _can_see(session.user, ret):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")
    try:
        data = await get_storage().get(photo.storage_key)
    except StorageError as exc:
        log.error("returns.photo_read_failed", photo_id=str(photo.id), error=str(exc))
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Photo unavailable") from exc
    return Response(
        content=data,
        media_type=photo.content_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )

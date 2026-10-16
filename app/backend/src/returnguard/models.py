"""ORM models: every table in the data model (BUILD_PLAN.md section 9).

Conventions:
- UUID primary keys for anything exposed through the API (no guessable ids);
  bigint identities for append-only log tables.
- Money is stored as integer cents.
- Enumerations are VARCHAR + CHECK constraints (easy to extend in a migration),
  not native Postgres enums.
- Timestamps are timezone-aware and default to the database clock.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from returnguard.db import Base

EMBEDDING_DIMENSIONS = 1536  # OpenAI text-embedding-3-small


def _enum(cls: type[enum.Enum], name: str) -> Enum:
    return Enum(
        cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# --- Enumerations -----------------------------------------------------------


class Role(enum.StrEnum):
    CUSTOMER = "customer"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class ProductCategory(enum.StrEnum):
    FOOTWEAR = "footwear"
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    HOME = "home"


class ReturnReason(enum.StrEnum):
    DAMAGED = "damaged"  # damaged on arrival
    DEFECTIVE = "defective"  # manufacturing defect
    WRONG_ITEM = "wrong_item"
    NOT_AS_DESCRIBED = "not_as_described"
    CHANGED_MIND = "changed_mind"


class ReturnStatus(enum.StrEnum):
    NEEDS_INFO = "needs_info"  # waiting on the customer (M6)
    SUBMITTED = "submitted"
    CHECKING = "checking"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    FAILED = "failed"  # pipeline gave up; shown to the customer as under review


class Decision(enum.StrEnum):
    APPROVE = "approve"
    DENY = "deny"
    ESCALATE = "escalate"


class EvidenceStrength(enum.StrEnum):
    STRONG = "strong"
    MIXED = "mixed"
    WEAK = "weak"


class Route(enum.StrEnum):
    AUTO_APPROVED = "auto_approved"
    REVIEWER = "reviewer"
    CUSTOMER = "customer"  # missing evidence goes back to the customer


class EscalationReason(enum.StrEnum):
    """Named reasons a case is in the reviewer queue (BUILD_PLAN.md section 5)."""

    PIPELINE_ERROR = "pipeline_error"
    PROPOSED_DENIAL = "proposed_denial"
    AMBIGUOUS_CALL = "ambiguous_call"
    UNVERIFIED_PHOTO = "unverified_photo"
    CRITIC_CONCERN = "critic_concern"
    HIGH_VALUE = "high_value"
    ELEVATED_RISK = "elevated_risk"
    AUTOMATION_OFF = "automation_off"
    QA_SAMPLE = "qa_sample"
    CUSTOMER_REQUESTED_REVIEW = "customer_requested_review"


class DeciderType(enum.StrEnum):
    AUTO = "auto"
    PERSON = "person"


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ActorType(enum.StrEnum):
    SYSTEM = "system"
    CHECK = "check"
    AI = "ai"
    GATE = "gate"
    CUSTOMER = "customer"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class AgreementKind(enum.StrEnum):
    AGREEMENT = "agreement"
    OVERRIDE = "override"
    QA_SAMPLE = "qa_sample"


class ReviewRequestStatus(enum.StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


# --- People and sessions ----------------------------------------------------


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("uq_users_email_lower", func.lower(text("email")), unique=True),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(_enum(Role, "user_role"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = _created_at()


class Session(Base):
    """Server-side login session. Only a SHA-256 hash of the cookie token is stored."""

    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = _created_at()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(lazy="joined")


# --- Catalog and orders -----------------------------------------------------


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("price_cents > 0", name="price_positive"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    sku: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ProductCategory] = mapped_column(
        _enum(ProductCategory, "product_category"), nullable=False
    )
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_final_sale: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    photo_key: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = _created_at()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_number: Mapped[int] = mapped_column(
        BigInteger, Identity(start=1001), unique=True, nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipping_name: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_line1: Mapped[str] = mapped_column(String(200), nullable=False)
    shipping_city: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    # SHA-256 of the normalised address, used to find accounts sharing an address
    # without comparing raw addresses.
    address_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    card_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price_cents > 0", name="unit_price_positive"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


# --- Returns ----------------------------------------------------------------


class Return(Base):
    __tablename__ = "returns"
    __table_args__ = (
        CheckConstraint("refund_amount_cents > 0", name="refund_positive"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        # A denial is always made by a person (M1).
        CheckConstraint(
            "final_decision IS DISTINCT FROM 'deny' OR decided_by_type = 'person'",
            name="denial_needs_person",
        ),
        Index("ix_returns_status", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    case_number: Mapped[int] = mapped_column(
        BigInteger, Identity(start=201), unique=True, nullable=False
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    reason: Mapped[ReturnReason] = mapped_column(
        _enum(ReturnReason, "return_reason"), nullable=False
    )
    reason_text: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    refund_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReturnStatus] = mapped_column(
        _enum(ReturnStatus, "return_status"), nullable=False
    )

    # Pipeline results
    evidence_strength: Mapped[EvidenceStrength | None] = mapped_column(
        _enum(EvidenceStrength, "evidence_strength")
    )
    route: Mapped[Route | None] = mapped_column(_enum(Route, "return_route"))
    escalation_reason: Mapped[EscalationReason | None] = mapped_column(
        _enum(EscalationReason, "escalation_reason")
    )
    ai_proposal: Mapped[Decision | None] = mapped_column(_enum(Decision, "ai_proposal"))
    policy_version: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    # Final decision
    final_decision: Mapped[Decision | None] = mapped_column(_enum(Decision, "final_decision"))
    decided_by_type: Mapped[DeciderType | None] = mapped_column(_enum(DeciderType, "decider"))
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer_message: Mapped[str | None] = mapped_column(Text)

    # Reviewer claim, so two reviewers don't work the same case
    claimed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ReturnPhoto(Base):
    __tablename__ = "return_photos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    return_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    perceptual_hash: Mapped[str | None] = mapped_column(String(32))
    metadata_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = _created_at()


class ReviewRequest(Base):
    """A customer asking for a second look at a denial (S2)."""

    __tablename__ = "review_requests"
    __table_args__ = (
        CheckConstraint(
            "assigned_reviewer_id IS NULL OR assigned_reviewer_id <> original_decider_id",
            name="different_reviewer",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    return_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    customer_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    original_decider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ReviewRequestStatus] = mapped_column(
        _enum(ReviewRequestStatus, "review_request_status"),
        nullable=False,
        server_default=ReviewRequestStatus.OPEN.value,
    )
    outcome: Mapped[Decision | None] = mapped_column(_enum(Decision, "review_outcome"))
    created_at: Mapped[datetime] = _created_at()
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- Policy -----------------------------------------------------------------


class PolicyDoc(Base):
    __tablename__ = "policy_docs"
    __table_args__ = (
        # At most one active policy version.
        Index(
            "uq_policy_docs_active", "is_active", unique=True, postgresql_where=text("is_active")
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    version: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = _created_at()

    chunks: Mapped[list["PolicyChunk"]] = relationship(back_populates="policy_doc")


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"
    __table_args__ = (UniqueConstraint("policy_doc_id", "clause_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    policy_doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_docs.id", ondelete="CASCADE"), nullable=False
    )
    clause_id: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Filled in by the embedding job once the model client exists (M5/M6).
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))

    policy_doc: Mapped[PolicyDoc] = relationship(back_populates="chunks")


# --- Pipeline ---------------------------------------------------------------


class Job(Base):
    """Durable work queue; a row is written in the same transaction as the return."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_due", "status", "run_after"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    return_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("returns.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        _enum(JobStatus, "job_status"), nullable=False, server_default=JobStatus.QUEUED.value
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AgentRun(Base):
    """One pipeline step's execution: what ran, on what, at what cost."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    return_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[int | None] = mapped_column(Integer)
    policy_version: Mapped[int | None] = mapped_column(Integer)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()


class AgentRunEvent(Base):
    """Fine-grained events for the live trace view."""

    __tablename__ = "agent_run_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    return_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    step: Mapped[str] = mapped_column(String(50), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = _created_at()


# --- Governance -------------------------------------------------------------


class Settings(Base):
    """Admin-controlled automation settings. Exactly one row (id = 1)."""

    __tablename__ = "settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("risk_limit >= 0 AND risk_limit <= 1", name="risk_limit_range"),
        CheckConstraint("high_value_limit_cents > 0", name="high_value_positive"),
        CheckConstraint("qa_sample_rate >= 0 AND qa_sample_rate <= 1", name="qa_rate_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=1)
    automation_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    risk_limit: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, server_default=text("0.30")
    )
    high_value_limit_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("25000")
    )
    qa_sample_rate: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, server_default=text("0.10")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class AuditLog(Base):
    """Append-only record of every check, gate decision, and human action (C1).

    A database trigger rejects UPDATE, DELETE, and TRUNCATE (see migration 0002).
    """

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_return_created", "return_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    created_at: Mapped[datetime] = _created_at()
    actor_type: Mapped[ActorType] = mapped_column(_enum(ActorType, "actor_type"), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    return_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("returns.id"))
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class AgreementSample(Base):
    """AI proposal vs. human decision, for agreement tracking (S1)."""

    __tablename__ = "agreement_samples"

    id: Mapped[uuid.UUID] = _uuid_pk()
    return_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[AgreementKind] = mapped_column(
        _enum(AgreementKind, "agreement_kind"), nullable=False
    )
    ai_proposal: Mapped[Decision] = mapped_column(_enum(Decision, "sample_ai"), nullable=False)
    human_decision: Mapped[Decision] = mapped_column(
        _enum(Decision, "sample_human"), nullable=False
    )
    agreed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(String(100))
    product_category: Mapped[ProductCategory] = mapped_column(
        _enum(ProductCategory, "sample_category"), nullable=False
    )
    escalation_reason: Mapped[EscalationReason | None] = mapped_column(
        _enum(EscalationReason, "sample_reason")
    )
    created_at: Mapped[datetime] = _created_at()

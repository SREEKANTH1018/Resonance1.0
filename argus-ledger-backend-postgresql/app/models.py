"""SQLAlchemy ORM models for the ARGUS audit ledger.

These mirror ``database/init.sql`` column-for-column. ``init.sql`` stays the
authoritative schema for the Docker/production database; ``create_all`` is used
only as a local-dev convenience and is a no-op against an already-initialised DB.

Tables
------
decisions        one row per AI decision (+ policy + review state)
evidence         supporting sources for a decision
audit_events     append-only lifecycle log (DECISION_CREATED, HUMAN_REVIEW, ...)
resource_usage   latency / tokens / estimated energy + carbon per decision
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

_UUID_PK = dict(
    primary_key=True,
    default=uuid.uuid4,
    server_default=text("gen_random_uuid()"),
)
_TS = dict(server_default=func.now())


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'COMPLETED'")
    )
    reasons: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    policy_name: Mapped[str | None] = mapped_column(String(255))
    policy_version: Mapped[str | None] = mapped_column(String(100))
    human_review_required: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=text("false")
    )
    human_reviewer: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, **_TS
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, onupdate=func.now(), **_TS
    )

    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="Evidence.created_at",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="AuditEvent.created_at",
    )
    resource_usage: Mapped[list["ResourceUsage"]] = relationship(
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="ResourceUsage.created_at",
    )


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "relevance IS NULL OR (relevance >= 0 AND relevance <= 1)",
            name="relevance_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(500), nullable=False)
    page: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str | None] = mapped_column(Text)
    relevance: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, **_TS
    )

    decision: Mapped["Decision"] = relationship(back_populates="evidence")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, **_TS
    )

    decision: Mapped["Decision"] = relationship(back_populates="audit_events")


class ResourceUsage(Base):
    __tablename__ = "resource_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    tokens: Mapped[int | None] = mapped_column(Integer)
    energy_wh: Mapped[float | None] = mapped_column(Float)
    carbon_g: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, **_TS
    )

    decision: Mapped["Decision"] = relationship(back_populates="resource_usage")

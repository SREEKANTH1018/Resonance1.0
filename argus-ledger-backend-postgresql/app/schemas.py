"""Pydantic request/response contracts.

Two decision shapes exist on purpose and must not be merged:

* **flat** — what ``app.ai_service`` emits (``model`` / ``model_version`` as
  strings). See :class:`AIDecision`.
* **nested** — what the frontend consumes, per ``docs/API_CONTRACT.md``
  (``model: {name, version}``). See :class:`DecisionResponse`.

``app.services.to_decision_response`` is the single place that converts stored
rows into the nested shape.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #


class EvidenceCreate(BaseModel):
    source: str = Field(min_length=1, max_length=500)
    page: int | None = Field(default=None, ge=0)
    content: str | None = None
    relevance: float | None = Field(default=None, ge=0, le=1)
    reason: str | None = None


class ResourceCreate(BaseModel):
    latency_ms: int | None = Field(default=None, ge=0)
    tokens: int | None = Field(default=None, ge=0)
    energy_wh: float | None = Field(default=None, ge=0)
    carbon_g: float | None = Field(default=None, ge=0)


class DecisionCreate(BaseModel):
    """Persist a decision that some caller (AI service or integration) produced."""

    input_text: str = Field(min_length=1)
    decision: str = Field(min_length=1, max_length=50)
    confidence: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)
    evidence: list[EvidenceCreate] = Field(default_factory=list)
    model: str = Field(min_length=1, max_length=255)
    model_version: str = Field(min_length=1, max_length=100)
    policy_name: str | None = Field(default=None, max_length=255)
    policy_version: str | None = Field(default=None, max_length=100)
    human_review_required: bool = False
    resource: ResourceCreate | None = None


class AIGenerateRequest(BaseModel):
    """Ask the configured AI provider to produce *and* persist a decision."""

    input_text: str = Field(min_length=1)
    policy_name: str | None = Field(default=None, max_length=255)
    policy_version: str | None = Field(default=None, max_length=100)


class ReviewCreate(BaseModel):
    reviewer: str = Field(min_length=1, max_length=255)
    decision: str = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=1)


# --------------------------------------------------------------------------- #
# Response bodies
# --------------------------------------------------------------------------- #


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EvidenceRead(_ORM):
    id: UUID
    decision_id: UUID
    source: str
    page: int | None
    content: str | None
    relevance: float | None
    reason: str | None
    created_at: datetime


class ResourceRead(_ORM):
    latency_ms: int | None
    tokens: int | None
    energy_wh: float | None
    carbon_g: float | None


class AuditEventRead(_ORM):
    id: UUID
    decision_id: UUID
    event: str
    actor: str
    details: dict
    created_at: datetime


class ModelInfo(BaseModel):
    name: str
    version: str


class PolicyInfo(BaseModel):
    name: str
    version: str | None = None


class HumanReviewInfo(BaseModel):
    required: bool
    reviewer: str | None = None


class DecisionResponse(BaseModel):
    """Nested decision object — the contract in ``docs/API_CONTRACT.md``.

    ``decision_id`` is a UUID string (the ``ARG-001`` in the doc is illustrative).
    """

    decision_id: UUID
    decision: str
    confidence: float
    status: str
    reasons: list[str]
    evidence: list[EvidenceCreate]
    model: ModelInfo
    policy: PolicyInfo | None
    resource: ResourceRead | None
    human_review: HumanReviewInfo
    timestamp: datetime


class DecisionSummary(_ORM):
    """Compact row for the list endpoint / dashboard tables."""

    decision_id: UUID = Field(validation_alias="id")
    decision: str
    confidence: float
    status: str
    model: str
    model_version: str
    human_review_required: bool
    created_at: datetime


class DecisionCreatedResponse(BaseModel):
    decision_id: UUID
    status: str = "created"


class ReviewResponse(BaseModel):
    decision_id: UUID
    status: str = "reviewed"


class DashboardResponse(BaseModel):
    total_decisions: int
    high_risk_decisions: int
    pending_human_review: int
    average_trust_score: float
    decisions_by_outcome: dict[str, int]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str


# --------------------------------------------------------------------------- #
# AI boundary contract (flat) — mirrors app.ai_service output
# --------------------------------------------------------------------------- #


class AIDecision(BaseModel):
    decision: str
    confidence: float = Field(ge=0, le=1)
    reasons: list[str]
    evidence: list[EvidenceCreate] = Field(default_factory=list)
    model: str
    model_version: str
    resource: ResourceCreate | None = None

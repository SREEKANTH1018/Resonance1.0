"""Persistence and business rules for the audit ledger.

Pure data/DB logic — no FastAPI types, no model generation. Routers call these
functions; the AI boundary is only touched via a provider passed in from the
router layer.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .config import get_settings
from .models import AuditEvent, Decision, Evidence, ResourceUsage
from .schemas import (
    AIGenerateRequest,
    DecisionCreate,
    DecisionResponse,
    EvidenceCreate,
    HumanReviewInfo,
    ModelInfo,
    PolicyInfo,
    ResourceRead,
    ReviewCreate,
)

settings = get_settings()

_DECISION_LOADERS = (
    selectinload(Decision.evidence),
    selectinload(Decision.resource_usage),
    selectinload(Decision.audit_events),
)


def _needs_review(requested: bool, confidence: float) -> bool:
    """Force human review when confidence is at/below the configured threshold."""
    return bool(requested) or confidence <= settings.human_review_confidence_threshold


def create_decision(
    db: Session, payload: DecisionCreate, *, commit: bool = True
) -> Decision:
    """Insert a decision plus its evidence, resource usage and creation event.

    ``commit=False`` leaves the transaction open so the caller can add more rows
    (e.g. an ``AI_GENERATED`` event) and commit everything atomically.
    """
    decision = Decision(
        input_text=payload.input_text,
        decision=payload.decision,
        confidence=payload.confidence,
        model=payload.model,
        model_version=payload.model_version,
        reasons=list(payload.reasons),
        policy_name=payload.policy_name,
        policy_version=payload.policy_version,
        human_review_required=_needs_review(
            payload.human_review_required, payload.confidence
        ),
    )
    db.add(decision)
    db.flush()  # assign decision.id

    for item in payload.evidence:
        db.add(Evidence(decision_id=decision.id, **item.model_dump()))

    if payload.resource is not None:
        db.add(
            ResourceUsage(
                decision_id=decision.id,
                model=payload.model,
                **payload.resource.model_dump(),
            )
        )

    db.add(
        AuditEvent(
            decision_id=decision.id,
            event="DECISION_CREATED",
            actor="backend",
            details={
                "model": payload.model,
                "model_version": payload.model_version,
                "confidence": payload.confidence,
                "auto_review_flagged": decision.human_review_required
                and not payload.human_review_required,
            },
        )
    )

    if not commit:
        db.flush()
        return decision

    db.commit()
    return get_decision(db, decision.id)  # reload with relationships


def persist_ai_decision(
    db: Session, req: AIGenerateRequest, ai_result: dict
) -> Decision:
    """Bridge the flat AI output into a stored decision — one transaction."""
    payload = DecisionCreate(
        input_text=req.input_text,
        decision=ai_result["decision"],
        confidence=ai_result["confidence"],
        reasons=ai_result.get("reasons", []),
        evidence=[EvidenceCreate(**e) for e in ai_result.get("evidence", [])],
        model=ai_result["model"],
        model_version=ai_result["model_version"],
        policy_name=req.policy_name,
        policy_version=req.policy_version,
        resource=ai_result.get("resource"),
    )
    decision = create_decision(db, payload, commit=False)
    db.add(
        AuditEvent(
            decision_id=decision.id,
            event="AI_GENERATED",
            actor=f"ai:{ai_result['model']}"[:255],
            details={"model_version": ai_result["model_version"]},
        )
    )
    db.commit()
    return get_decision(db, decision.id)


def get_decision(db: Session, decision_id: UUID) -> Decision | None:
    stmt = (
        select(Decision)
        .where(Decision.id == decision_id)
        .options(*_DECISION_LOADERS)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_decisions(db: Session, *, limit: int = 50, offset: int = 0) -> list[Decision]:
    stmt = (
        select(Decision)
        .order_by(Decision.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars())


def list_audit(db: Session, decision_id: UUID) -> list[AuditEvent]:
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.decision_id == decision_id)
        .order_by(AuditEvent.created_at)
    )
    return list(db.execute(stmt).scalars())


def list_evidence(db: Session, decision_id: UUID) -> list[Evidence]:
    stmt = (
        select(Evidence)
        .where(Evidence.decision_id == decision_id)
        .order_by(Evidence.created_at)
    )
    return list(db.execute(stmt).scalars())


def review_decision(
    db: Session, decision_id: UUID, payload: ReviewCreate
) -> Decision | None:
    decision = db.get(Decision, decision_id)
    if decision is None:
        return None

    previous = decision.decision
    decision.decision = payload.decision
    decision.human_reviewer = payload.reviewer
    decision.human_review_required = False
    decision.status = "REVIEWED"

    db.add(
        AuditEvent(
            decision_id=decision.id,
            event="HUMAN_REVIEW",
            actor=payload.reviewer,
            details={
                "previous_decision": previous,
                "new_decision": payload.decision,
                "reason": payload.reason,
            },
        )
    )
    db.commit()
    return get_decision(db, decision_id)


def dashboard_stats(db: Session) -> dict:
    total = db.scalar(select(func.count(Decision.id))) or 0
    high_risk = (
        db.scalar(
            select(func.count(Decision.id)).where(
                Decision.confidence < settings.human_review_confidence_threshold
            )
        )
        or 0
    )
    pending = (
        db.scalar(
            select(func.count(Decision.id)).where(
                Decision.human_review_required.is_(True)
            )
        )
        or 0
    )
    avg_conf = db.scalar(select(func.avg(Decision.confidence)))
    by_outcome = dict(
        db.execute(
            select(Decision.decision, func.count(Decision.id)).group_by(
                Decision.decision
            )
        ).all()
    )
    return {
        "total_decisions": int(total),
        "high_risk_decisions": int(high_risk),
        "pending_human_review": int(pending),
        "average_trust_score": round(float(avg_conf or 0.0), 4),
        "decisions_by_outcome": {k: int(v) for k, v in by_outcome.items()},
    }


def to_decision_response(decision: Decision) -> DecisionResponse:
    """Stored row -> nested contract shape (docs/API_CONTRACT.md)."""
    resource = decision.resource_usage[0] if decision.resource_usage else None
    policy = (
        PolicyInfo(name=decision.policy_name, version=decision.policy_version)
        if decision.policy_name
        else None
    )
    return DecisionResponse(
        decision_id=decision.id,
        decision=decision.decision,
        confidence=decision.confidence,
        status=decision.status,
        reasons=list(decision.reasons or []),
        evidence=[
            EvidenceCreate(
                source=e.source,
                page=e.page,
                content=e.content,
                relevance=e.relevance,
                reason=e.reason,
            )
            for e in decision.evidence
        ],
        model=ModelInfo(name=decision.model, version=decision.model_version),
        policy=policy,
        resource=ResourceRead.model_validate(resource) if resource else None,
        human_review=HumanReviewInfo(
            required=decision.human_review_required,
            reviewer=decision.human_reviewer,
        ),
        timestamp=decision.created_at,
    )

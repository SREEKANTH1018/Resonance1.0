"""Decision lifecycle: create, generate, read, audit, evidence, human review."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import services
from ..ai_service import get_ai_provider
from ..database import get_db
from ..schemas import (
    AIGenerateRequest,
    AuditEventRead,
    DecisionCreate,
    DecisionCreatedResponse,
    DecisionResponse,
    DecisionSummary,
    EvidenceRead,
    ReviewCreate,
    ReviewResponse,
)

router = APIRouter(prefix="/decisions", tags=["decisions"])


def _get_or_404(db: Session, decision_id: UUID):
    decision = services.get_decision(db, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.post(
    "", response_model=DecisionCreatedResponse, status_code=status.HTTP_201_CREATED
)
def create_decision(
    payload: DecisionCreate, db: Session = Depends(get_db)
) -> DecisionCreatedResponse:
    decision = services.create_decision(db, payload)
    return DecisionCreatedResponse(decision_id=decision.id, status="created")


@router.post(
    "/generate",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_decision(
    payload: AIGenerateRequest, db: Session = Depends(get_db)
) -> DecisionResponse:
    """Run the configured AI provider and persist the resulting decision."""
    provider = get_ai_provider()
    try:
        result = provider.generate(
            payload.input_text,
            policy_name=payload.policy_name,
            policy_version=payload.policy_version,
        )
    except Exception as exc:  # model failure — TEST_CASES #5
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI provider failed: {exc}",
        ) from exc
    decision = services.persist_ai_decision(db, payload, result)
    return services.to_decision_response(decision)


@router.get("", response_model=list[DecisionSummary])
def list_decisions(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[DecisionSummary]:
    return services.list_decisions(db, limit=limit, offset=offset)


@router.get("/{decision_id}", response_model=DecisionResponse)
def get_decision(
    decision_id: UUID, db: Session = Depends(get_db)
) -> DecisionResponse:
    return services.to_decision_response(_get_or_404(db, decision_id))


@router.get("/{decision_id}/audit", response_model=list[AuditEventRead])
def get_audit(
    decision_id: UUID, db: Session = Depends(get_db)
) -> list[AuditEventRead]:
    _get_or_404(db, decision_id)
    return services.list_audit(db, decision_id)


@router.get("/{decision_id}/evidence", response_model=list[EvidenceRead])
def get_evidence(
    decision_id: UUID, db: Session = Depends(get_db)
) -> list[EvidenceRead]:
    _get_or_404(db, decision_id)
    return services.list_evidence(db, decision_id)


@router.post("/{decision_id}/review", response_model=ReviewResponse)
def review_decision(
    decision_id: UUID, payload: ReviewCreate, db: Session = Depends(get_db)
) -> ReviewResponse:
    decision = services.review_decision(db, decision_id, payload)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return ReviewResponse(decision_id=decision.id, status="reviewed")

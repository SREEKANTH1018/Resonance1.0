"""POST /decisions/generate — AI provider -> persisted decision."""

import pytest

from app import ai_service


def test_generate_persists_and_returns_nested_decision(client):
    resp = client.post(
        "/decisions/generate",
        json={
            "input_text": "New applicant: standard onboarding request.",
            "policy_name": "Policy-01",
            "policy_version": "3.1",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["decision"] in {"APPROVED", "REJECTED"}
    assert body["model"]["name"] == ai_service.StubAIProvider.model_name
    assert body["policy"] == {"name": "Policy-01", "version": "3.1"}
    assert body["resource"]["tokens"] > 0

    events = client.get(f"/decisions/{body['decision_id']}/audit").json()
    assert {e["event"] for e in events} == {"DECISION_CREATED", "AI_GENERATED"}


def test_generated_decision_shows_in_list_and_dashboard(client):
    client.post("/decisions/generate", json={"input_text": "routine request"})
    assert client.get("/dashboard").json()["total_decisions"] == 1
    assert len(client.get("/decisions").json()) == 1


def test_model_failure_returns_502(client, monkeypatch):
    """TEST_CASES #5 — provider raising is surfaced as 502, nothing persisted."""

    class BrokenProvider:
        name = "broken"

        def generate(self, *a, **k):
            raise RuntimeError("model unavailable")

    monkeypatch.setitem(ai_service._PROVIDERS, "stub", BrokenProvider())

    resp = client.post("/decisions/generate", json={"input_text": "anything"})
    assert resp.status_code == 502
    assert "model unavailable" in resp.json()["detail"]
    assert client.get("/dashboard").json()["total_decisions"] == 0


def test_generate_path_commits_exactly_once(client, monkeypatch):
    """persist_ai_decision must be a single transaction (advisor finding)."""
    from sqlalchemy.orm import Session

    real_commit = Session.commit
    commits = []

    def counting_commit(self):
        commits.append(1)
        return real_commit(self)

    monkeypatch.setattr(Session, "commit", counting_commit)

    resp = client.post("/decisions/generate", json={"input_text": "routine request"})
    assert resp.status_code == 201
    assert sum(commits) == 1  # was 2 before the fix


def test_generate_persistence_is_atomic(engine, monkeypatch):
    """A failure writing the AI_GENERATED event rolls back the whole decision.

    Uses independent sessions (not the savepoint-wrapped ``db`` fixture) so the
    real commit/rollback boundary is exercised.
    """
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session

    from app import services
    from app.models import AuditEvent as AuditEventModel
    from app.schemas import AIGenerateRequest

    real_audit = services.AuditEvent

    def exploding_audit(*args, **kwargs):
        if kwargs.get("event") == "AI_GENERATED":
            raise SQLAlchemyError("boom writing audit event")
        return real_audit(*args, **kwargs)

    monkeypatch.setattr(services, "AuditEvent", exploding_audit)

    ai_result = ai_service.get_ai_provider().generate("routine request")
    with Session(engine) as s:
        with pytest.raises(SQLAlchemyError):
            services.persist_ai_decision(
                s, AIGenerateRequest(input_text="routine request"), ai_result
            )

    with Session(engine) as s:
        assert services.list_decisions(s) == []
        assert s.query(AuditEventModel).count() == 0

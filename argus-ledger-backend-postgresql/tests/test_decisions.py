"""Decision create / read / audit / evidence paths and their edge cases."""

import uuid

import pytest


def _create(client, payload) -> str:
    resp = client.post("/decisions", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["decision_id"]


def test_normal_decision_roundtrip(client, sample_payload):
    """TEST_CASES #1 — create then read back in the nested contract shape."""
    decision_id = _create(client, sample_payload)

    resp = client.get(f"/decisions/{decision_id}")
    assert resp.status_code == 200
    body = resp.json()

    assert body["decision_id"] == decision_id
    assert body["decision"] == "APPROVED"
    assert body["confidence"] == pytest.approx(0.91)
    assert body["model"] == {"name": "Model-A", "version": "1.2"}
    assert body["policy"] == {"name": "Policy-01", "version": "3.1"}
    assert body["resource"]["tokens"] == 1820
    assert body["human_review"] == {"required": False, "reviewer": None}
    assert body["reasons"] == ["Eligibility satisfied", "Risk below threshold"]
    assert body["evidence"][0]["source"] == "policy.pdf"
    assert "timestamp" in body


def test_creation_writes_audit_event(client, sample_payload):
    decision_id = _create(client, sample_payload)
    events = client.get(f"/decisions/{decision_id}/audit").json()
    assert [e["event"] for e in events] == ["DECISION_CREATED"]
    assert events[0]["actor"] == "backend"


def test_evidence_endpoint(client, sample_payload):
    decision_id = _create(client, sample_payload)
    evidence = client.get(f"/decisions/{decision_id}/evidence").json()
    assert len(evidence) == 1
    assert evidence[0]["relevance"] == pytest.approx(0.96)
    assert evidence[0]["decision_id"] == decision_id


def test_missing_evidence_is_allowed(client, sample_payload):
    """TEST_CASES #2 — evidence is optional."""
    sample_payload["evidence"] = []
    decision_id = _create(client, sample_payload)
    assert client.get(f"/decisions/{decision_id}/evidence").json() == []


def test_low_confidence_auto_flags_human_review(client, sample_payload):
    """TEST_CASES #4 — confidence <= threshold forces review even if caller said False."""
    sample_payload["confidence"] = 0.42
    sample_payload["human_review_required"] = False
    decision_id = _create(client, sample_payload)

    body = client.get(f"/decisions/{decision_id}").json()
    assert body["human_review"]["required"] is True

    events = client.get(f"/decisions/{decision_id}/audit").json()
    assert events[0]["details"]["auto_review_flagged"] is True


def test_unknown_decision_returns_404(client):
    """TEST_CASES #8 — missing resource."""
    assert client.get(f"/decisions/{uuid.uuid4()}").status_code == 404
    assert client.get(f"/decisions/{uuid.uuid4()}/audit").status_code == 404


@pytest.mark.parametrize(
    "mutation",
    [
        {"confidence": 1.5},
        {"confidence": -0.1},
        {"input_text": ""},
        {"decision": ""},
        {"model": ""},
    ],
)
def test_invalid_input_rejected_with_422(client, sample_payload, mutation):
    """TEST_CASES #7 — invalid input."""
    sample_payload.update(mutation)
    assert client.post("/decisions", json=sample_payload).status_code == 422


def test_list_decisions_returns_summaries(client, sample_payload):
    first = _create(client, sample_payload)
    sample_payload["input_text"] = "second application"
    second = _create(client, sample_payload)

    rows = client.get("/decisions").json()
    assert {first, second} == {r["decision_id"] for r in rows}
    assert {"decision", "confidence", "model", "model_version", "created_at"} <= rows[
        0
    ].keys()
    # newest-first ordering (created_at is non-decreasing in insertion order)
    times = [r["created_at"] for r in rows]
    assert times == sorted(times, reverse=True)


def test_list_pagination(client, sample_payload):
    for _ in range(3):
        _create(client, sample_payload)
    assert len(client.get("/decisions?limit=2").json()) == 2
    assert len(client.get("/decisions?limit=2&offset=2").json()) == 1

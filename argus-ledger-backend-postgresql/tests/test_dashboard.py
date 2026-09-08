"""Dashboard aggregates."""


def _create(client, payload):
    return client.post("/decisions", json=payload).json()["decision_id"]


def test_dashboard_counts_and_trust_score(client, sample_payload):
    # empty to start (per-test rollback)
    empty = client.get("/dashboard").json()
    assert empty["total_decisions"] == 0
    assert empty["average_trust_score"] == 0.0

    sample_payload["confidence"] = 0.9
    _create(client, sample_payload)
    sample_payload["confidence"] = 0.5  # high risk + auto review
    sample_payload["decision"] = "REJECTED"
    _create(client, sample_payload)

    body = client.get("/dashboard").json()
    assert body["total_decisions"] == 2
    assert body["high_risk_decisions"] == 1
    assert body["pending_human_review"] == 1
    assert body["average_trust_score"] == 0.7
    assert body["decisions_by_outcome"] == {"APPROVED": 1, "REJECTED": 1}

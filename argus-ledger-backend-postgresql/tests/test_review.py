"""Human review / override path (TEST_CASES #6)."""


def _create(client, payload) -> str:
    return client.post("/decisions", json=payload).json()["decision_id"]


def test_human_override_updates_decision_and_ledger(client, sample_payload):
    sample_payload["decision"] = "REJECTED"
    sample_payload["confidence"] = 0.4  # also auto-flags review
    decision_id = _create(client, sample_payload)

    resp = client.post(
        f"/decisions/{decision_id}/review",
        json={
            "reviewer": "analyst.jordan",
            "decision": "APPROVED",
            "reason": "Additional documents provided",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"decision_id": decision_id, "status": "reviewed"}

    body = client.get(f"/decisions/{decision_id}").json()
    assert body["decision"] == "APPROVED"
    assert body["status"] == "REVIEWED"
    assert body["human_review"] == {"required": False, "reviewer": "analyst.jordan"}

    events = client.get(f"/decisions/{decision_id}/audit").json()
    assert [e["event"] for e in events] == ["DECISION_CREATED", "HUMAN_REVIEW"]
    review = events[-1]
    assert review["actor"] == "analyst.jordan"
    assert review["details"]["previous_decision"] == "REJECTED"
    assert review["details"]["new_decision"] == "APPROVED"


def test_review_unknown_decision_404(client):
    resp = client.post(
        "/decisions/00000000-0000-0000-0000-000000000000/review",
        json={"reviewer": "x", "decision": "APPROVED", "reason": "y"},
    )
    assert resp.status_code == 404

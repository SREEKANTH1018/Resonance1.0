"""AI boundary contract — the shape app.services relies on (TEST_CASES #11, #12)."""

from app.ai_service import StubAIProvider, generate_decision, get_ai_provider


def test_ai_contract():
    result = generate_decision("demo application")
    assert result["decision"] in {"APPROVED", "REJECTED"}
    assert 0 <= result["confidence"] <= 1
    assert isinstance(result["reasons"], list)
    assert "model" in result
    assert "model_version" in result


def test_provider_is_swappable():
    provider = get_ai_provider()
    assert isinstance(provider, StubAIProvider)
    assert hasattr(provider, "generate")


def test_stub_is_deterministic_for_replay():
    a = generate_decision("same application text")
    b = generate_decision("same application text")
    assert a == b


def test_reject_markers_flip_the_outcome():
    approved = generate_decision("routine onboarding request")
    rejected = generate_decision("sanction list match, likely fraud")
    assert approved["decision"] == "APPROVED"
    assert rejected["decision"] == "REJECTED"
    assert rejected["confidence"] < approved["confidence"]


def test_evidence_and_resource_present():
    result = generate_decision("application with policy context")
    assert result["evidence"] and result["evidence"][0]["source"]
    assert result["resource"]["tokens"] > 0

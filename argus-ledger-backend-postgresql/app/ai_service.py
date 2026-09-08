"""AI boundary — owned by Member 3.

The persistence/API layer never imports a model. It only calls a provider that
satisfies :class:`AIProvider` and returns the **flat** decision dict described
below. Member 3 swaps the implementation by registering a provider in
:data:`_PROVIDERS` and pointing ``AI_PROVIDER`` at it — nothing in
``app/main.py``, ``app/services.py`` or the database layer changes.

Flat contract returned by ``generate``::

    {
        "decision":       "APPROVED" | "REJECTED" | ...,
        "confidence":     0.0 - 1.0,
        "reasons":        [str, ...],
        "evidence":       [{"source", "page", "content", "relevance", "reason"}, ...],
        "model":          str,
        "model_version":  str,
        "resource":       {"latency_ms", "tokens", "energy_wh", "carbon_g"} | None,
    }
"""

from __future__ import annotations

import hashlib
from typing import Any, Protocol, runtime_checkable

from .config import Settings, get_settings

_REJECT_MARKERS = ("fraud", "deny", "denied", "reject", "blacklist", "sanction")
_REVIEW_MARKERS = ("appeal", "exception", "override", "manual", "urgent")


@runtime_checkable
class AIProvider(Protocol):
    """Anything the backend will accept as a decision source."""

    name: str

    def generate(
        self,
        input_text: str,
        *,
        policy_name: str | None = None,
        policy_version: str | None = None,
    ) -> dict[str, Any]: ...


class StubAIProvider:
    """Deterministic placeholder so the pipeline runs end-to-end without a model.

    Output is a pure function of ``input_text`` (seeded by its SHA-256) so replay
    and comparison tests are stable.
    """

    name = "stub"
    model_name = "ARGUS-Stub"
    model_version = "0.1.0"

    def generate(
        self,
        input_text: str,
        *,
        policy_name: str | None = None,
        policy_version: str | None = None,
    ) -> dict[str, Any]:
        text = input_text.lower().strip()
        seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")

        rejected = any(marker in text for marker in _REJECT_MARKERS)
        needs_review = any(marker in text for marker in _REVIEW_MARKERS)

        # Confidence: deterministic in [0.55, 0.99]; rejections skew lower.
        base = 0.55 + (seed % 4500) / 10000
        confidence = round(base - (0.15 if rejected else 0.0), 4)
        confidence = max(0.05, min(confidence, 0.99))

        decision = "REJECTED" if rejected else "APPROVED"
        reasons = (
            ["Matched a disqualifying marker in the request", "Risk above threshold"]
            if rejected
            else ["Eligibility criteria satisfied", "Risk below threshold"]
        )
        if needs_review:
            reasons.append("Flagged for manual review by request content")

        evidence = [
            {
                "source": policy_name or "policy.pdf",
                "page": 1 + (seed % 12),
                "content": "Relevant clause extracted by the stub retriever.",
                "relevance": round(0.80 + (seed % 1900) / 10000, 4),
                "reason": "Primary basis for the decision",
            }
        ]

        tokens = 400 + (seed % 2000)
        latency_ms = 120 + (seed % 900)
        return {
            "decision": decision,
            "confidence": confidence,
            "reasons": reasons,
            "evidence": evidence,
            "model": self.model_name,
            "model_version": self.model_version,
            "resource": {
                "latency_ms": latency_ms,
                "tokens": tokens,
                "energy_wh": round(tokens * 1.1e-5, 6),
                "carbon_g": round(tokens * 4.5e-6, 6),
            },
        }


class EngineAIProvider:
    """Calls the teammate's separately trained decision engine over HTTP.

    Selected with ``AI_PROVIDER=engine``. Configured entirely from the
    environment (read at call time, so a restart is never needed after editing
    ``.env``):

        ARGUS_DECISION_ENGINE_URL              required, e.g. http://127.0.0.1:9000
        ARGUS_DECISION_ENGINE_API_KEY          sent as ``Authorization: Bearer``
        ARGUS_DECISION_ENGINE_PATH             default ``/v1/decision``
        ARGUS_DECISION_ENGINE_TIMEOUT_SECONDS  default ``60``

    The engine is expected to return the flat contract at the top of this module
    (``decision``/``confidence``/``reasons``/``evidence``/``model``/
    ``model_version``/``resource``). A ``model: {name, version}`` object and a
    ``status``/``label`` alias for ``decision`` are also accepted. Any failure
    raises ``RuntimeError`` — ``POST /decisions/generate`` turns that into a 502.
    """

    name = "engine"

    def generate(
        self,
        input_text: str,
        *,
        policy_name: str | None = None,
        policy_version: str | None = None,
    ) -> dict[str, Any]:
        import os

        base = os.getenv("ARGUS_DECISION_ENGINE_URL", "").rstrip("/")
        if not base:
            raise RuntimeError(
                "AI_PROVIDER=engine but ARGUS_DECISION_ENGINE_URL is not set"
            )
        url = base + os.getenv("ARGUS_DECISION_ENGINE_PATH", "/v1/decision")
        timeout = float(os.getenv("ARGUS_DECISION_ENGINE_TIMEOUT_SECONDS", "60"))
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("ARGUS_DECISION_ENGINE_API_KEY", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        import httpx

        try:
            response = httpx.post(
                url,
                json={
                    "input_text": input_text,
                    "policy_name": policy_name,
                    "policy_version": policy_version,
                },
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"decision engine request failed: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("decision engine returned non-JSON") from exc

        return self._to_flat(data)

    @staticmethod
    def _to_flat(data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise RuntimeError("decision engine response is not a JSON object")

        decision = data.get("decision") or data.get("status") or data.get("label")
        if decision is None or "confidence" not in data:
            raise RuntimeError(
                f"decision engine response missing decision/confidence: {sorted(data)}"
            )

        model = data.get("model")
        if isinstance(model, dict):
            model_name = model.get("name") or "engine"
            model_version = model.get("version") or data.get("model_version") or "0"
        else:
            model_name = model or "engine"
            model_version = data.get("model_version") or "0"

        evidence = [
            {
                "source": e.get("source") or e.get("url") or "engine",
                "page": e.get("page"),
                "content": e.get("content") or e.get("snippet"),
                "relevance": e.get("relevance") if e.get("relevance") is not None else e.get("score"),
                "reason": e.get("reason"),
            }
            for e in (data.get("evidence") or [])
            if isinstance(e, dict)
        ]

        return {
            "decision": str(decision),
            "confidence": float(data["confidence"]),
            "reasons": list(data.get("reasons") or []),
            "evidence": evidence,
            "model": str(model_name),
            "model_version": str(model_version),
            "resource": data.get("resource"),
        }


# Member 3: add real providers here, e.g. {"rag": RagAIProvider()}.
_PROVIDERS: dict[str, AIProvider] = {
    "stub": StubAIProvider(),
    "engine": EngineAIProvider(),
}


def get_ai_provider(settings: Settings | None = None) -> AIProvider:
    """Return the configured provider (``AI_PROVIDER``, default ``stub``)."""
    settings = settings or get_settings()
    try:
        return _PROVIDERS[settings.ai_provider]
    except KeyError:
        raise ValueError(
            f"Unknown AI_PROVIDER {settings.ai_provider!r}; "
            f"known: {sorted(_PROVIDERS)}"
        ) from None


def generate_decision(input_text: str) -> dict[str, Any]:
    """Backwards-compatible convenience wrapper around the default provider."""
    return get_ai_provider().generate(input_text)

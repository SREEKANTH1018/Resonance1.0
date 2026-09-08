"""Claim -> retrieve -> evaluate loop, hardened for partial configuration.

Every external call (Tavily, OCR, the monolithic AI engine, and each pluggable
engine in ``app/integrations/engines``) is optional. A failure or an unconfigured
provider becomes a ``warnings`` entry and the request still returns 200 with
whatever could be produced. Nothing in here raises out to the route.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from .ai_engine_client import AIEngineClient
from .config import config
from .engines import get_engine
from .ocr_client import OCRClient
from .retrieval_client import RetrievalClient


@dataclass
class VerificationResult:
    status: str
    confidence: float
    claims: list
    sources: list
    media_analysis: dict
    iterations: int
    warnings: list
    engines: dict  # per-engine raw output: claim_extractor / claim_classifier / source_credibility

    def as_dict(self):
        return asdict(self)


async def _safe(label, coro, warnings):
    """Await ``coro``; on ANY failure record a warning and return None.

    An ``{"enabled": false}`` adapter response is also treated as "not
    available": its reason is surfaced as a warning and None is returned.
    """
    try:
        result = await coro
    except Exception as exc:  # noqa: BLE001 - integration calls must never break the request
        warnings.append(f"{label}: {exc}")
        return None
    if isinstance(result, dict) and result.get("enabled") is False:
        warnings.append(
            f"{label}: {result.get('reason') or result.get('error') or 'not configured'}"
        )
        return None
    return result


class VerificationOrchestrator:
    def __init__(self):
        self.ai = AIEngineClient()
        self.retrieval = RetrievalClient()
        self.ocr = OCRClient()

    async def verify(self, *, text="", url=None, image_bytes=None, filename="input"):
        warnings: list = []
        sources: list = []
        claims: list = []
        media: dict = {}
        engines: dict = {}

        # 1. Submitted URL -> extracted article text + source row.
        if url:
            extracted = await _safe("url_extraction", self.retrieval.extract(url), warnings)
            if extracted:
                for item in extracted.get("results", []):
                    sources.append({
                        "url": item.get("url"),
                        "content": item.get("raw_content") or item.get("content"),
                        "retrieval_score": item.get("score"),
                        "source_type": "submitted_url",
                    })
                if extracted.get("results") and not text:
                    first = extracted["results"][0]
                    text = first.get("raw_content") or first.get("content", "")

        # 2. Submitted image -> OCR text + legacy vision / deepfake analysis.
        if image_bytes:
            payload = {
                "filename": filename,
                "image_base64": base64.b64encode(image_bytes).decode("ascii"),
            }
            ocr = await _safe("ocr", self.ocr.analyze(image_bytes, filename), warnings)
            if ocr:
                media["ocr"] = ocr
                if ocr.get("text"):
                    text = f"{text}\n{ocr['text']}".strip()
            image_res = await _safe("image_analysis", self.ai.image_analysis(payload), warnings)
            if image_res:
                media["image"] = image_res
            deepfake_res = await _safe("deepfake", self.ai.deepfake(payload), warnings)
            if deepfake_res:
                media["deepfake"] = deepfake_res

        if not text:
            return VerificationResult(
                "INSUFFICIENT_EVIDENCE", 0.0, [], sources, media, 0,
                warnings + ["No text/claim content available for verification"],
                engines,
            )

        # 3. Engine: pull check-worthy claims / stance / entities.
        extractor_out = await _safe(
            "engine.claim_extractor", get_engine("claim_extractor").extract(text), warnings
        )
        if extractor_out:
            engines["claim_extractor"] = extractor_out
            claims = extractor_out.get("claims", []) or claims

        # 4. Engine: fake-news / claim classifier.
        classifier_out = await _safe(
            "engine.claim_classifier", get_engine("claim_classifier").classify(text), warnings
        )
        if classifier_out:
            engines["claim_classifier"] = classifier_out

        # 5. Bounded retrieve -> decide loop against the monolithic AI engine.
        query = text[:2000]
        iterations = 0
        got_decision = False
        status, confidence = "UNCERTAIN", 0.0

        for iteration in range(1, config.max_retrieval_iterations + 1):
            iterations = iteration
            search = await _safe("web_search", self.retrieval.search(query), warnings)
            if not search:
                break
            for item in search.get("results", []):
                sources.append({
                    "url": item.get("url"),
                    "title": item.get("title"),
                    "content": item.get("raw_content") or item.get("content"),
                    "retrieval_score": item.get("score"),
                    "source_type": "web_search",
                })

            decision = await _safe(
                "decision_engine",
                self.ai.decision({"text": text, "sources": sources, "iteration": iteration}),
                warnings,
            )
            if not decision:
                break
            got_decision = True
            claims = decision.get("claims", claims)
            status = decision.get("status", "UNCERTAIN")
            confidence = float(decision.get("confidence", 0.0) or 0.0)
            if confidence >= config.min_evidence_score:
                break
            query = decision.get("next_query") or (
                f"{text[:800]} independent primary source evidence"
            )

        # 6. Engine: credibility score per distinct source domain.
        cred = await self._score_sources(sources, warnings)
        if cred:
            engines["source_credibility"] = cred

        if not got_decision:
            status = "UNCERTAIN" if sources else "INSUFFICIENT_EVIDENCE"
            confidence = 0.0

        return VerificationResult(
            status, confidence, claims, sources, media, iterations, warnings, engines
        )

    async def _score_sources(self, sources, warnings):
        engine = get_engine("source_credibility")
        scored: dict = {}
        seen: set = set()
        for item in sources:
            host = urlparse(item.get("url") or "").hostname
            if not host or host in seen:
                continue
            seen.add(host)
            if len(seen) > 10:
                break
            out = await _safe(
                f"engine.source_credibility[{host}]", engine.score(domain=host), warnings
            )
            if out:
                scored[host] = out
        return scored or None

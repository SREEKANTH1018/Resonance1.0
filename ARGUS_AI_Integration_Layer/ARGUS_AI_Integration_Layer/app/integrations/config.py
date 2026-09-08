import os
from dataclasses import dataclass

def _int(name, default):
    return int(os.getenv(name, str(default)))

def _float(name, default):
    return float(os.getenv(name, str(default)))

@dataclass(frozen=True)
class IntegrationConfig:
    ai_engine_url: str = os.getenv("ARGUS_AI_ENGINE_URL", "").rstrip("/")
    ai_engine_api_key: str = os.getenv("ARGUS_AI_ENGINE_API_KEY", "")
    ai_decision_path: str = os.getenv("ARGUS_AI_DECISION_PATH", "/v1/decision")
    ai_ocr_path: str = os.getenv("ARGUS_AI_OCR_PATH", "/v1/ocr")
    ai_image_path: str = os.getenv("ARGUS_AI_IMAGE_PATH", "/v1/image-analysis")
    ai_deepfake_path: str = os.getenv("ARGUS_AI_DEEPFAKE_PATH", "/v1/deepfake")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    tavily_max_results: int = _int("TAVILY_MAX_RESULTS", 5)
    llm_provider: str = os.getenv("LLM_PROVIDER", "disabled")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    max_retrieval_iterations: int = _int("MAX_RETRIEVAL_ITERATIONS", 3)
    min_evidence_score: float = _float("MIN_EVIDENCE_SCORE", 0.70)
    min_source_reliability: float = _float("MIN_SOURCE_RELIABILITY", 0.70)
    ai_engine_timeout: int = _int("AI_ENGINE_TIMEOUT_SECONDS", 60)
    search_timeout: int = _int("SEARCH_TIMEOUT_SECONDS", 30)
    ocr_timeout: int = _int("OCR_TIMEOUT_SECONDS", 30)

config = IntegrationConfig()

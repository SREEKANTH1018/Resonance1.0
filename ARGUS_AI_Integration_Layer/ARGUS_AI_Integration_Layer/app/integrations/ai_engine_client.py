from .config import config
from .http_client import post_json, IntegrationHTTPError

class AIEngineClient:
    # HTTP adapter for the teammate's separately trained service.

    def _url(self, path):
        if not config.ai_engine_url:
            raise IntegrationHTTPError("ARGUS_AI_ENGINE_URL is not configured.")
        return f"{config.ai_engine_url}{path}"

    async def decision(self, payload):
        return await post_json(
            self._url(config.ai_decision_path), payload,
            api_key=config.ai_engine_api_key,
            timeout=config.ai_engine_timeout,
        )

    async def ocr(self, payload):
        return await post_json(
            self._url(config.ai_ocr_path), payload,
            api_key=config.ai_engine_api_key,
            timeout=config.ocr_timeout,
        )

    async def image_analysis(self, payload):
        return await post_json(
            self._url(config.ai_image_path), payload,
            api_key=config.ai_engine_api_key,
            timeout=config.ai_engine_timeout,
        )

    async def deepfake(self, payload):
        return await post_json(
            self._url(config.ai_deepfake_path), payload,
            api_key=config.ai_engine_api_key,
            timeout=config.ai_engine_timeout,
        )

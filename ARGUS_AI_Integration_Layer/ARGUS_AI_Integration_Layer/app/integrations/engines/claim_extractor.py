from .base import BaseEngine


class ClaimExtractorEngine(BaseEngine):
    """Engine 3 - claim / stance / NER extraction.

    Pulls check-worthy claims from free text; optionally scores stance against a
    supplied source and returns named entities. Expected response shape:
        {"claims": [{"text": "...", "check_worthy": 0.88, "entities": [...]}],
         "stance": "REFUTES", "stance_score": 0.79,
         "model": {"name": "...", "version": "..."}}
    """

    name = "claim_extractor"
    env_prefix = "CLAIM_EXTRACTOR"
    default_path = "/v1/extract"
    default_timeout = 60

    async def extract(self, text, source_text=None):
        return await self.infer({"text": text, "source_text": source_text})

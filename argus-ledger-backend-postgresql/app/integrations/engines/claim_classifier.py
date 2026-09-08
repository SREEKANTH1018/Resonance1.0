from .base import BaseEngine


class ClaimClassifierEngine(BaseEngine):
    """Engine 1 - fake-news / claim classifier.

    Text in, label + score out. Expected response shape:
        {"label": "FALSE", "score": 0.93,
         "labels": {"FALSE": 0.93, "MISLEADING": 0.05, "TRUE": 0.02},
         "model": {"name": "...", "version": "..."}}
    """

    name = "claim_classifier"
    env_prefix = "CLAIM_CLASSIFIER"
    default_path = "/v1/classify"
    default_timeout = 60

    async def classify(self, text, context=None):
        return await self.infer({"text": text, "context": context or {}})

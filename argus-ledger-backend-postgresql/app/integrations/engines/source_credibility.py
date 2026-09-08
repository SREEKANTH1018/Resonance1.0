from .base import BaseEngine


class SourceCredibilityEngine(BaseEngine):
    """Engine 4 - source credibility / bot detection.

    Scores a domain or a social account for reliability and automated behaviour.
    Expected response shape:
        {"credibility_score": 0.31, "bot_likelihood": 0.74,
         "labels": ["low_transparency", "coordinated_activity"],
         "model": {"name": "...", "version": "..."}}
    """

    name = "source_credibility"
    env_prefix = "SOURCE_CREDIBILITY"
    default_path = "/v1/score"
    default_timeout = 45

    async def score(self, *, domain=None, account=None, signals=None):
        if not domain and not account:
            return {"enabled": False, "engine": self.name,
                    "error": "provide domain or account"}
        return await self.infer({
            "domain": domain,
            "account": account,
            "signals": signals or {},
        })

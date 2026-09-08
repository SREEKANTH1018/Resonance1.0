import asyncio

from ..http_client import post_json, IntegrationHTTPError
from .settings import settings_for
from .local_loader import call_local, LocalEngineError


class BaseEngine:
    """Common HTTP-or-local dispatch for one trained engine.

    Subclasses set `name`, `env_prefix`, `default_path`, `default_timeout` and
    add typed convenience methods that build a payload and call `self.infer()`.
    """

    name = ""
    env_prefix = ""
    default_path = "/v1/infer"
    default_timeout = 60

    def __init__(self):
        self._lock = None   # created lazily so it binds to the running loop

    def _local_lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def settings(self):
        return settings_for(
            self.name, self.env_prefix, self.default_path, self.default_timeout
        )

    def status(self):
        s = self.settings()
        return {
            "engine": self.name,
            "mode": s.mode,
            "enabled": s.enabled,
            "endpoint": (s.url + s.path) if s.mode == "http" else None,
            "local_target": s.local_target if s.mode == "local" else None,
            "needs": s.missing_vars(),   # exact env var names still missing
        }

    async def infer(self, payload):
        s = self.settings()

        if s.mode == "disabled":
            return {
                "enabled": False,
                "engine": self.name,
                "reason": f"{self.name} is not configured",
                "needs": s.missing_vars(),
            }

        try:
            if s.mode == "http":
                if not s.url:
                    return self._error(s, f"ARGUS_{s.prefix}_URL is not set")
                raw = await post_json(
                    s.url + s.path, payload, api_key=s.api_key, timeout=s.timeout
                )
            else:  # local
                if not s.local_target:
                    return self._error(s, f"ARGUS_{s.prefix}_LOCAL is not set")
                raw = await call_local(s.local_target, payload, self._local_lock())
        except (IntegrationHTTPError, LocalEngineError) as exc:
            return self._error(s, str(exc))

        if not isinstance(raw, dict):
            return self._error(s, "engine returned a non-object result")

        raw.setdefault("enabled", True)
        raw.setdefault("engine", self.name)
        raw.setdefault("mode", s.mode)
        return raw

    def _error(self, s, message):
        return {"enabled": False, "engine": self.name, "mode": s.mode, "error": message}

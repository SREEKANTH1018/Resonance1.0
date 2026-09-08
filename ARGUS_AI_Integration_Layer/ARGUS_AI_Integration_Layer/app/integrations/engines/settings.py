import os
from dataclasses import dataclass

# Per-engine configuration.
#
# Read from the environment at CALL TIME, never at import time. The existing
# app/integrations/config.py reads os.getenv into dataclass defaults, which are
# frozen the moment the module imports; that only works because scripts call
# load_dotenv() first. Engines avoid that trap: settings_for() is a plain dict
# lookup run inside infer(), so `engine_status()` stays honest after the env
# changes and import ordering can never silently disable an engine.
#
# Env var names: ARGUS_<PREFIX>_<FIELD>, e.g. ARGUS_CLAIM_CLASSIFIER_URL.


@dataclass(frozen=True)
class EngineSettings:
    name: str
    prefix: str
    mode: str          # "http" | "local" | "disabled"
    url: str
    api_key: str
    path: str
    local_target: str
    timeout: int

    @property
    def enabled(self):
        return self.mode in ("http", "local")

    def missing_vars(self):
        # What still needs to be set for this engine to run, in words.
        base = f"ARGUS_{self.prefix}"
        if self.mode == "disabled":
            return [f"{base}_URL (http mode) or {base}_LOCAL (local mode)"]
        if self.mode == "http" and not self.url:
            return [f"{base}_URL"]
        if self.mode == "local" and not self.local_target:
            return [f"{base}_LOCAL"]
        return []


def _env(prefix, field, default=""):
    return os.getenv(f"ARGUS_{prefix}_{field}", default)


def settings_for(name, prefix, default_path, default_timeout=60):
    url = _env(prefix, "URL").rstrip("/")
    local_target = _env(prefix, "LOCAL").strip()

    # Explicit MODE wins; otherwise infer it so "fill in a URL and it works".
    mode = _env(prefix, "MODE").strip().lower()
    if mode not in ("http", "local", "disabled"):
        if url:
            mode = "http"
        elif local_target:
            mode = "local"
        else:
            mode = "disabled"

    try:
        timeout = int(_env(prefix, "TIMEOUT_SECONDS", str(default_timeout)))
    except ValueError:
        timeout = default_timeout

    return EngineSettings(
        name=name,
        prefix=prefix,
        mode=mode,
        url=url,
        api_key=_env(prefix, "API_KEY"),
        path=_env(prefix, "PATH", default_path),
        local_target=local_target,
        timeout=timeout,
    )

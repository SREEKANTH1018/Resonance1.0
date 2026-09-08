"""Pluggable slots for the teammate's separately trained engines.

Point your teammate at this one folder. Each engine runs in "http" mode (their
service, its own URL + API key) or "local" mode (their .py + weights imported
in-process) with no code change - only env vars. See docs/ENGINES_CONTRACT.md.

Keep this package import-light: no torch / transformers at module scope, so a
broken local engine can never take down backend startup.
"""

from .base import BaseEngine
from .settings import EngineSettings, settings_for
from .claim_classifier import ClaimClassifierEngine
from .av_deepfake import AudioVideoDeepfakeEngine
from .claim_extractor import ClaimExtractorEngine
from .source_credibility import SourceCredibilityEngine

_ENGINE_CLASSES = {
    ClaimClassifierEngine.name: ClaimClassifierEngine,
    AudioVideoDeepfakeEngine.name: AudioVideoDeepfakeEngine,
    ClaimExtractorEngine.name: ClaimExtractorEngine,
    SourceCredibilityEngine.name: SourceCredibilityEngine,
}

_INSTANCES = {}


def engine_names():
    return list(_ENGINE_CLASSES)


def get_engine(name):
    """Return the shared instance for `name` (raises KeyError if unknown)."""
    if name not in _ENGINE_CLASSES:
        raise KeyError(
            f"Unknown engine '{name}'. Known: {', '.join(_ENGINE_CLASSES)}"
        )
    if name not in _INSTANCES:
        _INSTANCES[name] = _ENGINE_CLASSES[name]()
    return _INSTANCES[name]


def engine_status():
    """{name: {mode, enabled, endpoint, needs, ...}} for a health endpoint."""
    return {name: get_engine(name).status() for name in _ENGINE_CLASSES}


__all__ = [
    "BaseEngine",
    "EngineSettings",
    "settings_for",
    "ClaimClassifierEngine",
    "AudioVideoDeepfakeEngine",
    "ClaimExtractorEngine",
    "SourceCredibilityEngine",
    "engine_names",
    "get_engine",
    "engine_status",
]

import os

from .base import BaseEngine

# Audio/video clips are large. They are passed BY REFERENCE (a local path the
# engine can read, or a URL it can fetch) - never base64-inlined into JSON the
# way the legacy image path does, which would hold ~1.3x the file size in memory
# on both sides. Cap is enforced here for the local-path case.


def _max_media_mb():
    # Read at call time, never at import - see engines/settings.py for why.
    try:
        return int(os.getenv("ARGUS_AV_DEEPFAKE_MAX_MB", "50"))
    except ValueError:
        return 50


class AudioVideoDeepfakeEngine(BaseEngine):
    """Engine 2 - audio (voice-clone) and video manipulation detection.

    Expected response shape:
        {"deepfake_score": 0.82, "classification": "LIKELY_MANIPULATED",
         "modality": "video", "frames_flagged": [...],
         "model": {"name": "...", "version": "..."}}
    """

    name = "av_deepfake"
    env_prefix = "AV_DEEPFAKE"
    default_path = "/v1/av-deepfake"
    default_timeout = 120

    async def scan(self, *, media_url=None, media_path=None, media_kind="video"):
        if not media_url and not media_path:
            return {"enabled": False, "engine": self.name,
                    "error": "provide media_url or media_path"}

        if media_path:
            if not os.path.isfile(media_path):
                return {"enabled": False, "engine": self.name,
                        "error": f"media_path not found: {media_path}"}
            size_mb = os.path.getsize(media_path) / (1024 * 1024)
            cap = _max_media_mb()
            if size_mb > cap:
                return {"enabled": False, "engine": self.name,
                        "error": (f"media is {size_mb:.1f} MB, over the "
                                  f"{cap} MB cap (raise ARGUS_AV_DEEPFAKE_MAX_MB)")}

        return await self.infer({
            "media_kind": media_kind,   # "video" | "audio"
            "media_url": media_url,
            "media_path": media_path,
        })

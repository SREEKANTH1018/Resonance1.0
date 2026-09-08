"""Ping every engine and print its mode + result (or the reason it is off).

Usage:
    python scripts/test_engines.py

Run it after editing .env, and after your teammate gives you a URL or a local
module path. Disabled engines are reported, not treated as errors.
"""
import asyncio
import os
import sys

# Run as `python scripts/test_engines.py` from the repo root: put the repo root
# (not scripts/) on the path so `import app.integrations...` resolves.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # rely on the ambient environment if python-dotenv isn't installed

SAMPLES = {
    "claim_classifier": {"text": "The city banned all cars starting next Monday."},
    "av_deepfake": {"media_kind": "video", "media_url": "https://example.com/clip.mp4"},
    "claim_extractor": {"text": "Officials said the bridge reopened Monday after repairs."},
    "source_credibility": {"domain": "example.com"},
}


async def main():
    from app.integrations.engines import engine_names, engine_status, get_engine

    statuses = engine_status()
    for name in engine_names():
        s = statuses[name]
        print(f"\n== {name} ==  mode={s['mode']}  enabled={s['enabled']}")
        if s["needs"]:
            print("   needs:", "; ".join(s["needs"]))
        if not s["enabled"]:
            continue
        result = await get_engine(name).infer(SAMPLES[name])
        print("   result:", result)


if __name__ == "__main__":
    asyncio.run(main())

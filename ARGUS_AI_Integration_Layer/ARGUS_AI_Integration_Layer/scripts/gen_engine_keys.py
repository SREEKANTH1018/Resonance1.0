"""Print fresh per-engine API keys for the backend .env.

Usage:
    python scripts/gen_engine_keys.py

Keep the output out of git. Give teammates the engine URL, never the key.
"""
import secrets

PREFIXES = {
    "claim_classifier": "ccl",
    "av_deepfake": "avd",
    "claim_extractor": "cex",
    "source_credibility": "scr",
}


def main():
    print("# Generated engine API keys - paste into backend .env, do not commit\n")
    for name, short in PREFIXES.items():
        env_var = f"ARGUS_{name.upper()}_API_KEY"
        print(f"{env_var}=argus_{short}_{secrets.token_urlsafe(24)}")


if __name__ == "__main__":
    main()

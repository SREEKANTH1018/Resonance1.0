# ARGUS AI Integration Layer

Drop-in adapters for connecting independently trained teammate models to the ARGUS backend.

## Architecture

POST /verification/*
 -> verification orchestrator
 -> retrieval (Tavily)
 -> teammate AI HTTP service
 -> OCR / image / deepfake adapters
 -> structured result
 -> existing decision + audit layer

Prefer HTTP integration over copying model-training code into the backend.

## Setup

Copy the variables from `.env.integration.example` into your backend `.env`.

Install:

```powershell
pip install -r requirements-integration.txt
```

The teammate service should expose the endpoints documented in
`docs/AI_INTEGRATION_CONTRACT.md`.

No real API keys are included.

## Pluggable engines

The four separately trained engines live in `app/integrations/engines/` - one
folder to hand your teammate. Each is `http` (their URL + own API key) or
`local` (their `.py` + weights, imported in-process), switched by env vars only:

| engine name          | env prefix           | purpose                              |
|----------------------|----------------------|--------------------------------------|
| `claim_classifier`   | `CLAIM_CLASSIFIER`   | fake-news / claim classifier         |
| `av_deepfake`        | `AV_DEEPFAKE`        | audio + video deepfake detection     |
| `claim_extractor`    | `CLAIM_EXTRACTOR`    | claim / stance / NER extraction      |
| `source_credibility` | `SOURCE_CREDIBILITY` | source credibility / bot detection   |

- Config vars: `.env.integration.example`
- Contract + local-module interface: `docs/ENGINES_CONTRACT.md`
- Per-engine API keys: `python scripts/gen_engine_keys.py`
- Smoke test: `python scripts/test_engines.py`
- Optional HTTP passthrough: `app/integrations/engines_router.py`
  (`GET /engines/status`, `POST /engines/{name}/infer`)

Use from code:

```python
from app.integrations.engines import get_engine
result = await get_engine("claim_classifier").classify("some claim")
```

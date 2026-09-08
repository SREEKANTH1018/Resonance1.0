# ARGUS - Member 3 AI/ML Engine

This package is the complete Member 3 implementation scaffold for ARGUS:
domain-aware model routing, RAG, evidence mapping, validation, risk analysis,
resource/sustainability analysis, agents, and the Decision Passport contract.

## Minimum domains
- healthcare
- finance
- sustainability

The core pipeline is domain-agnostic. New domains can be registered without
rewriting the pipeline.

## Run locally

1. Create/activate a virtual environment.
2. Install:
   `pip install -r ai_engine/requirements.txt`
3. From this folder run:
   `uvicorn ai_engine.main:app --reload --port 8000`
4. Open:
   `http://127.0.0.1:8000/docs`

The default model adapter is deterministic/local so the API can be tested
without an API key. External model providers can be plugged in later.

## Integration contract

Backend sends:
POST /api/v1/decisions

```json
{
  "query": "Evaluate this sustainability decision.",
  "domain": "auto",
  "documents": [
    {"id": "doc-1", "title": "Example policy", "text": "Annual review is required."}
  ],
  "context": {}
}
```

ARGUS returns a Decision Passport containing:
decision, domain, model, answer, evidence, validation, risk, resources,
sustainability, human_review, audit, and replay metadata.

## Important engineering rule

Member 1 and Member 2 should integrate against the schemas in
`ai_engine/schemas.py` rather than importing internal AI modules.

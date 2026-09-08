# Provider/API key plan

## 1. Teammate model service
Required for your separately trained models:

```text
ARGUS_AI_ENGINE_URL=
ARGUS_AI_ENGINE_API_KEY=
```

Use one shared secret for the private HTTP service.

## 1b. Teammate engines (one key per engine)
The four pluggable engines in `app/integrations/engines/` each carry their own
key so one can be rotated or revoked without touching the others:

```text
ARGUS_CLAIM_CLASSIFIER_API_KEY=
ARGUS_AV_DEEPFAKE_API_KEY=
ARGUS_CLAIM_EXTRACTOR_API_KEY=
ARGUS_SOURCE_CREDIBILITY_API_KEY=
```

Generate them with `python scripts/gen_engine_keys.py`. The same value goes in
your backend `.env` and in the teammate's service that serves that engine; it is
sent as `Authorization: Bearer <key>`. Only needed for `http` mode. See
`docs/ENGINES_CONTRACT.md`.

## 2. Tavily
Recommended for web retrieval:

```text
TAVILY_API_KEY=
```

## 3. Google Cloud Vision
Optional if your teammate's OCR is not used:

```text
GOOGLE_APPLICATION_CREDENTIALS=
```

Do not commit the credential file.

## 4. Optional LLM
Keep disabled initially if your teammate's verifier handles reasoning:

```text
LLM_PROVIDER=disabled
LLM_API_KEY=
LLM_MODEL=
```

Never place real API keys in Python source code or Git.

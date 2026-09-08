# ARGUS Engine Contract (teammate-trained models)

Four engines plug into `app/integrations/engines/`. Each runs in one of two
modes, chosen per engine by environment variables only - no code change:

| mode       | how it runs                                   | you set                        |
|------------|-----------------------------------------------|--------------------------------|
| `http`     | teammate's service, called over HTTP + Bearer | `ARGUS_<X>_URL`, `ARGUS_<X>_API_KEY` |
| `local`    | teammate's `.py` + weights, imported in-proc  | `ARGUS_<X>_LOCAL`              |
| `disabled` | engine returns `{"enabled": false, ...}`      | (nothing)                      |

`MODE` is auto-picked when blank: URL set -> `http`, LOCAL set -> `local`,
neither -> `disabled`. Set `ARGUS_<X>_MODE` explicitly to force one.

Prefer `http`. Only use `local` if the model is small and dependency-light;
heavy models (torch, transformers) belong behind HTTP so they can't break
backend startup or block the event loop.

## Engines and env prefixes

| engine name          | `<X>` prefix          | default path        | default timeout |
|----------------------|-----------------------|---------------------|-----------------|
| `claim_classifier`   | `CLAIM_CLASSIFIER`    | `/v1/classify`      | 60s             |
| `av_deepfake`        | `AV_DEEPFAKE`         | `/v1/av-deepfake`   | 120s            |
| `claim_extractor`    | `CLAIM_EXTRACTOR`     | `/v1/extract`       | 60s             |
| `source_credibility` | `SOURCE_CREDIBILITY`  | `/v1/score`         | 45s             |

Full env var list: `.env.integration.example`. API keys:
`python scripts/gen_engine_keys.py` (one key per engine, keep out of git).

---

## HTTP mode

Backend sends `POST <URL><PATH>` with JSON body and, if a key is set:

```text
Authorization: Bearer <ARGUS_<X>_API_KEY>
```

Return JSON (an object). `enabled`, `engine`, `mode` are added by the backend if
absent. Any non-2xx or non-JSON response becomes
`{"enabled": false, "error": "..."}` - it never raises.

### 1. `claim_classifier` - POST /v1/classify

Request:
```json
{ "text": "claim text", "context": {} }
```
Response:
```json
{
  "label": "FALSE",
  "score": 0.93,
  "labels": { "FALSE": 0.93, "MISLEADING": 0.05, "TRUE": 0.02 },
  "model": { "name": "argus-claim-clf", "version": "1.0" }
}
```

### 2. `av_deepfake` - POST /v1/av-deepfake

Media is passed **by reference**, never base64 in the body.

Request:
```json
{
  "media_kind": "video",
  "media_url": "https://.../clip.mp4",
  "media_path": null
}
```
`media_path` is a path on the machine running the engine (useful in `local`
mode). One of `media_url` / `media_path` is always present. Files over
`ARGUS_AV_DEEPFAKE_MAX_MB` (default 50) are rejected before the call.

Response:
```json
{
  "deepfake_score": 0.82,
  "classification": "LIKELY_MANIPULATED",
  "modality": "video",
  "model": { "name": "argus-av-deepfake", "version": "1.0" }
}
```

### 3. `claim_extractor` - POST /v1/extract

Request:
```json
{ "text": "paragraph to mine", "source_text": "optional source to score stance against" }
```
Response:
```json
{
  "claims": [
    { "text": "...", "check_worthy": 0.88, "entities": [ { "text": "WHO", "type": "ORG" } ] }
  ],
  "stance": "REFUTES",
  "stance_score": 0.79,
  "model": { "name": "argus-claim-extractor", "version": "1.0" }
}
```

### 4. `source_credibility` - POST /v1/score

Request:
```json
{ "domain": "example.com", "account": null, "signals": {} }
```
Response:
```json
{
  "credibility_score": 0.31,
  "bot_likelihood": 0.74,
  "labels": ["low_transparency", "coordinated_activity"],
  "model": { "name": "argus-source-cred", "version": "1.0" }
}
```

---

## Local mode

`ARGUS_<X>_LOCAL` points at a callable:

```text
mypkg.claim_clf:predict          # dotted import path
D:\models\claim_clf.py:predict   # file path + attribute (Windows ok)
/opt/models/clf.py               # file path, attribute defaults to `predict`
```

The module must expose:

```python
def warmup() -> None:      # optional; called once, in a worker thread, before first predict
    ...

def predict(payload: dict) -> dict:   # sync or async; payload is the same JSON body as HTTP mode
    ...
```

Rules the loader enforces so real models work:

- The module is imported once and cached; `warmup()` runs once. Load weights in
  `warmup()` (or at module import), not inside `predict()`.
- For a file path, the file's directory is added to `sys.path` and the module is
  registered in `sys.modules` before execution, so `from .utils import x` and
  unpickling custom classes work.
- `predict()` runs in a worker thread (via `asyncio.to_thread`) so it can't
  block the event loop, and calls are serialised per engine with a lock -
  don't rely on concurrent `predict()` calls.
- Keep imports lazy/inside `warmup()`; a module that imports torch at top level
  will slow every backend start.

---

## Using an engine from code

```python
from app.integrations.engines import get_engine

clf = await get_engine("claim_classifier").classify("some claim")
if clf.get("enabled"):
    ...
```

Or the generic form: `await get_engine(name).infer(payload_dict)`.

## HTTP passthrough (for testing / other services)

`app/integrations/engines_router.py` exposes:

- `GET /engines/status` - mode + `needs` (missing env var names) per engine
- `POST /engines/{name}/infer` - body is the raw payload, forwarded to the engine

Wire it in like the existing router:

```python
from app.integrations.engines_router import router as engines_router
app.include_router(engines_router)
```

Smoke test everything: `python scripts/test_engines.py`

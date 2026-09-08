# ARGUS <-> Teammate AI Contract

Do not import training code directly. Expose the trained models through HTTP.

Environment:

```text
ARGUS_AI_ENGINE_URL=http://TEAMMATE_HOST:9000
ARGUS_AI_ENGINE_API_KEY=shared-secret
```

## POST /v1/decision

Request:

```json
{
  "text": "claim text",
  "sources": [
    {
      "url": "https://example.com",
      "content": "evidence text",
      "retrieval_score": 0.88
    }
  ],
  "iteration": 1
}
```

Response:

```json
{
  "status": "SUPPORTED",
  "confidence": 0.87,
  "claims": [
    {
      "text": "claim text",
      "status": "SUPPORTED",
      "confidence": 0.91
    }
  ],
  "next_query": null,
  "model": {"name": "ARGUS-Verifier", "version": "1.0"}
}
```

## POST /v1/ocr

```json
{
  "filename": "image.png",
  "image_base64": "..."
}
```

Response:

```json
{
  "text": "text extracted from image",
  "confidence": 0.94,
  "model": {"name": "ARGUS-OCR", "version": "1.0"}
}
```

## POST /v1/image-analysis

Response:

```json
{
  "image_class": "photograph",
  "confidence": 0.92,
  "model": {"name": "ARGUS-Vision", "version": "1.0"}
}
```

## POST /v1/deepfake

Response:

```json
{
  "deepfake_score": 0.08,
  "classification": "LIKELY_AUTHENTIC",
  "model": {"name": "ARGUS-Deepfake", "version": "1.0"}
}
```

The backend sends the shared secret as:

```text
Authorization: Bearer <ARGUS_AI_ENGINE_API_KEY>
```

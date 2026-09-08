# Backend ↔ Frontend Integration Contract

## Network

Development:

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8000
```

Frontend configuration:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Backend configuration must allow the frontend origin through `CORS_ORIGINS`.

## API map

| UI feature | Backend |
|---|---|
| Connection indicator | GET `/health` |
| Dashboard metrics | GET `/dashboard` |
| Decision list | GET `/decisions` |
| Decision details | GET `/decisions/{id}` |
| Evidence tab | GET `/decisions/{id}/evidence` |
| Audit tab | GET `/decisions/{id}/audit` |
| Generate | POST `/decisions/generate` |
| Persist | POST `/decisions` |
| Human review | POST `/decisions/{id}/review` |
| Verification text | POST `/verification/text`* |
| Verification URL | POST `/verification/url`* |
| Verification image | POST `/verification/image`* |

`*` These routes belong to the optional verification integration layer and must exist in the backend before those controls are used.

## Why the API layer is isolated

All fetch logic lives in `src/api.js`.

That means the UI does not know about:

- PostgreSQL
- SQLAlchemy
- provider API keys
- model weights
- Tavily credentials
- Google credentials
- Docker networking

Only FastAPI knows those things.

## AI engine hand-off

Recommended server-side contract:

```text
POST /v1/decision
Authorization: Bearer <server-side ARGUS_AI_ENGINE_API_KEY>
Content-Type: application/json
```

The React frontend should never call the teammate's AI laptop directly.

The frontend calls:

```text
POST /decisions/generate
```

and FastAPI calls the AI engine.

This lets the backend persist the AI output and audit event in one controlled path.

## If the AI engineer changes the model

Keep the API contract stable:

```json
{
  "model": "model-name",
  "version": "1.2.0",
  "decision": "example",
  "confidence": 0.91
}
```

The frontend can then keep working even when the underlying `.pt`/`.pth` model changes.

## Error handling

The frontend shows FastAPI's `detail`, `message`, or `error` response in the UI.

For a FastAPI validation response such as:

```json
{
  "detail": [
    {
      "loc": ["body", "field"],
      "msg": "Field required"
    }
  ]
}
```

the UI prints the returned validation object instead of hiding it.

This is deliberate: during integration, your team can immediately see which field does not match the backend contract.

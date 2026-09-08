# ARGUS Team Handoff

## Member: Frontend

Own:

```text
frontend/
└── src/
    ├── api.js
    ├── App.jsx
    ├── main.jsx
    └── styles.css
```

## Member: Backend / PostgreSQL

Own:

```text
backend/
├── app/
├── database/
└── .env
```

## Member: AI Engine

Own:

```text
ai-engine/
├── model/
├── weights/
└── API service
```

The AI engine should expose a stable HTTP API to the backend.

## Shared flow

```text
                   ┌──────────────────────┐
                   │       FRONTEND       │
                   │ React + Vite         │
                   └──────────┬───────────┘
                              │
                         HTTP / JSON
                              │
                              ▼
                   ┌──────────────────────┐
                   │       FASTAPI        │
                   │ validation + logic  │
                   └──────┬─────────┬─────┘
                          │         │
                          │         ▼
                          │   ┌──────────────┐
                          │   │ AI ENGINE    │
                          │   │ teammate API │
                          │   └──────────────┘
                          │
                          ▼
                   ┌──────────────────────┐
                   │     POSTGRESQL       │
                   │ decisions            │
                   │ evidence             │
                   │ audit_events         │
                   │ resource_usage       │
                   └──────────────────────┘
```

## Secrets

Never commit:

- PostgreSQL passwords
- AI engine API keys
- Tavily keys
- Google service-account credentials
- LLM provider keys

The frontend must never contain them.

## Final repository recommendation

```text
D:\argus-ledger\
├── backend\
├── frontend\
└── ai-engine\
```

Each team can work independently while the API contracts remain stable.

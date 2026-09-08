# ARGUS Ledger Frontend

A React + Vite frontend designed around the existing ARGUS Ledger FastAPI backend.

## Backend contract used

The frontend calls:

- `GET /health`
- `POST /decisions`
- `POST /decisions/generate`
- `GET /decisions`
- `GET /decisions/{id}`
- `GET /decisions/{id}/audit`
- `GET /decisions/{id}/evidence`
- `GET /dashboard`
- `POST /decisions/{id}/review`

It also has optional adapters for the verification integration layer:

- `POST /verification/text`
- `POST /verification/url`
- `POST /verification/image`

The verification UI is intentionally optional: if those backend routes are not installed yet, the rest of the dashboard still works.

## Project structure

```text
ARGUS_Ledger_Frontend/
├── src/
│   ├── api.js                 # One HTTP boundary for FastAPI
│   ├── App.jsx                # Pages, dashboard, decisions, verification
│   ├── main.jsx
│   └── styles.css
├── .env.example
├── .gitignore
├── index.html
├── package.json
└── README.md
```

## Put it beside the backend

Recommended final structure:

```text
D:\
└── argus-ledger\
    ├── backend\
    │   ├── app\
    │   ├── database\
    │   ├── scripts\
    │   └── ...
    └── frontend\
        ├── src\
        ├── package.json
        └── ...
```

If you want to keep the existing backend directory unchanged, simply use:

```text
D:\argus-ledger-backend-postgresql\
D:\argus-ledger-frontend\
```

## Run on Windows / PowerShell

```powershell
cd "D:\argus-ledger-frontend"
Copy-Item ".env.example" ".env"
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally:

```text
http://localhost:5173
```

Your backend should be running on:

```text
http://localhost:8000
```

The backend `.env` already allows `http://localhost:5173` through CORS in the supplied project configuration.

## Important AI-engine architecture

Do NOT put your teammate's AI provider keys in this frontend.

Correct flow:

```text
Browser / React
      |
      | HTTP/JSON
      v
FastAPI :8000
      |
      +--> app/ai_service.py / integration adapters
      |          |
      |          +--> teammate AI engine
      |          +--> Tavily / OCR / other providers
      |
      +--> PostgreSQL
             |
             +--> decisions
             +--> evidence
             +--> audit_events
             +--> resource_usage
```

The frontend only needs the FastAPI URL. AI credentials belong in the backend `.env` or server-side secret store.

## Payload note

The backend source package supplied with this frontend exposes the routes but the exact Pydantic request shapes are maintained in the backend's API contract. To keep this UI safe against future schema changes, the New Decision page exposes an editable JSON payload and displays FastAPI validation errors directly.

Once your team freezes the exact schema, the JSON editor can be replaced with strict typed form fields without changing `src/api.js`.

## Integrating your teammate's trained model

Prefer this:

```text
AI teammate laptop
    |
    | POST /v1/decision
    | Authorization: Bearer <server-side key>
    v
AI engine service

ARGUS FastAPI
    |
    +--> AI engine HTTP adapter
    +--> verification pipeline
    +--> PostgreSQL audit ledger
```

Do not copy `.pt`, `.pth`, `.h5`, etc. into the React app.

When the AI engineer changes model/version, the backend adapter can continue exposing the same contract to the frontend.

## Production

For production, set:

```env
VITE_API_BASE_URL=https://your-argus-api.example.com
```

Never place `TAVILY_API_KEY`, Google credentials, model-provider keys, database passwords, or your teammate's AI-engine secret in any `VITE_*` variable. Vite variables are shipped to the browser.

## CORS

The backend supplied with this project already includes:

```text
http://localhost:3000
http://localhost:5173
```

in its CORS configuration. If you change the frontend host/port, update the backend `CORS_ORIGINS`.

## One-project end state

```text
D:\argus-ledger\
├── backend\
│   ├── app\
│   │   ├── main.py
│   │   ├── ai_service.py
│   │   └── integrations\
│   ├── database\
│   ├── scripts\
│   ├── .env
│   └── Dockerfile
│
├── frontend\
│   ├── src\
│   ├── .env
│   └── package.json
│
└── ai-engine\
    ├── model code
    ├── model weights
    └── API service
```

The browser talks only to the backend. This keeps the frontend stable while the AI engineer trains and replaces models.

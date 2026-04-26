# Invest-Ed Parent Frontend

React + Vite SPA for parent-facing flows (consent, magic-link login, dashboard).

## Dev

```bash
cd invest-ed/backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 &
cd invest-ed/frontend && npm install && npm run dev
```

Open http://localhost:5173.

## Test

- `npm test` — Vitest unit + component
- `npm run test:e2e` — Playwright (requires backend on :8000)

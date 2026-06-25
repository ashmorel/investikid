# InvestiKid — frontend

The React 18 + Vite + TypeScript web app (also wrapped as the iOS/Android apps
via Capacitor). See the [root README](../README.md) for the project overview and
[CONTRIBUTING](../CONTRIBUTING.md) for the full workflow.

## Develop (Node 20)

```bash
npm ci
npm run dev          # http://127.0.0.1:5173
```

## Checks

```bash
npm run build        # tsc -b && vite build
npm test             # vitest
npm run lint         # eslint
npm run test:e2e     # playwright
```

## Native (Capacitor)

After a web build, sync the native projects (under `ios/` and `android/`):

```bash
npm run build && npx cap sync ios       # open in Xcode
npm run build && npx cap sync android   # open in Android Studio
```

The native bundle bakes the API base from `frontend/.env.local`
(`VITE_API_BASE_URL=https://api.investikid.ai`). See
[`docs/deployment-environments.md`](../docs/deployment-environments.md).

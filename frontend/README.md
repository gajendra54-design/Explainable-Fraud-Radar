# Fraud Radar frontend

React 18 + TypeScript + Vite, Tailwind 4, TanStack Query, Recharts, React Hook Form and Zod. Exact package versions are locked in package-lock.json. Every displayed metric comes from the authenticated backend API.

## Develop

Run `npm ci`, then `npm run dev` from this directory. The application serves port 5177 and proxies `/api` to `http://127.0.0.1:8017`. Set `API_PROXY_TARGET` to override the backend address. The API must be configured, migrated and seeded following the root README. Sign in with the bootstrap credentials generated during configuration.

`npm run build` performs strict TypeScript checking and creates `dist/`. `npm run typecheck` checks source types. `npm audit` checks the locked dependency graph. The Docker image uses an unprivileged nginx runtime on port 8080, proxying the Compose backend at port 8000.

## Browser workflow

Set `RADAR_E2E_USER`, `RADAR_E2E_PASSWORD`, and optionally `RADAR_E2E_URL` (defaults to http://127.0.0.1:5177). With Playwright Chromium installed (`npx playwright install chromium`), run `npm run test:e2e`. To use an existing Google Chrome installation, set `PLAYWRIGHT_CHANNEL=chrome`.

The test logs in, browses a critical transaction, inspects attribution, assigns a new case to the signed-in administrator/investigator, records a note, resolves it with confirmation, checks audit history and opens model evaluation. It changes synthetic case state; run against a disposable or demonstration dataset with at least one new alert. Genuine screenshots are saved under `reports/screenshots/` at repository root. It also captures the mobile layout.

## Interaction and security

Tokens are kept in sessionStorage and removed on logout. The backend enforces roles and allowed state transitions; frontend disabling is a convenience, not an authorization boundary. Resolved case updates return explicit API errors. Confirmation is required for dispositions and model activation. Pipeline runs are polled every five seconds. Threshold exploration uses held-out predictions and does not change operational alert configuration.

The UI distinguishes probability, anomaly percentile and rule score. Logistic contributions use log-odds with baseline and output displayed. Generated fraud labels and investigator opinions remain separate. Data, model and evaluation failures expose retry states rather than manufactured demo numbers.

## Known limitations

Navigation is in-memory (refresh returns to overview); session expiry returns an API error and requires signing out/in. The chart dependency chunk is approximately 541 KB minified and triggers Vite's advisory chunk-size warning. Fonts use Google Fonts with local sans-serif fallbacks. Production deployments should add a deployment-specific Content Security Policy and consider an HttpOnly-cookie identity integration.

## Hardening checks

API payloads have explicit TypeScript interfaces under `src/types/api.ts`; generic HTTP responses default to `unknown`. Automated axe-core checks exercise login, overview, transaction browsing and the monitoring investigation workflow with WCAG 2 A/AA and 2.1 AA tags. The initial color-contrast findings were corrected. Automated checks are not formal accessibility certification; keyboard-only, screen-reader and human usability review remain advisable.

The monitoring view separates live independent verified outcomes from synthetic held-out benchmarks, shows maturity and label coverage, preserves server-generated drift snapshots and records immutable resolved incident history. Administrator verified-label entry requires a supporting source, evidence and explicit confirmation. Sign-out invokes server token revocation before removing the client token; a failed revocation remains visible and can be retried.

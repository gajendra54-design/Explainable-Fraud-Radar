# Verification guide

Run Python tests from the repository root with `python -m pytest backend/tests -q`. ML tests cover reproducibility, validation/quarantine, exact metrics, chronological feature behavior, same-time boundary handling, persistence, online/offline parity, and deliberately shifted drift. API integration tests cover authentication, role restrictions, transaction scoring, audit history, immutable resolution, assignment/escalation, replay safety, timestamp normalization and missing artifacts.

API tests use an isolated temporary SQLite database unless `TEST_DATABASE_URL` points to a dedicated empty PostgreSQL test database. Never point this variable at a shared application database. Tests apply migrations and insert fixtures. CI supplies a disposable PostgreSQL service.

Quality commands:

```text
python -m ruff check backend ml
python -m ruff format --check backend ml
python -m pytest backend/tests -q --junitxml=reports/pytest.xml
```

In `frontend/`, `npm run build` checks TypeScript and builds production assets. `npm run test:e2e` runs Playwright against the running application. Set `RADAR_E2E_URL`, `RADAR_E2E_USER` and `RADAR_E2E_PASSWORD` for the test environment. Default URL is localhost:5177. Use `npx playwright install chromium` when the bundled browser is absent. Browser workflow tests intentionally mutate synthetic cases and require a seeded dataset with unresolved alerts.

The local credentials belong in environment variables, not test source or logs. CI credentials are explicitly disposable fixture values for the ephemeral CI environment, never shared production credentials.

The hardening suite also verifies lease expiry, stale-owner fencing, retry bounds, concurrent worker claims, session revocation, shared failed-login capacity, append-only database audit evidence, bounded retention, delayed-label maturity, and persisted monitoring investigations. PostgreSQL queue/limiter tests create unique disposable schemas inside the dedicated test database, exercise its advisory-lock branches, and remove only those schemas. Browser tests include axe accessibility scans and prove a token is rejected after sign-out. Automated accessibility checks are not an independent WCAG certification.

Run `npm audit` for JavaScript dependencies and `python -m pip_audit` for installed Python packages. These require registry access and only cover known advisories at the time of execution. Container scanning in CI complements package checks; neither constitutes a penetration test.

Windows restrictions may prevent asyncio socket creation or browser connections in a sandbox. A hung test in that environment is not evidence of a product failure or a passing test; rerun with permitted local networking or in a Linux container and record the outcome.

Actual execution results, caveats and screenshots are listed in `reports/verification.md`. Remote CI configuration has not been presented as an executed GitHub run.

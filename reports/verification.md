# Delivery verification — 23 October 2026

This report distinguishes executed behavior from configuration and production recommendations. All banking records are synthetic. No external bank integration, real money movement or public deployment occurred.

GitHub handoff, 24 October 2026: the project is now published at [gajendra54-design/Explainable-Fraud-Radar](https://github.com/gajendra54-design/Explainable-Fraud-Radar). Live remote verification results are available in [GitHub Actions](https://github.com/gajendra54-design/Explainable-Fraud-Radar/actions/workflows/ci.yml). This report retains the local verification snapshot below; publishing source code does not deploy the running application.

**Remote verification passed:** [workflow run 40069772845](https://github.com/gajendra54-design/Explainable-Fraud-Radar/actions/runs/40069772845) verified application commit `460f25ff218e8f8da6aebe1ac917a2e493564b1c`. All six jobs succeeded: PostgreSQL backend tests (**62 passed**), frontend build, browser workflow (**4 passed**), repository dependency/secret scan and both runtime image scans. Security gates fail on fixable high/critical advisories; the documented unfixed Debian advisories remain excluded from that gate, not resolved. The patched local Docker frontend also passed the new invalid-login test; evidence is `browser-validation-2026-10-24.xml`.

The first remote application build, PostgreSQL tests and browser workflow passed. Remote security scanning found newly reported fixable issues in Zod 3.24.1 and Brotli 1.2.0-r1. The frontend now uses Zod 4.6.6 with a compatible form resolver, and its container installs Brotli 1.2.1-r0 or newer while retaining its non-root runtime. An empty-login regression test covers validation errors after the major Zod upgrade. The unavailable Trivy action reference was replaced with the pinned scanner container; dependency, secret and image scans remain enforced. The 24 October backend rescan still reports eight unique unfixed Debian advisories and no critical findings; see `backend-image-audit-2026-10-24.json`. The 23 October scan reports below are historical snapshots, not assertions about today's advisory database.

## Executed checks

- Local Python 3.12 test suite: **62 passed** in 14.48 seconds. Evidence: `pytest.xml`. Includes durable job recovery/fencing, session revocation, shared login throttling, immutable audit records, retention, delayed labels and validated API responses. One upstream Starlette TestClient deprecation warning remains.
- Ruff lint and formatting: **passed**.
- Frontend TypeScript check and Vite production build: **passed**. A nonfatal bundle-size warning remains for the chart-rich JavaScript bundle.
- Updated Playwright suite: **3 passed** in 31.1 seconds against the development frontend and Docker API. Evidence: `browser-hardening.xml`. Covers the original case/evaluation workflow, saved drift investigations and resolution, and revoked-token rejection after logout.
- Final **Docker/PostgreSQL browser suite: 3 passed in 23.5 seconds**. Evidence: `browser-docker.xml`. Screenshots were refreshed from the containerized application. Axe WCAG 2 A/AA and 2.1 AA tagged checks reported zero violations on login, overview, transaction explorer and monitoring; this is automated testing, not a formal accessibility certification.
- Final visual correction reports performance degradation as **Not assessed** when labels are insufficient. The rebuilt Docker frontend passed the focused monitoring workflow again in 7.4 seconds, including this assertion, accessibility, persistence and logout revocation. Evidence: `browser-monitoring-final.xml`.
- JavaScript package audit: **0 known vulnerabilities**. Evidence: `npm-audit.json`.
- Python installed-package audit: **0 known vulnerabilities** after dependency updates. Evidence: `python-audit.json`.
- SQLite migration and 3,000-record application pipeline: **completed**. Actual stored investigation exported in `application/sample_incident.json` and `.md`.
- Docker images built; **PostgreSQL, FastAPI and frontend are healthy**, with a separate worker running. Local UI binds only to `127.0.0.1:8087`; database and backend have no published host ports.
- Additive migrations through **0006** applied to SQLite and PostgreSQL. The final container suite passed **62 tests in 13.54 seconds** against a dedicated `radar_hardening_test` database. Queue and limiter tests use isolated PostgreSQL schemas and exercise PostgreSQL locking and concurrency. Evidence: `postgres-tests.xml`.
- Real API-to-worker integration completed an existing 3,000-row seed replay in one attempt, deduplicated all 3,000 records and left the transaction count unchanged. Evidence: `worker-runtime.json`. The live monitoring window correctly reported insufficient verified labels.
- Frontend runtime image scan: **0 high/critical findings**; the hardening rebuild retains the same nginx runtime base. Refreshed final backend image scan: **0 Python findings**, but **44 high-severity Debian package findings across eight unique advisories**, none with a fixed version listed by the scanner; there were no critical findings. Evidence: `frontend-image-audit.json` and `backend-image-audit-final.json`. The earlier `backend-image-audit.json` preserves pre-remediation evidence. Pulling the latest compatible Python base returned the same base digest.
- Generated-secret check: **124 source, documentation and report files checked**, no generated database password, signing secret or bootstrap password found. Local `.env` remains Git-ignored.
- Eight-slide portfolio PPTX generated from actual benchmark reports and genuine screenshots, with visual and structural validation. Native PowerPoint opening and cross-application chart editing were not tested.

## Full synthetic benchmark

Executed command:

```text
.venv\Scripts\python.exe -m ml --transactions 100000 --customers 1000 --output reports/generated-100k
```

Generated and processed **100,000 transactions** in **36.77 seconds** on this workstation. Model version: `lr-v1-652d1d411f`. Training/validation/test counts: 60,000 / 20,000 / 20,000. The decision threshold selected on validation was 0.15; the final test set was not used for selection.

The logistic model's untouched synthetic test results were precision **47.07%**, recall **74.65%**, F1 **57.73%**, PR-AUC (average precision) **0.5745**, and ROC-AUC **0.9488**, producing **1,808 alerts**. These are synthetic benchmark results, not estimates of real-bank performance. The 3,000-row interactive demo is a different population and correctly displays different metrics.

Machine-readable evidence in `benchmark-100k/` includes quality, EDA, scenario distributions, feature importance, four-model comparison, thresholds, drift, configuration and pipeline timing. Large raw/curated datasets, features, labels and the model artifact remain in the ignored `generated-100k/` directory and can be regenerated.

## Significant implementation decisions

The operational score is 100 times the logistic model probability. Isolation Forest scores are empirical anomaly percentiles; rule scores are transparent contextual signals. They are not blended into a falsely calibrated probability. Exact linear attribution reconstructs the logistic output in log-odds and does not claim causation.

History features use strictly earlier observations, and equal-timestamp groups do not straddle dataset partitions. Incoming timestamps are normalized to UTC. LKR-only input avoids comparing unconverted currencies. Optional labels remain unknown when absent. Investigator opinions do not overwrite generator labels.

PostgreSQL stores normalized customers, accounts, transactions, model metadata, predictions, cases, notes, audit events, pipeline runs and quarantined records. Several derived fields are stored in JSON to retain their versioned explanation context. Frozen Alembic operations define the initial schema. Backend role checks protect mutations; audit and case changes commit together.

## Remaining limitations and intentionally simplified requirements

- Public application deployment remains pending. The source repository is hosted on GitHub and remote CI has been launched; use the workflow link above for its current result.
- The backend image retains eight unique Debian advisories with no fixed versions listed, represented by 44 affected-package findings. Application package audits are separate from container OS scans. The unused runtime packaging tools were removed after the initial scan. Review the remaining image advisories before external deployment; do not treat a clean Python/npm package audit as a clean operating-system image.
- A local artifact registry is used instead of an MLflow server. Exact logistic attribution replaces SHAP. Statistical monitoring replaces Evidently. These are documented substitutions permitted by the brief.
- Durable jobs and failed-login limits now use the database. Training persistence is serialized by a global lease; this is not a distributed compute engine. Trusted proxy configuration is needed to distinguish public source IPs behind a deployment proxy.
- Synthetic patterns are simplified, including velocity pairs rather than coordinated fraud campaigns. There is no real-world probability-calibration guarantee, external validity study or unseen-customer holdout study.
- Verified labels, maturity-aware performance and persisted drift investigations are implemented. Synthetic generator labels and investigator dispositions are excluded from live verified-outcome metrics. No external bank outcome feed or Grafana deployment is configured.
- Bounded quarantine retention and expired-session cleanup commands are implemented; scheduling and retention policy remain operator choices. Database triggers reject mutation of audit evidence, verified labels and monitoring history, but privileged database owners can disable them. Identity federation, external audit anchoring and independent security review remain deployment work.
- Core API response schemas are validated with Pydantic; variable model metadata remains extensible JSON. Frontend API interfaces no longer use explicit `any` types.
- The frontend uses reusable local components instead of importing shadcn/ui. Automated accessibility tests passed; a formal WCAG audit has not been performed.
- The original text referred to a Sentinel screenshot, but no reference image was attached; the implementation uses a distinctive design rather than an exact reproduction.
- No financial regulatory compliance or production certification is asserted.

## Reproduction

Use the README for setup. Run `python -m scripts.export_reports` after a real case is resolved to refresh the application evidence. Do not substitute synthetic benchmark labels with investigator opinions. Audit reports describe the advisory databases at execution time and do not guarantee absence of undiscovered vulnerabilities.

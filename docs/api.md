# Versioned API

FastAPI serves interactive OpenAPI at `/docs` and the machine-readable contract at `/openapi.json`. All domain endpoints start `/api/v1` and require a Bearer token. Obtain a two-hour token with `POST /auth/login` JSON `{ "username": "...", "password": "..." }`; use the administrator created from environment variables. `/auth/me` returns the authenticated role. There are no hardcoded credentials.

Errors use `{ "error": { "message": "...", "request_id": "..." } }`. Validation errors additionally contain field locations without echoing secret inputs. All responses carry `X-Request-ID`. Failed login attempts use database-backed rolling windows shared across API processes: ten per username/source-IP pair and fifty per source IP over sixty seconds. Success resets the pair window while retaining the IP spraying counter. PostgreSQL advisory locks serialize concurrent attempts; SQLite uses an immediate transaction. Only hashed bucket keys and bounded failure timestamps are persisted.

## Read contracts

- `GET /dashboard`: database-derived counts, daily trend, risk distribution, recent cases, model version and synthetic label prevalence.
- `GET /transactions`: `page` (1-based), `page_size` (1–100), `search`, `risk_band`, `channel`, `min_amount`, `max_amount`, `date_from`, `date_to`, `status`, `sort=timestamp|amount|risk_score`, `order=asc|desc`. Returns `items,total,page,page_size`.
- `GET /transactions/{id}`: raw synthetic fields, prediction, case reference and strictly earlier account transactions.
- `GET /transactions/{id}/risk` and `/explanation`: stored prediction and model-specific attribution.
- `GET /alerts` and `/cases`: paginated case queue, with optional `status,assigned_to`.
- `GET /alerts/{id}`: full case with transaction, prediction, notes and history. `GET /cases/{id}/history`: ordered audit events.
- `GET /evaluation/metrics?threshold=0.5`, `/confusion-matrix`, `/thresholds`: chronological held-out benchmark. Thresholds are fractions **0–1**, scores are **0–100**.
- `GET /models`, `/models/{version}`: saved artifact metadata and evaluation.
- `GET /monitoring/drift`, `/monitoring/performance`: synthetic reference/current monitoring and label provenance.
- `GET /pipeline/runs`, `/system/status`, `/users`: operational state and assignable user identities.

## Mutations

Analysts have read access only. Investigators may score with `POST /score` and edit their assigned cases. Administrators may ingest, train, activate a model, and reassign cases.

- `POST /transactions`: one canonical transaction. `POST /transactions/batch`: `{ "records": [...] }` (maximum 10,000). Invalid batch rows are quarantined; replayed transaction IDs are counted as duplicates. Valid rows are scored with earlier database history.
- `POST /alerts/{id}/assign`: `{ "username": "investigator" }`. Investigators can claim unassigned cases; only administrators can reassign someone else's case.
- `POST /alerts/{id}/status`: `{ "status": "Under Review" }` after assignment.
- `POST /alerts/{id}/notes`: `{ "text": "Investigation observations" }`.
- `POST /alerts/{id}/escalate`: `{ "reason": "Additional review required" }` from Assigned or Under Review.
- `POST /alerts/{id}/disposition`: `{ "disposition": "Inconclusive", "confirmed": true }` from Under Review or Escalated. Other supported dispositions are Confirmed suspicious activity, Legitimate activity / false positive, Requires further review. Resolution is immutable. Investigator opinions never rewrite synthetic ground truth.
- `POST /pipeline/runs`: `{ "transactions":3000,"seed":42,"customers":180,"fraud_rate":0.06 }`; returns HTTP 202 and a run ID. Poll run history. Durable database queue: run `python -m backend.app.worker` with the same database and artifact volume. Workers claim one global training lease, heartbeat it, recover expired leases after restarts and retry failures up to three times.
- `POST /models/{version}/activate`: explicit administrator promotion/rollback, audited. Existing predictions retain their original model/explanation.

Repeated identical assignment, review status, escalation and resolution requests do not duplicate audit events. Notes intentionally represent distinct submissions. State changes and audit events commit in one database transaction; PostgreSQL row locks serialize case edits.

`/health` indicates process liveness. `/ready` verifies migrated database access and an active seeded model; it returns 503 before seed. `/metrics` exports process-local Prometheus request/error counters. Do not use readiness to gate an external seed command on a clean database.

The current model accepts LKR transactions only; currency conversion is deliberately unsupported because training amounts use one currency. Timestamps normalize to UTC with fixed microsecond precision before storage and chronological filtering. Ground-truth labels accept 0, 1 or null; missing labels remain unknown. `/monitoring/drift?window_size=1000` compares training reference data against the latest persisted transaction window (50–10,000 rows), reports actual label coverage and recomputes features using all persisted prior history.


## Revocable sessions

All newly issued tokens have persisted session IDs; pre-migration tokens require a new login. `POST /auth/logout` revokes the current token, `/auth/logout-all` revokes all of the user's sessions, and `/auth/password` accepts `current_password,new_password` (minimum twelve characters), verifies the current password and revokes existing sessions. Administrators can `POST /users/{user_id}/sessions/revoke`. Each action is audited. The client must reauthenticate after revocation. All core endpoint responses now have explicit Pydantic/OpenAPI schemas; extensible model metadata remains typed JSON.

Expired login buckets are pruned in bounded batches on login. Run `python -m backend.app.security.cleanup --limit 1000` periodically to remove at most 1,000 expired sessions and 1,000 expired buckets per invocation. Active sessions and unexpired limiter state are preserved. Source addresses come from ASGI `request.client`; configure trusted reverse-proxy forwarding explicitly before exposing multiple client IPs through a proxy, rather than trusting arbitrary forwarded headers.

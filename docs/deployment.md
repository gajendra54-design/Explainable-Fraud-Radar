# Deployment runbook

The default deployment is local Docker Compose. No public deployment is implied by this repository.

## Production topology

Use a managed PostgreSQL service on a private subnet, a container service for FastAPI, and a frontend reverse proxy behind an HTTPS load balancer. Store immutable model versions on persistent object/block storage with access restricted to the application service account. A newly created web container must not silently replace an approved model.

1. Build and scan versioned backend/frontend images in CI; record digests.
2. Provision PostgreSQL and configure its connection URL through a secret manager.
3. Supply a strong bootstrap password and restrict allowed browser origins.
4. Run Alembic migrations as a single deployment job before starting replicas.
5. Generate synthetic data and train the initial model as a controlled job.
6. Confirm `/health` for process availability and `/ready` for usable dependencies.
7. Route HTTPS traffic to the frontend and route `/api` to the API privately.
8. Collect structured logs and scrape `/metrics` on the private service network.
9. Verify login, transaction explanation and a complete case workflow before enabling access.

Docker Compose also starts a dedicated `worker` using the backend image and shared artifact volume. The API persists queued training runs before returning HTTP 202. Workers claim database leases, renew heartbeats and retry interrupted executions with bounded attempts; stale owners cannot commit. Migrate the database before starting workers. Local development needs a separate `python -m backend.app.worker` process for API-submitted jobs. CLI seed operations execute synchronously through the same ownership checks.

The worker image must match the API image. On deployment, rebuild the backend and recreate both services together. No Redis service is required for this database-backed queue. Training persistence is serialized to avoid overlapping dataset ingestion; this prioritizes predictable behavior over distributed training throughput.

## Rollback and recovery

Keep the previous application image and model artifact. Back up the database before migrations; application rollback does not automatically reverse schema changes. Restore a compatible schema backup or apply a reviewed corrective migration. Re-promote a previously evaluated model only through an explicit administrative operation; drift is a reason to investigate, not automatic authorization to replace the model.

Monitor readiness failures, API error rates, ingestion rejections, scoring latency, alert backlog and feature drift. Alert thresholds should reflect a reference window, label coverage and staffing capacity. A synthetic benchmark does not establish a production service-level objective.

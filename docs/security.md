# Security and responsible use

All records are synthetic. A high operational score is a review priority, not proof of fraud. Investigator dispositions are opinions; they do not overwrite generator ground truth. Attribution describes a model calculation rather than a causal account of customer behavior.

## Deployment boundaries

Only the reverse-proxy frontend should be internet-facing. Keep PostgreSQL and the API on private networks. Terminate TLS at a managed load balancer, restrict configured CORS origins, and use a secrets manager for database and bootstrap credentials. Never commit `.env`. Rotate initial administrator credentials before sharing any environment.

Authentication proves a user's identity; authorization determines which operations that identity may perform. Password hashing is one-way verification, unlike reversible encryption. TLS encrypts traffic. Auditing records who changed a case and when; it does not prevent abuse by itself. Least privilege grants only the capabilities needed for a role. Data minimization avoids retaining unnecessary records even when synthetic.

The application must fail closed on protected routes. Analysts may inspect data; investigators may change cases; administrators may run data/model administration. UI hiding is convenience, not authorization. Case updates and their audit records belong in a single database transaction. Do not log passwords, authorization headers or session tokens.

The runtime container removes pip and setuptools after installation to reduce unused attack surface; rebuild the image to change dependencies. Scan the complete image as well as application packages. `reports/backend-image-audit.json` records discovered image advisories; unresolved distribution advisories must be reviewed before any external deployment. A local synthetic demo is not evidence that those advisories are harmless in another deployment.

## Production work still required

Before processing real financial data, obtain independent threat modeling, privacy and regulatory review, penetration testing, identity-provider integration, disaster recovery testing, externally anchored audit retention, managed encryption keys and organization-specific incident response. This repository makes no compliance certification claim. Artifact storage must be access-controlled because Python model deserialization is trusted-code execution.

Sessions are persisted and checked on each authenticated request. Signing out revokes the current token; password changes revoke every session for that account, and administrators can revoke another account's sessions. Existing tokens issued before the session migration require a new login. Password changes require the current password.

Migration 0005 installs database triggers rejecting UPDATE and DELETE against audit events, verified labels and monitoring incident history. PostgreSQL also rejects TRUNCATE. This protects against ordinary application SQL mistakes; a database owner who can disable triggers still has administrative control. External append-only storage and separate database credentials remain deployment responsibilities, so this is not a claim of cryptographic tamper-proofing.

## Retention and deletion

Define retention periods with the deployment owner. Back up PostgreSQL and model metadata together so historical explanations remain reproducible. Retired artifacts referenced by predictions must remain readable for the audit retention period. Purge expired synthetic datasets offline, retain aggregated reports, and verify restoration before removing backups. Do not delete a Docker volume unless intentionally resetting all application data.

`python -m backend.app.retention --days 90` previews expired rejected payloads from completed or failed runs. Adding `--apply` enables a bounded, repeatable purge suitable for an operator's scheduler; it preserves run counts, cases, model artifacts and audit history and records the deletion count atomically. The development deployment does not automatically delete existing data or infer a financial-record retention policy. Running jobs and recent rejected records are excluded.

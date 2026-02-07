# Security Checklist

## Identity and Access
- [ ] OIDC issuer and audience configured per environment.
- [ ] `SECRET_MANAGER_ENABLED=true` in staging and prod.
- [ ] Service accounts use least-privilege IAM roles only.
- [ ] RBAC checks present on every sensitive API endpoint.
- [ ] Tenant header and token tenant membership enforced.

## Secrets and Data Protection
- [ ] JWT, refresh, webhook, and provider tokens sourced from Secret Manager.
- [ ] No plaintext secrets in repository or CI logs.
- [ ] Signed URL access only for protected document content.
- [ ] PII-safe logging formatter enabled in all API processes.

## Runtime Controls
- [ ] Ingestion idempotency key enforced on document intake.
- [ ] Webhook delivery idempotency and dead-letter handling enabled.
- [ ] Low-confidence extraction routes to human review queue.
- [ ] Immutable audit events written for critical actions.

## Infrastructure and Monitoring
- [ ] Cloud Run error-rate and latency alert policies deployed.
- [ ] Pub/Sub DLQ backlog alert policy deployed.
- [ ] Cloud SQL backups enabled and tested.
- [ ] Artifact images tagged by git SHA and retained per policy.

## Release Gate
- [ ] `ruff`, `mypy`, `pytest`, and web build passing in CI.
- [ ] Alembic migrations applied before rollout.
- [ ] Incident, replay, and rollback runbooks validated.

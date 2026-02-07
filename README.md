# NexusCargo AI Platform

Production-oriented, multi-tenant logistics AI SaaS scaffold on Google Cloud.

## Monorepo layout

- `apps/api-gateway`: FastAPI gateway (`/api/v1`)
- `apps/web`: Next.js web app
- `services/*`: domain-agnostic processing services
- `modules/*`: domain modules (AWB, FIAR, AECA, AVIQM, discrepancy, station analytics, DG)
- `libs/*`: shared auth, schemas, and common platform utilities
- `infra/terraform`: baseline GCP infrastructure

## Quick start

```bash
python3 -m pip install -e '.[dev]'
./scripts/preflight.sh checks
uvicorn main:app --app-dir apps/api-gateway --host 0.0.0.0 --port 8080
```

Web app:

```bash
cd apps/web
npm install --cache .npm-cache
npm run build
npm run dev
```

## Quality gates

- Lint: `python3 -m ruff check .`
- Typecheck: `python3 -m mypy libs services modules apps/api-gateway tests`
- Tests + coverage: `python3 -m pytest`

## Security controls included

- Tenant-scoped API dependencies and query filters
- Role-based endpoint access
- Ingestion idempotency keys
- Immutable audit event writes
- Low-confidence review routing
- Webhook HMAC signatures + retry
- Refresh token rotation storage
- PII-safe structured logging

## Infrastructure baseline (GCP)

Terraform includes VPC, Cloud SQL, GCS buckets, Pub/Sub + DLQ, Cloud Run service/job, Artifact Registry, Secret Manager, Redis, BigQuery dataset, and Monitoring alert policy.

# Implementation Summary

## DB migrations and schema

- Alembic baseline migration:
  - `alembic/versions/0001_initial_schema.py`
- Required minimum tables included:
  - tenants, users, roles, tenant_memberships
  - documents, document_versions, document_classifications, extracted_entities
  - validation_results, review_tasks, corrections
  - shipments, awb_records, freight_invoices, contracts, three_way_match_results
  - discrepancies, disputes
  - exports, vehicle_import_cases, compliance_checks
  - alerts, webhook_subscriptions, webhook_deliveries, audit_events
- Additional hardening tables:
  - refresh_tokens, idempotency_keys

## Event contracts

Defined in `libs/schemas/events.py`:
- document.received
- document.preprocessed
- document.classified
- document.extracted
- document.validated
- review.required
- review.completed
- discrepancy.detected
- export.submission.updated
- invoice.dispute.updated

## API endpoints (implemented)

- Auth
  - `POST /api/v1/auth/token`
  - `POST /api/v1/auth/refresh`
- Ingestion and documents
  - `POST /api/v1/ingestion/documents`
  - `GET /api/v1/documents`
  - `GET /api/v1/documents/{document_id}`
  - `GET /api/v1/documents/{document_id}/signed-url`
- Review
  - `GET /api/v1/review/tasks`
  - `POST /api/v1/review/tasks/{task_id}/complete`
- Domain
  - `POST /api/v1/awb/validate`
  - `POST /api/v1/fiar/three-way-match`
  - `POST /api/v1/aeca/validate`
  - `GET /api/v1/aviqm/vin/{vin}`
  - `POST /api/v1/discrepancy/score`
  - `POST /api/v1/station-analytics/throughput`
  - `POST /api/v1/dg/validate`
- Active learning
  - `POST /api/v1/active-learning/curate`
- Webhooks
  - `POST /api/v1/webhooks/subscriptions`
  - `POST /api/v1/webhooks/dispatch`
- Analytics
  - `GET /api/v1/analytics/overview`

## UI routes (implemented)

- `/`
- `/login`
- `/documents`
- `/review`
- `/dashboards/awb`
- `/dashboards/fiar`
- `/dashboards/aeca`
- `/dashboards/aviqm`
- `/dashboards/station-analytics`

## Terraform resources

- VPC + subnet + firewall
- Cloud SQL PostgreSQL instance + database
- Cloud Storage buckets (raw, processed, audit archive)
- Pub/Sub topics and DLQ subscriptions
- Cloud Run service and Cloud Run job
- Artifact Registry
- Memorystore Redis
- Secret Manager secrets
- BigQuery dataset
- Monitoring alert policy

## CI/CD

Workflow: `.github/workflows/ci-cd.yml`
- lint -> typecheck -> test -> build -> security_scan -> deploy_staging -> deploy_prod
- Staging/prod deploy stages use GCP Workload Identity Federation action hooks.

# Architecture

## Core flow

```text
[API/UI Ingestion]
   -> document.received
   -> [Preprocessing]
   -> document.preprocessed
   -> [Classification]
   -> document.classified
   -> [Extraction (Mock Document AI/Vertex adapter)]
   -> document.extracted
   -> [Validation Rules]
   -> document.validated
   -> [Review Routing if low confidence/fail]
       -> review.required
       -> [Human Review]
       -> review.completed
```

## Service boundary map

- `apps/api-gateway`: tenant-aware API boundary, auth, RBAC, idempotency, orchestration.
- `services/*`: shared processing pipeline and cross-cutting concerns.
- `modules/*`: domain logic and provider adapters.
- `libs/common`: config, DB, events, storage, audit, idempotency, rate limiting.
- `libs/auth`: JWT issue/verify and tenant role dependencies.
- `libs/schemas`: API and event contracts.

## Data and infra

- OLTP: Cloud SQL PostgreSQL (local sqlite for tests)
- Object storage: Cloud Storage (local file adapter in dev)
- Messaging: Pub/Sub + DLQ (in-memory bus in tests)
- Runtime: Cloud Run services/jobs
- Analytics: BigQuery baseline dataset
- Secrets: Secret Manager path

## Tenant isolation model

- `X-Tenant-Id` required for `/api/v1` routes (except auth/docs).
- Access token contains `tenant_ids` and `roles`.
- Request tenant must belong to token tenant list.
- Queries and mutations include tenant filters at service/repository level.

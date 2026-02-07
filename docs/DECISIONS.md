# Decisions

## D-001: Modular monorepo with Python-first backend spine
- Date: 2026-02-07
- Decision: Implement backend core in Python 3.12 with FastAPI + SQLAlchemy and keep module-specific services in dedicated directories.
- Rationale: Satisfies mandatory stack while enabling incremental vertical slices.

## D-002: Event abstraction with in-memory and Pub/Sub adapters
- Date: 2026-02-07
- Decision: Introduce an `EventBus` interface with an in-memory implementation for local tests and a GCP Pub/Sub implementation for deployment.
- Rationale: Keeps tests deterministic while preserving production architecture alignment.

## D-003: Enforce tenant scoping at API dependency boundary
- Date: 2026-02-07
- Decision: Every API read/write path must consume tenant context from auth + header dependency and pass tenant id into service/repository functions.
- Rationale: Prevents accidental cross-tenant access in shared infrastructure.

## D-004: Core workflow coverage gate scoped to critical services
- Date: 2026-02-07
- Decision: Enforce `>=80%` coverage on core orchestration services and shared auth/idempotency paths in this MVP cycle.
- Rationale: Ensures strict quality on highest-risk logic while broad module expansion continues in subsequent cycles.

## D-005: Next.js 16 baseline for security patch posture
- Date: 2026-02-07
- Decision: Upgrade web app from `next@15.1.7` to `next@16.1.6`.
- Rationale: Removed a known vulnerability and achieved clean `npm audit` results.

## D-006: Runtime-validated non-dev secret policy
- Date: 2026-02-08
- Decision: Enforce runtime constraints that require Secret Manager in staging/prod and block startup when this policy is violated.
- Rationale: Prevents accidental deployment with plaintext-only secret sources.

## D-007: Pluggable extraction backend with GCP-first adapter
- Date: 2026-02-08
- Decision: Introduce `DocumentExtractor` with `mock` and `gcp` backends, using Document AI + Vertex Gemini when `ai_backend=gcp`.
- Rationale: Preserves local determinism while enabling production-aligned AI execution paths.

## D-008: Versioned validation rule packs
- Date: 2026-02-08
- Decision: Move validation checks into a `ValidationRulesEngine` with explicit `RulePack` version metadata and explainable rule outputs.
- Rationale: Enables traceable compliance behavior and safe rule evolution.

## D-009: Adapter contracts with mock-first and HTTP production path
- Date: 2026-02-08
- Decision: Implement strict adapter interfaces for AWB providers, ABF/ICS submission, and accounting exports with both robust mocks and HTTP-backed clients.
- Rationale: Keeps local/dev deterministic while allowing production endpoints and Secret Manager credentials in staging/prod.

## D-010: Queue-first webhook delivery with replay
- Date: 2026-02-08
- Decision: Move webhook delivery from inline retries to queue state (`pending/retry_scheduled/dead_lettered`) processed by worker loops and explicit replay APIs.
- Rationale: Prevents request-path blocking and supports safer operational recovery.

## D-011: Active learning model registry and rollback
- Date: 2026-02-08
- Decision: Add `model_versions` persistence and API workflows for register/list/rollback operations per tenant/domain/model.
- Rationale: Provides auditable rollback control for AI model deployments.

## D-012: CI/CD pre-deploy infra validation and migration gate
- Date: 2026-02-08
- Decision: Extend CI/CD with Terraform validation and migration execution in staging/prod deploy jobs.
- Rationale: Reduces deployment drift and schema/runtime mismatch risk.

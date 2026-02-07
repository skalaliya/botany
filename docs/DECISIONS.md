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

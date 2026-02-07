# Risks

## R-001: Scope breadth vs hard-stop budget
- Severity: High
- Risk: Full Phase 1-4 implementation may exceed single-session runtime.
- Mitigation: Maintain resumable state (`.codex/state.json`) and prioritize production-critical controls first.

## R-002: External adapter uncertainty
- Severity: Medium
- Risk: Real APIs for CHAMP, CargoWise, ABF/ICS, and accounting systems may vary.
- Mitigation: Use strict adapter interfaces with realistic mocked providers and contract tests.

## R-003: Security regressions in rapid iteration
- Severity: High
- Risk: Multi-tenant leakage or auth bypass during fast changes.
- Mitigation: Enforce dependency-based tenant + RBAC checks, add integration tests, fail review gate on missing evidence.

## R-004: Mock adapter drift from real provider behavior
- Severity: Medium
- Risk: Mock integrations may diverge from production partner API semantics.
- Mitigation: Add contract snapshots and staging smoke tests against sandbox/provider mocks with parity checks.

## R-005: GCP AI response schema instability
- Severity: Medium
- Risk: Vertex responses can deviate from strict JSON shape and require defensive parsing.
- Mitigation: Enforce strict JSON prompt contract, reject malformed outputs, and route low-confidence/invalid extraction to review.

## R-006: Webhook delivery durability in high-volume failures
- Severity: Medium
- Risk: In-process retry loops can delay worker throughput during persistent endpoint failures.
- Mitigation: Keep `dead_lettered` terminal state, move delivery retries into dedicated Cloud Run job/queue worker in next cycle.

## R-007: Provider endpoint variance across tenant integrations
- Severity: Medium
- Risk: HTTP adapter contracts are stable, but production providers can return variant payloads and status codes.
- Mitigation: Enforce contract tests per provider sandbox and extend tolerant response normalization before production onboarding.

## R-008: Model rollback governance drift
- Severity: Medium
- Risk: Rollback APIs are available, but human approval workflows may be bypassed operationally.
- Mitigation: Require role-based admin access, audit every rollback, and include model rollback runbook verification in release gates.

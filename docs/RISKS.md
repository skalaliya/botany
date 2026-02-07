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

# Assumptions

## Baseline (Cycle 1)

1. Source reference docs were not present:
   - `/mnt/data/awb_platform_architecture.md`
   - `/mnt/data/logistics_product_ideas.md`
2. GCP project, networking, and service accounts are provisioned per environment outside this repo, and Terraform in this repo manages application resources inside those projects.
3. Local development uses SQLite for fast tests; staging/prod use Cloud SQL PostgreSQL through environment configuration.
4. Identity Platform (OIDC/JWT) is the primary auth provider. Local development uses a deterministic signing secret sourced from environment variables only.
5. External systems (CHAMP, IBS iCargo, CargoWise, ABF/ICS, accounting exports) are integrated through adapters with mock providers enabled by default.
6. First implementation pass prioritizes a runnable Phase 1 MVP spine with strict tenant scoping, audit hooks, idempotency, and review routing.
7. Where functionality is partially implemented, every placeholder includes a TODO with explicit owner context and next action.
8. Local execution environment currently exposes `python3` only; CI and container runtime remain pinned to Python 3.12 for deployment parity.

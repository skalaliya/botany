# PREFLIGHT TODO

## P0 (Critical)

- Configure GitHub remote:
  - `git remote add origin <repo-url>`
  - `git ls-remote --heads origin`
- Add at least one service manifest (`package.json` or `pyproject.toml`) so dependency/bootstrap checks can run meaningfully.

## P1 (High)

- Replace placeholder `.env.example` values with project-specific required keys.
- Add project check scripts (lint/typecheck/test/build) so `scripts/preflight.sh checks` executes real validation.
- Add migration and health-check commands once DB and app entrypoint are defined.

## P2 (Nice to have)

- Extend `scripts/preflight.sh` with workspace/monorepo traversal once multiple apps/services are present.
- Add CI job that executes preflight checks on each pull request.

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STACKS=()

detect_stack() {
  STACKS=()

  if [[ -f "package.json" ]]; then
    STACKS+=("node")
  fi
  if [[ -f "pnpm-lock.yaml" ]]; then
    STACKS+=("pnpm")
  elif [[ -f "yarn.lock" ]]; then
    STACKS+=("yarn")
  elif [[ -f "package-lock.json" ]]; then
    STACKS+=("npm")
  fi

  if [[ -f "pyproject.toml" ]]; then
    STACKS+=("python")
  fi
  if [[ -f "poetry.lock" ]]; then
    STACKS+=("poetry")
  elif [[ -f "requirements.txt" ]]; then
    STACKS+=("pip")
  fi

  if [[ -f "docker-compose.yml" || -f "docker-compose.yaml" || -f "compose.yml" || -f "compose.yaml" ]]; then
    STACKS+=("docker-compose")
  fi
}

print_stack() {
  detect_stack
  if [[ ${#STACKS[@]} -eq 0 ]]; then
    echo "No stack files detected."
  else
    echo "Detected: ${STACKS[*]}"
  fi
}

install_deps() {
  detect_stack

  if [[ -f "pnpm-lock.yaml" && -f "package.json" ]]; then
    pnpm install --frozen-lockfile
  elif [[ -f "yarn.lock" && -f "package.json" ]]; then
    yarn install --frozen-lockfile
  elif [[ -f "package-lock.json" && -f "package.json" ]]; then
    npm ci
  elif [[ -f "package.json" ]]; then
    npm install
  fi

  if [[ -f "pyproject.toml" && -f "poetry.lock" ]]; then
    poetry install --no-interaction --no-root
  elif [[ -f "requirements.txt" ]]; then
    python3 -m pip install -r requirements.txt
  fi
}

run_if_script_exists() {
  local script_name="$1"
  if [[ -f "package.json" ]] && grep -q "\"${script_name}\"[[:space:]]*:" "package.json"; then
    if [[ -f "pnpm-lock.yaml" ]]; then
      pnpm run "$script_name"
    elif [[ -f "yarn.lock" ]]; then
      yarn "$script_name"
    else
      npm run "$script_name"
    fi
  fi
}

run_checks() {
  run_if_script_exists "format:check"
  run_if_script_exists "format"
  run_if_script_exists "lint"
  run_if_script_exists "typecheck"
  run_if_script_exists "test"
  run_if_script_exists "build"

  if [[ -f "pyproject.toml" ]]; then
    if command -v ruff >/dev/null 2>&1; then
      ruff check .
    fi
    if command -v pytest >/dev/null 2>&1; then
      pytest -q
    fi
  fi
}

usage() {
  cat <<'EOF'
Usage: scripts/preflight.sh [detect|install|checks|all]
  detect  Print detected stack files.
  install Install dependencies using lockfile-aware commands.
  checks  Run lightweight configured checks.
  all     Run detect, install, and checks.
EOF
}

cmd="${1:-all}"

case "$cmd" in
  detect)
    print_stack
    ;;
  install)
    install_deps
    ;;
  checks)
    run_checks
    ;;
  all)
    print_stack
    install_deps
    run_checks
    ;;
  *)
    usage
    exit 1
    ;;
esac

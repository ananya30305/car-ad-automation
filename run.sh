#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

cmd="${1:-help}"
shift || true

case "$cmd" in
  inspect)
    python scripts/inspect_form.py "$@"
    ;;
  inspect-source)
    python scripts/inspect_source.py "$@"
    ;;
  prepare|validate)
    python -m app.pipeline --prepare "$@"
    ;;
  dry-run)
    python -m app.pipeline --batch --dry-run "$@"
    ;;
  dry-run-one)
    id="${1:?usage: ./run.sh dry-run-one <id>}"
    shift
    python -m app.pipeline --id "$id" --dry-run "$@"
    ;;
  post)
    python -m app.pipeline --batch --submit "$@"
    ;;
  post-one)
    id="${1:?usage: ./run.sh post-one <id>}"
    shift
    python -m app.pipeline --id "$id" --submit "$@"
    ;;
  test)
    python -m pytest tests/ -q "$@"
    ;;
  help|*)
    cat <<'EOF'
Usage: ./run.sh <command>

  inspect          Open destination form inspector (login + dump selectors)
  inspect-source   Inspect one source id → canonical + preflight
  prepare          Ingest → canonicalize → preflight (no browser)
  validate         Alias for prepare
  dry-run          Prepare + dry-run batch (blocked until form_map ready)
  dry-run-one ID   Prepare + dry-run one vehicle
  post             Prepare + submit batch (requires form_map ready_for_browser)
  post-one ID      Prepare + submit one vehicle
  test             Run unit tests

Examples:
  ./run.sh prepare
  ./run.sh inspect-source --id 11195371
  ./run.sh dry-run-one 11195371
  python -m app.pipeline --id 11195371 --dry-run
EOF
    ;;
esac

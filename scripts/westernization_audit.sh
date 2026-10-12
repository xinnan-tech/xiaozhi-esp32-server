#!/usr/bin/env bash

# Thin wrapper around the Python implementation so CI (and muscle memory) can
# keep calling this script. All scan logic and the exception policy live in
# westernization_audit.py; keeping a single implementation guarantees CI and
# local runs agree.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for this audit." >&2
  exit 1
fi

exec python3 scripts/westernization_audit.py

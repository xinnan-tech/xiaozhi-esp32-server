#!/usr/bin/env bash
#
# Post-rebase verification gate for the westernized downstream branch.
#
# Run this after every upstream sync/rebase, BEFORE promoting the integration
# branch. It chains the checks that historically caught real regressions that
# `npm run build` and the unit suites do NOT catch on their own:
#
#   * westernization audit  (Han-script / path scan, exception zones)
#   * manager-web integrity (undefined identifiers, template tag mismatches,
#     duplicated Vue option keys -> the silent-blank-page class of bugs)
#   * manager-web i18n parity + referenced-key coverage
#   * manager-web snapshot/contract + unit tests
#   * manager-web production build
#
# Subsystem suites that need heavier toolchains (Java, Python) are listed at
# the end but only run when their toolchain is present, so this script is safe
# to run in a web-only environment.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0
run() {
  local name="$1"; shift
  echo
  echo "==> $name"
  if "$@"; then
    echo "--- PASS: $name"
  else
    echo "--- FAIL: $name"
    fail=1
  fi
}

# 1. Westernization audit (Han-script, paths, generator bundle).
run "westernization audit" bash scripts/westernization_audit.sh

# 2..5 manager-web checks (need node_modules; install if missing).
if [ -d main/manager-web/node_modules ] || npm --prefix main/manager-web ci --no-audit --no-fund >/dev/null 2>&1; then
  run "manager-web integrity"   node main/manager-web/scripts/integrity-check.js
  run "manager-web i18n parity" npm --prefix main/manager-web run --silent check:i18n
  run "manager-web snapshot tests" npm --prefix main/manager-web run --silent test:snapshot
  run "manager-web contract tests" npm --prefix main/manager-web run --silent test:contract
  run "manager-web unit tests"  npm --prefix main/manager-web run --silent test:unit
  run "manager-web build"       npm --prefix main/manager-web run --silent build
else
  echo "!! manager-web: node/npm unavailable or install failed - SKIPPING web checks"
  fail=1
fi

# 6. Optional heavier suites when toolchains exist.
if command -v mvn >/dev/null 2>&1; then
  run "manager-api compile" mvn -q -f main/manager-api/pom.xml -DskipTests compile
else
  echo "==> mvn not present - skipping manager-api compile"
fi

if command -v python3 >/dev/null 2>&1 && python3 -c 'import pytest' >/dev/null 2>&1; then
  ( cd main/xiaozhi-server && PYTHONPATH=. pytest tests/ -q ) \
    && echo "--- PASS: python tests" || { echo "--- FAIL: python tests"; fail=1; }
  # Upstream ships unittest-only lifecycle tests (excluded from pytest via
  # __test__ = False); run them explicitly.
  ( cd main/xiaozhi-server && PYTHONPATH=. python3 -B -m unittest discover -s tests -p 'test_*lifecycle*.py' ) \
    && echo "--- PASS: python lifecycle tests" || { echo "--- FAIL: python lifecycle tests"; fail=1; }
else
  echo "==> pytest not present - skipping python tests"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "ALL REBASE CHECKS PASSED"
else
  echo "REBASE CHECKS FAILED - fix the above before promoting the branch"
fi
exit "$fail"

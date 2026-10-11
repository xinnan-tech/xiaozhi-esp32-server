#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v rg >/dev/null 2>&1; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ripgrep (rg) or python3 is required for this audit." >&2
    exit 1
  fi
  python3 - <<'PY'
from pathlib import Path
import re
import subprocess
import sys

root = Path(".")
locale_pattern = "zh-" + "CN|" + "zh-" + "TW"
content_pattern = re.compile(r"[\u4e00-\u9fff]|" + locale_pattern)
path_pattern = re.compile(r"[\u4e00-\u9fff]")

content_skip_dirs = {
    ".git",
    "node_modules",
    "dist",
    "target",
    "build",
}
content_skip_exts = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bin", ".onnx", ".so",
    ".ttf", ".woff", ".woff2", ".mp3", ".wav", ".opus", ".pdf",
    ".ico", ".svg",
}
main_exceptions = (
    "main/manager-api/src/main/resources/db/changelog",
    "main/manager-web/public/generator",
)
generated_exception_paths = (
    "main/manager-web/public/generator",
)
path_skip_prefixes = (
    ".git",
    "node_modules",
    "main/manager-web/node_modules",
    "main/manager-web/dist",
    "main/manager-api/target",
)

def section(title):
    print(f"\n== {title} ==")

def rel(path):
    return path.relative_to(root).as_posix()

def is_under(path_text, prefixes):
    return any(path_text == prefix or path_text.startswith(prefix + "/") for prefix in prefixes)

def should_skip_content(path):
    parts = set(path.parts)
    if parts & content_skip_dirs:
        return True
    return path.suffix.lower() in content_skip_exts

def candidate_files():
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "-co", "--exclude-standard"],
            text=True,
        )
        return [root / line for line in output.splitlines() if line]
    except Exception:
        return [path for path in root.rglob("*") if path.is_file()]

def scan_paths(predicate):
    matches = []
    for path in candidate_files():
        if not path.is_file():
            continue
        path_text = rel(path)
        if should_skip_content(Path(path_text)) or not predicate(path_text):
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if content_pattern.search(line):
                matches.append((path_text, line_no, line[:240]))
    return matches

section("Live Source And Docs Audit")
live_matches = scan_paths(lambda path_text: not is_under(path_text, main_exceptions))
if live_matches:
    for path_text, line_no, line in live_matches:
        print(f"{path_text}:{line_no}:{line}")
    print("\nLive source/doc audit: FAIL")
    live_status = 1
else:
    print("Live source/doc audit: PASS")
    live_status = 0

section("Historical Changelog Exceptions")
changelog_matches = scan_paths(lambda path_text: is_under(path_text, (main_exceptions[0],)))
if changelog_matches:
    print(f"{len(changelog_matches)} match(es). Showing up to 40:")
    for path_text, line_no, line in changelog_matches[:40]:
        print(f"{path_text}:{line_no}:{line}")
    if len(changelog_matches) > 40:
        print("... truncated ...")
    print("\nHistorical changelog exceptions detected above.")
else:
    print("No matches.")
    print("No historical changelog hits.")

section("Generated Bundle Exceptions")
generated_matches = scan_paths(lambda path_text: is_under(path_text, generated_exception_paths))
if generated_matches:
    print(f"{len(generated_matches)} match(es). Showing up to 40:")
    for path_text, line_no, line in generated_matches[:40]:
        print(f"{path_text}:{line_no}:{line}")
    if len(generated_matches) > 40:
        print("... truncated ...")
    print("\nGenerated bundle exceptions detected above.")
else:
    print("No matches.")
    print("No generated bundle hits.")

section("Path Audit")
path_matches = []
for path in candidate_files():
    if not path.is_file():
        continue
    path_text = rel(path)
    if is_under(path_text, path_skip_prefixes):
        continue
    if path_pattern.search(path_text):
        path_matches.append(path_text)
if path_matches:
    print("\n".join(path_matches))
    print("\nPath audit: FAIL")
    path_status = 1
else:
    print("Path audit: PASS")
    path_status = 0

section("Summary")
if live_status == 0 and path_status == 0:
    print("Westernization baseline is clean outside intentional exceptions.")
    print("Intentional exceptions:")
    print("- append-only Liquibase history under main/manager-api/src/main/resources/db/changelog")
    print("- vendored generator bundle under main/manager-web/public/generator")
    sys.exit(0)

print("Westernization baseline still has non-exempt findings.")
sys.exit(1)
PY
  exit $?
fi

CONTENT_IGNORE=(
  "!**/.git/**"
  "!**/node_modules/**"
  "!**/.venv*/**"
  "!**/dist/**"
  "!**/target/**"
  "!**/build/**"
  "!**/*.png"
  "!**/*.jpg"
  "!**/*.jpeg"
  "!**/*.gif"
  "!**/*.webp"
  "!**/*.bin"
  "!**/*.onnx"
  "!**/*.so"
  "!**/*.ttf"
  "!**/*.woff"
  "!**/*.woff2"
  "!**/*.mp3"
  "!**/*.wav"
  "!**/*.opus"
  "!**/*.pdf"
)

MAIN_IGNORE=(
  "${CONTENT_IGNORE[@]}"
  "!main/manager-api/src/main/resources/db/changelog/**"
  "!main/manager-web/public/generator/**"
)

CONTENT_PATTERN='[\p{Han}]|zh-C''N|zh-T''W'
PATH_IGNORE=(
  "./.git"
  "./node_modules"
  "./main/manager-web/node_modules"
  "./main/manager-web/dist"
  "./main/manager-api/target"
)

section() {
  printf '\n== %s ==\n' "$1"
}

collect_audit_roots() {
  AUDIT_SEARCH_ROOTS=()
  local candidate
  for candidate in main docs scripts; do
    if [[ -e "$candidate" ]]; then
      AUDIT_SEARCH_ROOTS+=("$candidate")
    fi
  done
  shopt -s nullglob
  for candidate in *.md; do
    AUDIT_SEARCH_ROOTS+=("$candidate")
  done
  shopt -u nullglob
  if [[ ${#AUDIT_SEARCH_ROOTS[@]} -eq 0 ]]; then
    echo "No audit search roots found." >&2
    exit 1
  fi
}

run_rg() {
  local pattern="$1"
  shift
  local -a rg_globs=()
  local glob
  for glob in "$@"; do
    rg_globs+=(-g "$glob")
  done
  # Ripgrep matches nothing when every -g is negated and the search root is ".".
  # Scan explicit roots so negated globs filter within them instead of excluding all files.
  rg -n --no-messages "$pattern" "${AUDIT_SEARCH_ROOTS[@]}" "${rg_globs[@]}"
}

show_limited_matches() {
  local title="$1"
  local pattern="$2"
  shift 2
  local matches
  matches="$(rg -n "$pattern" "$@" || true)"
  if [[ -z "$matches" ]]; then
    echo "No matches."
    return 1
  fi

  local count
  count="$(printf '%s\n' "$matches" | wc -l | tr -d ' ')"
  echo "$count match(es). Showing up to 40:"
  printf '%s\n' "$matches" | sed -n '1,40p' | cut -c1-240
  if [[ "$count" -gt 40 ]]; then
    echo "... truncated ..."
  fi
  return 0
}

section "Live Source And Docs Audit"
collect_audit_roots
if run_rg "$CONTENT_PATTERN" "${MAIN_IGNORE[@]}"; then
  echo
  echo "Live source/doc audit: FAIL"
  live_status=1
else
  echo "Live source/doc audit: PASS"
  live_status=0
fi

section "Historical Changelog Exceptions"
if show_limited_matches \
  "Historical changelog exceptions" \
  "$CONTENT_PATTERN" \
  main/manager-api/src/main/resources/db/changelog; then
  echo
  echo "Historical changelog exceptions detected above."
else
  echo "No historical changelog hits."
fi

section "Generated Bundle Exceptions"
if show_limited_matches \
  "Generated bundle exceptions" \
  "$CONTENT_PATTERN" \
  main/manager-web/public/generator \
  -g '!**/*.png' -g '!**/*.jpg' -g '!**/*.jpeg'; then
  echo
  echo "Generated bundle exceptions detected above."
else
  echo "No generated bundle hits."
fi

section "Path Audit"
path_output="$(
  find . \
    $(printf " -path '%s' -prune -o" "${PATH_IGNORE[@]}") \
    -type f -print | rg '[\p{Han}]' || true
)"
if [[ -n "$path_output" ]]; then
  printf '%s\n' "$path_output"
  echo
  echo "Path audit: FAIL"
  path_status=1
else
  echo "Path audit: PASS"
  path_status=0
fi

section "Summary"
if [[ "$live_status" -eq 0 && "$path_status" -eq 0 ]]; then
  echo "Westernization baseline is clean outside intentional exceptions."
  echo "Intentional exceptions:"
  echo "- append-only Liquibase history under main/manager-api/src/main/resources/db/changelog"
  echo "- vendored generator bundle under main/manager-web/public/generator"
  exit 0
fi

echo "Westernization baseline still has non-exempt findings."
exit 1

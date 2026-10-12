#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Exception policy (agreed 2026-10-12):
#  - Append-only Liquibase history under
#    main/manager-api/src/main/resources/db/changelog keeps its historical
#    Chinese seed/updates (a fresh install is migrated + cleaned to English by
#    the append-only 202610111200.sql changeset).
#  - main/manager-web/public/generator/static is functional device data
#    (charset codepoint tables, CJK glyph tables, emoji gifs, wakeword model
#    blobs) consumed byte-for-byte by the firmware toolchain: exempt.
#  - The generator CODE bundle (generator/assets/**, generator/index.html) is
#    rebuilt from the translated generator source and is NOT exempt; it is
#    scanned like live source. One allowlisted artefact is tolerated: the
#    opentype.js LCID -> BCP47 table (e.g. 1028 -> zh TW locale id), a font
#    parsing table, not user-facing text.

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
# Third-party LCID -> BCP47 mapping in vendored opentype.js (font name tables).
allowline_pattern = re.compile(r"\d+:\"zh-(?:CN|TW)\"")

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
changelog_exception = "main/manager-api/src/main/resources/db/changelog"
generator_root = "main/manager-web/public/generator"
generator_data_exception = generator_root + "/static"
live_exceptions = (changelog_exception, generator_data_exception)
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

def scan_paths(predicate, allowlist=False):
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
                if allowlist and allowline_pattern.search(line):
                    continue
                matches.append((path_text, line_no, line[:240]))
    return matches

section("Live Source And Docs Audit")
live_matches = scan_paths(lambda path_text: not is_under(path_text, live_exceptions), allowlist=True)
if live_matches:
    for path_text, line_no, line in live_matches:
        print(f"{path_text}:{line_no}:{line}")
    print("\nLive source/doc audit: FAIL")
    live_status = 1
else:
    print("Live source/doc audit: PASS")
    live_status = 0

section("Historical Changelog Exceptions")
changelog_matches = scan_paths(lambda path_text: is_under(path_text, (changelog_exception,)))
if changelog_matches:
    print(f"{len(changelog_matches)} match(es). Showing up to 40:")
    for path_text, line_no, line in changelog_matches[:40]:
        print(f"{path_text}:{line_no}:{line}")
    if len(changelog_matches) > 40:
        print("... truncated ...")
    print("\nHistorical changelog exceptions detected above.")
else:
    print("No historical changelog hits.")

section("Vendored Device Data Exceptions")
data_matches = scan_paths(lambda path_text: is_under(path_text, (generator_data_exception,)))
if data_matches:
    print(f"{len(data_matches)} match(es). Showing up to 40:")
    for path_text, line_no, line in data_matches[:40]:
        print(f"{path_text}:{line_no}:{line}")
    if len(data_matches) > 40:
        print("... truncated ...")
    print("\nVendored device data exceptions detected above (byte-exact data, not prose).")
else:
    print("No vendored device data hits.")

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
    print("- append-only Liquibase history under " + changelog_exception)
    print("- vendored device data under " + generator_data_exception)
    print("- opentype.js LCID table (1028:\"zh-" "TW\") inside the generator bundle")
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
  "!main/manager-web/public/generator/static/**"
)

CONTENT_PATTERN='[\p{Han}]|zh-C''N|zh-T''W'
# Third-party LCID -> BCP47 mapping inside the vendored opentype.js font
# parser (e.g. LCID 1028 mapped to a zh TW locale id); font metadata, not text.
ALLOWLINE_PATTERN='[0-9]+:"zh-(CN|TW)"'
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
if matches="$(run_rg "$CONTENT_PATTERN" "${MAIN_IGNORE[@]}" | rg -v "$ALLOWLINE_PATTERN" || true)" && [[ -n "$matches" ]]; then
  printf '%s\n' "$matches"
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

section "Vendored Device Data Exceptions"
if show_limited_matches \
  "Vendored device data exceptions" \
  "$CONTENT_PATTERN" \
  main/manager-web/public/generator/static \
  -g '!**/*.png' -g '!**/*.jpg' -g '!**/*.jpeg'; then
  echo
  echo "Vendored device data exceptions detected above (byte-exact data, not prose)."
else
  echo "No vendored device data hits."
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
  echo "- vendored device data under main/manager-web/public/generator/static"
  echo "- opentype.js LCID font-name table inside the generator bundle"
  exit 0
fi

echo "Westernization baseline still has non-exempt findings."
exit 1

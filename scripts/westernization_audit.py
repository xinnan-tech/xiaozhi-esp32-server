#!/usr/bin/env python3
"""Westernization audit: single implementation used locally and in CI.

Deterministic scan over `git ls-files -co --exclude-standard` (plus a filesystem
sweep fallback outside a git checkout), so tracked files hidden from ripgrep by
gitignore rules (e.g. `*.json` ignores) are still inspected. Binary files (NUL
byte) and known media/font extensions are skipped: their bytes occasionally
decode as stray CJK codepoints and produce false positives.

Exception zones (agreed policy, see westernization.md):
  - append-only Liquibase history under main/manager-api/src/main/resources/db/changelog
  - vendored device data under main/manager-web/public/generator/static
  - one allowlisted third-party artefact: the opentype.js LCID -> BCP47
    font-name table line inside the generator bundle
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(".")

LOCALE_PATTERN = "zh-" + "CN|" + "zh-" + "TW"
CONTENT_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]|" + LOCALE_PATTERN)
PATH_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
# Third-party LCID -> BCP47 mapping table shipped inside the generator bundle
# (opentype.js font name tables); machine locale ids, not user-facing text.
ALLOWLINE_PATTERN = re.compile(r'\d+:"' + "zh-" + r"(?:CN|TW)\"")

CHANGELOG_EXCEPTION = "main/manager-api/src/main/resources/db/changelog"
GENERATOR_ROOT = "main/manager-web/public/generator"
GENERATOR_DATA_EXCEPTION = GENERATOR_ROOT + "/static"
LIVE_EXCEPTIONS = (CHANGELOG_EXCEPTION, GENERATOR_DATA_EXCEPTION)

SKIP_DIR_PARTS = {
    ".git", "node_modules", ".venv", ".venv-xiaozhi", "venv",
    "dist", "target", "build", "unpackage", "__pycache__", ".pytest_cache",
}
SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".bin", ".onnx", ".so", ".dll", ".dylib", ".a", ".o",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".mp3", ".wav", ".opus", ".ogg", ".m4a", ".mp4", ".webm",
    ".pdf", ".zip", ".gz", ".xz", ".7z", ".jar", ".war",
    ".pyc", ".pyo", ".class", ".key", ".crt", ".pem", ".p12",
    # Cubism / model blobs (may lack NUL in compressed payloads)
    ".can3", ".cmo3", ".cmfx", ".moc3", ".moc",
}


def section(title: str) -> None:
    print(f"\n== {title} ==")


def is_under(path_text: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        path_text == prefix or path_text.startswith(prefix + "/")
        for prefix in prefixes
    )


def candidate_files() -> list[Path]:
    try:
        listing = subprocess.check_output(
            ["git", "ls-files", "-co", "--exclude-standard"],
            text=True, stderr=subprocess.DEVNULL,
        )
        return [ROOT / line for line in listing.splitlines() if line]
    except Exception:
        files: list[Path] = []
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            parts = set(path.parts)
            if parts & SKIP_DIR_PARTS:
                continue
            files.append(path)
        return files


def is_text(path: Path) -> bool:
    if path.suffix.lower() in SKIP_EXTS:
        return False
    try:
        with path.open("rb") as fh:
            return b"\x00" not in fh.read(65536)
    except OSError:
        return False


def read_text(path: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def scan(files: list[Path], predicate, allowlist: bool = False):
    matches = []
    for path in files:
        if not path.is_file():
            continue
        try:
            path_text = path.relative_to(ROOT).as_posix()
        except ValueError:
            path_text = str(path)
        if set(Path(path_text).parts) & SKIP_DIR_PARTS or not predicate(path_text):
            continue
        if not is_text(path):
            continue
        text = read_text(path)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if CONTENT_PATTERN.search(line):
                if allowlist and ALLOWLINE_PATTERN.search(line):
                    continue
                matches.append((path_text, line_no, line[:240]))
    return matches


def report_exception(title: str, files: list[Path], prefix: str) -> None:
    section(title)
    matches = scan(files, lambda p: is_under(p, (prefix,)))
    if matches:
        print(f"{len(matches)} match(es). Showing up to 40:")
        for path_text, line_no, line in matches[:40]:
            print(f"{path_text}:{line_no}:{line}")
        if len(matches) > 40:
            print("... truncated ...")
        print(f"\n{title} detected above (exempt zone).")
    else:
        print("No matches.")


def main() -> int:
    files = candidate_files()

    section("Live Source And Docs Audit")
    live_matches = scan(
        files,
        lambda p: not is_under(p, LIVE_EXCEPTIONS),
        allowlist=True,
    )
    if live_matches:
        for path_text, line_no, line in live_matches:
            print(f"{path_text}:{line_no}:{line}")
        print("\nLive source/doc audit: FAIL")
        live_status = 1
    else:
        print("Live source/doc audit: PASS")
        live_status = 0

    report_exception(
        "Historical Changelog Exceptions", files, CHANGELOG_EXCEPTION
    )
    report_exception(
        "Vendored Device Data Exceptions", files, GENERATOR_DATA_EXCEPTION
    )

    section("Path Audit")
    path_matches = []
    for path in files:
        try:
            path_text = path.relative_to(ROOT).as_posix()
        except ValueError:
            path_text = str(path)
        if PATH_PATTERN.search(path_text):
            path_matches.append(path_text)
    if path_matches:
        print("\n".join(sorted(set(path_matches))))
        print("\nPath audit: FAIL")
        path_status = 1
    else:
        print("Path audit: PASS")
        path_status = 0

    section("Summary")
    if live_status == 0 and path_status == 0:
        print("Westernization baseline is clean outside intentional exceptions.")
        print("Intentional exceptions:")
        print(f"- append-only Liquibase history under {CHANGELOG_EXCEPTION}")
        print(f"- vendored device data under {GENERATOR_DATA_EXCEPTION}")
        print("- binary files and media/font blobs (NUL sniff + extension list)")
        print("- opentype.js LCID font-name table inside the generator bundle")
        return 0
    print("Westernization baseline still has non-exempt findings.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

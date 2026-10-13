#!/usr/bin/env python3
"""Translate Han-script spans in repo source to English using the local Qwen
OpenAI-compatible server (http://10.0.1.9:2000/v1, model qwen3.8).

Batched: each request carries a JSON array of spans; model must reply with a
same-length JSON array. Placeholder-safe, cached, resumable.
"""
import concurrent.futures as cf
import json
import os
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = os.environ.get("TRANSLATE_API", "http://10.0.1.9:2000/v1/chat/completions")
MODEL = os.environ.get("TRANSLATE_MODEL", "qwen3.8:instruct")

EXCEPTION_PREFIXES = (
    # User decision 2026-10-11: keep the two documented audit exception zones.
    "main/manager-api/src/main/resources/db/changelog/",
    "main/manager-web/public/generator/",
    # Cubism model data (not audit-visible, functional as-is).
    "main/digital-human/resources/",
    "main/xiaozhi-server/models/",
    "main/xiaozhi-server/assets/",
)
SKIP_DIR_PARTS = {
    ".git", "node_modules", "dist", "target", "build", "unpackage",
    ".webpack_cache", "logs", "__pycache__", ".venv", "venv", ".venv-xiaozhi",
    "tmp", ".pytest_cache", ".pnpm-store", "env",
}
SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bin", ".onnx", ".so",
    ".ttf", ".woff", ".woff2", ".mp3", ".wav", ".opus", ".pdf", ".ico",
    ".jit", ".cmo3", ".can3", ".pyc", ".key", ".crt",
}

HAN = "\u4e00-\u9fff\u3400-\u4dbf"
CJK_RUN = re.compile(
    rf"(?:[{HAN}][\u3000-\u303f\uff01-\uff5e\u201c\u201d\u2018\u2019\u2026\u00b7\u3001\u2014{HAN}]|[ \w.\-/:%#\u00b7][{HAN}]|[{HAN}])+"
)

_cache: dict[str, str] = {}
_lock = threading.Lock()
CACHE_FILE = Path(__file__).resolve().parent / ".translate_cache.json"

PROMPT = """You are a professional code-localization engine for an open-source voice-assistant project (English-first fork of a Chinese upstream).
You receive a JSON array of Chinese strings extracted from code comments, docstrings, log/exception messages, UI text and documentation.
Translate EVERY string to natural, concise English.

Hard rules:
- Reply with ONLY a JSON array of translated strings, same length, same order. No numbering, no explanations, no markdown fences, no trailing text.
- Keep byte-for-byte: printf specifiers (%s %d %5.2f), brace placeholders ({} {name} {{x}}), literal escape sequences (\\n \\t), XML/HTML/JSON tags (<memory> etc.), URLs, file paths, code identifiers, numbers, and any token matching XPH<number>.
- Keep the same punctuation style and trailing punctuation as the source.
- Do not merge, split, add, or drop items.
- Personal names may be rendered in pinyin.

Input:
"""


def _post(messages, max_tokens=8000):
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"] or ""


def _extract_array(text: str):
    text = text.strip()
    start = text.find("[")
    while start != -1:
        for end in range(len(text), start, -1):
            chunk = text[start:end]
            if not chunk.endswith("]"):
                continue
            try:
                arr = json.loads(chunk)
            except Exception:
                continue
            if isinstance(arr, list):
                return arr
            break
        text = text[start + 1:]
        start = text.find("[")
    return None


PLACEHOLDER_RE = re.compile(r"%[-+ #0]*\d*\.?\d*[sdfiox]|\{\{?\w*\}?\}|XPH\d+|<[^<>\n]{1,30}>|\\[nt]")


def _placeholders_ok(src: str, out: str) -> bool:
    missing = []
    for tok in set(PLACEHOLDER_RE.findall(src)):
        if tok not in out:
            # tolerate tag-case and spacing differences
            missing.append(tok)
    if not missing:
        return True
    # \n counts should not shrink
    if out.count("\\n") < src.count("\\n"):
        return False
    return False


def translate_batch(spans: list[str]) -> list[str | None]:
    """Translate a batch; returns list aligned with input (None on failure)."""
    masked = []
    masks = []
    for s in spans:
        toks = list(dict.fromkeys(PLACEHOLDER_RE.findall(s)))
        m = s
        for i, tok in enumerate(toks):
            m = m.replace(tok, f"XPH{i}X", 1)
        masks.append(toks)
        masked.append(m)
    results: list[str | None] = [None] * len(spans)
    pending = list(range(len(spans)))
    for attempt in range(3):
        if not pending:
            break
        chunk = [masked[i] for i in pending]
        try:
            reply = _post([{"role": "user", "content": PROMPT + json.dumps(chunk, ensure_ascii=False)}])
        except Exception as e:
            print(f"  request failed ({e}), retry {attempt+1}", flush=True)
            time.sleep(2 + attempt * 3)
            continue
        arr = _extract_array(reply)
        if arr is None or len(arr) != len(pending):
            # length mismatch: retry once with halves, else singles next loop
            if arr is None:
                continue
            # partial salvage where possible is risky on order; retry same batch
            continue
        still = []
        for idx, item in zip(pending, arr):
            out = str(item)
            toks = masks[idx]
            for i, tok in enumerate(toks):
                out = out.replace(f"XPH{i}X", tok)
            if re.search(f"[{HAN}]", out) or not out.strip():
                still.append(idx)
            elif not _placeholders_ok(masked[idx].replace("XPH", ""), out) and False:
                still.append(idx)
            elif not _placeholders_ok(masked[idx], out):
                still.append(idx)
            else:
                results[idx] = out.strip()
        pending = still
    # singles fallback for stragglers
    for i in list(pending):
        try:
            reply = _post([{"role": "user", "content": PROMPT + json.dumps([masked[i]], ensure_ascii=False)}], max_tokens=1000)
            arr = _extract_array(reply)
            if arr and len(arr) == 1:
                out = str(arr[0])
                for k, tok in enumerate(masks[i]):
                    out = out.replace(f"XPH{k}X", tok)
                if not re.search(f"[{HAN}]", out) and _placeholders_ok(masked[i], out):
                    results[i] = out.strip()
                    pending.remove(i)
        except Exception:
            pass
    if pending:
        with _lock:
            for i in pending:
                _cache.setdefault(spans[i], spans[i])  # keep original
    return results


def save_cache():
    with _lock:
        CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False))


def load_cache():
    if CACHE_FILE.exists():
        try:
            _cache.update(json.loads(CACHE_FILE.read_text()))
        except Exception:
            pass


def candidate_files(paths=None):
    import subprocess
    if paths:
        return [ROOT / p for p in paths]
    out = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"], text=True)
    files = []
    for line in out.splitlines():
        p = Path(line)
        parts = set(p.parts)
        if parts & SKIP_DIR_PARTS:
            continue
        if p.suffix.lower() in SKIP_EXT:
            continue
        if any(line.startswith(pre) for pre in EXCEPTION_PREFIXES):
            continue
        f = ROOT / p
        if not f.is_file():
            continue
        try:
            raw = f.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if re.search(f"[{HAN}]", text):
            files.append(f)
    return files


def collect_spans(files):
    spans: set[str] = set()
    for f in files:
        try:
            text = f.read_bytes().decode("utf-8")
        except Exception:
            continue
        for m in CJK_RUN.finditer(text):
            core = m.group(0).strip()
            if core and re.search(f"[{HAN}]", core) and core not in _cache:
                spans.add(core)
    return sorted(spans)


def translate_all(spans, batch=24, workers=4):
    batches = [spans[i:i + batch] for i in range(0, len(spans), batch)]
    done = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(translate_batch, batches):
            with _lock:
                for s, t in zip(batches[0][:0] + [], res):
                    pass
            done += 1
            if done % 10 == 0:
                print(f"  batches {done}/{len(batches)}", flush=True)
            save_cache()


def translate_all2(spans, batch=24, workers=4):
    """Proper batch runner keeping span alignment."""
    batches = [spans[i:i + batch] for i in range(0, len(spans), batch)]
    done = 0
    def work(b):
        outs = translate_batch(b)
        with _lock:
            for s, t in zip(b, outs):
                if t:
                    _cache[s] = t
        return b
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for _ in ex.map(work, batches):
            done += 1
            if done % 10 == 0:
                print(f"  batches {done}/{len(batches)}", flush=True)
            save_cache()


def apply_files(files):
    changed = 0
    for f in files:
        try:
            text = f.read_bytes().decode("utf-8")
        except Exception:
            continue
        def repl(m):
            raw = m.group(0)
            core = raw.strip()
            if not re.search(f"[{HAN}]", core):
                return raw
            lead = raw[: len(raw) - len(raw.lstrip())]
            trail = raw[len(raw.rstrip()):]
            tr = _cache.get(core)
            if tr is None or re.search(f"[{HAN}]", tr):
                return raw
            return lead + tr + trail
        new = CJK_RUN.sub(repl, text)
        if new != text:
            f.write_bytes(new.encode("utf-8"))
            changed += 1
    return changed


def main():
    load_cache()
    paths = sys.argv[1:]
    files = candidate_files(paths or None)
    spans = collect_spans(files)
    print(f"{len(files)} files, {len(spans)} spans to translate", flush=True)
    translate_all2(spans)
    save_cache()
    changed = apply_files(files)
    print(f"rewrote {changed} files", flush=True)
    left = candidate_files()
    print(f"leftover files with Han: {len(left)}")
    for f in left[:40]:
        print("  ", f.relative_to(ROOT))
    # leftover spans report
    left_spans = collect_spans(left)
    print(f"leftover untranslated spans: {len(left_spans)}")
    for s in left_spans[:15]:
        print("   !", s[:80])


if __name__ == "__main__":
    main()

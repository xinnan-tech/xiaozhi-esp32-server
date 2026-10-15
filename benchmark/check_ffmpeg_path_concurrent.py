"""PR #3442 PATH 注入并发竞态回归测试。

复现 pr02 第三轮 P1：多线程并发进出 `ffmpeg_path_override()`，验证
finally 退出后 `os.environ["PATH"]` 必等于调用前的原始值，不留 bin 前缀。

Usage:
    python benchmark/check_ffmpeg_path_concurrent.py
"""

from __future__ import annotations

import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(REPO, "main", "xiaozhi-server")
if SERVER not in sys.path:
    sys.path.insert(0, SERVER)

from core.utils.util import ffmpeg_path_override  # noqa: E402

THREADS = 16
ROUNDS = 200


def _worker(_idx: int) -> str:
    with ffmpeg_path_override():
        time.sleep(0.001)
        return os.environ.get("PATH", "")


def main() -> int:
    original = os.environ.get("PATH", "")
    print(f"original PATH first 60: {original[:60]!r}")
    if "miniconda3" not in original and "anaconda3" not in original:
        print(
            "SKIP: 当前 PATH 不含 conda 前缀，本测试设计为 conda env 场景。"
        )
        return 0

    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        for _ in range(ROUNDS):
            list(pool.map(_worker, range(THREADS)))

    final = os.environ.get("PATH", "")
    if final != original:
        print(f"FAIL: PATH 残留 original={original[:60]!r} final={final[:60]!r}")
        return 1

    print(
        f"OK: {THREADS} thread × {ROUNDS} round = {THREADS * ROUNDS} 次进出，"
        f"finally 后 PATH 等于原始值"
    )
    return 0


def test_no_residue_after_concurrent():
    """pytest 形式：PATH 必须等于原始值。"""
    original = os.environ.get("PATH", "")
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        for _ in range(ROUNDS):
            list(pool.map(_worker, range(THREADS)))
    assert os.environ.get("PATH", "") == original, (
        f"PATH 残留: original={original!r} final={os.environ.get('PATH', '')!r}"
    )


def test_env_opt_out():
    original = os.environ.get("PATH", "")
    os.environ["XIAOZHI_PYDUB_OVERRIDE_FFMPEG"] = "0"
    try:
        with ffmpeg_path_override():
            assert os.environ.get("PATH", "") == original
    finally:
        del os.environ["XIAOZHI_PYDUB_OVERRIDE_FFMPEG"]


def test_nested_no_residue():
    original = os.environ.get("PATH", "")
    with ffmpeg_path_override():
        with ffmpeg_path_override():
            inner = os.environ.get("PATH", "")
            assert "miniconda3" in inner or "anaconda3" in inner
    assert os.environ.get("PATH", "") == original


if __name__ == "__main__":
    sys.exit(main())

"""Smoke test — confirms pytest can collect from this directory.

Real tests land in Slice 2 (see docs/superpowers/specs/2026-09-02-test-infrastructure-design.md).
"""


def test_pytest_works():
    assert 1 + 1 == 2


def test_repo_path_is_writable(tmp_path):
    p = tmp_path / "scratch.txt"
    p.write_text("ok", encoding="utf-8")
    assert p.read_text(encoding="utf-8") == "ok"

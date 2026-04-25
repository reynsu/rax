"""Regression tests for v2.0 review security findings.

Each test pins a specific finding from the post-v2.0 review so a future
refactor can't quietly reintroduce the issue.
"""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------- M-4: judge_panel cache path traversal ----------


def test_cache_key_rejects_path_traversal():
    """Model name with `..` or `/` must not produce a valid cache path."""
    from scripts.judge_panel import _cache_key

    with pytest.raises(ValueError):
        _cache_key("../etc/cron.d/x", "prompt")
    with pytest.raises(ValueError):
        _cache_key("foo/bar", "prompt")
    with pytest.raises(ValueError):
        _cache_key("", "prompt")


def test_cache_key_accepts_normal_model_names():
    from scripts.judge_panel import _cache_key

    p = _cache_key("claude-opus-4-7", "prompt")
    assert "claude-opus-4-7" in str(p)


def test_cache_put_writes_with_restrictive_mode(tmp_path, monkeypatch):
    """Cache files should be created with mode 0o600 (no group/other read)."""
    import os

    import scripts.judge_panel as jp

    monkeypatch.setattr(jp, "CACHE_DIR", tmp_path / "cache")
    jp._cache_put("claude-opus", "abc", {"x": 1})

    cache_files = list((tmp_path / "cache").rglob("*.json"))
    assert cache_files, "cache file should have been created"
    mode = os.stat(cache_files[0]).st_mode & 0o777
    assert mode == 0o600, f"cache file mode should be 0o600, got {oct(mode)}"


# ---------- M-5: mine_corpus owner/repo validation ----------


def test_mine_corpus_validates_slug_shape():
    from scripts.mine_corpus import _validate_slug

    assert _validate_slug("facebook/react") == ("facebook", "react")
    assert _validate_slug("a/b") == ("a", "b")


def test_mine_corpus_rejects_traversal_in_repo():
    from scripts.mine_corpus import _validate_slug

    with pytest.raises(ValueError):
        _validate_slug("facebook/../../../etc/cron.d/rax")
    with pytest.raises(ValueError):
        _validate_slug("../etc/foo")
    with pytest.raises(ValueError):
        _validate_slug("foo")  # no slash
    with pytest.raises(ValueError):
        _validate_slug("foo/bar/baz")  # extra slash → name has slash


# ---------- M-2: telemetry endpoint validation ----------


def test_telemetry_rejects_non_https():
    from scripts.telemetry import _validate_endpoint

    with pytest.raises(ValueError):
        _validate_endpoint("http://example.com/rax")
    with pytest.raises(ValueError):
        _validate_endpoint("file:///etc/passwd")


def test_telemetry_rejects_private_ip():
    from scripts.telemetry import _validate_endpoint

    with pytest.raises(ValueError):
        _validate_endpoint("https://192.168.1.1/rax")
    with pytest.raises(ValueError):
        _validate_endpoint("https://127.0.0.1/rax")
    with pytest.raises(ValueError):
        _validate_endpoint("https://10.0.0.5/rax")


def test_telemetry_accepts_public_https_url():
    from scripts.telemetry import _validate_endpoint

    assert _validate_endpoint("https://api.example.com/rax/telemetry")


def test_telemetry_allow_private_overrides():
    from scripts.telemetry import _validate_endpoint

    assert _validate_endpoint("https://192.168.1.1/rax", allow_private=True)


# ---------- L-1: parse_deterministic size cap ----------


def test_parse_deterministic_skips_oversized_files(tmp_path, monkeypatch):
    import scripts.parse_deterministic as pd

    big = tmp_path / "huge.json"
    monkeypatch.setattr(pd, "_MAX_TOOL_OUTPUT_BYTES", 100)
    big.write_text("a" * 200)
    assert pd._read_json(str(big)) is None


def test_parse_deterministic_reads_normal_size_json(tmp_path):
    import json

    import scripts.parse_deterministic as pd

    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"hello": "world"}))
    assert pd._read_json(str(p)) == {"hello": "world"}

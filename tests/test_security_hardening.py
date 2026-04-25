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


# ---------- regression: rax custom rules' metadata.iso_sub_id is honored ----------


def test_parse_semgrep_uses_metadata_iso_sub_id(tmp_path):
    """When a rule's check_id is `references.rules.rax.<x>` and the regex-
    based mapper has no entry for that pattern, the parser previously fell
    back to TOOL_DEFAULT_ISO['semgrep'] = 'ISO_SEC_INT', mis-bucketing
    accessibility / perf / reliability findings as security. The parser
    must prefer `extra.metadata.iso_sub_id` declared in the rule YAML.
    """
    import json

    import scripts.parse_deterministic as pd

    semgrep_out = tmp_path / "semgrep.json"
    semgrep_out.write_text(json.dumps({"results": [
        # rax custom rule — has metadata.iso_sub_id, mapper has no regex match.
        {
            "check_id": "references.rules.rax.a11y.touchable-without-a11y",
            "path": "src/Foo.tsx",
            "start": {"line": 12},
            "extra": {
                "severity": "ERROR",
                "message": "missing accessibilityLabel",
                "metadata": {"iso_sub_id": "ISO_INTER_INC"},
            },
        },
        # OSS-style rule — no metadata.iso_sub_id; mapper handles via regex.
        {
            "check_id": "react-hooks/exhaustive-deps",
            "path": "src/Bar.tsx",
            "start": {"line": 7},
            "extra": {"severity": "WARNING", "message": "missing dep"},
        },
    ]}))

    findings = pd.parse_semgrep(str(semgrep_out))
    by_id = {f["rule_id"]: f["iso_sub_id"] for f in findings}

    # Custom rule lands in the metadata-declared bucket, NOT the SEC_INT default.
    assert by_id["references.rules.rax.a11y.touchable-without-a11y"] == "ISO_INTER_INC"
    # OSS rule continues to use the regex mapper.
    assert by_id["react-hooks/exhaustive-deps"] == "ISO_REL_FAULT"


def test_parse_semgrep_ignores_invalid_metadata_iso_sub_id(tmp_path):
    """If metadata.iso_sub_id is malformed (not a string starting with
    'ISO_'), fall back to the regex mapper instead of trusting it."""
    import json

    import scripts.parse_deterministic as pd

    semgrep_out = tmp_path / "semgrep.json"
    semgrep_out.write_text(json.dumps({"results": [
        {
            "check_id": "react-hooks/rules-of-hooks",
            "path": "x.tsx",
            "start": {"line": 1},
            "extra": {
                "severity": "ERROR",
                "metadata": {"iso_sub_id": "garbage"},
            },
        },
    ]}))
    findings = pd.parse_semgrep(str(semgrep_out))
    assert findings[0]["iso_sub_id"] == "ISO_REL_FAULT"


def test_parse_semgrep_survives_non_dict_metadata(tmp_path):
    """Third-party rule packs sometimes emit `metadata` as a non-dict.
    The parser must not crash with AttributeError."""
    import json

    import scripts.parse_deterministic as pd

    semgrep_out = tmp_path / "semgrep.json"
    semgrep_out.write_text(json.dumps({"results": [
        {
            "check_id": "third-party.rule",
            "path": "x.tsx",
            "start": {"line": 1},
            "extra": {"severity": "ERROR", "metadata": "not-a-dict"},
        },
        {
            "check_id": "another.rule",
            "path": "x.tsx",
            "start": {"line": 2},
            "extra": {"severity": "WARNING", "metadata": ["array", "form"]},
        },
        {
            "check_id": "third.rule",
            "path": "x.tsx",
            "start": {"line": 3},
            "extra": {"severity": "INFO", "metadata": 42},
        },
    ]}))
    # Must not raise.
    findings = pd.parse_semgrep(str(semgrep_out))
    assert len(findings) == 3
    for f in findings:
        assert f["iso_sub_id"].startswith("ISO_")


def test_parse_semgrep_survives_dict_fix_field(tmp_path):
    """Semgrep extended output can ship `extra.fix` as a dict.
    Slicing a dict raises TypeError; coerce to "" instead."""
    import json

    import scripts.parse_deterministic as pd

    semgrep_out = tmp_path / "semgrep.json"
    semgrep_out.write_text(json.dumps({"results": [
        {
            "check_id": "rule.with.dict.fix",
            "path": "x.tsx",
            "start": {"line": 1},
            "extra": {
                "severity": "ERROR",
                "fix": {"message": "rewrite this", "lines": [1, 2, 3]},
            },
        },
        {
            "check_id": "rule.with.string.fix",
            "path": "x.tsx",
            "start": {"line": 2},
            "extra": {"severity": "WARNING", "fix": "use Foo.bar()"},
        },
    ]}))
    findings = pd.parse_semgrep(str(semgrep_out))
    assert len(findings) == 2
    # Dict fix → empty string (not crash, not str(dict)).
    assert findings[0]["fix_hint"] == ""
    # String fix → preserved.
    assert findings[1]["fix_hint"] == "use Foo.bar()"

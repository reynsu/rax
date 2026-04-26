"""Tests for scripts/secret_scrub.py — best-effort secret redaction."""
from __future__ import annotations

from scripts.secret_scrub import REPLACEMENT, scrub


def test_scrubs_anthropic_key():
    text = "401 Unauthorized: invalid key sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAA"
    out = scrub(text)
    assert REPLACEMENT in out
    assert "sk-ant-api03-AAAAAAAAAA" not in out


def test_scrubs_openai_legacy_key():
    out = scrub("invalid Bearer sk-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789")
    assert REPLACEMENT in out
    assert "sk-AbCdEf" not in out


def test_scrubs_openai_project_key():
    out = scrub("error key=sk-proj-XXXXXXXXXXXXXXXXXXXXXX")
    assert REPLACEMENT in out


def test_scrubs_google_api_key():
    out = scrub("Permission denied for AIzaXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    assert REPLACEMENT in out


def test_scrubs_github_pat():
    out = scrub("auth ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa expired")
    assert REPLACEMENT in out


def test_scrubs_bearer_header():
    out = scrub("Authorization: Bearer abcdef0123456789abcdef0123456789")
    assert REPLACEMENT in out


def test_handles_empty_or_clean_strings():
    assert scrub("") == ""
    assert scrub("connection reset by peer") == "connection reset by peer"


def test_does_not_overmatch_short_tokens():
    """sk- followed by <20 chars should NOT match (would be too aggressive)."""
    out = scrub("see sk-12 in docs")
    assert REPLACEMENT not in out

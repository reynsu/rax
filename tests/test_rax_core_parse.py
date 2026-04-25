"""parse_report supports both v1 and v2 report formats.

The v1 path is preserved for backward compat (`rax show <old-id>` from a
pre-v2 install). The v2 path extracts intervals + ISO category names so
delta queries against a v2 baseline don't need a separate code path.
"""
from __future__ import annotations

import pytest

from scripts.rax_core import parse_report


# ---------------- v1 (legacy) ----------------

V1_REPORT = """\
# rax audit — 2026-04-25 · abc1234 · main

- **Mode:** diff
- **Commit:** abc1234
- **Branch:** main

## Overall: 7.0/10  ▼ -0.3 vs baseline (7.3)

| Category                     | Weight | Score    | Δ      |
|------------------------------|--------|----------|--------|
| ARC | 12 | 7.0/10 | -0.2 |
| SEC | 13 | 6.5/10 | -0.5 |

### C1. [SEC] Hardcoded API key
- **Where:** src/config/api.ts:12
- **Severity:** high
- **Fix:** Move to env var.
"""


def test_v1_overall_parsed():
    r = parse_report(V1_REPORT)
    assert r["version"] == "v1"
    assert r["overall"] == 7.0
    assert r["interval"] is None


def test_v1_categories_parsed():
    r = parse_report(V1_REPORT)
    assert r["categories"]["ARC"] == 7.0
    assert r["categories"]["SEC"] == 6.5


def test_v1_findings_parsed():
    r = parse_report(V1_REPORT)
    assert len(r["findings"]) == 1
    f = r["findings"][0]
    assert f["category"] == "SEC"
    assert f["severity"] == "high"
    assert "src/config/api.ts:12" in f["where"]


# ---------------- v2 ----------------

V2_REPORT = """\
# rax audit — 2026-04-25 · abc1234 · v2.0

**Profile:** consumer-app
**Mode:** full
**Rubric:** rax-v2.0.0
- **Commit:** abc1234
- **Branch:** v2.0

## Overall: [6.4, 8.1]/10  (90% CI, median 7.3)

| ISO Characteristic       | CI 90%       | Median | Confidence | Δ vs baseline |
|--------------------------|--------------|--------|------------|---------------|
| Security                 | [3.5, 5.0]   | 4.2    | high       | -0.4          |
| Maintainability          | [5.0, 7.5]   | 6.2    | medium     | +0.1          |
| Reliability              | ABSTAINED    | —      | low        | —             |

### 1. [SEC/Confidentiality] Hardcoded production secret
- **Where:** src/config/api.ts:12
- **Severity:** high
- **Fix:** Move to env var loaded at runtime; rotate the leaked key.

### 2. [MAINT/Modularity] Cross-feature import bypasses public API
- **Where:** src/features/checkout/CheckoutScreen.tsx:142
- **Severity:** medium
- **Fix:** Add public re-export.
"""


def test_v2_detected_by_interval_format():
    r = parse_report(V2_REPORT)
    assert r["version"] == "v2"
    assert r["overall"] == 7.3
    assert r["interval"] == [6.4, 8.1]


def test_v2_category_intervals_parsed():
    r = parse_report(V2_REPORT)
    assert r["category_intervals"]["Security"] == [3.5, 5.0]
    assert r["category_intervals"]["Maintainability"] == [5.0, 7.5]
    # Reliability is ABSTAINED — no interval, but row consumed without crashing.
    assert "Reliability" not in r["category_intervals"]


def test_v2_category_medians_parsed():
    r = parse_report(V2_REPORT)
    assert r["categories"]["Security"] == 4.2
    assert r["categories"]["Maintainability"] == 6.2
    # ABSTAINED rows are excluded from both `categories` and
    # `category_intervals` — the Overall aggregator depends on it.
    assert "Reliability" not in r["categories"]
    assert "Reliability" not in r["category_intervals"]


def test_v2_overall_without_median_derives_midpoint():
    """Claude sometimes omits or wraps the `median <X>` annotation.
    parse_report must derive (lo + hi) / 2 rather than raise."""
    md = """\
# rax audit

## Overall: [6.0, 8.0]/10

| ISO Characteristic | CI 90%      | Median | Confidence |
|--------------------|-------------|--------|------------|
| Security           | [5.0, 7.0]  | 6.0    | high       |
"""
    r = parse_report(md)
    assert r["version"] == "v2"
    assert r["interval"] == [6.0, 8.0]
    assert r["overall"] == 7.0  # midpoint derived


def test_v2_overall_with_wrapped_median_still_parses():
    """Median on a different line from the bracket — still resolved
    via the secondary regex search over the trailing context."""
    md = """\
# rax audit

## Overall: [6.4, 8.1]/10
  (90% CI, median 7.3)

| ISO Characteristic | CI 90%       | Median | Confidence |
|--------------------|--------------|--------|------------|
| Security           | [3.5, 5.0]   | 4.2    | high       |
"""
    r = parse_report(md)
    assert r["interval"] == [6.4, 8.1]
    assert r["overall"] == 7.3


def test_v2_findings_parsed_with_iso_subchars():
    r = parse_report(V2_REPORT)
    assert len(r["findings"]) == 2
    assert r["findings"][0]["category"] == "SEC"
    assert r["findings"][0]["category_full"] == "SEC/Confidentiality"
    assert r["findings"][0]["severity"] == "high"
    assert r["findings"][1]["category"] == "MAINT"
    assert r["findings"][1]["category_full"] == "MAINT/Modularity"


def test_v2_metadata_parsed():
    r = parse_report(V2_REPORT)
    assert r["profile"] == "consumer-app"
    assert r["rubric"] == "rax-v2.0.0"
    assert r["mode"] == "full"
    assert r["commit"] == "abc1234"


def test_invalid_input_raises():
    with pytest.raises(ValueError):
        parse_report("This is not a rax report.")

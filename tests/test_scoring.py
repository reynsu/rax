"""Tests for scripts/scoring.py — hybrid deterministic + LLM scoring."""
from __future__ import annotations

import pytest

from scripts.scoring import (
    DEFAULT_SEVERITY_WEIGHTS,
    NO_FINDINGS_CEILING,
    HybridScore,
    combine_scores,
    deterministic_score_from_findings,
    score_all_subcharacteristics,
    score_subcharacteristic,
)


# ---------------- combine_scores ----------------


def test_combine_alpha_zero_gives_pure_llm():
    assert combine_scores(2.0, 8.0, 0.0) == pytest.approx(8.0, abs=1e-9)


def test_combine_alpha_one_gives_pure_deterministic():
    assert combine_scores(2.0, 8.0, 1.0) == pytest.approx(2.0, abs=1e-9)


def test_combine_intermediate_alpha():
    # 0.7 * 4 + 0.3 * 8 = 2.8 + 2.4 = 5.2
    assert combine_scores(4.0, 8.0, 0.7) == pytest.approx(5.2, abs=1e-9)


def test_combine_no_llm_returns_deterministic():
    """LLM None falls back to det_score regardless of alpha."""
    assert combine_scores(6.5, None, 0.3) == pytest.approx(6.5, abs=1e-9)
    assert combine_scores(6.5, None, 1.0) == pytest.approx(6.5, abs=1e-9)


def test_combine_invalid_alpha_raises():
    with pytest.raises(ValueError):
        combine_scores(5.0, 5.0, -0.1)
    with pytest.raises(ValueError):
        combine_scores(5.0, 5.0, 1.1)


def test_combine_invalid_scores_raise():
    with pytest.raises(ValueError):
        combine_scores(11.0, 5.0, 0.5)
    with pytest.raises(ValueError):
        combine_scores(5.0, -1.0, 0.5)


# ---------------- deterministic_score_from_findings ----------------


def test_no_findings_ceiling_is_nine():
    assert deterministic_score_from_findings([]) == NO_FINDINGS_CEILING


def test_single_low_severity_drops_minimally():
    """A single low-severity finding subtracts 0.3 from the 10 ceiling."""
    score = deterministic_score_from_findings([{"severity": "low"}])
    assert score == pytest.approx(9.7, abs=1e-2)


def test_single_high_severity_lowers_meaningfully():
    score = deterministic_score_from_findings([{"severity": "high"}])
    # 10 - 1.5 = 8.5
    assert score == pytest.approx(8.5, abs=1e-2)


def test_multiple_high_drops_score():
    score = deterministic_score_from_findings([{"severity": "high"}] * 5)
    # 10 - 7.5 = 2.5
    assert score == pytest.approx(2.5, abs=1e-2)


def test_score_clamped_to_floor():
    """Many findings can't push below SCORE_FLOOR (1.0)."""
    score = deterministic_score_from_findings([{"severity": "high"}] * 100)
    assert score == 1.0


def test_unknown_severity_treated_as_medium():
    score = deterministic_score_from_findings([{"severity": "????"}])
    # falls back to medium = 0.7 -> 9.3
    assert score == pytest.approx(9.3, abs=1e-2)


def test_custom_severity_weights():
    score = deterministic_score_from_findings(
        [{"severity": "high"}],
        severity_weights={"high": 0.1, "medium": 0.05, "low": 0.0},
    )
    assert score == pytest.approx(9.9, abs=1e-2)


# ---------------- score_subcharacteristic ----------------


def test_score_subchar_uses_default_alpha_from_coverage_table():
    """ISO_SEC_CONF α is 0.85 in the coverage table; SEC_CONF override
    in scale-mapping.yaml maps 4 -> 9.0 (not the linear 10)."""
    res = score_subcharacteristic(
        "ISO_SEC_CONF",
        det_findings=[{"severity": "high"}],
        llm_audit={"score_1_to_4": 4},  # SEC_CONF override -> 9.0
    )
    # det = 8.5, llm = 9.0, alpha = 0.85
    # final = 0.85 * 8.5 + 0.15 * 9.0 = 7.225 + 1.35 = 8.575
    assert res.alpha == pytest.approx(0.85, abs=1e-9)
    assert res.deterministic == pytest.approx(8.5, abs=1e-2)
    assert res.llm == pytest.approx(9.0, abs=1e-2)
    assert res.final == pytest.approx(8.58, abs=1e-2)
    assert res.confidence == "high"
    assert res.used_llm is True
    assert res.deterministic_finding_count == 1


def test_score_subchar_unknown_id_defaults_alpha_zero():
    """Unknown sub-id defaults alpha=0 -> all weight on LLM."""
    res = score_subcharacteristic(
        "ISO_NEW_SUBCHAR_NOT_IN_TABLE",
        det_findings=[],
        llm_audit={"score": 6.5},
    )
    assert res.alpha == 0.0
    assert res.final == pytest.approx(6.5, abs=1e-2)
    assert res.confidence == "low"


def test_score_subchar_alpha_override():
    res = score_subcharacteristic(
        "ISO_SEC_CONF",
        det_findings=[{"severity": "high"}],
        llm_audit={"score": 5.0},
        alpha=0.5,
    )
    # det = 8.5, llm = 5.0, alpha override = 0.5 -> 6.75
    assert res.alpha == 0.5
    assert res.final == pytest.approx(6.75, abs=1e-2)


def test_score_subchar_no_llm_returns_pure_deterministic():
    res = score_subcharacteristic(
        "ISO_SEC_CONF",
        det_findings=[{"severity": "low"}],
    )
    # det = 9.7, llm = None -> final = 9.7
    assert res.llm is None
    assert res.final == pytest.approx(9.7, abs=1e-2)
    assert res.used_llm is False


# ---------------- _extract_llm_score (via score_subcharacteristic) ----------------


def test_score_1_to_4_default_mapping():
    """Default (no override): 1 -> 2.5, 2 -> 5.0, 3 -> 7.5, 4 -> 10.0.
    Use ISO_MAINT_MOD which has no override in scale-mapping.yaml."""
    for raw, expected in [(1, 2.5), (2, 5.0), (3, 7.5), (4, 10.0)]:
        res = score_subcharacteristic(
            "ISO_MAINT_MOD",
            det_findings=[],
            llm_audit={"score_1_to_4": raw},
            alpha=0.0,
        )
        assert res.llm == pytest.approx(expected, abs=1e-9)
        assert res.final == pytest.approx(expected, abs=1e-9)


def test_score_1_to_4_iso_sec_conf_override():
    """ISO_SEC_CONF override: 1 -> 1.0, 2 -> 4.0, 3 -> 7.0, 4 -> 9.0.
    Hardcoded production secret really is a 1, not a 2.5."""
    for raw, expected in [(1, 1.0), (2, 4.0), (3, 7.0), (4, 9.0)]:
        res = score_subcharacteristic(
            "ISO_SEC_CONF",
            det_findings=[],
            llm_audit={"score_1_to_4": raw},
            alpha=0.0,
        )
        assert res.llm == pytest.approx(expected, abs=1e-9)


def test_invalid_score_1_to_4_raises():
    with pytest.raises(ValueError):
        score_subcharacteristic(
            "ISO_SEC_CONF",
            llm_audit={"score_1_to_4": 0},
        )
    with pytest.raises(ValueError):
        score_subcharacteristic(
            "ISO_SEC_CONF",
            llm_audit={"score_1_to_4": 5},
        )


def test_invalid_score_raises():
    with pytest.raises(ValueError):
        score_subcharacteristic(
            "ISO_SEC_CONF",
            llm_audit={"score": 11},
        )


def test_llm_audit_without_score_treated_as_none():
    res = score_subcharacteristic(
        "ISO_SEC_CONF",
        det_findings=[],
        llm_audit={"justification": "looks fine"},  # no score field
    )
    assert res.llm is None
    assert res.used_llm is False


# ---------------- score_all_subcharacteristics ----------------


def test_bulk_scoring_with_full_payload():
    payload = {
        "by_iso_subcharacteristic": {
            "ISO_SEC_CONF": {"findings": [{"severity": "high"}]},
            "ISO_MAINT_MOD": {"findings": []},
        }
    }
    audits = {
        "ISO_SEC_CONF": {"score_1_to_4": 3},   # SEC_CONF override -> 7.0
        # ISO_MAINT_MOD has no llm audit
    }
    out = score_all_subcharacteristics(payload, audits)

    assert set(out.keys()) == {"ISO_SEC_CONF", "ISO_MAINT_MOD"}

    sec = out["ISO_SEC_CONF"]
    # det 8.5, llm 7.0 (SEC_CONF override), α 0.85
    # final = 0.85*8.5 + 0.15*7.0 = 7.225 + 1.05 = 8.275
    assert sec.final == pytest.approx(8.28, abs=1e-2)
    assert sec.used_llm is True

    mnt = out["ISO_MAINT_MOD"]
    # no findings -> det 9.0; no llm -> final 9.0
    assert mnt.final == pytest.approx(9.0, abs=1e-2)
    assert mnt.used_llm is False


def test_bulk_scoring_accepts_inner_mapping():
    inner = {
        "ISO_SEC_CONF": {"findings": []},
    }
    out = score_all_subcharacteristics(inner)
    assert "ISO_SEC_CONF" in out


def test_bulk_scoring_alpha_overrides_apply():
    payload = {
        "by_iso_subcharacteristic": {
            "ISO_SEC_CONF": {"findings": [{"severity": "high"}]},
        }
    }
    audits = {"ISO_SEC_CONF": {"score": 0.0}}
    out = score_all_subcharacteristics(
        payload, audits, alpha_overrides={"ISO_SEC_CONF": 0.0}
    )
    # alpha=0 -> pure llm = 0
    assert out["ISO_SEC_CONF"].final == 0.0
    assert out["ISO_SEC_CONF"].alpha == 0.0


# ---------------- HybridScore dataclass ----------------


def test_hybrid_score_is_immutable():
    h = HybridScore(
        iso_sub_id="ISO_X", final=5.0, deterministic=5.0, llm=None,
        alpha=0.5, confidence="medium", deterministic_finding_count=0,
        used_llm=False,
    )
    with pytest.raises((AttributeError, TypeError)):
        h.final = 9.0  # type: ignore[misc]

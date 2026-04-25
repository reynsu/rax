"""Hybrid deterministic + LLM scoring per ISO 25010 sub-characteristic.

Final score per sub-char:

    final = α · deterministic + (1 - α) · llm

    α  is the per-sub-char "deterministic coverage" from
    `references/deterministic-coverage.md` (also embedded in
    `scripts/parse_deterministic.py:COVERAGE_ALPHA`).

The deterministic side comes from `scripts/parse_deterministic.py`. The LLM
side comes from a JSON object emitted by the audit prompt in Phase 4 — for
this phase we only need the data path; the LLM output is mocked in tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from scripts.parse_deterministic import (
    COVERAGE_ALPHA,
    SCORE_CEILING,
    SCORE_FLOOR,
    SEVERITY_PENALTY,
)


# Default severity weights — same shape as parse_deterministic but
# overridable here so callers can experiment without editing both files.
DEFAULT_SEVERITY_WEIGHTS = dict(SEVERITY_PENALTY)
NO_FINDINGS_CEILING = 9.0  # 10 only allowed when LLM also confirms


ABSTAIN_INTERVAL_THRESHOLD = 3.0  # if interval width > 3 points -> abstain


@dataclass(frozen=True)
class HybridScore:
    """Result of combining deterministic + LLM for one sub-characteristic.

    Optional `interval` (lo, hi) is set when a conformal layer wraps the
    point estimate. `abstained` is True when the interval is wider than
    `ABSTAIN_INTERVAL_THRESHOLD` — the report should show 'ABSTAINED'
    instead of the point estimate.
    """
    iso_sub_id: str
    final: float
    deterministic: float
    llm: Optional[float]
    alpha: float
    confidence: str
    deterministic_finding_count: int
    used_llm: bool
    interval: Optional["tuple[float, float]"] = None
    abstained: bool = False


def attach_interval(score: HybridScore, lo: float, hi: float) -> HybridScore:
    """Return a new HybridScore with the given conformal interval attached.

    If width > ABSTAIN_INTERVAL_THRESHOLD, mark abstained.
    """
    width = max(0.0, hi - lo)
    return HybridScore(
        iso_sub_id=score.iso_sub_id,
        final=score.final,
        deterministic=score.deterministic,
        llm=score.llm,
        alpha=score.alpha,
        confidence=score.confidence,
        deterministic_finding_count=score.deterministic_finding_count,
        used_llm=score.used_llm,
        interval=(round(lo, 2), round(hi, 2)),
        abstained=width > ABSTAIN_INTERVAL_THRESHOLD,
    )


def combine_scores(
    det_score: float,
    llm_score: Optional[float],
    alpha: float,
) -> float:
    """Linear blend of deterministic and LLM scores.

    Args:
        det_score: deterministic score in [0, 10].
        llm_score: LLM score in [0, 10], or None if no LLM input is available.
        alpha:     weight for the deterministic side, in [0, 1].

    If `llm_score is None`, the function falls back to det_score regardless
    of alpha — better than blending with a guess. Callers should explicitly
    pass an LLM score even if they have to default it to det_score.

    Returns:
        final score in [0, 10].
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")
    if not (0.0 <= det_score <= 10.0):
        raise ValueError(f"det_score must be in [0, 10], got {det_score}")

    if llm_score is None:
        return float(det_score)

    if not (0.0 <= llm_score <= 10.0):
        raise ValueError(f"llm_score must be in [0, 10], got {llm_score}")

    blended = alpha * det_score + (1.0 - alpha) * llm_score
    return float(max(0.0, min(10.0, blended)))


def deterministic_score_from_findings(
    findings: Iterable[Dict[str, Any]],
    severity_weights: Optional[Dict[str, float]] = None,
    no_findings_ceiling: float = NO_FINDINGS_CEILING,
) -> float:
    """Convert a list of findings to a deterministic score in [1, 10].

    Defaults follow the plan:
      - 0 findings -> 9 (cannot be 10 without LLM confirmation).
      - high penalty 1.5, medium 0.7, low 0.3.
      - clamped to [SCORE_FLOOR, SCORE_CEILING].

    Tunable via `severity_weights`.
    """
    weights = dict(severity_weights or DEFAULT_SEVERITY_WEIGHTS)
    findings = list(findings)
    if not findings:
        return float(no_findings_ceiling)

    penalty = 0.0
    for f in findings:
        sev = (f.get("severity") or "medium").lower()
        penalty += weights.get(sev, weights.get("medium", 0.7))

    score = SCORE_CEILING - penalty
    return float(max(SCORE_FLOOR, min(SCORE_CEILING, round(score, 2))))


def _confidence_from_alpha(alpha: float) -> str:
    if alpha >= 0.7:
        return "high"
    if alpha >= 0.4:
        return "medium"
    return "low"


def score_subcharacteristic(
    iso_sub_id: str,
    det_findings: Optional[List[Dict[str, Any]]] = None,
    llm_audit: Optional[Dict[str, Any]] = None,
    alpha: Optional[float] = None,
    severity_weights: Optional[Dict[str, float]] = None,
) -> HybridScore:
    """Score one sub-characteristic using deterministic findings + LLM audit.

    Args:
        iso_sub_id: e.g. "ISO_SEC_CONF". Used to look up α in COVERAGE_ALPHA.
        det_findings: list of finding dicts from parse_deterministic.
        llm_audit: dict with at least {"score_1_to_4": int} or
            {"score": float in [0,10]}. None means LLM did not opine.
        alpha: override the default α for this sub-char.
        severity_weights: override the default severity weights.

    Returns:
        HybridScore.
    """
    alpha = COVERAGE_ALPHA.get(iso_sub_id, 0.0) if alpha is None else alpha
    findings = list(det_findings or [])
    det_score = deterministic_score_from_findings(findings, severity_weights)

    llm_score = _extract_llm_score(llm_audit, sub_id=iso_sub_id)
    used_llm = llm_score is not None

    final = combine_scores(det_score, llm_score, alpha)

    return HybridScore(
        iso_sub_id=iso_sub_id,
        final=round(final, 2),
        deterministic=round(det_score, 2),
        llm=None if llm_score is None else round(llm_score, 2),
        alpha=alpha,
        confidence=_confidence_from_alpha(alpha),
        deterministic_finding_count=len(findings),
        used_llm=used_llm,
    )


_SCALE_MAPPING_CACHE: Optional[Dict[str, Any]] = None


def _load_scale_mapping() -> Dict[str, Any]:
    """Load `references/scale-mapping.yaml` once. If absent or unreadable,
    return the linear `n * 2.5` default so callers always have a mapping."""
    global _SCALE_MAPPING_CACHE
    if _SCALE_MAPPING_CACHE is not None:
        return _SCALE_MAPPING_CACHE

    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "references" / "scale-mapping.yaml"
    fallback = {
        "default": {"1": 2.5, "2": 5.0, "3": 7.5, "4": 10.0},
        "overrides": {},
    }
    if not path.exists():
        _SCALE_MAPPING_CACHE = fallback
        return _SCALE_MAPPING_CACHE
    try:
        import yaml  # type: ignore[import-untyped]
        loaded = yaml.safe_load(path.read_text()) or {}
        if not isinstance(loaded, dict):
            _SCALE_MAPPING_CACHE = fallback
        else:
            loaded.setdefault("default", fallback["default"])
            loaded.setdefault("overrides", {})
            _SCALE_MAPPING_CACHE = loaded
    except Exception:
        _SCALE_MAPPING_CACHE = fallback
    return _SCALE_MAPPING_CACHE


def _scale_to_ten(raw: float, sub_id: Optional[str] = None) -> float:
    """Map a 1-4 internal score to the 1-10 user-visible scale, honoring
    `references/scale-mapping.yaml` overrides per sub-characteristic.

    Linearly interpolates between the four anchor points; values outside
    [1, 4] are clamped before mapping.
    """
    raw = max(1.0, min(4.0, float(raw)))
    cfg = _load_scale_mapping()
    table = cfg["default"]
    if sub_id and sub_id in (cfg.get("overrides") or {}):
        table = cfg["overrides"][sub_id]

    anchors = {int(k): float(v) for k, v in table.items()}
    if not anchors:
        return raw * 2.5

    if raw <= min(anchors):
        return anchors[min(anchors)]
    if raw >= max(anchors):
        return anchors[max(anchors)]
    # linear interp between bracket anchors
    floor = max(k for k in anchors if k <= raw)
    ceil = min(k for k in anchors if k >= raw)
    if floor == ceil:
        return anchors[floor]
    span = ceil - floor
    t = (raw - floor) / span
    return anchors[floor] + t * (anchors[ceil] - anchors[floor])


def _extract_llm_score(
    llm_audit: Optional[Dict[str, Any]],
    sub_id: Optional[str] = None,
) -> Optional[float]:
    """Map LLM audit output to a [0, 10] score.

    Accepts either:
      - {"score_1_to_4": <int 1..4>}  — the rubric-v2 internal scale.
        Mapped via `references/scale-mapping.yaml` (per-sub-char-aware).
      - {"score": <number in [0, 10]>}.
      - None.
    """
    if llm_audit is None:
        return None

    if "score_1_to_4" in llm_audit:
        raw = llm_audit["score_1_to_4"]
        if not isinstance(raw, (int, float)) or not (1 <= raw <= 4):
            raise ValueError(f"score_1_to_4 must be in [1, 4], got {raw}")
        return _scale_to_ten(float(raw), sub_id)

    if "score" in llm_audit:
        raw = llm_audit["score"]
        if not isinstance(raw, (int, float)) or not (0.0 <= raw <= 10.0):
            raise ValueError(f"score must be in [0, 10], got {raw}")
        return float(raw)

    return None


def score_all_subcharacteristics(
    deterministic_payload: Dict[str, Any],
    llm_audits: Optional[Dict[str, Dict[str, Any]]] = None,
    alpha_overrides: Optional[Dict[str, float]] = None,
) -> Dict[str, HybridScore]:
    """Bulk-score a `by_iso_subcharacteristic` payload from parse_deterministic.

    Args:
        deterministic_payload: shape produced by parse_deterministic — i.e.
            { "by_iso_subcharacteristic": { sub_id: {findings, ...}, ... } }
            or already the inner mapping if caller prefers to pre-extract.
        llm_audits: { sub_id: {"score_1_to_4"|"score": ...}, ... }.
        alpha_overrides: { sub_id: float }, beats COVERAGE_ALPHA.

    Returns:
        { sub_id: HybridScore }.
    """
    by_sub = deterministic_payload.get(
        "by_iso_subcharacteristic", deterministic_payload
    )
    audits = llm_audits or {}
    overrides = alpha_overrides or {}

    out: dict[str, HybridScore] = {}
    for sub_id, entry in by_sub.items():
        findings = entry.get("findings", []) if isinstance(entry, dict) else []
        out[sub_id] = score_subcharacteristic(
            sub_id,
            det_findings=findings,
            llm_audit=audits.get(sub_id),
            alpha=overrides.get(sub_id),
        )
    return out

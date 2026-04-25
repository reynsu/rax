"""Self-consistency benchmark for the LLM auditor.

Three tests:
    test_repetition_stability        — N=5 runs at temp=0.3, var ≤ 0.5.
    test_file_ordering_invariance    — 5 file orders, range ≤ 1.0.
    test_rubric_paraphrase_invariance — 3 rubric paraphrases, divergence ≤ 1.0.

These tests are EXPENSIVE: they hit real LLM APIs and burn tokens. They are
gated behind `@pytest.mark.expensive` so the regular test suite skips them.

Run them on a weekly cadence in CI, or before a release:

    pytest tests/test_self_consistency.py -m expensive --capture=no

Without ANTHROPIC_API_KEY the tests are skipped with a clear reason and a
synthetic results file is still written so downstream consumers (Phase 5
calibration drift monitoring) have a file to read.

Results land in `tests/results/self_consistency_<YYYY-MM-DD>.json` for
longitudinal tracking.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from statistics import variance
from typing import Any, Dict, List

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "tests" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


pytestmark = pytest.mark.expensive


def _have_anthropic_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _write_results(name: str, payload: Dict[str, Any]) -> Path:
    out = RESULTS_DIR / f"self_consistency_{date.today().isoformat()}.json"
    if out.exists():
        merged = json.loads(out.read_text())
    else:
        merged = {"runs": {}}
    merged["runs"][name] = payload
    out.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")
    return out


# ---------- shared LLM client ----------


def _audit_once(code: str, rubric_excerpt: str, temperature: float = 0.3) -> Dict[str, float]:
    """Call the LLM once. Return {sub_id: score_1_to_4}.

    Live implementation only runs when ANTHROPIC_API_KEY is set. Otherwise
    raises pytest.skip — the surrounding test wraps that.
    """
    if not _have_anthropic_key():
        pytest.skip("ANTHROPIC_API_KEY not set; skipping live LLM call")

    try:
        import anthropic  # type: ignore[import-untyped]
    except ImportError:
        pytest.skip("anthropic package not installed; pip install anthropic")

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=os.environ.get("RAX_AUDIT_MODEL", "claude-opus-4-7"),
        max_tokens=4096,
        temperature=temperature,
        system=(
            "You are auditing the following snippet. Return JSON of shape "
            "{\"subcharacteristics\": {\"ISO_X_Y\": {\"score_1_to_4\": <int 1..4>}}}. "
            "Use the rubric provided. JSON only, no prose."
        ),
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "[RUBRIC]\n" + rubric_excerpt},
            {"type": "text", "text": "[CODE]\n```tsx\n" + code + "\n```"},
        ]}],
    )
    text = "".join(part.text for part in msg.content if hasattr(part, "text"))
    parsed = json.loads(text)
    return {
        sub: float(entry.get("score_1_to_4", 0))
        for sub, entry in parsed.get("subcharacteristics", {}).items()
    }


# ---------- tests ----------


def test_repetition_stability():
    """N=5 runs on each anchor; variance per sub-characteristic ≤ 0.5."""
    anchors = sorted((REPO_ROOT / "tests" / "corpus" / "synthetic_anchors").iterdir())
    if not anchors:
        pytest.skip("no synthetic anchors found")

    rubric_text = (REPO_ROOT / "references" / "rubric-v2.md").read_text()
    fragile: List[Dict[str, Any]] = []

    for anchor_dir in anchors[:5]:  # cap to 5 anchors per run to control cost
        manifest = json.loads((anchor_dir / "manifest.json").read_text())
        code_path = next(anchor_dir.glob("code.*"))
        code = code_path.read_text()

        scores: List[float] = []
        for _ in range(5):
            res = _audit_once(code, rubric_text, temperature=0.3)
            scores.append(res.get(manifest["iso_sub_id"], 0.0))

        v = variance(scores) if len(scores) > 1 else 0.0
        if v > 0.5:
            fragile.append({"anchor": anchor_dir.name, "scores": scores, "variance": v})

    payload = {"fragile": fragile, "anchors_tested": len(anchors[:5])}
    _write_results("repetition_stability", payload)
    assert not fragile, f"fragile sub-chars: {fragile}"


def test_file_ordering_invariance():
    """Range (max-min) per sub-characteristic ≤ 1.0 across 5 file orders."""
    anchors = sorted((REPO_ROOT / "tests" / "corpus" / "synthetic_anchors").iterdir())
    if len(anchors) < 5:
        pytest.skip("need ≥ 5 anchors for file-ordering test")

    rubric_text = (REPO_ROOT / "references" / "rubric-v2.md").read_text()
    selected = anchors[:5]

    score_table: Dict[str, List[float]] = {}
    import random
    rng = random.Random(0)
    for _ in range(5):
        order = selected.copy()
        rng.shuffle(order)
        combined = "\n\n// ----\n\n".join((d.glob("code.*").__next__()).read_text() for d in order)
        res = _audit_once(combined, rubric_text)
        for sub, sc in res.items():
            score_table.setdefault(sub, []).append(sc)

    out_of_range = {
        sub: scores
        for sub, scores in score_table.items()
        if scores and (max(scores) - min(scores)) > 1.0
    }
    payload = {"out_of_range": out_of_range, "orders_tested": 5}
    _write_results("file_ordering_invariance", payload)
    assert not out_of_range, f"order-sensitive sub-chars: {out_of_range}"


def test_rubric_paraphrase_invariance():
    """3 paraphrased rubrics; divergence per sub-char ≤ 1.0."""
    anchors = sorted((REPO_ROOT / "tests" / "corpus" / "synthetic_anchors").iterdir())
    if not anchors:
        pytest.skip("no synthetic anchors found")

    rubric_text = (REPO_ROOT / "references" / "rubric-v2.md").read_text()
    paraphrases = [
        rubric_text,
        rubric_text.replace("anchor", "exemplar").replace("severity", "impact"),
        rubric_text.replace("score", "rating").replace("sub-characteristic", "sub-attribute"),
    ]

    score_table: Dict[str, List[float]] = {}
    for anchor_dir in anchors[:3]:
        code = next(anchor_dir.glob("code.*")).read_text()
        for r in paraphrases:
            res = _audit_once(code, r)
            for sub, sc in res.items():
                score_table.setdefault(sub, []).append(sc)

    diverging = {
        sub: scores
        for sub, scores in score_table.items()
        if scores and (max(scores) - min(scores)) > 1.0
    }
    payload = {"diverging": diverging, "paraphrases_tested": len(paraphrases)}
    _write_results("rubric_paraphrase_invariance", payload)
    assert not diverging, f"rubric-sensitive sub-chars: {diverging}"


# ---------- offline placeholder writer ----------


def test_write_offline_placeholder_results():
    """When LLM is unavailable, ensure a results file still exists.

    This test is the only one in this file that does not require an API key
    and runs even without `-m expensive`. It writes a placeholder so Phase 5
    calibration-drift monitoring has something to load.
    """
    out = RESULTS_DIR / f"self_consistency_{date.today().isoformat()}.json"
    if out.exists():
        return  # the real tests already wrote it
    placeholder = {
        "runs": {},
        "synthetic": True,
        "note": (
            "No live LLM run. Set ANTHROPIC_API_KEY and run "
            "`pytest tests/test_self_consistency.py -m expensive` to populate."
        ),
    }
    out.write_text(json.dumps(placeholder, indent=2) + "\n")


# Allow the placeholder writer to run without -m expensive
test_write_offline_placeholder_results.pytestmark = []  # type: ignore[attr-defined]

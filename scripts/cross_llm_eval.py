"""Cross-LLM consensus over a corpus item (anchor or mined repo).

Runs the audit prompt across three judges from distinct vendor families
(Anthropic Claude, OpenAI GPT-4o, Google Gemini Pro). For each ISO
sub-characteristic, reports per-judge score, median, range, std-dev, and
flags `high_disagreement_subchars` (range > 2).

Convergence ⇒ strong signal. Divergence ⇒ probably subjective sub-char or
prompt is ambiguous; review.

Auth via env vars:
    ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY

Missing keys → that judge is skipped and recorded under
`judges_unavailable`. The run still produces output as long as ≥1 judge
is available.

Usage:
    python scripts/cross_llm_eval.py tests/corpus/synthetic_anchors/<dir>
    python scripts/cross_llm_eval.py path/to/some/codebase

Outputs:
    tests/corpus/cross_llm/<corpus_item_slug>.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "tests" / "corpus" / "cross_llm"


# ---------- judge adapters (each returns Dict[sub_id, score_1_to_4]) ----------


def _read_corpus_item(path: Path) -> Tuple[str, Dict[str, Any]]:
    """Return (code_text, manifest_dict_or_empty)."""
    if path.is_dir():
        code_files = list(path.glob("code.*"))
        if not code_files:
            code_files = list(path.glob("*.tsx")) + list(path.glob("*.ts"))
        code = "\n\n".join(p.read_text() for p in code_files) if code_files else ""
        manifest_path = path / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        return code, manifest
    return path.read_text(), {}


def _build_prompt(code: str) -> str:
    rubric_path = REPO_ROOT / "references" / "rubric-v2.md"
    rubric = rubric_path.read_text() if rubric_path.exists() else ""
    return (
        "[ROLE] Senior React/RN auditor. Score each ISO 25010 sub-characteristic "
        "on a 1-4 scale per the rubric. Output strict JSON of shape "
        "{\"subcharacteristics\": {\"ISO_X_Y\": {\"score_1_to_4\": <int>}}}\n\n"
        f"[RUBRIC]\n{rubric}\n\n"
        f"[CODE]\n```tsx\n{code}\n```\n"
    )


def _parse_scores(text: str) -> Dict[str, float]:
    """Extract score_1_to_4 per sub_id from a JSON-shaped LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # try to locate the first {...} blob
        s = text.find("{")
        e = text.rfind("}")
        if s < 0 or e < 0:
            return {}
        try:
            data = json.loads(text[s:e + 1])
        except json.JSONDecodeError:
            return {}
    out: Dict[str, float] = {}
    for sub, entry in (data.get("subcharacteristics") or {}).items():
        score = entry.get("score_1_to_4")
        if isinstance(score, (int, float)):
            out[sub] = float(score)
    return out


def _judge_claude(prompt: str) -> Dict[str, float]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    try:
        import anthropic  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(f"anthropic package missing: {exc}") from exc
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=os.environ.get("RAX_CLAUDE_MODEL", "claude-opus-4-7"),
        max_tokens=4096,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(part.text for part in msg.content if hasattr(part, "text"))
    return _parse_scores(text)


def _judge_openai(prompt: str) -> Dict[str, float]:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set")
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(f"openai package missing: {exc}") from exc
    client = OpenAI()
    rsp = client.chat.completions.create(
        model=os.environ.get("RAX_OPENAI_MODEL", "gpt-4o-2024-11-20"),
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _parse_scores(rsp.choices[0].message.content or "")


def _judge_gemini(prompt: str) -> Dict[str, float]:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY not set")
    try:
        import google.generativeai as genai  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(f"google-generativeai package missing: {exc}") from exc
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel(os.environ.get("RAX_GEMINI_MODEL", "gemini-1.5-pro"))
    rsp = model.generate_content(prompt, generation_config={"temperature": 0.3})
    return _parse_scores(rsp.text)


JUDGES: Dict[str, Callable[[str], Dict[str, float]]] = {
    "claude": _judge_claude,
    "gpt4": _judge_openai,
    "gemini": _judge_gemini,
}

# Public alias so other modules don't reach for the underscore-prefixed
# private callables.
JUDGE_FUNCS: Dict[str, Callable[[str], Dict[str, float]]] = JUDGES


# ---------- aggregation ----------


def aggregate_scores(
    per_judge: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, Any]]:
    """For each sub_id present in any judge, compute median/range/std."""
    all_sub_ids = sorted({sid for d in per_judge.values() for sid in d})
    out: Dict[str, Dict[str, Any]] = {}
    for sub in all_sub_ids:
        votes = [(j, d[sub]) for j, d in per_judge.items() if sub in d]
        scores = [v for _, v in votes]
        record: Dict[str, Any] = {j: d.get(sub) for j, d in per_judge.items()}
        record["median"] = float(statistics.median(scores)) if scores else None
        record["range"] = round(max(scores) - min(scores), 3) if len(scores) > 1 else 0.0
        record["std"] = round(statistics.pstdev(scores), 3) if len(scores) > 1 else 0.0
        out[sub] = record
    return out


def high_disagreement(scores: Dict[str, Dict[str, Any]], threshold: float = 2.0) -> List[str]:
    return sorted(sub for sub, rec in scores.items() if (rec.get("range") or 0) > threshold)


# ---------- main ----------


def evaluate(
    target: Path,
    judges: Optional[List[str]] = None,
) -> Dict[str, Any]:
    code, manifest = _read_corpus_item(target)
    if not code.strip():
        raise ValueError(f"no code content found at {target}")

    prompt = _build_prompt(code)
    selected = judges or list(JUDGES.keys())

    per_judge: Dict[str, Dict[str, float]] = {}
    unavailable: Dict[str, str] = {}

    for name in selected:
        try:
            per_judge[name] = JUDGES[name](prompt)
        except Exception as exc:  # noqa: BLE001 — always continue on judge failure
            # Scrub before storing — SDK exception messages occasionally embed
            # the offending API key prefix.
            from scripts.secret_scrub import scrub
            unavailable[name] = scrub(str(exc))

    scores = aggregate_scores(per_judge)
    return {
        "target": str(target),
        "manifest": manifest,
        "judges_run": sorted(per_judge.keys()),
        "judges_unavailable": unavailable,
        "scores": scores,
        "high_disagreement_subchars": high_disagreement(scores),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def slugify(p: Path) -> str:
    return p.name.replace("/", "__").replace(" ", "_") or "unknown"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path)
    ap.add_argument("--judges", nargs="+", choices=list(JUDGES), default=None)
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = ap.parse_args(argv)

    if not args.target.exists():
        print(f"target not found: {args.target}", file=sys.stderr)
        return 2

    result = evaluate(args.target, args.judges)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{slugify(args.target)}.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    if not result["judges_run"]:
        print(
            "no judges available — set ANTHROPIC_API_KEY / OPENAI_API_KEY / "
            "GOOGLE_API_KEY and retry. Wrote empty result envelope.",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

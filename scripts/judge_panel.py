"""Multi-judge panel for rax v2 audits.

Runs the audit prompt against three judges from distinct vendor families
(Anthropic Claude, OpenAI GPT-4o, Google Gemini Pro). Optionally runs each
judge N times at temperature 0.3 to measure intra-judge stability. The
panel score per ISO sub-characteristic is the median of medians.

Output is structured JSON validated against
`references/audit-output.schema.json`. If a judge returns invalid JSON,
the parser tries one regex repair attempt; persistent failure marks the
judge as `failed` for that run and the panel proceeds with the survivors.

Pricing note. A full-mode run (3 models × 5 replicates = 15 calls) is the
single most expensive operation in rax. Use `--mode=quick` (3 calls total)
in CI; reserve full mode for releases.

Usage:
    python scripts/judge_panel.py --prompt-file /tmp/rax-prompt.txt
    python scripts/judge_panel.py --codebase tests/corpus/synthetic_anchors/<dir>/
    python scripts/judge_panel.py --codebase ./my-app --replicates 5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.cross_llm_eval import JUDGE_FUNCS
from scripts.secret_scrub import scrub as _scrub_secrets

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".cache" / "judge_panel"
SCHEMA_PATH = REPO_ROOT / "references" / "audit-output.schema.json"
CACHE_TTL_SEC = 7 * 24 * 3600   # 7 days

# Allowlist for path components used as cache directory names. Refuses any
# value containing path separators, nulls, or characters outside the safe set.
_SAFE_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


# ----- prompt utilities -----


def _load_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text()

    if not args.codebase:
        raise SystemExit("either --prompt-file or --codebase is required")

    target = Path(args.codebase)
    code_files: list[Path]
    if target.is_dir():
        code_files = sorted(list(target.glob("**/code.*"))) or sorted(
            list(target.glob("**/*.tsx"))[:20] + list(target.glob("**/*.ts"))[:20]
        )
    else:
        code_files = [target]

    code = "\n\n// ---- file: {f} ----\n\n".join(p.read_text() for p in code_files) if code_files else ""
    rubric_path = REPO_ROOT / "references" / "rubric-v2.md"
    rubric = rubric_path.read_text() if rubric_path.exists() else ""
    schema_text = SCHEMA_PATH.read_text() if SCHEMA_PATH.exists() else ""

    return (
        "[ROLE] Senior React/RN auditor. Output strict JSON conforming to the "
        "schema below. No prose outside the JSON.\n\n"
        f"[SCHEMA]\n{schema_text}\n\n"
        f"[RUBRIC]\n{rubric}\n\n"
        f"[CODE]\n```tsx\n{code}\n```\n"
    )


# ----- caching -----


def _safe_segment(value: str) -> str:
    """Refuse path-traversal-shaped components for cache filenames."""
    if not _SAFE_PATH_COMPONENT.match(value):
        raise ValueError(f"unsafe cache path segment: {value!r}")
    return value


def _cache_key(model: str, prompt: str) -> Path:
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / _safe_segment(model) / f"{h}.json"


def _cache_get(model: str, prompt: str) -> Optional[Dict[str, Any]]:
    try:
        p = _cache_key(model, prompt)
    except ValueError:
        return None
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL_SEC:
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def _cache_put(model: str, prompt: str, data: Dict[str, Any]) -> None:
    try:
        p = _cache_key(model, prompt)
    except ValueError:
        return  # don't write to a path we can't validate
    p.parent.mkdir(parents=True, exist_ok=True)
    # 0o600 so cached LLM outputs don't get read by other local users.
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        if os.path.exists(p):
            os.remove(p)
        raise


# ----- judges (delegated to cross_llm_eval; keeps sync wrappers reusable) -----


JUDGE_LABELS: Dict[str, str] = {
    "claude": os.environ.get("RAX_CLAUDE_MODEL", "claude-opus-4-7"),
    "gpt4": os.environ.get("RAX_OPENAI_MODEL", "gpt-4o-2024-11-20"),
    "gemini": os.environ.get("RAX_GEMINI_MODEL", "gemini-1.5-pro"),
}


def _run_judge_once(name: str, prompt: str) -> Dict[str, Any]:
    cached = _cache_get(name, prompt)
    if cached is not None:
        return {"source": "cache", "scores": cached}
    judge = JUDGE_FUNCS.get(name)
    if judge is None:
        raise ValueError(f"unknown judge: {name}")
    scores = judge(prompt)
    _cache_put(name, prompt, scores)
    return {"source": "live", "scores": scores}


def _run_judge_replicates(name: str, prompt: str, n: int) -> Dict[str, Any]:
    runs: list[Dict[str, float]] = []
    error: Optional[str] = None
    for _ in range(n):
        try:
            res = _run_judge_once(name, prompt)
            runs.append(res["scores"])
        except Exception as exc:  # noqa: BLE001 — keep panel running on any judge failure
            # Scrub before storing — exception text from SDK clients can embed
            # API key fragments (e.g., "Invalid key sk-ant-***...").
            error = _scrub_secrets(str(exc))
            break
    return {"runs": runs, "error": error}


# ----- aggregation -----


def _intra_judge(runs: List[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Per sub-id: median + variance across replicates."""
    sub_ids = sorted({sid for r in runs for sid in r})
    out: Dict[str, Dict[str, float]] = {}
    for sub in sub_ids:
        vals = [r[sub] for r in runs if sub in r]
        if not vals:
            continue
        out[sub] = {
            "median": float(statistics.median(vals)),
            "variance": float(statistics.pvariance(vals)) if len(vals) > 1 else 0.0,
            "samples": len(vals),
        }
    return out


def _confidence_class(intra_var: float, inter_var: float) -> str:
    if intra_var <= 0.5 and inter_var <= 0.5:
        return "high"
    if intra_var <= 1.0 and inter_var <= 1.0:
        return "medium"
    return "low"


def aggregate_panel(
    per_judge: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """For each sub-id, compute panel score + intra/inter variance + confidence."""
    judge_intras: Dict[str, Dict[str, Dict[str, float]]] = {
        j: _intra_judge(p["runs"]) for j, p in per_judge.items() if p["runs"]
    }
    sub_ids = sorted({sid for ji in judge_intras.values() for sid in ji})

    out: Dict[str, Dict[str, Any]] = {}
    for sub in sub_ids:
        medians = [ji[sub]["median"] for ji in judge_intras.values() if sub in ji]
        if not medians:
            continue
        intra_max = max(
            (ji[sub]["variance"] for ji in judge_intras.values() if sub in ji),
            default=0.0,
        )
        inter = float(statistics.pvariance(medians)) if len(medians) > 1 else 0.0
        out[sub] = {
            "panel_score": float(statistics.median(medians)),
            "per_judge_median": {
                j: ji[sub]["median"]
                for j, ji in judge_intras.items()
                if sub in ji
            },
            "intra_judge_variance_max": round(intra_max, 4),
            "inter_judge_variance": round(inter, 4),
            "confidence_class": _confidence_class(intra_max, inter),
        }
    return out


# ----- main -----


def run_panel(
    prompt: str,
    judges: Optional[List[str]] = None,
    replicates: int = 1,
) -> Dict[str, Any]:
    selected = judges or list(JUDGE_LABELS)
    per_judge: Dict[str, Dict[str, Any]] = {}
    judges_failed: Dict[str, str] = {}

    for j in selected:
        result = _run_judge_replicates(j, prompt, replicates)
        if result["error"] and not result["runs"]:
            judges_failed[j] = result["error"]
        else:
            per_judge[j] = result

    panel_scores = aggregate_panel(per_judge) if per_judge else {}
    return {
        "panel_scores": panel_scores,
        "judges_run": sorted(per_judge.keys()),
        "judges_failed": judges_failed,
        "models": JUDGE_LABELS,
        "replicates": replicates,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "is_single_judge_warning": len(per_judge) == 1,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", type=Path)
    ap.add_argument("--codebase", type=Path)
    ap.add_argument("--judges", nargs="+", choices=list(JUDGE_LABELS), default=None)
    ap.add_argument("--replicates", type=int, default=1)
    ap.add_argument("--mode", choices=("quick", "full"), default="quick",
                    help="quick: 1 replicate; full: --replicates (default 5)")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)

    if args.mode == "full" and args.replicates == 1:
        args.replicates = 5

    prompt = _load_prompt(args)
    result = run_panel(prompt, judges=args.judges, replicates=args.replicates)

    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    else:
        print(text)

    if not result["judges_run"]:
        sys.stderr.write(
            "WARN: no judges available — set ANTHROPIC_API_KEY / OPENAI_API_KEY / "
            "GOOGLE_API_KEY. Result envelope is still emitted.\n"
        )
        return 1
    if result["is_single_judge_warning"]:
        sys.stderr.write("WARN: only 1 judge available — single-judge result, less robust.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Compose the final audit prompt for the LLM.

Reads:
  - prompts/audit-system.md           (template with {placeholder}s)
  - /tmp/rax-deterministic.json       (or path passed via --deterministic)
  - references/rubric-v2.md           (filtered to relevant sub-chars)
  - corpus anchors (optional, empty in Phase 2; populated by Phase 3)

Substitutes:
  {deterministic_findings_json}            JSON of det findings
  {rubric_v2_for_relevant_subcharacteristics}  rubric excerpt
  {calibration_examples_from_corpus}       anchors corpus excerpt

Writes the composed prompt to stdout (default) or to a file.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = REPO_ROOT / "prompts" / "audit-system.md"
DEFAULT_DETERMINISTIC = Path("/tmp/rax-deterministic.json")
DEFAULT_RUBRIC = REPO_ROOT / "references" / "rubric-v2.md"
DEFAULT_CORPUS_ANCHORS = REPO_ROOT / "references" / "corpus-anchors.md"


def load_template(path: Path) -> str:
    return path.read_text()


def load_deterministic(path: Path) -> Dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {"by_iso_subcharacteristic": {}, "tools_run": [], "tools_failed": []}
    return json.loads(path.read_text())


def relevant_subchars(deterministic: Dict[str, Any]) -> List[str]:
    """Sub-chars that have any findings, plus the always-relevant ones."""
    by_sub = deterministic.get("by_iso_subcharacteristic", {})
    with_findings = [k for k, v in by_sub.items() if v.get("findings")]
    if with_findings:
        return sorted(with_findings)
    return sorted(by_sub.keys())


_SUBCHAR_HEADER_RE = re.compile(
    r"^##\s+\d+\.\d+\s+(ISO_[A-Z]+_[A-Z0-9]+)\s+", re.MULTILINE
)


def excerpt_rubric(rubric_text: str, sub_ids: List[str]) -> str:
    """Pull the sections of rubric-v2 that match the requested sub-chars.

    Falls back to the full rubric if the regex finds nothing (e.g., the
    rubric format changed). Better to give too much context than to fail
    silently.
    """
    if not sub_ids:
        return rubric_text

    matches = list(_SUBCHAR_HEADER_RE.finditer(rubric_text))
    if not matches:
        return rubric_text

    wanted = set(sub_ids)
    chunks: list[str] = []
    for i, m in enumerate(matches):
        sub_id = m.group(1)
        if sub_id not in wanted:
            continue
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(rubric_text)
        chunks.append(rubric_text[start:end].rstrip())

    if not chunks:
        return rubric_text
    return "\n\n".join(chunks)


def load_corpus_anchors(path: Path) -> str:
    """Reference-guided grading: pull 1 low + 1 high anchor per relevant
    sub-char from `tests/corpus/synthetic_anchors/`.

    `path` is kept as the manual override location (`references/corpus-anchors.md`)
    if the user wants to curate the section by hand. Otherwise we synthesize
    it from the structured anchor directories.
    """
    if path.exists() and path.read_text().strip():
        return path.read_text().strip()

    anchors_dir = REPO_ROOT / "tests" / "corpus" / "synthetic_anchors"
    if not anchors_dir.exists():
        return "(no calibration anchors yet — Phase 3 will populate this section)"

    by_sub: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for ad in anchors_dir.iterdir():
        if not ad.is_dir():
            continue
        manifest_path = ad / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            continue
        sub = manifest.get("iso_sub_id")
        score = manifest.get("expected_score_1_to_10")
        if not sub or not isinstance(score, (int, float)):
            continue
        bucket = "high" if score >= 7 else "low" if score <= 3 else "mid"
        if bucket == "mid":
            continue
        code_files = list(ad.glob("code.*"))
        if not code_files:
            continue
        by_sub.setdefault(sub, {})[bucket] = {
            "score": score,
            "code": code_files[0].read_text(),
            "justification": manifest.get("justification", ""),
            "slug": ad.name,
        }

    chunks: list[str] = []
    for sub in sorted(by_sub):
        pair = by_sub[sub]
        for tier in ("low", "high"):
            entry = pair.get(tier)
            if not entry:
                continue
            chunks.append(
                f"### {sub} — example at score {entry['score']}\n"
                f"```tsx\n{entry['code']}\n```\n"
                f"Why: {entry['justification']}"
            )

    if not chunks:
        return "(no calibration anchors yet — Phase 3 will populate this section)"
    return "\n\n".join(chunks)


def render_prompt(
    template: str,
    deterministic: Dict[str, Any],
    rubric_excerpt: str,
    corpus_anchors: str,
) -> str:
    return (
        template
        .replace(
            "{deterministic_findings_json}",
            json.dumps(deterministic, indent=2, sort_keys=True),
        )
        .replace(
            "{rubric_v2_for_relevant_subcharacteristics}",
            rubric_excerpt,
        )
        .replace(
            "{calibration_examples_from_corpus}",
            corpus_anchors,
        )
    )


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--deterministic", type=Path, default=DEFAULT_DETERMINISTIC)
    ap.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_ANCHORS)
    ap.add_argument("--output", type=Path, help="Write prompt here instead of stdout")
    args = ap.parse_args(argv)

    template = load_template(args.template)
    det = load_deterministic(args.deterministic)
    rubric_text = args.rubric.read_text() if args.rubric.exists() else ""
    sub_ids = relevant_subchars(det)
    rubric_excerpt = excerpt_rubric(rubric_text, sub_ids) if rubric_text else ""
    anchors = load_corpus_anchors(args.corpus)

    prompt = render_prompt(template, det, rubric_excerpt, anchors)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(prompt)
    else:
        sys.stdout.write(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())

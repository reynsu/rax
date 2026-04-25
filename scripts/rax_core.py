#!/usr/bin/env python3
"""rax · core

All state/query logic for the rax CLI. The bash dispatcher at bin/rax shells
out to this script for every subcommand except `audit`.

State lives under  .claude/rax/ :

  .claude/rax/
    baseline.json            active baseline (the thing we compare against)
    config.json              optional user overrides
    reports/
      latest.md              most recent report (copy, not symlink, for Windows)
      YYYY-MM-DDTHH-MM-SSZ.md
      ...
    baselines/
      <branch>.json          per-branch baseline snapshots
    archive/
      baseline_<ts>.json     archived baselines (from reset / overwrite)

Commands (dispatched by bin/rax):

  report save --file F [--commit SHA] [--mode MODE]
  report show [--id ID | latest] [--format full|summary|scores|raw]
  report latest
  report history [--limit N]
  report path --id ID
  baseline save [--id ID]
  baseline reset
  baseline info
  baseline list
  score
  scores
  delta
  findings pending [--category C] [--severity S] [--limit N]
  findings fixed
  findings new
  config init
  config show
  version

Exit codes: 0 ok, 1 usage error, 2 no data (no baseline/report), 3 parse error,
4 git error, 5 IO error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "0.2.0"

# ---------------------------------------------------------------------------
# ANSI colors — disabled if NO_COLOR env var or not a TTY.
# ---------------------------------------------------------------------------

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

def c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _USE_COLOR else s

BOLD   = lambda s: c("1", s)
DIM    = lambda s: c("2", s)
RED    = lambda s: c("31", s)
GREEN  = lambda s: c("32", s)
YELLOW = lambda s: c("33", s)
BLUE   = lambda s: c("34", s)
CYAN   = lambda s: c("36", s)
GRAY   = lambda s: c("90", s)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

STATE_DIRNAME = ".claude/rax"

def repo_root(start: Path) -> Path:
    """Discover git repo root, falling back to cwd if not a git repo."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, stderr=subprocess.DEVNULL, text=True
        ).strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not a git repo — rax still works, state just lives at cwd.
        return start.resolve()

def current_branch(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=root, stderr=subprocess.DEVNULL, text=True
        ).strip() or "detached"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no-git"

def current_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"

def state_dir(root: Path) -> Path:
    return root / STATE_DIRNAME

def reports_dir(root: Path) -> Path:
    return state_dir(root) / "reports"

def latest_report_path(root: Path) -> Path:
    return reports_dir(root) / "latest.md"

def active_baseline_path(root: Path) -> Path:
    return state_dir(root) / "baseline.json"

def branch_baseline_path(root: Path, branch: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", branch) or "unknown"
    return state_dir(root) / "baselines" / f"{safe}.json"

def archive_path(root: Path, kind: str = "baseline") -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return state_dir(root) / "archive" / f"{kind}_{ts}.json"

def config_path(root: Path) -> Path:
    return state_dir(root) / "config.json"

def ensure_dirs(root: Path) -> None:
    for p in [state_dir(root), reports_dir(root),
              state_dir(root) / "baselines", state_dir(root) / "archive"]:
        p.mkdir(parents=True, exist_ok=True)

def _safe_rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)

# ---------------------------------------------------------------------------
# Report parser — same fixed format as references/report-format.md
# ---------------------------------------------------------------------------

# v1 patterns (3-letter category codes, single-number scores).
RE_OVERALL = re.compile(r"^##\s*Overall:\s*([0-9]+\.[0-9])\s*/\s*10", re.MULTILINE)
RE_CAT_ROW = re.compile(
    r"^\|\s*([A-Z]{3})\s*\|[^|]+\|\s*([0-9]+\.[0-9])\s*/\s*10\s*\|",
    re.MULTILINE,
)
RE_SUB_ROW = re.compile(
    r"^\|\s*([A-Z]{3}-\d+)\s+([^|]+?)\s*\|\s*([0-9]+)\s*/\s*10\s*\|",
    re.MULTILINE,
)
RE_FINDING = re.compile(
    r"^###\s*([CW])(\d+)\.\s*\[([A-Z]{3})\]\s*(.+?)$",
    re.MULTILINE,
)

# v2 patterns. Reports place the overall as e.g.:
#   `## Overall: [6.4, 8.1]/10  (90% CI, median 7.3)`
RE_OVERALL_V2 = re.compile(
    r"^##\s*Overall:\s*\[\s*([0-9]+\.[0-9]+)\s*,\s*([0-9]+\.[0-9]+)\s*\]\s*/\s*10"
    r".*?median\s+([0-9]+\.[0-9]+)",
    re.MULTILINE | re.IGNORECASE,
)
# v2 category table row:
#   `| Security | [3.5, 5.0] | 4.2 | high | -0.4 |`
#   `| Reliability | ABSTAINED | — | low | — |`
RE_CAT_ROW_V2 = re.compile(
    r"^\|\s*([A-Za-z][A-Za-z _\-/]+?)\s*\|\s*"
    r"(?:\[\s*([0-9]+\.[0-9]+)\s*,\s*([0-9]+\.[0-9]+)\s*\]|ABSTAINED)\s*\|\s*"
    r"(?:([0-9]+\.[0-9]+)|—|-)\s*\|",
    re.MULTILINE,
)
# v2 finding header: `### 1. [SEC/Confidentiality] Hardcoded production secret`
RE_FINDING_V2 = re.compile(
    r"^###\s*\d+\.\s*\[([A-Z]+(?:/[A-Za-z _]+)?)\]\s*(.+?)$",
    re.MULTILINE,
)
RE_PROFILE  = re.compile(r"^\*\*Profile:\*\*\s*(.+?)$", re.MULTILINE)
RE_RUBRIC   = re.compile(r"^\*\*Rubric:\*\*\s*(.+?)$", re.MULTILINE)
RE_WHERE    = re.compile(r"^-\s*\*\*Where:\*\*\s*(.+?)$", re.MULTILINE)
RE_SEVERITY = re.compile(r"^-\s*\*\*Severity:\*\*\s*(\w+)", re.MULTILINE)
RE_FIX      = re.compile(r"^-\s*\*\*Fix:\*\*\s*(.+?)$", re.MULTILINE)
# Match metadata in either v1 (`- **Key:** value`) or v2 (`**Key:** value`)
# layout. Leading `- ` is optional.
RE_MODE     = re.compile(r"^(?:-\s*)?\*\*Mode:\*\*\s*(\w+)", re.MULTILINE)
RE_COMMIT   = re.compile(r"^(?:-\s*)?\*\*Commit:\*\*\s*([0-9a-f]{6,40})", re.MULTILINE)
RE_BRANCH   = re.compile(r"^(?:-\s*)?\*\*Branch:\*\*\s*(.+?)$", re.MULTILINE)

CATEGORY_WEIGHTS = {
    "ARC": 12, "CQR": 10, "RXP": 12, "PRF": 12, "SEC": 13,
    "UXA": 10, "TYP": 8,  "ERR": 7,  "TST": 8,  "DEP": 4, "APT": 4,
}
CATEGORY_NAMES = {
    "ARC": "Architecture",
    "CQR": "Code quality",
    "RXP": "React patterns",
    "PRF": "Performance",
    "SEC": "Security",
    "UXA": "UX & accessibility",
    "TYP": "Type safety",
    "ERR": "Error handling",
    "TST": "Testing",
    "DEP": "Dependencies",
    "APT": "Anti-patterns",
}

def parse_report(md: str) -> Dict[str, Any]:
    """Extract scores and findings from a report markdown file.

    Detects v1 vs v2 format and returns a unified shape:

        {
          "version":     "v1" | "v2",
          "overall":     float          # the median in v2, the score in v1
          "interval":    [lo, hi] | None # only for v2
          "categories":  {name: float}  # median in v2, score in v1
          "category_intervals": {name: [lo, hi]} | {}  # v2 only
          "subcriteria": {id: int}      # v1 only (kept for backwards compat)
          "findings":    [...]
          "mode" / "commit" / "branch" / "profile" / "rubric": str | None
        }
    """
    result: Dict[str, Any] = {
        "version": None,
        "overall": None,
        "interval": None,
        "categories": {},
        "category_intervals": {},
        "subcriteria": {},
        "findings": [],
        "mode": None,
        "commit": None,
        "branch": None,
        "profile": None,
        "rubric": None,
    }

    # --- detect version by overall-line shape ---
    m_v2 = RE_OVERALL_V2.search(md)
    m_v1 = RE_OVERALL.search(md)

    if m_v2:
        result["version"] = "v2"
        lo, hi, median = float(m_v2.group(1)), float(m_v2.group(2)), float(m_v2.group(3))
        result["overall"] = median
        result["interval"] = [lo, hi]

        for name, lo_s, hi_s, med_s in RE_CAT_ROW_V2.findall(md):
            cname = name.strip()
            if not cname or cname.lower() in ("iso characteristic", "characteristic"):
                continue
            if lo_s and hi_s:
                result["category_intervals"][cname] = [float(lo_s), float(hi_s)]
            if med_s:
                result["categories"][cname] = float(med_s)

        m_prof = RE_PROFILE.search(md)
        if m_prof:
            result["profile"] = m_prof.group(1).strip()
        m_rub = RE_RUBRIC.search(md)
        if m_rub:
            result["rubric"] = m_rub.group(1).strip()

    elif m_v1:
        result["version"] = "v1"
        result["overall"] = float(m_v1.group(1))
        for cat, score in RE_CAT_ROW.findall(md):
            result["categories"][cat] = float(score)
        for code, _name, score in RE_SUB_ROW.findall(md):
            result["subcriteria"][code] = int(score)
    else:
        raise ValueError("could not parse overall score; is this a rax report?")

    # Metadata shared between v1 and v2.
    m_mode = RE_MODE.search(md);   result["mode"]   = m_mode.group(1) if m_mode else None
    m_com  = RE_COMMIT.search(md); result["commit"] = m_com.group(1) if m_com else None
    m_br   = RE_BRANCH.search(md); result["branch"] = m_br.group(1).strip() if m_br else None

    # --- findings ---
    findings: List[Dict[str, Any]] = []

    if result["version"] == "v2":
        # v2 finding format: `### 1. [SEC/Confidentiality] Title here`
        for m_find in RE_FINDING_V2.finditer(md):
            cat_full = m_find.group(1).strip()              # e.g. "SEC/Confidentiality"
            title = m_find.group(2).strip()
            cat_top = cat_full.split("/", 1)[0]              # "SEC"
            start = m_find.end()
            next_heading = re.search(r"^###?\s|^##\s", md[start:], re.MULTILINE)
            block = md[start : start + (next_heading.start() if next_heading else len(md) - start)]

            m_where = RE_WHERE.search(block)
            where = m_where.group(1).strip() if m_where else ""
            m_sev = RE_SEVERITY.search(block)
            severity = m_sev.group(1).lower() if m_sev else "medium"
            m_fix = RE_FIX.search(block)
            fix = m_fix.group(1).strip() if m_fix else ""
            kind = "critical" if severity == "high" else "warning"

            findings.append({
                "kind": kind,
                "category": cat_top,
                "category_full": cat_full,
                "title": title,
                "where": where,
                "severity": severity,
                "fix": fix,
                "fingerprint": fingerprint(cat_top, title, where),
            })
    else:
        for m_find in RE_FINDING.finditer(md):
            kind = "critical" if m_find.group(1) == "C" else "warning"
            cat = m_find.group(3)
            title = m_find.group(4).strip()
            start = m_find.end()
            next_heading = re.search(r"^###\s", md[start:], re.MULTILINE)
            block = md[start : start + (next_heading.start() if next_heading else len(md) - start)]

            m_where = RE_WHERE.search(block)
            where = m_where.group(1).strip() if m_where else ""
            m_sev = RE_SEVERITY.search(block)
            severity = m_sev.group(1).lower() if m_sev else ("high" if kind == "critical" else "medium")
            m_fix = RE_FIX.search(block)
            fix = m_fix.group(1).strip() if m_fix else ""

            findings.append({
                "kind": kind,
                "category": cat,
                "title": title,
                "where": where,
                "severity": severity,
                "fix": fix,
                "fingerprint": fingerprint(cat, title, where),
            })

    result["findings"] = findings
    return result

def fingerprint(category: str, title: str, where: str) -> str:
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip()).lower()
    # Strip line ranges from where — a finding that shifts 5 lines is the same
    # finding. We keep the file path + first line only.
    w = norm(where)
    w = re.sub(r":(\d+)[-:][\d\-,\s]+", r":\1", w)
    payload = f"{category}|{norm(title)}|{w}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

# ---------------------------------------------------------------------------
# Report history (on-disk)
# ---------------------------------------------------------------------------

REPORT_TS_FMT = "%Y-%m-%dT%H-%M-%SZ"
# Allow optional `-N` counter suffix for sub-second collisions: 2026-04-24T21-56-06Z.md
# or 2026-04-24T21-56-06Z-2.md.
RE_REPORT_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)(?:-(\d+))?\.md$")

def list_reports(root: Path) -> List[Path]:
    d = reports_dir(root)
    if not d.exists():
        return []
    entries = []
    for p in d.iterdir():
        if not p.is_file():
            continue
        m = RE_REPORT_NAME.match(p.name)
        if not m:
            continue
        ts = m.group(1)
        counter = int(m.group(2)) if m.group(2) else 1
        entries.append((ts, counter, p))
    # Newest first — sort by (timestamp, counter) descending so that the
    # -2 suffix (saved later) ranks above the plain file in the same second.
    entries.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [p for _, _, p in entries]

def latest_report_file(root: Path) -> Optional[Path]:
    """Return the most recent timestamped report, or None."""
    reports = list_reports(root)
    return reports[0] if reports else None

def report_by_id(root: Path, ident: str) -> Optional[Path]:
    """Resolve an id to a report path. Accepts: 'latest', a full timestamp,
    a prefix of a timestamp, or an integer index (1-based, 1=latest)."""
    reports = list_reports(root)
    if not reports:
        return None
    if ident == "latest":
        return reports[0]
    if ident.isdigit():
        i = int(ident) - 1
        return reports[i] if 0 <= i < len(reports) else None
    # prefix match
    matches = [p for p in reports if p.stem.startswith(ident)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"ambiguous id '{ident}' (matches {len(matches)} reports)")
    return None

# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------

def load_baseline(root: Path) -> Optional[Dict[str, Any]]:
    p = active_baseline_path(root)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"warning: baseline at {p} is corrupt", file=sys.stderr)
        return None

def save_baseline_from_report(root: Path, report_path: Path,
                               commit: Optional[str]) -> Dict[str, Any]:
    md = report_path.read_text(encoding="utf-8")
    parsed = parse_report(md)  # may raise ValueError

    if not commit:
        commit = parsed.get("commit") or current_commit(root)
    branch = parsed.get("branch") or current_branch(root)

    baseline = {
        "version": 2,
        "commit_sha": commit,
        "branch": branch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": parsed["overall"],
        "categories": parsed["categories"],
        "subcriteria": parsed["subcriteria"],
        "findings": parsed["findings"],
        "report_path": _safe_rel(report_path, root),
        "mode": parsed.get("mode"),
    }

    ensure_dirs(root)
    active = active_baseline_path(root)
    if active.exists():
        arch = archive_path(root)
        arch.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(active, arch)

    branch_p = branch_baseline_path(root, branch)
    branch_p.parent.mkdir(parents=True, exist_ok=True)
    branch_p.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")

    shutil.copy2(branch_p, active)
    return baseline

# ---------------------------------------------------------------------------
# Delta math
# ---------------------------------------------------------------------------

def compute_delta(baseline: Dict[str, Any],
                  current: Dict[str, Any]) -> Dict[str, Any]:
    round1 = lambda x: round(x, 1)
    overall_delta = round1(current["overall"] - baseline["overall"])

    cat_deltas = {}
    all_cats = set(baseline.get("categories", {})) | set(current.get("categories", {}))
    for cat in sorted(all_cats):
        cur = current.get("categories", {}).get(cat)
        base = baseline.get("categories", {}).get(cat)
        if cur is None:
            cat_deltas[cat] = {"current": None, "baseline": base, "delta": None}
        elif base is None:
            cat_deltas[cat] = {"current": cur, "baseline": None, "delta": None}
        else:
            cat_deltas[cat] = {"current": cur, "baseline": base, "delta": round1(cur - base)}

    sub_deltas = {}
    for code, cur in current.get("subcriteria", {}).items():
        base = baseline.get("subcriteria", {}).get(code)
        if base is None:
            sub_deltas[code] = {"current": cur, "baseline": None, "delta": None}
        elif cur != base:
            sub_deltas[code] = {"current": cur, "baseline": base, "delta": cur - base}

    baseline_fps = {f["fingerprint"]: f for f in baseline.get("findings", [])}
    current_fps  = {f["fingerprint"]: f for f in current.get("findings", [])}

    new_findings   = [f for fp, f in current_fps.items()  if fp not in baseline_fps]
    fixed_findings = [f for fp, f in baseline_fps.items() if fp not in current_fps]
    persisting     = [f for fp, f in current_fps.items()  if fp in baseline_fps]

    return {
        "baseline_commit": baseline.get("commit_sha"),
        "baseline_branch": baseline.get("branch"),
        "baseline_date":   baseline.get("timestamp"),
        "overall": {
            "current":  current["overall"],
            "baseline": baseline["overall"],
            "delta":    overall_delta,
        },
        "categories":          cat_deltas,
        "subcriteria_changed": sub_deltas,
        "findings": {
            "new":              new_findings,
            "fixed":            fixed_findings,
            "persisting":       persisting,
            "persisting_count": len(persisting),
        },
    }

# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

def delta_arrow(d: Optional[float]) -> str:
    if d is None:
        return GRAY("—")
    if d > 0.05:
        return GREEN(f"▲ +{d:.1f}")
    if d < -0.05:
        return RED(f"▼ {d:+.1f}")
    return GRAY("↔  0.0")

def sev_tag(sev: str) -> str:
    sev = sev.lower()
    if sev in ("critical", "severe", "high"):
        return RED(f"[{sev.upper():<6}]")
    if sev == "medium" or sev == "major":
        return YELLOW(f"[{sev.upper():<6}]")
    return CYAN(f"[{sev.upper():<6}]")

def fmt_iso_human(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return iso

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_report_save(args) -> int:
    root = args.root
    src = args.file.resolve()
    if not src.exists():
        print(f"error: file not found: {src}", file=sys.stderr)
        return 1
    try:
        parsed = parse_report(src.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3

    ensure_dirs(root)
    ts = datetime.now(timezone.utc).strftime(REPORT_TS_FMT)
    dest = reports_dir(root) / f"{ts}.md"
    # If a report with this timestamp already exists (rare, but possible in
    # fast-fire tests), append -2, -3, ... so we never overwrite history.
    counter = 2
    while dest.exists():
        dest = reports_dir(root) / f"{ts}-{counter}.md"
        counter += 1
    shutil.copy2(src, dest)
    # Update latest.md pointer (copy for cross-platform).
    shutil.copy2(dest, latest_report_path(root))

    # Print one-line summary.
    print(GREEN("saved"),
          f"{_safe_rel(dest, root)}",
          DIM(f"({parsed['overall']:.1f}/10, {len(parsed['findings'])} findings)"))
    if args.json:
        print(json.dumps({
            "saved": str(dest),
            "overall": parsed["overall"],
            "findings": len(parsed["findings"]),
            "mode": parsed.get("mode"),
        }))
    return 0

def cmd_report_latest(args) -> int:
    root = args.root
    p = latest_report_file(root)
    if p is None:
        print("no reports found", file=sys.stderr)
        return 2
    print(_safe_rel(p, root))
    return 0

def cmd_report_path(args) -> int:
    root = args.root
    try:
        p = report_by_id(root, args.id)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if p is None:
        print(f"no report for id '{args.id}'", file=sys.stderr)
        return 2
    print(_safe_rel(p, root))
    return 0

def cmd_report_show(args) -> int:
    root = args.root
    ident = args.id or "latest"
    try:
        p = report_by_id(root, ident)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if p is None:
        print(f"no report for id '{ident}'", file=sys.stderr)
        return 2

    md = p.read_text(encoding="utf-8")
    fmt = args.format or "full"

    if fmt == "raw" or fmt == "full":
        # Just cat. For 'full' we could add colors but markdown renders fine.
        sys.stdout.write(md)
        if not md.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    parsed = parse_report(md)
    if fmt == "summary":
        return _print_summary(root, p, parsed)
    if fmt == "scores":
        return _print_scores(root, parsed, compare_baseline=True)
    print(f"error: unknown format '{fmt}'", file=sys.stderr)
    return 1

def cmd_report_history(args) -> int:
    root = args.root
    reports = list_reports(root)
    if not reports:
        print("no reports yet. run 'rax audit' first.", file=sys.stderr)
        return 2

    baseline = load_baseline(root)
    baseline_commit = baseline.get("commit_sha") if baseline else None

    print(BOLD("Audit history") + DIM(f" ({len(reports)} reports)"))
    print()
    # header
    print(GRAY(f"  {'#':>3}  {'when':<16}  {'score':<7}  {'mode':<8}  {'commit':<9}  branch"))
    limit = args.limit if args.limit else len(reports)
    for i, p in enumerate(reports[:limit], start=1):
        try:
            parsed = parse_report(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        when = p.stem.replace("T", " ").replace("-", ":")
        # timestamps are YYYY-MM-DDTHH-MM-SSZ with colons replaced; recover format:
        m = RE_REPORT_NAME.match(p.name)
        when = datetime.strptime(m.group(1), REPORT_TS_FMT).strftime("%Y-%m-%d %H:%M") if m else p.stem
        commit = (parsed.get("commit") or "unknown")[:7]
        branch = parsed.get("branch") or "?"
        is_base = baseline_commit and parsed.get("commit") == baseline_commit
        tag = YELLOW("  ★ baseline") if is_base else ""
        mode = parsed.get("mode") or "?"
        score = f"{parsed['overall']:.1f}/10"
        print(f"  {i:>3}  {when:<16}  {score:<7}  {mode:<8}  {commit:<9}  {branch}{tag}")
    return 0

def cmd_baseline_save(args) -> int:
    root = args.root
    if args.id:
        try:
            src = report_by_id(root, args.id)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr); return 1
        if src is None:
            print(f"no report for id '{args.id}'", file=sys.stderr); return 2
    else:
        src = latest_report_file(root)
        if src is None:
            print("no report to promote. run 'rax audit' first.", file=sys.stderr); return 2

    try:
        b = save_baseline_from_report(root, src, args.commit)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr); return 3

    print(GREEN("baseline saved"),
          DIM(f"(overall {b['overall']:.1f}/10, commit {(b['commit_sha'] or '?')[:7]}, branch {b['branch']})"))
    print(DIM(f"  from: {_safe_rel(src, root)}"))
    return 0

def cmd_baseline_reset(args) -> int:
    root = args.root
    active = active_baseline_path(root)
    if not active.exists():
        print("no baseline to reset"); return 0
    arch = archive_path(root)
    arch.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(active), str(arch))
    print(GREEN("baseline cleared"), DIM(f"(archived to {_safe_rel(arch, root)})"))
    return 0

def cmd_baseline_info(args) -> int:
    root = args.root
    b = load_baseline(root)
    if b is None:
        print("no baseline set. run 'rax baseline save' after an audit.", file=sys.stderr)
        return 2
    print(BOLD("Current baseline"))
    print(f"  overall:  {b['overall']:.1f}/10")
    print(f"  commit:   {(b.get('commit_sha') or '?')[:12]}")
    print(f"  branch:   {b.get('branch') or '?'}")
    print(f"  saved:    {fmt_iso_human(b.get('timestamp', ''))}")
    print(f"  mode:     {b.get('mode') or '?'}")
    print(f"  findings: {len(b.get('findings', []))}")
    print(f"  source:   {b.get('report_path') or '?'}")
    return 0

def cmd_baseline_list(args) -> int:
    root = args.root
    d = state_dir(root) / "baselines"
    if not d.exists():
        print("no branch baselines yet", file=sys.stderr); return 2
    files = sorted(d.glob("*.json"))
    if not files:
        print("no branch baselines yet", file=sys.stderr); return 2
    print(BOLD("Branch baselines"))
    active = load_baseline(root)
    active_commit = active.get("commit_sha") if active else None
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            score = f"{data['overall']:.1f}/10"
            commit = (data.get('commit_sha') or '?')[:7]
            when = fmt_iso_human(data.get('timestamp', ''))
            marker = YELLOW(" ★") if data.get('commit_sha') == active_commit else ""
            print(f"  {f.stem:<30}  {score:<7}  {commit:<8}  {when}{marker}")
        except (json.JSONDecodeError, KeyError):
            print(f"  {f.stem:<30}  {RED('corrupt')}")
    return 0

def cmd_score(args) -> int:
    root = args.root
    p = latest_report_file(root)
    if p is None:
        print("no reports yet. run 'rax audit' first.", file=sys.stderr); return 2
    parsed = parse_report(p.read_text(encoding="utf-8"))
    baseline = load_baseline(root)
    overall_str = f"{parsed['overall']:.1f}/10"
    line = BOLD(overall_str)
    if baseline:
        d = round(parsed["overall"] - baseline["overall"], 1)
        line += f"  {delta_arrow(d)} vs baseline ({baseline['overall']:.1f})"
    print(line)
    commit = (parsed.get("commit") or "?")[:7]
    print(DIM(f"last audit: {fmt_iso_human(datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat())}"
              f" · {parsed.get('mode') or '?'} mode · commit {commit}"))
    return 0

def _print_scores(root: Path, parsed: Dict[str, Any], compare_baseline: bool) -> int:
    baseline = load_baseline(root) if compare_baseline else None
    base_cats = baseline["categories"] if baseline else {}

    print(BOLD(f"Category scores  ({parsed['overall']:.1f}/10 overall)"))
    print()
    header = f"  {'code':<5}  {'category':<22}  {'score':>7}   {'Δ':<12}  {'weight':>6}"
    print(GRAY(header))
    for cat, weight in sorted(CATEGORY_WEIGHTS.items(), key=lambda x: -x[1]):
        cur = parsed["categories"].get(cat)
        base = base_cats.get(cat)
        if cur is None:
            score_str = GRAY("  n/a")
            delta_str = GRAY("—")
        else:
            score_str = f"{cur:.1f}/10"
            if base is not None:
                d = round(cur - base, 1)
                delta_str = delta_arrow(d)
            else:
                delta_str = GRAY("—")
        name = CATEGORY_NAMES.get(cat, cat)
        print(f"  {cat:<5}  {name:<22}  {score_str:>7}   {delta_str:<22}  {weight:>4}%")
    print()
    print(GRAY(f"  {'':<5}  {'':<22}  {'───':>7}"))
    overall_str = f"{parsed['overall']:.1f}/10"
    if baseline:
        d = round(parsed["overall"] - baseline["overall"], 1)
        print(f"  {'':<5}  {BOLD('overall'):<31}  {BOLD(overall_str):>7}   {delta_arrow(d)}")
    else:
        print(f"  {'':<5}  {BOLD('overall'):<31}  {BOLD(overall_str):>7}")
    return 0

def cmd_scores(args) -> int:
    root = args.root
    p = latest_report_file(root)
    if p is None:
        print("no reports yet. run 'rax audit' first.", file=sys.stderr); return 2
    parsed = parse_report(p.read_text(encoding="utf-8"))
    return _print_scores(root, parsed, compare_baseline=True)

def cmd_delta(args) -> int:
    root = args.root
    baseline = load_baseline(root)
    if baseline is None:
        print("no baseline to compare against. run 'rax baseline save' first.", file=sys.stderr)
        return 2
    p = latest_report_file(root)
    if p is None:
        print("no current report. run 'rax audit' first.", file=sys.stderr); return 2
    current = parse_report(p.read_text(encoding="utf-8"))
    d = compute_delta(baseline, current)

    print(BOLD("Score movement vs baseline"))
    print(DIM(f"  baseline: commit {(d['baseline_commit'] or '?')[:7]} · "
              f"{fmt_iso_human(d['baseline_date'] or '')}"))
    print()

    # Category table
    print(GRAY(f"  {'code':<5}  {'category':<22}  {'base':>5}  {'→':^3}  {'curr':>5}   {'Δ':<12}"))
    movers = []
    unchanged = 0
    for cat, info in d["categories"].items():
        if info["baseline"] is None or info["current"] is None:
            continue
        if info["delta"] == 0:
            unchanged += 1
            continue
        movers.append((cat, info))
    # Sort by absolute delta desc
    movers.sort(key=lambda x: -abs(x[1]["delta"] or 0))
    for cat, info in movers:
        name = CATEGORY_NAMES.get(cat, cat)
        print(f"  {cat:<5}  {name:<22}  "
              f"{info['baseline']:>5.1f}  {'→':^3}  {info['current']:>5.1f}   "
              f"{delta_arrow(info['delta'])}")
    if not movers:
        print(GRAY("  (all categories unchanged)"))
    if unchanged:
        print(GRAY(f"  ({unchanged} categor{'y' if unchanged==1 else 'ies'} unchanged)"))

    print()
    overall_d = d["overall"]["delta"]
    cur_str = BOLD(f"{d['overall']['current']:.1f}")
    delta_text = f"{overall_d:+.1f}" if overall_d else "0.0"
    print(f"  overall: {delta_text}  "
          f"({d['overall']['baseline']:.1f} → {cur_str})  "
          f"{delta_arrow(overall_d)}")

    n_new   = len(d["findings"]["new"])
    n_fixed = len(d["findings"]["fixed"])
    n_pers  = d["findings"]["persisting_count"]
    parts = []
    if n_fixed: parts.append(GREEN(f"{n_fixed} fixed"))
    if n_new:   parts.append(RED(f"{n_new} new"))
    if n_pers:  parts.append(GRAY(f"{n_pers} persisting"))
    if parts:
        print(f"  findings: {' · '.join(parts)}")
    return 0

def _filter_findings(findings: List[Dict[str, Any]],
                     category: Optional[str],
                     severity: Optional[str]) -> List[Dict[str, Any]]:
    out = findings
    if category:
        cat = category.upper()
        out = [f for f in out if f["category"] == cat]
    if severity:
        sev = severity.lower()
        # Allow grouping: 'high' matches critical+severe+high
        groups = {
            "high":   {"critical", "severe", "high"},
            "medium": {"medium", "major"},
            "low":    {"low", "minor", "info"},
        }
        allowed = groups.get(sev, {sev})
        out = [f for f in out if f["severity"] in allowed]
    return out

def _print_findings(title: str, findings: List[Dict[str, Any]],
                    limit: Optional[int] = None) -> None:
    print(BOLD(title) + DIM(f"  ({len(findings)})"))
    if not findings:
        print(GRAY("  (none)"))
        return
    print()
    # Group by severity: high first, then medium, then low.
    order = {"critical": 0, "severe": 0, "high": 0,
             "major": 1, "medium": 1,
             "minor": 2, "low": 2, "info": 2}
    findings = sorted(findings, key=lambda f: (order.get(f["severity"], 3),
                                                f["category"], f["title"]))
    shown = findings[:limit] if limit else findings
    for f in shown:
        tag = sev_tag(f["severity"])
        cat = BLUE(f["category"])
        where = f["where"] or DIM("(no location)")
        print(f"  {tag}  {cat}  {where}")
        print(f"         {f['title']}")
        if f.get("fix"):
            print(f"         {DIM('→ ' + f['fix'])}")
        print()
    if limit and len(findings) > limit:
        print(DIM(f"  ... {len(findings) - limit} more (use --limit 0 to show all)"))

def cmd_findings_pending(args) -> int:
    root = args.root
    p = latest_report_file(root)
    if p is None:
        print("no reports yet. run 'rax audit' first.", file=sys.stderr); return 2
    parsed = parse_report(p.read_text(encoding="utf-8"))
    filtered = _filter_findings(parsed["findings"], args.category, args.severity)
    _print_findings("Pending findings", filtered, limit=None if args.limit == 0 else args.limit)
    return 0

def cmd_findings_fixed(args) -> int:
    root = args.root
    baseline = load_baseline(root)
    if baseline is None:
        print("no baseline. run 'rax baseline save' first.", file=sys.stderr); return 2
    p = latest_report_file(root)
    if p is None:
        print("no current report. run 'rax audit' first.", file=sys.stderr); return 2
    current = parse_report(p.read_text(encoding="utf-8"))
    d = compute_delta(baseline, current)
    fixed = d["findings"]["fixed"]
    filtered = _filter_findings(fixed, args.category, args.severity) if hasattr(args, 'category') else fixed
    _print_findings(GREEN("Fixed since baseline") + "", filtered)
    return 0

def cmd_findings_new(args) -> int:
    root = args.root
    baseline = load_baseline(root)
    if baseline is None:
        print("no baseline. run 'rax baseline save' first.", file=sys.stderr); return 2
    p = latest_report_file(root)
    if p is None:
        print("no current report. run 'rax audit' first.", file=sys.stderr); return 2
    current = parse_report(p.read_text(encoding="utf-8"))
    d = compute_delta(baseline, current)
    new = d["findings"]["new"]
    filtered = _filter_findings(new, args.category, args.severity) if hasattr(args, 'category') else new
    _print_findings(RED("New findings introduced"), filtered)
    return 0

def _print_summary(root: Path, report_path: Path, parsed: Dict[str, Any]) -> int:
    baseline = load_baseline(root)
    print(BOLD(f"Report: {_safe_rel(report_path, root)}"))
    print(DIM(f"  commit {(parsed.get('commit') or '?')[:7]}  ·  "
              f"branch {parsed.get('branch') or '?'}  ·  "
              f"mode {parsed.get('mode') or '?'}"))
    print()
    overall_str = BOLD(f"{parsed['overall']:.1f}/10")
    line = f"Overall: {overall_str}"
    if baseline:
        d = round(parsed["overall"] - baseline["overall"], 1)
        line += f"  {delta_arrow(d)} vs baseline"
    print(line)
    print()
    # Top regressions/improvements if baseline exists
    if baseline:
        deltas = []
        for cat, cur in parsed["categories"].items():
            base = baseline["categories"].get(cat)
            if base is not None and cur != base:
                deltas.append((cat, cur - base, cur, base))
        if deltas:
            deltas.sort(key=lambda x: x[1])
            print(BOLD("Biggest movers:"))
            worst = [d for d in deltas if d[1] < 0][:3]
            best = [d for d in deltas if d[1] > 0][-3:][::-1]
            for cat, d, cur, base in worst:
                print(f"  {RED('▼')} {cat} {CATEGORY_NAMES.get(cat, '')}: "
                      f"{base:.1f} → {cur:.1f} ({d:+.1f})")
            for cat, d, cur, base in best:
                print(f"  {GREEN('▲')} {cat} {CATEGORY_NAMES.get(cat, '')}: "
                      f"{base:.1f} → {cur:.1f} ({d:+.1f})")
            print()
    # Finding counts by severity
    counts = {"high": 0, "medium": 0, "low": 0}
    for f in parsed["findings"]:
        sev = f["severity"]
        if sev in ("critical", "severe", "high"):
            counts["high"] += 1
        elif sev in ("major", "medium"):
            counts["medium"] += 1
        else:
            counts["low"] += 1
    total = sum(counts.values())
    print(BOLD(f"Findings ({total}):"))
    print(f"  {RED('high')}:   {counts['high']}")
    print(f"  {YELLOW('medium')}: {counts['medium']}")
    print(f"  {CYAN('low')}:    {counts['low']}")
    return 0

def cmd_config_init(args) -> int:
    root = args.root
    ensure_dirs(root)
    dest = config_path(root)
    if dest.exists() and not args.force:
        print(f"config already exists at {_safe_rel(dest, root)}. use --force to overwrite.", file=sys.stderr)
        return 1
    # Find the template relative to this script.
    script_dir = Path(__file__).resolve().parent
    template = script_dir.parent / "templates" / "config.example.json"
    if not template.exists():
        print(f"template not found at {template}", file=sys.stderr); return 5
    shutil.copy2(template, dest)
    print(GREEN("config created"), _safe_rel(dest, root))
    print(DIM("  edit to override weights, ignore globs, disable rules, etc."))
    return 0

def cmd_config_show(args) -> int:
    root = args.root
    p = config_path(root)
    if not p.exists():
        print("no config. run 'rax config init' to create one.", file=sys.stderr); return 2
    print(p.read_text(encoding="utf-8"), end="")
    return 0

def cmd_version(args) -> int:
    print(f"rax {VERSION}")
    return 0

# ---------------------------------------------------------------------------
# Argparse wiring
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rax-core", description="rax core (internal)")
    p.add_argument("--root", type=Path, default=None)
    p.add_argument("--json", action="store_true", help="emit JSON alongside text")
    sub = p.add_subparsers(dest="cmd", required=True)

    # report ...
    p_rep = sub.add_parser("report")
    rep_sub = p_rep.add_subparsers(dest="sub", required=True)

    p_rs = rep_sub.add_parser("save")
    p_rs.add_argument("--file", type=Path, required=True)
    p_rs.add_argument("--commit", type=str, default=None)
    p_rs.add_argument("--mode", type=str, default=None)
    p_rs.set_defaults(func=cmd_report_save)

    rep_sub.add_parser("latest").set_defaults(func=cmd_report_latest)

    p_rpath = rep_sub.add_parser("path")
    p_rpath.add_argument("--id", required=True)
    p_rpath.set_defaults(func=cmd_report_path)

    p_rsh = rep_sub.add_parser("show")
    p_rsh.add_argument("--id", default=None)
    p_rsh.add_argument("--format", default="full",
                       choices=["full", "raw", "summary", "scores"])
    p_rsh.set_defaults(func=cmd_report_show)

    p_rh = rep_sub.add_parser("history")
    p_rh.add_argument("--limit", type=int, default=0)
    p_rh.set_defaults(func=cmd_report_history)

    # baseline ...
    p_b = sub.add_parser("baseline")
    b_sub = p_b.add_subparsers(dest="sub", required=True)

    p_bs = b_sub.add_parser("save")
    p_bs.add_argument("--id", default=None)
    p_bs.add_argument("--commit", default=None)
    p_bs.set_defaults(func=cmd_baseline_save)

    b_sub.add_parser("reset").set_defaults(func=cmd_baseline_reset)
    b_sub.add_parser("info").set_defaults(func=cmd_baseline_info)
    b_sub.add_parser("list").set_defaults(func=cmd_baseline_list)

    # score / scores / delta
    sub.add_parser("score").set_defaults(func=cmd_score)
    sub.add_parser("scores").set_defaults(func=cmd_scores)
    sub.add_parser("delta").set_defaults(func=cmd_delta)

    # findings ...
    p_f = sub.add_parser("findings")
    f_sub = p_f.add_subparsers(dest="sub", required=True)

    p_fp = f_sub.add_parser("pending")
    p_fp.add_argument("--category", default=None)
    p_fp.add_argument("--severity", default=None)
    p_fp.add_argument("--limit", type=int, default=0)
    p_fp.set_defaults(func=cmd_findings_pending)

    p_ff = f_sub.add_parser("fixed")
    p_ff.add_argument("--category", default=None)
    p_ff.add_argument("--severity", default=None)
    p_ff.set_defaults(func=cmd_findings_fixed)

    p_fn = f_sub.add_parser("new")
    p_fn.add_argument("--category", default=None)
    p_fn.add_argument("--severity", default=None)
    p_fn.set_defaults(func=cmd_findings_new)

    # config ...
    p_c = sub.add_parser("config")
    c_sub = p_c.add_subparsers(dest="sub", required=True)
    p_ci = c_sub.add_parser("init")
    p_ci.add_argument("--force", action="store_true")
    p_ci.set_defaults(func=cmd_config_init)
    c_sub.add_parser("show").set_defaults(func=cmd_config_show)

    # version
    sub.add_parser("version").set_defaults(func=cmd_version)

    return p

def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.root = args.root if args.root else repo_root(Path.cwd())
    return args.func(args)

if __name__ == "__main__":
    # Allow piping to head/less without a BrokenPipeError traceback.
    # Not available on Windows; guard accordingly.
    import signal as _signal
    if hasattr(_signal, "SIGPIPE"):
        _signal.signal(_signal.SIGPIPE, _signal.SIG_DFL)
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        # Re-open stderr to prevent a second traceback on exit.
        try:
            sys.stdout = open(os.devnull, "w")
        except Exception:
            pass
        sys.exit(0)

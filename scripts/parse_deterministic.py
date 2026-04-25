"""Parse outputs of the deterministic-layer tools and aggregate to one JSON.

Read by `scripts/deterministic_layer.sh`. Outputs to a path passed via
`--output`. Schema:

    {
      "by_iso_subcharacteristic": {
        "ISO_SEC_CONF": {
          "findings": [
            {"iso_sub_id": "ISO_SEC_CONF",
             "tool": "semgrep",
             "rule_id": "...",
             "file": "src/...",
             "line": 42,
             "severity": "high|medium|low",
             "message": "...",
             "fix_hint": ""},
            ...
          ],
          "deterministic_score": 7.4,
          "confidence": "high"
        },
        ...
      },
      "tools_run":    ["semgrep", "eslint", ...],
      "tools_failed": [{"tool": "tsc", "reason": "no_tsconfig"}, ...]
    }

Score formula: start at 10.0, subtract per-finding penalty (high=1.5,
medium=0.7, low=0.3), floor at 1.0. Confidence is the bucket of the
sub-char's coverage_alpha from `references/deterministic-coverage.md`:
    α >= 0.7 -> high
    0.4 <= α < 0.7 -> medium
    α < 0.4 -> low
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# Static map: rule_id pattern -> ISO sub-characteristic.
# Order matters — first match wins.
RULE_TO_ISO_PATTERNS: list[tuple[re.Pattern, str]] = [
    # ---- security ----
    (re.compile(r"(secret|hardcoded[-_]?(api[-_]?key|token|password)|gitleaks|trufflehog)", re.I), "ISO_SEC_CONF"),
    (re.compile(r"(react/no-danger|dangerouslysetinnerhtml|xss|html-injection|html-sanitization)", re.I), "ISO_SEC_INT"),
    (re.compile(r"(sql[-_]?injection|command[-_]?injection|eval|new[-_]?function)", re.I), "ISO_SEC_INT"),
    (re.compile(r"(insecure[-_]?random|crypto|tls|ssl|certificate|http-url)", re.I), "ISO_SEC_RES"),
    (re.compile(r"(jwt|oauth|session|csrf|auth|login)", re.I), "ISO_SEC_AUTH"),
    (re.compile(r"(audit[-_]?log|user[-_]?context|sentry)", re.I), "ISO_SEC_ACC"),
    (re.compile(r"(deeplink|webview|allowurltype|originwhitelist)", re.I), "ISO_SEC_RES"),
    (re.compile(r"(asyncstorage|localstorage|sensitive[-_]?data)", re.I), "ISO_SEC_CONF"),
    (re.compile(r"^npm[-_]audit|^cve|^advisor", re.I), "ISO_SEC_RES"),
    # ---- reliability / faultlessness ----
    (re.compile(r"react-hooks/(rules-of-hooks|exhaustive-deps)", re.I), "ISO_REL_FAULT"),
    (re.compile(r"(no-floating-promises|no-misused-promises|require-await)", re.I), "ISO_REL_FAULT"),
    (re.compile(r"(no-unsafe-(any|argument|call|return|member-access)|no-explicit-any)", re.I), "ISO_REL_FAULT"),
    (re.compile(r"^TS\d{4}", re.I), "ISO_REL_FAULT"),  # TypeScript error codes
    (re.compile(r"(error[-_]?boundary|errorboundary)", re.I), "ISO_REL_FT"),
    (re.compile(r"(retry|backoff|circuit[-_]?breaker)", re.I), "ISO_REL_FT"),
    # ---- performance ----
    (re.compile(r"(react-perf|no-array-index-key|memo|usecallback|usememo)", re.I), "ISO_PERF_TIME"),
    (re.compile(r"(react-native/no-inline-styles|no-color-literals)", re.I), "ISO_PERF_TIME"),
    (re.compile(r"(bundle[-_]?size|large[-_]?import|moment|lodash[-_]?full)", re.I), "ISO_PERF_RES"),
    (re.compile(r"(image[-_]?size|fastimage|expo[-_]?image)", re.I), "ISO_PERF_RES"),
    (re.compile(r"(scrollview[-_]?with[-_]?map|flatlist|virtual)", re.I), "ISO_PERF_CAP"),
    # ---- maintainability ----
    (re.compile(r"^circular($|[-_])"), "ISO_MAINT_MOD"),
    (re.compile(r"(boundaries|import/no-cycle|import/no-relative-parent-imports)", re.I), "ISO_MAINT_MOD"),
    (re.compile(r"(complexity|max-(depth|lines|params|nested))", re.I), "ISO_MAINT_ANAL"),
    (re.compile(r"(jscpd|duplicate|copy-paste)", re.I), "ISO_MAINT_REUSE"),
    (re.compile(r"(prop-drilling|state-machine|exhaustive-deps)", re.I), "ISO_MAINT_MOD2"),
    (re.compile(r"(testing-library|test-file|coverage)", re.I), "ISO_MAINT_TEST"),
    # ---- interaction capability ----
    (re.compile(r"jsx-a11y/", re.I), "ISO_INTER_INC"),
    (re.compile(r"react-native-a11y", re.I), "ISO_INTER_INC"),
    (re.compile(r"(focus-visible|focus-trap|keyboard|tab[-_]?index)", re.I), "ISO_INTER_OP"),
    (re.compile(r"(touch[-_]?target|hit[-_]?slop)", re.I), "ISO_INTER_OP"),
    (re.compile(r"(zod|yup|valibot|runtime[-_]?validation|form-validation)", re.I), "ISO_INTER_UEP"),
    # ---- compatibility / flexibility ----
    (re.compile(r"(peer[-_]?dep|engines|platform[-_]?select)", re.I), "ISO_COMP_COEX"),
    (re.compile(r"(openapi|graphql[-_]?codegen|contract)", re.I), "ISO_COMP_INTER"),
    (re.compile(r"(responsive|breakpoint|safe-?area|theme[-_]?token)", re.I), "ISO_FLEX_ADAPT"),
    (re.compile(r"(code[-_]?split|lazy[-_]?load|dynamic[-_]?import)", re.I), "ISO_FLEX_SCAL"),
    (re.compile(r"(vendor[-_]?lock|firebase[-_]?import)", re.I), "ISO_FLEX_REPL"),
]


# Default sub-char mapping when a tool can be reasonably bucketed wholesale.
TOOL_DEFAULT_ISO: dict[str, str] = {
    "semgrep": "ISO_SEC_INT",        # most semgrep oss rules in p/javascript / p/react are security
    "eslint": "ISO_MAINT_ANAL",      # general code-quality bucket
    "tsc": "ISO_REL_FAULT",
    "madge": "ISO_MAINT_MOD",
    "jscpd": "ISO_MAINT_REUSE",
    "npm_audit": "ISO_SEC_RES",
}


# Coverage α from references/deterministic-coverage.md (kept here so the
# parser is self-contained — duplicates the doc but cheap to keep in sync
# because IDs and α move together).
COVERAGE_ALPHA: dict[str, float] = {
    "ISO_FUN_COMP": 0.0,  "ISO_FUN_CORR": 0.3,  "ISO_FUN_APPR": 0.0,  "ISO_FUN_IDEN": 0.1,
    "ISO_PERF_TIME": 0.7, "ISO_PERF_RES": 0.8,  "ISO_PERF_CAP": 0.5,
    "ISO_COMP_COEX": 0.5, "ISO_COMP_INTER": 0.6,
    "ISO_INTER_REC": 0.2, "ISO_INTER_LEARN": 0.15, "ISO_INTER_OP": 0.75,
    "ISO_INTER_UEP": 0.7, "ISO_INTER_ENG": 0.2,    "ISO_INTER_INC": 0.75,
    "ISO_INTER_UAA": 0.4, "ISO_INTER_SD": 0.4,
    "ISO_REL_FAULT": 0.75, "ISO_REL_AVAIL": 0.0, "ISO_REL_FT": 0.7, "ISO_REL_REC": 0.5,
    "ISO_SEC_CONF": 0.85, "ISO_SEC_INT": 0.75, "ISO_SEC_NR": 0.1,
    "ISO_SEC_ACC": 0.4, "ISO_SEC_AUTH": 0.65, "ISO_SEC_RES": 0.55,
    "ISO_MAINT_MOD": 0.75, "ISO_MAINT_REUSE": 0.6, "ISO_MAINT_ANAL": 0.8,
    "ISO_MAINT_MOD2": 0.7, "ISO_MAINT_TEST": 0.75,
    "ISO_FLEX_ADAPT": 0.55, "ISO_FLEX_SCAL": 0.5, "ISO_FLEX_INST": 0.15, "ISO_FLEX_REPL": 0.45,
    "ISO_SAFE_OP": 0.15, "ISO_SAFE_RISK": 0.1, "ISO_SAFE_FS": 0.6,
    "ISO_SAFE_HW": 0.1, "ISO_SAFE_SI": 0.55,
}

ALL_SUBCHARS = sorted(COVERAGE_ALPHA.keys())

SEVERITY_PENALTY = {"high": 1.5, "medium": 0.7, "low": 0.3}
SCORE_FLOOR = 1.0
SCORE_CEILING = 10.0


# ---------- helpers ----------

def map_rule_to_iso(rule_id: str, tool: str) -> str:
    """Resolve a rule_id to an ISO_<CHAR>_<SUB> bucket."""
    rule_id = rule_id or ""
    for pat, iso in RULE_TO_ISO_PATTERNS:
        if pat.search(rule_id):
            return iso
    return TOOL_DEFAULT_ISO.get(tool, "ISO_MAINT_ANAL")


def normalize_severity(value: Any) -> str:
    """Map varied severity strings to {high, medium, low}."""
    if value is None:
        return "medium"
    s = str(value).lower()
    if s in {"error", "high", "critical", "blocker", "2"}:
        return "high"
    if s in {"warning", "warn", "medium", "moderate", "1"}:
        return "medium"
    if s in {"info", "low", "minor", "note", "0"}:
        return "low"
    return "medium"


def confidence_from_alpha(alpha: float) -> str:
    if alpha >= 0.7:
        return "high"
    if alpha >= 0.4:
        return "medium"
    return "low"


def score_from_findings(findings: List[Dict[str, Any]]) -> float:
    if not findings:
        return SCORE_CEILING
    penalty = sum(SEVERITY_PENALTY.get(f.get("severity", "medium"), 0.7) for f in findings)
    score = SCORE_CEILING - penalty
    return max(SCORE_FLOOR, min(SCORE_CEILING, round(score, 2)))


# ---------- per-tool parsers ----------

_MAX_TOOL_OUTPUT_BYTES = 50 * 1024 * 1024  # 50 MB — semgrep on big monorepos can blow past this


def _read_json(path: Optional[str]) -> Optional[Any]:
    if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    if os.path.getsize(path) > _MAX_TOOL_OUTPUT_BYTES:
        sys.stderr.write(
            f"rax/parse_deterministic: {path} exceeds {_MAX_TOOL_OUTPUT_BYTES} bytes; "
            "skipping to avoid OOM. Re-run the upstream tool with tighter scope.\n"
        )
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def parse_semgrep(path: Optional[str]) -> List[Dict[str, Any]]:
    data = _read_json(path)
    out: list[dict] = []
    if not data or "results" not in data:
        return out
    for r in data.get("results", []):
        rule_id = r.get("check_id", "")
        extra = r.get("extra", {}) or {}
        # Prefer the rule's declared `metadata.iso_sub_id` (custom rax
        # rules set this explicitly). Fall back to the regex mapper for
        # OSS rulesets (p/javascript, p/react, p/owasp-top-ten) where we
        # don't control the YAML.
        # Defensive isinstance-guard: third-party rule packs sometimes ship
        # metadata as a non-dict (e.g., a free-form string), which would
        # crash a naive `.get()`.
        metadata = extra.get("metadata") if isinstance(extra.get("metadata"), dict) else {}
        meta_sub = metadata.get("iso_sub_id")
        sub_id = (
            meta_sub
            if isinstance(meta_sub, str) and meta_sub.startswith("ISO_")
            else map_rule_to_iso(rule_id, "semgrep")
        )
        # `extra.fix` can be either a string (semgrep classic) or a dict
        # with `{message, lines}` (semgrep extended output). Slicing a dict
        # raises TypeError; coerce to "" when it's not a string.
        fix_raw = extra.get("fix")
        fix_hint = fix_raw[:200] if isinstance(fix_raw, str) else ""
        out.append({
            "iso_sub_id": sub_id,
            "tool": "semgrep",
            "rule_id": rule_id,
            "file": r.get("path", ""),
            "line": (r.get("start") or {}).get("line", 0),
            "severity": normalize_severity(extra.get("severity")),
            "message": extra.get("message", ""),
            "fix_hint": fix_hint,
        })
    return out


def parse_eslint(path: Optional[str]) -> List[Dict[str, Any]]:
    data = _read_json(path)
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for file_entry in data:
        file_path = file_entry.get("filePath", "")
        for msg in file_entry.get("messages", []) or []:
            rule_id = msg.get("ruleId") or "eslint-builtin"
            sev = msg.get("severity")
            out.append({
                "iso_sub_id": map_rule_to_iso(rule_id, "eslint"),
                "tool": "eslint",
                "rule_id": rule_id,
                "file": file_path,
                "line": msg.get("line", 0),
                "severity": normalize_severity(sev),
                "message": msg.get("message", ""),
                "fix_hint": (msg.get("fix") or {}).get("text", "") if isinstance(msg.get("fix"), dict) else "",
            })
    return out


_TSC_RE = re.compile(r"^(?P<file>[^:]+)\((?P<line>\d+),\d+\):\s*error\s+(?P<code>TS\d+):\s*(?P<msg>.*)$")
_TSC_RE_ALT = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):\d+\s*-\s*error\s+(?P<code>TS\d+):\s*(?P<msg>.*)$")


def parse_tsc(path: Optional[str]) -> List[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return []
    out: list[dict] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.rstrip()
                m = _TSC_RE.match(line) or _TSC_RE_ALT.match(line)
                if not m:
                    continue
                out.append({
                    "iso_sub_id": "ISO_REL_FAULT",
                    "tool": "tsc",
                    "rule_id": m.group("code"),
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "severity": "high",
                    "message": m.group("msg"),
                    "fix_hint": "",
                })
    except OSError:
        pass
    return out


def parse_madge(path: Optional[str]) -> List[Dict[str, Any]]:
    data = _read_json(path)
    out: list[dict] = []
    cycles = []
    if isinstance(data, list):
        cycles = data
    elif isinstance(data, dict) and isinstance(data.get("circular"), list):
        cycles = data["circular"]
    for cycle in cycles:
        if not cycle:
            continue
        out.append({
            "iso_sub_id": "ISO_MAINT_MOD",
            "tool": "madge",
            "rule_id": "circular-dependency",
            "file": cycle[0] if isinstance(cycle, list) else "",
            "line": 0,
            "severity": "high",
            "message": " -> ".join(cycle) if isinstance(cycle, list) else str(cycle),
            "fix_hint": "Break the cycle by extracting shared deps to a leaf module",
        })
    return out


def parse_jscpd(path: Optional[str]) -> List[Dict[str, Any]]:
    data = _read_json(path)
    if not isinstance(data, dict):
        return []
    out: list[dict] = []
    for dup in data.get("duplicates", []) or []:
        first = dup.get("firstFile") or {}
        out.append({
            "iso_sub_id": "ISO_MAINT_REUSE",
            "tool": "jscpd",
            "rule_id": "duplicate-code",
            "file": first.get("name", ""),
            "line": first.get("start", 0),
            "severity": "medium",
            "message": f"Duplicated block ({dup.get('lines', '?')} lines)",
            "fix_hint": "Extract the shared block to a reusable function/component",
        })
    return out


def parse_audit(path: Optional[str]) -> List[Dict[str, Any]]:
    data = _read_json(path)
    if not isinstance(data, dict):
        return []
    out: list[dict] = []
    vulns = data.get("vulnerabilities") or {}
    if isinstance(vulns, dict):
        for name, info in vulns.items():
            if not isinstance(info, dict):
                continue
            sev = info.get("severity") or "medium"
            out.append({
                "iso_sub_id": "ISO_SEC_RES",
                "tool": "npm_audit",
                "rule_id": f"cve:{name}",
                "file": "package-lock.json",
                "line": 0,
                "severity": normalize_severity(sev),
                "message": f"Vulnerable dependency: {name} ({sev})",
                "fix_hint": "Run `npm audit fix` or update the affected package",
            })
    return out


# ---------- aggregation ----------

def aggregate(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_sub: Dict[str, Dict[str, Any]] = {
        sub: {"findings": [], "deterministic_score": SCORE_CEILING,
              "confidence": confidence_from_alpha(COVERAGE_ALPHA.get(sub, 0.0))}
        for sub in ALL_SUBCHARS
    }
    for f in findings:
        sub = f.get("iso_sub_id") or "ISO_MAINT_ANAL"
        if sub not in by_sub:
            by_sub[sub] = {
                "findings": [],
                "deterministic_score": SCORE_CEILING,
                "confidence": confidence_from_alpha(COVERAGE_ALPHA.get(sub, 0.0)),
            }
        by_sub[sub]["findings"].append(f)

    for sub, entry in by_sub.items():
        entry["deterministic_score"] = score_from_findings(entry["findings"])

    return by_sub


# ---------- main ----------

def _parse_csv(value: str) -> List[str]:
    return [v for v in (value or "").split(",") if v]


def _parse_failed(value: str) -> List[Dict[str, str]]:
    out: list[dict] = []
    for entry in (value or "").split("|"):
        entry = entry.strip()
        if not entry:
            continue
        if "\t" in entry:
            tool, reason = entry.split("\t", 1)
        else:
            tool, reason = entry, ""
        out.append({"tool": tool, "reason": reason})
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--semgrep")
    ap.add_argument("--eslint")
    ap.add_argument("--tsc")
    ap.add_argument("--madge")
    ap.add_argument("--jscpd")
    ap.add_argument("--audit")
    ap.add_argument("--tools-run", default="")
    ap.add_argument("--tools-failed", default="")
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)

    findings: list[dict] = []
    findings.extend(parse_semgrep(args.semgrep))
    findings.extend(parse_eslint(args.eslint))
    findings.extend(parse_tsc(args.tsc))
    findings.extend(parse_madge(args.madge))
    findings.extend(parse_jscpd(args.jscpd))
    findings.extend(parse_audit(args.audit))

    output = {
        "by_iso_subcharacteristic": aggregate(findings),
        "tools_run": _parse_csv(args.tools_run),
        "tools_failed": _parse_failed(args.tools_failed),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

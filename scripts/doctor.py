"""rax doctor — verify the local install.

Checks Python / Bash / tools / API keys / corpus / conformalizer presence.
Exits 0 if all CRITICAL checks pass, 1 otherwise. Optional checks (like
unset OPENAI_API_KEY when only ANTHROPIC_API_KEY is configured) print a
warning but do not fail.

Usage:
    python scripts/doctor.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

OK = "\033[32m✓\033[0m" if sys.stdout.isatty() else "[ok]"
FAIL = "\033[31m✗\033[0m" if sys.stdout.isatty() else "[fail]"
WARN = "\033[33m!\033[0m" if sys.stdout.isatty() else "[warn]"


def _print(level: str, msg: str) -> None:
    print(f"  {level} {msg}")


def _run(cmd: List[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return ""


def check_python() -> Tuple[bool, bool]:
    """Returns (passed, critical)."""
    v = sys.version_info
    if v >= (3, 8):
        _print(OK, f"Python {v.major}.{v.minor}.{v.micro}")
        return True, True
    _print(FAIL, f"Python {v.major}.{v.minor} — need ≥ 3.8")
    return False, True


def check_bash() -> Tuple[bool, bool]:
    out = _run(["bash", "--version"])
    m = re.search(r"version\s+(\d+)", out)
    if m and int(m.group(1)) >= 4:
        _print(OK, out.splitlines()[0])
        return True, True
    if out:
        _print(WARN, f"bash detected but version < 4 (or unparseable): {out.splitlines()[0]}")
        return True, False
    _print(FAIL, "bash not found")
    return False, True


def check_tool(name: str, version_arg: str = "--version", critical: bool = False) -> Tuple[bool, bool]:
    bin_path = shutil.which(name) or shutil.which(name.replace("_", "-"))
    if not bin_path:
        local_path = REPO_ROOT / "node_modules" / ".bin" / name
        if local_path.exists():
            bin_path = str(local_path)
    if not bin_path:
        msg = f"{name} not found" + ("" if critical else " (optional)")
        _print(FAIL if critical else WARN, msg)
        return False, critical
    out = _run([bin_path, version_arg])
    head = (out.splitlines() or [""])[0]
    _print(OK, f"{name} {head or '(version unreadable)'}")
    return True, critical


def check_env(name: str, critical: bool = False, hint: str = "") -> Tuple[bool, bool]:
    if os.environ.get(name):
        _print(OK, f"{name} set")
        return True, critical
    msg = f"{name} not set"
    if hint:
        msg += f" — {hint}"
    _print(FAIL if critical else WARN, msg)
    return False, critical


def check_corpus() -> Tuple[bool, bool]:
    anchors = REPO_ROOT / "tests" / "corpus" / "synthetic_anchors"
    mined = REPO_ROOT / "tests" / "corpus" / "mined"
    n_anchors = sum(1 for p in anchors.iterdir() if p.is_dir()) if anchors.exists() else 0
    n_mined = len(list(mined.glob("*.json"))) if mined.exists() else 0
    if n_anchors >= 60 and n_mined >= 50:
        _print(OK, f"Corpus: {n_anchors} synthetic anchors + {n_mined} mined repos")
        return True, True
    _print(WARN, f"Corpus partial: {n_anchors} anchors / {n_mined} mined (target ≥60 / ≥50)")
    return n_anchors > 0 and n_mined > 0, True


def check_conformalizer() -> Tuple[bool, bool]:
    cal = REPO_ROOT / "tests" / "results" / "conformal_calibration.json"
    if not cal.exists():
        _print(WARN, "conformalizer not trained — run `python scripts/conformal.py --calibrate`")
        return False, False
    import json
    from datetime import datetime, timezone
    try:
        data = json.loads(cal.read_text())
        fitted_at = data.get("fitted_at")
        if fitted_at:
            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(fitted_at)).days
            _print(OK, f"Conformalizer trained ({age_days} days ago)")
        else:
            _print(OK, "Conformalizer trained (date unknown)")
    except (json.JSONDecodeError, ValueError):
        _print(FAIL, "conformalizer file is not valid JSON")
        return False, True
    return True, True


def check_python_deps() -> Tuple[bool, bool]:
    required = ["numpy", "yaml", "jsonschema"]
    optional = ["mapie", "anthropic", "openai", "google.generativeai"]
    all_ok = True
    for name in required:
        try:
            __import__(name)
            _print(OK, f"python: {name}")
        except ImportError:
            _print(FAIL, f"python: {name} missing")
            all_ok = False
    for name in optional:
        try:
            __import__(name)
            _print(OK, f"python: {name} (optional)")
        except ImportError:
            _print(WARN, f"python: {name} not installed (optional)")
    return all_ok, True


def main() -> int:
    print("rax doctor — install diagnostics\n")

    checks: List[Tuple[bool, bool]] = []

    print("Runtime:")
    checks.append(check_python())
    checks.append(check_bash())

    print("\nPython packages:")
    checks.append(check_python_deps())

    print("\nDeterministic tools:")
    checks.append(check_tool("semgrep", critical=False))
    checks.append(check_tool("eslint", critical=False))
    checks.append(check_tool("tsc", critical=False))
    checks.append(check_tool("madge", critical=False))
    checks.append(check_tool("jscpd", critical=False))
    checks.append(check_tool("npm", critical=False))

    print("\nLLM API keys:")
    checks.append(check_env("ANTHROPIC_API_KEY", critical=False,
                            hint="get from console.anthropic.com"))
    checks.append(check_env("OPENAI_API_KEY", critical=False,
                            hint="get from platform.openai.com"))
    checks.append(check_env("GOOGLE_API_KEY", critical=False,
                            hint="get from console.cloud.google.com"))

    print("\nCorpus + calibration:")
    checks.append(check_corpus())
    checks.append(check_conformalizer())

    crit_failed = sum(1 for passed, critical in checks if critical and not passed)
    optional_failed = sum(1 for passed, critical in checks if not critical and not passed)

    print("\nSummary:")
    print(f"  Critical: {crit_failed} failed")
    print(f"  Optional: {optional_failed} failed/missing")
    print(f"  Status: {'OK' if crit_failed == 0 else 'CRITICAL'}")

    return 0 if crit_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

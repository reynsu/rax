"""Calibration drift check.

Loads the persisted conformal calibration, recomputes empirical coverage
on the current rax corpus, and exits 1 if it has drifted out of the
[0.85, 0.95] target band.

Run on every CI release.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

# Allow running as `python scripts/validate_calibration.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.conformal import (  # noqa: E402
    CALIBRATION_FILE,
    RaxConformalizer,
    assemble_calibration_set,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "tests" / "results"

LOWER = 0.85
UPPER = 0.95


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", type=Path, default=CALIBRATION_FILE)
    ap.add_argument("--lower", type=float, default=LOWER)
    ap.add_argument("--upper", type=float, default=UPPER)
    args = ap.parse_args(argv)

    cz = RaxConformalizer.load(args.calibration)
    if cz is None:
        print(f"no calibration at {args.calibration}; run conformal.py --calibrate", file=sys.stderr)
        return 2

    cal = assemble_calibration_set()
    if not cal:
        print("no corpus to validate against", file=sys.stderr)
        return 2

    cov = cz.empirical_coverage(cal)
    out = RESULTS_DIR / f"calibration_drift_{date.today().isoformat()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "empirical_coverage": round(cov, 4),
        "target_band": [args.lower, args.upper],
        "in_band": args.lower <= cov <= args.upper,
        "calibration_size": sum(len(v) for v in cal.values()),
        "fitted_at": cz.fitted_at,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2))

    if not payload["in_band"]:
        print(
            f"calibration drift: coverage {cov:.4f} outside "
            f"[{args.lower}, {args.upper}]",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

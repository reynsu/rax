"""Phase 1 milestone demo: same simulated codebase scored under 5 profiles.

Visualizes that profile weights matter — the same per-sub-char scores
produce noticeably different overall scores when filtered through
consumer-app vs fintech vs internal-tool vs accessibility-critical
vs default.

Run from repo root:
    python demos/phase1_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.aggregation import (
    QuamocoAggregator,
    linear_utility,
    sigmoid_penalty_utility,
)
from scripts.profiles import list_profiles, load_profile

# ---- simulated codebase: a consumer app with weak a11y, ok security ----

SIMULATED = {
    # Security: ok-but-not-great
    "ISO_SEC_CONF": 5,
    "ISO_SEC_INT": 6,
    "ISO_SEC_AUTH": 5,
    "ISO_SEC_RES": 6,
    "ISO_SEC_NR": 7,
    "ISO_SEC_ACC": 6,
    # Reliability: medium
    "ISO_REL_FAULT": 6,
    "ISO_REL_FT": 5,
    "ISO_REL_REC": 6,
    "ISO_REL_AVAIL": 7,
    # Performance: strong
    "ISO_PERF_TIME": 8,
    "ISO_PERF_RES": 7,
    "ISO_PERF_CAP": 8,
    # Interaction Capability: notably weak (a11y deficit)
    "ISO_INTER_OP": 4,
    "ISO_INTER_INC": 3,
    "ISO_INTER_UEP": 5,
    "ISO_INTER_REC": 5,
    "ISO_INTER_LEARN": 5,
    "ISO_INTER_ENG": 6,
    "ISO_INTER_UAA": 5,
    "ISO_INTER_SD": 6,
    # Maintainability: strong (well-engineered codebase)
    "ISO_MAINT_MOD": 8,
    "ISO_MAINT_REUSE": 7,
    "ISO_MAINT_ANAL": 8,
    "ISO_MAINT_MOD2": 7,
    "ISO_MAINT_TEST": 7,
    # filler (low signal)
    "ISO_FUN_CORR": 6, "ISO_FUN_COMP": 5, "ISO_FUN_APPR": 6, "ISO_FUN_IDEN": 5,
    "ISO_COMP_COEX": 7, "ISO_COMP_INTER": 6,
    "ISO_FLEX_ADAPT": 6, "ISO_FLEX_SCAL": 7, "ISO_FLEX_INST": 6, "ISO_FLEX_REPL": 6,
    "ISO_SAFE_OP": 5, "ISO_SAFE_RISK": 5, "ISO_SAFE_FS": 6,
    "ISO_SAFE_HW": 5, "ISO_SAFE_SI": 6,
}

CHAR_TO_SUBCHARS = {
    "functional_suitability": ["ISO_FUN_CORR", "ISO_FUN_COMP", "ISO_FUN_APPR", "ISO_FUN_IDEN"],
    "performance_efficiency": ["ISO_PERF_TIME", "ISO_PERF_RES", "ISO_PERF_CAP"],
    "compatibility": ["ISO_COMP_COEX", "ISO_COMP_INTER"],
    "interaction_capability": [
        "ISO_INTER_OP", "ISO_INTER_INC", "ISO_INTER_UEP", "ISO_INTER_REC",
        "ISO_INTER_LEARN", "ISO_INTER_ENG", "ISO_INTER_UAA", "ISO_INTER_SD",
    ],
    "reliability": ["ISO_REL_FAULT", "ISO_REL_FT", "ISO_REL_REC", "ISO_REL_AVAIL"],
    "security": ["ISO_SEC_CONF", "ISO_SEC_INT", "ISO_SEC_AUTH",
                 "ISO_SEC_RES", "ISO_SEC_NR", "ISO_SEC_ACC"],
    "maintainability": ["ISO_MAINT_MOD", "ISO_MAINT_REUSE", "ISO_MAINT_ANAL",
                        "ISO_MAINT_MOD2", "ISO_MAINT_TEST"],
    "flexibility": ["ISO_FLEX_ADAPT", "ISO_FLEX_SCAL", "ISO_FLEX_INST", "ISO_FLEX_REPL"],
    "safety": ["ISO_SAFE_OP", "ISO_SAFE_RISK", "ISO_SAFE_FS", "ISO_SAFE_HW", "ISO_SAFE_SI"],
}


def aggregator_for(profile):
    overrides = {}
    for sid, name in (profile.get("utility_overrides") or {}).items():
        overrides[sid] = sigmoid_penalty_utility if name == "sigmoid" else linear_utility
    return QuamocoAggregator(utility_functions=overrides)


def score_codebase(profile, subscores):
    agg = aggregator_for(profile)
    cat_scores = {}
    for cname, sub_ids in CHAR_TO_SUBCHARS.items():
        present = {s: subscores[s] for s in sub_ids if s in subscores}
        if not present:
            continue
        uniform = {s: 1.0 / len(present) for s in present}
        cat_scores[cname] = agg.aggregate_to_category(present, uniform)
    overall = agg.aggregate_to_overall(cat_scores, profile["weights"])
    return cat_scores, overall


def _bar(value, width=30):
    filled = int(round((value / 10.0) * width))
    return "█" * filled + "·" * (width - filled)


def main():
    print("Phase 1 demo — same simulated codebase scored under 5 profiles\n")
    print("Simulated subscores: weak a11y (Inter ~4), strong Maintainability (~7),")
    print("medium Security (~5-6), strong Performance (~7-8).\n")

    rows = []
    for name in list_profiles():
        profile = load_profile(name)
        cat_scores, overall = score_codebase(profile, SIMULATED)
        rows.append((name, overall, cat_scores))

    rows.sort(key=lambda r: -r[1])

    width = max(len(n) for n, _, _ in rows)
    print(f"{'profile':<{width}}  overall  {'':30}")
    print("-" * (width + 2 + 8 + 30))
    for name, overall, _ in rows:
        print(f"{name:<{width}}  {overall:>5.2f}    {_bar(overall)}")

    print()
    spread = max(r[1] for r in rows) - min(r[1] for r in rows)
    print(f"Spread (max - min): {spread:.2f} on a [0,10] scale.")
    print(f"=> Profile choice changes the verdict by {spread:.2f} points "
          "for the same codebase.\n")

    print("Per-category breakdown for the most differentiated pair:")
    top_name, top_overall, top_cats = rows[0]
    bot_name, bot_overall, bot_cats = rows[-1]
    print(f"  {top_name}: overall {top_overall:.2f}")
    print(f"  {bot_name}: overall {bot_overall:.2f}\n")

    print(f"{'characteristic':<24} {top_name:>10} {bot_name:>22} {'Δ':>8}")
    print("-" * 70)
    for cname in sorted(top_cats):
        a, b = top_cats[cname], bot_cats[cname]
        print(f"{cname:<24} {a:>10.2f} {b:>22.2f} {a-b:>+8.2f}")


if __name__ == "__main__":
    main()

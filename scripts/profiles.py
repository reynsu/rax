"""Loader for stakeholder profiles defined in templates/profiles/*.yaml.

A profile bundles:
    - weights:           ISO characteristic name -> weight in [0, 1], Σ ≈ 1.0
    - utility_overrides: sub-char ID -> "linear" | "sigmoid"
    - red_flag_rules:    list of rules, each with cap_category + cap_at
    - description:       human-readable rationale
    - extends:           optional parent profile name for inheritance

The loader validates Σ(weights) ∈ [1 ± 0.01] after merging with the parent
(if any). Returns a plain dict — consumers (QuamocoAggregator, the audit
runner) decide how to apply weights and red flags.

The 9 ISO 25010:2023 characteristics expected as weight keys:
    functional_suitability, performance_efficiency, compatibility,
    interaction_capability, reliability, security, maintainability,
    flexibility, safety.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

# Resolve repo root: scripts/profiles.py -> repo root is two parents up
_REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = _REPO_ROOT / "templates" / "profiles"

ISO_CHARACTERISTICS = frozenset({
    "functional_suitability",
    "performance_efficiency",
    "compatibility",
    "interaction_capability",
    "reliability",
    "security",
    "maintainability",
    "flexibility",
    "safety",
})

WEIGHT_TOLERANCE = 0.01


class ProfileError(ValueError):
    """Raised when a profile fails validation."""


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "PyYAML required to load profiles — install with `pip install pyyaml`"
        ) from exc

    with open(path) as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ProfileError(f"profile {path.name}: top-level must be a mapping")
    return data


def _resolve_path(name: str, profiles_dir: Optional[Path] = None) -> Path:
    base = profiles_dir or PROFILES_DIR
    candidate = base / f"{name}.yaml"
    if not candidate.exists():
        raise FileNotFoundError(
            f"profile {name!r} not found at {candidate} "
            f"(known names: {sorted(p.stem for p in base.glob('*.yaml'))})"
        )
    return candidate


def _merge(parent: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
    """Child overrides parent. Empty dicts/lists in child are NOT considered
    overrides — they fall back to parent. Use null/None to explicitly clear."""
    merged: Dict[str, Any] = dict(parent)

    for key in ("weights", "utility_overrides"):
        child_val = child.get(key)
        if child_val:
            merged[key] = {**parent.get(key, {}), **child_val}
        elif key in parent:
            merged[key] = dict(parent[key])
        else:
            merged[key] = {}

    parent_rules = list(parent.get("red_flag_rules") or [])
    child_rules = child.get("red_flag_rules")
    if child_rules:
        # child rules with same id replace parent rules
        by_id = {r["id"]: r for r in parent_rules if "id" in r}
        for r in child_rules:
            if "id" in r:
                by_id[r["id"]] = r
            else:
                parent_rules.append(r)
        merged["red_flag_rules"] = list(by_id.values()) + [
            r for r in parent_rules if "id" not in r
        ]
    else:
        merged["red_flag_rules"] = parent_rules

    if "description" in child and child["description"]:
        merged["description"] = child["description"]
    elif "description" in parent:
        merged["description"] = parent["description"]

    return merged


def _validate(profile: Dict[str, Any], name: str) -> None:
    weights = profile.get("weights") or {}
    if not isinstance(weights, dict) or not weights:
        raise ProfileError(f"profile {name!r}: weights mapping is required")

    unknown = set(weights) - ISO_CHARACTERISTICS
    if unknown:
        raise ProfileError(
            f"profile {name!r}: unknown characteristic(s) in weights: {sorted(unknown)}. "
            f"Allowed: {sorted(ISO_CHARACTERISTICS)}"
        )

    total = sum(float(v) for v in weights.values())
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise ProfileError(
            f"profile {name!r}: weights sum to {total:.4f}, "
            f"must be 1.0 ± {WEIGHT_TOLERANCE}"
        )

    for cname, w in weights.items():
        if not (0.0 <= float(w) <= 1.0):
            raise ProfileError(
                f"profile {name!r}: weight for {cname} = {w} not in [0, 1]"
            )

    overrides = profile.get("utility_overrides") or {}
    for sub_id, fname in overrides.items():
        if fname not in ("linear", "sigmoid"):
            raise ProfileError(
                f"profile {name!r}: utility_overrides[{sub_id}] = {fname!r}, "
                "must be 'linear' or 'sigmoid'"
            )

    rules = profile.get("red_flag_rules") or []
    for rule in rules:
        if "cap_category" in rule:
            if rule["cap_category"] not in ISO_CHARACTERISTICS:
                raise ProfileError(
                    f"profile {name!r}: red_flag_rule cap_category "
                    f"{rule['cap_category']!r} is not a valid ISO characteristic"
                )
        if "cap_at" in rule:
            cap = rule["cap_at"]
            if not (isinstance(cap, (int, float)) and 0 <= cap <= 10):
                raise ProfileError(
                    f"profile {name!r}: red_flag_rule cap_at = {cap} not in [0, 10]"
                )


def load_profile(
    name: str = "default",
    profiles_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load and validate a stakeholder profile.

    Resolves `extends:` chain (max depth 5 to prevent cycles).
    Validates Σ(weights) ≈ 1.0, allowed characteristic names, utility
    override values, and red flag rule shapes.

    Returns the merged-and-validated dict.
    """
    base_dir = profiles_dir or PROFILES_DIR
    seen: list[str] = []
    current_name = name
    chain: list[Dict[str, Any]] = []

    while True:
        if current_name in seen:
            raise ProfileError(
                f"profile inheritance cycle: {' -> '.join(seen + [current_name])}"
            )
        if len(seen) > 5:
            raise ProfileError(
                f"profile inheritance chain too deep (>5): {seen}"
            )
        seen.append(current_name)
        path = _resolve_path(current_name, base_dir)
        cfg = _load_yaml(path)
        chain.append(cfg)
        parent = cfg.get("extends")
        if not parent:
            break
        current_name = parent

    merged: Dict[str, Any] = {}
    for cfg in reversed(chain):
        merged = _merge(merged, cfg)

    merged.pop("extends", None)
    _validate(merged, name)
    return merged


def list_profiles(profiles_dir: Optional[Path] = None) -> list[str]:
    base = profiles_dir or PROFILES_DIR
    return sorted(p.stem for p in base.glob("*.yaml"))

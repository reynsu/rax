"""Quamoco-style aggregation with Multi-Attribute Utility Theory (MAUT).

Replaces v1's linear weighted-mean aggregation with utility functions per
sub-characteristic, allowing critical sub-characteristics (e.g. Security
Confidentiality) to dominate via non-linear penalties.

Math:
    U(s)             utility function per sub-characteristic, [0,10] -> [0,1]
    U_cat(category)  weighted mean of U(s_i), scaled back to [0,10]
    U_overall        weighted mean of category scores, on [0,10]

Defaults match `references/iso25010-mapping.md`:
    - Sub-chars in DEFAULT_CRITICAL_SUBCHARS use sigmoid penalty utility.
    - All other sub-chars use linear utility.
    - Overall aggregation is linear over category scores (categories already
      embed the per-sub-char penalties).

Standalone module: does not import from rax_core; safe to add as a layer.
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, Optional

import numpy as np


DEFAULT_CRITICAL_SUBCHARS: frozenset = frozenset({
    "ISO_SEC_CONF",   # Confidentiality — data leakage risk
    "ISO_SEC_AUTH",   # Authenticity — identity spoofing
    "ISO_REL_FAULT",  # Faultlessness — crash / type defects
    "ISO_SAFE_FS",    # Fail Safe — unsafe failure states
})


SIGMOID_DEFAULT_K: float = 1.5
SIGMOID_DEFAULT_MID: float = 5.0


def linear_utility(score: float) -> float:
    """U(s) = s/10, clamped to [0,1]."""
    s = float(score)
    if s < 0.0:
        return 0.0
    if s > 10.0:
        return 1.0
    return s / 10.0


def sigmoid_penalty_utility(
    score: float,
    k: float = SIGMOID_DEFAULT_K,
    mid: float = SIGMOID_DEFAULT_MID,
) -> float:
    """U(s) = 1 / (1 + exp(-k * (s - mid))), saturating in (0, 1).

    Penalizes low scores hard for critical sub-characteristics: at s=2,
    U≈0.011; at s=8, U≈0.989. Symmetric around `mid`.
    """
    return float(1.0 / (1.0 + np.exp(-k * (float(score) - mid))))


class QuamocoAggregator:
    """Quamoco/MAUT aggregator for ISO 25010 sub-characteristic scores.

    All inputs assumed on [0, 10]; outputs also on [0, 10].

    Args:
        critical_subchars: sub-char IDs that should use sigmoid penalty by
            default. None -> use DEFAULT_CRITICAL_SUBCHARS.
        utility_functions: explicit per-sub-char overrides. Wins over the
            critical/non-critical default. Maps sub-char ID -> Callable.
    """

    def __init__(
        self,
        critical_subchars: Optional[Iterable[str]] = None,
        utility_functions: Optional[Dict[str, Callable[[float], float]]] = None,
    ) -> None:
        self.critical_subchars = (
            set(critical_subchars)
            if critical_subchars is not None
            else set(DEFAULT_CRITICAL_SUBCHARS)
        )
        self.utility_functions: Dict[str, Callable[[float], float]] = dict(
            utility_functions or {}
        )

    def utility_for(self, subchar_id: str) -> Callable[[float], float]:
        """Resolve the utility function for a sub-characteristic ID.

        Resolution order:
            1. Explicit override in `self.utility_functions`.
            2. Sigmoid penalty if ID is in `self.critical_subchars`.
            3. Linear utility (default).
        """
        if subchar_id in self.utility_functions:
            return self.utility_functions[subchar_id]
        if subchar_id in self.critical_subchars:
            return sigmoid_penalty_utility
        return linear_utility

    def aggregate_to_category(
        self,
        subscores: Dict[str, float],
        weights: Dict[str, float],
    ) -> float:
        """Aggregate sub-characteristic scores to a category score on [0, 10].

        Only keys present in BOTH subscores and weights are used. Weights are
        normalized to sum to 1.0 over the intersection.
        """
        if not subscores:
            return 0.0
        if not weights:
            raise ValueError("weights must not be empty")

        common = sorted(set(subscores) & set(weights))
        if not common:
            raise ValueError(
                "no overlap between subscores and weights — nothing to aggregate"
            )

        w = np.array([weights[k] for k in common], dtype=float)
        total_w = float(w.sum())
        if total_w <= 0.0:
            raise ValueError("total weight must be positive")

        u = np.array(
            [self.utility_for(k)(subscores[k]) for k in common],
            dtype=float,
        )
        normalized_utility = float((u * w).sum() / total_w)
        return normalized_utility * 10.0

    def aggregate_intervals_to_category(
        self,
        subscore_intervals: Dict[str, tuple[float, float]],
        weights: Dict[str, float],
        n_samples: int = 10000,
        rng: Optional["np.random.Generator"] = None,
    ) -> tuple[float, float, float]:
        """Monte Carlo propagation of per-sub-char intervals to a category
        median + 5/95 percentile band.

        Fast path: when every sub-char in `common` resolves to the linear
        utility, the entire computation collapses to a single vectorised
        numpy expression — no per-sample Python call. Falls back to the
        general per-sample loop only when at least one sub-char uses
        sigmoid (or any custom callable utility).

        Uniform draws are conservative — if richer densities become available
        from the LLM panel later, swap them in here.
        """
        if not subscore_intervals:
            return 0.0, 0.0, 0.0
        rng = rng or np.random.default_rng(0)

        common = sorted(set(subscore_intervals) & set(weights))
        if not common:
            raise ValueError("no overlap between subscore_intervals and weights")

        intervals = np.array([subscore_intervals[k] for k in common], dtype=float)
        w = np.array([weights[k] for k in common], dtype=float)
        total_w = float(w.sum())
        if total_w <= 0.0:
            raise ValueError("total weight must be positive")

        # Sample once. Both paths reuse this draw.
        samples = rng.uniform(
            intervals[:, 0], intervals[:, 1], size=(n_samples, len(common))
        )

        all_linear = all(self.utility_for(k) is linear_utility for k in common)
        if all_linear:
            # U(s) = s/10 → category = (Σ U(s_i)·w_i / Σ w_i) · 10
            #                       = Σ s_i · w_i / Σ w_i  (the *10 cancels)
            out = (samples * w).sum(axis=1) / total_w
        else:
            out = np.empty(n_samples, dtype=float)
            for i in range(n_samples):
                row = {k: float(samples[i, j]) for j, k in enumerate(common)}
                out[i] = self.aggregate_to_category(row, weights)
        return (
            float(np.median(out)),
            float(np.percentile(out, 5)),
            float(np.percentile(out, 95)),
        )

    def aggregate_intervals_to_overall(
        self,
        category_intervals: Dict[str, tuple[float, float]],
        category_weights: Dict[str, float],
        n_samples: int = 10000,
        rng: Optional["np.random.Generator"] = None,
    ) -> tuple[float, float, float]:
        """Monte Carlo propagation at the category -> overall level."""
        if not category_intervals:
            return 0.0, 0.0, 0.0
        rng = rng or np.random.default_rng(0)

        common = sorted(set(category_intervals) & set(category_weights))
        if not common:
            raise ValueError("no overlap between category_intervals and category_weights")

        intervals = np.array([category_intervals[k] for k in common], dtype=float)
        weights = np.array([category_weights[k] for k in common], dtype=float)
        total_w = float(weights.sum())
        if total_w <= 0:
            raise ValueError("total weight must be positive")

        samples = rng.uniform(
            intervals[:, 0], intervals[:, 1], size=(n_samples, len(common))
        )
        out = (samples * weights).sum(axis=1) / total_w
        return (
            float(np.median(out)),
            float(np.percentile(out, 5)),
            float(np.percentile(out, 95)),
        )

    def aggregate_to_overall(
        self,
        category_scores: Dict[str, float],
        category_weights: Dict[str, float],
    ) -> float:
        """Aggregate category scores into the overall score on [0, 10].

        Linear weighted mean — sub-character penalties are already encoded
        in each category score. Weights normalized to sum to 1.0 over the
        intersection of keys.
        """
        if not category_scores:
            return 0.0
        if not category_weights:
            raise ValueError("category_weights must not be empty")

        common = sorted(set(category_scores) & set(category_weights))
        if not common:
            raise ValueError("no overlap between category_scores and category_weights")

        w = np.array([category_weights[k] for k in common], dtype=float)
        total_w = float(w.sum())
        if total_w <= 0.0:
            raise ValueError("total weight must be positive")

        s = np.array([category_scores[k] for k in common], dtype=float)
        return float((s * w).sum() / total_w)

    @classmethod
    def from_yaml(cls, path: str) -> "QuamocoAggregator":
        """Load aggregator config from YAML.

        Schema:
            critical_subchars:
              - ISO_SEC_CONF
              - ISO_REL_FAULT
            utility_functions:        # optional explicit overrides
              ISO_FOO_BAR: linear
              ISO_BAZ_QUX: sigmoid
        """
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "PyYAML required for from_yaml — install with `pip install pyyaml`"
            ) from exc

        with open(path) as f:
            cfg = yaml.safe_load(f) or {}

        critical = cfg.get("critical_subchars")
        if critical is not None:
            critical = set(critical)

        utilities: Dict[str, Callable[[float], float]] = {}
        for key, name in (cfg.get("utility_functions") or {}).items():
            if name == "linear":
                utilities[key] = linear_utility
            elif name == "sigmoid":
                utilities[key] = sigmoid_penalty_utility
            else:
                raise ValueError(f"unknown utility function name: {name!r}")

        return cls(critical_subchars=critical, utility_functions=utilities)

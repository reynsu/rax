"""Tests for the Quamoco/MAUT aggregator (scripts/aggregation.py)."""
from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from scripts.aggregation import (
    DEFAULT_CRITICAL_SUBCHARS,
    QuamocoAggregator,
    linear_utility,
    sigmoid_penalty_utility,
)
from scripts.profiles import load_profile, list_profiles


# ---------------- utility functions ----------------


def test_linear_utility_basic_and_clamp():
    assert linear_utility(0) == 0.0
    assert linear_utility(10) == 1.0
    assert linear_utility(5) == 0.5
    assert linear_utility(-3) == 0.0       # clamp below
    assert linear_utility(42) == 1.0       # clamp above


def test_sigmoid_utility_strictly_monotonic_in_unit_interval():
    prev = sigmoid_penalty_utility(0)
    assert 0 < prev < 1
    for s in range(1, 11):
        cur = sigmoid_penalty_utility(s)
        assert cur > prev, f"sigmoid not monotonic at s={s}"
        assert 0 < cur < 1
        prev = cur


def test_sigmoid_symmetric_around_5():
    """U(5-d) + U(5+d) ≈ 1 for any d."""
    for d in (1, 2, 3, 4):
        s = sigmoid_penalty_utility(5 - d) + sigmoid_penalty_utility(5 + d)
        assert s == pytest.approx(1.0, abs=1e-9)


# ---------------- aggregate_to_category ----------------


def test_aggregate_with_only_linear_subchars():
    a = QuamocoAggregator(critical_subchars=set())  # disable sigmoid path
    score = a.aggregate_to_category(
        {"ISO_FOO_A": 5, "ISO_FOO_B": 7},
        {"ISO_FOO_A": 0.5, "ISO_FOO_B": 0.5},
    )
    # linear: avg(5,7) = 6
    assert score == pytest.approx(6.0, abs=1e-9)


def test_acceptance_example_from_plan():
    """PLAN_rax_v2 step 1.3 acceptance: aggregate(SEC_CONF=2, SEC_INT=7, .5/.5) ~= 3.55.

    Why ~3.5 and not 4.5: ISO_SEC_CONF is critical (sigmoid penalty),
    ISO_SEC_INT is non-critical (linear). sigmoid(2) ≈ 0.011, linear(7) = 0.7.
    weighted: 0.5*0.011 + 0.5*0.7 = 0.355  ->  3.55 on [0,10].
    """
    a = QuamocoAggregator()  # default criticals include ISO_SEC_CONF
    score = a.aggregate_to_category(
        {"ISO_SEC_CONF": 2, "ISO_SEC_INT": 7},
        {"ISO_SEC_CONF": 0.5, "ISO_SEC_INT": 0.5},
    )
    # sigmoid(2) ≈ 0.01099, linear(7) = 0.7, mean ≈ 0.3555 -> 3.555
    assert score == pytest.approx(3.555, abs=0.01)
    # Strictly below the naive linear average of 4.5
    assert score < 4.5


def test_explicit_utility_override_wins_over_critical_default():
    """utility_functions[id] = linear forces linear even when id is critical."""
    a = QuamocoAggregator(utility_functions={"ISO_SEC_CONF": linear_utility})
    score = a.aggregate_to_category(
        {"ISO_SEC_CONF": 2, "ISO_SEC_INT": 7},
        {"ISO_SEC_CONF": 0.5, "ISO_SEC_INT": 0.5},
    )
    # both linear: avg(2,7) = 4.5
    assert score == pytest.approx(4.5, abs=1e-9)


def test_monotonicity_raising_subscore_never_lowers_category():
    a = QuamocoAggregator()
    weights = {
        "ISO_SEC_CONF": 0.4,
        "ISO_SEC_INT": 0.3,
        "ISO_SEC_AUTH": 0.3,
    }
    base = {"ISO_SEC_CONF": 5, "ISO_SEC_INT": 5, "ISO_SEC_AUTH": 5}
    base_score = a.aggregate_to_category(base, weights)

    for key in base:
        for new_val in range(int(base[key]) + 1, 11):
            higher = dict(base)
            higher[key] = new_val
            new_score = a.aggregate_to_category(higher, weights)
            assert new_score >= base_score - 1e-9, (
                f"raising {key} from {base[key]} -> {new_val} "
                f"decreased score {base_score} -> {new_score}"
            )


def test_critical_drop_is_more_sensitive_than_noncritical_drop():
    """An equal-magnitude drop on a critical sub-char must impact more than
    on a non-critical one."""
    a = QuamocoAggregator()  # ISO_SEC_CONF critical, ISO_FLEX_REPL not critical

    # Drop 8 -> 2 on critical (paired with neutral non-critical)
    high_crit = a.aggregate_to_category(
        {"ISO_SEC_CONF": 8, "ISO_FLEX_REPL": 5},
        {"ISO_SEC_CONF": 0.5, "ISO_FLEX_REPL": 0.5},
    )
    low_crit = a.aggregate_to_category(
        {"ISO_SEC_CONF": 2, "ISO_FLEX_REPL": 5},
        {"ISO_SEC_CONF": 0.5, "ISO_FLEX_REPL": 0.5},
    )
    delta_crit = high_crit - low_crit

    # Drop 7 -> 1 on non-critical (paired with neutral non-critical)
    high_noncrit = a.aggregate_to_category(
        {"ISO_FLEX_REPL": 7, "ISO_FLEX_ADAPT": 5},
        {"ISO_FLEX_REPL": 0.5, "ISO_FLEX_ADAPT": 0.5},
    )
    low_noncrit = a.aggregate_to_category(
        {"ISO_FLEX_REPL": 1, "ISO_FLEX_ADAPT": 5},
        {"ISO_FLEX_REPL": 0.5, "ISO_FLEX_ADAPT": 0.5},
    )
    delta_noncrit = high_noncrit - low_noncrit

    assert delta_crit > delta_noncrit, (
        f"Δcritical={delta_crit:.4f} should exceed Δnoncritical={delta_noncrit:.4f}"
    )


def test_weights_summing_to_one_keep_score_in_range():
    a = QuamocoAggregator()
    cases = [
        {"ISO_SEC_CONF": 0, "ISO_SEC_INT": 0},
        {"ISO_SEC_CONF": 10, "ISO_SEC_INT": 10},
        {"ISO_SEC_CONF": 5, "ISO_SEC_INT": 5},
        {"ISO_SEC_CONF": 1, "ISO_SEC_INT": 9},
        {"ISO_SEC_CONF": 9, "ISO_SEC_INT": 1},
    ]
    weights = {"ISO_SEC_CONF": 0.5, "ISO_SEC_INT": 0.5}
    for scores in cases:
        score = a.aggregate_to_category(scores, weights)
        assert 0.0 <= score <= 10.0, f"score={score} out of [0,10] for {scores}"


def test_unnormalized_weights_get_normalized():
    a = QuamocoAggregator(critical_subchars=set())
    s_unnorm = a.aggregate_to_category(
        {"ISO_FOO_A": 4, "ISO_FOO_B": 8},
        {"ISO_FOO_A": 1.0, "ISO_FOO_B": 1.0},  # sum = 2
    )
    s_unit = a.aggregate_to_category(
        {"ISO_FOO_A": 4, "ISO_FOO_B": 8},
        {"ISO_FOO_A": 0.5, "ISO_FOO_B": 0.5},
    )
    assert s_unnorm == pytest.approx(s_unit, abs=1e-9)


def test_keys_only_in_one_dict_are_ignored():
    a = QuamocoAggregator(critical_subchars=set())
    score = a.aggregate_to_category(
        {"ISO_A": 8, "ISO_B": 2, "ISO_C": 10},  # ISO_C has no weight
        {"ISO_A": 0.5, "ISO_B": 0.5, "ISO_DANGLING": 0.3},  # ISO_DANGLING has no score
    )
    # Effective: avg(8,2) under linear = 5.0
    assert score == pytest.approx(5.0, abs=1e-9)


# ---------------- aggregate_to_overall ----------------


def test_overall_is_linear_weighted_mean():
    a = QuamocoAggregator()
    overall = a.aggregate_to_overall(
        {"Security": 8, "Maintainability": 6, "Performance": 4},
        {"Security": 0.5, "Maintainability": 0.3, "Performance": 0.2},
    )
    expected = 8 * 0.5 + 6 * 0.3 + 4 * 0.2  # 6.6
    assert overall == pytest.approx(expected, abs=1e-9)


def test_overall_unnormalized_weights():
    a = QuamocoAggregator()
    overall = a.aggregate_to_overall(
        {"A": 10, "B": 0},
        {"A": 2.0, "B": 2.0},  # equivalent to .5/.5
    )
    assert overall == pytest.approx(5.0, abs=1e-9)


# ---------------- defaults & edge cases ----------------


def test_default_critical_set_contains_known_criticals():
    assert "ISO_SEC_CONF" in DEFAULT_CRITICAL_SUBCHARS
    assert "ISO_REL_FAULT" in DEFAULT_CRITICAL_SUBCHARS
    assert "ISO_SEC_AUTH" in DEFAULT_CRITICAL_SUBCHARS
    assert "ISO_SAFE_FS" in DEFAULT_CRITICAL_SUBCHARS


def test_empty_subscores_returns_zero():
    a = QuamocoAggregator()
    assert a.aggregate_to_category({}, {"ISO_FOO": 0.5}) == 0.0
    assert a.aggregate_to_overall({}, {"Cat": 0.5}) == 0.0


def test_invalid_inputs_raise():
    a = QuamocoAggregator()
    with pytest.raises(ValueError):
        a.aggregate_to_category({"ISO_FOO": 5}, {})
    with pytest.raises(ValueError):
        # zero overlap
        a.aggregate_to_category({"ISO_A": 5}, {"ISO_B": 0.5})
    with pytest.raises(ValueError):
        # weights sum to zero
        a.aggregate_to_category(
            {"ISO_A": 5, "ISO_B": 5},
            {"ISO_A": -0.5, "ISO_B": 0.5},
        )


def test_yaml_loader_round_trip(tmp_path):
    cfg_path = tmp_path / "agg.yaml"
    cfg_path.write_text(
        "critical_subchars:\n"
        "  - ISO_SEC_CONF\n"
        "utility_functions:\n"
        "  ISO_FOO_BAR: linear\n"
        "  ISO_BAZ_QUX: sigmoid\n"
    )
    a = QuamocoAggregator.from_yaml(str(cfg_path))
    assert a.critical_subchars == {"ISO_SEC_CONF"}
    assert a.utility_functions["ISO_FOO_BAR"] is linear_utility
    assert a.utility_functions["ISO_BAZ_QUX"] is sigmoid_penalty_utility


def test_yaml_loader_unknown_utility_raises(tmp_path):
    cfg_path = tmp_path / "agg.yaml"
    cfg_path.write_text(
        "utility_functions:\n"
        "  ISO_FOO: bogus\n"
    )
    with pytest.raises(ValueError):
        QuamocoAggregator.from_yaml(str(cfg_path))


# ---------------- property-based tests (hypothesis) ----------------


SUBCHAR_KEYS = [
    "ISO_SEC_CONF", "ISO_SEC_INT", "ISO_SEC_AUTH", "ISO_SEC_RES",
    "ISO_REL_FAULT", "ISO_REL_FT", "ISO_REL_REC",
    "ISO_PERF_TIME", "ISO_PERF_RES",
    "ISO_MAINT_MOD", "ISO_MAINT_ANAL", "ISO_MAINT_TEST",
    "ISO_INTER_OP", "ISO_INTER_INC", "ISO_INTER_UEP",
]


@st.composite
def _scores_and_weights(draw):
    n = draw(st.integers(min_value=2, max_value=8))
    keys = draw(
        st.lists(st.sampled_from(SUBCHAR_KEYS), min_size=n, max_size=n, unique=True)
    )
    scores = {k: draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False)) for k in keys}
    raw_w = {k: draw(st.floats(min_value=0.01, max_value=10.0, allow_nan=False)) for k in keys}
    return scores, raw_w


@given(_scores_and_weights())
@settings(max_examples=200, deadline=None)
def test_property_aggregate_to_category_in_range(case):
    """For any valid scores in [0,10] and positive weights, category ∈ [0,10]."""
    scores, weights = case
    a = QuamocoAggregator()
    out = a.aggregate_to_category(scores, weights)
    assert 0.0 <= out <= 10.0, f"out={out} for scores={scores} weights={weights}"


@given(_scores_and_weights())
@settings(max_examples=200, deadline=None)
def test_property_extreme_inputs_map_to_extremes(case):
    """All-zero scores -> 0 ± epsilon. All-ten scores -> 10 ± epsilon."""
    scores, weights = case
    a = QuamocoAggregator()

    zeros = {k: 0.0 for k in scores}
    out_zero = a.aggregate_to_category(zeros, weights)
    # sigmoid floor is small but >0; linear is 0; so [0, ~0.1) range
    assert 0.0 <= out_zero <= 0.5

    tens = {k: 10.0 for k in scores}
    out_ten = a.aggregate_to_category(tens, weights)
    # sigmoid ceiling at 10 is ~0.9997; linear is 1.0; so [9.5, 10]
    assert 9.5 <= out_ten <= 10.0


@given(
    st.dictionaries(
        keys=st.sampled_from(SUBCHAR_KEYS),
        values=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
        min_size=2, max_size=8,
    )
)
@settings(max_examples=100, deadline=None)
def test_property_overall_in_range(scores):
    """Overall aggregation always in [0,10] for any per-category scores in [0,10]."""
    a = QuamocoAggregator()
    n = len(scores)
    weights = {k: 1.0 / n for k in scores}  # uniform
    out = a.aggregate_to_overall(scores, weights)
    assert 0.0 <= out <= 10.0


# ---------------- profile differentiation ----------------


SIMULATED_SUBSCORES = {
    # Security sub-chars: medium-low (some defects)
    "ISO_SEC_CONF": 4,
    "ISO_SEC_INT": 6,
    "ISO_SEC_AUTH": 5,
    "ISO_SEC_RES": 6,
    "ISO_SEC_NR": 7,
    "ISO_SEC_ACC": 7,
    # Reliability sub-chars: medium
    "ISO_REL_FAULT": 6,
    "ISO_REL_FT": 5,
    "ISO_REL_REC": 6,
    "ISO_REL_AVAIL": 7,
    # Performance: high
    "ISO_PERF_TIME": 8,
    "ISO_PERF_RES": 7,
    "ISO_PERF_CAP": 8,
    # Interaction Capability: weak (poor a11y)
    "ISO_INTER_OP": 4,
    "ISO_INTER_INC": 3,
    "ISO_INTER_UEP": 5,
    "ISO_INTER_REC": 5,
    "ISO_INTER_LEARN": 5,
    "ISO_INTER_ENG": 6,
    "ISO_INTER_UAA": 5,
    "ISO_INTER_SD": 6,
    # Maintainability: high
    "ISO_MAINT_MOD": 8,
    "ISO_MAINT_REUSE": 7,
    "ISO_MAINT_ANAL": 8,
    "ISO_MAINT_MOD2": 7,
    "ISO_MAINT_TEST": 7,
    # rest: filler
    "ISO_FUN_CORR": 6, "ISO_FUN_COMP": 5, "ISO_FUN_APPR": 6, "ISO_FUN_IDEN": 5,
    "ISO_COMP_COEX": 7, "ISO_COMP_INTER": 6,
    "ISO_FLEX_ADAPT": 6, "ISO_FLEX_SCAL": 7, "ISO_FLEX_INST": 6, "ISO_FLEX_REPL": 6,
    "ISO_SAFE_OP": 5, "ISO_SAFE_RISK": 5, "ISO_SAFE_FS": 6, "ISO_SAFE_HW": 5, "ISO_SAFE_SI": 6,
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
    "security": [
        "ISO_SEC_CONF", "ISO_SEC_INT", "ISO_SEC_AUTH",
        "ISO_SEC_RES", "ISO_SEC_NR", "ISO_SEC_ACC",
    ],
    "maintainability": [
        "ISO_MAINT_MOD", "ISO_MAINT_REUSE", "ISO_MAINT_ANAL",
        "ISO_MAINT_MOD2", "ISO_MAINT_TEST",
    ],
    "flexibility": ["ISO_FLEX_ADAPT", "ISO_FLEX_SCAL", "ISO_FLEX_INST", "ISO_FLEX_REPL"],
    "safety": ["ISO_SAFE_OP", "ISO_SAFE_RISK", "ISO_SAFE_FS", "ISO_SAFE_HW", "ISO_SAFE_SI"],
}


def _aggregator_from_profile(profile):
    """Build an aggregator that honors the profile's utility_overrides."""
    overrides = {}
    from scripts.aggregation import linear_utility, sigmoid_penalty_utility
    for sub_id, name in (profile.get("utility_overrides") or {}).items():
        overrides[sub_id] = sigmoid_penalty_utility if name == "sigmoid" else linear_utility
    # union profile criticals with default criticals
    return QuamocoAggregator(utility_functions=overrides)


def _overall_for_profile(profile, subscores):
    """Reduce subscores -> categories with the profile's aggregator, then overall."""
    agg = _aggregator_from_profile(profile)
    cat_scores = {}
    for cname, sub_ids in CHAR_TO_SUBCHARS.items():
        present = {s: subscores[s] for s in sub_ids if s in subscores}
        if not present:
            continue
        uniform_w = {s: 1.0 / len(present) for s in present}
        cat_scores[cname] = agg.aggregate_to_category(present, uniform_w)
    return agg.aggregate_to_overall(cat_scores, profile["weights"])


def test_profiles_produce_different_overall_scores():
    """Same subscores under 5 profiles must spread > 0.5 between max and min.

    This validates that the weight differences in the profiles actually
    propagate to user-visible score differences.
    """
    overalls = {}
    for name in list_profiles():
        prof = load_profile(name)
        overalls[name] = _overall_for_profile(prof, SIMULATED_SUBSCORES)

    spread = max(overalls.values()) - min(overalls.values())
    assert spread > 0.5, f"profiles too similar: spread={spread:.3f}, overalls={overalls}"

    # Sanity: accessibility-critical, given weak Interaction Capability scores,
    # should rank LOW. Internal-tool, given strong Maintainability, should rank
    # HIGHER than accessibility-critical.
    assert overalls["accessibility-critical"] < overalls["internal-tool"], (
        f"accessibility-critical ({overalls['accessibility-critical']:.2f}) "
        f"should be lower than internal-tool ({overalls['internal-tool']:.2f}) "
        f"given weak a11y subscores in the simulation"
    )


def test_monte_carlo_propagation_to_category():
    """MC samples per-sub-char intervals, aggregates, returns (median, p5, p95).

    Coherence: the propagated interval should not be wider than the widest
    input interval and should not be narrower than what perfect-correlation
    aggregation would yield.
    """
    a = QuamocoAggregator(critical_subchars=set())  # disable sigmoid
    intervals = {
        "ISO_FOO_A": (4.0, 6.0),
        "ISO_FOO_B": (5.0, 7.0),
    }
    weights = {"ISO_FOO_A": 0.5, "ISO_FOO_B": 0.5}

    median, p5, p95 = a.aggregate_intervals_to_category(intervals, weights, n_samples=20000)
    width = p95 - p5
    assert 0.0 < width <= 2.5  # not wider than max sub-char width (2.0) by much
    assert 4.5 <= median <= 5.5
    assert p5 < median < p95


def test_monte_carlo_propagation_to_overall():
    a = QuamocoAggregator()
    cat_intervals = {
        "security": (5.0, 7.0),
        "maintainability": (6.0, 8.0),
    }
    cat_weights = {"security": 0.4, "maintainability": 0.6}
    median, p5, p95 = a.aggregate_intervals_to_overall(cat_intervals, cat_weights, n_samples=20000)
    # weighted center should be around 0.4*6 + 0.6*7 = 6.6
    assert 6.4 <= median <= 6.8
    assert p5 < median < p95


def test_catastrophic_subchar_drags_overall_significantly():
    """A critical sub-char dropping from 8 to 1 must lower overall by ≥1.5
    in a focused configuration where the critical category carries
    meaningful weight (here: 2 categories at .5/.5, sub-char at .5 within
    its category). This isolates the math from the dilution effect of the
    consumer-app default weights (security=0.15 over 6 sub-chars)."""
    a = QuamocoAggregator()

    healthy = {
        "ISO_SEC_CONF": 8, "ISO_SEC_INT": 6,
        "ISO_MAINT_MOD": 7, "ISO_MAINT_TEST": 6,
    }
    catastrophic = dict(healthy, ISO_SEC_CONF=1)

    def _overall(scores):
        sec = a.aggregate_to_category(
            {k: scores[k] for k in ("ISO_SEC_CONF", "ISO_SEC_INT")},
            {"ISO_SEC_CONF": 0.5, "ISO_SEC_INT": 0.5},
        )
        maint = a.aggregate_to_category(
            {k: scores[k] for k in ("ISO_MAINT_MOD", "ISO_MAINT_TEST")},
            {"ISO_MAINT_MOD": 0.5, "ISO_MAINT_TEST": 0.5},
        )
        return a.aggregate_to_overall(
            {"security": sec, "maintainability": maint},
            {"security": 0.5, "maintainability": 0.5},
        )

    delta = _overall(healthy) - _overall(catastrophic)
    assert delta >= 1.5, (
        f"expected catastrophic SEC_CONF drop to lower overall by ≥1.5, got Δ={delta:.3f}"
    )

"""Tests for scripts/profiles.py — stakeholder profile loader & validator."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.profiles import (
    ISO_CHARACTERISTICS,
    PROFILES_DIR,
    ProfileError,
    list_profiles,
    load_profile,
)

EXPECTED_PROFILES = {
    "consumer-app",
    "default",
    "fintech",
    "internal-tool",
    "accessibility-critical",
}


def test_all_expected_profiles_exist():
    found = set(list_profiles())
    missing = EXPECTED_PROFILES - found
    assert not missing, f"missing profiles: {missing}"


def test_each_profile_weights_sum_to_one():
    for name in EXPECTED_PROFILES:
        prof = load_profile(name)
        s = sum(prof["weights"].values())
        assert abs(s - 1.0) < 0.01, f"{name}: Σweights={s:.4f}, expected 1.0 ± 0.01"


def test_each_profile_uses_valid_characteristic_names():
    for name in EXPECTED_PROFILES:
        prof = load_profile(name)
        unknown = set(prof["weights"]) - ISO_CHARACTERISTICS
        assert not unknown, f"{name} has unknown chars: {unknown}"


def test_each_profile_has_description():
    for name in EXPECTED_PROFILES:
        prof = load_profile(name)
        assert prof.get("description"), f"{name} missing description"
        assert len(prof["description"]) > 30, f"{name} description too short"


def test_each_profile_has_red_flag_rules():
    for name in EXPECTED_PROFILES:
        prof = load_profile(name)
        rules = prof.get("red_flag_rules") or []
        assert len(rules) >= 1, f"{name} should have at least one red flag rule"
        for r in rules:
            assert "id" in r, f"{name}: rule missing id"
            assert "description" in r, f"{name}: rule {r.get('id')} missing description"
            assert r.get("cap_category") in ISO_CHARACTERISTICS, (
                f"{name}: rule {r['id']} has invalid cap_category={r.get('cap_category')}"
            )
            cap = r.get("cap_at")
            assert isinstance(cap, (int, float)) and 0 <= cap <= 10, (
                f"{name}: rule {r['id']} has invalid cap_at={cap}"
            )


def test_default_inherits_from_consumer_app():
    """default profile uses extends: consumer-app — they should have the
    same weights and red flags."""
    default = load_profile("default")
    consumer = load_profile("consumer-app")
    assert default["weights"] == consumer["weights"]
    assert {r["id"] for r in default["red_flag_rules"]} == {
        r["id"] for r in consumer["red_flag_rules"]
    }


def test_fintech_security_weight_higher_than_consumer():
    """The plan explicitly requires fintech.security > consumer-app.security."""
    fintech = load_profile("fintech")
    consumer = load_profile("consumer-app")
    assert fintech["weights"]["security"] > consumer["weights"]["security"], (
        f"fintech.security={fintech['weights']['security']} should exceed "
        f"consumer-app.security={consumer['weights']['security']}"
    )
    assert fintech["weights"]["security"] >= 0.25
    assert consumer["weights"]["security"] <= 0.20


def test_accessibility_profile_emphasizes_interaction():
    prof = load_profile("accessibility-critical")
    consumer = load_profile("consumer-app")
    assert prof["weights"]["interaction_capability"] > consumer["weights"][
        "interaction_capability"
    ]


def test_internal_tool_emphasizes_maintainability():
    prof = load_profile("internal-tool")
    consumer = load_profile("consumer-app")
    assert prof["weights"]["maintainability"] > consumer["weights"]["maintainability"]


def test_unknown_profile_raises():
    with pytest.raises(FileNotFoundError):
        load_profile("definitely-not-a-real-profile-xyz")


def test_invalid_weights_sum_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "weights:\n"
        "  security: 0.4\n"
        "  maintainability: 0.4\n"      # sum = 0.8, off by 0.2
    )
    with pytest.raises(ProfileError) as exc:
        load_profile("bad", profiles_dir=tmp_path)
    assert "weights sum" in str(exc.value)


def test_invalid_characteristic_name_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "weights:\n"
        "  not_a_real_iso_char: 1.0\n"
    )
    with pytest.raises(ProfileError) as exc:
        load_profile("bad", profiles_dir=tmp_path)
    assert "unknown characteristic" in str(exc.value)


def test_invalid_utility_override_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "weights:\n"
        "  security: 1.0\n"
        "utility_overrides:\n"
        "  ISO_SEC_CONF: bogus\n"
    )
    with pytest.raises(ProfileError) as exc:
        load_profile("bad", profiles_dir=tmp_path)
    assert "utility_overrides" in str(exc.value)


def test_invalid_red_flag_cap_at_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "weights:\n"
        "  security: 1.0\n"
        "red_flag_rules:\n"
        "  - id: foo\n"
        "    cap_category: security\n"
        "    cap_at: 99\n"               # out of [0,10]
    )
    with pytest.raises(ProfileError) as exc:
        load_profile("bad", profiles_dir=tmp_path)
    assert "cap_at" in str(exc.value)


def test_extends_chain_resolves(tmp_path):
    parent = tmp_path / "parent.yaml"
    parent.write_text(
        "weights:\n"
        "  security: 0.5\n"
        "  maintainability: 0.5\n"
        "description: parent profile baseline\n"
        "red_flag_rules:\n"
        "  - id: rule_a\n"
        "    description: parent rule a\n"
        "    cap_category: security\n"
        "    cap_at: 4\n"
    )
    child = tmp_path / "child.yaml"
    child.write_text(
        "extends: parent\n"
        "weights:\n"
        "  security: 0.7\n"             # overrides parent
        "  maintainability: 0.3\n"      # rebalance so Σ = 1.0
        "description: child profile description that is long enough\n"
    )
    prof = load_profile("child", profiles_dir=tmp_path)
    # Child's security overrides parent's; child rebalances maintainability
    assert prof["weights"]["security"] == 0.7
    assert prof["weights"]["maintainability"] == 0.3
    # Child inherits parent's red flag rules
    rule_ids = [r["id"] for r in prof["red_flag_rules"]]
    assert "rule_a" in rule_ids
    # Child's description wins
    assert "child profile" in prof["description"]


def test_extends_cycle_raises(tmp_path):
    a = tmp_path / "a.yaml"
    a.write_text("extends: b\nweights:\n  security: 1.0\n")
    b = tmp_path / "b.yaml"
    b.write_text("extends: a\nweights:\n  security: 1.0\n")
    with pytest.raises(ProfileError) as exc:
        load_profile("a", profiles_dir=tmp_path)
    assert "cycle" in str(exc.value).lower()


def test_list_profiles_returns_sorted_unique():
    names = list_profiles()
    assert names == sorted(set(names))
    assert len(names) >= 5


def test_profiles_dir_constant_points_to_existing_dir():
    assert PROFILES_DIR.exists()
    assert PROFILES_DIR.is_dir()

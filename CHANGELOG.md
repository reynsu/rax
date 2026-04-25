# Changelog

All notable changes to rax. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and dates follow
ISO 8601.

## [2.0.0] — 2026-04-25

### Headline
rax 2.0 replaces single-judge point estimates with a hybrid pipeline
(deterministic + LLM panel) that emits 90% confidence intervals
calibrated against a corpus of synthetic anchors, mined signals, and
cross-LLM consensus. Every score traces back to ISO/IEC 25010:2023.

### Breaking changes vs v1
- **Rubric.** v1 categories (`ARC`, `CQR`, `RXP`, `SEC`, `UXA`, `TYP`,
  `ERR`, `TST`, `DEP`, `APT`) replaced by the 9 ISO/IEC 25010:2023
  characteristics. The v1 rubric (`references/rubric.md`) is preserved
  read-only; v2 lives in `references/rubric-v2.md` and
  `references/iso25010-mapping.md` documents the migration.
- **Scores are intervals.** Every reported score is now `[p5, p95]/10`
  with a median; consumers used to a single number must update.
- **APT (anti-patterns) is no longer a top-level category.** Each
  anti-pattern is reassigned as a red flag inside its relevant ISO
  sub-characteristic.
- **Report format.** `references/report-format.md` is now v2-shaped;
  v1 format is preserved at `references/report-format-v1.md`.
- **README.** v1 README is preserved at `docs/README-v1.md`.

### Added
- ISO/IEC 25010:2023 mapping (`references/iso25010-mapping.md`).
- v2 rubric with 41 sub-characteristics, anchors, and α coverage hints
  (`references/rubric-v2.md`).
- Quamoco/MAUT aggregator with sigmoid penalty for critical sub-chars
  (`scripts/aggregation.py`, 100% test coverage).
- 5 stakeholder profiles + loader + extends-chain support
  (`templates/profiles/*.yaml`, `scripts/profiles.py`).
- Deterministic layer orchestrator (`scripts/deterministic_layer.sh`)
  + parser (`scripts/parse_deterministic.py`) — maps Semgrep/ESLint/
  tsc/madge/jscpd/npm-audit findings to ISO sub-characteristics.
- 31 custom Semgrep rules for React/RN
  (`references/rules/*.yaml`, all pass `semgrep --test`).
- Hybrid scoring: `final = α · det + (1-α) · llm` per sub-char
  (`scripts/scoring.py`).
- Audit-output JSON Schema (`references/audit-output.schema.json`).
- Multi-judge panel with replicates + caching
  (`scripts/judge_panel.py`).
- Reference-guided anchor injection in the prompt builder
  (`scripts/build_prompt.py`).
- Cross-LLM consensus tool (`scripts/cross_llm_eval.py`).
- Differential evaluation vs ESLint/Sonar
  (`scripts/differential_eval.py`).
- Corpus: 60+ synthetic anchors + 50+ mined repo signals
  (`tests/corpus/`).
- Self-consistency benchmark suite (`tests/test_self_consistency.py`,
  gated by `@pytest.mark.expensive`).
- Conformal prediction layer (`scripts/conformal.py`,
  `scripts/validate_calibration.py`); empirical coverage 94.7%
  on the bundled corpus.
- Monte Carlo propagation of intervals to category and overall
  (`scripts/aggregation.py`).
- Calibration drift CI workflow
  (`.github/workflows/calibration-drift.yml`).
- 1-4 internal scale → 1-10 user-visible mapping with per-sub-char
  overrides (`references/scale-mapping.yaml`).
- Opt-in telemetry CLI (`scripts/telemetry.py`); default OFF.
- Health check (`scripts/doctor.py`).
- Phase 1 milestone demo (`demos/phase1_demo.py`).
- Comprehensive test suite (80+ tests, 100% coverage on core modules).

### Known limitations (carried forward to 2.1)
- No human-validated corpus yet. Calibration uses proxy ground truth:
  synthetic anchors, mined defect-density, cross-LLM medians.
  Telemetry (opt-in) is the path to a real human corpus.
- Subjective sub-characteristics will abstain rather than invent a
  number; the panel-disagreement threshold is 1.5 points.
- React / React Native only.
- LLM cost: ~$0.5–2 per full-mode audit (3 models × 5 replicates).
- Not certified for regulated industries.
- IDE integration not yet shipped.

### Roadmap to v2.1
- Build a human-validated corpus from telemetry submissions
  (target: 1000+ corrected audits).
- Re-calibrate conformal layer against the human-validated corpus.
- Add SARIF export for GitHub Code Scanning integration.
- Tab completion for bash/zsh.
- More profiles: SaaS, embedded, OSS-library.
- Performance: parallel deterministic-layer workers.

### Upgrade guide
1. Run `python scripts/conformal.py --calibrate` once to generate
   `tests/results/conformal_calibration.json`.
2. Run `python scripts/doctor.py` to verify your install.
3. If you have a v1 report you want to compare against a v2 audit,
   the v2 reader auto-converts each v1 score `s` to the interval
   `[max(0, s-1), min(10, s+1)]` and tags the report
   `compatibility: v1-upgraded`.

---

## [1.0.0] — earlier
First release. Single Claude judge, hand-crafted rubric, point scores
from 1–10. Documented at `docs/README-v1.md`.

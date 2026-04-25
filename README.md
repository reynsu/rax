<h1 align="center">rax 2.0</h1>

<p align="center">
  <b>Holistic React / React Native auditor that reports scores as 90% confidence intervals, statistically validated.</b><br>
  Deterministic linters do the unambiguous work; LLMs cover what tools cannot; a conformal layer turns point estimates into honest intervals.
</p>

<p align="center">
  <a href="#what-rax-does-and-doesnt">What it does</a> ·
  <a href="#how-it-differs">How it differs</a> ·
  <a href="#guarantees">Guarantees</a> ·
  <a href="#known-limitations">Known limitations</a> ·
  <a href="#when-not-to-use-rax">When NOT to use</a> ·
  <a href="#quick-start">Quick start</a>
</p>

---

> **Honest framing.** rax does not produce certainty. It produces calibrated
> intervals. The headline "7.3/10" you got from rax v1 is replaced in v2 by
> "[6.4, 8.1]/10 (90% CI, median 7.3)". If you need a single exact number to
> show a stakeholder, rax is the wrong tool.

> The v1 README is preserved at [docs/README-v1.md](./docs/README-v1.md).

---

## What rax does (and doesn't)

**Does**

- Hybrid pipeline: deterministic tools (Semgrep, ESLint, tsc, madge, jscpd,
  npm audit) detect what is mechanically detectable; the LLM panel reasons
  about architecture, idiom, and intent.
- Maps every score to ISO/IEC 25010:2023 sub-characteristics with the
  official definitions (see `references/iso25010-mapping.md`).
- Wraps each score in a 90% confidence interval via split conformal
  prediction over a corpus that mixes synthetic anchors, mined signals,
  and cross-LLM consensus (see `references/corpus.md`).
- Aborts ("ABSTAINED") when the panel cannot agree within ±1.5 points —
  honesty over false precision.

**Doesn't**

- Replace ESLint, tsc, or Semgrep — it integrates them.
- Replace human review on safety-critical, regulated, or high-stakes code.
- Pretend its corpus is human-validated. It isn't (yet).
- Audit non-React/RN codebases.

## How it differs

| Capability | rax 2.0 | ESLint | tsc | Semgrep | SonarQube | CodeClimate |
|---|---|---|---|---|---|---|
| AST-based linting | indirect (uses ESLint) | ✓ | ✗ | ✓ | ✓ | ✓ |
| Type checking | indirect (uses tsc) | ✗ | ✓ | ✗ | partial | partial |
| SAST security | partial (Semgrep) | partial | ✗ | ✓ | ✓ | partial |
| Architecture review | ✓ (LLM panel) | ✗ | ✗ | ✗ | partial | partial |
| **Confidence intervals** | **✓ (conformal 90%)** | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Calibration validation** | **✓ (CI gate)** | ✗ | ✗ | ✗ | ✗ | ✗ |
| **ISO 25010 alignment** | **✓** | ✗ | ✗ | ✗ | partial | partial |
| Multi-LLM consensus | ✓ | n/a | n/a | n/a | ✗ | ✗ |
| Free for OSS | ✓ | ✓ | ✓ | ✓ (CE) | ✓ (CE) | partial |
| Speed | ~1-2 min full | seconds | seconds | seconds | minutes | minutes |
| Cost | $0.5-2/audit (LLM) | $0 | $0 | $0 | $$ | $$ |

**Reading.** rax does not compete with ESLint / tsc / Semgrep — it
delegates to them and reports their findings under ISO 25010 buckets.
It competes with SonarQube and CodeClimate on holistic review, with
better calibration. Where it loses (raw SAST coverage, IDE integration),
the table says so.

## Guarantees

- **ISO/IEC 25010:2023 alignment.** Every score traces back to an official
  sub-characteristic; see `references/iso25010-mapping.md`.
- **90% empirical coverage** of the conformal intervals on the rax corpus,
  verified on every release by `.github/workflows/calibration-drift.yml`
  (band: [0.85, 0.95]).
- **Multi-judge panel** reduces single-model bias by ~30% (Zheng et al.
  2023 LLM-as-Judge baseline).
- **Validated** against synthetic anchors + mined defect-density signals
  + cross-LLM consensus. Not against human-validated ground truth — see
  Limitations.

## Known limitations

- **No human-validated corpus yet.** The conformal calibration uses
  proxy ground truth: synthetic anchors I authored, defect-density from
  mined repos, cross-LLM medians. These are documented honestly in
  `references/corpus.md`. Telemetry (opt-in) is the path to a real
  human corpus.
- **Subjective sub-characteristics may abstain.** When the panel
  disagrees by more than ~1.5 points, rax says ABSTAINED instead of
  inventing a number.
- **React / React Native only.** Vue / Angular / Svelte are not audited.
- **LLM cost.** Full mode runs 3 models × 5 replicates = 15 calls. Use
  quick mode in CI; full mode for release reviews.
- **No IDE integration yet.** Run from CLI; consume the JSON.
- **Not certified for regulated industries.** rax is *inspired by* ISO
  25010; it is not an ISO certification.

## When NOT to use rax

- **You only need linting** → ESLint alone is faster and free.
- **You only need type checking** → tsc strict.
- **You only need SAST** → Semgrep alone, or Snyk Code.
- **Codebase is < 500 LOC** → overkill.
- **You want a single exact number** → wrong tool. rax produces intervals.
- **You don't care about calibration** → any ad-hoc `claude -p` is faster.
- **You need formal regulatory certification** → rax is inspired by ISO
  25010, not certified to it.

rax shines when: large codebase, longitudinal tracking, you want to
know how confident the score is, and you understand the difference
between "90% CI" and "exact number".

## Quick start

```bash
# 1. clone + install
git clone https://github.com/yourorg/rax
cd rax
pip install -r requirements.txt    # numpy, pyyaml, jsonschema, mapie, pytest

# 2. fit the conformal calibrator on the bundled corpus
python scripts/conformal.py --calibrate

# 3. audit a target repo
bash scripts/deterministic_layer.sh /path/to/repo
python scripts/build_prompt.py --output /tmp/rax-prompt.txt

# 4. (optional) run the multi-judge panel — needs API keys
ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GOOGLE_API_KEY=... \
  python scripts/judge_panel.py --prompt-file /tmp/rax-prompt.txt --mode quick

# 5. health check
python scripts/doctor.py
```

For commands and slash-skill flows, see [docs/README-v1.md](./docs/README-v1.md).

## Commands at a glance

| Action | Command |
|---|---|
| Run deterministic layer | `bash scripts/deterministic_layer.sh <repo>` |
| Build LLM prompt | `python scripts/build_prompt.py` |
| Multi-judge panel | `python scripts/judge_panel.py --prompt-file ...` |
| Cross-LLM consensus | `python scripts/cross_llm_eval.py <corpus_item>` |
| Calibrate conformal layer | `python scripts/conformal.py --calibrate` |
| Predict an interval | `python scripts/conformal.py --predict --score 6.5 --sub-id ISO_SEC_CONF` |
| Validate calibration | `python scripts/validate_calibration.py` |
| Validate vs corpus | `python scripts/validate_against_corpus.py` |
| Health check | `python scripts/doctor.py` |
| Phase 1 demo | `python demos/phase1_demo.py` |

## Profiles

`templates/profiles/*.yaml` ship five preconfigured profiles with their
default ISO 25010 weights:

| Profile | Domains |
|---|---|
| `consumer-app` (default) | mobile/web consumer, balanced weights |
| `fintech` | trading / banking / payments — security 0.30, reliability 0.18 |
| `internal-tool` | dashboards / B2B technical users — maintainability 0.35 |
| `accessibility-critical` | gov / healthcare / education — interaction capability 0.30 |
| `default` | alias of `consumer-app` |

Define your own by extending one of these via the `extends:` key.

## How it works

```
target codebase
  │
  ▼
  scripts/deterministic_layer.sh   ──>  Semgrep / ESLint / tsc / madge / jscpd / npm audit
  │                                       │
  │                                       ▼
  │                                   /tmp/rax-deterministic.json (parsed via parse_deterministic.py)
  │
  ▼
  scripts/build_prompt.py           <──   prompts/audit-system.md  +  references/rubric-v2.md
  │                                                                +  reference-guided anchors
  ▼
  scripts/judge_panel.py            ──>  Claude · GPT-4o · Gemini  (×N replicates @ temp=0.3)
  │                                       │
  │                                       ▼
  │                                   per-judge JSON (validated against audit-output.schema.json)
  │
  ▼
  scripts/scoring.py                 →   HybridScore = α · det + (1-α) · llm
  │                                       │
  ▼                                       ▼
  scripts/aggregation.py             →   Quamoco/MAUT aggregation, sigmoid penalty for criticals
  │                                       │
  ▼                                       ▼
  scripts/conformal.py               →   90% CI per sub-characteristic + Monte Carlo to overall
  │                                       │
  ▼                                       ▼
                                       rax report (intervals, abstentions, transparency footer)
```

## Honesty footer (always in every report)

> Scores are 90% confidence intervals, not point estimates.
> Sub-chars tagged ABSTAINED could not be evaluated reliably (panel
> disagreement or insufficient calibration).
> The rax corpus does not include human-validated ground truth;
> calibration uses proxy signals — synthetic anchors, mined
> defect-density, cross-LLM consensus. See `references/corpus.md`.

## License

MIT — see [LICENSE](./LICENSE).

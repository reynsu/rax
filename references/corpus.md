# Corpus epistemology — what each layer is, what it is *not*

> Without humans-in-the-loop labelling code as "good" or "bad" at scale, rax
> cannot have ground truth in the strict sense. Instead it builds a corpus of
> **four complementary layers**, each with documented confidence and known
> failure modes. None is authoritative on its own. Combined, they triangulate.
>
> This file is the contract: anyone who reads a rax score should know what
> evidence is behind it, and what it cannot tell them.

---

## Layer 1 — Synthetic anchors (`tests/corpus/synthetic_anchors/`)

**What it is.** ~60 hand-authored snippets, each scored at the EXTREMES of an
ISO 25010 sub-characteristic (1-2 / 9-10). The "ground truth" is the score
the author assigned, defended in `manifest.json#justification`. The selection
criterion is "any competent React/RN engineer would agree within ±1".

**Why only extremes.** The mid-range (4-7) is where reasonable engineers
disagree without humans-in-the-loop. Anchoring extremes lets us:
- Calibrate the LLM judge (Fase 4.3 reference-guided grading).
- Detect drift (a previously-1 anchor scoring 5 means the rubric or the
  judge changed).
- Run cross-LLM consensus (Fase 3.4) on stable inputs.

**Confidence:** **high for boundaries, none for the middle**.
The corpus tells us the judge can identify catastrophic vs. exemplary code.
It tells us nothing about whether 6 vs. 7 is reproducible.

**Limitations.**
- Cherry-picked: covers the cases I thought of. Production codebases
  contain unsynthesized failure modes.
- Authored, not natural: real code has noise, inertia, partial fixes.
- Author bias: my taste is encoded in the anchors.

---

## Layer 2 — Mined signals (`tests/corpus/mined/`)

**What it is.** Objective, scrape-able metadata from public React/RN repos:
defect-density proxy (`fix:`-keyword commit ratio), star count, lifespan,
review intensity (avg PR comments), CVE count, recent activity. One JSON
per repo. Code is NOT stored — only metadata.

**What it tells you.** **Weak proxies for code quality.** The literature
(Bird et al., Rahman & Devanbu, et al.) finds these metrics correlate with
defect rates but the effect sizes are small (R² typically 0.1-0.3). They
are useful as a population view, not as judgment of any single repo.

**Confidence:** **low individually, medium in aggregate**. Use these to
detect rax drift across populations, not to validate per-repo scores.

**Limitations.**
- `fix:` keyword is gameable; mature teams write neutral commit messages.
- Star count tracks popularity, not quality.
- Sample bias: GitHub-public repos are not representative.

**Offline mode.** When `GITHUB_TOKEN` is not available,
`scripts/mine_corpus.py --synthesize N` generates valid-schema placeholders.
These are clearly tagged `"synthetic": true` and MUST NOT be used for any
calibration claim.

---

## Layer 3 — Self-consistency benchmarks (`tests/results/self_consistency_*.json`)

**What it measures.** *Stability* of the LLM judge under perturbations that
do not change the substance of the code:

1. `repetition_stability` — N=5 runs at temp=0.3 on each anchor. Variance
   per sub-characteristic should stay ≤ 0.5.
2. `file_ordering_invariance` — present the same files in 5 orders.
   Range (max − min) per sub-char ≤ 1.0.
3. `rubric_paraphrase_invariance` — rewrite the rubric 3 ways with the
   same meaning. Divergence ≤ 1.0.

**What this is NOT.** It does not measure correctness. A judge can be
perfectly consistent and consistently wrong. Self-consistency is necessary
but not sufficient for trust.

**Confidence:** **diagnostic only**. Failures here flag sub-characteristics
that need the rubric tightened, not signal that rax is "right" anywhere.

**Limitations.**
- Expensive: hits real LLM APIs. Run weekly in CI, not per PR.
- Skipped automatically without `ANTHROPIC_API_KEY`. The placeholder file
  written in that case is marked `"synthetic": true`.

---

## Layer 4 — Cross-LLM consensus (`tests/corpus/cross_llm/*.json`)

**What it measures.** Agreement across three judges from distinct vendor
families: Anthropic Claude, OpenAI GPT-4o, Google Gemini Pro. For each
sub-characteristic: per-judge score, median, range, std-dev.

**Interpretation.**
- Range ≤ 1: convergence — strong signal that the input is unambiguous.
- Range 2-3: yellow — sub-char is borderline subjective or rubric is
  ambiguous; review.
- Range > 3: red — flag in `high_disagreement_subchars`. The score that
  rax reports for this sub-char on this codebase is unreliable.

**Confidence:** **medium**. Three frontier models from different
families is a defensible signal, but they share training-data biases and
post-training conventions. They are correlated, not independent samples.

**Limitations.**
- Three judges still leave a 33% tie-breaker problem.
- Pricing: a full corpus pass across three judges is the most expensive
  thing in the pipeline — gate behind `--mode=full`.

---

## Layer 5 (deferred) — Differential evaluation
`tests/results/differential_*.json`

**What it does.** For 20 representative codebases, run rax + ESLint +
SonarQube CE; bucket findings into `only_rax` (value-add), `only_others`
(false negatives), `intersection` (confirmed). Documents where rax stands.
The point is not to win — it is to be honest about gaps.

**Confidence:** **high for what it directly compares**. ESLint findings
that rax misses ARE gaps. ESLint findings rax also reports ARE confirmed.

---

## How a rax report uses these

The Phase 5 conformal-prediction layer reads:

- `synthetic_anchors` → calibration set for prediction intervals.
- `self_consistency` → if a sub-char is fragile, conformal interval widens.
- `cross_llm` → if a sub-char is in `high_disagreement_subchars`, conformal
  interval widens; if it widens past 3 points, rax abstains.

The Phase 6 honest-framing pass appends a transparency footer to every
audit:

> "This audit was produced by a hybrid (deterministic + LLM) pipeline.
> Sub-characteristics tagged `low confidence` were not auditable
> deterministically and the LLM judges disagreed materially.
> Treat scores within their published intervals, not as point estimates."

---

## Renewal policy

- **Anchors:** add when a new sub-characteristic gains coverage; never
  silently rescore. Changes ≥1 point require a CHANGELOG entry.
- **Mined corpus:** refresh quarterly. Snapshots are gitignored except for
  the seed `repo_list.txt`.
- **Self-consistency / cross-LLM results:** rolled up monthly into a
  longitudinal trend chart in `tests/results/`.

---

## What this corpus CANNOT do

- Replace human review on critical systems.
- Tell you whether a codebase is "good" — only whether it scores within
  an interval relative to ISO 25010 sub-characteristic anchors.
- Catch domain-specific defects (e.g., medical safety, financial
  regulatory) without targeted profile activation.
- Be used as ground truth in research papers without disclosing all
  layers' limitations.

When in doubt, lean conservative: report a wider interval, not a tighter one.

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

> **Coming from v1?** Read [docs/v1-to-v2.md](./docs/v1-to-v2.md) — full
> migration guide with side-by-side architecture, the v1→ISO category
> mapping table, and a step-by-step upgrade path. The v1 README is
> preserved at [docs/README-v1.md](./docs/README-v1.md).

---

## Why rax exists

The audit critique that drove rax v2: *"of the 22 findings you reported,
ESLint detects 10 of them in milliseconds."* Single-LLM auditors
re-detect what tools already find, then return one number with
no honest sense of confidence. rax v2 separates the two — deterministic
linters do the unambiguous work, the LLM panel adds what tools miss
(architecture, idiom, intent), and a conformal layer turns the result
into a calibrated 90% interval that you can actually defend in a
review.

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
| AST-based linting | ✓\* | ✓ | ✗ | ✓ | ✓ | ✓ |
| Type checking | ✓\* | ✗ | ✓ | ✗ | partial | partial |
| SAST security | ✓\* | partial | ✗ | ✓ | ✓ | partial |
| Architecture review | ✓ (LLM panel) | ✗ | ✗ | ✗ | partial | partial |
| 🟢 **Confidence intervals** | **✓ (conformal 90%)** | ✗ | ✗ | ✗ | ✗ | ✗ |
| 🟢 **Calibration validation** | **✓ (CI gate)** | ✗ | ✗ | ✗ | ✗ | ✗ |
| 🟢 **ISO 25010 alignment** | **✓** | ✗ | ✗ | ✗ | partial | partial |
| Multi-LLM consensus | ✓ | n/a | n/a | n/a | ✗ | ✗ |
| Free for OSS | ✓ | ✓ | ✓ | ✓ (CE) | ✓ (CE) | partial |
| Speed | ~1-2 min full | seconds | seconds | seconds | minutes | minutes |
| Cost | **$0 on a Claude Code plan**; ~$0.30 quick / ~$2-3 full via direct API | $0 | $0 | $0 | $$ | $$ |

<sub>\* delegated — rax invokes the tool from the same row; findings
are reported under ISO 25010 buckets in rax's report. 🟢 marks the three
rows where rax offers something none of the alternatives do.</sub>

> **Cost note.** When you trigger rax through Claude Code (the `SKILL.md`
> path — "audit my code"), the LLM calls run inside your Claude Code
> subscription (Pro / Max / Team / Enterprise) and there is **no
> per-audit charge**. The dollar figures above apply only when you run
> `--mode=full` via the direct provider APIs (`ANTHROPIC_API_KEY` +
> `OPENAI_API_KEY` + `GOOGLE_API_KEY`) outside Claude Code. Rax's
> deterministic layer (Semgrep / ESLint / tsc / madge / jscpd / npm
> audit) costs $0 either way — those tools run locally.

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
- **LLM cost depends on how you invoke rax.** Run via the Claude Code
  skill: $0 incremental (your Claude Code plan covers it). Run
  `--mode=full` via direct API keys: ~$2-3 per audit (3 models × 5
  replicates = 15 calls). Use `--mode=quick` in CI either way; reserve
  `--mode=full` for release reviews.
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

### Prerequisites

- **Python 3.10+** (the conformal layer, scoring, and rax_core).
- **`claude` CLI** (optional but recommended) — without it, `rax audit` prints
  the composed prompt for you to paste into any Claude Code UI.
- **Node tooling** (optional, opt-in per audit) — Semgrep, ESLint, tsc, madge,
  jscpd, npm audit. Install whichever you have; `rax audit` skips missing
  tools and records them under `tools_failed` rather than aborting.
- **API keys** (optional, only for `--mode=full`) — `ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, `GOOGLE_API_KEY`. Without these, `--mode=full` falls back
  to single-judge with an explicit warning.

### Two ways to use rax

**1. As a Claude Code skill (recommended).** rax ships a `SKILL.md` that triggers on
"audit my code", "score my codebase", "review this app", etc. The audit runs with
intervals, ABSTAINED rows, and the v2 honesty footer.

> **Skill registration.** Claude Code auto-discovers `SKILL.md` when you `cd` into
> the cloned `rax` directory before invoking it. For project-wide availability,
> copy `SKILL.md`, `scripts/`, `references/`, `prompts/`, and `templates/` into
> `~/.claude/skills/rax/`. `install.sh` only symlinks `bin/rax` onto PATH — it
> does NOT register the skill globally.

**2. As a first-class CLI.** Install the `rax` binary and call it directly.

### First audit in 5 minutes

#### 1. Install + calibrate (one time per machine)

```bash
git clone https://github.com/reynsu/rax && cd rax
pip install -r requirements.txt
bash install.sh                          # symlinks bin/rax onto PATH
python scripts/conformal.py --calibrate  # fit the conformal calibrator
```

The calibrate step prints something like:

```text
{
  "calibration_size": 225,
  "sub_chars_with_per_sub_q": 3,
  "global_q": 1.27,
  "empirical_coverage_on_calibration": 0.94
}
```

Coverage near 0.90 means the bundled corpus produced 90% intervals
that actually contain ground truth ~94% of the time — well inside
the [0.85, 1.00] band the CI gate enforces.

#### 2. Health check

```bash
rax doctor
```

Lists every dependency rax cares about, marking each as critical /
optional. Fix the critical lines first; the optional ones (e.g.,
`semgrep not installed`) are warnings, not blockers.

#### 3. Run the audit

```bash
cd /path/to/your-react-app
rax audit --mode=quick     # pre-commit / pre-push (~30s)
```

You'll see four progress lines as the orchestrator does its work:

```text
▶ rax/audit step 1/3  deterministic layer (semgrep/eslint/tsc/madge/jscpd/npm-audit)
▶ rax/audit step 2/3  building prompt with rubric-v2 + anchors + deterministic findings
  prompt: /tmp/rax-<user>/rax-prompt.txt  (1556 lines, 75920 bytes)
▶ rax/audit step 3/3  invoking Claude Code with the v2 prompt
```

When `claude` is on PATH, step 3 hands the prompt to Claude Code.
When it isn't, rax prints the composed prompt for you to paste into
any Claude Code UI — same fallback as v1.

#### 4. Read the report

```bash
rax show latest
```

Prints the full v2 report. Header → overall interval → per-ISO
table → critical findings → warnings → notes → honesty footer:

```text
# rax audit — 2026-04-25 · abc1234 · main

**Profile:**     consumer-app (default)
**Mode:**        quick
**Rubric:**      rax-v2.0.0
**Calibration:** empirical coverage 94% (target band 85–95%)
**Panel:**       claude-opus-4-7 · gpt-4o · gemini-1.5-pro
**Tools (det):** Semgrep · ESLint · tsc · madge · jscpd · npm audit

## Overall: [6.4, 8.1]/10  (90% CI, median 7.3)
vs baseline [6.6, 8.2]: overlap 76%  → no significant change

| ISO Characteristic    | CI 90%       | Median | Confidence | Δ vs baseline |
|-----------------------|--------------|--------|------------|---------------|
| Security              | [3.5, 5.0]   | 4.2    | high       | -0.4 (regr.)  |
| Maintainability       | [5.0, 7.5]   | 6.2    | medium     | +0.1          |
| Reliability           | ABSTAINED    | —      | low        | —             |
| Interaction Capability| [6.4, 8.1]   | 7.3    | high       | +0.0          |
```

Use `rax show latest --format summary` if you only want the header
and the table; `--format scores` is even shorter.

#### Other audit modes

```bash
rax audit                                  # diff vs baseline (default)
rax audit --mode=full --save               # multi-judge × N replicates; promotes baseline
rax audit --profile=fintech --mode=full    # weights from templates/profiles/fintech.yaml
rax audit --mode=focused --category=Security  # one ISO characteristic, deeply
```

Flags:

| Flag | Default | Meaning |
|---|---|---|
| `--mode {quick,diff,focused,full}` | `diff` | scope; `full` runs the multi-judge panel |
| `--profile NAME` | `consumer-app` | weights — see Profiles section |
| `--category NAME` | — | required with `--mode=focused` |
| `--save` | off | promote the result to baseline after the audit |
| `--no-deterministic` | off | skip Semgrep/ESLint/tsc/madge/jscpd/npm audit (LLM-only) |

#### Querying past audits

CLI commands print the median for terseness; the full report (with
90% intervals + ABSTAINED rows + the transparency footer) is in
`rax show`.

```bash
rax score                # median + delta vs baseline
rax scores               # per-ISO-characteristic medians
rax pending              # findings still open
rax delta                # what changed vs baseline
rax history --limit 10   # past audits
```

## Commands at a glance

**User-facing (the CLI you actually run):**

| Action | Command |
|---|---|
| Audit | `rax audit [--mode] [--profile] [--category] [--save] [--no-deterministic]` |
| Headline | `rax score` |
| Per-category table | `rax scores` |
| Movement vs baseline | `rax delta` |
| Findings still open | `rax pending [--category C] [--severity S]` |
| Findings fixed since baseline | `rax fixed` |
| Findings introduced since baseline | `rax new` |
| Show a report | `rax show [latest\|<id>] [--format full\|summary\|scores\|raw]` |
| Past audits | `rax history [--limit N]` |
| Save baseline | `rax baseline save` |
| Reset baseline | `rax baseline reset` |
| Health check | `rax doctor` |

**Maintainer / power-user (call directly only when debugging the pipeline):**

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

#### What that actually changes

`python demos/phase1_demo.py` runs the same simulated subscores under
each profile. The same code base scores differently depending on which
weights you apply:

```text
profile                 overall
--------------------------------------------------------------
internal-tool            6.97    █████████████████████·········
fintech                  6.78    ████████████████████··········
consumer-app             6.40    ███████████████████···········
default                  6.40    ███████████████████···········
accessibility-critical   5.94    ██████████████████············

Spread (max - min): 1.02 on a [0,10] scale.
=> Profile choice changes the verdict by 1.02 points for the same codebase.
```

The simulation has weak a11y (`Inter` ~4) and strong Maintainability
(~7), so `internal-tool` (which leans on Maintainability) scores
highest and `accessibility-critical` (which leans on Interaction
Capability) scores lowest. Pick the profile that matches your domain;
don't pick to "make the score look better" — that's a code review
of yourself.

## How it works

When you run `rax audit`, the CLI orchestrates the entire pipeline below
for you. Power users can call individual scripts when debugging — see
the maintainer table in *Commands at a glance*.

The flow, in prose: `rax audit` calls `scripts/invoke_audit.sh`, which
in turn (1) runs `gather_context.sh` to figure out the framework and
files in scope, (2) runs `deterministic_layer.sh` over Semgrep / ESLint
/ tsc / madge / jscpd / npm audit and parses the findings into
`rax-deterministic.json`, (3) runs `build_prompt.py` to compose a
prompt out of the rubric, reference-guided anchors, and the
deterministic findings, and (4) hands that prompt to `claude -p`
(or prints it for paste-into-Claude when `claude` isn't on PATH).
The skill (`SKILL.md`) walks Claude through producing a JSON output
that conforms to `audit-output.schema.json`. From there, `scoring.py`
blends the deterministic and LLM scores with `α·det + (1-α)·llm`,
`aggregation.py` runs Quamoco/MAUT plus a Monte Carlo to lift
sub-characteristic intervals to category and overall, and
`conformal.py` applies the 90% calibration band. The final report is
written to disk via `rax report save`.

The diagram below shows the same flow visually:

```text
$ rax audit                  ← user types one command (or triggers SKILL.md)
  │
  └── bin/rax audit
        │
        └── scripts/invoke_audit.sh
              │
              ├──[1]── scripts/gather_context.sh        framework / files / git context
              │
              ├──[2]── scripts/deterministic_layer.sh   semgrep · eslint · tsc
              │           │                             madge · jscpd · npm audit
              │           ▼
              │       parse_deterministic.py  →  $RAX_OUT_DIR/rax-deterministic.json
              │
              ├──[3]── scripts/build_prompt.py
              │           ├── references/rubric-v2.md
              │           ├── reference-guided anchors (synthetic_anchors/)
              │           └── deterministic findings JSON
              │           ▼
              │       $RAX_OUT_DIR/rax-prompt.txt
              │
              └──[4]── claude -p "$PROMPT"   (or: print prompt if claude not on PATH)
                          │
                          ▼
                      SKILL.md  →  Claude reads rubric, scores 1-4 per
                          │        ISO sub-char, outputs JSON conforming to
                          │        audit-output.schema.json
                          ▼
                      [optional, --mode=full]  scripts/judge_panel.py
                          │                    Claude · GPT-4o · Gemini × N
                          ▼
                      scripts/scoring.py     HybridScore = α·det + (1-α)·llm
                          ▼
                      scripts/aggregation.py Quamoco/MAUT + sigmoid penalty
                          ▼
                      scripts/conformal.py   90% CI per sub-char + Monte
                          │                  Carlo to category and overall
                          ▼
                      rax report (intervals, abstentions, transparency footer)
                          ▼
                      `rax report save --file <path>`  →  .claude/rax/reports/<ts>.md
```

## Honesty footer (always in every report)

> Scores are 90% confidence intervals, not point estimates.
> Sub-chars tagged ABSTAINED could not be evaluated reliably (panel
> disagreement or insufficient calibration).
> The rax corpus does not include human-validated ground truth;
> calibration uses proxy signals — synthetic anchors, mined
> defect-density, cross-LLM consensus. See `references/corpus.md`.

This block is the canonical wording. Every rax report appends it
verbatim; `references/report-format.md` references this section
rather than duplicating the text.

## CI integration

For per-PR audits in GitHub Actions, copy
[`.github/workflows/rax-audit-on-pr.yml`](./.github/workflows/rax-audit-on-pr.yml)
into your project and add an `ANTHROPIC_API_KEY` secret. The workflow:

- Runs `rax audit --mode=quick` on every PR that touches `src/**` (adjust
  the `paths:` filter for your project layout).
- Posts a GitHub **Check** with the median + interval as the summary.
- Uploads the full report as an artifact for human review.
- Uses `conclusion: neutral` rather than pass/fail — rax produces
  calibrated intervals, not thresholds. Forcing a hard pass/fail would
  be exactly the false-precision rax explicitly rejects.

For release-grade audits (`--mode=full`, multi-judge × 5 replicates),
run locally before tagging — that mode is too expensive for every PR.

## FAQ

**How much does an audit cost?**

It depends on how you invoke rax. There are two paths:

- **Via the Claude Code skill ("audit my code" / `rax audit` while Claude Code is on PATH).** The LLM calls run inside your Claude Code plan (Pro, Max, Team, Enterprise), so audits cost **$0 incremental** — they consume the same allowance you already pay for. The deterministic layer (Semgrep / ESLint / tsc / madge / jscpd / npm audit) runs locally and costs $0 too. **For most users this is the right path: zero per-audit cost on top of a plan you already have.**

- **Via direct provider APIs** (you set `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY` and run rax outside Claude Code, e.g. on a CI runner). Pay-per-token applies:
  - `--mode=quick` (1 model × 1 call): ~$0.30 cold, less with prompt caching.
  - `--mode=full` (3 models × 5 replicates = 15 calls): ~$2-3 with prompt caching, up to $3.50 on a large codebase without caching.
  - A daily quick + weekly full schedule on a single repo runs to roughly **$20-25/month** at direct-API rates.

The deterministic layer is always free either way.

**Do I need API keys to run rax?**

No, if you use the Claude Code skill path (recommended). Yes, only if you want to run rax outside Claude Code or if you want `--mode=full`'s multi-judge panel (which uses GPT-4o and Gemini in addition to Claude — Claude Code only covers Claude). Without keys, `--mode=full` falls back to single-judge with an explicit warning.

**Are runs reproducible?**
- The deterministic layer is fully reproducible — same inputs, same findings.
- The LLM panel runs at `temperature=0.3` so outputs vary slightly per call. The conformal layer is built around that variance: run-to-run intervals overlap heavily and the *median* moves much less than the variance of any single judge would suggest.
- For tightest reproducibility, increase `--replicates` in `--mode=full`.

**What if `claude` isn't installed?**
- `rax audit` prints the composed prompt to stdout with a banner that says where to paste it (any Claude Code UI works). The deterministic layer still runs and its findings are visible in the prompt.
- To skip both: `rax audit --no-deterministic`. You lose Semgrep/ESLint/tsc coverage; recommended only when you're sanity-checking the LLM path.

**Which profile do I pick?**
- Default to `consumer-app` for any consumer mobile/web app.
- Switch to `fintech` only for trading/banking/payments code (Security weight jumps to 0.30).
- Switch to `internal-tool` for B2B / dashboards (Maintainability weight jumps to 0.35).
- Switch to `accessibility-critical` for gov / health / education (Interaction Capability jumps to 0.30).
- **Don't pick a profile to make the score look better.** Pick the one that matches your domain; the profile is recorded in the report header, so reviewers can see the choice.

**Can I add my own ISO sub-characteristic?**
No. The 41 sub-characteristics in `references/rubric-v2.md` come from ISO/IEC 25010:2023 — that's the contract. You can adjust *weights* per profile (or define a new profile via `extends:`) but not invent new buckets, otherwise scores stop being comparable across rax users.

**The Overall is 7.3 but Security is 4.2 — should I trust the headline?**
Read the per-ISO table, not just the Overall. If a critical sub-characteristic (Security/Confidentiality, Reliability/Faultlessness, etc.) is below its anchor for "acceptable", the Overall is misleading. The kiwichat audit in `docs/example-audits/` is the canonical example of this pattern.

## Getting help

- **Bugs and feature requests** — open an issue on GitHub: <https://github.com/reynsu/rax/issues>.
- **Security issues** — please don't open a public issue. Use GitHub's
  private vulnerability reporting: *Security → Report a vulnerability*
  on the repo's Security tab.
- **Questions about scoring or methodology** — file a discussion or an
  issue with the `question` label. The corpus and rubric are versioned
  on disk (`references/rubric-v2.md`, `references/corpus.md`); cite the
  specific sub-characteristic ID (`ISO_SEC_CONF`, etc.) and version so
  the answer stays anchored.

## Documentation index

| Document | Purpose |
|---|---|
| [SKILL.md](./SKILL.md) | The Claude Code skill definition — triggers, workflow, principles, what Claude is told to do during an audit |
| [docs/v1-to-v2.md](./docs/v1-to-v2.md) | Detailed v1→v2 migration: side-by-side architecture, category mapping, upgrade steps. UX preserved; only the engine changed |
| [CHANGELOG.md](./CHANGELOG.md) | Release-format diff between versions |
| [references/iso25010-mapping.md](./references/iso25010-mapping.md) | ISO/IEC 25010:2023 mapping with bidirectional v1 ↔ v2 table |
| [references/rubric-v2.md](./references/rubric-v2.md) | The 41 sub-characteristics, anchors at 3/6/8/10, deterministic-coverage α |
| [references/deterministic-coverage.md](./references/deterministic-coverage.md) | Per-sub-char α + tools that cover each |
| [references/corpus.md](./references/corpus.md) | Epistemology of the 4 corpus layers — what each is, what it isn't |
| [references/report-format.md](./references/report-format.md) | v2 report shape with v1-compat rules |
| [references/audit-output.schema.json](./references/audit-output.schema.json) | JSON Schema for the LLM-side output |
| [references/scale-mapping.yaml](./references/scale-mapping.yaml) | 1-4 internal → 1-10 user-visible mapping (per-sub-char overrides) |
| [prompts/audit-system.md](./prompts/audit-system.md) | The system prompt for the multi-judge panel |
| [docs/README-v1.md](./docs/README-v1.md) | The v1 README, preserved read-only |

## License

MIT — see [LICENSE](./LICENSE).

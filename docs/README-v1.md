<h1 align="center">rax</h1>

<p align="center">
  <b>Deep, scored, diffable audits for React &amp; React Native codebases.</b><br>
  A <a href="https://www.anthropic.com/claude-code">Claude Code</a> skill with a first-class CLI.
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#commands">Commands</a> ·
  <a href="#full-workflow-example">Workflow</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#configuration">Config</a> ·
  <a href="#faq">FAQ</a>
</p>

---

```console
$ rax audit --mode=diff
▶ running rax audit via Claude Code  (mode=diff)
  ...Claude reads the rubric, scans the diff, writes the report...
  saved .claude/rax/reports/2026-04-24T21-55-44Z.md (7.0/10, 6 findings)

$ rax score
7.0/10  ▼ -0.3 vs baseline (7.3)
last audit: 2026-04-24 21:55 · diff mode · commit 9bc2de7

$ rax delta
Score movement vs baseline
  baseline: commit abc1234 · 2026-04-23 14:15

  code   category                 base   →    curr   Δ
  SEC    Security                  6.5   →     9.0   ▲ +2.5
  ARC    Architecture              7.5   →     6.9   ▼ -0.6
  PRF    Performance               7.0   →     6.5   ▼ -0.5
  (8 categories unchanged)

  overall: -0.3  (7.3 → 7.0)  ▼ -0.3
  findings: 1 fixed · 2 new · 4 persisting

$ rax new
New findings introduced  (2)

  [HIGH  ]  PRF  src/screens/Cart.tsx:78
         New O(n²) price recomputation in Cart
         → Build a Map<ItemId, Promo[]> once in a useMemo keyed on cart.items.

  [MEDIUM]  ARC  src/features/cart/services/applyPromo.ts:8
         Cross-feature import from cart to catalog
         → Move shared Promo type to src/shared/types/promo.ts.
```

## Why rax

Running a code quality tool on your branch is one thing. Knowing **whether your changes made the codebase better or worse** is something else — and it's usually what you actually care about before pushing.

rax answers that question with:

- **11 weighted categories** (Architecture, Security, Performance, React patterns, UX/Accessibility, Type safety, Testing, Error handling, Code quality, Dependencies, Anti-patterns) summing to 100.
- **Every subcriterion scored 1–10** against explicit rubric anchors in `references/rubric.md` — not vibes. A 9 is "exemplary"; a 10 is "I cannot find anything to improve"; most real code lives at 5–8.
- **Baseline-aware deltas.** Every run computes `▲ +0.3`, `▼ −0.4`, `↔ 0.0` against your last saved baseline, per category and overall.
- **Finding-level diffing.** Each finding gets a stable fingerprint (SHA1 of `category | normalized_title | file:line`) so `rax new` and `rax fixed` work reliably across runs even when line numbers shift.
- **Red-flag rules.** Severe findings cap the affected category at ≤4 regardless of other subcriterion scores — a hardcoded secret cannot coexist with `SEC 8/10`.
- **Per-branch baselines.** Feature branches track their own ground truth independently of `main`.
- **Four modes**, matched to how you actually work: `quick` (staged files, ~30s, pre-commit), `diff` (vs baseline, pre-push), `focused` (one category), `full` (entire codebase, releases).

The scoring is done by Claude Code using the rubric; the CLI handles state (saving, parsing, diffing, querying). This split means **you can ask questions about your audits from your terminal without invoking Claude** — `rax score`, `rax pending --category=SEC`, `rax delta` all run locally against the saved reports.

## Features

- ✅ Single-command interface: `rax audit`, `rax score`, `rax pending`, `rax fixed`, `rax new`, `rax delta`, `rax baseline save|reset|info|list`, `rax history`, `rax show`
- ✅ Works as a Claude Code skill (natural language triggers) and as a standalone CLI (terminal commands)
- ✅ Report history — every run kept and queryable
- ✅ Per-branch baselines for long-lived feature branches
- ✅ Config file (`.claude/rax/config.json`) to override weights, ignore globs, disable subcriteria
- ✅ Git-hook friendly (exit codes `0` ok / `1` usage error / `2` no data)
- ✅ Color output with `NO_COLOR` opt-out
- ✅ Survives pipe-to-`head`, `less`, etc. without stack traces
- ✅ Cross-platform Python (3.8+) + Bash (4+)

## Quick start

```bash
# 1. Drop the skill into your repo
git clone https://github.com/<you>/rax.git .claude/skills/rax
#    or unzip the release:
#    unzip rax.zip -d .claude/skills/

# 2. Put `rax` on your PATH
bash .claude/skills/rax/install.sh

# 3. Ignore state in git
echo ".claude/rax/" >> .gitignore

# 4. First audit — full sweep, save as baseline
rax audit --mode=full --save

# 5. Before your next push
rax audit            # default: diff vs baseline
rax delta            # see what changed
```

Installation options are covered in full under [Install](#install).

## Commands

All commands run from anywhere inside your repo. State lives at `.claude/rax/`.

### Audit

```bash
rax audit [--mode quick|diff|focused|full] [--category CAT] [--save]
```

| Mode      | Scope                                   | Target time | When                         |
|-----------|-----------------------------------------|-------------|------------------------------|
| `quick`   | Staged files + direct imports           | ~30s        | pre-commit                   |
| `diff`    | Everything changed vs baseline          | ~1–2 min    | pre-push *(default)*         |
| `focused` | One category, entire codebase           | ~2–3 min    | deep-dive (needs `--category`) |
| `full`    | Entire codebase                         | ~5–10 min   | releases, baseline refresh   |

`--save` promotes the report to the baseline after it's done.

### View

```bash
rax score                        # headline: overall /10 + Δ vs baseline
rax scores                       # per-category table with weights and deltas
rax delta                        # detailed movement breakdown
rax show [ID] [--format F]       # full report (ID: latest|1|2|...|prefix)
                                 # F: full|summary|scores|raw
rax history [--limit N]          # list past audits with scores
```

Examples:

```bash
rax show 2                       # the second-most-recent report
rax show --format=summary        # condensed view
rax show 2026-04-23              # match by timestamp prefix
rax history --limit=10
```

### Findings

```bash
rax pending [--category C] [--severity S] [--limit N]    # open findings
rax fixed                         # resolved since baseline
rax new                           # introduced since baseline
```

`--severity` accepts `high` (includes critical/severe), `medium` (includes major), `low` (includes minor/info).

Examples:

```bash
rax pending --category=SEC                # only security
rax pending --severity=high               # only high-severity
rax pending --category=PRF --limit=5      # top 5 performance issues
rax fixed                                 # celebrate what you cleaned up
```

### Baseline

```bash
rax baseline save [--id ID]      # promote latest (or given) report to baseline
rax baseline info                # metadata of current baseline
rax baseline list                # all per-branch baselines
rax baseline reset               # clear (archived, not deleted)
```

### Misc

```bash
rax config init                  # create .claude/rax/config.json from template
rax config show                  # print current config
rax where                        # show install paths
rax version
rax help                         # detailed help
```

## Full workflow example

A typical feature-branch workflow:

```bash
# On main, at last release
$ rax audit --mode=full --save
...
saved .claude/rax/reports/2026-04-23T14-15-00Z.md (7.3/10, 8 findings)
baseline saved (overall 7.3/10, commit abc1234, branch main)

# Switch to feature branch, do work...
$ git checkout -b feature/cleanup
$ # ... code, code, code ...

# Before pushing
$ rax audit --mode=diff
saved .claude/rax/reports/2026-04-24T21-55-44Z.md (7.0/10, 6 findings)

$ rax delta
Score movement vs baseline
  baseline: commit abc1234 · 2026-04-23 14:15

  code   category                 base   →    curr   Δ
  SEC    Security                  6.5   →     9.0   ▲ +2.5
  ARC    Architecture              7.5   →     6.9   ▼ -0.6
  PRF    Performance               7.0   →     6.5   ▼ -0.5
  (8 categories unchanged)

  overall: -0.3  (7.3 → 7.0)  ▼ -0.3
  findings: 1 fixed · 2 new · 4 persisting

# What broke?
$ rax new
New findings introduced  (2)

  [HIGH  ]  PRF  src/screens/Cart.tsx:78
         New O(n²) price recomputation in Cart
         → Build a Map<ItemId, Promo[]> once in a useMemo keyed on cart.items.

  [MEDIUM]  ARC  src/features/cart/services/applyPromo.ts:8
         Cross-feature import from cart to catalog
         → Move shared Promo type to src/shared/types/promo.ts.

# Fix the Cart issue, re-audit
$ # ... edit src/screens/Cart.tsx ...
$ rax audit --mode=diff
$ rax delta
# PRF is back up; the new finding disappeared from `rax new`.

# Happy with the state — now on merge into main, update baseline
$ git checkout main && git merge feature/cleanup
$ rax audit --mode=full --save
```

## How it works

rax has two layers:

1. **Intelligence layer (Claude Code).** Reads files, applies the rubric in `references/rubric.md`, scans for the ~46 patterns in `references/antipatterns.md`, writes a report in the fixed format defined in `references/report-format.md`. This is what `rax audit` invokes.
2. **State layer (Python + Bash CLI).** Parses reports, fingerprints findings, saves/loads baselines, computes deltas, filters findings, renders tables. This is what every other `rax` subcommand runs — no LLM needed. Fast, deterministic, scriptable.

The split matters: once a report exists on disk, you can query it indefinitely from scripts, hooks, CI, or just your terminal without spending tokens or waiting on Claude.

### The report format is fixed

Every report follows the same Markdown template. Section order, score formats, table columns — all fixed. That's what makes reports diffable by a regex-based parser. Don't improvise with the format; the whole CLI depends on it.

### Finding fingerprints

Every finding gets a stable ID: `sha1(category | normalized_title | file:line)[:16]`. Line-number-only shifts (e.g. you added a comment above) don't change the fingerprint because we normalize ranges to their first line. Title case and whitespace are normalized too. This gives `rax new` and `rax fixed` stability across edits.

### Red-flag rules

Certain findings force their category to a score ceiling regardless of everything else:

- **SEC ≤ 4** — hardcoded secrets, `dangerouslySetInnerHTML` on user input, `eval` on user input, auth tokens in `AsyncStorage` unencrypted, HTTP (non-TLS) calls in production.
- **PRF ≤ 4** — render loops, O(n²) in a hot path, unbounded list without virtualization, memory leaks in mount-on-app-start components.
- **RXP ≤ 4** — conditional hooks, hooks outside components/hooks, mutation of state/props.
- **ERR ≤ 4** — zero error boundaries in a network-using app, swallowed `.catch(() => {})`.
- **UXA ≤ 4** — touchable without accessible name, color contrast <3:1 on primary flows.

Everything else is a graded finding. Full anchors are in `references/rubric.md`.

## Install

### Option 1 — per-repo (recommended)

The skill lives inside your project and anyone who clones gets it automatically.

```bash
git clone https://github.com/<you>/rax.git .claude/skills/rax
bash .claude/skills/rax/install.sh
echo ".claude/rax/" >> .gitignore
git add .claude/skills/rax .gitignore
git commit -m "Add rax skill"
```

### Option 2 — user-global

Install once for all your projects:

```bash
git clone https://github.com/<you>/rax.git ~/.claude/skills/rax
bash ~/.claude/skills/rax/install.sh
```

### Option 3 — git submodule

If you want to pin the skill version and pull updates cleanly:

```bash
git submodule add https://github.com/<you>/rax.git .claude/skills/rax
git submodule update --init
bash .claude/skills/rax/install.sh
```

### What `install.sh` does

Symlinks `bin/rax` into the first writable bin dir on `PATH`, in this order:

1. `$RAX_INSTALL_DIR` (if set)
2. `~/.local/bin` (created if missing)
3. `~/bin` (only if it already exists)
4. `/usr/local/bin` (with sudo, as a last resort)

If your chosen dir isn't on `PATH`, the script tells you exactly what to add to your shell rc. Re-running `install.sh` is idempotent.

### Uninstall

```bash
rm "$(command -v rax)"           # remove the PATH entry
rm -rf .claude/skills/rax        # remove the skill
# optionally: rm -rf .claude/rax # wipe state (baselines, history, reports)
```

## Git hooks & CI

`rax` exits `0` on success and non-zero on errors, so it plugs into hooks directly.

**`.husky/pre-commit`** (or `.git/hooks/pre-commit`):

```bash
#!/bin/sh
rax audit --mode=quick || exit 1
```

**`.husky/pre-push`**:

```bash
#!/bin/sh
rax audit --mode=diff || exit 1
rax delta
```

**GitHub Actions snippet** (pseudo — adapt to your secrets setup for Claude Code):

```yaml
- name: rax audit
  run: |
    bash .claude/skills/rax/install.sh
    rax audit --mode=diff
    rax delta
    # Fail the job if overall score dropped more than 0.5
    rax score | python -c "
    import sys, re
    m = re.search(r'▼ -(\\d+\\.\\d+)', sys.stdin.read())
    if m and float(m.group(1)) > 0.5:
        sys.exit(1)
    "
```

## Configuration

Drop `.claude/rax/config.json` to customize (generate with `rax config init`):

```jsonc
{
  "weights": {
    // must sum to 100. Raise SEC if security is mission-critical; lower TST if
    // you explicitly don't test.
    "SEC": 20, "PRF": 15, "ARC": 12, "RXP": 12, "CQR": 10,
    "UXA": 10, "TYP": 8,  "ERR": 7,  "TST": 2,  "DEP": 2, "APT": 2
  },
  "ignore": [
    "src/legacy/**",
    "**/*.generated.ts"
  ],
  "focus": [
    "src/features/checkout/**"
  ],
  "rules": {
    "disable": ["TST-3", "DEP-2"],
    "severity": {
      "SEC": "strict"      // raise floors for this category
    }
  },
  "scope": { "src_root": "src" },
  "reporting": { "language": "es" },
  "baseline": {
    "auto_save": false,
    "per_branch": true,
    "require_clean_tree": true
  }
}
```

See `templates/config.example.json` for the full template with inline comments.

## Architecture

```
rax/
├── SKILL.md                   # Claude Code skill entry (frontmatter + instructions)
├── README.md                  # this file
├── install.sh                 # symlinks bin/rax to ~/.local/bin
├── bin/
│   └── rax                    # CLI dispatcher (bash, ~250 lines)
├── scripts/
│   ├── rax_core.py            # all state/query logic (Python, ~1000 lines)
│   ├── gather_context.sh      # framework/stack detection + file scoping
│   └── invoke_audit.sh        # runs claude CLI or prints a ready-to-paste prompt
├── references/
│   ├── rubric.md              # 11 categories × subcriteria, anchors at 3/6/8/10
│   ├── antipatterns.md        # ~46 detectable patterns + grep hints + fixes
│   └── report-format.md       # fixed report template (the diff contract)
└── templates/
    └── config.example.json
```

## State layout

Inside your repo (this is what `.claude/rax/` looks like after a few runs):

```
.claude/rax/
├── baseline.json              # active baseline (the thing `delta` compares against)
├── config.json                # (optional) user overrides
├── reports/
│   ├── latest.md              # pointer to most recent report
│   ├── 2026-04-23T14-15-00Z.md
│   ├── 2026-04-24T09-30-00Z.md
│   └── 2026-04-24T21-55-44Z.md
├── baselines/
│   ├── main.json              # per-branch baseline snapshots
│   └── feature_cleanup.json
└── archive/
    └── baseline_20260423T141500Z.json   # archived on reset/overwrite
```

Everything under `.claude/rax/` is per-machine, per-checkout state. Commit the skill (under `.claude/skills/rax/`), **ignore the state** (`.claude/rax/`).

## Requirements

- **Python 3.8+** on `PATH` (set `RAX_PYTHON` to override).
- **Bash 4+**.
- **Git** — recommended; without it, rax runs in a degraded mode (no commit/branch metadata).
- **[Claude Code](https://www.anthropic.com/claude-code)** — for `rax audit` to run end-to-end non-interactively. Without it, `rax audit` prints a ready-to-paste prompt you can run in any Claude Code UI.
- **`jq`** — optional; speeds up `package.json` parsing. Falls back to `node` if installed.

All the view/query commands (`score`, `scores`, `delta`, `pending`, `fixed`, `new`, `show`, `history`, `baseline *`, `config *`) work with just Python + a saved report — no LLM needed.

## FAQ

<details>
<summary><b>Does this replace ESLint / TypeScript / Sonar?</b></summary>

No. rax is complementary. ESLint catches syntactic issues; TypeScript catches type errors; Sonar does static analysis. rax does **holistic architectural and quality review** that requires understanding intent — the kind of thing a senior engineer notices in PR review. Run all of them.
</details>

<details>
<summary><b>Why 11 categories and those weights?</b></summary>

The categories map to the dimensions a senior React/RN engineer actually cares about in review. The weights (SEC 13, ARC 12, RXP 12, PRF 12, CQR 10, UXA 10, TYP 8, TST 8, ERR 7, DEP 4, APT 4 = 100) bias toward things that hurt in production: security, architecture drift, and performance. You can override all of them in `config.json`.
</details>

<details>
<summary><b>How conservative is the scoring?</b></summary>

Very. The rubric anchors are calibrated so a 9 means "exemplary, I'd show this to a new hire as a reference" and a 10 means "I cannot find anything to improve." Most real production code scores 5–8 per category. The tool actively refuses score inflation — if you ask Claude to "just give me a 9," the skill pushes back and explains what a 9 requires from the rubric and what's currently missing.
</details>

<details>
<summary><b>What happens if Claude's analysis varies between runs?</b></summary>

Two defenses: (1) the rubric defines explicit anchors at 3/6/8/10 for every subcriterion so scoring is calibrated, not improvised; (2) the report format is fixed so runs are structurally diffable. Some score variance on subjective subcriteria (±0.5 typical) is expected — that's why the default tolerance for "unchanged" is ±0.05 and the headline is the delta, not the absolute number.
</details>

<details>
<summary><b>Does it work on Next.js / Remix / Expo?</b></summary>

Yes. `scripts/gather_context.sh` detects the framework and the rubric has framework-specific sub-rules. Tested shapes: React + Vite, CRA, Next.js, Remix, React Native (bare), React Native (Expo), React Native + Web.
</details>

<details>
<summary><b>Can I run it offline / without Claude?</b></summary>

The audit (`rax audit`) needs Claude — it's the LLM doing the actual code reading and scoring. Everything else (`score`, `scores`, `delta`, `pending`, `fixed`, `new`, `show`, `history`, `baseline`, `config`) runs purely locally against saved reports. So you can audit once with Claude, then query the saved state forever without a network.
</details>

<details>
<summary><b>How does the per-branch baseline work?</b></summary>

When you run `rax baseline save`, the baseline is written both to `.claude/rax/baseline.json` (the active pointer) **and** `.claude/rax/baselines/<branch>.json` (the per-branch snapshot). When you switch branches, the active pointer doesn't auto-switch — you'd need tooling in your branch-switch hook for that. For most workflows, the single active baseline + explicit `rax baseline save` on branch changes works fine.
</details>

<details>
<summary><b>Is the 30-second quick mode really 30 seconds?</b></summary>

With `claude -p` and a small staged diff (≤10 files, ≤500 lines), yes. With larger diffs it scales up. The hard cap is 20 files per `quick` run — if more are staged, rax audits the 20 longest and notes the truncation in the Scope section.
</details>

<details>
<summary><b>What's not yet implemented?</b></summary>

- `rax watch` (re-audit on file change)
- `rax compare <id1> <id2>` (diff two arbitrary reports, not just vs baseline)
- `rax export --format=json` (machine-readable output for CI integrations)
- SARIF output for GitHub code scanning

PRs welcome.
</details>

## Contributing

Contributions welcome, especially:

- New anti-pattern detectors (`references/antipatterns.md`)
- Additional framework detectors in `scripts/gather_context.sh`
- Better rubric anchors for subcriteria
- CLI ergonomics (tab completion, `--json` outputs, etc.)

The design principle: **the rubric and report format are stable contracts**. Everything else can evolve.

## License

MIT. See `LICENSE`.

---

<p align="center">
  Made for engineers who want to know whether their branch made the codebase better or worse.
</p>

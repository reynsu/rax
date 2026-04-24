# Report Format

The report is the product. Its shape is fixed so reports are diffable run-to-run. Do not improvise sections. Do not reorder. Do not add emoji to the scoring headers (emojis in category *names* in the table are fine and encoded in the template).

Write the report in Markdown to a temp path, then call `rax report save --file <path>` — the CLI moves it to `.claude/rax/reports/<ISO-timestamp>.md` and updates the `latest` pointer. Print the full report to the user in the chat.

## Template (copy this shape exactly)

```markdown
# React/RN Audit — <mode> · <YYYY-MM-DD> · <branch>@<short-sha>

- **Mode:** <quick|diff|focused|full>
- **Commit:** <full-sha>
- **Branch:** <branch>
- **Scope:** <N> files · <project type: React Web | React Native | Expo | Next.js | Remix | RN + Web> · TS <on|off>
- **Baseline:** <short-sha> from <YYYY-MM-DD> (<commits-ago> commits ago) · <or: "none">
- **Config:** default weights <or: "custom — see footer">

## Overall: <X.X>/10  <delta arrow> <± delta>

<One-sentence headline. For diff mode: lead with what changed. For full mode: lead with the overall health statement. No emojis. No hype.>

## Category scores

| ID  | Category                     | Score  | Δ       | Weight |
|-----|------------------------------|--------|---------|--------|
| ARC | Architecture & Structure     | X.X/10 | ▲ +0.3  | 12     |
| CQR | Code Quality & Readability   | X.X/10 | ↔  0.0  | 10     |
| RXP | React / RN Patterns          | X.X/10 | ▼ −0.4  | 12     |
| PRF | Performance                  | X.X/10 | ▲ +0.2  | 12     |
| SEC | Security                     | X.X/10 | ↔  0.0  | 13     |
| UXA | UI/UX & Accessibility        | X.X/10 | ↔  0.0  | 10     |
| TYP | Type Safety                  | X.X/10 | ↔  0.0  | 8      |
| ERR | Error Handling & Resilience  | X.X/10 | ↔  0.0  | 7      |
| TST | Testing                      | X.X/10 | ↔  0.0  | 8      |
| DEP | Dependencies & Bundle        | X.X/10 | ↔  0.0  | 4      |
| APT | Anti-patterns                | X.X/10 | ↔  0.0  | 4      |

## Critical issues

<Every red-flag and every subcriterion scoring ≤3. Empty section allowed — write "None." if truly none.>

### C1. [SEC] <finding title>
- **Where:** `src/api/client.ts:14`, `src/auth/session.ts:42`
- **Severity:** high
- **Why it matters:** <one sentence, concrete impact>
- **Score impact:** SEC capped at 4 by red-flag rule
- **Fix:** <concrete steps — not "refactor this">

### C2. [PRF] <finding title>
...

## Warnings

<Subcriteria scoring 4–5, plus any `major` anti-pattern hits not already in Critical. Group by category.>

### W1. [CQR] Three copies of `formatPrice` diverging
- **Where:** `src/utils/format.ts:23`, `src/components/Cart/Line.tsx:88`, `src/screens/Checkout.tsx:201`
- **Fix:** Consolidate into `src/utils/format.ts` — the checkout variant has a bug the others fixed.

### W2. ...

## Regressions since baseline

<If no baseline: "No baseline for comparison.">
<Otherwise: list every subcriterion that dropped by ≥0.5, and every new Critical/Warning finding.>

- **[RXP-1 Hooks correctness]** 8 → 6  — conditional hook introduced at `src/hooks/useFeatureFlag.ts:34`
- **NEW CRITICAL [SEC-1 Secrets]** — Sentry DSN committed at `src/monitoring.ts:5`

## Improvements since baseline

<If no baseline: omit this section.>

- **[TST-1 Coverage]** 5 → 7 — new tests under `src/features/checkout/__tests__/`
- **[CQR-2 Complexity]** 6 → 8 — `OrderSummary` refactored, cyclomatic complexity 18 → 7

## Top 3 actions (highest score-per-effort)

<Rank by (estimated-score-lift) / (estimated-effort-hours). Include the specific files.>

1. **Move the Sentry DSN to an env var.** (+~0.8 overall, ~10 min)
   - Files: `src/monitoring.ts:5`
   - Exact change: replace hardcoded string with `process.env.EXPO_PUBLIC_SENTRY_DSN`; add to `.env.example`.

2. **Wrap `ProductList` rendering in `FlatList`.** (+~0.5 overall, ~1h)
   - Files: `src/screens/Catalog.tsx:44-89`
   - Details: current `ScrollView` + `.map` renders ~200 items on mount; swap for `FlatList` with `keyExtractor={item => item.id}` and `getItemLayout` (items are fixed 72px).

3. **Add error boundaries per route.** (+~0.4 overall, ~2h)
   - Files: `src/router.tsx` (one place to add)
   - Details: wrap each `<Route element=>` in a route-level boundary with a retry action.

## Per-category detail

### ARC — Architecture & Structure · <X.X>/10

| Subcriterion                           | Score | Note                                                                             |
|----------------------------------------|-------|----------------------------------------------------------------------------------|
| ARC-1 Folder organization              | 8/10  | Feature-sliced with `shared/` for cross-cutting; clean.                          |
| ARC-2 Separation of concerns           | 6/10  | Data fetching mixed with view in `screens/Profile.tsx:20-120`.                   |
| ARC-3 Module boundaries & coupling     | 7/10  | Path aliases set; no circular deps; two cross-feature imports noted below.       |
| ARC-4 State management architecture    | 8/10  | React Query for server, Zustand for UI state, URL for nav — clear split.        |
| ARC-5 Feature cohesion                 | 7/10  | Checkout feature has leakage into `shared/ui/`; see `shared/ui/PaymentBadge.tsx`.|

**Findings:**
- `src/screens/Profile.tsx:20-120` — 100 lines of data fetching + formatting + view. Extract `useProfile()` hook.
- `src/features/checkout/services/orders.ts:12` imports `src/features/catalog/utils/formatCurrency.ts` — cross-feature.

### CQR — Code Quality & Readability · <X.X>/10

...

<repeat for every category — include subcriterion table + findings list>

## Scope notes

<What was and wasn't assessed. Caveats. Anything the reader must know to trust the score.>

- **Mode:** quick (staged files only). 7 files audited in scope.
- **Not assessed:** E2E tests (none exist in repo); native iOS/Android code (out of skill scope).
- **Deferred:** PRF-4 (bundle analysis requires `yarn analyze` — not run).
- **Inferred:** TST score assumes current coverage numbers from `coverage/coverage-summary.json`.
- **Config:** default weights used.

## Methodology

Rubric version 1.0 · Anti-patterns catalog v1.0 · Tool: rax skill

---
*Generated by rax · <timestamp> · Claude*
```

## Formatting rules

### Scores
- Always one decimal: `7.3`, not `7` or `7.34`.
- Subcriterion scores are integers: `7/10`, not `7.5/10`. Use 5 or 6 rather than 5.5.

### Deltas
- `▲ +X.X` for increases
- `▼ −X.X` for decreases (use minus sign −, not hyphen -)
- `↔  0.0` for no change (within ±0.05) — two spaces after `↔` to align the column
- **NEW** tag for findings not present in baseline
- **FIXED** tag for Critical/Warning items in baseline that are gone

### File references
- Single line: `path/to/file.tsx:42`
- Range: `path/to/file.tsx:42-58`
- Multiple: `path/to/file.tsx:42, 89, 132`
- Never omit the line number. If you can't give one, re-read the file.

### Category names
Use these exact identifiers (ARC, CQR, RXP, PRF, SEC, UXA, TYP, ERR, TST, DEP, APT) in brackets when cross-referencing findings. The identifiers are stable; only the long names change. Makes grep-ability real.

### Language
- Match the user's language for prose sections.
- Keep identifiers, file paths, config keys, and category codes in English.
- Code in code blocks is always English (keywords, APIs).

### Tone
- Factual. Not cheerful ("Great job!"), not doom ("This is a disaster").
- Credit wins in the Improvements section, not mid-sentence.
- No emoji in the body (the visual indicators ▲ ▼ ↔ are allowed; they're semantic).
- Avoid hedging words: "perhaps", "kind of", "might be". If you're not sure, don't score it.

### Length discipline
- A `quick` mode report: ~1–2 pages.
- A `full` mode report: 4–8 pages. Anything longer means per-category details aren't focused.
- Per-category findings: prioritize. 3–5 per category is plenty. Not a dump.

## Output channels

1. **Print to chat** — full report, rendered as Markdown.
2. **Save to file** — `.claude/rax/reports/<ISO-date>_<mode>_<short-sha>.md`. Print the path at the bottom of the chat output.
3. **Baseline update** — only on `full` mode with clean working tree, and only after confirming with user if overwriting a recent baseline.

## What the report must not do

- **Not** say "overall the code is good" as the headline. Use numbers.
- **Not** restructure the sections. They're in the order that matters.
- **Not** bury critical findings inside per-category detail. Critical goes in Critical.
- **Not** score without evidence. Every category has findings, or explain why not.
- **Not** compare to a baseline that doesn't exist. Say "No baseline" and proceed.
- **Not** promise more than it delivers. "Top 3 actions" means 3, not 8.

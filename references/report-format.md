# rax v2 audit report — format

> v1 report format is preserved at `references/report-format-v1.md`. v2
> reports always carry intervals; consumers built for v1 fall back to
> `interval = [score - 1, score + 1]` when reading a point-only report.

The report is the product. Its shape is fixed so reports are diffable
run-to-run. Do not improvise sections. Do not reorder.

Write the report in Markdown to a temp path, then call `rax report save
--file <path>` — the CLI moves it to `.claude/rax/reports/<iso>.md` and
updates the `latest` pointer.

---

## Header

```
# rax audit — <iso_date> · <commit_short> · <profile>

**Profile:**     consumer-app (default)
**Mode:**        full | quick | diff
**Rubric:**      rax-v2.0.0  (anchored to ISO/IEC 25010:2023)
**Corpus:**      v2.<N>      (synthetic anchors + mined + cross-LLM)
**Calibration:** empirical coverage <X>% (target band 85–95%)
**Panel:**       claude-opus-4-7 · gpt-4o · gemini-1.5-pro
**Tools (det):** Semgrep · ESLint · tsc · madge · jscpd · npm audit
```

## Overall

```
## Overall: [<p5>, <p95>]/10  (90% CI, median <p50>)
vs baseline [<p5>, <p95>]: overlap <X>%  → <verdict>

verdicts:
   overlap ≥ 70% → "no significant change"
   30% ≤ overlap < 70% → "uncertain"
   overlap < 30% with this < baseline → "likely regression"
   overlap < 30% with this > baseline → "likely improvement"
```

## By ISO 25010 characteristic

```
| ISO Characteristic    | CI 90%       | Median | Confidence | Δ vs baseline |
|-----------------------|--------------|--------|------------|---------------|
| Security              | [3.5, 5.0]   | 4.2    | high       | -0.4 (regr.)  |
| Maintainability       | [5.0, 7.5]   | 6.2    | medium     | +0.1          |
| Reliability           | ABSTAINED    | —      | low        | —             |
| Interaction Capability| [6.4, 8.1]   | 7.3    | high       | +0.0          |
| ...                   |              |        |            |               |
```

ABSTAINED rows are NOT included in the Overall calculation. The remaining
weights are renormalized; the report header explicitly notes how many
abstentions there were and which characteristics they affected.

## Findings

Findings are sorted by severity and then by ISO sub-characteristic.

### Critical
```
1. [SEC/Confidentiality] Hardcoded production secret
   - File:        src/config/api.ts:12
   - Detected by: deterministic (semgrep rax.sec.hardcoded-jwt-secret)
   - Severity:    high
   - Fix:         Move to env var loaded at runtime; rotate the leaked key.
```

### Warnings
```
2. [MAINT/Modularity] Cross-feature import bypasses public API
   - File:        src/features/checkout/CheckoutScreen.tsx:142
   - Detected by: panel (Claude + GPT-4 majority)
   - Severity:    medium
   - Fix:         Add src/features/payments/index.ts re-exporting only the
                  public surface, then change the import.
```

### Notes (low-severity / suggestion only)
```
3. [INTER/Inclusivity] alt text reads like filename
   ...
```

## Footer

```
Rubric:               rax-v2.0.0     (references/rubric-v2.md)
ISO mapping:          ISO/IEC 25010:2023  (references/iso25010-mapping.md)
Corpus version:       v2.<N>          (synthetic + mined + cross-LLM, no human)
Calibration coverage: <X>%            (target band 85–95%)
Panel:                <models, with replicate count>
Tools deterministas:  Semgrep · ESLint · tsc · madge · jscpd · npm audit
Profile:              <profile name + path>
Generated:            <iso datetime>

Honesty footer (always included): see the canonical wording in
the README's "Honesty footer" section. Reports embed it verbatim;
this file references the README rather than duplicating the text
to avoid the two copies drifting.
```

## Backward compatibility (v1 readers)

A v1 reader receiving a v2 report should:
- Read `Overall.median` as the v1 overall score.
- Read each row's `Median` column as the v1 category score.
- Treat ABSTAINED categories as `n/a`.

A v2 reader receiving a v1 report should:
- Treat each v1 score `s` as the synthetic interval `[max(0, s-1.0), min(10, s+1.0)]`.
- Compute Overall via `aggregate_intervals_to_overall` over the synthesized intervals.
- Mark the report with `compatibility: v1-upgraded`.

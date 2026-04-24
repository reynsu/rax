# Rubric — React / React Native Code Audit

This is the scoring authority. Every score traces back here. Each subcriterion has anchors at 3, 6, 8, and 10 so scores are comparable run-to-run. Intermediate scores are interpolations.

## How to score a subcriterion

1. Find the anchor you're *worse than or equal to* at the high end.
2. Find the anchor you're *better than or equal to* at the low end.
3. If evidence is split across levels, pick the lower one. Conservative scoring is a feature.
4. A subcriterion with **zero applicability** (e.g. a11y on a headless library with no UI) is marked `n/a` — not 10. `n/a` subcriteria are dropped from the category mean.
5. Write a one-sentence justification. If you can't, re-read the anchors.

## Table of contents

1. [ARC — Architecture & Structure](#arc--architecture--structure) (weight 12)
2. [CQR — Code Quality & Readability](#cqr--code-quality--readability) (weight 10)
3. [RXP — React / RN Patterns](#rxp--react--rn-patterns) (weight 12)
4. [PRF — Performance](#prf--performance) (weight 12)
5. [SEC — Security](#sec--security) (weight 13)
6. [UXA — UI/UX & Accessibility](#uxa--uiux--accessibility) (weight 10)
7. [TYP — Type Safety](#typ--type-safety) (weight 8)
8. [ERR — Error Handling & Resilience](#err--error-handling--resilience) (weight 7)
9. [TST — Testing](#tst--testing) (weight 8)
10. [DEP — Dependencies & Bundle](#dep--dependencies--bundle) (weight 4)
11. [APT — Anti-patterns](#apt--anti-patterns) (weight 4)

---

## ARC — Architecture & Structure

### ARC-1 Folder organization
- **3** — Flat `src/` with 50+ mixed files, or deep nesting with no clear rationale. New engineer cannot predict where a file lives.
- **6** — Top-level split by kind (`components/`, `screens/`, `utils/`) but features are scattered across them.
- **8** — Feature-sliced: each feature is a folder containing its components, hooks, types, tests. Shared code lives in `shared/` or `common/`.
- **10** — Feature slices with explicit public APIs (index re-exports), clear boundary between domain and infra, no cross-feature imports except through public APIs.

### ARC-2 Separation of concerns
- **3** — Components fetch data, hold business logic, format for display, and handle navigation in one file.
- **6** — Data fetching separated (hooks or query layer) but business logic still mixed with rendering.
- **8** — Clear layers: data (queries/services), domain (hooks/reducers), view (components). Each has a single reason to change.
- **10** — Domain layer is UI-agnostic (could swap React for Vue). View components are almost entirely presentational.

### ARC-3 Module boundaries & coupling
- **3** — Circular dependencies present; deep relative imports (`../../../`); features import each other's internals freely.
- **6** — Some relative-import pain, occasional coupling between features, no circular deps.
- **8** — Path aliases (`@/features/*`), feature boundaries respected, coupling only through typed interfaces.
- **10** — Enforced by tooling (ESLint boundaries plugin, dependency-cruiser, or equivalent).

### ARC-4 State management architecture
- **3** — State is everywhere — local useState, contexts, Redux, a singleton module, URL — with overlapping responsibilities.
- **6** — One global store (Redux/Zustand/Jotai/Context) but unclear when to use local vs global; server state mixed with UI state.
- **8** — Clear separation: server state in a query cache (React Query/SWR/RTK Query), UI state local or in a small global store, URL for navigational state, form state in a form library.
- **10** — Each state type has a documented home, enforced by convention and lint rules. No duplicate sources of truth.

### ARC-5 Feature cohesion
- **3** — Features leak implementation details; editing one feature routinely requires changes in three folders.
- **6** — Features mostly self-contained but shared utilities grow unchecked.
- **8** — High cohesion within features; shared code is deliberate, named, and small.
- **10** — Feature additions touch a single feature folder 90%+ of the time.

---

## CQR — Code Quality & Readability

### CQR-1 Naming
- **3** — `data`, `handleClick`, `Component2`, `utils.ts`; names obscure intent; inconsistent casing.
- **6** — Names are grammatical but generic (`UserCard`, `getData`, `handleSubmit`); readers must open the file to know what it does.
- **8** — Names describe behavior from the caller's perspective (`useDebouncedSearch`, `formatPriceForLocale`, `ShippingOptionList`). Consistent conventions (PascalCase components, camelCase hooks with `use` prefix).
- **10** — Names make the code skimmable: reading the function/component names in a file is a summary of what it does.

### CQR-2 Function / component size & complexity
- **3** — Components >300 lines; functions with cyclomatic complexity >15; deep nesting (5+ levels of conditionals).
- **6** — Most components <200 lines; a handful of large components; some deeply nested logic.
- **8** — Components <150 lines typical; complex logic extracted into hooks or pure functions; nesting ≤3 levels.
- **10** — Components read as composition; complex branches are replaced by polymorphism, small components, or well-named helpers.

### CQR-3 Duplication (DRY without being dogmatic)
- **3** — Copy-pasted component skeletons (list items, forms, cards) diverge subtly; bug fixes must be repeated.
- **6** — Some repeated JSX or helper logic that would benefit from extraction.
- **8** — Shared patterns extracted into reusable components/hooks; only incidental repetition remains.
- **10** — Abstraction is earned, not forced. No premature generalizations. The "rule of three" is respected.

### CQR-4 Comments & documentation
- **3** — No comments where needed (complex algorithms, non-obvious workarounds), or noisy comments that restate the code.
- **6** — Occasional "why" comments, README exists but is shallow.
- **8** — Non-obvious code has "why" comments. Public hooks/components have JSDoc. README explains setup and architecture.
- **10** — ADRs (architecture decision records) or equivalent document major choices. Onboarding is documented.

### CQR-5 Consistency
- **3** — Style varies across files; multiple patterns for the same thing (e.g. both `() => {}` and `function()`, both `*.module.css` and inline styles, both Redux and Zustand).
- **6** — Mostly consistent with occasional drift; one canonical styling approach, minor formatting variance.
- **8** — Prettier + ESLint enforced; one styling approach; one state approach; consistent file organization.
- **10** — Style is invisible — the code reads as if one person wrote it, and automated checks prevent drift.

---

## RXP — React / RN Patterns

### RXP-1 Hooks correctness
- **3** — Rules of Hooks violated: conditional hooks, hooks in loops, hooks outside components/hooks. `react-hooks/rules-of-hooks` missing or disabled.
- **6** — Rules followed, but `exhaustive-deps` warnings ignored or suppressed without explanation.
- **8** — Rules enforced; deps arrays correct; custom hooks composed cleanly; effects have a clear single purpose.
- **10** — Effects are rare (most logic is derived state or event handlers); when used, each has a documented lifecycle intent.

**Red flag**: Rules-of-Hooks violation → category ≤4.

### RXP-2 Component composition
- **3** — God components with a dozen props including render-controlling booleans (`isEditMode`, `isAdminView`, `isCompact`, `isLoading`).
- **6** — Props are reasonable but boolean-flag explosion in some places; prop drilling 3+ levels.
- **8** — Composition over configuration; `children`/slot patterns; compound components where appropriate.
- **10** — Components feel like Lego — small, focused, composable. Polymorphic props (`as`) or compound components solve configuration needs.

### RXP-3 Props API design
- **3** — Props mix concerns (data + UI + callbacks + styling overrides); type defs are loose (`any`, `object`); no `children` where the pattern calls for it.
- **6** — Props types exist but are inconsistent; some "convenience" props duplicate data available via context or parent.
- **8** — Props are minimal, cohesive, well-named; required vs optional is deliberate; defaults are explicit.
- **10** — Props are the documentation. Hovering any component tells you exactly how to use it.

### RXP-4 Keys & lists
- **3** — `key={index}` on lists that reorder or filter; missing keys; non-stable keys (`key={Math.random()}`).
- **6** — Keys are stable IDs where available but `index` used for static lists without justification.
- **8** — Keys are always stable IDs from the data; `index` only used when lists are truly static.
- **10** — Keys are correct, and list virtualization is considered when appropriate.

### RXP-5 Context usage
- **3** — A single massive context with all app state → whole tree re-renders on any change.
- **6** — Multiple contexts but poorly scoped; frequent re-renders from over-broad context values.
- **8** — Contexts are narrow and memoized; split by update cadence (theme vs auth vs feature flags).
- **10** — Context is used for dependency injection only; server/UI state lives in proper stores.

### RXP-6 Refs & imperative escape hatches
- **3** — Refs used to read state instead of using state; forwarded refs missing where needed; DOM manipulation bypasses React.
- **6** — Refs used correctly but typed loosely; some `any` on ref types.
- **8** — Refs used only for imperative DOM/native APIs; properly typed; `useImperativeHandle` used sparingly with a narrow surface.
- **10** — Imperative code is isolated, well-commented, and has a clear boundary.

### RXP-7 React Native specifics (RN only)
- **3** — Native modules accessed without platform checks; inline styles everywhere; no `Platform.select` where needed; gesture handling via raw `PanResponder` when modern libs exist.
- **6** — Platform splits done but inconsistent; styles in `StyleSheet.create` mostly; navigation integrated but with prop-drilling.
- **8** — Platform-aware code isolated; `StyleSheet.create` used consistently; navigation uses typed routes; `SafeAreaView`/insets handled.
- **10** — Platform code is negligible because abstractions cover the common cases; new screens drop in with no platform fiddling.

*Mark `n/a` for web-only React projects.*

---

## PRF — Performance

### PRF-1 Re-render hygiene
- **3** — Inline objects/arrays/functions passed to memoized children; context value recreated every render; `useCallback`/`useMemo` misused (wrong deps, unnecessary wrapping).
- **6** — Mostly fine but some unnecessary re-renders in hot components; memoization applied inconsistently.
- **8** — Memoization is deliberate and justified; expensive components are `React.memo`'d with correct equality; no inline props to memoized children.
- **10** — A profiler run on the heaviest screen shows no wasted renders.

### PRF-2 Memoization correctness (over and under)
- **3** — Either no memoization where it's needed, or `useMemo`/`useCallback` wrapping trivial primitives everywhere (net loss).
- **6** — Memoization present but deps arrays have bugs or include unstable references.
- **8** — Memoization is applied where measurable, with correct deps; primitives not memoized.
- **10** — Memoization is documented at the point of use when non-obvious, and tested for stability.

### PRF-3 List rendering
- **3** — `Array.map` rendering unbounded lists; RN lists using `ScrollView` + `map` instead of `FlatList`; missing `keyExtractor`; no `getItemLayout` for fixed-height rows; missing windowSize/maxToRenderPerBatch tuning on slow lists.
- **6** — `FlatList`/virtualized lists used; minor misconfigurations.
- **8** — Virtualization + correct keys + `getItemLayout` where applicable + memoized item components.
- **10** — Performance budgeted (scroll at 60fps on target devices), verified with profiler.

**Red flag (RN)**: Unbounded list in `ScrollView` → category ≤4.

### PRF-4 Bundle size & code splitting
- **3** — Single bundle, no code splitting; large deps (moment, lodash full) fully imported; barrel files forcing whole-module import.
- **6** — Route-level code splitting; tree-shakeable imports mostly; bundle analyzed once historically.
- **8** — Route + component-level splitting where it matters; smaller alternatives picked (date-fns, lodash-es); bundle analyzed in CI.
- **10** — Bundle size budgeted per route; regression gates in CI.

*RN: interpret as JS bundle size + startup time + hermes/flipper config.*

### PRF-5 Image & asset handling
- **3** — Full-res images loaded for thumbnails; no caching; no lazy loading; SVGs as `<img>` of raw files.
- **6** — Some responsive sizing; basic caching.
- **8** — Responsive images (srcset / `expo-image` / `FastImage`); lazy loading; formats chosen (WebP/AVIF); preloading on critical paths.
- **10** — Image strategy documented; LCP/FCP metrics or equivalent are budgeted.

### PRF-6 Effect & subscription hygiene
- **3** — Effects without cleanup that subscribe, set timers, or listen for events; state updated after unmount; effects that should be event handlers.
- **6** — Mostly cleaned up; occasional missing cleanup or overly-broad deps.
- **8** — Every subscription/listener/timer has matching cleanup; effects narrow in scope; no "run once" hacks like `useRef(false)`.
- **10** — Effects are few and deliberate; cancellation via `AbortController` for async work; state updates gated on mounted status only when unavoidable.

### PRF-7 Expensive computation
- **3** — Heavy work in render or on every keystroke; blocking the main thread; no debounce/throttle on high-frequency events.
- **6** — Some expensive work memoized; debouncing present but inconsistent.
- **8** — Heavy work memoized, debounced, or moved off the main thread (web workers / native threads); budgeted in ms.
- **10** — Performance-critical paths profiled and documented with budgets.

---

## SEC — Security

### SEC-1 Secret management
- **3** — API keys, tokens, or credentials committed to the repo or hardcoded in source.
- **6** — Secrets in `.env`, but `.env.example` is stale or missing; build-time env vars exposed to client (`REACT_APP_*` containing server-only secrets).
- **8** — Clear separation between build-time public env vars and runtime server secrets; secret rotation process exists.
- **10** — Secrets managed via a vault or platform secret manager; git history audited for leaked secrets; secret scanning in CI.

**Red flag**: Hardcoded secret in source → category ≤4.

### SEC-2 Injection & XSS surface
- **3** — `dangerouslySetInnerHTML` with user-derived content; user input concatenated into URLs or `href`; `eval`/`Function` used on user input.
- **6** — `dangerouslySetInnerHTML` used with sanitization but policy is implicit; user input in URLs via template literals.
- **8** — HTML sanitization via a vetted library (DOMPurify) with strict config; URLs constructed via `URL` API; no dynamic code execution on user input.
- **10** — CSP enforced (web); no `dangerouslySetInnerHTML` except in a documented, reviewed location.

### SEC-3 Sensitive data storage
- **3** — Auth tokens, PII, or payment data in `localStorage` (web) or plain `AsyncStorage` (RN); secrets logged to console.
- **6** — Tokens in `localStorage` with a plan to migrate; RN uses `AsyncStorage` with some encryption wrapper.
- **8** — Web: tokens in httpOnly cookies (when server-side) or memory + refresh; RN: `react-native-keychain`, `expo-secure-store`, or `EncryptedSharedPreferences`.
- **10** — Threat-modeled data classification; no sensitive data at rest client-side unless required; automatic purge on logout.

**Red flag**: Auth token in plain `AsyncStorage`/`localStorage` → category ≤4.

### SEC-4 Authentication & session handling
- **3** — Tokens without expiry checks; no refresh logic; auth state derived from multiple sources; route guards only in UI (trivially bypassable).
- **6** — Token refresh exists but has race conditions; logout doesn't clear all state.
- **8** — Single source of auth state; token refresh with request deduplication; clean logout; route protection both in UI and at the API layer.
- **10** — Auth flows tested; session fixation/CSRF mitigated; suspicious-activity signals propagated.

### SEC-5 Network security
- **3** — HTTP (non-TLS) endpoints in production; `fetch` with `rejectUnauthorized: false`; no certificate pinning on sensitive RN apps.
- **6** — TLS everywhere; basic error handling on network failures.
- **8** — TLS enforced; API client rejects invalid certs; sensitive RN apps use pinning; CORS configured intentionally on web.
- **10** — Pinning with backup pins and rotation plan; network failure modes tested; traffic minimization reviewed.

**Red flag**: HTTP endpoint in production code → category ≤4.

### SEC-6 Input validation & output encoding
- **3** — User input reaches downstream systems unvalidated; types are treated as proof of safety (they aren't); output encoding missing where needed.
- **6** — Validation at form layer but trusted downstream; runtime validation uneven.
- **8** — Runtime validation at trust boundaries (Zod/Yup/Valibot); output encoding correct for context.
- **10** — Validation schemas are the types; single source of truth; fuzzing or property-based tests on critical parsers.

### SEC-7 Dependency supply chain
- **3** — `npm audit` shows high/critical vulns that are reachable; no lockfile; unmaintained deps with no alternative.
- **6** — Lockfile present; audit occasional; some known vulns with mitigations.
- **8** — Lockfile committed; Dependabot or Renovate configured; audit in CI with sensible thresholds; license review.
- **10** — SBOM generated; provenance checked; dep churn deliberate.

### SEC-8 Mobile/platform-specific (RN only)
- **3** — Deep links accepted without validation; WebView loads arbitrary URLs; Android `allowBackup=true` with sensitive data; iOS URL schemes overlap with common ones.
- **6** — Deep links validated at entry but logic inconsistent; WebView config partially hardened.
- **8** — Deep link schemas typed and validated; WebView restricted (`originWhitelist`, JS bridge audited); platform manifests reviewed.
- **10** — Mobile-specific threat model documented; jailbreak/root detection where warranted; tamper detection on release builds.

*Mark `n/a` for web-only projects.*

---

## UXA — UI/UX & Accessibility

### UXA-1 Semantics & a11y roles
- **3** — `<div onClick>` for buttons; images without `alt`; form fields without labels; RN `TouchableOpacity` without `accessibilityLabel`.
- **6** — Mostly semantic HTML / RN accessibility props; gaps in less-trafficked areas.
- **8** — Semantic elements throughout; all interactive elements have accessible names and roles; landmarks used.
- **10** — Tested with screen reader (VoiceOver, TalkBack, NVDA); navigation narrated correctly; live regions for dynamic content.

**Red flag**: Touchable without accessible name on a primary user flow → category ≤4.

### UXA-2 Keyboard / focus management (web) or focus order (RN)
- **3** — Tab traps; focus lost after modal close; focus outlines removed globally; order doesn't match visual order.
- **6** — Modals restore focus; some manual focus management where needed.
- **8** — Focus follows activation correctly; skip links; visible focus styles that meet contrast; trap/restore patterns in modals.
- **10** — Full keyboard operability verified; focus order matches reading order; docs for keyboard shortcuts.

### UXA-3 Color contrast & visual accessibility
- **3** — Text below WCAG AA (4.5:1 normal, 3:1 large); color-only state indication.
- **6** — Most text meets AA; some callouts (placeholders, helper text) fail.
- **8** — All text and interactive elements meet WCAG AA; non-color indicators for state.
- **10** — Design tokens enforce contrast; AAA for critical flows; dark/light parity verified.

**Red flag**: Primary-flow contrast <3:1 → category ≤4.

### UXA-4 Loading, empty, and error states
- **3** — No loading states (UI jumps); no empty states (blank screens); no error states (silent failures or raw error dumps).
- **6** — Spinners exist; empty/error states on main screens only.
- **8** — Every async boundary has all four states (idle, loading, success, error); skeletons used where they improve perceived performance; errors are actionable.
- **10** — State taxonomy documented; error recovery paths tested; all empty states educate the user.

### UXA-5 Responsive / adaptive layout
- **3** — Fixed widths; horizontal scroll on mobile; RN: no adaptation for tablet or landscape.
- **6** — Main breakpoints handled; some edge cases (very small / very large screens) ignored.
- **8** — Fluid layouts; breakpoint system; RN: responsive to orientation and size classes.
- **10** — Tested on real device matrix; safe-area and notch/cutout handling; zoom/text-scale respected.

### UXA-6 Touch targets & motion (mobile / touch)
- **3** — Touch targets <32pt; motion without `prefers-reduced-motion` respect; transitions block interaction.
- **6** — Targets mostly ≥40pt; reduced-motion honored on obvious animations.
- **8** — Targets ≥44pt on all primary actions; reduced-motion honored throughout; gestures have visual/haptic feedback.
- **10** — Haptics deliberate and consistent; motion budget documented; test matrix includes reduced-motion users.

### UXA-7 Internationalization & localization
- **3** — Hardcoded strings in components; ltr-only layouts; no plural or date formatting.
- **6** — I18n library in place but coverage incomplete; some hardcoded strings remain.
- **8** — Strings in one place; plurals/dates/currency formatted per locale; RTL tested.
- **10** — Pseudo-localization in CI; locale coverage monitored; content model supports translator workflow.

*Mark `n/a` for single-locale internal tools if explicitly scoped so.*

---

## TYP — Type Safety

### TYP-1 TypeScript strictness
- **3** — `strict: false` or no TypeScript at all in a project that would benefit; `// @ts-ignore` comments without justification.
- **6** — `strict: true` but with `strictNullChecks` loopholes or many `@ts-expect-error`.
- **8** — Full strict mode (`strict`, `noUncheckedIndexedAccess`, `noImplicitOverride`); `@ts-expect-error` only with comments and ticket references.
- **10** — Strictest practical config; type-coverage metric monitored.

### TYP-2 `any` and escape hatches
- **3** — `any` sprinkled throughout; `as unknown as Foo` casts; type assertions instead of validation.
- **6** — `any` in a few places with TODOs; assertions at boundaries.
- **8** — `any` restricted to truly dynamic areas and documented; `unknown` preferred; type guards do real checks.
- **10** — `any` is effectively prohibited; `unknown` + narrowing is the pattern.

### TYP-3 Runtime validation at boundaries
- **3** — External data (API, URL params, form input, storage) treated as typed without validation.
- **6** — Some boundaries validated; others rely on compile-time types for runtime data.
- **8** — All external boundaries validated with Zod/Yup/Valibot or equivalent; inferred types from schemas.
- **10** — Schema-first: types derive from schemas; fuzz/property tests on critical parsers.

### TYP-4 Types communicate intent
- **3** — Types mirror the data shape only; no branded types; no discriminated unions where they'd clarify state.
- **6** — Some domain types; unions used for states.
- **8** — Branded types for IDs; discriminated unions for state machines; `Readonly` used; types enforce invariants.
- **10** — Types make illegal states unrepresentable; parse-don't-validate is the idiom.

---

## ERR — Error Handling & Resilience

### ERR-1 Error boundaries
- **3** — No error boundaries; a single component error crashes the whole app.
- **6** — One top-level error boundary; routes not individually isolated.
- **8** — Error boundaries at strategic layers (app, route, risky sub-trees); fallback UIs are helpful, not generic.
- **10** — Error boundaries integrated with monitoring; recovery actions offered; distinct boundaries for distinct failure modes.

**Red flag**: No error boundaries in an app with network calls → category ≤4.

### ERR-2 Async error handling
- **3** — Promises without `.catch` or `try/catch`; rejections swallowed (`.catch(() => {})`); errors logged but not surfaced.
- **6** — Most awaits handled; some silent failures remain.
- **8** — Every await has a handler; errors propagate to a consistent sink (toast/log/monitoring); retries intentional.
- **10** — Error handling policies documented per error class; idempotent operations identified; retry/backoff strategies chosen per case.

**Red flag**: Empty `.catch(() => {})` on a user-facing call → category ≤4.

### ERR-3 User-facing error UX
- **3** — Raw error strings shown to users; errors in English only; no recovery actions.
- **6** — Friendly messages on main flows; some raw errors leak on edges.
- **8** — User-facing copy is clean, localized, and offers a next step (retry, support, fallback).
- **10** — Error UX reviewed by design/content; tone and content consistent; support handoff smooth.

### ERR-4 Logging & monitoring
- **3** — `console.log` debugging in production; no centralized error tracking; no source maps uploaded.
- **6** — Sentry or equivalent integrated; source maps sometimes uploaded; alerts loose.
- **8** — Errors captured with user/context/breadcrumbs; source maps reliable; meaningful alerts (not everything, not nothing).
- **10** — Error budgets, SLOs, or explicit targets; monitoring tied to releases; playbooks exist.

### ERR-5 Offline & degraded modes (RN/PWA especially)
- **3** — App white-screens offline; no feedback on network failure; cached data invisible.
- **6** — Basic offline indicator; some operations queue.
- **8** — Offline-first where appropriate; optimistic updates with rollback; queued mutations on reconnect.
- **10** — Full CRDT or sync strategy documented; reconciliation semantics clear; tested with real network conditions.

*Mark `n/a` for read-only or online-required tools.*

---

## TST — Testing

### TST-1 Coverage (as signal, not target)
- **3** — No tests, or vanity tests that don't assert behavior.
- **6** — Some tests on utils and a few critical components; coverage <40%.
- **8** — Critical paths covered (auth, checkout, data mutations); coverage 60–80% and trending up.
- **10** — Coverage is the byproduct, not the goal; every bug fix lands with a regression test.

### TST-2 Test quality
- **3** — Tests couple to implementation details (`expect(wrapper.state('x'))`); snapshot tests everywhere without review; flaky tests tolerated.
- **6** — Mostly behavior-focused tests; a few snapshots or implementation-coupled tests.
- **8** — Testing Library / React Native Testing Library used idiomatically; tests read like specs; no flake tolerated.
- **10** — Test utilities are themselves tested; flakiness is a P0; tests are fast.

### TST-3 Integration & E2E
- **3** — Unit tests only; no end-to-end coverage of user flows.
- **6** — Smoke E2E for happy path only; brittle selectors.
- **8** — E2E for critical flows (Playwright/Cypress for web, Detox/Maestro for RN); semantic selectors; run in CI.
- **10** — E2E tied to feature flags for canary rollout; visual regression where warranted; performance assertions in E2E.

### TST-4 Testability of code
- **3** — Components that are hard to test (side effects in render, direct imports of singletons, global fetch).
- **6** — Testable with some scaffolding; DI is manual.
- **8** — Components are easy to test because dependencies are injected/abstracted; hooks tested in isolation.
- **10** — Testability is a design principle; architecture supports testing at every seam.

---

## DEP — Dependencies & Bundle

### DEP-1 Freshness & maintenance
- **3** — Major versions behind; deprecated packages; peer dep warnings on install.
- **6** — Mostly current with a handful of stale deps; upgrade path planned.
- **8** — Auto-update tooling (Renovate/Dependabot) merges patches; majors reviewed quarterly.
- **10** — Upgrade cadence documented; breaking changes absorbed promptly.

### DEP-2 Footprint
- **3** — `moment`, full `lodash`, `rxjs`, and `axios` all present for trivial uses; duplicate functionality across deps.
- **6** — Some heavyweight deps remain but known; alternatives identified.
- **8** — `date-fns` or `dayjs` over `moment`; `lodash-es` or native ES; `ky`/`fetch` over `axios` when appropriate.
- **10** — Every dep justified against vanilla/smaller alternatives; bundle budgets enforced.

### DEP-3 Security posture
- **3** — High/critical CVEs in direct deps reachable from app code.
- **6** — Low/medium CVEs; transitive exposure mostly.
- **8** — `npm audit` clean at run threshold; advisories triaged.
- **10** — SBOM + provenance + automated advisory response.

---

## APT — Anti-patterns

Score this category as (10 − count_of_severe_antipatterns × 1.5), clamped to [1, 10]. "Severe" = any item in `antipatterns.md` tagged `severe`. Non-severe items subtract 0.5.

- **3** — Multiple severe anti-patterns present (god component, prop drilling >4 levels, effect-as-state, mutation).
- **6** — A few non-severe anti-patterns; one severe with a TODO.
- **8** — One or two minor anti-patterns; none severe.
- **10** — Clean. If you're considering 10, check `antipatterns.md` once more — you probably missed one.

See `antipatterns.md` for the full catalog with file:line detection hints.

---

## Custom weights

If `.claude/rax/config.json` overrides weights, use those. Validate that the override sums to 100 (tolerance ±0.5). If invalid, log a warning and use defaults. Print the active weights in the report header.

## When a subcriterion is unscorable

Prefer to score low (conservative) over marking `n/a`, unless the subcriterion is categorically inapplicable:

- Testing subcriteria on a project with explicit "no automated tests" policy documented → `n/a`
- A11y on a headless CLI or library with no UI → `n/a` for UXA entirely
- RN-specific subcriteria on a web-only project → `n/a`

Never mark `n/a` to hide findings. If you can't assess because of scope (quick mode, not enough files), mark it `deferred` — which counts as the baseline value for aggregation purposes, but is flagged in scope notes.

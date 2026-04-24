# Anti-patterns Catalog — React / React Native

Forty-plus detectable anti-patterns, each with: why it's bad, how to detect it (including `rg`/`grep` hints you can run directly), how to fix it, and severity. Severity drives the APT (anti-pattern) category score and surfaces critical items.

## Severity legend

- `severe` — high blast radius (data loss, crashes, security). Counts as 1.5 in APT scoring.
- `major` — bugs or significant perf/maintainability cost. Counts as 1.0.
- `minor` — smell, future-tax. Counts as 0.5.

---

## Table of contents

**Hooks & lifecycle** (1–10)
**Component design** (11–18)
**State management** (19–24)
**Performance** (25–32)
**React Native specific** (33–38)
**Styling & UI** (39–42)
**General** (43–46)

---

## Hooks & lifecycle

### 1. Conditional hooks — `severe`

Hooks called inside `if`, loops, or after early returns.

**Detect:**
```
rg -n "^\s*(if|for|while|switch)[^{]*\{[^}]*use[A-Z]" --type ts --type tsx
rg -n "return\s[^;]*;[\s\S]{0,500}use[A-Z]" --type tsx
```
Also: trust ESLint `react-hooks/rules-of-hooks`. If it's disabled, that alone is `severe`.

**Why:** React relies on call order to match hooks to state slots. Conditionally skipping one shifts every subsequent hook's state into the wrong slot. Symptoms: "Rendered more/fewer hooks" crashes, stale or swapped state.

**Fix:** Move the condition inside the hook (pass a disabled flag), or split into two components.

---

### 2. Stale closure in `useEffect` — `major`

Effect reads state but state is missing from deps (or deps array is `[]` by inertia).

**Detect:**
```
rg -nB1 "useEffect\s*\(\s*\(\s*\)\s*=>\s*\{" --type tsx | rg -B3 ", \[\]"
```
Then cross-reference with variables referenced inside. Also: suppressed `eslint-disable-next-line react-hooks/exhaustive-deps` without justification comment.

**Why:** The closure captures old values; the effect does the wrong thing with stale data.

**Fix:** Include the dependency. If it re-runs too often, either memoize the dep or pull the logic into a ref pattern — but only after justifying it in a comment.

---

### 3. Effect-as-state — `major`

Syncing derived data via effect when it could be computed directly in render.

**Detect:** pattern of `useState` + `useEffect` that sets the state from props/other state.
```
rg -nA5 "useState" --type tsx | rg -B5 "useEffect.*setState"
```

**Why:** Extra render; possibility of stale sync; exposes timing bugs.

**Fix:** Compute directly:
```tsx
// Before
const [full, setFull] = useState('');
useEffect(() => { setFull(`${first} ${last}`); }, [first, last]);

// After
const full = `${first} ${last}`;
```
Memoize only if the computation is expensive.

---

### 4. Event handler as effect — `major`

Using `useEffect` to react to a user action (e.g. submit analytics on a button press).

**Detect:** effects whose only trigger is a user-driven state flip.

**Why:** Effects are for synchronizing with external systems, not for reacting to events. Events run once per action; effects run whenever deps change — including Strict Mode double-invocations, back-nav restoration, etc.

**Fix:** Put the logic in the event handler where it belongs. The React docs ("You Might Not Need an Effect") are canonical.

---

### 5. Missing cleanup — `major` (`severe` if subscription/timer in app-lifetime component)

Subscriptions, timers, listeners, or `AbortController`s without a cleanup return.

**Detect:**
```
rg -nA5 "useEffect" --type tsx | rg -B1 "(addEventListener|subscribe|setInterval|setTimeout|on\()" | rg -vA5 "return \("
```
Visually: any `useEffect` that creates something cleanup-worthy and doesn't `return () => ...`.

**Why:** Memory leaks, duplicate listeners, state updates on unmounted components, "cannot update state on unmounted component" warnings.

**Fix:** Return a cleanup function. For fetches, use `AbortController` and abort in cleanup.

---

### 6. "Run once" with `useRef(false)` flag — `minor`

```tsx
const ranRef = useRef(false);
useEffect(() => { if (ranRef.current) return; ranRef.current = true; /* ... */ }, []);
```

**Why:** Fights Strict Mode; hides a real design issue (side effect belongs elsewhere, or should be idempotent).

**Fix:** Make the operation idempotent, or move it to an event handler / app bootstrap.

---

### 7. `useLayoutEffect` misused — `minor`

Using `useLayoutEffect` when `useEffect` would do (or vice versa).

**Detect:** `useLayoutEffect` used for non-DOM-measuring work; `useEffect` used to read layout and causing flash.

**Fix:** `useLayoutEffect` only when you need to measure or mutate the DOM before paint. Everything else uses `useEffect`.

---

### 8. Setting state during render — `severe`

```tsx
function X() {
  if (cond) setState(1); // bad — infinite loop or warning
  return <div/>;
}
```

**Detect:**
```
rg -n "setState|dispatch\(" --type tsx | rg -vB1 "(handleClick|on[A-Z]|useEffect|useCallback)"
```

**Why:** React throws. When it doesn't throw, it's because of a bug that will bite.

**Fix:** Compute the value and render it; or use `useEffect`; or move state up.

---

### 9. Custom hook that isn't — `minor`

A function named `useX` that doesn't use any hooks itself, or a function using hooks that isn't named `useX`.

**Detect:** linter catches this; also:
```
rg -n "^function use[A-Z]" --type ts --type tsx
```
then verify each uses at least one hook.

**Why:** Breaks the cognitive contract. Lint rules misfire.

**Fix:** Rename, or start using a hook.

---

### 10. Hooks inside JSX — `severe`

```tsx
<div>{items.map(() => { const x = useState(); ... })}</div>
```

**Detect:** hooks inside `.map` or other callbacks.

**Why:** Violates rules of hooks.

**Fix:** Move into a child component.

---

## Component design

### 11. God component — `major`

>300 lines, 10+ props, multiple responsibilities, deep conditionals.

**Detect:**
```
wc -l $(fd -e tsx -e jsx) | sort -rn | head -20
```
Then review the top offenders.

**Fix:** Extract subcomponents by responsibility; move business logic to hooks; split conditional branches into distinct components.

---

### 12. Boolean flag explosion — `major`

Props: `isEditMode`, `isAdmin`, `isCompact`, `isLoading`, `isDisabled`, `isReadOnly`, ...

**Why:** Combinatorial explosion, untestable; "view modes" are hiding actually-distinct components.

**Fix:** Prefer a `variant` discriminated union, or split into distinct components. Example:
```tsx
// Before: <UserCard isAdmin isCompact isEditMode />
// After:  <AdminUserCard compact /> or <UserCard.Edit />
```

---

### 13. Prop drilling >3 levels — `major`

Same prop passed through intermediate components that don't use it.

**Detect:** review the `props.children`-heavy layouts for repeated prop names.

**Fix:** Component composition (push the consumer up, the source down); or a narrow context; or the right abstraction (e.g. a form library for form state).

---

### 14. Render props that should be children — `minor`

`<X render={() => <Y/>}/>` when `<X><Y/></X>` would do.

**Fix:** Use `children`.

---

### 15. Leaky component API — `major`

Props that expose internal state (`setInternalRef`, `internalClassName`, `__dangerous_style_override__`).

**Why:** Callers reach into the component; refactoring internals breaks them.

**Fix:** Design a real API (variants, slots, a theme system). If an escape hatch is needed, make it one clearly-named prop with a typed shape.

---

### 16. Fragment children passed to components expecting a single element — `minor`

Leads to `React.Children.only` errors or weird behavior.

**Fix:** Wrap, or redesign.

---

### 17. Conditional rendering with `&&` on numbers — `major`

```tsx
{items.length && <List items={items}/>}  // renders '0' when empty
```

**Detect:**
```
rg -n "\.length &&" --type tsx
```

**Fix:** `items.length > 0 &&` or a ternary.

---

### 18. Missing `key` or `key={index}` on reordered lists — `major`

**Detect:**
```
rg -n "\.map\([^)]*\)\s*=>[^}]*<" --type tsx
```
Then check each hit's key.

**Why:** React can't track identity; wrong components update; state (like focused inputs) moves to the wrong row.

**Fix:** Stable IDs. If truly no ID, compose one from stable fields.

---

## State management

### 19. Massive single context — `major`

One context with `user`, `theme`, `cart`, `settings`, `feature flags`.

**Why:** Any change re-renders every consumer.

**Fix:** Split by update cadence. Memoize the value.

---

### 20. Context value recreated every render — `major`

```tsx
<X.Provider value={{ a, b }}>  // new object each render
```

**Detect:**
```
rg -n "Provider value=\{\{" --type tsx
```

**Fix:** `useMemo`.

---

### 21. Server state in client store — `major`

Putting API responses in Redux/Zustand without invalidation, background refetch, dedup.

**Why:** Reimplementing React Query badly.

**Fix:** Use a server-state library (React Query, SWR, RTK Query, Apollo).

---

### 22. URL state duplicated in component state — `minor`

`searchParams.get('q')` also stored in `useState`; they drift.

**Fix:** One source of truth — URL. Read and set via `useSearchParams` / router.

---

### 23. Mutation of state or props — `severe`

```tsx
user.name = 'new';        // mutation
setUser(user);            // same reference — no re-render
items.push(x);            // mutation
```

**Detect:**
```
rg -n "(props\.\w+\.\w+\s*=|state\.\w+\s*=|\.push\(|\.splice\(|\.sort\(\))" --type tsx
```

**Why:** React relies on referential equality for change detection. Mutation skips renders and creates hidden shared-reference bugs.

**Fix:** Immutable updates. Use Immer if the shape is complex.

---

### 24. Reducing with inline initial state — `minor`

```tsx
const [s, d] = useReducer(reducer, { /* big literal */ });
```

**Fix:** Extract the initial state constant outside the component; it'll be recreated every render otherwise (mostly perf, not correctness).

---

## Performance

### 25. Inline objects/arrays/functions to memoized children — `major`

```tsx
<Memo onChange={(v) => setX(v)} config={{ mode: 'a' }} items={[1,2,3]}/>
```

**Detect:** any `React.memo`-wrapped child receiving inline `{}`, `[]`, or `()=>` as props.

**Fix:** `useCallback`, `useMemo`, or hoist.

---

### 26. Over-memoization — `minor`

`useMemo(() => x + 1, [x])`, `useCallback(() => setX(1), [])` on cheap primitives.

**Why:** Net negative — memoization has overhead.

**Fix:** Only memoize when the cost of recomputing or rendering exceeds the bookkeeping.

---

### 27. Expensive computation in render — `major`

Sorting/filtering large arrays, parsing dates, regexes compiled every render.

**Detect:** `.sort`, `.filter`, `.reduce` on non-trivial arrays outside of `useMemo`.

**Fix:** `useMemo` with correct deps; consider moving to a query selector.

---

### 28. `ScrollView` with large list (RN) — `severe`

```tsx
<ScrollView>{items.map(...)}</ScrollView>
```

**Detect:**
```
rg -n "ScrollView[\s\S]{0,200}\.map" --type tsx
```

**Why:** Every item rendered; no recycling; phones choke at ~100+ items.

**Fix:** `FlatList` / `SectionList` / `FlashList`. Set `keyExtractor`, `getItemLayout` if fixed height, tune `windowSize` and `maxToRenderPerBatch`.

---

### 29. Non-stable `FlatList renderItem` — `major`

`renderItem={(item) => <Foo .../>}` with inline JSX re-created on every render.

**Fix:** Extract to a memoized component; pass stable callbacks.

---

### 30. Unnecessary re-renders from context — `major`

A component subscribes to a large context but uses one field.

**Fix:** Split context; selector pattern; `use-context-selector`.

---

### 31. Synchronous expensive work blocking interaction — `major`

Parsing a large JSON on a button click without yielding; freezes UI.

**Fix:** Chunk with `requestIdleCallback` / `InteractionManager.runAfterInteractions` (RN); move to a worker; `startTransition` for non-urgent updates.

---

### 32. Barrel files forcing full-module imports — `minor`

`export * from './everything'` prevents tree shaking when consumers use one symbol.

**Fix:** Explicit re-exports, or direct imports at the use site.

---

## React Native specific

### 33. Inline styles in hot components — `minor`

`style={{ flex: 1, padding: 8 }}` recreated every render.

**Fix:** `StyleSheet.create` (which memoizes and can be optimized).

---

### 34. `Image` without `resizeMode` or fixed dimensions — `minor`

Layout jank; no constraints.

**Fix:** Set `resizeMode` and either width/height or `aspectRatio`.

---

### 35. Missing `SafeAreaView` / insets — `major`

Content under notch/home indicator on modern devices.

**Detect:**
```
rg -n "import.*react-native" --type tsx | rg -L "SafeArea|useSafeAreaInsets"
```

**Fix:** `react-native-safe-area-context`'s `SafeAreaView` or `useSafeAreaInsets`.

---

### 36. Animation on JS thread where native driver would work — `major`

`useNativeDriver: false` for transforms/opacity.

**Detect:**
```
rg -n "useNativeDriver:\s*false" --type tsx
```

**Fix:** `useNativeDriver: true` for transform/opacity. Use Reanimated for complex cases.

---

### 37. Touchable without feedback — `minor`

`TouchableWithoutFeedback` where `TouchableOpacity`/`Pressable` is appropriate.

**Fix:** `Pressable` with appropriate press state styling.

---

### 38. Storing sensitive data in `AsyncStorage` — `severe`

Auth tokens, PII, payment info in plain storage.

**Detect:**
```
rg -n "AsyncStorage\.(set|get)Item\([^)]*(token|auth|password|credit|card|ssn|secret)" -i --type tsx
```

**Fix:** `react-native-keychain`, `expo-secure-store`, `@react-native-async-storage/async-storage` with encryption wrapper.

---

## Styling & UI

### 39. `dangerouslySetInnerHTML` with user content — `severe`

**Detect:**
```
rg -n "dangerouslySetInnerHTML" --type tsx
```
Then check each usage — is the HTML from a trusted source, sanitized via DOMPurify?

**Fix:** Render via components; or sanitize with DOMPurify + strict config; or use MDX / a renderer lib.

---

### 40. `<div onClick>` for buttons — `major`

Not keyboard-accessible; no role; screen readers don't announce.

**Detect:**
```
rg -n "<div[^>]*onClick" --type tsx
```

**Fix:** `<button type="button">`; or `<a>` if it's navigation; or role + keyboard handlers if truly custom.

---

### 41. `autoFocus` on mount-often components — `minor`

Steals focus unpredictably, disorients keyboard/SR users.

**Fix:** Manage focus with intent (`useRef` + `.focus()` in response to a user action).

---

### 42. CSS inline styles with computed values (web) — `minor`

Breaks CSP, defeats CSS optimization.

**Fix:** CSS variables, utility classes, or CSS-in-JS with static extraction.

---

## General

### 43. Hardcoded secrets — `severe`

API keys, tokens, DB URLs in source.

**Detect:**
```
rg -n "(sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z\-_]{35}|AKIA[0-9A-Z]{16}|xox[bap]-[0-9a-zA-Z-]{10,}|ghp_[0-9a-zA-Z]{36})"
rg -ni "(apikey|api_key|token|secret|password)\s*[:=]\s*['\"][^'\"]{10,}" --type ts --type tsx
```

**Fix:** `.env` + platform secret management; rotate if anything was committed.

---

### 44. `any` as type — `major`

```
rg -n ":\s*any(\s|,|=|\)|\||>)" --type ts --type tsx
rg -n "<any>" --type ts --type tsx
```

**Fix:** Use `unknown` + narrowing, or define the real type.

---

### 45. Empty catch — `severe` (if on user-facing operation)

```tsx
try { await risky() } catch {}
try { await risky() } catch(e) {}
```

**Detect:**
```
rg -n "catch\s*(\(\s*[a-z]*\s*\))?\s*\{\s*\}" --type ts --type tsx
rg -n "\.catch\(\s*(\(\s*\)|\([^)]*\))\s*=>\s*\{\s*\}\s*\)"
```

**Fix:** At minimum, log + surface. Better: retry/fallback/UI feedback.

---

### 46. `console.log` in production code — `minor`

**Detect:**
```
rg -n "console\.(log|debug|info)" --type ts --type tsx
```
Cross-reference whether these are stripped by the build.

**Fix:** Remove, or route through a logger that's stripped in prod.

---

## Using this catalog

1. **Scan phase:** run the `rg` commands across the in-scope files. Collect every hit.
2. **Classify:** confirm each hit is an actual anti-pattern (false positives are possible — e.g. `dangerouslySetInnerHTML` on a sanitized markdown renderer is often fine).
3. **Tally:**
   - Severe items → surface in Critical Issues; counts 1.5 in APT math.
   - Major items → surface in Warnings; counts 1.0.
   - Minor items → list at bottom of per-category detail; counts 0.5.
4. **APT score:** 10 − (1.5×severe + 1.0×major + 0.5×minor), clamped to [1, 10].
5. **Apply red-flag ceilings** from SKILL.md (e.g. any `severe` in SEC pins SEC ≤4).

## False positives to watch

- `dangerouslySetInnerHTML` in markdown/MDX renderers with sanitization config — OK if verified.
- `AsyncStorage` of non-sensitive data (UI prefs, cache keys) — OK.
- `any` in declaration files for untyped third-party libs — OK if narrowed at use sites.
- `console.log` in dev-only code paths or tests — OK.
- Inline styles on components that never re-render (static shells) — OK.

When in doubt, cite file:line and mark it `ambiguous` in the report; let the author decide.

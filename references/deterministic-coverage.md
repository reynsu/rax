# Deterministic Coverage — sub-caract. ISO 25010 ↔ tools

> **Propósito.** Por cada sub-característica ISO de `references/rubric-v2.md`,
> declarar qué tools deterministas la cubren y qué fracción del scoring puede
> provenir de ellos antes de invocar al LLM.
>
> **Cómo se usa.** La Fase 2 (`deterministic_layer.sh`) corre cada tool y
> publica findings agrupados por `ISO_<CHAR>_<SUB>`. La Fase 4 mezcla
> `final = α · deterministic + (1−α) · llm` por sub-característica. Las filas
> de esta tabla son la fuente de verdad de α.
>
> **Convención de α.** Conservador: si dudas, α menor. La idea es no
> hacer el LLM redundante, pero tampoco confiar ciegamente en linters
> que no saben de intent. Rangos típicos:
>
> - `α ≥ 0.7` — herramientas tienen autoridad cercana a la verdad
>   (rules-of-hooks, secret detection, CVEs, CSP). El LLM solo confirma o
>   marca falsos positivos.
> - `0.4 ≤ α < 0.7` — herramientas miden el qué pero no el por qué
>   (complejidad, duplicación, coverage). El LLM agrega contexto.
> - `0.1 ≤ α < 0.4` — herramientas dan señales sueltas (presencia de un
>   patrón). El LLM lleva el peso.
> - `α = 0.0` — sin tools deterministas; el LLM o la auditoría humana
>   resuelven (o queda `n/a`).
>
> **Tools cubiertos.**
>
> | Tool | Cobertura general |
> |---|---|
> | Semgrep | Patrón AST + tax. JS/TS/React; reglas open-source (`p/javascript`, `p/react`, `p/owasp-top-ten`, `p/typescript`); reglas custom en `references/rules/` (Fase 2.3). |
> | ast-grep | Patrón AST con sintaxis JSX/TSX nativa; bueno para detección de antipatrones React idiomáticos. |
> | ESLint | Reglas semánticas + plugins (`react`, `react-hooks`, `react-native`, `jsx-a11y`, `import`, `react-perf`, `boundaries`). |
> | TypeScript (`tsc --strict`) | Type errors, strict null checks, `noUncheckedIndexedAccess`. |
> | madge | Detecta circular deps + visualiza grafo. |
> | dependency-cruiser | Reglas de boundary (lo que `eslint-plugin-boundaries` no cubre). |
> | jscpd | Detecta clones de código. |
> | npm audit / Snyk | CVEs en el árbol de dependencias. |
> | gitleaks / trufflehog | Secret scanning en historial git + working tree. |
> | axe-core (CLI / `@axe-core/playwright`) | Accesibilidad runtime + estática parcial. |
> | Lighthouse CI | Performance + a11y + best practices runtime. |
> | source-map-explorer / `webpack-bundle-analyzer` | Tamaño de bundle. |
> | depcheck | Deps no usadas. |

---

## Tabla de cobertura por sub-característica

| ISO sub-characteristic | Tools applicable | Coverage α | Notes |
|---|---|---|---|
| ISO_FUN_COMP | — | 0.0 | No spec accesible; rax no audita completeness funcional. |
| ISO_FUN_CORR | jest/vitest coverage, mutation testing (stryker) | 0.3 | E2E/unit como evidencia parcial; correctness real requiere humano. |
| ISO_FUN_APPR | — | 0.0 | UX/intent — no detectable estática. |
| ISO_FUN_IDEN | grep README, marketing copy presence | 0.1 | Solo señal binaria de "existe documentación". |
| ISO_PERF_TIME | ESLint react-perf, react-hooks/exhaustive-deps, Lighthouse | 0.7 | Re-render hygiene + heavy work in render detectables; runtime profiling es el gold. |
| ISO_PERF_RES | webpack-bundle-analyzer, source-map-explorer, depcheck, image-size lint | 0.8 | Bundle composition + asset sizes son medibles directamente. |
| ISO_PERF_CAP | grep FlatList vs ScrollView (RN), pagination patterns | 0.5 | Virtualization detectable; límites reales no. |
| ISO_COMP_COEX | npm peer deps warnings, Platform.select coverage | 0.5 | Estructural; runtime cross-platform requiere CI matrix. |
| ISO_COMP_INTER | OpenAPI/GraphQL codegen presence, Zod/Yup at boundaries | 0.6 | Detectable presencia de schema-driven types + runtime validation. |
| ISO_INTER_REC | grep empty-state components, hero copy | 0.2 | Detección débil; UX recognizability requiere usuarios. |
| ISO_INTER_LEARN | grep onboarding/tooltip components, copy variability | 0.15 | Solo presencia, no efectividad. |
| ISO_INTER_OP | eslint-plugin-jsx-a11y, axe-core, react-native-a11y, focus-visible lints | 0.75 | Operability estática es muy bien cubierta por jsx-a11y + axe. |
| ISO_INTER_UEP | Zod/Yup detection, react-hook-form presence, confirm-dialog patterns | 0.7 | Validación runtime + patrones de protección detectables. |
| ISO_INTER_ENG | grep animation libraries, haptic API usage | 0.2 | Presencia de motion design; no calidad. |
| ISO_INTER_INC | jsx-a11y, axe-core, contrast-ratio CLI, i18n-coverage | 0.75 | Inclusivity (a11y + i18n) es uno de los frentes mejor cubiertos por static analysis. |
| ISO_INTER_UAA | grep error UX patterns (retry buttons, help links) | 0.4 | Patrones detectables; calidad textual no. |
| ISO_INTER_SD | grep loading/empty/error/success state coverage | 0.4 | Heuristics sobre presencia de los 4 estados por boundary async. |
| ISO_REL_FAULT | tsc --strict, eslint-plugin-react-hooks/rules-of-hooks, no-floating-promises, jest unit | 0.75 | Type errors + Rules of Hooks + promise hygiene son mecánicos. |
| ISO_REL_AVAIL | — | 0.0 | Concern de infra/runtime; no estática. |
| ISO_REL_FT | grep ErrorBoundary, retry/backoff libs, AbortController | 0.7 | Patrones tolerantes a fallo detectables vía AST. |
| ISO_REL_REC | grep Sentry/Bugsnag, source-maps upload, persistence layers | 0.5 | Presencia de error tracking + state persistence; quality del playbook no. |
| ISO_SEC_CONF | gitleaks, trufflehog, semgrep secrets, eslint no-process-env-leak, react-native-keychain detection | 0.85 | Secret detection es de las áreas más maduras de static analysis. |
| ISO_SEC_INT | semgrep r/javascript.lang.security, react/no-danger, Zod/Yup detection, CSP grep | 0.75 | XSS/injection vectors muy bien cubiertos. |
| ISO_SEC_NR | grep audit-log calls | 0.1 | Cliente solo aporta señal débil; concern de backend. |
| ISO_SEC_ACC | grep Sentry user context, analytics user-id propagation | 0.4 | Presencia detectable; calidad del context no. |
| ISO_SEC_AUTH | grep oauth/SSO patterns, refresh-token logic, route-guard patterns | 0.65 | Patrones estructurales detectables; correctness flow requiere review. |
| ISO_SEC_RES | npm audit, Snyk, semgrep deeplink/WebView hardening rules | 0.55 | Supply chain cubre buena parte; rate-limit cliente es heurística. |
| ISO_MAINT_MOD | madge, dependency-cruiser, eslint-plugin-boundaries, file-size lints | 0.75 | Estructura de módulos es objetivamente medible. |
| ISO_MAINT_REUSE | jscpd, eslint-plugin-react-perf, props-API surface analyzers | 0.6 | Duplication + props API metric. La "rule of three" es heurística. |
| ISO_MAINT_ANAL | ESLint complexity rules (cognitive/cyclomatic), file-size lints, type-coverage, comment ratio | 0.8 | Métricas estáticas tradicionales — cobertura alta. |
| ISO_MAINT_MOD2 | grep state-management coupling, prop-drilling detection, react-hooks/exhaustive-deps | 0.7 | Modificabilidad correlaciona con métricas estáticas estables. |
| ISO_MAINT_TEST | jest --coverage, vitest --coverage, presence of testing-library/RNTL/Detox/Playwright/Maestro | 0.75 | Coverage + framework usage detectables; quality de tests vía mutation testing parcial. |
| ISO_FLEX_ADAPT | grep responsive breakpoints, Platform.select coverage, theme tokens, RTL detection | 0.55 | Heurística de cobertura responsive + RTL + tema. |
| ISO_FLEX_SCAL | grep code-splitting, virtualization, pagination, bundle-size budget | 0.5 | Patrones detectables; carga real necesita load testing. |
| ISO_FLEX_INST | grep build/install scripts, package size | 0.15 | Concern principalmente de CI/CD pipeline. |
| ISO_FLEX_REPL | grep vendor lock-in patterns (importing client SDKs from components) | 0.45 | Heurística de capa de abstracción. |
| ISO_SAFE_OP | — | 0.15 | En consumer no auditada; en safety-critical, profile sube α. |
| ISO_SAFE_RISK | — | 0.1 | Idem — domain-specific. |
| ISO_SAFE_FS | grep ErrorBoundary fallbacks, optimistic-update rollback patterns | 0.6 | Fail-safe patterns detectables a nivel React. |
| ISO_SAFE_HW | — | 0.1 | Domain-specific; no estática general. |
| ISO_SAFE_SI | npm audit, semgrep WebView/deeplink rules | 0.55 | Supply chain cubre la mayor parte. |

---

## Mapeo inverso — qué cubre cada tool

> Para cuando se debugea por qué un finding aparece bajo cierta sub-característica, o cuándo se prioriza adoptar un nuevo tool.

| Tool | Sub-características que toca | α típico aportado |
|---|---|---|
| Semgrep (rulesets oss) | ISO_SEC_*, ISO_REL_FAULT, ISO_PERF_*, ISO_MAINT_MOD, ISO_MAINT_MOD2 | 0.4–0.7 |
| Semgrep (custom rules — Fase 2.3) | ISO_INTER_OP, ISO_INTER_UEP, ISO_INTER_INC, ISO_REL_FT | 0.4–0.6 |
| ast-grep | ISO_MAINT_MOD2, ISO_PERF_TIME, ISO_REL_FAULT (alternativas a semgrep para JSX) | 0.3–0.5 |
| ESLint react / react-hooks | ISO_REL_FAULT, ISO_PERF_TIME, ISO_MAINT_MOD2 | 0.5–0.75 |
| ESLint react-native | ISO_PERF_RES, ISO_PERF_CAP, ISO_INTER_OP (RN-specific) | 0.4–0.6 |
| ESLint jsx-a11y | ISO_INTER_OP, ISO_INTER_INC, ISO_INTER_UEP | 0.6–0.75 |
| ESLint import / boundaries | ISO_MAINT_MOD, ISO_MAINT_MOD2 | 0.5–0.7 |
| ESLint react-perf | ISO_PERF_TIME, ISO_PERF_RES | 0.5–0.7 |
| TypeScript (strict) | ISO_REL_FAULT, ISO_MAINT_ANAL, ISO_SEC_INT (vía Zod-derived types) | 0.6–0.75 |
| madge | ISO_MAINT_MOD | 0.5–0.75 |
| dependency-cruiser | ISO_MAINT_MOD, ISO_MAINT_MOD2 | 0.5–0.7 |
| jscpd | ISO_MAINT_REUSE, ISO_MAINT_ANAL | 0.4–0.6 |
| jest/vitest --coverage | ISO_MAINT_TEST, ISO_FUN_CORR | 0.5–0.7 |
| Stryker (mutation) | ISO_MAINT_TEST, ISO_FUN_CORR | 0.6–0.75 |
| npm audit / Snyk | ISO_SEC_RES, ISO_SAFE_SI, ISO_FLEX_REPL (parcial) | 0.5–0.65 |
| gitleaks / trufflehog | ISO_SEC_CONF | 0.7–0.85 |
| axe-core | ISO_INTER_INC, ISO_INTER_OP, ISO_INTER_UEP | 0.6–0.75 |
| Lighthouse CI | ISO_PERF_TIME, ISO_PERF_RES, ISO_INTER_INC | 0.5–0.7 |
| webpack-bundle-analyzer / source-map-explorer | ISO_PERF_RES, ISO_FLEX_SCAL | 0.6–0.8 |
| depcheck | ISO_PERF_RES, ISO_MAINT_REUSE | 0.4–0.6 |

---

## Criterios para subir/bajar α

> Cuándo cambiar el α de una fila — guardrails para que el documento no derive con cada PR.

- **Subir α** cuando:
  - Una nueva regla custom (Fase 2.3) cierra un gap consistente que el LLM venía cubriendo.
  - Un tool introduce un check que históricamente correlaciona con findings reales (verificable con benchmark de Fase 3.3).
  - Múltiples tools concuerdan sobre la misma sub-característica.
- **Bajar α** cuando:
  - Tasa de falsos positivos del tool es alta (>15%) en proyectos reales.
  - El tool requiere config compleja que el usuario probablemente no tiene.
  - Self-consistency benchmark muestra que el LLM detecta cosas que el tool no.

α se versiona aquí. Cambios significativos (>0.1) requieren una nota de "Por qué" en este documento más una prueba de regresión sobre el benchmark.

---

## Apéndice — Conteo

41 sub-características ISO → cada una tiene una fila en la tabla principal. 21 tools mapeados a sus rangos de α típicos.

Σ(α) sobre todas las sub-características = aproximadamente **20.4**, lo que da un α promedio de ~**0.50**. Esto significa que la capa determinista cubre ~50% del scoring antes de invocar al LLM, alineado con el objetivo de Fase 2 ("~50% del scoring se vuelve determinista").

# Rubric v2 — Anclado a ISO/IEC 25010:2023

> **Diferencias vs v1.** Las categorías ya no son nombres inventados (`ARC`, `RXP`, `APT`, …); son las 9 características de ISO/IEC 25010:2023. Los subcriterios son las sub-características oficiales del estándar. Los anchors a 3/6/8/10 siguen siendo míos pero ahora cuelgan de un nombre y definición externos.
>
> **Fuente del mapeo.** `references/iso25010-mapping.md` (paso 1.1). Cualquier divergencia entre este rubric y el mapeo es un bug; el mapeo manda.
>
> **v1 sigue vivo.** `references/rubric.md` no se toca. Existe en paralelo durante la migración para permitir A/B y rollback. La intención es deprecarlo cuando la Fase 6 cierre.

---

## Cómo leer cada sub-característica

Cada sub-característica tiene cuatro bloques fijos:

1. **ID estable** — `ISO_<CHAR>_<SUB>`, citable desde código y prompts.
2. **Definición ISO** — síntesis textual de la 25010:2023 (las definiciones del estándar son citas indirectas; el texto oficial es de pago).
3. **Cobertura determinista** — `alto` / `medio` / `bajo`. Indica qué porcentaje de la señal puede capturarse con tools estáticos antes de invocar al LLM. Usado por la Fase 2 (orquestador) para decidir el peso α de la mezcla determinista/LLM.
4. **Anchors 3 / 6 / 8 / 10** — ejemplos concretos React/RN. Reglas de scoring como en v1: el peor de los aplicables manda; intermedios se interpolan; `n/a` si la sub-característica no aplica al proyecto.

**IDs `n/a` por defecto.** Sub-características fuera del alcance de análisis estático (ver mapeo §11.5, §11.6) llevan etiqueta `[no auditada por defecto]` y peso 0. Activables vía `--profile` o `config.json`.

---

# 1. Functional Suitability

> ISO: "Degree to which a product or system provides functions that meet stated and implied needs when used under specified conditions."
>
> **Política rax v2.** Excepto `ISO_FUN_CORR` (parcial vía E2E), las sub-características aquí no se auditan estáticamente. Se incluyen para alinear con el estándar y para que el reporte sea explícito sobre lo que NO mide.

## 1.1 ISO_FUN_COMP — Functional Completeness `[no auditada por defecto]`

- **Definición ISO.** "Set of functions covers all specified tasks and user objectives."
- **Cobertura determinista.** **Bajo** (~0%). Requiere conocer la spec; rax no la tiene.
- **Anchors (aspiracionales — solo si hay spec accesible):**
  - **3** — No hay documentación de qué debería hacer la app; features se infieren del código.
  - **6** — README lista features pero sin trazabilidad a código; gaps obvios.
  - **8** — Cada feature listada en README/PRD tiene un test E2E ejecutable.
  - **10** — Trazabilidad bidireccional spec ↔ código ↔ test, monitoreada en CI.

## 1.2 ISO_FUN_CORR — Functional Correctness

- **Definición ISO.** "Functions provide correct results with the needed degree of precision."
- **Cobertura determinista.** **Medio** (~30%). Detectable parcialmente vía cobertura E2E + tipos estrictos + runtime validation. El "correcto" ground-truth requiere humanos.
- **Anchors:**
  - **3** — No hay tests E2E; bugs reportados se reabren porque no hay regresión.
  - **6** — Smoke E2E sobre happy path; bugs históricos sin regresión específica.
  - **8** — E2E cubre flujos críticos (auth, checkout, mutaciones); cada bug fix lleva test.
  - **10** — Property-based / fuzz tests sobre parsers críticos; mutation testing en lógica core.

## 1.3 ISO_FUN_APPR — Functional Appropriateness `[no auditada por defecto]`

- **Definición ISO.** "Functions facilitate the accomplishment of specified tasks and objectives."
- **Cobertura determinista.** **Bajo** (~0%). Es un juicio de UX, no de código.
- **Anchors (aspiracionales):**
  - **3** — Tareas comunes requieren múltiples pasos no documentados.
  - **6** — Flujos principales razonables; flujos secundarios fricción.
  - **8** — Cada tarea tiene un camino directo; atajos en flujos frecuentes.
  - **10** — Probado con usuarios; redesigns basados en datos.

## 1.4 ISO_FUN_IDEN — Functional Identification `[no auditada por defecto]`

- **Definición ISO.** "Capability to identify the functional capabilities of the product."
- **Cobertura determinista.** **Bajo** (~10%). Detectable parcialmente vía README/onboarding/empty states.
- **Anchors (aspiracionales):**
  - **3** — README ausente o desactualizado; primera pantalla sin onboarding.
  - **6** — README describe features básicas; sin onboarding in-app.
  - **8** — Onboarding in-app o tour; empty states educativos.
  - **10** — Onboarding personalizado por rol/contexto; help center contextual.

---

# 2. Performance Efficiency

> ISO: "Performance relative to the amount of resources used under stated conditions."

## 2.1 ISO_PERF_TIME — Time Behaviour

- **Definición ISO.** "Response and processing times and throughput rates of a product or system meet requirements."
- **Cobertura determinista.** **Alto** (~70%). React Profiler, Lighthouse, ESLint react-perf, react-hooks/exhaustive-deps, eslint-plugin-react-hooks, Hermes profiler para RN.
- **Anchors:**
  - **3** — Trabajo pesado en render o por keystroke; objetos/arrays/funciones inline pasados a children memoizados; effects sin debounce; overlay del Profiler muestra árboles enteros re-renderizando.
  - **6** — Algunas optimizaciones manuales; debounce inconsistente; deps arrays con falsos positivos.
  - **8** — Memoización deliberada y justificada con measurement; `React.memo` con equality correcto; deps arrays clean en `react-hooks/exhaustive-deps`; trabajo pesado off-main-thread o en `useMemo`/`useDeferredValue`.
  - **10** — Budgets de tiempo por componente crítico, monitoreados en CI; el Profiler sobre la pantalla más pesada no muestra renders desperdiciados.

## 2.2 ISO_PERF_RES — Resource Utilization

- **Definición ISO.** "Amounts and types of resources used by a product or system, when performing its functions, meet requirements."
- **Cobertura determinista.** **Alto** (~80%). webpack/vite/metro-bundle analyzer, source-map-explorer, depcheck, eslint-plugin-import/no-unused-modules, RN startup profiling.
- **Anchors:**
  - **3** — Bundle único sin code splitting; `moment`, `lodash` full, `axios` cargados; imágenes full-res sirviendo thumbnails; subscriptions/timers sin cleanup.
  - **6** — Code splitting por ruta; algunas alternativas más livianas adoptadas; cleanup mayoritario.
  - **8** — Code splitting ruta + componente donde mide; `date-fns`/`dayjs`, `lodash-es`, fetch nativo o `ky`; imágenes responsive (`expo-image`/`FastImage`/srcset); cleanup en cada subscription/timer/listener.
  - **10** — Bundle budgets enforced en CI con regression gates; image strategy documentada con métricas LCP/FCP; AbortController en async work.

## 2.3 ISO_PERF_CAP — Capacity

- **Definición ISO.** "Maximum limits of a product or system parameter meet requirements."
- **Cobertura determinista.** **Medio** (~50%). Detectable: virtualization de listas, paginación, query limits. No detectable: límites de carga real.
- **Anchors:**
  - **3** — Listas unbounded en `ScrollView` (RN) o `Array.map` sin virtualización; queries sin LIMIT; sin paginación visible.
  - **6** — `FlatList`/virtualización presente; paginación en pantallas obvias; misconfigurations menores.
  - **8** — Virtualización con `keyExtractor`, `getItemLayout` cuando aplica; paginación + infinite scroll donde corresponde; queries con limits.
  - **10** — Límites probados con datasets large; load tests (web) o stress tests (RN); decisiones documentadas (página máx, items máx).

---

# 3. Compatibility

> ISO: "Degree to which a product can exchange information with other products and/or perform its required functions while sharing the same hardware or software environment."

## 3.1 ISO_COMP_COEX — Co-existence

- **Definición ISO.** "Performs its required functions efficiently while sharing a common environment and resources with other products, without detrimental impact."
- **Cobertura determinista.** **Medio** (~50%). package.json peer deps, npm warnings on install, RN Platform.OS branching, browser matrix declarado.
- **Anchors:**
  - **3** — Peer dep warnings ignorados; conflicting RN versions; sin `Platform.select` donde aplica.
  - **6** — Peer deps satisfechos; algunas ramas Platform; matriz de browsers no declarada.
  - **8** — package.json `engines` declarado; matriz Platform/browser explícita; `Platform.select` consistente; sin warnings.
  - **10** — Tests cross-platform en CI (iOS+Android+web si aplica); compatibility matrix documentada; downgrade tests para deprecaciones.

## 3.2 ISO_COMP_INTER — Interoperability

- **Definición ISO.** "Two or more systems, products or components can exchange information and use the information that has been exchanged."
- **Cobertura determinista.** **Medio** (~60%). OpenAPI/GraphQL schemas, Zod/Yup validation en boundaries, type generation desde contratos.
- **Anchors:**
  - **3** — APIs consumidas con tipos manuales que divergen del backend; sin validación runtime; deep links sin contrato.
  - **6** — Tipos de API generados ocasionalmente; validación parcial; deep links documentados pero no validados runtime.
  - **8** — Tipos generados desde OpenAPI/GraphQL en CI; runtime validation (Zod) en cada boundary; deep links tipados y validados.
  - **10** — Contract tests entre cliente/servidor; backwards-compat policies documentadas; versioning de APIs visible.

---

# 4. Interaction Capability

> ISO (2023, reemplaza Usability): "Degree to which a product can be interacted with by specified users to exchange information via the user interface to complete the intended task."

## 4.1 ISO_INTER_REC — Appropriateness Recognizability

- **Definición ISO.** "Users can recognize whether a product or system is appropriate for their needs."
- **Cobertura determinista.** **Bajo** (~20%). Detectable: empty states informativos, copy en hero/landing, microcopy.
- **Anchors:**
  - **3** — Empty states blancos; sin onboarding; sin valor explícito en UI inicial.
  - **6** — Empty states con texto genérico; landing menciona feature pero no value-prop.
  - **8** — Empty states educan (qué hace la pantalla, cómo empezar); preview de capabilities visible.
  - **10** — First-run experience personalizada; "samples" o demo data para que el usuario vea el valor antes de invertir.

## 4.2 ISO_INTER_LEARN — Learnability

- **Definición ISO.** "Users can learn how to use the product or system."
- **Cobertura determinista.** **Bajo** (~15%). Detectable: presencia de onboarding, tooltips, help text, consistency.
- **Anchors:**
  - **3** — Sin onboarding ni tooltips; UI inconsistente (mismo concepto se llama distinto en pantallas distintas).
  - **6** — Onboarding básico saltable; tooltips en algunas features; consistencia razonable.
  - **8** — Onboarding contextual (no upfront wall); tooltips en features no obvias; vocabulario consistente across screens.
  - **10** — Progressive disclosure documentada; tutoriales interactivos; A/B sobre learnability con métricas.

## 4.3 ISO_INTER_OP — Operability

- **Definición ISO.** "Easy to operate and control."
- **Cobertura determinista.** **Alto** (~75%). axe-core, eslint-plugin-jsx-a11y, focus-visible checks, touch target size lints, eslint-plugin-react-native-a11y.
- **Anchors:**
  - **3** — Tab traps; focus perdido al cerrar modal; outlines de focus removidos globalmente; touch targets <32pt; sin `Platform.select` para gestos críticos.
  - **6** — Modales restauran focus; focus styles existen; touch targets ~40pt; gestos handled vía libs modernas.
  - **8** — Focus management correcto (trap + restore); skip links (web); touch targets ≥44pt; visible focus con contraste suficiente; gestos consistentes.
  - **10** — Operabilidad teclado verificada end-to-end; focus order = reading order; keyboard shortcuts documentados; haptics deliberados.

## 4.4 ISO_INTER_UEP — User Error Protection

- **Definición ISO.** "Protects users against making errors."
- **Cobertura determinista.** **Alto** (~70%). Form validation (Zod/Yup/React Hook Form), confirmation patterns, undo/redo presence, optimistic update detection.
- **Anchors:**
  - **3** — Acciones destructivas sin confirmación; formularios sin validation feedback; errores swallow con `.catch(() => {})`; raw error strings al usuario.
  - **6** — Confirmación en algunas acciones destructivas; validación parcial; mensajes de error genéricos.
  - **8** — Confirm + undo en destructivas; runtime validation con Zod/Yup en cada form; mensajes de error accionables; idempotencia visible en mutations.
  - **10** — Patrón "soft delete + undo" sistemático; preview before commit; validación schema-first; copy de errores reviewed por content.

## 4.5 ISO_INTER_ENG — User Engagement

- **Definición ISO.** "Pleasing and satisfying interaction for the user."
- **Cobertura determinista.** **Bajo** (~20%). Detectable: presencia de animaciones, microinteractions, haptics. No detectable: si son agradables.
- **Anchors:**
  - **3** — UI estática sin transiciones; sin haptics; transiciones bloquean interacción.
  - **6** — Algunas transiciones; haptics ocasionales; respeta `prefers-reduced-motion` parcialmente.
  - **8** — Animaciones intencionales (no decorativas); haptics consistentes; `prefers-reduced-motion` respetado throughout.
  - **10** — Motion design system documentado; budgets de animation duration; A/B sobre engagement.

## 4.6 ISO_INTER_INC — Inclusivity

- **Definición ISO.** "Used by people with widest range of characteristics and capabilities."
- **Cobertura determinista.** **Alto** (~75%). axe-core, jsx-a11y, contrast checkers (WCAG AA/AAA), i18n coverage analyzer, RTL detection.
- **Anchors:**
  - **3** — `<div onClick>` para botones; imágenes sin `alt`; forms sin labels; contraste por debajo de WCAG AA; strings hardcoded; layouts ltr-only.
  - **6** — Mayoría de elementos semánticos; gaps en menos-traficados; contraste AA en main flows; i18n con coverage incompleto.
  - **8** — Semántica throughout; `accessibilityLabel`/`role` en cada interactive; AA en todo texto e interactivos; strings centralizados; RTL probado.
  - **10** — Verificado con screen readers (VO/TalkBack/NVDA); AAA en flows críticos; pseudo-localización en CI; design tokens enforce contrast.

## 4.7 ISO_INTER_UAA — User Assistance

- **Definición ISO.** "Provides assistance when users need help."
- **Cobertura determinista.** **Medio** (~40%). Detectable: presencia de tooltips, help links, error messages with next steps, support handoff.
- **Anchors:**
  - **3** — Errores sin recovery action; sin help; soporte invisible.
  - **6** — Errores principales con retry; help link en footer.
  - **8** — Cada error ofrece next step (retry / contact / fallback); help contextual (tooltips, docs link); support handoff con context.
  - **10** — Self-service docs integrados; chatbot/assistant contextual; metrics de "asistencia exitosa".

## 4.8 ISO_INTER_SD — Self-descriptiveness

- **Definición ISO.** "Provides appropriate information at the right time and place."
- **Cobertura determinista.** **Medio** (~40%). Detectable: empty/loading/error/success state coverage; status badges; progress indicators.
- **Anchors:**
  - **3** — UI no comunica estado (¿cargando? ¿vacío? ¿error?); silencio total en async.
  - **6** — Spinners en main flows; empty/error en pantallas obvias.
  - **8** — Cada async tiene los 4 estados (idle/loading/success/error); skeletons donde mejoran perceived performance; status communication consistente.
  - **10** — Taxonomy de states documentada; recovery paths probados; live regions para dynamic content.

---

# 5. Reliability

> ISO: "Degree to which a system performs specified functions under specified conditions for a specified period of time."

## 5.1 ISO_REL_FAULT — Faultlessness

- **Definición ISO (2023).** "Performs specified functions without fault under normal operation." *(Renombrado desde "Maturity" en la edición 2011.)*
- **Cobertura determinista.** **Alto** (~75%). TypeScript strict, ESLint react-hooks/rules-of-hooks, no-floating-promises, eslint-plugin-react/exhaustive-deps, jest unit tests.
- **Anchors:**
  - **3** — Rules of Hooks violadas; `any` everywhere; promises sin `.catch`; effects con deps incorrectas; runtime crashes frecuentes en producción.
  - **6** — strict TypeScript pero con `@ts-expect-error` o `as any` esparcidos; awaits handled mostly; algunos warnings de hooks suprimidos.
  - **8** — `strict + noUncheckedIndexedAccess`; cero `any` sin justificación; `react-hooks/*` enforced; await handlers consistentes; tests unit en core lógica.
  - **10** — Type-coverage monitored; `unknown` + narrowing es el patrón; mutation testing en core; cero crashes-attributable-to-types reportados en último trimestre.

## 5.2 ISO_REL_AVAIL — Availability `[no auditada por defecto]`

- **Definición ISO.** "Operational and accessible when required for use."
- **Cobertura determinista.** **Bajo** (~5%). Concern de infra; rax es estática.
- **Anchors (aspiracionales):**
  - **3** — Sin SLO; outages sin postmortem; sin status page.
  - **6** — Uptime tracked manualmente; alerts loose.
  - **8** — SLO declarado; status page; alerts on-call.
  - **10** — Error budgets enforced; chaos eng; multi-region failover.

## 5.3 ISO_REL_FT — Fault Tolerance

- **Definición ISO.** "Operates as intended despite the presence of hardware or software faults."
- **Cobertura determinista.** **Alto** (~70%). React Error Boundaries detection, retry logic patterns, circuit breakers, offline-first patterns (Service Worker, RN AsyncStorage queues).
- **Anchors:**
  - **3** — Sin error boundaries; un error de componente crashea la app; sin retries; offline → white screen.
  - **6** — Un error boundary top-level; retries ad-hoc; indicador de offline básico.
  - **8** — Error boundaries a varios niveles (app/ruta/sub-tree); retry con backoff donde aplica; offline-first con queued mutations donde corresponde.
  - **10** — Error boundaries integradas a monitoreo con recovery actions; circuit breakers en clientes API; sync strategy documentada (CRDT u otra).

## 5.4 ISO_REL_REC — Recoverability

- **Definición ISO.** "Recovers data and re-establishes the desired state of the system in case of failure."
- **Cobertura determinista.** **Medio** (~50%). Logging coverage, Sentry/equivalent integration, source maps upload, persistence layer detection.
- **Anchors:**
  - **3** — `console.log` debugging; sin error tracking centralizado; estado se pierde al refresh; sin source maps.
  - **6** — Sentry integrado; source maps a veces; estado persistido parcialmente.
  - **8** — Errores capturados con user/breadcrumbs; source maps confiables; estado crítico persistido (Redux Persist / IndexedDB / AsyncStorage); reconnect logic visible.
  - **10** — Error budgets/SLOs; playbooks; tests específicos sobre recovery (refresh mid-flow, kill app mid-mutation, reconnect after offline).

---

# 6. Security

> ISO: "Degree to which a product or system defends against attack patterns by malicious actors and protects information and data."

## 6.1 ISO_SEC_CONF — Confidentiality

- **Definición ISO.** "Data are accessible only to those authorized to have access."
- **Cobertura determinista.** **Alto** (~80%). gitleaks, trufflehog, ESLint no-process-env-leak, semgrep secrets rules, npm audit, react-native-keychain detection.
- **Anchors:**
  - **3** — API keys/tokens hardcoded en source; auth tokens en `localStorage`/`AsyncStorage` plain; secrets logged a console.
  - **6** — Secrets en `.env` con leaks ocasionales; tokens en `localStorage` con plan de migración; encryption wrapper sobre AsyncStorage.
  - **8** — Build-time vs runtime secrets separados; tokens en httpOnly cookies (web) o `react-native-keychain`/`expo-secure-store` (RN); secret scanning en CI.
  - **10** — Vault/platform secret manager; git history audited; data classification con threat model; auto-purge on logout.

**Red flag.** Hardcoded secret en source o auth token en plain storage → sub-característica ≤4.

## 6.2 ISO_SEC_INT — Integrity

- **Definición ISO.** "Prevents unauthorized access to, or modification of, computer programs or data."
- **Cobertura determinista.** **Alto** (~75%). Semgrep XSS rules, ESLint react/no-danger, runtime validation detection (Zod/Yup), CSP detection.
- **Anchors:**
  - **3** — `dangerouslySetInnerHTML` con user-derived content; user input concatenado en URLs; `eval`/`Function` sobre input; no validation.
  - **6** — `dangerouslySetInnerHTML` con sanitization implícita; validation parcial.
  - **8** — DOMPurify con strict config; URLs vía `URL` API; runtime validation (Zod) en cada boundary; tipos derivados de schemas.
  - **10** — CSP enforced; `dangerouslySetInnerHTML` ausente o documentado y reviewed; fuzz/property-based tests sobre parsers críticos.

## 6.3 ISO_SEC_NR — Non-repudiation `[no auditada por defecto]`

- **Definición ISO.** "Actions or events can be proven to have taken place, so that the events or actions cannot be repudiated later."
- **Cobertura determinista.** **Bajo** (~10%). Concern principalmente backend; cliente solo puede aportar audit logs locales.
- **Anchors (aspiracionales):**
  - **3** — Sin logging de acciones de usuario; sin trazabilidad de mutations.
  - **6** — Logging de eventos clave a Analytics.
  - **8** — Audit log con userId/timestamp/action en mutations sensibles; backend co-firma.
  - **10** — Signed receipts; tamper-evident logs.

## 6.4 ISO_SEC_ACC — Accountability

- **Definición ISO.** "Actions of an entity can be traced uniquely to the entity."
- **Cobertura determinista.** **Medio** (~40%). Sentry user context, analytics user identification, telemetry presence.
- **Anchors:**
  - **3** — Errores sin user context; analytics anónimos sin correlación.
  - **6** — Sentry con user.id; analytics correlacionados.
  - **8** — User/session/device IDs propagados a logs/errors/analytics; breadcrumbs ricos.
  - **10** — Distributed tracing cliente-servidor; SLO de "every error has user context".

## 6.5 ISO_SEC_AUTH — Authenticity

- **Definición ISO.** "Identity of a subject or resource can be proved to be the one claimed."
- **Cobertura determinista.** **Alto** (~70%). Token expiry checks, refresh logic detection, OAuth/SSO patterns, MFA presence indicators.
- **Anchors:**
  - **3** — Tokens sin expiry; sin refresh logic; auth derivado de fuentes múltiples; route guards solo en UI (bypassable).
  - **6** — Refresh con race conditions; logout incompleto; algún state contradictorio.
  - **8** — Single source de auth; refresh con request dedup; logout limpio; route protection en UI + API.
  - **10** — Auth flows tested; CSRF/session-fixation mitigados; MFA disponible; suspicious-activity signals propagados.

## 6.6 ISO_SEC_RES — Resistance

- **Definición ISO.** "Sustains operations while under attack."
- **Cobertura determinista.** **Medio** (~50%). npm audit, supply-chain checks, deep link validation, WebView hardening detection, rate-limit detection on client side.
- **Anchors:**
  - **3** — Critical/high CVEs reachable; deep links sin validación; WebView con `originWhitelist: ['*']`; sin rate limiting cliente.
  - **6** — Lockfile + audit ocasional; deep links validados parcialmente; WebView restringido parcialmente.
  - **8** — Dependabot/Renovate; audit en CI con thresholds; deep links typed+validated; WebView restringido (`originWhitelist`, JS bridge auditado); cliente respeta rate limits.
  - **10** — SBOM + provenance; mobile threat model; jailbreak/root detection donde warrant; tamper detection on release builds.

**Red flag.** HTTP endpoint en producción → ≤4.

---

# 7. Maintainability

> ISO: "Degree of effectiveness and efficiency with which a product can be modified to improve, correct, or adapt it to changes."

## 7.1 ISO_MAINT_MOD — Modularity

- **Definición ISO.** "Composed of discrete components such that a change to one component has minimal impact on other components."
- **Cobertura determinista.** **Alto** (~75%). dependency-cruiser, madge (circular deps), ESLint boundaries plugin, file size lints, eslint-plugin-import/no-cycle.
- **Anchors:**
  - **3** — Flat `src/` con 50+ files mezclados o nesting profundo sin lógica; circular dependencies; deep relative imports `../../../`; features importan internals de otras features; god components 300+ líneas.
  - **6** — Top-level por kind (`components/`, `screens/`, `utils/`) pero features dispersas; algunas pain de relative imports; coupling ocasional sin circulares.
  - **8** — Feature-sliced; cada feature tiene componentes/hooks/types/tests propios; shared en `shared/`; path aliases (`@/features/*`); coupling solo vía interfaces tipadas.
  - **10** — Feature slices con public API explícita (`index.ts` re-exports); enforced por tooling (ESLint boundaries, dependency-cruiser); cross-feature imports solo vía public API.

## 7.2 ISO_MAINT_REUSE — Reusability

- **Definición ISO.** "Asset can be used in more than one system, or in building other assets."
- **Cobertura determinista.** **Medio** (~60%). jscpd (duplication), copy-paste detection, props API analysis (PropTypes/TypeScript surface area).
- **Anchors:**
  - **3** — Copy-paste de skeletons (lists, forms, cards); divergence sutil entre copias; props API mezcla data + UI + callbacks + styling overrides; types loose (`any`).
  - **6** — Repetición que pide extracción; props consistentes pero con boolean-flag explosion; algunos `convenience props` duplican context.
  - **8** — Patrones compartidos extraídos (componentes/hooks); composition over configuration; `children`/slots; props minimal y cohesivos; required vs optional deliberado.
  - **10** — Abstracción ganada (rule of three respetada); polymorphic props (`as`); compound components; props son la documentación.

## 7.3 ISO_MAINT_ANAL — Analysability

- **Definición ISO.** "Effectiveness and efficiency with which it is possible to assess the impact of a change, diagnose deficiencies, or identify parts to be modified."
- **Cobertura determinista.** **Alto** (~80%). ESLint complexity rules, file-size lints, naming conventions lint, comment ratio, type-coverage, Sentry breadcrumbs presence.
- **Anchors:**
  - **3** — Nombres `data`, `Component2`, `utils.ts`; componentes >300 líneas; nesting >5 niveles; sin comentarios ni README útil; sin tipos o muchos `any`; debugging vía `console.log`.
  - **6** — Nombres grammaticales pero genéricos; componentes <200 líneas mostly; comentarios "why" ocasionales; README shallow; strict TS con loopholes.
  - **8** — Nombres describen behavior desde el caller; componentes <150 líneas; nesting ≤3; "why" comments en non-obvious; JSDoc en hooks/components públicos; README con setup+arquitectura; strict + noUncheckedIndexedAccess.
  - **10** — Nombres = resumen del archivo; ADRs documentan decisiones mayores; type-coverage monitoreado; onboarding documentado; logs estructurados con context.

## 7.4 ISO_MAINT_MOD2 — Modifiability

- **Definición ISO.** "Can be effectively and efficiently modified without introducing defects or degrading existing product quality."
- **Cobertura determinista.** **Alto** (~70%). State management coupling analysis, prop drilling detection, single-source-of-truth checks, ESLint react-hooks/exhaustive-deps, type strictness.
- **Anchors:**
  - **3** — State everywhere (local + context + Redux + singleton + URL) con responsabilidades superpuestas; prop drilling 4+ niveles; tipos miran shape solo (sin discriminated unions); illegal states representables.
  - **6** — Un store global pero unclear cuándo usar local vs global; server state mezclado con UI; tipos comunican estado básico.
  - **8** — Server state en query cache; UI state local o en small store; URL para nav state; form state en form lib; branded types para IDs; discriminated unions para state machines; `Readonly`.
  - **10** — Cada tipo de state tiene home documentado y enforced por convention/lint; types make illegal states unrepresentable; parse-don't-validate como idioma; cambios típicos tocan ≤3 archivos.

## 7.5 ISO_MAINT_TEST — Testability

- **Definición ISO.** "Effectiveness and efficiency with which test criteria can be established and tests performed to determine whether those criteria have been met."
- **Cobertura determinista.** **Alto** (~75%). Coverage tools (jest --coverage), Testing Library presence, snapshot ratio, E2E framework presence (Playwright/Cypress/Detox/Maestro), DI patterns.
- **Anchors:**
  - **3** — Sin tests o tests vanity sin assertions; componentes hard-to-test (side effects en render, singletons importados directamente, global fetch); flake tolerada.
  - **6** — Tests sobre utils + algunos componentes; coverage <40%; testable con scaffolding manual.
  - **8** — Critical paths cubiertos (auth, mutations, checkout); 60–80% coverage trending up; React Testing Library / RNTL idiomático; tests = specs; E2E con semantic selectors en CI; flake = P0; DI/abstracciones.
  - **10** — Coverage es byproduct, no goal; cada bug fix landea con regression test; visual regression / performance assertions en E2E; testability como design principle; test utilities self-tested.

---

# 8. Flexibility

> ISO (2023, reemplaza Portability): "Degree to which a product can be used effectively, efficiently, and with satisfaction in contexts beyond those initially specified."

## 8.1 ISO_FLEX_ADAPT — Adaptability

- **Definición ISO.** "Can be effectively and efficiently adapted for or transferred to different or evolving hardware, software or other operational or usage environments."
- **Cobertura determinista.** **Medio** (~55%). Responsive design lints, Platform.select coverage, theme system detection, RTL support detection.
- **Anchors:**
  - **3** — Fixed widths; horizontal scroll en mobile; sin Platform branching; sin theme system; ltr-only.
  - **6** — Main breakpoints cubiertos; algún Platform branching; theme single-source pero sin dark mode.
  - **8** — Layouts fluidos; breakpoint system; RN responsive a orientación + size classes; dark/light parity; RTL probado.
  - **10** — Test matrix real device; safe-area + notch + keyboard avoidance; zoom/text-scale respetados; tokens drive everything (color/spacing/typography).

## 8.2 ISO_FLEX_SCAL — Scalability

- **Definición ISO.** "Can handle growing amounts of work, or be enlarged to accommodate growth."
- **Cobertura determinista.** **Medio** (~50%). Code splitting detection, virtualization detection, query pagination, lazy loading, store sharding.
- **Anchors:**
  - **3** — Bundle único; listas unbounded; queries sin LIMIT; store global con todo dentro.
  - **6** — Code splitting por ruta; virtualization en pantallas obvias.
  - **8** — Code splitting ruta+componente; virtualization con keys/getItemLayout; lazy loading de imágenes; store sliced (Redux Toolkit slices / Zustand stores separados).
  - **10** — Bundle budgets enforced en CI con regression gates; load tests sobre listas/queries grandes.

## 8.3 ISO_FLEX_INST — Installability `[no auditada por defecto]`

- **Definición ISO.** "Can be successfully installed and/or uninstalled in a specified environment."
- **Cobertura determinista.** **Bajo** (~15%). Detectable parcialmente: presencia de install scripts, uninstall hooks, package size, deeplinks de app stores.
- **Anchors (aspiracionales):**
  - **3** — Install/build steps undocumented; sin Docker/CI artifacts; tamaño del binary RN inflado.
  - **6** — README con install steps; CI build green; tamaño razonable.
  - **8** — Build reproducible (lockfile, `engines`); CI publica artifacts versionados; install scripts idempotentes.
  - **10** — Hermetic builds; packaging optimizado (App Bundle / PWA optimized); uninstall limpia state.

## 8.4 ISO_FLEX_REPL — Replaceability

- **Definición ISO.** "Can replace another specified product for the same purpose in the same environment."
- **Cobertura determinista.** **Medio** (~45%). Vendor lock-in detection (custom hooks abstrayendo libs), data export presence, feature flags for migration.
- **Anchors:**
  - **3** — Lock-in extremo: components dependen de APIs de un vendor específico (Firebase JS SDK importado en componentes, `moment` everywhere, axios concrete).
  - **6** — Algunas abstracciones (un cliente HTTP wrapping fetch/axios); migrations factibles con esfuerzo.
  - **8** — Capa de abstracción consistente (data layer detrás de hooks/services); export de data en formatos estándar; deps con alternativas identificadas.
  - **10** — Decisiones de vendor documentadas con exit plan; feature flags para canary migrations; tests sobre abstracciones aseguran swap-in.

---

# 9. Safety

> ISO (2023, nueva característica): "Degree to which a product under defined conditions avoids a state in which human life, health, property, or environment is endangered."
>
> **Política rax v2.** Para apps de consumo, peso default = 2 (mínimo). Para safety-critical (medical/automotive/aviónica), `--profile safety-critical` sube peso a 10+ y todas las sub-características pasan a auditadas.

## 9.1 ISO_SAFE_OP — Operational Constraint `[no auditada por defecto]`

- **Definición ISO.** "Operates within defined operational constraints (e.g., dose limits in a medical device)."
- **Cobertura determinista.** **Bajo** (~15%) en consumer; **Alto** (~70%) en safety-critical (con specs explícitas de constraints).
- **Anchors (safety-critical):**
  - **3** — Sin enforcement de constraints (UI permite valores fuera de rango); sin runtime checks.
  - **6** — Constraints en UI (max attribute) pero no runtime; sin tests.
  - **8** — Constraints validados runtime + UI; tests cubren bordes; backend co-valida.
  - **10** — Constraints en tipos (branded numeric ranges); fuzz/property tests; backend rechaza out-of-range con audit log.

## 9.2 ISO_SAFE_RISK — Risk Identification `[no auditada por defecto]`

- **Definición ISO.** "Identifies hazards or risks during operation."
- **Cobertura determinista.** **Bajo** (~10%) en consumer.
- **Anchors (safety-critical):**
  - **3** — Sin detección de estados peligrosos; UI no diferencia normal vs peligroso.
  - **6** — Algún warning ocasional.
  - **8** — Hazard taxonomy implementada; warnings claros en UI.
  - **10** — Risk model formal (FMEA u otro); detección automática + alertas tiered.

## 9.3 ISO_SAFE_FS — Fail Safe

- **Definición ISO.** "Reverts to a safe state in the event of a failure."
- **Cobertura determinista.** **Medio** (~60%). Error boundary fallbacks, graceful degradation, offline-safe states.
- **Anchors:**
  - **3** — Componente falla → app crashea; offline → white screen; error en mutation → estado inconsistente.
  - **6** — Error boundary top-level; offline indicator; rollback ad-hoc.
  - **8** — Error boundaries con fallback UI a varios niveles; optimistic updates con rollback; offline-first donde aplica.
  - **10** — Fail-safe states diseñados explícitamente per-feature; transactional flows con rollback semantics; tested.

## 9.4 ISO_SAFE_HW — Hazard Warning `[no auditada por defecto]`

- **Definición ISO.** "Warns users of detected unacceptable risks."
- **Cobertura determinista.** **Bajo** (~10%) en consumer.
- **Anchors (safety-critical):**
  - **3** — Sin warnings; o warnings genéricos sin info accionable.
  - **6** — Warnings en algunas situaciones críticas.
  - **8** — Warning system tiered (info/warning/critical) con acknowledgment requerido en críticos.
  - **10** — Warnings localizados, accesibles (screen reader), con audit trail; A/B sobre comprehension.

## 9.5 ISO_SAFE_SI — Safe Integration

- **Definición ISO.** "Maintains safety when integrating with components or systems."
- **Cobertura determinista.** **Medio** (~55%). Supply chain audit, deep link validation, WebView hardening, native module review.
- **Anchors:**
  - **3** — Deps con CVEs alta reachables; WebView abierto; deep links sin validar; native modules sin revisión.
  - **6** — Lockfile + audit ocasional; WebView restringido parcialmente; deep links validados parcialmente.
  - **8** — Audit en CI; WebView con `originWhitelist` estricto + JS bridge auditado; deep links typed+validated; native modules listados con auditor responsable.
  - **10** — SBOM + provenance; threat model de integraciones; tests sobre boundaries.

---

# Apéndice A — Tabla de cobertura determinista

> Resumen rápido para la Fase 2 (orquestador determinista). El peso α (0..1) indica cuánto del score puede provenir de tools antes de invocar al LLM. α alto → LLM solo confirma; α bajo → LLM lleva el peso.

| Sub-característica | Cobertura | α sugerido | Tools deterministas principales |
|---|---|---:|---|
| ISO_FUN_COMP | bajo | 0.0 | — *(no auditada)* |
| ISO_FUN_CORR | medio | 0.3 | E2E coverage, mutation testing |
| ISO_FUN_APPR | bajo | 0.0 | — *(no auditada)* |
| ISO_FUN_IDEN | bajo | 0.1 | README/onboarding presence |
| ISO_PERF_TIME | alto | 0.7 | React Profiler, ESLint react-perf, Lighthouse |
| ISO_PERF_RES | alto | 0.8 | bundle-analyzer, depcheck, image-size lints |
| ISO_PERF_CAP | medio | 0.5 | virtualization detection, query limits |
| ISO_COMP_COEX | medio | 0.5 | peer-deps, Platform.select coverage |
| ISO_COMP_INTER | medio | 0.6 | OpenAPI/GraphQL codegen, Zod presence |
| ISO_INTER_REC | bajo | 0.2 | empty-state lints |
| ISO_INTER_LEARN | bajo | 0.15 | onboarding/tooltip presence |
| ISO_INTER_OP | alto | 0.75 | jsx-a11y, axe-core, focus lints |
| ISO_INTER_UEP | alto | 0.7 | Zod/Yup, confirm-pattern detection |
| ISO_INTER_ENG | bajo | 0.2 | animation/haptic presence |
| ISO_INTER_INC | alto | 0.75 | axe-core, jsx-a11y, contrast checkers, i18n analyzer |
| ISO_INTER_UAA | medio | 0.4 | help/recovery action detection |
| ISO_INTER_SD | medio | 0.4 | state-coverage detection |
| ISO_REL_FAULT | alto | 0.75 | TS strict, react-hooks rules, no-floating-promises |
| ISO_REL_AVAIL | bajo | 0.0 | — *(no auditada)* |
| ISO_REL_FT | alto | 0.7 | error-boundary detection, retry/backoff patterns |
| ISO_REL_REC | medio | 0.5 | Sentry/source-maps detection, persistence detection |
| ISO_SEC_CONF | alto | 0.8 | gitleaks, semgrep secrets, keychain detection |
| ISO_SEC_INT | alto | 0.75 | semgrep XSS, react/no-danger, Zod presence |
| ISO_SEC_NR | bajo | 0.1 | audit-log detection |
| ISO_SEC_ACC | medio | 0.4 | Sentry user-context, analytics correlation |
| ISO_SEC_AUTH | alto | 0.7 | OAuth/SSO patterns, refresh logic, route guards |
| ISO_SEC_RES | medio | 0.5 | npm audit, deeplink validation, WebView hardening |
| ISO_MAINT_MOD | alto | 0.75 | dependency-cruiser, madge, ESLint boundaries |
| ISO_MAINT_REUSE | medio | 0.6 | jscpd, props-API analysis |
| ISO_MAINT_ANAL | alto | 0.8 | complexity lints, type-coverage, comment ratio |
| ISO_MAINT_MOD2 | alto | 0.7 | state-mgmt analysis, prop-drilling detection |
| ISO_MAINT_TEST | alto | 0.75 | coverage tools, RTL/jest presence, E2E framework |
| ISO_FLEX_ADAPT | medio | 0.55 | responsive lints, Platform coverage, theme detection |
| ISO_FLEX_SCAL | medio | 0.5 | code-splitting detection, virtualization |
| ISO_FLEX_INST | bajo | 0.15 | — *(no auditada)* |
| ISO_FLEX_REPL | medio | 0.45 | vendor-lock-in heuristics |
| ISO_SAFE_OP | bajo | 0.15 | — *(no auditada por defecto)* |
| ISO_SAFE_RISK | bajo | 0.1 | — *(no auditada por defecto)* |
| ISO_SAFE_FS | medio | 0.6 | error-boundary fallbacks, rollback patterns |
| ISO_SAFE_HW | bajo | 0.1 | — *(no auditada por defecto)* |
| ISO_SAFE_SI | medio | 0.55 | npm audit, WebView/deeplink hardening |

> **Cómo se usa.** En la Fase 2 (`scripts/aggregation.py` + `deterministic_layer.sh`):
>
> ```
> final_score = α · deterministic_score + (1 − α) · llm_score
> ```
>
> Para las sub-características con `α = 0.0`, el LLM lleva el peso entero (o la sub-característica queda excluida si el peso de característica es 0). Para `α ≥ 0.7`, el LLM solo se invoca para refinar / abstenerse, no para liderar.

---

# Apéndice B — Diferencias visibles vs v1

| Cambio | v1 | v2 |
|---|---|---|
| Categoría top-level | `ARC, CQR, RXP, PRF, SEC, UXA, TYP, ERR, TST, DEP, APT` (11) | `ISO_FUN, ISO_PERF, ISO_COMP, ISO_INTER, ISO_REL, ISO_SEC, ISO_MAINT, ISO_FLEX, ISO_SAFE` (9 ISO oficiales) |
| Anti-patterns como categoría | Sí (APT) | No — anti-patterns son red flags dentro de sub-características relevantes |
| Nombres | Inventados | ISO/IEC 25010:2023 |
| Cobertura determinista declarada | No | Sí (alto/medio/bajo + α sugerido) |
| Pesos por defecto | Intuitivos | Perfil "general consumer mobile/web app" basado en literatura |
| Sub-características fuera de scope estática | Eliminadas o forzadas | Incluidas con `[no auditada por defecto]` y peso 0 |

---

# Cuándo una sub-característica es `n/a` vs `deferred`

(Misma política que v1, generalizada.)

- **`n/a`** — la sub-característica es categóricamente inaplicable (RN-specific en proyecto web-only; UXA en headless library; safety-critical en consumer app sin profile activado). Se elimina del cálculo de la categoría.
- **`deferred`** — no se pudo evaluar por scope (quick mode, no enough files). Cuenta como baseline para agregación pero se flaggea en scope notes. Nunca usar `deferred` para esconder findings.

Las sub-características con `[no auditada por defecto]` empiezan en estado `n/a` con peso 0. Activarlas con `--profile safety-critical` o `config.json` las saca de `n/a` y entran al cálculo normal.

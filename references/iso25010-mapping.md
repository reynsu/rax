# ISO/IEC 25010:2023 ↔ rax v1 — Mapeo bidireccional

> **Propósito.** Anclar el rubric de rax al estándar internacional ISO/IEC 25010:2023 para que (a) los nombres de las dimensiones no sean inventados, (b) las definiciones tengan procedencia externa citada, y (c) los pesos por defecto provengan de literatura de la industria en lugar de mi intuición.
>
> **Alcance.** Este archivo es la fuente de verdad para el re-mapeo. Los pasos posteriores (1.2 reescritura del rubric, 2.x reglas Semgrep, 4.x prompts del juez LLM) consumen los identificadores `ISO_<CHAR>_<SUB>` definidos aquí.
>
> **Versión ISO.** ISO/IEC 25010:2023 (revisión que reemplaza la 2011). Cambios relevantes: Usability → **Interaction Capability**, Portability → **Flexibility**, se añade **Safety** como característica nueva, y Functional Suitability incorpora "Functional Identification".
>
> **Fuentes.**
> - https://iso25000.com/index.php/en/iso-25000-standards/iso-25010
> - https://quality.arc42.org/standards/iso-25010
> - ISO/IEC 25010:2023 (texto del estándar, citas indirectas; el estándar es de pago)

---

## 1. Functional Suitability

**Definición ISO.** "Degree to which a product or system provides functions that meet stated and implied needs when used under specified conditions."

| ID estable | Sub-característica | Definición ISO (síntesis) | Cobertura v1 | Mapeo desde v1 |
|---|---|---|---|---|
| `ISO_FUN_COMP` | Functional Completeness | Set of functions covers all specified tasks and user objectives. | ❌ No cubierto | — |
| `ISO_FUN_CORR` | Functional Correctness | Functions provide correct results with the needed precision. | ⚠️ Parcial | TST-3 (E2E como proxy de "lo que se especificó funciona") |
| `ISO_FUN_APPR` | Functional Appropriateness | Functions facilitate the accomplishment of specified tasks. | ❌ No cubierto | — |
| `ISO_FUN_IDEN` | Functional Identification | Capability to identify the functional capabilities of the product. | ❌ No cubierto | — |

**Nota de cobertura determinista.** Bajo. Functional Suitability requiere conocer la spec; rax no la tiene. Se incluye como característica para ser **explícitamente excluida del scoring** (peso 0 por defecto) y mostrada como "no auditada" en el reporte. Esto evita pretender que somos un auditor funcional cuando no lo somos.

---

## 2. Performance Efficiency

**Definición ISO.** "Performance relative to the amount of resources used under stated conditions."

| ID estable | Sub-característica | Definición ISO (síntesis) | Cobertura v1 | Mapeo desde v1 |
|---|---|---|---|---|
| `ISO_PERF_TIME` | Time Behaviour | Response, processing times, and throughput rates meet requirements. | ✅ Alta | PRF-1, PRF-2, PRF-7 |
| `ISO_PERF_RES` | Resource Utilization | Amounts and types of resources used meet requirements. | ✅ Alta | PRF-3, PRF-4, PRF-5, PRF-6, DEP-2 (footprint) |
| `ISO_PERF_CAP` | Capacity | Maximum limits of a product/system meet requirements. | ⚠️ Parcial | PRF-3 (list virtualization); no medición de límites reales |

**Nota de cobertura determinista.** Alta. Tools como bundle-analyzer, ESLint reglas de re-render, React DevTools profiler, Lighthouse, Hermes profiler producen señales objetivas.

---

## 3. Compatibility

**Definición ISO.** "Degree to which a product can exchange information with other products and/or perform its required functions while sharing the same hardware or software environment."

| ID estable | Sub-característica | Definición ISO (síntesis) | Cobertura v1 | Mapeo desde v1 |
|---|---|---|---|---|
| `ISO_COMP_COEX` | Co-existence | Performs efficiently while sharing environment with other products. | ⚠️ Parcial | RXP-7 (Platform splits), DEP-1 (peer deps) |
| `ISO_COMP_INTER` | Interoperability | Two or more systems can exchange information and use it. | ⚠️ Parcial | TYP-3 (validación en boundaries), SEC-6 |

**Nota de cobertura determinista.** Media. Detectable a nivel de package.json (peer dep warnings), Platform.OS coverage, contratos OpenAPI/GraphQL si están presentes.

---

## 4. Interaction Capability

**Definición ISO (2023).** "Degree to which a product can be interacted with by specified users to exchange information via the user interface to complete the intended task." *(Reemplaza "Usability" de la edición 2011 y amplía el alcance.)*

| ID estable | Sub-característica | Definición ISO (síntesis) | Cobertura v1 | Mapeo desde v1 |
|---|---|---|---|---|
| `ISO_INTER_REC` | Appropriateness Recognizability | Users can recognize whether the product is appropriate for their needs. | ⚠️ Parcial | UXA-4 (empty/error states educativos) |
| `ISO_INTER_LEARN` | Learnability | Users can learn how to use the product. | ❌ No cubierto | — |
| `ISO_INTER_OP` | Operability | Easy to operate and control. | ✅ Alta | UXA-2 (focus/keyboard), UXA-5 (responsive), UXA-6 (touch targets) |
| `ISO_INTER_UEP` | User Error Protection | Protects users against making errors. | ✅ Alta | UXA-4 (loading/error UX), ERR-3 (user-facing error UX), TYP-3 (runtime validation) |
| `ISO_INTER_ENG` | User Engagement | Pleasing and satisfying interaction. | ⚠️ Parcial | UXA-6 (haptics, motion) — auditable parcialmente |
| `ISO_INTER_INC` | Inclusivity | Usable by people with widest range of characteristics and capabilities. | ✅ Alta | UXA-1 (a11y roles), UXA-3 (contraste), UXA-7 (i18n) |
| `ISO_INTER_UAA` | User Assistance | Provides assistance when users need help. | ⚠️ Parcial | UXA-4 (error states con next step), ERR-3 |
| `ISO_INTER_SD` | Self-descriptiveness | Provides appropriate information at right time and place. | ⚠️ Parcial | UXA-4 (empty states); no medible directamente vía estática |

**Nota de cobertura determinista.** Media-alta para Operability/Inclusivity (axe-core, ESLint jsx-a11y, eslint-plugin-react-native-a11y, contrast checkers). Baja para Learnability/Engagement (requiere usuarios reales).

---

## 5. Reliability

**Definición ISO.** "Degree to which a system performs specified functions under specified conditions for a specified period of time."

| ID estable | Sub-característica | Definición ISO (síntesis) | Cobertura v1 | Mapeo desde v1 |
|---|---|---|---|---|
| `ISO_REL_FAULT` | Faultlessness *(antes "Maturity")* | Performs specified functions without fault under normal operation. | ✅ Alta | TYP-1, TYP-2, TYP-4 (ill states unrepresentable), ERR-2 (async error handling) |
| `ISO_REL_AVAIL` | Availability | Operational and accessible when required. | ❌ No cubierto | — *(infra concern, no estática)* |
| `ISO_REL_FT` | Fault Tolerance | Operates as intended despite hardware/software faults. | ✅ Alta | ERR-1 (error boundaries), ERR-2, ERR-5 (offline modes) |
| `ISO_REL_REC` | Recoverability | Recovers data and re-establishes desired state after failure. | ✅ Media | ERR-5 (queued mutations on reconnect), ERR-4 (logging para post-mortem) |

**Nota de cobertura determinista.** Alta para Faultlessness y Fault Tolerance; tools como react-error-boundary, ESLint no-floating-promises, TypeScript strict, AbortController checks.

---

## 6. Security

**Definición ISO.** "Degree to which a product or system defends against attack patterns by malicious actors and protects information and data."

| ID estable | Sub-característica | Definición ISO (síntesis) | Cobertura v1 | Mapeo desde v1 |
|---|---|---|---|---|
| `ISO_SEC_CONF` | Confidentiality | Data accessible only to those authorized. | ✅ Alta | SEC-1 (secrets), SEC-3 (sensitive data storage), SEC-5 (TLS) |
| `ISO_SEC_INT` | Integrity | Prevents unauthorized access/modification of programs or data. | ✅ Alta | SEC-2 (XSS), SEC-6 (input validation), SEC-7 (supply chain) |
| `ISO_SEC_NR` | Non-repudiation | Actions or events can be proven to have taken place. | ❌ No cubierto | — |
| `ISO_SEC_ACC` | Accountability | Actions of an entity can be traced uniquely to that entity. | ⚠️ Parcial | ERR-4 (logging con user context) |
| `ISO_SEC_AUTH` | Authenticity | Identity of a subject or resource can be proved. | ✅ Alta | SEC-4 (auth & session) |
| `ISO_SEC_RES` | Resistance | Sustains operations while under attack. | ⚠️ Parcial | SEC-7 (CVE response), SEC-8 (deep links, WebView hardening) |

**Nota de cobertura determinista.** Alta. Semgrep tiene reglas extensas (`p/javascript`, `p/react`, `p/owasp-top-ten`); npm audit, secret scanning, ESLint react/no-danger.

---

## 7. Maintainability

**Definición ISO.** "Degree of effectiveness and efficiency with which a product can be modified to improve, correct, or adapt it to changes in environment, requirements, and functional specifications."

| ID estable | Sub-característica | Definición ISO (síntesis) | Cobertura v1 | Mapeo desde v1 |
|---|---|---|---|---|
| `ISO_MAINT_MOD` | Modularity | Components are composed of discrete components such that change to one has minimal impact on others. | ✅ Alta | ARC-1, ARC-2, ARC-3, ARC-5, RXP-2 (composition) |
| `ISO_MAINT_REUSE` | Reusability | Asset can be used in more than one system or in building other assets. | ✅ Alta | CQR-3 (DRY), RXP-2, RXP-3 (props API) |
| `ISO_MAINT_ANAL` | Analysability | Effectiveness of assessing the impact of an intended change, diagnosing deficiencies, or identifying parts to be modified. | ✅ Alta | CQR-1, CQR-2, CQR-4, CQR-5, TYP-1, TYP-2, ERR-4 |
| `ISO_MAINT_MOD2` | Modifiability | Product can be modified without introducing defects or degrading quality. | ✅ Alta | ARC-3, ARC-4, RXP-1, RXP-5, TYP-4 |
| `ISO_MAINT_TEST` | Testability | Effectiveness and efficiency with which test criteria can be established and tests performed. | ✅ Alta | TST-1, TST-2, TST-3, TST-4 |

**Nota de cobertura determinista.** Alta. ESLint complexity rules, dependency-cruiser, jscpd (duplication), tsc strict, jest --coverage, react-hooks/rules-of-hooks.

---

## 8. Flexibility

**Definición ISO (2023).** "Degree to which a product can be used effectively, efficiently, and with satisfaction in contexts beyond those initially specified." *(Reemplaza "Portability" de la edición 2011 con un alcance más amplio.)*

| ID estable | Sub-característica | Definición ISO (síntesis) | Cobertura v1 | Mapeo desde v1 |
|---|---|---|---|---|
| `ISO_FLEX_ADAPT` | Adaptability | Can be adapted for different or evolving hardware, software, or other operational environments. | ⚠️ Parcial | UXA-5 (responsive), RXP-7 (Platform.select) |
| `ISO_FLEX_SCAL` | Scalability | Can handle growing amounts of work or be enlarged to accommodate growth. | ⚠️ Parcial | PRF-3 (virtualization), PRF-4 (code splitting) |
| `ISO_FLEX_INST` | Installability | Can be successfully installed and uninstalled in a specified environment. | ❌ No cubierto | — *(out of scope para audit estática)* |
| `ISO_FLEX_REPL` | Replaceability | Can replace another specified product for the same purpose in the same environment. | ⚠️ Parcial | DEP-1 (freshness), DEP-2 (vendor-neutral alternatives) |

**Nota de cobertura determinista.** Media. Adaptability/Scalability medibles parcialmente; Installability requiere artefactos de build.

---

## 9. Safety

**Definición ISO (2023, nueva).** "Degree to which a product under defined conditions avoids a state in which human life, health, property, or environment is endangered."

| ID estable | Sub-característica | Definición ISO (síntesis) | Cobertura v1 | Mapeo desde v1 |
|---|---|---|---|---|
| `ISO_SAFE_OP` | Operational Constraint | Operates within defined operational constraints. | ❌ No cubierto | — |
| `ISO_SAFE_RISK` | Risk Identification | Identifies hazards/risks during operation. | ❌ No cubierto | — |
| `ISO_SAFE_FS` | Fail Safe | Reverts to safe state on failure. | ⚠️ Parcial | ERR-1 (error boundaries con fallbacks); ERR-5 (offline degraded state) |
| `ISO_SAFE_HW` | Hazard Warning | Warns users of detected unacceptable risks. | ❌ No cubierto | — |
| `ISO_SAFE_SI` | Safe Integration | Maintains safety when integrating with components/systems. | ⚠️ Parcial | SEC-7 (supply chain), SEC-8 (deep links validados) |

**Nota de cobertura determinista.** Baja. Safety en sentido ISO se aplica primariamente a sistemas safety-critical (médicos, automotrices, aviónica). Para una app móvil de consumo, el peso por defecto es bajo y se ofrece como **categoría opcional activable** vía config.

---

## 10. Mapeo inverso — categorías rax v1 → ISO

| v1 | Peso v1 | Mapeo principal ISO | Mapeos secundarios | Notas |
|---|---|---|---|---|
| **ARC** — Architecture & Structure | 12 | Maintainability (Modularity, Modifiability) | — | Se descompone en sub-características ISO; identidad propia desaparece. |
| **CQR** — Code Quality & Readability | 10 | Maintainability (Analysability) | Maintainability (Modifiability) | Idem. |
| **RXP** — React/RN Patterns | 12 | Maintainability (Modularity, Modifiability, Reusability) | Reliability (Faultlessness vía Hooks correctness) | Patrones específicos al stack siguen como anchors v2 dentro de las sub-características ISO. |
| **PRF** — Performance | 12 | Performance Efficiency (Time Behaviour, Resource Utilization) | Flexibility (Scalability) | Mapeo casi 1-a-1. |
| **SEC** — Security | 13 | Security (Confidentiality, Integrity, Authenticity) | Security (Resistance) | Mapeo casi 1-a-1. |
| **UXA** — UI/UX & Accessibility | 10 | Interaction Capability (Inclusivity, Operability, User Error Protection) | Flexibility (Adaptability vía responsive) | Renombre conceptual: UXA → Interaction Capability. |
| **TYP** — Type Safety | 8 | Maintainability (Analysability) | Reliability (Faultlessness), Security (Integrity vía runtime validation) | TYP-3 (runtime validation) cruza Security. |
| **ERR** — Error Handling & Resilience | 7 | Reliability (Fault Tolerance, Recoverability) | Interaction Capability (User Error Protection), Safety (Fail Safe) | ERR cubre tres características ISO. |
| **TST** — Testing | 8 | Maintainability (Testability) | Functional Suitability (Functional Correctness vía E2E) | E2E como evidencia parcial de FUN_CORR. |
| **DEP** — Dependencies & Bundle | 4 | Security (Resistance) | Performance Efficiency (Resource Utilization), Maintainability (Modifiability) | Crosscut. |
| **APT** — Anti-patterns | 4 | *(meta-categoría)* | — | **Se descarta como categoría top-level.** Los anti-patterns se reasignan como red flags dentro de las sub-características ISO relevantes. Ver "Decisiones de diseño". |

---

## 11. Decisiones de diseño

> Justificación de cada mapeo no obvio en 2-3 líneas. Estas decisiones son revisables; este documento es la fuente de verdad versionada.

### 11.1 APT (Anti-patterns) deja de ser categoría top-level

Anti-patterns no es una *quality characteristic*; es un mecanismo de detección. En ISO 25010 la calidad se mide positivamente vía sub-características, no vía conteo de defectos. Se reasigna cada anti-pattern de `antipatterns.md` a la sub-característica ISO correspondiente (por ejemplo, "god component" → `ISO_MAINT_MOD`; "prop drilling" → `ISO_MAINT_MOD2`; "effect-as-state" → `ISO_REL_FAULT`). El red flag sigue existiendo; pero pulsa el score de la sub-característica, no de una categoría artificial.

### 11.2 UXA renombrada a Interaction Capability (no Usability)

La edición 2023 reemplaza explícitamente "Usability" por "Interaction Capability" para cubrir interacciones no humanas (agentes, sistemas) y enfatizar que la capacidad incluye *exchange of information*, no solo facilidad. Adoptar el nuevo nombre alinea rax al estándar vigente.

### 11.3 ARC desaparece como categoría; sus subcriterios viven en Maintainability

ARC-1..ARC-5 son aspectos de Modularidad y Modificabilidad. Mantener ARC como categoría duplicaría señales con CQR/RXP. La consolidación reduce la dimensionalidad y evita doble-conteo (un god component que viola ARC-2 y RXP-2 hoy se penaliza dos veces).

### 11.4 TST no es solo Testability — también evidencia de Functional Correctness

E2E tests son la única evidencia que rax puede observar sobre si "lo que se especificó funciona". Mapeamos TST-3 a `ISO_FUN_CORR` con peso bajo y nota de "evidencia parcial — depende de cobertura E2E". Esto explicita el límite.

### 11.5 Functional Suitability se incluye con peso 0 por defecto

ISO 25010 define las 9 características; rax solo puede auditar 8 con confianza. En lugar de omitir Functional Suitability silenciosamente, se incluye con peso 0 y se reporta como "no auditada — fuera del alcance de análisis estático". El usuario puede subir el peso si tiene tests E2E que rax pueda usar como evidencia.

### 11.6 Safety queda opcional, peso bajo por defecto

Safety en sentido ISO aplica a sistemas safety-critical. Para una app móvil de consumo el peso por defecto es 2 (conservador, pero no cero — Fail Safe vía error boundaries sí es relevante). Apps médicas/financieras pueden subir el peso vía config.

### 11.7 Pesos por defecto: industria > intuición

Los pesos v1 (ARC=12, SEC=13, …) provienen de mi intuición. Para v2 se adoptan los pesos sugeridos por:
- Wagner et al., *Quamoco Quality Model* (defaults para "interactive software")
- ISO/IEC 25010 industry profiles para "consumer mobile/web application"
- IEEE Software Quality literature, perfiles para "general consumer mobile app"

Ver siguiente sección.

---

## 12. Pesos por defecto — perfil "general consumer mobile/web app"

| ISO Característica | Peso default v2 | Justificación |
|---|---:|---|
| Functional Suitability | **0** | No auditable estáticamente. Activable si el proyecto tiene cobertura E2E significativa. |
| Performance Efficiency | **13** | App de consumo: latencia percibida domina abandono. Literatura industria sugiere 12–15. |
| Compatibility | **3** | Bajo en consumer apps de un solo stack. Sube en apps con muchas integraciones. |
| Interaction Capability | **17** | Reemplaza UXA (10 v1) + absorbe parte de ERR-3. App de consumo prioriza UX. |
| Reliability | **12** | Crashes y errores no manejados son top causa de uninstalls (Crashlytics, Firebase data). |
| Security | **15** | Top concern en apps que manejan PII/auth. Penalizada con sigmoid no-lineal (ver paso 1.3). |
| Maintainability | **25** | Absorbe ARC (12) + CQR (10) + parte de RXP (12) + TST (8) + TYP (8) v1 ≈ 50. Re-balanceado para no dominar el resto. Sigue siendo la característica de mayor peso porque mantenibilidad es el principal driver de costo total a 2+ años. |
| Flexibility | **5** | Bajo para apps single-platform; sube para apps multi-plataforma o que esperan mucho cambio. |
| Safety | **2** | Mínimo (Fail Safe vía error boundaries) para consumer. Activable para safety-critical (médica, automoción) → 8–10. |
| **Total** | **92** | El faltante (8 puntos) se reserva para "márgenes de redondeo + pesos custom de proyecto" — los pesos finales se normalizan a Σ=100 al cargar config. |

> **Nota.** Estos pesos son el default. `.claude/rax/config.json` puede sobrescribirlos por proyecto. La validación (suma ≈ 100, ±1.0) ocurre al inicio del audit.

### 12.1 Perfiles alternativos (sketches para release)

Para evitar que el default sea único, v2 incluye perfiles preconstruidos:

| Perfil | Diferencias clave vs default |
|---|---|
| `consumer-mobile` | Default. |
| `consumer-web` | Compatibility +2, Flexibility +2 (browser matrix), Safety -2. |
| `enterprise` | Maintainability +3, Reliability +2, Interaction Capability -3. |
| `safety-critical` | Safety +8 (subir a 10), Reliability +3, requiere config explícita. |
| `mvp-early-stage` | Maintainability -8, Performance -3, Functional Suitability +0 (ignorada). Solo para proyectos pre-PMF. |

Los perfiles viven en `references/profiles/*.yaml` y se aplican con `--profile <name>`.

---

## 13. Apéndice — IDs estables (para grep/import)

```
ISO_FUN_COMP, ISO_FUN_CORR, ISO_FUN_APPR, ISO_FUN_IDEN
ISO_PERF_TIME, ISO_PERF_RES, ISO_PERF_CAP
ISO_COMP_COEX, ISO_COMP_INTER
ISO_INTER_REC, ISO_INTER_LEARN, ISO_INTER_OP, ISO_INTER_UEP, ISO_INTER_ENG, ISO_INTER_INC, ISO_INTER_UAA, ISO_INTER_SD
ISO_REL_FAULT, ISO_REL_AVAIL, ISO_REL_FT, ISO_REL_REC
ISO_SEC_CONF, ISO_SEC_INT, ISO_SEC_NR, ISO_SEC_ACC, ISO_SEC_AUTH, ISO_SEC_RES
ISO_MAINT_MOD, ISO_MAINT_REUSE, ISO_MAINT_ANAL, ISO_MAINT_MOD2, ISO_MAINT_TEST
ISO_FLEX_ADAPT, ISO_FLEX_SCAL, ISO_FLEX_INST, ISO_FLEX_REPL
ISO_SAFE_OP, ISO_SAFE_RISK, ISO_SAFE_FS, ISO_SAFE_HW, ISO_SAFE_SI
```

Total: **9 características, 41 sub-características = 41 IDs estables.**

Estos IDs son la unidad atómica que consumen los pasos siguientes (rubric-v2 anchors, Semgrep mappings, Quamoco aggregator, prompts del juez). Cualquier cambio aquí requiere un commit explícito y propaga a todos los consumers.

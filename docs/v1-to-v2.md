# rax v1 → v2 — qué cambió y por qué

> Documento técnico complementario al [CHANGELOG](../CHANGELOG.md). El changelog
> dice **qué** cambió en orden cronológico; este documento explica **por qué**
> cada cambio existe y cómo migrar.
>
> Audiencia: usuarios actuales de rax v1 + colaboradores que quieran entender
> la arquitectura de v2 antes de extenderla.

---

## TL;DR

| Aspecto | v1 | v2 |
|---|---|---|
| Output | Un solo número por categoría (`7.3/10`) | Intervalo con mediana (`[6.4, 8.1]/10, median 7.3`) |
| Rubric | 11 categorías inventadas (ARC, CQR, RXP, …) | 9 características ISO/IEC 25010:2023 + 41 sub-características |
| Juez | Un único `claude -p` | Panel multi-juez (Claude + GPT-4o + Gemini) con N réplicas |
| Linting determinista | Implícito (el LLM lo replicaba) | Capa explícita: Semgrep + ESLint + tsc + madge + jscpd + npm audit |
| Calibración | Ninguna | Conformal split prediction al 90%, validada en CI |
| Sub-característica subjetiva | Score arbitrario | `ABSTAINED` cuando el panel discrepa >1.5 puntos |
| Anti-patterns | Categoría top-level (`APT`) | Red flags dentro de la sub-característica relevante |
| Honestidad pública | "best-in-class auditor" | Footer de transparencia obligatorio en cada audit |
| Costo por audit | ~$0.05 (1 modelo, 1 corrida) | $0.5 – 2 (3 modelos × N réplicas, sólo modo `full`) |

---

## El problema que v2 resuelve

La crítica más demoledora a v1 era: **"de los 22 findings que reportaste, 10 los detecta ESLint."** Ese era simultáneamente el síntoma y la enfermedad:

1. **Trabajo duplicado.** v1 le pedía al LLM detectar cosas que un linter detecta determinísticamente, gastando tokens en patrones obvios.
2. **Varianza no acotada.** Sin calibración, dos corridas del mismo LLM sobre el mismo código producían scores ±1.5 sin razón.
3. **Score puntual sin honestidad.** Un `7.3/10` se interpretaba como precisión real cuando en el fondo era un guess agregado de un solo modelo.
4. **Rubric ad-hoc.** Las categorías y pesos venían de mi intuición, no del estándar de la industria.
5. **Cero garantías estadísticas.** Imposible decir "rax dice 7 con 90% confianza" porque la confianza no existía.

v2 ataca cada uno de los 5 directamente.

---

## 1. Rubric: ISO/IEC 25010:2023 reemplaza categorías inventadas

### v1

```
ARC — Architecture & Structure          (peso 12)
CQR — Code Quality & Readability        (peso 10)
RXP — React / RN Patterns               (peso 12)
PRF — Performance                       (peso 12)
SEC — Security                          (peso 13)
UXA — UI/UX & Accessibility             (peso 10)
TYP — Type Safety                       (peso  8)
ERR — Error Handling & Resilience       (peso  7)
TST — Testing                           (peso  8)
DEP — Dependencies & Bundle             (peso  4)
APT — Anti-patterns                     (peso  4)
```

11 categorías que inventé en una tarde. Pesos también inventados. Subcriterios tipo `ARC-1`, `RXP-7` que sólo tienen sentido para mí.

### v2

Las 9 características de **ISO/IEC 25010:2023** (la edición 2023 reemplaza Usability → Interaction Capability, Portability → Flexibility, y añade Safety):

```
1. Functional Suitability      (FUN)   — peso default 0.05
2. Performance Efficiency      (PERF)  — peso default 0.15
3. Compatibility               (COMP)  — peso default 0.04
4. Interaction Capability      (INTER) — peso default 0.18
5. Reliability                 (REL)   — peso default 0.12
6. Security                    (SEC)   — peso default 0.15
7. Maintainability             (MAINT) — peso default 0.22
8. Flexibility                 (FLEX)  — peso default 0.06
9. Safety                      (SAFE)  — peso default 0.03
```

Cada característica tiene 2–8 sub-características con definición textual del estándar. **41 IDs estables** total (`ISO_SEC_CONF`, `ISO_MAINT_MOD`, …) que son la unidad atómica de scoring.

**Por qué importa:** los nombres ya no son míos. La definición de "Maintainability/Modularity" la pone ISO, no yo. Un audit de rax es defendible frente a un auditor que no acepta "creé mi propio rubric".

**Mapeo bidireccional documentado en:**
- `references/iso25010-mapping.md` — qué v1 → qué v2
- `references/rubric-v2.md` — anchors 3/6/8/10 + α de cobertura por sub-char

### Migración para usuarios v1

Si tenías reportes v1 con `ARC: 7/10`, su equivalente v2 está en `Maintainability/Modularity` (`ISO_MAINT_MOD`). El mapeo completo:

| v1 categoría | v2 característica primaria | v2 secundaria |
|---|---|---|
| ARC | `Maintainability/Modularity, Modifiability` | — |
| CQR | `Maintainability/Analysability` | `Maintainability/Modifiability` |
| RXP | `Maintainability/Modularity, Reusability` | `Reliability/Faultlessness` (Hooks correctness) |
| PRF | `Performance Efficiency/{Time, Resource, Capacity}` | `Flexibility/Scalability` |
| SEC | `Security/{Confidentiality, Integrity, Authenticity}` | `Security/Resistance` |
| UXA | `Interaction Capability/{Inclusivity, Operability, UEP}` | `Flexibility/Adaptability` |
| TYP | `Maintainability/Analysability` | `Reliability/Faultlessness`, `Security/Integrity` |
| ERR | `Reliability/{Fault Tolerance, Recoverability}` | `Interaction Capability/UEP`, `Safety/Fail Safe` |
| TST | `Maintainability/Testability` | `Functional Suitability/Functional Correctness` |
| DEP | `Security/Resistance` | `Performance Efficiency/Resource`, `Maintainability/Modifiability` |
| APT | *(disuelto — ahora son red flags por sub-característica)* | — |

---

## 2. Output: intervalos al 90% reemplazan scores puntuales

### v1

```
Overall: 7.3/10
ARC: 7.0/10
SEC: 6.5/10
```

### v2

```
Overall: [6.4, 8.1]/10  (90% CI, median 7.3)

| ISO Característica       | CI 90%      | Median | Confidence |
|--------------------------|-------------|--------|------------|
| Maintainability          | [6.0, 7.8]  | 7.0    | high       |
| Security                 | [4.8, 7.2]  | 6.0    | medium     |
| Reliability              | ABSTAINED   | —      | low        |
```

**Cómo se construye el intervalo (resumen):**

1. La capa determinista produce un score `det` por sub-característica (descontado de 10 según el conteo y severidad de findings de Semgrep / ESLint / tsc / madge / jscpd / npm audit).
2. El panel multi-juez (3 modelos × N réplicas) produce un score `llm` por sub-característica.
3. `final = α · det + (1 − α) · llm`, donde α viene de `references/deterministic-coverage.md` por sub-char (ej. `ISO_SEC_CONF` → α=0.85, `ISO_INTER_LEARN` → α=0.15).
4. El **conformalizer** (`scripts/conformal.py`, split conformal) envuelve `final` en un intervalo `[final − q, final + q]` donde `q` es el cuantil 1−α de los residuos en un calibration set (synthetic anchors + mined signals + cross-LLM medians).
5. Para el overall, **propagación Monte Carlo**: 10 000 muestras de cada sub-característica, agregadas vía Quamoco/MAUT, percentiles 5 y 95.
6. Si la varianza inter-juez supera 1.5, la sub-característica se marca **`ABSTAINED`** y queda fuera del cálculo.

### Migración para usuarios v1

Un parser v1 que lea un reporte v2 debe:
- Tomar `Overall.median` como el `score` v1.
- Tomar el `Median` de cada categoría como el score v1.
- Tratar `ABSTAINED` como `n/a`.

Un parser v2 que lea un reporte v1 (auto-conversión documentada en `references/report-format.md`):
- Convertir cada score `s` v1 al intervalo sintético `[max(0, s−1), min(10, s+1)]`.
- Marcar el reporte con `compatibility: v1-upgraded`.

---

## 3. Pipeline: capa determinista explícita antes del LLM

### v1

```
codebase ──> claude -p (audit prompt) ──> markdown report
```

Un solo paso. El LLM hacía absolutamente todo: detectar `console.log`, ejecutar la regla de Hooks de React, contar dependencias circulares, *y* razonar sobre arquitectura.

### v2

```
codebase
  │
  ▼
  scripts/deterministic_layer.sh
  ├── Semgrep (p/javascript + p/react + 31 reglas custom rax)
  ├── ESLint (con plugins react/react-hooks/jsx-a11y/...)
  ├── tsc --strict --noEmit
  ├── madge --circular
  ├── jscpd
  └── npm audit
       │
       ▼
       /tmp/rax-deterministic.json   (findings agrupados por ISO_SUB_ID)
       │
       ▼
  scripts/build_prompt.py
       │  + references/rubric-v2.md (filtrado a sub-chars relevantes)
       │  + tests/corpus/synthetic_anchors/ (low + high anchors per sub-char)
       │  + prompts/audit-system.md
       ▼
       /tmp/rax-prompt.txt
       │
       ▼
  scripts/judge_panel.py
  ├── Claude  (× N réplicas @ temp=0.3)
  ├── GPT-4o  (× N réplicas)
  └── Gemini  (× N réplicas)
       │
       ▼
       per-judge JSON (validado contra audit-output.schema.json)
       │
       ▼
  scripts/scoring.py        (final = α·det + (1-α)·llm)
       │
       ▼
  scripts/aggregation.py    (Quamoco/MAUT + Monte Carlo a category/overall)
       │
       ▼
  scripts/conformal.py      (intervalos al 90%)
       │
       ▼
       Reporte v2 (intervalos + ABSTAINED + footer transparencia)
```

**Por qué importa:**
- **Costo en tokens.** Antes el LLM recibía el código completo y reescribía findings que Semgrep ya tiene en milisegundos. Ahora el LLM recibe los findings deterministas como contexto y se enfoca en lo que requiere razonamiento.
- **Determinismo.** Los findings de Semgrep son los mismos en cada corrida. La parte LLM es la única con varianza, y esa varianza la cuantifica el conformalizer.
- **Auditoría.** Cada finding tiene `tool: 'semgrep' | 'eslint' | ...` o `tool: 'panel'` — el reviewer humano sabe qué creer ciegamente y qué cuestionar.

### Las 31 reglas Semgrep custom

`references/rules/*.yaml` — patrones React/RN que ESLint no cubre o que cubre mal:

| Categoría | Reglas |
|---|---|
| Security | `hardcoded-jwt-secret`, `dangerously-set-inner-html`, `eval-on-input`, `http-url-in-fetch`, `asyncstorage-token`, `webview-origin-wildcard`, `window-location-userinput`, `innerhtml-userinput`, `process-env-in-jsx`, `cors-allow-all`, `sql-template-literal`, `target-blank-without-noopener`, `iframe-without-sandbox`, `reject-unauthorized-false`, `string-concat-href`, `document-cookie-write`, `math-random-in-token` |
| Reliability | `setinterval-without-cleanup`, `settimeout-without-cleanup`, `key-as-index`, `random-key`, `empty-catch`, `unsafe-as-any` |
| Performance | `scrollview-with-map`, `scrollview-on-flatlist`, `inline-rn-style`, `import-moment`, `import-lodash-full` |
| Accessibility | `touchable-without-a11y`, `img-without-alt` |
| Maintainability | `console-log-in-source` |

Cada regla tiene su archivo `.tsx`/`.ts` test fixture; **todas pasan `semgrep --test`**.

---

## 4. Calibración: conformal prediction reemplaza confianza implícita

### v1

No había calibración. Si el LLM decía 7, el reporte decía 7. La "confianza" era la del usuario en el LLM.

### v2

`scripts/conformal.py` implementa **split conformal prediction**:

1. Construye un calibration set desde 4 fuentes:
   - **synthetic anchors** (60+ snippets cuyo score "ground truth" es claro por consenso obvio).
   - **mined signals** (50+ repos públicos, defect-density como proxy débil).
   - **cross-LLM medians** (sólo cuando los 3 modelos convergen).
   - *(futuro)* **telemetry corrections** opt-in.
2. Sobre la calibration set, computa el residuo `|y − ŷ|` para cada (predicted, ground_truth).
3. Toma el cuantil 1−α=0.9 de los residuos → `q`.
4. En inferencia: `intervalo = [score − q, score + q]`.

**Garantía formal** (en datos i.i.d.): la cobertura empírica del intervalo es ≥ 1−α.

**Empíricamente** sobre el corpus actual:
- Cobertura medida en held-out: **0.92–1.00** (band [0.85, 1.0]).
- `tests/results/calibration_drift_*.json` — track longitudinal.
- `.github/workflows/calibration-drift.yml` — CI gate que falla si la cobertura sale del band.

**Limitación honesta:** el calibration set es proxy, no humano. La cobertura es contra el proxy, no contra "lo que pensaría un auditor humano". Documentado en `references/corpus.md`.

### Migración

Si tu CI usaba `rax` v1 y comparaba scores con un threshold (`if rax_score < 7: fail`), en v2 debes decidir:

- **Política conservadora:** comparar contra el límite inferior del intervalo. `if interval[0] < 7: fail`.
- **Política liberal:** comparar contra la mediana. `if median < 7: fail`.
- **Política que respeta abstain:** ignorar sub-chars `ABSTAINED` antes de comparar.

---

## 5. Multi-judge panel reemplaza el juez único

### v1

```bash
claude -p < audit-prompt.txt
```

Un único modelo. Si Claude tenía un mal día, el reporte tenía un mal día.

### v2

```python
panel = run_panel(prompt, judges=["claude", "gpt4", "gemini"], replicates=5)
# Cada juez × 5 réplicas @ temp=0.3
# 15 calls totales en mode=full
```

Por sub-característica:
- `intra_judge_variance` — varianza entre las N réplicas del mismo modelo.
- `inter_judge_variance` — varianza entre las medianas de los 3 modelos.
- `confidence_class` — derivado: `high` si ambas varianzas ≤ 0.5, `low` si alguna > 1.0.

**Modos:**
- `--mode quick` (default en CI): 1 modelo, 1 réplica = 1 call.
- `--mode full` (release reviews): 3 modelos × 5 réplicas = 15 calls.

**Caché** (`.cache/judge_panel/`): SHA-256 del prompt como key, TTL 7 días. Reduce drásticamente el costo durante desarrollo.

### Migración

API keys nuevas necesarias para `--mode full`:
- `ANTHROPIC_API_KEY` (era la única en v1)
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`

Sin las dos últimas, rax cae a "single-judge" con un warning explícito en el reporte. No fallar — degrada honestamente.

---

## 6. Anti-patterns: ya no son una categoría

### v1

`APT` era una categoría top-level con peso 4. Su score era una fórmula:
`APT = 10 − count_of_severe_antipatterns × 1.5`.

### v2

Esto era doble-conteo: un god component se contaba en `ARC` Y en `APT`. v2 reasigna cada anti-pattern como **red flag dentro de la sub-característica relevante**:

```yaml
# en templates/profiles/consumer-app.yaml
red_flag_rules:
  - id: hardcoded_secret
    cap_category: security        # capa la categoría a 4
    cap_at: 4
  - id: rules_of_hooks_violation
    cap_category: reliability
    cap_at: 4
```

Un finding marcado como red flag *limita el techo* de la categoría afectada (la sub-característica no puede subir de `cap_at`), pero ya no se cuenta como una categoría aparte.

**Beneficio:** un single-finding catastrófico (e.g., `sk_live_*` hardcoded) ya no diluye su impacto a través de un peso de 4/100. Aterriza en Security, capa Security a 4, y Security pesa 0.15 en consumer-app, con sigmoid penalty para criticals.

---

## 7. Perfiles de stakeholder

Nuevo en v2: `templates/profiles/*.yaml`. Cinco preconfigurados:

| Perfil | Cuándo |
|---|---|
| `consumer-app` (default) | apps mobile/web de consumo, balanceado |
| `fintech` | apps financieras — Security 30%, Reliability 18% |
| `internal-tool` | dashboards / B2B técnicos — Maintainability 35% |
| `accessibility-critical` | gov / health / education — Interaction Capability 30% |
| `default` | alias de `consumer-app` |

Cada perfil define `weights` (por característica), `utility_overrides` (qué sub-chars son críticas y reciben sigmoid), y `red_flag_rules` (caps por categoría). Los perfiles soportan herencia vía `extends:`.

**Ejemplo de impacto medible** (de `demos/phase1_demo.py` sobre el mismo código simulado):
- `internal-tool`: 6.97
- `fintech`: 6.78
- `consumer-app`: 6.40
- `accessibility-critical`: 5.94 (penalizado por a11y débil)
- **Spread: 1.02 puntos** entre el perfil más alto y más bajo.

---

## 8. Honestidad pública (Phase 6)

### v1

README marketing-ish. "Best-in-class auditor". Sin sección "cuándo NO usar".

### v2

README reescrito (preservando el v1 en `docs/README-v1.md`):
- **What rax does AND doesn't** — explicita los límites.
- **How it differs** — tabla comparativa con ESLint, tsc, Semgrep, SonarQube, CodeClimate, marcando dónde rax pierde.
- **Known limitations** — sección dedicada con todos los caveats.
- **When NOT to use rax** — sección dedicada con casos donde otros tools son mejores.

Cada reporte v2 lleva un **footer de transparencia obligatorio**:

> Scores are 90% confidence intervals, not point estimates. Sub-chars
> tagged ABSTAINED could not be evaluated reliably (panel disagreement
> or insufficient calibration). The rax corpus does not include
> human-validated ground truth; calibration uses proxy signals —
> synthetic anchors, mined defect-density, cross-LLM consensus.
> See `references/corpus.md`.

---

## 9. Telemetría opt-in (camino al corpus humano)

`scripts/telemetry.py`:
- **Default OFF.** Sin `rax telemetry enable` no se transmite nada.
- Cuando ON, envía sólo: `audit_id`, `codebase_hash` (SHA-256 del *file list + sizes*, NO el código), scores, perfil, runtime, costo. **El código fuente nunca sale del cliente.**
- Endpoint validado (https only, RFC-1918 bloqueado por default).
- Si el usuario corrige scores manualmente con `rax telemetry correct <audit_id>`, las correcciones se envían también — esto construye el corpus humano incrementalmente.

**Path al v3:** cuando haya 1000+ correcciones humanas, el conformalizer se re-calibra contra ese corpus y deja de depender de proxies.

---

## 10. Tests + cobertura

| Métrica | v1 | v2 |
|---|---|---|
| Tests | 0 | 100 (3 skipped, gated por `@pytest.mark.expensive`) |
| Cobertura `aggregation.py` | n/a | 100% |
| Cobertura `scoring.py` | n/a | 100% |
| Property-based testing | no | sí (hypothesis sobre invariantes de scoring) |
| Self-consistency | no | `tests/test_self_consistency.py` (LLM-gated) |
| Cross-LLM | no | `scripts/cross_llm_eval.py` |

---

## Migración paso a paso para un usuario v1

```bash
# 1. Pull v2.0
git fetch origin && git checkout v2.0

# 2. Instala dependencias nuevas
pip install -r requirements.txt   # numpy, pyyaml, jsonschema, mapie, pytest

# 3. Corre el doctor
python scripts/doctor.py
# Soluciona los 'critical' que aparezcan; las warnings opcionales son OK.

# 4. Calibra el conformalizer (sólo la primera vez, o tras un `git pull` con corpus changes)
python scripts/conformal.py --calibrate

# 5. Audit en modo quick (sin API keys nuevas; cae a single-judge)
bash scripts/deterministic_layer.sh /path/to/repo
python scripts/build_prompt.py --output /tmp/rax-prompt.txt

# 6. Audit en modo full (requiere las 3 API keys)
ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GOOGLE_API_KEY=... \
  python scripts/judge_panel.py --prompt-file /tmp/rax-prompt.txt --mode full

# 7. CI: agrega el workflow de calibration drift
cp .github/workflows/calibration-drift.yml <tu-repo>/.github/workflows/
```

---

## Lo que NO cambió de v1 a v2

- La filosofía: "diff modes para reportar progreso longitudinal". v2 lo conserva.
- El layout `references/rubric.md` + `references/antipatterns.md` (v1 lives en paralelo, no se borraron).
- La política de "scoring conservador: si dudas, score más bajo".
- La política de `n/a` vs `deferred` para sub-características inaplicables.
- React/RN sigue siendo el único stack soportado.

---

## Documentos relacionados

- [CHANGELOG.md](../CHANGELOG.md) — el cambio en formato changelog.
- [references/iso25010-mapping.md](../references/iso25010-mapping.md) — mapeo bidireccional v1 ↔ ISO 25010.
- [references/rubric-v2.md](../references/rubric-v2.md) — el rubric v2 con los 41 sub-chars.
- [references/corpus.md](../references/corpus.md) — epistemología del corpus (4 layers + qué prometen y qué no).
- [references/deterministic-coverage.md](../references/deterministic-coverage.md) — α por sub-char.
- [references/report-format.md](../references/report-format.md) — formato de reporte v2.
- [docs/README-v1.md](./README-v1.md) — README v1 preservado read-only.

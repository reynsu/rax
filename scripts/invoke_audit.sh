#!/usr/bin/env bash
# invoke_audit.sh — orchestrate a rax v2 audit and hand off to Claude Code.
#
# v2 pipeline:
#   1. gather context (framework, files in scope) — gather_context.sh
#   2. run the deterministic layer (Semgrep, ESLint, tsc, madge, jscpd, npm audit)
#   3. build the audit prompt (rubric-v2 + reference-guided anchors + det findings)
#   4. invoke Claude Code with that prompt — the SKILL.md walks Claude through
#      reading the deterministic findings and producing the v2 report (with
#      90% conformal intervals, ABSTAINED rows, ISO sub-char IDs)
#   5. SKILL.md ends with `rax report save --file <path>` — state persists
#      via rax_core.py exactly as in v1
#
# When `claude` is not on PATH, prints the prompt + instructions and exits 0.
#
# Usage:
#   invoke_audit.sh [--mode MODE] [--profile NAME] [--category CAT] [--save] [--notes "text"]
#     MODE ∈ {quick, diff, focused, full}      default: diff
#     --profile NAME                           consumer-app | fintech | internal-tool | accessibility-critical
#                                              default: consumer-app
#     --save                                   promote resulting report to baseline
#     --no-deterministic                       skip the deterministic layer (fast path; LLM only)

set -euo pipefail

MODE="diff"
PROFILE="consumer-app"
CATEGORY=""
SAVE_BASELINE="no"
EXTRA_NOTES=""
SKIP_DETERMINISTIC="no"

while [ $# -gt 0 ]; do
  case "$1" in
    --mode=*)              MODE="${1#*=}"; shift ;;
    --mode)                MODE="${2:?}"; shift 2 ;;
    --profile=*)           PROFILE="${1#*=}"; shift ;;
    --profile)             PROFILE="${2:?}"; shift 2 ;;
    --category=*)          CATEGORY="${1#*=}"; shift ;;
    --category)            CATEGORY="${2:?}"; shift 2 ;;
    --save)                SAVE_BASELINE="yes"; shift ;;
    --notes=*)             EXTRA_NOTES="${1#*=}"; shift ;;
    --notes)               EXTRA_NOTES="${2:?}"; shift 2 ;;
    --no-deterministic)    SKIP_DETERMINISTIC="yes"; shift ;;
    -h|--help)
      cat <<EOF
Usage: rax audit [--mode MODE] [--profile NAME] [--category CAT] [--save] [--notes "text"]

Modes:
  quick     staged files only, fastest (~30s target)        pre-commit
  diff      compare working tree vs baseline                pre-push (default)
  focused   deep-dive on one ISO characteristic              (use --category)
  full      entire codebase + multi-judge panel              releases

Profiles (rax v2):
  consumer-app           default — balanced for consumer apps
  fintech                Security 0.30, Reliability 0.18 (no UX-domination)
  internal-tool          Maintainability 0.35, less UX
  accessibility-critical Interaction Capability 0.30, INC critical

Other:
  --save                 promote resulting report to baseline after the audit
  --no-deterministic     skip Semgrep/ESLint/tsc/madge/jscpd/npm audit
                         (faster but coverage drops to LLM-only)
  --notes "text"         extra context to pass to the auditor

Examples:
  rax audit --mode=quick
  rax audit                                       # same as --mode=diff
  rax audit --mode=focused --category=Security
  rax audit --mode=full --save                    # full audit AND promote to baseline
  rax audit --profile=fintech --mode=full
EOF
      exit 0
      ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

case "$MODE" in
  quick|diff|focused|full) ;;
  *) echo "error: invalid mode '$MODE' (use: quick|diff|focused|full)" >&2; exit 1 ;;
esac

if [ "$MODE" = "focused" ] && [ -z "$CATEGORY" ]; then
  echo "error: --mode=focused requires --category (e.g. Security, Reliability, Performance, ...)" >&2
  exit 1
fi

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  B="\033[1m"; D="\033[2m"; G="\033[32m"; Y="\033[33m"; C="\033[36m"; X="\033[0m"
else
  B=""; D=""; G=""; Y=""; C=""; X=""
fi

# Resolve skill root from this script's location.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$HERE/.." && pwd)"
TARGET="${RAX_TARGET:-$PWD}"
OUT_DIR="${RAX_OUT_DIR:-/tmp/rax-${USER:-user}}"
mkdir -p "$OUT_DIR"

# ---------------------------------------------------------------------------
# 1. Deterministic layer (skipped only on explicit --no-deterministic)
# ---------------------------------------------------------------------------
DETERMINISTIC_JSON="$OUT_DIR/rax-deterministic.json"
if [ "$SKIP_DETERMINISTIC" = "no" ]; then
  printf "${B}▶ rax/audit step 1/3${X}  ${D}deterministic layer (semgrep/eslint/tsc/madge/jscpd/npm-audit)${X}\n"
  RAX_OUT_DIR="$OUT_DIR" bash "$SKILL_ROOT/scripts/deterministic_layer.sh" "$TARGET" >&2 || true
else
  printf "${Y}▶ rax/audit step 1/3 SKIPPED${X}  ${D}(--no-deterministic)${X}\n"
  printf '{"by_iso_subcharacteristic":{},"tools_run":[],"tools_failed":[]}\n' > "$DETERMINISTIC_JSON"
fi

# ---------------------------------------------------------------------------
# 2. Build the v2 prompt (rubric + anchors + deterministic findings)
# ---------------------------------------------------------------------------
PROMPT_FILE="$OUT_DIR/rax-prompt.txt"
printf "\n${B}▶ rax/audit step 2/3${X}  ${D}building prompt with rubric-v2 + anchors + deterministic findings${X}\n"
"${RAX_PYTHON:-python3}" "$SKILL_ROOT/scripts/build_prompt.py" \
  --deterministic "$DETERMINISTIC_JSON" \
  --output "$PROMPT_FILE"
printf "${D}  prompt: $PROMPT_FILE  ($(wc -l < "$PROMPT_FILE") lines, $(wc -c < "$PROMPT_FILE") bytes)${X}\n"

# ---------------------------------------------------------------------------
# 3. Build the user-facing instruction for Claude. The skill itself does the
#    heavy work — we just trigger it and pass mode/profile/save context.
# ---------------------------------------------------------------------------
SKILL_HINT=""
case "$MODE" in
  quick)   SKILL_HINT="Run a quick rax v2 audit of my staged files." ;;
  diff)    SKILL_HINT="Run a rax v2 audit in diff mode (current working tree vs saved baseline)." ;;
  focused) SKILL_HINT="Run a rax v2 focused audit on the ${CATEGORY} characteristic." ;;
  full)    SKILL_HINT="Run a full rax v2 audit of this codebase." ;;
esac
PROFILE_HINT="Use the '${PROFILE}' profile."
DET_HINT="The deterministic layer has already run; its findings are at ${DETERMINISTIC_JSON} and are also embedded in the audit prompt."
SAVE_HINT=""
if [ "$SAVE_BASELINE" = "yes" ]; then
  SAVE_HINT="After producing the report and saving it via \`rax report save\`, promote it to baseline with \`rax baseline save\`."
fi

PROMPT="${SKILL_HINT} ${PROFILE_HINT} ${DET_HINT} Read references/rubric-v2.md and the deterministic findings JSON; produce a rax v2 report (intervals, ABSTAINED rows where panel disagreement >1.5, ISO sub-char IDs); write it to a temp file; then call \`rax report save --file <that-path>\` to persist. ${SAVE_HINT} ${EXTRA_NOTES}"

# ---------------------------------------------------------------------------
# 4. Hand off to Claude Code
# ---------------------------------------------------------------------------
printf "\n${B}▶ rax/audit step 3/3${X}  ${D}invoking Claude Code with the v2 prompt${X}\n"

if command -v claude >/dev/null 2>&1; then
  printf "${D}  mode=${MODE} profile=${PROFILE}${CATEGORY:+ category=$CATEGORY}${X}\n\n"
  exec claude -p "$PROMPT"
fi

# Fallback: print instructions
printf "\n${Y}Claude Code CLI not found on PATH.${X}\n\n"
printf "${B}Two ways to run this audit:${X}\n\n"
printf "${B}1.${X} Install Claude Code and re-run:\n"
printf "     ${C}npm install -g @anthropic-ai/claude-code${X}\n"
printf "     ${C}rax audit --mode=${MODE}${CATEGORY:+ --category=$CATEGORY} --profile=${PROFILE}${X}\n\n"
printf "${B}2.${X} Or open Claude Code and paste this prompt:\n\n"
printf -- "─────────────────────────────────────────────────────────────────\n"
printf "%s\n" "$PROMPT"
printf -- "─────────────────────────────────────────────────────────────────\n\n"
printf "${D}The skill picks up the trigger and walks through the v2 audit.${X}\n"
printf "${D}Deterministic findings are at:${X}  $DETERMINISTIC_JSON\n"
printf "${D}Full prompt is at:${X}              $PROMPT_FILE\n\n"
printf "${D}When the audit finishes, query results:${X}\n"
printf "  ${C}rax score${X}     ${D}— headline interval + median${X}\n"
printf "  ${C}rax scores${X}    ${D}— per-ISO-characteristic table${X}\n"
printf "  ${C}rax pending${X}   ${D}— open findings${X}\n"
printf "  ${C}rax delta${X}     ${D}— what changed vs baseline${X}\n"
exit 0

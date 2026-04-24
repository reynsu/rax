#!/usr/bin/env bash
# invoke_audit.sh — run a rax audit through Claude Code.
#
# If the `claude` CLI is on PATH, we invoke it non-interactively with a prompt
# that trigger-matches the skill. Otherwise we print a ready-to-paste prompt
# the user can run in an interactive Claude Code session.
#
# Usage:
#   invoke_audit.sh [--mode MODE] [--category CAT] [--save]
#     MODE ∈ {quick, diff, focused, full}    default: diff
#     --save  promote resulting report to baseline after audit completes

set -euo pipefail

MODE="diff"
CATEGORY=""
SAVE_BASELINE="no"
EXTRA_NOTES=""

while [ $# -gt 0 ]; do
  case "$1" in
    --mode=*)        MODE="${1#*=}"; shift ;;
    --mode)          MODE="${2:?}"; shift 2 ;;
    --category=*)    CATEGORY="${1#*=}"; shift ;;
    --category)      CATEGORY="${2:?}"; shift 2 ;;
    --save)          SAVE_BASELINE="yes"; shift ;;
    --notes=*)       EXTRA_NOTES="${1#*=}"; shift ;;
    --notes)         EXTRA_NOTES="${2:?}"; shift 2 ;;
    -h|--help)
      cat <<EOF
Usage: rax audit [--mode MODE] [--category CAT] [--save] [--notes "text"]

Modes:
  quick     staged files only, fastest (~30s target)        pre-commit
  diff      compare working tree vs baseline                pre-push (default)
  focused   deep-dive on one category (use --category)
  full      entire codebase                                  releases

Examples:
  rax audit --mode=quick
  rax audit                          # same as --mode=diff
  rax audit --mode=focused --category=SEC
  rax audit --mode=full --save       # full audit AND promote to baseline
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
  echo "error: --mode=focused requires --category (e.g. SEC, PRF, ARC, ...)" >&2
  exit 1
fi

# Colors
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  B="\033[1m"; D="\033[2m"; G="\033[32m"; Y="\033[33m"; C="\033[36m"; X="\033[0m"
else
  B=""; D=""; G=""; Y=""; C=""; X=""
fi

# ---------------------------------------------------------------------------
# Build the prompt that triggers the skill
# ---------------------------------------------------------------------------
SKILL_HINT=""
if [ "$MODE" = "quick" ]; then
  SKILL_HINT="Run a quick audit of my staged files using the rax skill (quick mode)."
elif [ "$MODE" = "diff" ]; then
  SKILL_HINT="Run a rax audit in diff mode (current working tree vs saved baseline)."
elif [ "$MODE" = "focused" ]; then
  SKILL_HINT="Run a rax focused audit on category ${CATEGORY}."
else
  SKILL_HINT="Run a full rax audit of this codebase."
fi

SAVE_HINT=""
if [ "$SAVE_BASELINE" = "yes" ]; then
  SAVE_HINT="After producing the report, promote it to the baseline by running \`rax baseline save\`."
fi

PROMPT="${SKILL_HINT} When finished, write the report to a temp file and call \`rax report save --file <that-path>\` so history and scoring queries work. ${SAVE_HINT} ${EXTRA_NOTES}"

# ---------------------------------------------------------------------------
# Try Claude Code CLI if available
# ---------------------------------------------------------------------------
if command -v claude >/dev/null 2>&1; then
  printf "${B}▶ running rax audit via Claude Code${X}  ${D}(mode=${MODE}${CATEGORY:+, category=$CATEGORY}${X}${D})${X}\n"
  printf "${D}  prompt: ${X}%s\n\n" "$PROMPT"
  # -p for one-shot, non-interactive. The skill in .claude/skills/rax/
  # will auto-trigger on the prompt text.
  exec claude -p "$PROMPT"
fi

# ---------------------------------------------------------------------------
# Fallback: print instructions
# ---------------------------------------------------------------------------
printf "${Y}Claude Code CLI not found on PATH.${X}\n\n"
printf "${B}Two ways to run this audit:${X}\n\n"
printf "${B}1.${X} Install Claude Code and re-run:\n"
printf "     ${C}npm install -g @anthropic-ai/claude-code${X}\n"
printf "     ${C}rax audit --mode=${MODE}${CATEGORY:+ --category=$CATEGORY}${X}\n\n"
printf "${B}2.${X} Or open Claude Code (any UI) and paste this prompt:\n\n"
printf -- "─────────────────────────────────────────────────────────────────\n"
printf "%s\n" "$PROMPT"
printf -- "─────────────────────────────────────────────────────────────────\n\n"
printf "${D}The skill will pick up the trigger and walk through the audit.${X}\n"
printf "${D}When it finishes, you can query results:${X}\n"
printf "  ${C}rax score${X}     ${D}— headline number${X}\n"
printf "  ${C}rax scores${X}    ${D}— per-category table${X}\n"
printf "  ${C}rax pending${X}   ${D}— open findings${X}\n"
printf "  ${C}rax delta${X}     ${D}— what changed vs baseline${X}\n"
exit 0

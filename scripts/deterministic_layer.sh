#!/usr/bin/env bash
# scripts/deterministic_layer.sh — Phase 2 deterministic orchestrator.
#
# Runs available static-analysis tools in parallel and aggregates their
# findings to $OUT_DIR/rax-deterministic.json grouped by ISO 25010
# sub-characteristic. Missing or failing tools are recorded in
# `tools_failed` and never abort the run.
#
# Usage:
#   bash scripts/deterministic_layer.sh [target_dir]
#
# Env vars:
#   RAX_OUT_DIR     directory for tool outputs (default: /tmp)
#   RAX_TIMEOUT     per-tool timeout in seconds (default: 120)
#
# Exit codes:
#   0  — orchestrator finished (regardless of individual tool results)
#   2  — argument error (target not a directory)

set -uo pipefail

TARGET="${1:-$PWD}"
TARGET="$(cd "$TARGET" 2>/dev/null && pwd || echo "$TARGET")"

if [[ ! -d "$TARGET" ]]; then
    echo "rax/deterministic: target not a directory: $TARGET" >&2
    exit 2
fi

# Resolve repo root (for custom semgrep rules + python parser)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAX_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OUT_DIR="${RAX_OUT_DIR:-/tmp}"
TIMEOUT="${RAX_TIMEOUT:-120}"
SEMGREP_OUT="$OUT_DIR/rax-semgrep.json"
ESLINT_OUT="$OUT_DIR/rax-eslint.json"
TSC_OUT="$OUT_DIR/rax-tsc.txt"
MADGE_OUT="$OUT_DIR/rax-madge.json"
JSCPD_OUT="$OUT_DIR/rax-jscpd"
AUDIT_OUT="$OUT_DIR/rax-audit.json"
DETERMINISTIC_OUT="$OUT_DIR/rax-deterministic.json"

mkdir -p "$OUT_DIR"
rm -f "$SEMGREP_OUT" "$ESLINT_OUT" "$TSC_OUT" "$MADGE_OUT" "$AUDIT_OUT" "$DETERMINISTIC_OUT"
rm -rf "$JSCPD_OUT"
mkdir -p "$JSCPD_OUT"

TOOLS_RUN_FILE="$(mktemp)"
TOOLS_FAILED_FILE="$(mktemp)"
trap 'rm -f "$TOOLS_RUN_FILE" "$TOOLS_FAILED_FILE"' EXIT

mark_run() { printf '%s\n' "$1" >> "$TOOLS_RUN_FILE"; }
mark_failed() { printf '%s\t%s\n' "$1" "$2" >> "$TOOLS_FAILED_FILE"; }

# Resolve a timeout binary if available (BSD `timeout` is not on macOS by default).
TIMEOUT_BIN=""
if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_BIN="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_BIN="gtimeout"
fi

with_timeout() {
    if [[ -n "$TIMEOUT_BIN" ]]; then
        "$TIMEOUT_BIN" "$TIMEOUT" "$@"
    else
        "$@"
    fi
}

# ----- tool runners -----

run_semgrep() {
    if ! command -v semgrep >/dev/null 2>&1; then
        mark_failed semgrep not_installed
        return 0
    fi
    local rules_arg=()
    [[ -d "$RAX_ROOT/references/rules" ]] && rules_arg+=("--config=$RAX_ROOT/references/rules")
    if with_timeout semgrep --config=p/javascript --config=p/react "${rules_arg[@]}" \
        --json --output="$SEMGREP_OUT" --quiet --metrics=off "$TARGET" >/dev/null 2>&1 \
        || [[ -s "$SEMGREP_OUT" ]]; then
        mark_run semgrep
    else
        mark_failed semgrep "exit_$?"
    fi
}

run_eslint() {
    if ! command -v eslint >/dev/null 2>&1 && ! [[ -x "$TARGET/node_modules/.bin/eslint" ]]; then
        mark_failed eslint not_installed
        return 0
    fi
    local bin="eslint"
    [[ -x "$TARGET/node_modules/.bin/eslint" ]] && bin="$TARGET/node_modules/.bin/eslint"
    if with_timeout "$bin" "$TARGET" --ext .ts,.tsx,.js,.jsx --format=json \
            -o "$ESLINT_OUT" >/dev/null 2>&1 \
        || [[ -s "$ESLINT_OUT" ]]; then
        mark_run eslint
    else
        mark_failed eslint "exit_$?"
    fi
}

run_tsc() {
    local bin=""
    if command -v tsc >/dev/null 2>&1; then bin="tsc"; fi
    [[ -x "$TARGET/node_modules/.bin/tsc" ]] && bin="$TARGET/node_modules/.bin/tsc"
    if [[ -z "$bin" ]]; then
        mark_failed tsc not_installed
        return 0
    fi
    if [[ ! -f "$TARGET/tsconfig.json" ]]; then
        mark_failed tsc no_tsconfig
        return 0
    fi
    ( cd "$TARGET" && with_timeout "$bin" --noEmit --pretty false ) > "$TSC_OUT" 2>&1 || true
    mark_run tsc
}

run_madge() {
    local bin=""
    if command -v madge >/dev/null 2>&1; then bin="madge"; fi
    [[ -x "$TARGET/node_modules/.bin/madge" ]] && bin="$TARGET/node_modules/.bin/madge"
    if [[ -z "$bin" ]]; then
        mark_failed madge not_installed
        return 0
    fi
    local src_dir="$TARGET/src"
    [[ ! -d "$src_dir" ]] && src_dir="$TARGET"
    if with_timeout "$bin" --circular --json "$src_dir" > "$MADGE_OUT" 2>/dev/null \
        || [[ -s "$MADGE_OUT" ]]; then
        mark_run madge
    else
        mark_failed madge "exit_$?"
    fi
}

run_jscpd() {
    local bin=""
    if command -v jscpd >/dev/null 2>&1; then bin="jscpd"; fi
    [[ -x "$TARGET/node_modules/.bin/jscpd" ]] && bin="$TARGET/node_modules/.bin/jscpd"
    if [[ -z "$bin" ]]; then
        mark_failed jscpd not_installed
        return 0
    fi
    if with_timeout "$bin" --reporters=json --output "$JSCPD_OUT" --silent "$TARGET" \
        >/dev/null 2>&1 || [[ -s "$JSCPD_OUT/jscpd-report.json" ]]; then
        mark_run jscpd
    else
        mark_failed jscpd "exit_$?"
    fi
}

run_audit() {
    if ! command -v npm >/dev/null 2>&1; then
        mark_failed npm_audit not_installed
        return 0
    fi
    if [[ ! -f "$TARGET/package-lock.json" && ! -f "$TARGET/npm-shrinkwrap.json" ]]; then
        mark_failed npm_audit no_lockfile
        return 0
    fi
    ( cd "$TARGET" && with_timeout npm audit --json ) > "$AUDIT_OUT" 2>/dev/null || true
    if [[ -s "$AUDIT_OUT" ]]; then
        mark_run npm_audit
    else
        mark_failed npm_audit "no_output"
    fi
}

# ----- launch in parallel -----

echo "rax/deterministic: target=$TARGET out=$OUT_DIR" >&2

run_semgrep & PID_SEMGREP=$!
run_eslint  & PID_ESLINT=$!
run_tsc     & PID_TSC=$!
run_madge   & PID_MADGE=$!
run_jscpd   & PID_JSCPD=$!
run_audit   & PID_AUDIT=$!

wait "$PID_SEMGREP" "$PID_ESLINT" "$PID_TSC" "$PID_MADGE" "$PID_JSCPD" "$PID_AUDIT" 2>/dev/null || true

TOOLS_RUN=$(sort -u "$TOOLS_RUN_FILE" 2>/dev/null | tr '\n' ',' | sed 's/,$//' || true)
TOOLS_FAILED=$(sort -u "$TOOLS_FAILED_FILE" 2>/dev/null | tr '\n' '|' | sed 's/|$//' || true)

# ----- aggregate -----

PYTHON="${PYTHON:-python3}"
"$PYTHON" "$SCRIPT_DIR/parse_deterministic.py" \
    --semgrep "$SEMGREP_OUT" \
    --eslint  "$ESLINT_OUT" \
    --tsc     "$TSC_OUT" \
    --madge   "$MADGE_OUT" \
    --jscpd   "$JSCPD_OUT/jscpd-report.json" \
    --audit   "$AUDIT_OUT" \
    --tools-run    "$TOOLS_RUN" \
    --tools-failed "$TOOLS_FAILED" \
    --output  "$DETERMINISTIC_OUT"

PARSE_RC=$?

if [[ $PARSE_RC -ne 0 ]]; then
    echo "rax/deterministic: aggregation failed (rc=$PARSE_RC)" >&2
    exit 0
fi

# ----- summary -----

echo
echo "==== rax/deterministic summary ===="
echo "tools_run:    $TOOLS_RUN"
echo "tools_failed: $TOOLS_FAILED"
"$PYTHON" -c "
import json, sys
d = json.load(open('$DETERMINISTIC_OUT'))
subs = d['by_iso_subcharacteristic']
total_findings = sum(len(v['findings']) for v in subs.values())
print(f'sub-characteristics indexed: {len(subs)}')
print(f'total findings:              {total_findings}')
ranked = sorted(subs.items(), key=lambda kv: kv[1]['deterministic_score'])
print('lowest scoring (top 5):')
for k, v in ranked[:5]:
    print(f'  {k}: {v[\"deterministic_score\"]:.2f}  ({len(v[\"findings\"])} findings, conf={v[\"confidence\"]})')
"
echo "==================================="
echo "output: $DETERMINISTIC_OUT"

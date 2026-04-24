#!/usr/bin/env bash
# rax · gather_context.sh
#
# Collects context for an audit run. Prints a JSON blob to stdout that the
# skill reads before any file access. Exit codes: 0 ok, 2 not a repo, 3 no
# package.json, 4 unsupported mode.
#
# Usage: bash scripts/gather_context.sh <mode>
#   mode: quick | diff | focused | full

set -euo pipefail

MODE="${1:-quick}"
case "$MODE" in
  quick|diff|focused|full) ;;
  *) echo '{"error":"unsupported mode"}' >&2; exit 4 ;;
esac

# --- Repo root --------------------------------------------------------------
if ! ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  echo '{"error":"not a git repository"}' >&2
  exit 2
fi
cd "$ROOT"

# --- package.json -----------------------------------------------------------
if [[ ! -f package.json ]]; then
  echo '{"error":"no package.json at repo root"}' >&2
  exit 3
fi

# Prefer jq when available; fall back to node.
have_jq() { command -v jq >/dev/null 2>&1; }
read_pkg() {
  local key="$1"
  if have_jq; then
    jq -r "$key // empty" package.json 2>/dev/null || true
  else
    node -e "
      try {
        const p = require('$ROOT/package.json');
        const v = eval('p.$(echo "$key" | sed 's/^\.//')');
        process.stdout.write(v == null ? '' : (typeof v === 'object' ? JSON.stringify(v) : String(v)));
      } catch (e) { process.stdout.write(''); }
    " 2>/dev/null || true
  fi
}

PKG_NAME="$(read_pkg '.name')"
PKG_VERSION="$(read_pkg '.version')"
DEPS_JSON="$(read_pkg '.dependencies')"
DEV_DEPS_JSON="$(read_pkg '.devDependencies')"

has_dep() {
  local dep="$1"
  [[ "$DEPS_JSON" == *"\"$dep\""* ]] || [[ "$DEV_DEPS_JSON" == *"\"$dep\""* ]]
}

# --- Framework detection ----------------------------------------------------
FRAMEWORK="unknown"
if has_dep "next"; then
  FRAMEWORK="next"
elif has_dep "@remix-run/react" || has_dep "@remix-run/node"; then
  FRAMEWORK="remix"
elif has_dep "expo"; then
  FRAMEWORK="expo"
elif has_dep "react-native"; then
  FRAMEWORK="react-native"
elif has_dep "vite" && has_dep "react"; then
  FRAMEWORK="react-vite"
elif has_dep "react-scripts"; then
  FRAMEWORK="cra"
elif has_dep "react"; then
  FRAMEWORK="react"
fi

# --- TypeScript -------------------------------------------------------------
TS="false"
if [[ -f tsconfig.json ]] || has_dep "typescript"; then
  TS="true"
fi

# --- Styling ---------------------------------------------------------------
STYLING="unknown"
if has_dep "tailwindcss"; then STYLING="tailwind";
elif has_dep "styled-components"; then STYLING="styled-components";
elif has_dep "@emotion/react" || has_dep "@emotion/styled"; then STYLING="emotion";
elif has_dep "nativewind"; then STYLING="nativewind";
elif has_dep "@stylexjs/stylex"; then STYLING="stylex";
elif find . -maxdepth 4 -name "*.module.css" -not -path "*/node_modules/*" 2>/dev/null | head -1 | grep -q .; then
  STYLING="css-modules";
fi

# --- State management ------------------------------------------------------
STATE="unknown"
STATE_LIBS=()
has_dep "@reduxjs/toolkit" && STATE_LIBS+=("rtk")
has_dep "redux" && ! has_dep "@reduxjs/toolkit" && STATE_LIBS+=("redux-classic")
has_dep "zustand" && STATE_LIBS+=("zustand")
has_dep "jotai" && STATE_LIBS+=("jotai")
has_dep "valtio" && STATE_LIBS+=("valtio")
has_dep "mobx" && STATE_LIBS+=("mobx")
has_dep "recoil" && STATE_LIBS+=("recoil")
if [[ ${#STATE_LIBS[@]} -gt 0 ]]; then
  STATE="$(IFS=,; echo "${STATE_LIBS[*]}")"
fi

# --- Server state ---------------------------------------------------------
SERVER_STATE="none"
SS_LIBS=()
has_dep "@tanstack/react-query" && SS_LIBS+=("react-query")
has_dep "swr" && SS_LIBS+=("swr")
has_dep "@apollo/client" && SS_LIBS+=("apollo")
has_dep "urql" && SS_LIBS+=("urql")
if [[ ${#SS_LIBS[@]} -gt 0 ]]; then
  SERVER_STATE="$(IFS=,; echo "${SS_LIBS[*]}")"
fi

# --- Testing stack ---------------------------------------------------------
TESTING="none"
TEST_LIBS=()
has_dep "vitest" && TEST_LIBS+=("vitest")
has_dep "jest" && TEST_LIBS+=("jest")
has_dep "@testing-library/react" && TEST_LIBS+=("rtl")
has_dep "@testing-library/react-native" && TEST_LIBS+=("rntl")
has_dep "playwright" && TEST_LIBS+=("playwright")
has_dep "cypress" && TEST_LIBS+=("cypress")
has_dep "detox" && TEST_LIBS+=("detox")
has_dep "@storybook/react" && TEST_LIBS+=("storybook")
if [[ ${#TEST_LIBS[@]} -gt 0 ]]; then
  TESTING="$(IFS=,; echo "${TEST_LIBS[*]}")"
fi

# --- Source root -----------------------------------------------------------
SRC_ROOT="src"
for candidate in src app lib packages; do
  if [[ -d "$candidate" ]]; then SRC_ROOT="$candidate"; break; fi
done

# --- Exclusions (glob list for ripgrep / find) -----------------------------
EXCLUDES=(
  "node_modules"
  "ios/Pods"
  "android/build"
  "android/.gradle"
  "android/app/build"
  "dist"
  "build"
  ".next"
  ".expo"
  ".expo-shared"
  ".turbo"
  "coverage"
  ".cache"
  ".parcel-cache"
  "web-build"
  ".vercel"
  "out"
  "storybook-static"
)

# --- Git context ----------------------------------------------------------
BRANCH="$(git branch --show-current 2>/dev/null || echo 'detached')"
SHORT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo 'none')"
CLEAN_TREE="true"
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  CLEAN_TREE="false"
fi

# --- Files in scope -------------------------------------------------------
# We write to a temp file because the list can get large.
FILES_TMP="$(mktemp)"
trap 'rm -f "$FILES_TMP"' EXIT

list_source_files() {
  # All tracked source files under src root, respecting excludes.
  # Filters to React-relevant extensions.
  git ls-files -- "$SRC_ROOT" 2>/dev/null \
    | grep -E '\.(tsx?|jsx?|mjs|cjs)$' \
    | grep -v -E '\.(test|spec|stories|d)\.(tsx?|jsx?)$' \
    || true
}

list_staged_files() {
  git diff --cached --name-only --diff-filter=ACM 2>/dev/null \
    | grep -E '\.(tsx?|jsx?|mjs|cjs)$' \
    | grep -v -E '\.(d)\.ts$' \
    || true
}

list_diff_vs_baseline() {
  local baseline_file=".claude/rax/baseline.json"
  if [[ -f "$baseline_file" ]]; then
    local baseline_sha
    baseline_sha="$(read_pkg_from_json "$baseline_file" '.commit_sha')"
    if [[ -n "$baseline_sha" ]] && git rev-parse --verify "$baseline_sha" >/dev/null 2>&1; then
      git diff --name-only "$baseline_sha"..HEAD 2>/dev/null \
        | grep -E '\.(tsx?|jsx?|mjs|cjs)$' \
        | grep -v -E '\.(d)\.ts$' \
        || true
      return
    fi
  fi
  # Fallback: files changed in last 10 commits.
  git diff --name-only "HEAD~10..HEAD" 2>/dev/null \
    | grep -E '\.(tsx?|jsx?|mjs|cjs)$' \
    | grep -v -E '\.(d)\.ts$' \
    || true
}

read_pkg_from_json() {
  local file="$1"
  local key="$2"
  if have_jq; then
    jq -r "$key // empty" "$file" 2>/dev/null || true
  else
    node -e "
      try { const p = require('$ROOT/$file'); const v = eval('p.$(echo "$key" | sed 's/^\.//')'); process.stdout.write(v == null ? '' : String(v)); } catch(e) {}
    " 2>/dev/null || true
  fi
}

case "$MODE" in
  quick)
    list_staged_files > "$FILES_TMP"
    if [[ ! -s "$FILES_TMP" ]]; then
      # No staged files — fall back to recently modified working tree files.
      git diff --name-only --diff-filter=ACM 2>/dev/null \
        | grep -E '\.(tsx?|jsx?|mjs|cjs)$' \
        | grep -v -E '\.(d)\.ts$' \
        > "$FILES_TMP" || true
    fi
    ;;
  diff)
    list_diff_vs_baseline > "$FILES_TMP"
    ;;
  focused|full)
    list_source_files > "$FILES_TMP"
    ;;
esac

FILE_COUNT="$(wc -l < "$FILES_TMP" | tr -d ' ')"

# Hard cap on quick mode — SKILL.md says 20.
TRUNCATED="false"
if [[ "$MODE" == "quick" && "$FILE_COUNT" -gt 20 ]]; then
  # Sort by line count descending, keep top 20
  awk -v cap=20 '
    BEGIN { count = 0 }
    {
      cmd = "wc -l < \"" $0 "\" 2>/dev/null"
      cmd | getline lines
      close(cmd)
      files[NR] = $0
      sizes[NR] = lines + 0
      total = NR
    }
    END {
      # Sort indices by size descending (simple O(n^2) — fine for <1000)
      for (i = 1; i <= total; i++) idx[i] = i
      for (i = 1; i <= total; i++) {
        for (j = i+1; j <= total; j++) {
          if (sizes[idx[i]] < sizes[idx[j]]) {
            tmp = idx[i]; idx[i] = idx[j]; idx[j] = tmp
          }
        }
      }
      for (i = 1; i <= total && i <= cap; i++) print files[idx[i]]
    }
  ' "$FILES_TMP" > "${FILES_TMP}.capped"
  mv "${FILES_TMP}.capped" "$FILES_TMP"
  TRUNCATED="true"
  FILE_COUNT="20"
fi

# --- Config overrides -----------------------------------------------------
CONFIG_EXISTS="false"
if [[ -f ".claude/rax/config.json" ]]; then
  CONFIG_EXISTS="true"
fi

# --- Baseline presence ----------------------------------------------------
BASELINE_EXISTS="false"
BASELINE_SHA=""
BASELINE_DATE=""
if [[ -f ".claude/rax/baseline.json" ]]; then
  BASELINE_EXISTS="true"
  BASELINE_SHA="$(read_pkg_from_json .claude/rax/baseline.json .commit_sha)"
  BASELINE_DATE="$(read_pkg_from_json .claude/rax/baseline.json .timestamp)"
fi

# --- Emit JSON ------------------------------------------------------------
# Build file list JSON
FILES_JSON="["
first="true"
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  if [[ "$first" == "true" ]]; then first="false"; else FILES_JSON+=","; fi
  # JSON-escape the path
  esc="${f//\\/\\\\}"
  esc="${esc//\"/\\\"}"
  FILES_JSON+="\"$esc\""
done < "$FILES_TMP"
FILES_JSON+="]"

cat <<EOF
{
  "mode": "$MODE",
  "root": "$ROOT",
  "project": {
    "name": "$PKG_NAME",
    "version": "$PKG_VERSION",
    "framework": "$FRAMEWORK",
    "typescript": $TS,
    "src_root": "$SRC_ROOT",
    "styling": "$STYLING",
    "state": "$STATE",
    "server_state": "$SERVER_STATE",
    "testing": "$TESTING"
  },
  "git": {
    "branch": "$BRANCH",
    "short_sha": "$SHORT_SHA",
    "clean_tree": $CLEAN_TREE
  },
  "scope": {
    "file_count": $FILE_COUNT,
    "truncated": $TRUNCATED,
    "files": $FILES_JSON,
    "excluded_dirs": [$(printf '"%s",' "${EXCLUDES[@]}" | sed 's/,$//')]
  },
  "config_override": $CONFIG_EXISTS,
  "baseline": {
    "exists": $BASELINE_EXISTS,
    "sha": "$BASELINE_SHA",
    "date": "$BASELINE_DATE"
  }
}
EOF

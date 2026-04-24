#!/usr/bin/env bash
# install.sh — put `rax` on PATH.
#
# Strategy: symlink bin/rax into the first writable dir on PATH that's
# conventional for user binaries. We try, in order:
#   1. $RAX_INSTALL_DIR  (if the user set it)
#   2. ~/.local/bin      (create if missing; used by pipx, cargo install etc.)
#   3. ~/bin             (only if exists)
#   4. /usr/local/bin    (needs sudo; only if user opts in)
#
# Idempotent: re-running replaces the symlink cleanly.
#
# Uninstall: rm "$(command -v rax)"

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/bin/rax"
[ -x "$SRC" ] || { echo "error: $SRC not found or not executable" >&2; exit 1; }

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  B="\033[1m"; D="\033[2m"; G="\033[32m"; Y="\033[33m"; X="\033[0m"
else
  B=""; D=""; G=""; Y=""; X=""
fi

info() { printf "${B}%s${X} %s\n" "→" "$*"; }
ok()   { printf "${G}✓${X} %s\n" "$*"; }
warn() { printf "${Y}!${X} %s\n" "$*"; }

# ---------------------------------------------------------------------------
# Pick target dir
# ---------------------------------------------------------------------------
TARGET_DIR=""

if [ -n "${RAX_INSTALL_DIR:-}" ]; then
  TARGET_DIR="$RAX_INSTALL_DIR"
  mkdir -p "$TARGET_DIR"
elif [ -w "$HOME/.local/bin" ] 2>/dev/null || mkdir -p "$HOME/.local/bin" 2>/dev/null; then
  TARGET_DIR="$HOME/.local/bin"
elif [ -d "$HOME/bin" ] && [ -w "$HOME/bin" ]; then
  TARGET_DIR="$HOME/bin"
else
  warn "couldn't pick a user-level bin dir; falling back to /usr/local/bin (sudo)"
  TARGET_DIR="/usr/local/bin"
fi

info "installing to ${TARGET_DIR}"

TARGET="$TARGET_DIR/rax"

# ---------------------------------------------------------------------------
# Install (symlink, fall back to copy if the FS doesn't support symlinks)
# ---------------------------------------------------------------------------
if [ -L "$TARGET" ] || [ -f "$TARGET" ]; then
  info "replacing existing ${TARGET}"
  if [ "$TARGET_DIR" = "/usr/local/bin" ]; then sudo rm -f "$TARGET"; else rm -f "$TARGET"; fi
fi

if [ "$TARGET_DIR" = "/usr/local/bin" ]; then
  sudo ln -s "$SRC" "$TARGET" 2>/dev/null || sudo cp "$SRC" "$TARGET"
else
  ln -s "$SRC" "$TARGET" 2>/dev/null || cp "$SRC" "$TARGET"
fi
chmod +x "$TARGET" 2>/dev/null || true

ok "installed: ${TARGET} → ${SRC}"

# ---------------------------------------------------------------------------
# Sanity-check PATH
# ---------------------------------------------------------------------------
case ":$PATH:" in
  *":$TARGET_DIR:"*) ;;
  *)
    warn "${TARGET_DIR} is not on your PATH."
    echo ""
    echo "Add one of these to your shell rc (.bashrc, .zshrc, .config/fish/config.fish):"
    echo ""
    printf "  bash/zsh:  ${D}export PATH=\"%s:\$PATH\"${X}\n" "$TARGET_DIR"
    printf "  fish:      ${D}fish_add_path %s${X}\n" "$TARGET_DIR"
    echo ""
    ;;
esac

# ---------------------------------------------------------------------------
# Python sanity check
# ---------------------------------------------------------------------------
if ! command -v "${RAX_PYTHON:-python3}" >/dev/null 2>&1; then
  warn "python3 not found. rax needs Python 3.8+ on PATH (or set RAX_PYTHON)."
fi

# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
if command -v rax >/dev/null 2>&1; then
  info "verifying install…"
  rax version || true
else
  warn "rax not found on PATH yet — open a new shell, or export PATH as shown."
fi

echo ""
ok "done. try:  ${B}rax help${X}"

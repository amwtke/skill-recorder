#!/usr/bin/env bash
# claude-rec install script
# Sets up runtime dependencies on macOS or Debian/Ubuntu Linux,
# then symlinks claude-rec and compress-spinner.py into ~/.local/bin
# so they're on $PATH globally. Idempotent — re-running is safe.
#
# Usage: install.sh [--no-link]
#   --no-link    Skip the ~/.local/bin symlink step (deps only)

set -euo pipefail

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
LINK_DIR="$HOME/.local/bin"
NO_LINK=0

need() { command -v "$1" >/dev/null 2>&1; }
say()  { printf '\033[1m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; }

show_help() {
  cat <<EOF
Usage: install.sh [OPTIONS]

Sets up dependencies for claude-rec and (by default) symlinks the
binaries into ~/.local/bin so they're available globally on \$PATH.

Options:
      --no-link    Skip the symlink step; only install dependencies
  -h, --help       Show this help
EOF
}

setup_macos() {
  if ! need brew; then
    err "Homebrew not found. Install from https://brew.sh, then re-run."
    exit 1
  fi

  for pkg in asciinema agg ffmpeg python3; do
    if need "$pkg"; then
      say "✓ $pkg already present"
    else
      say "installing $pkg via brew..."
      brew install "$pkg"
    fi
  done
}

setup_linux() {
  if ! need apt; then
    err "apt not found. This script supports Debian/Ubuntu only."
    exit 1
  fi

  say "updating apt index..."
  sudo apt update -qq

  for pkg in asciinema ffmpeg python3; do
    if need "$pkg"; then
      say "✓ $pkg already present"
    else
      say "installing $pkg via apt..."
      sudo apt install -y "$pkg"
    fi
  done

  if need agg; then
    say "✓ agg already present"
    return
  fi

  if ! need cargo; then
    say "cargo not found; trying apt..."
    if ! sudo apt install -y cargo 2>/dev/null; then
      err "could not install cargo via apt. Install Rust from https://rustup.rs/, then re-run."
      exit 1
    fi
  fi

  say "installing agg via cargo (this can take a few minutes)..."
  cargo install --git https://github.com/asciinema/agg

  if ! need agg; then
    warn "agg installed but not on PATH. Add this to your shell profile:"
    warn '    export PATH="$HOME/.cargo/bin:$PATH"'
    exit 1
  fi
}

link_binaries() {
  say "linking binaries to $LINK_DIR..."
  mkdir -p "$LINK_DIR"

  for file in claude-rec compress-spinner.py; do
    local src="$SCRIPT_DIR/$file"
    local dst="$LINK_DIR/$file"
    if [[ ! -f "$src" ]]; then
      err "source file missing: $src"
      exit 1
    fi
    ln -sf "$src" "$dst"
    printf '  \033[32m→\033[0m %s -> %s\n' "$dst" "$src"
  done

  case ":${PATH:-}:" in
    *":$LINK_DIR:"*)
      say "✓ $LINK_DIR is on \$PATH"
      ;;
    *)
      warn "$LINK_DIR is NOT on \$PATH. Add this to your shell profile (~/.zshrc or ~/.bashrc):"
      warn '    export PATH="$HOME/.local/bin:$PATH"'
      warn "After sourcing it, you can run 'claude-rec' from anywhere."
      ;;
  esac
}

verify() {
  say "verifying..."
  local missing=()
  for tool in asciinema agg ffmpeg python3; do
    if need "$tool"; then
      printf '  \033[32m✓\033[0m %-12s %s\n' "$tool" "$(command -v "$tool")"
    else
      printf '  \033[31m✗\033[0m %-12s MISSING\n' "$tool"
      missing+=("$tool")
    fi
  done

  if need claude; then
    printf '  \033[32m✓\033[0m %-12s %s\n' "claude" "$(command -v claude)"
  else
    printf '  \033[33m○\033[0m %-12s not installed (Claude Code CLI is a separate install)\n' "claude"
    say "see https://docs.claude.com/en/docs/claude-code"
  fi

  if [[ ${#missing[@]} -gt 0 ]]; then
    err "missing after install: ${missing[*]}"
    exit 1
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-link) NO_LINK=1; shift ;;
      -h|--help) show_help; exit 0 ;;
      *) err "unknown option: $1"; show_help >&2; exit 2 ;;
    esac
  done
}

main() {
  parse_args "$@"

  local os
  os="$(uname -s)"
  say "OS: $os"

  case "$os" in
    Darwin) setup_macos ;;
    Linux)  setup_linux ;;
    *)      err "unsupported OS: $os"; exit 1 ;;
  esac

  verify

  if [[ $NO_LINK -eq 0 ]]; then
    echo
    link_binaries
  fi

  echo
  if [[ $NO_LINK -eq 0 ]]; then
    say "All set! Try: claude-rec --help  (or ./bin/claude-rec --help if PATH not configured)"
  else
    say "All set! Deps installed. Run: ./bin/claude-rec --help"
  fi
}

main "$@"

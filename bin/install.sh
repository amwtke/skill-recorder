#!/usr/bin/env bash
# claude-rec install script
# Sets up runtime dependencies on macOS or Debian/Ubuntu Linux.
# Idempotent — re-running is safe.

set -euo pipefail

need() { command -v "$1" >/dev/null 2>&1; }
say()  { printf '\033[1m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; }

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

main() {
  local os
  os="$(uname -s)"
  say "OS: $os"

  case "$os" in
    Darwin) setup_macos ;;
    Linux)  setup_linux ;;
    *)      err "unsupported OS: $os"; exit 1 ;;
  esac

  verify
  echo
  say "All set! Try: ./bin/claude-rec --help"
}

main "$@"

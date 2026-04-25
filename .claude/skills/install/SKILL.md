---
name: install
description: Set up runtime dependencies (asciinema, agg, ffmpeg, python3) for claude-rec on a bare macOS or Ubuntu Linux machine. Use when the user wants to install or verify the environment from scratch, or fix a missing-dependency error from claude-rec.
---

# Install claude-rec runtime

Set up everything `claude-rec` needs to run: `asciinema`, `agg`, `ffmpeg`, `python3`. Plus a sanity check for the `claude` CLI itself.

## Steps

1. Run the installer:

   ```bash
   ./bin/install.sh
   ```

   The script is idempotent — re-running is safe. It detects OS (macOS or Debian/Ubuntu) and uses `brew` or `apt` accordingly.

2. Watch the output. The script will:
   - Report which deps are already present (skips reinstalling)
   - Install missing ones (will prompt for `sudo` on Linux)
   - Verify everything at the end

3. If the script exits with an error, follow the message:
   - **macOS, "Homebrew not found":** install from https://brew.sh, then re-run.
   - **Ubuntu, "could not install cargo":** install Rust from https://rustup.rs/, source `~/.cargo/env`, then re-run.
   - **"agg installed but not on PATH":** add `export PATH="$HOME/.cargo/bin:$PATH"` to the user's shell profile (`~/.zshrc` or `~/.bashrc`), source it, then re-run to verify.

4. After install completes, smoke-test:

   ```bash
   ./bin/claude-rec --help
   ```

   If the help text prints, the environment is ready.

## Notes for the model

- **Don't bypass `sudo` prompts**: on Linux, `apt install` will prompt for the user's password. That's expected — let it through.
- **`claude` CLI is out of scope**: this skill installs deps for `claude-rec`, not Claude Code itself. The script only warns if `claude` is missing; it does not install it. If the user needs Claude Code, point them at https://docs.claude.com/en/docs/claude-code.
- **Bare-machine vs. partial-machine**: if some deps are present and others aren't, the script handles both cases. Don't pre-flight-check yourself; just run the script.
- **What the deps are for** (for explaining to the user if asked):
  - `asciinema` — records terminal session as `.cast`
  - `agg` — converts `.cast` → `.gif`
  - `ffmpeg` — converts `.gif` → `.mp4`
  - `python3` — runs `bin/compress-spinner.py` (cast pre-processor for animated progress indicators)

## What gets installed

| Tool | macOS | Ubuntu |
|---|---|---|
| asciinema | `brew install asciinema` | `sudo apt install asciinema` |
| agg | `brew install agg` | `cargo install --git https://github.com/asciinema/agg` (no apt package) |
| ffmpeg | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| python3 | `brew install python3` (usually present) | `sudo apt install python3` (usually present) |

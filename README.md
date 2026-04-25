# claude-rec

Record [Claude Code](https://docs.claude.com/en/docs/claude-code) sessions as `.cast` / `.gif` / `.mp4`. Idle gaps are auto-compressed using asciinema; animated progress spinners ("Envisioning…", npm/docker bars, …) are collapsed to a 0.5s flash via cast pre-processing.

## Quick start (bare machine)

```bash
git clone git@github.com:amwtke/skill-recorder.git
cd skill-recorder
./bin/install.sh        # installs asciinema, agg, ffmpeg, python3
./bin/claude-rec        # record a session
```

Inside Claude Code, after cloning, you can also use the project-local skill:

```bash
cd skill-recorder
claude                  # launch Claude Code in this repo
/install                # invokes .claude/skills/install
```

## Install

### Option A — one-command (recommended)

```
./bin/install.sh
```

Auto-detects macOS or Debian/Ubuntu and installs everything below. Idempotent — already-installed deps are skipped.

### Option B — `/install` skill (when inside Claude Code)

The repo ships with a project-local skill at `.claude/skills/install`. Inside a Claude Code session opened in this repo, just type:

```
/install
```

The model runs `bin/install.sh` and walks through any prompts (e.g. `sudo` on Linux).

### What it installs

| Tool | macOS | Ubuntu Linux |
|---|---|---|
| asciinema | `brew install asciinema` | `sudo apt install asciinema` |
| agg | `brew install agg` | `cargo install --git https://github.com/asciinema/agg` (no apt package) |
| ffmpeg | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| python3 | `brew install python3` | `sudo apt install python3` |

Ubuntu has no official `agg` package, so a Rust toolchain (`cargo`) is required. The installer tries `apt install cargo` first; if that fails, install Rust from https://rustup.rs/ and re-run.

The `claude` CLI itself is not installed by this script — install Claude Code separately from https://docs.claude.com/en/docs/claude-code.

### Global `claude-rec` command

By default, `install.sh` symlinks `claude-rec` and `compress-spinner.py` into `~/.local/bin/`. After install:

```bash
claude-rec --help        # callable from anywhere
```

If `~/.local/bin` isn't on your `$PATH`, the script prints a one-line snippet to add to your shell profile.

The symlinks point back into the repo, so `git pull` updates `claude-rec` instantly without re-installing.

To skip the symlink step (deps only):

```bash
./bin/install.sh --no-link
```

## Usage

```
claude-rec                              # default: cast + gif + mp4
claude-rec --idle 1                     # idle threshold = 1s
claude-rec --no-mp4                     # skip mp4
claude-rec --cast-only                  # skip all conversion
claude-rec --no-compress-spinner        # disable spinner compression
claude-rec -o /tmp/test                 # custom output dir
claude-rec -h                           # full help
```

Output files default to `~/Recordings/claude-skills/claude-YYYYMMDD-HHMMSS.{cast,gif,mp4}`.

Inside the recorded session, just use Claude Code normally. When you exit (`/quit`), the script stops recording and converts.

## Notes

- Recording happens via `asciinema rec --command claude`. The wrapper must start `claude` itself; you cannot start recording from inside an already-running Claude Code session.
- **Spinner compression**: by default, the cast is pre-processed before gif/mp4 generation to collapse animated progress indicators (Claude Code's "Envisioning…", npm/docker progress bars, etc.) into a 0.5s flash. This requires `python3`. Disable with `--no-compress-spinner` if it interferes with your content. The original `.cast` file is preserved untouched; only the gif/mp4 are compressed.
- Multiple invocations within the same second will collide (filenames are second-precision). Wait a second between back-to-back recordings.
- If conversion fails, the `.cast` file is preserved. You can re-run `agg` and `ffmpeg` manually.

## Design

See [`docs/superpowers/specs/2026-04-25-claude-rec-design.md`](docs/superpowers/specs/2026-04-25-claude-rec-design.md).

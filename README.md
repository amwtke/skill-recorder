# cli-rec

Record AI-CLI sessions ([Claude Code](https://docs.claude.com/en/docs/claude-code), Trae, …) as `.cast` / `.gif` / `.mp4`. Idle gaps are auto-compressed using asciinema; animated progress spinners ("Envisioning…", npm/docker bars, …) are collapsed to a 0.5s flash via cast pre-processing. Each platform has its own spinner-tuning file under `bin/spinners/`.

## Quick start (bare machine)

```bash
git clone git@github.com:amwtke/skill-recorder.git
cd skill-recorder
./bin/install.sh        # installs asciinema, agg, ffmpeg, python3
./bin/cli-rec           # record a Claude Code session (default platform)
./bin/cli-rec -p trae   # record a Trae CLI session
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

The AI CLIs themselves (`claude`, `trae`, …) are not installed by this script — install them separately from their respective vendors.

### Global `cli-rec` command

By default, `install.sh` symlinks `cli-rec` and `compress-spinner.py` into `~/.local/bin/`. After install:

```bash
cli-rec --help        # callable from anywhere
```

If `~/.local/bin` isn't on your `$PATH`, the script prints a one-line snippet to add to your shell profile.

The symlinks point back into the repo, so `git pull` updates `cli-rec` instantly without re-installing. (The `bin/spinners/` package is loaded relative to `compress-spinner.py`'s real path, so it's picked up through the symlink without needing to be linked separately.)

To skip the symlink step (deps only):

```bash
./bin/install.sh --no-link
```

## Usage

```
cli-rec                                 # default: Claude Code, cast + gif + mp4
cli-rec -p trae                         # record Trae CLI
cli-rec --cmd "claude --resume"         # full command override
cli-rec -p claude -d                    # claude + --dangerously-skip-permissions
cli-rec --idle 1                        # idle threshold = 1s
cli-rec --no-mp4                        # skip mp4
cli-rec --cast-only                     # skip all conversion
cli-rec --no-compress-spinner           # disable spinner compression
cli-rec -o /tmp/test                    # custom output dir
cli-rec -h                              # full help
```

Output files default to `~/Recordings/claude-skills/<platform>-YYYYMMDD-HHMMSS.{cast,gif,mp4}`.

Inside the recorded session, just use the CLI normally. When you exit, the script stops recording and converts.

## Adding a new platform

Each AI CLI has its own spinner / progress-indicator style, so compression thresholds are tuned per platform via the strategy pattern under `bin/spinners/`:

```
bin/spinners/
  base.py        # SpinnerStrategy base class + shared OSC detection
  claude.py      # Claude Code tuning (the default)
  trae.py        # Trae CLI tuning (placeholder, inherits defaults)
```

To add support for another CLI, e.g. `foo-cli`:

1. Create `bin/spinners/foo.py`:

   ```python
   from .base import SpinnerStrategy

   class FooStrategy(SpinnerStrategy):
       name = "foo"
       # override class attrs as needed:
       # min_run_length = 20
       # max_event_bytes = 400
       # max_delta = 0.5
       # compressed_duration = 0.5

   STRATEGY = FooStrategy()
   ```

2. Run with `cli-rec -p foo` (or `cli-rec -p foo --cmd "foo-cli chat"` if the binary name differs).

The base class also exposes `is_invisible()` and `is_spinner_event()` if you need to override the detection logic itself, not just the thresholds.

## Notes

- Recording happens via `asciinema rec --command <cmd>`. The wrapper must start the CLI itself; you cannot start recording from inside an already-running session.
- **Spinner compression**: by default, the cast is pre-processed before gif/mp4 generation to collapse animated progress indicators into a 0.5s flash. This requires `python3`. Disable with `--no-compress-spinner` if it interferes with your content. The original `.cast` file is preserved untouched; only the gif/mp4 are compressed.
- **`-d` is Claude-only**: it appends `--dangerously-skip-permissions` to the launched command, which is a Claude Code flag. Using it with another platform errors out. For other CLIs, pass flags via `--cmd "trae chat --foo"`.
- Multiple invocations within the same second will collide (filenames are second-precision). Wait a second between back-to-back recordings.
- If conversion fails, the `.cast` file is preserved. You can re-run `agg` and `ffmpeg` manually.

## Design

See [`docs/superpowers/specs/2026-04-25-claude-rec-design.md`](docs/superpowers/specs/2026-04-25-claude-rec-design.md).

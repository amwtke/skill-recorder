# claude-rec

Record [Claude Code](https://docs.claude.com/en/docs/claude-code) sessions as `.cast` / `.gif` / `.mp4`. Idle gaps are auto-compressed using asciinema.

## Install

### 1. Dependencies

**macOS:**
```
brew install asciinema agg ffmpeg
```

**Ubuntu Linux:**
```
sudo apt install asciinema ffmpeg
cargo install --git https://github.com/asciinema/agg
```

(Ubuntu does not have an official `agg` package — `cargo` and a Rust toolchain are required for the `agg` install.)

Also requires the `claude` CLI in `$PATH`.

### 2. The script

```
mkdir -p ~/.local/bin
cp bin/claude-rec ~/.local/bin/
chmod +x ~/.local/bin/claude-rec
```

Make sure `~/.local/bin` is in your `$PATH`.

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

# claude-rec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-platform shell script `claude-rec` that records Claude Code sessions via asciinema with idle-gap compression, producing `.cast`, `.gif`, and `.mp4` files.

**Architecture:** Single bash script in `bin/claude-rec`. Wraps `asciinema rec --command claude`, then post-processes cast → gif (via `agg`) → mp4 (via `ffmpeg`). OS-aware error messages for missing dependencies. CLI flags control output directory, idle threshold, and conversion stages.

**Tech Stack:** bash 4+, asciinema, agg, ffmpeg, standard Unix utilities (`date`, `uname`, `mkdir`, `command -v`, `du`).

---

## File Structure

```
skill-recorder/
├── bin/
│   └── claude-rec                # Executable script (single source of truth)
├── README.md                     # Install + usage
├── LICENSE                       # (already present)
└── docs/superpowers/
    ├── specs/2026-04-25-claude-rec-design.md     # (already present)
    └── plans/2026-04-25-claude-rec-implementation.md  # (this file)
```

**Single-file design.** All logic lives in `bin/claude-rec` (~120 lines). No source split — script is small enough to be read top-to-bottom in one sitting.

**Verification approach.** Per spec, no automated test suite. Each task ends with **manual verification commands** + expected outputs. The implementer runs the script directly against scenarios; correctness is checked by inspecting output and generated files.

---

## Task 1: Skeleton + `--help`

**Files:**
- Create: `bin/claude-rec`

- [ ] **Step 1: Create the bin directory**

```bash
mkdir -p bin
```

- [ ] **Step 2: Write the minimal script with help text**

Create `bin/claude-rec` with this content:

```bash
#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
claude-rec — record a Claude Code session as cast/gif/mp4

Usage: claude-rec [OPTIONS]

Options:
  -o, --output <DIR>     Output directory (default: ~/Recordings/claude-skills)
  -i, --idle <SECONDS>   Compress idle gaps to N seconds (default: 1)
      --no-mp4           Skip mp4 generation (still produces cast + gif)
      --cast-only        Skip all conversion (only .cast file)
  -h, --help             Show this help

Output files: <DIR>/claude-YYYYMMDD-HHMMSS.{cast,gif,mp4}
EOF
}

main() {
  case "${1:-}" in
    -h|--help) show_help; exit 0 ;;
  esac
  echo "stub: not implemented yet" >&2
  exit 1
}

main "$@"
```

- [ ] **Step 3: Make it executable**

```bash
chmod +x bin/claude-rec
```

- [ ] **Step 4: Verify `--help` works**

Run: `./bin/claude-rec --help`
Expected: prints the help block, exits 0.

Run: `./bin/claude-rec -h`
Expected: same as above.

Run: `./bin/claude-rec`
Expected: prints `stub: not implemented yet`, exits 1.

- [ ] **Step 5: Commit**

```bash
git add bin/claude-rec
git commit -m "feat(claude-rec): add script skeleton with --help"
```

---

## Task 2: Argument parsing

**Files:**
- Modify: `bin/claude-rec`

- [ ] **Step 1: Replace `main` with full argument parser**

In `bin/claude-rec`, replace the existing `main` function with:

```bash
main() {
  local output_dir="$HOME/Recordings/claude-skills"
  local idle="1"
  local no_mp4=0
  local cast_only=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)    show_help; exit 0 ;;
      -o|--output)  output_dir="$2"; shift 2 ;;
      -i|--idle)    idle="$2"; shift 2 ;;
      --no-mp4)     no_mp4=1; shift ;;
      --cast-only)  cast_only=1; shift ;;
      *) echo "unknown option: $1" >&2; show_help >&2; exit 2 ;;
    esac
  done

  # cast-only is more aggressive than no-mp4
  if [[ $cast_only -eq 1 ]]; then
    no_mp4=1
  fi

  # Debug echos — will be replaced in later tasks
  echo "output_dir=$output_dir"
  echo "idle=$idle"
  echo "no_mp4=$no_mp4"
  echo "cast_only=$cast_only"
}
```

- [ ] **Step 2: Verify defaults**

Run: `./bin/claude-rec`
Expected:
```
output_dir=/Users/<you>/Recordings/claude-skills
idle=1
no_mp4=0
cast_only=0
```

- [ ] **Step 3: Verify each flag**

Run: `./bin/claude-rec -o /tmp/x -i 2 --no-mp4`
Expected:
```
output_dir=/tmp/x
idle=2
no_mp4=1
cast_only=0
```

Run: `./bin/claude-rec --cast-only`
Expected: `no_mp4=1` and `cast_only=1` (cast-only forces no_mp4=1).

Run: `./bin/claude-rec --bogus`
Expected: `unknown option: --bogus` to stderr, help to stderr, exit 2.

- [ ] **Step 4: Commit**

```bash
git add bin/claude-rec
git commit -m "feat(claude-rec): parse command-line arguments"
```

---

## Task 3: Dependency check

**Files:**
- Modify: `bin/claude-rec`

- [ ] **Step 1: Add OS detection and dependency check helpers**

In `bin/claude-rec`, add these functions **above** `main` (between `show_help` and `main`):

```bash
detect_os() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux)  echo "linux" ;;
    *)      echo "unsupported" ;;
  esac
}

install_hint() {
  local tool="$1" os="$2"
  case "$os:$tool" in
    macos:asciinema) echo "  brew install asciinema" ;;
    macos:agg)       echo "  brew install agg" ;;
    macos:ffmpeg)    echo "  brew install ffmpeg" ;;
    linux:asciinema) echo "  sudo apt install asciinema" ;;
    linux:agg)       echo "  cargo install --git https://github.com/asciinema/agg" ;;
    linux:ffmpeg)    echo "  sudo apt install ffmpeg" ;;
    *:claude)        echo "  see Claude Code install docs" ;;
    *)               echo "  (no install hint available)" ;;
  esac
}

check_dep() {
  local tool="$1" os="$2"
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "error: '$tool' not found in PATH" >&2
    echo "install with:" >&2
    install_hint "$tool" "$os" >&2
    exit 1
  fi
}

check_deps() {
  local os
  os="$(detect_os)"
  if [[ "$os" == "unsupported" ]]; then
    echo "error: unsupported OS ($(uname -s)). claude-rec supports macOS and Linux." >&2
    exit 1
  fi
  check_dep claude "$os"
  check_dep asciinema "$os"
  if [[ $cast_only -eq 0 ]]; then
    check_dep agg "$os"
  fi
  if [[ $no_mp4 -eq 0 ]]; then
    check_dep ffmpeg "$os"
  fi
}
```

Note: `cast_only` and `no_mp4` are read by `check_deps` from `main`'s local scope (bash dynamic scoping — locals are visible to functions called from within).

- [ ] **Step 2: Wire `check_deps` into `main`**

In `main`, replace the four debug `echo` lines with:

```bash
  check_deps
  echo "all deps OK"
  echo "output_dir=$output_dir idle=$idle no_mp4=$no_mp4 cast_only=$cast_only"
```

- [ ] **Step 3: Verify happy path (all deps present)**

Run: `./bin/claude-rec`
Expected:
```
all deps OK
output_dir=/Users/<you>/Recordings/claude-skills idle=1 no_mp4=0 cast_only=0
```

- [ ] **Step 4: Verify missing dep is detected**

Simulate missing deps by stripping non-system paths:

```bash
PATH="/usr/bin:/bin" ./bin/claude-rec
```

Expected: `error: 'claude' not found in PATH`, install hint, exit 1.
(If `claude` is in `/usr/bin`, the missing one will be `asciinema` or `agg` — same shape.)

- [ ] **Step 5: Verify `--cast-only` skips agg/ffmpeg**

Run: `./bin/claude-rec --cast-only`
Expected: `all deps OK` (only `claude` and `asciinema` were checked).

If you want to confirm agg/ffmpeg really weren't checked, temporarily rename one:
```bash
# (only if you want to be sure; otherwise skip)
sudo mv "$(command -v agg)" "$(command -v agg).bak"
./bin/claude-rec --cast-only   # should still say "all deps OK"
sudo mv "$(command -v agg).bak" "$(command -v agg | sed 's/.bak//')"
```

- [ ] **Step 6: Commit**

```bash
git add bin/claude-rec
git commit -m "feat(claude-rec): check dependencies with OS-specific install hints"
```

---

## Task 4: Path preparation

**Files:**
- Modify: `bin/claude-rec`

- [ ] **Step 1: Add `prepare_paths` helper**

Add this function above `main`, after `check_deps`:

```bash
prepare_paths() {
  local out_dir="$1"
  local ts
  ts="$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$out_dir"
  echo "${out_dir%/}/claude-${ts}"
}
```

- [ ] **Step 2: Use it in `main`**

In `main`, replace the two trailing `echo` lines (`all deps OK` + the params dump) with:

```bash
  local base cast_path gif_path mp4_path
  base="$(prepare_paths "$output_dir")"
  cast_path="$base.cast"
  gif_path="$base.gif"
  mp4_path="$base.mp4"

  echo "output dir ready: $output_dir"
  echo "would record to: $cast_path"
```

- [ ] **Step 3: Verify path generation**

Run: `./bin/claude-rec -o /tmp/test-claude-rec`
Expected:
```
output dir ready: /tmp/test-claude-rec
would record to: /tmp/test-claude-rec/claude-YYYYMMDD-HHMMSS.cast
```

Then: `ls -d /tmp/test-claude-rec`
Expected: directory exists.

- [ ] **Step 4: Cleanup**

```bash
rm -rf /tmp/test-claude-rec
```

- [ ] **Step 5: Commit**

```bash
git add bin/claude-rec
git commit -m "feat(claude-rec): compute timestamped output paths and create dir"
```

---

## Task 5: Recording invocation

**Files:**
- Modify: `bin/claude-rec`

- [ ] **Step 1: Replace the `would record to` echo with the actual recording**

In `main`, replace:

```bash
  echo "output dir ready: $output_dir"
  echo "would record to: $cast_path"
```

with:

```bash
  echo "output dir ready: $output_dir"
  echo "recording to: $cast_path"
  echo "(exit claude with /quit when done)"
  if ! asciinema rec --idle-time-limit="$idle" --command "claude" "$cast_path"; then
    echo "warning: claude exited non-zero (cast file is still valid)" >&2
  fi
  echo "recording stopped: $cast_path"
```

Note: the `if !` form prevents `set -e` from aborting if asciinema/claude returns non-zero — we want to continue to post-processing in that case.

- [ ] **Step 2: End-to-end test of recording**

Run: `./bin/claude-rec --cast-only -o /tmp/test-claude-rec`

Inside the claude session that opens:
1. Type `hello, this is a test`
2. Wait for response
3. Type `/quit` to exit

Expected after exit:
```
recording stopped: /tmp/test-claude-rec/claude-...cast
```

Verify the cast file:
```bash
ls /tmp/test-claude-rec/
asciinema play /tmp/test-claude-rec/claude-*.cast
```

The replay should show your input + claude's response, with idle gaps compressed.

- [ ] **Step 3: Commit**

```bash
git add bin/claude-rec
git commit -m "feat(claude-rec): invoke asciinema rec with idle-gap compression"
```

---

## Task 6: Conversion pipeline (cast → gif → mp4)

**Files:**
- Modify: `bin/claude-rec`

- [ ] **Step 1: Add the conversion block in `main`**

In `main`, after the `recording stopped:` line, add:

```bash
  if [[ $cast_only -eq 1 ]]; then
    echo "skipping conversion (--cast-only)"
  else
    echo "converting to gif: $gif_path"
    if ! agg "$cast_path" "$gif_path"; then
      echo "warning: agg failed; .cast preserved at $cast_path" >&2
      exit 0
    fi

    if [[ $no_mp4 -eq 1 ]]; then
      echo "skipping mp4 (--no-mp4)"
    else
      echo "converting to mp4: $mp4_path"
      if ! ffmpeg -y -i "$gif_path" -movflags +faststart -pix_fmt yuv420p "$mp4_path" 2>/dev/null; then
        echo "warning: ffmpeg failed; .cast and .gif preserved" >&2
        exit 0
      fi
    fi
  fi
```

The `2>/dev/null` on ffmpeg suppresses its verbose stderr output (it's noisy by default). Errors are still reflected in the exit code.

- [ ] **Step 2: Test full pipeline (cast + gif + mp4)**

Run: `./bin/claude-rec -o /tmp/test-claude-rec`
(Type something in claude, `/quit`)

Expected output:
```
recording stopped: /tmp/test-claude-rec/claude-....cast
converting to gif: /tmp/test-claude-rec/claude-....gif
converting to mp4: /tmp/test-claude-rec/claude-....mp4
```

Verify all three files exist:
```bash
ls /tmp/test-claude-rec/
# expect: claude-....cast, claude-....gif, claude-....mp4
```

Open the mp4 in any player:
```bash
open /tmp/test-claude-rec/claude-*.mp4   # macOS
xdg-open /tmp/test-claude-rec/claude-*.mp4   # Linux
```

Expected: video plays, idle gaps are compressed.

- [ ] **Step 3: Test `--no-mp4`**

Run: `./bin/claude-rec --no-mp4 -o /tmp/test-claude-rec`
(Brief session, `/quit`)

Expected: prints `skipping mp4 (--no-mp4)`. Only `.cast` and `.gif` produced for this run.

- [ ] **Step 4: Cleanup**

```bash
rm -rf /tmp/test-claude-rec
```

- [ ] **Step 5: Commit**

```bash
git add bin/claude-rec
git commit -m "feat(claude-rec): convert cast to gif and mp4 with conditional skip"
```

---

## Task 7: Final summary output

**Files:**
- Modify: `bin/claude-rec`

- [ ] **Step 1: Add `print_size` helper**

Above `main`, after `prepare_paths`, add:

```bash
print_size() {
  local file="$1"
  if [[ -f "$file" ]]; then
    local size
    size="$(du -h "$file" | awk '{print $1}')"
    echo "  $file ($size)"
  fi
}
```

- [ ] **Step 2: Append summary at the end of `main`**

At the very end of `main` (after the conversion block), add:

```bash
  echo
  echo "done. files:"
  print_size "$cast_path"
  print_size "$gif_path"
  print_size "$mp4_path"
```

`print_size` silently skips non-existent files — so under `--cast-only` only the cast row prints, under `--no-mp4` cast + gif print, etc.

- [ ] **Step 3: End-to-end smoke test**

Run: `./bin/claude-rec -o /tmp/test-claude-rec`
(Type stuff in claude, `/quit`)

Expected ending:
```
done. files:
  /tmp/test-claude-rec/claude-....cast (4.0K)
  /tmp/test-claude-rec/claude-....gif (200K)
  /tmp/test-claude-rec/claude-....mp4 (50K)
```
(actual sizes will vary)

- [ ] **Step 4: Verify summary respects `--cast-only`**

Run: `./bin/claude-rec --cast-only -o /tmp/test-claude-rec`
(Brief session, `/quit`)

Expected: only the `.cast` row in the final summary.

- [ ] **Step 5: Cleanup**

```bash
rm -rf /tmp/test-claude-rec
```

- [ ] **Step 6: Commit**

```bash
git add bin/claude-rec
git commit -m "feat(claude-rec): print final summary with file sizes"
```

---

## Task 8: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

Create `README.md`:

````markdown
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
claude-rec --idle 2                     # idle threshold = 2s
claude-rec --no-mp4                     # skip mp4
claude-rec --cast-only                  # skip all conversion
claude-rec -o /tmp/test                 # custom output dir
claude-rec -h                           # full help
```

Output files default to `~/Recordings/claude-skills/claude-YYYYMMDD-HHMMSS.{cast,gif,mp4}`.

Inside the recorded session, just use Claude Code normally. When you exit (`/quit`), the script stops recording and converts.

## Design

See [`docs/superpowers/specs/2026-04-25-claude-rec-design.md`](docs/superpowers/specs/2026-04-25-claude-rec-design.md).
````

- [ ] **Step 2: Verify README looks right**

Run: `cat README.md`
Expected: clean markdown, all sections present.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with install and usage"
```

---

## Spec Coverage Check

| Spec section | Implemented in |
|---|---|
| Single shell script `bin/claude-rec` | Tasks 1–7 |
| Cross-platform (macOS + Ubuntu) | Task 3 (OS detection + per-OS hints) |
| Uses asciinema | Task 5 |
| Uses agg | Task 6 |
| Uses ffmpeg | Task 6 |
| CLI args (`-o`, `-i`, `--no-mp4`, `--cast-only`, `-h`) | Tasks 1, 2 |
| Default output `~/Recordings/claude-skills/` | Task 2 (default value) |
| Filename `claude-YYYYMMDD-HHMMSS.{cast,gif,mp4}` | Task 4 |
| Idle compression | Task 5 (`--idle-time-limit`) |
| All 3 files retained | Task 6 (no `rm` of intermediates) |
| Error: dep missing → install hint, exit 1 | Task 3 |
| Error: claude not in PATH → exit 1 | Task 3 |
| Error: claude exits non-zero → warn, continue | Task 5 (`if !`) |
| Error: agg/ffmpeg fails → preserve cast, exit 0 | Task 6 |
| Error: output dir creation fails → exit 1 | Task 4 (`set -e` + `mkdir -p`) |
| Summary with paths + sizes | Task 7 |
| Install instructions | Task 8 |

All spec requirements have a task. No gaps.

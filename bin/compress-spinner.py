#!/usr/bin/env python3
"""
Compress spinner-like runs in an asciinema v2 or v3 cast file.

A "spinner run" is a sequence of small consecutive events that visually
appear as an animation but contain no substantial new content (e.g.,
Claude Code's "Envisioning..." / "Imagining..." status indicators,
npm/docker/git progress bars, etc).

Heuristic (tunable per platform via spinners/<platform>.py): a run of
>= min_run_length consecutive events where each event is <
max_event_bytes bytes and each delta is < max_delta seconds is collapsed
to a single "last frame" event with a fixed compressed_duration delta.
Real streamed content (typically larger events with formatted output) is
preserved.

We also drop "invisible" events whose payload renders nothing on the
terminal grid (default: payloads consisting entirely of OSC sequences —
window title, badges, iTerm2 notifications). agg renders only the
terminal grid, so these change nothing on screen — but each one is still
a separate cast event, which fragments long subagent-wait gaps into many
medium gaps that idle-time-limit cannot fully collapse. The dropped
event's delta is folded into the next visible event so timing stays
correct.

v2 and v3 differ in the first field of each event tuple: v2 stores an
absolute timestamp, v3 stores a delta from the previous event. We read
both, work in deltas internally, and emit in whichever format the input
used so downstream tools (e.g. agg) keep working.

Streams input → output line by line; the in-memory buffer holds at most
min_run_length events, so peak memory stays bounded regardless of cast
length (safe for multi-hour recordings).

Usage: compress-spinner.py [--platform NAME] <input.cast> <output.cast>
"""
import argparse
import json
import os
import shutil
import sys

# Resolve the real script path so the spinners/ package is importable
# even when this script is invoked through a symlink (install.sh links
# it into ~/.local/bin/).
_REAL_DIR = os.path.dirname(os.path.realpath(__file__))
if _REAL_DIR not in sys.path:
    sys.path.insert(0, _REAL_DIR)

from spinners import load as load_strategy


def parse_args():
    p = argparse.ArgumentParser(
        description="Compress spinner-like runs in an asciinema cast file.",
    )
    p.add_argument("input", help="input .cast file")
    p.add_argument("output", help="output .cast file")
    p.add_argument(
        "--platform",
        default="claude",
        help="spinner-strategy name (default: claude). Maps to spinners/<name>.py",
    )
    return p.parse_args()


def main():
    args = parse_args()

    try:
        strategy = load_strategy(args.platform)
    except ModuleNotFoundError:
        print(
            f"compress-spinner: unknown platform {args.platform!r} "
            f"(no spinners/{args.platform}.py)",
            file=sys.stderr,
        )
        sys.exit(2)

    inp, out = args.input, args.output

    buffer = []
    stats = {
        "saved": 0.0,
        "runs_compressed": 0,
        "events_dropped": 0,
        "invisible_dropped": 0,
    }

    with open(inp) as f_in, open(out, "w") as f_out:
        header_line = f_in.readline()
        try:
            version = json.loads(header_line).get("version")
        except (json.JSONDecodeError, AttributeError):
            version = None
        if version not in (2, 3):
            print(
                f"compress-spinner: unsupported cast version {version!r}, "
                "passing through unchanged",
                file=sys.stderr,
            )
            f_out.write(header_line)
            shutil.copyfileobj(f_in, f_out)
            return
        f_out.write(header_line)

        prev_in_ts = 0.0    # v2: last absolute timestamp read from input
        out_ts = 0.0        # v2: last absolute timestamp written to output
        pending_delta = 0.0 # delta accumulated from dropped invisible events

        def write_event(delta, kind, data):
            nonlocal out_ts
            if version == 2:
                out_ts += delta
                f_out.write(json.dumps([out_ts, kind, data], ensure_ascii=False) + "\n")
            else:
                f_out.write(json.dumps([delta, kind, data], ensure_ascii=False) + "\n")

        def flush():
            if not buffer:
                return
            if len(buffer) >= strategy.min_run_length:
                run_time = sum(e[0] for e in buffer)
                _, kind, data = buffer[-1]
                write_event(strategy.compressed_duration, kind, data)
                stats["saved"] += run_time - strategy.compressed_duration
                stats["runs_compressed"] += 1
                stats["events_dropped"] += len(buffer) - 1
            else:
                for delta, kind, data in buffer:
                    write_event(delta, kind, data)
            buffer.clear()

        for line in f_in:
            stripped = line.strip()
            if not stripped.startswith("["):
                continue
            t, kind, data = json.loads(stripped)
            if version == 2:
                delta = t - prev_in_ts
                prev_in_ts = t
            else:
                delta = t

            if strategy.is_invisible(kind, data):
                pending_delta += delta
                stats["invisible_dropped"] += 1
                continue

            delta += pending_delta
            pending_delta = 0.0

            if strategy.is_spinner_event(delta, data):
                buffer.append((delta, kind, data))
            else:
                flush()
                write_event(delta, kind, data)
        flush()

    print(
        f"compress-spinner[{strategy.name}]: "
        f"{stats['runs_compressed']} run(s) compressed, "
        f"{stats['events_dropped']} events dropped, "
        f"{stats['invisible_dropped']} invisible events dropped, "
        f"~{stats['saved']:.2f}s saved",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

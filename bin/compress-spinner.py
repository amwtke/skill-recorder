#!/usr/bin/env python3
"""
Compress spinner-like runs in an asciinema v2 or v3 cast file.

A "spinner run" is a sequence of small consecutive events that visually
appear as an animation but contain no substantial new content (e.g.,
Claude Code's "Envisioning..." / "Imagining..." status indicators,
npm/docker/git progress bars, etc).

Heuristic: a run of >= MIN_RUN_LENGTH consecutive events where each event
is < MAX_EVENT_BYTES bytes and each delta is < MAX_DELTA seconds is
collapsed to a single "last frame" event with a fixed COMPRESSED_DURATION
delta. Real streamed content (typically larger events with formatted
output) is preserved.

We also drop "invisible" events whose payload consists entirely of OSC
sequences (window title, badges, iTerm2 notifications). agg renders only
the terminal grid, so these change nothing on screen — but each one is
still a separate cast event, which fragments long subagent-wait gaps
into many medium gaps that idle-time-limit cannot fully collapse. The
dropped event's delta is folded into the next visible event so timing
stays correct.

v2 and v3 differ in the first field of each event tuple: v2 stores an
absolute timestamp, v3 stores a delta from the previous event. We read
both, work in deltas internally, and emit in whichever format the input
used so downstream tools (e.g. agg) keep working.

Streams input → output line by line; the in-memory buffer holds at most
MIN_RUN_LENGTH events, so peak memory stays bounded regardless of cast
length (safe for multi-hour recordings).

Usage: compress-spinner.py <input.cast> <output.cast>
"""
import json
import re
import shutil
import sys

MIN_RUN_LENGTH = 15
MAX_EVENT_BYTES = 250
MAX_DELTA = 0.3
COMPRESSED_DURATION = 0.5

# OSC sequence: ESC ] ... (BEL | ESC \). Body cannot contain BEL or ESC
# except as part of the ST terminator.
_OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


def is_invisible_event(kind, data):
    """True if this output event renders nothing on the terminal grid —
    i.e. its payload is entirely OSC sequences (and nothing else)."""
    if kind != "o" or not data:
        return False
    return _OSC_RE.sub("", data) == ""


def main():
    if len(sys.argv) != 3:
        print("usage: compress-spinner.py <input.cast> <output.cast>", file=sys.stderr)
        sys.exit(2)

    inp, out = sys.argv[1], sys.argv[2]

    buffer = []
    stats = {
        "saved": 0.0,
        "runs_compressed": 0,
        "events_dropped": 0,
        "osc_dropped": 0,
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
            if len(buffer) >= MIN_RUN_LENGTH:
                run_time = sum(e[0] for e in buffer)
                _, kind, data = buffer[-1]
                write_event(COMPRESSED_DURATION, kind, data)
                stats["saved"] += run_time - COMPRESSED_DURATION
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

            if is_invisible_event(kind, data):
                pending_delta += delta
                stats["osc_dropped"] += 1
                continue

            delta += pending_delta
            pending_delta = 0.0

            if len(data.encode()) < MAX_EVENT_BYTES and delta < MAX_DELTA:
                buffer.append((delta, kind, data))
            else:
                flush()
                write_event(delta, kind, data)
        flush()

    print(
        f"compress-spinner: {stats['runs_compressed']} run(s) compressed, "
        f"{stats['events_dropped']} events dropped, "
        f"{stats['osc_dropped']} OSC-only events dropped, "
        f"~{stats['saved']:.2f}s saved",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

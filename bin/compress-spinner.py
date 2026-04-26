#!/usr/bin/env python3
"""
Compress spinner-like runs in an asciinema v3 cast file.

A "spinner run" is a sequence of small consecutive events that visually
appear as an animation but contain no substantial new content (e.g.,
Claude Code's "Envisioning..." / "Imagining..." status indicators,
npm/docker/git progress bars, etc).

Heuristic: a run of >= MIN_RUN_LENGTH consecutive events where each event
is < MAX_EVENT_BYTES bytes and each delta is < MAX_DELTA seconds is
collapsed to a single "last frame" event with a fixed COMPRESSED_DURATION
delta. Real streamed content (typically larger events with formatted
output) is preserved.

Streams input → output line by line; the in-memory buffer holds at most
MIN_RUN_LENGTH events, so peak memory stays bounded regardless of cast
length (safe for multi-hour recordings).

Usage: compress-spinner.py <input.cast> <output.cast>
"""
import json
import sys

MIN_RUN_LENGTH = 15
MAX_EVENT_BYTES = 250
MAX_DELTA = 0.3
COMPRESSED_DURATION = 0.5


def main():
    if len(sys.argv) != 3:
        print("usage: compress-spinner.py <input.cast> <output.cast>", file=sys.stderr)
        sys.exit(2)

    inp, out = sys.argv[1], sys.argv[2]

    buffer = []
    stats = {"saved": 0.0, "runs_compressed": 0, "events_dropped": 0}

    def write_event(f, event):
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def flush(f):
        if not buffer:
            return
        if len(buffer) >= MIN_RUN_LENGTH:
            run_time = sum(e[0] for e in buffer)
            last = list(buffer[-1])
            last[0] = COMPRESSED_DURATION
            write_event(f, last)
            stats["saved"] += run_time - COMPRESSED_DURATION
            stats["runs_compressed"] += 1
            stats["events_dropped"] += len(buffer) - 1
        else:
            for e in buffer:
                write_event(f, e)
        buffer.clear()

    with open(inp) as f_in, open(out, "w") as f_out:
        header = f_in.readline()
        f_out.write(header)
        for line in f_in:
            stripped = line.strip()
            if not stripped.startswith("["):
                continue
            event = json.loads(stripped)
            delta, _kind, data = event
            if len(data.encode()) < MAX_EVENT_BYTES and delta < MAX_DELTA:
                buffer.append(event)
            else:
                flush(f_out)
                write_event(f_out, event)
        flush(f_out)

    print(
        f"compress-spinner: {stats['runs_compressed']} run(s) compressed, "
        f"{stats['events_dropped']} events dropped, ~{stats['saved']:.2f}s saved",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

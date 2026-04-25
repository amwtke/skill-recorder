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

    with open(inp) as f:
        header = f.readline()
        events = [json.loads(line.strip()) for line in f if line.strip().startswith("[")]

    output_events = []
    saved = 0.0
    runs_compressed = 0
    i = 0
    while i < len(events):
        j = i
        while j < len(events):
            delta, _kind, data = events[j]
            if len(data.encode()) < MAX_EVENT_BYTES and delta < MAX_DELTA:
                j += 1
            else:
                break

        run_length = j - i
        if run_length >= MIN_RUN_LENGTH:
            run_time = sum(e[0] for e in events[i:j])
            last = list(events[j - 1])
            last[0] = COMPRESSED_DURATION
            output_events.append(last)
            saved += run_time - COMPRESSED_DURATION
            runs_compressed += 1
            i = j
        else:
            output_events.append(events[i])
            i += 1

    with open(out, "w") as f:
        f.write(header)
        for e in output_events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(
        f"compress-spinner: {runs_compressed} run(s) compressed, "
        f"{len(events) - len(output_events)} events dropped, ~{saved:.2f}s saved",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

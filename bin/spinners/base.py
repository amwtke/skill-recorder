"""Base SpinnerStrategy: tuning knobs and shared heuristics.

Subclass per platform and override the class attributes (or methods) that
need different tuning. The base values reflect what worked for Claude
Code's "Envisioning…" indicator and similar small-payload spinners.
"""
import re

# OSC sequence: ESC ] ... (BEL | ESC \). Body cannot contain BEL or ESC
# except as part of the ST terminator.
OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


class SpinnerStrategy:
    name = "default"

    # Minimum consecutive small-fast events to treat as a spinner run.
    min_run_length = 15
    # Events larger than this byte count are treated as "real content".
    max_event_bytes = 250
    # Inter-event delay above this is treated as a real pause, not animation.
    max_delta = 0.3
    # Each compressed run collapses to one frame with this delta (seconds).
    compressed_duration = 0.5

    def is_invisible(self, kind: str, data: str) -> bool:
        """True if the event payload renders nothing on the terminal grid.

        Default: payload is entirely OSC sequences (window title, badges,
        iTerm2 notifications). agg ignores these but each one is still a
        cast event that fragments idle gaps, so we drop them and fold
        their delta into the next visible event.
        """
        if kind != "o" or not data:
            return False
        return OSC_RE.sub("", data) == ""

    def is_spinner_event(self, delta: float, data: str) -> bool:
        """True if the event is small and fast enough to be part of a run."""
        return len(data.encode()) < self.max_event_bytes and delta < self.max_delta

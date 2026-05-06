"""Claude Code spinner tuning.

Targets the small status-line animations Claude Code emits while waiting
on tools or subagents (e.g. "Envisioning…", "Imagining…"). The base
defaults already reflect this profile, so no overrides are needed.
"""
from .base import SpinnerStrategy


class ClaudeStrategy(SpinnerStrategy):
    name = "claude"


STRATEGY = ClaudeStrategy()

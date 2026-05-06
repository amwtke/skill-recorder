"""Trae CLI spinner tuning.

Placeholder: inherits the base defaults until we capture a real Trae
recording and tune the thresholds against its progress / spinner style.
"""
from .base import SpinnerStrategy


class TraeStrategy(SpinnerStrategy):
    name = "trae"


STRATEGY = TraeStrategy()

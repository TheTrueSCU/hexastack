"""Domain models and data contracts for CLI testing and narrative demonstration."""

from dataclasses import dataclass

__all__ = [
    "TerminalEvent",
]


@dataclass(frozen=True)
class TerminalEvent:
    """A discrete timestamped event within a CLI demo recording session."""

    event_type: str  # "step" | "input" | "output"
    payload: str
    timestamp: float

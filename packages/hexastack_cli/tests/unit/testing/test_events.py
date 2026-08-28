"""Unit tests for CLI testing events data models."""

from hexastack_cli.testing.events import TerminalEvent


def test_terminal_event_instantiation() -> None:
    """Verify TerminalEvent properties and immutability."""
    ev = TerminalEvent(event_type="step", payload="Running command...", timestamp=1.23)
    assert ev.event_type == "step"
    assert ev.payload == "Running command..."
    assert ev.timestamp == 1.23

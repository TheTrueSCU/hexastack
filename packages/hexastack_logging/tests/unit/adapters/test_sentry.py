"""Unit tests for SentryErrorAdapter."""

from __future__ import annotations

from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_logging.adapters.sentry import SentryErrorAdapter


def test_sentry_error_adapter_delegation() -> None:
    """Verify SentryErrorAdapter delegates logs to inner logger."""
    inner = InMemoryLogger()
    adapter = SentryErrorAdapter(dsn=None, inner_logger=inner)

    adapter.debug("debug message")
    adapter.info("info message")
    adapter.warning("warning message")
    adapter.error("error message", exc=ValueError("boom"))
    adapter.critical("critical message")

    entries = inner.all()
    assert len(entries) == 5
    assert entries[0].level == "debug"
    assert entries[3].level == "error"
    assert entries[4].level == "critical"

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


def test_sentry_error_adapter_properties() -> None:
    """Verify SentryErrorAdapter properties for is_connected and masked_dsn."""
    adapter_no_dsn = SentryErrorAdapter(dsn=None)
    conn_no_dsn = adapter_no_dsn.is_connected
    assert conn_no_dsn is False
    mask_none = adapter_no_dsn.masked_dsn
    assert mask_none is None

    test_dsn = (
        "https://abcdef1234567890abcdef1234567890@o000000.ingest.sentry.io/12345678"
    )
    adapter_with_dsn = SentryErrorAdapter(
        dsn=test_dsn,
        environment="staging",
        release="v1.0.0",
    )
    env = adapter_with_dsn.environment
    assert env == "staging"
    rel = adapter_with_dsn.release
    assert rel == "v1.0.0"
    masked = adapter_with_dsn.masked_dsn
    assert masked is not None
    assert "https://abcdef" in masked
    assert "345678" in masked

    short_adapter = SentryErrorAdapter(dsn="http://short.url")
    short_mask = short_adapter.masked_dsn
    assert short_mask == "***"


def test_sentry_error_adapter_with_mocked_sdk(monkeypatch) -> None:
    """Verify SentryErrorAdapter initializes SDK and calls capture_exception/capture_message."""
    import sys
    from unittest.mock import MagicMock

    mock_sentry = MagicMock()
    mock_scope = MagicMock()
    mock_sentry.push_scope.return_value.__enter__.return_value = mock_scope

    monkeypatch.setitem(sys.modules, "sentry_sdk", mock_sentry)

    test_dsn = "https://example@sentry.io/12345"
    adapter = SentryErrorAdapter(
        dsn=test_dsn,
        environment="production",
        release="1.0.0",
        sample_rate=0.5,
    )
    is_conn = adapter.is_connected
    assert is_conn is True
    mock_sentry.init.assert_called_once_with(
        dsn=test_dsn,
        environment="production",
        release="1.0.0",
        sample_rate=0.5,
    )

    err = RuntimeError("test-error")
    adapter.error("error occurred", extra={"user": "admin"}, exc=err)
    mock_scope.set_extra.assert_called_with("user", "admin")
    mock_sentry.capture_exception.assert_called_with(err)

    mock_sentry.reset_mock()
    mock_scope.reset_mock()
    adapter.critical("critical failure")
    mock_sentry.capture_message.assert_called_with("critical failure", level="fatal")

"""Sentry Error Tracking and Exception Forwarding Adapter."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from hexastack_core.ports.logging import Extras, LoggingPort


def default_before_send(
    event: Any,
    hint: Any,
) -> Any:
    """Filter out synthetic test events and simulated crash routes before Sentry ingestion.

    Args:
        event: Sentry event dictionary.
        hint: Sentry diagnostic hint dictionary containing exception info.

    Returns:
        The filtered event dictionary, or None if the event should be dropped.

    Notes/Architectural Intent:
        Prevents synthetic test routes (e.g. '/sentry-crash') and test-tagged executions
        from consuming ingestion quota or triggering false-positive alerts.
    """
    del hint  # Unused diagnostic hint

    if not isinstance(event, dict):
        return event

    # Inspect request URL if present
    req = event.get("request")
    if isinstance(req, dict):
        url = str(req.get("url", ""))
        if url.endswith("-crash") or "/sentry-crash" in url:
            return None

    # Inspect transaction name if present
    transaction = str(event.get("transaction", ""))
    if transaction.endswith("-crash") or "/sentry-crash" in transaction:
        return None

    # Inspect event tags
    tags = event.get("tags")
    if isinstance(tags, dict):
        path = str(tags.get("path", ""))
        if path.endswith("-crash") or "/sentry-crash" in path:
            return None
        if tags.get("test") in (True, "true", "True"):
            return None

    # Inspect event extra metadata
    extra = event.get("extra")
    if isinstance(extra, dict) and extra.get("test") in (True, "true", "True"):
        return None

    return event


class SentryErrorAdapter(LoggingPort):
    """LoggingPort wrapper that captures and forwards errors to Sentry SDK when initialized.

    Notes/Architectural Intent:
        Integrates Sentry error tracking with ambient context (correlation IDs, user identity, tags)
        without creating hard dependencies when sentry-sdk is absent.
    """

    def __init__(
        self,
        dsn: str | None = None,
        environment: str = "production",
        release: str | None = None,
        sample_rate: float = 1.0,
        inner_logger: LoggingPort | None = None,
        before_send: Callable[..., Any] | None = None,
    ) -> None:
        """Initialize SentryErrorAdapter.

        Args:
            dsn: Sentry Data Source Name URL.
            environment: Deployment environment tag (e.g. 'production', 'staging').
            release: Application version or commit SHA.
            sample_rate: Error sampling rate (0.0 to 1.0).
            inner_logger: Optional underlying LoggingPort to delegate standard logging to.
            before_send: Optional custom Sentry event filtering callback. Defaults to default_before_send.
        """
        self.inner_logger = inner_logger
        self.dsn = dsn
        self.environment = environment
        self.release = release
        self.before_send: Callable[..., Any] = before_send or default_before_send
        self._sentry_initialized = False

        if dsn:
            try:
                import sentry_sdk

                sentry_sdk.init(
                    dsn=dsn,
                    environment=environment,
                    release=release,
                    sample_rate=sample_rate,
                    before_send=self.before_send,
                )
                self._sentry_initialized = True
            except ImportError:
                logging.getLogger("hexastack.sentry").warning(
                    "sentry-sdk not installed; error reporting disabled."
                )
            except Exception as exc:
                logging.getLogger("hexastack.sentry").warning(
                    "Failed to initialize sentry-sdk: %s", exc
                )

    @property
    def is_connected(self) -> bool:
        """Indicate whether Sentry SDK was successfully initialized.

        Returns:
            True if sentry_sdk initialized successfully with a valid DSN, False otherwise.

        Notes/Architectural Intent:
            Used by runtime health checks and DevTools dashboards to verify telemetry connectivity.
        """
        return self._sentry_initialized

    @property
    def masked_dsn(self) -> str | None:
        """Provide a masked DSN string safe for logging and UI presentation.

        Returns:
            Partially masked DSN string if configured, or None.

        Notes/Architectural Intent:
            Prevents leaking sensitive secret keys in logs and diagnostic interfaces.
        """
        if not self.dsn:
            return None
        if len(self.dsn) <= 18:
            return "***"
        return f"{self.dsn[:14]}...{self.dsn[-6:]}"

    def debug(self, message: str, extra: Extras | None = None) -> None:
        """Log debug message to inner logger."""
        if self.inner_logger:
            self.inner_logger.debug(message, extra=extra)

    def info(self, message: str, extra: Extras | None = None) -> None:
        """Log info message to inner logger."""
        if self.inner_logger:
            self.inner_logger.info(message, extra=extra)

    def warning(self, message: str, extra: Extras | None = None) -> None:
        """Log warning message to inner logger."""
        if self.inner_logger:
            self.inner_logger.warning(message, extra=extra)

    def error(
        self,
        message: str,
        extra: Extras | None = None,
        exc: Exception | None = None,
    ) -> None:
        """Log error and capture in Sentry."""
        if self._sentry_initialized:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                if extra:
                    for k, v in extra.items():
                        scope.set_extra(k, v)
                if exc:
                    sentry_sdk.capture_exception(exc)
                else:
                    sentry_sdk.capture_message(message, level="error")

        if self.inner_logger:
            self.inner_logger.error(message, extra=extra, exc=exc)

    def critical(
        self,
        message: str,
        extra: Extras | None = None,
        exc: Exception | None = None,
    ) -> None:
        """Log critical error and capture in Sentry."""
        if self._sentry_initialized:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                if extra:
                    for k, v in extra.items():
                        scope.set_extra(k, v)
                if exc:
                    sentry_sdk.capture_exception(exc)
                else:
                    sentry_sdk.capture_message(message, level="fatal")

        if self.inner_logger:
            self.inner_logger.critical(message, extra=extra, exc=exc)


__all__ = [
    "default_before_send",
    "SentryErrorAdapter",
]

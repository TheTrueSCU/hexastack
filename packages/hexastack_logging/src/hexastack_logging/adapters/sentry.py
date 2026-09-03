"""Sentry Error Tracking and Exception Forwarding Adapter."""

from __future__ import annotations

import logging

from hexastack_core.ports.logging import Extras, LoggingPort


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
    ) -> None:
        """Initialize SentryErrorAdapter.

        Args:
            dsn: Sentry Data Source Name URL.
            environment: Deployment environment tag (e.g. 'production', 'staging').
            release: Application version or commit SHA.
            sample_rate: Error sampling rate (0.0 to 1.0).
            inner_logger: Optional underlying LoggingPort to delegate standard logging to.
        """
        self.inner_logger = inner_logger
        self.dsn = dsn
        self._sentry_initialized = False

        if dsn:
            try:
                import sentry_sdk

                sentry_sdk.init(
                    dsn=dsn,
                    environment=environment,
                    release=release,
                    sample_rate=sample_rate,
                )
                self._sentry_initialized = True
            except ImportError:
                logging.getLogger("hexastack.sentry").warning(
                    "sentry-sdk not installed; error reporting disabled."
                )

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
    "SentryErrorAdapter",
]

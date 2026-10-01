from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.logging import LoggingPort
from hexastack_logging.adapters.sentry import SentryErrorAdapter
from hexastack_logging.infra.bootstrap import LoggingBootstrapper


def test_logging_bootstrapper():
    bootstrapper = LoggingBootstrapper()
    res = bootstrap(bootstrappers=[bootstrapper], auto_discover=False)

    assert LoggingPort in res.container
    logger = res.container.resolve(LoggingPort)
    assert logger is not None
    assert res.get("logger") is logger


def test_logging_bootstrapper_sentry_auto_wrap(monkeypatch):
    """Verify LoggingBootstrapper auto-wraps with SentryErrorAdapter when SENTRY_DSN is set."""
    monkeypatch.setenv(
        "SENTRY_DSN",
        "https://dummykey1234567890abcdef@o000000.ingest.sentry.io/12345678",
    )
    bootstrapper = LoggingBootstrapper()
    res = bootstrap(bootstrappers=[bootstrapper], auto_discover=False)

    has_port = LoggingPort in res.container
    assert has_port is True
    logger = res.container.resolve(LoggingPort)
    is_sentry = isinstance(logger, SentryErrorAdapter)
    assert is_sentry is True
    masked = getattr(logger, "masked_dsn", None)
    assert masked is not None

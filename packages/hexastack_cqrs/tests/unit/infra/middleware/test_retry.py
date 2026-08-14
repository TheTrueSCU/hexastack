import pytest
from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_core.domain import Command, HexastackError
from hexastack_cqrs.infra.config import RetryMiddlewareConfig
from hexastack_cqrs.infra.middleware.retry import TenacityRetryMiddleware


class _DummyCommand(Command):
    val: int


def test_retry_middleware_defaults():
    middleware = TenacityRetryMiddleware()
    assert middleware._logger is None
    assert middleware._config.enable is True
    assert middleware._config.max_attempts == 3


def test_retries_on_transient_error_and_logs_debug():
    logger = InMemoryLogger()
    config = RetryMiddlewareConfig(enable=True, max_attempts=3)
    middleware = TenacityRetryMiddleware(logger=logger, config=config)
    attempts = 0

    def flaky_handler(cmd: _DummyCommand) -> int:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("transient")
        return cmd.val + 10

    result = middleware(_DummyCommand(val=5), flaky_handler)
    assert result == 15
    assert attempts == 3
    assert len(logger.entries) == 2  # logged debug on retry 1 and 2
    assert all(entry.level == "debug" for entry in logger.entries)


def test_retries_exhausted_raises_exception():
    config = RetryMiddlewareConfig(enable=True, max_attempts=2)
    middleware = TenacityRetryMiddleware(config=config)
    attempts = 0

    def always_failing_handler(cmd: _DummyCommand) -> int:
        nonlocal attempts
        attempts += 1
        raise ValueError("permanent error")

    with pytest.raises(ValueError, match="permanent error"):
        middleware(_DummyCommand(val=0), always_failing_handler)

    assert attempts == 2


def test_skips_retry_when_disabled():
    config = RetryMiddlewareConfig(enable=False)
    middleware = TenacityRetryMiddleware(config=config)
    calls = []

    def handler(cmd: _DummyCommand) -> int:
        calls.append(1)
        return cmd.val

    result = middleware(_DummyCommand(val=7), handler)
    assert result == 7
    assert len(calls) == 1


def test_does_not_retry_hexastack_errors():
    config = RetryMiddlewareConfig(enable=True, max_attempts=5)
    middleware = TenacityRetryMiddleware(config=config)
    attempts = 0

    def handler(cmd: _DummyCommand) -> int:
        nonlocal attempts
        attempts += 1
        raise HexastackError("domain error")

    with pytest.raises(HexastackError):
        middleware(_DummyCommand(val=0), handler)

    assert attempts == 1  # no retries for domain errors

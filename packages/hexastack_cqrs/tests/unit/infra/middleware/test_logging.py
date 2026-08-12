import pytest
from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_core.domain import Command
from hexastack_cqrs.infra.config import LoggingMiddlewareConfig
from hexastack_cqrs.infra.middleware.logging import LoggingMiddleware


class _DummyCommand(Command):
    name: str


def test_logging_middleware_successful_execution():
    logger = InMemoryLogger()
    config = LoggingMiddlewareConfig(enable=True, log_payload=True)
    middleware = LoggingMiddleware(logger=logger, config=config)

    def handler(cmd: _DummyCommand) -> str:
        return f"processed {cmd.name}"

    cmd = _DummyCommand(name="test-command")
    result = middleware(cmd, handler)

    assert result == "processed test-command"
    assert len(logger.entries) == 2
    assert logger.entries[0].level == "info"
    assert "Processing _DummyCommand" in logger.entries[0].message
    assert logger.entries[0].extra is not None
    assert logger.entries[0].extra["payload"] == {"name": "test-command"}
    assert logger.entries[1].level == "debug"
    assert "Successfully completed _DummyCommand" in logger.entries[1].message


def test_logging_middleware_error_execution():
    logger = InMemoryLogger()
    middleware = LoggingMiddleware(logger=logger)

    def failing_handler(cmd: _DummyCommand) -> str:
        raise ValueError("handling failed")

    cmd = _DummyCommand(name="error-cmd")
    with pytest.raises(ValueError, match="handling failed"):
        middleware(cmd, failing_handler)

    assert len(logger.entries) == 2
    assert logger.entries[0].level == "info"
    assert logger.entries[1].level == "error"
    assert "Failed processing _DummyCommand" in logger.entries[1].message


def test_logging_middleware_disabled():
    logger = InMemoryLogger()
    config = LoggingMiddlewareConfig(enable=False)
    middleware = LoggingMiddleware(logger=logger, config=config)

    cmd = _DummyCommand(name="disabled-cmd")
    result = middleware(cmd, lambda c: "ok")

    assert result == "ok"
    assert len(logger.entries) == 0


@pytest.mark.anyio
async def test_logging_middleware_async_coroutine_success():
    logger = InMemoryLogger()
    middleware = LoggingMiddleware(logger=logger)

    async def async_handler(cmd: _DummyCommand) -> str:
        return f"async {cmd.name}"

    cmd = _DummyCommand(name="async-cmd")
    coro = middleware(cmd, async_handler)
    result = await coro

    assert result == "async async-cmd"
    assert len(logger.entries) == 2
    assert logger.entries[0].level == "info"
    assert logger.entries[1].level == "debug"


@pytest.mark.anyio
async def test_logging_middleware_async_coroutine_error():
    logger = InMemoryLogger()
    middleware = LoggingMiddleware(logger=logger)

    async def async_failing_handler(cmd: _DummyCommand) -> str:
        raise RuntimeError("async failure")

    cmd = _DummyCommand(name="async-error-cmd")
    coro = middleware(cmd, async_failing_handler)

    with pytest.raises(RuntimeError, match="async failure"):
        await coro

    assert len(logger.entries) == 2
    assert logger.entries[0].level == "info"
    assert logger.entries[1].level == "error"
    assert "Failed processing _DummyCommand" in logger.entries[1].message

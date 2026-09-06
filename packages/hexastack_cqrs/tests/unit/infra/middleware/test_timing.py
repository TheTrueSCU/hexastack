import asyncio
import time

import pytest

from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_core.domain import Command
from hexastack_cqrs.infra.config import TimingMiddlewareConfig
from hexastack_cqrs.infra.middleware.timing import TimingMiddleware


class _DummyCommand(Command):
    name: str


@pytest.mark.anyio
async def test_timing_middleware_async_coroutine_execution():
    logger = InMemoryLogger()
    config = TimingMiddlewareConfig(
        enable_slow_warning=True, slow_threshold_seconds=0.01
    )
    middleware = TimingMiddleware(logger=logger, config=config)

    async def async_slow_handler(cmd: _DummyCommand) -> str:
        await asyncio.sleep(0.02)
        return "async-slow"

    cmd = _DummyCommand(name="async-cmd")
    coro = middleware(cmd, async_slow_handler)
    result = await coro

    assert result == "async-slow"
    assert len(logger.entries) == 1
    assert logger.entries[0].level == "warning"
    assert "Slow execution detected for _DummyCommand" in logger.entries[0].message


def test_timing_middleware_normal_execution():
    logger = InMemoryLogger()
    config = TimingMiddlewareConfig(
        enable_slow_warning=True, slow_threshold_seconds=1.0
    )
    middleware = TimingMiddleware(logger=logger, config=config)

    def fast_handler(cmd: _DummyCommand) -> str:
        return "fast"

    cmd = _DummyCommand(name="fast-cmd")
    result = middleware(cmd, fast_handler)

    assert result == "fast"
    assert len(logger.entries) == 1
    assert logger.entries[0].level == "info"
    assert "Executed _DummyCommand in" in logger.entries[0].message
    extra = logger.entries[0].extra
    assert extra is not None
    assert "duration_seconds" in extra


def test_timing_middleware_slow_execution_warning():
    logger = InMemoryLogger()
    config = TimingMiddlewareConfig(
        enable_slow_warning=True, slow_threshold_seconds=0.01
    )
    middleware = TimingMiddleware(logger=logger, config=config)

    def slow_handler(cmd: _DummyCommand) -> str:
        time.sleep(0.02)
        return "slow"

    cmd = _DummyCommand(name="slow-cmd")
    result = middleware(cmd, slow_handler)

    assert result == "slow"
    assert len(logger.entries) == 1
    assert logger.entries[0].level == "warning"
    assert "Slow execution detected for _DummyCommand" in logger.entries[0].message


def test_timing_middleware_slow_warning_disabled():
    logger = InMemoryLogger()
    config = TimingMiddlewareConfig(
        enable_slow_warning=False, slow_threshold_seconds=0.01
    )
    middleware = TimingMiddleware(logger=logger, config=config)

    def slow_handler(cmd: _DummyCommand) -> str:
        time.sleep(0.02)
        return "slow"

    cmd = _DummyCommand(name="slow-cmd")
    result = middleware(cmd, slow_handler)

    assert result == "slow"
    assert len(logger.entries) == 1
    assert logger.entries[0].level == "info"
    extra = logger.entries[0].extra
    assert extra is not None
    assert extra["message_type"] == "_DummyCommand"


def test_timing_middleware_on_error():
    logger = InMemoryLogger()
    middleware = TimingMiddleware(logger=logger)  # default config

    def failing_handler(cmd: _DummyCommand) -> str:
        raise ValueError("Handler failed")

    cmd = _DummyCommand(name="err-cmd")
    with pytest.raises(ValueError, match="Handler failed"):
        middleware(cmd, failing_handler)

    assert len(logger.entries) == 1
    assert logger.entries[0].level == "info"
    assert "Executed _DummyCommand in" in logger.entries[0].message
    extra = logger.entries[0].extra
    assert extra is not None
    assert extra["message_type"] == "_DummyCommand"
    assert "duration_seconds" in extra

    # on_error with None context is a safe no-op
    middleware.on_error(cmd, ValueError("error"), context=None)
    assert len(logger.entries) == 1

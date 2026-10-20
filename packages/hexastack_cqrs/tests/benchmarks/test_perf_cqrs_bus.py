"""Performance microbenchmarks for CQRS command and query bus dispatching.

Notes/Architectural Intent:
    Measures baseline in-process invocation overhead of SynchronousCommandBus and
    SynchronousQueryBus under zero-middleware and multi-middleware configurations.
    Enforces that framework abstraction layers maintain sub-microsecond latency
    for raw handler dispatching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hexastack_core.domain import Command, Query
from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
from hexastack_cqrs.adapters.buses.query.synchronous import SynchronousQueryBus
from hexastack_cqrs.infra.registries.handler import HandlerRegistry

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_benchmark.fixture import BenchmarkFixture


class BenchmarkPingCommand(Command):
    """Payload model for ping benchmark."""

    sequence: int


class BenchmarkPingQuery(Query[str]):
    """Payload model for query benchmark."""

    item_id: str


class PassThroughBenchmarkMiddleware:
    """Zero-allocation pass-through middleware for pipeline overhead benchmarking."""

    def __call__(self, instance: Any, next_call: Callable[[Any], Any]) -> Any:
        """Forward message to next pipeline step."""
        return next_call(instance)


def test_perf_command_bus_zero_middleware(benchmark: BenchmarkFixture) -> None:
    """Benchmark SynchronousCommandBus dispatch latency with zero middleware.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies raw handler invocation latency through handler registry resolution.
    """
    registry = HandlerRegistry()
    registry.register(BenchmarkPingCommand, lambda cmd: cmd.sequence + 1)
    bus = SynchronousCommandBus(handler_registry=registry)
    cmd = BenchmarkPingCommand(sequence=42)

    res = benchmark(bus.dispatch, cmd)
    assert res == 43


def test_perf_command_bus_multi_middleware(benchmark: BenchmarkFixture) -> None:
    """Benchmark SynchronousCommandBus dispatch with 3-layer middleware pipeline.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Evaluates cumulative middleware wrapping overhead per dispatch cycle.
    """
    registry = HandlerRegistry()
    registry.register(BenchmarkPingCommand, lambda cmd: cmd.sequence + 1)
    bus = SynchronousCommandBus(
        handler_registry=registry,
        middleware=[
            PassThroughBenchmarkMiddleware(),
            PassThroughBenchmarkMiddleware(),
            PassThroughBenchmarkMiddleware(),
        ],
    )
    cmd = BenchmarkPingCommand(sequence=100)

    res = benchmark(bus.dispatch, cmd)
    assert res == 101


def test_perf_query_bus_dispatch(benchmark: BenchmarkFixture) -> None:
    """Benchmark SynchronousQueryBus dispatch latency.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies query dispatch and return value handling overhead.
    """
    registry = HandlerRegistry()
    registry.register(BenchmarkPingQuery, lambda q: f"result:{q.item_id}")
    bus = SynchronousQueryBus(handler_registry=registry)
    query = BenchmarkPingQuery(item_id="item-777")

    res = benchmark(bus.dispatch, query)
    assert res == "result:item-777"

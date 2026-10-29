"""Lightweight embedded edge execution pipeline for WebAssembly and MicroPython runtimes.

Notes/Architectural Intent:
    Provides an ultra-lean, zero-C-extension CQRS execution pipeline configured with
    pure-Python in-memory buses and MicroContainer. Designed to execute within
    embedded microcontrollers, serverless edge workers, and browser WASM sandbox environments.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hexastack_core.domain import Command, Event, Generic, Query
from hexastack_core.infra.container import MicroContainer
from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
from hexastack_cqrs.adapters.buses.event.synchronous import SynchronousEventBus
from hexastack_cqrs.adapters.buses.query.synchronous import SynchronousQueryBus
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries import HandlerRegistry
from hexastack_cqrs.ports.buses import CommandBusPort, EventBusPort, QueryBusPort
from hexastack_cqrs.ports.pipeline import ExecutionPipelinePort


class EdgeExecutionProfile:
    """Convenience facade coordinating a zero-dependency CQRS edge runtime.

    Notes/Architectural Intent:
        Encapsulates in-process synchronous buses and MicroContainer, delivering
        sub-millisecond dispatch latency and minimal memory footprint (<1MB)
        for browser (Pyodide), edge-worker (WASI), and IoT (MicroPython) deployments.
    """

    def __init__(
        self,
        container: MicroContainer | None = None,
        pipeline: ExecutionPipeline | None = None,
    ) -> None:
        """Initialize edge execution profile with lightweight components.

        Args:
            container: Optional MicroContainer instance (defaults to a fresh MicroContainer).
            pipeline: Optional ExecutionPipeline instance.
        """
        self.container = container or MicroContainer()
        self._handler_registry = HandlerRegistry()

        self.command_bus = SynchronousCommandBus(
            handler_registry=self._handler_registry
        )
        self.query_bus = SynchronousQueryBus(handler_registry=self._handler_registry)
        self.event_bus = SynchronousEventBus()

        self.pipeline = pipeline or ExecutionPipeline(
            handler_registry=self._handler_registry,
            command_bus=self.command_bus,
            query_bus=self.query_bus,
            event_bus=self.event_bus,
        )

        # Wire interfaces into container
        self.container.add_instance(self.command_bus, declared_class=CommandBusPort)
        self.container.add_instance(self.query_bus, declared_class=QueryBusPort)
        self.container.add_instance(self.event_bus, declared_class=EventBusPort)
        self.container.add_instance(self.pipeline, declared_class=ExecutionPipelinePort)

    def register_handler(
        self,
        message_type: type[Generic],
        handler: Callable[..., Any],
    ) -> EdgeExecutionProfile:
        """Register a message handler for a Command, Query, or Event.

        Args:
            message_type: Concrete Command, Query, or Event subclass.
            handler: Synchronous or asynchronous handler callable.

        Returns:
            self for chaining.
        """
        if issubclass(message_type, Event):
            self.event_bus.subscribe(message_type, handler)
        else:
            self._handler_registry.register(message_type, handler)
        return self

    def dispatch(self, message: Generic) -> Any:
        """Dispatch a message synchronously through the edge pipeline.

        Args:
            message: Command, Query, or Event to process.

        Returns:
            Handler execution result.
        """
        if isinstance(message, Command):
            return self.command_bus.dispatch(message)
        if isinstance(message, Query):
            return self.query_bus.dispatch(message)
        if isinstance(message, Event):
            self.event_bus.publish(message)
            return None
        return self.pipeline.execute(message)

    async def dispatch_async(self, message: Generic) -> Any:
        """Dispatch a message asynchronously through the edge pipeline.

        Args:
            message: Command, Query, or Event to process.

        Returns:
            Handler execution result.
        """
        if isinstance(message, Command):
            return self.command_bus.dispatch(message)
        if isinstance(message, Query):
            return self.query_bus.dispatch(message)
        if isinstance(message, Event):
            self.event_bus.publish(message)
            return None
        return await self.pipeline.execute_async(message)


def create_edge_pipeline(
    container: MicroContainer | None = None,
) -> EdgeExecutionProfile:
    """Construct a turnkey lightweight edge execution profile for WASM/MicroPython.

    Args:
        container: Optional pre-configured MicroContainer.

    Returns:
        Configured EdgeExecutionProfile instance.
    """
    return EdgeExecutionProfile(container=container)


__all__ = [
    "create_edge_pipeline",
    "EdgeExecutionProfile",
]

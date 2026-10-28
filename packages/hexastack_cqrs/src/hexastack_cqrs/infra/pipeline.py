import inspect
from typing import Any

from hexastack_core.domain import Command, Event, Generic, HexastackError, Query
from hexastack_core.infra import ExceptionRegistry
from hexastack_core.utils.concurrency import (
    asyncify,
    is_coroutine_callable,
)
from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.adapters.buses.event.synchronous import (
    SynchronousEventBus,
)
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.registries import (
    CommandRegistry,
    HandlerRegistry,
    PresenterRegistry,
    QueryRegistry,
)
from hexastack_cqrs.ports.buses import (
    CommandBusPort,
    EventBusPort,
    QueryBusPort,
)
from hexastack_cqrs.ports.pipeline import ExecutionPipelinePort


class PipelineError(HexastackError):
    """Exception raised when message routing, resolution, or execution fails within the pipeline.

    Notes/Architectural Intent:
        Specializes HexastackError for pipeline-level dispatch, resolution, and routing errors.
    """


class AmbiguousMessageError(PipelineError):
    """Exception raised when a message name matches multiple type registries.

    Notes/Architectural Intent:
        Prevents silent ambiguity when a name is registered in both command and query registries.
    """


class UnregisteredMessageError(PipelineError):
    """Exception raised when no Command or Query is registered for the requested name.

    Notes/Architectural Intent:
        Signals lookup failure when dynamically instantiating messages from name strings.
    """


class ExecutionPipeline(ExecutionPipelinePort):
    """End-to-end CQRS execution pipeline integrating buses, registries, and presenters.

    Notes/Architectural Intent:
        Unified entry point for dispatching Generic messages, routing by lifecycle type
        via pattern matching, managing presentation conversion, and applying exception mapping.
    """

    def __init__(
        self,
        handler_registry: HandlerRegistry,
        command_registry: CommandRegistry | None = None,
        query_registry: QueryRegistry | None = None,
        presenter_registry: PresenterRegistry | None = None,
        exception_registry: ExceptionRegistry | None = None,
        command_bus: CommandBusPort | None = None,
        query_bus: QueryBusPort | None = None,
        event_bus: EventBusPort | None = None,
    ) -> None:
        """Initialize ExecutionPipeline with registries and optional buses.

        Args:
            handler_registry: HandlerRegistry mapping message classes to handler functions.
            command_registry: Optional CommandRegistry for string-to-class lookup.
            query_registry: Optional QueryRegistry for string-to-class lookup.
            presenter_registry: Optional PresenterRegistry for response formatting.
            exception_registry: Optional ExceptionRegistry for error interception and mapping.
            command_bus: Optional custom CommandBusPort implementation.
            query_bus: Optional custom QueryBusPort implementation.
            event_bus: Optional custom EventBusPort implementation.
        """
        self._handler_registry = handler_registry
        self._command_registry = command_registry or CommandRegistry()
        self._query_registry = query_registry or QueryRegistry()
        self._presenter_registry = presenter_registry or PresenterRegistry()
        self._exception_registry = exception_registry

        self._command_bus = command_bus or SynchronousCommandBus(handler_registry)
        self._query_bus = query_bus or SynchronousQueryBus(handler_registry)
        self._event_bus = event_bus or SynchronousEventBus()

    def execute(
        self,
        instance: Generic,
        output_format: str | None = None,
    ) -> Any:
        """Execute a Generic instance by routing to the appropriate bus and presenting output.

        Args:
            instance: Command, Query, Event, or Generic instance to execute.
            output_format: Optional format string for presenter (e.g. 'json', 'html').

        Returns:
            The presented result, raw execution result, or None for events.

        Raises:
            Exception: Propagates unhandled exceptions if unmapped by exception registry.
        """
        try:
            if isinstance(instance, Command):
                raw_result = self._command_bus.dispatch(instance)
            elif isinstance(instance, Query):
                raw_result = self._query_bus.dispatch(instance)
            elif isinstance(instance, Event):
                self._event_bus.publish(instance)
                raw_result = None
            else:
                raw_result = self._handler_registry.handle(instance, reraise=True)

            if output_format is not None and isinstance(raw_result, Generic):
                presented = self._presenter_registry.present(
                    raw_result, output_format, reraise=False
                )
                return presented if presented is not None else raw_result

            return raw_result

        except Exception as exc:
            if self._exception_registry is not None and (
                error_data := self._exception_registry.handle(exc, reraise=False)
            ):
                return error_data
            raise

    def execute_by_name(
        self,
        name: str,
        payload: dict[str, Any],
        output_format: str | None = None,
    ) -> Any:
        """Instantiate and execute a registered Command or Query by string name and payload.

        Args:
            name: Registered class name identifier.
            payload: Parameter dictionary to validate into the message model.
            output_format: Optional presenter format string.

        Returns:
            The presented or raw execution result.

        Raises:
            AmbiguousMessageError: If name is registered in multiple type registries.
            UnregisteredMessageError: If name is not registered in any type registry.
        """
        matches = [
            reg.get(name)
            for reg in (self._command_registry, self._query_registry)
            if name in reg
        ]

        if len(matches) > 1:
            raise AmbiguousMessageError(
                f"Ambiguous message name '{name}': registered in multiple type registries."
            )

        if matches:
            cls = matches[0]
            return self.execute(
                cls.model_validate(payload), output_format=output_format
            )

        raise UnregisteredMessageError(
            f"No Command or Query registered with name '{name}'"
        )

    async def execute_async(
        self,
        instance: Generic,
        output_format: str | None = None,
    ) -> Any:
        """Asynchronously execute a Generic instance without blocking the active event loop.

        Args:
            instance: Command, Query, Event, or Generic instance to execute.
            output_format: Optional format string for presenter (e.g. 'json', 'html').

        Returns:
            The presented result, raw execution result, or None for events.

        Raises:
            Exception: Propagates unhandled exceptions if unmapped by exception registry.

        Notes/Architectural Intent:
            Checks whether the registered handler is an asynchronous coroutine callable.
            If async, invokes and awaits it natively on the event loop. If synchronous, offloads
            execution to a worker thread via `asyncify`, ensuring non-blocking event-loop operation
            with ambient context variable preservation.
        """
        handler = self._handler_registry.get(type(instance))
        if handler is not None and is_coroutine_callable(handler):
            try:
                coro_or_res = self.execute(instance, output_format=None)
                if inspect.iscoroutine(coro_or_res):
                    raw_result = await coro_or_res
                else:
                    raw_result = coro_or_res

                if output_format is not None and isinstance(raw_result, Generic):
                    presented = self._presenter_registry.present(
                        raw_result, output_format, reraise=False
                    )
                    return presented if presented is not None else raw_result

                return raw_result
            except Exception as exc:
                if self._exception_registry is not None and (
                    error_data := self._exception_registry.handle(exc, reraise=False)
                ):
                    return error_data
                raise

        return await asyncify(self.execute)(instance, output_format=output_format)

    async def execute_by_name_async(
        self,
        name: str,
        payload: dict[str, Any],
        output_format: str | None = None,
    ) -> Any:
        """Asynchronously instantiate and execute a registered Command or Query.

        Args:
            name: Registered class name identifier.
            payload: Parameter dictionary to validate into the message model.
            output_format: Optional presenter format string.

        Returns:
            The presented or raw execution result.

        Raises:
            AmbiguousMessageError: If name is registered in multiple type registries.
            UnregisteredMessageError: If name is not registered in any type registry.
        """
        matches = [
            reg.get(name)
            for reg in (self._command_registry, self._query_registry)
            if name in reg
        ]

        if len(matches) > 1:
            raise AmbiguousMessageError(
                f"Ambiguous message name '{name}': registered in multiple type registries."
            )

        if matches:
            cls = matches[0]
            return await self.execute_async(
                cls.model_validate(payload), output_format=output_format
            )

        raise UnregisteredMessageError(
            f"No Command or Query registered with name '{name}'"
        )

    def get_registered_commands(self) -> dict[str, type[Command]]:
        """Return a mapping of registered command names to their command classes.

        Returns:
            Dictionary mapping string names to Command classes.
        """
        return dict(self._command_registry.all)

    def get_registered_queries(self) -> dict[str, type[Query[Any]]]:
        """Return a mapping of registered query names to their query classes.

        Returns:
            Dictionary mapping string names to Query classes.
        """
        return dict(self._query_registry.all)


__all__ = [
    "AmbiguousMessageError",
    "create_pipeline",
    "ExecutionPipeline",
    "PipelineError",
    "UnregisteredMessageError",
]


def create_pipeline(
    handler_registry: HandlerRegistry | None = None,
    command_registry: CommandRegistry | None = None,
    query_registry: QueryRegistry | None = None,
    presenter_registry: PresenterRegistry | None = None,
    exception_registry: ExceptionRegistry | None = None,
    command_bus: CommandBusPort | None = None,
    query_bus: QueryBusPort | None = None,
    event_bus: EventBusPort | None = None,
) -> ExecutionPipeline:
    """Factory function creating an ExecutionPipeline with default registries and buses.

    Args:
        handler_registry: Optional HandlerRegistry (defaults to empty registry).
        command_registry: Optional CommandRegistry.
        query_registry: Optional QueryRegistry.
        presenter_registry: Optional PresenterRegistry.
        exception_registry: Optional ExceptionRegistry.
        command_bus: Optional custom CommandBusPort.
        query_bus: Optional custom QueryBusPort.
        event_bus: Optional custom EventBusPort.

    Returns:
        Configured ExecutionPipeline instance.
    """
    return ExecutionPipeline(
        handler_registry=handler_registry or HandlerRegistry(),
        command_registry=command_registry,
        query_registry=query_registry,
        presenter_registry=presenter_registry,
        exception_registry=exception_registry,
        command_bus=command_bus,
        query_bus=query_bus,
        event_bus=event_bus,
    )

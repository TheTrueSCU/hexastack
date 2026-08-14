import importlib.util
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from hexastack_core.domain import Command, Generic
from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_cqrs.infra.middleware.generic import GenericMiddleware
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.ports.buses import CommandBusPort

if TYPE_CHECKING:
    from huey import Huey


class HueyCommandBus(CommandBusPort):
    """Asynchronous CommandBus adapter dispatching commands via Huey task queue.

    Notes/Architectural Intent:
        Delegates command execution to background worker processes via Huey,
        enabling distributed, durable asynchronous background processing.
        Requires hexastack-cqrs[huey].
    """

    def __init__(
        self,
        huey: "Huey",
        handler_registry: HandlerRegistry,
        middleware: list[GenericMiddleware] | None = None,
    ) -> None:
        """Initialize Huey command bus with Huey instance and handler registry.

        Args:
            huey: Initialized Huey task queue instance.
            handler_registry: HandlerRegistry containing registered command handlers.
            middleware: Optional ordered list of GenericMiddleware interceptors.

        Raises:
            MissingDependencyError: If huey package is not installed.
        """
        if importlib.util.find_spec("huey") is None:
            raise MissingDependencyError(
                "huey is required to use HueyCommandBus. "
                "Install via 'pip install hexastack-cqrs[huey]'."
            )

        self._huey = huey
        self._registry = handler_registry
        self._middleware = list(middleware) if middleware is not None else []

        @self._huey.task()
        def _execute_command_task(cmd: Command) -> Any:
            pipeline: Callable[[Generic], Any] = lambda inst: self._registry.handle(
                inst, reraise=True
            )
            for mw in reversed(self._middleware):
                next_fn = pipeline
                pipeline = lambda inst, m=mw, n=next_fn: m(inst, n)
            return pipeline(cmd)

        self._task_fn = _execute_command_task

    def dispatch(self, command: Command) -> Any:
        """Enqueue command to Huey background queue for execution.

        Args:
            command: The command instance to enqueue.

        Returns:
            Huey Task object representing the background job.

        Raises:
            Exception: If enqueuing to Huey queue fails.
        """
        return self._task_fn(command)


class AsyncNativeCommandBus(CommandBusPort):
    """Asynchronous in-process CommandBus using thread pool execution.

    Notes/Architectural Intent:
        Provides non-blocking in-process command execution without requiring external
        queue backends, returning a standard concurrent.futures.Future.
    """

    def __init__(
        self,
        handler_registry: HandlerRegistry,
        middleware: list[GenericMiddleware] | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        """Initialize native async command bus.

        Args:
            handler_registry: HandlerRegistry containing registered command handlers.
            middleware: Optional ordered list of GenericMiddleware interceptors.
            executor: Optional ThreadPoolExecutor for managing worker threads.
        """
        self._registry = handler_registry
        self._middleware = list(middleware) if middleware is not None else []
        self._executor = executor or ThreadPoolExecutor(thread_name_prefix="cqrs-async")

    def dispatch(self, command: Command) -> Future[Any]:
        """Submit command for asynchronous background execution on thread pool.

        Args:
            command: The command instance to dispatch.

        Returns:
            Future resolving to the handler execution result.

        Raises:
            Exception: If submitting task to thread pool executor fails.
        """

        def _run() -> Any:
            pipeline: Callable[[Generic], Any] = lambda inst: self._registry.handle(
                inst, reraise=True
            )
            for mw in reversed(self._middleware):
                next_fn = pipeline
                pipeline = lambda inst, m=mw, n=next_fn: m(inst, n)
            return pipeline(command)

        return self._executor.submit(_run)


__all__ = [
    "HueyCommandBus",
    "AsyncNativeCommandBus",
]

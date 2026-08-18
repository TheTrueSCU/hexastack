import inspect
from collections.abc import Callable
from typing import Any, cast

from hexastack_core.domain import Generic
from hexastack_core.ports.unit_of_work import UnitOfWorkPort


class UnitOfWorkMiddleware:
    """Middleware wrapping message execution in a Unit of Work transactional boundary.

    Notes/Architectural Intent:
        Enforces atomic commit on successful handler completion and rollback on exception.
        Supports both direct UnitOfWorkPort instances and factory callables, seamlessly
        managing transactional context for synchronous and asynchronous coroutine handlers.
    """

    def __init__(
        self,
        uow: UnitOfWorkPort | Callable[[], UnitOfWorkPort],
    ) -> None:
        """Initialize UnitOfWorkMiddleware with a UnitOfWorkPort instance or factory.

        Args:
            uow: UnitOfWorkPort instance or factory callable returning a UnitOfWorkPort.
        """
        self._uow_or_factory = uow

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        """Execute next_call inside a Unit of Work transactional lifecycle.

        Args:
            instance: The command or message Generic instance.
            next_call: Callable representing the remaining middleware/handler chain.

        Returns:
            The handler execution result of type R (or coroutine if next_call is async).

        Raises:
            Exception: Propagates unhandled exceptions after executing transactional rollback.
        """
        uow = self._resolve_uow()
        uow.__enter__()

        try:
            result = next_call(instance)
        except Exception as exc:
            uow.__exit__(type(exc), exc, exc.__traceback__)
            raise

        if inspect.iscoroutine(result):

            async def _async_wrapped() -> Any:
                try:
                    res = await result
                    uow.__exit__(None, None, None)
                    return res
                except Exception as async_exc:
                    uow.__exit__(type(async_exc), async_exc, async_exc.__traceback__)
                    raise

            return cast("R", _async_wrapped())

        uow.__exit__(None, None, None)
        return result

    def _resolve_uow(self) -> UnitOfWorkPort:
        """Resolve an active UnitOfWorkPort instance.

        Returns:
            UnitOfWorkPort instance.
        """
        if isinstance(self._uow_or_factory, UnitOfWorkPort):
            return self._uow_or_factory
        return self._uow_or_factory()

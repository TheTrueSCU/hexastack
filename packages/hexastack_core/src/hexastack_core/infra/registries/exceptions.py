from collections.abc import Callable
from typing import Any

from hexastack_core.domain import HexastackError

type ExceptionPayload = dict[str, Any]
type ExceptionHandler = Callable[[Exception], ExceptionPayload]
type ExceptionMapper = dict[type[Exception], ExceptionHandler]


class ExceptionRegistryError(HexastackError):
    def __init__(self, exc_type: type[Exception]):
        message = f"No handler registered for '{exc_type.__name__}'"
        super().__init__(message)
        

def _handle_unmapped_exception(exc: Exception, reraise: bool) -> None:
    if reraise:
        raise ExceptionRegistryError(type(exc)) from exc



class ExceptionRegistry:
    def __init__(self):
        self._mapper: ExceptionMapper = {}

    def handle_exception(self, exc: Exception, exact: bool = False, reraise: bool = False) -> ExceptionPayload | None:
        if handler := self._mapper.get(type(exc)):
            return handler(exc)

        if exact:
            return _handle_unmapped_exception(exc, reraise)

        for exc_type, handler in self._mapper.items():
            if isinstance(exc, exc_type):
                return handler(exc)

        return _handle_unmapped_exception(exc, reraise)

    def register_exception_handler(self, exc_type: type[Exception], handler: ExceptionHandler) -> None:
        self._mapper[exc_type] = handler

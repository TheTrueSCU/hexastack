from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from hexastack_core.domain import HexastackError


class UnitOfWorkError(HexastackError):
    pass


class UnitOfWorkPort(ABC):
    def __init__(self, reraise: bool = False):
        self._reraise = reraise

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, trace: TracebackType | None) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

            if self._reraise:
                raise UnitOfWorkError() from exc

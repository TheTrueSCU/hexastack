from abc import ABC, abstractmethod
from typing import Any

type Extras = dict[str, Any]

class LoggingPort(ABC):
    @abstractmethod
    def debug(self, message: str, extra: Extras | None = None) -> None: ...

    @abstractmethod
    def error(self, message: str, extra: Extras | None = None, exc: Exception | None = None) -> None: ...

    @abstractmethod
    def info(self, message: str, extra: Extras | None = None) -> None: ...

    @abstractmethod
    def warning(self, message: str, extra: Extras | None = None) -> None: ...

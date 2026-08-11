from abc import ABC, abstractmethod
from typing import Any


class Presenter[T](ABC):
    @abstractmethod
    def present(self, data: Any) -> T: ...

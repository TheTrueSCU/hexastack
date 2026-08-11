from abc import ABC, abstractmethod
from typing import TypeVar

E = TypeVar("E")
ID = TypeVar("ID")

class Repository[E, ID](ABC):
    @abstractmethod
    def add(self, entity: E) -> None: ...

    @abstractmethod
    def get_by_id(self, entity_id: ID) -> E | None: ...

    @abstractmethod
    def remove(self, entity_id: ID) -> None: ...

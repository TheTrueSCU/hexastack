from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)

class LlmProviderPort(ABC):
    @abstractmethod
    def generate_structured(self, prompt: str, response_schema: type[M]) -> M: ...

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str: ...


type Metadata = dict[str, Any]


class VectorStorePort(ABC):
    @abstractmethod
    def search(self, query_embedding = list[float], limit: int = 5) -> list[Metadata]: ...

    @abstractmethod
    def upsert(self, vector_id: str, embedding: list[float], metadata: Metadata) -> None: ...

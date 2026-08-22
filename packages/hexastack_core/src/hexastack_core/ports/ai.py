from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from pydantic import BaseModel

Metadata: TypeAlias = dict[str, Any]


class LlmProviderPort(ABC):
    """Abstract interface defining LLM interaction operations.

    Notes/Architectural Intent:
        Decouples application logic from specific LLM providers (e.g. Gemini, OpenAI)
        to allow vendor swapping and testing via mock implementations.
    """

    @abstractmethod
    def generate_structured(
        self, prompt: str, response_schema: type[BaseModel]
    ) -> BaseModel:
        """Generate structured output adhering to a Pydantic schema.

        Args:
            prompt: The user prompt input text.
            response_schema: The Pydantic model class defining output structure.

        Returns:
            An instance of response_schema populated with generated data.

        Raises:
            ValueError: If generation or schema parsing fails.
        """
        ...

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate unstructured text from a prompt.

        Args:
            prompt: The user prompt text.
            system_prompt: Optional system prompt to instruct model behavior.

        Returns:
            The generated text string.

        Raises:
            ValueError: If generation fails.
        """
        ...


class VectorStorePort(ABC):
    """Abstract interface defining vector database operations.

    Notes/Architectural Intent:
        Provides a storage-agnostic interface for vector embeddings retrieval and persistence,
        ensuring domain modules remain uncoupled from vector database vendor specifics.
    """

    @abstractmethod
    def search(self, query_embedding: list[float], limit: int = 5) -> list[Metadata]:
        """Search for vector entries similar to query_embedding.

        Args:
            query_embedding: Floating-point vector representing the query.
            limit: Maximum number of match results to return. Defaults to 5.

        Returns:
            List of metadata dictionaries corresponding to matching vectors.

        Raises:
            ValueError: If vector search operation fails.
        """
        ...

    @abstractmethod
    def upsert(
        self, vector_id: str, embedding: list[float], metadata: Metadata
    ) -> None:
        """Upsert a vector embedding and metadata record into the store.

        Args:
            vector_id: Unique string identifier for the vector.
            embedding: Floating-point vector data.
            metadata: Associated metadata dictionary.

        Returns:
            None.

        Raises:
            ValueError: If vector upsert operation fails.
        """
        ...

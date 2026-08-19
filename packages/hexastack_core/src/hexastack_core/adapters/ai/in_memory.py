import math
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from hexastack_core.ports.ai import LlmProviderPort, Metadata, VectorStorePort


@dataclass
class LlmCallRecord:
    """Record of an invocation made to InMemoryLlmProvider."""

    prompt: str
    system_prompt: str | None = None
    response_schema: type[BaseModel] | None = None
    response: Any = None


class InMemoryLlmProvider(LlmProviderPort):
    """In-memory LLM provider adapter for unit testing and local development.

    Notes/Architectural Intent:
        Implements LlmProviderPort, allowing tests to mock text and structured responses,
        inspect invocation history, and simulate errors without API keys or external services.
    """

    def __init__(
        self,
        default_text: str = "Mock LLM text response",
        default_structured: BaseModel | None = None,
    ) -> None:
        """Initialize InMemoryLlmProvider with optional default responses."""
        self._default_text = default_text
        self._default_structured = default_structured
        self._text_responses: dict[str, str] = {}
        self._structured_responses: dict[type[BaseModel], BaseModel] = {}
        self._simulated_error: Exception | None = None
        self.history: list[LlmCallRecord] = []

    def add_structured_response(
        self, schema_cls: type[BaseModel], response: BaseModel
    ) -> None:
        """Map a response schema class to a specific model response instance."""
        self._structured_responses[schema_cls] = response

    def add_text_response(self, prompt_substring: str, response: str) -> None:
        """Map a prompt substring to a specific text response."""
        self._text_responses[prompt_substring] = response

    def clear(self) -> None:
        """Reset all mock history and mappings."""
        self.history.clear()
        self._text_responses.clear()
        self._structured_responses.clear()
        self._simulated_error = None

    def _synthesize_mock_instance(self, response_schema: type[BaseModel]) -> BaseModel:
        """Synthesize mock field values for a required Pydantic model schema."""
        try:
            return response_schema()
        except Exception:  # noqa: BLE001
            init_data = {}
            for name, field_info in response_schema.model_fields.items():
                if field_info.annotation is str:
                    init_data[name] = f"Mock {name}"
                elif field_info.annotation in (int, float):
                    init_data[name] = 1
                elif field_info.annotation is bool:
                    init_data[name] = True
                else:
                    init_data[name] = None
            return response_schema.model_validate(init_data)

    def generate_structured(
        self,
        prompt: str,
        response_schema: type[BaseModel],
        system_prompt: str | None = None,
    ) -> BaseModel:
        """Generate a structured Pydantic model response."""
        if self._simulated_error is not None:
            raise self._simulated_error

        res: BaseModel
        if response_schema in self._structured_responses:
            res = self._structured_responses[response_schema]
        elif self._default_structured is not None and isinstance(
            self._default_structured, response_schema
        ):
            res = self._default_structured
        else:
            res = self._synthesize_mock_instance(response_schema)

        record = LlmCallRecord(
            prompt=prompt,
            response_schema=response_schema,
            response=res,
        )
        self.history.append(record)
        return res

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate text from prompt or match configured mock responses."""
        if self._simulated_error is not None:
            raise self._simulated_error

        # Check explicit prompt substring mappings
        response_text = self._default_text
        for sub, resp in self._text_responses.items():
            if sub in prompt:
                response_text = resp
                break

        record = LlmCallRecord(
            prompt=prompt,
            system_prompt=system_prompt,
            response=response_text,
        )
        self.history.append(record)
        return response_text

    def set_default_structured(self, model: BaseModel) -> None:
        """Set the fallback structured model response."""
        self._default_structured = model

    def set_default_text(self, text: str) -> None:
        """Set the fallback text response."""
        self._default_text = text

    def set_error(self, error: Exception | None) -> None:
        """Set a simulated exception to raise on subsequent generation calls."""
        self._simulated_error = error


class InMemoryVectorStore(VectorStorePort):
    """In-memory vector store adapter computing cosine similarity.

    Notes/Architectural Intent:
        Implements VectorStorePort with dictionary-backed in-memory vector storage
        and exact cosine similarity search for local development and testing.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory vector store."""
        self._vectors: dict[str, tuple[list[float], Metadata]] = {}

    def clear(self) -> None:
        """Clear all stored vectors."""
        self._vectors.clear()

    def delete(self, vector_id: str) -> bool:
        """Delete a vector by ID."""
        return self._vectors.pop(vector_id, None) is not None

    def get(self, vector_id: str) -> tuple[list[float], Metadata] | None:
        """Retrieve stored embedding and metadata for a vector ID."""
        return self._vectors.get(vector_id)

    def search(self, query_embedding: list[float], limit: int = 5) -> list[Metadata]:
        """Search for top similar vectors using cosine similarity."""
        if not self._vectors:
            return []

        def cosine_similarity(v1: list[float], v2: list[float]) -> float:
            dot = sum(a * b for a, b in zip(v1, v2, strict=False))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            if norm1 == 0.0 or norm2 == 0.0:
                return 0.0
            return dot / (norm1 * norm2)

        scored = []
        for vid, (emb, meta) in self._vectors.items():
            sim = cosine_similarity(query_embedding, emb)
            meta_with_id = dict(meta)
            meta_with_id["_id"] = vid
            meta_with_id["_score"] = sim
            scored.append((sim, meta_with_id))

        # Sort descending by similarity score
        scored.sort(key=lambda item: item[0], reverse=True)
        return [meta for _, meta in scored[:limit]]

    def upsert(
        self, vector_id: str, embedding: list[float], metadata: Metadata
    ) -> None:
        """Store or update vector embedding and metadata."""
        self._vectors[vector_id] = (list(embedding), dict(metadata))


__all__ = [
    "InMemoryLlmProvider",
    "InMemoryVectorStore",
    "LlmCallRecord",
]

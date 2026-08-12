from hexastack_core.ports.ai import LlmProviderPort, Metadata, VectorStorePort
from pydantic import BaseModel


class DummySchema(BaseModel):
    summary: str


class MockLlmProvider(LlmProviderPort):
    def generate_structured(
        self, prompt: str, response_schema: type[BaseModel]
    ) -> BaseModel:
        return response_schema.model_validate({"summary": f"Summary of: {prompt}"})

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        return f"Echo: {prompt}"


class MockVectorStore(VectorStorePort):
    def __init__(self) -> None:
        self.store: dict[str, tuple[list[float], Metadata]] = {}

    def search(self, query_embedding: list[float], limit: int = 5) -> list[Metadata]:
        return [meta for _, meta in list(self.store.values())[:limit]]

    def upsert(
        self, vector_id: str, embedding: list[float], metadata: Metadata
    ) -> None:
        self.store[vector_id] = (embedding, metadata)


def test_mock_llm_provider():
    provider = MockLlmProvider()
    res = provider.generate_structured("test prompt", DummySchema)
    assert isinstance(res, DummySchema)
    assert res.summary == "Summary of: test prompt"

    text = provider.generate_text("hello")
    assert text == "Echo: hello"


def test_mock_vector_store():
    store = MockVectorStore()
    store.upsert("v1", [0.1, 0.2], {"doc": "doc1"})

    results = store.search([0.1, 0.2], limit=1)
    assert len(results) == 1
    assert results[0]["doc"] == "doc1"

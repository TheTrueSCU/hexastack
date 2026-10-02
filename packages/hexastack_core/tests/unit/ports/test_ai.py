from pydantic import BaseModel

from hexastack_core.adapters.ai import InMemoryLlmProvider, InMemoryVectorStore
from hexastack_core.ports.ai import LlmProviderPort, VectorStorePort


class DummySchema(BaseModel):
    summary: str


def test_mock_llm_provider():
    provider: LlmProviderPort = InMemoryLlmProvider()
    res = provider.generate_structured("test prompt", DummySchema)
    assert isinstance(res, DummySchema)
    assert res.summary == "Mock summary"

    text = provider.generate_text("hello")
    assert text == "Mock LLM text response"


def test_mock_vector_store():
    store: VectorStorePort = InMemoryVectorStore()
    store.upsert("v1", [0.1, 0.2], {"doc": "doc1"})

    results = store.search([0.1, 0.2], limit=1)
    assert len(results) == 1
    assert results[0]["doc"] == "doc1"

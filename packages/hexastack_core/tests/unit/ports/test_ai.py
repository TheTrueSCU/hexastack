import inspect

import pytest
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


def test_llm_provider_port_is_abstract() -> None:
    """Verify that LlmProviderPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(LlmProviderPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        LlmProviderPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_llm_provider_port_abstract_methods() -> None:
    """Verify abstract methods on LlmProviderPort."""
    expected = {"generate_structured", "generate_text"}
    abstracts = LlmProviderPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_vector_store_port_is_abstract() -> None:
    """Verify that VectorStorePort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(VectorStorePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        VectorStorePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_vector_store_port_abstract_methods() -> None:
    """Verify abstract methods on VectorStorePort."""
    expected = {"search", "upsert"}
    abstracts = VectorStorePort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0

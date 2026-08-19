import pytest
from pydantic import BaseModel

from hexastack_core.adapters.ai import (
    InMemoryLlmProvider,
    InMemoryVectorStore,
)


class SummarizeOutput(BaseModel):
    summary: str
    confidence: float


def test_in_memory_llm_provider_simulated_error():
    llm = InMemoryLlmProvider()
    llm.set_error(RuntimeError("API quota exceeded"))

    with pytest.raises(RuntimeError, match="API quota exceeded"):
        llm.generate_text("Hello")

    with pytest.raises(RuntimeError, match="API quota exceeded"):
        llm.generate_structured("Hello", SummarizeOutput)

    llm.clear()
    assert llm.generate_text("Hello") == "Mock LLM text response"


def test_in_memory_llm_provider_structured():
    llm = InMemoryLlmProvider()

    canned = SummarizeOutput(summary="Great article", confidence=0.95)
    llm.add_structured_response(SummarizeOutput, canned)

    res = llm.generate_structured("Summarize this text", SummarizeOutput)
    assert isinstance(res, SummarizeOutput)
    assert res.summary == "Great article"
    assert res.confidence == 0.95


def test_in_memory_llm_provider_text_and_rules():
    llm = InMemoryLlmProvider(default_text="General default")

    # Default generation
    assert llm.generate_text("Hi there") == "General default"
    assert len(llm.history) == 1
    assert llm.history[0].prompt == "Hi there"

    # Custom text response rule
    llm.add_text_response("weather", "The weather is sunny")
    assert llm.generate_text("What is the weather today?") == "The weather is sunny"
    assert len(llm.history) == 2


def test_in_memory_vector_store_upsert_and_similarity_search():
    store = InMemoryVectorStore()

    # Insert 3 vectors:
    # v1: points mainly along x-axis [1.0, 0.0]
    # v2: points along 45-deg line [0.707, 0.707]
    # v3: points along y-axis [0.0, 1.0]
    store.upsert("doc1", [1.0, 0.0], {"title": "Doc 1 - X axis"})
    store.upsert("doc2", [0.707, 0.707], {"title": "Doc 2 - Diagonal"})
    store.upsert("doc3", [0.0, 1.0], {"title": "Doc 3 - Y axis"})

    # Query closest to x-axis
    results = store.search([0.95, 0.05], limit=2)
    assert len(results) == 2
    assert results[0]["_id"] == "doc1"
    assert results[0]["title"] == "Doc 1 - X axis"
    assert results[1]["_id"] == "doc2"

    # Query closest to y-axis
    results_y = store.search([0.0, 1.0], limit=1)
    assert len(results_y) == 1
    assert results_y[0]["_id"] == "doc3"

    # Test get, delete, clear
    assert store.get("doc1") is not None
    assert store.delete("doc1") is True
    assert store.get("doc1") is None
    store.clear()
    assert len(store.search([1.0, 0.0])) == 0

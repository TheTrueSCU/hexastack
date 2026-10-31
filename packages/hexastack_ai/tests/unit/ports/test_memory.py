"""Unit tests for AI vector memory and semantic cache abstract ports."""

import inspect

import pytest

from hexastack_ai.ports.memory import (
    AsyncSemanticCachePort,
    AsyncVectorMemoryPort,
    SemanticCachePort,
    VectorMemoryPort,
)


def test_vector_memory_port_is_abstract() -> None:
    """Verify that VectorMemoryPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(VectorMemoryPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        VectorMemoryPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_vector_memory_port_abstract_methods() -> None:
    """Verify abstract methods on VectorMemoryPort."""
    expected = {"clear", "delete", "get", "search", "store"}
    abstracts = VectorMemoryPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_async_vector_memory_port_is_abstract() -> None:
    """Verify that AsyncVectorMemoryPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncVectorMemoryPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncVectorMemoryPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_vector_memory_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncVectorMemoryPort."""
    expected = {"clear", "delete", "get", "search", "store"}
    abstracts = AsyncVectorMemoryPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_semantic_cache_port_is_abstract() -> None:
    """Verify that SemanticCachePort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(SemanticCachePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        SemanticCachePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_semantic_cache_port_abstract_methods() -> None:
    """Verify abstract methods on SemanticCachePort."""
    expected = {"clear", "get", "set"}
    abstracts = SemanticCachePort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_async_semantic_cache_port_is_abstract() -> None:
    """Verify that AsyncSemanticCachePort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncSemanticCachePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncSemanticCachePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_semantic_cache_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncSemanticCachePort."""
    expected = {"clear", "get", "set"}
    abstracts = AsyncSemanticCachePort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0

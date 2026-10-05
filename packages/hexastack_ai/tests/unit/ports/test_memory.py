"""Unit tests for AI vector memory and semantic cache abstract ports."""

import pytest

from hexastack_ai.ports.memory import (
    AsyncSemanticCachePort,
    AsyncVectorMemoryPort,
    SemanticCachePort,
    VectorMemoryPort,
)


def test_vector_memory_port_is_abstract() -> None:
    """Verify VectorMemoryPort cannot be instantiated directly without abstract method overrides."""
    with pytest.raises(TypeError):
        VectorMemoryPort()  # ty: ignore[call-non-callable]


def test_async_vector_memory_port_is_abstract() -> None:
    """Verify AsyncVectorMemoryPort cannot be instantiated directly without abstract method overrides."""
    with pytest.raises(TypeError):
        AsyncVectorMemoryPort()  # ty: ignore[call-non-callable]


def test_semantic_cache_port_is_abstract() -> None:
    """Verify SemanticCachePort cannot be instantiated directly without abstract method overrides."""
    with pytest.raises(TypeError):
        SemanticCachePort()  # ty: ignore[call-non-callable]


def test_async_semantic_cache_port_is_abstract() -> None:
    """Verify AsyncSemanticCachePort cannot be instantiated directly without abstract method overrides."""
    with pytest.raises(TypeError):
        AsyncSemanticCachePort()  # ty: ignore[call-non-callable]

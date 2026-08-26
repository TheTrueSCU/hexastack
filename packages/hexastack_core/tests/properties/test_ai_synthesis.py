"""Property-based invariant tests for InMemoryLlmProvider dynamic schema synthesis.

Notes/Architectural Intent:
    Fuzzes InMemoryLlmProvider._synthesize_mock_instance with dynamically generated
    Pydantic models across string, numeric, boolean, nested, and default fields to ensure
    it always synthesizes a valid, schema-compliant instance without raising runtime errors.
"""

from __future__ import annotations

from typing import Any

from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel, create_model

from hexastack_core.adapters.ai.in_memory import InMemoryLlmProvider


def test_in_memory_llm_provider_field_synthesis_invariants() -> None:
    """Verify synthesis handles standard types correctly without failing."""
    llm = InMemoryLlmProvider()

    class ComplexTarget(BaseModel):
        name: str
        count: int
        ratio: float
        active: bool
        optional_tag: str | None = None

    instance = llm.generate_structured("prompt", ComplexTarget)
    assert isinstance(instance, ComplexTarget)
    assert instance.name == "Mock name"
    assert instance.count == 1
    assert instance.ratio == 1
    assert instance.active is True
    assert instance.optional_tag is None


@given(
    field_names=st.lists(
        st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
        min_size=1,
        max_size=5,
        unique=True,
    )
)
def test_hypothesis_dynamic_pydantic_schema_synthesis(field_names: list[str]) -> None:
    """Fuzz arbitrary dynamic Pydantic models to ensure synthesis produces a valid instance."""
    fields: dict[str, tuple[Any, Any]] = {}
    for i, name in enumerate(field_names):
        if i % 3 == 0:
            fields[name] = (str, ...)
        elif i % 3 == 1:
            fields[name] = (int, ...)
        else:
            fields[name] = (bool, ...)

    create_fn: Any = create_model
    DynamicModel: type[BaseModel] = create_fn("DynamicFuzzModel", **fields)
    llm = InMemoryLlmProvider()
    synthesized = llm.generate_structured("Generate dynamic object", DynamicModel)

    assert isinstance(synthesized, DynamicModel)
    for i, name in enumerate(field_names):
        val = getattr(synthesized, name)
        if i % 3 == 0:
            assert isinstance(val, str)
        elif i % 3 == 1:
            assert isinstance(val, int)
        else:
            assert isinstance(val, bool)

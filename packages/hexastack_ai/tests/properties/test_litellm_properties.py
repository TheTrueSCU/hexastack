"""Property-based fuzz testing for Hexastack AI config and adapters."""

from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from hexastack_ai.adapters.litellm import LiteLlmAdapter
from hexastack_ai.infra.config import (
    HexastackAiConfig,
    LiteLlmDialectConfig,
)


class FuzzProductSchema(BaseModel):
    name: str
    price: float
    tags: list[str]


@settings(deadline=None)
@given(
    model=st.sampled_from(
        ["gpt-4o", "claude-3-5-sonnet-20241022", "gemini-1.5-pro", "llama3"]
    ),
    temperature=st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
    max_tokens=st.integers(min_value=1, max_value=8192),
    prompt=st.text(min_size=1, max_size=200),
    system_prompt=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
    response_text=st.text(min_size=0, max_size=500),
)
def test_litellm_adapter_text_generation_fuzz(
    model: str,
    temperature: float,
    max_tokens: int,
    prompt: str,
    system_prompt: str | None,
    response_text: str,
):
    """Property test verifying invariant message list format and kwargs generation across prompt inputs."""
    mock_choice = MagicMock()
    mock_choice.message.content = response_text
    mock_response = MagicMock(choices=[mock_choice])

    with patch("litellm.completion", return_value=mock_response) as mock_comp:
        config = HexastackAiConfig(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key="test-fuzz-key",
            litellm=LiteLlmDialectConfig(drop_params=True, num_retries=2, timeout=10.0),
        )
        adapter = LiteLlmAdapter(config=config)

        res = adapter.generate_text(prompt, system_prompt=system_prompt)
        assert res == response_text

        call_kwargs = mock_comp.call_args.kwargs
        assert call_kwargs["model"] == model
        assert call_kwargs["temperature"] == temperature
        assert call_kwargs["max_tokens"] == max_tokens
        assert call_kwargs["api_key"] == "test-fuzz-key"

        messages = call_kwargs["messages"]
        if system_prompt:
            assert len(messages) == 2
            assert messages[0] == {"role": "system", "content": system_prompt}
            assert messages[1] == {"role": "user", "content": prompt}
        else:
            assert len(messages) == 1
            assert messages[0] == {"role": "user", "content": prompt}


@settings(deadline=None)
@given(
    name=st.text(min_size=1, max_size=50),
    price=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False),
    tags=st.lists(st.text(min_size=1, max_size=20), max_size=5),
)
def test_litellm_adapter_structured_generation_fuzz(
    name: str,
    price: float,
    tags: list[str],
):
    """Property test verifying structured output generation invariants."""
    expected_obj = FuzzProductSchema(name=name, price=price, tags=tags)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = expected_obj

    with patch("instructor.from_litellm", return_value=mock_client):
        adapter = LiteLlmAdapter()
        res = adapter.generate_structured("Generate product", FuzzProductSchema)
        assert res == expected_obj
        assert res.name == name
        assert res.price == price
        assert res.tags == tags

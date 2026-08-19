from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from instructor.core import InstructorRetryException
from pydantic import BaseModel

from hexastack_ai.adapters.litellm import LiteLlmAdapter
from hexastack_ai.domain.exceptions import (
    LlmProviderError,
    StructuredOutputParsingError,
)
from hexastack_ai.infra.config import (
    HexastackAiConfig,
    LiteLlmDialectConfig,
    PydanticAiDialectConfig,
)


class SummarySchema(BaseModel):
    title: str
    score: int


# ---------------------------------------------------------------------------
# 1. generate_text (Sync) & Parameter Forwarding
# ---------------------------------------------------------------------------


def test_litellm_adapter_generate_text_full_config():
    """Verify all config fields, system prompt, api_key, api_base, and drop_params
    are explicitly forwarded to litellm.completion."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Mocked AI Response"
    mock_response = MagicMock(choices=[mock_choice])

    with patch("litellm.completion", return_value=mock_response) as mock_comp:
        config = HexastackAiConfig(
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            max_tokens=1024,
            api_key="secret-key-123",
            litellm=LiteLlmDialectConfig(
                api_base="https://custom.litellm.api",
                drop_params=True,
                num_retries=3,
                timeout=45.0,
            ),
        )
        adapter = LiteLlmAdapter(config=config)

        res = adapter.generate_text(
            "Explain quantum physics", system_prompt="You are a physicist."
        )
        assert res == "Mocked AI Response"

        mock_comp.assert_called_once_with(
            model="claude-3-5-sonnet-20241022",
            messages=[
                {"role": "system", "content": "You are a physicist."},
                {"role": "user", "content": "Explain quantum physics"},
            ],
            temperature=0.7,
            max_tokens=1024,
            drop_params=True,
            num_retries=3,
            timeout=45.0,
            api_key="secret-key-123",
            api_base="https://custom.litellm.api",
        )


def test_litellm_adapter_generate_text_agent_config_system_prompt():
    """Verify agent.system_prompt fallback when no explicit system_prompt is provided."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Agent reply"
    mock_response = MagicMock(choices=[mock_choice])

    with patch("litellm.completion", return_value=mock_response) as mock_comp:
        config = HexastackAiConfig(
            agent=PydanticAiDialectConfig(system_prompt="Default agent role"),
            api_key=None,
        )
        adapter = LiteLlmAdapter(config=config)

        res = adapter.generate_text("Hi agent")
        assert res == "Agent reply"

        call_kwargs = mock_comp.call_args.kwargs
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "Default agent role"},
            {"role": "user", "content": "Hi agent"},
        ]
        assert "api_key" not in call_kwargs


def test_litellm_adapter_generate_text_no_system_prompt():
    """Verify messages list contains only user prompt when no system prompt is configured."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Simple response"
    mock_response = MagicMock(choices=[mock_choice])

    with patch("litellm.completion", return_value=mock_response) as mock_comp:
        config = HexastackAiConfig(api_key=None)
        adapter = LiteLlmAdapter(config=config)

        res = adapter.generate_text("Just user text")
        assert res == "Simple response"

        call_kwargs = mock_comp.call_args.kwargs
        assert call_kwargs["messages"] == [
            {"role": "user", "content": "Just user text"}
        ]


def test_litellm_adapter_generate_text_none_content_fallback():
    """Verify empty string fallback when choices[0].message.content is None."""
    mock_choice = MagicMock()
    mock_choice.message.content = None
    mock_response = MagicMock(choices=[mock_choice])

    with patch("litellm.completion", return_value=mock_response):
        adapter = LiteLlmAdapter()
        res = adapter.generate_text("Prompt with empty output")
        assert res == ""


# ---------------------------------------------------------------------------
# 2. generate_text_async (Async) & Parameter Forwarding
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_litellm_adapter_generate_text_async_full_config():
    """Verify all config fields are passed to litellm.acompletion."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Async AI Response"
    mock_response = MagicMock(choices=[mock_choice])

    with patch(
        "litellm.acompletion", new_callable=AsyncMock, return_value=mock_response
    ) as mock_acomp:
        config = HexastackAiConfig(
            model="gpt-4o",
            temperature=0.2,
            max_tokens=2048,
            api_key="async-secret-key",
            litellm=LiteLlmDialectConfig(
                api_base="https://async.litellm.api",
                drop_params=False,
                num_retries=2,
                timeout=30.0,
            ),
        )
        adapter = LiteLlmAdapter(config=config)

        res = await adapter.generate_text_async(
            "Hello Async", system_prompt="Be concise"
        )
        assert res == "Async AI Response"

        mock_acomp.assert_called_once_with(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Be concise"},
                {"role": "user", "content": "Hello Async"},
            ],
            temperature=0.2,
            max_tokens=2048,
            drop_params=False,
            num_retries=2,
            timeout=30.0,
            api_key="async-secret-key",
            api_base="https://async.litellm.api",
        )


@pytest.mark.anyio
async def test_litellm_adapter_generate_text_async_agent_system_prompt():
    """Verify agent.system_prompt fallback in async generation."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Async agent reply"
    mock_response = MagicMock(choices=[mock_choice])

    with patch(
        "litellm.acompletion", new_callable=AsyncMock, return_value=mock_response
    ) as mock_acomp:
        config = HexastackAiConfig(
            agent=PydanticAiDialectConfig(system_prompt="Async Agent Role"),
            api_key=None,
        )
        adapter = LiteLlmAdapter(config=config)

        res = await adapter.generate_text_async("Async ping")
        assert res == "Async agent reply"

        call_kwargs = mock_acomp.call_args.kwargs
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "Async Agent Role"},
            {"role": "user", "content": "Async ping"},
        ]


@pytest.mark.anyio
async def test_litellm_adapter_generate_text_async_none_content():
    """Verify empty string fallback in async when content is None."""
    mock_choice = MagicMock()
    mock_choice.message.content = None
    mock_response = MagicMock(choices=[mock_choice])

    with patch(
        "litellm.acompletion", new_callable=AsyncMock, return_value=mock_response
    ):
        adapter = LiteLlmAdapter()
        res = await adapter.generate_text_async("Empty async")
        assert res == ""


# ---------------------------------------------------------------------------
# 3. generate_structured (Sync) & Instructor Integration
# ---------------------------------------------------------------------------


def test_litellm_adapter_generate_structured():
    expected = SummarySchema(title="Report", score=95)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = expected

    with patch("instructor.from_litellm", return_value=mock_client) as mock_from:
        config = HexastackAiConfig(
            model="gpt-4o",
            temperature=0.3,
            max_tokens=500,
            api_key="struct-key",
            litellm=LiteLlmDialectConfig(api_base="https://struct.litellm.api"),
        )
        adapter = LiteLlmAdapter(config=config)
        res = adapter.generate_structured("Analyze this", SummarySchema)
        assert res == expected
        assert res.title == "Report"
        assert res.score == 95

        mock_from.assert_called_once()
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Analyze this"}],
            response_model=SummarySchema,
            temperature=0.3,
            max_tokens=500,
            api_key="struct-key",
            api_base="https://struct.litellm.api",
        )


def test_litellm_adapter_generate_structured_retry_exception():
    """Verify instructor.core.InstructorRetryException is translated to StructuredOutputParsingError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = InstructorRetryException(
        "Validation failed repeatedly",
        n_attempts=3,
        total_usage=100,
    )

    with patch("instructor.from_litellm", return_value=mock_client):
        adapter = LiteLlmAdapter()
        with pytest.raises(StructuredOutputParsingError) as exc_info:
            adapter.generate_structured("Bad JSON output", SummarySchema)
        assert "Failed to generate structured SummarySchema" in str(exc_info.value)


def test_litellm_adapter_generate_structured_generic_exception():
    """Verify unexpected errors in structured sync generation raise LlmProviderError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError(
        "OpenAI rate limited"
    )

    with patch("instructor.from_litellm", return_value=mock_client):
        config = HexastackAiConfig(provider="openai", model="gpt-4o")
        adapter = LiteLlmAdapter(config=config)
        with pytest.raises(LlmProviderError) as exc_info:
            adapter.generate_structured("Rate limit prompt", SummarySchema)
        assert "OpenAI rate limited" in str(exc_info.value)
        assert exc_info.value.provider == "openai"
        assert exc_info.value.model == "gpt-4o"


# ---------------------------------------------------------------------------
# 4. generate_structured_async (Async) & Instructor Integration
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_litellm_adapter_generate_structured_async():
    expected = SummarySchema(title="Async Report", score=100)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = expected

    with patch("instructor.from_litellm", return_value=mock_client) as mock_from:
        config = HexastackAiConfig(
            model="claude-3-opus",
            temperature=0.1,
            max_tokens=800,
            api_key="async-struct-key",
            litellm=LiteLlmDialectConfig(api_base="https://async-struct.api"),
        )
        adapter = LiteLlmAdapter(config=config)
        res = await adapter.generate_structured_async("Async analyze", SummarySchema)
        assert res == expected

        mock_from.assert_called_once()
        mock_client.chat.completions.create.assert_called_once_with(
            model="claude-3-opus",
            messages=[{"role": "user", "content": "Async analyze"}],
            response_model=SummarySchema,
            temperature=0.1,
            max_tokens=800,
            api_key="async-struct-key",
            api_base="https://async-struct.api",
        )


@pytest.mark.anyio
async def test_litellm_adapter_generate_structured_async_retry_exception():
    """Verify instructor.core.InstructorRetryException in async call translates to StructuredOutputParsingError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = InstructorRetryException(
        "Async schema error",
        n_attempts=3,
        total_usage=100,
    )

    with patch("instructor.from_litellm", return_value=mock_client):
        adapter = LiteLlmAdapter()
        with pytest.raises(StructuredOutputParsingError) as exc_info:
            await adapter.generate_structured_async(
                "Async schema prompt", SummarySchema
            )
        assert "Failed to generate structured SummarySchema" in str(exc_info.value)


@pytest.mark.anyio
async def test_litellm_adapter_generate_structured_async_generic_exception():
    """Verify unexpected errors in structured async generation raise LlmProviderError."""
    mock_client = MagicMock()
    mock_coro = AsyncMock(side_effect=RuntimeError("Async connection reset"))
    mock_client.chat.completions.create = mock_coro

    with patch("instructor.from_litellm", return_value=mock_client):
        config = HexastackAiConfig(provider="anthropic", model="claude-3-5-sonnet")
        adapter = LiteLlmAdapter(config=config)
        with pytest.raises(LlmProviderError) as exc_info:
            await adapter.generate_structured_async("Prompt", SummarySchema)
        assert "Async connection reset" in str(exc_info.value)
        assert exc_info.value.provider == "anthropic"
        assert exc_info.value.model == "claude-3-5-sonnet"


# ---------------------------------------------------------------------------
# 5. Error translation & metadata
# ---------------------------------------------------------------------------


def test_litellm_adapter_error_handling_metadata():
    with patch("litellm.completion", side_effect=RuntimeError("API down")):
        config = HexastackAiConfig(provider="google", model="gemini-1.5-pro")
        adapter = LiteLlmAdapter(config=config)
        with pytest.raises(LlmProviderError) as exc_info:
            adapter.generate_text("Fail please")
        assert "API down" in str(exc_info.value)
        assert exc_info.value.provider == "google"
        assert exc_info.value.model == "gemini-1.5-pro"


@pytest.mark.anyio
async def test_litellm_adapter_error_handling_async_metadata():
    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Async API down"),
    ):
        config = HexastackAiConfig(provider="google", model="gemini-1.5-pro")
        adapter = LiteLlmAdapter(config=config)
        with pytest.raises(LlmProviderError) as exc_info:
            await adapter.generate_text_async("Fail async please")
        assert "Async API down" in str(exc_info.value)
        assert exc_info.value.provider == "google"
        assert exc_info.value.model == "gemini-1.5-pro"

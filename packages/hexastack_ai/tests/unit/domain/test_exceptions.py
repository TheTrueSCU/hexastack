from hexastack_ai.domain.exceptions import (
    AgentExecutionError,
    AiError,
    LlmProviderError,
    StructuredOutputParsingError,
)
from hexastack_core.domain import HexastackError


def test_ai_exceptions_hierarchy():
    assert issubclass(AiError, HexastackError)
    assert issubclass(LlmProviderError, AiError)
    assert issubclass(StructuredOutputParsingError, AiError)
    assert issubclass(AgentExecutionError, AiError)


def test_llm_provider_error_attributes():
    err = LlmProviderError("Rate limit exceeded", provider="openai", model="gpt-4o")
    assert "Rate limit exceeded" in str(err)
    assert "[provider=openai, model=gpt-4o]" in str(err)
    assert err.provider == "openai"
    assert err.model == "gpt-4o"


def test_structured_output_error_attributes():
    err = StructuredOutputParsingError(
        "Schema mismatch", raw_response='{"invalid": true}'
    )
    assert "Schema mismatch" in str(err)
    assert err.raw_response == '{"invalid": true}'

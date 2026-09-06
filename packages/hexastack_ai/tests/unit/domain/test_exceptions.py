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
    err_both = LlmProviderError(
        "Rate limit exceeded", provider="openai", model="gpt-4o"
    )
    assert str(err_both) == "Rate limit exceeded [provider=openai, model=gpt-4o]"
    assert err_both.provider == "openai"
    assert err_both.model == "gpt-4o"

    err_provider_only = LlmProviderError(
        "Auth failed", provider="anthropic", model=None
    )
    assert str(err_provider_only) == "Auth failed [provider=anthropic, model=None]"
    assert err_provider_only.provider == "anthropic"
    assert err_provider_only.model is None

    err_model_only = LlmProviderError(
        "Context length", provider=None, model="claude-3-opus"
    )
    assert str(err_model_only) == "Context length [provider=None, model=claude-3-opus]"
    assert err_model_only.provider is None
    assert err_model_only.model == "claude-3-opus"

    err_neither = LlmProviderError("Generic AI failure")
    assert str(err_neither) == "Generic AI failure"
    assert err_neither.provider is None
    assert err_neither.model is None


def test_structured_output_error_attributes():
    err = StructuredOutputParsingError(
        "Schema mismatch", raw_response='{"invalid": true}'
    )
    assert str(err) == "Schema mismatch"
    assert err.raw_response == '{"invalid": true}'

    err_default = StructuredOutputParsingError("Parsing failed")
    assert str(err_default) == "Parsing failed"
    assert err_default.raw_response is None

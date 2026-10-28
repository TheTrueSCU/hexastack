from hexastack_ai.domain.exceptions import (
    AgentExecutionError,
    AiError,
    LlmProviderError,
    StructuredOutputParsingError,
    TokenizerNotFoundError,
    TokenLimitExceededError,
)
from hexastack_core.domain import HexastackError


def test_ai_exceptions_hierarchy():
    sub_ai = issubclass(AiError, HexastackError)
    assert sub_ai is True
    sub_llm = issubclass(LlmProviderError, AiError)
    assert sub_llm is True
    sub_sop = issubclass(StructuredOutputParsingError, AiError)
    assert sub_sop is True
    sub_aee = issubclass(AgentExecutionError, AiError)
    assert sub_aee is True
    sub_tle = issubclass(TokenLimitExceededError, AiError)
    assert sub_tle is True
    sub_tnf = issubclass(TokenizerNotFoundError, AiError)
    assert sub_tnf is True


def test_llm_provider_error_attributes():
    err_both = LlmProviderError(
        "Rate limit exceeded", provider="openai", model="gpt-4o"
    )
    msg_both = str(err_both)
    assert msg_both == "Rate limit exceeded [provider=openai, model=gpt-4o]"
    assert err_both.provider == "openai"
    assert err_both.model == "gpt-4o"

    err_provider_only = LlmProviderError(
        "Auth failed", provider="anthropic", model=None
    )
    msg_provider = str(err_provider_only)
    assert msg_provider == "Auth failed [provider=anthropic, model=None]"
    assert err_provider_only.provider == "anthropic"
    assert err_provider_only.model is None

    err_model_only = LlmProviderError(
        "Context length", provider=None, model="claude-3-opus"
    )
    msg_model = str(err_model_only)
    assert msg_model == "Context length [provider=None, model=claude-3-opus]"
    assert err_model_only.provider is None
    assert err_model_only.model == "claude-3-opus"

    err_neither = LlmProviderError("Generic AI failure")
    msg_neither = str(err_neither)
    assert msg_neither == "Generic AI failure"
    assert err_neither.provider is None
    assert err_neither.model is None


def test_structured_output_error_attributes():
    err = StructuredOutputParsingError(
        "Schema mismatch", raw_response='{"invalid": true}'
    )
    msg = str(err)
    assert msg == "Schema mismatch"
    assert err.raw_response == '{"invalid": true}'

    err_default = StructuredOutputParsingError("Parsing failed")
    msg_def = str(err_default)
    assert msg_def == "Parsing failed"
    assert err_default.raw_response is None


def test_token_limit_exceeded_error_attributes():
    err = TokenLimitExceededError(
        message="Context limit reached",
        current_tokens=150000,
        max_tokens=128000,
        model="gpt-4o",
    )
    assert err.current_tokens == 150000
    assert err.max_tokens == 128000
    assert err.model == "gpt-4o"
    msg = str(err)
    assert msg == "Context limit reached [current=150000, max=128000, model=gpt-4o]"


def test_tokenizer_not_found_error_attributes():
    err = TokenizerNotFoundError("non-existent-encoder")
    assert err.model_or_encoding == "non-existent-encoder"
    msg = str(err)
    assert msg == "No suitable tokenizer found for: 'non-existent-encoder'"

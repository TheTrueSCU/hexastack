from hexastack_core.domain import HexastackError


class AiError(HexastackError):
    """Base exception for all AI, LLM, and agent operations in Hexastack."""


class LlmProviderError(AiError):
    """Exception raised when an upstream LLM API call fails."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize LlmProviderError with model and provider context.

        Args:
            message: Error description.
            provider: Name of the LLM provider (e.g. 'openai', 'anthropic').
            model: Name of the target model (e.g. 'gpt-4o', 'claude-3-5-sonnet').
        """
        self.provider = provider
        self.model = model
        suffix = f" [provider={provider}, model={model}]" if provider or model else ""
        super().__init__(f"{message}{suffix}")


class StructuredOutputParsingError(AiError):
    """Exception raised when LLM output fails schema validation."""

    def __init__(self, message: str, raw_response: str | None = None) -> None:
        """Initialize exception with raw output text.

        Args:
            message: Error description.
            raw_response: Raw response string from the model.
        """
        self.raw_response = raw_response
        super().__init__(message)


class AgentExecutionError(AiError):
    """Exception raised when an agent loop or tool execution fails."""


class TokenLimitExceededError(AiError):
    """Exception raised when token budget or context window limits are exceeded.

    Notes/Architectural Intent:
        Prevents outbound LLM requests from failing upstream at provider APIs with
        context-length errors by failing fast locally.
    """

    def __init__(
        self,
        message: str,
        current_tokens: int,
        max_tokens: int,
        model: str | None = None,
    ) -> None:
        """Initialize TokenLimitExceededError with token counts and model context.

        Args:
            message: Error description.
            current_tokens: Current token count exceeding the budget.
            max_tokens: Maximum allowed token limit.
            model: Optional model identifier.
        """
        self.current_tokens = current_tokens
        self.max_tokens = max_tokens
        self.model = model
        suffix = f" [current={current_tokens}, max={max_tokens}, model={model}]"
        super().__init__(f"{message}{suffix}")


class TokenizerNotFoundError(AiError):
    """Exception raised when a tokenizer cannot be resolved for a model.

    Notes/Architectural Intent:
        Signals missing tokenizer configurations or unsupported model encodings
        during local token counting.
    """

    def __init__(self, model_or_encoding: str) -> None:
        """Initialize TokenizerNotFoundError with target model or encoding.

        Args:
            model_or_encoding: The model name or encoding identifier that could not be resolved.
        """
        self.model_or_encoding = model_or_encoding
        super().__init__(f"No suitable tokenizer found for: '{model_or_encoding}'")


__all__ = [
    "AgentExecutionError",
    "AiError",
    "LlmProviderError",
    "StructuredOutputParsingError",
    "TokenizerNotFoundError",
    "TokenLimitExceededError",
]

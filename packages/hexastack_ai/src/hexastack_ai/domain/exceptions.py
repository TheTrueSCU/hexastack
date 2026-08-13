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


__all__ = [
    "AgentExecutionError",
    "AiError",
    "LlmProviderError",
    "StructuredOutputParsingError",
]

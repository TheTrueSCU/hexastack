from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from pydantic import BaseModel, Field


class LiteLlmDialectConfig(BaseModel):
    """Dialect configuration options specific to LiteLLM."""

    drop_params: bool = Field(
        default=True,
        description="Automatically drop unmapped provider parameters to prevent errors.",
    )
    num_retries: int = Field(
        default=3,
        description="Number of retry attempts on rate limits or transient errors.",
    )
    timeout: float = Field(
        default=60.0,
        description="Request timeout in seconds.",
    )
    api_base: str | None = Field(
        default=None,
        description="Custom API base URL (e.g. for self-hosted LiteLLM proxy or local endpoint).",
    )


class OllamaDialectConfig(BaseModel):
    """Dialect configuration options for local Ollama instances."""

    base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for the local Ollama daemon.",
    )


class PydanticAiDialectConfig(BaseModel):
    """Configuration options for PydanticAI agents."""

    max_turns: int = Field(
        default=10,
        description="Maximum turn limit for agent tool-calling loops.",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Default system prompt for agent personas.",
    )


@config_section("ai")
class HexastackAiConfig(BaseModel):
    """Configuration schema for Hexastack AI engine under [hexastack.ai].

    Notes/Architectural Intent:
        Partitions global model settings (model, temperature, tokens) from
        provider/dialect-specific subsections (LiteLLM, Ollama, PydanticAI).
    """

    provider: str = Field(
        default="memory",
        description="Target LLM provider ('memory', 'litellm', 'openai', 'anthropic', 'gemini', 'ollama').",
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="Default model identifier (e.g. 'gpt-4o', 'claude-3-5-sonnet-20241022', 'gemini/gemini-1.5-pro').",
    )
    temperature: float = Field(
        default=0.2,
        description="Sampling temperature between 0.0 and 2.0.",
    )
    max_tokens: int = Field(
        default=2048,
        description="Maximum tokens for text generation.",
    )
    api_key: str | None = Field(
        default=None,
        description="Optional explicit API key override (prefers environment variables by default).",
    )

    # Dialect-specific sections
    litellm: LiteLlmDialectConfig = Field(
        default_factory=LiteLlmDialectConfig,
        description="LiteLLM proxy and retry configuration.",
    )
    ollama: OllamaDialectConfig = Field(
        default_factory=OllamaDialectConfig,
        description="Ollama local model configuration.",
    )
    agent: PydanticAiDialectConfig = Field(
        default_factory=PydanticAiDialectConfig,
        description="PydanticAI agent configuration.",
    )


def register_ai_config(registry: ConfigRegistry) -> None:
    """Register AI configuration schema under 'ai' ([hexastack.ai]).

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("ai", HexastackAiConfig)


__all__ = [
    "HexastackAiConfig",
    "LiteLlmDialectConfig",
    "OllamaDialectConfig",
    "PydanticAiDialectConfig",
    "register_ai_config",
]

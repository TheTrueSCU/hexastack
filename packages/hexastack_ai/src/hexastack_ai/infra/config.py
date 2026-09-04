from hexastack_ai.domain.config import (
    HexastackAiConfig,
    LiteLlmDialectConfig,
    OllamaDialectConfig,
    PydanticAiDialectConfig,
)
from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry

# Tag config with section name for autodiscovery
config_section("ai")(HexastackAiConfig)

__all__ = [
    "HexastackAiConfig",
    "LiteLlmDialectConfig",
    "OllamaDialectConfig",
    "PydanticAiDialectConfig",
    "register_ai_config",
]


def register_ai_config(registry: ConfigRegistry) -> None:
    """Register AI configuration schema under 'ai' ([hexastack.ai]).

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("ai", HexastackAiConfig)

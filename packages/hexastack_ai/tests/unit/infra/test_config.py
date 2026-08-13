from hexastack_ai.infra.config import (
    HexastackAiConfig,
    LiteLlmDialectConfig,
    OllamaDialectConfig,
    PydanticAiDialectConfig,
    register_ai_config,
)
from hexastack_core.infra.registries.config import ConfigRegistry


def test_ai_config_defaults():
    config = HexastackAiConfig()
    assert config.provider == "memory"
    assert config.model == "gpt-4o-mini"
    assert config.temperature == 0.2
    assert config.max_tokens == 2048
    assert config.api_key is None

    # Dialect defaults
    assert config.litellm.drop_params is True
    assert config.litellm.num_retries == 3
    assert config.litellm.timeout == 60.0
    assert config.ollama.base_url == "http://localhost:11434"
    assert config.agent.max_turns == 10
    assert config.agent.system_prompt is None


def test_ai_config_custom_values():
    config = HexastackAiConfig(
        provider="litellm",
        model="anthropic/claude-3-5-sonnet",
        temperature=0.7,
        max_tokens=4096,
        api_key="sk-test-key",
        litellm=LiteLlmDialectConfig(timeout=30.0, num_retries=5),
        ollama=OllamaDialectConfig(base_url="http://remote-ollama:11434"),
        agent=PydanticAiDialectConfig(
            system_prompt="You are a helpful banking assistant."
        ),
    )
    assert config.provider == "litellm"
    assert config.model == "anthropic/claude-3-5-sonnet"
    assert config.temperature == 0.7
    assert config.max_tokens == 4096
    assert config.api_key == "sk-test-key"
    assert config.litellm.timeout == 30.0
    assert config.litellm.num_retries == 5
    assert config.ollama.base_url == "http://remote-ollama:11434"
    assert config.agent.system_prompt == "You are a helpful banking assistant."


def test_register_ai_config():
    registry = ConfigRegistry()
    register_ai_config(registry)
    assert "ai" in registry
    assert registry.get("ai") is HexastackAiConfig

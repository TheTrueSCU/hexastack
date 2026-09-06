from hexastack_ai.domain.config import (
    HexastackAiConfig,
    LiteLlmDialectConfig,
    OllamaDialectConfig,
    PydanticAiDialectConfig,
)


def test_hexastack_ai_config_defaults():
    cfg = HexastackAiConfig()
    assert cfg.provider == "memory"
    assert cfg.model == "gpt-4o-mini"
    assert cfg.temperature == 0.2
    assert cfg.max_tokens == 2048
    assert cfg.api_key is None
    assert isinstance(cfg.litellm, LiteLlmDialectConfig)
    assert isinstance(cfg.ollama, OllamaDialectConfig)
    assert isinstance(cfg.agent, PydanticAiDialectConfig)


def test_litellm_dialect_config():
    default_cfg = LiteLlmDialectConfig()
    assert default_cfg.drop_params is True
    assert default_cfg.num_retries == 3
    assert default_cfg.timeout == 60.0
    assert default_cfg.api_base is None

    custom_cfg = LiteLlmDialectConfig(
        drop_params=False,
        num_retries=5,
        timeout=120.0,
        api_base="https://custom.endpoint",
    )
    assert custom_cfg.drop_params is False
    assert custom_cfg.num_retries == 5
    assert custom_cfg.timeout == 120.0
    assert custom_cfg.api_base == "https://custom.endpoint"


def test_ollama_dialect_config():
    default_cfg = OllamaDialectConfig()
    assert default_cfg.base_url == "http://localhost:11434"

    custom_cfg = OllamaDialectConfig(base_url="http://remote-ollama:11434")
    assert custom_cfg.base_url == "http://remote-ollama:11434"


def test_pydantic_ai_dialect_config():
    default_cfg = PydanticAiDialectConfig()
    assert default_cfg.max_turns == 10
    assert default_cfg.system_prompt is None

    custom_cfg = PydanticAiDialectConfig(
        max_turns=20,
        system_prompt="Custom prompt",
    )
    assert custom_cfg.max_turns == 20
    assert custom_cfg.system_prompt == "Custom prompt"


def test_hexastack_ai_config_custom():
    cfg = HexastackAiConfig(
        provider="anthropic",
        model="claude-3-5-sonnet",
        temperature=0.7,
        max_tokens=4096,
        api_key="sk-test-key",  # pragma: allowlist secret
        litellm=LiteLlmDialectConfig(api_base="https://api.litellm.ai"),
        ollama=OllamaDialectConfig(base_url="http://local-ollama:11434"),
        agent=PydanticAiDialectConfig(system_prompt="Agent prompt"),
    )
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-3-5-sonnet"
    assert cfg.temperature == 0.7
    assert cfg.max_tokens == 4096
    assert cfg.api_key == "sk-test-key"
    assert cfg.litellm.api_base == "https://api.litellm.ai"
    assert cfg.ollama.base_url == "http://local-ollama:11434"
    assert cfg.agent.system_prompt == "Agent prompt"

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

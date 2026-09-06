from rodi import Container

from hexastack_ai.adapters.litellm import LiteLlmAdapter
from hexastack_ai.infra.bootstrap import (
    AiBootstrapper,
    AiBootstrapResult,
)
from hexastack_ai.infra.config import HexastackAiConfig
from hexastack_core.adapters.ai import InMemoryLlmProvider
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.ai import LlmProviderPort


def test_ai_bootstrapper_default_memory():
    result = bootstrap(bootstrappers=[AiBootstrapper()])
    container = result.container

    assert LlmProviderPort in container
    assert InMemoryLlmProvider in container
    llm = container.resolve(LlmProviderPort)
    assert isinstance(llm, InMemoryLlmProvider)

    ai_res: AiBootstrapResult = result.get("ai_result")
    assert ai_res is not None
    assert ai_res.config.provider == "memory"
    assert ai_res.llm_provider is llm

    ai_provider = result.get("ai_provider")
    assert ai_provider is llm


def test_ai_bootstrapper_litellm_provider():
    config = HexastackAiConfig(
        provider="litellm",
        model="gpt-4o-mini",
    )
    c = Container()
    c.add_instance(config, declared_class=HexastackAiConfig)

    result = bootstrap(
        bootstrappers=[AiBootstrapper()],
        container=c,
    )
    container = result.container

    assert LlmProviderPort in container
    assert LiteLlmAdapter in container
    llm = container.resolve(LlmProviderPort)
    assert isinstance(llm, LiteLlmAdapter)

    ai_res: AiBootstrapResult = result.get("ai_result")
    assert ai_res is not None
    assert ai_res.config is config
    assert ai_res.llm_provider is llm

    ai_provider = result.get("ai_provider")
    assert ai_provider is llm


def test_ai_bootstrapper_from_context_config():
    """Verify bootstrap retrieves HexastackAiConfig via context.get_config('ai', HexastackAiConfig)."""
    from hexastack_core.infra.bootstrap import BootstrapContext
    from hexastack_core.infra.config import HexastackConfig, HexastackCoreConfig
    from hexastack_core.infra.registries.config import ConfigRegistry

    c = Container()
    reg = ConfigRegistry()
    bootstrapper = AiBootstrapper()
    bootstrapper.register_config(reg)

    core_cfg = HexastackConfig(
        core=HexastackCoreConfig(),
        sections={"ai": HexastackAiConfig(provider="memory", model="test-custom-model")},
    )
    context = BootstrapContext(
        container=c,
        config=core_cfg,
        config_registry=reg,
    )
    bootstrapper.configure(context)

    ai_res: AiBootstrapResult = context.properties.get("ai_result")
    assert ai_res is not None
    assert ai_res.config.model == "test-custom-model"
    assert ai_res.config.provider == "memory"
    assert context.properties.get("ai_provider") is ai_res.llm_provider




def test_ai_bootstrapper_metadata():
    bootstrapper = AiBootstrapper()
    assert bootstrapper.name == "ai"
    assert bootstrapper.order == 18


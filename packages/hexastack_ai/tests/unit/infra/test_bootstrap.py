from hexastack_ai.adapters.litellm import LiteLlmAdapter
from hexastack_ai.infra.bootstrap import (
    AiBootstrapper,
    AiBootstrapResult,
)
from hexastack_ai.infra.config import HexastackAiConfig
from hexastack_core.adapters.ai import InMemoryLlmProvider
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.ai import LlmProviderPort
from rodi import Container


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


def test_ai_bootstrapper_metadata():
    bootstrapper = AiBootstrapper()
    assert bootstrapper.name == "ai"
    assert bootstrapper.order == 18

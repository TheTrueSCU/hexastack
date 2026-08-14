from dataclasses import dataclass

from hexastack_ai.infra.config import HexastackAiConfig, register_ai_config
from hexastack_core.adapters.ai import InMemoryLlmProvider
from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.ai import LlmProviderPort
from hexastack_core.ports.bootstrap import BootstrapperPort


@dataclass(frozen=True)
class AiBootstrapResult:
    """Dataclass holding initialized AI provider and configuration."""

    config: HexastackAiConfig
    llm_provider: LlmProviderPort


class AiBootstrapper(BootstrapperPort):
    """Bootstrap extension initializing LLM provider and agent integration.

    Notes/Architectural Intent:
        Implements BootstrapperPort at order=18, registering [hexastack.ai] config
        and binding LlmProviderPort into the DI container. Automatically defaults
        to InMemoryLlmProvider when provider='memory' for zero-infrastructure test isolation.
    """

    name: str = "ai"
    order: int = 18

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Assemble LLM provider adapter in DI container.

        Args:
            context: BootstrapContext containing DI container and config.
        """
        di = context.container

        # 1. Read AI Configuration
        if HexastackAiConfig in di:
            ai_config = di.resolve(HexastackAiConfig)
        else:
            ai_config = context.get_config("ai", HexastackAiConfig)

        # 2. Build Provider based on config
        llm_provider: LlmProviderPort
        if ai_config.provider == "memory":
            llm_provider = InMemoryLlmProvider()
            di.add_instance(llm_provider, declared_class=InMemoryLlmProvider)
        else:
            from hexastack_ai.adapters.litellm import LiteLlmAdapter

            llm_provider = LiteLlmAdapter(config=ai_config)
            di.add_instance(llm_provider, declared_class=LiteLlmAdapter)

        # 3. Register in DI container
        di.add_instance(llm_provider, declared_class=LlmProviderPort)

        # 4. Store result in context properties
        ai_result = AiBootstrapResult(
            config=ai_config,
            llm_provider=llm_provider,
        )
        context.properties["ai_result"] = ai_result
        context.properties["ai_provider"] = llm_provider

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register AI configuration schema under 'ai'.

        Args:
            registry: Target ConfigRegistry instance.
        """
        register_ai_config(registry)


__all__ = [
    "AiBootstrapResult",
    "AiBootstrapper",
]

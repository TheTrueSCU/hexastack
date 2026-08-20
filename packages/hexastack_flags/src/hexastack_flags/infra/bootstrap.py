"""Bootstrapper extension for hexastack-flags.

Notes/Architectural Intent:
    Configures the OpenFeature provider and registers OpenFeatureFlagAdapter
    into the rodi.Container as the singleton FeatureFlagPort at order=14.
"""

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_flags.adapters.openfeature import OpenFeatureFlagAdapter
from hexastack_flags.adapters.providers.factory import initialize_openfeature_provider
from hexastack_flags.domain.models import FlagProviderOptions
from hexastack_flags.infra.config import HexastackFlagsConfig, register_flags_config

__all__ = [
    "FeatureFlagBootstrapper",
]


class FeatureFlagBootstrapper(BootstrapperPort):
    """Bootstrapper that configures CNCF OpenFeature and binds OpenFeatureFlagAdapter."""

    name: str = "feature_flags"
    order: int = 14  # Runs before CQRS (20), FastAPI (30), etc.

    def configure(self, context: BootstrapContext) -> None:
        """Initialize OpenFeature provider and register OpenFeatureFlagAdapter in DI."""
        config = context.get_config("flags", HexastackFlagsConfig)

        options = FlagProviderOptions(
            host=config.host,
            port=config.port,
            cache=config.cache,
            timeout_ms=config.timeout_ms,
            extra=config.options,
        )

        initialize_openfeature_provider(
            provider_type=config.provider,
            options=options,
            in_memory_flags=config.flags,
        )

        adapter = OpenFeatureFlagAdapter()
        context.container.add_instance(adapter, declared_class=FeatureFlagPort)
        context.flags = adapter

    def register_config(self, registry: ConfigRegistry) -> None:
        """Register HexastackFlagsConfig under [hexastack.flags]."""
        register_flags_config(registry)

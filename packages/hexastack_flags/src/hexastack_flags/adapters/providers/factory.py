"""Provider factories and initialization for OpenFeature backends.

Notes/Architectural Intent:
    Encapsulates setup for Flagd, In-Memory, Environment, and Custom OpenFeature providers.
"""

from typing import Any

import openfeature.api
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_flags.domain.models import FeatureFlagProviderType, FlagProviderOptions

__all__ = [
    "initialize_openfeature_provider",
]


def initialize_openfeature_provider(
    provider_type: FeatureFlagProviderType | str,
    options: FlagProviderOptions | None = None,
    *,
    in_memory_flags: dict[str, Any] | None = None,
) -> None:
    """Initialize and set the global OpenFeature provider.

    Args:
        provider_type: Type of provider to configure (flagd, in_memory, env).
        options: Configuration options (host, port, cache, etc.).
        in_memory_flags: Initial flags dict when using in_memory provider.

    Raises:
        MissingDependencyError: If a provider extra (e.g. openfeature-provider-flagd) is missing.
    """
    opts = options or FlagProviderOptions()
    p_type = str(provider_type).lower()

    if p_type == FeatureFlagProviderType.FLAGD:
        try:
            import importlib

            flagd_mod = importlib.import_module("openfeature.contrib.provider.flagd")
            flagd_cls = flagd_mod.FlagdProvider
            provider = flagd_cls(
                host=opts.host,
                port=opts.port,
                cache=opts.cache,
                timeout_ms=opts.timeout_ms,
            )
            openfeature.api.set_provider(provider)
        except (ImportError, AttributeError) as e:
            raise MissingDependencyError(
                "openfeature-provider-flagd is required for Flagd provider. "
                "Install with 'pip install hexastack-flags[flagd]'."
            ) from e

    elif p_type == FeatureFlagProviderType.IN_MEMORY:
        flags_dict: dict[str, InMemoryFlag[Any]] = {}
        if in_memory_flags:
            for k, v in in_memory_flags.items():
                if isinstance(v, bool):
                    flags_dict[k] = InMemoryFlag(
                        state=InMemoryFlag.State.ENABLED,
                        default_variant="on" if v else "off",
                        variants={"on": True, "off": False},
                    )
                else:
                    flags_dict[k] = InMemoryFlag(
                        state=InMemoryFlag.State.ENABLED,
                        default_variant="default",
                        variants={"default": v},
                    )
        provider = InMemoryProvider(flags=flags_dict)
        openfeature.api.set_provider(provider)

    else:
        # Default fallback to in-memory provider
        provider = InMemoryProvider(flags={})
        openfeature.api.set_provider(provider)

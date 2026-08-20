"""Factory for initializing OpenFeature provider backends.

Notes/Architectural Intent:
    Decouples application setup from concrete OpenFeature provider implementations
    (Flagd, In-Memory, etc.), dynamically importing optional dependencies on demand.
"""

from __future__ import annotations

from typing import Any

import openfeature.api
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_flags.domain.models import (
    FeatureFlagProviderType,
    FlagProviderOptions,
)


def initialize_openfeature_provider(
    provider_type: FeatureFlagProviderType | str = FeatureFlagProviderType.IN_MEMORY,
    options: FlagProviderOptions | None = None,
    in_memory_flags: dict[str, Any] | None = None,
) -> None:
    """Initialize and register an OpenFeature provider backend globally.

    Args:
        provider_type: Target backend ("flagd", "in_memory", "env", etc.).
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
            config_mod = importlib.import_module(
                "openfeature.contrib.provider.flagd.config"
            )
            flagd_cls = flagd_mod.FlagdProvider
            cache_type_cls = config_mod.CacheType

            cache_val = cache_type_cls.LRU if opts.cache else cache_type_cls.DISABLED

            provider = flagd_cls(
                host=opts.host,
                port=opts.port,
                cache=cache_val,
                timeout=opts.timeout_ms,
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
        provider = InMemoryProvider(flags_dict)
        openfeature.api.set_provider(provider)


__all__ = [
    "initialize_openfeature_provider",
]

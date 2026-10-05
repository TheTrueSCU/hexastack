"""Factory for initializing OpenFeature provider backends.

Notes/Architectural Intent:
    Decouples application setup from concrete OpenFeature provider implementations
    (Flagd, In-Memory, etc.), dynamically importing optional dependencies on demand.
"""

from __future__ import annotations

import importlib
from typing import Any

import openfeature.api
from openfeature.provider import AbstractProvider
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_flags.domain.models import (
    FeatureFlagProviderType,
    FlagProviderOptions,
)


def _build_flagd_provider(opts: FlagProviderOptions) -> AbstractProvider:
    """Instantiate Flagd provider with cache and deadline configurations."""
    try:
        flagd_mod = importlib.import_module("openfeature.contrib.provider.flagd")
        config_mod = importlib.import_module(
            "openfeature.contrib.provider.flagd.config"
        )
        flagd_cls = flagd_mod.FlagdProvider
        cache_type_cls = config_mod.CacheType

        cache_val = cache_type_cls.LRU if opts.cache else cache_type_cls.DISABLED

        return flagd_cls(
            host=opts.host,
            port=opts.port,
            cache=cache_val,
            deadline_ms=opts.timeout_ms,
        )
    except (ImportError, AttributeError) as e:
        raise MissingDependencyError(
            "openfeature-provider-flagd is required for Flagd provider. "
            "Install with 'pip install hexastack-flags[flagd]'."
        ) from e


def _build_unleash_provider(opts: FlagProviderOptions) -> AbstractProvider:
    """Instantiate Unleash provider with custom URL, app name, and auth headers."""
    try:
        unleash_mod = importlib.import_module("openfeature.contrib.provider.unleash")
        unleash_cls = unleash_mod.UnleashProvider
        url = opts.extra.get("url", f"http://{opts.host}:{opts.port}/api")
        app_name = opts.extra.get("app_name", "hexastack-app")
        instance_id = opts.extra.get("instance_id", "hexastack-instance")
        api_token = opts.extra.get("api_token", None)

        return unleash_cls(
            url=url,
            app_name=app_name,
            instance_id=instance_id,
            custom_headers={"Authorization": api_token} if api_token else {},
        )
    except (ImportError, AttributeError) as e:
        raise MissingDependencyError(
            "openfeature-provider-unleash is required for Unleash provider. "
            "Install with 'pip install hexastack-flags[unleash]'."
        ) from e


def _build_flipt_provider(opts: FlagProviderOptions) -> AbstractProvider:
    """Instantiate Flipt provider with endpoint URL."""
    try:
        flipt_mod = importlib.import_module("openfeature.contrib.provider.flipt")
        flipt_cls = flipt_mod.FliptProvider
        url = opts.extra.get("url", f"http://{opts.host}:{opts.port}")

        return flipt_cls(url=url)
    except (ImportError, AttributeError) as e:
        raise MissingDependencyError(
            "openfeature-provider-flipt is required for Flipt provider. "
            "Install with 'pip install hexastack-flags[flipt]'."
        ) from e


def _build_in_memory_provider(
    in_memory_flags: dict[str, Any] | None = None,
) -> AbstractProvider:
    """Instantiate in-memory provider populated with initial flags dictionary."""
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
    return InMemoryProvider(flags_dict)


def initialize_openfeature_provider(
    provider_type: FeatureFlagProviderType | str = FeatureFlagProviderType.IN_MEMORY,
    options: FlagProviderOptions | None = None,
    in_memory_flags: dict[str, Any] | None = None,
) -> None:
    """Initialize and register an OpenFeature provider backend globally.

    Args:
        provider_type: Target backend ("flagd", "in_memory", "env", "unleash", "flipt").
        options: Configuration options (host, port, cache, etc.).
        in_memory_flags: Initial flags dict when using in_memory provider.

    Raises:
        MissingDependencyError: If a provider extra (e.g. openfeature-provider-flagd) is missing.
    """
    opts = options or FlagProviderOptions()
    p_type = str(provider_type).lower()

    if p_type == FeatureFlagProviderType.FLAGD:
        provider = _build_flagd_provider(opts)
    elif p_type == FeatureFlagProviderType.UNLEASH:
        provider = _build_unleash_provider(opts)
    elif p_type == FeatureFlagProviderType.FLIPT:
        provider = _build_flipt_provider(opts)
    else:
        provider = _build_in_memory_provider(in_memory_flags)

    openfeature.api.set_provider(provider)


__all__ = [
    "initialize_openfeature_provider",
]

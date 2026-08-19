import importlib.metadata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import BaseModel
from rodi import Container

from hexastack_core.adapters.feature_flags.config import ConfigFeatureFlagAdapter
from hexastack_core.infra.autodiscovery import (
    DiscoveryVisitor,
    scan_modules,
)
from hexastack_core.infra.config import HexastackConfig
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_core.ports.feature_flags import FeatureFlagPort


@dataclass
class BootstrapContext:
    """Contextual runtime state passed across bootstrap phases.

    Notes/Architectural Intent:
        Aggregates DI container, configuration models, registered discovery visitors,
        feature flag evaluation, and module scanning metadata for single-pass multi-subsystem discovery.
    """

    container: Container
    config: HexastackConfig | None
    config_registry: ConfigRegistry
    packages_to_scan: list[str | ModuleType] | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    visitors: list[DiscoveryVisitor] = field(default_factory=list)
    flags: FeatureFlagPort = field(default_factory=ConfigFeatureFlagAdapter)

    def get_config[T: BaseModel](
        self,
        section: str,
        schema_cls: type[T],
        default: T | None = None,
    ) -> T:
        """Retrieve typed configuration section or construct default schema instance.

        Notes/Architectural Intent:
            Eliminates repetitive configuration section lookup boilerplate across
            subsystem bootstrappers.

        Args:
            section: Section name registered in configuration registry.
            schema_cls: Pydantic BaseModel class for the section.
            default: Optional fallback instance if section is not present in config.

        Returns:
            The parsed section model instance, or a new default schema_cls() instance.
        """
        if self.config is not None:
            val = self.config.get_section(section, schema_cls)
            if val is not None:
                return val
        return default if default is not None else schema_cls()

    def register_visitor(self, visitor: DiscoveryVisitor) -> None:
        """Register a visitor callback to participate in single-pass module scanning.

        Args:
            visitor: Callable receiving (discovered_member, module).
        """
        self.visitors.append(visitor)


@dataclass(frozen=True)
class BootstrapResult:
    """Dataclass holding all initialized registries, container, and extension state.

    Notes/Architectural Intent:
        Encapsulates the complete bootstrapped application runtime context for web,
        CLI, and test execution environments.
    """

    container: Container
    config: HexastackConfig | None
    config_registry: ConfigRegistry
    bootstrappers: list[BootstrapperPort]
    properties: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a property stored by a bootstrap extension.

        Args:
            key: Target property name identifier.
            default: Default value if key is not found.

        Returns:
            The stored property value or default.
        """
        return self.properties.get(key, default)


__all__ = [
    "BootstrapContext",
    "BootstrapResult",
    "bootstrap",
]


def _discover_bootstrappers() -> list[BootstrapperPort]:
    """Discover installed bootstrap extensions via Python entry points."""
    discovered: list[BootstrapperPort] = []
    try:
        eps = importlib.metadata.entry_points(group="hexastack.bootstrappers")
        for ep in eps:
            loaded = ep.load()
            instance = loaded() if isinstance(loaded, type) else loaded
            if isinstance(instance, BootstrapperPort):
                discovered.append(instance)
    except Exception:  # noqa: BLE001, S110
        pass
    return discovered


def _collect_and_sort_bootstrappers(
    bootstrappers: list[BootstrapperPort] | None,
    auto_discover: bool,
) -> list[BootstrapperPort]:
    """Collect, deduplicate, and sort all configured and discovered bootstrappers."""
    collected: list[BootstrapperPort] = list(bootstrappers or [])
    if auto_discover:
        auto_list = _discover_bootstrappers()
        existing_types = {type(b) for b in collected}
        for auto_b in auto_list:
            if type(auto_b) not in existing_types:
                collected.append(auto_b)
                existing_types.add(type(auto_b))

    return sorted(collected, key=lambda b: getattr(b, "order", 50))


def bootstrap(
    config_path: str | Path | None = None,
    bootstrappers: list[BootstrapperPort] | None = None,
    auto_discover: bool = True,
    container: Container | None = None,
    configure_container: Callable[[Container], None] | None = None,
    packages_to_scan: list[str | ModuleType] | None = None,
) -> BootstrapResult:
    """Bootstrap a complete Hexastack application runtime through modular extensions.

    Notes/Architectural Intent:
        Orchestrates Phase 1 config registration, TOML loading, Phase 2 subsystem configuration,
        single-pass reflective module scanning across all registered visitors, and container customization.

    Args:
        config_path: Optional path to a TOML configuration file.
        bootstrappers: Optional explicit list of BootstrapperPort extensions.
        auto_discover: If True, discovers installed extensions via entry points.
        container: Optional pre-configured rodi Container instance.
        configure_container: Optional user hook to customize container bindings.
        packages_to_scan: Optional list of packages or modules to scan for decorators.

    Returns:
        BootstrapResult containing configured container, config, and properties.
    """
    di = container or Container()

    # 1. Collect & deduplicate bootstrappers
    sorted_bootstrappers = _collect_and_sort_bootstrappers(bootstrappers, auto_discover)

    # 2. Phase 1: Config Registration
    config_reg = ConfigRegistry()
    for b in sorted_bootstrappers:
        b.register_config(config_reg)

    di.add_instance(config_reg, declared_class=ConfigRegistry)

    # 3. Load TOML Configuration if available
    loaded_config: HexastackConfig | None = None
    if config_path and Path(config_path).exists():
        loaded_config = config_reg.load_config_toml(config_path)

    # 4. Phase 2: Runtime Subsystem Configuration
    flags_adapter = ConfigFeatureFlagAdapter(config=loaded_config)
    di.add_instance(flags_adapter, declared_class=FeatureFlagPort)

    context = BootstrapContext(
        container=di,
        config=loaded_config,
        config_registry=config_reg,
        packages_to_scan=packages_to_scan,
        properties={},
        flags=flags_adapter,
    )

    for b in sorted_bootstrappers:
        b.configure(context)

    # 5. Phase 3: Single-Pass Reflective Scanning
    effective_packages = packages_to_scan or context.properties.get("packages_to_scan")
    if effective_packages and context.visitors:
        scan_modules(effective_packages, context.visitors)

    # 6. User container customization hook
    if configure_container is not None:
        configure_container(di)

    return BootstrapResult(
        container=di,
        config=loaded_config,
        config_registry=config_reg,
        bootstrappers=sorted_bootstrappers,
        properties=context.properties,
    )

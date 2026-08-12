import importlib.metadata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from rodi import Container

from hexastack_core.infra.config import HexastackConfig
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort


@dataclass
class BootstrapContext:
    """Contextual runtime state passed across bootstrap phases.

    Notes/Architectural Intent:
        Aggregates DI container, configuration models, and module scanning metadata
        for extension modules to populate without direct inter-package couplings.
    """

    container: Container
    config: HexastackConfig | None
    config_registry: ConfigRegistry
    packages_to_scan: list[str | ModuleType] | None = None
    properties: dict[str, Any] = field(default_factory=dict)


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

        Raises:
            None.
        """
        return self.properties.get(key, default)


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


def bootstrap(
    config_path: str | Path | None = None,
    bootstrappers: list[BootstrapperPort] | None = None,
    auto_discover: bool = True,
    container: Container | None = None,
    configure_container: Callable[[Container], None] | None = None,
    packages_to_scan: list[str | ModuleType] | None = None,
) -> BootstrapResult:
    """Bootstrap a complete Hexastack application runtime through modular extensions.

    Args:
        config_path: Optional path to a TOML configuration file.
        bootstrappers: Optional explicit list of BootstrapperPort extensions.
        auto_discover: If True, discovers installed extensions via entry points.
        container: Optional pre-configured rodi Container instance.
        configure_container: Optional user hook to customize container bindings.
        packages_to_scan: Optional list of packages or modules to scan for decorators.

    Returns:
        BootstrapResult containing configured container, config, and properties.

    Raises:
        None.
    """
    di = container or Container()

    # 1. Collect & deduplicate bootstrappers
    collected: list[BootstrapperPort] = list(bootstrappers or [])
    if auto_discover:
        auto_list = _discover_bootstrappers()
        existing_types = {type(b) for b in collected}
        for auto_b in auto_list:
            if type(auto_b) not in existing_types:
                collected.append(auto_b)
                existing_types.add(type(auto_b))

    # Sort bootstrappers by order ascending
    sorted_bootstrappers = sorted(collected, key=lambda b: getattr(b, "order", 50))

    # 2. Phase 1: Config Registration
    config_reg = ConfigRegistry()
    for b in sorted_bootstrappers:
        b.register_config(config_reg)

    di.add_instance(config_reg, declared_class=ConfigRegistry)

    # 3. Load TOML Configuration if available
    loaded_config: HexastackConfig | None = None
    if config_path and Path(config_path).exists():
        loaded_config = config_reg.load_config_toml(config_path)

    # 4. Phase 2: Runtime Configuration
    context = BootstrapContext(
        container=di,
        config=loaded_config,
        config_registry=config_reg,
        packages_to_scan=packages_to_scan,
        properties={},
    )

    for b in sorted_bootstrappers:
        b.configure(context)

    # 5. User container customization hook
    if configure_container is not None:
        configure_container(di)

    return BootstrapResult(
        container=di,
        config=loaded_config,
        config_registry=config_reg,
        bootstrappers=sorted_bootstrappers,
        properties=context.properties,
    )

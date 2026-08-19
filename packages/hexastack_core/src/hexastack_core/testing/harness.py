"""Lightweight in-memory test runtime and DI harness for Hexastack applications.

Notes/Architectural Intent:
    Provides a one-liner test runtime factory that boots the DI container with
    clean in-memory test doubles (InMemoryFeatureFlagAdapter, RecordingEventBus)
    and custom port overrides for frictionless unit/integration testing.
"""

from collections.abc import Sequence
from typing import Any

from rodi import Container

from hexastack_core.adapters.feature_flags.in_memory import InMemoryFeatureFlagAdapter
from hexastack_core.infra.bootstrap import BootstrapResult, bootstrap
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_core.ports.feature_flags import FeatureFlagPort

__all__ = [
    "create_test_runtime",
    "TestRuntime",
]


class TestRuntime:
    """Encapsulates an isolated test environment with access to the DI container and test doubles."""

    __test__ = False  # Prevent Pytest from attempting to collect TestRuntime as a test suite class

    def __init__(
        self,
        bootstrap_result: BootstrapResult,
        flags: InMemoryFeatureFlagAdapter,
    ) -> None:
        self.result = bootstrap_result
        self.container: Container = bootstrap_result.container
        self.flags: InMemoryFeatureFlagAdapter = flags

    def resolve(self, service_type: type[Any]) -> Any:
        """Convenience resolution helper from the test DI container."""
        return self.container.resolve(service_type)


def create_test_runtime(
    packages_to_scan: Sequence[str] = (),
    *,
    flag_overrides: dict[str, Any] | None = None,
    instances: dict[type[Any], Any] | None = None,
    bootstrappers: Sequence[BootstrapperPort] | None = None,
    auto_discover: bool = False,
    container: Container | None = None,
) -> TestRuntime:
    """Boot an isolated Hexastack test runtime configured with in-memory adapters.

    Args:
        packages_to_scan: List of package names to reflectively scan for handlers and routes.
        flag_overrides: Initial feature flag states (e.g. {'features.beta': True}).
        instances: Pre-configured service instances to register into the test DI container.
        bootstrappers: Optional custom bootstrappers to include.
        auto_discover: Whether to auto-discover entrypoint bootstrappers (defaults to False in tests).
        container: Optional existing rodi Container instance.

    Returns:
        TestRuntime instance containing the configured container and feature flag double.
    """
    flags = InMemoryFeatureFlagAdapter(flags=flag_overrides or {})
    di = container or Container()
    di.add_instance(flags, declared_class=FeatureFlagPort)

    if instances:
        for service_cls, instance in instances.items():
            di.add_instance(instance, declared_class=service_cls)

    # Execute deterministic bootstrap with pre-configured container
    bootstrap_result = bootstrap(
        packages_to_scan=list(packages_to_scan) if packages_to_scan else None,
        container=di,
        bootstrappers=list(bootstrappers) if bootstrappers else None,
        auto_discover=auto_discover,
    )

    return TestRuntime(bootstrap_result=bootstrap_result, flags=flags)

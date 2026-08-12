from hexastack_core.domain import Command, Generic, Query


class SystemInfoDTO(Generic):
    """Data transfer object describing installed Hexastack runtime environment.

    Notes/Architectural Intent:
        Carries versioning, installed packages, and optional dependency statuses.
    """

    python_version: str
    platform: str
    installed_packages: dict[str, str]
    optional_dependencies: dict[str, bool]


class GetSystemInfoQuery(Query[SystemInfoDTO]):
    """Query requesting system environment diagnostics and optional dependency statuses.

    Notes/Architectural Intent:
        Diagnostic query resolved by GetSystemInfoHandler.
    """


class RegistryInfoDTO(Generic):
    """Data transfer object describing registered CQRS handlers and routes."""

    commands: list[str]
    queries: list[str]
    configs: list[str]


class InspectRegistryQuery(Query[RegistryInfoDTO]):
    """Query requesting active registry introspection.

    Notes/Architectural Intent:
        Returns all registered command, query, and config bindings.
    """


class PingDemoCommand(Command):
    """Demo command for testing live CQRS pipeline execution.

    Notes/Architectural Intent:
        Verifies end-to-end command dispatching and correlation ID tracing.
    """

    message: str = "ping"


class PingDemoDTO(Generic):
    """Response payload for live ping demo."""

    reply: str
    correlation_id: str


__all__ = [
    "GetSystemInfoQuery",
    "InspectRegistryQuery",
    "PingDemoCommand",
    "PingDemoDTO",
    "RegistryInfoDTO",
    "SystemInfoDTO",
]

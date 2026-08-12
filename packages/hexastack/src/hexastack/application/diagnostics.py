import importlib.metadata
import importlib.util
import platform
import sys

from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.utils.context import get_correlation_id
from hexastack_cqrs.infra.decorators import (
    command_handler,
    query_handler,
)
from hexastack_cqrs.infra.registries.handler import HandlerRegistry

from hexastack.domain.diagnostics import (
    GetSystemInfoQuery,
    InspectRegistryQuery,
    PingDemoCommand,
    PingDemoDTO,
    RegistryInfoDTO,
    SystemInfoDTO,
)

<<<<<<< Updated upstream
_KNOWN_PACKAGES = sorted([
    "hexastack",
    "hexastack-cli",
    "hexastack-core",
    "hexastack-cqrs",
    "hexastack-fastapi",
    "hexastack-logging",
])

_OPTIONAL_LIBS = sorted([
    "fastapi",
    "huey",
    "loguru",
    "rich",
    "structlog",
    "typer",
    "uvicorn",
])
=======
_KNOWN_PACKAGES = sorted(
    [
        "hexastack",
        "hexastack-cli",
        "hexastack-core",
        "hexastack-cqrs",
        "hexastack-db",
        "hexastack-fastapi",
        "hexastack-logging",
    ]
)

_OPTIONAL_LIBS = sorted(
    [
        "fastapi",
        "huey",
        "loguru",
        "rich",
        "sqlalchemy",
        "structlog",
        "typer",
        "uvicorn",
    ]
)
>>>>>>> Stashed changes


@query_handler(GetSystemInfoQuery)
class GetSystemInfoHandler:
    """Handler executing GetSystemInfoQuery.

    Notes/Architectural Intent:
        Gathers runtime metadata, package versions, and optional dependency statuses
        in alphabetical order to report system health in CLI and REST endpoints.
    """

    def __call__(self, qry: GetSystemInfoQuery) -> SystemInfoDTO:
        """Collect system diagnostics.

        Args:
            qry: The GetSystemInfoQuery request.

        Returns:
            SystemInfoDTO instance.

        Raises:
            None.
        """
        installed: dict[str, str] = {}
        for pkg in _KNOWN_PACKAGES:
            try:
                installed[pkg] = importlib.metadata.version(pkg)
            except importlib.metadata.PackageNotFoundError:
                installed[pkg] = "not installed"

        opt_status: dict[str, bool] = {}
        for lib in _OPTIONAL_LIBS:
            opt_status[lib] = importlib.util.find_spec(lib) is not None

        sorted_installed = {k: installed[k] for k in sorted(installed)}
        sorted_opt_status = {k: opt_status[k] for k in sorted(opt_status)}

        return SystemInfoDTO(
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            installed_packages=sorted_installed,
            optional_dependencies=sorted_opt_status,
        )


@query_handler(InspectRegistryQuery)
class InspectRegistryHandler:
    """Handler introspecting active HandlerRegistry and ConfigRegistry.

    Notes/Architectural Intent:
        Exposes registered CQRS message routes and configuration schemas in alphabetical order.
    """

    def __init__(
        self,
        handler_registry: HandlerRegistry,
        config_registry: ConfigRegistry,
    ) -> None:
        """Initialize with required registries."""
        self._handlers = handler_registry
        self._configs = config_registry

    def __call__(self, qry: InspectRegistryQuery) -> RegistryInfoDTO:
        """Introspect registries.

        Args:
            qry: The InspectRegistryQuery request.

        Returns:
            RegistryInfoDTO with command, query, and config names.

        Raises:
            None.
        """
        commands: list[str] = []
        queries: list[str] = []
        configs: list[str] = []

        if self._handlers is not None:
            for cls in self._handlers.all:
                name = getattr(cls, "__name__", str(cls))
<<<<<<< Updated upstream
                if "Command" in name or issubclass(
                    cls, type("Command", (), {})
                ):
=======
                if "Command" in name or issubclass(cls, type("Command", (), {})):
>>>>>>> Stashed changes
                    commands.append(name)
                else:
                    queries.append(name)

        if self._configs is not None:
            configs = list(self._configs.all.keys())

        return RegistryInfoDTO(
            commands=sorted(commands),
            queries=sorted(queries),
            configs=sorted(configs),
        )


@command_handler(PingDemoCommand)
class PingDemoHandler:
    """Handler processing live PingDemoCommand."""

    def __call__(self, cmd: PingDemoCommand) -> PingDemoDTO:
        """Process ping demo command.

        Args:
            cmd: The PingDemoCommand payload.

        Returns:
            PingDemoDTO with pong reply and correlation ID.

        Raises:
            None.
        """
        cid = get_correlation_id()
        return PingDemoDTO(
            reply=f"PONG: {cmd.message}",
            correlation_id=cid or "none",
        )


__all__ = [
    "GetSystemInfoHandler",
    "InspectRegistryHandler",
    "PingDemoHandler",
]

import importlib.metadata
import importlib.util
import platform
import re
import sys
import tomllib
from pathlib import Path

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

_DEFAULT_KNOWN_PACKAGES = [
    "hexastack",
    "hexastack-ai",
    "hexastack-auth",
    "hexastack-cli",
    "hexastack-core",
    "hexastack-cqrs",
    "hexastack-db",
    "hexastack-events",
    "hexastack-fastapi",
    "hexastack-graphql",
    "hexastack-grpc",
    "hexastack-logging",
    "hexastack-mcp",
    "hexastack-otel",
]

# Mapping between package/distribution names and Python importable module names
_PKG_TO_MODULE_MAP = {
    "alembic": "alembic",
    "cloudevents": "cloudevents",
    "fastapi": "fastapi",
    "grpcio": "grpc",
    "grpc": "grpc",
    "huey": "huey",
    "instructor": "instructor",
    "jwt": "jwt",
    "litellm": "litellm",
    "loguru": "loguru",
    "mcp": "mcp",
    "opentelemetry-api": "opentelemetry",
    "opentelemetry-sdk": "opentelemetry",
    "opentelemetry": "opentelemetry",
    "protobuf": "google.protobuf",
    "pydantic": "pydantic",
    "pydantic-ai": "pydantic_ai",
    "pydantic_ai": "pydantic_ai",
    "pyjwt": "jwt",
    "rich": "rich",
    "rodi": "rodi",
    "sqlalchemy": "sqlalchemy",
    "strawberry-graphql": "strawberry",
    "strawberry": "strawberry",
    "structlog": "structlog",
    "tenacity": "tenacity",
    "typer": "typer",
    "uvicorn": "uvicorn",
}


def _find_pyproject_toml() -> Path | None:
    """Locate root or umbrella pyproject.toml in the filesystem."""
    curr = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = curr / "pyproject.toml"
        if candidate.exists():
            return candidate
        curr = curr.parent

    cwd_candidate = Path.cwd() / "pyproject.toml"
    if cwd_candidate.exists():
        return cwd_candidate

    return None


def _parse_pyproject_metadata() -> tuple[list[str], dict[str, list[str]]]:
    """Parse pyproject.toml to extract workspace packages and optional extras."""
    packages = list(_DEFAULT_KNOWN_PACKAGES)
    extras: dict[str, list[str]] = {}

    pyproject_path = _find_pyproject_toml()
    if pyproject_path is not None:
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            tool_uv = data.get("tool", {}).get("uv", {})
            members = tool_uv.get("workspace", {}).get("members", [])
            for member in members:
                pkg_name = member.replace("packages/", "").replace("_", "-")
                if pkg_name not in packages:
                    packages.append(pkg_name)

            opt_deps = data.get("project", {}).get("optional-dependencies", {})
            for extra, deps in opt_deps.items():
                extras[extra] = deps
        except (OSError, tomllib.TOMLDecodeError):
            pass

    return sorted(set(packages)), extras


def _is_module_available(module_or_pkg_name: str) -> bool:
    """Check if a module or package is available in the current environment."""
    mod_name = _PKG_TO_MODULE_MAP.get(
        module_or_pkg_name, module_or_pkg_name.replace("-", "_")
    )
    if importlib.util.find_spec(mod_name) is not None:
        return True
    try:
        importlib.metadata.version(module_or_pkg_name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def _clean_req_name(req_str: str) -> tuple[str, bool]:
    """Parse requirement string into (clean_package_name, is_extra)."""
    is_extra = "extra ==" in req_str or "extra ==" in req_str.replace(" ", "")
    clean = re.split(r"[><=~!;\[\s]", req_str)[0].strip()
    return clean, is_extra


@query_handler(GetSystemInfoQuery)
class GetSystemInfoHandler:
    """Handler executing GetSystemInfoQuery with dynamic dependency classification.

    Notes/Architectural Intent:
        Gathers runtime metadata, package versions, and smartly categorizes 3rd-party
        dependencies into 'required' vs 'optional' based on which Hexastack packages
        are currently installed.
    """

    def __call__(self, qry: GetSystemInfoQuery) -> SystemInfoDTO:
        """Collect system diagnostics.

        Args:
            qry: The GetSystemInfoQuery request.

        Returns:
            SystemInfoDTO instance.
        """
        known_packages, known_extras = _parse_pyproject_metadata()

        # 1. Discover installed 1st-party Hexastack distributions
        installed_hexastack: dict[str, str] = {}
        installed_package_names: set[str] = set()

        for pkg in known_packages:
            try:
                ver = importlib.metadata.version(pkg)
                installed_hexastack[pkg] = ver
                installed_package_names.add(pkg)
            except importlib.metadata.PackageNotFoundError:
                installed_hexastack[pkg] = "not installed"

        # 2. Inspect dependencies of currently installed Hexastack packages
        required_3rd_party: set[str] = set()
        optional_3rd_party: set[str] = set()

        for pkg in installed_package_names:
            try:
                requirements = importlib.metadata.requires(pkg) or []
            except importlib.metadata.PackageNotFoundError:
                requirements = []

            for req_str in requirements:
                req_name, is_extra = _clean_req_name(req_str)
                if not req_name or req_name in _DEFAULT_KNOWN_PACKAGES:
                    continue

                if is_extra:
                    optional_3rd_party.add(req_name)
                else:
                    required_3rd_party.add(req_name)

        # A dependency required by any installed package takes precedence over optional
        optional_3rd_party -= required_3rd_party

        # 3. Build status dictionaries
        required_status: dict[str, bool] = {
            dep: _is_module_available(dep) for dep in sorted(required_3rd_party)
        }
        optional_status: dict[str, bool] = {
            dep: _is_module_available(dep) for dep in sorted(optional_3rd_party)
        }

        # 4. Check umbrella extras availability
        extras_status: dict[str, bool] = {}
        if known_extras:
            for extra_name in known_extras:
                mod_name = f"hexastack_{extra_name}"
                extras_status[extra_name] = importlib.util.find_spec(
                    mod_name
                ) is not None or _is_module_available(extra_name)

        sorted_installed = {
            k: installed_hexastack[k] for k in sorted(installed_hexastack)
        }
        sorted_extras = {k: extras_status[k] for k in sorted(extras_status)}

        return SystemInfoDTO(
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            installed_packages=sorted_installed,
            required_dependencies=required_status,
            optional_dependencies=optional_status,
            extras=sorted_extras,
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
        """
        commands: list[str] = []
        queries: list[str] = []
        configs: list[str] = []

        if self._handlers is not None:
            for cls in self._handlers.all:
                name = getattr(cls, "__name__", str(cls))
                if "Command" in name or issubclass(cls, type("Command", (), {})):
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
    """Handler executing PingDemoCommand to test CQRS execution.

    Notes/Architectural Intent:
        Demonstrates live message routing and context extraction (correlation_id).
    """

    def __call__(self, cmd: PingDemoCommand) -> PingDemoDTO:
        """Execute ping command.

        Args:
            cmd: PingDemoCommand instance.

        Returns:
            PingDemoDTO with response message and correlation ID.
        """
        cid = get_correlation_id() or "local-dev"
        return PingDemoDTO(
            reply=f"PONG: {cmd.message}",
            correlation_id=cid,
        )


__all__ = [
    "GetSystemInfoHandler",
    "InspectRegistryHandler",
    "PingDemoHandler",
]

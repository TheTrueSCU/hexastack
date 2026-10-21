"""Diagnostic runtime orchestration and capability inspection services.

Notes/Architectural Intent:
    Application-level orchestration layer coordinating framework bootstrap,
    Protobuf compilation, and MCP capability inspection for developer tooling.
    Decouples driving CLI presentation adapters from infrastructure internals (ADR-001).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hexastack_core.infra.bootstrap import BootstrapResult


def create_diagnostics_runtime() -> BootstrapResult:
    """Bootstrap and return the diagnostic runtime context for devtools.

    Returns:
        BootstrapResult containing configured container and properties.

    Notes/Architectural Intent:
        Application orchestration service that bootstraps the diagnostic container
        without coupling driving CLI adapters directly to infra bootstrap.
    """
    import hexastack.application.diagnostics as diag_module
    from hexastack_core.infra.bootstrap import bootstrap

    return bootstrap(packages_to_scan=[diag_module])


def compile_protobuf_stubs(
    out_dir: str,
    proto_files: list[str] | None = None,
) -> list[Path]:
    """Compile protobuf stubs from files or registry metadata.

    Args:
        out_dir: Target output directory for generated files.
        proto_files: Optional list of explicit .proto file paths.

    Returns:
        List of generated file Paths.

    Notes/Architectural Intent:
        Application helper that delegates Protobuf compilation without coupling CLI adapters
        directly to gRPC compiler infrastructure.
    """
    from hexastack_grpc.infra.compiler import ProtoCompiler
    from hexastack_grpc.infra.registries.proto import get_proto_registry

    registry = get_proto_registry()
    entries = registry.entries

    if proto_files:
        return ProtoCompiler.compile_files(
            proto_files=proto_files,
            output_dir=Path(out_dir),
        )
    if entries:
        return ProtoCompiler.compile_metadata(
            entries=entries,
            output_dir=Path(out_dir),
        )

    default_proto_dir = Path("protos")
    if default_proto_dir.exists():
        found_files = list(default_proto_dir.glob("**/*.proto"))
        if found_files:
            return ProtoCompiler.compile_files(
                proto_files=found_files,
                include_dirs=[default_proto_dir],
                output_dir=Path(out_dir),
            )
    return []


def get_grpc_capabilities() -> tuple[list[Any], list[Any]]:
    """Retrieve registered gRPC protobuf schemas and services.

    Returns:
        Tuple of (proto_entries_list, grpc_services_list).

    Notes/Architectural Intent:
        Introspects registered gRPC capabilities for devtools inspection.
    """
    from hexastack_grpc.infra.decorators import get_grpc_registry
    from hexastack_grpc.infra.registries.proto import get_proto_registry

    proto_reg = get_proto_registry()
    grpc_reg = get_grpc_registry()
    return list(proto_reg.entries), list(getattr(grpc_reg, "_services", []))


def get_mcp_capabilities() -> tuple[list[Any], list[Any], list[Any]]:
    """Retrieve registered MCP tools, prompt templates, and resources.

    Returns:
        Tuple of (tools_list, prompts_list, resources_list).

    Notes/Architectural Intent:
        Introspects registered MCP tools, prompts, and resources for devtools inspection.
    """
    from hexastack_mcp.infra.decorators import get_mcp_registry

    registry = get_mcp_registry()
    return list(registry.tools), list(registry.prompts), list(registry.resources)


__all__ = [
    "compile_protobuf_stubs",
    "create_diagnostics_runtime",
    "get_grpc_capabilities",
    "get_mcp_capabilities",
]

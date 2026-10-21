"""Hexastack architecture diagnostics and system inspection application handlers."""

from hexastack.application.diagnostics.handlers import (
    GetSystemInfoHandler,
    InspectRegistryHandler,
    PingDemoHandler,
)
from hexastack.application.diagnostics.runtime import (
    compile_protobuf_stubs,
    create_diagnostics_runtime,
    get_grpc_capabilities,
    get_mcp_capabilities,
)

__all__ = [
    "compile_protobuf_stubs",
    "create_diagnostics_runtime",
    "get_grpc_capabilities",
    "get_mcp_capabilities",
    "GetSystemInfoHandler",
    "InspectRegistryHandler",
    "PingDemoHandler",
]

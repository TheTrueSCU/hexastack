"""Registry for collecting and indexing Protobuf schemas across the application.

Notes/Architectural Intent:
    Maintains a unified catalog of all @proto_schema and @proto_file definitions
    for in-process compilation via ProtoCompiler.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hexastack_grpc.domain.models import ProtoSchemaMetadata


class ProtoRegistry:
    """Registry maintaining registered protobuf schemas and file associations."""

    def __init__(self) -> None:
        self._entries: list[ProtoSchemaMetadata] = []

    def register_schema(
        self,
        target: Any,
        message_name: str,
        schema: str,
        service_name: str | None = None,
        rpc_name: str | None = None,
    ) -> ProtoSchemaMetadata:
        """Register an inline protobuf schema string."""
        meta = ProtoSchemaMetadata(
            target=target,
            message_name=message_name,
            schema=schema.strip(),
            service_name=service_name,
            rpc_name=rpc_name,
        )
        self._entries.append(meta)
        return meta

    def register_file(
        self,
        target: Any,
        message_name: str,
        file_path: str | Path,
        service_name: str | None = None,
        rpc_name: str | None = None,
    ) -> ProtoSchemaMetadata:
        """Register an external .proto file reference."""
        path_obj = Path(file_path)
        meta = ProtoSchemaMetadata(
            target=target,
            message_name=message_name,
            file_path=path_obj,
            service_name=service_name,
            rpc_name=rpc_name,
        )
        self._entries.append(meta)
        return meta

    @property
    def entries(self) -> list[ProtoSchemaMetadata]:
        """Return all registered proto metadata entries."""
        return list(self._entries)

    def clear(self) -> None:
        """Clear all registered schemas."""
        self._entries.clear()


_default_proto_registry = ProtoRegistry()


def get_proto_registry() -> ProtoRegistry:
    """Return the global default ProtoRegistry instance."""
    return _default_proto_registry


__all__ = [
    "get_proto_registry",
    "ProtoRegistry",
]

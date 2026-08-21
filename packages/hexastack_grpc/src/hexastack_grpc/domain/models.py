"""Domain models for Protobuf schema metadata and bindings.

Notes/Architectural Intent:
    Encapsulates schema references (inline strings vs external .proto files)
    associated with CQRS Commands, Queries, and gRPC servicers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProtoSchemaMetadata:
    """Metadata describing an inline or file-referenced protobuf schema."""

    target: Any
    message_name: str
    schema: str | None = None
    file_path: Path | None = None
    service_name: str | None = None
    rpc_name: str | None = None


__all__ = [
    "ProtoSchemaMetadata",
]

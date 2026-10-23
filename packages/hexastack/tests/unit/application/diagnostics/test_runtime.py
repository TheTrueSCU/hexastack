"""Unit tests for diagnostic runtime orchestration and capability inspection services.

Notes/Architectural Intent:
    Verifies that create_diagnostics_runtime, compile_protobuf_stubs, get_grpc_capabilities,
    and get_mcp_capabilities execute cleanly, resolving dependencies and returning
    structured diagnostic metadata without side effects.
"""

from pathlib import Path
from unittest.mock import patch

from hexastack.application.diagnostics.runtime import (
    compile_protobuf_stubs,
    create_diagnostics_runtime,
    get_grpc_capabilities,
    get_mcp_capabilities,
)


def test_create_diagnostics_runtime():
    """Verify create_diagnostics_runtime bootstraps container and discovers handlers."""
    result = create_diagnostics_runtime()
    container = result.container
    assert container is not None
    assert result.config_registry is not None


def test_compile_protobuf_stubs_empty(tmp_path: Path):
    """Verify compile_protobuf_stubs handles empty proto files and returns empty list."""
    out_dir = str(tmp_path / "gen_grpc")
    with patch(
        "hexastack_grpc.infra.registries.proto.get_proto_registry"
    ) as mock_get_reg:
        mock_reg = mock_get_reg.return_value
        mock_reg.entries = []
        generated = compile_protobuf_stubs(out_dir=out_dir, proto_files=None)
        assert generated == []


def test_compile_protobuf_stubs_with_registry(tmp_path: Path):
    """Verify compile_protobuf_stubs compiles metadata when entries exist in registry."""
    out_dir = str(tmp_path / "gen_grpc")
    with (
        patch(
            "hexastack_grpc.infra.registries.proto.get_proto_registry"
        ) as mock_get_reg,
        patch(
            "hexastack_grpc.infra.compiler.ProtoCompiler.compile_metadata",
            return_value=[Path(out_dir) / "stub_pb2.py"],
        ) as mock_compile,
    ):
        mock_reg = mock_get_reg.return_value
        mock_reg.entries = ["dummy_entry"]
        generated = compile_protobuf_stubs(out_dir=out_dir, proto_files=None)
        assert len(generated) == 1
        mock_compile.assert_called_once()


def test_compile_protobuf_stubs_with_files(tmp_path: Path):
    """Verify compile_protobuf_stubs delegates to ProtoCompiler with explicit files."""
    out_dir = str(tmp_path / "gen_grpc")
    dummy_proto = tmp_path / "demo.proto"
    dummy_proto.write_text('syntax = "proto3"; message Demo {}')

    with patch(
        "hexastack_grpc.infra.compiler.ProtoCompiler.compile_files",
        return_value=[Path(out_dir) / "demo_pb2.py"],
    ) as mock_compile:
        generated = compile_protobuf_stubs(
            out_dir=out_dir, proto_files=[str(dummy_proto)]
        )
        assert len(generated) == 1
        assert generated[0].name == "demo_pb2.py"
        mock_compile.assert_called_once()


def test_get_grpc_capabilities():
    """Verify get_grpc_capabilities returns discovered proto entries and services."""
    entries, services = get_grpc_capabilities()
    assert isinstance(entries, list)
    assert isinstance(services, list)


def test_get_mcp_capabilities():
    """Verify get_mcp_capabilities returns discovered tools, prompts, and resources."""
    tools, prompts, resources = get_mcp_capabilities()
    assert isinstance(tools, list)
    assert isinstance(prompts, list)
    assert isinstance(resources, list)

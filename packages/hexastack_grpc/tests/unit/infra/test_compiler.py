"""Unit tests for ProtoCompiler and @proto_schema / @proto_file decorators."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hexastack_grpc.infra.compiler import ProtoCompiler
from hexastack_grpc.infra.decorators import (
    get_proto_registry,
    proto_file,
    proto_schema,
)


def test_proto_schema_decorator_registers_and_compiles():
    """Verify inline schema decoration and in-process compilation."""
    registry = get_proto_registry()
    registry.clear()

    inline_idl = """
    syntax = "proto3";
    package sample.v1;

    message SampleMessage {
        string id = 1;
        string name = 2;
    }
    """

    @proto_schema(schema=inline_idl, message_name="SampleMessage")
    class SampleCommand:
        id: str
        name: str

    assert len(registry.entries) == 1
    assert registry.entries[0].message_name == "SampleMessage"

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "gen"
        stubs = ProtoCompiler.compile_metadata(
            entries=registry.entries,
            output_dir=out_dir,
            generate_pyi=True,
        )

        assert len(stubs) >= 2  # _pb2.py, _pb2.pyi
        assert (out_dir / "__init__.py").exists()


def test_proto_file_decorator_registers_and_compiles():
    """Verify file-based schema decoration and in-process compilation."""
    registry = get_proto_registry()
    registry.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        proto_file_path = Path(tmpdir) / "service.proto"
        proto_file_path.write_text(
            """
            syntax = "proto3";
            package test.v1;

            message TestRequest {
                string query = 1;
            }
            """,
            encoding="utf-8",
        )

        @proto_file(file_path=proto_file_path, message_name="TestRequest")
        class QueryItem:
            query: str

        assert len(registry.entries) == 1
        assert registry.entries[0].file_path == proto_file_path

        out_dir = Path(tmpdir) / "gen"
        stubs = ProtoCompiler.compile_files(
            proto_files=[proto_file_path],
            output_dir=out_dir,
            generate_pyi=True,
        )

        assert any("service_pb2.py" in str(s) for s in stubs)
        assert (out_dir / "__init__.py").exists()

"""In-process Protobuf compilation engine powered by grpc_tools.protoc.

Notes/Architectural Intent:
    Invokes Google's embedded protoc compiler directly within the running Python
    process without external subprocess shells or system dependencies.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_grpc.domain.exceptions import ProtoCompilationError
from hexastack_grpc.domain.models import ProtoSchemaMetadata


class ProtoCompiler:
    """In-process compiler translating .proto files and inline schemas into Python stubs."""

    @staticmethod
    def _require_grpc_tools() -> None:
        try:
            import grpc_tools.protoc  # noqa: F401
        except ImportError as e:
            raise MissingDependencyError(
                "grpcio-tools is required to compile protobuf schemas. "
                "Install with 'pip install hexastack-grpc[tools]' or 'pip install grpcio-tools'."
            ) from e

    @classmethod
    def compile_files(
        cls,
        proto_files: Sequence[Path | str],
        include_dirs: Sequence[Path | str] | None = None,
        output_dir: Path | str = "src/generated/grpc",
        generate_pyi: bool = True,
    ) -> list[Path]:
        """Compile existing .proto files using grpc_tools.protoc.main in-process.

        Args:
            proto_files: Sequence of .proto file paths to compile.
            include_dirs: Optional directories to include in proto lookup (-I).
            output_dir: Target output directory for generated Python modules.
            generate_pyi: Whether to emit typing stub (.pyi) files.

        Returns:
            List of generated output file paths.

        Raises:
            ProtoCompilationError: If protoc compilation returns a non-zero exit status.
            MissingDependencyError: If grpc_tools is not installed.
        """
        cls._require_grpc_tools()
        from grpc_tools import protoc

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        includes = [Path(d).resolve() for d in (include_dirs or [])]
        # Always include the parent directory of each proto file
        for pf in proto_files:
            p_parent = Path(pf).resolve().parent
            if p_parent not in includes:
                includes.append(p_parent)

        args = ["protoc"]
        for inc in includes:
            args.append(f"-I{inc}")

        args.append(f"--python_out={out_path}")
        args.append(f"--grpc_python_out={out_path}")
        if generate_pyi:
            args.append(f"--pyi_out={out_path}")

        args.extend(str(Path(pf).resolve()) for pf in proto_files)

        exit_code = protoc.main(args)
        if exit_code != 0:
            raise ProtoCompilationError(
                f"Protobuf compilation failed with exit code {exit_code}."
            )

        # Ensure __init__.py exists in output directory
        init_file = out_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Generated gRPC stubs and protobuf messages."""\n')

        return sorted(out_path.glob("*_pb2*"))

    @classmethod
    def compile_metadata(
        cls,
        entries: Sequence[ProtoSchemaMetadata],
        output_dir: Path | str = "src/generated/grpc",
        generate_pyi: bool = True,
    ) -> list[Path]:
        """Compile a collection of ProtoSchemaMetadata (both inline schemas and file paths).

        Args:
            entries: Sequence of ProtoSchemaMetadata objects from ProtoRegistry.
            output_dir: Destination folder for compiled stubs.
            generate_pyi: Whether to emit .pyi typing stubs.

        Returns:
            List of generated output file paths.
        """
        file_targets: list[Path] = []
        inline_schemas: list[ProtoSchemaMetadata] = []

        for e in entries:
            if e.file_path:
                file_targets.append(e.file_path)
            elif e.schema:
                inline_schemas.append(e)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Write inline schemas to temporary files
            for idx, item in enumerate(inline_schemas):
                pkg_name = f"schema_{idx}"
                tmp_proto = tmp_path / f"{pkg_name}.proto"
                tmp_proto.write_text(item.schema or "", encoding="utf-8")
                file_targets.append(tmp_proto)

            include_dirs = [tmp_path]
            return cls.compile_files(
                proto_files=file_targets,
                include_dirs=include_dirs,
                output_dir=output_dir,
                generate_pyi=generate_pyi,
            )


__all__ = [
    "ProtoCompiler",
]

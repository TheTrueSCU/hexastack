"""CLI gRPC devtools commands."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import typer

__all__ = [
    "add_grpc_commands",
]


def add_grpc_commands(app: typer.Typer) -> None:
    """Register 'grpc' subcommand group for RPC services."""
    if importlib.util.find_spec("hexastack_grpc") is None:
        return

    grpc_app = typer.Typer(
        name="grpc",
        help="High-performance gRPC server management.",
        no_args_is_help=True,
    )
    app.add_typer(grpc_app, name="grpc")

    @grpc_app.command(name="serve", help="Launch the gRPC server daemon.")
    def grpc_serve(
        host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host."),
        port: int = typer.Option(50051, "--port", "-p", help="Bind port."),
    ) -> None:
        _exec_grpc_serve(host, port)

    @grpc_app.command(
        name="compile",
        help="Compile discovered @proto_schema inline strings and @proto_file definitions into Python stubs.",
    )
    def grpc_compile(
        out_dir: str = typer.Option(
            "src/generated/grpc",
            "--out-dir",
            "-o",
            help="Target output directory for generated protobuf stubs.",
        ),
        proto_file: list[str] | None = typer.Option(
            None,
            "--file",
            "-f",
            help="Optional explicit .proto file path(s) to compile.",
        ),
    ) -> None:
        _exec_grpc_compile(out_dir, proto_file)

    @grpc_app.command(
        name="list",
        help="Inspect and list registered gRPC services, RPC methods, and protobuf schemas.",
    )
    def grpc_list() -> None:
        _exec_grpc_list()

    @grpc_app.command(
        name="lint",
        help="Lint Protobuf schemas using Buf (requires buf CLI in PATH).",
    )
    def grpc_buf_lint(
        path: str = typer.Option(
            ".", "--path", "-p", help="Path to proto files or buf.yaml workspace."
        ),
    ) -> None:
        import shutil
        import subprocess

        buf_bin = shutil.which("buf")
        if not buf_bin:
            typer.echo(
                "❌ 'buf' CLI not found in PATH. Install from https://buf.build/docs/installation"
            )
            raise typer.Exit(code=1)

        typer.echo(f"🔍 Running 'buf lint' against {path}...")
        res = subprocess.run([buf_bin, "lint", path], check=False)
        if res.returncode == 0:
            typer.echo("✅ All Protobuf schemas passed Buf linting.")
        else:
            raise typer.Exit(code=res.returncode)

    @grpc_app.command(
        name="breaking",
        help="Detect backwards-incompatible Protobuf breaking changes against a git reference.",
    )
    def grpc_buf_breaking(
        against: str = typer.Option(
            ".git#branch=main",
            "--against",
            "-a",
            help="Git reference or branch to compare against (e.g. .git#branch=main).",
        ),
        path: str = typer.Option(
            ".", "--path", "-p", help="Path to current proto workspace."
        ),
    ) -> None:
        import shutil
        import subprocess

        buf_bin = shutil.which("buf")
        if not buf_bin:
            typer.echo(
                "❌ 'buf' CLI not found in PATH. Install from https://buf.build/docs/installation"
            )
            raise typer.Exit(code=1)

        typer.echo(f"🛡️ Checking Protobuf breaking changes against {against}...")
        res = subprocess.run(
            [buf_bin, "breaking", path, "--against", against], check=False
        )
        if res.returncode == 0:
            typer.echo(
                "✅ No breaking changes detected! Schemas are backwards-compatible."
            )
        else:
            raise typer.Exit(code=res.returncode)


def _exec_grpc_serve(host: str, port: int) -> None:
    import grpc

    import hexastack.application.diagnostics
    from hexastack_core.infra.bootstrap import bootstrap
    from hexastack_grpc.adapters.server import run_grpc_server

    runtime = bootstrap(packages_to_scan=[hexastack.application.diagnostics])
    server = runtime.container.resolve(grpc.Server)
    typer.echo(f"Starting gRPC server on {host}:{port}...")
    run_grpc_server(server, block=True)


def _exec_grpc_compile(out_dir: str, proto_file: list[str] | None) -> None:

    from hexastack_grpc.infra.compiler import ProtoCompiler
    from hexastack_grpc.infra.registries.proto import get_proto_registry

    registry = get_proto_registry()
    entries = registry.entries

    if proto_file:
        generated = ProtoCompiler.compile_files(
            proto_files=proto_file,
            output_dir=Path(out_dir),
        )
    elif entries:
        generated = ProtoCompiler.compile_metadata(
            entries=entries,
            output_dir=Path(out_dir),
        )
    else:
        default_proto_dir = Path("protos")
        if default_proto_dir.exists():
            found_files = list(default_proto_dir.glob("**/*.proto"))
            if found_files:
                generated = ProtoCompiler.compile_files(
                    proto_files=found_files,
                    include_dirs=[default_proto_dir],
                    output_dir=Path(out_dir),
                )
            else:
                typer.echo(
                    "⚠️  No @proto_schema annotations, @proto_file decorators, or .proto files found."
                )
                return
        else:
            typer.echo(
                "⚠️  No @proto_schema annotations, @proto_file decorators, or .proto files found."
            )
            return

    typer.echo(
        f"✨ Successfully compiled {len(generated)} protobuf stubs into '{out_dir}':"
    )
    for g in generated:
        typer.echo(f"   • {g.name}")


def _exec_grpc_list() -> None:
    from hexastack_grpc.infra.decorators import get_grpc_registry
    from hexastack_grpc.infra.registries.proto import get_proto_registry

    proto_reg = get_proto_registry()
    grpc_reg = get_grpc_registry()

    typer.echo(
        "🔍 [bold cyan]Registered gRPC Services & Protobuf Schemas[/bold cyan]\n"
    )

    if not proto_reg.entries and not grpc_reg._services:
        typer.echo("   (No gRPC services or protobuf schemas registered)")
        return

    if proto_reg.entries:
        typer.echo("📜 [bold]Protobuf Schemas & Models:[/bold]")
        for entry in proto_reg.entries:
            src_type = (
                "inline @proto_schema" if entry.schema else f"file: {entry.file_path}"
            )
            rpc_info = (
                f" -> {entry.service_name}/{entry.rpc_name}"
                if entry.service_name
                else ""
            )
            typer.echo(
                f"   • [green]{entry.message_name}[/green] ({src_type}){rpc_info}"
            )
        typer.echo("")

    if grpc_reg._services:
        typer.echo("⚡ [bold]gRPC Servicers:[/bold]")
        for svc in grpc_reg._services:
            servicer_name = getattr(svc.servicer, "__name__", str(svc.servicer))
            names = ", ".join(svc.service_names) if svc.service_names else "default"
            typer.echo(f"   • [yellow]{servicer_name}[/yellow] (Services: {names})")

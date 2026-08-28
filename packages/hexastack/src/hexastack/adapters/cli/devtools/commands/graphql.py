"""CLI command definitions for demo showcase and diagnostics.

Notes/Architectural Intent:
    Provides subcommands for inspecting registries, running diagnostic queries,
    and launching interactive developer servers.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import typer

__all__ = [
    "add_graphql_commands",
]


def add_graphql_commands(app: typer.Typer) -> None:
    """Register 'graphql' subcommand group for schema introspection."""
    if importlib.util.find_spec("hexastack_graphql") is None:
        return

    graphql_app = typer.Typer(
        name="graphql",
        help="GraphQL schema SDL and introspection (requires hexastack[graphql]).",
        no_args_is_help=True,
    )
    app.add_typer(graphql_app, name="graphql")

    @graphql_app.command(
        name="schema",
        help="Export or print the complete GraphQL Schema Definition (SDL).",
    )
    def graphql_schema() -> None:
        import strawberry

        import hexastack.application.diagnostics
        from hexastack_core.infra.bootstrap import bootstrap

        runtime = bootstrap(packages_to_scan=[hexastack.application.diagnostics])
        try:
            schema = runtime.container.resolve(strawberry.Schema)
            typer.echo(schema.as_str())
        except Exception:
            typer.echo(
                "⚠️  No Strawberry GraphQL Schema currently registered in container."
            )


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

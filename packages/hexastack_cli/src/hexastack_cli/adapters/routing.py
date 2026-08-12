import asyncio
import inspect
import json
import os
import re
import sys
from collections.abc import Callable, Sequence
from typing import Any, cast

import typer
from hexastack_core.domain import Command, Generic, Query
from hexastack_core.utils.context import (
    UserContext,
    set_correlation_id,
    set_user_context,
)
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from rich.console import Console

from hexastack_cli.adapters.presenter import RichTerminalPresenter


def _to_kebab_case(name: str) -> str:
    """Convert PascalCase class name to kebab-case CLI command name."""
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1-\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
    return (
        s.lower()
        .removesuffix("-command")
        .removesuffix("-query")
        .removesuffix("-cmd")
        .removesuffix("-qry")
    )


def _build_dynamic_cli_runner(
    model_cls: type[Command] | type[Query],
    pipeline: ExecutionPipeline,
    positional: Sequence[str] | None = None,
    output_format: str | None = None,
    presenter: RichTerminalPresenter | None = None,
    console: Console | None = None,
) -> Callable[..., None]:
    """Dynamically construct a typed function whose signature matches model_cls fields and CLI flags for Typer."""
    active_presenter = presenter or RichTerminalPresenter(console=console)
    active_console = console or Console()
    pos_set = set(positional or ())

    def runner(**kwargs: Any) -> None:
        # Extract CLI control flags
        requested_output = kwargs.pop("__output_format__", output_format)
        quiet_mode = kwargs.pop("__quiet__", False)
        debug_mode = kwargs.pop("__debug__", False)
        correlation_id = kwargs.pop("__correlation_id__", None)
        user_id = kwargs.pop("__user_id__", None)
        tenant_id = kwargs.pop("__tenant_id__", None)
        input_payload = kwargs.pop("__input__", None)

        if correlation_id:
            set_correlation_id(correlation_id)

        if user_id or tenant_id:
            set_user_context(
                UserContext(user_id=user_id or "cli-user", tenant_id=tenant_id)
            )

        try:
            field_data: dict[str, Any] = {}

            # Read raw JSON/file/stdin payload if --input was specified
            if input_payload:
                if input_payload == "-":
                    raw_json = sys.stdin.read()
                elif os.path.isfile(input_payload):
                    with open(input_payload, encoding="utf-8") as f:
                        raw_json = f.read()
                else:
                    raw_json = input_payload
                payload_dict = json.loads(raw_json)
                if isinstance(payload_dict, dict):
                    field_data.update(payload_dict)

            # Explicit CLI flags override payload defaults
            cli_flags = {k: v for k, v in kwargs.items() if v is not None}
            field_data.update(cli_flags)

            instance = model_cls(**field_data)
            result = pipeline.execute(
                instance, output_format=requested_output
            )

            # Resolve asynchronous handler coroutine if returned
            if inspect.iscoroutine(result):
                result = asyncio.run(result)

            if result is not None:
                if isinstance(result, Generic):
                    active_presenter.present(
                        result, format_mode=requested_output
                    )
                elif not quiet_mode or requested_output:
                    if requested_output == "json":
                        sys.stdout.write(
                            json.dumps(result, indent=2, default=str) + "\n"
                        )
                        sys.stdout.flush()
                    elif requested_output == "plain":
                        sys.stdout.write(f"{result}\n")
                        sys.stdout.flush()
                    else:
                        active_console.print(
                            f"[bold green]{result}[/bold green]"
                        )
        except Exception as exc:
            if debug_mode:
                active_presenter.print_exception()
            else:
                active_presenter.print_error(str(exc))
            raise typer.Exit(code=1) from exc

    # Separate parameters into positional arguments and options
    pos_params: list[inspect.Parameter] = []
    opt_params: list[inspect.Parameter] = []

    has_output_field = "output" in model_cls.model_fields
    has_quiet_field = "quiet" in model_cls.model_fields
    has_debug_field = "debug" in model_cls.model_fields
    has_cid_field = "correlation_id" in model_cls.model_fields
    has_user_id_field = "user_id" in model_cls.model_fields
    has_tenant_id_field = "tenant_id" in model_cls.model_fields
    has_input_field = "input" in model_cls.model_fields

    for field_name, field_info in model_cls.model_fields.items():
        annotation = field_info.annotation or str
        is_pos = field_name in pos_set

        if is_pos:
            default = typer.Argument(None, help=field_info.description)
            param = inspect.Parameter(
                name=field_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=annotation,
            )
            pos_params.append(param)
        else:
            default = typer.Option(None, help=field_info.description)
            param = inspect.Parameter(
                name=field_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=annotation,
            )
            opt_params.append(param)

    # Universal CLI control options
    control_params: list[inspect.Parameter] = []
    if not has_output_field:
        control_params.append(
            inspect.Parameter(
                name="__output_format__",
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=typer.Option(
                    output_format or "table",
                    "--output",
                    "-o",
                    help="Output format: table, json, or plain (CI/pipe friendly).",
                ),
                annotation=str,
            )
        )

    if not has_input_field:
        control_params.append(
            inspect.Parameter(
                name="__input__",
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=typer.Option(
                    None,
                    "--input",
                    "-i",
                    help="Input JSON payload string, file path, or '-' for stdin.",
                ),
                annotation=str | None,
            )
        )

    if not has_quiet_field:
        control_params.append(
            inspect.Parameter(
                name="__quiet__",
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=typer.Option(
                    False,
                    "--quiet",
                    "-q",
                    help="Quiet mode: suppress decorative terminal output.",
                ),
                annotation=bool,
            )
        )

    if not has_debug_field:
        control_params.append(
            inspect.Parameter(
                name="__debug__",
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=typer.Option(
                    False,
                    "--debug",
                    help="Enable debug mode and render formatted error tracebacks.",
                ),
                annotation=bool,
            )
        )

    if not has_cid_field:
        control_params.append(
            inspect.Parameter(
                name="__correlation_id__",
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=typer.Option(
                    None,
                    "--correlation-id",
                    help="Explicit correlation ID for request tracing.",
                ),
                annotation=str | None,
            )
        )

    if not has_user_id_field:
        control_params.append(
            inspect.Parameter(
                name="__user_id__",
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=typer.Option(
                    None,
                    "--user-id",
                    help="Authenticated user context identifier.",
                ),
                annotation=str | None,
            )
        )

    if not has_tenant_id_field:
        control_params.append(
            inspect.Parameter(
                name="__tenant_id__",
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=typer.Option(
                    None,
                    "--tenant-id",
                    help="Tenant isolation identifier for multi-tenancy.",
                ),
                annotation=str | None,
            )
        )

    all_params = pos_params + opt_params + control_params
    sig = inspect.Signature(parameters=all_params)
    cast(Any, runner).__signature__ = sig
    return runner


def register_cqrs_command(
    app: typer.Typer,
    command_cls: type[Command],
    pipeline: ExecutionPipeline,
    name: str | None = None,
    positional: Sequence[str] | None = None,
    help_text: str | None = None,
    output_format: str | None = None,
    presenter: RichTerminalPresenter | None = None,
    console: Console | None = None,
) -> None:
    """Register a CQRS Command model as a typed CLI sub-command on a Typer application.

    Notes/Architectural Intent:
        Reflects over Pydantic Command model fields to build dynamic CLI options and arguments,
        injecting CI-friendly flags (--output, --input, --quiet, --debug, --correlation-id, --user-id, --tenant-id).

    Args:
        app: Target Typer application instance.
        command_cls: Pydantic Command model class.
        pipeline: ExecutionPipeline for dispatching commands.
        name: Optional custom command name (defaults to kebab-case class name).
        positional: Optional sequence of field names to map as positional CLI arguments.
        help_text: Optional command description help string.
        output_format: Optional presenter format.
        presenter: Optional RichTerminalPresenter instance.
        console: Optional rich Console instance.

    Returns:
        None.

    Raises:
        None.
    """
    cmd_name = name or _to_kebab_case(command_cls.__name__)
    doc = help_text or (command_cls.__doc__ or f"Execute {command_cls.__name__}")
    runner = _build_dynamic_cli_runner(
        command_cls,
        pipeline,
        positional=positional,
        output_format=output_format,
        presenter=presenter,
        console=console,
    )
    app.command(name=cmd_name, help=doc)(runner)


def register_cqrs_query(
    app: typer.Typer,
    query_cls: type[Query],
    pipeline: ExecutionPipeline,
    name: str | None = None,
    positional: Sequence[str] | None = None,
    help_text: str | None = None,
    output_format: str | None = None,
    presenter: RichTerminalPresenter | None = None,
    console: Console | None = None,
) -> None:
    """Register a CQRS Query model as a typed CLI sub-command on a Typer application.

    Notes/Architectural Intent:
        Reflects over Pydantic Query model fields to build dynamic CLI options and arguments,
        injecting CI-friendly flags (--output, --input, --quiet, --debug, --correlation-id, --user-id, --tenant-id).

    Args:
        app: Target Typer application instance.
        query_cls: Pydantic Query model class.
        pipeline: ExecutionPipeline for dispatching queries.
        name: Optional custom query command name (defaults to kebab-case class name).
        positional: Optional sequence of field names to map as positional CLI arguments.
        help_text: Optional query description help string.
        output_format: Optional presenter format.
        presenter: Optional RichTerminalPresenter instance.
        console: Optional rich Console instance.

    Returns:
        None.

    Raises:
        None.
    """
    qry_name = name or _to_kebab_case(query_cls.__name__)
    doc = help_text or (query_cls.__doc__ or f"Execute {query_cls.__name__}")
    runner = _build_dynamic_cli_runner(
        query_cls,
        pipeline,
        positional=positional,
        output_format=output_format,
        presenter=presenter,
        console=console,
    )
    app.command(name=qry_name, help=doc)(runner)


__all__ = [
    "register_cqrs_command",
    "register_cqrs_query",
]

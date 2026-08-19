import inspect
import re
from collections.abc import Sequence
from types import ModuleType
from typing import Any

import typer
from rich.console import Console

from hexastack_cli.adapters.routing import (
    _to_kebab_case,
    register_cqrs_command,
    register_cqrs_query,
)
from hexastack_cli.infra.decorators import (
    _CLI_GROUP_ATTR,
    _CLI_METADATA_ATTR,
    CliMetadata,
    GroupMetadata,
)
from hexastack_core.domain import Command, Query
from hexastack_core.infra.autodiscovery import (
    DiscoveryVisitor,
    scan_modules,
)
from hexastack_cqrs.infra.pipeline import ExecutionPipeline

__all__ = [
    "autodiscover_cli_commands",
    "create_cli_visitor",
]


class _SubgroupManager:
    """Manages creation and nested mounting of Typer subgroups."""

    def __init__(self, root_app: typer.Typer) -> None:
        self.root_app = root_app
        self.subgroups: dict[tuple[str, ...], typer.Typer] = {}
        self.group_docs: dict[tuple[str, ...], str] = {}

    def get_or_create(self, group_parts: list[str]) -> typer.Typer:
        """Get or create nested subgroup Typer application."""
        if not group_parts:
            return self.root_app

        current_app = self.root_app
        current_path: list[str] = []
        for part in group_parts:
            current_path.append(part)
            key = tuple(current_path)
            if key not in self.subgroups:
                help_text = self.group_docs.get(
                    key, f"{part.title()} management commands"
                )
                sub_app = typer.Typer(
                    name=part,
                    help=help_text,
                    no_args_is_help=True,
                )

                @sub_app.callback()
                def _sub_cb() -> None:
                    pass

                current_app.add_typer(sub_app, name=part)
                self.subgroups[key] = sub_app
            current_app = self.subgroups[key]
        return current_app

    def register_group_metadata(self, obj: type[Any]) -> None:
        """Extract and cache group documentation from @cli_group."""
        grp_meta: GroupMetadata | None = getattr(obj, _CLI_GROUP_ATTR, None)
        if grp_meta is not None:
            parts = _normalize_group_path(grp_meta.name)
            if parts and grp_meta.help:
                self.group_docs[tuple(parts)] = grp_meta.help


def _normalize_group_path(group: str | Sequence[str] | None) -> list[str]:
    """Normalize a string or sequence into a list of subcommand group tokens."""
    if not group:
        return []
    if isinstance(group, str):
        return [part.strip() for part in re.split(r"[./\s]+", group) if part.strip()]
    return [str(part).strip() for part in group if str(part).strip()]


def _register_model_target(
    target_app: typer.Typer,
    obj: type[Any],
    meta: CliMetadata,
    cmd_name: str,
    help_text: str | None,
    pipeline: ExecutionPipeline,
    console: Console | None,
) -> None:
    """Register command or query class on the target Typer app."""
    if meta.kind == "command" and issubclass(obj, Command):
        register_cqrs_command(
            app=target_app,
            command_cls=obj,
            pipeline=pipeline,
            name=cmd_name,
            positional=meta.positional,
            help_text=help_text,
            output_format=meta.output_format,
            console=console,
            feature_flag=meta.feature_flag,
        )
    elif meta.kind == "query" and issubclass(obj, Query):
        register_cqrs_query(
            app=target_app,
            query_cls=obj,
            pipeline=pipeline,
            name=cmd_name,
            positional=meta.positional,
            help_text=help_text,
            output_format=meta.output_format,
            console=console,
            feature_flag=meta.feature_flag,
        )


def _resolve_targets(
    meta: CliMetadata, default_name: str
) -> list[tuple[list[str], str, str | None]]:
    """Resolve all (group_parts, cmd_name, help) targets including aliases."""
    primary_group = _normalize_group_path(meta.group)
    primary_name = meta.name or default_name
    targets: list[tuple[list[str], str, str | None]] = [
        (primary_group, primary_name, meta.help)
    ]

    for alias in meta.aliases:
        if alias.startswith("/"):
            targets.append(([], alias.lstrip("/"), meta.help))
        elif any(sep in alias for sep in (".", "/", " ")):
            parts = _normalize_group_path(alias)
            targets.append((parts[:-1], parts[-1], meta.help))
        else:
            targets.append((primary_group, alias, meta.help))

    return targets


def autodiscover_cli_commands(
    app: typer.Typer,
    packages_or_modules: Sequence[str | ModuleType],
    pipeline: ExecutionPipeline,
    console: Console | None = None,
) -> None:
    """Scan packages and register discovered CLI commands into a Typer application.

    Args:
        app: Target Typer application instance.
        packages_or_modules: Sequence of package names or module objects to inspect.
        pipeline: Target ExecutionPipeline instance.
        console: Optional rich Console instance.

    Returns:
        None.

    Raises:
        None.
    """
    visitor = create_cli_visitor(app=app, pipeline=pipeline, console=console)
    scan_modules(packages_or_modules, [visitor])


def create_cli_visitor(
    app: typer.Typer,
    pipeline: ExecutionPipeline,
    console: Console | None = None,
) -> DiscoveryVisitor:
    """Create a DiscoveryVisitor callback for single-pass CLI command and alias registration.

    Notes/Architectural Intent:
        Inspects discovered classes for @cli_command, @cli_query, and @cli_group metadata,
        dynamically building nested Typer subcommand trees and mounting intra-group
        and cross-group command aliases.

    Args:
        app: Target Typer root application instance.
        pipeline: ExecutionPipeline instance for command and query dispatching.
        console: Optional rich Console instance.

    Returns:
        DiscoveryVisitor callable accepting (member, module).

    Raises:
        None.
    """
    manager = _SubgroupManager(root_app=app)

    def visitor(obj: Any, module: ModuleType) -> None:
        if not inspect.isclass(obj):
            return

        manager.register_group_metadata(obj)

        meta: CliMetadata | None = getattr(obj, _CLI_METADATA_ATTR, None)
        if meta is None:
            return

        default_name = _to_kebab_case(obj.__name__)
        targets = _resolve_targets(meta, default_name)

        for group_parts, cmd_name, help_text in targets:
            target_app = manager.get_or_create(group_parts)
            _register_model_target(
                target_app, obj, meta, cmd_name, help_text, pipeline, console
            )

    return visitor

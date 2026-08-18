from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from hexastack_core.domain import Command, Query

_CLI_METADATA_ATTR = "__hexastack_cli__"
_CLI_GROUP_ATTR = "__hexastack_cli_group__"


@dataclass(frozen=True)
class CliMetadata:
    """Metadata describing a CLI command binding for a Command or Query.

    Notes/Architectural Intent:
        Carries CLI command naming, positional parameter mappings, aliases, help descriptions,
        and optional sub-command group identifications for automated terminal routing.
    """

    kind: Literal["command", "query"]
    name: str | None = None
    positional: tuple[str, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)
    help: str | None = None
    output_format: str | None = None
    group: str | Sequence[str] | None = None


@dataclass(frozen=True)
class GroupMetadata:
    """Metadata configuring a custom CLI subcommand group title and description.

    Notes/Architectural Intent:
        Allows domain modules or namespaces to define rich descriptions for CLI command groups.
    """

    name: str
    help: str | None = None


__all__ = [
    "CliMetadata",
    "GroupMetadata",
    "cli_command",
    "cli_group",
    "cli_query",
]


def _normalize_tokens(tokens: Sequence[str] | str | None) -> tuple[str, ...]:
    """Normalize string or sequence of token strings into an immutable tuple."""
    if not tokens:
        return ()
    if isinstance(tokens, str):
        return (tokens.strip(),)
    return tuple(str(t).strip() for t in tokens if str(t).strip())


def cli_command[TCommand: Command](
    name: str | None = None,
    *,
    positional: Sequence[str] | str | None = None,
    aliases: Sequence[str] | str | None = None,
    help: str | None = None,
    output_format: str | None = None,
    group: str | Sequence[str] | None = None,
) -> Callable[[type[TCommand]], type[TCommand]]:
    """Decorator marking a Command class for automatic CLI command exposure.

    Args:
        name: Optional custom CLI command name (defaults to kebab-cased class name).
        positional: Optional field name or list of field names to treat as positional CLI arguments.
        aliases: Optional alias or list of aliases (can be intra-group like 'create' or cross-group like 'account.new').
        help: Optional help text for the command.
        output_format: Optional presenter output format.
        group: Optional sub-command group name or nested group path (e.g. 'user', 'user.profile').

    Returns:
        Decorated Command class with attached CLI metadata.

    Raises:
        None.
    """

    def decorator(cls: type[TCommand]) -> type[TCommand]:
        meta = CliMetadata(
            kind="command",
            name=name,
            positional=_normalize_tokens(positional),
            aliases=_normalize_tokens(aliases),
            help=help,
            output_format=output_format,
            group=group,
        )
        setattr(cls, _CLI_METADATA_ATTR, meta)
        return cls

    return decorator


def cli_group(
    name: str,
    *,
    help: str | None = None,
) -> Callable[[type], type]:
    """Decorator configuring custom metadata or documentation for a CLI group.

    Args:
        name: The group name path (e.g. 'user', 'user.profile').
        help: Help description displayed for the group in terminal --help.

    Returns:
        Decorator function attaching GroupMetadata.

    Raises:
        None.
    """

    def decorator(cls: type) -> type:
        meta = GroupMetadata(name=name, help=help)
        setattr(cls, _CLI_GROUP_ATTR, meta)
        return cls

    return decorator


def cli_query[TQuery: Query](
    name: str | None = None,
    *,
    positional: Sequence[str] | str | None = None,
    aliases: Sequence[str] | str | None = None,
    help: str | None = None,
    output_format: str | None = None,
    group: str | Sequence[str] | None = None,
) -> Callable[[type[TQuery]], type[TQuery]]:
    """Decorator marking a Query class for automatic CLI command exposure.

    Args:
        name: Optional custom CLI command name (defaults to kebab-cased class name).
        positional: Optional field name or list of field names to treat as positional CLI arguments.
        aliases: Optional alias or list of aliases (can be intra-group like 'find' or cross-group like 'search.user').
        help: Optional help text for the command.
        output_format: Optional presenter output format.
        group: Optional sub-command group name or nested group path (e.g. 'user', 'user.profile').

    Returns:
        Decorated Query class with attached CLI metadata.

    Raises:
        None.
    """

    def decorator(cls: type[TQuery]) -> type[TQuery]:
        meta = CliMetadata(
            kind="query",
            name=name,
            positional=_normalize_tokens(positional),
            aliases=_normalize_tokens(aliases),
            help=help,
            output_format=output_format,
            group=group,
        )
        setattr(cls, _CLI_METADATA_ATTR, meta)
        return cls

    return decorator

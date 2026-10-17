import difflib
import os
import re
import sys
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

import typer
import typer.core

if TYPE_CHECKING:
    from typer._click import exceptions as click_exceptions
    from typer._click.parser import _OptionParser, _ParsingState
else:
    try:
        import typer._click.exceptions as click_exceptions
        from typer._click.parser import _OptionParser, _ParsingState
    except ImportError:
        import click.exceptions as click_exceptions
        from click.parser import _OptionParser, _ParsingState

__all__ = [
    "find_closest_match",
    "is_interactive",
    "SuggestCommand",
    "SuggestGroup",
    "SuggestOptionParser",
    "TyperSuggest",
]

_NUMERIC_ARG_RE = re.compile(r"^-[0-9]+(\.[0-9]+)?$")


def is_interactive(ctx: Any | None = None) -> bool:
    """Determine whether the current execution context is interactive.

    Notes/Architectural Intent:
        Evaluates environment flags (e.g. HEXASTACK_CLI_INTERACTIVE), context metadata,
        and TTY status to strictly prevent hanging prompts in non-interactive CI pipelines.

    Args:
        ctx: Optional Click or Typer execution context.

    Returns:
        True if running in an interactive TTY session or forced interactively, False otherwise.

    Raises:
        None.
    """
    if os.environ.get("HEXASTACK_CLI_INTERACTIVE", "").lower() in ("1", "true", "yes"):
        return True
    if ctx is not None and getattr(ctx, "meta", {}).get("force_interactive"):
        return True
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def find_closest_match(
    token: str,
    candidates: Sequence[str],
    cutoff: float = 0.6,
) -> str | None:
    """Find the closest matching string candidate using difflib sequence matching.

    Notes/Architectural Intent:
        Performs direct string distance matching, followed by leading-dash stripped
        normalization to forgivingly reconcile CLI flag and subcommand typos.

    Args:
        token: Target string token to match.
        candidates: Sequence of valid candidate strings.
        cutoff: Minimum similarity ratio required for a match (defaults to 0.6).

    Returns:
        Closest matching candidate string, or None if no match meets the cutoff.

    Raises:
        None.
    """
    matches = difflib.get_close_matches(token, candidates, n=1, cutoff=cutoff)
    if matches:
        return matches[0]

    clean_token = token.lstrip("-")
    norm_candidates = {c.lstrip("-"): c for c in candidates}
    norm_matches = difflib.get_close_matches(
        clean_token, list(norm_candidates.keys()), n=1, cutoff=cutoff
    )
    if norm_matches:
        return norm_candidates[norm_matches[0]]

    return None


def _substitute_flag_token(
    args: Sequence[str],
    target_opt: str,
    replacement_opt: str,
) -> list[str]:
    """Substitute an unrecognized option flag token with its corrected candidate.

    Notes/Architectural Intent:
        Preserves parameter assignments using '=' syntax (e.g. '--prt=8080' ->
        '--port=8080') while substituting exact option tokens.

    Args:
        args: Sequence of CLI argument tokens.
        target_opt: Unrecognized option token to replace.
        replacement_opt: Corrected replacement option token.

    Returns:
        New list of argument tokens with the target option replaced.

    Raises:
        None.
    """
    updated: list[str] = []
    prefix = f"{target_opt}="
    for token in args:
        if token == target_opt:
            updated.append(replacement_opt)
        elif token.startswith(prefix):
            val = token[len(prefix) :]
            updated.append(f"{replacement_opt}={val}")
        else:
            updated.append(token)
    return updated


def _extract_option_candidates(params: Sequence[Any]) -> list[str]:
    """Extract all available option flags from a collection of command parameters.

    Notes/Architectural Intent:
        Aggregates both primary option names and secondary negation flags
        (e.g. '--verbose' and '--no-verbose') across all command parameters.

    Args:
        params: Sequence of Click/Typer Parameter instances.

    Returns:
        List of all registered option flag strings.

    Raises:
        None.
    """
    candidates: list[str] = []
    for param in params:
        opts = getattr(param, "opts", [])
        sec_opts = getattr(param, "secondary_opts", [])
        candidates.extend(opts)
        candidates.extend(sec_opts)
    return candidates


class SuggestOptionParser(_OptionParser):
    """Custom Click option parser providing immunity for negative numbers and '--' delimiter.

    Notes/Architectural Intent:
        Intercepts option token evaluation to prevent negative numbers (e.g. -42, -0.5)
        from being erroneously parsed as unrecognized short options, preserving
        their positional argument semantics. Also ensures bare '--' strictly halts
        option parsing.
    """

    def _process_args_for_options(self, state: _ParsingState) -> None:
        while state.rargs:
            arg = state.rargs.pop(0)
            arglen = len(arg)
            if arg == "--":
                return
            if _NUMERIC_ARG_RE.match(arg):
                if self.allow_interspersed_args:
                    state.largs.append(arg)
                else:
                    state.rargs.insert(0, arg)
                    return
            elif arg[:1] in self._opt_prefixes and arglen > 1:
                self._process_opts(arg, state)
            elif self.allow_interspersed_args:
                state.largs.append(arg)
            else:
                state.rargs.insert(0, arg)
                return


def _parse_args_with_suggestions(
    command: Any,
    ctx: Any,
    args: list[str],
    super_parse: Callable[[Any, list[str]], list[str]],
) -> list[str]:
    """Parse CLI arguments intercepting unrecognized option errors to offer suggestions.

    Notes/Architectural Intent:
        Wraps command option parsing to catch NoSuchOption, query closest flag matches,
        and either prompt interactively for confirmation or emit standard Click code 2
        errors in non-interactive CI contexts. Preserves args copy against Click in-place mutation.

    Args:
        command: Command or Group instance providing parameters.
        ctx: Click/Typer context.
        args: List of argument strings.
        super_parse: Bound parse_args method from superclass.

    Returns:
        Remaining arguments after option parsing.

    Raises:
        UsageError: When an option typo is encountered in non-interactive mode.
        Abort: When interactive prompt is declined.
    """
    current_args = list(args)
    while True:
        args_copy = list(current_args)
        try:
            return super_parse(ctx, args_copy)
        except click_exceptions.NoSuchOption as exc:
            opt = getattr(exc, "option_name", None)
            if not opt:
                raise
            candidates = _extract_option_candidates(command.get_params(ctx))
            match = find_closest_match(opt, candidates)
            if not match:
                raise

            if is_interactive(ctx):
                confirmed = typer.confirm(
                    f"Unrecognized option '{opt}'. Did you mean '{match}'?",
                    default=False,
                )
                if not confirmed:
                    raise typer.Abort from exc
                current_args = _substitute_flag_token(current_args, opt, match)
                continue
            raise click_exceptions.UsageError(
                f"No such option: {opt}. Did you mean '{match}'?",
                ctx=ctx,
            ) from exc


class SuggestCommand(typer.core.TyperCommand):
    """TyperCommand with automatic typo tolerance for options and negative number immunity.

    Notes/Architectural Intent:
        Inherits from TyperCommand to provide typo correction for leaf commands
        and subcommands in TyperSuggest applications.
    """

    def make_parser(self, ctx: Any) -> SuggestOptionParser:
        """Create a SuggestOptionParser instance populated with command parameters.

        Args:
            ctx: Click/Typer context.

        Returns:
            Configured SuggestOptionParser instance.

        Raises:
            None.
        """
        parser = SuggestOptionParser(ctx)
        for param in self.get_params(ctx):
            param.add_to_parser(parser, ctx)
        return parser

    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:
        """Parse arguments with typo detection and suggestions for options.

        Args:
            ctx: Click/Typer context.
            args: Command-line arguments.

        Returns:
            Remaining positional arguments after option processing.

        Raises:
            UsageError: When an unrecognized option is encountered in non-interactive mode.
            Abort: When the user declines the correction prompt in interactive mode.
        """
        return _parse_args_with_suggestions(self, ctx, args, super().parse_args)


class SuggestGroup(typer.core.TyperGroup):
    """TyperGroup with automatic typo tolerance for subcommands, options, and negative numbers.

    Notes/Architectural Intent:
        Overrides resolve_command to intercept unknown subcommands and suggest
        closest matches, supporting both interactive confirmation prompts and
        non-interactive CI error reporting. Defaults command_class to SuggestCommand.
    """

    command_class: type[typer.core.TyperCommand] = SuggestCommand

    def make_parser(self, ctx: Any) -> SuggestOptionParser:
        """Create a SuggestOptionParser instance populated with group parameters.

        Args:
            ctx: Click/Typer context.

        Returns:
            Configured SuggestOptionParser instance.

        Raises:
            None.
        """
        parser = SuggestOptionParser(ctx)
        for param in self.get_params(ctx):
            param.add_to_parser(parser, ctx)
        return parser

    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:
        """Parse arguments with typo detection and suggestions for options.

        Args:
            ctx: Click/Typer context.
            args: Command-line arguments.

        Returns:
            Remaining positional arguments after option processing.

        Raises:
            UsageError: When an unrecognized option is encountered in non-interactive mode.
            Abort: When the user declines the correction prompt in interactive mode.
        """
        return _parse_args_with_suggestions(self, ctx, args, super().parse_args)

    def resolve_command(
        self,
        ctx: Any,
        args: list[str],
    ) -> tuple[str | None, Any | None, list[str]]:
        """Resolve subcommand with typo tolerance and interactive prompting.

        Args:
            ctx: Click/Typer execution context.
            args: CLI arguments remaining to be processed.

        Returns:
            Tuple of (command_name, command_instance, remaining_args).

        Raises:
            UsageError: When an unrecognized subcommand is encountered in non-interactive mode.
            Abort: When user declines correction prompt in interactive mode.
        """
        if not args:
            return super().resolve_command(ctx, args)
        cmd_name = str(args[0])
        if cmd_name.startswith("-"):
            return super().resolve_command(ctx, args)

        cmd = self.get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd_name, cmd, args[1:]

        candidates = list(self.commands.keys())
        match = find_closest_match(cmd_name, candidates)
        if match:
            if is_interactive(ctx):
                confirmed = typer.confirm(
                    f"Unrecognized command '{cmd_name}'. Did you mean '{match}'?",
                    default=False,
                )
                if confirmed:
                    return match, self.get_command(ctx, match), args[1:]
                raise typer.Abort
            raise click_exceptions.UsageError(
                f"No such command '{cmd_name}'. Did you mean '{match}'?",
                ctx=ctx,
            )

        return super().resolve_command(ctx, args)


class TyperSuggest(typer.Typer):
    """Drop-in replacement for typer.Typer with typo tolerance and suggestion capabilities.

    Notes/Architectural Intent:
        Defaults group class to SuggestGroup and command class to SuggestCommand,
        ensuring all subcommands and flags are protected by forgiving string-distance
        matching, numeric negative argument immunity, and non-interactive CI safety.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize TyperSuggest configuring SuggestGroup as default group class.

        Args:
            *args: Positional arguments forwarded to typer.Typer.
            **kwargs: Keyword arguments forwarded to typer.Typer.

        Returns:
            None.

        Raises:
            None.
        """
        kwargs.setdefault("cls", SuggestGroup)
        super().__init__(*args, **kwargs)

    def command(self, *args: Any, cls: Any = None, **kwargs: Any) -> Any:
        """Register a command defaulting cls to SuggestCommand.

        Args:
            *args: Positional arguments forwarded to typer.Typer.command.
            cls: Optional command class (defaults to SuggestCommand).
            **kwargs: Keyword arguments forwarded to typer.Typer.command.

        Returns:
            Decorator registering the command callback.

        Raises:
            None.
        """
        if cls is None:
            cls = SuggestCommand
        return super().command(*args, cls=cls, **kwargs)

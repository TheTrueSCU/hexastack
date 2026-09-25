"""CQRS commands for hexastack-qual.

Notes/Architectural Intent:
    Encapsulates state-changing intent: running sanity gates, auto-fixing
    statements, executing mutation tests, and syncing agent assets.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from hexastack_core.domain import Command


class RunSanityCheckCommand(Command):
    """Command to execute full or scoped sanity check quality gate.

    Notes/Architectural Intent:
        Triggers cognitive complexity, test parity, and __all__ validation.
    """

    model_config = ConfigDict(frozen=True)

    package: str | None = Field(
        default=None,
        description="Target package name or None for workspace.",
    )
    skip_tests: bool = Field(
        default=True,
        description="Whether to skip unit test suites.",
    )


class FormatStatementsCommand(Command):
    """Command to auto-format and sort __all__ export statements.

    Notes/Architectural Intent:
        Modifies target files in-place to enforce casefold ordering.
    """

    model_config = ConfigDict(frozen=True)

    package: str | None = Field(
        default=None,
        description="Target package name or None for workspace.",
    )


class RunMutationTestingCommand(Command):
    """Command to execute mutation testing across target components.

    Notes/Architectural Intent:
        Executes mutmut runner and compiles surviving mutant scorecards.
    """

    model_config = ConfigDict(frozen=True)

    package: str | None = Field(
        default=None,
        description="Target package name or None for workspace.",
    )
    reset: bool = Field(
        default=False,
        description="Whether to clear existing mutation cache before running.",
    )


class SyncAgentAssetsCommand(Command):
    """Command to re-synchronize universal AI agent rules and workflows.

    Notes/Architectural Intent:
        Materializes latest hexaqual agent assets into .agents/.
    """

    model_config = ConfigDict(frozen=True)

    dry_run: bool = Field(
        default=False,
        description="If True, verifies sync without writing files.",
    )


__all__ = [
    "FormatStatementsCommand",
    "RunMutationTestingCommand",
    "RunSanityCheckCommand",
    "SyncAgentAssetsCommand",
]

"""Unit tests for CQRS commands.

Notes/Architectural Intent:
    Validates CQRS command instantiation, parameters, and immutability.
"""

from __future__ import annotations

import pytest
from hexastack_qual.adapters.cqrs.commands import (
    FormatStatementsCommand,
    RunMutationTestingCommand,
    RunSanityCheckCommand,
    SyncAgentAssetsCommand,
)
from pydantic import ValidationError


def test_run_sanity_check_command() -> None:
    """Ensure RunSanityCheckCommand sets package and skip_tests."""
    cmd = RunSanityCheckCommand(package="core", skip_tests=True)
    assert cmd.package == "core"
    assert cmd.skip_tests is True

    attr_name = "package"
    with pytest.raises(ValidationError):
        setattr(cmd, attr_name, "other")


def test_format_statements_command() -> None:
    """Ensure FormatStatementsCommand stores target package."""
    cmd = FormatStatementsCommand(package="ai")
    assert cmd.package == "ai"


def test_run_mutation_testing_command() -> None:
    """Ensure RunMutationTestingCommand stores package and reset."""
    cmd = RunMutationTestingCommand(package="cqrs", reset=True)
    assert cmd.package == "cqrs"
    assert cmd.reset is True


def test_sync_agent_assets_command() -> None:
    """Ensure SyncAgentAssetsCommand sets dry_run."""
    cmd = SyncAgentAssetsCommand(dry_run=True)
    assert cmd.dry_run is True

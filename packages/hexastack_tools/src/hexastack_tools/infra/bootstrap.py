"""Bootstrap wiring and dependency registration for Hexastack Tools.

Notes/Architectural Intent:
    Assembles the SynchronousCommandBus, binds domain Command types to their
    respective CommandHandler implementations, and injects the ToolRunnerPort adapter.
"""

from __future__ import annotations

from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
from hexastack_cqrs.infra.registries import HandlerRegistry
from hexastack_tools.adapters.runners.subprocess_runner import (
    SubprocessToolRunnerAdapter,
)
from hexastack_tools.domain.governance import (
    AuditComplexityCommand,
    CheckAllStatementsCommand,
    CheckTestParityCommand,
    RunLinterCommand,
    RunPytestCommand,
    RunSanityCheckCommand,
    RunTypecheckCommand,
)
from hexastack_tools.infra.handlers.governance import (
    AuditComplexityHandler,
    CheckAllStatementsHandler,
    CheckTestParityHandler,
    RunLinterHandler,
    RunPytestHandler,
    RunSanityCheckHandler,
    RunTypecheckHandler,
)
from hexastack_tools.ports.governance import ToolRunnerPort

__all__ = [
    "create_governance_bus",
]


def create_governance_bus(
    runner: ToolRunnerPort | None = None,
) -> SynchronousCommandBus:
    """Construct and configure CommandBus with all governance handlers registered.

    Args:
        runner: Optional ToolRunnerPort adapter. Defaults to SubprocessToolRunnerAdapter.

    Returns:
        Configured SynchronousCommandBus instance.

    Notes/Architectural Intent:
        Creates a circular binding where the composite RunSanityCheckHandler receives
        the bus itself to dispatch individual check commands.
    """
    actual_runner = runner or SubprocessToolRunnerAdapter()
    registry = HandlerRegistry()
    bus = SynchronousCommandBus(handler_registry=registry)

    # 1. Register leaf check handlers
    linter_handler = RunLinterHandler(actual_runner)
    registry.register(RunLinterCommand, linter_handler.handle)

    typecheck_handler = RunTypecheckHandler(actual_runner)
    registry.register(RunTypecheckCommand, typecheck_handler.handle)

    complexity_handler = AuditComplexityHandler(actual_runner)
    registry.register(AuditComplexityCommand, complexity_handler.handle)

    all_statements_handler = CheckAllStatementsHandler(actual_runner)
    registry.register(CheckAllStatementsCommand, all_statements_handler.handle)

    parity_handler = CheckTestParityHandler(actual_runner)
    registry.register(CheckTestParityCommand, parity_handler.handle)

    pytest_handler = RunPytestHandler(actual_runner)
    registry.register(RunPytestCommand, pytest_handler.handle)

    # 2. Register composite sanity check handler
    sanity_handler = RunSanityCheckHandler(bus)
    registry.register(RunSanityCheckCommand, sanity_handler.handle)

    return bus

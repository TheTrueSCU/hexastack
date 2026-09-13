"""Unit tests for CommandStep and QueryStep adapters.

Notes/Architectural Intent:
    Verifies that CommandStep and QueryStep construct domain messages from StepContext,
    delegate dispatching to respective CQRS buses, and return results.
"""

from unittest.mock import MagicMock

import pytest
from hexaflow.domain.state import StepContext

from hexastack_core.domain import Command, Query
from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
from hexastack_flow.adapters.cqrs.steps import (
    CommandStep,
    QueryStep,
    as_command_step,
    as_query_step,
)


class DummyCommand(Command):
    order_id: str
    amount: float


class DummyQuery(Query[dict]):
    order_id: str


def test_command_step_execution() -> None:
    """Validate CommandStep executes factory and dispatches command to bus."""
    mock_bus = MagicMock(spec=CommandBusPort)
    mock_bus.dispatch.return_value = "cmd_success_123"

    factory = lambda ctx: DummyCommand(order_id=ctx.inputs["order_id"], amount=99.95)
    step = CommandStep(factory, mock_bus)

    ctx = StepContext(
        run_id="run-1",
        stage_name="stage-1",
        step_name="step-1",
        inputs={"order_id": "ord-888"},
    )

    res = step(ctx)
    assert res == "cmd_success_123"
    assert mock_bus.dispatch.call_count == 1

    dispatched = mock_bus.dispatch.call_args[0][0]
    assert isinstance(dispatched, DummyCommand)
    assert dispatched.order_id == "ord-888"
    assert dispatched.amount == 99.95


def test_query_step_execution() -> None:
    """Validate QueryStep executes factory and dispatches query to bus."""
    mock_bus = MagicMock(spec=QueryBusPort)
    mock_bus.dispatch.return_value = {"status": "PAID"}

    factory = lambda ctx: DummyQuery(order_id=ctx.inputs["id"])
    step = QueryStep(factory, mock_bus)

    ctx = StepContext(
        run_id="run-1",
        stage_name="stage-1",
        step_name="step-1",
        inputs={"id": "ord-777"},
    )

    res = step(ctx)
    assert res == {"status": "PAID"}
    assert mock_bus.dispatch.call_count == 1


def test_as_command_step_helper() -> None:
    """Validate as_command_step builds a StepDefinition with metadata."""
    mock_bus = MagicMock(spec=CommandBusPort)
    step_def = as_command_step(
        name="charge_card",
        command_factory=lambda ctx: DummyCommand(order_id="1", amount=10.0),
        command_bus=mock_bus,
        depends_on=("validate_cart",),
        description="Charges customer payment card",
        timeout_seconds=5.0,
    )

    name = step_def.name
    deps = step_def.depends_on
    timeout = step_def.timeout_seconds
    meta = step_def.metadata

    assert name == "charge_card"
    assert deps == ("validate_cart",)
    assert timeout == 5.0
    assert "cqrs" in meta
    assert meta["cqrs"]["step_type"] == "command"


def test_as_command_step_validation() -> None:
    """Ensure as_command_step rejects empty names."""
    mock_bus = MagicMock(spec=CommandBusPort)
    with pytest.raises(ValueError, match="Step name must not be empty"):
        as_command_step(
            "", lambda ctx: DummyCommand(order_id="1", amount=1.0), mock_bus
        )


def test_as_query_step_helper() -> None:
    """Validate as_query_step builds a StepDefinition with query metadata."""
    mock_bus = MagicMock(spec=QueryBusPort)
    step_def = as_query_step(
        name="get_order",
        query_factory=lambda ctx: DummyQuery(order_id="1"),
        query_bus=mock_bus,
        description="Fetches order status",
    )

    name = step_def.name
    meta = step_def.metadata

    assert name == "get_order"
    assert "cqrs" in meta
    assert meta["cqrs"]["step_type"] == "query"
    assert meta["cqrs"]["requires_transaction"] is False


def test_as_query_step_validation() -> None:
    """Ensure as_query_step rejects empty names."""
    mock_bus = MagicMock(spec=QueryBusPort)
    with pytest.raises(ValueError, match="Step name must not be empty"):
        as_query_step("", lambda ctx: DummyQuery(order_id="1"), mock_bus)

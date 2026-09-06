import pytest

from hexastack_ai.infra.tools import create_cqrs_agent, create_tool_for_message
from hexastack_core.domain import Command, Query
from hexastack_cqrs.infra.pipeline import ExecutionPipeline, create_pipeline
from hexastack_cqrs.infra.registries import (
    CommandRegistry,
    HandlerRegistry,
    QueryRegistry,
)


class CalculateTaxCommand(Command):
    amount: float
    tax_rate: float


class GetCustomerBalanceQuery(Query[float]):
    customer_id: str


@pytest.fixture
def pipeline() -> ExecutionPipeline:
    handler_reg = HandlerRegistry()
    command_reg = CommandRegistry()
    query_reg = QueryRegistry()

    command_reg.register(CalculateTaxCommand)
    query_reg.register(GetCustomerBalanceQuery)

    handler_reg.register(
        CalculateTaxCommand,
        lambda cmd: {"total": cmd.amount * (1 + cmd.tax_rate)},
    )
    handler_reg.register(
        GetCustomerBalanceQuery,
        lambda qry: 150.0 if qry.customer_id == "cust-1" else 0.0,
    )

    return create_pipeline(
        handler_registry=handler_reg,
        command_registry=command_reg,
        query_registry=query_reg,
    )


def test_create_cqrs_agent(pipeline: ExecutionPipeline):
    agent = create_cqrs_agent(
        pipeline=pipeline,
        messages=[CalculateTaxCommand, GetCustomerBalanceQuery],
        model="test",
        system_prompt="Test agent",
    )
    assert agent is not None
    res = agent.run_sync("Calculate tax for 100")
    assert res is not None


def test_create_cqrs_agent_defaults(pipeline: ExecutionPipeline):
    agent = create_cqrs_agent(
        pipeline=pipeline,
        messages=[CalculateTaxCommand],
    )
    assert agent is not None
    # Verify default system prompt
    assert (
        "You are an AI assistant capable of executing domain operations using the provided tools."
        in str(agent._system_prompts)
    )


@pytest.mark.anyio
async def test_create_tool_for_message(pipeline: ExecutionPipeline):
    tool_fn = create_tool_for_message(CalculateTaxCommand, pipeline)
    assert tool_fn.__name__ == "CalculateTaxCommand"
    assert tool_fn.__doc__ == "Execute the CalculateTaxCommand domain operation."
    assert "amount" in tool_fn.__annotations__
    assert tool_fn.__annotations__["amount"] is float
    assert "tax_rate" in tool_fn.__annotations__
    assert tool_fn.__annotations__["tax_rate"] is float

    res = await tool_fn(amount=100.0, tax_rate=0.2)
    assert res == {"total": 120.0}


@pytest.mark.anyio
async def test_create_tool_for_message_with_docstring(pipeline: ExecutionPipeline):
    class DocumentedCommand(Command):
        """Custom docstring for testing tool introspection."""

        value: int = 42

    tool_fn = create_tool_for_message(DocumentedCommand, pipeline)
    assert tool_fn.__name__ == "DocumentedCommand"
    assert tool_fn.__doc__ == "Custom docstring for testing tool introspection."
    assert "value" in tool_fn.__annotations__
    assert tool_fn.__annotations__["value"] is int


@pytest.mark.anyio
async def test_create_tool_for_message_unannotated_fallback(
    pipeline: ExecutionPipeline,
):
    from typing import Any

    from pydantic import Field

    class UntypedCommand(Command):
        raw_field: Any = Field(default="default_val")

    tool_fn = create_tool_for_message(UntypedCommand, pipeline)
    sig = tool_fn.__signature__
    assert "raw_field" in sig.parameters
    assert sig.parameters["raw_field"].annotation is Any
    assert sig.parameters["raw_field"].default == "default_val"


@pytest.mark.anyio
async def test_create_tool_for_message_async_handler():
    """Verify tool_executor awaits coroutine returned by pipeline.execute."""
    from unittest.mock import MagicMock

    async def _async_res():
        return {"async_total": 200.0}

    mock_pipeline = MagicMock(spec=ExecutionPipeline)
    mock_pipeline.execute = MagicMock(return_value=_async_res())

    tool_fn = create_tool_for_message(CalculateTaxCommand, mock_pipeline)
    res = await tool_fn(amount=100.0, tax_rate=1.0)
    assert res == {"async_total": 200.0}

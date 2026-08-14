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


@pytest.mark.anyio
async def test_create_tool_for_message(pipeline: ExecutionPipeline):
    tool_fn = create_tool_for_message(CalculateTaxCommand, pipeline)
    assert tool_fn.__name__ == "CalculateTaxCommand"

    res = await tool_fn(amount=100.0, tax_rate=0.2)
    assert res == {"total": 120.0}


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

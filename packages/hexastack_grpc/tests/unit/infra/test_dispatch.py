from dataclasses import dataclass

from hexastack_core.domain.command import Command
from hexastack_core.domain.query import Query
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.infra.decorators import command_handler, query_handler
from hexastack_grpc.infra.dispatch import (
    dispatch_rpc_command,
    dispatch_rpc_query,
)


@dataclass(frozen=True)
class CreateOrderCommand(Command):
    order_id: str
    amount: float


@command_handler(CreateOrderCommand)
class CreateOrderHandler:
    def __call__(self, cmd: CreateOrderCommand) -> str:
        return f"Order {cmd.order_id} created for ${cmd.amount}"


@dataclass(frozen=True)
class GetOrderQuery(Query):
    order_id: str


@query_handler(GetOrderQuery)
class GetOrderHandler:
    def __call__(self, qry: GetOrderQuery) -> dict[str, str]:
        return {"order_id": qry.order_id, "status": "CONFIRMED"}


def test_dispatch_rpc_helpers():
    runtime = bootstrap(packages_to_scan=[__name__])

    # Mock protobuf-like request
    class MockProtoRequest:
        def __init__(self, order_id: str, amount: float = 0.0) -> None:
            self.order_id = order_id
            self.amount = amount

    cmd_req = MockProtoRequest(order_id="ord-100", amount=49.99)
    cmd_res = dispatch_rpc_command(
        request=cmd_req,
        command_cls=CreateOrderCommand,
        container=runtime.container,
    )
    assert cmd_res == "Order ord-100 created for $49.99"

    qry_req = MockProtoRequest(order_id="ord-100")
    qry_res = dispatch_rpc_query(
        request=qry_req,
        query_cls=GetOrderQuery,
        container=runtime.container,
    )
    assert qry_res == {"order_id": "ord-100", "status": "CONFIRMED"}

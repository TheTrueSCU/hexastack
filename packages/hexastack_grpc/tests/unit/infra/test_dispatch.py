from dataclasses import dataclass

import pytest

from hexastack_core.domain.command import Command
from hexastack_core.domain.query import Query
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.infra.decorators import command_handler, query_handler
from hexastack_grpc.infra.dispatch import (
    dispatch_rpc_command,
    dispatch_rpc_command_async,
    dispatch_rpc_query,
    dispatch_rpc_query_async,
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


class MockProtoRequest:
    def __init__(self, order_id: str, amount: float = 0.0) -> None:
        self.order_id = order_id
        self.amount = amount


@pytest.mark.anyio
async def test_dispatch_rpc_async_helpers():
    runtime = bootstrap(packages_to_scan=[__name__])

    cmd_req = MockProtoRequest(order_id="ord-async-1", amount=19.99)
    cmd_res = await dispatch_rpc_command_async(
        request=cmd_req,
        command_cls=CreateOrderCommand,
        container=runtime.container,
    )
    assert cmd_res == "Order ord-async-1 created for $19.99"

    qry_req = MockProtoRequest(order_id="ord-async-1")
    qry_res = await dispatch_rpc_query_async(
        request=qry_req,
        query_cls=GetOrderQuery,
        container=runtime.container,
    )
    assert qry_res == {"order_id": "ord-async-1", "status": "CONFIRMED"}


def test_dispatch_rpc_helpers():
    runtime = bootstrap(packages_to_scan=[__name__])

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


@pytest.mark.anyio
async def test_dispatch_rpc_async_with_awaitable_handlers():
    """Verify dispatch_rpc_command_async and dispatch_rpc_query_async when bus returns coroutine."""
    from rodi import Container

    from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort

    class AsyncMockCmdBus:
        async def dispatch(self, cmd):
            return f"async-bus-cmd-{cmd.order_id}"

    class AsyncMockQryBus:
        async def dispatch(self, qry):
            return f"async-bus-qry-{qry.order_id}"

    container = Container()
    container.add_instance(AsyncMockCmdBus(), declared_class=CommandBusPort)
    container.add_instance(AsyncMockQryBus(), declared_class=QueryBusPort)

    cmd_req = MockProtoRequest(order_id="async-awaitable-1")
    cmd_res = await dispatch_rpc_command_async(
        request=cmd_req,
        command_cls=CreateOrderCommand,
        container=container,
    )
    assert cmd_res == "async-bus-cmd-async-awaitable-1"

    qry_req = MockProtoRequest(order_id="async-awaitable-2")
    qry_res = await dispatch_rpc_query_async(
        request=qry_req,
        query_cls=GetOrderQuery,
        container=container,
    )
    assert qry_res == "async-bus-qry-async-awaitable-2"


@pytest.mark.anyio
async def test_dispatch_rpc_streaming_helpers():
    """Verify dispatch_rpc_stream_query and dispatch_rpc_bidirectional_stream."""
    from rodi import Container

    from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
    from hexastack_grpc.infra.dispatch import (
        dispatch_rpc_bidirectional_stream,
        dispatch_rpc_stream_query,
    )

    class MockStreamBus:
        def dispatch(self, msg):
            if isinstance(msg, GetOrderQuery):

                async def gen():
                    yield f"chunk1_{msg.order_id}"
                    yield f"chunk2_{msg.order_id}"

                return gen()
            if isinstance(msg, CreateOrderCommand):
                return f"processed_{msg.order_id}"
            return None

    container = Container()
    container.add_instance(MockStreamBus(), declared_class=CommandBusPort)
    container.add_instance(MockStreamBus(), declared_class=QueryBusPort)

    # 1. Server stream query
    req = MockProtoRequest(order_id="stream-99")
    chunks = [
        c
        async for c in dispatch_rpc_stream_query(
            request=req, query_cls=GetOrderQuery, container=container
        )
    ]
    assert chunks == ["chunk1_stream-99", "chunk2_stream-99"]

    # 2. Bidirectional stream
    async def request_stream():
        yield MockProtoRequest(order_id="bidi-1", amount=10.0)
        yield MockProtoRequest(order_id="bidi-2", amount=20.0)

    out_chunks = [
        c
        async for c in dispatch_rpc_bidirectional_stream(
            requests_iterator=request_stream(),
            command_cls=CreateOrderCommand,
            container=container,
        )
    ]
    assert out_chunks == ["processed_bidi-1", "processed_bidi-2"]

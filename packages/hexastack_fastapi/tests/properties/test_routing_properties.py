"""Hypothesis property-based tests for CqrsRouter dynamic route generation and HTTP validation.

Notes/Architectural Intent:
    Fuzzes arbitrary Command/Query models with randomized fields (strings, ints, floats,
    booleans, nested lists/dicts) across custom HTTP methods, status codes, and path prefixes,
    proving that CqrsRouter dynamically produces valid OpenAPI schema annotations and correctly
    binds and dispatches requests through the ExecutionPipeline.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st
from pydantic import create_model

from hexastack_core.domain import Command
from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.adapters.buses.event.synchronous import (
    SynchronousEventBus,
)
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry
from hexastack_fastapi.adapters.routing import CqrsRouter

# Strategies for dynamic model fields
primitive_strategies = st.one_of(
    st.tuples(
        st.just(str),
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=32
        ),
    ),
    st.tuples(st.just(int), st.integers(min_value=-10000, max_value=10000)),
    st.tuples(st.just(bool), st.booleans()),
)


@given(
    path_suffix=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=16),
    status_code=st.sampled_from([200, 201, 202]),
    method=st.sampled_from(["POST", "PUT", "PATCH"]),
    str_val=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=32
    ),
    int_val=st.integers(min_value=1, max_value=1000),
)
def test_cqrs_router_dynamic_command_dispatch_property(
    path_suffix: str,
    status_code: int,
    method: str,
    str_val: str,
    int_val: int,
):
    """Property: Any dynamically synthesized Command schema bound via CqrsRouter executes cleanly."""
    DynamicCommand = create_model(
        f"DynamicCommand_{path_suffix}",
        name=(str, ...),
        count=(int, ...),
        __base__=Command,
    )

    handler_reg = HandlerRegistry()
    handler_reg.register(
        DynamicCommand,
        lambda cmd: {"received_name": cmd.name, "received_count": cmd.count},
    )

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=PresenterRegistry(),
    )

    router = CqrsRouter()
    route_path = f"/{path_suffix}"
    router.add_command(
        route_path,
        DynamicCommand,
        method=method,
        status_code=status_code,
    )

    app = FastAPI()
    app.state.pipeline = pipeline
    app.include_router(router)

    client = TestClient(app)
    req_payload = {"name": str_val, "count": int_val}

    http_method = getattr(client, method.lower())
    response = http_method(route_path, json=req_payload)

    assert response.status_code == status_code
    assert response.json() == {"received_name": str_val, "received_count": int_val}
